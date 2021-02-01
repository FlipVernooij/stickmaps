import argparse
import logging
from pprint import pprint

import serial
from PySide6.QtWidgets import QApplication
from serial.tools import list_ports
from datetime import datetime
import time

import sys
from PySide6 import QtGui, QtWidgets

class SurveyData:

    def __init__(self):
        self.explorers = []
        self.date = datetime.now()
        self.sections = []

    def add_explorer(self, name):
        self.add_explorers([name])

    def add_explorers(self, names):
        self.explorers.extend(names)




class SectionData:

    def __init__(self):
        self.lines = []
        self.name = None


class DataPoint:

    def __init__(
            self,
            depth: int,
            azimut_in: int = 0,
            azimut_out: int = 0,
            length_in: int = 0,
            length_out: int = 0,
            temp: int = None
    ):
        self.depth = depth
        self.azimut_in = azimut_in
        self.azimut_out = azimut_out
        self.length_in = length_in
        self.length_out = length_out
        self.temp = temp


class DataStruct:

    DEVICE_UNKNOWN = 'unknown'
    DEVICE_MNEMO = 'mnemo'

    def __init__(self, device='unknown'):
        self.device = device
        self.line = []

    def add_point(self, point: DataPoint) -> int:
        self.line.append(point)
        return len(self.line) - 1


class MnemoDataAdapter:

    DEVICE_DESCRIPTION = "MCP2221 USB-I2C/UART Combo"

    def __init__(self, device=None, baudrate=9600, timeout=1, verbose=0):
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout
        self.verbose = verbose

        self.import_string = None

    def get_device_location(self, device=None):
        if device is None:
            ports = list_ports.comports()
            for port in ports:
                if port.description == self.DEVICE_DESCRIPTION:
                    device = port.device

        if not device:
            raise ConnectionError("Can not find Mnemo device, please specify using --device /dev/tty*")

        return device

    def read_from_device(self):
        try:
            self.device = self.get_device_location(self.device)
            ser = serial.Serial(self.device, self.baudrate, timeout=self.timeout, bytesize=8, stopbits=1, parity='N')
            ser.flushInput()
            ser.flushOutput()

            ser.write(b'C')
            time.sleep(.1)
            now = datetime.now()
            dt = [
                now.strftime("%y").encode("ascii"),
                now.strftime("%m").encode("ascii"),
                now.strftime("%d").encode("ascii"),
                now.strftime("%H").encode("ascii"),
                now.strftime("%M").encode("ascii")
            ]
            for d in dt:
                ser.write(d)
            dump_file = []
            c = 0
            while True:
                if c > 100:
                    if len(dump_file) == 0:
                        raise ConnectionError('NO_DATA_FOUND')
                    else:
                        self.import_string = ';'.join(str(x) for x in dump_file)
                    ser.close()
                    break
                c = c + 1
                time.sleep(0.1)
                while ser.in_waiting > 0:
                    dump_file.append(int(ser.read(1).hex(), 16))

            if ser.is_open:
                ser.close()

        except KeyboardInterrupt:
            if ser.is_open:
                ser.close()
            print('Keyboard interupt... RESTART THE MNEMO before rereading as you will end up somewhere in the middle of the stream.')

    def read_dump_file(self, path):
        with open(path, "r") as dmp_file:
            self.import_string = dmp_file.readlines()

    def write_dumpfile(self, path):
        if self.import_string is None:
            raise Exception('No data to be written.')
        text_file = open(path, "w")
        text_file.write(self.import_string)
        text_file.close()


    def get_data(self):
        response = []
        struct = None
        for byte in self.raw_import:
           if('we_have_a_new_line' is True):
               if struct:
                   response.append(struct)
               struct = DataStruct(device=DataStruct.DEVICE_MNEMO)
        ##### whatever...
        return struct


class StickMaps(QtWidgets.QMainWindow):

    errorMessages = {
        'UNKNOWN_ERROR': {
          'title': "Unknown error occurred",
          'body': "Bang head against screen and try again."
        },
        'NO_DATA_FOUND': {
            'title': "No data found",
            'body': """
                        <h3>Could not read any data on your Mnemo.</h3>
                        <p>Please make sure you select &gt;OK&lt; on the first menu-screen on the Mnemo in order to enable communications. </p>
                        <p>If this message re-appears, you most probably have NO DATA on your device.</p>
                    """
        }
    }

    def __init__(self):
        super(StickMaps, self).__init__()
        self.init()

    def init(self):
        self.setWindowTitle('StickMaps')
        #self.setWindowIcon(QtGui.QIcon('web.png'))
        self.get_menu()
        self.showMaximized()
        self.statusBar().showMessage('status: Ready')

    def get_menu(self):
        exit_action = QtGui.QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        file_menu.addAction(exit_action)

        import_mnemo = QtGui.QAction('Connect to Mnemo', self)
        import_mnemo.triggered.connect(self.connect_mnemo)

        import_menu = menubar.addMenu('Import')
        import_menu.addAction(import_mnemo)


        import_mnemo_dmp = QtGui.QAction('Load Mnemo dump file', self)
        import_mnemo_dmp.triggered.connect(self.load_mnemo_dmp)

        import_menu.addAction(import_mnemo_dmp)

    def show_error(self, error_key):
        try:
            title = self.errorMessages[error_key]['title']
            body = self.errorMessages[error_key]['body']
        except:
            title = self.errorMessages['UNKNOWN_ERROR']['title']
            body = self.errorMessages['UNKNOWN_ERROR']['body']

        error = QtWidgets.QErrorMessage(self)
        error.resize(500, 250)
        error.showMessage(body)
        error.setWindowTitle(title)
        error.show()

    def connect_mnemo(self):
        self.statusBar().showMessage('Connecting to Mnemo...', 3000)
        try:
            dmp = MnemoDataAdapter()
            dmp.read_from_device()
            self.append_survey_data(dmp.get_data())
        except ConnectionError as err:
            self.statusBar().showMessage('Failed reading Mnemo.', 1000)
            self.show_error(str(err))

    def load_mnemo_dmp(self):
        self.statusBar().showMessage('Loading Mnemo dump file...', 3000)

        file = QtWidgets.QFileDialog(self)

        options = file.Options()
        options |= file.DontUseNativeDialog

        file.setWindowTitle('Select Mnemo .dmp file to load')
        file.setNameFilter('Mnemo dump files (*.dmp)')
        file_name, _ = file.getOpenFileName()

        if not file_name:
            return

        print('filename read {}'.format(file_name))

        dmp = MnemoDataAdapter()
        dmp.read_dump_file(file_name)
        self.append_survey_data(dmp.get_data())




# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # parent_app = QtWidgets.QApplication()
    #
    # app = StickMaps()
    #
    # sys.exit(parent_app.exec_())
    from Gui.Windows import MainApplicationWindow

    if __name__ == '__main__':
        parent_app = QApplication()

        app = MainApplicationWindow()

        sys.exit(parent_app.exec_())




