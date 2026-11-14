"""Rendus photoréalistes du Disque Corona (Cycles).

Usage : python render_shots.py <modele.blend> <dossier_sortie> [plan ...] [--preview]
Plans : posee, crepuscule, dessous, detail
"""
import math
import os
import random
import sys

import bpy  # noqa: F401  (doit précéder bmesh)
import bmesh
from mathutils import Vector, noise

args = [a for a in sys.argv[1:] if not a.startswith("--")]
PREVIEW = "--preview" in sys.argv
BLEND, OUT = os.path.abspath(args[0]), os.path.abspath(args[1])
SHOTS = args[2:] or ["posee", "crepuscule", "dessous", "detail"]
GROUND = -1.62
EXPOSURE = 0.0

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
root = bpy.data.objects["DisqueCorona"]
P = lambda m: m.node_tree.nodes["Principled BSDF"]  # noqa: E731


# ------------------------------------------------------------ rendu
def setup_render(w, h, samples):
    scene.render.engine = 'CYCLES'
    cy = scene.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    cy.max_bounces = 8
    cy.glossy_bounces = 6
    cy.transmission_bounces = 8
    cy.volume_bounces = 1
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 0.5
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    scene.render.threads_mode = 'AUTO'


# ------------------------------------------------------------ monde
world = bpy.data.worlds.new("ciel")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
sky = wn.new("ShaderNodeTexSky")
sky.sky_type = 'MULTIPLE_SCATTERING'
bg = wn["Background"]
world.node_tree.links.new(sky.outputs["Color"], bg.inputs["Color"])

sun_data = bpy.data.lights.new("soleil", 'SUN')
sun_data.angle = math.radians(0.55)
sun = bpy.data.objects.new("soleil", sun_data)
scene.collection.objects.link(sun)


def set_sun(elev_deg, azim_deg, strength, sky_strength=1.0):
    for prop, val in [("sun_elevation", math.radians(elev_deg)), ("sun_rotation", math.radians(azim_deg)),
                      ("altitude", 1600.0), ("aerosol_density", 1.2), ("air_density", 1.0), ("ozone_density", 1.0)]:
        if hasattr(sky, prop):
            setattr(sky, prop, val)
    sky.sun_disc = False  # le disque est rendu par la lampe soleil
    bg.inputs["Strength"].default_value = sky_strength
    # Direction : élévation au-dessus de l'horizon, azimut mesuré depuis +Y vers +X (convention du ciel)
    e, a = math.radians(elev_deg), math.radians(azim_deg)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sun_data.energy = strength
    # couleur plus chaude près de l'horizon
    warm = max(0.0, min(1.0, 1 - elev_deg / 25))
    sun_data.color = (1.0, 1.0 - 0.22 * warm, 1.0 - 0.48 * warm)


# ------------------------------------------------------------ sol et décor
def desert_material():
    m = bpy.data.materials.new("desert")
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.035; n1.inputs["Detail"].default_value = 10; n1.inputs["Roughness"].default_value = 0.62
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 2.5; n2.inputs["Detail"].default_value = 6
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 22
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.30, (0.30, 0.20, 0.13, 1)
    cr.elements[1].position, cr.elements[1].color = 0.70, (0.58, 0.44, 0.31, 1)
    e = cr.elements.new(0.5); e.color = (0.45, 0.32, 0.21, 1)
    mix = nt.nodes.new("ShaderNodeMath"); mix.operation = 'MULTIPLY_ADD'
    mix.inputs[1].default_value = 0.22
    for n in (n1, n2, vor):
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n2.outputs["Fac"], mix.inputs[0])
    nt.links.new(n1.outputs["Fac"], mix.inputs[2])
    nt.links.new(mix.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.93
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.03
    add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'
    nt.links.new(n2.outputs["Fac"], add.inputs[0])
    nt.links.new(vor.outputs["Distance"], add.inputs[1])
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def rock_material():
    m = bpy.data.materials.new("roche")
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 9; n.inputs["Detail"].default_value = 10
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.16, 0.11, 0.08, 1)
    ramp.color_ramp.elements[1].color = (0.42, 0.33, 0.25, 1)
    nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.85
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


DESERT = desert_material()
ROCK = rock_material()


