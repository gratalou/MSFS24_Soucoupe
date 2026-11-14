# Disque Corona — notes pour Claude

Projet : mod MSFS 2024, soucoupe « Disque Corona type R-47 » (Roswell 1947), modèle de vol hélicoptère
renommé, histoire « Dossier Sable » sur la tablette. L'utilisateur parle français : répondre en français,
simplement (il ne connaît ni Blender ni le SDK), et faire valider les choix visuels par des rendus.

## État (fin de la session cloud, 2026-11-14)
- Fait : dossier de conception (`dossier-conception.html`), générateurs `tools/`, modèle 3D exporté dans
  `package/` (glTF + textures + XML + animations de pieds c_gear/l_gear/r_gear), 4 rendus `renders/v1/`.
- Manque pour un premier vol : les cfg de vol. Décision : partir de l'exemple officiel **Cabri G2** du SDK
  (dossier sur le PC de l'utilisateur, plusieurs Go ; ses cfg sont modulaires : `common/config/flight_model.cfg`
  ne contient que `reference_datum_position`, le reste est dans d'autres sous-dossiers à identifier).
- À adapter ensuite : contact points (3 pieds), masse (2 850 kg à vide, 3 600 kg max), rotor principal invisible
  au centre + rotor anticouple invisible, noms OVNI (voir le tableau dans le dossier de conception),
  `common/config/aircraft.cfg` (category Helicopter), caméras (œil sous le dôme, ~z +1,3 m).

## Conventions techniques (voir research/msfs2024-notes.md)
- Voie d'export : glTF standard (bpy) + post-traitement `tools/export_msfs.py` (ASOBO_unique_id, textures
  `../texture/*.png` + `.png.xml`, normale DirectX). Package modulaire `ModularSimObject` (common + presets).
- Repère Blender : Z haut, avant = -Y, gauche = +X ; origine = point de référence (centre, plan du bord).
- Pieds (pads au sol z = -1,62 m) : avant (0, -2,95), gauche (+2,555, +1,475), droite (-2,555, +1,475) en m Blender.
  En pieds MSFS (long, lat, vert) : avant (+9,68, 0, -5,31), gauche (-4,84, -8,38, -5,31), droite (-4,84, +8,38, -5,31).
- Compilation : sur Windows uniquement (mode développeur MSFS 2024 › Project Editor › ouvrir `package/DisqueCorona.xml` › Build All).

## Régénérer
Python 3.13 + `pip install bpy pillow` : voir README.md. `build/` est régénérable et ignoré par git.

## Améliorations visuelles notées (prochaine passe)
- Glyphes de la gorge trop « manuscrits » : les rendre géométriques/gravés.
- Rendus : intérieur provisoire visible sous le dôme (le retirer), bande de brume au crépuscule,
  montagnes trop anguleuses, dessous trop pâle.
