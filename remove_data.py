import os
import sys
import shutil
from transfer_data import ask_if_sure, storage_usage_bar, check_if_proper_step
from validate_data import check_if_exists_in_DST

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

def remove_folder(SRC_DIR) :
    print(f"{bcolors.WARNING}[DELETING]{bcolors.ENDC} Are you sure you want to remove folder : {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}?" %(SRC_DIR))
    sure = ask_if_sure()
    if not sure :
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} User canceled the deletion of DAQ PC folder. Exiting...")
        sys.exit()
    else :
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Deleting directory {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC}" %(SRC_DIR))
        try : 
            shutil.rmtree(SRC_DIR)
        except OSError as e :
            print(e)
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Directory {bcolors.OKCYAN}{bcolors.BOLD}{bcolors.UNDERLINE}%s{bcolors.ENDC} deleted successfully." %(SRC_DIR))
    
if __name__ == "__main__" :

    SRC_DIR_PREFIX = "/Users/swkim/DRC/2022_TB_at_CERN/DAQ_data_transfer_for_Kor_TB/Run_"

    if not len(sys.argv) == 3 :
        print(f"{bcolors.ERROR} [ERROR] {bcolors.ENDC}Need {bcolors.BOLD}{bcolors.UNDERLINE}{bcolors.ERROR}2 arguments{bcolors.ENDC} to remove data from DAQ PC, please check your arguments")
        print(f"{bcolors.INFO} [Usage] {bcolors.ENDC} ./Remove_Data.sh {bcolors.UNDERLINE}<run_num>{bcolors.ENDC} {bcolors.UNDERLINE}<destination_path>{bcolors.ENDC}")
        print(f"{bcolors.INFO} [Example] {bcolors.ENDC}./Remove_Data.sh 999 /Volumes/DST_16TB_1/DST_Run_999/")
        sys.exit()
    
    SRC_DIR = SRC_DIR_PREFIX + sys.argv[1]
    DST_DIR = sys.argv[2]

    if not SRC_DIR.endswith('/'): SRC_DIR += '/'
    if not DST_DIR.endswith('/'): DST_DIR += '/'

    if not os.path.exists(SRC_DIR) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Original SRC data with path {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (SRC_DIR) )
        sys.exit()
    if not os.path.exists(DST_DIR) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} Copied DST data with path {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (DST_DIR) )
        sys.exit()

    copied , validated = check_if_proper_step(SRC_DIR)
    if not copied :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SRC directory not yet copied, please check!")
        sys.exit()
    if not validated :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SRC directory not yet validated, please check!")
        sys.exit()

    check_if_exists_in_DST(SRC_DIR, DST_DIR)

    print(f"{bcolors.WARNING}############################################################################{bcolors.ENDC}")
    print(f"{bcolors.WARNING}[WARNING] You're trying to {bcolors.BOLD}{bcolors.UNDERLINE}remove the DATA{bcolors.ENDC}{bcolors.WARNING} from DAQ PC. PLEASE BE CAREFUL!!!{bcolors.ENDC}")
    print(f"{bcolors.WARNING}############################################################################{bcolors.ENDC}")

    remove_folder(SRC_DIR)

    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking SRC storage usage...")
    total, used, free = shutil.disk_usage("/Users/swkim")
    storage_usage_bar(total, used, free)