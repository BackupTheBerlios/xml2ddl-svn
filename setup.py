#!/usr/bin/env python

from distutils.core import setup
import glob

# Note to self:
# python setup.py sdist --formats=zip
# To create the zip file

# python setup.py register
# to register with PyPI
# 

# Set this on command line
# DISTUTILS_DEBUG=true
# 
setup(
    name='xml2ddl',
    version='0.1',
    description="Xml to DDL is a set of python programs to convert an XML representation of a database into a set of SQL (or DDL - Data Definition Language) commands.",
    long_description="""
XML to DDL is a set of Python programs that converts an XML representation of a database into a set of SQL (or DDL commands - Data Definition Language) commands.
In addition it can examine the difference between two XML files and output a sequence of SQL statements (normally ALTER statements).
Finally, there's a tool to convert your schema into HTML for documentation purposes. 
XML to DDL requires no database to run (XML text in -> SQL text out) and currently supports PostgreSQL, MySQL, and Firefox databases.
""",
    author='Scott Kirkwood',
    author_email='scott_kirkwood@users.berlios.de',
    url='http://xml2ddl.berlios.de/',
    download_url='http://developer.berlios.de/project/showfiles.php?group_id=2209&release_id=3368',
    keywords=['XML', 'SQL', 'DDL', 'ALTER', 'Database', 'AgileDB', 'PostgreSQL', 'MySQL', 'Firebird', 'SQL99'],
    license='GNU GPL',
    platforms=['POSIX', 'Windows'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: SQL',
        'Topic :: Database',
        'Topic :: Documentation',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Text Processing :: Markup :: XML',
        'Topic :: Utilities',
    ],    
    py_modules=['xml2ddl', 'diffxml2ddl', 'xml2html'],
)