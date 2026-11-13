---
name: "update-broll-library"
description: "Catalog new B-roll videos and photos Maria adds to her 'b-roll collection' folder: cut usable clips, make photo push-ins, and update CATALOG.md."
---

# Update the B-roll library

Maria adds raw videos and photos (.mov, .MOV, .heic, .jpg, .png) to `~/Desktop/b-roll collection`, and sometimes deletes raw files that were already processed. She also reviews `clips/` directly: she **deletes** clips she doesn't like and **renames** clips whose name misreads the scene (2026-10-30, 2026-11-07). She never touches `_catalog/`. Process only what's new.

## Where things are (this Mac)
- `~/Desktop/b-roll collection/` (run the catalog scripts from there; it's an extra working directory of this project)
  - `clips/` holds the output clips.
  - `_catalog/clips.json` is the master list of clips.
  - `_catalog/CATALOG.md` has the theme finder, clip tables, "Sources already processed", "Skipped footage" and "Usage log".
  - `_catalog/build_clips.py` cuts every clip in clips.json that doesn't exist yet. Pass clip ids to force a rebuild (not yet confirmed on macOS: check the first new clips closely).
  - `_catalog/stills/` holds JPG copies of photos.
  - `stock originals/` holds the full stock videos she downloads (renamed from `broll/` on 2026-11-07). Move new stock downloads from the top level into it before cutting; their clips get `stock-` ids, `"stock": true` and `src: "stock originals/<file>"`.
  - `READ ME.txt` at the top explains the folders to her. Keep it accurate if the layout changes.
  - `_catalog/previews/` and `_catalog/thumbs/` hold contact sheets and clip thumbnails.
- `PY=~/vidpolish/.venv/bin/python` (has pillow-heif, opencv, numpy). Look at images with the Read tool. No time limits.
- Deleting is off in her folders; move junk to `_catalog/_to_delete/`.

## Steps
0. **Sync with what she changed in `clips/`** (always first; otherwise `build_clips.py` rebuilds clips she deleted):
   - Compare the `.mp4` names in `clips/` with the ids in `clips.json`.
   - An id with no file and a file with no id at the same time usually means she **renamed** it: match the new file to the old id by comparing its frames with `_catalog/thumbs/<old id>.jpg`, then update the id, scene, mood and tags (her name tells you what the clip really shows; stock conflict scenes matter for her unhappy-relationship content), rename the thumb, and replace the old id in CATALOG.md (theme finder included) and in any video project that uses it.
   - An id with no file and no new file means she **deleted** it: remove the entry from clips.json, move its thumb to `_catalog/_to_delete/`, take it out of the theme finder and tables, and list it under "Skipped footage" ("she deleted after review, don't re-cut").
   - Back up `clips.json` and `CATALOG.md` to `_catalog/_to_delete/<name>_before_<change>_<date>` first.
1. **List new sources:** files not under "Sources already processed" in CATALOG.md.
   - Check for duplicates (same size and creation date as a processed file, or names like `X 2.mov`) and skip them.
2. **Probe each video** for duration, size, rotation, fps and color_transfer. If it's `arib-std-b67` or `smpte2084` it's HDR: set `"hdr": true` so it gets tone-mapped.
3. **Make a contact sheet per video** (one frame per second for clips up to 24 seconds, every 2 seconds for longer ones, with timestamps), plus one sheet of all new photos.
   - HEIC opens with pillow-heif (installed in the venv). Convert photos to `_catalog/stills/<name>.jpg`, with EXIF rotation applied.
4. **Measure camera motion** per second with phase correlation on small grayscale frames. Prefer steady stretches.
5. **Choose clips** of 2–4 seconds, about 1–4 per video:
   - Pick steady, well-lit moments with clear subjects.
   - Avoid shaky pans, mid-turn blur, close-ups of strangers, and moments where she's clearly talking.
   - Leave out shots with her daughter unless Maria asks for family clips. Scenery and solo shots from the same file are fine.
   - Make one push-in clip per photo (`"still": "<name>.jpg"`; the in/out times are set to 0 to 3.5). Images that resemble real celebrities get a `"caution"` note and are never used unless she asks.
6. **Write the entries** and append them to clips.json. Each entry needs: id (kebab-case, `maria-...` when she's in it, `photo-...` for stills), src, in, out, scene, maria (true/false), setting, tags, mood.
7. **Build** with `$PY _catalog/build_clips.py` (one run builds every missing clip; it reports `remaining: 0` when done).
8. **Check:** tile the mid-frames of the new clips into a sheet and view it. Fix any bad picks by changing times and forcing a rebuild of those ids.
9. **Update CATALOG.md:**
   - Regenerate the tables from clips.json and extend the theme finder.
   - Add the new sources to "Sources already processed" and note anything skipped.
   - Keep the usage log exactly as it was.
   - **Write safely** (on 2026-11-08 a one-liner `open(C,'w').write(open(C).read()+...)` emptied the file before reading it and wiped everything but the log): read the file into a variable first, build the new text, check it still has `## Theme finder`, `## Sources already processed`, `## Skipped footage` and `## Usage log` and is not shorter than before except for clips you removed, then write. Every clips.json id must appear in the tables.
   - Regenerate `catalog_overview.jpg` from `thumbs/`.
10. **Reply briefly:** how many clips were added, the highlights, what was skipped and why, and anything she needs to decide.