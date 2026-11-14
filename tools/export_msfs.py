"""Exporte le Disque Corona vers le package MSFS 2024 (voie « glTF standard + post-traitement »).

Usage : python export_msfs.py <modele.blend> <dossier_textures> <dossier_package>

- glTF séparé (.gltf + .bin), axes MSFS (X gauche, Y haut, Z avant), mètres, origine = point de référence.
- Identifiant ASOBO_unique_id sur chaque nœud.
- Textures PNG copiées dans common/texture avec leur fichier .png.xml ; carte normale convertie en convention DirectX.
- Animations des pieds regroupées en c_gear / l_gear / r_gear (0 = rentré, 100 = sorti).
"""
import json
import os
import shutil
import sys
import uuid

import bpy  # noqa: F401
import numpy as np
from PIL import Image

BLEND, TEX, PKG = (os.path.abspath(a) for a in sys.argv[1:4])
NAME = "DisqueCorona"
COMPANY = "r47lab"
AIRCRAFT_DIR = os.path.join(PKG, "PackageSources", "SimObjects", "Airplanes", f"{COMPANY}-disquecorona")
MODEL_DIR = os.path.join(AIRCRAFT_DIR, "common", "model")
TEX_DIR = os.path.join(AIRCRAFT_DIR, "common", "texture")
for d in (MODEL_DIR, TEX_DIR):
    os.makedirs(d, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene

# Faces simples (pas de double face) sur tous les matériaux
for m in bpy.data.materials:
    m.use_backface_culling = True

# L'intérieur provisoire et le noyau ne sont pas exportés en phase 1 (dôme opaque fumé)
for n in ("interior_shell", "interior_core"):
    ob = bpy.data.objects.get(n)
    if ob:
        bpy.data.objects.remove(ob)

scene.frame_set(0)
gl_path = os.path.join(MODEL_DIR, f"{NAME}_LOD0.gltf")
bpy.ops.export_scene.gltf(filepath=gl_path, export_format='GLTF_SEPARATE', export_yup=True, export_apply=True,
                          export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
                          export_cameras=False, export_lights=False, export_image_format='NONE',
                          export_extras=False)

g = json.load(open(gl_path, encoding="utf-8"))

# ---------------------------------------------------------------- nœuds
for n in g["nodes"]:
    n.setdefault("extensions", {})["ASOBO_unique_id"] = {"id": n["name"]}

# ---------------------------------------------------------------- textures
TEXTURES = [  # (fichier source, nom dans le package, slot MSFS, options XML)
    ("hull_albedo.png", "dc_hull_albd.png", "MTL_BITMAP_DECAL0", ""),
    ("hull_orm.png", "dc_hull_comp.png", "MTL_BITMAP_METAL_ROUGH_AO", "<ForceNoAlpha>true</ForceNoAlpha>"),
    ("hull_normal.png", "dc_hull_norm.png", "MTL_BITMAP_NORMAL", '<UserFlags Type="_DEFAULT">QUALITYHIGH</UserFlags>'),
    ("hull_emissive.png", "dc_hull_emis.png", "MTL_BITMAP_EMISSIVE", ""),
]
for src, dst, slot, extra in TEXTURES:
    s, d = os.path.join(TEX, src), os.path.join(TEX_DIR, dst)
    if slot == "MTL_BITMAP_NORMAL":
        a = np.asarray(Image.open(s).convert("RGB")).copy()
        a[..., 1] = 255 - a[..., 1]  # OpenGL -> DirectX (vert inversé)
        Image.fromarray(a).save(d, optimize=True)
    else:
        shutil.copyfile(s, d)
    with open(d + ".xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="utf-8"?>\n<BitmapConfiguration><BitmapSlot>{slot}</BitmapSlot>{extra}</BitmapConfiguration>\n')

g["images"] = [{"uri": f"../texture/{t[1]}"} for t in TEXTURES]
g["textures"] = [{"source": i, "name": os.path.splitext(t[1])[0]} for i, t in enumerate(TEXTURES)]
g.pop("samplers", None)

# ---------------------------------------------------------------- matériaux
EMISSIVE_SCALE = {"hull_alloy": 260.0, "emitter": 900.0, "ventral_lens": 1100.0}
for m in g["materials"]:
    nm = m["name"]
    m.pop("extensions", None)
    m["doubleSided"] = False
    pbr = m.setdefault("pbrMetallicRoughness", {})
    if nm == "hull_alloy":
        m["pbrMetallicRoughness"] = {"baseColorTexture": {"index": 0}, "metallicRoughnessTexture": {"index": 1},
                                     "metallicFactor": 1.0, "roughnessFactor": 1.0}
        m["occlusionTexture"] = {"index": 1}
        m["normalTexture"] = {"index": 2}
        m["emissiveTexture"] = {"index": 3}
        m["emissiveFactor"] = [EMISSIVE_SCALE[nm]] * 3
    else:
        for k in ("baseColorTexture", "metallicRoughnessTexture"):
            pbr.pop(k, None)
        for k in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            m.pop(k, None)
        if nm in EMISSIVE_SCALE:
            col = {"emitter": (0.74, 0.60, 1.0), "ventral_lens": (0.78, 0.68, 1.0)}[nm]
            m["emissiveFactor"] = [c * EMISSIVE_SCALE[nm] for c in col]
        if nm == "dome_glass":
            # Phase 1 : verre fumé opaque très brillant (le vrai verre viendra avec l'intérieur)
            pbr.update({"baseColorFactor": [0.035, 0.03, 0.05, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.04})
            m.pop("alphaMode", None)
g["extensionsUsed"] = ["ASOBO_unique_id"]
g.pop("extensionsRequired", None)

# ---------------------------------------------------------------- animations : regroupement par pied
node_name = {i: n["name"] for i, n in enumerate(g["nodes"])}
groups = {"c_gear": ("leg_0", "door_0"), "l_gear": ("leg_1", "door_1"), "r_gear": ("leg_2", "door_2")}
new_anims = []
for gname, owners in groups.items():
    samplers, channels = [], []
    for an in g.get("animations", []):
        for ch in an["channels"]:
            if node_name.get(ch["target"]["node"]) in owners:
                samplers.append(an["samplers"][ch["sampler"]])
                channels.append({"sampler": len(samplers) - 1, "target": ch["target"]})
    if channels:
        new_anims.append({"name": gname, "samplers": samplers, "channels": channels})
g["animations"] = new_anims

json.dump(g, open(gl_path, "w", encoding="utf-8"), separators=(",", ":"))

# ---------------------------------------------------------------- XML du modèle et model.cfg
GUID = {"c_gear": "E2E339A6-FCBF-43a9-A780-3473E03AB54B", "l_gear": "E6A307E6-D0D8-4ca0-8A8E-77B7EA22FFB9",
        "r_gear": "77C00B94-DDA1-450a-B725-1E2B4ADF6BC8"}
x = ['<?xml version="1.0" encoding="utf-8" ?>',
     '<!-- Généré par tools/export_msfs.py : ne pas modifier à la main. -->',
     f'<ModelInfo guid="{{{uuid.uuid5(uuid.NAMESPACE_DNS, "disque-corona.r47")}}}" version="1.1">',
     "\t<LODS>", f'\t\t<LOD minSize="0" ModelFile="{NAME}_LOD0.gltf"/>', "\t</LODS>"]
for a in new_anims:
    x.append(f'\t<Animation name="{a["name"]}" guid="{GUID[a["name"]]}" length="100" type="Sim" typeParam2="{a["name"]}" typeParam="AutoPlay" />')
for i, a in enumerate(new_anims):
    idx = {"c_gear": 0, "l_gear": 1, "r_gear": 2}[a["name"]]
    x.append(f"\t<PartInfo>\n\t\t<Name>{a['name']}</Name>\n\t\t<AnimLength>100</AnimLength>\n\t\t<Animation>\n\t\t\t<Parameter>\n\t\t\t\t<Sim>\n"
             f"\t\t\t\t\t<Variable>GEAR ANIMATION POSITION:{idx}</Variable>\n\t\t\t\t\t<Units>number</Units>\n\t\t\t\t\t<Scale>100</Scale>\n"
             f"\t\t\t\t\t<Bias>0</Bias>\n\t\t\t\t</Sim>\n\t\t\t</Parameter>\n\t\t</Animation>\n\t</PartInfo>")
x.append("</ModelInfo>")
open(os.path.join(MODEL_DIR, f"{NAME}.xml"), "w", encoding="utf-8").write("\n".join(x) + "\n")
open(os.path.join(MODEL_DIR, "model.cfg"), "w", encoding="utf-8").write(
    "; Généré par tools/export_msfs.py\n[model.options]\nwithExterior_showInterior=false\nwithInterior_showExterior=true\n\n[models]\nnormal=" + NAME + ".xml\n")

tri = sum(a["count"] for a in g["accessors"] if False)
print("noeuds :", len(g["nodes"]), "| matériaux :", [m["name"] for m in g["materials"]], "| animations :", [a["name"] for a in new_anims])
print("ok :", gl_path)
