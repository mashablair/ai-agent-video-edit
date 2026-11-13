# Maria's video studio: Glorious Goddess (GG) + MariaTalksTech (MTT)

This folder is Maria's short-form video pipeline. Raw iPhone talking-head videos go in, finished vertical reels come out.
**Her goal (2026-11-10):** she records a video (scripted or not), drops it in, and Claude does all the work here, including the hook, so she can take the final video and post it. Automate as much as possible and save her time.
Maria is a senior developer (Angular/TypeScript), so technical detail is fine. In replies, keep the focus on what she needs to watch for or decide.

Current reference: the skills in `.claude/skills/` (how each step works) and `_agent/VERSION.txt` (every script change since 2026-10-24, dated, with its reason and backup). Read the VERSION.txt entries for a script before changing it.
History: `_agent/VIDEO_EDITING_HANDOFF.md` (frozen 2026-10-24: tools tried, early bugs and rules; its paths and pipeline are out of date, the skills win where they disagree).

## Folders
Layout of `~/Desktop/AI agent video edit/` (reorganized 2026-10-27 so it's obvious what's hers and what's the agent's; keep it this way):
| Folder | Whose | What |
|---|---|---|
| `Drop raw videos here/` | hers | Raw videos she drops in. Never modify, move or delete them; she clears this folder herself. |
| `Videos/<name>/` | hers (generated) | **Everything made for one video**, so she can delete the whole folder when done: `<name>_clean.mp4`, `_glorious.mp4`, `<code>_thumb_1..3.jpg`, cutlists, transcripts, lists, and `editor files/` (`<code>_cut_project.json`, `<code>_broll_project.json`, `proxy.mp4`, `voice.wav`). `<name>` = the raw file's stem plus a short topic from the transcript, e.g. `1108-4 stop chasing` (her request, 2026-11-13, so she can tell videos apart without opening them). 2-5 plain words, no apostrophes, quotes, colons or slashes (they break ffmpeg filter paths); the raw file keeps its own name and the cut project's `src` points to it. Only the folder, the videos and `<name>_transcript.txt` carry the full name; meta files (projects, cutlist, lists, thumbnails) use the short code: `1108-4_cut_project.json`, `1108-4_thumb_1.jpg`. `render_edits.py` and `thumbnail.py` accept either the code or the full name. Always quote paths (they have spaces). |
| `Editors/` | hers | `Video Editor.html` (her main editor since 2026-11-04: cuts + B-roll + captions in one, saves both projects), plus `Cut Editor.html` (detailed cut work) and `B-roll Editor.html` (Chrome only; never treat them as videos). They open the main folder and find projects in `Videos/*/editor files/`. Backups in `_agent/editor-backups/`. |
| `_agent/` | agent's, **never deleted** | Scripts (`polish.py`, `glorious.py`, `captions.py`, `rvm_mask.py`), models, fonts, caption presets, text-card refs, `VERSION.txt`, `VIDEO_EDITING_HANDOFF.md`, `tmp/` (superseded versions, backups, `_to_delete/`). Was `_tools/` before 2026-10-27. |
| `CLAUDE.md`, `AGENTS.md`, `.claude/` | agent's | Must stay at the top level. |
- Never write generated files anywhere else in her folder (no files at the top level, no `edited/`). If a video has no `Videos/<name>/` yet, create it.
- When she deletes a `Videos/<name>/` folder, that video is gone for good (projects too). Don't recreate it unless she asks.
- `~/Desktop/b-roll collection/` is her B-roll library. It is added as an extra working directory in `.claude/settings.json` (until setup step 0 is done, start with `claude --add-dir ~/Desktop/"b-roll collection"`).
  It holds `clips/<id>.mp4` (1080x1920, 30fps, muted) and `_catalog/` (`clips.json`, `CATALOG.md` with the theme finder and the **usage log**, `build_clips.py`, `add_broll.py`, `thumbs/`, `stills/`).
- Work directories go in `~/vp/<name>`, never inside her folders.
- Python tools are installed in `~/vidpolish/` (venv at `~/vidpolish/.venv`).

## Skills (in `.claude/skills/`, tracked in git)
| She says | Skill |
|---|---|
| "clean up / polish <video>", "render my cuts for <name>" | `polish-talking-video` (step 1: cuts and studio voice only) |
| "add the visuals / Glorious look to <name>", "render my edits for <name>" | `glorious-visuals` (step 2: captions, zooms, B-roll, hook text with 3 options, accent words, cards, then the thumbnail + cover video; since 2026-11-13 "visuals" always includes the thumbnail). Edits from the Video Editor render with one command: `_agent/render_edits.py <name>` |
| "just add B-roll to <name>" | `add-broll-to-video` (older, simpler B-roll-only path) |
| "update the B-roll library" | `update-broll-library` |
| "make a thumbnail for <name>" (with or without a headline) | `glorious-thumbnail` (step 3, also run automatically at the end of every visuals run: `_agent/thumbnail.py`, 3 options in `Videos/<name>/`) |

