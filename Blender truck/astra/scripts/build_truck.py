"""Original procedural pickup. Run in Blender; never invokes rendering."""
import bpy, bmesh, math, json, time, sys, os
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from math import sin, cos, pi, sqrt, atan2
START=time.perf_counter()
ROOT=Path(__file__).resolve().parent.parent
R=.405
TRACK=1.66
AXLES={'F':1.6,'R':-1.6}
SIDES={'L':TRACK/2,'R':-TRACK/2}
COLLECTIONS='BODY INTERIOR CHASSIS DRIVETRAIN FRONT_SUSPENSION REAR_SUSPENSION WHEELS RIG ROAD CAMERAS LIGHTS'.split()
rig_only='--rig-only' in sys.argv
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection': bpy.data.collections.remove(c)
base=bpy.data.collections.get('Collection')
if base: bpy.data.collections.remove(base)
C={n:bpy.data.collections.new(n) for n in COLLECTIONS}
for c in C.values(): bpy.context.scene.collection.children.link(c)
scene=bpy.context.scene
scene.name='KESTREL | 4x4 mechanical proving ground'
scene.unit_settings.system='METRIC'; scene.unit_settings.length_unit='METERS'
scene.render.engine='CYCLES' if False else 'BLENDER_EEVEE'
scene.render.resolution_x=1920; scene.render.resolution_y=1080; scene.render.resolution_percentage=100
scene.render.fps=24; scene.frame_start=1; scene.frame_end=240
scene.render.image_settings.file_format='PNG'; scene.render.filepath='//renders/kestrel_'
scene.render.film_transparent=False
if hasattr(scene.render,'use_motion_blur'): scene.render.use_motion_blur=False
if hasattr(scene,'eevee'):
    for k,v in [('taa_render_samples',64),('taa_samples',32),('use_gtao',True)]:
        if hasattr(scene.eevee,k): setattr(scene.eevee,k,v)
    scene.eevee.use_raytracing=True
    scene.eevee.ray_tracing_options.screen_trace_quality=.5
    scene.eevee.ray_tracing_options.screen_trace_thickness=.03
scene.world.color=(.22,.24,.27)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.48,.57,.69,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
scene.view_settings.view_transform='AgX'
scene.render.fps_base=1
M={}
def mat(name,color,metal=0,rough=.45):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough
    M[name]=m; return m
paint=mat('Paint | satin forest green',(.075,.155,.107),.62,.29)
black=mat('Trim | charcoal polymer',(.018,.026,.028),.12,.48)
steel=mat('Frame | graphite powdercoat',(.055,.066,.072),.68,.34)
alloy=mat('Metal | brushed aluminium',(.43,.48,.50),.82,.28)
chrome=mat('Metal | polished damper shafts',(.62,.67,.7),.92,.19)
rubber=mat('Rubber | restrained road wear',(.024,.029,.027),0,.77)
red=mat('Lens | garnet red',(.33,.018,.009),.12,.24)
amber=mat('Lens | warm amber',(.70,.23,.035),.22,.22)
leafmat=mat('Leaf springs | manganese steel',(.13,.16,.17),.78,.39)
brake=mat('Caliper | oxblood coating',(.28,.041,.027),.58,.35)
roadmat=mat('Road | fine aggregate concrete',(.24,.27,.29),0,.86)
lightmat=mat('LED | warm white',(.95,.76,.45),.2,.22)
p=lightmat.node_tree.nodes['Principled BSDF']; p.inputs['Emission Color'].default_value=(1,.77,.4,1); p.inputs['Emission Strength'].default_value=3
redlight=mat('LED | rear running light',(.45,.013,.006),.15,.2)
p=redlight.node_tree.nodes['Principled BSDF']; p.inputs['Emission Color'].default_value=(1,.02,.007,1); p.inputs['Emission Strength'].default_value=1.5
glass=mat('Glass | laminated smoke',(.12,.21,.24),.08,.17)
p=glass.node_tree.nodes['Principled BSDF']; p.inputs['Transmission Weight'].default_value=.72; p.inputs['IOR'].default_value=1.46
seatmat=mat('Interior | graphite fabric',(.055,.066,.060),0,.88)
accent=mat('Details | warm nickel',(.52,.43,.28),.76,.33)
for m,scale,strength in [(rubber,125,.11),(roadmat,35,.19),(steel,95,.07),(seatmat,165,.10)]:
    nt=m.node_tree; tex=nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=scale; tex.inputs['Detail'].default_value=2
    bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=strength; bump.inputs['Distance'].default_value=.009
    nt.links.new(tex.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],nt.nodes['Principled BSDF'].inputs['Normal'])

def link(o,col,ma=None,parent=None):
    for c in list(o.users_collection): c.objects.unlink(o)
    C[col].objects.link(o)
    if ma and o.type in {'MESH','CURVE'}: o.data.materials.append(ma)
    if parent: o.parent=parent
    return o

def mesh(name,verts,faces,col,ma=None,parent=None,bevel=0):
    me=bpy.data.meshes.new(name+' mesh'); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); C[col].objects.link(o)
    if ma: me.materials.append(ma)
    if parent:o.parent=parent
    if bevel:
        b=o.modifiers.new('Small manufactured edge radii','BEVEL'); b.width=bevel; b.segments=3
        b=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    return o

def box(name,loc,size,col,ma,parent=None,bev=.014):
    x,y,z=[v/2 for v in size]
    vs=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    fs=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    o=mesh(name,vs,fs,col,ma,parent,min(bev,min(size)*.25));o.location=loc;return o

def uv(name,loc,scale,col,ma,parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(0,0,0))
    o=bpy.context.object;o.name=name;o.location=loc;o.scale=scale;link(o,col,ma,parent)
    for p in o.data.polygons:p.use_smooth=True
    return o

def cyl(name,a,b,r,col,ma,parent=None,n=20,r2=None):
    a,b=Vector(a),Vector(b);d=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=n,radius1=r,radius2=r if r2 is None else r2,depth=d.length,location=(0,0,0))
    o=bpy.context.object;o.name=name;link(o,col,ma,parent);o.location=(a+b)*.5;o.rotation_mode='QUATERNION';o.rotation_quaternion=d.to_track_quat('Z','Y')
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    be=o.modifiers.new('Machined edges','BEVEL');be.width=min(.004,r*.15);be.segments=2
    return o

def tube(name,pts,r,col,ma,parent=None,cyclic=False):
    cu=bpy.data.curves.new(name+' path','CURVE');cu.dimensions='3D';cu.resolution_u=12;cu.bevel_depth=r;cu.bevel_resolution=3
    sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts):p.co=(*co,1)
    sp.use_cyclic_u=cyclic
    o=bpy.data.objects.new(name,cu);C[col].objects.link(o);cu.materials.append(ma)
    if parent:o.parent=parent
    return o

def empty(name,loc=(0,0,0),parent=None,col='RIG',size=.13):
    o=bpy.data.objects.new(name,None);C[col].objects.link(o);o.location=loc;o.empty_display_type='PLAIN_AXES';o.empty_display_size=size
    if parent:o.parent=parent
    return o

def prop(o,key,val,lo,hi,desc):
    o[key]=float(val);o.id_properties_ui(key).update(min=lo,max=hi,soft_min=lo,soft_max=hi,description=desc)

def driver(o,path,index,expr,variables):
    fc=o.driver_add(path,index) if index is not None else o.driver_add(path)
    d=fc.driver;d.type='SCRIPTED';d.expression=expr
    for name,target,dp in variables:
        v=d.variables.new();v.name=name;v.type='SINGLE_PROP';v.targets[0].id=target;v.targets[0].data_path=dp
    return fc

def pvar(name,o,key):return (name,o,'["'+key+'"]')

def dynamic_rod(name,a,b,r,col,ma,length=None):
    # Local geometry starts at Z=0. Constraints and a distance driver keep endpoints attached.
    n=16;vs=[]
    for z in (0,1):
        for i in range(n):vs.append((r*cos(i*2*pi/n),r*sin(i*2*pi/n),z))
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,vs,fs,col,ma)
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    co=o.constraints.new('COPY_LOCATION');co.target=a
    co=o.constraints.new('DAMPED_TRACK');co.target=b;co.track_axis='TRACK_Z'
    if length is None:
        fc=o.driver_add('scale',2);d=fc.driver;d.expression='distance';v=d.variables.new();v.name='distance';v.type='LOC_DIFF';v.targets[0].id=a;v.targets[1].id=b
    else:o.scale.z=length
    o['endpoint_a']=a.name;o['endpoint_b']=b.name
    return o

def keyprop(o,k,v,f):o[k]=v;o.keyframe_insert(data_path='["'+k+'"]',frame=f)

