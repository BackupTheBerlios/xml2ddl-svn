#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import DbDmlTest
import os
if os.path.exists('my_conn.py'):
    from my_conn import conn_info
else:
    from connect_info import conn_info

import logging, logging.config

logging.config.fileConfig("xml2ddl.ini")
log = logging.getLogger("xml2ddl")

bExec = True

class DbTests:
    def __init__(self, testList = None):
        self.testList = testList
        
    def pgTests(self):
        try:
            import psycopg
        except:
            print "Missing PostgreSQL support through psycopg"
            return
        
        self.strDbms = 'postgres'
        info = conn_info[self.strDbms]
        self.conn = psycopg.connect('dbname=%(dbname)s user=%(user)s password=%(pass)s' % info)
        ddt = DbDmlTest.DbDmlTest(self.strDbms, self.testList, log)
        ddt.doTests(self.conn, bExec)
    
    def mySqlTests(self):
        try:
            import MySQLdb
        except:
            print "Missing MySQL support through MySQLdb"
            return
        
        self.strDbms = 'mysql'
        info = conn_info[self.strDbms]
    
        self.conn = MySQLdb.connect(db=info['dbname'], user=info['user'], passwd=info['pass'])
        ddt = DbDmlTest.DbDmlTest(self.strDbms, self.testList, log)
        ddt.doTests(self.conn, bExec)

    def fireBirdTests(self):
        try:
            import kinterbasdb
        except:
            print "Missing Firebird support through kinterbasdb"
            return
        
        self.strDbms = 'firebird'
        info = conn_info[self.strDbms]
        self.conn = kinterbasdb.connect(
            dsn='localhost:%s' % info['dbname'],
            user = info['user'], 
            password = info['pass'])
    
        ddt = DbDmlTest.DbDmlTest(self.strDbms, self.testList, log)
        ddt.doTests(self.conn, bExec)

def doTests(testList = None):
    dbt = DbTests(testList)
    
    dbt.pgTests()
    dbt.mySqlTests()
    #~ dbt.fireBirdTests()
    
if __name__ == "__main__":
    import sys
    
    tests = None
    if len(sys.argv) > 1:
        tests = sys.argv[1]
    
    doTests(tests)
