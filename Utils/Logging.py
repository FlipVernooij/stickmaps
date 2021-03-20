import logging
import sys
from datetime import datetime
from time import sleep

from PySide6.QtCore import QObject, Signal


class Track():

    TIME_START = {}

    @classmethod
    def timer_start(cls, name='default'):
        if name in cls.TIME_START.keys():
            raise Exception(f'timer_start: name {name} already running, call times_stop() first')
        cls.TIME_START[name] = datetime.now().timestamp()

    @classmethod
    def timer_end(cls, name='default'):
        end = datetime.now().timestamp()
        if name not in cls.TIME_START.keys():
            raise Exception('timer_end: name {name} is not running, call times_start() first')
        start = cls.TIME_START[name]
        del cls.TIME_START[name]
        return end - start


class LogStream(QObject):

    _stdout = None

    is_enabled = True

    received = Signal(logging.LogRecord)

    def flush(self):
        pass

    def fileno(self):
        -1

    def write(self, mesg: str):
        if mesg.strip() != '':
            log = logging.LogRecord(name='stdout', level=logging.INFO, msg=mesg, pathname=None, lineno=None, args=None, exc_info=None)
            self.send(log)

    def send(self, record: logging.LogRecord):
        if self.is_enabled is False:
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


