#!/usr/bin/env python3
"""Render what Maria saved in the Video Editor, in one command:  render_edits.py NAME [--dry]

1. Cuts changed (cut project keep != renderedKeep)? Re-render the clean video from the raw take
   (polish.py fromcut/plan/audio/chunk/assemble/qa), deliver Videos/NAME/NAME_clean_vN.mp4 and refresh the cut project.
   The visuals were already moved to the new cut by the editor (broll project "cutKeep"); polish.py remap only
   moves them when they still sit on the old cut (e.g. after an edit in the old Cut Editor).
2. Render the Glorious video (glorious.py plan/chunk/assemble) and deliver Videos/NAME/NAME_glorious_vN.mp4.
3. Superseded versions go to _agent/tmp/superseded/, the usage-log line in CATALOG.md is refreshed, and a contact
   sheet (one frame per B-roll slot plus a few on her face) is written to the work dir for checking.
Work dirs: ~/vp/NAME_cut and ~/vp/NAME_g, one per video, emptied at the start of each render (no stale chunks or hook masks)."""
import sys, os, json, re, glob, shutil, subprocess, time, datetime
HOME=os.path.expanduser("~"); AG=os.path.dirname(os.path.abspath(__file__)); VID=os.path.dirname(AG)
PY=f"{HOME}/vidpolish/.venv/bin/python"; POL=f"{AG}/polish.py"; GLO=f"{AG}/glorious.py"
CAT=f"{HOME}/Desktop/b-roll collection/_catalog/CATALOG.md"
def J(p): return json.load(open(p))
def run(*a,quiet=False):
    r=subprocess.run([PY,*a],cwd=VID,capture_output=True,text=True)
    if r.returncode: sys.exit(f"FAILED: {' '.join(a[:3])}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    if not quiet: print(r.stdout.rstrip())
    return r.stdout
def same(a,b): return bool(a) and bool(b) and len(a)==len(b) and all(abs(x-y)<5e-4 for o,n in zip(a,b) for x,y in zip(o,n))
def nextv(d,stem):   # NAME_clean.mp4 -> NAME_clean_v2.mp4 -> _v3 ...
    n=1
    for f in glob.glob(f"{d}/{stem}*.mp4"):
        m=re.fullmatch(re.escape(stem)+r"(?:_v(\d+))?\.mp4",os.path.basename(f))
        if m: n=max(n,int(m.group(1) or 1))
    return f"{d}/{stem}_v{n+1}.mp4" if glob.glob(f"{d}/{stem}*.mp4") else f"{d}/{stem}.mp4"
def retire(path):
    if path and os.path.isfile(path):
        os.makedirs(f"{AG}/tmp/superseded",exist_ok=True); dst=f"{AG}/tmp/superseded/{os.path.basename(path)}"
        if os.path.exists(dst): dst=dst[:-4]+f"_{int(time.time())}.mp4"
        shutil.move(path,dst); print("  moved the old version to",os.path.relpath(dst,VID))
def fresh(wd):   # the same folder every time (was timestamped and piled up in ~/vp), emptied so nothing stale is reused
    shutil.rmtree(wd,ignore_errors=True); os.makedirs(wd); return wd

def main(name,dry=False):
    D=f"{VID}/Videos/{name}"; ED=f"{D}/editor files"; CP=f"{ED}/{name}_cut_project.json"; BP=f"{ED}/{name}_broll_project.json"
    C=J(CP); B=J(BP)
    cut_changed=not same(C["keep"],C.get("renderedKeep"))
    print(f"{name}: cuts {'CHANGED' if cut_changed else 'unchanged'} ({sum(b-a for a,b in C['keep']):.2f}s vs rendered {sum(b-a for a,b in C.get('renderedKeep') or []):.2f}s); visuals status {B.get('status')}")
    if dry: return
    if cut_changed:
        raw=os.path.join(VID,C["src"])
        if not os.path.isfile(raw): sys.exit(f"The raw video {C['src']} is gone, so the cut changes can't be rendered. Ask Maria to put it back.")
        wd=fresh(f"{HOME}/vp/{name}_cut")
        print("== cuts ==")
        json.dump(C.get("renderedKeep") or [],open(f"{wd}/oldkeep.json","w"))   # for capsync: which joins are new
        run(POL,"fromcut",CP,wd); run(POL,"plan",wd,quiet=True); run(POL,"audio",wd,quiet=True)
        n=len(J(f"{wd}/plan.json")["chunks"])
        for k in range(n): run(POL,"chunk",wd,str(k),quiet=True)
        out=run(POL,"assemble",wd,f"{wd}/final.mp4")
        if "MISMATCH" in out: sys.exit("clean video frame count mismatch")
        qa=run(POL,"qa",wd,f"{wd}/final.mp4",quiet=True)
        for l in qa.splitlines():
            if l.startswith(("fillers left","doubled words")): print(" ",l)
        new=nextv(D,f"{name}_clean"); old=os.path.join(VID,B["video"]) if B.get("video") else None
        shutil.copy(f"{wd}/final.mp4",new); print("  delivered",os.path.relpath(new,VID))
        run(POL,"remap",CP,BP)   # no-op when the editor already moved the visuals
        run(POL,"cutproject",wd,name,os.path.relpath(new,VID),quiet=True)
        B=J(BP); C=J(CP); B["video"]=os.path.relpath(new,VID); B["cutKeep"]=C["keep"]; B["duration"]=round(sum(b-a for a,b in C["keep"]),3)
        json.dump(B,open(BP,"w"),indent=1)
        print(" ",run(POL,"capsync",BP,new,f"{wd}/oldkeep.json",quiet=True).strip().splitlines()[-1])   # listen: caption words at the new joins
        if old!=new: retire(old)
    print("== visuals ==")
    wd=fresh(f"{HOME}/vp/{name}_g")
    pl=run(GLO,"plan",BP,quiet=True); n=int(re.findall(r"chunks (\d+)",pl)[-1])
    for k in range(n): run(GLO,"chunk",BP,wd,str(k),quiet=True)
    out=run(GLO,"assemble",BP,wd,f"{wd}/final.mp4")
    m=re.search(r"frames (\d+) expected (\d+)",out)
    if not m or m.group(1)!=m.group(2): sys.exit("glorious frame count mismatch")
    B=J(BP); new=nextv(D,f"{name}_glorious"); old=os.path.join(VID,B["rendered"]) if B.get("rendered") else None
    shutil.copy(f"{wd}/final.mp4",new); print("  delivered",os.path.relpath(new,VID))
    B["status"]="rendered"; B["rendered"]=os.path.relpath(new,VID); json.dump(B,open(BP,"w"),indent=1)
    C=J(CP)
    if C.get("status")=="edited" and same(C["keep"],C.get("renderedKeep")): C["status"]="rendered"; json.dump(C,open(CP,"w"))
    if old and old!=new: retire(old)
    # usage log: replace this video's line, keep its topic
    if os.path.isfile(CAT):
        L=open(CAT).read().rstrip("\n").split("\n"); clips=", ".join(s["clip"] for s in sorted(B["slots"],key=lambda s:s["a"]))
        stem=os.path.basename(B["video"])[:-4]; pat=re.compile(rf"^- (\d{{4}}-\d\d-\d\d), {re.escape(name)}(_clean\S*)? (\(.*?\)):")
        for i in range(len(L)-1,-1,-1):
            mm=pat.match(L[i])
            if mm: L[i]=f"- {mm.group(1)}, {stem} {mm.group(3)}: {clips}"; break
        else: L.append(f"- {datetime.date.today()}, {stem} (Glorious): {clips}")
        open(CAT,"w").write("\n".join(L)+"\n")
    # contact sheet for checking by eye
    run(GLO,"sheet",BP,new,f"{wd}/sheet.jpg")

if __name__=="__main__":
    a=[x for x in sys.argv[1:] if not x.startswith("--")]
    main(a[0],"--dry" in sys.argv)
