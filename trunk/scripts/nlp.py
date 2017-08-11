#!/usr/bin/env python
# -*- coding=utf-8 -*-

import codecs
import matplotlib.pyplot as plt
import numpy
from matplotlib import cm
import re
import math
from optparse import OptionParser
import sys, os

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

def getwords(path, defaultencoding='utf-8'):
    with codecs.open(path, 'r', defaultencoding) as fp:
        for line in fp:
            for word in line.split():
                yield word

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


class Tokenize:
    def __init__(self, caseSensitive=False):
        self._words = {}  # {word: freq}
        self._totalCount = 0 # 单词总计数
        self._wordCount = 0 #单词个数
        self._caseSensitive = caseSensitive

    def _input(self, text):
        if not self._caseSensitive:
            text = text.lower()
        words = text.split()
        for word in words:
            self._words[word] = self._words.get(word, 0) + 1
            self._totalCount += 1

    def inputFile(self, paths, isCountFile=False):
        '''        
        :param path: 
        :param isCountFile: 计数文件，两列，第一列为词，第二列为计数 
        :return: 
        '''
        if isinstance(paths, str):
            paths = [paths]

        for path in paths:
            encoding = getfileencode(path)
            with codecs.open(path, 'r', encoding) as fp:
                if not isCountFile:
                    for line in fp:
                        self._input(line)
                else:
                    for line in fp:
                        cols = line.split()
                        if len(cols) < 2:
                            continue
                        __count = int(cols[1])
                        if not self._caseSensitive:
                            self._words[cols[0].lower()] = __count
                        else:
                            self._words[cols[0]] = __count
                        self._totalCount += __count

        self._wordCount = len(self._words)


    def tolist(self, reverse=False):
        ''' 输出为列表，默认按计数从大到小排序       
        :param reverse: 
        :return: 
        '''
        return sorted(self._words.iteritems(), key=lambda k: k[1], reverse=not reverse)

    def showDistribution(self, count=50):
        '''显示分布图
        :return: 
        '''
        def autolabel(rects):
            for rect in rects:
                width = rect.get_width()
                plt.text(rect.get_x()+width+2000, rect.get_y(), '%s' % int(width))

        plt.xlabel(u'Word')
        plt.ylabel(u'Count')
        plt.title(u"Top 50 distribution".format(count))
        wordAndCounts = sorted(self._words.iteritems(), key=lambda k: k[1])[len(self._words)-count:]
        count = len(wordAndCounts)
        
        words = [word[0] for word in wordAndCounts]
        x = [word[1] for word in wordAndCounts]
        y = numpy.arange(count)
        rect = plt.barh(range(count), x)
        plt.yticks(y + 0.4, words)
        plt.grid(axis='x')

        autolabel(rect)

        plt.savefig("distribution.png")

        # plt.show()
        plt.close()
       
       
        
 
        
    def showCoverage(self):
        '''显示覆盖率图形        
        :return: 
        '''
        counts = sorted(self._words.itervalues(), reverse=True)
        totalCount = sum(counts)
        # print totalCount, counts

        # x = (1, 2, 3)
        # y1 = (2, 3, 4)
        # y2 = (3, 4, 5)
        # plt.plot(x, y1, 'r',  x, y2, 'g', linewidth=2)
        
        def coverage(counts):
            total = 0
            for count in counts:
                total += count
                yield 1.0 * total / totalCount
                            
        freq = list(coverage(counts))
        # print counts
        # print freq
        
        plt.plot(range(len(counts)), freq, 'r', linewidth=2)
        plt.xlim(-1000, 100000)# set axis limits
        plt.ylim(0.0, 1.1)
        # plt.axis([-1, 100000, 0, 1.1])
        plt.savefig("coverage.png")
        # plt.show()
        plt.close()
       
    def checkCoverage(self, paths, isFilterInvalidChars=False):
        ''' 检测测试语料的覆盖率，该文件是以词为单位，词之间空字符隔开（空字符包括\t、\r、\n、空格）        
        :param path: 
        :return: 
        '''
        if isinstance(paths, str):
            paths = [paths]
            
        testwords = list()    
        for path in paths:
            if isFilterInvalidChars:
                subpattern = re.compile("[^a-zA-Z'\-]")
                for word in getwords(path, getfileencode(path)):
                    words = subpattern.sub(' ', word)
                    for word in words.split():
                        testwords.append(word.lower())
            else:
                testwords.extend(list(getwords(path, getfileencode(path))))

        testwordscount = len(testwords)
        if testwordscount == 0:
            assert testwordscount != 0
        nonexistentWords = set()
        probsMap = {}
        totalProb = 0
        oovCount = 0
        unkProb = math.log10(1.0 * (self._wordCount + 1) / ((self._totalCount + self._wordCount) + self._wordCount + 1))
        for word in testwords:
            wordLower = word.lower()
            wordCount = self._words.get(wordLower, None)
            if wordCount is None:
                oovCount += 1
                nonexistentWords.add(word)
                totalProb += unkProb
            else:
                prob = probsMap.get(wordCount, None)
                if prob is None:
                    # 计算一维频率
                    # Pwb(wi) = (C(wi)+1) / (C* + N1+*)
                    # =（单词个数+1） / （（单词总频率 + unk频率） + （单词条目个数+1））
                    # =（单词个数+1） / （（单词总频率 + 单词条目个数） + （单词条目个数+1））
                    freq = 1.0 * (wordCount + 1) / ((self._totalCount + self._wordCount) + self._wordCount + 1)
                    prob = math.log10(freq)
                    probsMap[wordCount] = prob
                totalProb += prob

        # 计算困惑度perplexity
        # ppl = math.exp(-(prob/count)*math.log(10))
        perplexity = math.exp(-(totalProb/(testwordscount-0)) * math.log(10))               
                
        
        # print "测试单词个数：", testwordscount        
        # print "覆盖率：", 1- 1.0 * len(nonexistentWords) / testwordscount
        # print "不存在的词：", ' '.join(nonexistentWords)
        
        # return (测试用例个数，不存在的个数，不存在的词）
        return (testwordscount, len(nonexistentWords), perplexity, nonexistentWords)

        
