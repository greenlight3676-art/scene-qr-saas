# Connect SCENE to Codex

This package is prepared for Codex, but it is **not yet connected** to a remote repository or hosted production environment. All steps involving account authorization must be completed by the account owner.

## Option A — Chromebook Linux: quickest, no GitHub needed
1. Download and unzip `SCENE_Codex_Ready.zip` into Chromebook Linux files or Linux-accessible Downloads.
2. Open Terminal and `cd` into the extracted `SCENE_Codex_Ready` folder containing `AGENTS.md`.
3. If Codex isn't installed, run `npm install -g @openai/codex`. Then run `codex login` and sign in with the same ChatGPT account. If already signed in, skip login.
4. Type `codex` within the SCENE folder, then paste the first task below. Keep the project under git version control before large changes.
5. To smoke-test locally: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt && python3 -m pytest -q tests && node --check static/app.js`. Use `SCENE_DEMO=1` ONLY for an offline local demo, not publicly.

## Option B — GitHub + Codex Cloud: use phone/browser after initial upload
1. In GitHub, create a NEW **private** repository named `scene-qr` (do not add README/license/gitignore, as this bundle contains them).
2. On Chromebook Linux Terminal in the extracted folder, after configuring Git identity and authenticating GitHub:

```bash
git init
git add .
git commit -m "Initialize SCENE QR Codex beta"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/scene-qr.git
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username. GitHub HTTPS operations may require a credential manager or token instead of account password. Never paste secrets into chat or store them in repository files. `gh auth login` can help if GitHub CLI is installed.
3. Open `https://chatgpt.com/codex` and sign in with the ChatGPT account. Connect/authorize GitHub for the newly created `scene-qr` repo (GitHub integration used for general ChatGPT retrieval isn't necessarily the same Codex authorization). Set up a Codex Cloud environment for that repo if prompted.
4. Start a new Codex task: use the prompt below. Review changes and tests, then merge a PR after approval.

## First Codex task prompt

"Read AGENTS.md, CODEX_TASKS.md, README.md, and DEPLOYMENT_CHECKLIST.md first. Work ONLY on Task 0: audit and stabilize the existing FastAPI beta. Run current tests, identify real bugs and authorization gaps, fix the highest priority issues with regression tests, ensure CI passes, and open a scoped PR. Preserve all current user journeys and mobile UI. Do not migrate frameworks, connect live merchants, invent POS integration access, publish the demo, or add real payments. Summarize all changes and blockers."

## Trouble spots
- `codex: command not found`: install Node.js/npm for Chromebook Linux and then `npm install -g @openai/codex`; restart terminal if PATH has not refreshed.
- No repo in Codex: confirm the correct GitHub account and repository approval in Codex/GitHub settings; allow repository listing time to update.
- `git push` authentication fails: sign in using your GitHub credential manager or official GitHub CLI; don't use an account password in scripts.
- Tests fail to import `httpx` or `pytest`: activate venv and install both requirements files.
- Don't use a public web host until the deployment checklist's pilot controls have been met.
