"""Track and repair small generated dial markings. Requires opencv-python-headless and Pillow.
Authored for the inspected landscape macro v1, 1928x1076, 24 fps. No geometric watch edits.
"""
import cv2, numpy as np, json, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
source, output = sys.argv[1:]
if Path(output).exists(): raise RuntimeError('Output already exists')
cap=cv2.VideoCapture(source)
w,h=int(cap.get(3)),int(cap.get(4)); count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
assert (w,h)==(1928,1076)
gray=[]
for n in range(min(count,121)):
    ok,frame=cap.read()
    if not ok: break
    gray.append(cv2.cvtColor(cv2.resize(frame,(w//2,h//2)),cv2.COLOR_BGR2GRAY))
cap.release()
base=72; Hs={base:np.eye(3)}
face=np.zeros_like(gray[base]);cv2.ellipse(face,(571,145),(198,79),0,0,360,255,-1)
S=np.diag([2.,2.,1.]); invS=np.linalg.inv(S)
for direction in [-1,1]:
    previous=base; cumulative=np.eye(3)
    for current in range(base+direction, len(gray) if direction==1 else -1, direction):
        mask=cv2.warpPerspective(face,cumulative,(w//2,h//2))
        pts=cv2.goodFeaturesToTrack(gray[previous],120,.01,5,mask=mask)
        if pts is None or len(pts)<8: break
        nxt,status,error=cv2.calcOpticalFlowPyrLK(gray[previous],gray[current],pts,None,winSize=(31,31),maxLevel=4)
        good=status.ravel()==1
        if sum(good)<8: break
        step,inliers=cv2.findHomography(pts[good],nxt[good],cv2.RANSAC,2.0)
        if step is None: break
        cumulative=step@cumulative
        Hs[current]=S@cumulative@invS
        previous=current
mask=np.zeros((h,w),np.uint8)
for x1,y1,x2,y2 in [(1030,174,1290,219),(1028,317,1238,353),(1364,250,1452,289)]: cv2.rectangle(mask,(x1,y1),(x2,y2),255,-1)
overlay=Image.new('RGBA',(w,h))
d=ImageDraw.Draw(overlay)
font='/System/Library/Fonts/Supplemental/Arial.ttf'
# Small horizontal lettering follows the tracked dial plane.
def label(text,center,size,width,color):
    tile=Image.new('RGBA',(500,80));td=ImageDraw.Draw(tile)
    td.text((250,40),text,font=ImageFont.truetype(font,size),fill=color,anchor='mm')
    box=tile.getbbox();tile=tile.crop(box);tile=tile.resize((width,round(tile.height*.82)),Image.Resampling.LANCZOS)
    overlay.alpha_composite(tile,(round(center[0]-tile.width/2),round(center[1]-tile.height/2)))
label('MERIDIAN',(1158,197),32,229,(188,196,201,255))
label('AUTOMATIC',(1132,335),24,150,(189,196,201,255))
d=ImageDraw.Draw(overlay);d.polygon([(1369,253),(1443,254),(1440,282),(1368,282)],fill=(206,208,198,255))
label('18',(1406,267),25,31,(25,32,40,255))
rgba=np.array(overlay); alpha=rgba[:,:,3]; overlay_bgr=rgba[:,:,:3][:,:,::-1].astype(np.float32)*(alpha[:,:,None]/255.)
encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r','24','-i','-','-an','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',output],stdin=subprocess.PIPE)
cap=cv2.VideoCapture(source); modified=[]
for n in range(count):
    ok,frame=cap.read()
    if not ok: break
    if n in Hs:
        transform=Hs[n]
        m=cv2.warpPerspective(mask,transform,(w,h),flags=cv2.INTER_NEAREST)
        if np.count_nonzero(m):
            repaired=cv2.inpaint(frame,m,5,cv2.INPAINT_TELEA)
            pixels=cv2.warpPerspective(overlay_bgr,transform,(w,h))
            a=cv2.warpPerspective(alpha,transform,(w,h)).astype(np.float32)/255
            sigma=max(.5,min(5.,(n-72)/10+.5))
            pixels=cv2.GaussianBlur(pixels,(0,0),sigma)
            a=cv2.GaussianBlur(a,(0,0),sigma)
            frame=(repaired*(1-a[:,:,None])+pixels).clip(0,255).astype(np.uint8)
            modified.append(n)
    if n in [24,48,72,96]:cv2.imwrite(f'artifacts/media-qa/dial-repair-{n}.jpg',frame)
    encoder.stdin.write(frame.tobytes())
cap.release();encoder.stdin.close()
if encoder.wait()!=0:raise RuntimeError('Encoding failed')
Path(output.replace('.mp4','.json')).write_text(json.dumps({'source':source,'output':output,'modifiedFrames':modified,'operation':'Optical-flow homography tracking, inpaint only small dial text/date regions, overlay original MERIDIAN / AUTOMATIC /18. No watch shape or timing changes.'},indent=2))
print(json.dumps({'output':output,'modifiedFrames':len(modified),'first':min(modified),'last':max(modified)}))
