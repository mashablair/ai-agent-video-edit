#!/usr/bin/env python3
"""'Glorious' visuals, rendered from a B-roll Editor project file (captions.engine == "glorious").
Captions: Inter Tight Bold #FCFCFC, no outline/shadow/box, centered, <=2 lines, tight tracking/leading, each word slides
 in from the left as spoken, lead word supersized. Per-word keyword styles (word["emph"]): neg (Inter Tight Bold Italic in
 NEGATIVE mode: the letters show the inverted picture), serif (Instrument Serif Italic), script (yellow brush script),
 yellow (mustard Inter Tight Bold), num (accent Inter Tight Bold for prices, years and percents; see "numbers").
Hook text (project "hookText"): her hook sentence in a dark box in front of her for the first seconds (hookbox_png).
Accent words (project "accents" + "accentStyle"): huge Inter Tight Black words behind her head (person cut-out on top) at
 big moments through the video. An old project's single "hook" word is read as one accent (legacy_hook).
Visuals: B-roll slots with a slow push-in; slot options "headline" ("there" or "hot|COLD") and "reveal" (framed photo on a
 blurred copy that grows to full screen); project "zooms" [{a,b,z}] punch-ins on her face; project "tiles" [{a,b,num,text}].
Usage:  glorious.py numbers PROJECT.json [--dry]  -> spoken prices/years/percents become digits ("$9.5 million.") in the num style
        glorious.py plan PROJECT.json            -> pages + chunk count
        glorious.py chunk PROJECT.json WD N      -> WD/glo_N.mp4 (video only)
        glorious.py assemble PROJECT.json WD OUT -> joins chunks + the source audio
        glorious.py hookbox PROJECT.json OUT.png -> the hook text box alone (to check it by eye)
        glorious.py placehook PROJECT.json [--dry] -> puts the hook box below her chin (or above her head when there's
                                                  room) and moves the captions under it while it shows
Times are absolute; each chunk is rendered on an absolute timeline, so captions/B-roll can cross chunk edges."""
import json, os, re, sys, subprocess, math
from PIL import ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); VID=os.path.dirname(HERE)
FONTDIR=os.path.join(HERE,"fonts"); LIB=os.path.join(os.path.dirname(VID),"b-roll collection")
FONTS={"black":("GL Sans Black","GLSansBlack.ttf"),"sans":("GL Sans","GLSans.ttf"),"sansm":("GL Sans Medium","GLSansMedium.ttf"),"sansi":("GL Sans Italic","GLSansItalic.ttf"),
       "serif":("GL Serif Italic","GLSerifItalic.ttf"),"script":("GL Script","GLScript.ttf")}
WHITE="#FCFCFC"; YELLOW="#F2EC2E"; MUSTARD="#D9C933"; NUMCOL="#FFB000"
STY={"small":("sans",.068,WHITE,False),"big":("sans",.13,WHITE,False),"neg":("sansi",.12,WHITE,True),
     "serif":("serif",.14,WHITE,False),"script":("script",.15,YELLOW,False),"yellow":("sans",.12,MUSTARD,False),"num":("sans",.12,NUMCOL,False)}
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

# A quoted one-word keyword keeps its punctuation outside the quotes: comment "choose", not "choose," (Maria, 2026-11-10:
# the word in quotes is what viewers type to trigger her ManyChat automation, so it has to read exactly as typed).
QUOTED=re.compile(r'^(["“])([^"“”\s]+?)([,.!?;:]+)(["”])$')
def load(pp):
    p=json.load(open(pp)); src=os.path.join(VID,p["video"]); W,H,fps,dur=probe(src); c=p.get("captions",{}); legacy_hook(p)
    words=[w for w in p["words"] if not w.get("hide") and w.get("w") and w["s"]>=c.get("start",0)-1e-6]
    for w in words: w["w"]=QUOTED.sub(r"\1\2\4\3",w["w"])   # comment "choose", : the trigger word stays clean inside its quotes
    return dict(p=p,src=src,W=W,H=H,fps=fps,dur=dur,words=words,broll=p.get("slots",[]),zooms=p.get("zooms",[]),
                tiles=p.get("tiles",[]),cap_on=c.get("enabled",False) and c.get("engine")=="glorious",
                cap_y=c.get("y",0.635),cap_y_broll=c.get("yB",0.70),c=c,
                sizes={k:float(c.get("gSizes",{}).get(k,v[1])) for k,v in STY.items()},
                pad=float(c.get("gPad",0.06)),line=float(c.get("gLine",0.72)),
                colors={"small":c.get("color","#FCFCFC"),"big":c.get("color","#FCFCFC"),"serif":c.get("color","#FCFCFC"),
                        "script":c.get("gScriptColor",YELLOW),"yellow":c.get("gYellowColor",MUSTARD),"num":c.get("gNumColor",NUMCOL)},outline=float(c.get("gOutline",0.003)) if c.get("gOutlineOn") else 0.0,outline_c=c.get("gOutlineColor","#000000"),
                shadow=float(c.get("gShadow",0.003)),shadow_op=float(c.get("gShadowOpacity",0.5)),shadow_blur=float(c.get("gShadowBlur",0.006)),
                cap_hook=hook_caps(p))
