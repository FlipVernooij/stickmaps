from PySide6.QtCore import QDir
from PySide6.QtGui import QIcon, Qt, QCloseEvent
from PySide6.QtWidgets import QMainWindow, QWidget, QTreeView, QDockWidget, QMessageBox, \
    QAbstractItemView, QMenu

from Config.Constants import MAIN_WINDOW_TITLE, MAIN_WINDOW_STATUSBAR_TIMEOUT, TREE_MIN_WIDTH, TREE_START_WIDTH, \
    MAIN_WINDOW_ICON
from Gui.Actions import TreeActions
from Gui.Menus import MainMenu
from Models.TreeViews import SurveyCollection
from Models.TableModels import QueryMixin


class MainApplicationWindow(QMainWindow):

    def __init__(self):
        super(MainApplicationWindow, self).__init__()

        self.central_widget = QWidget(self)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(QIcon(MAIN_WINDOW_ICON))
        self.init_database()
        self.tree_view = self.get_treenav()
        self.setup_interface()
        self.statusBar().showMessage('Loading ...', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.showMaximized()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        response = QMessageBox.question(self, 'Quit application', 'Are you sure you want to quit?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if response == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


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
        tree = QTreeView(self)
        tree.setHeaderHidden(True)
        tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree.setContextMenuPolicy(Qt.ActionsContextMenu)

        context_menu = QMenu(tree)
        actions = TreeActions(tree, context_menu)
        tree.addAction(actions.edit())

        """
            This should more or less be good, see SurveyCollection for details.
        """

        tree.setModel(SurveyCollection())

        tree.setMinimumWidth(TREE_START_WIDTH)
        tree.setMinimumWidth(TREE_MIN_WIDTH)
        tree.show()
        return tree

    def init_database(self):
        QueryMixin.init_db()
        QueryMixin.create_tables()

