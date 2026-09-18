"""
ut99_t3d - sculpt UT99 levels in Blender.

Install: copy this file into Blender's addons directory and enable
"Import-Export: UT99 T3D (Unreal Engine 1)", or just run it from the Text
Editor. It adds File > Import/Export > Unreal T3D (.t3d).

How UT99 geometry works, and what that means here:

  UE1 levels are CSG. The world starts as infinite solid rock; a SUBTRACT
  brush carves a room out of it and an ADD brush puts solid back. So a mesh
  here is not a wall - it is the volume of air a room occupies. Model the
  space, not the shell.

  Each object carries its CSG operation in a custom property (UI panel: "UT99
  Brush"). Subtract is the default.

  Units: 1 Blender metre = 16 UT units by default (UT_SCALE), so a 64-unit
  player-height doorway is 4m. UT's Z is up, which matches Blender.

  Only convex meshes work as brushes. UE1's CSG will accept a concave shape
  and produce sealed-looking geometry with holes in the BSP; the exporter
  refuses instead, so split concave rooms into convex pieces.
"""

bl_info = {
    "name": "UT99 T3D (Unreal Engine 1)",
    "author": "cliemu",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "File > Import/Export > Unreal T3D (.t3d)",
    "description": "Import and export Unreal Engine 1 .t3d brush geometry",
    "category": "Import-Export",
}

import bmesh
import bpy
from bpy.props import EnumProperty, FloatProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from mathutils import Vector

UT_SCALE = 16.0          # UT units per Blender metre
CONVEX_EPS = 1e-4        # tolerance when testing a face plane


# --------------------------------------------------------------------------
# object properties
# --------------------------------------------------------------------------

CSG_ITEMS = [
    ("CSG_Subtract", "Subtract (carve room)",
     "Carve this volume out of the solid world - use for rooms and corridors"),
    ("CSG_Add", "Add (solid block)",
     "Put solid back - use for pillars, ledges and blocks inside a room"),
]


def _register_props():
    bpy.types.Object.ut99_csg = EnumProperty(
        name="CSG", items=CSG_ITEMS, default="CSG_Subtract")
    bpy.types.Object.ut99_texture = StringProperty(
        name="Texture", default="",
        description="Package.Texture applied to faces with no material")
    bpy.types.Object.ut99_scale = FloatProperty(
        name="Tex Scale", default=4.0, min=0.05, soft_max=16.0,
        description="How large the texture appears; 2 halves the tiling")


def _unregister_props():
    for a in ("ut99_csg", "ut99_texture", "ut99_scale"):
        if hasattr(bpy.types.Object, a):
            delattr(bpy.types.Object, a)


class UT99_PT_brush(bpy.types.Panel):
    bl_label = "UT99 Brush"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == "MESH"

    def draw(self, context):
        ob = context.object
        col = self.layout.column()
        col.prop(ob, "ut99_csg")
        col.prop(ob, "ut99_texture")
        col.prop(ob, "ut99_scale")
        col.separator()
        col.label(text="Mesh = the AIR of a room, not its walls.")


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------

def _is_convex(bm):
    """Every vertex must lie on or behind every face plane."""
    for f in bm.faces:
        n = f.normal
        if n.length < CONVEX_EPS:
            return False, "a face has no area (degenerate geometry)"
        d = n.dot(f.verts[0].co)
        for v in bm.verts:
            if n.dot(v.co) - d > CONVEX_EPS * max(1.0, abs(d)):
                return False, "mesh is concave - split it into convex pieces"
    return True, ""


def _tex_axes(normal):
    """A U/V basis for a face, branching on the dominant axis so the cross
    product never degenerates."""
    nx, ny, nz = normal
    if abs(nz) > 0.9:
        return Vector((1, 0, 0)), Vector((0, 1, 0))
    if abs(nx) > 0.9:
        return Vector((0, 1, 0)), Vector((0, 0, -1))
    return Vector((1, 0, 0)), Vector((0, 0, -1))


def _fmt(v):
    return ",".join(f"{c:+013.6f}" for c in v)


def _material_texture(ob, face):
    """A material named like "ShaneChurch.BrownWall" names a UT texture."""
    if not ob.material_slots:
        return ""
    idx = face.material_index
    if idx >= len(ob.material_slots):
        return ""
    mat = ob.material_slots[idx].material
    if mat and "." in mat.name:
        return mat.name.split(":")[0].strip()
    return ""


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------

