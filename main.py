import sys

from PySide6.QtWidgets import QApplication

if __name__ == '__main__':
    # parent_app = QtWidgets.QApplication()
    #
    # app = StickMaps()
    #
    # sys.exit(parent_app.exec_())
    from Gui.Windows import MainApplicationWindow

    if __name__ == '__main__':
        parent_app = QApplication(sys.argv)

        app = MainApplicationWindow()

        sys.exit(parent_app.exec_())




