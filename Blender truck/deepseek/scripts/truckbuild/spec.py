"""All fixed dimensions and design constants for the truck, road and film.

Units: metres.  Scene convention:
    +X = forward (direction of travel)      +Z = up
    +Y = vehicle LEFT                       -Y = vehicle RIGHT
The camera views the truck's RIGHT side (negative Y) throughout the film.
"""

# ---------------------------------------------------------------- vehicle envelope
LENGTH      = 5.35
WIDTH       = 1.92          # over fender flares
HEIGHT      = 1.86
WHEELBASE   = 3.20

AXLE_F      = 1.60          # front axle x
AXLE_R      = -1.60         # rear axle x
TIRE_R      = 0.395         # rolling radius
TIRE_W      = 0.28
RIM_R       = 0.232
RIM_W       = 0.24
TRACK       = 1.58
WHEEL_Y     = TRACK / 2.0   # 0.79
RIDE_Z      = TIRE_R        # wheel centre height at rest

FRONT_FACE  = 2.67
REAR_FACE   = -2.68

# ---------------------------------------------------------------- body key lines
BELTLINE    = 1.30          # window sill
ROOF_Z      = HEIGHT
HOOD_Z      = 1.22
FENDER_TOP  = 1.27
COWL_X      = 1.30          # windscreen base
ROOF_F_X    = 0.70          # roof front edge
ROOF_R_X    = -0.62         # roof rear edge
CAB_REAR    = -0.80
BED_FRONT   = -0.84
BED_FLOOR   = 0.98
BED_RAIL    = 1.32
TAILGATE_X  = -2.55
BODY_BOT    = 0.50          # rocker underside
BED_IN_Y    = 0.66          # bed inner wall
BED_OUT_Y   = 0.96          # bed outer skin
CAB_SKIN_Y  = 0.90          # cab outer skin
CAB_IN_Y    = 0.74          # cab inner shell
TUB_HW      = 0.72          # inner tub half width

# wheel arches (x centre, radius of the opening)
ARCH_F_X, ARCH_F_R = AXLE_F, 0.50
ARCH_R_X, ARCH_R_R = AXLE_R, 0.53

# ---------------------------------------------------------------- frame / chassis
FRAME_Y     = 0.44          # rail centreline
FRAME_HW    = 0.05          # rail half width
FRAME_TOP   = 0.78
FRAME_BOT   = 0.60
FRAME_F_X   = 2.30
FRAME_R_X   = -2.52

FUEL_TANK   = dict(x0=-0.42, x1=-1.34, hw=0.40, z0=0.42, z1=0.66)
EXH_Y       = -0.53
EXH_Z       = 0.44

# ---------------------------------------------------------------- front suspension
FS_LOW_PIVOT   = (0.40, 0.44)     # (|y|, z) of lower arm inner pivot
FS_LOW_BALL    = (0.64, 0.42)     # lower ball joint at rest
FS_UP_PIVOT    = (0.36, 0.82)
FS_UP_BALL     = (0.58, 0.78)
FS_COIL_LOW    = (0.487, 0.4328)  # coil-over lower mount (on lower arm)
FS_COIL_UP     = (0.50, 0.95)     # coil-over upper mount (frame tower)
FS_ARM_X       = AXLE_F           # pivot axis fore/aft position
FS_STEER_ARM   = (1.44, 0.60, 0.50)   # knuckle steering arm ball (x, |y|, z)
FS_STEER_ARM_UV = (0.600, 0.500) # steering arm ball absolute (|y|, z) at rest
FS_STEER_ARM_DX = -0.16          # steering arm ball x offset from the axle plane
LB0_ISH_U      = 0.64

RACK_X      = 1.86
RACK_Z      = 0.54
RACK_HW     = 0.36

FDIFF       = dict(x=1.34, y=-0.26, z=0.50, hw=0.20, r=0.15)

# ---------------------------------------------------------------- rear suspension
LEAF_FRONT_EYE = (-0.86, 0.64, 0.552)
LEAF_REAR_EYE  = (-2.34, 0.64, 0.576)
LEAF_LEN       = None            # computed from the rest arc
LEAF_HW        = 0.035
LEAF_CLAMP_Z   = 0.468           # leaf centreline where it clamps the axle
SHACKLE_PIVOT  = (-2.34, 0.64, 0.700)
SHACKLE_LEN    = 0.126
RSHOCK_LOW     = (-1.44, 0.66, 0.462)
RSHOCK_UP      = (-1.30, 0.44, 0.870)
AXLE_TUBE_R    = 0.062
DIFF_R         = 0.135

# ---------------------------------------------------------------- drivetrain
ENGINE      = dict(x0=1.22, x1=2.14, hw=0.33, z0=0.60, z1=1.06)
TRANS       = dict(x0=0.66, x1=1.22, hw=0.20, z0=0.52, z1=0.88)
TCASE       = dict(x0=0.18, x1=0.66, hw=0.17, z0=0.50, z1=0.80)
TC_REAR_OUT = (0.20, 0.0, 0.60)
TC_FRONT_OUT= (0.60, -0.22, 0.58)
RDIFF_PINION= (-1.30, 0.0, 0.52)

# ---------------------------------------------------------------- film
FPS         = 24
FRAME_START = 1
FRAME_END   = 672           # 28.0 s at 24 fps
SPEED       = 3.0           # m/s
DURATION    = (FRAME_END - FRAME_START + 1) / FPS   # 28.0 s

# ---- film shot boundaries (seconds) ------------------------------------------
SHOT = {
    'side_track':   (0.0, 3.0),
    'arc_to_under': (3.0, 5.8),
    'under_pass':   (5.8, 9.4),
    'chase_under':  (9.4, 11.4),
    'under_hold':   (11.2, 16.2),   # 5.0 s centred undercarriage hold
    'rear_closeup': (16.2, 18.6),
    'drivetrain':   (18.6, 21.4),   # gliding forward under the chassis
    'return_axle':  (21.4, 23.0),
    'axle_wheel':   (23.0, 25.8),   # look along the axle at the inside of the wheel
    'pull_out':     (25.8, 28.0),
}
# frame windows in which the camera must be inside the recessed inspection channel
CHANNEL_WINDOWS = [(6.0, 16.2), (19.2, 26.0)]
ROAD_X0, ROAD_X1 = -30.0, 140.0
RES_X, RES_Y = 1920, 1080

TRAVEL_TOTAL = SPEED * DURATION

# suspension travel the mechanism is validated against
TRAVEL_MIN, TRAVEL_MAX = -0.080, 0.080

COLLECTIONS = ['BODY', 'INTERIOR', 'CHASSIS', 'DRIVETRAIN', 'FRONT_SUSPENSION',
               'REAR_SUSPENSION', 'WHEELS', 'RIG', 'ROAD', 'CAMERAS', 'LIGHTS']


def truck_x(t):
    """World x of the truck origin (centre of wheelbase) at time t seconds."""
    return SPEED * t
