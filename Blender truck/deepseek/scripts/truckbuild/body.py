"""Exterior body: cab, fenders, doors, glazing, bed, tailgate, bumpers, lamps, kit."""
import math
from mathutils import Vector
from . import spec as S
from . import util as U

TAU = math.tau
BEV = 0.006

# ------------------------------------------------------------------ greenhouse lines
PILLAR_A = ((1.005, 1.300), (0.755, 1.840))
PILLAR_B = ((-0.020, 1.300), (-0.062, 1.840))
PILLAR_C = ((-0.782, 1.300), (-0.652, 1.845))
RAIL_Z = 1.812
GLASS_CLEAR = 0.045
GLASS_Z = (1.355, 1.760)


def _lx(line, z):
    (x0, z0), (x1, z1) = line
    return x0 + (x1 - x0) * (z - z0) / (z1 - z0)


def window_quad(pf, pr, z_lo=GLASS_Z[0], z_hi=GLASS_Z[1], clear=GLASS_CLEAR):
    return [( _lx(pf, z_lo) - clear, z_lo), ( _lx(pf, z_hi) - clear, z_hi),
            ( _lx(pr, z_hi) + clear, z_hi), ( _lx(pr, z_lo) + clear, z_lo)]


# ------------------------------------------------------------------ helpers
def arch_edge(xs, xe, zb, cx, r, segs=22):
    pts = []
    if xe > xs:
        pts.append((xs, zb))
        if cx - r > xs:
            pts.append((cx - r, zb))
        pts += U.circle_pts(cx, zb, r, segs, math.pi, 0.0)
        if cx + r < xe:
            pts.append((xe, zb))
    else:
        pts.append((xs, zb))
        if cx + r < xs:
            pts.append((cx + r, zb))
        pts += U.circle_pts(cx, zb, r, segs, 0.0, math.pi)
        if cx - r > xe:
            pts.append((xe, zb))
    return pts


def dedup(pts):
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    return out


def skin(side, y_in, y_out, tumble=0.0, z_ref=S.BELTLINE):
    def fi(z):
        return side * (y_in(z) if callable(y_in) else y_in)
    def fo(z):
        return side * ((y_out(z) if callable(y_out) else y_out) + tumble * (z - z_ref))
    return fi, fo


def crown_slab(name, x0, x1, hw_fn, top_fn, thick, coll, mat, bev=BEV, nseg=10, ny=6):
    sections = []
    for i in range(nseg + 1):
        x = x0 + (x1 - x0) * i / nseg
        hw = hw_fn(x)
        pts = []
        for j in range(ny + 1):
            y = -hw + 2 * hw * j / ny
            pts.append((y, top_fn(x, y)))
        for j in range(ny, -1, -1):
            y = -hw + 2 * hw * j / ny
            pts.append((y, top_fn(x, y) - thick))
        sections.append((x, pts))
    return U.loft_x(name, sections, coll, mat=mat, bev=bev)


