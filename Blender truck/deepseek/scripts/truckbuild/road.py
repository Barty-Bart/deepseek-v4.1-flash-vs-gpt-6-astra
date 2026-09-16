"""Rough-road test set: analytic surface + geometry + wheel contact solver."""
import math, bpy
from . import spec
from . import util as U

# ------------------------------------------------------------------ surface profile
CHANNEL_HALF = 0.44          # |y| inside this is the recessed inspection channel
CHANNEL_TOP  = 0.52          # |y| where the channel wall meets the track surface
CHANNEL_Z    = -0.55         # channel floor height
TRACK_IN     = 0.52
TRACK_OUT    = 1.12          # track band outer edge
SHOULDER_END = 8.0

# (centre x, amplitude, half width) - the right side carries the featured bump
BUMPS = {
    -1: [(-5.2, 0.035, 0.40), (-2.8, 0.045, 0.36), (-0.4, 0.030, 0.42),
         (1.9, 0.040, 0.38), (4.3, 0.032, 0.44), (6.6, 0.045, 0.36),
         (8.9, 0.028, 0.40), (11.3, 0.042, 0.38), (13.6, 0.036, 0.42),
         (15.9, 0.048, 0.34), (18.2, 0.030, 0.44), (19.6, 0.078, 0.52),
         (21.4, 0.040, 0.30), (23.7, 0.034, 0.42), (26.1, 0.044, 0.38),
         (28.4, 0.030, 0.40), (30.8, 0.040, 0.36), (33.2, 0.034, 0.42),
         (36.0, 0.036, 0.40), (38.8, 0.030, 0.42)],
    1:  [(-6.0, 0.040, 0.38), (-3.5, 0.032, 0.42), (-1.1, 0.044, 0.36),
         (1.3, 0.030, 0.40), (3.6, 0.042, 0.38), (5.9, 0.034, 0.44),
         (8.2, 0.046, 0.34), (10.5, 0.028, 0.40), (12.9, 0.040, 0.38),
         (15.2, 0.033, 0.42), (17.6, 0.050, 0.40), (19.9, 0.030, 0.44),
         (22.3, 0.042, 0.36), (24.6, 0.032, 0.40), (27.0, 0.045, 0.38),
         (29.3, 0.030, 0.42), (31.6, 0.040, 0.36), (34.0, 0.044, 0.38),
         (36.8, 0.030, 0.42)],
}

FEATURE_BUMP_X = 19.6        # right rear wheel compression / rebound event
# additional featured bumps that land inside the long undercarriage shots
FEATURE_BUMPS = [(-1, 19.6, 0.078, 0.52), (1, 17.4, 0.050, 0.40),
                 (-1, 51.2, 0.072, 0.50), (1, 52.6, 0.048, 0.42),
                 (-1, 44.0, 0.075, 0.55), (1, 45.6, 0.050, 0.45),
                 (-1, 54.2, 0.070, 0.50), (1, 55.6, 0.048, 0.42),
                 (-1, 66.0, 0.072, 0.52), (1, 67.4, 0.050, 0.44),
                 (-1, 74.6, 0.068, 0.50), (1, 76.0, 0.046, 0.42),
                 (-1, 84.0, 0.070, 0.52), (1, 85.4, 0.048, 0.44)]


def _gen_bumps(x0, x1, seed, amp_lo=0.026, amp_hi=0.050, hw_lo=0.30, hw_hi=0.46):
    """Deterministic pseudo-random roughness so the whole road is reproducible."""
    out = []
    st = seed
    x = x0
    while x < x1:
        st = (1103515245 * st + 12345) % (2 ** 31)
        u1 = (st % 10000) / 10000.0
        st = (1103515245 * st + 12345) % (2 ** 31)
        u2 = (st % 10000) / 10000.0
        st = (1103515245 * st + 12345) % (2 ** 31)
        u3 = (st % 10000) / 10000.0
        amp = amp_lo + (amp_hi - amp_lo) * u1
        hw = hw_lo + (hw_hi - hw_lo) * u2
        out.append((round(x, 3), round(amp, 4), round(hw, 3)))
        x += 2.10 + 0.95 * u3
    return out


def _all_bumps():
    for side in (1, -1):
        lst = list(BUMPS[side])
        lst += _gen_bumps(41.0, 128.0, 9871 if side < 0 else 4441)
        for (s, cx, amp, hw) in FEATURE_BUMPS:
            if s == side and cx > 40.0:
                lst.append((cx, amp, hw))
        lst.sort()
        BUMPS[side] = lst


_all_bumps()


def _track_dz(x, side):
    z = 0.0
    for (cx, a, hw) in BUMPS[side]:
        d = x - cx
        if abs(d) < hw:
            z += a * 0.5 * (1.0 + math.cos(math.pi * d / hw))
    return z


def _track_dzdz(x, side):
    s = 0.0
    for (cx, a, hw) in BUMPS[side]:
        d = x - cx
        if abs(d) < hw:
            s += -a * 0.5 * (math.pi / hw) * math.sin(math.pi * d / hw)
    return s


