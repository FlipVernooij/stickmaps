import logging
import os
import pathlib

from Utils import Logging

DEBUG = True
DS = os.sep

ORGANISATION_NAME = 'Squad'
ORGANISATION_DOMAIN = 'squad.nl'
APPLICATION_NAME = 'StickMaps'
APPLICATION_ICON = f'Assets{DS}windowIcon.png'
APPLICATION_VERSION = "0.1 ALPHA"
APPLICATION_AUTHOR = "Flip Vernooij <flip@stickmaps.co>"
APPLICATION_FILE_EXTENSION = 'stk'
APPLICATION_SPLASH_IMAGE = f"Assets{DS}splash.jpg"
APPLICATION_STARTUP_DIALOG_IMAGE = APPLICATION_ICON
APPLICATION_NEWPROJECT_IMAGE = f"Assets{DS}project.jpg"

APPLICATION_DATA_DIR = f'{str(pathlib.Path.home())}{DS}.stickmaps'

APPLICATION_CACHE_DIR = f'{APPLICATION_DATA_DIR}{DS}cache'
APPLICATION_CACHE_MAX_SIZE = 100  # mb

APPLICATION_DEFAULT_PROJECT_NAME = "Untitled project"
APPLICATION_DEFAULT_FILE_NAME = f"Untitled.{APPLICATION_FILE_EXTENSION}"

MAIN_WINDOW_TITLE = f'{APPLICATION_NAME} v{APPLICATION_VERSION}'
MAIN_WINDOW_ICON = APPLICATION_ICON
MAIN_WINDOW_STATUSBAR_TIMEOUT = 3000

DOCS_SEARCH_PATHS = (f'Documentation{DS}',)

TREE_START_WIDTH = 300
TREE_MIN_WIDTH = 100

TREE_LIGHT_ICON_SURVEY = f'Assets{DS}surveyIcon.png'
TREE_LIGHT_ICON_LINE = f'Assets{DS}sectionIcon.png'
TREE_LIGHT_ICON_STATION = f'Assets{DS}pointIcon.png'

TREE_DARK_ICON_SURVEY = f'Assets{DS}surveyIcon.png'
TREE_DARK_ICON_LINE = f'Assets{DS}sectionIcon.png'
TREE_DARK_ICON_STATION = f'Assets{DS}pointIcon.png'

MNEMO_DEVICE_NAME = "Mnemo"
MNEMO_DEVICE_DESCRIPTION = "MCP2221 USB-I2C/UART Combo"
MNEMO_BAUDRATE = 9600
MNEMO_TIMEOUT = 1
MNEMO_CYCLE_COUNT = 50

SURVEY_DIRECTION_IN = "In"
SURVEY_DIRECTION_OUT = "Out"

#SQL_DB_LOCATION = ":memory:"
SQL_DB_LOCATION = f"{APPLICATION_DATA_DIR}{DS}stickmaps.sqlite"
SQL_CONNECTION_NAME = "qt_sql_default_connection"

SQL_TABLE_PROJECT_SETTINGS = "project_settings"
SQL_TABLE_IMPORT_SURVEYS = "import_surveys"
SQL_TABLE_IMPORT_LINES = "import_lines"
SQL_TABLE_IMPORT_STATIONS = "import_stations"
SQL_TABLE_MAP_LINES = "map_lines"
SQL_TABLE_MAP_STATIONS = "map_stations"
SQL_TABLE_CONTACTS = "contacts"
SQL_TABLE_EXPLORERS = "explorers"
SQL_TABLE_SURVEYORS = "surveyors"

QML_MAPVIEW = 'data_files/map_view.qml'

logging.getLogger(__name__).warning('Using "STOLEN" google-api key, DO NOT RELEASE LIKE THIS')

GOOGLE_STATIC_MAPS_API_KEY = 'AIzaSyA2xikjgNyQJi6IA0WynJMGf13RS3tx2OE'
GOOGLE_STATIC_MAPS_URL = 'https://maps.googleapis.com/maps/api/staticmap'
GOOGLE_STATIC_MAPS_CACHE_DIR = f'{DS}google_static'

GOOGLE_MAPS_SCALING = 2


# Scene constants

# When a project doesn't have a lat/lng set, we need to have a default to calculate our scene from.
SCENE_DEFAULT_LATITUDE = 20.491621764639405
SCENE_DEFAULT_LONGITUDE = -87.25863770346321
SCENE_MAP_TILE_SIZE = 256
SCENE_DEFAULT_ZOOM = 20

DEGREES_N = 0
DEGREES_NE = 45
DEGREES_E = 90
DEGREES_SE = 135
DEGREES_S = 180
DEGREES_SW = 225
DEGREES_W = 270
DEGREES_NW = 315


