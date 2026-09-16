"""Front double-wishbone and rear leaf-spring suspension: geometry and kinematics.

Kinematics are solved in the sprung-mass local frame and are fully deterministic:

* FRONT - a planar 4-bar linkage (frame / lower arm / knuckle / upper arm) lying in
  the (y,z) plane.  The lower-arm angle is bisected until the wheel centre reaches
  the height the road demands; the knuckle's rigid-body transform follows from the
  solved ball joints, so camber change and track change are real linkage outputs.
  Steering rotates the knuckle about the kingpin axis.
* REAR - the beam axle is positioned by the two wheel centres (position + roll), the
  differential rides with it.  Each leaf spring is a fixed-length chain solved with
  FABRIK: front eye pinned to the frame, middle joint clamped to the axle, rear eye
  constrained to the shackle circle.  The damper is a rigid link that re-aims and
  whose rod slides so its length stays exact.
"""
import math
from mathutils import Vector, Matrix, Quaternion
from . import spec as S
from . import util as U

TAU = math.tau
NLEAF = 14
LEAF_SUB = 6
AXLE_CLAMP_DZ = 0.069          # axle tube radius + main-leaf half thickness


# ======================================================================================
# shared helpers
# ======================================================================================
def wrap_pi(a):
    """Wrap an angle into (-pi, pi] - essential because the leaf chain runs along -X
    where atan2 jumps between +pi and -pi."""
    while a > math.pi:
        a -= TAU
    while a <= -math.pi:
        a += TAU
    return a


def _rot2(v, a):
    c, s = math.cos(a), math.sin(a)
    return Vector((v.x * c - v.y * s, v.x * s + v.y * c))


def _v3(side, uv, x):
    return Vector((x, side * uv.x, uv.y))


def link(name, length, r, coll, mat, nseg=12):
    """Rigid link whose origin is at its base end, extending along local +X."""
    return U.pipe(name, [(0, 0, 0), (length, 0, 0)], r, coll, mat, nseg=nseg)


def place_link(ob, base, tip, rest_len, scale_x=True):
    d = Vector(tip) - Vector(base)
    L = d.length
    U.aim(ob, d)
    ob.location = tuple(base)
    if scale_x:
        ob.scale = (L / rest_len, 1.0, 1.0)
    return L


# ======================================================================================
# front double wishbone
# ======================================================================================
class FrontGeo:
    def __init__(self, side):
        self.side = side
        self.PL = Vector(S.FS_LOW_PIVOT)
        self.LB0 = Vector(S.FS_LOW_BALL)
        self.PU = Vector(S.FS_UP_PIVOT)
        self.UB0 = Vector(S.FS_UP_BALL)
        self.WC0 = Vector((S.WHEEL_Y, S.RIDE_Z))
        self.d_low = (self.LB0 - self.PL).length
        self.d_up = (self.UB0 - self.PU).length
        self.d_kn = (self.UB0 - self.LB0).length
        self.ang_low0 = math.atan2(self.LB0.y - self.PL.y, self.LB0.x - self.PL.x)
        self.ang_up0 = math.atan2(self.UB0.y - self.PU.y, self.UB0.x - self.PU.x)
        self.wc_rest = (self.WC0 - self.LB0).length
        probe = self._ubj_raw(self.LB0, +1.0)
        self.sense = 1.0 if (probe - self.UB0).length < 1e-9 else -1.0

    def _ubj_raw(self, lbj, sense):
        d = max(1e-6, (lbj - self.PU).length)
        a = (self.d_up ** 2 - self.d_kn ** 2 + d * d) / (2 * d)
        h = math.sqrt(max(0.0, self.d_up ** 2 - a * a))
        base = self.PU + (lbj - self.PU) * (a / d)
        perp = Vector((-(lbj - self.PU).y, (lbj - self.PU).x)) / d
        return base + perp * (h * sense)

    def solve(self, theta):
        lbj = self.PL + _rot2(self.LB0 - self.PL, theta)
        ubj = self._ubj_raw(lbj, self.sense)
        a0 = self.UB0 - self.LB0
        a1 = ubj - lbj
        phi = math.atan2(a1.y, a1.x) - math.atan2(a0.y, a0.x)
        wc = lbj + _rot2(self.WC0 - self.LB0, phi)
        return lbj, ubj, phi, wc

    def theta_for(self, target_z, lo=-0.55, hi=0.55):
        f = lambda t: self.solve(t)[3].y - target_z
        flo, fhi = f(lo), f(hi)
        if flo * fhi > 0.0:
            return lo if abs(flo) < abs(fhi) else hi
        for _ in range(56):
            mid = 0.5 * (lo + hi)
            fm = f(mid)
            if flo * fm <= 0.0:
                hi, fhi = mid, fm
            else:
                lo, flo = mid, fm
        return 0.5 * (lo + hi)

    def state(self, wheel_z):
        th = self.theta_for(wheel_z)
        lbj, ubj, phi, wc = self.solve(th)
        return dict(theta=th, lbj=lbj, ubj=ubj, phi=phi, wc=wc)

    def coil_low(self, theta):
        off = Vector((S.FS_COIL_LOW[0] - self.PL.x, S.FS_COIL_LOW[1] - self.PL.y))
        return self.PL + _rot2(off, theta)

    def steer_ball(self, lbj, phi):
        off = Vector((S.FS_STEER_ARM_UV[0] - self.LB0.x,
                      S.FS_STEER_ARM_UV[1] - self.LB0.y))
        return lbj + _rot2(off, phi)

    def steer_ball3(self, side, lbj, phi):
        return _v3(side, self.steer_ball(lbj, phi),
                   S.FS_ARM_X + S.FS_STEER_ARM_DX)


