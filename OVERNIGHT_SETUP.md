# Scene QR — overnight Codex quick start (Chromebook/Linux)

This is a bounded local automation, NOT an always-on cloud service. The Chromebook must stay awake, charged, online, and logged into Codex and GitHub. It runs up to four rounds by default (configurable between 1 and 6); usage limits or errors can stop it earlier.

## Prerequisites

- Your Scene QR repo lives in `~/scene-qr-saas`.
- Codex CLI is installed, authenticated, and supports `codex exec --sandbox workspace-write --ask-for-approval never`. Verify with `codex exec --help`.
- GitHub CLI login (or another working Git credential helper) can push to `greenlight3676-art/scene-qr-saas`.
- Python project test dependencies and Node are installed. Install dependencies from the pinned repository requirement files using a local virtual environment if needed. The script intentionally stops rather than pushing untested changes.
- Read `AGENTS.md` and `SUPABASE_CONNECTION.md`.

## Start

Exit interactive Codex first if you are inside it (`/exit`), then run in the Linux terminal:

```bash
cd ~/scene-qr-saas
git status --short
git fetch origin
git switch qr-overnight-build
git pull --ff-only origin qr-overnight-build
gh auth status
codex exec --help
sudo apt install -y tmux
tmux new-session -d -s qr-night 'bash scripts/scene-qr-overnight.sh'
```

**Stop if `git status --short` shows modifications you want to keep.** Never run `git reset --hard` just to get a clean tree.

## Check progress

```bash
tmux attach -t qr-night
# Press Ctrl+B, release, then press D to detach without terminating.
tail -n 50 ~/scene-qr-overnight.log
git log -5 --oneline qr-overnight-build
```

## Stop safely

```bash
tmux send-keys -t qr-night C-c
```

If `tmux` says the session no longer exists, the job has finished or stopped. Review the log and `git status`; do not restart blindly over uncommitted work.

## What the runner can and cannot do

- Works in `qr-overnight-build` only and checks the Git remote before starting.
- Runs Codex in workspace-write mode with no routine approval prompts and no unrestricted host access.
- Runs Python and frontend tests after each pass; only commits/pushes after success.
- Rejects common secret/database filenames and selected key patterns in the staged diff. **This is not an exhaustive secret scan**; avoid keeping secrets in the repository in the first place.
- Uploads code to GitHub, but **does not host the website**, and a local green test run does not guarantee remote CI will pass.
- Does **not** touch the hosted Supabase database, migrate the schema, change `main`, or deploy customer-facing production services.
- Requires manual setup for Supabase CLI authentication and database credentials. Link only the verified project reference in `SUPABASE_CONNECTION.md`; never print or paste secrets.
