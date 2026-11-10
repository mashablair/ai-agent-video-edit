# VIDEO_EDITING_HANDOFF.md
**Automated short-form video editing for Glorious Goddess (GG) / MariaTalksTech (MTT)**
Technical handoff from Claude to ChatGPT Work / Codex. Prepared 2026-10-24.

---

## 0. Read this first

### What this report is based on
Everything below comes from **our actual work**, recovered from:
- **5 past Claude chats** (2026-10-07 → 2026-10-23): "Video editing for dating rambles", "Video script and B-roll workflow", "Add B-roll to video", "B-roll for video edit", "Video editing interface for B-roll", "Talking head video editing", plus the Mic Drop caption session.
- **4 saved Claude skills** (written instructions that encode every approved rule): `polish-talking-video`, `glorious-visuals`, `add-broll-to-video`, `update-broll-library`.
- **The scripts, configs, logs and backups on Maria's Mac**, read directly on 2026-10-24:
  - `~/Desktop/AI agent video edit/`
  - `~/Desktop/b-roll collection/`

Nothing in sections 1–5 is general internet advice. Section 6 is clearly marked where it goes beyond what we tested.

### Legend used throughout
| Mark | Meaning |
|---|---|
| ✅ **TESTED – KEPT** | Used on Maria's real videos and is part of the current working pipeline |
| ⚠️ **TESTED – DISAPPOINTED / REJECTED** | We tried it and it failed, produced bad output, or Maria rejected the result |
| 🔍 **LOOKED AT – NOT TESTED** | Researched, installed or probed, but never produced output with it |
| 💡 **NEW RECOMMENDATION – UNTESTED** | Claude's recommendation for the concert project; never run in our workflow |

### ⚠️ Critical environment fact (read before reusing any code)
All of our processing ran on Maria's MacBook Pro (Apple Silicon), **but inside a sandboxed Linux VM** that the Claude desktop app provides. It did **not** run natively on macOS.
- OS: Ubuntu 22.04, **aarch64**
- Software: **ffmpeg 4.4.2** (Ubuntu build with libass, libzimg, librubberband and libx264), Python 3.10.12
- Shell cap: each shell call was capped at **180 seconds**, and background processes were killed when a call ended. **That is why every renderer works in ~18–35 s "chunks" and has a separate `assemble` step.** Codex running natively may not need chunking, but the chunk design is proven and keeps renders resumable.
- Folders appeared at `$HOME/mnt/<folder name>` inside the VM. Native paths are `/Users/mariablair/Desktop/<folder name>`. Some scripts derive paths relative to their own location, so they are portable. Saved JSON project files contain old absolute VM paths (`/sessions/...`) in a few places.
- **The saved Python wheels in `_tools/wheels/` are Linux aarch64 and will NOT install on native macOS.** The model files are portable:
  - Parakeet ONNX
  - `sh.rnnn`
  - RVM ONNX
  - fonts
- Network inside the VM: GitHub, PyPI and npm were reachable. **Hugging Face was blocked.** This decided our speech-model choice (see §1).

---

## 1. Tools we experimented with

### 1a. Core media tools
| Tool | Status | What we used it for |
|---|---|---|
| **ffmpeg / ffprobe 4.4.2** | ✅ TESTED – KEPT | Everything: trimming, concat, filter graphs (`-filter_complex_script`), scale/crop zooms, overlays, libass subtitles, audio chain, loudnorm, tone-mapping, contact sheets (`tile`), silence detection (`silencedetect`), frame counting |
| **libx264** (CRF 18, preset medium, yuv420p, BT.709 tags) | ✅ TESTED – KEPT | All final renders. Library clips use CRF 19. |
| **libass via ffmpeg `ass=` / `subtitles=` filters** | ✅ TESTED – KEPT | All captions, hook word, headlines, list cards. Animation uses ASS `\move`, `\t`, `\alpha`, `\fscx/\fscy`, `\blur` and vector drawing `\p1`. |
| **ffmpeg `arnndn` + RNNoise model `sh.rnnn`** (GregorR/rnnoise-models "somnolent-hogwash") | ✅ TESTED – KEPT | Noise reduction inside the "studio voice" chain (car noise) |
| **ffmpeg `loudnorm`, two-pass, linear** | ✅ TESTED – KEPT | -14 LUFS, TP -1.5, LRA 7 |
| **ffmpeg `zscale` + `tonemap=hable`** | ✅ TESTED – KEPT | iPhone HDR (HLG / PQ) → SDR BT.709 for B-roll clips |
| **ffmpeg `zoompan`** | ✅ TESTED – KEPT | 3.5 s slow push-in on still photos (library build only) |
| **ffmpeg `atempo` / `setpts`** | ✅ TESTED – KEPT (optional) | Speed-up with natural pitch, only when Maria picks 1.1–1.3× in the editor |
| **ffmpeg `cropdetect`** | ✅ TESTED – KEPT | Remove letterbox bars and watermarks from short AI clips going into the library |

### 1b. Speech recognition (transcription)
| Tool | Status | Notes |
|---|---|---|
| **sherpa-onnx 1.13.8 + NVIDIA NeMo Parakeet TDT 0.6B v2 (int8 ONNX)** — model `sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` | ✅ TESTED – KEPT | Our only production ASR. Downloaded from GitHub release `k2-fsa/sherpa-onnx` → `asr-models`. Gives token timestamps that we merge into words. **It transcribes "uh/um" and repeated words, but only when decoded phrase by phrase** (see §3). Runs on CPU with `num_threads=4`. English only. |
| **faster-whisper** | 🔍 INSTALLED – NEVER RAN | `pip install faster-whisper` succeeded on day 1. Model download from Hugging Face (`Systran/faster-whisper-small.en`) was **blocked**, so it never transcribed anything. **No quality verdict.** |
| **whisper-timestamped, OpenAI Whisper, whisper.cpp ggml models, Vosk** | 🔍 PROBED ONLY | Checked whether downloads were reachable (OpenAI blob storage, alphacephei, npm, GitHub search). Picked Parakeet because it was on GitHub and reachable. **Never tested for quality.** |
| **Whisper-family models inside sherpa-onnx** (whisper-tiny/base/small.en) | 🔍 LISTED – NOT TESTED | Seen in the same GitHub release; not used |

