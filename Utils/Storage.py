import codecs
import mimetypes
import zlib

from Config.Constants import APPLICATION_VERSION
from Models.TableModels import QueryMixin
import json

class Save():

    def __init__(self, file_path):
        self.file_path = file_path

    def save_to_file(self):
        save = {
            'version': APPLICATION_VERSION,
            'database': QueryMixin.dump_tables()
        }
        data = self._encode(save)
        self._write(data)

    def open_from_file(self) -> str:
        types = mimetypes.MimeTypes().guess_type(self.file_path)
        data = self._read()
        data = self._decode(data)
        return data

    def _write(self, data) -> bool:
        with open(self.file_path, 'wb') as fp:
            fp.write(data)

    def _read(self):
        with open(self.file_path, 'rb') as fp:
            data = fp.read()
        return data

    def _decode(self, data) -> bytes:
        uncompressed = zlib.decompress(data[::-1])
        return json.loads(uncompressed)

    def _encode(self, data: dict) -> bytes:
        json_str = json.dumps(data)
        return zlib.compress(bytes(json_str, 'utf8'))[::-1]
