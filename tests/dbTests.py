#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""
This is the main test routine which will actually connect to a database and try the
tests. 

WARNING: These test perform operations like DROP and should not be used on a database
that's in use.  My tests are done with empty databases, for example.
"""

import DbDmlTest
import os
if os.path.exists('my_conn.py'):
    from my_conn import conn_info
else:
    from connection_info import conn_info

import logging, logging.config

logging.config.fileConfig("xml2ddl.ini")
log = logging.getLogger("xml2ddl")

class DbTests:
    def __init__(self, testList = None):
        self.testList = testList
        
    def pgTests(self, bExec = True):
        try:
            import psycopg
        except:
            print "Missing PostgreSQL support through psycopg"
            return
        
        for strDbms in ['postgres', 'postgres7']:
            self.strDbms = strDbms
            info = conn_info[self.strDbms]
            
            #self.conn = psycopg.connect('dbname=%(dbname)s user=%(user)s password=%(pass)s' % info)
            print info
            self.conn = psycopg.connect('host=%(host)s dbname=%(dbname)s user=%(user)s password=%(pass)s' % info)
            ddt = DbDmlTest.DbDmlTest(self.strDbms, self.testList, log)
            ddt.doTests(self.conn, info['version'], bExec = bExec)
    
    def mySqlTests(self, bExec = True):
        try:
            import MySQLdb
        except:
            print "Missing MySQL support through MySQLdb"
            return
        
        for dbms in ['mysql4']:  # new machine doesn't have mysql 5.0 , 'mysql']:
            self.strDbms = dbms
            info = conn_info[self.strDbms]
        
            self.conn = MySQLdb.connect(host=info['host'], db=info['dbname'], user=info['user'], passwd=info['pass'])
            ddt = DbDmlTest.DbDmlTest(self.strDbms, self.testList, log)
            ddt.doTests(self.conn, info['version'], bExec = bExec)

    def fireBirdTests(self, bExec = True):
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
        ddt.doTests(self.conn, info['version'], bExec = bExec)

    def oracleTests(self, bExec = True):
        try:
            import cx_Oracle
        except:
            print "Missing Oracle support through cx_Oracle"
            return
        
        self.strDbms = 'oracle'
        info = conn_info[self.strDbms]
        self.conn = cx_Oracle.connect(
            info['user'], info['pass'], info['dbname'])
        ddt = DbDmlTest.DbDmlTest(self.strDbms, self.testList, log)
        ddt.doTests(self.conn, info['version'], bExec = bExec)

def doTests(testList = None, bExec = True):
    dbt = DbTests(testList)
    
    dbt.pgTests(bExec = bExec)
    dbt.mySqlTests(bExec = bExec)
    dbt.fireBirdTests(bExec = bExec)
    dbt.oracleTests(bExec = bExec) 
    
if __name__ == "__main__":
    import sys
    
    tests = None
    if len(sys.argv) > 1:
        tests = sys.argv[1]
    
    doTests(tests)
