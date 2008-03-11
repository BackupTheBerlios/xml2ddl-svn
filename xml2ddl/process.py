#!/usr/bin/env python

import sys, os, StringIO, os.path

def print_usage():
    print """Usage: process xslfile xmlfile"""

def my_exec(cmd):
    (child_in, child_out) = os.popen2(cmd)
    s = StringIO.StringIO()
    s = child_out
    lines = s.readlines()
    return "".join(lines)


if len(sys.argv) < 3:
    print_usage()
    sys.exit(-1)

xslfile = sys.argv[1]
xmlfile = sys.argv[2]

args = "xsltproc --xinclude %s %s" % (xslfile, xmlfile)
xslproc_result = my_exec(args)

dotargs = {}
dotargs['dotname'] = "%s.dot" % ( xmlfile[:xmlfile.rfind(".")])
dotargs['psname'] = "%s.ps" % ( xmlfile[:xmlfile.rfind(".")])

my_dotfile = open(dotargs['dotname'],'w')
my_dotfile.write(xslproc_result)
my_dotfile.close()

dotcmd = "dot -Tps -o %(psname)s %(dotname)s" % dotargs
#dotcmd = "dot -Tsvg -o %(psname)s %(dotname)s" % dotargs
result = my_exec(dotcmd)
#print result
