#!/usr/bin/python
#-*- coding=utf-8 -*-



import codecs
import re
import sys
import os
import time
from optparse import OptionParser
import languageinfo

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
            encoding='utf_8_sig'     
        elif header[:2] == codecs.BOM_LE:
            encoding='utf_16_le'
        elif header[:2] == codecs.BOM_BE:
            encoding='utf_16_be'
        return encoding


def getFileLine(path):
    fileencoding = getfileencode(path)
    with codecs.open(path, 'r', fileencoding) as fp:
        for line in fp:
            yield line

BIGRAM_MAX_COUNT = 100
    
class GOLatin:
    def __init__(self, maxBigramCount=BIGRAM_MAX_COUNT):
        self.languageList = None
        self.__header = None
        self.maxBigramCount = maxBigramCount
        self.shortcuts = {}
        self.offensive = {}
        self.keepOffensiveFreq=False
        pass
    
    def loadLanguageList(self):
        jsonpath = languageinfo.DEFAULT_LANGUAGE_INFO_FILE_PATH
        with open(jsonpath) as fp:
            jsoninfo = eval(fp.read().decode('utf8'))
        if jsoninfo is None:
            return

        self.languageList = languageinfo.LanguageList(jsoninfo.get(languageinfo.LanguageInfo._KEY_LANGUAGE_LIST, None))

    def __updateHeader(self, locale='', version='0', options=None):
        description = "???"
        if self.languageList.hasLocale(locale):
            description = self.languageList.getDescription(locale)
        #dictionary=main:en,description=English,locale=en,date=1381226516,version=42
        if options is None:
            self.__header = 'dictionary=main:%s,description=%s,locale=%s,date=%d,version=%s' \
                % (locale, description, locale, int(time.time()), version)
        else:
            self.__header = 'dictionary=main:%s,options=%s,description=%s,locale=%s,date=%d,version=%s' \
                % (locale, options, description, locale, int(time.time()), version)               
    
    def generate(self):
        if self.maxNgram == 0:
            sys.stderr.write("error: not gram...\n")            
            return
        if self.__header is not None:
            self.stdout.write(self.__header+'\n')
        
        unigram = self.ngramWords[1]
        bigram = self.ngramWords[2] if self.maxNgram > 1 else None

        # 过滤数据中<s></s><unk>等标签
        filterPattern = re.compile('<.*>')
        filterWords = []
        for w,f in unigram.iteritems():           
            if len(filterPattern.findall(w)) > 0:
                filterWords.append(w)
                continue
            unigram[w] = [f, {}]
        for w in filterWords:
            del(unigram[w])
                
        if bigram is not None:
            for word, prev in bigram.iteritems():
                cols = word.split()
                if len(cols) != 2:
                    sys.stderr.write("error: bigram (%s) not 2 word\n" % word)    
                    continue
                _bigram = unigram.get(cols[0], None)
                if _bigram is not None:
                    _bigram[1][cols[1]] = prev
                
        unigram_list = sorted(unigram.iteritems(), key=lambda k:k[1][0], reverse=True)
        shortcutinfoInUnigramList = {}
        for word, freq_bigram in unigram_list:
            # word=de,f=239
            notAWord = False
            shortcutinfo = self.shortcuts.get(word)
            shortcuts = set()
            if shortcutinfo is not None:
                shortcutinfoInUnigramList[word] = 0;
                notAWord = shortcutinfo[0]
                shortcuts = shortcutinfo[1]

            isOffensive = self.offensive.has_key(word)

            self.stdout.write(' word={0},f={1}{2}{3}\n'.format(word,
                                                           freq_bigram[0] if not isOffensive or self.keepOffensiveFreq else 0,
                                                           ',not_a_word=true' if notAWord else '',
                                                           ',possibly_offensive=true' if isOffensive else '',
                                                           )
                              )
            shortcutF = 15 if notAWord else 14
            for shortcut in shortcuts:
                #  shortcut=don't,f=15
                self.stdout.write('  shortcut=%s,f=%d\n'%(shortcut, shortcutF)) 
                
                
            bigram = sorted(freq_bigram[1].iteritems(), key=lambda k:k[1], reverse=True)
            bigramCount = self.maxBigramCount if len(bigram) > self.maxBigramCount else len(bigram)
            addBigCount = 0
            for w, f in bigram:
                #   bigram=la,f=253
                if addBigCount >= bigramCount:
                    break
                # 引擎中二维词频要比实际的一维词频大
                if unigram.has_key(w) and f < unigram[w][0]:
                    continue
                if len(filterPattern.findall(w)) > 0:
                    continue
                self.stdout.write('  bigram=%s,f=%d\n'%(w, f))
                addBigCount += 1

        for word, shortcutinfo in self.shortcuts.iteritems():
            if word in shortcutinfoInUnigramList:
                continue
            notAWord = shortcutinfo[0]
            self.stdout.write(' word={0},f={1}{2}\n'.format(word, 0, ',not_a_word=true' if notAWord else '', ))
            shortcutF = 15 if notAWord else 14
            for shortcut in shortcutinfo[1]:
                #  shortcut=don't,f=15
                self.stdout.write('  shortcut=%s,f=%d\n'%(shortcut, shortcutF))

    def loadShortcutAndOffensivePath(self, shortcutPath=None, offensivePath=None, keepOffensiveFreq=False):
        if shortcutPath is not None:
            for line in getFileLine(shortcutPath):
                # shortcut文件中第三列0为not_a_word=true,1则表示词语为正常词语
                # self.shortcuts = {word: [notAword, set(shortcut)]}
                word, shortcut, notAWord = map(unicode.strip, line.split('\t'))
                # 单词两边出现-和'删掉
                if (word[0] in "-'" or word[-1] in "-'"
                    or shortcut[0] in "-'" or shortcut[-1] in "-'"
                    ):
                    continue

                notAWord = True if notAWord == '0' else False
                info = self.shortcuts.get(word, None)
                if info is None:
                    self.shortcuts[word] = [notAWord, set([shortcut])]
                else:
                    if notAWord: info[0] = True
                    info[1].add(shortcut)
                
        if offensivePath is not None:
            self.keepOffensiveFreq = keepOffensiveFreq
            for line in getFileLine(offensivePath):
                self.offensive[line.strip()] = 0
    
    def load(self, stdin, stdout, locale='???', version='0', bigramMaxCount=100, coding='utf8'):
        self.__updateHeader(locale, version)
        
        self.stdout = stdout
        lineno = 0        
        ngramMaxCodeCount = []
        ngramWordCount = []
        self.maxNgram = 0
        self.ngramWords = []
        while True:
            lineno+=1
            try:         
                #如果命令行使用<传入时，即stdin是sys.stdin时，需要由coding来指定编码
                line = stdin.readline()
                if line is None or len(line) == 0:
                    break
                if type(line) != unicode:
                    try:
                        line = line.decode(coding, 'ignore')
                    except:
                        pass
                #qARPA 2 256 256
                if True == line.strip().startswith(u'qARPA'):
                    cols = line.split()
                    self.maxNgram = int(cols[1])
                    ngramMaxCodeCount = [int(i) for i in cols[1:]]
                    ngramWordCount = [0] * (self.maxNgram+1)
                    for i in range(self.maxNgram+1):
                        self.ngramWords.append({})
                    continue
                if line.strip() == u'\\data\\':
                    for i in range(self.maxNgram):
                        lineno+=1
                        line = stdin.readline()
                        gram_and_count = re.findall(u'ngram\s*(\d+)\s*=\s*(\d+)\s*', line)
                        ngramWordCount[int(gram_and_count[0][0])] = int(gram_and_count[0][1])
                    continue
                
                if False == line.strip().endswith(u'grams:'):
                    continue

                curGram = re.findall(ur'\\(\d+)-grams:', line)
                curGram = int(curGram[0])
                #取code
                lineno+=1
                line = stdin.readline()
                count = int(line.strip())
                if count != ngramMaxCodeCount[curGram]:
                    sys.stderr.write("error： line(%d) code not %d\n" % (lineno, ngramWordCount[curGram]))
                    break
                for i in range(count):
                    lineno+=1
                    line = stdin.readline()                    
                    #暂时不做任何事情
                curGramWordCount = ngramWordCount[curGram]
                for i in xrange(curGramWordCount):
                    lineno+=1
                    line = stdin.readline().strip()        
                    type_and_word = line.strip().split()
                    if len(type_and_word) < 2:
                        sys.stderr.write("error： line(%d) [%s] word col error.\n" % (lineno, line))
                        break
                    pt = int(type_and_word[0])+1
                    assert pt >= 1 and pt <= 255
                    word = ' '.join(type_and_word[1:curGram+1])
                    curNgramWords = self.ngramWords[curGram]
                    if not curNgramWords.has_key(word):
                        curNgramWords[word] = pt
                    else:
                        sys.stderr.write("error： line(%d) [%s] word repetitional.\n" % (lineno, line))
                        break          
                    
            except Exception, e:
                pass
            except KeyboardInterrupt:
                break        
        
        #for i in range(len(self.ngramWords)):
            #if len(self.ngramWords[i]) == 0:
                #continue
            #with codecs.open('test_%d.txt' % (i), 'w') as fp:
                #for k, v in self.ngramWords[i].iteritems():
                    #fp.write('%s\t%d\n' % (k, v))
        

