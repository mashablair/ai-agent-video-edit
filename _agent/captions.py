# Burns styled word captions (from a B-roll Editor project) into a video. Matches the editor preview.
# Usage:
#   python3 captions.py chunks  <project.json> <in.mp4>            -> prints number of render chunks
#   python3 captions.py chunk   <project.json> <in.mp4> <wd> <i>   -> renders wd/cap_<i>.mp4 (video only)
#   python3 captions.py assemble <project.json> <in.mp4> <wd> <out.mp4>  -> joins chunks + original audio
#   python3 captions.py ass     <project.json> <in.mp4> <out.ass>  -> just writes the subtitle file (for checking)
# Fonts and fonts.json live in ./fonts next to this script. Caption sizes are fractions of video width.
import json, os, re, subprocess, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
FONTDIR = os.path.join(HERE, "fonts")
FONTS = {f["key"]: f for f in json.load(open(os.path.join(FONTDIR, "fonts.json")))}
DEFAULT = {"enabled": False, "font": "montserrat-xb", "size": 0.078, "words": 3, "upper": True, "nopunct": True,
           "color": "#FFFFFF", "hlMode": "color", "hl": "#FFD23F", "outline": 0.0065, "outlineColor": "#000000",
           "shadow": 0.004, "shadowOpacity": 0.45, "box": False, "boxColor": "#FFFFFF", "boxOpacity": 1.0, "boxPad": 0.012,
           "pop": True, "x": 0.5, "y": 0.66, "width": 0.84, "start": 0.0}
PUNCT = re.compile(r"[.,!?;:]$")

def cfg_of(p):
    c = dict(DEFAULT); c.update(p.get("captions") or {}); return c

def word_text(w, c):
    t = w.get("w", "")
    if c["nopunct"]: t = re.sub(r"(?!(?<=\d)[.,]\d)[.,!?;:\"“”]+", "", t).strip()
    if c["upper"]: t = t.upper()
    return t

def chunks(words, c):
    """Same rules as the editor: break on max words, end punctuation, or a pause > 0.6s."""
    ws = [w for w in words if not w.get("hide") and w["s"] >= c["start"] - 1e-6 and word_text(w, c)]
    out, cur = [], []
    for w in ws:
        if cur and (len(cur) >= int(c["words"]) or w["s"] - cur[-1]["e"] > 0.6 or PUNCT.search(cur[-1]["w"])):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    res = []
    for i, ch in enumerate(out):
        a = ch[0]["s"]; nxt = out[i + 1][0]["s"] if i + 1 < len(out) else None
        b = ch[-1]["e"] + 0.3
        if nxt is not None and (nxt - ch[-1]["e"] < 0.3 or b > nxt): b = nxt
        res.append({"a": a, "b": b, "words": ch})
    return res

def ass_color(hexc, opacity=1.0):
    h = hexc.lstrip("#"); r, g, b = h[0:2], h[2:4], h[4:6]
    a = max(0, min(255, round((1 - opacity) * 255)))
    return f"&H{a:02X}{b}{g}{r}".upper()

def ts(t):
    t = max(0, t); cs = int(round(t * 100)); h = cs // 360000; m = cs // 6000 % 60; s = cs // 100 % 60
    return f"{h}:{m:02d}:{s:02d}.{cs % 100:02d}"

def esc(t): return t.replace("\\", "").replace("{", "(").replace("}", ")")

