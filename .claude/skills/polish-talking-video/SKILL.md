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

## Where things are (this Mac)
- Her folder: `~/Desktop/AI agent video edit` (run commands from there). Raw videos: `Drop raw videos here/` (never touch them). Deliverables: `Videos/<name>/`.
- Work dirs: `~/vp/<name>`, never in her folder.
- Python: `PY=~/vidpolish/.venv/bin/python`. Script: `_agent/polish.py` (call it from there; `~/vidpolish/polish.py` is a copy: after changing the script, `cp _agent/polish.py ~/vidpolish/`). Speech model, `sh.rnnn` and fonts are already installed; never run `polish.py setup` here (its wheels are Linux-only).
- Look at images (frame strips, contact sheets) with the Read tool.
- No time limits: run a whole stage chain in one command; long renders can run in the background.

## Steps
In the commands, `PY=~/vidpolish/.venv/bin/python`, `POL=_agent/polish.py`, `WD=~/vp/<name>`.
0. **Name the video** (her rule, 2026-11-13): `<name>` = raw stem + a short topic you take from the transcript, e.g. `1108-4 stop chasing` (2-5 plain words; no apostrophes, quotes, colons or slashes). Use the full `<name>` for the folder `Videos/<name>/`, the videos (`<name>_clean.mp4`, `_glorious`, `_cover`) and `<name>_transcript.txt`; every other file (cut/broll projects, cutlist, list .txt, thumbnails) is prefixed with just `<code>` = the raw stem (`1108-4_cut_project.json`, her rule 2026-11-13; polish.py, render_edits.py and thumbnail.py do this themselves). Quote every path. Transcribe first if you need the topic, then name it before `deliver`.
1. **Transcribe.** `$PY $POL transcribe "Drop raw videos here/<file>" $WD`. It prints an indexed word list (`idx:word@start [gap]`) plus FILLERS and REPEATS lists. Parakeet DOES transcribe "uh/um". With several new videos, transcribe them all first, then decide each one's cuts.
2. **Decide the cuts yourself** by reading the transcript like a viewer (see "Editing rules"), then write `$WD/edits.json`:
   ```json
   {"delete_words": [[a,b,"filler"], [c,d,"restart"], ...],
    "delete_times": [[t1,t2], ...],
    "keep_pauses": [[t1,t2], ...],
    "max_pause": 0.2}
   ```
   - `delete_words` are inclusive word-index ranges. Give each a reason, shown as a label in her Cut Editor: `filler` (um/uh/you know/like/basically), `restart` (false start, she re-says it), `repeat` (doubled word or phrase), `ramble` (whole muddled stretch), `stumble` (half-word, slip), `trim` (anything else).
   - `delete_times` are raw-time cuts for fillers, slivers or dead air the word list doesn't cover.
   - `keep_pauses` are raw ranges of reaction beats to keep (step 3).
   - `max_pause` (default 0.2 s) squeezes dead air to a short breath, matching her own CapCut pass.
   - `noise` (optional): `off` / `standard` / `strong` background-noise remover. Leave it out: the `audio` step auto-picks (see "Audio rules").
   - Leave out `hook`, `cards`, `zoom` and `speed`. The script defaults to no overlays, no zoom and normal speed. Add one only if she explicitly asks for it on that video (`"zoom": true` gives the face-anchored 1.22x zooms; `"speed": 1.1` speeds up with pitch preserved).
