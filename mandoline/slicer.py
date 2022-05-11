from __future__ import print_function

import sys
import math
import time
import random
import os.path
import platform
from collections import OrderedDict
from appdirs import user_config_dir

import mandoline.geometry2d as geom
from .TextThermometer import TextThermometer


slicer_configs = OrderedDict([
    ('Quality', (
        ('layer_height',      float,  50., (0.1, 100.0), "Slice layer height in mm."),
        ('shell_count',       int,      1, (1, 10),     "Number of outer shells to print."),
        ('random_starts',     bool,   True, None,       "Enable randomizing of perimeter starts."),
        ('top_layers',        int,      1, (0, 10),     "Number of layers to print on the top side of the object."),
        ('bottom_layers',     int,      1, (0, 10),     "Number of layers to print on the bottom side of the object."),
        ('infill_type',       list, 'Triangles', ['Lines', 'Triangles', 'Grid', 'Hexagons'], "Pattern that the infill will be printed in."),
        ('infill_density',    float,  25., (0., 100.),  "Infill density in percent."),
        ('infill_overlap',    float,   1., (0.0, 10.0),  "Amount, in mm that infill will overlap with perimeter extrusions."),
        ('feed_rate',         int,    100, (1, 300),    "Speed while extruding. (mm/s)"),
        ('travel_rate_xy',    int,    100, (1, 300),    "Travel motion speed (mm/s)"),
        ('travel_rate_z',     float,  50., (0.1, 100.),  "Z-axis  motion speed (mm/s)"),
    )),
    ('Support', (
        ('support_type',      list, 'External', ('None', 'External', 'Everywhere'), "What kind of support structure to add."),
        ('support_outset',    float,    2., (0., 2.),   "How far support structures should be printed away from model, horizontally."),
        ('support_density',   float,  33.0, (0., 100.), "Density of support structure internals."),
        ('overhang_angle',    int,      45, (0, 90),    "Angle from vertical that support structures should be printed for."),
    )),
    ('Adhesion', (
        ('adhesion_type',     list, 'None', ('None', 'Brim', 'Raft'), "What kind of base adhesion structure to add."),
        ('brim_width',        float,  0.0, (0., 20.),   "Width of brim to print on first layer to help with part adhesion."),
        ('raft_layers',       int,      1, (1, 5),      "Number of layers to use in making the raft."),
        ('raft_outset',       float,  5.0, (0., 50.),   "How much bigger raft should be than the model footprint."),
        ('skirt_outset',      float,  0.0, (0., 20.),   "How far the skirt should be printed away from model."),
        ('skirt_layers',      int,      0, (0, 1000),   "Number of layers to print print the skirt on."),
        ('prime_length',      float, 10.0, (0., 1000.), "Length of filament to extrude when priming hotends."),
    )),
    ('Retraction', (
        ('retract_enable',    bool,   True, None,       "Enable filament retraction."),
        ('retract_speed',     float,  50.0, (0., 200.), "Speed to retract filament at. (mm/s)"),
        ('retract_dist',      float,   5.0, (0., 20.),  "Distance to retract filament between extrusion moves. (mm)"),
        ('retract_extruder',  float,   5.0, (0., 50.),  "Distance to retract filament on extruder change. (mm)"),
        ('retract_lift',      float,   0.0, (0., 10.),  "Distance to lift the extruder head during retracted moves. (mm)"),
    )),
    ('Materials', (
        ('abs_bed_temp',        int,      90,  (  0, 150),  "The bed temperature to use for ABS filament. (C)"),
        ('abs_hotend_temp',     int,     230,  (150, 300),  "The extruder temperature to use for ABS filament. (C)"),
        ('abs_max_speed',       float,  75.0,  (  0, 150),  "The maximum speed when extruding ABS filament. (mm/s)"),
        ('hips_bed_temp',       int,     100,  (  0, 150),  "The bed temperature to use for dissolvable HIPS filament. (C)"),
        ('hips_hotend_temp',    int,     230,  (150, 300),  "The extruder temperature to use for dissolvable HIPS filament. (C)"),
        ('hips_max_speed',      float,  30.0,  (  0, 150),  "The maximum speed when extruding dissolvable HIPS filament. (mm/s)"),
        ('nylon_bed_temp',      int,      70,  (  0, 150),  "The bed temperature to use for Nylon filament. (C)"),
        ('nylon_hotend_temp',   int,     255,  (150, 300),  "The extruder temperature to use for Nylon filament. (C)"),
        ('nylon_max_speed',     float,  75.0,  (  0, 150),  "The maximum speed when extruding Nylon filament. (mm/s)"),
        ('pc_bed_temp',         int,     130,  (  0, 150),  "The bed temperature to use for Polycarbonate filament. (C)"),
        ('pc_hotend_temp',      int,     290,  (150, 300),  "The extruder temperature to use for Polycarbonate filament. (C)"),
        ('pc_max_speed',        float,  75.0,  (  0, 150),  "The maximum speed when extruding Polycarbonate filament. (mm/s)"),
        ('pet_bed_temp',        int,      70,  (  0, 150),  "The bed temperature to use for PETG/PETT filament. (C)"),
        ('pet_hotend_temp',     int,     230,  (150, 300),  "The extruder temperature to use for PETG/PETT filament. (C)"),
        ('pet_max_speed',       float,  75.0,  (  0, 150),  "The maximum speed when extruding PETG/PETT filament. (mm/s)"),
        ('pla_bed_temp',        int,      45,  (  0, 150),  "The bed temperature to use for PLA filament. (C)"),
        ('pla_hotend_temp',     int,     205,  (150, 300),  "The extruder temperature to use for PLA filament. (C)"),
        ('pla_max_speed',       float,  75.0,  (  0, 150),  "The maximum speed when extruding PLA filament. (mm/s)"),
        ('pp_bed_temp',         int,     110,  (  0, 150),  "The bed temperature to use for Polypropylene filament. (C)"),
        ('pp_hotend_temp',      int,     250,  (150, 300),  "The extruder temperature to use for Polypropylene filament. (C)"),
        ('pp_max_speed',        float,  75.0,  (  0, 150),  "The maximum speed when extruding Polypropylene filament. (mm/s)"),
        ('pva_bed_temp',        int,      60,  (  0, 150),  "The bed temperature to use for dissolvable PVA filament. (C)"),
        ('pva_hotend_temp',     int,     220,  (150, 300),  "The extruder temperature to use for dissolvable PVA filament. (C)"),
        ('pva_max_speed',       float,  30.0,  (  0, 150),  "The maximum speed when extruding dissolvable PVA filament. (mm/s)"),
        ('softpla_bed_temp',    int,      30,  (  0, 150),  "The bed temperature to use for flexible SoftPLA filament. (C)"),
        ('softpla_hotend_temp', int,     230,  (150, 300),  "The extruder temperature to use for flexible SoftPLA filament. (C)"),
        ('softpla_max_speed',   float,  30.0,  (  0, 150),  "The maximum speed when extruding flexible SoftPLA filament. (mm/s)"),
        ('tpe_bed_temp',        int,      30,  (  0, 150),  "The bed temperature to use for flexible TPE filament. (C)"),
        ('tpe_hotend_temp',     int,     220,  (150, 300),  "The extruder temperature to use for flexible TPE filament. (C)"),
        ('tpe_max_speed',       float,  30.0,  (  0, 150),  "The maximum speed when extruding flexible TPE filament. (mm/s)"),
        ('tpu_bed_temp',        int,      50,  (  0, 150),  "The bed temperature to use for flexible TPU filament. (C)"),
        ('tpu_hotend_temp',     int,     250,  (150, 300),  "The extruder temperature to use for flexible TPU filament. (C)"),
        ('tpu_max_speed',       float,  30.0,  (  0, 150),  "The maximum speed when extruding flexible TPU filament. (mm/s)"),
    )),
    ('Machine', (
        ('bed_geometry',      list, 'Rectangular', ('Rectangular', 'Cylindrical'), "The shape of the build volume cross-section."),
        ('bed_size_x',        float,  2000, (0,2000),    "The X-axis size of the build platform bed."),
        ('bed_size_y',        float,  2000, (0,2000),    "The Y-axis size of the build platform bed."),
        ('bed_center_x',      float,  1000, (0,2000),  "The X coordinate of the center of the bed."),
        ('bed_center_y',      float,  1000, (0,2000),  "The Y coordinate of the center of the bed."),
        ('bed_temp',          int,      70, (0, 150),    "The temperature to set the heated bed to."),

        ('extruder_count',    int,      1, (1, 4),      "The number of extruders this machine has."),
        ('default_nozzle',    int,      0, (0, 4),      "The default extruder used for printing."),
        ('infill_nozzle',     int,     -1, (-1, 4),     "The extruder used for infill material.  -1 means use default nozzle."),
        ('support_nozzle',    int,     -1, (-1, 4),     "The extruder used for support material.  -1 means use default nozzle."),

        ('nozzle_0_temp',      int,     190, (150, 250),  "The temperature of the nozzle for extruder 0. (C)"),
        ('nozzle_0_filament',  float,  20.0, (1.0, 50.),  "The diameter of the filament for extruder 0. (mm)"),
        ('nozzle_0_diam',      float,  10.0, (0.1, 25.),  "The diameter of the nozzle for extruder 0. (mm)"),
        ('nozzle_0_xoff',      float,   0.0, (-100, 100), "The X positional offset for extruder 0. (mm)"),
        ('nozzle_0_yoff',      float,   0.0, (-100, 100), "The Y positional offset for extruder 0. (mm)"),
        ('nozzle_0_max_speed', float, 100.0, (0., 200.),  "The maximum speed when using extruder 0. (mm/s)"),

        ('nozzle_1_temp',      int,    190, (150, 250),  "The temperature of the nozzle for extruder 1. (C)"),
        ('nozzle_1_filament',  float, 1.75, (1.0, 3.5),  "The diameter of the filament for extruder 1. (mm)"),
        ('nozzle_1_diam',      float,  0.4, (0.1, 1.5),  "The diameter of the nozzle for extruder 1. (mm)"),
        ('nozzle_1_xoff',      float, 25.0, (-100, 100), "The X positional offset for extruder 1. (mm)"),
        ('nozzle_1_yoff',      float,  0.0, (-100, 100), "The Y positional offset for extruder 1. (mm)"),
        ('nozzle_1_max_speed', float, 75.0, (0., 200.),  "The maximum speed when using extruder 1. (mm/s)"),

        ('nozzle_2_temp',      int,    190, (150, 250),  "The temperature of the nozzle for extruder 2. (C)"),
        ('nozzle_2_filament',  float, 1.75, (1.0, 3.5),  "The diameter of the filament for extruder 2. (mm)"),
        ('nozzle_2_diam',      float,  0.4, (0.1, 1.5),  "The diameter of the nozzle for extruder 2. (mm)"),
        ('nozzle_2_xoff',      float, -25., (-100, 100), "The X positional offset for extruder 2. (mm)"),
        ('nozzle_2_yoff',      float,  0.0, (-100, 100), "The Y positional offset for extruder 2. (mm)"),
        ('nozzle_2_max_speed', float, 75.0, (0., 200.),  "The maximum speed when using extruder 2. (mm/s)"),

        ('nozzle_3_temp',      int,    190, (150, 250),  "The temperature of the nozzle for extruder 3. (C)"),
        ('nozzle_3_filament',  float, 1.75, (1.0, 3.5),  "The diameter of the filament for extruder 3. (mm)"),
        ('nozzle_3_diam',      float,  0.4, (0.1, 1.5),  "The diameter of the nozzle for extruder 3. (mm)"),
        ('nozzle_3_xoff',      float,  0.0, (-100, 100), "The X positional offset for extruder 3. (mm)"),
        ('nozzle_3_yoff',      float, 25.0, (-100, 100), "The Y positional offset for extruder 3. (mm)"),
        ('nozzle_3_max_speed', float, 75.0, (0., 200.),  "The maximum speed when using extruder 3. (mm/s)"),
    )),
])


