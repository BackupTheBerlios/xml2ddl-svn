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
    try:
        from connect_info import conn_info
    except:
        print "Can't find conn_info"


"""
INFORMATION_SCHEMA....
http://developer.mimer.com/documentation/html_92/Mimer_SQL_Engine_DocSet/Data_dic_views2.html#wp1118541

MySQL uses:
SHOW DATABASES (1 column)
SHOW TABLES (1 column)
DESCRIBE <table>;
Columns Field  | Type             | Null | Key | Default | Extra       
The "Extra" field records special information about columns. 
If you have selected the "auto_increment" functionality for a column, for example, that would show up in the "Extra" field when doing a "describe".
SHOW INDEX FROM tbl_name
"""

def getSeqName(strTableName, strColName):
    return '%s_%s_seq' % (strTableName.strip(), strColName.strip())

class PgDownloader:
    """ Silly me, I didn't know about INFORMATION_SCHEMA """
    def __init__(self):
        self.strDbms = 'postgres'
        
    def connect(self, info):
        try:
            import psycopg
        except:
            print "Missing PostgreSQL support through psycopg"
            return
        
        self.conn = psycopg.connect('dbname=%(dbname)s user=%(user)s password=%(pass)s' % info)
        self.cursor = self.conn.cursor()
        #self.doSomeTests()
        
    def useConnection(self, con):
        self.conn = con
        self.cursor = self.conn.cursor()
        
    def doSomeTests(self):
        sql = "select tablename from pg_tables where tablename in %s"
        inList = (('sample', 'companies', 'table1'), )
        self.cursor.execute(sql, inList)
        print self.cursor.fetchall()
        
        sql = "select tablename from pg_tables where tablename = %(tbl)s"
        inDict = {  'tbl' : 'sample' }
        self.cursor.execute(sql, inDict)
        print self.cursor.fetchall()

        sys.exit(-1)

    def getTables(self, tableList):
        """ Returns the list of tables as a array of strings """
        
        strQuery = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES where TABLE_SCHEMA not in ('pg_catalog', 'information_schema') and TABLE_NAME NOT LIKE 'pg_%' AND TABLE_TYPE = 'BASE TABLE'"
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if rows:
            return [x[0] for x in rows]
        
        return []

    def getTableColumns(self, strTable):
        """ Returns column in this format
            (nColIndex, strColumnName, strColType, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, bNotNull, strDefault, auto_increment)
        """
        strSql = """
            SELECT ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_PRECISION_RADIX, NUMERIC_SCALE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION"""
        self.cursor.execute(strSql, [strTable])
        rows = self.cursor.fetchall()
        
        ret = []
        fixNames = {
            'character varying' : 'varchar',
        }
        for row in rows:
            attnum, name, type, size, numsize, numprecradix, numprec, attnotnull, default = row
            if type in fixNames:
                type = fixNames[type]
            
            if not size and numprecradix == 10:
                size = numsize
            
            if attnotnull.lower() == "yes":
                attnotnull = False
            else:
                attnotnull = True
            
            if default:
                # remove the '::text stuff
                default = default.replace('::text', '')
            
            bAutoIncrement = False
            if default == "nextval('%s')" % (getSeqName(strTable, name)):
                default = ''
                bAutoIncrement = True
                
            ret.append((name, type, size, numprec, attnotnull, default, bAutoIncrement))
            
        return ret
    
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
            colList = self._fetchTableColumnsNamesByNums(strTableName, strColumns.split())
            ret.append((strIndexName, colList, bIsUnique, bIsPrimary, bIsClustered))
        
        return ret

    def getTableRelations(self, strTableName):
        """ Returns 
            (strConstraintName, colName, fk_table, fk_columns, confupdtype, confdeltype)
            or []
        """
        strSql = """SELECT pcon.conname, pcon.conkey, pcla2.relname, pcon.confkey, pcon.confupdtype, pcon.confdeltype
            FROM pg_constraint pcon, pg_class pcla, pg_class pcla2
            WHERE pcla.relname = %s
            AND pcla.relkind = 'r'
            AND pcon.conrelid = pcla.oid
            AND pcon.confrelid = pcla2.oid
            AND pcon.contype = 'f'
            """
        self.cursor.execute(strSql, [strTableName])
        rows = self.cursor.fetchall()
        
        ret = []
        
        if not rows:
            return ret
        
        for row in rows:
            (strConstraintName, cols, fk_table, fkeys, chUpdateType, chDelType) = row
            cols = cols[1:-1]
            colList = self._fetchTableColumnsNamesByNums(strTableName, cols.split(','))
            fkeys = fkeys[1:-1]
            fkColList = self._fetchTableColumnsNamesByNums(fk_table, fkeys.split(','))
            ret.append((strConstraintName, colList, fk_table, fkColList, chUpdateType, chDelType))
        
        return ret

    def _fetchTableColumnsNamesByNums(self, strTableName, nums):
        ret = []
        
        for num in nums:
            strSql = """
                SELECT pa.attname
                FROM pg_attribute pa, pg_class pc
                WHERE pa.attrelid = pc.oid
                AND pa.attisdropped = 'f'
                AND pc.relname = %s
                AND pc.relkind = 'r'
                AND pa.attnum = %s
                ORDER BY pa.attnum
                """
            
            self.cursor.execute(strSql, [strTableName] + [num])
            rows = self.cursor.fetchall()
            ret.append(rows[0][0])
                
        return ret
        
    def _decodeLength(self, type, atttypmod):
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

    def getViews(self):
        """ Returns the list of views as a array of strings """
        
        strQuery =  "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES where TABLE_SCHEMA not in ('pg_catalog', 'information_schema') and TABLE_NAME NOT LIKE 'pg_%' AND TABLE_TYPE = 'VIEW'"
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if rows:
            return [x[0] for x in rows]
        
        return []

    def getViewDefinition(self, strViewName):
        strQuery = "SELECT VIEW_DEFINITION FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME = %s"
        self.cursor.execute(strQuery, [strViewName])
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0]
        
        return []

    def getFunctions(self):
        """ Returns functions """
        strQuery = """SELECT SPECIFIC_NAME
        FROM INFORMATION_SCHEMA.ROUTINES 
        WHERE SPECIFIC_SCHEMA not in ('pg_catalog', 'information_schema')
        AND ROUTINE_NAME not in ('_get_parser_from_curcfg', 'ts_debug', 'pg_file_length', 'pg_file_rename')
        AND external_language != 'C' """
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if rows:
            return [x[0] for x in rows]
        
        return []

    def getFunctionDefinition(self, strSpecifiName):
        """ Returns (routineName, parameters, return, language, definition) """
        
        strQuery = "SELECT ROUTINE_NAME, ROUTINE_DEFINITION, DATA_TYPE, EXTERNAL_LANGUAGE from INFORMATION_SCHEMA.ROUTINES WHERE SPECIFIC_NAME = %s"
        self.cursor.execute(strQuery, [strSpecifiName])
        rows = self.cursor.fetchall()
        if not rows:
            return (None, None, None, None)
        
        
        strRoutineName, strDefinition, retType, strLanguage = rows[0]

        strQuery = "SELECT PARAMETER_MODE, DATA_TYPE, PARAMETER_NAME from INFORMATION_SCHEMA.PARAMETERS WHERE SPECIFIC_NAME = %s ORDER BY ORDINAL_POSITION"
        self.cursor.execute(strQuery, [strSpecifiName])
        params = []
        repList = []
        for nIndex, row in enumerate(self.cursor.fetchall()):
            paramMode, dataType, paramName = row
            strParam = dataType
            if paramName:
                strParam += ' ' + paramName
            params.append(strParam)
            repList.append(r'\s+(\w+) ALIAS FOR \$%d;' % (nIndex + 1))

        # Cleanup definition by removing the stuff we added.
        strDefinition = re.compile('|'.join(repList), re.DOTALL | re.MULTILINE).sub('', strDefinition)
        strDefinition = re.compile(r'\s*DECLARE\s+BEGIN', re.DOTALL | re.MULTILINE).sub('BEGIN', strDefinition)
        
        return (strRoutineName, params, retType, strLanguage, strDefinition)

