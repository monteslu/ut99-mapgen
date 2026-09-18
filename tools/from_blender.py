"""
from_blender.py - compile a .t3d exported from Blender into a playable .unr.

    python3 tools/from_blender.py scene.t3d DM-MyMap [--shot]

The .t3d only carries geometry, so this adds what a level needs to actually
run: PlayerStarts and a light grid, both derived from the rooms themselves.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build import Map, screenshot, stats, tour     # noqa: E402
from t3d import Brush, Poly                        # noqa: E402


def parse_t3d(path):
    """Read brushes back out of a .t3d. Vertices stay in brush-local space and
    the Location is kept separate, which is what UE1 expects."""
    text = open(path, encoding="latin-1", errors="replace").read()
    brushes = []
    for i, actor in enumerate(text.split("Begin Actor")[1:]):
        csg = "CSG_Add" if "CSG_Add" in actor else "CSG_Subtract"
        loc = (0.0, 0.0, 0.0)
        m = re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)",
                      actor)
        if m:
            loc = tuple(float(g) for g in m.groups())

        polys = []
        for chunk in actor.split("Begin Polygon")[1:]:
            tex = ""
            tm = re.match(r"\s*Texture=([^\s]+)", chunk)
            if tm:
                tex = tm.group(1)
            nums = lambda kw: [tuple(float(g) for g in mm.groups())
                               for mm in re.finditer(
                                   kw + r"\s+([-+\d.]+),([-+\d.]+),([-+\d.]+)",
                                   chunk)]
            verts = nums("Vertex")
            normal = (nums("Normal") or [(0, 0, 1)])[0]
            u = (nums("TextureU") or [(1, 0, 0)])[0]
            v = (nums("TextureV") or [(0, 1, 0)])[0]
            if len(verts) >= 3:
                polys.append(Poly(verts=verts, normal=normal, texture_u=u,
                                  texture_v=v, texture=tex))
        if polys:
            brushes.append(Brush(polys=polys, name=f"BBrush{i}", csg=csg,
                                 location=loc))
    return brushes


def bounds(brush):
    xs = [v[0] for p in brush.polys for v in p.verts]
    ys = [v[1] for p in brush.polys for v in p.verts]
    zs = [v[2] for p in brush.polys for v in p.verts]
    ox, oy, oz = brush.location
    return (min(xs) + ox, min(ys) + oy, min(zs) + oz,
            max(xs) + ox, max(ys) + oy, max(zs) + oz)


def populate(m, light_step=640, brightness=170, radius=72):
    """Add starts and lights to every carved room, sized from the room itself.

    Rooms are lit on a grid rather than from one central lamp: a single light
    in a 2000-unit hall leaves most of it black.
    """
    rooms = [b for b in m.brushes if b.csg != "CSG_Add"]
    adds = [b for b in m.brushes if b.csg == "CSG_Add"]
    starts = 0

    for br in rooms:
        x0, y0, z0, x1, y1, z1 = bounds(br)
        if min(x1 - x0, y1 - y0) < 256 or (z1 - z0) < 160:
            continue                       # too tight to stand in

        # Lights on a grid, hung just under the ceiling.
        lz = z1 - 96
        x = x0 + light_step / 2
        while x < x1:
            y = y0 + light_step / 2
            while y < y1:
                m.actor("Light", int(x), int(y), int(lz),
                        LightBrightness=brightness, LightRadius=radius)
                y += light_step
            x += light_step

        # Up to four starts per room, inset from the walls and clear of solids.
        inset = 160
        for sx, sy in ((x0 + inset, y0 + inset), (x1 - inset, y1 - inset),
                       (x0 + inset, y1 - inset), (x1 - inset, y0 + inset)):
            if x1 - x0 < 2 * inset or y1 - y0 < 2 * inset:
                continue
            z = z0 + m.START_HEIGHT + 8
            if any(_hits(a, sx, sy, z) for a in adds):
                continue
            m.player_start(int(sx), int(sy), floor_z=int(z0))
            starts += 1
    return starts


def _hits(brush, x, y, z, r=46, h=50):
    x0, y0, z0, x1, y1, z1 = bounds(brush)
    return (x - r < x1 and x + r > x0 and y - r < y1 and y + r > y0 and
            z - h < z1 and z + h > z0)


def compile_map(t3d_path, name, shot=False):
    m = Map(name)
    for br in parse_t3d(t3d_path):
        m.add(br)
    if not m.brushes:
        raise SystemExit(f"{t3d_path}: no brushes found")

    starts = populate(m)
    if not starts:
        raise SystemExit("no room was big enough for a PlayerStart")

    unr, log = m.build()
    print("built:", unr)
    for line in stats(log):
        print("  ", line)
    print(f"  brushes {len(m.brushes)}  starts {starts}  lights "
          f"{sum(1 for a in m.actors if a[0] == 'Light')}")
    if shot:
        print("shots:", *tour(name, shots=2), sep="\n  ")
    return unr


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__.strip())
    compile_map(args[0], args[1], shot="--shot" in sys.argv)
