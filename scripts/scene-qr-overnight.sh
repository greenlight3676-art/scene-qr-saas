#!/usr/bin/env bash
# Scene QR unattended development runner.
# Run manually inside tmux on a trusted, powered-on Chromebook.
set -Eeuo pipefail

REPO="${SCENE_REPO_DIR:-$HOME/scene-qr-saas}"
BRANCH="qr-overnight-build"
ROUNDS="${SCENE_ROUNDS:-4}"
LOG="${SCENE_LOG_FILE:-$HOME/scene-qr-overnight.log}"

if ! [[ "$ROUNDS" =~ ^[1-6]$ ]]; then
  echo "SCENE_ROUNDS must be an integer from 1 to 6."
  exit 2
fi
for command in git codex python3 node timeout; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing required command: $command"
    exit 2
  fi
done
cd "$REPO"
if [[ "$(git branch --show-current)" != "$BRANCH" ]]; then
  echo "Switch to $BRANCH before starting. Refusing to touch another branch."
  exit 2
fi
origin="$(git remote get-url origin)"
case "$origin" in
  https://github.com/greenlight3676-art/scene-qr-saas|https://github.com/greenlight3676-art/scene-qr-saas.git|git@github.com:greenlight3676-art/scene-qr-saas|git@github.com:greenlight3676-art/scene-qr-saas.git)
    ;;
  *)
    echo "Unexpected Git origin: $origin"
    exit 2
    ;;
esac
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Review/preserve pending changes first."
  exit 2
fi
git fetch origin "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "Scene QR overnight run on $BRANCH" | tee -a "$LOG"
for ((round=1; round<=ROUNDS; round++)); do
  echo "===== Development round $round/$ROUNDS =====" | tee -a "$LOG"
  prompt="$(cat <<'PROMPT'
Continue development of Scene QR SaaS in the existing repository and branch.
Read AGENTS.md, README.md, CODEX_TASKS.md, SUPABASE_CONNECTION.md,
DEPLOYMENT_CHECKLIST.md and recent progress reports.
Inspect the code and select ONE high-value, safely testable unfinished task,
prioritizing fixes, tenant security, responsive UX, customer requests,
QR operations and verified analytics. Implement real functionality and tests.
Run focused tests and clearly state what was changed.
Never add secrets, personal customer data, paid actions or fake integrations.
No hosted Supabase database writes or migrations. Do not deploy, force-push,
change CI/security guardrails, modify this runner, or change Git refs.
Do not commit or push: the outer runner will validate, commit and push.
If the next task requires unverified credentials or irreversible changes,
document the blocker and select a different safe task.
PROMPT
)"
  if ! timeout 7200 codex exec \
      --sandbox workspace-write \
      --ask-for-approval never \
      "$prompt" >>"$LOG" 2>&1; then
    echo "Codex exited unsuccessfully or reached the 2-hour cap; stopping." | tee -a "$LOG"
    exit 1
  fi

  # Fail closed: a coding pass does not get uploaded unless local checks pass.
  if ! python3 -m pytest -q tests >>"$LOG" 2>&1; then
    echo "Python tests failed; leaving changes local for review." | tee -a "$LOG"
    exit 1
  fi
  if ! node tests/frontend.test.cjs >>"$LOG" 2>&1 ||
     ! node --check static/app.js >>"$LOG" 2>&1 ||
     ! git diff --check >>"$LOG" 2>&1; then
    echo "Frontend/syntax/diff checks failed; leaving changes local." | tee -a "$LOG"
    exit 1
  fi

  git add -A -- .
  while IFS= read -r -d '' path; do
    case "$path" in
      .env|.env.*|*/.env|*/.env.*|*.pem|*.p12|*.pfx|*.key|*.sqlite|*.sqlite3|*.db|*.db-*|*.log|*.zip|*credentials*.json|*service-account*.json)
        echo "Sensitive/runtime path staged: $path. Stopping." | tee -a "$LOG"
        git reset --quiet
        exit 1
        ;;
    esac
  done < <(git diff --cached --name-only -z)

  # Detect common newly-added credential formats. This is not a full secret scan.
  if git diff --cached -U0 | grep -Eq '^\+.*(sk-[A-Za-z0-9]{20,}|sb_secret_[A-Za-z0-9]+|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN ([A-Z ]+)?PRIVATE KEY)'; then
    echo "Possible credential in staged diff. Stopping." | tee -a "$LOG"
    git reset --quiet
    exit 1
  fi
  git diff --cached --check
  if git diff --cached --quiet; then
    echo "No new changes; stopping rather than repeating." | tee -a "$LOG"
    break
  fi
  git commit -m "Scene QR autonomous development round $round"
  git push origin "HEAD:$BRANCH"
  echo "Round $round pushed to $BRANCH. GitHub CI still needs verification." | tee -a "$LOG"
done
echo "Overnight coding session ended." | tee -a "$LOG"
