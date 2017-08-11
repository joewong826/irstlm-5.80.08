#!/usr/bin/env python
# -*- coding=utf-8 -*-

import os
import re
import copy

# 语言信息对应的json文件名
DEFAULT_LANGUAGE_INFO_FILE_NAME = 'languageinfo'
# 程序所在目录
mainDir = os.path.split(os.path.realpath(__file__))[0]
# 自动在程序所在目录下查找validchars文件
DEFAULT_LANGUAGE_INFO_FILE_PATH = os.path.join(mainDir, DEFAULT_LANGUAGE_INFO_FILE_NAME)


class LanguageList:
    ''' 语言列表，包括语言名字，语言描述，语言locale， 语言中文描述
    ["Chinese",  "中文",  "zh",  "中文"],
    '''
    _LANGUAGE_LIST_INDEX_MAX = 4
    (_LANGUAGE_LIST_INDEX_NAME,
     _LANGUAGE_LIST_INDEX_DESCRIPTION,
     _LANGUAGE_LIST_INDEX_LOCALE,
     _LANGUAGE_LIST_INDEX_CHINESE_DESCRIPTION) = range(_LANGUAGE_LIST_INDEX_MAX)

    def __init__(self, languagelist):
        if not isinstance(languagelist, list):
            raise "error: LanguageList.__init__ param is list."
        self.languageMap = {}
        for ll in languagelist:
            if len(ll) < self._LANGUAGE_LIST_INDEX_MAX:
                raise 'error: LanguageList is 4 col, eg: ["Chinese",  "中文",  "zh",  "中文"]'
            self.languageMap[ll[self._LANGUAGE_LIST_INDEX_LOCALE].lower()] = ll

    def hasLocale(self, locale):
        locale = locale.lower()
        return self.languageMap.has_key(locale)

    def _get(self, locale, index):
        locale = locale.lower()
        ll = self.languageMap.get(locale, None)
        if ll is not None:
            return ll[index]
        return None

    def getName(self, locale):
        return self._get(locale, self._LANGUAGE_LIST_INDEX_NAME)

    def getDescription(self, locale):
        return self._get(locale, self._LANGUAGE_LIST_INDEX_DESCRIPTION)

    def getZhDescription(self, locale):
        return self._get(locale, self._LANGUAGE_LIST_INDEX_CHINESE_DESCRIPTION)

    def getLoacles(self):
        return self.languageMap.iterkeys()


class LanguageCharsetInfo:
    KEY_LOCALE = "locale"
    # 有效字符，只存放区间
    KEY_VALIDCHARS = "validchars"
    # 字符替换，一般用于标点的替换
    KEY_WORD_REPLACE = "wordReplace"
    # 整句结尾的符号
    KEY_SENTENCE_TERMINATORS = "sentenceTerminators"
    # 符号前需要空格
    KEY_SYMBOLS_PRECEDED_BY_SPACE = "symbolsPrecededBySpace"
    # 符号后需要空格
    KEY_SYMBOLS_FOLLOWED_BY_SPACE = "symbolsFollowedBySpace"
    # 聚合符号，该字符前不需要前面的空格，一般用来区别symbolsPrecededBySpace
    KEY_SYMBOLS_CLUSTERING_TOGETHER = "symbolsClusteringTogether"
    # 词语连接符，一般为'和-
    KEY_WORD_CONNECTORS = "wordConnectors"
    # 词语分隔符，一般为标点符号
    KEY_WORD_SEPARATORS = "wordSeparators"
    # 单词间存在多个空白字符时，是否进行上下文关联（建立ngram关系）
    KEY_CONTEXT_SENSITIVE_MULTI_WHITESPACE = "contextSensitiveMultiWhitespace"
    # 单词间存在换行符时，是否进行上下文关联（建立ngram关系）
    KEY_CONTEXT_SENSITIVE_WRAP = "contextSensitiveWrap"
    # 区分大小写
    KEY_CASE_SENSITIVE = "caseSensitive"
    # 单词纠错
    KEY_WORD_CORRECTION = "wordCorrection"
    # 基本词表中不存在的单词,转换成小写形式
    KEY_UNKNOWN_WORD_TO_LOWER = "unknownWordToLower";

    def __init__(self, locale):
        self.locale = locale
        self.charsetInfo = {
            self.KEY_LOCALE: locale,
            # 有效字符区间
            self.KEY_VALIDCHARS: (),#((u'a', u'z'), (u'A', u'Z'), )
            self.KEY_WORD_REPLACE: (), # ((u'‘’', u'\''),  )
            self.KEY_SENTENCE_TERMINATORS: "",
            self.KEY_SYMBOLS_PRECEDED_BY_SPACE: "",
            self.KEY_SYMBOLS_FOLLOWED_BY_SPACE: "",
            self.KEY_SYMBOLS_CLUSTERING_TOGETHER: "",
            self.KEY_WORD_CONNECTORS: "",
            self.KEY_WORD_SEPARATORS: "",
            self.KEY_CONTEXT_SENSITIVE_MULTI_WHITESPACE: False,
            self.KEY_CONTEXT_SENSITIVE_WRAP: False,
            self.KEY_CASE_SENSITIVE: True,
            self.KEY_WORD_CORRECTION: True,
            self.KEY_UNKNOWN_WORD_TO_LOWER: True,
        }

    def setLocale(self, locale):
        self.locale = locale
        self.charsetInfo[self.KEY_LOCALE] = locale

    def keys(self):
        return self.charsetInfo.iterkeys()

    def get(self, key):
        return self.charsetInfo.get(key, None)

    def gets(self):
        return self.charsetInfo

    def _setWordReplace(self, charsetMap):
        info = charsetMap.get(self.KEY_WORD_REPLACE, None)
        if info is None:
            return
        self.charsetInfo[self.KEY_WORD_REPLACE] = tuple(tuple(i) for i in info)
    def _setValidchars(self, charsetMap):
        charsRegion = charsetMap.get(self.KEY_VALIDCHARS, None)
        if charsRegion is None:
            return

        validCharsRegion = set()
        for line in charsRegion:
            line = line.strip()
            if len(line) == 0:
                continue
            start, end = '', ''
            if line.find('-') >= 0:
                start, end = [c.strip() for c in line.split('-')]
            else:
                start = end = line.strip()
            try:
                start = int(start, 16)
                end = int(end, 16)
            except:
                raise 'locale [%d] valid chars error: [%s] to int faild' % (self.locale, line)
                continue
            if start > end:
                raise 'locale [%d] valid chars error: [%s] first < second' % (self.locale, line)
                continue
            start = unichr(start)
            end = unichr(end)

            validCharsRegion.add((start, end))

        self.charsetInfo[self.KEY_VALIDCHARS] = tuple(validCharsRegion)

    def _set(self, charsetMap, key):
        value = charsetMap.get(key, None)
        if value is not None:
            self.charsetInfo[key] = value

    def set(self, charsetMap):
        self._setValidchars(charsetMap)
        self._setWordReplace(charsetMap)

        self._set(charsetMap, self.KEY_SENTENCE_TERMINATORS)
        self._set(charsetMap, self.KEY_SYMBOLS_PRECEDED_BY_SPACE)
        self._set(charsetMap, self.KEY_SYMBOLS_FOLLOWED_BY_SPACE)
        self._set(charsetMap, self.KEY_SYMBOLS_CLUSTERING_TOGETHER)
        self._set(charsetMap, self.KEY_WORD_CONNECTORS)
        self._set(charsetMap, self.KEY_WORD_SEPARATORS);
        self._set(charsetMap, self.KEY_CONTEXT_SENSITIVE_MULTI_WHITESPACE)
        self._set(charsetMap, self.KEY_CONTEXT_SENSITIVE_WRAP)
        self._set(charsetMap, self.KEY_CASE_SENSITIVE)
        self._set(charsetMap, self.KEY_WORD_CORRECTION)
        self._set(charsetMap, self.KEY_UNKNOWN_WORD_TO_LOWER)

    @classmethod
    def getDefault(self, locale):
        return LanguageCharsetInfo(locale)

    def toString(self):
        logs = []

        logs.append("[%s]:" % self.locale)
        for key in self.charsetInfo.keys():
            logs.append("\t%s: %s" % (key, self.charsetInfo.get(key)))

        return '\n'.join(logs)


