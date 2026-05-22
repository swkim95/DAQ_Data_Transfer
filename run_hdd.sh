#! /bin/zsh

# Manual secondary backup helper: HDD_24TB_6 -> HDD_16TB_4
./Transfer_Data_HDD.sh ${1} /Volumes/HDD_16TB_4/
./Valid_Data_HDD.sh ${1} /Volumes/HDD_16TB_4/Run_${1}
#./Remove_Data.sh ${1} /Volumes/HDD_24TB_6/Run_${1}
