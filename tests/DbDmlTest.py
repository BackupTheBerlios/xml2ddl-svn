#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""
Use dbTest to run this.
"""

import sys

sys.path += ['..']
# Import Psyco if available
try:
    import psyco
    psyco.full()
except ImportError:
    pass
from xml2ddl import diffxml2ddl
import re, glob
import os.path
from xml.dom.minidom import parse, parseString
from xml2ddl.xml2ddl import handleDictionary
from xml2ddl import downloadXml
from cStringIO import StringIO
import logging

class DbDmlTest:
    def __init__(self, strDbms, testList, log):
        self.log = log
        self.testList = testList
        self.aFindChanges = diffxml2ddl.DiffXml2Ddl()

        self.aFindChanges.setDbms(strDbms)
        self.strDbms = strDbms
        
    def doTests(self, con, version, bExec = True):
        self.log.info("Logging using the test files")
        self.useTheTestXmls(con, version, bExec)
        
    def useTheTestXmls(self, con, version, bExec = True):
        options = {
            'getfunctions' : True,
            'getviews'     : True,
            'getrelations' : True,
            'getindexes'   : True,
            'tables'       : ['table1', 'table2', 'table3', 'Table with spaces', 'new_table_name'],
            'views'        : ['myview', 'newview',  'oldview', 'view2'],
            'functions'    : ['myfunc', 'newfunc', 'func2'],
            'version'      : version,
        }
        self.downLoader = downloadXml.createDownloader(self.strDbms, con, info = { 'version' : version }, options = options)
        
        for testFilename in glob.glob('testfiles/test*.xml'):
            if self.testList != None and len(self.testList) > 0 and os.path.basename(testFilename) not in self.testList:
                continue
            
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
        
        print "Test file:", testFilename
        
        empty = parseString('<schema name="public">\n</schema>\n')
        
        ddls = self.aFindChanges.diffTables(empty, docBefore)
        self.execSome(con, ddls, bExec, "(%s) %s: empty->before" % (self.strDbms, testFilename))
        self.aFindChanges.reset()
    
        ddls = self.aFindChanges.diffTables(docBefore, docAfter)
        self.execSome(con, ddls, bExec, "(%s) %s: before->after" % (self.strDbms, testFilename))
        self.aFindChanges.reset()
        
        outStr = StringIO()
        self.downLoader.downloadSchema(of = outStr)
        docFromDb = None
        try:
            docFromDb = parseString(outStr.getvalue())
        except Exception, e:
            strErr = "Problem parsing: (%s)'" % (str(e),) + outStr.getvalue() + "'"
            self.log.warning(strErr)
        
        self.aFindChanges.reset()
        ddls = self.aFindChanges.diffTables(docAfter, docFromDb)
        
        if len(ddls) > 0:
            ddlType = ddls[0][0].lower()
        
        if len(ddls) > 0 and ddlType != 'add view' and ddlType != 'add function':
            print "They are different (%s)" % (self.strDbms)
            self.log.warning("Downloaded:\n" + outStr.getvalue())
            self.log.warning("Expected:\n" + docAfter.toxml())
            for ddl in ddls:
                self.log.warning(ddl)
        else:
            self.log.info("Passed download check")
        
        outStr.close()
        self.aFindChanges.reset()

        #~ if testFilename.endswith('test-01a.xml'):
            #~ sys.exit(-1)
        
        ddls = self.aFindChanges.diffTables(docAfter, empty)
        self.execSome(con, ddls, bExec, "(%s) %s: after->empty" % (self.strDbms, testFilename))
        self.aFindChanges.reset()
        
    def execSome(self, con, ddls, bExec, strContext):
        bPrintAll = False
        for nIndex, ret in enumerate(ddls):
            if bExec:
                cursor = con.cursor()
                try:
                    if ret:
                        self.log.info('%s SQL: "%s"' % (strContext, ret[1]))
                        
                        cursor.execute(ret[1].encode('ISO-8859-1'))
                        con.commit()
                except Exception, e:
                    strError = str(e)
                    self.log.warning("Failed with error: %s" % strError)
                    self.log.warning('%s SQL: "%s"' % (strContext, ret[1]))
                    
                    if strError.lower().find('already exists') != -1 or strError.lower().find('does not exist') != -1:
                        self.log.warning("Plunging on ahead")
                    else:
                        sys.exit(-1)
                
                cursor.close()
    
if __name__ == "__main__":
    import dbTests

    dbTests.doTests(bExec = True)
