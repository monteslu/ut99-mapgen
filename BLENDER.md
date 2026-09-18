# Sculpting rooms in Blender

`blender/ut99_t3d.py` is an addon that imports and exports UE1 `.t3d` brush
geometry, so you can model a level by hand instead of writing coordinates.

## Install

```bash
cp blender/ut99_t3d.py ~/.config/blender/*/scripts/addons/
# Flatpak:
cp blender/ut99_t3d.py \
   ~/.var/app/org.blender.Blender/config/blender/*/scripts/addons/
```

Enable **UT99 T3D (Unreal Engine 1)** in Preferences → Add-ons. It adds
`File ▸ Import/Export ▸ Unreal T3D (.t3d)` and a **UT99 Brush** panel in object
properties.

## The one thing to internalise

**Model the air, not the walls.** UE1 starts as solid rock and you carve rooms
out of it, so a cube in Blender becomes a *room*, not a block. A room's walls
are whatever is left over between the volumes you carve.

Set each object's role in the **UT99 Brush** panel:

| property | meaning |
|---|---|
| CSG | *Subtract* carves a room (default); *Add* puts solid back, for pillars and ledges |
| Texture | `Package.Texture` for faces with no material |
| Tex Scale | how large the texture appears; 2 halves the tiling |

A material named `ShaneChurch.BrownWall` sets that face's texture, so you can
mix several textures on one object.

## Units

1 Blender metre = 16 UT units, so:

| | metres | UT units |
|---|---|---|
| player height | 4.9 | 78 |
| corridor | 16 | 256 |
| comfortable ceiling | 20 | 320 |
| a decent room | 64 × 64 | 1024 × 1024 |

Change `UT_SCALE` in the addon, or the *UT units per metre* field in the
import/export dialog, if you prefer a different ratio.

## Convex only

UE1's CSG needs convex brushes. The exporter **refuses** concave meshes rather
than letting the engine build sealed-looking geometry with holes in the BSP.
Split an L-shaped room into two boxes instead.

## Round trip

```bash
# Model, then File ▸ Export ▸ Unreal T3D
python3 tools/from_blender.py scene.t3d DM-MyMap --shot
```

`from_blender.py` adds what a `.t3d` cannot carry (PlayerStarts and a light
grid sized from the rooms themselves) then compiles and optionally screenshots
it.

## Reading Epic's maps

The import direction is the more useful one. Decompile any stock map and open
it:

```bash
python3 tools/decompile.py "DM-Deck16]["
# then File ▸ Import ▸ Unreal T3D on work/DM-Deck16][.t3d
```

Deck16 comes back as 187 editable brushes. Subtracted rooms are displayed as
wireframe so you can see the space they enclose rather than a wall of solid
cubes.

## Headless

The addon's functions work under `blender --background`:

```bash
blender --background --python blender/test_roundtrip.py
```

That builds a room and a pillar, exports them, and checks that a deliberately
concave mesh is rejected. Flatpak Blender needs `--filesystem=home` and an
**absolute** script path.
