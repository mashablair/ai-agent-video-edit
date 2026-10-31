---
name: "add-broll-to-video"
description: "Add B-roll to Maria's finished talking video in 'AI agent video edit', using ONLY clips from her own 'b-roll collection' library (never stock or online footage). Also re-renders B-roll and caption edits she saved in the B-roll Editor."
---

# Add B-roll to a finished video

Maria drops an already-polished vertical talking video (GG dating or MTT AI content) into `~/Desktop/AI agent video edit`. Add B-roll from HER OWN library so people can watch without full attention. Deliver the finished video. Don't ask her to approve a plan first.

**Use only clips from her `b-roll collection` library. Never search online, never download stock or third-party footage, and never generate footage.** If the library folder isn't connected, stop and ask her to connect it.

## Where things are (on her Mac, through `device_bash`)
- Videos: `$HOME/mnt/AI agent video edit/`.
  - `_agent/` holds the transcription toolkit (`polish.py`), the caption renderer (`captions.py`), caption fonts (`fonts/` with `fonts.json`) and her saved default caption style (`caption-style.json`, if she saved one).
  - `Editors/B-roll Editor.html` is her timeline editor for B-roll and captions. Never treat it as a video.
- Library: `$HOME/mnt/b-roll collection/`
  - `clips/<id>.mp4` are 1080x1920 muted clips.
  - `_catalog/CATALOG.md` has a theme finder, every clip with what's in it, mood and tags, and a usage log.
  - `_catalog/clips.json` is the same data as JSON. `_catalog/thumbs/<id>.jpg` are thumbnails the editor uses.
  - `_catalog/add_broll.py` is the B-roll render script.
- If either folder isn't connected, ask her to add it with "Add folder" in the Claude desktop app.
- Each `device_bash` call is capped at 180 seconds. Keep work directories in `~/vp/<name>`, never in her folders.
- Deleting in her folders is off by default. Don't leave scratch files there. If something must go, move it into `_agent/tmp/_to_delete/` and tell her.

## Steps
1. **Find the video.** Raw videos are in `Drop raw videos here/`. If several new videos are there, do each one.
2. **Transcribe.** Run `mkdir -p ~/vidpolish && cp "$HOME/mnt/AI agent video edit/_agent/polish.py" ~/vidpolish/ && python3 ~/vidpolish/polish.py setup`, then `python3 ~/vidpolish/polish.py transcribe "<video>" ~/vp/<name>`. You get word timestamps in `~/vp/<name>/words.json` (`{"words":[{w,s,e}]}`).
3. **Look at the video.** Make a contact sheet (one frame every 2–3 seconds, with timestamps), stage it and view it. Note any hook title already on screen, and her gestures.
4. **Read CATALOG.md**, including the usage log. Pick clips whose content matches each line, not just the topic. Literal matches work best:
   - "show off" → sparkly lights
   - "look at the action" → her walking
   - "receiving" → face in the sun
5. **Plan the slots** in `~/vp/<name>/broll.json`:
   `{"src": "<full video path>", "slots": [{"a": start, "b": end, "clip": "<id>", "from": offset_in_clip, "line": "what she says"}]}`
   Rules (approved by Maria):
   - Keep her face on screen for the hook or opening (at least the first 4–10 seconds, and any on-screen hook title), for punchlines and jokes, for her key thesis line, and for the last line through the end.
   - Cover about 30–35% of the runtime, with each slot 2.5–3 seconds long. Start a slot about 0.1 seconds before a word starts, and end it at a phrase boundary.
   - Don't use a clip that's in the most recent usage-log entry, and don't use any clip twice in one video.
   - Avoid clips where her mouth is clearly moving (the B-roll is muted). Never use `photo-me-and-bond` unless she asks.
   - Mixing outfits and days is fine; she approved that.
