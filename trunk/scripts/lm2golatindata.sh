#! /bin/bash

#脚本所在路径
scriptDirPath=$(cd "$(dirname "$0")"; pwd)
#echo $scriptDirPath

#if [ $# == 0 ] ; then
#	python ${scriptDirPath}/lm2golatindata.py -h
#	exit 0
#fi

python ${scriptDirPath}/lm2golatindata.py $@