def build_front(colls, mats, reg):
    C, M = colls['FRONT_SUSPENSION'], mats
    R = colls['RIG']
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        g = FrontGeo(side)
        reg.put('frontgeo_' + tag, g)
        x = S.FS_ARM_X
        # ---- lower arm (origin at pivot) ----
        p3 = _v3(side, g.PL, x)
        b3 = _v3(side, g.LB0, x)
        arm = U.sweep_ribbon('FS_LowerArm_%s' % tag,
                             [(0.0, 0.0, 0.0), tuple(b3 - p3)], 0.070, 0.026, C,
                             M['steel'], width_axis=(1, 0, 0), bev=0.010)
        arm.location = tuple(p3)
        reg.put('front_lower_arm_' + tag, arm)
        # arm end ball joint housing
        bj = U.sphere('FS_LowerBallJoint_%s' % tag, 0.040, tuple(p3 + (b3 - p3)),
                      C, M['steel'], segs=14, rings=8)
        U.parent(bj, arm)
        # ---- upper arm ----
        pu3 = _v3(side, g.PU, x)
        u3 = _v3(side, g.UB0, x)
        uarm = U.sweep_ribbon('FS_UpperArm_%s' % tag,
                              [(0.0, 0.0, 0.0), tuple(u3 - pu3)], 0.055, 0.022, C,
                              M['steel'], width_axis=(1, 0, 0), bev=0.010)
        uarm.location = tuple(pu3)
        reg.put('front_upper_arm_' + tag, uarm)
        ubj = U.sphere('FS_UpperBallJoint_%s' % tag, 0.034, tuple(u3), C,
                       M['steel'], segs=14, rings=8)
        U.parent(ubj, uarm)
        # pivot brackets + bushings
        for (pt, nm) in ((g.PL, 'Low'), (g.PU, 'Up')):
            for dy in (-0.048, 0.048):
                U.cylinder('FS_PivotBush_%s%s' % (nm, tag), 0.030, 0.05,
                           (x + dy, side * pt.x, pt.y), axis='X', coll=C,
                           mat=M['rubber'], verts=12)
            U.box('FS_PivotBracket_%s%s' % (nm, tag), (0.13, 0.075, 0.10),
                  (x + 0.0, side * pt.x, pt.y + 0.075 * (1 if nm == 'Low' else -1)),
                  C, M['frame'], bev=0.008)
        # ---- knuckle ----
        kb = U.Builder()
        kn = g.UB0 - g.LB0                      # (du, dz) of the upright
        sp = g.WC0 - g.LB0                      # (du, dz) of the spindle
        sa = Vector((S.FS_STEER_ARM_UV[0] - g.LB0.x, S.FS_STEER_ARM_UV[1] - g.LB0.y))
        y0, y1 = side * 0.034, side * -0.034

        def prism(u0, u1, z0, z1, x0=-0.030, x1=0.030, mat=0):
            v = []
            for xx in (x0, x1):
                for (yy, zz) in ((u0, z0), (u1, z0), (u1, z1), (u0, z1)):
                    v.append((xx, yy * side, zz))
            f = [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2],
                 [2, 6, 7, 3], [3, 7, 4, 0]]
            kb.add(v, f, mat)
        prism(0.034, -0.034, 0.0, kn.y)                     # upright
        prism(0.05, 0.16, sp.y - 0.055, sp.y + 0.055, -0.075, 0.075)   # spindle
        prism(-0.04, 0.03, sa.y - 0.055, sa.y + 0.055, -0.20, 0.0)     # steering arm
        prism(-0.02, 0.06, 0.30, 0.42, -0.04, 0.04)                     # abs sensor boss
        knu = kb.object('FS_Knuckle_%s' % tag, C, [M['steel']])
        U.bevel(knu, 0.007, 2, 30)
        knu.location = tuple(_v3(side, g.LB0, x))
        # hub flange
        hub = U.cylinder('FS_Hub_%s' % tag, 0.086, 0.105,
                         (S.FS_ARM_X, side * S.WHEEL_Y, S.RIDE_Z), axis='Y',
                         coll=C, mat=M['steel'], verts=18)
        # control empty: origin at the lower ball joint (rest)
        ctrl = U.ensure_empty('CTRL_FSusp_%s' % tag, R, 0.22)
        ctrl.location = tuple(_v3(side, g.LB0, x))
        reg.put('fctrl_' + tag, ctrl)
        for ob in (knu, hub):
            U.parent(ob, ctrl)
        # caliper
        cal = _caliper('FS_Caliper_%s' % tag, C, M, side)
        cal.location = (S.FS_ARM_X, side * S.WHEEL_Y, S.RIDE_Z)
        U.parent(cal, ctrl)
        # ---- coil-over ----
        lo = _v3(side, Vector((S.FS_COIL_LOW[0], S.FS_COIL_LOW[1])), x)
        up = _v3(side, Vector((S.FS_COIL_UP[0], S.FS_COIL_UP[1])), x)
        L = (up - lo).length
        body = link('FS_CoilBody_%s' % tag, L * 0.58, 0.050, C, M['steel'], 14)
        rod = link('FS_CoilRod_%s' % tag, L * 0.52, 0.021, C, M['chrome'], 10)
        spring = U.helix('FS_CoilSpring_%s' % tag, 0.086, 0.016, L * 0.50, 8.5, C,
                         M['steel'], segs=9, nseg=7)
        for ob in (body, rod, spring):
            ob.parent = None
        reg.put('coil_body_' + tag, body)
        reg.put('coil_rod_' + tag, rod)
        reg.put('coil_spring_' + tag, spring)
        reg.put('coil_up_' + tag, up)
        reg.put('coil_len_' + tag, L)
        U.box('FS_Tower_%s' % tag, (0.20, 0.055, 0.22),
              (x, side * 0.505, 0.905), C, M['frame'], bev=0.008)
        U.box('FS_TowerBrace_%s' % tag, (0.16, 0.16, 0.045),
              (x, side * 0.470, 0.980), C, M['frame'], bev=0.006)
        # ---- tie rod ----
        inner = Vector((S.RACK_X, side * S.RACK_HW, S.RACK_Z))
        outer = g.steer_ball3(side, g.LB0, 0.0)
        tl = (outer - inner).length
        tr = link('FS_TieRod_%s' % tag, tl, 0.017, C, M['steel'], 10)
        reg.put('tierod_' + tag, tr)
        reg.put('tierod_len_' + tag, tl)
        reg.put('tierod_inner_' + tag, inner)
        U.cylinder('FS_TieRodEnd_%s' % tag, 0.028, 0.05, tuple(inner),
                   axis='Y', coll=C, mat=M['steel'], verts=12)
        # ---- brake hose (two rigid segments, re-aimed each frame) ----
        h1 = link('FS_BrakeHose_%s_1' % tag, 0.20, 0.0075, C, M['hose'], 8)
        h2 = link('FS_BrakeHose_%s_2' % tag, 0.22, 0.0075, C, M['hose'], 8)
        reg.put('brakehose_' + tag, (h1, h2))
        reg.put('brakehose_len_' + tag, (0.20, 0.22))
        # bump stop
        U.cylinder('FS_BumpStop_%s' % tag, 0.040, 0.085,
                   (x - 0.12, side * 0.505, 0.845), coll=C, mat=M['rubber'],
                   verts=12)
    return C


