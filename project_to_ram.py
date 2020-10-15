mport lib.nova_lib as nova
import sys
import click

configfilename = 'sample_files/ISL69269-0 0x60e.txt'
SMB_Add = 0x60

class inputfile:
    def __init__(self,filename):
        try:
            with open(filename) as file:
                file_contents = file.read()
        except:
            sys.exit("invalid filename! re-run program")
        self.commands = file_contents.split('\n')[9:-1]

def load_and_ready(cmds):
    nova.load_config_commands(cmds,SMB_Add)
    nova.Command('apply_project_settings',SMB_Add).write_reg()
    nova.set_page(0,SMB_Add)

onoff= nova.Enable(dev_addr=SMB_Add)

#main program
nova.set_page(0,SMB_Add)
onoff.off()

if __name__=='__main__':

    @click.command()
    @click.option('--inputfilename', prompt='input project or changes filename', 
                  help='this *txt file is created by either PowerNavigator or project_diff.py')

    def inp(inputfilename):
        commands = inputfile(inputfilename).commands
        load_and_ready(commands)
        click.echo('')
        click.echo('file loaded to RAM.')

    inp()

    #inputfilename = 'diff_file_bc.txt'





