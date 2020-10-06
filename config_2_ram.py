import lib.nova_lib as nova
import sys

configfilename = '' #'sample_files/ISL69269-0 0x60g.txt'
SMB_Add = 0x60

try:
    with open(configfilename) as file:
        file_contents = file.read()
except:
    sys.exit("enter valid filename into variable 'patchfilename' and rerun program")

    
lines        = file_contents.split('\n')
header       = lines[0:6]
crc          = lines[7]
commands     = lines[9:-1]

onoff= nova.Enable(dev_addr=SMB_Add)



#main program
nova.set_page(0,SMB_Add)
onoff.off()
try:
    nova.load_config_commands(commands,SMB_Add)
    nova.Command('apply_project_settings',SMB_Add).write_reg()
    nova.set_page(0,SMB_Add)
    print('load successful! exiting program.  end of line')
except:
    sys.exit("load failed! exiting program.  end of line")








