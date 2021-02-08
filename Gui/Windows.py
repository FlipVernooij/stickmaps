from PySide6.QtCore import QStringListModel
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QTreeView, QDockWidget

from Config.Constants import MAIN_WINDOW_TITLE, MAIN_WINDOW_STATUSBAR_TIMEOUT, TREE_MIN_WIDTH, TREE_START_WIDTH, \
    MAIN_WINDOW_ICON
from Gui.Menus import MainMenu
from Models.TreeViews import SurveyCollection
from Models.PointModel import Point
from Models.SectionModel import Section
from Models.SurveyModel import Survey

class MainApplicationWindow(QMainWindow):

    def __init__(self):
        super(MainApplicationWindow, self).__init__()

        self.central_widget = QWidget(self)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(QIcon(MAIN_WINDOW_ICON))
        self.tree_view = self.get_treenav()
        self.setup_interface()
        self.statusBar().showMessage('Loading ...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        self.init_database()
        self.showMaximized()

    def setup_interface(self):
        main_menu = MainMenu(self)
        main_menu.generate()

        self.setCentralWidget(self.central_widget)
        dock = QDockWidget("Survey data", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setWidget(self.tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def get_treenav(self):
        tree_view = QTreeView()
        tree_model = SurveyCollection.get_instance()
        tree_view.setModel(tree_model)
        tree_view.setMinimumWidth(TREE_START_WIDTH)
        tree_view.setMinimumWidth(TREE_MIN_WIDTH)
        tree_view.show()
        return tree_view

    def init_database(self):
        Survey.create_database_tables()
        Section.create_database_tables()
        Point.create_database_tables()