#!/bin/zsh

SRC_DIR=$1
DEST_DIR=$2

SRC_BASENAME=$(echo $SRC_DIR | awk -F/ '{print $NF}')

LOG_FILE="./Log/Copy_Log_HDD_to_HDD/Log_$SRC_BASENAME.txt"

echo "\033[94m[INFO]\033[0m Log file will be created with path :\033[96m\033[1m $LOG_FILE \033[0m"
python transfer_from_HDD_to_HDD.py ${SRC_DIR} ${DEST_DIR} | tee -a ${LOG_FILE} 