3. **Plan and look at the pauses.** `$PY $POL plan $WD`, then `$PY $POL pauses $WD` and view `$WD/pauses.jpg` (3 frames per pause >=0.4 s, numbered as in the printed list). Thinking pauses are squeezed to ~0.2 s automatically; for any pause where she smiles, smirks, rolls her eyes, gestures, or holds a deliberate dramatic beat, add its raw range to `keep_pauses` and plan again. Plan prints the final length and the KEPT TEXT; the kept text is only a rough guide around squeezed pauses, step 4 is the real check.
4. **Hear the cut before rendering video.** `$PY $POL audio $WD && $PY $POL hear $WD`. `hear` re-transcribes the cut audio and lists:
   - `fillers left`, `doubled words` (not across a sentence end: "better now. Now that" is fine),
   - `long gaps`: real quiet between words (measured against the local background, so wave/wind noise counts as quiet and a stretched word doesn't), with the raw times (`src a-b`) to fix; pauses inside `keep_pauses` are marked `(kept beat)`,
   - `drawn-out connectives` ("and…", "now…" held over 0.9 s): cut them when the sentence works without (see "Slow or outdoor talk").
   Also read the HEARD text like a viewer: words that crept back from a cut, broken grammar, a sliver ("I'm s… when" = a half-kept "sometimes").
   To place a fix, `$PY $POL prof $WD <a> <b>` prints the raw loudness every 20 ms around a spot, the words and kept pieces there, and the quietest points; put a `delete_times` edge at the quiet point right before the kept word. To keep a sliver's whole word instead, shrink the `delete_words` range. Re-run `plan`, `audio`, `hear` until it reads clean. This loop is cheap (seconds); the video render is not.
5. **Render.** `$PY $POL render $WD` runs plan, audio, every chunk, assemble (`$WD/final.mp4`; the frame count must say OK) and qa (the same report as `hear`, on the final video, plus `$WD/_qa_frames.jpg`). View the contact sheet. Rendering is frame-exact (each piece gets exactly its share of frames, so video never drifts from the audio). Several videos: render them one after another in one background command.
6. **Deliver.** `$PY $POL deliver $WD <name>`: copies `final.mp4` to `Videos/<name>/<name>_clean.mp4` (or the next `_vN`; never overwrites; an older clean video moves to `_agent/tmp/superseded/`, keeping only the newest), copies the cut list next to it, and writes the cut project (`Videos/<name>/editor files/<code>_cut_project.json` + proxy + studio-voice audio; about 45 s) so she can fix cuts herself. Then write by hand:
   - in `<code>_cutlist.txt`: a "Kept on purpose:" note (kept beats, anything left in on purpose, anything odd in her raw),
   - `<name>_transcript.txt`: a clean, punctuated transcript of the edited version, fixing ASR misspellings such as "MASH.com" for Match.com, "breath crumbing" for breadcrumbing, "faith" where she means fate. Put punctuation outside the quotes of a comment keyword: comment "choose", not "choose," (it triggers her ManyChat automation). Step 2 (captions, B-roll) can use it.
7. **Reply briefly**: a table of old length to new length and what was cut, anything she should listen for, and always end with how to fix a cut: **"If anything sounds off, open `Editors/Video Editor.html` (or `Cut Editor.html`), pick <name>, fix it, Save, and tell me “render my cuts for <name>”."** When done, clear `~/vp` work dirs of videos that are finished (`du -sh ~/vp`).

## The Cut Editor (added 2026-10-21)
`Editors/Cut Editor.html` (the detailed cut editor; the Video Editor links to it, and it links back with "Video Editor ↗"; a missing editor is restored from git). Separate from the visuals editor: it works on the RAW video's time. It targets what took her the most time to fix by hand: clipped words, abrupt joins, missed "um"s and "you know"s.
- **Transcript view:** cut words struck through with Claude's reason label; click a word to jump, drag to select, ⌫ cuts, R restores. Cuts/restores use the same natural-break rule as the script (90 ms tail after a phrase, 60 ms lead before the next; the quietest point when there's no pause).
- **Timeline:** waveform in original time with cut parts hatched, or "Hide cut parts (CapCut view)". Drag the pink edge handles, nudge ±10/50 ms (arrow keys), per-join pause −/+ (only real silence from the original), "Snap to break", drag on the waveform to cut or keep any part.
- **Things to check:** auto-flags edges that land mid-sound with a ≥12 dB quieter point within 80 ms (a clipped word, or a sliver of a cut word still playing), leftover fillers (um/uh, you know, I mean, "like,", basically, literally), repeated words, joins with no breath after a sentence or no air at all, and long pauses. Each has ▶ Hear (2 s either side in the edited video), Original, a one-click Fix, and "Sounds fine" (remembered).
- **Playback** stitches the studio-voice audio with Web Audio exactly like the render (same pieces, same 12 ms fades), so what she hears is what she gets; the proxy video follows.
- **Save** writes `keep` (the kept pieces in raw time, 0.1 ms precision), `ignored` and `status:"edited"` into the cut project.

