# Setup

## 1. Unreal Tournament

You need a real UT99 install — Steam, GOG, itch, or the original discs all
work. **Nothing from the game ships in this repo**; the toolkit reads whatever
copy you own.

Copying the install rather than using it in place is recommended, because the
toolkit writes maps into `Maps/` and a prop package into the game tree:

```bash
cp -r "/path/to/Unreal Tournament" ut/
```

## 2. The OldUnreal 469 patch

This is not optional. The stock 1999 build has no way to compile a map from the
command line; 469 adds `Editor.ExecCommandlet` and a native Linux `ucc`.

```bash
mkdir -p vendor && cd vendor
curl -LO https://github.com/OldUnreal/UnrealTournamentPatches/releases/download/v469e/OldUnreal-UTPatch469e-Linux-amd64.tar.bz2
cd ../ut && tar xjf ../vendor/OldUnreal-UTPatch469e-Linux-amd64.tar.bz2
chmod +x System64/ucc-bin-amd64 System64/ut-bin-amd64
```

Check the latest release tag first — `v469e` was current when this was written.

Optionally also fetch the SDK (`OldUnreal-UTPatch469e-SDK.tar.bz2`) into
`vendor/`. It is not needed to build maps, but it contains the complete engine
headers and UnrealScript sources, which are the reference for anything the
documentation here does not cover.

## 3. Tell the toolkit where things are

If you copied the game to `ut/` it is found automatically. Otherwise, either
set environment variables:

```bash
export UT99_DIR="$HOME/.steam/steam/steamapps/common/Unreal Tournament"
export KENNEY_DIR="$HOME/Downloads/kenney_furniture-kit/Models/OBJ format"
```

or write `ut99-mapgen.conf` in the repo root (gitignored):

```ini
UT99_DIR   = /home/you/games/UnrealTournament
UT99_PREFS = /home/you/.utpg
KENNEY_DIR = /home/you/assets/kenney_furniture-kit/Models/OBJ format
```

Verify:

```bash
python3 tools/paths.py
```

It prints every resolved path and marks any that are missing.

## 4. One-time game configuration

The Linux build defaults to the Windows viewport driver, which makes
`ucc exec` die with *"Can't find file for package WinDrv"*. Edit
`~/.utpg/System/UnrealTournament.ini` (created on the game's first run):

```ini
[Engine.Engine]
ViewportManager=SDLDrv.SDLClient

[SDLDrv.SDLClient]
StartupFullscreen=False
WindowedViewportX=1280
WindowedViewportY=720
```

Windowed mode matters for screenshots: fullscreen captures are unreliable.

## 5. Check it works

```bash
python3 tools/selftest.py
```

11 checks, each paired with a control that must fail. They take a few minutes
because several of them build real maps and read the results back out of the
compiled `.unr`.

---

# Regenerating what this repo does not ship

Several files are deliberately absent because they are derived from your game
install or from third-party art. All of them rebuild automatically or with one
command.

## The texture catalog — automatic

`work/textures.json` indexes every stock texture (name + pixel dimensions) by
parsing your own `.utx` packages. It is **built on first use**, takes about
0.2 seconds, and is gitignored.

```bash
python3 tools/textures.py --rescan     # force a rebuild
python3 tools/textures.py carpet       # search it
python3 tools/textures.py              # list packages
```

Rebuild it after installing a new texture pack. If it looks wrong, delete
`work/textures.json` and any command will regenerate it.

## The office textures — one command

The ten generated office textures (carpet, ceiling tile, cubicle fabric,
whiteboard, elevator doors, fluorescent panel) are written as 8-bit PCX by
`tools/pcx.py`. They are ours, not Epic's, but they are generated rather than
stored:

```bash
python3 tools/pcx.py ut/OfficeProps/Textures
```

Edit the generator functions in `tools/pcx.py` to change colours or patterns —
each is a small procedural drawing routine.

## The furniture props — needs the CC0 kit

The office map uses 16 models from Kenney's **Furniture Kit**, which is
[CC0 / public domain](https://kenney.nl/assets/furniture-kit). It is not
vendored here; download it yourself:

```bash
mkdir -p assets && cd assets
curl -LO https://kenney.nl/media/pages/assets/furniture-kit/kenney_furniture-kit.zip
unzip kenney_furniture-kit.zip
```

Then convert and compile the whole set into a UT99 package:

```bash
python3 tools/make_props.py --list     # what it will build
python3 tools/make_props.py            # convert, then ucc make
```

This writes `.3d` meshes and UnrealScript classes into
`ut/OfficeProps/`, generates the shared palette texture, and compiles
`OfficeProps.u` into your prefs directory.

Any CC0 OBJ works — edit the `PROPS` table in `tools/make_props.py` to add
models, giving each a target width in UT units (a player is 78 units tall).

## Screenshots — rendered on demand

`shots/` is gitignored because its contents are renders of your own install's
artwork. Regenerate any of them:

```bash
python3 maps/dm_crucible.py --shot          # build, then screenshot
OFFICE_VIEW=7 python3 maps/dm_quarterly.py  # pick a fixed camera, then:
python3 -c "import sys; sys.path.insert(0,'tools'); \
            from build import tour; print(tour('DM-QuarterlyReview')[0])"
```

Screenshots need `xdotool` and ImageMagick's `import`:

```bash
sudo apt install xdotool imagemagick     # or your distro's equivalent
```

## Blender addon — copy it in

```bash
cp blender/ut99_t3d.py ~/.config/blender/*/scripts/addons/
# Flatpak Blender:
cp blender/ut99_t3d.py \
   ~/.var/app/org.blender.Blender/config/blender/*/scripts/addons/
```

Then enable *UT99 T3D (Unreal Engine 1)* in Preferences → Add-ons. See
[BLENDER.md](BLENDER.md).

---

# Troubleshooting

**`Could not find a UT99 installation`** — set `UT99_DIR`, or check
`python3 tools/paths.py` for what it looked at.

**`No ucc-bin-amd64 under ...`** — the 469 patch is not applied, or was
extracted to the wrong place. It must land in `System64/` inside the game dir.

**`Can't find file for package WinDrv`** — set
`ViewportManager=SDLDrv.SDLClient`, step 4 above.

**`Can't find file for package <yours>`** on every map build — a broken
`EditPackages=` entry in the ini. Remove it if that package does not compile;
one bad entry breaks *all* later builds.

**Screenshots show the wrong map, or a map that failed to spawn** — a stale
game process is holding the display. UT99 only writes its log at exit, so the
log will still show the *previous* map. The tools `pkill` first; if you are
launching by hand, do the same.
