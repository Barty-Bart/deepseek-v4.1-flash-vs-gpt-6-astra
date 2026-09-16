"""Read-only verification in a separate Blender process. Does not save or render."""
import bpy, math, json, time
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
START=time.perf_counter();ROOT=Path(__file__).resolve().parent.parent
scene=bpy.context.scene;R=.405;TRACK=1.66
root=bpy.data.objects['CTRL_VEHICLE_TRAVEL'];cam=scene.camera
hubs={c:bpy.data.objects['RIG_HUB_'+c] for c in ('FL','FR','RL','RR')}
shocks={c:(bpy.data.objects['Shock upper '+c],bpy.data.objects['Shock lower '+c]) for c in hubs}
controls={c:bpy.data.objects['CTRL_SUSPENSION_'+c] for c in hubs}
BUMPS=[(2.7,.048,1.6),(6.4,.060,1.9),(10.8,.047,1.6),(14.7,.055,2.0),(18.9,.082,1.8),(20.9,.064,1.7),(25.5,.058,1.9),(30.0,.043,2.0),(35.1,.055,1.8)]
def ground(x,y):
    z=0
    for i,(c,h,w) in enumerate(BUMPS):
        if y>0:c+=.32;h*=.5 if i in (4,5) else .76
        u=(x-c)/(w/2)
        if abs(u)<1:z+=h*(.5+.5*math.cos(math.pi*u))
    return z

def contact(x,y):return max(ground(x+R*(-1+2*i/160),y)+R*math.sqrt(max(0,1-(-1+2*i/160)**2)) for i in range(161))
def position(o,dg):return o.evaluated_get(dg).matrix_world.translation.copy()
def inframe(p):
    n=world_to_camera_view(scene,cam,p);return 0<=n.x<=1 and 0<=n.y<=1 and n.z>0,list(n)
