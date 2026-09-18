"""
build.py - drive the headless UT99 map pipeline.

Each brush must be imported and applied as its own CSG operation, in order:
UE1's editor holds exactly one "builder brush" at a time, so the exec script is
a sequence of IMPORT / SUBTRACT-or-ADD pairs rather than one bulk import.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths as _paths                                # noqa: E402

ROOT = _paths.ROOT
# Resolved lazily through tools/paths.py so nothing here assumes a particular
# install location; see SETUP.md for how to point it at yours.
SYSTEM64 = _paths.system_dir()
UCC = _paths.ucc()
UT = _paths.ut_binary()
WORK = _paths.work_dir()
MAPS = _paths.maps_dir()
SHOTS = _paths.shots_dir()


class Map:
    """Accumulates brushes and actors, then builds them into a .unr."""

    def __init__(self, name):
        self.name = name
        self.brushes = []
        self.actors = []
        self.texture_packages = []

    def add(self, brush):
        self.brushes.append(brush)
        return brush

    # A PlayerStart inherits NavigationPoint's collision (radius 46, height 50),
    # which is fatter than the pawn it spawns (radius 17, height 39). If that
    # cylinder intersects a wall or floor the spawn fails and the game aborts
    # with "Failed to spawn player actor" rather than nudging the start.
    START_RADIUS = 46
    START_HEIGHT = 50

    def actor(self, cls, x, y, z, **props):
        self.actors.append((cls, x, y, z, props))

    def player_start(self, x, y, floor_z, clearance=8):
        """Place a PlayerStart sitting on `floor_z` with its collision clear."""
        self.actor("PlayerStart", x, y,
                   floor_z + self.START_HEIGHT + clearance)

    # Pickups rest on the floor rather than at its exact plane; Epic's maps sit
    # them a little above it so they do not z-fight or fall through.
    PICKUP_CLEARANCE = 40

    def pickup(self, cls, x, y, floor_z, clearance=None):
        """Place a weapon, ammo or powerup standing on `floor_z`."""
        if clearance is None:
            clearance = self.PICKUP_CLEARANCE
        self.actor(cls, x, y, floor_z + clearance)

    def path_node(self, x, y, floor_z, clearance=58):
        """A bot navigation waypoint. Bots walk between nodes that are within
        reach of each other, so these need to form a connected chain through
        every space a bot should use."""
        self.actor("PathNode", x, y, floor_z + clearance)

    def path_grid(self, x0, x1, y0, y1, floor_z, step=256, clearance=58):
        """Fill a walkable area with PathNodes, skipping any that would land
        inside an added solid.

        Deck16's median node spacing is 208 units, so 256 is a reasonable
        default. Nodes inside a pillar do not error - they just vanish from the
        path network - so they are dropped here instead.
        """
        placed = 0
        z = floor_z + clearance
        adds = [b for b in self.brushes if b.csg == "CSG_Add"]
        x = x0
        while x <= x1:
            y = y0
            while y <= y1:
                if not any(_overlaps(b, x, y, z, self.START_RADIUS,
                                     self.START_HEIGHT) for b in adds):
                    self.actor("PathNode", int(x), int(y), int(z))
                    placed += 1
                y += step
            x += step
        return placed

    def camera(self, x, y, z, yaw=0, pitch=0):
        """A SpectatorCam viewpoint. In-game, spectators cycle cameras with
        fire. Angles are UE1 rotator units: 65536 to a full turn."""
        self.actors.append(("SpectatorCam", x, y, z,
                            {"Rotation": f"(Yaw={int(yaw)},Pitch={int(pitch)})"}))

    def viewpoint(self, x, y, z, yaw=0, pitch=0):
        """The ONLY PlayerStart, with an explicit facing.

        A spectator spawns at some PlayerStart facing whatever that start's
        rotation says. With several starts the engine picks one at random, so
        screenshots of the same map differ run to run and it is easy to read
        "my prop is invisible" off a camera that was simply pointed elsewhere.
        One start with a known rotation makes a shot reproducible.
        """
        self.actors = [a for a in self.actors if a[0] != "PlayerStart"]
        self.actors.append(("PlayerStart", x, y, z,
                            {"Rotation": f"(Yaw={int(yaw)},Pitch={int(pitch)})"}))

    def use_textures(self, *packages):
        """Load .utx packages explicitly. Usually unnecessary: build() loads
        whatever packages the faces actually reference."""
        self.texture_packages.extend(packages)

    def referenced_packages(self):
        """Packages named by any face, in first-use order."""
        seen = []
        for br in self.brushes:
            for p in br.polys:
                if not p.texture:
                    continue
                pkg = p.texture.partition(".")[0]
                if pkg and pkg not in seen:
                    seen.append(pkg)
        return seen

    def check(self):
        """Report actor placements the engine would reject at spawn time.

        UT99 aborts the whole game on a bad PlayerStart, and the log names only
        one start, so finding them by trial costs a full launch each. This
        checks every start against the open (subtracted) space up front.
        """
        subs = [b for b in self.brushes if b.csg != "CSG_Add"]
        adds = [b for b in self.brushes if b.csg == "CSG_Add"]
        problems = []

        # A misspelled texture is not an error at build time: the face just
        # renders untextured, so it is only noticed by eye much later.
        import textures as _tex
        for br in self.brushes:
            for p in br.polys:
                if p.texture and not _tex.exists(p.texture):
                    problems.append(
                        f"brush '{br.name}' references unknown texture "
                        f"'{p.texture}'")

        # PathNodes share NavigationPoint's collision with PlayerStart. A node
        # buried in an added solid is not an error the engine reports - it just
        # silently drops out of the path network, and enough of them takes bot
        # navigation to zero while the map still builds and plays.
        for cls, x, y, z, _ in self.actors:
            if cls not in ("PlayerStart", "PathNode"):
                continue
            r, h = self.START_RADIUS, self.START_HEIGHT
            inside = any(_contains(b, x, y, z, r, h) for b in subs)
            if not inside:
                problems.append(
                    f"{cls} at ({x},{y},{z}) is not fully inside any "
                    f"subtracted room (needs {r} radius / {h} half-height "
                    f"clearance)")
                continue
            for b in adds:
                if _overlaps(b, x, y, z, r, h):
                    problems.append(
                        f"{cls} at ({x},{y},{z}) intersects added brush "
                        f"'{b.name}'")
        return problems

    def build(self, rebuild="BALANCE=15 LAME OPTGEOM ZONES", lights=True,
              paths=False, validate=True):
        from t3d import write_t3d

        if validate:
            problems = self.check()
            if problems:
                raise ValueError(f"{self.name}: invalid actor placement:\n  " +
                                 "\n  ".join(problems))

        os.makedirs(WORK, exist_ok=True)
        os.makedirs(MAPS, exist_ok=True)
        out_unr = os.path.join(MAPS, f"{self.name}.unr")
        if os.path.exists(out_unr):
            os.remove(out_unr)

        cmds = ["MAP NEW"]
        for pkg in dict.fromkeys(self.texture_packages +
                                 self.referenced_packages()):
            cmds.append(f'OBJ LOAD FILE="../Textures/{pkg}.utx"')

        # One import+apply pair per brush, in declaration order.
        for i, br in enumerate(self.brushes):
            t3d_path = os.path.join(WORK, f"{self.name}_b{i}.t3d")
            write_t3d(br, t3d_path)
            cmds.append(f'BRUSH IMPORT FILE="{t3d_path}"')
            cmds.append("BRUSH ADD" if br.csg == "CSG_Add" else "BRUSH SUBTRACT")

        # Actors go in through MAP IMPORTADD, NOT `ACTOR ADD CLASS=.. XPOS=..`.
        # ACTOR ADD drops the actor at the editor's current add-location (the
        # spot you last clicked in UnrealEd) and IGNORES XPOS/YPOS/ZPOS
        # entirely - it reports "Added actor ... successfully" either way, and
        # the saved map ends up with every light, item and start stacked on the
        # origin with no Location property at all.
        if self.actors:
            actors_t3d = os.path.join(WORK, f"{self.name}_actors.t3d")
            with open(actors_t3d, "w") as fh:
                fh.write("Begin Map\n")
                for i, (cls, x, y, z, props) in enumerate(self.actors):
                    fh.write(f"Begin Actor Class={cls} Name={cls}{i}\n")
                    fh.write(f"    Location=(X={float(x):.6f},"
                             f"Y={float(y):.6f},Z={float(z):.6f})\n")
                    for k, v in props.items():
                        fh.write(f"    {k}={v}\n")
                    fh.write("End Actor\n")
                fh.write("End Map\n")
            cmds.append(f'MAP IMPORTADD FILE="{actors_t3d}"')

        cmds.append(f"BSP REBUILD {rebuild}")
        if lights:
            cmds.append("BSP BUILDLIGHTS")
        if paths:
            cmds.append("PATHS BUILD")
        cmds.append(f'MAP SAVE FILE="{out_unr}"')

        script = os.path.join(WORK, f"{self.name}.exec")
        with open(script, "w") as fh:
            fh.write("\n".join(cmds) + "\n")

        res = subprocess.run([UCC, "exec", script], cwd=SYSTEM64,
                             capture_output=True, text=True, timeout=900)
        log = res.stdout + res.stderr

        if not os.path.exists(out_unr):
            fail = [l for l in log.splitlines()
                    if any(w in l.lower() for w in
                           ("error", "fail", "unrecognized", "appError"))]
            raise RuntimeError(f"build failed for {self.name}:\n" +
                               "\n".join(fail[-25:] or log.splitlines()[-25:]))
        return out_unr, log


def _bounds(brush):
    """Axis-aligned extent of a brush, in world space."""
    xs = [v[0] for p in brush.polys for v in p.verts]
    ys = [v[1] for p in brush.polys for v in p.verts]
    zs = [v[2] for p in brush.polys for v in p.verts]
    ox, oy, oz = brush.location
    return (min(xs) + ox, min(ys) + oy, min(zs) + oz,
            max(xs) + ox, max(ys) + oy, max(zs) + oz)


def _contains(brush, x, y, z, r, h):
    """Is the collision cylinder wholly inside this brush's extent?

    Only exact for box brushes; a non-box brush is treated as its bounding
    box, so this can pass a start that a concave shape would still reject.
    """
    x0, y0, z0, x1, y1, z1 = _bounds(brush)
    return (x0 <= x - r and x + r <= x1 and
            y0 <= y - r and y + r <= y1 and
            z0 <= z - h and z + h <= z1)


def _overlaps(brush, x, y, z, r, h):
    x0, y0, z0, x1, y1, z1 = _bounds(brush)
    return (x - r < x1 and x + r > x0 and
            y - r < y1 and y + r > y0 and
            z - h < z1 and z + h > z0)


def stats(log):
    """Pull the BSP numbers worth asserting on out of a build log."""
    keys = ("Portalized:", "Static BSP Nodes", "Found ", "zones",
            "Bsp rebuild in")
    return [l.strip() for l in log.splitlines()
            if any(k in l for k in keys)]


def tour(map_name, out_dir=None, shots=6, wait=30, bots=0):
    """Fly a spectator camera round the level and grab several frames.

    A normal deathmatch screenshot is whatever the player happens to see, which
    after twenty seconds is usually a death-cam pressed into the floor. Running
    as a spectator with no bots gives a clean look at the geometry instead.
    """
    import time

    out_dir = out_dir or SHOTS
    os.makedirs(out_dir, exist_ok=True)
    env = dict(os.environ, DISPLAY=":0")
    subprocess.run(["pkill", "-9", "-f", "ut-bin-amd64"], capture_output=True)
    time.sleep(2)

    # DeathMatchPlus reads its bot count from the ini, not the URL, so a
    # ?numbots=0 alone still fills the level with fighting bots.
    restore = _set_ini("Botpack.DeathMatchPlus", "InitialBots", str(bots))

    url = f"{map_name}?quickstart=1?numbots={bots}?spectatoronly=1"
    game = subprocess.Popen([UT, url, "-windowed", "-nosound"], cwd=SYSTEM64,
                            env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    out = []
    try:
        time.sleep(wait)
        wid = _find_window(env)
        if not wid:
            raise RuntimeError(f"no render window for {map_name}")
        subprocess.run(["xdotool", "windowactivate", wid], env=env,
                       capture_output=True)
        subprocess.run(["xdotool", "windowraise", wid], env=env,
                       capture_output=True)
        for i in range(shots):
            time.sleep(3)
            p = os.path.join(out_dir, f"{map_name}_{i}.png")
            subprocess.run(["import", "-window", wid, p], env=env,
                           capture_output=True, timeout=60)
            out.append(p)
    finally:
        game.kill()
        subprocess.run(["pkill", "-9", "-f", "ut-bin-amd64"],
                       capture_output=True)
        restore()
    return out


INI = _paths.ini()


def _set_ini(section, key, value):
    """Set one ini key, returning a callable that puts the old value back."""
    import re

    with open(INI, encoding="latin-1", errors="replace") as fh:
        original = fh.read()

    m = re.search(r"^\[" + re.escape(section) + r"\]", original, re.M)
    if not m:
        return lambda: None
    start = m.end()
    nxt = re.search(r"^\[", original[start:], re.M)
    end = start + (nxt.start() if nxt else len(original) - start)
    block = original[start:end]

    if re.search(r"^" + re.escape(key) + r"=", block, re.M):
        block = re.sub(r"^" + re.escape(key) + r"=.*$", f"{key}={value}",
                       block, flags=re.M)
    else:
        block = f"\n{key}={value}" + block

    with open(INI, "w", encoding="latin-1", errors="replace") as fh:
        fh.write(original[:start] + block + original[end:])

    def restore():
        with open(INI, "w", encoding="latin-1", errors="replace") as fh:
            fh.write(original)
    return restore


def screenshot(map_name, out_png=None, wait=30, timeout=90, quickstart=True):
    """Launch UT99 on a map, grab the render window, kill the game.

    Uses `import -window` because the SDL/Wayland window does not accept
    xdotool key injection, so the in-game SHOT command cannot be triggered
    from outside. `?quickstart=1` skips the "waiting for ready signals"
    screen so the shot shows the level rather than the lobby overlay.
    """
    import time

    os.makedirs(SHOTS, exist_ok=True)
    out_png = out_png or os.path.join(SHOTS, f"{map_name}.png")
    env = dict(os.environ, DISPLAY=":0")

    # A previous instance still holding the display would be screenshotted
    # instead of this one, which silently shows the wrong map.
    subprocess.run(["pkill", "-9", "-f", "ut-bin-amd64"], capture_output=True)
    time.sleep(2)

    url = f"{map_name}?quickstart=1" if quickstart else map_name
    game = subprocess.Popen([UT, url, "-windowed", "-nosound"], cwd=SYSTEM64,
                            env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + timeout
        wid = None
        time.sleep(wait)
        while time.time() < deadline:
            wid = _find_window(env)
            if wid:
                break
            if game.poll() is not None:
                raise RuntimeError(
                    f"UT99 exited before rendering {map_name}; check "
                    f"~/.utpg/System/UnrealTournament.log for a spawn failure")
            time.sleep(3)
        if not wid:
            raise RuntimeError(f"no UT99 render window appeared for {map_name}")

        subprocess.run(["xdotool", "windowactivate", wid], env=env,
                       capture_output=True)
        subprocess.run(["xdotool", "windowraise", wid], env=env,
                       capture_output=True)
        time.sleep(4)
        subprocess.run(["import", "-window", wid, out_png], env=env,
                       capture_output=True, timeout=60)
    finally:
        game.kill()
        subprocess.run(["pkill", "-9", "-f", "ut-bin-amd64"],
                       capture_output=True)
    return out_png


def _find_window(env):
    """The game makes several X windows; the render surface is the big one."""
    res = subprocess.run(["xdotool", "search", "--name", "Unreal Tournament"],
                         env=env, capture_output=True, text=True)
    best, best_area = None, 0
    for wid in res.stdout.split():
        g = subprocess.run(["xdotool", "getwindowgeometry", "--shell", wid],
                           env=env, capture_output=True, text=True).stdout
        d = dict(l.split("=", 1) for l in g.strip().splitlines() if "=" in l)
        area = int(d.get("WIDTH", 0)) * int(d.get("HEIGHT", 0))
        if area > best_area:
            best, best_area = wid, area
    return best if best_area > 100000 else None


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
