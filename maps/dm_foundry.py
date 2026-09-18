"""DM-Foundry - a playable-scale deathmatch map.

Sized against the real thing: DM-Deck16][ spans roughly 3700 x 4000 x 1950
world units, its largest rooms reach 2048 x 1024 x 2048, its median room height
is 512, and it carries 231 lights and 15 PlayerStarts. A single 1024-cube room
with one light is a texture swatch, not a level, so this lays out four connected
spaces on two heights at that real scale.

Layout (viewed from above, X east / Y south):

    +----------------+        +--------------+
    |                |        |              |
    |   MAIN HALL    |=======>|   ANNEX      |
    |  2560x2048     | bridge |  1536x1536   |
    |   h=1024       |        |   h=768      |
    +--------+-------+        +------+-------+
             |                       |
             | ramp down             | corridor
             v                       v
    +--------+-----------------------+-------+
    |            LOWER GALLERY               |
    |            3584 x 1024  h=512          |
    +----------------------------------------+
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

from build import Map, stats, screenshot          # noqa: E402
from t3d import box                               # noqa: E402

# One coherent texture set, scaled up so it does not tile like graph paper.
FLOOR = "ShaneChurch.BrownFloor"
WALL = "ShaneChurch.BrownWall"
CEIL = "ShaneChurch.Celing2"
TRIM = "ShaneChurch.BrownTrim"

m = Map("DM-Foundry")

# ---------------------------------------------------------------- upper level
# Main hall: the big central arena, tall enough for lift/rocket fights.
m.add(box(-1280, -1024, 0, 1280, 1024, 1024, name="MainHall", scale=4.0,
          floor=FLOOR, ceiling=CEIL, walls=WALL))

# Annex: a smaller, lower side room east of the hall.
m.add(box(2048, -768, 0, 3584, 768, 768, name="Annex", scale=4.0,
          floor=FLOOR, ceiling=CEIL, walls=WALL))

# Bridge joining hall to annex, wide enough for two players to pass.
m.add(box(1280, -192, 0, 2048, 192, 384, name="Bridge", scale=3.0,
          floor=FLOOR, ceiling=CEIL, walls=TRIM))

# ---------------------------------------------------------------- lower level
# Gallery runs the full width underneath both upper rooms.
m.add(box(-1280, 1024, -768, 2304, 2048, -256, name="Gallery", scale=4.0,
          floor=FLOOR, ceiling=CEIL, walls=WALL))

# Two shafts drop from the upper rooms into the gallery. Each is a full-height
# subtract so the floor above genuinely opens into the space below.
m.add(box(-768, 640, -768, -256, 1408, 1024, name="ShaftWest", scale=3.0,
          floor=FLOOR, ceiling=CEIL, walls=TRIM))
m.add(box(1536, 640, -768, 2048, 1408, 768, name="ShaftEast", scale=3.0,
          floor=FLOOR, ceiling=CEIL, walls=TRIM))

# ------------------------------------------------------------------ structure
# Cover in the main hall: two pillars, stopping short of the ceiling.
for px in (-640, 640):
    m.add(box(px - 128, -128, 0, px + 128, 128, 640, name=f"Pillar{px}",
              scale=2.0, texture=TRIM, csg="CSG_Add"))

# A low block in the annex to break sightlines.
m.add(box(2688, -192, 0, 3072, 192, 256, name="AnnexBlock", scale=2.0,
          texture=TRIM, csg="CSG_Add"))

# --------------------------------------------------------------------- actors
# 10 starts spread across all three areas (Deck16 ships 15).
for x, y in [(-960, -768), (-960, 768), (960, -768), (960, 768), (0, 0)]:
    m.player_start(x, y, floor_z=0)
for x, y in [(2304, -512), (3328, 512), (3328, -512)]:
    m.player_start(x, y, floor_z=0)
for x, y in [(-960, 1536), (1920, 1536)]:
    m.player_start(x, y, floor_z=-768)

# Lighting. Stock maps use hundreds of lights; a sparse grid per room keeps the
# space readable instead of one hotspot in a black void.
def grid(x0, x1, y0, y1, z, step=640, bright=170, radius=72):
    x = x0
    while x <= x1:
        y = y0
        while y <= y1:
            m.actor("Light", int(x), int(y), int(z),
                    LightBrightness=bright, LightRadius=radius)
            y += step
        x += step

grid(-1024, 1024, -768, 768, 832)            # main hall
grid(2304, 3328, -512, 512, 640)             # annex
grid(-1024, 2048, 1280, 1792, -384)          # lower gallery
grid(1408, 1920, -64, 64, 320, step=512)     # bridge
for x, y in [(-512, 1024), (1792, 1024)]:    # shafts
    m.actor("Light", x, y, 640, LightBrightness=200, LightRadius=80)

if __name__ == "__main__":
    unr, log = m.build()
    print("built:", unr)
    for line in stats(log):
        print("  ", line)
    print("lights:", sum(1 for a in m.actors if a[0] == "Light"),
          "starts:", sum(1 for a in m.actors if a[0] == "PlayerStart"))
    if "--shot" in sys.argv:
        print("shot:", screenshot("DM-Foundry"))
