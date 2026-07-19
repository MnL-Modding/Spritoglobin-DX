import copy
import struct
from io import BytesIO

from mnllib.bis import decompress as rlz_decompress
import numpy

from spritoglobin_dx.constants import *
from spritoglobin_dx.graphics import SIZING_TABLE, SWIZZLE_TABLE, get_sprite_graphic, get_sprite_part_set_graphic, draw_part
from spritoglobin_dx import palette_anim


class InvalidObjectFileError(Exception):
    """
    Raised when an invalid object file is attempted to be parsed.
    Code 100: All key tests failed.
    Code 101: BG4 file has no cellanim info.
    Code 102: File is not a BG4 file, or the given metadata produced undesirable results.
    """
    def __init__(self, error_code):
        message = {
            100: "Bad Game ID Tests",
            101: "No _CA_INFO_",
            102: "Bad Archive",
        }[error_code]
        super().__init__(message)
        self.error_code = error_code


class ObjFile:
    def __init__(self, input_data, game_id = None):
        self.cellanim_files = {}
        self.palette_files = {"": self.PaletteFile("", b'')}
        self.data_files = {"": self.DataFile("", None)}
        self.cached_objects = {}

        # each known container format is simply attempted in turn
        try:
            bg4_extract, self.bg4_version, self.valid_entries, self.invalid_entries = self.bg4_extract(input_data)

            for name in bg4_extract:
                data = bg4_extract[name]

                if name != "_CA_INFO_":
                    self.data_files[name] = self.DataFile(name, data)
                    continue

                cellanim_info = self.DataFile(name, data)

                cellanim_extract, self.bg4_ca_version, self.valid_ca_entries, self.invalid_ca_entries = self.bg4_extract(cellanim_info.decompress_data("blz"))
                for name in cellanim_extract:
                    self.cellanim_files[name] = self.CellAnimFile(name, cellanim_extract[name])

            if game_id is None:
                for game_key in GAME_IDS_THAT_USE_BG4:
                    tests_completed = True
                    for file in self.cellanim_files:
                        self.cellanim_files[file].interpret_data(game_key)
                        test = self.AnimData(self.data_files[self.cellanim_files[file].anim_file].decompress_data(game_key), game_key, test = True)

                        # if file uses sprite sheet mode, move on TODO: re-enable and finish
                        # if test.sprite_sheet_mode:
                        #     continue

                        test_value = test.anim_offset + (test.anim_num * test.anim_size)
                        test_conditional = test_value == test.frame_offset
                        if not test_conditional:
                            tests_completed = False
                            break
                    if tests_completed: game_id = game_key

        except ValueError:
            # not a BG4 archive; try the NDS games' ".dat" sprite containers
            # (support for further container formats would go here as the next
            # attempts)
            try:
                nds_extract, self.valid_entries, self.invalid_entries = self.nds_dat_extract(input_data)

                for name in nds_extract:
                    data = nds_extract[name]

                    if name != "0000":
                        self.data_files[name] = self.DataFile(name, data)
                        continue

                    # entry 0 holds the sprite and palette records, filling the
                    # role that _CA_INFO_ fills in the BG4 archives
                    self.nds_is_bobj, sprites, nds_palettes = self.nds_header_extract(data, len(nds_extract))
                    for i, data in enumerate(sprites):
                        if data == bytes(len(data)): continue # invalid data TODO: display that number
                        name = f"Sprite 0x{i:03X}"
                        self.cellanim_files[name] = self.CellAnimFile(name, data)
                    for i, data in enumerate(nds_palettes):
                        name = f"{i:04X}"
                        self.palette_files[name] = self.PaletteFile(name, data)

                if game_id is None:
                    for game_key in GAME_IDS_THAT_ARE_ON_NDS:
                        tests_completed = True
                        for file in self.cellanim_files:
                            self.cellanim_files[file].interpret_data(game_key)
                            # if the sprite has no animation data, move on
                            if self.cellanim_files[file].anim_file == "0000":
                                continue

                            test = self.data_files[self.cellanim_files[file].anim_file].decompress_data(game_key)

                            if len(test) < 0x18:
                                tests_completed = False
                                break

                            transform_count, = struct.unpack_from('<H', test, 0x2)
                            sequence_count, frame_count, clip_count, layer_count = struct.unpack_from('<4H', test, 0xC)

                            test_value = 0x18 + (sequence_count * 8) + (frame_count * 4) + (clip_count * 4) + (layer_count * 12) + (transform_count * 12)
                            test_conditional = sequence_count != 0 and frame_count != 0 and clip_count != 0 and test_value <= len(test)
                            if not test_conditional:
                                tests_completed = False
                                break
                        if tests_completed: game_id = game_key

            except ValueError:
                # nothing recognized the file, report error 102 ("Bad Archive")
                raise InvalidObjectFileError(102)

        self.game_id = game_id

        if self.cellanim_files == {}:
            # no _CA_INFO_, report error 101 ("No _CA_INFO_")
            raise InvalidObjectFileError(101)

        if self.game_id is None:
            # all tests failed, report error 100 ("Bad Game ID Tests")
            raise InvalidObjectFileError(100)

        for file in self.cellanim_files: # just in case
            self.cellanim_files[file].interpret_data(self.game_id)
        for file in self.palette_files:
            self.palette_files[file].interpret_data(self.game_id)
    
    def perform_tests(self):
        return

        for file in self.cellanim_files:
            test = self.AnimData(self.data_files[self.cellanim_files[file].anim_file].decompress_data(self.game_id), self.game_id)
    
    def cache_object(self, object_name, cache_id = None):
        if cache_id is None:
            cache_id = "_main_"

        cached_object = self.get_cached_object(cache_id)

        if cached_object.name != object_name:
            current_obj_data = self.cellanim_files[object_name]
            current_pal_data = self.palette_files[current_obj_data.palette_entry]

            # for testing DT
            use_force = False
            force_root = "DT/FObjUI"
            force = (0x130, 0x131, None)

            cached_object.name = object_name

            if not use_force or not force[0] is not None:
                cached_object.obj_anim_data = self.AnimData(self.data_files[current_obj_data.anim_file].decompress_data(self.game_id), self.game_id)
            else:
                with open(f"{force_root}/{force[0]:04X}.dat", "rb") as test:
                    cached_object.obj_anim_data = self.AnimData(test.read(), "ML4")

            if not use_force or not force[1] is not None:
                cached_object.graph_file = self.data_files[current_obj_data.graph_file].decompress_data(self.game_id)
            else:
                with open(f"{force_root}/{force[1]:04X}.dat", "rb") as test:
                    cached_object.graph_file = test.read()

            if not use_force or not force[2] is not None:
                cached_object.color_data = self.ColorData(self.data_files[current_obj_data.color_file].decompress_data(self.game_id))
            else:
                with open(f"{force_root}/{force[2]:04X}.dat", "rb") as test:
                    cached_object.color_data = self.ColorData(test.read())

            pal_data = self.data_files[current_pal_data.palette_file].data
            pal_anim_data = self.data_files[current_pal_data.palette_anim_file].data
            
            cached_object.palette_data = self.PaletteData(
                pal_data[:current_pal_data.palette_size] if pal_data is not None else b'',
                pal_anim_data[:current_pal_data.palette_anim_size] if pal_anim_data is not None else b'',
            )
            
            self.cached_objects[cache_id] = cached_object
    
    def get_cached_object(self, cache_id = None):
        if cache_id is None:
            cache_id = "_main_"

        return self.cached_objects.get(cache_id, self.ObjectCache(None))
    
    def get_file_properties(self):
        return {
            "game_id": self.game_id,
        }
    
    def get_object_palette(self, object_name, strict = False, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)

        if self.game_id not in GAME_IDS_THAT_USE_PALETTES:
            return None

        obj_data = cached_object.obj_anim_data
        palette_data = cached_object.palette_data

        try:
            animation_timer = self.animation_timer
        except AttributeError:
            animation_timer = 0

        palette = palette_data.get_palette(
            timer  = animation_timer,
            strict = strict,
        )

        return palette
    
    def get_object_pica200_palette(self, object_name, animation_index, color_anim_index = None, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)

        if self.game_id not in GAME_IDS_THAT_USE_PICA200_RENDERING:
            return None

        obj_data = cached_object.obj_anim_data
        color_data = cached_object.color_data
        anim_data = obj_data.get_anim_data(animation_index)

        try:
            animation_timer = self.animation_timer
            color_timer = self.color_timer
        except AttributeError:
            animation_timer = 0
            color_timer = 0

        if anim_data.anim_length is None:
            anim_length = 0
            for i in range(anim_data.total_frames):
                frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
                anim_length += frame_data.anim_duration
        else:
            anim_length = anim_data.anim_length

        anim_set = color_data.get_rgba(
            anim_index        = animation_index,
            global_anim_index = color_anim_index,
            time_anim         = animation_timer,
            time_color        = color_timer,
            anim_length       = anim_data.anim_length,
        )

        renderer_colors = copy.deepcopy(obj_data.default_renderer_colors)
        for color_mod, renderer_channel in anim_set:
            for i, channel in enumerate(color_mod):
                if channel is not None:
                    renderer_colors[renderer_channel][i] = channel
    
        return renderer_colors
    
    def get_object_properties(self, object_name, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)

        obj_data = cached_object.obj_anim_data
        color_data = cached_object.color_data
        palette_data = cached_object.palette_data

        has_color_data = color_data.global_animations != {} or palette_data.input_anim_data.getbuffer().nbytes != 0

        return {
            "animation_number":  obj_data.anim_num,
            "color_mode":        obj_data.color_mode,
            "renderer_number":   obj_data.renderer_num,
            "bounding_box":      obj_data.bounding_box,
            "has_color_data":    has_color_data,
            "color_data":        color_data.global_animations,
            "sprite_sheet_mode": obj_data.sprite_sheet_mode,
        }
    
    def get_animation_properties(self, object_name, animation_index, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)

        anim_data = cached_object.obj_anim_data.get_anim_data(animation_index)
        color_data = cached_object.color_data

        keyframe_list = [0]
        timer_accumulate = 0
        for i in range(anim_data.total_frames - 1):
            frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
            if frame_data.anim_timer is None:
                timer_accumulate += frame_data.anim_duration
                keyframe_list.append(timer_accumulate)
            else:
                keyframe_list.append(frame_data.anim_timer)
        
        has_color_data = animation_index in color_data.animations

        if anim_data.anim_length is None:
            anim_length = 0
            for i in range(anim_data.total_frames):
                frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
                anim_length += frame_data.anim_duration
        else:
            anim_length = anim_data.anim_length

        return {
            "first_frame":    anim_data.first_frame,
            "total_frames":   anim_data.total_frames,
            "length":         anim_length,
            "keyframes":      keyframe_list,
            "bounding_box":   anim_data.bounding_box,
            "has_color_data": has_color_data,
            "color_data":     color_data.animations,
        }
    
    def get_frame_properties(self, object_name, animation_index = None, frame_index = None, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)

        anim_data = cached_object.obj_anim_data.get_anim_data(animation_index)

        if frame_index is None:
            try:
                anim_data = cached_object.obj_anim_data.get_anim_data(animation_index)

                if anim_data.anim_length is None:
                    anim_length = 0
                    for i in range(anim_data.total_frames):
                        frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
                        anim_length += frame_data.anim_duration
                else:
                    anim_length = anim_data.anim_length

                timer = self.animation_timer % anim_length

                timer_accumulate = 0
                for i in range(anim_data.total_frames):
                    frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
                    if frame_data.anim_timer is None:
                        timer_accumulate += frame_data.anim_duration
                        anim_timer = timer_accumulate
                    else:
                        anim_timer = frame_data.anim_timer
                    if not timer >= anim_timer:
                        frame_index = i
                        break
            except AttributeError:
                frame_index = 0
        
        if animation_index is None:
            frame_data = cached_object.obj_anim_data.get_frame_data(frame_index)
        else:
            frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + frame_index)

        if frame_data.transform != 0: transform_matrix = cached_object.obj_anim_data.get_full_transform_data(frame_data.transform - 1).matrix
        else: transform_matrix = []

        if transform_matrix != []:
            if frame_data.invert_matrix_rotation is None:
                invert_matrix = (transform_matrix[0] < 0) != (transform_matrix[4] < 0)
            else:
                invert_matrix = frame_data.invert_matrix_rotation == 1
        else:
            invert_matrix = False

        timer_accumulate = 0
        if frame_data.anim_timer is None:
            for i in range(frame_index):
                test_frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
                timer_accumulate += test_frame_data.anim_duration
            anim_timer = timer_accumulate
        else:
            anim_timer = frame_data.anim_timer

        return {
            "first_part":         frame_data.first_part,
            "total_parts":        frame_data.total_parts,
            "keyframe_timer":     anim_timer,
            "transform_index":    frame_data.transform - 1,
            "transform":          transform_matrix,
            "transform_inverted": invert_matrix,
        }
    
    def get_sprite_part_properties(self, object_name, sprite_part_index, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)

        part_data = cached_object.obj_anim_data.get_part_data(sprite_part_index)

        return {
            "oam_size":        part_data.part_size,
            "oam_shape":       part_data.part_shape,
            "horizontal_flip": part_data.x_flip,
            "vertical_flip":   part_data.y_flip,
            "size":            SIZING_TABLE[part_data.part_shape][part_data.part_size],
            "buffer_offset":   part_data.graphics_buffer_offset,
            "offset":          (part_data.x_offset, part_data.y_offset),
            "renderer_index":  part_data.renderer,
            "palette_shift":   part_data.palette_shift,
        }
    
    def get_sprite(self, object_name, animation_index, color_anim_index = None, frame_index = None, bypass_shader = False, cache_id = None):
        img, size, _ = self._get_sprite_data(
            object_name      = object_name,
            animation_index  = animation_index,
            color_anim_index = color_anim_index,
            frame_index      = frame_index,
            bypass_shader    = bypass_shader,
            separate         = False,
            cache_id         = cache_id,
        )

        return img, size
    
    def get_sprite_with_offset(self, object_name, animation_index, color_anim_index = None, frame_index = None, bypass_shader = False, cache_id = None):
        img, size, offset = self._get_sprite_data(
            object_name      = object_name,
            animation_index  = animation_index,
            color_anim_index = color_anim_index,
            frame_index      = frame_index,
            bypass_shader    = bypass_shader,
            separate         = False,
            cache_id         = cache_id,
        )

        return img, size, offset
    
    def get_sprite_part_entities(self, object_name, animation_index, color_anim_index = None, frame_index = None, bypass_shader = False, cache_id = None):
        data = self._get_sprite_data(
            object_name      = object_name,
            animation_index  = animation_index,
            color_anim_index = color_anim_index,
            frame_index      = frame_index,
            bypass_shader    = bypass_shader,
            separate         = True,
            cache_id         = cache_id,
        )

        return data
    
    def _get_sprite_data(self, object_name, animation_index, color_anim_index, frame_index, bypass_shader, separate, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)
        
        obj_anim_data = cached_object.obj_anim_data
        graph_file    = cached_object.graph_file
        color_data    = cached_object.color_data
        palette_data  = cached_object.palette_data

        if frame_index is None:
            try:
                anim_data = obj_anim_data.get_anim_data(animation_index)

                if anim_data.anim_length is None:
                    anim_length = 0
                    for i in range(anim_data.total_frames):
                        frame_data = cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
                        anim_length += frame_data.anim_duration
                else:
                    anim_length = anim_data.anim_length

                timer = self.animation_timer % anim_length

                timer_accumulate = 0
                for i in range(anim_data.total_frames):
                    frame_data = obj_anim_data.get_frame_data(anim_data.first_frame + i)
                    if frame_data.anim_timer is None:
                        timer_accumulate += frame_data.anim_duration
                        anim_timer = timer_accumulate
                    else:
                        anim_timer = frame_data.anim_timer
                    if not timer >= anim_timer:
                        frame_index = i
                        break

                animation_timer = self.animation_timer
                color_timer = self.color_timer
            except AttributeError:
                frame_index = 0
                animation_timer = 0
                color_timer = 0

        return get_sprite_graphic(
            obj_anim_data       = obj_anim_data, 
            graph_file          = graph_file,
            palette_data        = palette_data,
            current_anim_index  = animation_index,
            color_anim_index    = color_anim_index,
            current_frame_index = frame_index,
            current_time_anim   = animation_timer,
            current_time_color  = color_timer,
            color_data          = color_data,
            bypass_shader       = bypass_shader,
            separate            = separate,
        )
    
    def get_sprite_part_set_with_offset(self, object_name, first_part, total_parts, highlighted_part = None, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)
        
        obj_anim_data = cached_object.obj_anim_data
        graph_file    = cached_object.graph_file
        palette_data  = cached_object.palette_data
        
        return get_sprite_part_set_graphic(
            obj_anim_data    = obj_anim_data,
            graph_file       = graph_file,
            palette_data     = palette_data,
            first_part       = first_part,
            total_parts      = total_parts,
            highlighted_part = highlighted_part,
        )
    
    def get_sprite_part_graphic(self, object_name, sprite_part_index, cache_id = None):
        self.cache_object(object_name, cache_id)
        cached_object = self.get_cached_object(cache_id)

        part_data     = cached_object.obj_anim_data.get_part_data(sprite_part_index)
        graph_file    = cached_object.graph_file
        obj_anim_data = cached_object.obj_anim_data
        palette_data  = cached_object.palette_data

        try:
            animation_timer = self.animation_timer
        except AttributeError:
            animation_timer = 0

        palette = palette_data.get_palette(
            timer  = animation_timer,
            strict = strict,
        )
        
        return draw_part(
            part_data     = part_data,
            graph_file    = graph_file,
            obj_anim_data = obj_anim_data,
            palette       = palette,
            ignore_flips  = True,
        )
    
    def reset_timers(self):
        self.animation_timer = 0
        self.color_timer = 0
    
    init_timers = reset_timers
    
    def increment_timers(self, delta, animation_timer = False, color_timer = False):
        if animation_timer:
            self.animation_timer += delta

        if color_timer:
            self.color_timer += delta
    
    def set_timers(self, time, animation_timer = False, color_timer = False):
        if isinstance(time, int):
            time = (time, time)

        if animation_timer:
            self.animation_timer = time[0]

        if color_timer:
            self.color_timer = time[1]
    
    def get_timers(self, animation_timer = False, color_timer = False):
        timers = []

        if animation_timer:
            timers.append(self.animation_timer)

        if color_timer:
            timers.append(self.color_timer)

        return timers

    def bg4_extract(self, input_data): # stole most of this from danius
        files = {}
        valid_count, invalid_count = 0, 0
        data = BytesIO(input_data)

        header_magic = b"BG4\0"
        # header_versions = [0x0105, 0x0104, 0x0305]

        # --- Header ---
        magic = data.read(4)
        if magic != header_magic:
            raise ValueError("invalid BG4 magic")

        version = int.from_bytes(data.read(2), 'little')
        # if version not in header_versions:
        #     raise ValueError(f"unsupported version {version:#04x}")

        file_count = int.from_bytes(data.read(2), 'little')
        meta_size = int.from_bytes(data.read(4), 'little')
        _ = int.from_bytes(data.read(2), 'little')  # derived count
        _ = int.from_bytes(data.read(2), 'little')  # multiplier

        # --- File entries ---
        entries = []
        for _ in range(file_count):
            file_offset = int.from_bytes(data.read(4), 'little') & 0x7FFFFFFF
            file_size   = int.from_bytes(data.read(4), 'little') & 0x7FFFFFFF
            _name_hash  = int.from_bytes(data.read(4), 'little')
            name_offset = int.from_bytes(data.read(2), 'little')
            entries.append((file_offset, file_size, name_offset))

        # --- File names ---
        names_origin = data.tell()
        names = []
        for _, _, name_offset in entries:
            data.seek(names_origin + name_offset)
            name_bytes = bytearray()
            while (c := data.read(1)) != b"\0":
                name_bytes.append(c[0])
            names.append(name_bytes.decode("ascii"))

        # --- Extract files ---
        for i, (file_offset, file_size, _) in enumerate(entries):
            name = names[i]
            if not name or name.lower() == "(invalid)":
                invalid_count += 1
                continue
            valid_count += 1
            data.seek(file_offset)
            raw = data.read(file_size)
            files[name] = raw

        return files, ((version >> 8) & 0xFF, version & 0xFF), valid_count, invalid_count

    def nds_dat_extract(self, input_data):
        files = {}
        padding_words = 0
        data = BytesIO(input_data)

        # --- Offset table ---
        # the first offset is also the table's byte length, and unused
        # trailing words are 0xFFFFFFFF
        first_offset = int.from_bytes(data.read(4), 'little')
        if first_offset < 8 or first_offset % 4 != 0 or first_offset > len(input_data):
            raise ValueError("invalid .dat offset table")

        offsets = [first_offset]
        for i in range(1, first_offset // 4):
            word = int.from_bytes(data.read(4), 'little')
            if word == 0xFFFFFFFF:
                padding_words = (first_offset // 4) - i
                break
            if word < offsets[-1] or word > len(input_data):
                raise ValueError("invalid .dat offset table")
            offsets.append(word)

        if len(offsets) < 3 or offsets[-1] != len(input_data):
            raise ValueError("invalid .dat offset table")

        # --- Extract entries ---
        for i in range(len(offsets) - 1):
            data.seek(offsets[i])
            files[f"{i:04X}"] = data.read(offsets[i + 1] - offsets[i])

        return files, len(files), padding_words

    def nds_header_extract(self, header, entry_count):
        data = BytesIO(header)

        # --- Header ---
        # entry 0 of a sprite container holds the sprite and palette records
        sprite_count = int.from_bytes(data.read(4), 'little')
        palette_count = int.from_bytes(data.read(4), 'little')
        if not 0 < sprite_count < 0x10000 or not 0 < palette_count < 0x10000:
            raise ValueError("no sprite header")

        # battle sprite records are 0x14 bytes with 0xFFFF at offset 4;
        # field sprite records are 8 bytes
        for record_size in (0x14, 0x8):
            if 8 + (sprite_count * record_size) + (palette_count * 8) > len(header):
                continue

            # --- Sprite records ---
            data.seek(8)
            sprites = []
            for _ in range(sprite_count):
                sprites.append(data.read(record_size))
            if len(sprites) != sprite_count:
                continue

            # --- Palette records ---
            palettes = []
            for _ in range(palette_count):
                palettes.append(data.read(8))
            if len(palettes) != palette_count:
                continue

            return record_size == 0x14, sprites, palettes

        raise ValueError("invalid sprite or palette records")

    def nds_convert_object(self, anim_data, graph_file, palette, is_bobj):
        # Parse one sprite's NDS animation and pixel data into the AnimData
        # layout and the swizzled RGBA8888 tile buffer the rest of the program
        # already understands, so that nothing past this point needs any NDS
        # handling.
        #
        # A PiT *sequence* plays a run of *frames*; every frame shows one
        # *clip* for some duration; a clip is a run of *layers*, which are
        # OAM-like graphics with optional per-layer affine transforms.
        # Sequences map straight onto animation records, frames onto frame
        # records (with their clip's layer run and their end time filled in),
        # and layers onto sprite part records.
        try:
            flags, transform_count = struct.unpack_from('<2H', anim_data, 0)
            sequence_count, frame_count, clip_count, layer_count = struct.unpack_from('<4H', anim_data, 0xC)
            sequences_offset = 0x18
            frames_offset = sequences_offset + (sequence_count * 8)
            clips_offset = frames_offset + (frame_count * 4)
            layers_offset = clips_offset + (clip_count * 4)
            transforms_offset = layers_offset + (layer_count * 12)
            if not sequence_count or not frame_count or not clip_count or transforms_offset + (transform_count * 12) > len(anim_data):
                raise ValueError("animation arrays don't fit the decompressed entry")

            sequences = [struct.unpack_from('<2H', anim_data, sequences_offset + (i * 8)) for i in range(sequence_count)]
            # the timing routines mask each frame's duration to its low 9 bits
            frames = [(clip, duration & 0x1FF) for clip, duration in
                      (struct.unpack_from('<2H', anim_data, frames_offset + (i * 4)) for i in range(frame_count))]
            clips = [struct.unpack_from('<2H', anim_data, clips_offset + (i * 4)) for i in range(clip_count)]
            layers = [struct.unpack_from('<6H', anim_data, layers_offset + (i * 12)) for i in range(layer_count)]
            transforms = [(angle, scale_x / 0x100, scale_y / 0x100) for angle, scale_x, scale_y in
                          (struct.unpack_from('<H2h', anim_data, transforms_offset + (i * 12)) for i in range(transform_count))]
        except Exception:
            # keep the UI alive on the couple of records that don't point at
            # real animation data (e.g. USA FObj.dat sprite 0x1AB) by swapping
            # in one empty single-frame animation
            flags = 0
            sequences, frames, clips, layers, transforms = [(0, 1)], [(0, 1)], [(0, 0)], [], []

        # each frame's keyframe timer is its end time in 60fps ticks,
        # cumulative from the start of its sequence
        frame_timers = [duration for clip, duration in frames]
        anim_lengths = []
        for first_frame, end_frame in sequences:
            total = 0
            for frame in range(first_frame, min(end_frame, len(frames))):
                total += frames[frame][1]
                frame_timers[frame] = min(total, 0xFFFF)
            anim_lengths.append(min(max(total, 1), 0xFFFF))

        # layers map onto sprite part records, and their paletted 4bpp/8bpp
        # graphics (OBJ tile chains in FObj files, or textures in BObj files,
        # where the layer word at 0x04 is an identity key and repeated keys
        # reuse the pixels of the first layer that used the key) get decoded
        # on first use into one shared RGBA8888 tile buffer. A layer's affine
        # transform and flips are static, so they get baked into its texture,
        # padded to the smallest fitting OAM size, or split into a grid of
        # 64x64 parts when not even that fits; its part record then needs
        # nothing beyond the ordinary fields.
        bobj_is256 = bool(flags & 0x4000)
        bobj_linear = bool(flags & 0x2000)

        colors = palette.astype(numpy.uint32)
        colors = (colors[:, 0] << 24) | (colors[:, 1] << 16) | (colors[:, 2] << 8) | colors[:, 3]

        part_fields = []
        part_starts = [0] # a layer scaled beyond 64x64 spans several parts
        textures = [numpy.zeros(64, dtype = numpy.uint32)] # a transparent 8x8 tile for malformed layers
        destinations = {}
        source_offsets = {}
        next_source = 0
        next_destination = 2
        for attr0, attr1, attr2, unknown_06, transform_word, unknown_0a in layers:
            shape = attr0 >> 14
            width, height = SIZING_TABLE[shape][attr1 >> 14] if shape < 3 else (0, 0)

            if is_bobj:
                is256, linear = bobj_is256, bobj_linear
                palette_bank = 0 if is256 else (transform_word >> 12) & 7
                if attr2 not in source_offsets:
                    source_offsets[attr2] = next_source
                    next_source += (width * height) if is256 else (width * height) // 2
                source = source_offsets[attr2]
            else:
                is256 = bool(attr0 & 0x2000)
                linear = False
                palette_bank = 0
                source = (attr2 & 0x3FF) * (0x40 if is256 else 0x20)

            if shape == 3: # prohibited OAM shape; point at the transparent tile
                part_fields.append((0, 0, 0, 0))
                part_starts.append(len(part_fields))
                continue

            # signed 8/9-bit offsets of the layer's top-left corner, relative
            # to the sprite's anchor; the part records use center-based
            # offsets with +Y up
            center_x = (((attr1 & 0x1FF) ^ 0x100) - 0x100) + (width // 2)
            center_y = (((attr0 & 0xFF) ^ 0x80) - 0x80) + (height // 2)

            transform = None
            if attr0 & 0x100 and (transform_word & 0x3FF) < len(transforms):
                transform = transforms[transform_word & 0x3FF]

            oam_data = (attr1 >> 14) | (shape << 2)
            if transform is None:
                baked_flips = (False, False)
                out_width, out_height = width, height
                if attr1 & 0x1000: oam_data |= 0x100
                if attr1 & 0x2000: oam_data |= 0x200
            else:
                # flips get baked along with the transform, and in double-size
                # mode the transform center is at (x + width, y + height)
                # instead of the layer's center
                baked_flips = (bool(attr1 & 0x1000), bool(attr1 & 0x2000))
                out_shape, out_size, out_width, out_height = self.nds_transformed_size(width, height, transform)
                if out_shape is not None:
                    oam_data = out_size | (out_shape << 2)
                if attr0 & 0x200:
                    center_x += width // 2
                    center_y += height // 2

            texture = (source, width, height, is256, linear, palette_bank, transform, baked_flips)
            if texture not in destinations:
                destinations[texture] = next_destination
                next_destination += (out_width * out_height * 4) // 128

                # decode the texture: expand the indices, detile, apply the
                # palette and bake the flips and transform
                byte_length = (width * height) if is256 else (width * height) // 2
                raw = numpy.zeros(byte_length, dtype = numpy.uint8)
                available = graph_file[source:source + byte_length]
                raw[:len(available)] = numpy.frombuffer(available, dtype = numpy.uint8)

                if is256:
                    indices = raw
                else:
                    # two pixels per byte, low nibble first
                    indices = numpy.empty(byte_length * 2, dtype = numpy.uint8)
                    indices[0::2] = raw & 0x0F
                    indices[1::2] = raw >> 4

                if linear:
                    indices = indices.reshape(height, width)
                else:
                    indices = indices.reshape(height // 8, width // 8, 8, 8).transpose(0, 2, 1, 3).reshape(height, width)

                pixels = (colors if is256 else colors[palette_bank * 16:(palette_bank * 16) + 16])[indices]
                pixels[indices == 0] = 0 # color 0 is transparent

                if baked_flips[0]: pixels = pixels[:, ::-1]
                if baked_flips[1]: pixels = pixels[::-1, :]
                if transform is not None:
                    pixels = self.nds_warp_texture(pixels, transform, out_width, out_height)

                # store as up-to-64x64 cells of swizzled 8x8 tiles
                cell_width, cell_height = min(out_width, 64), min(out_height, 64)
                tiles = pixels.reshape(out_height // cell_height, cell_height // 8, 8, out_width // cell_width, cell_width // 8, 8)
                tiles = tiles.transpose(0, 3, 1, 4, 2, 5).reshape(-1, 64)
                swizzled = numpy.empty_like(tiles)
                swizzled[:, SWIZZLE_TABLE] = numpy.ascontiguousarray(tiles)
                textures.append(swizzled.reshape(-1))
            destination = destinations[texture]

            if out_width <= 64 and out_height <= 64:
                part_fields.append((oam_data, destination, center_x, -center_y))
            else:
                # scaled up beyond the largest OAM size: the baked texture
                # becomes a grid of 64x64 parts (oam_data 3)
                for cell_y in range(out_height // 64):
                    for cell_x in range(out_width // 64):
                        cell_center_x = center_x + (cell_x * 64) + 32 - (out_width // 2)
                        cell_center_y = center_y + (cell_y * 64) + 32 - (out_height // 2)
                        cell_destination = destination + (((cell_y * (out_width // 64)) + cell_x) * 128)
                        part_fields.append((3, cell_destination, cell_center_x, -cell_center_y))

            part_starts.append(len(part_fields))

        graph_file = numpy.concatenate(textures).tobytes()

        # emit the parsed data as an AnimData blob: header, offsets and the 16
        # renderer colors (filled with the palette) like the native layouts,
        # then the animation, frame and part records
        anims_offset = 0xE + 0x14 + 0x40
        frame_offset = anims_offset + (len(sequences) * 8)
        part_offset = frame_offset + (len(frames) * 8)
        end_offset = part_offset + (len(part_fields) * 12)

        records = bytearray()
        records += struct.pack('<H2BH2I', len(sequences), 0, 0, 0, end_offset, len(graph_file))
        records += struct.pack('<5I', frame_offset, part_offset, end_offset, end_offset, end_offset)
        for i in range(16):
            records += struct.pack('4B', *palette[i])

        for (first_frame, end_frame), anim_length in zip(sequences, anim_lengths):
            end_frame = min(end_frame, len(frames))
            records += struct.pack('<4H', min(first_frame, len(frames)), max(end_frame - first_frame, 0), anim_length, 0)

        for (clip, duration), frame_timer in zip(frames, frame_timers):
            first_layer, end_layer = clips[clip] if clip < len(clips) else (0, 0)
            first_part = part_starts[min(first_layer, len(part_starts) - 1)]
            end_part = part_starts[min(max(end_layer, first_layer), len(part_starts) - 1)]
            records += struct.pack('<HBBHH', first_part, min(end_part - first_part, 0xFF), 0, frame_timer, 0)

        for oam_data, destination, x_offset, y_offset in part_fields:
            records += struct.pack('<HHhHhh', oam_data, 0, 0, destination, x_offset, y_offset)

        return bytes(records), graph_file

    def nds_transformed_size(self, width, height, transform):
        # the smallest OAM shape and size that fit the layer after rotation
        # and scaling; when nothing fits, a shapeless 64x64-celled grid size
        angle, scale_x, scale_y = transform
        theta = (angle / 0x10000) * 2 * numpy.pi
        cos, sin = abs(numpy.cos(theta)), abs(numpy.sin(theta))

        minimum_width = (abs(scale_x) * width * cos) + (abs(scale_y) * height * sin)
        minimum_height = (abs(scale_x) * width * sin) + (abs(scale_y) * height * cos)

        best = None
        for shape, sizing in enumerate(SIZING_TABLE):
            for size, (w, h) in enumerate(sizing):
                if w >= minimum_width and h >= minimum_height and (best is None or w * h < best[2] * best[3]):
                    best = (shape, size, w, h)

        if best is None:
            best = (None, None, max(-(int(minimum_width) // -64), 1) * 64, max(-(int(minimum_height) // -64), 1) * 64)

        return best

    def nds_warp_texture(self, pixels, transform, out_width, out_height):
        # rotate and scale around the center (a binary angle, running
        # clockwise on screen), exactly like the game's affine sampling
        angle, scale_x, scale_y = transform
        if scale_x == 0 or scale_y == 0:
            return numpy.zeros((out_height, out_width), dtype = numpy.uint32)

        theta = (angle / 0x10000) * 2 * numpy.pi
        cos, sin = numpy.cos(theta), numpy.sin(theta)

        height, width = pixels.shape
        out_y, out_x = numpy.indices((out_height, out_width), dtype = numpy.float64)
        out_x += 0.5 - (out_width / 2)
        out_y += 0.5 - (out_height / 2)

        source_x = numpy.floor((( cos * out_x) + (sin * out_y)) / scale_x + (width / 2)).astype(int)
        source_y = numpy.floor(((-sin * out_x) + (cos * out_y)) / scale_y + (height / 2)).astype(int)

        valid = (source_x >= 0) & (source_x < width) & (source_y >= 0) & (source_y < height)
        warped = numpy.zeros((out_height, out_width), dtype = numpy.uint32)
        warped[valid] = pixels[source_y[valid], source_x[valid]]

        return warped

    class ObjectCache:
        def __init__(self, name):
            self.name = name
    
    class CAFile:
        def get_string(self, input_data):
            string_end = input_data.find(0)
            return input_data[:string_end].decode("ascii")
        
        def get_num(self, number):
            return f"{number:04X}"
        
    class CellAnimFile(CAFile): # TODO: lots of unknowns here
        def __init__(self, name, input_data):
            self.name = name
            self.input_data = input_data

        def interpret_data(self, game_id):
            data = BytesIO(self.input_data)

            if game_id in GAME_IDS_THAT_USE_BG4: # > ml5
                self.anim_file = self.get_string(data.read(4))
                self.graph_file = self.get_string(data.read(4))
                self.color_file = self.get_string(data.read(4))
                self.palette_entry = ""
                self.hitbox_file = self.get_string(data.read(4)) # TODO: figure out how this works
                # more unknowns past here

            elif game_id in GAME_IDS_THAT_USE_PALETTES: # < ml3
                anim_file = int.from_bytes(data.read(2), 'little')
                self.anim_file = self.get_num(anim_file)
                self.graph_file = self.get_num(anim_file + 1)
                self.color_file = ""
                self.palette_entry = self.get_num(int.from_bytes(data.read(2), 'little'))
                # more unknowns past here
            
            else: # poor ol' lonely ml4
                ...
        
    class PaletteFile(CAFile): # TODO: lots of unknowns here
        def __init__(self, name, input_data):
            self.name = name
            self.input_data = input_data

        def interpret_data(self, game_id):
            data = BytesIO(self.input_data)

            if self.input_data == b'':
                self.palette_file = ""
                self.palette_anim_file = ""
                self.palette_size = 0
                self.palette_anim_size = 0
                return

            match game_id:
                case "ML2":
                    self.palette_file = self.get_num(int.from_bytes(data.read(2), 'little'))
                    palette_anim_file = int.from_bytes(data.read(2), 'little')
                    if palette_anim_file != 0xFFFF:
                        self.palette_anim_file = self.get_num(palette_anim_file)
                    else:
                        self.palette_anim_file = ""
                    self.palette_size = int.from_bytes(data.read(1)) * 0x20
                    self.palette_anim_size = int.from_bytes(data.read(1)) * 0x2
        
    class DataFile:
        def __init__(self, name, input_data):
            self.name = name
            self.data = input_data
        
        def decompress_data(self, key):
            if self.data == b'' or self.data is None: return b''

            key = {
                "ML2":  "rlz",
                "ML3":  "rlz",
                "ML5":  "blz",
                "ML1R": "blz",
                "ML3R": "blz",
            }.get(key, key)

            match key:
                case "blz":
                    return self.blz_decompress_data()
                case "rlz":
                    return rlz_decompress(BytesIO(self.data))
                case _:
                    return self.data

        def blz_decompress_data(self): # stole this from danius
            if self.data is None: return bytearray([])

            data = self.data

            """Detect if compressed and decompress using Backward LZ77"""
            # Uncompressed if too short or doesn't have footer
            if len(data) < 8:
                return data

            footer = data[-8:]
            buffer_top_and_bottom, _ = struct.unpack("<ii", footer)
            footer_len = (buffer_top_and_bottom >> 24) & 0xFF
            if footer_len == 0 or (buffer_top_and_bottom & 0xFFFFFF) == 0:
                return data  # likely uncompressed

            try:
                # Reverse input
                compressed_len = len(data) - footer_len
                compressed = data[:compressed_len][::-1]
                in_stream = BytesIO(compressed)
                out_stream = BytesIO()
                circular = bytearray(0x1002)
                pos = 0

                end_position = (buffer_top_and_bottom & 0xFFFFFF) - footer_len

                code_block = in_stream.read(1)[0]
                code_pos = 8

                while in_stream.tell() < end_position:
                    if code_pos == 0:
                        code_block = in_stream.read(1)[0]
                        code_pos = 8

                    flag = (code_block >> (code_pos - 1)) & 1
                    code_pos -= 1

                    if flag == 0:
                        b = in_stream.read(1)
                        if not b:
                            break
                        out_stream.write(b)
                        circular[pos % len(circular)] = b[0]
                        pos += 1
                    else:
                        pair = in_stream.read(2)
                        if len(pair) < 2:
                            break
                        b1, b2 = pair
                        length = (b1 >> 4) + 3
                        displacement = ((b1 & 0xF) << 8 | b2) + 3
                        start = pos - displacement
                        for _ in range(length):
                            val = circular[start % len(circular)]
                            out_stream.write(bytes([val]))
                            circular[pos % len(circular)] = val
                            start += 1
                            pos += 1
                    
                while in_stream.tell() < len(compressed):
                    out_stream.write(in_stream.read(1))

                # Reverse output
                return out_stream.getvalue()[::-1]
            except Exception:
                return data

    class AnimData:
        def __init__(self, input_data, game_id, test = False):
            self.input_data = BytesIO(input_data)
            # with open("test.dat", "wb") as test:
            #     test.write(input_data)

            self.game_id = game_id
            self.bounding_box = None

            match self.game_id:
                case "ML3R": # Bowser's Inside Story DX --- added bounding boxes, added a new unused offset in the header (might be padding)
                    self.anim_num, color_mode, self.renderer_num, unused, self.anim_file_length, self.graph_file_length = struct.unpack('<4B2I', self.input_data.read(0xC))
                    self.bounding_box = struct.unpack('<4h', self.input_data.read(0x8))
                    self.frame_offset, self.part_offset, self.part_trans_offset, self.full_trans_offset, self.renderer_offset, self.normal_offset, unused_offset = struct.unpack('<7I', self.input_data.read(0x1C))
                    self.tiled_mode = True

                    self.anim_size = 16
                    self.frame_size = 8
                    self.part_size = 16
                    self.part_trans_size = 16

                    self.renderer_size = 84
                    self.full_trans_size = 20
                    self.normal_size = 48

                    if unused_offset != 0 and not test: print(f"THE 'unused_offset_1' VALUE IN CLASS ObjFile.AnimData IS USED ACTUALLY: unused_offset_1 = {unused_offset}")
                    if unused != 0 and not test: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData IS USED ACTUALLY: unused = {unused}")

                case "ML1R": # Superstar Saga DX --- added normal maps (or something lighting related)
                    self.anim_num, color_mode, self.renderer_num, unused, self.anim_file_length, self.graph_file_length = struct.unpack('<4B2I', self.input_data.read(0xC))
                    self.frame_offset, self.part_offset, self.part_trans_offset, self.full_trans_offset, self.renderer_offset, self.normal_offset = struct.unpack('<6I', self.input_data.read(0x18))
                    self.tiled_mode = True

                    self.anim_size = 8
                    self.frame_size = 8
                    self.part_size = 16
                    self.part_trans_size = 16

                    self.renderer_size = 84
                    self.full_trans_size = 20
                    self.normal_size = 48

                    if unused != 0 and not test: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData IS USED ACTUALLY: unused = {unused}")

                case "ML4" | "ML5": # Dream Team & Paper Jam --- complete overhaul from the previous games
                    self.anim_num, color_mode, self.renderer_num, unused, self.anim_file_length, self.graph_file_length = struct.unpack('<4B2I', self.input_data.read(0xC))
                    self.frame_offset, self.part_offset, self.part_trans_offset, self.full_trans_offset, self.renderer_offset = struct.unpack('<5I', self.input_data.read(0x14))
                    self.tiled_mode = True

                    self.anim_size = 8
                    self.frame_size = 8
                    self.part_size = 12
                    self.part_trans_size = 16

                    self.renderer_size = 84
                    self.full_trans_size = 20

                    if unused != 0 and not test: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData IS USED ACTUALLY: unused = {unused}")
                    if self.full_trans_offset - self.part_trans_offset != 0 and not test: print(f"THE 'part_trans_offset' VALUE IN CLASS ObjFile.AnimData IS USED IN THIS FILE")

                case "ML2": # Partners in Time
                    # TODO: unknowns
                    flags, part_trans_num, unk, unk, unk, unk = struct.unpack('<6H', self.input_data.read(0xC))
                    self.anim_num, frame_num, part_set_num, part_num, unk = struct.unpack('<4HI', self.input_data.read(0xC))

                    # things are laid out like this so it's easy to see what bits are used where
                    self.graph_shift =    (flags & 0b0000000001110000) >> 4
                    color_mode       =    (flags & 0b0001110000000000) >> 10
                    self.tiled_mode  =     flags & 0b0010000000000000 == 0 # TODO: expose this to the user
                    bpp_flag         =     flags & 0b0100000000000000 != 0 # TODO: expose this to the user

                    self.color_mode = [{ # key, bits-per-pixel # TODO: make bpp's function more accurate to the DS hardware
                        1: "A3I5",
                        3: "I4",
                        4: "I8",
                        6: "A5I3",
                    }.get(color_mode, f"Not Found: {color_mode}"), 8 if bpp_flag else 4]

                    self.anim_offset = self.input_data.tell()

                    self.anim_size = 8
                    self.frame_size = 4
                    self.part_size = 12
                    self.part_trans_size = 12

                    self.part_set_size = 4

                    self.frame_offset = self.anim_offset + (self.anim_num * self.anim_size)
                    self.part_set_offset = self.frame_offset + (frame_num * self.frame_size)
                    self.part_offset = self.part_set_offset + (part_set_num * self.part_set_size)
                    self.part_trans_offset = self.part_offset + (part_num * self.part_size)

                    # whole-cell frame transforms index the same 0xC-byte transform
                    # pool as the per-part transforms (see AnimFrame's duration bits)
                    self.full_trans_offset = self.part_trans_offset
                    self.full_trans_size = self.part_trans_size

            if self.game_id in GAME_IDS_THAT_USE_PICA200_RENDERING:
                self.color_mode = [ # key, bits-per-pixel
                    ["RGBA8888", 32],
                    ["RGB888",   24],
                    ["RGBA5551", 16],
                    ["RGB565",   16],
                    ["RGBA4444", 16],
                    ["LA88",     16],
                    ["HILO88",   16],
                    ["L8",        8],
                    ["A8",        8],
                    ["LA44",      8],
                    ["L4",        4],
                    ["A4",        4],
                    ["ETC1",      4],
                    ["ETC1A4",    8],
                ][color_mode]

                self.default_renderer_colors = {}
                for i in range(16):
                    self.default_renderer_colors[i] = list(struct.unpack('4B', self.input_data.read(4)))
                self.anim_offset = self.input_data.tell()
            else:
                self.renderer_num = 0

            if self.game_id in GAME_IDS_THAT_USE_SPRITE_SHEETS:
                if self.part_offset != 0:
                    self.sprite_sheet_mode = False
                else:
                    self.sprite_sheet_mode = True
                    self.part_offset = self.anim_offset + (self.anim_num * self.anim_size)
            else:
                self.sprite_sheet_mode = False
    
        class Animation:
            def __init__(self, parent, input_data, game_id):
                if game_id in GAME_IDS_THAT_USE_ALT_COUNTING_SCHEMES:
                    # TODO: unknowns
                    self.first_frame, last_frame, unk, unk = struct.unpack('<4H', input_data[:8])
                    self.total_frames = last_frame - self.first_frame
                    self.anim_length = None
                else:
                    self.first_frame, self.total_frames, self.anim_length, unused = struct.unpack('<4H', input_data[:8])
                    if unused != 0: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData.Animation IS USED ACTUALLY: unused = {unused}")

                if game_id in GAME_IDS_THAT_USE_BOUNDING_BOXES:
                    self.bounding_box = struct.unpack('<4h', input_data[8:])
                else:
                    self.bounding_box = None
    
        class AnimFrame:
            def __init__(self, parent, input_data, game_id):
                if game_id in GAME_IDS_THAT_USE_SPLIT_PATTERN_DATA:
                    # TODO: unknown
                    part_set_index, self.anim_duration, unk = struct.unpack('<H2B', input_data)
                    self.first_part, last_part = struct.unpack('<2H', parent.get_data_at_offset(parent.part_set_size, parent.part_set_offset, part_set_index))
                    self.total_parts = last_part - self.first_part
                    # anim_duration/unk are the low/high bytes of a u16 duration word.
                    # the game masks timing to bits 0-8; bit 9 (unk & 0x02) flags a
                    # whole-cell transform and bits 10-15 ((unk >> 2) & 0x3F) index it.
                    self.transform = ((unk >> 2) & 0x3F) + 1 if unk & 0x02 else 0
                    self.anim_timer = None
                else:
                    self.first_part, self.total_parts, self.invert_matrix_rotation, self.anim_timer, self.transform = struct.unpack('<HBBHH', input_data)
                    self.anim_duration = None

                if game_id not in GAME_IDS_THAT_USE_MATRIX_INVERSION:
                    self.invert_matrix_rotation = None
    
        class SpritePart: # TODO: figure out what "horizontal_flip" actually does in ML4+
            def __init__(self, parent, input_data, game_id):
                match game_id:
                    case "ML2":
                        # TODO: unknowns
                        # TODO: do stuff with depth and flags and stuff
                        attr0, attr1, attr2, attr3, attr4, attr5 = struct.unpack('<6H', input_data)
                        # things are laid out like this so it's easy to see what bits are used where
                        self.y_offset               = ((attr0 & 0b0000000011111111) ^ 0x80) - 0x80
                        trans_flag                  =  (attr0 & 0b0000000100000000) != 0
                        double_size_flag            =  (attr0 & 0b0000001000000000) != 0
                        self.depth                  =  (attr0 & 0b0010000000000000) >> 13
                        self.part_shape             =  (attr0 & 0b1100000000000000) >> 14
        
                        self.x_offset               = ((attr1 & 0b0000000111111111) ^ 0x100) - 0x100
                        self.x_flip                 =  (attr1 & 0b0001000000000000) != 0
                        self.y_flip                 =  (attr1 & 0b0010000000000000) != 0
                        self.part_size              =  (attr1 & 0b1100000000000000) >> 14

                        self.graphics_buffer_offset =  (attr2 & 0b1111111111111111) << parent.graph_shift

                        self.transform              =  (attr4 & 0b0000001111111111) + 1 if trans_flag else 0
                        self.palette_shift          =  (attr4 & 0b0011110000000000) >> 10 # TODO: expose to user and also fix

                        # TODO: make transform shit available to all the thingies that get bounding boxes based on sprite

                        self.renderer = None
                    case _:
                        oam_data, self.renderer, self.horizontal_flip, self.graphics_buffer_offset, self.x_offset, self.y_offset = struct.unpack('<HHhHhh', input_data[:12])
                        self.part_size =  (oam_data)      & 0b11
                        self.part_shape = (oam_data >> 2) & 0b11
                        self.x_flip =     (oam_data)      & 0x100 != 0
                        self.y_flip =     (oam_data)      & 0x200 != 0
                        self.graphics_buffer_offset *= 0x80

                        if self.horizontal_flip != 0 and self.horizontal_flip != -1:
                            print(f"'self.horizontal_flip' IS WEIRD IN ONE OF THE SPRITE PARTS: {self.horizontal_flip}")

                        self.transform = 0 # TODO: find a way to make it obvious whether transform is unused or straight up not supported
                        self.palette_shift = 0

                if game_id in GAME_IDS_THAT_USE_NORMAL_MAPS:
                    self.normal_map, = struct.unpack('<I', input_data[12:])
                
                if game_id in GAME_IDS_THAT_USE_ALT_COORDINATES_SYSTEM: # TODO: make these changes reflect in sprite part info so it's not dishonest to the end user
                    x, y = SIZING_TABLE[self.part_shape][self.part_size]
                    if not double_size_flag:
                        self.x_offset += x // 2
                        self.y_offset += y // 2
                    else:
                        self.x_offset += x
                        self.y_offset += y

                    self.y_offset *= -1

        class Transform:
            def __init__(self, parent, input_data, game_id, has_offset = True):
                if game_id in GAME_IDS_THAT_USE_MATRICES:
                    if has_offset:
                        matrix = struct.unpack(f'<4{"f" if game_id in GAME_IDS_THAT_USE_FLOATS else "h"}2h', input_data)
                    else:
                        matrix = struct.unpack(f'<4{"f" if game_id in GAME_IDS_THAT_USE_FLOATS else "h"}', input_data) + (0, 0)

                    if game_id not in GAME_IDS_THAT_USE_FLOATS:
                        matrix = tuple([matrix[i] / 0x100 for i in range(6)])

                    self.matrix = [
                        matrix[0], matrix[2],  matrix[4],
                        matrix[1], matrix[3], -matrix[5],
                    ]
                else:
                    # TODO: unknowns? maybe?
                    angle, scale_x, scale_y, translate_x, translate_y = struct.unpack('<Hhhhh2x', input_data) # TODO: make the matrix be better
                    theta = (angle / 0x10000) * 2 * numpy.pi
                    scale_x /= 0x100
                    scale_y /= 0x100
                    # per-part transforms carry their position separately, so only the
                    # whole-cell transform (has_offset) consumes translate_x/translate_y
                    tx, ty = (translate_x, -translate_y) if has_offset else (0, 0)
                    self.matrix = [
                        scale_x * numpy.cos(theta), -numpy.sin(theta), tx,
                        numpy.sin(theta),  scale_y * numpy.cos(theta), ty,
                    ]
    
        class Renderer:
            def __init__(self, parent, input_data, game_id):
                input_data = BytesIO(input_data)

                # TODO: unknown
                pass_list_num, unk, unused = struct.unpack('<BbH', input_data.read(4))

                self.pass_list = []
                for i in range(pass_list_num):
                    pass_dict = {}
                    texture_sources, combiner_operands, combine_modes = struct.unpack('<3I', input_data.read(12))

                    pass_dict["rgb_source_0"]       = (texture_sources >>  0) & 0xF
                    pass_dict["rgb_source_1"]       = (texture_sources >>  4) & 0xF
                    pass_dict["rgb_source_2"]       = (texture_sources >>  8) & 0xF
                    pass_dict["alpha_source_0"]     = (texture_sources >> 16) & 0xF
                    pass_dict["alpha_source_1"]     = (texture_sources >> 20) & 0xF
                    pass_dict["alpha_source_2"]     = (texture_sources >> 24) & 0xF

                    pass_dict["rgb_operand_0"]      = (combiner_operands >>  0) & 0xF
                    pass_dict["rgb_operand_1"]      = (combiner_operands >>  4) & 0xF
                    pass_dict["rgb_operand_2"]      = (combiner_operands >>  8) & 0xF
                    pass_dict["alpha_operand_0"]    = (combiner_operands >> 12) & 0xF
                    pass_dict["alpha_operand_1"]    = (combiner_operands >> 16) & 0xF
                    pass_dict["alpha_operand_2"]    = (combiner_operands >> 20) & 0xF

                    pass_dict["rgb_combine_mode"]   = (combine_modes >>  0) & 0xF
                    pass_dict["alpha_combine_mode"] = (combine_modes >> 16) & 0xF

                    pass_dict["write_rgb_buffer"]   = 0
                    pass_dict["write_a_buffer"]     = 0

                    self.pass_list.append([pass_dict])

                input_data.seek(12 * (6 - pass_list_num), 1)

                for i in range(pass_list_num):
                    channel = struct.unpack(f'b', input_data.read(1))[0]
                    self.pass_list[i].append(channel)
                
                input_data.seek(6 - pass_list_num, 1)

                self.previous_buffer_init = int.from_bytes(input_data.read(1), 'little', signed = True)
                buffer_write_flags = int.from_bytes(input_data.read(1), 'little') # no clue if this is accurate but there has been nothing to prove otherwise so far lol
                for i in range(4):
                    current_flag = i
                    self.pass_list[i][0]["write_rgb_buffer"] = ((buffer_write_flags >> (current_flag + 0)) & 1)
                    self.pass_list[i][0]["write_a_buffer"]   = ((buffer_write_flags >> (current_flag + 4)) & 1)

                if unused != 0: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData.Renderer IS USED ACTUALLY: unused = {unused}")
    
        class NormalMap: # TODO: idek if this is accurate, but it's probably something to do with lighting
            def __init__(self, parent, input_data, game_id):
                self.input_data = input_data # unknown
        
        class SpriteSheetPart:
            def __init__(self, parent, input_data, game_id, index):
                input_data = BytesIO(input_data)

                segment_group_list_size = 0xC
                segment_list_size = 0x10
                segment_graph_list_size = 0x8

                # header
                segment_group_list_offset = 8
                segment_group_list_amt = int.from_bytes(input_data.read(2), 'little')
                segment_list_offset = segment_group_list_offset + (segment_group_list_size * segment_group_list_amt)
                segment_list_amt = int.from_bytes(input_data.read(2), 'little')
                segment_graph_list_offset = segment_list_offset + (segment_list_size * segment_list_amt)

                self.sheet_size = struct.unpack('<2H', input_data.read(4))

                # segment group
                input_data.seek(segment_group_list_offset + (segment_group_list_size * index))
                # TODO: unknowns
                first_segment, segment_amount, unk, self.x_offset, self.y_offset, unk = struct.unpack('<HHHhhH', input_data.read(segment_group_list_size))

                # segment
                self.segments = []
                for i in range(segment_amount):
                    segment_index = first_segment + i
                    input_data.seek(segment_list_offset + (segment_list_size * segment_index))

                    seg = self.Segment()

                    # segment properties
                    seg.set_properties(input_data.read(segment_list_size))

                    # segment graph
                    input_data.seek(segment_graph_list_offset + (segment_graph_list_size * seg.segment_graph_index))
                    seg.set_graph(input_data.read(segment_graph_list_size))

                    self.segments.append(seg)

            class Segment:
                def set_properties(self, input_data):
                    # TODO: unknowns
                    self.unk, self.unk, self.unk, self.transform, self.segment_graph_index, self.unk, self.unk, self.unk = struct.unpack('<HHHHHHHH', input_data)

                def set_graph(self, input_data):
                    self.graph_x, self.graph_y, self.graph_w, self.graph_h = struct.unpack('<4h', input_data)
    
        def get_data_at_offset(self, data_size, data_offset, index):
            self.input_data.seek(data_offset + (index * data_size))
    
            return(self.input_data.read(data_size))
    
        def get_anim_data(self, index_num):
            data_size = self.anim_size
            data_offset = self.anim_offset

            return self.Animation(self, self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)

        def get_frame_data(self, index_num):
            data_size = self.frame_size
            data_offset = self.frame_offset

            return self.AnimFrame(self, self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)

        def get_part_data(self, index_num):
            data_size = self.part_size
            data_offset = self.part_offset

            if not self.sprite_sheet_mode:
                return self.SpritePart(self, self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
            else:
                return self.SpriteSheetPart(self, self.get_data_at_offset(self.frame_offset - self.part_offset, data_offset, 0), self.game_id, index_num)
    
        def get_part_transform_data(self, index_num):
            data_size = self.part_trans_size
            data_offset = self.part_trans_offset
    
            return self.Transform(self, self.get_data_at_offset(data_size, data_offset, index_num), self.game_id, has_offset = False)
    
        def get_full_transform_data(self, index_num):
            data_size = self.full_trans_size
            data_offset = self.full_trans_offset
    
            return self.Transform(self, self.get_data_at_offset(data_size, data_offset, index_num), self.game_id, has_offset = True)
    
        def get_renderer_data(self, index_num):
            data_size = self.renderer_size
            data_offset = self.renderer_offset

            return self.Renderer(self, self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
        def get_normal_data(self, index_num):
            data_size = self.normal_size
            data_offset = self.normal_offset
    
            return self.NormalMap(self, self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
    class ColorData:
        def __init__(self, input_data):
            self.is_used = True
    
            self.animations = {}
            self.global_animations = {}
    
            if input_data == b'':
                self.is_used = False
                return
    
            self.input_data = BytesIO(input_data)
            # with open("test2.dat", "wb") as test:
            #     test.write(input_data)
            
            anim_num, anim_global_num = struct.unpack('<2H', self.input_data.read(0x4))
    
            for anim_index in range(anim_num + anim_global_num):
                self.input_data.seek(4 + (anim_index * 8))
    
                test = self.input_data.read(0x8)
                if test == bytes(8): continue
    
                seek_offset, total_length, layers, persistant = struct.unpack('<IHBB', test)
                self.input_data.seek(4 + (anim_index * 8) + seek_offset)
    
                full_anim = []
                for i in range(layers):
                    r_frame_num, g_frame_num, b_frame_num, a_frame_num, renderer_channel, anim_length = struct.unpack('<6H', self.input_data.read(0xC))
    
                    r_keyframes = [struct.unpack('<2H', self.input_data.read(0x4)) for i in range(r_frame_num)]
                    g_keyframes = [struct.unpack('<2H', self.input_data.read(0x4)) for i in range(g_frame_num)]
                    b_keyframes = [struct.unpack('<2H', self.input_data.read(0x4)) for i in range(b_frame_num)]
                    a_keyframes = [struct.unpack('<2H', self.input_data.read(0x4)) for i in range(a_frame_num)]

                    full_anim.append([(r_keyframes, g_keyframes, b_keyframes, a_keyframes), renderer_channel, persistant == 1, anim_length])
    
                if not anim_index >= anim_num:
                    self.animations[anim_index] = full_anim
                else:
                    self.global_animations[anim_index - anim_num] = full_anim
    
        def get_rgba(self, anim_index, global_anim_index, time_anim, time_color, anim_length):
            animation_set = self.animations.get(anim_index, None)
    
            return_set = []
            if animation_set != None:
            
                return_set = []
                for animation_full in animation_set:
                    length = animation_full[3]
                    if animation_full[2]:
                        time = time_anim % length
                    else:
                        time = time_anim % anim_length

                    animation = animation_full[0]
                    self.return_color = []
                    for keyframes in animation:
                        if keyframes == []:
                            self.return_color.append(None)
                        else:
                            self.return_color.append(numpy.interp(time, [key[1] for key in keyframes], [key[0] for key in keyframes]))
                    return_set.append([self.return_color, animation_full[1]])
            
            if global_anim_index is None:
                return return_set
            
            if not isinstance(global_anim_index, list):
                global_anim_index = [global_anim_index]
    
            for global_index in global_anim_index:
                animation_set = self.global_animations.get(global_index, None)
                if animation_set != None:
                
                    for animation_full in animation_set:
                        length = animation_full[3]
                        if animation_full[2]:
                            time = time_color % length
                        else:
                            time = time_anim % anim_length

                        animation = animation_full[0]
                        self.return_color = []
                        for keyframes in animation:
                            if keyframes == []:
                                self.return_color.append(None)
                            else:
                                self.return_color.append(numpy.interp(time, [key[1] for key in keyframes], [key[0] for key in keyframes]))
                        return_set.append([self.return_color, animation_full[1]])
            
            return return_set
    
    class PaletteData:
        def __init__(self, input_data, input_anim_data):
            self.palette = [0x0000] * 256
            self.input_data = BytesIO(input_data)
            self.input_anim_data = BytesIO(input_anim_data)

            palette_colors = struct.unpack(f'<{len(input_data) // 2}H', self.input_data.read())
            self.palette_size = len(palette_colors)
            self.palette[:len(palette_colors)] = palette_colors

            self.anim_data = palette_anim.parse(input_anim_data)

        def get_palette(self, timer, strict = False):
            frame_palette = self.palette
            slot = palette_anim.resolve(self.anim_data)
            if slot is not None:
                frame_palette = palette_anim.apply(frame_palette, self.anim_data['slots'][slot], timer, self.palette_size)

            palette = []
            if strict:
                palette_size = self.palette_size
            else:
                palette_size = 256

            for i in range(palette_size):
                color = frame_palette[i]
                out_color = []
                for x in range(3):
                    x = color >> (x * 5) & 0x1F       # 5 bit color
                    x = (x << 1) + min(x, 1)              # 6 bit color
                    out_color.append((x << 2) | (x >> 4)) # 8 bit color
                palette.append(out_color)
            return palette