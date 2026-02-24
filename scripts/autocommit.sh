#!/usr/bin/env bash
# autocommit.sh — validate .gitignore, stage all changes, commit, and push.
#
# Usage:
#   ./scripts/autocommit.sh "feat: describe the change"
#   ./scripts/autocommit.sh          # auto-generates message from changed files
#
# Called automatically by the Copilot CLI agent after every code change.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# ── 1. Validate / repair .gitignore ─────────────────────────────────────────
REQUIRED_PATTERNS=(
    "__pycache__/"
    "*.py[cod]"
    "venv/"
    "env/"
    ".env"
    "*.egg-info/"
    "dist/"
    "build/"
    ".DS_Store"
    ".pytest_cache/"
    "bet_history/"
    "data/*.db"
    "data/*.json"
    ".coverage"
    "htmlcov/"
    "*.log"
    "logs/"
    ".tox/"
    "*.bak"
    "*.old"
)

GITIGNORE=".gitignore"
ADDED=0
for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if ! grep -qF "$pattern" "$GITIGNORE" 2>/dev/null; then
        echo "$pattern" >> "$GITIGNORE"
        echo "  ➕ .gitignore ← $pattern"
        ADDED=1
    fi
done

if [ "$ADDED" -eq 1 ]; then
    echo "✅ .gitignore updated"
else
    echo "✅ .gitignore is up to date"
fi

# ── 2. Stage everything ──────────────────────────────────────────────────────
git add -A

# ── 3. Bail early if nothing to commit ──────────────────────────────────────
if git diff --cached --quiet; then
    echo "ℹ️  Nothing to commit — working tree clean."
    exit 0
fi

# ── 4. Build commit message ──────────────────────────────────────────────────
if [ -n "${1:-}" ]; then
    SUBJECT="$1"
else
    # Auto-generate subject from list of changed files/dirs
    CHANGED_FILES=$(git diff --cached --name-only)
    FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l | tr -d ' ')
    TOP=$(echo "$CHANGED_FILES" | head -3 | paste -sd ', ' -)
    if [ "$FILE_COUNT" -le 3 ]; then
        SUBJECT="chore: update ${TOP}"
    else
        SUBJECT="chore: update ${TOP} (+$((FILE_COUNT - 3)) more)"
    fi
fi

FULL_MSG="${SUBJECT}

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# ── 5. Commit ────────────────────────────────────────────────────────────────
git commit -m "$FULL_MSG"
echo "✅ Committed: ${SUBJECT}"

# ── 6. Push ──────────────────────────────────────────────────────────────────
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git push origin "$BRANCH"
echo "🚀 Pushed → origin/${BRANCH}"
