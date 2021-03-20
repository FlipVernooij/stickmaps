import logging
import os
import traceback
import time
from datetime import datetime

import serial
from serial.tools import list_ports

from Config.Constants import MNEMO_DEVICE_NAME, MNEMO_DEVICE_DESCRIPTION, MNEMO_CYCLE_COUNT
from Models.TableModels import Survey, Section, Station, SqlManager
from Utils.Settings import Preferences
from Workers.Mixins import WorkerMixin


class MnemoImporter(WorkerMixin):

    # dump file uses "LINE_BIT_COUNT" bits for every line.
    LINE_BYTE_COUNT = 16

    ACTION_WRITE_DUMP = 1
    ACTION_READ_DUMP = 2
    ACTION_READ_DEVICE = 3

    SURVEY_IN = 'IN'
    SURVEY_OUT = 'OUT'
    SURVEY_UNKNOWN = 'DIRECTION UNKNOWN'

    SURVEY_DIRECTIONS = [
        SURVEY_IN, SURVEY_OUT, SURVEY_UNKNOWN
    ]

## typeshot CSA, CSB, STD, EOC
    SURVEY_MODE_BASIC = 'CSA'
    SURVEY_MODE_ONE_GO = 'CSB'
    SURVEY_MODE_ADVANCED = 'STD'
    SURVEY_MODE_EXIT = 'EOC'

    SURVEY_MODES = [SURVEY_MODE_BASIC, SURVEY_MODE_ONE_GO, SURVEY_MODE_ADVANCED, SURVEY_MODE_EXIT]

    def __init__(
            self,
            thread_action: str = None,
            device=None,
            baudrate=9600,
            timeout=1,

            in_file=None,
            out_file=None

    ):
        super().__init__()
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout

        self.import_list = None
        self.survey = None
        self.sections = []
        self.stations = []
        self.byte_index = -1  # we update the index before returning it.

        self.tread_action = thread_action
        self.out_file = out_file
        self.in_file = in_file
        self.last_error = None

    def run(self):
        self.set_sql_manager('MNEMO_WORKER_THREAD')
        if self.tread_action == self.ACTION_WRITE_DUMP:
            try:
                self.read_from_device()
                self.write_dumpfile(self.out_file)
                self.s_task_label.emit('Done')
                self.finished()
            except Exception as error:
                self.s_error.emit(str(error), error if self.last_error is None else self.last_error)
                self.finished()
            return

        if self.tread_action == self.ACTION_READ_DEVICE:
            try:
                self.read_from_device()
                survey_id = self.get_data()
                self.s_task_label.emit('Done')
                self.s_reload_treeview.emit(survey_id)
                self.finished()
            except Exception as error:
                self.s_error.emit(str(error), error if self.last_error is None else self.last_error)
                self.finished()
            return

        if self.tread_action == self.ACTION_READ_DUMP:
            try:
                self.read_dump_file(self.in_file)
                survey_id = self.get_data()
                self.s_reload_treeview.emit(survey_id)
                self.s_task_label.emit('Done')
                self.finished()
            except Exception as error:
                self.s_error.emit(str(error), error if self.last_error is None else self.last_error)
                self.finished()
                raise error
            return

        self.s_error.emit(f'Unknown threadAction: {self.tread_action}')
        self.finished()

    def get_device_location(self, device=None):
        if device is None:
            ports = list_ports.comports()
            for port in ports:
                if port.description == Preferences.get('mnemo_device_description', MNEMO_DEVICE_DESCRIPTION):
                    device = port.device

        if not device:
            raise Exception('NO_DEVICE_FOUND')

        return device

    def read_from_device(self):
        try:
            self.s_task_label.emit('Connecting to device')
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
            # Within ariane a harcoded / non-resettable cycle-count of 100 is used
            # Yet when debugging,.. I haven't seen it use more then 3 ever...
            cycle_count = Preferences.get('mnemo_cycle_count', MNEMO_CYCLE_COUNT, int)
            while True:
                if c > cycle_count:
                    # time.sleep(0.5)  # @todo why is this here?
                    self.s_task_label.emit('Finished reading data')
                    if len(dump_file) == 0:
                        raise Exception('NO_DATA_FOUND')
                    else:
                        self.import_list = dump_file
                    ser.close()
                    break
                c = c + 1
                time.sleep(0.1)
                self.s_task_label.emit(f'Searching for entries {c} tries left')
                while ser.in_waiting > 0:
                    x = x + 1
                    self.s_task_label.emit(f'Reading byte {x}')
                    dump_file.append(self.setbit_read(ser.read(1)))
                    self.s_progress.emit(x)
                    # reset the cycle count here, should allow us to use a even lower cycle count.
                    c = 0

            self.import_list = dump_file
            if ser.is_open:
                ser.close()

        except KeyboardInterrupt:
            if ser.is_open:
                ser.close()
            print('Keyboard interupt... RESTART THE MNEMO before rereading as you will end up somewhere in the middle of the stream.')

    def read_dump_file(self, path):
        f_size = self._readable_size(os.stat(path).st_size)
        self.s_task_label.emit(f'Reading file {f_size}')
        with open(path, "r") as dmp_file:
            lines = dmp_file.readlines()
            list = lines[0].split(';')
            if list[-1] == '' or list[-1] == "\n":
                list.pop()
            self.import_list = [int(i) for i in list]

    def write_dumpfile(self, path):
        if not self.import_list:
            raise Exception('NO_DATA_FOUND')
        self.s_task_label.emit('Writing data to file.')
        text_file = open(path, "w")
        text_file.write(';'.join(str(x) for x in self.import_list))
        text_file.close()

    def get_data(self) -> int:
        if not self.import_list:
            raise Exception('NO_DATA_FOUND')

        reader = MnemoDmpReader(self.import_list, self.sql_manager())
        survey_id = reader.read()
        return survey_id



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

    def _readable_size(self, byte_length: int, index=0):
        names = ['bytes', 'kilobytes', 'megabytes', 'gigabytes']
        if byte_length < 1000:
            return f'{round(byte_length, 2)} {names[index]}'
        return self._readable_size(byte_length / 1000, index + 1)


