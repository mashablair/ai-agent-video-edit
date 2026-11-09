#!/usr/bin/env python3
"""Put a thumbnail in front of a finished video as its first frame (for FB, YouTube and TikTok, where the cover must be picked from the video).
usage: cover.py VIDEO IMAGE [--frames N]      (N = how many frames the thumbnail holds; default 1 = 1/30 s, invisible to viewers)
  Writes VIDEO_cover.mp4 next to it (then _cover_v2, ...; never overwrites). No re-render: the thumbnail becomes a tiny
  segment encoded with glorious.py's exact settings and is joined in front by stream copy, the way glorious.py joins its
  chunks. Audio is delayed by the same N frames. Checks: frame count, a clean decode, and every original frame identical."""
import sys, os, json, re, subprocess, tempfile, shutil
def sh(c): return subprocess.run(c,check=True,capture_output=True,text=True)
def probe(v):
    o=json.loads(sh(["ffprobe","-v","error","-show_streams","-of","json",v]).stdout)["streams"]
    vs=[s for s in o if s["codec_type"]=="video"][0]; a=[s for s in o if s["codec_type"]=="audio"]
    n,d=map(int,vs["r_frame_rate"].split("/")); return vs,(a[0] if a else None),n/d
def frames(v): return int(sh(["ffprobe","-v","error","-count_packets","-select_streams","v","-show_entries","stream=nb_read_packets","-of","csv=p=0",v]).stdout)
def outname(v):
    b=v[:-4]+"_cover"; p=b+".mp4"; k=2
    while os.path.exists(p): p=f"{b}_v{k}.mp4"; k+=1
    return p

def cover(video,image,nf=1):
    vs,au,fps=probe(video); w,h=vs["width"],vs["height"]; out=outname(video); td=tempfile.mkdtemp(prefix="cover_")
    if vs["codec_name"]!="h264": sys.exit("expects an H.264 video (our renders are)")
    # 1. the thumbnail as an N-frame segment, encoded exactly like glorious.py's chunks
    sh(["ffmpeg","-y","-v","error","-loop","1","-i",image,"-vf",f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},scale=out_range=tv,setsar=1",
        "-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-color_range","tv",   # a JPEG is full range; tagged so, it would retag the whole video
        "-r",str(round(fps)),"-frames:v",str(nf),
        "-colorspace","bt709","-color_primaries","bt709","-color_trc","bt709",f"{td}/c.mp4"])
    # 2. join the video streams without re-encoding, then add the audio delayed by N frames
    sh(["ffmpeg","-y","-v","error","-i",video,"-map","0:v","-c","copy",f"{td}/v.mp4"])
    open(f"{td}/l.txt","w").write(f"file '{td}/c.mp4'\nfile '{td}/v.mp4'\n")
    sh(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",f"{td}/l.txt","-c","copy",f"{td}/cat.mp4"])
    am=[]
    if au: am=["-i",video,"-map","1:a","-af",f"adelay={nf/fps*1000:.3f}:all=1","-c:a","aac","-b:a","192k","-ar",au["sample_rate"]]
    sh(["ffmpeg","-y","-v","error","-i",f"{td}/cat.mp4"]+am+["-map","0:v","-c:v","copy","-map_metadata","-1","-movflags","+faststart",out])
    # 3. checks
    n0,n1=frames(video),frames(out)
    err=subprocess.run(["ffmpeg","-v","error","-i",out,"-f","null","-"],capture_output=True,text=True).stderr.strip()
    rng=sh(["ffprobe","-v","error","-select_streams","v","-show_entries","stream=color_range","-of","csv=p=0",out]).stdout.strip()
    if rng!=vs.get("color_range","tv"): err+=f" color range {rng} (source {vs.get('color_range')})"
    ps=sh(["ffmpeg","-v","info","-i",out,"-i",video,"-filter_complex",f"[0:v]trim=start_frame={nf},setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]psnr","-f","null","-"]).stderr
    same=re.search(r"PSNR .*average:(\S+)",ps)
    shutil.rmtree(td)
    ok=n1==n0+nf and not err and same and same.group(1)=="inf"
    print(f"{out}\n  frames {n1} = {n0} + {nf} cover: {'OK' if n1==n0+nf else 'MISMATCH'}; decode errors: {err[:200] or 'none'}; original frames identical: {'yes' if same and same.group(1)=='inf' else 'NO ('+(same.group(1) if same else '?')+' dB)'}")
    if not ok: sys.exit("check failed: don't deliver this file")
    return out

if __name__=="__main__":
    a=[x for x in sys.argv[1:] if not x.startswith("--")]; nf=1
    for x in sys.argv[1:]:
        if x.startswith("--frames"): nf=int(x.split("=")[1]) if "=" in x else int(sys.argv[sys.argv.index(x)+1])
    if "--frames" in sys.argv: a=[x for x in a if x!=str(nf)]
    cover(a[0],a[1],nf)
