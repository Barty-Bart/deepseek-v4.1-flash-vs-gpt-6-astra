"""GPU render of the verified Blender scene downloaded from Higgsfield MCP.
Preserves both accepted local files; renders only, with Blender's native encoder.
"""
import bpy,time,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=bpy.context.scene
s.render.engine='BLENDER_EEVEE'
s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
s.render.fps=24;s.render.fps_base=1;s.frame_start=1;s.frame_end=498
s.view_settings.view_transform='AgX';s.render.use_motion_blur=False;s.camera.data.dof.use_dof=False
s.eevee.taa_render_samples=64
s.eevee.shadow_pool_size='1024'
s.render.use_file_extension=True
start=time.perf_counter()
if '--preview' in sys.argv:
 s.render.image_settings.media_type='IMAGE';s.render.image_settings.file_format='PNG'
 s.frame_set(386);s.render.filepath=str(ROOT/'renders/higgsfield/local_gpu_preview.png')
 bpy.ops.render.render(write_still=True)
else:
 s.render.image_settings.media_type='VIDEO';s.render.image_settings.file_format='FFMPEG'
 s.render.ffmpeg.format='MPEG4';s.render.ffmpeg.codec='H264';s.render.ffmpeg.constant_rate_factor='HIGH'
 s.render.ffmpeg.ffmpeg_preset='GOOD';s.render.ffmpeg.audio_codec='NONE'
 s.render.filepath=str(ROOT/'renders/higgsfield/kestrel_blender_source_1080p.mp4')
 bpy.ops.render.render(animation=True)
result={'seconds':time.perf_counter()-start,'file':s.render.filepath,'engine':s.render.engine,'samples':s.eevee.taa_render_samples,'resolution':[1920,1080],'preview':'--preview' in sys.argv}
(ROOT/('reports/higgsfield/local_render_preview.json' if '--preview' in sys.argv else 'reports/higgsfield/local_render.json')).write_text(json.dumps(result,indent=2))
print('LOCAL_GPU_RENDER_COMPLETE',json.dumps(result),flush=True)
