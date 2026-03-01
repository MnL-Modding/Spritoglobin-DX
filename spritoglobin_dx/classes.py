import struct
from io import BytesIO

import numpy

from spritoglobin_dx.constants import *
from spritoglobin_dx.scripts import SIZING_TABLE, get_sprite_graphic, get_sprite_part_set_graphic, draw_part


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
        self.data_files = {"": self.DataFile("", None)}
        self.cached_object = self.ObjectCache(None)

        try:
            bg4_extract, self.bg4_version, self.valid_entries, self.invalid_entries = self.bg4_extract(input_data)

            for name in bg4_extract:
                data = bg4_extract[name]

                if name != "_CA_INFO_":
                    self.data_files[name] = self.DataFile(name, data)
                    continue

                cellanim_info = self.DataFile(name, data)

                cellanim_extract, self.bg4_ca_version, self.valid_ca_entries, self.invalid_ca_entries = self.bg4_extract(cellanim_info.blz77_decompress_data())
                for name in cellanim_extract:
                    self.cellanim_files[name] = self.CellAnimFile(name, cellanim_extract[name])

            if game_id is None:
                for game_key in GAME_IDS_THAT_USE_BG4:
                    tests_completed = True
                    for file in self.cellanim_files:
                        test = self.AnimData(self.data_files[self.cellanim_files[file].anim_file].blz77_decompress_data(), game_key, test = True)
                        test_value = test.anim_offset + (test.anim_num * test.anim_size)
                        test_conditional = test_value == test.frame_offset
                        if not test_conditional:
                            tests_completed = False
                            break
                    if tests_completed: game_id = game_key

            self.game_id = game_id

        except ValueError as e:
            # no BG4 magic number, report error 102 ("Bad Archive")
            # implementing pre-PJ games may deprecate this specific context for this error
            raise InvalidObjectFileError(102)
        
        if self.cellanim_files == {}:
            # no _CA_INFO_, report error 101 ("No _CA_INFO_")
            raise InvalidObjectFileError(101)

        if self.game_id is None:
            # all tests failed, report error 100 ("Bad Game ID Tests")
            raise InvalidObjectFileError(100)
    
    def perform_tests(self):
        return

        for file in self.cellanim_files:
            test = self.AnimData(self.data_files[self.cellanim_files[file].anim_file].blz77_decompress_data(), self.game_id)
    
    def cache_object(self, object_name):
        if self.cached_object.name != object_name:
            current_obj_data = self.cellanim_files[object_name]

            self.cached_object.name          = object_name
            self.cached_object.obj_anim_data = self.AnimData(self.data_files[current_obj_data.anim_file].blz77_decompress_data(), self.game_id)
            self.cached_object.graph_file    = self.data_files[current_obj_data.graph_file].blz77_decompress_data()
            self.cached_object.color_data    = self.ColorData(self.data_files[current_obj_data.color_file].blz77_decompress_data())
    
    def get_file_properties(self):
        return {
            "game_id": self.game_id,
        }
    
    def get_object_properties(self, object_name):
        self.cache_object(object_name)

        obj_data = self.cached_object.obj_anim_data
        color_data = self.cached_object.color_data

        has_color_data = color_data.global_animations != {}

        return {
            "color_mode":       obj_data.color_mode,
            "animation_number": obj_data.anim_num,
            "bounding_box":     obj_data.bounding_box,
            "has_color_data":   has_color_data,
            "color_data":       color_data.global_animations,
        }
    
    def get_animation_properties(self, object_name, animation_index):
        self.cache_object(object_name)

        anim_data = self.cached_object.obj_anim_data.get_anim_data(animation_index)
        color_data = self.cached_object.color_data

        keyframe_list = [0]
        for i in range(anim_data.total_frames - 1):
            frame_data = self.cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
            keyframe_list.append(frame_data.anim_timer)
        
        has_color_data = animation_index in color_data.animations

        return {
            "first_frame":    anim_data.first_frame,
            "total_frames":   anim_data.total_frames,
            "length":         anim_data.anim_length,
            "keyframes":      keyframe_list,
            "bounding_box":   anim_data.bounding_box,
            "has_color_data": has_color_data,
            "color_data":     color_data.animations,
        }
    
    def get_frame_properties(self, object_name, animation_index = None, frame_index = None):
        self.cache_object(object_name)

        anim_data = self.cached_object.obj_anim_data.get_anim_data(animation_index)

        if frame_index is None:
            try:
                anim_data = self.cached_object.obj_anim_data.get_anim_data(animation_index)
                timer = self.animation_timer % anim_data.anim_length

                for i in range(anim_data.total_frames):
                    frame_data = self.cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + i)
                    if not timer >= frame_data.anim_timer:
                        frame_index = i
                        break
            except AttributeError:
                frame_index = 0
        
        if animation_index is None:
            frame_data = self.cached_object.obj_anim_data.get_frame_data(frame_index)
        else:
            frame_data = self.cached_object.obj_anim_data.get_frame_data(anim_data.first_frame + frame_index)

        if frame_data.transform != 0: transform_matrix = self.cached_object.obj_anim_data.get_transform_data(frame_data.transform - 1).matrix
        else: transform_matrix = []

        if transform_matrix != []:
            if frame_data.invert_matrix_rotation is None:
                invert_matrix = transform_matrix[0] < 0 and not transform_matrix[4] < 0 # TODO: idk how paper jam does matrix inversion
            else:
                invert_matrix = frame_data.invert_matrix_rotation == 1
        else:
            invert_matrix = False

        return {
            "first_part":         frame_data.first_part,
            "total_parts":        frame_data.total_parts,
            "keyframe_timer":     frame_data.anim_timer,
            "transform_index":    frame_data.transform - 1,
            "transform":          transform_matrix,
            "transform_inverted": invert_matrix,
        }
    
    def get_sprite_part_properties(self, object_name, sprite_part_index):
        self.cache_object(object_name)

        part_data = self.cached_object.obj_anim_data.get_part_data(sprite_part_index)
        
        part_size = (part_data.oam_data) & 0b11
        part_shape = (part_data.oam_data >> 2) & 0b11
        x_flip = part_data.oam_data & 0x100 != 0
        y_flip = part_data.oam_data & 0x200 != 0

        return {
            "oam_size":        part_size,
            "oam_shape":       part_shape,
            "horizontal_flip": x_flip,
            "vertical_flip":   y_flip,
            "size":            SIZING_TABLE[part_shape][part_size],
            "buffer_offset":   part_data.graphics_buffer_offset,
            "offset":          (part_data.x_offset, part_data.y_offset),
            "renderer_index":  part_data.renderer,
        }
    
    def get_sprite(self, object_name, animation_index, color_anim_index = None, frame_index = None):
        img, size, _ = self.get_sprite_with_offset(
            object_name      = object_name,
            animation_index  = animation_index,
            color_anim_index = color_anim_index,
            frame_index      = frame_index
        )

        return img, size
    
    def get_sprite_with_offset(self, object_name, animation_index, color_anim_index = None, frame_index = None):
        self.cache_object(object_name)
        
        obj_anim_data = self.cached_object.obj_anim_data
        graph_file    = self.cached_object.graph_file
        color_data    = self.cached_object.color_data

        if frame_index is None:
            try:
                anim_data = obj_anim_data.get_anim_data(animation_index)
                
                timer = self.animation_timer % anim_data.anim_length

                for i in range(anim_data.total_frames):
                    frame_data = obj_anim_data.get_frame_data(anim_data.first_frame + i)
                    if not timer >= frame_data.anim_timer:
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
            current_anim_index  = animation_index,
            color_anim_index    = color_anim_index,
            current_frame_index = frame_index,
            current_time_anim   = animation_timer,
            current_time_color  = color_timer,
            color_data          = color_data,
        )
    
    def get_sprite_part_set_with_offset(self, object_name, first_part, total_parts, highlighted_part = None):
        self.cache_object(object_name)
        
        obj_anim_data = self.cached_object.obj_anim_data
        graph_file    = self.cached_object.graph_file
        
        return get_sprite_part_set_graphic(
            obj_anim_data    = obj_anim_data,
            graph_file       = graph_file,
            first_part       = first_part,
            total_parts      = total_parts,
            highlighted_part = highlighted_part,
        )
    
    def get_sprite_part_graphic(self, object_name, sprite_part_index):
        self.cache_object(object_name)

        part_data = self.cached_object.obj_anim_data.get_part_data(sprite_part_index)
        graph_file    = self.cached_object.graph_file
        obj_anim_data = self.cached_object.obj_anim_data
        
        return draw_part(
            part_data     = part_data,
            graph_file    = graph_file,
            obj_anim_data = obj_anim_data,
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
        if animation_timer:
            self.animation_timer = time

        if color_timer:
            self.color_timer = time
    
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
    
    class ObjectCache:
        def __init__(self, name):
            self.name = name
        
    class CellAnimFile: # TODO: lots of unknowns here
        def __init__(self, name, input_data):
            data = BytesIO(input_data)
            self.name = name

            self.anim_file = self.get_string(data.read(4))
            self.graph_file = self.get_string(data.read(4))
            self.color_file = self.get_string(data.read(4))
            self.hitbox_file = self.get_string(data.read(4)) # TODO: figure out how this works

            self.input_data = input_data

            # more unknowns past here
        
        def get_string(self, input_data):
            string_end = input_data.find(0)
            return input_data[:string_end].decode("ascii")
        
    class DataFile:
        def __init__(self, name, input_data):
            self.name = name
            self.data = input_data
        
        def blz77_decompress_data(self): # stole this from danius
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

    class AnimData: # TODO: unknowns here
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
                    frame_offset, part_offset, unused_offset_0, trans_offset, renderer_offset, normal_offset, unused_offset_1 = struct.unpack('<7I', self.input_data.read(0x1C))

                    self.anim_size = 16
                    self.frame_size = 8
                    self.part_size = 16
                    self.trans_size = 20
                    self.renderer_size = 84

                    self.normal_size = 48
                    self.normal_offset = normal_offset

                    if unused_offset_1 != 0 and not test: print(f"THE 'unused_offset_1' VALUE IN CLASS ObjFile.AnimData IS USED ACTUALLY: unused_offset_1 = {unused_offset_1}")

                case "ML1R": # Superstar Saga DX --- added normal maps (or something lighting related)
                    self.anim_num, color_mode, self.renderer_num, unused, self.anim_file_length, self.graph_file_length = struct.unpack('<4B2I', self.input_data.read(0xC))
                    frame_offset, part_offset, unused_offset_0, trans_offset, renderer_offset, normal_offset = struct.unpack('<6I', self.input_data.read(0x18))

                    self.anim_size = 8
                    self.frame_size = 8
                    self.part_size = 16
                    self.trans_size = 20
                    self.renderer_size = 84

                    self.normal_size = 48
                    self.normal_offset = normal_offset

                case "ML5": # Paper Jam --- i haven't looked into it too hard but it looks like the format is literally exactly the same as DT lol
                    self.anim_num, color_mode, self.renderer_num, unused, self.anim_file_length, self.graph_file_length = struct.unpack('<4B2I', self.input_data.read(0xC))
                    frame_offset, part_offset, unused_offset_0, trans_offset, renderer_offset = struct.unpack('<5I', self.input_data.read(0x14))

                    self.anim_size = 8
                    self.frame_size = 8
                    self.part_size = 12
                    self.trans_size = 20
                    self.renderer_size = 84

            if unused != 0 and not test: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData IS USED ACTUALLY: unused = {unused}")
            if trans_offset - unused_offset_0 != 0 and not test: print(f"THE 'unused_offset_0' VALUE IN CLASS ObjFile.AnimData IS USED ACTUALLY: unused_offset_0 size = {trans_offset - unused_offset_0}")
    
            # buncha unknowns here
            self.input_data.seek(0x40, 1)

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


            anim_offset = self.input_data.tell()
    
            self.anim_offset = anim_offset
            self.frame_offset = frame_offset
            self.part_offset = part_offset # TODO: implement Sprite Sheet Mode when this value is 0
            # ???
            self.trans_offset = trans_offset
            self.renderer_offset = renderer_offset
    
        class Animation:
            def __init__(self, input_data, game_id):
                self.first_frame, self.total_frames, self.anim_length, unused = struct.unpack('<4H', input_data[:8])

                if game_id in GAME_IDS_THAT_USE_BOUNDING_BOXES:
                    self.bounding_box = struct.unpack('<4h', input_data[8:])
                else:
                    self.bounding_box = None

                if unused != 0: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData.Animation IS USED ACTUALLY: unused = {unused}")
    
        class AnimFrame:
            def __init__(self, input_data, game_id):
                self.first_part, self.total_parts, self.invert_matrix_rotation, self.anim_timer, self.transform = struct.unpack('<HBBHH', input_data)

                if game_id not in GAME_IDS_THAT_USE_MATRIX_INVERSION:
                    self.invert_matrix_rotation = None
    
        class SpritePart: # TODO: figure out what "horizontal_flip" actually does
            def __init__(self, input_data, game_id):
                self.oam_data, self.renderer, self.horizontal_flip, self.graphics_buffer_offset, self.x_offset, self.y_offset = struct.unpack('<HHhHhh', input_data[:12])
                
                if game_id in GAME_IDS_THAT_USE_NORMAL_MAPS:
                    self.normal_map, = struct.unpack('<I', input_data[12:])
    
        class Transform:
            def __init__(self, input_data, game_id):
                matrix = struct.unpack('<4f2h', input_data)
                self.matrix = [
                    matrix[0], matrix[2],  matrix[4],
                    matrix[1], matrix[3], -matrix[5],
                ]
    
        class Renderer:
            def __init__(self, input_data, game_id):
                input_data = BytesIO(input_data)

                pass_list_num, self.default_envelope, unused = struct.unpack('<BbH', input_data.read(4))

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
                    pass_dict["alpha_operand_0"]    = (combiner_operands >> 16) & 0xF
                    pass_dict["alpha_operand_1"]    = (combiner_operands >> 20) & 0xF
                    pass_dict["alpha_operand_2"]    = (combiner_operands >> 24) & 0xF

                    pass_dict["rgb_combine_mode"]   = (combine_modes >>  0) & 0xF
                    pass_dict["alpha_combine_mode"] = (combine_modes >> 16) & 0xF

                    self.pass_list.append(pass_dict)

                input_data.seek(12 * (6 - pass_list_num), 1)

                self.listening_channels = struct.unpack(f'<{pass_list_num}b', input_data.read(pass_list_num))

                if unused != 0: print(f"THE 'unused' VALUE IN CLASS ObjFile.AnimData.Renderer IS USED ACTUALLY: unused = {unused}")
    
        class NormalMap: # TODO: idek if this is accurate, but it's probably something to do with lighting
            def __init__(self, input_data, game_id):
                self.input_data = input_data # unknown
    
        def get_data_at_offset(self, data_size, data_offset, index):
            self.input_data.seek(data_offset + (index * data_size))
    
            return(self.input_data.read(data_size))
    
        def get_anim_data(self, index_num):
            data_size = self.anim_size
            data_offset = self.anim_offset
    
            return self.Animation(self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
        def get_frame_data(self, index_num):
            data_size = self.frame_size
            data_offset = self.frame_offset
    
            return self.AnimFrame(self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
        def get_part_data(self, index_num):
            data_size = self.part_size
            data_offset = self.part_offset
    
            return self.SpritePart(self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
        def get_transform_data(self, index_num):
            data_size = self.trans_size
            data_offset = self.trans_offset
    
            return self.Transform(self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
        def get_renderer_data(self, index_num):
            data_size = self.renderer_size
            data_offset = self.renderer_offset
    
            return self.Renderer(self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
        def get_normal_data(self, index_num):
            data_size = self.normal_size
            data_offset = self.normal_offset
    
            return self.NormalMap(self.get_data_at_offset(data_size, data_offset, index_num), self.game_id)
    
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