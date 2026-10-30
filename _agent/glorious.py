#!/usr/bin/env python3
"""'Glorious' visuals, rendered from a B-roll Editor project file (captions.engine == "glorious").
Captions: Inter Tight Bold #FCFCFC, no outline/shadow/box, centered, <=2 lines, tight tracking/leading, each word slides
 in from the left as spoken, lead word supersized. Per-word keyword styles (word["emph"]): neg (Inter Tight Bold Italic in
 NEGATIVE mode: the letters show the inverted picture), serif (Instrument Serif Italic), script (yellow brush script),
 yellow (mustard Inter Tight Bold).
Visuals: B-roll slots with a slow push-in; slot options "headline" ("there" or "hot|COLD") and "reveal" (framed photo on a
 blurred copy that grows to full screen); project "zooms" [{a,b,z}] punch-ins on her face; project "tiles" [{a,b,num,text}].
Usage:  glorious.py plan PROJECT.json            -> pages + chunk count
        glorious.py chunk PROJECT.json WD N      -> WD/glo_N.mp4 (video only)
        glorious.py assemble PROJECT.json WD OUT -> joins chunks + the source audio
Times are absolute; each chunk is rendered on an absolute timeline, so captions/B-roll can cross chunk edges."""
import json, os, re, sys, subprocess, math
from PIL import ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); VID=os.path.dirname(HERE)
FONTDIR=os.path.join(HERE,"fonts"); LIB=os.path.join(os.path.dirname(VID),"b-roll collection")
FONTS={"black":("GL Sans Black","GLSansBlack.ttf"),"sans":("GL Sans","GLSans.ttf"),"sansm":("GL Sans Medium","GLSansMedium.ttf"),"sansi":("GL Sans Italic","GLSansItalic.ttf"),
       "serif":("GL Serif Italic","GLSerifItalic.ttf"),"script":("GL Script","GLScript.ttf")}
WHITE="#FCFCFC"; YELLOW="#F2EC2E"; MUSTARD="#D9C933"
STY={"small":("sans",.068,WHITE,False),"big":("sans",.13,WHITE,False),"neg":("sansi",.12,WHITE,True),
     "serif":("serif",.14,WHITE,False),"script":("script",.15,YELLOW,False),"yellow":("sans",.12,MUSTARD,False)}
SPAN=24.0
def hexass(h,a=0): h=h.lstrip("#"); return f"&H{a:02X}{h[4:6]}{h[2:4]}{h[0:2]}&"
def ts(t): t=max(0,t); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
def esc(t): return t.replace("\\","").replace("{","(").replace("}",")")

class Fonts:
    def __init__(s,d): s.d=d; s.cal=json.load(open(os.path.join(d,"cal.json"))); s.cache={}
    def pil(s,f,px):
        k=(f,round(px))
        if k not in s.cache: s.cache[k]=ImageFont.truetype(os.path.join(s.d,FONTS[f][1]),round(px))
        return s.cache[k]
    def fs(s,f,em): return em/s.cal[FONTS[f][0]]["r"]
    def base(s,f,em): return s.cal[FONTS[f][0]]["base"]*s.fs(f,em)

