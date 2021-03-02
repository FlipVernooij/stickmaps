from PySide6.QtGui import QIcon, Qt, QCloseEvent
from PySide6.QtWidgets import QMainWindow, QWidget, QTreeView, QDockWidget, QMessageBox, \
    QAbstractItemView, QMenu

from Config.Constants import MAIN_WINDOW_TITLE, MAIN_WINDOW_STATUSBAR_TIMEOUT, TREE_MIN_WIDTH, TREE_START_WIDTH, \
    MAIN_WINDOW_ICON
from Gui.Actions import TreeActions
from Gui.Menus import MainMenu
from Models.ItemModels import SurveyCollection
from Models.TableModels import QueryMixin


class MainApplicationWindow(QMainWindow):

    def __init__(self):
        super(MainApplicationWindow, self).__init__()
        self.tree_view = None
        self.central_widget = QWidget(self)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(QIcon(MAIN_WINDOW_ICON))
        self.init_database()
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
        self.tree_view = SurveyOverview(self)
        dock.setWidget(self.tree_view)
        self.tree_view.show()
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def init_database(self):
        QueryMixin.init_db()
        QueryMixin.create_tables()


class SurveyOverview(QTreeView):

    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent

        self.setHeaderHidden(True)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.build_contextmenu)

        model = SurveyCollection()
        self.setModel(model)

        self.setMinimumWidth(TREE_START_WIDTH)
        self.setMinimumWidth(TREE_MIN_WIDTH)

    def build_contextmenu(self, pos):
        menu = QMenu(self)
        # menu.entry = self.tree_view.entry
        actions = TreeActions(self, menu)
        if len(self.selectedIndexes()) == 0:
            return  # add import menu here!

        index = self.selectedIndexes()[0]
        model = index.model()
        item = model.itemFromIndex(index)

        if item.item_type == model.ITEM_TYPE_SURVEY:
            menu.addAction(actions.edit_survey())
            menu.addAction(actions.edit_sections())
            menu.addAction(actions.remove_survey())
        elif item.item_type == model.ITEM_TYPE_SECTION:
            menu.addAction(actions.edit_section())
            menu.addAction(actions.edit_stations())
            menu.addAction(actions.remove_section())
        elif item.item_type == model.ITEM_TYPE_SECTION:
            menu.addAction(actions.edit_station())

        menu.popup(self.mapToGlobal(pos))