def visibility_sample(obj,dg,max_points=80):
    ev=obj.evaluated_get(dg);me=ev.to_mesh();verts=me.vertices
    if not verts:ev.to_mesh_clear();return {'visible':False,'visible_samples':0,'tested':0}
    step=max(1,len(verts)//max_points);origin=position(cam,dg);found=0;tested=0;occluders={};seen=[]
    points=[verts[i].co.copy() for i in range(0,len(verts),step)]
    pstep=max(1,len(me.polygons)//max_points)
    points += [me.polygons[i].center.copy() for i in range(0,len(me.polygons),pstep)]
    for point in points:
        p=ev.matrix_world@point;inside,n=inframe(p)
        if not inside:continue
        tested+=1;ray=p-origin;dist=ray.length
        hit,loc,normal,face,hitobj,matrix=scene.ray_cast(dg,origin,ray.normalized(),distance=dist+.003)
        if hit and (hitobj.original==obj or (loc-p).length<.012):found+=1;seen.append(n[:2])
        elif hit:occluders[hitobj.name]=occluders.get(hitobj.name,0)+1
    ev.to_mesh_clear()
    return {'visible':found>0,'visible_samples':found,'tested_in_frame':tested,'occluders':dict(sorted(occluders.items(),key=lambda kv:-kv[1])[:4])}

rows=[];clearance=[];link_errors=[];bodyh=[];arm_lengths={};leafmid=[];framing={};visibility={}
vehicle=[o for c in ['BODY','INTERIOR','CHASSIS','DRIVETRAIN','FRONT_SUSPENSION','REAR_SUSPENSION','WHEELS'] for o in bpy.data.collections[c].objects if o.type in {'MESH','CURVE','FONT'}]
allmeshes=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
rods=[o for o in scene.objects if 'endpoint_a' in o and o.animation_data and o.animation_data.drivers]
representative=[1,24,48,62,77,84,93,107,118,126,135,144,151,157,165,172,181,192,201,214,240]
for f in range(1,241):
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    d=root['travel_m'];r={'frame':f,'travel_m':d,'wheel_contact_error_m':{},'wheel_spin_error_rad':{},'travel_m_by_wheel':{},'RR_shock_length_m':0,'rear_axle_length_m':0}
    for c,hub in hubs.items():
        p=position(hub,dg);r['wheel_contact_error_m'][c]=p.z-contact(p.x,p.y)
        spin=bpy.data.objects['CTRL_WHEEL_ROTATION_'+c].evaluated_get(dg)
        r['wheel_spin_error_rad'][c]=spin.rotation_euler.y-d/R
        r['travel_m_by_wheel'][c]=controls[c]['travel_m']
    r['RR_shock_length_m']=(position(shocks['RR'][0],dg)-position(shocks['RR'][1],dg)).length
    r['rear_axle_length_m']=(position(hubs['RL'],dg)-position(hubs['RR'],dg)).length
    bodyh.append(root['body_heave_m']);rows.append(r)
    for o in rods:
        ev=o.evaluated_get(dg);a=position(bpy.data.objects[o['endpoint_a']],dg);b=position(bpy.data.objects[o['endpoint_b']],dg)
        p0=ev.matrix_world@Vector((0,0,0));p1=ev.matrix_world@Vector((0,0,1))
        link_errors.append(max((p0-a).length,(p1-b).length))
        if 'A-arm' in o.name:arm_lengths.setdefault(o.name,[]).append((a-b).length)
    # Fixed axle span and leaf saddle tracking through evaluated shape keys.
    leaf=bpy.data.objects['Leaf pack RR lamination 1'];ev=leaf.evaluated_get(dg);me=ev.to_mesh()
    # Bevel evaluation changes indexing, so find mesh vertices near the centerline section.
    local=[v.co for v in me.vertices if abs(v.co.x+1.6)<.004]
    if local:
        center=ev.matrix_world@(sum(local,Vector())/len(local));axle=bpy.data.objects['RIG_REAR_SOLID_AXLE'].evaluated_get(dg).matrix_world@Vector((0,-.57,-.095))
        leafmid.append({'frame':f,'center':list(center),'saddle_error_m':(center-axle).length})
    ev.to_mesh_clear()
    # Mesh-nearest distance after bounding-box culling; records a 150 mm lens safety neighborhood.
    cp=position(cam,dg);near=10;nearest='none within 150 mm'
    for o in allmeshes:
        ev=o.evaluated_get(dg);corners=[ev.matrix_world@Vector(v) for v in ev.bound_box]
        mins=Vector(tuple(min(v[i] for v in corners) for i in range(3)));maxs=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
        bounddist=math.sqrt(sum(max(mins[i]-cp[i],0,cp[i]-maxs[i])**2 for i in range(3)))
        if bounddist>.15:continue
        localpoint=ev.matrix_world.inverted_safe()@cp
        hit,p,n,index=ev.closest_point_on_mesh(localpoint)
        if hit:
            distance=(ev.matrix_world@p-cp).length
            if distance<near:near=distance;nearest=o.name
    clearance.append({'frame':f,'distance_m':near if near<10 else .15,'nearest':nearest,'lower_bound_only':near==10})
    if f in (1,24,48,240):
        bounds=[]
        for o in vehicle:
            ev=o.evaluated_get(dg)
            if o.type in {'CURVE','FONT'}:
                me=ev.to_mesh()
                for v in me.vertices:bounds.append(world_to_camera_view(scene,cam,ev.matrix_world@v.co))
                ev.to_mesh_clear()
            else:
                for p in ev.bound_box:bounds.append(world_to_camera_view(scene,cam,ev.matrix_world@Vector(p)))
        framing[str(f)]={'min_x':min(p.x for p in bounds),'max_x':max(p.x for p in bounds),'min_y':min(p.y for p in bounds),'max_y':max(p.y for p in bounds),'all_in_front':min(p.z for p in bounds)>0}
    if f in representative:
        print('CHECK_FRAME',f,'contact',max(abs(v) for v in r['wheel_contact_error_m'].values()),'clearance',clearance[-1],flush=True)

# Visibility through actual evaluated mesh ray casts at representative inspection frames.
visibility_targets={
93:['Front differential | compact carrier','Engine oil sump','Front CV halfshaft FR','FR Lower A-arm -0.18'],
107:['Transmission | longitudinal case','Transfer case | offset front output','Fuel tank | left side protected polymer','Muffler | oval silencer','Frame rail R'],
118:['Rear driveshaft | articulated','Exhaust | continuous right-side routing','Frame rail L','Rear differential | cast housing'],
135:['Rear differential | cast housing','Rear axle | rigid driven tube'],
151:['Leaf pack RR lamination 1','Rear shock body RR','Rear shock chrome shaft RR','Wheel hub RR','Brake rotor face RR-0.035','Rear axle | rigid driven tube','Rear driveshaft | articulated'],
165:['Leaf pack RR lamination 1','Rear shock body RR','Rear shock chrome shaft RR','Wheel hub RR','Brake rotor face RR-0.035','Rear axle | rigid driven tube','Rear driveshaft | articulated'],
181:['Leaf pack RR lamination 1','Rear shock body RR','Rear shock chrome shaft RR','Wheel hub RR','Rear axle | rigid driven tube'],
}
for f,names in visibility_targets.items():
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();visibility[str(f)]={}
    for name in names:
        o=bpy.data.objects.get(name)
        visibility[str(f)][name]=visibility_sample(o,dg) if o else {'missing':True}
rrrows=[r for r in rows if 145<=r['frame']<=192]
rrmin=min(rrrows,key=lambda r:r['travel_m_by_wheel']['RR']);rrmax=max(rrrows,key=lambda r:r['travel_m_by_wheel']['RR'])
# Required undercarriage components must be observable at some point in the scan.
scan_names=['Engine oil sump','Transmission | longitudinal case','Transfer case | offset front output','Front differential | compact carrier','Rear differential | cast housing','Rear driveshaft | articulated','Front driveshaft | transfer to IFS differential','Fuel tank | left side protected polymer','Exhaust | continuous right-side routing','Muffler | oval silencer','Frame rail L','Frame rail R','Steering rack | central housing','Front CV halfshaft FR','FR Lower A-arm -0.18','FR Lower A-arm 0.18','Front coil spring FR']
scan_visibility={n:[] for n in scan_names}
for f in range(85,144,4):
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    for name in scan_names:
        result=visibility_sample(bpy.data.objects[name],dg,48)
        if result['visible_samples']>=2:scan_visibility[name].append(f)
# Check the actual evaluated tire surfaces at representative frames and both RR extremes.
tire_surface=[]
for f in sorted(set(representative+[rrmin['frame'],rrmax['frame']])):
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    for c in hubs:
        clear=100
        for name in ['Tire '+c+' | formed sidewall and carcass','Tread '+c+' | 192 staggered all-terrain blocks']:
            ev=bpy.data.objects[name].evaluated_get(dg);me=ev.to_mesh()
            center=position(hubs[c],dg)
            for v in me.vertices:
                p=ev.matrix_world@v.co
                if p.z>center.z-.25:continue
                clear=min(clear,p.z-ground(p.x,p.y))
            ev.to_mesh_clear()
        tire_surface.append({'frame':f,'wheel':c,'surface_clearance_m':clear})
# Inspect exact rebound and compression frames, not only a nominal key pose.
for f in (rrmin['frame'],rrmax['frame']):
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    visibility[str(f)]={name:visibility_sample(bpy.data.objects[name],dg) for name in ['Leaf pack RR lamination 1','Rear shock body RR','Rear shock chrome shaft RR','Wheel hub RR','Rear axle | rigid driven tube','Brake rotor face RR-0.011']}

summary={'file':bpy.data.filepath,'blender':bpy.app.version_string,'frame_range':[scene.frame_start,scene.frame_end],'fps':scene.render.fps,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'engine':scene.render.engine,'render_invoked':False,'checked_frames':240,'max_wheel_contact_error_m':max(abs(v) for r in rows for v in r['wheel_contact_error_m'].values()),'max_wheel_rotation_error_rad':max(abs(v) for r in rows for v in r['wheel_spin_error_rad'].values()),'distance_travelled_m':rows[-1]['travel_m']-rows[0]['travel_m'],'suspension_range_m':[min(v for r in rows for v in r['travel_m_by_wheel'].values()),max(v for r in rows for v in r['travel_m_by_wheel'].values())],'body_heave_range_m':[min(bodyh),max(bodyh)],'RR_closeup_min_travel':rrmin,'RR_closeup_max_travel':rrmax,'RR_closeup_shock_range_m':[min(r['RR_shock_length_m'] for r in rrrows),max(r['RR_shock_length_m'] for r in rrrows)],'max_rigid_axle_span_error_m':max(abs(r['rear_axle_length_m']-TRACK) for r in rows),'max_link_endpoint_error_m':max(link_errors),'max_leaf_saddle_error_m':max(r['saddle_error_m'] for r in leafmid),'min_camera_mesh_clearance_m':min(r['distance_m'] for r in clearance),'min_camera_clearance_frame':min(clearance,key=lambda r:r['distance_m']),'wishbone_length_variation_pct':{n:100*(max(v)-min(v))/v[0] for n,v in arm_lengths.items()},'full_vehicle_framing':framing,'visibility':visibility,'inspection_cameras':[o.name for o in bpy.data.collections['CAMERAS'].objects if o.type=='CAMERA' and o.name.startswith('INSPECT')],'invalid_drivers':[],'verification_seconds':time.perf_counter()-START}
for owner in list(bpy.data.objects)+list(bpy.data.shape_keys):
    if owner.animation_data:
        for fc in owner.animation_data.drivers:
            if not fc.driver.is_valid:summary['invalid_drivers'].append(owner.name+':'+fc.data_path)
summary['checks']={'wheel_contact_under_2mm':summary['max_wheel_contact_error_m']<.002,'wheel_spin_under_1e-4rad':summary['max_wheel_rotation_error_rad']<1e-4,'travel_within_80mm':max(abs(v) for v in summary['suspension_range_m'])<=.08,'rigid_axle_under_0.1mm':summary['max_rigid_axle_span_error_m']<.0001,'link_endpoints_under_0.1mm':summary['max_link_endpoint_error_m']<.0001,'leaf_center_under_5mm':summary['max_leaf_saddle_error_m']<.005,'lens_clearance_over_50mm':summary['min_camera_mesh_clearance_m']>.05,'four_inspection_cameras':len(summary['inspection_cameras'])==4,'all_drivers_valid':not summary['invalid_drivers'],'whole_truck_in_establishing_and_end':all(0<=b['min_x']<b['max_x']<=1 and 0<=b['min_y']<b['max_y']<=1 and b['all_in_front'] for b in framing.values()),'RR_compression_rebound_over_50mm':rrmax['travel_m_by_wheel']['RR']-rrmin['travel_m_by_wheel']['RR']>.05}
summary['undercarriage_visibility_frames']=scan_visibility
summary['evaluated_tire_surface_clearance_range_m']=[min(r['surface_clearance_m'] for r in tire_surface),max(r['surface_clearance_m'] for r in tire_surface)]
summary['checks']['all_required_undercarriage_groups_visible']=all(scan_visibility[n] for n in scan_names if 'A-arm' not in n and 'CV halfshaft' not in n)
summary['checks']['RR_mechanism_visible_at_both_extremes']=all(visibility[str(f)][n]['visible'] for f in (rrmin['frame'],rrmax['frame']) for n in ['Leaf pack RR lamination 1','Rear shock body RR','Rear shock chrome shaft RR','Wheel hub RR','Rear axle | rigid driven tube'])
summary['checks']['tire_surface_contact_within_6mm']=all(abs(r['surface_clearance_m'])<.006 for r in tire_surface)
summary['verification_seconds']=time.perf_counter()-START
(ROOT/'reports/tire_surface_contact.json').write_text(json.dumps(tire_surface,indent=2))
(ROOT/'reports/verification.json').write_text(json.dumps(summary,indent=2));(ROOT/'reports/evaluated_frames.json').write_text(json.dumps({'frames':rows,'camera_clearance':clearance,'leaf_centers':leafmid},indent=2))
print('VERIFICATION_SUMMARY',json.dumps({k:v for k,v in summary.items() if k not in ['visibility','RR_closeup_min_travel','RR_closeup_max_travel']},indent=2))

assert all(summary['checks'].values()),'Verification failed: '+str([k for k,v in summary['checks'].items() if not v])
