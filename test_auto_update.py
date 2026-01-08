#!/usr/bin/env python3
"""Test auto-update functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from updater import AutoUpdater


def test_update_check():
    """Test checking for updates."""
    print("=" * 60)
    print("Testing Auto-Update Functionality")
    print("=" * 60)
    
    updater = AutoUpdater()
    
    print(f"\n📦 Current Version: v{updater.CURRENT_VERSION}")
    print(f"🔗 Repository: {updater.GITHUB_REPO}")
    print(f"🌐 API URL: {updater.GITHUB_API_URL}")
    
    print("\n🔍 Checking for updates...")
    update_available = updater.check_for_updates()
    
    if update_available:
        print(f"\n✅ Update available!")
        print(f"   Latest version: v{updater.latest_version}")
        print(f"   Download URL: {updater.download_url}")
        
        # Don't actually install in test
        print("\n⚠️  Skipping installation in test mode")
        print("   To install, run the GUI and use Help → Check for Updates")
    else:
        print(f"\n✅ You're running the latest version!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_update_check()
