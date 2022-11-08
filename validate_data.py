import os
import sys
import hashlib
import random
from transfer_data import check_if_proper_step

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

def get_data_dir(SRC_DIR, DST_DIR) :
    SRC_FILE_LIST = []
    for SRC_ROOT_DIR, _, SRC_files in os.walk(SRC_DIR) :
        for SRC_file_name in SRC_files :
            SRC_FILE_LIST.append(os.path.join(SRC_ROOT_DIR,SRC_file_name))
    # SRC_DATA_LIST = [x for x in SRC_FILE_LIST if not "log" in x and not "png" in x and not "root" in x]
    SRC_DATA_LIST = [x for x in SRC_FILE_LIST if ".dat" in x]
    SRC_DATA_LIST.sort()

    DST_FILE_LIST = []
    for DST_ROOT_DIR, _, DST_files in os.walk(DST_DIR) :
        for DST_file_name in DST_files :
            DST_FILE_LIST.append(os.path.join(DST_ROOT_DIR,DST_file_name))
    # DST_DATA_LIST = [x for x in DST_FILE_LIST if not "log" in x and not "png" in x and not "root" in x]
    DST_DATA_LIST = [x for x in DST_FILE_LIST if ".dat" in x]
    DST_DATA_LIST.sort()

    return SRC_DATA_LIST, DST_DATA_LIST

def cksum_sha256(file_name) :
    sha256 = hashlib.sha256()
    with open(file_name, 'rb') as f :
        for chunk in iter(lambda: f.read(65536), b"") :
            sha256.update(chunk)
    return sha256.hexdigest()

def valid_with_checksum_sha256(SRC_SORTED_DIR, DST_SORTED_DIR) :
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Comparing SHA256 checksum values for SRC & DST files...")
    for idx, (src_file, dst_file) in enumerate(zip(SRC_SORTED_DIR, DST_SORTED_DIR)) :
        sha256_src_file = cksum_sha256(src_file)
        sha256_dst_file = cksum_sha256(dst_file)
        if not (sha256_src_file == sha256_dst_file) :
            print(f"{bcolors.ERRORBLOCK}[ERROR]{bcolors.ENDC} SHA256 checksum failed!!!")
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SHA256 checksum of SRC file : {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} and DST file {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} does not match. PLEASE CHECK!!" %(src_file, dst_file) )
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SHA256 decimal checksum of SRC file {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} : {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(src_file, int(sha256_src_file, base=16)))
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SHA256 decimal checksum of DST file {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} : {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(dst_file, int(sha256_dst_file, base=16)))
            sys.exit()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SHA256 checksum compare {bcolors.OKGREEN}{bcolors.BOLD}successful!{bcolors.ENDC} Proceeding...")

def check_entry(SRC_SORTED_DIR, DST_SORTED_DIR) :
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking number of events stored in SRC & DST files...")
    for idx, (src_file, dst_file) in enumerate(zip(SRC_SORTED_DIR, DST_SORTED_DIR)) :
        src_file_size = os.stat(src_file).st_size
        dst_file_size = os.stat(dst_file).st_size
        base_size = 65536
        if ( (src_file_size == 0) and (dst_file_size == 0) ) : continue
        if "Fast" in src_file : base_size = 256
        if not ( ( (src_file_size%base_size) == 0) or ( (dst_file_size%base_size) == 0) ) :
            print(f"{bcolors.ERRORBLOCK}[ERROR]{bcolors.ENDC} Event number check failed!!!")
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Some file does not contain proper number of evt. Please check")
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} # of event in SRC file : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC} == {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(src_file, (src_file_size//base_size)))
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} # of event in DST file : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC} == {bcolors.ERROR}{bcolors.BOLD}%s{bcolors.ENDC}" %(dst_file, (dst_file_size//base_size)))
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
    ltmp = int(bin(ltmp << 8), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[14].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 16), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[15].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 24), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[16].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 32), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[17].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 40), base=2)
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

    ## local trigger pattern
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
    ltmp = int(bin(ltmp << 8), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[30].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 16), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[31].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 24), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[32].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 32), base=2)
    coarse_time = coarse_time + ltmp
    ltmp = int(bin(int(meta_data_bits[33].hex(), base=16) & 0b11111111), base=2)
    ltmp = int(bin(ltmp << 40), base=2)
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

