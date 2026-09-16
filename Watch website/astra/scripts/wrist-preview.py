"""Create an explicitly incomplete wrist preview from a reviewed clean tail.
The failed reassembly/clasp action is excluded; this is not a storyboard-approved replacement.
"""
import cv2, numpy as np, subprocess, json, sys
from pathlib import Path
source, reference, output=sys.argv[1:]
if Path(output).exists():raise RuntimeError('Output exists')
cap=cv2.VideoCapture(source);w,h=int(cap.get(3)),int(cap.get(4));cap.set(cv2.CAP_PROP_POS_FRAMES,180)
tail=[]
while True:
    ok,f=cap.read()
    if not ok:break
    tail.append(f)
cap.release();opening=cv2.imread(reference)
pipe=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r','24','-i','-','-an','-c:v','libx264','-crf','17','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',output],stdin=subprocess.PIPE)
smooth=lambda p:max(0,min(1,p))**2*(3-2*max(0,min(1,p)))
count=12+len(tail)*2+12
for n in range(count):
    if n<12:frame=opening
    else:
        frame=tail[min(len(tail)-1,(n-12)//2)]
        sigma=120*(1-smooth((n-12)/36))
        if sigma>.1:frame=cv2.GaussianBlur(frame,(0,0),sigma)
        mix=smooth((n-12)/12)
        if mix<1:frame=cv2.addWeighted(opening,1-mix,frame,mix,0)
    pipe.stdin.write(frame.tobytes())
pipe.stdin.close()
if pipe.wait()!=0:raise RuntimeError('Encoder failed')
Path(output.replace('.mp4','.json')).write_text(json.dumps({'source':source,'reference':reference,'output':output,'duration':count/24,'sourceTailStartFrame':180,'sourceTailFrames':len(tail),'status':'preview-story-incomplete','edit':'Use only clean wrist tail from7.5s onward, half speed, short final hold. Match abstract opening through a local defocus/blur-colour transition. Failed action entirely excluded; no reassembly or clasp-closure claim.'},indent=2))
print(json.dumps({'output':output,'frames':count,'duration':count/24}))
