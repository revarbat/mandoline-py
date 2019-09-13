import math
import struct
import numbers

try:
    from itertools import zip_longest as ziplong
except ImportError:
    from itertools import izip_longest as ziplong

from .float_fmt import float_fmt


class Point3D(object):
    """Class to represent a 3D Point."""

    def __init__(self, *args):
        self._values = [0.0, 0.0, 0.0]
        if len(args) == 1:
            val = args[0]
            if isinstance(val, numbers.Real):
                self._values = [val, 0.0, 0.0]
                return
            elif isinstance(val, numbers.Complex):
                self._values = [val.real, val.imag, 0.0]
                return
        else:
            val = args
        try:
            for i, x in enumerate(val):
                if not isinstance(x, numbers.Real):
                    raise TypeError('Expected sequence of real numbers.')
                self._values[i] = x
        except:
            pass

    def __iter__(self):
        """Iterator generator for point values."""
        for idx in range(3):
            yield self[idx]

    def __len__(self):
        return 3

    def __setitem__(self, idx, val):
        self._values[idx] = val

    def __getitem__(self, idx):
        """Given a vertex number, returns a vertex coordinate vector."""
        if type(idx) is not slice and idx >= len(self._values):
            return 0.0
        return self._values[idx]

    def __hash__(self):
        """Returns hash value for point coords"""
        return hash(tuple(self._values))

    def __cmp__(self, p):
        """Compare points for sort ordering in an arbitrary heirarchy."""
        longzip = ziplong(self._values, p, fillvalue=0.0)
        for v1, v2 in reversed(list(longzip)):
            val = v1 - v2
            if val != 0:
                val /= abs(val)
                return val
        return 0

    def __eq__(self, other):
        """Equality comparison for points."""
        return self._values == other._values

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __sub__(self, v):
        return Point3D(self[i] - v[i] for i in range(3))

    def __rsub__(self, v):
        return Point3D(v[i] - self[i] for i in range(3))

    def __add__(self, v):
        return Vector(i + j for i, j in zip(self._values, v))

    def __radd__(self, v):
        return Vector(i + j for i, j in zip(v, self._values))

    def __div__(self, s):
        """Divide each element in a vector by a scalar."""
        return Vector(x / s for x in self._values)

    def __format__(self, fmt):
        vals = [float_fmt(x) for x in self._values]
        if "a" in fmt:
            return "[{0}]".format(", ".join(vals))
        if "s" in fmt:
            return " ".join(vals)
        if "b" in fmt:
            return struct.pack('<3f', *self._values)
        return "({0})".format(", ".join(vals))

    def __repr__(self):
        return "<Point3D: {0}>".format(self)

    def __str__(self):
        """Returns a standard array syntax string of the coordinates."""
        return "{0:a}".format(self)

    def translate(self, offset):
        """Translates the coordinates of this point."""
        self._values = [i + j for i, j in zip(offset, self._values)]

    def distFromPoint(self, v):
        """Returns the distance from another point."""
        return math.sqrt(sum(math.pow(x1-x2, 2.0) for x1, x2 in zip(v, self)))

    def distFromLine(self, pt, line):
        """
        Returns the distance of a 3d point from a line defined by a sequence
        of two 3d points.
        """
        w = Vector(pt - line[0])
        v = Vector(line[1]-line[0])
        return v.normalize().cross(w).length()


class Point3DCache(object):
    """Cache class for 3D Points."""

    def __init__(self):
        """Initialize as an empty cache."""
        self.point_hash = {}
        self.minx = 9e99
        self.miny = 9e99
        self.minz = 9e99
        self.maxx = -9e99
        self.maxy = -9e99
        self.maxz = -9e99

    def __len__(self):
        """Length of sequence."""
        return len(self.point_hash)

    def _update_volume(self, p):
        """Update the volume cube that contains all the points."""
        if p[0] < self.minx:
            self.minx = p[0]
        if p[0] > self.maxx:
            self.maxx = p[0]
        if p[1] < self.miny:
            self.miny = p[1]
        if p[1] > self.maxy:
            self.maxy = p[1]
        if p[2] < self.minz:
            self.minz = p[2]
        if p[2] > self.maxz:
            self.maxz = p[2]

    def rehash(self):
        """Rebuild the point cache."""
        oldpthash = self.point_hash
        self.point_hash = {
            tuple(round(n, 4) for n in pt): pt
            for pt in oldpthash.values()
        }

    def translate(self, offset):
        """Translates all cached points."""
        self.minx += offset[0]
        self.maxx += offset[0]
        self.miny += offset[1]
        self.maxy += offset[1]
        self.minz += offset[2]
        self.maxz += offset[2]
        for pt in self.point_hash.values():
            pt.translate(offset)
        self.rehash()

    def get_volume(self):
        """Returns the 3D volume that contains all the points in the cache."""
        return (
            self.minx, self.miny, self.minz,
            self.maxx, self.maxy, self.maxz
        )

    def add(self, x, y, z):
        """Given XYZ coords, returns the (new or cached) Point3D instance."""
        key = tuple(round(n, 4) for n in [x, y, z])
        if key in self.point_hash:
            return self.point_hash[key]
        pt = Point3D(key)
        self.point_hash[key] = pt
        self._update_volume(pt)
        return pt

    def __iter__(self):
        """Creates an iterator for the points in the cache."""
        for pt in self.point_hash.values():
            yield pt


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
