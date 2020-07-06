import sys
import os.path
import argparse

# import pyximport; pyximport.install()

from .stl_data import StlData
from mandoline.slicer import Slicer


def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('-o', '--outfile',
                        help='Slices STL and write GCode to file.')
    parser.add_argument('-n', '--no-validation', action="store_true",
                        help='Skip performing model validation.')
    parser.add_argument('-g', '--gui-display', action="store_true",
                        help='Show sliced paths output in GUI.')
    parser.add_argument('-v', '--verbose', action="store_true",
                        help='Show verbose output.')

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
    parser.add_argument('infile', nargs="?", help='Input STL filename.')
    args = parser.parse_args()

    stl = StlData()
    if args.infile:
        stl.read_file(args.infile)
        if args.verbose:
            print("Read {0} ({4} facets, {1:.1f} x {2:.1f} x {3:.1f})".format(
                args.infile,
                stl.points.maxx - stl.points.minx,
                stl.points.maxy - stl.points.miny,
                stl.points.maxz - stl.points.minz,
                len(stl.facets),
            ))

        if not args.no_validation:
            manifold = True
            manifold = stl.check_manifold(verbose=args.verbose)
            if manifold and (args.verbose or args.gui_display):
                print("{} is manifold.".format(args.infile))
            if not manifold:
                sys.exit(-1)

    slicer = Slicer([stl])

    slicer.load_configs()
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
            outfile = os.path.splitext(args.infile)[0] + ".gcode"
        slicer.slice_to_file(outfile, showgui=args.gui_display)

    sys.exit(0)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
