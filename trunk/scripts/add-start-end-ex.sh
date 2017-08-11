#! /bin/bash

#脚本所在路径
scriptDirPath=$(cd "$(dirname "$0")"; pwd)
#echo $scriptDirPath

#if [ $# == 0 ] ; then
#	python ${scriptDirPath}/add_start_end.py -h
#	exit 0
#fi

python ${scriptDirPath}/add_start_end.py $@
