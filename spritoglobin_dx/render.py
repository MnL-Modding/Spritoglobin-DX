import math
import struct

import moderngl
import numpy



class SpriteRenderer:
    def __init__(self, canvas_size):
        self.framebuffer = None
        
        self.context = moderngl.create_context(standalone=True)
        self.context.enable(moderngl.BLEND)

        self.resize(canvas_size)
        
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
                    int const_color_index;
                    int keep_going;
                };
                layout(std140) uniform PassBlock {
                    Pass passes[6];
                };

                vec4 getSource(int rgb_index, int a_index, vec4 out_tex, vec2 uv, int global_color_index) {
                    vec4 source_out = vec4(1.0, 0.0, 1.0, 0.5);

                    if (rgb_index == 0)       source_out.rgb = u_primary_color.rgb;
                    else if (rgb_index == 1)  source_out.rgb = u_light_0.rgb;
                    else if (rgb_index == 2)  source_out.rgb = u_light_1.rgb;
                    else if (rgb_index == 3)  source_out.rgb = texture(u_texture_0, uv).rgb;
                    else if (rgb_index == 4)  source_out.rgb = texture(u_texture_1, uv).rgb;
                    else if (rgb_index == 5)  source_out.rgb = texture(u_texture_2, uv).rgb;
                    else if (rgb_index == 6)  source_out.rgb = texture(u_texture_3, uv).rgb;
                    else if (rgb_index == 13) source_out.rgb = vec3(0.0, 0.0, 0.0);
                    else if (rgb_index == 14) source_out.rgb = u_globalPalette[global_color_index].rgb;
                    else if (rgb_index == 15) source_out.rgb = out_tex.rgb;

                    if (a_index == 0)       source_out.a = u_primary_color.a;
                    else if (a_index == 1)  source_out.a = u_light_0.a;
                    else if (a_index == 2)  source_out.a = u_light_1.a;
                    else if (a_index == 3)  source_out.a = texture(u_texture_0, uv).a;
                    else if (a_index == 4)  source_out.a = texture(u_texture_1, uv).a;
                    else if (a_index == 5)  source_out.a = texture(u_texture_2, uv).a;
                    else if (a_index == 6)  source_out.a = texture(u_texture_3, uv).a;
                    else if (a_index == 13) source_out.a = 0.0;
                    else if (a_index == 14) source_out.a = u_globalPalette[global_color_index].a;
                    else if (a_index == 15) source_out.a = out_tex.a;

                    return source_out;
                }

                vec4 getOperand(int rgb_index, int a_index, vec4 input) {
                    vec4 operand_out = vec4(1.0, 0.0, 1.0, 0.5);

                    if (rgb_index == 0)      operand_out.rgb = input.rgb;
                    else if (rgb_index == 1) operand_out.rgb = 1.0 - input.rgb;
                    else if (rgb_index == 2) operand_out.rgb = vec3(input.a);
                    else if (rgb_index == 3) operand_out.rgb = vec3(1.0 - input.a);

                    if (a_index == 0)      operand_out.a = input.a;
                    else if (a_index == 1) operand_out.a = 1.0 - input.a;

                    return operand_out;
                }

                vec4 getCombinedColor(int rgb_index, int a_index, vec4 source_0, vec4 source_1, vec4 source_2) {
                    vec4 combineOut = vec4(1.0, 0.0, 1.0, 0.5);

                    if (rgb_index == 0)      combineOut.rgb = source_0.rgb;
                    else if (rgb_index == 1) combineOut.rgb = source_0.rgb * source_1.rgb;
                    else if (rgb_index == 2) combineOut.rgb = source_0.rgb + source_1.rgb;
                    else if (rgb_index == 3) combineOut.rgb = (source_0.rgb - 0.5) + (source_1.rgb - 0.5);
                    else if (rgb_index == 4) combineOut.rgb = mix(source_0.rgb, source_1.rgb, source_2.rgb);
                    else if (rgb_index == 5) combineOut.rgb = source_0.rgb - source_1.rgb;
                    else if (rgb_index == 6) {
                        vec3 source_0_n = (source_0.rgb * 2.0) - 1.0;
                        vec3 source_1_n = (source_1.rgb * 2.0) - 1.0;
                        combineOut.rgb = vec3(dot(source_0_n, source_1_n));
                    }
                    else if (rgb_index == 7) {
                        vec4 source_0_n = (source_0 * 2.0) - 1.0;
                        vec4 source_1_n = (source_1 * 2.0) - 1.0;
                        combineOut.rgb = vec3(dot(source_0_n, source_1_n));
                    }
                    else if (rgb_index == 8) combineOut.rgb = (source_0.rgb * source_1.rgb) + source_2.rgb;
                    else if (rgb_index == 9) combineOut.rgb = (source_0.rgb + source_1.rgb) * source_2.rgb;

                    if (a_index == 0)      combineOut.a = source_0.a;
                    else if (a_index == 1) combineOut.a = source_0.a * source_1.a;
                    else if (a_index == 2) combineOut.a = source_0.a + source_1.a;
                    else if (a_index == 3) combineOut.a = (source_0.a - 0.5) + (source_1.a - 0.5);
                    else if (a_index == 4) combineOut.a = mix(source_0.a, source_1.a, source_2.a);
                    else if (a_index == 5) combineOut.a = source_0.a - source_1.a;
                    else if (a_index == 6) {
                        vec3 source_0_n = (source_0.rgb * 2.0) - 1.0;
                        vec3 source_1_n = (source_1.rgb * 2.0) - 1.0;
                        combineOut.a = dot(source_0_n, source_1_n);
                    }
                    else if (a_index == 7) {
                        vec4 source_0_n = (source_0 * 2.0) - 1.0;
                        vec4 source_1_n = (source_1 * 2.0) - 1.0;
                        combineOut.a = dot(source_0_n, source_1_n);
                    }
                    else if (a_index == 8) combineOut.a = (source_0.a * source_1.a) + source_2.a;
                    else if (a_index == 9) combineOut.a = (source_0.a + source_1.a) * source_2.a;

                    return combineOut;
                }

                void main() {
                    out_tex = texture(u_texture_0, v_texcoord);

                    for (int i = 0; i < 6; i++) {
                        if (passes[i].keep_going == 0) break;

                        vec4 source_0 = getSource(passes[i].rgb_source_0, passes[i].alpha_source_0, out_tex, v_texcoord, passes[i].const_color_index);
                        vec4 source_1 = getSource(passes[i].rgb_source_1, passes[i].alpha_source_1, out_tex, v_texcoord, passes[i].const_color_index);
                        vec4 source_2 = getSource(passes[i].rgb_source_2, passes[i].alpha_source_2, out_tex, v_texcoord, passes[i].const_color_index);

                        source_0 = getOperand(passes[i].rgb_operand_0, passes[i].alpha_operand_0, source_0);
                        source_1 = getOperand(passes[i].rgb_operand_1, passes[i].alpha_operand_1, source_1);
                        source_2 = getOperand(passes[i].rgb_operand_2, passes[i].alpha_operand_2, source_2);

                        out_tex = getCombinedColor(passes[i].rgb_combine_mode, passes[i].alpha_combine_mode, source_0, source_1, source_2);
                    }

                    f_color = out_tex;
                    if (f_color.a <= 0.0) discard;
                }
            """
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
                    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
                    tex.use(0)

                    pass_data = [value for render_pass in renderer_data.pass_list for value in [*render_pass[0].values()] + [render_pass[1], 1]]
                    pass_data.extend([0] * (96 - len(pass_data)))
                    pass_bytes = struct.pack('96i', *pass_data)

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