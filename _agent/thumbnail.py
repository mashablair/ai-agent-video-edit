#!/usr/bin/env python3
"""Glorious Goddess thumbnail maker (step 3 of the pipeline).
usage: thumbnail.py NAME --headline "How to lose a man *real fast*! 🤣" [--n 3] [--at SEC ...]
  NAME = a folder in Videos/ (uses Videos/NAME/NAME_clean.mp4); a video path also works (then --out DIR).
  *words* = blush italic accent. Writes Videos/NAME/NAME_thumb_1..3.jpg (next set _v2, _v3; never overwrites),
  NAME_thumb_list.txt, and a side-by-side check image in ~/vp/NAME/thumb_compare.jpg."""
import argparse, json, os, re, subprocess, sys, urllib.request
import numpy as np, cv2, onnxruntime as ort
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))            # .../AI agent video edit/_agent
ROOT = os.path.dirname(HERE)
_FILES = {"rvm.onnx": "rvm_mobilenetv3_fp32.onnx", "yunet.onnx": "face_detection_yunet_2023mar.onnx"}
def A(n):
    if n.endswith(".ttf"): return os.path.join(HERE, "fonts", n)
    if n.startswith("emoji"): return os.path.join(HERE, "thumb-emoji", n[len("emoji"):].lstrip("/"))
    return os.path.join(HERE, _FILES.get(n, n))
W, H = 1080, 1920
CREAM = (248, 238, 224); BLUSH = (236, 178, 172); BOX_ALPHA = 0.55
SAFE_TOP, SAFE_BOT = 240, 1680   # IG grid shows the centre 3:4 crop; keep text inside

def run(cmd): return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
def duration(v): return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",v]))
def grab(v, t, w=W):
    p = subprocess.run(["ffmpeg","-v","error","-ss",f"{t:.3f}","-i",v,"-frames:v","1","-vf",f"scale={w}:-2","-f","image2pipe","-vcodec","png","-"], capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(p, np.uint8), cv2.IMREAD_COLOR)

