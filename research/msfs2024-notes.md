# MSFS 2024 add-on research notes (flying saucer on the HELICOPTER flight model)

Researched 2026-11-14. Scope: what is needed to go from a `bpy`-generated model on Linux to a
package the user builds with the free MSFS 2024 SDK on Windows.

**How to read this file**

- **VERIFIED (source)** means I read it in source code or files in a public repo, cloned under
  `research/repos/` (paths below are relative to `research/`).
- **VERIFIED-IN-SIM (3rd party)** means a public project states it tested the behavior in MSFS 2024.
- **SEARCH-SNIPPET** means it comes from web-search summaries of the official docs. I could not
  open the pages themselves (see the network limits below), so it is likely but second-hand.
- **UNVERIFIED** means memory, inference or a single forum post. Check it before relying on it.

**Network limits met:** `docs.flightsimulator.com`, `devsupport.flightsimulator.com`, `fsdeveloper.com`,
`context7.com`, `apollomaniacs.com` and doc mirrors do not resolve from this container, through curl
or WebFetch. To read the official SDK pages, allow `docs.flightsimulator.com` in the session's
network settings. Tip from a 3rd-party project: on the new doc site, adding `index.md` to a page
URL returns its Markdown source
(`samples/f104-djcolumbia-2024-modular/docs/notes/msfs2024-sdk.md`). GitHub cloning worked.

---

## 0. Quick answers / decisions

| Question | Answer | Confidence |
|---|---|---|
| Official MSFS 2024 Blender exporter | `io_scene_gltf2_msfs_2024`, shipped **inside the MSFS 2024 SDK** at `<SDK>\Tools\Blender\addons\io_scene_gltf2_msfs_2024` with its helper package `_addons_common` (current version 8.4.2 = SDK 1.8.2). There is **no official public GitHub repo** for it. `AsoboStudio/glTF-Blender-IO-MSFS` (branches `main`, `update_to_blender_4_5`) is the **MSFS 2020** exporter. | VERIFIED (source; see §1.1) |
| Blender versions | The 2024 add-on has `bl_info.blender = (3,3,0)`, and its code branches for 3.3 / 3.6 / 4.2 / 4.5 / 5.2. Docs, quoted on forums: 3.6 LTS, 4.2 LTS, 4.5 LTS. **Use Blender 4.5 LTS** (pip `bpy` 4.5 on Python 3.11) for the Asobo route. bpy 5.3 is UNVERIFIED with the add-on. | VERIFIED (source) + SEARCH-SNIPPET |
| Headless use | **Yes.** The add-on itself exports from a `blender --background` subprocess with `bpy.ops.msfs2024.multi_export_gltf(...)`. Calling plain `bpy.ops.export_scene.gltf` alone does **NOT** add the MSFS extensions. | VERIFIED (source) |
| Plain glTF from stock Blender exporter | **Accepted by MSFS 2024** (Blender 5.2 exporter, no Asobo add-on, PNG + `.png.xml` textures), as long as you add `ASOBO_unique_id` per node by post-processing. You lose the Asobo material types (glass, etc.) unless you hand-write the extensions. | VERIFIED-IN-SIM (3rd party) |
| Aircraft project type for 2024 | `ModularSimObject` asset group with `common/` + `presets/` (+ optional `liveries/`, `attachments/`). 2020-style `SimObject` packages still load in 2024 as "legacy". | VERIFIED (3rd-party 2024 repo) + SEARCH-SNIPPET |
| Textures | Put PNGs plus a sidecar `<name>.png.xml` (BitmapConfiguration) in the `texture` folder. The 2024 package builder compiles them to **KTX2** (2020 built DDS). | VERIFIED-IN-SIM (3rd party) + SEARCH-SNIPPET |
| Official helicopter sample | **Cabri G2** sample in the MSFS 2024 SDK, downloadable from the Dev Mode Help menu. It holds a full helicopter project plus model source files. **The user should start from it** for the 2024 rotorcraft cfgs. | SEARCH-SNIPPET |
| EFB apps / HTML HUD | Both exist. EFB: SDK "EFB Template Sample" + "Electronic Flight Bag API". HUD: `panel.cfg` `[VCockpitNN]` with `htmlgauge00=` rendering onto a mesh material named `$NAME`. | VERIFIED (3rd-party repos) + SEARCH-SNIPPET |

---

## 1. Blender exporter for MSFS 2024

### 1.1 Which exporter / where it lives

- **MSFS 2024 exporter = `io_scene_gltf2_msfs_2024`**, bl_info name "Microsoft Flight Simulator 2024: glTF Extension"
  ("author": "Asobo Studio (ykhodja and mrichecoeur)", "version": (8, 4, 2), "blender": (3, 3, 0)).
  - Ships in the SDK. A 3rd-party note gives the path `C:\MSFS 2024 SDK\Tools\Blender\addons\io_scene_gltf2_msfs_2024`
    (`samples/f104-djcolumbia-2024-modular/docs/notes/3d-model.md`). Forum reports say `_addons_common` must sit
    next to it (SEARCH-SNIPPET, fsdeveloper thread "nothing works with blender 3, 4 ... io_import_export_msfs2024").
  - The add-on imports `_addons_common` (`from _addons_common.registration import Registration`), so you must copy
    both folders. VERIFIED: `repos/asobo2024-upstream/io_scene_gltf2_msfs_2024/__init__.py`.
  - Public copy of the vanilla code, used for this research: `https://github.com/uraymeiviar/msfs2024-blender-addons`,
    branch **`upstream`**, commit "upstream: Asobo MSFS 2024 Blender exporter 8.4.2 (SDK 1.8.2)", cloned to
    `repos/asobo2024-upstream/` (Apache-2.0). This is a community mirror, not Asobo's: diff it against the copy in
    the user's SDK before trusting details.
  - Other community repackagings: `GRD-Brasil/GRD_gltf2_msfs2024` (`repos/GRD-Brasil_GRD_gltf2_msfs2024`; Blender
    4.2-5.x extension build, v6.4.9) and `uraymeiviar/msfs-blender-5-addons` (unified 2020+2024 fork for Blender 5.2).
- **`AsoboStudio/glTF-Blender-IO-MSFS`** (= `AsoboStudio/Microsoft-Flight-Simulator-2020-glTF-Blender-IO`; `git
  ls-remote` shows both resolve to the same commits), branches `main` and `update_to_blender_4_5`: README title
  "Microsoft Flight Simulator **2020** glTF 2.0 Importer and Exporter for Blender". Supported Blender versions:
  3.3.x, 3.6.x, 4.2.x, 4.5.x LTS (`repos/asobo-4_5/README.md`). Do not use it for 2024-native work, and do not enable
  the 2020 and 2024 add-ons together: the 2024 add-on's `scene_loading.prepare_scenes()` checks for
  `io_scene_gltf2_msfs`, and GRD-Brasil's README warns about it.

### 1.2 Supported Blender versions (2024 add-on 8.4.2)

- Code branches on `bpy.app.version` at 3.3, 3.6, 4.2, 4.5 and 5.2. Examples: `io/exp/multi_export.py` has
  `_export_blender_3_3/_3_6/_4_2`; `ui/exp/export_settings_panel.py` has `>= (5, 2, 0)`; `blender/msfs_gizmo.py` has
  `>= (5,2,0)`. The uraymeiviar README says "Asobo exporter 8.4.2 (SDK 1.8.2, which supports Blender 5.2 itself)".
  VERIFIED (source).
- Officially documented, as quoted on a forum: "only compatible with Blender 3.6.x LTS, 4.2.x LTS, and 4.5.x LTS".
  SEARCH-SNIPPET.
