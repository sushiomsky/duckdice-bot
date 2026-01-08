"""
Sound Notification System
Cross-platform audio alerts for betting events
"""

import os
import platform
import subprocess
import threading
from pathlib import Path
from typing import Optional


class SoundManager:
    """
    Manages sound notifications for betting events.
    Cross-platform: macOS (afplay), Linux (paplay/aplay), Windows (winsound).
    """
    
    SOUNDS = {
        'win': 'win.wav',
        'loss': 'loss.wav',
        'target': 'target.wav',
        'stop': 'stop.wav',
        'alert': 'alert.wav',
    }
    
    def __init__(self, enabled: bool = False, sounds_dir: Optional[Path] = None):
        """
        Initialize sound manager.
        
        Args:
            enabled: Whether sounds are enabled
            sounds_dir: Directory containing sound files
        """
        self.enabled = enabled
        self.sounds_dir = sounds_dir or Path(__file__).parent.parent.parent / "assets" / "sounds"
        self.platform = platform.system()
        
        # Create sounds directory if needed
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate placeholder sound files if they don't exist
        self._ensure_sound_files()
    
    def _ensure_sound_files(self):
        """Create placeholder sound files if they don't exist."""
        # For now, we'll just create empty placeholder files
        # In production, these should be actual WAV files
        for sound_file in self.SOUNDS.values():
            path = self.sounds_dir / sound_file
            if not path.exists():
                # Create empty file as placeholder
                path.touch()
    
    def play(self, sound_name: str, async_play: bool = True):
        """
        Play a sound effect.
        
        Args:
            sound_name: Name of sound to play (win, loss, target, stop, alert)
            async_play: Play sound in background thread (non-blocking)
        """
        if not self.enabled:
            return
        
        if sound_name not in self.SOUNDS:
            print(f"Unknown sound: {sound_name}")
            return
        
        sound_file = self.sounds_dir / self.SOUNDS[sound_name]
        if not sound_file.exists() or sound_file.stat().st_size == 0:
            # File doesn't exist or is empty placeholder
            return
        
        if async_play:
            thread = threading.Thread(target=self._play_sound, args=(sound_file,), daemon=True)
            thread.start()
        else:
            self._play_sound(sound_file)
    
    def _play_sound(self, sound_file: Path):
        """Internal method to play sound file."""
        try:
            if self.platform == "Darwin":  # macOS
                subprocess.run(['afplay', str(sound_file)], check=False, capture_output=True)
            
            elif self.platform == "Linux":
                # Try paplay (PulseAudio) first, then aplay (ALSA)
                try:
                    subprocess.run(['paplay', str(sound_file)], check=True, capture_output=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    subprocess.run(['aplay', str(sound_file)], check=False, capture_output=True)
            
            elif self.platform == "Windows":
                import winsound
                winsound.PlaySound(str(sound_file), winsound.SND_FILENAME)
            
        except Exception as e:
            # Silently fail - sounds are non-critical
            pass
    
    def play_win(self):
        """Play win sound."""
        self.play('win')
    
    def play_loss(self):
        """Play loss sound."""
        self.play('loss')
    
    def play_target(self):
        """Play target reached sound."""
        self.play('target')
    
    def play_stop(self):
        """Play stop/alert sound."""
        self.play('stop')
    
    def play_alert(self):
        """Play generic alert sound."""
        self.play('alert')
    
    def set_enabled(self, enabled: bool):
        """Enable or disable sounds."""
        self.enabled = enabled
    
    def is_enabled(self) -> bool:
        """Check if sounds are enabled."""
        return self.enabled
    
    def beep(self):
        """Play system beep (fallback when no sound files available)."""
        if not self.enabled:
            return
        
        try:
            if self.platform == "Darwin":  # macOS
                os.system('afplay /System/Library/Sounds/Ping.aiff &')
            elif self.platform == "Linux":
                os.system('beep &')
            elif self.platform == "Windows":
                import winsound
                winsound.Beep(1000, 200)  # 1000 Hz for 200ms
        except:
            pass  # Silently fail
