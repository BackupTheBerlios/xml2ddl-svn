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

tests = [
    (None, 'Add table', [ 
            ('A:<schema>', '<table name="table1">|</table>'), 
            ('A:<table', '<columns>|</columns>'),
            ('A:<column', '<column name="col1" type="integer"/>'),
        ],
    ),
    (None, 'Add column', [
            ('A:<col', '<column name="col2" type="varchar" size="60"/>'),
        ],
    ),
    (None, 'Modify column', [
            ('M:col2', '<column name="col2" type="varchar" size="255"/>'),
        ],
    ),
    (None, 'Add a table comment', [
            ('M:<table', '<table name="table1" desc="Table Comment">'),
        ],
    ),
    (None, 'Add a column comment', [
            ('M:col1', '<column name="col1" type="integer" desc="The key?"/>'),
        ],
    ),
    (None, 'Change a column comment', [
            ('M:col1', '<column name="col1" type="integer" desc="Yes the key"/>'),
        ],
    ),
    (None, 'Swap column order (should make no diff)', [
            ('D:col1', ),
            ('A:col2', '<column name="col1" type="integer" desc="Yes the key"/>'),
        ],
    ),
    (None, 'Add a column with decimal', [
            ('A:col2', '<column name="col3" type="decimal" size="15" precision="2" desc="Decimal value"/>'),
        ],
    ),
    (None, 'Change decimal value', [
            ('M:col3', '<column name="col3" type="decimal" size="16" precision="3" desc="Decimal value"/>'),
        ],
    ),
    (None, 'Add Index', [
            ('A:</column>', '<indexes>|<index columns="col1,col2">|</indexes>'),
        ],
    ),
    (None, 'Remove column', [
            ('D:col2', ),
        ],
    ),
    (None, 'Drop table(s)', [ 
            ('D:table',), ('D:column',),
        ],
    ),
    
    # Two tables
    (None, 'Add table', [ 
            ('A:<schema>', '<table name="table1">|</table>'), 
            ('A:<table', '<columns>|</columns>'),
            ('A:<columns', '<column name="col1" type="integer" null="no" key="1"/>'),
            ('A:<column name="col1"', '<column name="col2" type="integer"/>'),
        ],
    ),
    (None, 'Add table Another Table', [ 
            ('A:</table>', '<table name="table2">|</table>'), 
            ('A:table2', '<columns id="t2">|</columns> <!-- t2 -->'),
            ('A:id="t2"', '<column name="col4" type="integer" null="no" key="1"/>'),
            ('A:<column name="col4"', '<column name="col5" type="integer"/>'),
            ('A:<!-- t2', '<relations id="t3">|</relations>'),
            ('A:id="t3"', '<relation column="col4" table="table1" fk="col1"/>'),
        ],
    ),
    
    (None, 'Drop all table(s)', [ 
            ('D:table',), ('D:column',),
        ],
    ),
]
bExec = True

class DbTests:

    def pgTests(self):
        try:
            import psycopg
        except:
            print "Missing PostgreSQL support through psycopg"
            return
        
        self.strDbms = 'postgres'
        info = conn_info[self.strDbms]
        self.conn = psycopg.connect('dbname=%(dbname)s user=%(user)s password=%(pass)s' % info)
        ddt = DbDmlTest.DbDmlTest(self.strDbms, log)
        ddt.doTests(self.conn, tests, bExec)

    def mySqlTests(self):
        try:
            import MySQLdb
        except:
            print "Missing MySQL support through MySQLdb"
            return
        
        self.strDbms = 'mysql'
        info = conn_info[self.strDbms]
    
        self.conn = MySQLdb.connect(db=info['dbname'], user=info['user'], passwd=info['pass'])
        ddt = DbDmlTest.DbDmlTest(self.strDbms, log)
        ddt.doTests(self.conn, tests, bExec)

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
    
        ddt = DbDmlTest.DbDmlTest(self.strDbms, log)
        ddt.doTests(self.conn, tests, bExec)
        

def doTests():
    dbt = DbTests()
    
    dbt.pgTests()
    dbt.mySqlTests()
    dbt.fireBirdTests()
    
if __name__ == "__main__":
    doTests()
