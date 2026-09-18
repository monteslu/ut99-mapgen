"""
t3d.py - generate UT99 (Unreal Engine 1) .t3d brush geometry from Python.

UE1 maps are built with CSG: you subtract solid space out of the infinite solid
world to carve rooms, then add brushes back for pillars/ledges. A brush is a
closed set of convex polygons; the engine BSPs them at build time.

Coordinate system (UnrealEd): X east, Y south, Z up. 1 unit ~ 1 inch; a player
is 78 units tall and a comfortable corridor is 256 wide / 256 high.
"""

from dataclasses import dataclass, field


# Polygon flags worth knowing (UnrealEd PF_* values).
PF_INVISIBLE = 0x00000001
PF_MASKED = 0x00000002
PF_TRANSLUCENT = 0x00000004
PF_NOTSOLID = 0x00000008
PF_TWOSIDED = 0x00000100
PF_UNLIT = 0x00400000
PF_PORTAL = 0x04000000
PF_MIRRORED = 0x08000000


@dataclass
class Poly:
    """One convex, planar face of a brush. Vertices must be ordered so the
    winding matches `normal` (right-hand rule)."""
    verts: list                      # [(x, y, z), ...] in order
    normal: tuple
    texture_u: tuple                 # texture space axes; length sets the scale
    texture_v: tuple
    texture: str = ""                # "Package.Group.Name" or "" for default
    flags: int = 0
    pan_u: int = 0
    pan_v: int = 0

    def to_t3d(self) -> str:
        origin = self.verts[0]
        head = "         Begin Polygon"
        if self.texture:
            head += f" Texture={self.texture}"
        if self.flags:
            head += f" Flags={self.flags}"
        lines = [head]
        lines.append(f"            Origin   {_v(origin)}")
        lines.append(f"            Normal   {_v(self.normal)}")
        lines.append(f"            TextureU {_v(self.texture_u)}")
        lines.append(f"            TextureV {_v(self.texture_v)}")
        if self.pan_u or self.pan_v:
            lines.append(f"            Pan      U={self.pan_u} V={self.pan_v}")
        for v in self.verts:
            lines.append(f"            Vertex   {_v(v)}")
        lines.append("         End Polygon")
        return "\n".join(lines)


@dataclass
class Brush:
    """A CSG brush: a closed polyhedron plus the operation to apply with it."""
    polys: list = field(default_factory=list)
    name: str = "Brush0"
    csg: str = "CSG_Subtract"        # CSG_Subtract carves, CSG_Add fills
    location: tuple = (0.0, 0.0, 0.0)
    poly_flags: int = 0

    def to_t3d(self) -> str:
        out = [f"   Begin Actor Class=Brush Name={self.name}",
               f"      CsgOper={self.csg}",
               "      MainScale=(SheerAxis=SHEER_ZX)",
               "      PostScale=(SheerAxis=SHEER_ZX)",
               f"      Location=({_loc(self.location)})",
               f"      Begin Brush Name=Model_{self.name}",
               "         Begin PolyList"]
        for p in self.polys:
            out.append(p.to_t3d())
        out.append("         End PolyList")
        out.append("      End Brush")
        out.append(f"      Brush=Model'MyLevel.Model_{self.name}'")
        out.append("   End Actor")
        return "\n".join(out)


def _v(t) -> str:
    return ",".join(f"{c:+013.6f}" for c in t)


def _loc(t) -> str:
    return ",".join(f"{a}={c:.6f}" for a, c in zip("XYZ", t))


def _axes(normal):
    """Pick two unit vectors perpendicular to `normal` for texture mapping.
    UE1 needs a U/V basis per face; we branch on the dominant axis to avoid a
    degenerate cross product."""
    nx, ny, nz = normal
    if abs(nz) > 0.9:                    # floor / ceiling
        return (1, 0, 0), (0, 1, 0)
    if abs(nx) > 0.9:                    # east / west wall
        return (0, 1, 0), (0, 0, -1)
    return (1, 0, 0), (0, 0, -1)         # north / south wall


def _scaled(axis, scale):
    """UE1 derives texture size from the LENGTH of the U/V axis vectors: a
    shorter vector stretches the texture over more world units. So a scale of
    2.0 (texture twice as big on the wall) divides the axis by 2."""
    return tuple(c / scale for c in axis)


