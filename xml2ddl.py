
#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

import re, os
from xml.dom.minidom import parse, parseString
from ddlInterface import createDdlInterface, attribsToDict

__author__ = "Scott Kirkwood (scott_kirkwood at berlios.com)"
__keywords__ = ['XML', 'DML', 'SQL', 'Databases', 'Agile DB', 'ALTER', 'CREATE TABLE', 'GPL']
__licence__ = "GNU Public License (GPL)"
__longdescr__ = ""
__url__ = 'http://xml2dml.berlios.de'
__version__ = "$Revision: 0.2 $"

"""
Supports:
    - Primary keys and primary keys on multiple columns.
    - Foreign key relations (constraint)
        - todo: multiple fk constraints
    - Indexes
    - Check constraint - not done...
    - UNIQUE constraint - not done...
    - Autoincrement or the nearest equivalent depending on the database
    
Notes:
    - I explicitly set the constraint and index names instead of using the defaults for things like PRIMARY KEY
      etc.  This makes it easier to perform modifications when needed. There is no way to 
      specify the constraint names in the XML (at least the moment)

TODO:
    - encrypted flag?

http://weblogs.asp.net/jamauss/articles/DatabaseNamingConventions.aspx

"""

class Xml2Ddl:
    def __init__(self):
        self.ddlInterface = None
        self._setDefaults()
        self.reset()
        
    def reset(self):
        self.ddls = []
    
    def _setDefaults(self):
        self.dbmsType = 'postgres'
        self.params = {
            'drop-tables' : True,
            'output_primary_keys' : True,
            'output_references' : True,
            'output_indexes' : True,
            'add_dataset' : True,
        }

    def setDbms(self, dbms):
        self._setDefaults()
        
        self.ddlInterface = createDdlInterface(dbms)
        self.dbmsType = dbms.lower()


    def retColDefs(self, doc, strPreDdl, strPostDdl):
        colDefs = []
        strTableName = doc.getAttribute('name')
        cols = doc.getElementsByTagName('column')
        for col in cols:
            colDefs.append(self.retColumnDefinition(col, strPreDdl, strPostDdl))
        
        return colDefs
    
    def retColumnDefinition(self, col, strPreDdl, strPostDdl):
        strColName = col.getAttribute('name')
        
        strRet = self.ddlInterface.quoteName(strColName) + ' ' + self.ddlInterface.retColTypeEtc(attribsToDict(col))
        
        if col.hasAttribute('autoincrement') and col.getAttribute('autoincrement').lower() == "yes":
            strTableName = col.parentNode.parentNode.getAttribute('name')
            strRet += self.ddlInterface.addAutoIncrement(strTableName, strColName, col.getAttribute('default'), strPreDdl, strPostDdl)

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
        
        for relation in relations:
            self.ddlInterface.addRelation(strTableName, 
                self.getRelationName(relation), 
                relation.getAttribute('column'), 
                relation.getAttribute('table'),
                relation.getAttribute('fk'),
                relation.getAttribute('ondelete'),
                relation.getAttribute('onupdate'),
                self.ddls)
        
    def getRelationName(self, relation):
        strConstraintName = relation.getAttribute('name')
        if len(strConstraintName) == 0:
            strConstraintName = "fk_%s" % (relation.getAttribute('column'))

        return strConstraintName
    
    def addIndexes(self, doc):
        if not self.params['output_indexes']:
            return
            
        strTableName = doc.getAttribute('name')
        indexes = doc.getElementsByTagName('index')
        for index in indexes:
            strColumns = index.getAttribute("columns")
            self.ddlInterface.addIndex(strTableName, self.getIndexName(strTableName, index), strColumns.split(','), self.ddls)

    def getIndexName(self, strTableName, index):
        strIndexName = index.getAttribute("name")
        if strIndexName and len(strIndexName) > 0:
            return strIndexName
        
        cols = index.getAttribute("columns").split(',')
        cols = [ self.ddlInterface.quoteName(col.strip()) for col in cols ] # Remove spaces
        
        strIndexName = "idx_" + strTableName + '_'.join([col.strip() for col in cols])
        
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
                if strType in ('varchar', 'char', 'date', 'point'):
                    # TODO: do more types
                    vals.append(self.ddlInterface.quoteString(strColValue))
                else:
                    vals.append(strColValue)
            
            self.ddls.append(('dataset',
                'INSERT INTO %s (%s) VALUES (%s)' % (self.ddlInterface.quoteName(strTableName), ', '.join(cols), ', '.join(vals))))
        
    def createTable(self, doc):
        strTableName = self.ddlInterface.quoteName(doc.getAttribute('name'))
        
        if self.params['drop-tables']:
            self.ddlInterface.dropTable(strTableName, '', self.ddls)
        
        strPreDdl = []
        strPostDdl = []
        colDefs = self.retColDefs(doc, strPreDdl, strPostDdl)
        
        self.ddls += strPreDdl
        
        keys = self.retKeys(doc)
        strTableStuff = ''
        if len(keys) > 0:
            strPrimaryKeys = ',\n\tCONSTRAINT pk_%s PRIMARY KEY (%s)' % (strTableName, ',\n\t'.join(keys))
        else:
            strPrimaryKeys = '\n'
        
        if self.dbmsType == 'mysql':
            strTableStuff += ' ENGINE=InnoDB'
        if doc.hasAttribute('desc') and self.dbmsType == 'mysql':
            strTableStuff += " COMMENT=%s" % (self.ddlInterface.quoteString(doc.getAttribute('desc')))
        
        self.ddls.append(
            ('Create Table', 'CREATE TABLE %s (\n\t%s%s)%s' % (strTableName, ',\n\t'.join(colDefs), strPrimaryKeys, strTableStuff)))

        self.ddls += strPostDdl

        if doc.hasAttribute('desc'):
            self.addTableComment(strTableName, doc.getAttribute('desc'))
            
        self.addColumnComments(doc)
        self.addIndexes(doc)
        self.addRelations(doc)
        self.addDataset(doc)
    

    def addColumnComments(self, doc):
        """ TODO: Fix the desc for special characters """
        strTableName = doc.getAttribute('name')
        
        for column in doc.getElementsByTagName('column'):
            if column.hasAttribute('desc'):
                self.ddlInterface.addColumnComment(strTableName, column.getAttribute('name'), column.getAttribute('desc'), 'TODO', self.ddls)


    def createTables(self, xml):
        self.ddls = []
        
        # Should double check here that there is only one table.
        tbls = xml.getElementsByTagName('table')
        
        for tbl in tbls:
            self.createTable(tbl)
            
        xml.unlink()
        return self.ddls

    
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
    
    usage = "usage: %prog [options]"
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
    