def _caliper(name, coll, mats, side):
    b = U.Builder()
    v = []
    for y in (0.006, 0.058):
        for (x, z) in ((-0.088, 0.152), (0.088, 0.152), (0.088, 0.086), (-0.088, 0.086)):
            v.append((x, y, z))
    b.add(v, [[0, 1, 5, 4], [3, 7, 6, 2], [0, 4, 6, 2], [1, 3, 7, 5],
              [0, 2, 3, 1], [4, 5, 7, 6]], mat=0)
    v2 = []
    for x in (-0.130, -0.084):
        for (y, z) in ((0.006, 0.142), (0.006, 0.060), (0.058, 0.060), (0.058, 0.142)):
            v2.append((x, y, z))
    b.add(v2, [[0, 1, 2, 3], [4, 5, 6, 7], [0, 3, 7, 4], [1, 5, 6, 2],
               [0, 4, 5, 1], [3, 2, 6, 7]], mat=0)
    if side > 0:
        b.v = [(v[0], -v[1], v[2]) for v in b.v]
        b.f = [list(reversed(f)) for f in b.f]
    return b.object(name, coll, [mats['caliper']])


# ======================================================================================
# rear leaf spring chain
# ======================================================================================
def leaf_rest_arc():
    p0 = Vector((S.LEAF_FRONT_EYE[0], S.LEAF_FRONT_EYE[2]))
    p1 = Vector((S.AXLE_R, S.RIDE_Z + AXLE_CLAMP_DZ))
    p2 = Vector((S.LEAF_REAR_EYE[0], S.LEAF_REAR_EYE[2]))
    ax, ay = p0.x, p0.y
    bx, by = p1.x, p1.y
    cx, cy = p2.x, p2.y
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax ** 2 + ay ** 2) * (by - cy) + (bx ** 2 + by ** 2) * (cy - ay)
          + (cx ** 2 + cy ** 2) * (ay - by)) / d
    uy = ((ax ** 2 + ay ** 2) * (cx - bx) + (bx ** 2 + by ** 2) * (ax - cx)
          + (cx ** 2 + cy ** 2) * (bx - ax)) / d
    c = Vector((ux, uy))
    r = (p0 - c).length
    return c, r, p0, p1, p2


