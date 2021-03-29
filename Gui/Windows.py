import logging
import os

from PySide6.QtCore import QSettings, QSize, QPoint, QMimeData, Signal
from PySide6.QtGui import QIcon, Qt, QCloseEvent, QPalette, QDrag, QScreen, QPixmap, QColor
from PySide6.QtWidgets import QMainWindow, QWidget, QTreeView, QDockWidget, QMessageBox, \
    QAbstractItemView, QVBoxLayout, QTextBrowser, QPushButton, QComboBox, QHBoxLayout, QGraphicsView, QToolBar, \
    QSplashScreen

from Config.Constants import MAIN_WINDOW_TITLE, MAIN_WINDOW_STATUSBAR_TIMEOUT, TREE_MIN_WIDTH, TREE_START_WIDTH, \
    MAIN_WINDOW_ICON, DEBUG, APPLICATION_SPLASH_IMAGE
from Gui.Actions import GlobalActions
from Gui.Dialogs import NewProjectDialog, StartupWidget
from Gui.Menus import MainMenu, ContextMenuSurvey, ContextMenuLine, ContextMenuStation, ContextMenuImports
from Models.ItemModels import ProxyModel
from Models.TableModels import SqlManager
from Utils.Logging import LogStream
from Utils.Rendering import DragImage, MapScene
from Utils.Settings import Preferences
from Utils.Storage import SaveFile


class Splash(QSplashScreen):

    def __init__(self):
        super().__init__()
        self.setPixmap(QPixmap(APPLICATION_SPLASH_IMAGE))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

    def showMessage(self, message: str, alignment: int = Qt.AlignBottom, color: QColor = Qt.white) -> None:
        super().showMessage(message, alignment, color)