class MySqlDownloader:
    def __init__(self):
        self.strDbms = 'mysql'
    
    def connect(self, info):
        try:
            import MySQLdb
        except:
            print "Missing MySQL support through MySQLdb"
            return
        self.conn = MySQLdb.connect(db=info['dbname'], user=info['user'], passwd=info['pass'])
        self.cursor = self.conn.cursor()

    def useConnection(self, conn):
        self.conn = conn
        self.cursor = self.conn.cursor()
        
    def getTables(self, tableList):
        """ Returns the list of tables as a array of strings """
        
        strQuery = "SHOW TABLES"
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        ret = []
        for row in rows:
            if row[1] == 'BASE TABLE':
                ret.append(row[0])
        
        return ret
    
    def getTableColumns(self, strTable):
        """ Returns column in this format
            (strColumnName, strColType, nColSize, nColPrecision, bNotNull, strDefault, auto_increment)
        """
        re_size_prec = re.compile(r'(\w+)\((\d+),\s*(\d+)\)')
        re_size = re.compile(r'(\w+)\((\d+)\)')
        
        strQuery = "SHOW COLUMNS FROM `%s`" % (strTable)
        self.cursor.execute(strQuery)
        fullcols = self.cursor.fetchall()
        ret = []
        
        bAutoIncrement = False 
        for col in fullcols:
            (name, type, bNotNull, key, strDefault, extra) = col
            nColSize = None
            nColPrecision = None
            if extra == 'auto_increment':
                bAutoIncrement = True
            else:
                bAutoIncrement = False
            
            match = re_size_prec.match(type)
            if match:
                newType = match.group(1)
                nColSize = int(match.group(2))
                nColPrecision = int(match.group(3))
            else:
                match = re_size.match(type)
                if match:
                    newType = match.group(1)
                    nColSize = int(match.group(2))
                    nColPrecision = None
                else:
                    newType = type
            
            if newType == "int":
                newType = 'integer'
                nColSize = None
                nColPrecision = None
                
            bNotNull = not (bNotNull == "YES")
            ret.append( (name, newType, nColSize, nColPrecision, bNotNull, strDefault, bAutoIncrement) )
        return ret
    
    def getTableComment(self, strTableName):
        """ Returns the comment as a string -- humm, no way to get the table comment? """
        
        return None

    def getColumnComment(self, strTableName, strColumnName):
        """ Returns the comment as a string """
        strQuery = "SHOW FULL COLUMNS FROM `%s`" % (strTableName)
        self.cursor.execute(strQuery)
        fullcols = self.cursor.fetchall()
        strColumnName = strColumnName.lower()
        for col in fullcols:
            (Field, Type, Collation, Null, Key, Default, Extra, Privileges, Comment) = col
            if Field.lower() == strColumnName:
                return Comment
        
        return None

    def getTableIndexes(self, strTableName):
        """ Returns 
            (strIndexName, [strColumns,], bIsUnique, bIsPrimary, bIsClustered)
            or []
        """
        strQuery = 'show index from `%s`' % (strTableName)
        self.cursor.execute(strQuery)
        indexes = self.cursor.fetchall()
        ret = []
        keyMap = {}
        for index in indexes:
            (Table, Non_unique, Key_name, Seq_in_index, Column_name, Collation, Cardinality, Sub_part, Packed, Null, Index_type, Comment) = index
            if Key_name == 'PRIMARY':
                bIsPrimary = True
            else:
                bIsPrimary = False
            
            if Non_unique == 0:
                bIsUnique = False
            else:
                bIsUnique = True
            
            if Key_name in keyMap:
                #FIX: TODO: make sure the keys are in order.
                keyMap[Key_name][1].append(Column_name)
            else:
                keyMap[Key_name] = (Key_name, [Column_name], bIsUnique, bIsPrimary, Packed)
                ret.append( keyMap[Key_name] )
        
        return ret

    def getTableRelations(self, strTableName):
        """ Returns 
            (strConstraintName, colName, fk_table, fk_columns, confupdtype, confdeltype))
            or []
        """
        re_ref = re.compile(r'\s*CONSTRAINT\s+`(\w+)`\s+FOREIGN KEY\s+\(([^)]+)\)\s+REFERENCES\s+`(\w+)`\s+\(([^)]+)\)( ON DELETE (?:[A-Z]+))?( ON UPDATE (?:[A-Z]+))?')
        """ex. CONSTRAINT `fk_category_id` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`),"""
        
        # TODO
        delType = ''
        updateType = ''
        
        strQuery = 'SHOW CREATE TABLE `%s`' % (strTableName)
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        ret = []
        for line in rows[0][1].split('\n'):
            match = re_ref.match(line)
            if match:
                myCols = [ str.strip()[1:-1] for str in match.group(2).split(',') ]
                fkCols = [ str.strip()[1:-1] for str in match.group(4).split(',') ]
                delType = self.mapMySqlOnSomething(match.group(5))
                updateType = self.mapMySqlOnSomething(match.group(6))
                ret.append( ( match.group(1), myCols, match.group(3), fkCols, delType, updateType) )
        
        return ret
        
    def mapMySqlOnSomething(self, strStr):
        if strStr == None:
            return None
        
        if strStr.endswith('CASCADE'):
            return 'c'
        
        if strStr.endswith('RESTRICT'):
            return 'r'
        
        if strStr.endswith('NULL'):
            return 'n'
            
        if strStr.endswith('DEFAULT'):
            return 'd'
        
        return 'a'
        
    def getViews(self):
        strQuery = "SHOW TABLES"
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        ret = []
        for row in rows:
            if row[1] == 'VIEW':
                ret.append(row[0])
                
        return ret
        
    def getViewDefinition(self, strViewName):
        strQuery = "SHOW CREATE VIEW `%s`" % (strViewName)
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if rows:
            ret = rows[0][1]
            # ext CREATE VIEW test.v AS select 1 AS `a`,2 AS `b`
            reGetDef = re.compile('CREATE VIEW [a-zA-Z0-9_$`\.]+ AS (.*)')
            match = reGetDef.match(ret)
            if match:
                return match.group(1)
            else:
                print "Didn't match %s" % (ret)
            
            return ret
        
        return []
        
    def getFunctions(self):
        """ Returns functions """
        strQuery = "SHOW FUNCTION STATUS"
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if rows:
            return [x[1] for x in rows]
        
        return []

    def getFunctionDefinition(self, strSpecifiName):
        """ Returns (routineName, parameters, return, language, definition) """
        
        strQuery = "SHOW CREATE FUNCTION `%s`" % (strSpecifiName)
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if not rows:
            return (None, None, None, None)
        
        
        strCreate = rows[0][2]
        # ex.CREATE FUNCTION `test`.`sales_tax`(subtotal real) RETURNS real BEGIN    RETURN subtotal * 0.06;END
        re_createFunc = re.compile(r'\s* CREATE \s+ FUNCTION \s+ ([\w`\.-]*) \s* \( ([^)]*) \) \s+ RETURNS \s+ (\w+) \s+ (.*)', re.DOTALL | re.MULTILINE | re.VERBOSE)
        match = re_createFunc.match(strCreate)
        if match:
            strParams = match.group(2).split(',')
            strReturns = match.group(3)
            strLanguage = ''
            strDefinition = match.group(4)
        else:
            print "'%s'" % (strCreate)
            strParams = []
            strReturns = ''
            strLanguage = ''
            strDefinition = strCreate
            
        return (strSpecifiName, strParams, strReturns, strLanguage, strDefinition)
    
