"""DM-QuarterlyReview - a corporate office complex.

Three floors of an office block, built at the scale real UT99 maps use
(DM-Deck16][ spans ~3700 x 4000 x 1950 units; this is ~4400 x 3800 x 1500).

    L2  z=896   executive: corner office, boardroom, balcony over the atrium
    L1  z=448   cubicle farm, meeting room, break room, copy room
    G   z=0     lobby, reception, atrium floor, server room, loading bay

## What makes it play

The **atrium** is a full-height shaft through all three floors. You can drop
from the executive balcony into the lobby, and anyone in the lobby can be shot
at from two floors up. That vertical sightline is the spine of the map: without
it an office block is a maze of same-sized boxes.

Three separate routes connect the floors, so no single staircase is a
chokepoint: the **west stair**, the **east stair**, and the **lift shaft**,
whose doors on each floor are movers.

Item placement follows Epic's convention: the strongest gear (shield belt,
rocket launcher, damage amp) sits in the most exposed low ground of the atrium,
each weapon is paired with its own ammo, and health is scattered along the
routes between them rather than next to the weapons.

## Layout, viewed from above

        WEST                        EAST
    +---------------+  +--------------------+
    |  west wing    |  |   meeting / server |   north (y < 0)
    +------+--------+  +---------+----------+
           |                     |
    +------+---------------------+----------+
    |            ATRIUM (full height)        |  middle
    +------+---------------------+----------+
           |                     |
    +------+--------+  +---------+----------+
    |  south wing   |  |   copy / loading   |   south (y > 0)
    +---------------+  +--------------------+
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import items                                       # noqa: E402
from build import Map, stats, tour                 # noqa: E402
from t3d import box, stairs                        # noqa: E402

# ------------------------------------------------------------- materials
CARPET = "OfficeProps.OfCarpet"
CARPET_BLUE = "OfficeProps.OfCarpetBlue"
CARPET_GREY = "OfficeProps.OfCarpetGrey"
CEIL = "OfficeProps.OfCeiling"
WALL = "OfficeProps.OfWall"
WALL_BLUE = "OfficeProps.OfWallBlue"
CUBICLE = "OfficeProps.OfCubicle"
WHITEBOARD = "OfficeProps.OfWhiteboard"
ELEVATOR = "OfficeProps.OfElevator"
# UTtech1 is the stock "modern industrial" set, right for the service spaces
# an office block hides behind its carpet.
STEEL = "UTtech1.bmTrim"
TREAD = "UTtech1.bmFloor2"
SERVICE = "UTtech1.bmwall3"
SERVICE_FLOOR = "UTtech1.bmFloor"

# Floor heights. 448 of floor-to-floor gives 320 of headroom (a comfortable
# office ceiling for a 78-unit player) plus 128 of structure.
GROUND, L1, L2 = 0, 448, 896
CEIL_H = 320
TOP = L2 + CEIL_H

m = Map("DM-QuarterlyReview")

# The single biggest lever on how a UT99 map looks. Left unset, every surface
# renders near its full texture brightness and the level is flat and washed
# out however carefully you place lights. Epic's DM-Codex uses 6 and renders
# at a mean of (54,46,34); this map with no ambient set rendered (137,146,166).
m.level_info(AmbientBrightness=8, Brightness="1.000000")


def room(x0, y0, x1, y1, z, name, carpet=CARPET, walls=WALL, ceiling=CEIL,
         height=CEIL_H, scale=2.0):
    """One carved room on a storey.

    Rooms must not overlap in Z with the floorplate above them: a room that
    reaches into the next storey carves through its floor and the two merge
    into a single void. Only the atrium deliberately spans storeys.
    """
    m.add(box(x0, y0, z, x1, y1, z + height, name=name, scale=scale,
              floor=carpet, ceiling=ceiling, walls=walls))


# ==================================================== the atrium (all floors)
# Carved first and full height, so every storey opens onto it.
AT_X0, AT_Y0, AT_X1, AT_Y1 = -400, -500, 900, 500
m.add(box(AT_X0, AT_Y0, GROUND, AT_X1, AT_Y1, TOP, name="Atrium", scale=3.0,
          floor=CARPET_GREY, ceiling=CEIL, walls=WALL_BLUE))

# ============================================================== GROUND floor
room(-2000, -1500, AT_X0, 500, GROUND, "LobbyWest", carpet=CARPET_GREY)
room(-2000, 500, 400, 1500, GROUND, "LobbySouth", carpet=CARPET_GREY)
room(AT_X1, -1500, 2200, 500, GROUND, "ServerRoom", carpet=SERVICE_FLOOR,
     walls=SERVICE, ceiling=SERVICE)
room(400, 500, 2200, 1500, GROUND, "LoadingBay", carpet=SERVICE_FLOOR,
     walls=SERVICE, ceiling=SERVICE)

# Reception desk: a solid island to break line of sight behind.
m.add(box(-1500, -300, GROUND, -1000, -160, GROUND + 48, name="Reception",
          texture=WALL_BLUE, csg="CSG_Add", scale=1.5))

# Server racks in rows, chest height for cover.
for i in range(5):
    rx = 1050 + i * 220
    m.add(box(rx, -1400, GROUND, rx + 120, -700, GROUND + 190,
              name=f"Rack{i}", texture=SERVICE, csg="CSG_Add", scale=1.5))

# Loading bay crates, staggered so the room is not a shooting gallery. They
# keep clear of y 900-1180, which is the east stairwell's run.
for i, (cx, cy, ch) in enumerate((
        (600, 650, 160), (1400, 620, 224), (1900, 700, 160),
        (700, 1250, 192), (1250, 1300, 160), (1800, 1250, 192))):
    m.add(box(cx, cy, GROUND, cx + 190, cy + 190, GROUND + ch,
              name=f"Crate{i}", texture=STEEL, csg="CSG_Add", scale=1.2))

# ============================================================= L1: open plan
room(-2000, -1500, AT_X0, 500, L1, "OpenPlanWest", carpet=CARPET)
room(-2000, 500, 400, 1500, L1, "CubicleFarm", carpet=CARPET)
room(AT_X1, -1500, 2200, 500, L1, "MeetingRoom", carpet=CARPET_BLUE,
     walls=WALL_BLUE)
room(400, 500, 2200, 1500, L1, "CopyRoom", carpet=CARPET_GREY)

# The cubicle farm: L-shaped partitions, waist high. This is the floor that
# plays best - lots of cover, nothing that fully blocks a sightline.
CUBE_W, CUBE_D, PART_H, PART_T = 330, 300, 120, 16
for gx in range(6):
    for gy in range(3):
        cx = -1900 + gx * (CUBE_W + 60)
        cy = 600 + gy * (CUBE_D + 50)
        m.add(box(cx, cy, L1, cx + CUBE_W, cy + PART_T, L1 + PART_H,
                  name=f"CubA{gx}{gy}", texture=CUBICLE, csg="CSG_Add"))
        m.add(box(cx, cy, L1, cx + PART_T, cy + CUBE_D, L1 + PART_H,
                  name=f"CubB{gx}{gy}", texture=CUBICLE, csg="CSG_Add"))

# Meeting room: a whiteboard wall you can see from the door.
m.add(box(2140, -1200, L1 + 40, 2180, -400, L1 + 230, name="Whiteboard",
          texture=WHITEBOARD, csg="CSG_Add"))

# Copy room: a bank of machines along the wall.
for i in range(3):
    m.add(box(600 + i * 320, 1320, L1, 780 + i * 320, 1460, L1 + 150,
              name=f"Copier{i}", texture=STEEL, csg="CSG_Add", scale=1.2))

# ============================================================= L2: executive
room(-2000, -1500, AT_X0, 500, L2, "ExecFloor", carpet=CARPET_BLUE,
     walls=WALL_BLUE)
room(-2000, 500, 400, 1500, L2, "Boardroom", carpet=CARPET_BLUE,
     walls=WALL_BLUE)
room(AT_X1, -1500, 2200, 500, L2, "ExecEast", carpet=CARPET_BLUE,
     walls=WALL_BLUE)

# Balcony ring around the atrium: the reason the vertical sightline exists.
BAL = 200
for nm, (bx0, by0, bx1, by1) in {
        "BalN": (AT_X0 - BAL, AT_Y0 - BAL, AT_X1 + BAL, AT_Y0),
        "BalS": (AT_X0 - BAL, AT_Y1, AT_X1 + BAL, AT_Y1 + BAL),
        "BalW": (AT_X0 - BAL, AT_Y0, AT_X0, AT_Y1),
        "BalE": (AT_X1, AT_Y0, AT_X1 + BAL, AT_Y1)}.items():
    m.add(box(bx0, by0, L2, bx1, by1, L2 + CEIL_H, name=nm, scale=2.0,
              floor=CARPET_BLUE, ceiling=CEIL, walls=WALL_BLUE))

# A low parapet round the atrium edge, so the drop reads as deliberate rather
# than as a missing floor. Kept low: at 56+ it fills the view from the balcony
# and hides the very sightline the atrium exists to create.
PARA = 32
for nm, (px0, py0, px1, py1) in {
        "ParaN": (AT_X0, AT_Y0 - 24, AT_X1, AT_Y0),
        "ParaS": (AT_X0, AT_Y1, AT_X1, AT_Y1 + 24),
        "ParaW": (AT_X0 - 24, AT_Y0, AT_X0, AT_Y1),
        "ParaE": (AT_X1, AT_Y0, AT_X1 + 24, AT_Y1)}.items():
    m.add(box(px0, py0, L2, px1, py1, L2 + PARA, name=nm, texture=WALL_BLUE,
              csg="CSG_Add", scale=1.0))

# ==================================================== vertical circulation
# 160-unit treads: a PathNode carries a 46-unit radius, and on a narrower
# tread its collision cylinder clips the next step up and drops out of the
# bot network entirely.
STAIR_STEPS, TREAD_D = 8, 160
STAIR_RUN = STAIR_STEPS * TREAD_D


def stairwell(x0, y0, z_from, z_to, name, width=280):
    """A straight run plus the shaft it climbs through.

    The shaft stops at the destination floor plus headroom, NOT at
    `z_to + CEIL_H`: a shaft that reaches a full storey above its landing
    carves through the floorplate up there and opens a hole in the middle of
    that room, which reads in game as a wall of bare service texture standing
    in an office.
    """
    rise = (z_to - z_from) / STAIR_STEPS
    m.add(box(x0, y0, z_from, x0 + STAIR_RUN, y0 + width, z_to + 224,
              name=f"{name}Shaft", scale=2.0, floor=TREAD, ceiling=CEIL,
              walls=SERVICE))
    for br in stairs(x0, y0, z_from, x0 + STAIR_RUN, y0 + width,
                     steps=STAIR_STEPS, rise=rise, axis="x", texture=TREAD,
                     name=name, scale=1.5):
        m.add(br)
    # A node per tread, minus the top two: those sit against the shaft head
    # where a node's collision cylinder is buried in solid.
    for i in range(STAIR_STEPS - 2):
        m.path_node(int(x0 + i * TREAD_D + TREAD_D / 2), int(y0 + width / 2),
                    int(z_from + (i + 1) * rise))


stairwell(-1900, -1400, GROUND, L1, "StairW1")
stairwell(-1900, -1400, L1, L2, "StairW2")
stairwell(900, 900, GROUND, L1, "StairE1")
stairwell(900, 900, L1, L2, "StairE2")

# The lift shaft. Its doors on each floor are movers, which is what makes the
# building feel like a building rather than a set of rooms.
LIFT_X, LIFT_Y = -1900, 200
m.add(box(LIFT_X, LIFT_Y, GROUND, LIFT_X + 300, LIFT_Y + 300, TOP,
          name="LiftShaft", scale=2.0, floor=SERVICE_FLOOR, ceiling=SERVICE,
          walls=ELEVATOR))
for floor_z in (GROUND, L1, L2):
    m.mover(box(LIFT_X + 292, LIFT_Y + 30, floor_z,
                LIFT_X + 308, LIFT_Y + 270, floor_z + 240,
                texture=ELEVATOR, name=f"LiftDoor{floor_z}"),
            dy=-240, move_time=1.1, stay_open=3.0)

# =================================================================== spawns
# spawn() nudges each start to the nearest spot its collision cylinder
# actually fits, so adding a desk or a crate near a spawn point cannot silently
# break the map. A start that cannot be placed anywhere nearby is reported
# rather than shipped broken.
_wanted = ((-1400, -1200, GROUND), (-600, 1200, GROUND),
           (1500, -1200, GROUND), (1500, 1200, GROUND),
           (-1400, -1200, L1), (-1400, 1200, L1), (1900, -600, L1),
           (600, 1200, L1),
           (-1400, -1200, L2), (-1400, 1200, L2), (1900, -600, L2))
_failed = [w for w in _wanted if not m.spawn(*w[:2], floor_z=w[2])]
if _failed:
    raise SystemExit(f"no room for spawns at {_failed}")

# ==================================================================== items
# Strongest gear in the atrium: taking it means standing in the open with two
# floors of balcony looking down at you.
m.pickup(items.SHIELD_BELT, 250, 0, GROUND)
m.pickup(items.weapon("rocket"), -200, -300, GROUND)
m.pickup(items.ammo("rocket"), -200, -150, GROUND)
m.pickup(items.ammo("rocket"), -200, 150, GROUND)
m.pickup(items.POWERUP_DAMAGE, 700, 300, GROUND)

for key, x, y, z in (("flakcannon", -1500, -1200, GROUND),
                     ("shockrifle", 1500, -1100, GROUND),
                     ("biorifle", -1000, 1200, GROUND),
                     ("minigun", -1700, 900, L1),
                     ("pulsegun", 1800, -1100, L1),
                     ("shockrifle", 800, 1200, L1),
                     ("sniper", -1700, -1200, L2),
                     ("ripper", 1900, 300, L2)):
    m.pickup(items.weapon(key), x, y, z)
    m.pickup(items.ammo(key), x + 160, y, z)

m.pickup(items.ARMOR_LARGE, -1900, -400, L2)
m.pickup(items.ARMOR_SMALL, 2000, 1200, GROUND)
m.pickup(items.JUMP_BOOTS, -1900, 1300, L1)
for x, y, z in ((-900, -1300, GROUND), (1700, 900, GROUND), (-1900, 300, L1),
                (1000, -1300, L1), (-900, 1300, L1), (-1900, 1300, L2),
                (1900, -1300, L2), (100, 900, GROUND)):
    m.pickup(items.HEALTH_SMALL, x, y, z)
for x, y, z in ((-1900, -900, GROUND), (2000, -1300, L1), (-600, 1300, L2)):
    m.pickup(items.HEALTH_LARGE, x, y, z)

# ================================================================= lighting
# UE1's LightRadius is not world units: Deck16's median light is brightness
# 128, radius 10. Radii in the 40+ range flood a whole floor to white.
def lightgrid(x0, x1, y0, y1, z, step=340, bright=150, radius=22):
    x = x0
    while x <= x1:
        y = y0
        while y <= y1:
            m.actor("Light", int(x), int(y), int(z),
                    LightBrightness=bright, LightRadius=radius)
            y += step
        x += step


for z in (GROUND, L1, L2):
    ceiling = z + CEIL_H - 40
    lightgrid(-1900, -500, -1400, 400, ceiling)        # west wing
    lightgrid(-1900, 300, 600, 1400, ceiling)          # south wing
    lightgrid(1000, 2100, -1400, 400, ceiling)         # east wing
    lightgrid(500, 2100, 600, 1400, ceiling)           # south-east wing

# The atrium is lit from its own ceiling and from each balcony level, so the
# shaft reads as daylit rather than as a dark hole.
lightgrid(-300, 800, -400, 400, TOP - 48, step=300, bright=210,
          radius=30)
for z in (GROUND + 260, L1 + 260):
    lightgrid(-300, 800, -400, 400, z, step=340, bright=170, radius=24)

# Stairwells and lift: dimmer, so the service routes feel different.
for sx in (-1800, 1000):
    for sz in (GROUND + 240, L1 + 240, L2 + 240):
        m.actor("Light", sx, -1260 if sx < 0 else 1040, sz,
                LightBrightness=165, LightRadius=24)
for lz in (GROUND + 240, L1 + 240, L2 + 240):
    m.actor("Light", LIFT_X + 150, LIFT_Y + 150, lz,
            LightBrightness=180, LightRadius=22)

# =================================================================== sound
# Stock maps carry 1-19 ambient sounds; with none, a level is silent apart
# from weapons and reads as unfinished. hum60 is mains hum, which is exactly
# what a floor of fluorescent lighting sounds like.
for z in (GROUND, L1, L2):
    m.sound(-1200, -500, z + 200, "AmbModern.Looping.hum60",
            radius=48, volume=90)
    m.sound(800, 900, z + 200, "AmbModern.Looping.hum60",
            radius=48, volume=80)
m.sound(1600, -1000, GROUND + 160, "AmbModern.Looping.beeps3",
        radius=40, volume=110)       # server room
m.sound(1600, -1000, GROUND + 200, "AmbModern.Looping.fan3",
        radius=36, volume=95)
m.sound(250, 0, GROUND + 300, "AmbModern.Looping.hum1",
        radius=64, volume=70)        # atrium
m.sound(LIFT_X + 150, LIFT_Y + 150, L1, "AmbModern.Looping.mach10",
        radius=32, volume=85)        # lift machinery
for i in range(3):                    # copy room
    m.sound(700 + i * 320, 1380, L1 + 120, "AmbModern.Looping.mach15",
            radius=24, volume=70)

# ================================================================ furniture
def prop(cls, x, y, z, yaw=0):
    """obj2mesh puts each model's base at mesh z=0, so the floor height IS the
    actor height. Any clearance and the furniture hovers."""
    m.actor(f"OfficeProps.{cls}", int(x), int(y), int(z),
            Rotation=f"(Yaw={int(yaw)})")


# A desk, chair and computer in every cubicle.
for gx in range(6):
    for gy in range(3):
        cx = -1900 + gx * (CUBE_W + 60) + CUBE_W // 2
        cy = 600 + gy * (CUBE_D + 50) + CUBE_D // 2
        prop("OfDesk", cx, cy + 40, L1, yaw=16384)
        prop("OfChair", cx, cy - 30, L1, yaw=49152)
        prop("OfMonitor", cx - 30, cy + 55, L1 + 46, yaw=16384)
        prop("OfKeyboard", cx + 35, cy + 28, L1 + 46, yaw=16384)

# Lobby: reception seating, plants, a waiting area.
prop("OfSofa", -1700, -700, GROUND, yaw=0)
prop("OfSofa", -1700, -200, GROUND, yaw=32768)
prop("OfCoffeeTable", -1700, -450, GROUND)
prop("OfChairPlain", -1300, -700, GROUND, yaw=16384)
for px, py in ((-1950, -1450), (-450, -1450), (-1950, 450), (350, 1450),
               (-1950, 1450)):
    prop("OfPlantTall", px, py, GROUND)

# Meeting room: a table run facing the whiteboard.
for i in range(4):
    prop("OfTableRound", 1400 + i * 180, -800, L1)
    prop("OfChairPlain", 1400 + i * 180, -650, L1, yaw=49152)
    prop("OfChairPlain", 1400 + i * 180, -950, L1, yaw=16384)
prop("OfPlantTall", 2100, -1450, L1)

# Open plan west: loose desks and a seating corner.
for i in range(4):
    prop("OfDesk", -1800 + i * 400, -600, L1, yaw=16384)
    prop("OfChair", -1800 + i * 400, -720, L1, yaw=49152)
    prop("OfMonitor", -1830 + i * 400, -585, L1 + 46, yaw=16384)
prop("OfSofa", -1800, -1300, L1, yaw=0)
prop("OfCoffeeTable", -1500, -1300, L1)
prop("OfCabinet", -1950, -1000, L1, yaw=16384)
prop("OfPlant", -700, -1400, L1)

# Executive: corner office, bookcases, and a boardroom that means business.
prop("OfDeskCorner", -1750, -1350, L2, yaw=8192)
prop("OfChair", -1750, -1180, L2, yaw=49152)
prop("OfBookcaseWide", -1950, -900, L2, yaw=16384)
prop("OfBookcase", -1950, -600, L2, yaw=16384)
prop("OfLamp", -1450, -1400, L2)
prop("OfSideTable", -1450, -1150, L2)
for i in range(5):
    prop("OfTableRound", -1600 + i * 200, 900, L2)
    prop("OfChairPlain", -1600 + i * 200, 1050, L2, yaw=49152)
    prop("OfChairPlain", -1600 + i * 200, 750, L2, yaw=16384)
for px, py in ((-1950, 1450), (300, 1450), (2100, 450)):
    prop("OfPlantTall", px, py, L2)

# ================================================================ bot paths
# One grid per open area at ~256 spacing (Deck16's median is 208).
for z in (GROUND, L1, L2):
    m.path_grid(-1900, -500, -1400, 400, z)
    m.path_grid(-1900, 300, 600, 1400, z)
    m.path_grid(1000, 2100, -1400, 400, z)
for z in (GROUND, L1):
    m.path_grid(500, 2100, 600, 1400, z)
# Atrium floor and the balcony ring, so bots use the vertical space.
m.path_grid(-300, 800, -400, 400, GROUND)
m.path_grid(AT_X0 - 150, AT_X1 + 150, AT_Y0 - 150, AT_Y1 + 150, L2,
            step=280)

# ================================================================== cameras
# A fixed viewpoint makes shots reproducible: a spectator otherwise spawns at a
# random PlayerStart facing whatever rotation it has. OFFICE_VIEW picks one.
VIEWS = [
    (-1750, -1150, GROUND + 58, 6000, -500),    # 0 lobby toward reception
    (-1750, 620, L1 + 150, 4000, -2600),        # 1 over the cubicle farm
    (1100, -800, L1 + 58, 32768, -500),         # 2 meeting room + whiteboard
    (-1850, -1400, L2 + 58, 6000, -700),        # 3 corner office
    (-1750, 500, L2 + 58, 12000, -900),         # 4 boardroom
    (250, 0, GROUND + 58, 0, 5000),             # 5 atrium looking up
    (1400, -1000, GROUND + 58, 30000, -300),    # 6 server room
    (AT_X1 + 120, 0, L2 + 58, 32768, -4500),    # 7 balcony over the atrium
    (-1500, 1000, GROUND + 58, 0, -200),        # 8 lobby south
    (900, 1000, GROUND + 58, 20000, -300),      # 9 loading bay
]

if "OFFICE_VIEW" in os.environ:
    _v = VIEWS[int(os.environ["OFFICE_VIEW"]) % len(VIEWS)]
    # Snap the camera to the nearest open spot: a viewpoint buried in a desk
    # or a cubicle partition fails the spawn and the screenshot comes back
    # stale rather than wrong, which is much harder to notice.
    _spot = m.clear_spot(_v[0], _v[1], _v[2] - m.START_HEIGHT - 8)
    if _spot is None:
        raise SystemExit(f"view {_v} has no open space near it")
    m.viewpoint(_spot[0], _spot[1], _spot[2], yaw=_v[3], pitch=_v[4])
else:
    m.camera(*VIEWS[0][:3], yaw=VIEWS[0][3], pitch=VIEWS[0][4])

if __name__ == "__main__":
    unr, log = m.build(paths=True)
    print("built:", unr)
    for line in stats(log):
        print("  ", line)
    if "--shot" in sys.argv:
        for p in tour("DM-QuarterlyReview", shots=3):
            print("  shot:", p)