def print_meta_data(DST_SORTED_DIR, fraction=0.1, metadata_size=64) :
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Printing out random file's metadata...", end="\n\n")
    total_number_of_files = len(DST_SORTED_DIR)
    files_to_investigate = int(total_number_of_files * fraction) if total_number_of_files >= 10 else total_number_of_files
    file_num_list = random.sample(DST_SORTED_DIR, files_to_investigate)
    for dst_file in file_num_list :
        meta_data_bits = []
        dst_file_size = os.stat(dst_file).st_size
        if dst_file_size == 0 : continue
        base_size = 65536 if "Wave" in dst_file else 256
        evt_number = (dst_file_size//base_size)
        random_evt_num = random.randint(0, evt_number-1)
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking metadata of DST file : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(dst_file))
        with open(dst_file, "rb") as f :
            f.seek(random_evt_num * base_size)
            for i in range(metadata_size) :
                meta_data_bits.append(f.read(1))
        meta_data = decode_meta_data(meta_data_bits)
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Data Length = %s, Run # = %s, MID = %s" %(meta_data[0], meta_data[1], meta_data[5]))
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Trigger type = %x, Local trigger pattern = %x" %(meta_data[2], meta_data[7]))
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} TCB trigger # = %s, Local trigger # = %s" %(meta_data[3], meta_data[6]))
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} TCB trigger time = %s, Local trigger time = %s, difference = %s" %(meta_data[4], meta_data[8], meta_data[9]), end="\n\n")
    confirmed = ask_if_sure()
    if not confirmed : sys.exit()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Metadata check all clear. Proceeding...")

def compare_meta_data(DST_SORTED_DIR, SRC_SORTED_DIR, metadata_size=64) :
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Comparing DST & SRC file's metadata...")
    for dst_file, src_file in zip(DST_SORTED_DIR, SRC_SORTED_DIR) :
        dst_first_meta_data_bits = []
        dst_last_meta_data_bits  = []
        src_first_meta_data_bits = []
        src_last_meta_data_bits  = []
        dst_file_size = os.stat(dst_file).st_size
        src_file_size = os.stat(src_file).st_size
        if dst_file_size == 0 : continue
        base_size = 65536 if "Wave" in dst_file else 256
        evt_number = (dst_file_size//base_size)
        with open(dst_file, "rb") as f :
            for i in range(metadata_size) :
                dst_first_meta_data_bits.append(f.read(1))
        with open(src_file, "rb") as f :
            for i in range(metadata_size) :
                src_first_meta_data_bits.append(f.read(1))
        dst_first_meta_data = decode_meta_data(dst_first_meta_data_bits)
        src_first_meta_data = decode_meta_data(src_first_meta_data_bits)
        with open(dst_file, "rb") as f :
            f.seek((evt_number-1) * base_size)
            for i in range(metadata_size) :
                dst_last_meta_data_bits.append(f.read(1))
        with open(src_file, "rb") as f :
            f.seek((evt_number-1) * base_size)
            for i in range(metadata_size) :
                src_last_meta_data_bits.append(f.read(1))
        dst_last_meta_data = decode_meta_data(dst_last_meta_data_bits)
        src_last_meta_data = decode_meta_data(src_last_meta_data_bits)
        if not ( (dst_first_meta_data == src_first_meta_data) ) :
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Mismatch in DST and SRC 1st event's metadata, please check")
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} DST file : %s" %(dst_file))
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SRC file : %s" %(src_file))
            sys.exit()
        if not ( (dst_last_meta_data == src_last_meta_data) ) :
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Mismatch in DST and SRC last event's metadata, please check")
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} DST file : %s" %(dst_file))
            print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SRC file : %s" %(src_file))
            sys.exit()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Metadata check {bcolors.OKGREEN}{bcolors.BOLD}successful!{bcolors.ENDC}. Proceeding...")

def ask_if_sure() :
    answer = input(f"{bcolors.ERRORBLOCK}{bcolors.BOLD}[CONFIRMATION]{bcolors.ENDC} Are you sure the meta data is correct? [y/n] ")
    while not ( (answer == 'y') or (answer == 'n') ) :
        print(f"{bcolors.WARNING}[WARNING]{bcolors.ENDC} Only available options are `{bcolors.OKGREEN}{bcolors.BOLD}y{bcolors.ENDC}` or `{bcolors.OKGREEN}{bcolors.BOLD}n{bcolors.ENDC}`, please check your reply")
        answer = input(f"{bcolors.ERRORBLOCK}{bcolors.BOLD}[CONFIRMATION]{bcolors.ENDC} Are you sure the meta data is correct? [y/n] ")
    if answer == 'y' : return True
    elif answer == 'n' : return False

