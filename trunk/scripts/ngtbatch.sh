#!/usr/bin/env bash
#source irstlm.config
function usage()
{
    cmnd=$(basename $0);
    cat<<EOF

$cmnd - Corpus -> LM -> ARPA -> Go data

USAGE:
       $cmnd [options]
       -k|--thread             The number of thread 
OPTIONS:
       -c|--corpus             Corpus's path
       -f|--filelist           Filelist (the files in this list must be googleformat)
       -l|--locale             Lanuage locale
       -o|--order              Ngram order, default 2 (bigram)
       -y|--year       	       Only persist ngrams from this year
       -r|--result             Result
       -s|--ngtsd	       NgtSD
       -k|--thread             The number of thread 
       -h|-?|--help            Show this message

       e.g. :
        $cmnd  -f ./filelist -l en -y 1990 -o 1 -c ./googlecorpus

EOF
}

#other
cmnd=$(basename $0)

# some path

TMPDIR=stat_$$
TOOL_SCRIPTS=${IRSTLM}/bin

# some tools
#google_ngram=${TOOL_SCRIPTS}/google-ngram
#ngt=${TOOL_SCRIPTS}/ngt
google_ngram=`which google-ngram 2> /dev/null`;
ngt=`which ngt 2> /dev/null`;
gzip=`which gzip 2> /dev/null`;
gunzip=`which gunzip 2> /dev/null`;

echo IRSTLM=${IRSTLM}
echo google_ngram=${google_ngram}
echo ngt=${ngt}

#default parameters
NAME="" #english
LOCALE=en
ORDER=1
YEAR=1900
FILE=""
CORPUS=.
RESULT=${NAME}.ngt
NGTSD=""
NGTOTHER=""
THREAD=5

while [ "$1" != "" ]; do
    case $1 in
        -c | --corpus )         shift; CORPUS=$1;
                                ;;
        -L | --lanuage )        shift; NAME=$1; 
                                ;;
        -l | --locale )         shift; LOCALE=$1;
                                ;;
        -o | --order )          shift; ORDER=$1;
                                ;;
	-y | --year )    	shift; YEAR=$1;
				;;
	-r | --result )    	shift; RESULT=$1;
				;;
	-s | --ngtsd )    	shift; NGTSD=$1;
				;;
        -k | --thread )    	shift; THREAD=$1;
                                ;;
        -h | -? | --help )      usage;
                                exit 0;
                                ;;
        * )                     usage;
                                exit 1;
    esac
    shift
done


# config ngt sd
if [ -z "$NGTSD" ] ;
then
	echo "ngt work without sd";	
#	echo NGTOTHER=$NGTOTHER;
else
	echo "ngt work with sd : ${NGTSD}"
	NGTOTHER="-sd=${NGTSD} "
#	echo NGTOTHER=$NGTOTHER;
fi


#check tools
gzip=`which gzip 2> /dev/null`;
python=`which pypy 2> /dev/null`;
if [ -z "$python" ];
then
    echo "Pypy is faster than Python, suggest installing pypy !"
    python=`which python 2> /dev/null`;
fi

#check tmpdir
if [ ! -d $TMPDIR ]; then
   echo "Temporary directory $TMPDIR does not exist";
   echo "creating $TMPDIR";
   mkdir -p $TMPDIR;
fi

#generate file list
dir ${CORPUS} | grep ${ORDER}gram > ./$TMPDIR/${ORDER}gram.list &&


#for each file in list : google-ngram --> ngt
i=1;
while read -a ARRAY
do
	name=${ARRAY[@]};
	echo dealing with ${name};
	len=${#name};
	newnameing=${name:0:(${len}-3)}.ngram.ing;
	newnameprengt=${name:0:(${len}-3)}.prengt.gz;
	newnamengt=${name:0:(${len}-3)}.ngt.gz
	(
	 echo ${python} ${google_ngram} -l ${LOCALE} -n ${ORDER} -c 0,2,1 -y ${YEAR} -i "$gunzip -c ${CORPUS}/${ARRAY[@]}"  -o "$gzip -c > ./$TMPDIR/${newnameing}"  &&
	 ${python} ${google_ngram} -l ${LOCALE} -n ${ORDER} -c 0,2,1 -y ${YEAR} -i "$gunzip -c ${CORPUS}/${ARRAY[@]}"  -o "$gzip -c > ./$TMPDIR/${newnameing}"  &&
	 mv ./$TMPDIR/${newnameing} ./$TMPDIR/${newnameprengt} &&
	 ${ngt}  -gooinp=y -i="$gunzip -c ./$TMPDIR/${newnameprengt} " -n=${ORDER} $NGTOTHER -gooout=y -o="$gzip -c > ./$TMPDIR/${newnamengt} " &&
	echo ${name} finish!
	)&

	let i+=1;
	if [ $i -gt $THREAD ]; then
		wait;
		i=1;
	fi
done < $TMPDIR/${ORDER}gram.list

# Wait for all parallel jobs to finish
wait

# generate all sub ngt to one  
$gunzip -c $TMPDIR/*-${ORDER}gram-*.ngt.gz  | $gzip -c >  ./$TMPDIR/${ORDER}gram.total.ngt.gz

${ngt}  -gooinp=y -i="$gunzip -c ./$TMPDIR/${ORDER}gram.total.ngt.gz" -n=${ORDER} $NGTOTHER -gooout=y -o="$gzip -c >  ${RESULT} "

echo =========================================================== 
echo   $cmnd  finish! 
echo ===========================================================
