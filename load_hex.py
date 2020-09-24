import lib.nova_lib as nova
import sys

hexfilename = '' #'ISL69269-1 0x60.hex'
SMB_Add = 0x60

try:
    with open(hexfilename) as file:
        file_contents = file.read()
except:
    sys.exit("enter valid filename into variable 'hexfilename' and rerun program")


lines        = file_contents.split('\n')
header       = lines[:5]
commands     = lines[5:-2]
exec_command = lines[-2]

def disable_controller():
    onoff= nova.Enable(dev_addr=SMB_Add)
    onoff.off()

def verify_device_and_file_versions():
    allgood = (nova.check_REV(header=header,dev_addr=SMB_Add) 
               and nova.Command('avail_NVM_slots',SMB_Add).formatted()
               and nova.check_ID(header=header,dev_addr=SMB_Add))
    return allgood

def write_hexfile_to_device():
    print("writing hex file to OTP")
    nova.load_commands(commands)
    nova.write_to_OTP(exec_command)

def reload_and_restart_fw():
    nova.Command('load_FW',SMB_Add).write_reg()
    nova.Command('recomp_OTP_bounds',SMB_Add).write_reg()
    nova.Command('wake_FW',SMB_Add).write_reg()
    nova.Command('restcfg',SMB_Add).write_reg()
        
def print_new_nvm_and_crc_info():
    slots = nova.Command('avail_NVM_slots',SMB_Add).formatted()
    print(f"Available NVM slots: {slots}")
    crc = nova.Command('crc',SMB_Add).formatted()
    print(f"new CRC: {crc}")
        



#main program

disable_controller()
if verify_device_and_file_versions():
    write_hexfile_to_device()
    if nova.Command('prog_status',SMB_Add).formatted() & 1:
        print("OTP programming successful!  Restarting FW")
        reload_and-restart_fw()
        print_new_nvm_and_crc_info()
        print("End of Line")
    else:
        errorcode = bin(int(nova.Command('bank_status',SMB_Add).formatted()[0],16))
        print(f"OTP programming failed.  Bank Status: {errorcode}")
else:
    print("Check REV, available NVM slots, and ID")













