import math
import struct
import numbers

try:
    from itertools import zip_longest as ziplong
except ImportError:
    from itertools import izip_longest as ziplong

from .float_fmt import float_fmt


class Vector(object):
    """Class to represent an N dimentional vector."""

    def __init__(self, *args):
        self._values = []
        if len(args) == 1:
            val = args[0]
            if isinstance(val, numbers.Real):
                self._values = [val]
                return
            elif isinstance(val, numbers.Complex):
                self._values = [val.real, val.imag]
                return
        else:
            val = args
        try:
            for x in val:
                if not isinstance(x, numbers.Real):
                    raise TypeError('Expected sequence of real numbers.')
                self._values.append(x)
        except:
            pass

    def __iter__(self):
        """Iterator generator for vector values."""
        for idx in self._values:
            yield idx

    def __len__(self):
        return len(self._values)

    def __getitem__(self, idx):
        """Given a vertex number, returns a vertex coordinate vector."""
        return self._values[idx]

    def __hash__(self):
        """Returns hash value for vector coords"""
        return hash(tuple(self._values))

    def __eq__(self, other):
        """Equality comparison for points."""
        return self._values == other._values

    def __cmp__(self, other):
        """Compare points for sort ordering in an arbitrary heirarchy."""
        longzip = ziplong(self._values, other, fillvalue=0.0)
        for v1, v2 in reversed(list(longzip)):
            val = v1 - v2
            if val != 0:
                val /= abs(val)
                return val
        return 0

    def __sub__(self, v):
        return Vector(i - j for i, j in zip(self._values, v))

    def __rsub__(self, v):
        return Vector(i - j for i, j in zip(v, self._values))

    def __add__(self, v):
        return Vector(i + j for i, j in zip(self._values, v))

    def __radd__(self, v):
        return Vector(i + j for i, j in zip(v, self._values))

    def __div__(self, s):
        """Divide each element in a vector by a scalar."""
        return Vector(x / (s+0.0) for x in self._values)

    def __mul__(self, s):
        """Multiplies each element in a vector by a scalar."""
        return Vector(x * s for x in self._values)

    def __format__(self, fmt):
        vals = [float_fmt(x) for x in self._values]
        if "a" in fmt:
            return "[{0}]".format(", ".join(vals))
        if "s" in fmt:
            return " ".join(vals)
        if "b" in fmt:
            return struct.pack('<{0:d)f'.format(len(self._values)), *self._values)
        return "({0})".format(", ".join(vals))

    def __repr__(self):
        return "<Vector: {0}>".format(self)

    def __str__(self):
        """Returns a standard array syntax string of the coordinates."""
        return "{0:a}".format(self)

    def dot(self, v):
        """Dot (scalar) product of two vectors."""
        return sum(p*q for p, q in zip(self, v))

    def cross(self, v):
        """
        Cross (vector) product against another 3D Vector.
        Returned 3D Vector will be perpendicular to both original 3D Vectors.
        """
        return Vector(
            self._values[1]*v[2] - self._values[2]*v[1],
            self._values[2]*v[0] - self._values[0]*v[2],
            self._values[0]*v[1] - self._values[1]*v[0]
        )

    def length(self):
        """Returns the length of the vector."""
        return math.sqrt(sum(x*x for x in self._values))

    def normalize(self):
        """Normalizes the given vector to be unit-length."""
        return self / self.length()

    def angle(self, other):
        """Returns angle in radians between this and another vector."""
        l = self.length() * other.length()
        if l == 0:
            return 0.0
        return math.acos(self.dot(other) / l)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
