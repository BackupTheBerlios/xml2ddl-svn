#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
""" The purpose of this file is to allow default naming schemes for tables, columns etc. 

For example, you may define an abbreviation for the table name and the column names will use
that abbreviation + "_" + the column name given in the XML file.

"""


def getTableName(table):
    return table.getAttribute('name')
    
def getColName(col):
    strAbbr = col.parentNode.parentNode.getAttribute('abbr')
    if len(strAbbr) > 0:
        return strAbbr + '_' + col.getAttribute('name')
    
    return col.getAttribute('name')
    
def getRelationName(relation):
    strConstraintName = relation.getAttribute('name')
    if len(strConstraintName) == 0:
        strConstraintName = "fk_%s" % (relation.getAttribute('column'))

    return strConstraintName

def getIndexName(strTableName, index):
    strIndexName = index.getAttribute("name")
    if strIndexName and len(strIndexName) > 0:
        return strIndexName
    
    cols = index.getAttribute("columns").split(',')
    cols = [col.strip() for col in cols ] # Remove spaces
    
    strIndexName = "idx_" + strTableName + '_'.join([col.strip() for col in cols])
    
    return strIndexName

def getPkContraintName(strTableName):
    return 'pk_%s' % (strTableName)
    

def getSeqName(strTableName, strColName):
    return '%s_%s_seq' % (strTableName, strColName)

def getAiTriggerName(strTableName, strColName):
    return 'ai_%s_%s' % (strTableName, strColName)