
import lib.dongle_cmds as d
import time


register = {'avail_NVM_slots': {'d_func': d.read_dma_cmd,'reg': ['0xc2', '0x00'],'data_length': 4, 'parse_idx':(0,1), 'mask': 0xFF, 'function': 'int_8bit'},
            'device_ID'      : {'d_func': d.read_smb_cmd,'reg': ['0xad'],        'data_length': 4, 'parse_idx':(2,3), 'mask': 0xFF, 'function': 'read_reg'},
            'revision'       : {'d_func': d.read_smb_cmd,'reg': ['0xae'],        'data_length': 5, 'parse_idx':(1,5), 'mask': 0xFF, 'function': 'rev_reg'},
            'prog_status'    : {'d_func': d.read_dma_cmd,'reg': ['0x07', '0x07'],'data_length': 4, 'parse_idx':(0,1), 'mask': 0xFF, 'function': 'int_8bit'},
            'bank_status'    : {'d_func': d.read_dma_cmd,'reg': ['0x09', '0x07'],'data_length': 4, 'parse_idx':(0,4), 'mask': 0xFF, 'function': 'read_reg'},
            'config_id'      : {'d_func': d.read_dma_cmd,'reg': ['0xc1', '0x00'],'data_length': 4, 'parse_idx':(0,1), 'mask': 0xFF, 'function': 'read_reg'},
            'crc'            : {'d_func': d.read_dma_cmd,'reg': ['0x3f', '0x00'],'data_length': 4, 'parse_idx':(0,4), 'mask': 0xFF, 'function': 'rev_reg'},
            
            'load_FW'               : {'d_func': d.write_smb_cmd,'reg':['0xe6'], 'data': ['0x10','0x00'], 'function': 'write_reg'},
            'recomp_OTP_bounds'     : {'d_func': d.write_smb_cmd,'reg':['0xe6'], 'data': ['0x06','0x28'], 'function': 'write_reg'},
            'wake_FW'               : {'d_func': d.write_smb_cmd,'reg':['0xe6'], 'data': ['0x03','0x00'], 'function': 'write_reg'},
            'apply_project_settings': {'d_func': d.write_smb_cmd,'reg':['0xe7'], 'data': ['0x01','0x00'], 'function': 'write_reg'},
            'restart_FW'            : {'d_func': d.write_smb_cmd,'reg':['0xe6'], 'data': ['0x07','0x00'], 'function': 'write_reg'},
            'restcfg'               : {'d_func': d.write_smb_cmd,'reg':['0xf2'], 'data': ['0x00'],        'function': 'write_reg'},
            
            'fw_revision'    : {'d_func': d.read_dma_cmd,'reg': ['0xc3', '0x00'],'data_length': 5, 'parse_idx':(0,5), 'mask': 0xFF, 'function': 'rev_reg'},
            
           
            'halt_FW'               : {'d_func': d.write_smb_cmd,'reg':['0xe6'], 'data': ['0x02','0x00'], 'function': 'write_reg'},
            'commit_patch_data'     : {'d_func': d.write_smb_cmd,'reg':['0xe6'], 'data': ['0x0f','0x00'], 'function': 'write_reg'},
            'patch_status'   : {'d_func': d.read_dma_cmd,'reg': ['0xda', '0x00'],'data_length': 4, 'parse_idx':(3,4), 'mask': 0x10, 'function': 'read_reg'}}


#readsmb  - reg, data_length, dev_addr
#writesmb - reg, data_length, data, dev_addr  
#readdma  - reg,data_length, dev_addr
#writedma - reg, data_length=2, data, dev_addr  #same as writesmb?



class Command:
    def __init__(self,reg_key, dev_addr):
        self.dev_addr = dev_addr
        self.params = register[reg_key]
        self.dfunc       = self.params['d_func']
        self.reg         = self.params['reg']
        self.functiondict  = {'read_reg'    : self.read_reg,   'rev_reg'  : self.rev_reg, 
                              'int_8bit'    : self.int_8bit,   'bin32'    : self.bin32, 
                              'apply_mask'  : self.apply_mask, 'write_reg': self.write_reg}
        
    def read_reg(self):
        a,b = self.params['parse_idx']
        return self.dfunc(self.reg,self.params['data_length'],self.dev_addr)[a:b]
    
    def rev_reg(self):
        data = self.read_reg()
        data.reverse()
        return data
    
    def int_8bit(self):
        data = self.read_reg()
        return int(data[0],16)
    
    def decimal(self,data):
        return d.bytearray2decimal(data)
        
    def bin32(self,data):
        pass
    
    def apply_mask(self):
        data = self.read_reg() #int_8bit()
        #convert to integer
        return data #& self.params['mask']
    
    def formatted(self):
        return self.functiondict[self.params['function']]()
    
    def write_reg(self):
        data = self.params['data']
        data_length = len(data)
        self.dfunc(self.reg,data_length,data,self.dev_addr)
        
        
    
    


