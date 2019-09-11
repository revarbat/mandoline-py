from __future__ import print_function

import sys
import math
import time
import os.path
from collections import OrderedDict
from appdirs import user_config_dir

import mandoline.geometry2d as geom
from .TextThermometer import TextThermometer


# Support:
#   For External support type:
#     Start with total footprint
#     For each layer up from bottom, diff out layer outline (outset by support_outset) to calc layer support clip region
#     Make array of parallel lines
#     clip lines by layer clip region
#     add clipped lines and clip region outline to layer output.


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
        ('skirt_min_len',     float, 10.0, (0., 1000.), "Add extra loops on the first layer until we've extruded at least this amount."),
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
        ('heated_bed_temp',   int,     70, (0, 150),   "The temperature to set the heated bed to."),

        ('extruder_count',    int,      1, (1, 4),     "The number of extruders this machine has."),
        ('default_nozzle',    int,      0, (0, 7),     "The default extruder used for printing."),
        ('infill_nozzle',     int,     -1, (-1, 7),    "The extruder used for infill material.  -1 means use default nozzle."),
        ('support_nozzle',    int,     -1, (-1, 7),    "The extruder used for support material.  -1 means use default nozzle."),

        ('nozzle_0_temp',     int,    190, (150, 250),  "The temperature of the nozzle for extruder 0. (C)"),
        ('nozzle_0_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 0. (mm)"),
        ('nozzle_0_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 0. (mm)"),
        ('nozzle_0_xoff',     float,  0.0, (-100., 100.), "The X positional offset for extruder 0. (mm)"),
        ('nozzle_0_yoff',     float,  0.0, (-100., 100.), "The Y positional offset for extruder 0. (mm)"),
        ('nozzle_0_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 0. (mm^3/s)"),

        ('nozzle_1_temp',     int,    190, (150, 250),  "The temperature of the nozzle for extruder 1. (C)"),
        ('nozzle_1_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 1. (mm)"),
        ('nozzle_1_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 1. (mm)"),
        ('nozzle_1_xoff',     float, 25.0, (-100., 100.), "The X positional offset for extruder 1. (mm)"),
        ('nozzle_1_yoff',     float,  0.0, (-100., 100.), "The Y positional offset for extruder 1. (mm)"),
        ('nozzle_1_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 1. (mm^3/s)"),

        ('nozzle_2_temp',     int,    190, (150, 250),  "The temperature of the nozzle for extruder 2. (C)"),
        ('nozzle_2_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 2. (mm)"),
        ('nozzle_2_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 2. (mm)"),
        ('nozzle_2_xoff',     float, -25., (-100., 100.), "The X positional offset for extruder 2. (mm)"),
        ('nozzle_2_yoff',     float,  0.0, (-100., 100.), "The Y positional offset for extruder 2. (mm)"),
        ('nozzle_2_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 2. (mm^3/s)"),

        ('nozzle_3_temp',     int,    190, (150, 250),  "The temperature of the nozzle for extruder 3. (C)"),
        ('nozzle_3_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 3. (mm)"),
        ('nozzle_3_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 3. (mm)"),
        ('nozzle_3_xoff',     float,  0.0, (-100., 100.), "The X positional offset for extruder 3. (mm)"),
        ('nozzle_3_yoff',     float, 25.0, (-100., 100.), "The Y positional offset for extruder 3. (mm)"),
        ('nozzle_3_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 3. (mm^3/s)"),
    )),
])


############################################################


class Slicer(object):
    def __init__(self, model, **kwargs):
        self.model = model
        self.conf = {}
        self.conf_metadata = {}
        for key, opts in slicer_configs.items():
            for name, typ, dflt, rng, desc in opts:
                self.conf[name] = dflt
                self.conf_metadata[name] = {
                    "type": typ,
                    "default": dflt,
                    "range": rng,
                    "descr": desc
                }
        self.mag = 4
        self.layer = 0
        self.config(**kwargs)

    def config(self, **kwargs):
        for key, val in kwargs.items():
            if key in self.conf:
                self.conf[key] = val

    def get_conf_filename(self):
        return user_config_dir("Mandoline")

    def set_config(self, key, valstr):
        key = key.strip()
        valstr = valstr.strip()
        if key not in self.conf_metadata:
            print("Ignoring unknown config option: {}".format(key))
            return
        typ = self.conf_metadata[key]["type"]
        rng = self.conf_metadata[key]["range"]
        badval = True
        typestr = ""
        errmsg = ""
        if typ is bool:
            typestr = "boolean "
            errmsg = "Value should be either True or False"
            if valstr in ["True", "False"]:
                self.conf[key] = valstr == "True"
                badval = False
        elif typ is int:
            typestr = "integer "
            errmsg = "Value should be between {} and {}, inclusive.".format(*rng)
            try:
                if int(valstr) >= rng[0] and int(valstr) <= rng[1]:
                    self.conf[key] = int(valstr)
                    badval = False
            except(ValueError):
                pass
        elif typ is float:
            typestr = "float "
            errmsg = "Value should be between {} and {}, inclusive.".format(*rng)
            try:
                if float(valstr) >= rng[0] and float(valstr) <= rng[1]:
                    self.conf[key] = float(valstr)
                    badval = False
            except(ValueError):
                pass
        elif typ is list:
            typestr = ""
            errmsg = "Valid options are: {}".format(", ".join(rng))
            if valstr in rng:
                self.conf[key] = str(valstr)
                badval = False
        if badval:
            print("Ignoring bad {0}configuration value: {1}={2}".format(typestr,key,valstr))
            print(errmsg)

    def load_configs(self):
        conffile = self.get_conf_filename()
        if not os.path.exists(conffile):
            return
        if not os.path.isfile(conffile):
            return
        print("Loading configs from {}".format(conffile))
        with open(conffile, "r") as f:
            for line in f.readlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, val = line.split("=")
                self.set_config(key,val)

    def save_configs(self):
        conffile = self.get_conf_filename()
        confdir = os.path.dirname(conffile)
        if not os.path.exists(confdir):
            os.makedirs(confdir)
        with open(conffile, "w") as f:
            for sect, opts in slicer_configs.items():
                f.write("# {}\n".format(sect))
                for name, typ, dflt, rng, desc in opts:
                    f.write("{}={}\n".format(name, self.conf[name]))
                f.write("\n\n")
        print("Saving configs to {}".format(conffile))

    def display_configs_help(self, key=None, vals_only=False):
        if key:
            key = key.strip()
            if key not in self.conf_metadata:
                print("Unknown config option: {}".format(key))
                return
        for sect, opts in slicer_configs.items():
            if not vals_only and not key:
                print("{}:".format(sect))
            for name, typ, dflt, rng, desc in opts:
                if key and key != name:
                    continue
                if typ is bool:
                    typename = "bool"
                    rngstr = "True/False"
                elif typ is int:
                    typename = "int"
                    rngstr = "{} ... {}".format(*rng)
                elif typ is float:
                    typename = "float"
                    rngstr = "{} ... {}".format(*rng)
                elif typ is list:
                    typename = "opt"
                    rngstr = ", ".join(rng)
                print("  {} = {}".format(name, self.conf[name]))
                if not vals_only:
                    print("          Type: {}  ({})".format(typename, rngstr))
                    print("          {}".format(desc))

    def slice_to_file(self, filename, showgui=False):
        print("Slicing start")
        self.dflt_nozl = self.conf['default_nozzle']
        self.infl_nozl = self.conf['infill_nozzle']
        self.supp_nozl = self.conf['support_nozzle']
        if self.infl_nozl == -1:
            self.infl_nozl = self.dflt_nozl
        if self.supp_nozl == -1:
            self.supp_nozl = self.dflt_nozl
        dflt_nozl_d = self.conf['nozzle_{0}_diam'.format(self.dflt_nozl)]
        infl_nozl_d = self.conf['nozzle_{0}_diam'.format(self.infl_nozl)]
        supp_nozl_d = self.conf['nozzle_{0}_diam'.format(self.supp_nozl)]

        self.layer_h = self.conf['layer_height']
        self.extrusion_ratio = 1.25
        self.extrusion_width = dflt_nozl_d * self.extrusion_ratio
        self.infill_width = infl_nozl_d * self.extrusion_ratio
        self.support_width = supp_nozl_d * self.extrusion_ratio
        height = self.model.points.maxz - self.model.points.minz
        self.layers = int(height / self.layer_h)
        self.model.assign_layers(self.layer_h)
        self.layer_zs = [
            self.model.points.minz + self.layer_h * (layer + 1)
            for layer in range(self.layers)
        ]
        self.thermo = TextThermometer(self.layers)

        print("Perimeters")
        self._slicer_task_perimeters()

        print("Support")
        self._slicer_task_support()

        print("Raft, Brim, and Skirt")
        self._slicer_task_adhesion()

        print("Infill")
        self._slicer_task_fill()

        print("Gcode Generation")
        self._slicer_task_gcode(filename)

        print("Slicing complete")

        if showgui:
            print("Launching slice viewer")
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

    ############################################################

    def _slicer_task_perimeters(self):
        self.thermo.set_target(2*self.layers)
        self.layer_paths = []
        self.perimeter_paths = []
        self.bounding_region = []
        for layer in range(self.layers):
            self.thermo.update(layer)

            # Layer Slicing
            z = self.layer_zs[layer]
            paths = self.model.slice_at_z(z - self.layer_h/2, self.layer_h)
            paths = geom.orient_paths(paths)
            paths = geom.union(paths, [])
            self.layer_paths.append(paths)

            # Perimeters
            perims = []
            for i in range(self.conf['shell_count']):
                shell = geom.offset(paths, -(i+0.5) * self.extrusion_width)
                shell = geom.close_paths(shell)
                perims.append(shell)
            self.perimeter_paths.append(perims)

            # Calculate horizontal bounding path
            self.bounding_region = geom.union(self.bounding_region, paths)

        self.top_masks = []
        self.bot_masks = []
        for layer in range(self.layers):
            self.thermo.update(self.layers+layer)

            # Top and Bottom masks
            below = [] if layer < 1 else self.perimeter_paths[layer-1][-1]
            perim = self.perimeter_paths[layer][-1]
            above = [] if layer >= self.layers-1 else self.perimeter_paths[layer+1][-1]
            self.top_masks.append(geom.diff(perim, above))
            self.bot_masks.append(geom.diff(perim, below))
        self.thermo.clear()

    def _slicer_task_support(self):
        self.thermo.set_target(4.0)

        self.support_outline = []
        self.support_infill = []
        supp_type = self.conf['support_type']
        if supp_type == 'None':
            return
        supp_ang = self.conf['overhang_angle']
        outset = self.conf['support_outset']

        facets = self.model.get_facets()
        facet_cnt = len(facets)
        drop_paths = [[] for layer in range(self.layers)]
        for fnum, facet in enumerate(facets):
            self.thermo.update((fnum+0.0)/facet_cnt)
            if facet.overhang_angle() < supp_ang:
                continue
            minz, maxz = facet.z_range()
            footprint = facet.get_footprint()
            if not footprint:
                break
            for layer in range(self.layers):
                z = self.layer_zs[layer]
                if z > maxz:
                    break
                if z >= minz:
                    footprint = facet.get_footprint(z=z)
                    if not footprint:
                        break
                drop_paths[layer].append(footprint)
                # drop_paths[layer] = geom.union(drop_paths[layer], [footprint])

        cumm_mask = []
        for layer in range(self.layers):
            self.thermo.update(1 + (0.0+layer)/self.layers)

            # Remove areas too close to model
            mask = geom.offset(self.layer_paths[layer], outset)
            if layer > 0 and supp_type == "Everywhere":
                mask = geom.union(mask, geom.offset(self.layer_paths[layer-1], outset))
            if layer < self.layers - 1:
                mask = geom.union(mask, geom.offset(self.layer_paths[layer+1], outset))
            if supp_type == "External":
                cumm_mask = geom.union(cumm_mask, mask)
                mask = cumm_mask
            overhang = geom.diff(drop_paths[layer], mask)

            # Clean up overhang paths
            overhang = geom.offset(overhang, self.extrusion_width)
            overhang = geom.offset(overhang, -self.extrusion_width*2)
            overhang = geom.offset(overhang, self.extrusion_width)
            drop_paths[layer] = geom.close_paths(overhang)

        for layer in range(self.layers):
            self.thermo.update(2 + (2.0+layer)/self.layers)

            # Generate support infill
            outline = []
            infill = []
            overhangs = drop_paths[layer]
            density = self.conf['support_density'] / 100.0
            if density > 0.0:
                outline = geom.offset(overhangs, -self.extrusion_width/2.0)
                outline = geom.close_paths(outline)
                mask = geom.offset(outline, self.conf['infill_overlap']-self.extrusion_width)
                bounds = geom.paths_bounds(mask)
                lines = geom.make_infill_lines(bounds, 0, density, self.extrusion_width)
                infill = geom.clip(lines, mask, subj_closed=False)
            self.support_outline.append(outline)
            self.support_infill.append(infill)

        self.thermo.clear()

    # Adhesion Paths
    def _slicer_task_adhesion(self):
        # Raft
        raft_outline = []
        raft_infill = []
        if self.conf['adhesion_type'] == "Raft":
            rings = int(math.ceil(self.conf['brim_width']/self.extrusion_width))
            outset = max(self.conf['skirt_outset']+self.extrusion_width*self.conf['skirt_loops'], self.conf['raft_outset'])
            paths = geom.union(self.layer_paths[0], self.support_outline[0])
            raft_outline = geom.offset(paths, outset)
            bounds = geom.paths_bounds(raft_outline)
            mask = geom.offset(raft_outline, self.conf['infill_overlap']-self.extrusion_width)
            lines = geom.make_infill_lines(bounds, 0, 0.75, self.extrusion_width)
            raft_infill.append(geom.clip(lines, mask, subj_closed=False))
            raft_layers = self.conf['raft_layers']
            for layer in range(raft_layers-1):
                base_ang = 90 * ((layer+1) % 2)
                lines = geom.make_infill_lines(bounds, base_ang, 1.0, self.extrusion_width)
                raft_infill.append(geom.clip(lines, raft_outline, subj_closed=False))
                self.layer_zs.append(self.layer_zs[-1]+self.layer_h)
        self.raft_outline = geom.close_paths(raft_outline)
        self.raft_infill = raft_infill
        for layer in range(len(self.layer_zs)):
            self.layer_zs[layer] -= self.model.points.minz

        # Brim
        brim = []
        adhesion = self.conf['adhesion_type']
        brim_w = self.conf['brim_width']
        if adhesion == "Brim":
            rings = int(math.ceil(brim_w/self.extrusion_width))
            for i in range(rings):
                for path in geom.offset(self.layer_paths[0], (i+0.5)*self.extrusion_width):
                    if path[-1] != path[0]:
                        path.append(path[0])
                    brim.append(path)
        self.brim_paths = geom.close_paths(brim)

        # Skirt
        skirt = []
        priming = []
        skirt_w = self.conf['skirt_outset']
        minloops = self.conf['skirt_loops']
        minlen = self.conf['skirt_min_len']
        skirt_mask = geom.union(self.bounding_region, self.support_outline[0])
        skirt = geom.offset(skirt_mask, brim_w + skirt_w + self.extrusion_width/2.0)
        self.skirt_paths = geom.close_paths(skirt)
        plen = max(
            1.0,
            sum(
                sum([math.hypot(p2[0]-p1[0], p2[1]-p1[1]) for p1, p2 in zip(path, path[1:]+path[0:1])])
                for path in skirt
            )
        )
        loops = minloops
        if adhesion != "Raft":
            loops = max(loops, int(math.ceil(minlen/plen)))
        for i in range(loops-1):
            for path in geom.offset(skirt, (i+1)*self.extrusion_width):
                priming.append(path)
        self.priming_paths = geom.close_paths(priming)
        self.thermo.clear()

    # Infill Paths
    def _slicer_task_fill(self):
        self.thermo.set_target(self.layers)

        self.solid_infill = []
        self.sparse_infill = []
        for layer in range(self.layers):
            self.thermo.update(layer)
            # Solid Mask
            top_cnt = self.conf['top_layers']
            bot_cnt = self.conf['bottom_layers']
            top_masks = self.top_masks[layer : layer+top_cnt]
            perims = self.perimeter_paths[layer]
            bot_masks = self.bot_masks[max(0, layer-bot_cnt+1) : layer+1]
            outmask = []
            for mask in top_masks:
                outmask = geom.union(outmask, geom.close_paths(mask))
            for mask in bot_masks:
                outmask = geom.union(outmask, geom.close_paths(mask))
            solid_mask = geom.clip(outmask, perims[-1])
            bounds = geom.paths_bounds(perims[-1])

            # Solid Infill
            solid_infill = []
            base_ang = 45 if layer % 2 == 0 else -45
            solid_mask = geom.offset(solid_mask, self.conf['infill_overlap']-self.extrusion_width)
            lines = geom.make_infill_lines(bounds, base_ang, 1.0, self.extrusion_width)
            for line in lines:
                lines = [line]
                lines = geom.clip(lines, solid_mask, subj_closed=False)
                solid_infill.extend(lines)
            self.solid_infill.append(solid_infill)

            # Sparse Infill
            sparse_infill = []
            infill_type = self.conf['infill_type']
            density = self.conf['infill_density'] / 100.0
            if density > 0.0:
                if density >= 0.99:
                    infill_type = "Lines"
                mask = geom.offset(perims[-1], self.conf['infill_overlap']-self.infill_width)
                mask = geom.diff(mask, solid_mask)
                if infill_type == "Lines":
                    base_ang = 90 * (layer % 2) + 45
                    lines = geom.make_infill_lines(bounds, base_ang, density, self.infill_width)
                elif infill_type == "Triangles":
                    base_ang = 60 * (layer % 3)
                    lines = geom.make_infill_triangles(bounds, base_ang, density, self.infill_width)
                elif infill_type == "Grid":
                    base_ang = 90 * (layer % 2) + 45
                    lines = geom.make_infill_grid(bounds, base_ang, density, self.infill_width)
                elif infill_type == "Hexagons":
                    base_ang = 120 * (layer % 3)
                    lines = geom.make_infill_hexagons(bounds, base_ang, density, self.infill_width)
                else:
                    lines = []
                lines = geom.clip(lines, mask, subj_closed=False)
                sparse_infill.extend(lines)
            self.sparse_infill.append(sparse_infill)
        self.thermo.clear()

    def _slicer_task_gcode(self, filename):
        self.thermo.set_target(self.layers)

        raft_layers = len(self.raft_infill)
        with open(filename, "w") as f:
            f.write("( setup )\n")
            f.write("M82 ;absolute extrusion mode\n")
            f.write("M107 ;Fan off\n")
            if self.conf['heated_bed_temp'] > 0:
                f.write("M140 S{:d} ;set bed temp\n".format(self.conf['heated_bed_temp']))
                f.write("M190 S{:d} ;wait for bed temp\n".format(self.conf['heated_bed_temp']))
            f.write("M104 S{:d} ;set extruder0 temp\n".format(self.conf['nozzle_0_temp']))
            f.write("M109 S{:d} ;wait for extruder0 temp\n".format(self.conf['nozzle_0_temp']))
            f.write("G28 ;auto-home all axes\n")
            f.write("G1 Z15 F6000 ;raise extruder\n")
            f.write("G92 E0\n")
            f.write("G1 F200 E3\n")
            f.write("G92 E0\n")

            if self.raft_outline:
                f.write("( raft_outline )\n")
                outline = geom.close_paths(self.raft_outline)
                for line in self._paths_gcode(outline, self.support_width, self.supp_nozl, self.layer_zs[0]):
                    f.write(line)
            if self.raft_infill:
                f.write("( raft_infill )\n")
                for layer, layer_paths in enumerate(self.raft_infill):
                    for line in self._paths_gcode(layer_paths, self.support_width, self.supp_nozl, self.layer_zs[layer]):
                        f.write(line)

            layer = raft_layers
            if self.priming_paths:
                f.write("( priming )\n")
                paths = geom.close_paths(self.priming_paths)
                for line in self._paths_gcode(paths, self.support_width, self.supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            if self.brim_paths:
                f.write("( brim )\n")
                for line in self._paths_gcode(self.brim_paths, self.support_width, self.supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            for slicenum in range(len(self.perimeter_paths)):
                self.thermo.update(slicenum)
                layer = raft_layers + slicenum

                if self.skirt_paths and slicenum < self.conf['skirt_layers']:
                    f.write("( skirt )\n")
                    for line in self._paths_gcode(self.skirt_paths, self.support_width, self.supp_nozl, self.layer_zs[layer]):
                        f.write(line)

                outline = geom.close_paths(self.support_outline[slicenum])
                f.write("( support outline )\n")
                for line in self._paths_gcode(outline, self.support_width, self.supp_nozl, self.layer_zs[layer]):
                    f.write(line)
                f.write("( support infill )\n")
                for line in self._paths_gcode(self.support_infill[slicenum], self.support_width, self.supp_nozl, self.layer_zs[layer]):
                    f.write(line)

                f.write("( perimeters )\n")
                for paths in reversed(self.perimeter_paths[slicenum]):
                    paths = geom.close_paths(paths)
                    for line in self._paths_gcode(paths, self.extrusion_width, self.dflt_nozl, self.layer_zs[layer]):
                        f.write(line)
                f.write("( solid fill )\n")
                for line in self._paths_gcode(self.solid_infill[slicenum], self.extrusion_width, self.dflt_nozl, self.layer_zs[layer]):
                    f.write(line)

                f.write("( sparse infill )\n")
                for line in self._paths_gcode(self.sparse_infill[slicenum], self.infill_width, self.infl_nozl, self.layer_zs[layer]):
                    f.write(line)
            self.thermo.clear()

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

    def _display_paths(self):
        try:  # Python 2
            from Tkinter import (Tk, Canvas, mainloop)
        except ImportError:  # Python 3
            from tkinter import (Tk, Canvas, mainloop)
        self.layer = 0
        self.mag = 5.0
        self.master = Tk()
        self.canvas = Canvas(self.master, width=800, height=600)
        self.canvas.pack(fill="both", expand=1)
        self.canvas.focus()
        self.master.bind("<Key-Prior>", lambda e: self._redraw_paths(incdec=10))
        self.master.bind("<Key-Up>", lambda e: self._redraw_paths(incdec=1))
        self.master.bind("<Key-Down>", lambda e: self._redraw_paths(incdec=-1))
        self.master.bind("<Key-Next>", lambda e: self._redraw_paths(incdec=-10))
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
        raft_layers = len(self.raft_infill)
        self.layer = min(max(0, self.layer + incdec), len(self.perimeter_paths)-1+raft_layers)
        layernum = self.layer
        layers = raft_layers + self.layers
        self.canvas.delete("all")
        self.canvas.create_text((30, 550), anchor="nw", text="Layer {layer}/{layers}\nZ: {z:.2f}\nZoom: {zoom:.1f}%".format(layer=layernum, layers=layers-1, z=self.layer_zs[layernum], zoom=self.mag*100/5.0))
        barpos = (150,570)
        barsize = (500,10)
        pcnt = layernum / (layers-1.0)
        self.canvas.create_rectangle(barpos[0]-1,barpos[1]-1,barpos[0]+barsize[0]+1,barpos[1]+barsize[1]+1,outline="black")
        if pcnt * barsize[0] > 1.0:
            self.canvas.create_rectangle(barpos[0],barpos[1],barpos[0]+int(barsize[0]*pcnt),barpos[1]+barsize[1],outline="blue",fill="blue")

        colors = ["#700", "#c00", "#f00", "#f77"]
        if layernum < raft_layers:
            if layernum == 0:
                self._draw_line(self.raft_outline, colors=colors, ewidth=self.support_width)
            self._draw_line(self.raft_infill[layernum], colors=colors, ewidth=self.support_width)
            return
        else:
            if layernum == 0:
                self._draw_line(self.priming_paths, colors=colors, ewidth=self.support_width)
                self._draw_line(self.brim_paths, colors=colors, ewidth=self.support_width)
            layernum -= raft_layers

        if self.skirt_paths and layernum < self.conf['skirt_layers']:
            self._draw_line(self.skirt_paths, colors=colors, ewidth=self.support_width)
        self._draw_line(self.support_outline[layernum], colors=colors, ewidth=self.support_width)
        self._draw_line(self.support_infill[layernum], colors=colors, ewidth=self.support_width)

        colors = ["#070", "#0c0", "#0f0", "#7f7"]
        for pathnum, path in enumerate(self.perimeter_paths[layernum]):
            self._draw_line(path, offset=pathnum, colors=colors, ewidth=self.extrusion_width)

        colors = ["#770", "#aa0", "#dd0", "#ff0"]
        self._draw_line(self.solid_infill[layernum], colors=colors, ewidth=self.infill_width)
        self._draw_line(self.sparse_infill[layernum], colors=colors, ewidth=self.infill_width)

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
            self.canvas.create_line(path, fill=color, width=self.mag*ewidth, capstyle="round", joinstyle="round")


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