def export_t3d(context, filepath, selected_only=False, scale=UT_SCALE):
    objects = (context.selected_objects if selected_only
               else context.scene.objects)
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("no mesh objects to export")

    chunks = []
    problems = []
    for i, ob in enumerate(meshes):
        bm = bmesh.new()
        bm.from_mesh(ob.evaluated_get(
            context.evaluated_depsgraph_get()).to_mesh())
        bmesh.ops.triangulate(bm, faces=[])          # planar-safe n-gons below
        bm.free()

        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.transform(ob.matrix_world)
        bm.normal_update()

        ok, why = _is_convex(bm)
        if not ok:
            problems.append(f"{ob.name}: {why}")
            bm.free()
            continue

        # Vertices go out in WORLD space with Location left at the origin:
        # BRUSH IMPORT reads only the polygon list and ignores the actor's
        # Location, so centring the brush here would carve every room at the
        # origin and collapse the whole map into one space.
        csg = getattr(ob, "ut99_csg", "CSG_Subtract")
        tscale = getattr(ob, "ut99_scale", 4.0) or 1.0
        default_tex = getattr(ob, "ut99_texture", "")

        polys = []
        for f in bm.faces:
            # Both CSG operations use normals-out winding; Epic's own added
            # brushes are wound the same way as their subtracts. Flipping them
            # yields inside-out solids that silently zero the bot paths.
            verts = [v.co * scale for v in f.verts]
            normal = f.normal.copy()
            u, v = _tex_axes(normal)
            tex = _material_texture(ob, f) or default_tex

            lines = ["         Begin Polygon"]
            if tex:
                lines[0] += f" Texture={tex}"
            lines.append(f"            Origin   {_fmt(verts[0])}")
            lines.append(f"            Normal   {_fmt(normal)}")
            lines.append(f"            TextureU {_fmt(u / tscale)}")
            lines.append(f"            TextureV {_fmt(v / tscale)}")
            for vv in verts:
                lines.append(f"            Vertex   {_fmt(vv)}")
            lines.append("         End Polygon")
            polys.append("\n".join(lines))

        loc = Vector((0.0, 0.0, 0.0))
        name = f"Brush{i}"
        chunks.append("\n".join([
            f"   Begin Actor Class=Brush Name={name}",
            f"      CsgOper={csg}",
            "      MainScale=(SheerAxis=SHEER_ZX)",
            "      PostScale=(SheerAxis=SHEER_ZX)",
            f"      Location=(X={loc.x:.6f},Y={loc.y:.6f},Z={loc.z:.6f})",
            f"      Begin Brush Name=Model_{name}",
            "         Begin PolyList",
            "\n".join(polys),
            "         End PolyList",
            "      End Brush",
            f"      Brush=Model'MyLevel.Model_{name}'",
            "   End Actor",
        ]))
        bm.free()

    if problems:
        raise RuntimeError("; ".join(problems))

    with open(filepath, "w") as fh:
        fh.write("Begin Map\n" + "\n".join(chunks) + "\nEnd Map\n")
    return len(chunks)


# --------------------------------------------------------------------------
# import
# --------------------------------------------------------------------------

def import_t3d(context, filepath, scale=UT_SCALE):
    import re

    text = open(filepath, encoding="latin-1", errors="replace").read()
    made = 0
    for actor in text.split("Begin Actor")[1:]:
        csg = ("CSG_Add" if "CSG_Add" in actor else "CSG_Subtract")
        loc = (0.0, 0.0, 0.0)
        m = re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)",
                      actor)
        if m:
            loc = tuple(float(g) for g in m.groups())

        verts, faces = [], []
        for poly in actor.split("Begin Polygon")[1:]:
            idx = []
            for vm in re.finditer(
                    r"Vertex\s+([-+\d.]+),([-+\d.]+),([-+\d.]+)", poly):
                co = tuple(float(g) for g in vm.groups())
                verts.append(co)
                idx.append(len(verts) - 1)
            if len(idx) >= 3:
                faces.append(idx)
        if not faces:
            continue

        mesh = bpy.data.meshes.new(f"t3d_brush{made}")
        mesh.from_pydata([(x / scale, y / scale, z / scale)
                          for x, y, z in verts], [], faces)
        mesh.validate()
        mesh.update()

        ob = bpy.data.objects.new(mesh.name, mesh)
        ob.location = (loc[0] / scale, loc[1] / scale, loc[2] / scale)
        ob.ut99_csg = csg
        # Show rooms as wireframe: a solid box hides the space it encloses.
        ob.display_type = "WIRE" if csg == "CSG_Subtract" else "SOLID"
        context.collection.objects.link(ob)
        made += 1

    # Remove the duplicate verts from per-face vertex lists.
    for ob in context.collection.objects:
        if ob.type == "MESH" and ob.name.startswith("t3d_brush"):
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
            bm.to_mesh(ob.data)
            bm.free()
    return made


# --------------------------------------------------------------------------
# operators
# --------------------------------------------------------------------------

class UT99_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.ut99_t3d"
    bl_label = "Export Unreal T3D"
    filename_ext = ".t3d"
    filter_glob: StringProperty(default="*.t3d", options={"HIDDEN"})
    ut_scale: FloatProperty(name="UT units per metre", default=UT_SCALE,
                            min=1.0, soft_max=64.0)
    selection_only: bpy.props.BoolProperty(name="Selected only", default=False)

    def execute(self, context):
        try:
            n = export_t3d(context, self.filepath, self.selection_only,
                           self.ut_scale)
        except RuntimeError as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}
        self.report({"INFO"}, f"exported {n} brushes")
        return {"FINISHED"}


class UT99_OT_import(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.ut99_t3d"
    bl_label = "Import Unreal T3D"
    filename_ext = ".t3d"
    filter_glob: StringProperty(default="*.t3d", options={"HIDDEN"})
    ut_scale: FloatProperty(name="UT units per metre", default=UT_SCALE,
                            min=1.0, soft_max=64.0)

    def execute(self, context):
        n = import_t3d(context, self.filepath, self.ut_scale)
        self.report({"INFO"}, f"imported {n} brushes")
        return {"FINISHED"}


def _menu_export(self, context):
    self.layout.operator(UT99_OT_export.bl_idname, text="Unreal T3D (.t3d)")


def _menu_import(self, context):
    self.layout.operator(UT99_OT_import.bl_idname, text="Unreal T3D (.t3d)")


CLASSES = (UT99_PT_brush, UT99_OT_export, UT99_OT_import)


def register():
    _register_props()
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_export.append(_menu_export)
    bpy.types.TOPBAR_MT_file_import.append(_menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(_menu_export)
    bpy.types.TOPBAR_MT_file_import.remove(_menu_import)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
    _unregister_props()


if __name__ == "__main__":
    register()
