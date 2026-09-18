"""
paths.py - where everything lives, with nothing hardcoded.

Every path the toolkit needs resolves through here, in this order:

  1. an environment variable      (UT99_DIR, UT99_PREFS, KENNEY_DIR)
  2. a local config file          (ut99-mapgen.conf, gitignored)
  3. a list of usual suspects     (Steam, GOG, itch, /usr/games, ./ut)

Nothing in this repo is tied to one machine or one user's home directory, so a
clone works anywhere the game is installed.
"""

import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "ut99-mapgen.conf")

# Where a UT99 install might be. `~` and env vars are expanded before use.
GAME_CANDIDATES = [
    os.path.join(ROOT, "ut"),
    "~/.steam/steam/steamapps/common/Unreal Tournament",
    "~/.local/share/Steam/steamapps/common/Unreal Tournament",
    "~/snap/steam/common/.local/share/Steam/steamapps/common/Unreal Tournament",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/"
    "common/Unreal Tournament",
    "~/GOG Games/Unreal Tournament",
    "~/Games/UnrealTournament",
    "/usr/share/games/ut",
    "/opt/UnrealTournament",
]

# The OldUnreal Linux build keeps its config and compiled packages here rather
# than in the game tree.
PREFS_CANDIDATES = ["~/.utpg"]

KENNEY_CANDIDATES = [
    os.path.join(ROOT, "assets", "kenney_furniture-kit", "Models", "OBJ format"),
    os.path.join(ROOT, "assets", "furniture-kit", "Models", "OBJ format"),
    "~/Downloads/kenney_furniture-kit/Models/OBJ format",
    # The all-in-one bundle nests kits under a versioned folder; the glob in
    # _search() copes with the version varying.
    "~/Downloads/Kenney Game Assets*/3D assets/Furniture Kit/Models/OBJ format",
]

_config = None


def config():
    """key=value pairs from ut99-mapgen.conf, if present."""
    global _config
    if _config is None:
        _config = {}
        if os.path.exists(CONFIG):
            for line in open(CONFIG, encoding="utf-8"):
                line = line.split("#", 1)[0].strip()
                if "=" in line:
                    k, _, v = line.partition("=")
                    _config[k.strip().upper()] = v.strip()
    return _config


def _search(candidates, marker=None):
    """First candidate that exists (and contains `marker`, if given)."""
    import glob

    for cand in candidates:
        for path in sorted(glob.glob(os.path.expanduser(cand))):
            if marker and not os.path.exists(os.path.join(path, marker)):
                continue
            if os.path.isdir(path):
                return os.path.abspath(path)
    return None


def _resolve(env_var, conf_key, candidates, marker, what, hint):
    explicit = os.environ.get(env_var) or config().get(conf_key)
    if explicit:
        path = os.path.abspath(os.path.expanduser(explicit))
        if marker and not os.path.exists(os.path.join(path, marker)):
            raise SystemExit(
                f"{env_var}={path} does not look like {what}: "
                f"expected to find {marker!r} inside it")
        return path
    found = _search(candidates, marker)
    if found:
        return found
    raise SystemExit(
        f"Could not find {what}.\n"
        f"Set {env_var}=/path/to/it, or add\n"
        f"    {conf_key} = /path/to/it\n"
        f"to {CONFIG}\n{hint}")


def game_dir():
    """The UT99 install: the directory containing System/, Maps/, Textures/."""
    return _resolve(
        "UT99_DIR", "UT99_DIR", GAME_CANDIDATES, "Textures",
        "a UT99 installation",
        "You need UT99 (any edition) plus the OldUnreal 469 patch; see "
        "SETUP.md.")


def prefs_dir():
    """Where the OldUnreal Linux build keeps its ini and compiled packages."""
    explicit = os.environ.get("UT99_PREFS") or config().get("UT99_PREFS")
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    found = _search(PREFS_CANDIDATES, "System")
    # Not an error if absent: the game creates it on first run.
    return found or os.path.expanduser("~/.utpg")


def system_dir():
    """The directory holding ucc-bin-amd64 and ut-bin-amd64 (System64), or
    the Windows System/ if that is all there is."""
    game = game_dir()
    for name in ("System64", "System"):
        path = os.path.join(game, name)
        if os.path.exists(os.path.join(path, "ucc-bin-amd64")):
            return path
    raise SystemExit(
        f"No ucc-bin-amd64 under {game}. The OldUnreal 469 Linux patch "
        f"provides it - see SETUP.md.")


def ucc():
    return os.path.join(system_dir(), "ucc-bin-amd64")


def ut_binary():
    return os.path.join(system_dir(), "ut-bin-amd64")


def ini():
    return os.path.join(prefs_dir(), "System", "UnrealTournament.ini")


def maps_dir():
    return os.path.join(game_dir(), "Maps")


def kenney_dir():
    """Kenney's Furniture Kit (CC0). Only needed to rebuild the props."""
    return _resolve(
        "KENNEY_DIR", "KENNEY_DIR", KENNEY_CANDIDATES, None,
        "Kenney's Furniture Kit",
        "Download the CC0 kit from https://kenney.nl/assets/furniture-kit "
        "and unzip it into assets/, or set KENNEY_DIR to wherever it is.")


def work_dir():
    path = os.path.join(ROOT, "work")
    os.makedirs(path, exist_ok=True)
    return path


def shots_dir():
    path = os.path.join(ROOT, "shots")
    os.makedirs(path, exist_ok=True)
    return path


if __name__ == "__main__":
    print(f"repo root  {ROOT}")
    for name, fn in (("game", game_dir), ("system", system_dir),
                     ("prefs", prefs_dir), ("ini", ini),
                     ("maps", maps_dir), ("kenney", kenney_dir)):
        try:
            value = fn()
            mark = "" if os.path.exists(value) else "   (missing)"
            print(f"{name:10} {value}{mark}")
        except SystemExit as err:
            print(f"{name:10} NOT FOUND - {str(err).splitlines()[0]}")
