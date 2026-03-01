from pathlib import Path

from PySide6 import QtCore, QtWidgets


APP_NAME = "spritoglobin_dx"
APP_DISPLAY_NAME = "Spritoglobin DX"

QtWidgets.QApplication.setApplicationName(APP_NAME)
QtWidgets.QApplication.setApplicationDisplayName(APP_DISPLAY_NAME)


SCRIPT_DIR = Path(__file__).parent
FILES_DIR = SCRIPT_DIR / 'files'
LANG_DIR = SCRIPT_DIR / 'lang'

CONFIG_DIR = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.AppConfigLocation))

THEME_COLORS = {
    "M_COLOR_0": "#f81810", # mario
    "L_COLOR_0": "#18f868", # luigi
    "K_COLOR_0": "#f79c14", # koopa
    "P_COLOR_0": "#dddddd", # paper

    "WHITE": "#ffffffff",

    "GRAY_L": "#88888888",
    "GRAY_M": "#aa777777",
    "GRAY_H": "#ee666666",

    "BLACK": "#ff555555",
}

THEME_COLOR_ICON_MASKS = {
    "M_COLOR_0": ("#FF0000", "#FF8080", "#800000"),
    "L_COLOR_0": ("#00FF00", "#BFFFBF", "#008000"),
    "K_COLOR_0": ("#FFFF00", "#FFFFBF", "#808000"),
    "P_COLOR_0": ("#00FFFF", "#BFFFFF", "#008080"),
}

# TODO: custom themes (temp test examples)

# THEME_COLORS["M_COLOR_0"] = "#f05ec7" # sprito
# THEME_COLORS["L_COLOR_0"] = "#edd20a" # cheato
# THEME_COLORS["K_COLOR_0"] = "#9f5cda" # data
# THEME_COLORS["P_COLOR_0"] = "#14bb59" # rando

# THEME_COLORS["M_COLOR_0"] = "#e125d0" # dx sprito
# THEME_COLORS["L_COLOR_0"] = "#ffff00" # dx cheato (NYI)
# THEME_COLORS["K_COLOR_0"] = "#7f00ff" # dx data (NYI)
# THEME_COLORS["P_COLOR_0"] = "#00ff00" # dx rando (NYI)


LANGUAGES = { # display name, NDS value, 3DS key
    "None":  [None,           -1, "None"],
    "ja_JP": ["日本語",        0, "JP_ja"],
    "ko_KR": ["한국어",        0, "KR_ko"],
    "en_US": ["English (US)",  1, "US_en"],
    "fr_CA": ["Français (CA)", 2, "US_fr"],
    "es_MX": ["Español (MX)",  5, "US_sp"],
    "nl_NL": ["Nederlands",   -1, "EU_du"],
    "en_GB": ["English (UK)",  1, "EU_en"],
    "fr_FR": ["Français (FR)", 2, "EU_fr"],
    "de_DE": ["Deutsch",       3, "EU_ge"],
    "it_IT": ["Italiano",      4, "EU_it"],
    "pt_PT": ["Português",    -1, "EU_pt"],
    "ru_RU": ["Русский",      -1, "EU_ru"],
    "es_ES": ["Español (ES)",  5, "EU_sp"],
}

GAME_IDS_THAT_ARE_CURRENTLY_SUPPORTED = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_ARE_ON_3DS = ["ML4", "ML5", "ML1R", "ML3R"]

GAME_IDS_THAT_USE_BG4 = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_BOUNDING_BOXES = ["ML3R"]
GAME_IDS_THAT_USE_LOW_FRAMERATE = ["ML3R"]
GAME_IDS_THAT_USE_MATRIX_INVERSION = ["ML1R", "ML3R"]
GAME_IDS_THAT_USE_NORMAL_MAPS = ["ML1R", "ML3R"]