### 1c. Computer vision / ML
| Tool | Status | Notes |
|---|---|---|
| **OpenCV (`opencv-python-headless<5`)** Haar cascades (frontal + profile face) | ✅ TESTED – KEPT | Used for: face-anchored zooms (legacy cleanup step), placing hook/cards so they never cover her face, `face_at()` in the visuals renderer. **Pin `<5`**: a newer wheel lacked `CascadeClassifier` (see §3). |
| **OpenCV `cv2.phaseCorrelate`** on small grayscale frames (~6 fps sampling) | ✅ TESTED – KEPT | Camera-motion score per second, used to find steady stretches when cutting B-roll from raw footage |
| **Frame-difference jump-cut detector** (mean abs diff of 72×128 gray frames > max(6, 4×median), local max) | ✅ TESTED – KEPT | `glorious.py jump_cuts()`: finds cuts in the cleaned video so zoom changes land on them (hides the jump) |
| **Robust Video Matting (RVM), MobileNetV3 fp32 ONNX + onnxruntime 1.23.2** | ✅ TESTED – KEPT | Person alpha matte so the giant hook word sits **behind** Maria. 720×1280 inference, ~6 s per 3 s of video. File: `_tools/rvm_mobilenetv3_fp32.onnx`, script `_tools/rvm_mask.py`. (Earlier summaries called it an "AI-generated cut-out"; it is matting, not generative AI.) |
| **ORB feature matching** (final vs clean frames) | ✅ TESTED – used for QA only | Measured the real zoom scale per frame to verify the zoom curve and catch single-frame jumps |
| **Pillow** (+ `ImageFont.getlength`) | ✅ TESTED – KEPT | Text measurement for caption line-wrapping. Drew the legacy name/list cards (PNG). |
| **pillow-heif** | ✅ TESTED – KEPT | HEIC photo import into the B-roll library |
| **fontTools** | ✅ TESTED – KEPT | Read font metrics (winAscent/winDescent) so browser preview = libass render. Renamed font families (e.g. `GL Sans`, `GL Roboto Bold`) so libass picks the exact file. |
| **PySceneDetect, MediaPipe, YOLO, Demucs, librosa** | ❌ **NEVER USED** | Not tried in any session. (Some are recommended in §6 as untested.) |
| **Any generative video / AI image tool inside the pipeline** | ❌ NOT USED | Maria's library contains some AI images and a Veo clip she made elsewhere; the pipeline only catalogs them. |

