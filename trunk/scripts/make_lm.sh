#!/usr/bin/env bash

#需要先设置IRSTLM的安装目录
if [ ! $IRSTLM ]; then
   echo -e "Set IRSTLM environment variable with path to irstlm. default: export IRSTLM=/opt/irstlm"
   export IRSTLM=/opt/irstlm
fi

#check irstlm installation
if [ ! -e $IRSTLM/bin/dict -o  ! -e $IRSTLM/bin/split-dict.pl ]; then
   echo "$IRSTLM does not contain a proper installation of IRSTLM"
   exit 3
fi


function usage()
{
    cmnd=$(basename $0);
    cat<<EOF

$cmnd - Corpus -> LM -> ARPA -> Go data

USAGE:
       $cmnd [options]

OPTIONS:
       -a|--addStartEnd        first step: run add start end, add <s></s>
       -d|--dict               second step: run dict, generate word count.
       -b|--buildIm            Third step: run build im..generate *.im.gz
       -p|--prune              Four step: run prune im. generate *.plm,*qlm,*_go.txt

       -c|--corpusPath         Input Corpus, or Corpus dirs
       -L|--lanuage            Lanuage
       -l|--locale             Lanuage locale
       -v|--dataversion        Data version, default 1
       -o|--order              ngram order, default 2 (bigram)
       -u|--unigramCount       Unigram word count, default 1000000000
       -w|--wordMaxLen         Word max len, default 30
       -t|--pruneThreshold     Pruning frequency threshold for each level; comma-separated list of values; (default is '0,0,...,0', for all levels)
       -W|--wordlist           Base dictionary for add-start-end
       
          --shortcut           shortcut file path
          --offensive          offensive file path
          --keepOffensiveFreq  keep offensive freq, default f=0

       -h|-?|--help            Show this message

       e.g. :
        ./make_lm.sh -a -d -b -p -c english.txt -L english -l en -v 100 -o 2 -u 100000 -w 32 -t 1e-07
        ./make_lm.sh -a -d -b -p -L english -l en -v 100 -o 2 -u 100000 -w 32 -t 1e-07
        ./make_lm.sh -a -d -b -p -L english -l en -v 100 -u 100000 -t 1e-07

EOF
}


#default parameters
#语料文件
CORPUS_PATH="" #english.txt
NAME="" #english
LOCALE="" #en            #当前语言locale
VERSION=1               #生成的go二进制数据的版本号
ORDER=2	                # ngram
UNIGRAM=1000000000      #指定单词的个数
WORD_MAX_LEN=30         #dict中生成的文件，单词最大长度
PRUNE_THRESHOLD=0       #语言模型裁剪阀值，裁剪二维则为ne-n，裁剪三维则为ne-n,ne-n
PARAM_BASE_DICTIONARY=""
B_ADD_START_END=0       #第一步：格式化语料文件
B_DICT=0                #第二步：生成频度
B_BUILD_IM=0            #第三步：语言模型训练
B_PRUNE=0               #第四步：语言模型裁剪 and 第五步：语言模型词频转换

SHORTCUT_FILT_PATH=""
OFFENSIVE_FILT_PATH=""
KEEP_OFFENSIVE_FREQ=""

while [ "$1" != "" ]; do
    case $1 in
        -a | --addStartEnd )    B_ADD_START_END=1;
                                ;;
        -d | --dict )           B_DICT=1;
                                ;;
        -b | --buildIm )        B_BUILD_IM=1;
                                ;;
        -p | --prune )          B_PRUNE=1;
                                ;;

        -c | --corpusPath )     shift; CORPUS_PATH=$1;
                                ;;
        -L | --lanuage )        shift; NAME=$1;
                                ;;
        -l | --locale )         shift; LOCALE=$1;
                                ;;
        -v | --dataversion )    shift; VERSION=$1;
							    ;;
        -o | --order )          shift; ORDER=$1;
                                ;;
        -u | --unigramCount )   shift; UNIGRAM=$1;
                                ;;
        -w | --wordMaxLen )     shift; WORD_MAX_LEN=$1;
                                ;;
        -t | --pruneThreshold ) shift; PRUNE_THRESHOLD=$1;
								;;
	    -W | --wordlist)        shift; PARAM_BASE_DICTIONARY="-w $1";
	                            ;;
	                            
             --shortcut)       shift; SHORTCUT_FILT_PATH="-s $1";
                                ;;
             --offensive)       shift; OFFENSIVE_FILT_PATH="-f $1";
                                ;;
             --keepOffensiveFreq)       shift; KEEP_OFFENSIVE_FREQ="--keepOffensiveFreq";
                                ;;

        -h | -? | --help )      usage;
                                exit 0;
                                ;;
        * )                     usage;
                                exit 1;
    esac
    shift
done

if [ $NAME -a -z $CORPUS_PATH ];
then
    CORPUS_PATH=${NAME}.txt
fi

