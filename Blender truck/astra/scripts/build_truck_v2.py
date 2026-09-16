"""Extend accepted v1 with engine-bay opening, hood closure and a second moving rear inspection.
Run in Blender. Loads v1 read-only, saves pickup_truck_v2.blend. Never renders.
"""
import bpy,bmesh,ast,math,json,time,hashlib
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from math import sin,cos,pi,sqrt,atan2
ROOT=Path(__file__).resolve().parent.parent
START=time.perf_counter();BASE=ROOT/'pickup_truck.blend';OUT=ROOT/'pickup_truck_v2.blend';REPORT=ROOT/'reports/v2'
REPORT.mkdir(parents=True,exist_ok=True)
base_hash=hashlib.sha256(BASE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene=bpy.context.scene;root=bpy.data.objects['CTRL_VEHICLE_TRAVEL'];body=bpy.data.objects['CTRL_BODY_HEAVE_PITCH_ROLL'];rear=bpy.data.objects['RIG_REAR_SOLID_AXLE'];cam=scene.camera
C={c.name:c for c in bpy.data.collections};M={m.name:m for m in bpy.data.materials}
paint=M['Paint | satin forest green'];black=M['Trim | charcoal polymer'];steel=M['Frame | graphite powdercoat'];alloy=M['Metal | brushed aluminium'];chrome=M['Metal | polished damper shafts'];rubber=M['Rubber | restrained road wear'];brake=M['Caliper | oxblood coating'];accent=M['Details | warm nickel'];leafmat=M['Leaf springs | manganese steel'];amber=M['Lens | warm amber']
# Reuse only helper function definitions from the preserved original construction source.
source=ast.parse((ROOT/'scripts/build_truck.py').read_text())
helpers={'mat','link','mesh','box','uv','cyl','tube','empty','prop','driver','pvar','dynamic_rod','keyprop','ring_y','text_obj','camera','area'}
for node in source.body:
    if isinstance(node,ast.FunctionDef) and node.name in helpers:exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'scripts/build_truck.py'),'exec'),globals())
R=.405;TRACK=1.66;INTRO=132;EXTRA=126;END=498
controls={c:bpy.data.objects['CTRL_SUSPENSION_'+c] for c in ['FL','FR','RL','RR']}
# Inspect and snapshot the accepted shot before changing any animation.
original=[]
for f in range(1,241):
    scene.frame_set(f);bpy.context.view_layer.update()
    original.append({'frame':f,'travel':root['travel_m'],'camera_relative':list(cam.location-Vector((root['travel_m'],0,0))),'rotation':list(cam.rotation_quaternion),'lens':cam.data.lens})
(REPORT/'original_camera_snapshot.json').write_text(json.dumps(original,indent=2))
print('V1_INSPECTED',len(scene.objects),'objects',scene.frame_end,'frames; SHA256',base_hash,flush=True)
scene.frame_set(1)
# Fresh animation on existing controls preserves all native drivers and component hierarchy.
for o in [root,*controls.values(),cam,cam.data]:
    if o.animation_data:o.animation_data.action=None
cam.name='CAM_ANIMATION_V2 | engine and dual rear inspection'
scene.name='KESTREL v2 | engine bay and moving rear suspension'
scene.frame_start=1;scene.frame_end=END;scene.render.filepath='//renders/kestrel_v2_'

# Keep original bump positions through the accepted underside/RR sequence; add stronger paired
# bumps only where the extended driving now takes place.
BUMPS=[(2.7,.048,1.6),(6.4,.060,1.9),(10.8,.047,1.6),(14.7,.055,2.0),(18.9,.082,1.8),(20.9,.064,1.7),(25.5,.058,1.9),(30.0,.082,1.9),(32.25,.074,1.9),(35.1,.055,1.8)]
def ground(x,y):
    z=0
    for i,(c,h,w) in enumerate(BUMPS):
        if y>0:c+=.32;h*=.5 if i in (4,5) else .76
        u=(x-c)/(w/2)
        if abs(u)<1:z+=h*(.5+.5*cos(pi*u))
    return z

def contact_height(x,y):return max(ground(x+R*(-1+2*i/160),y)+R*sqrt(max(0,1-(-1+2*i/160)**2)) for i in range(161))
def distance_at(f):
    if f<=109:return -1.5
    if f<133:
        u=(f-109)/24
        return -1.5+3*(u**3-.5*u**4)
    return (f-133)*3/24

def pose_at(d):
    wh={a+s:contact_height(d+x,y)-R for a,x in [('F',1.6),('R',-1.6)] for s,y in [('L',.83),('R',-.83)]}
    avg={}
    for code in wh:
        x=1.6 if code[0]=='F' else -1.6;y=.83 if code[1]=='L' else -.83
        avg[code]=sum((1-abs(k)/9)*(contact_height(d+x+k*.13,y)-R) for k in range(-8,9))/9
    h=sum(avg.values())/4*.72
    pitch=-(avg['FL']+avg['FR']-avg['RL']-avg['RR'])/2/3.2*.35
    roll=(avg['FL']+avg['RL']-avg['FR']-avg['RR'])/2/TRACK*.3
    return h,math.degrees(pitch),math.degrees(roll),{c:z-h for c,z in wh.items()}
