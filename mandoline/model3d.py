# History:
# 2021/09/04: supporting 3MF, OFF, Wavefront OBJ and compressed 3MJ too
# 2021/09/04: renamed stl_data.py to model3d.py to reflect broader functionality to support more than just stl, first new format uncompressed 3MJ

from __future__ import print_function

import os.path
import sys
import math
import time
import struct
import json
import re

import gzip                         # for compressed .3mj
import zipfile                      # for .3mf
#import Savitar                      # parsing .3mf
import numpy                        # for .3mf
import defusedxml.ElementTree       # for .amf (and maybe .3mf as well)

from pyquaternion import Quaternion

from TextThermometer import TextThermometer
from point3d import Point3DCache
from vector import Vector
from facet3d import Facet3DCache
from line_segment3d import LineSegment3DCache

def list_methods(obj):
   return [method_name for method_name in dir(obj) if callable(getattr(obj, method_name))]
   
class ModelEndOfFileException(Exception):
    """Exception class for reaching the end of the STL file while reading."""
    pass


class ModelMalformedLineException(Exception):
    """Exception class for malformed lines in the STL file being read."""
    pass


class ModelData(object):
    """Class to read, write, and validate STL, OBJ, AMF, 3MF, 3MJ file data."""

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

    def _read_stl_ascii_line(self, f, watchwords=None):
        line = f.readline(1024).decode('utf-8')
        if line == "":
            raise ModelEndOfFileException()
        words = line.strip(' \t\n\r').lower().split()
        if not words:
            return []
        if words[0] == 'endsolid':
            raise ModelEndOfFileException()
        argstart = 0
        if watchwords:
            watchwords = watchwords.lower().split()
            argstart = len(watchwords)
            for i in range(argstart):
                if words[i] != watchwords[i]:
                    raise ModelMalformedLineException()
        return [float(val) for val in words[argstart:]]

    def _read_stl_ascii_vertex(self, f):
        point = self._read_stl_ascii_line(f, watchwords='vertex')
        return self.points.add(*point)

    def quantz(self, pt, quanta=1e-3):
        """Quantize the Z coordinate of the given point so that it won't be exactly on a layer."""
        x, y, z = pt
        z = math.floor(z / quanta + 0.5) * quanta
        return (x, y, z)

    def _add_facet(self,v1,v2,v3,quanta=1e-3):
       normal = Vector(0,0,0)             # -- create a dummy
       #print(v1,v2,v3)
       if quanta > 0.0:                   
          v1 = self.quantz(v1, quanta)
          v2 = self.quantz(v2, quanta)
          v3 = self.quantz(v3, quanta)
          if v1 == v2 or v2 == v3 or v3 == v1:
              return        # zero area facet.  Skip to next facet.
          vec1 = Vector(v1) - Vector(v2)
          vec2 = Vector(v3) - Vector(v2)
          if vec1.angle(vec2) < 1e-8:
              return        # zero area facet.  Skip to next facet.
       v1 = self.points.add(*v1)
       v2 = self.points.add(*v2)
       v3 = self.points.add(*v3)
       self.edges.add(v1,v2)
       self.edges.add(v2,v3)
       self.edges.add(v3,v1)
       self.facets.add(v1,v2,v3,normal)

    def _read_stl_ascii_facet(self, f, quanta=1e-3):
        while True:
            try:
                normal = self._read_stl_ascii_line(f, watchwords='facet normal')
                self._read_stl_ascii_line(f, watchwords='outer loop')
                vertex1 = self._read_stl_ascii_vertex(f)
                vertex2 = self._read_stl_ascii_vertex(f)
                vertex3 = self._read_stl_ascii_vertex(f)
                self._read_stl_ascii_line(f, watchwords='endloop')
                self._read_stl_ascii_line(f, watchwords='endfacet')
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
            except ModelEndOfFileException:
                return None
            except ModelMalformedLineException:
                continue  # Skip to next facet.
            self.edges.add(vertex1, vertex2)
            self.edges.add(vertex2, vertex3)
            self.edges.add(vertex3, vertex1)
            return self.facets.add(vertex1, vertex2, vertex3, normal)

    def _read_stl_binary_facet(self, f, quanta=1e-3):
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

    def _read_3MJ(self,fn):
        fh = open(fn,"rb")
        magic = fh.read(10)
        fh.close()
        if re.search(b'^\{',magic):         # -- uncompressed
           fh = open(fn,'r')
        else: 
           fh = gzip.open(fn,'rb')
        data = json.loads(fh.read())
        if data['format'] and data['format'] == "3MJ/1.0":
            ps = [v['c'] for v in data['vertices']]
            for v in data['volumes']:       # -- FUTURE: extract material/color per volume
                for f in v['triangles']:
                    f = f['v']
                    self._add_facet(ps[f[0]],ps[f[1]],ps[f[2]])
        else:
            sys.exit(f"ERROR: 3MJ file-format mal-formed: <{fn}>")

    def _read_OFF(self,fn):                 # -- .off 
        fh = open(fn,"r")
        ps = []
        l = fh.readline()
        if not re.search('^OFF',l):
            sys.exit("ERROR: mal-format OFF <{fn}>")
        (np,nf,ne) = [int(a) for a in fh.readline().split()]        # -- 2nd line has n-points, n-faces, n-edges (ignored)
        for i in range(np):
            ps.append([float(x) for x in fh.readline().split()])
        for i in range(nf):
            f = [int(x) for x in fh.readline().split()]
            f.pop(0)
            self._add_facet(ps[f[0]],ps[f[1]],ps[f[2]])
        
    def _read_OBJ(self,fn):                 # -- wavefront .obj
        fh = open(fn,"r")
        ps = []
        while 1:
            l = fh.readline()                               # -- we parse line-wise
            if not l:
                break
            if re.search('^v ',l):                          # -- v <x> <y> <z> (coordinate)
                vs = l.split()
                vs.pop(0)
                ps.append([float(x) for x in vs])
            elif re.search('^f ',l):                        # -- f <i0> <i1> <i2> (face)
                fs = l.split()
                fs.pop(0)
                fs = [re.sub('/.*','',x) for x in fs]       # -- remove all /...
                f = [int(x)-1 for x in fs]                  # -- indices start with 1 => start with 0
                self._add_facet(ps[f[0]],ps[f[1]],ps[f[2]])
            else:
                """we ignore anything else silently"""
                
    def _read_3MF(self,fn):                 # -- 3mf (what a pain to parse)
        if 1:
            z = zipfile.ZipFile(fn)
            fh = z.open('3D/3dmodel.model','r')
            xm = fh.read()
            root = defusedxml.ElementTree.fromstring(xm)    # -- going full XML
            #root = root.getroot()                 # -- doesn't work with named spaces (F*CK - it never works)
            ns = root.tag
            ns = re.sub('}(.*)$','}',ns)           # -- XML Crap: we need to retrieve name space, and reference it below
            obj = { }
            ps = [ ]
            for o in root.iter(f'{ns}object'):     # -- fetch vertices from all objects
               obj[o.attrib['id']] = o             # -- reference it for later use below
               for v in o.iter(f'{ns}vertex'):
                  ps.append([float(v.attrib[x].strip()) for x in v.attrib])
            for b in root.iter(f'{ns}build'):      # -- for each builds
               for i in b.iter(f'{ns}item'):       # -- which item
                  for v in obj[i.attrib['objectid']].iter(f'{ns}triangle'):   # -- compose the mesh (TODO: apply transformations)
                     self._add_facet(*[ps[int(v.attrib[x].strip())] for x in v.attrib])
        else:
            archive = zipfile.ZipFile(fn)
            parser = Savitar.ThreeMFParser()
            scene = parser.parse(archive.open("3D/3dmodel.model").read())
            for n in scene.getSceneNodes():
                mesh = n.getMeshData()
                vb = mesh.getVerticesAsBytes()
                fb = mesh.getFacesAsBytes()
                ps = [ ]
                for i in range(int(len(vb)/12)):            # -- we extract 3 floats (each 4 bytes) => 1 vertice/point
                    v = struct.unpack_from('3f',vb,i*3*4)
                    ps.append(v)
                for i in range(int(len(fb)/12)):            # -- we extract 3 indices (each 4 bytes) => 1 face
                    f = struct.unpack_from('3i',fb,i*3*4)
                    self._add_facet(ps[f[0]],ps[f[1]],ps[f[2]])

    def _read_AMF(self,fn):                 # -- amf (facepalm)
        ps = [ ]
        root = defusedxml.ElementTree.parse(fn)
        root = root.getroot()
        for v in root.iter('vertex'):
            ps.append([float(x.text.strip()) for x in v[0]])
        for v in root.iter('volume'):
           for c in v.iter('triangle'):
               f = [int(x.text.strip()) for x in c]
               self._add_facet(ps[f[0]],ps[f[1]],ps[f[2]])
               
    def read_file(self, filename):
        """Read the model data from the given STL, OBJ, OFF, 3MF, AMF, 3MJ file."""
        self.filename = filename
        print("Loading model \"{}\"".format(filename))
        file_size = os.path.getsize(filename)
        if re.search("\.stl",filename): 
           with open(filename, 'rb') as f:         # -- STL
               line = f.readline(80)
               if line == "":
                   return  # End of file.
               if line[0:6].lower() == b"solid " and len(line) < 80:
                   # Reading ASCII STL file.
                   thermo = TextThermometer(file_size)
                   while self._read_stl_ascii_facet(f) is not None:
                       thermo.update(f.tell())
                   thermo.clear()
               else:
                   # Reading Binary STL file.
                   chunk = f.read(4)
                   facets = struct.unpack('<I', chunk)[0]
                   thermo = TextThermometer(facets)
                   for n in range(facets):
                       thermo.update(n)
                       if self._read_stl_binary_facet(f) is None:
                           pass
                   thermo.clear()
    
        elif re.search("\.3mj",filename):           # -- 3MJ
           self._read_3MJ(filename)
        elif re.search("\.off",filename):           # -- OFF
           self._read_OFF(filename)
        elif re.search("\.obj",filename):           # -- OBJ
           self._read_OBJ(filename)
        elif re.search("\.3mf",filename):           # -- 3MF
           self._read_3MF(filename)
        elif re.search("\.amf",filename):           # -- AMF
           self._read_AMF(filename)
        else:
            sys.exit(f"ERROR: file-format not supported to import <{filename}>, only STL, OBJ, OFF, 3MF, 3MJ, AMF")

    def _write_stl_ascii_file(self, filename):
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

    def _write_stl_binary_file(self, filename):
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
        """Write the model data to an STL, OFF, OBJ, 3MF, 3MJ file."""
        if filename.search("\.stl$",filename):
           if binary:
               self._write_stl_binary_file(filename)
           else:
               self._write_stl_ascii_file(filename)
        elif filename.search("\.3mj$",filename):
            self._write_3mj(filename)
        else:
            sys.exit(f"ERR: file-format not supported to export <%s>", filename)
            
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
            print("WARN: NON-MANIFOLD DUPLICATE FACE! {0}: {1}"
                  .format(self.filename, face))
        self.hole_edges = self._check_manifold_hole_edges()
        for edge in self.hole_edges:
            is_manifold = False
            print("WARN: NON-MANIFOLD HOLE EDGE! {0}: {1}"
                  .format(self.filename, edge))
        self.dupe_edges = self._check_manifold_excess_edges()
        for edge in self.dupe_edges:
            is_manifold = False
            print("WARN: NON-MANIFOLD DUPLICATE EDGE! {0}: {1}"
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

    def scale(self, scale): 
        """Scale vertices of all facets in the STL model."""
        self.points.scale(scale)
        self.edges.scale(scale)
        self.facets.scale(scale)
           
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
            print("\nWARN: Incomplete Polygon at z=%s" % z)
            if self.debug:
               print(json.dumps(deadpaths))
        return (outpaths, deadpaths)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap

