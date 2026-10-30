import cv2, numpy as np, onnxruntime as ort, sys, subprocess, time
src,out,t0,t1=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]); model=sys.argv[5] if len(sys.argv)>5 else "rvm.onnx"
s=ort.InferenceSession(model); cap=cv2.VideoCapture(src); fps=cap.get(5); cap.set(cv2.CAP_PROP_POS_MSEC,t0*1000)
W,H=720,1280; rec=[np.zeros([1,1,1,1],np.float32)]*4; dr=np.array([0.4],np.float32)
p=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","gray","-s",f"{W}x{H}","-r",str(fps),"-i","-","-c:v","libx264","-crf","12","-pix_fmt","yuv420p",out],stdin=subprocess.PIPE)
n=int(round((t1-t0)*fps)); st=time.time()
for i in range(n):
    ok,f=cap.read()
    if not ok: break
    x=cv2.cvtColor(cv2.resize(f,(W,H)),cv2.COLOR_BGR2RGB).astype(np.float32).transpose(2,0,1)[None]/255
    fgr,pha,*rec=s.run(None,{"src":x,"r1i":rec[0],"r2i":rec[1],"r3i":rec[2],"r4i":rec[3],"downsample_ratio":dr})
    p.stdin.write((pha[0,0]*255).clip(0,255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait(); print(f"{n} frames in {time.time()-st:.1f}s")
