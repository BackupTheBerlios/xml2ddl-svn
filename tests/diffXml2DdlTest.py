import sys, re

sys.path += ['..']

import diffxml2ddl
from xml2ddl import handleDictionary
import glob
from xml.dom.minidom import parse, parseString
import logging, logging.config


logging.config.fileConfig("xml2ddl.ini")
log = logging.getLogger("xml2ddl.diffXml2DdlTest")

nPassed = 0
aFindChanges = diffxml2ddl.FindChanges()

def cleanString(strString):
    strString = re.sub(r'\s\s+', ' ', strString)
    strString = re.sub(r'\r', '', strString)
    strString= re.sub(r'\n', ' ', strString)
    return strString

def doOne(strDbms, testFilename, docBefore, docAfter, docDdl, bFails):
    global nPassed
    
    aFindChanges.setDbms(strDbms)
    ret = aFindChanges.diffTables(docBefore, docAfter)
    
    docDdlList = docDdl.getElementsByTagName('ddl')
    for nIndex, ddlGood in enumerate(docDdlList):
        strGood = cleanString(ddlGood.firstChild.nodeValue)
        
        if ret and nIndex < len(ret):
            strRet = cleanString(ret[nIndex][1])
            if strGood != strRet:
                if not bFails:
                    strMess = "%s (%s): Expected '%s' need to add\n\t<ddl>%s</ddl>" % (testFilename, strDbms, strGood, strRet)
                    log.critical(strMess)
            else:
                if log.isEnabledFor('INFO'):
                    strMess = "%s (%s): passed '%s'"  % (testFilename, strDbms, strRet)
                    log.info(strMess)
                    
                nPassed += 1
        elif not bFails:
            strMess = "%s (%s): Expected '%s' got nothing instead"  % (testFilename, strDbms, strGood)
            log.critical(strMess)
            
    if ret and docDdlList and len(ret) > len(docDdlList):
        for retItem in ret[len(docDdlList):]:
            if not bFails:
                strMess = "%s (%s): Need to add from rule %s\n\t<ddl>%s</ddl>" % (testFilename, strDbms, retItem[0], retItem[1])
                log.critical(strMess)
    

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
                curList = docDdl.getAttribute('dbms').split(',')
                for aDbms in curList:
                    theList.remove(aDbms)
            else:
                continue
            
            bFails = False
            if docDdl.hasAttribute('fails') and docDdl.getAttribute('fails').lower() == 'true':
                bFails = True
            
            for strDbms in curList:
                doOne(strDbms, testFilename, docBefore, docAfter, docDdl, bFails)

        docDdls = doc.getElementsByTagName('ddls')
        for docDdl in docDdls:
            if docDdl.hasAttribute('dbms'):
                continue
                
            bFails = False
            if docDdl.hasAttribute('fails') and docDdl.getAttribute('fails').lower() == 'true':
                bFails = True
                
            for strDbms in theList:
                doOne(strDbms, testFilename, docBefore, docAfter, docDdl, bFails)

        doc.unlink()

    print "Passed %d tests" % (nPassed,)
if __name__ == "__main__":
    doTests()