def box(x0, y0, z0, x1, y1, z1, texture="", flags=0, name="Brush0",
        csg="CSG_Subtract", scale=1.0, floor=None, ceiling=None, walls=None):
    """Axis-aligned box brush spanning the two corners.

    Faces are wound normals-out for BOTH operations - Epic's own CSG_Add
    brushes in DM-Deck16][ use exactly the same winding as their subtracts.
    Reversing the winding for added brushes instead produces a map that still
    builds and still reports plausible BSP numbers, but whose added solids are
    inside-out: the node count collapses and `PATHS BUILD` yields *zero*
    reachspecs, so bots have no navigation at all.

    `texture` sets every face; `floor`, `ceiling` and `walls` override it per
    surface. `scale` multiplies how large the texture appears in world units,
    so scale=2 halves the visible tiling.

    Vertices are in WORLD space and Location stays at the origin. `BRUSH
    IMPORT` loads only the polygon list into the builder brush and ignores the
    actor's Location, so a brush positioned that way carves at the origin
    instead: every room ends up stacked in the same place, which shows up as a
    map whose BSP node count never grows no matter how many rooms you add.
    (A saved .unr does store per-brush Location - that is how UnrealEd tracks
    brushes you dragged - but it is not how geometry gets imported.)
    """
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))

    faces = [
        ((0, 0, -1), [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)]),
        ((0, 0, 1),  [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
        ((-1, 0, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
        ((1, 0, 0),  [(x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (x1, y0, z0)]),
        ((0, -1, 0), [(x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (x0, y0, z0)]),
        ((0, 1, 0),  [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)]),
    ]
    polys = []
    for i, (normal, verts) in enumerate(faces):
        # faces[] is ordered floor, ceiling, then the four walls.
        tex = texture
        if i == 0 and floor is not None:
            tex = floor
        elif i == 1 and ceiling is not None:
            tex = ceiling
        elif i >= 2 and walls is not None:
            tex = walls

        u, v = _axes(normal)
        polys.append(Poly(verts=verts, normal=normal,
                          texture_u=_scaled(u, scale),
                          texture_v=_scaled(v, scale),
                          texture=tex, flags=flags))
    return Brush(polys=polys, name=name, csg=csg)


def stairs(x0, y0, z0, x1, y1, steps, rise, axis="x", texture="",
           name="Stairs", scale=1.0):
    """A run of step brushes climbing `steps * rise` units.

    Built as solid CSG_Add treads inside an already-carved room, which is how
    UnrealEd's stair builder works: the room provides the air, the steps put
    solid back. Returns a list of brushes.

    `axis` is the direction of travel, "x" or "y".
    """
    out = []
    for i in range(steps):
        top = z0 + (i + 1) * rise
        if axis == "x":
            span = (x1 - x0) / steps
            a, b = x0 + i * span, x0 + (i + 1) * span
            out.append(box(a, y0, z0, b, y1, top, texture=texture,
                           name=f"{name}{i}", csg="CSG_Add", scale=scale))
        else:
            span = (y1 - y0) / steps
            a, b = y0 + i * span, y0 + (i + 1) * span
            out.append(box(x0, a, z0, x1, b, top, texture=texture,
                           name=f"{name}{i}", csg="CSG_Add", scale=scale))
    return out


def ramp(x0, y0, z0, x1, y1, z1, axis="x", texture="", name="Ramp",
         scale=1.0, steps=8):
    """A walkable slope, approximated as a short stair run.

    UE1 can do true angled brushes, but stepped ramps are what most UT99 maps
    actually use and they path far more reliably for bots. `steps` trades
    smoothness against BSP node count.
    """
    return stairs(x0, y0, z0, x1, y1, steps, (z1 - z0) / steps, axis=axis,
                  texture=texture, name=name, scale=scale)


def arch(cx, cy, z0, z1, width, depth, texture="", name="Arch", scale=1.0,
         segments=4):
    """A doorway with a stepped arched top, cut as subtract brushes.

    Segments approximate the curve; each is a separate carve, so keep the
    count low - every brush costs BSP nodes.
    """
    out = [box(cx - width / 2, cy - depth / 2, z0,
               cx + width / 2, cy + depth / 2, z1 - width / 2,
               texture=texture, name=f"{name}Body", scale=scale)]
    for i in range(segments):
        frac = (i + 1) / (segments + 1)
        w = width * (1.0 - frac * frac) ** 0.5
        zt = z1 - width / 2 + (width / 2) * frac
        zb = z1 - width / 2 + (width / 2) * (i / (segments + 1))
        out.append(box(cx - w / 2, cy - depth / 2, zb,
                       cx + w / 2, cy + depth / 2, zt,
                       texture=texture, name=f"{name}Arc{i}", scale=scale))
    return out


def write_t3d(brushes, path):
    """Write brushes as a .t3d. Each brush imports as its own CSG operation."""
    if isinstance(brushes, Brush):
        brushes = [brushes]
    body = "\n".join(b.to_t3d() for b in brushes)
    with open(path, "w") as fh:
        fh.write("Begin Map\n" + body + "\nEnd Map\n")
    return path
