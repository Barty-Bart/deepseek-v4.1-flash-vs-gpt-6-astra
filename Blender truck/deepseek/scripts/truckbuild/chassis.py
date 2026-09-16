"""Body-on-frame chassis: rails, crossmembers, skid plates, tank, exhaust, rack."""
import math
from . import spec as S
from . import util as U


def build(colls, mats, reg):
    C, M = colls['CHASSIS'], mats
    # ---- twin frame rails (straight, documented simplification) ----
    length = S.FRAME_F_X - S.FRAME_R_X
    cx = (S.FRAME_F_X + S.FRAME_R_X) / 2.0
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        U.box('Chassis_Rail_%s' % tag, (length, S.FRAME_HW * 2, 0.18),
              (cx, side * S.FRAME_Y, 0.69), C, M['frame'], bev=0.008)
        # rail flange lips for mechanical read
        U.box('Chassis_RailLip_%s' % tag, (length, S.FRAME_HW * 2 + 0.03, 0.028),
              (cx, side * S.FRAME_Y, 0.786), C, M['frame'], bev=0.004)
    # ---- crossmembers ----
    for i, xx in enumerate((2.22, 1.05, 0.35, -0.65, -1.85, -2.44)):
        h = 0.16 if xx < 1.0 else 0.20
        U.box('Chassis_Crossmember_%d' % i, (0.12, 0.86, h), (xx, 0, 0.69), C,
              M['frame'], bev=0.008)
    # transmission crossmember
    U.box('Chassis_TransCrossmember', (0.10, 0.70, 0.10), (0.80, 0, 0.52), C,
          M['frame'], bev=0.006)
    U.box('Chassis_TransMount', (0.10, 0.16, 0.10), (0.80, 0, 0.58), C,
          M['frame'], bev=0.006)
    # ---- body mounts ----
    for i, xx in enumerate((2.18, 0.95, -0.10, -1.72)):
        for side in (1, -1):
            U.cylinder('Chassis_BodyMount_%d_%s' % (i, 'L' if side > 0 else 'R'),
                       0.038, 0.075, (xx, side * S.FRAME_Y, 0.815), coll=C,
                       mat=M['rubber'], verts=14)
    # ---- skid plates (partial: drivetrain stays visible) ----
    U.panel('Chassis_SkidFront', [(1.36, 0.505), (1.36, 0.535), (2.22, 0.585),
                                  (2.22, 0.555)], -0.340, lambda z: 0.340, C,
            M['aluminium'], bev=0.008)
    U.panel('Chassis_SkidTcase', [(0.02, 0.395), (0.02, 0.425), (0.72, 0.455),
                                  (0.72, 0.425)], -0.310, lambda z: 0.310, C,
            M['aluminium'], bev=0.008)
    for xx in (1.42, 2.16, 0.08, 0.66):
        for side in (1, -1):
            U.box('Chassis_SkidLeg_%d_%s' % (int(xx * 100), 'L' if side > 0 else 'R'),
                  (0.05, 0.06, 0.07), (xx, side * 0.320, 0.560), C, M['steel'],
                  bev=0.004)
    # ---- fuel tank, straps, heat shield ----
    t = S.FUEL_TANK
    tx = (t['x0'] + t['x1']) / 2.0
    tl = abs(t['x1'] - t['x0'])
    U.box('Chassis_FuelTank', (tl, t['hw'] * 2, t['z1'] - t['z0']),
          (tx, 0, (t['z0'] + t['z1']) / 2.0), C, M['tank'], bev=0.030, segments=3)
    for xx in (t['x0'] - 0.16, t['x1'] + 0.16):
        U.box('Chassis_TankStrap_%d' % int(abs(xx) * 100), (0.04, t['hw'] * 2 + 0.02, 0.26),
              (xx, 0, 0.545), C, M['steel'], bev=0.004)
    U.panel('Chassis_TankShield', [(-0.45, 0.400), (-0.45, 0.600), (-1.38, 0.600),
                                   (-1.38, 0.400)], -0.470, lambda z: -0.445, C,
            M['heatshield'], bev=0.004)
    # ---- exhaust: downpipe -> cat -> pipe -> over axle -> muffler -> tailpipe ----
    U.pipe('Exhaust_Downpipe', [(1.62, -0.24, 0.62), (1.34, -0.30, 0.50),
                                (1.16, -0.38, 0.45)], 0.045, C, M['exhaust'], nseg=14)
    U.cylinder('Exhaust_Catalyst', 0.078, 0.34, (0.98, -0.43, 0.445), axis='X',
               coll=C, mat=M['exhaust'], verts=18)
    U.pipe('Exhaust_PipeFront', [(0.80, -0.46, 0.44), (0.30, -0.53, 0.44),
                                 (-0.50, -0.53, 0.44)], 0.040, C, M['exhaust'], nseg=14)
    U.pipe('Exhaust_PipeRear', [(-0.44, -0.53, 0.44), (-1.25, -0.53, 0.45),
                                (-1.62, -0.50, 0.60), (-1.95, -0.42, 0.575)],
           0.040, C, M['exhaust'], nseg=14)
    U.cylinder('Exhaust_Muffler', 0.105, 0.46, (-2.16, -0.31, 0.525), axis='X',
               coll=C, mat=M['exhaust'], verts=20)
    U.pipe('Exhaust_Tailpipe', [(-2.38, -0.31, 0.525), (-2.55, -0.42, 0.50),
                                (-2.74, -0.50, 0.462)], 0.040, C, M['exhaust'], nseg=14)
    for xx in (0.20, -0.90, -1.70):
        U.box('Exhaust_Hanger_%d' % int(abs(xx) * 100), (0.03, 0.03, 0.10),
              (xx, -0.50, 0.50), C, M['steel'], bev=0.004)
    # heat shields above the pipe near the tank and under the cab
    U.panel('Chassis_HeatShieldA', [(-0.30, 0.560), (-0.30, 0.575), (-1.40, 0.575),
                                    (-1.40, 0.560)], -0.600, lambda z: -0.420, C,
            M['heatshield'], bev=0.003)
    U.panel('Chassis_HeatShieldB', [(0.10, 0.548), (0.10, 0.563), (-0.30, 0.563),
                                    (-0.30, 0.548)], -0.580, lambda z: -0.440, C,
            M['heatshield'], bev=0.003)
    # ---- steering rack ----
    U.cylinder('Chassis_SteerRack', 0.048, 0.74, (S.RACK_X, 0, S.RACK_Z),
               axis='Y', coll=C, mat=M['steel'], verts=18)
    for side in (1, -1):
        U.cylinder('Chassis_RackBoot_%s' % ('L' if side > 0 else 'R'), 0.046, 0.16,
                   (S.RACK_X, side * 0.40, S.RACK_Z), axis='Y', coll=C,
                   mat=M['boot'], verts=14)
    U.box('Chassis_RackMount_L', (0.10, 0.10, 0.12), (S.RACK_X, 0.36, 0.60), C,
          M['steel'], bev=0.005)
    U.box('Chassis_RackMount_R', (0.10, 0.10, 0.12), (S.RACK_X, -0.36, 0.60), C,
          M['steel'], bev=0.005)
    U.cylinder('Chassis_SteerColumn', 0.030, 0.34, (1.98, -0.30, 0.86),
               axis='X', coll=C, mat=M['steel'], verts=12, rot=(0, -0.35, 0))
    # ---- brake / fuel lines along the frame ----
    U.pipe('Chassis_FuelLine', [(1.60, -0.34, 0.585), (0.60, -0.36, 0.585),
                                (-0.40, -0.36, 0.585), (-1.20, -0.34, 0.60)],
           0.010, C, M['steel'], nseg=8)
    U.pipe('Chassis_BrakeLineF', [(1.80, 0.36, 0.545), (1.30, 0.40, 0.545),
                                  (0.30, 0.38, 0.555), (-1.20, 0.38, 0.560),
                                  (-2.00, 0.40, 0.560)], 0.008, C, M['steel'], nseg=8)
    # ---- underbody braces / floor pan ribs ----
    for xx in (1.60, 1.00, 0.40, -0.20):
        U.box('Chassis_FloorRib_%d' % int(abs(xx) * 100), (0.06, 1.30, 0.05),
              (xx, 0, 0.840), C, M['frame'], bev=0.004)
    return C
