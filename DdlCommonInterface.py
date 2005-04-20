#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import re, os

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
            'drop_table_has_cascade' : False, # Test
            'no_alter_default' : False,
            'change_type_keyword' : 'ALTER',
            'TYPE' : 'TYPE ',
            'can_change_table_comment' : True,
            'no_rename_col' : False,
            'drop_index'    : 'DROP INDEX %(index_name)s',
            'default_keyword' : 'DEFAULT',
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
        ddls.append(('Add Table Comment',
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

        diffs.append(('Drop Column', strAlter))
        
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
        ddls.append(('Add Column comment',
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
        diffs.append( ('Add key constraint',
            'ALTER TABLE %(table_name)s ADD CONSTRAINT %(pk_constraint)s PRIMARY KEY (%(keys)s)' % info))

    def dropKeyConstraint(self, strTable, strConstraintName, diffs):
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
            
        diffs.append(('Add Relation', 
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
            strPreDdl.append(('Add Autoincrement Generator',
                'CREATE GENERATOR %(seq_name)s' % info))
            strPostDdl.append(('Add Autoincrement Trigger',
                """CREATE TRIGGER %(ai_trigger)s FOR %(table_name)s
                BEFORE INSERT AS
                BEGIN
                    NEW.%(col_name)s = GEN_ID(%(seq_name)s, 1);
                END""" % info))
            return ''
        
        strPreDdl.append(('Add Autoincrement', 
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
            'default_keyword' : 'DROP DEFAULT',
            'column_type' : self.retColTypeEtc(col),
            'TYPE' : self.params['TYPE'],
        }
        
        if self.params['no_alter_default']:
            # Firebird
            diffs.append(
                ('Change Default', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s' % info))
        else:
            diffs.append(
                ('Change Default', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(default_keyword)s' % info))

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
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s' % info))
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
                ('Change Col Type', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s' % info))

    def renameView(self, strOldViewName, strNewViewName, newDefinition, newAttribs, diffs):
        self.dropView(strOldViewName, diffs)
        self.addView(strNewViewName, newDefinition, newAttribs, diffs)
    
    def dropView(self, strOldViewName, diffs):
        info = {
            'viewname' : self.quoteName(strOldViewName),
        }
        diffs.append(('Drop view',
            'DROP VIEW %(viewname)s' % info )
        )
    
    def addView(self, strNewViewName, strContents, attribs, diffs):
        info = {
            'viewname' : self.quoteName(strNewViewName),
            'contents' : strContents,
        }
        diffs.append(('Add view',  # OR REPLACE 
            'CREATE VIEW %(viewname)s AS %(contents)s' % info )
        )
    
    def updateView(self, strViewName, strContents, attribs, diffs):
        self.addView(strViewName, strContents, attribs, diffs)

    # Function stuff
    def renameFunction(self, strOldFunctionName, strNewFunctionName, newDefinition, newAttribs, diffs):
        self.dropFunction(strOldFunctionName, newAttribs['arguments'].split(','), diffs)
        self.addFunction(strNewFunctionName, newAttribs['arguments'].split(','), newAttribs['returns'], newDefinition, newAttribs, diffs)
    
    def dropFunction(self, strOldFunctionName, argumentList, diffs):
        paramList = [arg.split()[-1] for arg in argumentList]
        info = {
            'functionname' : self.quoteName(strOldFunctionName),
            'params'       : ', '.join(paramList),
        }
        diffs.append(('Drop function',
            'DROP FUNCTION %(functionname)s(%(params)s)' % info )
        )
    
    def addFunction(self, strNewFunctionName, argumentList, strReturn, strContents, attribs, diffs):
        info = {
            'functionname' : self.quoteName(strNewFunctionName),
            'arguments'  : ', '.join(argumentList),
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
    
    def updateFunction(self, strNewFunctionName, argumentList, strReturn, strContents, attribs, diffs):
        self.dropFunction(strNewFunctionName, argumentList, diffs)
        self.addFunction(strNewFunctionName, argumentList, strReturn, strContents, attribs, diffs)

    def retColTypeEtc(self, col):
        strNull = ''
        if 'null' in col:
            strVal = col.get('null')
            if re.compile('not|no', re.IGNORECASE).search(strVal):
                strNull = ' NOT NULL'

        strDefault = ''
        if 'default' in col:
            strDefault = ' ' + self.params['default_keyword'] + ' ' + col.get('default')
        elif self.dbmsType == 'mysql' and col.get('type') == 'timestamp':
            # MySQL silently sets the default to CURRENT_TIMESTAMP
            strRet += ' DEFAULT null'

        strType = col.get('type', None)
        strSize = col.get('size', None)
        strPrec = col.get('precision', None)
        
        if strPrec:
            strRet = '%s(%s, %s)%s%s' % (strType, strSize, strPrec, strDefault, strNull)
        elif strSize:
            strRet = '%s(%s)%s%s' % (strType, strSize, strDefault, strNull)
        else:
            strRet = '%s%s%s' % (strType, strDefault, strNull)

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
