import numpy

import math


def render_object_scene(canvas_size, global_translation, global_rotation, global_scale, img_data):
    g_t = get_translation_matrix(*global_translation)
    g_r = get_rotation_matrix(*global_rotation)
    g_s = get_scale_matrix(*global_scale)

    global_matrix = g_t @ g_r @ g_s

    for parts_list, translation, rotation, scale in img_data:
        l_t = get_translation_matrix(*translation)
        l_r = get_rotation_matrix(*rotation)
        l_s = get_scale_matrix(*scale)

        local_matrix = l_t @ l_r @ l_s

        for graphics_buffer, size, offset, base_matrix in parts_list:
            a, b, x, c, d, y = base_matrix
            part_matrix = numpy.array([
                [a, b, 0,  (x + offset[0])],
                [c, d, 0, -(y + offset[1])],
                [0, 0, 1,  0],
                [0, 0, 0,  1],
            ])

            full_matrix = global_matrix @ local_matrix @ part_matrix


def get_translation_matrix(x, y, z):
    return numpy.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1],
    ])

def get_rotation_matrix(x, y, z):
    x, y, z = [math.radians(v) for v in (x, y, z)]

    r_x = numpy.array([
        [1, 0, 0, 0],
        [0, math.cos(x), -math.sin(x), 0],
        [0, math.sin(x),  math.cos(x), 0],
        [0, 0, 0, 1],
    ])

    r_y = numpy.array([
        [ math.cos(y), 0, math.sin(y), 0],
        [ 0, 1, 0, 0],
        [-math.sin(y), 0, math.cos(y), 0],
        [ 0, 0, 0, 1],
    ])

    r_z = numpy.array([
        [math.cos(z), -math.sin(z), 0, 0],
        [math.sin(z),  math.cos(z), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ])

    return r_x @ r_y @ r_z

def get_scale_matrix(x, y, z):
    return numpy.array([
        [x, 0, 0, 0],
        [0, y, 0, 0],
        [0, 0, z, 0],
        [0, 0, 0, 1],
    ])