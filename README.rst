############
Mandoline Py
############

This is a 3D printing STL-to-GCode slicer, written in Python, based
on the Clipper geometry library.  It will let you take STL files
and generate a GCode path file that you can send to your RepRap 3D
printer to print the object.


Installation
============

Install using PyPi::

    pip install pymuv

Installing from sources::

    python3 setup.py build install


Usage
=====
The simplest way to use ``mandoline-py`` on the command-line is to
give it the name of an STL file to slice.  By default, it will write
the gcode output to a file with the same name as the STL file, but
with the suffix changed to ``.gcode``.  Any error messages will be
printed to ``STDERR``, and the return code will be non-zero if
errors were found::

    mandoline-py testcube.stl

You can use ``-o FILENAME`` to specify what file the GCode output
should be written to::

    mandoline-py -o cube20x20.gcode testcube.stl



