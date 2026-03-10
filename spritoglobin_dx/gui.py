import numpy
from PySide6 import QtWidgets, QtGui

from spritoglobin_dx.constants import *
from spritoglobin_dx.render import SpriteRenderer
from spritoglobin_dx.graphics import create_transform_demo


def grab_icon(index): # TODO: GET RID OF THIS THING, THIS IS ONLY TEMPORARY
    map_theme_colors = True
    icon_size = 16, 16
    file_path = 'img_icons_dx'

    # this function is being misused horribly rn
    # this type of thing is for caching, not for grabbing a bunch of shit in real time
    # it also doesn't need to be global like this for the system i'm planning on replacing it with
    # i'm sick of working on v0.1 tho so this is what you get for now lmao

    if index == 0:
        icon = QtGui.QPixmap(*icon_size)
        icon.fill(QtCore.Qt.transparent)
        return icon

    icon_sheet = QtGui.QPixmap(str(FILES_DIR / f'{file_path}.png'))
    num_columns = icon_sheet.width() // icon_size[0]

    index -= 1
    x = (index % num_columns) * icon_size[0]
    y = (index // num_columns) * icon_size[1]

    img_rect = QtCore.QRect(x, y, *icon_size)
    icon = icon_sheet.copy(img_rect)

    if not map_theme_colors:
        return icon
    
    qp = QtGui.QPainter(icon)
    qp.setPen(QtCore.Qt.NoPen)

    icon_map_sheet = QtGui.QPixmap(str(FILES_DIR / f'{file_path}_map.png'))
    icon_map = icon_map_sheet.copy(img_rect)

    for color in THEME_COLOR_ICON_MASKS:
        base_color = QtGui.QColor(THEME_COLORS[color])

        replace_colors = [
            base_color,
            base_color.lighter(150),
            base_color.darker(150),
        ]

        for i in range(3):
            replace_color = QtGui.QColor(THEME_COLOR_ICON_MASKS[color][i])
            replace_region = QtGui.QRegion(icon_map.createMaskFromColor(replace_color, QtCore.Qt.MaskMode.MaskOutColor))

            qp.setClipRegion(replace_region)
            qp.setBrush(QtGui.QColor(replace_colors[i]))

            qp.drawRect(icon.rect())
    
    qp.end()

    return icon


class ItemDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        option.decorationPosition = QtWidgets.QStyleOptionViewItem.Right
        super().paint(painter, option, index)



class InteractiveGraphicsWindow(QtWidgets.QLabel):
    background_color = QtCore.Qt.GlobalColor.black

    def __init__(self, font, size, default_scale, default_offset, min_scale, max_scale, grid_size, disable_controls = False, even_center = False, three_dimensional = False):
        super().__init__()
        self.disable_controls = disable_controls
        self.even_center = even_center
        if not self.disable_controls:
            self.setCursor(QtCore.Qt.OpenHandCursor)

            layout = QtWidgets.QGridLayout()

            padding = QtWidgets.QWidget()
            layout.addWidget(padding, 1, 4)
            padding.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

            self.info_text = QtWidgets.QLabel()
            self.info_text.setFont(font)
            palette = self.info_text.palette()
            palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(THEME_COLORS["BLACK"]))
            self.info_text.setPalette(palette)
            layout.addWidget(self.info_text, 0, 1, 1, -1)

            self.zoom_in_button = QtWidgets.QPushButton()
            self.zoom_in_button.setIcon(grab_icon(3))
            self.zoom_in_button.clicked.connect(self.zoom_in)
            self.zoom_in_button.setCursor(QtCore.Qt.ArrowCursor)
            layout.addWidget(self.zoom_in_button, 2, 1)

            self.zoom_out_button = QtWidgets.QPushButton()
            self.zoom_out_button.setIcon(grab_icon(2))
            self.zoom_out_button.clicked.connect(self.zoom_out)
            self.zoom_out_button.setCursor(QtCore.Qt.ArrowCursor)
            layout.addWidget(self.zoom_out_button, 2, 2)

            self.reset_button = QtWidgets.QPushButton()
            self.reset_button.setIcon(grab_icon(4))
            self.reset_button.clicked.connect(self.reset_view)
            self.reset_button.setCursor(QtCore.Qt.ArrowCursor)
            layout.addWidget(self.reset_button, 2, 3)

            self.setLayout(layout)

            self.mouse_last_pos = [0, 0]
            self.dragging = False

        self.canvas = QtGui.QPixmap(*size)

        self.center = [i // 2 for i in size]
        self.size = size
        self.default_scale = default_scale
        self.default_offset = default_offset
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.grid_size = grid_size
        self.bounding_boxes = []

        if three_dimensional:
            self.renderer = SpriteRenderer(self.size)
        else:
            self.renderer = None

        self.img = None
        self.img_data = None
        self.reset_view()
    
    def resizeEvent(self, event):
        size = event.size()
        self.resize([size.width(), size.height()])
        if self.renderer is not None:
            self.renderer.resize([size.width(), size.height()])
        self.update_image()
    
    def mousePressEvent(self, event):
        if self.disable_controls: return

        if (event.buttons() & QtCore.Qt.LeftButton) or ((event.buttons() & QtCore.Qt.RightButton != 0) and self.renderer is not None):
            self.dragging = True
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            pos = event.pos()
            self.mouse_last_pos = [pos.x(), pos.y()]

    def mouseMoveEvent(self, event):
        if self.disable_controls: return
        
        if self.dragging:
            if event.buttons() & QtCore.Qt.LeftButton:
                pos = event.pos()
                self.offset[0] += pos.x() - self.mouse_last_pos[0]
                self.offset[1] += pos.y() - self.mouse_last_pos[1]
                self.mouse_last_pos = [pos.x(), pos.y()]
                self.update_image()
            elif (event.buttons() & QtCore.Qt.RightButton != 0) and self.renderer is not None:
                pos = event.pos()
                #self.rotation[1] += (pos.x() - self.mouse_last_pos[0]) / 2
                #self.rotation[0] += (pos.y() - self.mouse_last_pos[1]) / 2
                self.mouse_last_pos = [pos.x(), pos.y()]
                self.update_image()
    
    def mouseReleaseEvent(self, event):
        if self.disable_controls: return
        
        self.dragging = False
        self.setCursor(QtCore.Qt.OpenHandCursor)
    
    def wheelEvent(self, event):
        if self.disable_controls: return
        
        delta = event.angleDelta().y()

        if delta > 0:
            self.zoom_in()
        elif delta < 0:
            self.zoom_out()
        event.accept()
    
    def resize(self, size):
        self.canvas = QtGui.QPixmap(*size)
        self.size = size
        self.center = [i // 2 for i in size]

        self.update_image()
    
    def zoom_in(self):
        delta = numpy.sqrt(2)
        new_scale = max(self.min_scale, min(self.scale * delta, self.max_scale))

        if self.scale != new_scale:
            if abs(self.scale - new_scale) > 0.01:
                self.offset = [offset * delta for offset in self.offset]
                self.scale = new_scale
                self.update_image()
            else:
                self.scale = new_scale
    
    def zoom_out(self):
        delta = numpy.sqrt(2)
        new_scale = max(self.min_scale, min(self.scale / delta, self.max_scale))

        if self.scale != new_scale:
            if abs(self.scale - new_scale) > 0.01:
                self.offset = [offset / delta for offset in self.offset]
                self.scale = new_scale
                self.update_image()
            else:
                self.scale = new_scale
    
    def reset_view(self):
        self.offset = list(self.default_offset)
        self.rotation = [0, 0]
        self.scale = self.default_scale
        self.update_image()
    
    def update_image(self):
        self.canvas.fill(self.background_color)
        qp = QtGui.QPainter(self.canvas)

        offset = [int(offset) for offset in self.offset]
        if self.grid_size is not None:
            grid_step = int(self.grid_size * self.scale)

            if self.scale > 1.99:
                pen_width = 2
                offset_correction = 0
            else:
                pen_width = 2
                offset_correction = 0
                # making it do this caused lots of visual errors, so for cleanliness i'm disabling it
                # pen_width = 1
                # offset_correction = 1

            for i in range(-((self.center[1] + offset[1]) // grid_step) - 1, ((self.center[1] - offset[1]) // grid_step) + 1):
                if i == 0:
                    continue
                elif i % 2 == 0:
                    qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_M"]), 1))
                else:
                    qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_L"]), 1))
                
                if  i >= 0: off_center_offset = 0
                elif i < 0: off_center_offset = -1

                line_offset = offset[1] + self.center[1] + (i * grid_step) - offset_correction + off_center_offset
                qp.drawLine(0, line_offset, self.width(), line_offset)

            for i in range(-((self.center[0] + offset[0]) // grid_step) - 1, ((self.center[0] - offset[0]) // grid_step) + 1):
                if i == 0:
                    qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["L_COLOR_0"]), pen_width))
                elif i % 2 == 0:
                    qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_M"]), 1))
                else:
                    qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_L"]), 1))
                
                if  i >= 0: off_center_offset = 0
                elif i < 0: off_center_offset = -1

                line_offset = offset[0] + self.center[0] + (i * grid_step) - offset_correction + off_center_offset
                qp.drawLine(line_offset, 0, line_offset, self.height())

            qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["M_COLOR_0"]), pen_width))
            line_offset = offset[1] + self.center[1] - offset_correction
            qp.drawLine(0, line_offset, self.width(), line_offset)

        if not self.disable_controls:
            self.info_text.setText(f"({(self.offset[0] / self.scale):5.2f}, {(self.offset[1] / self.scale):5.2f})\n{(100.00 * self.scale):6.2f}%")

        if self.even_center:
            center_offset = 0
        else:
            # i don't actually know if this offset was the true center, so for now i'm putting it back to an even center like OG Sprito
            center_offset = 0 # 0.5

        if self.img is not None:
            img_x = offset[0] + ((-self.img_offset[0] + center_offset) * self.scale) + self.center[0]
            img_y = offset[1] + ((-self.img_offset[1] + center_offset) * self.scale) + self.center[1]
            img = self.img.transformed(QtGui.QTransform().scale(self.scale, self.scale))

            qp.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
            qp.drawImage(img_x, img_y, img)
        
        if self.img_data is not None and self.renderer is not None:
            buffer = self.renderer.render_object_scene(
                global_translation = (
                    float(( offset[0] + self.center[0]) / self.scale),
                    float((-offset[1] + self.center[1]) / self.scale),
                    -0.5),
                global_rotation = (
                    self.rotation[0],
                    self.rotation[1],
                    0),
                global_scale = (
                    float(self.scale),
                    float(self.scale),
                    1),
                img_data = self.img_data,
            )

            img = QtGui.QImage(buffer, *self.renderer.canvas_size, QtGui.QImage.Format_RGBA8888)

            qp.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
            qp.drawImage(0, 0, img)

        for bounding_box in self.bounding_boxes:
            x_pos = offset[0] + (( bounding_box[0] + center_offset) * self.scale) + self.center[0]
            y_pos = offset[1] + ((-bounding_box[3] + center_offset) * self.scale) + self.center[1]
            x_size = (-bounding_box[0] +  bounding_box[1]) * self.scale
            y_size = ( bounding_box[3] + -bounding_box[2]) * self.scale
            thickness = 2

            pen = QtGui.QPen()
            pen.setWidth(thickness)
            pen.setJoinStyle(QtCore.Qt.MiterJoin)

            pen.setColor(QtGui.QColor(THEME_COLORS["WHITE"]))
            qp.setPen(pen)
            qp.drawRect(x_pos - (thickness / 2), y_pos - (thickness / 2), x_size + thickness, y_size + thickness)

            if not self.disable_controls:
                pen.setColor(QtGui.QColor(THEME_COLORS["K_COLOR_0"]))
            else:
                pen.setColor(QtGui.QColor(THEME_COLORS["P_COLOR_0"]))
            qp.setPen(pen)
            qp.drawRect(x_pos - (thickness / 2) - thickness, y_pos - (thickness / 2) - thickness, x_size + (thickness * 3), y_size + (thickness * 3))
            
        qp.end()
        self.setPixmap(self.canvas)
    
    def draw_image(self, img, img_offset):
        self.img = img
        self.img_offset = img_offset
        self.img_data = None
        self.update_image()
    
    def draw_3d_image(self, img_data):
        self.img = None
        self.img_offset = (0, 0)
        self.img_data = img_data
        self.update_image()



