"""Auto-update manager for checking and installing updates from GitHub releases."""

import json
import os
import sys
import urllib.request
import urllib.error
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Callable
import threading


class AutoUpdater:
    """Manages auto-update functionality for DuckDice Bot."""
    
    GITHUB_REPO = "sushiomsky/duckdice-bot"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    CURRENT_VERSION = "3.2.0"
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize auto-updater.
        
        Args:
            callback: Optional callback function to report progress
        """
        self.callback = callback
        self.update_available = False
        self.latest_version = None
        self.download_url = None
        
    def _log(self, message: str):
        """Log message via callback or print."""
        if self.callback:
            self.callback(message)
        else:
            print(f"[AutoUpdater] {message}")
    
    def check_for_updates(self) -> bool:
        """
        Check if a new version is available on GitHub.
        
        Returns:
            True if update is available, False otherwise
        """
        try:
            self._log("Checking for updates...")
            
            # Fetch latest release info from GitHub API
            request = urllib.request.Request(
                self.GITHUB_API_URL,
                headers={'User-Agent': 'DuckDice-Bot-AutoUpdater'}
            )
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Parse version info
            tag_name = data.get('tag_name', '')
            self.latest_version = tag_name.lstrip('v')
            
            # Compare versions
            if self._compare_versions(self.latest_version, self.CURRENT_VERSION) > 0:
                self.update_available = True
                self.download_url = data.get('zipball_url')
                self._log(f"✅ Update available: v{self.latest_version} (current: v{self.CURRENT_VERSION})")
                return True
            else:
                self._log(f"✅ You're running the latest version (v{self.CURRENT_VERSION})")
                return False
                
        except urllib.error.URLError as e:
            self._log(f"⚠️ Network error checking for updates: {e}")
            return False
        except Exception as e:
            self._log(f"⚠️ Error checking for updates: {e}")
            return False
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Returns:
            1 if version1 > version2
            0 if version1 == version2
            -1 if version1 < version2
        """
        def normalize(v):
            return [int(x) for x in v.replace('v', '').split('.')]
        
        v1_parts = normalize(version1)
        v2_parts = normalize(version2)
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        
        return 0
    
    def download_and_install_update(self) -> bool:
        """
        Download and install the latest update.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.update_available or not self.download_url:
            self._log("⚠️ No update available to install")
            return False
        
        try:
            self._log(f"📥 Downloading v{self.latest_version}...")
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix='duckdice_update_')
            zip_path = os.path.join(temp_dir, 'update.zip')
            
            # Download update
            urllib.request.urlretrieve(self.download_url, zip_path)
            self._log("✅ Download complete")
            
            # Extract
            self._log("📦 Extracting update...")
            extract_dir = os.path.join(temp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find extracted directory (GitHub zipballs have a single root directory)
            extracted_items = os.listdir(extract_dir)
            if len(extracted_items) != 1:
                raise Exception("Unexpected archive structure")
            
            source_dir = os.path.join(extract_dir, extracted_items[0])
            
            # Get current installation directory
            current_dir = Path(__file__).parent.parent.parent.absolute()
            
            # Backup current installation
            backup_dir = os.path.join(temp_dir, 'backup')
            self._log("💾 Creating backup...")
            shutil.copytree(current_dir, backup_dir, ignore=shutil.ignore_patterns(
                '__pycache__', '*.pyc', '.git', 'bet_history', 'rng_analysis', '.env'
            ))
            
            # Install update (copy new files over existing)
            self._log("🔄 Installing update...")
            self._copy_update_files(source_dir, str(current_dir))
            
            # Clean up temp files
            shutil.rmtree(temp_dir)
            
            self._log(f"✅ Update to v{self.latest_version} installed successfully!")
            self._log("🔄 Please restart the application to use the new version")
            
            return True
            
        except Exception as e:
            self._log(f"❌ Error installing update: {e}")
            
            # Attempt to restore backup if it exists
            if 'backup_dir' in locals() and os.path.exists(backup_dir):
                self._log("🔄 Restoring backup...")
                try:
                    self._copy_update_files(backup_dir, str(current_dir))
                    self._log("✅ Backup restored")
                except Exception as restore_error:
                    self._log(f"❌ Error restoring backup: {restore_error}")
            
            return False
    
    def _copy_update_files(self, src: str, dst: str):
        """Copy files from source to destination, preserving directory structure."""
        for item in os.listdir(src):
            # Skip git files and other non-essential items
            if item in ['.git', '.github', '__pycache__', '.DS_Store', 'bet_history', 'rng_analysis']:
                continue
            
            src_path = os.path.join(src, item)
            dst_path = os.path.join(dst, item)
            
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
    
    def check_and_prompt_update(self, parent_window=None) -> bool:
        """
        Check for updates and prompt user to install if available.
        
        Args:
            parent_window: Optional tkinter parent window for dialog
            
        Returns:
            True if update was installed, False otherwise
        """
        if not self.check_for_updates():
            return False
        
        # If parent window provided, use tkinter dialog
        if parent_window:
            try:
                from tkinter import messagebox
                response = messagebox.askyesno(
                    "Update Available",
                    f"A new version (v{self.latest_version}) is available!\n"
                    f"Current version: v{self.CURRENT_VERSION}\n\n"
                    f"Would you like to download and install it now?",
                    parent=parent_window
                )
                
                if response:
                    success = self.download_and_install_update()
                    if success:
                        messagebox.showinfo(
                            "Update Complete",
                            "Update installed successfully!\n"
                            "Please restart the application.",
                            parent=parent_window
                        )
                        return True
                    else:
                        messagebox.showerror(
                            "Update Failed",
                            "Failed to install update.\n"
                            "Please try again or update manually.",
                            parent=parent_window
                        )
                
            except ImportError:
                pass
        
        return False
    
    def check_updates_async(self, parent_window=None):
        """Check for updates in background thread."""
        thread = threading.Thread(
            target=self.check_and_prompt_update,
            args=(parent_window,),
            daemon=True
        )
        thread.start()
