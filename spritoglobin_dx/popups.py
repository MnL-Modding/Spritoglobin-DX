import configparser
import os

from PIL import Image
from PySide6 import QtWidgets, QtGui

from spritoglobin_dx.classes import ObjFile, InvalidObjectFileError
from spritoglobin_dx.constants import *
from spritoglobin_dx.gui import InteractiveGraphicsWindow


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



class FileImportWindow(QtWidgets.QDialog):
    def __init__(self, parent, game_title_strings, current_window_icon):
        super().__init__()

        self.parent = parent
        self.game_title_strings = game_title_strings

        self.game_ids = GAME_IDS_THAT_ARE_CURRENTLY_SUPPORTED

        self.current_window_icon = current_window_icon

        supported_games = [self.game_title_strings[f"GameTitle{game_id}"] for game_id in self.game_ids]

        self.supported_games_list_string_format = ", ".join(supported_games[:-1]), supported_games[-1]

        self.setWindowTitle(self.tr("ImportWindowTitle"))
        self.setWindowIcon(self.current_window_icon)

        layout = QtWidgets.QGridLayout()

        self.choose_file_button = QtWidgets.QPushButton(self.tr("ImportChooseFileButton"))
        self.choose_file_button.setIcon(grab_icon(14))
        self.choose_file_button.clicked.connect(self.import_obj_file)

        file_info_none_string = self.tr("FileInfoNone")
        self.file_info_text = QtWidgets.QLabel(f"\n{file_info_none_string}\n")
        self.file_info_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.sort_contents_toggle = QtWidgets.QCheckBox(self.tr("ImportAlphabetizeToggle"))
        self.sort_contents_toggle.setVisible(False)

        self.import_button = QtWidgets.QPushButton(self.tr("ImportAcceptButton"))
        self.import_button.setIcon(grab_icon(1))
        self.import_button.clicked.connect(self.finalize)
        self.import_button.setEnabled(False)

        layout.addWidget(self.choose_file_button, 0, 1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_info_text, 1, 0, 1, 3, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sort_contents_toggle, 2, 0, 1, 3, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.import_button, 3, 1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

        self.prematurely_closed = None
        self.prevent_open = False

        self.import_obj_file()

        if self.prematurely_closed == True:
            self.prematurely_closed = True
            self.prevent_open = True
            return
        else:
            self.prematurely_closed = True
    
    def import_obj_file(self):
        config = configparser.ConfigParser()
        config.read(str(CONFIG_DIR / "config.ini"))

        path = config.get("NavigationPaths", "obj_import_path")

        QtWidgets.QMessageBox.information(
            self,
            self.tr("ImportChooseFileTitle"),
            self.tr("ImportChooseFileBlurb").format(*self.supported_games_list_string_format),
        )

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("ImportChooseFileTitle"),
            path,
            "Data Archives (*.dat);;All Files (*)",
        )

        if path == '':
            if self.prematurely_closed is None:
                self.prematurely_closed = True
            return
        
        config["NavigationPaths"]["obj_import_path"] = os.path.dirname(path)
        with open(CONFIG_DIR / "config.ini", "w") as config_file:
            config.write(config_file)

        paths = dict(config['NavigationPaths'])

        self.obj_import_path = paths.get("obj_import_path", "")

        game_title = "???"
        info = "???"
        valid = ("?", "?")
        ca_info = "???"
        ca_valid = ("?", "?")
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            with open(path, 'rb') as obj_in:
                obj_data = ObjFile(obj_in.read())
        except InvalidObjectFileError as e:
            self.import_button.setEnabled(False)
            QtWidgets.QApplication.restoreOverrideCursor()

            err = QtWidgets.QMessageBox(self.parent)
            error_strings = {
                100: self.tr("ImportFileError100"),
                101: self.tr("ImportFileError101"),
                102: self.tr("ImportFileError102"),
            }

            err.setWindowTitle(self.tr("ImportFileFailureTitle"))
            err.setWindowIcon(self.current_window_icon)
            err.setText(self.tr("ImportFileFailureBlurb").format(e, error_strings[e.error_code].format(*self.supported_games_list_string_format)))
            err.setIcon(QtWidgets.QMessageBox.Icon.Critical)

            err.exec()

            file_info_none_string = self.tr("FileInfoNone")
            self.file_info_text.setText(f"\n{file_info_none_string}\n")
            self.sort_contents_toggle.setVisible(False)
        else:
            self.current_path = path
            self.current_game_id = obj_data.game_id
            self.import_button.setEnabled(True)
            self.sort_contents_toggle.setVisible(True)

            info = self.tr("FileInfoBG4TitleAndVersion").format(*obj_data.bg4_version)
            valid = (obj_data.valid_entries, obj_data.invalid_entries)
            ca_info = self.tr("FileInfoBG4TitleAndVersion").format(*obj_data.bg4_ca_version)
            ca_valid = (obj_data.valid_ca_entries, obj_data.invalid_ca_entries)

            game_title = self.game_title_strings[f"GameTitle{self.current_game_id}"]
        finally:
            cellanime_title_string = self.tr("FileInfoCellAnimeTitle")

            string = ""

            string += "\n"
            string += f"{os.path.basename(path)} - {info}"
            string += "\n"
            string += self.tr("FileInfoValidEntryCount").format(*valid)
            string += "\n"
            string += f"({game_title})"
            string += "\n"
            string += "\n"
            string += f"{cellanime_title_string} - {ca_info}"
            string += "\n"
            string += self.tr("FileInfoValidEntryCount").format(*ca_valid)
            string += "\n"

            self.file_info_text.setText(string)
            QtWidgets.QApplication.restoreOverrideCursor()

    def finalize(self):
        self.sort_contents = self.sort_contents_toggle.isChecked()
        self.prematurely_closed = False
        self.close()



