import os
import sys
from glob import glob
import shutil
import hashlib
from remove_data_from_DAQ_PC import check_if_exists_in_HDD
import random

class bcolors:
    HEADER     = '\033[95m'
    OKCYAN     = '\033[96m'
    OKGREEN    = '\033[92m'
    WARNING    = '\033[93m'
    ERROR      = '\033[91m'
    ERRORBLOCK = '\033[41m'
    ENDC       = '\033[0m'
    BOLD       = '\033[1m'
    UNDERLINE  = '\033[4m'
    INFO       = '\033[94m'
    INFOBLOCK  = '\033[44m'
    CMD        = '\033[35m'

def cksum_sha256(file_name) :
    sha256 = hashlib.sha256()
    with open(file_name, 'rb') as f :
        for chunk in iter(lambda: f.read(65536), b"") :
            sha256.update(chunk)
    return sha256.hexdigest()

def valid_with_checksum_sha256(SSD_SORTED_DIR, HDD_SORTED_DIR) :
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Comparing SHA256 checksum values for SSD & HDD files...")
    for idx, (ssd_file, hdd_file) in enumerate(zip(SSD_SORTED_DIR, HDD_SORTED_DIR)) :
        sha256_ssd_file = cksum_sha256(ssd_file)
        sha256_hdd_file = cksum_sha256(hdd_file)
        if not (sha256_ssd_file == sha256_hdd_file) :
            print(f"{bcolors.ERRORBLOCK}[ERROR]{bcolors.ENDC} SHA256 checksum failed!!!")
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SHA256 checksum of SSD file : {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} and HDD file {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} does not match. PLEASE CHECK!!" %(ssd_file, hdd_file) )
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SHA256 decimal checksum of SSD file {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} : {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(ssd_file, int(sha256_ssd_file, base=16)))
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SHA256 decimal checksum of HDD file {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} : {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(hdd_file, int(sha256_hdd_file, base=16)))
            sys.exit()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SHA256 checksum compare {bcolors.OKGREEN}{bcolors.BOLD}successful!{bcolors.ENDC} Proceeding...")

def check_file_size(SSD_SORTED_DIR, HDD_SORTED_DIR) :
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking number of events stored in SSD & HDD files...")
    for idx, (ssd_file, hdd_file) in enumerate(zip(SSD_SORTED_DIR, HDD_SORTED_DIR)) :
        ssd_file_size = os.stat(ssd_file).st_size
        hdd_file_size = os.stat(hdd_file).st_size
        base_size = 65536
        if ( (ssd_file_size == 0) and (hdd_file_size == 0) ) : continue
        if "Fast" in ssd_file : base_size = 256
        if not ( ( (ssd_file_size%base_size) == 0) or ( (hdd_file_size%base_size) == 0) ) :
            print(f"{bcolors.ERRORBLOCK}[ERROR]{bcolors.ENDC} Event number check failed!!!")
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Some file does not contain proper number of evt. Please check")
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} # of event in SSD file : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC} == {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(ssd_file, (ssd_file_size//base_size)))
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} # of event in HDD file : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC} == {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(hdd_file, (hdd_file_size//base_size)))
            sys.exit()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking event number {bcolors.OKGREEN}{bcolors.BOLD}successful!{bcolors.ENDC} Proceeding...")