class MnemoDmpReader:

    LINE_LENGTH_SECTION = 10
    LINE_LENGTH_STATION = 16

    END_OF_SECTION_LIST = (3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,)

    DIRECTION_IN = 0
    DIRECTION_OUT = 1
    DIRECTIONS = ("IN", "OUT", "UNKNOWN",)

    STATUS_INPROGRESS = 2
    STATUS_ENDSECTION = 3

    def __init__(self, byte_list: list, sql_manager: SqlManager):
        self.bytes = byte_list
        self.sql_manager = sql_manager

        self.survey = self.sql_manager.factor(Survey)
        self.section = self.sql_manager.factor(Section)
        self.station = self.sql_manager.factor(Station)

        self._index = -1

    def read(self) -> list:
        """
        :return: survey_id
        """
        survey_id = self.survey.insert_survey(
                device_name=Preferences.get("mnemo_device_name", MNEMO_DEVICE_NAME, str),
                device_properties={
                    "bytes_in_dumpfile": len(self.bytes)
                }
            )

        section_reference_id = 0
        while True:
            if self.end_of_bytes(self.LINE_LENGTH_SECTION):
                # empty section / incomplete section
                break

            # Loop through every section on the device
            #  2;21;3;7;13;4;66;65;83;0
            section_reference_id += 1
            section_props = self.parse_section_line()
            section_id = self.section.insert_section(
                    survey_id=survey_id,
                    section_reference_id=section_reference_id,
                    direction=section_props['direction'],
                    device_properties=section_props
                )

            station_reference_id = 0
            azimuth_in = 0
            length_in = 0
            while True:
                if self.end_of_bytes(self.LINE_LENGTH_STATION):
                    # end of dumpfile / incomplete line.
                    if len(self.bytes) - self._jump(0, False) > 0:
                        logging.getLogger(__name__).error(f'Found incomplete station at ending at byte: {self._jump(0, False)}')
                    break
                # Loop through every station for this stations
                station_reference_id += 1
                if self.end_of_section():
                    # @todo I think that I need to add a last point to the database.
                    #       This as we are not storing lines but points, the only question I have is... where do I get the depth from..?
                    #       it should be the depth_in...
                    props = {
                        "status": True,
                        "skipped_bytes": 0,
                        "status_byte": 3,
                        "comment": "Last station is generated"

                    }
                    self.station.insert_station(
                        survey_id=survey_id,
                        section_id=section_id,
                        section_reference_id=section_reference_id,
                        station_reference_id=station_reference_id,
                        length_in=length_in,
                        length_out=0,
                        #  we need to reverse the azimuth as we are storing a station and not a line.
                        #  as the line starts at a point, the azimuth in of a line.. is the azimuth out of a station.
                        #  the azimuth out of a line..is the azimuth in of a station.
                        azimuth_in=azimuth_in,
                        azimuth_out=0,
                        # @todo I should use the avg of the previous station here probably.
                        azimuth_out_avg=azimuth_in,
                        depth=last_depth,
                        station_properties=props,
                        station_name=f"Station {station_reference_id}"
                    )
                    break

                station_reference_id += 1
                station_props = self.parse_station_line()
                self.station.insert_station(
                    survey_id=survey_id,
                    section_id=section_id,
                    section_reference_id=section_reference_id,
                    station_reference_id=station_reference_id,
                    length_in=length_in,
                    length_out=station_props['length'],
                    #  we need to reverse the azimuth as we are storing a station and not a line.
                    #  as the line starts at a point, the azimuth in of a line.. is the azimuth out of a station.
                    #  the azimuth out of a line..is the azimuth in of a station.
                    azimuth_in=azimuth_in,
                    azimuth_out=station_props['azimuth_in'],
                    azimuth_out_avg=(station_props['azimuth_in'] + station_props['azimuth_out']) / 2,
                    depth=station_props['depth_out'],
                    station_properties=station_props,
                    station_name= f"Station {station_reference_id}"
                )
                length_in = station_props['length']
                azimuth_in = station_props['azimuth_out']
                last_depth = station_props['depth_in']

        return survey_id

    def parse_section_line(self):
        #  2;21;3;7;13;4;66;65;83;0
        properties = {
            "direction": self.DIRECTIONS[2],
            "skipped_bytes": 0,
            "status": False,
        }
        # @ariane Skip unknown data until version number in case of previously damaged sections?
        while self.read_int8() != 2:
            properties['skipped_bytes'] += 1
            if self.end_of_bytes():
                properties["status"] = False
                properties["error"] = "End of dmp file reached"
                return properties
            continue


        if self.end_of_bytes(self.LINE_LENGTH_SECTION):
            # empty survey
            return False, properties

        if self.byte_at_has_value(self.LINE_LENGTH_SECTION - 1, [self.DIRECTION_IN, self.DIRECTION_OUT]) is False \
                or self.byte_at_has_value(self.LINE_LENGTH_SECTION, [self.STATUS_INPROGRESS, self.STATUS_ENDSECTION]) is False:
            # Station line does not start at the expected location.
            properties['error'] = "Section does not meet expected length"
            properties['error_data'] = {
                "status_byte_index": self._jump(-1, False),
                "status_byte_value": self.read_int8(-1, False),
                "next_direction_byte_index": self._jump(self.LINE_LENGTH_SECTION - 1, False),
                "next_direction_byte_value": self.read_int8(self.LINE_LENGTH_SECTION - 1, False),
            }
            return False, properties

        properties['version'] = self.read_int8(0, False)

        year = self.read_int8()
        month = self.read_int8()
        day = self.read_int8()
        hour = self.read_int8()
        minute = self.read_int8()

        properties["datetime"] = f'{hour}:{0 if minute < 10 else ""}{minute} {day}-{month} {year}'
        properties["name"] = f'{self.read_char()}{self.read_char()}{self.read_char()}'
        properties["direction"] = self.get_direction(self.read_int8())
        properties["status"] = True
        return properties

    def parse_station_line(self):
        # 2;2;28;2;78;5;27;6;-4;7;37;-1;-17;-1;-60;0;  ## station is 16 long
        props = {
            'status': False,
            'missing_bytes': 0,
            'byte_start': self._jump(0, False)
        }
        try:
            props['status_byte'] = self.read_int8()
            props['azimuth_in'] = self.read_int16() / 10
            props['azimuth_out'] = self.read_int16() / 10
            props['length'] = self.read_int16() / 100
            props['depth_in'] = self.read_int16() / 100
            props['depth_out'] = self.read_int16() / 100
            props['pitch_in'] = self.read_int16() / 100
            props['pitch_out'] = self.read_int16() / 100
            props['direction'] = self.get_direction(self.read_int8())
            props['status'] = True

        except IndexError as error:
            props['error'] = 'Next byte could not be found',
            props['missing_bytes'] = (props['byte_start'] + self.LINE_LENGTH_STATION) - self._jump(0, False)

        props['byte_end'] = self._jump(0, False)
        return props

    def get_direction(self, index: int) -> str:
        try:
            return self.DIRECTIONS[index]
        except IndexError:
            return f'{self.DIRECTIONS[2]} - ({index})'

    def read_int8(self, add_to_index: int = 1, update_index: bool=True) -> int:
        return self._setbit_negative_to_positive(self.bytes[self._jump(add_to_index, update_index)], True)

    def read_int16(self, add_to_index: int = 1, update_index: bool=True) -> int:
        b_1 = self._setbit_negative_to_positive(self.bytes[self._jump(add_to_index, False)])
        b_2 = self._setbit_negative_to_positive(self.bytes[self._jump(add_to_index+1, update_index)])
        pad = ''
        if len(b_2) < 2:
            pad = '0'
        hex_str = '0x{}{}{}'.format(b_1, pad, b_2)
        response = int(hex_str, 16)
        return response

    def read_char(self, add_to_index: int = 1, update_index: bool=True) -> chr:
        return chr(self.read_int8(add_to_index, update_index))

    def end_of_bytes(self, add_to_index: int = 1) -> int:
        if self._jump(add_to_index, False) >= len(self.bytes):
            return True
        return False

    def end_of_section(self, from_index: int = 0):
        for i in range(1, self.LINE_LENGTH_STATION+1):
            if self.read_int8(from_index + i, False) != self.END_OF_SECTION_LIST[i - 1]:
                return False
        return True

    def byte_at_has_value(self, add_to_index: int, value) -> bool:
        if isinstance(value, list) is False:
            value = [value]

        if self.read_int8(add_to_index, False) in value:
            return True
        return False

    def _jump(self, count: int, update_index: bool = True) -> int:
        index = self._index + count
        if update_index is True:
            self._index = index
        return index

    def _setbit_negative_to_positive(self, decimal, as_int=False):
        """
        Mnemo/ariane uses "signed short integer" as a datatype (JAVA)
        This has a range of -127 to 127 (which is setbit + 7 bits)

        There are NO unsigned values in the data-dumps, yet there are values bigger than 127.
        As a result, these are writen as negative numbers in the dump file.

        When reading the dumpfile we need to convert these negatives back to it's positive representation.
        """
        if decimal < 0:
            decimal = int(format((1 << 8) + decimal, '08b'), 2)

        result = hex(decimal).split('x')[1]
        if as_int is True:
            return int(result, 16)
        return result



if __name__ == '__main__':
    #importer = MnemoImporter(thread_action=MnemoImporter.ACTION_READ_DUMP, in_file='/home/flip/Code/stickmaps/data_files/tux.dmp')
    importer = MnemoImporter(thread_action=MnemoImporter.ACTION_READ_DUMP, in_file='/home/flip/Code/stickmaps/data_files/stickmaps_dump.dmp')
    importer.run()
    #importer.read_dump_file('/home/flip/Code/stickmaps/data_files/findingmnemo_orig.dmp')
    # print(f"DEVICE is at: {importer.get_device_location()}")
    # importer.read_from_device()
    # importer.write_dumpfile('/tmp/fuariane.dmp')
    # survey = importer.get_data()
    # foo = 'bar'