def hook_caps(p):
    """(a, b, y): captions move to y while the hook text shows (hookText.capY, set by placehook), so they never sit on the box."""
    hb=dict(HBDEF,**(p.get("hookText") or {}))
    return (hb["a"],hb["b"],float(hb["capY"])) if hb["enabled"] and hb["text"].strip() and hb.get("capY") is not None else None

# Hook text and accent words (2026-11-10). The hook is a sentence in a box, in front of her, for the first seconds
# (project "hookText"); the big words behind her head are accents through the video (project "accents" = [{text,a,b}],
# one shared look in "accentStyle"). Projects from before keep working: their single "hook" word becomes one accent
# (a hook in the old "card" style becomes the hook text).
ACCDEF={"y":0.22,"size":0.34,"style":"neg","color":"#FFFFFF"}
HBDEF={"enabled":False,"text":"","a":0.0,"b":6.0,"style":"serif","size":0.07,"y":0.56,"box":0.74,"capY":None}
def legacy_hook(p):
    hk=p.get("hook")
    if not hk or "accents" in p: return
    on=hk.get("enabled") and hk.get("text")
    if hk.get("style")=="card":
        p["accents"]=[]
        if on and "hookText" not in p: p["hookText"]=dict(HBDEF,enabled=True,text=hk["text"],a=hk["a"],b=hk["b"],style="card",y=hk.get("y",0.6),size=hk.get("size",0.052))
    else:
        p["accents"]=[{"text":hk["text"],"a":hk["a"],"b":hk["b"]}] if on else []
        p["accentStyle"]={k:v for k,v in hk.items() if k not in ("enabled","text","a","b")}
def accents(S):
    st=S["p"].get("accentStyle") or {}
    return [dict(ACCDEF,**st,**a) for a in S["p"].get("accents",[]) if a.get("text")]
def hook_text(S):
    hb=dict(HBDEF,**(S["p"].get("hookText") or {}))
    return hb if hb["enabled"] and hb["text"].strip() else None

