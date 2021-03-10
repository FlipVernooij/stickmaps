import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from Config.Constants import ORGANISATION_NAME, ORGANISATION_DOMAIN, APPLICATION_NAME

if __name__ == '__main__':
    # parent_app = QtWidgets.QApplication()
    #
    # app = StickMaps()
    #
    # sys.exit(parent_app.exec_())
    from Gui.Windows import MainApplicationWindow

    if __name__ == '__main__':
        QCoreApplication.setOrganizationName(ORGANISATION_NAME)
        QCoreApplication.setOrganizationDomain(ORGANISATION_DOMAIN)
        QCoreApplication.setApplicationName(APPLICATION_NAME)

        parent_app = QApplication(sys.argv)
        app = MainApplicationWindow()



        sys.exit(parent_app.exec_())




