import os
import sys
from glob import glob
import shutil
from transfer_from_DAQ_PC_to_HDD import get_directory_size, ask_if_sure

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

def check_if_exists_in_HDD(SSD_DIR, HDD_DIR) :
    SSD_BASE_DIR = SSD_DIR.split('/')[-2]
    SSD_RUN_NUM = SSD_BASE_DIR.split('_')[-2]

    HDD_BASE_DIR = HDD_DIR.split('/')[-2]
    HDD_RUN_NUM = HDD_BASE_DIR.split('_')[-1]

    if not (SSD_RUN_NUM == HDD_RUN_NUM) :
        print(f"{bcolors.ERRORBLOCK}###############################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] The {bcolors.BOLD}{bcolors.UNDERLINE}RUN NUMBER{bcolors.ENDC}{bcolors.ERRORBLOCK} of both DAQ DATA and HDD DATA {bcolors.BOLD}{bcolors.UNDERLINE}MUST BE MATCHED{bcolors.ENDC}{bcolors.ERRORBLOCK}. PLEASE CHECK ARGUMENTS!!!{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}###############################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Your DAQ PC data run number : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}   Your HDD data run number : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(SSD_RUN_NUM, HDD_RUN_NUM) )
        sys.exit()

    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking if SSD directory properly copied to HDD before removing...")
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking SSD directory : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(SSD_DIR))
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking HDD directory : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(HDD_DIR))

    SSD_FILE_LIST = []
    for _, _, SSD_files in os.walk(SSD_DIR) :
        for SSD_file_name in SSD_files :
            SSD_FILE_LIST.append(SSD_file_name)
    SSD_FILE_LIST.sort()
    SSD_DATA_SIZE = get_directory_size(SSD_DIR)

    HDD_FILE_LIST = []
    for _, _, HDD_files in os.walk(HDD_DIR) :
        for HDD_file_name in HDD_files :
            HDD_FILE_LIST.append(HDD_file_name)
    HDD_FILE_LIST.sort()
    HDD_DATA_SIZE = get_directory_size(HDD_DIR)

    if not (SSD_DATA_SIZE == HDD_DATA_SIZE) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Data size in SSD and HDD mismatch. Please check!")
        print(f"Data size in SSD : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} (Bytes) in HDD : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} (Bytes)" %(SSD_DATA_SIZE, HDD_DATA_SIZE))
        sys.exit()
    for idx, (ssd_file, hdd_file) in enumerate(zip(SSD_FILE_LIST, HDD_FILE_LIST)) :
        try : 
            if not (SSD_FILE_LIST[idx] == HDD_FILE_LIST[idx]) :
                print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Mismatch between SSD file list & HDD file list. Please check!")
                print(f"Length of SSD file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(SSD_FILE_LIST)) )
                print(f"Length of HDD file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(HDD_FILE_LIST)) )
                print(f"Content of SSD file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, ssd_file))
                print(f"Content of HDD file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, hdd_file))
                sys.exit()
        except IndexError as e :
            print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Mismatch between SSD file list & HDD file list. Please check!")
            print(f"Length of SSD file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(SSD_FILE_LIST)) )
            print(f"Length of HDD file list : {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} " %(len(HDD_FILE_LIST)) )
            if ( (idx + 1) == len(SSD_FILE_LIST)) : print(f"Content of SSD file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, ssd_file))
            if ( (idx + 1) == len(HDD_FILE_LIST)) : print(f"Content of HDD file list with Index {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} = {bcolors.ERROR}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(idx, hdd_file))
            sys.exit()

    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} File list & size check between SSD folder and HDD folder {bcolors.OKGREEN}{bcolors.BOLD}successful!{bcolors.ENDC} Proceeding...")


def remove_folder(SSD_DIR) :
    print(f"{bcolors.WARNING}[DELETING]{bcolors.ENDC} Are you sure you want to remove folder : {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}?" %(SSD_DIR))
    sure = ask_if_sure()
    if not sure :
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} User canceled the deletion of DAQ PC folder. Exiting...")
        sys.exit()
    else :
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Deleting directory {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(SSD_DIR))
        try : 
            shutil.rmtree(SSD_DIR)
        except OSError as e :
            print(e)
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Directory {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} deleted successfully." %(SSD_DIR))

if __name__ == "__main__" :

    if not len(sys.argv) == 3 :
        print(f"{bcolors.ERROR} [ERROR] {bcolors.ENDC}Need {bcolors.BOLD}{bcolors.UNDERLINE}{bcolors.ERROR}2 arguments{bcolors.ENDC} to remove data from DAQ PC, please check your arguments")
        print(f"{bcolors.INFO} [Usage] {bcolors.ENDC} ./Remove_Data.sh {bcolors.UNDERLINE}<source_path>{bcolors.ENDC} {bcolors.UNDERLINE}<destination_path>{bcolors.ENDC}")
        print(f"{bcolors.INFO} [Example] {bcolors.ENDC}./Remove_Data.sh ~/scratch/202208TB/SSD/SSD_Run_999/ /Volumes/HDD_16TB_1/HDD_Run_999/")
        sys.exit()
    
    SSD_DIR = sys.argv[1]
    HDD_DIR = sys.argv[2]

    if not SSD_DIR.endswith('/'): SSD_DIR += '/'
    if not HDD_DIR.endswith('/'): HDD_DIR += '/'

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
    if not ("_validated") in sys.argv[1] :
        print(f"{bcolors.ERRORBLOCK}#############################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] DAQ data must be {bcolors.BOLD}{bcolors.UNDERLINE}VALIDATED{bcolors.ENDC}{bcolors.ERRORBLOCK} before deleting. PLEASE CHECK ARGUMENTS!!!{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}#############################################################################{bcolors.ENDC}")
        sys.exit()
    if not ("HDD" and "Run") in sys.argv[2] :
        print(f"{bcolors.ERRORBLOCK}###########################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] DAQ data must be copied under {bcolors.BOLD}{bcolors.UNDERLINE}HDD{bcolors.ENDC}{bcolors.ERRORBLOCK} with proper {bcolors.BOLD}{bcolors.UNDERLINE}Run number{bcolors.ENDC}{bcolors.ERRORBLOCK}. PLEASE CHECK ARGUMENTS!!!{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}###########################################################################################{bcolors.ENDC}")
        sys.exit()

    check_if_exists_in_HDD(SSD_DIR, HDD_DIR)

    print(f"{bcolors.WARNING}############################################################################{bcolors.ENDC}")
    print(f"{bcolors.WARNING}[WARNING] You're trying to {bcolors.BOLD}{bcolors.UNDERLINE}remove the DATA{bcolors.ENDC}{bcolors.WARNING} from DAQ PC. PLEASE BE CAREFUL!!!{bcolors.ENDC}")
    print(f"{bcolors.WARNING}############################################################################{bcolors.ENDC}")

    remove_folder(SSD_DIR)