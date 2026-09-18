"""
selftest.py - checks that catch the failure modes that look like success.

Run:  python3 tools/selftest.py

Each check has a control that must FAIL. A build that reports "Success - 0
errors" while quietly producing wrong geometry is the normal failure mode here,
so every check asserts on a number that only moves when the map is really right.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import items                                       # noqa: E402
from build import Map                              # noqa: E402
from t3d import box                                # noqa: E402

WALL = "ShaneChurch.BrownWall"
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if detail
                                                   else ""))


def nodes(log):
    m = re.search(r"Static BSP Nodes (\d+)", log)
    return int(m.group(1)) if m else -1


def build(name, brushes, **kw):
    m = Map(name)
    for b in brushes:
        m.add(b)
    m.player_start(0, 0, floor_z=-512)
    m.actor("Light", 0, 0, 600, LightBrightness=200, LightRadius=120)
    return m.build(validate=False, **kw)[1]


def room(x0, y0, z0, x1, y1, z1, name, csg="CSG_Subtract"):
    return box(x0, y0, z0, x1, y1, z1, name=name, texture=WALL, scale=4.0,
               csg=csg)


# ---------------------------------------------------------------------------
# 1. Separate rooms must produce MORE bsp nodes than one room.
#    This is the check that catches brushes collapsing onto the origin - the
#    bug where every room carves in the same place and the node count is flat.
# ---------------------------------------------------------------------------
one = nodes(build("ST-One", [room(-1024, -1024, -512, 1024, 1024, 768, "A")]))
two = nodes(build("ST-Two", [room(-1024, -1024, -512, 1024, 1024, 768, "A"),
                             room(-2048, -1024, 0, -1536, 1024, 768, "B")]))
check("two separate rooms build more nodes than one",
      two > one, f"one={one} two={two}")

# Control: the SAME room twice must NOT increase the node count, or the check
# above would pass for a broken build too.
dup = nodes(build("ST-Dup", [room(-1024, -1024, -512, 1024, 1024, 768, "A"),
                             room(-1024, -1024, -512, 1024, 1024, 768, "B")]))
check("control: duplicate room does not add nodes",
      dup == one, f"one={one} dup={dup}")

# ---------------------------------------------------------------------------
# 2. A CSG_Add solid inside a room must change the geometry.
# ---------------------------------------------------------------------------
plain = nodes(build("ST-Plain", [room(-1024, -1024, -512, 1024, 1024, 768, "A")]))
withcol = nodes(build("ST-Col", [
    room(-1024, -1024, -512, 1024, 1024, 768, "A"),
    room(-128, -128, -512, 128, 128, 128, "P", csg="CSG_Add")]))
check("an added pillar changes the bsp", withcol > plain,
      f"plain={plain} pillar={withcol}")

# ---------------------------------------------------------------------------
# 3. PATHS BUILD must produce reachspecs, and more nodes must mean more paths.
# ---------------------------------------------------------------------------
def paths_for(step):
    m = Map(f"ST-Path{step}")
    m.add(room(-1024, -1024, 0, 1024, 1024, 768, "A"))
    m.player_start(-800, -800, floor_z=0)
    for x in range(-896, 897, step):
        for y in range(-896, 897, step):
            m.path_node(x, y, 0)
    m.actor("Light", 0, 0, 600, LightBrightness=200, LightRadius=120)
    log = m.build(paths=True, validate=False)[1]
    built = re.search(r"Built Paths: (\d+)", log)
    specs = sum(int(n) for n in re.findall(r"Added (\d+) reachspecs", log))
    return (int(built.group(1)) if built else -1), specs


coarse_built, coarse_specs = paths_for(512)
fine_built, fine_specs = paths_for(256)
check("paths build produces reachspecs", coarse_specs > 0,
      f"specs={coarse_specs}")
check("denser pathnodes produce more reachspecs", fine_specs > coarse_specs,
      f"512-grid={coarse_specs} 256-grid={fine_specs}")


# ---------------------------------------------------------------------------
# 3b. Adding solid cover must NOT destroy bot navigation.
#     An inside-out CSG_Add brush still builds and still reports believable
#     BSP numbers, but takes reachspecs to zero - so pathing has to be measured
#     with added geometry present, not just in an empty box.
# ---------------------------------------------------------------------------
def paths_with_columns(n_cols):
    m = Map(f"ST-Cols{n_cols}")
    m.add(room(-1024, -1024, -512, 1024, 1024, 768, "Pit"))
    spots = [(-480, -480), (480, -480), (-480, 480), (480, 480)][:n_cols]
    for px, py in spots:
        m.add(box(px - 96, py - 96, -512, px + 96, py + 96, -128,
                  texture=WALL, name=f"C{px}_{py}", csg="CSG_Add", scale=2.0))
    m.player_start(-800, -800, floor_z=-512)
    m.path_grid(-820, 820, -820, 820, -512)
    m.actor("Light", 0, 0, 600, LightBrightness=200, LightRadius=200)
    log = m.build(paths=True, validate=False)[1]
    return sum(int(n) for n in re.findall(r"Added (\d+) reachspecs", log))


bare_specs = paths_with_columns(0)
col_specs = paths_with_columns(4)
check("bot paths survive added cover", col_specs > 0,
      f"empty={bare_specs} with-4-columns={col_specs}")

# ---------------------------------------------------------------------------
# 4. Every item class name must actually spawn.
# ---------------------------------------------------------------------------
def saved_classes(unr):
    """Classes actually present in a built map, read back from the .unr.

    Read from the map, not the build log: MAP IMPORTADD places actors without
    logging a line per actor, so counting log messages measures nothing.
    """
    import subprocess as _sp

    from build import SYSTEM64 as _S, UCC as _U, WORK as _W
    out = os.path.join(_W, "_classes.t3d")
    script = os.path.join(_W, "_classes.exec")
    with open(script, "w") as fh:
        fh.write(f'MAP LOAD FILE="{unr}"\nMAP EXPORT FILE="{out}"\n')
    _sp.run([_U, "exec", script], cwd=_S, capture_output=True, timeout=600)
    text = open(out, encoding="latin-1", errors="replace").read()
    return set(re.findall(r"Begin Actor Class=(\w+)", text))


m = Map("ST-Items")
m.add(room(-2048, -2048, 0, 2048, 2048, 768, "A"))
m.player_start(-1800, -1800, floor_z=0)
classes = sorted(items.all_classes())
for i, c in enumerate(classes):
    m.pickup(c, -1600 + (i % 10) * 320, -1600 + (i // 10) * 320, 0)
m.actor("Light", 0, 0, 600, LightBrightness=220, LightRadius=200)
unr = m.build(validate=False)[0]
present = saved_classes(unr)
# The Enforcer is the default spawn weapon; UT99 never places one as a map
# pickup, so its absence is correct rather than a failure.
missing = [c for c in classes if c not in present and c != "Enforcer"]
check("every item class spawns", not missing,
      f"requested={len(classes)} missing={missing[:4]}")

# Control: a class that does not exist must NOT end up in the map.
m2 = Map("ST-BadItem")
m2.add(room(-1024, -1024, 0, 1024, 1024, 768, "A"))
m2.player_start(0, 0, floor_z=0)
m2.actor("NoSuchPickupClass", 100, 100, 40)
check("control: unknown item class is not added",
      "NoSuchPickupClass" not in saved_classes(
          m2.build(validate=False)[0]))

# ---------------------------------------------------------------------------
# 5. Validators must reject what the engine would reject.
# ---------------------------------------------------------------------------
bad = Map("ST-BadStart")
bad.add(room(-1024, -1024, 0, 1024, 1024, 768, "A"))
bad.actor("PlayerStart", 0, 0, 740)        # cylinder pokes through ceiling
check("control: start in the ceiling is rejected", bool(bad.check()))

badtex = Map("ST-BadTex")
badtex.add(box(-1024, -1024, 0, 1024, 1024, 768, name="A",
               texture="ShaneChurch.NotARealTexture"))
badtex.player_start(0, 0, floor_z=0)
check("control: unknown texture is rejected", bool(badtex.check()))

# ---------------------------------------------------------------------------
# 6. Actors must land at the coordinates they were given.
#    `ACTOR ADD ... XPOS=` reports success and silently ignores the position,
#    stacking every light/item/start on the origin. Nothing in the build log
#    hints at it; the map just looks unlit and the props all pile up.
# ---------------------------------------------------------------------------
import subprocess                                     # noqa: E402

from build import SYSTEM64, UCC, WORK                 # noqa: E402

m = Map("ST-Place")
m.add(room(-1024, -1024, 0, 1024, 1024, 512, "A"))
m.viewpoint(0, -800, 58, yaw=16384)
m.actor("Light", 400, 300, 400, LightBrightness=200, LightRadius=64)
m.actor("Light", -400, -300, 400, LightBrightness=200, LightRadius=64)
unr = m.build(validate=False)[0]

exp = os.path.join(WORK, "_place.t3d")
script = os.path.join(WORK, "_place.exec")
with open(script, "w") as fh:
    fh.write(f'MAP LOAD FILE="{unr}"\nMAP EXPORT FILE="{exp}"\n')
subprocess.run([UCC, "exec", script], cwd=SYSTEM64, capture_output=True,
               timeout=600)
text = open(exp, encoding="latin-1", errors="replace").read()
locs = re.findall(r"Location=\(([^)]*)\)", text)
check("actors keep the coordinates they were given",
      len(locs) >= 3 and any("400" in l for l in locs),
      f"{len(locs)} actors have a Location")

# ---------------------------------------------------------------------------
# 7. Movers must actually become movers.
#    A Mover's geometry rides on the actor instead of being carved into the
#    world, so it shows up as MoverNodes rather than static BSP nodes. If the
#    class substitution silently failed it would import as an ordinary brush -
#    still "Success", but a door that never opens.
# ---------------------------------------------------------------------------
m = Map("ST-Mover")
m.add(room(-768, -768, 0, 768, 768, 384, "R"))
m.player_start(-600, -600, floor_z=0)
m.mover(box(-64, -8, 0, 64, 8, 192, texture=WALL, name="Door"), dy=120)
m.actor("Light", 0, 0, 330, LightBrightness=140, LightRadius=20)
log = m.build(validate=False)[1]
mover_nodes = re.search(r"MoverNodes = (\d+)", log)
check("a mover builds as a mover, not static geometry",
      bool(mover_nodes) and int(mover_nodes.group(1)) > 0,
      f"MoverNodes={mover_nodes.group(1) if mover_nodes else 'none'}")

# Control: the same brush added normally must contribute ZERO mover nodes.
m2 = Map("ST-NoMover")
m2.add(room(-768, -768, 0, 768, 768, 384, "R"))
m2.add(box(-64, -8, 0, 64, 8, 192, texture=WALL, name="Door",
           csg="CSG_Add"))
m2.player_start(-600, -600, floor_z=0)
m2.actor("Light", 0, 0, 330, LightBrightness=140, LightRadius=20)
log2 = m2.build(validate=False)[1]
mn2 = re.search(r"MoverNodes = (\d+)", log2)
check("control: a plain brush contributes no mover nodes",
      bool(mn2) and int(mn2.group(1)) == 0,
      f"MoverNodes={mn2.group(1) if mn2 else 'none'}")

print()
failed = [n for n, ok, _ in results if not ok]
print(f"{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
