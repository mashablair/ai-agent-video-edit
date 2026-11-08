---
name: "polish-talking-video"
description: "Step 1 cleanup of Maria's raw talking-head video (car rambles for GG/MTT): cut fillers, stumbles, rambling and dead air, give it studio voice, and make it editable in her Cut Editor; also renders the cuts she fixed there (\"render my cuts\"). No cards, hook, zooms or captions; those are the visuals step."
---

# Clean up a raw talking-head video (step 1 of 2)

Maria hands over a raw phone video (usually vertical, 1080x1920 or 1440x2560, her talking in the car). This skill does ONLY the cleanup pass:
- cut fillers, false starts, repeated takes and rambling
- squeeze dead air to a short breath
- studio voice (denoise, EQ, compression, -14 LUFS)

It does NOT add visuals: no hook title, no list cards, no zooms, no captions, no B-roll, no speed-up. Those belong to step 2 (the glorious-visuals skill). Only add one of them here if she explicitly asks for it on that video.

Deliver ONE finished cleaned video without asking her to approve a first test.

## Where it runs
The work has to run on Maria's Mac, using the remote-devices `device_bash` tool.
- She keeps her videos in `~/Desktop/AI agent video edit`. Inside `device_bash` that folder is `$HOME/mnt/AI agent video edit`.
- If that folder isn't connected, ask her to add it with "Add folder" in the Claude desktop app. New raw videos should go into this folder, because it also holds the saved tools.
- In the cloud workspace, Hugging Face and most other sites are blocked. On her Mac, GitHub, PyPI and npm are reachable.
- Each `device_bash` call is capped at 180 seconds and background processes are killed when the call ends. That's why the script works in stages: each stage, and each render chunk, fits in one call.
- Keep the work directory in `~` (for example `~/vp/<name>`), never in her folder. Put only the deliverables in `<her folder>/Videos/<name>/` (her raw videos are in `Drop raw videos here/`). Never touch or delete her original file.

## Saved tools (`_agent` folder on her Mac)
`AI agent video edit/_agent/` holds the following, about 700 MB:
- `polish.py`, the latest script (always prefer it over the copy embedded below if they differ)
- `wheels/`, the Python packages
- the Parakeet speech model
- `sh.rnnn`, the noise-reduction model
- `VERSION.txt`, the date, versions and change notes
- `cut/<name>/`, the Cut Editor's files per video (`proxy.mp4`, `voice.wav`) and `cut/Cut Editor (backup).html`

Each chat gets a fresh workspace on her Mac, so load the tools from here instead of downloading them:
- **Saved copy exists:** `mkdir -p ~/vidpolish && cp "$HOME/mnt/AI agent video edit/_agent/polish.py" ~/vidpolish/ && python3 ~/vidpolish/polish.py setup`. This takes a few seconds.
- **Saved copy is gone** (she deleted it to refresh): write the script below to `~/vidpolish/polish.py`, then run `python3 ~/vidpolish/polish.py setup`. It downloads everything (about 3 minutes) and re-saves `_agent`.
- **She asks to update the tools:** run `python3 ~/vidpolish/polish.py setup --refresh`. It upgrades the packages, re-downloads, and re-saves `_agent` with a new date. Test on a short clip afterwards. If a newer or better speech model is adopted, change `MODEL_NAME` and the recognizer call, and keep the rest of the pipeline.

## Steps
1. **Setup** (see above).
2. **Transcribe.** Run `python3 ~/vidpolish/polish.py transcribe "<video>" ~/vp/<name>`. It prints an indexed word list (`idx:word@start [gap]`) plus FILLERS and REPEATS lists. Parakeet DOES transcribe "uh/um".
3. **Decide the cuts yourself** by reading the transcript, then write `~/vp/<name>/edits.json`:
   ```json
   {"delete_words": [[a,b,"filler"], [c,d,"restart"], ...],
    "delete_times": [[t1,t2], ...],
    "max_pause": 0.2}
   ```
   - `delete_words` are inclusive word-index ranges. Give each a reason, shown as a label in her Cut Editor: `filler` (um/uh/you know/like/basically), `restart` (false start, she re-says it), `repeat` (doubled word or phrase), `ramble` (whole muddled stretch), `stumble` (half-word, slip), `trim` (anything else).
   - `delete_times` are source-time cuts for fillers or doubled words the transcript missed.
   - `max_pause` (default 0.2 s) squeezes dead air to a short breath, matching her own CapCut pass.
   - Leave out `hook`, `cards`, `zoom` and `speed`. The script defaults to no overlays, no zoom and normal speed. Add one only if she explicitly asks for it on that video (`"zoom": true` gives the face-anchored 1.22x zooms; `"speed": 1.1` speeds up with pitch preserved).
4. **Plan.** Run `python3 ~/vidpolish/polish.py plan ~/vp/<name>`, then `python3 ~/vidpolish/polish.py pauses ~/vp/<name>` and view `pauses.jpg` (3 frames per pause >=0.4 s). Thinking pauses are squeezed to ~0.2 s automatically; for any pause where she smiles, smirks, rolls her eyes, gestures, or holds a deliberate dramatic beat, add its raw range to `"keep_pauses": [[t1,t2], ...]` in edits.json and plan again. List the kept beats in the cut list. It prints the final length, segment count, chunk count and the KEPT TEXT. Read the kept text like a viewer would (see "Editing rules"). If a sentence reads broken or a passage rambles, adjust `edits.json` and plan again.
5. **Audio.** Run `python3 ~/vidpolish/polish.py audio ~/vp/<name>`. Studio voice is applied to the whole raw take first (`voice.wav`, the same audio her Cut Editor plays), then cut with 12 ms fades and normalized to -14 LUFS.
6. **Video.** Run `python3 ~/vidpolish/polish.py chunk ~/vp/<name> N` for every chunk. Two or three chunks fit in one call; each takes about 30–50 seconds. Rendering is frame-exact (each piece gets exactly its share of frames, so video never drifts from the audio).
7. **Assemble.** Run `python3 ~/vidpolish/polish.py assemble ~/vp/<name> ~/vp/<name>/final.mp4`. The frame count must say OK.
8. **Check the result.** Run `python3 ~/vidpolish/polish.py qa ~/vp/<name> ~/vp/<name>/final.mp4`.
   - Check "long gaps" (dead air the squeeze missed, in output time; added 2026-11-08 after IMG_0959). In noisy outdoor audio (waves, wind, traffic) the pause detector misses gaps, so every one listed is a candidate: trim it with a `delete_times` cut at the quiet points (look at the dB profile), or cut the drawn-out connective it sits around (see "Slow or outdoor talk" below). Best done before the video render: after `audio`, re-transcribe `audio.m4a` and check the gaps there first.
   - Check "fillers left" and "doubled words". To fix one, map the output time back to source time through plan.json (segs/off), look at the 10 ms dB profile of a16.wav around it to find the exact burst, add a `delete_times` cut, then re-run plan, audio, all chunks and assemble.
   - Read the FINAL TRANSCRIPT once more for anything that still rambles or reads broken.