class AnimationTimeline(QtWidgets.QWidget):
    background_color = QtCore.Qt.GlobalColor.black

    playbackToggled = QtCore.Signal(bool)
    playbackStopped = QtCore.Signal()
    timelineScrubbed = QtCore.Signal(int)

    def __init__(self, font, padding_amount, timeline_height, timeline_amt, keyframe_padding, playhead_height):
        super().__init__()

        self.layout = QtWidgets.QGridLayout()

        padding = QtWidgets.QWidget()
        self.layout.addWidget(padding, 0, 2, 1, 1)
        padding.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.play_button = QtWidgets.QPushButton()
        self.play_button.setIcon(grab_icon(5))
        self.play_button.clicked.connect(self.toggle_playback)
        self.layout.addWidget(self.play_button, 0, 0)

        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setIcon(grab_icon(7))
        self.stop_button.clicked.connect(self.stop_playback)
        self.layout.addWidget(self.stop_button, 0, 1)

        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.timeline_scrollarea = QtWidgets.QScrollArea()
        self.timeline_scrollarea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.timeline_scrollarea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        timeline_layout = QtWidgets.QGridLayout()
        timeline_layout.setContentsMargins(*[padding_amount * (2 / 3) for _ in range(4)])

        padding = QtWidgets.QWidget()
        padding.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        timeline_layout.addWidget(padding, 1, 0)
        padding.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.info_text = QtWidgets.QLabel()
        self.info_text.setFont(font)
        palette = self.info_text.palette()
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(THEME_COLORS["BLACK"]))
        self.info_text.setPalette(palette)
        timeline_layout.addWidget(self.info_text, 0, 1)

        self.timeline_image = QtWidgets.QLabel()
        self.timeline_image.setCursor(QtCore.Qt.PointingHandCursor)
        self.timeline_image.mousePressEvent = self.scrub_timeline
        self.timeline_image.mouseMoveEvent = self.scrub_timeline

        self.timeline_scrollarea.setWidget(self.timeline_image)
        self.timeline_scrollarea.setLayout(timeline_layout)

        self.layout.addWidget(self.timeline_scrollarea, 1, 0, 1, 5)

        self.setLayout(self.layout)

        self.current_time = 0
        self.padding_amount = padding_amount
        self.timeline_height = timeline_height
        self.timeline_amt = timeline_amt
        self.keyframe_gap = keyframe_padding
        self.timeline_above = playhead_height + 4
        self.playing = False

        self.update_timeline(
            length    = 0,
            keyframes = [],
        )
    
    def resizeEvent(self, event):
        self.draw_base()
    
    def toggle_playback(self):
        self.playing = not self.playing

        if self.playing:
            self.play_button.setIcon(grab_icon(6))
        else:
            self.play_button.setIcon(grab_icon(5))

        self.playbackToggled.emit(self.playing)
    
    def stop_playback(self):
        self.playing = False

        self.play_button.setIcon(grab_icon(5))
        self.timeline_scrollarea.horizontalScrollBar().setValue(0)

        self.playbackStopped.emit()
    
    def toggle_bounding_box(self):
        self.bounding_box_visible = not self.bounding_box_visible

        self.boundingBoxToggled.emit(self.bounding_box_visible)
    
    def set_time(self, time):
        self.current_time = time

        self.draw_full()

    def scrub_timeline(self, event):
        if event.buttons() & QtCore.Qt.LeftButton and not self.playing:
            pos = event.pos().x() - self.padding_amount

            if self.current_anim_length != 0:
                timeline_width = max(self.timeline_scrollarea.width() - ((self.padding_amount * 2) + 1) - 2, (self.current_anim_length * 2))
                frame_visual_len = max(timeline_width / self.current_anim_length, 2)

                timeline_pos = max(0, min(round(pos / frame_visual_len), self.current_anim_length - 1))
                if self.current_time == timeline_pos:
                    return

                self.timelineScrubbed.emit(timeline_pos)
    
    def draw_base(self):
        padding_amount = self.padding_amount
        timeline_width = max(self.timeline_scrollarea.width() - ((padding_amount * 2) + 1) - 2, (self.current_anim_length * 2))
        timeline_height = self.timeline_height
        timeline_amt = self.timeline_amt
        keyframe_gap = self.keyframe_gap

        canvas = QtGui.QPixmap(timeline_width + 1, timeline_height * timeline_amt)
        canvas.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(canvas)

        if self.current_anim_length != 0:
            frame_visual_len = max(timeline_width / self.current_anim_length, 2)

            for i in range(self.current_anim_length):
                if i % 2 == 0: qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_H"]), 1))
                else:          qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_M"]), 1))

                line_offset = i * frame_visual_len

                qp.drawLine(line_offset, 0, line_offset, (timeline_height * timeline_amt) - 1)
        else:
            qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_H"]), 1))
            qp.drawLine(0, 0, 0, (timeline_height * timeline_amt) - 1)

        qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_H"]), 1))
        qp.drawLine(timeline_width, 0, timeline_width, (timeline_height * timeline_amt) - 1)

        for i in range(timeline_amt):
            line_height = (i * timeline_height) + (timeline_height // 2)

            qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_H"]), 1))
            qp.drawLine(0, line_height, timeline_width, line_height)

        if self.current_anim_length != 0:
            self.draw_keyframes(qp, frame_visual_len)

        qp.end()
        self.base_timeline_img = canvas.copy()
        self.draw_full()
    
    def draw_full(self):
        padding_amount = self.padding_amount
        timeline_width = max(self.timeline_scrollarea.width() - ((padding_amount * 2) + 1) - 2, (self.current_anim_length * 2))
        timeline_above = self.timeline_above
        timeline_height = self.timeline_height
        keyframe_gap = self.keyframe_gap

        canvas = QtGui.QPixmap(
            self.base_timeline_img.width() + (padding_amount * 2),
            timeline_above + self.base_timeline_img.height() + (padding_amount * 2)
        )
        canvas.fill(self.background_color)
        qp = QtGui.QPainter(canvas)

        qp.drawPixmap(padding_amount, timeline_above + padding_amount, self.base_timeline_img)
        
        if self.current_anim_length != 0:
            current_time = self.current_time % self.current_anim_length

            frame_visual_len = max(timeline_width / self.current_anim_length, 2)

            k_color = QtGui.QColor(THEME_COLORS["K_COLOR_0"])

            line_offset = current_time * frame_visual_len
            qp.setPen(QtGui.QPen(k_color, 1))
            qp.drawLine(
                padding_amount + line_offset,
                padding_amount + timeline_above,
                padding_amount + line_offset,
                padding_amount + timeline_above + self.base_timeline_img.height()
            )

            k_color.setAlpha(127)

            qp.setBrush(QtGui.QBrush(k_color))
            x = padding_amount + line_offset
            y = padding_amount + timeline_above
            playhead = QtGui.QPolygonF([
                QtCore.QPointF(x +  0, y +  0),
                QtCore.QPointF(x + -4, y + -4),
                QtCore.QPointF(x + -4, y + -self.timeline_above),
                QtCore.QPointF(x +  4, y + -self.timeline_above),
                QtCore.QPointF(x +  4, y + -4),
            ])

            qp.drawPolygon(playhead)

            self.draw_highlighted_keyframe(qp, frame_visual_len)

        qp.end()

        self.timeline_image.resize(canvas.size())
        self.timeline_image.setPixmap(canvas)

        scroll = self.timeline_scrollarea.horizontalScrollBar().value()
        
        if (not self.timeline_scrollarea.horizontalScrollBar().isSliderDown()) and self.playing:
            max_scroll = self.timeline_scrollarea.horizontalScrollBar().maximum()
            if self.current_anim_length != 0:
                progress = current_time / self.current_anim_length
            else:
                progress = 0
            scroll = max_scroll * progress

        self.timeline_scrollarea.horizontalScrollBar().setValue(scroll)

        self.display_info()
    
    def update_timeline(self, length = 0, keyframes = []):
        self.current_anim_length = length
        self.current_keyframe_list = keyframes

        self.draw_base()



class GraphicsAnimationTimeline(AnimationTimeline):
    boundingBoxToggled = QtCore.Signal(bool)

    def __init__(self, font, padding_amount, timeline_height, keyframe_padding, playhead_height):
        self.bounding_box_visible = False
        self.current_parts = None
        self.current_matrix = None
        self.current_matrix_inv = False

        self.bounding_box_toggle = QtWidgets.QCheckBox()
        self.bounding_box_toggle_string = QtWidgets.QLabel(self.tr("ShowBoundingBoxToggle"))
        self.bounding_box_toggle_string.setBuddy(self.bounding_box_toggle)
        self.bounding_box_toggle.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.bounding_box_toggle.checkStateChanged.connect(self.toggle_bounding_box)

        frame_data = QtWidgets.QWidget()
        frame_data_layout = QtWidgets.QGridLayout(frame_data)
        frame_data_layout.setContentsMargins(0, 0, 0, 0)

        self.frame_data = QtWidgets.QLabel()
        self.frame_data.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        frame_data_layout.addWidget(self.frame_data, 0, 0, 2, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        frame_data_layout.addWidget(line, 0, 2, 2, 1)

        self.frame_data_matrix = []
        for i in range(6):
            temp = QtWidgets.QLabel()
            self.frame_data_matrix.append(temp)
            frame_data_layout.addWidget(temp, i // 3, (i % 3) + 3, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        frame_data_layout.addWidget(line, 0, 6, 2, 1)

        self.matrix_demo = QtWidgets.QLabel()
        frame_data_layout.addWidget(self.matrix_demo, 0, 7, 2, 1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        timeline_amt = 1
        super().__init__(font, padding_amount, timeline_height, timeline_amt, keyframe_padding, playhead_height)

        self.layout.addWidget(self.bounding_box_toggle_string, 0, 3)
        self.layout.addWidget(self.bounding_box_toggle, 0, 4)

        self.layout.addWidget(frame_data, 2, 0, 1, -1)
    
    def draw_keyframes(self, qp, frame_visual_len):
        keyframe_ends = self.current_keyframe_list + [self.current_anim_length]
        for i, keyframe in enumerate(self.current_keyframe_list):
            if i % 2 == 0:
                m_color = QtGui.QColor(THEME_COLORS["M_COLOR_0"])
                qp.setPen(QtGui.QPen(m_color, 1))
                m_color.setAlpha(127)
                qp.setBrush(QtGui.QBrush(m_color))
            else:
                l_color = QtGui.QColor(THEME_COLORS["L_COLOR_0"])
                qp.setPen(QtGui.QPen(l_color, 1))
                l_color.setAlpha(127)
                qp.setBrush(QtGui.QBrush(l_color))
            
            box_offset = keyframe * frame_visual_len
            box_offset_end = keyframe_ends[i + 1] * frame_visual_len
            
            qp.drawRect(
                box_offset,
                self.keyframe_gap,
                box_offset_end - box_offset - (max(frame_visual_len * 0.2, 1)),
                self.timeline_height - (self.keyframe_gap * 2) - 1
            )
    
    def draw_highlighted_keyframe(self, qp, frame_visual_len):
        keyframe_ends = self.current_keyframe_list + [self.current_anim_length]
        current_time = self.current_time % self.current_anim_length
        for i, keyframe in enumerate(self.current_keyframe_list):

            playhead_is_over = (current_time >= keyframe) and (current_time < keyframe_ends[i + 1])
            if playhead_is_over:
                qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["K_COLOR_0"]), 1))
                w_color = QtGui.QColor(THEME_COLORS["WHITE"])
                w_color.setAlpha(127)
                qp.setBrush(QtGui.QBrush(w_color))

                box_offset = keyframe * frame_visual_len
                box_offset_end = keyframe_ends[i + 1] * frame_visual_len

                qp.drawRect(
                    self.padding_amount + box_offset,
                    self.padding_amount + self.timeline_above + self.keyframe_gap,
                    box_offset_end - box_offset - (max(frame_visual_len * 0.2, 1)),
                    self.timeline_height - (self.keyframe_gap * 2) - 1
                )

                break

    def display_info(self):
        if self.current_anim_length != 0:
            current_time = self.current_time % self.current_anim_length

            self.info_text.setText(f"{(current_time):3} / {self.current_anim_length:3}")
        else:
            self.info_text.setText("")
        
        string = ""

        if self.current_parts is None:
            string += self.tr("FrameDataSpritePartsUsed").format("?")
        elif self.current_parts[1] == 1:
            string += self.tr("FrameDataSpritePartsUsed").format(self.current_parts[0])
        elif self.current_parts[1] == 0:
            string += self.tr("FrameDataSpritePartsUsedNone")
        else:
            string += self.tr("FrameDataSpritePartsUsed").format(f"{self.current_parts[0]} - {self.current_parts[0] + self.current_parts[1] - 1}")
        
        string += "\n"

        if self.current_parts is None:
            string += self.tr("FrameDataTransformMatrixUsed").format("?")
        elif not self.current_matrix_index > -1:
            string += self.tr("FrameDataTransformMatrixUsedNone")
        else:
            string += self.tr("FrameDataTransformMatrixUsed").format(self.current_matrix_index)
        
        string += "\n"
        if self.current_matrix_inv:
            string += self.tr("FrameDataTransformMatrixInverted")
        else:
            string += "---"
            
        self.frame_data.setText(string)

        if self.current_matrix == [] or self.current_matrix is None:
            matrix = [1, 0, 0, 0, 1, 0]
            [label.setEnabled(False) for label in self.frame_data_matrix]
        else:
            matrix = list(self.current_matrix)
            [label.setEnabled(True) for label in self.frame_data_matrix]

        for i, label in enumerate(self.frame_data_matrix):
            string = [
                self.tr("FrameDataTransformMatrixXScale"),
                self.tr("FrameDataTransformMatrixXShear"),
                self.tr("FrameDataTransformMatrixXPos"),
                self.tr("FrameDataTransformMatrixYShear"),
                self.tr("FrameDataTransformMatrixYScale"),
                self.tr("FrameDataTransformMatrixYPos"),
            ][i]

            label.setText(string.format(f"{matrix[i]:7.4f}", matrix[i]))

        matrix_demo = QtGui.QPixmap(72, 72)
        matrix_demo.fill(self.background_color)
        qp = QtGui.QPainter(matrix_demo)
        thickness = 2

        pen = QtGui.QPen()
        pen.setWidth(thickness)
        pen.setJoinStyle(QtCore.Qt.MiterJoin)
        
        pen.setColor(QtGui.QColor(THEME_COLORS["P_COLOR_0"]))
        qp.setPen(pen)
        qp.drawRect(1, 1, 70, 70)

        pen.setColor(QtGui.QColor(THEME_COLORS["WHITE"]))
        qp.setPen(pen)
        qp.drawRect(3, 3, 66, 66)

        demo_img, demo_img_size = create_transform_demo(
            scale = 2,
            checker_amt = 8,
            colors = [
                QtGui.QColor(THEME_COLORS["M_COLOR_0"]).getRgb(),
                QtGui.QColor(THEME_COLORS["L_COLOR_0"]).getRgb(),
                QtGui.QColor(THEME_COLORS["K_COLOR_0"]).getRgb(),
                QtGui.QColor(THEME_COLORS["P_COLOR_0"]).getRgb(),
            ],
            matrix = matrix,
            inverted = self.current_matrix_inv,
        )
        
        qp.drawImage(4, 4, QtGui.QImage(demo_img, *demo_img_size, QtGui.QImage.Format.Format_RGBA8888))

        qp.end()

        self.matrix_demo.setPixmap(matrix_demo)
        self.matrix_demo.resize(matrix_demo.size())
    
    def send_frame_data(self, current_parts = None, current_keyframe_timer = None, current_matrix_index = None, current_matrix = None, current_matrix_inv = False):
        self.current_parts          = current_parts
        self.current_keyframe_timer = current_keyframe_timer
        self.current_matrix_index   = current_matrix_index
        self.current_matrix         = current_matrix
        self.current_matrix_inv     = current_matrix_inv
        
        if self.current_parts is None:
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        else:
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)