root=empty('CTRL_VEHICLE_TRAVEL',size=.6)
prop(root,'travel_m',0,-20,80,'Forward travel in meters. Wheel rotation is distance / rolling radius.')
prop(root,'steering_deg',0,-25,25,'Common front steering angle, degrees; animation holds nearly straight.')
prop(root,'body_heave_m',0,-.08,.08,'Smoothed sprung-body vertical displacement in meters.')
prop(root,'body_pitch_deg',0,-5,5,'Sprung body pitch about local Y.')
prop(root,'body_roll_deg',0,-5,5,'Sprung body roll about local X.')
prop(root,'wheel_rotation_offset_deg',0,-360,360,'Offset for wheel spin; travel remains the rotation source.')
root['rolling_radius_m']=R;root['wheelbase_m']=3.2;root['track_m']=TRACK
root['animation_note']='All controls are keyed 1–240. Edit keys or clear selected property animation to pose. Forward +X, right -Y.'
driver(root,'location',0,'distance',[pvar('distance',root,'travel_m')])
body=empty('CTRL_BODY_HEAVE_PITCH_ROLL',parent=root,size=.4)
driver(body,'location',2,'h',[pvar('h',root,'body_heave_m')])
driver(body,'rotation_euler',1,'p*pi/180',[pvar('p',root,'body_pitch_deg')])
driver(body,'rotation_euler',0,'r*pi/180',[pvar('r',root,'body_roll_deg')])
controls={};hubs={};spins={}; shocks={}; leafs={}; arm_rods=[]
for a,x in AXLES.items():
    for s,y in SIDES.items():
        code=a+s;c=empty('CTRL_SUSPENSION_'+code,parent=root)
        prop(c,'travel_m',0,-.08,.08,'Wheel displacement relative to heaved chassis; positive is compression.')
        controls[code]=c
rear=empty('RIG_REAR_SOLID_AXLE',(-1.6,0,R),root)
driver(rear,'location',2,f'{R}+h+(l+r)/2',[pvar('h',root,'body_heave_m'),pvar('l',controls['RL'],'travel_m'),pvar('r',controls['RR'],'travel_m')])
driver(rear,'rotation_euler',0,f'atan2(l-r,{TRACK})',[pvar('l',controls['RL'],'travel_m'),pvar('r',controls['RR'],'travel_m')])
for code,c in controls.items():
    a,s=code;x=AXLES[a];y=SIDES[s]
    if a=='F':
        hub=empty('RIG_HUB_'+code,(x,y,R),root)
        driver(hub,'location',2,f'{R}+h+q',[pvar('h',root,'body_heave_m'),pvar('q',c,'travel_m')])
        driver(hub,'rotation_euler',2,'s*pi/180',[pvar('s',root,'steering_deg')])
    else:hub=empty('RIG_HUB_'+code,(0,y,0),rear)
    hubs[code]=hub
    spin=empty('CTRL_WHEEL_ROTATION_'+code,parent=hub)
    driver(spin,'rotation_euler',1,f'd/{R}+o*pi/180',[pvar('d',root,'travel_m'),pvar('o',root,'wheel_rotation_offset_deg')]);spins[code]=spin

# Compact rough-road profiles, continuous along both wheel tracks.
BUMPS=[(2.7,.048,1.6),(6.4,.060,1.9),(10.8,.047,1.6),(14.7,.055,2.0),(18.9,.082,1.8),(20.9,.064,1.7),(25.5,.058,1.9),(30.0,.043,2.0),(35.1,.055,1.8)]
def ground(x,y):
    right=y<0;z=0
    for i,(center,height,width) in enumerate(BUMPS):
        center+=0 if right else .32
        h=height if right else height*(.50 if i in (4,5) else .76)
        u=(x-center)/(width/2)
        if abs(u)<1:z+=h*(.5+.5*cos(pi*u))
    return z

def contact_height(x,y):
    return max(ground(x+R*(-1+2*i/160),y)+R*sqrt(max(0,1-(-1+2*i/160)**2)) for i in range(161))

def pose(f):
    t=(f-1)/24;d=3*t
    wh={a+s:contact_height(d+x,y)-R for a,x in AXLES.items() for s,y in SIDES.items()}
    # Spatially filtered sprung mass response, smaller than unsprung wheel motion.
    avg={}
    for code in wh:
        a,s=code;avg[code]=sum((1-abs(k)/9)* (contact_height(d+AXLES[a]+k*.13,SIDES[s])-R) for k in range(-8,9))/9
    h=sum(avg.values())/4*.72
    pitch=-(avg['FL']+avg['FR']-avg['RL']-avg['RR'])/2/3.2*.35
    roll=(avg['FL']+avg['RL']-avg['FR']-avg['RR'])/2/TRACK*.3
    return d,h,pitch,roll,{c:z-h for c,z in wh.items()}

for f in range(1,241):
    d,h,pitch,roll,q=pose(f)
    for k,v in [('travel_m',d),('body_heave_m',h),('body_pitch_deg',math.degrees(pitch)),('body_roll_deg',math.degrees(roll)),('steering_deg',0)]:keyprop(root,k,v,f)
    for c,v in q.items():keyprop(controls[c],'travel_m',v,f)

# Primary frame, axle and linkage blockout. Also used for the first rig-only verification.
for s,y in [('L',.48),('R',-.48)]:
    box('Frame rail '+s,(0,y,.69),(4.7,.115,.18),'CHASSIS',steel,body,.022)
for i,x in enumerate([-2.2,-1.05,.02,.88,1.92]):box('Frame crossmember %02d'%i,(x,0,.70),(.11,1.05,.12),'CHASSIS',steel,body)
cyl('Rear axle | rigid driven tube',(0,-.82,0),(0,.82,0),.063,'REAR_SUSPENSION',steel,rear)
uv('Rear differential | cast housing',(0,0,-.005),(.19,.235,.19),'DRIVETRAIN',steel,rear)
for code in ('FL','FR'):
    s=1 if code[-1]=='L' else -1;hub=hubs[code]
    for level,z,wy in [('Lower',.33,.37),('Upper',.65,.44)]:
        bj=empty('Joint '+code+' '+level,(0,-s*.115,z-R),hub)
        for xx in (-.18,.18):
            pivot=empty('Mount '+code+' '+level+str(xx),(1.6+xx,s*wy,z+.015),body)
            rod=dynamic_rod(code+' '+level+' A-arm '+str(xx),pivot,bj,.028 if level=='Lower' else .024,'FRONT_SUSPENSION',alloy)
            arm_rods.append(rod)
        uv(code+' '+level+' ball joint',(0,-s*.115,z-R),(.045,.045,.044),'FRONT_SUSPENSION',black,hub)
    kn=cyl('Steering knuckle '+code,(0,-s*.10,-.09),(0,-s*.10,.23),.045,'FRONT_SUSPENSION',steel,hub)
    top=empty('Shock upper '+code,(1.56,s*.47,.99),body)
    low=empty('Shock lower '+code,(-.06,-s*.17,-.055),hub)
    shocks[code]=(top,low)
    dynamic_rod('Front damper body '+code,top,low,.046,'FRONT_SUSPENSION',brake,.285)
    dynamic_rod('Front damper chrome shaft '+code,low,top,.019,'FRONT_SUSPENSION',chrome)
for code in ('RL','RR'):
    s=1 if code[-1]=='L' else -1
    top=empty('Shock upper '+code,(-2.24,s*.30,.81),body)
    low=empty('Shock lower '+code,(-.10,s*.45,-.025),rear)
    shocks[code]=(top,low)
    dynamic_rod('Rear shock body '+code,top,low,.038,'REAR_SUSPENSION',brake,.30)
    dynamic_rod('Rear shock chrome shaft '+code,low,top,.017,'REAR_SUSPENSION',chrome)
    saddle=empty('Leaf saddle target '+code,(0,s*.57,-.095),rear)
    local_saddle=empty('Leaf local deformation target '+code,(-1.6,s*.57,R-.095),body)
    con=local_saddle.constraints.new('COPY_LOCATION');con.target=saddle
    # A laminated, underslung pack; flex follows the exact body-local saddle position.
    for layer,half in enumerate([.86,.73,.59,.46,.32]):
        vs=[];fs=[];n=40
        for i in range(n+1):
            u=-half+2*half*i/n;z=R-.095+.295*(u/.86)**2-layer*.009
            vs.extend([(-1.6+u,s*.57-.035,z-.004),(-1.6+u,s*.57+.035,z-.004),(-1.6+u,s*.57+.035,z+.004),(-1.6+u,s*.57-.035,z+.004)])
        for i in range(n):
            for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
        fs += [(3,2,1,0),(4*n,4*n+1,4*n+2,4*n+3)]
        o=mesh('Leaf pack '+code+' lamination '+str(layer+1),vs,fs,'REAR_SUSPENSION',leafmat,body,.0015)
        o.shape_key_add(name='Rest manufactured camber');k=o.shape_key_add(name='Compression and rebound',from_mix=False);k.slider_min=-1;k.slider_max=1
        for i,v in enumerate(k.data):
            u=vs[i][0]+1.6;v.co.z+=.12*(1-(u/.86)**2)
        def saddle_driver(key,axis,rest):
            fc=key.driver_add('value');d=fc.driver;d.expression=f'(v-({rest}))/.12'
            v=d.variables.new();v.name='v';v.type='TRANSFORMS';v.targets[0].id=local_saddle
            v.targets[0].transform_type='LOC_'+axis;v.targets[0].transform_space='LOCAL_SPACE'
        saddle_driver(k,'Z',R-.095)
        for axis,label,rest in [(0,'Longitudinal compliance',-1.6),(1,'Axle roll accommodation',s*.57)]:
            sk=o.shape_key_add(name=label,from_mix=False);sk.slider_min=-1;sk.slider_max=1
            for i,v in enumerate(sk.data):v.co[axis]+=.12*(1-((vs[i][0]+1.6)/.86)**2)
            saddle_driver(sk,'XY'[axis],rest)
        leafs.setdefault(code,[]).append(o)