6. **Render B-roll.** Run `python3 "$HOME/mnt/b-roll collection/_catalog/add_broll.py" chunks ~/vp/<name>` to get N. Then `... chunk ~/vp/<name> i` for each chunk (two per call is fine). Then `... assemble ~/vp/<name> ~/vp/<name>/final.mp4`. The original audio is kept untouched.
7. **Captions (only if enabled).** Write the project file from step 9 first, to `~/vp/<name>/project.json`. For a new video, set its `captions` to her default style from `_agent/caption-style.json` with `"enabled": true` and `"start"` set to just after the hook line, if that default file exists. If it doesn't exist, set `{"enabled": false}`. When captions are enabled, burn them on top of the B-roll render with `C="$HOME/mnt/AI agent video edit/_agent/captions.py"`:
   - Once the project file has its words, run `python3 "$HOME/mnt/AI agent video edit/_agent/glorious.py" numbers ~/vp/<name>/project.json` so prices, years and percents she says show as digits ("nine and a half million." -> "$9.5 million."). She approved this on 2026-10-31; don't re-ask. Read its "left as spoken" list and fix any that are prices. The amber accent only shows in the Glorious look; these captions keep their own colors.
   - Run `python3 "$C" chunks <project.json> ~/vp/<name>/final.mp4` to get N.
   - Run `python3 "$C" chunk <project.json> ~/vp/<name>/final.mp4 ~/vp/<name> i` for each chunk. Each takes about 16s per 16s of video.
   - Run `python3 "$C" assemble <project.json> ~/vp/<name>/final.mp4 ~/vp/<name> ~/vp/<name>/final_cap.mp4`. Deliver `final_cap.mp4` instead of `final.mp4`.
   - Ignore "Error opening memory font 'fonts.json'" warnings.
   - Captions sit on top of the B-roll as well. Keep them clear of any on-screen hook title, using the `start` time or the y position.
8. **Check.** Pull one frame from inside each slot plus a face frame into a strip, and include a caption frame if captions are on. Stage it and view it. Confirm the frame count matches the length. Write contact sheets and check strips in `~/vp/<name>`. If one has to be staged, put it in `_agent/tmp/` and move it to `_agent/tmp/_to_delete/` afterwards.
9. **Deliver** to `AI agent video edit/Videos/<name>/`:
   - `<name>_broll.mp4`. If that exists, add _v2, _v3 and so on; never overwrite.
   - `<name>_broll_list.txt` listing each slot as time, clip and line, plus the total B-roll percentage. Add the caption style used, if any.
   - `editor files/<name>_broll_project.json` for the B-roll Editor. Overwriting is fine because this is the live edit file:
     `{"version":1, "video":"<path from her folder, e.g. Drop raw videos here/<file> or Videos/<name>/<name>_clean.mp4>", "duration":<sec>, "fps":<fps>, "rendered":"Videos/<name>/<the mp4 just written>", "status":"rendered", "savedAt":"<ISO time>", "words":[{w,s,e}...], "slots":[...same as broll.json...], "captions":{...}}`
   - Add a line to the usage log in CATALOG.md: `- <date>, <video topic>: clip, clip, ...`
10. **Reply briefly** with a small table of what she says and what's on screen, where her face stays, and anything to check (for example, "if it feels busy, drop X first"). Mention she can open `Editors/B-roll Editor.html` in Chrome to tweak the B-roll or captions.

## Rendering her edits from the B-roll Editor
When she says something like "render my B-roll edits for <name>" (or caption edits):
1. Read `Videos/<name>/editor files/<name>_broll_project.json`. Its `status` should be `edited`, which means she clicked Save in the editor. If it says `rendered`, tell her nothing new was saved.
2. Write `~/vp/<name>/broll.json` as `{"src": "<full expanded path to the video in AI agent video edit>", "slots": <project slots>}`.
   - Her edits are the plan. Don't re-pick clips, move slots, change caption style or re-transcribe.
   - Words she fixed or hid in the editor are already in the project's `words`. Use them as they are.
   - Just render, and point out any rule warnings in the reply.
3. Render B-roll (step 6), then captions from the project file if `captions.enabled` is true (step 7). Then check and deliver as in steps 8–9: the next free `<name>_broll_vN.mp4` and a matching `<name>_broll_vN_list.txt`. Then update the project file to `status: "rendered"` and `rendered: "edited/<new mp4>"`.
4. In the usage log, replace that video's line with the final clip list instead of adding a second line.
5. Reply with what changed compared with the previous version (clips swapped, added, removed or retimed, caption style) and the new B-roll percentage.