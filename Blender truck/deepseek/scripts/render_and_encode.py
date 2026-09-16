"""Render the film in chunks and encode with the system ffmpeg.

This Blender 5.2.1 build cannot write video itself (FFMPEG is not offered by
scene.render.image_settings.file_format at runtime), and the boot disk is nearly
full, so each chunk of PNG frames is encoded to an H.264 segment and the frames are
deleted before the next chunk starts.  Segments are stream-copied into one MP4.

    python3 scripts/render_and_encode.py [chunk_frames] [samples]
"""
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
FFMPEG = '/opt/homebrew/bin/ffmpeg'
FRAMES = os.path.join(ROOT, 'renders', 'frames')
SEGS = os.path.join(ROOT, 'renders', 'segments')
LOG = os.path.join(ROOT, 'renders', 'render_log.txt')
LAST = 672


def log(msg):
    with open(LOG, 'a') as fh:
        fh.write(msg + '\n')
    print(msg, flush=True)


def main():
    chunk = int(sys.argv[1]) if len(sys.argv) > 1 else 96
    samples = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    # resumable: completed segments are kept and their chunks skipped
    for d in (FRAMES, SEGS):
        os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(FRAMES, '*.png')):
        os.remove(f)

    t0 = time.time()
    start, idx = 1, 0
    while start <= LAST:
        end = min(start + chunk - 1, LAST)
        seg = os.path.join(SEGS, 'seg_%02d.mp4' % idx)
        if os.path.exists(seg):
            log('chunk %d already encoded, skipping' % idx)
            start, idx = end + 1, idx + 1
            continue
        log('=== chunk %d: frames %d-%d ===' % (idx, start, end))
        with open(LOG, 'a') as fh:
            subprocess.run([BLENDER, '--background', '--factory-startup',
                            '--python', os.path.join(ROOT, 'scripts', 'render_film.py'),
                            '--', '--start', str(start), '--end', str(end),
                            '--samples', str(samples), '--out', FRAMES + os.sep],
                           stdout=fh, stderr=subprocess.STDOUT, check=True)
            subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-framerate', '24',
                            '-start_number', str(start),
                            '-i', os.path.join(FRAMES, '%04d.png'),
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                            '-pix_fmt', 'yuv420p', seg],
                           stdout=fh, stderr=subprocess.STDOUT, check=True)
        for f in glob.glob(os.path.join(FRAMES, '*.png')):
            os.remove(f)
        log('chunk %d done (frames %d-%d) at %s, %.0f s elapsed'
            % (idx, start, end, time.strftime('%H:%M:%S'), time.time() - t0))
        start, idx = end + 1, idx + 1

    segs = sorted(glob.glob(os.path.join(SEGS, '*.mp4')))
    listfile = os.path.join(ROOT, 'renders', 'concat.txt')
    with open(listfile, 'w') as fh:
        for s in segs:
            fh.write("file '%s'\n" % s)
    out = os.path.join(ROOT, 'renders', 'pickup_truck_1080p.mp4')
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                    '-i', listfile, '-c', 'copy', out], check=True)
    for f in segs:
        os.remove(f)
    os.remove(listfile)
    for d in (FRAMES, SEGS):
        try:
            os.rmdir(d)
        except OSError:
            pass
    log('ALL DONE %s  (%.1f MB, %.1f min)'
        % (time.strftime('%H:%M:%S'), os.path.getsize(out) / 1e6,
           (time.time() - t0) / 60.0))


if __name__ == '__main__':
    main()