class FbDownloader:
    def __init__(self):
        self.strDbms = 'firebird'
        
    def connect(self, info):
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
        self.cursor = self.conn.cursor()
        
    def useConnection(self, con):
        self.conn = con
        self.cursor = self.conn.cursor()
        
    def getTables(self, tableList):
        """ Returns the list of tables as a array of strings """
        
        strQuery =  "SELECT RDB$RELATION_NAME FROM RDB$RELATIONS WHERE RDB$SYSTEM_FLAG=0 AND RDB$VIEW_SOURCE IS NULL;"
        self.cursor.execute(strQuery)
        return [x[0].strip() for x in self.cursor.fetchall() ]
    
    def getTableColumns(self, strTable):
        """ Returns column in this format
            (nColIndex, strColumnName, strColType, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, bNotNull, strDefault, auto_increment)
        """
        strSql = """
            SELECT RF.RDB$FIELD_POSITION, RF.RDB$FIELD_NAME, RDB$FIELD_TYPE, F.RDB$FIELD_LENGTH, 
            RDB$FIELD_PRECISION, RDB$FIELD_SCALE, RF.RDB$NULL_FLAG, RF.RDB$DEFAULT_SOURCE, F.RDB$FIELD_SUB_TYPE
            FROM RDB$RELATION_FIELDS RF, RDB$FIELDS F
            WHERE RF.RDB$RELATION_NAME = ?
            AND RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
            ORDER BY RF.RDB$FIELD_POSITION;"""
        self.cursor.execute(strSql, [strTable])
        rows = self.cursor.fetchall()
        
        ret = []
        fixNames = {
            'character varying' : 'varchar',
        }
        
        # TODO auto_increment
        bAutoIncrement = False
        for row in rows:
            attnum, name, nType, size, numsize, scale, attnull, default, sub_type = row
            
            if scale and scale < 0:
                scale = -scale
            
            if not size and numprecradix == 10:
                size = numsize
            
            strType = self.convertTypeId(nType)
                
            if sub_type == 1:
                strType = 'numeric'
            elif sub_type == 2:
                strType = 'decimal'
            
            if not size and numsize > 0:
                size = numsize
                numsize = None
                
            if default:
                # Remove the 'DEFAULT ' part of the SQL
                default = default.replace('DEFAULT ', '')
            
            if self.hasAutoincrement(strTable, name):
                bAutoIncrement = True
            else:
                bAutoIncrement = False
                
            ret.append((name.strip(), strType, size, scale, attnull, default, bAutoIncrement))
            
        return ret

    def convertTypeId(self, nType):
        types = {
            261: 'blob',
            14 : 'char',    
            40 : 'cstring',
            11 : 'd_float',
            27 : 'double',
            10 : 'float',
            16 : 'int64',
            8  : 'integer',
            9  : 'quad',
            7  : 'smallint',
            12 : 'date',
            13 : 'time',
            35 : 'timestamp',
            37 : 'varchar',
        }
        
        strType = ''
        if nType in types:
            strType = types[nType]
            if nType not in [14, 40, 37]:
                size = None
        else:
            print "Uknown type %d" % (nType)
        
        return strType

    def hasAutoincrement(self, strTableName, strColName):
        strSql = "SELECT RDB$GENERATOR_NAME FROM RDB$GENERATORS WHERE UPPER(RDB$GENERATOR_NAME)=UPPER(?);"
        self.cursor.execute(strSql, [getSeqName(strTableName, strColName)[0:31]])
        rows = self.cursor.fetchall()
        if rows:
            return True
        
        return False
        
    def getTableComment(self, strTableName):
        """ Returns the comment as a string """
        
        strSql = "SELECT RDB$DESCRIPTION FROM RDB$RELATIONS WHERE RDB$RELATION_NAME=?;"
        self.cursor.execute(strSql, [strTableName])
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0]
        
        return None

    def getColumnComment(self, strTableName, strColumnName):
        """ Returns the comment as a string """
        
        strSql = """SELECT RDB$DESCRIPTION 
            FROM RDB$RELATION_FIELDS
            WHERE RDB$RELATION_NAME = ? AND RDB$FIELD_NAME = ?"""
        
        self.cursor.execute(strSql, [strTableName, strColumnName])
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0]
        
        return None

    def getTableIndexes(self, strTableName):
        """ Returns 
            (strIndexName, [strColumns,], bIsUnique, bIsPrimary, bIsClustered)
            or []
            Warning the Primary key constraint cheats by knowing the name probably starts with pk_
        """
        strSql = """SELECT RDB$INDEX_NAME, RDB$UNIQUE_FLAG
            FROM RDB$INDICES
            WHERE RDB$RELATION_NAME = '%s'
            """ % (strTableName)
        self.cursor.execute(strSql)
        rows = self.cursor.fetchall()
        
        ret = []
        
        if not rows:
            return ret
        
        for row in rows:
            (strIndexName, bIsUnique) = row
            colList = self._fetchTableColumnsForIndex(strIndexName)
            if strIndexName.lower().startswith('pk_'):
                bIsPrimary = True
            else:
                bIsPrimary = False
            strIndexName = strIndexName.strip()
            ret.append((strIndexName, colList, bIsUnique, bIsPrimary, None))
        
        return ret

    def _fetchTableColumnsForIndex(self, strIndexName):
        strSql = """SELECT RDB$FIELD_NAME
            FROM RDB$INDEX_SEGMENTS
            WHERE RDB$INDEX_NAME = ?
            ORDER BY RDB$FIELD_POSITION
            """
        self.cursor.execute(strSql, [strIndexName.strip()])
        rows = self.cursor.fetchall()
        return [row[0].strip() for row in rows]

    def getTableRelations(self, strTableName):
        """ Returns 
            (strConstraintName, colName, fk_table, fk_columns)
            or []
        """
        strSql = """SELECT RDB$CONSTRAINT_NAME
            FROM RDB$RELATION_CONSTRAINTS
            WHERE RDB$RELATION_NAME = '%s'
            """ % (strTableName)
        self.cursor.execute(strSql)
        rows = self.cursor.fetchall()
        
        ret = []
        
        if not rows:
            return ret
        
        return ret

    def _fetchTableColumnsNamesByNums(self, strTableName, nums):
        strSql = """
            SELECT pa.attname
            FROM pg_attribute pa, pg_class pc
            WHERE pa.attrelid = pc.oid
            AND pa.attisdropped = 'f'
            AND pc.relname = %s
            AND pc.relkind = 'r'
            AND pa.attnum in (%s)
            ORDER BY pa.attnum
            """ % ( '%s', ','.join(['%s' for num in nums]) )
            
        self.cursor.execute(strSql, [strTableName] + nums)
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]
        
    def _decodeLength(self, type, atttypmod):
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

    def getViews(self):
        strQuery =  "SELECT RDB$VIEW_NAME FROM RDB$VIEW_RELATIONS"
        self.cursor.execute(strQuery)
        return [x[0].strip() for x in self.cursor.fetchall() ]

    def getViewDefinition(self, strViewName):
        strQuery = "SELECT RDB$RELATION_NAME, RDB$VIEW_SOURCE FROM RDB$RELATIONS WHERE RDB$RELATION_NAME = UPPER(?)"
        self.cursor.execute(strQuery, [strViewName])
        rows = self.cursor.fetchall()
        if rows:
            ret = rows[0][1].strip()
            return ret
        
        return ''

    def getFunctions(self):
        #strQuery = "SELECT RDB$FUNCTION_NAME FROM RDB$FUNCTIONS WHERE RDB$SYSTEM_FLAG = 0"
        strQuery = "SELECT RDB$PROCEDURE_NAME FROM RDB$PROCEDURES WHERE RDB$SYSTEM_FLAG = 0"
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        return [x[0].strip() for x in rows]

    def getFunctionDefinition(self, strSpecifiName):
        """ Returns (routineName, parameters, return, language, definition) """
        strQuery = "SELECT RDB$PROCEDURE_NAME, RDB$PROCEDURE_SOURCE FROM RDB$PROCEDURES WHERE RDB$SYSTEM_FLAG = 0 AND RDB$PROCEDURE_NAME = upper(?)"
        self.cursor.execute(strQuery, [strSpecifiName])
        rows = self.cursor.fetchall()
        strProcName, strDefinition = rows[0]
        strDefinition = strDefinition.strip()
        strProcName = strProcName.strip()
        
        strQuery = """SELECT PP.RDB$PARAMETER_NAME, PP.RDB$FIELD_SOURCE, PP.RDB$PARAMETER_TYPE, F.RDB$FIELD_TYPE, F.RDB$FIELD_LENGTH, F.RDB$FIELD_PRECISION, RDB$FIELD_SCALE
            FROM RDB$PROCEDURE_PARAMETERS PP, RDB$FIELDS F
            WHERE PP.RDB$PROCEDURE_NAME = upper(?) 
            AND   PP.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
            ORDER BY PP.RDB$PARAMETER_NUMBER"""
        self.cursor.execute(strQuery, [strSpecifiName])
        rows = self.cursor.fetchall()
        args = []
        rets = []
        
        for row in rows:
            strParamName, strSrc, nParamType, nType, nLen, nPrecision, nScale = row
            strParamName = strParamName.strip().lower()
            strSrc = strSrc.strip()
            strType = self.convertTypeId(nType)
            
            if nParamType == 0:
                args.append(strParamName + ' ' + strType)
            else:
                if strParamName.lower() == 'ret':
                    rets.append(strType)
                else:
                    rets.append(strParamName + ' ' + strType)
        
        return (strProcName.lower(), args, ','.join(rets), '', strDefinition)
        
