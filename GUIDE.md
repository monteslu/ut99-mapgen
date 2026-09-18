# Building a map

## The mental model

UT99 levels are **CSG**. The world starts as infinite solid rock. A *subtract*
brush carves a room out of it; an *add* brush puts solid back. So when you
write `box(...)` you are describing the **air** of a room, not its walls.

```python
m.add(box(-1024, -1024, 0, 1024, 1024, 384))            # a room
m.add(box(-128, -128, 0, 128, 128, 192, csg="CSG_Add"))  # a pillar in it
```

Order matters: brushes apply in the order you add them, so an add brush placed
before the room that contains it gets carved straight back out.

## Scale

Everything is in UT units. The numbers that matter, measured from
`DM-Deck16][`:

| | |
|---|---|
| player | 78 tall, 34 wide (collision height 39, radius 17) |
| comfortable ceiling | 320 |
| corridor | 256 wide |
| Deck16 overall | 3713 × 4076 × 1957 |
| Deck16's biggest room | 2048 × 1024 × 2048 |
| Deck16 median room height | 512 |
| Deck16 lights / starts | **231 / 15** |

A 1024-unit cube with one light is a texture swatch, not a level. Build big,
and light generously.

## A complete small map

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

from build import Map, stats, tour
from t3d import box
import items

m = Map("DM-Example")

# Geometry
m.add(box(-1024, -1024, 0, 1024, 1024, 384, name="Room", scale=2.0,
          floor="UTtech1.bmFloor", ceiling="UTtech1.nmceiling5",
          walls="UTtech1.bmwall3"))
m.add(box(-96, -96, 0, 96, 96, 200, name="Pillar",
          texture="UTtech1.bmTrim", csg="CSG_Add"))

# Gameplay
for x, y in ((-700, -700), (700, 700), (-700, 700), (700, -700)):
    m.player_start(x, y, floor_z=0)
m.pickup(items.weapon("flakcannon"), 400, 0, floor_z=0)
m.pickup(items.ammo("flakcannon"), 400, 150, floor_z=0)
m.pickup(items.HEALTH_LARGE, -400, 0, floor_z=0)

# Bots
m.path_grid(-900, 900, -900, 900, floor_z=0)

# Light
for x in range(-768, 769, 384):
    for y in range(-768, 769, 384):
        m.actor("Light", x, y, 300, LightBrightness=128, LightRadius=16)

unr, log = m.build(paths=True)
for line in stats(log):
    print(line)
```

Run it, then look at it:

```bash
python3 maps/my_map.py
python3 -c "import sys; sys.path.insert(0,'tools'); \
            from build import tour; print(tour('DM-Example')[0])"
```

---

# API

## `t3d.box(x0, y0, z0, x1, y1, z1, ...)`

An axis-aligned box brush.

| argument | meaning |
|---|---|
| `texture` | applied to every face, as `"Package.Texture"` |
| `floor`, `ceiling`, `walls` | override `texture` per surface |
| `scale` | how large the texture appears; `2.0` halves the tiling |
| `csg` | `"CSG_Subtract"` (default) or `"CSG_Add"` |
| `name` | shows up in build logs and validation errors |

Also in `t3d`: `stairs()` for a run of treads, `ramp()` for a stepped slope,
`arch()` for a doorway with an arched top, and the `Brush` / `Poly` classes if
you need geometry `box()` cannot express.

## `build.Map`

### Geometry
- `add(brush)` — append a brush; order is CSG order.

### Actors
- `player_start(x, y, floor_z, clearance=8)` — a spawn standing on the floor.
- `pickup(cls, x, y, floor_z)` — a weapon, ammo or powerup.
- `path_node(x, y, floor_z)` — one bot waypoint.
- `path_grid(x0, x1, y0, y1, floor_z, step=256)` — fill an area with
  waypoints, **skipping any that would land inside an added solid**. Returns
  how many it placed.
- `actor(cls, x, y, z, **props)` — any actor class, with UnrealScript
  properties (`LightBrightness=128`, `Rotation="(Yaw=16384)"`).
- `camera(x, y, z, yaw, pitch)` — a `SpectatorCam` viewpoint.
- `viewpoint(x, y, z, yaw, pitch)` — replaces **all** PlayerStarts with one, at
  a known facing, so screenshots are reproducible. Inspection only: it removes
  the spawns a real match needs.

### Building
- `check()` — returns a list of placement problems without building.
- `build(paths=False, lights=True, validate=True)` — compile to `.unr`.
  Returns `(path, log)`. Pass `paths=True` to run `PATHS BUILD`.

### Looking at the result
- `tour(name, shots=3)` — spectator, **bots forced off**, clean geometry shots.
- `screenshot(name)` — a live deathmatch with bots.
- `stats(log)` — pull the BSP numbers out of a build log.

## `items`

Verified UT99 class names — the naming is inconsistent enough (`ut_biorifle`,
`ripper`, `minigun2`, `Miniammo`) that guessing gets you silent no-ops.

```python
items.weapon("rocket")      # "UT_Eightball"
items.ammo("rocket")        # "RocketPack"
items.SHIELD_BELT           # "UT_ShieldBelt"
items.HEALTH_SMALL          # "HealthVial"
items.POWERUP_DAMAGE        # "UDamage"
```

Every name is checked by `selftest.py`, which reads the built map back and
asserts each class is present.

## `textures`

```bash
python3 tools/textures.py carpet     # search
```
```python
textures.find("floor")               # [(ref, (u, v)), ...]
textures.size("UTtech1.bmFloor")     # (256, 256)
textures.exists(ref)                 # used by Map.check()
```

## `decompile`

Read Epic's maps to see how they did it:

```bash
python3 tools/decompile.py "DM-Deck16]["   # -> work/DM-Deck16][.t3d
```

The `.t3d` is plain text: brushes, actors, every light and pickup with its
coordinates. This is the single best reference for "what numbers do real maps
use", and it is where every figure in the scale table above came from.

---

# Validation

`Map.check()` runs before every build. It catches the failure modes that
otherwise cost a full game launch each, because the engine reports them badly
or not at all:

- **A PlayerStart embedded in geometry** — UT99 aborts the entire game with
  `Failed to spawn player actor`, naming only one start per crash.
- **A PathNode inside an added solid** — no error at all; the node silently
  drops out of the path network, and enough of them takes bot navigation to
  zero while the map still builds and plays.
- **A misspelled texture** — no error; the face renders untextured and you find
  out by eye much later.

Note that PlayerStarts and PathNodes carry `NavigationPoint`'s collision
(radius 46, height 50), which is *fatter* than the player it spawns (17, 39).

## Checking bot navigation really worked

```bash
grep -E "Built Paths|Added [0-9]+ reachspecs" <build log>
```

`Built Paths: 0` means bots cannot navigate. For comparison, Deck16 produces
2881 walk reachspecs; the example office map produces ~8000.

---

# Common mistakes

**Nothing gets bigger when I add rooms.** Check the BSP node count across
builds. If it stays flat, your brushes are landing on top of each other.

**The map is dark, or blown out white.** `LightRadius` is *not* world units —
Deck16's median light is brightness 128, radius **10**. Radii in the 40+ range
flood a whole floor.

**Two floors merged into one space.** A tall room whose footprint overlaps the
floorplate above it carves straight through. Only a deliberate shaft should
span storeys.

**My prop is invisible.** Probably the camera. A spectator spawns at a randomly
chosen PlayerStart facing whatever rotation it has, so the same map shot twice
gives different views. Use `viewpoint()`.

[PIPELINE.md](PIPELINE.md) has the full list, with the engine-level reason for
each.
