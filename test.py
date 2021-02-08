import sys
from pprint import pprint

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QApplication, QMainWindow

from Gui.Actions import GlobalActions


class MainApplicationWindow(QMainWindow):
    def __init__(self):
        super(MainApplicationWindow, self).__init__()
        self.setWindowTitle('TEST QAction')
        self.setWindowIcon(QIcon('Assets/windowIcon.png'))

        mb = self.menuBar()
        fm = mb.addMenu('File')

        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        fm.addAction(exit_action)

        fm.addAction(GlobalActions.wtf(self))
        fm.addAction(GlobalActions.mnemo_connect_to(self))

        self.statusBar().showMessage('Loading ...', 5000)
        self.showMaximized()

    def wtf(self):
        pprint(self)


if __name__ == '__main__':

    if __name__ == '__main__':
        parent_app = QApplication(sys.argv)

        app = MainApplicationWindow()

        sys.exit(parent_app.exec_())
