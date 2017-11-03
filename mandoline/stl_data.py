import struct
from pyquaternion import Quaternion

from .point3d import Point3DCache
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

    def _read_ascii_facet(self, f):
        while True:
            try:
                normal = self._read_ascii_line(f, watchwords='facet normal')
                self._read_ascii_line(f, watchwords='outer loop')
                vertex1 = self._read_ascii_vertex(f)
                vertex2 = self._read_ascii_vertex(f)
                vertex3 = self._read_ascii_vertex(f)
                self._read_ascii_line(f, watchwords='endloop')
                self._read_ascii_line(f, watchwords='endfacet')
                if vertex1 == vertex2:
                    continue  # zero area facet.  Skip to next facet.
                if vertex2 == vertex3:
                    continue  # zero area facet.  Skip to next facet.
                if vertex3 == vertex1:
                    continue  # zero area facet.  Skip to next facet.
            except StlEndOfFileException:
                return None
            except StlMalformedLineException:
                continue  # Skip to next facet.
            self.edges.add(vertex1, vertex2)
            self.edges.add(vertex2, vertex3)
            self.edges.add(vertex3, vertex1)
            return self.facets.add(vertex1, vertex2, vertex3, normal)

    def _read_binary_facet(self, f):
        data = struct.unpack('<3f 3f 3f 3f H', f.read(4*4*3+2))
        normal = data[0:3]
        vertex1 = data[3:6]
        vertex2 = data[6:9]
        vertex3 = data[9:12]
        v1 = self.points.add(*vertex1)
        v2 = self.points.add(*vertex2)
        v3 = self.points.add(*vertex3)
        self.edges.add(v1, v2)
        self.edges.add(v2, v3)
        self.edges.add(v3, v1)
        return self.facets.add(v1, v2, v3, normal)

    def read_file(self, filename):
        self.filename = filename
        with open(filename, 'rb') as f:
            line = f.readline(80)
            if line == "":
                return  # End of file.
            if line[0:6].lower() == b"solid " and len(line) < 80:
                # Reading ASCII STL file.
                while self._read_ascii_facet(f) is not None:
                    pass
            else:
                # Reading Binary STL file.
                chunk = f.read(4)
                facets = struct.unpack('<I', chunk)[0]
                for n in range(facets):
                    if self._read_binary_facet(f) is None:
                        break

    def _write_ascii_file(self, filename):
        with open(filename, 'wb') as f:
            f.write("solid Model\n")
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
                )
            f.write("endsolid Model\n")

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

    def get_overhang_footprint_triangles(self, ang=45, z=None):
        out = []
        for facet in self.facets:
            if facet.overhang_angle() < ang:
                continue
            if z is not None and not facet.intersects_z(z):
                continue
            tri = facet.get_footprint()
            if tri is None:
                continue
            out.append(tri)
        return out

    def slice_at_z(self, z):

        def ptkey(pt):
            return "{0:.8g}, {1:.8g}".format(pt[0], pt[1])

        paths = {}
        pathends = {}
        for facet in self.facets:
            line = facet.slice_at_z(z)
            if line is None:
                continue
            path = list(line)
            while True:
                first_key = ptkey(path[0])
                end_key = ptkey(path[-1])
                if first_key in pathends:
                    opath = pathends[first_key]
                    del pathends[first_key]
                    del paths[ptkey(opath[0])]
                    opath.extend(path[1:])
                    path = opath
                elif end_key in paths:
                    opath = paths[end_key]
                    del paths[end_key]
                    del pathends[ptkey(opath[-1])]
                    path.extend(opath[1:])
                else:
                    break
            paths[ptkey(path[0])] = path
            pathends[ptkey(path[-1])] = path
        return list(paths.values())


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
