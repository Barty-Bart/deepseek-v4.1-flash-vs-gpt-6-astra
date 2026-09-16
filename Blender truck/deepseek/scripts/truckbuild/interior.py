"""Cabin interior: seats, dash, console, steering, headliner."""
import math
from . import spec as S
from . import util as U

TAU = math.tau


def build(colls, mats):
    C, M = colls['INTERIOR'], mats
    # carpet over the cab floor
    U.panel('Int_Carpet', [(1.20, 0.882), (1.20, 0.900), (-0.780, 0.900),
                           (-0.780, 0.882)], -0.725, lambda z: 0.725, C,
            M['interior'], bev=0.004)
    # front seats (right-hand drive: driver at -Y)
    for side in (1, -1):
        tag = 'L' if side > 0 else 'R'
        y = side * 0.380
        U.box('Int_SeatBase_%s' % tag, (0.46, 0.44, 0.09), (0.40, y, 0.945), C,
              M['seat'], bev=0.022, segments=2)
        U.box('Int_SeatSide_%s' % tag, (0.42, 0.50, 0.10), (0.38, y, 0.885), C,
              M['interior'], bev=0.020, segments=2)
        U.box('Int_SeatBack_%s' % tag, (0.15, 0.44, 0.56), (0.145, y, 1.180), C,
              M['seat'], bev=0.028, segments=2, rot=(0, -0.19, 0))
        U.box('Int_Headrest_%s' % tag, (0.11, 0.235, 0.15), (0.055, y, 1.462), C,
              M['interior'], bev=0.026, segments=2)
        U.box('Int_SeatRail_%s' % tag, (0.40, 0.05, 0.03), (0.40, y, 0.902), C,
              M['steel'])
        U.box('Int_BeltAnchor_%s' % tag, (0.06, 0.06, 0.16), (0.23, side * 0.70, 1.22),
              C, M['interior'])
    # rear bench
    U.box('Int_RearBase', (0.44, 1.34, 0.10), (-0.44, 0, 0.945), C, M['seat'],
          bev=0.024, segments=2)
    U.box('Int_RearBack', (0.15, 1.34, 0.52), (-0.700, 0, 1.165), C, M['seat'],
          bev=0.028, segments=2, rot=(0, 0.17, 0))
    for side in (1, -1):
        U.box('Int_RearHead_%s' % ('L' if side > 0 else 'R'),
              (0.11, 0.22, 0.14), (-0.775, side * 0.40, 1.400), C, M['interior'],
              bev=0.024, segments=2)
    # dashboard + console
    U.box('Int_Dash', (0.30, 1.42, 0.22), (1.06, 0, 1.130), C, M['interior'],
          bev=0.030, segments=2)
    U.box('Int_DashTop', (0.30, 1.40, 0.06), (1.06, 0, 1.260), C, M['interior'],
          bev=0.018, segments=2)
    U.box('Int_Cluster', (0.07, 0.36, 0.17), (0.900, -0.380, 1.165), C,
          M['interior'], bev=0.012)
    U.box('Int_ClusterFace', (0.02, 0.32, 0.13), (0.868, -0.380, 1.165), C,
          M['lamp_white'])
    U.box('Int_CentreDisplay', (0.05, 0.30, 0.17), (0.900, 0.070, 1.150), C,
          M['interior'], bev=0.010)
    U.box('Int_CentreScreen', (0.02, 0.26, 0.13), (0.872, 0.070, 1.150), C,
          M['lamp_white'])
    U.box('Int_Console', (0.50, 0.24, 0.19), (0.600, 0, 1.010), C, M['interior'],
          bev=0.020)
    U.box('Int_GearLever', (0.05, 0.05, 0.16), (0.640, -0.05, 1.150), C,
          M['steel'], bev=0.010)
    # pedals
    for (xx, yy) in ((0.905, -0.26), (0.905, -0.44), (0.905, -0.62)):
        U.box('Int_Pedal_%d' % int(abs(yy) * 100), (0.05, 0.09, 0.14),
              (xx, yy, 0.965), C, M['steel'], bev=0.008)
    # steering column + wheel
    U.cylinder('Int_SteerColumn', 0.038, 0.30, (0.790, -0.380, 1.180),
               axis='X', coll=C, mat=M['interior'], verts=16)
    w = U.torus('Int_SteerWheel', 0.176, 0.021, (0.665, -0.380, 1.215), C,
                M['interior'], mseg=28, nseg=10, rot=(0, math.pi / 2 - 0.34, 0))
    U.box('Int_SteerHub', (0.05, 0.09, 0.09), (0.672, -0.380, 1.215), C,
          M['interior'], bev=0.010)
    # headliner + rear trim
    U.panel('Int_Headliner', [(0.700, 1.788), (0.700, 1.808), (-0.620, 1.808),
                              (-0.620, 1.788)], -0.775, lambda z: 0.775, C,
            M['interior'], bev=0.004)
    U.panel('Int_ATrim_L', [(0.700, 1.780), (0.700, 1.812), (0.620, 1.812),
                            (0.620, 1.780)], 0.770, lambda z: 0.800, C,
            M['interior'], bev=0.004)
    U.panel('Int_ATrim_R', [(0.700, 1.780), (0.700, 1.812), (0.620, 1.812),
                            (0.620, 1.780)], -0.770, lambda z: -0.800, C,
            M['interior'], bev=0.004)
    U.panel('Int_RearTrim', [(-0.790, 0.900), (-0.790, 1.320), (-0.775, 1.320),
                             (-0.775, 0.900)], -0.700, lambda z: 0.700, C,
            M['interior'], bev=0.004)
    return C
