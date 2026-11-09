---
name: glorious-thumbnail
description: "Step 3 for Maria's videos: make 9:16 Glorious Goddess thumbnails (her real frame, big serif headline in a dark box) from a cleaned video, 3 options to pick from."
---

# Glorious thumbnail (step 3)

Input: a video cleaned by step 1 (`Videos/<name>/<name>_clean.mp4`) and a headline. Output: 3 finished 1080x1920 JPGs in `Videos/<name>/`. Built 2026-11-08 to replace her manual ChatGPT thumbnails; the text style was matched to her ChatGPT examples the same day and she liked the frame picks. No AI image generation: her real face, her real frame.

## Tools
- `_agent/thumbnail.py` (run with `~/vidpolish/.venv/bin/python`). Uses `_agent/rvm_mobilenetv3_fp32.onnx` (person cut-out, same model as the hook), `_agent/face_detection_yunet_2023mar.onnx` (face finder), `_agent/fonts/PlayfairDisplay[wght].ttf` + `PlayfairDisplay-Italic[wght].ttf`, and `_agent/thumb-emoji/` (Twemoji PNGs; a new emoji is downloaded once from GitHub).
- Built and tested in a Linux VM (OpenCV 5). Not yet run on her Mac venv (Python 3.9, OpenCV 4.x, which has FaceDetectorYN): check the first Mac run closely.
- Always use the CLEAN video, never `_glorious.mp4`: captions would end up in the thumbnail.

## Steps
1. **Headline.** Use her exact headline. If she gives none, write one from the video's hook: 3-6 words, story-first, curiosity gap, and say which you picked. Mark 1-2 key words for the blush italic accent with `*asterisks*`. Emoji allowed. No extra text, no logos.
2. **Run:** `~/vidpolish/.venv/bin/python _agent/thumbnail.py <name> --headline "How to lose a man *real fast*! 🤣"` (~20 s). It scores frames every 0.4 s (eyes open, sharp, facing camera, smiling, not mid-word) and renders the 3 best, at least 4 s apart. `--at 12.4 30.1` forces specific moments (she can say "use 0:44").
3. **Output:** `Videos/<name>/<name>_thumb_1..3.jpg` + `<name>_thumb_list.txt` (headline, frame times, placement). A second run writes `_thumb_v2_1..3` (never overwrites). Check image: `~/vp/<name>/thumb_compare.jpg`.
4. **Check by looking** at the compare image: words never over her face or forehead, readable, no halo around her outline, background warm with no teal/cyan. Re-run with `--at` if a frame catches her mid-word or blinking.
5. **Reply** briefly with the path of each thumbnail and which one you'd pick.

## The look (approved 2026-11-08; don't re-ask)
- Vertical 9:16; her face, expression, body, outfit and pose preserved exactly.
- Warm golden-hour grade; background softly blurred, lightened toward cream, blue/cyan hues desaturated. No teal, cyan, neon or cold tones in the background (her outfit stays as it is).
- Headline BIG and bold, magazine-cover size (about 90-120 px on 1080 wide, the largest that fits the spot): Playfair Display Bold in cream (#F8EEE0), accent words Playfair Italic in blush (#ECB2AC); tight leading; balanced short lines (max 4); soft drop shadow. (v1 with small 58-64 px text in a 55% box was too timid.)
- Box: warm near-black (24,17,15) at 80%, softly rounded corners (14 px), snug padding. NO border, outline, frame, divider lines, hearts or ornaments (her prompt's rule; some of her ChatGPT examples have a small heart divider, add it only if she asks).
- Placement adapts to the photo: upper-left beside her face with left-aligned text when there's room, otherwise centered above her head. The box tucks behind her hair (she is layered in front of the box); the words are always on top and stay inside the centre 3:4 area the Instagram grid shows (y 240-1680).

## Fallback
If she ever prefers the generated ChatGPT look, the agreed alternative is an OpenAI image API call with her prompt and the chosen frame (needs her API key). Ask before setting that up.
