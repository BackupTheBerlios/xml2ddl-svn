#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

import re, os
from xml.dom.minidom import parse, parseString

__author__ = "Scott Kirkwood (scott_kirkwood at berlios.com)"
__keywords__ = ['XML', 'DML', 'SQL', 'Databases', 'Agile DB', 'ALTER', 'CREATE TABLE', 'GPL']
__licence__ = "GNU Public License (GPL)"
__longdescr__ = ""
__url__ = 'http://xml2dml.berlios.de'
__version__ = "$Revision: 0.1 $"

import os,sys

sys.path += ['./tests']
if os.path.exists('tests/my_conn.py'):
    from my_conn import conn_info
else:
    from connect_info import conn_info

"""
MySQL uses:
SHOW DATABASES (1 column)
SHOW TABLES (1 column)
DESCRIBE <table>;
Columns Field  | Type             | Null | Key | Default | Extra       
The "Extra" field records special information about columns. 
If you have selected the "auto_increment" functionality for a column, for example, that would show up in the "Extra" field when doing a "describe".
SHOW INDEX FROM tbl_name
"""

class DownloadXml:
    def __init__(self):
        self.strDbms = 'postgres'
        
    def downloadPg(self):
        try:
            import psycopg
        except:
            print "Missing PostgreSQL support through psycopg"
            return
        
        self.strDbms = 'postgres'
        info = conn_info[self.strDbms]
        self.conn = psycopg.connect('dbname=%(dbname)s user=%(user)s password=%(pass)s' % info)
        self.cursor = self.conn.cursor()
        
        tables = self.getTablesPg()
        for strTableName in tables:
            curTable = {
                'name' : strTableName,
                'columns' : []
            }
            desc = self.getTableComment(strTableName)
            if desc:
                curTable['desc'] = desc
            
            indexes = self.getTableIndexes(strTableName)
            
            for colRow in self.getTableColumns(strTableName):
                (strColumnName, type, attlen, precision, attnotnull, default) = colRow
                curCol = {
                    'name' : str(strColumnName),
                    'type' : str(type),
                }   
                if attlen:
                    curCol['size'] = attlen
                
                if precision:
                    curCol['precision'] = precision
                
                if attnotnull:
                    curCol['null'] = 'no'
                
                if default:
                    curCol['default'] = default
                
                strComment = self.getColumnComment(strTableName, strColumnName)
                if strComment:
                    curCol['desc'] = strComment
                
                curTable['columns'].append(curCol)
            
            self.dumpTable(curTable)
    
    def dumpTable(self, info):
        of = sys.stdout
        
        of.write('  <table %s>\n' % (self.doAttribs(info, ['name', 'desc'])))
        for col in info['columns']:
            of.write('    <column %s/>\n' % (self.doAttribs(col, ['name', 'type', 'size', 'precision', 'null', 'default', 'desc'])))
        
        of.write('  </table>\n')
    
    def doAttribs(self, attribs, nameList):
        ret = []
        for name in nameList:
            if name in attribs:
                ret.append('%s="%s"' % (name, attribs[name]))
        
        return ' '.join(ret)
    
    def getTablesPg(self):
        """ Returns the list of tables as a array of strings """
        
        self.cursor.execute("select tablename from pg_tables where schemaname not in ('pg_catalog', 'information_schema')")
        return [x[0] for x in self.cursor.fetchall() ]
    
    def getTableColumns(self, strTable):
        """ Returns column in this format
            (strColumnName, strColType, nColSize, nColPrecision, bNotNull, strDefault)
        """
        strSql = """
            SELECT pa.attnum, pa.attname, pt.typname, pa.atttypmod, pa.attnotnull, pa.atthasdef, pc.oid
            FROM pg_attribute pa, pg_type pt, pg_class pc
            WHERE pa.atttypid = pt.oid 
            AND pa.attrelid = pc.oid
            AND pa.attisdropped = 'f'
            AND pc.relname = %s
            AND pc.relkind = 'r'
            ORDER BY attnum"""
        self.cursor.execute(strSql, [strTable])
        rows = self.cursor.fetchall()
        
        specialCols = ['cmax', 'cmin', 'xmax', 'xmin', 'oid', 'ctid', 'tableoid']
        fixNames = {
            'int4' : 'integer',
            'int'  : 'integer',
            'bool' : 'boolean',
            'float8' : 'double precision',
            'int8' : 'bigint',
            'serial8' : 'bigserial',
            'serial4' : 'serial',
            'float4' : 'real',
            'int2' : 'smallint',
        }
        ret = []
        for row in rows:
            attnum, name, type, attlen, attnotnull, atthasdef, clasoid = row
            if name not in specialCols:
                if type in fixNames:
                    type = fixNames[type]
                
                attlen, precision = self.decodeLength(type, attlen)
                    
                default = None
                if atthasdef:
                    default = self.getColumnDefault(clasoid, attnum)
                ret.append((name, type, attlen, precision, attnotnull, default))
            
        return ret
    
    def getColumnDefault(self, clasoid, attnum):
        """ Returns the default value for a comment or None """
        strSql = "SELECT adsrc FROM pg_attrdef WHERE adrelid = %s AND adnum = %s"
        self.cursor.execute(strSql, [clasoid, attnum])
        rows = self.cursor.fetchall()
        if not rows:
            return None
        
        strDefault = rows[0][0]
        
        strDefault = strDefault.replace('::text', '')
        return strDefault
    
    def getTableComment(self, strTableName):
        """ Returns the comment as a string """
        
        strSql = """SELECT description FROM pg_description pd, pg_class pc 
            WHERE pc.relname = %s AND pc.relkind = 'r' AND pd.objoid = pc.oid AND pd.objsubid = 0"""
        self.cursor.execute(strSql, [strTableName])
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0]
        
        return None

    def getColumnComment(self, strTableName, strColumnName):
        """ Returns the comment as a string """
        
        strSql = """SELECT description FROM pg_description pd, pg_class pc, pg_attribute pa
            WHERE pc.relname = %s AND pc.relkind = 'r' 
            AND pd.objoid = pc.oid AND pd.objsubid = pa.attnum AND pa.attname = %s AND pa.attrelid = pc.oid"""
        
        self.cursor.execute(strSql, [strTableName, strColumnName])
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0]
        
        return None

    def getTableIndexes(self, strTableName):
        """ Returns 
            (strIndexName, [strColumns,], bIsUnique, bIsPrimary, bIsClustered)
            or []
        """
        strSql = """SELECT pc.relname, pi.indkey, indisunique, indisprimary, indisclustered
            FROM pg_index pi, pg_class pc, pg_class pc2
            WHERE pc2.relname = %s
            AND pc2.relkind = 'r'
            AND pc2.oid = pi.indrelid
            AND pc.oid = pi.indexrelid
            """
        self.cursor.execute(strSql, [strTableName])
        rows = self.cursor.fetchall()
        
        ret = []
        
        if not rows:
            return ret
        
        for row in rows:
            (strIndexName, strColumns, bIsUnique, bIsPrimary, bIsClustered) = row
            colList = self.fetchTableColumnsNamesByNums(strTableName, strColumns.split())
            ret += [strIndexName, colList, bIsUnique, bIsPrimary, bIsClustered]
        
        print "Indexes, ", ret
        
        return ret
    
    def fetchTableColumnsNamesByNums(self, strTableName, nums):
        strSql = """
            SELECT pa.attnum, pa.attname
            FROM pg_attribute pa, pg_class pc
            WHERE pa.attrelid = pc.oid
            AND pa.attisdropped = 'f'
            AND pc.relname = %s
            AND pc.relkind = 'r'
            AND pa.attnum in (%s)
            """
        self.cursor.execute(strSql, [strTableName] + nums)
        rows = self.cursor.fetchall()
        print rows
        
    def decodeLength(self, type, atttypmod):
        # gleamed from http://www.postgresql-websource.com/psql713/source-format_type.htm
        VARHDRSZ = 4
        
        if type == 'varchar':
            return (atttypmod - VARHDRSZ, None)
        
        if type == 'numeric':
            atttypmod -= VARHDRSZ
            return  ( (atttypmod >> 16) & 0xffff, atttypmod & 0xffff)
        
        if type == 'varbit' or type == 'bit':
            return (atttypmod, None)
        
        return (None, None)
        
    def getTableConstraints(self, strTable):
        strSql = 'select conname, contype from pg_constraint where conrelid = pg_class.oid'
if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser()
                  
    (options, args) = parser.parse_args()

    cd = DownloadXml()
    cd.downloadPg()