for s in (-1,1):
    road=bpy.data.objects['Continuous wheel track '+('left' if s>0 else 'right')]
    for v in road.data.vertices:
        if v.co.z>-.1:v.co.z=ground(v.co.x,s*.83)
    road.data.update()

# Hinged hood with insulation, pressed reinforcement, real hinge pins and two telescopic struts.
hood=bpy.data.objects['Hood | crowned one-piece pressing'];pivot=Vector((1.08,0,1.305))
for v in hood.data.vertices:
    if v.co.x<1.0:v.co.x=1.07
hinge=empty('CTRL_HOOD_OPEN',pivot,body,size=.20)
prop(hinge,'open_deg',68,0,75,'Hood rotation about its rear hinge; 0 is fully latched.')
driver(hinge,'rotation_euler',1,'-a*pi/180',[pvar('a',hinge,'open_deg')])
def hood_parent(o):
    o.parent=hinge;o.matrix_parent_inverse=Matrix.Translation(-pivot);return o
hood_parent(hood)
# Lower surface interpolated directly from the accepted hood sections.
def hood_under_z(x):
    sec=[(1.07,1.245),(1.13,1.31),(2.30,1.245),(2.56,1.145)]
    for (a,za),(b,zb) in zip(sec,sec[1:]):
        if a<=x<=b:return za+(zb-za)*(x-a)/(b-a)
    return sec[0][1] if x<.91 else sec[-1][1]
for x in [1.15,1.43,1.75,2.08,2.18]:hood_parent(box('Hood underside pressed rib '+str(x),(x,0,hood_under_z(x)-.011),(.055,1.43,.020),'BODY',paint,bev=.008))
verts=[];faces=[]
for x in [1.12,1.35,1.75,2.14,2.24]:
    for y in (-.65,.65):verts.append((x,y,hood_under_z(x)-.021))
for i in range(4):faces.append((2*i,2*i+1,2*i+3,2*i+2))
pad=mesh('Hood heat and acoustic liner',verts,faces,'BODY',rubber);pad.modifiers.new('Insulation pad thickness','SOLIDIFY').thickness=.009;hood_parent(pad)
for s in (-1,1):
    y=s*.64
    box('Hood fixed hinge bracket '+str(s),(1.079,y,1.281),(.105,.08,.034),'BODY',steel,body,.008)
    cyl('Hood hinge pin '+str(s),(1.08,y-.051,1.305),(1.08,y+.051,1.305),.014,'BODY',chrome,body,n=16)
    hood_parent(box('Hood moving hinge arm '+str(s),(1.158,y,1.298),(.175,.037,.016),'BODY',alloy,bev=.006))
    low=empty('Hood strut body anchor '+str(s),(1.00,s*.775,1.07),body)
    high=empty('Hood strut lid anchor '+str(s),Vector((1.63,s*.780,1.285))-pivot,hinge)
    dynamic_rod('Hood gas strut outer '+str(s),low,high,.020,'BODY',black,.51)
    dynamic_rod('Hood gas strut sliding rod '+str(s),high,low,.008,'BODY',chrome)
    for a,label in [(low,'lower'),(high,'upper')]:
        uv('Hood strut ball joint '+str(s)+label,(0,0,0),(.023,.019,.023),'BODY',alloy,a)
    box('Hood strut lower bracket '+str(s),(1.00,s*.796,1.063),(.07,.058,.051),'BODY',steel,body,.007)
hood_parent(tube('Hood latch striker',[(2.46,-.037,1.169),(2.46,-.037,1.127),(2.46,.037,1.127),(2.46,.037,1.169)],.007,'BODY',alloy))
box('Hood latch receiver',(2.514,0,1.157),(.08,.132,.046),'BODY',steel,body,.012)

# Engine-bay details are genuine editable solids and hoses, with room under the closed hood.
service=mat('V2 | yellow service caps',(.69,.42,.05),.16,.36)
reservoir=mat('V2 | molded fluid reservoir',(.58,.63,.57),0,.48)
wiremat=mat('V2 | red cable insulation',(.28,.018,.01),0,.57)
for s in (-1,1):
    rr=.525;y=s*.675
    poly=[(.96,.62),(.96,1.225),(2.35,1.225),(2.35,.62),(1.6+rr,.62),(1.6+rr,R)]
    poly += [(1.6+rr*cos(i*pi/32),R+rr*sin(i*pi/32)) for i in range(33)]
    poly += [(1.6-rr,.62)]
    vs=[(x,yy,z) for yy in (y-.006,y+.006) for x,z in poly];n=len(poly)
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh('Engine bay inner wheelhouse '+str(s),vs,fs,'BODY',black,body,.004)
    tube('Fender mounting lip '+str(s),[(.99,s*.77,1.21),(1.5,s*.77,1.25),(2.33,s*.74,1.20)],.016,'BODY',paint,body)
    for x in [1.05,1.32,1.98,2.30]:
        z=1.21+(x-.99)/.51*.04 if x<=1.5 else 1.25-(x-1.5)/.83*.05
        cyl('Fender flange screw '+str(s)+str(x),(x,s*.771,z+.013),(x,s*.771,z+.024),.009,'BODY',alloy,body,n=6)
