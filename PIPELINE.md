# Engine notes

How UT99's editor actually behaves, and the bugs that cost real debugging time.
For getting started see [SETUP.md](SETUP.md); for the API see
[GUIDE.md](GUIDE.md).

## The key discovery
OldUnreal 469e ships `ucc exec <file>` - "Executes a command file in a minimal
editor environment". That gives the full UnrealEd exec command set headlessly.
Web research says this is impossible ("GUI-only, no commandlet replaces it") -
true for the stock v436 build, false for 469, which added
`Editor.ExecCommandlet`.

## Layout
- `tools/` the toolkit
- `blender/` Blender addon + headless test
- `maps/` example map sources
- `ut/` your UT99 install + the 469 patch (gitignored; see SETUP.md)
- `vendor/` OldUnreal SDK + Linux tarballs (gitignored, downloaded)
- `work/`, `shots/` scratch and screenshots (gitignored, regenerated)

## Scale
All measured by decompiling `DM-Deck16][` rather than guessed - see the table
in [GUIDE.md](GUIDE.md). The short version: world span ~3700 x 4000 x 1950,
biggest room 2048 x 1024 x 2048, median room height 512, **231 lights**.

## Gotchas, each one cost real debugging time
- **`ACTOR ADD CLASS=.. XPOS=.. YPOS=.. ZPOS=..` IGNORES the coordinates.**
  It drops the actor at the editor's current add-location (where you last
  clicked in UnrealEd) and logs "Added actor ... successfully" regardless, so
  every light, item, PlayerStart and prop ends up stacked on the origin with
  no Location property at all. Actors must go in via `MAP IMPORTADD` of a .t3d
  that carries explicit `Location=(X=..,Y=..,Z=..)` lines. This one is
  especially nasty because a map full of origin-stacked lights still looks
  *plausibly* lit, and a prop sitting on top of the camera reads as "my mesh
  scale is wrong" rather than "my actor never moved".
- **`LevelInfo AmbientBrightness` is the biggest lever on how a map looks.**
  Left unset, every surface renders near its full texture brightness and the
  level is flat and washed out however carefully you place lights or however
  dark you author the textures. Epic's DM-Codex sets 6 and renders at a mean
  RGB of (54,46,34); the same office map with no ambient set rendered
  (137,146,166) and with `AmbientBrightness=8` rendered (56,63,67).
  Set it with `m.level_info(AmbientBrightness=8)` - note `MAP SETLEVELINFO`
  looks like the right exec verb and reports Success but is a silent no-op;
  the working route is `MAP IMPORTADD` of a LevelInfo with the same name.
- **Movers work headlessly.** A brush actor of class `Mover` with `KeyPos(1)`
  gives doors and lifts; they appear as `MoverNodes` in the build log rather
  than adding to the static count. Stock maps carry 1-7 of them.
- **UE1 `LightRadius` is NOT world units.** Deck16's median light is
  brightness 128, radius **10**; radii in the 40-50 range flood a whole floor
  and blow every surface to white. Match Epic: ~128 brightness, 12-24 radius,
  lights every ~380 units.
- **Overlapping Z between floors merges them.** A double-height room whose
  footprint sits under the next storey's floorplate carves straight through it
  and the two become one void - the "ground floor" turns into a pit under an
  open mezzanine. Only a deliberate shaft (an atrium) should span storeys.
- **Screenshots need a fixed viewpoint.** A spectator spawns at a randomly
  chosen PlayerStart facing whatever rotation it has, so the same map shot
  twice gives different views and "my prop is invisible" is often "the camera
  was pointed at a wall". Use `m.viewpoint(x, y, z, yaw=..)` - a single start
  with explicit rotation.
- **`BRUSH IMPORT` ignores the actor's `Location`.** Vertices must be in WORLD
  space with Location left at zero. Position a brush via Location and every
  room carves at the origin instead - the map still builds, still reports
  believable numbers, and its BSP node count simply never grows as you add
  rooms. (A saved `.unr` *does* store per-brush Location; that is how UnrealEd
  tracks brushes you dragged, but it is not how geometry is imported.)
- **`CSG_Add` uses the SAME normals-out winding as subtract.** Epic's own added
  brushes in Deck16 are wound exactly like their subtracts. Reversing it builds
  inside-out solids: node count collapses and `PATHS BUILD` returns *zero*
  reachspecs, so bots have no navigation while the map still looks fine.
  `tools/selftest.py` checks pathing with cover present for this reason.
- **A PathNode inside an added solid is not an error** - it silently drops out
  of the path network, and enough of them takes bot navigation to zero. Use
  `m.path_grid()`, which skips blocked nodes; `m.check()` also rejects them.
- **Stair treads must be wider than a PathNode's radius.** A node carries
  NavigationPoint's 46-unit radius, so on an 80-unit tread its cylinder always
  clips the next step and drops out. 160-unit treads path reliably.