# Driveshafts use live universal-joint endpoints.
transfer_rear=empty('Joint transfer rear',(.16,0,.60),body)
rear_pinion=empty('Joint rear pinion',(.23,0,.015),rear)
rearshaft=dynamic_rod('Rear driveshaft | articulated',transfer_rear,rear_pinion,.038,'DRIVETRAIN',alloy)
transfer_front=empty('Joint transfer front',(.52,-.13,.60),body)
frontdiff=empty('Front differential carrier',(1.60,0,.47),body)
front_pinion=empty('Joint front pinion',(-.20,-.08,.015),frontdiff)
dynamic_rod('Front driveshaft | transfer to IFS differential',transfer_front,front_pinion,.031,'DRIVETRAIN',alloy)
uv('Front differential | compact carrier',(0,0,0),(.18,.23,.14),'DRIVETRAIN',steel,frontdiff)
for code in ('FL','FR'):
    s=1 if code[-1]=='L' else -1
    a=empty('CV inner '+code,(0,s*.18,0),frontdiff);b=empty('CV outer '+code,(0,-s*.08,0),hubs[code])
    dynamic_rod('Front CV halfshaft '+code,a,b,.023,'DRIVETRAIN',alloy)

# Blockout tires, replaced with detailed parametric tires in the complete build.
if rig_only:
    for code,spin in spins.items():cyl('Rig test tire '+code,(0,-.127,0),(0,.127,0),R,'WHEELS',rubber,spin,32)
    box('Rig test sprung body',(0,0,1.12),(4.8,1.75,.42),'BODY',paint,body)
    scene.frame_set(1);bpy.context.view_layer.update()
    scene['build_stage']='Simple rig verified before fine detail'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'rig_prototype.blend'))
    result={'version':bpy.app.version_string,'stage':'rig prototype','frames':[]}
    for f in [1,56,100,151,163,169,176,192,240]:
        scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();d,h,p,r,q=pose(f)
        row={'frame':f,'travel':d,'wheel_error_m':{},'rear_shock_length':None}
        for code,hub in hubs.items():
            p=hub.evaluated_get(dg).matrix_world.translation
            row['wheel_error_m'][code]=p.z-contact_height(p.x,p.y)
        row['rear_shock_length']=(shocks['RR'][0].evaluated_get(dg).matrix_world.translation-shocks['RR'][1].evaluated_get(dg).matrix_world.translation).length
        result['frames'].append(row)
    result['max_contact_error_m']=max(abs(e) for r in result['frames'] for e in r['wheel_error_m'].values())
    assert result['max_contact_error_m']<.002,result
    result['elapsed_seconds']=time.perf_counter()-START
    (ROOT/'reports/rig_prototype.json').write_text(json.dumps(result,indent=2))
    print('RIG_PROTOTYPE_VERIFIED',json.dumps(result));sys.exit(0)

def ring_y(name,profile,col,ma,parent,n=64):
    vs=[(r*cos(i*2*pi/n),y,r*sin(i*2*pi/n)) for y,r in profile for i in range(n)];fs=[]
    for j in range(len(profile)):
        for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i))
    o=mesh(name,vs,fs,col,ma,parent)
    for p in o.data.polygons:p.use_smooth=True
    return o

def text_obj(name,words,loc,size,col,ma,parent=None,rot=(0,0,0),align='CENTER'):
    cu=bpy.data.curves.new(name+' lettering','FONT');cu.body=words;cu.align_x=align;cu.size=size;cu.extrude=.0005;cu.bevel_depth=.0002
    o=bpy.data.objects.new(name,cu);C[col].objects.link(o);cu.materials.append(ma);o.location=loc;o.rotation_euler=rot
    if parent:o.parent=parent
    return o

for code,spin in spins.items():
    s=1 if code[-1]=='L' else -1;hub=hubs[code]
    profile=[(-.118,.232),(-.130,.255),(-.137,.306),(-.130,.347),(-.112,.374),(-.091,.392),(0,.394),(.091,.392),(.112,.374),(.130,.347),(.137,.306),(.130,.255),(.118,.232),(.092,.229),(-.092,.229)]
    ring_y('Tire '+code+' | formed sidewall and carcass',profile,'WHEELS',rubber,spin,96)
    # Staggered three-row individual tread solids, combined only within each tire.
    vs=[];fs=[]
    for i in range(64):
        for row in (-1,0,1):
            ang=2*pi*(i+(.48 if row==0 else 0))/64
            yc=row*.071;rad=.397;radial=Vector((cos(ang),0,sin(ang)));tangent=Vector((-sin(ang),0,cos(ang)));across=Vector((0,1,0))
            center=radial*rad+across*yc
            for rr,tt,yy in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]:
                v=center+radial*(rr*.008)+tangent*(tt*.014+yy*.006*(1 if row>=0 else -1))+across*(yy*.028)
                vs.append(tuple(v))
            k=len(vs)-8
            fs += [tuple(k+j for j in face) for face in [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]]
    mesh('Tread '+code+' | 192 staggered all-terrain blocks',vs,fs,'WHEELS',rubber,spin,.0018)
    for sy in (-1,1):
        ring_y('Sidewall molded bead '+code+str(sy),[(sy*.137,.275),(sy*.138,.278),(sy*.138,.281),(sy*.136,.283)],'WHEELS',rubber,spin)
        ring_y('Sidewall shoulder rib '+code+str(sy),[(sy*.131,.338),(sy*.133,.342),(sy*.131,.346)],'WHEELS',rubber,spin)
    ring_y('Alloy rim barrel '+code,[(-.12,.235),(-.12,.220),(.12,.220),(.12,.235),(.104,.24),(.09,.233),(-.09,.233),(-.104,.24)],'WHEELS',alloy,spin)
    for sy in (-1,1):ring_y('Rim polished lip '+code+str(sy),[(sy*.121,.218),(sy*.125,.221),(sy*.125,.235),(sy*.118,.241)],'WHEELS',chrome,spin)
    for k in range(6):
        for split in (-1,1):
            ang=k*2*pi/6; a=ang+split*.075;b=ang+split*.16
            verts=[]
            for y in (s*.085,s*.119):
                verts.extend([(.069*cos(a-.11),y,.069*sin(a-.11)),(.22*cos(b-.05),y,.22*sin(b-.05)),(.22*cos(b+.05),y,.22*sin(b+.05)),(.069*cos(a+.11),y,.069*sin(a+.11))])
            mesh('Alloy split spoke '+code+f' {k}-{split}',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'WHEELS',alloy,spin,.004)
    cyl('Wheel hub '+code,(0,-.10,0),(0,.10,0),.080,'WHEELS',steel,spin,n=32)
    cyl('Center cap '+code,(0,s*.12,0),(0,s*.136,0),.047,'WHEELS',black,spin,n=32)
    for k in range(6):
        a=k*2*pi/6
        cyl('Lug nut '+code+' '+str(k),(.063*cos(a),s*.118,.063*sin(a)),(.063*cos(a),s*.141,.063*sin(a)),.011,'WHEELS',chrome,spin,n=6)
    # Visible disc plates and an open, ventilated center channel.
    for yy in (-.035,-.011):ring_y('Brake rotor face '+code+str(yy),[(yy,.085),(yy,.186),(yy+.007,.186),(yy+.007,.085)],'WHEELS',alloy,spin)
    for k in range(32):
        a=k*2*pi/32
        ob=box('Rotor cooling vane '+code+' '+str(k),(.14*cos(a),-.018,.14*sin(a)),(.082,.017,.007),'WHEELS',steel,spin,.001)
        ob.rotation_euler.y=-a
    box('Brake caliper '+code,(.133,-s*.058,.092),(.106,.09,.17),'FRONT_SUSPENSION' if code[0]=='F' else 'REAR_SUSPENSION',brake,hub,.026)
    box('Caliper bridge '+code,(.128,-s*.007,.098),(.08,.08,.052),'FRONT_SUSPENSION' if code[0]=='F' else 'REAR_SUSPENSION',brake,hub,.012)
    # Tire lettering is editable geometry and rotates with the tire.
    text_obj('Tire molded lettering '+code,'TERRA  /  A-T',(-.005,s*.138,.304),.028,'WHEELS',steel,spin,(pi/2 if s<0 else -pi/2,0,0))
    text_obj('Tire size '+code,'265 / 65  R18',(0,s*.139,-.318),.020,'WHEELS',steel,spin,(pi/2 if s<0 else -pi/2,0,0))

# A formed side panel with true wheel-arch void; no hidden box across the tire.
def side_panel(name,xmin,xmax,cx,y,top,bottom,col='BODY'):
    rr=.476; poly=[(xmin,bottom),(xmin,top),(xmax,top),(xmax,bottom),(cx+rr,bottom),(cx+rr,R)]
    poly += [(cx+rr*cos(a),R+rr*sin(a)) for a in [pi*i/32 for i in range(33)]]
    poly += [(cx-rr,bottom)]
    verts=[(x,yy,z) for yy in (y-.025,y+.025) for x,z in poly];n=len(poly)
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,verts,fs,col,paint,body,.009)

# Hood is a contoured closed shell with a subtle center crown.
vs=[]
sections=[(.91,.865,1.32),(1.13,.878,1.385),(2.30,.84,1.32),(2.56,.81,1.22)]
for x,w,z in sections:vs += [(x,-w,z-.075),(x,-w,z),(x,-w*.62,z+.024),(x,w*.62,z+.024),(x,w,z),(x,w,z-.075)]
fs=[tuple(range(5,-1,-1)),tuple(range(18,24))]
for j in range(3):
    for k in range(6):fs.append((6*j+k,6*j+(k+1)%6,6*(j+1)+(k+1)%6,6*(j+1)+k))
