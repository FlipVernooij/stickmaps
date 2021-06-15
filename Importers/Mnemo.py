import json
import logging
import os
import time
from datetime import datetime

import serial
from serial.tools import list_ports

from Config.Constants import MNEMO_DEVICE_NAME, MNEMO_DEVICE_DESCRIPTION, MNEMO_CYCLE_COUNT, SURVEY_DIRECTION_IN, \
    SURVEY_DIRECTION_OUT
from Models.TableModels import ImportSurvey, ImportLine, ImportStation, SqlManager
from Utils.Settings import Preferences
from Workers.Mixins import WorkerMixin




class MnemoImporter(WorkerMixin):

    ACTION_WRITE_DUMP = 1
    ACTION_READ_DUMP = 2
    ACTION_READ_DEVICE = 3

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
                survey_id = self.parse_bytelist()
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
                survey_id = self.parse_bytelist()
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
            # @todo somehow the dat is not set correctly?
            """
            LocalDateTime
            Thread.sleep(100L);
            date = LocalDateTime.now();
            startCode[0] = (byte)(date.getYear() % 1000);
            startCode[1] = (byte) date.getMonthValue();
            startCode[2] = (byte) date.getDayOfMonth();
            startCode[3] = (byte) date.getHour();
            startCode[4] = (byte) date.getMinute();
            comPort.writeBytes(startCode, 5L);
            """
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
                    dump_file.append(self._setbit_to_uint8(ser.read(1)))
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
        writer = MnemoDumpWriter(self.import_list)
        writer.write_file(path)

    def parse_bytelist(self) -> int:
        if not self.import_list:
            raise Exception('NO_DATA_FOUND')

        reader = MnemoDmpReader(self.import_list, self.sql_manager())
        survey_id = reader.read()
        return survey_id

    def get_device_location(self, device=None):
        if device is None:
            ports = list_ports.comports()
            for port in ports:
                if port.description == Preferences.get('mnemo_device_description', MNEMO_DEVICE_DESCRIPTION):
                    device = port.device

        if not device:
            raise Exception('NO_DEVICE_FOUND')

        return device

    def _setbit_to_uint8(self, byte) -> int:
        """
                  In JAVA the "byte" type is not a real byte but a byte with the setbit set.
                  This allows negative numbers, -127 to 127 instead of the usual 0 to 256.

                  Python just reads bytes as a collection of bits that causes me to work out the setbit stuff myself.

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

    LINE_LENGTH_LINE = 10
    LINE_LENGTH_STATION = 16

    END_OF_LINE_LIST = (3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,)

    DIRECTION_IN = 0
    DIRECTION_OUT = 1
    DIRECTIONS = (SURVEY_DIRECTION_IN, SURVEY_DIRECTION_OUT, "UNKNOWN",)

    STATUS_INPROGRESS = 2
    STATUS_END_LINE = 3

    def __init__(self, byte_list: list, sql_manager: SqlManager):
        self._bytes = byte_list
        self.sql_manager = sql_manager

        self.survey = self.sql_manager.factor(ImportSurvey)
        self.line = self.sql_manager.factor(ImportLine)
        self.station = self.sql_manager.factor(ImportStation)

        self._index = -1

        self.logger = logging.getLogger(__name__)

    def read(self) -> list:
        line_id = -1
        station_id = -1
        survey_id = self.survey.insert(
                device_name=Preferences.get("mnemo_device_name", MNEMO_DEVICE_NAME, str),
                device_properties={
                    "bytes_in_dumpfile": len(self._bytes)
                }
            )
        self.logger.info(f"Created new survey, survey_id={survey_id}")
        line_reference_id = 0
        while True:
            if self.end_of_bytes(self.LINE_LENGTH_LINE):
                # empty line / incomplete line
                self.logger.info(
                    f"ln 257: End import at station_id={station_id} line_id={line_id} survey_id={survey_id} (at index {self._index} of {len(self._bytes)}")
                return survey_id

            # Loop through every line on the device
            #  2;21;3;7;13;4;66;65;83;0
            line_reference_id += 1
            line_props = self.parse_line_part()
            line_id = self.line.insert(
                    survey_id=survey_id,
                    line_reference_id=line_reference_id,
                    direction=line_props['direction'],
                    device_properties=line_props
                )
            self.logger.info(f"Created new line, line_id={line_id} survey_id={survey_id} (at index {self._index} of {len(self._bytes)}")
            station_reference_id = 0
            azimuth_in = 0
            azimuth_avg = 0
            length_in = 0
            while True:
                if self.end_of_bytes(self.LINE_LENGTH_STATION):
                    # Here we have LESS than a full station-line.
                    #   1.) The line is the last entry of the dump, no end-line line exists
                    #   2.) The next line is incomplete and is smaller then 16 bytes.
                    if len(self._bytes) - self._jump(self.LINE_LENGTH_STATION+1, False) > 0:
                        logging.getLogger(__name__).error(f'Found incomplete station with {len(self._bytes) - self._jump(0, False)} bytes, starting at byte: {self._jump(0, False)}, total bytes {len(self._bytes)}')
                    self.logger.info(
                        f"ln 281: End import at station_id={station_id} line_id={line_id} survey_id={survey_id} (at index {self._index} of {len(self._bytes)}")
                    return survey_id

                # Loop through every station for these stations
                station_reference_id += 1
                if self.end_of_line():
                    if station_reference_id == 1:
                        self.logger.info(f"Empty line, line_id={line_id} survey_id={survey_id} (at index {self._index} of {len(self._bytes)}")
                        # this is an empty line, don't insert this station
                        break

                    props = {
                        "status": True,
                        "skipped_bytes": 0,
                        "status_byte": 3,
                        "comment": "Last station is generated"

                    }
                    station_id = self.station.insert(
                        survey_id=survey_id,
                        line_id=line_id,
                        line_reference_id=line_reference_id,
                        station_reference_id=station_reference_id,
                        length_in=length_in,
                        length_out=0,
                        #  we need to reverse the azimuth as we are storing a station and not a line.
                        #  as the line starts at a point, the azimuth in of a line.. is the azimuth out of a station.
                        #  the azimuth out of a line..is the azimuth in of a station.
                        azimuth_in=azimuth_in,
                        azimuth_out=0,
                        azimuth_out_avg=azimuth_avg,
                        depth=last_depth,
                        station_properties=props,
                        station_name=f"Station {station_reference_id}"
                    )
                    break

                station_props = self.parse_station_part()
                station_id = self.station.insert(
                    survey_id=survey_id,
                    line_id=line_id,
                    line_reference_id=line_reference_id,
                    station_reference_id=station_reference_id,
                    length_in=length_in,
                    length_out=station_props['length'],
                    #  we need to reverse the azimuth as we are storing a station and not a line.
                    #  as the line starts at a point, the azimuth in of a line.. is the azimuth out of a station.
                    #  the azimuth out of a line..is the azimuth in to a station.
                    azimuth_in=azimuth_in,
                    azimuth_out=station_props['azimuth_in'],
                    #  @todo OneGo mode most probably breaks this.
                    azimuth_out_avg=(station_props['azimuth_in'] + station_props['azimuth_out']) / 2,
                    depth=station_props['depth_out'],
                    station_properties=station_props,
                    station_name= f"Station {station_reference_id}"
                )
                length_in = station_props['length']
                azimuth_in = station_props['azimuth_out']
                #  @todo OneGo mode most probably breaks this.
                azimuth_avg = (station_props['azimuth_in'] + station_props['azimuth_out']) / 2
                last_depth = station_props['depth_in']

        self.logger.info(
            f"ln 346: End import at station_id={station_id} line_id={line_id} survey_id={survey_id} (at index {self._index} of {len(self._bytes)}")
        return survey_id

    def parse_line_part(self):
        #  2;21;3;7;13;4;66;65;83;0
        properties = {
            "direction": self.DIRECTIONS[2],
            "skipped_bytes": 0,
            "status": False,
        }
        # @ariane skips unknown data until version number in case of previously damaged lines?
        while self.read_int8() != 2:
            properties['skipped_bytes'] += 1
            if self.end_of_bytes():
                properties["status"] = False
                properties["error"] = "End of dmp file reached"
                return properties
            continue


        if self.end_of_bytes(self.LINE_LENGTH_LINE):
            # empty survey
            return False, properties

        if self.byte_at_has_value(self.LINE_LENGTH_LINE - 1, [self.DIRECTION_IN, self.DIRECTION_OUT]) is False \
                or self.byte_at_has_value(self.LINE_LENGTH_LINE, [self.STATUS_INPROGRESS, self.STATUS_END_LINE]) is False:
            # Station line does not start at the expected location.
            properties['error'] = "Line does not meet expected byte-length"
            properties['error_data'] = {
                "status_byte_index": self._jump(-1, False),
                "status_byte_value": self.read_int8(-1, False),
                "next_direction_byte_index": self._jump(self.LINE_LENGTH_LINE - 1, False),
                "next_direction_byte_value": self.read_int8(self.LINE_LENGTH_LINE - 1, False),
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

    def parse_station_part(self):
        # 2;2;28;2;78;5;27;6;-4;7;37;-1;-17;-1;-60;0;  ## station is 16 long
        props = {
            'status': False,
            'missing_bytes': 0,
            'byte_start': self._jump(0, False)
        }
        try:
            # @todo I am only accepting unsigned ints for depths,
            #       yet I might not be surprised if we should actually allow them for every property
            #       Despite what ariane is doing, as I do think that ariane might not even understand there is a setbit set to start with.
            props['status_byte'] = self.read_int8()
            props['azimuth_in'] = self.read_int16() / 10
            props['azimuth_out'] = self.read_int16() / 10
            props['length'] = self.read_int16() / 100
            props['depth_in'] = self.read_int16(unsigned=True) / 100
            props['depth_out'] = self.read_int16(unsigned=True) / 100
            props['pitch_in'] = self.read_int16() / 100
            props['pitch_out'] = self.read_int16() / 100
            props['direction'] = self.get_direction(self.read_int8())
            props['status'] = True



        except IndexError as error:
            props['error'] = 'Next byte could not be found',
            props['missing_bytes'] = (props['byte_start'] + self.LINE_LENGTH_STATION) - self._jump(0, False)

        props['byte_end'] = self._jump(0, False)
        return props

    def end_of_line(self, add_to_index: int = 0):
        # +1 because _jump() first adds to the index, then returns it.
        #    so self._index is always 1 step behind...
        for i in range(1, self.LINE_LENGTH_STATION+1):
            if self.read_int8(add_to_index + i, False) != self.END_OF_LINE_LIST[i - 1]:
                return False
        return True

    def end_of_bytes(self, add_to_index: int = 1) -> int:
        # +1 because _jump() first adds to the index, then returns it.
        #    so self._index is always 1 step behind...
        if self._jump(add_to_index + 1, False) >= len(self._bytes):
            return True
        return False

    def get_direction(self, index: int) -> str:
        try:
            return self.DIRECTIONS[index]
        except IndexError:
            return f'{self.DIRECTIONS[2]} - ({index})'

    def read_int8(self, add_to_index: int = 1, update_index: bool=True) -> int:
        return self._setbit_negative_to_positive(self._bytes[self._jump(add_to_index, update_index)], True)

    def read_int16(self, add_to_index: int = 1, update_index: bool=True, unsigned=False) -> int:
        # Ariane does not handle setbits correctly.
        #
        # When writing a dump-file, it is actively trying to ignore and remove setbits,
        # making all values positive even when provided as negative by the mnemo.
        #
        # The problem is that when we reset the depth-sensor at depth, we might actually end up with negative numbers.
        # The negative value is correctly shown on the Mnemo, but crashes ariane and mnemo-bridge.
        # After reading the dumpfile according to ariane standards, the negatives are wrapping resulting in very high positive numbers.
        #
        # We need to fix that somehow, I want stickmaps to show the correct negative value.
        #
        if unsigned is False:
            # ariane's way of dealing with set-bits.
            # @todo can't this be done a bit nicer, juggling between hex and hex strings is sort of dirty...
            b_1 = self._setbit_negative_to_positive(self._bytes[self._jump(add_to_index, False)])
            b_2 = self._setbit_negative_to_positive(self._bytes[self._jump(add_to_index + 1, update_index)])
            pad = ''
            if len(b_2) < 2:
                pad = '0'
            hex_str = '0x{}{}{}'.format(b_1, pad, b_2)
            response = int(hex_str, 16)
            return response
        else:
            # actually allow for negative values, practically undoing MnemoDmpWriter._setbit_to_uint8()
            byte_1 = self._bytes[self._jump(add_to_index, False)]
            byte_2 = self._bytes[self._jump(add_to_index + 1, update_index)]
            return (byte_1 << 8) | (byte_2 & 0xff)




    def read_char(self, add_to_index: int = 1, update_index: bool=True) -> chr:
        return chr(self.read_int8(add_to_index, update_index))

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
        JAVA's byte type is a setbit byte type, which translates to a unsigned u_int_8 (-127 / 127)
        In order to use the full 256 byte values, we need to translate all negative values back to its positive counter part.
        I don't know why this wasn't done at the moment of writing the dump-file itself.
        """

        if decimal < 0:
            decimal = int(format((1 << 8) + decimal, '08b'), 2)

        result = hex(decimal).split('x')[1]
        if as_int is True:
            return int(result, 16)
        return result


