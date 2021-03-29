import logging
import os
import pathlib
import sys
from pprint import pprint
from time import sleep

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QStyleFactory, QSplashScreen
from PySide6.QtCore import QCoreApplication

from Gui.Windows import MainApplicationWindow, Splash

from Config.Constants import ORGANISATION_NAME, ORGANISATION_DOMAIN, APPLICATION_NAME, APPLICATION_CACHE_DIR, \
    APPLICATION_CACHE_MAX_SIZE, APPLICATION_SPLASH_IMAGE
from Utils.Logging import LogStreamHandler
from Utils.Settings import Preferences

if __name__ == '__main__':

    parent_app = QApplication(sys.argv)
    splash = Splash()
    splash.show()
    splash.setFocus()
    parent_app.processEvents()

    splash.showMessage("Loading settings.")
    QCoreApplication.setOrganizationName(ORGANISATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANISATION_DOMAIN)
    QCoreApplication.setApplicationName(APPLICATION_NAME)

    splash.showMessage("Initializing log facilities.")
    logger = logging.getLogger()
    handler = LogStreamHandler()
    logger.addHandler(handler)

    if Preferences.debug() is True:
        logger.setLevel(Preferences.get('debug_loglevel', logging.WARNING, int))

    splash.showMessage("Verifying cache dir.")
    dir_path = Preferences.get("application_cache_dir", APPLICATION_CACHE_DIR, str)
    dir = pathlib.Path(dir_path)
    dir.mkdir(parents=True, exist_ok=True)

    bytes = sum(f.stat().st_size for f in dir.glob('**/*') if f.is_file())
    if Preferences.get('application_cache_max_size', APPLICATION_CACHE_MAX_SIZE, int) < (bytes / 1024) / 1024:
        logger.info("Cache max size exceeded, cleaning cache!")
        while True:
            oldest_file = sorted([os.path.abspath(f) for f in os.listdir(dir_path)], key=os.path.getctime)[0]
            logger.info(f'Removing file {oldest_file}')
            os.remove(oldest_file)
            if Preferences.get('application_cache_max_size', APPLICATION_CACHE_MAX_SIZE, int) >= (bytes / 1024) / 1024:
                break

    splash.showMessage("Executing main application window.")
    app = MainApplicationWindow()

    splash.finish(app)
    sys.exit(parent_app.exec_())