### 1d. Apps and front-ends
| Tool | Status | Notes |
|---|---|---|
| **Captions app (Captions.ai)**, Maria's paid subscription | ✅ USED AS THE STYLE REFERENCE | We reverse-engineered its caption animation, zoom rhythm, whip transition and list cards frame by frame from Maria's export `what_is_breadcrumbing_EDITED-IN-CAPTIONS.mp4` (still in her folder). Result = our "Glorious" look. We did not automate the app itself. |
| **CapCut (Pro)** | ✅ USED MANUALLY BY MARIA | We **learned rules** by diffing her own CapCut edit against ours (whole rambling blocks cut, pauses squeezed to ~0.2 s, speed 1.1× as a per-video choice). **Never automated CapCut**, never generated CapCut project files. |
| **Custom browser editors** (plain HTML/JS, Chrome) | ✅ TESTED – KEPT | `B-roll Editor.html` (B-roll, captions, zooms, cards, hook, speed) and `Cut Editor.html` (fix cuts). Both use the **File System Access API** (Chrome only; Safari can't save into folders). |
| **Headless Chromium + `node --check`** | ✅ TESTED – QA only | Tested the editors and caught a JS syntax bug. Headless Chromium could not play her video files, so live preview was only proven in her real Chrome. |

---

## 2. What worked best (and why)

1. **"Claude decides, ffmpeg executes, a JSON file is the contract."** The AI reads a word-level transcript and writes an edit decision file:
   - `edits.json` for cuts
   - `*_broll_project.json` for visuals

   Deterministic Python + ffmpeg renders exactly that file. Maria edits the same JSON visually in the HTML editors, then the identical renderer re-renders. This loop is the single most important design choice: it is reproducible, diffable and human-correctable.

2. **Parakeet TDT 0.6B v2 via sherpa-onnx, decoded phrase by phrase.** We split on silences (`silencedetect=n=-38dB:d=0.18`), merged into phrases of 1–4 s, and padded each phrase with 0.2 s of silence before decoding. This preserved **um/uh and doubled words**, which long-window decoding silently drops. Word end = next word start, clamped to the next detected silence.

3. **Voice-fade-aware cut edges (no clipped words).**
   - Each kept phrase gets -0.12 s / +0.15 s base padding.
   - The edge is then **extended until the 10 ms RMS falls below -42 dB**, plus a 0.06 s tail / 0.04 s lead.
   - Inner dead air ≥ 0.2 s is squeezed to a breath (0.08 s tail + 0.06 s lead).
   - Every edge gets a 12 ms audio fade.
   - Everything snaps to the frame grid.

   This fixed Maria's #1 complaint (clipped words, abrupt joins).

4. **Studio voice on the whole raw take first, then cut** (so the Cut Editor preview sounds exactly like the render):
   `highpass 85 Hz → arnndn (RNNoise, mix 0.85) → EQ -3 dB @250 Hz → +3.5 dB @3.2 kHz → high-shelf +4 dB @6.5 kHz → compressor 3:1 (thr -26 dB, att 8 ms, rel 120 ms, makeup 4 dB) → deesser → two-pass loudnorm -14 LUFS / TP -1.5 / LRA 7`.
   Her raw car audio sits around -35 LUFS; the result is much louder and clearer. Approved.

5. **Frame-exact chunked rendering.**
   - Each kept segment gets exactly `round(off[k+1]·fps) − round(off[k]·fps)` frames (`trim` + `setpts=N/(fps*TB)` + `tpad` clone + `trim=end_frame`).
   - Chunks are concatenated with `-c copy`.
   - The assembled frame count must equal the expected count.

   Result: video never drifts from audio, and the editor round-trip was frame-identical (tested: 3,049 frames, audio within half a frame).

6. **The "Glorious" look**, Captions-app style. It took **9 versions** (v1–v9) to get right, and Maria approved v9 with her own edits.
   - **Captions:**
     - Inter Tight Bold, off-white `#FCFCFC`.
     - Each word slides in from the left (0.045×W over 230 ms) and fades up (170 ms) as she says it.
     - The first word of each page is supersized.
     - Pages hold max 5 words and max 2 lines, wrapping at 72 % of width.
   - **Hand-picked keywords**, roughly one every 3–4 s, in four styles:
     - `neg`: Inter Tight Bold Italic rendered in **negative** (letters show the inverted video)
     - `serif`: Instrument Serif Italic
     - `script`: Yellowtail, yellow `#F2EC2E`
     - `yellow`: mustard `#D9C933`
   - **Fast zooms**: a new framing on almost every caption page (~every 1.5 s) cycling wide 1.0 / medium 1.12 / tight 1.24.
     - Changes snap in 0.22 s, or instantly on a jump cut, then creep in +1.5 %/s.
     - **Whips** on 3–5 big lines: 2-frame 55 % white flash, then 1.55× snapping back over 0.8 s on the measured curve `[1, .951, .805, .369, .147, .065, .027, .005, 0]`.
     - The measured whip matched the Captions app "to the hundredth".
   - **Hook word**: a huge Inter Tight Black word behind her head (RVM matte), "sunrise" rise and fade-in over 0.65 s.
   - **2026-11-10 change:** the hook is now a sentence in a dark box in front of her (`hookText`, `glorious.py hookbox_png`; 3 options written per video, see `.claude/skills/glorious-visuals/hooks.md`). The big words became **accent words** through the video (`accents` + `accentStyle`, one RVM cut-out per accent); the framing eases to wide while one shows so it stays readable above her head. Old `hook` projects are read as one accent (`legacy_hook`).
   - **List cards**: light panel, translucent top strip, gray "0 1" number plus label.

7. **B-roll from her own library only, matched literally to the spoken line.** Examples: "walk away" → her walking down the dock; "hot and cold" → quick burst with headline words.
   - Her face stays on screen for the hook, thesis, punchlines and last line.
   - Coverage: 20–35 %.
   - No clip reused in back-to-back videos (enforced via the usage log in `CATALOG.md`).
   - Library clips are pre-cut to 1080×1920 / 30 fps / muted, with HDR tone-mapped and photos turned into push-ins.

8. **Visual QA by actually looking.** Every render was checked: contact sheets / frame strips from each B-roll slot, caption pages, hook and whip were staged and viewed, plus re-transcription of the output to catch leftover fillers. This caught most bugs before Maria saw them.

9. **Persisting tools + rules.** A `_tools/` folder (~700 MB) caches models and scripts, and saved skills store every approved rule. This removed the repeated back-and-forth.

---

## 3. What failed and what we learned

| # | Problem we hit | Cause | Fix / lesson |
|---|---|---|---|
| 1 | faster-whisper unusable | Hugging Face blocked in the sandbox | Switched to Parakeet from GitHub. *Lesson: check model-hosting reachability first.* |
| 2 | **Leftover "um"s and repeated words** in video 2 ("0924-2") | Parakeet over long 15–30 s windows **smooths over disfluencies** | Phrase-level decoding (§2.2). A stray "A" before a word is often an "uh". Always re-transcribe the output as QA. |
| 3 | **Clipped word endings / choppy sentence** (the "Tinder" section, video 1) | Cut edges at ASR word boundaries; several micro-cuts in one sentence | Voice-fade edge extension (§2.3). Rule: **one clean cut beats several micro-cuts**; leave a small stutter ("v- very") if cutting it sounds worse. Never cut where grammar breaks ("if you kind of interested" stays). |
| 4 | Single full-length render died | 180 s shell cap; `nohup`/`setsid` background jobs were killed | Chunked rendering + assemble (all scripts) |
| 5 | Zoom-ins felt jarring (v1) | Hard cuts between zoom levels | 0.7 s smoothstep ease |
| 6 | Zoom showed the **car ceiling** | Zoomed on frame center | Face-anchored zoom (Haar face + chest anchor) |
| 7 | **Zoom pinned to top-left corner** (v3) | Using `iw/ih` in `crop` x/y with `scale=...:eval=frame`; ffmpeg 4.4 keeps the first frame's size | Never use `iw/ih` there; compute crop offsets from the fixed anchor: `x='ax*(Z-1)'` |
| 8 | Hook title covered her face (tighter-framed video) | Fixed overlay position | Face-band aware placement with fallbacks (top / above head / below chin) |
| 9 | `CascadeClassifier` missing | Latest opencv-python-headless wheel | Pin `opencv-python-headless<5` |
| 10 | Setup installed packages into the wrong Python | Bare `pip3` | Always `sys.executable -m pip` |
| 11 | Claude inferred a **1.1× speed-up default** from her CapCut edit | Over-generalised one per-video choice | Rejected by Maria. Speed is only a manual editor setting. *Lesson: ask before turning observed edits into defaults.* |
| 12 | "Captions-style" zooms came out almost **flat** (Glorious v3) | We measured Captions' zooms by comparing against an **intermediate** edit that already had our zooms, which cancelled them out | Compare against the **clean source**. Also: rare/slow zooms (every 8–10 s) and subtle drift-outs were **rejected**; the fast per-phrase rhythm is the point. |
| 13 | First whip flickered every 3rd frame | Timing bug in the zoom expression | Fixed; full-video scan for single-frame jumps (ORB scale) |
| 14 | Caption preview vs render mismatch risk | Browser and libass size fonts differently | `fonts.json` `k` = (winAscent+winDescent)/unitsPerEm; `cal.json` per-font baseline/cap calibration. Pixel-match verified. |
| 15 | Non-Glorious caption presets (Bold Pop, Clean, Elegant, Boxed) **silently rendered no captions** in the visuals renderer | `glorious.py` only drew its own engine | Fixed 2026-10-23 (`glorious.py` now also burns classic presets via `captions.py`) |
| 16 | A new chat used **stock footage** from the internet, against Maria's rule | Skills had been described but not saved | Rule now hard-coded: **her library only**; stock only from her saved `stock-` clips, max 1–2 per video. *Lesson: persist rules in files, not in chat.* |
| 17 | Library clips slightly softer than the main video | Library standardised at 1080×1920; her talking videos are 1440×2560 | Not noticeable on a phone; would matter on large screens. Consider 1440×2560 library clips in future. |
| 18 | JS syntax error after patching an editor | Escaped backticks in a Python string patch | Always run `node --check` on the extracted `<script>` after edits; keep backups (`_tools/tmp/`) |
| 19 | Card/cleanup pass vs visuals confusion | One monolithic skill did everything | Split into **Step 1 cleanup** (cuts + voice only) and **Step 2 visuals** |
| 20 | Logos | Real brand logos shouldn't be redrawn | Name cards in brand colours; real logo files only if Maria supplies them |

**Unproven or in progress:**
- **Cut Editor:** built and round-trip tested by Claude, but Maria hasn't saved a real fix in it yet (`breadcrumbing_cut_project.json` shows `keep == autoKeep`, `savedAt: null`). It is still unproven in her hands.
- **Hook-word style:** still being settled.
- **"Mic Drop" caption preset:** Roboto Bold, white, thin outline, soft shadow. Built and test-rendered on 2026-10-23, but not yet used on a published video.

---

## 4. Our final working pipeline (as of 2026-10-24)

```
RAW iPhone talking video (.mov, HEVC, 1440x2560 or 1080x1920, 30fps)
   │
   ├─ STEP 0 (separate, ongoing): B-roll library  [update-broll-library]
   │     raw clips/photos → probe → HDR? tone-map → contact sheets → phaseCorrelate motion
   │     → Claude picks 2–4 s steady moments → clips.json → build_clips.py
   │     → clips/<id>.mp4 (1080x1920/30/muted) + thumbs + CATALOG.md (theme finder, usage log)
   │
   ├─ STEP 1: Cleanup  [polish-talking-video → _tools/polish.py]
   │     setup → transcribe (Parakeet, phrase-level) → Claude writes edits.json
   │     → plan (prints KEPT TEXT; iterate) → audio (studio voice on whole take, cut, -14 LUFS)
   │     → chunk N… (frame-exact) → assemble (frame-count OK) → qa (re-transcribe, fillers, doubles)
   │     → edited/<name>_clean.mp4 + _cutlist.txt + _transcript.txt
   │     → cutproject → edited/<name>_cut_project.json (+ proxy.mp4, voice.wav)  ⇄  Cut Editor.html
   │                                                     ("render my cuts" → fromcut → re-render; remap visuals)
   │
   └─ STEP 2: Visuals  [glorious-visuals → _tools/glorious.py]  (or add-broll-to-video for B-roll only)
         words of CLEAN video (verbatim_words) → contact sheet → Claude picks keywords (emph)
         → B-roll slots from CATALOG.md (+ usage-log check) → cards (tiles) → hook word
         → write edited/<name>_broll_project.json → whipAt + autozoom
         → plan (prints caption pages) → chunk N… → assemble → visual QA
         → edited/<name>_glorious.mp4 + _glorious_list.txt + usage-log line
         ⇄ B-roll Editor.html (Maria tweaks; Save → status "edited")
            → "render my edits for <name>": diff vs last render, re-render as-is, next _vN
```

### Step 1 in commands (Linux VM paths; replace `$HOME/mnt/...` with `/Users/mariablair/Desktop/...` natively)
```bash
V="$HOME/mnt/AI agent video edit"
mkdir -p ~/vidpolish && cp "$V/_tools/polish.py" ~/vidpolish/ && python3 ~/vidpolish/polish.py setup
python3 ~/vidpolish/polish.py transcribe "$V/<raw>.mov" ~/vp/<name>      # prints idx:word@start, FILLERS, REPEATS
# Claude writes ~/vp/<name>/edits.json:
#   {"delete_words": [[a,b,"filler"],[c,d,"restart"],...],  "delete_times": [[t1,t2]], "max_pause": 0.2}
#   reasons: filler | restart | repeat | ramble | stumble | trim
python3 ~/vidpolish/polish.py plan ~/vp/<name>        # final length, chunks, KEPT TEXT → re-read like a viewer
python3 ~/vidpolish/polish.py audio ~/vp/<name>
python3 ~/vidpolish/polish.py chunk ~/vp/<name> 0     # …for every chunk N (≈30–50 s each)
python3 ~/vidpolish/polish.py assemble ~/vp/<name> ~/vp/<name>/final.mp4   # must print OK
python3 ~/vidpolish/polish.py qa ~/vp/<name> ~/vp/<name>/final.mp4
python3 ~/vidpolish/polish.py cutproject ~/vp/<name> <name> edited/<name>_clean.mp4
# After Maria fixes cuts in Cut Editor.html:
python3 ~/vidpolish/polish.py fromcut "$V/edited/<name>_cut_project.json" ~/vp/<name>_cut   # then plan/audio/chunk/assemble/qa
python3 ~/vidpolish/polish.py remap "$V/edited/<name>_cut_project.json" "$V/edited/<name>_broll_project.json"
```

### Step 2 in commands
```bash
G="$V/_tools/glorious.py"
python3 "$G" autozoom "$V/edited/<name>_broll_project.json"    # after setting project.whipAt
python3 "$G" plan     "$V/edited/<name>_broll_project.json"    # prints caption pages + chunk count
python3 "$G" chunk    "$V/edited/<name>_broll_project.json" ~/vp/<name>_glo 0   # …each chunk (~24 s spans)
python3 "$G" assemble "$V/edited/<name>_broll_project.json" ~/vp/<name>_glo ~/vp/<name>_glo/final.mp4
```
B-roll-only path (older, still works): `"$B/_catalog/add_broll.py" chunks|chunk|assemble` with `broll.json`, optionally followed by `_tools/captions.py chunks|chunk|assemble`.

### Editorial rules Maria approved (these matter as much as the code)
- **Cut:**
  - um/uh; filler "you know", "basically", "kind of", "I mean", "like"
  - extra "I would say / I think" hedges
  - false starts and half-words; keep the **last** clean take
  - **whole rambling blocks** ("does the viewer lose anything if this is gone?")
  - restatements and circular labels
- **Keep:** her personality and hooks ("So honestly, ladies", "Hands down", "And here's the thing", "God forbid"), jokes, short emphasis beats, wrap-up recaps. When unsure: keep and flag in the cut list.
- **Normal speed** by default. Dead air goes down to about 0.2 s, but never tighten the voice-fade padding.
- Strip all metadata (`-map_metadata -1`; the iPhone GPS location). Never touch originals. Version outputs `_v2`, `_v3`.
- **B-roll:**
  - Her own footage first. No daughter in shots unless asked. Clips where her mouth moves are avoided (B-roll is muted).
  - Celebrity-lookalike images get a caution flag and are never used unless she asks.
- **Glorious B-roll pacing:** visual lines get bursts of 1.2–2 s per clip; elsewhere single 2–3 s slots; 20–30 % of runtime. Classic B-roll skill: 30–35 %, 2.5–3 s slots.
- Deliver one finished result without asking for approval first, then report changes in a short table.

---

## 5. Implementation details

### 5a. File map (on Maria's Mac)
```
~/Desktop/AI agent video edit/
├── B-roll Editor.html          # visuals editor (Chrome; File System Access API)
├── Cut Editor.html             # cut-fixing editor (Web Audio playback identical to render)
├── edited/                     # deliverables + project JSONs
│   ├── breadcrumbing_clean.mp4, breadcrumbing_glorious_v9.mp4 (approved reference result)
│   ├── breadcrumbing_cut_project.json, breadcrumbing_broll_project.json
│   ├── Glorious-custom-theme.txt   # slot/zoom/card list of the approved v9
│   └── _analysis/                  # frame studies of the Captions reference (z21_*.jpg = zoom study 0:21–0:25)
├── what_is_breadcrumbing_EDITED-IN-CAPTIONS.mp4   # Captions-app reference export
└── _tools/
    ├── polish.py               # Step 1 (setup, transcribe, plan, audio, chunk, assemble, qa,
    │                           #         voice, proxy, cutproject, fromcut, remap)
    ├── glorious.py             # Step 2 renderer (captions, B-roll, zooms, whips, cards, headlines, hook, speed)
    ├── captions.py             # classic caption presets → ASS → libass
    ├── rvm_mask.py + rvm_mobilenetv3_fp32.onnx   # person matte for the hook word
    ├── sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/  # ASR model (portable)
    ├── sh.rnnn                 # RNNoise model (portable)
    ├── fonts/  (*.ttf, fonts.json, cal.json)   # GL* = renamed Inter Tight / Instrument Serif / Yellowtail / Roboto
    ├── caption-presets.json    # Maria's saved preset tweaks (her "glorious" version has the shadow ON)
    ├── caption-style.json      # her default caption style
    ├── wheels/                 # Linux aarch64 wheels — NOT for native macOS
    ├── cut/<name>/             # proxy.mp4, voice.wav per video
    ├── tmp/                    # backups: glorious_v1..v7.py, editor versions, older renders
    └── VERSION.txt             # change log
~/Desktop/b-roll collection/
├── clips/<id>.mp4              # 142 clips, 1080x1920, 30fps, muted
├── _catalog/clips.json         # master DB: id, src, in, out, scene, maria, setting, tags, mood, hdr, still, ai, stock, caution
├── _catalog/CATALOG.md         # theme finder, tables, sources processed, skipped, USAGE LOG
├── _catalog/build_clips.py     # cuts clips (HDR tone-map, photo push-in), --only=N batching
├── _catalog/add_broll.py       # simple B-roll overlay renderer
└── _catalog/thumbs/, stills/, previews/
```

### 5b. Dependencies we actually used
- **System:** ffmpeg/ffprobe 4.4.2 with `libass`, `libzimg` (zscale), `arnndn` (built in), `loudnorm`, `libx264`
- **Python 3.10:**
  - `sherpa-onnx==1.13.8`, `soundfile`, `numpy` (2.2.6), `pillow` (12.3), `opencv-python-headless<5` (4.14)
  - `onnxruntime==1.23.2`, `pillow-heif`, `fontTools`
- **Models:**
  - `sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8` from `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2`
  - RNNoise `sh.rnnn` from `https://raw.githubusercontent.com/GregorR/rnnoise-models/master/somnolent-hogwash-2018-09-01/sh.rnnn`
  - RVM `rvm_mobilenetv3_fp32.onnx`, saved in `_tools/`
- **Fonts (Google Fonts, renamed):**
  - Inter Tight Bold / Bold Italic / Medium / Black
  - Instrument Serif Italic, Yellowtail, Roboto Bold
  - Montserrat ExtraBold, Anton, Bebas Neue, Poppins, DM Serif Display, Great Vibes

### 5c. Key code excerpts (verbatim from the working scripts)

**Recognizer + phrase-level decoding** (`polish.py`):
```python
rec = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=M+"encoder.int8.onnx", decoder=M+"decoder.int8.onnx", joiner=M+"joiner.int8.onnx",
    tokens=M+"tokens.txt", model_type="nemo_transducer", num_threads=4)
# silencedetect=n=-38dB:d=0.18 → speech regions → merge into phrases (<4 s, gaps <0.35 s)
# each phrase decoded separately with 0.2 s of zero padding on both sides; tokens starting with " " begin a new word
```

**Studio voice + loudness** (`polish.py`):
```python
STUDIO = ("highpass=f=85:poles=2,arnndn=m={rnn}:mix=0.85,equalizer=f=250:t=q:w=1.2:g=-3,"
          "equalizer=f=3200:t=q:w=1.0:g=3.5,highshelf=f=6500:g=4,"
          "acompressor=threshold=-26dB:ratio=3:attack=8:release=120:makeup=4dB:knee=4,deesser=i=0.4")
# applied to the whole take at 48 kHz mono → cut pieces with 12 ms afade in/out → concat
# pass 1: loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json ; pass 2 with measured_* values, linear=true → AAC 192k
```

**Frame-exact segment render** (`polish.py chunk`):
```python
st = (round(g["s"]*fps) - 0.5)/fps - t0     # nearest source frame to the cut
f.append(f"[0:v]trim=start={st:.5f}:end={st+nk/fps:.5f},setpts=N/({fps}*TB){zoom},"
         f"tpad=stop_mode=clone:stop=3,trim=end_frame={nk},setsar=1[v{k}]")
# encode: libx264 -preset medium -crf 18 -pix_fmt yuv420p -colorspace/primaries/trc bt709 -frames:v <exact>
```

**Zoom without the `iw/ih` bug** (both renderers):
```
scale=w='trunc(W*Z/2)*2':h='trunc(H*Z/2)*2':eval=frame:flags=bicubic,
crop=W:H:x='AX*(Z-1)':y='AY*(Z-1)'          # AX,AY = fixed anchor in pixels; Z = time expression
```

**HDR → SDR and photo push-in** (`build_clips.py`):
```
TM = zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p
clip:  [TM,]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p   (-an, crf 19)
photo: scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840:(iw-2160)/2:(ih-3840)*0.3,
       zoompan=z='1+0.0008*on':x='iw/2-(iw/zoom/2)':y='ih*0.35-(ih/zoom*0.35)':d=1:s=1080x1920:fps=30   (105 frames)
HDR detection: ffprobe color_transfer in {arib-std-b67, smpte2084}
```

**Negative-mode keyword / hook** (`glorious.py`): render the text as a white-on-black ASS **mask**, `negate` a copy of the video, `alphamerge` the mask, overlay. For the hook: mask = text_mask × (255 − person_matte)/255, so the word sits behind her.

**Speed** (`glorious.py`): all timings stay in clean-video time; `setpts=(PTS-STARTPTS)/SP` at the end of each chunk with cumulative frame rounding (`round(t1*fps/SP) − round(t0*fps/SP)`); audio via `atempo`.

### 5d. The project file (the contract between AI, editor and renderer)
```jsonc
// edited/<name>_broll_project.json
{
  "version": 1, "video": "edited/<name>_clean.mp4", "duration": 101.667, "fps": 30,
  "status": "rendered|edited", "rendered": "edited/<name>_glorious_v9.mp4", "savedAt": "...",
  "words":  [{"w":"Breadcrumbing","s":0.62,"e":1.31,"emph":"neg","hide":false}, ...],
  "slots":  [{"a":31.0,"b":32.25,"clip":"cocktails-dinner-table","from":0.3,"line":"one day he is there,",
              "headline":"there","reveal":false}, ...],
  "tiles":  [{"a":58.05,"b":65.25,"num":1,"text":"Withhold intimacy"}],
  "zooms":  [{"a":0.0,"b":0.8,"type":"beatwhip","z":1.35,"to":1.0,"flash":false},
             {"a":0.8,"b":2.15,"type":"beat","z":1.0,"ease":0,"creep":0.015}, ...],
  "whipAt": [24.7, 49.0, 72.6, 98.97], "zoomAnchor": [0.515, 0.5],
  "hook":   {"enabled":true,"text":"Breadcrumbing","a":0.6,"b":3.6,"y":0.165,"size":0.35,"style":"neg"},
  "speed":  1.1,
  "captions": {"enabled":true,"engine":"glorious","preset":"glorious","color":"#FCFCFC","y":0.635,"yB":0.70,
               "gLine":0.72,"gPad":0.06,"gScriptColor":"#F2EC2E","gYellowColor":"#D9C933",
               "gSizes":{"small":0.068,"big":0.13,"neg":0.12,"serif":0.14,"script":0.15,"yellow":0.12},
               "gShadowOn":true,"gShadow":0.0055,"gShadowBlur":0.006,"gShadowOpacity":0.5,"start":0}
}
```
Caption presets available in the editor: **Bold Pop, Clean, Elegant, Boxed, Mic Drop, Glorious**. Sizes are fractions of video width.
Mic Drop = `roboto-b`, size 0.082, 4 words, white, outline 0.0025, shadow 0.003 @ 50 %, y 0.665, width 0.72, no highlight, no pop.

### 5e. Reusable code (keep, don't rewrite)
| File | Reuse for concert project? |
|---|---|
| `polish.py` (transcribe/verbatim_words, auto_segs, voice, frame-exact chunk/assemble, qa) | **Yes**, for the talking-head part of Reel B |
| `glorious.py` (captions, zooms, B-roll overlay, hook, cards, speed) | **Yes**, for Reel B visuals; parts for Reel A text overlays |
| `captions.py` (classic presets incl. Mic Drop) | Yes |
| `build_clips.py` + catalog method (contact sheets, phaseCorrelate, HDR tone-map) | **Yes**, for turning concert footage into clips |
| `add_broll.py` | Yes (simple overlay path) |
| `rvm_mask.py` | Optional (hook word behind her) |
| `B-roll Editor.html`, `Cut Editor.html` | Yes, for Reel B review and fixes. **No music/beat timeline exists in them.** |

---

## 6. Recommendations for the concert project

> Everything in this section marked 💡 is **new and untested in our workflow**. Items marked ✅ reuse proven parts.

### 6a. Expected input problems (from what we know about her footage)
1. ✅ **iPhone HDR (HLG/Dolby Vision HEVC)**: very likely for concert clips. Tone-map with the proven `TM` chain before anything else, or colours wash out and grey out on Instagram.
2. 💡 **4K and/or 60 fps sources**: conform to 1080×1920 at 30 fps (our standard). For slow-motion dance moments, 60 fps clips could be slowed to 50 % (untested).
3. 💡 **Horizontal clips** of the stage: our crop is center-crop to 9:16. For stage shots, a fixed center crop may cut the performer. Consider subject-aware crop (face/person detection → crop center) or a blurred-background "framed reveal" (our tested `reveal` effect does exactly this for photos).
4. ⚠️ **Concert noise under talking-head speech**: our studio-voice chain (RNNoise mix 0.85) was tuned for **car noise**, not 100 dB music. Parakeet transcription accuracy over loud music is **untested**. See §6d.
5. 💡 **Copyright**: concert audio contains the artist's copyrighted performance. Instagram may mute or limit Reels with recognised music, and music-library access can differ for business accounts. **Check Instagram's current rules** ([Instagram Help: licensed music library](https://help.instagram.com/ipad-app/402084904469945)). Design both reels so the music bed is replaceable.

### 6b. Recommended stack
| Layer | Recommendation | Status |
|---|---|---|
| Render engine | ffmpeg (Homebrew `ffmpeg-full` on native macOS) + Python | ✅ proven (Linux VM, then native macOS since the 2026-10-25 port) |
| Check native ffmpeg has the filters | `ffmpeg -hide_banner -filters \| grep -E " (ass\|subtitles\|zscale\|tonemap\|arnndn\|loudnorm\|xfade) "` | 💡 must verify; `zscale` needs libzimg |
| Transcription | Parakeet TDT 0.6B v2 via sherpa-onnx, phrase-level | ✅ (quiet speech); 💡 untested over music |
| Speech/music separation | **Demucs (htdemucs)** to pull voice out of concert noise; alternatively CapCut Pro's voice enhance/noise reduction | 💡 untested |
| Beat detection for montage | **librosa** `beat.beat_track` + `onset_strength` (or aubio) on the chosen music file | 💡 untested |
| Shot selection | Our catalog method: contact sheets + `phaseCorrelate` camera-motion score + face detection + AI review of frames. **Note:** phase correlation measures *camera* motion, so a steady shot of her dancing still scores as steady. Exactly what we want. | ✅ method proven; 💡 on concert/low-light footage untested |
| Low-light quality filter | Sharpness (variance of Laplacian) + brightness/exposure score to drop blurry/dark frames | 💡 untested |
| Transitions | Mostly hard cuts on beats; `xfade=fade` 0.2–0.3 s only at section changes | 💡 xfade untested in our pipeline |
| Colour | One consistent grade for all clips (`eq`, `colorbalance`, or a `.cube` LUT via `lut3d`) after tone-mapping | 💡 untested |
| Captions/text | Our fonts and presets: **Elegant** (DM Serif), Glorious serif/script, or **Mic Drop** for speech | ✅ |
| Final polish | CapCut Pro, optional manual pass | ✅ Maria uses it; automation with CapCut 🔍 never tried |
| Hardware encoding | Tested 2026-10-25 with VMAF (her rule: switch only if within 1 point and at least 2x faster). polish.py finals use `h264_videotoolbox -b:v 16M` (VMAF 98.07 vs 98.72, 2.6x faster); glorious.py stays on `libx264 -crf 18` (its compositing caps the gain at 1.8x). | ✅ decided |

**Native macOS setup (💡 untested):**
```bash
brew install ffmpeg            # verify filters as above
python3 -m venv ~/.venv/gg && source ~/.venv/gg/bin/activate
python -m pip install sherpa-onnx soundfile numpy pillow "opencv-python-headless<5" onnxruntime pillow-heif fonttools librosa
# reuse model files from ~/Desktop/AI agent video edit/_tools (Parakeet dir, sh.rnnn, rvm onnx, fonts/)
```

### 6c. Reel A: 15–25 s elegant, music-driven lifestyle montage (💡 new workflow, built on ✅ parts)
1. **Ingest.** Probe all clips; tone-map HDR; conform to 1080×1920 / 30 fps (✅ `build_clips.py` logic). Keep a 1440×2560 or 4K intermediate if possible to avoid the softness issue (#17).
2. **Catalog.**
   - Make a contact sheet per clip (1 frame/s, timestamps) and compute camera motion, sharpness, brightness and face present (✅/💡).
   - The AI reviews the sheets and tags each candidate moment: `dancing`, `smiling`, `crowd`, `stage`, `lights`, `close-up`, `wide`, `energy 1–5`, `elegance 1–5`.
3. **Music.** Choose **one licensed track** as a local file (or the exact song she'll add in Instagram, so the edit matches its tempo).
   - Detect BPM, beats and downbeats (💡 librosa).
   - Pick the 15–25 s section with the strongest build or drop.
4. **Cut plan (JSON EDL, same philosophy as our project file).**
   - Elegant ≠ frantic: cut every **2 beats** in calm parts and every **1 beat** only at the peak. At ~120 BPM, 2 beats = 1 s.
   - Arc: establishing (lights, venue) → Maria enjoying (smile, sway) → peak (dancing, crowd) → hero close-up ending on a smile or look to camera.
   - No clip reused. Prefer her face and body over stage shots (≥ 60 % "Maria" shots).
   - Allow a slight speed ramp or slow-mo on 1–2 hero moments (💡).
5. **Render.**
   - Hard cuts exactly on beat frames (round to the frame grid, our frame-exact method ✅).
   - Gentle 3–7 % push-in on held shots (✅ our B-roll push-in).
   - Optional 1–2 short text overlays in serif (e.g. a "Glorious at 40+" line), placed in the upper third away from the Instagram UI.
   - Music at -14 LUFS integrated; concert ambience optional at -20 dB under the track.
6. **QA (✅ method).** Contact strip at every cut; verify cut frames land on beats (±1 frame); frame count; loudness via `ebur128`.
7. **Deliverables.** `concert_montage_vN.mp4`, plus a **"no music" version** (so Maria can add a licensed song in Instagram), plus the numbered selected clips for CapCut if she wants to fine-tune.

### 6d. Reel B: 30–60 s personal-story Reel (talking head + dancing/concert B-roll)
Reuses the proven two-step pipeline almost unchanged:
1. **Audio decision first (most important risk).**
   - **Best:** record the talking-head part in a quiet place (car or home) the day after, and use concert clips only as B-roll. The proven pipeline then works as-is.
   - **If the talking head was filmed at the concert:** run voice separation (💡 Demucs), then our studio voice (✅), then check intelligibility. Parakeet over residual music is 💡 untested; budget for manual word fixes in the B-roll Editor's caption words.
2. **Step 1 cleanup** with `polish.py` (✅): fillers, restarts, rambling blocks, 0.2 s pauses, -14 LUFS, Cut Editor available.
3. **Concert clips into the library.**
   - Add the concert clips to the B-roll library with tags (`concert`, `dancing`, `crowd`, `stage`, `night`) via `build_clips.py` and catalog entries (✅).
   - Or keep a separate `concert` catalog so the usage-log rule still works.
4. **Step 2 visuals** with `glorious.py` (✅):
   - Her face for the hook, thesis lines and ending.
   - Dancing/concert B-roll on visual lines in bursts of 1.2–2 s, 25–35 % coverage.
   - Captions: **Glorious** (keywords) or **Mic Drop** (cleaner).
   - Fast zooms only on face segments, never under B-roll.
   - Optional hook word behind her (RVM ✅).
5. **Music bed under speech** (💡 untested): a licensed track ducked about 18–22 dB below the voice (`sidechaincompress` or a fixed volume envelope). Keep the voice at -14 LUFS integrated. Option: let concert audio swell for 1–2 s in a B-roll burst with no speech.
6. **Review** in `B-roll Editor.html` → "render my edits" (✅ loop).

### 6e. Suggested build order for Codex
1. Port `polish.py` / `glorious.py` / `build_clips.py` to run **natively** (paths, venv, filter check). Run them on the existing `breadcrumbing` project and compare against `breadcrumbing_glorious_v9.mp4`: same frame count, visually identical. This proves the port before anything new.
2. Build the **concert ingest + catalog** step (tone-map, conform, quality scores, contact sheets).
3. Build **Reel B** first (mostly reuse), then **Reel A** (new: beat detection + montage EDL + renderer).
4. Optional: add a music/beat lane to `B-roll Editor.html` so Maria can nudge cuts.

### 6f. Acceptance checklist (from Maria's stated preferences)
- 9:16, 1080×1920 (or 1440×2560), 30 fps, H.264, AAC 48 kHz, -14 LUFS / TP ≤ -1.5, metadata stripped
- No clipped words, no leftover fillers (re-transcribe), no abrupt joins
- Text never covers her face; captions sit roughly 63–70 % down the frame (clear of the Instagram caption area)
- Her own footage only (no internet stock unless she asks)
- Originals untouched; outputs versioned `_vN`; a short "what changed" table per version
- One finished deliverable per request; she fine-tunes in the editor or CapCut

---

## 7. What's missing / could not be verified
- **Native macOS:** nothing was ever run natively; all results are from the Linux VM inside the Claude desktop app.
- **Music and beat sync:** we never did any music editing, beat detection or montage work. Reel A is new territory.
- **Concert footage:** not seen yet, so the HDR, frame-rate, orientation and noise assumptions are unverified.
- **No numeric quality benchmarks** beyond frame-count checks, re-transcription QA, loudness targets and Maria's approvals. No word-error-rate comparison of ASR models was ever done.
- **The early raw videos** (`online-dating-apps.mov`, `0924-2`) and Maria's own CapCut edit file are no longer in the folder; the rules learned from them survive only in the skills and this report.
- **Unproven in practice:**
  - The Cut Editor hasn't been used by Maria on a real fix yet.
  - Mic Drop hasn't been used on a published video.
  - The hook-word style is still being decided.
- **Chat history coverage:** these were recovered via search of the past chats, not a full line-by-line read of every turn, though the saved skills and scripts are complete and authoritative. If something here conflicts with the code, **the code in `_tools/` and `_catalog/` wins.**

## Sources
- Local code and configs read on 2026-10-24: `~/Desktop/AI agent video edit/_tools/{polish.py, glorious.py, captions.py, rvm_mask.py, VERSION.txt, caption-presets.json, fonts/fonts.json}`, `~/Desktop/b-roll collection/_catalog/{build_clips.py, add_broll.py, CATALOG.md}`, `edited/Glorious-custom-theme.txt`, project JSONs
- Saved skills: `polish-talking-video`, `glorious-visuals`, `add-broll-to-video`, `update-broll-library`
- Past Claude chats, 2026-10-07 → 2026-10-23 (titles listed in §0)
- [Instagram Help: Access to the licensed music library](https://help.instagram.com/ipad-app/402084904469945): check current music rules before posting
