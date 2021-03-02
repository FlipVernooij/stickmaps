import codecs
import mimetypes
import zlib

from PySide6.QtWidgets import QMessageBox

from Config.Constants import APPLICATION_VERSION, APPLICATION_NAME
from Models.TableModels import QueryMixin
import json

class SurveyData():

    def __init__(self, file_path):
        self.file_path = file_path

    def save_to_file(self):
        save = {
            'version': APPLICATION_VERSION,
            'database': QueryMixin.dump_tables()
        }
        data = self._encode(save)
        self._write(data)

    def load_from_file(self) -> bool:
        data = self._open_file()
        if data['version'] != APPLICATION_VERSION:
            QMessageBox.warning(None, APPLICATION_NAME, """
            You are attempting to load a file with a newer version number then this application.\n
            In order to load this file successfully, please update this application to its newest version.
            """)
            return
        return self._load_to_db(data['database'])

    def load_new(self) -> bool:
        QueryMixin.drop_tables()
        QueryMixin.create_tables()
        return True

    def _open_file(self) -> dict:
        data = self._read()
        data = self._decode(data)
        return data

    def _load_to_db(self, table_data) -> bool:

        QueryMixin.drop_tables()
        QueryMixin.create_tables()
        QueryMixin.load_table_data(table_data)
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
