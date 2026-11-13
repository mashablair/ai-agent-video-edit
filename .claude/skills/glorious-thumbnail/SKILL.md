---
name: glorious-thumbnail
description: "Step 3 for Maria's videos: make 9:16 Glorious Goddess thumbnails (her real frame, big DM Serif headline in a stepped dark box) from a cleaned video, 3 options to pick from, and put the chosen one in as the video's first frame."
---

# Glorious thumbnail (step 3)

Input: a video cleaned by step 1 (`Videos/<name>/<name>_clean.mp4`) and a headline. Output: 3 finished 1080x1920 JPGs in `Videos/<name>/`. Built 2026-11-08 to replace her manual ChatGPT thumbnails; the text style was matched to her ChatGPT examples the same day and she liked the frame picks. No AI image generation: her real face, her real frame.

## Tools
- `_agent/thumbnail.py` (run with `~/vidpolish/.venv/bin/python`). Uses `_agent/rvm_mobilenetv3_fp32.onnx` (person cut-out, same model as the hook, used to keep her whole head in frame and blur only the background), `_agent/face_detection_yunet_2023mar.onnx` (face finder), `_agent/fonts/DMSerifDisplay-Regular.ttf` + `DMSerifDisplay-Italic.ttf`, and Apple Color Emoji from macOS (crisp; the emoji her viewers see on iPhone). Off a Mac it falls back to Twemoji PNGs in `_agent/thumb-emoji/` (downloaded once; a download that isn't a real PNG is rejected).
- Always use the CLEAN video, never `_glorious.mp4`: captions would end up in the thumbnail. Output is at the video's own resolution (1440x2560 for her iPhone takes).

## Steps
1. **Headline.** Use her exact headline. If she gives none, write one from the video's hook: 3-7 words, story-first, curiosity gap, and say which you picked. Mark the key phrase for the blush italic accent with `*asterisks*` (one phrase; it gets its own line when it fits). Emoji allowed. `|` forces line breaks ("Ladies,|*Never Be*|An Option! 😑"); otherwise lines are balanced automatically (at most 3, an accent phrase never split).
2. **Run:** `~/vidpolish/.venv/bin/python _agent/thumbnail.py <name> --headline "He just didn't *choose* you 🙄"` (~20 s). It scores frames every 0.4 s and renders the 3 best, at least 4 s apart. `--at 16.0 58.0` forces specific moments (she can say "use 0:44").
3. **Output:** `Videos/<name>/<code>_thumb_1..3.jpg` + `<code>_thumb_list.txt` (headline, frame times, text size, lines). A second run writes `_thumb_v2_1..3` (never overwrites). Check image: `~/vp/<name>/thumb_compare.jpg`.
4. **Check by looking** at the compare image: her face big with the whole head in frame, a smile with eyes on the camera, the box inside the frame and below her chin, text readable. Re-run with `--at` if a frame catches her mid-word, blinking, or looking away; pick her best smiles by eye from a contact sheet when the scorer's third choice is weak.
5. **Reply** briefly with the path of each thumbnail and which one you'd pick.

## Frame choice (her preference, 2026-11-08: "smile, eyes on camera so far is the best")
The scorer favours visible teeth and raised mouth corners (a smile), and penalises a dark open mouth (mid-word), eyes closed (eye contrast 18% under the video's typical) and a turned head. Calibrated on 1108-2/1108-4 frames judged by eye: smiles and calm looks had mouth darkness <=0.21 and corners at 0.38-0.44; talking, shouting and puckers 0.29+ and 0.47-0.61. The old scorer (mouth width) picked mid-word frames.

## Putting the thumbnail in as the first frame
She cross-posts to Instagram, Facebook, YouTube and TikTok and wants the cover in the video on all of them (2026-11-08). When she picks a thumbnail for a video: `~/vidpolish/.venv/bin/python _agent/cover.py Videos/<name>/<video>.mp4 Videos/<name>/<thumbnail>.jpg` (usually the newest `_glorious` video). It writes `<video>_cover.mp4` next to it (then `_cover_v2`; never overwrites) in about 10 s, with no re-render: the thumbnail becomes a 3-frame segment (0.1 s) encoded with glorious.py's exact settings (forced to TV color range; a JPEG's full range would retag the whole video) and is joined in front by stream copy; the audio is delayed by those 3 frames. It checks the frame count, a clean decode, the color range, and that every original frame is identical to the source, and refuses to finish if any check fails. Why 3 frames (tested by her 2026-11-09): Instagram's web uploader can't pick a 1-frame cover from its frame strip, but 3 frames work, and 0.1 s is barely visible to viewers. Picking it at upload time saves her setting the cover again by hand on Instagram and Facebook in the phone app. Don't go back to 1 frame. `--frames N` changes the length. Look at the first few frames before telling her it's ready. Store the chosen thumbnail in `Videos/<name>/editor files/<code>_broll_project.json` as `"thumb"` (path from her folder): `_agent/render_edits.py` rebuilds the cover from it after every re-render, so the file she posts always starts on the thumbnail (her rule, 2026-11-13).

## The look (approved 2026-11-08; don't re-ask)
Built from a GPT render she liked ("Ladies, *Never Be* An Option! 😑") and her choice between Playfair, Bodoni Moda, Bodoni 72, Didot and DM Serif Display at phone-grid size (hairline Bodoni/Didot strokes vanish when small; DM Serif reads best and is closest to the GPT look). Her real frame, not AI-redrawn.
- **Framing:** her face ~42% of the width, eyes in the upper third, the whole head in frame (zoom only as far as the frame allows; never invent headroom).
- **Grade:** crisp and warm (a touch of contrast and saturation); background softly blurred behind her cut-out. No hazy cream wash (the first version's, too flat).
- **Headline:** DM Serif Display in cream (#FAF0E2), the accent phrase in DM Serif Display Italic, blush (#F0B2B0), 12% larger. As big as fits (about 196 px on 1440 wide). Left-aligned, low in the frame over her chest (the box also hides the selfie arm and earbud cable).
- **Box:** warm near-black (38,28,24) at 74%, one rounded rectangle per line joined into a single stepped shape, soft text shadow. The whole box stays inside the frame and inside the centre 3:4 the Instagram grid shows (bottom at 87.5% of the height).
- Earlier looks (Playfair box above her head; bold sans lower third; the cream brand card; a big word behind her head) are in `_agent/tmp/` scripts if she ever asks for them.

## Fallback
If she ever prefers the generated ChatGPT look, the agreed alternative is an OpenAI image API call with her prompt and the chosen frame (needs her API key). Ask before setting that up.
