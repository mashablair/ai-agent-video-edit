---
name: "video-posted"
description: "Clean up after Maria posts a video and deletes its Videos/<name>/ folder: remove every leftover copy, list file and work dir for it on the agent's side. Use for \"posted <video>\", \"I posted <video>\", \"done with <video>\" or \"clean up posted videos\"."
---

# Video posted: clean up its leftovers (her command, 2026-11-19)

She says "posted 1108-7" (or "posted", for every video she has deleted). She deletes `Videos/<name>/` herself; this removes what's left on our side.

1. Check the folder is really gone (`ls Videos`). If it still exists, ask whether she wants it deleted; never delete her folder yourself.
2. Run `~/vidpolish/.venv/bin/python _agent/render_edits.py --prune`. For every video whose folder is gone it deletes the superseded videos and list files in `_agent/tmp/superseded/` and its `~/vp/` work dirs (for videos still there it keeps only the newest old copy of each).
3. **Keep** its usage-log line in `~/Desktop/b-roll collection/_catalog/CATALOG.md`: it blocks reusing the same clips next time and tells "process my new videos" it was posted. Never touch her raw file in `Drop raw videos here/` (she clears that herself).
4. Reply in 2-3 lines: what was deleted (and roughly how much space), what was kept, and the next video to post.