def build_ass(p, W, H, offset=0.0, until=None):
    c = cfg_of(p); f = FONTS.get(c["font"], FONTS["montserrat-xb"])
    px = c["size"] * W; fs = px * f["k"]                       # libass sizes by (winAscent+winDescent)
    margin = round((1 - c["width"]) / 2 * W)
    if c["box"]:
        border, outline_c, bord, shad, back = 3, ass_color(c["boxColor"], c["boxOpacity"]), c["boxPad"] * W, 0, "&H00000000"
    else:
        border, outline_c, bord = 1, ass_color(c["outlineColor"]), c["outline"] * W
        shad, back = c["shadow"] * W, ass_color("#000000", c["shadowOpacity"])
    base, hl = ass_color(c["color"]), ass_color(c["hl"])
    L = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0",
         "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "", "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
         f"Style: Cap,{f['ass']},{fs:.2f},{base},&H000000FF,{outline_c},{back},0,{-1 if f['italic'] else 0},0,0,100,100,0,0,{border},{bord:.2f},{shad:.2f},5,{margin},{margin},0,1",
         "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    pos = f"\\an5\\pos({c['x'] * W:.1f},{c['y'] * H:.1f})"
    for ch in chunks(p["words"], c):
        ws = ch["words"]
        for k, w in enumerate(ws):
            a = ch["a"] if k == 0 else w["s"]; b = ch["b"] if k == len(ws) - 1 else ws[k + 1]["s"]
            if until is not None and a >= until: continue
            if b <= offset: continue
            parts = []
            for j, x in enumerate(ws):
                t = esc(word_text(x, c))
                if j == k and c["hlMode"] != "none":
                    on = "\\c" + hl
                    if c["hlMode"] == "grow": on += "\\fscx115\\fscy115"
                    off = "\\c" + base + ("\\fscx100\\fscy100" if c["hlMode"] == "grow" else "")
                    t = "{" + on + "}" + t + "{" + off + "}"
                parts.append(t)
            pop = "\\fscx85\\fscy85\\t(0,90,\\fscx100\\fscy100)" if (c["pop"] and k == 0) else ""
            L.append(f"Dialogue: 0,{ts(a - offset)},{ts(b - offset)},Cap,,0,0,0,,{{{pos}{pop}}}" + " ".join(parts))
    return "\n".join(L) + "\n"

def info(src):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_format", "-of", "json", src], capture_output=True, text=True).stdout)
    s = o["streams"][0]; w, h = s["width"], s["height"]
    for sd in s.get("side_data_list", []) or []:
        if abs(int(sd.get("rotation", 0))) == 90: w, h = h, w
    n, d = map(int, s["r_frame_rate"].split("/")); return w, h, round(n / d), float(o["format"]["duration"])

def spans(dur, size=18.0):
    k = max(1, math.ceil(dur / size)); e = [round(dur * i / k, 3) for i in range(k + 1)]; return list(zip(e[:-1], e[1:]))

def fesc(path): return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,").replace("[", "\\[").replace("]", "\\]")

def render_chunk(p, src, wd, n):
    W, H, fps, dur = info(src); a0, b0 = spans(dur)[n]
    ass = os.path.join(wd, f"cap_{n}.ass"); open(ass, "w").write(build_ass(p, W, H, offset=a0, until=b0))
    vf = f"setpts=PTS-STARTPTS,ass=filename={fesc(ass)}:fontsdir={fesc(FONTDIR)},format=yuv420p"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a0), "-t", str(b0 - a0), "-i", src, "-vf", vf, "-an",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
                    "-frames:v", str(round((b0 - a0) * fps)), "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                    os.path.join(wd, f"cap_{n}.mp4")], check=True)
    print(f"caption chunk {n}/{len(spans(dur)) - 1} ok")

def assemble(src, wd, out):
    dur = info(src)[3]; N = len(spans(dur))
    lst = os.path.join(wd, "capl.txt"); open(lst, "w").write("".join(f"file 'cap_{n}.mp4'\n" for n in range(N)))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", src, "-map", "0:v", "-map", "1:a",
                    "-c", "copy", "-map_metadata", "-1", "-movflags", "+faststart", "-shortest", out], check=True)
    print("assembled", out, "chunks", N)

if __name__ == "__main__":
    a = sys.argv[1:]; p = json.load(open(a[1])); src = a[2]
    if a[0] == "chunks": W, H, fps, dur = info(src); print(len(spans(dur)), "chunks", W, H, fps, dur)
    elif a[0] == "ass": W, H, _, _ = info(src); open(a[3], "w").write(build_ass(p, W, H)); print("wrote", a[3])
    elif a[0] == "chunk": render_chunk(p, src, a[3], int(a[4]))
    elif a[0] == "assemble": assemble(src, a[3], a[4])