mesh('Hood | crowned one-piece pressing',vs,fs,'BODY',paint,body,.021)
box('Cowl below windshield',(.965,0,1.28),(.13,1.68,.095),'BODY',black,body)
for s,y in [('L',.891),('R',-.891)]:
    sign=1 if y>0 else -1
    side_panel('Front fender '+s,.99,2.59,1.6,y,1.278,.66)
    side_panel('Bed side '+s,-2.60,-1.045,-1.6,y,1.285,.66)
    for label,cx in [('Front',1.6),('Rear',-1.6)]:
        # Extruded annular lip follows the opening, independent from side sheet metal.
        vs=[];fs=[]
        for i in range(41):
            a=pi*i/40
            for rr,yy in [(.468,y+sign*.002),(.511,y+sign*.008),(.511,y+sign*.050),(.468,y+sign*.050)]:vs.append((cx+rr*cos(a),yy,R+rr*sin(a)))
        for i in range(40):
            for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
        mesh(label+' wheel arch flare '+s,vs,fs,'BODY',black,body,.005)
        # Inboard wheelhouse arch, only above the wheel.
        pts=[(cx+.501*cos(pi*i/32),y-sign*.10,R+.501*sin(pi*i/32)) for i in range(33)]
        tube(label+' wheelhouse inner rolled edge '+s,pts,.014,'BODY',black,body)
    box('Rocker sill '+s,(-.025,y-sign*.032,.807),(2.04,.092,.075),'BODY',black,body)
    box('Running board '+s,(-.05,y+sign*.055,.65),(1.93,.21,.055),'BODY',steel,body,.018)
    for x in (-.75,.64):box('Running board chassis mount '+s+str(x),(x,sign*.70,.66),(.085,.37,.055),'CHASSIS',steel,body)
    for i,(x0,x1) in enumerate([(-1.025,-.068),(-.045,.977)]):
        # The dark backing and separated sheet metal leave a real, visible door gap.
        box('Door seam backing '+s+str(i),((x0+x1)/2,y-sign*.024,1.045),(x1-x0+.016,.026,.464),'BODY',black,body,.012)
        poly=[(x0,.847),(x1,.847),(x1,1.282),(x0,1.282)]
        v=[(x,yy,z) for yy in (y-sign*.018,y+sign*.008) for x,z in poly]
        mesh(('Rear' if i==0 else 'Front')+' door skin '+s,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'BODY',paint,body,.024)
        box('Door character line '+s+str(i),((x0+x1)/2,y+sign*.013,1.195),(x1-x0-.045,.012,.018),'BODY',paint,body,.005)
        hx=x0+.17
        box('Handle recess '+s+str(i),(hx,y+sign*.025,1.234),(.20,.022,.053),'BODY',black,body,.02)
        box('Door pull '+s+str(i),(hx,y+sign*.051,1.246),(.139,.033,.024),'BODY',alloy,body,.009)
    # Actual sloped side glazing: quad meshes with laminated thickness.
    for label,pts in [('Rear',[(-1.013,1.323),(-.104,1.323),(-.104,1.759),(-.887,1.759)]),('Front',[(-.022,1.323),(.922,1.323),(.491,1.759),(-.022,1.759)])]:
        co=[(x,sign*(.892-(z-1.3)*.245),z) for x,z in pts]
        o=mesh(label+' door glazing '+s,co,[(3,2,1,0) if sign>0 else (0,1,2,3)],'BODY',glass,body);mod=o.modifiers.new('Laminated glass 8 mm','SOLIDIFY');mod.thickness=.008
        tube(label+' window gasket '+s,co,.017,'BODY',black,body,True)
    for label,a,b,rad in [('A',(.98,sign*.889,1.29),(.505,sign*.779,1.798),.042),('B',(-.06,sign*.89,1.29),(-.06,sign*.779,1.798),.035),('C',(-1.048,sign*.889,1.29),(-.93,sign*.779,1.798),.043)]:
        cyl(label+' pillar '+s,a,b,rad,'BODY',paint if label!='B' else black,body,n=12)
    # Mirror base, articulated neck, shaped housing and mirror glass.
    box('Mirror sail '+s,(.855,sign*.904,1.36),(.14,.065,.16),'BODY',black,body,.026)
    cyl('Mirror arm '+s,(.79,sign*.91,1.391),(.75,sign*1.045,1.425),.028,'BODY',black,body)
    box('Mirror housing '+s,(.735,sign*1.076,1.46),(.23,.14,.14),'BODY',paint,body,.046)
    box('Mirror glass '+s,(.611,sign*1.079,1.466),(.009,.106,.09),'BODY',chrome,body,.01)
    box('Mirror signal strip '+s,(.855,sign*1.089,1.445),(.014,.10,.012),'BODY',lightmat,body,.004)
box('Cab roof | soft rectangular pressing',(-.206,0,1.815),(1.53,1.64,.085),'BODY',paint,body,.064)
for s in (-1,1):
    tube('Roof rain gutter '+str(s),[(-.90,s*.806,1.841),(.45,s*.806,1.841)],.008,'BODY',black,body)
    for x in (-.72,.32):box('Roof rail pedestal '+str(s)+str(x),(x,s*.60,1.872),(.14,.055,.03),'BODY',black,body,.011)
    tube('Low roof rail '+str(s),[(-.78,s*.60,1.90),(.39,s*.60,1.90)],.018,'BODY',steel,body)
co=[(1.008,-.847,1.322),(1.008,.847,1.322),(.519,.756,1.779),(.519,-.756,1.779)]
o=mesh('Windshield | thick sloped laminated glass',co,[(0,1,2,3)],'BODY',glass,body);o.modifiers.new('Windshield 10 mm','SOLIDIFY').thickness=.01
tube('Windshield perimeter gasket',co,.019,'BODY',black,body,True)
for y in (-.43,.36):
    cyl('Wiper arm '+str(y),(1.032,y,1.335),(.90,y+.10,1.46),.006,'BODY',steel,body)
    tube('Wiper blade '+str(y),[(.905,y-.11,1.45),(.905,y+.23,1.45)],.009,'BODY',black,body)
box('Cab rear lower bulkhead',(-1.031,0,1.057),(.063,1.77,.465),'BODY',paint,body,.014)
co=[(-1.025,-.79,1.322),(-1.025,.79,1.322),(-.932,.745,1.765),(-.932,-.745,1.765)]
o=mesh('Cab rear window',co,[(3,2,1,0)],'BODY',glass,body);o.modifiers.new('Rear glass 8 mm','SOLIDIFY').thickness=.008
tube('Rear glass gasket',co,.018,'BODY',black,body,True)
for y in (-.24,.24):tube('Rear sliding glass divider '+str(y),[(-1.022,y,1.33),(-.936,y,1.75)],.009,'BODY',black,body)
for sign in (-1,1):box('Cab interior floor '+str(sign),(-.07,sign*.535,.858),(1.92,.60,.045),'INTERIOR',black,body,.02)
mesh('Raised transmission tunnel',[(-1.03,-.235,.858),(-1.03,-.19,1.03),(-1.03,.19,1.03),(-1.03,.235,.858),(.91,-.235,.858),(.91,-.19,1.03),(.91,.19,1.03),(.91,.235,.858)],[(0,4,5,1),(1,5,6,2),(2,6,7,3)],'INTERIOR',black,body,.018)
# Open cargo bed with wheel tubs, liner ribs, separate tailgate and metal tie-downs.
box('Bed liner floor',(-1.86,0,.903),(1.52,1.69,.075),'BODY',black,body,.012)
box('Bed forward bulkhead',(-1.079,0,1.116),(.055,1.74,.335),'BODY',paint,body)
for y in [i*.098 for i in range(-8,9)]:box('Bed raised liner rib '+str(y),(-1.856,y,.945),(1.43,.028,.018),'BODY',black,body,.006)
for s in (-1,1):
    box('Bed rail cap '+str(s),(-1.835,s*.892,1.296),(1.60,.10,.033),'BODY',black,body,.011)
    box('Bed inner wall '+str(s),(-1.835,s*.853,1.118),(1.49,.032,.30),'BODY',black,body,.008)
    box('Bed wheel tub '+str(s),(-1.60,s*.736,.99),(.97,.255,.173),'BODY',black,body,.075)
    for x in (-2.43,-1.23):
        tube('Cargo tie-down '+str(s)+str(x),[(x-.035,s*.808,1.18),(x-.035,s*.788,1.14),(x+.035,s*.788,1.14),(x+.035,s*.808,1.18)],.009,'BODY',alloy,body)
