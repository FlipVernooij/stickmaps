import logging
import sys
from time import sleep

from PySide6.QtCore import QObject, Signal


class LogStream(QObject):

    _stdout = None

    is_enabled = True

    received = Signal(logging.LogRecord)

    def flush(self):
        pass

    def fileno(self):
        -1

    def send(self, record: logging.LogRecord):
        if self.is_disabled:
            return

        while self.signalsBlocked():
            sleep(0.05)

        self.received.emit(record)

    @classmethod
    def stdout(cls):
        if not cls._stdout:
            cls._stdout = cls()
            sys.stdout = cls._stdout
        return cls._stdout

    @classmethod
    def enable(cls):
        cls.is_enabled = True

    @classmethod
    def disable(cls):
        cls.is_enabled = False

class LogStreamHandler(logging.Handler):

    def emit(self, record):
        LogStream.stdout().send(record)


