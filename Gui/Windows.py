from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMainWindow

from Gui.Menus import MainMenu


class MainApplicationWindow(QMainWindow):

    WINDOW_TITLE = 'StickMaps'

    STATUSBAR_TIMEOUT = 3000

    def __init__(self):
        super(MainApplicationWindow, self).__init__()
        self.setWindowTitle(self.WINDOW_TITLE)
# self.setWindowIcon(QIcon('../Assets/windowIcon.png'))
        # self.setup_interface()
        self.statusBar().showMessage('Loading ...', self.STATUSBAR_TIMEOUT)


        #exit_action = QAction('Exit')
        #exit_action.setShortcut('Ctrl+Q')
        #exit_action.triggered.connect(self.close)

        #mb = self.menuBar()
        #fm = mb.addMenu('File')
        #fm.addAction(exit_action)

        self.showMaximized()

    def setup_interface(self):
        # main_menu = MainMenu(self)
        # main_menu.generate()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        mb = self.menuBar()
        fm = mb.addMenu('&File')
        fm.addAction(exit_action)
