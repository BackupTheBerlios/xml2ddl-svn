
#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

import re, os
from xml.dom.minidom import parse, parseString

__author__ = "Scott Kirkwood (scott_kirkwood at berlios.com)"
__keywords__ = ['XML', 'DML', 'SQL', 'Databases', 'Agile DB', 'ALTER', 'CREATE TABLE', 'GPL']
__licence__ = "GNU Public License (GPL)"
__longdescr__ = ""
__url__ = 'http://xml2dml.berlios.de'
__version__ = "$Revision: 0.2 $"

class DdlCommonInterface:
    def __init__(self, strDbms):
        self.dbmsType = strDbms
        self.params = {
            'table_desc' : "COMMENT ON TABLE %(table)s IS %(desc)s",
            'column_desc' : "COMMENT ON COLUMN %(table)s.%(column)s IS %(desc)s",
            'unquoted_id' : re.compile(r'^[A-Za-z][A-Za-z0-9_]+$'),
            'max_id_len' : { 'default' : 256 },
            'has_auto_increment' : False,
            'keywords' : [ 'NULL', 'SELECT', 'FROM' ],
            'quote_l' : '"',
            'quote_r' : '"',
            'drop_constraints_on_col_rename' : False,
            'rename_keyword' : 'RENAME', # or ALTER
            'no_alter_column_type' : False,
            'drop_table_has_cascade' : True,
            'no_alter_default' : False,
            'change_type_keyword' : 'ALTER',
            'TYPE' : 'TYPE ',
            'can_change_table_comment' : True,
            'no_rename_col' : False,
            'drop_index'    : 'DROP INDEX %(index_name)s'
        }

    # Tables
    def dropTable(self, strTableName, strCascade, diffs):
        info = {
            'table_name' : self.quoteName(strTableName),
            'cascade'    : strCascade,
        }
        
        diffs.append(
            ('Drop Table', 'DROP TABLE %(table_name)s%(cascade)s' % info))

    def renameTable(self, strTableOld, strTableNew, diffs):
        info = {
            'table_name' : self.quoteName(strTableOld), 
            'new_table_name' : self.quoteName(strTableNew),
        }
        diffs.append(('Rename Table',
            'ALTER TABLE %(table_name)s RENAME TO %(new_table_name)s' % info) )

    def addTableComment(self, tableName, desc, ddls):
        """ TODO: Fix the desc for special characters """
        info = {
            'table' : tableName,
            'desc' : self.quoteString(desc),
        }
        ddls.append(('Table Comment',
            self.params['table_desc'] % info ))
    
    # Columns
    def addColumn(self, strTableName, strColName, strColType, nAfter, diffs):
        """ nAfter not used yet """
        
        info = { 
            'table_name' : self.quoteName(strTableName),
            'column_name' : self.quoteName(strColName),
            'column_type' : strColType
        }
        
        strAlter = 'ALTER TABLE %(table_name)s ADD %(column_name)s %(column_type)s' % info

        diffs.append(('Add Column', strAlter))
        
    def dropCol(self, strTableName, strColName, diffs):
        info = { 
            'table_name' : self.quoteName(strTableName),
            'column_name' : self.quoteName(strColName),
        }
        
        strAlter = 'ALTER TABLE %(table_name)s DROP %(column_name)s' % info

        diffs.append(('Dropped Column', strAlter))
        
    def renameColumn(self, strTableName, strOldName, strNewName, strNewColType, diffs):
        info = {
            'table_name'   : self.quoteName(strTableName),
            'old_col_name' : self.quoteName(strOldName),
            'new_col_name' : self.quoteName(strNewName),
            'rename'       : self.params['rename_keyword'],
            'column_type'  : strNewColType,
        }
        
        if self.params['no_rename_col']:
            # MySQL is like this
            diffs.append(
                ('Rename column',
                'ALTER TABLE %(table_name)s CHANGE %(old_col_name)s %(new_col_name)s %(column_type)s' % info))
        else:
            diffs.append(
                ('Rename column',
                'ALTER TABLE %(table_name)s %(rename)s %(old_col_name)s TO %(new_col_name)s' % info))


    def addColumnComment(self, strTableName, strColumnName, strDesc, strColType, ddls):
        info = {
            'table' : strTableName,
            'column' : strColumnName,
            'desc' :  self.quoteString(strDesc),
            'type' : strColType + ' ',
        }
        ddls.append(('Column comment',
            self.params['column_desc'] % info ))

    def changeColumnComment(self, strTableName, strColumnName, strDesc, strColType, ddls):
        self.addColumnComment(strTableName, strColumnName, strDesc, strColType, ddls)

    # Primary Keys
    def addKeyConstraint(self, strTableName, keylist, diffs):
        info = {
            'table_name'    : self.quoteName(strTableName), 
            'pk_constraint' : self.quoteName('pk_%s' % (strTableName)),
            'keys'          : ', '.join(keylist),
        }
        diffs.append( ('Create primary keys',
            'ALTER TABLE %(table_name)s ADD CONSTRAINT %(pk_constraint)s PRIMARY KEY (%(keys)s)' % info))

    def dropKeyConstraint(self, strTable, strConstraintName, diffs):
        # Note, apparently wasn't used
        info = {
            'table_name' : strTable,
            'constraint_name' : strConstraintName,
        }
        diffs.append(('Drop key constraint', 
            'ALTER TABLE %(table_name)s DROP CONSTRAINT %(constraint_name)s' % info))
    
    # Indexes
    def addIndex(self, strTableName, strIndexName, cols, ddls):
        cols = [self.quoteName(col) for col in cols]
        
        ddls.append(('Add Index',
            'CREATE INDEX %s ON %s (%s)' % (self.quoteName(strIndexName), self.quoteName(strTableName), ', '.join(cols)) ))

    def deleteIndex(self, strTableName, strIndexName, diffs):
        info = { 
            'index_name' : self.quoteName(strIndexName),
            'table_name' : strTableName,
        }
        diffs += [(
            'Drop Index', self.params['drop_index'] % info)]

    def renameIndex(self, strTableName, strOldIndexName, strNewIndexName, cols, diffs):
        self.deleteIndex(strTableName, strOldIndexName, diffs)
        self.addIndex(strTableName, strNewIndexName, cols, diffs)

    def changeIndex(self, strTableName, strOldIndexName, strNewIndexName, cols, diffs):
        self.deleteIndex(strTableName, strOldIndexName, diffs)
        self.addIndex(strTableName, strNewIndexName, cols, diffs)

    # Relations
    def addRelation(self, strTableName, strRelationName, strColumn, strFkTable, strFk, strOnDelete, strOnUpdate, diffs):
        info = {
            'tablename'  : self.quoteName(strTableName),
            'thiscolumn' : self.quoteName(strColumn),
            'othertable' : self.quoteName(strFkTable),
            'constraint' : self.quoteName(strRelationName),
            'ondelete' : '',
            'onupdate' : '',
        }
        if len(strFk) > 0:
            info['fk'] = strFk
        else:
            info['fk'] = info['thiscolumn']
        
        if len(strOnDelete) > 0:
            action = strOnDelete.upper()
            if action == 'SETNULL':
                action = 'SET NULL'
            info['ondelete'] = ' ON DELETE ' + action
        
        if len(strOnUpdate) > 0:
            action = strOnUpdate.upper()
            if action == 'SETNULL':
                action = 'SET NULL'
            info['onupdate'] = ' ON UPDATE ' + action
            
        diffs.append(('relation', 
            'ALTER TABLE %(tablename)s ADD CONSTRAINT %(constraint)s FOREIGN KEY (%(thiscolumn)s) REFERENCES %(othertable)s(%(fk)s)%(ondelete)s%(onupdate)s' % info))

    def dropRelation(self, strTableName, strRelationName, diffs):
        info = {
            'tablename': self.quoteName(strTableName),
            'constraintname' : strRelationName,
        }
        
        diffs += [
            ('Drop Relation', 'ALTER TABLE %(tablename)s DROP CONSTRAINT %(constraintname)s' % info)]


    # Autoincrement
    def addAutoIncrement(self, strTableName, strColName, strDefault, strPreDdl, strPostDdl):
        info = {
            'table_name' : strTableName,
            'col_name'   : strColName,
            'seq_name'   : self.getSeqName(strTableName, strColName),
            'ai_trigger' : self.getAiTriggerName(strTableName, strColName),
        }
        
        if self.params['has_auto_increment']:
            return ' AUTO_INCREMENT'
    
        if self.dbmsType == 'firebird':
            strPreDdl.append(('autoincrement generator',
                'CREATE GENERATOR %(seq_name)s' % info))
            strPostDdl.append(('autoincrement trigger',
                """CREATE TRIGGER %(ai_trigger)s FOR %(table_name)s
                BEFORE INSERT AS
                BEGIN
                    NEW.%(col_name)s = GEN_ID(%(seq_name)s, 1);
                END""" % info))
            return ''
        
        strPreDdl.append(('autoincrement', 
            'CREATE SEQUENCE %(seq_name)s' % info))
            
        if strDefault:
            print "Error: can't have a default and autoincrement together"
            return ''
            
        return " DEFAULT nextval('%(seq_name)s')" % info

    def dropAutoIncrement(self, strTableName, col, diffs):
        # Todo get rid of the col
        
        strColName = col.get('name')
        info = {
            'table_name' : strTableName,
            'col_name'   : strColName,
            'seq_name'   : self.getSeqName(strTableName, strColName),
            'ai_trigger' : self.getAiTriggerName(strTableName, strColName),
        }
        if self.params['has_auto_increment']:
            self.doChangeColType(strTableName, strColName, self.retColTypeEtc(col), diffs)
            return

        
        if self.dbmsType == 'firebird':
            diffs.append(('Drop Autoincrement Trigger', 
                'DROP TRIGGER %(ai_trigger)s' % info))
            
            diffs.append(('Drop Autoincrement', 
                'DROP GENERATOR %(seq_name)s' % info))
            return
            
        # For postgres
        diffs.append(('Drop Autoincrement', 
            'DROP SEQUENCE %(seq_name)s' % info))
        
        self.dropDefault(strTableName, col, diffs)
    
    # Column default
    def dropDefault(self, strTableName, col, diffs):
        info = {
            'table_name' : self.quoteName(strTableName),
            'column_name' : self.quoteName(col.get('name')),
            'change_type_keyword' : 'ALTER',
            'new_default' : 'null', # FIX TODO Null, 0 or ''
            'default_keyword' : 'SET DEFAULT',
            'column_type' : self.retColTypeEtc(col),
            'TYPE' : self.params['TYPE'],
        }
            
        if self.params['no_alter_default']:
            # Firebird
            diffs.append(
                ('Drop Default', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s' % info))
        else:
            diffs.append(
                ('Drop Default', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(default_keyword)s %(new_default)s' % info))

    def changeColDefault(self, strTableName, strColumnName, strNewDefault, strColType, diffs):
        info = {
            'table_name' : self.quoteName(strTableName),
            'column_name' : self.quoteName(strColumnName),
            'change_type_keyword' : 'ALTER',
            'new_default' : strNewDefault,
            'default_keyword' : 'SET DEFAULT',
            'column_type' : strColType,
            'TYPE' : self.params['TYPE'],
        }
        
        if self.params['no_alter_default']:
            # Firebird
            diffs.append(
                ('Change Default', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s DEFAULT %(new_default)s' % info))
        else:
            diffs.append(
                ('Change Default', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(default_keyword)s %(new_default)s' % info))

    # Column type
    def doChangeColType(self, strTableName, strColumnName, strNewColType, diffs):
        info = {
            'table_name' : strTableName,
            'column_name' : strColumnName,
            'column_type' : strNewColType,
            'change_type_keyword' : self.params['change_type_keyword'],
            'TYPE' : self.params['TYPE'],
        }
        
        if self.params['no_alter_column_type']:
            # For PostgreSQL 7.x you need to do...
            diffs.append( ('Add for change type',
                'ALTER TABLE %(table_name)s ADD tmp_%(column_name)s %(column_type)s' % info) )
            diffs.append( ('Copy the data over for change type',
                'UPDATE %(table_name)s SET tmp_%(column_name)s = %(column_name)s' % info) )
            diffs.append( ('Drop the old column for change type',
                'ALTER TABLE %(table_name)s DROP %(column_name)s' % info) )
            diffs.append( ('Rename column for change type',
                'ALTER TABLE %(table_name)s RENAME tmp_%(column_name)s TO %(column_name)s' % info) )
        else:
            diffs.append(
                ('Modify column', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s' % info))

    def renameView(self, strOldViewName, strNewViewName, newDefinition, newAttribs, diffs):
        self.dropView(strOldViewName, diffs)
        self.addView(strNewViewName, newDefinition, newAttribs, diffs)
    
    def dropView(self, strOldViewName, diffs):
        info = {
            'viewname' : self.quoteName(strOldViewName),
        }
        diffs.append( (
            'Drop view',
            'DROP VIEW %(viewname)s' % info ))
    
    def addView(self, strNewViewName, strContents, attribs, diffs):
        info = {
            'viewname' : self.quoteName(strNewViewName),
            'contents' : strContents,
        }
        diffs.append( (
            'Drop view',
            'CREATE OR REPLACE VIEW %(viewname)s AS %(contents)s' % info ))
    
    def updateView(self, strViewName, strContents, attribs, diffs):
        self.addView(strViewName, strContents, attribs, diffs)
        
    def retColTypeEtc(self, col):
        strNull = ''
        if 'null' in col:
            strVal = col.get('null')
            if re.compile('not|no', re.IGNORECASE).search(strVal):
                strNull = ' NOT NULL'
        
        strType = col.get('type', None)
        strSize = col.get('size', None)
        strPrec = col.get('precision', None)
        
        if strPrec:
            strRet = '%s(%s, %s)%s' % (strType, strSize, strPrec, strNull)
        elif strSize:
            strRet = '%s(%s)%s' % (strType, strSize, strNull)
        else:
            strRet = '%s%s' % (strType, strNull)

        return strRet


    def getSeqName(self, strTableName, strColName):
        return '%s_%s_seq' % (strTableName, strColName)
    
    def getAiTriggerName(self, strTableName, strColName):
        return 'ai_%s_%s' % (strTableName, strColName)

    def quoteName(self, strName):
        bQuoteName = False
        
        if not self.params['unquoted_id'].match(strName):
            bQuoteName = True

        if strName.upper() in self.params['keywords']:
            bQuoteName = True
        
        if not bQuoteName:
            if strName[0] == '"' and strName[-1] == '"':
                # Already quoted.
                bQuoteName = False

        if bQuoteName:
            return self.params['quote_l'] + strName + self.params['quote_r']
        
        return strName

    def quoteString(self, strStr):
        return "'%s'" % (strStr.replace("'", "''"))

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
        

class DdlMySql(DdlCommonInterface):
    def __init__(self):
        DdlCommonInterface.__init__(self, 'mysql')
        self.params['max_id_len'] = { 'default' : 64 }
        self.params['quote_l'] = '`'
        self.params['quote_r'] = '`'
        self.params['table_desc'] = "ALTER TABLE %(table)s COMMENT %(desc)s"
        self.params['column_desc'] = "ALTER TABLE %(table)s MODIFY %(column)s %(type)sCOMMENT %(desc)s"
        self.params['has_auto_increment'] = True
        self.params['rename_keyword'] = 'ALTER'
        self.params['no_rename_col'] = True
        self.params['change_type_keyword'] = 'MODIFY'
        self.params['TYPE'] = ''
        self.params['can_change_table_comment'] = False
        self.params['drop_index'] = 'DROP INDEX %(index_name)s ON %(table_name)s'
        self.params['keywords'] = """
            ADD ALL ALTER ANALYZE AND AS ASC ASENSITIVE AUTO_INCREMENT BDB BEFORE BERKELEYDB BETWEEN BIGINT BINARY
            BLOB BOTH BY CALL CASCADE CASE CHANGE CHAR CHARACTER CHECK COLLATE COLUMN COLUMNS CONDITION CONNECTION
            CONSTRAINT CONTINUE CREATE CROSS CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP CURSOR DATABASE 
            DATABASES DAY_HOUR DAY_MICROSECOND DAY_MINUTE DAY_SECOND DEC DECIMAL DECLARE DEFAULT DELAYED DELETE DESC
            DESCRIBE DETERMINISTIC DISTINCT DISTINCTROW DIV DOUBLE DROP ELSE ELSEIF ENCLOSED ESCAPED EXISTS EXIT 
            EXPLAIN FALSE FETCH FIELDS FLOAT FOR FORCE FOREIGN FOUND FRAC_SECOND FROM FULLTEXT GRANT GROUP
            HAVING HIGH_PRIORITY HOUR_MICROSECOND HOUR_MINUTE HOUR_SECOND IF IGNORE IN INDEX INFILE INNER INNODB
            INOUT INSENSITIVE INSERT INT INTEGER INTERVAL INTO IO_THREAD IS ITERATE JOIN KEY KEYS KILL LEADING
            LEAVE LEFT LIKE LIMIT LINES LOAD LOCALTIME LOCALTIMESTAMP LOCK LONG LONGBLOB LONGTEXT LOOP LOW_PRIORITY 
            MASTER_SERVER_ID MATCH MEDIUMBLOB MEDIUMINT MEDIUMTEXT MIDDLEINT MINUTE_MICROSECOND MINUTE_SECOND MOD NATURAL
            NOT NO_WRITE_TO_BINLOG NULL NUMERIC ON OPTIMIZE OPTION OPTIONALLY OR ORDER OUT OUTER OUTFILE PRECISION PRIMARY
            PRIVILEGES PROCEDURE PURGE READ REAL REFERENCES REGEXP RENAME REPEAT REPLACE REQUIRE RESTRICT RETURN REVOKE RIGHT
            RLIKE SECOND_MICROSECOND SELECT SENSITIVE SEPARATOR SET SHOW SMALLINT SOME SONAME SPATIAL SPECIFIC
            SQL SQLEXCEPTION SQLSTATE SQLWARNING SQL_BIG_RESULT SQL_CALC_FOUND_ROWS SQL_SMALL_RESULT SQL_TSI_DAY 
            SQL_TSI_FRAC_SECOND SQL_TSI_HOUR SQL_TSI_MINUTE SQL_TSI_MONTH SQL_TSI_QUARTER SQL_TSI_SECOND SQL_TSI_WEEK
            SQL_TSI_YEAR SSL STARTING STRAIGHT_JOIN STRIPED TABLE TABLES TERMINATED THEN TIMESTAMPADD TIMESTAMPDIFF TINYBLOB
            TINYINT TINYTEXT TO TRAILING TRUE UNDO UNION UNIQUE UNLOCK UNSIGNED UPDATE USAGE USE USER_RESOURCES USING
            UTC_DATE UTC_TIME UTC_TIMESTAMP VALUES VARBINARY VARCHAR VARCHARACTER VARYING WHEN WHERE WHILE WITH
            WRITE XOR YEAR_MONTH ZEROFILL""".split() 

class DdlFirebird(DdlCommonInterface):
    def __init__(self):
        DdlCommonInterface.__init__(self, 'firebird')
        self.params['max_id_len'] = { 'default' : 256 }
        self.params['table_desc'] = "UPDATE RDB$RELATIONS SET RDB$DESCRIPTION = %(desc)s\n\tWHERE RDB$RELATION_NAME = upper('%(table)s')"
        self.params['column_desc'] = "UPDATE RDB$RELATION_FIELDS SET RDB$DESCRIPTION = %(desc)s\n\tWHERE RDB$RELATION_NAME = upper('%(table)s') AND RDB$FIELD_NAME = upper('%(column)s')"
        self.params['rename_keyword'] = 'ALTER'
        self.params['drop_constraints_on_col_rename'] = True
        self.params['drop_table_has_cascade'] = False
        self.params['no_alter_default'] = True
        
        self.params['keywords'] = """
            ACTION ACTIVE ADD ADMIN AFTER ALL ALTER AND ANY AS ASC ASCENDING AT AUTO AUTODDL AVG BASED BASENAME BASE_NAME 
            BEFORE BEGIN BETWEEN BLOB BLOBEDIT BUFFER BY CACHE CASCADE CAST CHAR CHARACTER CHARACTER_LENGTH CHAR_LENGTH
            CHECK CHECK_POINT_LEN CHECK_POINT_LENGTH COLLATE COLLATION COLUMN COMMIT COMMITTED COMPILETIME COMPUTED CLOSE 
            CONDITIONAL CONNECT CONSTRAINT CONTAINING CONTINUE COUNT CREATE CSTRING CURRENT CURRENT_DATE CURRENT_TIME 
            CURRENT_TIMESTAMP CURSOR DATABASE DATE DAY DB_KEY DEBUG DEC DECIMAL DECLARE DEFAULT
            DELETE DESC DESCENDING DESCRIBE DESCRIPTOR DISCONNECT DISPLAY DISTINCT DO DOMAIN DOUBLE DROP ECHO EDIT ELSE 
            END ENTRY_POINT ESCAPE EVENT EXCEPTION EXECUTE EXISTS EXIT EXTERN EXTERNAL EXTRACT FETCH FILE FILTER FLOAT 
            FOR FOREIGN FOUND FREE_IT FROM FULL FUNCTION GDSCODE GENERATOR GEN_ID GLOBAL GOTO GRANT GROUP GROUP_COMMIT_WAIT 
            GROUP_COMMIT_ WAIT_TIME HAVING HELP HOUR IF IMMEDIATE IN INACTIVE INDEX INDICATOR INIT INNER INPUT INPUT_TYPE 
            INSERT INT INTEGER INTO IS ISOLATION ISQL JOIN KEY LC_MESSAGES LC_TYPE LEFT LENGTH LEV LEVEL LIKE LOGFILE 
            LOG_BUFFER_SIZE LOG_BUF_SIZE LONG MANUAL MAX MAXIMUM MAXIMUM_SEGMENT MAX_SEGMENT MERGE MESSAGE MIN MINIMUM 
            MINUTE MODULE_NAME MONTH NAMES NATIONAL NATURAL NCHAR NO NOAUTO NOT NULL NUMERIC NUM_LOG_BUFS NUM_LOG_BUFFERS 
            OCTET_LENGTH OF ON ONLY OPEN OPTION OR ORDER OUTER OUTPUT OUTPUT_TYPE OVERFLOW PAGE PAGELENGTH PAGES PAGE_SIZE 
            PARAMETER PASSWORD PLAN POSITION POST_EVENT PRECISION PREPARE PROCEDURE PROTECTED PRIMARY PRIVILEGES PUBLIC QUIT 
            RAW_PARTITIONS RDB$DB_KEY READ REAL RECORD_VERSION REFERENCES RELEASE RESERV RESERVING RESTRICT RETAIN RETURN 
            RETURNING_VALUES RETURNS REVOKE RIGHT ROLE ROLLBACK RUNTIME SCHEMA SECOND SEGMENT SELECT SET SHADOW SHARED SHELL 
            SHOW SINGULAR SIZE SMALLINT SNAPSHOT SOME SORT SQLCODE SQLERROR SQLWARNING STABILITY STARTING STARTS STATEMENT 
            STATIC STATISTICS SUB_TYPE SUM SUSPEND TABLE TERMINATOR THEN TIME TIMESTAMP TO TRANSACTION TRANSLATE TRANSLATION 
            TRIGGER TRIM TYPE UNCOMMITTED UNION UNIQUE UPDATE UPPER USER USING VALUE VALUES VARCHAR VARIABLE VARYING VERSION 
            VIEW WAIT WEEKDAY WHEN WHENEVER WHERE WHILE WITH WORK WRITE YEAR YEARDAY""".split()
        

def attribsToDict(node):
    dict = {}
    attribs = node.attributes
    for nIndex in range(attribs.length):
        dict[attribs.item(nIndex).name] = attribs.item(nIndex).value
    
    return dict

def createDdlInterface(strDbms):
    if strDbms.startswith('postgres'):
        return DdlPostgres(strDbms)
    elif strDbms.startswith('mysql'):
        return DdlMySql()
    elif strDbms.startswith('firebird'):
        return DdlFirebird()
    else:
        assert(false)
        
if __name__ == "__main__":
    import os, sys
    sys.path += ['tests']
    from diffXml2DdlTest import doTests
    
    os.chdir('./tests')
    doTests()
