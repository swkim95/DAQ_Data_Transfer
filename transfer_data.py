import sys
import os
import shutil
import subprocess
######################### FILE COPY LOG 만들기!!!!! ##########################

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

def check_storage_usage(storage) :
    total, used, free = shutil.disk_usage(storage)
    storage_usage_bar(total, used, free)

    if ( (used/total) >= 0.8 ) :
        print(f"{bcolors.ERRORBLOCK}###############################################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] Storage used more than {bcolors.BOLD}", round(100*(used/total), 2), f"%{bcolors.ENDC}{bcolors.ERRORBLOCK} of the total space. If not urgent, can't copy the data {bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}###############################################################################################{bcolors.ENDC}")
        urgent = ask_if_sure()
        if not (urgent) : sys.exit()
    elif ( (used/total) >= 0.7 ) :
        print(f"{bcolors.WARNING}##############################################################################################{bcolors.ENDC}")
        print(f"{bcolors.WARNING}[WARNING] Storage used more than {bcolors.BOLD}", round(100*(used/total), 2), f"%{bcolors.ENDC}{bcolors.WARNING} of the total space. If not urgent, please change DST {bcolors.ENDC}")
        print(f"{bcolors.WARNING}#####################$$#######################################################################{bcolors.ENDC}")

    return total, used, free

def storage_usage_bar(total, used, free) :
    total_GB = round(total/1024/1024/1024, 3)
    used_GB = round(used/1024/1024/1024, 3)
    free_GB = round(free/1024/1024/1024, 3)
    progress_bar_length = 50
    num_of_sharp = round(progress_bar_length * (used / total) )
    num_of_bar = (progress_bar_length - num_of_sharp)
    used_percent = round( (100 * (used / total)) , 3 )
    bar_color = bcolors.OKGREEN
    if (used_percent >= 50) : bar_color = bcolors.WARNING
    if (used_percent >= 70) : bar_color = bcolors.ERROR
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC}{bar_color} Storage usage : [" + "#"*num_of_sharp + "-"*num_of_bar+f"]{bcolors.ENDC}", end= ' ')
    print(f"{bar_color}{bcolors.BOLD}%s{bcolors.ENDC}" %( (str(used_percent)+" %")) )
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC}{bar_color}{bcolors.BOLD} Total : %s GB / Used : %s GB / Free : {bcolors.UNDERLINE}%s GB{bcolors.ENDC}" %(total_GB, used_GB, free_GB))

def get_directory_size(dir_path) :
    total = 0
    with os.scandir(dir_path) as dir_iterator :
        for entry in dir_iterator :
            if entry.is_file() :
                total += entry.stat().st_size
            elif entry.is_dir() :
                total += get_directory_size(entry.path)
    return total

def check_transfer_location(SRC_DIR, DST_DIR) :
    compatible = False

    SRC_DIR = os.path.dirname(SRC_DIR)
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking size of SRC data folder : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(SRC_DIR) )
    SRC_folder_size = get_directory_size(SRC_DIR)
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SRC data folder size = {bcolors.OKCYAN}{bcolors.BOLD}%s GB{bcolors.ENDC}" % (round((SRC_folder_size/1024/1024/1024), 3)) )
    storage_dir = os.path.dirname(DST_DIR)
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking DST storage : {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %(storage_dir) )
    DST_total_space, DST_used_space, DST_free_space = check_storage_usage(storage_dir)
    Left_storage_fraction_after_transfer = (DST_free_space - SRC_folder_size) / DST_total_space
    
    if (DST_free_space <= SRC_folder_size) :
        print(f"{bcolors.ERRORBLOCK}############################################################################{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}[ERROR] SRC data folder larger than DST free space, please change to new DST{bcolors.ENDC}")
        print(f"{bcolors.ERRORBLOCK}############################################################################{bcolors.ENDC}")
        sys.exit()
    
    elif( Left_storage_fraction_after_transfer <= 0.2 ) :
        print(f"{bcolors.WARNING}#####################################################################################################{bcolors.ENDC}")
        print(f"{bcolors.WARNING}[WARNING] DST usage exceeds {bcolors.BOLD}", round((100*Left_storage_fraction_after_transfer), 2), f"%{bcolors.ENDC}{bcolors.WARNING} after transferring the SRC folder, BE CAREFUL WHEN TRANSFER!!{bcolors.ENDC}" )
        print(f"{bcolors.WARNING}#####################################################################################################{bcolors.ENDC}")
        urgent = ask_if_sure()
        if (urgent) : compatible = True
        else :
            print(f"{bcolors.ERROR}#######################################################################################################{bcolors.ENDC}")
            print(f"{bcolors.ERROR}[ERROR] DST usage exceeds {bcolors.BOLD}", round((100*Left_storage_fraction_after_transfer), 2), f"%{bcolors.ENDC}{bcolors.ERROR} after transferring the SRC folder, CAN'T TRANSFER IF NOT URGENT!!{bcolors.ENDC}")
            print(f"{bcolors.ERROR}#######################################################################################################{bcolors.ENDC}")
            sys.exit()

    else  : compatible = True
    return compatible

