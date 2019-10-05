from __future__ import print_function

import os.path
import sys
import math
import time
import struct
from pyquaternion import Quaternion

from .TextThermometer import TextThermometer
from .point3d import Point3DCache
from .vector import Vector
from .facet3d import Facet3DCache
from .line_segment3d import LineSegment3DCache


class StlEndOfFileException(Exception):
    """Exception class for reaching the end of the STL file while reading."""
    pass


class StlMalformedLineException(Exception):
    """Exception class for malformed lines in the STL file being read."""
    pass


class StlData(object):
    """Class to read, write, and validate STL file data."""

    def __init__(self):
        """Initialize with empty data set."""
        self.points = Point3DCache()
        self.edges = LineSegment3DCache()
        self.facets = Facet3DCache()
        self.filename = ""
        self.dupe_faces = []
        self.dupe_edges = []
        self.hole_edges = []
        self.layer_facets = {}

    def _read_ascii_line(self, f, watchwords=None):
        line = f.readline(1024).decode('utf-8')
        if line == "":
            raise StlEndOfFileException()
        words = line.strip(' \t\n\r').lower().split()
        if not words:
            return []
        if words[0] == 'endsolid':
            raise StlEndOfFileException()
        argstart = 0
        if watchwords:
            watchwords = watchwords.lower().split()
            argstart = len(watchwords)
            for i in range(argstart):
                if words[i] != watchwords[i]:
                    raise StlMalformedLineException()
        return [float(val) for val in words[argstart:]]

    def _read_ascii_vertex(self, f):
        point = self._read_ascii_line(f, watchwords='vertex')
        return self.points.add(*point)

    def quantz(self, pt, quanta=1e-3):
        """Quantize the Z coordinate of the given point so that it won't be exactly on a layer."""
        x, y, z = pt
        z = math.floor(z / quanta + 0.5) * quanta
        return (x, y, z)

    def _read_ascii_facet(self, f, quanta=1e-3):
        while True:
            try:
                normal = self._read_ascii_line(f, watchwords='facet normal')
                self._read_ascii_line(f, watchwords='outer loop')
                vertex1 = self._read_ascii_vertex(f)
                vertex2 = self._read_ascii_vertex(f)
                vertex3 = self._read_ascii_vertex(f)
                self._read_ascii_line(f, watchwords='endloop')
                self._read_ascii_line(f, watchwords='endfacet')
                if quanta > 0.0:
                    vertex1 = self.quantz(vertex1, quanta)
                    vertex2 = self.quantz(vertex2, quanta)
                    vertex3 = self.quantz(vertex3, quanta)
                    if vertex1 == vertex2 or vertex2 == vertex3 or vertex3 == vertex1:
                        continue  # zero area facet.  Skip to next facet.
                    vec1 = Vector(vertex1) - Vector(vertex2)
                    vec2 = Vector(vertex3) - Vector(vertex2)
                    if vec1.angle(vec2) < 1e-8:
                        continue  # zero area facet.  Skip to next facet.
            except StlEndOfFileException:
                return None
            except StlMalformedLineException:
                continue  # Skip to next facet.
            self.edges.add(vertex1, vertex2)
            self.edges.add(vertex2, vertex3)
            self.edges.add(vertex3, vertex1)
            return self.facets.add(vertex1, vertex2, vertex3, normal)

    def _read_binary_facet(self, f, quanta=1e-3):
        data = struct.unpack('<3f 3f 3f 3f H', f.read(4*4*3+2))
        normal = data[0:3]
        vertex1 = data[3:6]
        vertex2 = data[6:9]
        vertex3 = data[9:12]
        if quanta > 0.0:
            vertex1 = self.quantz(vertex1, quanta)
            vertex2 = self.quantz(vertex2, quanta)
            vertex3 = self.quantz(vertex3, quanta)
            if vertex1 == vertex2 or vertex2 == vertex3 or vertex3 == vertex1:
                return None
            vec1 = Vector(vertex1) - Vector(vertex2)
            vec2 = Vector(vertex3) - Vector(vertex2)
            if vec1.angle(vec2) < 1e-8:
                return None
        v1 = self.points.add(*vertex1)
        v2 = self.points.add(*vertex2)
        v3 = self.points.add(*vertex3)
        self.edges.add(v1, v2)
        self.edges.add(v2, v3)
        self.edges.add(v3, v1)
        return self.facets.add(v1, v2, v3, normal)

    def read_file(self, filename):
        """Read the model data from the given STL file."""
        self.filename = filename
        print("Loading model")
        file_size = os.path.getsize(filename)
        with open(filename, 'rb') as f:
            line = f.readline(80)
            if line == "":
                return  # End of file.
            if line[0:6].lower() == b"solid " and len(line) < 80:
                # Reading ASCII STL file.
                thermo = TextThermometer(file_size)
                while self._read_ascii_facet(f) is not None:
                    thermo.update(f.tell())
                thermo.clear()
            else:
                # Reading Binary STL file.
                chunk = f.read(4)
                facets = struct.unpack('<I', chunk)[0]
                thermo = TextThermometer(facets)
                for n in range(facets):
                    thermo.update(n)
                    if self._read_binary_facet(f) is None:
                        pass
                thermo.clear()

    def _write_ascii_file(self, filename):
        with open(filename, 'wb') as f:
            f.write(b"solid Model\n")
            for facet in self.facets.sorted():
                f.write(
                    "  facet normal {norm:s}\n"
                    "    outer loop\n"
                    "      vertex {v0:s}\n"
                    "      vertex {v1:s}\n"
                    "      vertex {v2:s}\n"
                    "    endloop\n"
                    "  endfacet\n"
                    .format(
                        v0=facet[0],
                        v1=facet[1],
                        v2=facet[2],
                        norm=facet.norm
                    )
                    .encode('utf-8')
                )
            f.write(b"endsolid Model\n")

    def _write_binary_file(self, filename):
        with open(filename, 'wb') as f:
            f.write('{0:-80s}'.format('Binary STL Model'))
            f.write(struct.pack('<I', len(self.facets)))
            for facet in self.facets.sorted():
                f.write(struct.pack(
                    '<3f 3f 3f 3f H',
                    facet.norm[0], facet.norm[1], facet.norm[2],
                    facet[0][0], facet[0][1], facet[0][2],
                    facet[1][0], facet[1][1], facet[1][2],
                    facet[2][0], facet[2][1], facet[2][2],
                    0
                ))

    def write_file(self, filename, binary=False):
        """Write the model data to an STL file."""
        if binary:
            self._write_binary_file(filename)
        else:
            self._write_ascii_file(filename)

    def _check_manifold_duplicate_faces(self):
        return [facet for facet in self.facets if facet.count != 1]

    def _check_manifold_hole_edges(self):
        return [edge for edge in self.edges if edge.count == 1]

    def _check_manifold_excess_edges(self):
        return [edge for edge in self.edges if edge.count > 2]

    def check_manifold(self, verbose=False):
        """Validate if the model is manifold, and therefore printable."""
        is_manifold = True
        self.dupe_faces = self._check_manifold_duplicate_faces()
        for face in self.dupe_faces:
            is_manifold = False
            print("NON-MANIFOLD DUPLICATE FACE! {0}: {1}"
                  .format(self.filename, face))
        self.hole_edges = self._check_manifold_hole_edges()
        for edge in self.hole_edges:
            is_manifold = False
            print("NON-MANIFOLD HOLE EDGE! {0}: {1}"
                  .format(self.filename, edge))
        self.dupe_edges = self._check_manifold_excess_edges()
        for edge in self.dupe_edges:
            is_manifold = False
            print("NON-MANIFOLD DUPLICATE EDGE! {0}: {1}"
                  .format(self.filename, edge))
        return is_manifold

    def get_facets(self):
        return self.facets

    def get_edges(self):
        return self.edges

    def center(self, cp):
        """Centers the model at the given centerpoint cp."""
        cx = (self.points.minx + self.points.maxx)/2.0
        cy = (self.points.miny + self.points.maxy)/2.0
        cz = (self.points.minz + self.points.maxz)/2.0
        self.translate((cp[0]-cx, cp[1]-cy, cp[2]-cz))

    def translate(self, offset):
        """Translates vertices of all facets in the STL model."""
        self.points.translate(offset)
        self.edges.translate(offset)
        self.facets.translate(offset)

    def assign_layers(self, layer_height):
        """Calculate which layers intersect which facets, for faster lookup."""
        self.layer_facets = {}
        for facet in self.facets:
            minz, maxz = facet.z_range()
            minl = int(math.floor(minz / layer_height + 0.01))
            maxl = int(math.ceil(maxz / layer_height - 0.01))
            for layer in range(minl, maxl + 1):
                if layer not in self.layer_facets:
                    self.layer_facets[layer] = []
                self.layer_facets[layer].append(facet)

    def get_layer_facets(self, layer):
        """Get all facets that intersect the given layer."""
        if layer not in self.layer_facets:
            return []
        return self.layer_facets[layer]

    def slice_at_z(self, z, layer_h):
        """Get paths outlines of where this model intersects the given Z level."""

        def ptkey(pt):
            return "{0:.3f}, {1:.3f}".format(pt[0], pt[1])

        layer = math.floor(z / layer_h + 0.5)
        paths = {}
        for facet in self.get_layer_facets(layer):
            line = facet.slice_at_z(z)
            if line is None:
                continue
            path = list(line)
            key1 = ptkey(path[0])
            key2 = ptkey(path[-1])
            if key2 in paths and paths[key2][-1] == path[0]:
                continue
            if key1 not in paths:
                paths[key1] = []
            paths[key1].append(path)

        outpaths = []
        deadpaths = []
        while paths:
            path = paths[next(iter(paths))][0]
            key1 = ptkey(path[0])
            key2 = ptkey(path[-1])
            del paths[key1][0]
            if not paths[key1]:
                del paths[key1]
            if key1 == key2:
                outpaths.append(path)
                continue
            elif key2 in paths:
                opath = paths[key2][0]
                del paths[key2][0]
                if not paths[key2]:
                    del paths[key2]
                path.extend(opath[1:])
            elif key1 in paths:
                opath = paths[key1][0]
                del paths[key1][0]
                if not paths[key1]:
                    del paths[key1]
                opath = list(reversed(opath))
                opath.extend(path[1:])
                path = opath
            else:
                deadpaths.append(path)
                continue
            key1 = ptkey(path[0])
            if key1 not in paths:
                paths[key1] = []
            paths[key1].append(path)
        if deadpaths:
            print("\nIncomplete Polygon at z=%s" % z)
        return (outpaths, deadpaths)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
