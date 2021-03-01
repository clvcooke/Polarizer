import serial
import time


class Polarizer:

    # TODO: support multiple polarizers on the same bus
    def __init__(self, port, baudrate=9600, bytesize=8, parity='N', timeout=2, address=0, wait_time=0.01):
        self.address = address
        self.connection = serial.Serial(port, baudrate=baudrate, bytesize=bytesize, parity=parity, timeout=timeout)
        self.device_info = self.get_device_info()
        self.wait_time = wait_time

    @staticmethod
    def scan_for_devices():
        pass

    @staticmethod
    def twos_comp(val, bits):
        """compute the 2's complement of int value val"""
        if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
            val = val - (1 << bits)  # compute negative value
        return val

    def close(self):
        self.connection.close()

    def _send_command(self, command_id, hex_data=None):
        serial_data = f"{self.address}{command_id}"
        if hex_data is not None:
            serial_data += f"{hex_data}"
        self.connection.write(serial_data.encode())

    def _read_reply(self, num_bytes):
        reply = self.connection.read(num_bytes)
        reply_str = reply.decode()
        return reply_str

    def get_device_info(self):
        command_id = 'in'
        self._send_command(command_id)
        # terimates with carraige
        reply = self._read_reply(33 + 2)[:-2]
        # parse the reply
        model_number = int(reply[3:5], 16)
        serial_number = int(reply[5:13], 16)
        year = reply[13:17]
        firmware_version = reply[17:19]
        hardware_version = reply[19:21]
        travel = int(reply[21:25], 16)
        pulses = int(reply[25:33], 16)
        device_info = {
            'model_number': model_number,
            'serial_number': serial_number,
            'year': year,
            'firmware_version': firmware_version,
            'hardware_version': hardware_version,
            'travel': travel,
            'pulses': pulses
        }
        return device_info

    @staticmethod
    def parse_status(status_code):
        code_values = [
            'OK, no error',
            'Communication time out',
            'Mechanical time out',
            'Command error or not supported',
            'Value of out range',
            'Module isolated',
            'Module out of isolation',
            'Initializing error',
            'Thermal error',
            'Busy',
            'Sensor Error',
            'Motor Error',
            'Out of Range'
            'Over current error',
            'INVALID ERROR'
        ]
        return code_values[status_code]

    def get_status(self):
        command_id = 'gs'
        self._send_command(command_id)
        reply = self._read_reply(5 + 2)[:-2]
        status_code = int(reply[3:5], 16)
        return self.parse_status(status_code), status_code

    def save_motor_params(self):
        command_id = 'us'
        self._send_command(command_id)
        # reply through status
        status, status_code = self.get_status()
        if status_code == 0:
            return True
        else:
            return False

    def get_motor_params(self):
        command_id = 'i1'
        self._send_command(command_id)
        reply = self._read_reply(25 + 2)[:-2]
        loop = int(reply[3])
        motor = int(reply[4])
        current = int(reply[5:9], 16)
        ramp_up = int(reply[9:13], 16)
        ramp_down = int(reply[13:17], 16)
        forward_period = int(reply[17:21], 16)
        backward_period = int(reply[21:25], 16)
        return {
            'loop': loop,
            'motor': motor,
            'current': current,
            'ramp_up': ramp_up,
            'ramp_down': ramp_down,
            'forward_period': forward_period,
            'backward_period': backward_period
        }

    def wait_for_move(self):
        header = None
        reply = None
        while header is None or header == 'GS':
            time.sleep(self.wait_time)
            reply = self._read_reply(5)
            header = reply[1:3]
            if header == 'GS':
                # clear the carraige
                self._read_reply(2)
        reply += self._read_reply(11 - 5 + 2)[:-2]
        if header != 'PO':
            raise RuntimeError('Wrong header')
        position_data = self.twos_comp(int(reply[3:11], 16), 32)
        return position_data

    def home(self, direction='cw', blocking=True):
        command_id = 'ho'
        if direction == 'cw':
            hex_data = 0
        elif direction == 'ccw':
            hex_data = 1
        else:
            raise RuntimeError("Only cw and ccw are supported")
        self._send_command(command_id, hex_data=hex_data)
        # if we should wait for the homing to complete
        if blocking:
            return self.wait_for_move()
        else:
            return -1

    def move_absolute(self, position, blocking=True):
        command_id = 'ma'
        hex_data = hex(position)[2:]
        message_length = 8
        hex_data = '0' * (message_length - len(hex_data)) + hex_data.upper()
        self._send_command(command_id, hex_data=hex_data)
        if blocking:
            return self.wait_for_move()
        else:
            return -1

    def move_relative(self, amount, blocking=True):
        command_id = 'mr'
        hex_data = hex(amount)[2:]
        message_length = 8
        hex_data = '0' * (message_length - len(hex_data)) + hex_data.upper()
        self._send_command(command_id, hex_data=hex_data)
        if blocking:
            return self.wait_for_move()
        else:
            return -1

    def flush(self):
        self.connection.flush()
