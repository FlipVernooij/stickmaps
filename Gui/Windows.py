import logging
import os

from PySide6.QtCore import QSettings, QSize, QPoint, QMimeData, Signal, QPointF
from PySide6.QtGui import QIcon, Qt, QCloseEvent, QDrag, QPixmap, QColor, QWheelEvent, QResizeEvent
from PySide6.QtWidgets import QMainWindow, QWidget, QTreeView, QDockWidget, QMessageBox, \
    QAbstractItemView, QVBoxLayout, QTextBrowser, QPushButton, QComboBox, QHBoxLayout, QGraphicsView, QSplashScreen

from Config.Constants import MAIN_WINDOW_TITLE, MAIN_WINDOW_STATUSBAR_TIMEOUT, TREE_MIN_WIDTH, TREE_START_WIDTH, \
    MAIN_WINDOW_ICON, DEBUG, APPLICATION_SPLASH_IMAGE
from Gui.Actions import GlobalActions
from Gui.Dialogs import StartupWidget
from Gui.Scene.MainScene import MainScene
from Gui.Menus import MainMenu, ContextMenuSurvey, ContextMenuLine, ContextMenuStation, ContextMenuImports, MapsToolBar
from Models.ItemModels import ProxyModel
from Models.TableModels import SqlManager
from Utils.Logging import LogStream
from Utils.Rendering import DragImage
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

    def disable_ui(self):
        self.tree_view.setDisabled(True)
        self.map_view.setDisabled(True)
        self.menuBar().setDisabled(True)
        return

    def enable_ui(self):
        self.tree_view.setDisabled(False)
        self.map_view.setDisabled(False)
        self.menuBar().setDisabled(False)
        return

    def start_project(self, project_name: str):
        self.statusBar().showMessage(f'Project {project_name} loaded', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        self.setWindowTitle(f'{project_name} -- {MAIN_WINDOW_TITLE}')
        self.tree_view.model().reload()
        self.map_view.map_scene.reload()
        self.enable_ui()

    def __init__(self):
        super(MainApplicationWindow, self).__init__()
        self.log = logging.getLogger(__name__)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(QIcon(MAIN_WINDOW_ICON))
        self.statusBar().showMessage('Loading ...', MAIN_WINDOW_STATUSBAR_TIMEOUT)


        self.sql_manager = self.init_database()

        main_menu = MainMenu(self)
        main_menu.generate()

        self.debug_console = QDockWidget('Debug console', self)
        self.debug_console.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        self.debug_console.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea | Qt.RightDockWidgetArea)
        self.debug_console.setWidget(DebugConsole(self))
        self.addDockWidget(Qt.BottomDockWidgetArea, self.debug_console)
        self.toggle_debug_console(Preferences.get('debug', DEBUG, bool))

        self.tree_view = SurveyOverview(self)
        tree_dock = QDockWidget("Survey data", self)
        tree_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        tree_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        tree_dock.setWidget(self.tree_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, tree_dock)

        self.map_view = MapView(self)
        self.setCentralWidget(self.map_view)

        map_tools = QDockWidget("Tools", self)
        map_tools.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        map_tools.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        map_tools.setWidget(MapsToolBar(self, self.map_view))
        self.addDockWidget(Qt.RightDockWidgetArea, map_tools)

        self.read_settings()
        self.show()
        self.setFocus()

        settings = QSettings()
        file_name = settings.value('SaveFile/current_file_name', None)
        if file_name is not None and os.path.exists(file_name):
            project = SaveFile(self, file_name)
            project.open_project()
            return

        self.sql_manager.flush_db()
        wizard = StartupWidget(self)
        wizard.show()

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

    def init_database(self):
        obj = SqlManager('default_db')
        obj.create_tables()
        return obj

    def write_settings(self):
        self.log.debug('Writing settings')
        self.settings = QSettings()
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.endGroup()

    def read_settings(self):

        self.log.debug('Reading settings')
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

        menu = None
        if item.type() == item.ITEM_TYPE_IMPORTS:
            menu = ContextMenuImports(self)
        elif item.type() == item.ITEM_TYPE_SURVEY:
            menu = ContextMenuSurvey(self)
        elif item.type() == item.ITEM_TYPE_LINE:
            menu = ContextMenuLine(self)
        elif item.type() == item.ITEM_TYPE_STATION:
            menu = ContextMenuStation(self)

        if menu is None:
            return

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
    ZOOM_DEFAULT_LEVEL = 20.9
    ZOOM_MAX_LEVEL = 20.9
    ZOOM_MIN_LEVEL = 0

    # Called on a screen resize, this is ALSO TRIGGERED when opening the application and loading the view the first time.
    s_resize_viewport = Signal(QSize)
    # min zoom (world) = 0, max zoom (building) = 20.9
    s_zoom_viewport = Signal(float, QPointF)
    s_move_viewport = Signal(QPointF)
    s_rotate_viewport = Signal(int)


    # when the project changed or a new project is loaded, this signal is triggered
    s_project_changed = Signal(dict)

    # self.s_toggle_satellite.emit(None) to toggle the satellite overlay
    # self.s_toggle_satellite.emit(True) to show
    # self.s_toggle_satellite.emit(False) to hide
    s_toggle_satellite = Signal(object)


    # #  Received a mouse scroll, should get cursor location (Qpoint?) and the zoom "amount"
    # s_map_zoom = Signal(int, QPointF)
    # s_map_rotate = Signal(int, QPointF)
    # s_map_move = Signal(QPointF)
    #
    # s_show_stations = Signal(bool)
    # s_show_station_names = Signal(bool)
    # s_show_depths = Signal(bool)
    # s_toggle_satellite = Signal()
    #
    # ZOOM_MIN = 0
    # ZOOM_MAX = 21
    # ZOOM_DEFAULT = 20

    def __init__(self, parent):
        """
        To enable OpenGL rendering, you simply set a new QOpenGLWidget as the viewport of QGraphicsView by calling QGraphicsView::setViewport().
        If you want OpenGL with antialiasing, you need to set a QSurfaceFormat with the needed sample count (see QSurfaceFormat::setSamples()).
        https://doc.qt.io/qt-6/graphicsview.html

        QGraphicsView view(&scene);
        QOpenGLWidget *gl = new QOpenGLWidget();
        QSurfaceFormat format;
        format.setSamples(4);
        gl->setFormat(format);
        view.setViewport(gl);

        :param parent:
        """
        super().__init__(parent)
        self.log = logging.getLogger(__name__)
        self._current_zoom_level = self.ZOOM_DEFAULT_LEVEL
        self.map_scene = MainScene(self)
        self.setScene(self.map_scene)
        self.show()

    def get_zoom(self) -> float:
        return self._current_zoom_level

    def wheelEvent(self, event: QWheelEvent) -> None:
        return
        change = (event.angleDelta().y() / 1200) * 2.5 # 0.1 per bump * 2.5 = 0.25
        zoom = self._current_zoom_level + change
        if zoom > self.ZOOM_MAX_LEVEL:
            zoom = self.ZOOM_MAX_LEVEL
        elif zoom < self.ZOOM_MIN_LEVEL:
            zoom = self.ZOOM_MIN_LEVEL

        self._current_zoom_level = round(zoom, 2)
        self.s_zoom_viewport.emit(self._current_zoom_level, event.globalPosition())

        # @todo We should probably start of with a sensible size....

        #
        #
        # self.map_zoom = self.ZOOM_DEFAULT
        # self.map_rotate = 0
        # self.map_move = 0
        #
        # self.show_stations = True
        # self.show_station_names = True
        # self.show_depths = True
        #
        # self.s_map_move.connect(self.c_map_move)
        # self.s_map_rotate.connect(self.c_map_rotate)
        # self.s_map_zoom.connect(self.c_map_zoom)
        #
        # self.s_show_stations.connect(self.c_show_stations)
        # self.s_show_station_names.connect(self.c_show_station_names)
        # self.s_show_depths.connect(self.c_show_depths)
        #
        # self.s_toggle_satellite.connect(self.c_toggle_satellite)



        # self.map_scene.load_map_from_database()


        # self.setAcceptDrops(True)
        #self.show()

    def resizeEvent(self, event: QResizeEvent):
        self.s_resize_viewport.emit(event.size())

    #
    # def c_map_zoom(self, zoom: int, zoom_center: QPointF):
    #     """
    #     For zooming we will use the google/bing zooming logic.
    #
    #     zoom 0 represents to hole world in a single tile
    #     every zoom-level doubles the amount of tiles IN BOTH DIRECTIONS:
    #
    #      zoom 0   1
    #      zoom 1   1|1
    #               1|1
    #      zoom 2   1|1|1|1
    #               1|1|1|1
    #               1|1|1|1
    #               1|1|1|1
    #      and so on.
    #
    #      This means that every zoom-level increases or decreases the shown grounds-area by a factor of 2.
    #
    #
    #     https://www.microimages.com/documentation/TechGuides/80TilesetZoom.pdf
    #
    #     :param zoom:
    #     :param zoom_center:
    #     :return:
    #     """
    #     if zoom < 0:
    #         zoom = 0  # is world
    #
    #     self.log.warning(f'zoom: {zoom} map_zoom: {self.map_zoom}')
    #     #self.log.warning(f'position: {event.position().toPoint()} = {self.mapToScene(event.position().toPoint())}')
    #     #sself.log.warning(f'globalPosition: {event.globalPosition().toPoint()} = {self.mapToScene(event.globalPosition().toPoint())}')
    #
    #     # @todo
    #     # This this.sceneRect() is the size of the total view...
    #     # When scaling on the cursor position, when reaching the edge of the sceneRect... the zoom will loose the cursor position.
    #     # When this happends we need to ... somehow enlarge the screenRect.
    #     # We probably need a max zoom for that...
    #     # now the question is, are we going to
    #     #   -support endless zoom?
    #     # Or are we just going to limit it at some extrodenairy large size.
    #
    #     # Blalalllajsdhkjas kasjhkjsahdv = sdfdsfdsfds
    #
    #
    #     # Set Anchors (zoom_center)
    #     self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
    #     self.setResizeAnchor(QGraphicsView.NoAnchor)
    #
    #     # Save the scene pos
    #     oldPos = self.mapToScene(zoom_center.toPoint())
    #
    #     # Zoom
    #     # Zoom Factor
    #
    #     zoomInFactor = 1.25
    #     zoomOutFactor = -1 / zoomInFactor
    #
    #     zoom_in_factor = 2
    #     zoom_out_factor = -2
    #
    #     if self.map_zoom < zoom:
    #         zoomFactor = zoom_in_factor
    #     elif self.map_zoom > zoom:
    #         zoomFactor = zoom_out_factor
    #     else:
    #         return
    #
    #
    #
    #     self.scale(zoomFactor, zoomFactor)
    #
    #     #self.log.warning(f'NEW position: {event.position().toPoint()} = {self.mapToScene(event.position().toPoint())}')
    #     #self.log.warning(f'NEW globalPosition: {event.globalPosition().toPoint()} = {self.mapToScene(event.globalPosition().toPoint())}')
    #     # Get the new position
    #     #newPos = self.mapToScene(zoom_center.toPoint())
    #
    #     # Move scene to old position
    #     #delta = newPos - oldPos
    #     # self.translate(delta.x(), delta.y())
    #
    #     self.map_zoom = zoom
    #
    # def c_map_rotate(self, degrees: int, cursor_location: QPoint):
    #     self.log.debug(f'Signal map_rotate({degrees}, {cursor_location})')
    #
    # def c_map_move(self, move_to: QPoint):
    #     self.log.debug(f'Signal map_move({move_to})')
    #
    # def c_show_stations(self, show: bool):
    #     self.log.debug(f'Signal show_stations({show})')
    #
    # def c_show_station_names(self, show: bool):
    #     self.log.debug(f'Signal show_station_namess({show})')
    #
    # def c_show_depths(self, show: bool):
    #     self.log.debug(f'Signal show_depths({show})')
    #
    # def c_toggle_satellite(self):
    #     self.log.debug(f'Signal c_toggle_satellite')
    #     self.map_scene.reload()
    #
    #
    #
    # def wheelEvent(self, event: QWheelEvent) -> None:
    #     # numPixels = event.pixelDelta()
    #     zoom = self.map_zoom + (event.angleDelta().y() / 120)  # increase zoom-lvl with 1 per "scoll-teeth"
    #     self.s_map_zoom.emit(zoom, event.globalPosition())
    #     event.accept()
    #
    # def resizeEvent(self, event: QResizeEvent) -> None:
    #     pass
    #
    #



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