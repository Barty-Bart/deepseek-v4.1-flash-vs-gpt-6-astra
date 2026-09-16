import bpy, bmesh, math, json, time
from mathutils import Vector, Matrix, Quaternion
from math import sin, cos, pi, sqrt, atan2
base_hash='077f035f0202dffc63b8c8433709b1fabbf69f36698949d46cf4ae2929a68ffd'
rig_only=False
if bpy.context.scene.world is None: bpy.context.scene.world=bpy.data.worlds.new("Kestrel World")

"""Original procedural pickup. Run in Blender; never invokes rendering."""
START = time.perf_counter()
R = 0.405
TRACK = 1.66
AXLES = {'F': 1.6, 'R': -1.6}
SIDES = {'L': TRACK / 2, 'R': -TRACK / 2}
COLLECTIONS = 'BODY INTERIOR CHASSIS DRIVETRAIN FRONT_SUSPENSION REAR_SUSPENSION WHEELS RIG ROAD CAMERAS LIGHTS'.split()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection':
        bpy.data.collections.remove(c)
base = bpy.data.collections.get('Collection')
if base:
    bpy.data.collections.remove(base)
C = {n: bpy.data.collections.new(n) for n in COLLECTIONS}
for c in C.values():
    bpy.context.scene.collection.children.link(c)
scene = bpy.context.scene
scene.name = 'KESTREL | 4x4 mechanical proving ground'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'
scene.render.engine = 'CYCLES' if False else 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 240
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = '//renders/kestrel_'
scene.render.film_transparent = False
if hasattr(scene.render, 'use_motion_blur'):
    scene.render.use_motion_blur = False
if hasattr(scene, 'eevee'):
    for k, v in [('taa_render_samples', 64), ('taa_samples', 32), ('use_gtao', True)]:
        if hasattr(scene.eevee, k):
            setattr(scene.eevee, k, v)
    scene.eevee.use_raytracing = True
    scene.eevee.ray_tracing_options.screen_trace_quality = 0.5
    scene.eevee.ray_tracing_options.screen_trace_thickness = 0.03
scene.world.color = (0.22, 0.24, 0.27)
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.48, 0.57, 0.69, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
scene.view_settings.view_transform = 'AgX'
scene.render.fps_base = 1
M = {}

def mat(name, color, metal=0, rough=0.45):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    M[name] = m
    return m
paint = mat('Paint | satin forest green', (0.075, 0.155, 0.107), 0.62, 0.29)
black = mat('Trim | charcoal polymer', (0.018, 0.026, 0.028), 0.12, 0.48)
steel = mat('Frame | graphite powdercoat', (0.055, 0.066, 0.072), 0.68, 0.34)
alloy = mat('Metal | brushed aluminium', (0.43, 0.48, 0.5), 0.82, 0.28)
chrome = mat('Metal | polished damper shafts', (0.62, 0.67, 0.7), 0.92, 0.19)
rubber = mat('Rubber | restrained road wear', (0.024, 0.029, 0.027), 0, 0.77)
red = mat('Lens | garnet red', (0.33, 0.018, 0.009), 0.12, 0.24)
amber = mat('Lens | warm amber', (0.7, 0.23, 0.035), 0.22, 0.22)
leafmat = mat('Leaf springs | manganese steel', (0.13, 0.16, 0.17), 0.78, 0.39)
brake = mat('Caliper | oxblood coating', (0.28, 0.041, 0.027), 0.58, 0.35)
roadmat = mat('Road | fine aggregate concrete', (0.24, 0.27, 0.29), 0, 0.86)
lightmat = mat('LED | warm white', (0.95, 0.76, 0.45), 0.2, 0.22)
p = lightmat.node_tree.nodes['Principled BSDF']
p.inputs['Emission Color'].default_value = (1, 0.77, 0.4, 1)
p.inputs['Emission Strength'].default_value = 3
redlight = mat('LED | rear running light', (0.45, 0.013, 0.006), 0.15, 0.2)
p = redlight.node_tree.nodes['Principled BSDF']
p.inputs['Emission Color'].default_value = (1, 0.02, 0.007, 1)
p.inputs['Emission Strength'].default_value = 1.5
glass = mat('Glass | laminated smoke', (0.12, 0.21, 0.24), 0.08, 0.17)
p = glass.node_tree.nodes['Principled BSDF']
p.inputs['Transmission Weight'].default_value = 0.72
p.inputs['IOR'].default_value = 1.46
seatmat = mat('Interior | graphite fabric', (0.055, 0.066, 0.06), 0, 0.88)
accent = mat('Details | warm nickel', (0.52, 0.43, 0.28), 0.76, 0.33)
for m, scale, strength in [(rubber, 125, 0.11), (roadmat, 35, 0.19), (steel, 95, 0.07), (seatmat, 165, 0.1)]:
    nt = m.node_tree
    tex = nt.nodes.new('ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = scale
    tex.inputs['Detail'].default_value = 2
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = strength
    bump.inputs['Distance'].default_value = 0.009
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], nt.nodes['Principled BSDF'].inputs['Normal'])

def link(o, col, ma=None, parent=None):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    C[col].objects.link(o)
    if ma and o.type in {'MESH', 'CURVE'}:
        o.data.materials.append(ma)
    if parent:
        o.parent = parent
    return o

def mesh(name, verts, faces, col, ma=None, parent=None, bevel=0):
    me = bpy.data.meshes.new(name + ' mesh')
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    C[col].objects.link(o)
    if ma:
        me.materials.append(ma)
    if parent:
        o.parent = parent
    if bevel:
        b = o.modifiers.new('Small manufactured edge radii', 'BEVEL')
        b.width = bevel
        b.segments = 3
        b = o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o

def box(name, loc, size, col, ma, parent=None, bev=0.014):
    x, y, z = [v / 2 for v in size]
    vs = [(-x, -y, -z), (-x, -y, z), (-x, y, -z), (-x, y, z), (x, -y, -z), (x, -y, z), (x, y, -z), (x, y, z)]
    fs = [(0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4), (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6)]
    o = mesh(name, vs, fs, col, ma, parent, min(bev, min(size) * 0.25))
    o.location = loc
    return o