############################################################


class Slicer(object):
    def __init__(self, models, **kwargs):
        self.models = models
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
        self.raw_layer_paths = {}
        self.last_pos = (0.0, 0.0, 0.0)
        self.last_e = 0.0
        self.last_nozl = 0
        self.total_build_time = 0.0
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
        self.center_point = (self.conf['bed_center_x'], self.conf['bed_center_y'])
        if self.infl_nozl == -1:
            self.infl_nozl = self.dflt_nozl
        if self.supp_nozl == -1:
            self.supp_nozl = self.dflt_nozl
        dflt_nozl_d = self.conf['nozzle_{0}_diam'.format(self.dflt_nozl)]
        infl_nozl_d = self.conf['nozzle_{0}_diam'.format(self.infl_nozl)]
        supp_nozl_d = self.conf['nozzle_{0}_diam'.format(self.supp_nozl)]

        self.layer_h = self.conf['layer_height']
        self.raft_layers = self.conf['raft_layers'] if self.conf['adhesion_type'] == "Raft" else 0
        self.extrusion_ratio = 1.25
        self.extrusion_width = dflt_nozl_d * self.extrusion_ratio
        self.infill_width = infl_nozl_d * self.extrusion_ratio
        self.support_width = supp_nozl_d * self.extrusion_ratio
        for model in self.models:
            model.center( (self.center_point[0], self.center_point[1], (model.points.maxz-model.points.minz)/2.0) )
            model.assign_layers(self.layer_h)
        height = max([model.points.maxz - model.points.minz for model in self.models])
        self.layers = int(height / self.layer_h)
        self.layer_zs = [
            self.layer_h * (layer + 1)
            for layer in range(self.layers + self.raft_layers)
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

        print("Pathing")
        self._slicer_task_pathing()

        print("Writing GCode to {}".format(filename))
        self._slicer_task_gcode(filename)

        print(
            "Slicing complete.  Estimated build time: {:d}h {:02d}m".format(
                int(self.total_build_time/3600),
                int((self.total_build_time%3600)/60)
            )
        )

        if showgui:
            print("Launching slice viewer")
            self._display_paths()

        # TODO: Enable multi-model loading/placement/rotation
        # TODO: Verify models fit inside build volume.
        # TODO: Interior solid infill perimeter paths
        # TODO: Pathing type prioritization
        # TODO: Optimize route paths
        # TODO: Skip retraction for short motions
        # TODO: Smooth top surfacing for non-flat surfaces
        # TODO: G-Code custom startup/shutdown/toolchange scripts.
        # TODO: G-Code flavors
        # TODO: G-Code volumetric extrusion
        # TODO: Relative E motions.
        # TODO: Better Bridging

    ############################################################

    def _slicer_task_perimeters(self):
        self.thermo.set_target(2*self.layers)
        self.layer_paths = []
        self.perimeter_paths = []
        self.skirt_bounds = []
        random_starts = self.conf['random_starts']
        self.dead_paths = []
        for layer in range(self.layers):
            self.thermo.update(layer)

            # Layer Slicing
            z = self.layer_zs[layer]
            paths = []
            layer_dead_paths = []
            for model in self.models:
                model_paths, dead_paths = model.slice_at_z(z - self.layer_h/2, self.layer_h)
                layer_dead_paths.extend(dead_paths)
                model_paths = geom.orient_paths(model_paths)
                paths = geom.union(paths, model_paths)
            self.layer_paths.append(paths)
            self.dead_paths.append(layer_dead_paths)

            # Perimeters
            perims = []
            randpos = random.random()
            for i in range(self.conf['shell_count']):
                shell = geom.offset(paths, -(i+0.5) * self.extrusion_width)
                shell = geom.close_paths(shell)
                if self.conf['random_starts']:
                    shell = [
                        ( path if i == 0 else (path[i:] + path[1:i+1]) )
                        for path in shell
                        for i in [ int(randpos * (len(path)-1)) ]
                    ]
                perims.insert(0, shell)
            self.perimeter_paths.append(perims)

            # Calculate horizontal bounding path
            if layer < self.conf['skirt_layers']:
                self.skirt_bounds = geom.union(self.skirt_bounds, paths)

        self.top_masks = []
        self.bot_masks = []
        for layer in range(self.layers):
            self.thermo.update(self.layers+layer)

            # Top and Bottom masks
            below = [] if layer < 1 else self.perimeter_paths[layer-1][0]
            perim = self.perimeter_paths[layer][0]
            above = [] if layer >= self.layers-1 else self.perimeter_paths[layer+1][0]
            self.top_masks.append(geom.diff(perim, above))
            self.bot_masks.append(geom.diff(perim, below))
        self.thermo.clear()

    def _slicer_task_support(self):
        self.thermo.set_target(5.0)

        self.support_outline = []
        self.support_infill = []
        supp_type = self.conf['support_type']
        if supp_type == 'None':
            return
        supp_ang = self.conf['overhang_angle']
        outset = self.conf['support_outset']
        layer_height = self.conf['layer_height']

        facets = [facet for model in self.models for facet in model.get_facets()]
        facet_cnt = len(facets)
        layer_facets = [[] for layer in range(self.layers)]
        for fnum, facet in enumerate(facets):
            self.thermo.update(0 + float(fnum)/facet_cnt)
            minz, maxz = facet.z_range()
            minl = int(math.ceil(minz/layer_height))
            maxl = int(math.floor(maxz/layer_height))
            for layer in range(minl, maxl):
                layer_facets[layer].append(facet)

        drop_mask = []
        drop_paths = [[] for layer in range(self.layers)]
        for layer in reversed(range(self.layers)):
            self.thermo.update(1 + float(self.layers-1-layer)/self.layers)
            adds = []
            diffs = []
            for facet in layer_facets[layer]:
                footprint = facet.get_footprint()
                if not footprint:
                    continue
                if facet.overhang_angle() < supp_ang:
                    diffs.append(footprint)
                else:
                    adds.append(footprint)
            drop_mask = geom.union(drop_mask, adds)
            drop_mask = geom.diff(drop_mask, diffs)
            drop_paths[layer] = drop_mask

        cumm_mask = []
        for layer in range(self.layers):
            self.thermo.update(2 + float(layer)/self.layers)

            # Remove areas too close to model
            mask = geom.offset(self.layer_paths[layer], outset)
            if layer > 0 and supp_type == "Everywhere":
                mask = geom.union(mask, self.layer_paths[layer-1])
            if layer < self.layers - 1:
                mask = geom.union(mask, self.layer_paths[layer+1])
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
            self.thermo.update(3 + float(layer)/self.layers)

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

    def _slicer_task_adhesion(self):
        adhesion = self.conf['adhesion_type']
        skirt_w  = self.conf['skirt_outset']
        brim_w   = self.conf['brim_width']
        raft_w   = self.conf['raft_outset']

        # Skirt
        if self.support_outline:
            skirt_mask = geom.offset(geom.union(self.skirt_bounds, self.support_outline[0]), skirt_w)
        else:
            skirt_mask = geom.offset(self.skirt_bounds, skirt_w)
        skirt = geom.offset(skirt_mask, brim_w + skirt_w + self.extrusion_width/2.0)
        self.skirt_paths = geom.close_paths(skirt)

        # Brim
        brim = []
        if adhesion == "Brim":
            rings = int(math.ceil(brim_w/self.extrusion_width))
            for i in range(rings):
                for path in geom.offset(self.layer_paths[0], (i+0.5)*self.extrusion_width):
                    brim.append(path)
        self.brim_paths = geom.close_paths(brim)

        # Raft
        raft_outline = []
        raft_infill = []
        if adhesion == "Raft":
            rings = int(math.ceil(brim_w/self.extrusion_width))
            outset = raft_w + max(
                skirt_w + self.extrusion_width,
                self.conf['raft_outset'] + self.extrusion_width
            )
            paths = geom.union(self.layer_paths[0], self.support_outline[0])
            raft_outline = geom.offset(paths, outset)
            bounds = geom.paths_bounds(raft_outline)
            mask = geom.offset(raft_outline, self.conf['infill_overlap']-self.extrusion_width)
            lines = geom.make_infill_lines(bounds, 0, 0.75, self.extrusion_width)
            raft_infill.append(geom.clip(lines, mask, subj_closed=False))
            for layer in range(self.raft_layers-1):
                base_ang = 90 * ((layer+1) % 2)
                lines = geom.make_infill_lines(bounds, base_ang, 1.0, self.extrusion_width)
                raft_infill.append(geom.clip(lines, raft_outline, subj_closed=False))
        self.raft_outline = geom.close_paths(raft_outline)
        self.raft_infill = raft_infill
        self.thermo.clear()

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
            solid_mask = geom.clip(outmask, perims[0])
            bounds = geom.paths_bounds(perims[0])

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
                mask = geom.offset(perims[0], self.conf['infill_overlap']-self.infill_width)
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

    def _slicer_task_pathing(self):
        prime_nozls = [self.conf['default_nozzle']];
        if self.conf['infill_nozzle'] != -1:
            prime_nozls.append(self.conf['infill_nozzle']);
        if self.conf['support_nozzle'] != -1:
            prime_nozls.append(self.conf['support_nozzle']);
        center_x = self.conf['bed_center_x']
        center_y = self.conf['bed_center_y']
        size_x = self.conf['bed_size_x']
        size_y = self.conf['bed_size_y']
        minx = center_x - size_x/2
        maxx = center_x + size_x/2
        miny = center_y - size_y/2
        maxy = center_y + size_y/2
        bed_geom = self.conf['bed_geometry']
        rect_bed = bed_geom == 'Rectangular'
        cyl_bed = bed_geom == 'Cylindrical'
        maxlen = (maxy-miny-20) if rect_bed else (2*math.pi*math.sqrt((size_x*size_x)/2)-20)
        reps = self.conf['prime_length'] / maxlen
        ireps = int(math.ceil(reps))
        for noznum, nozl in enumerate(prime_nozls):
            ewidth = self.extrusion_width * 1.25
            nozl_path = []
            for rep in range(ireps):
                if rect_bed:
                    x = minx + 5 + (noznum*reps+rep+1) * ewidth
                    if rep%2 == 0:
                        y1 = miny+10
                        y2 = maxy-10
                    else:
                        y1 = maxy-10
                        y2 = miny+10
                    nozl_path.append([x, y1])
                    if rep == ireps-1:
                        part = reps-math.floor(reps)
                        nozl_path.append([x, y1 + (y2-y1)*part])
                    else:
                        nozl_path.append([x, y2])
                elif cyl_bed:
                    r = maxx - 5 - (noznum*reps+rep+1) * ewidth
                    if rep == ireps-1:
                        part = float(reps) - math.floor(reps)
                    else:
                        part = 1.0
                    steps = math.floor(2.0 * math.pi * r * part / 4.0)
                    stepang = 2 * math.pi / steps
                    for i in range(int(steps)):
                        nozl_path.append( [r*math.cos(i*stepang), r*math.sin(i*stepang)] )
            self._add_raw_layer_paths(0, [nozl_path], ewidth, noznum)

        if self.brim_paths:
            paths = geom.close_paths(self.brim_paths)
            self._add_raw_layer_paths(0, paths, self.support_width, self.supp_nozl)
        if self.raft_outline:
            outline = geom.close_paths(self.raft_outline)
            self._add_raw_layer_paths(0, outline, self.support_width, self.supp_nozl)
        if self.raft_infill:
            for layer in range(self.raft_layers):
                paths = self.raft_infill[layer]
                self._add_raw_layer_paths(layer, paths, self.support_width, self.supp_nozl)

        for slicenum in range(len(self.perimeter_paths)):
            self.thermo.update(slicenum)
            layer = self.raft_layers + slicenum

            if self.skirt_paths:
                paths = geom.close_paths(self.skirt_paths)
                if layer < self.conf['skirt_layers'] + self.raft_layers:
                    self._add_raw_layer_paths(layer, paths, self.support_width, self.supp_nozl)

            if slicenum < len(self.support_outline):
                outline = geom.close_paths(self.support_outline[slicenum])
                self._add_raw_layer_paths(layer, outline, self.support_width, self.supp_nozl)
                self._add_raw_layer_paths(layer, self.support_infill[slicenum], self.support_width, self.supp_nozl)

            for paths in self.perimeter_paths[slicenum]:
                paths = geom.close_paths(paths)
                self._add_raw_layer_paths(layer, paths, self.extrusion_width, self.dflt_nozl)
            self._add_raw_layer_paths(layer, self.solid_infill[slicenum], self.extrusion_width, self.dflt_nozl)

            self._add_raw_layer_paths(layer, self.sparse_infill[slicenum], self.infill_width, self.infl_nozl)
        self.thermo.clear()

    def _slicer_task_gcode(self, filename):
        self.thermo.set_target(self.layers)

        total_layers = self.layers + self.raft_layers
        with open(filename, "w") as f:
            f.write(";FLAVOR:Marlin\n")
            f.write(";Layer height: {:.2f}\n".format(self.conf['layer_height']))
            f.write("M82 ;absolute extrusion mode\n")
            f.write("G21 ;metric values\n")
            f.write("G90 ;absolute positioning\n")
            f.write("M107 ;Fan off\n")
            if self.conf['bed_temp'] > 0:
                f.write("M140 S{:d} ;set bed temp\n".format(self.conf['bed_temp']))
                f.write("M190 S{:d} ;wait for bed temp\n".format(self.conf['bed_temp']))
            f.write("M104 S{:d} ;set extruder0 temp\n".format(self.conf['nozzle_0_temp']))
            f.write("M109 S{:d} ;wait for extruder0 temp\n".format(self.conf['nozzle_0_temp']))
            f.write("G28 X0 Y0 ;auto-home all axes\n")
            f.write("G28 Z0 ;auto-home all axes\n")
            f.write("G1 Z15 F6000 ;raise extruder\n")
            f.write("G92 E0 ;Zero extruder\n")
            f.write("M117 Printing...\n")
            f.write(";LAYER_COUNT:{}\n".format(total_layers))

            self.thermo.set_target(total_layers)
            for layer in range(total_layers):
                self.thermo.update(layer)
                f.write(";LAYER:{}\n".format(layer))
                for nozl in range(4):
                    if layer in self.raw_layer_paths and self.raw_layer_paths[layer][nozl] != []:
                        f.write("( Nozzle {} )\n".format(nozl))
                        for paths, width in self.raw_layer_paths[layer][nozl]:
                            for line in self._paths_gcode(paths, width, nozl, self.layer_zs[layer]):
                                f.write(line)
            self.thermo.clear()

    ############################################################

    def _vdist(self,a,b):
        delta = [x-y for x,y in zip(a,b)]
        dist = math.sqrt(sum([float(x)*float(x) for x in delta]))
        return dist

    def _add_raw_layer_paths(self, layer, paths, width, nozl, do_not_cross=[]):
        maxdist = 2.0
        joined = []
        if paths:
            path = paths.pop(0)
            while paths:
                mindist = 1e9
                minidx = None
                enda = False
                endb = False
                dists = [
                    [i, self._vdist(path[a], paths[i][b]), a==-1, b==-1]
                    for a in [0,-1]
                    for b in [0,-1]
                    for i in range(len(paths))
                ]
                for i, dist, ea, eb in dists:
                    if dist < mindist:
                        minidx, mindist, enda, endb = (i, dist, ea, eb)
                if mindist <= maxdist:
                    path2 = paths.pop(minidx)
                    if enda:
                        path = path + (list(reversed(path2)) if endb else path2)
                    else:
                        path = (path2 if endb else list(reversed(path2))) + path
                else:
                    if minidx is not None:
                        if enda == endb:
                            paths.insert(0, list(reversed(paths.pop(minidx))))
                        else:
                            paths.insert(0, paths.pop(minidx))
                    joined.append(path)
                    path = paths.pop(0)
            joined.append(path)
        if layer not in self.raw_layer_paths:
            self.raw_layer_paths[layer] = [[] for i in range(4)]
        self.raw_layer_paths[layer][nozl].append( (joined, width) )

    def _tool_change_gcode(self, newnozl):
        retract_ext_dist = self.conf['retract_extruder']
        retract_speed = self.conf['retract_speed']
        if self.last_nozl == newnozl:
            return []
        gcode_lines = []
        gcode_lines.append("G1 E{e:.3f} F{f:g}\n".format(e=-retract_ext_dist, f=retract_speed*60.0))
        gcode_lines.append("T{t:d}\n".format(t=newnozl))
        gcode_lines.append("G1 E{e:.3f} F{f:g}\n".format(e=retract_ext_dist, f=retract_speed*60.0))
        return gcode_lines

    def _paths_gcode(self, paths, ewidth, nozl, z):
        fil_diam = self.conf['nozzle_{0:d}_filament'.format(nozl)]
        nozl_diam = self.conf['nozzle_{0:d}_filament'.format(nozl)]
        max_speed = self.conf['nozzle_{0:d}_max_speed'.format(nozl)]
        layer_height = self.conf['layer_height']
        retract_dist = self.conf['retract_dist']
        retract_speed = self.conf['retract_speed']
        retract_lift = self.conf['retract_lift']
        feed_rate = self.conf['feed_rate']
        travel_rate_xy = self.conf['travel_rate_xy']
        travel_rate_z = self.conf['travel_rate_z']
        ewidth = nozl_diam * self.extrusion_ratio
        xsect = math.pi * ewidth/2 * layer_height/2
        fil_xsect = math.pi * fil_diam/2 * fil_diam/2
        gcode_lines = []
        for line in self._tool_change_gcode(nozl):
            gcode_lines.append(line)
        for path in paths:
            ox, oy = path[0][0:2]
            if retract_lift > 0 or self.last_pos[2] != z:
                self.total_build_time += abs(retract_lift) / travel_rate_z
                gcode_lines.append("G1 Z{z:.2f} F{f:g}\n".format(z=z+retract_lift, f=travel_rate_z*60.0))
            dist = math.hypot(self.last_pos[1]-oy, self.last_pos[0]-ox)
            self.total_build_time += dist / travel_rate_xy
            gcode_lines.append("G0 X{x:.2f} Y{y:.2f} F{f:g}\n".format(x=ox, y=oy, f=travel_rate_xy*60.0))
            if retract_lift > 0:
                self.total_build_time += abs(retract_lift) / travel_rate_z
                gcode_lines.append("G1 Z{z:.2f} F{f:g}\n".format(z=z, f=travel_rate_z*60.0))
            if retract_dist > 0:
                self.total_build_time += abs(retract_dist) / retract_speed
                gcode_lines.append("G1 E{e:.3f} F{f:g}\n".format(e=self.last_e+retract_dist, f=retract_speed*60.0))
                self.last_e += retract_dist
            for x, y in path[1:]:
                dist = math.hypot(y-oy, x-ox)
                fil_dist = dist * xsect / fil_xsect
                speed = min(feed_rate, max_speed) * 60.0
                self.total_build_time += dist / feed_rate
                self.last_e += fil_dist
                gcode_lines.append("G1 X{x:.2f} Y{y:.2f} E{e:.3f} F{f:g}\n".format(x=x, y=y, e=self.last_e, f=speed))
                self.last_pos = (x, y, z)
                ox, oy = x, y
            if retract_dist > 0:
                self.total_build_time += abs(retract_dist) / retract_speed
                gcode_lines.append("G1 E{e:.3f} F{f:g}\n".format(e=self.last_e-retract_dist, f=retract_speed*60.0))
                self.last_e -= retract_dist
        return gcode_lines

    ############################################################

    def _display_paths(self):
        try:  # Python 2
            from Tkinter import (Tk, Canvas, Label, Frame, Scrollbar, mainloop)
            from ttk import Progressbar, Style
        except ImportError:  # Python 3
            from tkinter import (Tk, Canvas, Label, Frame, Scrollbar, mainloop)
            from tkinter.ttk import Progressbar, Style
        self.layer = 0
        self.mag = 1.0
        self.master = Tk()
        self.master.title("Mandoline - Layer Paths")
        self.info_fr = Frame(self.master, bd=2, relief="flat", bg="#ccc")
        self.info_fr.pack(side="top", fill="x", expand=False)
        self.zoom_lbl = Label(self.info_fr, anchor="w", width=16, bg="#ccc")
        self.zoom_lbl.pack(side="left")
        self.layer_lbl = Label(self.info_fr, anchor="w", width=16, bg="#ccc")
        self.layer_lbl.pack(side="left")
        self.zed_lbl = Label(self.info_fr, anchor="w", width=16, bg="#ccc")
        self.zed_lbl.pack(side="left")
        self.progbar = Progressbar(self.info_fr, orient="horizontal", length=200, value=0, maximum=100, mode="determinate")
        self.progbar.pack(side="left", fill="y", pady=5)
        st = Style()
        st.theme_use("default")
        st.configure("bar.Horizontal.TProgressbar", troughcolor="white", foreground="blue", background="white")
        self.fr = Frame(self.master)
        self.fr.pack(fill="both", expand=True)
        self.fr.grid_rowconfigure(0, weight=1)
        self.fr.grid_columnconfigure(0, weight=1)
        self.canvas = Canvas(self.fr, width=1400, height=1000, scrollregion=(0,0,1000,1000))
        self.hbar = Scrollbar(self.fr, orient="horizontal", command=self.canvas.xview)
        self.vbar = Scrollbar(self.fr, orient="vertical", command=self.canvas.yview)
        self.canvas.config(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.focus()
        self.canvas.bind_all('<Shift-MouseWheel>', lambda event: self.canvas.xview_scroll(int(-abs(event.delta)/event.delta), "units"))
        self.canvas.bind_all('<MouseWheel>', lambda event: self.canvas.yview_scroll(int(-abs(event.delta)/event.delta), "units"))
        self.canvas.bind_all('<Control-MouseWheel>', lambda event: self._zoom(incdec=int(abs(event.delta)/event.delta)))
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
        size_x = self.conf['bed_size_x']
        size_y = self.conf['bed_size_y']
        cx = self.conf['bed_center_x']
        cy = self.conf['bed_center_y']
        neww = (cx-700/self.mag)/size_x
        newh = (cy-500/self.mag)/size_y
        self.canvas.xview("moveto", neww)
        self.canvas.yview("moveto", newh)
        if platform.system() == "Darwin":
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
        mainloop()

    def _zoom(self, incdec=0, val=None):
        self.master.update()
        winx = self.canvas.winfo_width()
        winy = self.canvas.winfo_height()
        cx = self.canvas.canvasx(int(winx/2))/self.mag
        cy = self.canvas.canvasy(int(winy/2))/self.mag
        size_x = self.conf['bed_size_x']
        size_y = self.conf['bed_size_y']
        if val is None:
            self.mag = max(1, self.mag+incdec)
        else:
            self.mag = val
        self._redraw_paths()
        neww = (cx-winx/2/self.mag)/size_x
        newh = (cy-winy/2/self.mag)/size_y
        self.canvas.xview("moveto", neww)
        self.canvas.yview("moveto", newh)

    def _redraw_paths(self, incdec=0):
        self.layer = min(max(0, self.layer + incdec), len(self.perimeter_paths)-1+self.raft_layers)
        layernum = self.layer
        layers = self.raft_layers + self.layers
        center_x = self.conf['bed_center_x']
        center_y = self.conf['bed_center_y']
        size_x = self.conf['bed_size_x']
        size_y = self.conf['bed_size_y']
        minx = (center_x - size_x/2) * self.mag
        maxx = (center_x + size_x/2) * self.mag
        miny = (center_y - size_y/2) * self.mag
        maxy = (center_y + size_y/2) * self.mag
        self.zoom_lbl.config(text="Zoom: {}%".format(int(self.mag*100/10.0)))
        self.layer_lbl.config(text="Layer: {}/{}".format(layernum, layers-1))
        self.zed_lbl.config(text="Z: {:.3f}".format(self.layer_zs[layernum]))
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(minx,miny,maxx,maxy))
        self.progbar['value'] = layernum
        self.progbar['maximum'] = layers-1

        grid_colors = ["#ccf", "#eef"]
        for x in range(int(size_x/10)):
            for y in range(int(size_y/10)):
                rect = [val*10*self.mag for val in (x, y, x+1, y+1)]
                self.canvas.create_rectangle(rect, fill=grid_colors[(x+y)%2])
        # nozl_colors = [
        #     ["#070", "#0c0", "#0f0", "#7f7"],
        #     ["#770", "#aa0", "#dd0", "#ff0"],
        #     ["#007", "#00c", "#00f", "#77f"],
        #     ["#700", "#c00", "#f00", "#f77"],
        # ]
        nozl_colors = [ ["#0c0"], ["#aa0"], ["#00c"], ["#c00"] ]
        for nozl in range(4):
            if layernum in self.raw_layer_paths and self.raw_layer_paths[layernum][nozl]:
                for paths, width in self.raw_layer_paths[layernum][nozl]:
                    self._draw_line(paths, colors=nozl_colors[nozl], ewidth=width)
        self._draw_line(self.layer_paths[self.layer], colors=["#cc0"], ewidth=self.extrusion_width/8.0)
        self._draw_line(self.dead_paths[self.layer], colors=["red"], ewidth=self.extrusion_width/8.0)

    def _draw_line(self, paths, offset=0, colors=["red", "green", "blue"], ewidth=0.5):
        center_x = self.conf['bed_center_x']
        center_y = self.conf['bed_center_y']
        size_x = self.conf['bed_size_x']
        size_y = self.conf['bed_size_y']
        minx = (center_x - size_x/2) * self.mag
        maxx = (center_x + size_x/2) * self.mag
        miny = (center_y - size_y/2) * self.mag
        maxy = (center_y + size_y/2) * self.mag
        for pathnum, path in enumerate(paths):
            path = [(x*self.mag, maxy-y*self.mag) for x, y in path]
            color = colors[(pathnum + offset) % len(colors)]
            self.canvas.create_line(path, fill=color, width=self.mag*ewidth, capstyle="round", joinstyle="round")
            self.canvas.create_line([path[0],path[0]], fill="blue", width=self.mag*ewidth, capstyle="round", joinstyle="round")
            self.canvas.create_line([path[-1],path[-1]], fill="cyan", width=self.mag*ewidth, capstyle="round", joinstyle="round")


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
