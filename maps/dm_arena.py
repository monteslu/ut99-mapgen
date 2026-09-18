"""DM-Arena - a two-room test map that exercises the whole toolkit:
multi-brush CSG (rooms + connecting corridor), an added solid pillar,
textures from a stock package, lights, and several player starts.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

from build import Map, stats, screenshot          # noqa: E402
from t3d import box                               # noqa: E402

WALL = "ShaneChurch.BrownWall"
FLOOR = "ShaneChurch.BrownFloor"

m = Map("DM-Arena")
m.use_textures("ShaneChurch")

# Two rooms carved out of solid space, joined by a corridor.
m.add(box(-1024, -1024, -256, 1024, 1024, 320, texture=FLOOR, name="RoomA"))
m.add(box(1536, -512, -256, 3072, 512, 320, texture=FLOOR, name="RoomB"))
m.add(box(1024, -160, -256, 1536, 160, 128, texture=WALL, name="Hall"))

# A solid pillar added back into room A for cover. It stops short of the
# ceiling: a brush spanning the room's full height would re-seal the space and
# leave the spawns embedded in solid geometry.
m.add(box(-160, -160, -256, 160, 160, 128, texture=WALL, name="Pillar",
          csg="CSG_Add"))

# Spread the starts out so bots do not telefrag each other on spawn.
# player_start() lifts each one clear of the floor; m.check() then verifies the
# collision cylinder actually fits in the room before we spend a launch on it.
for x, y in [(-700, -700), (-700, 700), (700, 700)]:
    m.player_start(x, y, floor_z=-256)
for x, y in [(2600, -250), (2600, 250)]:
    m.player_start(x, y, floor_z=-256)

for x, y, z in [(-500, -500, 200), (500, 500, 200), (0, 0, 280),
                (2300, 0, 200), (1280, 0, 80)]:
    m.actor("Light", x, y, z, LightBrightness=200, LightRadius=40)

if __name__ == "__main__":
    unr, log = m.build()
    print("built:", unr)
    for line in stats(log):
        print("  ", line)
    if "--shot" in sys.argv:
        print("shot:", screenshot("DM-Arena"))
