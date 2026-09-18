"""
textures.py - find stock UT99 textures by name and know how big they are.

The catalog is built from YOUR OWN UT99 install's .utx packages the first time
anything asks for it (about 0.2s for the full stock set) and cached in
work/textures.json, which is gitignored. Nothing derived from the game ships
in this repo - point it at your install and it indexes itself.

Rebuild explicitly with:  python3 tools/textures.py --rescan
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The cache lives in work/ (ignored) rather than beside the source, so a clone
# never carries an index of someone else's game files.
CATALOG = os.path.join(ROOT, "work", "textures.json")

_cache = None


def texture_dir():
    """Where the stock .utx packages live, from paths.game_dir()."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import paths
    return os.path.join(paths.game_dir(), "Textures")


def build_catalog():
    """Index every .utx in the install. Fast enough to do on demand."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from utx import scan
    cat = scan(texture_dir())
    os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
    with open(CATALOG, "w") as fh:
        json.dump(cat, fh, indent=0, sort_keys=True)
    return cat


def catalog():
    global _cache
    if _cache is None:
        if os.path.exists(CATALOG):
            with open(CATALOG) as fh:
                _cache = json.load(fh)
        else:
            _cache = build_catalog()
    return _cache


def find(term, package=None, limit=40):
    """Case-insensitive substring search. Returns [(ref, (u, v)), ...] where
    `ref` is the "Package.Texture" string a brush face wants."""
    term = term.lower()
    hits = []
    for pkg, texes in catalog().items():
        if package and pkg.lower() != package.lower():
            continue
        for name, size in texes.items():
            if term in name.lower():
                hits.append((f"{pkg}.{name}", tuple(size)))
    hits.sort()
    return hits[:limit]


def size(ref):
    """(usize, vsize) for a "Package.Texture" reference."""
    pkg, _, name = ref.partition(".")
    try:
        return tuple(catalog()[pkg][name])
    except KeyError:
        raise KeyError(f"unknown texture {ref!r}")


# Textures compiled into our own packages are not in the stock catalog.
EXTRA_PACKAGES = {"OfficeProps"}


def exists(ref):
    pkg, _, name = ref.partition(".")
    if pkg in EXTRA_PACKAGES:
        return True
    return name in catalog().get(pkg, {})


def packages():
    return sorted(k for k, v in catalog().items() if v)


if __name__ == "__main__":
    if "--rescan" in sys.argv:
        cat = build_catalog()
        print(f"{len(cat)} packages, "
              f"{sum(len(v) for v in cat.values())} textures -> {CATALOG}")
    elif len(sys.argv) > 1:
        for ref, (u, v) in find(sys.argv[1]):
            print(f"{ref:40} {u}x{v}")
    else:
        for p in packages():
            print(f"{p:20} {len(catalog()[p])}")