def contrastCoverage(trainingCorpuss, testCorpus):
    nonexistentWordsList = []
    for trainingCorpus in trainingCorpuss:
        tokenize = Tokenize()
        tokenize.inputFile(trainingCorpus, True)
        testwordscount, nonexistentWordsCount, perplexity, nonexistentWords = tokenize.checkCoverage(testCorpus)
        print "训练语料：",trainingCorpus
        print "测试单词个数：", testwordscount
        print "覆盖率：", (1- 1.0 * nonexistentWordsCount / testwordscount)*100, '%'
        print "困惑度：", perplexity
        # print "不存在的词：", ' '.join(nonexistentWords)
        nonexistentWordsList.append(nonexistentWords)
    print "0 - 1 差：\n",nonexistentWordsList[0] - nonexistentWordsList[1]
    print "1 - 0 差：\n",nonexistentWordsList[1] - nonexistentWordsList[0]

def findWord(paths, word):    
    for path in paths:
        defaultencoding = getfileencode(path)
        with codecs.open(path, 'r', defaultencoding) as fp:
            for i, line in enumerate(fp):
                findall = re.findall(word, line)
                if len(findall) > 0:
                    print "path:{}, line:{}".format(path, i)
                    print line


def tolower(paths):
    if isinstance(paths, str):
        paths = [paths]
    for path in paths:
        name, ext = os.path.splitext(path)
        newpath = name + "_lower" + ext
        with codecs.open(newpath, 'w') as fpOut:
            with codecs.open(path, 'r') as fp:
                for line in fp:
                    fpOut.write(line.lower())


def analyzeParams(args):
    parser = OptionParser(usage="%prog -t [0 or 1] -i FILE -u -d file -s"
                                ""
                          , version="%prog 2.0")

    # add_option用来加入选项，action是有store，store_true，store_false等，dest是存储的变量，default是缺省值，help是帮助提示
    parser.set_description(u'计算语料覆盖率，可以是纯语料文件，也可以是词语计数格式文件（2列：词\t计数)');

    parser.add_option("-t", "--type", dest="filetype", metavar="int"
                      , help=u'语料格式，取指0和1，0为纯语料文件，1为词语计数格式文件，默认为0', default=0)
    parser.add_option("-i", "--input", dest="inputPath", metavar="FILE", action="store"
                      , help=u'输入文件路径, 可以是目录,也可以是逗号分割的多个文件路径')
    parser.add_option("-u", "--nocasesensitive", dest="nocasesensitive", action="store_true"
                      , help=u'不区分大小写，会把所有字符转成小写', default=False)

    parser.add_option("-d", "--detection", dest="detection", metavar="FILE", action="store"
                      , help=u'测试语料文件路径，可以是逗号分开的多个文件路径')
    parser.add_option("-s", "--savepng", dest="savepng", action="store_true"
                      , help=u'是否保存树状图和覆盖曲线图为图片', default=False) 
  

    # if len(args) <= 1:
    #     print parser.print_help()
    # return

    (opt, args) = parser.parse_args(args)

    if opt.inputPath is None:
        print 'error: 没有指定文件'
        sys.exit(0)

    tokenize = Tokenize(not opt.nocasesensitive)

    paths = []
    if os.path.isdir(opt.inputPath):
        paths = getfiles(opt.inputPath)        
    else:
        paths = opt.inputPath.split(',')

    tokenize.inputFile(paths)
    if opt.savepng:
        tokenize.showDistribution()
        tokenize.showCoverage()
        
    if opt.detection:
        testwordscount, nonexistentWordsCount, perplexity, nonexistentWords = tokenize.checkCoverage(opt.detection)
        print "训练语料：", opt.inputPath
        print "测试单词个数：", testwordscount
        print "覆盖率：", (1 - 1.0 * nonexistentWordsCount / testwordscount) * 100, '%'
        print "困惑度：", perplexity
        # print "不存在的词：", ' '.join(nonexistentWords)
        
