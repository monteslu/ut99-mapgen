"""Headless check of the Blender addon: build geometry, export, verify."""

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ut99_t3d                                    # noqa: E402

try:
    ut99_t3d.register()
except ValueError:
    pass                # already enabled as an installed addon

# Empty the default scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

S = ut99_t3d.UT_SCALE       # 16 UT units per metre

# primitive_cube_add(size=1) already spans -0.5..0.5, so object scale is the
# full edge length in metres - dividing by 2 as well would halve the room.
# A 2560 x 2048 x 1024 hall (the size of a real UT room) as a subtract brush.
bpy.ops.mesh.primitive_cube_add(size=1)
hall = bpy.context.object
hall.name = "Hall"
hall.scale = (2560 / S, 2048 / S, 1024 / S)
hall.location = (0, 0, 0)
hall.ut99_csg = "CSG_Subtract"
hall.ut99_texture = "ShaneChurch.BrownWall"
hall.ut99_scale = 4.0

# A pillar as an add brush, stopping short of the ceiling.
bpy.ops.mesh.primitive_cube_add(size=1)
pillar = bpy.context.object
pillar.name = "Pillar"
pillar.scale = (256 / S, 256 / S, 640 / S)
pillar.location = (0, 0, -(1024 / S / 2) + (640 / S / 2))
pillar.ut99_csg = "CSG_Add"
pillar.ut99_texture = "ShaneChurch.BrownTrim"
pillar.ut99_scale = 2.0

bpy.context.view_layer.update()

out = os.path.join(HERE, "blender_out.t3d")
n = ut99_t3d.export_t3d(bpy.context, out)
print(f"RESULT exported={n} path={out}")

# A concave mesh must be REFUSED, not silently exported into broken CSG.
bpy.ops.mesh.primitive_cube_add(size=2)
bad = bpy.context.object
bad.name = "Concave"
import bmesh
bm = bmesh.new()
bm.from_mesh(bad.data)
bm.verts.ensure_lookup_table()
bm.verts[0].co.z -= 3.0          # pull one corner through the body
bm.to_mesh(bad.data)
bm.free()
bpy.ops.object.select_all(action="DESELECT")
bad.select_set(True)
try:
    ut99_t3d.export_t3d(bpy.context, out + ".bad", selected_only=True)
    print("RESULT concave-control=FAILED (was accepted)")
except RuntimeError as err:
    print(f"RESULT concave-control=OK ({err})")