def build_terrain():
    """Sol plat détaillé près de l'appareil, relief montagneux au loin."""
    bm = bmesh.new()
    N, half = 300, 40000.0
    verts = []
    for iy in range(N + 1):
        row = []
        for ix in range(N + 1):
            # grille plus dense au centre
            fx = (ix / N) * 2 - 1
            fy = (iy / N) * 2 - 1
            x = math.copysign(abs(fx) ** 2.2, fx) * half
            y = math.copysign(abs(fy) ** 2.2, fy) * half
            dist = math.hypot(x, y)
            env = max(0.0, min(1.0, (dist - 7000) / 9000)) ** 1.2
            h = (noise.fractal(Vector((x / 7000, y / 7000, 0.3)), 0.55, 2.1, 7) * 0.5 + 0.45) * 650
            h += noise.ridged_multi_fractal(Vector((x / 4500, y / 4500, 1.7)), 0.8, 2.2, 6, 1.0, 2.0) * 380
            z = GROUND + env * max(0.0, h)
            # micro-ondulations près de l'appareil
            z += noise.noise(Vector((x / 9, y / 9, 0.5))) * 0.06 * (1 - env)
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)
    for iy in range(N):
        for ix in range(N):
            bm.faces.new((verts[iy][ix], verts[iy][ix + 1], verts[iy + 1][ix + 1], verts[iy + 1][ix]))
    me = bpy.data.meshes.new("terrain")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(DESERT)
    ob = bpy.data.objects.new("terrain", me)
    scene.collection.objects.link(ob)
    # assurer que le sol est exactement au niveau des patins sous l'appareil
    return ob


def scatter_rocks(n=420, radius=55.0, seed=7):
    rnd = random.Random(seed)
    bm_all = bmesh.new()
    for i in range(n):
        while True:
            x, y = rnd.uniform(-radius, radius), rnd.uniform(-radius, radius)
            if 6.5 < math.hypot(x, y) < radius:
                break
        s = rnd.random() ** 3 * 0.38 + 0.03
        tmp = bmesh.new()
        bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=s)
        off = Vector((rnd.random() * 10, rnd.random() * 10, rnd.random() * 10))
        for v in tmp.verts:
            v.co *= 1 + 0.35 * noise.noise(v.co / s * 0.9 + off)
            v.co.z *= 0.55
        bmesh.ops.rotate(tmp, verts=tmp.verts, cent=(0, 0, 0),
                         matrix=Vector((0, 0, 1)).rotation_difference(Vector((rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), 1))).to_matrix())
        bmesh.ops.translate(tmp, verts=tmp.verts, vec=(x, y, GROUND + s * 0.15))
        me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free(); bm_all.from_mesh(me); bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("rochers")
    bm_all.to_mesh(me)
    bm_all.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(ROCK)
    ob = bpy.data.objects.new("rochers", me)
    scene.collection.objects.link(ob)
    return ob


def scatter_scrub(n=160, radius=60.0, seed=11):
    """Touffes d'arbustes secs (créosote) : petites grappes de brindilles."""
    rnd = random.Random(seed)
    m = bpy.data.materials.new("arbuste")
    m.use_nodes = True
    P(m).inputs["Base Color"].default_value = (0.20, 0.19, 0.10, 1)
    P(m).inputs["Roughness"].default_value = 0.9
    bm_all = bmesh.new()
    for i in range(n):
        while True:
            x, y = rnd.uniform(-radius, radius), rnd.uniform(-radius, radius)
            if 8 < math.hypot(x, y) < radius:
                break
        size = rnd.uniform(0.35, 1.1)
        for k in range(int(26 * size) + 8):
            ang, tilt = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.15, 0.9)
            L = size * rnd.uniform(0.5, 1.0)
            d = Vector((math.cos(ang) * math.sin(tilt), math.sin(ang) * math.sin(tilt), math.cos(tilt)))
            p0 = Vector((x + rnd.uniform(-.08, .08), y + rnd.uniform(-.08, .08), GROUND))
            tmp = bmesh.new()
            bmesh.ops.create_cone(tmp, cap_ends=False, segments=4, radius1=0.012 * size, radius2=0.002, depth=L)
            bmesh.ops.rotate(tmp, verts=tmp.verts, cent=(0, 0, 0), matrix=Vector((0, 0, 1)).rotation_difference(d).to_matrix())
            bmesh.ops.translate(tmp, verts=tmp.verts, vec=p0 + d * L / 2)
            # feuillage : petites boules
            for t in (0.55, 0.8, 1.0):
                bmesh.ops.create_icosphere(tmp, subdivisions=1, radius=0.05 * size * rnd.uniform(0.6, 1.3),
                                           matrix=__import__("mathutils").Matrix.Translation(p0 + d * L * t))
            me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free(); bm_all.from_mesh(me); bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("arbustes")
    bm_all.to_mesh(me)
    bm_all.free()
    me.materials.append(m)
    ob = bpy.data.objects.new("arbustes", me)
    scene.collection.objects.link(ob)
    return ob


