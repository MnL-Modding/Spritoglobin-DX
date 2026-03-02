import configparser
import importlib.metadata
import os
import re
import sys
import time
from importlib.metadata import PackageNotFoundError
from functools import partial

import numpy
import requests
from packaging.version import Version
from PIL import Image
from PySide6 import QtWidgets, QtGui, QtMultimedia

from spritoglobin_dx.classes import ObjFile, InvalidObjectFileError, GAME_IDS_THAT_USE_BOUNDING_BOXES
from spritoglobin_dx.constants import *
from spritoglobin_dx.scripts import create_transform_demo


def main():
    # Workaround for the app root directory sometimes
    # not being added to the module search path by Nuitka.
    # TODO: Remove this when this is fixed in Nuitka, or
    # https://github.com/Nuitka/Nuitka/issues/2965 is implemented.
    if '__compiled__' in globals():
        sys.path.append(str(SCRIPT_DIR.parent))

    app = QtWidgets.QApplication(sys.argv)

    if os.name == 'nt':
        app.setStyle('Fusion')

    window = MainWindow(app)
    window.adjustSize()

    screen_center = QtWidgets.QApplication.primaryScreen().availableGeometry().center()
    window_geometry = window.frameGeometry()
    window_geometry.moveCenter(screen_center)
    window.move(window_geometry.topLeft())
    
    window.show()
    window.check_for_updates(force = False)
    window.open_file()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()


