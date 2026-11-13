---
name: "process-videos"
description: "The whole chain for Maria's raw videos in one go: step 1 cleanup (polish-talking-video), then step 2 visuals with the thumbnail and cover (glorious-visuals), ending with the file she posts. Use for \"process my new videos\", \"process <video>\" or \"do everything for <video>\"."
---

# Process videos: the whole chain (her request, 2026-11-13)

Her three commands:
| She says | What runs |
|---|---|
| "process my new videos" / "process <video>" | **this skill**: cleanup, then visuals + thumbnail + cover, one reply at the end |
| "clean up <video>" | `polish-talking-video` only (step 1) |
| "add visuals to <name>" | `glorious-visuals` only (step 2, which always ends with the thumbnail + cover) |

Using this command is her asking for both steps together, so the house rule "step 1 and step 2 separately" doesn't apply here. Don't stop between the steps to ask her anything; she reviews the finished video and fixes anything in the Video Editor.

## Steps
1. **Find the videos.** With a name ("process 1115-2"), do that raw file. With "my new videos": every raw file in `Drop raw videos here/` whose code (file stem) has no `Videos/<code> …/` folder and no line in the B-roll usage log (`~/Desktop/b-roll collection/_catalog/CATALOG.md`). A raw with a usage-log line but no folder is one she already posted and deleted: skip it and list it in the reply. If nothing is new, say so and stop.
2. **Step 1 for each video:** follow `.claude/skills/polish-talking-video/SKILL.md` completely (naming with the topic, cuts, pause check, hear loop, render, deliver, cutlist note, transcript), including its checks by looking and listening. With several videos, transcribe all first, then cut each.
3. **Step 2 for each video:** follow `.claude/skills/glorious-visuals/SKILL.md` completely on the new `<name>_clean.mp4`, through step 13 (thumbnails + cover). Several videos: B-roll picks must not repeat across them or hit the latest usage-log entry; give each its own usage-log line. Renders can run one after another in the background; check each one by looking before delivering.
4. **Reply once, per video:**
   - the folder and **the file to post** (`<name>_glorious_cover.mp4` or its newest `_vN_cover`),
   - cleanup: old → new length, what was cut, the noise level picked, anything to listen for,
   - visuals: the hook text pick and the 2 alternatives, accent words, B-roll lines (what she says / what's on screen), B-roll %,
   - thumbnail: the headline and which of the 3 was put in as the cover,
   - how to change things: `Editors/Video Editor.html` (reload it first), Save, then "render my edits for <name>".
   Keep it short; tables over prose.