def haze(density):
    me = bpy.data.meshes.new("brume")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("brume", me)
    ob.scale = (80000, 80000, 3000)
    ob.location = (0, 0, 1400)
    scene.collection.objects.link(ob)
    m = bpy.data.materials.new("brume")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = (0.75, 0.80, 0.95, 1)
    vol.inputs["Anisotropy"].default_value = 0.6
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    me.materials.append(m)
    ob.visible_shadow = False
    return ob, vol


terrain = build_terrain()
rocks = scatter_rocks()
haze_ob, haze_vol = haze(0.000004)

# lumière ventrale (éclaire le sol en vol)
glow_data = bpy.data.lights.new("lueur_ventrale", 'SPOT')
glow_data.spot_size = math.radians(150)
glow_data.spot_blend = 1.0
glow_data.color = (0.72, 0.56, 1.0)
glow_data.shadow_soft_size = 0.7
glow = bpy.data.objects.new("lueur_ventrale", glow_data)
glow.parent = root
glow.location = (0, 0, -0.95)
glow.rotation_euler = (0, 0, 0)  # un spot éclaire vers -Z local
scene.collection.objects.link(glow)

# ------------------------------------------------------------ caméra
cam_data = bpy.data.cameras.new("camera")
cam_data.clip_start, cam_data.clip_end = 0.05, 40000
cam = bpy.data.objects.new("camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim(loc, target, lens, fstop=None, focus=None):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = lens
    cam_data.sensor_width = 36
    if fstop:
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = fstop
        cam_data.dof.focus_distance = focus or (Vector(target) - Vector(loc)).length
    else:
        cam_data.dof.use_dof = False


def emit(emitter, ventral, glow_w, glyph=2.0):
    P(bpy.data.materials["emitter"]).inputs["Emission Strength"].default_value = emitter
    P(bpy.data.materials["ventral_lens"]).inputs["Emission Strength"].default_value = ventral
    P(bpy.data.materials["hull_alloy"]).inputs["Emission Strength"].default_value = glyph
    glow_data.energy = glow_w


def shot(name, w, h, samples):
    setup_render(w // (2 if PREVIEW else 1), h // (2 if PREVIEW else 1), samples // (4 if PREVIEW else 1))
    scene.render.filepath = os.path.join(OUT, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendu :", scene.render.filepath, flush=True)


os.makedirs(OUT, exist_ok=True)
for name in SHOTS:
    if name == "posee":
        scene.frame_set(100)
        root.location = (0, 0, 0)
        set_sun(8, 245, 16, sky_strength=0.07)
        scene.view_settings.exposure = 0.15
        haze_vol.inputs["Density"].default_value = 0.000005
        emit(1.2, 0.12, 0)
        aim((-13.5, -19.0, 0.15), (0.3, 0.0, -0.35), 55, fstop=5.6)
        shot(name, 1920, 1080, 160)
    elif name == "crepuscule":
        scene.frame_set(0)
        root.location = (0, 0, 5.2)
        set_sun(-1.5, 260, 0.0, sky_strength=0.5)
        scene.view_settings.exposure = 0.6
        haze_vol.inputs["Density"].default_value = 0.000008
        emit(14, 30, 2600, glyph=6)
        aim((15.0, -21.0, -0.55), (0.0, 0.0, 3.6), 45, fstop=4.0)
        shot(name, 1920, 1080, 192)
    elif name == "dessous":
        scene.frame_set(0)
        root.location = (0, 0, 9.0)
        set_sun(38, 150, 16, sky_strength=0.07)
        scene.view_settings.exposure = -1.4
        haze_vol.inputs["Density"].default_value = 0.000004
        emit(2.5, 3.5, 0)
        aim((3.5, -6.5, -1.2), (-0.3, 0.6, 8.2), 26)
        shot(name, 1920, 1080, 160)
    elif name == "detail":
        scene.frame_set(100)
        root.location = (0, 0, 0)
        set_sun(14, 230, 16, sky_strength=0.07)
        scene.view_settings.exposure = 0.2
        emit(4, 1.0, 0, glyph=1.6)
        a = math.radians(-52)
        rim = Vector((4.70 * math.cos(a), 4.70 * math.sin(a), 0.0))
        out = Vector((math.cos(a), math.sin(a), 0))
        tan = Vector((-math.sin(a), math.cos(a), 0))
        aim(rim + out * 1.55 + tan * 0.55 + Vector((0, 0, 0.38)), rim + tan * 0.05, 85, fstop=3.2)
        shot(name, 1920, 1080, 160)
