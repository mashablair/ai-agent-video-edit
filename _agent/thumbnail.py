#!/usr/bin/env python3
"""Glorious Goddess thumbnail maker (step 3 of the pipeline).
usage: thumbnail.py NAME --headline "He just didn't *choose* you 🙄" [--n 3] [--at SEC ...]
  NAME = a folder in Videos/ (uses the newest Videos/NAME/NAME_clean[_vN].mp4); a video path also works (then --out DIR).
  *words* = blush italic accent; "|" forces a line break (otherwise lines are balanced automatically, at most 3).
  Writes Videos/NAME/CODE_thumb_1..3.jpg (CODE = NAME up to the first space, e.g. 1108-4) at the video's own resolution (next set _v2, _v3; never overwrites),
  CODE_thumb_list.txt, and a side-by-side check image in ~/vp/NAME/thumb_compare.jpg.
Look (approved 2026-11-08, from a GPT render she liked): her face big with the whole head in frame, crisp warm grade,
huge DM Serif Display in cream with the accent in blush italic, inside a stepped dark box low in the frame."""
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
W, H = 1080, 1920; K = 1.0                                     # set per video in main(): its own resolution, K = W/1080
CREAM = (250, 240, 226); BLUSH = (240, 178, 176); BOX = (38, 28, 24); BOX_ALPHA = 0.74
def safe(): return int(H * 0.125), int(H * 0.875)              # the IG grid shows the centre 3:4 crop; keep text inside

def run(cmd): return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
def duration(v): return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",v]))
def size(v): return [int(x) for x in run(["ffprobe","-v","error","-select_streams","v","-show_entries","stream=width,height","-of","csv=p=0",v]).split(",")[:2]]
def grab(v, t, w=None):
    p = subprocess.run(["ffmpeg","-v","error","-ss",f"{t:.3f}","-i",v,"-frames:v","1"]+(["-vf",f"scale={w}:-2"] if w else [])+["-f","image2pipe","-vcodec","png","-"], capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(p, np.uint8), cv2.IMREAD_COLOR)