def check_if_exists_in_DST(SRC_DIR, DST_DIR) :
    SRC_BASE_DIR = SRC_DIR.split('/')[-2]
    SRC_RUN_NUM = SRC_BASE_DIR.split('_')[-2]

    DST_BASE_DIR = DST_DIR.split('/')[-2]
    DST_RUN_NUM = DST_BASE_DIR.split('_')[-1]

    if not (SRC_RUN_NUM == DST_RUN_NUM) :
        print(f"{bcolors.ERRORBLOCK}###############################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] The {bcolors.BOLD}{bcolors.UNDERLINE}RUN NUMBER{bcolors.ENDC}{bcolors.ERRORBLOCK} of both DAQ DATA and DST DATA {bcolors.BOLD}{bcolors.UNDERLINE}MUST BE MATCHED{bcolors.ENDC}{bcolors.ERRORBLOCK}. PLEASE CHECK ARGUMENTS!!!{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}###############################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Your DAQ PC data run number : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}   Your DST data run number : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(SRC_RUN_NUM, DST_RUN_NUM) )
        sys.exit()

    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking if SRC directory properly copied to DST")
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking SRC directory : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(SRC_DIR))
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking DST directory : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(DST_DIR))

    SRC_FILE_LIST = []
    for _, _, SRC_files in os.walk(SRC_DIR) :
        for SRC_file_name in SRC_files :
            SRC_FILE_LIST.append(SRC_file_name)
    SRC_FILE_LIST.sort()
    SRC_DATA_SIZE = get_directory_size(SRC_DIR)

    DST_FILE_LIST = []
    for _, _, DST_files in os.walk(DST_DIR) :
        for DST_file_name in DST_files :
            DST_FILE_LIST.append(DST_file_name)
    DST_FILE_LIST.sort()
    DST_DATA_SIZE = get_directory_size(DST_DIR)

    if not (SRC_DATA_SIZE == DST_DATA_SIZE) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Data size in SRC and DST mismatch. Please check!")
        print(f"Data size in SRC : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} (Bytes) in DST : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} (Bytes)" %(SRC_DATA_SIZE, DST_DATA_SIZE))
        sys.exit()
    for idx, (src_file, dst_file) in enumerate(zip(SRC_FILE_LIST, DST_FILE_LIST)) :
        try : 
            if not (SRC_FILE_LIST[idx] == DST_FILE_LIST[idx]) :
                print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Mismatch between SRC file list & DST file list. Please check!")
                print(f"Length of SRC file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(SRC_FILE_LIST)) )
                print(f"Length of DST file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(DST_FILE_LIST)) )
                print(f"Content of SRC file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, src_file))
                print(f"Content of DST file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, dst_file))
                sys.exit()
        except IndexError as e :
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Mismatch between SRC file list & DST file list. Please check!")
            print(f"Length of SRC file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(SRC_FILE_LIST)) )
            print(f"Length of DST file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(DST_FILE_LIST)) )
            if ( (idx + 1) == len(SRC_FILE_LIST)) : print(f"Content of SRC file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, src_file))
            if ( (idx + 1) == len(DST_FILE_LIST)) : print(f"Content of DST file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, dst_file))
            sys.exit()
            
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} File list & size check between SRC folder and DST folder {bcolors.OKGREEN}{bcolors.BOLD}successful!{bcolors.ENDC} Proceeding...")`

def action_after_valid(SRC_DIR) :
    f = open(SRC_DIR + "validated_directory.flag", "w")
    f.close()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Validate flag will be created under {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %( SRC_DIR ))
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} {bcolors.BOLD}{bcolors.OKGREEN}Validation of the data completed. PLEASE WRITE LOG & PROCEED TO REMOVE STEP{bcolors.ENDC}")
#############################################################################################################
if __name__ == "__main__" :

    if not len(sys.argv) == 3 : 
        print(f"{bcolors.ERROR}[ERROR] Invalid command line argument. Require 2 arguments to validate copied data {bcolors.ENDC}")
        print(f"{bcolors.INFO}[Usage]{bcolors.ENDC} ./Valid_Data.sh {bcolors.UNDERLINE}<run_num>{bcolors.ENDC} {bcolors.UNDERLINE}<destination_path>{bcolors.ENDC}")
        print(f"{bcolors.INFO}[Example]{bcolors.ENDC} ./Valid_Data.sh  999 /Volumes/HDD_16TB_1/HDD_Run_999/")
        sys.exit()
    
    SRC_DIR_PREFIX = "/Users/drc_daq/scratch/Aug2022TB/SSD/Run_"

    # SRC_DIR will be "/Path/to/DAQPC/data/dir/Run_X"
    SRC_DIR = SRC_DIR_PREFIX + sys.argv[1]
    DST_DIR = sys.argv[2]

    if not SRC_DIR.endswith("/") : SRC_DIR += "/"
    if not DST_DIR.endswith("/") : DST_DIR += "/"

    if not os.path.exists(SRC_DIR) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Original SRC data with path {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (SRC_DIR) )
        sys.exit()
    if not os.path.exists(DST_DIR) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Copied DST data with path {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (DST_DIR) )
        sys.exit()
    
    ## Check if the data in DAQ PC is already copied by checking copy flag file
    copied, validated = check_if_proper_step(SRC_DIR)
    if not copied :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SRC directory not yet copied, please check!")
        sys.exit()
    if validated :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SRC directory already validated, please check!")
        sys.exit()
        
    check_if_exists_in_DST(SRC_DIR, DST_DIR)
    SRC_DATA_LIST, DST_DATA_LIST = get_data_dir(SRC_DIR, DST_DIR)
    check_entry(SRC_DATA_LIST, DST_DATA_LIST)
    valid_with_checksum_sha256(SRC_DATA_LIST, DST_DATA_LIST)
    #print_meta_data(DST_DATA_LIST, fraction=0.1)
    compare_meta_data(SRC_DATA_LIST, DST_DATA_LIST)
    action_after_valid(SRC_DIR)