The skills are written for this Mac (rewritten 2026-11-08; the old cloud-bridge wording and its translation table are gone): real `~/Desktop/...` paths, `~/vidpolish/.venv/bin/python`, no time limits, images opened with the Read tool. Never run `polish.py setup` here (its wheels are Linux-only).

## macOS port (done 2026-10-25)
Setup is done and the smoke test passed: polish.py through the full chain, and glorious.py with captions, 2 B-roll slots, a zoom and the RVM hook. The steps below are kept for reinstalling on a new Mac. What differs from the old Ubuntu VM (ffmpeg 4.4.2, Python 3.10):
- **ffmpeg:** Homebrew `ffmpeg-full` 9.0.2, linked as `ffmpeg`. The plain `ffmpeg` formula is unlinked because it lacks `ass`, `subtitles` and `zscale`. If a `brew upgrade` relinks the slim build, run `brew unlink ffmpeg && brew link ffmpeg-full`.
- **Python:** the venv runs on the system Python 3.9.6 (the old Python that ships with macOS). All the scripts work on it for now, but newer packages are dropping 3.9 support. If a pip install or upgrade fails because of the Python version, rebuild the venv on Homebrew Python 3.12: `brew install python@3.12`, move the old venv to `~/vidpolish/.venv_py39_old`, recreate it with `/opt/homebrew/bin/python3.12 -m venv ~/vidpolish/.venv`, run the setup step 2 install, then re-run a short smoke test.
- **Script changes** (logged in `_agent/VERSION.txt`, originals in `_agent/tmp/before_macos_port_2026-10-25/`):
  - `-filter_complex_script` was removed in ffmpeg 8, so polish.py and glorious.py now use `-/filter_complex FILE` (needs ffmpeg 7 or newer).
  - The loudnorm JSON parse in polish.py now cuts at the closing brace, because ffmpeg 9 prints a stats line after the JSON.
  - polish.py paths: `DEFAULT_TOOLS` → `~/Desktop/AI agent video edit/_agent`, and the legacy-card font → `_agent/fonts/Poppins-ExtraBold.ttf`.
  - `verbatim_words` now guards against a negative start when no silence is found (qa returned an empty transcript on a tightly cut clip).
- **Fallback copy:** the script embedded in the polish skill is the Mac version too. After changing `_agent/polish.py`, copy it to `~/vidpolish/` and re-sync the embedded copy.
- **Confirmed on macOS:** the whole cleanup chain incl. `fromcut`/`cutproject`/`deliver`, `render_edits.py`, glorious.py, thumbnail/cover, and `build_clips.py` (33 boat show clips incl. HEIC stills, 2026-10-30). **Still unconfirmed:** `add_broll.py` (old B-roll-only path) and `remap` actually moving visuals (since the Video Editor moves them itself, `render_edits.py` only ever ran it as a no-op; a real run would follow an edit in the separate Cut Editor). Check those closely the first time.
- **Watch for:** in fast speech with no pause between words, the auto-cut edge extension can let a deleted word back in. Read the KEPT TEXT after `plan` and fix any leftovers with `delete_times` at the quietest point.

## First-run setup on a new Mac (reference)
0. The Claude Code config (`.claude/skills/`, `.claude/settings.json`) comes with the git clone (github.com/mashablair/ai-agent-video-edit). Check `settings.json` points `additionalDirectories` at the new Mac's `b-roll collection`, then restart Claude Code so the skills load.
1. `brew install ffmpeg-full && brew unlink ffmpeg; brew link ffmpeg-full` (the plain `ffmpeg` formula lacks the caption filters), then check that the filters exist:
   `ffmpeg -hide_banner -filters | grep -E " (ass|subtitles|zscale|tonemap|arnndn|loudnorm) "`
   If one is missing, stop and tell Maria which one, along with a fix (for example, a fuller ffmpeg build).
2. `python3 -m venv ~/vidpolish/.venv && ~/vidpolish/.venv/bin/python -m pip install sherpa-onnx soundfile numpy pillow "opencv-python-headless<5" onnxruntime pillow-heif fonttools`
   Keep the `opencv<5` pin, because newer versions lack `CascadeClassifier`.
3. Reuse the portable model files from `_agent/` instead of downloading them:
   `mkdir -p ~/vidpolish && cp _agent/polish.py ~/vidpolish/ && cp _agent/sh.rnnn ~/vidpolish/ && ln -sfn "$PWD/_agent/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8" ~/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8`