def leaf_chain(n=NLEAF):
    c, r, p0, p1, p2 = leaf_rest_arc()
    a0 = math.atan2(p0.y - c.y, p0.x - c.x)
    a1 = math.atan2(p1.y - c.y, p1.x - c.x)
    a2 = math.atan2(p2.y - c.y, p2.x - c.x)
    pts = []
    for i in range(n + 1):
        t = i / n
        ang = (a0 + (a1 - a0) * (t / 0.5)) if t <= 0.5 else (a1 + (a2 - a1) * ((t - 0.5) / 0.5))
        pts.append(Vector((c.x + r * math.cos(ang), c.y + r * math.sin(ang))))
    return pts


def leaf_solve(clamp, front_eye, shackle_pivot, shackle_len, chain, iters=220):
    n = len(chain) - 1
    mid = n // 2
    d = [(chain[i + 1] - chain[i]).length for i in range(n)]
    q = [Vector(p) for p in chain]
    q[0] = Vector(front_eye)
    for _ in range(iters):
        q[0] = Vector(front_eye)
        for i in range(1, n + 1):
            if i == mid:
                q[i] = Vector(clamp)
            else:
                v = q[i] - q[i - 1]
                L = v.length or 1e-9
                q[i] = q[i - 1] + v * (d[i - 1] / L)
        v = q[n] - Vector(shackle_pivot)
        q[n] = Vector(shackle_pivot) + v.normalized() * shackle_len
        for i in range(n - 1, -1, -1):
            if i == mid:
                q[i] = Vector(clamp)
            else:
                v = q[i] - q[i + 1]
                L = v.length or 1e-9
                q[i] = q[i + 1] + v * (d[i] / L)
        q[0] = Vector(front_eye)
    return q


