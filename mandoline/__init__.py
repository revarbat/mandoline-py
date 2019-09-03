import sys
import argparse

from .stl_data import StlData

def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('-v', '--verbose',
                        help='Show verbose output.',
                        action="store_true")
    parser.add_argument('-o', '--outfile',
                        help='Slices STL and write GCode to file.')
    parser.add_argument('-g', '--gui-display',
                        help='Show sliced paths output in GUI.',
                        action="store_true")
    parser.add_argument('-y', '--slice-anyways',
                        help='Perform slicing even if the model fails validation.',
                        action="store_true")
    parser.add_argument('infile', help='Input STL filename.')
    args = parser.parse_args()

    stl = StlData()
    stl.read_file(args.infile)
    if args.verbose:
        print("Read {0} ({4} facets, {1:.1f} x {2:.1f} x {3:.1f})".format(
            args.infile,
            stl.points.maxx - stl.points.minx,
            stl.points.maxy - stl.points.miny,
            stl.points.maxz - stl.points.minz,
            len(stl.facets),
        ))

    manifold = True
    manifold = stl.check_manifold(verbose=args.verbose)
    if manifold and (args.verbose or args.gui_display):
        print("{} is manifold.".format(args.infile))
    if not manifold and not args.slice_anyways:
        sys.exit(-1)

    if args.outfile:
        from mandoline.slicer import Slicer
        slicer = Slicer(stl)
        slicer.slice_to_file(args.outfile, showgui=args.gui_display, threads=1)

    sys.exit(0)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
