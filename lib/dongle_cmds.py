import lib.dongle as d
import time


def connect():
    dpath = d.search_devices()
    if not dpath:
        return None
    return d.connect_usb_interface("i2c::")
    
def dummy_read(dev_addr):
    try:
        dummy=dongle.read(0x01,2,slave_addr=dev_addr)
    except:
        print('error')

def list_and_str_2int(x):
    if type(x)==list:
        x=x[0]
    if type(x)==str:
        x=int(x,16)
    return x

def read_smb_cmd(cmd_code, data_length,dev_addr):
    cmd_code = list_and_str_2int(cmd_code)
    dummy_read(dev_addr)
    time.sleep(.005)
    
    try:
        result = dongle.read(reg_addr=cmd_code, size=data_length, slave_addr=dev_addr)
        time.sleep(0.005)
    except:
        time.sleep(0.005)
        print('error')
        result = dongle.read(reg_addr=cmd_code, size=data_length, slave_addr=dev_addr)
        time.sleep(0.005)
    result = dongle.read(reg_addr=cmd_code, size=data_length, slave_addr=dev_addr)
    return result
    
def write_smb_cmd(cmd_code, data_length, data, dev_addr):
    cmd_code = list_and_str_2int(cmd_code)
    data = [int(b, 16) for b in data]
    dongle.write(cmd_code, data_length, data, slave_addr=dev_addr)
    
def write_dma_cmd(reg,data_length,data,dev_addr):    #swapped length and data
    write_smb_cmd(0xc7,2,reg,dev_addr)
    time.sleep(0.005)
    write_smb_cmd(0xc5,4,data,dev_addr)
        
def read_dma_cmd(reg, data_length, dev_addr):
#    try:
#        write_smb_cmd(reg,2,dev_addr)
#        time.sleep(0.25)
#        read_smb_cmd(0xc5,data_length,dev_addr)
#        time.sleep(0.25)
#    except:
    data_length = 4
    write_smb_cmd(0xc7,2,reg,dev_addr)
    time.sleep(0.005)
    read_smb_cmd(0xc5,data_length,dev_addr)
    time.sleep(0.005)
    return read_smb_cmd(0xc5,data_length,dev_addr)

def bytearray2mv(bytearray):
    hexbytearray = ''
    for byte in reversed(bytearray):
        hexbytearray += f"{int(byte,16):02x}"
    return int(hexbytearray,16) 

def bytearray2decimal(bytearray):
    hexbytearray = ''
    for byte in reversed(bytearray):
        hexbytearray += f"{int(byte,16):02x}"
    return int(hexbytearray,16) 

def mv2bytearray(mv):
    return [hex(byte) for byte in list(((mv).to_bytes(2,byteorder='little')))]
  
def decimal2bytearray(mv):
    return [hex(byte) for byte in list(((mv).to_bytes(2,byteorder='little')))]

dongle = connect()