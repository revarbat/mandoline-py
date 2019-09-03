############
Mandoline Py
############

This is a 3D printing STL-to-GCode slicer, written in Python, based
on the Clipper geometry library.  It will let you take STL files
and generate a GCode path file that you can send to your RepRap 3D
printer to print the object.


Installation
============

Install using PyPi (NOT IMPLEMENTED YET)::

    unzip mandoline-py.zip
    cd mandoline-py
    pip3 install .

Installing from sources::

    python3 setup.py build install


Usage
=====
To just validate a model, checking it for manifold errors, just run
``mandoline`` with the name of the file::

    mandoline testcube.stl

Any error messages will be printed to ``STDERR``, and the return code
will be non-zero if errors were found.

To slice a file into GCode, you need to specify the file to write to
with the -o OUTFILE arguments::

    mandoline -o testcube.gcode testcube.stl

If you want to force it to try to slice the STL file, even if it fails
validation, then add the -y argument::

    mandoline -o testcube.gcode -y testcube.stl

You can view the sliced output in a GUI window if you add the -g argument.
In this window, up and down arrow keys will move through the slice layers,
and the 'q' key will quit and close the window.  The keys `1` - `4` or
`-` and `=` will zoom the image.