if [ -z "$LOCALE" -o -z "$CORPUS_PATH" -o -z "$NAME" ];
then
    echo "Error: Not specified locale or language, -c -L -l ..."
    exit 2;
fi

if [ $B_ADD_START_END -eq 0 -a $B_DICT -eq 0 -a $B_BUILD_IM -eq 0 -a $B_PRUNE -eq 0 ];
then
    B_ADD_START_END=1       #第一步：格式化语料文件
    B_DICT=1                #第二步：生成频度
    B_BUILD_IM=1            #第三步：语言模型训练
    B_PRUNE=1
fi

echo "====================================================================="
echo "Corpus path: $CORPUS_PATH, Language: $NAME, Locale: $LOCALE "
echo "Data version: $VERSION, Ngram order: $ORDER, Unigram count: $UNIGRAM, Word max len: $WORD_MAX_LEN, Prune threshold: $PRUNE_THRESHOLD"
echo "====================================================================="

#export IRSTLM=/opt/irstlm

#TOOL_SCRIPTS=/home/zhaokun/IME/StatisticalLanguageModel/irstlm-5.80.08/trunk/scripts
#TOOL_BIN=/home/zhaokun/.clion11/system/cmake/generated/aa4b1bab/aa4b1bab/Debug/src
TOOL_SCRIPTS=${IRSTLM}/bin
TOOL_BIN=${IRSTLM}/bin


add_start_end_ex=${TOOL_SCRIPTS}/add-start-end-ex.sh
dict=${TOOL_BIN}/dict
build_lm=${TOOL_SCRIPTS}/build-lm.sh
compile_lm=${TOOL_BIN}/compile-lm
prune_lm=${TOOL_BIN}/prune-lm
quantize_lm=${TOOL_BIN}/quantize-lm
ngt=${TOOL_BIN}/ngt
lm2golatindata=${TOOL_SCRIPTS}/lm2golatindata.py
build_sublm=${TOOL_SCRIPTS}/build-sublm.pl
merge_sublm=${TOOL_SCRIPTS}/merge-sublm.pl
GODicttool=../../GODicttool/GODicttool


###############################
#工具分为5步
#第一步：格式化语料文件，给语料断句，添加<s></s>标签
#第二步：生成频度，结果文件×××_count.txt，文件2列，为词和计数
#第三步：语言模型训练，会占用大部分时间
#第四步：语言模型裁剪，裁剪二维词个数，需要手动设置PRUNE_THRESHOLD进行裁剪，ne-m，n越大词越少，m(整数)越大，词越多
#第五步：语言模型词频转换，转换成0-255词频，生成go的文本词库。生成文件是***_go.txt

#其中，第二步和第四步分别是对一维和二维裁剪，需要手动调整，
###############################




#############################################################################
###第一步##添加<s></s>标签
if [ $B_ADD_START_END -eq 1 ] ;
then
    echo "########################## [start add start and end] ##########################"
    if [ ! -e ${CORPUS_PATH} ];then echo "error: file or dir ${CORPUS_PATH} not exist.."; exit 4; fi
    ${add_start_end_ex} -i ${CORPUS_PATH} -o ${NAME}_add_start_end.txt -l ${LOCALE} ${PARAM_BASE_DICTIONARY}
fi

