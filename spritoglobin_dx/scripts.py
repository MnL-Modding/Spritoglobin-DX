import struct

import cv2
import numpy


SWIZZLE_TABLE = numpy.array([
    0x00, 0x01, 0x04, 0x05, 0x10, 0x11, 0x14, 0x15,
    0x02, 0x03, 0x06, 0x07, 0x12, 0x13, 0x16, 0x17,
    0x08, 0x09, 0x0C, 0x0D, 0x18, 0x19, 0x1C, 0x1D,
    0x0A, 0x0B, 0x0E, 0x0F, 0x1A, 0x1B, 0x1E, 0x1F,
    0x20, 0x21, 0x24, 0x25, 0x30, 0x31, 0x34, 0x35,
    0x22, 0x23, 0x26, 0x27, 0x32, 0x33, 0x36, 0x37,
    0x28, 0x29, 0x2C, 0x2D, 0x38, 0x39, 0x3C, 0x3D,
    0x2A, 0x2B, 0x2E, 0x2F, 0x3A, 0x3B, 0x3E, 0x3F,
], dtype = numpy.uint8)

SIZING_TABLE = [[(8, 8), (16, 16), (32, 32), (64, 64)], [(16, 8), (32, 8), (32, 16), (64, 32)], [(8, 16), (8, 32), (16, 32), (32, 64)]]


def get_sprite_graphic(obj_anim_data, graph_file, current_anim_index, color_anim_index, current_frame_index, current_time_anim, current_time_color, color_data, separate = False):
    anim_data = obj_anim_data.get_anim_data(current_anim_index)
    frame_data = obj_anim_data.get_frame_data(anim_data.first_frame + current_frame_index)

    matrix = None
    if frame_data.transform != 0:
        transform_data = obj_anim_data.get_transform_data(frame_data.transform - 1)
        matrix = list(transform_data.matrix)
        if frame_data.invert_matrix_rotation is None:
            invert_matrix = matrix[0] < 0 and not matrix[4] < 0 # TODO: idk how paper jam does matrix inversion
        else:
            invert_matrix = frame_data.invert_matrix_rotation == 1

        if invert_matrix:
            matrix[1], matrix[3] = -matrix[1], -matrix[3]

    # using the bounding box to display stuff *probably* isn't a great way to go about this
    # especially since these are 3D graphics and are likely unaffected by the bounding box?
    # i'm not sure, but i'll just keep it as a thing you can view in the main window rather than using it here
    full_bounding_box = None # anim_data.bounding_box
    if full_bounding_box is None:
        min_x, max_x, min_y, max_y = get_sprite_part_set_bounding_box(
            obj_anim_data      = obj_anim_data,
            first_part         = frame_data.first_part,
            total_parts        = frame_data.total_parts,
            given_bounding_box = None,
        )
        
        if matrix is not None:
            corners = [
                (min_x, min_y),
                (max_x, min_y),
                (min_x, max_y),
                (max_x, max_y)
            ]

            trans_x, trans_y = [], []
            for x, y in corners:
                # have to invert stuff manually here since +Y is up for bounding boxes but down for matrices
                new_x =  matrix[0] * x - matrix[1] * y + matrix[2]
                new_y = -matrix[3] * x + matrix[4] * y - matrix[5]
                trans_x.append(new_x)
                trans_y.append(new_y)

            full_bounding_box = (
                numpy.floor(min(trans_x)).astype(int),
                numpy.ceil(max(trans_x)).astype(int),
                numpy.floor(min(trans_y)).astype(int),
                numpy.ceil(max(trans_y)).astype(int),
            )
        else:
            full_bounding_box = min_x, max_x, min_y, max_y
    
    data = get_sprite_part_set_graphic(
        obj_anim_data          = obj_anim_data,
        graph_file             = graph_file,
        first_part             = frame_data.first_part,
        total_parts            = frame_data.total_parts,
        separate               = separate,
        matrix                 = matrix,
        given_bounding_box     = full_bounding_box,
        color_data             = color_data,
        current_anim_index     = current_anim_index,
        color_anim_index       = color_anim_index,
        current_time_anim      = current_time_anim,
        current_time_color     = current_time_color,
    )

    if separate:
        return data
    else:
        img, (graph_w, graph_h), (offset_x, offset_y) = data

    if img is None: return None, (0, 0), (0, 0)
    img = numpy.array(bytearray(img)).reshape(graph_h, graph_w, 4)

    bounding_box = [
        -offset_x,           # left
        -offset_x + graph_w, # right
         offset_y - graph_h, # down
         offset_y,           # up
    ]

    y = bounding_box[3] - full_bounding_box[3]
    x = full_bounding_box[0] - bounding_box[0]
    w = -full_bounding_box[0] + full_bounding_box[1]
    h = -full_bounding_box[2] + full_bounding_box[3]

    new_img = numpy.array(bytearray(img)).reshape(graph_h, graph_w, 4)
    img = new_img[y:y+h, x:x+w]
    img = img.tobytes()

    graph_w, graph_h = w, h
    offset_x -= x
    offset_y -= y

    return img, (graph_w, graph_h), (offset_x, offset_y)

