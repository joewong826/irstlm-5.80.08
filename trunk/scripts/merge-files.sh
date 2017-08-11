#! /bin/bash

function usage()
{
    cmnd=$(basename $0);
    cat<<EOF

$cmnd - 合并指定目录下所有文件到指定文件

USAGE:
       $cmnd [options] inputfile outputfile

OPTIONS:
       -h        Show this message

EOF
}

# Parse options
while getopts h OPT; do
    case "$OPT" in
        h)
            usage >&2;
            exit 0;
            ;;
    esac
done

# 合并目录下有文件到指定文件
echo "merger $1 files to $2"

touch $2

#\( ! -regex '.*/\..*' ! -regex '.*~' \) 过滤掉所有.开头的文件和～结尾的文件，这两类文件一般为隐藏文件
# -type f 只列出文件
find $1 \( ! -regex '.*/\..*' ! -regex '.*~' \) -type f | xargs cat 2>/dev/null >> $2
