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


THEME_PRESETS = { # fifth and sixth colors are white/black for preset icons
    'mlkp': ["#f81810", "#18f868", "#f79c14", "#ffffff", '#ffffff', "#002020"], # mario, luigi, koopa, pmario
    'gmgd': ["#aee714", "#ff3c75", "#cf2cff", "#555596", '#ffdfdf', "#200000"], # geraco, mboss, gedonko, dstar
    'glob': ["#f05ec7", "#edd20a", "#9f5cda", "#14bb59", '#ffffff', "#000000"], # the globins
    'choc': ["#883800", "#ffe898", "#ff7020", "#404050", '#ffefdf', "#100000"], # chococat
    'f_ww': ["#d462a6", "#ff9b56", "#a40062", "#d62800", '#ffffff', "#201000"], # lesbean flag
    'f_mm': ["#26ceaa", "#5049cc", "#98e8c1", "#7bade2", '#ffffff', "#002030"], # toothpaste flag
    'f_nb': ["#fff433", "#9b59d0", "#2d2d2d", "#ffffff", '#ffffff', "#181800"], # en-bee flag
    'f_py': ["#009fe3", "#e50051", "#340c46", "#fcbf00", '#ffffff', "#001030"], # poly want a cracker flag
}

THEME_COLORS = {
    "LIGHT":  "#ffffffff",
    "GRAY_L": "#88888888",
    "GRAY_M": "#aa777777",
    "GRAY_H": "#ee666666",
    "DARK":   "#ff555555",

    "WHITE": "#FFFFFF",
    "BLACK": "#000000",
}

THEME_COLOR_ICON_MASKS = { # normal, light, dark
    "M_COLOR_0": ("#FF0000", "#FF8080", "#800000"),
    "L_COLOR_0": ("#00FF00", "#BFFFBF", "#008000"),
    "K_COLOR_0": ("#FFFF00", "#FFFFBF", "#808000"),
    "P_COLOR_0": ("#00FFFF", "#BFFFFF", "#008080"),
    "WHITE":     ("#BFBFBF", "#FFFFFF", "#808080"),
    "BLACK":     ("#202020", "#404040", "#000000"),
}


DEFAULT_LANGUAGE = "en_US"
LANGUAGES = {
    "None":  {'name': None},
    "ja_JP": {'name': "日本語",        'ml3_key': "J0", 'ml4_key': "00", 'ml5_key': "JP_ja", 'github_lang': "ja", 'unfinished':  True},
    "en_US": {'name': "English (US)",  'ml3_key': "E1", 'ml4_key': "11", 'ml5_key': "US_en", 'github_lang': "en", 'unfinished': False},
    "fr_CA": {'name': "Français (CA)", 'ml3_key': "E2", 'ml4_key': "12", 'ml5_key': "US_fr", 'github_lang': "fr", 'unfinished':  True},
    "es_MX": {'name': "Español (MX)",  'ml3_key': "E5", 'ml4_key': "15", 'ml5_key': "US_sp", 'github_lang': "es", 'unfinished':  True},
    "en_GB": {'name': "English (UK)",  'ml3_key': "P1", 'ml4_key': "21", 'ml5_key': "EU_en", 'github_lang': "en", 'unfinished': False},
    "fr_FR": {'name': "Français (FR)", 'ml3_key': "P2", 'ml4_key': "22", 'ml5_key': "EU_fr", 'github_lang': "fr", 'unfinished': False},
    "de_DE": {'name': "Deutsch",       'ml3_key': "P3", 'ml4_key': "23", 'ml5_key': "EU_ge", 'github_lang': "de", 'unfinished':  True},
    "it_IT": {'name': "Italiano",      'ml3_key': "P4", 'ml4_key': "24", 'ml5_key': "EU_it", 'github_lang': None, 'unfinished':  True},
    "es_ES": {'name': "Español (ES)",  'ml3_key': "P5", 'ml4_key': "25", 'ml5_key': "EU_sp", 'github_lang': "es", 'unfinished': False},
    "nl_NL": {'name': "Nederlands",    'ml3_key': None, 'ml4_key': "28", 'ml5_key': "EU_du", 'github_lang': None, 'unfinished':  True},
    "pt_PT": {'name': "Português",     'ml3_key': None, 'ml4_key': "29", 'ml5_key': "EU_pt", 'github_lang': "pt", 'unfinished':  True},
    "ru_RU": {'name': "Русский",       'ml3_key': None, 'ml4_key': "2A", 'ml5_key': "EU_ru", 'github_lang': "ru", 'unfinished':  True},
    "ko_KR": {'name': "한국어",        'ml3_key': "K0", 'ml4_key': "57", 'ml5_key': "KR_ko", 'github_lang': "ko", 'unfinished':  True},
    "zh_CN": {'name': "简体中文",      'ml3_key': None, 'ml4_key': "46", 'ml5_key': "CN_ch", 'github_lang': "zh", 'unfinished':  True}, # there is no easter bunny, there is no tooth fairy, and there is no chinese BIS release
    "zh_TW": {'name': "繁體中文",      'ml3_key': None, 'ml4_key': "4B", 'ml5_key': "CN_tw", 'github_lang': "zh", 'unfinished':  True},
    "pl_PL": {'name': "Polski",        'ml3_key': None, 'ml4_key': None, 'ml5_key': None,    'github_lang': None, 'unfinished': False},
}


# used for sprito dx ui
GAME_IDS_THAT_ARE_CURRENTLY_SUPPORTED = ["ML2", "ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_ARE_ON_3DS = ["ML4", "ML5", "ML1R", "ML3R"]

# general purpose
GAME_IDS_THAT_ARE_ON_NDS = ["ML2"] # TODO urgent: deprecate
GAME_IDS_THAT_USE_3D_ENGINES = ["ML3", "ML4", "ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_ALT_COUNTING_SCHEMES = ["ML2"]
GAME_IDS_THAT_USE_ALT_COORDINATES_SYSTEM = ["ML2"]
GAME_IDS_THAT_USE_BG4 = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_BOUNDING_BOXES = ["ML3R"]
GAME_IDS_THAT_USE_FLOATS = ["ML4", "ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_LOW_FRAMERATE = ["ML3R"]
GAME_IDS_THAT_USE_MATRICES = ["ML3", "ML4", "ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_MATRIX_INVERSION = ["ML1R", "ML3R"]
GAME_IDS_THAT_USE_ML3_LANGUAGE_KEY = ["ML1", "ML2", "ML3"]
GAME_IDS_THAT_USE_ML4_LANGUAGE_KEY = ["ML4"]
GAME_IDS_THAT_USE_ML5_LANGUAGE_KEY = ["ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_NORMAL_MAPS = ["ML1R", "ML3R"]
GAME_IDS_THAT_USE_PALETTES = ["ML1", "ML2", "ML3"]
GAME_IDS_THAT_USE_PICA200_RENDERING = ["ML4", "ML5", "ML1R", "ML3R"]
GAME_IDS_THAT_USE_SPLIT_PATTERN_DATA = ["ML2"]
GAME_IDS_THAT_USE_SPRITE_SHEETS = ["ML4", "ML5", "ML1R", "ML3R"]