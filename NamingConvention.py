#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-


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