def grab_icon(index):
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


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super(MainWindow, self).__init__()

        self.current_window_icon = QtGui.QIcon(str(FILES_DIR / 'ico_sprito_dx.ico'))

        self.setWindowIcon(self.current_window_icon)
        self.setWindowTitle("")

        self.success_jingle = QtMultimedia.QSoundEffect(self)
        self.success_jingle.setSource(QtCore.QUrl.fromLocalFile(FILES_DIR / "snd_success_dx.wav"))
        self.success_jingle.setVolume(0.3)

        self.parent = parent

        self.obj_data = None
        self.current_path = None
        self.current_game_id = None

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config = configparser.ConfigParser()
        if not (CONFIG_DIR / "config.ini").exists():

            config['UserPreferences'] = {}
            config['NavigationPaths'] = {}

            with open(CONFIG_DIR / "config.ini", "w") as config_file:
                config.write(config_file)

        config.read(str(CONFIG_DIR / "config.ini"))
        
        
        if not config.has_section('UserPreferences'):
            config['UserPreferences'] = {}
        self.settings = dict(config['UserPreferences'])

        self.change_lang(self.settings.get("language", "None"), reset_ui = False)
        self.set_framerate(int(self.settings.get("framerate", 1)), reset_ui = False)
        self.toggle_mute(self.settings.get("muted", False))
        self.toggle_update_check(self.settings.get("check_for_updates", None))
        


        if not config.has_section('NavigationPaths'):
            config['NavigationPaths'] = {}
        paths = dict(config['NavigationPaths'])

        config["NavigationPaths"]["obj_import_path"] = paths.get("obj_import_path", "")
        config["NavigationPaths"]["img_export_path"] = paths.get("img_export_path", "")

        
        config['UserPreferences'] = self.settings
        with open(CONFIG_DIR / "config.ini", "w") as config_file:
            config.write(config_file)


        self.init_ui()
    

    def check_for_updates(self, force = True):
        config = configparser.ConfigParser()
        config.read(str(CONFIG_DIR / "config.ini"))
        if not config.has_section('UpdateCheckSettings'):
            config['UpdateCheckSettings'] = {}
        update_config = dict(config['UpdateCheckSettings'])

        timestamp = float(update_config.get("timestamp", 0))

        minimum_interval = 80000 # roughly 22.2 hours
        too_often = time.time() - timestamp < minimum_interval

        # pre-bail if necessary
        if not (self.settings.get("check_for_updates", False) == "True" and not too_often) and not force:
            print("check_for_updates returned due to conditions prohibiting an automatic check")
            return

        # MOST OF THE FOLLOWING CODE WAS PROVIDED BY DIMIDIMIT, THE G.O.A.T.
        
        # get current version of app (poetry or compiled only)
        try:
            dist = importlib.metadata.distribution(APP_NAME)
        except PackageNotFoundError:
            print("check_for_updates returned due to PackageNotFoundError")
            return

        # get latest release on github
        repo_url = dict(x.split(', ', 1) for x in dist.metadata.get_all('Project-URL') or []).get('Repository')
        if repo_url is None:
            # `repository` is missing from pyproject.toml, abort
            print("check_for_updates returned due to lacking a repository value in pyproject.toml")
            return
        repo_match = re.fullmatch('https://github.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)', repo_url)
        if repo_match is None:
            # Repository URL is malformed or repository is not on GitHub. Since we've hardcoded only GitHub, abort
            print("check_for_updates returned due to bad GitHub link")
            return
        try:
            latest_release_resp = requests.get(f'https://api.github.com/repos/{repo_match.group('owner')}/{repo_match.group('repo')}/releases/latest', headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
            latest_release_resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Network error, or there are currently no releases in the repo
            if force:
                QtWidgets.QMessageBox.critical(
                    self,
                    self.tr("CheckUpdateErrorTitle"),
                    self.tr("CheckUpdateErrorBlurb").format(e),
                )
            return
        latest_release = latest_release_resp.json()

        # compare release versions and display a prompt
        latest_ver = Version(latest_release['tag_name'])
        current_ver = Version(dist.version)
        skip_ver = Version(update_config.get("ignore_version", dist.version))

        if latest_ver <= skip_ver and not force:
            pass
        elif latest_ver > current_ver:
            new_version_assurance_string = self.tr("CheckUpdateNewVersionAssurance")

            information_box = QtWidgets.QMessageBox(self)
            information_box.setTextFormat(QtCore.Qt.RichText)
            information_box.setWindowTitle(self.tr("CheckUpdateNewVersionTitle"))
            information_box.setText(self.tr("CheckUpdateNewVersionBlurb").format(
                f"<b>{latest_release['name']}</b>",
                latest_release['body'],
                f"<a href='{latest_release['html_url']}'>GitHub</a>.",
            ).replace("\n", "<br>") + f"<br><br><span style='color: rgb(127, 127, 127);'>{new_version_assurance_string}</span>")

            remind_button = QtWidgets.QPushButton(self.tr("CheckUpdateNewVersionRemindOption"))
            ignore_button = QtWidgets.QPushButton(self.tr("CheckUpdateNewVersionIgnoreOption"))

            information_box.addButton(remind_button, QtWidgets.QMessageBox.AcceptRole)
            information_box.addButton(ignore_button, QtWidgets.QMessageBox.ActionRole)

            information_box.exec()
            check = information_box.buttonRole(information_box.clickedButton()) == QtWidgets.QMessageBox.ActionRole
            if check:
                update_config["ignore_version"] = latest_ver
        elif force:
            QtWidgets.QMessageBox.information(
                self,
                self.tr("CheckUpdateUpToDateTitle"),
                self.tr("CheckUpdateUpToDateBlurb"),
            )

        update_config["timestamp"] = time.time()
        config['UpdateCheckSettings'] = update_config
        with open(CONFIG_DIR / "config.ini", "w") as config_file:
            config.write(config_file)


    def init_ui(self):
        self.menuBar().clear()
        menu_bar = self.menuBar()


        if self.obj_data is not None:
            self.setWindowTitle(f"{os.path.basename(self.current_path)} ({self.game_title_strings[f"GameTitle{self.current_game_id}"]})")

    
        menu_bar_file = menu_bar.addMenu(self.tr("MenuBarFileTitle"))

        menu_bar_file.addAction(
            grab_icon(14),
            self.tr("MenuBarFileOpenOption"),
            QtGui.QKeySequence.StandardKey.Open,
            self.open_file,
        )

        menu_bar_file.addAction(
            grab_icon(13),
            self.tr("MenuBarFileCloseOption"),
            QtGui.QKeySequence.StandardKey.Close,
            self.close_file,
        )

        menu_bar_file.addSeparator() # -----------------------------------------

        menu_bar_file.addAction(
            grab_icon(16),
            self.tr("MenuBarFileQuickExportOption"),
            QtGui.QKeySequence.StandardKey.Save,
            partial(self.export_file, True),
        )

        menu_bar_file.addAction(
            grab_icon(16),
            self.tr("MenuBarFileExportOption"),
            QtGui.QKeySequence.StandardKey.SaveAs,
            partial(self.export_file, False),
        )

        menu_bar_file.addSeparator() # -----------------------------------------

        menu_bar_file.addAction(
            grab_icon(15),
            self.tr("MenuBarFileQuitOption"),
            QtGui.QKeySequence.StandardKey.Quit,
            QtWidgets.QApplication.quit,
        )


        menu_bar_options = menu_bar.addMenu(self.tr("MenuBarOptionsTitle"))

        language_selector = QtWidgets.QMenu(self.tr("MenuBarOptionsLanguageOption"), self)
        for i, lang_key in enumerate(LANGUAGES):
            if not (LANG_DIR / f'{lang_key}.qm').exists() and not lang_key == "None": continue
            lang = LANGUAGES[lang_key]

            lang_string = lang[0]
            if lang_string is None:
                lang_string = self.tr("MenuBarOptionsLanguageSystem")

            #if lang[3]:
            #    lang_string += "⚠"

            if self.settings["language"] == lang_key:
                lang_string += " ✓"

            language_selector.addAction(
                QtGui.QIcon(str(LANG_DIR / f"{lang_key}.png")),
                lang_string,
                partial(self.change_lang, lang_key)
            )

        framerate_selector = QtWidgets.QMenu(self.tr("MenuBarOptionsFramerateOption"), self)
        self.framerate_options = []
        for i in range(2):
            string = [
                self.tr("MenuBarOptionsFramerate").format(60),
                self.tr("MenuBarOptionsFramerate").format(30),
            ][i]

            if self.settings["framerate"] == i: string += " ✓"

            framerate_action = QtGui.QAction(string)
            framerate_action.triggered.connect(partial(self.set_framerate, i))

            framerate_selector.addAction(framerate_action)
            self.framerate_options.append(framerate_action)

        audio_mute = QtGui.QAction(self.tr("MenuBarOptionsMuteOption"), self)
        audio_mute.setCheckable(True)
        audio_mute.setChecked(self.settings["muted"] == "True")
        audio_mute.toggled.connect(self.toggle_mute)

        check_updates = QtGui.QAction(self.tr("MenuBarOptionsCheckUpdatesOption"), self)
        check_updates.setCheckable(True)
        check_updates.setChecked(self.settings["check_for_updates"] == "True")
        check_updates.toggled.connect(self.toggle_update_check)
        
        menu_bar_options.addMenu(framerate_selector)
        menu_bar_options.addAction(audio_mute)
        menu_bar_options.addSeparator() # -----------------------------------------
        menu_bar_options.addMenu(language_selector)
        menu_bar_options.addAction(check_updates)

    
        menu_bar_help = menu_bar.addMenu(self.tr("MenuBarHelpTitle"))

        menu_bar_help.addAction(
            # grab_icon(14),
            self.tr("MenuBarHelpCheckUpdates"),
            self.check_for_updates,
        )

    
        mono_font = QtGui.QFont()
        mono_font.setFamily("Monospace")
        mono_font.setFixedPitch(True)

        self.obj_list_box = QtWidgets.QComboBox()
        self.obj_list_box.currentIndexChanged.connect(self.change_object)
        self.obj_list_box.setSizePolicy(QtWidgets.QSizePolicy.Preferred, self.obj_list_box.sizePolicy().verticalPolicy())
    
        self.anim_list_box = QtWidgets.QListWidget()
        self.anim_list_box.currentRowChanged.connect(self.change_animation)
        self.anim_list_box.setSizePolicy(QtWidgets.QSizePolicy.Ignored, self.anim_list_box.sizePolicy().verticalPolicy())
        self.anim_list_box.setItemDelegate(self.ItemDelegate())
        self.anim_list_box.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.sprite_viewer = self.InteractiveGraphicsWindow(
            font = mono_font,
            size = [513, 513],
            default_scale = 2,
            default_offset = [0.0, 0.0],
            min_scale = 0.5,
            max_scale = 16.0,
            grid_size = 32,
        )
        self.sprite_viewer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sprite_viewer.setMinimumWidth(513)
        self.sprite_viewer.setMinimumHeight(513)

        self.sprite_anim_timeline = self.GraphicsAnimationTimeline(
            font             = mono_font,
            padding_amount   = 9,
            timeline_height  = 39,
            keyframe_padding = 6,
            playhead_height  = 8,
        )
        self.sprite_anim_timeline.playbackToggled.connect(self.sprite_anim_toggle_playback)
        self.sprite_anim_timeline.playbackStopped.connect(self.sprite_anim_stop_playback)
        self.sprite_anim_timeline.boundingBoxToggled.connect(self.update_sprite_viewer)
        self.sprite_anim_timeline.timelineScrubbed.connect(self.set_animation_timer)

        self.sprite_color_anim_timeline = self.ColorAnimationTimeline(
            font             = mono_font,
            padding_amount   = 9,
            timeline_height  = 29,
            keyframe_padding = 2,
            playhead_height  = 8,
        )
        self.sprite_color_anim_timeline.playbackToggled.connect(self.sprite_color_anim_toggle_playback)
        self.sprite_color_anim_timeline.playbackStopped.connect(self.sprite_color_anim_stop_playback)
        self.sprite_color_anim_timeline.timelineScrubbed.connect(self.set_animation_timer)
        self.sprite_color_anim_timeline.setEnabled(False)

        self.global_color_anim_timeline = self.ColorAnimationTimeline(
            font             = mono_font,
            padding_amount   = 9,
            timeline_height  = 29,
            keyframe_padding = 2,
            playhead_height  = 8,
        )
        self.global_color_anim_timeline.playbackToggled.connect(self.color_anim_toggle_playback)
        self.global_color_anim_timeline.playbackStopped.connect(self.color_anim_stop_playback)
        self.global_color_anim_timeline.timelineScrubbed.connect(self.set_color_timer)
        self.global_color_anim_timeline.sendLayerPersistance.connect(self.change_global_color_persistance)
        self.global_color_anim_timeline.setEnabled(False)
    
        self.color_anim_list_box = QtWidgets.QListWidget()
        self.color_anim_list_box.setSizePolicy(QtWidgets.QSizePolicy.Ignored, self.color_anim_list_box.sizePolicy().verticalPolicy())
        self.color_anim_list_box.currentRowChanged.connect(self.change_global_color_data)
        self.color_anim_list_box.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.color_anim_list_box.setEnabled(False)

        self.animation_timer = QtCore.QTimer()
        self.animation_timer.setTimerType(QtCore.Qt.PreciseTimer)
        framerate = [60, 30][self.settings["framerate"]]
        self.animation_timer.setInterval(round(1000 / framerate))
        self.animation_timer.timeout.connect(self.tick_timer)

        object_info = QtWidgets.QFrame()
        #object_info.setFrameShape(QtWidgets.QFrame.StyledPanel)
        #object_info.setFrameShadow(QtWidgets.QFrame.Raised)
        object_info_layout = QtWidgets.QGridLayout(object_info)
        object_info_layout.setContentsMargins(0, 0, 0, 0)

        self.color_mode_info_text = QtWidgets.QLabel()
        object_info_layout.addWidget(self.color_mode_info_text)
        self.color_mode_info_text.setVisible(False)

        self.object_bounding_box_enable = QtWidgets.QCheckBox(self.tr("ShowBoundingBoxToggle"))
        self.object_bounding_box_enable.checkStateChanged.connect(self.update_sprite_viewer)
        object_info_layout.addWidget(self.object_bounding_box_enable)

        QtWidgets.QApplication.styleHints().colorSchemeChanged.connect(self.set_theme)



        string = QtWidgets.QLabel(self.tr("ColorAnimSelectorTitle"))
        string.setBuddy(self.color_anim_list_box)
        string.setEnabled(False)

        global_color_anim = QtWidgets.QWidget()
        global_color_anim_layout = QtWidgets.QGridLayout(global_color_anim)
        global_color_anim_layout.setColumnStretch(0, 1)
        global_color_anim_layout.setColumnStretch(1, 10)

        global_color_anim_layout.addWidget(self.color_anim_list_box, 1, 0)
        global_color_anim_layout.addWidget(string, 0, 0)
        global_color_anim_layout.addWidget(self.global_color_anim_timeline, 0, 1, 2, 1)
        self.global_color_anim_timeline.layout.setContentsMargins(0, 0, 0, 0)

        pal_icon = grab_icon(8)
        pal_icon = pal_icon.toImage()
        gray_pal_icon = pal_icon.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
        gray_pal_icon = gray_pal_icon.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        gray_pal_icon.setAlphaChannel(pal_icon.convertToFormat(QtGui.QImage.Format.Format_Alpha8))
        gray_pal_icon = QtGui.QPixmap.fromImage(gray_pal_icon)

        self.timeline_tabs = QtWidgets.QTabWidget()
        self.timeline_tabs.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.timeline_tabs.setMinimumWidth(320)
        self.timeline_tabs.setTabPosition(QtWidgets.QTabWidget.South)
        self.timeline_tabs.addTab(self.sprite_anim_timeline, grab_icon(1), self.tr("AnimationTabsSpriteAnimTitle"))
        self.timeline_tabs.addTab(self.sprite_color_anim_timeline, gray_pal_icon, self.tr("AnimationTabsSpriteColorAnimTitle"))
        self.timeline_tabs.addTab(global_color_anim, gray_pal_icon, self.tr("AnimationTabsSpriteGlobalAnimTitle"))
        self.timeline_tabs.setAutoFillBackground(True)



        sprite_part_info = QtWidgets.QFrame()
        sprite_part_info.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sprite_part_info_layout = QtWidgets.QGridLayout(sprite_part_info)
        sprite_part_info_layout.setContentsMargins(0, 0, 0, 0)

        self.sprite_part_set_list_box = QtWidgets.QComboBox()
        self.sprite_part_set_list_box.currentIndexChanged.connect(self.change_sprite_parts)
        self.sprite_part_set_list_box.setSizePolicy(QtWidgets.QSizePolicy.Preferred, self.sprite_part_set_list_box.sizePolicy().verticalPolicy())
        sprite_part_info_layout.addWidget(self.sprite_part_set_list_box, 1, 0, 1, -1)

        string = QtWidgets.QLabel(self.tr("SpritePartSetSelectorTitle"))
        string.setBuddy(self.sprite_part_set_list_box)
        string.setEnabled(False)
        sprite_part_info_layout.addWidget(string, 0, 0, 1, -1)

        self.sprite_part_viewer = self.InteractiveGraphicsWindow(
            font = mono_font,
            size = [255, 255],
            default_scale = 1,
            default_offset = [0.0, 0.0],
            min_scale = 0.5,
            max_scale = 8.0,
            grid_size = 32,
        )
        self.sprite_part_viewer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sprite_part_viewer.setMinimumWidth(255)
        self.sprite_part_viewer.setMinimumHeight(255)
        sprite_part_info_layout.addWidget(self.sprite_part_viewer, 2, 0, 1, -1)

        self.sprite_part_list_box = QtWidgets.QComboBox()
        self.sprite_part_list_box.currentIndexChanged.connect(self.change_highlighted_sprite_part)
        self.sprite_part_list_box.setSizePolicy(QtWidgets.QSizePolicy.Preferred, self.sprite_part_list_box.sizePolicy().verticalPolicy())
        sprite_part_info_layout.addWidget(self.sprite_part_list_box, 4, 0, 1, -1)

        string = QtWidgets.QLabel(self.tr("SpritePartSelectorTitle"))
        string.setBuddy(self.sprite_part_list_box)
        string.setEnabled(False)
        sprite_part_info_layout.addWidget(string, 3, 0, 1, -1)

        self.sprite_part_graphics_buffer_info_text = QtWidgets.QLabel()
        sprite_part_info_layout.addWidget(self.sprite_part_graphics_buffer_info_text, 5, 0, 1, -1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        self.sprite_part_info_text = QtWidgets.QLabel()
        sprite_part_info_layout.addWidget(self.sprite_part_info_text, 6, 0)
        
        tile_viewer_size = (64 * 2) + 8
        self.sprite_part_tile_viewer = self.InteractiveGraphicsWindow(
            font = mono_font,
            size = [tile_viewer_size, tile_viewer_size],
            default_scale = 2,
            default_offset = [0.0, 0.0],
            min_scale = 2.0,
            max_scale = 2.0,
            grid_size = None,
            disable_controls = True,
            even_center = True,
        )
        self.sprite_part_tile_viewer.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.sprite_part_tile_viewer.setFixedWidth(tile_viewer_size)
        self.sprite_part_tile_viewer.setFixedHeight(tile_viewer_size)
        sprite_part_info_layout.addWidget(self.sprite_part_tile_viewer, 6, 1)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        sprite_part_info_layout.addWidget(line, 7, 0, 1, 2)

        self.sprite_part_renderer_info_text = QtWidgets.QLabel()
        sprite_part_info_layout.addWidget(self.sprite_part_renderer_info_text, 8, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        string = QtWidgets.QLabel("Renderer/Lighting Data Display NYI")
        string.setEnabled(False)
        sprite_part_info_layout.addWidget(string, 9, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        padding = QtWidgets.QWidget()
        sprite_part_info_layout.addWidget(padding, 10, 0, 1, -1)
        padding.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        sprite_part_info_layout.setColumnStretch(0, 1)
        sprite_part_info_layout.setColumnStretch(1, 1)



        self.animation_timer_going = False
        self.color_timer_going = False



        main = QtWidgets.QWidget()
        main_layout = QtWidgets.QGridLayout(main)

        main_layout.addWidget(self.obj_list_box, 1, 0, 1, 2)
        main_layout.addWidget(object_info, 2, 0, 1, 2)
        main_layout.addWidget(self.anim_list_box, 5, 0, 1, 2)
        main_layout.addWidget(self.sprite_viewer, 0, 2, 6, 1)
        main_layout.addWidget(self.timeline_tabs, 6, 0, 1, 3)
        main_layout.addWidget(sprite_part_info, 0, 3, -1, 1)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)
        main_layout.setColumnStretch(2, 9)
        main_layout.setColumnStretch(3, 4)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addWidget(line, 3, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("ObjectSelectorTitle"))
        string.setBuddy(self.obj_list_box)
        string.setEnabled(False)
        main_layout.addWidget(string, 0, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationSelectorTitle"))
        string.setBuddy(self.anim_list_box)
        string.setEnabled(False)
        main_layout.addWidget(string, 4, 0, 1, 1)

        self.global_animation_icon = QtWidgets.QLabel()
        self.global_animation_icon.setPixmap(grab_icon(0))
        main_layout.addWidget(self.global_animation_icon, 4, 1, 1, 1, alignment = QtCore.Qt.AlignmentFlag.AlignRight)

        self.setCentralWidget(main)
        self.set_theme(update = False)


        # Space = Play/Pause Animation Timeline
        action = QtGui.QAction(self)
        action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space))
        action.triggered.connect(self.timeline_toggle_playback)
        self.addAction(action)

        # Shift+Space = Play/Pause Color Animation Timeline
        action = QtGui.QAction(self)
        action.setShortcut(QtGui.QKeySequence(QtCore.Qt.ShiftModifier | QtCore.Qt.Key_Space))
        action.triggered.connect(self.color_timeline_toggle_playback)
        self.addAction(action)


        self.change_file()
    

    def open_file(self):
        self.animation_timer.stop()

        import_window = self.FileImportWindow(self, self.game_title_strings, self.current_window_icon)
        if not import_window.prevent_open:
            import_window.exec()
            
        self.animation_timer.start()

        if import_window.prematurely_closed:
            return

        self.current_path = import_window.current_path
        self.current_game_id = import_window.current_game_id
        sort_contents = import_window.sort_contents

        with open(self.current_path, 'rb') as obj_in:
            self.obj_data = ObjFile(obj_in.read(), self.current_game_id)

        self.setWindowTitle(f"{os.path.basename(self.current_path)} ({self.game_title_strings[f"GameTitle{self.current_game_id}"]})")
        self.change_file(sort_contents)

    def close_file(self):
        self.obj_data = None
        self.current_path = None
        self.current_game_id = None

        self.setWindowTitle("")
        self.change_file()

    def export_file(self, quick):
        if self.obj_data is None:
            QtWidgets.QMessageBox.critical(
                self,
                self.tr("ExportFailNoDataTitle"),
                self.tr("ExportFailNoDataBlurb"),
            )
            return
            
        self.animation_timer.stop()

        with open(self.current_path, 'rb') as obj_in:
            obj_data = ObjFile(obj_in.read(), self.current_game_id)

        if self.settings["muted"] == "True":
            success_jingle = None
        else:
            success_jingle = self.success_jingle
        
        export_window = self.GifExportWindow(
            parent              = self,
            current_window_icon = self.current_window_icon,
            success_jingle      = success_jingle,
            obj_data            = obj_data,
            use_low_framerate   = self.current_game_id in GAME_IDS_THAT_USE_LOW_FRAMERATE,
            initial_object      = self.obj_list_box.currentText(),
            initial_animation   = self.anim_list_box.currentRow(),
            initial_color_anim  = self.color_anim_list_box.currentRow(),
        )

        if quick:
            export_window.export_gif()
        else:
            export_window.exec()
            
        self.animation_timer.start()

    def write_config(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_DIR / "config.ini")
        config['UserPreferences'] = self.settings
        with open(CONFIG_DIR / "config.ini", "w") as config_file:
            config.write(config_file)
    
    def change_lang(self, lang_key, reset_ui = True):
        self.settings["language"] = lang_key

        if lang_key == "None":
            lang_key = QtCore.QLocale.system().name()
    
        default_path = QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.TranslationsPath)

        self.default_translator = QtCore.QTranslator()
        if self.default_translator.load(f"qtbase_{lang_key}.qm", default_path):
            QtCore.QCoreApplication.installTranslator(self.default_translator)
        else:
            self.default_translator.load(f"qt_{lang_key}.qm", default_path)
            QtCore.QCoreApplication.installTranslator(self.default_translator)

        self.translator_fallback = QtCore.QTranslator()
        if self.translator_fallback.load(str(LANG_DIR / 'en_US.qm')):
            self.parent.installTranslator(self.translator_fallback)

        self.translator = QtCore.QTranslator()
        if self.translator.load(str(LANG_DIR / f'{self.settings["language"]}.qm')):
            self.parent.installTranslator(self.translator)
        
        QtCore.QLocale.setDefault(QtCore.QLocale(lang_key))

        self.game_title_strings = {
            "GameTitleML1":  self.tr("GameTitleML1"),
            "GameTitleML2":  self.tr("GameTitleML2"),
            "GameTitleML3":  self.tr("GameTitleML3"),
            "GameTitleML4":  self.tr("GameTitleML4"),
            "GameTitleML5":  self.tr("GameTitleML5"),
            "GameTitleML1R": self.tr("GameTitleML1R"),
            "GameTitleML3R": self.tr("GameTitleML3R"),
        }

        self.write_config()

        if reset_ui:
            self.init_ui()
    
    def set_framerate(self, framerate, reset_ui = True):
        self.settings["framerate"] = framerate

        self.write_config()

        if reset_ui:
            framerate = [60, 30][self.settings["framerate"]]
            self.animation_timer.setInterval(round(1000 / framerate))

            for i, action in enumerate(self.framerate_options):
                string = [
                    self.tr("MenuBarOptionsFramerate").format(60),
                    self.tr("MenuBarOptionsFramerate").format(30),
                ][i]

                if self.settings["framerate"] == i: string += " ✓"

                action.setText(string)
    
    def toggle_mute(self, muted):
        self.settings["muted"] = str(muted)

        self.write_config()
    
    def toggle_update_check(self, check):
        if check is None:
            query_link_string = self.tr("CheckUpdateQueryLinkString")

            check_updates_box = QtWidgets.QMessageBox(self)
            check_updates_box.setTextFormat(QtCore.Qt.RichText)
            check_updates_box.setWindowTitle(self.tr("CheckUpdateQueryTitle"))
            check_updates_box.setText(self.tr("CheckUpdateQueryBlurb").format(
                f"<a href='https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement'>{query_link_string}</a>"
            ).replace("\n", "<br>"))
            check_updates_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

            check = check_updates_box.exec() == QtWidgets.QMessageBox.Yes

        self.settings["check_for_updates"] = str(check)

        self.write_config()

    
    def change_file(self, sort_contents = False):
        if self.obj_data is not None:
            self.obj_list_box.blockSignals(True)
            self.obj_list_box.clear()
            self.obj_list_box.blockSignals(False)
        

            game_id = self.obj_data.get_file_properties()["game_id"]

            self.object_bounding_box_enable.blockSignals(True)
            self.sprite_anim_timeline.bounding_box_toggle.blockSignals(True)

            if game_id in GAME_IDS_THAT_USE_BOUNDING_BOXES:
                self.object_bounding_box_enable.setVisible(True)
                self.sprite_anim_timeline.bounding_box_toggle.setVisible(True)
                self.sprite_anim_timeline.bounding_box_toggle_string.setVisible(True)
            else:
                self.object_bounding_box_enable.setChecked(False)
                self.object_bounding_box_enable.setVisible(False)
                self.sprite_anim_timeline.bounding_box_toggle.setChecked(False)
                self.sprite_anim_timeline.bounding_box_toggle.setVisible(False)
                self.sprite_anim_timeline.bounding_box_toggle_string.setVisible(False)
                self.sprite_viewer.bounding_boxes = []

            self.object_bounding_box_enable.blockSignals(False)
            self.sprite_anim_timeline.bounding_box_toggle.blockSignals(False)


            self.obj_data.init_timers()

            cellanims = list(self.obj_data.cellanim_files)
            if sort_contents: cellanims = sorted(cellanims)

            for cellanim in cellanims:
                self.obj_list_box.addItem(self.obj_data.cellanim_files[cellanim].name)
        else:
            self.obj_list_box.clear()

            self.object_bounding_box_enable.setChecked(False)
            self.object_bounding_box_enable.setVisible(False)
            self.sprite_anim_timeline.bounding_box_toggle.setChecked(False)
            self.sprite_anim_timeline.bounding_box_toggle.setVisible(False)
            self.sprite_anim_timeline.bounding_box_toggle_string.setVisible(False)

            self.change_highlighted_sprite_part()

        self.anim_list_box.setCurrentRow(0)

        if self.color_timer_going:
            self.color_anim_list_box.setCurrentRow(1)
        else:
            self.color_anim_list_box.setCurrentRow(0)

        if self.current_game_id in GAME_IDS_THAT_ARE_ON_3DS or self.current_game_id is None:
            self.current_window_icon = QtGui.QIcon(str(FILES_DIR / 'ico_sprito_dx.ico'))
            self.success_jingle.setSource(QtCore.QUrl.fromLocalFile(FILES_DIR / "snd_success_dx.wav"))
        else:
            self.current_window_icon = QtGui.QIcon(str(FILES_DIR / 'ico_sprito.ico'))
            self.success_jingle.setSource(QtCore.QUrl.fromLocalFile(FILES_DIR / "snd_success.wav"))

        self.setWindowIcon(self.current_window_icon)
    
    def change_object(self):
        if self.obj_data is None:
            pal_icon = grab_icon(8)
            pal_icon = pal_icon.toImage()
            gray_pal_icon = pal_icon.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
            gray_pal_icon = gray_pal_icon.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
            gray_pal_icon.setAlphaChannel(pal_icon.convertToFormat(QtGui.QImage.Format.Format_Alpha8))
            gray_pal_icon = QtGui.QPixmap.fromImage(gray_pal_icon)

            self.animation_timer.stop()
            self.anim_list_box.clear()
            self.color_mode_info_text.setVisible(False)
            self.sprite_part_set_list_box.clear()
            self.update_sprite_viewer(force = True)
            self.timeline_tabs.setTabIcon(2, gray_pal_icon)
            self.global_color_anim_timeline.setEnabled(False)
            self.global_animation_icon.setPixmap(grab_icon(0))
            
            self.color_anim_list_box.blockSignals(True)
            self.color_anim_list_box.clear()
            self.color_anim_list_box.blockSignals(False)
            self.color_anim_list_box.addItem(self.tr("ColorAnimSelectorNone"))
            self.color_anim_list_box.setEnabled(False)
            return

        # with open("test1.dat", "wb") as test:
        #     test.write(self.obj_data.cellanim_files[self.obj_list_box.currentText()].input_data)

        self.obj_data.cache_object(self.obj_list_box.currentText())


        self.anim_list_box.blockSignals(True)
        self.anim_list_box.clear()
        self.anim_list_box.blockSignals(False)

        object_properties = self.obj_data.get_object_properties(object_name = self.obj_list_box.currentText())


        self.color_anim_list_box.blockSignals(True)
        self.color_anim_list_box.clear()

        self.color_anim_list_box.addItem(self.tr("ColorAnimSelectorNone"))

        for i in object_properties["color_data"].keys():
            self.color_anim_list_box.addItem(str(i))
        
        if self.color_timer_going:
            self.color_anim_list_box.setCurrentRow(1)
        else:
            self.color_anim_list_box.setCurrentRow(0)
        self.color_anim_list_box.blockSignals(False)

        self.obj_data.set_timers(0, color_timer = True)
        self.global_color_anim_timeline.set_time(0)

        pal_icon = grab_icon(8)
        if object_properties["has_color_data"]:
            self.global_animation_icon.setPixmap(pal_icon)
            self.timeline_tabs.setTabIcon(2, pal_icon)
        else:
            self.global_animation_icon.setPixmap(grab_icon(0))
            pal_icon = pal_icon.toImage()
            gray_pal_icon = pal_icon.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
            gray_pal_icon = gray_pal_icon.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
            gray_pal_icon.setAlphaChannel(pal_icon.convertToFormat(QtGui.QImage.Format.Format_Alpha8))
            gray_pal_icon = QtGui.QPixmap.fromImage(gray_pal_icon)
            self.timeline_tabs.setTabIcon(2, gray_pal_icon)

        self.global_color_anim_timeline.setEnabled(object_properties["has_color_data"])
        self.color_anim_list_box.setEnabled(object_properties["has_color_data"])


        for i in range(object_properties["animation_number"]):
            item = QtWidgets.QListWidgetItem(str(i))
            if self.obj_data.get_animation_properties(
                object_name     = self.obj_list_box.currentText(), 
                animation_index = i,
            )["has_color_data"]:
                item.setIcon(grab_icon(8))
            else:
                item.setIcon(grab_icon(0))
            self.anim_list_box.addItem(item)
        self.anim_list_box.setCurrentRow(0)


        self.obj_data.reset_timers()
        self.animation_timer.start()


        self.color_mode_info_text.setVisible(True)
        self.color_mode_info_text.setText(self.tr('ColorModeInfo').format(object_properties['color_mode'][0]))


        self.sprite_part_set_list_box.blockSignals(True)
        self.sprite_part_set_list_box.clear()
        self.sprite_part_set_list_box.blockSignals(False)


        sprite_part_sets = []
        for i in range(object_properties["animation_number"]):
            animation_properties = self.obj_data.get_animation_properties(
                object_name     = self.obj_list_box.currentText(), 
                animation_index = i,
            )
            for j in range(animation_properties["total_frames"]):
                frame_properties = self.obj_data.get_frame_properties(
                    object_name     = self.obj_list_box.currentText(), 
                    animation_index = i,
                    frame_index     = j,
                )
                sprite_part_set = [frame_properties["first_part"], frame_properties["total_parts"]]
                if sprite_part_set not in sprite_part_sets and frame_properties["total_parts"] > 0: sprite_part_sets.append(sprite_part_set)
            
        self.all_sprite_part_sets = sorted(sprite_part_sets)

        for sprite_part_set in self.all_sprite_part_sets:
            if sprite_part_set[1] == 1:
                self.sprite_part_set_list_box.addItem(f"{sprite_part_set[0]}")
            else:
                self.sprite_part_set_list_box.addItem(f"{sprite_part_set[0]} - {sum(sprite_part_set) - 1}")
    
    def change_animation(self):
        if self.obj_data is None:
            pal_icon = grab_icon(8)
            pal_icon = pal_icon.toImage()
            gray_pal_icon = pal_icon.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
            gray_pal_icon = gray_pal_icon.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
            gray_pal_icon.setAlphaChannel(pal_icon.convertToFormat(QtGui.QImage.Format.Format_Alpha8))
            gray_pal_icon = QtGui.QPixmap.fromImage(gray_pal_icon)

            self.sprite_anim_timeline.update_timeline()
            self.sprite_color_anim_timeline.send_color_data()
            self.timeline_tabs.setTabIcon(1, gray_pal_icon)
            self.sprite_color_anim_timeline.setEnabled(False)
            self.timeline_tabs.setTabIcon(2, gray_pal_icon)
            self.global_color_anim_timeline.setEnabled(False)

            self.color_anim_list_box.setEnabled(False)
            return

        self.obj_data.set_timers(0, animation_timer = True)

        animation_properties = self.obj_data.get_animation_properties(
            object_name     = self.obj_list_box.currentText(), 
            animation_index = self.anim_list_box.currentRow(),
        )

        self.sprite_anim_timeline.update_timeline(
            length    = animation_properties["length"],
            keyframes = animation_properties["keyframes"],
        )

        color_data = animation_properties["color_data"].get(self.anim_list_box.currentRow(), None)
        if color_data is not None:
            self.sprite_color_anim_timeline.send_color_data(
                layer_amt      = len(color_data),
                keyframes      = [layer_data[0] for layer_data in color_data],
                render_channel = [layer_data[1] for layer_data in color_data],
                is_persistant  = [layer_data[2] for layer_data in color_data],
                length         = [layer_data[3] for layer_data in color_data],
                parent_length  = animation_properties["length"],
            )
        else:
            self.sprite_color_anim_timeline.send_color_data()

        pal_icon = grab_icon(8)
        if animation_properties["has_color_data"]:
            self.timeline_tabs.setTabIcon(1, pal_icon)
        else:
            pal_icon = pal_icon.toImage()
            gray_pal_icon = pal_icon.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
            gray_pal_icon = gray_pal_icon.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
            gray_pal_icon.setAlphaChannel(pal_icon.convertToFormat(QtGui.QImage.Format.Format_Alpha8))
            gray_pal_icon = QtGui.QPixmap.fromImage(gray_pal_icon)
            self.timeline_tabs.setTabIcon(1, gray_pal_icon)
            
        self.sprite_color_anim_timeline.setEnabled(animation_properties["has_color_data"])

        self.change_global_color_data(reset_timer = False)
    
    def change_global_color_data(self, reset_timer = True):
        if self.obj_data is None:
            self.global_color_anim_timeline.send_color_data()
            return

        object_properties = self.obj_data.get_object_properties(
            object_name = self.obj_list_box.currentText()
        )

        animation_properties = self.obj_data.get_animation_properties(
            object_name     = self.obj_list_box.currentText(), 
            animation_index = self.anim_list_box.currentRow(),
        )

        color_anim_index = -1
        if self.color_anim_list_box.currentRow() != 0 and object_properties["has_color_data"] and self.color_anim_list_box.currentItem() is not None:
            color_anim_index = int(self.color_anim_list_box.currentItem().text())
        
        color_data = object_properties["color_data"].get(color_anim_index, None)
        if color_data is not None:
            self.global_color_anim_timeline.send_color_data(
                layer_amt      = len(color_data),
                keyframes      = [layer_data[0] for layer_data in color_data],
                render_channel = [layer_data[1] for layer_data in color_data],
                is_persistant  = [layer_data[2] for layer_data in color_data],
                length         = [layer_data[3] for layer_data in color_data],
                parent_length  = animation_properties["length"],
            )
        else:
            self.global_color_anim_timeline.send_color_data()
        
        if reset_timer:
            self.obj_data.set_timers(0, color_timer = True)
            self.global_color_anim_timeline.set_time(0)
        
        self.update_sprite_viewer(force = True)
    
    def change_global_color_persistance(self, persistant):
        self.global_color_anim_timeline.use_alt_timer = not persistant


    def update_sprite_viewer(self, force = True):
        if self.obj_data is None:
            self.sprite_viewer.draw_image(None, (0, 0))
            self.sprite_viewer.bounding_boxes = []
            self.sprite_anim_timeline.send_frame_data()
            self.sprite_anim_timeline.set_time(0)
            self.sprite_color_anim_timeline.send_color_data()
            self.sprite_color_anim_timeline.set_time(0)
            self.global_color_anim_timeline.send_color_data()
            self.global_color_anim_timeline.set_time(0)
            return
        
        object_properties = self.obj_data.get_object_properties(object_name = self.obj_list_box.currentText())

        color_anim_index = -1
        if self.color_anim_list_box.currentRow() != 0 and object_properties["has_color_data"] and self.color_anim_list_box.currentItem() is not None:
            color_anim_index = int(self.color_anim_list_box.currentItem().text())

        img, size, offset = self.obj_data.get_sprite_with_offset(
            object_name      = self.obj_list_box.currentText(), 
            animation_index  = self.anim_list_box.currentRow(),
            color_anim_index = color_anim_index,
        )

        bounding_boxes = []
        if self.sprite_anim_timeline.bounding_box_toggle.isChecked():
            box = self.obj_data.get_animation_properties(
                object_name     = self.obj_list_box.currentText(), 
                animation_index = self.anim_list_box.currentRow(),
            )["bounding_box"]
            bounding_boxes.append(box)

        if self.object_bounding_box_enable.isChecked():
            box = object_properties["bounding_box"]
            bounding_boxes.append(box)
        
        self.sprite_viewer.bounding_boxes = bounding_boxes

        if img is not None:
            self.sprite_viewer.draw_image(QtGui.QImage(img, *size, QtGui.QImage.Format_RGBA8888), offset)
        else:
            self.sprite_viewer.draw_image(None, (0, 0))

        frame_properties = self.obj_data.get_frame_properties(
            object_name     = self.obj_list_box.currentText(), 
            animation_index = self.anim_list_box.currentRow(),
        )

        self.sprite_anim_timeline.send_frame_data(
            current_parts          = (frame_properties["first_part"], frame_properties["total_parts"]),
            current_keyframe_timer = frame_properties["keyframe_timer"],
            current_matrix_index   = frame_properties["transform_index"],
            current_matrix         = frame_properties["transform"],
            current_matrix_inv     = frame_properties["transform_inverted"],
        )

        sprite_timer, color_timer = self.obj_data.get_timers(animation_timer = True, color_timer = True)
        self.sprite_anim_timeline.set_time(sprite_timer)
        self.sprite_color_anim_timeline.set_time(sprite_timer)

        if not self.global_color_anim_timeline.use_alt_timer:
            self.global_color_anim_timeline.set_time(color_timer)
        else:
            self.global_color_anim_timeline.set_time(sprite_timer)


    def change_sprite_parts(self):
        if self.obj_data is None:
            self.sprite_part_list_box.blockSignals(True)
            self.sprite_part_list_box.clear()
            self.sprite_part_list_box.blockSignals(False)
            return

        sprite_part_set = self.all_sprite_part_sets[self.sprite_part_set_list_box.currentIndex()]

        self.sprite_part_list_box.blockSignals(True)
        self.sprite_part_list_box.clear()

        self.sprite_part_list_box.addItem(self.tr("SpritePartSelectorNone"))
        [self.sprite_part_list_box.addItem(f"{sprite_part_set[0] + i}") for i in range(sprite_part_set[1])]
        self.sprite_part_list_box.blockSignals(False)

        self.change_highlighted_sprite_part()
    
    def change_highlighted_sprite_part(self):
        if self.obj_data is None:
            self.sprite_part_viewer.bounding_boxes = []
            self.sprite_part_viewer.draw_image(None, (0, 0))
            self.set_highlighted_sprite_part_info(None)
            self.sprite_part_tile_viewer.bounding_boxes = []
            self.sprite_part_tile_viewer.draw_image(None, (0, 0))
            return

        sprite_part_set = self.all_sprite_part_sets[self.sprite_part_set_list_box.currentIndex()]

        highlighted_part = None
        sprite_part_properties = None
        bounding_boxes = []
        if self.sprite_part_list_box.currentIndex() != 0:
            highlighted_part = self.sprite_part_list_box.currentIndex() - 1

            sprite_part_properties = self.obj_data.get_sprite_part_properties(
                object_name       = self.obj_list_box.currentText(), 
                sprite_part_index = sprite_part_set[0] + self.sprite_part_list_box.currentIndex() - 1,
            )
            (x, y), (w, h) = sprite_part_properties["offset"], sprite_part_properties["size"]
            bounding_boxes.append([
                x - (w // 2),
                x + (w // 2),
                y - (h // 2),
                y + (h // 2),
            ])
        self.sprite_part_viewer.bounding_boxes = bounding_boxes


        img, size, offset = self.obj_data.get_sprite_part_set_with_offset(
            object_name      = self.obj_list_box.currentText(), 
            first_part       = sprite_part_set[0],
            total_parts      = sprite_part_set[1],
            highlighted_part = highlighted_part,
        )
        
        self.sprite_part_viewer.draw_image(QtGui.QImage(img, *size, QtGui.QImage.Format_RGBA8888), offset)

        self.set_highlighted_sprite_part_info(sprite_part_properties)

        bounding_boxes = []
        if self.sprite_part_list_box.currentIndex() != 0:
            img, size = self.obj_data.get_sprite_part_graphic(
                object_name       = self.obj_list_box.currentText(), 
                sprite_part_index = sprite_part_set[0] + self.sprite_part_list_box.currentIndex() - 1,
            )

            (x, y), (w, h) = (0, 0), size
            bounding_boxes.append([
                x - (w // 2),
                x + (w // 2),
                y - (h // 2),
                y + (h // 2),
            ])

        self.sprite_part_tile_viewer.bounding_boxes = bounding_boxes

        if self.sprite_part_list_box.currentIndex() != 0:
            self.sprite_part_tile_viewer.draw_image(QtGui.QImage(img, *size, QtGui.QImage.Format_RGBA8888), (size[0] // 2, size[1] // 2))
        else:
            self.sprite_part_tile_viewer.draw_image(None, (0, 0))
    
    def set_highlighted_sprite_part_info(self, sprite_part_properties):
        if sprite_part_properties is not None:
            self.sprite_part_graphics_buffer_info_text.setEnabled(True)

            object_properties = self.obj_data.get_object_properties(object_name = self.obj_list_box.currentText())
            buf_off = sprite_part_properties["buffer_offset"] * 128
            buf_size = (sprite_part_properties["size"][0] * sprite_part_properties["size"][1])
            buf_size *= object_properties["color_mode"][1] / 8
            buf_size = round(buf_size)

            buffer_offset = (
                f"{buf_off:06X}",
                f"{(buf_off + buf_size):06X}",
            )
        else:
            self.sprite_part_graphics_buffer_info_text.setEnabled(False)

            buffer_offset = ("?", "?")
        
        self.sprite_part_graphics_buffer_info_text.setText(self.tr("SpritePartBufferOffset").format(*buffer_offset))

        string = ""

        if sprite_part_properties is not None:
            self.sprite_part_info_text.setEnabled(True)

            size = [self.tr("SpritePartSize0"), self.tr("SpritePartSize1"), self.tr("SpritePartSize2"), self.tr("SpritePartSize3")][sprite_part_properties["oam_size"]]
            shape = [self.tr("SpritePartShape0"), self.tr("SpritePartShape1"), self.tr("SpritePartShape2")][sprite_part_properties["oam_shape"]]
            px_size = sprite_part_properties["size"]
            h_flip = sprite_part_properties["horizontal_flip"] # TODO
            v_flip = sprite_part_properties["vertical_flip"] # TODO
            offset = sprite_part_properties["offset"]
        else:
            self.sprite_part_info_text.setEnabled(False)

            size = "?"
            shape = "?"
            px_size = ("?", "?")
            h_flip = "?"
            v_flip = "?"
            offset = ("?", "?")

        string += self.tr("SpritePartSizeTitle").format(size)
        string += "\n"
        string += self.tr("SpritePartShapeTitle").format(shape)
        string += "\n"
        string += self.tr("SpritePartSizePixels").format(*px_size)
        string += "\n\n"
        string += self.tr("SpritePartFlipHorizontal").format(h_flip)
        string += "\n"
        string += self.tr("SpritePartFlipVertical").format(v_flip)
        string += "\n\n"
        string += self.tr("SpritePartOffset").format(*offset)

        self.sprite_part_info_text.setText(string)


        string = ""

        if sprite_part_properties is not None:
            self.sprite_part_renderer_info_text.setEnabled(True)

            renderer_index = sprite_part_properties["renderer_index"]
        else:
            self.sprite_part_renderer_info_text.setEnabled(False)

            renderer_index = "?"

        string += self.tr("SpritePartRendererTitle").format(renderer_index)

        self.sprite_part_renderer_info_text.setText(string)


    def tick_timer(self):
        if not self.animation_timer_going and not self.color_timer_going:
            return

        timer_delta = [1, 2][self.settings["framerate"]]
        self.obj_data.increment_timers(timer_delta,
            animation_timer = self.animation_timer_going,
            color_timer     = self.color_timer_going,
        )

        self.update_sprite_viewer(force = True)
    
    def timeline_toggle_playback(self):
        self.sprite_color_anim_timeline.toggle_playback()

    def set_animation_timer(self, time):
        self.obj_data.set_timers(time, animation_timer = True)

        self.update_sprite_viewer(force = True)
    
    def sprite_anim_toggle_playback(self, play):
        if play:
            self.animation_timer_going = True
            self.sprite_color_anim_timeline.playing = True
            self.sprite_color_anim_timeline.play_button.setIcon(grab_icon(6))
        else:
            self.animation_timer_going = False
            self.sprite_color_anim_timeline.playing = False
            self.sprite_color_anim_timeline.play_button.setIcon(grab_icon(5))
    
    def sprite_anim_stop_playback(self):
        self.animation_timer_going = False
        self.obj_data.set_timers(0, animation_timer = True)

        self.sprite_color_anim_timeline.playing = False
        self.sprite_color_anim_timeline.play_button.setIcon(grab_icon(5))

        self.sprite_anim_timeline.set_time(0)
        self.sprite_color_anim_timeline.set_time(0)

        self.update_sprite_viewer(force = True)
    
    def sprite_color_anim_toggle_playback(self, play):
        if play:
            self.animation_timer_going = True
            self.sprite_anim_timeline.playing = True
            self.sprite_anim_timeline.play_button.setIcon(grab_icon(6))
        else:
            self.animation_timer_going = False
            self.sprite_anim_timeline.playing = False
            self.sprite_anim_timeline.play_button.setIcon(grab_icon(5))
    
    def sprite_color_anim_stop_playback(self):
        self.animation_timer_going = False
        self.obj_data.set_timers(0, animation_timer = True)

        self.sprite_anim_timeline.playing = False
        self.sprite_anim_timeline.play_button.setIcon(grab_icon(5))

        self.sprite_anim_timeline.set_time(0)
        self.sprite_color_anim_timeline.set_time(0)

        self.update_sprite_viewer(force = True)


    def color_timeline_toggle_playback(self):
        if self.color_anim_list_box.currentRow() == 0 and self.color_anim_list_box.count() > 1:
            self.color_anim_list_box.setCurrentRow(1)

        self.global_color_anim_timeline.toggle_playback()

    def set_color_timer(self, time):
        self.obj_data.set_timers(time, color_timer = True)

        self.update_sprite_viewer(force = True)
    
    def color_anim_toggle_playback(self, play):
        if play:
            self.color_timer_going = True
        else:
            self.color_timer_going = False
    
    def color_anim_stop_playback(self):
        self.color_timer_going = False
        self.obj_data.set_timers(0, color_timer = True)

        self.global_color_anim_timeline.set_time(0)

        self.update_sprite_viewer(force = True)


    def set_theme(self, update = True):
        self.parent.setPalette(self.parent.palette()) # fixes some race conditions

        dark = self.parent.styleHints().colorScheme() == QtCore.Qt.ColorScheme.Dark
        if dark: background_color = QtCore.Qt.GlobalColor.gray
        else:    background_color = QtCore.Qt.GlobalColor.lightGray

        self.sprite_viewer.background_color = background_color
        if update: self.sprite_viewer.update_image()
        self.sprite_part_viewer.background_color = background_color
        if update: self.sprite_part_viewer.update_image()
        self.sprite_part_tile_viewer.background_color = background_color
        if update: self.sprite_part_tile_viewer.update_image()

        
        tabs_palette = QtWidgets.QTabWidget().palette()
        if dark: tabs_palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QPalette().color(QtGui.QPalette.ColorRole.Dark))
        else:    tabs_palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QPalette().color(QtGui.QPalette.ColorRole.Light))
        self.timeline_tabs.setPalette(tabs_palette)


        self.sprite_anim_timeline.background_color = background_color
        if update: self.sprite_anim_timeline.draw_full()
        self.sprite_color_anim_timeline.background_color = background_color
        if update: self.sprite_color_anim_timeline.draw_full()
        self.global_color_anim_timeline.background_color = background_color
        if update: self.global_color_anim_timeline.draw_full()



    class ItemDelegate(QtWidgets.QStyledItemDelegate):
        def paint(self, painter, option, index):
            option.decorationPosition = QtWidgets.QStyleOptionViewItem.Right
            super().paint(painter, option, index)



    class InteractiveGraphicsWindow(QtWidgets.QLabel):
        background_color = QtCore.Qt.GlobalColor.black

        def __init__(self, font, size, default_scale, default_offset, min_scale, max_scale, grid_size, disable_controls = False, even_center = False):
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

            self.img = None
            self.reset_view()
        
        def resizeEvent(self, event):
            size = event.size()
            self.resize([size.width(), size.height()])
        
        def mousePressEvent(self, event):
            if self.disable_controls: return

            if event.buttons() & QtCore.Qt.LeftButton:
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
                    pen_width = 1
                    offset_correction = 1

                for i in range(-((self.center[1] + offset[1]) // grid_step) - 1, ((self.center[1] - offset[1]) // grid_step) + 1):
                    if i == 0:
                        continue
                    elif i % 2 == 0:
                        qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_M"]), 1))
                    else:
                        qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_L"]), 1))
                    line_offset = offset[1] + self.center[1] + (i * grid_step) - offset_correction
                    qp.drawLine(0, line_offset, self.width(), line_offset)

                for i in range(-((self.center[0] + offset[0]) // grid_step) - 1, ((self.center[0] - offset[0]) // grid_step) + 1):
                    if i == 0:
                        qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["L_COLOR_0"]), pen_width))
                    elif i % 2 == 0:
                        qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_M"]), 1))
                    else:
                        qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["GRAY_L"]), 1))
                    line_offset = offset[0] + self.center[0] + (i * grid_step) - offset_correction
                    qp.drawLine(line_offset, 0, line_offset, self.height())

                qp.setPen(QtGui.QPen(QtGui.QColor(THEME_COLORS["M_COLOR_0"]), pen_width))
                line_offset = offset[1] + self.center[1] - offset_correction
                qp.drawLine(0, line_offset, self.width(), line_offset)

            if not self.disable_controls:
                self.info_text.setText(f"({(self.offset[0] / self.scale):5.2f}, {(self.offset[1] / self.scale):5.2f})\n{(100.00 * self.scale):6.2f}%")

            if self.even_center:
                center_offset = 0
            else:
                center_offset = 0.5

            if self.img is not None:
                img_x = offset[0] + ((-self.img_offset[0] + center_offset) * self.scale) + self.center[0]
                img_y = offset[1] + ((-self.img_offset[1] + center_offset) * self.scale) + self.center[1]
                img = self.img.transformed(QtGui.QTransform().scale(self.scale, self.scale))

                qp.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
                qp.drawImage(img_x, img_y, img)
            
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

        def __init__(self, font, padding_amount, timeline_height, keyframe_padding, playhead_height):
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
                persistant = self.animation_data[self.current_layer]["is_persistant"] # TODO
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

            self.gif_preview = self.parent.InteractiveGraphicsWindow(
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
