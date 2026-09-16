"""Read-only evaluated verification of v2. No image rendering and no scene saves."""
import bpy,ast,json,math,time,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parent.parent;REPORT=ROOT/'reports/v2';START=time.perf_counter()
scene=bpy.context.scene;root=bpy.data.objects['CTRL_VEHICLE_TRAVEL'];cam=scene.camera;R=.405;TRACK=1.66
manifest=json.loads((REPORT/'build_manifest.json').read_text());BUMPS=manifest['bumps']
for node in ast.parse((ROOT/'scripts/verify_scene.py').read_text()).body:
    if isinstance(node,ast.FunctionDef) and node.name in ['ground','contact','position','inframe','visibility_sample']:exec(compile(ast.Module(body=[node],type_ignores=[]),'verify_helpers','exec'),globals())
# Sample interior areas of long faces as well as their ends. Axle tube end rings
# are naturally hidden by hubs, and the central strip is hidden by the differential.
helper_source=(ROOT/'scripts/verify_scene.py').read_text()
node=next(n for n in ast.parse(helper_source).body if isinstance(n,ast.FunctionDef) and n.name=='visibility_sample')
func=ast.get_source_segment(helper_source,node)
func=func.replace("    for point in points:","    for idx in range(0,len(me.polygons),pstep):\n        face=me.polygons[idx]\n        for vi in face.vertices:points.append(face.center.lerp(me.vertices[vi].co,.5))\n    for point in points:")
exec(compile(func,'visibility_surface_sampler','exec'),globals())
hubs={c:bpy.data.objects['RIG_HUB_'+c] for c in ['FL','FR','RL','RR']};controls={c:bpy.data.objects['CTRL_SUSPENSION_'+c] for c in hubs}
rods=[o for o in scene.objects if 'endpoint_a' in o and o.animation_data and o.animation_data.drivers]
meshes=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
vehicle=[o for col in ['BODY','INTERIOR','CHASSIS','DRIVETRAIN','FRONT_SUSPENSION','REAR_SUSPENSION','WHEELS'] for o in bpy.data.collections[col].objects if o.type in {'MESH','CURVE','FONT'}]
rows=[];clearance=[];link_errors=[];leaf_errors=[];eye_errors=[];span_errors=[];framing={};lastq=None;camera_steps=[]
def raw_key_center(o,indices,dg):
    keys=o.data.shape_keys.key_blocks;basis=keys[0];pts=[]
    for i in indices:
        v=basis.data[i].co.copy()
        for key in list(keys)[1:]:v+=(key.data[i].co-basis.data[i].co)*key.value
        pts.append(o.evaluated_get(dg).matrix_world@v)
    return sum(pts,Vector())/len(pts)
for f in range(1,scene.frame_end+1):
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();d=root['travel_m'];row={'frame':f,'travel_m':d,'contact_error_m':{},'suspension_m':{},'wheel_spin_error_rad':{},'shock_length_m':{},'shackle_angle_deg':{}}
    for c,hub in hubs.items():
        p=position(hub,dg);row['contact_error_m'][c]=p.z-contact(p.x,p.y);row['suspension_m'][c]=controls[c]['travel_m'];row['wheel_spin_error_rad'][c]=bpy.data.objects['CTRL_WHEEL_ROTATION_'+c].evaluated_get(dg).rotation_euler.y-d/R
    for code in ['RL','RR']:
        row['shock_length_m'][code]=(position(bpy.data.objects['Shock upper '+code],dg)-position(bpy.data.objects['Shock lower '+code],dg)).length
        sh=bpy.data.objects['RIG_REAR_SHACKLE_'+code];end=bpy.data.objects['Rear moving leaf eye '+code];row['shackle_angle_deg'][code]=math.degrees(sh.evaluated_get(dg).rotation_euler.y)
        span_errors.append(abs((position(sh,dg)-position(end,dg)).length-.13))
        leaf=bpy.data.objects['Leaf pack '+code+' lamination 1'];center=raw_key_center(leaf,[80,81,82,83],dg);tip=raw_key_center(leaf,[0,1,2,3],dg)
        leaf_errors.append((center-position(bpy.data.objects['Leaf saddle target '+code],dg)).length);eye_errors.append((tip-position(end,dg)).length)
    for o in rods:
        ev=o.evaluated_get(dg);a=position(bpy.data.objects[o['endpoint_a']],dg);b=position(bpy.data.objects[o['endpoint_b']],dg)
        link_errors.append(max((ev.matrix_world@Vector((0,0,0))-a).length,(ev.matrix_world@Vector((0,0,1))-b).length))
    cp=position(cam,dg);near=.15;nearest='none within 150 mm'
    for o in meshes:
        ev=o.evaluated_get(dg);corners=[ev.matrix_world@Vector(v) for v in ev.bound_box]
        mins=Vector(tuple(min(v[i] for v in corners) for i in range(3)));maxs=Vector(tuple(max(v[i] for v in corners) for i in range(3)))
        if sum(max(mins[i]-cp[i],0,cp[i]-maxs[i])**2 for i in range(3))>.15**2:continue
        hit,p,n,index=ev.closest_point_on_mesh(ev.matrix_world.inverted_safe()@cp)
        if hit:
            dist=(ev.matrix_world@p-cp).length
            if dist<near:near=dist;nearest=o.name
    clearance.append({'frame':f,'distance_m':near,'object':nearest})
    q=cam.evaluated_get(dg).matrix_world.to_quaternion()
    if lastq:camera_steps.append({'frame':f,'angular_step_deg':math.degrees(2*math.acos(min(1,abs(q.dot(lastq)))))})
    lastq=q.copy();rows.append(row)
    if f in [84,108,133,156,180,498]:
        pts=[]
        for o in vehicle:
            ev=o.evaluated_get(dg)
            if o.type in {'CURVE','FONT'}:
                me=ev.to_mesh();pts.extend(world_to_camera_view(scene,cam,ev.matrix_world@v.co) for v in me.vertices);ev.to_mesh_clear()
            else:pts.extend(world_to_camera_view(scene,cam,ev.matrix_world@Vector(v)) for v in ev.bound_box)
        framing[str(f)]={'min_x':min(v.x for v in pts),'max_x':max(v.x for v in pts),'min_y':min(v.y for v in pts),'max_y':max(v.y for v in pts)}
    if f%60==0:print('V2_CHECKED_FRAME',f,'clearance',near,nearest,flush=True)
