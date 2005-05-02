#Store your connection information here
#
conn_info = {
    'firebird' : {
        'dbname' : 'mydb.db',
        'user'   : 'SYSDBA',
        'pass'   : 'masterkey',
    },
    'postgres' : {
        'host'   : 'localhost',
        'dbname' : 'testdb', 
        'user'   : 'postgres', 
        'pass'   : 'postgres', 
    },
    'mysql' : {
        'host'   : 'localhost',
        'dbname' : 'test',
        'user'   : 'root',
        'pass'   : '',
    },
    'oracle' : {
        'dbname' : 'test', # DSN Name
        'user'   : 'scott',
        'pass'   : 'tiger',
    },
}