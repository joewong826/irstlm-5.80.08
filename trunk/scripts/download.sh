#!/bin/bash

cmnd=$(basename $0)

function usage()
{
    cmnd=$(basename $0);
    cat<<EOF

$cmnd- this tool is used to download multiple files, specially,
       download all files in addresslist to localfolder.
USAGE:
       $cmnd [options]

OPTIONS:
       -a|--addresslist        addresslist
       -l|--localfolder        All files will download to this localfolder
       -k|--thread             The number of thread 
       -h|-?|--help            Show this message

       eg :
        $cmnd -a addresslist.txt -f localfolder

EOF
}


#
ADDRESSLIST=
LOCALFOLDER=.
THREAD=5
#
while [ "$1" != "" ]; do
    case $1 in
        -a | --addresslist )    shift; ADDRESSLIST=$1;
                                ;;
        -l | --localfolder )    shift; LOCALFOLDER=$1;
                                ;;
        -k | --thread )    	shift; THREAD=$1;
                                ;;
        -h | -? | --help )      usage;
                                exit 0;
                                ;;
        * ) 			echo "ERR input";
	                        usage;
                                exit 1;
    esac
    shift
done


#check addresslist
if [ !  $ADDRESSLIST   ]; then
	echo "ERR: no addresslist!";
	usage;
     	exit 1;
fi

#check addresslist
if [ ! -f $ADDRESSLIST ]; then
	echo "ERR: no file: $ADDRESSLIST ";
	usage;
     	exit 1;
fi


#check localfolder
if [ ! -d $LOCALFOLDER ]; then
   echo "Temporary directory $LOCALFOLDER does not exist";
   echo "creating $LOCALFOLDER";
   mkdir -p $LOCALFOLDER;
fi

i=1;
while read -a ARRAY
do
#	echo i=$i
#	echo filename=$filename
	fileadd=${ARRAY[@]}
	filename=$(echo ${fileadd##*/})
	(
	wget   -c -P $LOCALFOLDER -O $LOCALFOLDER/${filename}.ing ${ARRAY[@]}  &&
	mv $LOCALFOLDER/${filename}.ing $LOCALFOLDER/${filename}&&
	echo  "$filename finish!"
	)&

	let i+=1;
	if [ $i -gt $THREAD ]; then
		wait;
		i=1;
	fi


done < $ADDRESSLIST

#
wait

#
echo =====================
echo   $cmnd  finish! 
echo =====================
