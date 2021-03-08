import sys
import time
from datetime import datetime

import serial
from PySide6.QtCore import QObject, Signal
from serial.tools import list_ports

from Config.Constants import DEVICE_NAME_MNEMO
from Gui.Dialogs import ErrorDialog
from Models.TableModels import Survey, Section, Station, QueryMixin

class MnemoImporter(QObject):

    finished = Signal()
    error = Signal(str, Exception)
    progress = Signal(int)
    task_label = Signal(str)

    DEVICE_DESCRIPTION = "MCP2221 USB-I2C/UART Combo"

    # dump file uses "LINE_BIT_COUNT" bits for every line.
    LINE_BIT_COUNT = 16

    ACTION_WRITE_DUMP = 1
    ACTION_READ_DUMP = 2
    ACTION_READ_DEVICE = 3

    def __init__(
            self,
            device=None,
            baudrate=9600,
            timeout=1,
            verbose=0,
            treeview_model=None,
            thread_action=None,
            in_file=None,
            out_file=None

    ):
        super().__init__()
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout
        self.verbose = verbose

        self.import_list = None
        self.survey = None
        self.sections = []
        self.stations = []

        self.treeview_model = treeview_model

        self.tread_action = thread_action
        self.out_file = out_file
        self.in_file = in_file
        self.last_error = None

        self.database = None

    def run(self):
        self.database = QueryMixin.init_db('MNEMO_WORKER_THREAD')
        if self.tread_action == self.ACTION_WRITE_DUMP:
            try:
                self.read_from_device()
                self.write_dumpfile(self.out_file)
                self.task_label.emit('Done')
                self.finished.emit()
            except Exception as error:
                self.error.emit(str(error), self.last_error)
                self.finished.emit()
            return

        if self.tread_action == self.ACTION_READ_DEVICE:
            try:
                self.read_from_device()
                survey_id = self.get_data()
                # I need to get the treeview somehow.
                # model = self.treeview_model
                # model.append_survey_from_db(survey_id)
                self.task_label.emit('Done')
                self.finished.emit()
            except Exception as error:
                self.error.emit(str(error), self.last_error)
                self.finished.emit()
            return

        if self.tread_action == self.ACTION_READ_DUMP:
            try:
                self.read_dump_file(self.in_file)
                survey_id = self.get_data()
                # I need to get the treeview somehow.
                # model = self.treeview_model
                # model.append_survey_from_db(survey_id)
                self.task_label.emit('Done')
                self.finished.emit()
            except Exception as error:
                self.error.emit(str(error), self.last_error)
                self.finished.emit()
            return

        raise AttributeError(f'Unknown threadAction: {self.tread_action}')

    def get_device_location(self, device=None):
        if device is None:
            ports = list_ports.comports()
            for port in ports:
                if port.description == self.DEVICE_DESCRIPTION:
                    device = port.device

        if not device:
            raise Exception('NO_DEVICE_FOUND')

        return device

    def read_from_device(self):
        try:
            self.task_label.emit('Connection to device')
            self.device = self.get_device_location(self.device)
            try:
                ser = serial.Serial(self.device, self.baudrate, timeout=self.timeout, bytesize=8, stopbits=1, parity='N')
                ser.flushInput()
                ser.flushOutput()
            except serial.SerialException as error:
                self.last_error = error
                raise Exception('SERIAL_ERROR')

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
            x = 0
            while True:
                if c > 100:
                    time.sleep(0.5)
                    self.task_label.emit('Finished reading data')
                    if len(dump_file) == 0:
                        raise Exception('NO_DATA_FOUND')
                    else:
                        self.import_list = dump_file
                    ser.close()
                    break
                c = c + 1
                time.sleep(0.1)
                self.task_label.emit(f'Searching for entries {c} tries left')
                while ser.in_waiting > 0:
                    x = x + 1
                    self.task_label.emit(f'Reading byte {x}')
                    dump_file.append(self.setbit_read(ser.read(1)))
                    self.progress.emit(x)

            self.import_list = dump_file
            if ser.is_open:
                ser.close()

        except KeyboardInterrupt:
            if ser.is_open:
                ser.close()
            print('Keyboard interupt... RESTART THE MNEMO before rereading as you will end up somewhere in the middle of the stream.')

    def read_dump_file(self, path):
        with open(path, "r") as dmp_file:
            lines = dmp_file.readlines()
            list = lines[0].split(';')
            if list[-1] == '' or list[-1] == "\n":
                list.pop()
            self.import_list = [int(i) for i in list]

    def write_dumpfile(self, path):
        if not self.import_list:
            raise Exception('NO_DATA_FOUND')
        self.task_label.emit('Writing data to file.')
        text_file = open(path, "w")
        text_file.write(';'.join(str(x) for x in self.import_list))
        text_file.close()

    def get_data(self) -> int:
        if not self.import_list:
            raise Exception('NO_DATA_FOUND')

        survey_id = self.get_survey()
        return survey_id

    def get_survey(self):
        print('DB = ')
        print(self.database)
        survey_id = Survey.insert_survey(device_name=DEVICE_NAME_MNEMO)
        index = 6
        while True:
            index = self.get_section(index, survey_id)
            index = index + 6
            if index > len(self.import_list):
                break
        return survey_id

    def get_section(self, start_from, survey_id):
        mnemo_mode = ''.join([
            chr(self.import_list[start_from]),
            chr(self.import_list[start_from + 1]),
            chr(self.import_list[start_from + 2])
        ])

        mnemo_section_number = self.too_2byte_int(self.import_list[start_from + 3], self.import_list[start_from + 4])
        section_id = Section.insert_section(
            survey_id=survey_id,
            section_reference_id=mnemo_section_number,
            device_properties={"line_mode": mnemo_mode}
        )
        index = start_from + 3
        station_reference_id = 1
        length_in = 0
        azimuth_in = 0
        while True:
            section_reference_id, length_in, azimuth_in = self.get_station(index, station_reference_id, survey_id, section_id, length_in, azimuth_in)
            station_reference_id = station_reference_id + 1
            index = index + self.LINE_BIT_COUNT
            if section_reference_id != mnemo_section_number:
                index = index + 1
                break
            if index + self.LINE_BIT_COUNT > len(self.import_list):
                break
        return index

    def get_station(self, index: int, station_reference_id: int, survey_id: int, section_id: int,
                    length_in: float = 0.0, azimuth_in: float = 0.0):
        imp = self.import_list
        section_reference_id = self.too_2byte_int(imp[index], imp[index + 1])
        index = index + 2
        azimuth_out = self.too_2byte_int(imp[index], imp[index + 1]) / 10
        index = index + 2
        azimuth_in_new = self.too_2byte_int(imp[index], imp[index + 1]) / 10
        index = index + 2
        length_out = self.too_2byte_int(imp[index], imp[index + 1]) / 100
        index = index + 2
        depth = self.too_2byte_int(imp[index], imp[index + 1]) / 100
        index = index + 2
        temperature = self.too_2byte_int(imp[index], imp[index + 1])

        n = 11

        avg_az_out = (azimuth_out + azimuth_in_new) / 2
        Station.insert_station(
            survey_id=survey_id,
            section_id=section_id,
            section_reference_id=section_reference_id,
            station_reference_id=station_reference_id,
            length_in=length_in,
            length_out=length_out,
            azimuth_in=azimuth_in,
            azimuth_out=azimuth_out,
            azimuth_out_avg=avg_az_out,
            depth=depth,
            station_properties={'temperature': temperature},
            station_name=f"Station {station_reference_id}"
        )
        return section_reference_id, length_out, azimuth_in_new

    def too_2byte_int(self, byte_1: int, byte_2: int):
        hex_1 = self.setbit_negative_to_positive(byte_1)
        hex_2 = self.setbit_negative_to_positive(byte_2)
        pad = ''
        if len(hex_2) < 2:
            pad = '0'
        hex_str = '0x{}{}{}'.format(hex_1, pad, hex_2)
        response = int(hex_str, 16)
        return response

    def setbit_negative_to_positive(self, decimal):
        """
        Mnemo/ariane uses "signed short integer" as a datatype (JAVA)
        This has a range of -127 to 127 (which is setbit + 7 bits)

        There are NO unsigned values in the data-dumps, yet there are values bigger than 127.
        As a result, these are writen as negative numbers in the dump file.

        When reading the dumpfile we need to convert these negatives back to it's positive representation.

            For some reason.
        """
        if decimal < 0:
            decimal = int(format((1 << 8) + decimal, '08b'), 2)

        return hex(decimal).split('x')[1]

    def setbit_read(self, byte) -> int:
        """
                  I think this firmware is written in JAVA which does support sign-bits yet it is used and later reverted.
                  So I get a signed bit from the device, that needs to be written in the dump-file as a negative number.
                  So when reading the dump-file, this needs to be converted to a positive number (ignoring the sign bit ;p)
                  in order to merge it into a 16 bit number.

                  Python doesn't have a sign-bit, so we need to detect it manually.
                  So yeah... let's detect this sign-bit.

                  8 bit int will become a sign-bit + 7bit int
                  So [signbit]1111111 = total 8 bits.

                  python native:

                  Shift the bit 7 places to the right.. dropping all others.
                  Then keep only the last bit (1)

                  (byte >> 7) & 3
              """
        integer = int(byte.hex(), 16)
        is_negative = (integer >> 7) & 1 == 1
        if is_negative is False:
            return integer

        return integer - 256


if __name__ == '__main__':
    QueryMixin.init_db()
    QueryMixin.create_tables()

    importer = MnemoImporter(thread_action=MnemoImporter.ACTION_READ_DEVICE)
    importer.run()
    #importer.read_dump_file('/home/flip/Code/stickmaps/data_files/findingmnemo_orig.dmp')
    # print(f"DEVICE is at: {importer.get_device_location()}")
    # importer.read_from_device()
    # importer.write_dumpfile('/tmp/fuariane.dmp')
    # survey = importer.get_data()
    # foo = 'bar'