def height(x, y):
    """Road surface height at (x, y)."""
    ay = abs(y)
    if ay <= CHANNEL_HALF:
        return CHANNEL_Z
    if ay < CHANNEL_TOP:
        t = (ay - CHANNEL_HALF) / (CHANNEL_TOP - CHANNEL_HALF)
        return CHANNEL_Z * (1.0 - U.smoothstep(t))
    if ay <= TRACK_OUT:
        return _track_dz(x, 1 if y > 0 else -1)
    # shoulder: slight crown falling away from the tracks
    t = min(1.0, (ay - TRACK_OUT) / 2.6)
    return -0.05 * t - 0.02 * t * t


def wheel_center_z(x, y):
    """Wheel centre height so the tyre rests on the (convex) road surface.

    Solves for the contact point where the surface normal passes through the
    wheel centre - keeps the tyre from sinking into bump peaks.
    """
    side = 1 if y > 0 else -1
    R = spec.TIRE_R
    xc = x
    for _ in range(24):
        h = _track_dzdz(xc, side)
        n = math.hypot(h, 1.0)
        xc_new = x + R * h / n
        if abs(xc_new - xc) < 1e-7:
            xc = xc_new
            break
        xc = xc_new
    h = _track_dzdz(xc, side)
    n = math.hypot(h, 1.0)
    return _track_dz(xc, side) + R / n


# ------------------------------------------------------------------ geometry
def _x_samples():
    from . import spec as S
    xs = []
    x = S.ROAD_X0
    while x < -10.0:                      # coarse lead-in
        xs.append(x)
        x += 0.35
    x = -10.0
    while x <= 100.0:                     # dense wherever wheels will be
        xs.append(x)
        x += 0.06
    x = 100.0
    while x <= S.ROAD_X1:
        xs.append(x)
        x += 0.35
    xs.append(S.ROAD_X1)
    return xs


YS = [-8.0, -6.0, -4.0, -2.6, -1.9, -1.30, -1.14, -1.12, -0.86, -0.52,
      -0.50, -0.46, -0.30, 0.0, 0.30, 0.46, 0.50, 0.52, 0.86, 1.12,
      1.14, 1.30, 1.9, 2.6, 4.0, 6.0, 8.0]


def build(coll, mats):
    xs = _x_samples()
    ny = len(YS)
    verts = []
    for x in xs:
        for y in YS:
            verts.append((x, y, height(x, y)))
    faces = []
    for i in range(len(xs) - 1):
        a = i * ny
        b = (i + 1) * ny
        for j in range(ny - 1):
            faces.append([a + j, a + j + 1, b + j + 1, b + j])
    ob = U.mesh_obj('ROAD_Surface', verts, faces, coll)
    for m in (mats['asphalt'], mats['gravel'], mats['channel']):
        ob.data.materials.append(m)
    for p in ob.data.polygons:
        cy = p.center.y
        ay = abs(cy)
        if ay < CHANNEL_TOP + 0.02:
            p.material_index = 2
        elif ay > TRACK_OUT + 0.05:
            p.material_index = 1
        else:
            p.material_index = 0

    # side skirts + end caps so the slab reads as solid ground
    skirt_h = 1.4
    v = []
    f = []
    for (idx_y, yedge) in ((0, YS[0]), (ny - 1, YS[-1])):
        base = len(v)
        for x in xs:
            v.append((x, yedge, height(x, yedge)))
        for x in xs:
            v.append((x, yedge, -skirt_h))
        for i in range(len(xs) - 1):
            f.append([base + i, base + i + 1, base + len(xs) + i + 1, base + len(xs) + i])
    for (idx_x, xedge) in ((0, xs[0]), (len(xs) - 1, xs[-1])):
        base = len(v)
        for y in YS:
            v.append((xedge, y, height(xedge, y)))
        for y in YS:
            v.append((xedge, y, -skirt_h))
        for j in range(ny - 1):
            f.append([base + j, base + j + 1, base + ny + j + 1, base + ny + j])
    # channel end walls
    ob2 = U.mesh_obj('ROAD_Skirts', v, f, coll, mat=mats['gravel'])

    # channel floor detail: shallow formed joints every 6 m
    jv, jf = [], []
    step = 6.0
    x = -24.0
    while x <= 134.0:
        b = len(jv)
        for y in (-CHANNEL_HALF + 0.02, CHANNEL_HALF - 0.02):
            jv.append((x, y, CHANNEL_Z + 0.004))
        jv.append((x + 0.05, -CHANNEL_HALF + 0.02, CHANNEL_Z + 0.004))
        jv.append((x + 0.05, CHANNEL_HALF - 0.02, CHANNEL_Z + 0.004))
        jf.append([b + 0, b + 1, b + 2])
        jf.append([b + 1, b + 3, b + 2])
        x += step
    U.mesh_obj('ROAD_ChannelJoints', jv, jf, coll, mat=mats['channel_detail'])
    return ob


def road_stats():
    from . import spec as S
    return dict(x0=S.ROAD_X0, x1=S.ROAD_X1, channel_z=CHANNEL_Z,
                max_bump=max(a for s in BUMPS.values() for (_, a, _) in s))