9. **Deliver to `<her folder>/Videos/<name>/`:**
   - `<name>_clean.mp4`; if that name exists, add _v2, _v3 and so on rather than overwriting.
   - `<name>_cutlist.txt`: take cutlist.txt and add a "kept on purpose" note.
   - `<name>_transcript.txt`: a clean, punctuated transcript of the edited version, fixing ASR misspellings such as "MASH.com" for Match.com or "breath crumbing" for breadcrumbing. Step 2 (captions, B-roll) can use it.
10. **Make it editable:** `python3 ~/vidpolish/polish.py cutproject ~/vp/<name> <name> Videos/<name>/<clean file>` (about 45 s; makes `Videos/<name>/editor files/<name>_cut_project.json` plus a quick-seek proxy and the studio-voice audio in `Videos/<name>/editor files/`). Always do this; it's what lets her fix a cut herself.
   Then reply briefly: old length to new length, what was cut, anything she should listen for, and always end with how to fix a cut: **"If anything sounds off, open `Editors/Cut Editor.html` in your video folder (or the ✂ Fix cuts button in the B-roll Editor), pick <name>, fix it, Save, and tell me “render my cuts for <name>”."**

## The Cut Editor (added 2026-10-21)
`Editors/Cut Editor.html` (backup: `_agent/editor-backups/Cut Editor (backup).html`; the B-roll Editor links to it with "✂ Fix cuts", and it links back with "Visuals editor"). Separate from the visuals editor: it works on the RAW video's time. It targets what took her the most time to fix by hand: clipped words, abrupt joins, missed "um"s and "you know"s.
- **Transcript view:** cut words struck through with Claude's reason label; click a word to jump, drag to select, ⌫ cuts, R restores. Cuts/restores use the same natural-break rule as the script (90 ms tail after a phrase, 60 ms lead before the next; the quietest point when there's no pause).
- **Timeline:** waveform in original time with cut parts hatched, or "Hide cut parts (CapCut view)". Drag the pink edge handles, nudge ±10/50 ms (arrow keys), per-join pause −/+ (only real silence from the original), "Snap to break", drag on the waveform to cut or keep any part.
- **Things to check:** auto-flags edges that land mid-sound with a ≥12 dB quieter point within 80 ms (a clipped word, or a sliver of a cut word still playing), leftover fillers (um/uh, you know, I mean, "like,", basically, literally), repeated words, joins with no breath after a sentence or no air at all, and long pauses. Each has ▶ Hear (2 s either side in the edited video), Original, a one-click Fix, and "Sounds fine" (remembered).
- **Playback** stitches the studio-voice audio with Web Audio exactly like the render (same pieces, same 12 ms fades), so what she hears is what she gets; the proxy video follows.
- **Save** writes `keep` (the kept pieces in raw time, 0.1 ms precision), `ignored` and `status:"edited"` into the cut project.