# ---------- 1. pick frames ----------
def score_frames(v, step=0.4):
    d = duration(v); det = cv2.FaceDetectorYN.create(A("yunet.onnx"), "", (360, 640), 0.7)
    tmp = subprocess.run(["ffmpeg","-v","error","-i",v,"-vf",f"fps={1/step},scale=360:640","-f","rawvideo","-pix_fmt","bgr24","-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(tmp, np.uint8).reshape(-1, 640, 360, 3); rows = []
    for i, f in enumerate(fr):
        t = i*step
        if t < 1.0 or t > d-1.5: continue
        _, faces = det.detect(f)
        if faces is None: continue
        x,y,w,h = faces[0][:4]; L = faces[0][4:14].reshape(5,2); conf = faces[0][14]
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        ed = np.linalg.norm(L[1]-L[0]); r = max(3,int(ed*0.22))
        eyes = [g[int(p[1])-r:int(p[1])+r, int(p[0])-r:int(p[0])+r] for p in L[:2]]
        eye_open = float(np.mean([e.std() for e in eyes if e.size]))
        fx = g[max(0,int(y)):int(y+h), max(0,int(x)):int(x+w)]
        sharp = float(cv2.Laplacian(fx, cv2.CV_64F).var()) if fx.size else 0
        smile = float(np.linalg.norm(L[4]-L[3])/ed)                       # wide mouth = smile
        mx0,mx1 = sorted([int(L[3][0]),int(L[4][0])]); my = int((L[3][1]+L[4][1])/2)
        mouth = g[my-int(ed*.18):my+int(ed*.22), mx0:mx1]
        open_m = float((mouth < np.percentile(fx,12)).mean()) if mouth.size else 0   # dark gap = mouth open mid-word
        sym = abs((L[2][0]-L[0][0])-(L[1][0]-L[2][0]))/ed                  # 0 = facing camera
        rows.append(dict(t=t,conf=float(conf),eye=eye_open,sharp=sharp,smile=smile,openm=open_m,sym=sym,size=w/360))
    if not rows: sys.exit("no face found")
    med = lambda k: float(np.median([r[k] for r in rows]))
    me, ms, msm = med("eye"), med("sharp"), med("smile")
    for r in rows:
        r["score"] = (min(r["eye"]/me,1.3)*2.0 - (2.5 if r["eye"]<0.8*me else 0)
                      + min(r["sharp"]/ms,1.5) + (r["smile"]/msm-1)*6.0
                      - r["openm"]*10 - r["sym"]*3 + r["conf"])
    return rows

def pick(rows, n, gap=4.0):
    out = []
    for r in sorted(rows, key=lambda r: -r["score"]):
        if all(abs(r["t"]-o["t"]) >= gap for o in out): out.append(r)
        if len(out) == n: break
    return out

# ---------- 2. cut-out (Robust Video Matting) ----------
_sess = None
def matte(v, t):
    global _sess
    _sess = _sess or ort.InferenceSession(A("rvm.onnx"), providers=["CPUExecutionProvider"])
    rec = [np.zeros((1,1,1,1), np.float32)]*4; ds = np.array([0.25], np.float32); pha = None
    for tt in [max(0,t-1.2+i*0.2) for i in range(6)] + [t]:      # warm up the recurrent state
        f = grab(v, tt); src = (f[:,:,::-1].astype(np.float32)/255).transpose(2,0,1)[None]
        fgr, pha, *rec = _sess.run(None, {"src":src,"r1i":rec[0],"r2i":rec[1],"r3i":rec[2],"r4i":rec[3],"downsample_ratio":ds})
    return f, pha[0,0]

# ---------- 3. look ----------
def warm(img, k=1.0):
    x = img.astype(np.float32)/255
    x = x*np.array([0.90,1.0,1.05])**k            # BGR: less blue, a touch more red
    x = 0.06*k + x*(1-0.06*k)                      # soft lifted blacks
    x = x + 0.08*k*np.sin(np.pi*x)*(x-0.5)*-1      # gentle, low-contrast curve
    return np.clip(x*255,0,255)

def compose_base(frame, a):
    a3 = cv2.GaussianBlur(a, (0,0), 1.2)[...,None]
    person = warm(frame, 1.0)
    small = cv2.resize(frame,(W//4,H//4)); m = (cv2.resize(a,(W//4,H//4))>0.05).astype(np.uint8)*255
    m = cv2.dilate(m, np.ones((9,9),np.uint8))
    filled = cv2.resize(cv2.inpaint(small, m, 6, cv2.INPAINT_TELEA),(W,H), interpolation=cv2.INTER_CUBIC)
    hsv = cv2.cvtColor(cv2.GaussianBlur(filled,(0,0),5), cv2.COLOR_BGR2HSV).astype(np.float32)
    blue = ((hsv[...,0]>80)&(hsv[...,0]<135)).astype(np.float32)          # cyan..blue hues
    hsv[...,1] *= 1-0.85*cv2.GaussianBlur(blue,(0,0),8)
    bg = warm(cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR), 1.3)
    bg = bg*0.68 + np.array(CREAM[::-1],np.float32)*0.32          # light, warm, uncluttered
    glow = np.zeros((H,W,1),np.float32); cv2.circle(glow,(int(W*.7),int(H*.12)),int(W*.9),1,-1)
    glow = cv2.GaussianBlur(glow,(0,0),W*.35)[...,None] if glow.ndim==2 else cv2.GaussianBlur(glow,(0,0),W*.35)[...,None]
    bg = bg + glow*np.array([150,200,255],np.float32)*0.12         # golden-hour bloom top right
    return np.clip(bg,0,255), np.clip(person,0,255), a3

# ---------- 4. headline (ChatGPT-reference look, approved 2026-11-08) ----------
BOX_RGB = (24, 17, 15); BOX_ALPHA = 0.80; RADIUS = 14
def fonts(size):
    reg = ImageFont.truetype(A("PlayfairDisplay[wght].ttf"), size); reg.set_variation_by_axes([700])
    ita = ImageFont.truetype(A("PlayfairDisplay-Italic[wght].ttf"), size); ita.set_variation_by_axes([600])
    return reg, ita

EMO = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
def emoji_img(ch, px):
    cp = "-".join(f"{ord(c):x}" for c in ch if ord(c)!=0xfe0f); p = A(f"emoji/{cp}.png")
    if not os.path.exists(p):
        os.makedirs(A("emoji"), exist_ok=True)
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/jdecked/twemoji/main/assets/72x72/{cp}.png", p)
    return Image.open(p).convert("RGBA").resize((px,px), Image.LANCZOS)

def tokens(headline):
    out = []
    for i, part in enumerate(re.split(r"\*", headline)):
        out += [(w, i % 2 == 1) for w in part.split()]
    return out

def segs(w): return [m for m in re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]|[^\U0001F300-\U0001FAFF\u2600-\u27BF\ufe0f]+", w)]
def wlen(w, f, size): return sum(size*1.0 if EMO.match(g) else f.getlength(g) for g in segs(w))

def wrap(headline, size, maxw):
    reg, ita = fonts(size); sp = reg.getlength(" ")*0.9
    lines, cur, cw = [], [], 0
    for w, acc in tokens(headline):
        ww = wlen(w, ita if acc else reg, size)
        if cur and cw+sp+ww > maxw: lines.append((cur,cw)); cur, cw = [], 0
        cw += (sp if cur else 0)+ww; cur.append((w,acc,ww))
    lines.append((cur,cw)); return lines

def balanced(headline, size, maxw):
    lines = wrap(headline, size, maxw); n = len(lines); w = maxw*0.35
    while n > 1 and w < maxw:                       # narrowest width with the same number of lines
        t = wrap(headline, size, w)
        if len(t) == n: return t
        w += size*0.2
    return lines

def text_block(headline, size, maxw, align="center"):
    lines = balanced(headline, size, maxw); reg, ita = fonts(size); sp = reg.getlength(" ")*0.9
    lh = int(size*1.04); px, py = int(size*.42), int(size*.30)
    tw = int(max(c for _,c in lines)); bw = tw+2*px; bh = lh*len(lines)+2*py+int(size*.12)
    txt = Image.new("RGBA",(bw,bh)); d = ImageDraw.Draw(txt)
    for i,(ws,cw) in enumerate(lines):
        x = px if align=="left" else (bw-cw)/2; y = py+i*lh-int(size*.06)
        for w,acc,ww in ws:
            f = ita if acc else reg; col = BLUSH if acc else CREAM
            for g in segs(w):                       # whole runs keep the font's kerning
                if EMO.match(g):
                    e = emoji_img(g, int(size*.82)); txt.alpha_composite(e,(int(x+size*.08),int(y+size*.24))); x += size*1.0
                else:
                    d.text((x,y),g,font=f,fill=col+(255,)); x += f.getlength(g)
            x += sp
    return txt, len(lines)

def candidates(face, headline):
    """(name, align, maxw, x, y) for a block of size bw,bh -> computed later"""
    fx,fy,fw,fh = face; gap = 0.04*W; m = 44
    left_w = fx - gap - m; right_w = W - (fx+fw) - gap - m
    out = [("left of face","left", left_w), ("right of face","left", right_w),
           ("above head","center", W*0.74), ("top","center", W*0.74)]
    return [c for c in out if c[2] > W*0.22]

def place(face, alpha, headline):
    fx,fy,fw,fh = face; fy2, fh2 = fy-0.18*fh, fh*1.18          # face + forehead must stay clear of words
    best = None
    for name, align, maxw in candidates(face, headline):
        for size in range(120, 66, -6):                          # big, bold, magazine-cover size
            txt, n = text_block(headline, size, maxw, align); bw, bh = txt.size
            if n > 4 or bw > maxw+0.9*size*0.84: continue
            if name == "left of face":  x, y = 44, fy - 0.35*fh
            elif name == "right of face": x, y = W-44-bw, fy - 0.35*fh
            elif name == "above head":  x, y = fx+fw/2-bw/2, fy - 0.42*fh - bh*0.92   # bottom tucks behind hair
            else:                        x, y = (W-bw)/2, SAFE_TOP+20
            x = int(min(max(36,x),W-bw-36)); y = int(min(max(SAFE_TOP,y),SAFE_BOT-bh))
            # words (not the padding) vs face
            ix0,iy0,ix1,iy1 = x+size*.4, y+size*.3, x+bw-size*.4, y+bh-size*.3
            fov = max(0,min(ix1,fx+fw)-max(ix0,fx))*max(0,min(iy1,fy2+fh2)-max(iy0,fy2))
            if fov > 0: continue
            inner = alpha[int(iy0):int(iy1), int(ix0):int(ix1)]
            hit = float((inner>0.3).mean()) if inner.size else 1
            s = -size*1.0 + hit*60 + (0 if name.startswith("left") else 6) + (4 if name=="top" else 0) + max(0,n-3)*15
            if best is None or s < best[0]: best = (s,name,x,y,txt,size)
            break                                                # largest size that fits this spot
    if best is None:                                             # tiny frame fallback
        txt,_ = text_block(headline, 66, W*0.74); best = (0,"top",(W-txt.size[0])//2,SAFE_TOP+20,txt,66)
    return best

def rounded_box(size):
    bw,bh = size; s = 3
    m = Image.new("L",(bw*s,bh*s),0); ImageDraw.Draw(m).rounded_rectangle([0,0,bw*s-1,bh*s-1], RADIUS*s, fill=int(255*BOX_ALPHA))
    box = Image.new("RGBA",(bw,bh),BOX_RGB+(0,)); box.putalpha(m.resize((bw,bh),Image.LANCZOS)); return box

def make(v, t, headline, out):
    frame, a = matte(v, t)
    frame = cv2.resize(frame,(W,H)); a = cv2.resize(a,(W,H))
    det = cv2.FaceDetectorYN.create(A("yunet.onnx"),"",(W,H),0.6); _, faces = det.detect(frame)
    face = faces[0][:4] if faces is not None else (W*.3,H*.25,W*.4,W*.4)
    bg, person, a3 = compose_base(frame, a)
    s,name,x,y,txt,size = place(face, a, headline)
    canvas = Image.fromarray(bg[:,:,::-1].astype(np.uint8)).convert("RGBA")
    canvas.alpha_composite(rounded_box(txt.size),(x,y))
    comp = np.array(canvas.convert("RGB"))[:,:,::-1].astype(np.float32)
    comp = person*a3 + comp*(1-a3)                       # she is in front of the box...
    top = Image.fromarray(np.clip(comp,0,255).astype(np.uint8)[:,:,::-1]).convert("RGBA")
    sh = Image.new("RGBA", txt.size); sh.putalpha(txt.getchannel("A").point(lambda v: v*0.45))
    top.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)), (x+2,y+3))   # soft depth
    top.alpha_composite(txt,(x,y))                       # ...and the words are in front of everything
    cv2.imwrite(out, np.array(top.convert("RGB"))[:,:,::-1], [cv2.IMWRITE_JPEG_QUALITY, 93])
    return dict(file=out, t=round(t,2), placement=name, size=size)

def outputs(name, outdir, n):
    """Never overwrite: first set NAME_thumb_1..n, then NAME_thumb_v2_1..n, ..."""
    for v in range(1, 100):
        tag = "" if v == 1 else f"_v{v}"
        files = [os.path.join(outdir, f"{name}_thumb{tag}_{i+1}.jpg") for i in range(n)]
        if not any(os.path.exists(f) for f in files): return tag, files
    sys.exit("too many versions")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("video", help="Videos/ folder name or a video path")
    ap.add_argument("--headline", required=True); ap.add_argument("--out")
    ap.add_argument("--n", type=int, default=3); ap.add_argument("--at", type=float, nargs="*")
    g = ap.parse_args()
    if os.path.isfile(g.video):
        video = g.video; name = os.path.splitext(os.path.basename(video))[0].replace("_clean", "")
        outdir = g.out or os.path.dirname(os.path.abspath(video))
    else:
        name = g.video; outdir = g.out or os.path.join(ROOT, "Videos", name)
        video = os.path.join(ROOT, "Videos", name, f"{name}_clean.mp4")
        if not os.path.isfile(video): sys.exit(f"no clean video at {video} (run step 1 first)")
    os.makedirs(outdir, exist_ok=True)
    times = g.at or [r["t"] for r in pick(score_frames(video), g.n)]
    tag, files = outputs(name, outdir, len(times))
    res = [make(video, t, g.headline, f) for t, f in zip(times, files)]
    wd = os.path.expanduser(f"~/vp/{name}"); os.makedirs(wd, exist_ok=True)
    cv2.imwrite(os.path.join(wd, f"thumb{tag}_compare.jpg"), np.hstack([cv2.resize(cv2.imread(r["file"]), (360, 640)) for r in res]))
    with open(os.path.join(outdir, f"{name}_thumb{tag}_list.txt"), "w") as fh:
        fh.write(f"Headline: {g.headline}\nVideo: {os.path.basename(video)}\n")
        for r in res:
            m, s_ = divmod(r["t"], 60)
            fh.write(f"{os.path.basename(r['file'])}: frame at {int(m)}:{s_:04.1f}, text {r['placement']}, {r['size']}px\n")
    print(json.dumps(res, indent=1)); print("check:", os.path.join(wd, f"thumb{tag}_compare.jpg"))
