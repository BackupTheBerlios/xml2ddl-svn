XML to DDL
==========

This is a set of programs to create a database schema (structure) from an XML representation of the database.

There are 3 tools available:

  python xml2ddl.py --dbms <dbms> <schema.xml>
  
  python diffxml2ddl.py --dbms <dbms> <new-schema.xml> [<old-schema.xml>]
  
  python xml2html.py [-f <outfile.html>] <schema.xml>

<dbms> can (currently) be one of: postgres, postgres7, mysql, or firefox

xml2ddl outputs the SQL (aka DDL) statements to standard output.

diffxml2ddl does the same but only the changes required to bring <old-schema.xml> up-to-date with <new-schema.xml>

xml2html creates one (currently) HTML file representation of the schema.

More info available in the subdirectory doc.

Install
-------

Uncompress the files in a folder of your choosing.
The programs are best run from the command line.

Prerequesites
-------------

Requires Python 2.3

License
-------

GNU GPL http://www.gnu.org/copyleft/gpl.html
