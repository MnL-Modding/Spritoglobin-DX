import math
import struct

import moderngl
import numpy



class SpriteRenderer:
    def __init__(self, canvas_size, pretty = True, use_filtering = False, limit_resolution = False):
        self.framebuffer = None
        
        self.context = moderngl.create_context(standalone=True)
        self.context.gc_mode = "auto"
        self.context.enable(moderngl.BLEND)

        self.resize(canvas_size)

        self.set_program(
            pretty = pretty,
            use_filtering = use_filtering,
            limit_resolution = limit_resolution,
        )
        
    def set_program(self, pretty, use_filtering, limit_resolution):
        if use_filtering:
            self.filtering_mode = moderngl.LINEAR
        else:
            self.filtering_mode = moderngl.NEAREST
        
        main_passes = """
            for (int i = 0; i < 6; i++) {
                if (!passes[i].keep_going) break;

                if (i >= 2) saved_buffer = buffer_save[i - 2];
                else        saved_buffer = vec4(0.0);

                source_0_rgb = getSource(passes[i].rgb_source_0, out_tex, saved_buffer, current_coord, passes[i].const_color_index);
                source_1_rgb = getSource(passes[i].rgb_source_1, out_tex, saved_buffer, current_coord, passes[i].const_color_index);
                source_2_rgb = getSource(passes[i].rgb_source_2, out_tex, saved_buffer, current_coord, passes[i].const_color_index);
                source_0_a = getSource(passes[i].alpha_source_0, out_tex, saved_buffer, current_coord, passes[i].const_color_index);
                source_1_a = getSource(passes[i].alpha_source_1, out_tex, saved_buffer, current_coord, passes[i].const_color_index);
                source_2_a = getSource(passes[i].alpha_source_2, out_tex, saved_buffer, current_coord, passes[i].const_color_index);

                source_0_rgb = getOperandRgb(passes[i].rgb_operand_0, source_0_rgb);
                source_1_rgb = getOperandRgb(passes[i].rgb_operand_1, source_1_rgb);
                source_2_rgb = getOperandRgb(passes[i].rgb_operand_2, source_2_rgb);
                source_0_a = getOperandA(passes[i].alpha_operand_0, source_0_a);
                source_1_a = getOperandA(passes[i].alpha_operand_1, source_1_a);
                source_2_a = getOperandA(passes[i].alpha_operand_2, source_2_a);

                out_tex = getCombinedColor(passes[i].rgb_combine_mode, passes[i].alpha_combine_mode, source_0_rgb, source_0_a, source_1_rgb, source_1_a, source_2_rgb, source_2_a);

                if (i < 4) {
                    if (passes[i].write_rgb_buffer == 1) temp_buffer.rgb = out_tex.rgb;
                    if (passes[i].write_a_buffer   == 1) temp_buffer.a   = out_tex.a;

                    buffer_save[i] = temp_buffer;
                }
            }"""

        if pretty:
            main = """
                float blur_radius = 0.3;
                vec2 uv_per_screen_pixel = vec2(length(dFdx(v_texcoord)), length(dFdy(v_texcoord)));
                vec2 offset = uv_per_screen_pixel * blur_radius;

                vec4 total_color = vec4(0.0, 0.0, 0.0, 0.0);
                vec4 source_0_rgb;
                vec4 source_1_rgb;
                vec4 source_2_rgb;
                vec4 source_0_a;
                vec4 source_1_a;
                vec4 source_2_a;
                vec2 current_coord;

                float rgb_mix = 9.0;

                for (int x = -1; x <= 1; x += 1) {
                    for (int y = -1; y <= 1; y += 1) {
                        current_coord = v_texcoord + vec2(x, y) * offset;

                        bool invalid_pixel = false;

                        if (any(lessThan(current_coord, vec2(0.0)))) invalid_pixel = true;
                        if (any(greaterThan(current_coord, vec2(1.0)))) invalid_pixel = true;

                        if (invalid_pixel) {
                            rgb_mix -= 1.0;
                            continue;
                        }

                        out_tex = texture(u_texture_0, current_coord);
                        vec4 temp_buffer = vec4(0.0);
                        vec4 saved_buffer;

                        """ + main_passes + """
                        
                        total_color += out_tex;
                    }
                }

                f_color = total_color / rgb_mix;
                if (f_color.a <= 0.0) discard;
            """
        else:
            main = """
                out_tex = texture(u_texture_0, current_coord);
                vec4 temp_buffer = vec4(0.0);
                vec4 saved_buffer;

                """ + main_passes + """

                f_color = out_tex;
                if (f_color.a <= 0.0) discard;
            """
            
        self.program = self.context.program(
            vertex_shader="""
                #version 330
                uniform mat4 u_matrix;
                in vec2 in_vert;
                in vec2 in_texcoord;
                out vec2 v_texcoord;
                void main() {
                    v_texcoord = in_texcoord;
                    gl_Position = u_matrix * vec4(in_vert, 0.0, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                uniform vec4 u_primary_color;
                uniform vec4 u_light_0;
                uniform vec4 u_light_1;
                uniform sampler2D u_texture_0;
                uniform sampler2D u_texture_1;
                uniform sampler2D u_texture_2;
                uniform sampler2D u_texture_3;

                uniform vec4[16] u_globalPalette;

                vec4 out_tex;
                vec4[4] buffer_save = vec4[4](vec4(0.0), vec4(0.0), vec4(0.0), vec4(0.0));

                in vec2 v_texcoord;
                out vec4 f_color;

                struct Pass {
                    int rgb_source_0;
                    int rgb_source_1;
                    int rgb_source_2;
                    int alpha_source_0;
                    int alpha_source_1;
                    int alpha_source_2;
                    int rgb_operand_0;
                    int rgb_operand_1;
                    int rgb_operand_2;
                    int alpha_operand_0;
                    int alpha_operand_1;
                    int alpha_operand_2;
                    int rgb_combine_mode;
                    int alpha_combine_mode;
                    int write_rgb_buffer;
                    int write_a_buffer;
                    int const_color_index;
                    bool keep_going;
                    bool padding_12h;
                    bool padding_13h;
                };
                layout(std140) uniform PassBlock {
                    Pass passes[6];
                };

                vec4 getSource(int index, vec4 out_tex, vec4 saved_buffer, vec2 uv, int global_color_index) {
                    vec4 source_out = vec4(1.0, 0.0, 1.0, 0.5);

                    if      (index == 0)  source_out = u_primary_color;
                    else if (index == 1)  source_out = u_light_0;
                    else if (index == 2)  source_out = u_light_1;
                    else if (index == 3)  source_out = texture(u_texture_0, uv);
                    else if (index == 4)  source_out = texture(u_texture_1, uv);
                    else if (index == 5)  source_out = texture(u_texture_2, uv);
                    else if (index == 6)  source_out = texture(u_texture_3, uv);
                    else if (index == 13) source_out = saved_buffer;
                    else if (index == 14) source_out = u_globalPalette[global_color_index];
                    else if (index == 15) source_out = out_tex;

                    return source_out;
                }

                vec4 getOperandRgb(int rgb_index, vec4 input) {
                    vec4 operand_out = vec4(1.0, 0.0, 1.0, 0.5);

                    if      (rgb_index == 0)  operand_out = input;
                    else if (rgb_index == 1)  operand_out = 1.0 - input;
                    else if (rgb_index == 2)  operand_out = vec4(input.a);
                    else if (rgb_index == 3)  operand_out = vec4(1.0 - input.a);
                    else if (rgb_index == 4)  operand_out = vec4(input.r);
                    else if (rgb_index == 5)  operand_out = vec4(1.0 - input.r);
                    else if (rgb_index == 8)  operand_out = vec4(input.g);
                    else if (rgb_index == 9)  operand_out = vec4(1.0 - input.g);
                    else if (rgb_index == 12) operand_out = vec4(input.b);
                    else if (rgb_index == 13) operand_out = vec4(1.0 - input.b);

                    return operand_out;
                }

                vec4 getOperandA(int a_index, vec4 input) {
                    vec4 operand_out = vec4(1.0, 0.0, 1.0, 0.5);

                    if      (a_index == 0) operand_out = vec4(input.a);
                    else if (a_index == 1) operand_out = vec4(1.0 - input.a);
                    else if (a_index == 2) operand_out = vec4(input.r);
                    else if (a_index == 3) operand_out = vec4(1.0 - input.r);
                    else if (a_index == 4) operand_out = vec4(input.g);
                    else if (a_index == 5) operand_out = vec4(1.0 - input.g);
                    else if (a_index == 6) operand_out = vec4(input.b);
                    else if (a_index == 7) operand_out = vec4(1.0 - input.b);

                    return operand_out;
                }

                vec4 getCombinedColor(int rgb_index, int a_index, vec4 source_0_rgb, vec4 source_0_a, vec4 source_1_rgb, vec4 source_1_a, vec4 source_2_rgb, vec4 source_2_a) {
                    vec4 combineOut = vec4(1.0, 0.0, 1.0, 0.5);

                    if      (rgb_index == 0) combineOut.rgb = source_0_rgb.rgb;
                    else if (rgb_index == 1) combineOut.rgb = source_0_rgb.rgb * source_1_rgb.rgb;
                    else if (rgb_index == 2) combineOut.rgb = source_0_rgb.rgb + source_1_rgb.rgb;
                    else if (rgb_index == 3) combineOut.rgb = (source_0_rgb.rgb - 0.5) + (source_1_rgb.rgb - 0.5);
                    else if (rgb_index == 4) {
                        vec3 a = source_0_rgb.rgb;
                        vec3 b = source_1_rgb.rgb;
                        vec3 c = 1 - source_2_rgb.rgb;
                        combineOut.rgb = (1 - c) * a + c * b;
                    }
                    else if (rgb_index == 5) combineOut.rgb = source_0_rgb.rgb - source_1_rgb.rgb;
                    else if (rgb_index == 6) {
                        vec3 source_0_n = (source_0_rgb.rgb * 2.0) - 1.0;
                        vec3 source_1_n = (source_1_rgb.rgb * 2.0) - 1.0;
                        combineOut.rgb = vec3(dot(source_0_n, source_1_n));
                    }
                    else if (rgb_index == 7) {
                        vec4 source_0_n = (source_0_rgb * 2.0) - 1.0;
                        vec4 source_1_n = (source_1_rgb * 2.0) - 1.0;
                        combineOut.rgb = vec3(dot(source_0_n, source_1_n));
                    }
                    else if (rgb_index == 8) combineOut.rgb = (source_0_rgb.rgb * source_1_rgb.rgb) + source_2_rgb.rgb;
                    else if (rgb_index == 9) combineOut.rgb = (source_0_rgb.rgb + source_1_rgb.rgb) * source_2_rgb.rgb;

                    if      (a_index == 0) combineOut.a = source_0_a.a;
                    else if (a_index == 1) combineOut.a = source_0_a.a * source_1_a.a;
                    else if (a_index == 2) combineOut.a = source_0_a.a + source_1_a.a;
                    else if (a_index == 3) combineOut.a = (source_0_a.a - 0.5) + (source_1_a.a - 0.5);
                    else if (a_index == 4) {
                        float a = source_0_a.a;
                        float b = source_1_a.a;
                        float c = 1 - source_2_a.a;
                        combineOut.a = (1 - c) * a + c * b;
                    }
                    else if (a_index == 5) combineOut.a = source_0_a.a - source_1_a.a;
                    else if (a_index == 6) {
                        vec3 source_0_n = (source_0_a.rgb * 2.0) - 1.0;
                        vec3 source_1_n = (source_1_a.rgb * 2.0) - 1.0;
                        combineOut.a = dot(source_0_n, source_1_n);
                    }
                    else if (a_index == 7) {
                        vec4 source_0_n = (source_0_a * 2.0) - 1.0;
                        vec4 source_1_n = (source_1_a * 2.0) - 1.0;
                        combineOut.a = dot(source_0_n, source_1_n);
                    }
                    else if (a_index == 8) combineOut.a = (source_0_a.a * source_1_a.a) + source_2_a.a;
                    else if (a_index == 9) combineOut.a = (source_0_a.a + source_1_a.a) * source_2_a.a;

                    return combineOut;
                }

                void main() {""" + main + "}"
        )

        vertices = numpy.array([
            -0.5, -0.5, 0, 1,
             0.5, -0.5, 1, 1,
            -0.5,  0.5, 0, 0,
             0.5,  0.5, 1, 0,
        ], dtype='f4')

        self.vertex_buffer = self.context.buffer(vertices)
        self.vertex_array = self.context.simple_vertex_array(self.program, self.vertex_buffer, 'in_vert', 'in_texcoord')

    def get_projection_matrix(self):
        width, height = self.canvas_size
        l, r = 0, self.canvas_size[0]
        b, t = self.canvas_size[1], 0
        n, f = -100.0, 100.0
        
        return numpy.array([
            [2/(r-l), 0, 0, -(r+l)/(r-l)],
            [0, 2/(t-b), 0, -(t+b)/(t-b)],
            [0, 0, -2/(f-n), -(f+n)/(f-n)],
            [0, 0, 0, 1],
        ], dtype='f4')
    
    def resize(self, canvas_size):
        self.canvas_size = (canvas_size)

        if self.framebuffer:
            for attachment in self.framebuffer.color_attachments:
                attachment.release()
            if self.framebuffer.depth_attachment:
                self.framebuffer.depth_attachment.release()
            self.framebuffer.release()

        self.framebuffer = self.context.framebuffer(
            color_attachments=[self.context.texture(self.canvas_size, 4)],
            depth_attachment=self.context.depth_renderbuffer(self.canvas_size),
        )

        self.projection = self.get_projection_matrix()


    def render_object_scene(self, global_translation, global_rotation, global_scale, img_data):
        self.framebuffer.use()
        self.framebuffer.clear()

        g_s = self.get_scale_matrix(*global_scale)
        g_t = self.get_translation_matrix(*global_translation)
        g_r = self.get_rotation_matrix(*global_rotation)

        global_matrix = g_s @ g_t @ g_r
        
        global_palette = [value / 255 for color in img_data[1].values() for value in color]
        global_palette_bytes = struct.pack('64f', *global_palette)

        self.program['u_globalPalette'].write(global_palette_bytes)

        fragment_lighting = img_data[2]
        self.program['u_light_0'].value = fragment_lighting[0]
        self.program['u_light_1'].value = fragment_lighting[1]

        for real_draw in [False, True]:

            if not real_draw: self.context.blend_func = (moderngl.ONE, moderngl.ZERO, moderngl.ZERO, moderngl.ZERO)
            else:             self.context.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ONE_MINUS_DST_ALPHA, moderngl.ONE)


            for [parts_list, translation, rotation, scale] in img_data[0]:
                l_s = self.get_scale_matrix(*scale)
                l_t = self.get_translation_matrix(*translation)
                l_r = self.get_rotation_matrix(*rotation)

                local_matrix = l_s @ l_t @ l_r

                for graphics_buffer, size, offset, base_matrix, renderer_data in parts_list:
                    a, b, x, c, d, y = base_matrix

                    part_sr = numpy.array([
                        [a * size[0], -b * size[1], 0,  x],
                        [-c * size[0], d * size[1], 0, -y],
                        [0, 0, 1,  0],
                        [0, 0, 0,  1],
                    ], dtype='f4')

                    part_t = numpy.array([
                        [1, 0, 0, offset[0] / size[0]],
                        [0, 1, 0, offset[1] / size[1]],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ], dtype='f4')

                    part_matrix = part_sr @ part_t

                    full_matrix = self.projection @ global_matrix @ local_matrix @ part_matrix

                    tex = self.context.texture(size, 4, graphics_buffer)
                    tex.filter = (self.filtering_mode, self.filtering_mode)
                    tex.repeat_x = False
                    tex.repeat_y = False
                    tex.use(0)

                    buffer_length = 20
                    passes = 6
                    buffer_full = buffer_length * passes
                    if renderer_data is not None:
                        pass_data = [value for render_pass in renderer_data.pass_list for value in [*render_pass[0].values()] + [render_pass[1], 1, 0, 0]]
                        pass_data.extend([0] * (buffer_full - len(pass_data)))
                        pass_bytes = struct.pack(f'{buffer_full}i', *pass_data)
                    else:
                        pass_bytes = struct.pack(f'{buffer_full}i', *bytes(buffer_full))

                    pass_data_buffer = self.context.buffer(pass_bytes)
                    self.program['PassBlock'].binding = 0
                    pass_data_buffer.bind_to_uniform_block(0)

                    self.program['u_matrix'].write(full_matrix.T.astype('f4').tobytes())
                    self.vertex_array.render(moderngl.TRIANGLE_STRIP)

                    tex.release()

        return self.framebuffer.read(components=4, dtype='f1')


    def get_translation_matrix(self, x, y, z):
        return numpy.array([
            [1, 0, 0, x],
            [0, 1, 0, y],
            [0, 0, 1, z],
            [0, 0, 0, 1],
        ])

    def get_rotation_matrix(self, x, y, z):
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

    def get_scale_matrix(self, x, y, z):
        return numpy.array([
            [x, 0, 0, 0],
            [0, y, 0, 0],
            [0, 0, z, 0],
            [0, 0, 0, 1],
        ])