def build_rear(colls, mats, reg):
    C, M = colls['REAR_SUSPENSION'], mats
    R = colls['RIG']
    # ---- driven beam axle ----
    ax = U.ensure_empty('CTRL_RearAxle', R, 0.32)
    ax.location = (S.AXLE_R, 0.0, S.RIDE_Z)
    reg.put('axle_ctrl', ax)
    parts = []
    parts.append(U.cylinder('Rear_AxleTube', S.AXLE_TUBE_R, 1.44,
                            (S.AXLE_R, 0, S.RIDE_Z), axis='Y', coll=C,
                            mat=M['steel'], verts=20))
    parts.append(U.sphere('Rear_DiffHousing', S.DIFF_R, (S.AXLE_R, -0.155, S.RIDE_Z),
                          C, M['steel'], segs=20, rings=12))
    parts.append(U.cylinder('Rear_DiffCover', 0.126, 0.05,
                            (S.AXLE_R, -0.285, S.RIDE_Z), axis='Y', coll=C,
                            mat=M['steel'], verts=18))
    parts.append(U.cylinder('Rear_DiffPinionNose', 0.058, 0.16,
                            (S.AXLE_R + 0.16, -0.02, S.RIDE_Z), axis='X', coll=C,
                            mat=M['steel'], verts=14))
    parts.append(U.cylinder('Rear_DiffYoke', 0.056, 0.055,
                            (S.AXLE_R + 0.245, -0.02, S.RIDE_Z), axis='X', coll=C,
                            mat=M['steel'], verts=12))
    parts.append(U.cylinder('Rear_DiffFill', 0.030, 0.03,
                            (S.AXLE_R, -0.055, S.RIDE_Z + 0.11), coll=C,
                            mat=M['steel'], verts=10))
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        parts.append(U.cylinder('Rear_Hub_%s' % tag, 0.074, 0.14,
                                (S.AXLE_R, side * 0.700, S.RIDE_Z), axis='Y',
                                coll=C, mat=M['steel'], verts=16))
        parts.append(U.cylinder('Rear_BackingPlate_%s' % tag, 0.168, 0.018,
                                (S.AXLE_R, side * 0.618, S.RIDE_Z), axis='Y',
                                coll=C, mat=M['steel'], verts=20))
        parts.append(U.box('Rear_LeafSeat_%s' % tag, (0.30, 0.105, 0.070),
                           (S.AXLE_R, side * 0.640, S.RIDE_Z + 0.055), C,
                           M['steel'], bev=0.006))
        for xx in (-0.10, 0.10):
            parts.append(U.box('Rear_Ubolt_%s_%d' % (tag, int(abs(xx) * 100)),
                               (0.020, 0.022, 0.21),
                               (S.AXLE_R + xx, side * 0.640, S.RIDE_Z + 0.095), C,
                               M['steel']))
        parts.append(U.box('Rear_ShockMount_%s' % tag, (0.05, 0.055, 0.075),
                           (S.RSHOCK_LOW[0], side * S.RSHOCK_LOW[1],
                            S.RSHOCK_LOW[2] + 0.055), C, M['steel'], bev=0.006))
        parts.append(U.box('Rear_TrackBarMount_%s' % tag, (0.06, 0.06, 0.05),
                           (S.AXLE_R + 0.14, side * (S.AXLE_TUBE_R + 0.03),
                            S.RIDE_Z), C, M['steel'], bev=0.004))
    for p in parts:
        U.parent(p, ax)
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        cal = _caliper('Rear_Caliper_%s' % tag, C, M, side)
        cal.location = (S.AXLE_R, side * S.WHEEL_Y, S.RIDE_Z)
        U.parent(cal, ax)
    # ---- leaf springs ----
    chain = leaf_chain()
    reg.put('leaf_chain', chain)
    c, r, p0, p1, p2 = leaf_rest_arc()
    reg.put('leaf_arc', (c, r))
    fe = Vector((S.LEAF_FRONT_EYE[0], S.LEAF_FRONT_EYE[2]))
    sp = Vector((S.SHACKLE_PIVOT[0], S.SHACKLE_PIVOT[2]))
    slen = (sp - Vector((S.LEAF_REAR_EYE[0], S.LEAF_REAR_EYE[2]))).length
    reg.put('leaf_eyes', (fe, sp, slen))
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        arm = build_leaf_armature('LeafArm_%s' % tag, chain, side, R)
        reg.put('leaf_arm_' + tag, arm)
        mesh = build_leaf_mesh('Rear_LeafSpring_%s' % tag, chain, side, C, M)
        bind_leaf(mesh, arm, chain)
        reg.put('leaf_mesh_' + tag, mesh)
        # hanger + shackle
        U.box('Rear_LeafHanger_%s' % tag, (0.095, 0.075, 0.155),
              (S.LEAF_FRONT_EYE[0], side * 0.640, S.LEAF_FRONT_EYE[2] + 0.078), C,
              M['frame'], bev=0.008)
        U.cylinder('Rear_LeafEye_%s' % tag, 0.030, 0.075,
                   (S.LEAF_FRONT_EYE[0], side * 0.640, S.LEAF_FRONT_EYE[2]),
                   axis='Y', coll=C, mat=M['rubber'], verts=12)
        U.box('Rear_ShackleBracket_%s' % tag, (0.03, 0.075, 0.09),
              (S.SHACKLE_PIVOT[0], side * 0.640, S.SHACKLE_PIVOT[2] + 0.045), C,
              M['frame'], bev=0.004)
        link_ob = U.box('Rear_Shackle_%s' % tag, (0.036, 0.062, slen),
                        (0, 0, 0), C, M['steel'], bev=0.005)
        reg.put('shackle_' + tag, link_ob)
        reg.put('shackle_len', slen)
        # damper
        lo = Vector((S.RSHOCK_LOW[0], side * S.RSHOCK_LOW[1], S.RSHOCK_LOW[2]))
        up = Vector((S.RSHOCK_UP[0], side * S.RSHOCK_UP[1], S.RSHOCK_UP[2]))
        L = (up - lo).length
        dbody = link('Rear_ShockBody_%s' % tag, L * 0.55, 0.040, C, M['steel'], 14)
        drod = link('Rear_ShockRod_%s' % tag, L * 0.52, 0.016, C, M['chrome'], 10)
        reg.put('shock_body_' + tag, dbody)
        reg.put('shock_rod_' + tag, drod)
        reg.put('shock_up_' + tag, up)
        reg.put('shock_lo_' + tag, lo)
        reg.put('shock_len_' + tag, L)
        # bump stop on the frame
        U.cylinder('Rear_BumpStop_%s' % tag, 0.044, 0.10,
                   (S.AXLE_R, side * 0.46, 0.715), coll=C, mat=M['rubber'], verts=12)
        h1 = link('Rear_BrakeHose_%s_1' % tag, 0.18, 0.0075, C, M['hose'], 8)
        h2 = link('Rear_BrakeHose_%s_2' % tag, 0.20, 0.0075, C, M['hose'], 8)
        reg.put('rbrakehose_' + tag, (h1, h2))
    return C


