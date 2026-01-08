"""
Emergency Stop System
Global hotkey (Ctrl+Shift+S) for immediate betting halt
"""

import threading
from typing import Callable, Optional

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Warning: pynput not installed. Emergency stop hotkey disabled.")
    print("Install with: pip install pynput")


class EmergencyStopManager:
    """
    Manages global emergency stop hotkey (Ctrl+Shift+S).
    Works even when GUI window is not focused.
    """
    
    def __init__(self, stop_callback: Callable[[], None]):
        """
        Initialize emergency stop manager.
        
        Args:
            stop_callback: Function to call when emergency stop is triggered
        """
        self.stop_callback = stop_callback
        self.listener: Optional[keyboard.Listener] = None
        self.current_keys = set()
        self.enabled = PYNPUT_AVAILABLE
        
        # Define the emergency combination: Ctrl+Shift+S
        self.emergency_combo = {
            keyboard.Key.ctrl_l,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char('s')
        }
        
        # Also accept right control
        self.emergency_combo_alt = {
            keyboard.Key.ctrl_r,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char('s')
        }
    
    def on_press(self, key):
        """Handle key press events."""
        try:
            self.current_keys.add(key)
            
            # Check if emergency combination is pressed
            if self._is_emergency_combo():
                print("\n🚨 EMERGENCY STOP TRIGGERED (Ctrl+Shift+S)")
                self.stop_callback()
                
        except AttributeError:
            # Handle special keys
            pass
    
    def on_release(self, key):
        """Handle key release events."""
        try:
            if key in self.current_keys:
                self.current_keys.discard(key)
        except:
            pass
    
    def _is_emergency_combo(self) -> bool:
        """Check if current keys match emergency combination."""
        # Normalize the current keys for comparison
        normalized_keys = set()
        for key in self.current_keys:
            if key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                normalized_keys.add(keyboard.Key.ctrl_l)
            elif isinstance(key, keyboard.KeyCode) and hasattr(key, 'char') and key.char == 's':
                normalized_keys.add(keyboard.KeyCode.from_char('s'))
            else:
                normalized_keys.add(key)
        
        # Check both combinations
        return (
            self.emergency_combo.issubset(normalized_keys) or
            self.emergency_combo_alt.issubset(normalized_keys)
        )
    
    def start(self):
        """Start listening for emergency stop hotkey."""
        if not self.enabled:
            print("Emergency stop not available (pynput not installed)")
            return
        
        if self.listener is not None:
            return  # Already running
        
        def listener_thread():
            with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            ) as listener:
                self.listener = listener
                listener.join()
        
        thread = threading.Thread(target=listener_thread, daemon=True)
        thread.start()
        print("✅ Emergency stop hotkey enabled: Ctrl+Shift+S")
    
    def stop(self):
        """Stop listening for emergency stop hotkey."""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            self.current_keys.clear()
            print("Emergency stop hotkey disabled")


# Fallback implementation without pynput
class EmergencyStopManagerFallback:
    """Fallback when pynput is not available."""
    
    def __init__(self, stop_callback: Callable[[], None]):
        self.stop_callback = stop_callback
        self.enabled = False
    
    def start(self):
        """No-op when pynput not available."""
        pass
    
    def stop(self):
        """No-op when pynput not available."""
        pass