def parse_line(line,position_tuple):
    start, stop = position_tuple
    return line[start:stop]

def is_header(line):
    return parse_line(line,header_dict['type']) == '49'

def data_2_list(data):
    datalist = [data[i:i+2] for i in range(0, len(data), 2)]
    datalist.reverse()
    return datalist

def check_ID(header='duh',dev_addr=0x60):
    file_id = parse_line(header[0],(8,16))[4:6]
    ic_id = Command('device_ID',dev_addr).formatted()[0][2:4]
    return file_id==ic_id

def check_REV(config_or_firmware = 'config',header='duh',dev_addr=0x60):
    def element_cmp(a,b):
        a,b = int(a,16), int(b,16)
        return a == b 

    def cmp_a_b(a,b):
        result = [element_cmp(i,j) for i,j in zip(a,b)]
        if config_or_firmware == 'config':
            result[3] = a > b
        else:
            result[3] = a == b
        return all(result)

    file_rev = parse_line(header[1],(8,16))
    file_rev = [file_rev[i:i+2] for i in range(0, len(file_rev), 2)]
    ic_rev = Command('revision',dev_addr).formatted()
    return cmp_a_b(ic_rev,file_rev)
  


class Cmdline:
    def __init__(self,line):
        #self.numbytes = int(line[2:4],16)
        self.pmbaddr  = hex(int(line[4:6],16)>>1)
        self.cmd      = line[6:8]
        self.data = data_2_list(line[8:-2]) 
        self.data.reverse()
        
    def write(self):
        d.write_smb_cmd(int(self.cmd,16),len(self.data),self.data,int(self.pmbaddr,16)) 

class FWcmdline:
    def __init__(self,line,dev_addr):
        self.pmbaddr = dev_addr
        self.cmd = line[2:4]
        self.data = data_2_list(line[5:]) 
        #self.data.reverse()
        if self.cmd == 'c7':
            self.data = self.data[0:2]
            
    def write(self):
        d.write_smb_cmd(int(self.cmd,16),len(self.data),self.data,self.pmbaddr)

class Config_cmdline:
    def __init__(self,line,dev_addr):
        self.line = line
        self.pmbaddr = dev_addr
        self.descr = self.line[:20].rstrip()
        self.reg  = data_2_list(self.line[61:].rstrip())
        self.data = data_2_list(self.line[37:47].rstrip())
        self.add_leading_0byte_if_r()  
        
    def add_leading_0byte_if_r(self):
        if self.descr[0] == 'r' and len(self.reg)==1:
            self.reg.append('00') #is trailing since has been reversed by data_to_list()
        
    def write(self):
        if len(self.reg) ==2:
            d.write_dma_cmd(self.reg,len(self.data),self.data,self.pmbaddr)
        else:
            d.write_smb_cmd(self.reg,len(self.data),self.data,self.pmbaddr)
    

def load_OTP_commands(commandlist):
    for line in commandlist:
        command=Cmdline(line)
        command.write()
        time.sleep(.02)
        
def write_to_OTP(lastline):
    command=Cmdline(lastline)
    command.write()

def load_fw_commands(commandlist,dev_addr):
    for line in commandlist:
        command=FWcmdline(line,dev_addr)
        command.write()
        time.sleep(.005)       
            
def load_config_commands(commandlist,dev_addr):
    for line in commandlist:
        command=Config_cmdline(line,dev_addr)
        try:
            command.write()
        except:
            print(line)
        time.sleep(.005) 
    
    
class Enable:
    def __init__(self,dev_addr=0x60):
        self.dev_addr = dev_addr
        
    def on(self):
        d.write_smb_cmd(0x01,1,['0x80'],self.dev_addr)
        time.sleep(0.25)
        state = d.read_smb_cmd(0x01,1,self.dev_addr)
        #print(state)
    
    def off(self):
        d.write_smb_cmd(0x01,1,['0x00'],self.dev_addr)
        time.sleep(0.25)
        state = d.read_smb_cmd(0x01,1,self.dev_addr)
        #print(state)
    
    def status(self):
        return d.read_smb_cmd(0x01,1,self.dev_addr)


def set_page(page,dev_addr):
    reg=['0x00']
    data = [hex(page)]
    d.write_smb_cmd(reg,1,data,dev_addr)
