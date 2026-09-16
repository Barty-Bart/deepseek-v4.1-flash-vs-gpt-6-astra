"""Render the prepared film.  This is the render pass that the build deliberately
skipped; it is kept in its own script so scripts/build_truck.py stays render-free.

    Blender --background --factory-startup --python scripts/render_film.py -- \
        --start 1 --end 672 --samples 64 --out renders/pickup_truck_1080p.mp4

Options
    --start/--end   frame range (default: the scene range)
    --samples       Eevee TAA render samples (default 64)
    --out           output file; .mp4 writes FFmpeg video, otherwise a PNG sequence
    --camera        camera object name (default: the scene camera)
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

import bpy                                                    # noqa: E402


def parse_args():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:] if '--' in argv else []
    opts = {'start': None, 'end': None, 'samples': 64,
            'out': 'renders/pickup_truck_1080p.mp4', 'camera': None}
    i = 0
    while i < len(argv):
        if argv[i].startswith('--'):
            key = argv[i][2:]
            val = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith('--') else '1'
            if key in opts:
                opts[key] = int(val) if key in ('start', 'end', 'samples') else val
            i += 2
        else:
            i += 1
    return opts


def main():
    o = parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'pickup_truck.blend'))
    sc = bpy.context.scene
    if o['camera']:
        sc.camera = bpy.data.objects[o['camera']]
    if o['start']:
        sc.frame_start = o['start']
    if o['end']:
        sc.frame_end = o['end']
    sc.eevee.taa_render_samples = o['samples']
    out = o['out']
    if not os.path.isabs(out):
        out = os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if out.lower().endswith('.mp4'):
        sc.render.image_settings.file_format = 'FFMPEG'
        sc.render.ffmpeg.format = 'MPEG4'
        sc.render.ffmpeg.codec = 'H264'
        sc.render.ffmpeg.constant_rate_factor = 'HIGH'
        sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
        sc.render.ffmpeg.gopsize = 12
        sc.render.filepath = out
    else:
        sc.render.image_settings.file_format = 'PNG'
        sc.render.filepath = out

    n = sc.frame_end - sc.frame_start + 1
    print('rendering %d frames %d-%d at %dx%d, %d samples -> %s'
          % (n, sc.frame_start, sc.frame_end, sc.render.resolution_x,
             sc.render.resolution_y, o['samples'], out))
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    dt = time.time() - t0
    print('render finished in %.1f s (%.2f s/frame)' % (dt, dt / max(1, n)))
    if os.path.exists(out):
        print('output: %s (%.1f MB)' % (out, os.path.getsize(out) / 1e6))
    return 0


if __name__ == '__main__':
    sys.exit(main())
