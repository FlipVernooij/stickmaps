import time
from datetime import datetime

import serial
from serial.tools import list_ports


class MnemoImporter:

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
