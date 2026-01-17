# GitHub Branch Protection Setup Guide

This document explains how to configure GitHub branch protection rules to ensure main branch is **always buildable**.

---

## 🎯 Goal

**No code can be merged to main unless CI/CD passes.**

## 📋 Workflow

```
Developer          Feature Branch         Pull Request         Main Branch
   │                     │                      │                    │
   ├─ Create branch ────►│                      │                    │
   │                     │                      │                    │
   ├─ Make changes ──────►│                      │                    │
   │                     │                      │                    │
   ├─ Push ──────────────►│                      │                    │
   │                     │                      │                    │
   │                     ├─ Open PR ───────────►│                    │
   │                     │                      │                    │
   │                     │             Run CI/CD (9 configs)         │
   │                     │                      │                    │
   │                     │              ✅ All tests pass             │
   │                     │                      │                    │
   │                     │              Merge allowed ──────────────►│
   │                     │                      │                    │
   │                     │                      │         ✅ Always buildable
```

---

## 🔧 GitHub Repository Settings

### Step 1: Enable Branch Protection

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Click **Branches** (left sidebar)
4. Click **Add branch protection rule**

### Step 2: Configure Protection Rules

**Branch name pattern**: `main`

**Enable these settings**:

#### ✅ Require a pull request before merging
- ☑ Require approvals: **0** (or 1 if you want manual review)
- ☑ Dismiss stale pull request approvals when new commits are pushed
- ☑ Require review from Code Owners (optional)

#### ✅ Require status checks to pass before merging
- ☑ Require branches to be up to date before merging
- **Select required status checks**:
  - `Validation on ubuntu-latest - Python 3.9`
  - `Validation on ubuntu-latest - Python 3.11`
  - `Validation on ubuntu-latest - Python 3.12`
  - `Validation on windows-latest - Python 3.9`
  - `Validation on windows-latest - Python 3.11`
  - `Validation on windows-latest - Python 3.12`
  - `Validation on macos-latest - Python 3.9`
  - `Validation on macos-latest - Python 3.11`
  - `Validation on macos-latest - Python 3.12`
  - `Code Quality`
  - `PR Validation Summary`

#### ✅ Require conversation resolution before merging
- Ensures all PR comments are addressed

#### ✅ Require linear history
- Prevents merge commits (enforces rebase or squash)

#### ✅ Do not allow bypassing the above settings
- Even admins must follow the rules

#### ❌ Allow force pushes: DISABLED
- Prevents rewriting history on main

#### ❌ Allow deletions: DISABLED
- Prevents accidental branch deletion

### Step 3: Save Protection Rules

Click **Create** or **Save changes**

---

## 🔄 Development Workflow

### 1. Create Feature Branch

```bash
# Start from latest main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Develop on Feature Branch

```bash
# Make changes
vim src/betbot_strategies/new_strategy.py

# Commit frequently
git add .
git commit -m "feat: add new strategy"

# Push to your branch
git push origin feature/your-feature-name
```

**Note**: You can push broken commits to feature branches - they're not protected!

### 3. Validate Locally (Optional but Recommended)

```bash
# Run validation script
./scripts/validate-build.sh

# Or manually
pytest tests/ -v
python -m py_compile duckdice_cli.py
```

### 4. Open Pull Request

```bash
# Via GitHub CLI
gh pr create --base main --head feature/your-feature-name \
  --title "Add new strategy" \
  --body "Implements XYZ strategy with ABC features"

# Or via GitHub web interface
# Click "Pull requests" → "New pull request"
```

### 5. Wait for CI/CD

GitHub Actions will automatically:
- Run tests on 9 configurations (3 OS × 3 Python versions)
- Run code quality checks
- Report status on PR

**You'll see**:
```
✅ Validation on ubuntu-latest - Python 3.9
✅ Validation on ubuntu-latest - Python 3.11
✅ Validation on ubuntu-latest - Python 3.12
✅ Validation on windows-latest - Python 3.9
... (all 9 must pass)
✅ Code Quality
✅ PR Validation Summary
```

### 6. Merge Pull Request

**If all checks pass**:
- Green "Merge pull request" button enabled
- Click "Merge pull request"
- Choose merge strategy (Squash recommended)
- Click "Confirm merge"

**If any check fails**:
- Red "Some checks were not successful"
- Cannot merge until fixed
- Push more commits to fix
- CI/CD runs again automatically

### 7. Automatic Release

After merge to main:
- `build-and-release.yml` workflow triggers
- Builds Windows/macOS/Linux executables
- Publishes to PyPI (if version bumped)
- Creates GitHub release with artifacts

---

## 🚫 What's Prevented

### ❌ Direct Commits to Main
```bash
# This will be REJECTED:
git checkout main
git commit -m "quick fix"
git push origin main
# Error: Protected branch - use pull request
```

### ❌ Merging with Failing Tests
```
PR status: ❌ Some checks were not successful
[Merge] button: DISABLED (greyed out)
```

### ❌ Force Pushes
```bash
git push origin main --force
# Error: Protected branch - force push disabled
```

### ❌ Bypassing Protection
```
Even repository admins must:
- Create PR
- Wait for CI/CD
- Merge only when green
```

---

## ✅ What's Allowed

### ✅ Feature Branch Development
```bash
# Totally fine - not protected:
git checkout -b experiment
git commit -m "WIP: broken code"
git push origin experiment --force  # Force push allowed
```

### ✅ Multiple Commits in PR
```bash
# Push as many times as needed:
git push origin feature/my-feature
git push origin feature/my-feature  # Again
git push origin feature/my-feature  # And again
# CI/CD runs on each push
```

### ✅ Merge After Fixes
```bash
# Initial push: ❌ Tests fail
git push origin feature/fix