class MainApplicationWindow(QMainWindow):

    def __init__(self):
        super(MainApplicationWindow, self).__init__()
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(QIcon(MAIN_WINDOW_ICON))
        self.statusBar().showMessage('Loading ...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        self.read_settings()

        self.sql_manager = self.init_database()


        self.debug_console = QDockWidget('Debug console', self)
        self.debug_console.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        self.debug_console.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea | Qt.RightDockWidgetArea)
        inner = DebugConsole(self)
        self.debug_console.setWidget(inner)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.debug_console)
        self.toggle_debug_console(Preferences.get('debug', DEBUG, bool))

        dock = QDockWidget("Survey data", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.tree_view = SurveyOverview(self)
        dock.setWidget(self.tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        self.map_view = MapView(self)
        self.setCentralWidget(self.map_view)

        self.setup_interface()

        self.show()
        self.setFocus()
        # settings = QSettings()
        # file_name = settings.value('SaveFile/current_file_name', None)
        # if file_name is not None and os.path.exists(file_name):
        #     project = SaveFile(self, file_name)
        #     project.open_project()
        #     return
        self.sql_manager.flush_db()
        new_file = StartupWidget(self)
        new_file.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        if Preferences.get('debug', DEBUG, bool) is True:
            self.write_settings()
            event.accept()
            return

        response = QMessageBox.question(self, 'Quit application', 'Are you sure you want to quit?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if response == QMessageBox.Yes:
            self.write_settings()
            actions = GlobalActions(self)
            actions._check_if_save_required()
            self.sql_manager.drop_tables()
            event.accept()
        else:
            event.ignore()

    def setup_interface(self):
        main_menu = MainMenu(self)
        main_menu.generate()




        tools = QDockWidget("Tools", self)
        tools.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        tools.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        tools.setWidget(QToolBar("Test this toolbar", self))
        self.addDockWidget(Qt.RightDockWidgetArea, tools)

    def init_database(self):
        obj = SqlManager('default_db')
        obj.create_tables()
        return obj

    def write_settings(self):
        self.settings = QSettings()
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.endGroup()

    def read_settings(self):
        self.settings = QSettings()
        self.settings.beginGroup("MainWindow")
        self.resize(self.settings.value("size", QSize(400, 400)))
        self.move(self.settings.value("pos", QPoint(200, 200)))
        self.settings.endGroup()

        self.settings.setValue('SaveFile/is_changed', False)

    def toggle_debug_console(self, show: bool = True):
        if show is True:
            LogStream.enable()
            self.debug_console.show()
        else:
            self.debug_console.hide()
            LogStream.disable()


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

        model = ProxyModel(self.main_window.sql_manager)
        self.setModel(model)

        self.setMinimumWidth(TREE_START_WIDTH)
        self.setMinimumWidth(TREE_MIN_WIDTH)

    def get_selected_item(self):
        if len(self.selectedIndexes()) == 0:
            return None

        index = self.selectedIndexes()[0]
        model = index.model()
        item = model.itemFromIndex(index)
        return item

    def build_contextmenu(self, pos):
        item = self.get_selected_item()
        if item is None:
            return

        if item.type() == item.ITEM_TYPE_IMPORTS:
            menu = ContextMenuImports(self)
        elif item.type() == item.ITEM_TYPE_SURVEY:
            menu = ContextMenuSurvey(self)
        elif item.type() == item.ITEM_TYPE_LINE:
            menu = ContextMenuLine(self)
        elif item.type() == item.ITEM_TYPE_STATION:
            menu = ContextMenuStation(self)

        menu.popup(self.mapToGlobal(pos))

    def mouseMoveEvent(self, event) -> None:
        item = self.get_selected_item()
        if item is None:
            event.ignore()
            return

        if item.type() is not item.ITEM_TYPE_LINE:
            event.ignore()
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setProperty('survey_id', item.survey_id())
        mime.setProperty('line_id', item.line_id())
        mime.setProperty('line_name', item.text())
        mime.setText(item.text())

        pixmap = DragImage(line_id=item.line_id())
        drag.setPixmap(pixmap.get_pixmap())
        drag.setHotSpot(pixmap.get_cursor_location())
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)
        event.accept()


class MapView(QGraphicsView):

    #  Received a mouse scroll, should get cursor location (Qpoint?) and the zoom "amount"
    s_map_scale = Signal(int, QPoint)
    s_map_rotate = Signal(int, QPoint)
    s_map_move = Signal(QPoint)

    s_show_stations = Signal(bool)
    s_show_station_names = Signal(bool)
    s_show_depths = Signal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.log = logging.getLogger(__name__)

        self.map_scale = 1
        self.map_rotate = 0
        self.map_move = 0

        self.show_stations = True
        self.show_station_names = True
        self.show_depths = True

        self.s_map_move.connect(self.c_map_move)
        self.s_map_rotate.connect(self.c_map_rotate)
        self.s_map_scale.connect(self.c_map_scale)

        self.s_show_stations.connect(self.c_show_stations)
        self.s_show_station_names.connect(self.c_show_station_names)
        self.s_show_depths.connect(self.c_show_depths)

        self.map_scene = MapScene(self)
        self.setScene(self.map_scene)

        self.map_scene.load_map_from_database()

        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Light)
        self.setAcceptDrops(True)
        self.show()

    def c_map_scale(self, zoom: int, cursor_location: QPoint):
        self.log.debug(f'Signal map_scale({zoom}, {cursor_location})')

    def c_map_rotate(self, degrees: int, cursor_location: QPoint):
        self.log.debug(f'Signal map_rotate({degrees}, {cursor_location})')

    def c_map_move(self, move_to: QPoint):
        self.log.debug(f'Signal map_move({move_to})')

    def c_show_stations(self, show: bool):
        self.log.debug(f'Signal show_stations({show})')

    def c_show_station_names(self, show: bool):
        self.log.debug(f'Signal show_station_namess({show})')

    def c_show_depths(self, show: bool):
        self.log.debug(f'Signal show_depths({show})')

    # def event(self, event):
    #     if event.type() not in [event.Type.Enter]:
    #         print('scrolling')
    #     event.accept()
    #
    # def wheelEvent(self, event) -> None:
    #     event.accept()
    #     ##event.
    #     #QWheelEvent
    #     print('wheel event')

    # # Drag & drop event
    # def dragEnterEvent(self, event) -> None:
    #     event.accept()
    #
    # def dragLeaveEvent(self, event) -> None:
    #    event.accept()
    #
    # def dragMoveEvent(self, event) -> None:
    #     event.accept()
    #
    # def dropEvent(self, event):
    #     super().dropEvent(event)
    #     mime = event.mimeData()
    #     survey = self.import_survey.get(int(mime.property('survey_id')))
    #     line = self.import_line.get(int(mime.property('line_id'))
    #
    #
    #     event.accept()
    #     return


class DebugConsole(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.console = QTextBrowser(self)
        self.clear_button = QPushButton(self)
        self.clear_button.setText('clear')

        layout = QVBoxLayout()
        layout.addWidget(self.console)


        self.clear_button.clicked.connect(self.clear_console)

        self.log_level_combo = QComboBox(self)
        self.log_level_combo.addItems([
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL"
        ])
        self.log_level_combo.setCurrentText(logging.getLevelName(logging.root.level))
        self.log_level_combo.currentTextChanged.connect(self.set_loglevel)
        b_group = QHBoxLayout()
        b_group.addWidget(self.log_level_combo)
        b_group.addWidget(self.clear_button)
        layout.addLayout(b_group)
        self.setLayout(layout)

        LogStream.stdout().received.connect(self.stdout_received)

    def stdout_received(self, record: logging.LogRecord):
        mesg = self.format_record(record)
        all_text = self.console.toHtml()
        self.console.setHtml(mesg+all_text)

    def format_record(self, record):
        color_lookup = {
            'DEBUG': 'green',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'orange',
            'CRITICAL': 'red',
            'stdout': 'purple'
        }
        r = record
        if r.name == 'stdout':
            return f'<label style="color:{color_lookup[r.name]}">{r.name}</label> # <strong>{r.msg}</strong>'

        return f'<label style="color:{color_lookup[r.levelname]}">{r.levelname} - {r.name}</label> -> {r.filename}:{r.funcName}():{r.lineno} # <strong>{r.msg}</strong>'

    def clear_console(self, event):
        self.console.setHtml('')

    def set_loglevel(self, loglevel: str):
        logging.getLogger().setLevel(getattr(logging, loglevel))
        Preferences.set('debug_loglevel', getattr(logging, loglevel))
        self.clear_console(None)