def probe(src):
    o=json.loads(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_streams","-show_format","-of","json",src],capture_output=True,text=True).stdout)
    s=o["streams"][0]; w,h=s["width"],s["height"]
    for sd in s.get("side_data_list",[]) or []:
        if abs(int(sd.get("rotation",0)))==90: w,h=h,w
    n,d=map(int,s["r_frame_rate"].split("/")); return w,h,round(n/d),float(o["format"]["duration"])

def load(pp):
    p=json.load(open(pp)); src=os.path.join(VID,p["video"]); W,H,fps,dur=probe(src); c=p.get("captions",{})
    words=[w for w in p["words"] if not w.get("hide") and w.get("w") and w["s"]>=c.get("start",0)-1e-6]
    return dict(p=p,src=src,W=W,H=H,fps=fps,dur=dur,words=words,broll=p.get("slots",[]),zooms=p.get("zooms",[]),
                tiles=p.get("tiles",[]),cap_on=c.get("enabled",False) and c.get("engine")=="glorious",
                cap_y=c.get("y",0.635),cap_y_broll=c.get("yB",0.70),c=c,
                sizes={k:float(c.get("gSizes",{}).get(k,v[1])) for k,v in STY.items()},
                pad=float(c.get("gPad",0.06)),line=float(c.get("gLine",0.72)),
                colors={"small":c.get("color","#FCFCFC"),"big":c.get("color","#FCFCFC"),"serif":c.get("color","#FCFCFC"),
                        "script":c.get("gScriptColor",YELLOW),"yellow":c.get("gYellowColor",MUSTARD)},outline=float(c.get("gOutline",0.003)) if c.get("gOutlineOn") else 0.0,outline_c=c.get("gOutlineColor","#000000"),
                shadow=float(c.get("gShadow",0.003)),shadow_op=float(c.get("gShadowOpacity",0.5)),shadow_blur=float(c.get("gShadowBlur",0.006)))

def pages(words):
    """Phrases split at punctuation and pauses >0.5s; at most 5 words per page; a keyword ends its page
    (it goes on its own line under the others) and a keyword that opens a phrase stands alone."""
    P=[];cur=[]
    for w in words:
        if cur and w["s"]-cur[-1]["e"]>0.5: P.append(cur);cur=[]
        cur.append(w)
        if re.search(r"[.?!,]$",w["w"]): P.append(cur);cur=[]
    if cur: P.append(cur)
    G=[]
    for ph in P:
        if len(ph)>1 and ph[0].get("emph"): G.append(ph[:1]); ph=ph[1:]
        segs=[];cur=[]
        for w in ph:   # a keyword closes its segment
            cur.append(w)
            if w.get("emph"): segs.append(cur); cur=[]
        if cur:
            if segs and len(cur)==1: segs[-1]+=cur   # don't leave one word alone after a keyword
            else: segs.append(cur)
        for sg in segs:   # balanced chunks of at most 5 words
            n=len(sg); k=math.ceil(n/5); base=n//k; extra=n%k; i=0
            for j in range(k):
                m=base+(1 if j<extra else 0); G.append(sg[i:i+m]); i+=m
    return G

def style_rows(page,S,F):
    """Captions-style wrapping: words fill lines up to the line width; a final keyword gets its own line."""
    W=S["W"]; em=lambda s: S["sizes"][s]*W; sp=0.22*em("small"); maxl=S["line"]*W
    def wl(w,s): e=em(s); return F.pil(STY[s][0],e).getlength(w["w"])-0.017*e*len(w["w"])
    kw_last=bool(page[-1].get("emph")) and len(page)>=2
    body=page[:-1] if kw_last else page
    rows=[];cur=[];curw=0
    for k,w in enumerate(body):
        st=w.get("emph") or ("big" if (k==0 and len(page)>1) or len(page)==1 else "small")
        l=wl(w,st)
        if cur and curw+sp+l>maxl: rows.append(cur); cur=[]; curw=0
        cur.append((w,st)); curw+=(sp if len(cur)>1 else 0)+l
    if cur: rows.append(cur)
    if kw_last: rows.append([(page[-1],page[-1]["emph"])])
    return rows

def paginate(S,F):
    """Pages with at most 2 lines: a page that would need 3+ lines is split after its first line."""
    out=[]; todo=pages(S["words"])
    while todo:
        g=todo.pop(0); rows=style_rows(g,S,F)
        if len(rows)>2 and len(g)>1:
            n=len(rows[0]); todo[0:0]=[g[:n],g[n:]]; continue
        out.append(g)
    res=[]
    for i,g in enumerate(out):
        a=g[0]["s"]-0.08; b=(out[i+1][0]["s"]-0.08) if i+1<len(out) else g[-1]["e"]+0.5
        res.append((a,min(b,g[-1]["e"]+1.0),g))
    return res

def layout(page,S,F):
    W,H=S["W"],S["H"]; rows=style_rows(page,S,F)
    em=lambda s: S["sizes"][s]*W; maxw=(1-2*S["pad"])*W
    def wlen(w,s): e=em(s); fsp=-0.017*e; return F.pil(STY[s][0],e).getlength(w["w"])+fsp*len(w["w"]), fsp
    sp=0.22*em("small")
    on_b=any(b["a"]<=page[0]["s"]+0.05<b["b"] for b in S["broll"])
    cy=(S["cap_y_broll"] if on_b else S["cap_y"])*H
    fit=[]
    for r in rows:   # a single word wider than the padded frame shrinks to fit
        tot=sum(wlen(w,s)[0] for w,s in r)+sp*(len(r)-1); fit.append(min(1.0,maxw/tot))
    ems=[max(em(s) for _,s in r)*k for r,k in zip(rows,fit)]
    if len(rows)==2:
        small2=all(st=='small' for _,st in rows[1]); gap=(1.12 if small2 else 0.80)*ems[1]
        B=[cy-gap/2+0.2*ems[0], cy+gap/2+0.2*ems[0]]
    else: B=[cy+0.25*ems[0]]
    out=[]
    for row,bl,k in zip(rows,B,fit):
        ws=[wlen(w,s) for w,s in row]; tot=(sum(x for x,_ in ws)+sp*(len(row)-1))*k; x=W/2-tot/2
        for (w,s),(l,fsp) in zip(row,ws): out.append((w,s,x,bl,em(s)*k,fsp*k)); x+=(l+sp)*k
    return out

def build(S):
    W,H=S["W"],S["H"]; F=Fonts(FONTDIR); ev=[]; neg=[]
    if S["cap_on"]:
        for a,b,g in paginate(S,F):
            for (w,s,x,bl,e,fsp) in layout(g,S,F):
                f,_,col,isneg=STY[s]; col=S["colors"].get(s,col); fs=F.fs(f,e); y=bl-F.base(f,e); t=int(max(0,w["s"]-0.04-a)*1000); dx=0.045*W
                ol=S["outline"]*W if not isneg else 0
                tag=(f"{{\\an7\\move({x-dx:.0f},{y:.0f},{x:.0f},{y:.0f},{t},{t+230})\\fn{FONTS[f][0]}\\fs{fs:.0f}\\fsp{fsp:.1f}"
                     f"\\bord{ol:.1f}\\3c{hexass(S['outline_c'])}\\shad0\\1c{hexass('#FFFFFF' if isneg else col)}\\alpha&HFF&\\t({t},{t+170},\\alpha&H00&)}}")
                (neg if isneg else ev).append((1,a,b,tag+esc(w["w"])))
                if S["c"].get("gShadowOn"):
                    o=S["shadow"]*W; al=f"&H{round((1-S['shadow_op'])*255):02X}&"
                    ev.append((0,a,b,f"{{\\an7\\move({x-dx+o:.0f},{y+o:.0f},{x+o:.0f},{y+o:.0f},{t},{t+230})\\fn{FONTS[f][0]}\\fs{fs:.0f}\\fsp{fsp:.1f}"
                        f"\\bord{ol:.1f}\\3c&H000000&\\shad0\\1c&H000000&\\blur{S['shadow_blur']*W:.1f}\\alpha&HFF&\\t({t},{t+170},\\alpha{al})}}"+esc(w["w"])))
    for h in [b for b in S["broll"] if b.get("headline")]:
        hl=[x for x in re.split(r"\s*\|\s*",h["headline"]) if x][:2]; a,b=h["a"],h["b"]; c=hexass(WHITE)
        pop="\\alpha&HFF&\\t(0,120,\\alpha&H00&)\\fscx116\\fscy116\\t(0,220,\\fscx100\\fscy100)"
        big=lambda t: f"{{\\fn{FONTS['sans'][0]}\\fs{F.fs('sans',.26*W):.0f}\\fsp{-0.02*.26*W:.1f}\\1c{c}}}{esc(t)}"
        txt=(f"{{\\fn{FONTS['serif'][0]}\\fs{F.fs('serif',.17*W):.0f}\\fsp-2\\1c{c}}}{esc(hl[0])}\\N"+big(hl[1])) if len(hl)==2 else big(hl[0])
        ev.append((2,a,b,f"{{\\an5\\pos({W/2:.0f},{0.20*H:.0f})\\bord0\\shad0\\q2{pop}}}"+txt))
    for tl in S["tiles"]:   # list card (Captions style): light panel with a translucent strip on top, bold "0 3", label
        a,b=tl["a"],tl["b"]; x0,y0=0.104*W,0.788*H; tw,th=0.78*W,0.132*H; bh=0.125*th; dx=0.05*W
        mv=lambda x,y,al=0: f"\\move({x-dx:.0f},{y:.0f},{x:.0f},{y:.0f},0,260)\\alpha&HFF&\\t(0,180,\\alpha&H{al:02X}&)"
        rect=lambda w_,h_: f"m 0 0 l {w_:.0f} 0 l {w_:.0f} {h_:.0f} l 0 {h_:.0f}"
        ev.append((3,a,b,f"{{\\an7{mv(x0,y0-bh,0x99)}\\bord0\\shad0\\1c&HFFFFFF&\\p1}}{rect(tw,bh)}{{\\p0}}"))
        ev.append((3,a,b,f"{{\\an7{mv(x0,y0,0x06)}\\bord0\\shad0\\1c&HF8F8F8&\\p1}}{rect(tw,th)}{{\\p0}}"))
        n=" ".join(str(tl.get("num","")).zfill(2)); F_=lambda f,e: F.fs(f,e*W)
        ev.append((4,a,b,f"{{\\an7{mv(x0+0.047*W,y0+0.024*H)}\\fn{FONTS['sans'][0]}\\fs{F_('sans',.035):.0f}\\fsp1\\1c&H4D4D4D&\\bord0\\shad0}}{n}"))
        ev.append((4,a,b,f"{{\\an7{mv(x0+0.047*W,y0+0.056*H)}\\fn{FONTS['sansm'][0]}\\fs{F_('sansm',.06):.0f}\\fsp{-0.012*.06*W:.1f}\\1c&H555555&\\bord0\\shad0}}{esc(tl['text'])}"))
    def doc(E):
        hdr=(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
             "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
             "Style: G,GL Sans,80,&H00FCFCFC,&H00FCFCFC,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n"
             "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        return hdr+"\n".join(f"Dialogue: {L},{ts(a)},{ts(b)},G,,0,0,0,,{t}" for L,a,b,t in sorted(E,key=lambda e:(e[1],e[0])))+"\n"
    return doc(ev),doc(neg)

def spans(S):
    fr=1/S["fps"]; k=max(1,math.ceil(S["dur"]/SPAN)); e=[round(S["dur"]*i/k/fr)*fr for i in range(k)]+[S["dur"]]
    return list(zip(e[:-1],e[1:]))

def face_at(S,t):
    import cv2, numpy as np
    cap=cv2.VideoCapture(S["src"]); c=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml"); pts=[]
    for dt in (0.1,0.4,0.8):
        cap.set(cv2.CAP_PROP_POS_MSEC,(t+dt)*1000); ok,f=cap.read()
        if not ok: continue
        g=cv2.cvtColor(cv2.resize(f,(540,int(540*f.shape[0]/f.shape[1]))),cv2.COLOR_BGR2GRAY); q=540/f.shape[1]
        fs=c.detectMultiScale(g,1.1,5,minSize=(70,70))
        if len(fs): x,y,w,h=max(fs,key=lambda r:r[2]); pts.append(((x+w/2)/q,(y+h/2)/q))
    return [float(v) for v in np.median(np.array(pts),axis=0)] if pts else [S["W"]/2,S["H"]*0.4]

def hook_ass(S,F):
    """Big hook word: Inter Tight Black, tight tracking, rises from below ('sunrise') and fades in, fades out at the end.
    Rendered white-on-black as a mask; the renderer fills it with the inverted picture (or a color) behind her."""
    W,H=S["W"],S["H"]; hk=S["p"]["hook"]; a,b=hk["a"],hk["b"]; lines=[x for x in re.split(r"\s*\|\s*",hk["text"]) if x]
    em=float(hk.get("size",0.34))*W; fnt=F.pil("black",em)
    wid=max(fnt.getlength(x)*(1-0.03) for x in lines); em*=min(1.0,0.94*W/wid)
    fs=F.fs("black",em); y=float(hk.get("y",0.22))*H; d=int((b-a)*1000); rise=0.045*H
    txt="\\N".join(esc(x) for x in lines)
    ev=(f"Dialogue: 0,{ts(a)},{ts(b+0.35)},G,,0,0,0,,{{\\an5\\move({W/2:.0f},{y+rise:.0f},{W/2:.0f},{y:.0f},0,650)\\fn{FONTS['black'][0]}\\fs{fs:.0f}"
        f"\\fsp{-0.03*em:.1f}\\q2\\bord0\\shad0\\1c&HFFFFFF&\\fscx96\\fscy96\\alpha&HFF&\\t(0,500,0.6,\\alpha&H00&\\fscx100\\fscy100)\\t({d},{d+350},\\alpha&HFF&)}}{txt}")
    return (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: G,GL Sans Black,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"+ev+"\n")

EMOJI_FONT="/System/Library/Fonts/Apple Color Emoji.ttc"
def _is_emoji(ch): o=ord(ch); return o>=0x1F000 or 0x2600<=o<0x27C0 or o in (0xFE0F,0x200D)
def hook_card_png(S,path):
    """Hook style "card" (added 2026-10-26): her approved text card drawn IN FRONT of her (no cut-out): slim cream panel,
    square corners, 8px gold bar, burgundy Montserrat with *accent words* in Instrument Serif Italic, | = line break,
    emoji from Apple Color Emoji. hook.y = panel top, hook.size = text size (fraction of the width)."""
    from PIL import Image, ImageDraw, ImageFilter
    W,H=S["W"],S["H"]; hk=S["p"]["hook"]; s=W/1080; F=Fonts(FONTDIR)
    lines=[x for x in re.split(r"\s*\|\s*",hk["text"]) if x]
    def runs(line):   # [(text, accent?, emoji?)]
        out=[]
        for k,part in enumerate(re.split(r"\*",line)):
            buf=""; emo=None
            for ch in part:
                e=_is_emoji(ch)
                if buf and e!=emo: out.append((buf,k%2==1,emo)); buf=""
                buf+=ch; emo=e
            if buf: out.append((buf,k%2==1,emo))
        return out
    def measure(em):
        sans=ImageFont.truetype(os.path.join(FONTDIR,"Montserrat-ExtraBold.ttf"),round(em)); ser=F.pil("serif",em*1.39)
        rows=[]
        for ln in lines:
            items=[]
            for t,acc,emo in runs(ln):
                if emo: items.append(("emoji",t,em*1.1))
                else: f=ser if acc else sans; items.append(("text",t,f.getlength(t),f))
            rows.append(items)
        return rows,sans,ser
    em=float(hk.get("size",0.052))*W
    for _ in range(12):   # shrink until the widest line fits
        rows,sans,ser=measure(em); widest=max(sum(it[2] for it in r) for r in rows)
        if widest<=W-(52+36+28+40)*s: break
        em*=0.94
    bar=8*s; x0=52*s; tx=x0+bar+28*s; padv=26*s; asc=ser.getmetrics()[0]; lh=1.62*em
    top=float(hk.get("y",0.60))*H; ph=padv*2+lh*len(rows)+0.25*em; pw=tx-x0+widest+28*s
    img=Image.new("RGBA",(W,H),(0,0,0,0))
    sh_=Image.new("RGBA",(W,H),(0,0,0,0)); ImageDraw.Draw(sh_).rectangle((x0,top+10*s,x0+pw,top+ph+10*s),fill=(0,0,0,70))
    img.alpha_composite(sh_.filter(ImageFilter.GaussianBlur(18*s)))
    d=ImageDraw.Draw(img); d.rectangle((x0,top,x0+pw,top+ph),fill=(250,243,235,242)); d.rectangle((x0,top,x0+bar,top+ph),fill=(201,160,90,255))
    efont=ImageFont.truetype(EMOJI_FONT,160)
    for i,r in enumerate(rows):
        base=top+padv+lh*(i+0.78); x=tx
        for it in r:
            if it[0]=="emoji":
                g=Image.new("RGBA",(220*len(it[1]),220),(0,0,0,0)); ImageDraw.Draw(g).text((0,0),it[1],font=efont,embedded_color=True)
                g=g.crop(g.getbbox()); h=round(it[2]); g=g.resize((max(1,round(g.width*h/g.height)),h),Image.LANCZOS)
                img.alpha_composite(g,(round(x),round(base-0.86*h))); x+=g.width
            else: d.text((x,base),it[1],font=it[3],fill=(110,26,46,255),anchor="ls"); x+=it[2]
    img.save(path)

def hookmask(pp,wd):
    """Person cut-out (Robust Video Matting) for the hook window, so the hook word sits behind her."""
    S=load(pp); hk=S["p"].get("hook") or {}; os.makedirs(wd,exist_ok=True)
    if not hk.get("enabled") or hk.get("style")=="card": print("no cut-out needed"); return
    subprocess.run([sys.executable,os.path.join(HERE,"rvm_mask.py"),S["src"],os.path.join(wd,"hookmask.mp4"),str(max(0,hk["a"])),str(min(S["dur"],hk["b"]+0.4)),
                    os.path.join(HERE,"rvm_mobilenetv3_fp32.onnx")],check=True)

def chain_beats(Z):
    """Each framing starts where the previous one ended (so edits in the editor stay smooth)."""
    Z.sort(key=lambda z:z["a"]); prev=None
    for z in Z:
        if z.get("type") not in ("beat","beatwhip"): prev=None; continue
        if z["type"]=="beat":
            if prev is not None and abs(prev["b"]-z["a"])<0.02:
                z["from"]=prev["to"] if prev["type"]=="beatwhip" else prev["z"]+prev.get("creep",0.015)*(prev["b"]-prev["a"])
            else: z["from"]=z.get("z",1.0); z["ease"]=0
        prev=z

def jump_cuts(src):
    import cv2, numpy as np
    cap=cv2.VideoCapture(src); fps=cap.get(5); prev=None; i=0; D=[]
    while True:
        ok=cap.grab()
        if not ok: break
        if True:
            _,f=cap.retrieve(); g=cv2.cvtColor(cv2.resize(f,(72,128)),cv2.COLOR_BGR2GRAY).astype("float32")
            if prev is not None: D.append((i/fps,float(np.abs(g-prev).mean())))
            prev=g
        i+=1
    d=np.array([x[1] for x in D]); med=float(np.median(d)) if len(d) else 0
    return [round(t,3) for k,(t,v) in enumerate(D) if v>max(6,4*med) and v>=d[max(0,k-3):k+4].max()]

def autozoom(pp):
    """Zoom plan modeled on the Captions example (0:21-0:25) that Maria approved:
    - a new framing on (almost) every caption page while her face is on screen: wide 1.0 / medium 1.12 / tight 1.24
      (a page with a keyword goes tight), at least 1.1s apart, never the same twice in a row
    - each change snaps in 0.22s, or instantly when a jump cut is within 0.35s (also hides the cut); then creeps in slowly
    - whips (white flash + 1.55x snapping back to medium in 0.8s) on big lines: project["whipAt"] times, else one about
      every 22s at a sentence start; the opening is a soft 1.35x pull-back without flash
    - nothing changes under B-roll; coming back from B-roll starts on a fresh (wide/medium) framing."""
    P=json.load(open(pp)); S=load(pp); F=Fonts(FONTDIR); dur=S["dur"]
    cuts=jump_cuts(S["src"]); B=sorted((s["a"],s["b"]) for s in P.get("slots",[]))
    inB=lambda t: any(a-0.05<=t<b for a,b in B)
    pg=[(a+0.08,g) for a,b,g in paginate(S,F)]
    whips=P.get("whipAt")
    if not whips:
        whips=[];last=-12
        for t,g in pg:
            if t-last>=22 and t>8 and not inB(t) and (re.search(r"[.?!]$",g[-1]["w"]) or g[0]["w"][:1].isupper()): whips.append(round(t-0.05,3)); last=t
    pts=[]
    for t,g in pg:
        if inB(t): continue
        c=min(cuts,key=lambda x:abs(x-t)) if cuts else -9; snap=abs(c-t)<=0.35
        pts.append({"t":round(c if snap else t-0.05,3),"cut":snap,"key":any(w.get("emph") for w in g)})
    for a,b in B: pts.append({"t":b,"cut":True,"key":False,"exit":True})
    for w in whips: pts.append({"t":w,"cut":True,"key":True,"whip":True})
    pts.sort(key=lambda p:p["t"]); keep=[]
    for p in pts:
        if keep and p["t"]-keep[-1]["t"]<1.1:
            if p.get("whip") or p.get("exit"): keep[-1]=p
            continue
        keep.append(p)
    cyc=[1.12,1.0,1.24,1.06,1.18,1.0]; ci=0; Z=[]; prev=1.0
    ends=[p["t"] for p in keep[1:]]+[dur]
    for p,end in zip(keep,ends):
        if inB(p["t"]+0.05) and not p.get("exit"): continue
        end=min([end]+[a for a,b in B if a>p["t"]+0.05])
        if p.get("whip"):
            to=1.12 if prev<1.1 else 1.0
            Z.append({"a":p["t"],"b":round(p["t"]+0.8,3),"type":"beatwhip","z":1.55,"to":to,"flash":True})
            if end>p["t"]+0.8: Z.append({"a":round(p["t"]+0.8,3),"b":round(end,3),"type":"beat","z":to,"ease":0,"creep":0.015})
            prev=to; continue
        L=1.24 if (p["key"] and prev<1.15) else cyc[ci%len(cyc)]; ci+=1
        if abs(L-prev)<0.05: L=cyc[ci%len(cyc)]; ci+=1
        if p.get("exit") and L>1.15: L=1.0
        Z.append({"a":p["t"],"b":round(end,3),"type":"beat","z":L,"ease":0 if p["cut"] else 0.22,"creep":0.015}); prev=L
    if Z and Z[0]["a"]>0.85: Z.insert(0,{"a":0.8,"b":Z[0]["a"],"type":"beat","z":1.0,"ease":0,"creep":0.015})
    Z=[z for z in Z if z["a"]>=0.8 or z["type"]!="beat"]
    Z.insert(0,{"a":0.0,"b":0.8,"type":"beatwhip","z":1.35,"to":1.0,"flash":False})
    Z=[z for z in Z if z["b"]-z["a"]>0.05]; chain_beats(Z)
    P["zooms"]=Z; P["zoomAnchor"]=P.get("zoomAnchor",[0.515,0.5]); json.dump(P,open(pp,"w"),indent=1)
    print(f"{sum(1 for z in Z if z['type']=='beat')} framing changes, {sum(1 for z in Z if z['type']=='beatwhip')} whips; jump cuts found: {len(cuts)}")

def fesc(p): return p.replace("\\","\\\\").replace(":","\\:").replace("'","\\'").replace(",","\\,").replace("[","\\[").replace("]","\\]")

def chunk(pp,wd,n):
    S=load(pp); os.makedirs(wd,exist_ok=True); W,H,fps=S["W"],S["H"],S["fps"]; t0,t1=spans(S)[n]; D=t1-t0
    main,neg=build(S); ap=os.path.join(wd,"glo.ass"); npth=os.path.join(wd,"glo_neg.ass"); open(ap,"w").write(main); open(npth,"w").write(neg)
    inputs=["-ss",f"{t0:.3f}","-t",f"{D+0.1:.3f}","-i",S["src"]]; f=[f"[0:v]setpts=PTS-STARTPTS+{t0:.6f}/TB,setsar=1[v0]"]; last="v0"
    # Zooms, modeled on the Captions app (measured frame by frame), all scaled around the frame center by default:
    #  drift: starts at s0 (1.064 long shot / 1.04 short) and eases out to 1.0 as (1-p)^1.5 by time b, then holds 1.0
    #  whip:  white flash (2 frames, ~55%) at a, shot starts at 1.55x and snaps back to 1.0 in 0.8s (measured curve)
    #  hold:  static zoom z from a to b (manual use)
    WHIP=[1.0,0.951,0.805,0.369,0.147,0.065,0.027,0.005,0.0]
    chain_beats(S["zooms"])
    Zs=[z for z in S["zooms"] if z["b"]+0.8>t0-1 and z["a"]<t1+1]
    terms=[]; flashes=[]; base=[]; beats=[]; zoomf=None
    for z in Zs:
        ty=z.get("type","drift"); a_,b_=z["a"],z["b"]
        if ty=="beat":   # absolute framing: snap from 'from' to z over 'ease' s (0 = instant cut), then creep in slowly
            e=float(z.get("ease",0.22)); fr=float(z.get("from",1.0)); cr=float(z.get("creep",0.015)); L=float(z.get("z",1.0))
            u=f"min(max((t-{a_:.4f})/{max(e,0.001):.3f},0),1)"; sm=f"({u}*{u}*(3-2*{u}))" if e>0 else "1"
            beats.append(f"gte(t,{a_:.4f})*lt(t,{b_:.4f})*({fr-1:.4f}+({L-fr:.4f})*{sm}+{cr:.4f}*(t-{a_:.4f}))")
            if z.get("flash"): flashes.append(a_)
            continue
        if ty=="beatwhip":   # absolute: flash, start at z (1.55) and snap down to 'to' with the measured curve
            to=float(z.get("to",1.0)); amp=float(z.get("z",1.55))-to
            if z.get("flash",True): flashes.append(a_)
            for kk in range(8):
                ta=a_+kk*0.1; da=WHIP[kk]; db=WHIP[kk+1]
                beats.append(f"gte(t,{ta:.4f})*lt(t,{ta+0.1:.4f})*({to-1:.4f}+{amp:.4f}*({da}+({db-da:.3f})*(t-{ta:.4f})/0.1))")
            continue
        if ty=="zoomin":   # the main zoom-in layer: eases in over 0.7s at a, holds, eases back out over 0.7s after b
            r=float(z.get("ramp",0.7)); amp=z.get("z",1.22)-1
            ui=f"min(max((t-{a_:.4f})/{r:.3f},0),1)"; uo=f"min(max((t-{b_:.4f})/{r:.3f},0),1)"
            base.append(f"gte(t,{a_:.4f})*lt(t,{b_:.4f})*{amp:.3f}*({ui}*{ui}*(3-2*{ui}))")
            base.append(f"gte(t,{b_:.4f})*lt(t,{b_+r:.4f})*{amp:.3f}*(1-{uo}*{uo}*(3-2*{uo}))")
            continue
        if ty=="whip":
            amp=z.get("z",1.55)-1; flashes.append(a_)
            for kk in range(8):
                ta=a_+kk*0.1; da=WHIP[kk]; db=WHIP[kk+1]
                terms.append(f"gte(t,{ta:.4f})*lt(t,{ta+0.1:.4f})*{amp:.3f}*({da}+({db-da:.3f})*(t-{ta:.3f})/0.1)")
        elif ty=="hold":
            terms.append(f"gte(t,{a_:.4f})*lt(t,{b_:.4f})*{z.get('z',1.15)-1:.3f}")
        else:
            d=max(0.2,b_-a_); terms.append(f"gte(t,{a_:.4f})*lt(t,{b_:.4f})*{z.get('z',1.064)-1:.4f}*pow(min(max(1-(t-{a_:.3f})/{d:.3f},0),1),1.5)")
    if terms or base or beats:
        ZE="((1+"+("+".join(base) or "0")+")*(1+"+("+".join(terms) or "0")+")*(1+"+("+".join(beats) or "0")+"))"
        ax=W*float(S["p"].get("zoomAnchor",[0.5,0.5])[0]); ay=H*float(S["p"].get("zoomAnchor",[0.5,0.5])[1])
        zoomf=f"scale=w='trunc({W}*{ZE}/2)*2':h='trunc({H}*{ZE}/2)*2':eval=frame:flags=bicubic,crop={W}:{H}:x='{ax:.0f}*({ZE}-1)':y='{ay:.0f}*({ZE}-1)'"
        f.append(f"[{last}]{zoomf}[vz]"); last="vz"
    S["_flashes"]=[x for x in flashes if t0-0.1<=x<t1]
    k=1
    for j,b in enumerate(S["broll"]):
        if b["b"]<=t0 or b["a"]>=t1: continue
        d=b["b"]-b["a"]; skip=max(0,t0-b["a"]); inputs+=["-ss",f"{b.get('from',0)+skip:.3f}","-t",f"{d-skip+0.2:.3f}","-i",os.path.join(LIB,"clips",b["clip"]+".mp4")]
        st=b["a"]+skip; P=f"(1+0.07*max(t-{b['a']:.3f},0)/{d:.3f})" if not b["clip"].startswith("photo-") else "1"
        push=(f",scale=w='trunc({W}*{P}/2)*2':h='trunc({H}*{P}/2)*2':eval=frame:flags=bicubic,crop={W}:{H}:x='{W/2}*({P}-1)':y='{H/2}*({P}-1)'") if P!="1" else ""
        tag=f"r{j}"
        if b.get("reveal"):
            K=f"(0.46+0.54*pow(min(max((t-{b['a']+0.75:.3f})/0.55,0),1),2)*(3-2*min(max((t-{b['a']+0.75:.3f})/0.55,0),1)))"
            f+= [f"[{k}:v]fps={fps},scale={W}:{H},setsar=1,setpts=PTS-STARTPTS+{st:.4f}/TB,split[{tag}a][{tag}b]",
                 f"[{tag}a]boxblur=30:2,eq=brightness=-0.32:saturation=0.8[{tag}bg]",
                 f"[{tag}b]scale=w='trunc({W}*{K}/2)*2':h='trunc({H}*{K}/2)*2':eval=frame[{tag}fg]",
                 f"[{tag}bg][{tag}fg]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame[{tag}]"]
        else: f.append(f"[{k}:v]fps={fps},scale={W}:{H},setsar=1,setpts=PTS-STARTPTS+{st:.4f}/TB{push}[{tag}]")
        f.append(f"[{last}][{tag}]overlay=enable='between(t,{b['a']:.3f},{b['b']:.3f})':eof_action=pass[o{j}]"); last=f"o{j}"; k+=1
    hk=S["p"].get("hook") or {}
    hm=os.path.join(wd,"hookmask.mp4")
    if hk.get("enabled") and hk.get("text") and hk.get("style")=="card" and hk["a"]<t1 and hk["b"]>t0:   # text card (fully gone by b) in front of her
        cp=os.path.join(wd,"hookcard.png"); hook_card_png(S,cp); a_,b_=hk["a"],hk["b"]
        inputs+=["-loop","1","-framerate",str(fps),"-t",f"{D+0.1:.3f}","-i",cp]
        fin=f",fade=t=in:st={a_:.3f}:d=0.25:alpha=1" if a_>0.01 else ""
        f+=[f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{t0:.6f}/TB{fin},fade=t=out:st={b_-0.25:.3f}:d=0.25:alpha=1[hcard]",
            f"[{last}][hcard]overlay=enable='between(t,{a_:.3f},{b_:.3f})':eof_action=pass[hk]"]; last="hk"; k+=1
    elif hk.get("enabled") and hk.get("text") and hk["a"]<t1 and hk["b"]+0.4>t0:
        meta=os.path.join(wd,"hookmask.json"); want={"a":hk["a"],"b":hk["b"],"src":S["src"]}
        if not os.path.exists(hm) or not os.path.exists(meta) or json.load(open(meta))!=want:
            hookmask(pp,wd); json.dump(want,open(meta,"w"))
        hp=os.path.join(wd,"glo_hook.ass"); open(hp,"w").write(hook_ass(S,Fonts(FONTDIR)))
        inputs+=["-i",hm,"-f","lavfi","-t",f"{D+0.1:.3f}","-i",f"color=black:s={W}x{H}:r={fps}"]; pm=k; tm=k+1; k+=2
        f+=[f"[{pm}:v]fps={fps},scale={W}:{H},setsar=1,setpts=PTS-STARTPTS+{hk['a']-0.0:.6f}/TB"+(f",{zoomf}" if zoomf else "")+",format=gray[pmask]",
            f"[{tm}:v]setpts=PTS-STARTPTS+{t0:.6f}/TB,subtitles=filename={fesc(hp)}:fontsdir={fesc(FONTDIR)},format=gray[tmask]",
            "[tmask][pmask]blend=all_expr='A*(255-B)/255',format=gray[hmask]",
            f"[{last}]split[hb][hv]"]
        if hk.get("style","neg")=="neg": f.append("[hv]negate[hfill]")
        else: f.append(f"[hv]drawbox=c={hk.get('color','#FFFFFF')}:t=fill[hfill]")
        f+=["[hfill][hmask]alphamerge[hword]","[hb][hword]overlay=eof_action=pass:shortest=0[hk]"]; last="hk"
    if S.get("_flashes"):
        inputs+=["-f","lavfi","-t",f"{D+0.1:.3f}","-i",f"color=white@0.55:s={W}x{H}:r={fps},format=rgba"]
        en="+".join(f"between(t,{x:.3f},{x+0.066:.3f})" for x in S["_flashes"])
        f.append(f"[{k}:v]setpts=PTS-STARTPTS+{t0:.6f}/TB[wf]"); f.append(f"[{last}][wf]overlay=enable='{en}'[fl]"); last="fl"; k+=1
    if "Dialogue" in neg:
        inputs+=["-f","lavfi","-t",f"{D+0.1:.3f}","-i",f"color=black:s={W}x{H}:r={fps}"]
        f+= [f"[{k}:v]setpts=PTS-STARTPTS+{t0:.6f}/TB,subtitles=filename={fesc(npth)}:fontsdir={fesc(FONTDIR)},format=gray[mask]",
             f"[{last}]split[pv][pn]","[pn]negate[inv]","[inv][mask]alphamerge[negw]","[pv][negw]overlay[nv]"]; last="nv"; k+=1
    SP=float(S["p"].get("speed",1.0) or 1.0)   # playback speed chosen in the editor (1 / 1.1 / 1.2 / 1.3); pitch kept natural
    cls=""   # classic caption presets (Bold Pop, Clean, Elegant, Boxed, Mic Drop) are drawn with captions.py's rules, same as the editor
    if S["c"].get("enabled") and S["c"].get("engine","classic")!="glorious":
        sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import captions as _cap
        cp=os.path.join(wd,"cls.ass"); open(cp,"w").write(_cap.build_ass(S["p"],W,H)); cls=f"subtitles=filename={fesc(cp)}:fontsdir={fesc(FONTDIR)},"
    f.append(f"[{last}]{cls}subtitles=filename={fesc(ap)}:fontsdir={fesc(FONTDIR)},setpts=(PTS-STARTPTS)/{SP},format=yuv420p[v]")
    nfr=round(t1*fps/SP)-round(t0*fps/SP)   # cumulative rounding keeps chunks in sync with the sped-up audio
    fs=os.path.join(wd,f"glo_fv{n}.txt"); open(fs,"w").write(";\n".join(f))
    subprocess.run(["ffmpeg","-y","-v","error"]+inputs+["-/filter_complex",fs,"-map","[v]","-an","-c:v","libx264","-preset","medium","-crf","18",
        "-pix_fmt","yuv420p","-r",str(fps),"-frames:v",str(nfr),"-colorspace","bt709","-color_primaries","bt709","-color_trc","bt709",os.path.join(wd,f"glo_{n}.mp4")],check=True)
    print(f"chunk {n}/{len(spans(S))-1} ok")

def assemble(pp,wd,out):
    S=load(pp); N=len(spans(S)); lst=os.path.join(wd,"glol.txt"); open(lst,"w").write("".join(f"file 'glo_{n}.mp4'\n" for n in range(N)))
    SP=float(S["p"].get("speed",1.0) or 1.0)
    au=["-c:a","copy"] if SP==1 else ["-af",f"atempo={SP}","-c:a","aac","-b:a","192k"]
    subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-i",S["src"],"-map","0:v","-map","1:a","-c:v","copy"]+au+
                    ["-map_metadata","-1","-movflags","+faststart","-shortest",out],check=True)
    nf=subprocess.run(["ffprobe","-v","error","-count_packets","-select_streams","v","-show_entries","stream=nb_read_packets","-of","csv=p=0",out],capture_output=True,text=True).stdout.strip()
    print("assembled",out,"frames",nf,"expected",round(S["dur"]*S["fps"]/SP),f"(speed {SP}x)")

if __name__=="__main__":
    cmd,pp=sys.argv[1],sys.argv[2]
    if cmd=="plan":
        S=load(pp)
        for a,b,g in paginate(S,Fonts(FONTDIR)): print(f"{a:6.2f} "+" ".join(w["w"]+("["+w["emph"]+"]" if w.get("emph") else "") for w in g))
        print("chunks",len(spans(S)))
    elif cmd=="chunk": chunk(pp,sys.argv[3],int(sys.argv[4]))
    elif cmd=="hookmask": hookmask(pp,sys.argv[3])
    elif cmd=="autozoom":   # plan the zooms (approved Oct 21: Captions-style framing changes every ~1.5s + whips)
        autozoom(pp)
    elif cmd=="anchors":   # fill missing face anchors (fractions) for zooms
        S=load(pp); p=S["p"]
        for z in p.get("zooms",[]):
            if "ax" not in z: x,y=face_at(S,z["a"]+0.05); z["ax"]=round(x/S["W"],4); z["ay"]=round(y/S["H"],4)
        json.dump(p,open(pp,"w"),indent=1); print("anchors set for",len(p.get("zooms",[])),"zooms")
    elif cmd=="assemble": assemble(pp,sys.argv[3],sys.argv[4])