# Fix issues
git commit -m "fix: resolve test failures"
git push origin feature/fix

# Now: ✅ Tests pass
# Merge allowed!
```

---

## 📊 CI/CD Status Checks

### Required Checks (11 total)

1. **Validation on ubuntu-latest - Python 3.9**
2. **Validation on ubuntu-latest - Python 3.11**
3. **Validation on ubuntu-latest - Python 3.12**
4. **Validation on windows-latest - Python 3.9**
5. **Validation on windows-latest - Python 3.11**
6. **Validation on windows-latest - Python 3.12**
7. **Validation on macos-latest - Python 3.9**
8. **Validation on macos-latest - Python 3.11**
9. **Validation on macos-latest - Python 3.12**
10. **Code Quality** (no legacy files, core decoupled)
11. **PR Validation Summary** (overall status)

### What Each Check Does

**Validation Jobs**:
- Syntax check (py_compile)
- Import verification (21+ strategies)
- Test suite (pytest with coverage)
- Package build (pip install)
- CLI functionality test

**Code Quality**:
- No .bak, .old, _deprecated files
- No archive directories
- Core has no UI imports
- Repository cleanliness

**PR Summary**:
- Aggregates all results
- Final pass/fail status
- Blocks merge if any check fails

---

## 🔍 Troubleshooting

### PR Checks Not Running

**Problem**: Opened PR but no CI/CD runs

**Solution**:
1. Check workflow file exists: `.github/workflows/pr-validation.yml`
2. Check workflow syntax (no YAML errors)
3. Check repository permissions: Actions enabled
4. Wait 30 seconds - can be delayed

### Checks Failing

**Problem**: Red X on checks

**Solution**:
1. Click "Details" to see logs
2. Fix the issue in your branch
3. Commit and push - CI runs automatically
4. Repeat until green

### Can't Merge Even Though Checks Pass

**Problem**: Green checks but merge disabled

**Solution**:
1. Branch may be out of date with main
2. Click "Update branch" button
3. Wait for CI to run again
4. Then merge

### Need to Bypass Protection (Emergency)

**Problem**: Critical hotfix needed immediately

**Solution**:
1. **Don't bypass** - defeats the purpose
2. Instead: Create PR, wait for CI (usually < 10 minutes)
3. If truly urgent: Temporarily disable protection
   - Settings → Branches → Edit rule
   - Uncheck "Do not allow bypassing"
   - Merge your fix
   - **Re-enable immediately**

---

## 📝 Example PR Workflow

### Complete Example

```bash
# 1. Start from main
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/add-kelly-strategy

# 3. Make changes
vim src/betbot_strategies/kelly_criterion.py
vim tests/test_kelly_criterion.py

# 4. Commit
git add .
git commit -m "feat: add Kelly Criterion strategy

- Implements fractional Kelly betting
- Adds comprehensive tests
- Updates strategy list
- Documents parameters
"

# 5. Push to remote
git push origin feature/add-kelly-strategy

# 6. Open PR
gh pr create --base main --head feature/add-kelly-strategy \
  --title "Add Kelly Criterion strategy" \
  --body "
## Summary
Adds Kelly Criterion betting strategy for optimal bet sizing.

## Changes
- New strategy: kelly_criterion.py
- Tests: test_kelly_criterion.py
- Documentation updated

## Testing
- ✅ All tests pass locally
- ✅ Syntax validated
- ✅ CLI tested
"

# 7. Wait for CI/CD (automatic)
# GitHub shows: ⏳ Running checks...

# 8. If checks fail, fix and push again
git commit -m "fix: resolve test failures"
git push origin feature/add-kelly-strategy
# CI runs again automatically

# 9. When all green, merge via GitHub UI
# ✅ All checks passed
# Click "Merge pull request"

# 10. Delete branch (optional)
git branch -d feature/add-kelly-strategy
git push origin --delete feature/add-kelly-strategy
```

---

## 🎯 Summary

### Setup Required (One-Time)

1. ✅ Create `.github/workflows/pr-validation.yml` (done)
2. ✅ Configure branch protection rules (GitHub Settings)
3. ✅ Add required status checks (11 checks)
4. ✅ Enforce rules for everyone including admins

### Daily Workflow

1. Create feature branch
2. Develop and commit
3. Open pull request
4. Wait for CI/CD (automatic)
5. Merge when green
6. Main stays buildable ✅

### Protection Guarantees

- ✅ Main always buildable
- ✅ All tests pass before merge
- ✅ No broken commits
- ✅ Code quality enforced
- ✅ No bypassing (even admins)

---

## 📚 Related Files

- `.github/workflows/pr-validation.yml` - PR CI/CD workflow
- `.github/workflows/build-and-release.yml` - Post-merge release workflow
- `.github/DEVELOPMENT_GUARDRAILS.md` - Development standards
- `scripts/validate-build.sh` - Local validation script

---

**Status**: Ready to configure on GitHub repository settings

*Last Updated: 2026-01-17*