box('Battery tray',(1.12,-.595,1.000),(.35,.31,.025),'DRIVETRAIN',steel,body,.009)
box('Engine bay battery',(1.12,-.595,1.106),(.30,.25,.188),'DRIVETRAIN',black,body,.017)
box('Battery lid',(1.12,-.595,1.207),(.31,.26,.020),'DRIVETRAIN',steel,body,.007)
for xx,ma in [(1.02,wiremat),(1.22,black)]:
    cyl('Battery terminal '+str(xx),(xx,-.565,1.216),(xx,-.565,1.239),.014,'DRIVETRAIN',alloy,body)
    box('Battery terminal cover '+str(xx),(xx,-.565,1.236),(.058,.059,.019),'DRIVETRAIN',ma,body,.008)
for y in (-.694,-.496):cyl('Battery hold-down rod '+str(y),(1.12,y,1.015),(1.12,y,1.222),.005,'DRIVETRAIN',alloy,body)
box('Battery hold-down bridge',(1.12,-.595,1.225),(.027,.26,.012),'DRIVETRAIN',steel,body,.003)
box('Engine fuse and relay box',(1.07,-.388,1.164),(.185,.126,.09),'DRIVETRAIN',black,body,.013)
box('Air filter box',(2.035,.566,1.111),(.31,.322,.222),'DRIVETRAIN',black,body,.036)
box('Air filter lid',(2.035,.566,1.227),(.317,.326,.025),'DRIVETRAIN',steel,body,.010)
for x in [1.93,2.035,2.14]:box('Airbox molded lid ridge '+str(x),(x,.566,1.244),(.016,.25,.008),'DRIVETRAIN',black,body,.003)
for y in (.422,.711):box('Airbox retaining clip '+str(y),(2.035,y,1.205),(.036,.019,.069),'DRIVETRAIN',alloy,body,.004)
tube('Engine intake duct',[(1.945,.437,1.165),(1.80,.449,1.159),(1.66,.438,1.137),(1.59,.35,1.108)],.047,'DRIVETRAIN',black,body)
for x in [1.80,1.84,1.88]:cyl('Intake flexible bellows '+str(x),(x-.009,.449,1.159),(x+.009,.449,1.159),.052,'DRIVETRAIN',rubber,body,n=24)
box('Coolant expansion reservoir',(1.24,.566,1.139),(.20,.21,.158),'DRIVETRAIN',reservoir,body,.042)
cyl('Coolant pressure cap',(1.24,.566,1.218),(1.24,.566,1.244),.035,'DRIVETRAIN',black,body,n=12)
box('Brake master fluid reservoir',(.994,.415,1.155),(.13,.17,.095),'DRIVETRAIN',reservoir,body,.023)
cyl('Brake fluid cap',(.994,.415,1.205),(.994,.415,1.222),.026,'DRIVETRAIN',black,body,n=12)
tube('Upper radiator coolant hose',[(2.293,-.40,1.185),(2.15,-.40,1.191),(1.95,-.37,1.170),(1.83,-.24,1.142)],.031,'DRIVETRAIN',rubber,body)
tube('Expansion reservoir small hose',[(1.24,.46,1.135),(1.36,.41,1.18),(1.50,.35,1.21),(1.76,.28,1.15)],.009,'DRIVETRAIN',rubber,body)
cyl('Radiator filler neck',(2.33,.46,1.215),(2.33,.46,1.245),.024,'DRIVETRAIN',alloy,body)
cyl('Radiator pressure cap',(2.33,.46,1.241),(2.33,.46,1.256),.035,'DRIVETRAIN',steel,body,n=12)
# Ignition coils, fuel rail, oil service points and restrained wiring.
for i,x in enumerate([1.36,1.51,1.66,1.81]):
    box('Ignition coil '+str(i+1),(x,0,1.296),(.089,.133,.039),'DRIVETRAIN',black,body,.012)
    box('Ignition coil plug '+str(i+1),(x,-.091,1.294),(.038,.039,.031),'DRIVETRAIN',steel,body,.006)
    tube('Ignition coil wire '+str(i+1),[(x,-.11,1.294),(x-.04,-.145,1.287),(x-.04,-.19,1.265)],.005,'DRIVETRAIN',rubber,body)
    cyl('Fuel injector '+str(i+1),(x,.17,1.195),(x,.21,1.245),.014,'DRIVETRAIN',steel,body)