def uv(name, loc, scale, col, ma, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.scale = scale
    link(o, col, ma, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    return o

def cyl(name, a, b, r, col, ma, parent=None, n=20, r2=None):
    a, b = (Vector(a), Vector(b))
    d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=r, radius2=r if r2 is None else r2, depth=d.length, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name
    link(o, col, ma, parent)
    o.location = (a + b) * 0.5
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    be = o.modifiers.new('Machined edges', 'BEVEL')
    be.width = min(0.004, r * 0.15)
    be.segments = 2
    return o

def tube(name, pts, r, col, ma, parent=None, cyclic=False):
    cu = bpy.data.curves.new(name + ' path', 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = 12
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for p, co in zip(sp.points, pts):
        p.co = (*co, 1)
    sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, cu)
    C[col].objects.link(o)
    cu.materials.append(ma)
    if parent:
        o.parent = parent
    return o

def empty(name, loc=(0, 0, 0), parent=None, col='RIG', size=0.13):
    o = bpy.data.objects.new(name, None)
    C[col].objects.link(o)
    o.location = loc
    o.empty_display_type = 'PLAIN_AXES'
    o.empty_display_size = size
    if parent:
        o.parent = parent
    return o

def prop(o, key, val, lo, hi, desc):
    o[key] = float(val)
    o.id_properties_ui(key).update(min=lo, max=hi, soft_min=lo, soft_max=hi, description=desc)

def driver(o, path, index, expr, variables):
    fc = o.driver_add(path, index) if index is not None else o.driver_add(path)
    d = fc.driver
    d.type = 'SCRIPTED'
    d.expression = expr
    for name, target, dp in variables:
        v = d.variables.new()
        v.name = name
        v.type = 'SINGLE_PROP'
        v.targets[0].id = target
        v.targets[0].data_path = dp
    return fc

def pvar(name, o, key):
    return (name, o, '["' + key + '"]')

def dynamic_rod(name, a, b, r, col, ma, length=None):
    n = 16
    vs = []
    for z in (0, 1):
        for i in range(n):
            vs.append((r * cos(i * 2 * pi / n), r * sin(i * 2 * pi / n), z))
    fs = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    o = mesh(name, vs, fs, col, ma)
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    co = o.constraints.new('COPY_LOCATION')
    co.target = a
    co = o.constraints.new('DAMPED_TRACK')
    co.target = b
    co.track_axis = 'TRACK_Z'
    if length is None:
        fc = o.driver_add('scale', 2)
        d = fc.driver
        d.expression = 'distance'
        v = d.variables.new()
        v.name = 'distance'
        v.type = 'LOC_DIFF'
        v.targets[0].id = a
        v.targets[1].id = b
    else:
        o.scale.z = length
    o['endpoint_a'] = a.name
    o['endpoint_b'] = b.name
    return o

def keyprop(o, k, v, f):
    o[k] = v
    o.keyframe_insert(data_path='["' + k + '"]', frame=f)
root = empty('CTRL_VEHICLE_TRAVEL', size=0.6)
prop(root, 'travel_m', 0, -20, 80, 'Forward travel in meters. Wheel rotation is distance / rolling radius.')
prop(root, 'steering_deg', 0, -25, 25, 'Common front steering angle, degrees; animation holds nearly straight.')
prop(root, 'body_heave_m', 0, -0.08, 0.08, 'Smoothed sprung-body vertical displacement in meters.')
prop(root, 'body_pitch_deg', 0, -5, 5, 'Sprung body pitch about local Y.')
prop(root, 'body_roll_deg', 0, -5, 5, 'Sprung body roll about local X.')
prop(root, 'wheel_rotation_offset_deg', 0, -360, 360, 'Offset for wheel spin; travel remains the rotation source.')
root['rolling_radius_m'] = R
root['wheelbase_m'] = 3.2
root['track_m'] = TRACK
root['animation_note'] = 'All controls are keyed 1–240. Edit keys or clear selected property animation to pose. Forward +X, right -Y.'
driver(root, 'location', 0, 'distance', [pvar('distance', root, 'travel_m')])
body = empty('CTRL_BODY_HEAVE_PITCH_ROLL', parent=root, size=0.4)
driver(body, 'location', 2, 'h', [pvar('h', root, 'body_heave_m')])
driver(body, 'rotation_euler', 1, 'p*pi/180', [pvar('p', root, 'body_pitch_deg')])
driver(body, 'rotation_euler', 0, 'r*pi/180', [pvar('r', root, 'body_roll_deg')])
controls = {}
hubs = {}
spins = {}
shocks = {}
leafs = {}
arm_rods = []
for a, x in AXLES.items():
    for s, y in SIDES.items():
        code = a + s
        c = empty('CTRL_SUSPENSION_' + code, parent=root)
        prop(c, 'travel_m', 0, -0.08, 0.08, 'Wheel displacement relative to heaved chassis; positive is compression.')
        controls[code] = c
rear = empty('RIG_REAR_SOLID_AXLE', (-1.6, 0, R), root)
driver(rear, 'location', 2, f'{R}+h+(l+r)/2', [pvar('h', root, 'body_heave_m'), pvar('l', controls['RL'], 'travel_m'), pvar('r', controls['RR'], 'travel_m')])
driver(rear, 'rotation_euler', 0, f'atan2(l-r,{TRACK})', [pvar('l', controls['RL'], 'travel_m'), pvar('r', controls['RR'], 'travel_m')])
for code, c in controls.items():
    a, s = code
    x = AXLES[a]
    y = SIDES[s]
    if a == 'F':
        hub = empty('RIG_HUB_' + code, (x, y, R), root)
        driver(hub, 'location', 2, f'{R}+h+q', [pvar('h', root, 'body_heave_m'), pvar('q', c, 'travel_m')])
        driver(hub, 'rotation_euler', 2, 's*pi/180', [pvar('s', root, 'steering_deg')])
    else:
        hub = empty('RIG_HUB_' + code, (0, y, 0), rear)
    hubs[code] = hub
    spin = empty('CTRL_WHEEL_ROTATION_' + code, parent=hub)
    driver(spin, 'rotation_euler', 1, f'd/{R}+o*pi/180', [pvar('d', root, 'travel_m'), pvar('o', root, 'wheel_rotation_offset_deg')])
    spins[code] = spin
BUMPS = [(2.7, 0.048, 1.6), (6.4, 0.06, 1.9), (10.8, 0.047, 1.6), (14.7, 0.055, 2.0), (18.9, 0.082, 1.8), (20.9, 0.064, 1.7), (25.5, 0.058, 1.9), (30.0, 0.043, 2.0), (35.1, 0.055, 1.8)]

def ground(x, y):
    right = y < 0
    z = 0
    for i, (center, height, width) in enumerate(BUMPS):
        center += 0 if right else 0.32
        h = height if right else height * (0.5 if i in (4, 5) else 0.76)
        u = (x - center) / (width / 2)
        if abs(u) < 1:
            z += h * (0.5 + 0.5 * cos(pi * u))
    return z

def contact_height(x, y):
    return max((ground(x + R * (-1 + 2 * i / 160), y) + R * sqrt(max(0, 1 - (-1 + 2 * i / 160) ** 2)) for i in range(161)))

def pose(f):
    t = (f - 1) / 24
    d = 3 * t
    wh = {a + s: contact_height(d + x, y) - R for a, x in AXLES.items() for s, y in SIDES.items()}
    avg = {}
    for code in wh:
        a, s = code
        avg[code] = sum(((1 - abs(k) / 9) * (contact_height(d + AXLES[a] + k * 0.13, SIDES[s]) - R) for k in range(-8, 9))) / 9
    h = sum(avg.values()) / 4 * 0.72
    pitch = -(avg['FL'] + avg['FR'] - avg['RL'] - avg['RR']) / 2 / 3.2 * 0.35
    roll = (avg['FL'] + avg['RL'] - avg['FR'] - avg['RR']) / 2 / TRACK * 0.3
    return (d, h, pitch, roll, {c: z - h for c, z in wh.items()})
for f in range(1, 241):
    d, h, pitch, roll, q = pose(f)
    for k, v in [('travel_m', d), ('body_heave_m', h), ('body_pitch_deg', math.degrees(pitch)), ('body_roll_deg', math.degrees(roll)), ('steering_deg', 0)]:
        keyprop(root, k, v, f)
    for c, v in q.items():
        keyprop(controls[c], 'travel_m', v, f)
for s, y in [('L', 0.48), ('R', -0.48)]:
    box('Frame rail ' + s, (0, y, 0.69), (4.7, 0.115, 0.18), 'CHASSIS', steel, body, 0.022)
for i, x in enumerate([-2.2, -1.05, 0.02, 0.88, 1.92]):
    box('Frame crossmember %02d' % i, (x, 0, 0.7), (0.11, 1.05, 0.12), 'CHASSIS', steel, body)
cyl('Rear axle | rigid driven tube', (0, -0.82, 0), (0, 0.82, 0), 0.063, 'REAR_SUSPENSION', steel, rear)
uv('Rear differential | cast housing', (0, 0, -0.005), (0.19, 0.235, 0.19), 'DRIVETRAIN', steel, rear)
for code in ('FL', 'FR'):
    s = 1 if code[-1] == 'L' else -1
    hub = hubs[code]
    for level, z, wy in [('Lower', 0.33, 0.37), ('Upper', 0.65, 0.44)]:
        bj = empty('Joint ' + code + ' ' + level, (0, -s * 0.115, z - R), hub)
        for xx in (-0.18, 0.18):
            pivot = empty('Mount ' + code + ' ' + level + str(xx), (1.6 + xx, s * wy, z + 0.015), body)
            rod = dynamic_rod(code + ' ' + level + ' A-arm ' + str(xx), pivot, bj, 0.028 if level == 'Lower' else 0.024, 'FRONT_SUSPENSION', alloy)
            arm_rods.append(rod)
        uv(code + ' ' + level + ' ball joint', (0, -s * 0.115, z - R), (0.045, 0.045, 0.044), 'FRONT_SUSPENSION', black, hub)
    kn = cyl('Steering knuckle ' + code, (0, -s * 0.1, -0.09), (0, -s * 0.1, 0.23), 0.045, 'FRONT_SUSPENSION', steel, hub)
    top = empty('Shock upper ' + code, (1.56, s * 0.47, 0.99), body)
    low = empty('Shock lower ' + code, (-0.06, -s * 0.17, -0.055), hub)
    shocks[code] = (top, low)
    dynamic_rod('Front damper body ' + code, top, low, 0.046, 'FRONT_SUSPENSION', brake, 0.285)
    dynamic_rod('Front damper chrome shaft ' + code, low, top, 0.019, 'FRONT_SUSPENSION', chrome)
for code in ('RL', 'RR'):
    s = 1 if code[-1] == 'L' else -1
    top = empty('Shock upper ' + code, (-2.24, s * 0.3, 0.81), body)
    low = empty('Shock lower ' + code, (-0.1, s * 0.45, -0.025), rear)
    shocks[code] = (top, low)
    dynamic_rod('Rear shock body ' + code, top, low, 0.038, 'REAR_SUSPENSION', brake, 0.3)
    dynamic_rod('Rear shock chrome shaft ' + code, low, top, 0.017, 'REAR_SUSPENSION', chrome)
    saddle = empty('Leaf saddle target ' + code, (0, s * 0.57, -0.095), rear)
    local_saddle = empty('Leaf local deformation target ' + code, (-1.6, s * 0.57, R - 0.095), body)
    con = local_saddle.constraints.new('COPY_LOCATION')
    con.target = saddle
    for layer, half in enumerate([0.86, 0.73, 0.59, 0.46, 0.32]):
        vs = []
        fs = []
        n = 40
        for i in range(n + 1):
            u = -half + 2 * half * i / n
            z = R - 0.095 + 0.295 * (u / 0.86) ** 2 - layer * 0.009
            vs.extend([(-1.6 + u, s * 0.57 - 0.035, z - 0.004), (-1.6 + u, s * 0.57 + 0.035, z - 0.004), (-1.6 + u, s * 0.57 + 0.035, z + 0.004), (-1.6 + u, s * 0.57 - 0.035, z + 0.004)])
        for i in range(n):
            for j in range(4):
                fs.append((4 * i + j, 4 * i + (j + 1) % 4, 4 * (i + 1) + (j + 1) % 4, 4 * (i + 1) + j))
        fs += [(3, 2, 1, 0), (4 * n, 4 * n + 1, 4 * n + 2, 4 * n + 3)]
        o = mesh('Leaf pack ' + code + ' lamination ' + str(layer + 1), vs, fs, 'REAR_SUSPENSION', leafmat, body, 0.0015)
        o.shape_key_add(name='Rest manufactured camber')
        k = o.shape_key_add(name='Compression and rebound', from_mix=False)
        k.slider_min = -1
        k.slider_max = 1
        for i, v in enumerate(k.data):
            u = vs[i][0] + 1.6
            v.co.z += 0.12 * (1 - (u / 0.86) ** 2)

        def saddle_driver(key, axis, rest):
            fc = key.driver_add('value')
            d = fc.driver
            d.expression = f'(v-({rest}))/.12'
            v = d.variables.new()
            v.name = 'v'
            v.type = 'TRANSFORMS'
            v.targets[0].id = local_saddle
            v.targets[0].transform_type = 'LOC_' + axis
            v.targets[0].transform_space = 'LOCAL_SPACE'
        saddle_driver(k, 'Z', R - 0.095)
        for axis, label, rest in [(0, 'Longitudinal compliance', -1.6), (1, 'Axle roll accommodation', s * 0.57)]:
            sk = o.shape_key_add(name=label, from_mix=False)
            sk.slider_min = -1
            sk.slider_max = 1
            for i, v in enumerate(sk.data):
                v.co[axis] += 0.12 * (1 - ((vs[i][0] + 1.6) / 0.86) ** 2)
            saddle_driver(sk, 'XY'[axis], rest)
        leafs.setdefault(code, []).append(o)
transfer_rear = empty('Joint transfer rear', (0.16, 0, 0.6), body)
rear_pinion = empty('Joint rear pinion', (0.23, 0, 0.015), rear)
rearshaft = dynamic_rod('Rear driveshaft | articulated', transfer_rear, rear_pinion, 0.038, 'DRIVETRAIN', alloy)
transfer_front = empty('Joint transfer front', (0.52, -0.13, 0.6), body)
frontdiff = empty('Front differential carrier', (1.6, 0, 0.47), body)
front_pinion = empty('Joint front pinion', (-0.2, -0.08, 0.015), frontdiff)
dynamic_rod('Front driveshaft | transfer to IFS differential', transfer_front, front_pinion, 0.031, 'DRIVETRAIN', alloy)
uv('Front differential | compact carrier', (0, 0, 0), (0.18, 0.23, 0.14), 'DRIVETRAIN', steel, frontdiff)
for code in ('FL', 'FR'):
    s = 1 if code[-1] == 'L' else -1
    a = empty('CV inner ' + code, (0, s * 0.18, 0), frontdiff)
    b = empty('CV outer ' + code, (0, -s * 0.08, 0), hubs[code])
    dynamic_rod('Front CV halfshaft ' + code, a, b, 0.023, 'DRIVETRAIN', alloy)

def ring_y(name, profile, col, ma, parent, n=64):
    vs = [(r * cos(i * 2 * pi / n), y, r * sin(i * 2 * pi / n)) for y, r in profile for i in range(n)]
    fs = []
    for j in range(len(profile)):
        for i in range(n):
            fs.append((j * n + i, j * n + (i + 1) % n, (j + 1) % len(profile) * n + (i + 1) % n, (j + 1) % len(profile) * n + i))
    o = mesh(name, vs, fs, col, ma, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    return o

def text_obj(name, words, loc, size, col, ma, parent=None, rot=(0, 0, 0), align='CENTER'):
    cu = bpy.data.curves.new(name + ' lettering', 'FONT')
    cu.body = words
    cu.align_x = align
    cu.size = size
    cu.extrude = 0.0005
    cu.bevel_depth = 0.0002
    o = bpy.data.objects.new(name, cu)
    C[col].objects.link(o)
    cu.materials.append(ma)
    o.location = loc
    o.rotation_euler = rot
    if parent:
        o.parent = parent
    return o
for code, spin in spins.items():
    s = 1 if code[-1] == 'L' else -1
    hub = hubs[code]
    profile = [(-0.118, 0.232), (-0.13, 0.255), (-0.137, 0.306), (-0.13, 0.347), (-0.112, 0.374), (-0.091, 0.392), (0, 0.394), (0.091, 0.392), (0.112, 0.374), (0.13, 0.347), (0.137, 0.306), (0.13, 0.255), (0.118, 0.232), (0.092, 0.229), (-0.092, 0.229)]
    ring_y('Tire ' + code + ' | formed sidewall and carcass', profile, 'WHEELS', rubber, spin, 96)
    vs = []
    fs = []
    for i in range(64):
        for row in (-1, 0, 1):
            ang = 2 * pi * (i + (0.48 if row == 0 else 0)) / 64
            yc = row * 0.071
            rad = 0.397
            radial = Vector((cos(ang), 0, sin(ang)))
            tangent = Vector((-sin(ang), 0, cos(ang)))
            across = Vector((0, 1, 0))
            center = radial * rad + across * yc
            for rr, tt, yy in [(-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (-1, 1, 1), (1, -1, -1), (1, -1, 1), (1, 1, -1), (1, 1, 1)]:
                v = center + radial * (rr * 0.008) + tangent * (tt * 0.014 + yy * 0.006 * (1 if row >= 0 else -1)) + across * (yy * 0.028)
                vs.append(tuple(v))
            k = len(vs) - 8
            fs += [tuple((k + j for j in face)) for face in [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]]
    mesh('Tread ' + code + ' | 192 staggered all-terrain blocks', vs, fs, 'WHEELS', rubber, spin, 0.0018)
    for sy in (-1, 1):
        ring_y('Sidewall molded bead ' + code + str(sy), [(sy * 0.137, 0.275), (sy * 0.138, 0.278), (sy * 0.138, 0.281), (sy * 0.136, 0.283)], 'WHEELS', rubber, spin)
        ring_y('Sidewall shoulder rib ' + code + str(sy), [(sy * 0.131, 0.338), (sy * 0.133, 0.342), (sy * 0.131, 0.346)], 'WHEELS', rubber, spin)
    ring_y('Alloy rim barrel ' + code, [(-0.12, 0.235), (-0.12, 0.22), (0.12, 0.22), (0.12, 0.235), (0.104, 0.24), (0.09, 0.233), (-0.09, 0.233), (-0.104, 0.24)], 'WHEELS', alloy, spin)
    for sy in (-1, 1):
        ring_y('Rim polished lip ' + code + str(sy), [(sy * 0.121, 0.218), (sy * 0.125, 0.221), (sy * 0.125, 0.235), (sy * 0.118, 0.241)], 'WHEELS', chrome, spin)
    for k in range(6):
        for split in (-1, 1):
            ang = k * 2 * pi / 6
            a = ang + split * 0.075
            b = ang + split * 0.16
            verts = []
            for y in (s * 0.085, s * 0.119):
                verts.extend([(0.069 * cos(a - 0.11), y, 0.069 * sin(a - 0.11)), (0.22 * cos(b - 0.05), y, 0.22 * sin(b - 0.05)), (0.22 * cos(b + 0.05), y, 0.22 * sin(b + 0.05)), (0.069 * cos(a + 0.11), y, 0.069 * sin(a + 0.11))])
            mesh('Alloy split spoke ' + code + f' {k}-{split}', verts, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], 'WHEELS', alloy, spin, 0.004)
    cyl('Wheel hub ' + code, (0, -0.1, 0), (0, 0.1, 0), 0.08, 'WHEELS', steel, spin, n=32)
    cyl('Center cap ' + code, (0, s * 0.12, 0), (0, s * 0.136, 0), 0.047, 'WHEELS', black, spin, n=32)
    for k in range(6):
        a = k * 2 * pi / 6
        cyl('Lug nut ' + code + ' ' + str(k), (0.063 * cos(a), s * 0.118, 0.063 * sin(a)), (0.063 * cos(a), s * 0.141, 0.063 * sin(a)), 0.011, 'WHEELS', chrome, spin, n=6)
    for yy in (-0.035, -0.011):
        ring_y('Brake rotor face ' + code + str(yy), [(yy, 0.085), (yy, 0.186), (yy + 0.007, 0.186), (yy + 0.007, 0.085)], 'WHEELS', alloy, spin)
    for k in range(32):
        a = k * 2 * pi / 32
        ob = box('Rotor cooling vane ' + code + ' ' + str(k), (0.14 * cos(a), -0.018, 0.14 * sin(a)), (0.082, 0.017, 0.007), 'WHEELS', steel, spin, 0.001)
        ob.rotation_euler.y = -a
    box('Brake caliper ' + code, (0.133, -s * 0.058, 0.092), (0.106, 0.09, 0.17), 'FRONT_SUSPENSION' if code[0] == 'F' else 'REAR_SUSPENSION', brake, hub, 0.026)
    box('Caliper bridge ' + code, (0.128, -s * 0.007, 0.098), (0.08, 0.08, 0.052), 'FRONT_SUSPENSION' if code[0] == 'F' else 'REAR_SUSPENSION', brake, hub, 0.012)
    text_obj('Tire molded lettering ' + code, 'TERRA  /  A-T', (-0.005, s * 0.138, 0.304), 0.028, 'WHEELS', steel, spin, (pi / 2 if s < 0 else -pi / 2, 0, 0))
    text_obj('Tire size ' + code, '265 / 65  R18', (0, s * 0.139, -0.318), 0.02, 'WHEELS', steel, spin, (pi / 2 if s < 0 else -pi / 2, 0, 0))

def side_panel(name, xmin, xmax, cx, y, top, bottom, col='BODY'):
    rr = 0.476
    poly = [(xmin, bottom), (xmin, top), (xmax, top), (xmax, bottom), (cx + rr, bottom), (cx + rr, R)]
    poly += [(cx + rr * cos(a), R + rr * sin(a)) for a in [pi * i / 32 for i in range(33)]]
    poly += [(cx - rr, bottom)]
    verts = [(x, yy, z) for yy in (y - 0.025, y + 0.025) for x, z in poly]
    n = len(poly)
    fs = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return mesh(name, verts, fs, col, paint, body, 0.009)
vs = []
sections = [(0.91, 0.865, 1.32), (1.13, 0.878, 1.385), (2.3, 0.84, 1.32), (2.56, 0.81, 1.22)]
for x, w, z in sections:
    vs += [(x, -w, z - 0.075), (x, -w, z), (x, -w * 0.62, z + 0.024), (x, w * 0.62, z + 0.024), (x, w, z), (x, w, z - 0.075)]
fs = [tuple(range(5, -1, -1)), tuple(range(18, 24))]
for j in range(3):
    for k in range(6):
        fs.append((6 * j + k, 6 * j + (k + 1) % 6, 6 * (j + 1) + (k + 1) % 6, 6 * (j + 1) + k))
mesh('Hood | crowned one-piece pressing', vs, fs, 'BODY', paint, body, 0.021)
box('Cowl below windshield', (0.965, 0, 1.28), (0.13, 1.68, 0.095), 'BODY', black, body)
for s, y in [('L', 0.891), ('R', -0.891)]:
    sign = 1 if y > 0 else -1
    side_panel('Front fender ' + s, 0.99, 2.59, 1.6, y, 1.278, 0.66)
    side_panel('Bed side ' + s, -2.6, -1.045, -1.6, y, 1.285, 0.66)
    for label, cx in [('Front', 1.6), ('Rear', -1.6)]:
        vs = []
        fs = []
        for i in range(41):
            a = pi * i / 40
            for rr, yy in [(0.468, y + sign * 0.002), (0.511, y + sign * 0.008), (0.511, y + sign * 0.05), (0.468, y + sign * 0.05)]:
                vs.append((cx + rr * cos(a), yy, R + rr * sin(a)))
        for i in range(40):
            for j in range(4):
                fs.append((4 * i + j, 4 * i + (j + 1) % 4, 4 * (i + 1) + (j + 1) % 4, 4 * (i + 1) + j))
        mesh(label + ' wheel arch flare ' + s, vs, fs, 'BODY', black, body, 0.005)
        pts = [(cx + 0.501 * cos(pi * i / 32), y - sign * 0.1, R + 0.501 * sin(pi * i / 32)) for i in range(33)]
        tube(label + ' wheelhouse inner rolled edge ' + s, pts, 0.014, 'BODY', black, body)
    box('Rocker sill ' + s, (-0.025, y - sign * 0.032, 0.807), (2.04, 0.092, 0.075), 'BODY', black, body)
    box('Running board ' + s, (-0.05, y + sign * 0.055, 0.65), (1.93, 0.21, 0.055), 'BODY', steel, body, 0.018)
    for x in (-0.75, 0.64):
        box('Running board chassis mount ' + s + str(x), (x, sign * 0.7, 0.66), (0.085, 0.37, 0.055), 'CHASSIS', steel, body)
    for i, (x0, x1) in enumerate([(-1.025, -0.068), (-0.045, 0.977)]):
        box('Door seam backing ' + s + str(i), ((x0 + x1) / 2, y - sign * 0.024, 1.045), (x1 - x0 + 0.016, 0.026, 0.464), 'BODY', black, body, 0.012)
        poly = [(x0, 0.847), (x1, 0.847), (x1, 1.282), (x0, 1.282)]
        v = [(x, yy, z) for yy in (y - sign * 0.018, y + sign * 0.008) for x, z in poly]
        mesh(('Rear' if i == 0 else 'Front') + ' door skin ' + s, v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], 'BODY', paint, body, 0.024)
        box('Door character line ' + s + str(i), ((x0 + x1) / 2, y + sign * 0.013, 1.195), (x1 - x0 - 0.045, 0.012, 0.018), 'BODY', paint, body, 0.005)
        hx = x0 + 0.17
        box('Handle recess ' + s + str(i), (hx, y + sign * 0.025, 1.234), (0.2, 0.022, 0.053), 'BODY', black, body, 0.02)
        box('Door pull ' + s + str(i), (hx, y + sign * 0.051, 1.246), (0.139, 0.033, 0.024), 'BODY', alloy, body, 0.009)
    for label, pts in [('Rear', [(-1.013, 1.323), (-0.104, 1.323), (-0.104, 1.759), (-0.887, 1.759)]), ('Front', [(-0.022, 1.323), (0.922, 1.323), (0.491, 1.759), (-0.022, 1.759)])]:
        co = [(x, sign * (0.892 - (z - 1.3) * 0.245), z) for x, z in pts]
        o = mesh(label + ' door glazing ' + s, co, [(3, 2, 1, 0) if sign > 0 else (0, 1, 2, 3)], 'BODY', glass, body)
        mod = o.modifiers.new('Laminated glass 8 mm', 'SOLIDIFY')
        mod.thickness = 0.008
        tube(label + ' window gasket ' + s, co, 0.017, 'BODY', black, body, True)
    for label, a, b, rad in [('A', (0.98, sign * 0.889, 1.29), (0.505, sign * 0.779, 1.798), 0.042), ('B', (-0.06, sign * 0.89, 1.29), (-0.06, sign * 0.779, 1.798), 0.035), ('C', (-1.048, sign * 0.889, 1.29), (-0.93, sign * 0.779, 1.798), 0.043)]:
        cyl(label + ' pillar ' + s, a, b, rad, 'BODY', paint if label != 'B' else black, body, n=12)
    box('Mirror sail ' + s, (0.855, sign * 0.904, 1.36), (0.14, 0.065, 0.16), 'BODY', black, body, 0.026)
    cyl('Mirror arm ' + s, (0.79, sign * 0.91, 1.391), (0.75, sign * 1.045, 1.425), 0.028, 'BODY', black, body)
    box('Mirror housing ' + s, (0.735, sign * 1.076, 1.46), (0.23, 0.14, 0.14), 'BODY', paint, body, 0.046)
    box('Mirror glass ' + s, (0.611, sign * 1.079, 1.466), (0.009, 0.106, 0.09), 'BODY', chrome, body, 0.01)
    box('Mirror signal strip ' + s, (0.855, sign * 1.089, 1.445), (0.014, 0.1, 0.012), 'BODY', lightmat, body, 0.004)
box('Cab roof | soft rectangular pressing', (-0.206, 0, 1.815), (1.53, 1.64, 0.085), 'BODY', paint, body, 0.064)
for s in (-1, 1):
    tube('Roof rain gutter ' + str(s), [(-0.9, s * 0.806, 1.841), (0.45, s * 0.806, 1.841)], 0.008, 'BODY', black, body)
    for x in (-0.72, 0.32):
        box('Roof rail pedestal ' + str(s) + str(x), (x, s * 0.6, 1.872), (0.14, 0.055, 0.03), 'BODY', black, body, 0.011)
    tube('Low roof rail ' + str(s), [(-0.78, s * 0.6, 1.9), (0.39, s * 0.6, 1.9)], 0.018, 'BODY', steel, body)
co = [(1.008, -0.847, 1.322), (1.008, 0.847, 1.322), (0.519, 0.756, 1.779), (0.519, -0.756, 1.779)]
o = mesh('Windshield | thick sloped laminated glass', co, [(0, 1, 2, 3)], 'BODY', glass, body)
o.modifiers.new('Windshield 10 mm', 'SOLIDIFY').thickness = 0.01
tube('Windshield perimeter gasket', co, 0.019, 'BODY', black, body, True)
for y in (-0.43, 0.36):
    cyl('Wiper arm ' + str(y), (1.032, y, 1.335), (0.9, y + 0.1, 1.46), 0.006, 'BODY', steel, body)
    tube('Wiper blade ' + str(y), [(0.905, y - 0.11, 1.45), (0.905, y + 0.23, 1.45)], 0.009, 'BODY', black, body)
box('Cab rear lower bulkhead', (-1.031, 0, 1.057), (0.063, 1.77, 0.465), 'BODY', paint, body, 0.014)
co = [(-1.025, -0.79, 1.322), (-1.025, 0.79, 1.322), (-0.932, 0.745, 1.765), (-0.932, -0.745, 1.765)]
o = mesh('Cab rear window', co, [(3, 2, 1, 0)], 'BODY', glass, body)
o.modifiers.new('Rear glass 8 mm', 'SOLIDIFY').thickness = 0.008
tube('Rear glass gasket', co, 0.018, 'BODY', black, body, True)
for y in (-0.24, 0.24):
    tube('Rear sliding glass divider ' + str(y), [(-1.022, y, 1.33), (-0.936, y, 1.75)], 0.009, 'BODY', black, body)
for sign in (-1, 1):
    box('Cab interior floor ' + str(sign), (-0.07, sign * 0.535, 0.858), (1.92, 0.6, 0.045), 'INTERIOR', black, body, 0.02)
mesh('Raised transmission tunnel', [(-1.03, -0.235, 0.858), (-1.03, -0.19, 1.03), (-1.03, 0.19, 1.03), (-1.03, 0.235, 0.858), (0.91, -0.235, 0.858), (0.91, -0.19, 1.03), (0.91, 0.19, 1.03), (0.91, 0.235, 0.858)], [(0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3)], 'INTERIOR', black, body, 0.018)
box('Bed liner floor', (-1.86, 0, 0.903), (1.52, 1.69, 0.075), 'BODY', black, body, 0.012)
box('Bed forward bulkhead', (-1.079, 0, 1.116), (0.055, 1.74, 0.335), 'BODY', paint, body)
for y in [i * 0.098 for i in range(-8, 9)]:
    box('Bed raised liner rib ' + str(y), (-1.856, y, 0.945), (1.43, 0.028, 0.018), 'BODY', black, body, 0.006)
for s in (-1, 1):
    box('Bed rail cap ' + str(s), (-1.835, s * 0.892, 1.296), (1.6, 0.1, 0.033), 'BODY', black, body, 0.011)
    box('Bed inner wall ' + str(s), (-1.835, s * 0.853, 1.118), (1.49, 0.032, 0.3), 'BODY', black, body, 0.008)
    box('Bed wheel tub ' + str(s), (-1.6, s * 0.736, 0.99), (0.97, 0.255, 0.173), 'BODY', black, body, 0.075)
    for x in (-2.43, -1.23):
        tube('Cargo tie-down ' + str(s) + str(x), [(x - 0.035, s * 0.808, 1.18), (x - 0.035, s * 0.788, 1.14), (x + 0.035, s * 0.788, 1.14), (x + 0.035, s * 0.808, 1.18)], 0.009, 'BODY', alloy, body)
box('Tailgate gap backing', (-2.595, 0, 1.061), (0.047, 1.77, 0.458), 'BODY', black, body)
box('Tailgate | separated pressed skin', (-2.624, 0, 1.066), (0.053, 1.688, 0.424), 'BODY', paint, body, 0.025)
box('Tailgate top protector', (-2.62, 0, 1.292), (0.102, 1.745, 0.035), 'BODY', black, body, 0.012)
box('Tailgate handle recess', (-2.66, 0, 1.222), (0.013, 0.256, 0.056), 'BODY', black, body, 0.017)
box('Tailgate handle metal', (-2.671, 0, 1.23), (0.014, 0.17, 0.024), 'BODY', alloy, body, 0.005)
for y in (-0.59, 0.59):
    cyl('Tailgate hinge ' + str(y), (-2.607, y - 0.06, 0.87), (-2.607, y + 0.06, 0.87), 0.022, 'BODY', steel, body)
box('Front fascia bridge', (2.574, 0, 1.191), (0.12, 1.67, 0.095), 'BODY', paint, body, 0.03)
box('Front grille dark recess', (2.57, 0, 1.012), (0.075, 1.19, 0.306), 'BODY', black, body, 0.032)
for z in (0.89, 0.969, 1.048, 1.127):
    box('Grille horizontal bar ' + str(z), (2.627, 0, z), (0.035, 1.17, 0.015), 'BODY', steel, body, 0.005)
for y in [i * 0.075 for i in range(-7, 8)]:
    box('Grille vertical fin ' + str(y), (2.618, y, 1.01), (0.026, 0.011, 0.248), 'BODY', steel, body, 0.004)
for s in (-1, 1):
    box('Headlight black module ' + str(s), (2.55, s * 0.697, 1.076), (0.16, 0.272, 0.239), 'BODY', black, body, 0.034)
    box('Headlamp glazing ' + str(s), (2.641, s * 0.697, 1.076), (0.017, 0.247, 0.209), 'BODY', glass, body, 0.019)
    for y in (s * 0.642, s * 0.751):
        cyl('LED projector bezel ' + str(y), (2.639, y, 1.092), (2.661, y, 1.092), 0.045, 'BODY', alloy, body, n=32)
        cyl('LED projector optic ' + str(y), (2.662, y, 1.092), (2.669, y, 1.092), 0.033, 'BODY', lightmat, body, n=32)
    tube('Daytime lamp signature ' + str(s), [(2.674, s * 0.59, 1.159), (2.674, s * 0.792, 1.159), (2.674, s * 0.804, 1.013)], 0.009, 'BODY', lightmat, body)
    box('Front turn signal ' + str(s), (2.667, s * 0.697, 0.998), (0.012, 0.19, 0.013), 'BODY', amber, body, 0.004)
    box('Taillamp housing ' + str(s), (-2.599, s * 0.859, 1.095), (0.09, 0.107, 0.331), 'BODY', black, body, 0.026)
    box('Taillamp red lens ' + str(s), (-2.651, s * 0.859, 1.11), (0.018, 0.085, 0.287), 'BODY', red, body, 0.018)
    for z in (1.01, 1.1, 1.2):
        box('Rear LED blade ' + str(s) + str(z), (-2.664, s * 0.859, z), (0.012, 0.062, 0.035), 'BODY', redlight, body, 0.009)
    box('Rear reversing lamp ' + str(s), (-2.666, s * 0.859, 1.055), (0.013, 0.063, 0.024), 'BODY', lightmat, body, 0.006)
box('Front bumper | graphite center', (2.548, 0, 0.751), (0.25, 1.32, 0.181), 'BODY', black, body, 0.048)
for s in (-1, 1):
    box('Front bumper corner ' + str(s), (2.47, s * 0.735, 0.752), (0.31, 0.3, 0.162), 'BODY', black, body, 0.056)
    box('Front recovery eye base ' + str(s), (2.66, s * 0.463, 0.707), (0.048, 0.07, 0.095), 'CHASSIS', steel, body, 0.012)
    tube('Front recovery loop ' + str(s), [(2.691, s * 0.5, 0.716), (2.736, s * 0.5, 0.65), (2.736, s * 0.43, 0.65), (2.691, s * 0.43, 0.716)], 0.013, 'CHASSIS', accent, body)
box('Rear bumper | step center', (-2.606, 0, 0.752), (0.23, 1.82, 0.146), 'BODY', black, body, 0.037)
for s in (-1, 1):
    box('Rear step tread ' + str(s), (-2.675, s * 0.598, 0.83), (0.24, 0.55, 0.021), 'BODY', rubber, body, 0.006)
    for i in range(5):
        box('Rear step grip ' + str(s) + str(i), (-2.675, s * 0.598 + (i - 2) * 0.087, 0.843), (0.18, 0.017, 0.006), 'BODY', steel, body, 0.002)
box('Tow receiver crossbar', (-2.33, 0, 0.592), (0.12, 1.05, 0.1), 'CHASSIS', steel, body)
box('Tow hitch receiver', (-2.555, 0, 0.574), (0.48, 0.09, 0.09), 'CHASSIS', steel, body, 0.012)
box('Tow receiver dark aperture', (-2.802, 0, 0.574), (0.006, 0.065, 0.065), 'CHASSIS', black, body, 0.003)
box('Hitch ball tongue', (-2.82, 0, 0.552), (0.26, 0.073, 0.035), 'CHASSIS', steel, body)
cyl('Hitch ball neck', (-2.914, 0, 0.57), (-2.914, 0, 0.625), 0.022, 'CHASSIS', chrome, body)
uv('Hitch tow ball', (-2.914, 0, 0.648), (0.029, 0.029, 0.029), 'CHASSIS', chrome, body)
for label, x, ys in [('Front', 0.29, (-0.435, 0.435)), ('Rear', -0.61, (-0.53, 0, 0.53))]:
    for i, y in enumerate(ys):
        box(label + ' seat cushion ' + str(i), (x, y, 1.003), (0.43, 0.4 if label == 'Front' else 0.43, 0.136), 'INTERIOR', seatmat, body, 0.064)
        ob = box(label + ' seat back ' + str(i), (x - 0.206, y, 1.253), (0.113, 0.408, 0.444), 'INTERIOR', seatmat, body, 0.053)
        ob.rotation_euler.y = -0.13
        box(label + ' headrest ' + str(i), (x - 0.235, y, 1.54), (0.115, 0.229, 0.144), 'INTERIOR', black, body, 0.04)
        for yy in (y - 0.065, y + 0.065):
            cyl('Headrest stalk ' + label + str(i) + str(yy), (x - 0.224, yy, 1.42), (x - 0.23, yy, 1.51), 0.008, 'INTERIOR', chrome, body)
        for yy in (y - 0.13, y + 0.13):
            tube('Seat seam ' + label + str(i) + str(yy), [(x - 0.09, yy, 1.077), (x + 0.13, yy, 1.077)], 0.002, 'INTERIOR', steel, body)
        box('Seatbelt buckle ' + label + str(i), (x - 0.06, y + 0.205, 1.06), (0.042, 0.032, 0.072), 'INTERIOR', brake, body, 0.009)
box('Dashboard main shell', (0.775, 0, 1.203), (0.38, 1.58, 0.216), 'INTERIOR', black, body, 0.065)
box('Dashboard brushed strip', (0.555, 0, 1.25), (0.028, 1.42, 0.029), 'INTERIOR', alloy, body, 0.005)
for y in (-0.63, -0.28, 0.29, 0.63):
    box('Air vent surround ' + str(y), (0.566, y, 1.289), (0.025, 0.164, 0.07), 'INTERIOR', steel, body, 0.011)
    for z in (1.27, 1.288, 1.306):
        box('Air vent slat ' + str(y) + str(z), (0.549, y, z), (0.01, 0.137, 0.006), 'INTERIOR', black, body, 0.001)
box('Instrument binnacle', (0.561, 0.426, 1.346), (0.144, 0.352, 0.143), 'INTERIOR', black, body, 0.035)
box('Instrument dark glass', (0.483, 0.426, 1.35), (0.01, 0.291, 0.08), 'INTERIOR', glass, body, 0.009)
box('Center display', (0.558, 0, 1.357), (0.037, 0.249, 0.15), 'INTERIOR', steel, body, 0.012)
box('Display glass', (0.534, 0, 1.358), (0.008, 0.219, 0.12), 'INTERIOR', glass, body, 0.005)
box('Center console', (0.139, 0, 1.003), (0.63, 0.22, 0.237), 'INTERIOR', black, body, 0.045)
cyl('Gear selector', (0.296, 0, 1.1), (0.275, 0, 1.23), 0.019, 'INTERIOR', alloy, body)
uv('Gear knob', (0.275, 0, 1.234), (0.038, 0.033, 0.034), 'INTERIOR', black, body)
for x in (-0.05, 0.095):
    ring_y('Console cupholder ' + str(x), [(0, 0.039), (0.025, 0.039), (0.026, 0.049), (0, 0.049)], 'INTERIOR', black, body).rotation_euler.x = pi / 2
    o = bpy.data.objects['Console cupholder ' + str(x)]
    o.location = (x, 0, 1.127)
cyl('Steering column', (0.7, 0.435, 1.17), (0.365, 0.435, 1.299), 0.027, 'INTERIOR', steel, body)
steer = empty('Interior steering wheel pivot', (0.345, 0.435, 1.306), body)
steer.rotation_euler.y = pi / 2 - 0.27
tube('Steering wheel rim', [(0.164 * cos(i * 2 * pi / 64), 0.164 * sin(i * 2 * pi / 64), 0) for i in range(64)], 0.016, 'INTERIOR', black, steer, True)
for a in (0, pi, 1.5 * pi):
    cyl('Steering wheel spoke ' + str(a), (0, 0, 0), (0.148 * cos(a), 0.148 * sin(a), 0), 0.018, 'INTERIOR', alloy, steer)
uv('Steering wheel airbag', (0, 0, 0), (0.068, 0.062, 0.03), 'INTERIOR', black, steer)
for s in (-1, 1):
    for x in (-0.59, 0.48):
        box('Interior door card ' + str(s) + str(x), (x, s * 0.834, 1.083), (0.87, 0.056, 0.331), 'INTERIOR', black, body, 0.024)
        box('Interior door armrest ' + str(s) + str(x), (x, s * 0.799, 1.117), (0.39, 0.066, 0.056), 'INTERIOR', seatmat, body, 0.016)
box('Engine | inline four cast block', (1.63, 0, 0.958), (0.68, 0.48, 0.42), 'DRIVETRAIN', steel, body, 0.066)
box('Engine cylinder head', (1.6, 0, 1.184), (0.69, 0.45, 0.106), 'DRIVETRAIN', alloy, body, 0.025)
box('Engine valve cover', (1.59, 0, 1.255), (0.59, 0.366, 0.065), 'DRIVETRAIN', black, body, 0.023)
box('Engine oil sump', (1.67, 0, 0.695), (0.45, 0.345, 0.164), 'DRIVETRAIN', alloy, body, 0.04)
for x in (1.39, 1.57, 1.75, 1.93):
    tube('Exhaust manifold runner ' + str(x), [(x, -0.24, 1.075), (x, -0.303, 1.035), (1.26, -0.337, 0.939)], 0.024, 'DRIVETRAIN', alloy, body)
    cyl('Intake runner ' + str(x), (x, 0.223, 1.1), (x, 0.317, 1.11), 0.039, 'DRIVETRAIN', black, body)
box('Intake plenum', (1.61, 0.337, 1.103), (0.67, 0.132, 0.123), 'DRIVETRAIN', black, body, 0.03)
cyl('Transmission bellhousing', (1.23, 0, 0.878), (0.957, 0, 0.797), 0.226, 'DRIVETRAIN', alloy, body, n=32, r2=0.18)
cyl('Transmission | longitudinal case', (0.969, 0, 0.797), (0.397, 0, 0.675), 0.178, 'DRIVETRAIN', alloy, body, n=32, r2=0.108)
for i in range(8):
    x = 0.46 + i * 0.066
    z = 0.675 + (x - 0.397) / (0.969 - 0.397) * 0.122
    cyl('Transmission cast rib ' + str(i), (x - 0.01, 0, z), (x + 0.013, 0, z), 0.123 + (x - 0.397) * 0.096, 'DRIVETRAIN', steel, body, n=24)
box('Transfer case | offset front output', (0.318, -0.065, 0.642), (0.28, 0.37, 0.256), 'DRIVETRAIN', alloy, body, 0.054)
for s in (-1, 1):
    box('Engine mount bracket ' + str(s), (1.54, s * 0.376, 0.844), (0.22, 0.233, 0.08), 'CHASSIS', steel, body)
    cyl('Engine mount bushing ' + str(s), (1.54, s * 0.35, 0.83), (1.54, s * 0.35, 0.885), 0.057, 'CHASSIS', rubber, body)
box('Gearbox mount saddle', (0.37, 0, 0.568), (0.138, 0.46, 0.061), 'CHASSIS', rubber, body, 0.012)
box('Radiator core', (2.333, 0, 1.028), (0.066, 1.24, 0.377), 'DRIVETRAIN', steel, body, 0.014)
for y in [i * 0.042 for i in range(-14, 15)]:
    box('Radiator fin ' + str(y), (2.294, y, 1.033), (0.018, 0.012, 0.329), 'DRIVETRAIN', alloy, body, 0.002)
for y in (-0.678, 0.678):
    box('Radiator support ' + str(y), (2.301, y, 0.994), (0.114, 0.067, 0.537), 'CHASSIS', steel, body)
box('Fuel tank | left side protected polymer', (-0.43, 0.253, 0.612), (0.98, 0.3, 0.248), 'DRIVETRAIN', black, body, 0.071)
for x in (-0.79, -0.11):
    tube('Fuel tank retaining strap ' + str(x), [(x, 0.085, 0.692), (x, 0.09, 0.502), (x, 0.14, 0.471), (x, 0.399, 0.471), (x, 0.417, 0.506), (x, 0.466, 0.7)], 0.014, 'CHASSIS', alloy, body)
tube('Fuel filler neck', [(-0.7, 0.375, 0.72), (-0.78, 0.375, 0.84), (-1.1, 0.66, 0.91), (-1.18, 0.89, 1.15)], 0.027, 'DRIVETRAIN', black, body)
box('Fuel flap gasket', (-1.18, 0.922, 1.154), (0.151, 0.015, 0.138), 'BODY', black, body, 0.027)
box('Fuel flap | flush bed-side door', (-1.18, 0.932, 1.154), (0.135, 0.015, 0.122), 'BODY', paint, body, 0.024)
exhaustpts = [(1.26, -0.337, 0.939), (1.23, -0.365, 0.724), (1.2, -0.365, 0.545), (1.05, -0.646, 0.54), (0.72, -0.673, 0.52), (0.1, -0.673, 0.505), (-0.47, -0.673, 0.507), (-0.8, -0.65, 0.53), (-1.08, -0.64, 0.71), (-1.43, -0.64, 0.802), (-1.77, -0.64, 0.802), (-2.0, -0.691, 0.68), (-2.35, -0.741, 0.557), (-2.47, -0.897, 0.535)]
tube('Exhaust | continuous right-side routing', exhaustpts, 0.024, 'DRIVETRAIN', alloy, body)
cyl('Catalytic converter', (1.03, -0.66, 0.565), (0.72, -0.673, 0.52), 0.064, 'DRIVETRAIN', alloy, body, n=24)
cyl('Muffler | oval silencer', (0.08, -0.673, 0.505), (-0.45, -0.673, 0.507), 0.071, 'DRIVETRAIN', steel, body, n=32)
cyl('Exhaust tip', (-2.4, -0.79, 0.55), (-2.49, -0.931, 0.529), 0.033, 'DRIVETRAIN', chrome, body, n=24)
for x, z in ((0.5, 0.67), (-0.5, 0.65), (-2.12, 0.75)):
    tube('Exhaust hanger ' + str(x), [(x, -0.47, z), (x, -0.615, z), (x, -0.675, z - 0.13)], 0.01, 'CHASSIS', steel, body)
    uv('Exhaust rubber isolator ' + str(x), (x, -0.61, z - 0.01), (0.025, 0.018, 0.04), 'CHASSIS', rubber, body)
for i, (x, z, length) in enumerate([(0.77, 0.685, 0.56), (-0.22, 0.68, 0.69), (-1.58, 0.851, 0.72)]):
    box('Exhaust heat shield ' + str(i), (x, -0.67, z), (length, 0.2, 0.012), 'DRIVETRAIN', alloy, body, 0.021)
    for xx in [x - length * 0.37, x, x + length * 0.37]:
        box('Heat shield pressed rib ' + str(i) + str(xx), (xx, -0.67, z - 0.01), (0.015, 0.185, 0.008), 'DRIVETRAIN', steel, body, 0.002)
ob = box('Front bash plate | limited engine protection', (2.08, 0, 0.584), (0.45, 0.74, 0.035), 'CHASSIS', alloy, body, 0.018)
ob.rotation_euler.y = -0.23
box('Transfer skid | small serviceable plate', (0.26, 0, 0.465), (0.36, 0.38, 0.025), 'CHASSIS', alloy, body, 0.012)
for x in (0.12, 0.4):
    for y in (-0.14, 0.14):
        cyl('Transfer skid bolt ' + str(x) + str(y), (x, y, 0.448), (x, y, 0.468), 0.012, 'CHASSIS', steel, body, n=6)
cyl('Rear differential cover', (-0.162, 0, -0.005), (-0.194, 0, -0.005), 0.163, 'DRIVETRAIN', alloy, rear, n=16)
for i in range(10):
    a = i * 2 * pi / 10
    y = 0.143 * cos(a)
    z = -0.005 + 0.143 * sin(a)
    cyl('Rear differential cover bolt ' + str(i), (-0.2, y, z), (-0.209, y, z), 0.01, 'DRIVETRAIN', steel, rear, n=6)
for s in (-1, 1):
    cyl('Rear wheel bearing housing ' + str(s), (0, s * 0.703, 0), (0, s * 0.784, 0), 0.085, 'REAR_SUSPENSION', steel, rear, n=24)
    box('Leaf spring saddle ' + str(s), (0, s * 0.57, -0.094), (0.155, 0.119, 0.025), 'REAR_SUSPENSION', steel, rear, 0.008)
    box('Leaf pack clamp plate ' + str(s), (0, s * 0.57, -0.151), (0.183, 0.128, 0.017), 'REAR_SUSPENSION', alloy, rear, 0.004)
    for xx in (-0.057, 0.057):
        pts = [(xx, s * 0.57 - 0.049, -0.162), (xx, s * 0.57 - 0.049, 0.045)]
        pts += [(xx, s * 0.57 - 0.049 * cos(i * pi / 12), 0.045 + 0.049 * sin(i * pi / 12)) for i in range(13)]
        pts += [(xx, s * 0.57 + 0.049, -0.162)]
        tube('Axle U-bolt ' + str(s) + str(xx), pts, 0.008, 'REAR_SUSPENSION', alloy, rear)
        for yy in (s * 0.57 - 0.049, s * 0.57 + 0.049):
            cyl('U-bolt retaining nut ' + str(s) + str(xx) + str(yy), (xx, yy, -0.17), (xx, yy, -0.149), 0.013, 'REAR_SUSPENSION', steel, rear, n=6)
    for xx, label in [(-0.74, 'Front fixed eye'), (-2.46, 'Rear shackle')]:
        cyl(label + ' bushing ' + str(s), (xx, s * 0.57 - 0.047, 0.605), (xx, s * 0.57 + 0.047, 0.605), 0.041, 'REAR_SUSPENSION', rubber, body, n=24)
        cyl(label + ' through bolt ' + str(s), (xx, s * 0.57 - 0.065, 0.605), (xx, s * 0.57 + 0.065, 0.605), 0.015, 'REAR_SUSPENSION', alloy, body, n=6)
        for yy in (s * 0.57 - 0.055, s * 0.57 + 0.055):
            box(label + ' mounting cheek ' + str(s) + str(yy), (xx, yy, 0.657), (0.091, 0.015, 0.16), 'REAR_SUSPENSION', steel, body, 0.008)
        box(label + ' frame outrigger ' + str(s), (xx, s * 0.525, 0.735), (0.135, 0.198, 0.045), 'CHASSIS', steel, body, 0.009)
    box('Rear upper damper frame bracket ' + str(s), (-2.24, s * 0.39, 0.798), (0.13, 0.26, 0.044), 'REAR_SUSPENSION', steel, body, 0.009)
    tube('Rear axle brake hardline ' + str(s), [(0, 0, 0.087), (-0.028, s * 0.29, 0.085), (-0.04, s * 0.65, 0.077), (0.075, s * 0.75, 0.09)], 0.006, 'REAR_SUSPENSION', alloy, rear)
    tube('Rear caliper flexible hose ' + str(s), [(0.075, s * 0.75, 0.09), (0.13, s * 0.7, 0.11), (0.18, s * 0.73, 0.1), (0.15, s * 0.8, 0.095)], 0.008, 'REAR_SUSPENSION', rubber, rear)
rearhose = tube('Rear brake distribution flex loop', [(-1.31, 0.16, 0.72), (-1.46, 0.15, 0.6), (-1.59, 0.15, 0.51), (-1.628, 0.15, 0.49)], 0.008, 'REAR_SUSPENSION', rubber, body)
rearhose.shape_key_add(name='Rest brake hose loop')
key = rearhose.shape_key_add(name='Axle hose articulation', from_mix=False)
key.slider_min = -1
key.slider_max = 1
for i, p in enumerate(key.data):
    p.co.z += 0.12 * (i / (len(key.data) - 1)) ** 2
driver(key, 'value', None, '((l+r)/2+.15/1.66*(l-r)-1.6*p*pi/180-.15*q*pi/180)/.12', [pvar('l', controls['RL'], 'travel_m'), pvar('r', controls['RR'], 'travel_m'), pvar('p', root, 'body_pitch_deg'), pvar('q', root, 'body_roll_deg')])
for code in ('FL', 'FR'):
    s = 1 if code[-1] == 'L' else -1
    hub = hubs[code]
    top, low = shocks[code]
    pts = []
    for i in range(241):
        t = i / 240
        a = t * 8 * 2 * pi
        pts.append((0.076 * cos(a), 0.076 * sin(a), 0.1 + t * 0.72))
    o = tube('Front coil spring ' + code, pts, 0.011, 'FRONT_SUSPENSION', steel)
    co = o.constraints.new('COPY_LOCATION')
    co.target = top
    co = o.constraints.new('DAMPED_TRACK')
    co.target = low
    co.track_axis = 'TRACK_Z'
    fc = o.driver_add('scale', 2)
    d = fc.driver
    d.expression = 'L'
    v = d.variables.new()
    v.name = 'L'
    v.type = 'LOC_DIFF'
    v.targets[0].id = top
    v.targets[1].id = low
    dynamic_rod('Front upper spring seat ' + code, top, low, 0.092, 'FRONT_SUSPENSION', alloy, 0.028)
    dynamic_rod('Front lower spring seat ' + code, low, top, 0.088, 'FRONT_SUSPENSION', alloy, 0.045)
    for xx in (1.42, 1.78):
        for z, yy in ((0.345, 0.37), (0.665, 0.44)):
            cyl('Wishbone pivot sleeve ' + code + str(xx) + str(z), (xx - 0.049, s * yy, z), (xx + 0.049, s * yy, z), 0.045, 'FRONT_SUSPENSION', rubber, body)
            cyl('Wishbone pivot bolt ' + code + str(xx) + str(z), (xx - 0.06, s * yy, z), (xx + 0.06, s * yy, z), 0.015, 'FRONT_SUSPENSION', alloy, body, n=6)
            for xoff in (-0.055, 0.055):
                box('Wishbone frame tab ' + code + str(xx) + str(z) + str(xoff), (xx + xoff, s * yy, z + 0.046), (0.017, 0.093, 0.126), 'FRONT_SUSPENSION', steel, body, 0.006)
    box('Upper shock tower ' + code, (1.56, s * 0.473, 0.95), (0.162, 0.197, 0.183), 'FRONT_SUSPENSION', steel, body, 0.026)
    cyl('Top shock mount bolt ' + code, (1.56, s * 0.41, 0.99), (1.56, s * 0.56, 0.99), 0.017, 'FRONT_SUSPENSION', alloy, body, n=6)
    a = empty('Steering rack end ' + code, (1.33, s * 0.41, 0.52), body)
    b = empty('Steering arm joint ' + code, (-0.125, -s * 0.101, 0.055), hub)
    dynamic_rod('Steering tie rod ' + code, a, b, 0.014, 'FRONT_SUSPENSION', alloy)
    cyl('Knuckle steering arm ' + code, (0, -s * 0.1, 0.02), (-0.125, -s * 0.101, 0.055), 0.026, 'FRONT_SUSPENSION', steel, hub)
    uv('Tie rod ball end ' + code, (-0.125, -s * 0.101, 0.055), (0.023, 0.025, 0.023), 'FRONT_SUSPENSION', black, hub)
    for end, label in [('CV inner ' + code, 'inboard'), ('CV outer ' + code, 'outboard')]:
        anchor = bpy.data.objects[end]
        other = bpy.data.objects['CV outer ' + code if label == 'inboard' else 'CV inner ' + code]
        for k in range(5):
            ob = dynamic_rod('CV boot ' + code + ' ' + label + ' rib ' + str(k), anchor, other, 0.05 - k * 0.004, 'DRIVETRAIN', rubber, 0.015)
            for vv in ob.data.vertices:
                vv.co.z += k * 1.05
    pts = [(1.38, s * 0.49, 0.83), (1.31, s * 0.6, 0.76), (1.31, s * 0.7, 0.63), (1.45, s * 0.75, 0.54), (1.67, s * 0.77, 0.5)]
    hose = tube('Front brake flex hose ' + code, pts, 0.008, 'FRONT_SUSPENSION', rubber, body)
    hose.shape_key_add(name='Rest hose loop')
    k = hose.shape_key_add(name='Wheel articulation')
    k.slider_min = -1
    k.slider_max = 1
    for i, p in enumerate(k.data):
        p.co.z += 0.12 * (i / (len(k.data) - 1)) ** 2
    driver(k, 'value', None, 'q/.12', [pvar('q', controls[code], 'travel_m')])
cyl('Steering rack | central housing', (1.33, -0.4, 0.52), (1.33, 0.4, 0.52), 0.039, 'FRONT_SUSPENSION', steel, body)
for s in (-1, 1):
    for i in range(6):
        cyl('Rack bellows ' + str(s) + str(i), (1.33, s * (0.3 + i * 0.017), 0.52), (1.33, s * (0.31 + i * 0.017), 0.52), 0.048, 'FRONT_SUSPENSION', rubber, body)
tube('Steering intermediate shaft', [(1.32, 0.19, 0.56), (1.18, 0.27, 0.79), (0.83, 0.425, 1.1)], 0.016, 'DRIVETRAIN', alloy, body)
for x in (-2.2, -1.05, 0.02, 0.88, 1.92):
    for s in (-1, 1):
        cyl('Body isolation mount ' + str(x) + str(s), (x, s * 0.48, 0.773), (x, s * 0.48, 0.845), 0.039, 'CHASSIS', rubber, body)
        for dx in (-0.035, 0.035):
            cyl('Frame crossmember bolt ' + str(x) + str(s) + str(dx), (x + dx, s * 0.48, 0.794), (x + dx, s * 0.48, 0.81), 0.011, 'CHASSIS', alloy, body, n=6)
for code, (top, low) in shocks.items():
    for anchor, label in [(top, 'upper'), (low, 'lower')]:
        cyl('Shock eye ' + code + ' ' + label, (0, -0.035, 0), (0, 0.035, 0), 0.039, 'FRONT_SUSPENSION' if code[0] == 'F' else 'REAR_SUSPENSION', steel, anchor)
        cyl('Shock eye bushing ' + code + ' ' + label, (0, -0.037, 0), (0, 0.037, 0), 0.022, 'FRONT_SUSPENSION' if code[0] == 'F' else 'REAR_SUSPENSION', rubber, anchor)
        cyl('Shock eye through bolt ' + code + ' ' + label, (0, -0.049, 0), (0, 0.049, 0), 0.012, 'FRONT_SUSPENSION' if code[0] == 'F' else 'REAR_SUSPENSION', alloy, anchor, n=6)
for anchor in (transfer_rear, rear_pinion, transfer_front, front_pinion):
    uv('Universal joint cross ' + anchor.name, (0, 0, 0), (0.05, 0.049, 0.049), 'DRIVETRAIN', steel, anchor)
    cyl('Universal joint bearing ' + anchor.name, (0, -0.058, 0), (0, 0.058, 0), 0.023, 'DRIVETRAIN', alloy, anchor)
for s in (-1, 1):
    vs = []
    fs = []
    n = 2800
    for i in range(n + 1):
        x = -12 + 70 * i / n
        z = ground(x, s * 0.83)
        vs += [(x, s * 0.6, z), (x, s * 1.1, z), (x, s * 1.1, -0.68), (x, s * 0.6, -0.68)]
    for i in range(n):
        for j in range(4):
            fs.append((4 * i + j, 4 * i + (j + 1) % 4, 4 * (i + 1) + (j + 1) % 4, 4 * (i + 1) + j))
    fs += [(3, 2, 1, 0), (4 * n, 4 * n + 1, 4 * n + 2, 4 * n + 3)]
    mesh('Continuous wheel track ' + ('left' if s > 0 else 'right'), vs, fs, 'ROAD', roadmat)
    box('Outer concrete apron ' + str(s), (23, s * 5.05, -0.09), (70, 7.9, 0.18), 'ROAD', roadmat, bev=0.015)
    box('Inspection channel wall ' + str(s), (23, s * 0.565, -0.345), (70, 0.07, 0.67), 'ROAD', roadmat, bev=0.007)
    for i, x in enumerate(range(-10, 57, 4)):
        box('Lane edge marking ' + str(s) + str(i), (x, s * 1.23, 0.004), (1.6, 0.035, 0.005), 'ROAD', accent, bev=0.001)
        box('Apron expansion joint ' + str(s) + str(i), (x, s * 4.7, 0.002), (0.009, 7.1, 0.003), 'ROAD', black, bev=0)
box('Inspection channel floor', (23, 0, -0.725), (70, 1.12, 0.09), 'ROAD', roadmat, bev=0.008)
wallmat = mat('Background | warm light concrete', (0.46, 0.48, 0.47), 0, 0.84)
for x, width, height in [(-8, 12, 3.6), (9, 16, 4.3), (29, 16, 3.7), (49, 13, 4.1)]:
    box('Industrial hall ' + str(x), (x, 12.5, height / 2 - 0.04), (width, 7, height), 'ROAD', wallmat, bev=0.04)
    box('Hall parapet ' + str(x), (x, 12.4, height), (width + 0.1, 7.2, 0.18), 'ROAD', steel, bev=0.02)
    for xx in [x - width * 0.3, x, x + width * 0.3]:
        box('Loading bay ' + str(xx), (xx, 8.972, 1.25), (2.5, 0.026, 2.5), 'ROAD', steel, bev=0.014)
        for z in [0.3 + i * 0.27 for i in range(8)]:
            box('Loading shutter seam ' + str(xx) + str(z), (xx, 8.948, z), (2.44, 0.012, 0.016), 'ROAD', black, bev=0.002)
for s in (-1, 1):
    for x in range(-9, 58, 7):
        box('Safety bollard foot ' + str(s) + str(x), (x, s * 2.3, 0.042), (0.27, 0.27, 0.084), 'ROAD', black, bev=0.024)
        cyl('Safety bollard ' + str(s) + str(x), (x, s * 2.3, 0.075), (x, s * 2.3, 0.62), 0.055, 'ROAD', accent, n=16)
        cyl('Bollard dark band ' + str(s) + str(x), (x, s * 2.3, 0.4), (x, s * 2.3, 0.5), 0.056, 'ROAD', black, n=16)

def camera(name, pos, target, lens=35, parent=None):
    data = bpy.data.cameras.new(name + ' optics')
    data.lens = lens
    data.sensor_width = 36
    data.clip_start = 0.025
    data.clip_end = 300
    data.dof.use_dof = False
    o = bpy.data.objects.new(name, data)
    C['CAMERAS'].objects.link(o)
    if parent:
        o.parent = parent
    o.location = pos
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y')
    return o
cam = camera('CAM_ANIMATION | continuous 10 second inspection', (0, -7, 1), (0, 0, 1), 36)
scene.camera = cam
CAM_KEYS = [(1, (-0.2, -7.9, 1.04), (0, 0, 0.95), 38), (36, (-0.2, -7.9, 1.04), (0, 0, 0.95), 38), (48, (0.15, -7.8, 1.1), (0.05, 0, 0.93), 38), (62, (4.1, -5.9, 1.26), (0.45, 0, 0.86), 36), (70, (5.2, -3.25, 0.93), (0.85, 0, 0.72), 31), (77, (4.35, -0.74, 0.38), (1.15, 0, 0.56), 24), (84, (3.02, -0.02, -0.105), (1.3, 0.05, 0.53), 20), (93, (1.87, 0.01, -0.135), (1.27, 0.19, 0.6), 18), (107, (0.63, 0.01, -0.135), (0.05, 0.2, 0.65), 18), (118, (-0.4, 0.0, -0.135), (-1.07, 0.12, 0.61), 19), (126, (-1.32, -0.06, -0.13), (-1.6, -0.28, 0.52), 20), (135, (-2.35, 0.31, 0.035), (-1.52, -0.48, 0.53), 24), (144, (-2.6, 0.43, 0.28), (-1.51, -0.53, 0.53), 27), (153, (-2.6, 0.43, 0.28), (-1.51, -0.53, 0.53), 27), (183, (-2.6, 0.43, 0.28), (-1.51, -0.53, 0.53), 27), (192, (-2.72, 0.37, 0.36), (-1.48, -0.53, 0.55), 28), (201, (-4.1, -1.74, 0.88), (-0.75, -0.18, 0.82), 32), (214, (-6.65, -3.75, 1.68), (-0.1, 0, 0.95), 35), (240, (-10.5, -5.2, 2.35), (0, 0, 0.96), 38)]

def smooth_path(f, column):
    k = next((i for i in range(len(CAM_KEYS) - 1) if CAM_KEYS[i][0] <= f <= CAM_KEYS[i + 1][0]), len(CAM_KEYS) - 2)
    fs = [p[0] for p in CAM_KEYS]
    vals = [Vector(p[column]) if column in (1, 2) else p[column] for p in CAM_KEYS]

    def tangent(i):
        if i == 0:
            return (vals[1] - vals[0]) / (fs[1] - fs[0])
        if i == len(fs) - 1:
            return (vals[-1] - vals[-2]) / (fs[-1] - fs[-2])
        before = (vals[i] - vals[i - 1]) / (fs[i] - fs[i - 1])
        after = (vals[i + 1] - vals[i]) / (fs[i + 1] - fs[i])
        if column in (1, 2):
            if before.length < 1e-06 or after.length < 1e-06:
                return Vector((0, 0, 0))
        elif abs(before) < 1e-06 or abs(after) < 1e-06:
            return 0
        return (before + after) * 0.5
    dt = fs[k + 1] - fs[k]
    u = (f - fs[k]) / dt
    return (2 * u ** 3 - 3 * u * u + 1) * vals[k] + (u ** 3 - 2 * u * u + u) * dt * tangent(k) + (-2 * u ** 3 + 3 * u * u) * vals[k + 1] + (u ** 3 - u * u) * dt * tangent(k + 1)
lastq = None
camera_samples = []
for f in range(1, 241):
    distance = (f - 1) * 3 / 24
    pos = smooth_path(f, 1) + Vector((distance, 0, 0))
    aim = smooth_path(f, 2) + Vector((distance, 0, 0))
    q = (aim - pos).to_track_quat('-Z', 'Y')
    if lastq and q.dot(lastq) < 0:
        q.negate()
    cam.location = pos
    cam.rotation_quaternion = q
    cam.data.lens = smooth_path(f, 3)
    cam.keyframe_insert(data_path='location', frame=f)
    cam.keyframe_insert(data_path='rotation_quaternion', frame=f)
    cam.data.keyframe_insert(data_path='lens', frame=f)
    camera_samples.append({'frame': f, 'position': list(pos), 'target': list(aim), 'lens_mm': cam.data.lens})
    lastq = q.copy()
camera('INSPECT_01_FULL_TRUCK', (6.7, -7.4, 3.5), (0, 0, 0.95), 48, root)
camera('INSPECT_02_UNDERSIDE_OVERVIEW', (0.2, -0.07, -0.38), (-0.15, 0.08, 0.67), 14, root)
camera('INSPECT_03_FRONT_SUSPENSION', (2.8, -0.35, 0.3), (1.58, -0.56, 0.57), 43, root)
camera('INSPECT_04_REAR_RIGHT_SUSPENSION', (-2.6, 0.43, 0.28), (-1.51, -0.53, 0.53), 27, root)
path = tube('GUIDE | camera trajectory', [r['position'] for r in camera_samples], 0.009, 'CAMERAS', accent)
path.hide_render = True
path.hide_set(True)
for f, label in [(1, '01 • PROFILE / 0 s'), (49, '02 • FRONT ARC / 2 s'), (85, '03 • UNDERCARRIAGE / 3.5 s'), (145, '04 • REAR RIGHT / 6 s'), (165, 'RR BUMP CREST'), (193, '05 • REAR PULLAWAY / 8 s'), (240, 'END / 10 s output')]:
    scene.timeline_markers.new(label, frame=f)

def area(name, loc, target, power, color, size, parent=None):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.color = color
    data.shape = 'DISK'
    data.size = size
    o = bpy.data.objects.new(name, data)
    C['LIGHTS'].objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if parent:
        o.parent = parent
    return o
area('Daylight | broad soft key', (13, -7, 11), (16, 0, 0), 3300, (1, 0.9, 0.77), 10)
area('Daylight | sky fill', (18, 8, 8), (18, 0, 0), 2400, (0.72, 0.84, 1), 12)
data = bpy.data.lights.new('Sun | soft afternoon', 'SUN')
data.energy = 1.5
data.angle = math.radians(18)
o = bpy.data.objects.new('Sun | soft afternoon', data)
C['LIGHTS'].objects.link(o)
o.rotation_euler = (0.38, -0.45, -0.38)
area('Inspection fill | front', (1.12, -0.3, -0.32), (1.4, 0, 0.55), 95, (0.76, 0.87, 1), 1.1, root)
area('Inspection fill | driveline', (-0.12, 0.22, -0.35), (-0.1, 0, 0.64), 110, (0.83, 0.91, 1), 1.25, root)
area('Inspection fill | rear-right', (-2.6, -0.25, 0.04), (-1.45, -0.52, 0.53), 75, (1, 0.88, 0.7), 0.8, root)
area('Rear chassis rim', (-2.2, 0.28, -0.29), (-1.6, 0, 0.55), 75, (0.76, 0.86, 1), 0.75, root)
for act in bpy.data.actions:
    if hasattr(act, 'layers'):
        for layer in act.layers:
            for strip in layer.strips:
                for slot in act.slots:
                    try:
                        bag = strip.channelbag(slot)
                    except Exception:
                        continue
                    if bag:
                        for fc in bag.fcurves:
                            for k in fc.keyframe_points:
                                k.interpolation = 'LINEAR'
scene['project'] = 'KESTREL / original crew-cab expedition pickup'
scene['build_notes'] = 'Original local bpy geometry. Deterministic road-contact rig. No renders have been executed. No downloaded or paid assets.'
scene['rig_simplifications'] = 'Kinematic wheel travel; small wishbone length accommodation; fixed leaf eyes with parabolic leaf flex; universal joints aim shafts without spline plunge detail; rigid undeformed tire carcasses; forward rolling distance on X; no full rigid-body simulation.'
scene['nominal_dimensions_m'] = '5.3 body length; 1.9 body/tire width; 1.85 cab roof; 3.2 wheelbase. Mirrors/hitch/roof rails extend envelope.'
scene['camera_route'] = 'Two continuous road tracks flank a 1.06 m clear recessed channel. Lens scans from -0.14 m before exiting behind the axle into a rear/inboard view.'
scene['construction_elapsed_seconds'] = round(time.perf_counter() - START, 3)
for me in bpy.data.meshes:
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    me.update()
scene.frame_set(1)
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type == 'VIEW_3D':
            sp = ar.spaces.active
            sp.clip_start = 0.01
            sp.clip_end = 300
            sp.lens = 48
            sp.shading.type = 'SOLID'
            sp.shading.light = 'STUDIO'
            sp.shading.color_type = 'MATERIAL'
            sp.shading.show_shadows = True
            sp.shading.show_cavity = True
            sp.overlay.show_extras = False
            sp.overlay.show_relationship_lines = False
            sp.overlay.show_floor = False
            sp.overlay.show_axis_x = False
            sp.overlay.show_axis_y = False
            rv = sp.region_3d
            rv.view_distance = 7.2
            rv.view_location = (0, 0, 0.9)
            rv.view_rotation = Vector((6.7, -7.4, 3.5)).to_track_quat('Z', 'Y')
            rv.view_perspective = 'PERSP'
for o in bpy.context.selected_objects:
    o.select_set(False)
root.select_set(True)
bpy.context.view_layer.objects.active = root
text = bpy.data.texts.new('README | START HERE')
text.write('KESTREL 4x4 — 10 s / 24 fps / 1920x1080\n\nOpen README.md beside this scene for controls, verified results and limitations.\nActive camera: CAM_ANIMATION. Four INSPECT cameras follow vehicle travel.\nSelect CTRL_VEHICLE_TRAVEL for travel, steering and body controls.\nEach CTRL_SUSPENSION_* has an animated travel_m control.\nAll mechanical motion evaluates through native drivers, constraints and shape keys.\nAnimation is baked at 240 frames; no external runtime scripts needed.\nNo rendering performed.\n')
bpy.ops.file.pack_all()
"""Extend accepted v1 with engine-bay opening, hood closure and a second moving rear inspection.
Run in Blender. Loads v1 read-only, saves pickup_truck_v2.blend. Never renders.
"""
START = time.perf_counter()
scene = bpy.context.scene
root = bpy.data.objects['CTRL_VEHICLE_TRAVEL']
body = bpy.data.objects['CTRL_BODY_HEAVE_PITCH_ROLL']
rear = bpy.data.objects['RIG_REAR_SOLID_AXLE']
cam = scene.camera
C = {c.name: c for c in bpy.data.collections}
M = {m.name: m for m in bpy.data.materials}
paint = M['Paint | satin forest green']
black = M['Trim | charcoal polymer']
steel = M['Frame | graphite powdercoat']
alloy = M['Metal | brushed aluminium']
chrome = M['Metal | polished damper shafts']
rubber = M['Rubber | restrained road wear']
brake = M['Caliper | oxblood coating']
accent = M['Details | warm nickel']
leafmat = M['Leaf springs | manganese steel']
amber = M['Lens | warm amber']
R = 0.405
TRACK = 1.66
INTRO = 132
EXTRA = 126
END = 498
controls = {c: bpy.data.objects['CTRL_SUSPENSION_' + c] for c in ['FL', 'FR', 'RL', 'RR']}
original = []
for f in range(1, 241):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    original.append({'frame': f, 'travel': root['travel_m'], 'camera_relative': list(cam.location - Vector((root['travel_m'], 0, 0))), 'rotation': list(cam.rotation_quaternion), 'lens': cam.data.lens})
print('V1_INSPECTED', len(scene.objects), 'objects', scene.frame_end, 'frames; SHA256', base_hash, flush=True)
scene.frame_set(1)
for o in [root, *controls.values(), cam, cam.data]:
    if o.animation_data:
        o.animation_data.action = None
cam.name = 'CAM_ANIMATION_V2 | engine and dual rear inspection'
scene.name = 'KESTREL v2 | engine bay and moving rear suspension'
scene.frame_start = 1
scene.frame_end = END
scene.render.filepath = '//renders/kestrel_v2_'
BUMPS = [(2.7, 0.048, 1.6), (6.4, 0.06, 1.9), (10.8, 0.047, 1.6), (14.7, 0.055, 2.0), (18.9, 0.082, 1.8), (20.9, 0.064, 1.7), (25.5, 0.058, 1.9), (30.0, 0.082, 1.9), (32.25, 0.074, 1.9), (35.1, 0.055, 1.8)]

def ground(x, y):
    z = 0
    for i, (c, h, w) in enumerate(BUMPS):
        if y > 0:
            c += 0.32
            h *= 0.5 if i in (4, 5) else 0.76
        u = (x - c) / (w / 2)
        if abs(u) < 1:
            z += h * (0.5 + 0.5 * cos(pi * u))
    return z

def contact_height(x, y):
    return max((ground(x + R * (-1 + 2 * i / 160), y) + R * sqrt(max(0, 1 - (-1 + 2 * i / 160) ** 2)) for i in range(161)))

def distance_at(f):
    if f <= 109:
        return -1.5
    if f < 133:
        u = (f - 109) / 24
        return -1.5 + 3 * (u ** 3 - 0.5 * u ** 4)
    return (f - 133) * 3 / 24

def pose_at(d):
    wh = {a + s: contact_height(d + x, y) - R for a, x in [('F', 1.6), ('R', -1.6)] for s, y in [('L', 0.83), ('R', -0.83)]}
    avg = {}
    for code in wh:
        x = 1.6 if code[0] == 'F' else -1.6
        y = 0.83 if code[1] == 'L' else -0.83
        avg[code] = sum(((1 - abs(k) / 9) * (contact_height(d + x + k * 0.13, y) - R) for k in range(-8, 9))) / 9
    h = sum(avg.values()) / 4 * 0.72
    pitch = -(avg['FL'] + avg['FR'] - avg['RL'] - avg['RR']) / 2 / 3.2 * 0.35
    roll = (avg['FL'] + avg['RL'] - avg['FR'] - avg['RR']) / 2 / TRACK * 0.3
    return (h, math.degrees(pitch), math.degrees(roll), {c: z - h for c, z in wh.items()})
for s in (-1, 1):
    road = bpy.data.objects['Continuous wheel track ' + ('left' if s > 0 else 'right')]
    for v in road.data.vertices:
        if v.co.z > -0.1:
            v.co.z = ground(v.co.x, s * 0.83)
    road.data.update()
hood = bpy.data.objects['Hood | crowned one-piece pressing']
pivot = Vector((1.08, 0, 1.305))
for v in hood.data.vertices:
    if v.co.x < 1.0:
        v.co.x = 1.07
hinge = empty('CTRL_HOOD_OPEN', pivot, body, size=0.2)
prop(hinge, 'open_deg', 68, 0, 75, 'Hood rotation about its rear hinge; 0 is fully latched.')
driver(hinge, 'rotation_euler', 1, '-a*pi/180', [pvar('a', hinge, 'open_deg')])

def hood_parent(o):
    o.parent = hinge
    o.matrix_parent_inverse = Matrix.Translation(-pivot)
    return o
hood_parent(hood)

def hood_under_z(x):
    sec = [(1.07, 1.245), (1.13, 1.31), (2.3, 1.245), (2.56, 1.145)]
    for (a, za), (b, zb) in zip(sec, sec[1:]):
        if a <= x <= b:
            return za + (zb - za) * (x - a) / (b - a)
    return sec[0][1] if x < 0.91 else sec[-1][1]
for x in [1.15, 1.43, 1.75, 2.08, 2.18]:
    hood_parent(box('Hood underside pressed rib ' + str(x), (x, 0, hood_under_z(x) - 0.011), (0.055, 1.43, 0.02), 'BODY', paint, bev=0.008))
verts = []
faces = []
for x in [1.12, 1.35, 1.75, 2.14, 2.24]:
    for y in (-0.65, 0.65):
        verts.append((x, y, hood_under_z(x) - 0.021))
for i in range(4):
    faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
pad = mesh('Hood heat and acoustic liner', verts, faces, 'BODY', rubber)
pad.modifiers.new('Insulation pad thickness', 'SOLIDIFY').thickness = 0.009
hood_parent(pad)
for s in (-1, 1):
    y = s * 0.64
    box('Hood fixed hinge bracket ' + str(s), (1.079, y, 1.281), (0.105, 0.08, 0.034), 'BODY', steel, body, 0.008)
    cyl('Hood hinge pin ' + str(s), (1.08, y - 0.051, 1.305), (1.08, y + 0.051, 1.305), 0.014, 'BODY', chrome, body, n=16)
    hood_parent(box('Hood moving hinge arm ' + str(s), (1.158, y, 1.298), (0.175, 0.037, 0.016), 'BODY', alloy, bev=0.006))
    low = empty('Hood strut body anchor ' + str(s), (1.0, s * 0.775, 1.07), body)
    high = empty('Hood strut lid anchor ' + str(s), Vector((1.63, s * 0.78, 1.285)) - pivot, hinge)
    dynamic_rod('Hood gas strut outer ' + str(s), low, high, 0.02, 'BODY', black, 0.51)
    dynamic_rod('Hood gas strut sliding rod ' + str(s), high, low, 0.008, 'BODY', chrome)
    for a, label in [(low, 'lower'), (high, 'upper')]:
        uv('Hood strut ball joint ' + str(s) + label, (0, 0, 0), (0.023, 0.019, 0.023), 'BODY', alloy, a)
    box('Hood strut lower bracket ' + str(s), (1.0, s * 0.796, 1.063), (0.07, 0.058, 0.051), 'BODY', steel, body, 0.007)
hood_parent(tube('Hood latch striker', [(2.46, -0.037, 1.169), (2.46, -0.037, 1.127), (2.46, 0.037, 1.127), (2.46, 0.037, 1.169)], 0.007, 'BODY', alloy))
box('Hood latch receiver', (2.514, 0, 1.157), (0.08, 0.132, 0.046), 'BODY', steel, body, 0.012)
service = mat('V2 | yellow service caps', (0.69, 0.42, 0.05), 0.16, 0.36)
reservoir = mat('V2 | molded fluid reservoir', (0.58, 0.63, 0.57), 0, 0.48)
wiremat = mat('V2 | red cable insulation', (0.28, 0.018, 0.01), 0, 0.57)
for s in (-1, 1):
    rr = 0.525
    y = s * 0.675
    poly = [(0.96, 0.62), (0.96, 1.225), (2.35, 1.225), (2.35, 0.62), (1.6 + rr, 0.62), (1.6 + rr, R)]
    poly += [(1.6 + rr * cos(i * pi / 32), R + rr * sin(i * pi / 32)) for i in range(33)]
    poly += [(1.6 - rr, 0.62)]
    vs = [(x, yy, z) for yy in (y - 0.006, y + 0.006) for x, z in poly]
    n = len(poly)
    fs = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    mesh('Engine bay inner wheelhouse ' + str(s), vs, fs, 'BODY', black, body, 0.004)
    tube('Fender mounting lip ' + str(s), [(0.99, s * 0.77, 1.21), (1.5, s * 0.77, 1.25), (2.33, s * 0.74, 1.2)], 0.016, 'BODY', paint, body)
    for x in [1.05, 1.32, 1.98, 2.3]:
        z = 1.21 + (x - 0.99) / 0.51 * 0.04 if x <= 1.5 else 1.25 - (x - 1.5) / 0.83 * 0.05
        cyl('Fender flange screw ' + str(s) + str(x), (x, s * 0.771, z + 0.013), (x, s * 0.771, z + 0.024), 0.009, 'BODY', alloy, body, n=6)
box('Battery tray', (1.12, -0.595, 1.0), (0.35, 0.31, 0.025), 'DRIVETRAIN', steel, body, 0.009)
box('Engine bay battery', (1.12, -0.595, 1.106), (0.3, 0.25, 0.188), 'DRIVETRAIN', black, body, 0.017)
box('Battery lid', (1.12, -0.595, 1.207), (0.31, 0.26, 0.02), 'DRIVETRAIN', steel, body, 0.007)
for xx, ma in [(1.02, wiremat), (1.22, black)]:
    cyl('Battery terminal ' + str(xx), (xx, -0.565, 1.216), (xx, -0.565, 1.239), 0.014, 'DRIVETRAIN', alloy, body)
    box('Battery terminal cover ' + str(xx), (xx, -0.565, 1.236), (0.058, 0.059, 0.019), 'DRIVETRAIN', ma, body, 0.008)
for y in (-0.694, -0.496):
    cyl('Battery hold-down rod ' + str(y), (1.12, y, 1.015), (1.12, y, 1.222), 0.005, 'DRIVETRAIN', alloy, body)
box('Battery hold-down bridge', (1.12, -0.595, 1.225), (0.027, 0.26, 0.012), 'DRIVETRAIN', steel, body, 0.003)
box('Engine fuse and relay box', (1.07, -0.388, 1.164), (0.185, 0.126, 0.09), 'DRIVETRAIN', black, body, 0.013)
box('Air filter box', (2.035, 0.566, 1.111), (0.31, 0.322, 0.222), 'DRIVETRAIN', black, body, 0.036)
box('Air filter lid', (2.035, 0.566, 1.227), (0.317, 0.326, 0.025), 'DRIVETRAIN', steel, body, 0.01)
for x in [1.93, 2.035, 2.14]:
    box('Airbox molded lid ridge ' + str(x), (x, 0.566, 1.244), (0.016, 0.25, 0.008), 'DRIVETRAIN', black, body, 0.003)
for y in (0.422, 0.711):
    box('Airbox retaining clip ' + str(y), (2.035, y, 1.205), (0.036, 0.019, 0.069), 'DRIVETRAIN', alloy, body, 0.004)
tube('Engine intake duct', [(1.945, 0.437, 1.165), (1.8, 0.449, 1.159), (1.66, 0.438, 1.137), (1.59, 0.35, 1.108)], 0.047, 'DRIVETRAIN', black, body)
for x in [1.8, 1.84, 1.88]:
    cyl('Intake flexible bellows ' + str(x), (x - 0.009, 0.449, 1.159), (x + 0.009, 0.449, 1.159), 0.052, 'DRIVETRAIN', rubber, body, n=24)
box('Coolant expansion reservoir', (1.24, 0.566, 1.139), (0.2, 0.21, 0.158), 'DRIVETRAIN', reservoir, body, 0.042)
cyl('Coolant pressure cap', (1.24, 0.566, 1.218), (1.24, 0.566, 1.244), 0.035, 'DRIVETRAIN', black, body, n=12)
box('Brake master fluid reservoir', (0.994, 0.415, 1.155), (0.13, 0.17, 0.095), 'DRIVETRAIN', reservoir, body, 0.023)
cyl('Brake fluid cap', (0.994, 0.415, 1.205), (0.994, 0.415, 1.222), 0.026, 'DRIVETRAIN', black, body, n=12)
tube('Upper radiator coolant hose', [(2.293, -0.4, 1.185), (2.15, -0.4, 1.191), (1.95, -0.37, 1.17), (1.83, -0.24, 1.142)], 0.031, 'DRIVETRAIN', rubber, body)
tube('Expansion reservoir small hose', [(1.24, 0.46, 1.135), (1.36, 0.41, 1.18), (1.5, 0.35, 1.21), (1.76, 0.28, 1.15)], 0.009, 'DRIVETRAIN', rubber, body)
cyl('Radiator filler neck', (2.33, 0.46, 1.215), (2.33, 0.46, 1.245), 0.024, 'DRIVETRAIN', alloy, body)
cyl('Radiator pressure cap', (2.33, 0.46, 1.241), (2.33, 0.46, 1.256), 0.035, 'DRIVETRAIN', steel, body, n=12)
for i, x in enumerate([1.36, 1.51, 1.66, 1.81]):
    box('Ignition coil ' + str(i + 1), (x, 0, 1.296), (0.089, 0.133, 0.039), 'DRIVETRAIN', black, body, 0.012)
    box('Ignition coil plug ' + str(i + 1), (x, -0.091, 1.294), (0.038, 0.039, 0.031), 'DRIVETRAIN', steel, body, 0.006)
    tube('Ignition coil wire ' + str(i + 1), [(x, -0.11, 1.294), (x - 0.04, -0.145, 1.287), (x - 0.04, -0.19, 1.265)], 0.005, 'DRIVETRAIN', rubber, body)
    cyl('Fuel injector ' + str(i + 1), (x, 0.17, 1.195), (x, 0.21, 1.245), 0.014, 'DRIVETRAIN', steel, body)
tube('Engine wiring loom', [(1.12, -0.38, 1.165), (1.2, -0.22, 1.265), (1.82, -0.19, 1.265), (1.93, -0.28, 1.14)], 0.012, 'DRIVETRAIN', rubber, body)
tube('Common fuel rail', [(1.29, 0.215, 1.241), (1.89, 0.215, 1.241)], 0.013, 'DRIVETRAIN', alloy, body)
cyl('Oil filler cap', (1.38, 0.11, 1.283), (1.38, 0.11, 1.305), 0.033, 'DRIVETRAIN', black, body, n=12)
tube('Dipstick tube', [(1.81, -0.23, 0.85), (1.86, -0.27, 1.05), (1.86, -0.28, 1.205)], 0.007, 'DRIVETRAIN', alloy, body)
tube('Dipstick handle', [(1.86 + 0.018 * cos(i * 2 * pi / 24), -0.28, 1.228 + 0.023 * sin(i * 2 * pi / 24)) for i in range(24)], 0.005, 'DRIVETRAIN', service, body, True)
tube('Battery positive cable', [(1.02, -0.565, 1.236), (0.977, -0.57, 1.21), (0.975, -0.46, 1.188), (1.0, -0.388, 1.177)], 0.008, 'DRIVETRAIN', wiremat, body)
tube('Battery ground cable', [(1.22, -0.565, 1.236), (1.27, -0.55, 1.205), (1.28, -0.66, 1.151)], 0.008, 'DRIVETRAIN', rubber, body)
engine_ctrl = empty('CTRL_ENGINE_ACCESSORIES', parent=body)
prop(engine_ctrl, 'demonstration_rpm', 60, 0, 600, 'Illustrative accessory speed; slowed for readable 24 fps inspection, not engine combustion RPM.')
prop(engine_ctrl, 'fan_rpm', 90, 0, 600, 'Cooling fan demonstration speed.')
pulleys = [('Crank', 0, 0.89, 0.104), ('Alternator', -0.247, 1.125, 0.052), ('Water pump', 0.192, 1.102, 0.061)]
for name, y, z, r in pulleys:
    p = empty('RIG_ENGINE_PULLEY_' + name, (2.063, y, z), body)
    driver(p, 'rotation_euler', 0, f'frame/24*rpm*2*pi/60*{0.104 / r}', [pvar('rpm', engine_ctrl, 'demonstration_rpm')])
    ob = ring_y('Accessory pulley grooved rim ' + name, [(-0.015, r * 0.75), (-0.015, r), (-0.006, r + 0.003), (0.006, r + 0.003), (0.015, r), (0.015, r * 0.75)], 'DRIVETRAIN', steel, p, 48)
    ob.rotation_euler.z = -pi / 2
    cyl('Accessory pulley hub ' + name, (-0.019, 0, 0), (0.024, 0, 0), r * 0.25, 'DRIVETRAIN', alloy, p, n=20)
    for k in range(5):
        a = k * 2 * pi / 5
        cyl('Accessory pulley spoke ' + name + str(k), (0, r * 0.2 * cos(a), r * 0.2 * sin(a)), (0, r * 0.83 * cos(a), r * 0.83 * sin(a)), 0.009, 'DRIVETRAIN', steel, p, n=12)
    cyl('Accessory shaft mount ' + name, (1.945, y, z), (2.046, y, z), 0.024, 'DRIVETRAIN', alloy, body)
    uv('Pulley balance marker ' + name, (0.019, r * 0.64, 0), (0.003, 0.007, 0.007), 'DRIVETRAIN', accent, p)
cyl('Alternator cast housing', (1.864, -0.247, 1.125), (2.016, -0.247, 1.125), 0.083, 'DRIVETRAIN', alloy, body, n=32)
for x in [1.88, 1.91, 1.94, 1.97]:
    cyl('Alternator cooling rib ' + str(x), (x - 0.005, -0.247, 1.125), (x + 0.005, -0.247, 1.125), 0.087, 'DRIVETRAIN', steel, body, n=24)
pts = sorted(set(((y + (r + 0.004) * cos(i * 2 * pi / 64), z + (r + 0.004) * sin(i * 2 * pi / 64)) for _, y, z, r in pulleys for i in range(64))))

def cross2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
lo = []
hi = []
for p in pts:
    while len(lo) >= 2 and cross2(lo[-2], lo[-1], p) <= 0:
        lo.pop()
    lo.append(p)
for p in reversed(pts):
    while len(hi) >= 2 and cross2(hi[-2], hi[-1], p) <= 0:
        hi.pop()
    hi.append(p)
belt_path = lo[:-1] + hi[:-1]
N = len(belt_path)
vs = []
fs = []
for i, (y, z) in enumerate(belt_path):
    before = Vector(belt_path[(i - 1) % N])
    after = Vector(belt_path[(i + 1) % N])
    t = (after - before).normalized()
    normal = Vector((t.y, -t.x))
    for xx, offset in [(-0.013, -0.003), (0.013, -0.003), (0.013, 0.003), (-0.013, 0.003)]:
        vs.append((2.063 + xx, y + normal.x * offset, z + normal.y * offset))
for i in range(N):
    for k in range(4):
        fs.append((4 * i + k, 4 * i + (k + 1) % 4, 4 * ((i + 1) % N) + (k + 1) % 4, 4 * ((i + 1) % N) + k))
mesh('Engine serpentine belt | tangent continuous loop', vs, fs, 'DRIVETRAIN', rubber, body, 0.0006)
lengths = [(Vector(belt_path[(i + 1) % N]) - Vector(belt_path[i])).length for i in range(N)]
belt_length = sum(lengths)

def belt_position(d):
    d = d % belt_length
    for i, L in enumerate(lengths):
        if d <= L:
            a = Vector(belt_path[i])
            b = Vector(belt_path[(i + 1) % N])
            q = a + (b - a) * (d / L)
            t = (b - a).normalized()
            return (q, t)
        d -= L
    return (Vector(belt_path[0]), Vector((1, 0)))
belt_ribs = [box('Moving belt molded timing rib ' + str(i), (0, 0, 0), (0.027, 0.004, 0.004), 'DRIVETRAIN', steel, body, 0.001) for i in range(7)]
fan = empty('RIG_ENGINE_COOLING_FAN', (2.201, 0, 1.025), body)
driver(fan, 'rotation_euler', 0, 'frame/24*rpm*2*pi/60', [pvar('rpm', engine_ctrl, 'fan_rpm')])
cyl('Cooling fan hub', (-0.022, 0, 0), (0.021, 0, 0), 0.044, 'DRIVETRAIN', black, fan, n=24)
for k in range(5):
    a = k * 2 * pi / 5
    verts = []
    blade = [(0.041, a - 0.1), (0.163, a + 0.02), (0.172, a + 0.29), (0.063, a + 0.48)]
    for xx in (-0.007, 0.007):
        for r, ang in blade:
            verts.append((xx + 0.024 * (r - 0.041), r * cos(ang), r * sin(ang)))
    mesh('Swept cooling fan blade ' + str(k), verts, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], 'DRIVETRAIN', black, fan, 0.002)
shroud = ring_y('Cooling fan protective shroud', [(-0.022, 0.185), (-0.022, 0.207), (0.022, 0.207), (0.022, 0.185)], 'DRIVETRAIN', black, body, 64)
shroud.rotation_euler.z = -pi / 2
shroud.location = (2.241, 0, 1.025)
for y in (-0.27, 0.27):
    box('Cooling shroud radiator bracket ' + str(y), (2.271, y, 1.025), (0.043, 0.12, 0.042), 'DRIVETRAIN', steel, body, 0.006)
shackles = {}
for s, code in [(1, 'RL'), (-1, 'RR')]:
    y = s * 0.57
    L = 0.13
    a0 = math.radians(8)
    top = Vector((-2.46 + L * sin(a0), y, 0.605 + L * cos(a0)))
    for o in list(bpy.data.objects):
        if o.name.startswith('Rear shackle ') and (o.name.startswith('Rear shackle bushing ' + str(s)) or o.name.startswith('Rear shackle through bolt ' + str(s)) or o.name.startswith('Rear shackle mounting cheek ' + str(s))):
            bpy.data.objects.remove(o, do_unlink=True)
    ctrl = empty('RIG_REAR_SHACKLE_' + code, top, body)
    fc = ctrl.driver_add('rotation_euler', 1)
    d = fc.driver
    d.expression = '8*pi/180+(z-.31)*3.4'
    v = d.variables.new()
    v.name = 'z'
    v.type = 'TRANSFORMS'
    v.targets[0].id = bpy.data.objects['Leaf local deformation target ' + code]
    v.targets[0].transform_type = 'LOC_Z'
    v.targets[0].transform_space = 'LOCAL_SPACE'
    end = empty('Rear moving leaf eye ' + code, (0, 0, -L), ctrl)
    target = empty('Rear leaf eye body-local target ' + code, (-2.46, y, 0.605), body)
    con = target.constraints.new('COPY_LOCATION')
    con.target = end
    shackles[code] = (ctrl, end, target)
    for yy in (-0.052, 0.052):
        box('Moving shackle side plate ' + code + str(yy), (0, yy, -L / 2), (0.047, 0.013, L + 0.035), 'REAR_SUSPENSION', alloy, ctrl, 0.012)
    for anchor, label in [(ctrl, 'upper'), (end, 'lower')]:
        cyl('Shackle elastomer bushing ' + code + label, (0, -0.042, 0), (0, 0.042, 0), 0.028, 'REAR_SUSPENSION', rubber, anchor, n=24)
        cyl('Shackle shoulder bolt ' + code + label, (0, -0.07, 0), (0, 0.07, 0), 0.013, 'REAR_SUSPENSION', steel, anchor, n=6)
    box('Shackle fixed clevis base ' + code, top + Vector((0, -s * 0.045, 0.026)), (0.113, 0.175, 0.045), 'REAR_SUSPENSION', steel, body, 0.01)
    for layer in range(1, 6):
        o = bpy.data.objects['Leaf pack ' + code + ' lamination ' + str(layer)]
        basis = o.data.shape_keys.key_blocks[0]
        for axis, label, rest in [(0, 'Rear shackle eye X', -2.46), (2, 'Rear shackle eye Z', 0.605)]:
            k = o.shape_key_add(name=label, from_mix=False)
            k.slider_min = -2
            k.slider_max = 2
            for i, p in enumerate(k.data):
                u = basis.data[i].co.x + 1.6
                w = max(0, -u / 0.86) ** 3
                p.co[axis] += 0.05 * w
            fc = k.driver_add('value')
            d = fc.driver
            d.expression = f'(v-({rest}))/.05'
            var = d.variables.new()
            var.name = 'v'
            var.type = 'TRANSFORMS'
            var.targets[0].id = target
            var.targets[0].transform_type = 'LOC_' + ('X' if axis == 0 else 'Z')
            var.targets[0].transform_space = 'LOCAL_SPACE'
    cyl('Progressive axle bump stop ' + code, (-1.6, s * 0.48, 0.63), (-1.6, s * 0.48, 0.574), 0.038, 'REAR_SUSPENSION', rubber, body, n=24, r2=0.028)
    cyl('Bump stop retaining washer ' + code, (-1.6, s * 0.48, 0.628), (-1.6, s * 0.48, 0.636), 0.043, 'REAR_SUSPENSION', alloy, body, n=24)
shaft = bpy.data.objects['Rear driveshaft | articulated']
transfer = bpy.data.objects['Joint transfer rear']
pinion = bpy.data.objects['Joint rear pinion']
shaft_spin = empty('RIG_REAR_PROPSHAFT_ROTATION', parent=shaft)
driver(shaft_spin, 'rotation_euler', 2, 'd/.405*3.73', [pvar('d', root, 'travel_m')])
for a in (0, pi):
    verts = []
    for z in (0.36, 0.46):
        for i in range(8):
            ang = a - 0.16 + 0.32 * i / 7
            verts.append((0.0387 * cos(ang), 0.0387 * sin(ang), z))
    mesh('Rotating prop shaft witness band ' + str(a), verts, [(i, i + 1, i + 9, i + 8) for i in range(7)], 'DRIVETRAIN', accent, shaft_spin)
sleeve = dynamic_rod('Rear driveshaft slip sleeve', transfer, pinion, 0.046, 'DRIVETRAIN', steel, 0.185)
for start, end, label in [(transfer, pinion, 'transfer'), (pinion, transfer, 'pinion')]:
    orient = empty('RIG_PROPSHAFT_YOKE_' + label)
    co = orient.constraints.new('COPY_LOCATION')
    co.target = start
    co = orient.constraints.new('DAMPED_TRACK')
    co.target = end
    co.track_axis = 'TRACK_Z'
    rotor = empty('Rotating universal joint ' + label, parent=orient)
    driver(rotor, 'rotation_euler', 2, ('' if label == 'transfer' else '-') + 'd/.405*3.73', [pvar('d', root, 'travel_m')])
    cyl('Prop shaft flange ' + label, (0, 0, -0.016), (0, 0, 0.002), 0.062, 'DRIVETRAIN', alloy, rotor, n=32)
    for sign in (-1, 1):
        box('Universal yoke ear ' + label + str(sign), (sign * 0.041, 0, 0.029), (0.018, 0.051, 0.065), 'DRIVETRAIN', steel, rotor, 0.008)
    cyl('Universal joint trunnion ' + label, (-0.053, 0, 0.037), (0.053, 0, 0.037), 0.018, 'DRIVETRAIN', alloy, rotor, n=16)
    for k in range(4):
        a = k * pi / 2
        cyl('Prop flange bolt ' + label + str(k), (0.049 * cos(a), 0.049 * sin(a), -0.02), (0.049 * cos(a), 0.049 * sin(a), 0.005), 0.009, 'DRIVETRAIN', steel, rotor, n=6)
for f in range(1, END + 1):
    d = distance_at(f)
    h, p, r, q = pose_at(d)
    for k, v in [('travel_m', d), ('body_heave_m', h), ('body_pitch_deg', p), ('body_roll_deg', r), ('steering_deg', 0)]:
        keyprop(root, k, v, f)
    for c, v in q.items():
        keyprop(controls[c], 'travel_m', v, f)
    hood_angle = 68 if f <= 84 else 68 * (0.5 + 0.5 * cos(pi * min(1, (f - 84) / 24))) if f < 108 else 0
    keyprop(hinge, 'open_deg', hood_angle, f)
    belt_speed = 60 / 60 * 2 * pi * 0.104
    for i, o in enumerate(belt_ribs):
        p, t = belt_position(f / 24 * belt_speed + i * belt_length / len(belt_ribs))
        o.location = (2.063, p.x, p.y)
        o.rotation_euler.x = atan2(t.y, t.x)
        o.keyframe_insert(data_path='location', frame=f)
        o.keyframe_insert(data_path='rotation_euler', frame=f)
block = bpy.data.objects['Engine | inline four cast block']
block.scale.z *= 0.355 / 0.42
block.location.z -= 0.0325
for name in ['Engine cylinder head', 'Engine valve cover']:
    bpy.data.objects[name].location.z -= 0.065
for o in bpy.data.objects:
    if any((o.name.startswith(p) for p in ['Ignition coil ', 'Ignition coil plug ', 'Ignition coil wire ', 'Fuel injector ', 'Common fuel rail', 'Oil filler cap'])):
        o.location.z -= 0.065
loom = bpy.data.objects['Engine wiring loom']
for point in list(loom.data.splines[0].points)[1:]:
    point.co.z -= 0.065
for o in bpy.data.objects:
    if any((o.name.startswith(p) for p in ['Air filter box', 'Air filter lid', 'Airbox molded lid ridge', 'Airbox retaining clip'])):
        o.location += Vector((0.07, -0.09, -0.025))
for o in bpy.data.objects:
    if o.name.startswith('Battery ') or o.name == 'Engine bay battery':
        o.location += Vector((0.13, 0.08, 0))
bpy.data.objects['Battery ground cable'].data.splines[0].points[-1].co.y = -0.749
cyl('Electrical ground lug bolt', (1.41, -0.662, 1.151), (1.41, -0.68, 1.151), 0.009, 'DRIVETRAIN', alloy, body, n=6)
bpy.data.objects['Engine fuse and relay box'].location.y += 0.077
for name in ['Coolant expansion reservoir', 'Coolant pressure cap']:
    bpy.data.objects[name].location.y -= 0.025
bpy.data.objects['Engine intake duct'].data.splines[0].points[0].co.x = 1.97
for name in ['Radiator filler neck', 'Radiator pressure cap']:
    bpy.data.objects[name].location.x -= 0.07
    bpy.data.objects[name].location.z -= 0.019
tube('Radiator filler neck elbow', [(2.33, 0.46, 1.2), (2.26, 0.46, 1.208)], 0.021, 'DRIVETRAIN', alloy, body)
for v in pad.data.vertices:
    v.co.y *= 0.33 / 0.65
    v.co.z += 0.017
pad.modifiers['Insulation pad thickness'].offset = 1
INTRO_KEYS = [(1, (3.24, -1.68, 2.4), (1.63, -0.08, 1.16), 38), (48, (3.18, -1.59, 2.38), (1.63, -0.06, 1.16), 38), (84, (2.8, -6.6, 1.85), (0.2, 0, 1.25), 38), (108, (2.8, -6.6, 1.85), (0.2, 0, 1.25), 38), (133, tuple(original[0]['camera_relative']), (0, 0, 0.95), 38)]
DETAIL_KEYS = [(324, tuple(original[191]['camera_relative']), (-1.48, -0.53, 0.55), 28), (330, (-2.72, 0.25, 0.03), (-1.55, -0.22, 0.5), 26), (338, (-2.05, 0.12, -0.16), (-1.55, -0.3, 0.48), 23), (346, (-1.05, 0.03, -0.18), (-1.6, -0.24, 0.5), 23), (354, (-0.15, 0, 0.02), (-1.62, -0.05, 0.5), 23), (360, (0.05, 0, 0.27), (-1.65, 0, 0.5), 23), (420, (0.05, 0, 0.27), (-1.65, 0, 0.5), 23), (427, (-0.25, 0.015, -0.02), (-1.65, -0.06, 0.5), 23), (435, (-1.25, 0.07, -0.18), (-1.65, -0.3, 0.48), 23), (442, (-2.35, 0.24, -0.1), (-1.52, -0.53, 0.53), 26), (450, tuple(original[191]['camera_relative']), (-1.48, -0.53, 0.55), 28)]

def path_at(keys, f, col):
    idx = next((i for i in range(len(keys) - 1) if keys[i][0] <= f <= keys[i + 1][0]), len(keys) - 2)
    times = [k[0] for k in keys]
    vals = [Vector(k[col]) if col in (1, 2) else k[col] for k in keys]

    def tangent(i):
        if i == 0 or i == len(keys) - 1:
            return Vector((0, 0, 0)) if col in (1, 2) else 0
        a = (vals[i] - vals[i - 1]) / (times[i] - times[i - 1])
        b = (vals[i + 1] - vals[i]) / (times[i + 1] - times[i])
        if col in (1, 2):
            if a.length < 1e-06 or b.length < 1e-06:
                return Vector((0, 0, 0))
        elif abs(a) < 1e-06 or abs(b) < 1e-06:
            return 0
        return (a + b) * 0.5
    dt = times[idx + 1] - times[idx]
    u = (f - times[idx]) / dt
    return (2 * u ** 3 - 3 * u * u + 1) * vals[idx] + (u ** 3 - 2 * u * u + u) * dt * tangent(idx) + (-2 * u ** 3 + 3 * u * u) * vals[idx + 1] + (u ** 3 - u * u) * dt * tangent(idx + 1)

def detail_orientation(f):
    held = (Vector((-1.65, 0, 0.5)) - Vector((0.05, 0, 0.27))).to_track_quat('-Z', 'Y')
    knots = [(324, Quaternion(original[191]['rotation'])), (342, (Vector((-1.6, -0.42, 0.5)) - path_at(DETAIL_KEYS, 342, 1)).to_track_quat('-Z', 'Y')), (360, held), (420, held), (435, (Vector((-1.65, -0.4, 0.48)) - path_at(DETAIL_KEYS, 435, 1)).to_track_quat('-Z', 'Y')), (450, Quaternion(original[191]['rotation']))]
    i = next((i for i in range(len(knots) - 1) if knots[i][0] <= f <= knots[i + 1][0]), len(knots) - 2)
    a, qa = knots[i]
    b, qb = knots[i + 1]
    qa = qa.copy()
    qb = qb.copy()
    if qa.dot(qb) < 0:
        qb.negate()
    u = (f - a) / (b - a)
    u = u * u * (3 - 2 * u)
    return qa.slerp(qb, u)
camera_samples = []
last = None
for f in range(1, END + 1):
    d = distance_at(f)
    if 133 <= f <= 324:
        old = original[f - 133]
        pos = Vector(old['camera_relative'])
        quat = Quaternion(old['rotation'])
        lens = old['lens']
        segment = 'retained original inspection'
    elif f >= 451:
        old = original[f - 259]
        pos = Vector(old['camera_relative'])
        quat = Quaternion(old['rotation'])
        lens = old['lens']
        segment = 'retained original pullaway'
    else:
        keys = INTRO_KEYS if f < 133 else DETAIL_KEYS
        pos = path_at(keys, f, 1)
        aim = path_at(keys, f, 2)
        lens = path_at(keys, f, 3)
        quat = (aim - pos).to_track_quat('-Z', 'Y')
        segment = 'engine bay opening' if f < 133 else 'additional rear inspection'
    if 325 <= f <= 450:
        quat = detail_orientation(f)
    if last and quat.dot(last) < 0:
        quat.negate()
    cam.location = pos + Vector((d, 0, 0))
    cam.rotation_quaternion = quat
    cam.data.lens = lens
    cam.keyframe_insert(data_path='location', frame=f)
    cam.keyframe_insert(data_path='rotation_quaternion', frame=f)
    cam.data.keyframe_insert(data_path='lens', frame=f)
    camera_samples.append({'frame': f, 'vehicle_travel_m': d, 'camera_relative': list(pos), 'rotation': list(quat), 'lens_mm': lens, 'segment': segment})
    last = quat.copy()
camera('INSPECT_05_ENGINE_BAY', (3.24, -1.68, 2.4), (1.63, -0.08, 1.16), 38, root)
camera('INSPECT_06_REAR_AXLE_AND_DRIVESHAFT', (0.05, 0, 0.27), (-1.65, 0, 0.5), 23, root)
oldguide = bpy.data.objects.get('GUIDE | camera trajectory')
if oldguide:
    bpy.data.objects.remove(oldguide, do_unlink=True)
guide = tube('GUIDE V2 | complete camera trajectory', [Vector(r['camera_relative']) + Vector((r['vehicle_travel_m'], 0, 0)) for r in camera_samples], 0.009, 'CAMERAS', accent)
guide.hide_render = True
guide.hide_set(True)
area('Engine bay soft inspection fill', (2.8, -1.7, 3.7), (1.6, 0, 1.1), 125, (1, 0.91, 0.79), 1.5, root)
area('Rear axle detail front fill', (0.35, -0.22, 0.035), (-1.6, 0, 0.55), 90, (0.81, 0.89, 1), 1.0, root)
for marker in list(scene.timeline_markers):
    scene.timeline_markers.remove(marker)
for f, label in [(1, '01 ENGINE BAY • hood open'), (49, '02 PAN OUT'), (85, '03 CLOSE HOOD'), (109, '04 PULL AWAY'), (133, '05 ORIGINAL SIDE PROFILE'), (181, '06 ORIGINAL FRONT ARC'), (217, '07 ORIGINAL UNDERSIDE'), (277, '08 ORIGINAL REAR-RIGHT'), (324, '09 MOVE TO SECOND REAR ANGLE'), (361, '10 REAR AXLE HOLD • 2.5 s'), (386, 'REAR BUMP CYCLE 1'), (404, 'REAR BUMP CYCLE 2'), (421, '11 EXIT CHANNEL'), (451, '12 ORIGINAL REAR PULLAWAY'), (498, 'END • 20.75 s')]:
    scene.timeline_markers.new(label, frame=f)
for act in bpy.data.actions:
    for layer in act.layers:
        for strip in layer.strips:
            for slot in act.slots:
                try:
                    bag = strip.channelbag(slot)
                except Exception:
                    continue
                if bag:
                    for fc in bag.fcurves:
                        for k in fc.keyframe_points:
                            k.interpolation = 'LINEAR'
for me in bpy.data.meshes:
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    me.update()
scene['revision'] = 'v2 — engine bay, closing hood, second rear axle angle'
scene['accepted_v1_sha256'] = base_hash
scene['shot_duration_seconds'] = END / 24
scene['new_rear_hold_frames'] = '361–420 inclusive: 60 output frames, 2.5 seconds'
scene['new_rear_hold_description'] = 'Camera holds its truck-relative position while the vehicle travels at 3 m/s over two rounded bumps.'
scene['rig_simplifications'] = 'Kinematic road-contact rig; wishbone length accommodation; flexing leaves with native pivoting shackles; constant-ratio driveshaft witness rotation; accessory drive slowed for 24 fps readability; rigid tire carcasses. No combustion or internal differential gear simulation.'
root['animation_note'] = 'V2 controls keyed 1–498. 1–108 parked, hood closes 85–108; smooth launch 109–133; driving 133–498 at 3 m/s.'
for key in ['verification_status', 'measured_camera_clearance_m', 'measured_max_leaf_saddle_error_m']:
    if key in scene:
        del scene[key]
scene['verification_report'] = 'V2 verification pending; v1 reports describe the archived original only.'
scene.frame_set(1)
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type == 'VIEW_3D':
            sp = ar.spaces.active
            sp.shading.type = 'SOLID'
            sp.shading.color_type = 'MATERIAL'
            sp.overlay.show_relationship_lines = False
            sp.overlay.show_extras = False
            sp.region_3d.view_perspective = 'PERSP'
            sp.region_3d.view_distance = 8.1
            sp.region_3d.view_location = (-1.5, 0, 1.15)
            sp.region_3d.view_rotation = Vector((6.7, -7.4, 3.5)).to_track_quat('Z', 'Y')
for o in bpy.context.selected_objects:
    o.select_set(False)
hinge.select_set(True)
bpy.context.view_layer.objects.active = hinge
block = bpy.data.texts.get('build_truck_v2.py') or bpy.data.texts.new('build_truck_v2.py')
bpy.ops.file.pack_all()

scene=bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
scene['cloud_source']='Procedural reconstruction from preserved build_truck.py and build_truck_v2.py; local accepted files unchanged.'
scene['rendering_status']='Cloud render preparation; animation source retained at 24 fps, 498 frames.'
scene['verification_report']='Local v2 passed 19 checks. Cloud scene requires its own render inspection.'
scene.view_settings.view_transform='AgX'
block=bpy.data.texts.get('README | START HERE') or bpy.data.texts.new('README | START HERE')
block.clear()
block.write('KESTREL v2 — 498 frames / 24 fps / 20.75 seconds. Engine-bay intro, hood close, driving inspection and additional 2.5-second rear axle hold. Procedural cloud reconstruction. Local accepted files preserved.')
result={'objects':len(scene.objects),'frames':[scene.frame_start,scene.frame_end],'fps':scene.render.fps,'camera':scene.camera.name,'hood_angle':bpy.data.objects['CTRL_HOOD_OPEN']['open_deg'],'build_seconds':time.perf_counter()-START}
print('CLOUD_BUILD_READY',json.dumps(result),flush=True)