## "Render my cuts for <name>"
If she edited in the Video Editor (`Editors/Video Editor.html`; the visuals project has `cutKeep`), use the glorious-visuals skill's one command, `_agent/render_edits.py <name>`, instead: it renders the cuts and the visuals together. The steps below are for a cut-only edit (no visuals yet, or the separate Cut Editor).
1. Read `Videos/<name>/editor files/<code>_cut_project.json` (status should be `edited`; `rendered` means nothing new was saved). Compare `keep` with `renderedKeep` so you can tell her what changed (which joins moved, words cut or restored). The raw video must still be in `Drop raw videos here/`; if it's gone, ask her to put it back.
2. `$PY $POL fromcut "Videos/<name>/editor files/<code>_cut_project.json" ~/vp/<name>_cut` (a work dir with her exact pieces), then `$PY $POL render ~/vp/<name>_cut`. Her cuts are rendered as-is; don't "improve" them. If qa lists a leftover filler or gap, mention it rather than cutting it.
3. **If a visuals project exists** (`Videos/<name>/editor files/<code>_broll_project.json`), do this BEFORE step 4 (it needs the old `renderedKeep`): `$PY $POL remap "Videos/<name>/editor files/<code>_cut_project.json" "Videos/<name>/editor files/<code>_broll_project.json"`. It moves caption words, B-roll slots, cards, zooms and the hook from the old clean timeline to the new one (backup in `_agent/tmp/`), drops caption words that were cut, adds restored words, and flags slots/cards whose edges landed on cut material. Set the visuals project's `video` to the new clean file, tell her what moved or was flagged, and offer to re-render the Glorious version.
4. `$PY $POL deliver ~/vp/<name>_cut <name>`: the next `<name>_clean_vN.mp4`, the old one to `_agent/tmp/superseded/`, and the cut project refreshed (keeps Claude's reasons and first cut; sets `renderedKeep` and status `rendered`). Add a `<name>_transcript_vN.txt` if the words changed.
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
- **Silences she still trimmed (her 1108-9 re-cut, 2026-11-11):** (1) a kept dramatic beat ran 1.1 s; she cut it to ~0.57 s (0.4 s after the line, 0.17 s before the next), so kept beats are now capped there automatically. (2) a 0.7 s hesitation mid-sentence ("absolutely … not how") and 0.55 s of silence before her first word survived because the ASR put the next word's timestamp inside the silence, which the squeeze read as soft speech; it now only counts as speech when there's sound right after it. Dead air before the very first word: at most ~0.1 s. When reading the KEPT TEXT and `pauses.jpg`, treat any pause over ~0.4 s that isn't a smile/gesture beat as a miss.
- **Pause squeezing:** dead air is squeezed to a short breath (`max_pause`), but the script still extends phrase edges until the voice fades, so words aren't clipped. Don't tighten the voice-fade padding; she complained about clipped words. Fixing clipped words, abrupt joins and missed fillers by hand used to take her the most time; that's what the Cut Editor is for.
- **Speed:** keep normal speed. She speeds up manually in CapCut when she wants to.

## Audio rules
- **Studio voice:** 85 Hz high-pass, noise remover (see below), -3 dB at 250 Hz, +3.5 dB at 3.2 kHz, +4 dB high shelf at 6.5 kHz, 3:1 compression, de-esser, then two-pass loudnorm to -14 LUFS. Her raw car audio sits around -35 LUFS, so the result is much louder; that's expected.
- **Background noise, three levels per video (her request, 2026-11-11):** `off` = no noise remover (good mic, or audio she already cleaned in CapCut; EQ, compression and loudness stay), `standard` = RNNoise mix 0.85 (the chain used before), `strong` = RNNoise mix 1.0 + `afftdn=nr=10:nf=-42:tn=1` (her pick for the noisy 1108-9). Don't make strong the default; she often records with a good mic.
  - **Auto pick** (`noise_level`, runs at the `audio` step and prints its reasoning): all three voices are made (about 2 s per minute of raw video) and the pause loudness at -14 LUFS is measured for each. Strong if standard still leaves the pauses above -35 dB and strong takes out 5 dB more (1108-9 at standard: -32, too noisy for her; 1108-4 at -37 was fine). Off if the pauses are already at -45 dB or below, or standard improves them by under 2.5 dB (nothing steady to remove, e.g. she barely pauses). Otherwise standard. Say which level was picked in the reply.
  - To force a level, put `"noise": "off"|"standard"|"strong"` in edits.json. `cutproject` writes all three (`editor files/voice_off|standard|strong.wav`) and `noise:{level,floor,auto}` + `renderedNoise` into the cut project; she switches it in the Video Editor's Cut tab, and `render_edits.py` re-renders the clean video when `noise.level` differs from `renderedNoise`. Cut projects from before then were given the three voices with `polish.py noiseproject PROJECT [LEVEL]` (they were all rendered with standard).
- **Metadata:** the script strips all metadata, including the iPhone's GPS location. Keep it that way.

## If she asks for zooms here anyway
Set `"zoom": true`. It's 1.22x with a 0.7-second eased ramp, toggling at a cut no more than every 8–10 seconds, anchored at her face and chest so the ceiling gets cropped. Never zoom on the frame center, and never use `iw/ih` in the crop expression (ffmpeg 4.4 keeps the first frame's size, which pins the zoom to the top-left corner; that was the v3 bug).

## Learning from her own edits
When she drops a version she finished herself (e.g. "Edited-by-Maria.mov"), compare it to the delivered one:
- Transcribe both, diff the word sequences (difflib) to find her content cuts.
- Compare durations of long matched passages and cross-correlate audio envelopes over a range of time-scale factors to detect a speed change.
- Compare quiet time and the count of pauses over 0.15 s to detect pause tightening.
- Look at a contact sheet for visual changes, and check loudness with ebur128.
Then report what she changed and ASK which changes should become the standard before baking them into `polish.py` or this skill. Some of her manual steps (like a 1.1x speed-up) are per-video choices, not defaults. When a change is adopted, back up the old script to `_agent/tmp/before_<change>_<date>/`, note the change in VERSION.txt and propose an update to this skill.

## If `_agent/polish.py` is missing or broken
Restore it from git (`git checkout -- _agent/polish.py`, or an older version with `git log -- _agent/polish.py`; the repo is on GitHub too), then copy it to `~/vidpolish/`. Never run its `setup` stage here (Linux VM only). A missing editor: `git checkout -- "Editors/Cut Editor.html"` (or Video Editor).
