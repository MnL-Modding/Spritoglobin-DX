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

# leaving this here to copy/paste later
# THEME_COLORS["M_COLOR_0"] = 
# THEME_COLORS["L_COLOR_0"] = 
# THEME_COLORS["K_COLOR_0"] = 
# THEME_COLORS["P_COLOR_0"] = 

THEME_PRESETS = [
    ["#f81810", "#18f868", "#f79c14", "#dddddd"], # mlkp
    ["#aee714", "#ff3c75", "#cf2cff", "#555596"], # gmgd
    ["#f05ec7", "#edd20a", "#9f5cda", "#14bb59"], # the globins
    ["#000000", "#000000", "#000000", "#000000"], # ??? (undecided)
    ["#ff9b56", "#d462a6", "#a40062", "#d62800"], # lesbean flag
    ["#26ceaa", "#5049cc", "#7bade2", "#98e8c1"], # toothpaste flag
    ["#fff433", "#9b59d0", "#2d2d2d", "#dddddd"], # en-bee flag
    ["#009fe3", "#e50051", "#340c46", "#fcbf00"], # poly want a cracker flag
]


LANGUAGES = { # display name, NDS value, 3DS key, github documentation language key
    "None":  [None],
    "ja_JP": ["日本語",        0, "JP_ja", "ja"],
    "ko_KR": ["한국어",        0, "KR_ko", "ko"],
    "en_US": ["English (US)",  1, "US_en", "en"],
    "fr_CA": ["Français (CA)", 2, "US_fr", "fr"],
    "es_MX": ["Español (MX)",  5, "US_sp", "es"],
    "nl_NL": ["Nederlands",   -1, "EU_du", "en"], # no github language
    "en_GB": ["English (UK)",  1, "EU_en", "en"],
    "fr_FR": ["Français (FR)", 2, "EU_fr", "fr"],
    "de_DE": ["Deutsch",       3, "EU_ge", "de"],
    "it_IT": ["Italiano",      4, "EU_it", "en"], # no github language
    "pt_PT": ["Português",    -1, "EU_pt", "pt"],
    "ru_RU": ["Русский",      -1, "EU_ru", "ru"],
    "es_ES": ["Español (ES)",  5, "EU_sp", "es"],
}


GAME_IDS_THAT_ARE_CURRENTLY_SUPPORTED = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_ARE_ON_3DS = ["ML4", "ML5", "ML1R", "ML3R"]

GAME_IDS_THAT_USE_BG4 = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_BOUNDING_BOXES = ["ML3R"]
GAME_IDS_THAT_USE_LOW_FRAMERATE = ["ML3R"]
GAME_IDS_THAT_USE_MATRIX_INVERSION = ["ML1R", "ML3R"]
GAME_IDS_THAT_USE_NORMAL_MAPS = ["ML1R", "ML3R"]