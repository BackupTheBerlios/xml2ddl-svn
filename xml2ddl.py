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

"""
Supports:
    - Primary keys and primary keys on multiple columns.
    - Foreign key relations (constraint)
        - todo: on delete cascade
        - todo: multiple fk constraints
    - Variable types:
        - todo: numeric with size+accuracy
    - Check constraint
    - UNIQUE constraint
    
Notes:
    - I explicitly set the constraint names instead of using the defaults for things like PRIMARY KEY
      etc.  This makes it easier to perform modifications when needed. There is no way to 
      specify the constraint names in the XML (at the moment)
    - 

TODO:
    - encrypted
    - desc
    - autoincrement
    - handling of tables, columns with spaces & other special characters

http://weblogs.asp.net/jamauss/articles/DatabaseNamingConventions.aspx

"""

class Xml2Ddl:
    def __init__(self):
        self.dbms = 'postgres'
        self.params = {
            'drop-tables' : True,
            'output_primary_keys' : True,
            'output_references' : True,
            'output_indexes' : True,
            'add_dataset' : True,
            'table_desc' : "COMMENT ON TABLE %(table)s IS '%(desc)s'",
            'column_desc' : "COMMENT ON COLUMN %(table)s.%(column)s IS '%(desc)s'",
        }
        self.dmls = []
        
    def setDbms(self, dbms):
        self.dbms = dbms.lower()
        if dbms == 'firebird':
            self.params['table_desc'] = "UPDATE RDB$RELATIONS SET RDB$DESCRIPTION = '%(desc)s'\n\tWHERE RDB$RELATION_NAME = upper('%(table)s')"
            self.params['column_desc'] = "UPDATE RDB$RELATION_FIELDS SET RDB$DESCRIPTION = '%(desc)s'\n\tWHERE RDB$RELATION_NAME = upper('%(table)s') AND RDB$FIELD_NAME = upper('%(column)s')"
        elif dbms == 'mysql':
            self.params['table_desc'] = "ALTER TABLE %(table)s COMMENT '%(desc)s'"
            self.params['column_desc'] = "ALTER TABLE %(table)s MODIFY %(column)s %(type)sCOMMENT '%(desc)s'"
            
    
    def retColDefs(self, doc):
        colDefs = []
        cols = doc.getElementsByTagName('column')
        for col in cols:
            colDefs.append(self.retColumnDefinition(col))
    
        return colDefs
    
    def retColumnDefinition(self, col):
        strColName = col.getAttribute('name')
        
        strRet = strColName + ' ' + self.getColType(col)
        
        if col.hasAttribute('null') and col.getAttribute('null') == 'no':
            strRet += ' NOT NULL'
        
        return strRet
        
    def getColType(self, col):
        strColType = col.getAttribute('type')
        nSize = None
        if col.hasAttribute('precision'):
            nSize = int(col.getAttribute('size'))
            nPrec = int(col.getAttribute('precision'))
            strRet = '%s(%d, %d)' % (strColType, nSize, nPrec)
        elif col.hasAttribute('size'):
            nSize = int(col.getAttribute('size'))
            strRet = '%s(%d)' % (strColType, nSize)
        else:
            strRet = '%s' % (strColType)
        
        return strRet
        
    def retKeys(self, doc):
        columns = doc.getElementsByTagName('column')
        keys = []
        for column in columns:
            if column.hasAttribute('key'):
                keys.append(column.getAttribute('name'))
        
        return keys

    def addRelations(self, doc):
        if not self.params['output_references']:
            return
            
        relations = doc.getElementsByTagName('relation')
        strTableName = doc.getAttribute('name')
        
        relList = []
        for relation in relations:
            strThisColName = relation.getAttribute('column')
            strOtherTable = relation.getAttribute('table')

            if relation.hasAttribute('fk'):
                strFk = relation.getAttribute('fk')
            else:
                strFk = strThisColName
            
            strConstraintName = relation.getAttribute('name')
            if len(strConstraintName) == 0:
                strConstraintName = "fk_%s" % (strThisColName)
            
            relList.append('ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s(%s)' % 
                (strTableName, strConstraintName, strThisColName, strOtherTable, strFk))
        
        for relation in relList:
            self.dmls.append(('relation', relation))

    def addIndexes(self, doc):
        if not self.params['output_indexes']:
            return
            
        strTableName = doc.getAttribute('name')
        indexes = doc.getElementsByTagName('index')
        for index in indexes:
            self.addIndex(strTableName, index)

    def addIndex(self, strTableName, index):
        strColumns = index.getAttribute("columns")
        strIndexName = self.getIndexName(strTableName, index)
        cols = strColumns.split(',')
        cols = index.getAttribute("columns").split(',')
        
        self.dmls.append(('Add Index',
            'CREATE INDEX %s ON %s (%s)' % (strIndexName, strTableName, ', '.join(cols)) ))
    
    def getIndexName(self, strTableName, index):
        strIndexName = index.getAttribute("name")
        if strIndexName and len(strIndexName) > 0:
            return strIndexName
        
        cols = index.getAttribute("columns").split(',')
        cols = [ col.strip() for col in cols ] # Remove spaces
        
        strIndexName = strTableName + '_'.join([col.title() for col in cols])
        
        return strIndexName
        
    def col2Type(self, doc):
        ret = {}
        for col in doc.getElementsByTagName('column'):
            strColName = col.getAttribute('name')
            strType = col.getAttribute('type')
            ret[strColName] = strType
        
        return ret
        
    def addDataset(self, doc):
        if not self.params['add_dataset']:
            return
        
        strTableName = doc.getAttribute('name')
        
        datasets = doc.getElementsByTagName('val')
        
        col2Type = self.col2Type(doc)
        
        for dataset in datasets:
            cols = []
            vals = []
            attribs = dataset.attributes
            for nIndex in range(attribs.length):
                strColName = attribs.item(nIndex).name
                strColValue = attribs.item(nIndex).value
                
                cols.append(strColName)
                
                strType = col2Type[strColName].lower()
                if strType == 'varchar' or strType == 'char':
                    # TODO: do more types
                    vals.append("'%s'" % (strColValue))
                else:
                    vals.append(strColValue)
            
            self.dmls.append(('dataset',
                'INSERT INTO %s (%s) VALUES (%s)' % (strTableName, ', '.join(cols), ', '.join(vals))))
        
    def createTable(self, doc):
        strTableName = doc.getAttribute('name')
        
        if self.params['drop-tables']:
            self.dmls.append(
                ('Drop table', 'DROP TABLE %s' % (strTableName)))
        
        
        colDefs = self.retColDefs(doc)
        
        keys = self.retKeys(doc)
        if len(keys) > 0:
            strPrimaryKeys = ',\n\tCONSTRAINT pk_%s PRIMARY KEY (%s)' % (strTableName, ',\n\t'.join(keys))
        else:
            strPrimaryKeys = '\n'
        
        self.dmls.append(
            ('Create Table', 'CREATE TABLE %s (\n\t%s%s)' % (strTableName, ',\n\t'.join(colDefs), strPrimaryKeys)))
        
        if doc.hasAttribute('desc'):
            self.addTableComment(strTableName, doc.getAttribute('desc'))
            
        self.addColumnComments(doc)
        self.addRelations(doc)
        self.addIndexes(doc)
        self.addDataset(doc)
    
    def addTableComment(self, tableName, desc):
        """ TODO: Fix the desc for special characters """
        info = {
            'table' : tableName,
            'desc' : desc,
        }
        self.dmls.append(('Table Comment',
            self.params['table_desc'] % info ))

    def addColumnComments(self, doc):
        """ TODO: Fix the desc for special characters """
        strTableName = doc.getAttribute('name')
        
        for column in doc.getElementsByTagName('column'):
            if column.hasAttribute('desc'):
                self.addColumnComment(column, strTableName, column.getAttribute('name'), column.getAttribute('desc'))

    def addColumnComment(self, col, strTableName, strColumnName, strDesc):
        info = {
            'table' : strTableName,
            'column' : strColumnName,
            'desc' :  strDesc,
            'type' : self.getColType(col) + ' ',
        }
        self.dmls.append(('Column comment',
            self.params['column_desc'] % info ))

    def createTables(self, xml):
        self.dmls = []
        
        # Should double check here that there is only one table.
        tbls = xml.getElementsByTagName('table')
        
        for tbl in tbls:
            self.createTable(tbl)
            
        xml.unlink()
        return self.dmls

