# Speed tests

from CheckNumbers import getCheckNumber
from random import randint
import os
import time

if os.path.exists('my_conn.py'):
    from my_conn import conn_info
else:
    from connect_info import conn_info

strCreateTable = 'CREATE TABLE %s (a INTEGER, b INTEGER, c VARCHAR(100))'
strInsertT1 = 'INSERT INTO t1 (a, b, c) VALUES (%s, %s, %s)'
strInsertT2 = 'INSERT INTO t1 (a, b, c) VALUES (%s, %s, %s)'
strSelect1 = "SELECT count(*), avg(b) FROM t2 WHERE b>=%s AND b < %s"
strSelect2 = "SELECT count(*), avg(b) FROM t2 WHERE c LIKE %s"

class SpeedTests:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.times = {}

    def createTestTable(self, strTable):
        global strCreateTable
        
        try: 
            self.cursor.execute(strCreateTable % strTable)
        except Exception, e:
            print e
            self.conn.rollback()
            self.cursor.execute('DROP TABLE %s' % strTable)
            self.cursor.execute(strCreateTable % strTable)
    
        self.conn.commit()
    
    def emptyTable(self, strTable):
        self.cursor.execute("DELETE FROM %s" % strTable)
        self.conn.commit()
        
    def doTimeRandEtc(self, nSize):
        info = { }
        for a in range(nSize):
            nRand = randint(1000, 999999)
            
            info['a'] = a + 1
            info['b'] = nRand
            info['c'] = getCheckNumber(nRand)
            x = strInsert % info 
        
    def dropTestTable(self, strTable):
        global strDrop
        
        try:
            self.cursor.execute("DROP TABLE %s" % strTable)
        except Exception, e:
            print e
    
        self.conn.commit()

    def doInsertTest1(self, bCommitEach, nRange):
        global strInsert
        
        info = [0, 0, '']
        for a in range(nRange):
            nRand = randint(1000, 999999)
            
            info[0] = a + 1
            info[1] = int(nRand)
            info[2] = getCheckNumber(nRand)
            self.cursor.execute(strInsertT1, info)
            if bCommitEach:
                self.conn.commit()
                
        self.conn.commit()

    def doInsertTest2(self, nRange):
        global strInsert
        
        info = [0, 0, '']
        for a in range(nRange):
            nRand = randint(1000, 999999)
            
            info[0] = a + 1
            info[1] = nRand
            info[2] = getCheckNumber(nRand)
            self.cursor.execute(strInsertT2, info)
                
        self.conn.commit()

    def doSelectTest1(self, nRange):
        """SELECT count(*), avg(b) FROM t2 WHERE b>=0 AND b<1000;
            SELECT count(*), avg(b) FROM t2 WHERE b>=100 AND b<1100;
            """
        info = [0, 0]
        nStart = 0
        for nIndex in range(nRange):
            info[0] = nStart
            info[1] = nStart + 1000
            nStart += 100
            self.cursor.execute(strSelect1, info)

    def doSelectTest2(self, nRange):
        """
        SELECT count(*), avg(b) FROM t2 WHERE c LIKE '%one%';
        SELECT count(*), avg(b) FROM t2 WHERE c LIKE '%two%';
        """
        info = ['']
        nStart = 0
        for nIndex in range(nRange):
            info[0] = getCheckNumber(nIndex + 1)
            nStart += 100
            self.cursor.execute(strSelect2, info)
        
    def createIndexes(self):
        self.cursor.execute('CREATE INDEX i2a ON t2(a)')
        self.cursor.execute('CREATE INDEX i2b ON t2(b)') 
        self.conn.commit()
        
    def start(self, testDesc):
        self.nStart = time.clock()
        self.testDesc = testDesc
    
    def end(self):
        nNow = time.clock()
        print "%s: %.2f sec" % (self.testDesc, nNow - self.nStart)
        if self.dbms not  in self.times:
            self.times[self.dbms] = [nNow - self.nStart]
        else:
            self.times[self.dbms].append(nNow - self.nStart)
        
        self.testNames.append(self.testDesc)
        
    def printTimes(self):
        
        fo = open("results.html", "w")
        fo.write("<html><body>\n")
        fo.write("<table>\n")
        
        fo.write("<tr><th></th>\n")
        for key, val in self.times.items():
            fo.write("<th>%s</th>\n" % (key))
        fo.write("</tr>\n")
    
    
        for nIndex in range(6):
            fo.write("<tr>\n")
            fo.write("<td>%s</td>\n" % (self.testNames[nIndex]))
            
            for key, val in self.times.items():
                fo.write("<td>%.1f</td>\n" % (val[nIndex] * 1000))
    
            fo.write("</tr>\n")
        
        fo.write("</table>\n")
        fo.write("</body></html>\n")
        fo.close()
        
    def doPg(self):
        import psycopg
        
        self.dbms = 'PostgreSQL'
        info = conn_info['postgres']
        self.conn = psycopg.connect('dbname=%(dbname)s user=%(user)s password=%(pass)s' % info)
        self.cursor = self.conn.cursor()
        
        self.doTests()
        
    def doMySql(self):
        global strCreateTable
        import MySQLdb

        self.dbms = 'MySQL'
        info = conn_info['mysql']
        self.conn = MySQLdb.connect(db=info['dbname'], user=info['user'], passwd=info['pass'])
        self.cursor = self.conn.cursor()
        
        self.doTests()

    def doMySqlInno(self):
        global strCreateTable
        import MySQLdb

        strAppendInno = ' TYPE=InnoDB'
        strCreateTable += strAppendInno
        
        self.dbms = 'MySQL InnoDB'
        info = conn_info['mysql']
        self.conn = MySQLdb.connect(db=info['dbname'], user=info['user'], passwd=info['pass'])
        self.cursor = self.conn.cursor()
        
        self.doTests()
        strCreateTable = strCreateTable.replace(strAppendInno, '')


    def doFirebird(self):
        global strSelect1, strSelect2, strInsertT1, strInsertT2
        import kinterbasdb

        self.dbms = 'firebird'
        print kinterbasdb.paramstyle
        
        info = conn_info['firebird']
        self.conn = kinterbasdb.connect(
            dsn='localhost:%s' % info['dbname'],
            user = info['user'], 
            password = info['pass'])
        self.cursor = self.conn.cursor()

        strSelect1 = strSelect1.replace("%s", "?")
        strSelect2 = strSelect2.replace("%s", "?")
        strInsertT1 = strInsertT1.replace("%s", "?")
        strInsertT2 = strInsertT2.replace("%s", "?")

        self.doTests()
        strSelect1 = strSelect1.replace("?", "%s")
        strSelect2 = strSelect2.replace("?", "%s")
        strInsertT1 = strInsertT1.replace("?", "%s")
        strInsertT2 = strInsertT2.replace("?", "%s")
    
    def doTests(self):
        self.testNames = []
        
        self.createTestTable('t1')
        self.createTestTable('t2')
        
        nRange = 1000
        self.start("%d insert with commits" % (nRange))
        self.doInsertTest1(True, nRange)
        self.end()
        
        self.emptyTable('t1')

        nRange = 2500
        self.start("%d insert no commits" % (nRange))
        self.doInsertTest2(nRange)
        self.end()
    
        nRange = 2000
        self.start("%d Selects no index" % (nRange))
        self.doSelectTest1(nRange)
        self.end()

        nRange = 2000
        self.start("%d Selects on a string comparison" % (nRange))
        self.doSelectTest2(nRange)
        self.end()

        self.start("Create indexes")
        self.createIndexes()
        self.end()
        
        nRange = 5000
        self.start("%d Selects with index" % (nRange))
        self.doSelectTest1(nRange)
        self.end()
        
        self.dropTestTable('t1')
        self.dropTestTable('t2')
    
st = SpeedTests()
st.doPg()
#st.doMySql()
#st.doMySqlInno()
st.doFirebird()
st.printTimes()
