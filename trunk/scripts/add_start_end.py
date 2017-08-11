#!/usr/bin/python
# -*- coding=utf-8 -*-



import codecs
import re
import sys
import os
from optparse import OptionParser


from languageinfo import *
from languageparse import *

'''
格式化文件，以文件的行为单位，把每行分割成句子，每个句子左右分别添加<s> </s>

-f FILE 指定有效字符文件
python add_start_end.py -l en -j languageinfo -w wordlistPath -i input.txt -o output.txt
python add_start_end.py -l en -j languageinfo -w wordlistPath < input.txt > output.txt

'''

try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except:
    pass


def getfileencode(path, defaultencoding='utf-8'):
    encoding = defaultencoding
    with open(path, 'r') as fp:
        header = fp.read(3)
        if header == codecs.BOM_UTF8:
            encoding = 'utf_8_sig'
        elif header[:2] == codecs.BOM_LE:
            encoding = 'utf_16_le'
        elif header[:2] == codecs.BOM_BE:
            encoding = 'utf_16_be'
        return encoding


def getfiles(path):
    path = os.path.abspath(path)
    for root, dirs, files in os.walk(path):
        if os.path.basename(root).startswith('.'):
            continue
        for filename in files:
            if filename.startswith('.') or filename.endswith('~'):
                continue
            inputpath = os.path.join(root, filename)
            yield inputpath


class FormatSentence:
    def __init__(self, verbose=False):
        self.lower = False
        self.chars = {}
        self.charsTotalNum = 0
        self.mLanguageInfo = None
        self.mLanguageParse = None
        self.mbVerbose = verbose

    def setLower(self, lower=True):
        '''lower为True和False'''
        self.lower = lower

    def loadWordList(self, wordListPath, encoding="utf8"):
        if self.mLanguageParse is None:
            raise "未加载Language info json....."
        self.mLanguageParse.loadWordList(wordListPath, encoding)

    def loadLanguageInfo(self, locale, languageInfoPath=None):
        self.mLanguageParse = LanguageParse.getLanguageParse(locale, languageInfoPath, verbose=self.mbVerbose)

    def statisticsChars(self, line):
        for c in line:
            num = self.chars.get(c, 0)
            self.chars[c] = num + 1
            self.charsTotalNum += 1

    def outStatisticsChars(self):
        if not self.mbVerbose:
            return
        self.log('\nstatistics chars:')
        kvs = sorted(self.chars.iteritems(), key=lambda kv: kv[1], reverse=True)
        for k, v in kvs:
            try:
                self.log(u"%s(%s)\t%d\t%d%%" % (k, hex(ord(k)), v, 1.0 * v / self.charsTotalNum * 100))
            except Exception, e:
                self.log(u"%s(%s)\t%d\t%d%%" % ("???", hex(ord(k)), v, 1.0 * v / self.charsTotalNum * 100))
                self.log("Total count: %d" % self.charsTotalNum)

    def run(self, stdin, stdout, coding='utf-8'):
        # import pdb;pdb.set_trace()
        for word in self.mLanguageParse.formatByStdio(stdin, coding):
            if self.lower:
                word = word.lower()
            stdout.write(word)
            if word.strip() != "":
                stdout.write(" ")

            self.statisticsChars(word)

        self.outStatisticsChars()

    def log(self, *args, **kwargs):
        sys.stderr.write(' '.join(args))
        sys.stderr.write("\n")
        for k, v in kwargs.iteritems():
            sys.stderr.write("%s:%s " % (k, v))
            sys.stderr.write("\n")

