"""
obj2mesh.py - convert a Wavefront .obj into a UT99 (UE1) vertex mesh.

UT99 has no static meshes - those arrived in UT2003. Every non-BSP prop in UT99
is a *vertex-animated* mesh, the same format used for players and weapons, and
it is imported at COMPILE time by an `#exec MESH IMPORT` line in an
UnrealScript class. A one-frame animation is a perfectly good static prop.

The format is a pair of little-endian files:

  <name>_d.3d   "data": a 48-BYTE header then one 16-byte triangle per poly
  <name>_a.3d   "anim": a 4-byte header then one packed DWORD per vertex,
                per frame

The data header really is 48 bytes even though only the first four are read
(NumPolys, NumVerts); the rest is documented as "not currently read by
UnrealEd". Writing a short header does not error - it silently shifts every
triangle record and segfaults the importer inside meshLODProcess.

A vertex is packed into one DWORD as X:11, Y:11, Z:10 SIGNED bits, low to
high, with fixed scale factors baked into the format: X and Y are stored as
round(x * 8) and Z as round(z * 4). That caps a mesh at +-128 world units per
axis (a 256-unit box); going past it wraps silently rather than erroring, so
models are fitted into that box here and scaled back up with DrawScale.

Usage:
    python3 tools/obj2mesh.py desk.obj OfficeDesk ut/OfficeProps/Models
"""

import os
import struct
import sys

# The packed vertex gives 11 bits signed for X and Y, 10 for Z, with fixed
# scale factors of 8 and 4 - so the usable world-space extent is +-128 on
# every axis, and the raw field values run -1024..1023 / -512..511.
XY_SCALE = 8.0
Z_SCALE = 4.0
XY_LIMIT = 1023
Z_LIMIT = 511
MESH_EXTENT = 127.0          # world units from origin, kept just inside +-128


def load_obj(path):
    """Return (verts, tris) where each tri is (idx0, idx1, idx2, material).

    Kenney's models carry no usable texture coordinates - their `vt` values are
    world-scale (tens of units), because the models are coloured by MATERIAL,
    not by a texture atlas. So the material name per face is what matters, and
    UVs are synthesised later from a generated palette texture.
    """
    verts, tris = [], []
    material = "_defaultMat"
    for line in open(path, encoding="utf-8", errors="replace"):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            verts.append(tuple(float(p) for p in parts[1:4]))
        elif parts[0] == "usemtl":
            material = parts[1] if len(parts) > 1 else "_defaultMat"
        elif parts[0] == "f":
            face = []
            for tok in parts[1:]:
                vi = int(tok.split("/")[0])
                # OBJ indices are 1-based; negative counts back from the end.
                face.append(vi - 1 if vi > 0 else len(verts) + vi)
            # Fan-triangulate: Kenney's models are quads and n-gons.
            for i in range(1, len(face) - 1):
                tris.append((face[0], face[i], face[i + 1], material))
    return verts, tris


def load_mtl(path):
    """{material: (r, g, b)} from the .mtl beside an .obj, 0-255."""
    out = {}
    name = None
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "newmtl":
                name = parts[1]
            elif parts[0] == "Kd" and name:
                r, g, b = (float(p) for p in parts[1:4])
                out[name] = (int(r * 255), int(g * 255), int(b * 255))
    except OSError:
        pass
    return out