# ------------------------------------------------------------------ front end
def build_front(colls, mats):
    C, M = colls['BODY'], mats
    U.panel('Body_FrontBumper', dedup([
        (2.665, 0.575), (2.665, 0.845), (2.430, 0.845), (2.430, 0.575)]),
        -0.945, lambda z: 0.945, C, M['plastic'], bev=0.012)
    U.panel('Body_FrontBumperSkid', dedup([
        (2.640, 0.455), (2.640, 0.585), (2.330, 0.585), (2.300, 0.455)]),
        -0.640, lambda z: 0.640, C, M['aluminium'], bev=0.008)
    U.panel('Body_FrontValance', dedup([
        (2.430, 0.430), (2.430, 0.590), (2.300, 0.590), (2.300, 0.430)]),
        -0.700, lambda z: 0.700, C, M['plastic'], bev=0.008)
    U.panel('Body_GrilleSurround', dedup([
        (2.590, 0.850), (2.590, 1.120), (2.430, 1.120), (2.430, 0.850)]),
        -0.740, lambda z: 0.740, C, M['paint_dark'], bev=0.008)
    U.panel('Body_GrilleBed', dedup([
        (2.520, 0.870), (2.520, 1.105), (2.450, 1.105), (2.450, 0.870)]),
        -0.680, lambda z: 0.680, C, M['paint_dark'], bev=0.004)
    for i in range(5):
        z0 = 0.880 + i * 0.044
        U.panel('Body_GrilleSlat_%d' % i, dedup([
            (2.600, z0), (2.600, z0 + 0.026), (2.460, z0 + 0.026), (2.460, z0)]),
            -0.665, lambda z: 0.665, C, M['chrome'], bev=0.004)
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        U.panel('Body_HeadlampHousing_%s' % tag, dedup([
            (2.630, 0.885), (2.630, 1.070), (2.455, 1.105), (2.455, 0.855)]),
            lambda z, s=side: s * 0.680, lambda z, s=side: s * 0.915, C,
            M['paint_dark'], bev=0.006)
        U.panel('Body_HeadlampLens_%s' % tag, dedup([
            (2.648, 0.900), (2.648, 1.058), (2.500, 1.090), (2.500, 0.872)]),
            lambda z, s=side: s * 0.695, lambda z, s=side: s * 0.898, C,
            M['lens'])
        U.panel('Body_HeadlampLED_%s' % tag, dedup([
            (2.655, 0.975), (2.655, 1.028), (2.520, 1.058), (2.520, 0.982)]),
            lambda z, s=side: s * 0.712, lambda z, s=side: s * 0.872, C,
            M['lamp_warm'])
        U.panel('Body_DRL_%s' % tag, dedup([
            (2.655, 0.900), (2.655, 0.925), (2.520, 0.888), (2.520, 0.872)]),
            lambda z, s=side: s * 0.712, lambda z, s=side: s * 0.872, C,
            M['lamp_white'])
        # bumper side cap
        U.panel('Body_FrontBumperCap_%s' % tag, dedup([
            (2.665, 0.575), (2.665, 0.850), (2.560, 0.845), (2.560, 0.575)]),
            lambda z, s=side: s * 0.930, lambda z, s=side: s * 0.958, C,
            M['plastic'], bev=0.010)
        # tow hook
        U.box('Body_TowHook_%s' % tag, (0.22, 0.075, 0.045),
              (2.44, side * 0.36, 0.500), C, M['steel'], bev=0.010)
    U.panel('Body_RadiatorSupport', dedup([
        (2.430, 0.600), (2.430, 1.165), (2.300, 1.165), (2.300, 0.600)]),
        -0.710, lambda z: 0.710, C, M['paint_dark'], bev=0.005)
    for side in (1, -1):
        U.panel('Body_EngineBaySill_%s' % ('L' if side > 0 else 'R'), dedup([
            (2.430, 1.150), (2.430, 1.240), (1.300, 1.215), (1.300, 1.145)]),
            lambda z, s=side: s * 0.700, lambda z, s=side: s * 0.758, C,
            M['paint_dark'], bev=0.004)

    def hood_top(x, y):
        t = (x - 1.28) / (2.42 - 1.28)
        base = 1.212 - 0.026 * t
        return base + 0.024 * (1.0 - min(1.0, abs(y) / 0.70))
    crown_slab('Body_Hood', 1.30, 2.42, lambda x: 0.706, hood_top, 0.030,
               C, M['paint'], bev=0.008, nseg=8, ny=6)
    U.panel('Body_Cowl', dedup([(1.300, 1.180), (1.300, 1.315), (1.195, 1.325),
                                (1.195, 1.175)]), -0.725, lambda z: 0.725, C,
            M['paint_dark'], bev=0.005)
    U.box('Body_Wiper_L', (0.30, 0.020, 0.012), (1.130, -0.310, 1.335), C,
          M['plastic'], bev=0.003)
    U.box('Body_Wiper_R', (0.30, 0.020, 0.012), (1.120, 0.240, 1.335), C,
          M['plastic'], bev=0.003)


