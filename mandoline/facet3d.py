import math
import numbers

try:
    from itertools import zip_longest as ziplong
except ImportError:
    from itertools import izip_longest as ziplong

from .vector import Vector
from .point3d import Point3D
from .line_segment3d import LineSegment3D


class Facet3D(object):
    """Class to represent a 3D triangular face."""

    def __init__(self, v1, v2, v3, norm):
        for x in [v1, v2, v3, norm]:
            try:
                n = len(x)
            except:
                n = 0
            if n != 3:
                raise TypeError('Expected 3D vector.')
            for y in x:
                if not isinstance(y, numbers.Real):
                    raise TypeError('Expected 3D vector.')
        verts = [
            Point3D(v1),
            Point3D(v2),
            Point3D(v3)
        ]
        # Re-order vertices in a normalized order.
        while verts[0] > verts[1] or verts[0] > verts[2]:
            verts = verts[1:] + verts[:1]
        self.vertices = verts
        self.norm = Vector(norm)
        self.count = 1
        self.fixup_normal()

    def __len__(self):
        """Length of sequence.  Three vertices and a normal."""
        return 4

    def __getitem__(self, idx):
        """Get vertices and normal by index."""
        lst = self.vertices + [self.norm]
        return lst[idx]

    def __hash__(self):
        """Returns hash value for facet"""
        return hash((self.verts, self.norm))

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __cmp__(self, other):
        """Compare faces for sorting in an arbitrary heirarchy."""
        cl1 = [sorted(v[i] for v in self.vertices) for i in range(3)]
        cl2 = [sorted(v[i] for v in other.vertices) for i in range(3)]
        for i in reversed(range(3)):
            for c1, c2 in ziplong(cl1[i], cl2[i]):
                if c1 is None:
                    return -1
                val = (c1 > c2) - (c1 < c2)
                if val != 0:
                    return val
        return 0

    def __format__(self, fmt):
        """Provides .format() support."""
        pfx = ""
        sep = " - "
        sfx = ""
        if "a" in fmt:
            pfx = "["
            sep = ", "
            sfx = "]"
        elif "s" in fmt:
            pfx = ""
            sep = " "
            sfx = ""
        ifx = sep.join(n.__format__(fmt) for n in list(self)[0:3])
        return pfx + ifx + sfx

    def _side_of_line(self, line, pt):
        return (line[1][0] - line[0][0]) * (pt[1] - line[0][1]) - (line[1][1] - line[0][1]) * (pt[0] - line[0][0])

    def _clockwise_line(self, line, pt):
        if self._side_of_line(line, pt) < 0:
            return (line[1], line[0])
        return (line[0], line[1])

    def _shoestring_algorithm(self, path):
        if path[0] == path[-1]:
            path = path[1:]
        out = 0
        for p1, p2 in zip(path, path[1:] + path[0:1]):
            out += p1[0] * p2[1]
            out -= p2[0] * p1[1]
        return out

    def _z_intercept(self,p1,p2,z):
        if p1[2] > z and p2[2] > z:
            return None
        if p1[2] < z and p2[2] < z:
            return None
        if p1[2] == z and p2[2] == z:
            return None
        u = (0.0+z-p1[2])/(p2[2]-p1[2])
        delta = [p2[a]-p1[a] for a in range(3)]
        return [delta[a]*u+p1[a] for a in range(3)]

    def translate(self, offset):
        for a in range(3):
            for v in self.vertices:
                v[a] += offset[a]

    def get_footprint(self, z=None):
        if z is None:
            path = [v[0:2] for v in self.vertices]
        else:
            opath = list(self.vertices) + [self.vertices[0]]
            path = []
            zed = zip(opath[:-1], opath[1:])
            for v1,v2 in zed:
                if v1[2] > z:
                    path.append(v1[0:2])
                if (v1[2] > z and v2[2] < z) or (v1[2] < z and v2[2] > z):
                    icept = self._z_intercept(v1,v2,z)
                    if icept:
                        path.append(icept[0:2])
        if not path:
            return None
        a = self._shoestring_algorithm(path)
        if a == 0:
            return None
        if a > 0:  # counter-clockwise
            path = list(reversed(path))
        return path

    def overhang_angle(self):
        vert = Vector([0.0, 0.0, -1.0])
        ang = vert.angle(self.norm) * 180.0 / math.pi
        return (90.0 - ang)

    def intersects_z(self, z):
        minz = min([v[2] for v in self.vertices])
        maxz = max([v[2] for v in self.vertices])
        return z >= minz and z <= maxz

    def z_range(self):
        allz = [v[2] for v in self.vertices]
        return (min(allz), max(allz))

    def slice_at_z(self, z, quanta=1e-3):
        z = math.floor(z / quanta + 0.5) * quanta + quanta/2
        minz, maxz = self.z_range()
        if z < minz:
            return None
        if z > maxz:
            return None
        if math.hypot(self.norm[0], self.norm[1]) < 1e-6:
            return None
        norm2d = self.norm[0:2]
        vl = self.vertices
        vl2 = vl[1:] + vl[0:1]
        for v1, v2 in zip(vl, vl2):
            if v1[2] == z and v2[2] == z:
                line = ((v1[0], v1[1]), (v2[0], v2[1]))
                pt = (v1[0] + norm2d[0], v1[1] + norm2d[1])
                line = self._clockwise_line(line, pt)
                return line
        if z == minz or z == maxz:
            return None
        vl3 = vl2[1:] + vl2[0:1]
        for v1, v2, v3 in zip(vl, vl2, vl3):
            if v2[2] == z:
                u = (z-v1[2])/(v3[2]-v1[2])
                px =  v1[0]+u*(v3[0]-v1[0])
                py =  v1[1]+u*(v3[1]-v1[1])
                line = ((v2[0], v2[1]), (px, py))
                pt = (v2[0] + norm2d[0], v2[1] + norm2d[1])
                line = self._clockwise_line(line, pt)
                return line
        isects = []
        for v1, v2 in zip(vl, vl2):
            if v1[2] == v2[2]:
                continue
            u = (z-v1[2])/(v2[2]-v1[2])
            if u >= 0.0 and u <= 1.0:
                isects.append((v1, v2))
        p1, p2 = isects[0]
        p3, p4 = isects[1]
        u1 = (z-p1[2])/(p2[2]-p1[2])
        u2 = (z-p3[2])/(p4[2]-p3[2])
        px =  p1[0]+u1*(p2[0]-p1[0])
        py =  p1[1]+u1*(p2[1]-p1[1])
        qx =  p3[0]+u2*(p4[0]-p3[0])
        qy =  p3[1]+u2*(p4[1]-p3[1])
        line = ((px, py), (qx, qy))
        pt = (px + norm2d[0], py + norm2d[1])
        line = self._clockwise_line(line, pt)
        return line

    def is_clockwise(self):
        """
        Returns true if the three vertices of the face are in clockwise
        order with respect to the normal vector.
        """
        v1 = Vector(self.vertices[1]-self.vertices[0])
        v2 = Vector(self.vertices[2]-self.vertices[0])
        return self.norm.dot(v1.cross(v2)) < 0

    def fixup_normal(self):
        if self.norm.length() > 0:
            # Make sure vertex ordering is counter-clockwise,
            # relative to the outward facing normal.
            if self.is_clockwise():
                self.vertices = [
                    self.vertices[0],
                    self.vertices[2],
                    self.vertices[1]
                ]
        else:
            # If no normal was specified, we should calculate it, relative
            # to the counter-clockwise vertices (as seen from outside).
            v1 = Vector(self.vertices[2] - self.vertices[0])
            v2 = Vector(self.vertices[1] - self.vertices[0])
            self.norm = v1.cross(v2)
            if self.norm.length() > 1e-6:
                self.norm = self.norm.normalize()


