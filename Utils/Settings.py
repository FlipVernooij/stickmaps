from PySide6.QtCore import QSettings

from Config.Constants import DEBUG


class Preferences:

    section_key = "Preferences"

    @classmethod
    def debug(cls) -> bool:
        return cls.get('debug', DEBUG, bool)

    @classmethod
    def get(cls, key: str, default=None, type_hint=str):
        s = QSettings()
        val = s.value(f"{cls.section_key}/{key}", None)
        if val is None:
            return default
        if type_hint is bool:
            return bool(int(val))
        return type_hint(val)

    @classmethod
    def set(cls, key: str, value):
        s = QSettings()
        s.setValue(f"{cls.section_key}/{key}", value)
        s.sync()

    @classmethod
    def get_all(cls) -> dict:
        s = QSettings()
        s.beginGroup(cls.section_key)
        keys = s.childKeys()
        all = {}
        for key in keys:
            all[key] = s.value(key, None)
        s.endGroup()
        return all

    @classmethod
    def get_everything(cls) -> dict:
        s = QSettings()
        keys = s.allKeys()
        all = {}
        for key in keys:
            all[key] = s.value(key, None)
        return all