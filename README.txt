XML to DDL
==========

This is a set of programs to create a database schema (structure) from an XML representation of the database.

There are 4 tools available:

  python xml2ddl.py --dbms <dbms> <schema.xml>
  
  python diffxml2ddl.py --dbms <dbms> <new-schema.xml> [<old-schema.xml>]
  
  python xml2html.py [-f <outfile.html>] <schema.xml>
  
  python downloadXml.py --dbms <dbms> --user <user> --pass <pass>

<dbms> can (currently) be one of: postgres, postgres7, mysql, or firefox

xml2ddl outputs the SQL (aka DDL) statements to standard output.

diffxml2ddl does the same but only the changes required to bring <old-schema.xml> up-to-date with <new-schema.xml>

xml2html creates one (currently) HTML file representation of the schema.

downloadXml.py Queries the server database and outputs it's resulting XML schema. Requires psycopg, MySQLdb or kinterbasdb.

More info available at index.html in the subdirectory doc.

Install
-------

Uncompress the files in a folder of your choosing.
The programs are best run from the command line.

Prerequesites
-------------

Requires Python 2.3.

Tested with:
    - PostgreSQL version 8.0.0beta2
    - MySQL version 5.0.1-alpha-nt
    - Firebird version 1.5.1

License
-------

GNU GPL http://www.gnu.org/copyleft/gpl.html