box('Tailgate gap backing',(-2.595,0,1.061),(.047,1.77,.458),'BODY',black,body)
box('Tailgate | separated pressed skin',(-2.624,0,1.066),(.053,1.688,.424),'BODY',paint,body,.025)
box('Tailgate top protector',(-2.62,0,1.292),(.102,1.745,.035),'BODY',black,body,.012)
box('Tailgate handle recess',(-2.660,0,1.222),(.013,.256,.056),'BODY',black,body,.017)
box('Tailgate handle metal',(-2.671,0,1.23),(.014,.17,.024),'BODY',alloy,body,.005)
for y in (-.59,.59):cyl('Tailgate hinge '+str(y),(-2.607,y-.06,.87),(-2.607,y+.06,.87),.022,'BODY',steel,body)
# Front fascia: recessed real grille openings, warm corner modules, separate bash bar.
box('Front fascia bridge',(2.574,0,1.191),(.12,1.67,.095),'BODY',paint,body,.03)
box('Front grille dark recess',(2.57,0,1.012),(.075,1.19,.306),'BODY',black,body,.032)
for z in (.89,.969,1.048,1.127):box('Grille horizontal bar '+str(z),(2.627,0,z),(.035,1.17,.015),'BODY',steel,body,.005)
for y in [i*.075 for i in range(-7,8)]:box('Grille vertical fin '+str(y),(2.618,y,1.01),(.026,.011,.248),'BODY',steel,body,.004)
for s in (-1,1):
    box('Headlight black module '+str(s),(2.55,s*.697,1.076),(.16,.272,.239),'BODY',black,body,.034)
    box('Headlamp glazing '+str(s),(2.641,s*.697,1.076),(.017,.247,.209),'BODY',glass,body,.019)
    for y in (s*.642,s*.751):
        cyl('LED projector bezel '+str(y),(2.639,y,1.092),(2.661,y,1.092),.045,'BODY',alloy,body,n=32)
        cyl('LED projector optic '+str(y),(2.662,y,1.092),(2.669,y,1.092),.033,'BODY',lightmat,body,n=32)
    tube('Daytime lamp signature '+str(s),[(2.674,s*.59,1.159),(2.674,s*.792,1.159),(2.674,s*.804,1.013)],.009,'BODY',lightmat,body)
    box('Front turn signal '+str(s),(2.667,s*.697,.998),(.012,.19,.013),'BODY',amber,body,.004)
    box('Taillamp housing '+str(s),(-2.599,s*.859,1.095),(.09,.107,.331),'BODY',black,body,.026)
    box('Taillamp red lens '+str(s),(-2.651,s*.859,1.11),(.018,.085,.287),'BODY',red,body,.018)
    for z in (1.01,1.10,1.20):box('Rear LED blade '+str(s)+str(z),(-2.664,s*.859,z),(.012,.062,.035),'BODY',redlight,body,.009)
    box('Rear reversing lamp '+str(s),(-2.666,s*.859,1.055),(.013,.063,.024),'BODY',lightmat,body,.006)
box('Front bumper | graphite center',(2.548,0,.751),(.25,1.32,.181),'BODY',black,body,.048)
for s in (-1,1):
    box('Front bumper corner '+str(s),(2.47,s*.735,.752),(.31,.30,.162),'BODY',black,body,.056)
    box('Front recovery eye base '+str(s),(2.66,s*.463,.707),(.048,.07,.095),'CHASSIS',steel,body,.012)
    tube('Front recovery loop '+str(s),[(2.691,s*.50,.716),(2.736,s*.50,.65),(2.736,s*.43,.65),(2.691,s*.43,.716)],.013,'CHASSIS',accent,body)
box('Rear bumper | step center',(-2.606,0,.752),(.23,1.82,.146),'BODY',black,body,.037)
for s in (-1,1):
    box('Rear step tread '+str(s),(-2.675,s*.598,.83),(.24,.55,.021),'BODY',rubber,body,.006)
    for i in range(5):box('Rear step grip '+str(s)+str(i),(-2.675,s*.598+(i-2)*.087,.843),(.18,.017,.006),'BODY',steel,body,.002)
box('Tow receiver crossbar',(-2.33,0,.592),(.12,1.05,.10),'CHASSIS',steel,body)
box('Tow hitch receiver',(-2.555,0,.574),(.48,.09,.09),'CHASSIS',steel,body,.012)
box('Tow receiver dark aperture',(-2.802,0,.574),(.006,.065,.065),'CHASSIS',black,body,.003)
box('Hitch ball tongue',(-2.82,0,.552),(.26,.073,.035),'CHASSIS',steel,body)
cyl('Hitch ball neck',(-2.914,0,.57),(-2.914,0,.625),.022,'CHASSIS',chrome,body)
uv('Hitch tow ball',(-2.914,0,.648),(.029,.029,.029),'CHASSIS',chrome,body)
# Visible, modeled interior: five seats, dash, console, controls and door cards.
for label,x,ys in [('Front',.29,(-.435,.435)),('Rear',-.61,(-.53,0,.53))]:
    for i,y in enumerate(ys):
        box(label+' seat cushion '+str(i),(x,y,1.003),(.43,.40 if label=='Front' else .43,.136),'INTERIOR',seatmat,body,.064)
        ob=box(label+' seat back '+str(i),(x-.206,y,1.253),(.113,.408,.444),'INTERIOR',seatmat,body,.053);ob.rotation_euler.y=-.13
        box(label+' headrest '+str(i),(x-.235,y,1.54),(.115,.229,.144),'INTERIOR',black,body,.04)
        for yy in (y-.065,y+.065):cyl('Headrest stalk '+label+str(i)+str(yy),(x-.224,yy,1.42),(x-.23,yy,1.51),.008,'INTERIOR',chrome,body)
        for yy in (y-.13,y+.13):tube('Seat seam '+label+str(i)+str(yy),[(x-.09,yy,1.077),(x+.13,yy,1.077)],.002,'INTERIOR',steel,body)
        box('Seatbelt buckle '+label+str(i),(x-.06,y+.205,1.06),(.042,.032,.072),'INTERIOR',brake,body,.009)
box('Dashboard main shell',(.775,0,1.203),(.38,1.58,.216),'INTERIOR',black,body,.065)
box('Dashboard brushed strip',(.555,0,1.25),(.028,1.42,.029),'INTERIOR',alloy,body,.005)
for y in (-.63,-.28,.29,.63):
    box('Air vent surround '+str(y),(.566,y,1.289),(.025,.164,.070),'INTERIOR',steel,body,.011)
    for z in (1.27,1.288,1.306):box('Air vent slat '+str(y)+str(z),(.549,y,z),(.01,.137,.006),'INTERIOR',black,body,.001)
box('Instrument binnacle',(.561,.426,1.346),(.144,.352,.143),'INTERIOR',black,body,.035)
box('Instrument dark glass',(.483,.426,1.35),(.010,.291,.080),'INTERIOR',glass,body,.009)
box('Center display',(.558,0,1.357),(.037,.249,.15),'INTERIOR',steel,body,.012)
box('Display glass',(.534,0,1.358),(.008,.219,.12),'INTERIOR',glass,body,.005)
box('Center console',(.139,0,1.003),(.63,.22,.237),'INTERIOR',black,body,.045)
cyl('Gear selector',(.296,0,1.10),(.275,0,1.23),.019,'INTERIOR',alloy,body)
uv('Gear knob',(.275,0,1.234),(.038,.033,.034),'INTERIOR',black,body)
for x in (-.05,.095):
    ring_y('Console cupholder '+str(x),[(0,.039),(.025,.039),(.026,.049),(0,.049)],'INTERIOR',black,body).rotation_euler.x=pi/2
    o=bpy.data.objects['Console cupholder '+str(x)];o.location=(x,0,1.127)
cyl('Steering column',(.70,.435,1.17),(.365,.435,1.299),.027,'INTERIOR',steel,body)
steer=empty('Interior steering wheel pivot',(.345,.435,1.306),body)
steer.rotation_euler.y=pi/2-.27
# Steering rim is an actual round tube in its local XY plane.
tube('Steering wheel rim',[(.164*cos(i*2*pi/64),.164*sin(i*2*pi/64),0) for i in range(64)],.016,'INTERIOR',black,steer,True)
for a in (0,pi,1.5*pi):cyl('Steering wheel spoke '+str(a),(0,0,0),(.148*cos(a),.148*sin(a),0),.018,'INTERIOR',alloy,steer)
uv('Steering wheel airbag',(0,0,0),(.068,.062,.03),'INTERIOR',black,steer)
for s in (-1,1):
    for x in (-.59,.48):
        box('Interior door card '+str(s)+str(x),(x,s*.834,1.083),(.87,.056,.331),'INTERIOR',black,body,.024)
        box('Interior door armrest '+str(s)+str(x),(x,s*.799,1.117),(.39,.066,.056),'INTERIOR',seatmat,body,.016)
# Engine, transmission and transfer case remain individually editable.
box('Engine | inline four cast block',(1.63,0,.958),(.68,.48,.42),'DRIVETRAIN',steel,body,.066)
box('Engine cylinder head',(1.60,0,1.184),(.69,.45,.106),'DRIVETRAIN',alloy,body,.025)
box('Engine valve cover',(1.59,0,1.255),(.59,.366,.065),'DRIVETRAIN',black,body,.023)
box('Engine oil sump',(1.67,0,.695),(.45,.345,.164),'DRIVETRAIN',alloy,body,.04)
for x in (1.39,1.57,1.75,1.93):
    tube('Exhaust manifold runner '+str(x),[(x,-.24,1.075),(x,-.303,1.035),(1.26,-.337,.939)],.024,'DRIVETRAIN',alloy,body)
    cyl('Intake runner '+str(x),(x,.223,1.10),(x,.317,1.11),.039,'DRIVETRAIN',black,body)
box('Intake plenum',(1.61,.337,1.103),(.67,.132,.123),'DRIVETRAIN',black,body,.03)
cyl('Transmission bellhousing',(1.23,0,.878),(.957,0,.797),.226,'DRIVETRAIN',alloy,body,n=32,r2=.18)
cyl('Transmission | longitudinal case',(.969,0,.797),(.397,0,.675),.178,'DRIVETRAIN',alloy,body,n=32,r2=.108)
for i in range(8):
    x=.46+i*.066;z=.675+(x-.397)/(.969-.397)*.122
    cyl('Transmission cast rib '+str(i),(x-.01,0,z),(x+.013,0,z),.123+(x-.397)*.096,'DRIVETRAIN',steel,body,n=24)
