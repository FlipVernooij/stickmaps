from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QToolBar

from Gui.Actions import GlobalActions, TreeActions, MapToolbarActions


class MainMenu:

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def generate(self):
        self.set_file_menu()
        self.set_edit_menu()
        self.set_import_menu()
        self.set_help_menu()

    def set_file_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('File')

        fm.addAction(actions.new())
        fm.addAction(actions.open())
        fm.addAction(actions.save())
        fm.addAction(actions.save_as())
        fm.addAction(self._separator())
        fm.addAction(actions.preferences())
        fm.addAction(self._separator())
        fm.addAction(actions.exit_application())

    def set_edit_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('Edit')

    def set_help_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('Help')

        fm.addAction(actions.documentation())
        fm.addAction(actions.about_qt())

    def set_import_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('Import')
        fm.addAction(actions.mnemo_connect_to())
        fm.addAction(actions.mnemo_load_dump_file())
        fm.addAction(self._separator())
        fm.addAction(actions.mnemo_dump())

    def _separator(self):
        action = QAction()
        action.setSeparator(True)
        return action

class MapsToolBar(QToolBar):

    def __init__(self, parent, map_view):
        super().__init__(parent)
        self.map_view = map_view

        actions = MapToolbarActions(self, self.map_view)
        self.addAction(actions.toggle_satellite())

        self.addAction(actions.zoom_in())
        self.addAction(actions.zoom_out())

class ContextMenuImports(QMenu):
    def __init__(self, parent):
        super().__init__()
        actions = TreeActions(parent, self)
        self.addAction(actions.edit_surveys())
        self.addAction(actions.remove_surveys())


class ContextMenuSurvey(QMenu):
    def __init__(self, parent):
        super().__init__()
        actions = TreeActions(parent, self)
        self.addAction(actions.edit_survey())
        self.addAction(actions.edit_lines())
        self.addAction(actions.remove_empty_lines())
        self.addAction(actions.remove_survey())
        self.addAction(actions.save_survey_to_dmp_file())


class ContextMenuLine(QMenu):
    def __init__(self, parent):
        super().__init__()
        actions = TreeActions(parent, self)
        self.addAction(actions.edit_line())
        self.addAction(actions.edit_stations())
        self.addAction(actions.remove_line())


class ContextMenuStation(QMenu):
    def __init__(self, parent):
        super().__init__()
        actions = TreeActions(parent, self)
        self.addAction(actions.edit_station())
        self.addAction(actions.remove_station())

