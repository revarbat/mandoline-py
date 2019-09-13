import sys
import argparse

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
    parser.add_argument('-S', '--set-option', action="append",
                        metavar="OPTNAME=VALUE",
                        help='Set a slicing config option.')
    parser.add_argument('-q', '--query-option', action="append",
                        metavar="OPTNAME",
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
    if args.write_configs:
        slicer.save_configs()
    if args.query_option:
        for opt in args.query_option:
            slicer.display_configs_help(key=opt, vals_only=True)
    if args.help_configs:
        slicer.display_configs_help()
    if args.show_configs:
        slicer.display_configs_help(vals_only=True)

    if args.outfile:
        slicer.slice_to_file(args.outfile, showgui=args.gui_display)

    sys.exit(0)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