def test():
    # tokenize = Tokenize()
    # # tokenize.input("good morining good asdf good ads f")
    # tokenize.inputFile('/home/zhaokun/文档/hk/en/output_new/新建/en_new_word_list_lower_count.txt', True)
    # # tokenize.inputFile('/home/zhaokun/文档/hk/output_new/ar_add_start_end.txt', False)
    # # print tokenize.tolist()
    # tokenize.showDistribution()
    # tokenize.showCoverage()

    # tokenize.checkCoverage('/home/zhaokun/文档/hk/en_news.txt')


    # contrastCoverage(
    #     # ['/home/zhaokun/文档/hk/output_new/ar_new_count.txt',
    #     #  '/home/zhaokun/文档/hk/output_old/ar_count.txt'],
    #     # '/home/zhaokun/文档/hk/ar_CapStandard.txt'
    # 
    #     # ['/home/zhaokun/文档/hk/output_new/ar_new_count_original.txt',
    #     #  '/home/zhaokun/文档/hk/output_old/ar_count_original.txt'],
    #     # '/home/zhaokun/文档/hk/en_blogs.txt'
    #     # '/home/zhaokun/文档/hk/Arabic_news2.txt'
    #     # '/home/zhaokun/文档/hk/Arabic_news2_filter.txt'
    # 
    #     # '/home/zhaokun/文档/hk/en_news.txt'
    #     # '/home/zhaokun/IME/StatisticalLanguageModel/data/new_lm/english_add_start_end.txt'
    # 
    #     [
    #         '/home/zhaokun/文档/hk/en/output_new/新建/en_new_word_list_lower_count.txt',
    #         # '/home/zhaokun/文档/hk/en/output_new/新建/en_new_count.txt',
    #         # '/home/zhaokun/文档/hk/en/output_new/新建/en_new_word_list_count.txt',                 
    #         # '/home/zhaokun/文档/hk/en/output_old/en_old_count_original.txt',
    #         '/home/zhaokun/文档/hk/en/output_old/新建/en_old_count.txt'
    #     ], '/home/zhaokun/文档/hk/en_news.txt'
    # )

    # findWord([
    #     # '/home/zhaokun/文档/hk/Arabic_Corpus_2011_03_09/Ara_Blogs.txt',
    #     # '/home/zhaokun/文档/hk/Arabic_Corpus_2011_03_09/Ara_Newspapers.txt',
    #     # '/home/zhaokun/文档/hk/Arabic_Corpus_2011_03_09/Ara_Twitter.txt',
    #     # '/home/zhaokun/文档/hk/output_new/ar_new_count_original.txt',
    #     # '/home/zhaokun/文档/hk/output_old/ar_count_original.txt',
    # 
    #     '/home/zhaokun/文档/hk/en/English_HCCorpus/Blogs.txt',
    #     '/home/zhaokun/文档/hk/en/English_HCCorpus/Newspapers.txt',
    #     '/home/zhaokun/文档/hk/en/English_HCCorpus/Twitter.txt',
    # 
    #           ], u'[^a-zA-Z\'\-]zite[^a-zA-Z\'\-]')#u'\u0628\u0640\u0628\u0631\u0646\u0627\u0645\u062c')

    tolower('/home/zhaokun/IME/StatisticalLanguageModel/data/hk/en/output_new/en_new_syn_table_add_start_end.txt')
                
if __name__ == "__main__":
    analyzeParams(sys.argv)    
    # test()
    # import pickle
    # buf = open('/home/zhaokun/IME/StatisticalLanguageModel/data/hk/lm_new_svn15933/trunk/scripts/languageinfo.json', 'r').read()
    # buf = buf.replace("//",  '#').replace('/*', '#').replace('true', 'True').replace('false', 'False')
    # json = eval(buf)
    # print json
    # 
    