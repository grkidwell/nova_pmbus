#!python3




import pandas as pd
from datetime import datetime
import click

class Config_cmdline:
    def __init__(self,line):
        self.line = line
        self.name = self.line[:20].rstrip()
        self.value = self.line[37:47].rstrip()
        self.addr  = self.line[61:].rstrip()
        
        self.add_leading_0byte_if_r()  
        
    def add_leading_0byte_if_r(self):
        if self.name[0] == 'r' and len(self.addr)==2:
            self.addr='00'+self.addr #.append('00') #is trailing since has been reversed by data_to_list()
        
def create_command_dict(commands):
    line   = [x for x,line in enumerate(commands)]
    name   = [Config_cmdline(line).name  for line in commands]
    value  = [Config_cmdline(line).value for line in commands]
    addr   = [Config_cmdline(line).addr  for line in commands]
    return {'line':line,'name':name, 'value': value, 'address': addr}
    
def create_diff_df_with_pagecalls(df1,df2):
    def add_missing_pagecalls(df_1,df_2,df_delta):
        df_delta_with_pages=df_delta.loc[:,['line','name','value','address']]
        for row in df_delta.index:
            line,name,value,addr = df_delta.loc[row,['line','name','value','address']]
            is_PMB_address=len(addr)==2
            if is_PMB_address:
                df_closest_preceeding_pageline = df_2[df_2['name']=='PAGE'][df2['line']<line].tail(1)
                df_delta_with_pages=df_delta_with_pages.append(df_closest_preceeding_pageline)
        df_delta_with_pages=df_delta_with_pages.sort_values(by=['line'])
        return df_delta_with_pages
    df_diff = df1.merge(df2,how='outer',indicator=True).loc[lambda x : x['_merge']=='right_only']
    df_diff = add_missing_pagecalls(df1,df2,df_diff)
    return df_diff

def create_file_header(header,crc):
    diff_header=header
    now=datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    diff_header[-1]=now
    header_contents=''
    for line in diff_header:
        header_contents=header_contents+f"{line}"+'\n'
    header_contents=header_contents+'\n'+crc+'\n'+'\n'
    return header_contents

def create_data_contents(delta):
    delta_list=delta[['name','value','address']].values.tolist()
    data_contents=''
    for line in delta_list:
        formatted_line = f"{line[0]:<35}{'0x'+line[1]:<22}"+'# 0x'+line[2]+'\n'
        data_contents = data_contents+formatted_line
    return data_contents

def create_file_contents(header_contents,data_contents):
    file_contents=header_contents+data_contents
    return file_contents

class file_delta:
    def __init__(self,oldfile,newfile,outputfile):
        self.outputfile = outputfile
        with open(oldfile) as file:
            file1_contents = file.read()
        with open(newfile) as file:
            file2_contents = file.read()
        lines1        = file1_contents.split('\n')
        lines2        = file2_contents.split('\n')
        commands1     = lines1[9:-1]
        commands2     = lines2[9:-1]
        header        = lines2[:6]
        crc           = lines2[7]
        command1_dict = create_command_dict(commands1)
        command2_dict = create_command_dict(commands2)
        df1           = pd.DataFrame(command1_dict) 
        df2           = pd.DataFrame(command2_dict)
        self.delta    = create_diff_df_with_pagecalls(df1,df2)
        hdr           = create_file_header(header,crc)
        cmds          = create_data_contents(self.delta)
        self.file_contents = create_file_contents(hdr,cmds)
        
    def write_outputfile(self):
        with open(self.outputfile, 'w') as diff_file:
            diff_file.write(self.file_contents)


if __name__=='__main__':

    @click.command()
    @click.option('--oldfile', prompt="old project filename ", help='this *.txt file is created by PowerNavigator')
    @click.option('--newfile', prompt="new project filename ", help='this *.txt file is created by PowerNavigator')
    @click.option('--outfile', prompt="output project filename ", help='this *.txt file can be used as an input file by config_2_ram.py')

    def inp(oldfile,newfile,outfile):
        diff = file_delta(oldfile,newfile,outfile)
        diff.write_outputfile()
        click.echo('')
        click.echo('diff file generated.  end of line')
        


    inp()
    #oldprojectfile = 'sample_files/ISL69269-0 0x60e.txt'
    #newprojectfile = 'sample_files/ISL69269-0 0x60f.txt'
    #outputfilename = 'diff_file_ef.txt'
    