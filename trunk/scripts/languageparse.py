#!/usr/bin/env python
# -*- coding=utf-8 -*-

import os
import codecs
import re
from languageinfo import *
import sys

class LanguageParse:
    ''' 对语言进行解析：
    处理有效字符，及整句的断句

    # 正则使用的无效字符的pattern
    KEY_PATTERN_INVALID_CHARS = "patternInvalidChars"

    '''

    TABLE_BEGINNING_OF_THE_SENTENCE = '<s>'  # 句首标签
    TABLE_END_OF_THE_SENTENCE = '</s>'  # 句尾标签
    TABLE_WRAP = os.linesep  # 换行标签

    _WORD_STATE_NO_END = 0  # 没有结束
    _WORD_STATE_END = 1  # 结束，用于终止ngram关系简历，如用逗号隔开，
    _WORD_STATE_END_OF_THE_SENTENCE = 2  # 整句的结束，需要用来添加句尾标签
    _WORD_STATE_START_OF_THE_SENTENCE = 3 # 整句的开始

    @classmethod
    def getLanguageParse(self, locale, jsonpath=None, verbose=False):
        li = LanguageInfo(jsonpath)
        lci = li.getLanguageCharsetInfo(locale)
        return LanguageParse(lci.get(LanguageCharsetInfo.KEY_LOCALE),
                             validchars=lci.get(LanguageCharsetInfo.KEY_VALIDCHARS),
                             wordReplace=lci.get(LanguageCharsetInfo.KEY_WORD_REPLACE),
                             sentenceTerminators=lci.get(LanguageCharsetInfo.KEY_SENTENCE_TERMINATORS),
                             symbolsPrecededBySpace=lci.get(LanguageCharsetInfo.KEY_SYMBOLS_PRECEDED_BY_SPACE),
                             symbolsFollowedBySpace=lci.get(LanguageCharsetInfo.KEY_SYMBOLS_FOLLOWED_BY_SPACE),
                             symbolsClusteringTogether=lci.get(LanguageCharsetInfo.KEY_SYMBOLS_CLUSTERING_TOGETHER),
                             wordConnectors=lci.get(LanguageCharsetInfo.KEY_WORD_CONNECTORS),
                             wordSeparators=lci.get(LanguageCharsetInfo.KEY_WORD_SEPARATORS),
                             contextSensitiveMultiWhitespace=lci.get(
                                 LanguageCharsetInfo.KEY_CONTEXT_SENSITIVE_MULTI_WHITESPACE),
                             contextSensitiveWrap=lci.get(LanguageCharsetInfo.KEY_CONTEXT_SENSITIVE_WRAP),
                             caseSensitive=lci.get(LanguageCharsetInfo.KEY_CASE_SENSITIVE),
                             wordCorrection=lci.get(LanguageCharsetInfo.KEY_WORD_CORRECTION),
                             unknownWordToLower=lci.get(LanguageCharsetInfo.KEY_UNKNOWN_WORD_TO_LOWER),
                             verbose=verbose
                             )


    def __init__(self, locale, validchars,
                 wordReplace=(),
                 sentenceTerminators='',
                 symbolsPrecededBySpace='',
                 symbolsFollowedBySpace='',
                 symbolsClusteringTogether='',
                 wordConnectors='',
                 wordSeparators='',
                 contextSensitiveMultiWhitespace=True,
                 contextSensitiveWrap=True,
                 caseSensitive=True,
                 wordCorrection=True,
                 unknownWordToLower=True,
                 verbose=False
                 ):
        '''
        validchars ： 有效字符，只存放区间
        sentenceTerminators ： 整句结尾的符号
        symbolsPrecededBySpace ： 符号前需要空格
        symbolsFollowedBySpace ： 符号后需要空格
        symbolsClusteringTogether ： 聚合符号，该字符前不需要前面的空格，一般用来区别symbolsPrecededBySpace
        wordConnectors ： 词语连接符，一般为'和-
        wordSeparators : 词语分隔符，一般为标点符号
        contextSensitiveMultiWhitespace :  单词间存在多个空白字符时，是否进行上下文关联（建立ngram关系）
        contextSensitiveWrap :  单词间存在换行符时，是否进行上下文关联（建立ngram关系）
        caseSensitive :  区分大小写，为true时，处理大小写，为false时，全部转成小写处理
        wordCorrection: 是否纠错单词，如基本词表有VIP，语料中vip纠正为VIP
        unknownWordToLower: 基本词表中不存在的单词,转换成小写形式
        '''
        self.mbVerbose = verbose #详细的log输出
        self.validchars = validchars
        self.wordReplace = wordReplace
        self.sentenceTerminators = sentenceTerminators
        self.symbolsPrecededBySpace = symbolsPrecededBySpace
        self.symbolsFollowedBySpace = symbolsFollowedBySpace
        self.symbolsClusteringTogether = symbolsClusteringTogether
        self.wordConnectors = wordConnectors
        self.wordSeparators = wordSeparators
        self.contextSensitiveMultiWhitespace = contextSensitiveMultiWhitespace
        self.contextSensitiveWrap = contextSensitiveWrap
        self.caseSensitive = caseSensitive
        self.wordCorrection = wordCorrection
        self.unknownWordToLower = unknownWordToLower

        # 无效字符，re.compile or None
        self.compileInvalidChars = self._parseValidchars(validchars)

        # 字符替换，((re.compile, newword), ) or None
        self.compileWordReplaces = self._parseWordReplaces(wordReplace)

        self.basicWordList = None  # 基本词表,{word:None, }
        self.basicWordListLowerAndOther = None # 基本词表，{word lower: (set(各种形式), 优先词)}

        self.wordTransformFunc = self.wordTransformByBeginningOfTheSentence;

    def loadWordList(self, path, encoding="utf8"):
        self.basicWordList = None
        self.basicWordListLowerAndOther = None
        self.wordTransformFunc = self.wordTransformByBeginningOfTheSentence;
        if path is None or not os.path.exists(path):
            return
        with codecs.open(path, 'r', encoding=encoding) as fp:
            # python 2.6里不支持dict的列表推导
            # self.basicWordList = {(line.strip().split() + [None])[0]: None
            #                       for line in fp}
            self.basicWordList = {}
            self.basicWordListLowerAndOther = {}
            # import pdb;pdb.set_trace()
            for line in fp:
                word = (line.strip().split() + [None])[0]
                if word is None:
                    continue
                self.basicWordList[word] = None

                if self.wordCorrection:
                    wordlower = word.lower()
                    info = self.basicWordListLowerAndOther.get(wordlower, None)
                    if info is None:
                        info = (set(), word)
                        self.basicWordListLowerAndOther[wordlower] = info
                    info[0].add(word)

        self.wordTransformFunc = self.wordTransformByWordList;

    def isWord(self, word):
        '''如果存在基本词表，并且word存在，则认定该word为一个有效的单词
           如果不存在基本词表，则也认为word为有效单词
        '''
        return not self.basicWordList or self.basicWordList.has_key(word)

    def isCapitalize(self, word):
        """判断单词是否是首字母大写。（首字母大写，其他小写）
        空字符false，首字母小写false
        首字母大写，单字母为true，其他字符小写为true
        要用not word[0].isupper()，因为数字islower和isupper都为false
        """
        if word is None or len(word) == 0 or not word[0].isupper():
            return False
        return len(word) == 1 or word[1:].islower()

    def wordTransform(self, word, bBeginningOfTheSentence=False):
        return self.wordTransformFunc(word, bBeginningOfTheSentence)

    def wordTransformByBeginningOfTheSentence(self, word, bBeginningOfTheSentence=False):
        """ 如果word是首字母大写（只有第一个字母是大写，其他小写），并且是句首，则转成小写
        """
        if bBeginningOfTheSentence and self.isCapitalize(word):
            return word[0].lower() + word[1:]
        return word

    def wordTransformByWordList(self, word, bBeginningOfTheSentence=False):
        """根据基本词表对单词进行转换，只考虑首字母大写的情况
        word.lower存在 and word存在      =>>  word.lower
        word.lower存在 and word不存在    =>>  word.lower
        word.lower不存在 and word存在    =>>  word
        word.lower不存在 and word不存在  =>>  word.lower//修改为原样输出
        """
        if not self.isCapitalize(word):
            return word
        wordLower = word[0].lower() + word[1:]
        if self.isWord(wordLower):
            return wordLower
        # 如果小写形式不存在，则取原样的，也就是取首字母大写的词
        # elif self.isWord(word):
        #     return word
        else:
            return word

    def getWordCorrection(self, word):
        ''' 单词纠错
        1）语料词语在标准词表中找到（小写）匹配的：
            标准词表只存在小写形式的词语—》语料中换成小写形式进行词语训练
            标准词表存在两种以上形式的词语--》匹配状态的词语优先，其次全小写状态优先，进行替换训练
        2）语料词语在标准词表中找不到匹配的：原样统计

        存放 { 单词小写: [各种形式], }， 如 "iphone": [Iphone, IPhone, iPhone, iphone]
        if word lower in map:
            if word in [各种形式]:
                return word
            elif word lower in [各种形式]:
                return word lower
            else:
                return [各种形式]最优先的一个(基本词表最先出现的)
        else:
            if 是单字母，基本词表不存在：
                return None
            return word
        '''
        wordlower = word.lower()
        wordlist = self.basicWordListLowerAndOther.get(wordlower, None)
        if wordlist is None:
            if len(wordlower) == 1:
                return None
            if self.unknownWordToLower:
                return word.lower()
            return word
        if word in wordlist[0]:
            return word
        elif wordlower in wordlist[0]:
            return wordlower
        else:
            return wordlist[1]

    def _parseWordReplaces(self, wordReplace):
        if wordReplace is None:
            return None
        return tuple((re.compile("[%s]" % old), new) for old, new in wordReplace)

    def _parseValidchars(self, charsRegion):
        pattern = ' '
        for start, end in charsRegion:
            start = ur'\-' if start == u'-' else start
            end = ur'\-' if end == u'-' else end
            pattern += '%s-%s' % (start, end)

        if len(pattern) != 0:
            return re.compile(u'[^%s]+' % pattern)
        return None

    def hasInvalidChars(self, word):
        if self.compileInvalidChars is None:
            return False
        chars = self.compileInvalidChars.findall(word)
        return len(chars) != 0

    def replaceInvalidChars(self, word, new):
        '''替换word中无效字符为new'''
        if self.compileInvalidChars is None:
            return False
        return self.compileInvalidChars.sub(new, word)

    def replaceChars(self, pattern, word, new):
        '''替换word中指定字符为new'''
        ret = re.sub(pattern, new, word)
        return ret

    def returnEnding(self, endHasSentenceTerminator, bBeginningOfTheSentence):
        if endHasSentenceTerminator:
            if bBeginningOfTheSentence:
                # 又是开始又是结尾就不输出</s>，避免出现<s> </s>
                return "", self._WORD_STATE_END_OF_THE_SENTENCE
            return self.TABLE_END_OF_THE_SENTENCE, self._WORD_STATE_END_OF_THE_SENTENCE
        return "", self._WORD_STATE_END
    
    #@profile
    def format(self, word, bBeginningOfTheSentence=False):
        '''格式化：对传入的文章或者短句进行格式化
        干掉无效字符，切开短语，有效的标点符号作为一个词输出
        .good ==> good
        good. ==> good  .
        go----od ==>
        g-o-o-d
        good';
        go""od
        good:"good".
        good."
        good".
        U.S.
        'SNL'.
        .net
        1213good  ==> 丢弃
        '''
        # 先来个替换字符
        if self.compileWordReplaces is not None:
            for recp, new in self.compileWordReplaces:
                word = recp.sub(new, word)

        # 先考虑去除word前后的标点
        # 如.."go..od"..去除后是go..od.
        length = len(word)
        afterHasSeparator = False
        wordEnd = length - 1
        endHasSentenceTerminator = False
        endHasSeparator = False
        # 后标点如果是sentenceTerminators,则保留一个
        # import pdb;pdb.set_trace()
        for i in xrange(wordEnd, -1, -1):
            c = word[i]
            if c in self.sentenceTerminators:
                afterHasSeparator = True
                endHasSentenceTerminator = True
                wordEnd -= 1
            elif c in self.wordSeparators or c in self.wordConnectors:
                wordEnd -= 1
                endHasSeparator = True
                afterHasSeparator = True
            elif not self.hasInvalidChars(c):
                break
            else:
                if self.mbVerbose: print "invalid char: %s(%s) in (%s)" % (c, hex(ord(c)), word)
                yield self.returnEnding(endHasSentenceTerminator, bBeginningOfTheSentence)
                return;

        wordStart = 0
        beforeHasSeparator = False
        # 前标点去除
        for i in xrange(wordStart, wordEnd+1):
            c = word[i]
            if c in self.wordSeparators or c in self.wordConnectors:
                wordStart += 1
                beforeHasSeparator = True
            elif not self.hasInvalidChars(c):
                break
            else:
                if self.mbVerbose: print "invalid char: %s(%s) in (%s)" % (c, hex(ord(c)), word)
                yield self.returnEnding(endHasSentenceTerminator, bBeginningOfTheSentence)
                return;
        #前面有标点符号的都不关联二元关系，如 is <abc， is和abc不建立二元关系
        if beforeHasSeparator and wordStart <= wordEnd:
            yield "", self._WORD_STATE_END

        if wordStart > wordEnd:
            yield self.returnEnding(endHasSentenceTerminator, bBeginningOfTheSentence)
            return;

        # 先对word进行切分，去掉无效的内容
        words = [[], ]
        wordsState = [self._WORD_STATE_NO_END,]
        nextWordIndex = 0
        prevChar = ''
        bPrevWordIsConnectior = False
        bPrevWordIsSeparator = False
        for i in xrange(wordStart, wordEnd + 1):
            c = word[i]
            if (bPrevWordIsConnectior or bPrevWordIsSeparator) and c in self.wordConnectors:
                # 连续出现两个连接符，认为是个无效词，如go--od或go'-od
                if self.mbVerbose: print "has multi connector: %s" % (word)
                yield self.returnEnding(endHasSentenceTerminator, bBeginningOfTheSentence)
                return;
            if c not in self.symbolsClusteringTogether and c in self.symbolsPrecededBySpace:
                # 如果当前字符属于symbolsPrecededBySpace， 那么当前word是个无效词，因为c前必须有空格
                if self.mbVerbose: print "preceded by space: %s(%s) in (%s)" % (c, hex(ord(c)), word)
                yield self.returnEnding(endHasSentenceTerminator, bBeginningOfTheSentence)
                return;
            if i != wordEnd and c in self.symbolsFollowedBySpace:
                # 如果当前字符属于symbolsFollowedBySpace， 那么当前word是个无效词，因为c后面必须有空格
                if self.mbVerbose: print "followed by space: %s(%s) in (%s)" % (c, hex(ord(c)), word)                
                yield self.returnEnding(endHasSentenceTerminator, bBeginningOfTheSentence)
                return;
            if c in self.sentenceTerminators:
                # 如果是整句结束符，则开始下一个词，
                # eg：u.s 当.前后都可以不为空格是，应该拆分成u </s> <s> s
                wordsState[nextWordIndex] = self._WORD_STATE_END_OF_THE_SENTENCE
                nextWordIndex += 1
                words.append([])
                wordsState.append(self._WORD_STATE_NO_END)
                continue
            if c in self.wordSeparators:
                # 如果是单词切分字符，也可以说成是一般的标点符号，则认为句子中断，不建立二元关系，但不作为句子结束
                # eg: u,s 当，前后都可以不为空格时，应该拆分成u \n s
                if (bPrevWordIsSeparator or bPrevWordIsConnectior) and len(words[nextWordIndex]) > 0:
                    del(words[nextWordIndex][-1])
                wordsState[nextWordIndex] = self._WORD_STATE_END
                nextWordIndex += 1
                words.append([])
                wordsState.append(self._WORD_STATE_NO_END)
                bPrevWordIsSeparator = True
                continue
            bPrevWordIsConnectior = c in self.wordConnectors
            bPrevWordIsSeparator = False
            if self.hasInvalidChars(c):
                # 无效字符，丢弃该词
                if self.mbVerbose: print "invalid char: %s(%s) in (%s)" % (c, hex(ord(c)), word)
                yield self.returnEnding(endHasSentenceTerminator, bBeginningOfTheSentence)
                return;
            words[nextWordIndex].append(c)
            prevChar = c

        if endHasSentenceTerminator:
            wordsState[nextWordIndex] = self._WORD_STATE_END_OF_THE_SENTENCE
        elif endHasSeparator:
            wordsState[nextWordIndex] = self._WORD_STATE_END
        # import pdb;pdb.set_trace()
        for w, state in [(''.join(cl), state)
                         for cl, state in zip(words, wordsState)]:
            if self.wordCorrection and self.basicWordListLowerAndOther is not None:
                w = self.getWordCorrection(w)
            else:
                w = self.wordTransform(w, bBeginningOfTheSentence)
            if w is None:
                yield "", self._WORD_STATE_END
                continue
            if bBeginningOfTheSentence:
                yield self.TABLE_BEGINNING_OF_THE_SENTENCE, self._WORD_STATE_START_OF_THE_SENTENCE
                bBeginningOfTheSentence = False
                # 如果是句首，并且该单词的第一个字母大写，其他字母小写，则转成小写
                # ?????? 如果是单字母怎么办？
                # if self.caseSensitive and (w[0].isupper() and w[1:].islower()):
                #     w = w.lower()
            # 如果当前最后一个字符是sentence terminatores，则下一个词为句首
            if w != "" and w in self.sentenceTerminators:
                yield self.TABLE_END_OF_THE_SENTENCE, self._WORD_STATE_END_OF_THE_SENTENCE
                bBeginningOfTheSentence = True

            yield w, self._WORD_STATE_NO_END

            if state == self._WORD_STATE_END:
                yield "", self._WORD_STATE_END
            elif state == self._WORD_STATE_END_OF_THE_SENTENCE:
                yield self.TABLE_END_OF_THE_SENTENCE, self._WORD_STATE_END_OF_THE_SENTENCE
                bBeginningOfTheSentence = True


    def testFormat(self):
        words = [
            # '.good',
            # 'good.',
            # 'go----od',
            # 'g-o-o-d',
            # 'good\'',
            # 'go""od',
            # 'good:"good".',
            # 'good."',
            # 'good".',
            'U.S.',
            # 'US.',
            # '\'SNL\'.',
            # '.net',
            # '1213good',
        ]
        for word in words:
            print word, "---->",
            for w, bState in self.format(word):
                print w,
            print
    
    def formatByStdio(self, stdio, coding='utf8'):
        '''
        "Good morning to you, how are you. This is end." 格式化后：
        <s> good morning to you
        how are you </s>
        <s> this is end </s>
        '''
        # wordList = []  #考虑用yield 方式，避免wordlist过大
        bBeginningOfTheSentence = True  # 是否句首

        # 首先读文件，把每行内容中的单词添加到列表里，去掉每个单词左右无效内容
        # 把非空格的空字符转换成2个空格
        compileNonSpaceWhitespace2Sapce = None if self.contextSensitiveMultiWhitespace else re.compile("[\t\r\n]+")
        compileWhitespace = re.compile("\s+") if self.contextSensitiveMultiWhitespace else re.compile("\s?")
        prevWordIsWrap = False
        lastState = self._WORD_STATE_NO_END
        for line in stdio:
            # 1.先根据空白字符切开短语，包括换行符，把所有内容作为一行处理
            line = line.strip()
            # import pdb;pdb.set_trace()
            if len(line) == 0:
                if not prevWordIsWrap and not self.contextSensitiveWrap:
                    prevWordIsWrap = True
                    yield self.TABLE_WRAP
                continue
            if type(line) is not unicode:
                try:
                    line = line.decode(coding, 'ignore')
                except:
                    pass
            # 如果不区分大小写，则全部转换成小写
            if not self.caseSensitive:
                line = line.lower()
            if compileNonSpaceWhitespace2Sapce:
                line = compileNonSpaceWhitespace2Sapce.sub("  ", line)
            words = compileWhitespace.split(line)
            bPrevWhitespace = False
            # import pdb;pdb.set_trace()
            for word in words:
                if len(word) == 0:
                    if not bPrevWhitespace:
                        bPrevWhitespace = True
                        prevWordIsWrap = True
                        yield self.TABLE_WRAP
                    continue
                bPrevWhitespace = False
                for w, bState in self.format(word, bBeginningOfTheSentence):
                    yield w
                    
                    if w != '' and w != self.TABLE_WRAP:
                        prevWordIsWrap = False
                    if bBeginningOfTheSentence and bState == self._WORD_STATE_START_OF_THE_SENTENCE:
                        bBeginningOfTheSentence = False
                    elif bState == self._WORD_STATE_END_OF_THE_SENTENCE:                        
                        if not prevWordIsWrap:
                            prevWordIsWrap = True
                            yield self.TABLE_WRAP
                        bBeginningOfTheSentence = True
                    elif bState == self._WORD_STATE_END:                        
                        if not prevWordIsWrap:
                            prevWordIsWrap = True
                            yield self.TABLE_WRAP
                   
                     
                    lastState = bState
                
                # 解决类似 “&& abc def”，输出"<s> abc def </s>"的问题
                # 正确输出应该是“<s> \n abc def </s>”
                if bBeginningOfTheSentence and lastState != self._WORD_STATE_END_OF_THE_SENTENCE:
                    bBeginningOfTheSentence = False
                    yield self.TABLE_BEGINNING_OF_THE_SENTENCE
                    prevWordIsWrap = True
                    yield self.TABLE_WRAP

            # ???? 对于换行，只换一行作为一行处理，如果换多行，是否也一行处理呢？？？
            # 如果换行不关联上下文，则添加一个空字符
            # wordList.append(self.TABLE_WRAP)
            if not prevWordIsWrap and not self.contextSensitiveWrap:
                prevWordIsWrap = True
                yield self.TABLE_WRAP
        
        if bBeginningOfTheSentence == False and lastState != self._WORD_STATE_END_OF_THE_SENTENCE:
            yield self.TABLE_END_OF_THE_SENTENCE
            