def build_fenders(colls, mats, reg):
    C, M = colls['BODY'], mats
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        outline = dedup([(2.42, 1.265), (0.985, 1.265), (0.985, 0.50)]
                        + arch_edge(0.985, 2.42, 0.50, S.ARCH_F_X, S.ARCH_F_R)[1:]
                        + [(2.42, 0.565)])
        fi, fo = skin(side, 0.745, 0.918, tumble=-0.012)
        U.panel('Body_FrontFender_%s' % tag, outline, fi, fo, C, M['paint'], bev=BEV)
        arc = U.circle_pts(S.ARCH_F_X, 0.50, S.ARCH_F_R - 0.004, 24, math.pi, 0.0)
        U.sweep_ribbon('Body_ArchFlare_F_%s' % tag,
                       [(x, side * 0.926, z) for (x, z) in arc],
                       0.044, 0.030, C, M['plastic_rough'], bev=0.006)
        ww = U.sweep_ribbon('Body_WheelWell_F_%s' % tag,
                            [(x, side * 0.800, z) for (x, z) in
                             U.circle_pts(S.ARCH_F_X, 0.50, S.ARCH_F_R - 0.028, 20,
                                          math.pi, 0.0)],
                            0.155, 0.010, C, M['underbody'], bev=0.004)
        # front wheel-well closing wall (firewall side)
        U.panel('Body_WheelWellWall_FR_%s' % tag, dedup([
            (1.075, 0.50), (1.075, 0.98), (1.115, 1.02), (1.115, 0.50)]),
            lambda z, s=side: s * 0.740, lambda z, s=side: s * 0.920, C,
            M['underbody'], bev=0.004)
        U.panel('Body_WheelWellWall_FF_%s' % tag, dedup([
            (2.130, 0.50), (2.130, 1.02), (2.180, 1.00), (2.180, 0.50)]),
            lambda z, s=side: s * 0.740, lambda z, s=side: s * 0.920, C,
            M['underbody'], bev=0.004)