class ColorAnimationTimeline(AnimationTimeline):
    sendLayerPersistance = QtCore.Signal(bool)

    def __init__(self, font, boolean_strings, padding_amount, timeline_height, keyframe_padding, playhead_height):
        self.boolean_strings = boolean_strings
        self.layer_toggle_list_string = QtWidgets.QLabel()

        self.layer_toggle_list = QtWidgets.QComboBox()
        self.layer_toggle_list.currentIndexChanged.connect(self.update_layer)

        layer_info = QtWidgets.QWidget()
        layer_info_layout = QtWidgets.QGridLayout(layer_info)
        layer_info_layout.setContentsMargins(0, 0, 0, 0)

        self.layer_info_text_1 = QtWidgets.QLabel()
        self.layer_info_text_1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.layer_info_text_2 = QtWidgets.QLabel()
        self.layer_info_text_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.layer_info_color = QtWidgets.QLabel()
        self.layer_info_alpha = QtWidgets.QLabel()

        string_color = QtWidgets.QLabel(self.tr("LayerInfoColorRGB"))
        string_color.setBuddy(self.layer_info_color)
        string_alpha = QtWidgets.QLabel(self.tr("LayerInfoColorA"))
        string_alpha.setBuddy(self.layer_info_alpha)

        layer_info_layout.addWidget(self.layer_info_text_1, 0, 0, 1, -1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layer_info_layout.addWidget(self.layer_info_text_2, 1, 0, 1, -1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layer_info_layout.addWidget(string_color, 2, 0, alignment = QtCore.Qt.AlignmentFlag.AlignRight)
        layer_info_layout.addWidget(string_alpha, 2, 1, alignment = QtCore.Qt.AlignmentFlag.AlignLeft)
        layer_info_layout.addWidget(self.layer_info_color, 3, 0, alignment = QtCore.Qt.AlignmentFlag.AlignRight)
        layer_info_layout.addWidget(self.layer_info_alpha, 3, 1, alignment = QtCore.Qt.AlignmentFlag.AlignLeft)

        timeline_amt = 4
        super().__init__(font, padding_amount, timeline_height, timeline_amt, keyframe_padding, playhead_height)

        self.layout.addWidget(self.layer_toggle_list_string, 0, 4, 1, 2)
        self.layout.addWidget(self.layer_toggle_list, 0, 6)
        self.layout.addWidget(layer_info, 1, 5, -1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        self.animation_data = None
        self.use_alt_timer = False

        self.update_layer(0, update_list = True)
    
    def set_time(self, time):
        if self.animation_data is not None:
            if not self.animation_data[self.current_layer]["is_persistant"]:
                time = min(
                    time % self.animation_data[self.current_layer]["parent_length"],
                    self.animation_data[self.current_layer]["length"] - 1,
                )
                
        self.current_time = time

        self.draw_full()
    
    def draw_keyframes(self, qp, frame_visual_len):
        for channel in range(4):
            keyframe_list = self.current_keyframe_list[channel]
            if keyframe_list == []:
                continue

            test_keyframe = keyframe_list[-1]
            if test_keyframe[1] != self.current_anim_length:
                keyframe_list.append([test_keyframe[0], self.current_anim_length])

            for i in range(len(keyframe_list) - 1):
                value, keyframe = keyframe_list[i]
                next_value, next_keyframe = keyframe_list[i + 1]

                color = QtGui.QColor(["#FF0000", "#00FF00", "#0000FF", "#FFFFFF"][channel])
                qp.setPen(QtGui.QPen(color, 1))
                color.setAlpha(127)
                qp.setBrush(QtGui.QBrush(color))

                box_offset = keyframe * frame_visual_len
                box_offset_end = next_keyframe * frame_visual_len

                initial_x = keyframe * frame_visual_len
                final_x = next_keyframe * frame_visual_len
                base_y = ((channel + 1) * self.timeline_height) - self.keyframe_gap - 1
                height_y = self.timeline_height - (2 * self.keyframe_gap)

                polygon = QtGui.QPolygonF([
                    QtCore.QPointF(initial_x, base_y),
                    QtCore.QPointF(final_x,   base_y),
                    QtCore.QPointF(final_x,   base_y - round(height_y * (next_value / 255))),
                    QtCore.QPointF(initial_x, base_y - round(height_y * (value / 255))),
                ])

                qp.drawPolygon(polygon)

    def draw_highlighted_keyframe(self, qp, frame_visual_len):
        current_time = self.current_time % self.current_anim_length
        for channel in range(4):
            keyframe_list = self.current_keyframe_list[channel]
            if keyframe_list == []:
                continue

            test_keyframe = keyframe_list[-1]
            if test_keyframe[1] != self.current_anim_length:
                keyframe_list.append([test_keyframe[0], self.current_anim_length])

            for i in range(len(keyframe_list) - 1):
                value, keyframe = keyframe_list[i]
                next_value, next_keyframe = keyframe_list[i + 1]

                playhead_is_over = (current_time >= keyframe) and (current_time < next_keyframe)
                if playhead_is_over:
                    qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["K_COLOR_0"]), 1))
                    w_color = QtGui.QColor(THEME_COLORS["WHITE"])
                    w_color.setAlpha(127)
                    qp.setBrush(QtGui.QBrush(w_color))

                    box_offset = keyframe * frame_visual_len
                    box_offset_end = next_keyframe * frame_visual_len

                    initial_x = keyframe * frame_visual_len
                    final_x = next_keyframe * frame_visual_len
                    base_y = ((channel + 1) * self.timeline_height) - self.keyframe_gap - 1
                    height_y = self.timeline_height - (2 * self.keyframe_gap)

                    initial_x += self.padding_amount
                    final_x += self.padding_amount
                    base_y += self.padding_amount + self.timeline_above

                    polygon = QtGui.QPolygonF([
                        QtCore.QPointF(initial_x, base_y),
                        QtCore.QPointF(final_x,   base_y),
                        QtCore.QPointF(final_x,   base_y - round(height_y * (next_value / 255))),
                        QtCore.QPointF(initial_x, base_y - round(height_y * (value / 255))),
                    ])

                    qp.drawPolygon(polygon)

                    break

    def display_info(self):
        if self.current_anim_length != 0:
            current_time = self.current_time % self.current_anim_length

            self.info_text.setText(f"{(current_time):3} / {self.current_anim_length:3}")
        else:
            self.info_text.setText("")


        string = ""

        if self.current_anim_length != 0:
            channel = self.animation_data[self.current_layer]["render_channel"]
            persistant = self.boolean_strings[self.animation_data[self.current_layer]["is_persistant"]]
        else:
            channel = "?"
            persistant = "?"

        string += self.tr("LayerInfoRenderChannel").format(channel)
        string += "\n"
        string += self.tr("LayerInfoPersistant").format(persistant)

        self.layer_info_text_1.setText(string)

        
        string = ""

        if self.current_anim_length != 0:
            colors1 = []
            colors2 = []
            for channel in range(4):
                keyframe_list = self.current_keyframe_list[channel]

                if keyframe_list == []:
                    colors1.append("---")
                    colors2.append("---")
                    continue
                
                test_keyframe = keyframe_list[-1]
                if test_keyframe[1] != self.current_anim_length:
                    keyframe_list.append([test_keyframe[0], self.current_anim_length])

                for i in range(len(keyframe_list) - 1):
                    value, keyframe = keyframe_list[i]
                    next_value, next_keyframe = keyframe_list[i + 1]

                    if not ((current_time >= keyframe) and (current_time < next_keyframe)):
                        continue
                    
                    colors1.append(value)
                    colors2.append(next_value)
                
                    break

            r1, g1, b1, a1 = colors1
            r2, g2, b2, a2 = colors2
        else:
            r1, g1, b1, a1 = "?", "?", "?", "?"
            r2, g2, b2, a2 = "?", "?", "?", "?"

        string += self.tr("LayerInfoStartEndColor")
        string += "\n"
        string += f"({r1}, {g1}, {b1}, {a1})"
        string += "\n"
        string += f"({r2}, {g2}, {b2}, {a2})"

        self.layer_info_text_2.setText(string)

        
        if self.current_anim_length != 0:
            colors_interp = []
            for keyframes in self.current_keyframe_list:
                if keyframes == []:
                    out = "---"
                else:
                    out = round(numpy.interp(current_time, [key[1] for key in keyframes], [key[0] for key in keyframes]))
                colors_interp.append(out)

            r, g, b, a = colors_interp
        else:
            r, g, b, a = None, None, None, None

        for i in range(2):
            colors = [(r, g, b), (a, a, a)][i]
            color = QtGui.QPixmap(40, 40)
            color.fill(QtGui.QColor(*[c if isinstance(c, int) else 255 for c in colors]))
            qp = QtGui.QPainter(color)
            thickness = 2

            pen = QtGui.QPen()
            pen.setWidth(thickness)
            pen.setJoinStyle(QtCore.Qt.MiterJoin)

            pen.setColor(QtGui.QColor(THEME_COLORS["P_COLOR_0"]))
            qp.setPen(pen)
            qp.drawRect(1, 1, 38, 38)

            pen.setColor(QtGui.QColor(THEME_COLORS["WHITE"]))
            qp.setPen(pen)
            qp.drawRect(3, 3, 34, 34)

            qp.end()
            [self.layer_info_color, self.layer_info_alpha][i].setPixmap(color)

    def update_layer(self, layer, update_list = False):
        self.current_layer = layer

        if update_list:
            if self.animation_data is None:
                layers = 1
                layer_amt = "?"
            else:
                layers = len(self.animation_data)
                layer_amt = layers

            self.layer_toggle_list_string.setText(self.tr("LayerToggleTitle").format(layer_amt))

            self.layer_toggle_list.blockSignals(True)
            self.layer_toggle_list.clear()

            for i in range(layers):
                self.layer_toggle_list.addItem(str(i))
            self.layer_toggle_list.blockSignals(False)
            self.layer_toggle_list.setCurrentIndex(0)

            if layers == 1:
                self.layer_toggle_list_string.setEnabled(False)
                self.layer_toggle_list.setEnabled(False)
            else:
                self.layer_toggle_list_string.setEnabled(True)
                self.layer_toggle_list.setEnabled(True)

        if self.animation_data is not None:
            self.update_timeline(self.animation_data[self.current_layer]["length"], self.animation_data[self.current_layer]["keyframes"])

            self.sendLayerPersistance.emit(self.animation_data[self.current_layer]["is_persistant"])

    def send_color_data(self, layer_amt = 0, keyframes = None, render_channel = None, is_persistant = None, length = None, parent_length = None):
        if layer_amt != 0:
            self.animation_data = [{
                "keyframes":      keyframes[i],
                "render_channel": render_channel[i],
                "is_persistant":  is_persistant[i],
                "length":         length[i],
                "parent_length":  parent_length
            } for i in range(layer_amt)]
        else:
            self.animation_data = None
            self.update_timeline()
        
        self.update_layer(0, update_list = True)
        
        if self.animation_data is None or self.use_alt_timer:
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        else:
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)