# ---------- 1. pick frames: a smile with eyes on the camera (her pick, 2026-11-08) ----------
def score_frames(v, step=0.4):
    """Per frame: mouth darkness (open mid-word), visible teeth, mouth-corner height (corners up = smile), eyes open, facing camera, sharpness.
    Calibrated on frames she and Claude judged in 1108-2/1108-4: smiles and calm looks had dark<=0.21 and corners at 0.38-0.44,
    talking/shouting/pucker dark>=0.29 and corners 0.47-0.61; closed eyes ~25% under the video's typical eye contrast."""
    d = duration(v); det = cv2.FaceDetectorYN.create(A("yunet.onnx"), "", (540, 960), 0.7)
    raw = subprocess.run(["ffmpeg","-v","error","-i",v,"-vf",f"fps={1/step},scale=540:960","-f","rawvideo","-pix_fmt","bgr24","-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 960, 540, 3); rows = []
    for i, f in enumerate(fr):
        t = i*step
        if t < 1.0 or t > d-1.5: continue
        _, faces = det.detect(f)
        if faces is None: continue
        x,y,w,h = faces[0][:4]; L = faces[0][4:14].reshape(5,2); g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        ed = np.linalg.norm(L[1]-L[0]); fx = g[max(0,int(y)):int(y+h), max(0,int(x)):int(x+w)]
        if not fx.size: continue
        r = max(3,int(ed*0.22)); eyes = [g[int(p[1])-r:int(p[1])+r, int(p[0])-r:int(p[0])+r] for p in L[:2]]
        mx0,mx1 = sorted([int(L[3][0]),int(L[4][0])]); my = int((L[3][1]+L[4][1])/2); m = g[my-int(ed*.15):my+int(ed*.2), mx0:mx1]
        rows.append(dict(t=t, conf=float(faces[0][14]), eye=float(np.mean([e.std() for e in eyes if e.size])),
            sharp=float(cv2.Laplacian(fx, cv2.CV_64F).var()),
            dark=float((m < np.percentile(fx,12)).mean()) if m.size else 1, teeth=float((m > np.percentile(fx,80)).mean()) if m.size else 0,
            lift=float(((L[3][1]+L[4][1])/2-L[2][1])/ed), sym=float(abs((L[2][0]-L[0][0])-(L[1][0]-L[2][0]))/ed)))
    if not rows: sys.exit("no face found")
    med = {k: float(np.median([r[k] for r in rows])) for k in ("eye","sharp","teeth","lift")}
    for r in rows:
        r["score"] = (6*(r["teeth"]-med["teeth"]) - 6*(r["lift"]-med["lift"]) - 10*max(0, r["dark"]-0.21)
                      - (4 if r["eye"] < 0.82*med["eye"] else 0) - 2*r["sym"] + 0.5*min(r["sharp"]/med["sharp"], 1.5) + r["conf"])
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
        f = grab(v, tt, 1080); src = (f[:,:,::-1].astype(np.float32)/255).transpose(2,0,1)[None]
        fgr, pha, *rec = _sess.run(None, {"src":src,"r1i":rec[0],"r2i":rec[1],"r3i":rec[2],"r4i":rec[3],"downsample_ratio":ds})
    return pha[0,0]

# ---------- 3. frame: big face, whole head in frame, crisp grade ----------
def framed(v, t, facew=0.42, facey=0.27):
    """Her frame cropped so the face is ~42% of the width with the eyes in the upper third, zooming out only
    as far as needed to keep the top of her head in frame (no invented headroom). Returns frame, alpha (at W x H)."""
    hi = grab(v, t); a = cv2.resize(matte(v, t), (hi.shape[1], hi.shape[0]))
    sc = hi.shape[1]/540; det = cv2.FaceDetectorYN.create(A("yunet.onnx"), "", (540, int(hi.shape[0]/sc)), 0.6)   # same scale as the scorer:
    _, fc = det.detect(cv2.resize(hi, (540, int(hi.shape[0]/sc))))       # at full size it once took a patch of hair for a face
    if fc is None: sys.exit(f"no face at {t:.1f}s")
    fx,fy,fw,fh = max(fc, key=lambda f: f[2]*f[3])[:4]*sc                 # her face = the biggest one
    Z = min(1.8, max(1.0, facew*hi.shape[1]/fw)); cx, cy = fx+fw/2, fy+fh/2
    top = int(np.argmax(a[:, int(fx):int(fx+fw)].max(1) > 0.5))         # top of her hair, from the cut-out
    while True:
        cw, ch = hi.shape[1]/Z, hi.shape[0]/Z; y0 = max(0, min(cy-facey*ch, top-0.035*ch))
        if top-y0 >= 0.03*ch or Z <= 1.0: break
        Z = max(1.0, Z-0.03)
    x0 = min(max(0, cx-0.5*cw), hi.shape[1]-cw); y0 = min(y0, hi.shape[0]-ch)
    M = lambda im: cv2.resize(im[int(y0):int(y0+ch), int(x0):int(x0+cw)], (W, H), interpolation=cv2.INTER_LANCZOS4)
    return M(hi), M(a)

def crisp(x):   # clean and warm, a touch of contrast and colour (replaced the hazy cream wash, 2026-11-08)
    x = x.astype(np.float32)/255*np.array([0.96,1.0,1.04]); x = 0.5+(x-0.5)*1.10
    hsv = cv2.cvtColor(np.clip(x*255,0,255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32); hsv[...,1] *= 1.08
    return cv2.cvtColor(np.clip(hsv,0,255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)

def base(frame, a):   # she stays sharp; the background gets a soft blur so she pops
    a3 = cv2.GaussianBlur(a, (0,0), 1.2*K)[...,None]; p = crisp(frame)
    return p*a3 + cv2.GaussianBlur(p, (0,0), 5*K)*0.97*(1-a3)

# ---------- 4. headline: DM Serif Display in a stepped box ----------
def fonts(s): return (ImageFont.truetype(A("DMSerifDisplay-Regular.ttf"), s), ImageFont.truetype(A("DMSerifDisplay-Italic.ttf"), int(s*1.12)))
EMO = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
APPLE = "/System/Library/Fonts/Apple Color Emoji.ttc"
def emoji_img(ch, px):
    """Apple's emoji (what her viewers see on iPhone, crisp at 160 px); Twemoji PNG as the fallback off a Mac."""
    if os.path.exists(APPLE):
        im = Image.new("RGBA", (200, 200)); ImageDraw.Draw(im).text((0, 0), ch, font=ImageFont.truetype(APPLE, 160), embedded_color=True)
        if im.getbbox(): return im.crop(im.getbbox()).resize((px, px), Image.LANCZOS)
    cp = "-".join(f"{ord(c):x}" for c in ch if ord(c)!=0xfe0f); p = A(f"emoji/{cp}.png")
    if not os.path.exists(p):
        os.makedirs(A("emoji"), exist_ok=True)
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/jdecked/twemoji/main/assets/72x72/{cp}.png", p)
    if open(p, "rb").read(4) != b"\x89PNG": os.remove(p); sys.exit(f"emoji {cp}: the download was not a PNG")
    return Image.open(p).convert("RGBA").resize((px,px), Image.LANCZOS)

def segs(w): return re.findall(r"[\U0001F300-\U0001FAFF☀-➿]|[^\U0001F300-\U0001FAFF☀-➿️]+", w)
def wlen(w, f): return sum(f.size*0.99 if EMO.match(g) else f.getlength(g) for g in segs(w))
def tokens(text):
    out = []
    parts = re.split(r"\*", text)
    for i, part in enumerate(parts):
        ws = part.split(); glued = i and parts[i-1][-1:] not in ("", " ") and part[:1] not in ("", " ")
        if ws and out and glued and out[-1][0] != "|": out[-1] = (out[-1][0]+ws.pop(0), out[-1][1])   # "*fast*!" -> "fast!"
        out += [(w, i % 2 == 1) for w in ws]
    return out

def layout(headline):
    """Largest size whose lines (forced with |, else the most balanced split into <=3 lines) fit the frame with the box."""
    allt = tokens(headline.replace("|", " | ")); toks = [t for t in allt if t[0] != "|"]; forced = None
    if "|" in headline:                                                    # an *accent* may span a forced break
        forced = [[]]
        for t in allt:
            if t[0] == "|": forced.append([])
            else: forced[-1].append(t)
    split_acc = lambda L: sum(1 for x, y in zip(L, L[1:]) if x[-1][1] and y[0][1])   # a break inside an *accent* phrase
    for whole in (True, False):                     # keeping the accent phrase on one line beats a bigger size
        for s in range(int(200*K), int(60*K), -max(1, int(4*K))):
            reg, ita = fonts(s); sp = reg.getlength(" ")
            width = lambda ln, reg=reg, ita=ita, sp=sp: sum(wlen(w, ita if a else reg) for w, a in ln) + sp*(len(ln)-1)
            room = W - 2*int(s*0.36) - int(64*K) - int(44*K)
            if forced: splits = [forced]
            else:
                n = len(toks); splits = [[toks]] + [[toks[:i], toks[i:]] for i in range(1, n)] + [[toks[:i], toks[i:j], toks[j:]] for i in range(1, n) for j in range(i+1, n)]
            ok = [L for L in splits if max(width(l) for l in L) <= room and (forced or not whole or not split_acc(L))]
            if ok: return s, min(ok, key=lambda L: (max(width(l) for l in L) - min(width(l) for l in L)) + (0 if len(L) > 1 else 1e9)), width
    sys.exit("headline too long for a thumbnail")

def headline_layers(headline):
    s, L, width = layout(headline); reg, ita = fonts(s); sp = reg.getlength(" ")
    lh = [int((ita if any(a for _, a in ln) else reg).size*1.02) for ln in L]
    padx, pady, x0, r = int(s*0.36), int(s*0.22), int(64*K), int(s*0.26)
    y = ytop = safe()[1] - int(30*K) - sum(lh) - 2*pady                   # the whole box inside the grid-safe area
    box = Image.new("L", (W, H), 0); d = ImageDraw.Draw(box); rows = []
    for i, (ln, h) in enumerate(zip(L, lh)):                               # one rounded rect per line...
        rows.append((y-(pady if i == 0 else 0), y+h+(pady if i == len(L)-1 else 0), x0+width(ln)+2*padx)); y += h
    for y0, y1, x1 in rows: d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=255)
    for (a0, a1, ax), (b0, b1, bx) in zip(rows, rows[1:]):                # ...joined into one stepped shape
        d.rectangle([x0, a1-r, min(ax, bx), b0+r], fill=255)
    boxl = Image.new("RGBA", (W, H), BOX+(0,)); boxl.putalpha(box.point(lambda v: int(v*BOX_ALPHA)).filter(ImageFilter.GaussianBlur(K)))
    txt = Image.new("RGBA", (W, H)); dt = ImageDraw.Draw(txt); y = ytop
    for ln, h in zip(L, lh):
        x = x0+padx
        for w, acc in ln:
            f = ita if acc else reg; col = BLUSH if acc else CREAM; yy = y - f.getbbox("A")[1]*0.55
            for g in segs(w):
                if EMO.match(g):
                    px = int(f.size*0.9); txt.alpha_composite(emoji_img(g, px), (int(x), int(yy+f.size*0.12))); x += px*1.1
                else: dt.text((x, yy), g, font=f, fill=col+(255,)); x += f.getlength(g)
            x += sp
        y += h
    return boxl, txt, dict(size=s, lines=[" ".join(w for w, _ in ln) for ln in L])

def make(v, t, headline, out):
    frame, a = framed(v, t); canvas = Image.fromarray(np.clip(base(frame, a),0,255).astype(np.uint8)[:,:,::-1]).convert("RGBA")
    boxl, txt, info = headline_layers(headline); canvas.alpha_composite(boxl)
    sh = Image.new("RGBA", (W, H)); sh.putalpha(txt.getchannel("A").point(lambda v: v*0.35))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4*K)), (0, int(3*K))); canvas.alpha_composite(txt)
    canvas.convert("RGB").save(out, quality=94)
    return dict(file=out, t=round(t,2), **info)

