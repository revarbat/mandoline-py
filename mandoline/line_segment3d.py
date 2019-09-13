
class LineSegment3D(object):
    """A class to represent a 3D line segment."""

    def __init__(self, p1, p2):
        """Initialize with twwo endpoints."""
        if p1 > p2:
            p1, p2 = (p2, p1)
        self.p1 = p1
        self.p2 = p2
        self.count = 1

    def __len__(self):
        """Line segment always has two endpoints."""
        return 2

    def __iter__(self):
        """Iterator generator for endpoints."""
        yield self.p1
        yield self.p2

    def __getitem__(self, idx):
        """Given a vertex number, returns a vertex coordinate vector."""
        if idx == 0:
            return self.p1
        if idx == 1:
            return self.p2
        raise LookupError()

    def __hash__(self):
        """Returns hash value for endpoints"""
        return hash((self.p1, self.p2))

    def __lt__(self, p):
        return self < p

    def __cmp__(self, p):
        """Compare points for sort ordering in an arbitrary heirarchy."""
        val = self[0].__cmp__(p[0])
        if val != 0:
            return val
        return self[1].__cmp__(p[1])

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
        p1 = self.p1.__format__(fmt)
        p2 = self.p2.__format__(fmt)
        return pfx + p1 + sep + p2 + sfx

    def __repr__(self):
        """Standard string representation."""
        return "<LineSegment3D: {0}>".format(self)

    def __str__(self):
        """Returns a human readable coordinate string."""
        return "{0:a}".format(self)

    def translate(self,offset):
        """Translate the endpoint's vertices"""
        self.p1 = (self.p1[a] + offset[a] for a in range(3))
        self.p2 = (self.p2[a] + offset[a] for a in range(3))

    def length(self):
        """Returns the length of the line."""
        return self.p1.distFromPoint(self.p2)


class LineSegment3DCache(object):
    """Cache class for 3D Line Segments."""

    def __init__(self):
        """Initialize as an empty cache."""
        self.endhash = {}
        self.seghash = {}

    def _add_endpoint(self, p, seg):
        """Remember that this segment has a given endpoint"""
        if p not in self.endhash:
            self.endhash[p] = []
        self.endhash[p].append(seg)

    def rehash(self):
        """Reset the hashes for changed edge vertices"""
        oldseghash = self.seghash
        self.seghash = {
            (v[0], v[1]): v
            for v in oldseghash.values()
        }
        oldendhash = self.endhash
        self.endhash = {
            k: v
            for v in oldendhash.values()
            for k in v
        }

    def translate(self,offset):
        """Translate vertices of all edges."""
        for v in self.seghash.values():
            v.translate(offset)
        self.rehash()

    def endpoint_segments(self, p):
        """get list of edges that end at point p"""
        if p not in self.endhash:
            return []
        return self.endhash[p]

    def get(self, p1, p2):
        """Given 2 endpoints, return the cached LineSegment3D inst, if any."""
        key = (p1, p2) if p1 < p2 else (p2, p1)
        if key not in self.seghash:
            return None
        return self.seghash[key]

    def add(self, p1, p2):
        """Given 2 endpoints, return the (new or cached) LineSegment3D inst."""
        key = (p1, p2) if p1 < p2 else (p2, p1)
        if key in self.seghash:
            seg = self.seghash[key]
            seg.count += 1
            return seg
        seg = LineSegment3D(p1, p2)
        self.seghash[key] = seg
        self._add_endpoint(p1, seg)
        self._add_endpoint(p2, seg)
        return seg

    def __iter__(self):
        """Creates an iterator for the line segments in the cache."""
        for pt in self.seghash.values():
            yield pt

    def __len__(self):
        """Length of sequence."""
        return len(self.seghash)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