box('Transfer case | offset front output',(.318,-.065,.642),(.28,.37,.256),'DRIVETRAIN',alloy,body,.054)
for s in (-1,1):
    box('Engine mount bracket '+str(s),(1.54,s*.376,.844),(.22,.233,.080),'CHASSIS',steel,body)
    cyl('Engine mount bushing '+str(s),(1.54,s*.35,.83),(1.54,s*.35,.885),.057,'CHASSIS',rubber,body)
box('Gearbox mount saddle',(.37,0,.568),(.138,.46,.061),'CHASSIS',rubber,body,.012)
# Radiator lies inside the nose; independent fins and support frame.
box('Radiator core',(2.333,0,1.028),(.066,1.24,.377),'DRIVETRAIN',steel,body,.014)
for y in [i*.042 for i in range(-14,15)]:box('Radiator fin '+str(y),(2.294,y,1.033),(.018,.012,.329),'DRIVETRAIN',alloy,body,.002)
for y in (-.678,.678):box('Radiator support '+str(y),(2.301,y,.994),(.114,.067,.537),'CHASSIS',steel,body)
# Tank and exhaust occupy opposite sides of the driveline corridor.
box('Fuel tank | left side protected polymer',(-.43,.253,.612),(.98,.30,.248),'DRIVETRAIN',black,body,.071)
for x in (-.79,-.11):
    tube('Fuel tank retaining strap '+str(x),[(x,.085,.692),(x,.09,.502),(x,.14,.471),(x,.399,.471),(x,.417,.506),(x,.466,.70)],.014,'CHASSIS',alloy,body)
tube('Fuel filler neck',[(-.70,.375,.72),(-.78,.375,.84),(-1.10,.66,.91),(-1.18,.89,1.15)],.027,'DRIVETRAIN',black,body)
box('Fuel flap gasket',(-1.18,.922,1.154),(.151,.015,.138),'BODY',black,body,.027)
box('Fuel flap | flush bed-side door',(-1.18,.932,1.154),(.135,.015,.122),'BODY',paint,body,.024)
# Exhaust is outboard of the right rail, leaving RR shock and leaf visible inboard.
exhaustpts=[(1.26,-.337,.939),(1.23,-.365,.724),(1.20,-.365,.545),(1.05,-.646,.54),(.72,-.673,.52),(.10,-.673,.505),(-.47,-.673,.507),(-.80,-.650,.53),(-1.08,-.640,.71),(-1.43,-.640,.802),(-1.77,-.640,.802),(-2.0,-.691,.68),(-2.35,-.741,.557),(-2.47,-.897,.535)]
tube('Exhaust | continuous right-side routing',exhaustpts,.024,'DRIVETRAIN',alloy,body)
cyl('Catalytic converter',(1.03,-.66,.565),(.72,-.673,.52),.064,'DRIVETRAIN',alloy,body,n=24)
cyl('Muffler | oval silencer',(.08,-.673,.505),(-.45,-.673,.507),.071,'DRIVETRAIN',steel,body,n=32)
cyl('Exhaust tip',(-2.40,-.79,.55),(-2.49,-.931,.529),.033,'DRIVETRAIN',chrome,body,n=24)
for x,z in ((.5,.67),(-.5,.65),(-2.12,.75)):
    tube('Exhaust hanger '+str(x),[(x,-.47,z),(x,-.615,z),(x,-.675,z-.13)],.01,'CHASSIS',steel,body)
    uv('Exhaust rubber isolator '+str(x),(x,-.61,z-.01),(.025,.018,.04),'CHASSIS',rubber,body)
for i,(x,z,length) in enumerate([(.77,.685,.56),(-.22,.68,.69),(-1.58,.851,.72)]):
    box('Exhaust heat shield '+str(i),(x,-.67,z),(length,.20,.012),'DRIVETRAIN',alloy,body,.021)
    for xx in [x-length*.37,x,x+length*.37]:box('Heat shield pressed rib '+str(i)+str(xx),(xx,-.67,z-.01),(.015,.185,.008),'DRIVETRAIN',steel,body,.002)
# Limited protection at nose and transfer case; central and rear drivetrain stays open.
ob=box('Front bash plate | limited engine protection',(2.08,0,.584),(.45,.74,.035),'CHASSIS',alloy,body,.018);ob.rotation_euler.y=-.23
box('Transfer skid | small serviceable plate',(.26,0,.465),(.36,.38,.025),'CHASSIS',alloy,body,.012)
for x in (.12,.40):
    for y in (-.14,.14):cyl('Transfer skid bolt '+str(x)+str(y),(x,y,.448),(x,y,.468),.012,'CHASSIS',steel,body,n=6)
# Differential cover, flange fasteners and axle end bearing housings.
cyl('Rear differential cover',(-.162,0,-.005),(-.194,0,-.005),.163,'DRIVETRAIN',alloy,rear,n=16)
for i in range(10):
    a=i*2*pi/10;y=.143*cos(a);z=-.005+.143*sin(a)
    cyl('Rear differential cover bolt '+str(i),(-.2,y,z),(-.209,y,z),.010,'DRIVETRAIN',steel,rear,n=6)
for s in (-1,1):
    cyl('Rear wheel bearing housing '+str(s),(0,s*.703,0),(0,s*.784,0),.085,'REAR_SUSPENSION',steel,rear,n=24)
    # Leaf saddles sit on the rigid axle; U-bolts wrap the axle and clamp five leaves.
    box('Leaf spring saddle '+str(s),(0,s*.57,-.094),(.155,.119,.025),'REAR_SUSPENSION',steel,rear,.008)
    box('Leaf pack clamp plate '+str(s),(0,s*.57,-.151),(.183,.128,.017),'REAR_SUSPENSION',alloy,rear,.004)
    for xx in (-.057,.057):
        pts=[(xx,s*.57-.049,-.162),(xx,s*.57-.049,.045)]
        pts += [(xx,s*.57-.049*cos(i*pi/12),.045+.049*sin(i*pi/12)) for i in range(13)]
        pts += [(xx,s*.57+.049,-.162)]
        tube('Axle U-bolt '+str(s)+str(xx),pts,.008,'REAR_SUSPENSION',alloy,rear)
        for yy in (s*.57-.049,s*.57+.049):cyl('U-bolt retaining nut '+str(s)+str(xx)+str(yy),(xx,yy,-.17),(xx,yy,-.149),.013,'REAR_SUSPENSION',steel,rear,n=6)
    for xx,label in [(-.74,'Front fixed eye'),(-2.46,'Rear shackle')]:
        # Body-mounted eyes and short shackle links.
        cyl(label+' bushing '+str(s),(xx,s*.57-.047,.605),(xx,s*.57+.047,.605),.041,'REAR_SUSPENSION',rubber,body,n=24)
        cyl(label+' through bolt '+str(s),(xx,s*.57-.065,.605),(xx,s*.57+.065,.605),.015,'REAR_SUSPENSION',alloy,body,n=6)
        for yy in (s*.57-.055,s*.57+.055):
            box(label+' mounting cheek '+str(s)+str(yy),(xx,yy,.657),(.091,.015,.16),'REAR_SUSPENSION',steel,body,.008)
        box(label+' frame outrigger '+str(s),(xx,s*.525,.735),(.135,.198,.045),'CHASSIS',steel,body,.009)
    box('Rear upper damper frame bracket '+str(s),(-2.24,s*.39,.798),(.13,.26,.044),'REAR_SUSPENSION',steel,body,.009)
    # Rear brake plumbing moves with the axle. Center flexible loop is a separate hose.
    tube('Rear axle brake hardline '+str(s),[(0,0,.087),(-.028,s*.29,.085),(-.04,s*.65,.077),(.075,s*.75,.09)],.006,'REAR_SUSPENSION',alloy,rear)
    tube('Rear caliper flexible hose '+str(s),[(.075,s*.75,.09),(.13,s*.70,.11),(.18,s*.73,.10),(.15,s*.80,.095)],.008,'REAR_SUSPENSION',rubber,rear)
