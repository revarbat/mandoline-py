from __future__ import print_function

import sys
import math
import multiprocessing

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from tkinter import (Tk, Canvas, BOTH, ROUND, NW, ALL, mainloop)

import pyclipper


# Support:
#   For External support type:
#     Start with total footprint
#     For each layer up from bottom, diff out layer outline (outset by support_outset) to calc layer support clip region
#     Make array of parallel lines
#     clip lines by layer clip region
#     add clipped lines and clip region outline to layer output.
# Raft:
#   calculate outset footprint for raft outline.
#   make array of parallel thick lines, and clip by extrusion inset raft outline
#   make perpendicular array of parallel thin lines, and clip by extrusion inset raft outline
#   Add raft outline and clipped thick lines to first layer.
#   Add raft outline and clipped thin lines to second layer.
#   Raise remainder of print 2 layers.


slicer_configs = OrderedDict([
    ('Quality', (
        ('layer_height',      float,  0.2, (0.01, 0.5), "Slice layer height in mm."),
        ('shell_count',       int,      2, (1, 10),     "Number of outer shells to print."),
        ('top_layers',        int,      3, (0, 10),     "Number of layers to print on the top side of the object."),
        ('bottom_layers',     int,      3, (0, 10),     "Number of layers to print on the bottom side of the object."),
        ('infill_type',       list, 'Grid', ['Lines', 'Triangles', 'Grid', 'Hexagons'], "Pattern that the infill will be printed in."),
        ('infill_density',    float,  30., (0., 100.),  "Infill density in percent."),
        ('infill_overlap',    float, 0.15, (0.0, 1.0),  "Amount, in mm that infill will overlap with perimeter extrusions."),
        ('feed_rate',         int,     60, (1, 300),    "Speed while extruding. (mm/s)"),
        ('travel_rate_xy',    int,    100, (1, 300),    "Travel motion speed (mm/s)"),
        ('travel_rate_z',     float,   5., (0.1, 30.),  "Z-axis  motion speed (mm/s)"),
    )),
    ('Support', (
        ('adhesion_type',     list, 'None', ('None', 'Brim', 'Raft'),           "What kind of base adhesion structure to add."),
        ('support_type',      list, 'External', ('None', 'External', 'Everywhere'), "What kind of support structure to add."),
        ('support_outset',    float,   0.5, (0., 2.),   "How far support structures should be printed away from model, horizontally."),
        ('support_density',   float,  33.0, (0., 100.), "Density of support structure internals."),
        ('overhang_angle',    int,      45, (0, 90),    "Angle from vertical that support structures should be printed for."),
    )),
    ('Extras', (
        ('skirt_loops',       int,      0, (0, 100),    "Print at least this many skirt loops to prime the extruder."),
        ('skirt_min_len',     float,  0.0, (0., 1000.), "Add extra loops on the first layer until we've extruded at least this amount."),
        ('skirt_outset',      float,  0.0, (0., 20.),   "How far the skirt should be printed away from model."),
        ('skirt_layers',      int,      1, (1, 1000),   "Number of layers to print print the skirt on."),
        ('brim_width',        float,  3.0, (0., 20.),   "Width of brim to print on first layer to help with part adhesion."),
        ('raft_layers',       int,      1, (1, 5),      "Number of layers to use in making the raft."),
        ('raft_outset',       float,  3.0, (0., 50.),   "How much bigger raft should be than the model footprint."),
    )),
    ('Retraction', (
        ('retract_enable',    bool,   True, None,       "Enable filament retraction."),
        ('retract_speed',     float,  30.0, (0., 200.), "Speed to retract filament at. (mm/s)"),
        ('retract_dist',      float,   3.0, (0., 20.),  "Distance to retract filament between extrusion moves. (mm)"),
        ('retract_extruder',  float,   3.0, (0., 50.),  "Distance to retract filament on extruder change. (mm)"),
        ('retract_lift',      float,   0.0, (0., 10.),  "Distance to lift the extruder head during retracted moves. (mm)"),
    )),
    ('Machine', (
        ('extruder_count',    int,      1, (1, 4),     "The number of extruders this machine has."),
        ('default_nozzle',    int,      0, (0, 7),     "The default extruder used for printing."),
        ('infill_nozzle',     int,     -1, (-1, 7),    "The extruder used for infill material.  -1 means use default nozzle."),
        ('support_nozzle',    int,     -1, (-1, 7),    "The extruder used for support material.  -1 means use default nozzle."),

        ('nozzle_0_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 0. (C)"),
        ('nozzle_0_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 0. (mm)"),
        ('nozzle_0_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 0. (mm)"),
        ('nozzle_0_xoff',     float,  0.0, (0., 100.), "The X positional offset for extruder 0. (mm)"),
        ('nozzle_0_yoff',     float,  0.0, (0., 100.), "The Y positional offset for extruder 0. (mm)"),
        ('nozzle_0_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 0. (mm^3/s)"),

        ('nozzle_1_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 1. (C)"),
        ('nozzle_1_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 1. (mm)"),
        ('nozzle_1_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 1. (mm)"),
        ('nozzle_1_xoff',     float, 25.0, (0., 100.), "The X positional offset for extruder 1. (mm)"),
        ('nozzle_1_yoff',     float,  0.0, (0., 100.), "The Y positional offset for extruder 1. (mm)"),
        ('nozzle_1_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 1. (mm^3/s)"),

        ('nozzle_2_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 2. (C)"),
        ('nozzle_2_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 2. (mm)"),
        ('nozzle_2_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 2. (mm)"),
        ('nozzle_2_xoff',     float, -25., (0., 100.), "The X positional offset for extruder 2. (mm)"),
        ('nozzle_2_yoff',     float,  0.0, (0., 100.), "The Y positional offset for extruder 2. (mm)"),
        ('nozzle_2_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 2. (mm^3/s)"),

        ('nozzle_3_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 3. (C)"),
        ('nozzle_3_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 3. (mm)"),
        ('nozzle_3_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 3. (mm)"),
        ('nozzle_3_xoff',     float,  0.0, (0., 100.), "The X positional offset for extruder 3. (mm)"),
        ('nozzle_3_yoff',     float, 25.0, (0., 100.), "The Y positional offset for extruder 3. (mm)"),
        ('nozzle_3_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 3. (mm^3/s)"),
    )),
])




class Slicer(object):
    def __init__(self, model, **kwargs):
        self.SCALING_FACTOR = 1000
        self.model = model
        self.conf = {}
        for key, opts in slicer_configs.items():
            for name, typ, dflt, rng, desc in opts:
                self.conf[name] = dflt
        self.mag = 4
        self.layer = 0
        self.config(**kwargs)

    def config(self, **kwargs):
        for key, val in kwargs.items():
            if key in self.conf:
                self.conf[key] = val

    def slice_to_file(self, filename, threads=-1):
        print("Slicing start")
        layer_h = self.conf['layer_height']
        dflt_nozl = self.conf['default_nozzle']
        infl_nozl = self.conf['infill_nozzle']
        supp_nozl = self.conf['support_nozzle']
        if infl_nozl == -1:
            infl_nozl = dflt_nozl
        if supp_nozl == -1:
            supp_nozl = dflt_nozl
        dflt_nozl_d = self.conf['nozzle_{0}_diam'.format(dflt_nozl)]
        infl_nozl_d = self.conf['nozzle_{0}_diam'.format(infl_nozl)]
        supp_nozl_d = self.conf['nozzle_{0}_diam'.format(supp_nozl)]
        self.layer_height = layer_h
        self.extrusion_ratio = 1.25
        self.extrusion_width = dflt_nozl_d * self.extrusion_ratio
        self.infill_width = infl_nozl_d * self.extrusion_ratio
        self.support_width = supp_nozl_d * self.extrusion_ratio
        height = self.model.points.maxz - self.model.points.minz
        layer_cnt = math.floor(height / layer_h)
        self.model.assign_layers(layer_h)
        self.layer_zs = [
            self.model.points.minz + layer_h * (layer + 1)
            for layer in range(layer_cnt)
        ]
        if threads <= 0:
            threads = 4 * multiprocessing.cpu_count()
        # print('<tkcad formatversion="1.1" units="inches" showfractions="YES" material="Aluminum">', file=sys.stderr)
        with ThreadPoolExecutor(max_workers=threads) as ex:
            print("Cut")
            self.layer_paths = list(ex.map(self._cut_task, self.layer_zs))

            print("Overhang mask")
            self.overhang_masks = list(ex.map(self._overhang_mask_task, range(layer_cnt)))

            self.future_brim = ex.submit(self._brim_task)
            self.future_skirt = ex.submit(self._skirt_task)
            self.future_raft = ex.submit(self._raft_task)
            self.future_overhang_drop = ex.submit(self._overhang_drop_task)

            print("Perimeters")
            self.perimeter_paths = list(ex.map(self._perimeter_task, range(layer_cnt)))

            print("Top/Bottom masks")
            self.top_masks = []
            self.bot_masks = []
            for topmask, botmask in ex.map(self._top_bottom_mask_task, range(layer_cnt)):
                self.top_masks.append(topmask)
                self.bot_masks.append(botmask)

            print("Solid masks")
            self.solid_masks = list(ex.map(self._solid_mask_task, range(layer_cnt)))

            print("Brim")
            self.brim_paths = self.future_brim.result()

            print("Skirt")
            self.skirt_paths, self.priming_paths = self.future_skirt.result()

            print("Raft")
            self.raft_outline, self.raft_infill = self.future_raft.result()

            del self.top_masks
            del self.bot_masks

            print("Overhang drops")
            self.overhang_drops = self.future_overhang_drop.result()

            print("Solid infill")
            self.solid_infill = list(ex.map(self._solid_infill_task, range(layer_cnt)))

            print("Sparse infill")
            self.sparse_infill = list(ex.map(self._sparse_infill_task, range(layer_cnt)))

            print("Support")
            self.support_outline = []
            self.support_infill = []
            for outline, infill in ex.map(self._support_task, range(layer_cnt)):
                self.support_outline.append(outline)
                self.support_infill.append(infill)

            del self.overhang_drops

        raft_layers = len(self.raft_infill)
        for i in range(raft_layers):
            self.layer_zs.append(self.layer_zs[-1]+self.conf[layer_height])

        print("Gcode")
        with open(filename, "w") as f:
            f.write("( raft_outline )\n")
            outline = self._close_paths(self.raft_outline)
            for line in self._paths_gcode(outline, self.support_width, supp_nozl, self.layer_zs[0]):
                f.write(line)
            f.write("( raft_infill )\n")
            for layer, layer_paths in enumerate(self.raft_infill):
                for line in self._paths_gcode(layer_paths, self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            layer = raft_layers
            f.write("( priming )\n")
            for paths in self.priming_paths:
                paths = self._close_paths(paths)
                for line in self._paths_gcode(paths, self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)
            f.write("( brim )\n")
            for paths in self.brim_paths:
                for line in self._paths_gcode(paths+paths[0], self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            for slicenum in range(len(self.perimeter_paths)):
                layer = raft_layers + slicenum
                outline = self._close_paths(self.support_outline[slicenum])
                f.write("( support outline )\n")
                for line in self._paths_gcode(outline, self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)
                f.write("( support infill )\n")
                for line in self._paths_gcode(self.support_infill[slicenum], self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

                f.write("( perimeters )\n")
                for paths in reversed(self.perimeter_paths[slicenum]):
                    paths = self._close_paths(paths)
                    for line in self._paths_gcode(paths, self.extrusion_width, dflt_nozl, self.layer_zs[layer]):
                        f.write(line)
                f.write("( solid fill )\n")
                for line in self._paths_gcode(self.solid_infill[slicenum], self.extrusion_width, dflt_nozl, self.layer_zs[layer]):
                    f.write(line)

                f.write("( sparse infill )\n")
                for line in self._paths_gcode(self.sparse_infill[slicenum], self.infill_width, infl_nozl, self.layer_zs[layer]):
                    f.write(line)

        # print('</tkcad>', file=sys.stderr)
        self._display_paths()
        # TODO: Route paths
        # TODO: No retraction and hop for short paths
        # TODO: No Z move when Z hasn't changed.
        # TODO: Reset E axis less frequently.
        # TODO: Heated Bed temperature setup and warmup wait
        # TODO: Extruder temperature setup and warmup wait
        # TODO: G-Code state initialization and shutdown
        # TODO: Relative E motions.
        # TODO: Interior solid infill perimeter paths
        # TODO: Shorten support structures Z height
        # TODO: Bridging

    def _close_path(self, path):
        if not path:
            return path
        if path[0] == path[-1]:
            return path
        return path + path[0:1]

    def _close_paths(self, paths):
        return [self._close_path(path) for path in paths]


    ############################################################

    def _cut_task(self, z):
        layer_h = self.conf['layer_height']
        paths = self.model.slice_at_z(z - layer_h/2, layer_h)
        return self._union(paths, [])

    def _perimeter_task(self, layer):
        paths = self.layer_paths[layer]
        ewidth = self.extrusion_width
        out = []
        for i in range(self.conf['shell_count']):
            shell = self._offset(paths, -(i+0.5) * ewidth)
            shell = [self._close_path(path) for path in shell]
            out.append(shell)
        return out

    def _top_bottom_mask_task(self, layer):
        paths = self.perimeter_paths[layer][-1]
        top_mask = paths
        bot_mask = paths
        try:
            top_mask = self._diff(top_mask, self.perimeter_paths[layer+1][-1])
        except IndexError:
            pass
        if layer > 0:
            bot_mask = self._diff(bot_mask, self.perimeter_paths[layer-1][-1])
        return (top_mask, bot_mask)

    def _solid_mask_task(self, layer):
        outmask = []
        for i in range(self.conf['top_layers']):
            try:
                outmask = self._union(outmask, self.top_masks[layer+i])
            except IndexError:
                pass
        for i in range(self.conf['bottom_layers']):
            if layer - i >= 0:
                outmask = self._union(outmask, self.bot_masks[layer-i])
        layer_mask = self.perimeter_paths[layer][-1]
        solid_mask = self._clip(outmask, layer_mask)
        return solid_mask

    def _solid_infill_task(self, layer):
        base_ang = 45 if layer % 2 == 0 else -45
        solid_mask = self.solid_masks[layer]
        solid_mask = self._offset(solid_mask, self.conf['infill_overlap']-self.extrusion_width)
        lines = self._make_infill_lines(base_ang, 1.0)
        clipped_lines = []
        for line in lines:
            clipped_lines.extend(self._clip([line], solid_mask, subj_closed=False))
        return clipped_lines

    def _sparse_infill_task(self, layer):
        infill_type = self.conf['infill_type']
        density = self.conf['infill_density'] / 100.0
        ewidth = self.infill_width
        if density <= 0.0:
            return []
        if density >= 0.99:
            infill_type = "Lines"
        mask = self.perimeter_paths[layer][-1]
        mask = self._offset(mask, self.conf['infill_overlap']-ewidth)
        mask = self._diff(mask, self.solid_masks[layer])
        # bounds = self._paths_bounds(mask)
        if infill_type == "Lines":
            base_ang = 90 * (layer % 2) + 45
            lines = self._make_infill_lines(base_ang, density, ewidth=ewidth)
        elif infill_type == "Triangles":
            base_ang = 60 * (layer % 3)
            lines = self._make_infill_triangles(base_ang, density, ewidth=ewidth)
        elif infill_type == "Grid":
            base_ang = 90 * (layer % 2) + 45
            lines = self._make_infill_grid(base_ang, density, ewidth=ewidth)
        elif infill_type == "Hexagons":
            base_ang = 120 * (layer % 3)
            lines = self._make_infill_hexagons(base_ang, density, ewidth=ewidth)
        else:
            lines = []
        clipped_lines = []
        for line in lines:
            clipped_lines.extend(self._clip([line], mask, subj_closed=False))
        return clipped_lines

    def _overhang_mask_task(self, layer):
        supp_ang = self.conf['overhang_angle']
        mask = self._get_overhang_footprint(ang=supp_ang, z=self.layer_zs[layer])
        return self._diff(mask, self.layer_paths[layer])

    def _support_task(self, layer):
        density = self.conf['support_density'] / 100.0
        if density <= 0.0:
            return []
        ewidth = self.support_width
        try:
            outline = self.overhang_drops[layer]
        except IndexError:
            outline = []
        outline = self._offset(outline, -ewidth/2.0)
        outline = [self._close_path(path) for path in outline]
        mask = self._offset(outline, self.conf['infill_overlap']-ewidth)
        lines = self._make_infill_lines(0, density, ewidth=ewidth)
        infill = self._clip(lines, mask, subj_closed=False)
        return outline, infill

    ############################################################

    def _overhang_drop_task(self):
        outset = self.conf['support_outset']
        supp_type = self.conf['support_type']
        if supp_type == 'None':
            return []
        layer_drops = []
        drop_paths = []
        for layer in reversed(range(len(self.layer_zs))):
            drop_paths = self._union(drop_paths, self.overhang_masks[layer])
            layer_mask = self._offset(self.layer_paths[layer], outset)
            layer_drops.insert(0, self._diff(drop_paths, layer_mask))
        if supp_type == 'External':
            return layer_drops
        out_paths = []
        mask_paths = []
        for layer, drop_paths in enumerate(layer_drops):
            layer_mask = self._offset(self.layer_path[layer], outset)
            mask_paths = self._union(mask_paths, layer_mask)
            drop_paths = self._diff(drop_paths, mask_paths)
            out_paths.append(drop_paths)
        return out_paths

    def _brim_task(self):
        if self.conf['adhesion_type'] != "Brim":
            return []
        ewidth = self.support_width
        rings = math.ceil(self.conf['brim_width']/ewidth)
        paths = self.layer_paths[0]
        out = []
        for i in range(rings):
            out.append(self._offset(paths, (i+0.5)*ewidth))
        return out

    def _skirt_task(self):
        ewidth = self.support_width
        brim_w = self.conf['brim_width']
        skirt_w = self.conf['skirt_outset']
        minloops = self.conf['skirt_loops']
        minlen = self.conf['skirt_min_len']
        paths = self.layer_paths[0]
        skirt_paths = self._offset(paths, brim_w + skirt_w + ewidth/2.0)
        plen = sum(
            sum([math.hypot(p2[0]-p1[0], p2[1]-p1[1]) for p1, p2 in zip(path, path[1:]+path[0:1])])
            for path in skirt_paths
        )
        loops = minloops
        if self.conf['adhesion_type'] != "Raft":
            loops = max(loops, math.ceil(minlen/plen))
        base_paths = []
        for i in range(loops-1):
            base_paths.append(self._offset(skirt_paths, (i+1)*ewidth))
        return skirt_paths, base_paths

    def _raft_task(self):
        if self.conf['adhesion_type'] != "Raft":
            return [], []
        ewidth = self.support_width
        rings = math.ceil(self.conf['brim_width']/ewidth)
        outset = min(self.conf['skirt_outset']+ewidth*self.conf['skirt_loops'], self.conf['raft_outset'])
        paths = self.layer_paths[0]
        paths = self._union(paths, self.support_outline[0])
        outline = self._offset(paths, outset)
        mask = self._offset(outline, self.conf['infill_overlap']-ewidth)
        raftlines = []
        lines = self._make_infill_lines(0, 0.75, ewidth=ewidth)
        raftlines.append(self._clip(lines, mask, subj_closed=False))
        for layer in range(self.conf['raft_layers']-1):
            base_ang = 90 * ((layer+1) % 2)
            lines = self._make_infill_lines(base_ang, 1.0, ewidth=ewidth)
            raftlines.append(self._clip(lines, outline, subj_closed=False))
        return outline, raftlines

    ############################################################

    def _get_overhang_footprint(self, ang=45, z=None):
        tris = self.model.get_overhang_footprint_triangles(ang=ang, z=z)
        return self._union(tris, [])

    def _make_infill_pat(self, baseang, spacing, rots):
        ptcache = self.model.points
        minx = ptcache.minx
        maxx = ptcache.maxx
        miny = ptcache.miny
        maxy = ptcache.maxy
        w = maxx - minx
        h = maxy - miny
        cx = (maxx + minx)/2.0
        cy = (maxy + miny)/2.0
        r = max(w, h) * math.sqrt(2.0)
        n = math.ceil(r / spacing)
        out = []
        for rot in rots:
            s = math.sin((baseang+rot)*math.pi/180.0)
            c = math.cos((baseang+rot)*math.pi/180.0)
            for i in range(-n, n):
                p1 = (cx - r, cy + spacing*i)
                p2 = (cx + r, cy + spacing*i)
                line = [(x*c - y*s, x*s + y*c) for x, y in (p1, p2)]
                out.append( line )
        return out

    def _make_infill_lines(self, base_ang, density, ewidth=None):
        if density <= 0.0:
            return []
        if density > 1.0:
            density = 1.0
        if ewidth is None:
            ewidth = self.extrusion_width
        spacing = ewidth / density
        return self._make_infill_pat(base_ang, spacing, [0])

    def _make_infill_triangles(self, base_ang, density, ewidth=None):
        if density <= 0.0:
            return []
        if density > 1.0:
            density = 1.0
        if ewidth is None:
            ewidth = self.extrusion_width
        spacing = 3.0 * ewidth / density
        return self._make_infill_pat(base_ang, spacing, [0, 60, 120])

    def _make_infill_grid(self, base_ang, density, ewidth=None):
        if density <= 0.0:
            return []
        if density > 1.0:
            density = 1.0
        if ewidth is None:
            ewidth = self.extrusion_width
        spacing = 2.0 * ewidth / density
        return self._make_infill_pat(base_ang, spacing, [0, 90])

    def _make_infill_hexagons(self, base_ang, density, ewidth=None):
        if density <= 0.0:
            return []
        if density > 1.0:
            density = 1.0
        if ewidth is None:
            ewidth = self.extrusion_width
        ext = 0.5 * ewidth / math.tan(60.0*math.pi/180.0)
        aspect = 3.0 / math.sin(60.0*math.pi/180.0)
        col_spacing = ewidth * 4./3. / density
        row_spacing = col_spacing * aspect
        ptcache = self.model.points
        minx = ptcache.minx
        maxx = ptcache.maxx
        miny = ptcache.miny
        maxy = ptcache.maxy
        w = maxx - minx
        h = maxy - miny
        cx = (maxx + minx)/2.0
        cy = (maxy + miny)/2.0
        r = max(w, h) * math.sqrt(2.0)
        n_col = math.ceil(r / col_spacing)
        n_row = math.ceil(r / row_spacing)
        out = []
        s = math.sin(base_ang*math.pi/180.0)
        c = math.cos(base_ang*math.pi/180.0)
        for col in range(-n_col, n_col):
            path = []
            base_x = col * col_spacing
            for row in range(-n_row, n_row):
                base_y = row * row_spacing
                x1 = base_x + ewidth/2.0
                x2 = base_x + col_spacing - ewidth/2.0
                if col % 2 != 0:
                    x1, x2 = x2, x1
                path.append((x1, base_y+ext))
                path.append((x2, base_y+row_spacing/6-ext))
                path.append((x2, base_y+row_spacing/2+ext))
                path.append((x1, base_y+row_spacing*2/3-ext))
            path = [(x*c - y*s, x*s + y*c) for x, y in path]
            out.append(path)
        return out

    ############################################################

    def _tool_change_gcode(self, newnozl):
        retract_ext_dist = self.conf['retract_extruder']
        retract_speed = self.conf['retract_speed']
        gcode_lines = []
        gcode_lines.append("G1 E{e:.2f} F{f:g}\n".format(e=retract_ext_dist, f=retract_speed*60.0))
        gcode_lines.append("T{t:d}\n".format(t=newnozl))
        gcode_lines.append("G1 E{e:.2f} F{f:g}\n".format(e=-retract_ext_dist, f=retract_speed*60.0))
        return gcode_lines

    def _paths_gcode(self, paths, ewidth, nozl, z):
        fil_diam = self.conf['nozzle_{0:d}_filament'.format(nozl)]
        nozl_diam = self.conf['nozzle_{0:d}_filament'.format(nozl)]
        max_rate = self.conf['nozzle_{0:d}_max_rate'.format(nozl)]
        layer_height = self.conf['layer_height']
        retract_dist = self.conf['retract_dist']
        retract_speed = self.conf['retract_speed']
        retract_lift = self.conf['retract_lift']
        feed_rate = self.conf['feed_rate']
        travel_rate_xy = self.conf['travel_rate_xy']
        travel_rate_z = self.conf['travel_rate_z']
        ewidth = nozl_diam * self.extrusion_ratio
        xsect = ewidth * layer_height
        fil_xsect = math.pi * fil_diam * fil_diam / 4
        gcode_lines = []
        for path in paths:
            ox, oy = path[0][0:2]
            tot_ext = 0.0
            gcode_lines.append("G92 E0\n")
            gcode_lines.append("G1 Z{z:.2f} F{f:g}\n".format(z=z+retract_lift, f=travel_rate_z*60.0))
            gcode_lines.append("G1 X{x:.2f} Y{y:.2f} F{f:g}\n".format(x=ox, y=oy, f=travel_rate_xy*60.0))
            if retract_lift > 0.0:
                gcode_lines.append("G1 Z{z:.2f} F{f:g}\n".format(z=z, f=travel_rate_z*60.0))
            gcode_lines.append("G1 E{e:.2f} F{f:g}\n".format(e=retract_dist, f=retract_speed*60.0))
            for x, y in path[1:]:
                dist = math.hypot(y-oy, x-ox)
                fil_dist = dist * xsect / fil_xsect
                secs = dist / feed_rate
                if secs > 0:
                    vol_rate = fil_dist * fil_xsect / secs
                    ratio = min(vol_rate, max_rate) / vol_rate
                else:
                    ratio = 1.0
                tot_ext += fil_dist
                gcode_lines.append("G1 X{x:.2f} Y{y:.2f} E{e:.2f} F{f:g}\n".format(x=x, y=y, e=tot_ext, f=ratio*feed_rate*60.0))
                ox, oy = x, y
            gcode_lines.append("G1 E{e:.2f} F{f:g}\n".format(e=tot_ext-retract_dist, f=retract_speed*60.0))
        return gcode_lines

    ############################################################

    def _offset(self, paths, amount):
        # print("_offset(\n  paths={},\n  amount={}\n)\n\n".format(paths, amount), file=sys.stderr);
        pco = pyclipper.PyclipperOffset()
        paths = pyclipper.scale_to_clipper(paths, self.SCALING_FACTOR)
        pco.AddPaths(paths, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
        outpaths = pco.Execute(amount * self.SCALING_FACTOR)
        outpaths = pyclipper.scale_from_clipper(outpaths, self.SCALING_FACTOR)
        return outpaths

    def _union(self, paths1, paths2):
        # print("_union(\n  paths1={},\n  paths2={}\n)\n\n".format(paths1, paths2), file=sys.stderr);
        pc = pyclipper.Pyclipper()
        if paths1:
            if paths1[0][0] in (int, float):
                raise pyclipper.ClipperException()
            paths1 = pyclipper.scale_to_clipper(paths1, self.SCALING_FACTOR)
            pc.AddPaths(paths1, pyclipper.PT_SUBJECT, True)
        if paths2:
            if paths2[0][0] in (int, float):
                raise pyclipper.ClipperException()
            paths2 = pyclipper.scale_to_clipper(paths2, self.SCALING_FACTOR)
            pc.AddPaths(paths2, pyclipper.PT_CLIP, True)
        outpaths = pc.Execute(pyclipper.CT_UNION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
        outpaths = pyclipper.scale_from_clipper(outpaths, self.SCALING_FACTOR)
        return outpaths

    def _diff(self, subj, clip_paths, subj_closed=True):
        # print("_diff(\n  subj={},\n  clip_paths={}\n  subj_closed={}\n)\n\n".format(subj, clip_paths, subj_closed), file=sys.stderr);
        pc = pyclipper.Pyclipper()
        if subj:
            subj = pyclipper.scale_to_clipper(subj, self.SCALING_FACTOR)
            pc.AddPaths(subj, pyclipper.PT_SUBJECT, subj_closed)
        if clip_paths:
            clip_paths = pyclipper.scale_to_clipper(clip_paths, self.SCALING_FACTOR)
            pc.AddPaths(clip_paths, pyclipper.PT_CLIP, True)
        outpaths = pc.Execute(pyclipper.CT_DIFFERENCE, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
        outpaths = pyclipper.scale_from_clipper(outpaths, self.SCALING_FACTOR)
        return outpaths

    def _clip(self, subj, clip_paths, subj_closed=True):
        # print("_clip(\n  subj={},\n  clip_paths={}\n  subj_closed={}\n)\n\n".format(subj, clip_paths, subj_closed), file=sys.stderr);
        pc = pyclipper.Pyclipper()
        if subj:
            subj = pyclipper.scale_to_clipper(subj, self.SCALING_FACTOR)
            pc.AddPaths(subj, pyclipper.PT_SUBJECT, subj_closed)
        if clip_paths:
            clip_paths = pyclipper.scale_to_clipper(clip_paths, self.SCALING_FACTOR)
            pc.AddPaths(clip_paths, pyclipper.PT_CLIP, True)
        out_tree = pc.Execute2(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
        outpaths = pyclipper.PolyTreeToPaths(out_tree)
        outpaths = pyclipper.scale_from_clipper(outpaths, self.SCALING_FACTOR)
        return outpaths

    def _paths_bounds(self, paths):
        minx = None
        miny = None
        maxx = None
        maxy = None
        for path in path:
            for x, y in path:
                if minx is None or x < minx:
                    minx = x
                if maxx is None or x > maxx:
                    maxx = x
                if miny is None or y < miny:
                    miny = y
                if maxy is None or y > maxy:
                    maxy = y
        return (minx, miny, maxx, maxy)

    ############################################################

    def _display_paths(self):
        self.layer = 0
        self.mag = 5.0
        self.master = Tk()
        self.canvas = Canvas(self.master, width=800, height=600)
        self.canvas.pack(fill=BOTH, expand=1)
        self.canvas.focus()
        self.master.bind("<Key-Up>", lambda e: self._redraw_paths(incdec=1))
        self.master.bind("<Key-Down>", lambda e: self._redraw_paths(incdec=-1))
        self.master.bind("<Key-equal>", lambda e: self._zoom(incdec=1))
        self.master.bind("<Key-minus>", lambda e: self._zoom(incdec=-1))
        self.master.bind("<Key-1>", lambda e: self._zoom(val= 5.0))
        self.master.bind("<Key-2>", lambda e: self._zoom(val=10.0))
        self.master.bind("<Key-3>", lambda e: self._zoom(val=15.0))
        self.master.bind("<Key-4>", lambda e: self._zoom(val=20.0))
        self.master.bind("<Key-q>", lambda e: sys.exit(0))
        self.master.bind("<Key-Escape>", lambda e: sys.exit(0))
        self._redraw_paths()
        mainloop()

    def _zoom(self, incdec=0, val=None):
        if val is None:
            self.mag = max(1, self.mag+incdec)
        else:
            self.mag = val
        self._redraw_paths()

    def _redraw_paths(self, incdec=0):
        self.layer = min(max(0, self.layer + incdec), len(self.perimeter_paths)-1)
        self.canvas.delete(ALL)
        self.canvas.create_text((30, 550), anchor=NW, text="Layer {layer}\nZ: {z:.2f}\nZoom: {zoom:.1f}%".format(layer=self.layer, z=self.layer_zs[self.layer], zoom=self.mag*100/5.0))

        colors = ["#700", "#c00", "#f00", "#f77"]
        self._draw_line(self.support_outline[self.layer], colors=colors, ewidth=self.support_width)
        self._draw_line(self.support_infill[self.layer], colors=colors, ewidth=self.support_width)

        colors = ["#070", "#0c0", "#0f0", "#7f7"]
        for pathnum, path in enumerate(self.perimeter_paths[self.layer]):
            self._draw_line(path, offset=pathnum, colors=colors, ewidth=self.extrusion_width)

        colors = ["#770", "#aa0", "#dd0", "#ff0"]
        self._draw_line(self.solid_infill[self.layer], colors=colors, ewidth=self.infill_width)
        self._draw_line(self.sparse_infill[self.layer], colors=colors, ewidth=self.infill_width)

    def _draw_line(self, paths, offset=0, colors=["red", "green", "blue"], ewidth=0.5):
        ptcache = self.model.points
        wincx = self.master.winfo_width() / 2
        wincy = self.master.winfo_height() / 2
        wincx = wincx if wincx > 1 else 400
        wincy = wincy if wincy > 1 else 300
        minx = ptcache.minx
        maxx = ptcache.maxx
        miny = ptcache.miny
        maxy = ptcache.maxy
        cx = (maxx + minx)/2.0
        cy = (maxy + miny)/2.0
        for pathnum, path in enumerate(paths):
            path = [(wincx+(x-cx)*self.mag, wincy+(cy-y)*self.mag) for x, y in path]
            color = colors[(pathnum + offset) % len(colors)]
            self.canvas.create_line(path, fill=color, width=self.mag*ewidth, capstyle=ROUND, joinstyle=ROUND)


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
