#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-


def getTableName(table):
    return table.getAttribute('name')
    
def getColName(col):
    return col.getAttribute('name')