rearhose=tube('Rear brake distribution flex loop',[(-1.31,.16,.72),(-1.46,.15,.60),(-1.59,.15,.51),(-1.628,.15,.490)],.008,'REAR_SUSPENSION',rubber,body)
rearhose.shape_key_add(name='Rest brake hose loop')
key=rearhose.shape_key_add(name='Axle hose articulation',from_mix=False);key.slider_min=-1;key.slider_max=1
for i,p in enumerate(key.data):p.co.z+=.12*(i/(len(key.data)-1))**2
driver(key,'value',None,'((l+r)/2+.15/1.66*(l-r)-1.6*p*pi/180-.15*q*pi/180)/.12',[pvar('l',controls['RL'],'travel_m'),pvar('r',controls['RR'],'travel_m'),pvar('p',root,'body_pitch_deg'),pvar('q',root,'body_roll_deg')])
# Front suspension detail, actual springs around only the front dampers.
for code in ('FL','FR'):
    s=1 if code[-1]=='L' else -1;hub=hubs[code];top,low=shocks[code]
    pts=[]
    for i in range(241):
        t=i/240;a=t*8*2*pi;pts.append((.076*cos(a),.076*sin(a),.10+t*.72))
    o=tube('Front coil spring '+code,pts,.011,'FRONT_SUSPENSION',steel)
    co=o.constraints.new('COPY_LOCATION');co.target=top
    co=o.constraints.new('DAMPED_TRACK');co.target=low;co.track_axis='TRACK_Z'
    fc=o.driver_add('scale',2);d=fc.driver;d.expression='L';v=d.variables.new();v.name='L';v.type='LOC_DIFF';v.targets[0].id=top;v.targets[1].id=low
    dynamic_rod('Front upper spring seat '+code,top,low,.092,'FRONT_SUSPENSION',alloy,.028)
    dynamic_rod('Front lower spring seat '+code,low,top,.088,'FRONT_SUSPENSION',alloy,.045)
    for xx in (1.42,1.78):
        for z,yy in ((.345,.37),(.665,.44)):
            cyl('Wishbone pivot sleeve '+code+str(xx)+str(z),(xx-.049,s*yy,z),(xx+.049,s*yy,z),.045,'FRONT_SUSPENSION',rubber,body)
            cyl('Wishbone pivot bolt '+code+str(xx)+str(z),(xx-.06,s*yy,z),(xx+.06,s*yy,z),.015,'FRONT_SUSPENSION',alloy,body,n=6)
            for xoff in (-.055,.055):box('Wishbone frame tab '+code+str(xx)+str(z)+str(xoff),(xx+xoff,s*yy,z+.046),(.017,.093,.126),'FRONT_SUSPENSION',steel,body,.006)
    box('Upper shock tower '+code,(1.56,s*.473,.95),(.162,.197,.183),'FRONT_SUSPENSION',steel,body,.026)
    cyl('Top shock mount bolt '+code,(1.56,s*.41,.99),(1.56,s*.56,.99),.017,'FRONT_SUSPENSION',alloy,body,n=6)
    a=empty('Steering rack end '+code,(1.33,s*.41,.52),body)
    b=empty('Steering arm joint '+code,(-.125,-s*.101,.055),hub)
    dynamic_rod('Steering tie rod '+code,a,b,.014,'FRONT_SUSPENSION',alloy)
    cyl('Knuckle steering arm '+code,(0,-s*.1,.02),(-.125,-s*.101,.055),.026,'FRONT_SUSPENSION',steel,hub)
    uv('Tie rod ball end '+code,(-.125,-s*.101,.055),(.023,.025,.023),'FRONT_SUSPENSION',black,hub)
    for end,label in [('CV inner '+code,'inboard'),('CV outer '+code,'outboard')]:
        anchor=bpy.data.objects[end];other=bpy.data.objects['CV outer '+code if label=='inboard' else 'CV inner '+code]
        for k in range(5):
            # Bellows shells anchored to the correct live endpoint, with a fixed boot length.
            ob=dynamic_rod('CV boot '+code+' '+label+' rib '+str(k),anchor,other,.050-k*.004,'DRIVETRAIN',rubber,.015)
            # Geometry offset along the tracked axis, leaving the anchor unchanged.
            for vv in ob.data.vertices:vv.co.z+=k*1.05
    pts=[(1.38,s*.49,.83),(1.31,s*.60,.76),(1.31,s*.70,.63),(1.45,s*.75,.54),(1.67,s*.77,.50)]
    hose=tube('Front brake flex hose '+code,pts,.008,'FRONT_SUSPENSION',rubber,body)
    # Endpoint deforms with wheel travel; rubber hose naturally changes curvature.
    # Curve shape keys are native and work after opening without Python handlers.
    hose.shape_key_add(name='Rest hose loop');k=hose.shape_key_add(name='Wheel articulation');k.slider_min=-1;k.slider_max=1
    for i,p in enumerate(k.data):p.co.z+=.12*(i/(len(k.data)-1))**2
    driver(k,'value',None,'q/.12',[pvar('q',controls[code],'travel_m')])
cyl('Steering rack | central housing',(1.33,-.40,.52),(1.33,.40,.52),.039,'FRONT_SUSPENSION',steel,body)
for s in (-1,1):
    for i in range(6):cyl('Rack bellows '+str(s)+str(i),(1.33,s*(.30+i*.017),.52),(1.33,s*(.31+i*.017),.52),.048,'FRONT_SUSPENSION',rubber,body)
tube('Steering intermediate shaft',[(1.32,.19,.56),(1.18,.27,.79),(.83,.425,1.10)],.016,'DRIVETRAIN',alloy,body)
# Fasteners and body isolators on every main crossmember.
for x in (-2.20,-1.05,.02,.88,1.92):
    for s in (-1,1):
        cyl('Body isolation mount '+str(x)+str(s),(x,s*.48,.773),(x,s*.48,.845),.039,'CHASSIS',rubber,body)
        for dx in (-.035,.035):cyl('Frame crossmember bolt '+str(x)+str(s)+str(dx),(x+dx,s*.48,.794),(x+dx,s*.48,.810),.011,'CHASSIS',alloy,body,n=6)
for code,(top,low) in shocks.items():
    for anchor,label in [(top,'upper'),(low,'lower')]:
        cyl('Shock eye '+code+' '+label,(0,-.035,0),(0,.035,0),.039,'FRONT_SUSPENSION' if code[0]=='F' else 'REAR_SUSPENSION',steel,anchor)
        cyl('Shock eye bushing '+code+' '+label,(0,-.037,0),(0,.037,0),.022,'FRONT_SUSPENSION' if code[0]=='F' else 'REAR_SUSPENSION',rubber,anchor)
        cyl('Shock eye through bolt '+code+' '+label,(0,-.049,0),(0,.049,0),.012,'FRONT_SUSPENSION' if code[0]=='F' else 'REAR_SUSPENSION',alloy,anchor,n=6)
# Universal-joint yokes visually connect both articulated propeller shafts.
for anchor in (transfer_rear,rear_pinion,transfer_front,front_pinion):
    uv('Universal joint cross '+anchor.name,(0,0,0),(.050,.049,.049),'DRIVETRAIN',steel,anchor)
    cyl('Universal joint bearing '+anchor.name,(0,-.058,0),(0,.058,0),.023,'DRIVETRAIN',alloy,anchor)
# Test-road geometry, 25 mm longitudinal sampling. The central channel is open.
for s in (-1,1):
    vs=[];fs=[];n=2800
    for i in range(n+1):
        x=-12+70*i/n;z=ground(x,s*.83)
        vs += [(x,s*.60,z),(x,s*1.10,z),(x,s*1.10,-.68),(x,s*.60,-.68)]
    for i in range(n):
        for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    fs += [(3,2,1,0),(4*n,4*n+1,4*n+2,4*n+3)]
    mesh('Continuous wheel track '+('left' if s>0 else 'right'),vs,fs,'ROAD',roadmat)
    box('Outer concrete apron '+str(s),(23,s*5.05,-.09),(70,7.9,.18),'ROAD',roadmat,bev=.015)
    box('Inspection channel wall '+str(s),(23,s*.565,-.345),(70,.07,.67),'ROAD',roadmat,bev=.007)
    for i,x in enumerate(range(-10,57,4)):
        box('Lane edge marking '+str(s)+str(i),(x,s*1.23,.004),(1.6,.035,.005),'ROAD',accent,bev=.001)
        box('Apron expansion joint '+str(s)+str(i),(x,s*4.7,.002),(.009,7.1,.003),'ROAD',black,bev=0)
box('Inspection channel floor',(23,0,-.725),(70,1.12,.09),'ROAD',roadmat,bev=.008)
# Distant utilitarian background, restrained enough to keep the truck legible.
wallmat=mat('Background | warm light concrete',(.46,.48,.47),0,.84)
for x,width,height in [(-8,12,3.6),(9,16,4.3),(29,16,3.7),(49,13,4.1)]:
    box('Industrial hall '+str(x),(x,12.5,height/2-.04),(width,7,height),'ROAD',wallmat,bev=.04)
    box('Hall parapet '+str(x),(x,12.4,height), (width+.1,7.2,.18),'ROAD',steel,bev=.02)
    for xx in [x-width*.3,x,x+width*.3]:
        box('Loading bay '+str(xx),(xx,8.972,1.25),(2.5,.026,2.5),'ROAD',steel,bev=.014)
        for z in [.3+i*.27 for i in range(8)]:box('Loading shutter seam '+str(xx)+str(z),(xx,8.948,z),(2.44,.012,.016),'ROAD',black,bev=.002)
for s in (-1,1):
    for x in range(-9,58,7):
        box('Safety bollard foot '+str(s)+str(x),(x,s*2.30,.042),(.27,.27,.084),'ROAD',black,bev=.024)
        cyl('Safety bollard '+str(s)+str(x),(x,s*2.30,.075),(x,s*2.30,.62),.055,'ROAD',accent,n=16)
        cyl('Bollard dark band '+str(s)+str(x),(x,s*2.30,.40),(x,s*2.30,.50),.056,'ROAD',black,n=16)

# The continuous shot is baked at every frame; no runtime handlers are required.
def camera(name,pos,target,lens=35,parent=None):
    data=bpy.data.cameras.new(name+' optics');data.lens=lens;data.sensor_width=36;data.clip_start=.025;data.clip_end=300
    data.dof.use_dof=False
    o=bpy.data.objects.new(name,data);C['CAMERAS'].objects.link(o)
    if parent:o.parent=parent
    o.location=pos;o.rotation_mode='QUATERNION';o.rotation_quaternion=(Vector(target)-Vector(pos)).to_track_quat('-Z','Y')
    return o
