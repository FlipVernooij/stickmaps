import logging

from PySide6.QtCore import QSettings, QSize, QPoint, QMimeData
from PySide6.QtGui import QIcon, Qt, QCloseEvent, QPalette, QDrag
from PySide6.QtWidgets import QMainWindow, QWidget, QTreeView, QDockWidget, QMessageBox, \
    QAbstractItemView, QMenu, QLabel, QVBoxLayout, QScrollArea, QSizePolicy, QTextBrowser, QPushButton, QComboBox, \
    QButtonGroup, QHBoxLayout

from Config.Constants import MAIN_WINDOW_TITLE, MAIN_WINDOW_STATUSBAR_TIMEOUT, TREE_MIN_WIDTH, TREE_START_WIDTH, \
    MAIN_WINDOW_ICON, DEBUG
from Gui.Actions import TreeActions, GlobalActions
from Gui.Menus import MainMenu
from Models.ItemModels import SurveyCollection, SectionItem
from Models.TableModels import SqlManager
from Utils.Logging import LogStream
from Utils.Rendering import DragImage, ImageTest
from Utils.Settings import Preferences


class MainApplicationWindow(QMainWindow):

    def __init__(self):
        super(MainApplicationWindow, self).__init__()
        self.debug_console = None
        self.debug_console = QDockWidget('Debug console', self)
        self.debug_console.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        self.debug_console.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea | Qt.RightDockWidgetArea)
        inner = DebugConsole(self)
        self.debug_console.setWidget(inner)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.debug_console)
        self.toggle_debug_console(Preferences.get('debug', DEBUG, bool))
        self.tree_view = None
        self.map_view = MapView(self)
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.setWindowIcon(QIcon(MAIN_WINDOW_ICON))
        self.sql_manager = self.init_database()
        self.setup_interface()
        self.statusBar().showMessage('Loading ...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        self.read_settings()
        self.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        if Preferences.get('debug', DEBUG, bool) is True:
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
        self.setCentralWidget(self.map_view)
        dock = QDockWidget("Survey data", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.tree_view = SurveyOverview(self)
        dock.setWidget(self.tree_view)
        self.tree_view.show()
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

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

        model = SurveyCollection(self.main_window.sql_manager)
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
        elif item.item_type == model.ITEM_TYPE_STATION:
            menu.addAction(actions.edit_station())
            menu.addAction(actions.remove_station())

        menu.popup(self.mapToGlobal(pos))

    def mouseMoveEvent(self, event) -> None:
        item = self.selectedIndexes()
        if len(item) == 0:
            return

        item = self.model().itemFromIndex(item[0])
        if not isinstance(item, SectionItem):
            event.ignore()
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setProperty('survey_id', item.survey_id)
        mime.setProperty('section_id', item.section_id)
        mime.setProperty('section_name', item.text())
        mime.setText(item.text())

        pixmap = DragImage(section_id=item.section_id, section_name=item.text())
        drag.setPixmap(pixmap.get_pixmap())
        drag.setHotSpot(pixmap.get_cursor_location())
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)
        event.accept()


class MapView(QScrollArea):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.Light)
        self.setAcceptDrops(True)
        self.horizontalScrollBar()
        self.verticalScrollBar()

        self.show()


    # def event(self, event):
    #     if event.type() not in [event.Type.Enter]:
    #         print('scrolling')
    #     event.accept()

    def wheelEvent(self, event) -> None:
        event.accept()
        ##event.
        #QWheelEvent
        print('wheel event')

    # Drag & drop event
    def dragEnterEvent(self, event) -> None:
        event.accept()

    def dragLeaveEvent(self, event) -> None:
       event.accept()

    def dragMoveEvent(self, event) -> None:
        event.accept()

    def dropEvent(self, event):
        super().dropEvent(event)
        mime = event.mimeData()
        survey_id = mime.property('survey_id')
        section_id = mime.property('section_id')
        section_name = mime.property('section_name')

        pixmap = ImageTest(section_id=section_id, section_name=section_name)
        image = QLabel('img')
        image.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        image.setScaledContents(True)
        image.setPixmap(pixmap.get_pixmap())
        self.setWidget(image)

        event.accept()
        return



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
        self.clear_console(None)