if __name__ == "__main__":
    lp = LanguageParse.getLanguageParse("en")

    # basicWordListPath = "/home/zhaokun/IME/StatisticalLanguageModel/data/new_lm/english_count.txt"
    # basicWordListPath = "/home/zhaokun/文档/test.txt"
    # lp.loadWordList(basicWordListPath)

    # ll = 'Michelle Obama Goes Hollywood; Dr. C.'.split()
    # for word in lp.formatByStdio(ll):
    #     print word,

    lines = [
#         u'''“Hydra’s been played as [being split into] cells, so there’s a lot of them, and as they always say, you cut off one head and many more grow, so in our mind, this was an impressive feat Coulson pulled off, but it doesn’t necessarily mean that Hydra is done,” Loeb observed.
# 
# “Will they ever be done? Their logo’s too cool to ever go away,” Whedon laughed.
#     ''',
#         u'U.S. Inflation',
#         u'Advertisement "Obviously,',
#         u'team…',
#         u'Inc. (NASDAQ:OREX). The current ',
#         u'(NASDAQ:OREX).',
#         u'234(NASDAQ:OREX).',
#         u'of the time. ... Georgia',
#         u'. 45     Good    moring\t\tto\r\nyou', 
#         u'this my soft..',
#         u'iphone Iphone IPhone ipHONE IPHONE the THE The i I THe good Good GOOD GOOd GOod',
#         '''Good morning .
# Marsha is on her way. She called She SSSjSS from the car phone I think. It sounded like the''',
#         '''I succeeded by overcoming my longstanding relationship with weed -- because ''',
#         '''all’—the
# ''',
#         u'#RIM',
#         '''I’m pretty late to the LCD Soundsystem party (a great oversight on my part), but thankfully rectified with Mr James Murphy’s third (and final?) outing of liquid crystal disco. It sounds effortlessly cool, but there’s so much going on, it’s just plain fun to listen to, dance to and do just about anything to – be it the washing up, filling out an application form or being attacked by PANDUHS!''',
#         '''“God—‘Our Father who art in heaven,’ the creator of heaven and Earth in six days—gets the bus?”'''
#         '''“God—‘Our days—gets the bus?”''',
#         '''Hold’em Probablities + Test
# 4 p.m. - DJ No Fame makes another appearance at the kick off of our pool party!''',
#         '''my own.
# 2. In a large pan''',
        '''Tower Jam Concert Series- Brownman - 4:30 p.m. – 7:30 p.m. HSBC Center Plaza'''
    ]
    # for line in lines:
    #     for w in lp.formatByStdio([line]):
    #         print w,
    #     print
    #     print '*'*20

    for w in lp.formatByStdio(lines):
        print w,
    # stdio = open('/home/zhaokun/IME/StatisticalLanguageModel/data/corpus/corpus/ATHEL-Sample Corpus.txt', 'r')
    # for line in lp.formatByStdio(stdio):
    #     print line,

    # print lp.replaceInvalidChars("abcd-@#`'21", ' , ')

    # lp.testFormat()

    #
    # #filepath = r'/home/zhaokun/IME/DicTools/gram_statistics_latin/output/output_webContent/sitroom.html'
    # filepath = r'/home/zhaokun/文档/news.txt'
    # outputpath = os.path.splitext(filepath)[0] + "_add_start_end" +os.path.splitext(filepath)[1]
    # import time
    # st = time.time()
    # with codecs.open(filepath, 'r', 'utf8') as fp:
    #     with codecs.open(outputpath, 'w', 'utf8') as fpOut:
    #         for word in lp.formatByStdio(fp):
    #             if word != "":
    #                 fpOut.write(word)
    #             if word.strip() != "":
    #                 fpOut.write(" ")
    # print time.time()-st