cam=camera('CAM_ANIMATION | continuous 10 second inspection',(0,-7,1),(0,0,1),36)
scene.camera=cam
# Frame, truck-relative lens position, truck-relative aim, focal length.
CAM_KEYS=[
(1,(-.2,-7.9,1.04),(0,0,.95),38),
(36,(-.2,-7.9,1.04),(0,0,.95),38),
(48,(.15,-7.8,1.10),(.05,0,.93),38),
(62,(4.1,-5.9,1.26),(.45,0,.86),36),
(70,(5.2,-3.25,.93),(.85,0,.72),31),
(77,(4.35,-.74,.38),(1.15,0,.56),24),
(84,(3.02,-.02,-.105),(1.30,.05,.53),20),
(93,(1.87,.01,-.135),(1.27,.19,.60),18),
(107,(.63,.01,-.135),(.05,.20,.65),18),
(118,(-.40,.00,-.135),(-1.07,.12,.61),19),
(126,(-1.32,-.06,-.13),(-1.60,-.28,.52),20),
(135,(-2.35,.31,.035),(-1.52,-.48,.53),24),
(144,(-2.60,.43,.28),(-1.51,-.53,.53),27),
(153,(-2.60,.43,.28),(-1.51,-.53,.53),27),
(183,(-2.60,.43,.28),(-1.51,-.53,.53),27),
(192,(-2.72,.37,.36),(-1.48,-.53,.55),28),
(201,(-4.1,-1.74,.88),(-.75,-.18,.82),32),
(214,(-6.65,-3.75,1.68),(-.10,0,.95),35),
(240,(-10.50,-5.20,2.35),(0,0,.96),38),
]
def smooth_path(f,column):
    # Non-uniform cubic Hermite, bounded adjacent velocities, zero velocity during holds.
    k=next((i for i in range(len(CAM_KEYS)-1) if CAM_KEYS[i][0]<=f<=CAM_KEYS[i+1][0]),len(CAM_KEYS)-2)
    fs=[p[0] for p in CAM_KEYS]
    vals=[Vector(p[column]) if column in (1,2) else p[column] for p in CAM_KEYS]
    def tangent(i):
        if i==0:return (vals[1]-vals[0])/(fs[1]-fs[0])
        if i==len(fs)-1:return (vals[-1]-vals[-2])/(fs[-1]-fs[-2])
        before=(vals[i]-vals[i-1])/(fs[i]-fs[i-1]);after=(vals[i+1]-vals[i])/(fs[i+1]-fs[i])
        if column in (1,2):
            if before.length<1e-6 or after.length<1e-6:return Vector((0,0,0))
        elif abs(before)<1e-6 or abs(after)<1e-6:return 0
        return (before+after)*.5
    dt=fs[k+1]-fs[k];u=(f-fs[k])/dt
    return (2*u**3-3*u*u+1)*vals[k]+(u**3-2*u*u+u)*dt*tangent(k)+(-2*u**3+3*u*u)*vals[k+1]+(u**3-u*u)*dt*tangent(k+1)
lastq=None
camera_samples=[]
for f in range(1,241):
    distance=(f-1)*3/24
    pos=smooth_path(f,1)+Vector((distance,0,0));aim=smooth_path(f,2)+Vector((distance,0,0))
    q=(aim-pos).to_track_quat('-Z','Y')
    if lastq and q.dot(lastq)<0:q.negate()
    cam.location=pos;cam.rotation_quaternion=q;cam.data.lens=smooth_path(f,3)
    cam.keyframe_insert(data_path='location',frame=f);cam.keyframe_insert(data_path='rotation_quaternion',frame=f);cam.data.keyframe_insert(data_path='lens',frame=f)
    camera_samples.append({'frame':f,'position':list(pos),'target':list(aim),'lens_mm':cam.data.lens});lastq=q.copy()
# Additional cameras track vehicle travel, and remain useful at any animation frame.
camera('INSPECT_01_FULL_TRUCK',(6.7,-7.4,3.5),(0,0,.95),48,root)
camera('INSPECT_02_UNDERSIDE_OVERVIEW',(.2,-.07,-.38),(-.15,.08,.67),14,root)
camera('INSPECT_03_FRONT_SUSPENSION',(2.8,-.35,.30),(1.58,-.56,.57),43,root)
camera('INSPECT_04_REAR_RIGHT_SUSPENSION',(-2.60,.43,.28),(-1.51,-.53,.53),27,root)
# Readable 3D camera path guides; hidden from rendering and disabled in viewport by default.
path=tube('GUIDE | camera trajectory',[r['position'] for r in camera_samples],.009,'CAMERAS',accent)
path.hide_render=True;path.hide_set(True)
for f,label in [(1,'01 • PROFILE / 0 s'),(49,'02 • FRONT ARC / 2 s'),(85,'03 • UNDERCARRIAGE / 3.5 s'),(145,'04 • REAR RIGHT / 6 s'),(165,'RR BUMP CREST'),(193,'05 • REAR PULLAWAY / 8 s'),(240,'END / 10 s output')]:scene.timeline_markers.new(label,frame=f)

def area(name,loc,target,power,color,size,parent=None):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);C['LIGHTS'].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    if parent:o.parent=parent
    return o
area('Daylight | broad soft key',(13,-7,11),(16,0,0),3300,(1,.90,.77),10)
area('Daylight | sky fill',(18,8,8),(18,0,0),2400,(.72,.84,1),12)
data=bpy.data.lights.new('Sun | soft afternoon','SUN');data.energy=1.5;data.angle=math.radians(18)
o=bpy.data.objects.new('Sun | soft afternoon',data);C['LIGHTS'].objects.link(o);o.rotation_euler=(.38,-.45,-.38)
# Motivated channel fill, following the inspection zone without visible cards.
area('Inspection fill | front', (1.12,-.30,-.32),(1.40,0,.55),95,(.76,.87,1),1.1,root)
area('Inspection fill | driveline',(-.12,.22,-.35),(-.1,0,.64),110,(.83,.91,1),1.25,root)
area('Inspection fill | rear-right',(-2.6,-.25,.04),(-1.45,-.52,.53),75,(1,.88,.70),.8,root)
area('Rear chassis rim',(-2.2,.28,-.29),(-1.6,0,.55),75,(.76,.86,1),.75,root)
# Linear interpolation on dense baked controls avoids overshoot at subframes.
for act in bpy.data.actions:
    if hasattr(act,'layers'):
        for layer in act.layers:
            for strip in layer.strips:
                for slot in act.slots:
                    try:bag=strip.channelbag(slot)
                    except Exception:continue
                    if bag:
                        for fc in bag.fcurves:
                            for k in fc.keyframe_points:k.interpolation='LINEAR'
scene['project']='KESTREL / original crew-cab expedition pickup'
scene['build_notes']='Original local bpy geometry. Deterministic road-contact rig. No renders have been executed. No downloaded or paid assets.'
scene['rig_simplifications']='Kinematic wheel travel; small wishbone length accommodation; fixed leaf eyes with parabolic leaf flex; universal joints aim shafts without spline plunge detail; rigid undeformed tire carcasses; forward rolling distance on X; no full rigid-body simulation.'
scene['nominal_dimensions_m']='5.3 body length; 1.9 body/tire width; 1.85 cab roof; 3.2 wheelbase. Mirrors/hitch/roof rails extend envelope.'
scene['camera_route']='Two continuous road tracks flank a 1.06 m clear recessed channel. Lens scans from -0.14 m before exiting behind the axle into a rear/inboard view.'
scene['construction_elapsed_seconds']=round(time.perf_counter()-START,3)
# Consistent outward normals on custom closed solids; preserve all vertices and shape keys.
for me in bpy.data.meshes:
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me);bm.free();me.update()
# Useful solid-material three-quarter opening view, camera animation remains active.
scene.frame_set(1);bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            sp=ar.spaces.active;sp.clip_start=.01;sp.clip_end=300;sp.lens=48
            sp.shading.type='SOLID';sp.shading.light='STUDIO';sp.shading.color_type='MATERIAL';sp.shading.show_shadows=True;sp.shading.show_cavity=True
            sp.overlay.show_extras=False;sp.overlay.show_relationship_lines=False;sp.overlay.show_floor=False;sp.overlay.show_axis_x=False;sp.overlay.show_axis_y=False
            rv=sp.region_3d;rv.view_distance=7.2;rv.view_location=(0,0,.9);rv.view_rotation=Vector((6.7,-7.4,3.5)).to_track_quat('Z','Y');rv.view_perspective='PERSP'
for o in bpy.context.selected_objects:o.select_set(False)
root.select_set(True);bpy.context.view_layer.objects.active=root
# Source and rig notes also travel inside the blend.
text=bpy.data.texts.new('README | START HERE');text.write('KESTREL 4x4 — 10 s / 24 fps / 1920x1080\n\nOpen README.md beside this scene for controls, verified results and limitations.\nActive camera: CAM_ANIMATION. Four INSPECT cameras follow vehicle travel.\nSelect CTRL_VEHICLE_TRAVEL for travel, steering and body controls.\nEach CTRL_SUSPENSION_* has an animated travel_m control.\nAll mechanical motion evaluates through native drivers, constraints and shape keys.\nAnimation is baked at 240 frames; no external runtime scripts needed.\nNo rendering performed.\n')
bpy.data.texts.load(str(Path(__file__).resolve()))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'pickup_truck.blend'))
(ROOT/'reports/camera_samples.json').write_text(json.dumps(camera_samples,indent=2))
manifest={'blender':bpy.app.version_string,'objects':len(scene.objects),'collections':{n:len(c.objects) for n,c in C.items()},'mesh_vertices':sum(len(o.data.vertices) for o in scene.objects if o.type=='MESH'),'build_seconds':time.perf_counter()-START,'render_invoked':False}
(ROOT/'reports/build_manifest.json').write_text(json.dumps(manifest,indent=2));print('BUILD_COMPLETE',json.dumps(manifest))