- **Recommendation:** use the Blender 4.5 LTS binary, or pip `bpy==4.5.*` (Python 3.11, through `uv`). bpy 5.3 is
  newer than anything the code checks. The add-on reaches into Khronos `io_scene_gltf2` internals, for example
  `from io_scene_gltf2.blender.exp import accessors`, so a newer Blender can break it. **UNVERIFIED for 5.3.**

### 1.3 Headless export (how the add-on actually exports)

Facts read in the source, all VERIFIED:

1. The add-on hooks the stock Khronos exporter through `glTF2ExportUserExtension` (`__init__.py`, which wraps
   `io/exp/gltf_hooks.py: Export`). **Every hook returns early unless `Export.msfs_export_settings` is set and
   `enable_msfs_extension` is true** (`_hooks_enabled()`). Only the operator **`bpy.ops.msfs2024.multi_export_gltf`**
   sets them. So a direct `bpy.ops.export_scene.gltf()` gives a plain glTF, even with the add-on enabled.
2. Asobo's own "background export" (`scene.msfs_background_export`) launches
   `blender --background --factory-startup --disable-autoexec -noaudio --python-expr ... [--offline-mode]` with env
   `MSFS_HANDLERS_DISABLED=True` (`io/exp/subprocess.py`, `blender/msfs_handlers.py`). It then runs
   `io/exp/subprocess_script.py`:
   ```python
   bpy.ops.preferences.addon_enable(module='io_scene_gltf2_msfs_2024')   # hooks only load if enabled
   bpy.ops.wm.open_mainfile(filepath=scene)
   bpy.ops.msfs2024.multi_export_gltf(export_mode=export_mode, called_in_subprocess=True, profiling=...)
   ```
3. What gets exported is the scene's LOD groups (`scene.msfs_multi_exporter_lod_groups`). With
   `scene.msfs_export_mode = "OBJECTS"`, `lod_groups.reload_lod_groups(scene, reset=True)` makes one LOD per
   **top-level object** (parent is None) and includes its children recursively. Names matching
   `^x[0-9]_|_lod[0-9]+$` (case-insensitive) are grouped: for example `Saucer_LOD0` and `Saucer_LOD1` form group
   `Saucer`. Per group, set `folder_path` (it must exist; the setter stores it blend-relative, **so save the .blend
   first**: on Linux an unsaved scene turns `/abs/path` into `//abs/path`), `enabled`, `generate_xml`,
   `autogenerate_lods`, and per LOD `enabled`, `lod_value` (becomes `minSize`) and `file_name`.
   Sources: `io/exp/lod_groups.py`, `io/com/msfs_path_utils.py`, `io/exp/multi_export.py:get_export_folder`.
4. Export settings live in the scene presets: `export_settings.init_setting_presets(scene)` creates "Default", and
   `get_active_export_settings(scene)` returns it. Notable fields: `enable_msfs_extension` (default True),
   `generate_texturelib` (default True, writes texture XMLs), `export_animation_mode` (default `NLA_TRACKS` on
   Blender >= 4.2, so **each NLA track becomes one glTF animation, named after the track**), `reset_origins`,
   `remove_lod_prefix`, `merge_nodes`. The exporter always writes `GLTF_SEPARATE` (.gltf + .bin), `export_yup=True`
   when MSFS extensions are on, tangents off, and at most 4 skin influences.
5. A **3rd-party harness drives exactly this headless**:
   `repos/uraymeiviar_msfs-blender-5-addons/tests/harness/blender_case.py` (`_export_2024`), run with
   `blender --background --factory-startup --python blender_case.py -- --addon ... --case ... --out ...`. It
   enables the add-on with `addon_utils.enable(name, default_set=True, persistent=False)`, adding the comment "the
   Khronos exporter only discovers glTF2ExportUserExtension from add-ons registered in preferences". Copy:
   `samples/blender-headless-export/blender_case.py` and `scenes.py`. The latter sets every `msfs_*` material
   property from code.
6. **Template for this project:** `samples/blender-headless-export/export_msfs2024_headless.py`. It combines both
   sources, sets `MSFS_HANDLERS_DISABLED` like Asobo does (the load_post handler would otherwise touch
   `bpy.context.window`, which is None in background mode), and calls the operator with
   `called_in_subprocess=True`. It was **not run here**: no Blender in the container, and the SDK add-on is
   Windows-delivered.

Outputs per LOD group (VERIFIED, `io/exp/xml_export.py`, `io/exp/texture_lib/*`):

- `<lod file_name>.gltf` + `.bin` per LOD.
- `<GroupName>.xml`, written or updated conservatively, only the `<LODS>` block:
  ```xml
  <ModelInfo guid="{uuid4}" version="1.1">
    <LODS>
      <LOD minSize="<lod_value>" ModelFile="Saucer_LOD0.gltf"/>
      <LOD ModelFile="Saucer_LOD1.gltf"/>   <!-- last LOD has no minSize -->
    </LODS>
  </ModelInfo>
  ```
  `autogenerate_lods=True` gives `<LODS autoGenerate="true">`, and the 2024 build then makes LODs with Simplygon.
- `<texture file>.xml` next to each texture (for example `Hull_ALBD.png.xml`), when `generate_texturelib` is on:
  `<BitmapConfiguration><BitmapSlot>MTL_BITMAP_...</BitmapSlot>[<UserFlags Type="_DEFAULT">...</UserFlags>][<ForceNoAlpha>true</ForceNoAlpha>]</BitmapConfiguration>`.

### 1.4 Material model: exact Python property names (2024 add-on)

All are on `bpy.types.Material`, from `io/com/extensions/material/*.py` and
`blender/utils/msfs_material_utils.py`. VERIFIED (source).

