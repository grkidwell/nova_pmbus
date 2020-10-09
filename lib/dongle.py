"""
Module for Intersil USB to I2C dongle
"""
from collections import OrderedDict
import pywinusb.hid as hid

LATEST_FW_VERSION = 3.1

# Intersil's USB vendor ID
VENDOR_ID = 0x09aa

# Max number of particular I2C transaction types that can fit into a single
# hihg-throughput packet
MAX_PACKET_WORDS = 12
MAX_PACKET_BYTES = 15

# Dongle Speeds
ONE_HUNDRED_KHZ = 1e5
FOUR_HUNDRED_KHZ = 4e5
ONE_MHZ = 1e6

# Using module level variables so the names are correct
# pylint: disable=invalid-name
device_filter = hid.HidDeviceFilter

_device_cache = OrderedDict()
_opened_devices = set()


class _I2CInterface(object):
    """
    Intersil dongle_test control class. Class should not be used directly
    but proxied through a I2C instance
    """

    def __init__(self, device, slave_address):
        super(_I2CInterface, self).__init__()
        self.device = device
        self._input_report = self.device.find_input_reports()[0]
        self._output_report = self.device.find_output_reports()[0]
        self._target = next(iter(self._output_report.keys()))
        self._slave_address = slave_address
        self.s_alert = True

    def __str__(self):
        return '<%s at %#x>' % (self.__class__.__name__, id(self))

    @property
    def device_path(self):
        """
        :return: The device path of the dongle_test object it wraps
        """
        return self.device.device_path

    def close(self):
        """Close connection to interface"""
        close_device(self.device)

    def zone_block_parse(self, data):
        devs = []
        i = 0
        while i < 61 and int(data[i]) != 0:
            length = int(data[i])
            devs.append(data[i + 1:i + length + 2])
            i += length + 2
        return devs

    def zone_bw_parse(self, data, dev_size):
        devs = []
        for i, d in enumerate(data, 1):
            if i % dev_size == 0 and d != 0:
                devs.append(data[i - dev_size:i])
        return devs

    def parse_zone_data(self, data, dev_size):
        if dev_size == 0:
            return self.zone_block_parse(data)
        else:
            return self.zone_bw_parse(data, dev_size + 1)

    def rshift(self, val, n):
        return (val % 0x100000000) >> n

    def format_zone_data(self, devs):
        strs = []
        for dev in devs:
            strs.append("Device: " + '{}'.format(hex(self.rshift(dev[-1], 1))) + "\n" +
                        "Data: " + '[{}]'.format(', '.join(hex(x) for x in dev[:-1])) + '\n\n')
        return strs

    def _build_ht_buffer(self, cmds):
        # TODO need to add check somewhere to make sure all cmds will fit
        buff = [0] * 63
        buff[0] = 19
        buff[1] = len(cmds)
        i = 2
        for cmd in cmds:
            buff[i] = cmd["slave_addr"]
            buff[i + 1] = cmd["size"]
            buff[i + 2] = 1                 # Start reg length
            buff[i + 3] = cmd["reg_addr"]
            if cmd["data"] and type(cmd["data"]) is list:
                buff[(i + 4):(i + 4) + cmd["size"]] = cmd["data"][:cmd["size"]]
            elif cmd["data"]:
                buff[(i + 4)] = cmd["data"]
            i += 4 if cmd["slave_addr"] & 1 else (buff[i + 1] + buff[i + 2] + 1)
        return buff

    def _generate_cmd_dicts(self, slave_addr, reg_addr, size, count, data, **kwargs):
        cmds = []
        for i in range(count):
            cmds.append({"slave_addr": slave_addr,
                         "reg_addr": reg_addr,
                         "size": size,
                         "data": data})
        return cmds

    def _get_ht_write_cmd_codes(self, buff):
        cmds = []
        i = 2
        for x in range(buff[1]):
            # Only care about single byte reg addresses now
            cmds.append(buff[i+3])
            i += 4 if buff[i] & 1 else (buff[i + 1] + buff[i + 2] + 3)
        return cmds

    def _parse_ht_response(self, in_buff, out_buff):
        print('Overflow Status:    0x{:02X}'.format(out_buff[1]))
        print('I2C Response Count: {:d}\n'.format(out_buff[2]))
        cmds = self._get_ht_write_cmd_codes(in_buff)
        i = 3
        for x in range(out_buff[2]):
            ttype = 'READ' if out_buff[i + 1] & 1 else 'WRITE'
            out = ('Response {:d}\n'
                   '\tSlave Addr:         0x{:02X}\n'
                   '\tReg Addr:           0x{:02X}\n'
                   '\tTransaction Type:   {:s}\n'
                   '\tTransaction Status: 0x{:02X}\n').format(x, out_buff[i + 1] >> 1, cmds[x], ttype, out_buff[i + 2])
            if out_buff[i] > 2:
                data = out_buff[i + 3 : i + out_buff[i] + 1]
                out += '\tTransaction Data:   {0}\n'.format(['0x{:02X}'.format(y) for y in data])
            print(out)
            i += out_buff[i] + 1

    def ht_transaction_rep(self, reg_addr, size, count, data=None, **kwargs):
        """
        Handles high-throughput PMBus transaction request

        :param reg_addr:
        :param size:
        :param count:
        :param kwargs:
        :return:
        """
        slave_addr = (
            kwargs['slave_addr']
            if 'slave_addr' in kwargs else
            self._slave_address
        )
        ignore_nack = (
            kwargs['ignore_nack'] is True if 'ignore_nack' in kwargs else False
        )
        use_block = (
            kwargs['use_block'] is True if 'use_block' in kwargs else False
        )
        extend_command = (
            kwargs['extend_command'] if 'extend_command' in kwargs else None
        )
        is_zone = (
            kwargs['zone'] if 'zone' in kwargs else False
        )

        cmds = self._generate_cmd_dicts(slave_addr, reg_addr, size, count, data)
        write_buffer = self._build_ht_buffer(cmds)
        #print("Sent down for ht-transaction")
        #print(write_buffer)

        self._output_report[self._target] = write_buffer
        self._output_report.send()
        read_buffer = self._input_report.get()
        #print("Read back from ht-transaction")
        #print(read_buffer)
        #self._parse_ht_response(read_buffer)
        return read_buffer

    def run_generated_ht_vec(self, write_buffer):
        self._output_report[self._target] = write_buffer
        self._output_report.send()
        read_buffer = self._input_report.get()
        print("Read back from ht-transaction")
        print(read_buffer)
        self._parse_ht_response(write_buffer, read_buffer)
        return read_buffer

    def read(self, reg_addr, size, **kwargs):
        """
        Perform I2C read

        :param reg_addr: I2C reg_addr to send to device
        :param size: Size in bytes of the data to be read
        :keyword mode: If mode is set to 'int' then data will be returned as a
            single integer, if mode is not set, returns array of bytes
        :return: Tuple containing (status code, read data)
        """
        slave_addr = (
            kwargs['slave_addr']
            if 'slave_addr' in kwargs else
            self._slave_address
            )
        ignore_nack = (
            kwargs['ignore_nack'] is True if 'ignore_nack' in kwargs else False
            )
        use_block = (
            kwargs['use_block'] is True if 'use_block' in kwargs else False
            )
        extend_command = (
            kwargs['extend_command'] if 'extend_command' in kwargs else None
            )
        zone = (
            kwargs['zone'] if 'zone' in kwargs else None
            )

        self._dev_write(
            ((slave_addr & 0x7f) << 1) + 1,
            reg_addr,
            0 if use_block else size,
            extend_command,
            extend_command=extend_command,
            zone=zone
            )
        if extend_command is not None:
            result = self._dev_read(ignore_nack, zone=True)
            parsed = self.parse_zone_data(result, size)
            return self.format_zone_data(parsed)
        else:
            result = self._dev_read(ignore_nack)
        if use_block and result is not None:
            return bytes(
                 result[1:1 + result[0]]
                 )
        elif result is not None:
            hexres = []
            for res in result:
                hexres.append(hex(res))
            return hexres[:size]
        else:
            return None

    # IOMan requires transaction arguments to be all positional
    # pylint: disable=too-many-arguments
    def write(self, reg_addr, size, data, **kwargs):
        """
        Perform I2C write

        :param reg_addr: I2C reg_addr to send to device
        :param size: size in bytes of data to be written
        :param data: Data to be written in the format of a list of bytes
        :keyword mode: If mode is set to 'int' then input data is single
            integer, if mode is not set, data must be an array of bytes
        :return: Write status code
        """
        slave_addr = (
            kwargs['slave_addr']
            if 'slave_addr' in kwargs else
            self._slave_address
            )
        ignore_nack = (
            kwargs['ignore_nack'] is True if 'ignore_nack' in kwargs else False
            )
        use_block = (
            kwargs['use_block'] is True if 'use_block' in kwargs else False
            )
        buf_size, write_data = (
            (len(data) + 1, len(data).to_bytes(1, 'little') + data)
            if use_block else
            (size, data)
            )
        zone = (
            kwargs['zone'] if 'zone' in kwargs else None
        )
        self._dev_write(
            (slave_addr & 0x7f) << 1, reg_addr, buf_size, write_data, zone=zone
            )
        self._dev_read(ignore_nack)

    def read_fw_version(self):
        """
        Request dongle firmware version info
        """
        write_buffer = [0] * 63
        write_buffer[0] = 0  # Value for FW version

        self._output_report[self._target] = write_buffer
        self._output_report.send()
        return self._dev_read(False)

    def setup_i2c(self, mode):
        """
        Perform dongle_test initialization
        """
        write_buffer = [0] * 63
        write_buffer[0] = 4  # Value for I2C config
        write_buffer[1] = 0  # Config write
        write_buffer[2] = mode  # ZONE mode
        write_buffer[3] = 0  # EXTHOLD Low
        write_buffer[4] = 0  # Don't toggle SCL if SDA stuck low

        self._output_report[self._target] = write_buffer
        self._output_report.send()

    def config(self):
        self.setup_i2c(1)

    def read_i2c_config(self):
        write_buffer = [0] * 63
        write_buffer[0] = 4  # Value for I2C config
        write_buffer[1] = 1  # Config read

        self._output_report[self._target] = write_buffer
        self._output_report.send()
        return self._dev_read(False)

    def setup_i2c_clk(self, clk_speed):
        """
        Perform dongle_test initialization
        """
        write_buffer = [0] * 63
        write_buffer[0] = 5  # Value for I2C clock config
        write_buffer[1] = 0  # Config write
        write_buffer[2] = int(8e6 / clk_speed)  # Repeated start

        self._output_report[self._target] = write_buffer
        self._output_report.send()

    def uart_write(self, data):
        dlen = len(data)

        write_buffer = [0] * 63
        write_buffer[0] = 0x41
        write_buffer[1] = dlen
        write_buffer[2:2 + dlen] = data[:dlen]
        self._output_report[self._target] = write_buffer
        self._output_report.send()

    def uart_init(self, mode0, mode1, sof, eof):
        write_buffer = [0] * 63
        write_buffer[0] = 0x40
        write_buffer[1] = mode0
        write_buffer[2] = mode1
        write_buffer[3] = sof
        write_buffer[4] = eof
        self._output_report[self._target] = write_buffer
        self._output_report.send()
        read_buffer = self._input_report.get()
        return read_buffer[2:]

    def uart_read_cache(self, cache_index):
        write_buffer = [0] * 63
        write_buffer[0] = 0x43
        write_buffer[1] = cache_index
        self._output_report[self._target] = write_buffer
        self._output_report.send()
        read_buffer = self._input_report.get()
        return read_buffer

    def _dev_write(self, slave_addr, reg_addr, buf_size, data=None, **kwargs):
        """
        Perform the dongle_test write
        """

        extend_command = (
            kwargs['extend_command'] if 'extend_command' in kwargs else None
        )
        usb_code = (
            20 if kwargs['zone'] else 6
        )

        write_buffer = [0] * 63
        write_buffer[0] = usb_code
        write_buffer[1] = slave_addr
        write_buffer[2] = buf_size
        write_buffer[3] = 1
        write_buffer[4] = reg_addr

        if extend_command is not None:
            write_buffer[3] = 2

        if data and type(data) is list:
            write_buffer[5:5 + buf_size] = data[:buf_size]
        elif data:
            write_buffer[5] = data

        self._output_report[self._target] = write_buffer
        self._output_report.send()

    def _dev_read(self, ignore_nack, **kwargs):
        """
        Perform the dongle_test read
        """
        zone = (
            kwargs['zone'] if 'zone' in kwargs else None
        )

        read_buffer = self._input_report.get()
        self.s_alert = (read_buffer[1] & 0x80) == 0x00
        if zone:
            print(read_buffer)
            return read_buffer[2:]
        if ignore_nack and (read_buffer[1] & 0x01) == 0x01:
            return None
        elif (read_buffer[1] & 0x01) == 0x01:
            print("DEV READ ERROR. RETRYING")
            #print(read_buffer)
            return
        return read_buffer[2:]