def fit(verts, target_size):
    """Fit the model into the format's +-128 unit box, Z-up and sitting on 0.

    Returns (world_verts, drawscale). The mesh is stored as large as the box
    allows to minimise quantisation error, then scaled back to the size you
    actually want in-game via the class's DrawScale.
    """
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) or 1.0
    cx = (max(xs) + min(xs)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0

    # Fill the box: the tallest axis becomes the full 2 * MESH_EXTENT.
    mesh_scale = (MESH_EXTENT * 2.0) / span
    out = []
    for x, y, z in verts:
        # OBJ is Y-up, Unreal is Z-up: (x, y, z)_obj -> (x, -z, y)_unreal.
        out.append(((x - cx) * mesh_scale,
                    -(z - cz) * mesh_scale,
                    (y - min(ys)) * mesh_scale))

    # The MESHMAP scale that turns stored mesh units into world units.
    #
    # The engine uses the RAW packed field values as mesh units, so the scale
    # has to undo the format's own 8x (X/Y) and 4x (Z) packing as well as the
    # fitting above. That is why Z always comes out twice X/Y - exactly the
    # 0.1/0.1/0.2 shape every stock mesh in the SDK uses.
    xy = target_size / (span * mesh_scale * XY_SCALE)
    return out, (xy, xy, xy * (XY_SCALE / Z_SCALE))


def _clamp(v, limit):
    return max(-limit, min(limit, v))


def pack_vertex(x, y, z):
    """Pack world coords into one DWORD: X:11, Y:11, Z:10 signed, low to high.

    X and Y are stored at 8x and Z at 4x - these factors are part of the
    format, not a choice.
    """
    ix = _clamp(int(round(x * XY_SCALE)), XY_LIMIT)
    iy = _clamp(int(round(y * XY_SCALE)), XY_LIMIT)
    iz = _clamp(int(round(z * Z_SCALE)), Z_LIMIT)
    return (ix & 0x7FF) | ((iy & 0x7FF) << 11) | ((iz & 0x3FF) << 22)


# The palette texture is a grid of solid colour cells; a face is textured by
# pointing all three of its UVs at the centre of its material's cell.
PALETTE_CELLS = 8          # 8x8 = 64 materials, at 32x32 px each in a 256 map


def cell_uv(slot):
    """Byte UV of the centre of palette cell `slot`, for a 256x256 texture."""
    step = 256 // PALETTE_CELLS
    cx = (slot % PALETTE_CELLS) * step + step // 2
    cy = (slot // PALETTE_CELLS) * step + step // 2
    return min(255, cx), min(255, cy)


def write_palette(materials, path):
    """Render {material: (r,g,b)} as a paletted PCX of solid cells.

    Cells are deliberately much larger than the single texel each face samples
    so that UE1's bilinear filtering and mipmapping never bleed one material's
    colour into its neighbour.
    """
    from pcx import Texture

    t = Texture(256, 256)
    step = 256 // PALETTE_CELLS
    for slot, (name, rgb) in enumerate(materials.items()):
        if slot >= PALETTE_CELLS * PALETTE_CELLS:
            break
        idx = t.color(*rgb)
        x = (slot % PALETTE_CELLS) * step
        y = (slot // PALETTE_CELLS) * step
        t.rect(x, y, x + step, y + step, idx)
    return t.save(path)


def write_mesh(obj_path, name, out_dir, target_size=64.0, texture_index=0,
               material_slots=None):
    """Write the mesh pair. `material_slots` maps material name -> palette cell
    so several props can share one palette texture."""
    verts, tris = load_obj(obj_path)
    if not verts or not tris:
        raise SystemExit(f"{obj_path}: no geometry")
    scaled, drawscale = fit(verts, target_size)
    material_slots = material_slots or {}

    os.makedirs(out_dir, exist_ok=True)
    data_path = os.path.join(out_dir, f"{name}_d.3d")
    anim_path = os.path.join(out_dir, f"{name}_a.3d")

    if len(tris) > 65535 or len(scaled) > 65535:
        raise SystemExit(f"{obj_path}: {len(tris)} tris / {len(scaled)} verts "
                         "exceeds the format's 16-bit limits")

    with open(data_path, "wb") as fh:
        # dataheader, 48 bytes. Only NumPolys/NumVerts are read by the
        # importer, but the full 48 must be present or every triangle after
        # it is read at the wrong offset (segfault, no error message).
        fh.write(struct.pack("<HH", len(tris), len(scaled)))
        fh.write(b"\0" * 44)
        for i0, i1, i2, material in tris:
            # unreal_tri, 16 bytes: 3 vertex indices, type, colour,
            # UVs as [u0,v0,u1,v1,u2,v2], texture number, flags.
            fh.write(struct.pack("<HHH", i0, i1, i2))
            fh.write(struct.pack("<BB", 0, 0))          # type 0 = one-sided
            u, v = cell_uv(material_slots.get(material, 0))
            for _ in range(3):
                fh.write(struct.pack("<BB", u, v))
            fh.write(struct.pack("<BB", texture_index, 0))

    with open(anim_path, "wb") as fh:
        # aniv header: NumFrames, FrameSize. One frame = a static prop.
        fh.write(struct.pack("<hh", 1, len(scaled) * 4))
        for x, y, z in scaled:
            fh.write(struct.pack("<I", pack_vertex(x, y, z)))

    return data_path, anim_path, drawscale, len(tris), len(scaled)


def uc_class(name, scale, texture="", collision=(24, 24)):
    """The UnrealScript decoration class that imports and places the mesh.

    `scale` is the (x, y, z) MESHMAP scale from fit(); DrawScale stays at 1
    because the meshmap already puts the model at its intended world size.
    """
    sx, sy, sz = scale
    radius, height = collision
    tex_line = (f"#exec MESH IMPORT MESH={name} "
                f"ANIVFILE=Models\\{name}_a.3d DATAFILE=Models\\{name}_d.3d "
                f"X=0 Y=0 Z=0 MLOD=0\n")
    return f"""//=============================================================================
// {name} - generated by tools/obj2mesh.py, do not edit by hand.
//=============================================================================
class {name} extends Decoration;

{tex_line}#exec MESH ORIGIN MESH={name} X=0 Y=0 Z=0 YAW=0
#exec MESH SEQUENCE MESH={name} SEQ=All STARTFRAME=0 NUMFRAMES=1
#exec MESH SEQUENCE MESH={name} SEQ=Still STARTFRAME=0 NUMFRAMES=1
#exec MESHMAP NEW MESHMAP={name} MESH={name}
#exec MESHMAP SCALE MESHMAP={name} X={sx:.6f} Y={sy:.6f} Z={sz:.6f}
{f'#exec MESHMAP SETTEXTURE MESHMAP={name} NUM=0 TEXTURE={texture}' if texture else ''}

defaultproperties{{
     DrawType=DT_Mesh
     Mesh=Mesh'OfficeProps.{name}'
     DrawScale=+00001.000000
     CollisionRadius=+{radius:09.6f}
     CollisionHeight=+{height:09.6f}
     bCollideActors=False
     bBlockActors=False
     bBlockPlayers=False
     bStatic=False
     bCollideWorld=True
     bNoDelete=True
}}
"""


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__.strip())
    obj, name = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "ut/Models"
    d, a, ds, nt, nv = write_mesh(obj, name, out)
    print(f"{d}\n{a}\ntris={nt} verts={nv} drawscale={ds:.4f}")
