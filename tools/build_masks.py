#!/usr/bin/env python3
"""Build glass masks (all 6 views) + wheel masks (3 main views) from the white base renders.
Saves PNG masks (white = region) used by the live canvas compositor in index.html."""
import os, numpy as np
from PIL import Image
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAR=os.path.join(ROOT,"public/tuning-assets/base/car")
MASKS=os.path.join(ROOT,"public/tuning-assets/base/masks")
GLASS=os.path.join(ROOT,"public/tuning-assets/base/glass"); os.makedirs(GLASS,exist_ok=True)
WHEEL=os.path.join(ROOT,"public/tuning-assets/base/wheels"); os.makedirs(WHEEL,exist_ok=True)
PREV=os.path.join(ROOT,"tools/_masktest"); os.makedirs(PREV,exist_ok=True)
VIEWS=["front-left","side","rear-left","top","front","rear"]

# cabin band (y fraction) per view for glass
GLASS_BAND={"front-left":(0.12,0.47),"side":(0.18,0.46),"rear-left":(0.16,0.46),
            "top":(0.10,0.80),"front":(0.18,0.45),"rear":(0.30,0.55)}
WHEELS={
 "front-left":[(0.602,0.638,0.070,0.120),(0.800,0.520,0.030,0.058)],
 "side":[(0.225,0.620,0.072,0.130),(0.723,0.620,0.072,0.130)],
 "rear-left":[(0.164,0.628,0.043,0.103),(0.452,0.648,0.057,0.133)],
}

def comps(v):
    base=np.asarray(Image.open(os.path.join(CAR,v+".jpg")).convert("RGB"),float)
    body=np.asarray(Image.open(os.path.join(MASKS,v+".png")).convert("L").resize((base.shape[1],base.shape[0])),float)/255.0
    return base,body

def glass_mask(v,base,body):
    H,W,_=base.shape
    R,G,B=base[:,:,0],base[:,:,1],base[:,:,2]
    lum=(0.299*R+0.587*G+0.114*B)/255.0
    mx=np.maximum(np.maximum(R,G),B);mn=np.minimum(np.minimum(R,G),B);sat=(mx-mn)/(mx+1e-6)
    yy,xx=np.mgrid[0:H,0:W]; yf=yy/H; xf=xx/W
    cols=np.where(body.max(0)>0.4)[0]
    x0,x1=(cols.min()/W,cols.max()/W) if len(cols) else (0,1)
    pad=0.03
    lo,hi=GLASS_BAND[v]
    g=(lum<0.30)&(sat<0.45)&(body<0.4)&(yf>lo)&(yf<hi)&(xf>x0+pad)&(xf<x1-pad)
    return g

def wheel_mask(v,base,body):
    H,W,_=base.shape
    yy,xx=np.mgrid[0:H,0:W]; yf=yy/H; xf=xx/W
    ell=np.zeros((H,W),bool)
    for cx,cy,rx,ry in WHEELS.get(v,[]):
        ell|=(((xf-cx)/rx)**2+((yf-cy)/ry)**2)<=1.0
    R,G,B=base[:,:,0],base[:,:,1],base[:,:,2]
    lum=(0.299*R+0.587*G+0.114*B)/255.0
    mx=np.maximum(np.maximum(R,G),B);mn=np.minimum(np.minimum(R,G),B);sat=(mx-mn)/(mx+1e-6)
    neutral=np.abs(R-B)<20   # silver wheels are neutral; warm pavers (R>B) excluded
    return ell&(body<0.4)&(lum>0.30)&(lum<0.82)&(sat<0.25)&neutral

for v in VIEWS:
    base,body=comps(v)
    g=glass_mask(v,base,body)
    Image.fromarray((g*255).astype(np.uint8)).save(os.path.join(GLASS,v+".png"))
    if v in WHEELS:
        w=wheel_mask(v,base,body)
        Image.fromarray((w*255).astype(np.uint8)).save(os.path.join(WHEEL,v+".png"))
        # preview: black wheels + 38% tint
        lum=(0.299*base[:,:,0]+0.587*base[:,:,1]+0.114*base[:,:,2])/255.0
        out=base.copy()
        out[g]=out[g]*0.42
        sh=np.clip(lum*1.2,0,1)[...,None]
        blk=np.array([18,18,20])*sh
        out[w]=blk[w]
        Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(os.path.join(PREV,v+"_preview.jpg"),quality=86)
        print(v,"glass%",round(g.mean()*100,2),"wheel%",round(w.mean()*100,2))
    else:
        print(v,"glass%",round(g.mean()*100,2))
print("masks ->",GLASS,WHEEL)