def analyzeParams(args):
    parser = OptionParser(usage="%prog [-c str] [-u] [-l] [-v] -i FILE or [< FILE] -o FILE or [> FILE]"
                                ""
                          , version="%prog 2.0")

    # add_option用来加入选项，action是有store，store_true，store_false等，dest是存储的变量，default是缺省值，help是帮助提示
    parser.set_description(u'格式化文件，以文件的行为单位，把每行分割成句子，每个句子左右分别添加<s> </s>');

    parser.add_option("-c", "--coding", dest="coding", metavar="string"
                      , help=u'指定输入文件编码， 默认utf-8，使用-i时该参数无效，对使用<传入文件时有效', default=None)
    parser.add_option("-u", "--nocasesensitive", dest="nocasesensitive", action="store_true"
                      , help=u'不区分大小写，会把所有字符转成小写', default=False)
    parser.add_option("-j", "--languageInfoPath", dest="languageInfoPath", metavar="FILE", action="store"
                      , help=u'语言信息文件, 默认文件为工程目录languageinfo.json')
    parser.add_option("-w", "--wordlist", dest="wordlistPath", metavar="FILE", action="store"
                      , help=u'基本词表文件路径，用来表明单词')

    parser.add_option("-i", "--input", dest="inputPath", metavar="FILE", action="store"
                      , help=u'输入文件路径, 可以是目录， 也可使用< FILE')
    parser.add_option("-o", "--output", dest="outputpath", metavar="FILE", action="store"
                      , help=u'输出文件路径，可以是目录， 也可使用> FILE')

    parser.add_option("-l", "--locale", dest="locale", metavar="string"
                      , help=u'语言locale, 通过locale来决定有效字符', default='')

    parser.add_option("-v", "--verbose", dest="verbose", action="store_true"
                      , help=u'输出详细信息，会输出字符统计及其他信息', default=False)

    # if len(args) <= 1:
    #     print parser.print_help()
    # return

    (opt, args) = parser.parse_args(args)

    if opt.locale == '':
        print 'error: 没有通过-l指定locale。'
        sys.exit(0)
    # import pdb;pdb.set_trace()
    formatFile = FormatSentence(verbose=opt.verbose)
    formatFile.setLower(opt.nocasesensitive == True)
    formatFile.loadLanguageInfo(opt.locale, opt.languageInfoPath)
    if opt.wordlistPath:
        formatFile.loadWordList(opt.wordlistPath, getfileencode(opt.wordlistPath))

    readCode = opt.coding if opt.coding is not None else None
    writeCode = opt.coding if opt.coding is not None else 'utf8'

    if opt.inputPath is None:
        stdin = sys.stdin
        if opt.outputpath is None:
            stdout = sys.stdout
        else:
            stdout = codecs.open(opt.outputpath, 'w', writeCode)
        if readCode is None:
            readCode = 'utf8'
        formatFile.run(stdin, stdout, readCode)
        stdin.close()
        stdout.close()
        return

    if os.path.isdir(opt.inputPath):
        # 输入是目录
        stdout = sys.stdout
        bOutputDir = False
        if opt.outputpath is not None:
            if os.path.exists(opt.outputpath) and os.path.isdir(opt.outputpath):
                bOutputDir = True
            else:
                stdout = codecs.open(opt.outputpath, 'w', writeCode)

        path_str_len = len(opt.inputPath.rstrip(os.path.sep))
        filecount = 0
        for ip in getfiles(opt.inputPath):
            filecount += 1
            print filecount, '\r',
            # print ip
            fileencoding = getfileencode(ip)
            stdin = codecs.open(ip, 'r', fileencoding) if fileencoding.startswith("utf_16") else open(ip, 'r')
            if bOutputDir == True:
                op = os.path.join(opt.outputpath, ip[path_str_len + 1:])
                if not os.path.exists(os.path.split(op)[0]):
                    os.makedirs(os.path.split(op)[0])
                stdout = codecs.open(op, 'w', writeCode)
            if readCode is None:
                readCode = fileencoding
            formatFile.run(stdin, stdout, readCode)
            stdin.close()
            if bOutputDir == True:
                stdout.close()
        stdout.close()
    else:
        # 输入是文件
        fileencoding = getfileencode(opt.inputPath)
        stdin = codecs.open(opt.inputPath, 'r', fileencoding) if fileencoding.startswith("utf_16") else open(opt.inputPath, 'r')
        if opt.outputpath is not None:
            stdout = codecs.open(opt.outputpath, 'w', writeCode)
        else:
            stdout = sys.stdout
        if readCode is None:
            readCode = fileencoding
        formatFile.run(stdin, stdout, readCode)
        stdin.close()
        stdout.close()


if __name__ == "__main__":
    # sys.argv = ['/home/zhaokun/IME/StatisticalLanguageModel/irstlm-5.80.08/trunk/scripts/add_start_end.py',
    #             # '-i', '/home/zhaokun/IME/DicTools/gram_statistics_latin/output/output_webContent/sitroom.html',
    #             # '-o', '/home/zhaokun/IME/DicTools/gram_statistics_latin/output/output_webContent/sitroom_new.html',
    #             '-i', '/home/zhaokun/文档/add-start-end/news.txt',
    #             '-o', '/home/zhaokun/文档/add-start-end/news_add_start_end.txt',
    #             '-l', 'en',
    #             '-v'
    #             ]
    # sys.argv = ['add_start_end.py',
    #             '-i', '/home/zhaokun/文档/hk/Arabic_news2.txt',
    #             '-o', '/home/zhaokun/文档/hk/Arabic_news2_filter.txt',
    #             '-l', 'ar',
    #             '-w', '/home/zhaokun/文档/hk/ar_CapStandard.txt'
    #             ]
    
    analyzeParams(sys.argv)


