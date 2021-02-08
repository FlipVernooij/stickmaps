from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog

from Gui.Actions import GlobalActions
from Gui.Dialogs import ErrorDialog
from Importers.Mnemo import MnemoImporter
from Models.SurveyData import RawDataModel


class MainMenu:

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def generate(self):
        self.set_file_menu()
        self.set_import_menu()

    def set_file_menu(self):
        actions = GlobalActions(self.parent_window)

        mb = self.parent_window.menuBar()
        fm = mb.addMenu('File')
        fm.addAction(actions.exit_application())

    def set_import_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('Import')

        fm.addAction(actions.mnemo_connect_to())
        fm.addAction(actions.mnemo_load_dump_file())

