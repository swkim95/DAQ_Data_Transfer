#!/bin/zsh

# DAQ Data Transfer Script (SSD to HDD)
# Usage: ./Transfer_Data.sh <run_number> [destination_path]
# Example: ./Transfer_Data.sh 999
# Example: ./Transfer_Data.sh 999 /Volumes/HDD_16TB_1/

RUN_NUMBER=$1
DEST_DIR=$2

if [ -z "$RUN_NUMBER" ]; then
    echo "\033[91m[ERROR]\033[0m Run number is required"
    echo "\033[94m[Usage]\033[0m ./Transfer_Data.sh <run_number> [destination_path]"
    echo "\033[94m[Example]\033[0m ./Transfer_Data.sh 999"
    exit 1
fi

LOG_FILE="./Log/Copy_Log/Log_Run_$RUN_NUMBER.txt"

echo "\033[94m[INFO]\033[0m Log file will be created with path :\033[96m\033[1m $LOG_FILE \033[0m"

# Check if running from automation (no logging interference)
if [ "$DAQ_AUTOMATION" = "true" ]; then
    # Direct execution for automation - preserves progress bars
    if [ -n "$DEST_DIR" ]; then
        python3 transfer_from_DAQ_PC_to_HDD.py ${RUN_NUMBER} ${DEST_DIR}
    else
        python3 transfer_from_DAQ_PC_to_HDD.py ${RUN_NUMBER}
    fi
else
    # Manual execution with logging
    if [ -n "$DEST_DIR" ]; then
        python3 transfer_from_DAQ_PC_to_HDD.py ${RUN_NUMBER} ${DEST_DIR} | tee -a ${LOG_FILE}
    else
        python3 transfer_from_DAQ_PC_to_HDD.py ${RUN_NUMBER} | tee -a ${LOG_FILE}
    fi
fi 
