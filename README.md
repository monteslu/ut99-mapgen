# ut99-mapgen

Build Unreal Tournament 99 maps from Python or Blender, compile them with no
GUI, and look at the result in the real game. Linux, no Wine, no UnrealEd.

```python
from build import Map
from t3d import box

m = Map("DM-Foo")
m.add(box(-1280, -1024, 0, 1280, 1024, 1024,       # carve a room
          floor="UTtech1.bmFloor", walls="UTtech1.bmwall3"))
m.add(box(-128, -128, 0, 128, 128, 640,            # add a pillar
          texture="UTtech1.bmTrim", csg="CSG_Add"))
m.player_start(-960, -768, floor_z=0)
m.pickup("UT_FlakCannon", 400, 0, floor_z=0)
m.path_grid(-1100, 1100, -900, 900, floor_z=0)     # bot waypoints
m.actor("Light", 0, 0, 900, LightBrightness=128, LightRadius=16)

m.build(paths=True)                                 # -> DM-Foo.unr
```

## Why this exists

The received wisdom is that UT99 map compilation is UnrealEd-only: import a
`.t3d`, rebuild BSP and save a `.unr` are GUI operations with no command-line
equivalent. That is true of the stock 1999 build.

It is **not** true of [OldUnreal's 469 patch](https://github.com/OldUnreal/UnrealTournamentPatches),
which added `Editor.ExecCommandlet`:

```
ucc exec <file>     # "Executes a command file in a minimal editor environment"
```

That runs the full UnrealEd exec command set headlessly, on a native Linux
binary. Everything here is built on it.

## What it does

| | |
|---|---|
| **Geometry** | CSG brushes from Python, or sculpted in Blender and exported as `.t3d` |
| **Textures** | search your install's ~4800 stock textures; generate new ones as 8-bit PCX |
| **Props** | convert CC0 OBJ models into UE1 vertex meshes (UT99 has no static meshes) |
| **Gameplay** | weapons, ammo, pickups, PlayerStarts, and `PATHS BUILD` bot navigation |
| **Verification** | screenshot any map from a fixed camera; decompile Epic's maps to study them |

## Quick start

You need a UT99 install and the OldUnreal 469 Linux patch. See
**[SETUP.md](SETUP.md)**, which also covers regenerating everything this repo
deliberately does not ship.

```bash
python3 tools/paths.py          # check it found your install
python3 tools/selftest.py       # 11 checks, each with a control that must fail
python3 maps/dm_crucible.py     # build the example deathmatch map
```

## Documentation

- **[SETUP.md](SETUP.md)**: install, configure, regenerate generated files
- **[GUIDE.md](GUIDE.md)**: how to build a map, with the API reference
- **[PIPELINE.md](PIPELINE.md)**: how the engine internals actually work, and
  the bugs that cost real debugging time
- **[BLENDER.md](BLENDER.md)**: sculpting rooms in Blender

## Example maps

`maps/` holds four worked examples, roughly in order of complexity:

| map | what it demonstrates |
|---|---|
| `dm_arena.py` | two rooms, a corridor, a pillar |
| `dm_foundry.py` | multi-storey layout, shafts, light grids |
| `dm_crucible.py` | full deathmatch: stairs, cover, weapon placement, bot paths |
| `dm_quarterly.py` | a three-floor office complex with custom textures and props |

## What this repo does *not* contain

No Unreal Tournament content. No Epic Games assets, binaries, texture data or
map files. You bring your own legally-obtained copy of the game; the toolkit
reads it, indexes it, and writes new maps into it.

The Kenney furniture used by the office map is [CC0](https://kenney.nl/assets/furniture-kit)
and downloaded separately, not vendored.

## Requirements

- Linux, Python 3.9+ (no third-party packages required)
- Unreal Tournament (any edition) + [OldUnreal 469 patch](https://github.com/OldUnreal/UnrealTournamentPatches/releases)
- Optional: Blender 3.3+ for the modelling workflow
- Optional: `xdotool` and ImageMagick's `import` for screenshots

## Licence

MIT. See [LICENSE](LICENSE). This covers the toolkit only, not the game it
drives or any art you point it at.
