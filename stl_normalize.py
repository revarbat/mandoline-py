#!/usr/bin/env python

import sys
import argparse

from mandoline.stl_data import StlData


def main():
    parser = argparse.ArgumentParser(prog='myprogram')
    parser.add_argument('-v', '--verbose',
                        help='Show verbose output.',
                        action="store_true")
    parser.add_argument('-c', '--check-manifold',
                        help='Perform manifold validation of model.',
                        action="store_true")
    parser.add_argument('-b', '--write-binary',
                        help='Use binary STL format for output.',
                        action="store_true")
    parser.add_argument('-o', '--outfile',
                        help='Write normalized STL to file.')
    parser.add_argument('-g', '--gui-display',
                        help='Show non-manifold edges in GUI.',
                        action="store_true")
    parser.add_argument('-f', '--show-facets',
                        help='Show facet edges in GUI.',
                        action="store_true")
    parser.add_argument('-w', '--wireframe-only',
                        help='Display wireframe only in GUI.',
                        action="store_true")
    parser.add_argument('-s', '--slice-to-file',
                        help='Slice and write g-code to file.')
    parser.add_argument('infile', help='Input STL filename.')
    args = parser.parse_args()

    stl = StlData()
    stl.read_file(args.infile)
    if args.verbose:
        print("Read {0} ({1:.1f} x {2:.1f} x {3:.1f})".format(
            args.infile,
            stl.points.maxx - stl.points.minx,
            stl.points.maxy - stl.points.miny,
            stl.points.maxz - stl.points.minz,
        ))

    manifold = True
    if args.check_manifold:
        manifold = stl.check_manifold(verbose=args.verbose)
        if manifold and (args.verbose or args.gui_display):
            print("{} is manifold.".format(args.infile))
    if args.gui_display:
        from mandoline.stl_display_gl import StlDisplayGL
        disp = StlDisplayGL(stl)
        disp.gui_show(wireframe=args.wireframe_only, show_facets=args.show_facets)
    if not manifold:
        sys.exit(-1)

    if args.outfile:
        stl.write_file(args.outfile, binary=args.write_binary)
        if args.verbose:
            print("Wrote {0} ({1})".format(
                args.outfile,
                ("binary" if args.write_binary else "ASCII"),
            ))

    if args.slice_to_file:
        from mandoline.slicer import Slicer
        slicer = Slicer(stl)
        slicer.slice_to_file(args.slice_to_file)

    sys.exit(0)


if __name__ == "__main__":
    main()


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
