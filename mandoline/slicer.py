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
        ('extruder_count',    int,      1, (1, 4),     "The number of extruders this machine has."),
        ('default_nozzle',    int,      0, (0, 7),     "The default extruder used for printing."),
        ('infill_nozzle',     int,     -1, (-1, 7),    "The extruder used for infill material.  -1 means use default nozzle."),
        ('support_nozzle',    int,     -1, (-1, 7),    "The extruder used for support material.  -1 means use default nozzle."),

        ('nozzle_0_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 0. (C)"),
        ('nozzle_0_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 0. (mm)"),
        ('nozzle_0_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 0. (mm)"),
        ('nozzle_0_xoff',     float,  0.0, (-100., 100.), "The X positional offset for extruder 0. (mm)"),
        ('nozzle_0_yoff',     float,  0.0, (-100., 100.), "The Y positional offset for extruder 0. (mm)"),
        ('nozzle_0_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 0. (mm^3/s)"),

        ('nozzle_1_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 1. (C)"),
        ('nozzle_1_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 1. (mm)"),
        ('nozzle_1_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 1. (mm)"),
        ('nozzle_1_xoff',     float, 25.0, (-100., 100.), "The X positional offset for extruder 1. (mm)"),
        ('nozzle_1_yoff',     float,  0.0, (-100., 100.), "The Y positional offset for extruder 1. (mm)"),
        ('nozzle_1_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 1. (mm^3/s)"),

        ('nozzle_2_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 2. (C)"),
        ('nozzle_2_filament', float, 1.75, (1.0, 3.5), "The diameter of the filament for extruder 2. (mm)"),
        ('nozzle_2_diam',     float,  0.4, (0.1, 1.5), "The diameter of the nozzle for extruder 2. (mm)"),
        ('nozzle_2_xoff',     float, -25., (-100., 100.), "The X positional offset for extruder 2. (mm)"),
        ('nozzle_2_yoff',     float,  0.0, (-100., 100.), "The Y positional offset for extruder 2. (mm)"),
        ('nozzle_2_max_rate', float, 50.0, (0., 100.), "The maximum extrusion speed for extruder 2. (mm^3/s)"),

        ('nozzle_3_temp',     float,  0.4, (0.1, 1.5), "The temperature of the nozzle for extruder 3. (C)"),
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
        if typ is bool:
            if valstr in ["True", "False"]:
                self.conf[key] = valstr == "True"
            else:
                print("Ignoring bad boolean configuration value: {}={}".format(key,valstr))
                print("Value should be either True or False")
        elif typ is int:
            if int(valstr) >= rng[0] and int(valstr) <= rng[1]:
                self.conf[key] = int(valstr)
            else:
                print("Ignoring bad integer configuration value: {}={}".format(key,valstr))
                print("Value should be between {} and {}, inclusive.".format(*rng))
        elif typ is float:
            if float(valstr) >= rng[0] and float(valstr) <= rng[1]:
                self.conf[key] = float(valstr)
            else:
                print("Ignoring bad float configuration value: {}={}".format(key,valstr))
                print("Value should be between {} and {}, inclusive.".format(*rng))
        elif typ is list:
            if valstr in rng:
                self.conf[key] = str(valstr)
            else:
                print("Ignoring bad configuration value: {}={}".format(key,valstr))
                print("Valid options are: {}".format(", ".join(rng)))

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
        layer_h = self.conf['layer_height']
        dflt_nozl = self.conf['default_nozzle']
        infl_nozl = self.conf['infill_nozzle']
        supp_nozl = self.conf['support_nozzle']
        ptcache = self.model.points
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
        layer_cnt = int(height / layer_h)
        self.model.assign_layers(layer_h)
        self.layer_zs = [
            self.model.points.minz + layer_h * (layer + 1)
            for layer in range(layer_cnt)
        ]
        thermo = TextThermometer(layer_cnt)

        # print('<tkcad formatversion="1.1" units="inches" showfractions="YES" material="Aluminum">', file=sys.stderr)
        print("Stage 1: Perimeters")
        (
            self.layer_paths,
            self.overhang_masks,
            self.perimeter_paths
        ) = zip(
            *list(
                map(
                    Slicer._slicer_task_1,
                    self.layer_zs,
                    range(layer_cnt),
                    [thermo] * layer_cnt,
                    [self.extrusion_width] * layer_cnt,
                    [self.support_width] * layer_cnt,
                    [layer_h] * layer_cnt,
                    [self.conf] * layer_cnt,
                    [self.model] * layer_cnt
                )
            )
        )
        thermo.clear()

        print("Stage 2: Generate Masks")
        overhang_drops = Slicer._slicer_task_2a(
            self.conf,
            self.overhang_masks,
            self.layer_paths
        )

        top_masks, bot_masks = zip(
            *list(
                map(
                    Slicer._slicer_task_2b,
                    range(layer_cnt),
                    [thermo] * layer_cnt,
                    [([] if i < 1 else self.perimeter_paths[i-1][-1]) for i in range(layer_cnt)],
                    [p[-1] for p in self.perimeter_paths],
                    [([] if i >= layer_cnt-1 else self.perimeter_paths[i+1][-1]) for i in range(layer_cnt)]
                )
            )
        )
        thermo.clear()

        print("Stage 3: Support & Raft")
        (
            self.support_outline,
            self.support_infill
        ) = zip(
            *list(
                map(
                    Slicer._slicer_task_3b,
                    range(layer_cnt),
                    [thermo] * layer_cnt,
                    [self.conf] * layer_cnt,
                    [self.support_width] * layer_cnt,
                    overhang_drops
                )
            )
        )
        del overhang_drops
        thermo.clear()

        print("Stage 4: Layer Path Generation")
        (
            self.raft_outline,
            self.raft_infill,
            self.brim_paths,
            self.skirt_paths,
            self.priming_paths
        ) = self._slicer_task_4a(
            self.support_width,
            self.conf,
            self.layer_paths[0],
            self.support_outline[0]
        )

        top_cnt = self.conf['top_layers']
        bot_cnt = self.conf['bottom_layers']
        thermo = TextThermometer(layer_cnt)
        (
            self.solid_infill,
            self.sparse_infill
        ) = zip(
            *list(
                map(
                    self._slicer_task_4b,
                    range(layer_cnt),
                    [thermo] * layer_cnt,
                    [self.extrusion_width] * layer_cnt,
                    [self.infill_width] * layer_cnt,
                    [self.conf] * layer_cnt,
                    [top_masks[i : i+top_cnt] for i in range(layer_cnt)],
                    [bot_masks[max(0, i-bot_cnt+1) : i+1] for i in range(layer_cnt)],
                    self.perimeter_paths
                )
            )
        )
        thermo.clear()

        del top_masks
        del bot_masks

        raft_layers = len(self.raft_infill)
        for i in range(raft_layers):
            self.layer_zs.append(self.layer_zs[-1]+self.conf[layer_height])

        print("Gcode Generation")
        with open(filename, "w") as f:
            f.write("( raft_outline )\n")
            outline = geom.close_paths(self.raft_outline)
            for line in self._paths_gcode(outline, self.support_width, supp_nozl, self.layer_zs[0]):
                f.write(line)
            f.write("( raft_infill )\n")
            for layer, layer_paths in enumerate(self.raft_infill):
                for line in self._paths_gcode(layer_paths, self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            layer = raft_layers
            if self.priming_paths:
                f.write("( priming )\n")
                paths = geom.close_paths(self.priming_paths)
                for line in self._paths_gcode(paths, self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            if self.skirt_paths:
                f.write("( skirt )\n")
                for line in self._paths_gcode(self.skirt_paths, self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            if self.brim_paths:
                f.write("( brim )\n")
                paths = self.brim_paths
                for line in self._paths_gcode(paths+paths[0], self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

            for slicenum in range(len(self.perimeter_paths)):
                layer = raft_layers + slicenum
                thermo.update(slicenum)
                outline = geom.close_paths(self.support_outline[slicenum])
                f.write("( support outline )\n")
                for line in self._paths_gcode(outline, self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)
                f.write("( support infill )\n")
                for line in self._paths_gcode(self.support_infill[slicenum], self.support_width, supp_nozl, self.layer_zs[layer]):
                    f.write(line)

                f.write("( perimeters )\n")
                for paths in reversed(self.perimeter_paths[slicenum]):
                    paths = geom.close_paths(paths)
                    for line in self._paths_gcode(paths, self.extrusion_width, dflt_nozl, self.layer_zs[layer]):
                        f.write(line)
                f.write("( solid fill )\n")
                for line in self._paths_gcode(self.solid_infill[slicenum], self.extrusion_width, dflt_nozl, self.layer_zs[layer]):
                    f.write(line)

                f.write("( sparse infill )\n")
                for line in self._paths_gcode(self.sparse_infill[slicenum], self.infill_width, infl_nozl, self.layer_zs[layer]):
                    f.write(line)
            thermo.clear()
        print("Slicing complete")

        # print('</tkcad>', file=sys.stderr)
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

    # cut: model
    #   layer_paths
    # overhang_mask: model
    #   overhang_masks
    # perimeter: layer_paths
    #   perimeter_paths
    # brim: layer_paths[0]
    #   brim_paths
    # skirt: layer_paths[0]
    #   skirt_paths
    #   priming_paths

    # overhang_drop: layer_paths[*] overhang_masks[*]
    #   overhang_drops
    # top_bottom_mask: perimeter_paths[*]
    #   top_masks
    #   bot_masks

    # support: overhang_drops[*]
    #    support_outline
    #    support_infill
    # raft: support_outline[0] layer_paths[0]
    #   raft_outline
    #   raft_infill

    # solid_mask: top_masks[*] bot_masks[*]
    #   solid_masks
    # solid_infill: solid_masks
    #   solid_infill
    # sparse_infill: perimeter_paths solid_masks
    #   sparse_infill

    ############################################################

    @staticmethod
    def _slicer_task_1(z, layer, thermo, ewidth, suppwidth, layer_h, conf, model):
        thermo.update(layer)

        # Layer Slicing
        paths = model.slice_at_z(z - layer_h/2, layer_h)
        paths = geom.orient_paths(paths)
        paths = geom.union(paths, [])

        # Overhang Masks
        supp_ang = conf['overhang_angle']
        tris = model.get_overhang_footprint_triangles(ang=supp_ang, z=z)
        overhangs = geom.diff(geom.union(tris, []), paths)

        # Perimeters
        perims = []
        for i in range(conf['shell_count']):
            shell = geom.offset(paths, -(i+0.5) * ewidth)
            shell = geom.close_paths(shell)
            perims.append(shell)

        return paths, overhangs, perims

    @staticmethod
    def _slicer_task_2a(conf, overhangs, layer_paths):
        # Overhang Drops
        outset = conf['support_outset']
        supp_type = conf['support_type']
        if supp_type == 'None':
            return []
        layer_drops = []
        drop_paths = []
        for layer in reversed(range(len(overhangs))):
            drop_paths = geom.union(drop_paths, overhangs[layer])
            layer_mask = geom.offset(layer_paths[layer], outset)
            layer_drops.insert(0, geom.diff(drop_paths, layer_mask))
        if supp_type == 'External':
            return layer_drops
        out_paths = []
        mask_paths = []
        for layer, drop_paths in enumerate(layer_drops):
            layer_mask = geom.offset(layer_paths[layer], outset)
            mask_paths = geom.union(mask_paths, layer_mask)
            drop_paths = geom.diff(drop_paths, mask_paths)
            out_paths.append(drop_paths)
        return out_paths

    @staticmethod
    def _slicer_task_2b(layer, thermo, below, perim, above):
        thermo.update(layer)
        # Top and Bottom masks
        top_mask = geom.diff(perim, above)
        bot_mask = geom.diff(perim, below)
        return top_mask, bot_mask

    @staticmethod
    def _slicer_task_3b(layer, thermo, conf, ewidth, overhangs):
        thermo.update(layer)
        # Support
        outline = []
        infill = []
        density = conf['support_density'] / 100.0
        if density > 0.0:
            outline = geom.offset(overhangs, -ewidth/2.0)
            outline = geom.close_paths(outline)
            mask = geom.offset(outline, conf['infill_overlap']-ewidth)
            bounds = geom.paths_bounds(mask)
            lines = geom.make_infill_lines(bounds, 0, density, ewidth)
            infill = geom.clip(lines, mask, subj_closed=False)
        return outline, infill

    @staticmethod
    def _slicer_task_4a(ewidth, conf, layer_paths, supp_outline):
        # Raft
        raft_outline = []
        raft_infill = []
        if conf['adhesion_type'] == "Raft":
            rings = int(math.ceil(conf['brim_width']/ewidth))
            outset = min(conf['skirt_outset']+ewidth*conf['skirt_loops'], conf['raft_outset'])
            paths = geom.union(layer_paths, supp_outline)
            raft_outline = geom.offset(paths, outset)
            bounds = geom.paths_bounds(raft_outline)
            mask = geom.offset(raft_outline, conf['infill_overlap']-ewidth)
            lines = geom.make_infill_lines(bounds, 0, 0.75, ewidth)
            raft_infill.append(geom.clip(lines, mask, subj_closed=False))
            for layer in range(conf['raft_layers']-1):
                base_ang = 90 * ((layer+1) % 2)
                lines = geom.make_infill_lines(bounds, base_ang, 1.0, ewidth)
                raft_infill.append(geom.clip(lines, raft_outline, subj_closed=False))

        # Brim
        brim = []
        adhesion = conf['adhesion_type']
        brim_w = conf['brim_width']
        if adhesion == "Brim":
            rings = int(math.ceil(brim_w/ewidth))
            for i in range(rings):
                brim.append(geom.offset(layer_paths, (i+0.5)*ewidth))

        # Skirt
        skirt = []
        priming = []
        skirt_w = conf['skirt_outset']
        minloops = conf['skirt_loops']
        minlen = conf['skirt_min_len']
        skirt = geom.offset(layer_paths, brim_w + skirt_w + ewidth/2.0)
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
            priming.append(geom.offset(skirt, (i+1)*ewidth))

        return (
            geom.close_paths(raft_outline),
            raft_infill,
            geom.close_paths(brim),
            geom.close_paths(skirt),
            geom.close_paths(priming)
        )

    @staticmethod
    def _slicer_task_4b(layer, thermo, ewidth, iwidth, conf, top_masks, bot_masks, perims):
        # Solid Mask
        thermo.update(layer)
        outmask = []
        for mask in top_masks:
            outmask = geom.union(outmask, geom.close_paths(mask))
        for mask in bot_masks:
            outmask = geom.union(outmask, geom.close_paths(mask))
        solid_mask = geom.clip(outmask, perims[-1])
        bounds = geom.paths_bounds(outmask)

        # Solid Infill
        solid_infill = []
        base_ang = 45 if layer % 2 == 0 else -45
        solid_mask = geom.offset(solid_mask, conf['infill_overlap']-ewidth)
        lines = geom.make_infill_lines(bounds, base_ang, 1.0, ewidth)
        for line in lines:
            lines = [line]
            lines = geom.clip(lines, solid_mask, subj_closed=False)
            solid_infill.extend(lines)

        # Sparse Infill
        sparse_infill = []
        infill_type = conf['infill_type']
        density = conf['infill_density'] / 100.0
        if density > 0.0:
            if density >= 0.99:
                infill_type = "Lines"
            mask = geom.offset(perims[-1], conf['infill_overlap']-iwidth)
            mask = geom.diff(mask, solid_mask)
            if infill_type == "Lines":
                base_ang = 90 * (layer % 2) + 45
                lines = geom.make_infill_lines(bounds, base_ang, density, iwidth)
            elif infill_type == "Triangles":
                base_ang = 60 * (layer % 3)
                lines = geom.make_infill_triangles(bounds, base_ang, density, iwidth)
            elif infill_type == "Grid":
                base_ang = 90 * (layer % 2) + 45
                lines = geom.make_infill_grid(bounds, base_ang, density, iwidth)
            elif infill_type == "Hexagons":
                base_ang = 120 * (layer % 3)
                lines = geom.make_infill_hexagons(bounds, base_ang, density, iwidth)
            else:
                lines = []
            for line in lines:
                lines = [line]
                lines = geom.clip(lines, mask, subj_closed=False)
                sparse_infill.extend(lines)
        return solid_infill, sparse_infill

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
        self.canvas.delete("all")
        self.canvas.create_text((30, 550), anchor="nw", text="Layer {layer}\nZ: {z:.2f}\nZoom: {zoom:.1f}%".format(layer=self.layer, z=self.layer_zs[self.layer], zoom=self.mag*100/5.0))

        colors = ["#700", "#c00", "#f00", "#f77"]
        if self.layer == 0:
            self._draw_line(self.priming_paths, colors=colors, ewidth=self.support_width)
            self._draw_line(self.brim_paths, colors=colors, ewidth=self.support_width)
            self._draw_line(self.skirt_paths, colors=colors, ewidth=self.support_width)
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
            self.canvas.create_line(path, fill=color, width=self.mag*ewidth, capstyle="round", joinstyle="round")


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
