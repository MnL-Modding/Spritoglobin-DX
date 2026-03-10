import math

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
                uniform sampler2D u_texture;
                in vec2 v_texcoord;
                out vec4 f_color;
                void main() {
                    f_color = texture(u_texture, v_texcoord);
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

        for real_draw in [False, True]:

            if not real_draw: self.context.blend_func = (moderngl.ONE, moderngl.ZERO, moderngl.ZERO, moderngl.ZERO)
            else:             self.context.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ONE, moderngl.ONE)

            for parts_list, translation, rotation, scale in img_data:
                l_s = self.get_scale_matrix(*scale)
                l_t = self.get_translation_matrix(*translation)
                l_r = self.get_rotation_matrix(*rotation)

                local_matrix = l_s @ l_t @ l_r

                for graphics_buffer, size, offset, base_matrix in parts_list:
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