tube('Engine wiring loom',[(1.12,-.38,1.165),(1.20,-.22,1.265),(1.82,-.19,1.265),(1.93,-.28,1.14)],.012,'DRIVETRAIN',rubber,body)
tube('Common fuel rail',[(1.29,.215,1.241),(1.89,.215,1.241)],.013,'DRIVETRAIN',alloy,body)
cyl('Oil filler cap',(1.38,.11,1.283),(1.38,.11,1.305),.033,'DRIVETRAIN',black,body,n=12)
tube('Dipstick tube',[(1.81,-.23,.85),(1.86,-.27,1.05),(1.86,-.28,1.205)],.007,'DRIVETRAIN',alloy,body)
tube('Dipstick handle',[(1.86+.018*cos(i*2*pi/24),-.28,1.228+.023*sin(i*2*pi/24)) for i in range(24)],.005,'DRIVETRAIN',service,body,True)
tube('Battery positive cable',[(1.02,-.565,1.236),(.977,-.57,1.21),(.975,-.46,1.188),(1.00,-.388,1.177)],.008,'DRIVETRAIN',wiremat,body)
tube('Battery ground cable',[(1.22,-.565,1.236),(1.27,-.55,1.205),(1.28,-.66,1.151)],.008,'DRIVETRAIN',rubber,body)
# Visible accessory drive. Speeds are intentionally slowed for inspection at 24 fps.
engine_ctrl=empty('CTRL_ENGINE_ACCESSORIES',parent=body)
prop(engine_ctrl,'demonstration_rpm',60,0,600,'Illustrative accessory speed; slowed for readable 24 fps inspection, not engine combustion RPM.')
prop(engine_ctrl,'fan_rpm',90,0,600,'Cooling fan demonstration speed.')
pulleys=[('Crank',0,.890,.104),('Alternator',-.247,1.125,.052),('Water pump',.192,1.102,.061)]
for name,y,z,r in pulleys:
    p=empty('RIG_ENGINE_PULLEY_'+name,(2.063,y,z),body)
    driver(p,'rotation_euler',0,f'frame/24*rpm*2*pi/60*{.104/r}',[pvar('rpm',engine_ctrl,'demonstration_rpm')])
    ob=ring_y('Accessory pulley grooved rim '+name,[(-.015,r*.75),(-.015,r),(-.006,r+.003),(.006,r+.003),(.015,r),(.015,r*.75)],'DRIVETRAIN',steel,p,48);ob.rotation_euler.z=-pi/2
    cyl('Accessory pulley hub '+name,(-.019,0,0),(.024,0,0),r*.25,'DRIVETRAIN',alloy,p,n=20)
    for k in range(5):
        a=k*2*pi/5
        cyl('Accessory pulley spoke '+name+str(k),(0,r*.20*cos(a),r*.20*sin(a)),(0,r*.83*cos(a),r*.83*sin(a)),.009,'DRIVETRAIN',steel,p,n=12)
    cyl('Accessory shaft mount '+name,(1.945,y,z),(2.046,y,z),.024,'DRIVETRAIN',alloy,body)
    uv('Pulley balance marker '+name,(.019,r*.64,0),(.003,.007,.007),'DRIVETRAIN',accent,p)
