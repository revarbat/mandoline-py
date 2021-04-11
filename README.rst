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

    mandoline cube.stl

Any error messages will be printed to ``STDERR``, and the return code
will be non-zero if errors were found.

To slice a file into GCode, you need to specify the file to write to
with the -o OUTFILE arguments::

    mandoline -o cube.gcode cube.stl

If you want to force it to skip validation, then add the -n argument::

    mandoline -o cube.gcode -n cube.stl

Settings
--------
To display all slicing config options, use the --show-configs argument::

    mandoline --show-configs

To get descriptions about all slicing config options, use the --help-configs argument::

    mandoline --help-configs

You can set slicing options on the command-line with -S NAME=VALUE args::

    mandoline -S layer_height=0.3 -S skirt_lines=3

You can write changed options to the persistent slicing configs file using
the -w argument::

    mandoline -S layer_height=0.3 -S brim_width=3 -w

Query Settings
--------------
You can query the value of a slicing config option with the -q OPTNAME argument::

    mandoline -Q layer_height -Q brim_width

Built-in GUI
------------
You can view the sliced output in a GUI window if you add the -g argument.
In this window, up and down arrow keys will move through the slice layers,
and the 'q' key will quit and close the window.  The keys `1` - `4` or
`-` and `=` will zoom the image.

TODO
====
* Fixing non-manifold or general get more linient on models
    * 3DBenchy fails to slice without `-n`
    * Voron_Design_Cube_v7 slices wrong as seen with `-g`
* Allow case-insensitive settings (infill_type, support_type, adhesion_type, bed_geometry)
* Resolve "shell" vs "wall" vs "perimeter" in source variables, source comments and config
* Support more import formats, e.g. 3MF
* Enable multi-model loading/placement/rotation
    * 0.8.4: -M scale=s or -M scale=x,y,z for single model
* Verify models fit inside build volume.
* Interior solid infill perimeter paths
* Pathing type prioritization
* Optimize route paths
* Skip retraction for short motions
* Smooth top surfacing for non-flat surfaces
* G-Code custom startup/shutdown/toolchange scripts.
    * 0.8.3: start_gcode and end_gcode added
* G-Code flavors
* G-Code volumetric extrusion
* Relative E motions.
* Better Bridging