def readDict(dictionaryNode):
    dict = {}
    for adict in dictionaryNode.getElementsByTagName('dict'):
        strClass = adict.getAttribute('class')
        if strClass in dict:
            newDict = dict[strClass]
        else:
            newDict = {}
        
        attrs = adict.attributes
        for nIndex in range(attrs.length):
            strName = attrs.item(nIndex).name
            strValue = attrs.item(nIndex).value
            
            if strName == 'class':
                # Skip the class
                continue
            elif strName == 'inherits':
                # Merge in the inherited values (multiple inheritance supported with comma
                classes = strValue.split(',')
                for aClass in classes:
                    if aClass not in dict:
                        print "class '%s' not found in dictionary" % (aClass)
                    else:
                        for key, val in dict[str(aClass)].items():
                            if key not in newDict:
                                newDict[key] = val
            else:
                newDict[str(strName)] = str(strValue)
                
        dict[str(strClass)] = newDict
    
    return dict

def readMergeDict(strFilename):
    ret = parse(strFilename)
    
    handleIncludes(ret)
    
    handleDictionary(ret)
    
    return ret

def handleIncludes(ret):
    includes = ret.getElementsByTagName('include')
    if not includes:
        return
    
    for include in includes:
        strHref = include.getAttribute('href')
        print "Including", strHref
        new = None
        try:
            new = parse(strHref)
        except Exception, e:
            print e
            
        if not new:
            print "Unable to include '%s'" % (strHref)
            continue
        
        include.parentNode.insertBefore(new.documentElement.firstChild.nextSibling, include)
        # I could delete the <include> node, but why bother?
        
    
def handleDictionary(ret):
    dictionaries = ret.getElementsByTagName('dictionary')
    if not dictionaries:
        return
    
    for aNode in dictionaries:
        strReplaceNodes = aNode.getAttribute('name')
        
        dict = readDict(aNode)
    
        for column in ret.getElementsByTagName(str(strReplaceNodes)):
            strClass = column.getAttribute('class')
            if not strClass:
                continue
            
            if strClass in dict:
                # Merge in the attributes
                for key, val in dict[strClass].items():
                    # Don't blow away already existing attributes
                    if not column.hasAttribute(key):
                        column.setAttribute(key, val)
            else:
                print "Error class name not found '%s'" % (strClass)
    
    
if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-d", "--drop",
                  action="store_true", dest="bDrop", default=True,
                  help="Drop Tables")
    parser.add_option("-b", "--dbms",
                  dest="strDbms", metavar="DBMS", default="postgres",
                  help="Output for which Database System")
                  
    (options, args) = parser.parse_args()

    cd = Xml2Ddl()
    cd.setDbms(options.strDbms)
    cd.params['drop-tables'] = options.bDrop
    
    strFilename = args[0]
    xml = readMergeDict(strFilename)
    results = cd.createTables(xml)
    for result in results:
        print "%s;" % (result[1])
    
    
