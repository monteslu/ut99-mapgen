"""
make_props.py - turn Kenney CC0 furniture into a UT99 prop package.

Converts a list of .obj models into UE1 vertex meshes, generates one shared
palette texture holding every material colour used across them, writes the
UnrealScript classes, and compiles the lot with `ucc make`.

    python3 tools/make_props.py            # build everything in PROPS
    python3 tools/make_props.py --list     # just show what would be built

Kenney's Furniture Kit is CC0 (see its License.txt). The models carry no usable
UVs - they are coloured per MATERIAL - so each face is pointed at a solid cell
in the palette texture instead.
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import paths                                       # noqa: E402
from obj2mesh import (load_mtl, load_obj, uc_class,  # noqa: E402
                      write_mesh, write_palette)

ROOT = paths.ROOT
PKG = os.path.join(paths.game_dir(), "OfficeProps")
CLASSES = os.path.join(PKG, "Classes")
MODELS = os.path.join(PKG, "Models")
TEXTURES = os.path.join(PKG, "Textures")
SYSTEM64 = paths.system_dir()
UCC = paths.ucc()


def kenney():
    """Resolved on demand so the rest of the toolkit works without the kit."""
    return paths.kenney_dir()

# (class name, kenney obj, target width in UT units, collision radius/height)
#
# Sizes are chosen against the player: a UT99 player is 78 units tall with a
# 17-unit radius, so a desk about 120 wide and 45 high reads correctly, and a
# monitor is a small object on top of it.
PROPS = [
    ("OfDesk",       "desk.obj",             130, (34, 22)),
    ("OfDeskCorner", "deskCorner.obj",       150, (40, 22)),
    ("OfChair",      "chairDesk.obj",         55, (18, 26)),
    ("OfChairPlain", "chair.obj",             50, (16, 26)),
    ("OfMonitor",    "computerScreen.obj",    38, (14, 14)),
    ("OfKeyboard",   "computerKeyboard.obj",  40, (14,  3)),
    ("OfBookcase",   "bookcaseOpen.obj",      90, (26, 48)),
    ("OfBookcaseWide", "bookcaseClosedWide.obj", 120, (34, 40)),
    ("OfCabinet",    "kitchenCabinetDrawer.obj", 70, (22, 28)),
    ("OfPlant",      "plantSmall1.obj",       46, (16, 30)),
    ("OfPlantTall",  "pottedPlant.obj",       55, (18, 40)),
    ("OfSofa",       "loungeSofa.obj",       150, (44, 22)),
    ("OfTableRound", "tableRound.obj",        80, (28, 22)),
    ("OfCoffeeTable", "tableCoffee.obj",      90, (30, 16)),
    ("OfLamp",       "lampSquareFloor.obj",   40, (12, 46)),
    ("OfSideTable",  "sideTableDrawers.obj",  60, (20, 24)),
]

PALETTE = "OfPalette"


def collect_materials():
    """Every material used by the props, mapped to a palette slot."""
    colors, order = {}, []
    for _, obj, _, _ in PROPS:
        path = os.path.join(kenney(), obj)
        if not os.path.exists(path):
            continue
        mtl = load_mtl(path[:-4] + ".mtl")
        _, tris = load_obj(path)
        for tri in tris:
            name = tri[3]
            if name not in colors:
                colors[name] = mtl.get(name, (160, 160, 160))
                order.append(name)
    slots = {name: i for i, name in enumerate(order)}
    return colors, slots


def build(verbose=True):
    for d in (CLASSES, MODELS, TEXTURES):
        os.makedirs(d, exist_ok=True)

    colors, slots = collect_materials()
    pal = write_palette(colors, os.path.join(TEXTURES, f"{PALETTE}.pcx"))
    if verbose:
        print(f"palette: {len(colors)} materials -> {pal}")
        for n, c in colors.items():
            print(f"    {n:16} slot {slots[n]:2}  rgb{c}")

    made = []
    for name, obj, size, collision in PROPS:
        path = os.path.join(kenney(), obj)
        if not os.path.exists(path):
            print(f"  SKIP {name}: no {obj}")
            continue
        _, _, scale, tris, verts = write_mesh(
            path, name, MODELS, target_size=size, material_slots=slots)
        src = uc_class(name, scale, texture=f"{PALETTE}",
                       collision=collision)
        # The palette texture is imported into this package, so it must be
        # declared before the meshmap that references it.
        src = src.replace(
            "#exec MESHMAP NEW",
            f"#exec TEXTURE IMPORT NAME={PALETTE} "
            f"FILE=Textures\\{PALETTE}.pcx GROUP=Props\n#exec MESHMAP NEW")
        open(os.path.join(CLASSES, f"{name}.uc"), "w").write(src)
        made.append((name, tris, verts, scale))
        if verbose:
            print(f"  {name:16} {tris:5} tris {verts:4} verts  "
                  f"meshmap {scale[0]:.4f}/{scale[2]:.4f}")
    return made


def ensure_editpackage():
    """Add EditPackages=OfficeProps last, so Engine/Botpack resolve first."""
    INI = paths.ini()
    s = open(INI, encoding="latin-1", errors="replace").read()
    if "EditPackages=OfficeProps" in s:
        return False
    lines = s.split("\n")
    last = max(i for i, l in enumerate(lines)
               if l.startswith("EditPackages="))
    lines.insert(last + 1, "EditPackages=OfficeProps")
    open(INI, "w", encoding="latin-1", errors="replace").write(
        "\n".join(lines))
    return True


def compile_package():
    out = os.path.join(paths.prefs_dir(), "System", "OfficeProps.u")
    if os.path.exists(out):
        os.remove(out)
    ensure_editpackage()
    res = subprocess.run([UCC, "make"], cwd=SYSTEM64, capture_output=True,
                         text=True, timeout=1800)
    log = res.stdout + res.stderr
    if not os.path.exists(out):
        bad = [l for l in log.splitlines()
               if re.search(r"error|Error|Signal|fail", l)]
        raise SystemExit("compile failed:\n" + "\n".join(bad[-20:]))
    warns = [l.strip() for l in log.splitlines() if "Warning," in l]
    return out, warns


if __name__ == "__main__":
    if "--list" in sys.argv:
        for name, obj, size, _ in PROPS:
            ok = "ok " if os.path.exists(os.path.join(kenney(), obj)) else "MISS"
            print(f"{ok} {name:16} {obj:26} {size}u")
        raise SystemExit

    made = build()
    out, warns = compile_package()
    print(f"\ncompiled {out} ({os.path.getsize(out)//1024} KB), "
          f"{len(made)} props")
    for w in warns[:8]:
        print("  warn:", w)
