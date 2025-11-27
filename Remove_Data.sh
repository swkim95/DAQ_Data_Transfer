#!/bin/zsh

# DAQ Data Removal Script (SSD cleanup)
# Usage: ./Remove_Data.sh <run_number>
# Example: ./Remove_Data.sh 999

RUN_NUMBER=$1

if [ -z "$RUN_NUMBER" ]; then
    echo "\033[91m[ERROR]\033[0m Run number is required"
    echo "\033[94m[Usage]\033[0m ./Remove_Data.sh <run_number>"
    echo "\033[94m[Example]\033[0m ./Remove_Data.sh 999"
    exit 1
fi

LOG_FILE="./Log/Remove_Log/Log_Run_$RUN_NUMBER.txt"

echo "\033[94m[INFO]\033[0m Log file will be created with path :\033[96m\033[1m $LOG_FILE \033[0m"
python3 remove_data_from_DAQ_PC.py ${RUN_NUMBER} | tee -a ${LOG_FILE} 
