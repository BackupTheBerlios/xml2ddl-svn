#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import sys

sys.path += ['..']

import diffxml2ddl
import re, glob
from xml.dom.minidom import parse, parseString
from xml2ddl import handleDictionary
import downloadXml
import logging



class DbDmlTest:
    def __init__(self, strDbms, log):
        self.log = log
        self.aFindChanges = diffxml2ddl.FindChanges()
        self.downLoader = downloadXml.createDownloader(strDbms)

        self.aFindChanges.setDbms(strDbms)
        self.strDbms = strDbms
        
    def doTests(self, con, bExec = True):
        
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
        
        outStr = cStringIO()
        self.self.downloader.downloadSchema(conn = con, of = outStr)
        print outStr


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
    
if __name__ == "__main__":
    import dbTests

    dbTests.doTests()