cyl('Alternator cast housing',(1.864,-.247,1.125),(2.016,-.247,1.125),.083,'DRIVETRAIN',alloy,body,n=32)
for x in [1.88,1.91,1.94,1.97]:cyl('Alternator cooling rib '+str(x),(x-.005,-.247,1.125),(x+.005,-.247,1.125),.087,'DRIVETRAIN',steel,body,n=24)
# Convex envelope of the pulley circles gives a continuous tangent belt route.
pts=sorted(set((y+(r+.004)*cos(i*2*pi/64),z+(r+.004)*sin(i*2*pi/64)) for _,y,z,r in pulleys for i in range(64)))
def cross2(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
lo=[];hi=[]
for p in pts:
    while len(lo)>=2 and cross2(lo[-2],lo[-1],p)<=0:lo.pop()
    lo.append(p)
for p in reversed(pts):
    while len(hi)>=2 and cross2(hi[-2],hi[-1],p)<=0:hi.pop()
    hi.append(p)
belt_path=lo[:-1]+hi[:-1];N=len(belt_path);vs=[];fs=[]
for i,(y,z) in enumerate(belt_path):
    before=Vector(belt_path[(i-1)%N]);after=Vector(belt_path[(i+1)%N]);t=(after-before).normalized();normal=Vector((t.y,-t.x))
    for xx,offset in [(-.013,-.003),(.013,-.003),(.013,.003),(-.013,.003)]:vs.append((2.063+xx,y+normal.x*offset,z+normal.y*offset))
for i in range(N):
    for k in range(4):fs.append((4*i+k,4*i+(k+1)%4,4*((i+1)%N)+(k+1)%4,4*((i+1)%N)+k))
mesh('Engine serpentine belt | tangent continuous loop',vs,fs,'DRIVETRAIN',rubber,body,.0006)
lengths=[(Vector(belt_path[(i+1)%N])-Vector(belt_path[i])).length for i in range(N)];belt_length=sum(lengths)
def belt_position(d):
    d=d%belt_length
    for i,L in enumerate(lengths):
        if d<=L:
            a=Vector(belt_path[i]);b=Vector(belt_path[(i+1)%N]);q=a+(b-a)*(d/L);t=(b-a).normalized()
            return q,t
        d-=L
    return Vector(belt_path[0]),Vector((1,0))
belt_ribs=[box('Moving belt molded timing rib '+str(i),(0,0,0),(.027,.004,.004),'DRIVETRAIN',steel,body,.001) for i in range(7)]
fan=empty('RIG_ENGINE_COOLING_FAN',(2.201,0,1.025),body)
driver(fan,'rotation_euler',0,'frame/24*rpm*2*pi/60',[pvar('rpm',engine_ctrl,'fan_rpm')])
cyl('Cooling fan hub',(-.022,0,0),(.021,0,0),.044,'DRIVETRAIN',black,fan,n=24)
for k in range(5):
    a=k*2*pi/5;verts=[]
    blade=[(.041,a-.10),(.163,a+.02),(.172,a+.29),(.063,a+.48)]
    for xx in (-.007,.007):
        for r,ang in blade:verts.append((xx+.024*(r-.041),r*cos(ang),r*sin(ang)))
    mesh('Swept cooling fan blade '+str(k),verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'DRIVETRAIN',black,fan,.002)
shroud=ring_y('Cooling fan protective shroud',[(-.022,.185),(-.022,.207),(.022,.207),(.022,.185)],'DRIVETRAIN',black,body,64)
shroud.rotation_euler.z=-pi/2;shroud.location=(2.241,0,1.025)
for y in (-.27,.27):box('Cooling shroud radiator bracket '+str(y),(2.271,y,1.025),(.043,.12,.042),'DRIVETRAIN',steel,body,.006)

# Rear shackles now pivot; leaf eyes follow their real moving lower pivots.
shackles={}
for s,code in [(1,'RL'),(-1,'RR')]:
    y=s*.57;L=.13;a0=math.radians(8);top=Vector((-2.46+L*sin(a0),y,.605+L*cos(a0)))
    for o in list(bpy.data.objects):
        if o.name.startswith('Rear shackle ') and (o.name.startswith('Rear shackle bushing '+str(s)) or o.name.startswith('Rear shackle through bolt '+str(s)) or o.name.startswith('Rear shackle mounting cheek '+str(s))):bpy.data.objects.remove(o,do_unlink=True)
    ctrl=empty('RIG_REAR_SHACKLE_'+code,top,body)
    fc=ctrl.driver_add('rotation_euler',1);d=fc.driver;d.expression='8*pi/180+(z-.31)*3.4'
    v=d.variables.new();v.name='z';v.type='TRANSFORMS';v.targets[0].id=bpy.data.objects['Leaf local deformation target '+code];v.targets[0].transform_type='LOC_Z';v.targets[0].transform_space='LOCAL_SPACE'
    end=empty('Rear moving leaf eye '+code,(0,0,-L),ctrl)
    target=empty('Rear leaf eye body-local target '+code,(-2.46,y,.605),body)
    con=target.constraints.new('COPY_LOCATION');con.target=end
    shackles[code]=(ctrl,end,target)
    for yy in (-.052,.052):box('Moving shackle side plate '+code+str(yy),(0,yy,-L/2),(.047,.013,L+.035),'REAR_SUSPENSION',alloy,ctrl,.012)
    for anchor,label in [(ctrl,'upper'),(end,'lower')]:
        cyl('Shackle elastomer bushing '+code+label,(0,-.042,0),(0,.042,0),.028,'REAR_SUSPENSION',rubber,anchor,n=24)
        cyl('Shackle shoulder bolt '+code+label,(0,-.070,0),(0,.070,0),.013,'REAR_SUSPENSION',steel,anchor,n=6)
    box('Shackle fixed clevis base '+code,top+Vector((0,-s*.045,.026)),(.113,.175,.045),'REAR_SUSPENSION',steel,body,.010)
    for layer in range(1,6):
        o=bpy.data.objects['Leaf pack '+code+' lamination '+str(layer)];basis=o.data.shape_keys.key_blocks[0]
        for axis,label,rest in [(0,'Rear shackle eye X',-2.46),(2,'Rear shackle eye Z',.605)]:
            k=o.shape_key_add(name=label,from_mix=False);k.slider_min=-2;k.slider_max=2
            for i,p in enumerate(k.data):
                u=basis.data[i].co.x+1.6;w=max(0,-u/.86)**3;p.co[axis]+=.05*w
            fc=k.driver_add('value');d=fc.driver;d.expression=f'(v-({rest}))/.05'
            var=d.variables.new();var.name='v';var.type='TRANSFORMS';var.targets[0].id=target;var.targets[0].transform_type='LOC_'+('X' if axis==0 else 'Z');var.targets[0].transform_space='LOCAL_SPACE'
    cyl('Progressive axle bump stop '+code,(-1.60,s*.48,.63),(-1.60,s*.48,.574),.038,'REAR_SUSPENSION',rubber,body,n=24,r2=.028)
    cyl('Bump stop retaining washer '+code,(-1.60,s*.48,.628),(-1.60,s*.48,.636),.043,'REAR_SUSPENSION',alloy,body,n=24)
# An articulated slip sleeve and rotating balance mark make shaft motion legible.
shaft=bpy.data.objects['Rear driveshaft | articulated'];transfer=bpy.data.objects['Joint transfer rear'];pinion=bpy.data.objects['Joint rear pinion']
shaft_spin=empty('RIG_REAR_PROPSHAFT_ROTATION',parent=shaft)
driver(shaft_spin,'rotation_euler',2,'d/.405*3.73',[pvar('d',root,'travel_m')])
# The parent scale follows shaft length; the band sits at a constant fractional location.
for a in (0,pi):
    verts=[]
    for z in (.36,.46):
        for i in range(8):
            ang=a-.16+.32*i/7;verts.append((.0387*cos(ang),.0387*sin(ang),z))
    mesh('Rotating prop shaft witness band '+str(a),verts,[(i,i+1,i+9,i+8) for i in range(7)],'DRIVETRAIN',accent,shaft_spin)
sleeve=dynamic_rod('Rear driveshaft slip sleeve',transfer,pinion,.046,'DRIVETRAIN',steel,.185)
for start,end,label in [(transfer,pinion,'transfer'),(pinion,transfer,'pinion')]:
    orient=empty('RIG_PROPSHAFT_YOKE_'+label)
    co=orient.constraints.new('COPY_LOCATION');co.target=start
    co=orient.constraints.new('DAMPED_TRACK');co.target=end;co.track_axis='TRACK_Z'
    rotor=empty('Rotating universal joint '+label,parent=orient)
    driver(rotor,'rotation_euler',2,('' if label=='transfer' else '-')+'d/.405*3.73',[pvar('d',root,'travel_m')])
    cyl('Prop shaft flange '+label,(0,0,-.016),(0,0,.002),.062,'DRIVETRAIN',alloy,rotor,n=32)
    for sign in (-1,1):box('Universal yoke ear '+label+str(sign),(sign*.041,0,.029),(.018,.051,.065),'DRIVETRAIN',steel,rotor,.008)
    cyl('Universal joint trunnion '+label,(-.053,0,.037),(.053,0,.037),.018,'DRIVETRAIN',alloy,rotor,n=16)
    for k in range(4):
        a=k*pi/2;cyl('Prop flange bolt '+label+str(k),(.049*cos(a),.049*sin(a),-.020),(.049*cos(a),.049*sin(a),.005),.009,'DRIVETRAIN',steel,rotor,n=6)

# Rebuild all driving keys: motion continues through the new view, never freezing the truck.
for f in range(1,END+1):
    d=distance_at(f);h,p,r,q=pose_at(d)
    for k,v in [('travel_m',d),('body_heave_m',h),('body_pitch_deg',p),('body_roll_deg',r),('steering_deg',0)]:keyprop(root,k,v,f)
    for c,v in q.items():keyprop(controls[c],'travel_m',v,f)
    hood_angle=68 if f<=84 else (68*(.5+.5*cos(pi*min(1,(f-84)/24))) if f<108 else 0)
    keyprop(hinge,'open_deg',hood_angle,f)
    belt_speed=60/60*2*pi*.104
    for i,o in enumerate(belt_ribs):
        p,t=belt_position(f/24*belt_speed+i*belt_length/len(belt_ribs));o.location=(2.063,p.x,p.y);o.rotation_euler.x=atan2(t.y,t.x)
        o.keyframe_insert(data_path='location',frame=f);o.keyframe_insert(data_path='rotation_euler',frame=f)
# Package the exposed top end within the actual closed hood envelope.
block=bpy.data.objects['Engine | inline four cast block'];block.scale.z*=.355/.420;block.location.z-=.0325
for name in ['Engine cylinder head','Engine valve cover']:
    bpy.data.objects[name].location.z-=.065
for o in bpy.data.objects:
    if any(o.name.startswith(p) for p in ['Ignition coil ','Ignition coil plug ','Ignition coil wire ','Fuel injector ','Common fuel rail','Oil filler cap']):o.location.z-=.065
loom=bpy.data.objects['Engine wiring loom']
for point in list(loom.data.splines[0].points)[1:]:point.co.z-=.065
for o in bpy.data.objects:
    if any(o.name.startswith(p) for p in ['Air filter box','Air filter lid','Airbox molded lid ridge','Airbox retaining clip']):o.location+=Vector((.070,-.090,-.025))
for o in bpy.data.objects:
    if o.name.startswith('Battery ') or o.name=='Engine bay battery':o.location+=Vector((.13,.08,0))
bpy.data.objects['Battery ground cable'].data.splines[0].points[-1].co.y=-.749
cyl('Electrical ground lug bolt',(1.41,-.662,1.151),(1.41,-.680,1.151),.009,'DRIVETRAIN',alloy,body,n=6)
bpy.data.objects['Engine fuse and relay box'].location.y+=.077
for name in ['Coolant expansion reservoir','Coolant pressure cap']:bpy.data.objects[name].location.y-=.025
bpy.data.objects['Engine intake duct'].data.splines[0].points[0].co.x=1.97
for name in ['Radiator filler neck','Radiator pressure cap']:
    bpy.data.objects[name].location.x-=.070;bpy.data.objects[name].location.z-=.019
tube('Radiator filler neck elbow',[(2.33,.46,1.20),(2.26,.46,1.208)],.021,'DRIVETRAIN',alloy,body)
for v in pad.data.vertices:v.co.y*=.33/.65;v.co.z+=.017
pad.modifiers['Insulation pad thickness'].offset=1

# Camera extension. Retained segments use the exact accepted relative camera samples.
INTRO_KEYS=[
(1,(3.24,-1.68,2.40),(1.63,-.08,1.16),38),
(48,(3.18,-1.59,2.38),(1.63,-.06,1.16),38),
(84,(2.80,-6.60,1.85),(.20,0,1.25),38),
(108,(2.80,-6.60,1.85),(.20,0,1.25),38),
(133,tuple(original[0]['camera_relative']),(0,0,.95),38),
]
DETAIL_KEYS=[
(324,tuple(original[191]['camera_relative']),(-1.48,-.53,.55),28),
(330,(-2.72,.25,.030),(-1.55,-.22,.50),26),
(338,(-2.05,.12,-.16),(-1.55,-.30,.48),23),
(346,(-1.05,.03,-.18),(-1.60,-.24,.50),23),
(354,(-.15,0,.020),(-1.62,-.05,.50),23),
(360,(.05,0,.27),(-1.65,0,.50),23),
(420,(.05,0,.27),(-1.65,0,.50),23),
(427,(-.25,.015,-.02),(-1.65,-.06,.50),23),
(435,(-1.25,.07,-.18),(-1.65,-.30,.48),23),
(442,(-2.35,.24,-.10),(-1.52,-.53,.53),26),
(450,tuple(original[191]['camera_relative']),(-1.48,-.53,.55),28),
]
def path_at(keys,f,col):
    idx=next((i for i in range(len(keys)-1) if keys[i][0]<=f<=keys[i+1][0]),len(keys)-2)
    times=[k[0] for k in keys];vals=[Vector(k[col]) if col in (1,2) else k[col] for k in keys]
    def tangent(i):
        if i==0 or i==len(keys)-1:return Vector((0,0,0)) if col in (1,2) else 0
        a=(vals[i]-vals[i-1])/(times[i]-times[i-1]);b=(vals[i+1]-vals[i])/(times[i+1]-times[i])
        if col in (1,2):
            if a.length<1e-6 or b.length<1e-6:return Vector((0,0,0))
        elif abs(a)<1e-6 or abs(b)<1e-6:return 0
        return (a+b)*.5
    dt=times[idx+1]-times[idx];u=(f-times[idx])/dt
    return (2*u**3-3*u*u+1)*vals[idx]+(u**3-2*u*u+u)*dt*tangent(idx)+(-2*u**3+3*u*u)*vals[idx+1]+(u**3-u*u)*dt*tangent(idx+1)
def detail_orientation(f):
    held=(Vector((-1.65,0,.50))-Vector((.05,0,.27))).to_track_quat('-Z','Y')
    knots=[(324,Quaternion(original[191]['rotation'])),
           (342,(Vector((-1.60,-.42,.50))-path_at(DETAIL_KEYS,342,1)).to_track_quat('-Z','Y')),
           (360,held),(420,held),
           (435,(Vector((-1.65,-.40,.48))-path_at(DETAIL_KEYS,435,1)).to_track_quat('-Z','Y')),
           (450,Quaternion(original[191]['rotation']))]
    i=next((i for i in range(len(knots)-1) if knots[i][0]<=f<=knots[i+1][0]),len(knots)-2)
    a,qa=knots[i];b,qb=knots[i+1];qa=qa.copy();qb=qb.copy()
    if qa.dot(qb)<0:qb.negate()
    u=(f-a)/(b-a);u=u*u*(3-2*u)
    return qa.slerp(qb,u)
camera_samples=[];last=None
for f in range(1,END+1):
    d=distance_at(f)
    if 133<=f<=324:
        old=original[f-133];pos=Vector(old['camera_relative']);quat=Quaternion(old['rotation']);lens=old['lens'];segment='retained original inspection'
    elif f>=451:
        old=original[f-259];pos=Vector(old['camera_relative']);quat=Quaternion(old['rotation']);lens=old['lens'];segment='retained original pullaway'
    else:
        keys=INTRO_KEYS if f<133 else DETAIL_KEYS
        pos=path_at(keys,f,1);aim=path_at(keys,f,2);lens=path_at(keys,f,3);quat=(aim-pos).to_track_quat('-Z','Y');segment='engine bay opening' if f<133 else 'additional rear inspection'
    if 325<=f<=450:quat=detail_orientation(f)
    if last and quat.dot(last)<0:quat.negate()
    cam.location=pos+Vector((d,0,0));cam.rotation_quaternion=quat;cam.data.lens=lens
    cam.keyframe_insert(data_path='location',frame=f);cam.keyframe_insert(data_path='rotation_quaternion',frame=f);cam.data.keyframe_insert(data_path='lens',frame=f)
    camera_samples.append({'frame':f,'vehicle_travel_m':d,'camera_relative':list(pos),'rotation':list(quat),'lens_mm':lens,'segment':segment});last=quat.copy()
# Existing inspection cameras are retained; two new inspection presets are added.
camera('INSPECT_05_ENGINE_BAY',(3.24,-1.68,2.40),(1.63,-.08,1.16),38,root)
camera('INSPECT_06_REAR_AXLE_AND_DRIVESHAFT',(.05,0,.27),(-1.65,0,.50),23,root)
oldguide=bpy.data.objects.get('GUIDE | camera trajectory')
if oldguide:bpy.data.objects.remove(oldguide,do_unlink=True)
guide=tube('GUIDE V2 | complete camera trajectory',[Vector(r['camera_relative'])+Vector((r['vehicle_travel_m'],0,0)) for r in camera_samples],.009,'CAMERAS',accent);guide.hide_render=True;guide.hide_set(True)
area('Engine bay soft inspection fill',(2.8,-1.7,3.7),(1.60,0,1.1),125,(1,.91,.79),1.5,root)
area('Rear axle detail front fill',(.35,-.22,.035),(-1.6,0,.55),90,(.81,.89,1),1.0,root)
for marker in list(scene.timeline_markers):scene.timeline_markers.remove(marker)
for f,label in [(1,'01 ENGINE BAY • hood open'),(49,'02 PAN OUT'),(85,'03 CLOSE HOOD'),(109,'04 PULL AWAY'),(133,'05 ORIGINAL SIDE PROFILE'),(181,'06 ORIGINAL FRONT ARC'),(217,'07 ORIGINAL UNDERSIDE'),(277,'08 ORIGINAL REAR-RIGHT'),(324,'09 MOVE TO SECOND REAR ANGLE'),(361,'10 REAR AXLE HOLD • 2.5 s'),(386,'REAR BUMP CYCLE 1'),(404,'REAR BUMP CYCLE 2'),(421,'11 EXIT CHANNEL'),(451,'12 ORIGINAL REAR PULLAWAY'),(498,'END • 20.75 s')]:scene.timeline_markers.new(label,frame=f)
# Dense baked curves use linear interpolation; paths themselves were eased before sampling.
for act in bpy.data.actions:
    for layer in act.layers:
        for strip in layer.strips:
            for slot in act.slots:
                try:bag=strip.channelbag(slot)
                except Exception:continue
                if bag:
                    for fc in bag.fcurves:
                        for k in fc.keyframe_points:k.interpolation='LINEAR'
for me in bpy.data.meshes:
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
scene['revision']='v2 — engine bay, closing hood, second rear axle angle'
scene['accepted_v1_sha256']=base_hash
scene['shot_duration_seconds']=END/24
scene['new_rear_hold_frames']='361–420 inclusive: 60 output frames, 2.5 seconds'
scene['new_rear_hold_description']='Camera holds its truck-relative position while the vehicle travels at 3 m/s over two rounded bumps.'
scene['rig_simplifications']='Kinematic road-contact rig; wishbone length accommodation; flexing leaves with native pivoting shackles; constant-ratio driveshaft witness rotation; accessory drive slowed for 24 fps readability; rigid tire carcasses. No combustion or internal differential gear simulation.'
root['animation_note']='V2 controls keyed 1–498. 1–108 parked, hood closes 85–108; smooth launch 109–133; driving 133–498 at 3 m/s.'
for key in ['verification_status','measured_camera_clearance_m','measured_max_leaf_saddle_error_m']:
    if key in scene:del scene[key]
scene['verification_report']='V2 verification pending; v1 reports describe the archived original only.'
scene.frame_set(1);bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            sp=ar.spaces.active;sp.shading.type='SOLID';sp.shading.color_type='MATERIAL';sp.overlay.show_relationship_lines=False;sp.overlay.show_extras=False
            sp.region_3d.view_perspective='PERSP';sp.region_3d.view_distance=8.1;sp.region_3d.view_location=(-1.5,0,1.15);sp.region_3d.view_rotation=Vector((6.7,-7.4,3.5)).to_track_quat('Z','Y')
for o in bpy.context.selected_objects:o.select_set(False)
hinge.select_set(True);bpy.context.view_layer.objects.active=hinge
block=bpy.data.texts.get('build_truck_v2.py') or bpy.data.texts.new('build_truck_v2.py');block.clear();block.write(Path(__file__).read_text())
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==base_hash,'Accepted v1 was changed'
manifest={'scene':str(OUT),'base_sha256':base_hash,'frame_range':[1,END],'fps':24,'duration_seconds':END/24,'new_hold':[361,420],'objects':len(scene.objects),'build_seconds':time.perf_counter()-START,'render_invoked':False,'bumps':BUMPS}
(REPORT/'build_manifest.json').write_text(json.dumps(manifest,indent=2));(REPORT/'camera_samples.json').write_text(json.dumps(camera_samples,indent=2));print('V2_BUILD_COMPLETE',json.dumps(manifest),flush=True)