#-------------------------------------------------------------------
###第二步##生成频度
if [ $B_DICT -eq 1 ] ;
then
    echo "########################## [make dict count] ##########################"
    if [ ! -e ${NAME}_add_start_end.txt ];then echo "error: file ${NAME}_add_start_end.txt not exist.."; exit 4; fi
    ${dict} -i=${NAME}_add_start_end.txt -o=${NAME}_count_original.txt -f=y -sort=no
    while [ 1 ];
    do
        FREQ_MIN=`sort -rn -k2 ${NAME}_count_original.txt | awk 'NR=='''${UNIGRAM}''' {print $2}'`
        if [ -z $FREQ_MIN ]; then FREQ_MIN=0; fi
        echo '>>>>>>> min freq:' $FREQ_MIN

        (echo DICTIONARY; tail -n +2 ${NAME}_count_original.txt | awk '
            {
                if ($2>='''$FREQ_MIN''' && length($1)<='''$WORD_MAX_LEN''') print;
            }') > ${NAME}_count.txt
        let WORD_COUNT=`cat ${NAME}_count.txt | wc -l`-1

        echo '>>>>>>> unigram count:' $WORD_COUNT

        break;

    done
fi

#是否删除原始的数据呢？
if [ 0 -eq 1 ] ; then rm ${NAME}_count_original.txt; fi

#-------------------------------------------------------------------
###第三步##语料训练
if [ $B_BUILD_IM -eq 1 ] ;
then
    echo "########################## [build lm] ##########################"
    if [ ! -e ${NAME}_add_start_end.txt ];then echo "error: file ${NAME}_add_start_end.txt not exist.."; exit 4; fi
    ${build_lm} -i ${NAME}_add_start_end.txt -n ${ORDER} -o ${NAME}.ilm -k 5 -p -d ${NAME}_count.txt
    #####训练结果转换为APRA格式
    if [ ! -e ${NAME}.ilm.gz ];then echo "error: file ${NAME}.ilm.gz not exist.."; exit 4; fi
    ${compile_lm} ${NAME}.ilm.gz --text=yes /dev/stdout | gzip -c > ${NAME}.lm.gz
fi

#-------------------------------------------------------------------
###第四步##语言模型裁剪,threshold指定裁剪几维,3维则是1e-6,1e-6
unigramcount=0
bigramcount=0
if [ $B_PRUNE -eq 1 ] ;
then
    echo "########################## [prune lm] ##########################"
    while [ 1 ];
    do
        if [ ! -e "${NAME}.lm.gz" ];then echo "error: file ${NAME}.lm.gz not exist.."; exit 4; fi
        ${prune_lm} --threshold=${PRUNE_THRESHOLD} ${NAME}.lm.gz ${NAME}.plm

        #考虑在这个地方把<>标签去除
        #这个地方删掉标签，出来的数据经过测试发现输入效率变差
#        cat ${NAME}.plm | awk '$0 !~ /<.*>/ {print}' > ${NAME}_not_tag.plm
#        mv ${NAME}_not_tag.plm ${NAME}.plm

        #-------------------------------------------------------------------
        ###第五步##量化语言模型，把频率转换为0-255的值
        echo "########################## [quanize lm] ##########################"
        if [ ! -e ${NAME}.plm ];then echo "error: file ${NAME}.plm not exist.."; exit 4; fi
        ${quantize_lm} ${NAME}.plm ${NAME}.qlm 2> /dev/null
        #####转换成go的文本词库
        echo "########################## [lm to go latin data] ##########################"
        if [ ! -e ${NAME}.qlm ];then echo "error: file ${NAME}.qlm not exist.."; exit 4; fi
              
        python ${lm2golatindata} -l ${LOCALE} -v ${VERSION} -i ${NAME}.qlm -o ${NAME}_go.txt ${SHORTCUT_FILT_PATH} ${OFFENSIVE_FILT_PATH} ${KEEP_OFFENSIVE_FREQ}

        unigramcount=`cat ${NAME}_go.txt | grep "word=" | wc -l`
        bigramcount=`cat ${NAME}_go.txt | grep "bigram=" | wc -l`

        echo '>>>>>>> unigram count' $unigramcount
        echo '>>>>>>> bigram count' $bigramcount

        function SaveResult() {
            if [ -e ${NAME}_go.txt ]; then
                mv ${NAME}.plm ${NAME}_${unigramcount}_${bigramcount}.plm
                mv ${NAME}_go.txt ${NAME}_${unigramcount}_${bigramcount}_go.txt
                echo -e "\033[31m@@@@@   result file: ${NAME}_${unigramcount}_${bigramcount}_go.txt   @@@@@\033[0m"
            fi
        }

        stop='false'
        while [ 1 ];
        do
            echo -en "\n\n\033[31mSave result? [Y/N]:\033[0m" # 是否保存结果
            read bSave
            if [ $bSave = 'Y' -o $bSave = 'y' ]; then
                SaveResult;
            fi


            echo -en "\n\n\033[31mReset Prune Threshold [Ae-B/N]:\033[0m" #是否调整二维阀值
            read bAdjust

            if [ $bAdjust = 'N' -o $bAdjust = 'n' ]; then
                SaveResult;
                stop='true';
                break;
            fi

            if [ `echo $bAdjust | grep "[0-9.]e-[0-9]"` ];
            then
                #echo $bAdjust
                PRUNE_THRESHOLD=$bAdjust
                break;
            fi
        done

        if [ $stop = 'true' ]; then break; fi

    done
fi


#####转换成go的二进制词库
#${GODicttool} -s ${NAME}_go.txt -d GODict_${NAME}.mp3

####################################################################################

# 一个一个的运行

#${add_start_end_ex} -i ${CORPUS_PATH} -o ${NAME}_add_start_end.txt
#生成计数
#${dict} -i=${NAME}_add_start_end.txt -o=${NAME}_count.txt -f=y -sort=no
#生成计数
#${dict} -i=${NAME}_add_start_end.txt -o=tmp/dict.000 -f=y -sort=no
#计算二维计数
#${ngt} -i=${NAME}_add_start_end.txt -n=${ORDER} -gooout=y -o=tmp/ngram.000.txt -fd=tmp/dict.000 -sd=${NAME}_count.txt
#计算频率
#${build_sublm} --prune-singletons --witten-bell  --size ${ORDER} --ngrams tmp/ngram.000.txt -sublm tmp/lm.000
#合并频率
#${merge_sublm} --size ${ORDER} --sublm tmp/lm.000 -lm ${NAME}.ilm


















