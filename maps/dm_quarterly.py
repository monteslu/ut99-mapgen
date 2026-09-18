"""DM-QuarterlyReview - a corporate office complex.

Three floors of an office block connected by stairwells and an atrium, built
at real UT99 scale (DM-Deck16][ spans ~3700 x 4000 x 1950 units; this is
roughly 4600 x 3600 x 1400).

    LEVEL 2  (z=768)   executive floor: corner office, boardroom, balcony
                       ring overlooking the atrium
    LEVEL 1  (z=384)   cubicle farm, meeting room, break room
    GROUND   (z=0)     lobby + atrium, reception, server room

The atrium is a full-height shaft through all three floors, so the lobby is
visible from the executive balcony and vice versa - that vertical sightline is
what makes an office block play as a deathmatch map rather than a maze of
corridors.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import items                                       # noqa: E402
from build import Map, stats, tour                 # noqa: E402
from t3d import box, stairs                        # noqa: E402

# --------------------------------------------------------------- materials
CARPET = "OfficeProps.OfCarpet"
CARPET_BLUE = "OfficeProps.OfCarpetBlue"
CARPET_GREY = "OfficeProps.OfCarpetGrey"
CEIL = "OfficeProps.OfCeiling"
WALL = "OfficeProps.OfWall"
WALL_BLUE = "OfficeProps.OfWallBlue"
CUBICLE = "OfficeProps.OfCubicle"
WHITEBOARD = "OfficeProps.OfWhiteboard"
ELEVATOR = "OfficeProps.OfElevator"
LIGHTPANEL = "OfficeProps.OfLight"
# Stock UTtech1 is the "modern industrial" set - right for stairs and the
# service areas an office block hides behind its carpet.
STEEL = "UTtech1.bmTrim"
TREAD = "UTtech1.bmFloor2"
SERVICE = "UTtech1.bmwall3"

# Explicit floor heights. 448 of floor-to-floor gives 320 of headroom (a
# comfortable office ceiling for a 78-unit player) plus 128 of structure.
GROUND, L1, L2 = 0, 448, 896
CEIL_H = 320

m = Map("DM-QuarterlyReview")


def floorplate(x0, y0, x1, y1, z, name, carpet=CARPET, walls=WALL,
               ceiling=CEIL, height=CEIL_H, scale=2.0):
    """One carved room on a storey."""
    m.add(box(x0, y0, z, x1, y1, z + height, name=name, scale=scale,
              floor=carpet, ceiling=ceiling, walls=walls))


# =========================================================== GROUND: lobby
# Single storey. A double-height lobby would carve through the L1 floorplate
# above it - same footprint, overlapping Z - and merge both floors into one
# void. The atrium is the only shaft that spans storeys.
floorplate(-1600, -1400, 400, 200, GROUND, "Lobby", carpet=CARPET_GREY,
           walls=WALL, height=CEIL_H, scale=3.0)

# Reception desk island (solid, waist height) and two lift doors on the wall.
m.add(box(-700, -500, GROUND, -300, -360, GROUND + 48, name="Reception",
          texture=STEEL, csg="CSG_Add", scale=1.5))
for i, ex in enumerate((-1450, -1150)):
    m.add(box(ex, -1400, GROUND, ex + 220, -1380, GROUND + 260,
              name=f"LiftDoor{i}", texture=ELEVATOR, csg="CSG_Add", scale=1.0))

# Server room off the lobby - the one place with stock industrial textures.
floorplate(600, -1400, 1700, -700, GROUND, "ServerRoom", carpet=TREAD,
           walls=SERVICE, ceiling=SERVICE, height=CEIL_H, scale=2.0)
# Connecting corridor, lobby -> server room.
floorplate(400, -1150, 600, -950, GROUND, "ServerHall", carpet=CARPET_GREY,
           walls=WALL, height=260, scale=2.0)

# Server racks, as solid blocks in rows.
for i in range(4):
    rx = 760 + i * 230
    m.add(box(rx, -1300, GROUND, rx + 110, -900, GROUND + 190,
              name=f"Rack{i}", texture=SERVICE, csg="CSG_Add", scale=1.5))

# ===================================================== GROUND: atrium shaft
# The full-height void. Carved from the ground floor to above L2 so all three
# storeys open onto it.
ATRIUM = (400, -600, 1700, 200)
m.add(box(ATRIUM[0], ATRIUM[1], GROUND, ATRIUM[2], ATRIUM[3],
          L2 + CEIL_H, name="Atrium", scale=3.0,
          floor=CARPET_GREY, ceiling=CEIL, walls=WALL_BLUE))

# ============================================================ L1: open plan
floorplate(-1600, -1400, 400, 200, L1, "OpenPlanA",
           carpet=CARPET, walls=WALL)
floorplate(-1600, 200, 1700, 900, L1, "OpenPlanB",
           carpet=CARPET, walls=WALL)

# The cubicle farm: a grid of low partitions. Each is a separate solid, which
# is what makes this floor play - lots of waist-high cover, no full walls.
CUBE_W, CUBE_D, PART_H, PART_T = 320, 300, 120, 16
for gx in range(4):
    for gy in range(2):
        cx = -1500 + gx * (CUBE_W + 60)
        cy = 260 + gy * (CUBE_D + 60)
        z = L1
        # Two walls per cubicle (an L), so the farm stays permeable.
        m.add(box(cx, cy, z, cx + CUBE_W, cy + PART_T, z + PART_H,
                  name=f"CubA{gx}{gy}", texture=CUBICLE, csg="CSG_Add",
                  scale=1.0))
        m.add(box(cx, cy, z, cx + PART_T, cy + CUBE_D, z + PART_H,
                  name=f"CubB{gx}{gy}", texture=CUBICLE, csg="CSG_Add",
                  scale=1.0))

# Meeting room with a whiteboard wall, off the open plan.
floorplate(700, -1400, 1700, -700, L1, "MeetingRoom",
           carpet=CARPET_BLUE, walls=WALL_BLUE)
m.add(box(1650, -1300, L1 + 40, 1690, -800, L1 + 220,
          name="Whiteboard", texture=WHITEBOARD, csg="CSG_Add", scale=1.0))

# Break room, the other corner.
floorplate(-1600, -1400, -700, -800, L1, "BreakRoom",
           carpet=CARPET_GREY, walls=WALL)

# ========================================================= L2: executive
floorplate(-1600, -1400, 400, -200, L2, "ExecFloor",
           carpet=CARPET_BLUE, walls=WALL_BLUE)
floorplate(-1600, -200, 1700, 900, L2, "Boardroom",
           carpet=CARPET_BLUE, walls=WALL_BLUE)

# Balcony ring around the atrium, so the exec floor overlooks the lobby.
BAL = 160
for nm, (bx0, by0, bx1, by1) in {
        "BalW": (ATRIUM[0] - BAL, ATRIUM[1] - BAL, ATRIUM[0], ATRIUM[3] + BAL),
        "BalE": (ATRIUM[2], ATRIUM[1] - BAL, ATRIUM[2] + BAL, ATRIUM[3] + BAL),
        "BalN": (ATRIUM[0], ATRIUM[1] - BAL, ATRIUM[2], ATRIUM[1]),
        "BalS": (ATRIUM[0], ATRIUM[3], ATRIUM[2], ATRIUM[3] + BAL)}.items():
    m.add(box(bx0, by0, L2, bx1, by1,
              L2 + CEIL_H, name=nm, scale=2.0,
              floor=CARPET_BLUE, ceiling=CEIL, walls=WALL_BLUE))

# ======================================================= vertical circulation
# Two stairwells at opposite ends, so neither floor has a single chokepoint.
# 160-unit treads: a PathNode carries a 46-unit radius and on a narrower tread
# its collision cylinder clips the next step up and drops out of the network.
STAIR_STEPS, TREAD_D = 8, 160
STAIR_RUN = STAIR_STEPS * TREAD_D


def stairwell(x0, y0, z_from, z_to, name, width=260):
    """A straight run plus the shaft it climbs through."""
    rise = (z_to - z_from) / STAIR_STEPS
    # Carve the shaft first, tall enough to walk the whole run.
    m.add(box(x0, y0, z_from, x0 + STAIR_RUN, y0 + width, z_to + CEIL_H,
              name=f"{name}Shaft", scale=2.0, floor=TREAD, ceiling=CEIL,
              walls=SERVICE))
    for br in stairs(x0, y0, z_from, x0 + STAIR_RUN, y0 + width,
                     steps=STAIR_STEPS, rise=rise, axis="x", texture=TREAD,
                     name=name, scale=1.5):
        m.add(br)
    # Nodes on the middle of each tread link the two storeys for bots.
    # Only the treads whose node clears the NEXT tread get one: the top steps
    # of a run sit against the shaft head and a node there is buried in solid.
    for i in range(STAIR_STEPS - 2):
        m.path_node(int(x0 + i * TREAD_D + TREAD_D / 2), int(y0 + width / 2),
                    int(z_from + (i + 1) * rise))


# West stairwell: ground -> L1 -> L2.
stairwell(-1500, -780, GROUND, L1, "StairW1")
stairwell(-1500, -780, L1, L2, "StairW2")
# East stairwell, offset so the two runs do not stack into one shaft.
stairwell(700, 300, GROUND, L1, "StairE1")
stairwell(700, 300, L1, L2, "StairE2")

# ================================================================== spawns
for x, y, z in ((-1400, -1200, GROUND), (-200, -1200, GROUND),
                (1200, -800, GROUND), (1500, 100, GROUND),
                (-1400, 150, L1), (-200, 150, L1), (1200, -1000, L1),
                (-1400, -1200, L2), (300, 600, L2), (1500, 600, L2)):
    m.player_start(x, y, floor_z=z)

# =================================================================== items
# Strongest gear in the atrium - the most exposed space in the building.
m.pickup(items.SHIELD_BELT, 1050, -200, GROUND)
m.pickup(items.weapon("rocket"), 700, -400, GROUND)
m.pickup(items.ammo("rocket"), 700, -250, GROUND)
m.pickup(items.POWERUP_DAMAGE, 1400, 0, GROUND)

# Weapons spread one per zone, each beside its ammo.
for key, x, y, z in (("flakcannon", -1200, -1100, GROUND),
                     ("shockrifle", 1100, -1050, GROUND),
                     ("minigun", -1200, 600, L1),
                     ("pulsegun", 1200, -1050, L1),
                     ("biorifle", -1000, -1200, L1),
                     ("sniper", -1200, -1200, L2),
                     ("ripper", 1400, 600, L2)):
    m.pickup(items.weapon(key), x, y, z)
    m.pickup(items.ammo(key), x + 150, y, z)

m.pickup(items.ARMOR_LARGE, -1400, -900, L2)
m.pickup(items.ARMOR_SMALL, 1500, -1000, GROUND)
for x, y, z in ((-800, -1200, GROUND), (-1400, 100, L1), (900, 700, L1),
                (-800, -1200, L2), (1500, 200, L2), (200, -1200, GROUND)):
    m.pickup(items.HEALTH_SMALL, x, y, z)
for x, y, z in ((-1500, -1000, L1), (1600, 800, L2)):
    m.pickup(items.HEALTH_LARGE, x, y, z)

# ================================================================= lighting
# A ceiling-light grid per floor. Offices are evenly lit; one lamp in a big
# room leaves a black void, and stock UT99 maps use hundreds of lights.
def lightgrid(x0, x1, y0, y1, z, step=380, bright=128, radius=16):
    x = x0
    while x <= x1:
        y = y0
        while y <= y1:
            m.actor("Light", int(x), int(y), int(z),
                    LightBrightness=bright, LightRadius=radius)
            y += step
        x += step


lightgrid(-1400, 200, -1200, 0, GROUND + 700, bright=140, radius=22)  # lobby
lightgrid(700, 1600, -1300, -800, GROUND + 260)                       # server
lightgrid(500, 1600, -500, 100, GROUND + 700, bright=140, radius=24)  # atrium
lightgrid(-1400, 200, -1200, 100, L1 + 280)                           # openplan
lightgrid(-1400, 1600, 300, 800, L1 + 280)                            # cubicles
lightgrid(800, 1600, -1300, -800, L1 + 280)                           # meeting
lightgrid(-1400, 200, -1300, -300, L2 + 280)                          # exec
lightgrid(-1400, 1600, -100, 800, L2 + 280)                           # board
lightgrid(400, 1700, -600, 200, L2 + 280, bright=132)                 # balcony
for sx in (-1400, 800):                                               # stairs
    for sz in (GROUND + 200, L1 + 200, L2 + 200):
        m.actor("Light", sx, -650 if sx < 0 else 430, sz,
                LightBrightness=128, LightRadius=16)

# ================================================================ bot paths
# One grid per open area, on a ~256 spacing (Deck16's median is 208).
m.path_grid(-1500, 300, -1300, 100, GROUND)      # lobby
m.path_grid(700, 1600, -1300, -800, GROUND)      # server room
m.path_grid(500, 1600, -500, 100, GROUND)        # atrium floor
m.path_grid(-1500, 300, -1300, 100, L1)          # open plan A
m.path_grid(-1500, 1600, 300, 800, L1)           # cubicle farm
m.path_grid(800, 1600, -1300, -800, L1)          # meeting room
m.path_grid(-1500, -800, -1300, -900, L1)        # break room
m.path_grid(-1500, 300, -1300, -300, L2)         # exec floor
m.path_grid(-1500, 1600, -100, 800, L2)          # boardroom
m.path_grid(450, 1650, -550, 150, L2)            # balcony ring

# ================================================================ furniture
# Props are Kenney CC0 models converted to UE1 vertex meshes (tools/make_props).
# They are decoration only - they do not block movement - so they dress the
# space without turning the cubicle farm into a maze.
def prop(cls, x, y, z, yaw=0):
    # obj2mesh sits each model's base at mesh z=0, so the floor height IS the
    # actor height - no clearance, or the furniture hovers.
    m.actor(f"OfficeProps.{cls}", int(x), int(y), int(z),
            Rotation=f"(Yaw={int(yaw)})")


# A desk, chair and computer per cubicle in the farm.
for gx in range(4):
    for gy in range(2):
        cx = -1500 + gx * (CUBE_W + 60) + CUBE_W // 2
        cy = 260 + gy * (CUBE_D + 60) + CUBE_D // 2
        prop("OfDesk", cx, cy + 40, L1, yaw=16384)
        prop("OfChair", cx, cy - 40, L1, yaw=49152)
        prop("OfMonitor", cx - 30, cy + 55, L1 + 46, yaw=16384)
        prop("OfKeyboard", cx + 30, cy + 30, L1 + 46, yaw=16384)

# Lobby: reception seating and greenery.
prop("OfSofa", -1100, -700, GROUND, yaw=0)
prop("OfSofa", -1100, -300, GROUND, yaw=32768)
prop("OfCoffeeTable", -1100, -500, GROUND)
for px, py in ((-1500, -1250), (-350, -1250), (300, 100), (-1500, 100)):
    prop("OfPlantTall", px, py, GROUND)

# Meeting room: a long table flanked by chairs, facing the whiteboard.
for i in range(3):
    prop("OfTableRound", 1050 + i * 190, -1050, L1)
for i in range(3):
    prop("OfChairPlain", 1050 + i * 190, -900, L1, yaw=49152)
    prop("OfChairPlain", 1050 + i * 190, -1200, L1, yaw=16384)

# Break room: tables, chairs, a plant.
for i in range(2):
    prop("OfTableRound", -1400 + i * 300, -1100, L1)
    prop("OfChairPlain", -1400 + i * 300, -970, L1, yaw=49152)
prop("OfPlant", -800, -1300, L1)
prop("OfCabinet", -1550, -1300, L1, yaw=16384)

# Executive floor: corner office and a boardroom that means business.
prop("OfDeskCorner", -1350, -1250, L2, yaw=8192)
prop("OfChair", -1350, -1100, L2, yaw=49152)
prop("OfBookcaseWide", -1550, -700, L2, yaw=16384)
prop("OfBookcase", -1550, -400, L2, yaw=16384)
prop("OfLamp", -1100, -1300, L2)
for i in range(4):
    prop("OfTableRound", -800 + i * 200, 300, L2)
    prop("OfChairPlain", -800 + i * 200, 450, L2, yaw=49152)
    prop("OfChairPlain", -800 + i * 200, 150, L2, yaw=16384)
for px, py in ((-1550, 800), (1600, 800), (1600, -100)):
    prop("OfPlantTall", px, py, L2)

# Open plan A gets a few loose desks so it is not an empty carpet.
for i in range(3):
    prop("OfDesk", -1300 + i * 420, -300, L1, yaw=16384)
    prop("OfChair", -1300 + i * 420, -420, L1, yaw=49152)
    prop("OfMonitor", -1330 + i * 420, -285, L1 + 46, yaw=16384)

# ================================================================== camera
# A fixed viewpoint makes shots reproducible; the spectator spawns at the ONLY
# PlayerStart, so without this the camera lands somewhere different each run.
# Override with OFFICE_VIEW=<n> to inspect a different room.
VIEWS = [
    (-1250, -1150, GROUND + 58, 8192, -600),    # 0 lobby, toward reception
    (-1500, 350, L1 + 58, 0, -800),             # 1 down the cubicle farm
    (900, -1000, L1 + 58, 16384, -400),         # 2 meeting room + whiteboard
    (-1500, -1300, L2 + 58, 6000, -600),        # 3 corner office
    (-900, 300, L2 + 58, 0, -400),              # 4 boardroom table
    (500, -200, GROUND + 58, 0, 2000),          # 5 atrium, looking up
    (1100, -1100, GROUND + 58, 0, -400),        # 6 server room
    (-1500, 500, L1 + 200, 2000, -2500),        # 7 cubicle farm from above
    (1650, -150, L2 + 150, 32768, -3000),       # 8 atrium from the balcony
    (-1500, -1300, GROUND + 58, 6000, 0),       # 9 lobby, corner to corner
]
if "OFFICE_VIEW" in os.environ:
    # Inspection mode: one start with a known facing, so shots are repeatable.
    _v = VIEWS[int(os.environ["OFFICE_VIEW"]) % len(VIEWS)]
    m.viewpoint(*_v[:3], yaw=_v[3], pitch=_v[4])
else:
    # Play mode keeps all ten spawns spread across the three floors.
    m.camera(*VIEWS[0][:3], yaw=VIEWS[0][3], pitch=VIEWS[0][4])

if __name__ == "__main__":
    unr, log = m.build(paths=True)
    print("built:", unr)
    for line in stats(log):
        print("  ", line)
    if "--shot" in sys.argv:
        for p in tour("DM-QuarterlyReview", shots=3):
            print("  shot:", p)
