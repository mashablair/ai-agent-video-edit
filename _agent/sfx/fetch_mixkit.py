#!/usr/bin/env python3
"""Re-download the Mixkit sound effects listed in sfx.json (Mixkit Sound Effects Free License: free for commercial use,
social media included, no attribution; the files must not be redistributed on their own, so they are NOT in the public git
repo). Trims silence (-40 dB) and writes 48 kHz stereo WAVs to mixkit/<name>.wav.
Run: ~/vidpolish/.venv/bin/python _agent/sfx/fetch_mixkit.py"""
import json, os, subprocess, tempfile, urllib.request, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); M=json.load(open(os.path.join(HERE,"sfx.json"))); os.makedirs(os.path.join(HERE,"mixkit"),exist_ok=True)
for name,m in M.items():
    with tempfile.TemporaryDirectory() as td:
        raw=os.path.join(td,"raw.wav"); urllib.request.urlretrieve(urllib.request.Request(m["url"],headers={"User-Agent":"Mozilla/5.0"}).full_url,raw)
        x=np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",raw,"-ac","1","-ar","48000","-f","f32le","-"],capture_output=True,check=True).stdout,np.float32)
        env=np.array([np.sqrt(np.mean(x[k:k+480]**2)+1e-12) for k in range(0,len(x),480)]); on=np.where(20*np.log10(env/env.max())>-40)[0]
        a=max(0,on[0]-2)*480; b=min(len(x),(on[-1]+5)*480)
        subprocess.run(["ffmpeg","-v","error","-y","-i",raw,"-af",f"aresample=48000,atrim=start_sample={a}:end_sample={b},afade=t=out:st={max(0,(b-a)/48000-0.03)}:d=0.03",
                        "-ac","2","-map_metadata","-1",os.path.join(HERE,m["file"])],check=True)
    print(name,"ok")
