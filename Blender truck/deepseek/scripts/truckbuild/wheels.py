"""Wheels: 31.5in all-terrain tyre with real tread-block geometry, alloy rim, rotor."""
import math
from mathutils import Euler, Vector
from . import spec
from . import util as U

TAU = math.tau
R = spec.TIRE_R          # 0.395 lug-top radius (defines rolling radius)
RIM_R = spec.RIM_R
HW = spec.TIRE_W / 2.0   # 0.14

# axial (y) stations of the tread pattern, groove edges included
_TREAD_Y = [-0.118, -0.106, -0.084, -0.062, -0.0415, -0.040, -0.029,
            -0.0275, -0.014, 0.0, 0.014, 0.0275, 0.029, 0.040, 0.0415,
            0.062, 0.084, 0.106, 0.118]

_TIRE_SECTION = ([
    (0.236, -0.132), (0.262, -0.140), (0.292, -0.140), (0.322, -0.138),
    (0.350, -0.133), (0.370, -0.124), (0.381, -0.118),
] + [(0.381, y) for y in _TREAD_Y] + [
    (0.381, 0.118), (0.370, 0.124), (0.350, 0.133), (0.322, 0.138),
    (0.292, 0.140), (0.262, 0.140), (0.236, 0.132),
    (0.228, 0.120), (0.226, 0.0), (0.228, -0.120),
])


def _smooth_square(t, duty, edge):
    lo = 0.5 - duty / 2.0
    hi = 0.5 + duty / 2.0
    if t < lo - edge or t > hi + edge:
        return 0.0
    if lo + edge <= t <= hi - edge:
        return 1.0
    if t < lo + edge:
        return U.smoothstep((t - (lo - edge)) / (2 * edge))
    return U.smoothstep(((hi + edge) - t) / (2 * edge))


def _row_mask(y):
    ay = abs(y)
    if ay > 0.106:
        return 0.0
    if 0.040 < ay < 0.0415:
        return 0.0
    return 1.0


def _tread_r(a, y, base):
    """Tread radius: lug tops reach exactly R so the rolling radius is exact."""
    t = (a * 34.0 / TAU) % 1.0
    lug = _smooth_square(t, 0.62, 0.10)
    m = _row_mask(y)
    if base > 0.34:
        return 0.381 + 0.014 * lug * m
    return base


def build_wheel(name, coll, mats, flip=False):
    """One wheel object: origin at the wheel centre, axle along local Y."""
    b = U.Builder()
    b.revolve(_TIRE_SECTION, 96, mat=0, rfun=_tread_r, smooth=True)
    # --- rim barrel (inboard lip -> outboard face) ---
    barrel = [(0.236, -0.118), (0.232, -0.100), (0.196, -0.090), (0.190, -0.060),
              (0.190, 0.085), (0.196, 0.098), (0.232, 0.108), (0.236, 0.118)]
    b.revolve(barrel + [(0.230, 0.118), (0.230, -0.118)], 48, mat=1, smooth=True)
    # outboard face annulus
    face = [(0.190, -0.118), (0.232, -0.118), (0.232, -0.135), (0.176, -0.132)]
    b.revolve(face + [(0.176, -0.118)], 48, mat=1, smooth=False)
    # hub + spokes
    hub = [(0.088, -0.150), (0.088, -0.098), (0.0, -0.098), (0.0, -0.150)]
    b.revolve(hub, 32, mat=1, smooth=False)
    for k in range(6):
        th = TAU * k / 6.0 + 0.26
        d = Vector((math.cos(th), 0.0, math.sin(th)))
        n = Vector((-math.sin(th), 0.0, math.cos(th)))
        rr0, rr1 = 0.075, 0.186
        w0, w1 = 0.052, 0.036
        y0, y1 = -0.148, -0.118
        c = (rr0 + rr1) / 2.0
        v = []
        for (rt, wt) in ((rr0, w0), (rr1, w1)):
            for sgn in (1, -1):
                p = d * rt + n * (wt * sgn)
                v.append((p.x, y0, p.z))
                v.append((p.x, y1, p.z))
        faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3]]
        b.add(v, faces, mat=1, smooth=False)
    # lug nuts
    for k in range(6):
        th = TAU * k / 6.0 + 0.26
        p = Vector((math.cos(th), 0, math.sin(th))) * 0.055
        b.revolve([(0.017, -0.164), (0.017, -0.150), (0.0, -0.150), (0.0, -0.164)],
                  6, mat=2, smooth=False, offset=(p.x, 0, p.z))
    # --- brake rotor (rotates with the wheel) fitted inside the barrel ---
    rotor = [(0.176, 0.014), (0.176, 0.040), (0.182, 0.040), (0.182, 0.014)]
    b.revolve(rotor, 40, mat=3, smooth=False)
    rot2 = [(0.176, -0.014), (0.176, 0.014), (0.096, 0.014), (0.096, -0.014)]
    b.revolve(rot2, 40, mat=3, smooth=False)
    # cooling vanes between the two rotor faces
    for k in range(20):
        th = TAU * k / 20.0
        d = Vector((math.cos(th), 0, math.sin(th)))
        n = Vector((-math.sin(th), 0, math.cos(th)))
        v = []
        for rr in (0.110, 0.170):
            for s in (1, -1):
                p = d * rr + n * (0.005 * s)
                v.append((p.x, -0.013, p.z))
                v.append((p.x, 0.013, p.z))
        b.add(v, [[0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]],
              mat=3, smooth=False)

    if flip:
        b.v = [(v[0], -v[1], v[2]) for v in b.v]
        b.f = [list(reversed(f)) for f in b.f]
    ob = b.object(name, coll, [mats['rubber'], mats['alloy'], mats['steel'],
                               mats['brake_steel']])
    U.noise_bump(mats['rubber'], scale=90.0, strength=0.25, rough_var=0.05)
    return ob


def build_caliper(name, coll, mats):
    """Caliper + pads: mounts on the knuckle/axle, straddles the rotor at y=+0.027."""
    b = U.Builder()
    # body over the top of the rotor
    v = []
    for y in (0.006, 0.056):
        for (x, z) in ((-0.085, 0.150), (0.085, 0.150), (0.085, 0.088), (-0.085, 0.088)):
            v.append((x, y, z))
    b.add(v, [[0, 1, 5, 4], [3, 7, 6, 2], [0, 4, 6, 2], [1, 3, 7, 5],
              [0, 2, 3, 1], [4, 5, 7, 6]], mat=0, smooth=False)
    # sliding bracket toward the rear of the knuckle
    v2 = []
    for x in (-0.128, -0.082):
        for (y, z) in ((0.006, 0.140), (0.006, 0.062), (0.056, 0.062), (0.056, 0.140)):
            v2.append((x, y, z))
    b.add(v2, [[0, 1, 2, 3], [4, 5, 6, 7], [0, 3, 7, 4], [1, 5, 6, 2],
               [0, 4, 5, 1], [3, 2, 6, 7]], mat=0, smooth=False)
    return b.object(name, coll, [mats['caliper']])


def build_brake_hose_anchor(name, coll, mats):
    b = U.Builder()
    b.revolve([(0.011, 0.0), (0.011, 0.030), (0.0, 0.030), (0.0, 0.0)], 10,
              mat=0, smooth=False)
    return b.object(name, coll, [mats['steel']])
