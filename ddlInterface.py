
#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

import re, os
from xml.dom.minidom import parse, parseString

__author__ = "Scott Kirkwood (scott_kirkwood at berlios.com)"
__keywords__ = ['XML', 'DML', 'SQL', 'Databases', 'Agile DB', 'ALTER', 'CREATE TABLE', 'GPL']
__licence__ = "GNU Public License (GPL)"
__longdescr__ = ""
__url__ = 'http://xml2dml.berlios.de'
__version__ = "$Revision: 0.2 $"

class DdlCommonInterface:
    def __init__(self, strDbms):
        self.dbmsType = strDbms
        self.params = {
            'drop-tables' : True,
            'output_primary_keys' : True,
            'output_references' : True,
            'output_indexes' : True,
            'add_dataset' : True,
            'table_desc' : "COMMENT ON TABLE %(table)s IS %(desc)s",
            'column_desc' : "COMMENT ON COLUMN %(table)s.%(column)s IS %(desc)s",
            'unquoted_id' : re.compile(r'^[A-Za-z][A-Za-z0-9_]+$'),
            'max_id_len' : { 'default' : 256 },
            'has_auto_increment' : False,
            'keywords' : [ 'NULL', 'SELECT', 'FROM' ],
            'quote_l' : '"',
            'quote_r' : '"',
        }

    def quoteName(self, strName):
        bQuoteName = False
        
        if not self.params['unquoted_id'].match(strName):
            bQuoteName = True

        if strName.upper() in self.params['keywords']:
            bQuoteName = True
        
        if not bQuoteName:
            if strName[0] == '"' and strName[-1] == '"':
                # Already quoted.
                bQuoteName = False

        if bQuoteName:
            return self.params['quote_l'] + strName + self.params['quote_r']
        
        return strName

    def quoteString(self, strStr):
        return "'%s'" % (strStr.replace("'", "''"))

class DdlPostgres(DdlCommonInterface):
    def __init__(self):
        DdlCommonInterface.__init__(self, 'postgres')
        

class DdlMySql(DdlCommonInterface):
    def __init__(self):
        DdlCommonInterface.__init__(self, 'mysql')
        self.params['quote_l'] = '`'
        self.params['quote_r'] = '`'

class DdlFirebird(DdlCommonInterface):
    def __init__(self):
        DdlCommonInterface.__init__(self, 'firebird')
        

def createDdlInterface(strDbms):
    if strDbms.startswith('postgres'):
        return DdlPostgres()
    elif strDbms.startswith('mysql'):
        return DdlMySql()
    elif strDbms.startswith('firebird'):
        return DdlFirebird()
    else:
        assert(false)
    