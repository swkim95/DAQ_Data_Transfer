#!/bin/zsh

# DAQ Data Validation Script (HDD ↔ HDD)
# Usage: ./Valid_Data_HDD.sh <run_number>
# Example: ./Valid_Data_HDD.sh 999

RUN_NUMBER=$1

if [ -z "$RUN_NUMBER" ]; then
    echo "\033[91m[ERROR]\033[0m Run number is required"
    echo "\033[94m[Usage]\033[0m ./Valid_Data_HDD.sh <run_number>"
    echo "\033[94m[Example]\033[0m ./Valid_Data_HDD.sh 999"
    exit 1
fi

LOG_FILE="./Log_HDD/Valid_Log/Log_Run_$RUN_NUMBER.txt"

echo "\033[94m[INFO]\033[0m Log file will be created with path :\033[96m\033[1m $LOG_FILE \033[0m"

# Check if running from automation (no logging interference)
if [ "$DAQ_AUTOMATION" = "true" ]; then
    # Direct execution for automation - preserves progress bars
    python3 validate_data_HDD.py ${RUN_NUMBER}
else
    # Manual execution with logging
    python3 validate_data_HDD.py ${RUN_NUMBER} | tee -a ${LOG_FILE}
fi 
