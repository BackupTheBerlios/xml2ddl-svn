import re, os
import xml2ddl
from xml.dom.minidom import parse, parseString

"""
TODO:
    - DESC
    - handling of spaces in column names, table names
    - Unique constraint
    - check constraint
"""

class FindChanges:
    def __init__(self):
        self.dbmsType = 'postgres'
        self.reset()
        
    def reset(self):
        self.strTableName = None
        self.diffs = []
        self.params = {
            'drop_constraints_on_col_rename' : False,
            'rename_keyword' : 'RENAME', # or ALTER
            'no_alter_column_type' : False,
            'drop_table_has_cascade' : True,
            'change_type_keyword' : 'ALTER',
            'TYPE' : 'TYPE ',
            'can_change_table_comment' : True,
        }
    
    def setDbms(self, dbmsType):
        self.reset()
        self.dbmsType = dbmsType.lower()
        if self.dbmsType not in ['postgres', 'postgres7', 'mysql', 'oracle', 'firebird']:
            print "Unknown dbms %s" % (dbmsType)
        
        if self.dbmsType == 'postgres7':
            self.params['no_alter_column_type'] = True
            
        if self.dbmsType == 'firebird':
            self.params['rename_keyword'] = 'ALTER'
            self.params['drop_constraints_on_col_rename'] = True
            self.params['drop_table_has_cascade'] = False
        if self.dbmsType == 'mysql':
            self.params['change_type_keyword'] = 'MODIFY'
            self.params['TYPE'] = ''
            self.params['can_change_table_comment'] = False
        
    def retColTypeEtc(self, col):
        strNull = ''
        if col.getAttribute('null'):
            strVal = col.getAttribute('null')
            if re.compile('not', re.IGNORECASE).search(strVal):
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
                'table_name' : strTableName,
                'column_name' : new.getAttribute('name'),
                'change_type_keyword' : self.params['change_type_keyword'],
                'new_default' : strNewDefault,
            }
            
            self.diffs.append(
                ('Change Default', 
                'ALTER TABLE %(table_name)s %(change_type_keyword)s %(column_name)s DEFAULT %(new_default)s' % info))

    def changeColComments(self, strTableName, old, new):
        # Check for difference in comments.
        strNewComment = safeGet(new, 'desc')
        strOldComment = safeGet(old, 'desc')
        if strNewComment and strNewComment != strOldComment:
            # Fix to delete comments?
            aCreate = xml2ddl.Xml2Ddl()
            aCreate.setDbms(self.dbmsType)
    
            aCreate.addColumnComment(new, strTableName, new.getAttribute('name'), strNewComment)
            self.diffs.extend(aCreate.dmls)
            

    def renameColumn(self, strTable, old, new):
        strOldName = old.getAttribute('name')
        strNewName = new.getAttribute('name')
        
        info = {
            'table_name' : strTable,
            'old_col_name' : strOldName,
            'new_col_name' : strNewName,
            'rename'       : self.params['rename_keyword'],
        }
        
        if self.params['drop_constraints_on_col_rename']:
            self.dropRelatedConstraints(strTable, strOldName)
        
        # I think Firebird it's ALTER COLUMN instead of RENAME COLUMN
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
                            self.addRelation(table.getAttribute('name'), strCurColName, strTable, fk)

    def addKeyConstraint(self, tableDoc):
        strTableName = tableDoc.getAttribute('name')
        columns = tableDoc.getElementsByTagName('column')
        keys = []
        for column in columns:
            if column.hasAttribute('key'):
                keys.append(column.getAttribute('name'))
        
        self.diffs.append( ('Create primary keys',
                'ALTER TABLE %s ADD CONSTRAINT pk_%s PRIMARY KEY (%s)' % (strTableName, strTableName, ', '.join(keys))) )

    def addRelation(self, strTable, strColumn, strRelatedTable, strRelatedColumn):
        """ Todo Missing multicolumn relations """
        self.diffs.append( ('Create relation ',
                'ALTER TABLE %s ADD CONSTRAINT fk_%s FOREIGN KEY (%s) REFERENCES %s(%s)' % 
                    (strTable, strColumn, strColumn, strRelatedTable, strRelatedColumn)) )

        
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
                            pkList.append(self.dropKeyConstraint(strTable))
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
        
    def dropRelation(self, strTable, strColumnName):
        return ('Drop relation constraint', 
            'ALTER TABLE %s DROP CONSTRAINT fk_%s' % (strTable, strColumnName))
    
    def dropKeyConstraint(self, strTable):
        return ('Drop key constraint', 
            'ALTER TABLE %s DROP CONSTRAINT pk_%s' % (strTable, strTable))
    
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
            

    def newCol(self, strTableName, new, nAfter):
        """ nAfter not used yet """
        
        info = { 
            'table_name' : strTableName,
            'column_name' : new.getAttribute('name'),
            'column_type' : self.retColTypeEtc(new) 
        }
        
        strAlter = 'ALTER TABLE %(table_name)s ADD %(column_name)s %(column_type)s' % info

        self.diffs.append(('Add Column', strAlter))

    def deletedCol(self, strTableName, oldCol):
        info = { 
            'table_name' : strTableName,
            'column_name' : oldCol.getAttribute('name'),
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
            aCreate = xml2ddl.Xml2Ddl()
            aCreate.setDbms(self.dbmsType)
            aCreate.addTableComment(self.strTableName, strNewComment)
            self.diffs.extend(aCreate.dmls)

    def diffColumns(self, old, new):
        self.diffSomething(old, new, 'column', self.renameColumn,  self.changeCol, self.newCol, self.deletedCol, self.findColumn)

    def diffSomething(self, old, new, strTag, renameFunc, changeFunc, insertFunc, deleteFunc, findSomething):
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
                    insertFunc(self.strTableName, newCol, nIndex)
            
        newCols = new.getElementsByTagName(strTag)
        oldCols = old.getElementsByTagName(strTag)
        for nIndex, oldCol in enumerate(oldCols):
            strOldColName = oldCol.getAttribute('name')
            if strOldColName in skipCols:
                continue
            
            newCol = findSomething(newCols, strOldColName)
            
            if not newCol:
                deleteFunc(old.getAttribute('name'), oldCol)
        
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
        aCreate = xml2ddl.Xml2Ddl()
        aCreate.setDbms(self.dbmsType)

        aCreate.addIndex(self.strTableName, new)
        self.diffs.extend(aCreate.dmls)

    def deleteIndex(self, strTableName, old):
        aCreate = xml2ddl.Xml2Ddl()
        aCreate.setDbms(self.dbmsType)
        strIndexName = aCreate.getIndexName(strTableName, old)

        self.diffs += [('Drop Index', 'DROP INDEX %s' % (strIndexName))]
    
    def findIndex(self, indexes, strIndexName):
        for index in indexes:
            aCreate = xml2ddl.Xml2Ddl()
            aCreate.setDbms(self.dbmsType)
            strCurIndexName = aCreate.getIndexName(self.strTableName, index)
            if strCurIndexName == strIndexName:
                return index
            
        return None
        
    def diffRelations(self, old_xml, new_xml):
        self.diffSomething(old_xml, new_xml, 'relation', self.renameRelation, self.changeRelation, self.insertRelation, self.deleteRelation, self.findRelation)

    def renameRelation(self, strTableName, old, new):
        self.deleteRelation(strTableName, old)
        self.insertRelation(strTableName, new, -1)
    
    def changeRelation(self, strTableName, old, new):
        strColumnOld = old.getAttribute('column')
        strColumnNew = new.getAttribute('column')
        
        strTableOld = old.getAttribute('table')
        strTableNew = new.getAttribute('table')
        
        strFkOld = old.getAttribute('fk')
        strFkNew = old.getAttribute('fk')
        
        if len(strFkOld) == 0:
            strFkOld = strColumnOld
        
        if len(strFkNew) == 0:
            strFkNew = strColumnNew
        
        if strColumnOld != strColumnNew or strTableOld != strTableNew or strFkOld != strFkNew:
            self.deleteRelation(strTableName, old)
            self.insertRelation(strTableName, new, 0)
    
    def insertRelation(self, strTableName, new, nRelation):
        aCreate = xml2ddl.Xml2Ddl()
        aCreate.setDbms(self.dbmsType)

        aCreate.addRelation(self.strTableName, new)
        self.diffs.extend(aCreate.dmls)

    def deleteRelation(self, strTableName, old):
        aCreate = xml2ddl.Xml2Ddl()
        aCreate.setDbms(self.dbmsType)
        strRelationName = aCreate.getRelationName(strTableName, old)

        self.diffs += [('Drop Relation', 'DROP RELATION %s' % (strRelationName))]

    def findRelation(self, relations, strRelationName):
        for relation in relations:
            aCreate = xml2ddl.Xml2Ddl()
            aCreate.setDbms(self.dbmsType)
            strCurRelationName = aCreate.getRelationName(self.strTableName, relation)
            if strCurRelationName == strRelationName:
                return relation
            
        return None
        
    def createTable(self, strTableName, xml, nIndex):
        aCreate = xml2ddl.Xml2Ddl()
        aCreate.setDbms(self.dbmsType)
        aCreate.params['drop-tables'] = False

        aCreate.createTable(xml)
        self.diffs.extend(aCreate.dmls)

    def dropTable(self, strTableName, xml):
        """ TODO: May need to kill some related constraints which I haven't coded yet. """
        
        self.strTableName = xml.getAttribute('name')
        strCascade = ''
        if self.params['drop_table_has_cascade']:
            strCascade = ' CASCADE'
        else:
            self.dropRelatedConstraints(self.strTableName)

        self.diffs.append(
            ('Drop Table', 'DROP TABLE %s%s' % (self.strTableName, strCascade)))
        
    def renameTable(self, strTableName, tblOldXml, tblNewXml):
        strTableOld = tblOldXml.getAttribute('name')
        strTableNew = tblNewXml.getAttribute('name')
        
        self.diffs.append(('Rename Table',
            'ALTER TABLE %s RENAME TO %s' % (strTableOld, strTableNew)) )

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
    
    