def build_leaf_armature(name, chain, side, rig_coll):
    ob = U.ensure_armature(name, rig_coll)
    U.enter_edit(ob)
    prev = None
    for i in range(len(chain) - 1):
        b = ob.data.edit_bones.new('seg_%02d' % i)
        b.head = (chain[i].x, side * 0.640, chain[i].y)
        b.tail = (chain[i + 1].x, side * 0.640, chain[i + 1].y)
        b.roll = 0.0
        if prev is not None:
            b.parent = prev
            b.use_connect = True
        prev = b
    U.exit_edit(ob)
    return ob


def build_leaf_mesh(name, chain, side, coll, mats):
    arc = sample_arc(chain, LEAF_SUB)
    blades = [(0.00, 1.00, 0.0135, 0.0), (0.18, 0.82, 0.0125, -0.013),
              (0.34, 0.66, 0.0115, -0.024), (0.48, 0.52, 0.0105, -0.033)]
    b = U.Builder()
    for (t0, t1, th, dz) in blades:
        i0 = int(round(t0 * (len(arc) - 1)))
        i1 = int(round(t1 * (len(arc) - 1)))
        seg = arc[i0:i1 + 1]
        v = []
        for i, p in enumerate(seg):
            if i == 0:
                tv = seg[1] - seg[0]
            elif i == len(seg) - 1:
                tv = seg[-1] - seg[-2]
            else:
                tv = seg[i + 1] - seg[i - 1]
            tv.normalize()
            n = Vector((-tv.y, tv.x))
            for (w, h) in ((0.036, th), (-0.036, th), (-0.036, -th), (0.036, -th)):
                v.append((p.x + n.x * h, side * 0.640 + w, p.y + dz + n.y * h))
        faces = []
        for i in range(len(seg) - 1):
            a0 = i * 4
            b0 = (i + 1) * 4
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append([a0 + k, a0 + k2, b0 + k2, b0 + k])
        faces.append([0, 1, 2, 3])
        o = (len(seg) - 1) * 4
        faces.append([o + 3, o + 2, o + 1, o + 0])
        b.add(v, faces, mat=0, smooth=False)
    return b.object(name, coll, [mats['steel']])


def sample_arc(chain, per_seg):
    out = []
    for i in range(len(chain) - 1):
        a, b = chain[i], chain[i + 1]
        for k in range(per_seg):
            out.append(a.lerp(b, k / per_seg))
    out.append(chain[-1])
    return out


