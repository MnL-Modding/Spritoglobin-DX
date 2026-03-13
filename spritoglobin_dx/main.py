import configparser
import importlib.metadata
import os
import re
import sys
import time
from importlib.metadata import PackageNotFoundError
from functools import partial

import requests
from packaging.version import Version
from PySide6 import QtWidgets, QtGui, QtMultimedia

from spritoglobin_dx.classes import ObjFile, GAME_IDS_THAT_USE_BOUNDING_BOXES
from spritoglobin_dx.constants import *
from spritoglobin_dx.gui import ItemDelegate, InteractiveGraphicsWindow, GraphicsAnimationTimeline, ColorAnimationTimeline
from spritoglobin_dx.popups import FileImportWindow, GifExportWindow


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

        self.theme_icons = {}
        self.current_theme_file_path = 'img_icons_dx'

        self.theme_icons_current_obj_color_anim_icon = 'blank'
        self.theme_icons_current_single_color_anim_timeline_icon = 'blank'
        self.theme_icons_current_obj_color_anim_timeline_icon = 'blank'

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
        self.set_framerate(int(self.settings.get("framerate", 1)))
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

        # Ctrl+Shift+G = Globin Theme Toggle (Secret, Mostly for Testing)
        action = QtGui.QAction(self)
        action.setShortcut(QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier | QtCore.Qt.Key_G))
        action.triggered.connect(self.globin_theme_toggle)
        self.addAction(action)


        self.init_ui()
        self.update_program_theme()


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
        
        # get current version of app
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

        self.menu_bar_file_open_action = QtGui.QAction(self.tr("MenuBarFileOpenOption"), self)
        self.menu_bar_file_open_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.menu_bar_file_open_action.triggered.connect(self.open_file)
        menu_bar_file.addAction(self.menu_bar_file_open_action)

        self.menu_bar_file_close_action = QtGui.QAction(self.tr("MenuBarFileCloseOption"), self)
        self.menu_bar_file_close_action.setShortcut(QtGui.QKeySequence.StandardKey.Close)
        self.menu_bar_file_close_action.triggered.connect(self.close_file)
        menu_bar_file.addAction(self.menu_bar_file_close_action)

        menu_bar_file.addSeparator() # -----------------------------------------

        self.menu_bar_file_quick_export_action = QtGui.QAction(self.tr("MenuBarFileQuickExportOption"), self)
        self.menu_bar_file_quick_export_action.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.menu_bar_file_quick_export_action.triggered.connect(partial(self.export_file, True))
        menu_bar_file.addAction(self.menu_bar_file_quick_export_action)

        self.menu_bar_file_export_action = QtGui.QAction(self.tr("MenuBarFileExportOption"), self)
        self.menu_bar_file_export_action.setShortcut(QtGui.QKeySequence.StandardKey.SaveAs)
        self.menu_bar_file_export_action.triggered.connect(partial(self.export_file, False))
        menu_bar_file.addAction(self.menu_bar_file_export_action)

        menu_bar_file.addSeparator() # -----------------------------------------

        self.menu_bar_file_quit_action = QtGui.QAction(self.tr("MenuBarFileQuitOption"), self)
        self.menu_bar_file_quit_action.setShortcut(QtGui.QKeySequence.StandardKey.Quit)
        self.menu_bar_file_quit_action.triggered.connect(QtWidgets.QApplication.quit)
        menu_bar_file.addAction(self.menu_bar_file_quit_action)


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
        framerates = QtGui.QActionGroup(self)
        framerates.setExclusive(True)
        for i in range(2):
            string = [
                self.tr("MenuBarOptionsFramerate").format(60),
                self.tr("MenuBarOptionsFramerate").format(30),
            ][i]

            framerate_action = QtGui.QAction(string)
            framerate_action.setData(i)
            framerate_action.setCheckable(True)
            if self.settings["framerate"] == i:
                framerate_action.setChecked(True)

            framerates.addAction(framerate_action)
        framerate_selector.addActions(framerates.actions())
        framerate_selector.triggered.connect(self.set_framerate)

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
        self.anim_list_box.setItemDelegate(ItemDelegate())
        self.anim_list_box.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.sprite_viewer = InteractiveGraphicsWindow(
            font = mono_font,
            size = [512, 512],
            default_scale = 2,
            default_offset = [0.0, 0.0],
            min_scale = 0.5,
            max_scale = 16.0,
            grid_size = 32,
            three_dimensional = True,
        )
        self.sprite_viewer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sprite_viewer.setMinimumWidth(512)
        self.sprite_viewer.setMinimumHeight(512)

        self.sprite_anim_timeline = GraphicsAnimationTimeline(
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

        self.sprite_color_anim_timeline = ColorAnimationTimeline(
            font             = mono_font,
            boolean_strings  = self.boolean_strings,
            padding_amount   = 9,
            timeline_height  = 29,
            keyframe_padding = 2,
            playhead_height  = 8,
        )
        self.sprite_color_anim_timeline.playbackToggled.connect(self.sprite_color_anim_toggle_playback)
        self.sprite_color_anim_timeline.playbackStopped.connect(self.sprite_color_anim_stop_playback)
        self.sprite_color_anim_timeline.timelineScrubbed.connect(self.set_animation_timer)
        self.sprite_color_anim_timeline.setEnabled(False)

        self.global_color_anim_timeline = ColorAnimationTimeline(
            font             = mono_font,
            boolean_strings  = self.boolean_strings,
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

        self.timeline_tabs = QtWidgets.QTabWidget()
        self.timeline_tabs.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.timeline_tabs.setMinimumWidth(320)
        self.timeline_tabs.setTabPosition(QtWidgets.QTabWidget.South)
        self.timeline_tabs.addTab(self.sprite_anim_timeline, self.tr("AnimationTabsSpriteAnimTitle"))
        self.timeline_tabs.addTab(self.sprite_color_anim_timeline, self.tr("AnimationTabsSpriteColorAnimTitle"))
        self.timeline_tabs.addTab(global_color_anim, self.tr("AnimationTabsSpriteGlobalAnimTitle"))
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

        self.sprite_part_viewer = InteractiveGraphicsWindow(
            font = mono_font,
            size = [256, 256],
            default_scale = 1,
            default_offset = [0.0, 0.0],
            min_scale = 0.5,
            max_scale = 8.0,
            grid_size = 32,
        )
        self.sprite_part_viewer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sprite_part_viewer.setMinimumWidth(256)
        self.sprite_part_viewer.setMinimumHeight(256)
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
        self.sprite_part_tile_viewer = InteractiveGraphicsWindow(
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

        # string = QtWidgets.QLabel("global palette")
        # string.setEnabled(False)
        # sprite_part_info_layout.addWidget(string, 8, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        global_palette = QtWidgets.QWidget()
        global_palette_layout = QtWidgets.QGridLayout(global_palette)
        global_palette_layout.setContentsMargins(0, 0, 0, 0)
        self.global_palette_labels = []
        palette_row_width = 8
        palette_total = 16
        for i in range(palette_total):
            palette_label = QtWidgets.QLabel()
            palette_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, palette_label.sizePolicy().verticalPolicy())
            global_palette_layout.addWidget(palette_label, i // palette_row_width, i % palette_row_width)
            self.global_palette_labels.append(palette_label)

        # only one of them needs to be given this
        self.global_palette_size = 1
        self.global_palette_line_thickness = 1
        self.global_palette_labels[palette_total - 1].resizeEvent = self.resize_global_palette

        sprite_part_info_layout.addWidget(global_palette, 9, 0, 1, 2)

        self.sprite_part_renderer_info_text = QtWidgets.QLabel()
        sprite_part_info_layout.addWidget(self.sprite_part_renderer_info_text, 10, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        string = QtWidgets.QLabel("Lighting Data Display NYI")
        string.setEnabled(False)
        sprite_part_info_layout.addWidget(string, 11, 0, 1, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter)

        try:
            dist = importlib.metadata.distribution(APP_NAME)
            ver_num = f"{APP_DISPLAY_NAME} v{dist.version}"
        except PackageNotFoundError:
            ver_num = "(Unknown Version)"

        version_number = QtWidgets.QLabel(ver_num)
        version_number.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        version_number.setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignRight)
        version_number.setEnabled(False)
        sprite_part_info_layout.addWidget(version_number, 12, 0, 1, -1)

        sprite_part_info_layout.setColumnStretch(0, 1)
        sprite_part_info_layout.setColumnStretch(1, 1)



        lists_and_stuff = QtWidgets.QFrame()
        lists_and_stuff.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lists_and_stuff_layout = QtWidgets.QGridLayout(lists_and_stuff)
        lists_and_stuff_layout.setContentsMargins(0, 0, 0, 0)

        lists_and_stuff_layout.addWidget(self.obj_list_box, 1, 0, 1, 2)
        lists_and_stuff_layout.addWidget(object_info, 2, 0, 1, 2)
        lists_and_stuff_layout.addWidget(self.anim_list_box, 5, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("ObjectSelectorTitle"))
        string.setBuddy(self.obj_list_box)
        string.setEnabled(False)
        lists_and_stuff_layout.addWidget(string, 0, 0, 1, 2)

        string = QtWidgets.QLabel(self.tr("AnimationSelectorTitle"))
        string.setBuddy(self.anim_list_box)
        string.setEnabled(False)
        lists_and_stuff_layout.addWidget(string, 4, 0, 1, 1)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        lists_and_stuff_layout.addWidget(line, 3, 0, 1, 2)

        self.global_animation_icon = QtWidgets.QLabel()
        lists_and_stuff_layout.addWidget(self.global_animation_icon, 4, 1, 1, 1, alignment = QtCore.Qt.AlignmentFlag.AlignRight)



        self.animation_timer_going = False
        self.color_timer_going = False



        main = QtWidgets.QWidget()
        main_layout = QtWidgets.QGridLayout(main)

        main_layout.addWidget(lists_and_stuff, 0, 0, 1, 1)
        main_layout.addWidget(self.sprite_viewer, 0, 1, 1, 1)
        main_layout.addWidget(self.timeline_tabs, 1, 0, 1, 2)
        main_layout.addWidget(sprite_part_info, 0, 2, 2, 1)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 5)
        main_layout.setColumnStretch(2, 2)

        self.setCentralWidget(main)
        self.set_theme(update = False)


        self.change_file()
    

    def open_file(self):
        self.animation_timer.stop()

        import_window = FileImportWindow(self, self.game_title_strings, self.current_window_icon)
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
        
        export_window = GifExportWindow(
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

        self.boolean_strings = {
            True:  self.tr("GenericBooleanAffirmative"),
            False: self.tr("GenericBooleanNegative"),
        }

        self.write_config()

        if reset_ui:
            save_obj = self.obj_list_box.currentText()
            save_ans = self.anim_list_box.currentRow()
            save_anc = self.color_anim_list_box.currentRow()
            save_gos = self.animation_timer_going
            save_goc = self.color_timer_going
            save_tab = self.timeline_tabs.currentIndex()
            save_sps = self.sprite_part_set_list_box.currentIndex()
            save_sph = self.sprite_part_list_box.currentIndex()
            if self.obj_data is not None:
                save_tmr = self.obj_data.get_timers(animation_timer = True, color_timer = True)

            self.init_ui()

            self.obj_list_box.setCurrentText(save_obj)
            self.anim_list_box.setCurrentRow(save_ans)
            self.color_anim_list_box.setCurrentRow(save_anc)
            self.animation_timer_going = save_gos
            self.color_timer_going = save_goc
            self.timeline_tabs.setCurrentIndex(save_tab)
            self.sprite_part_set_list_box.setCurrentIndex(save_sps)
            self.sprite_part_list_box.setCurrentIndex(save_sph)
            if self.obj_data is not None:
                self.obj_data.set_timers(save_tmr, animation_timer = True, color_timer = True)
    
    def set_framerate(self, framerate):
        if not isinstance(framerate, int):
            framerate = framerate.data()

        self.settings["framerate"] = framerate

        try:
            framerate = [60, 30][self.settings["framerate"]]
            self.animation_timer.setInterval(round(1000 / framerate))
        except AttributeError:
            pass

        self.write_config()
    
    def toggle_mute(self, muted):
        self.settings["muted"] = str(muted)

        self.write_config()
    
    def toggle_update_check(self, check):
        if check is None:
            query_link_string = self.tr("CheckUpdateQueryLinkString")
            
            lang_key = self.settings["language"]

            if lang_key == "None":
                lang_key = QtCore.QLocale.system().name()
            
            github_lang_key = LANGUAGES[lang_key][3]

            check_updates_box = QtWidgets.QMessageBox(self)
            check_updates_box.setTextFormat(QtCore.Qt.RichText)
            check_updates_box.setWindowTitle(self.tr("CheckUpdateQueryTitle"))
            check_updates_box.setText(self.tr("CheckUpdateQueryBlurb").format(
                f"<a href='https://docs.github.com/{github_lang_key}/site-policy/privacy-policies/github-general-privacy-statement'>{query_link_string}</a>"
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

            self.obj_list_box.blockSignals(True)
            for cellanim in cellanims:
                self.obj_list_box.addItem(self.obj_data.cellanim_files[cellanim].name)
            self.obj_list_box.blockSignals(False)
        else:
            self.obj_list_box.clear()

            self.object_bounding_box_enable.setChecked(False)
            self.object_bounding_box_enable.setVisible(False)
            self.sprite_anim_timeline.bounding_box_toggle.setChecked(False)
            self.sprite_anim_timeline.bounding_box_toggle.setVisible(False)
            self.sprite_anim_timeline.bounding_box_toggle_string.setVisible(False)

            self.change_highlighted_sprite_part()

        self.update_program_theme()
        self.change_object()

        self.anim_list_box.setCurrentRow(0)

        if self.color_timer_going:
            self.color_anim_list_box.setCurrentRow(1)
        else:
            self.color_anim_list_box.setCurrentRow(0)
    
    def change_object(self):
        if self.obj_data is None:
            self.animation_timer.stop()
            self.anim_list_box.clear()
            self.color_mode_info_text.setVisible(False)
            self.sprite_part_set_list_box.clear()
            self.update_sprite_viewer(force = True)

            self.theme_icons_current_single_color_anim_timeline_icon = 'g_palette'
            self.timeline_tabs.setTabIcon(1, self.theme_icons[self.theme_icons_current_single_color_anim_timeline_icon])
            self.sprite_color_anim_timeline.setEnabled(False)

            self.theme_icons_current_obj_color_anim_timeline_icon = 'g_palette'
            self.timeline_tabs.setTabIcon(2, self.theme_icons[self.theme_icons_current_obj_color_anim_timeline_icon])
            self.global_color_anim_timeline.setEnabled(False)

            self.theme_icons_current_obj_color_anim_icon = 'blank'
            self.global_animation_icon.setPixmap(self.theme_icons[self.theme_icons_current_obj_color_anim_icon])
            
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

        if object_properties["has_color_data"]:
            self.theme_icons_current_obj_color_anim_icon = 'palette'
            self.global_animation_icon.setPixmap(self.theme_icons[self.theme_icons_current_obj_color_anim_icon])

            self.theme_icons_current_obj_color_anim_timeline_icon = 'palette'
            self.timeline_tabs.setTabIcon(2, self.theme_icons[self.theme_icons_current_obj_color_anim_timeline_icon])
        else:
            self.theme_icons_current_obj_color_anim_icon = 'blank'
            self.global_animation_icon.setPixmap(self.theme_icons[self.theme_icons_current_obj_color_anim_icon])

            self.theme_icons_current_obj_color_anim_timeline_icon = 'g_palette'
            self.timeline_tabs.setTabIcon(2, self.theme_icons[self.theme_icons_current_obj_color_anim_timeline_icon])

        self.global_color_anim_timeline.setEnabled(object_properties["has_color_data"])
        self.color_anim_list_box.setEnabled(object_properties["has_color_data"])


        for i in range(object_properties["animation_number"]):
            item = QtWidgets.QListWidgetItem(str(i))
            # if self.obj_data.get_animation_properties(
            #     object_name     = self.obj_list_box.currentText(), 
            #     animation_index = i,
            # )["has_color_data"]:
            #     item.setIcon(self.theme_icons['palette'])
            # else:
            #     item.setIcon(self.theme_icons['blank'])
            self.anim_list_box.addItem(item)
        self.anim_list_box.setCurrentRow(0)

        self.set_anim_list_box_palette_icons()


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
    
    def set_anim_list_box_palette_icons(self):
        if self.obj_data is None:
            return

        for i in range(self.anim_list_box.count()):
            item = self.anim_list_box.item(i)
            if self.obj_data.get_animation_properties(
                object_name     = self.obj_list_box.currentText(), 
                animation_index = i,
            )["has_color_data"]:
                item.setIcon(self.theme_icons['palette'])
            else:
                item.setIcon(self.theme_icons['blank'])
    
    def change_animation(self):
        if self.obj_data is None:
            self.sprite_anim_timeline.update_timeline()
            self.sprite_color_anim_timeline.send_color_data()

            self.theme_icons_current_single_color_anim_timeline_icon = 'g_palette'
            self.timeline_tabs.setTabIcon(1, self.theme_icons[self.theme_icons_current_single_color_anim_timeline_icon])
            self.sprite_color_anim_timeline.setEnabled(False)

            self.theme_icons_current_obj_color_anim_timeline_icon = 'g_palette'
            self.timeline_tabs.setTabIcon(2, self.theme_icons[self.theme_icons_current_obj_color_anim_timeline_icon])
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

        if animation_properties["has_color_data"]:
            self.theme_icons_current_single_color_anim_timeline_icon = 'palette'
            self.timeline_tabs.setTabIcon(1, self.theme_icons[self.theme_icons_current_single_color_anim_timeline_icon])
        else:
            self.theme_icons_current_single_color_anim_timeline_icon = 'g_palette'
            self.timeline_tabs.setTabIcon(1, self.theme_icons[self.theme_icons_current_single_color_anim_timeline_icon])
            
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
            self.update_global_palette()
            return
        
        object_properties = self.obj_data.get_object_properties(object_name = self.obj_list_box.currentText())

        color_anim_index = -1
        if self.color_anim_list_box.currentRow() != 0 and object_properties["has_color_data"] and self.color_anim_list_box.currentItem() is not None:
            color_anim_index = int(self.color_anim_list_box.currentItem().text())

        # for testing
        renderer_to_use = 1

        match renderer_to_use:
            case 0:
                img, size, offset = self.obj_data.get_sprite_with_offset(
                    object_name      = self.obj_list_box.currentText(), 
                    animation_index  = self.anim_list_box.currentRow(),
                    color_anim_index = color_anim_index,
                )

                if img is not None:
                    self.sprite_viewer.draw_image(QtGui.QImage(img, *size, QtGui.QImage.Format_RGBA8888), offset)
                else:
                    self.sprite_viewer.draw_image(None, (0, 0))
            case 1:
                img_data = self.obj_data.get_sprite_part_entities(
                    object_name      = self.obj_list_box.currentText(), 
                    animation_index  = self.anim_list_box.currentRow(),
                    color_anim_index = color_anim_index,
                )
        
                base_sprite = [
                    img_data,  # sprite parts list
                    (0, 0, 0), # translation
                    (0, 0, 0), # rotation
                    (1, 1, 1), # scale
                ]

                palette = self.obj_data.get_object_palette(
                    object_name      = self.obj_list_box.currentText(),
                    animation_index  = self.anim_list_box.currentRow(),
                    color_anim_index = color_anim_index,
                )

                fragment_light = [(1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 1.0)]

                self.sprite_viewer.draw_3d_image([[base_sprite], palette, fragment_light])

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

        self.update_global_palette()


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
            h_flip = self.boolean_strings[sprite_part_properties["horizontal_flip"]]
            v_flip = self.boolean_strings[sprite_part_properties["vertical_flip"]]
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
    
    def resize_global_palette(self, event = None):
        if event is None:
            width = 40
        else:
            width = event.size().width()

        self.global_palette_line_thickness = min(2, (width // 40) + 1)
        self.global_palette_size = ((width - (self.global_palette_line_thickness * 4)) // 2)
        self.update_renderer_data()
    
    def update_global_palette(self):
        if self.obj_data is not None:
            object_name = self.obj_list_box.currentText()

            object_properties = self.obj_data.get_object_properties(object_name = object_name)

            color_anim_index = -1
            if self.color_anim_list_box.currentRow() != 0 and object_properties["has_color_data"] and self.color_anim_list_box.currentItem() is not None:
                color_anim_index = int(self.color_anim_list_box.currentItem().text())

            palette = self.obj_data.get_object_palette(
                object_name      = object_name,
                animation_index  = self.anim_list_box.currentRow(),
                color_anim_index = color_anim_index,
            )
        else:
            palette = [[0xFF, 0xFF, 0xFF, 0xFF], [0x00, 0x00, 0x00, 0xFF]] * 8
        
        self.global_palette_data = palette
        self.update_renderer_data()

    def update_renderer_data(self):
        size = self.global_palette_size
        thickness = self.global_palette_line_thickness
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
            r, g, b, a = self.global_palette_data[i]

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
        self.sprite_part_viewer.background_color = background_color
        self.sprite_part_tile_viewer.background_color = background_color

        tabs_palette = QtWidgets.QTabWidget().palette()
        if dark: tabs_palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QPalette().color(QtGui.QPalette.ColorRole.Dark))
        else:    tabs_palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QPalette().color(QtGui.QPalette.ColorRole.Light))
        self.timeline_tabs.setPalette(tabs_palette)

        self.sprite_anim_timeline.background_color = background_color
        self.sprite_color_anim_timeline.background_color = background_color
        self.global_color_anim_timeline.background_color = background_color

        if update: self.update_program_theme()
    
    def update_program_theme(self):
        if self.current_game_id in GAME_IDS_THAT_ARE_ON_3DS or self.current_game_id is None:
            self.current_window_icon = QtGui.QIcon(str(FILES_DIR / 'ico_sprito_dx.ico'))
            self.success_jingle.setSource(QtCore.QUrl.fromLocalFile(FILES_DIR / "snd_success_dx.wav"))
            self.current_theme_file_path = 'img_icons_dx'
        else:
            self.current_window_icon = QtGui.QIcon(str(FILES_DIR / 'ico_sprito.ico'))
            self.success_jingle.setSource(QtCore.QUrl.fromLocalFile(FILES_DIR / "snd_success.wav"))
            self.current_theme_file_path = 'img_icons'

        self.set_theme_icons(self.current_theme_file_path, True)
        self.apply_theme_icons()
        self.setWindowIcon(self.current_window_icon)

        self.sprite_viewer.update_image()
        self.sprite_part_viewer.update_image()
        self.sprite_part_tile_viewer.update_image()

        self.sprite_anim_timeline.draw_full()
        self.sprite_color_anim_timeline.draw_full()
        self.global_color_anim_timeline.draw_full()
    
    def globin_theme_toggle(self):
        THEME_COLORS["M_COLOR_0"], THEME_COLORS["L_COLOR_0"], THEME_COLORS["K_COLOR_0"], THEME_COLORS["P_COLOR_0"] = THEME_PRESETS['glob']
        self.update_program_theme()

    def set_theme_icons(self, icon_path, map_theme_colors):
        self.theme_icons['blank']     = self.grab_theme_icon(icon_path,  0, (16, 16), map_theme_colors)
        self.theme_icons['sprito']    = self.grab_theme_icon(icon_path,  1, (16, 16), map_theme_colors)
        self.theme_icons['zoom_in']   = self.grab_theme_icon(icon_path,  2, (16, 16), map_theme_colors)
        self.theme_icons['zoom_out']  = self.grab_theme_icon(icon_path,  3, (16, 16), map_theme_colors)
        self.theme_icons['reset']     = self.grab_theme_icon(icon_path,  4, (16, 16), map_theme_colors)
        self.theme_icons['play']      = self.grab_theme_icon(icon_path,  5, (16, 16), map_theme_colors)
        self.theme_icons['pause']     = self.grab_theme_icon(icon_path,  6, (16, 16), map_theme_colors)
        self.theme_icons['stop']      = self.grab_theme_icon(icon_path,  7, (16, 16), map_theme_colors)
        self.theme_icons['palette']   = self.grab_theme_icon(icon_path,  8, (16, 16), map_theme_colors)
        self.theme_icons['add']       = self.grab_theme_icon(icon_path,  9, (16, 16), map_theme_colors)
        self.theme_icons['subtract']  = self.grab_theme_icon(icon_path, 10, (16, 16), map_theme_colors)
        self.theme_icons['up']        = self.grab_theme_icon(icon_path, 11, (16, 16), map_theme_colors)
        self.theme_icons['down']      = self.grab_theme_icon(icon_path, 12, (16, 16), map_theme_colors)
        self.theme_icons['close']     = self.grab_theme_icon(icon_path, 13, (16, 16), map_theme_colors)
        self.theme_icons['open']      = self.grab_theme_icon(icon_path, 14, (16, 16), map_theme_colors)
        self.theme_icons['exit']      = self.grab_theme_icon(icon_path, 15, (16, 16), map_theme_colors)
        self.theme_icons['export']    = self.grab_theme_icon(icon_path, 16, (16, 16), map_theme_colors)

        self.theme_icons['g_palette'] = self.grab_disabled_icon(self.theme_icons['palette'])

    def apply_theme_icons(self):
        self.menu_bar_file_open_action.setIcon(self.theme_icons['open'])
        self.menu_bar_file_close_action.setIcon(self.theme_icons['close'])
        self.menu_bar_file_quick_export_action.setIcon(self.theme_icons['export'])
        self.menu_bar_file_export_action.setIcon(self.theme_icons['export'])
        self.menu_bar_file_quit_action.setIcon(self.theme_icons['exit'])

        self.global_animation_icon.setPixmap(self.theme_icons[self.theme_icons_current_obj_color_anim_icon])
        self.set_anim_list_box_palette_icons()

        self.timeline_tabs.setTabIcon(0, self.theme_icons['sprito'])
        self.timeline_tabs.setTabIcon(1, self.theme_icons[self.theme_icons_current_single_color_anim_timeline_icon])
        self.timeline_tabs.setTabIcon(2, self.theme_icons[self.theme_icons_current_obj_color_anim_timeline_icon])

    def grab_theme_icon(self, file_path, index, icon_size, map_theme_colors = False):
        if index == 0:
            if icon_size is None:
                icon = QtGui.QPixmap(str(FILES_DIR / f'{file_path}.png'))
            else:
                icon = QtGui.QPixmap(*icon_size)
            icon.fill(QtCore.Qt.transparent)
            return icon

        icon_sheet = QtGui.QPixmap(str(FILES_DIR / f'{file_path}.png'))

        if icon_size is not None:
            num_columns = icon_sheet.width() // icon_size[0]

            index -= 1
            x = (index % num_columns) * icon_size[0]
            y = (index // num_columns) * icon_size[1]

            img_rect = QtCore.QRect(x, y, *icon_size)
            icon = icon_sheet.copy(img_rect)
        else:
            icon = icon_sheet

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
    
    def grab_disabled_icon(self, icon):
        icon = icon.toImage()
        gray_icon = icon.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
        gray_icon = gray_icon.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        gray_icon.setAlphaChannel(icon.convertToFormat(QtGui.QImage.Format.Format_Alpha8))
        return QtGui.QPixmap.fromImage(gray_icon)