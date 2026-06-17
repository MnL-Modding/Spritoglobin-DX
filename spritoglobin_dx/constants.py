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


THEME_PRESETS = {
    'mlkp': ["#f81810", "#18f868", "#f79c14", "#dddddd"], # mario, luigi, koopa, pmario
    'gmgd': ["#aee714", "#ff3c75", "#cf2cff", "#555596"], # geraco, mboss, gedonko, dstar
    'glob': ["#f05ec7", "#edd20a", "#9f5cda", "#14bb59"], # the globins
    'choc': ["#883800", "#ffe898", "#ff7020", "#404050"], # chococat
    'f_ww': ["#d462a6", "#ff9b56", "#a40062", "#d62800"], # lesbean flag
    'f_mm': ["#26ceaa", "#5049cc", "#98e8c1", "#7bade2"], # toothpaste flag
    'f_nb': ["#fff433", "#9b59d0", "#2d2d2d", "#dddddd"], # en-bee flag
    'f_py': ["#009fe3", "#e50051", "#340c46", "#fcbf00"], # poly want a cracker flag
}

THEME_COLORS = {
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


LANGUAGES = { # display name, NDS value, DT value, PJ+ value, github documentation language key, unfinished
    "None":  [None],
    "ja_JP": ["日本語",        0, 0x00, "JP_ja", "ja",  True],
    "en_US": ["English (US)",  1, 0x11, "US_en", "en", False],
    "fr_CA": ["Français (CA)", 2, 0x12, "US_fr", "fr",  True],
    "es_MX": ["Español (MX)",  5, 0x15, "US_sp", "es",  True],
    "en_GB": ["English (UK)",  1, 0x21, "EU_en", "en", False],
    "fr_FR": ["Français (FR)", 2, 0x22, "EU_fr", "fr", False],
    "de_DE": ["Deutsch",       3, 0x23, "EU_ge", "de",  True],
    "it_IT": ["Italiano",      4, 0x24, "EU_it", "en",  True], # no github language
    "es_ES": ["Español (ES)",  5, 0x25, "EU_sp", "es", False],
    "nl_NL": ["Nederlands",   -1, 0x28, "EU_du", "en",  True], # no github language
    "pt_PT": ["Português",    -1, 0x29, "EU_pt", "pt",  True],
    "ru_RU": ["Русский",      -1, 0x2A, "EU_ru", "ru",  True],
    "ko_KR": ["한국어",        0, 0x57, "KR_ko", "ko",  True],
    "pl_PL": ["Polski",       -1,   -1,  None  , "en", False], # no github language
}


GAME_IDS_THAT_ARE_CURRENTLY_SUPPORTED = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_ARE_ON_3DS = ["ML4", "ML5", "ML1R", "ML3R"]

GAME_IDS_THAT_USE_BG4 = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_BOUNDING_BOXES = ["ML3R"]
GAME_IDS_THAT_USE_LOW_FRAMERATE = ["ML3R"]
GAME_IDS_THAT_USE_MATRIX_INVERSION = ["ML1R", "ML3R"]
GAME_IDS_THAT_USE_NORMAL_MAPS = ["ML1R", "ML3R"]