def outputs(name, outdir, n):
    """Never overwrite: first set NAME_thumb_1..n, then NAME_thumb_v2_1..n, ..."""
    for v in range(1, 100):
        tag = "" if v == 1 else f"_v{v}"
        files = [os.path.join(outdir, f"{name.split(' ')[0]}_thumb{tag}_{i+1}.jpg") for i in range(n)]
        if not any(os.path.exists(f) for f in files): return tag, files
    sys.exit("too many versions")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("video", help="Videos/ folder name or a video path")
    ap.add_argument("--headline", required=True); ap.add_argument("--out")
    ap.add_argument("--n", type=int, default=3); ap.add_argument("--at", type=float, nargs="*")
    g = ap.parse_args()
    if os.path.isfile(g.video):
        video = g.video; name = re.sub(r"_clean(_v\d+)?$", "", os.path.splitext(os.path.basename(video))[0])
        outdir = g.out or os.path.dirname(os.path.abspath(video))
    else:
        m = [d for d in os.listdir(os.path.join(ROOT, "Videos")) if d == g.video or d.split(" ")[0] == g.video]   # "1108-4" or the full folder name
        if len(m) != 1: sys.exit(f"no single video folder for {g.video!r} in Videos/: {m}")
        name = m[0]; outdir = g.out or os.path.join(ROOT, "Videos", name)
        cands = {0 if m.group(1) is None else int(m.group(1)): f for f in os.listdir(outdir)   # newest NAME_clean[_vN].mp4
                 for m in [re.fullmatch(re.escape(name) + r"_clean(?:_v(\d+))?\.mp4", f)] if m} if os.path.isdir(outdir) else {}
        if not cands: sys.exit(f"no clean video in {outdir} (run step 1 first)")
        video = os.path.join(outdir, cands[max(cands)])
    W, H = size(video); K = W/1080; os.makedirs(outdir, exist_ok=True)
    times = g.at or [r["t"] for r in pick(score_frames(video), g.n)]
    tag, files = outputs(name, outdir, len(times))
    res = [make(video, t, g.headline, f) for t, f in zip(times, files)]
    wd = os.path.expanduser(f"~/vp/{name}"); os.makedirs(wd, exist_ok=True)
    cv2.imwrite(os.path.join(wd, f"thumb{tag}_compare.jpg"), np.hstack([cv2.resize(cv2.imread(r["file"]), (360, 640)) for r in res]))
    with open(os.path.join(outdir, f"{name.split(' ')[0]}_thumb{tag}_list.txt"), "w") as fh:
        fh.write(f"Headline: {g.headline}\nVideo: {os.path.basename(video)}\n")
        for r in res:
            m, s_ = divmod(r["t"], 60)
            fh.write(f"{os.path.basename(r['file'])}: frame at {int(m)}:{s_:04.1f}, {r['size']}px, lines: {' / '.join(r['lines'])}\n")
    print(json.dumps(res, indent=1)); print("check:", os.path.join(wd, f"thumb{tag}_compare.jpg"))
