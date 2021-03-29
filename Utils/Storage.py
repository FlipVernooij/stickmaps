import codecs
import mimetypes
import os
import zlib

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from Config.Constants import APPLICATION_VERSION, APPLICATION_NAME, MAIN_WINDOW_STATUSBAR_TIMEOUT, MAIN_WINDOW_TITLE
from Models.TableModels import SqlManager, ProjectSettings
import json

class SaveFile():

    def __init__(self, parent, file_path=None):
        self.parent = parent
        self.settings = QSettings()
        if file_path is None:
            file_path = self.settings.value('SaveFile/current_file_name', None)
        self.file_path = file_path
        self.sql_manager = SqlManager()

    def check_if_save_required(self):
        if self.settings.value('SaveFile/is_changed', False) is True:
            response = QMessageBox.question(self.parent, 'Save current changes?',
                                            'You have a file with pending changes. \n Do you want to save changes?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if response == QMessageBox.Yes:
                self.save_to_file()

    def save_to_file(self):
        save = {
            'version': APPLICATION_VERSION,
            'database':  self.sql_manager.dump_tables()
        }
        data = self._encode(save)
        self._write(data)

    def open_project(self) -> bool:
        data = self._open_file()
        if data['version'] != APPLICATION_VERSION:
            QMessageBox.warning(None, APPLICATION_NAME, """
            You are attempting to load a file with a newer version number then this application.\n
            In order to load this file successfully, please update this application to its newest version.
            """)
            return
        self.parent.tree_view.setDisabled(True)
        self.parent.map_view.setDisabled(True)
        self.parent.menuBar().setDisabled(True)

        self._load_to_db(data['database'])
        project = self.sql_manager.factor(ProjectSettings)
        data = project.get()
        self._update_ui(data['project_name'])

    def create_new_project(self, project_name, latitude, longitude) -> bool:
        settings = QSettings()
        settings.setValue('SaveFile/current_file_name', self.file_path)
        settings.setValue('SaveFile/last_path', os.path.dirname(self.file_path))
        settings.setValue('SaveFile/is_changed', False)
        self.sql_manager.flush_db()
        sql = self.sql_manager.factor(ProjectSettings)
        sql.insert(project_name, latitude, longitude)
        self._update_ui(project_name)
        return True

    def _update_ui(self, project_name):
        self.parent.statusBar().showMessage(f'Project {project_name} loaded', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        self.parent.setWindowTitle(f'{project_name} -- {MAIN_WINDOW_TITLE}')
        self.parent.tree_view.model().reload()
        self.parent.tree_view.setDisabled(False)
        self.parent.map_view.setDisabled(False)
        self.parent.menuBar().setDisabled(False)

    def _open_file(self) -> dict:
        data = self._read()
        data = self._decode(data)
        return data

    def _load_to_db(self, table_data) -> bool:
        self.sql_manager.flush_db()
        self.sql_manager.load_table_data(table_data)
        return True

    def _write(self, data) -> bool:
        with open(self.file_path, 'wb') as fp:
            fp.write(data)

    def _read(self):
        with open(self.file_path, 'rb') as fp:
            data = fp.read()
        return data

    def _decode(self, data) -> dict:
        uncompressed = zlib.decompress(data)
        return json.loads(uncompressed)

    def _encode(self, data: dict) -> bytes:
        json_str = json.dumps(data)
        return zlib.compress(bytes(json_str, 'utf8'))
