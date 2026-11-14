"""Génère les textures PBR de la coque du Disque Corona (atlas 4096 x 4096).

Disposition de l'atlas (coordonnées UV, v vers le haut) :
  - [0,0.5] x [0.5,1] : dessus de la coque, projection planaire vue de dessus
  - [0.5,1] x [0.5,1] : dessous de la coque, même projection
  - [0,1] x [0,0.125] : bande du bord (lèvres + gorge des émetteurs), répétée 6 fois
Sorties : hull_albedo.png (sRGB), hull_orm.png (R occlusion, G rugosité, B métal),
          hull_normal.png (convention OpenGL), hull_emissive.png (sRGB).
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import saucer_profile as SP  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
S = 4096
H = S // 2
R = SP.R_TEX
PX = 2 * R / H  # mètres par pixel dans les îlots planaires
rng = np.random.default_rng(1947)


# ---------- bruit ----------
def lowfreq(shape, cell_px, seed):
    g = np.random.default_rng(seed)
    sh = (max(2, int(shape[0] / cell_px) + 2), max(2, int(shape[1] / cell_px) + 2))
    small = Image.fromarray(g.standard_normal(sh).astype(np.float32), mode="F")
    a = np.asarray(small.resize((shape[1], shape[0]), Image.BICUBIC), dtype=np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def fractal(shape, cells, seed):
    acc = np.zeros(shape, np.float32)
    amp, tot = 1.0, 0.0
    for i, c in enumerate(cells):
        acc += amp * lowfreq(shape, c, seed + i * 31)
        tot += amp
        amp *= 0.55
    return acc / tot


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def streaks_1d(n, seed, smooth=3):
    g = np.random.default_rng(seed)
    a = g.standard_normal(n + smooth * 4).astype(np.float32)
    k = np.ones(smooth, np.float32) / smooth
    a = np.convolve(a, k, mode="same")[smooth * 2:smooth * 2 + n]
    return (a - a.mean()) / (a.std() + 1e-6)


# ---------- glyphes (même générateur que le dossier de conception) ----------
def glyph_strokes(seed):
    s = (seed * 7919 + 13) % 4294967296

    def r():
        nonlocal s
        s = (s * 1664525 + 1013904223) % 4294967296
        return s / 4294967296

    pts = [(6, 6), (20, 6), (34, 6), (6, 20), (20, 20), (34, 20), (6, 34), (20, 34), (34, 34)]
    strokes = []
    n = 2 + int(r() * 3)
    for _ in range(n):
        a = pts[int(r() * 9)]
        b = pts[int(r() * 9)]
        if a == b:
            continue
        if r() < 0.45:  # courbe quadratique passant par le centre
            poly = []
            for k in range(13):
                t = k / 12
                x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * 20 + t * t * b[0]
                y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * 20 + t * t * b[1]
                poly.append((x, y))
            strokes.append(poly)
        else:
            strokes.append([a, b])
    dot = pts[int(r() * 9)] if r() < 0.6 else None
    return strokes, dot


def draw_glyph(draw, seed, to_px, width):
    strokes, dot = glyph_strokes(seed)
    for poly in strokes:
        draw.line([to_px(x, y) for x, y in poly], fill=255, width=width, joint="curve")
    if dot:
        cx, cy = to_px(*dot)
        rr = width * 0.9
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=255)


# ---------- îlots planaires ----------
def island_coords():
    idx = (np.arange(H, dtype=np.float32) + 0.5) * PX
    x = idx - R
    y = R - idx
    X, Y = np.meshgrid(x, y)
    return X, Y, np.hypot(X, Y), np.arctan2(Y, X)


def mask_from_drawing(fn, ss=4):
    """Dessine en sur-échantillonnage puis réduit (anticrénelage). fn(draw, scale)."""
    img = Image.new("L", (H * ss, H * ss), 0)
    fn(ImageDraw.Draw(img), ss)
    return np.asarray(img.resize((H, H), Image.LANCZOS), dtype=np.float32) / 255.0


def world_to_px(x, y, ss):
    return ((x + R) / PX * ss, (R - y) / PX * ss)


def rounded_rect_sdf(X, Y, cx, cy, ang, half_len, half_wid, corner):
    ca, sa = math.cos(ang), math.sin(ang)
    dx, dy = X - cx, Y - cy
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    qx = np.abs(u) - (half_len - corner)
    qy = np.abs(v) - (half_wid - corner)
    out = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    return out + np.minimum(np.maximum(qx, qy), 0) - corner


def seam(sdf, width=0.0035):
    return 1 - smoothstep(0, width, np.abs(sdf))


def brushed(Rr, Th, seed):
    st = streaks_1d(int(R / 0.0006) + 8, seed)
    wob = lowfreq(Rr.shape, 220, seed + 5) * 0.004
    rr = np.clip(((Rr + wob) / 0.0006).astype(np.int64), 0, len(st) - 1)
    st2 = streaks_1d(int(R / 0.0021) + 8, seed + 9, smooth=2)
    rr2 = np.clip(((Rr + wob * 0.5) / 0.0021).astype(np.int64), 0, len(st2) - 1)
    strength = 0.6 + 0.4 * lowfreq(Rr.shape, 90, seed + 7)
    return (0.65 * st[rr] + 0.35 * st2[rr2]) * strength


BASE = np.array([0.905, 0.913, 0.928], np.float32)  # argent légèrement froid (sRGB)


def upper_island():
    X, Y, Rr, Th = island_coords()
    br = brushed(Rr, Th, 11)
    lf = fractal(Rr.shape, [400, 140, 48], 21)
    tint = lowfreq(Rr.shape, 700, 33)
    smudge = smoothstep(0.55, 1.6, fractal(Rr.shape, [160, 60, 20], 41))
    alb = np.empty(Rr.shape + (3,), np.float32)
    for c in range(3):
        alb[..., c] = BASE[c] + 0.012 * lf + 0.006 * br - 0.022 * smudge
    alb[..., 0] += 0.0035 * tint
    alb[..., 2] += 0.0055 * tint
    alb[..., 1] -= 0.0015 * tint
    alb -= (0.03 * smoothstep(4.35, 4.62, Rr))[..., None]  # léger encrassement près du bord
    rough = 0.25 + 0.035 * br + 0.09 * smudge + 0.02 * lf
    height = br * 0.000015

    # Glyphes gravés (anneau r = 4,18 m, 6 groupes de 7)
    gsize, gpitch, r_g = 0.092, 0.128, 4.18

    def draw_ring(d, ss):
        for grp in range(6):
            base_ang = math.radians(grp * 60 + 30)
            for k in range(7):
                ang = base_ang + (k - 3) * gpitch / r_g
                cxw, cyw = r_g * math.cos(ang), r_g * math.sin(ang)
                tx, ty = -math.sin(ang), math.cos(ang)
                rx, ry = math.cos(ang), math.sin(ang)

                def to_px(gx, gy, cxw=cxw, cyw=cyw, tx=tx, ty=ty, rx=rx, ry=ry):
                    t = (gx - 20) / 40 * gsize
                    q = (20 - gy) / 40 * gsize
                    return world_to_px(cxw + t * tx + q * rx, cyw + t * ty + q * ry, ss)

                draw_glyph(d, 500 + grp * 7 + k, to_px, max(1, int(0.0058 / PX * ss)))

    engr = mask_from_drawing(draw_ring)
    height -= engr * 0.0015
    alb -= (engr * 0.10)[..., None]
    rough += engr * 0.22

    # Capteurs affleurants (6 hublots à r = 3,70 m)
    port = np.zeros_like(Rr)
    lens = np.zeros_like(Rr)
    for k in range(6):
        a = math.radians(k * 60)
        d = np.hypot(X - 3.70 * math.cos(a), Y - 3.70 * math.sin(a))
        port = np.maximum(port, seam(d - 0.062, 0.0028))
        lens = np.maximum(lens, 1 - smoothstep(0.050, 0.054, d))
    height -= port * 0.0018
    alb = alb * (1 - lens[..., None] * 0.86) + lens[..., None] * np.array([0.06, 0.05, 0.09])
    rough = rough * (1 - lens) + 0.06 * lens
    metal = 1 - 0.9 * lens
    return alb, rough, metal, height, np.zeros(Rr.shape + (3,), np.float32)


def heat_ramp(f):
    stops = [(0.00, (0.42, 0.47, 0.66)), (0.12, (0.50, 0.42, 0.62)), (0.26, (0.66, 0.50, 0.42)),
             (0.42, (0.80, 0.70, 0.52)), (0.62, (0.87, 0.84, 0.76)), (1.00, tuple(BASE))]
    out = np.zeros(f.shape + (3,), np.float32)
    for (f0, c0), (f1, c1) in zip(stops, stops[1:]):
        m = (f >= f0) & (f <= f1)
        t = ((f - f0) / (f1 - f0))[m][:, None]
        out[m] = np.array(c0) * (1 - t) + np.array(c1) * t
    out[f > 1] = BASE
    return out


def lower_island():
    X, Y, Rr, Th = island_coords()
    br = brushed(Rr, Th, 61)
    lf = fractal(Rr.shape, [400, 140, 48], 71)
    smudge = smoothstep(0.4, 1.5, fractal(Rr.shape, [160, 60, 20], 81))
    alb = np.empty(Rr.shape + (3,), np.float32)
    for c in range(3):
        alb[..., c] = BASE[c] - 0.03 + 0.014 * lf + 0.006 * br - 0.03 * smudge
    # Coloration thermique autour de l'émetteur ventral (titane revenu)
    wob = lowfreq(Rr.shape, 60, 91) * 0.035 + lowfreq(Rr.shape, 18, 92) * 0.012
    f = (Rr - 0.80) / 0.80 + wob
    heat = heat_ramp(np.clip(f, 0, 1.01))
    hs = (1 - smoothstep(0.85, 1.0, f)) * 0.72
    alb = alb * (1 - hs[..., None]) + heat * hs[..., None]
    # Traînées radiales de suie
    ang_noise = streaks_1d(4096, 95, smooth=5)
    ai = ((Th + math.pi) / (2 * math.pi) * 4095).astype(np.int64)
    soot = np.clip(ang_noise[ai], 0, None) * smoothstep(1.6, 1.9, Rr) * (1 - smoothstep(2.4, 3.3, Rr))
    soot *= 0.5 + 0.5 * lowfreq(Rr.shape, 120, 96)
    alb -= (0.035 * soot)[..., None]
    rough = 0.31 + 0.035 * br + 0.10 * smudge + 0.04 * soot - 0.06 * hs
    height = br * 0.000015

    # Joints des trappes des pieds
    doors = np.zeros_like(Rr)
    for a_deg in SP.LEG_ANGLES:
        a = math.radians(a_deg)
        sdf = rounded_rect_sdf(X, Y, SP.LEG_DOOR_R * math.cos(a), SP.LEG_DOOR_R * math.sin(a), a,
                               SP.LEG_DOOR_LEN / 2, SP.LEG_DOOR_WID / 2, SP.LEG_DOOR_CORNER)
        doors = np.maximum(doors, seam(sdf, 0.004))
    # Trappe d'accès en iris (cercle + 6 lames spirales)
    a = math.radians(SP.HATCH_ANGLE)
    hx, hy = SP.HATCH_R * math.cos(a), SP.HATCH_R * math.sin(a)
    dx, dy = X - hx, Y - hy
    rl = np.hypot(dx, dy)
    iris = seam(rl - SP.HATCH_RADIUS, 0.004)
    phi = np.arctan2(dy, dx) - 1.15 * rl / SP.HATCH_RADIUS
    sector = 2 * math.pi / 6
    dphi = np.abs(((phi + sector / 2) % sector) - sector / 2)
    blades = seam(dphi * rl, 0.0028) * (rl < SP.HATCH_RADIUS) * smoothstep(0.02, 0.05, rl)
    seams = np.maximum(np.maximum(doors, iris), blades)
    height -= seams * 0.002
    alb -= (seams * 0.25)[..., None]
    rough += seams * 0.15
    return alb, rough, np.ones_like(Rr), height, np.zeros(Rr.shape + (3,), np.float32)


# ---------- bande du bord ----------
def rim_strip():
    prof = SP.build_profile()
    _, _, s, total, (c0, c1) = SP.rim_arc_info(prof)
    W, Hh = S, S // 8
    pu = (2 * math.pi * SP.R_MAX / SP.RIM_REPEAT) / W
    pv = total / Hh
    vv = 1 - (np.arange(Hh, dtype=np.float32) + 0.5) / Hh  # 1 en haut de l'image
    V = np.repeat(vv[:, None], W, 1)
    st = streaks_1d(Hh * 4, 121)
    vi = np.clip((V * (Hh * 4 - 1)).astype(np.int64), 0, Hh * 4 - 1)
    lf = lowfreq((Hh, W), 60, 131)
    br = st[vi] * (0.7 + 0.3 * lf)
    chan = smoothstep(c0 - 0.01, c0 + 0.005, V) * (1 - smoothstep(c1 - 0.005, c1 + 0.01, V))
    alb = np.empty((Hh, W, 3), np.float32)
    for c in range(3):
        alb[..., c] = BASE[c] - 0.02 + 0.006 * br + 0.01 * lf
    chan_col = np.array([0.20, 0.19, 0.24], np.float32)
    alb = alb * (1 - chan[..., None]) + chan_col * chan[..., None]
    rough = 0.26 + 0.03 * br + chan * 0.14
    metal = 1 - 0.25 * chan

    # Glyphes lumineux dans la gorge, entre les émetteurs
    ch_h = (c1 - c0) * total  # hauteur du fond de gorge en mètres
    gsize = ch_h * 0.62
    pitch = gsize * 1.38
    vmid = (c0 + c1) / 2
    ss = 2
    img = Image.new("L", (W * ss, Hh * ss), 0)
    d = ImageDraw.Draw(img)
    span_m = 2 * math.pi * SP.R_MAX / SP.N_EMITTERS
    seed = 900
    for e in range(SP.N_EMITTERS // SP.RIM_REPEAT):
        u_center_m = (e + 0.5) * span_m + span_m / 2  # milieu entre deux émetteurs
        n = int((span_m - 0.20) / pitch)
        for k in range(n):
            um = u_center_m - (n - 1) / 2 * pitch + k * pitch

            def to_px(gx, gy, um=um):
                x_m = um + (gx - 20) / 40 * gsize
                v = vmid + (20 - gy) / 40 * gsize / total
                return ((x_m / pu) % W * ss, (1 - v) * Hh * ss)

            draw_glyph(d, seed, to_px, max(1, int(gsize * 0.075 / pu * ss)))
            seed += 1
    g = np.asarray(img.resize((W, Hh), Image.LANCZOS), dtype=np.float32) / 255.0
    emis = g[..., None] * np.array([0.78, 0.64, 1.0], np.float32)
    height = br * 0.00001 - g * 0.0006
    return alb, rough, metal, height, emis, (pu, pv)


def normal_from_height(h, px_u, px_v, strength=1.0):
    dhdc = np.gradient(h, axis=1) / px_u
    dhdr = np.gradient(h, axis=0) / px_v
    nx = -dhdc * strength
    ny = dhdr * strength  # convention OpenGL (vert vers +v)
    nz = np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln, ny / ln, nz / ln], -1)


def main():
    os.makedirs(OUT, exist_ok=True)
    alb = np.zeros((S, S, 3), np.float32) + BASE
    rough = np.full((S, S), 0.3, np.float32)
    metal = np.ones((S, S), np.float32)
    nrm = np.zeros((S, S, 3), np.float32)
    nrm[..., 2] = 1
    emis = np.zeros((S, S, 3), np.float32)

    print("dessus...")
    a, r, m, h, e = upper_island()
    alb[:H, :H], rough[:H, :H], metal[:H, :H], emis[:H, :H] = a, r, m, e
    nrm[:H, :H] = normal_from_height(h, PX, PX)
    print("dessous...")
    a, r, m, h, e = lower_island()
    alb[:H, H:], rough[:H, H:], metal[:H, H:], emis[:H, H:] = a, r, m, e
    nrm[:H, H:] = normal_from_height(h, PX, PX)
    print("bord...")
    a, r, m, h, e, (pu, pv) = rim_strip()
    hs = S // 8
    alb[S - hs:], rough[S - hs:], metal[S - hs:], emis[S - hs:] = a, r, m, e
    nrm[S - hs:] = normal_from_height(h, pu, pv)

    def save(arr, name):
        Image.fromarray(np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name), optimize=True)

    save(alb, "hull_albedo.png")
    orm = np.stack([np.ones_like(rough), np.clip(rough, 0.04, 1), np.clip(metal, 0, 1)], -1)
    save(orm, "hull_orm.png")
    save(nrm * 0.5 + 0.5, "hull_normal.png")
    save(emis, "hull_emissive.png")
    print("ok", OUT)


if __name__ == "__main__":
    main()
