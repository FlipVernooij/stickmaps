import sys

from PySide6.QtWidgets import QApplication

from Gui.Dialogs import ErrorDialog

if __name__ == '__main__':
    # parent_app = QtWidgets.QApplication()
    #
    # app = StickMaps()
    #
    # sys.exit(parent_app.exec_())
    from Gui.Windows import MainApplicationWindow

    if __name__ == '__main__':
        parent_app = QApplication(sys.argv)  ## get as singleton QApplication.instance()
        app = MainApplicationWindow()

        sys.exit(parent_app.exec_())