def connect_usb_interface(path_spec):
    """Return an HID-based interface handler"""
    if not _device_cache:
        search_devices()
    spec_parts = path_spec.split('::')
    interface = spec_parts[0].lower()
    if interface == 'i2c':
        slave_addr = int(spec_parts[1], 0) if spec_parts[1] else None
        device_path = (
            spec_parts[2] if len(spec_parts) == 3 else
            next(iter(_device_cache.keys()))
            )
        device = _device_cache[device_path]
        device.open()
        device_wrapper = _I2CInterface(device, slave_addr)
        device_wrapper.setup_i2c(0x01)
        device_wrapper.setup_i2c_clk(ONE_HUNDRED_KHZ)
        _opened_devices.add(device_path)
        return device_wrapper


def search_devices():
    """Search for connected Intersil USB HID devices"""
    device_list = device_filter(
        vendor_id=VENDOR_ID
        ).get_devices()
    for device in device_list:
        _device_cache[device.instance_id.split('\\')[-1]] = device
    try:
        return [path for path in _device_cache.keys()]
    except AttributeError as error:
        print(error)


def clear_device_cache():
    """Clear device cache, mostly needed to ensure sanity during unit tests"""
    _device_cache.clear()


def close_device(device):
    """Close connection to device"""
    device_path = device.instance_id.split('\\')[-1]
    if device_path in _opened_devices:
        _device_cache[device_path].close()
        _opened_devices.remove(device_path)


def close_connections():
    """Close all the connections so python can terminate"""
    for device_path in _opened_devices:
        _device_cache[device_path].close()

    # Empty opened device list
    _opened_devices.clear()