**Material type** `msfs_material_type` (EnumProperty; set it first, because its update callback rebuilds the node
tree into Asobo's node group):
`NONE` (Disabled), `msfs_standard`, `msfs_decal`, `msfs_geo_decal_frosted`, `msfs_windshield`, `msfs_porthole`,
`msfs_glass`, `msfs_clearcoat`, `msfs_parallax_window`, `msfs_anisotropic`, `msfs_hair`, `msfs_sss`,
`msfs_invisible`, `msfs_fake_terrain`, `msfs_fresnel_fade`, `msfs_environment_occluder`, `msfs_ghost`,
`msfs_geo_decal_blendmasked`, `msfs_sail`, `msfs_propeller`, `msfs_tree`, `msfs_vegetation`, `msfs_tire`.
There is **no separate "emissive" type**: emission is part of every type, through the properties below.

**Common properties (with defaults):**

| Property | Type / default | glTF output |
|---|---|---|
| `msfs_base_color_factor` | RGBA, (1,1,1,1) | `pbrMetallicRoughness.baseColorFactor` |
| `msfs_metallic_factor` | 0..1, 1.0 | `metallicFactor` |
| `msfs_roughness_factor` | 0..1, 1.0 | `roughnessFactor` |
| `msfs_emissive_factor` | RGB 0..1, (0,0,0) | `emissiveFactor = color * msfs_emissive_scale` |
| `msfs_emissive_scale` | 0..200000, **1000.0** (it was 1.0 in the 2020 add-on) | multiplies into emissiveFactor; `KHR_materials_emissive_strength` is removed. Unit UNVERIFIED (probably nits) |
| `msfs_emissive_day_multiplier`, `msfs_emissive_night_multiplier` | 1.0 | `ASOBO_material_emissive.{emissiveDayMultiplier, emissiveNightMultiplier}` |
| `msfs_normal_scale` | 1.0 | `normalTexture.scale` |
| `msfs_alpha_mode` | `OPAQUE` / `MASK` / `BLEND` / `DITHER` | alphaMode (DITHER uses `ASOBO_material_alphamode_dither`) |
| `msfs_alpha_cutoff` | 0.5 | alphaCutoff (MASK only) |
| `msfs_double_sided` | False | doubleSided |
| `msfs_base_color_texture` | Image | baseColorTexture |
| `msfs_occlusion_metallic_roughness_texture` | Image | metallicRoughnessTexture **and** occlusionTexture (same image) |
| `msfs_normal_texture` | Image | normalTexture |
| `msfs_emissive_texture` | Image | emissiveTexture |
| `msfs_occlusion_strength` | 1.0 | `ASOBO_occlusion_strength` |
| `msfs_draw_order_offset` | 0 | `ASOBO_material_draw_order` |
| `msfs_no_cast_shadow` | False | `ASOBO_material_shadow_options` |
| `msfs_day_night_cycle` | False | `ASOBO_material_day_night_switch` |
| `msfs_disable_motion_blur` | False | `ASOBO_material_disable_motion_blur` |
| `msfs_flip_back_face_normal` | False | `ASOBO_material_flip_back_face` |
| `msfs_uv_offset_u/v`, `msfs_uv_tiling_u/v`, `msfs_uv_rotation`, `msfs_clamp_uv_x/y` | | `ASOBO_material_UV_options` (animatable) |
| `msfs_collision_material`, `msfs_road_collision_material`, `msfs_ground_collision_material` | False | collision flags |
| `msfs_receive_rain`, `msfs_rain_drop_tiling`, `msfs_rain_on_backface` | | `ASOBO_material_rain_options` |

**Glass:** `msfs_material_type="msfs_glass"`, then `msfs_glass_width` ("Glass Width (mm)", default 0). It is exported
as **value / 100** into `ASOBO_material_glass_v2.glassWidth`. Use BLEND alpha mode, with the base color alpha as
coverage. For a cockpit canopy with rain, wipers and scratches, use `msfs_windshield` and its
`msfs_windshield_*` properties.

**Texture packing (ORM / "comp"):** R = ambient occlusion, G = roughness, B = metallic, as in glTF. One image goes
to both the occlusion and metallicRoughness slots (`asobo_material_common.py: to_extension`). The comp texture
uses BitmapSlot `MTL_BITMAP_METAL_ROUGH_AO` + `ForceNoAlpha`. Channel order confirmed by
`samples/texture-xml/Image to MSFS KTX2.bat` (theflaknine) README: "red ... ambient occlusion, green ...
roughness, blue ... metallicness".

**Normal maps: DirectX convention (green channel = -Y).** The exporter always writes
`asset.extensions.ASOBO_normal_map_convention = {"tangent_space_convention": "DirectX"}` (`gltf_hooks.py:
gather_asset_hook`). The add-on's Blender preview node group has an "Invert Y" RGB-curve "in order to obtain
OpenGl normal format" for viewport display (`blender/material/msfs_material.py`). So **flip the G channel of
normal maps baked in Blender (OpenGL) before using them.** VERIFIED (source).

**Image flags** (`bpy.types.Image.msfs_flags`, a PointerProperty): `msfs_image_quality_high` (+QUALITYHIGH),
`msfs_image_alpha_preserv` (+ALPHAPRESERVATION), `msfs_image_no_reduction` (+NOREDUCE), `msfs_image_no_mipmap`
(+NOMIPMAP), `msfs_image_prec_inv_avg` (+PRECOMPUTEDINVAVG), `msfs_image_anisotropic` (+ANISOTROPIC=). These become
`<UserFlags>` in the texture XML. BitmapSlot values (`io/exp/texture_lib/bitmap_config.py`) include
`MTL_BITMAP_DECAL0` (albedo), `MTL_BITMAP_METAL_ROUGH_AO`, `MTL_BITMAP_NORMAL`, `MTL_BITMAP_EMISSIVE` and 25 others.

**Objects / bones / meshes:**

- `Object.msfs_override_unique_id` (bool) and `Object.msfs_unique_id` (str) give `ASOBO_unique_id`, which defaults
  to the node name.
- `Object.msfs_export_transform` (per-object reset), `Object.msfs_gizmo_type`, `Object.msfs_collision_is_road_collider`
  and `Object.msfs_collision_is_ground_collider`.
- `Mesh.msfs_softbody`, `Bone.msfs_unique_id`, `Action.msfs_facial_animation`.

**Lights in glTF:** `Light.msfs_light_type` = `NONE | streetLight | advancedLight | skyPortalLight`, with
properties under `msfs_light_*`: `msfs_light_intensity` (cd), `msfs_light_cone_angle`, `msfs_light_flash_frequency`,
`msfs_light_rotation_speed`, `msfs_light_channel_exterior` and others (`blender/msfs_lights.py`). These are mainly
scenery lights (`ASOBO_macro_light` is "deprecated in MSFS2024"). **Aircraft lights belong in `systems.cfg
[LIGHTS]` (§4), not in glTF.** UNVERIFIED whether `advancedLight` is honored on SimObjects.

**Animated material properties:** `ASOBO_property_animation` exports keyframed `msfs_base_color_factor`,
`msfs_emissive_factor`, `msfs_metallic_factor`, `msfs_roughness_factor`, `msfs_uv_*`, and the windshield, dirt and
tire states as glTF animation channels (`io/com/extensions/asobo_property_animation.py`). You can drive these from
the model XML like any other animation.

Ready-to-adapt snippet: `samples/blender-headless-export/msfs2024_material_setup_example.py`.

### 1.5 Does MSFS 2024 accept plain glTF from Blender's stock exporter?

**Yes, with caveats.** VERIFIED-IN-SIM (3rd party): `djcolumbia-f-104/F-104G_Starfighter_MSFS2024`,
`docs/notes/3d-model.md`, section "Proven in the sim (2026-11-11, two Build All, 0 failed)":

> Plain glTF 2.0 from Blender's own exporter is accepted (no Asobo exporter, no Asobo material extension); PNG
> textures with a `.png.xml` (`MTL_BITMAP_DECAL0` for albedo, `MTL_BITMAP_METAL_ROUGH_AO` + `ForceNoAlpha` for comp)
> in the preset `texture` folder are compiled and shown; glTF image uri `../texture/<name>.png`.
> Axes X = left, Y = up, Z = forward, metres; origin = cfg datum ...

Their generator (`samples/f104-djcolumbia-2024-modular/tools/make_f104_model.py`, Blender 5.2.3 headless) does
the following:

1. Calls `export_scene.gltf(export_format="GLTF_SEPARATE", export_apply=True, export_yup=True,
   export_image_format="NONE", ...)`.
2. Adds `ASOBO_unique_id = {"id": node.name}` on every node.
3. Rewrites `images` / `textures` to `../texture/*.png`.
4. Sets the same comp texture for metallicRoughness and occlusion.
5. Writes animations into the glTF by hand.
6. Writes the model XML and model.cfg itself.

Lesson from the same project: set `use_backface_culling = True` on every material, or the export comes out
double sided. Still unverified there: animations, glass, decals. Their note says glass and decals "will need Asobo
material extensions written into the glTF by hand". Template: `samples/blender-headless-export/plain_gltf_postprocess_example.py`.

**Recommendation for the saucer:**

- If you only need opaque PBR, emissive, and hinge or rotation animations, the **plain route with pip bpy 5.3**
  is simplest and works on Linux without the SDK add-on.
- If you need a real glass canopy, or want Asobo-exact output (emissive scale, draw order, collision materials),
  use the **Asobo add-on route with Blender or bpy 4.5**. The user must copy `io_scene_gltf2_msfs_2024` and
  `_addons_common` from their SDK (Apache-2.0) to the Linux box.

---

## 2. Package project structure (MSFS 2024 SDK)

### 2.1 Files the user opens and builds

The project file sits at the project root and is opened in Dev Mode with File > Open project, which brings up the
Project Editor, where you click "Build All". This XML is verbatim from the 2024 modular F-104 repo
(`samples/f104-djcolumbia-2024-modular/F104G.xml`). The EFB sample and the KTX2 tool use the same shape:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project Version="2" Name="F104G" FolderName="Packages" MetadataFolderName="PackagesMetadata">
	<OutputDirectory>.</OutputDirectory>
	<TemporaryOutputDirectory>_PackageInt</TemporaryOutputDirectory>
	<Packages>
		<Package>PackageDefinitions\pete-aircraft-f104g.xml</Package>
	</Packages>
</Project>
```

The package definition is `PackageDefinitions/<company>-aircraft-<name>.xml` (2024 modular, verbatim from the
F-104):

```xml
<AssetPackage Version="0.1.0">
	<ItemSettings>
		<ContentType>AIRCRAFT</ContentType>
		<Title>Lockheed F-104G Starfighter</Title>
		<Manufacturer>Lockheed</Manufacturer>
		<Creator>pete</Creator>
	</ItemSettings>
	<Flags><VisibleInStore>false</VisibleInStore><CanBeReferenced>true</CanBeReferenced></Flags>
	<PackageOrderHint>CUSTOM_SIMOBJECTS</PackageOrderHint>
	<AssetGroups>
		<AssetGroup Name="ContentInfo">
			<Type>Copy</Type>
			<Flags><FSXCompatibility>false</FSXCompatibility></Flags>
			<AssetDir>PackageDefinitions\pete-aircraft-f104g\ContentInfo</AssetDir>
			<OutputDir>ContentInfo\pete-aircraft-f104g\</OutputDir>
		</AssetGroup>
		<AssetGroup Name="pete-f104g">
			<Type>ModularSimObject</Type>
			<Flags><FSXCompatibility>false</FSXCompatibility></Flags>
			<AssetDir>PackageSources\SimObjects\Airplanes\pete-f104g\</AssetDir>
			<OutputDir>SimObjects\Airplanes\pete-f104g\</OutputDir>
		</AssetGroup>
		<!-- optional: <Type>Copy</Type> groups for modules\ (WASM), html_ui\ (instruments/EFB), ModelBehaviorDefs\ -->
	</AssetGroups>
</AssetPackage>
```

- Asset group type for a 2024 aircraft: **`ModularSimObject`**. For a 2020-style aircraft: **`SimObject`** (UH-60 and
  flying-brick samples).
- ContentInfo: the F-104 uses `Copy`. The 2020 samples and the 2024 EFB sample use `ContentInfo` (EFB:
  `<Type Version="0">ContentInfo</Type>`). Put `Thumbnail.jpg` in it.
- The company name must be lowercase `a-z0-9`, at most 25 characters (from the EFB-iframe README; Dev Mode asks
  for a default company and creator name). The package name convention is `<company>-aircraft-<name>`.
- Build output goes to `Packages/<package>/`, `PackagesMetadata/` and `_PackageInt/`. Do not also copy the package
  into Community while it is loaded as a project (EFB-iframe README).

**Command-line build:** `"<SDK>\tools\bin\fspackagetool.exe" -nopause -rebuild [-forcesteam] -outputtoseparateconsole
<Project>.xml` (VERIFIED: used by `samples/texture-xml/Image to MSFS KTX2.bat`; add `-forcesteam` for the Steam
version of the sim). It **drives the game executable**: it attaches to, or starts, the sim and waits. There is
no truly headless build (3rd party: `f104 docs/notes/systems-module.md`, `research.md`). **Builds must happen on
the user's Windows machine.**

### 2.2 2024 modular SimObject layout

Taken from the F-104 repo, which builds and flies in MSFS 2024 SDK 1.8.1, plus SDK doc snippets:

```
PackageSources/SimObjects/Airplanes/<company>-<aircraft>/
  common/                       <- "base" of the aircraft (required)
    config/  aircraft.cfg flight_model.cfg engines.cfg systems.cfg cockpit.cfg cameras.cfg gameplay.cfg ai.cfg
             (optional: target_performance.cfg, ...)
    flt/     apron.flt hangar.flt runway.flt taxi.flt climb.flt cruise.flt approach.flt final.flt
    model/   model.cfg, <Model>.xml, <Model>_LOD0.gltf/.bin
    texture/ *.png + *.png.xml (+ texture.cfg)
    sound/  soundAI/  panel/  (panel.cfg, panel.xml, instruments)
  presets/<creator>/<preset>/   <- the "glue"; one preset = one selectable variation (required)
    config/aircraft.cfg         [MODULAR_MERGE] auto = true   + [FLTSIM.0] title = "..."
    model/  texture/            (optional; a preset model REPLACES common/model for that variation, VERIFIED-IN-SIM)
  liveries/<creator>/<livery>/  livery.cfg ([GENERAL] Name=...) + texture.<x>/texture.cfg ([fltsim] fallback.1=..\..\common\texture)
  attachments/                  (optional; engines, gear etc. as attachable parts)
```

Merge order per SEARCH-SNIPPET ("Modular SimObject Merging" page): common, then attachments, then preset, then
auto-merge, then manual-merge.

The preset `aircraft.cfg` in the F-104 is just this (VERIFIED):

```ini
[MODULAR_MERGE]
auto = true

[FLTSIM.0]
title = "F-104G Starfighter 3D-Entwurf"
ui_variation = "3D-Entwurf"
description = "..."
```

`common/config/aircraft.cfg` carries the full `[GENERAL]`, `[FLTSIM.0]` (title "... Common"), and so on.
Practical notes from that project:

- `flight_model.cfg` changes need a **full sim restart**; normalization only runs at sim start.
- "Build All" reloads the aircraft, so only run it with the aircraft on the ground.
- "Without a valid `.gltf` model the aircraft does not appear in the selection."

### 2.3 Legacy (2020-style) vs modular

- 2020 layout: everything sits flat in one SimObject folder, with `aircraft.cfg` holding
  `[FLTSIM.N] Model=""/Texture=""` suffixes that point to `model.<x>/` and `texture.<x>/`. Asset group `SimObject`.
  Example: `samples/uh60-delta-sim-2020-helicopter/`.
- MSFS 2024 still loads 2020-built packages as **legacy / compatible** aircraft, but they are excluded from Career
  activities. Only modular SimObjects can be used in Career Mode, and the 2024 Marketplace only accepts packages
  built with the 2024 SDK. SEARCH-SNIPPET (msfsaddons.com, simdispatch.de, DevSupport threads). The 2024 SDK release
  notes mention a "Simple SimObjects" section next to "Modular Aircraft SimObjects".
- **Can the 2024 SDK build a 2020-style `SimObject` aircraft? UNVERIFIED.** The docs recommend modular for every new
  aircraft. **Recommendation: go modular from day one** (`common/` + one `presets/` entry). It costs only one extra
  folder and one 3-line cfg.

### 2.4 Where model, textures and model XML go

- `common/model/` (or `presets/.../model/`) holds `model.cfg`, `<Name>.xml` and `<Name>_LOD0.gltf` + `.bin`.
- `model.cfg` (verbatim F-104):
  ```ini
  [model.options]
  withExterior_showInterior=false
  withInterior_showExterior=true

  [models]
  normal=F104G.xml          ; 2020 samples also use exterior=... / interior=...
  ```
- Textures: in the 2024 Asobo add-on the glTF references `../texture/<file>`. Put PNG (TIF also accepted) in
  `texture/`, each with a `<file>.png.xml`. The **package builder compiles glTF to .glb and textures to .KTX2**
  (+ .json) in 2024 (SEARCH-SNIPPET, "glTF files get compiled to *.glb and *.png files get compiled to *.ktx2";
  an Asobo staffer confirms PNG/TIF are converted). In 2020 they became DDS (flying-brick `textures.md`).
  Avoid extra dots in texture file names (flying-brick `textures.md`).
- Texture XML examples (VERIFIED, F-104 and the KTX2 tool):
  ```xml
  <BitmapConfiguration><BitmapSlot>MTL_BITMAP_DECAL0</BitmapSlot></BitmapConfiguration>                                     <!-- albedo -->
  <BitmapConfiguration><BitmapSlot>MTL_BITMAP_METAL_ROUGH_AO</BitmapSlot><ForceNoAlpha>true</ForceNoAlpha></BitmapConfiguration>  <!-- ORM -->
  <BitmapConfiguration><BitmapSlot>MTL_BITMAP_NORMAL</BitmapSlot><UserFlags Type="_DEFAULT">QUALITYHIGH</UserFlags></BitmapConfiguration>
  ```

### 2.5 Sample skeletons copied into `samples/`

| Folder | What | Licence |
|---|---|---|
| `f104-djcolumbia-2024-modular/` | **MSFS 2024 modular** aircraft: project XML, package def (`ModularSimObject`), `common/config/*.cfg`, `common/flt`, 2 presets (one with its own model, gltf omitted), livery, texture XMLs, the Blender generator script, notes | none declared, reference only |
| `uh60-delta-sim-2020-helicopter/` | **MSFS 2020 helicopter** (UH-60, native heli FM): project XML, package def (`SimObject`), all cfgs, model XML, panel.cfg with HTML HUD, behavior templates, HUD template.js | GPL-3.0 |
| `flying-brick-tml1024-2020-minimal/` | Minimal from-scratch 2020 aircraft, heavily commented cfgs | MIT |
| `efb-apps-2024/` | Two MSFS 2024 EFB apps (plain JS iframe app, TSX app built on the SDK TemplateApp) | MIT / GPL-3.0 |
| `texture-xml/` | Batch tool that writes texture XMLs and calls fspackagetool to make KTX2 | MIT |
| `blender-headless-export/` | Asobo-add-on headless template, material setup example, plain-glTF post-process example, 3rd-party harness | own templates / Apache-2.0 (harness) |

---

## 3. Aircraft config files (helicopter / rotorcraft)

**Best reference: the Cabri G2 sample in the MSFS 2024 SDK** (Dev Mode, Help menu download; SEARCH-SNIPPET:
"contains a complete helicopter project ... plus the source files used to create the model"). I could not see its
files. The open-source reference I could read is the **Delta Simulations UH-60M**
(`https://github.com/Delta-Simulations/MSFS-H-60M`, GPL-3.0; 2020 SDK; generator string "Khronos glTF Blender I/O
v1.8.19 and Asobo Studio MSFS Blender I/O v1.3.2"). Its cfgs are in
`samples/uh60-delta-sim-2020-helicopter/PackageSources/SimObjects/Airplanes/UH60/`. I removed the 4 GB clone
afterwards to save disk space.

### 3.1 File set

| File | Needed | Notes |
|---|---|---|
| `aircraft.cfg` | yes | `[VERSION]`, `[GENERAL]` (`Category = "Helicopter"` in UH-60, `icao_engine_type = "Turboprop/Turboshaft"`), `[PILOT]`, `[SERVICES]`, `[EFFECTS]` (helo: `landrotorwash=fx_rtr_lnd, 1`, `waterrotorwash=fx_rtr_wtr, 1`), `[LOADING]`, `[FLTSIM.N]` (title, `ui_typerole="Rotorcraft"`, `ui_certified_ceiling`, `isUserSelectable=1`, `isFlyable=1`, `canBeUsedByAITraffic`). In 2024 modular, this full file goes in `common/config`, with a small one in each preset. |
| `flight_model.cfg` | yes | `[VERSION]`, `[WEIGHT_AND_BALANCE]`, `[CONTACT_POINTS]`, `[FUEL]` / `[FUEL_SYSTEM]`, `[REFERENCE SPEEDS]`, `[FUSELAGE_AERODYNAMICS]`, **`[HELICOPTER]`**, **`[MAINROTOR]`**, **`[SECONDARYROTOR]`** (helicopters have no wing sections) |
| `engines.cfg` | yes | `[GENERALENGINEDATA] engine_type = 3 ; 0=Piston, 1=Jet, 2=None, 3=Helo-Turbine, 4=Rocket, 5=Turboprop`, `[TURBINEENGINEDATA]`, `[TURBOPROP_ENGINE]` (helo turbines use the turboprop shaft-torque tables; `free_turbine = 1`), `[DISABLED_CONTROLS]` |
| `systems.cfg` | yes | `[ELECTRICAL]`, **`[LIGHTS]`** (§4), `[HYDRAULIC_SYSTEM]`, `[PITOT_STATIC]`, `[AUTOPILOT]`, ... |
| `cockpit.cfg` | yes | gauge ranges (`[FUEL_QUANTITY]`, `[OIL_PRESSURE]`, ...) |
| `cameras.cfg` | yes | pilot eyepoint etc. Copy from a sample and move the eyepoint. |
| `gameplay.cfg` | yes (in samples) | assistance / gameplay options |
| `ai.cfg`, `target_performance.cfg` | optional | AI / performance tables |
| `*.flt` | strongly advised | spawn states (apron, runway, cruise, ...) |
| `model/model.cfg` + xml + gltf | yes | §2.4 |
| `texture/texture.cfg` | optional | `[fltsim] fallback.1=...` |
| `sound/sound.xml`, `soundAI/soundai.xml` | optional | fallback sound otherwise |
| `panel/panel.cfg` | optional | needed for HTML instruments / HUD (§5) |

### 3.2 Helicopter sections (verbatim keys from the UH-60 `flight_model.cfg`, with its comments)

```ini
[FUSELAGE_AERODYNAMICS]
drag_force_cf = 0.8 ; front drag coef
side_drag_force_cf = 0.7
pitch_damp_cf / pitch_stability_cf / roll_damp_cf / yaw_damp_cf / yaw_stability_cf   ; "legacy"
use_modern_surfaces = 0 ; 0 = legacy helicopter flight model; 1 = modern surface & CFD based flight model
fuselage_position = -7.821,0,-1.193 ; ft
fuselage_rear_diam_scale, fuselage_rear_pos_vert
hstab_pos_lon, hstab_pos_vert, hstab_span, hstab_area, hstab_incidence, hstab_lift_coef
vstab_pos_lon, vstab_pos_vert, vstab_span, vstab_area, vstab_incidence, vstab_lift_coef

[HELICOPTER]
reference_length, reference_frontal_area, reference_side_area, side_aero_center, lift_aero_center
right_trim_scalar, front_trim_scalar, correlator_available, governed_pct_rpm_ref, rotor_brake_scalar,
torque_scalar, tail_rotor_translating_scalar,
cyclic_roll_control_scalar = 0.4, cyclic_pitch_control_scalar = 0.4, pedal_control_scalar = 0.3,
disk_roll_animation_scalar, disk_pitch_animation_scalar, collective_on_rotor_torque_scalar,
governor_pid = 20.0, 10.0, 20.0, 10, 10
low_realism_stability_scale = 1, 1, 1
assistance_cyclic_pitch_stability_centre, assistance_cyclic_bank_stability_centre, assistance_pedal_yaw_stability_centre
engine_trim_rate, engine_trim_max, engine_trim_min, rotor_friction_torque

[MAINROTOR]
TailRotor = 0 ; 0 = horizontal lifting rotor, 1 = secondary vertical stabilization rotor
Position = -3.667,0,5.27 ; ft
max_disc_angle = 9 ; deg (legacy) / blade beta (modern) at 100% cyclic
Radius = 23 ; ft
RatedRpm = 420
static_pitch_angle, static_bank_angle, number_of_blades, weight_per_blade (lbs), weight_to_moi_factor,
inflow_vel_reference, coning_ratio_load_factor_one/two, coning_angle_at_ratio_one,
blade_aspect_ratio, blade_AOA0_lift_slope, blade_AOAStall_lift_slope, blade_tip_to_root_lineartwist,
blade_AOAStall_scaler, blade_AOAStall_power, blade_AOA0_inddrag_efficiency, blade_AOA0_parasiticdrag,
blade_thickness_ratio,
blade_beta_input_max = 15.0 ; deg at max collective
blade_beta_input_min = -0.5 ; deg at min collective
blade_flap_rigidity, blade_flap_inertia, Reverse_rotation = 0, gyro_precession_scalar

[SECONDARYROTOR]   ; same keys; TailRotor = 1 for a tail rotor, blade_beta_input_max/min = pedal range
```

**MSFS 2024 additions** (SEARCH-SNIPPET from the 2024 SDK release notes and CFG parameter index; exact syntax
UNVERIFIED):

- `[HELICOPTER]`: `cyclic_roll_control_scalar_negative`, `cyclic_pitch_control_scalar_negative`,
  `collective_move_rate_limit_vr`, `cyclic_move_rate_limit`, `rudder_pedals_move_rate_limit`,
  `governed_pct_rpm_min`, `governor_speed_limit`, `rotor_brake_torque`.
- **`rotor_node.N`** links each rotor to its model node, and can list more than one node per rotor (low-detail and
  high-detail blades). For modular aircraft it points at an attachment alias. It is documented on the 2024 page
  "Propellers, Turbines And Blades".
- New `[MAINROTOR]` / `[SECONDARYROTOR]` keys exist but were not listed in the snippets.
- Dual-rotor keys `pedal_on_collective` and `pedal_on_bank` predate 2024. When `pedal_on_collective > 0` the pilot
  yaws through rotor drag. "The cyclic pitch centre parameter is only used for dual rotor helicopters, where the
  TailRotor parameter is set to 0 for both the main and secondary rotor."
- Known bug report: rotor MOI is miscalculated for all helicopters. It depends on the ratio of `max_rated_rpm`
  (engines.cfg) to `RatedRpm` (flight_model.cfg). DevSupport thread 18769.

**Saucer idea (design, not verified):** model it as a **coaxial dual-rotor**: `[MAINROTOR]` and
`[SECONDARYROTOR]` both `TailRotor = 0`, the second with `Reverse_rotation = 1`, both at the saucer center, with
yaw from `pedal_on_collective` / `pedal_on_bank`. That avoids a visible tail rotor. Keep the rotor nodes
invisible, or show them as a spinning ring with a blur.

### 3.3 Contact points (skids / landing pads)

Format: `point.N = ` with 17 comma-separated values. The UH-60 uses 17, for example
`point.0 = 1,-0.2,4.5,-6.3,2000,1,1.5,0,0.45,1.1,1,0,0,2,0,0,1`. Field meanings, from the 2020 SDK as I remember
them and partly confirmed by snippets (UNVERIFIED in exact wording):

| # | Field | Saucer pad suggestion |
|---|---|---|
| 1 | class: 1 = wheel, 2 = scrape, **3 = skid** (snippet: "code 3 is the skid type"), 4 = float, 5 = water rudder, ... The UH-60 uses `17` for fuselage and rotor strike points (meaning UNVERIFIED) | 3 |
| 2-4 | longitudinal, lateral, vertical position (ft, from the reference datum; vertical negative = down) | pad positions |
| 5 | impact damage threshold (ft/min) | 1500-2000 |
| 6 | brake map (0 none, 1 left, 2 right) | 0 |
| 7 | wheel radius (ft) | 0.2-0.5 |
| 8 | steer angle (deg) | 0 |
| 9 | static compression (ft; 0 = rigid) | 0.1-0.3 |
| 10 | max / static compression ratio | ~1.5-2 |
| 11 | damping ratio | 0.8-1 |
| 12 / 13 | extension / retraction time (s) | 0 = fixed; e.g. 4 / 4 for retracting pads |
| 14 | sound type (0 center gear, 1 aux, 2 left gear, 3 right gear, 4 fuselage scrape, 5 left wing scrape, 6 right wing scrape, 7/8 aux scrape, 9 tail scrape; matches UH-60 usage) | 0-3 |
| 15 | airspeed limit for retraction (KIAS) | |
| 16 | airspeed at which the gear is damaged (KIAS) | |
| 17 | (newer field, 1 in the UH-60 file) | 1 |

- Skid rules (SEARCH-SNIPPET, 2024 "flight_model.cfg - Additional Information"): skid slots are Center Front,
  Center Rear, Left Front, Left Rear, Right Front, Right Rear. More than 2 skids per side are ignored. A lone skid
  on one side is "front" if its longitudinal coordinate > 0, else "rear". Retractable skids: at most 6.
- Section keys used by the UH-60: `static_pitch`, `static_cg_height`, `gear_system_type = 4` (meaning UNVERIFIED;
  probably "none"), `tailwheel_lock`, `max_number_of_points`, `gear_locked_on_ground`, `gear_locked_above_speed`,
  plus the steering keys.
- Advice from the docs: add contact points with the Dev Mode **Aircraft Editor** and only hand-tweak the cfg. For
  points that are not landing gear, only type and position matter.
- **Saucer:** 3 or 4 landing pads as class-3 skids at LF / LR / RF / RR (or CF / CR + 2 side), plus class-2 scrape
  points on the rim for crash detection. For retractable pads, set an extension/retraction time and give
  `gear_system_type` a real system, then animate with `GEAR ANIMATION POSITION:n` (§4).

### 3.4 Ceiling / speed limits

- `aircraft.cfg [FLTSIM.N] ui_certified_ceiling` (ft) and `ui_max_range`. These are UI and info values.
- `flight_model.cfg [REFERENCE SPEEDS]`: `max_indicated_speed` (red line KIAS), `cruise_speed`, `cruise_alt`,
  `spawn_cruise_altitude`, `airspeed_indicator_max`, `climb_speed`. In the UH-60 the fixed-wing keys are 0.
- The real ceiling and speed come from rotor and engine power and density tables (`density_on_torque_table`,
  `[HELICOPTER]` governor), not from a single cap. UNVERIFIED whether 2024 has a hard altitude cap key for
  rotorcraft.

---

## 4. Model XML / behaviors: lights, emissive, animations

### 4.1 Aircraft lights: `systems.cfg [LIGHTS]`

Verbatim from the UH-60 (2020 SDK; the same `lightdef` syntax is documented in the 2024 systems.cfg page per
SEARCH-SNIPPET, where the old `light.N` form is "legacy"):

```ini
[LIGHTS]
lightdef.0=Type:3#Index:1#LocalPosition:0,0,0#LocalRotation:0,0,0#EffectFile:LIGHT_ASOBO_NavigationRed#Node:NAV_L#PotentiometerIndex:1#EmMesh:NAV_LEFT
lightdef.1=Type:3#Index:1#LocalPosition:0,0,0#LocalRotation:0,0,0#EffectFile:LIGHT_ASOBO_NavigationGreen#Node:NAV_R#PotentiometerIndex:1#EmMesh:NAV_RIGHT
lightdef.3=Type:1#Index:1#LocalPosition:0,0,0#LocalRotation:0,0,0#EffectFile:LIGHT_H60_BeaconNight#Node:Tail_BCN_Night#PotentiometerIndex:2#EmMesh:BCN_TAIL_NIGHT
lightdef.5=Type:2#Index:1#LocalPosition:0,0,0#LocalRotation:0,0,0#EffectFile:LIGHT_H60_BeaconDay#Node:Tail_BCN_Day#PotentiometerIndex:3#EmMesh:BCN_TAIL_DAY
lightdef.7=Type:5#Index:1#LocalPosition:0,0,0#LocalRotation:0,0,0#EffectFile:fx_H60Landing.fx#Node:SL_Attach#PotentiometerIndex:4#EmMesh:SL_Emiss
```

- `Type`: 1 beacon, 2 strobe, 3 navigation, 4 cabin / panel, 5 landing, 6 taxi (consistent across UH-60 and
  community examples). Higher numbers (recognition, wing, logo, panel, ...) are UNVERIFIED.
- `Index` selects which of several lights of a type (it matches the SimVar / circuit index).
- `EffectFile` is required: a built-in `LIGHT_ASOBO_*` effect (for example `LIGHT_ASOBO_NavigationRed`,
  `LIGHT_ASOBO_StrobeSimple`, `LIGHT_ASOBO_BeaconTop`, `LIGHT_ASOBO_LandingLarge`, `LIGHT_ASOBO_TaxiLarge`) or your
  own .fx.
- **`Node:<name>`**: the light attaches to that glTF node, so **it follows any animation of the node.** This is how
  you get a spot or landing light on a moving part. Example: `Node:SL_Attach` above, the UH-60's searchlight
  attach node. `LocalPosition` / `LocalRotation` offset it relative to the node (the UH-60 uses 0s and orients the
  node in Blender instead). One forum note says you still need explicit `0,0,0` values when using a node.
- `PotentiometerIndex` scales intensity with `LIGHT POTENTIOMETER:n`. `EmMesh:<node>` names the emissive mesh that
  lights up together with the light (snippet: its material should be the Standard type; one snippet says it should
  be named "LIGHTS", which is UNVERIFIED).
- A spot light that follows an animated node: make an empty in Blender (for example `SPOT_ATTACH`), parent it
  under the animated object, and point its local axis along the beam (axis convention UNVERIFIED; the UH-60 leaves
  rotation at 0 and orients the node). Export it so it keeps its name (`ASOBO_unique_id`). Then add
  `lightdef.N=Type:5#Index:1#LocalPosition:0,0,0#LocalRotation:0,0,0#EffectFile:LIGHT_ASOBO_LandingLarge#Node:SPOT_ATTACH#PotentiometerIndex:1`.

### 4.2 Emissive driven by a variable

From the UH-60 `Model/UH60M.xml`, verbatim pattern (2020 SDK; the template comes from `Asobo\Common.xml`):

```xml
<Behaviors>
  <Include ModelBehaviorFile="Asobo\Exterior.xml" />
  <Include ModelBehaviorFile="Asobo\Generic\FX.xml" />
  <Include ModelBehaviorFile="Asobo\AircraftTypes\Rotorcrafts.xml" />
  <Component ID="nav1" Node="NAV_MAST">
    <UseTemplate Name="ASOBO_GT_Material_Emissive_Code">
      <EMISSIVE_CODE>(A:LIGHT NAV ON,bool) 1 == if{ 50 } els{ 0 }</EMISSIVE_CODE>
    </UseTemplate>
  </Component>
  <Component ID="Slime_Fwd" Node="Slime_Fwd">
    <UseTemplate Name="ASOBO_GT_Material_Emissive_Code">
      <EMISSIVE_CODE>(A:LIGHT POTENTIOMETER:10, percent) 0.005 * (A:ELECTRICAL MASTER BATTERY, bool) *</EMISSIVE_CODE>
    </UseTemplate>
  </Component>
</Behaviors>
```

`Node` is the mesh node (object) name in the glTF. The code result scales the material's emissive. Visibility:
`ASOBO_GT_Visibility` with `<VISIBILITY_CODE>`. Each-frame code: `ASOBO_GT_Update` with `<UPDATE_CODE>` and
`<UPDATE_ONCE>`. Whether these `Asobo\*.xml` template libraries work unchanged for 2024 **modular** aircraft is
UNVERIFIED, though the templates ship with the 2024 sim. Compare with the Cabri G2 or SimpleAircraft model XML.

### 4.3 Animations

1. **Simple sim-variable animations, legacy `<Animation>` + `<PartInfo>` style.** These are verbatim in the 2024
   F-104 model XML, which builds in 2024:
   ```xml
   <Animation name="c_gear" guid="E2E339A6-FCBF-43a9-A780-3473E03AB54B" length="100" type="Sim" typeParam2="c_gear" typeParam="AutoPlay" />
   <PartInfo><Name>c_gear</Name><AnimLength>100</AnimLength>
     <Animation><Parameter><Sim><Variable>GEAR ANIMATION POSITION:0</Variable><Units>number</Units><Scale>100</Scale><Bias>0</Bias></Sim></Parameter></Animation>
   </PartInfo>
   ```
   Gear: `GEAR ANIMATION POSITION:0` (center), `:1` (left), `:2` (right), 0 = retracted. The glTF animation name
   must equal the `name` / `typeParam2`. Key-time mapping (glTF key times to AnimLength 100) is NOT verified in that
   project.
2. **Behavior templates** (UH-60 / flying-brick):
   ```xml
   <UseTemplate Name="ASOBO_GEAR_Center_Template"><ANIM_NAME>c_gear</ANIM_NAME></UseTemplate>
   <UseTemplate Name="ASOBO_GEAR_Left_Template"><ANIM_NAME>l_gear</ANIM_NAME></UseTemplate>
   <UseTemplate Name="ASOBO_GEAR_Right_Template"><ANIM_NAME>r_gear</ANIM_NAME></UseTemplate>
   <!-- or ASOBO_GEAR_Base_Template with <ID>n</ID> (flying-brick) -->
   ```
3. **Continuous rotation (rotor / spinning ring)**, verbatim UH-60:
   ```xml
   <UseTemplate Name="ASOBO_GT_Anim">
     <ANIM_NAME>RTR_Tail_Rot</ANIM_NAME>
     <ANIM_CODE>(A:ROTOR RPM:2, degrees per second) (A:ANIMATION DELTA TIME, seconds) *</ANIM_CODE>
     <ANIM_LENGTH>360</ANIM_LENGTH>
     <ANIM_WRAP>1</ANIM_WRAP>
     <ANIM_DELTA>1</ANIM_DELTA>
   </UseTemplate>
   ```
   The glTF animation `RTR_Tail_Rot` is one full revolution over a length of 360. Main rotor: `ROTOR RPM:1`. They
   switch still and blurred blades with `ASOBO_GT_Visibility` on `(A:ROTOR RPM PCT:1, percent)`.
   Custom code-driven animation: `ASOBO_GT_Anim_Code` with `<ANIM_CODE>` (see `DeltaSim_Anim_Template.xml`).
4. **From Blender with the Asobo exporter:** one action per animation, pushed to an **NLA track named exactly like
   `ANIM_NAME`** (the exporter's default `export_animation_mode = NLA_TRACKS`). Community convention: keyframe
   frame 0..N where N = ANIM_LENGTH (0..100 for gear, 0..360 for a rotation). Frame-to-time conversion is not
   verified by me, so check against the Cabri or SimpleAircraft samples.

---

## 5. EFB apps and HTML/JS instruments on a mesh (HUD)

### 5.1 Custom EFB (tablet) apps: they exist in MSFS 2024

- SDK sample "**EFB Template Sample**" (`.../7_Samples_Tutorials/Samples/EFB/EFB_Template_Sample.htm`, refreshed in
  SDK 1.8.2) and the "**Electronic Flight Bag API**" reference (`.../6_Programming_APIs/EFB/Electronic_Flight_Bag_API.htm`).
  SEARCH-SNIPPET.
- Structure (VERIFIED, `samples/efb-apps-2024/`):
  - Copy asset group `PackageSources\<AppName>\`, which outputs to `.\html_ui\efb_ui\efb_apps\<AppName>\`.
  - JS registers through `window.EFB_API` and uses `window.msfssdk` (`@microsoft/msfs-sdk` FSComponent); the base
    URL is `coui://html_ui/efb_ui/efb_apps/<AppName>`.
  - TSX version: `@efb/efb-api` (`App`, `AppView`, `Efb`), esbuild, `npm run build` in the SDK's TemplateApp
    folder.
  - The internal name must match the file name, the folder name and the `OutputDir`, or the app silently does not
    appear. Do not call it `TemplateApp`.
  - The Coherent GT browser is old: avoid CSS grid, CSS variables, `calc()` and optional chaining (RCCSilva
    README).
- An EFB app is a package of its own (ContentType MISC) or an extra Copy group in the aircraft package.

### 5.2 HTML/JS instrument rendered on a mesh (HUD): it exists

`panel/panel.cfg`, verbatim UH-60:

```ini
[Vcockpit05]
size_mm=1360,1350
pixel_size=1024,1024
texture=$HUD
hud=1
render_on_screen = 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1
htmlgauge00=H60/HUD/template.html?Index=4, 0,0,1360,1350
```

- The glTF mesh whose **material is named `HUD`** (the `$` prefix in `texture=$HUD` refers to it) shows the gauge.
  This material-naming convention is long-standing MSFS practice; I could not check the 2024 doc text.
- The HTML path is relative to `html_ui/Pages/VCockpit/Instruments/`. Ship it through a Copy asset group
  `PackageSources\html_ui\` that outputs to `html_ui\`.
- Instrument JS: `class X extends BaseInstrument { get templateID() {...} ... }` +
  `registerInstrument('hud-element', X)` (`samples/uh60-.../html_ui/Pages/VCockpit/Instruments/H60/HUD/template.js`).
- The modern alternative is the **MSFS Avionics Framework** (`@microsoft/msfs-sdk`). Docs:
  `https://microsoft.github.io/msfs-avionics-mirror/2024/`, repo `https://github.com/microsoft/msfs-avionics-mirror`.
- Meaning of `hud=1` and `render_on_screen`: UNVERIFIED. The UH-60 uses them for a pop-out / HMD view.

---

## 6. Implementation checklist for "disque-corona"

1. Pick the exporter route.
   - Plain route: pip bpy 5.3, stock exporter + `plain_gltf_postprocess_example.py`.
   - Asobo route: Blender or bpy 4.5 + `export_msfs2024_headless.py` + SDK add-on copied from the user's SDK.
2. Units: metres. Axes after glTF export: X left, Y up, Z forward. With the exporter's Y-up conversion (Blender
   (x, y, z) to glTF (x, z, -y)) this means, in Blender: **nose toward -Y, Z up, left side toward +X**. This
   matches the F-104 generator, which flips x and y before export. The origin is the cfg reference datum (feet in
   the cfgs, metres in the glTF).
3. Name nodes for behaviors: `RING_SPIN`, `PAD_L`, `SPOT_ATTACH`, `NAV_L`, etc. Name animations (NLA tracks) after
   the `ANIM_NAME`s. Name the HUD screen material `HUD` if you use one.
4. Textures: PNG, ORM-packed comp, DirectX normal maps, a `.png.xml` per file, no extra dots in names.
5. Package: copy `samples/f104-djcolumbia-2024-modular/` as the skeleton (rename company and aircraft). Take the
   rotorcraft sections from the **Cabri G2 SDK sample**, cross-checked with
   `samples/uh60-delta-sim-2020-helicopter/.../flight_model.cfg` and `engines.cfg` (`engine_type = 3`).
6. User on Windows: Dev Mode, open the project XML, Build All (or run fspackagetool with the sim installed). Tune
   contact points in the Aircraft Editor. Fully restart the sim after flight_model changes.

## 7. Source index

**Repos (cloned under `repos/`):**

- `AsoboStudio/glTF-Blender-IO-MSFS`: `main` → `asobo-main/`, `update_to_blender_4_5` → `asobo-4_5/`. This is the
  2020 exporter.
- `uraymeiviar/msfs2024-blender-addons`: `upstream` branch → `asobo2024-upstream/` (vanilla Asobo 2024 add-on
  8.4.2); `main` → `uraymeiviar_msfs2024-blender-addons/`.
- `uraymeiviar/msfs-blender-5-addons` → headless harness `tests/harness/blender_case.py`.
- `GRD-Brasil/GRD_gltf2_msfs2024`: repackaged 2024 add-on for Blender 4.2-5.x.
- `djcolumbia-f-104/F-104G_Starfighter_MSFS2024` → `f104-2024/`: MSFS 2024 modular project, plain-glTF route proven
  in the sim.
- `Delta-Simulations/MSFS-H-60M`: 2020 helicopter, GPL-3.0. The clone was deleted after copying (4 GB).
- `tml1024/flying-brick`: minimal 2020 aircraft, MIT.
- `RCCSilva/msfs-efb-iframe`, `Arun-N/msfs24-efb-descent-calculator-app`: MSFS 2024 EFB apps.
- `theflaknine/ImageToMSFSKTX2`: texture XML and fspackagetool usage.

**Official docs** (seen only as search results, not opened; enable `docs.flightsimulator.com` to read them):

- Blender plugin: https://docs.flightsimulator.com/msfs2024/html/3_Models_And_Textures/Plugins/Blender_Plugin/The_Blender_Plugin.htm
- Blender plugin properties: https://docs.flightsimulator.com/msfs2024/html/3_Models_And_Textures/Plugins/Blender_Plugin/Blender_Plugin_Properties.htm
- Model exporting: https://docs.flightsimulator.com/msfs2024/html/3_Models_And_Textures/Modeling/Aircraft/Model_Exporting.htm
- Modular SimObject project structure: https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/Modular_SimObjects/Modular_SimObject_Project_Structure.htm
- Modular SimObject merging: https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/Modular_SimObjects/Modular_SimObject_Merging.htm
- flight_model.cfg: https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/CFG_Files/flight_model_cfg.htm
- Flight model additional information (skids): https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/CFG_Files/Flight_Model/flight_model_info.htm
- CFG parameter index: https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/CFG_Files/CFG_Parameter_Index.htm
- systems.cfg: https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/CFG_Files/systems_cfg.htm
- Propellers, turbines and blades (`rotor_node`): https://docs.flightsimulator.com/msfs2024/html/3_Models_And_Textures/Modeling/Aircraft/Airframe/Propellers_Turbines_And_Blades.htm
- Texture XML properties: https://docs.flightsimulator.com/msfs2024/html/5_Content_Configuration/Textures/Texture_XML_Properties.htm
- Package tool: https://docs.flightsimulator.com/msfs2024/html/8_SDK_Tools/Package_Tool/Package_Tool.htm
- Cabri G2 sample: https://docs.flightsimulator.com/msfs2024/retail/samples-tutorials/samples/simobjects-aircraft/cabri-g2/
- SimpleAircraft sample: https://docs.flightsimulator.com/msfs2024/html/7_Samples_Tutorials/Samples/SimObjects_Aircraft/SimpleAircraft.htm
- EFB template sample: https://docs.flightsimulator.com/msfs2024/html/7_Samples_Tutorials/Samples/EFB/EFB_Template_Sample.htm
- Electronic Flight Bag API: https://docs.flightsimulator.com/msfs2024/html/6_Programming_APIs/EFB/Electronic_Flight_Bag_API.htm
- SDK release notes: https://docs.flightsimulator.com/msfs2024/html/1_Introduction/Release_Notes.htm
- SDK installers manifest (from the EFB-iframe README): https://sdk.flightsimulator.com/msfs2024/files/sdk.json

**Forum and blog sources (search snippets only):**

- DevSupport 18769 (rotor MOI bug) and 10261 (Blender exporter 2020 vs 2024).
- fsdeveloper thread 461170 (`_addons_common`).
- msfsaddons.com and simdispatch.de (legacy aircraft vs Career Mode).
