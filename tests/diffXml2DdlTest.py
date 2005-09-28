#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

""" You can safely run these set of tests, there is no coneection
made with a database. Basically, this just performs string
manipulation
"""

import sys, re, os

from xml2ddl import diffxml2ddl
from xml2ddl import xml2html
from xml2ddl import xml2ddl
from xml2ddl.DdlCommonInterface import g_dbTypes
import glob
from xml.dom.minidom import parse, parseString, getDOMImplementation
import xml.dom
import logging, logging.config

logging.config.fileConfig("xml2ddl.ini")
log = logging.getLogger("xml2ddl.diffXml2DdlTest")

nPassed = 0
nFailed = 0
aFindChanges = diffxml2ddl.DiffXml2Ddl()

def cleanString(strString):
    strString = re.sub(r'\s\s+', ' ', strString)
    strString = re.sub(r'\r', '', strString)
    strString= re.sub(r'\n', ' ', strString)
    return strString

def outputHtml(testFilename, doc):
    import codecs
    
    xml2htm = xml2html.Xml2Html()
    impl = getDOMImplementation()
    newDoc = impl.createDocument(None, "schema", None)
    newDoc.documentElement.appendChild(doc)
    lines = xml2htm.outputHtml(newDoc)
    newFilename = testFilename.replace('.xml', '.html')
    of = codecs.open(newFilename, "wb", 'ISO-8859-1')
    strOut = '\n'.join(lines)
    of.write(strOut)
    of.close()
    
    
def doOne(strDbms, testFilename, docBefore, docAfter, docDdl, bFails):
    global nPassed, nFailed
    
    log.info("Doing test for dbms '%s'" % (strDbms))
    
    aFindChanges.setDbms(strDbms)
    ret = aFindChanges.diffTables(docBefore, docAfter)
    
    outputHtml(testFilename, docAfter)
    
    docDdlList = docDdl.getElementsByTagName('ddl')
    expected = []
    got = []
    info = []
    
    for nIndex, ddlGood in enumerate(docDdlList):
        strGood = cleanString(ddlGood.firstChild.nodeValue)
        
        if ret and nIndex < len(ret):
            strRet = cleanString(ret[nIndex][1])
            if strGood != strRet:
                if not bFails:
                    nFailed += 1
                    expected.append("    %s" % (strGood))
                    got.append("    <ddl>%s</ddl> <!-- %s -->" % (ret[nIndex][1], ret[nIndex][0], ))
                else:
                    # this test is supposed to fail, probably to be fixed later (essentially the test is skipped)
                    #info.append("Was expected to fail")
                    pass
            else:
                info.append('%s'  % (strRet))
                    
                nPassed += 1
        elif not bFails:
            nFailed += 1
            expected.append("    Expected '%s' got nothing instead"  % (strGood))
            
    if ret and docDdlList and len(ret) > len(docDdlList):
        for retItem in ret[len(docDdlList):]:
            if not bFails:
                got.append("  <ddl>%s</ddl>" % (retItem[1]))
    
    if len(got) > 0:
        strMess = '%s (%s)' % (testFilename, strDbms)
        log.critical(strMess)
        log.critical("Expected:")
        log.critical('\n'.join(expected))
        log.critical("Got:")
        log.critical('\n'.join(['    <ddl>%s</ddl>' % (ddl[1]) for ddl in ret]))

    if len(expected) > 0:
        strMess = '%s (%s)' % (testFilename, strDbms)
        log.critical(strMess)
        log.critical("Expected:")
        log.critical('\n'.join(expected))
        log.critical("Got: nothing instead")
        
    if len(info) > 0:
        log.info('\n'.join(info))
    
def doTests():
    for testFilename in glob.glob('testfiles/test*.xml'):
        doc = parse(testFilename)
        log.info("Doing test %s" % (testFilename))
        docBefore = doc.getElementsByTagName('before')[0].firstChild.nextSibling
        xml2ddl.handleDictionary(docBefore)
        
        docAfter = doc.getElementsByTagName('after')[0].firstChild.nextSibling
        xml2ddl.handleDictionary(docAfter)
        
        theList = g_dbTypes[:]
        docDdls = doc.getElementsByTagName('ddls')
        for docDdl in docDdls:
            if docDdl.hasAttribute('dbms'):
                curList = docDdl.getAttribute('dbms').split(',')
                for aDbms in curList:
                    if aDbms in theList:
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

    if nFailed:
        print "Failed %d test(s), passed %d test(s)" % (nFailed, nPassed)
    else:
        print "Passed %d tests" % (nPassed,)
    
if __name__ == "__main__":
    doTests()