# ------------------------------------------------------------------ cab
def build_cab(colls, mats):
    C, M = colls['BODY'], mats
    belt, bot = S.BELTLINE, S.BODY_BOT
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        fi, fo = skin(side, 0.745, 0.900, tumble=-0.014)
        U.panel('Body_DoorF_%s' % tag, dedup([
            (0.985, bot), (0.985, belt), (-0.020, belt), (-0.022, bot)]),
            fi, fo, C, M['paint'], bev=BEV)
        U.panel('Body_DoorR_%s' % tag, dedup([
            (-0.062, bot), (-0.062, belt), (-0.782, belt), (-0.782, bot)]),
            fi, fo, C, M['paint'], bev=BEV)
        # door break shadow strip in the front door gap
        U.panel('Body_DoorGap_%s' % tag, dedup([
            (-0.046, bot + 0.02), (-0.046, belt - 0.01),
            (-0.054, belt - 0.01), (-0.054, bot + 0.02)]),
            side * 0.742, side * 0.897, C, M['paint_dark'])
        # pillars + roof rail
        for nm, pth, ht in (('A', PILLAR_A, 0.034), ('B', PILLAR_B, 0.031),
                            ('C', PILLAR_C, 0.035)):
            U.strip('Body_Pillar%s_%s' % (nm, tag), list(pth), ht,
                    side * 0.800, side * 0.880, C, M['paint'], bev=0.004)
        U.strip('Body_RoofRail_%s' % tag, [(PILLAR_A[1][0], RAIL_Z),
                                           (PILLAR_C[1][0], RAIL_Z)],
                0.042, side * 0.800, side * 0.880, C, M['paint'], bev=0.004)
        # glazing
        U.panel('Body_GlassDoorF_%s' % tag, window_quad(PILLAR_A, PILLAR_B),
                side * 0.822, side * 0.836, C, M['glass'])
        U.panel('Body_GlassDoorR_%s' % tag, window_quad(PILLAR_B, PILLAR_C),
                side * 0.822, side * 0.836, C, M['glass'])
        # beltline sill, inner trim, rocker, slider
        U.panel('Body_BeltSill_%s' % tag, dedup([
            (1.00, belt - 0.014), (1.00, belt + 0.010), (-0.79, belt + 0.010),
            (-0.79, belt - 0.014)]),
            side * 0.740, side * 0.902, C, M['paint_dark'], bev=0.003)
        U.panel('Body_DoorInner_%s' % tag, dedup([
            (0.965, bot + 0.02), (0.965, belt), (-0.760, belt), (-0.760, bot + 0.02)]),
            side * 0.700, side * 0.745, C, M['interior'], bev=0.004)
        U.panel('Body_Rocker_%s' % tag, dedup([
            (1.00, bot - 0.035), (1.00, bot + 0.080), (-0.79, bot + 0.080),
            (-0.79, bot - 0.035)]),
            side * 0.700, side * 0.905, C, M['paint_dark'], bev=0.005)
        U.panel('Body_Slider_%s' % tag, dedup([
            (0.86, 0.398), (0.86, 0.452), (-0.72, 0.452), (-0.72, 0.398)]),
            side * 0.902, side * 1.008, C, M['plastic_rough'], bev=0.008)
        for xx in (0.78, -0.62):
            U.box('Body_SliderBracket_%s_%d' % (tag, int(abs(xx) * 100)),
                  (0.05, 0.10, 0.05), (xx, side * 0.865, 0.428), C, M['steel'])
        # mirror
        U.box('Body_MirrorArm_%s' % tag, (0.055, 0.115, 0.035),
              (1.020, side * 0.950, 1.442), C, M['plastic'], bev=0.006,
              rot=(0, 0, side * 0.25))
        U.box('Body_Mirror_%s' % tag, (0.078, 0.080, 0.160),
              (0.982, side * 1.062, 1.462), C, M['paint'], bev=0.014)
        U.panel('Body_MirrorGlass_%s' % tag, dedup([
            (0.985, 1.398), (1.000, 1.532), (0.962, 1.532), (0.947, 1.398)]),
            side * 1.036, side * 1.044, C, M['chrome'])
        for xx in (0.24, -0.42):
            U.box('Body_Handle_%s_%d' % (tag, int(abs(xx) * 100)),
                  (0.145, 0.030, 0.032), (xx, side * 0.910, 1.185), C,
                  M['chrome'], bev=0.008)
    # floor, firewall, rear panel, rear header/pillars
    U.panel('Cab_Floor', dedup([(1.280, 0.845), (1.280, 0.880), (-0.790, 0.880),
                                (-0.790, 0.845)]), -0.725, lambda z: 0.725, C,
            M['underbody'], bev=0.006)
    U.panel('Cab_Firewall', dedup([(1.230, 0.860), (1.230, 1.220), (1.300, 1.260),
                                   (1.300, 0.840)]), -0.740, lambda z: 0.740, C,
            M['underbody'], bev=0.006)
    U.panel('Cab_RearPanel', dedup([(-0.782, 0.500), (-0.782, belt), (-0.848, belt),
                                    (-0.848, 0.500)]), -0.730, lambda z: 0.730, C,
            M['paint'], bev=0.006)
    U.panel('Cab_RearHeader', dedup([(-0.780, 1.790), (-0.780, 1.855),
                                     (-0.848, 1.855), (-0.848, 1.790)]),
            -0.730, lambda z: 0.730, C, M['paint'], bev=0.004)
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        U.panel('Cab_RearPillar_%s' % tag, dedup([
            (-0.780, 1.300), (-0.780, 1.800), (-0.848, 1.800), (-0.848, 1.300)]),
            lambda z, s=side: s * 0.616, lambda z, s=side: s * 0.730, C,
            M['paint'], bev=0.004)
    U.panel('Body_GlassRear', dedup([
        (-0.796, 1.345), (-0.796, 1.765), (-0.828, 1.765), (-0.828, 1.345)]),
        -0.605, lambda z: 0.605, C, M['glass'], bev=0.002)
    # roof
    def roof_top(x, y):
        t = abs(y) / 0.80
        return S.ROOF_Z - 0.012 * t * t
    crown_slab('Body_Roof', -0.62, 0.70, lambda x: 0.802, roof_top, 0.035,
               C, M['paint'], bev=0.008, nseg=8, ny=6)
    U.panel('Body_RoofFront', dedup([(0.695, 1.790), (0.695, 1.886),
                                     (0.815, 1.886), (0.815, 1.790)]),
        -0.805, lambda z: 0.805, C, M['paint'], bev=0.005)
    U.panel('Body_RoofBack', dedup([(-0.620, 1.855), (-0.680, 1.800), (-0.800, 1.788),
                                    (-0.800, 1.855)]), -0.805, lambda z: 0.805, C,
            M['paint'], bev=0.005)
    # windscreen: curved + solidified
    secs = []
    for i in range(9):
        t = i / 8.0
        z = 1.315 + (1.848 - 1.315) * t
        x = 1.305 + (0.735 - 1.305) * t
        hw = 0.762 - 0.055 * t
        pts = []
        for j in range(9):
            u = -1.0 + 2.0 * j / 8.0
            pts.append((x - 0.055 * (1 - u * u), hw * u, z))
        secs.append(pts)
    ws = U.loft_pts('Body_Windshield', secs, C, mat=M['glass'], closed_section=False,
                    cap_start=False, cap_end=False)
    U.solidify(ws, 0.006, 0.0)


