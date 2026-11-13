# AGENTS.md (for Codex and other non-Claude agents)

This folder is shared by Claude Code and Codex. **`CLAUDE.md` is the single source of truth.** Read it completely before doing anything, and follow it exactly: the folders, house rules, first-run setup and card style all apply to you too.

## How to use the Claude-specific parts
- **Skills:** the workflows live in `.claude/skills/<name>/SKILL.md`. When Maria asks for one of these tasks, open the matching file and follow its steps as plain instructions:
  - `process-videos`: the whole chain ("process my new videos", "process <video>"): step 1, then step 2, one reply
  - `polish-talking-video`: step 1 cleanup ("clean up <video>", "render my cuts for <name>")
  - `glorious-visuals`: step 2 visuals ("add the Glorious visuals", "render my edits for <name>"); it always ends with the thumbnail step (3 thumbnails + a `_cover` video that starts on the pick)
  - `update-broll-library`: catalog new B-roll in `~/Desktop/b-roll collection`
  - `glorious-thumbnail`: step 3 thumbnails (run at the end of every visuals pass, or alone for "make a thumbnail for <name>")
- The skills are written for this Mac: run their commands as written (real `~/Desktop/...` paths, `~/vidpolish/.venv/bin/python`) and open the images they mention yourself to check renders.
- Mentions of Claude's tools (the Read tool, slash commands, `.claude/settings.json`) map to your own equivalents.

## Environment (already set up; don't reinstall)
- Python venv: `~/vidpolish/.venv/bin/python`. ffmpeg comes from Homebrew. Models, fonts and scripts are in `_agent/`. See the folder layout table in CLAUDE.md: raw videos in `Drop raw videos here/`, everything generated per video in `Videos/<name>/`, editors in `Editors/`.
- The B-roll library is outside this folder: `~/Desktop/b-roll collection`. You need write access to it for library updates and for the usage log in `_catalog/CATALOG.md`.

## Working alongside Claude Code
- All state lives in files (`Videos/*/editor files/*_project.json`, `_catalog/clips.json`, the usage log in CATALOG.md), so either agent can pick up where the other stopped.
- Never work on the same video at the same time as another agent.
- If you learn a new rule from Maria, add it to **CLAUDE.md** (not here) so both agents get it.
