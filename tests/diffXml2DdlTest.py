import sys, re

sys.path += ['..']

import diffxml2ddl
from xml2ddl import handleDictionary
import glob
from xml.dom.minidom import parse, parseString

aFindChanges = diffxml2ddl.FindChanges()

def cleanString(strString):
    strString = re.sub(r'\s\s+', ' ', strString)
    strString = re.sub(r'\r', '', strString)
    strString= re.sub(r'\n', ' ', strString)
    return strString

def doOne(strDbms, testFilename, docBefore, docAfter, docDdl):
    aFindChanges.setDbms(strDbms)
    ret = aFindChanges.diffDocuments(docBefore, docAfter)
    
    docDdlList = docDdl.getElementsByTagName('ddl')
    for nIndex, ddlGood in enumerate(docDdlList):
        strGood = cleanString(ddlGood.firstChild.nodeValue)
        
        if nIndex < len(ret):
            strRet = cleanString(ret[nIndex][1])
            if strGood != strRet:
                print "%s (%s): Expected '%s' need to add\n\t<ddl>%s</ddl>" % (testFilename, strDbms, strGood, strRet)
        else:
            print "%s (%s): Expected '%s' got nothing instead"  % (testFilename, strDbms, strGood)
    if len(ret) > len(docDdlList):
        for retItem in ret[len(docDdlList):]:
            print "%s (%s): Need to add\n\t<ddl>%s</ddl>" % (testFilename, strDbms, retItem[1])
        

def doTests():
    for testFilename in glob.glob('testfiles/test*.xml'):
        doc = parse(testFilename)
        docBefore = doc.getElementsByTagName('before')[0].firstChild.nextSibling
        handleDictionary(docBefore)
        
        docAfter = doc.getElementsByTagName('after')[0].firstChild.nextSibling
        handleDictionary(docAfter)
        
        theList = ['postgres', 'postgres7', 'mysql', 'firebird']
        docDdls = doc.getElementsByTagName('ddls')
        for docDdl in docDdls:
            if docDdl.hasAttribute('dbms'):
                strDbms = docDdl.getAttribute('dbms')
                curList = strDbms.split(',')
                for aDbms in curList:
                    theList.remove(aDbms)
            else:
                continue
                
            for strDbms in curList:
                doOne(strDbms, testFilename, docBefore, docAfter, docDdl)

        docDdls = doc.getElementsByTagName('ddls')
        for docDdl in docDdls:
            if docDdl.hasAttribute('dbms'):
                continue
                
            for strDbms in theList:
                doOne(strDbms, testFilename, docBefore, docAfter, docDdl)

if __name__ == "__main__":
    doTests()