# ------------------------------------------------------------------ bed
def build_bed(colls, mats):
    C, M = colls['BODY'], mats
    xf, xr = S.BED_FRONT, S.TAILGATE_X
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        outline = dedup([(xf, S.BED_RAIL), (xr + 0.03, S.BED_RAIL),
                         (xr + 0.03, 0.520)]
                        + arch_edge(xr + 0.03, xf, 0.520, S.ARCH_R_X, S.ARCH_R_R)[1:]
                        + [(xf, 0.600)])
        U.panel('Body_BedSide_%s' % tag, outline,
                side * 0.660, side * 0.958, C, M['paint'], bev=BEV)
        U.panel('Body_BedLinerSide_%s' % tag, dedup([
            (xf + 0.02, 0.990), (xf + 0.02, S.BED_RAIL - 0.020),
            (xr + 0.05, S.BED_RAIL - 0.020), (xr + 0.05, 0.990)]),
            side * 0.644, side * 0.664, C, M['bedliner'], bev=0.004)
        U.panel('Body_BedRail_%s' % tag, dedup([
            (xf, S.BED_RAIL - 0.030), (xf, S.BED_RAIL + 0.010),
            (xr + 0.02, S.BED_RAIL + 0.010), (xr + 0.02, S.BED_RAIL - 0.030)]),
            side * 0.644, side * 0.962, C, M['paint'], bev=0.006)
        arc = U.circle_pts(S.ARCH_R_X, 0.520, S.ARCH_R_R - 0.004, 24, math.pi, 0.0)
        U.sweep_ribbon('Body_ArchFlare_R_%s' % tag,
                       [(x, side * 0.962, z) for (x, z) in arc],
                       0.042, 0.028, C, M['plastic_rough'], bev=0.006)
        U.sweep_ribbon('Body_WheelWell_R_%s' % tag,
                       [(x, side * 0.810, z) for (x, z) in
                        U.circle_pts(S.ARCH_R_X, 0.520, S.ARCH_R_R - 0.028, 20,
                                     math.pi, 0.0)],
                       0.160, 0.010, C, M['underbody'], bev=0.004)
        for (a, b, nm) in ((xf - 0.02, S.ARCH_R_X - S.ARCH_R_R, 'F'),
                           (S.ARCH_R_X + S.ARCH_R_R, xr + 0.03, 'R')):
            U.panel('Body_BedUnder_%s%s' % (nm, tag), dedup([
                (a, 0.860), (a, 0.930), (b, 0.930), (b, 0.860)]),
                side * 0.660, side * 0.905, C, M['underbody'], bev=0.004)
        if side > 0:
            U.cylinder('Body_FuelFiller', 0.055, 0.032,
                       (xf - 0.34, side * 0.960, 1.145), axis='Y', coll=C,
                       mat=M['paint_dark'], verts=16)
    U.panel('Body_BedFloor', dedup([
        (-0.855, 0.955), (-0.855, 0.995), (-2.545, 0.995), (-2.545, 0.955)]),
        -0.652, lambda z: 0.652, C, M['bedliner'], bev=0.006)
    U.panel('Body_BedFrontPanel', dedup([
        (-0.845, 0.980), (-0.845, S.BED_RAIL), (-0.905, S.BED_RAIL),
        (-0.905, 0.980)]), -0.648, lambda z: 0.648, C, M['bedliner'], bev=0.006)
    U.panel('Body_Tailgate', dedup([
        (-2.545, 0.980), (-2.545, 1.300), (-2.628, 1.300), (-2.628, 0.980)]),
        -0.938, lambda z: 0.938, C, M['paint'], bev=0.010)
    U.panel('Body_TailgateCap', dedup([
        (-2.545, 1.278), (-2.545, 1.320), (-2.640, 1.320), (-2.640, 1.278)]),
        -0.938, lambda z: 0.938, C, M['paint_dark'], bev=0.005)
    U.panel('Body_TailgateHandle', dedup([
        (-2.634, 1.060), (-2.634, 1.105), (-2.664, 1.105), (-2.664, 1.060)]),
        -0.300, lambda z: 0.300, C, M['chrome'], bev=0.004)
    U.panel('Body_RearBumper', dedup([
        (-2.600, 0.540), (-2.600, 0.790), (-2.700, 0.790), (-2.700, 0.540)]),
        -0.948, lambda z: 0.948, C, M['plastic'], bev=0.012)
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        U.panel('Body_RearBumperStep_%s' % tag, dedup([
            (-2.650, 0.545), (-2.650, 0.850), (-2.560, 0.850), (-2.560, 0.545)]),
            lambda z, s=side: s * 0.850, lambda z, s=side: s * 0.958, C,
            M['plastic_rough'], bev=0.010)
        U.panel('Body_TailLampHousing_%s' % tag, dedup([
            (-2.632, 0.955), (-2.632, 1.290), (-2.700, 1.240), (-2.700, 0.995)]),
            lambda z, s=side: s * 0.622, lambda z, s=side: s * 0.818, C,
            M['paint_dark'], bev=0.006)
        U.panel('Body_TailLampLens_%s' % tag, dedup([
            (-2.664, 0.972), (-2.664, 1.276), (-2.712, 1.230), (-2.712, 1.008)]),
            lambda z, s=side: s * 0.640, lambda z, s=side: s * 0.804, C,
            M['lamp_tail'])
        U.panel('Body_ReverseLamp_%s' % tag, dedup([
            (-2.664, 0.978), (-2.664, 1.032), (-2.712, 1.046), (-2.712, 1.014)]),
            lambda z, s=side: s * 0.652, lambda z, s=side: s * 0.792, C,
            M['lamp_white'])
        U.panel('Body_MudFlap_%s' % tag, dedup([
            (-2.150, 0.185), (-2.150, 0.560), (-2.118, 0.560), (-2.118, 0.185)]),
            lambda z, s=side: s * 0.700, lambda z, s=side: s * 0.930, C,
            M['plastic_rough'], bev=0.004)
    U.panel('Body_LicensePlate', dedup([
        (-2.702, 0.870), (-2.702, 1.030), (-2.708, 1.030), (-2.708, 0.870)]),
        -0.200, lambda z: 0.200, C, M['marking'])
    U.box('Body_HitchReceiver', (0.42, 0.075, 0.075), (-2.500, 0, 0.478), C,
          M['steel'], bev=0.006)
    U.box('Body_HitchBar', (0.075, 1.10, 0.075), (-2.340, 0, 0.478), C,
          M['steel'], bev=0.006)
    U.box('Body_HitchBall', (0.10, 0.070, 0.10), (-2.700, 0, 0.540), C,
          M['steel'], bev=0.010)


