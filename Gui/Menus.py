from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QFileDialog

from Gui.Dialogs import ErrorDialog
from Importers.Mnemo import MnemoImporter
from Models.SurveyData import RawDataModel


class MainMenu:

    def __init__(self, main_window):
        self.main_window = main_window

    def generate(self):
        self.set_file_menu()
        self.set_import_menu()

    def set_file_menu(self):
        mb = self.main_window.menuBar()
        fm = mb.addMenu('File')

        exit_action = QAction('Exit', self.main_window)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.main_window.close)

        fm.addAction(exit_action)

    def set_import_menu(self):
        mb = self.main_window.menuBar()
        fm = mb.addMenu('Import')

        import_mnemo = QAction('Connect to Mnemo', self.main_window)
        import_mnemo.triggered.connect(self.connect_mnemo)
        fm.addAction(import_mnemo)

        import_mnemo_dmp = QAction('Load Mnemo dump file', self.main_window)
        import_mnemo_dmp.triggered.connect(self.load_mnemo_dmp)
        fm.addAction(import_mnemo_dmp)

    def connect_mnemo(self):
        self.main_window.statusBar().showMessage('Connection to Mnemo...', self.main_window.STATUSBAR_TIMEOUT)
        try:
            dmp = MnemoImporter()
            dmp.read_from_device()
            RawDataModel.appendSurvey(dmp.get_data())
        except ConnectionError as err:
            err = ErrorDialog(self.main_window)
            err.show(str(err))

    def load_mnemo_dmp(self):
        self.main_window.statusBar().showMessage('Loading mnemo dump file...', self.main_window.STATUSBAR_TIMEOUT)
        try:
            file = QFileDialog(self)

            options = file.Options()
            options |= file.DontUseNativeDialog

            file.setWindowTitle('Select Mnemo .dmp file to load')
            file.setNameFilter('Mnemo dump files (*.dmp)')
            file_name, _ = file.getOpenFileName()

            if not file_name:
                return

            dmp = MnemoImporter()
            dmp.read_dump_file()
            RawDataModel.appendSurvey(dmp.get_data())
        except Exception as err:
            err = ErrorDialog(self.main_window)
            err.show(str(err))