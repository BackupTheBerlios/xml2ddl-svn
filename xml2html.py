#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

import re, os
from xml.dom.minidom import parse, parseString
import xml2ddl

__author__ = "Scott Kirkwood (scott_kirkwood at berlios.com)"
__keywords__ = ['XML', 'DDL', 'SQL', 'Databases', 'Agile DB', 'ALTER', 'CREATE TABLE', 'GPL']
__licence__ = "GNU Public License (GPL)"
__longdescr__ = ""
__url__ = 'http://xml2ddl.berlios.de'
__version__ = "$Revision: 0.1 $"

""" Output HTML from XML """

class Xml2Html:
    def __init__(self):
        self.lines = []
        self.Xml2Ddl = xml2ddl.Xml2Ddl()
        
    def addHeader(self):
        schema = self.xml.getElementsByTagName('schema')
        strSchemaName = schema[0].getAttribute("name")
        self.lines += ['<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">']
        self.lines += ["<html>"]
        self.lines += ["<head>"]
        self.lines += ["<title>%s schema</title>" % (strSchemaName)]
        self.lines += ['<link  type="text/css" rel="stylesheet" type="text/css" href="schema.css" />']
        self.lines += ['</style>']


        self.lines += ["</head>"]
        self.lines += ["<body>"]
        
    def addTrailer(self):
        self.lines += ["</body>"]
        self.lines += ["</html>"]
        
    def outTables(self):
        tables = self.xml.getElementsByTagName('table')
        for table in tables:
            self.outputTable(table)
    
    def outputTable(self, table):
        strTableName = table.getAttribute("name")
        strDesc = table.getAttribute("desc")
        
        self.lines += ['<h1>%s</h1>' % (strTableName) ]
        self.lines += ['<div>%s</div>' % (strDesc) ]
        
        self.outputColumns(table)

        self.outputRelations(table)
        
        self.outputIndexes(table)

        self.outputDetailColumns(table)
        

    def outputColumns(self, table):
        self.lines += ['<table class="blue" border="1">']
        self.lines += ['<tr>']
        self.lines += ['<th>Column Name</th>']
        self.lines += ['<th>Full Name</th>']
        self.lines += ['<th>Data Type</th>']
        self.lines += ['<th>Null</th>']
        self.lines += ['<th>Key</th>']
        self.lines += ['</tr>']
        
        strTableName = table.getAttribute('name')
        for column in table.getElementsByTagName('column'):
            self.outputColumn(strTableName, column)
        
        self.lines += ['</table>']
        
    def outputColumn(self, strTableName, column):
        strColName = column.getAttribute('name')
        strFullName = column.getAttribute('fullname')
        strType = self.Xml2Ddl.getColType(column)
        strNull = column.getAttribute('null')
        strKey = column.getAttribute('key')
        
        self.lines += ['<tr>']
        self.lines += ['<td><a href="#full_%s.%s" id="%s.%s"/>%s</td>' % (strTableName, strColName, strTableName, strColName, strColName)  ]
        self.lines += ['<td>%s</td>' % strFullName]
        self.lines += ['<td>%s</td>' % strType]
        self.lines += ['<td>%s</td>' % strNull]
        self.lines += ['<td>%s</td>' % strKey]
        self.lines += ['</tr>']
    
    def outputDetailColumns(self, table):
        self.lines += ['<h3>Column Definitions</h3>']
        
        strTableName = table.getAttribute('name')
        
        self.lines += ['<table>']
        for column in table.getElementsByTagName('column'):
            self.outputDetailColumn(strTableName, column)
        self.lines += ['</table>']
        
    def outputDetailColumn(self, strTableName, column):
        strColName = column.getAttribute('name')
        self.lines += ['<tr><td class="def" id="full_%s.%s">' % (strTableName, strColName)]
        self.lines += [ '<a href="#%s.%s">%s</a></td>' % (strTableName, strColName, strColName) ]
        if column.hasAttribute('fullname'):
            strFullName = column.getAttribute('fullname')
            self.lines += ['<td class="extradef">%s</td>' % strFullName]
        else:
            self.lines += ['<td></td>']
        self.lines += ['</tr>']
        
        self.lines += ['<tr><td>&nbsp;</td>']
        self.lines += ['<td>']
        if column.hasAttribute('desc'):
            self.lines += [ column.getAttribute('desc') ]
        else:
            self.lines += [ "Requires detailed description" ]
        self.lines += ['</td></tr>']
        
    def outputRelations(self, table):
        relationsNode = table.getElementsByTagName('relations')
        if not relationsNode:
            return
        
        self.lines += ['<h3>Relations</h3>']
        
        strTableName = table.getAttribute('name')
        relations = relationsNode[0].getElementsByTagName('relation')
        self.lines += ['<table class="blue">']
        
        self.lines += ['<tr>']
        self.lines += ['<th>Column Name</th>']
        self.lines += ['<th>Related Table</th>']
        self.lines += ['<th>Related Column</th>']
        self.lines += ['</tr>']
        
        for relation in relations:
            self.outputRelation(strTableName, relation)
        
        self.lines += ['</table>']
        
    def outputRelation(self, strTableName, relation):
        strColName = relation.getAttribute('column')
        strFkTable = relation.getAttribute('table')
        strFkCol = relation.getAttribute('fk')
        
        if len(strFkCol) == 0:
            strFkCol = strColName
        
        self.lines += ['<tr><td class="def" id="full_%s.%s">' % (strTableName, strColName)]
        self.lines += [ '<a href="#%s.%s">%s</a></td>' % (strTableName, strColName, strColName) ]
        self.lines += ['<td>%s</td>' % (strFkTable) ]
        self.lines += ['<td><a href="#%s.%s">%s</a></td>' % (strFkTable, strFkCol, strFkCol) ]
        self.lines += ['</tr>']

        
    def outputIndexes(self, table):
        indexsNode = table.getElementsByTagName('indexes')
        if not indexsNode:
            return
        
        self.lines += ['<h3>Indexes</h3>']
        
        strTableName = table.getAttribute('name')
        indexs = indexsNode[0].getElementsByTagName('index')
        self.lines += ['<table class="blue">']
        
        self.lines += ['<tr>']
        self.lines += ['<th>Index Name</th>']
        self.lines += ['<th>Columns</th>']
        self.lines += ['</tr>']
        
        for index in indexs:
            self.outputIndex(strTableName, index)
        
        self.lines += ['</table>']
        
    def outputIndex(self, strTableName, index):
        strIndexName = index.getAttribute('name')
        strColumns = index.getAttribute('columns')
        
        self.lines += ['<tr>']
        self.lines += ['<td>%s</td>' % (strIndexName) ]
        self.lines += ['<td>%s</td>' % (strColumns) ]
        self.lines += ['</tr>']
        
    def outputHtml(self, xml):
        self.xml = xml
        self.lines = []
        
        self.addHeader()
        self.outTables()
        self.addTrailer()
        
        return self.lines
        
if __name__ == "__main__":
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                  help="write report to FILE", metavar="FILE")

    (options, args) = parser.parse_args()

    x2h = Xml2Html()
    
    strFilename = args[0]
    xml = xml2ddl.readMergeDict(strFilename)
    lines = x2h.outputHtml(xml)
    if options.filename:
        strOutfile = options.filename
    else:
        strOutfile = "outschema.html"
        
    of = open(strOutfile, "w")
    for line in lines:
        of.write("%s\n" % (line))
        
    of.close()
    
    
