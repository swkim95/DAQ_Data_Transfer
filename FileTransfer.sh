#!/bin/zsh

SRC_DIR=$1
DEST_DIR=$2

LAST_CHAR="${SRC_DIR:(-1)}"
if [ ${LAST_CHAR} = "/" ]
then
    RUN_NUM="${SRC_DIR:(-2):1}"
else
    RUN_NUM="${SRC_DIR:(-1)}"
fi

LOG_FILE="./Copy_Log/Log_RUN_$RUN_NUM.txt"
echo $LOG_FILE

python transfer_from_DAQ_PC_to_HDD.py ${SRC_DIR} ${DEST_DIR} | tee -a ${LOG_FILE} 