class DownloadXml:
    def __init__(self, downloader):
        self.db = downloader
        
    def downloadSchema(self, tableList = None, of = sys.stdout):
        tables = self.db.getTables(tableList = None)

        of.write('<schema generated="yes">\n')
        
        for strTableName in tables:
            curTable = {
                'name' : strTableName,
                'columns' : []
            }
            desc = self.db.getTableComment(strTableName)
            if desc:
                curTable['desc'] = desc
            
            curTable['indexes'] = self.db.getTableIndexes(strTableName)
            
            pkMap = {}
            for index in curTable['indexes']:
                if index[3]: # If Primary key
                    for nIndex, colName in enumerate(index[1]):
                        pkMap[colName] = nIndex + 1
            
            curTable['relations'] = self.db.getTableRelations(strTableName)
            
            for colRow in self.db.getTableColumns(strTableName):
                (strColumnName, type, attlen, precision, attnotnull, default, bAutoIncrement) = colRow
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
                
                if strColumnName in pkMap:
                    curCol['key'] = pkMap[strColumnName]
                
                if default:
                    curCol['default'] = default
                
                strComment = self.db.getColumnComment(strTableName, strColumnName)
                if strComment:
                    curCol['desc'] = strComment
                
                if bAutoIncrement:
                    curCol['autoincrement'] = "yes"
                
                curTable['columns'].append(curCol)
            
            self.dumpTable(curTable, of)
            
        self.getViews(of)

        self.getFunctions(of)

        of.write('</schema>\n')

    def getViews(self, of):
        views = self.db.getViews()
        for viewName in views:
            definition = self.db.getViewDefinition(viewName)
            info = {
                'name' : viewName,
                'definition' : definition,
            }
            self.dumpView(info, of)
    
    def dumpView(self, info, of):
        of.write('  <view %s>\n' % (self.doAttribs(info, ['name'])))
        of.write('    %s\n' % (info['definition']))
        of.write('  </view>\n')

    def getFunctions(self, of):
        mangledNames = self.db.getFunctions()
        for mangledName in mangledNames:
            strFuncName, params, strReturn, strLanguage, definition = self.db.getFunctionDefinition(mangledName)
            info = {
                'name'       : strFuncName,
                'definition' : definition,
                'arguments'  : ', '.join(params),
                'returns'    : strReturn,
            }
            if strLanguage and len(strLanguage) > 0:
                info['language'] = strLanguage
            
            self.dumpFunction(info, of)
    
    def dumpFunction(self, info, of):
        of.write('  <function %s>\n' % (self.doAttribs(info, ['name', 'arguments', 'returns', 'language'])))
        of.write('%s\n' % (info['definition'].strip()))
        of.write('  </function>\n')

    def dumpTable(self, info, of):
        of.write('  <table %s>\n' % (self.doAttribs(info, ['name', 'desc'])))
        for col in info['columns']:
            of.write('    <column %s/>\n' % (self.doAttribs(col, ['name', 'type', 'size', 'precision', 'null', 'default', 'key', 'desc', 'autoincrement'])))
        
        strIndexes = ""
        for index in info['indexes']:
            if not index[3]:
                strIndexes += '        <index name="%s" columns="%s"/>\n' % (index[0], ','.join(index[1]))
            
        if len(strIndexes) > 0:
            of.write('    <indexes>\n')
            of.write(strIndexes)
            of.write('    </indexes>\n')
            
        if len(info['relations']) > 0:
            of.write('    <relations>\n')
            for index in info['relations']:
                # Need to add On Delete, and On Update 
                """
                confdeltype = 'c' THEN 0 -- Cascade 
                confdeltype = 'r' THEN 1 -- Restrict
                confdeltype = 'n' THEN 2 -- set Null
                confdeltype = 'a' THEN 3 -- no Action
                confdeltype = 'd' THEN 4 -- Default """
                curInfo = {
                    'name' : index[0],
                    'column' : ','.join(index[1]),
                    'table'  : index[2],
                    'fk'     : ','.join(index[3])
                }
                if index[4] == 'c':
                    curInfo['onupdate'] = 'cascade'
                elif index[4] == 'r':
                    curInfo['onupdate'] = 'restrict'
                elif index[4] == 'n':
                    curInfo['onupdate'] = 'setnull'
                elif index[4] == 'd':
                    curInfo['onupdate'] = 'default'
                    
                if index[5] == 'c':
                    curInfo['ondelete'] = 'cascade'
                elif index[5] == 'r':
                    curInfo['ondelete'] = 'restrict'
                elif index[5] == 'n':
                    curInfo['ondelete'] = 'setnull'
                elif index[5] == 'd':
                    curInfo['ondelete'] = 'default'
                    
                of.write('        <relation %s/>\n' % (self.doAttribs(curInfo, ['name', 'column', 'table', 'fk', 'ondelete', 'onupdate'])))
            
            of.write('    </relations>\n')
            
        of.write('  </table>\n')
    
    def doAttribs(self, attribs, nameList):
        ret = []
        for name in nameList:
            if name in attribs:
                ret.append('%s="%s"' % (name, attribs[name]))
        
        return ' '.join(ret)
    