- **A stale `ut-bin-amd64` fakes a spawn failure.** UT99 only writes its log at
  exit, so a hung instance leaves the *previous* map's crash in the log while
  new launches silently get no window. `pkill -9` before every launch (the
  tools do). This cost the most time by far - it disguised itself as an
  imaginary "minimum room size" rule.
- **PlayerStart collision is fatter than the pawn**: NavigationPoint is radius
  46 / height 50 vs the player's 17 / 39. `m.check()` validates before a launch
  is wasted; `player_start()` lifts starts clear of the floor.
- **A misspelled texture is not a build error** - the face just renders
  untextured and you find out by eye much later. `m.check()` rejects unknown
  texture names.
- **Bot count comes from the ini, not the URL.** `?numbots=0` alone still fills
  the level; `tour()` sets `[Botpack.DeathMatchPlus] InitialBots` and restores it.
- **`ViewportManager=WinDrv.WindowsClient`** in `~/.utpg/System/UnrealTournament.ini`
  makes `ucc exec` die with "Can't find file for package WinDrv". Use
  `SDLDrv.SDLClient`.
- xdotool key injection does **not** reach the SDL/Wayland window, so in-game
  `SHOT` and `-exec=` cannot be triggered externally. `import -window` works.
- Flatpak Blender needs `--filesystem=home` and an **absolute** script path.

## Verifying
- structural: `ut/System64/ucc-bin-amd64 packagedump <map>.unr`
- visual: `tour(name, shots=3)` - spectator, no bots, clean geometry shots
- gameplay: `screenshot(name)` - live deathmatch with bots

## Custom textures (tools/pcx.py)

Stock UT99 has no ceiling tiles, office carpet or whiteboards, and the CC0
libraries ship 1K+ photos that would need downscaling and palette-reducing
anyway - so these are generated directly as 8-bit PCX, which also sidesteps
every licensing question:

    python3 tools/pcx.py work/textures     # 10 office textures

UT99 imports ONLY 8-bit indexed PCX/BMP and does NOT quantise for you.
Dimensions must be powers of two; above 256x256 needs mipmaps or the game
crashes, so everything here is 256x256 or smaller. Palette index 0 is UE1's
transparent colour, so opaque pixels always start at index 1.

## Props from Kenney CC0 models (tools/obj2mesh.py)

UT99 has no static meshes (those arrived in UT2003). Props are *vertex meshes*
- the same format as players and weapons - imported at COMPILE time by an
`#exec MESH IMPORT` line in an UnrealScript class. A one-frame animation makes
a perfectly good static prop.

    python3 tools/obj2mesh.py path/to/desk.obj OfficeDesk ut/OfficeProps/Models
    # then add EditPackages=OfficeProps (LAST) and run ucc-bin-amd64 make

Verified working end to end with Kenney's Furniture Kit (CC0): desk, chairDesk,
computerScreen, bookcases, plants - 140 models at 18-292 verts each.

Format gotchas, all of which cost real time:
- **The `_d.3d` header is 48 bytes, not 12.** Only the first 4 (NumPolys,
  NumVerts) are read, but a short header shifts every triangle record and
  SEGFAULTS the importer inside `meshLODProcess` with no error message.
- Triangles are 16 bytes in the FILE (`3 x uint16 idx, type, colour, 6 UV
  bytes, texnum, flags`) - different from the 20-byte in-memory `FMeshTri`.
- Vertices pack into one DWORD X:11 Y:11 Z:10 signed, low to high, with FIXED
  scale factors: X/Y stored at 8x, Z at 4x. That caps a mesh at +-128 units
  per axis; going past wraps silently rather than erroring.
- `MLOD=0` disables the LOD collapse pass, worth setting while debugging.
- `Mesh=Mesh'Package.Name'` in defaultproperties, not a bare `Mesh=Name`, or
  the actor spawns and renders nothing.
- **Size a prop with `#exec MESHMAP SCALE`, not `DrawScale`.** The engine uses
  the RAW packed field values as mesh units, so the meshmap scale has to undo
  the format's own 8x (X/Y) and 4x (Z) packing. That is why Z always comes out
  twice X/Y - every stock mesh in the SDK is `X=0.1 Y=0.1 Z=0.2`.
- **Kenney models have no usable UVs.** Their `vt` values are world-scale
  (tens of units) because the models are coloured per MATERIAL. `make_props.py`
  builds one palette texture of solid cells and points every face at its own
  material's cell, which is why the desks come out wood-coloured rather than
  flat grey.
- A broken `EditPackages=` entry makes EVERY later map build fail with
  "Can't find file <pkg>" - remove it if the package does not compile.
- The compiled .u lands in `~/.utpg/System/`, not the game tree.