def bind_leaf(mesh, arm_ob, chain):
    """Skin the leaf pack to the bone chain, one rigid bone per chain segment.

    Rigid per-segment weighting keeps every joint exactly on the solved chain (a
    linear blend between two bones would lag at the joints, because a joint sits at
    one bone's head and the other bone's tail).  The per-joint kink over the whole
    travel range is well under one degree, so the pack still reads as a smooth
    bending spring.
    """
    xs = [c.x for c in chain]
    nb = len(chain) - 1
    groups = [mesh.vertex_groups.new(name='seg_%02d' % i) for i in range(nb)]
    lo = min(xs[0], xs[-1])
    hi = max(xs[0], xs[-1])
    for v in mesh.data.vertices:
        x = v.co.x
        if x >= hi:
            i = 0 if xs[0] >= xs[-1] else nb - 1
        elif x <= lo:
            i = nb - 1 if xs[0] >= xs[-1] else 0
        else:
            i = 0
            for k in range(nb):
                a, b = xs[k], xs[k + 1]
                if (a >= x >= b) or (a <= x <= b):
                    i = k
                    break
        groups[i].add([v.index], 1.0, 'REPLACE')
    mesh.parent = arm_ob
    m = mesh.modifiers.new('armature', 'ARMATURE')
    m.object = arm_ob
    m.use_deform_preserve_volume = False
    return mesh


# ======================================================================================
# per-frame application (called from the animation baker)
# ======================================================================================
def apply_front(reg, tag, side, wheel_z_local, steer):
    g = reg.require('frontgeo_' + tag)
    st = g.state(wheel_z_local)
    lbj3 = _v3(side, st['lbj'], S.FS_ARM_X)
    lbj3_rest = _v3(side, g.LB0, S.FS_ARM_X)
    ubj3 = _v3(side, st['ubj'], S.FS_ARM_X)
    Rx = Matrix.Rotation(side * st['phi'], 4, 'X')
    M = (Matrix.Translation(lbj3) @ Rx @ Matrix.Translation(-lbj3_rest))
    if abs(steer) > 1e-9:
        axis = (ubj3 - lbj3)
        K = (Matrix.Translation(lbj3)
             @ Matrix.Rotation(steer, 4, axis.normalized())
             @ Matrix.Translation(-lbj3))
        M = K @ M
    ctrl = reg.require('fctrl_' + tag)
    ctrl.location = M @ lbj3_rest
    ctrl.rotation_mode = 'QUATERNION'
    ctrl.rotation_quaternion = M.to_quaternion()
    # lower + upper arms
    la = reg.require('front_lower_arm_' + tag)
    la.rotation_euler = (side * st['theta'], 0, 0)
    ua = reg.require('front_upper_arm_' + tag)
    ua.rotation_euler = (side * wrap_pi(math.atan2(st['ubj'].y - g.PU.y,
                                                   st['ubj'].x - g.PU.x) - g.ang_up0), 0, 0)
    # coil-over: body on the arm, rod reaching the frame tower, spring compresses
    lo = _v3(side, g.coil_low(st['theta']), S.FS_ARM_X)
    up = Vector(reg.require('coil_up_' + tag))
    d = (up - lo)
    L = d.length
    d = d.normalized()
    Lb = reg.require('coil_len_' + tag) * 0.58
    Lr = reg.require('coil_len_' + tag) * 0.52
    Ls = reg.require('coil_len_' + tag) * 0.50
    place_link(reg.require('coil_body_' + tag), lo, lo + d * Lb, Lb, scale_x=False)
    place_link(reg.require('coil_rod_' + tag), up - d * Lr, up, Lr, scale_x=False)
    sp = reg.require('coil_spring_' + tag)
    U.aim(sp, d)
    sp.location = tuple(lo)
    sp.scale = (1.0, 1.0, (L * 0.50) / Ls)
    # steering arm ball, tie rod, brake hose
    ball = M @ g.steer_ball3(side, g.LB0, 0.0)
    inner = Vector(reg.require('tierod_inner_' + tag))
    inner.y += -steer * 0.30
    tl = reg.require('tierod_len_' + tag)
    place_link(reg.require('tierod_' + tag), inner, ball, tl)
    h1, h2 = reg.require('brakehose_' + tag)
    l1, l2 = reg.require('brakehose_len_' + tag)
    mid = Vector((S.FS_ARM_X - 0.20, side * 0.54, 0.560))
    place_link(h1, Vector((S.FS_ARM_X + 0.04, side * 0.50, 0.640)), mid, l1)
    place_link(h2, mid, ball + Vector((0.0, 0.05 * side, -0.03)), l2)
    # CV half shaft: diff output (frame) -> hub (follows the knuckle)
    cv = reg.require('cvshaft_' + tag)
    tip = M @ Vector((S.AXLE_F, side * S.WHEEL_Y, S.RIDE_Z))
    place_link(cv, Vector(reg.require('cv_base_' + tag)), tip,
               reg.require('cv_len_' + tag))
    st['M'] = M
    st['hub'] = tip
    return st