def transfer_data(SRC_DIR, DST_DIR) :
    SRC_BASE_NAME = SRC_DIR.split("/")[-2]
    # copy_folder_name = SRC_BASE_NAME.replace("SSD", "HDD")
    DST_DIR = DST_DIR + SRC_BASE_NAME + "/"
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Copying folder {bcolors.BOLD}{bcolors.OKCYAN}%s{bcolors.ENDC} to {bcolors.BOLD}{bcolors.OKCYAN}%s{bcolors.ENDC}" % (SRC_DIR, DST_DIR))
    #copy_cmd = ("rsync -ahv --progress %s %s" %(SRC_DIR, DST_DIR))
    copy_cmd_org = ("rsync -avh --itemize-changes --log-file=./Log/Copy_Log/rsync_log_%s.txt --progress %s %s" %(SRC_BASE_NAME, SRC_DIR, DST_DIR))
    execute = ask_command_execution(copy_cmd_org)
    # copy_cmd = ["rsync", "-avh", "--itemize-changes", "--log-file=./Log/Copy_Log/rsync_log_%s.txt" %(SRC_BASE_NAME), "--progress", "%s" %(SRC_DIR), "%s" %(DST_DIR)]
    # execute = ask_command_execution(copy_cmd)
    if execute :
        stream = os.popen(copy_cmd_org)
        output = f"{bcolors.CMD}[EXECUTING]{bcolors.ENDC} : " + stream.read()
        print(output)
  
