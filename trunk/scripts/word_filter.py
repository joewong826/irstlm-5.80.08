#!/usr/bin/python
#-*- coding=utf-8 -*-



import codecs
import re
import sys
import os
from optparse import OptionParser  


'''
-v FILE [-n NUMBER] [-c str] [-l] -i FILE or [< FILE] -o FILE or [> FILE]
过滤文件中指定列的内容
-v 指定一个文件，包含有效的词，没包含的词将过滤掉
-n 指定行，过滤文件中的指定行
-c 指定输入文件编码， 默认utf-8，使用-i时该参数无效
-l 小写模式
-i 输入
-o 输出
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
            encoding='utf_8_sig'     
        elif header[:2] == codecs.BOM_LE:
            encoding='utf_16_le'
        elif header[:2] == codecs.BOM_BE:
            encoding='utf_16_be'
        return encoding

class WordFilter:
    def __init__(self):
        self.validWordList = {}
        self.lower = False
        pass
    def setLower(self, lower):
        '''是否设置为小写模式，lower为True和False'''
        self.lower = lower
    def loadValidWordList(self, filepath):
        encoding = getfileencode(filepath)
        with codecs.open(filepath, 'r', encoding) as fp:
            for line in fp:
                word = (line.split()+[''])[0].strip()
                if self.lower:
                    self.validWordList[word.lower()] = 0;
                else:
                    self.validWordList[word] = 0;
                
    def run(self, stdin, stdout, col=0, inputcoding='utf-8'):
        lineno = 0
        stdout.write('DICTIONARY\n')
        writelinecount = 0
        while True:
            lineno+=1            
            try:         
                #如果命令行使用<传入时，即stdin是sys.stdin时，需要由coding来指定编码
                line = stdin.readline()
                if line is None or len(line) == 0:
                    break
                if type(line) != unicode:
                    try:
                        line = line.decode(inputcoding, 'ignore')
                    except:
                        pass
                
                if self.lower:
                    line = line.lower()
                
                cols = line.split()
                if col > len(cols):
                    continue
                word = cols[col-1]
                if not self.validWordList.has_key(word):
                    continue               
                stdout.write(line)
                writelinecount+=1
                
            except Exception, e:                
                pass
            except KeyboardInterrupt:
                break
            #if lineno == 5:
                #break

def analyzeParams(args):
    parser = OptionParser(usage="%prog -v FILE [-n NUMBER] [-c str] [-l] -i FILE or [< FILE] -o FILE or [> FILE]"
                      , version="%prog 1.0")    

    #add_option用来加入选项，action是有store，store_true，store_false等，dest是存储的变量，default是缺省值，help是帮助提示     
    parser.set_description(u'过滤文件中指定列的内容');
    parser.add_option("-v", "--validwordlist", dest="validwordlist",metavar="FILE", action="store"
                      , help=u'有效词语列表文件，只把文件第一列作为词语')  
    parser.add_option("-n", "--col", dest="col", metavar="int"
                      , help=u'指定解析文件的列数，从1开始', default=1)    
    parser.add_option("-c", "--coding", dest="coding", metavar="string"
                      , help=u'指定输入文件编码， 默认utf-8，使用-i时该参数无效', default="utf-8")    
    parser.add_option("-l", "--lower", dest="lower", action="store_true"
                      , help=u'按小写方式解析文件', default=False)     
    parser.add_option("-i", "--input", dest="inputPath",metavar="FILE", action="store"
                      , help=u'输入文件路径， 也可使用< FILE')  
    parser.add_option("-o", "--output", dest="outputpath",metavar="FILE", action="store"
                      , help=u'输出文件路径， 也可使用> FILE')   
    
    (opt, args) = parser.parse_args(args)

    if opt.validwordlist is None or not os.path.exists(opt.validwordlist):
        print "未指定-v参数, -h查看帮助";
        return;
    
    stdin = sys.stdin
    stdout = sys.stdout
    if opt.inputPath is not None:
        fileencoding = getfileencode(opt.inputPath)
        stdin = codecs.open(opt.inputPath, 'r', fileencoding)
    if opt.outputpath is not None:
        stdout = codecs.open(opt.outputpath, 'w', 'utf-8')
     
    wordFilter = WordFilter()
    wordFilter.setLower(opt.lower)
    wordFilter.loadValidWordList(opt.validwordlist)
    wordFilter.run(stdin, stdout, opt.col, opt.coding)
    
    stdin.close()
    stdout.close()



if __name__ == "__main__":
    analyzeParams(sys.argv)