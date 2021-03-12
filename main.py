import logging
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from Gui.Windows import MainApplicationWindow

from Config.Constants import ORGANISATION_NAME, ORGANISATION_DOMAIN, APPLICATION_NAME
from Utils.Logging import LogStreamHandler

if __name__ == '__main__':
    QCoreApplication.setOrganizationName(ORGANISATION_NAME)
    QCoreApplication.setOrganizationDomain(ORGANISATION_DOMAIN)
    QCoreApplication.setApplicationName(APPLICATION_NAME)

    parent_app = QApplication(sys.argv)
    app = MainApplicationWindow()

    logger = logging.getLogger()
    handler = LogStreamHandler()
    logger.addHandler(handler)
    sys.exit(parent_app.exec_())