class Facet3DCache(object):
    """Cache class for 3D Facets."""

    def __init__(self):
        """Initialize as an empty cache."""
        self.vertex_hash = {}
        self.edge_hash = {}
        self.facet_hash = {}

    def rehash(self):
        """Rebuild the facet caches."""
        oldhash = self.facet_hash
        self.vertex_hash = {}
        self.edge_hash = {}
        self.facet_hash = {}
        for facet in oldhash.values():
            self._rehash_facet(facet)

    def _rehash_facet(self, facet):
        """Re-adds a facet to the caches."""
        pts = tuple(facet[a] for a in range(3))
        self.facet_hash[pts] = facet
        self._add_edge(pts[0], pts[1], facet)
        self._add_edge(pts[1], pts[2], facet)
        self._add_edge(pts[2], pts[0], facet)
        self._add_vertex(pts[0], facet)
        self._add_vertex(pts[1], facet)
        self._add_vertex(pts[2], facet)

    def translate(self, offset):
        """Translates vertices of all facets in the facet cache."""
        for facet in self.facet_hash.values():
            facet.translate(offset)
        self.rehash()

    def _add_vertex(self, pt, facet):
        """Remember that a given vertex touches a given facet."""
        if pt not in self.vertex_hash:
            self.vertex_hash[pt] = []
        self.vertex_hash[pt].append(facet)

    def _add_edge(self, p1, p2, facet):
        """Remember that a given edge touches a given facet."""
        if p1 > p2:
            edge = (p1, p2)
        else:
            edge = (p2, p1)
        if edge not in self.edge_hash:
            self.edge_hash[edge] = []
        self.edge_hash[edge].append(facet)

    def vertex_facets(self, pt):
        """Returns the facets that have a given facet."""
        if pt not in self.vertex_hash:
            return []
        return self.vertex_hash[pt]

    def edge_facets(self, p1, p2):
        """Returns the facets that have a given edge."""
        if p1 > p2:
            edge = (p1, p2)
        else:
            edge = (p2, p1)
        if edge not in self.edge_hash:
            return []
        return self.edge_hash[edge]

    def get(self, p1, p2, p3):
        """Given 3 vertices, return the cached Facet3D instance, if any."""
        key = (p1, p2, p3)
        if key not in self.facet_hash:
            return None
        return self.facet_hash[key]

    def add(self, p1, p2, p3, norm):
        """
        Given 3 vertices and a norm, return the (new or cached) Facet3d inst.
        """
        key = (p1, p2, p3)
        if key in self.facet_hash:
            facet = self.facet_hash[key]
            facet.count += 1
            return facet
        facet = Facet3D(p1, p2, p3, norm)
        self.facet_hash[key] = facet
        self._add_edge(p1, p2, facet)
        self._add_edge(p2, p3, facet)
        self._add_edge(p3, p1, facet)
        self._add_vertex(p1, facet)
        self._add_vertex(p2, facet)
        self._add_vertex(p3, facet)
        return facet

    def sorted(self):
        """Returns a sorted iterator."""
        vals = self.facet_hash.values()
        for pt in sorted(vals):
            yield pt

    def __iter__(self):
        """Creates an iterator for the facets in the cache."""
        for pt in self.facet_hash.values():
            yield pt

    def __len__(self):
        """Length of sequence."""
        return len(self.facet_hash)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
