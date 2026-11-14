# Disque Corona (type R-47)

Mod pour Microsoft Flight Simulator 2024 : une soucoupe volante inspirée des récits de Roswell (1947),
pilotable sur la base du modèle de vol hélicoptère, avec une histoire racontée par le livre de vol
(« Dossier Sable ») sur la tablette de bord.

## Contenu du dépôt

| Dossier | Rôle |
|---|---|
| `dossier-conception.html` | Dossier de conception (recherche, plans, intérieur, HUD, tablette, rayon, eau, espace) |
| `tools/` | Générateurs Python : profil, textures, modèle 3D Blender, rendus, export MSFS |
| `package/` | Projet MSFS 2024 à ouvrir dans le mode développeur (`DisqueCorona.xml`) |
| `renders/` | Rendus photoréalistes du modèle |
| `research/msfs2024-notes.md` | Notes techniques sur le format MSFS 2024 |

## Régénérer le modèle (Linux ou Windows, Python 3.13 + `pip install bpy pillow`)

```bash
python tools/make_textures.py build/textures
python tools/build_model.py build/textures build/disque_corona.blend build/gltf/disque_corona.gltf
python tools/render_shots.py build/disque_corona.blend renders/v1
python tools/export_msfs.py build/disque_corona.blend build/textures package
```

## Avancement

- [x] Phase 1 : modèle extérieur, textures, rendus, export glTF vers le package
- [ ] Phase 1 : modèle de vol (à partir de l'exemple Cabri G2 du SDK), premier vol
- [ ] Phase 2 : intérieur
- [ ] Phase 3 : HUD, tablette « Dossier Sable »
- [ ] Phase 4 : lumières, rayon pilotable, sons
- [ ] Phase 5 : vol avancé, haute altitude
- [ ] Phase 6 : eau