def get_sprite_part_set_bounding_box(obj_anim_data, first_part, total_parts, given_bounding_box = None):
    min_x, max_x, min_y, max_y = 0, 0, 0, 0
    for i in range(total_parts):
        part_data = obj_anim_data.get_part_data(first_part + i)

        part_size = (part_data.oam_data) & 0b11
        part_shape = (part_data.oam_data >> 2) & 0b11
        w, h = SIZING_TABLE[part_shape][part_size]

        part_min_x = part_data.x_offset - (w // 2)
        part_max_x = part_data.x_offset + (w // 2)
        part_min_y = part_data.y_offset - (h // 2)
        part_max_y = part_data.y_offset + (h // 2)

        min_x, max_x = min(min_x, part_min_x), max(max_x, part_max_x)
        min_y, max_y = min(min_y, part_min_y), max(max_y, part_max_y)
    
    if given_bounding_box is not None:
        min_x, max_x, min_y, max_y = [
            min(min_x, given_bounding_box[0]),
            max(max_x, given_bounding_box[1]),
            min(min_y, given_bounding_box[2]),
            max(max_y, given_bounding_box[3]),
        ]
    
    return min_x, max_x, min_y, max_y

def get_sprite_part_set_graphic(obj_anim_data, graph_file, first_part, total_parts, separate = False, matrix = None, given_bounding_box = None, color_data = None, current_anim_index = None, color_anim_index = None, current_time_anim = None, current_time_color = None, highlighted_part = None):
    min_x, max_x, min_y, max_y = get_sprite_part_set_bounding_box(
        obj_anim_data      = obj_anim_data,
        first_part         = first_part,
        total_parts        = total_parts,
        given_bounding_box = given_bounding_box,
    )

    graph_w, graph_h = max_x - min_x, max_y - min_y

    if (graph_w < 1 or graph_h < 1) and not separate:
        return None, (0, 0), (0, 0)
    
    img = numpy.zeros((graph_h, graph_w, 4), dtype=numpy.uint8)

    offset_x, offset_y, = -min_x, max_y

    sprite_part_list = []
    for i in reversed(range(total_parts)):
        part_data = obj_anim_data.get_part_data(first_part + i)

        if obj_anim_data.renderer_num > 0:
            renderer_data = obj_anim_data.get_renderer_data(part_data.renderer)
        else:
            renderer_data = None

        alpha_divisor = None
        if highlighted_part is not None and highlighted_part != i:
            alpha_divisor = 3
        
        tile, tile_size = draw_part(
            part_data     = part_data,
            graph_file    = graph_file,
            obj_anim_data = obj_anim_data,
            alpha_divisor = alpha_divisor,
        )

        if color_data is not None and renderer_data is not None:
            anim_data = obj_anim_data.get_anim_data(current_anim_index)

            tile = apply_sprite_color(
                img                 = tile,
                obj_anim_data       = obj_anim_data,
                color_data          = color_data,
                renderer_data       = renderer_data,
                current_anim_index  = current_anim_index,
                global_anim_index   = color_anim_index,
                current_time_anim   = current_time_anim,
                current_time_color  = current_time_color,
                current_anim_length = anim_data.anim_length
            )

        x = offset_x - (tile_size[0] // 2) + part_data.x_offset
        y = offset_y - (tile_size[1] // 2) - part_data.y_offset

        w = tile_size[0]
        h = tile_size[1]

        if separate:
            sprite_part_list.append([tile.flatten(), (w, h), (part_data.x_offset, part_data.y_offset), matrix])
            continue

        target_area = img[y:y+h, x:x+w].astype(numpy.float32)
        tile = tile.astype(numpy.float32)

        source_alpha = tile[..., 3:4] / 255.0
        dest_alpha = target_area[..., 3:4] / 255.0
        
        alpha = source_alpha + dest_alpha * (1.0 - source_alpha)
        # this used to be the method of preventing edges from looking bad, but as it turns out
        # not every sprite part expands its color edges, and the ones that don't just look bad
        is_dest_transparent = False # dest_alpha < 0.001
        target_area[..., :3] = numpy.where(is_dest_transparent, tile[..., :3], target_area[..., :3])

        rgb = (tile[..., :3] * source_alpha + target_area[..., :3] * dest_alpha * (1.0 - source_alpha)) / numpy.maximum(alpha, 0.001)
        rgb = numpy.where(alpha < 0.001, tile[..., :3], rgb)
        
        img[y:y+h, x:x+w, :3] = numpy.clip(rgb, 0, 255).astype(numpy.uint8)
        img[y:y+h, x:x+w, 3] = numpy.clip(alpha * 255, 0, 255).astype(numpy.uint8).reshape(tile_size[1], tile_size[0])

    if separate:
        return sprite_part_list
        
    if matrix is not None:
        # this is the new method of preventing edges from looking bad
        # it's a little slow but it actually looks good now
        _, mask_orig = cv2.threshold(img[..., 3], 1, 255, cv2.THRESH_BINARY)
        mask_exp = cv2.dilate(img[..., 3], numpy.ones((5, 5), numpy.uint8), iterations = 2)

        rgb = cv2.inpaint(img[..., :3], cv2.subtract(mask_exp, mask_orig), inpaintRadius = 1, flags = cv2.INPAINT_TELEA)

        img[..., :3] = rgb

        img = transform_image(
            img =    img,
            matrix = matrix,
            center = (offset_x, offset_y),
            size =   (graph_w, graph_h),
        )
    
    return img.tobytes(), (graph_w, graph_h), (offset_x, offset_y)

def draw_part(part_data, graph_file, obj_anim_data, alpha_divisor = None, ignore_flips = False):
    part_size = (part_data.oam_data) & 0b11
    part_shape = (part_data.oam_data >> 2) & 0b11
    img_width, img_height = SIZING_TABLE[part_shape][part_size]
    color_mode = obj_anim_data.color_mode

    tile_amt = (img_width * img_height) // 64
    tile_offsets = numpy.arange(tile_amt)[:, None] * 64
    swizzle = (tile_offsets + SWIZZLE_TABLE).flatten()
    
    start = 128 * part_data.graphics_buffer_offset
    size = ((img_width * img_height) * color_mode[1]) // 8
    raw = numpy.frombuffer(graph_file[start:start + size], dtype = numpy.uint8)

    # for more info:
    # https://problemkaputt.de/gbatek-3ds-gpu-texture-formats.htm

    etc1 = False
    match color_mode[0]:
        case "RGBA8888":
            raw_pixel = raw.view(numpy.uint32)[swizzle]
            r = (raw_pixel >> 24) & 0xFF
            g = (raw_pixel >> 16) & 0xFF
            b = (raw_pixel >>  8) & 0xFF
            a = (raw_pixel >>  0) & 0xFF
        case "RGB888":
            raw_pixel = raw.view(numpy.uint8).reshape(-1, 3)[swizzle]
            r = raw_pixel[:, 0]
            g = raw_pixel[:, 1]
            b = raw_pixel[:, 2]
            a = raw_pixel[:, 0] | 0xFF
            pass
        case "RGBA5551":
            raw_pixel = raw.view(numpy.uint16)[swizzle]
            r = ((raw_pixel >> 11) & 0x1F) << 3 | ((raw_pixel >> 11) & 0x1F) >> 2
            g = ((raw_pixel >>  6) & 0x1F) << 3 | ((raw_pixel >>  6) & 0x1F) >> 2
            b = ((raw_pixel >>  1) & 0x1F) << 3 | ((raw_pixel >>  1) & 0x1F) >> 2
            a = ((raw_pixel >>  0) & 0x01) * 0xFF
        case "RGB565":
            raw_pixel = raw.view(numpy.uint16)[swizzle]
            r = ((raw_pixel >> 11) & 0x1F) << 3 | ((raw_pixel >> 11) & 0x1F) >> 2
            g = ((raw_pixel >>  5) & 0x3F) << 2 | ((raw_pixel >>  5) & 0x3F) >> 4
            b = ((raw_pixel >>  0) & 0x1F) << 3 | ((raw_pixel >>  0) & 0x1F) >> 2
            a = (raw_pixel & 0xFF) | 0xFF
        case "RGBA4444":
            raw_pixel = raw.view(numpy.uint16)[swizzle]
            r = ((raw_pixel >> 12) & 0x0F) << 4 | ((raw_pixel >> 12) & 0x0F)
            g = ((raw_pixel >>  8) & 0x0F) << 4 | ((raw_pixel >>  8) & 0x0F)
            b = ((raw_pixel >>  4) & 0x0F) << 4 | ((raw_pixel >>  4) & 0x0F)
            a = ((raw_pixel >>  0) & 0x0F) << 4 | ((raw_pixel >>  0) & 0x0F)
        case "LA88":
            raw_pixel = raw.view(numpy.uint16)[swizzle]
            r = (raw_pixel >>  8) & 0xFF
            g = (raw_pixel >>  8) & 0xFF
            b = (raw_pixel >>  8) & 0xFF
            a = (raw_pixel >>  0) & 0xFF
        case "HILO88":
            raw_pixel = raw.view(numpy.uint16)[swizzle]
            r = (raw_pixel >>  8) & 0xFF
            g = (raw_pixel >>  0) & 0xFF
            b = (raw_pixel & 0) + 0x00
            a = (raw_pixel & 0xFF) | 0xFF
        case "L8":
            raw_pixel = raw.view(numpy.uint8)[swizzle]
            r = raw_pixel
            g = raw_pixel
            b = raw_pixel
            a = raw_pixel | 0xFF
        case "A8":
            raw_pixel = raw.view(numpy.uint8)[swizzle]
            r = raw_pixel & 0x00
            g = raw_pixel & 0x00
            b = raw_pixel & 0x00
            a = raw_pixel
        case "LA44":
            raw_pixel = raw.view(numpy.uint8)[swizzle]
            r = ((raw_pixel >>  4) & 0x0F) << 4 | ((raw_pixel >>  4) & 0x0F)
            g = ((raw_pixel >>  4) & 0x0F) << 4 | ((raw_pixel >>  4) & 0x0F)
            b = ((raw_pixel >>  4) & 0x0F) << 4 | ((raw_pixel >>  4) & 0x0F)
            a = ((raw_pixel >>  0) & 0x0F) << 4 | ((raw_pixel >>  0) & 0x0F)
        case "L4":
            raw = raw.view(numpy.uint8)
            pixels = numpy.empty(raw.size * 2, dtype=numpy.uint8)
            pixels[0::2] = raw & 0x0F
            pixels[1::2] = raw >> 4
            raw_pixel = pixels[swizzle]
            r = raw_pixel << 4 | raw_pixel & 0x0F
            g = raw_pixel << 4 | raw_pixel & 0x0F
            b = raw_pixel << 4 | raw_pixel & 0x0F
            a = raw_pixel | 0xFF
        case "A4":
            raw = raw.view(numpy.uint8)
            pixels = numpy.empty(raw.size * 2, dtype=numpy.uint8)
            pixels[0::2] = raw & 0x0F
            pixels[1::2] = raw >> 4
            raw_pixel = pixels[swizzle]
            r = raw_pixel & 0x00
            g = raw_pixel & 0x00
            b = raw_pixel & 0x00
            a = raw_pixel << 4 | raw_pixel & 0x0F
        case "ETC1":
            etc1 = True
            color_block = (raw.view(numpy.uint64)[0::1]).reshape(-1, 4)

            pixels = etc1_decompress(color_block)
        case "ETC1A4":
            etc1 = True
            alpha_block = (raw.view(numpy.uint64)[0::2]).reshape(-1, 4)
            color_block = (raw.view(numpy.uint64)[1::2]).reshape(-1, 4)

            pixels = etc1_decompress(color_block, alpha_block)
    
    tiles_x, tiles_y = img_width // 8, img_height // 8

    if not etc1:
        pixels = numpy.stack([r, g, b, a], axis=-1).astype(numpy.uint8)
    
    if alpha_divisor is not None:
        pixels[..., 3] //= alpha_divisor
    
    out = pixels.reshape(tiles_y, tiles_x, 8, 8, 4).transpose(0, 2, 1, 3, 4)
    out = out.reshape(img_height, img_width, 4)

    if not ignore_flips:
        if part_data.oam_data & 0x100 != 0:
            out = cv2.flip(out, 1)
        if part_data.oam_data & 0x200 != 0:
            out = cv2.flip(out, 0)
    
    return out, (img_width, img_height)

def apply_sprite_color(img, obj_anim_data, color_data, renderer_data, current_anim_index, global_anim_index, current_time_anim, current_time_color, current_anim_length):
    anim_set = color_data.get_rgba(
        anim_index        = current_anim_index,
        global_anim_index = global_anim_index,
        time_anim         = current_time_anim,
        time_color        = current_time_color,
        anim_length       = current_anim_length,
    )

    fragment_light = [ # TODO: expose this to the user
        [255, 255, 255, 255], # shadow
        [  0,   0,   0, 255], # light
    ]

    anim_set.append([[0, 0, 0, 0], renderer_data.default_envelope])

    for color_mod, renderer_channel in anim_set:
        img_split = cv2.split(img)
        img_split_out = []
        for channel in range(4):
            pass_dict = None

            if renderer_channel in renderer_data.listening_channels:
                pass_dict = renderer_data.pass_list[renderer_data.listening_channels.index(renderer_channel)]

            channel_key = ["rgb", "rgb", "rgb", "alpha"][channel]

            if color_mod[channel] is None or pass_dict is None:
                img_split_out.append(img_split[channel])
                continue
            
            # for more info:
            # https://problemkaputt.de/gbatek-3ds-gpu-internal-registers-texturing-registers-environment.htm

            sources = [0, 0, 0]
            last_source = 3

            for i in range(3):
                current_source = pass_dict[f"{channel_key}_source_{i}"]
                if current_source == 0xF:
                    current_source = last_source
                
                last_source = current_source
                
                match current_source: # TODO: add the rest of these
                    case 0x1:
                        source = fragment_light[0]
                    case 0x2:
                        source = fragment_light[1]
                    case 0x3:
                        source = img_split
                    case 0xD:
                        source = 0
                    case 0xE:
                        source = color_mod
                    case _:
                        print("FUCK")
            
                match pass_dict[f"{channel_key}_operand_{i}"]:
                    case 0x0:
                        sources[i] = source[channel]
                    case 0x1:
                        sources[i] = 1 - source[channel]
                    case 0x2:
                        sources[i] = source[3]
                    case 0x3:
                        sources[i] = 1 - source[3]
                    case _:
                        print("FUCK")
                    
                if isinstance(sources[i], int):
                    sources[i] = numpy.full(len(img_split[channel].flatten()), sources[i]).reshape(img_split[channel].shape)
                
                sources[i] = sources[i].astype(float) / 255.0

            match pass_dict[f"{channel_key}_combine_mode"]: # TODO: add the rest of these
                case 0x0:
                    img_channel[:] = sources[0]
                case 0x1:
                    img_channel = cv2.multiply(
                        sources[0],
                        sources[1])
                case 0x2:
                    img_channel = cv2.add(
                        sources[0],
                        sources[1])
                case 0x8:
                    img_channel = cv2.multiply(
                        sources[0],
                        sources[1])
                    img_channel = cv2.add(
                        img_channel,
                        sources[2])
                case 0x9:
                    img_channel = cv2.add(
                        sources[0],
                        sources[1])
                    img_channel = cv2.multiply(
                        img_channel,
                        sources[2])
            
            img_channel = numpy.clip(img_channel, 0, 1) * 255
            img_split_out.append(numpy.array(img_channel).clip(0, 255).astype(numpy.uint8))

        img = cv2.merge(img_split_out)
    
    return img

def transform_image(img, matrix, center, size):
    M = numpy.eye(3, dtype=numpy.float32)
    M[0, 0:3] = matrix[0:3]
    M[1, 0:3] = matrix[3:6]

    center = (center[0] - 0.5, center[1] - 0.5)

    M[0, 2] += (1 - M[0, 0]) * center[0] - M[0, 1] * center[1]
    M[1, 2] += (1 - M[1, 1]) * center[1] - M[1, 0] * center[0]

    filtering = cv2.INTER_CUBIC
    img = cv2.warpAffine(img, M[:2], size, flags = filtering, borderMode = cv2.BORDER_CONSTANT, borderValue = (0, 0, 0, 0))

    return img


def create_transform_demo(scale, checker_amt, colors, matrix, inverted):
    img = numpy.zeros([4, 4, 4], dtype = numpy.float64)

    if inverted:
        matrix[1], matrix[3] = -matrix[1], -matrix[3]

    for i in range(4):
        off_y = i // 2
        off_x = i % 2
        
        img[off_y * 2:(off_y + 1) * 2, off_x * 2:(off_x + 1) * 2, :3] = colors[i][:3]
        img[1 + off_y, 1 + off_x, 3] = 255
    
    img = cv2.resize(img, None, fx = checker_amt, fy = checker_amt, interpolation = cv2.INTER_NEAREST)

    grid = (numpy.indices((checker_amt * 4, checker_amt * 4)).sum(axis = 0) % 2).astype(bool)
    img[grid, :3] *= [0.7, 0.9, 1.0]

    matrix[2], matrix[5] = 0, 0
    img = cv2.resize(img.astype(numpy.uint8), None, fx = scale, fy = scale, interpolation = cv2.INTER_NEAREST)

    center = [checker_amt * 2 * scale] * 2
    size = [checker_amt * 4 * scale] * 2
    img = transform_image(
        img =    img,
        matrix = matrix,
        center = center,
        size =   size,
    )
    
    return img, size



ETC1_TABLE = numpy.array([
    [ 2,   8],
    [ 5,  17],
    [ 9,  29],
    [13,  42],
    [18,  60],
    [24,  80],
    [33, 106],
    [47, 183],
], dtype = numpy.int16)


def etc1_decompress(color_block, alpha_block=None):
    num_tiles = color_block.shape[0]
    blocks = color_block.flatten().view(numpy.uint8).reshape(-1, 8)
    blocks_amt = blocks.shape[0]

    lsb_table = blocks[:, 0:2]
    msb_table = blocks[:, 2:4]
    control_byte = blocks[:, 4]
    color_data = blocks[:, 5:8].astype(numpy.int16)

    lsb_bits = numpy.unpackbits(lsb_table, axis=1, bitorder='little').reshape(blocks_amt, 16)
    msb_bits = numpy.unpackbits(msb_table, axis=1, bitorder='little').reshape(blocks_amt, 16)
    
    diff_bit = (control_byte & 0b10) != 0
    flip_bit = (control_byte & 0b01) != 0
    table_idx1 = (control_byte >> 5) & 0x7
    table_idx2 = (control_byte >> 2) & 0x7
    

    # individual mode
    r1_i = (color_data[:, 2] & 0xF0) | ((color_data[:, 2] & 0xF0) >> 4)
    r2_i = ((color_data[:, 2] & 0x0F) << 4) | (color_data[:, 2] & 0x0F)
    g1_i = (color_data[:, 1] & 0xF0) | ((color_data[:, 1] & 0xF0) >> 4)
    g2_i = ((color_data[:, 1] & 0x0F) << 4) | (color_data[:, 1] & 0x0F)
    b1_i = (color_data[:, 0] & 0xF0) | ((color_data[:, 0] & 0xF0) >> 4)
    b2_i = ((color_data[:, 0] & 0x0F) << 4) | (color_data[:, 0] & 0x0F)


    # differential mode
    rb = color_data[:, 2] >> 3
    gb = color_data[:, 1] >> 3
    bb = color_data[:, 0] >> 3

    rd = (color_data[:, 2] & 0x7); rd = numpy.where(rd >= 4, rd - 8, rd)
    gd = (color_data[:, 1] & 0x7); gd = numpy.where(gd >= 4, gd - 8, gd)
    bd = (color_data[:, 0] & 0x7); bd = numpy.where(bd >= 4, bd - 8, bd)

    r2_raw = rb + rd
    g2_raw = gb + gd
    b2_raw = bb + bd

    r1_d = (rb << 3) | (rb >> 2)
    g1_d = (gb << 3) | (gb >> 2)
    b1_d = (bb << 3) | (bb >> 2)
    r2_d = (r2_raw << 3) | (r2_raw >> 2)
    g2_d = (g2_raw << 3) | (g2_raw >> 2)
    b2_d = (b2_raw << 3) | (b2_raw >> 2)


    r1 = numpy.where(diff_bit, r1_d, r1_i)
    g1 = numpy.where(diff_bit, g1_d, g1_i)
    b1 = numpy.where(diff_bit, b1_d, b1_i)
    r2 = numpy.where(diff_bit, r2_d, r2_i)
    g2 = numpy.where(diff_bit, g2_d, g2_i)
    b2 = numpy.where(diff_bit, b2_d, b2_i)

    pixel_index = numpy.arange(16)
    mask_flip0 = (pixel_index < 8)
    mask_flip1 = ((pixel_index % 4) < 2)
    
    is_subblock_0 = numpy.where(flip_bit[:, None], mask_flip1, mask_flip0)
    etc1_table_index = numpy.where(is_subblock_0, table_idx1[:, None], table_idx2[:, None])
    
    raw_mod = ETC1_TABLE[etc1_table_index, lsb_bits]
    modifiers = numpy.where(msb_bits == 1, -raw_mod, raw_mod)

    base_r = numpy.where(is_subblock_0, r1[:, None], r2[:, None])
    base_g = numpy.where(is_subblock_0, g1[:, None], g2[:, None])
    base_b = numpy.where(is_subblock_0, b1[:, None], b2[:, None])
    r = numpy.clip(base_r + modifiers, 0, 255).astype(numpy.uint8)
    g = numpy.clip(base_g + modifiers, 0, 255).astype(numpy.uint8)
    b = numpy.clip(base_b + modifiers, 0, 255).astype(numpy.uint8)


    if alpha_block is not None:
        a_data = alpha_block.flatten().view(numpy.uint8).reshape(-1, 8)
        alpha = a_data & 0x0F | a_data << 4, a_data & 0xF0 | a_data >> 4
        a = numpy.stack(alpha, axis=2).reshape(blocks_amt, 16)
    else:
        a = numpy.full((blocks_amt, 16), 255, dtype=numpy.uint8)
    

    pixels = numpy.stack([r, g, b, a], axis=-1)
    pixels = pixels.reshape(num_tiles, 2, 2, 4, 4, 4)
    pixels = pixels.transpose(0, 1, 4, 2, 3, 5)
    pixels = pixels.reshape(num_tiles, 64, 4)

    return pixels