def createDownloader(dbms, conn = None, info = None):
    if dbms == 'postgres' or dbms == 'postgres7':
        db = PgDownloader()
    elif dbms == 'mysql':
        db = MySqlDownloader()
    elif dbms == 'firebird':
        db = FbDownloader()
    
    if conn:
        db.useConnection(conn)
    elif info:
        db.connect(info)
    else:
        info = conn_info[dbms]
        db.connect(info)
        
    return DownloadXml(db)

if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-b", "--dbms",
                  dest="strDbms", metavar="DBMS", default="firebird", #"postgres",
                  help="Dowload for which Database Managment System (postgres, mysql, or firebird)")
    parser.add_option("-d", "--dbname",
                  dest="strDbName", metavar="DATABASE", default="/scott/xml2ddl/tests/test.db",#"simplifia",
                  help="Dowload for which named Database")
    parser.add_option("-u", "--user",
                  dest="strUserName", metavar="USER", default="SYSDBA", #"postgres",
                  help="User to login with")
    parser.add_option("-p", "--pass",
                  dest="strPassword", metavar="PASS", default="masterkey", #"postgres",
                  help="Password for the user")

    (options, args) = parser.parse_args()
    info = {
        'dbname' : options.strDbName, 
        'user'   : options.strUserName, 
        'pass'   : options.strPassword, 
    }

    cd = createDownloader(options.strDbms, info = info)
    cd.downloadSchema()
