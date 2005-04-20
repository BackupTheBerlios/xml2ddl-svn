#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

from downloadCommon import DownloadCommon, getSeqName
from DdlCommonInterface import DdlCommonInterface
import re

class OracleDownloader(DownloadCommon):
    def __init__(self):
        self.strDbms = 'oracle'
        
    def connect(self, info):
        try:
            import cx_Oracle
        except:
            print "Missing PostgreSQL support through psycopg"
            return
        
        self.conn = cx_Oracle.connect(info['user'], info['pass'], info['dbname'])
        self.cursor = self.conn.cursor()
        
    def _tableInfo(self, strTable):
        self.cursor.execute("select * from %s" % (strTable,))
        for col in self.cursor.description:
            print col[0]
        
    def useConnection(self, con):
        self.conn = con
        self.cursor = self.conn.cursor()
        
    def getTables(self, tableList):
        """ Returns the list of tables as a array of strings """
        
        if tableList and len(tableList) > 0:
            inTables = "AND TABLE_NAME IN ('%s')" % ("' , '".join([name.upper() for name in tableList]))
        else:
            inTables = ""
        strQuery = """SELECT TABLE_NAME FROM ALL_TABLES WHERE 
            TABLE_NAME NOT IN ('DUAL')
            AND OWNER NOT IN ('SYS', 'SYSTEM')
            %s
            ORDER BY TABLE_NAME
            """ % (inTables)
        
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
            SELECT COLUMN_ID, COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE, DATA_DEFAULT
            FROM ALL_TAB_COLUMNS
            WHERE TABLE_NAME = :tablename
            ORDER BY COLUMN_ID"""
        # self._tableInfo('ALL_TAB_COLUMNS')
        self.cursor.execute(strSql, { 'tablename' : strTable})
        rows = self.cursor.fetchall()
        
        ret = []
        fixNames = {
            'character varying' : 'varchar',
        }
        for row in rows:
            attnum, name, type, size, numsize, numprec, nullable, default = row
            if type in fixNames:
                type = fixNames[type]
            
            if nullable == "Y":
                bNotNull = False
            else:
                bNotNull = True
            
            bAutoIncrement = False
            if default:
                default = default.rstrip()
                
            if default == "nextval('%s')" % (getSeqName(strTable, name)):
                default = ''
                bAutoIncrement = True
                
            ret.append((name, type, size, numprec, bNotNull, default, bAutoIncrement))
            
        return ret
    
    def getTableComment(self, strTableName):
        """ Returns the comment as a string """
        # TODO
        
        strSql = "SELECT COMMENTS from ALL_TAB_COMMENTS WHERE TABLE_NAME = :TABLENAME"
        self.cursor.execute(strSql, { 'TABLENAME' : strTableName })
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0]
        
        return None

    def getColumnComment(self, strTableName, strColumnName):
        """ Returns the comment as a string """
        strSql = "SELECT COMMENTS from  ALL_COL_COMMENTS WHERE TABLE_NAME = :TABLENAME AND COLUMN_NAME = :COLUMNAME"
        self.cursor.execute(strSql, { 'TABLENAME' : strTableName, 'COLUMNAME' : strColumnName })
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0]
        
        return []
        return None

    def getTableIndexes(self, strTableName):
        """ Returns 
            (strIndexName, [strColumns,], bIsUnique, bIsPrimary, bIsClustered)
            or []
        """
        
        #self._tableInfo("ALL_INDEXES")
        strSql = """SELECT table_name, index_name, uniqueness, secondary, CLUSTERING_FACTOR
            FROM ALL_INDEXES
            WHERE table_name = :tablename
            """
        self.cursor.execute(strSql, { 'tablename' : strTableName} )
        rows = self.cursor.fetchall()
        
        ret = []
        if not rows:
            return ret
        #self._tableInfo("ALL_IND_COLUMNS")
        
        for row in rows:
            (strIndexName, strColumns, bIsUnique, bIsPrimary, bIsClustered) = row
            strSql = """SELECT column_name FROM ALL_IND_COLUMNS 
                WHERE table_name = :tablename AND index_name = :indexname
                ORDER BY COLUMN_POSITION """
            self.cursor.execute(strSql, { 'tablename' : strTableName, 'indexname' : strIndexName } )
            colrows = self.cursor.fetchall()
            colList = [col[0] for col in colrows]
            ret.append((strIndexName, colList, bIsUnique, bIsPrimary, bIsClustered))
        
        return ret

    def _getTableViaConstraintName(self, strConstraint):
        """ Returns strTablename """
        
        strSql = """SELECT TABLE_NAME FROM ALL_CONSTRAINTS WHERE CONSTRAINT_NAME = :strConstraint"""
        self.cursor.execute(strSql, { 'strConstraint' : strConstraint } )
        rows = self.cursor.fetchall()
        
        if rows:
            return rows[0][0]
        
        return None

    def _getColumnsViaConstraintName(self, strConstraint):
        """ Returns strTablename """
        
        strSql = """SELECT COLUMN_NAME FROM all_cons_columns WHERE CONSTRAINT_NAME = :strConstraint ORDER BY POSITION"""
        self.cursor.execute(strSql, { 'strConstraint' : strConstraint } )
        rows = self.cursor.fetchall()
        
        if rows:
            return [ col[0] for col in rows ]
        
        return []

    def getTableRelations(self, strTableName):
        """ Returns 
            (strConstraintName, colName, fk_table, fk_columns, confupdtype, confdeltype)
            or []
        """
        # CONSTRAINT_TYPE == "P" primary key
        # CONSTRAINT_TYPE == "R" 'Ref. Integrity'
        # CONSTRAINT_TYPE == "U" 'Unique Constr.'
        # CONSTRAINT_TYPE == "C" 'Check Constr.'
        strSql = """SELECT CONSTRAINT_NAME, TABLE_NAME, R_CONSTRAINT_NAME, DELETE_RULE
            FROM  ALL_CONSTRAINTS
            WHERE TABLE_NAME = :tablename
            AND   CONSTRAINT_TYPE = 'R'
            AND   STATUS='ENABLED'
            """
        self.cursor.execute(strSql, { 'tablename' : strTableName })
        rows = self.cursor.fetchall()
        
        ret = []
        
        if not rows:
            return ret
        
        for row in rows:
            (strConstraintName, strTable, fk_constraint, chDelType) = row
            # Todo get the fk table name
            # and the col list
            # and the fk col list
            if fk_constraint:
                fk_table = self._getTableViaConstraintName(fk_constraint)
            else:
                fk_table = None
            
            colList = self._getColumnsViaConstraintName(strConstraintName)
            if fk_constraint:
                fkColList = self._getColumnsViaConstraintName(fk_constraint)
            else:
                fkColList = []
                
            chUpdateType = ''
            ret.append((strConstraintName, colList, fk_table, fkColList, chUpdateType, chDelType))
        
        return ret
        
    def getViews(self, viewList):
        """ Returns the list of views as a array of strings """
        
        if viewList and len(viewList) > 0:
            inViews = "WHERE VIEW_NAME IN ('%s')" % ("','".join([name.upper() for name in viewList]))
        else:
            inViews = ""
        strQuery = """SELECT VIEW_NAME FROM ALL_VIEWS %s ORDER BY VIEW_NAME""" % (inViews)
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if rows:
            return [x[0] for x in rows]
        
        return []

    def getViewDefinition(self, strViewName):
        strQuery = "SELECT TEXT FROM ALL_VIEWS WHERE VIEW_NAME = :viewName"
        self.cursor.execute(strQuery, { 'viewName' : strViewName })
        rows = self.cursor.fetchall()
        if rows:
            return rows[0][0].rstrip()
        
        return None

    def getFunctions(self, functionList):
        """ Returns functions """
        
        if functionList and len(functionList) > 0:
            inFunctions = "AND OBJECT_NAME IN ('%s')" % ("','".join([name.upper() for name in functionList]))
        else:
            inFunction = ""
        
        strQuery = """SELECT OBJECT_NAME
        FROM ALL_OBJECTS
        WHERE OBJECT_TYPE in ('PROCEDURE', 'FUNCTION')
        AND OWNER NOT IN ('SYS', 'SYSTEM')
        %s
        ORDER BY OBJECT_NAME""" % (inFunctions)
        
        self.cursor.execute(strQuery)
        rows = self.cursor.fetchall()
        if rows:
            return [x[0] for x in rows]
        
        return []

    def getFunctionDefinition(self, strSpecifiName):
        """ Returns (routineName, parameters, return, language, definition) """
        
        strQuery = "select TEXT from all_source where name=:strSpecifiName ORDER BY LINE"
        self.cursor.execute(strQuery, { 'strSpecifiName' : strSpecifiName })
        rows = self.cursor.fetchall()
        if not rows:
            return (None, None, None, None)
        
        lines = []
        for row in rows:
            lines.append(row[0])
        
        strDefinition = ''.join(lines)

        strQuery = """select PACKAGE_NAME, ARGUMENT_NAME, DATA_TYPE, SEQUENCE, IN_OUT
            FROM ALL_ARGUMENTS 
            WHERE object_name = :strSpecifiName AND ARGUMENT_NAME is not null and position is not null"""
        self.cursor.execute(strQuery, { 'strSpecifiName' : strSpecifiName })
        rows = self.cursor.fetchall()
        parameters = [] 
        if rows: 
            for row in rows:
                (PACKAGE_NAME, ARGUMENT_NAME, DATA_TYPE, SEQUENCE, IN_OUT) = row
                if ARGUMENT_NAME:
                    parameters.append(DATA_TYPE + " " + ARGUMENT_NAME)
                else:
                    parameters.append(DATA_TYPE)
            
        strQuery = """select ARGUMENT_NAME, DATA_TYPE 
            FROM ALL_ARGUMENTS
            WHERE object_name = :strSpecifiName AND position is null"""
        self.cursor.execute(strQuery, { 'strSpecifiName' : strSpecifiName })
        rows = self.cursor.fetchall()
        if rows:
            if len(rows) > 1:
                print "More than one return statement?, please check code"
                ARGUMENT_NAME, DATA_TYPE = rows[0]
                if ARGUMENT_NAME:
                    strReturn = DATA_TYPE + ' ' + ARGUMENT_NAME
                else:
                    strReturn = DATA_TYPE
        else:
            strReturn = None
        
        return (strSpecifiName, parameters, strReturn, 'PL/SQL', strDefinition)


class DdlOracle(DdlCommonInterface):
    def __init__(self, strDbms):
        DdlCommonInterface.__init__(self, strDbms)
        
        self.params['max_id_len'] = { 'default' : 63 }
                
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
        
        diffs.append(('Add view',  # OR REPLACE 
            "CREATE FUNCTION %(functionname)s(%(arguments)s) RETURNS %(returns)s AS '\n%(contents)s'" % info )
        )
