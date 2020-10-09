# nova_pmbus
python libraries for Renesas Nova Digital Multiphase controllers

Jupyter notebook and stand alone *.py version for most of below utilities:

1. write_otp    - write *.hex file to OTP bank
   *edit input file variable at top of *.py program before running

2. update_fw    - update fw with *.txt file
   **edit input file variable at top of *.py program before running

3. project_to_ram - load project *.txt file directly to IC registers
   *.py version has commandline interface with prompts 

4. project_diff - create difflist from 2 project files.  
   *output file can be used by config_2_ram program 
   *.py version has commandline interface with prompts

5. pmbus_tool.ipynb - jupyter notebook utility for pmbus and dma read/write
