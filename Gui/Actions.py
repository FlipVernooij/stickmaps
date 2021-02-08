import pathlib

from PySide6 import QtCore
from PySide6.QtGui import QAction

from pprint import pprint

from PySide6.QtWidgets import QFileDialog

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT
from Gui.Dialogs import ErrorDialog
from Importers.Mnemo import MnemoImporter
from Models.SurveyData import RawDataModel


class GlobalActions:

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def exit_application(self):
        action = QAction('Exit', self.parent_window)
        action.setShortcut('Ctrl+Q')
        action.triggered.connect(self.parent_window.close)
        return action

    def mnemo_connect_to(self):
        action = QAction('Connect to Mnemo', self.parent_window)
        action.triggered.connect(lambda: self.mnemo_connect_to_callback())
        return action

    def mnemo_connect_to_callback(self):
        self.parent_window.statusBar().showMessage('Connection to Mnemo...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        try:
            dmp = MnemoImporter()
            dmp.read_from_device()
            RawDataModel.appendSurvey(dmp.get_data())
        except ConnectionError as err_mesg:
            ErrorDialog.show_error(self.parent_window, str(err_mesg))

    def mnemo_load_dump_file(self):
        action = QAction('Load Mnemo .dmp file', self.parent_window)
        action.triggered.connect(lambda: self.mnemo_load_dump_file_callback())
        return action

    def mnemo_load_dump_file_callback(self):
        self.parent_window.statusBar().showMessage('Loading mnemo dump file...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        try:
            file = QFileDialog(self.parent_window)

            options = file.Options()
            options |= file.DontUseNativeDialog

            file.setOptions(options)
            file.setWindowTitle('Select Mnemo .dmp file to load')
            file.setNameFilters(['Mnemo dump file (*.dmp)', 'All files (*)'])
            file.setDirectory(str(pathlib.Path.home()))

            if file.exec() == QFileDialog.Accepted:
                file_name = file.selectedFiles()[0]
                dmp = MnemoImporter()
                dmp.read_dump_file(file_name)
                RawDataModel.append_survey(dmp.get_data())

        except Exception as err_mesg:
            ErrorDialog.show_error(self.parent_window, str(err_mesg))