def analyzeParams(args):
    parser = OptionParser(usage="%prog [-c str] [-v str] [-l] -i FILE or [< FILE] -o FILE or [> FILE]"
                          , version="%prog 1.0")    

    #add_option用来加入选项，action是有store，store_true，store_false等，dest是存储的变量，default是缺省值，help是帮助提示     
    parser.set_description(u'把语言模型训练的qlm文件转换成golatin需要的词库源文件');
    parser.add_option("-c", "--coding", dest="coding", metavar="string"
                      , help=u'指定输入文件编码， 默认utf-8，使用-i时该参数无效', default="utf-8")
    parser.add_option("-v", "--dataversion", dest="dataversion", metavar="string"
                      , help=u'数据版本，默认为0', default='0')
    parser.add_option("-l", "--locale", dest="locale", metavar="string"
                      , help=u'语言locale', default='???')        
    parser.add_option("-i", "--input", dest="inputPath",metavar="FILE", action="store"
                      , help=u'输入文件路径， 也可使用< FILE')  
    parser.add_option("-o", "--output", dest="outputpath",metavar="FILE", action="store"
                      , help=u'输出文件路径， 也可使用> FILE')   
    parser.add_option("-n", "--bigrammaxcount", dest="bigramMaxCount", type='int', metavar="int",
                      help=u"二维词的最大个数,可选,默认设置为100,", default=BIGRAM_MAX_COUNT)

    parser.add_option("-s", "--shortcut", dest="shortcutPath", metavar="FILE", action="store"
                      , help=u'shortcut文件路径。文件三列，分别为word\\tshortcut\\tnot a word')
    parser.add_option("-f", "--offensive", dest="offensivePath", metavar="FILE", action="store"
                      , help=u'offensive文件路径。文件一列词')
    parser.add_option("", "--keepOffensiveFreq", dest="keepOffensiveFreq", action="store_true"
                      , help=u'保留冒犯性词的实际频率。默认false，所有冒犯词频率为0.'
                             u'旧版本生成器用f=0来识别冒犯性词，新版本生成器用标记possibly_offensive=true标记', default=False)
    
    (opt, args) = parser.parse_args(args)
    
    stdin = sys.stdin
    stdout = sys.stdout
    inputfilecodeing = opt.coding
    if opt.inputPath is not None:
        inputfilecodeing = getfileencode(opt.inputPath)
        stdin = codecs.open(opt.inputPath, 'r', inputfilecodeing)
    if opt.outputpath is not None:
        stdout = codecs.open(opt.outputpath, 'w', inputfilecodeing)
        
        
    golatin = GOLatin(opt.bigramMaxCount)
    golatin.loadLanguageList()
    golatin.load(stdin, stdout, opt.locale, opt.dataversion, coding=inputfilecodeing)
    golatin.loadShortcutAndOffensivePath(shortcutPath=opt.shortcutPath, offensivePath=opt.offensivePath, keepOffensiveFreq=opt.keepOffensiveFreq)
    golatin.generate()
    
    stdin.close()
    stdout.close()
    
    
if __name__ == '__main__':
    argv = sys.argv
    #argv = ['lm2golatindata.py', '-l', 'en', '-v', '1',  '-i', '../data/english.qlm', '-o', '../data/english_go.txt']
    #argv = ['lm2golatindata.py', '-l', 'en', '-v', '1',  '-i', '../data/train.qlm', '-o', '../data/train.txt', '-n', '1']
    # argv = ['lm2golatindata.py', '-l', 'en', '-v', '1',
    #         '-i', '/home/zhaokun/IME/StatisticalLanguageModel/data/hk/en/output_new/en_new_modify_lower_20000.qlm',
    #         '-o', '/home/zhaokun/IME/StatisticalLanguageModel/data/hk/en/output_new/en_new_modify_lower_20000.txt',
    #         '-s', '/home/zhaokun/IME/StatisticalLanguageModel/data/hk/en/en_words_shortcuts.txt',
    #         '-f', '/home/zhaokun/IME/StatisticalLanguageModel/data/hk/en/en_words_offensive.txt',
    #         # '--keepOffensiveFreq',
    #         '-n', '100']
    print ' '.join(argv)
    analyzeParams(argv)
    
