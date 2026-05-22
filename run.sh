#! /bin/zsh

# Manual primary backup helper: SSD_8TB -> HDD_24TB_6
./Transfer_Data.sh ${1} /Volumes/HDD_24TB_6/
./Valid_Data.sh ${1} /Volumes/HDD_24TB_6/Run_${1}
#./Remove_Data.sh ${1} /Volumes/HDD_24TB_6/Run_${1}
