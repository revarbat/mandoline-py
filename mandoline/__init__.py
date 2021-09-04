# == __init__.py ==
#   written by Revar Desmera (2017/11)
#   extended by Rene K. Mueller (2021/04)

NAME = 'Mandoline Py'
APPNAME = 'mandoline'
VERSION = '0.8.5'                       # HINT: keep version consistent also in ../setup.py
    
import re
import sys
import os.path
from os.path import dirname, abspath, join
import argparse

# import pyximport; pyximport.install()

if(__name__!="__main__"):
    sys.path.insert(0,abspath(dirname(__file__)))         # -- needed when installed, if running locally (without build/install) all works fine

#from stl_data import StlData
from model3d import ModelData
from slicer import Slicer

def main():
    print("== {} {} == https://github.com/revarbat/mandoline-py".format(NAME,VERSION))
    
    parser = argparse.ArgumentParser(prog=APPNAME)
    parser.add_argument('-o', '--outfile',
                        help='Slices model (STL) and write GCode or SVGs to file.')
    parser.add_argument('-n', '--no-validation', action="store_true",
                        help='Skip performing model validation.')
    parser.add_argument('-g', '--gui-display', action="store_true",
                        help='Show sliced paths output in GUI.')
    parser.add_argument('-v', '--verbose', action="store_true",
                        help='Show verbose output.')
    parser.add_argument('-d', '--debug', action="store_true",
                        help='Show debug output.')

    parser.add_argument('--no-raft', dest="set_option", action="append_const",
                        const="adhesion_type=None", help='Force adhesion to not be generated.')
    parser.add_argument('--raft', dest="set_option", action="append_const",
                        const="adhesion_type=Raft", help='Force raft generation.')
    parser.add_argument('--brim', dest="set_option", action="append_const",
                        const="adhesion_type=Brim", help='Force brim generation.')

    parser.add_argument('--no-support', dest="set_option", action="append_const",
                        const="support_type=None", help='Force external support structure generation.')
    parser.add_argument('--support', dest="set_option", action="append_const",
                        const="support_type=External", help='Force external support structure generation.')
    parser.add_argument('--support-all', dest="set_option", action="append_const",
                        const="support_type=Everywhere", help='Force external support structure generation.')

    parser.add_argument('-f', '--filament', metavar="MATERIAL,...",
                        help='Configures extruder(s) for given materials, in order.  Ex: -f PLA,TPU,PVA')

    parser.add_argument('-F', '--format', metavar="FORMAT",
                        help='Set output format (gcode, svg)')
    parser.add_argument('-l', '--load', action="append", metavar="OPTNAME",
                        help='Load config file, containing <k>=<v> lines')

    parser.add_argument('-M', '--model', action="append", metavar="OPTNAME=VALUE",
                        help='Set model manipulation operation(s) (scale).')
    parser.add_argument('-S', '--set-option', action="append", metavar="OPTNAME=VALUE",
                        help='Set a slicing config option.')
    parser.add_argument('-Q', '--query-option', action="append", metavar="OPTNAME",
                        help='Display a slicing config option value.')
    parser.add_argument('-w', '--write-configs', action="store_true",
                        help='Save any changed slicing config options.')
    parser.add_argument('--help-configs', action="store_true",
                        help='Display help for all slicing options.')
    parser.add_argument('--show-configs', action="store_true",
                        help='Display values of all slicing options.')
    parser.add_argument('infile', nargs="?", help='Input model filename (STL).')
    args = parser.parse_args()

    if args.verbose:
       print("args",args)
    
    model = [ ]
    if args.infile:
        if not os.path.isfile(args.infile):
            print("ERROR: model file \"{}\" not found, abort.".format(args.infile))
            sys.exit(-1)
        if re.search(r'.(stl|3mj)$',args.infile):
            model = ModelData() 
        else:
            print("ERROR: only STL & 3MJ format supported, abort.")
            sys.exit(-1)
        model.read_file(args.infile)
        model.debug = args.debug
        if model.points.minz > 0 or model.points.minz < 0:    # -- make sure it sits perfectly on Z=0
            print("+ Relevel model {:.3f}".format(-model.points.minz))
            model.translate([0,0,-model.points.minz])
        if args.model:                                        # -- anything to apply on the model(s)
            for m in args.model:
                ma = re.match("(\w+)=(.*)",m)
                if ma[1] and ma[1] == "scale":
                    v = ma[2].split(",")
                    if len(v)!=3:
                        v = [v[0],v[0],v[0]]
                    v = list(map(lambda x: float(x),v))
                    print("+ Scaling",v)
                    model.scale(v)
                else:
                    print("WARN: ignoring {} model operation".format(m))
        if args.verbose:
            print("Read {0} ({4} facets, {1:.1f} x {2:.1f} x {3:.1f})".format(
                args.infile,
                model.points.maxx - model.points.minx,
                model.points.maxy - model.points.miny,
                model.points.maxz - model.points.minz,
                len(model.facets),
            ))
        if not args.no_validation:
            manifold = True
            manifold = model.check_manifold(verbose=args.verbose)
            if manifold and (args.verbose or args.gui_display):
                print("{} is manifold.".format(args.infile))
            if not manifold:
                print("ERROR: model is non-manifold and will likely cause bad/missing layers, abort.")
                print("HINT:  use `-n` switch to skip checking, but the same bad/missing layers remain,")
                print("       and or use `-d` to list incomplete polygons in details.")
                sys.exit(-1)
    elif not ( args.query_option or args.help_configs or args.show_configs or args.write_configs ):
        parser.print_help()
        print('''
examples:
   mandoline cube.stl
   mandoline -l myprinter.ini cube.stl
   mandoline -l myprinter.ini -S layer_height=0.3 cube.stl
   mandoline -l myprinter.ini -l petg.ini -S infill_type=Triangles cube.stl -o test.gcode
   mandoline -Q skirt

''')
        sys.exit(0)

    slicer = Slicer([model])

    slicer.args = args;
    slicer.NAME = NAME
    slicer.VERSION = VERSION
    
    slicer.load_configs()
    
    if not(args.load is None):          # -- any configs listed? load them all in sequence
       for c in args.load:
           slicer.load_configs(c)
    
    if args.set_option:
        for opt in args.set_option:
            key, val = opt.split('=', 1)
            slicer.set_config(key,val)
 
    if args.filament:
        materials = args.filament.lower().split(",")
        for extnum,material in enumerate(materials):
            if '{}_hotend_temp'.format(material) not in slicer.conf:
                print("Unknown material: {}".format(material))
                sys.exit(-1)
        newbedtemp = max(slicer.conf['{}_bed_temp'.format(material)] for material in materials)
        slicer.set_config("bed_temp", str(newbedtemp))
        for extnum,material in enumerate(materials):
            print("Configuring extruder{} for {}".format(extnum, material))
            slicer.set_config("nozzle_{}_temp".format(extnum), str(slicer.conf['{}_hotend_temp'.format(material)]))
            slicer.set_config("nozzle_{}_max_speed".format(extnum), str(slicer.conf['{}_max_speed'.format(material)]))
 
    if args.write_configs:
        slicer.save_configs()
 
    if args.query_option:
        for opt in args.query_option:
            slicer.display_configs_help(key=opt, vals_only=True)
 
    if args.help_configs:
        slicer.display_configs_help()
 
    if args.show_configs:
        slicer.display_configs_help(vals_only=True)

    if args.infile:
        if args.outfile:
            outfile = args.outfile
        else:
            outfile = os.path.splitext(args.infile)[0] + (".svg" if args.format=='svg' else '.gcode')
        slicer.slice_to_file(outfile, showgui=args.gui_display)

    sys.exit(0)

if(__name__=="__main__"):
    main()

# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