class LanguageInfo:
    _KEY_LANGUAGE_LIST = "language_list"
    _KEY_LANGUAGE_CHARSET = "language_charset"
    _KEY_LANGUAGE_CHARSET_LOCALE_DEFAULT = "default"
    _KEY_BASE = "base"

    _mLanguageList = None
    _mLanguageCharset = None

    def __init__(self, jsonpath=None):
        if self._mLanguageCharset is None:
            if jsonpath is None:
                self.reload()
            else:
                self.reload(jsonpath)

    def reload(self, jsonpath=DEFAULT_LANGUAGE_INFO_FILE_PATH):
        self._mLanguageCharset = {}
        if not os.path.exists(jsonpath):
            raise IOError("error: Language info file not exists.....")
        jsoninfo = None
        # import pdb;pdb.set_trace()
        with open(jsonpath) as fp:
            jsoninfo = eval(fp.read().decode('utf8'))
        if jsoninfo is None:
            return

        self._mLanguageList = LanguageList(jsoninfo.get(self._KEY_LANGUAGE_LIST, None))

        languageCharset = jsoninfo.get(self._KEY_LANGUAGE_CHARSET, None)
        if languageCharset is None:
            return

        for locale in languageCharset.iterkeys():
            self._addCharset(languageCharset, locale)

    def _addCharset(self, languageCharsetJson, locale):
        if self._mLanguageCharset.has_key(locale):
            return
        infoJson = languageCharsetJson.get(locale, {})
        if self._KEY_LANGUAGE_CHARSET_LOCALE_DEFAULT == locale:
            baseCharset = LanguageCharsetInfo.getDefault(locale)
        else:
            baseLocale = infoJson.get(self._KEY_BASE, self._KEY_LANGUAGE_CHARSET_LOCALE_DEFAULT)
            if not self._mLanguageCharset.has_key(baseLocale):
                self._addCharset(languageCharsetJson, baseLocale)
            baseCharset = self._mLanguageCharset.get(baseLocale)
        currentCharset = copy.deepcopy(baseCharset)
        currentCharset.set(infoJson)
        currentCharset.setLocale(locale)
        self._mLanguageCharset[locale] = currentCharset

    def getLanguageList(self):
        return self._mLanguageList;

    def getLanguageCharsetInfo(self, locale):
        return self._mLanguageCharset.get(locale, None)

    def toString(self):
        logs = []
        logs.append("languages:")
        for locale in self._mLanguageList.getLoacles():
            logs.append("%s\t%s\t%s\t%s" % (locale,
                                            self._mLanguageList.getName(locale),
                                            self._mLanguageList.getZhDescription(locale),
                                            self._mLanguageList.getDescription(locale)))
        logs.extend([""] * 3)
        for locale, value in self._mLanguageCharset.iteritems():
            logs.append("%s: " % locale)
            for key in value.keys():
                logs.append("\t%s: %s" % (key, value.get(key)))

        return '\n'.join(logs)


if __name__ == "__main__":
    li = LanguageInfo()
    print li.toString()
    lci = li.getLanguageCharsetInfo('en')
    print lci.toString()
    print li.getLanguageCharsetInfo('default').toString()
