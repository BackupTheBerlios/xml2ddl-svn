#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

from downloadCommon import DownloadCommon, getSeqName
from DdlCommonInterface import DdlCommonInterface
import re

class PgDownloader(DownloadCommon):
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

class DdlPostgres(DdlCommonInterface):
    def __init__(self, strDbms):
        DdlCommonInterface.__init__(self, strDbms)
        
        self.params['max_id_len'] = { 'default' : 63 }
        
        if self.dbmsType == 'postgres7':
            self.params['no_alter_column_type'] = True
        
        self.params['keywords'] = """
            ALL AND ANY AS ASC AUTHORIZATION BETWEEN BINARY BOTH CASE CAST CHECK COLLATE COLUMN CONSTRAINT CREATE
            CROSS CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP CURRENT_USER DEFAULT DEFERRABLE DESC DISTINCT ELSE
            END EXCEPT FALSE FOR FOREIGN FREEZE FROM FULL GRANT GROUP HAVING ILIKE IN INITIALLY INNER INTERSECT
            INTO IS ISNULL JOIN LEADING LEFT LIKE LIMIT LOCALTIME LOCALTIMESTAMP NATURAL NEW NOT NOTNULL NULL 
            OFF OLD ON ONLY OR ORDER OUTER OVERLAPS PRIMARY REFERENCES RIGHT SELECT SESSION_USER SIMILAR SOME TABLE 
            THEN TO TRAILING TRUE UNION UNIQUE USER USING VERBOSE WHEN WHERE""".split()
        
    def addFunction(self, strNewFunctionName, argumentList, strReturn, strContents, attribs, diffs):
        newArgs = []
        declares = []
        for nIndex, arg in enumerate(argumentList):
            oneArg = arg.strip().split()
            newArgs.append(oneArg[-1])
            declares.append('    %s ALIAS FOR $%d;' % (oneArg[0], nIndex + 1))
        
        if len(declares) > 0:
            match = re.compile('(\s*declare)(.*)', re.IGNORECASE | re.MULTILINE | re.DOTALL).match(strContents)
            if match:
                strContents = match.group(1) + '\n' + '\n'.join(declares) + match.group(2)
            else:
                strContents = 'DECLARE\n' + '\n'.join(declares) + "\n" + strContents
            
        info = {
            'functionname' : self.quoteName(strNewFunctionName),
            'arguments'  : ', '.join(newArgs),
            'returns'  : strReturn,
            'contents' : strContents.replace("'", "''"),
        }
        if 'language' not in attribs:
            info['language'] = ' LANGUAGE plpgsql'
        else:
            info['language'] = ' LANGUAGE %s' % (attribs['language'])

        diffs.append(('Add view',  # OR REPLACE 
            "CREATE FUNCTION %(functionname)s(%(arguments)s) RETURNS %(returns)s AS '\n%(contents)s'%(language)s" % info )
        )
