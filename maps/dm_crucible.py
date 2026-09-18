"""DM-Crucible - a real deathmatch map, not a box.

Two-storey layout built from many brushes rather than one large room:

    upper                        lower (z = -512)
    +-------------------+        +-------------------+
    |    WEST LEDGE     |        |                   |
    |  (sniper perch)   |        |                   |
    +----+---------+----+        |   PIT / ARENA     |
         |         |             |   (rocket, belt)  |
      stairs    stairs           |                   |
         |         |             +---------+---------+
    +----+---------+----+                  |
    |   NORTH GALLERY   |===== corridor ===+
    |   (flak, health)  |
    +-------------------+

Item placement follows how Epic does it in DM-Deck16][: the strongest items
(shield belt, rocket launcher, damage amp) sit in the most exposed low ground,
weapons are each paired with their ammo nearby, and health is scattered along
the routes between them rather than next to the weapons.

Bot navigation: PathNodes on a ~256 grid through every walkable space (Deck16's
median node spacing is 208), then PATHS BUILD links them.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import items                                       # noqa: E402
from build import Map, stats, tour                 # noqa: E402
from t3d import box, stairs                        # noqa: E402

WALL = "ShaneChurch.BrownWall"
FLOOR = "ShaneChurch.BrownFloor"
CEIL = "ShaneChurch.Celing2"
TRIM = "ShaneChurch.BrownTrim"
STEP = "ShaneChurch.Bloks-l"

UPPER_Z = 0          # floor height of the upper storey
LOWER_Z = -512       # floor height of the pit
CEIL_UP = 768        # ceiling above the upper floor

m = Map("DM-Crucible")

# ------------------------------------------------------------------ the pit
# Big central arena, two storeys tall, open to the upper ring.
m.add(box(-1024, -1024, LOWER_Z, 1024, 1024, CEIL_UP, name="Pit",
          scale=4.0, floor=FLOOR, ceiling=CEIL, walls=WALL))

# --------------------------------------------------------------- upper ring
# A walkway around the pit: four subtracted arms at UPPER_Z.
RING_W = 512
m.add(box(-1024 - RING_W, -1024, UPPER_Z, -1024, 1024, CEIL_UP,
          name="RingWest", scale=4.0, floor=FLOOR, ceiling=CEIL, walls=WALL))
m.add(box(1024, -1024, UPPER_Z, 1024 + RING_W, 1024, CEIL_UP,
          name="RingEast", scale=4.0, floor=FLOOR, ceiling=CEIL, walls=WALL))
m.add(box(-1024 - RING_W, -1024 - RING_W, UPPER_Z, 1024 + RING_W, -1024,
          CEIL_UP, name="RingNorth", scale=4.0, floor=FLOOR, ceiling=CEIL,
          walls=WALL))
m.add(box(-1024 - RING_W, 1024, UPPER_Z, 1024 + RING_W, 1024 + RING_W,
          CEIL_UP, name="RingSouth", scale=4.0, floor=FLOOR, ceiling=CEIL,
          walls=WALL))

# No floor slabs are needed under the ring: the ring rooms are carved starting
# at UPPER_Z, so everything below them is still solid world. Adding slabs there
# re-filled the rings and collapsed the map to a single BSP leaf.

# ------------------------------------------------------------------- stairs
# Two staircases down into the pit, on opposite corners, so the low ground is
# contested from two directions instead of being a single chokepoint.
#
# Tread depth is 160 rather than the 80 a shorter run would give: a PathNode
# carries NavigationPoint's 46-unit radius, so on a narrow tread its collision
# cylinder always clips the next step up and the node drops out of the path
# network. 8 steps x 160 = 1280 of run for 512 of rise, a walkable 1:2.5.
STAIR_STEPS = 8
STAIR_TREAD = 160
STAIR_RUN = STAIR_STEPS * STAIR_TREAD
for br in stairs(-1024, -1024, LOWER_Z, -1024 + STAIR_RUN, -768,
                 steps=STAIR_STEPS, rise=(UPPER_Z - LOWER_Z) / STAIR_STEPS,
                 axis="x", texture=STEP, name="StairNW", scale=2.0):
    m.add(br)
for br in stairs(1024, 1024, LOWER_Z, 1024 - STAIR_RUN, 768,
                 steps=STAIR_STEPS, rise=(UPPER_Z - LOWER_Z) / STAIR_STEPS,
                 axis="x", texture=STEP, name="StairSE", scale=2.0):
    m.add(br)

# ------------------------------------------------------------------- cover
# Four pillars in the pit break the long sightlines a square arena would have.
for px, py in ((-480, -480), (480, -480), (-480, 480), (480, 480)):
    m.add(box(px - 96, py - 96, LOWER_Z, px + 96, py + 96, LOWER_Z + 384,
              texture=TRIM, name=f"Col{px}_{py}", csg="CSG_Add", scale=2.0))

# A raised sniper ledge on the west ring.
m.add(box(-1024 - RING_W, -256, UPPER_Z, -1024 - 128, 256, UPPER_Z + 192,
          texture=TRIM, name="Perch", csg="CSG_Add", scale=2.0))

# ------------------------------------------------------------------- spawns
# The west mid-ring slot would land inside the sniper perch, so it moves north.
for x, y in ((-1280, -1280), (1280, -1280), (-1280, 1280), (1280, 1280),
             (-1280, -640), (1280, 0)):
    m.player_start(x, y, floor_z=UPPER_Z)
for x, y in ((-700, -700), (700, 700)):
    m.player_start(x, y, floor_z=LOWER_Z)

# -------------------------------------------------------------------- items
# Strongest gear in the open low ground, where taking it exposes you.
m.pickup(items.SHIELD_BELT, 0, 0, LOWER_Z)
m.pickup(items.weapon("rocket"), -300, 0, LOWER_Z)
m.pickup(items.ammo("rocket"), -300, 160, LOWER_Z)
m.pickup(items.ammo("rocket"), -300, -160, LOWER_Z)
m.pickup(items.POWERUP_DAMAGE, 300, 0, LOWER_Z)

# Mid-tier weapons on the ring, each next to its own ammo.
ring_items = [
    ("flakcannon", -1280, -700),
    ("minigun", 1280, -700),
    ("pulsegun", -1280, 700),
    ("biorifle", 1280, 700),
]
for key, x, y in ring_items:
    m.pickup(items.weapon(key), x, y, UPPER_Z)
    m.pickup(items.ammo(key), x, y + 160, UPPER_Z)

# Sniper rifle on the perch it was built for.
m.pickup(items.weapon("sniper"), -1400, 0, UPPER_Z + 192)
m.pickup(items.ammo("sniper"), -1400, 160, UPPER_Z + 192)

# Shock rifle at each stair head - the route item.
m.pickup(items.weapon("shockrifle"), -640, -1200, UPPER_Z)
m.pickup(items.ammo("shockrifle"), -640, -1360, UPPER_Z)
m.pickup(items.weapon("shockrifle"), 640, 1200, UPPER_Z)
m.pickup(items.ammo("shockrifle"), 640, 1360, UPPER_Z)

# Armour on the ring corners, health scattered along the routes.
m.pickup(items.ARMOR_LARGE, -1280, -1280, UPPER_Z)
m.pickup(items.ARMOR_SMALL, 1280, 1280, UPPER_Z)
for x, y in ((-800, -1280), (800, -1280), (-800, 1280), (800, 1280),
             (-1280, -300), (1280, 300)):
    m.pickup(items.HEALTH_SMALL, x, y, UPPER_Z)
for x, y in ((-820, 0), (820, 0)):
    m.pickup(items.HEALTH_LARGE, x, y, LOWER_Z)

# ---------------------------------------------------------------- bot paths
# A ~256 grid through each walkable space. Bots step between nodes that are in
# reach of one another, so the grids must overlap at the stairs to connect the
# two storeys.
# path_grid skips nodes that would land inside the pillars; a node buried in a
# solid silently drops out of the network and takes the bot paths with it.
placed = 0
placed += m.path_grid(-820, 820, -820, 820, LOWER_Z)       # pit floor
placed += m.path_grid(-1400, -1120, -1400, 1400, UPPER_Z)  # west ring
placed += m.path_grid(1120, 1400, -1400, 1400, UPPER_Z)    # east ring
placed += m.path_grid(-1024, 1024, -1400, -1120, UPPER_Z)  # north ring
placed += m.path_grid(-1024, 1024, 1120, 1400, UPPER_Z)    # south ring

# Nodes climbing each staircase. Tread i has its top at LOWER_Z+(i+1)*rise, so
# the node for that tread stands on top of it; putting the node at the tread's
# base would bury it in solid and drop it from the network.
# Nodes climbing each staircase. A node stands on tread i and must clear tread
# i+1, so it sits at the middle of its own tread where there is room for the
# 46-unit collision radius on both sides.
RISE = (UPPER_Z - LOWER_Z) / STAIR_STEPS
for i in range(STAIR_STEPS):
    top = LOWER_Z + (i + 1) * RISE
    mid = STAIR_TREAD / 2
    m.path_node(int(-1024 + i * STAIR_TREAD + mid), -896, int(top))
    m.path_node(int(1024 - i * STAIR_TREAD - mid), 896, int(top))

# ----------------------------------------------------------------- lighting
def lights(x0, x1, y0, y1, z, step=512, bright=160, radius=64):
    x = x0
    while x <= x1:
        y = y0
        while y <= y1:
            m.actor("Light", int(x), int(y), int(z),
                    LightBrightness=bright, LightRadius=radius)
            y += step
        x += step

lights(-896, 896, -896, 896, CEIL_UP - 96, bright=150, radius=80)   # pit
lights(-1408, -1152, -1280, 1280, CEIL_UP - 96)                     # west
lights(1152, 1408, -1280, 1280, CEIL_UP - 96)                       # east
lights(-1024, 1024, -1408, -1152, CEIL_UP - 96)                     # north
lights(-1024, 1024, 1152, 1408, CEIL_UP - 96)                       # south
# Warm up the two stair runs and the pit floor itself.
lights(-960, -320, -1024, -768, UPPER_Z + 200, step=320, radius=56)
lights(320, 960, 768, 1024, UPPER_Z + 200, step=320, radius=56)
lights(-768, 768, -768, 768, LOWER_Z + 300, step=640, bright=130, radius=72)

# A camera looking across the pit, for screenshots.
m.camera(-1500, 0, UPPER_Z + 400, yaw=0, pitch=-3000)

if __name__ == "__main__":
    unr, log = m.build(paths=True)
    print("built:", unr)
    for line in stats(log):
        print("  ", line)
    kinds = {}
    for a in m.actors:
        kinds[a[0]] = kinds.get(a[0], 0) + 1
    print("  brushes", len(m.brushes))
    print("  ", ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    if "--shot" in sys.argv:
        for p in tour("DM-Crucible", shots=3):
            print("  shot:", p)
