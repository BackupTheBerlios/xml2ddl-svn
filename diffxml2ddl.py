import re, os
import xml2ddl
import copy
from xml.dom.minidom import parse, parseString
from ddlInterface import createDdlInterface, attribsToDict

__author__ = "Scott Kirkwood (scott_kirkwood at berlios.com)"
__keywords__ = ['XML', 'DML', 'SQL', 'Databases', 'Agile DB', 'ALTER', 'CREATE TABLE', 'GPL']
__licence__ = "GNU Public License (GPL)"
__longdescr__ = ""
__url__ = 'http://xml2dml.berlios.de'
__version__ = "$Revision: 0.2 $"

"""
TODO:
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
            'no_alter_column_type' : False,
            'drop_table_has_cascade' : True,
            'can_change_table_comment' : True,
        }
    
    def setDbms(self, dbmsType):
        self._defaults()
        self.reset()
        
        self.dbmsType = dbmsType.lower()
        self.xml2ddl.setDbms(self.dbmsType)
        self.ddli = createDdlInterface(self.dbmsType)
        
        if self.dbmsType not in ['postgres', 'postgres7', 'mysql', 'oracle', 'firebird']:
            print "Unknown dbms %s" % (dbmsType)
        if self.dbmsType == 'firebird':
            self.params['drop_constraints_on_col_rename'] = True
            self.params['drop_table_has_cascade'] = False
        elif self.dbmsType == 'mysql':
            self.params['can_change_table_comment'] = False
            

    def changeAutoIncrement(self, strTableName, old, new):
        # Remove old, and new
        strOldAuto = old.getAttribute('autoincrement').lower()
        strNewAuto = new.getAttribute('autoincrement').lower()
        if strOldAuto != strNewAuto:
            if strNewAuto == 'yes':
                # Hmm, if we created the column the autoincrement would already be there anyway.
                pass
                #print "Add Autoincrement TODO"
            else:
                self.ddli.dropAutoIncrement(strTableName, attribsToDict(old), self.diffs)

    def changeCol(self, strTableName, old, new):
        self.changeColType(strTableName, attribsToDict(old), attribsToDict(new))
        
        self.changeAutoIncrement(strTableName, old, new)
        
        self.changeColDefaults(strTableName, old, new)
        
        self.changeColComments(strTableName, old, new)

    def changeColType(self, strTableName, old, new):
        strOldColType = self.ddli.retColTypeEtc(old)
        strNewColType = self.ddli.retColTypeEtc(new)
        
        if self.normalizedColType(strNewColType) != self.normalizedColType(strOldColType):
            self.ddli.doChangeColType(strTableName, old.get('name'), strNewColType, self.diffs)

    def normalizedColType(self, strColTypeEtc):
        if not self.bGenerated:
            return strColTypeEtc
        
        # The purpose here is to compare two column types and see if the appear to be the same (essentially).
        # I'm not trying to convert them to SQL9x which would make more sense, perhaps.
        strColTypeEtc = strColTypeEtc.lower();
        strColTypeEtc = strColTypeEtc.replace('integer', 'int')
        strColTypeEtc = strColTypeEtc.replace('numeric', 'decimal')
        strColTypeEtc = strColTypeEtc.replace('double precision', 'float' )
        strColTypeEtc = strColTypeEtc.replace('timestamp without time zone', 'timestamp')
        
        return strColTypeEtc
    
    def changeColDefaults(self, strTableName, old, new):
        strOldDefault = old.getAttribute('default')
        strNewDefault = new.getAttribute('default')
        if strNewDefault != strOldDefault:
            self.ddli.changeColDefault(strTableName, new.getAttribute('name'), strNewDefault, self.ddli.retColTypeEtc(attribsToDict(new)), self.diffs)

    def changeColComments(self, strTableName, old, new):
        # Check for difference in comments.
        strNewComment = safeGet(new, 'desc')
        strOldComment = safeGet(old, 'desc')
        if strNewComment and strNewComment != strOldComment:
            # Fix to delete comments?
            self.ddli.changeColumnComment(strTableName, new.getAttribute('name'), strNewComment, self.ddli.retColTypeEtc(attribsToDict(new)), self.diffs)
            

    def renameColumn(self, strTableName, old, new):
        strOldName = old.getAttribute('name')
        strNewName = new.getAttribute('name')
        
        if self.params['drop_constraints_on_col_rename']:
            self.dropRelatedConstraints(strTableName, strOldName)
            
        columnType = self.ddli.retColTypeEtc(attribsToDict(new))
        self.ddli.renameColumn(strTableName, strOldName, strNewName, columnType, self.diffs)
        
        if self.params['drop_constraints_on_col_rename']:
            self.rebuildRelatedConstraints(strTableName, strNewName)
        
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
                
        self.ddli.addKeyConstraint(strTableName, keys, self.diffs)
        
    def dropKeyConstraint(self, strTable, col, diffs):
        self.ddli.dropKeyConstraint(strTable, 'pk_%s' % (strTable), diffs)
    
    def addRelation(self, strTable, relation):
        self.ddli.addRelation(strTable, relation, self.diffs)
        
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
                            self.dropKeyConstraint(strTable, col, pkList)
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
        
    def dropRelatedSequences(self, strTableName):
        if self.dbmsType == 'firebird' or self.dbmsType.startswith('postgres'):
            table = self.findTable(self.old_xml.getElementsByTagName('table'), strTableName)
            columns = table.getElementsByTagName('column')
            for column in columns:
                self._dropRelatedSequence(strTableName, column)
            
            return
        
    def _dropRelatedSequence(self, strTableName, col):
        if col.getAttribute('autoincrement').lower() == 'yes':
            self.ddli.dropAutoIncrement(strTableName, attribsToDict(col), self.diffs)


    def addColumn(self, strTableName, new, nAfter):
        """ nAfter not used yet """
        
        self.ddli.addColumn(strTableName, new.getAttribute('name'), self.ddli.retColTypeEtc(attribsToDict(new)), nAfter, self.diffs)

    def dropCol(self, strTableName, oldCol):
        self.ddli.dropCol(strTableName, oldCol.getAttribute('name'), self.diffs)

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
            self.ddli.addTableComment(self.strTableName, strNewComment, self.diffs)

    def diffColumns(self, old, new):
        self.diffSomething(old, new, 'column', self.renameColumn,  self.changeCol, self.addColumn, self.dropCol, self.findColumn, self.getColName)

    def diffSomething(self, old, new, strTag, renameFunc, changeFunc, addFunc, deleteFunc, findSomething, getName):
        newXs = new.getElementsByTagName(strTag)
        oldXs = old.getElementsByTagName(strTag)
        
        nOldIndex = 0
        skipXs = []
        for nIndex, newX in enumerate(newXs):
            strnewXName = getName(newX)
            oldX = findSomething(oldXs, strnewXName)
            
            if oldX:
                changeFunc(self.strTableName, oldX, newX)
            else:
                if newX.hasAttribute('oldname'):
                    strOldName = newX.getAttribute('oldname')
                    oldX = findSomething(oldXs, strOldName)
                    
                if oldX:
                    changeFunc(self.strTableName, oldX, newX)
                    renameFunc(self.strTableName, oldX, newX)
                    skipXs.append(strOldName)
                    # Just in case user changed name and the type as well.
                else:                    
                    addFunc(self.strTableName, newX, nIndex)
            
        newXs = new.getElementsByTagName(strTag)
        oldXs = old.getElementsByTagName(strTag)
        for nIndex, oldX in enumerate(oldXs):
            stroldXName = getName(oldX)
            if stroldXName in skipXs:
                continue
            
            newX = findSomething(newXs, stroldXName)
            
            if not newX:
                try:
                    strTableName = old.getAttribute('name')
                except:
                    strTableName = None
                
                deleteFunc(strTableName, oldX)
        
    def getColName(self, col):
        return col.getAttribute('name')
        
    def findColumn(self, columns, strColName):
        strColName = strColName.lower()
        for column in columns:
            strCurColName = column.getAttribute('name').lower()
            if strCurColName == strColName:
                return column
            
        return None
        
    def getTableName(self, table):
        return table.getAttribute('name')

    def findTable(self, tables, strTableName):
        strTableName = strTableName.lower()
        for tbl in tables:
            strCurTableName = tbl.getAttribute('name').lower()
            if strCurTableName == strTableName:
                return tbl
            
        return None
        
    def diffIndexes(self, old_xml, new_xml):
        self.diffSomething(old_xml, new_xml, 'index', self.renameIndex, self.changeIndex, self.insertIndex, self.deleteIndex, self.findIndex, self.getIndexName)

    def renameIndex(self, strTableName, old, new):
        strColumns = new.getAttribute("columns")
        self.ddli.renameIndex(strTableName, 
            self.xml2ddl.getIndexName(strTableName, old), 
            self.xml2ddl.getIndexName(strTableName, new), 
            strColumns.split(','), 
            self.diffs)
    
    def deleteIndex(self, strTableName, old):
        strIndexName = self.xml2ddl.getIndexName(strTableName, old)
        self.ddli.deleteIndex(strTableName, strIndexName, self.diffs)

    def changeIndex(self, strTableName, old, new):
        strColumnsOld = old.getAttribute('columns').replace(' ', '').lower()
        strColumnsNew = new.getAttribute('columns').replace(' ', '').lower()
        if strColumnsOld != strColumnsNew:
            self.ddli.changeIndex(strTableName,
                self.xml2ddl.getIndexName(strTableName, old), 
                self.xml2ddl.getIndexName(strTableName, new), 
                strColumnsNew.split(','), 
                self.diffs)
    
    def insertIndex(self, strTableName, new, nIndex):
        strColumns = new.getAttribute("columns")
        self.ddli.addIndex(self.strTableName, self.xml2ddl.getIndexName(strTableName, new), strColumns.split(','), self.diffs)

    def getIndexName(self, index):
        return self.xml2ddl.getIndexName(self.strTableName, index)
        
    def findIndex(self, indexes, strIndexName):
        strIndexName = strIndexName.lower()
        for index in indexes:
            strCurIndexName = self.getIndexName(index).lower()
            if strCurIndexName == strIndexName:
                return index
            
        return None
        
    def diffRelations(self, old_xml, new_xml):
        self.diffSomething(old_xml, new_xml, 'relation', self.renameRelation, self.changeRelation, self.insertRelation, self.myDropRelation, self.findRelation, self.getRelationName)

    def renameRelation(self, strTableName, old, new):
        # TODO put in ddlinterface
        self.myDropRelation(strTableName, old)
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
            self.myDropRelation(strTableName, old)
            self.insertRelation(strTableName, new, 0)
    
    def insertRelation(self, strTableName, old, nIndex):
        strRelationName = self.xml2ddl.getRelationName(old)
        strFk = old.getAttribute('fk')
        strOnDelete = old.getAttribute('ondelete')
        strOnUpdate = old.getAttribute('onupdate')
        strFkTable = old.getAttribute('table')
        strColumn = old.getAttribute('column')
        self.ddli.addRelation(strTableName, strRelationName, strColumn, strFkTable, strFk, strOnDelete, strOnUpdate, self.diffs)

    def myDropRelation(self, strTableName, old):
        strRelationName = self.xml2ddl.getRelationName(old)
        self.ddli.dropRelation(strTableName, strRelationName, self.diffs)

    def getRelationName(self, relation):
        return self.xml2ddl.getRelationName(relation)
        
    def findRelation(self, relations, strRelationName):
        for relation in relations:
            strCurRelationName = self.getRelationName(relation)
            if strCurRelationName == strRelationName:
                return relation
            
        return None
        
    def createTable(self, strTableName, xml, nIndex):
        self.xml2ddl.reset()
        self.xml2ddl.params['drop-tables'] = False

        self.xml2ddl.createTable(xml)
        self.diffs.extend(self.xml2ddl.ddls)

    def dropTable(self, strTableName, xml):
        self.strTableName = xml.getAttribute('name')
        strCascade = ''
        if self.params['drop_table_has_cascade']:
            strCascade = ' CASCADE'
        else:
            self.dropRelatedConstraints(self.strTableName)

        self.dropRelatedSequences(self.strTableName)
        
        self.ddli.dropTable(self.strTableName, strCascade, self.diffs)
        
    def renameTable(self, strTableName, tblOldXml, tblNewXml):
        strTableOld = tblOldXml.getAttribute('name')
        strTableNew = tblNewXml.getAttribute('name')
        
        self.ddli.renameTable(strTableOld, strTableNew, self.diffs)

    def renameView(self, ignore, old, new):
        attribs = attribsToDict(new)
        strDefinition = new.firstChild.nodeValue.strip()
        
        self.ddli.renameView(old.getAttribute('name'), new.getAttribute('name'), strDefinition, attribs, self.diffs)
        
    def diffView(self, ignore, oldView, newView):
        strOldContents = oldView.firstChild.nodeValue.strip()
        strNewContents = newView.firstChild.nodeValue.strip()
        
        if strOldContents != strNewContents:
            attribs = attribsToDict(newView)
            strDefinition = newView.firstChild.nodeValue.strip()
            
            self.ddli.updateView(newView.getAttribute('name'), strDefinition, attribs, self.diffs)
        
    def createView(self, ignore, new, nIndex):
        attribs = attribsToDict(new)
        strDefinition = new.firstChild.nodeValue.strip()
        
        self.ddli.addView(new.getAttribute('name'), strDefinition, attribs, self.diffs)
        
    def dropView(self, ignore, view):
        self.ddli.dropView(view.getAttribute('name'), self.diffs)
        
    def findView(self, views, strViewName):
        strViewName = strViewName.lower()
        for view in views:
            strCurViewName = view.getAttribute('name').lower()
            if strCurViewName == strViewName:
                return view
            
        return None
        
    def getViewName(self, node):
        return node.getAttribute('name')

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
        
        self.bGenerated = False
        try:
            schema = new_xml.getElementsByTagName('schema')[0]
        except:
            schema = new_xml
            
        if schema.hasAttribute('generated'):
            self.bGenerated = True
            if schema.getAttribute('generated').lower() == 'no':
                self.bGenerated = False
            
        
        self.diffSomething(old_xml, new_xml, 'table', self.renameTable,  self.diffTable, self.createTable, self.dropTable, self.findTable, self.getTableName)

        self.diffSomething(old_xml, new_xml, 'view', self.renameView,  self.diffView, self.createView, self.dropView, self.findView, self.getViewName)

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
    
    
