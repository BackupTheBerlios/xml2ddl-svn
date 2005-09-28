#Store your connection information here
#
conn_info = {
#~     _    _    _    _    _    _    _  
#~    / \  / \  / \  / \  / \  / \  / \ 
#~  ( W )( A )( R )( N )( I )( N )( G )
#~   \_/  \_/  \_/  \_/  \_/  \_/  \_/ 
# Don't point to any database you care about
# The test programs delete whole tables, functions, views, etc.
# It is possible that it deletes your entire database 
# I usually test on an empty database
# You have been warned.
#
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
        'pass'   : 'mysql',
    },
    'oracle' : {
        'dbname' : 'test', # DSN Name
        'user'   : 'scott',
        'pass'   : 'tiger',
    },
}