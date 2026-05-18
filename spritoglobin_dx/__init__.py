# spritoglobin frontend
from .main import main as main

# main classes for spritoglobin
from .classes import ObjFile, InvalidObjectFileError
from .render import SpriteRenderer

# game_id related constants
from .constants import GAME_IDS_THAT_ARE_CURRENTLY_SUPPORTED
from .constants import GAME_IDS_THAT_ARE_ON_3DS
from .constants import GAME_IDS_THAT_USE_BG4
from .constants import GAME_IDS_THAT_USE_BOUNDING_BOXES
from .constants import GAME_IDS_THAT_USE_LOW_FRAMERATE
from .constants import GAME_IDS_THAT_USE_MATRIX_INVERSION
from .constants import GAME_IDS_THAT_USE_NORMAL_MAPS