# Geometry visibility at engine opening and at actual extrema of the new rear hold.
hold=[r for r in rows if 361<=r['frame']<=420];lo=min(hold,key=lambda r:r['suspension_m']['RR']);hi=max(hold,key=lambda r:r['suspension_m']['RR'])
rear_targets=['Leaf pack RR lamination 1','Leaf pack RL lamination 1','Rear shock body RR','Rear shock body RL','Rear shock chrome shaft RR','Rear shock chrome shaft RL','Wheel hub RR','Wheel hub RL','Rear axle | rigid driven tube','Rear differential | cast housing','Rear driveshaft | articulated','Moving shackle side plate RR-0.052','Moving shackle side plate RL0.052']
engine_targets=['Engine valve cover','Engine cylinder head','Engine bay battery','Air filter lid','Coolant expansion reservoir','Upper radiator coolant hose','Engine serpentine belt | tangent continuous loop','Accessory pulley grooved rim Crank','Accessory pulley grooved rim Alternator','Swept cooling fan blade 0','Ignition coil 3']
visibility={}
for f,names in [(1,engine_targets),(36,engine_targets),(lo['frame'],rear_targets),(hi['frame'],rear_targets),(410,rear_targets)]:
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();visibility[str(f)]={name:visibility_sample(bpy.data.objects[name],dg) for name in names}
# Hood skin, reinforcement and liner must clear the packaged engine when latched.
scene.frame_set(108);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
hoodparts=[bpy.data.objects['Hood | crowned one-piece pressing'],bpy.data.objects['Hood heat and acoustic liner']]+[o for o in scene.objects if o.name.startswith('Hood underside pressed rib')]
engineparts=[o for o in bpy.data.collections['DRIVETRAIN'].objects if o.type in {'MESH','CURVE'} and o.name not in ['Hood gas strut']]
def world_bvh(o):
    ev=o.evaluated_get(dg);me=ev.to_mesh();verts=[ev.matrix_world@v.co for v in me.vertices];faces=[tuple(p.vertices) for p in me.polygons];ev.to_mesh_clear();return BVHTree.FromPolygons(verts,faces)
hood_trees={o.name:world_bvh(o) for o in hoodparts};hood_overlap=[]
for o in engineparts:
    ev=o.evaluated_get(dg);bb=[ev.matrix_world@Vector(v) for v in ev.bound_box]
    if max(v.z for v in bb)<1.18 or max(v.x for v in bb)<root['travel_m']+.90 or min(v.x for v in bb)>root['travel_m']+2.6:continue
    tree=world_bvh(o)
    for name,ht in hood_trees.items():
        pairs=ht.overlap(tree)
        if pairs:hood_overlap.append({'hood_part':name,'engine_part':o.name,'triangle_pairs':len(pairs)})
# The whole opening/closing sweep must also avoid fixed cowl, glazing and bay walls.
hood_sweep=[]
fixed_names=['Cowl below windshield','Windshield | thick sloped laminated glass','Engine bay inner wheelhouse -1','Engine bay inner wheelhouse 1']
for f in [1,84,90,96,102,108]:
    scene.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    moving={o.name:world_bvh(o) for o in hoodparts}
    fixed=[bpy.data.objects[n] for n in fixed_names]+[o for o in scene.objects if o.name.startswith('Fender mounting lip') or o.name.startswith('Fender flange screw')]
    for o in fixed:
        tree=world_bvh(o)
        for n,ht in moving.items():
            hits=ht.overlap(tree)
            if hits:hood_sweep.append({'frame':f,'moving':n,'fixed':o.name,'triangle_pairs':len(hits)})
