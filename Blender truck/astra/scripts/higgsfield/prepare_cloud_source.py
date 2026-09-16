"""Adapt existing procedural scripts for the Higgsfield Blender worker.
No model bytes or external asset fetches; disk I/O and local save steps are removed.
"""
import ast, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def adapt(path, v2=False):
    nodes=[]
    for node in ast.parse(path.read_text()).body:
        source=ast.unparse(node)
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            continue
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'ROOT','BASE','OUT','REPORT','source','helpers','rig_only','manifest','base_hash'} for t in node.targets):
            continue
        if isinstance(node,ast.If) and ast.unparse(node.test)=='rig_only':
            continue
        if v2 and isinstance(node,ast.For) and 'source.body' in ast.unparse(node.iter):
            continue
        if any(token in source for token in ['.write_text(','.read_text(','.read_bytes(','bpy.ops.wm.open_mainfile','bpy.ops.wm.save_as_mainfile','bpy.data.texts.load','REPORT.mkdir','block.clear()','BUILD_COMPLETE','V2_BUILD_COMPLETE']):
            continue
        nodes.append(node)
    return ast.unparse(ast.Module(body=nodes,type_ignores=[]))

base_hash=hashlib.sha256((ROOT/'pickup_truck.blend').read_bytes()).hexdigest()
header='import bpy, bmesh, math, json, time\nfrom mathutils import Vector, Matrix, Quaternion\nfrom math import sin, cos, pi, sqrt, atan2\nbase_hash='+repr(base_hash)+'\nrig_only=False\nif bpy.context.scene.world is None: bpy.context.scene.world=bpy.data.worlds.new("Kestrel World")\n'
first=adapt(ROOT/'scripts/build_truck.py')
second=adapt(ROOT/'scripts/build_truck_v2.py',True)
tail='''
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
'''
code=header+'\n'+first+'\n'+second+'\n'+tail
assert len(code.encode())<256*1024
names={n.id for n in ast.walk(ast.parse(code)) if isinstance(n,ast.Name)}
for banned in ['ROOT','REPORT','OUT','__file__','Path','manifest']:
    assert banned not in names,banned
out=ROOT/'scripts/higgsfield/cloud_build.py';out.write_text(code)
print('Cloud source bytes:',len(code.encode()))
