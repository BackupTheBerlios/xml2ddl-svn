#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import sys

sys.path += ['..']

import diffxml2ddl
import re, glob
from xml.dom.minidom import parse, parseString
from xml2ddl import handleDictionary
import logging


class CreateXmlDynamically:
    def __init__(self):
        # <schema> is always the first and last lines
        self.strXml = [
            "<schema>",
            "</schema>"]
            
    def retCommands(self, params):
        return params
        
    def addAfter(self, strSearch, action):
        params = action.split("|")
        
        re_search = re.compile(strSearch)
        
        toAdd = self.retCommands(params)
        for nIndex, strText in enumerate(self.strXml):
            if re_search.search(strText):
                self.strXml[nIndex + 1:nIndex + 1] = toAdd
                break

    def replace(self, strSearch, action):
        params = action.split("|")
        
        re_search = re.compile(strSearch)
        
        toReplace = self.retCommands(params)
        for nIndex, strText in enumerate(self.strXml):
            if re_search.search(strText):
                self.strXml = self.strXml[:nIndex] + toReplace + self.strXml[nIndex + 1:]
                break
        
    def deleteLines(self, strSearch):
        re_search = re.compile(strSearch)
        self.strXml = filter(lambda x: not re_search.search(x), self.strXml)
        
    def __str__(self):
        return '\n'.join(self.strXml)


class DbDmlTest:
    def __init__(self, strDbms, log):
        self.log = log
        self.aFindChanges = diffxml2ddl.FindChanges()
        self.aFindChanges.setDbms(strDbms)
        self.strDbms = strDbms
        
    def perform(self, xml, action):
        strCommand, strSearch = action[0].split(':')
        
        if strCommand.lower() == 'a':
            xml.addAfter(strSearch, action[1])
        elif strCommand.lower() == 'd':
            xml.deleteLines(strSearch)
        elif strCommand.lower() == 'm':
            xml.replace(strSearch, action[1])
    
    def doTests(self, con, tests, bExec = True):
        #doItTheHardWay(con, tests, bExec)
        
        self.log.info("Logging using the test files")
        self.useTheTestXmls(con, bExec)
        
    def useTheTestXmls(self, con, bExec = True):
        for testFilename in glob.glob('testfiles/test*.xml'):
            doc = parse(testFilename)
            
            bDoIt = True
            for ddl in doc.getElementsByTagName('ddls'):
                dbmsList = ddl.getAttribute('dbms').split(',')
                if ddl.getAttribute('fails').lower() == 'true' and self.strDbms in dbmsList:
                    self.log.info("Skipping test %s" % (testFilename))
                    # Don't bother with tests that'll likely fail
                    bDoIt = False
                    break
            
            if bDoIt:
                self.doOne(con, bExec, testFilename, doc)
    
    def doOne(self, con, bExec, testFilename, doc):
        docBefore = doc.getElementsByTagName('before')[0].firstChild.nextSibling
        handleDictionary(docBefore)
        
        docAfter = doc.getElementsByTagName('after')[0].firstChild.nextSibling
        handleDictionary(docAfter)
        
        empty = parseString('<schema name="public">\n</schema >\n')
        
        ddls = self.aFindChanges.diffTables(empty, docBefore)
        self.execSome(con, ddls, bExec, "(%s) %s: empty->before" % (self.strDbms, testFilename))
        self.aFindChanges.reset()
    
        ddls = self.aFindChanges.diffTables(docBefore, docAfter)
        self.execSome(con, ddls, bExec, "(%s) %s: before->after" % (self.strDbms, testFilename))
        self.aFindChanges.reset()
        
        ddls = self.aFindChanges.diffTables(docAfter, empty)
        self.execSome(con, ddls, bExec, "(%s) %s: after->empty" % (self.strDbms, testFilename))
        self.aFindChanges.reset()
            
    
    def execSome(self, con, ddls, bExec, strContext):
        bPrintAll = False
        for nIndex, ret in enumerate(ddls):
            if bExec:
                cursor = con.cursor()
                try:
                    if self.log.isEnabledFor('DEBUG'):
                        self.log.debug('%s SQL: "%s"' % (strContext, ret[1]))
                    
                    cursor.execute(ret[1])
                except Exception, e:
                    strError = str(e)
                    self.log.warning("Failed with error: %s" % strError)
                    self.log.warning('%s SQL: "%s"' % (strContext, ret[1]))
                    
                    if strError.lower().find('already exists') != -1:
                        self.log.warning("Plunging on ahead")
                    else:
                        sys.exit(-1)
                
                con.commit()
                cursor.close()
    
    def doItTheHardWay(self, con, tests, bExec = True):
        xml = CreateXmlDynamically()
        
        strNew = str(xml)
        for test in tests:
            strOld = strNew
            
            self.aFindChanges.setDbms(self.strDbms)
            dbmsList = test[0]
            strTitle = test[1]
            strActions = test[2]
            
            for action in strActions:
                perform(xml, action)
            
            strNew = str(xml)
            fo = open("new.xml", "w")
            fo.write(strNew)
            fo.close()
            
            fo = open("old.xml", "w")
            fo.write(strOld)
            fo.close()
            
            rets = self.aFindChanges.diffFiles('old.xml', 'new.xml')
            
            bPrintAll = True
            if not bPrintAll:
                sys.stdout.write(".")
                
            for nIndex, ret in enumerate(rets):
                if bPrintAll:
                    print "'%s' %s" % (ret[0], ret[1])
                
                if bExec:
                    cursor = con.cursor()
                    try:
                        cursor.execute(ret[1])
                    except Exception, e:
                        print "Failed", e
                        if not bPrintAll:
                            print 'SQL: "%s"' % (ret[1])
                    
                    con.commit()
                    cursor.close()
            
    
        sys.stdout.write('\n')
        
if __name__ == "__main__":
    import dbTests

    dbTests.doTests()