## "Render my cuts for <name>"
If she edited in the Video Editor (`Editors/Video Editor.html`; the visuals project has `cutKeep`), use the glorious-visuals skill's one command, `_agent/render_edits.py <name>`, instead: it renders the cuts and the visuals together. The steps below are for the separate Cut Editor.
1. Read `Videos/<name>/editor files/<name>_cut_project.json` (status should be `edited`). Compare `keep` with `renderedKeep` so you can tell her what changed (which joins moved, words cut or restored).
2. `python3 ~/vidpolish/polish.py fromcut "<her folder>/Videos/<name>/editor files/<name>_cut_project.json" ~/vp/<name>_cut` (sets up a work dir with her exact pieces), then `plan`, `audio`, all `chunk`s, `assemble`, `qa` on that work dir as usual. Her cuts are rendered as-is; don't "improve" them. If qa still finds a leftover filler, mention it rather than cutting it.
3. **If a visuals project exists** (`Videos/<name>/editor files/<name>_broll_project.json`), do this BEFORE step 4 (it needs the old `renderedKeep`): `python3 ~/vidpolish/polish.py remap "<her folder>/Videos/<name>/editor files/<name>_cut_project.json" "<her folder>/Videos/<name>/editor files/<name>_broll_project.json"`. It moves caption words, B-roll slots, cards, zooms and the hook from the old clean timeline to the new one (backup in `_agent/tmp/`), drops caption words that were cut, adds restored words, and flags slots/cards whose edges landed on cut material. Set the visuals project's `video` to the new clean file, tell her what moved or was flagged, and offer to re-render the Glorious version.
4. Deliver the next `<name>_clean_vN.mp4`, move the superseded clean video into `_agent/tmp/`, then refresh the cut project: `python3 ~/vidpolish/polish.py cutproject ~/vp/<name>_cut <name> Videos/<name>/<name>_clean_vN.mp4` (keeps Claude's reasons and first cut; sets `renderedKeep` and status `rendered`).
5. Reply with a short table of what changed and the new length.

## Learning from her cut fixes
She offered to supply before/after examples of her manual fixes. When she has saved edits in the Cut Editor, compare her `keep` with `autoKeep` (Claude's first cut): how much she extended phrase tails or leads, which flagged spots she fixed vs marked "Sounds fine", which words she restored or cut. When the same adjustment repeats (e.g. she always lets sentence ends ring 50 ms longer), report it and ASK before changing `polish.py` defaults or the editor's detector thresholds.

## Editing rules (her approved taste)
- **Cut:** um/uh, filler "you know", "basically", "kind of", "I mean" and "like" (when they're filler), extra "I would say" and "I think" hedges, false starts, half-words, and repeated takes. Keep the LAST clean take.
- **Cut rambling blocks whole (learned from her CapCut pass, 2026-10-20).** She goes further than word-level cleanup:
  - When an explanation gets tangled (restarts, "if you're starting to, if you start…", "this is the situation"), cut the whole muddled stretch and jump straight to the clean version of the idea. Example: "What do I mean? A man is breadcrumbing you. If you're starting to, if you start dating, and this is the situation, one day he is there…" became "He starts dating, and one day he is there…". A rhetorical opener ("What do I mean?") goes too when what follows it is the muddle.
  - Cut restatements that repeat what was just said ("and she said that he's been doing that and she's been a victim" lost "he's been doing that").
  - Cut circular labels that name the topic while describing it ("acts like breadcrumbing, right? He is not committing" became "acts like he's not committing").
  - Test: for each sentence ask "does the viewer lose anything if this is gone?" If not, cut it.
  - Go straight to the call to action (her Cut Editor fix of 1103-1, 2026-11-04): "I'm not gonna wait. I'm not gonna wait. So don't wait." became just "So don't wait." When a line about herself only sets up the line telling the viewer what to do, cut both takes of it, not just the repeat.
- **Her Cut Editor fix of 1103-5 (2026-11-07, approved as defaults):**
  - Cut a self-intro that doesn't hook ("I make content. I create content."): open on who the video is for ("My loves, I talk to women over 40…").
  - Cut a sentence-opening "And" after a pause ("And sometimes before you can leave" became "Sometimes, before you can leave").
  - Never stitch across a hesitation: "dating is… [pause, "you know"] a skill" glued into "dating is a skill" sounds stitched. Keep the take that flows ("dating, it's a skill") even if the grammar is looser.
  - Keep an affirming "Yes," when it opens a clean sentence ("Yes, it can be either abusive…"); only the broken words before it are the false start.
- **Keep:** her personality and hooks, such as rhetorical openers that lead somewhere crisp ("Which ones do we have? Which ones do I recommend?", "And here's the thing"), "So honestly, ladies", "Hands down", "God forbid", short emphasis beats like "Yeah.", wrap-up recaps, and jokes or playful rephrasings ("you're not gonna get sex, so you're not gonna get intimacy, or whatever…"). When unsure, keep it and flag it in the cut list.
- **No slivers at word-level cuts (1103-1):** in fast speech, a cut word's edge often leaves a 50–250 ms sliver of it ("ple-" before "pleasant", "your" after "Create", a breath-word before "As a 45-year-old"); she moved those edges to the next word's onset herself. For every word-level cut with no pause around it, check the 10 ms dB profile and put the edge at the quietest point right before the kept word starts. Read the KEPT TEXT for words that crept back (e.g. "women they need to be rescued").
- **Prefer one clean cut over several micro-cuts in one sentence.** Three tiny cuts in the Tinder sentence sounded choppy. If cutting a small stutter ("v- very") would sound worse, leave it in.
- **Don't cut where the grammar would break.** For example, "if you kind of interested" stays rather than becoming "if you interested".
- **Slow or outdoor talk (her Cut Editor fix of IMG_0959, a beach-walk vlog, 2026-11-08: 75 s → 62 s; she said my version "was very weak").** When she talks slowly while walking, cut much harder than for a car take:
  - Dead air inside sentences: she removed every 0.3–1.9 s gap between words ("a date later tonight … and … someone asked me", "I said no … because … sometimes"). No mid-sentence pause survives unless it's a deliberate beat.
  - Drawn-out connectives: cut a trailing "and…", "then…", "now…" or "but I…" when the sentence works without it ("met with someone, walked on the beach together"; "If you don't enjoy your company, chances are…").
  - Lists of what she did: fragment style, drop the repeated "I" ("Got some work done. Worked on my course. Talked to my friends.").
  - Extra alternatives that add nothing: "go for a walk on the beach this morning [or meet for coffee]".
  - Scenic vlog openings: keep at most the first one or two looks at the view at ~1 s. She cut the third (1.9 s after "Such warm water").
  - Target for this kind of take: about 55% of the raw length (she kept 62 s of 111 s). If the kept text still has "and… then… so…" joins, it isn't done.
- **Pauses (approved 2026-10-26 from her CapCut re-cut of 1025-1):** long pauses between thoughts lose viewers: cut thinking pauses to ~0.2 s. Keep only silent reaction beats; if the beat holds a stray sound or throwaway word (the "Next." after "they don't show up in your life" in 1103-1), she cuts it. **Exception, the very end:** no silent hold before the closing kiss or sign-off; keep the "mwah" itself but cut the wait before it (her 1103-5 fix). Keep reaction beats (smile, smirk, gesture after a punchline, e.g. "much better." → smile, "when I was 19." → smirk) and dramatic beats ("until … five in the morning") at their natural ~0.5–0.9 s via `keep_pauses`. Pauses are detected relative to the background noise (car hum sits ~-35 dB, above the old fixed -42 dB that let 1–1.3 s pauses through): 6 dB over the local background, capped at -34 dB (2026-11-07; at +4 dB, -38 dB room tone in 1103-5 kept a 0.77 s gap). After a cut word, the next piece starts at the kept word's onset, skipping a breath left between (1103-5: 0.56 s of breath after a cut "Um"). Still read the KEPT TEXT and check after each cut filler that no breath is left. Since 2026-11-08 (IMG_0959): a word timestamp in the last 0.3 s of a pause no longer blocks the squeeze (slow, noisy speech gets early ASR timestamps); the next piece starts 40 ms before it so a quiet k/t/s onset survives. Before a cut word, the piece ends 0.18 s after the kept word fades (a word's end time runs to the next word, so noise used to ride up to the cut).
- **Pause squeezing:** dead air is squeezed to a short breath (`max_pause`), but the script still extends phrase edges until the voice fades, so words aren't clipped. Don't tighten the voice-fade padding; she complained about clipped words. Fixing clipped words, abrupt joins and missed fillers by hand used to take her the most time; that's what the Cut Editor is for.
- **Speed:** keep normal speed. She speeds up manually in CapCut when she wants to.

## Audio rules
- **Studio voice:** 85 Hz high-pass, RNNoise at mix 0.85, -3 dB at 250 Hz, +3.5 dB at 3.2 kHz, +4 dB high shelf at 6.5 kHz, 3:1 compression, de-esser, then two-pass loudnorm to -14 LUFS. Her raw car audio sits around -35 LUFS, so the result is much louder; that's expected.
- **Metadata:** the script strips all metadata, including the iPhone's GPS location. Keep it that way.

## If she asks for zooms here anyway
Set `"zoom": true`. It's 1.22x with a 0.7-second eased ramp, toggling at a cut no more than every 8–10 seconds, anchored at her face and chest so the ceiling gets cropped. Never zoom on the frame center, and never use `iw/ih` in the crop expression (ffmpeg 4.4 keeps the first frame's size, which pins the zoom to the top-left corner; that was the v3 bug).

## Learning from her own edits
When she drops a version she finished herself (e.g. "Edited-by-Maria.mov"), compare it to the delivered one:
- Transcribe both, diff the word sequences (difflib) to find her content cuts.
- Compare durations of long matched passages and cross-correlate audio envelopes over a range of time-scale factors to detect a speed change.
- Compare quiet time and the count of pauses over 0.15 s to detect pause tightening.
- Look at a contact sheet for visual changes, and check loudness with ebur128.
Then report what she changed and ASK which changes should become the standard before baking them into `polish.py` or this skill. Some of her manual steps (like a 1.1x speed-up) are per-video choices, not defaults. When a change is adopted, back up the old script as `_agent/polish_before_<date>.py`, note the change in VERSION.txt and propose an update to this skill.

## The script (fallback when `_agent/polish.py` is missing)
Write this verbatim to `~/vidpolish/polish.py` with `mkdir -p ~/vidpolish && cat > ~/vidpolish/polish.py <<'PYEOF'` … `PYEOF`. It still contains the hook/card/zoom code for step-2 or on-request use; it stays dormant unless edits.json asks for it. If `Editors/Cut Editor.html` is missing from her folder, copy `_agent/editor-backups/Cut Editor (backup).html` back.

```python
#!/usr/bin/env python3
"""Talking-head video polisher. Stages (each fits in one 3-minute shell call):
  setup | transcribe SRC WD | plan WD | audio WD | chunk WD N | assemble WD OUT | qa WD OUT
  Cut Editor round trip: cutproject WD NAME [CLEAN] | fromcut PROJECT WD | remap PROJECT BROLLPROJECT | proxy WD NAME | voice WD
WD = work dir (outside the user's folder). Edits are decided by Claude in WD/edits.json
(delete_words items may carry a reason: [a,b,"filler"|"restart"|"ramble"|"trim"]) or come from her Cut Editor ("keep" pieces)."""
import sys, os, json, re, subprocess, math
HOME=os.path.expanduser("~"); MODEL=f"{HOME}/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/"
RNN=f"{HOME}/vidpolish/sh.rnnn"
FONT=f"{HOME}/Desktop/AI agent video edit/_agent/fonts/Poppins-ExtraBold.ttf"   # legacy cards only (was Linux Poppins-Bold)
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

DEFAULT_TOOLS=f"{HOME}/Desktop/AI agent video edit/_agent"   # agent files (was _tools until 2026-10-27)
MODEL_NAME="sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
def setup(tools=None):
    """Fast path: install from the saved _agent folder on the user's Mac (seconds, no downloads).
    Slow path (no _agent): download from PyPI/GitHub. `setup --refresh` re-downloads and re-saves _agent."""
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
        open(f"{tools}/VERSION.txt","w").write(f"saved {datetime.date.today()} | sherpa-onnx {sherpa_onnx.__version__} | ASR {MODEL_NAME} | RNNoise sh.rnnn\nAgent files: don't delete this _agent folder (setup --refresh re-downloads the models and re-saves it).\n")
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
    if dur>t+0.05: regs.append((max(0,t-0.05),dur))
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

def db10(wav):
    """Loudness every 10 ms (dB RMS). Same measure the editor uses for its smart cuts."""
    import numpy as np, soundfile as sf
    A,sr=sf.read(wav,dtype="float32")
    if A.ndim>1: A=A.mean(1)
    hop=sr//100; fr=A[:len(A)//hop*hop].reshape(-1,hop)
    return 20*np.log10(np.sqrt((fr**2).mean(1))+1e-9)

def pause_level(db):
    """Per-10ms pause level: 6 dB over the local background (was 4 until 2026-11-07: -38 dB room tone in 1103-5 read as sound) (15th percentile over +-5 s), clamped to -42..-34 dB (was -32: in the noisy 1103-2 take +6 dB then reached soft words)
    (soft speech sits around -25..-30 dB, so a higher cap squeezed real words away).
    Car hum sits around -35 dB, so the old fixed -42 dB never saw her thinking pauses (her CapCut re-cut of 1025-1, 2026-10-26).
    Returns (smoothed level, threshold); the 50 ms median keeps single hum spikes from splitting a pause."""
    import numpy as np
    n=len(db); pts=np.arange(0,n,50)
    fl=np.array([np.percentile(db[max(0,i-500):min(n,i+500)],15) for i in pts])
    th=np.clip(np.interp(np.arange(n),pts,fl)+6,-42,-34)
    sm=np.median(np.lib.stride_tricks.sliding_window_view(np.pad(db,2,mode="edge"),5),axis=1)
    return sm,th

def merge_keep(keep,dur):
    segs=sorted([[max(0.0,float(k[0])),min(dur,float(k[1]))] for k in keep],key=lambda g:g[0]); out=[]
    for s,e in segs:
        if e-s<0.03: continue
        if out and s<=out[-1][1]+0.001: out[-1][1]=max(out[-1][1],e)
        else: out.append([s,e])
    return [{"s":s,"e":e} for s,e in out]

def del_ranges(E): return [(d[0],d[1]) for d in E.get("delete_words",[])]

def auto_segs(W,dur,E,db,fps):
    import numpy as np
    sm,th=pause_level(db); ix=lambda t: min(len(db)-1,max(0,int(t*100)))
    lv=lambda t: sm[ix(t)]; quiet=lambda t: sm[ix(t)]<th[ix(t)]
    KP=E.get("keep_pauses",[])   # [[t1,t2],...] raw-time pauses Claude keeps whole: a smile, smirk or gesture, or a deliberate beat
    DEL=set()
    for a,b in del_ranges(E): DEL.update(range(a,b+1))
    WS=[w["s"] for i,w in enumerate(W) if i not in DEL]   # a quiet run with a word starting inside it is soft speech, not a pause
    segs=[]
    for i,w in enumerate(W):
        if i in DEL: continue
        if segs and segs[-1]["last"]==i-1 and w["s"]-W[i-1]["e"]<0.45: segs[-1].update(e=w["e"],last=i)
        else: segs.append({"s":w["s"],"e":w["e"],"first":i,"last":i})
    for g in segs:   # base breathing room around each phrase
        i0,i1=g["first"],g["last"]
        lo=W[i0-1]["e"]+0.02 if i0>0 else 0; hi=W[i1+1]["s"]-0.04 if i1+1<len(W) else dur
        g["s"]=max(lo,g["s"]-0.12); g["e"]=min(hi,g["e"]+0.15)
    for g in segs:   # extend edges until the voice actually fades (prevents clipped words)
        i0,i1=g["first"],g["last"]; lim=W[i1+1]["s"]-0.03 if i1+1<len(W) else dur
        t=g["e"]
        while t<lim and not quiet(t): t+=0.01
        g["e"]=min(lim,t+0.12); lo=W[i0-1]["s"]+0.15 if i0>0 else 0; t=g["s"]
        while t>lo and not quiet(t-0.01): t-=0.01
        g["s"]=max(lo,t-0.08)
        if i0>0 and i0-1 in DEL:   # after a cut word: start at the kept word's onset, skipping a breath or noise left between (her 1103-5 fix)
            k0,k1=ix(max(lo,W[i0]["s"]-0.6)),ix(W[i0]["s"]+0.1); q=0; onset=None
            for j in range(k0,k1):
                q=q+1 if sm[j]<th[j] else 0
                if q>=8: onset=j+1   # end of the last quiet run of >=80 ms before the word
            if onset is not None: g["s"]=max(g["s"],onset/100-0.08)
        if i1+1<len(W) and i1+1 in DEL:   # before a cut word: end where the kept word fades (her IMG_0959 fix: a word's end time runs to the next word, so wave noise rode to the cut)
            k0,k1=ix(W[i1]["s"]+0.12),ix(g["e"]); q=0
            for j in range(k0,k1):
                q=q+1 if sm[j]<th[j] else 0
                if q>=15: g["e"]=min(g["e"],(j-14)/100+0.18); break   # 150 ms of quiet; 0.18 s tail keeps a soft t/s ending
    for k in range(1,len(segs)):
        if segs[k]["s"]<segs[k-1]["e"]: segs[k]["s"]=segs[k-1]["e"]
    for a,b in KP:   # a kept pause between two phrases: join them so the whole beat stays
        for k in range(len(segs)-1,0,-1):
            if segs[k-1]["e"]<=b and segs[k]["s"]>=a and segs[k]["s"]-segs[k-1]["e"]<3 and segs[k]["first"]==segs[k-1]["last"]+1: segs[k-1].update(e=segs[k]["e"],last=segs[k]["last"]); del segs[k]
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
    MP=E.get("max_pause",0.2)   # her CapCut edit: dead air squeezed to a short breath everywhere
    if MP:
        o2=[]
        for g in out:
            x,y=g["s"],g["e"]; q=[quiet(t) for t in np.arange(x,y,0.01)]; runs=[]; i=0
            while i<len(q):
                if q[i]:
                    j=i
                    while j<len(q) and q[j]: j+=1
                    runs.append((x+i*0.01,x+j*0.01)); i=j
                else: i+=1
            pieces=[[x,y]]
            for qa_,qb_ in runs:
                # a word starting well inside the run is soft speech: leave it. One in the last 0.3 s is usually an early ASR timestamp
                # (slow, noisy speech in IMG_0959 kept 0.4-0.8 s pauses this way), so squeeze it but start 40 ms before that timestamp
                if qb_-qa_<MP or any(qa_<b and qb_>a for a,b in KP) or any(qa_+0.03<w<qb_-0.3 for w in WS): continue
                lead=min([qb_-0.08]+[w-0.04 for w in WS if qa_+0.03<w<qb_])
                # 0.12 s of tail after the voice fades, 0.08 s of lead-in: ~0.2 s thinking pause, like her CapCut re-cut
                if qa_<=x+0.011: pieces[-1][0]=max(pieces[-1][0],lead)
                elif qb_>=y-0.011: pieces[-1][1]=min(pieces[-1][1],qa_+0.12)
                else: pieces[-1][1]=qa_+0.12; pieces.append([lead,y])
            o2+=[{"s":u,"e":v} for u,v in pieces if v-u>0.05]
        out=o2
    F=1/fps
    for g in out: g["s"]=round(g["s"]/F)*F; g["e"]=round(g["e"]/F)*F
    return [g for g in out if g["e"]>g["s"]]

def plan(wd):
    import numpy as np
    M=J(f"{wd}/meta.json"); D=J(f"{wd}/words.json"); E=J(f"{wd}/edits.json"); W=D["words"]; dur=D["dur"]
    if E.get("keep"):   # her cuts from the Cut Editor: rendered exactly as she set them
        segs=merge_keep(E["keep"],dur); print(f"using her cuts from the Cut Editor ({len(segs)} pieces)")
    else:
        segs=auto_segs(W,dur,E,db10(f"{wd}/a16.wav"),M["fps"])
    inside=lambda t: any(g["s"]<=t<g["e"] for g in segs)
    DEL=set(i for i,w in enumerate(W) if not inside((w["s"]+min(w["e"],w["s"]+0.6))/2))
    shh=M["h"]; sw=M["w"]
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
    if not E.get("zoom",False): z=[0]*len(segs)   # cleanup pass: no zooms unless asked (visuals are a later step)
    events=[]
    for c in E.get("cards",[]): events.append(dict(c,t=m(W[c["word"]]["s"])))
    # chunks of ~35s output so each render fits in one shell call
    chunks=[]; a=0
    for k in range(1,len(segs)+1):
        if k==len(segs) or off[k]-off[a]>=35: chunks.append((a,k)); a=k
    anc=[None]*len(segs); ovy={}
    if any(z) or E.get("hook") or events:   # legacy overlays/zooms only: find the face
        import cv2
        c1=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
        c2=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_profileface.xml")
        cap=cv2.VideoCapture(M["src"]); FC=[]; q=540/sw
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
        k=0
        while k<len(segs):
            j=k
            while j+1<len(segs) and z[j+1]==z[k]: j+=1
            pts=[FC[i] for i in range(k,j+1) if FC[i] and FC[i][1]<shh*0.55] or [[gx,gy,gh]]
            cx,cy,_=np.median(np.array(pts),axis=0)
            for i in range(k,j+1): anc[i]=(float(cx),float(min(shh*0.8,cy+1.1*gh)))
            k=j+1
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
            ft,fb=face_band(t0,t1); mg=30*sc; safe=150*sc
            if default+oh+mg<=ft: return int(default)
            if ft-oh-mg>=safe: return int(ft-oh-mg)
            return int(min(shh-0.25*shh-oh,fb+mg))
        if E.get("hook"): ovy["hook"]=place(0.15,2.9,370*sc,230*sc)
        for n_,e in enumerate(events): ovy[f"card{n_}"]=place(e["t"]-0.1,e["t"]+4.2,270*sc,300*sc)
    P={"segs":segs,"off":off,"z":z,"anc":anc,"events":events,"hook":E.get("hook"),"chunks":chunks,"ovy":ovy,"speed":float(E.get("speed",1.0))}
    W_(f"{wd}/plan.json",P)
    if E.get("hook") or events: make_cards(wd,M,P)
    L=off[-1]/P["speed"]; lines=[f"Original {int(dur//60)}:{dur%60:04.1f} -> edited {int(L//60)}:{L%60:04.1f}"+(f" (at {P['speed']}x)" if P["speed"]!=1 else ""),"Removed (timestamps in the original):"]
    i=0
    while i<len(W):   # list every removed run of words (works for both auto and her cuts)
        if i in DEL:
            j=i
            while j+1<len(W) and j+1 in DEL: j+=1
            lines.append(f"{int(W[i]['s']//60)}:{W[i]['s']%60:05.2f}  \"{' '.join(W[x]['w'] for x in range(i,j+1))}\""); i=j+1
        else: i+=1
    open(f"{wd}/cutlist.txt","w").write("\n".join(lines)+"\n")
    print(f"{len(segs)} segments, {off[-1]:.2f}s of {dur:.1f}s (expected frames {round(off[-1]*M['fps'])}); chunks={len(chunks)}")
    print("KEPT TEXT:"," ".join(w["w"] for i,w in enumerate(W) if i not in DEL))

def pauses(wd):
    """Every pause >=0.4s between two kept words (raw time), with a frame strip (WD/pauses.jpg, 3 frames per pause) so Claude
    can spot a smile, smirk or gesture and keep that beat via edits.json "keep_pauses". Thinking pauses stay squeezed."""
    import numpy as np, cv2
    M=J(f"{wd}/meta.json"); D=J(f"{wd}/words.json"); P=J(f"{wd}/plan.json"); W=D["words"]; db=db10(f"{wd}/a16.wav"); sm,th=pause_level(db)
    inside=lambda t: any(g["s"]<=t<g["e"] for g in P["segs"]); kept=[i for i,w in enumerate(W) if inside((w["s"]+min(w["e"],w["s"]+0.6))/2)]
    out=[]
    for i,j in zip(kept,kept[1:]):
        if j!=i+1: continue
        a,b=W[i]["s"]+0.1,W[j]["s"]; best=(0,0,0); st=None
        for k in range(int(a*100),int(b*100)+1):
            q=k<int(b*100) and sm[min(k,len(sm)-1)]<th[min(k,len(th)-1)]
            if q and st is None: st=k
            if not q and st is not None:
                if k-st>best[0]: best=(k-st,st,k)
                st=None
        if best[0]>=40: out.append((best[1]/100,best[2]/100,W[i]["w"],W[j]["w"]))
    cap=cv2.VideoCapture(M["src"]); tiles=[]
    for n,(a,b,w1,w2) in enumerate(out):
        print(f"#{n:2d} {a:7.2f}-{b:7.2f} ({b-a:.2f}s)  {w1} | {w2}")
        row=[]
        for t in (a+0.05,(a+b)/2,b-0.05):
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,f=cap.read()
            f=cv2.resize(f,(120,int(120*f.shape[0]/f.shape[1]))) if ok else np.zeros((213,120,3),np.uint8); row.append(f)
        r=np.hstack(row); cv2.putText(r,f"#{n}",(4,18),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2); tiles.append(r)
    if tiles:
        cols=4; tiles+=[np.zeros_like(tiles[0])]*((-len(tiles))%cols)
        cv2.imwrite(f"{wd}/pauses.jpg",np.vstack([np.hstack(tiles[i:i+cols]) for i in range(0,len(tiles),cols)]))
        print("frame strip:",f"{wd}/pauses.jpg")

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


# "studio voice": rumble HPF, RNN denoise, de-box, presence, air, compression, de-ess (loudness -14 LUFS is set after cutting)
STUDIO="highpass=f=85:poles=2,arnndn=m={rnn}:mix=0.85,equalizer=f=250:t=q:w=1.2:g=-3,equalizer=f=3200:t=q:w=1.0:g=3.5,highshelf=f=6500:g=4,acompressor=threshold=-26dB:ratio=3:attack=8:release=120:makeup=4dB:knee=4,deesser=i=0.4"
FADE=0.012   # tiny fade at every cut edge (the Cut Editor preview uses the same)

def voice(wd):
    """Studio voice on the WHOLE raw take, before cutting. The Cut Editor plays this same file, so the preview sounds like the render."""
    M=J(f"{wd}/meta.json"); out=f"{wd}/voice.wav"
    if os.path.exists(out) and os.path.getsize(out)>1000: return out
    rnn=RNN if os.path.exists(RNN) else f"{DEFAULT_TOOLS}/sh.rnnn"
    sh(["ffmpeg","-v","error","-y","-i",M["src"],"-vn","-af","aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono,"+STUDIO.format(rnn=rnn),"-ar","48000","-c:a","pcm_s16le",out])
    return out

def audio(wd):
    M=J(f"{wd}/meta.json"); P=J(f"{wd}/plan.json"); v=voice(wd); f=[]
    for k,g in enumerate(P["segs"]):
        a,b=g["s"],g["e"]; L=b-a; fd=min(FADE,L/3)
        f.append(f"[0:a]atrim=start={a:.5f}:end={b:.5f},asetpts=PTS-STARTPTS,afade=t=in:d={fd:.3f},afade=t=out:st={L-fd:.5f}:d={fd:.3f}[a{k}]")
    f.append("".join(f"[a{k}]" for k in range(len(P["segs"])))+f"concat=n={len(P['segs'])}:v=0:a=1[a]")
    open(f"{wd}/fa.txt","w").write(";".join(f))
    sh(["ffmpeg","-v","error","-y","-i",v,"-/filter_complex",f"{wd}/fa.txt","-map","[a]","-ac","1","-ar","48000",f"{wd}/cut.wav"])
    S=P.get("speed",1.0); pre=f"{wd}/cut.wav"
    if S!=1:   # only when she asks for a speed-up (pitch preserved)
        sh(["ffmpeg","-v","error","-y","-i",pre,"-af",f"atempo={S}",f"{wd}/pre.wav"]); pre=f"{wd}/pre.wav"
    t=subprocess.run(["ffmpeg","-hide_banner","-i",pre,"-af","loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json","-f","null","-"],capture_output=True,text=True).stderr
    j=json.loads(t[t.rindex("{"):t.rindex("}")+1])
    LN=f"loudnorm=I=-14:TP=-1.5:LRA=7:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
    sh(["ffmpeg","-v","error","-y","-i",pre,"-af",LN,"-ar","48000","-c:a","aac","-b:a","192k",f"{wd}/audio.m4a"]); print("audio ok")

def outframes(P,fps): return [round(o*fps) for o in P["off"]]   # cumulative output frame at each segment start

def chunk(wd,n):
    M=J(f"{wd}/meta.json"); P=J(f"{wd}/plan.json"); i0,i1=P["chunks"][n]
    segs,off,z,anc=P["segs"],P["off"],P["z"],P["anc"]; sub=segs[i0:i1]; O=off[i0]; Dd=off[i1]-O
    VW,VH,fps=M["w"],M["h"],M["fps"]; Z=1.22; s=VW/1080; C=outframes(P,fps)
    t0=max(0,sub[0]["s"]-1); f=[]; labs=[]
    for k,g in enumerate(sub):
        gi=i0+k; nk=C[gi+1]-C[gi]
        if nk<=0: continue
        zz=""
        if z[gi] or (gi>0 and z[gi-1]):
            zp=Z if (gi>0 and z[gi-1]) else 1.0; zn=Z if z[gi] else 1.0
            ax,ay=anc[gi] if z[gi] else anc[max(gi-1,0)]
            if zp==zn: ZE=f"{zn}"
            else: X="min(t/0.7,1)"; ZE=f"({zp}+({zn-zp:.4f})*{X}*{X}*(3-2*{X}))"
            # NB: crop x/y must NOT use iw/ih (ffmpeg keeps the first frame's size); fixed-point zoom on the anchor
            zz=(f",scale=w='trunc({VW}*{ZE}/2)*2':h='trunc({VH}*{ZE}/2)*2':eval=frame:flags=bicubic"
                f",crop={VW}:{VH}:x='{ax:.1f}*({ZE}-1)':y='{ay:.1f}*({ZE}-1)'")
        # frame-exact: the source frames nearest the cut, and exactly nk frames so video never drifts from the audio
        st=(round(g["s"]*fps)-0.5)/fps-t0
        f.append(f"[0:v]trim=start={max(0,st):.5f}:end={st+nk/fps:.5f},setpts=N/({fps}*TB){zz},tpad=stop_mode=clone:stop=3,trim=end_frame={nk},setsar=1[v{k}]"); labs.append(f"[v{k}]")
    f.append("".join(labs)+f"concat=n={len(labs)}:v=1:a=0[b0]")
    OV=[]; OY=P.get("ovy",{})
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
    S=P.get("speed",1.0); nfr=round(C[i1]/S)-round(C[i0]/S)
    if S!=1: f.append(f"[{last}]setpts=PTS/{S}[spd]"); last="spd"
    open(f"{wd}/fv{n}.txt","w").write(";".join(f))
    sh(["ffmpeg","-y","-v","error","-ss",f"{t0:.3f}","-t",f"{sub[-1]['e']-t0+0.5:.3f}","-i",M["src"]]+inputs+["-/filter_complex",f"{wd}/fv{n}.txt","-map",f"[{last}]","-an","-c:v","h264_videotoolbox","-b:v","16M","-allow_sw","0","-pix_fmt","yuv420p","-colorspace","bt709","-color_primaries","bt709","-color_trc","bt709","-r",str(fps),"-frames:v",str(nfr),f"{wd}/part_{n:03d}.mp4"])
    print(f"chunk {n}/{len(P['chunks'])-1} ok")

def assemble(wd,out):
    P=J(f"{wd}/plan.json"); M=J(f"{wd}/meta.json")
    with open(f"{wd}/list.txt","w") as f:
        for n in range(len(P["chunks"])): f.write(f"file 'part_{n:03d}.mp4'\n")
    sh(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",f"{wd}/list.txt","-i",f"{wd}/audio.m4a","-map","0:v","-map","1:a","-c","copy","-map_metadata","-1","-movflags","+faststart",out])
    nf=int(subprocess.run(["ffprobe","-v","error","-count_packets","-select_streams","v","-show_entries","stream=nb_read_packets","-of","csv=p=0",out],capture_output=True,text=True).stdout)
    exp=round(outframes(P,M["fps"])[-1]/P.get("speed",1.0))
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
    # dead air the squeeze missed (noisy outdoor audio): >0.45 s mid-sentence or >0.8 s anywhere, in output time
    print("long gaps:",[(round(words[i-1]["s"],1),words[i-1]["w"],words[i]["w"],round(words[i]["s"]-words[i-1]["s"]-0.35,1)) for i in range(1,len(words))
        if words[i]["s"]-words[i-1]["s"]-0.35>(0.8 if words[i-1]["w"][-1:] in ".?!" else 0.45)])
    off,z=P["off"],P["z"]; ts=[off[k]+1.5 for k in range(1,len(z)) if z[k] and not z[k-1]]
    ts+=[e["t"]+1 for e in P["events"]]+([1.5] if P["hook"] else [])
    ts=sorted(t/P.get("speed",1.0) for t in ts if t<off[-1])[:12]
    if not ts: L=off[-1]/P.get("speed",1.0); ts=[L*(i+0.5)/8 for i in range(8)]   # no overlays: sample evenly
    sel="+".join(f"eq(n\\,{int(t*fps)})" for t in ts)
    sh(["ffmpeg","-v","error","-y","-i",out,"-vf",f"select='{sel}',scale=200:-1,tile={len(ts)}x1","-frames:v","1",os.path.join(os.path.dirname(out),"_qa_frames.jpg")])
    print("contact sheet: _qa_frames.jpg")

# ---------------- Cut Editor round trip ----------------
VIDDIR=os.path.dirname(DEFAULT_TOOLS)   # her "AI agent video edit" folder
def edfiles(name):   # one folder per video: Videos/<name>/ (deliverables) and Videos/<name>/editor files/ (projects, proxy, voice)
    d=f"{VIDDIR}/Videos/{name}/editor files"; os.makedirs(d,exist_ok=True); return d
FILLERS={"um","uh","umm","uhm","hmm","mm","er","ah","erm"}
FILLER_PHRASES={"you know","i mean","like","basically","kind of","sort of","you see","right","okay so","so yeah"}
def _norm(w): return re.sub(r"[^a-z']","",w.lower())

def cut_reason(W,a,b):
    """Label for the Cut Editor (Claude should pass its own reason in edits.json; this is the fallback)."""
    t=[_norm(W[i]["w"]) for i in range(a,b+1)]; txt=" ".join(t)
    nxt=[_norm(W[i]["w"]) for i in range(b+1,min(len(W),b+1+max(3,len(t))))]
    soft={"you","know","like","kind","of","just","i","mean","so","basically","uh","um","and","yeah","right","sort"}
    strong={"um","uh","umm","uhm","hmm","mm","er","ah","know","like","basically","mean"}
    if all(x in FILLERS for x in t) or txt in FILLER_PHRASES or (len(t)<=4 and all(x in soft for x in t) and any(x in strong for x in t)): return "filler"
    if t==nxt[:len(t)]: return "repeat"
    if len(t)>=6: return "ramble"
    if t[0] in nxt[:3] or (len(t)>1 and t[1] in nxt[:3]): return "restart"
    if any(len(x)<=2 and x not in ("a","i","is","it","to","so","or","of","in","we","he","me","my","no","on","at","as","be","do","if","an","up","us") for x in t): return "stumble"
    return "trim"

def proxy(wd,name):
    """Small, quick-to-seek copy of the raw video for the Cut Editor (keyframe every 0.2s, no audio)."""
    M=J(f"{wd}/meta.json"); cd=edfiles(name); out=f"{cd}/proxy.mp4"
    sh(["ffmpeg","-v","error","-y","-i",M["src"],"-an","-vf","scale=540:-2","-c:v","libx264","-preset","veryfast","-tune","fastdecode","-crf","27","-g","6","-keyint_min","6","-sc_threshold","0","-pix_fmt","yuv420p","-movflags","+faststart",out])
    print("proxy ok",out)

def cutproject(wd,name,clean=None):
    """Write Videos/<name>/editor files/<name>_cut_project.json for the Cut Editor (raw-time words, loudness, Claude's cuts with reasons, the kept pieces)."""
    import shutil
    M=J(f"{wd}/meta.json"); D=J(f"{wd}/words.json"); P=J(f"{wd}/plan.json")
    E=J(f"{wd}/edits.json") if os.path.exists(f"{wd}/edits.json") else {}
    W=D["words"]; cd=edfiles(name)
    shutil.copy(voice(wd),f"{cd}/voice.wav")
    if not os.path.exists(f"{cd}/proxy.mp4"): proxy(wd,name)
    pj=f"{cd}/{name}_cut_project.json"; old=J(pj) if os.path.exists(pj) else {}
    db=db10(f"{wd}/a16.wav") if os.path.exists(f"{wd}/a16.wav") else old["db"]; keep=[[round(g["s"],4),round(g["e"],4)] for g in P["segs"]]
    cuts=[]
    for d in E.get("delete_words",[]):
        a,b=d[0],d[1]; cuts.append({"a":a,"b":b,"why":d[2] if len(d)>2 else cut_reason(W,a,b)})
    if E.get("keep"): cuts=old.get("cuts",[])   # re-render of her cuts: keep Claude's original reasons
    proj={"version":1,"kind":"cut","name":name,"src":os.path.relpath(M["src"],VIDDIR),"proxy":f"Videos/{name}/editor files/proxy.mp4","voice":f"Videos/{name}/editor files/voice.wav",
          "clean":clean or old.get("clean") or f"Videos/{name}/{name}_clean.mp4","w":M["w"],"h":M["h"],"fps":M["fps"],"dur":D["dur"],
          "words":[{"w":w["w"],"s":round(w["s"],3),"e":round(w["e"],3)} for w in W],"db":[int(round(max(-90,x))) for x in db] if not isinstance(db,list) else db,
          "cuts":cuts,"keep":keep,"autoKeep":old.get("autoKeep") or keep,"renderedKeep":keep,"ignored":old.get("ignored",[]),
          "status":"rendered","savedAt":None}
    W_(pj,proj); print("cut project:",pj,f"({len(keep)} pieces, {len(cuts)} cuts)")

def fromcut(projpath,wd):
    """Set up a work dir that renders her saved cuts exactly (then: plan, audio, chunk..., assemble, qa)."""
    import shutil
    P=J(projpath); src=os.path.join(VIDDIR,P["src"]); os.makedirs(wd,exist_ok=True); w,h,fps,dur=probe(src)
    W_(f"{wd}/meta.json",{"src":src,"w":w,"h":h,"fps":fps,"dur":dur})
    W_(f"{wd}/words.json",{"words":P["words"],"silences":[],"dur":P["dur"]})
    vp=os.path.join(VIDDIR,P.get("voice",""))
    if os.path.isfile(vp): shutil.copy(vp,f"{wd}/voice.wav")
    W_(f"{wd}/edits.json",{"keep":P["keep"]})
    old,new=P.get("renderedKeep") or [],P["keep"]
    sg=lambda L:set((round(a,2),round(b,2)) for a,b in L)
    print(f"her cuts: {len(new)} pieces, {sum(b-a for a,b in new):.2f}s (last render {sum(b-a for a,b in old):.2f}s); pieces changed since the last render: {len(sg(new)-sg(old))}")

def _offs(L):
    o=[0.0]
    for a,b in L: o.append(o[-1]+b-a)
    return o
def _c2r(t,L,o):
    for k,(a,b) in enumerate(L):
        if t<o[k+1] or k==len(L)-1: return a+min(max(t-o[k],0),b-a)
def _r2c(x,L,o):
    for k,(a,b) in enumerate(L):
        if x<a: return o[k],False
        if x<b: return o[k]+x-a,True
    return o[-1],False

def remap(projpath,brollpath):
    """After a re-cut: move the visuals (captions words, B-roll, cards, zooms, hook) from the old clean timeline to the new one."""
    import shutil, time
    P=J(projpath); B=J(brollpath); old,new=B.get("cutKeep") or P["renderedKeep"],P["keep"]; oo,on=_offs(old),_offs(new)
    if len(old)==len(new) and all(abs(x-y)<5e-4 for o,n in zip(old,new) for x,y in zip(o,n)):   # the Video Editor already laid the visuals out on this cut
        P["renderedKeep"]=new; W_(projpath,P); print("visuals already match this cut (edited in the Video Editor); nothing to move"); return
    shutil.copy(brollpath,f"{DEFAULT_TOOLS}/tmp/{os.path.basename(brollpath)[:-5]}_before_recut_{int(time.time())}.json")
    def mp(t): return _r2c(_c2r(t,old,oo),new,on)
    inold=lambda x: any(a<=x<b for a,b in old); innew=lambda x: any(a<=x<b for a,b in new)
    words=[]; lost=[]
    for w in B["words"]:
        mid=_c2r((w["s"]+w["e"])/2,old,oo)
        if not innew(mid): lost.append(w["w"]+(f" ({w['emph']})" if w.get("emph") else "")); continue
        s,_=mp(w["s"]); e,_=mp(w["e"]); words.append(dict(w,s=round(s,3),e=round(max(e,s+0.05),3)))
    added=[]
    for w in P["words"]:
        mid=(w["s"]+min(w["e"],w["s"]+0.6))/2
        if innew(mid) and not inold(mid):
            s,_=_r2c(max(w["s"],mid-0.3),new,on); e,_=_r2c(min(w["e"],mid+0.3),new,on)
            words.append({"w":w["w"],"s":round(s,3),"e":round(max(e,s+0.05),3)}); added.append(w["w"])
    B["words"]=sorted(words,key=lambda w:w["s"]); flags=[]
    for key in ("slots","tiles","zooms"):
        keepi=[]
        for it in B.get(key,[]):
            a,oka=mp(it["a"]); b,okb=mp(it["b"])
            if b-a<0.15: flags.append(f"{key[:-1]} at {it['a']:.1f}s was on cut material and was removed"); continue
            if not (oka and okb) and key!="zooms": flags.append(f"{key[:-1]} '{it.get('clip') or it.get('text') or ''}' now {a:.1f}-{b:.1f}s (edge was on a cut, check it)")
            keepi.append(dict(it,a=round(a,3),b=round(b,3)))
        B[key]=keepi
    if B.get("hook"): B["hook"]["a"]=round(mp(B["hook"]["a"])[0],3); B["hook"]["b"]=round(mp(B["hook"]["b"])[0],3)
    if B.get("whipAt"): B["whipAt"]=[round(mp(t)[0],3) for t in B["whipAt"]]
    B["duration"]=round(on[-1],3); B["status"]="edited"; B["cutKeep"]=new
    W_(brollpath,B); P["renderedKeep"]=new; W_(projpath,P)
    print(f"visuals moved to the new cut ({oo[-1]:.2f}s -> {on[-1]:.2f}s). caption words removed: {lost or 'none'}; added: {added or 'none'}")
    for x in flags: print(" !",x)

if __name__=="__main__":
    a=sys.argv[1:]; cmd=a[0]
    if cmd=="setup": setup(a[1] if len(a)>1 else None)
    elif cmd=="transcribe": transcribe(a[1],a[2])
    elif cmd=="plan": plan(a[1])
    elif cmd=="pauses": pauses(a[1])
    elif cmd=="voice": print(voice(a[1]))
    elif cmd=="audio": audio(a[1])
    elif cmd=="chunk": chunk(a[1],int(a[2]))
    elif cmd=="assemble": assemble(a[1],a[2])
    elif cmd=="qa": qa(a[1],a[2])
    elif cmd=="proxy": proxy(a[1],a[2])
    elif cmd=="cutproject": cutproject(a[1],a[2],a[3] if len(a)>3 else None)
    elif cmd=="fromcut": fromcut(a[1],a[2])
    elif cmd=="remap": remap(a[1],a[2])
```

Tested 2026-10-20/21 on the "breadcrumbing" video: 2:43 raw → 1:41.7 clean (3,050 frames, OK). The Cut Editor round trip was tested on 2026-10-21: an editor edit with 13 ms / 35 ms edge moves rendered to exactly the expected 3,049 frames, frame-identical to the clean video elsewhere, audio within half a frame.

macOS port (2026-10-25): the script above is the Mac version (ffmpeg 9 via Homebrew `ffmpeg-full`). It uses `-/filter_complex FILE` instead of the removed `-filter_complex_script`, so it needs ffmpeg 7 or newer. The final render (`chunk`) encodes with `h264_videotoolbox -b:v 16M` (Apple Silicon only): 2.6x faster than libx264 CRF 18 for 0.65 VMAF points; to go back, swap in `"libx264","-preset","medium","-crf","18"`. Smoke-tested on a 30 s piece of 1025-1: 718/718 frames OK, -14.1 LUFS.