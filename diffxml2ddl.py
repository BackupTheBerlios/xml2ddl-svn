import re, os
import xml2ddl
from xml.dom.minidom import parse, parseString

__author__ = "Scott Kirkwood (scott_kirkwood at berlios.com)"
__keywords__ = ['XML', 'DML', 'SQL', 'Databases', 'Agile DB', 'ALTER', 'CREATE TABLE', 'GPL']
__licence__ = "GNU Public License (GPL)"
__longdescr__ = ""
__url__ = 'http://xml2dml.berlios.de'
__version__ = "$Revision: 0.2 $"

"""
TODO:
    - DESC
    - handling of spaces in column names, table names
    - Unique constraint
    - check constraint
"""

class FindChanges:
    def __init__(self):
        self.xml2ddl = xml2ddl.Xml2Ddl()
        self._defaults()
        self.reset()
        
    def reset(self):
        self.strTableName = None
        self.diffs = []
        self.xml2ddl.reset()
        
    def _defaults(self):
        self.dbmsType = 'postgres'
        self.params = {
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
    
    def setDbms(self, dbmsType):
        self._defaults()
        self.reset()
        
        self.dbmsType = dbmsType.lower()
        self.xml2ddl.setDbms(self.dbmsType)
        
        if self.dbmsType not in ['postgres', 'postgres7', 'mysql', 'oracle', 'firebird']:
            print "Unknown dbms %s" % (dbmsType)
        elif self.dbmsType == 'postgres7':
            self.params['no_alter_column_type'] = True
        elif self.dbmsType == 'firebird':
            self.params['rename_keyword'] = 'ALTER'
            self.params['drop_constraints_on_col_rename'] = True
            self.params['drop_table_has_cascade'] = False
            self.params['no_alter_default'] = True
        elif self.dbmsType == 'mysql':
            self.params['rename_keyword'] = 'ALTER'
            self.params['no_rename_col'] = True
            self.params['change_type_keyword'] = 'MODIFY'
            self.params['TYPE'] = ''
            self.params['can_change_table_comment'] = False
            self.params['drop_index'] = 'DROP INDEX %(index_name)s ON %(table_name)s'
            

    def retColTypeEtc(self, col):
        strNull = ''
        if col.getAttribute('null'):
            strVal = col.getAttribute('null')
            if re.compile('not|no', re.IGNORECASE).search(strVal):
                strNull = ' NOT NULL'
        
        strType = col.getAttribute('type')
        strSize = col.getAttribute('size')
        strPrec = col.getAttribute('precision')
        
        if strPrec:
            strRet = '%s(%s, %s)%s' % (strType, strSize, strPrec, strNull)
        elif strSize:
            strRet = '%s(%s)%s' % (strType, strSize, strNull)
        else:
            strRet = '%s%s' % (strType, strNull)

        return strRet

    def changeCol(self, strTableName, old, new):
        self.changeColType(strTableName, old, new)
        
        self.changeColDefaults(strTableName, old, new)
        
        self.changeColComments(strTableName, old, new)

    def changeColType(self, strTableName, old, new):
        strOldColType = self.retColTypeEtc(old)
        strNewColType = self.retColTypeEtc(new)
        
        # TODO: I think this is wrong if change name and type at the same time.
        if strNewColType != strOldColType:
            self.doChangeColType(strTableName, old.getAttribute('name'), strNewColType)
        elif new.getAttribute('name') != old.getAttribute('name'):
            self.renameColumn(strTableName, old, new)

    def changeColDefaults(self, strTableName, old, new):
        strOldDefault = old.getAttribute('default')
        strNewDefault = new.getAttribute('default')
        if strNewDefault != strOldDefault:
            info = {
                'table_name' : self.xml2ddl.quoteName(strTableName),
                'column_name' : self.xml2ddl.quoteName(new.getAttribute('name')),
                'change_type_keyword' : 'ALTER',
                'new_default' : strNewDefault,
                'default_keyword' : 'SET DEFAULT',
                'column_type' : self.retColTypeEtc(new),
                'TYPE' : self.params['TYPE'],
            }
            
            if self.params['no_alter_default']:
                # Firebird
                self.diffs.append(
                    ('Change Default', 
                    'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s DEFAULT %(new_default)s' % info))
            else:
                self.diffs.append(
                    ('Change Default', 
                    'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(default_keyword)s %(new_default)s' % info))

    def changeColComments(self, strTableName, old, new):
        # Check for difference in comments.
        strNewComment = safeGet(new, 'desc')
        strOldComment = safeGet(old, 'desc')
        if strNewComment and strNewComment != strOldComment:
            # Fix to delete comments?
            self.xml2ddl.reset()
    
            self.xml2ddl.addColumnComment(new, strTableName, new.getAttribute('name'), strNewComment)
            self.diffs.extend(self.xml2ddl.ddls)
            

    def renameColumn(self, strTable, old, new):
        strOldName = old.getAttribute('name')
        strNewName = new.getAttribute('name')
        
        info = {
            'table_name'   : self.xml2ddl.quoteName(strTable),
            'old_col_name' : self.xml2ddl.quoteName(strOldName),
            'new_col_name' : self.xml2ddl.quoteName(strNewName),
            'rename'       : self.params['rename_keyword'],
            'column_type'  : self.retColTypeEtc(new), 
        }
        
        if self.params['drop_constraints_on_col_rename']:
            self.dropRelatedConstraints(strTable, strOldName)
        
        if self.params['no_rename_col']:
            # MySQL is like this
            self.diffs.append(
                ('Rename column',
                'ALTER TABLE %(table_name)s CHANGE %(old_col_name)s %(new_col_name)s %(column_type)s' % info))
        else:
            self.diffs.append(
                ('Rename column',
                'ALTER TABLE %(table_name)s %(rename)s %(old_col_name)s TO %(new_col_name)s' % info))

        if self.params['drop_constraints_on_col_rename']:
            self.rebuildRelatedConstraints(strTable, strNewName)
        
    def rebuildRelatedConstraints(self, strTable, strColumnName):
        tables = self.new_xml.getElementsByTagName('table')
        for table in tables:
            strCurTableName = table.getAttribute('name')
            if strCurTableName == strTable:
                # Find if the PK constraint is on this table
                for col in table.getElementsByTagName('column'):
                    strCurColName = col.getAttribute('name')
                    if strCurColName == strColumnName:
                        if col.hasAttribute('key'):
                            self.addKeyConstraint(table)
                            break
            else:
                relations = table.getElementsByTagName('relation')
                for relation in relations:
                    strCurTableName = relation.getAttribute('table')
                    if strCurTableName == strTable:
                        strCurColName = relation.getAttribute('name')
                        
                        fk = safeGet(relation, 'fk', strCurColName)
                        
                        if fk == strColumnName:
                            self.addRelation(table.getAttribute('name'), relation)

    def addKeyConstraint(self, tableDoc):
        """ The Primary Key constraint is always called pk_<tablename> and can't be changed """
        
        strTableName = tableDoc.getAttribute('name')
        columns = tableDoc.getElementsByTagName('column')
        keys = []
        for column in columns:
            if column.hasAttribute('key'):
                keys.append(column.getAttribute('name'))
        
        info = {
            'table_name'    : self.xml2ddl.quoteName(strTableName), 
            'pk_constraint' : self.xml2ddl.quoteName('pk_%s' % (strTableName)),
            'keys'          : ', '.join(keys),
        }
        self.diffs.append( ('Create primary keys',
            'ALTER TABLE %(table_name)s ADD CONSTRAINT %(pk_constraint)s PRIMARY KEY (%(keys)s)' % info))

    def dropKeyConstraint(self, strTable, col):
        # Note, apparently wasn't used
        info = {
            'table_name' : strTable,
            'constraint_name' : 'pk_%s_%s' % (strTable, col.getAttribute('name')),
        }
        return ('Drop key constraint', 
            'ALTER TABLE %(table_name)s DROP CONSTRAINT %(constraint_name)s' % info)
    
    def addRelation(self, strTable, relation):
        self.xml2ddl.reset()
        self.xml2ddl.addRelation(strTable, relation)
        self.diffs.extend(self.xml2ddl.ddls)
        
    def dropRelation(self, strTable, strColumnName):
        info = {
            'table_name' : strTable,
            'constraint_name' : 'fk_%s_%s' % (strTable, strColumnName),
        }
        return ('Drop relation constraint', 
            'ALTER TABLE %(table_name)s DROP CONSTRAINT %(constraint_name)s' % info)
    
    def dropRelatedConstraints(self, strTable, strColumnName = None):
        if strColumnName != None:
            self._dropRelatedConstraints(strTable, strColumnName)
        else:
            table = self.findTable(self.old_xml.getElementsByTagName('table'), strTable)
            columns = table.getElementsByTagName('column')
            for column in columns:
                self._dropRelatedConstraints(strTable, column.getAttribute('name'))
        
    def _dropRelatedConstraints(self, strTable, strColumnName):
        tables = self.old_xml.getElementsByTagName('table')
        
        relationLst = []
        pkList = []
        # need to sometimes reverse the order
        for table in tables:
            strCurTableName = table.getAttribute('name')
            if strCurTableName == strTable:
                # Find if the PK constraint is on this table
                for col in table.getElementsByTagName('column'):
                    strCurColName = col.getAttribute('name')
                    if strCurColName == strColumnName:
                        if col.hasAttribute('key'):
                            pkList.append(self.dropKeyConstraint(strTable, col))
                            break
            else:
                relations = table.getElementsByTagName('relation')
                for relation in relations:
                    strCurTableName = relation.getAttribute('table')
                    if strCurTableName == strTable:
                        strCurColName = relation.getAttribute('column')
                        
                        fk = safeGet(relation, 'fk', strCurColName)
                        
                        if len(strCurColName) > 0 and fk == strColumnName:
                            relationLst.append(self.dropRelation(table.getAttribute('name'), strCurColName))
        
        for relation in relationLst:
            self.diffs.append(relation)
        
        for pk in pkList:
            self.diffs.append(pk)
        
    def doChangeColType(self, strTableName, strColumnName, strNewColType):
        info = {
            'table_name' : strTableName,
            'column_name' : strColumnName,
            'column_type' : strNewColType,
            'change_type_keyword' : self.params['change_type_keyword'],
            'TYPE' : self.params['TYPE'],
        }
        
        if self.params['no_alter_column_type']:
            # For PostgreSQL 7.x you need to do...
            self.diffs.append( ('Add for change type',
                'ALTER TABLE %(table_name)s ADD tmp_%(column_name)s %(column_type)s' % info) )
            self.diffs.append( ('Copy the data over for change type',
                'UPDATE %(table_name)s SET tmp_%(column_name)s = %(column_name)s' % info) )
            self.diffs.append( ('Drop the old column for change type',
                'ALTER TABLE %(table_name)s DROP %(column_name)s' % info) )
            self.diffs.append( ('Rename column for change type',
                'ALTER TABLE %(table_name)s RENAME tmp_%(column_name)s TO %(column_name)s' % info) )
        else:
            self.diffs.append(
                ('Modify column', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s %(TYPE)s%(column_type)s' % info))
            

    def addColumn(self, strTableName, new, nAfter):
        """ nAfter not used yet """
        
        info = { 
            'table_name' : self.xml2ddl.quoteName(strTableName),
            'column_name' : self.xml2ddl.quoteName(new.getAttribute('name')),
            'column_type' : self.retColTypeEtc(new) 
        }
        
        strAlter = 'ALTER TABLE %(table_name)s ADD %(column_name)s %(column_type)s' % info

        self.diffs.append(('Add Column', strAlter))

    def dropCol(self, strTableName, oldCol):
        info = { 
            'table_name' : self.xml2ddl.quoteName(strTableName),
            'column_name' : self.xml2ddl.quoteName(oldCol.getAttribute('name')),
        }
        
        strAlter = 'ALTER TABLE %(table_name)s DROP %(column_name)s' % info

        self.diffs.append(('Dropped Column', strAlter))
        

    def diffTable(self, strTableName, tbl_old, tbl_new):
        """ strTableName is there just to be consistant with the other diff... """
        self.strTableName = tbl_new.getAttribute('name')
        
        self.diffColumns(tbl_old, tbl_new)
        self.diffRelations(tbl_old, tbl_new)
        self.diffIndexes(tbl_old, tbl_new)
        self.diffTableComment(tbl_old, tbl_new)

    def diffTableComment(self, tbl_old, tbl_new):
        strNewComment = safeGet(tbl_new, 'desc')
        strOldComment = safeGet(tbl_old, 'desc')

        if self.params['can_change_table_comment'] == False:
            return
            
        if strOldComment != strNewComment and strNewComment:
            self.xml2ddl.reset()
            self.xml2ddl.addTableComment(self.strTableName, strNewComment)
            self.diffs.extend(self.xml2ddl.ddls)

    def diffColumns(self, old, new):
        self.diffSomething(old, new, 'column', self.renameColumn,  self.changeCol, self.addColumn, self.dropCol, self.findColumn)

    def diffSomething(self, old, new, strTag, renameFunc, changeFunc, addFunc, deleteFunc, findSomething):
        newCols = new.getElementsByTagName(strTag)
        oldCols = old.getElementsByTagName(strTag)
        
        nOldIndex = 0
        skipCols = []
        for nIndex, newCol in enumerate(newCols):
            strNewColName = newCol.getAttribute('name')
            oldCol = findSomething(oldCols, strNewColName)
            
            if oldCol:
                changeFunc(self.strTableName, oldCol, newCol)
            else:
                if newCol.hasAttribute('oldname'):
                    strOldName = newCol.getAttribute('oldname')
                    oldCol = findSomething(oldCols, strOldName)
                    
                if oldCol:
                    renameFunc(self.strTableName, oldCol, newCol)
                    skipCols.append(strOldName)
                else:                    
                    addFunc(self.strTableName, newCol, nIndex)
            
        newCols = new.getElementsByTagName(strTag)
        oldCols = old.getElementsByTagName(strTag)
        for nIndex, oldCol in enumerate(oldCols):
            strOldColName = oldCol.getAttribute('name')
            if strOldColName in skipCols:
                continue
            
            newCol = findSomething(newCols, strOldColName)
            
            if not newCol:
                try:
                    strTableName = old.getAttribute('name')
                except:
                    strTableName = None
                
                deleteFunc(strTableName, oldCol)
        
    def findColumn(self, columns, strColName):
        for column in columns:
            strCurColName = column.getAttribute('name')
            if strCurColName == strColName:
                return column
            
        return None
        
    def findTable(self, tables, strTableName):
        for tbl in tables:
            strCurTableName = tbl.getAttribute('name')
            if strCurTableName == strTableName:
                return tbl
            
        return None
        
    def diffIndexes(self, old_xml, new_xml):
        self.diffSomething(old_xml, new_xml, 'index', self.renameIndex, self.changeIndex, self.insertIndex, self.deleteIndex, self.findIndex)

    def renameIndex(self, strTableName, old, new):
        self.deleteIndex(strTableName, old)
        self.insertIndex(strTableName, new, -1)
    
    def changeIndex(self, strTableName, old, new):
        strColumnsOld = old.getAttribute('columns')
        strColumnsNew = new.getAttribute('columns')
        if strColumnsOld != strColumnsNew:
            self.deleteIndex(strTableName, old)
            self.insertIndex(strTableName, new, 0)
    
    def insertIndex(self, strTableName, new, nIndex):
        self.xml2ddl.reset()

        self.xml2ddl.addIndex(self.strTableName, new)
        self.diffs.extend(self.xml2ddl.ddls)

    def deleteIndex(self, strTableName, old):
        self.xml2ddl.reset()
        strIndexName = self.xml2ddl.getIndexName(strTableName, old)
        info = { 
            'index_name' : self.xml2ddl.quoteName(strIndexName),
            'table_name' : strTableName,
        }
        self.diffs += [(
            'Drop Index', self.params['drop_index'] % info)]
    
    def findIndex(self, indexes, strIndexName):
        for index in indexes:
            self.xml2ddl.reset()
            strCurIndexName = self.xml2ddl.getIndexName(self.strTableName, index)
            if strCurIndexName == strIndexName:
                return index
            
        return None
        
    def diffRelations(self, old_xml, new_xml):
        self.diffSomething(old_xml, new_xml, 'relation', self.renameRelation, self.changeRelation, self.insertRelation, self.dropRelation, self.findRelation)

    def renameRelation(self, strTableName, old, new):
        self.dropRelation(strTableName, old)
        self.insertRelation(strTableName, new, -1)
    
    def changeRelation(self, strTableName, old, new):
        strColumnOld = old.getAttribute('column')
        strColumnNew = new.getAttribute('column')
        
        strTableOld = old.getAttribute('table')
        strTableNew = new.getAttribute('table')
        
        strFkOld = old.getAttribute('fk')
        strFkNew = old.getAttribute('fk')
        
        strDelActionOld = old.getAttribute('ondelete')
        strDelActionNew = new.getAttribute('ondelete')

        strUpdateActionOld = old.getAttribute('onupdate')
        strUpdateActionNew = old.getAttribute('onupdate')
        
        if len(strFkOld) == 0:
            strFkOld = strColumnOld
        
        if len(strFkNew) == 0:
            strFkNew = strColumnNew
        
        if strColumnOld != strColumnNew or strTableOld != strTableNew or strFkOld != strFkNew or strDelActionOld != strDelActionNew or strUpdateActionOld != strUpdateActionNew:
            self.dropRelation(strTableName, old)
            self.insertRelation(strTableName, new, 0)
    
    def insertRelation(self, strTableName, new, nRelation):
        self.xml2ddl.reset()

        self.xml2ddl.addRelation(self.strTableName, new)
        self.diffs.extend(self.xml2ddl.ddls)

    def dropRelation(self, strTableName, old):
        self.xml2ddl.reset()
        strRelationName = self.xml2ddl.getRelationName(old)

        info = {
            'tablename': self.xml2ddl.quoteName(strTableName),
            'constraintname' : strRelationName,
        }
        
        self.diffs += [
            ('Drop Relation', 'ALTER TABLE %(tablename)s DROP CONSTRAINT %(constraintname)s' % info)]

    def findRelation(self, relations, strRelationName):
        for relation in relations:
            self.xml2ddl.reset()
            strCurRelationName = self.xml2ddl.getRelationName(relation)
            if strCurRelationName == strRelationName:
                return relation
            
        return None
        
    def createTable(self, strTableName, xml, nIndex):
        self.xml2ddl.reset()
        self.xml2ddl.params['drop-tables'] = False

        self.xml2ddl.createTable(xml)
        self.diffs.extend(self.xml2ddl.ddls)

    def dropTable(self, strTableName, xml):
        """ TODO: May need to kill some related constraints which I haven't coded yet. """
        
        self.strTableName = xml.getAttribute('name')
        strCascade = ''
        if self.params['drop_table_has_cascade']:
            strCascade = ' CASCADE'
        else:
            self.dropRelatedConstraints(self.strTableName)

        info = {
            'table_name' : self.xml2ddl.quoteName(self.strTableName),
            'cascade'    : strCascade,
        }
        
        self.diffs.append(
            ('Drop Table', 'DROP TABLE %(table_name)s%(cascade)s' % info))
        
    def renameTable(self, strTableName, tblOldXml, tblNewXml):
        strTableOld = tblOldXml.getAttribute('name')
        strTableNew = tblNewXml.getAttribute('name')
        
        info = {
            'table_name' : self.xml2ddl.quoteName(strTableOld), 
            'new_table_name' : self.xml2ddl.quoteName(strTableNew),
        }
        self.diffs.append(('Rename Table',
            'ALTER TABLE %(table_name)s RENAME TO %(new_table_name)s' % info) )

    def diffFiles(self, strOldFilename, strNewFilename):
        self.old_xml = xml2ddl.readMergeDict(strOldFilename) # parse an XML file by name
        self.new_xml = xml2ddl.readMergeDict(strNewFilename)
        
        self.diffTables(self.old_xml, self.new_xml)

        self.old_xml.unlink()
        self.new_xml.unlink()
        
        return self.diffs

    def diffTables(self, old_xml, new_xml):
        self.old_xml = old_xml
        self.new_xml = new_xml
        
        self.diffSomething(old_xml, new_xml, 'table', self.renameTable,  self.diffTable, self.createTable, self.dropTable, self.findTable)
        
        return self.diffs
        
def safeGet(dom, strKey, default = None):
    if dom.hasAttribute(strKey):
        return dom.getAttribute(strKey)
    return default
    
if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-b", "--dbms",
                  dest="strDbms", metavar="DBMS", default="postgres",
                  help="Output for which Database System")
    (options, args) = parser.parse_args()

    fc = FindChanges()
    fc.setDbms(options.strDbms)
    strNewFile = args[0]
    if len(args) > 1:
        strOldFile = args[1]
    else:
        strOldFile = './.svn/text-base/%s.svn-base' % strNewFile
  
    results = fc.diffFiles(strOldFile, strNewFile)
    for result in results:
        print '%s;' % (result[1])
    
    
