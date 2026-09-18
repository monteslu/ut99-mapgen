"""
decompile.py - export an existing .unr back to .t3d so Blender can open it.

    python3 tools/decompile.py DM-Deck16][            # -> work/DM-Deck16][.t3d
    python3 tools/decompile.py DM-Codex out.t3d

Useful for studying how Epic built a room before trying to build one yourself.
The .t3d holds brushes and actors; it does not hold the built BSP, so a map
round-tripped this way must be rebuilt (which the build tools do anyway).
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build import MAPS, SYSTEM64, UCC, WORK      # noqa: E402


def decompile(map_name, out_path=None):
    if map_name.lower().endswith(".unr"):
        map_name = map_name[:-4]
    src = os.path.join(MAPS, f"{map_name}.unr")
    if not os.path.exists(src):
        raise SystemExit(f"no such map: {src}")

    os.makedirs(WORK, exist_ok=True)
    out_path = out_path or os.path.join(WORK, f"{map_name}.t3d")
    script = os.path.join(WORK, "_decompile.exec")
    with open(script, "w") as fh:
        fh.write(f'MAP LOAD FILE="{src}"\n')
        fh.write(f'MAP EXPORT FILE="{out_path}"\n')

    res = subprocess.run([UCC, "exec", script], cwd=SYSTEM64,
                         capture_output=True, text=True, timeout=900)
    if not os.path.exists(out_path):
        raise SystemExit((res.stdout + res.stderr)[-2000:])
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip())
    p = decompile(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    size = os.path.getsize(p)
    with open(p, encoding="latin-1", errors="replace") as fh:
        text = fh.read()
    print(f"{p}  ({size // 1024} KB)")
    print(f"  brushes {text.count('Class=Brush')}  "
          f"lights {text.count('Class=Light ')}  "
          f"starts {text.count('Class=PlayerStart')}")