def ask_command_execution(cmd_line) :
    execute = input(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Will you execute command `{bcolors.BOLD}{bcolors.CMD}%s{bcolors.ENDC}`? [y/n] " % cmd_line)
    while( not ( (execute == 'y') or (execute == 'n') ) ) :
        print(f"{bcolors.WARNING}[WARNING]{bcolors.ENDC} Only available options are `{bcolors.OKGREEN}{bcolors.BOLD}y{bcolors.ENDC}` or `{bcolors.OKGREEN}{bcolors.BOLD}n{bcolors.ENDC}`, please check your reply")
        execute = input(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Will you execute command `{bcolors.BOLD}{bcolors.CMD}%s{bcolors.ENDC}`? [y/n] " % cmd_line)
    if ( execute == 'y') :
        return True
    if ( execute == 'n') : 
        print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Execution of command `{bcolors.CMD}{bcolors.BOLD}%s{bcolors.ENDC}` canceled, exiting..." %(cmd_line) )
        sys.exit()

def ask_if_sure() :
    answer = input(f"{bcolors.ERRORBLOCK}{bcolors.BOLD}[CONFIRMATION]{bcolors.ENDC} Trying to take action which is {bcolors.ERROR}{bcolors.BOLD}NOT RECOMMENDED{bcolors.ENDC}. Are you sure? [y/n] ")
    while not ( (answer == 'y') or (answer == 'n') ) :
        print(f"{bcolors.WARNING}[WARNING]{bcolors.ENDC} Only available options are `{bcolors.OKGREEN}{bcolors.BOLD}y{bcolors.ENDC}` or `{bcolors.OKGREEN}{bcolors.BOLD}n{bcolors.ENDC}`, please check your reply")
        answer = input(f"{bcolors.ERRORBLOCK}{bcolors.BOLD}[CONFIRMATION]{bcolors.ENDC} Trying to take action which is {bcolors.ERROR}{bcolors.BOLD}NOT RECOMMENDED{bcolors.ENDC}. Are you sure? [y/n] ")
    if answer == 'y' : return True
    elif answer == 'n' : return False

# def action_after_transfer(SRC_DIR) :
#     new_SRC_DIR = SRC_DIR.replace( SRC_DIR.split('/')[-2], SRC_DIR.split('/')[-2] + "_copied" )
#     print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} SRC folder {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC} will be renamed to {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %( SRC_DIR, new_SRC_DIR ))
#     print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} {bcolors.BOLD}{bcolors.OKGREEN}Transferring the data completed. PLEASE WRITE LOG & PROCEED TO VALIDATION STEP{bcolors.ENDC}")
#     os.rename(SRC_DIR, new_SRC_DIR)

def check_if_proper_step(SRC_DIR) :
    copied = os.path.exists(SRC_DIR + "copied_directory.flag")
    validated = os.path.exists(SRC_DIR + "validated_directory.flag")
    return copied, validated

def action_after_transfer(SRC_DIR) :
    f = open(SRC_DIR + "copied_directory.flag", "w")
    f.close()
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Copy flag will be created under {bcolors.OKCYAN}{bcolors.BOLD}%s{bcolors.ENDC}" %( SRC_DIR ))
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} {bcolors.BOLD}{bcolors.OKGREEN}Transferring the data completed. PLEASE WRITE LOG & PROCEED TO VALIDATION STEP{bcolors.ENDC}")

#############################################################################################################
if __name__ == "__main__" :

    if not len(sys.argv) == 3 : 
        print(f"{bcolors.ERROR} [ERROR] Invalid command line argument. Require 2 arguments to transfer folders to DST {bcolors.ENDC}")
        print(f"{bcolors.INFO} [Usage] {bcolors.ENDC} ./Transfer_Data.sh {bcolors.UNDERLINE}<run_num>{bcolors.ENDC} {bcolors.UNDERLINE}<DST_DIR>{bcolors.ENDC}")
        print(f"{bcolors.INFO} [Example] {bcolors.ENDC}./Transfer_Data.sh 999 /Volumes/DST_16TB_1/")
        sys.exit()
    
    SRC_DIR_PREFIX = "/Users/drc_daq/scratch/Aug2022TB/SRC/SRC_Run_"

    SRC_DIR = SRC_DIR_PREFIX + sys.argv[1]
    DST_DIR = sys.argv[2]

    if not SRC_DIR.endswith("/") : SRC_DIR += "/"
    if not DST_DIR.endswith("/") : DST_DIR += "/"

    if not "Run" in SRC_DIR :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SRC folder is not {bcolors.ERROR}{bcolors.BOLD}Run folder{bcolors.ENDC}, CAN'T TRANSFER")
        sys.exit()

    if not os.path.exists(SRC_DIR) :
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} SRC folder {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (SRC_DIR) )
        sys.exit()
    if not os.path.exists(DST_DIR):
        print(f"{bcolors.ERROR}[ERROR]{bcolors.ENDC} DST folder {bcolors.BOLD}\"%s\"{bcolors.ENDC} {bcolors.ERROR}does not exist{bcolors.ENDC}, please check" % (DST_DIR) )
        sys.exit()

    copied, validated = check_if_proper_step(SRC_DIR)
    if copied or validated :
        print(f"{bcolors.WARNING}#######################################################################################################{bcolors.ENDC}")
        print(f"{bcolors.WARNING}[WARNING] You're trying to copy the SRC folder which may already copied, PLEASE CHECK BEFORE COPY!!!{bcolors.ENDC}")
        print(f"{bcolors.WARNING}#######################################################################################################{bcolors.ENDC}")
        confirmed = ask_if_sure()
        if not confirmed : sys.exit()

    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Transferring SRC folder : {bcolors.BOLD}{bcolors.OKCYAN}%s{bcolors.ENDC} to DST dir : {bcolors.BOLD}{bcolors.OKCYAN}%s{bcolors.ENDC}" %(SRC_DIR, DST_DIR))
    print(f"{bcolors.INFO}[INFO]{bcolors.ENDC} Checking folder size...{bcolors.ENDC}")

    status = check_transfer_location(SRC_DIR, DST_DIR)
    if (status) :
        transfer_data(SRC_DIR, DST_DIR)
        action_after_transfer(SRC_DIR)