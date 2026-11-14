"""Profil de révolution du Disque Corona (type R-47).

Unités : mètres. Axe de révolution = Z (Blender). r = rayon, z = hauteur.
Partagé par le générateur de textures et le générateur de modèle,
pour que les coordonnées UV et les textures restent alignées.
"""
import math

R_MAX = 4.705          # rayon hors tout (diamètre 9,41 m)
R_TEX = 4.75           # demi-largeur couverte par les îlots UV planaires
RIM_REPEAT = 6         # la bande du bord se répète 6 fois sur le tour
N_EMITTERS = 24        # émetteurs de la couronne
EMITTER_R = 4.672      # rayon des lentilles d'émetteurs (dans la gorge)

GROOVES_LOWER = [1.35, 3.25, 3.95]   # rainures concentriques sous la coque
GROOVE_W, GROOVE_D = 0.026, 0.007

# Trappes des pieds (sous la coque) : angle (deg, 0 = +X, sens trigonométrique),
# l'avant de l'appareil est -Y (270°).
LEG_ANGLES = [270.0, 30.0, 150.0]
LEG_DOOR_R = 2.40      # rayon du centre des trappes
LEG_DOOR_LEN = 0.84    # longueur radiale
LEG_DOOR_WID = 0.58    # largeur tangentielle
LEG_DOOR_CORNER = 0.16
HATCH_ANGLE = 90.0     # trappe d'accès à l'arrière (+Y)
HATCH_R = 2.0
HATCH_RADIUS = 0.46
GROUND_Z = -1.62       # niveau du sol, pieds sortis


def _catmull(pts, n_per_seg):
    """Catmull-Rom centripète simple sur une liste (r, z)."""
    out = []
    p = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n_per_seg):
            t = k / n_per_seg
            t2, t3 = t * t, t * t * t
            r = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            z = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((r, z))
    out.append(pts[-1])
    return out


def _z_on(curve, r):
    """Interpolation linéaire de z sur une courbe dense (r croissant ou décroissant)."""
    for (r0, z0), (r1, z1) in zip(curve, curve[1:]):
        if (r0 - r) * (r1 - r) <= 0 and r0 != r1:
            t = (r - r0) / (r1 - r0)
            return z0 + t * (z1 - z0)
    return curve[-1][1]


LOWER_CTRL = [(0.88, -0.905), (1.6, -0.862), (2.4, -0.772), (3.2, -0.612),
              (3.8, -0.445), (4.25, -0.262), (4.58, -0.092)]
UPPER_CTRL_OUT = [(4.55, 0.110), (4.10, 0.268), (3.50, 0.440), (3.02, 0.556)]
UPPER_CTRL_IN = [(2.955, 0.592), (2.40, 0.712), (2.00, 0.780), (1.75, 0.826), (1.70, 0.835)]


def build_profile():
    """Retourne une liste de (r, z, tag) ; tag ∈ {'lower', 'rim', 'upper'}.

    Le tag d'un point vaut pour le segment qui part de ce point vers le suivant.
    """
    prof = []
    # Logement de la lentille ventrale
    for r, z in [(0.80, -0.842), (0.80, -0.872), (0.815, -0.892), (0.84, -0.902)]:
        prof.append((r, z, 'lower'))
    # Surface inférieure avec rainures
    dense = _catmull(LOWER_CTRL, 14)
    pts = []
    for r, z in dense:
        if any(abs(r - g) < GROOVE_W * 1.2 for g in GROOVES_LOWER):
            continue
        pts.append((r, z))
    for g in GROOVES_LOWER:
        zg = _z_on(dense, g)
        hw = GROOVE_W / 2
        for dr, dz in [(-hw * 1.15, 0.0), (-hw * 0.55, GROOVE_D * 0.9), (0.0, GROOVE_D), (hw * 0.55, GROOVE_D * 0.9), (hw * 1.15, 0.0)]:
            pts.append((g + dr, _z_on(dense, g + dr) + dz))
    pts.sort(key=lambda p: p[0])
    for r, z in pts:
        prof.append((r, z, 'lower'))
    # Bord : lèvre inférieure, gorge des émetteurs, lèvre supérieure
    rim = [(4.625, -0.074), (4.665, -0.058), (4.692, -0.043), (4.705, -0.031),
           (4.703, -0.024), (4.688, -0.021), (4.652, -0.019), (4.640, -0.006),
           (4.638, 0.000), (4.640, 0.008), (4.652, 0.021), (4.688, 0.024),
           (4.703, 0.027), (4.705, 0.034), (4.693, 0.050), (4.660, 0.072), (4.605, 0.093)]
    for r, z in rim:
        prof.append((r, z, 'rim'))
    # Surface supérieure, épaulement à r = 3,0 m
    up_out = _catmull(UPPER_CTRL_OUT, 12)
    for r, z in up_out:
        prof.append((r, z, 'upper'))
    for r, z in [(2.995, 0.562), (2.985, 0.574), (2.972, 0.586)]:
        prof.append((r, z, 'upper'))
    up_in = _catmull(UPPER_CTRL_IN, 12)
    for r, z in up_in:
        prof.append((r, z, 'upper'))
    prof.append((1.60, 0.835, 'upper'))
    # Dédoublonnage des points trop proches
    clean = [prof[0]]
    for p in prof[1:]:
        if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-4:
            clean.append(p)
    return clean


def lower_curve():
    """Courbe dense de la surface inférieure (sans rainures), r croissant."""
    return _catmull(LOWER_CTRL, 14)


def z_lower(r):
    return _z_on(lower_curve(), r)


def rim_arc_info(profile):
    """Longueur d'arc cumulée sur la partie 'rim' + intervalle de la gorge (fond)."""
    idx = [i for i, p in enumerate(profile) if p[2] == 'rim']
    i0, i1 = idx[0], idx[-1] + 1  # inclut le point suivant (premier 'upper')
    s = [0.0]
    for a, b in zip(profile[i0:i1], profile[i0 + 1:i1 + 1]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = s[-1]
    # Fond de gorge : points dont r < 4.66 dans la zone rim
    ch = [k for k, i in enumerate(range(i0, i1 + 1)) if profile[i][0] < 4.66 and abs(profile[i][1]) < 0.03 and profile[i][2] == 'rim']
    return i0, i1, s, total, (s[ch[0]] / total, s[ch[-1]] / total)


COLLAR = [(1.58, 0.828), (1.735, 0.828), (1.758, 0.858), (1.750, 0.902),
          (1.712, 0.928), (1.640, 0.936), (1.605, 0.922), (1.58, 0.900)]
DOME_CTRL = [(1.632, 0.925), (1.605, 1.10), (1.505, 1.36), (1.335, 1.60),
             (1.085, 1.79), (0.745, 1.92), (0.385, 1.985), (0.0, 2.0)]
