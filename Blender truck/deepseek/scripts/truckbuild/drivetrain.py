"""Engine, transmission, transfer case, prop shafts, front differential and CV axles."""
import math
from mathutils import Vector
from . import spec as S
from . import util as U
from . import suspension as SUS


def build(colls, mats, reg):
    C, M = colls['DRIVETRAIN'], mats
    # ---- engine ----
    U.box('Drive_EngineBlock', (0.90, 0.62, 0.44), (1.68, 0, 0.820), C, M['steel'],
          bev=0.020, segments=2)
    U.box('Drive_ValveCover', (0.64, 0.48, 0.085), (1.72, 0, 1.105), C,
          M['frame'], bev=0.014, segments=2)
    U.box('Drive_IntakePlenum', (0.46, 0.36, 0.10), (1.42, 0, 1.150), C,
          M['frame'], bev=0.016, segments=2)
    U.box('Drive_OilPan', (0.52, 0.38, 0.135), (1.70, 0, 0.545), C, M['steel'],
          bev=0.018, segments=2)
    U.cylinder('Drive_CrankPulley', 0.098, 0.055, (2.165, 0, 0.860), axis='X',
               coll=C, mat=M['steel'], verts=20)
    U.cylinder('Drive_Alternator', 0.075, 0.135, (2.000, -0.415, 0.905), axis='X',
               coll=C, mat=M['steel'], verts=16)
    U.cylinder('Drive_ACCompressor', 0.070, 0.125, (2.000, 0.410, 0.900), axis='X',
               coll=C, mat=M['steel'], verts=16)
    U.box('Drive_Radiator', (0.055, 0.62, 0.36), (2.300, 0, 1.000), C,
          M['aluminium'], bev=0.006)
    U.box('Drive_AirBox', (0.34, 0.30, 0.22), (1.90, 0.36, 1.070), C,
          M['plastic'], bev=0.018, segments=2)
    U.pipe('Drive_AirPipe', [(1.74, 0.34, 1.100), (1.55, 0.22, 1.140),
                             (1.42, 0.04, 1.155)], 0.038, C, M['plastic'], nseg=12)
    # engine mounts
    for side in (1, -1):
        U.box('Drive_EngineMount_%s' % ('L' if side > 0 else 'R'),
              (0.10, 0.13, 0.10), (1.55, side * 0.36, 0.635), C, M['rubber'],
              bev=0.010)
    # ---- transmission + transfer case ----
    secs = []
    for i in range(7):
        t = i / 6.0
        x = 1.20 - 0.48 * t
        r = 0.205 - 0.070 * t
        secs.append((x, [(r * math.cos(a), 0.780 + r * math.sin(a))
                         for a in [math.tau * k / 20 for k in range(20)]]))
    U.loft_x('Drive_Transmission', secs, C, mat=M['aluminium'], bev=0.006)
    U.cylinder('Drive_Bellhousing', 0.215, 0.085, (1.205, 0, 0.800), axis='X',
               coll=C, mat=M['aluminium'], verts=22)
    U.box('Drive_TransMount', (0.10, 0.16, 0.08), (0.80, 0, 0.575), C, M['rubber'],
          bev=0.008)
    U.box('Drive_TransferCase', (0.42, 0.32, 0.30), (0.420, 0, 0.660), C,
          M['aluminium'], bev=0.022, segments=2)
    U.cylinder('Drive_TCaseRearYoke', 0.060, 0.090, (0.205, 0, 0.600), axis='X',
               coll=C, mat=M['steel'], verts=14)
    U.cylinder('Drive_TCaseFrontYoke', 0.055, 0.085, (0.585, -0.235, 0.585),
               axis='X', coll=C, mat=M['steel'], verts=14)
    U.box('Drive_TCaseSkid', (0.40, 0.30, 0.03), (0.420, 0, 0.495), C,
          M['aluminium'], bev=0.006)
    # ---- rear prop shaft (animated: aims from transfer case to rear diff) ----
    base_r = Vector((0.205, 0.0, 0.600))
    pin_loc = Vector((S.AXLE_R + 0.245, -0.02, S.RIDE_Z))   # rest-world pinion centre
    tip_r = Vector((S.AXLE_R + 0.245, -0.02, S.RIDE_Z))
    L_r = (tip_r - base_r).length
    shaft = SUS.link('Drive_RearShaft', L_r, 0.036, C, M['steel'], 14)
    # child of the shaft: position must be expressed in the shaft's local frame
    slip = U.cylinder('Drive_RearShaftSlip', 0.052, 0.16, (0.30, 0.0, 0.0),
                      axis='X', coll=C, mat=M['steel'], verts=14)
    U.parent(slip, shaft)
    reg.put('driveshaft_rear', shaft)
    reg.put('ds_rear_base', base_r)
    reg.put('ds_rear_tip', tip_r)
    reg.put('ds_rear_len', L_r)
    reg.put('ds_rear_pinloc', pin_loc)
    # ---- front prop shaft (front diff is frame mounted: fixed geometry) ----
    # ---- front prop shaft ----
    U.pipe('Drive_FrontShaft', [(0.60, -0.235, 0.575), (1.06, -0.250, 0.512)],
           0.032, C, M['steel'], nseg=12)
    U.cylinder('Drive_FrontShaftBoot', 0.055, 0.11, (0.66, -0.237, 0.570),
               axis='X', coll=C, mat=M['boot'], verts=14)
    # ---- front differential (frame mounted) ----
    U.sphere('Drive_FrontDiffHousing', 0.150, (1.340, -0.260, 0.500), C,
             M['aluminium'], segs=20, rings=12)
    U.cylinder('Drive_FrontDiffCover', 0.140, 0.055, (1.190, -0.260, 0.500),
               axis='X', coll=C, mat=M['aluminium'], verts=20)
    U.cylinder('Drive_FrontDiffPinion', 0.085, 0.145, (1.115, -0.260, 0.500),
               axis='X', coll=C, mat=M['steel'], verts=16)
    U.cylinder('Drive_FrontDiffOutL', 0.062, 0.130, (1.340, -0.085, 0.500),
               axis='Y', coll=C, mat=M['aluminium'], verts=14)
    U.cylinder('Drive_FrontDiffOutR', 0.062, 0.130, (1.340, -0.435, 0.500),
               axis='Y', coll=C, mat=M['aluminium'], verts=14)
    U.box('Drive_FrontDiffBracket', (0.20, 0.30, 0.16), (1.340, -0.260, 0.640),
          C, M['steel'], bev=0.006)
    # ---- CV half shafts (animated: re-aimed from the diff to the steering knuckle) ----
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        y0 = -0.085 if side > 0 else -0.435
        a = Vector((1.340, y0, 0.500))
        b = Vector((S.AXLE_F, side * S.WHEEL_Y, S.RIDE_Z))
        L = (b - a).length
        sh = SUS.link('Drive_CVShaft_%s' % tag, L, 0.028, C, M['steel'], 12)
        # boots are children of the shaft link: local +X runs along the shaft
        for (frac, rr, dep, nm) in ((0.17, 0.068, 0.15, 'In'), (0.84, 0.078, 0.16, 'Out')):
            bt = U.cylinder('Drive_CVBoot%s_%s' % (nm, tag), rr, dep,
                            (L * frac, 0.0, 0.0), axis='X', coll=C,
                            mat=M['boot'], verts=14)
            U.parent(bt, sh)
        reg.put('cvshaft_%s' % tag, sh)
        reg.put('cv_base_%s' % tag, a)
        reg.put('cv_tip_%s' % tag, b)
        reg.put('cv_len_%s' % tag, L)
    return C
