python /usr/share/python-docutils/rst2latex.py -dg /home/scott/scott/xml2ddl/doc/index.rst index.tex
python /usr/share/python-docutils/rst2html.py -dg /home/scott/scott/xml2ddl/doc/index.rst index.html
python outputSamples.py
pdflatex index.tex