# ------------------------------------------------------------------ expedition kit
def build_expedition(colls, mats):
    C, M = colls['BODY'], mats
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        U.panel('Body_RackRail_%s' % tag, dedup([
            (-0.900, 1.372), (-0.900, 1.408), (-2.420, 1.408), (-2.420, 1.372)]),
            side * 0.720, side * 0.782, C, M['steel'], bev=0.005)
    for i, xx in enumerate((-0.95, -1.44, -1.93, -2.42)):
        U.box('Body_RackSlat_%d' % i, (0.045, 1.46, 0.024), (xx, 0, 1.396), C,
              M['steel'], bev=0.004)
        for side in (1, -1):
            U.box('Body_RackLeg_%d_%s' % (i, 'L' if side > 0 else 'R'),
                  (0.05, 0.05, 0.105), (xx, side * 0.752, 1.325), C, M['steel'],
                  bev=0.004)
    U.box('Body_RackLightBar', (0.075, 1.22, 0.070), (-0.900, 0, 1.452), C,
          M['paint_dark'], bev=0.010)
    for k in range(6):
        U.cylinder('Body_RackLight_%d' % k, 0.042, 0.020,
                   (-0.948, -0.45 + k * 0.18, 1.452), axis='X', coll=C,
                   mat=M['lamp_white'], verts=16)
    U.box('Body_RackCase', (1.06, 1.22, 0.165), (-2.060, 0, 1.492), C,
          M['paint_dark'], bev=0.020)
    # snorkel up the right A pillar
    U.sweep_ribbon('Body_Snorkel', [(1.330, -0.952, 1.120), (1.305, -0.952, 1.430),
                                    (1.230, -0.952, 1.700), (1.130, -0.952, 1.870)],
                   0.050, 0.050, C, M['plastic_rough'], bev=0.012)
    U.box('Body_SnorkelHead', (0.22, 0.14, 0.15), (1.070, -0.952, 1.905), C,
          M['plastic_rough'], bev=0.020)
