import configparser
import math
import os
from functools import partial
from itertools import groupby

from PIL import Image
from PySide6 import QtWidgets, QtGui

from spritoglobin_dx.classes import ObjFile, InvalidObjectFileError
from spritoglobin_dx.constants import *
from spritoglobin_dx.gui import InteractiveGraphicsWindow, GraphicsAnimationTimeline


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
        self.choose_file_button.setIcon(self.parent.theme_icons['open'])
        self.choose_file_button.clicked.connect(self.import_obj_file)

        file_info_none_string = self.tr("FileInfoNone")
        self.file_info_text = QtWidgets.QLabel(f"\n{file_info_none_string}\n")
        self.file_info_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.sort_contents_toggle = QtWidgets.QCheckBox(self.tr("ImportAlphabetizeToggle"))
        self.sort_contents_toggle.setVisible(False)

        self.import_button = QtWidgets.QPushButton(self.tr("ImportAcceptButton"))
        self.import_button.setIcon(self.parent.theme_icons['sprito'])
        self.import_button.clicked.connect(self.finalize)
        self.import_button.setEnabled(False)

        layout.addWidget(self.choose_file_button, 0, 1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_info_text, 1, 0, 1, 3, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sort_contents_toggle, 2, 0, 1, 3, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.import_button, 3, 1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        # this does nothing but i'm keeping it here in case it randomly decides to work ever
        self.import_button.setFocus()

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
    def __init__(self, parent, current_window_icon, success_jingle, obj_data, renderer, use_low_framerate, initial_object, initial_animation, initial_color_anim):
        super().__init__()

        self.parent = parent
        self.obj_data = obj_data

        self.current_window_icon = current_window_icon
        self.success_jingle = success_jingle

        self.setWindowTitle(self.tr("ExportWindowTitle"))
        self.setWindowIcon(self.current_window_icon)

        self.renderer = renderer

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

        self.speed_controller = QtWidgets.QDoubleSpinBox()
        self.speed_controller.setRange(0.1, 100)
        self.speed_controller.setSingleStep(0.05)
        self.speed_controller.setDecimals(4)
        self.speed_controller.setValue(1)

        self.scale_controller = QtWidgets.QDoubleSpinBox()
        self.scale_controller.setRange(0.1, 100)
        self.scale_controller.setSingleStep(0.1)
        self.scale_controller.setDecimals(4)
        self.scale_controller.setValue(1)

        self.anim_list_box = QtWidgets.QListWidget()
        self.anim_list_box.currentRowChanged.connect(self.update_anim_options)

        self.add_button = QtWidgets.QPushButton()
        self.add_button.setIcon(self.parent.theme_icons['add'])
        self.add_button.clicked.connect(self.add_anim)

        self.remove_button = QtWidgets.QPushButton()
        self.remove_button.setIcon(self.parent.theme_icons['subtract'])
        self.remove_button.clicked.connect(self.remove_anim)

        self.move_up_button = QtWidgets.QPushButton()
        self.move_up_button.setIcon(self.parent.theme_icons['up'])
        self.move_up_button.clicked.connect(self.move_anim_up)

        self.move_down_button = QtWidgets.QPushButton()
        self.move_down_button.setIcon(self.parent.theme_icons['down'])
        self.move_down_button.clicked.connect(self.move_anim_down)

        self.anim_choose_list_box = QtWidgets.QComboBox()
        self.anim_choose_list_box.currentIndexChanged.connect(self.change_current_anim_data)

        self.loop_choose_spin_box = QtWidgets.QSpinBox()
        self.loop_choose_spin_box.setMinimum(1)
        self.loop_choose_spin_box.setMaximum(99)
        self.loop_choose_spin_box.valueChanged.connect(self.change_current_anim_data)

        self.export_button = QtWidgets.QPushButton(self.tr("ExportAcceptButton"))
        self.export_button.setIcon(self.parent.theme_icons['export'])
        self.export_button.clicked.connect(self.export_gif)

        mono_font = QtGui.QFont()
        mono_font.setFamily("Monospace")
        mono_font.setFixedPitch(True)

        self.gif_preview = InteractiveGraphicsWindow(
            parent = self.parent,
            font = mono_font,
            size = [514, 514],
            default_scale = 1,
            default_offset = [0.0, 0.0],
            min_scale = 0.5,
            max_scale = 16.0,
            grid_size = 32,
            renderer = self.renderer,
        )
        self.gif_preview.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.gif_preview.setMinimumWidth(514)
        self.gif_preview.setMinimumHeight(514)
        self.gif_preview.background_color = QtCore.Qt.transparent
        self.gif_preview.update_program_theme()

        self.gif_timer_text = QtWidgets.QLabel(f"{0:3} / {0:3}")
        self.gif_timer_text.setFont(mono_font)

        layout.addWidget(self.framerate_choose_box, 1, 0, 1, 2)
        layout.addWidget(self.color_anim_list_box, 1, 2, 1, 2)
        layout.addWidget(self.speed_controller, 3, 0, 1, 2)
        layout.addWidget(self.scale_controller, 3, 2, 1, 2)
        layout.addWidget(self.anim_list_box, 5, 0, 1, 4)
        layout.addWidget(self.add_button, 6, 0)
        layout.addWidget(self.remove_button, 6, 1)
        layout.addWidget(self.move_up_button, 6, 2)
        layout.addWidget(self.move_down_button, 6, 3)
        layout.addWidget(self.anim_choose_list_box, 10, 0, 1, 2)
        layout.addWidget(self.loop_choose_spin_box, 10, 2, 1, 2)
        layout.addWidget(self.export_button, 11, 0, 1, 4, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.gif_preview, 0, 4, 11, 1)
        layout.addWidget(self.gif_timer_text, 11, 4, alignment = QtCore.Qt.AlignmentFlag.AlignRight)

        string = QtWidgets.QLabel(self.tr("AnimationOptionFramerateTitle"))
        string.setBuddy(self.framerate_choose_box)
        string.setEnabled(False)
        layout.addWidget(string, 0, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationOptionColorAnimTitle"))
        string.setBuddy(self.color_anim_list_box)
        string.setEnabled(False)
        layout.addWidget(string, 0, 2, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationOptionSpeedTitle"))
        string.setBuddy(self.speed_controller)
        string.setEnabled(False)
        layout.addWidget(string, 2, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationOptionScaleTitle"))
        string.setBuddy(self.scale_controller)
        string.setEnabled(False)
        layout.addWidget(string, 2, 2, 1, 2)

        string = QtWidgets.QLabel(self.tr("ExportAnimationListTitle"))
        string.setBuddy(self.anim_list_box)
        string.setEnabled(False)
        layout.addWidget(string, 4, 0, 1, 4)

        string = QtWidgets.QLabel(self.tr("AnimationListDataCurrentAnim"))
        string.setBuddy(self.anim_choose_list_box)
        string.setEnabled(False)
        layout.addWidget(string, 9, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationListDataCurrentLoops"))
        string.setBuddy(self.loop_choose_spin_box)
        string.setEnabled(False)
        layout.addWidget(string, 9, 2, 1, 2)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line, 8, 0, 1, 4)

        self.setLayout(layout)
        self.export_button.setFocus()

        self.animation_timer = QtCore.QTimer(self)
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
        
        speed = self.speed_controller.value()

        advance_amt_adjusted = advance_amt * speed

        self.obj_data.increment_timers(advance_amt_adjusted, animation_timer = True, color_timer = True)
        
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

        scale = self.scale_controller.value()

        color_animation = -1
        if self.color_anim_list_box.currentIndex() != 0:
            color_animation = int(self.color_anim_list_box.currentText())
        
        img_data = self.obj_data.get_sprite_part_entities(
            object_name      = self.obj_data.cached_object.name, 
            animation_index  = anim,
            color_anim_index = color_animation,
        )
    
        base_sprite = [
            img_data,  # sprite parts list
            (0, 0, 0), # translation
            (0, 0, 0), # rotation
            (scale, scale, 1), # scale
        ]

        palette = self.obj_data.get_object_palette(
            object_name      = self.obj_data.cached_object.name, 
            animation_index  = anim,
            color_anim_index = color_animation,
        )

        fragment_light = [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]

        self.gif_preview.draw_3d_image([[base_sprite], palette, fragment_light])

        animation_properties = self.obj_data.get_animation_properties(
            object_name     = self.obj_data.cached_object.name,
            animation_index = anim,
        )
        
        total_time = animation_properties["length"]
        current_time = math.floor(self.obj_data.get_timers(color_timer = True)[0]) % total_time

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

        color_animation = -1
        if self.color_anim_list_box.currentIndex() != 0:
            color_animation = int(self.color_anim_list_box.currentText())

        framerate = self.framerate_choose_box.currentIndex()
        # 60 / 50 fps, 30 / 25 fps
        advance_amt = [ 1,  2][framerate]
        
        speed = self.speed_controller.value()
        scale = self.scale_controller.value()

        advance_amt_adjusted = advance_amt * speed
        
        self.obj_data.init_timers()

        # gather all the image data
        image_data = []
        min_x, max_x, min_y, max_y = 0, 0, 0, 0

        anim_list = []
        for key, group in groupby(self.current_anim_list, key = lambda x: x[0]):
            anim_list.append([key, sum(count for _, count in group)])

        for anim, count in anim_list:
            object_name = self.obj_data.cached_object.name

            self.obj_data.set_timers(0, animation_timer = True)

            animation_properties = self.obj_data.get_animation_properties(
                object_name     = object_name,
                animation_index = anim,
            )

            anim_length = animation_properties["length"] * count

            for i in range(math.ceil(anim_length / advance_amt_adjusted)):
                img, (w, h), (x, y) = self.obj_data.get_sprite_with_offset(
                    object_name      = object_name, 
                    animation_index  = anim,
                    color_anim_index = color_animation,
                    bypass_shader    = True,
                )

                if img is not None:
                    min_x, max_x, min_y, max_y = [
                        min(min_x, -x,    ), # left
                        max(max_x, -x + w,), # right
                        min(min_y,  y - h,), # down
                        max(max_y,  y,    ), # up
                    ]
                
                img = self.obj_data.get_sprite_part_entities(
                    object_name      = object_name, 
                    animation_index  = anim,
                    color_anim_index = color_animation,
                )
    
                base_sprite = [
                    img,  # sprite parts list
                    (0, 0, 0), # translation
                    (0, 0, 0), # rotation
                    (1, 1, 1), # scale
                ]

                palette = self.obj_data.get_object_palette(
                    object_name      = object_name, 
                    animation_index  = anim,
                    color_anim_index = color_animation,
                )

                fragment_light = [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]

                img = [[base_sprite], palette, fragment_light]

                image_data.append(img)

                self.obj_data.increment_timers(
                    advance_amt_adjusted,
                    animation_timer = True,
                    color_timer     = color_animation >= 0,
                )

        # compile the image data
        padding_amt = 3

        image_array = []
        image_size = [
            round((-min_x + max_x + (padding_amt * 2)) * scale),
            round((-min_y + max_y + (padding_amt * 2)) * scale),
        ]
        center = [
            ((-min_x) + padding_amt) * scale,
            ((-min_y) + padding_amt) * scale,
        ]

        self.renderer.resize(image_size)
        
        test_img = Image.new("RGBA", image_size)

        for img in image_data:
            img_out = Image.new("RGBA", image_size)

            img = self.renderer.render_object_scene(
                global_translation = (
                    float(center[0] / scale),
                    float(center[1] / scale),
                    -0.5),
                global_rotation = (
                    0,
                    0,
                    0),
                global_scale = (
                    float(scale),
                    float(scale),
                    1),
                img_data = img,
            )

            img_out = Image.frombytes("RGBA", image_size, img)

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

        self.gif_preview.resizeEvent()
        self.animation_timer.start()

    def ready_for_release(self):
        self.animation_timer.stop()
        self.animation_timer.deleteLater()



class ProgramThemeEditor(QtWidgets.QWidget):
    closed = QtCore.Signal()

    def __init__(self, parent, current_window_icon, renderer, default_colors, default_map, icon_path, graphics_window_bg, graphics_timeline_bg):
        super().__init__()

        self.parent = parent

        self.current_window_icon = current_window_icon

        self.setWindowTitle(self.tr("ThemeWindowTitle"))
        self.setWindowIcon(self.current_window_icon)
        self.setWindowFlag(QtCore.Qt.CustomizeWindowHint, True)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, False)

        self.theme_colors = list(default_colors)
        self.icon_path = icon_path

        layout = QtWidgets.QGridLayout()

        color_buttons = QtWidgets.QWidget()
        color_buttons_layout = QtWidgets.QHBoxLayout(color_buttons)
        color_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.color_buttons = []
        for i in range(4):
            button = QtWidgets.QPushButton()
            button.setText("#000000")
            button.clicked.connect(partial(self.set_theme_color, i))
            color_buttons_layout.addWidget(button)
            self.color_buttons.append(button)

        preset_buttons = QtWidgets.QWidget()
        preset_buttons_layout = QtWidgets.QGridLayout(preset_buttons)
        preset_buttons_layout.setContentsMargins(0, 0, 0, 0)

        self.map_colors_toggle = QtWidgets.QCheckBox(self.tr("ThemeMapColorsToggle"))
        self.map_colors_toggle.setChecked(default_map)
        self.map_colors_toggle.checkStateChanged.connect(self.set_colors)

        columns = 4
        for i, preset in enumerate(THEME_PRESETS):
            button = QtWidgets.QPushButton()

            icon_size = (52, 52)
            scale_factor = 1

            button.setIcon(self.parent.grab_theme_icon('img_presets_temp', i + 1, icon_size).transformed(QtGui.QTransform().scale(scale_factor, scale_factor)))
            button.setIconSize(QtCore.QSize(icon_size[0] * scale_factor, icon_size[1] * scale_factor))

            button.clicked.connect(partial(self.set_preset_colors, preset))
            preset_buttons_layout.addWidget(button, (i // columns), i % columns)

        global_palette = QtWidgets.QWidget()
        global_palette_layout = QtWidgets.QHBoxLayout(global_palette)
        global_palette_layout.setContentsMargins(0, 0, 0, 0)
        self.global_palette_labels = []

        palette_total = 4
        for i in range(palette_total):
            palette_label = QtWidgets.QLabel()
            palette_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, palette_label.sizePolicy().verticalPolicy())
            global_palette_layout.addWidget(palette_label)
            self.global_palette_labels.append(palette_label)

        # only one of them needs to be given this
        self.global_palette_labels[palette_total - 1].resizeEvent = self.redraw_global_palette

        button_icon_demo_frame = QtWidgets.QFrame()
        button_icon_demo_frame_layout = QtWidgets.QHBoxLayout(button_icon_demo_frame)
        button_icon_demo_frame_layout.setContentsMargins(6, 6, 6, 6)
        self.button_icon_demo = QtWidgets.QLabel()
        button_icon_demo_frame_layout.addWidget(self.button_icon_demo)

        button_icon_demo_frame.setFrameShape(QtWidgets.QFrame.Panel)
        button_icon_demo_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        button = QtWidgets.QPushButton()
        button_color = button.palette().color(QtGui.QPalette.Button).name()
        button_icon_demo_frame.setStyleSheet(f"background-color: {button_color};")
        button_icon_demo_frame.setAutoFillBackground(True)

        mono_font = QtGui.QFont()
        mono_font.setFamily("Monospace")
        mono_font.setFixedPitch(True)

        self.graphics_window_preview = InteractiveGraphicsWindow(
            parent = self,
            font = mono_font,
            size = [128, 128],
            default_scale = 2,
            default_offset = [0.0, 0.0],
            min_scale = 1.0,
            max_scale = 4.0,
            grid_size = 16,
            renderer = renderer,
        )
        self.graphics_window_preview.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.graphics_window_preview.setMinimumWidth(128)
        self.graphics_window_preview.setMinimumHeight(128)
        self.graphics_window_preview.background_color = graphics_window_bg
        self.graphics_window_preview.bounding_boxes = [[-8, 8, -8, 8]]
        self.graphics_window_preview.draw_image(self.parent.grab_theme_icon(self.icon_path, 1, (16, 16)).toImage(), (8, 8))

        self.graphics_timeline_preview = GraphicsAnimationTimeline(
            parent           = self,
            font             = mono_font,
            padding_amount   = 9,
            timeline_height  = 39,
            keyframe_padding = 6,
            playhead_height  = 8,
            minimal          = True,
        )
        self.graphics_timeline_preview.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.graphics_timeline_preview.layout.setContentsMargins(0, 0, 0, 0)
        self.graphics_timeline_preview.background_color = graphics_timeline_bg
        self.graphics_timeline_preview.update_timeline(
            length    = 32,
            keyframes = [0, 8, 16, 24],
        )
        self.graphics_timeline_preview.play_button.setEnabled(True)
        self.graphics_timeline_preview.stop_button.setEnabled(True)
        self.graphics_timeline_preview.playbackToggled.connect(self.toggle_playback)
        self.graphics_timeline_preview.playbackStopped.connect(self.stop_playback)
        self.graphics_timeline_preview.timelineScrubbed.connect(self.set_animation_timer)

        self.graphics_timeline_preview.bounding_box_toggle.setVisible(True)
        self.graphics_timeline_preview.bounding_box_toggle_string.setVisible(True)
        self.graphics_timeline_preview.bounding_box_toggle.setEnabled(False)
        self.graphics_timeline_preview.bounding_box_toggle_string.setEnabled(False)
        self.graphics_timeline_preview.bounding_box_toggle.setChecked(True)

        self.accept_button = QtWidgets.QPushButton(self.tr("ThemeAcceptButton"))
        self.accept_button.clicked.connect(self.accept_theme)

        layout.addWidget(color_buttons, 1, 0, 1, 2)
        layout.addWidget(self.map_colors_toggle, 2, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(preset_buttons, 5, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(button_icon_demo_frame, 8, 0)
        layout.addWidget(self.graphics_window_preview, 8, 1)
        layout.addWidget(self.graphics_timeline_preview, 9, 0, 1, 2)
        layout.addWidget(global_palette, 10, 0, 1, 2)
        layout.addWidget(self.accept_button, 11, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)
        
        string = QtWidgets.QLabel(self.tr("ThemeSettingsTitle"))
        string.setEnabled(False)
        layout.addWidget(string, 0, 0, 1, 2)
        
        string = QtWidgets.QLabel(self.tr("ThemePresetsTitle"))
        string.setEnabled(False)
        layout.addWidget(string, 4, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("ThemePreviewTitle"))
        string.setEnabled(False)
        layout.addWidget(string, 7, 0, 1, 2)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line, 3, 0, 1, 2)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line, 6, 0, 1, 2)

        self.setLayout(layout)

        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.setTimerType(QtCore.Qt.PreciseTimer)
        framerate = [60, 30][self.parent.settings["framerate"]]
        self.timer_advance = [1, 2][self.parent.settings["framerate"]]
        self.animation_timer.setInterval(round(1000 / framerate))
        self.animation_timer.timeout.connect(self.tick_timer)

        self.timeline_timer = 0

        self.prematurely_closed = True

        self.set_colors()

    def set_theme_color(self, color):
        chosen_color = QtWidgets.QColorDialog.getColor(self.theme_colors[color])
        if chosen_color.isValid():
            self.theme_colors[color] = chosen_color.name()
            self.set_colors()

    def set_preset_colors(self, preset):
        self.theme_colors = list(THEME_PRESETS[preset])
        self.map_colors_toggle.setChecked(True)
        self.set_colors()

    def set_colors(self):
        THEME_COLORS["M_COLOR_0"] = self.theme_colors[0]
        THEME_COLORS["L_COLOR_0"] = self.theme_colors[1]
        THEME_COLORS["K_COLOR_0"] = self.theme_colors[2]
        THEME_COLORS["P_COLOR_0"] = self.theme_colors[3]
        map_theme_colors = self.map_colors_toggle.isChecked()

        for i, button in enumerate(self.color_buttons):
            color = QtGui.QColor(self.theme_colors[i])

            r, g, b, _ = color.getRgbF()
            lum = (0.2126 * r + 0.7152 * g + 0.0722 * b)
            if lum > 0.5:
                text_color = "#000000"
            else:
                text_color = "#FFFFFF"

            button.setStyleSheet(f"QPushButton {{background-color: {color.name()}; color: {text_color};}}")
            button.setText(color.name())

        icon_demo = self.parent.grab_theme_icon(self.icon_path, 1, None, map_theme_colors = map_theme_colors)
        icon_demo = icon_demo.transformed(QtGui.QTransform().scale(2, 2))
        self.button_icon_demo.setPixmap(icon_demo)

        self.theme_icons = {
            'zoom_in':  self.parent.grab_theme_icon(self.icon_path, 3, (16, 16), map_theme_colors = map_theme_colors),
            'zoom_out': self.parent.grab_theme_icon(self.icon_path, 2, (16, 16), map_theme_colors = map_theme_colors),
            'reset':    self.parent.grab_theme_icon(self.icon_path, 4, (16, 16), map_theme_colors = map_theme_colors),
            'play':     self.parent.grab_theme_icon(self.icon_path, 5, (16, 16), map_theme_colors = map_theme_colors),
            'pause':    self.parent.grab_theme_icon(self.icon_path, 6, (16, 16), map_theme_colors = map_theme_colors),
            'stop':     self.parent.grab_theme_icon(self.icon_path, 7, (16, 16), map_theme_colors = map_theme_colors),
        }

        self.graphics_window_preview.update_program_theme()
        self.graphics_timeline_preview.update_program_theme()

        self.redraw_global_palette()

        palette_button_icon = self.parent.grab_theme_icon(self.icon_path, 8, (16, 16), map_theme_colors = map_theme_colors)
        self.accept_button.setIcon(palette_button_icon)

    def accept_theme(self):
        self.prematurely_closed = False
        self.close()

    def set_animation_timer(self, time):
        self.timeline_timer = time
        self.graphics_timeline_preview.set_time(self.timeline_timer)

    def toggle_playback(self, play):
        if play:
            self.animation_timer.start()
        else:
            self.animation_timer.stop()

    def stop_playback(self):
        self.animation_timer.stop()
        self.timeline_timer = 0
        self.graphics_timeline_preview.set_time(self.timeline_timer)

    def tick_timer(self):
        self.timeline_timer += self.timer_advance
        self.graphics_timeline_preview.set_time(self.timeline_timer)
    
    def redraw_global_palette(self, event = None):
        if event is None:
            width = 70
        else:
            width = event.size().width()

        global_palette_line_thickness = min(2, (width // 40) + 1)
        global_palette_size = ((width - (global_palette_line_thickness * 4)) // 2)

        size = global_palette_size
        thickness = global_palette_line_thickness
        color_label_base = QtGui.QPixmap((size * 2) + (thickness * 4), size + (thickness * 4))

        color_label_base.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(color_label_base)

        pen = QtGui.QPen()
        pen.setWidth(thickness)
        pen.setJoinStyle(QtCore.Qt.MiterJoin)
        qp.setPen(pen)

        pen.setColor(QtGui.QColor(THEME_COLORS["P_COLOR_0"]))
        qp.setPen(pen)
        qp.drawRect(thickness // 2, thickness // 2, (size * 2) + ((thickness * 4) - thickness), size + ((thickness * 4) - thickness))

        pen.setColor(QtGui.QColor(THEME_COLORS["WHITE"]))
        qp.setPen(pen)
        qp.drawRect(thickness + (thickness // 2), thickness + (thickness // 2), (size * 2) + ((thickness * 4) - (thickness * 3)), size + ((thickness * 4) - (thickness * 3)))

        qp.end()

        for i, label in enumerate(self.global_palette_labels):
            r, g, b, a = [
                [0x00, 0x00, 0x00, 0xFF],
                [0xFF, 0x00, 0x00, 0xAA],
                [0x00, 0xFF, 0x00, 0x55],
                [0x00, 0x00, 0xFF, 0x00],
                [0x00, 0xFF, 0xFF, 0xFF],
                [0xFF, 0x00, 0xFF, 0xAA],
                [0xFF, 0xFF, 0x00, 0x55],
                [0xFF, 0xFF, 0xFF, 0x00],
            ][i]

            qp = QtGui.QPainter(color_label_base)
            qp.fillRect(
                thickness * 2,
                thickness * 2,
                (color_label_base.width() // 2) - (thickness * 2),
                color_label_base.height() - (thickness * 4),
                QtGui.QBrush(QtGui.QColor(r, g, b))
            )
            qp.fillRect(
                color_label_base.width() // 2,
                thickness * 2,
                (color_label_base.width() // 2) - (thickness * 2),
                color_label_base.height() - (thickness * 4),
                QtGui.QBrush(QtGui.QColor(a, a, a))
            )
            qp.end()

            label.setPixmap(color_label_base)

    def ready_for_release(self):
        self.animation_timer.stop()
        self.animation_timer.deleteLater()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)