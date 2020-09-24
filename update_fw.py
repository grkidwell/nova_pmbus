import lib.nova_lib as nova
import sys

patchfilename = 'patch_2_0_5_0.txt'
SMB_Add = 0x60

try:
    with open(patchfilename) as file:
        file_contents = file.read()
except:
    sys.exit("enter valid filename into variable 'patchfilename' and rerun program")

    
lines        = file_contents.split('\n')
commands     = lines[0:-1]

def disable_controller():
    onoff= nova.Enable(dev_addr=SMB_Add)
    onoff.off()


#main program

print(f"silicon fw rev = {nova.Command('fw_revision',SMB_Add).formatted()}")
proceed = input("Enter 'y' to proceed ")
if proceed == "y" or proceed == "yes":
    disable_controller()
    print("halting fw")
    nova.Command('halt_FW',SMB_Add).write_reg()
    print("loading fw patch")
    nova.load_fw_commands(commands,SMB_Add)
    nova.Command('commit_patch_data',SMB_Add).write_reg()
    if (int(nova.Command('patch_status',SMB_Add).formatted()[0],16) >>4 & 1):
        input('fw patch successful! recycle Vcc then press enter to display fw revision')
        print(f"fw revision = {nova.Command('fw_revision',SMB_Add).formatted()}")
    else:
        print(f"fw patch failed!  fw revision = {nova.Command('fw_revision',SMB_Add).formatted()}")
        print('exiting program.  end of line')
else:
    sys.exit("exiting program.  end of line")




