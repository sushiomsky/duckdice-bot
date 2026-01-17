# Quick Setup: Enable Branch Protection

**Time required**: 2 minutes  
**Do this once**: After this setup, main will be protected forever

---

## 🎯 What This Does

After these steps:
- ✅ **No one can commit directly to main** (including you)
- ✅ **All changes must go through Pull Requests**
- ✅ **GitHub blocks merge until all 11 CI/CD checks pass**
- ✅ **Main is always buildable** (guaranteed by GitHub)

---

## 📋 Setup Steps

### 1. Go to Repository Settings

1. Open https://github.com/sushiomsky/duckdice-bot
2. Click **Settings** tab (top right)
3. Click **Branches** in left sidebar

### 2. Add Branch Protection Rule

1. Click **Add branch protection rule** button
2. **Branch name pattern**: Type `main`

### 3. Enable Required Settings

Check these boxes:

#### ✅ Require a pull request before merging
- Set **Required approvals**: `0` (no manual review needed)
- ✅ Check "Dismiss stale pull request approvals when new commits are pushed"

#### ✅ Require status checks to pass before merging
- ✅ Check "Require branches to be up to date before merging"
- In the search box, type and select each of these **11 checks**:
  
  ```
  1. Validation on ubuntu-latest - Python 3.9
  2. Validation on ubuntu-latest - Python 3.11
  3. Validation on ubuntu-latest - Python 3.12
  4. Validation on windows-latest - Python 3.9
  5. Validation on windows-latest - Python 3.11
  6. Validation on windows-latest - Python 3.12
  7. Validation on macos-latest - Python 3.9
  8. Validation on macos-latest - Python 3.11
  9. Validation on macos-latest - Python 3.12
  10. Code Quality
  11. PR Validation Summary
  ```
  
  **Note**: These will appear after first PR is opened. If not visible now, save and come back later.

#### ✅ Require linear history
- Prevents merge commits

#### ✅ Do not allow bypassing the above settings
- Even admins must follow rules

#### Leave UNCHECKED:
- ❌ Allow force pushes (disabled)
- ❌ Allow deletions (disabled)

### 4. Save

Click **Create** button at bottom

---

## ✅ Verification

Test that it works:

```bash
# Try to commit directly to main (should fail)
git checkout main
echo "test" >> README.md
git commit -m "test"
git push origin main

# Expected: ❌ Error: Protected branch
```

If you see the error, protection is working! ✅

---

## 🔄 Daily Workflow (After Setup)

### Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature
```

### Develop and Push
```bash
# Make changes
git add .
git commit -m "feat: add feature"
git push origin feature/your-feature
```

### Open Pull Request
```bash
# Via GitHub CLI
gh pr create --base main --head feature/your-feature

# Or via GitHub web UI
# Click "Pull requests" → "New pull request"
```

### Wait for CI/CD (Automatic)
- GitHub runs 11 checks automatically
- Usually completes in 5-10 minutes
- You'll see status on PR page

### Merge When Green
- When all checks pass: ✅
- "Merge pull request" button enabled
- Click to merge
- GitHub triggers release workflow automatically

---

## 🚨 Important Notes

1. **First PR won't show all checks** - They appear after workflow runs once
2. **Come back to settings** after first PR to select the 11 checks
3. **All future PRs** will require those checks before merge
4. **No bypassing** even for emergencies (good practice!)

---

## 📚 Full Documentation

For complete details, see: `docs/BRANCH_PROTECTION.md`

---

**Setup once, protected forever!** ✅
