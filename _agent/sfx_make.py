#!/usr/bin/env python3
"""Sound effects for the Glorious videos, synthesized here (no downloads, no licences to track). 48 kHz mono WAVs in _agent/sfx/.
Run: ~/vidpolish/.venv/bin/python _agent/sfx_make.py"""
import numpy as np, soundfile as sf, os
SR=48000; OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"sfx"); rng=np.random.default_rng(7)
def t(d): return np.arange(int(d*SR))/SR
def norm(x,peak=0.8): return x/np.max(np.abs(x))*peak
def sweep_noise(d,f0,f1,bw=0.6,env=None):
    """Noise through a band that sweeps f0 -> f1 (frame-wise FFT mask, overlap-add)."""
    n=int(d*SR); N=2048; hop=512; x=rng.standard_normal(n+N); y=np.zeros(n+N); w=np.hanning(N); fr=np.fft.rfftfreq(N,1/SR)
    for i in range(0,n,hop):
        p=i/n; fc=f0*(f1/f0)**p; m=np.exp(-0.5*(np.log(np.maximum(fr,1)/fc)/bw)**2)
        y[i:i+N]+=np.fft.irfft(np.fft.rfft(x[i:i+N]*w)*m)*w
    y=y[:n]; return y*(env(t(d)) if env else 1)
def save(name,x): sf.write(os.path.join(OUT,name+".wav"),norm(x).astype(np.float32),SR); print(name, f"{len(x)/SR:.2f}s")
def fade(x,a=0.005,b=0.02):
    k=int(a*SR); x[:k]*=np.linspace(0,1,k); k=int(b*SR); x[-k:]*=np.linspace(1,0,k); return x
# whoosh: air passing, rises then falls in pitch and loudness (for accent words rising in, whips, B-roll jumps)
d=0.55; e=lambda s: np.sin(np.pi*np.clip(s/d,0,1))**1.6
save("whoosh",fade(sweep_noise(d,350,2600,0.5,e)+0.5*sweep_noise(d,700,5000,0.35,e)))
# soft whoosh: shorter, darker, quieter-feeling (for frequent uses: hook box in, B-roll cuts)
d=0.35; save("whoosh_soft",fade(sweep_noise(d,250,1400,0.5,lambda s: np.sin(np.pi*np.clip(s/d,0,1))**2)))
# swish: quick fast swipe (whip zooms)
d=0.22; save("swish",fade(sweep_noise(d,900,7000,0.4,lambda s:(s/d)**1.5*np.exp(-((s/d)**4)*3)*4)))
# pop: bubbly pitched blip (cards, headlines, small text popping in)
s=t(0.12); f=900*np.exp(-s*30)+400; ph=2*np.pi*np.cumsum(f)/SR
save("pop",fade(np.sin(ph)*np.exp(-s*45)+0.15*rng.standard_normal(len(s))*np.exp(-s*400),0.0005,0.01))
# click/tick: tiny UI tick (list numbers, keywords)
s=t(0.05); save("tick",fade(np.sin(2*np.pi*2400*s)*np.exp(-s*160)+0.3*rng.standard_normal(len(s))*np.exp(-s*900),0.0002,0.005))
# ding: soft bell (a punchline, "the answer")
s=t(1.6); bell=sum(a*np.sin(2*np.pi*1318*r*s)*np.exp(-s*k) for a,r,k in [(1,1,3),(0.5,2.76,6),(0.3,5.4,10),(0.2,8.9,16)])
save("ding",fade(bell*(1-np.exp(-s*900)),0.0005,0.1))
# ka-ching: drawer clack + two bright bells (money, prices, "worth it")
s=t(1.3); clack=np.concatenate([rng.standard_normal(int(0.03*SR))*np.exp(-t(0.03)*120),np.zeros(len(s)-int(0.03*SR))])
b=lambda f0,dl: np.concatenate([np.zeros(int(dl*SR)),sum(a*np.sin(2*np.pi*f0*r*t(1.3-dl))*np.exp(-t(1.3-dl)*k) for a,r,k in [(1,1,4),(0.6,2.4,7),(0.35,4.1,11),(0.25,6.3,15)])])
save("kaching",fade(0.7*clack+b(2093,0.06)+0.8*b(2637,0.16),0.0005,0.1))
# riser: quick build into a big moment (before a whip or reveal)
d=0.9; save("riser",fade(sweep_noise(d,300,6000,0.3,lambda s:(s/d)**2.2)+0.3*np.sin(2*np.pi*np.cumsum(200+600*(t(d)/d)**2)/SR)*(t(d)/d)**2))