4. Check the scripts for hard-coded Linux paths before running them. Examples: `/usr/share/fonts/...` in `polish.py` (only used for legacy cards) and any `/sessions/...` paths inside the saved project JSONs. Fix paths, not logic.
5. **Prove the port before using it for real.** The breadcrumbing reference files have been removed, so do the smoke test on a ~30-second piece of a real raw video instead:
   - Run polish.py through transcribe, plan, audio, chunk, assemble and qa.
   - Check that the frame count says OK, the audio is clean (around -14 LUFS), and the contact sheet looks right.
   - Then run one short glorious.py render (captions plus 1–2 B-roll slots).
   - Report anything that behaves differently from the handoff doc (newer ffmpeg, macOS paths) to Maria before processing full videos.
6. Hardware encoding (tested 2026-10-25 with VMAF; Maria's rule is to switch only if the score is within 1 point and the render is at least 2× faster): `polish.py` final renders use `h264_videotoolbox -b:v 16M` (VMAF 98.07 vs 98.72, 2.6× faster). `glorious.py` stays on libx264 CRF 18, because its compositing filters cap the gain at 1.8×.

## House rules (approved by Maria; don't re-ask)
- **Never modify or move her original files.** Deliverables go to `Videos/<name>/` as `<name>_clean.mp4`, `<name>_glorious.mp4` and so on. Never overwrite: add `_v2`, `_v3`. Move superseded versions to `_agent/tmp/`. Don't let video backups pile up there (her rule, 2026-11-04): keep at most the one newest superseded version of each deliverable, and only while that video's `Videos/<name>/` folder still exists; delete older video copies, samples and proxies in `_agent/tmp/` (scripts and JSON backups are tiny, keep them). Also clear `~/vp/` work dirs of videos that are done. Check sizes now and then (`du -sh _agent/tmp ~/vp`).
- **Don't delete anything in her folders.** Move junk to `_agent/tmp/_to_delete/` (or `_catalog/_to_delete/` in the library) and tell her.
- Strip all metadata from outputs (`-map_metadata -1`), including the iPhone GPS location.
- Two separate steps: **step 1 cleanup** (cuts and studio voice only; no captions, zooms, B-roll or cards), then **step 2 visuals**. Never mix them unless she asks.
- **Normal speed by default.** She speeds things up herself in the editor or in CapCut.
- **B-roll comes only from her own library.** Never download stock footage, search online or generate footage. Check the most recent usage-log entry and never reuse those clips. Never use the same clip twice in one video. Never use `photo-me-and-bond` unless she asks. Leave out shots with her daughter unless she asks.
- Deliver one finished result without asking her to approve a plan first. Then reply briefly with a table of what changed, and say where she can tweak it (Cut Editor / B-roll Editor).
- **Check by looking:** make contact sheets or frame strips of every render and view them, and re-transcribe cleaned audio to catch leftover fillers.
- Before turning one of her manual edits into a new default (speed, pause length, thresholds), ask her first. Back up a script to `_agent/tmp/` before changing it, and add a line to `_agent/VERSION.txt`.

## Text-overlay cards (montage reels with music, no talking)
Maria's approved style (2026-10-24, concert reel "Utekay"):
- A **slim cream panel** (#FAF3EB, ~95% opacity) with **square corners**, tight padding (~28px × 16px) and an 8px gold bar (#C9A05A) on the left edge.
- Burgundy text (#6E1A2E): Montserrat Bold ~56px, with the accent words in Instrument Serif Italic ~78px. Left-aligned at x≈80. Panel top at y≈145 on a 1080×1920 frame.
- She dislikes very rounded corners and big padding ("out of date"). Cards must **never cover a face**: check frames every 0.5s across each card's time window.
- Keep each card on screen long enough to read: about 3.5–5 s for 2 lines, longer for the closing line. Fade in and out over 0.25s.
- Reference images of the approved cards: `_agent/text-cards/cardC1–4.png` (full-frame 1080×1920 transparent overlays).
- About 4 short beats per 60–90 s reel: hook in the first frame (it doubles as the cover), story beats, closing payoff line.
- She also posts 60-second Story cuts. Keep the music continuous and fade it out, and cut the video only at shot changes.

## Getting files to her phone
Finished videos stay in `Videos/<name>/`. She AirDrops them to her phone or opens them through iCloud Drive. Mention the path of each deliverable in your reply.

## Brand context (for picking keywords, hook words and B-roll)
- GG = Maria's personal brand for women 40+: leaving unhappy relationships, starting over, building a happy single life, with dating as one part of it. The signature mark is the 🐆 leopard.
- Brand palette: cream, blush, deep burgundy, soft gold. Her voice is direct, first-person and story-first.
- MTT = AI for non-technical women.
- Hooks are written here, in step 2 (3 options per video, guide in `.claude/skills/glorious-visuals/hooks.md`), and so are thumbnail headlines (step 3). When she brings a hook, title or headline from her other Claude work along with the video, use hers as the pick.
- Post captions and strategy still mostly come from her Claude "Glorious Goddess" project; help with them here when she asks.