def decode_meta_data(meta_data_bits) :
    data = []
    ## data length
    data_length = int(bin(int(meta_data_bits[0].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(int(meta_data_bits[1].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 8), base=2)
    data_length = data_length + itmp
    itmp = int(bin(int(meta_data_bits[2].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 16), base=2)
    data_length = data_length + itmp
    itmp = int(bin(int(meta_data_bits[3].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp & 0b11111111), base=2)
    data_length = data_length + itmp
    data.append(data_length)

    ## run number
    run_number = int(bin(int(meta_data_bits[4].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(int(meta_data_bits[5].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 8), base=2)
    run_number = run_number + itmp
    data.append(run_number)
    
    ## trigger type
    tcb_trig_type = int(bin(int(meta_data_bits[6].hex(), base=16) & 0b11111111), base=2)
    data.append(tcb_trig_type)

    ## TCB trigger #
    tcb_trig_number = int(bin(int(meta_data_bits[7].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(int(meta_data_bits[8].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 8), base=2)
    tcb_trig_number = tcb_trig_number + itmp
    itmp = int(bin(int(meta_data_bits[9].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 16), base=2)
    tcb_trig_number = tcb_trig_number + itmp
    itmp = int(bin(int(meta_data_bits[10].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 24), base=2)
    tcb_trig_number = tcb_trig_number + itmp
    data.append(tcb_trig_number)

    ## TCB trigger time
    fine_time = int(bin(int(meta_data_bits[11].hex(), base=16) & 0b11111111), base=2)
    fine_time = fine_time * 11     ## actually * (1000 / 90)
    coarse_time = int(bin(int(meta_data_bits[12].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(int(meta_data_bits[13].hex(), base=16) & 0b11111111), base=2)
    ltmp = itmp = int(bin(itmp << 8), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[14].hex(), base=16) & 0b11111111), base=2)
    ltmp = itmp = int(bin(itmp << 16), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[15].hex(), base=16) & 0b11111111), base=2)
    ltmp = itmp = int(bin(itmp << 24), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[16].hex(), base=16) & 0b11111111), base=2)
    ltmp = itmp = int(bin(itmp << 32), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[17].hex(), base=16) & 0b11111111), base=2)
    ltmp = itmp = int(bin(itmp << 40), base=2)
    coarse_time = coarse_time + ltmp
    coarse_time = coarse_time * 1000   ## get ns
    tcb_trig_time = fine_time + coarse_time
    data.append(tcb_trig_time)

    ## mid
    mid = int(bin(int(meta_data_bits[18].hex(), base=16) & 0b11111111), base=2)
    data.append(mid)

    ## local trigger #
    local_trig_number = int(bin(int(meta_data_bits[19].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(int(meta_data_bits[20].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 8), base=2)
    local_trig_number = local_trig_number + itmp
    itmp = int(bin(int(meta_data_bits[21].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 16), base=2)
    local_trig_number = local_trig_number + itmp
    itmp = int(bin(int(meta_data_bits[22].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 24), base=2)
    local_trig_number = local_trig_number + itmp
    data.append(local_trig_number)

    ## local trigger #
    local_trigger_pattern = int(bin(int(meta_data_bits[23].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(int(meta_data_bits[24].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 8), base=2)
    local_trigger_pattern = local_trigger_pattern + itmp
    itmp = int(bin(int(meta_data_bits[25].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 16), base=2)
    local_trigger_pattern = local_trigger_pattern + itmp
    itmp = int(bin(int(meta_data_bits[26].hex(), base=16) & 0b11111111), base=2)
    itmp = int(bin(itmp << 24), base=2)
    local_trigger_pattern = local_trigger_pattern + itmp
    data.append(local_trigger_pattern)

    ## local trigger time
    fine_time = int(bin(int(meta_data_bits[27].hex(), base=16) & 0b11111111), base=2)
    fine_time = fine_time * 11     ## actually * (1000 / 90)
    coarse_time = int(bin(int(meta_data_bits[28].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(int(meta_data_bits[29].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(itmp << 8), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[30].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(itmp << 16), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[31].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(itmp << 24), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[32].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(itmp << 32), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[33].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(itmp << 40), base=2)
    coarse_time = coarse_time + ltmp
    coarse_time = coarse_time * 1000   ## get ns
    local_trig_time = fine_time + coarse_time
    data.append(local_trig_time)

    diff_time = local_trig_time - tcb_trig_time
    data.append(diff_time)
    
    return data

## data[0] = data_length
## data[1] = run_number
## data[2] = tcb_trig_type
## data[3] = tcb_trig_number
## data[4] = tcb_trig_time
## data[5] = mid
## data[6] = local_trig_number
## data[7] = local_trigger_pattern
## data[8] = local_trig_time
## data[9] = diff_time

def print_meta_data(HDD_SORTED_DIR, fraction=0.1, metadata_size=64) :
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Printing out random file's metadata...", end="\n\n")
    total_number_of_files = len(HDD_SORTED_DIR)
    files_to_investigate = int(total_number_of_files * fraction) if total_number_of_files >= 10 else total_number_of_files
    file_num_list = random.sample(HDD_SORTED_DIR, files_to_investigate)
    for hdd_file in file_num_list :
        meta_data_bits = []
        hdd_file_size = os.stat(hdd_file).st_size
        if hdd_file_size == 0 : continue
        base_size = 65536 if "Wave" in hdd_file else 256
        evt_number = (hdd_file_size//base_size)
        random_evt_num = random.randint(0, evt_number)
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking metadata of HDD file : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(hdd_file))
        with open(hdd_file, "rb") as f :
            f.seek(random_evt_num * base_size)
            for i in range(metadata_size) :
                meta_data_bits.append(f.read(1))
        meta_data = decode_meta_data(meta_data_bits)
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Data Length = %s, Run # = %s, MID = %s" %(meta_data[0], meta_data[1], meta_data[5]))
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Trigger type = %s, Local trigger pattern = %s" %(meta_data[2], meta_data[7]))
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} TCB trigger # = %s, Local trigger # = %s" %(meta_data[3], meta_data[6]))
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} TCB trigger time = %s, Local trigger time = %s, difference = %s" %(meta_data[4], meta_data[8], meta_data[9]), end="\n\n")
    confirmed = ask_if_sure()
    if not confirmed : sys.exit()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Metadata check all clear. Proceeding...")

# def check_meta_data(HDD_SORTED_DIR, fraction=0.1, metadata_size=64) :
#     print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Printing out random file's metadata...", end="\n\n")
#     total_number_of_files = len(HDD_SORTED_DIR)
#     files_to_investigate = int(total_number_of_files * fraction) if total_number_of_files >= 10 else total_number_of_files
#     file_num_list = random.sample(HDD_SORTED_DIR, files_to_investigate)
#     for hdd_file in file_num_list :
#         hdd_file_base_name = hdd_file.split("/")[-1]
#         hdd_file_RunNum = hdd_file_base_name.split("_")[1]
#         hdd_wave_or_fast = hdd_file_base_name.split("_")[2]
#         hdd_file_MID = hdd_file_base_name.split("_")[4]

#         meta_data_bits = []
#         hdd_file_size = os.stat(hdd_file).st_size
#         base_size = 65536 if "Wave" in hdd_wave_or_fast else 256
#         evt_number = (hdd_file_size//base_size)
#         random_evt_num = random.randint(0, evt_number)

#         print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Matching metadata with actual HDD file : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(hdd_file))
#         with open(hdd_file, "rb") as f :
#             f.seek(random_evt_num * base_size)
#             for i in range(metadata_size) :
#                 meta_data_bits.append(f.read(1))
#         meta_data = decode_meta_data(meta_data_bits)
#         if not ( () ) :
#     print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Metadata check all clear. Proceeding...")

def ask_if_sure() :
    answer = input(f"{bcolors.ERRORBLOCK}{bcolors.BOLD}[CONFIRMATION]{bcolors.ENDC} Are you sure the meta data is correct? [y/n] ")
    while not ( (answer == 'y') or (answer == 'n') ) :
        print(f"{bcolors.WARNING}[WARNING]{bcolors.ENDC} Only available options are `{bcolors.OKGREEN}{bcolors.BOLD}y{bcolors.ENDC}` or `{bcolors.OKGREEN}{bcolors.BOLD}n{bcolors.ENDC}`, please check your reply")
        answer = input(f"{bcolors.ERRORBLOCK}{bcolors.BOLD}[CONFIRMATION]{bcolors.ENDC} Are you sure the meta data is correct? [y/n] ")
    if answer == 'y' : return True
    elif answer == 'n' : return False

def action_after_valid(source_path) :
    base_source_path = source_path.split('/')[-2]
    new_base_source_path = base_source_path.replace( "_copied", "_validated" )
    new_source_path = source_path.replace(base_source_path, new_base_source_path)
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Source folder {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC} will be renamed to {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %( source_path, new_source_path ))
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} {bcolors.BOLD}{bcolors.OKGREEN}Validation of the data completed. PLEASE WRITE LOG & PROCEED TO REMOVE STEP{bcolors.ENDC}")
    os.rename(source_path, new_source_path)
    
#############################################################################################################
if __name__ == "__main__" :

    if not len(sys.argv) == 3 : 
        print(f"{bcolors.ERROR}[ERROR] Invalid command line argument. Require 2 arguments to validate copied data {bcolors.ENDC}")
        print(f"{bcolors.INFO}[Usage]{bcolors.ENDC} ./Valid_Data.sh {bcolors.UNDERLINE}<source_path>{bcolors.ENDC} {bcolors.UNDERLINE}<destination_path>{bcolors.ENDC}")
        print(f"{bcolors.INFO}[Example]{bcolors.ENDC} ./Valid_Data.sh  ~/scratch/202208TB/SSD/SSD_Run_999/ /Volumes/HDD_16TB_1/HDD_Run_999/")
        sys.exit()
    
    SSD_DIR = sys.argv[1]
    HDD_DIR = sys.argv[2]

    if not SSD_DIR.endswith("/") : SSD_DIR += "/"
    if not HDD_DIR.endswith("/") : HDD_DIR += "/"

    if not os.path.exists(SSD_DIR) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Original SSD data with path {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (SSD_DIR) )
        sys.exit()
    if not os.path.exists(HDD_DIR) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Copied HDD data with path {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (HDD_DIR) )
        sys.exit()

    if not ("SSD" and "Run") in sys.argv[1] :
        print(f"{bcolors.ERRORBLOCK}###########################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] DAQ data must be stored under {bcolors.BOLD}{bcolors.UNDERLINE}SSD{bcolors.ENDC}{bcolors.ERRORBLOCK} with proper {bcolors.BOLD}{bcolors.UNDERLINE}Run number{bcolors.ENDC}{bcolors.ERRORBLOCK}. PLEASE CHECK ARGUMENTS!!!{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}###########################################################################################{bcolors.ENDC}")
        sys.exit()
    if not ("_copied") in sys.argv[1] :
        print(f"{bcolors.ERRORBLOCK}#############################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] DAQ data must be {bcolors.BOLD}{bcolors.UNDERLINE}COPIED{bcolors.ENDC}{bcolors.ERRORBLOCK} before deleting. PLEASE CHECK ARGUMENTS!!!{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}#############################################################################{bcolors.ENDC}")
        sys.exit()
    if not ("HDD" and "Run") in sys.argv[2] :
        print(f"{bcolors.ERRORBLOCK}###########################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] DAQ data must be copied under {bcolors.BOLD}{bcolors.UNDERLINE}HDD{bcolors.ENDC}{bcolors.ERRORBLOCK} with proper {bcolors.BOLD}{bcolors.UNDERLINE}Run number{bcolors.ENDC}{bcolors.ERRORBLOCK}. PLEASE CHECK ARGUMENTS!!!{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}###########################################################################################{bcolors.ENDC}")
        sys.exit()

    check_if_exists_in_HDD(SSD_DIR, HDD_DIR)

    SSD_FILE_LIST = []
    for SSD_ROOT_DIR, _, SSD_files in os.walk(SSD_DIR) :
        for SSD_file_name in SSD_files :
            SSD_FILE_LIST.append(os.path.join(SSD_ROOT_DIR,SSD_file_name))
    SSD_DATA_LIST = [x for x in SSD_FILE_LIST if not "log" in x]
    SSD_DATA_LIST.sort()

    HDD_FILE_LIST = []
    for HDD_ROOT_DIR, _, HDD_files in os.walk(HDD_DIR) :
        for HDD_file_name in HDD_files :
            HDD_FILE_LIST.append(os.path.join(HDD_ROOT_DIR,HDD_file_name))
    HDD_DATA_LIST = [x for x in HDD_FILE_LIST if not "log" in x]
    HDD_DATA_LIST.sort()

    check_file_size(SSD_DATA_LIST, HDD_DATA_LIST)
    valid_with_checksum_sha256(SSD_DATA_LIST, HDD_DATA_LIST)
    print_meta_data(HDD_DATA_LIST, fraction=0.1)
    action_after_valid(SSD_DIR)