# Spoken numbers -> digits. Only amounts with a clear unit change; anything unsure is listed for a human to read.
UNITS={n:i for i,n in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS={n:(i+2)*10 for i,n in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES={"thousand":1000,"million":10**6,"billion":10**9}
COSTS={"for","cost","costs","costing","paid","pay","pays","price","priced","worth","spent","spend","spends","charge","charges","sold","bought","make","makes","made","earn","earns"}
def _low(w): return re.sub(r"[^a-z0-9$.,%-]","",w.lower()).rstrip(".,")
def _say(tok,i):
    """Whole number spoken in words starting at tok[i]: returns (value, next index) or None."""
    n=len(tok); val=None; k=i
    if k<n and tok[k]=="a" and k+1<n and tok[k+1] in ("hundred","thousand","million","billion"): val=1; k+=1
    elif k<n and tok[k] in TENS:
        val=TENS[tok[k]]; k+=1
        if k<n and tok[k] in UNITS and 0<UNITS[tok[k]]<10: val+=UNITS[tok[k]]; k+=1
    elif k<n and tok[k] in UNITS: val=UNITS[tok[k]]; k+=1
    if val is None: return None
    if k<n and tok[k]=="hundred":
        val*=100; k+=1
        m=k+1 if k<n and tok[k]=="and" else k
        r=_say2(tok,m)
        if r: val+=r[0]; k=r[1]
    return val,k
def _say2(tok,i):
    n=len(tok)
    if i<n and tok[i] in TENS:
        v=TENS[tok[i]]; i+=1
        if i<n and tok[i] in UNITS and 0<UNITS[tok[i]]<10: v+=UNITS[tok[i]]; i+=1
        return v,i
    if i<n and tok[i] in UNITS and tok[i]!="zero": return UNITS[tok[i]],i+1
    return None
def _amount(tok,i):
    """One amount at tok[i]: returns (value as float, scale word or None, had a $ sign, next index) or None."""
    n=len(tok); dollar=False; m=re.fullmatch(r"(\$?)(\d[\d,]*(?:\.\d+)?)",tok[i]) if i<n else None
    if m: dollar=bool(m[1]); v=float(m[2].replace(",","")); k=i+1
    else:
        r=_say(tok,i)
        if not r: return None
        v,k=float(r[0]),r[1]
    if k<n and tok[k]=="point" and k+1<n and tok[k+1] in UNITS and tok[k+1] not in TENS and UNITS[tok[k+1]]<10:
        v+=UNITS[tok[k+1]]/10; k+=2
    elif k+2<n and tok[k:k+3]==["and","a","half"] and (k+3<n and (tok[k+3] in SCALES or tok[k+3] in ("dollars","bucks"))): v+=.5; k+=3
    sc=None
    if k<n and tok[k] in SCALES: sc=tok[k]; k+=1
    return v,sc,dollar,k
def _num(v):
    return (f"{v:,.2f}".rstrip("0").rstrip(".") if v!=int(v) else f"{int(v):,}")
def _money(v,sc,sign="$"):
    if sc in ("million","billion"): return f"{sign}{v:g} {sc}"
    return sign+_num(v*(SCALES[sc] if sc else 1))
def _year(tok,i):
    """Spoken year: nineteen ninety five, twenty twenty, two thousand eight. Returns (year, next index) or None."""
    n=len(tok)
    if i+1<n and tok[i] in ("nineteen","twenty"):
        r=_say2(tok,i+1)
        if r and r[0]>=10: return (19 if tok[i]=="nineteen" else 20)*100+r[0],r[1]
    if i+2<n and tok[i]=="two" and tok[i+1]=="thousand":
        m=i+3 if tok[i+2]=="and" else i+2; r=_say2(tok,m)
        if r and r[0]<100 and not (r[1]<n and tok[r[1]] in ("dollars","bucks")): return 2000+r[0],r[1]
    return None
def numbers(pp,dry=False):
    import shutil, time
    p=json.load(open(pp)); W=p["words"]; out=[]; log=[]; left=[]; i=0
    while i<len(W):
        w=W[i]
        if w.get("hide"): out.append(w); i+=1; continue
        # a phrase can't run past a hidden word or past punctuation (the word that carries it ends the phrase)
        tok=[]; j=i
        while j<len(W) and not W[j].get("hide") and len(tok)<12:
            for part in (_low(W[j]["w"]).split("-") if not re.search(r"\d",W[j]["w"]) else [_low(W[j]["w"])]): tok.append(part)
            if re.search(r"[.?!,;:]$",W[j]["w"]): break
            j+=1
        hyph=[len(_low(x["w"]).split("-")) if not re.search(r"\d",x["w"]) else 1 for x in W[i:j+1]]
        def span(k):   # tokens used -> words used; None when it would end in the middle of a hyphenated word
            c=0
            for q,h in enumerate(hyph):
                c+=h
                if c==k: return q+1
                if c>k: return None
            return None
        text=None; used=0; emph=True
        y=_year(tok,0)
        if y: text=str(y[0]); used=y[1]
        else:
            a=_amount(tok,0)
            if a:
                v,sc,dl,k=a; nxt=tok[k] if k<len(tok) else None; prev=_low(W[i-1]["w"]) if i else ""
                # "20 and 40 million dollars": the first amount takes the second one's unit
                if sc is None and not dl and nxt in ("and","or","to") and k+1<len(tok):
                    b=_amount(tok,k+1)
                    if b and b[1] in ("million","billion"):
                        k2=b[3]; un=k2<len(tok) and tok[k2] in ("dollars","bucks"); end=k2>=len(tok)
                        if un or end or prev in COSTS:
                            text=f"${v:g} {nxt} {_money(b[0],b[1])}"; used=k2+(1 if un else 0)
                if text is None:
                    if nxt in ("dollars","dollar","bucks","buck"): text=_money(v,sc); used=k+1
                    elif nxt=="percent": text=_num(v)+"%"; used=k+1
                    elif dl: text=_money(v,sc); used=k
                    elif sc in ("million","billion") and (k>=len(tok) or prev in COSTS) and tok[0]!="a": text=_money(v,sc); used=k
                    elif sc in ("million","billion") and tok[0]!="a": left.append(f"{w['s']:.1f}s: "+" ".join(tok[:k+2])+" (a price?)")
                    elif re.fullmatch(r"(19|20)\d\d",tok[0]) and k==1: text=tok[0]; used=1
                    elif sc or (not re.search(r"\d",tok[0]) and v>=100): left.append(f"{w['s']:.1f}s: "+" ".join(tok[:k+1]))
        n=span(used) if text else None
        if text and n:
            g=W[i:i+n]; punct=re.search(r"[.?!,;:]*$",g[-1]["w"])[0]; new=text+punct
            same=(n==1 and g[0]["w"]==new)
            keep={k_:v_ for k_,v_ in g[0].items() if k_ not in ("w","s","e","emph")}
            emph_=g[0].get("emph") if same and g[0].get("emph") else "num"
            if not same or g[0].get("emph")!=emph_: log.append(f"{g[0]['s']:6.2f}s  {' '.join(x['w'] for x in g)}  ->  {new} [{emph_}]")
            out.append(dict(keep,w=new,s=g[0]["s"],e=g[-1]["e"],emph=emph_)); i+=n; continue
        out.append(w); i+=1
    print("changed:" if log else "changed: nothing"); [print(" ",x) for x in log]
    if left: print("left as spoken, read these in context:"); [print(" ",x) for x in left]
    if not dry and log:
        shutil.copy(pp,os.path.join(HERE,"tmp",f"{os.path.basename(pp)[:-5]}_before_numbers_{int(time.time())}.json"))
        p["words"]=out; json.dump(p,open(pp,"w"),indent=1)
    return out

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
    ch=S.get("cap_hook")
    if ch and page[0]["s"]<ch[1] and page[-1]["e"]>ch[0]: cy=ch[2]*H   # under the hook text box while it shows
    fit=[]
    for r in rows:   # a single word wider than the padded frame shrinks to fit
        tot=sum(wlen(w,s)[0] for w,s in r)+sp*(len(r)-1); fit.append(min(1.0,maxw/tot))
    ems=[max(em(s) for _,s in r)*k for r,k in zip(rows,fit)]
    if len(rows)==2:
        small2=all(st=='small' for _,st in rows[1]); gap=(1.12 if small2 else 0.98 if any(st=='num' for _,st in rows[1]) else 0.80)*ems[1]
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

def hook_geom(S,F,hk):
    """Size and position of an accent word (shared by the word mask and its outline/shadow)."""
    W,H=S["W"],S["H"]; lines=[x for x in re.split(r"\s*\|\s*",hk["text"]) if x]
    em=float(hk.get("size",0.34))*W; fnt=F.pil("black",em)
    wid=max(fnt.getlength(x)*(1-0.03) for x in lines); em*=min(1.0,0.94*W/wid)   # never wider than the frame
    return lines,em,float(hk.get("y",0.22))*H

def hook_ass(S,F,hk,deco=False):
    """Big accent word (was the hook word until 2026-11-10): Inter Tight Black, tight tracking, rises from below ('sunrise') and fades in, fades out at the end.
    Rendered white-on-black as a mask; the renderer fills it with the inverted picture (or a color) behind her.
    deco=True: its outline and drop shadow instead (hook.outline/outlineColor, hook.shadow/shadowBlur/shadowOpacity, fractions
    of the width like the caption ones; added 2026-11-07), drawn in color under the word, or None when both are off."""
    W,H=S["W"],S["H"]; a,b=hk["a"],hk["b"]; lines,em,y=hook_geom(S,F,hk)
    fs=F.fs("black",em); d=int((b-a)*1000); rise=0.045*H; txt="\\N".join(esc(x) for x in lines)
    def ev(layer,dx,tags,fin,fout):
        return (f"Dialogue: {layer},{ts(a)},{ts(b+0.35)},G,,0,0,0,,{{\\an5\\move({W/2+dx:.0f},{y+rise+dx:.0f},{W/2+dx:.0f},{y+dx:.0f},0,650)\\fn{FONTS['black'][0]}\\fs{fs:.0f}"
                f"\\fsp{-0.03*em:.1f}\\q2\\fscx96\\fscy96{tags}\\t(0,500,0.6,{fin}\\fscx100\\fscy100)\\t({d},{d+350},{fout})}}{txt}")
    if not deco: evs=[ev(0,0,"\\bord0\\shad0\\1c&HFFFFFF&\\alpha&HFF&","\\alpha&H00&","\\alpha&HFF&")]
    else:
        ol=float(hk.get("outline",0) or 0)*W if hk.get("outlineOn") else 0; sh=float(hk.get("shadow",0) or 0)*W if hk.get("shadowOn") else 0; evs=[]
        if sh>0:
            al=f"&H{round((1-float(hk.get('shadowOpacity',0.5)))*255):02X}&"
            evs.append(ev(0,sh,f"\\bord{ol:.1f}\\shad0\\1c&H000000&\\3c&H000000&\\blur{float(hk.get('shadowBlur',0.008))*W:.1f}\\alpha&HFF&",f"\\alpha{al}","\\alpha&HFF&"))
        if ol>0:
            evs.append(ev(1,0,f"\\bord{ol:.1f}\\shad0\\1a&HFF&\\3c{hexass(hk.get('outlineColor','#000000'))}\\3a&HFF&","\\3a&H00&","\\3a&HFF&"))
        if not evs: return None
    return (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: G,GL Sans Black,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"+"\n".join(evs)+"\n")

EMOJI_FONT="/System/Library/Fonts/Apple Color Emoji.ttc"
def _is_emoji(ch): o=ord(ch); return o>=0x1F000 or 0x2600<=o<0x27C0 or o in (0xFE0F,0x200D)
def hook_card_png(S,path,hk):
    """Hook style "card" (added 2026-10-26): her approved text card drawn IN FRONT of her (no cut-out): slim cream panel,
    square corners, 8px gold bar, burgundy Montserrat with *accent words* in Instrument Serif Italic, | = line break,
    emoji from Apple Color Emoji. hook.y = panel top, hook.size = text size (fraction of the width)."""
    from PIL import Image, ImageDraw, ImageFilter
    W,H=S["W"],S["H"]; s=W/1080; F=Fonts(FONTDIR)
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

HB_STYLE={   # regular font, accent font, accent scale, text, accent text, box colour, line height, side pad, top/bottom pad, corner radius (in em)
    "serif":("DMSerifDisplay-Regular.ttf","DMSerifDisplay-Italic.ttf",1.12,(250,240,226),(240,178,176),(38,28,24),1.18,0.36,0.2,0.26),
    "sans": ("Poppins-SemiBold.ttf","Poppins-SemiBold.ttf",1.0,(244,244,244),(240,178,176),(22,22,22),1.32,0.5,0.32,0.32)}
def hb_words(text):
    """[[(word, accent?)] per forced line]: *x* = accent (may span words), | = line break."""
    out=[]
    for ln in re.split(r"\s*\|\s*",text.strip()):
        ws=[]
        for k,part in enumerate(ln.split("*")): ws+=[(w,k%2==1) for w in part.split()]
        if ws: out.append(ws)
    return out
def hb_layout(text,style,em,maxw,wlen):
    """Lines of the hook box: each forced line wraps into as few lines as fit maxw, balanced so they come out about even
    (no long line over a lone word). wlen(word, accent?) = width. Same rules as the editor's preview."""
    lines=[]
    for ws in hb_words(text):
        L=[wlen(w,acc) for w,acc in ws]; sp=wlen(" ",False)
        def greedy(lim):
            rows=[[]]; cw=0
            for i,l in enumerate(L):
                if rows[-1] and cw+sp+l>lim: rows.append([]); cw=0
                cw+=(sp if rows[-1] else 0)+l; rows[-1].append(i)
            return rows
        n=len(greedy(maxw)); lo,hi=max(L),maxw
        for _ in range(24):
            mid=(lo+hi)/2
            if len(greedy(mid))<=n: hi=mid
            else: lo=mid
        lines+=[[ws[i] for i in r] for r in greedy(hi)]
    return lines
def hookbox_png(S,path,hb):
    """Hook text box (added 2026-11-10): her hook sentence in front of her for the first seconds, in a dark box.
    style "serif" = the thumbnail's look (DM Serif Display cream, *accent* DM Serif Italic blush 12% bigger, one rounded box
    per line joined into a stepped shape); "sans" = her older hook look (Poppins SemiBold off-white in one rounded box,
    *accent* blush); "card" = her cream text card (hook_card_png). size = text size (fraction of the width), y = centre of
    the box (fraction of the height), box = box opacity. Lines centred, at most 86% of the frame wide. The editor's preview
    (Video Editor, Hook tab) draws it with the same rules."""
    if hb.get("style")=="card": return hook_card_png(S,path,hb)
    from PIL import Image, ImageDraw, ImageFilter
    W,H=S["W"],S["H"]; st=HB_STYLE.get(hb.get("style"),HB_STYLE["serif"]); em=float(hb.get("size",0.064))*W
    efont=ImageFont.truetype(EMOJI_FONT,160)
    def fonts(em): return ImageFont.truetype(os.path.join(FONTDIR,st[0]),round(em)),ImageFont.truetype(os.path.join(FONTDIR,st[1]),round(em*st[2]))
    def runs(w):   # emoji / text runs of one word
        out=[]; buf=""; emo=None
        for ch in w:
            e=_is_emoji(ch)
            if buf and e!=emo: out.append((buf,emo)); buf=""
            buf+=ch; emo=e
        if buf: out.append((buf,emo))
        return out
    def wlen(w,acc,reg,ita): return sum(len([c for c in t if ord(c) not in (0xFE0F,0x200D)])*em*1.08 if e else (ita if acc else reg).getlength(t) for t,e in runs(w))
    for _ in range(14):   # shrink only if one word alone is wider than the frame allows
        reg,ita=fonts(em); padx=st[7]*em; maxw=0.86*W-2*padx
        lines=hb_layout(hb["text"],hb.get("style"),em,maxw,lambda w,acc:wlen(w,acc,reg,ita))
        lw=[sum(wlen(w,acc,reg,ita) for w,acc in ln)+reg.getlength(" ")*(len(ln)-1) for ln in lines]
        if max(lw)<=maxw+0.5: break
        em*=0.94
    lh=st[6]*em; pady=st[8]*em; r=st[9]*em; A,D=reg.getmetrics(); n=len(lines)
    top=float(hb.get("y",0.56))*H-(n*lh+2*pady)/2; top=max(0.05*H,min(top,0.9*H-n*lh-2*pady))
    box=Image.new("L",(W,H),0); d=ImageDraw.Draw(box)
    if hb.get("style")=="sans":
        m=max(lw); d.rounded_rectangle([W/2-m/2-padx,top,W/2+m/2+padx,top+n*lh+2*pady],radius=r,fill=255)
    else:   # stepped: one rounded box per line, joined where they meet
        rows=[(W/2-l/2-padx,top+pady+i*lh-(pady if i==0 else 0),W/2+l/2+padx,top+pady+(i+1)*lh+(pady if i==n-1 else 0)) for i,l in enumerate(lw)]
        for x0,y0,x1,y1 in rows: d.rounded_rectangle([x0,y0,x1,y1],radius=r,fill=255)
        for a,b in zip(rows,rows[1:]): d.rectangle([max(a[0],b[0]),a[3]-r,min(a[2],b[2]),b[1]+r],fill=255)
    op=float(hb.get("box",0.74)); img=Image.new("RGBA",(W,H),st[5]+(0,)); img.putalpha(box.point(lambda v:round(v*op)))
    txt=Image.new("RGBA",(W,H),(0,0,0,0)); dt=ImageDraw.Draw(txt)
    for i,(ln,l) in enumerate(zip(lines,lw)):
        x=W/2-l/2; base=top+pady+i*lh+(lh-(A+D))/2+A
        for j,(w,acc) in enumerate(ln):
            for t,e in runs(w):
                if e:
                    k=len([c for c in t if ord(c) not in (0xFE0F,0x200D)]); h=round(em*0.98)
                    g=Image.new("RGBA",(220*len(t),220),(0,0,0,0)); ImageDraw.Draw(g).text((0,0),t,font=efont,embedded_color=True)
                    g=g.crop(g.getbbox()); g=g.resize((max(1,round(g.width*h/g.height)),h),Image.LANCZOS)
                    txt.alpha_composite(g,(round(x+(k*em*1.08-g.width)/2),round(base-0.84*h))); x+=k*em*1.08
                else: f=ita if acc else reg; dt.text((x,base),t,font=f,fill=(st[4] if acc else st[3])+(255,),anchor="ls"); x+=f.getlength(t)
            x+=reg.getlength(" ")
    sh=Image.new("RGBA",(W,H),(0,0,0,0)); sh.putalpha(txt.getchannel("A").point(lambda v:round(v*0.35)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3*W/1080)),(0,round(2*W/1080))); img.alpha_composite(txt)
    img.save(path)

def zoom_at(S,t):
    """Framing scale at time t: the same maths as the zoom expression in chunk and the editor's zoomAt."""
    WH=[1.0,0.951,0.805,0.369,0.147,0.065,0.027,0.005,0.0]; chain_beats(S["zooms"]); b=v=f=1.0
    for z in S["zooms"]:
        ty=z.get("type","drift"); a_,b_=z["a"],z["b"]
        if ty in ("beat","beatwhip"):
            if not a_<=t<b_: continue
            if ty=="beat":
                e=float(z.get("ease",0.22)); fr=float(z.get("from",1.0)); u=min(max((t-a_)/max(e,0.001),0),1)
                f=fr+(float(z.get("z",1.0))-fr)*(u*u*(3-2*u) if e>0 else 1)+float(z.get("creep",0.015))*(t-a_)
            else:
                u=(t-a_)/0.1; k=min(7,int(u)); to=float(z.get("to",1.0)); f=to+(float(z.get("z",1.55))-to)*(WH[k]+(WH[k+1]-WH[k])*(u-k))
            continue
        if ty=="zoomin":
            r=float(z.get("ramp",0.7)); amp=z.get("z",1.22)-1; ss=lambda u:(lambda u:u*u*(3-2*u))(min(max(u,0),1))
            if a_<=t<b_: b+=amp*ss((t-a_)/r)
            elif b_<=t<b_+r: b+=amp*(1-ss((t-b_)/r))
            continue
        if not a_<=t<b_: continue
        if ty=="whip": u=(t-a_)/0.1; k=min(7,int(u)); v=1+(z.get("z",1.55)-1)*(WH[k]+(WH[k+1]-WH[k])*(u-k))
        elif ty=="hold": v=z.get("z",1.15)
        else: v=1+(z.get("z",1.064)-1)*pow(min(max(1-(t-a_)/max(0.2,b_-a_),0),1),1.5)
    w=sum(min(max((t-x["a"])/0.22,0),1)*(1-min(max((t-x["b"]-0.35)/0.22,0),1)) for x in accents(S))
    return b*v*(1+(f-1)*(1-w))

def face_track(S,a,b,step=0.2):
    """Her head top (with hair) and chin, as fractions of the height in the FINAL frame (zooms applied), every `step`
    seconds from a to b. Frames under B-roll are skipped (her face isn't on screen there)."""
    import cv2
    W,H=S["W"],S["H"]; q=540/W; det=cv2.FaceDetectorYN.create(os.path.join(HERE,"face_detection_yunet_2023mar.onnx"),"",(540,round(H*q)),0.6)
    ay=H*float(S["p"].get("zoomAnchor",[0.5,0.5])[1]); cap=cv2.VideoCapture(S["src"]); fps=cap.get(cv2.CAP_PROP_FPS) or S["fps"]
    cap.set(cv2.CAP_PROP_POS_FRAMES,int(a*fps)); i=int(a*fps); nxt=a; out=[]
    while i/fps<=b:
        ok=cap.grab(); t=i/fps; i+=1
        if not ok: break
        if t+1e-6<nxt or any(s["a"]<=t<s["b"] for s in S["broll"]): continue
        nxt=t+step; _,fr=cap.retrieve(); _,fs=det.detect(cv2.resize(fr,(540,round(H*q))))
        if fs is None or not len(fs): continue
        x,y,w,h=[v/q for v in max(fs,key=lambda r:r[2]*r[3])[:4]]; z=zoom_at(S,t); Y=lambda v:(ay+(v-ay)*z)/H
        out.append((round(t,2),float(Y(y-0.28*h)),float(Y(y+h))))   # YuNet's box: forehead to just under the chin; hair adds ~1/4 face height on top
    return out

HB_SAFE=(0.11,0.80)   # keep the hook box under Instagram's top bar and above its name/caption area
CAP_MAX=0.82          # lowest caption centre while the hook shows (below that Instagram's name and caption cover them)
def place_hook(pp,dry=False):
    """Put the hook text box where it covers no part of her face (Maria, 2026-11-10: it covered her chin): below her
    chin, or above her head when there's plenty of room there. Measured on the final framing (zooms included) over the
    whole time the box shows. If the captions would touch the box, they move just below it while it shows (capY), and go
    back to their usual height after. Also stores the measurements (hookText.place) so the editor re-places the box the
    same way when she switches option or changes the size."""
    P=json.load(open(pp)); S=load(pp); hb=hook_text(S)
    if not hb: print("no hook text"); return
    W,H=S["W"],S["H"]; tr=face_track(S,hb["a"],hb["b"])
    if not tr: print("no face found while the hook shows; left as is"); return
    # a detection only counts when a neighbouring sample agrees (one-frame misdetections, e.g. 1108-1 at 0.4 s, chin 0.78)
    ok=[r for k,r in enumerate(tr) if any(abs(q[2]-r[2])<0.04 and abs(q[1]-r[1])<0.06 and abs(q[0]-r[0])<0.45 for q in tr[max(0,k-2):k]+tr[k+1:k+3])] or tr
    top=min(r[1] for r in ok); chin=max(r[2] for r in ok)
    F=Fonts(FONTDIR); off=0.0   # how far a caption page reaches above its centre line (fraction of H)
    for a,b_,g in paginate(S,F):
        if g[0]["s"]<hb["b"] and g[-1]["e"]>hb["a"]:
            for w,st,x,bl,e,fsp in layout(g,dict(S,cap_y=0,cap_y_broll=0,cap_hook=None),F): off=max(off,-(bl-0.78*e)/H)
    pl={"top":round(top,4),"chin":round(chin,4),"capOff":round(off,4),"capNormal":S["cap_y"],
        "capB":S["cap_y_broll"] if any(s["a"]<hb["b"] and s["b"]>hb["a"] for s in S["broll"]) else None}
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        hookbox_png(S,os.path.join(td,"b.png"),hb); from PIL import Image
        bb=Image.open(os.path.join(td,"b.png")).getchannel("A").getbbox(); bh=(bb[3]-bb[1])/H
    y,capY,where=hook_spot(pl,bh)
    print(f"face over {len(tr)} frames: head top {top:.3f}, chin {chin:.3f}; box {bh:.3f} tall -> {where}, centre y {y:.3f}"
          +(f"; captions move to {capY:.3f} while it shows" if capY is not None else "; captions stay put"))
    if dry: return
    P.setdefault("hookText",{}).update(y=y,capY=capY,place=pl,auto=True); json.dump(P,open(pp,"w"),indent=1)

def hook_spot(pl,bh,gap=0.03):
    """(box centre y, caption y while it shows or None, "above"/"below"). Same rule as the editor's hookSpot."""
    lo,hi=HB_SAFE; free=pl["top"]-gap-lo
    if free-bh>=0.06: return round((lo+pl["top"]-gap)/2,3),None,"above her head"
    y=min(pl["chin"]+gap+bh/2,hi-bh/2,CAP_MAX-pl["capOff"]-0.02-bh/2)   # the captions must still fit under it
    where="below her chin" if y-bh/2>=pl["chin"]+0.01 else f"low as allowed (touches her chin by {pl['chin']+0.01-(y-bh/2):.3f})"
    need=y+bh/2+0.02+pl["capOff"]; norm=min(pl["capNormal"],pl["capB"] if pl.get("capB") is not None else 9)
    return round(y,3),(round(need,3) if need>norm else None),where

def accent_mask(S,hk,wd):
    """Person cut-out (Robust Video Matting) for one accent word's window, so the word sits behind her. Named by its
    times, so a chunk reuses the cut-out the chunk before it made (the work dir is emptied for every render)."""
    out=os.path.join(wd,f"accmask_{hk['a']:.3f}_{hk['b']:.3f}.mp4")
    if not os.path.exists(out):
        subprocess.run([sys.executable,os.path.join(HERE,"rvm_mask.py"),S["src"],out,str(max(0,hk["a"])),str(min(S["dur"],hk["b"]+0.4)),
                        os.path.join(HERE,"rvm_mobilenetv3_fp32.onnx")],check=True)
    return out

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
        # while an accent word shows, the framing eases back to wide (her head drops lower in the frame, so the word
        # behind it stays readable; at medium/tight framing her head covered the middle of the word): 0.22 s each way
        aw="+".join(f"(min(max((t-{x['a']:.3f})/0.22,0),1)*(1-min(max((t-{x['b']+0.35:.3f})/0.22,0),1)))" for x in accents(S) if x["a"]<t1+1 and x["b"]+0.6>t0-1)
        BE=("+".join(beats) or "0")+(f")*(1-({aw})" if aw else "")
        ZE="((1+"+("+".join(base) or "0")+")*(1+"+("+".join(terms) or "0")+")*(1+("+BE+")))"
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
    for i,hk in enumerate(accents(S)):   # big accent words behind her (person cut-out on top), each with its own cut-out
        if not (hk["a"]<t1 and hk["b"]+0.4>t0): continue
        hm=accent_mask(S,hk,wd); q=f"a{i}"
        hp=os.path.join(wd,f"glo_acc{i}.ass"); open(hp,"w").write(hook_ass(S,Fonts(FONTDIR),hk))
        dk=hook_ass(S,Fonts(FONTDIR),hk,deco=True)   # outline / drop shadow, also behind her
        inputs+=["-i",hm,"-f","lavfi","-t",f"{D+0.1:.3f}","-i",f"color=black:s={W}x{H}:r={fps}"]; pm=k; tm=k+1; k+=2
        f+=[f"[{pm}:v]fps={fps},scale={W}:{H},setsar=1,setpts=PTS-STARTPTS+{hk['a']:.6f}/TB"+(f",{zoomf}" if zoomf else "")+",format=gray"+(f",split[{q}pm][{q}pm2]" if dk else f"[{q}pm]"),
            f"[{tm}:v]setpts=PTS-STARTPTS+{t0:.6f}/TB,subtitles=filename={fesc(hp)}:fontsdir={fesc(FONTDIR)},format=gray[{q}tm]",
            f"[{q}tm][{q}pm]blend=all_expr='A*(255-B)/255',format=gray[{q}hm]",
            f"[{last}]split[{q}b0][{q}v]"]
        if dk:
            dp=os.path.join(wd,f"glo_acc{i}deco.ass"); open(dp,"w").write(dk)
            inputs+=["-f","lavfi","-t",f"{D+0.1:.3f}","-i",f"color=black@0.0:s={W}x{H}:r={fps},format=rgba"]; dm=k; k+=1
            f+=[f"[{dm}:v]setpts=PTS-STARTPTS+{t0:.6f}/TB,subtitles=filename={fesc(dp)}:fontsdir={fesc(FONTDIR)}:alpha=1,format=rgba,split[{q}dc][{q}da]",
                f"[{q}da]alphaextract[{q}dal]",f"[{q}dal][{q}pm2]blend=all_expr='A*(255-B)/255'[{q}dam]",f"[{q}dc][{q}dam]alphamerge[{q}dw]",
                f"[{q}b0][{q}dw]overlay=eof_action=pass:shortest=0[{q}b]"]
        else: f.append(f"[{q}b0]null[{q}b]")
        if hk.get("style","neg")=="neg": f.append(f"[{q}v]negate[{q}f]")
        else: f.append(f"[{q}v]drawbox=c={'#FCFCFC' if hk.get('style')=='white' else hk.get('color','#FFFFFF')}:t=fill[{q}f]")
        f+=[f"[{q}f][{q}hm]alphamerge[{q}w]",f"[{q}b][{q}w]overlay=eof_action=pass:shortest=0[{q}o]"]; last=f"{q}o"
    hb=hook_text(S)
    if hb and hb["a"]<t1 and hb["b"]>t0:   # hook text box in front of her, fades in (unless it starts the video) and out by b
        cp=os.path.join(wd,"hookbox.png"); hookbox_png(S,cp,hb); a_,b_=hb["a"],hb["b"]
        inputs+=["-loop","1","-framerate",str(fps),"-t",f"{D+0.1:.3f}","-i",cp]
        fin=f",fade=t=in:st={a_:.3f}:d=0.25:alpha=1" if a_>0.01 else ""
        f+=[f"[{k}:v]format=rgba,setpts=PTS-STARTPTS+{t0:.6f}/TB{fin},fade=t=out:st={b_-0.3:.3f}:d=0.3:alpha=1[hbox]",
            f"[{last}][hbox]overlay=enable='between(t,{a_:.3f},{b_:.3f})':eof_action=pass[hbo]"]; last="hbo"; k+=1
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

def sheet(pp,video,out):
    """Contact sheet for checking a render by eye: the hook text, every accent word, the middle of every B-roll slot, every card, and her face across the video (time on each frame)."""
    p=json.load(open(pp)); legacy_hook(p); d=p.get("duration") or float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",video],capture_output=True,text=True).stdout)
    sp=float(p.get("speed",1.0) or 1.0)
    ts={0.6}|{round((s["a"]+s["b"])/2,2) for s in p.get("slots",[])}|{round(t["a"]+1.2,2) for t in p.get("tiles",[])}|{round(a["a"]+0.8,2) for a in p.get("accents",[])}|{round(d*f,2) for f in (0.2,0.45,0.7,0.95)}
    ts=sorted(t for t in ts if t<d)[:40]; tmp=out+"_f"; os.makedirs(tmp,exist_ok=True)
    for i,t in enumerate(ts):
        subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{t/sp:.2f}","-i",video,"-frames:v","1","-vf",f"scale=216:-1,drawtext=text='{t}':x=5:y=5:fontsize=20:fontcolor=yellow",f"{tmp}/f_{i:02d}.jpg"])
    subprocess.run(["ffmpeg","-v","error","-y","-pattern_type","glob","-i",f"{tmp}/f_*.jpg","-vf",f"tile=10x{(len(ts)+9)//10}","-frames:v","1",out])
    for f in os.listdir(tmp): os.remove(f"{tmp}/{f}")
    os.rmdir(tmp); print("contact sheet:",out,f"({len(ts)} frames)")

if __name__=="__main__":
    cmd,pp=sys.argv[1],sys.argv[2]
    if cmd=="numbers": numbers(pp,"--dry" in sys.argv)
    elif cmd=="plan":
        S=load(pp)
        for a,b,g in paginate(S,Fonts(FONTDIR)): print(f"{a:6.2f} "+" ".join(w["w"]+("["+w["emph"]+"]" if w.get("emph") else "") for w in g))
        print("chunks",len(spans(S)))
    elif cmd=="chunk": chunk(pp,sys.argv[3],int(sys.argv[4]))
    elif cmd=="hookbox":   # glorious.py hookbox PROJECT OUT.png: the hook text box alone, for checking by eye
        S=load(pp); hb=hook_text(S); hookbox_png(S,sys.argv[3],hb) if hb else print("no hook text in this project")
    elif cmd=="placehook": place_hook(pp,"--dry" in sys.argv)
    elif cmd=="autozoom":   # plan the zooms (approved Oct 21: Captions-style framing changes every ~1.5s + whips)
        autozoom(pp)
    elif cmd=="anchors":   # fill missing face anchors (fractions) for zooms
        S=load(pp); p=S["p"]
        for z in p.get("zooms",[]):
            if "ax" not in z: x,y=face_at(S,z["a"]+0.05); z["ax"]=round(x/S["W"],4); z["ay"]=round(y/S["H"],4)
        json.dump(p,open(pp,"w"),indent=1); print("anchors set for",len(p.get("zooms",[])),"zooms")
    elif cmd=="assemble": assemble(pp,sys.argv[3],sys.argv[4])
    elif cmd=="sheet": sheet(pp,sys.argv[3],sys.argv[4])