class GifExportWindow(QtWidgets.QDialog):
    def __init__(self, parent, current_window_icon, success_jingle, obj_data, use_low_framerate, initial_object, initial_animation, initial_color_anim):
        super().__init__()

        self.parent = parent
        self.obj_data = obj_data

        self.current_window_icon = current_window_icon
        self.success_jingle = success_jingle

        self.setWindowTitle(self.tr("ExportWindowTitle"))
        self.setWindowIcon(self.current_window_icon)

        layout = QtWidgets.QGridLayout()

        self.framerate_choose_box = QtWidgets.QComboBox()
        self.framerate_choose_box.addItems([
            self.tr("AnimationOptionFramerate").format("60 / 50"),
            self.tr("AnimationOptionFramerate").format("30 / 25"),
        ])
        if use_low_framerate:
            self.framerate_choose_box.setCurrentIndex(1)
        self.framerate_choose_box.currentIndexChanged.connect(self.reset_timer)

        self.color_anim_list_box = QtWidgets.QComboBox()
        self.color_anim_list_box.currentIndexChanged.connect(self.reset_timer)

        self.anim_list_box = QtWidgets.QListWidget()
        self.anim_list_box.currentRowChanged.connect(self.update_anim_options)

        self.add_button = QtWidgets.QPushButton()
        self.add_button.setIcon(grab_icon(9))
        self.add_button.clicked.connect(self.add_anim)

        self.remove_button = QtWidgets.QPushButton()
        self.remove_button.setIcon(grab_icon(10))
        self.remove_button.clicked.connect(self.remove_anim)

        self.move_up_button = QtWidgets.QPushButton()
        self.move_up_button.setIcon(grab_icon(11))
        self.move_up_button.clicked.connect(self.move_anim_up)

        self.move_down_button = QtWidgets.QPushButton()
        self.move_down_button.setIcon(grab_icon(12))
        self.move_down_button.clicked.connect(self.move_anim_down)

        self.anim_choose_list_box = QtWidgets.QComboBox()
        self.anim_choose_list_box.currentIndexChanged.connect(self.change_current_anim_data)

        self.loop_choose_spin_box = QtWidgets.QSpinBox()
        self.loop_choose_spin_box.setMinimum(1)
        self.loop_choose_spin_box.setMaximum(99)
        self.loop_choose_spin_box.valueChanged.connect(self.change_current_anim_data)

        self.export_button = QtWidgets.QPushButton(self.tr("ExportAcceptButton"))
        self.export_button.setIcon(grab_icon(16))
        self.export_button.clicked.connect(self.export_gif)

        mono_font = QtGui.QFont()
        mono_font.setFamily("Monospace")
        mono_font.setFixedPitch(True)

        self.gif_preview = InteractiveGraphicsWindow(
            font = mono_font,
            size = [513, 513],
            default_scale = 2,
            default_offset = [0.0, 0.0],
            min_scale = 0.5,
            max_scale = 16.0,
            grid_size = 32,
        )
        self.gif_preview.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.gif_preview.setMinimumWidth(513)
        self.gif_preview.setMinimumHeight(513)
        self.gif_preview.background_color = QtCore.Qt.transparent

        self.gif_timer_text = QtWidgets.QLabel(f"{0:3} / {0:3}")
        self.gif_timer_text.setFont(mono_font)

        layout.addWidget(self.framerate_choose_box, 1, 0, 1, 2)
        layout.addWidget(self.color_anim_list_box, 1, 2, 1, 2)
        layout.addWidget(self.anim_list_box, 3, 0, 1, 4)
        layout.addWidget(self.add_button, 4, 0)
        layout.addWidget(self.remove_button, 4, 1)
        layout.addWidget(self.move_up_button, 4, 2)
        layout.addWidget(self.move_down_button, 4, 3)
        layout.addWidget(self.anim_choose_list_box, 8, 0, 1, 2)
        layout.addWidget(self.loop_choose_spin_box, 8, 2, 1, 2)
        layout.addWidget(self.export_button, 9, 0, 1, 4, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.gif_preview, 0, 4, 9, 1)
        layout.addWidget(self.gif_timer_text, 9, 4, alignment = QtCore.Qt.AlignmentFlag.AlignRight)

        string = QtWidgets.QLabel(self.tr("AnimationOptionFramerateTitle"))
        string.setBuddy(self.framerate_choose_box)
        string.setEnabled(False)
        layout.addWidget(string, 0, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationOptionColorAnimTitle"))
        string.setBuddy(self.color_anim_list_box)
        string.setEnabled(False)
        layout.addWidget(string, 0, 2, 1, 2)

        string = QtWidgets.QLabel(self.tr("ExportAnimationListTitle"))
        string.setBuddy(self.anim_list_box)
        string.setEnabled(False)
        layout.addWidget(string, 2, 0, 1, 4)

        string = QtWidgets.QLabel(self.tr("AnimationListDataCurrentAnim"))
        string.setBuddy(self.anim_choose_list_box)
        string.setEnabled(False)
        layout.addWidget(string, 7, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationListDataCurrentLoops"))
        string.setBuddy(self.loop_choose_spin_box)
        string.setEnabled(False)
        layout.addWidget(string, 7, 2, 1, 2)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line, 6, 0, 1, 4)

        self.setLayout(layout)

        self.animation_timer = QtCore.QTimer()
        self.animation_timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.animation_timer.timeout.connect(self.tick_timer)

        self.obj_data.cache_object(initial_object)
        self.current_anim_list = [[initial_animation, 1]]

        self.update_anim_choose_data(initial_color_anim)
        self.update_anim_list_box_entries()
        self.anim_list_box.setCurrentRow(0)

        self.reset_timer()
        self.animation_timer.start()
    
    def tick_timer(self):
        framerate = self.framerate_choose_box.currentIndex()
        # 60 / 50 fps, 30 / 25 fps
        advance_amt = [ 1,  2][framerate]

        self.obj_data.increment_timers(advance_amt, animation_timer = True, color_timer = True)
        
        self.update_preview()

    def reset_timer(self):
        self.obj_data.set_timers(0, animation_timer = True, color_timer = True)

        framerate = self.framerate_choose_box.currentIndex()
        # 60 fps, 30 fps
        advance_spd = [17, 33][framerate]
        
        self.animation_timer.setInterval(round(advance_spd))
        self.update_preview()
    
    def update_preview(self):
        anim, _ = self.current_anim_list[self.anim_list_box.currentRow()]

        color_animation = -1
        if self.color_anim_list_box.currentIndex() != 0:
            color_animation = int(self.color_anim_list_box.currentText())

        img, size, offset = self.obj_data.get_sprite_with_offset(
            object_name      = self.obj_data.cached_object.name, 
            animation_index  = anim,
            color_anim_index = color_animation,
        )
        
        if img is not None:
            self.gif_preview.draw_image(QtGui.QImage(img, *size, QtGui.QImage.Format_RGBA8888), offset)
        else:
            self.gif_preview.draw_image(None, (0, 0))

        animation_properties = self.obj_data.get_animation_properties(
            object_name     = self.obj_data.cached_object.name,
            animation_index = anim,
        )
        
        total_time = animation_properties["length"]
        current_time = self.obj_data.get_timers(color_timer = True)[0] % total_time

        self.gif_timer_text.setText(f"{(current_time):3} / {total_time:3}")


    def add_anim(self):
        anim, count = self.current_anim_list[self.anim_list_box.currentRow()]
        insertion_point = self.anim_list_box.currentRow() + 1

        self.current_anim_list.insert(insertion_point, [anim, 1])

        self.update_anim_list_box_entries()

        self.anim_list_box.setCurrentRow(insertion_point)
    
    def remove_anim(self):
        del self.current_anim_list[self.anim_list_box.currentRow()]

        self.update_anim_list_box_entries()
    
    def move_anim_up(self):
        curr = self.anim_list_box.currentRow()
        swap = self.anim_list_box.currentRow() - 1

        self.current_anim_list[curr], self.current_anim_list[swap] = self.current_anim_list[swap], self.current_anim_list[curr]

        self.update_anim_list_box_entries()
        self.anim_list_box.setCurrentRow(self.anim_list_box.currentRow() - 1)
    
    def move_anim_down(self):
        curr = self.anim_list_box.currentRow()
        swap = self.anim_list_box.currentRow() + 1

        self.current_anim_list[curr], self.current_anim_list[swap] = self.current_anim_list[swap], self.current_anim_list[curr]

        self.update_anim_list_box_entries()
        self.anim_list_box.setCurrentRow(self.anim_list_box.currentRow() + 1)


    def change_current_anim_data(self):
        anim = self.anim_choose_list_box.currentIndex()
        count = self.loop_choose_spin_box.value()

        self.current_anim_list[self.anim_list_box.currentRow()] = [anim, count]
        
        self.update_anim_list_box_entries()
    
    def update_anim_choose_data(self, initial_color_anim = None):
        self.anim_choose_list_box.blockSignals(True)
        self.anim_choose_list_box.clear()

        object_properties = self.obj_data.get_object_properties(object_name = self.obj_data.cached_object.name)

        for i in range(object_properties["animation_number"]):
            self.anim_choose_list_box.addItem(str(i))

        self.anim_choose_list_box.blockSignals(False)


        self.color_anim_list_box.blockSignals(True)
        self.color_anim_list_box.clear()

        object_properties = self.obj_data.get_object_properties(object_name = self.obj_data.cached_object.name)

        self.color_anim_list_box.setEnabled(object_properties["has_color_data"])

        self.color_anim_list_box.addItem(self.tr("AnimationOptionColorAnimNone"))
        if object_properties["has_color_data"]:
            for anim in object_properties["color_data"].keys():
                self.color_anim_list_box.addItem(str(anim))
        
            if initial_color_anim is not None:
                self.color_anim_list_box.setCurrentIndex(initial_color_anim)

        self.color_anim_list_box.blockSignals(False)
    
    def update_anim_list_box_entries(self):
        self.anim_list_box.blockSignals(True)

        diff = len(self.current_anim_list) - self.anim_list_box.count()
        abs_diff = abs(diff)

        if diff > 0:
            for i in range(abs_diff):
                self.anim_list_box.addItem("")
        elif diff < 0:
            for i in range(abs_diff):
                self.anim_list_box.takeItem(0)
        
        for i, (anim, count) in enumerate(self.current_anim_list):
            if count == 1:
                string = self.tr("ExportAnimationListData").format(anim)
            else:
                string = self.tr("ExportAnimationListDataWithLoop").format(anim, count)
            item = self.anim_list_box.item(i)
            item.setText(string)

        self.anim_list_box.blockSignals(False)

        self.update_button_permissions()
        self.reset_timer()
    
    def update_anim_options(self):
        anim, count = self.current_anim_list[self.anim_list_box.currentRow()]

        self.anim_choose_list_box.blockSignals(True)
        self.anim_choose_list_box.setCurrentIndex(anim)
        self.anim_choose_list_box.blockSignals(False)
        
        self.loop_choose_spin_box.blockSignals(True)
        self.loop_choose_spin_box.setValue(count)
        self.loop_choose_spin_box.blockSignals(False)

        self.update_button_permissions()
        self.reset_timer()

    def update_button_permissions(self):
        self.remove_button.setEnabled(self.anim_list_box.count() > 1)
        self.move_up_button.setEnabled(self.anim_list_box.currentRow() > 0)
        self.move_down_button.setEnabled(self.anim_list_box.currentRow() < (self.anim_list_box.count() - 1))


    def export_gif(self):
        config = configparser.ConfigParser()
        config.read(str(CONFIG_DIR / "config.ini"))

        path = config.get("NavigationPaths", "img_export_path")
        filename = f"{self.obj_data.game_id}_{self.obj_data.cached_object.name}_"
        filename += ".".join(f"{anim}" for anim, _ in self.current_anim_list)

        path, file_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr("ExportChooseFileTitle"),
            f"{path}/{filename}",
            "GIF files (*.gif);;Animated PNGs (*.png);;All Files (*)",
        )

        if path == '':
            return
        
        config["NavigationPaths"]["img_export_path"] = os.path.dirname(path)
        with open(CONFIG_DIR / "config.ini", "w") as config_file:
            config.write(config_file)

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        # begin compiling the animation
        self.reset_timer()
        self.animation_timer.stop()
        object_properties = self.obj_data.get_object_properties(object_name = self.obj_data.cached_object.name)
        animations = [anim for anim, count in self.current_anim_list for _ in range(count)]

        color_animation = -1
        if self.color_anim_list_box.currentIndex() != 0:
            color_animation = int(self.color_anim_list_box.currentText())

        framerate = self.framerate_choose_box.currentIndex()
        # 60 / 50 fps, 30 / 25 fps
        advance_amt = [ 1,  2][framerate]
        
        self.obj_data.init_timers()

        # gather all the image data
        image_data = []
        min_x, max_x, min_y, max_y = 0, 0, 0, 0

        for anim_num in animations:
            object_name = self.obj_data.cached_object.name

            self.obj_data.set_timers(0, animation_timer = True)

            animation_properties = self.obj_data.get_animation_properties(
                object_name     = object_name,
                animation_index = anim_num,
            )

            for i in range(animation_properties["length"] // advance_amt):
                img, (w, h), (x, y) = self.obj_data.get_sprite_with_offset(
                    object_name      = object_name, 
                    animation_index  = anim_num,
                    color_anim_index = color_animation,
                )

                image_data.append([img, (w, h), (x, y)])

                if img is not None:
                    min_x, max_x, min_y, max_y = [
                        min(min_x, -x,    ), # left
                        max(max_x, -x + w,), # right
                        min(min_y,  y - h,), # down
                        max(max_y,  y,    ), # up
                    ]

                self.obj_data.increment_timers(
                    advance_amt,
                    animation_timer = True,
                    color_timer     = color_animation >= 0,
                )

        # compile the image data
        image_array = []
        image_size = [
            -min_x + max_x,
            -min_y + max_y,
        ]
        
        test_img = Image.new("RGBA", image_size)

        for img, (w, h), (x, y) in image_data:
            img_out = Image.new("RGBA", image_size)

            if img is not None:
                img_raw = Image.frombytes("RGBA", (w, h), img)

                x_out = -x - min_x
                y_out = max_y - y

                img_out.paste(img_raw, (x_out, y_out), img_raw)

            image_array.append(img_out)
            test_img.alpha_composite(img_out)
        
        # crop the gif to smallest size
        crop = test_img.getbbox()

        for i, image in enumerate(image_array):
            image_array[i] = image.crop(crop)
        
        # export the file
        if file_filter == "GIF files (*.gif)":
            disposal = 2
            # 50 fps, 25 fps
            advance_spd = [20, 40][framerate]
        else:
            disposal = 0
            # 60 fps, 30 fps
            advance_spd = [17, 33][framerate]
        image_array[0].save(
            path,
            save_all      = True,
            append_images = image_array[1:],
            optimize      = True,
            duration      = advance_spd,
            loop          = 0,
            disposal      = disposal,
        )

        self.setEnabled(True)
        QtWidgets.QApplication.restoreOverrideCursor()

        if self.success_jingle is None:
            QtWidgets.QApplication.beep()
        else:
            self.success_jingle.play()

        QtWidgets.QMessageBox.about(
            self,
            self.tr("ExportFileSuccessTitle"),
            self.tr("ExportFileSuccessBlurb").format(filename),
        )

        self.animation_timer.start()