def apply_rear(reg, zL, zR):
    ax = reg.require('axle_ctrl')
    zc = 0.5 * (zL + zR)
    roll = math.asin(max(-0.3, min(0.3, (zL - zR) / S.TRACK)))
    ax.location = (S.AXLE_R, 0.0, zc)
    ax.rotation_mode = 'XYZ'
    ax.rotation_euler = (roll, 0.0, 0.0)
    out = dict(roll=roll, zc=zc, side_z={})
    chain = reg.require('leaf_chain')
    fe, sp, slen = reg.require('leaf_eyes')
    for side, (tag, zw) in ((1, ('L', zL)), (-1, ('R', zR))):
        zclamp = zc + side * 0.640 * math.sin(roll) + AXLE_CLAMP_DZ
        clamp = Vector((S.AXLE_R, zclamp))
        q = leaf_solve(clamp, fe, sp, slen, chain)
        out['side_z'][tag] = zclamp
        # drive the leaf armature bones
        arm = reg.require('leaf_arm_' + tag)
        rest = chain
        # NOTE: Blender's bone local X axis is world -Y for a bone pointing along +X
        # and world +Y for a bone pointing along -X, so the sign of the in-plane bend
        # depends on the bone's own rest direction.  The leaf chain runs along -X.
        sgn = -1.0 if (rest[1].x - rest[0].x) < 0 else 1.0
        for i in range(len(rest) - 1):
            a_r = math.atan2(rest[i + 1].y - rest[i].y, rest[i + 1].x - rest[i].x)
            a_n = math.atan2(q[i + 1].y - q[i].y, q[i + 1].x - q[i].x)
            if i == 0:
                d0 = wrap_pi(a_n - a_r)
            else:
                a_rp = math.atan2(rest[i].y - rest[i - 1].y, rest[i].x - rest[i - 1].x)
                a_np = math.atan2(q[i].y - q[i - 1].y, q[i].x - q[i - 1].x)
                d0 = wrap_pi(wrap_pi(a_n - a_np) - wrap_pi(a_r - a_rp))
            d0 *= sgn
            pb = arm.pose.bones['seg_%02d' % i]
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (d0, 0.0, 0.0)
        # shackle aims at the rear eye
        link_ob = reg.require('shackle_' + tag)
        eye = q[-1]
        d = Vector((eye.x, 0, eye.y)) - Vector((sp.x, 0, sp.y))
        U.aim(link_ob, d)
        L = d.length
        link_ob.scale = (1.0, 1.0, L / max(1e-6, reg.require('shackle_len')))
        link_ob.location = ((sp.x + eye.x) / 2.0, side * 0.640, (sp.y + eye.y) / 2.0)
        # damper: lower mount rides with the axle, rod slides to the frame mount
        axle_M = (Matrix.Translation(Vector((S.AXLE_R, 0.0, zc)))
                  @ Matrix.Rotation(roll, 4, 'X')
                  @ Matrix.Translation(Vector((-S.AXLE_R, 0.0, -S.RIDE_Z))))
        lo_rest = Vector((S.RSHOCK_LOW[0], side * S.RSHOCK_LOW[1], S.RSHOCK_LOW[2]))
        lo = axle_M @ lo_rest
        up = reg.require('shock_up_' + tag)
        L = (up - lo).length
        Lrest = reg.require('shock_len_' + tag)
        place_link(reg.require('shock_body_' + tag), lo, up, L * 0.55)
        place_link(reg.require('shock_rod_' + tag), lo, up, L * 0.52)
        # rear brake hose
        h1, h2 = reg.require('rbrakehose_' + tag)
        m1 = Vector((S.AXLE_R, side * 0.34, 0.60))
        m2 = axle_M @ Vector((S.AXLE_R, side * 0.30, S.RIDE_Z + 0.14))
        place_link(h1, Vector((S.AXLE_R, side * 0.30, 0.66)), m1, 0.18)
        place_link(h2, m1, m2, 0.20)
    out['axle_M'] = Matrix.Translation(Vector((S.AXLE_R, 0.0, zc))) \
        @ Matrix.Rotation(roll, 4, 'X') \
        @ Matrix.Translation(Vector((-S.AXLE_R, 0.0, -S.RIDE_Z)))
    return out
