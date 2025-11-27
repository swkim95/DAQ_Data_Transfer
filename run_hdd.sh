#! /bin/zsh

./Transfer_Data_HDD.sh ${1} /Volumes/HDD_16TB_4/
./Valid_Data_HDD.sh ${1} /Volumes/HDD_16TB_4/Run_${1}
#./Remove_Data.sh ${1} /Volumes/HDD_16TB_3/Run_${1}
