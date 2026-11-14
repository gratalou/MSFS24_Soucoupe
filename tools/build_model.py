"""Construit le modèle 3D du Disque Corona avec Blender (bpy, sans interface).

Usage : python build_model.py <dossier_textures> <sortie.blend> [<export.gltf>]
Repère Blender : Z vers le haut, l'avant de l'appareil vers -Y.
"""
import math
import os
import sys

import bpy  # doit précéder bmesh
import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import saucer_profile as SP  # noqa: E402

TEX = os.path.abspath(sys.argv[1])
OUT_BLEND = os.path.abspath(sys.argv[2])
OUT_GLTF = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

TAU = 2 * math.pi
R4 = 4 * SP.R_TEX


# ---------------------------------------------------------------- matériaux
def principled(name, base=(0.8, 0.8, 0.8), metal=0.0, rough=0.5, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*base, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    if "emit" in kw:
        p.inputs["Emission Color"].default_value = (*kw["emit"], 1)
        p.inputs["Emission Strength"].default_value = kw.get("emit_strength", 1.0)
    if "transmission" in kw:
        p.inputs["Transmission Weight"].default_value = kw["transmission"]
    if "ior" in kw:
        p.inputs["IOR"].default_value = kw["ior"]
    if "coat" in kw:
        p.inputs["Coat Weight"].default_value = kw["coat"]
    return m


def image(name, colorspace):
    img = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def hull_material():
    m = principled("hull_alloy", metal=1.0, rough=0.2)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = image("hull_albedo.png", "sRGB"); tc.location = (-700, 300)
    to = nt.nodes.new("ShaderNodeTexImage"); to.image = image("hull_orm.png", "Non-Color"); to.location = (-700, 0)
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = image("hull_normal.png", "Non-Color"); tn.location = (-700, -300)
    te = nt.nodes.new("ShaderNodeTexImage"); te.image = image("hull_emissive.png", "sRGB"); te.location = (-700, -600)
    sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.location = (-400, 0)
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-400, -300)
    nt.links.new(tc.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(to.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    nt.links.new(te.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = 2.0
    return m


MAT = {
    "hull": hull_material(),
    "glass": principled("dome_glass", base=(0.045, 0.038, 0.06), rough=0.02, transmission=1.0, ior=1.52),
    "titanium": principled("titanium_dark", base=(0.50, 0.49, 0.52), metal=1.0, rough=0.26),
    "chrome": principled("chrome", base=(0.93, 0.93, 0.94), metal=1.0, rough=0.05),
    "foot": principled("foot_pad", base=(0.07, 0.07, 0.08), metal=0.2, rough=0.6),
    "cavity": principled("cavity", base=(0.05, 0.05, 0.06), metal=0.6, rough=0.45),
    "emitter": principled("emitter", base=(0.82, 0.78, 1.0), rough=0.08, emit=(0.74, 0.60, 1.0), emit_strength=4.0, coat=1.0),
    "ventral": principled("ventral_lens", base=(0.55, 0.50, 0.75), rough=0.06, emit=(0.78, 0.68, 1.0), emit_strength=3.0, coat=1.0),
    "bone": principled("interior_bone", base=(0.60, 0.58, 0.53), rough=0.65),
    "core": principled("interior_core", base=(0.5, 0.4, 0.8), rough=0.3, emit=(0.70, 0.52, 1.0), emit_strength=1.2),
}


# ---------------------------------------------------------------- outils
def new_object(name, bm, mat, parent=None, smooth=True, sharp_deg=40):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = smooth
    if smooth and sharp_deg:
        me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def revolve(profile, nseg, uv_fn=None):
    """Révolution d'un profil [(r, z, ...)] autour de Z. Normales vers l'extérieur
    si le profil va du bas vers le haut en passant par l'extérieur."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = []
    for p in profile:
        r, z = p[0], p[1]
        rings.append([bm.verts.new((r * math.cos(TAU * j / nseg), r * math.sin(TAU * j / nseg), z)) for j in range(nseg)])
    for i in range(len(rings) - 1):
        for j in range(nseg):
            j2 = (j + 1) % nseg
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            if uv_fn:
                for loop, (ii, jj) in zip(f.loops, [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]):
                    loop[uv].uv = uv_fn(ii, jj, loop.vert.co)
    return bm


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def set_origin(ob, point):
    point = Vector(point)
    ob.data.transform(__import__("mathutils").Matrix.Translation(-point))
    ob.location = ob.location + point


root = bpy.data.objects.new("DisqueCorona", None)
scene.collection.objects.link(root)

# ---------------------------------------------------------------- coque
PROF = SP.build_profile()
i0, i1, S_ARC, TOTAL, _ = SP.rim_arc_info(PROF)
NSEG = 384


def hull_uv(i, j, co):
    tag = PROF[i][2] if i < len(PROF) - 1 else PROF[i - 1][2]
    if i in range(i0, i1 + 1) and (tag == 'rim' or i == i1):
        # Bande du bord (les points i0..i1 inclus)
        pass
    seg_tag = PROF[min(i, len(PROF) - 2)][2]
    return None


def make_hull():
    # Tag par segment (ligne de faces i -> i+1)
    seg_tags = [PROF[i][2] for i in range(len(PROF) - 1)]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = []
    for (r, z, _t) in PROF:
        rings.append([bm.verts.new((r * math.cos(TAU * j / NSEG), r * math.sin(TAU * j / NSEG), z)) for j in range(NSEG)])
    for i in range(len(rings) - 1):
        tag = seg_tags[i]
        for j in range(NSEG):
            j2 = (j + 1) % NSEG
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            for loop, (ii, jj) in zip(f.loops, [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]):
                x, y = loop.vert.co.x, loop.vert.co.y
                if tag == 'upper':
                    loop[uv].uv = (0.25 + x / R4, 0.75 + y / R4)
                elif tag == 'lower':
                    loop[uv].uv = (0.75 + x / R4, 0.75 + y / R4)
                else:
                    u = jj / NSEG * SP.RIM_REPEAT
                    v = S_ARC[ii - i0] / TOTAL * 0.125
                    loop[uv].uv = (u, v)
    return new_object("hull", bm, MAT["hull"], root, sharp_deg=38)


hull = make_hull()

# ---------------------------------------------------------------- collerette, dôme, capuchon
collar_prof = SP.COLLAR + [SP.COLLAR[0]]
bm = revolve(collar_prof, 256, lambda i, j, co: (j / 256 * 8, i / len(collar_prof)))
collar = new_object("collar", bm, MAT["titanium"], root, sharp_deg=50)

dome_pts = SP._catmull(SP.DOME_CTRL, 10)
dome_pts = [p for p in dome_pts if p[0] >= 0.13]
bm = revolve(dome_pts, 256, lambda i, j, co: (0.5 + co.x / 4, 0.5 + co.y / 4))
dome = new_object("dome_glass", bm, MAT["glass"], root, sharp_deg=0)
sol = dome.modifiers.new("epaisseur", "SOLIDIFY")
sol.thickness = 0.012
sol.offset = -1
apply_modifiers(dome)

cap_prof = [(0.001, 1.986), (0.13, 1.986), (0.16, 1.992), (0.165, 2.002), (0.15, 2.016), (0.10, 2.026), (0.001, 2.030)]
bm = revolve(cap_prof, 96, lambda i, j, co: (j / 96, i / 7))
cap = new_object("dome_cap", bm, MAT["chrome"], root, sharp_deg=45)

# ---------------------------------------------------------------- émetteurs de la couronne
bm_l = bmesh.new()
bm_b = bmesh.new()
for k in range(SP.N_EMITTERS):
    a = math.radians((k + 0.5) * 360 / SP.N_EMITTERS)
    m_rot = __import__("mathutils").Matrix.Rotation(a, 4, 'Z')
    # Lentille : demi-sphère aplatie orientée vers l'extérieur (+X local)
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=24, v_segments=12, radius=0.028)
    for v in tmp.verts:
        v.co.x *= 0.62
        v.co.x += 4.655
    bmesh.ops.transform(tmp, matrix=m_rot, verts=tmp.verts)
    me_tmp = bpy.data.meshes.new("tmp"); tmp.to_mesh(me_tmp); tmp.free()
    bm_l.from_mesh(me_tmp); bpy.data.meshes.remove(me_tmp)
    # Lunette
    tmp = bmesh.new()
    rot_y = __import__("mathutils").Matrix.Rotation(math.pi / 2, 4, 'Y')
    seg_major, seg_minor, R_maj, r_min = 24, 8, 0.031, 0.0045
    ring_verts = []
    for ia in range(seg_major):
        th = TAU * ia / seg_major
        row = []
        for ib in range(seg_minor):
            ph = TAU * ib / seg_minor
            p = Vector(((R_maj + r_min * math.cos(ph)) * math.cos(th), (R_maj + r_min * math.cos(ph)) * math.sin(th), r_min * math.sin(ph)))
            row.append(tmp.verts.new(p))
        ring_verts.append(row)
    for ia in range(seg_major):
        for ib in range(seg_minor):
            tmp.faces.new((ring_verts[ia][ib], ring_verts[(ia + 1) % seg_major][ib], ring_verts[(ia + 1) % seg_major][(ib + 1) % seg_minor], ring_verts[ia][(ib + 1) % seg_minor]))
    bmesh.ops.transform(tmp, matrix=rot_y, verts=tmp.verts)
    for v in tmp.verts:
        v.co.x += 4.664
    bmesh.ops.transform(tmp, matrix=m_rot, verts=tmp.verts)
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    me_tmp = bpy.data.meshes.new("tmp"); tmp.to_mesh(me_tmp); tmp.free()
    bm_b.from_mesh(me_tmp); bpy.data.meshes.remove(me_tmp)
uvl = bm_l.loops.layers.uv.verify()
emitters = new_object("emitters", bm_l, MAT["emitter"], root, sharp_deg=0)
bezels = new_object("emitter_bezels", bm_b, MAT["chrome"], root, sharp_deg=0)

# ---------------------------------------------------------------- lentille ventrale (anneaux de Fresnel)
lens_prof = []
NR = 7
for k in range(NR):
    ra, rb = k * 0.80 / NR, (k + 1) * 0.80 / NR

    def zb(r):
        return -0.848 - 0.012 * (1 - (r / 0.8) ** 2)

    if k == 0:
        lens_prof.append((0.001, zb(0.001) + 0.004))
    lens_prof.append((ra + 0.004, zb(ra) + 0.004))
    lens_prof.append((rb - 0.003, zb(rb)))
    lens_prof.append((rb - 0.0005, zb(rb) + 0.004))
lens_prof.append((0.80, -0.842))
bm = revolve(lens_prof, 192, lambda i, j, co: (0.5 + co.x / 1.7, 0.5 + co.y / 1.7))
ventral = new_object("ventral_lens", bm, MAT["ventral"], root, sharp_deg=30)


# ---------------------------------------------------------------- trappes, cavités, pieds
def rrect_outline(hl, hw, c, n=10):
    pts = []
    for cx, cy, a0 in [(hl - c, hw - c, 0), (-(hl - c), hw - c, 90), (-(hl - c), -(hw - c), 180), (hl - c, -(hw - c), 270)]:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + c * math.cos(a), cy + c * math.sin(a)))
    return pts


def door_frame(a_deg):
    a = math.radians(a_deg)
    rad = Vector((math.cos(a), math.sin(a), 0))
    tan = Vector((-math.sin(a), math.cos(a), 0))
    c = rad * SP.LEG_DOOR_R
    return c, rad, tan


def prism(name, a_deg, shrink=0.0, z0=-1.4, z1=0.3):
    c, rad, tan = door_frame(a_deg)
    out = rrect_outline(SP.LEG_DOOR_LEN / 2 - shrink, SP.LEG_DOOR_WID / 2 - shrink, SP.LEG_DOOR_CORNER - shrink)
    bm = bmesh.new()
    bot = [bm.verts.new(c + rad * u + tan * v + Vector((0, 0, z0))) for u, v in out]
    top = [bm.verts.new(c + rad * u + tan * v + Vector((0, 0, z1))) for u, v in out]
    n = len(out)
    for i in range(n):
        bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    return ob


def boolean(target, cutter, op):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.object = cutter
    mod.operation = op
    mod.solver = 'EXACT'
    apply_modifiers(target)


doors, legs = [], []
cavity_bm = bmesh.new()
Z_TOP = 0.30
for li, a_deg in enumerate(SP.LEG_ANGLES):
    c, rad, tan = door_frame(a_deg)
    # Panneau de trappe : intersection d'une copie de la coque avec un prisme légèrement réduit
    panel = bpy.data.objects.new(f"door_{li}", hull.data.copy())
    scene.collection.objects.link(panel)
    panel.parent = root
    cut_small = prism(f"cut_small_{li}", a_deg, shrink=0.0035)
    boolean(panel, cut_small, 'INTERSECT')
    bpy.data.objects.remove(cut_small)
    zc = SP.z_lower(SP.LEG_DOOR_R)
    set_origin(panel, (c.x, c.y, zc))
    doors.append(panel)
    # Ouverture dans la coque
    cut = prism(f"cut_{li}", a_deg)
    boolean(hull, cut, 'DIFFERENCE')
    bpy.data.objects.remove(cut)
    # Cavité : parois verticales depuis la surface jusqu'au plafond
    out = rrect_outline(SP.LEG_DOOR_LEN / 2, SP.LEG_DOOR_WID / 2, SP.LEG_DOOR_CORNER)
    bots, tops = [], []
    for u, v in out:
        p = c + rad * u + tan * v
        zr = SP.z_lower(math.hypot(p.x, p.y)) - 0.006
        bots.append(cavity_bm.verts.new((p.x, p.y, zr)))
        tops.append(cavity_bm.verts.new((p.x, p.y, Z_TOP)))
    n = len(out)
    for i in range(n):
        cavity_bm.faces.new((tops[i], tops[(i + 1) % n], bots[(i + 1) % n], bots[i]))
    cavity_bm.faces.new(list(reversed(tops)))

cavity = new_object("leg_bays", cavity_bm, MAT["cavity"], root, sharp_deg=30)


def cyl_between(bm, p0, p1, radius, seg=24):
    d = p1 - p0
    L = d.length
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, segments=seg, radius1=radius, radius2=radius, depth=L)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.rotate(tmp, verts=tmp.verts, cent=(0, 0, 0), matrix=q.to_matrix())
    bmesh.ops.translate(tmp, verts=tmp.verts, vec=(p0 + p1) / 2)
    me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free()
    bm.from_mesh(me); bpy.data.meshes.remove(me)


def sphere_at(bm, p, radius):
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=20, v_segments=10, radius=radius)
    bmesh.ops.translate(tmp, verts=tmp.verts, vec=p)
    me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free()
    bm.from_mesh(me); bpy.data.meshes.remove(me)


LEG_TOP_R, LEG_TOP_Z = 2.30, -0.45
FOOT_R, FOOT_Z = 2.95, SP.GROUND_Z + 0.05
RETRACT = 1.05
for li, a_deg in enumerate(SP.LEG_ANGLES):
    c, rad, tan = door_frame(a_deg)
    top = rad * LEG_TOP_R + Vector((0, 0, LEG_TOP_Z))
    foot = rad * FOOT_R + Vector((0, 0, FOOT_Z))
    d = (foot - top)
    bm_t, bm_c, bm_f = bmesh.new(), bmesh.new(), bmesh.new()
    cyl_between(bm_t, top, top + d * 0.62, 0.092)
    cyl_between(bm_t, top + d * 0.585, top + d * 0.625, 0.108)   # bague
    cyl_between(bm_c, top + d * 0.55, top + d * 0.93, 0.062)    # tige polie
    sphere_at(bm_t, foot + Vector((0, 0, 0.075)), 0.082)          # rotule
    # Bras de contrefiche
    brace0 = rad * 2.06 + Vector((0, 0, -0.52))
    cyl_between(bm_t, brace0, top + d * 0.52, 0.034, 16)
    # Patin
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, segments=40, radius1=0.215, radius2=0.19, depth=0.05)
    bmesh.ops.translate(tmp, verts=tmp.verts, vec=foot + Vector((0, 0, -0.025)))
    me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free(); bm_f.from_mesh(me); bpy.data.meshes.remove(me)
    leg = new_object(f"leg_{li}", bm_t, MAT["titanium"], root, sharp_deg=50)
    rod = new_object(f"leg_{li}_rod", bm_c, MAT["chrome"], leg, sharp_deg=50)
    pad = new_object(f"leg_{li}_pad", bm_f, MAT["foot"], leg, sharp_deg=50)
    pad_bev = pad.modifiers.new("bev", "BEVEL"); pad_bev.width = 0.008; pad_bev.segments = 3
    apply_modifiers(pad)
    set_origin(leg, top)
    # rod et pad sont enfants de leg : compenser le déplacement d'origine
    for ch in (rod, pad):
        ch.location = ch.location - (top - Vector((0, 0, 0)))
        ch.data.transform(__import__("mathutils").Matrix.Translation((0, 0, 0)))
    legs.append((leg, d.normalized(), tan))

# ---------------------------------------------------------------- intérieur provisoire (visible à travers le dôme)
bm = bmesh.new()
floor = revolve([(0.001, 0.33), (1.60, 0.33)], 128, lambda i, j, co: (0.5 + co.x / 4, 0.5 + co.y / 4))
me = bpy.data.meshes.new("tmp"); floor.to_mesh(me); floor.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
wall = revolve([(1.60, 0.84), (1.60, 0.33)], 128, lambda i, j, co: (j / 128, i))
me = bpy.data.meshes.new("tmp"); wall.to_mesh(me); wall.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
interior = new_object("interior_shell", bm, MAT["bone"], root, sharp_deg=60)
bm = revolve([(0.001, 0.33), (0.11, 0.33), (0.13, 0.40), (0.06, 1.05), (0.13, 1.68), (0.11, 1.74), (0.001, 1.74)], 48, lambda i, j, co: (j / 48, i / 4))
core = new_object("interior_core", bm, MAT["core"], root, sharp_deg=60)

# ---------------------------------------------------------------- animation des pieds (0 = rentré, 100 = sorti)
for li, (leg, dn, tan) in enumerate(legs):
    deployed = leg.location.copy()
    leg.location = deployed - dn * RETRACT
    leg.keyframe_insert("location", frame=0)
    leg.keyframe_insert("location", frame=40)
    leg.location = deployed
    leg.keyframe_insert("location", frame=100)
    door = doors[li]
    closed = door.location.copy()
    door.keyframe_insert("location", frame=0)
    door.location = closed + Vector((0, 0, 0.07))
    door.keyframe_insert("location", frame=15)
    door.location = closed + Vector((0, 0, 0.07)) + tan * 0.64
    door.keyframe_insert("location", frame=40)
    door.keyframe_insert("location", frame=100)

scene.frame_start, scene.frame_end = 0, 100
scene.frame_set(100)

# Nettoyage
for ob in list(bpy.data.objects):
    if ob.name.startswith("cut"):
        bpy.data.objects.remove(ob)

tris = sum(len(o.data.loop_triangles) if o.type == 'MESH' else 0 for o in bpy.data.objects if not (o.data.calc_loop_triangles() if o.type == 'MESH' else None))
print("Triangles :", tris)
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print("blend :", OUT_BLEND)

if OUT_GLTF:
    os.makedirs(os.path.dirname(OUT_GLTF), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=OUT_GLTF, export_format='GLTF_SEPARATE', export_yup=True,
                              export_animations=True, export_texture_dir="textures", export_apply=True)
    print("gltf :", OUT_GLTF)
