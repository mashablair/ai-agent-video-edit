#!/usr/bin/env python3
"""Talking-head video polisher. Stages (each fits in one 3-minute shell call):
  setup | transcribe SRC WD | plan WD | audio WD | chunk WD N | assemble WD OUT | qa WD OUT
WD = work dir (outside the user's folder). Edits are decided by Claude in WD/edits.json."""
import sys, os, json, re, subprocess, math
HOME=os.path.expanduser("~"); MODEL=f"{HOME}/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/"
RNN=f"{HOME}/vidpolish/sh.rnnn"
FONT="/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
def sh(c,**k): return subprocess.run(c,check=True,**k)
def J(p): return json.load(open(p))
def W_(p,o): json.dump(o,open(p,"w"),indent=0)
def probe(src):
    o=json.loads(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_streams","-show_format","-of","json",src],capture_output=True,text=True).stdout)
    s=o["streams"][0]; w,h=s["width"],s["height"]; rot=0
    rot=int(float((s.get("tags") or {}).get("rotate",0) or 0))
    for sd in s.get("side_data_list",[]) or []:
        if "rotation" in sd: rot=int(sd["rotation"])
    if abs(rot)%180==90: w,h=h,w
    n,d=map(int,s["r_frame_rate"].split("/")); fps=round(n/d) if abs(n/d-round(n/d))<0.05 else n/d
    return w,h,fps,float(o["format"]["duration"])

DEFAULT_TOOLS=f"{HOME}/mnt/AI agent video edit/_tools"
MODEL_NAME="sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
def setup(tools=None):
    """Fast path: install from the saved _tools folder on the user's Mac (seconds, no downloads).
    Slow path (no _tools): download from PyPI/GitHub. `setup --refresh` re-downloads and re-saves _tools."""
    tools=tools or DEFAULT_TOOLS; refresh=tools=="--refresh"
    if refresh: tools=DEFAULT_TOOLS
    os.makedirs(f"{HOME}/vidpolish",exist_ok=True)
    pk=["sherpa-onnx","soundfile","numpy","pillow","opencv-python-headless<5"]
    if os.path.isdir(f"{tools}/wheels") and not refresh:
        sh([sys.executable,"-m","pip","install","-q","--no-index","--find-links",f"{tools}/wheels"]+pk)
        if not os.path.exists(MODEL+"tokens.txt"):
            if os.path.lexists(MODEL.rstrip("/")): os.remove(MODEL.rstrip("/"))
            os.symlink(f"{tools}/{MODEL_NAME}",MODEL.rstrip("/"))
        if not os.path.exists(RNN): sh(["cp",f"{tools}/sh.rnnn",RNN])
        print("setup ok (from saved tools:",open(f"{tools}/VERSION.txt").read().strip().splitlines()[0] if os.path.exists(f"{tools}/VERSION.txt") else "?",")"); return
    sh([sys.executable,"-m","pip","install","-q","--upgrade"]+pk)
    if refresh or not os.path.exists(MODEL+"tokens.txt"):
        if os.path.islink(MODEL.rstrip("/")): os.remove(MODEL.rstrip("/"))
        sh(["curl","-sL","-o",f"{HOME}/pk.tar.bz2",f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{MODEL_NAME}.tar.bz2"])
        sh(["tar","xjf",f"{HOME}/pk.tar.bz2","-C",HOME]); os.remove(f"{HOME}/pk.tar.bz2")
    if not os.path.exists(RNN):
        sh(["curl","-sL","-o",RNN,"https://raw.githubusercontent.com/GregorR/rnnoise-models/master/somnolent-hogwash-2018-09-01/sh.rnnn"])
    if os.path.isdir(os.path.dirname(tools)):   # save tools to the user's Mac for next time
        os.makedirs(f"{tools}/wheels",exist_ok=True); os.makedirs(f"{tools}/{MODEL_NAME}",exist_ok=True)
        sh([sys.executable,"-m","pip","download","-q","-d",f"{tools}/wheels"]+pk)
        for f in ["encoder.int8.onnx","decoder.int8.onnx","joiner.int8.onnx","tokens.txt"]: sh(["cp",MODEL+f,f"{tools}/{MODEL_NAME}/"])
        sh(["cp",RNN,f"{tools}/sh.rnnn"]); sh(["cp",os.path.abspath(__file__),f"{tools}/polish.py"])
        import datetime, sherpa_onnx
        open(f"{tools}/VERSION.txt","w").write(f"saved {datetime.date.today()} | sherpa-onnx {sherpa_onnx.__version__} | ASR {MODEL_NAME} | RNNoise sh.rnnn\nDelete this _tools folder any time; the skill re-downloads and re-saves it.\n")
    print("setup ok (downloaded)")

def recognizer():
    import sherpa_onnx
    return sherpa_onnx.OfflineRecognizer.from_transducer(encoder=MODEL+"encoder.int8.onnx",decoder=MODEL+"decoder.int8.onnx",joiner=MODEL+"joiner.int8.onnx",tokens=MODEL+"tokens.txt",model_type="nemo_transducer",num_threads=4)

def asr_words(wav):
    import soundfile as sf
    rec=recognizer(); audio,sr=sf.read(wav,dtype="float32"); dur=len(audio)/sr
    out=subprocess.run(["ffmpeg","-i",wav,"-af","silencedetect=n=-35dB:d=0.25","-f","null","-"],capture_output=True,text=True).stderr
    ss=[float(x) for x in re.findall(r"silence_start: ([\d.]+)",out)]; se=[float(x) for x in re.findall(r"silence_end: ([\d.]+)",out)]
    B=[0.0]
    for a,b in zip(ss,se):
        m=(a+b)/2
        if m-B[-1]>=15: B.append(m)
    B.append(dur); B2=[B[0]]
    for b in B[1:]:
        while b-B2[-1]>30: B2.append(B2[-1]+28)
        B2.append(b)
    words=[]
    for a,b in zip(B2[:-1],B2[1:]):
        s=rec.create_stream(); s.accept_waveform(sr,audio[int(a*sr):int(b*sr)]); rec.decode_stream(s)
        cur=None
        for t,st in zip(s.result.tokens,s.result.timestamps):
            if t.startswith(" ") or cur is None:
                if cur: words.append(cur)
                cur={"w":t.strip(),"s":a+st}
            else: cur["w"]+=t
        if cur: words.append(cur)
    for i,w in enumerate(words):
        nxt=words[i+1]["s"] if i+1<len(words) else dur; e=nxt
        for a,b in zip(ss,se):
            if w["s"]+0.1<a<nxt: e=min(e,a)
        w["e"]=e
    return words,list(zip(ss,se)),dur

def verbatim_words(wav):
    import numpy as np, soundfile as sf
    A,sr=sf.read(wav,dtype="float32"); dur=len(A)/sr; rec=recognizer()
    out=subprocess.run(["ffmpeg","-i",wav,"-af","silencedetect=n=-38dB:d=0.18","-f","null","-"],capture_output=True,text=True).stderr
    ss=[float(x) for x in re.findall(r"silence_start: ([\d.]+)",out)]; se=[float(x) for x in re.findall(r"silence_end: ([\d.]+)",out)]
    # speech regions = gaps between silences
    regs=[]; t=0.0
    for a,b in zip(ss,se):
        if a>t+0.05: regs.append((max(0,t-0.05),a+0.05))
        t=b
    if dur>t+0.05: regs.append((t-0.05,dur))
    # merge tiny regions into ~1-4s phrases
    ph=[]
    for a,b in regs:
        if ph and (b-ph[-1][0]<4.0 and a-ph[-1][1]<0.35): ph[-1]=(ph[-1][0],b)
        else: ph.append((a,b))
    words=[]; pad=np.zeros(sr//5,dtype="float32")
    for a,b in ph:
        s=rec.create_stream(); s.accept_waveform(sr,np.concatenate([pad,A[int(a*sr):int(b*sr)],pad])); rec.decode_stream(s)
        cur=None
        for tk,st in zip(s.result.tokens,s.result.timestamps):
            t0=a+st-0.2
            if tk.startswith(" ") or cur is None:
                if cur: words.append(cur)
                cur={"w":tk.strip(),"s":round(max(a,t0),3)}
            else: cur["w"]+=tk
        if cur: words.append(cur)
    for i,w in enumerate(words):
        nxt=words[i+1]["s"] if i+1<len(words) else dur; e=nxt
        for x,y in zip(ss,se):
            if w["s"]+0.1<x<nxt: e=min(e,x)
        w["e"]=e
    return words,list(zip(ss,se)),dur

def transcribe(src,wd):
    os.makedirs(wd,exist_ok=True); w,h,fps,dur=probe(src)
    W_(f"{wd}/meta.json",{"src":os.path.abspath(src),"w":w,"h":h,"fps":fps,"dur":dur})
    sh(["ffmpeg","-v","error","-y","-i",src,"-vn","-ac","1","-ar","16000",f"{wd}/a16.wav"])
    words,sil,dur=verbatim_words(f"{wd}/a16.wav"); W_(f"{wd}/words.json",{"words":words,"silences":sil,"dur":dur})
    print(f"{w}x{h} {fps}fps {dur:.1f}s, {len(words)} words. Format: idx:word@start [gap>0.4s]")
    line=[]
    for i,x in enumerate(words):
        gap=words[i+1]["s"]-x["e"] if i+1<len(words) else 0
        line.append(f"{i}:{x['w']}@{x['s']:.2f}"+(f" [{gap:.1f}]" if gap>0.4 else ""))
        if len(line)==12: print(" ".join(line)); line=[]
    print(" ".join(line))
    ws=[x["w"].lower().strip(",.?!") for x in words]
    print("FILLERS:",[(i,x["w"]) for i,x in enumerate(words) if ws[i] in ("uh","um","umm","uhm","hmm","mm")])
    print("REPEATS:",[(i-1,i,ws[i]) for i in range(1,len(ws)) if ws[i]==ws[i-1]])

def plan(wd):
    import numpy as np, soundfile as sf
    M=J(f"{wd}/meta.json"); D=J(f"{wd}/words.json"); E=J(f"{wd}/edits.json"); W=D["words"]; dur=D["dur"]
    DEL=set()
    for a,b in E.get("delete_words",[]): DEL.update(range(a,b+1))
    segs=[]
    for i,w in enumerate(W):
        if i in DEL: continue
        if segs and segs[-1]["last"]==i-1 and w["s"]-W[i-1]["e"]<0.45: segs[-1].update(e=w["e"],last=i)
        else: segs.append({"s":w["s"],"e":w["e"],"first":i,"last":i})
    for g in segs:   # base breathing room around each phrase
        i0,i1=g["first"],g["last"]
        lo=W[i0-1]["e"]+0.02 if i0>0 else 0; hi=W[i1+1]["s"]-0.04 if i1+1<len(W) else dur
        g["s"]=max(lo,g["s"]-0.12); g["e"]=min(hi,g["e"]+0.15)
    A,sr=sf.read(f"{wd}/a16.wav",dtype="float32"); hop=sr//100
    fr=A[:len(A)//hop*hop].reshape(-1,hop); db=20*np.log10(np.sqrt((fr**2).mean(1))+1e-9)
    lv=lambda t: db[min(len(db)-1,max(0,int(t*100)))]
    for g in segs:   # extend edges until the voice actually fades (prevents clipped words)
        i0,i1=g["first"],g["last"]; lim=W[i1+1]["s"]-0.03 if i1+1<len(W) else dur
        t=g["e"]
        while t<lim and lv(t)>-42: t+=0.01
        g["e"]=min(lim,t+0.06); lo=W[i0-1]["s"]+0.15 if i0>0 else 0; t=g["s"]
        while t>lo and lv(t-0.01)>-42: t-=0.01
        g["s"]=max(lo,t-0.04)
    for k in range(1,len(segs)):
        if segs[k]["s"]<segs[k-1]["e"]: segs[k]["s"]=segs[k-1]["e"]
    out=[]
    for g in segs:
        parts=[(g["s"],g["e"])]
        for a,b in E.get("delete_times",[]):
            np_=[]
            for x,y in parts:
                if b<=x or a>=y: np_.append((x,y))
                else:
                    if a>x: np_.append((x,a))
                    if b<y: np_.append((b,y))
            parts=np_
        out+=[{"s":x,"e":y} for x,y in parts if y-x>0.05]
    F=1/M["fps"]
    for g in out: g["s"]=round(g["s"]/F)*F; g["e"]=round(g["e"]/F)*F
    segs=[g for g in out if g["e"]>g["s"]]
    def m(t):
        acc=0
        for g in segs:
            if t<g["s"]: return acc
            if t<g["e"]: return acc+t-g["s"]
            acc+=g["e"]-g["s"]
        return acc
    off=[0.0]
    for g in segs: off.append(off[-1]+g["e"]-g["s"])
    # zoom: toggle in/out at a cut at most every ~8-10s
    z=[0]*len(segs); cur=0; last=0.0
    for k in range(len(segs)):
        if k>0 and off[k]-last>=8 and segs[k]["e"]-segs[k]["s"]>=1.5: cur=1-cur; last=off[k]
        z[k]=cur
    # face anchors (zoom pushes in on face->chest, never frame centre)
    import cv2
    c1=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    c2=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_profileface.xml")
    cap=cv2.VideoCapture(M["src"]); FC=[]; sw,shh=M["w"],M["h"]; q=540/sw
    for g in segs:
        pts=[]
        for t in np.linspace(g["s"]+0.1,max(g["s"]+0.1,g["e"]-0.1),5):
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,f=cap.read()
            if not ok: continue
            if f.shape[1]!=sw: f=cv2.resize(f,(sw,shh))
            gimg=cv2.cvtColor(cv2.resize(f,(540,int(shh*q))),cv2.COLOR_BGR2GRAY)
            fs=list(c1.detectMultiScale(gimg,1.1,5,minSize=(int(90*sw/1080*q*2),)*2)) or list(c2.detectMultiScale(gimg,1.1,5,minSize=(int(90*sw/1080*q*2),)*2))
            if fs:
                x,y,w,h=max(fs,key=lambda r:r[2]); pts.append(((x+w/2)/q,(y+h/2)/q,h/q))
        FC.append(np.median(np.array(pts),axis=0).tolist() if pts else None)
    good=[f for f in FC if f and f[1]<shh*0.55]
    gx,gy,gh=np.median(np.array(good),axis=0) if good else (sw/2,shh*0.45,shh*0.19)
    anc=[None]*len(segs); k=0
    while k<len(segs):
        j=k
        while j+1<len(segs) and z[j+1]==z[k]: j+=1
        pts=[FC[i] for i in range(k,j+1) if FC[i] and FC[i][1]<shh*0.55] or [[gx,gy,gh]]
        cx,cy,_=np.median(np.array(pts),axis=0)
        for i in range(k,j+1): anc[i]=(float(cx),float(min(shh*0.8,cy+1.1*gh)))
        k=j+1
    events=[]
    for c in E.get("cards",[]): events.append(dict(c,t=m(W[c["word"]]["s"])))
    # chunks of ~35s output so each render fits in one shell call
    chunks=[]; a=0
    for k in range(1,len(segs)+1):
        if k==len(segs) or off[k]-off[a]>=35: chunks.append((a,k)); a=k
    # overlay vertical position: keep hook/cards off the face (face box from detections, in output coords)
    sc=sw/1080; Zf=1.22
    def face_band(t0,t1):
        ks=[k for k in range(len(segs)) if off[k+1]>t0 and off[k]<t1]
        pts=[(FC[k],k) for k in ks if FC[k] and FC[k][1]<shh*0.55] or [([gx,gy,gh],ks[0] if ks else 0)]
        tops=[];bots=[]
        for (cx,cy,h),k in pts:
            top,bot=cy-1.0*h,cy+0.55*h
            if z[k]: ay=anc[k][1]; top,bot=ay+(top-ay)*Zf,ay+(bot-ay)*Zf
            tops.append(top); bots.append(bot)
        return min(tops),max(bots)
    def place(t0,t1,oh,default):
        ft,fb=face_band(t0,t1); m=30*sc; safe=150*sc
        if default+oh+m<=ft: return int(default)
        if ft-oh-m>=safe: return int(ft-oh-m)
        return int(min(shh-0.25*shh-oh,fb+m))   # below the chin, above the bottom UI zone
    ovy={}
    if E.get("hook"): ovy["hook"]=place(0.15,2.9,370*sc,230*sc)
    for n_,e in enumerate(events): ovy[f"card{n_}"]=place(e["t"]-0.1,e["t"]+4.2,270*sc,300*sc)
    P={"segs":segs,"off":off,"z":z,"anc":anc,"events":events,"hook":E.get("hook"),"chunks":chunks,"ovy":ovy}
    W_(f"{wd}/plan.json",P); make_cards(wd,M,P)
    # cut list for the user
    lines=[f"Original {int(dur//60)}:{dur%60:04.1f} -> edited {int(off[-1]//60)}:{off[-1]%60:04.1f}","Removed (timestamps in the original):"]
    for a,b in E.get("delete_words",[]): lines.append(f"{int(W[a]['s']//60)}:{W[a]['s']%60:05.2f}  \"{' '.join(W[i]['w'] for i in range(a,b+1))}\"")
    open(f"{wd}/cutlist.txt","w").write("\n".join(lines)+"\n")
    print(f"{len(segs)} segments, {off[-1]:.1f}s of {dur:.1f}s; {sum(1 for k in range(1,len(z)) if z[k]!=z[k-1])} zoom changes; chunks={len(chunks)}")
    print("cards at:",[(e['name'],round(e['t'],1)) for e in events],"overlay y:",ovy)
    print("KEPT TEXT:"," ".join(w["w"] for i,w in enumerate(W) if i not in DEL))

def hexrgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def make_cards(wd,M,P):
    from PIL import Image,ImageDraw,ImageFont,ImageFilter
    s=M["w"]/1080
    def shadowed(W,H,r):
        im=Image.new("RGBA",(W+40,H+40),(0,0,0,0)); shd=Image.new("RGBA",im.size,(0,0,0,0))
        ImageDraw.Draw(shd).rounded_rectangle((24,28,W+24,H+28),r,fill=(0,0,0,90)); im.alpha_composite(shd.filter(ImageFilter.GaussianBlur(12))); return im
    for n,c in enumerate(P["events"]):
        bg=hexrgb(c.get("bg","#111111")); fg=hexrgb(c.get("fg","#FFFFFF")); bg2=hexrgb(c["bg2"]) if c.get("bg2") else None
        nf=ImageFont.truetype(FONT,112 if len(c["name"])<9 else 96); tmp=ImageDraw.Draw(Image.new("RGB",(1,1)))
        W=max(820,int(300+tmp.textlength(c["name"],font=nf)+70)); H=230; im=shadowed(W,H,60)
        body=Image.new("RGBA",(W,H),bg+(255,))
        if bg2:
            g=Image.new("RGBA",(W,1))
            for x in range(W): t=x/(W-1); g.putpixel((x,0),tuple(int(bg[i]*(1-t)+bg2[i]*t) for i in range(3))+(255,))
            body=g.resize((W,H))
        mk=Image.new("L",(W,H),0); ImageDraw.Draw(mk).rounded_rectangle((0,0,W-1,H-1),60,fill=255); im.paste(body,(20,20),mk)
        d=ImageDraw.Draw(im); x0=50
        if c.get("label"):
            d.rounded_rectangle((50,55,220,225),45,fill=fg); d.text((135,140),c["label"],font=ImageFont.truetype(FONT,78),fill=bg,anchor="mm"); x0=260
        d.text((x0,140),c["name"],font=nf,fill=fg,anchor="lm")
        im.resize((int(im.width*s),int(im.height*s))).save(f"{wd}/card{n}.png")
    if P["hook"]:
        l1,l2=(P["hook"]+[""])[:2]; W,H=980,330; im=shadowed(W,H,56); d=ImageDraw.Draw(im)
        d.rounded_rectangle((20,20,W+20,H+20),56,fill=(255,255,255,245))
        d.text((W/2+20,135 if l2 else 185),l1,font=ImageFont.truetype(FONT,96 if len(l1)<18 else 80),fill=(20,20,20),anchor="mm")
        if l2: d.text((W/2+20,250),l2,font=ImageFont.truetype(FONT,84),fill=(232,44,110),anchor="mm")
        im.resize((int(im.width*s),int(im.height*s))).save(f"{wd}/hook.png")

def audio(wd):
    M=J(f"{wd}/meta.json"); P=J(f"{wd}/plan.json"); f=[]
    for k,g in enumerate(P["segs"]):
        a,b=g["s"],g["e"]; L=b-a; fd=min(0.012,L/3)
        f.append(f"[0:a]atrim=start={a:.4f}:end={b:.4f},asetpts=PTS-STARTPTS,afade=t=in:d={fd:.3f},afade=t=out:st={L-fd:.4f}:d={fd:.3f}[a{k}]")
    f.append("".join(f"[a{k}]" for k in range(len(P["segs"])))+f"concat=n={len(P['segs'])}:v=0:a=1[a]")
    open(f"{wd}/fa.txt","w").write(";".join(f))
    sh(["ffmpeg","-v","error","-y","-i",M["src"],"-filter_complex_script",f"{wd}/fa.txt","-map","[a]","-ac","1","-ar","48000",f"{wd}/cut.wav"])
    # "studio voice": rumble HPF, RNN denoise, de-box, presence, air, compression, de-ess, -14 LUFS
    CH=f"highpass=f=85:poles=2,arnndn=m={RNN}:mix=0.85,equalizer=f=250:t=q:w=1.2:g=-3,equalizer=f=3200:t=q:w=1.0:g=3.5,highshelf=f=6500:g=4,acompressor=threshold=-26dB:ratio=3:attack=8:release=120:makeup=4dB:knee=4,deesser=i=0.4"
    sh(["ffmpeg","-v","error","-y","-i",f"{wd}/cut.wav","-af",CH,f"{wd}/pre.wav"])
    t=subprocess.run(["ffmpeg","-hide_banner","-i",f"{wd}/pre.wav","-af","loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json","-f","null","-"],capture_output=True,text=True).stderr
    j=json.loads(t[t.rindex("{"):])
    LN=f"loudnorm=I=-14:TP=-1.5:LRA=7:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
    sh(["ffmpeg","-v","error","-y","-i",f"{wd}/pre.wav","-af",LN,"-ar","48000","-c:a","aac","-b:a","192k",f"{wd}/audio.m4a"]); print("audio ok")

def chunk(wd,n):
    M=J(f"{wd}/meta.json"); P=J(f"{wd}/plan.json"); i0,i1=P["chunks"][n]
    segs,off,z,anc=P["segs"],P["off"],P["z"],P["anc"]; sub=segs[i0:i1]; O=off[i0]; Dd=off[i1]-O
    VW,VH,fps=M["w"],M["h"],M["fps"]; Z=1.22; s=VW/1080
    t0=max(0,sub[0]["s"]-1); f=[]
    for k,g in enumerate(sub):
        gi=i0+k; zp=Z if (gi>0 and z[gi-1]) else 1.0; zn=Z if z[gi] else 1.0
        ax,ay=anc[gi] if z[gi] else anc[max(gi-1,0)]
        if zp==zn==1.0: zz=""
        else:
            if zp==zn: ZE=f"{zn}"
            else: X="min(t/0.7,1)"; ZE=f"({zp}+({zn-zp:.4f})*{X}*{X}*(3-2*{X}))"
            # NB: crop x/y must NOT use iw/ih (ffmpeg keeps the first frame's size); fixed-point zoom on the anchor
            zz=(f",scale=w='trunc({VW}*{ZE}/2)*2':h='trunc({VH}*{ZE}/2)*2':eval=frame:flags=bicubic"
                f",crop={VW}:{VH}:x='{ax:.1f}*({ZE}-1)':y='{ay:.1f}*({ZE}-1)'")
        f.append(f"[0:v]trim=start={g['s']-t0:.4f}:end={g['e']-t0:.4f},setpts=PTS-STARTPTS{zz},setsar=1[v{k}]")
    f.append("".join(f"[v{k}]" for k in range(len(sub)))+f"concat=n={len(sub)}:v=1:a=0[b0]")
    OV=[]
    OY=P.get("ovy",{})
    if P["hook"]: OV.append((f"{wd}/hook.png",0.15,2.9,"top",OY.get("hook")))
    for n2,e in enumerate(P["events"]): OV.append((f"{wd}/card{n2}.png",e["t"]-0.1,e["t"]+4.2,"left",OY.get(f"card{n2}")))
    inputs=[]; last="b0"; q=0
    for png,a,b,kind,oy in OV:
        if b<O or a>O+Dd: continue
        q+=1; inputs+=["-loop","1","-framerate",str(fps),"-t",f"{Dd+1:.2f}","-i",png]
        T=f"(t+{O:.4f})"; ai=0.4; ao=0.35
        if kind=="left":
            X=int(60*s); Y=oy if oy is not None else int(300*s)
            x=f"if(lt({T},{a+ai:.3f}),-w+({X}+w)*(1-pow(1-({T}-{a:.3f})/{ai},3)),if(gt({T},{b-ao:.3f}),{X}-({X}+w)*pow(({T}-{b-ao:.3f})/{ao},3),{X}))"; y=str(Y)
        else:
            Y=oy if oy is not None else int(230*s); x="(W-w)/2"
            y=f"if(lt({T},{a+ai:.3f}),-h+({Y}+h)*(1-pow(1-({T}-{a:.3f})/{ai},3)),if(gt({T},{b-ao:.3f}),{Y}-({Y}+h)*pow(({T}-{b-ao:.3f})/{ao},3),{Y}))"
        f.append(f"[{last}][{q}:v]overlay=x='{x}':y='{y}':enable='between({T},{a:.3f},{b:.3f})':eval=frame:shortest=1[o{q}]"); last=f"o{q}"
    open(f"{wd}/fv{n}.txt","w").write(";".join(f))
    nfr=sum(round((g["e"]-g["s"])*fps) for g in sub)
    sh(["ffmpeg","-y","-v","error","-ss",f"{t0:.3f}","-t",f"{sub[-1]['e']-t0+0.5:.3f}","-i",M["src"]]+inputs+["-filter_complex_script",f"{wd}/fv{n}.txt","-map",f"[{last}]","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-colorspace","bt709","-color_primaries","bt709","-color_trc","bt709","-r",str(fps),"-frames:v",str(nfr),f"{wd}/part_{n:03d}.mp4"])
    print(f"chunk {n}/{len(P['chunks'])-1} ok")

def assemble(wd,out):
    P=J(f"{wd}/plan.json"); M=J(f"{wd}/meta.json")
    with open(f"{wd}/list.txt","w") as f:
        for n in range(len(P["chunks"])): f.write(f"file 'part_{n:03d}.mp4'\n")
    sh(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",f"{wd}/list.txt","-i",f"{wd}/audio.m4a","-map","0:v","-map","1:a","-c","copy","-map_metadata","-1","-movflags","+faststart",out])
    nf=int(subprocess.run(["ffprobe","-v","error","-count_packets","-select_streams","v","-show_entries","stream=nb_read_packets","-of","csv=p=0",out],capture_output=True,text=True).stdout)
    exp=sum(round((g["e"]-g["s"])*M["fps"]) for g in P["segs"])
    print(f"assembled {out}: {nf} frames (expected {exp}) {'OK' if nf==exp else 'MISMATCH'}")

def qa(wd,out):
    P=J(f"{wd}/plan.json"); M=J(f"{wd}/meta.json"); fps=M["fps"]
    sh(["ffmpeg","-v","error","-y","-i",out,"-vn","-ac","1","-ar","16000",f"{wd}/qa.wav"])
    words,_,_=verbatim_words(f"{wd}/qa.wav"); txt=" ".join(w["w"] for w in words)
    print("FINAL TRANSCRIPT:",txt)
    left=[(round(w["s"],1),w["w"]) for w in words if w["w"].lower().strip(",.?!") in ("uh","um","umm","uhm","hmm","mm")]
    print("fillers left:",left)
    ws=[w["w"].lower().strip(",.?!") for w in words]
    print("doubled words:",[(round(words[i]["s"],1),ws[i]) for i in range(1,len(ws)) if ws[i]==ws[i-1]])
    off,z=P["off"],P["z"]; ts=[off[k]+1.5 for k in range(1,len(z)) if z[k] and not z[k-1]]
    ts+=[e["t"]+1 for e in P["events"]]+([1.5] if P["hook"] else [])
    ts=sorted(t for t in ts if t<off[-1])[:12]
    sel="+".join(f"eq(n\\,{int(t*fps)})" for t in ts)
    sh(["ffmpeg","-v","error","-y","-i",out,"-vf",f"select='{sel}',scale=200:-1,tile={len(ts)}x1","-frames:v","1",os.path.join(os.path.dirname(out),"_qa_frames.jpg")])
    print("contact sheet: _qa_frames.jpg (zoom-ins, cards, hook)")

if __name__=="__main__":
    a=sys.argv[1:]; cmd=a[0]
    if cmd=="setup": setup(a[1] if len(a)>1 else None)
    elif cmd=="transcribe": transcribe(a[1],a[2])
    elif cmd=="plan": plan(a[1])
    elif cmd=="audio": audio(a[1])
    elif cmd=="chunk": chunk(a[1],int(a[2]))
    elif cmd=="assemble": assemble(a[1],a[2])
    elif cmd=="qa": qa(a[1],a[2])
