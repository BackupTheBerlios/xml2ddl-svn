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

        if col.getAttribute('default'):
            strRet += ' DEFAULT ' + col.getAttribute('default')
        
        return strRet

    def checkColDiff(self, old, new):
        strOldColType = self.retColTypeEtc(old)
        strNewColType = self.retColTypeEtc(new)
        
        if strNewColType != strOldColType:
            self.changeColType(self.strTableName, old.getAttribute('name'), strNewColType)
        elif new.getAttribute('name') != old.getAttribute('name'):
            self.renameColumn(self.strTableName, old.getAttribute('name'), new.getAttribute('name'))
        
        # Check for difference in comments.
        strNewComment = safeGet(new, 'desc')
        strOldComment = safeGet(old, 'desc')
        if strNewComment and strNewComment != strOldComment:
            # Fix to delete comments?
            aCreate = xml2ddl.Xml2Ddl()
            aCreate.setDbms(self.dbmsType)
    
            aCreate.addColumnComment(new, self.strTableName, new.getAttribute('name'), strNewComment)
            self.diffs.extend(aCreate.dmls)
            

    def renameColumn(self, strTable, strOldName, strNewName):
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
            table = self.findTable(self.old_xml, strTable)
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
    
    def changeColType(self, strTableName, strColumnName, strNewColType):
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
            

    def newCol(self, new, after):
        info = { 
            'table_name' : self.strTableName,
            'column_name' : new.getAttribute('name'),
            'column_type' : self.retColTypeEtc(new) 
        }
        
        strAlter = 'ALTER TABLE %(table_name)s ADD %(column_name)s %(column_type)s' % info

        self.diffs.append(('Add Column', strAlter))

    def deletedCol(self, oldCol):
        info = { 
            'table_name' : self.strTableName,
            'column_name' : oldCol,
        }
        
        strAlter = 'ALTER TABLE %(table_name)s DROP %(column_name)s' % info

        self.diffs.append(('Dropped Column', strAlter))
        

    def diffTables(self, tbl_old, tbl_new):
        self.diffColumns(tbl_old, tbl_new)
        self.diffRelations(tbl_old, tbl_new)
        self.diffIndexes(tbl_old, tbl_new)
        self.diffTableComment(tbl_old, tbl_new)

    def diffColumns(self, old, new):
        newCols = new.getElementsByTagName('column')
        oldCols = old.getElementsByTagName('column')
        
        nOldIndex = 0
        skipCols = []
        for nIndex, newCol in enumerate(newCols):
            strNewColName = newCol.getAttribute('name')
            oldCol = self.findColumn(oldCols, strNewColName)
            
            if oldCol:
                self.checkColDiff(oldCol, newCol)
            else:
                if newCol.hasAttribute('oldname'):
                    strOldName = newCol.getAttribute('oldname')
                    oldCol = self.findColumn(oldCols, strOldName)
                    
                if oldCol:
                    self.renameColumn(self.strTableName, strOldName, strNewColName)
                    skipCols.append(strOldName)
                else:                    
                    self.newCol(newCol, nIndex)
            
        newCols = new.getElementsByTagName('column')
        oldCols = old.getElementsByTagName('column')
        for nIndex, oldCol in enumerate(oldCols):
            strOldColName = oldCol.getAttribute('name')
            if strOldColName in skipCols:
                continue
            newCol = self.findColumn(newCols, strOldColName)
            
            if not newCol:
                self.deletedCol(strOldColName)

    def findColumn(self, columns, strColName):
        for column in columns:
            strCurColName = column.getAttribute('name')
            if strCurColName == strColName:
                return column
            
            if column.hasAttribute('oldname'):
                strCurColName = column.getAttribute('name')
                if strCurColName == strColName:
                    return column
        
        return None
        
    def findTable(self, xml, strTableName):
        for tbl in xml.getElementsByTagName('table'):
            strCurTableName = tbl.getAttribute('name')
            if strCurTableName == strTableName:
                return tbl
            
            if tbl.hasAttribute('oldname'):
                strCurTableName = tbl.getAttribute('oldname')
                if strCurTableName == strTableName:
                    return tbl
        
        return None
        
    def diffIndexes(self, old_xml, new_xml):
        pass
        #print "TODO: diffIndexes"
    
    def diffRelations(self, old_xml, new_xml):
        pass
        #print "TODO: diffRelations"
    
    def createTable(self, xml):
        aCreate = xml2ddl.Xml2Ddl()
        aCreate.setDbms(self.dbmsType)
        aCreate.params['drop-tables'] = False

        aCreate.createTable(xml)
        self.diffs.extend(aCreate.dmls)

    def dropTable(self, xml):
        """ TODO: May need to kill some related constraints which I haven't coded yet. """
        
        strTableName = xml.getAttribute('name')
        strCascade = ''
        if self.params['drop_table_has_cascade']:
            strCascade = ' CASCADE'
        else:
            self.dropRelatedConstraints(strTableName)

        self.diffs.append(
            ('Drop Table', 'DROP TABLE %s%s' % (strTableName, strCascade)))
        

    def renameTable(self, tblOldXml, tblNewXml):
        strTableOld = tblOldXml.getAttribute('name')
        strTableNew = tblNewXml.getAttribute('name')
        
        self.diffs.append(('Rename Table',
            'ALTER TABLE %s RENAME TO %s' % (strTableOld, strTableNew)) )

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

    def diffFiles(self, strOldFilename, strNewFilename):
        self.old_xml = xml2ddl.readMergeDict(strOldFilename) # parse an XML file by name
        self.new_xml = xml2ddl.readMergeDict(strNewFilename)
        
        self.diffDocuments(self.old_xml, self.new_xml)

        self.old_xml.unlink()
        self.new_xml.unlink()
        
        return self.diffs

    def diffDocuments(self, strOldFilename, strNewFilename):
        self.diffs = []
        
        tbl_news = self.new_xml.getElementsByTagName('table')
        
        for tbl_new in tbl_news:
                
            self.strTableName = tbl_new.getAttribute('name')
            
            tbl_old = self.findTable(self.old_xml, self.strTableName)
            
            #print tbl_old.getAttribute('name'), '=', self.strTableName
            if not tbl_old:
                if tbl_new.hasAttribute('oldname'):
                    strOldName = tbl_new.getAttribute('oldname')
                    tbl_old = self.findTable(self.old_xml, strOldName)
                
                if tbl_old:
                    self.renameTable(tbl_old, tbl_new)
                else:
                    self.createTable(tbl_new)
            else:
                self.diffTables(tbl_old, tbl_new)
        
        # Scan for missing tables.
        tbl_olds = self.old_xml.getElementsByTagName('table')
        for tbl_old in tbl_olds:
            self.strTableName = tbl_old.getAttribute('name')
            
            tbl_new = self.findTable(self.new_xml, self.strTableName)
            
            if not tbl_new:
                self.dropTable(tbl_old)

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
    
    