class MnemoDumpWriter:
    """
    -518 ==          0xFDFA = 11111101 11111010

    actual: 6523
        signed 16b   0x197B = 00011001 01111011
       usigned 16b   0x197B = 00011001 01111011
    """
    LINE_LENGTH_LINE = 10
    LINE_LENGTH_STATION = 16

    END_OF_LINE_LIST = (3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,)

    DIRECTION_IN = 0
    DIRECTION_OUT = 1
    DIRECTIONS = (SURVEY_DIRECTION_IN, SURVEY_DIRECTION_OUT, "UNKNOWN",)

    STATUS_INPROGRESS = 2
    STATUS_END_LINE = 3

    LAST_STATION_GENERATED = 'Last station is generated'

    def __init__(self, import_list: list = None):
        self.import_list = import_list

    def save_survey_to_dmp(self, survey_id, file_name):
        self._ariane_dmp_dump(survey_id)
        self.write_file(file_name)


    def _csv_dump(self, survey_id: int):
        manager = SqlManager()
        lines = manager.factor(ImportLine).get_all(survey_id, True)
        station_obj = manager.factor(ImportStation)
        rows = [
            ';line_nr',
            'line_name',
            'direction',
            'station_nr',
            'length_in',
            'azimuth_in',
            'depth',
            'azimuth_out',
            'azimuth_out_avg'

            '\n'
        ]

        l = -1
        for line in lines:
            l += 1
            s = -1
            stations = station_obj.get_all(line['line_id'])
            for station in stations:
                s+=1
                rows.append(f'{l}')
                rows.append(line['line_name'])
                rows.append(line['direction'])
                rows.append(s)
                rows.append(station['length_in'])
                rows.append(station['azimuth_in'])
                rows.append(station['depth']),
                rows.append(station['azimuth_out'])
                rows.append(station['azimuth_out_avg'])
                rows.append("\n")

        self.import_list = rows

    def _ariane_dmp_dump(self, survey_id: int):
        manager = SqlManager()
        lines = manager.factor(ImportLine).get_all(survey_id, True)
        station_obj = manager.factor(ImportStation)
        rows = []
        # version and DateTime
        # now = datetime.now()
        now = datetime(2021, 3, 7, 13, 4)
        l = -1


        for line in lines:
            rows.extend([
                2,
                # https: // stackoverflow.com / questions / 34009653 / convert - bytes - to - int
                int(now.strftime("%y")),
                int(now.strftime("%m")),
                int(now.strftime("%d")),
                int(now.strftime("%H")),
                int(now.strftime("%M")),
                int.from_bytes(b'B', 'big'),
                int.from_bytes(b'A', 'big'),
                int.from_bytes(b'S', 'big'),
                self.DIRECTION_IN if line['direction'] == 'In' else self.DIRECTION_OUT
            ])

            l += 1
            s = -1
            stations = station_obj.get_all(line['line_id'])
            for index, station in enumerate(stations):
                orig_props = json.loads(station['device_properties'])
                try:
                    if orig_props['comment'] == self.LAST_STATION_GENERATED:
                        # As we are storing stations instead of lines, we should ignore the last station of a line.
                        rows.extend(self.END_OF_LINE_LIST)
                        continue
                except KeyError:
                    pass


                rows.append(self.STATUS_INPROGRESS)
                rows.extend(self.to_uint16(station['azimuth_out'] * 10))  # status byte int8
                rows.extend(self.to_uint16(stations[index+1]['azimuth_in'] * 10))  # status byte int8
                rows.extend(self.to_uint16(station['length_out'] * 100))  # status byte int8
                rows.extend(self.to_uint16(station['depth'] * 100))  # <- This should be a signed INT...
                rows.extend(self.to_uint16(station['depth'] * 100))  # status byte int8
                rows.extend(self.to_uint16(orig_props['pitch_in'] * 100))  # status byte int8
                rows.extend(self.to_uint16(orig_props['pitch_out'] * 100))  # status byte int8
                rows.append(self.DIRECTION_IN if line['direction'] == 'In' else self.DIRECTION_OUT)  # status byte int8

        rows.extend(self.END_OF_LINE_LIST)
        self.import_list = rows

    def to_uint16(self, decimal):
        # Skip fancy bit-shifting, using a blunt axe today.
        c, f = divmod(int(decimal), 1 << 8)
        if c > 127:
            c -= 256
        if f > 127:
            f -= 256

        return c, f

    def write_file(self, path):
        if not self.import_list:
            raise Exception('NO_DATA_FOUND')
        text_file = open(path, "w")
        text_file.write(f"{';'.join(str(x) for x in self.import_list)};")
        text_file.close()

if __name__ == '__main__':
    #importer = MnemoImporter(thread_action=MnemoImporter.ACTION_READ_DUMP, in_file='/home/flip/Code/Stickmaps/data_files/tux.dmp')
    importer = MnemoImporter(thread_action=MnemoImporter.ACTION_READ_DUMP, in_file='/home/flip/Code/Stickmaps/data_files/negative_depth.dmp')
    importer.run()
    #importer.read_dump_file('/home/flip/Code/stickmaps/data_files/findingmnemo_orig.dmp')
    # print(f"DEVICE is at: {importer.get_device_location()}")
    # importer.read_from_device()
    # importer.write_dumpfile('/tmp/fuariane.dmp')
    # survey = importer.get_data()
    # foo = 'bar'