invalid=[]
for owner in list(bpy.data.objects)+list(bpy.data.shape_keys):
    if owner.animation_data:
        for fc in owner.animation_data.drivers:
            if not fc.driver.is_valid:invalid.append(owner.name+':'+fc.data_path)
summary={'file':bpy.data.filepath,'duration_seconds':scene.frame_end/24,'frames_checked':len(rows),'hold_frames':[361,420],'hold_seconds':2.5,'hold_minimum_frame':lo['frame'],'hold_maximum_frame':hi['frame'],'hold_RR_travel_range_m':[lo['suspension_m']['RR'],hi['suspension_m']['RR']],'hold_shock_length_ranges_m':{c:[min(r['shock_length_m'][c] for r in hold),max(r['shock_length_m'][c] for r in hold)] for c in ['RL','RR']},'hold_shackle_angle_ranges_deg':{c:[min(r['shackle_angle_deg'][c] for r in hold),max(r['shackle_angle_deg'][c] for r in hold)] for c in ['RL','RR']},'maximum_wheel_contact_error_m':max(abs(v) for r in rows for v in r['contact_error_m'].values()),'maximum_wheel_spin_error_rad':max(abs(v) for r in rows for v in r['wheel_spin_error_rad'].values()),'suspension_range_m':[min(v for r in rows for v in r['suspension_m'].values()),max(v for r in rows for v in r['suspension_m'].values())],'maximum_link_endpoint_error_m':max(link_errors),'maximum_leaf_saddle_error_m':max(leaf_errors),'maximum_leaf_eye_error_m':max(eye_errors),'maximum_shackle_span_error_m':max(span_errors),'minimum_camera_clearance':min(clearance,key=lambda r:r['distance_m']),'maximum_camera_angular_step':max(camera_steps,key=lambda r:r['angular_step_deg']),'full_vehicle_framing':framing,'visibility':visibility,'hood_engine_intersections':hood_overlap,'invalid_drivers':invalid,'base_v1_unchanged':hashlib.sha256((ROOT/'pickup_truck.blend').read_bytes()).hexdigest()==manifest['base_sha256'],'render_invoked':False}
summary['checks']={'original_preserved':summary['base_v1_unchanged'],'correct_duration':scene.frame_end==498,'hold_is_2_5_seconds':len(hold)==60,'truck_keeps_driving_during_hold':all(abs((b['travel_m']-a['travel_m'])*24-3)<.0001 for a,b in zip(hold,hold[1:])),'suspension_within_80mm':max(abs(v) for v in summary['suspension_range_m'])<=.08,'wheel_contact_within_2mm':summary['maximum_wheel_contact_error_m']<.002,'wheel_rotation_consistent':summary['maximum_wheel_spin_error_rad']<1e-4,'link_endpoints_within_0_1mm':max(link_errors)<.0001,'leaf_saddles_within_0_1mm':max(leaf_errors)<.0001,'leaf_eyes_within_0_1mm':max(eye_errors)<.0001,'shackles_rigid':max(span_errors)<.0001,'camera_clearance_over_50mm':summary['minimum_camera_clearance']['distance_m']>.05,'hood_clears_engine_when_closed':not hood_overlap,'all_drivers_valid':not invalid,'rear_cycle_over_50mm':hi['suspension_m']['RR']-lo['suspension_m']['RR']>.05,'engine_key_groups_visible':all(any(visibility[str(f)][n]['visible'] for f in [1,36]) for n in engine_targets if n!='Swept cooling fan blade 0'),'new_rear_key_groups_visible':all(any(visibility[str(f)][n]['visible'] for f in [lo['frame'],hi['frame'],410]) for n in rear_targets),'whole_vehicle_fits_wide_shots':all(0<=v['min_x']<v['max_x']<=1 and 0<=v['min_y']<v['max_y']<=1 for v in framing.values())}
summary['hood_sweep_intersections']=hood_sweep
summary['checks']['hood_sweep_clears_fixed_body']=not hood_sweep
summary['verification_seconds']=time.perf_counter()-START
(REPORT/'verification.json').write_text(json.dumps(summary,indent=2));(REPORT/'evaluated_frames.json').write_text(json.dumps({'frames':rows,'camera_clearance':clearance,'camera_steps':camera_steps},indent=2))
print('V2_CHECKS',json.dumps(summary['checks']));print('V2_HOOD_INTERSECTIONS',json.dumps(hood_overlap));print('V2_REAR_EXTREMES',lo['frame'],hi['frame']);print('V2_VERIFY_SECONDS',summary['verification_seconds'])
assert all(summary['checks'].values()),str([k for k,v in summary['checks'].items() if not v])
