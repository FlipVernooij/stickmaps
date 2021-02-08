import time
from datetime import datetime
from pprint import pprint

import serial
from serial.tools import list_ports

from Config.Constants import DEVICE_NAME_MNEMO
from Models.PointModel import Point
from Models.SectionModel import Section
from Models.SurveyModel import Survey


class MnemoImporter:

    DEVICE_DESCRIPTION = "MCP2221 USB-I2C/UART Combo"

    # dump file uses "LINE_BIT_COUNT" bits for every line.
    LINE_BIT_COUNT = 16

    def __init__(self, device=None, baudrate=9600, timeout=1, verbose=0):
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout
        self.verbose = verbose

        self.import_list = None


        self.survey = None
        self.sections = []
        self.points  = []

    def get_device_location(self, device=None):
        if device is None:
            ports = list_ports.comports()
            for port in ports:
                if port.description == self.DEVICE_DESCRIPTION:
                    device = port.device

        if not device:
            raise ConnectionError('NO_DEVICE_FOUND')

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
                        self.import_list = ';'.join(str(x) for x in dump_file)
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
            lines = dmp_file.readlines()
            list = lines[0].split(';')
            if list[-1] == '' or list[-1] == "\n":
                list.pop()
            self.import_list = [int(i) for i in list]

    def write_dumpfile(self, path):
        if not self.import_list:
            raise Exception('No data to be written.')
        text_file = open(path, "w")
        text_file.write(self.import_list)
        text_file.close()

    def get_data(self):
        if not self.import_list:
            raise Exception('No data available')
        survey = self.get_survey()
        return survey

    def get_survey(self):
        survey = Survey(device_name=DEVICE_NAME_MNEMO)
        survey.save()
        index = 6
        while True:
            section, index = self.get_section(index, survey.survey_id)
            survey.append_section(section=section)
            index = index + 6
            if index > len(self.import_list):
                break

        return survey

    def get_section(self, start_from, survey_id):
        mnemo_mode = ''.join([
            chr(self.import_list[start_from]),
            chr(self.import_list[start_from + 1]),
            chr(self.import_list[start_from + 2])
        ])

        mnemo_section_number = self.too_2byte_int(self.import_list[start_from + 3], self.import_list[start_from + 4])
        section = Section(survey_id=survey_id, section_reference_id=mnemo_section_number,
                          device_properties={"line_mode": mnemo_mode})
        section_id = section.save()

        index = start_from + 3
        point_reference_id = 1
        length_in = 0
        azimuth_in = 0
        while True:
            point, azimuth_in = self.get_point(index, point_reference_id, survey_id, section_id, length_in, azimuth_in)
            section.append_point(point=point)
            length_in = point.length_out
            point_reference_id = point_reference_id + 1
            index = index + self.LINE_BIT_COUNT
            if point.section_reference_id != mnemo_section_number:
                index = index + 1
                break
            if index + self.LINE_BIT_COUNT > len(self.import_list):
                break
        return section, index

    def get_point(self, index, point_reference_id, survey_id, section_id, length_in=0, azimuth_in=0):
        imp = self.import_list
        point = Point(survey_id=survey_id, section_id=section_id, point_reference_id=point_reference_id, length_in=length_in, azimuth_in=azimuth_in)
        point.section_reference_id = self.too_2byte_int(imp[index], imp[index + 1])
        index = index + 2
        point.azimuth_in = azimuth_in
        azimuth_next_in = self.too_2byte_int(imp[index], imp[index + 1]) / 10
        point.azimuth_out = self.too_2byte_int(imp[index], imp[index + 1]) / 10
        index = index + 4
        point.length_out = self.too_2byte_int(imp[index], imp[index + 1]) / 100
        index = index + 2
        point.depth = self.too_2byte_int(imp[index], imp[index + 1])
        index = index + 2
        point.temperature = self.too_2byte_int(imp[index], imp[index + 1])
        point.save()
        return point, azimuth_next_in

    def too_2byte_int(self, byte_1: int, byte_2: int):
        hex_1 = self.twos_complement(byte_1)
        hex_2 = self.twos_complement(byte_2)
        hex_str = '0x{}{}'.format(hex_1, hex_2)
        response = int(hex_str, 16)
        return response

    def twos_complement(self, decimal):
        if decimal < 0:
            decimal = int(format((1 << 8) + decimal, '08b'), 2)

        return hex(decimal).split('x')[1]


if __name__ == '__main__':
    Survey.create_database_tables()
    Section.create_database_tables()
    Point.create_database_tables()

    importer = MnemoImporter()
    importer.read_dump_file('/home/flip/Code/stickmaps/data_files/findingmnemo_orig.dmp')
    survey = importer.get_data()