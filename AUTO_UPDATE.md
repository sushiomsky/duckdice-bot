# Auto-Update System

DuckDice Bot now includes an automatic update system that checks for new releases on GitHub and installs them with one click.

## ✨ Features

- ✅ **Automatic checking** on startup (runs 2 seconds after launch)
- ✅ **Manual checking** via Help → Check for Updates menu
- ✅ **One-click installation** from GitHub releases
- ✅ **Automatic backup** before update
- ✅ **Rollback on failure** - restores backup if update fails
- ✅ **Non-blocking** - checks run in background thread
- ✅ **Toast notifications** - friendly update status messages
- ✅ **Semantic versioning** - compares versions correctly (3.2.1 > 3.2.0)

## 🚀 How It Works

### Automatic Update Checks

1. GUI launches
2. After 2 seconds, background thread starts
3. Checks GitHub API for latest release: `https://api.github.com/repos/sushiomsky/duckdice-bot/releases/latest`
4. Compares latest version with current version (v3.2.0)
5. If newer version exists, shows dialog asking user to install

### Manual Update Checks

1. Go to **Help** → **Check for Updates**
2. Immediately checks for updates
3. Shows result dialog

### Update Installation Process

When user clicks "Yes" to install update:

1. **Download**: Fetches latest release zipball from GitHub
2. **Extract**: Unzips to temporary directory
3. **Backup**: Creates backup of current installation
4. **Install**: Copies new files over existing (preserves user data)
5. **Cleanup**: Removes temporary files
6. **Success**: Shows success message, prompts restart

### What Gets Preserved

During updates, these files/directories are **NOT** overwritten:
- `bet_history/` - Your betting history
- `rng_analysis/` - Your RNG analysis data
- `.env` - Your environment configuration
- `__pycache__/` - Python cache files
- `.git/` - Git repository data

### What Gets Updated

All code files are replaced with new versions:
- `duckdice_gui_ultimate.py`
- `duckdice.py`
- `src/` - All source modules
- `requirements.txt`
- `README.md`, `CHANGELOG.md`
- Documentation files

## 🔧 Configuration

### Disable Automatic Checking

If you don't want automatic update checks on startup:

1. Open Settings (Ctrl+,)
2. Add this to your config:
   ```json
   {
     "check_updates_on_startup": false
   }
   ```

Or edit `~/.duckdice/config.json` manually:
```json
{
  "check_updates_on_startup": false
}
```

### Version Information

Current version is stored in:
- `src/updater/auto_updater.py` - `CURRENT_VERSION = "3.2.0"`
- Update this when releasing new versions

## 🧪 Testing

Test the update checker:
```bash
python3 test_auto_update.py
```

This will:
- Check current version
- Query GitHub API for latest release
- Report if update is available
- **NOT** install update (test mode only)

## 📦 Creating a Release

To enable auto-update for users, create a GitHub release:

1. **Tag the version**:
   ```bash
   git tag -a v3.2.1 -m "Release v3.2.1 - Bug fixes"
   git push origin v3.2.1
   ```

2. **Create GitHub Release**:
   - Go to https://github.com/sushiomsky/duckdice-bot/releases/new
   - Select tag: `v3.2.1`
   - Title: "v3.2.1 - Bug Fixes"
   - Description: Release notes from CHANGELOG.md
   - Click "Publish release"

3. **Users will auto-update**:
   - Next time they launch the app, it will detect v3.2.1
   - They can click "Yes" to download and install

## 🔒 Security

- Uses HTTPS for all downloads
- Verifies zipball structure before extracting
- Creates backup before touching any files
- Automatic rollback on any error
- No code execution from downloaded files (just file copying)

## ❌ Troubleshooting

### "Network error checking for updates"
- Check internet connection
- GitHub API may be rate-limited (60 requests/hour unauthenticated)
- Try again later

### "Update Failed"
- Backup is automatically restored
- Check permissions (need write access to installation directory)
- Try manual update via git pull

### Update check never runs
- Check `check_updates_on_startup` in config
- Check if GUI is connected to internet
- Look for errors in console output

### "No update available" but there is one
- Clear cache and restart app
- Check version in src/updater/auto_updater.py
- Verify GitHub release was published correctly

## 🛠️ Advanced Usage

### Programmatic Usage

```python
from updater import AutoUpdater

# Create updater
updater = AutoUpdater(callback=print)

# Check for updates
if updater.check_for_updates():
    print(f"Update available: v{updater.latest_version}")
    
    # Install update
    success = updater.download_and_install_update()
    if success:
        print("Update installed! Please restart.")
```

### With GUI Integration

```python
from updater import AutoUpdater

# Create updater with toast callback
updater = AutoUpdater(callback=lambda msg: Toast.show(self, msg))

# Check async (non-blocking)
updater.check_updates_async(parent_window=self)
```

## 📝 API Reference

### `AutoUpdater` Class

**Constructor**:
```python
AutoUpdater(callback: Optional[Callable] = None)
```

**Methods**:
- `check_for_updates() -> bool` - Check if update available
- `download_and_install_update() -> bool` - Download and install
- `check_and_prompt_update(parent_window=None) -> bool` - Check and show dialog
- `check_updates_async(parent_window=None)` - Check in background thread

**Attributes**:
- `GITHUB_REPO` - Repository name (sushiomsky/duckdice-bot)
- `CURRENT_VERSION` - Current version (3.2.0)
- `update_available` - Boolean, True if update found
- `latest_version` - Latest version string
- `download_url` - Download URL for latest release

## 🎯 Future Enhancements

Potential improvements:
- [ ] Delta updates (only download changed files)
- [ ] Cryptographic signature verification
- [ ] Update changelog preview before install
- [ ] Scheduled update checks (daily/weekly)
- [ ] Beta/alpha release channel selection
- [ ] Bandwidth-aware downloading with progress bar
- [ ] Resume failed downloads

---

**Auto-update system powered by GitHub Releases** 🚀
