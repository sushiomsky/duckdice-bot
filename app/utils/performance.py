"""
Performance utilities for DuckDice Bot UI
Debouncing, lazy loading, and optimization helpers
"""

import asyncio
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime, timedelta


class Debouncer:
    """
    Debounce function calls to prevent excessive updates.
    
    Example:
        debouncer = Debouncer(delay=0.5)
        search_input.on_value_change(debouncer.debounce(search_function))
    """
    
    def __init__(self, delay: float = 0.3):
        """
        Initialize debouncer.
        
        Args:
            delay: Delay in seconds before executing the function
        """
        self.delay = delay
        self.task: Optional[asyncio.Task] = None
    
    def debounce(self, func: Callable) -> Callable:
        """
        Create a debounced version of the function.
        
        Args:
            func: Function to debounce
            
        Returns:
            Debounced function
        """
        @wraps(func)
        async def debounced(*args, **kwargs):
            # Cancel previous task if it exists
            if self.task and not self.task.done():
                self.task.cancel()
            
            # Create new delayed task
            async def delayed_call():
                await asyncio.sleep(self.delay)
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            
            self.task = asyncio.create_task(delayed_call())
        
        return debounced
    
    def cancel(self):
        """Cancel pending debounced call"""
        if self.task and not self.task.done():
            self.task.cancel()


class Throttler:
    """
    Throttle function calls to limit execution frequency.
    
    Example:
        throttler = Throttler(interval=1.0)
        button.on_click(throttler.throttle(expensive_function))
    """
    
    def __init__(self, interval: float = 1.0):
        """
        Initialize throttler.
        
        Args:
            interval: Minimum interval in seconds between calls
        """
        self.interval = interval
        self.last_call: Optional[datetime] = None
        self.pending_task: Optional[asyncio.Task] = None
    
    def throttle(self, func: Callable) -> Callable:
        """
        Create a throttled version of the function.
        
        Args:
            func: Function to throttle
            
        Returns:
            Throttled function
        """
        @wraps(func)
        async def throttled(*args, **kwargs):
            now = datetime.now()
            
            # Check if enough time has passed
            if self.last_call is None or (now - self.last_call).total_seconds() >= self.interval:
                self.last_call = now
                
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            else:
                # Schedule for later if not already scheduled
                if self.pending_task is None or self.pending_task.done():
                    async def delayed_call():
                        wait_time = self.interval - (now - self.last_call).total_seconds()
                        if wait_time > 0:
                            await asyncio.sleep(wait_time)
                        
                        self.last_call = datetime.now()
                        if asyncio.iscoroutinefunction(func):
                            await func(*args, **kwargs)
                        else:
                            func(*args, **kwargs)
                    
                    self.pending_task = asyncio.create_task(delayed_call())
        
        return throttled


class LazyLoader:
    """
    Lazy load heavy components only when needed.
    
    Example:
        loader = LazyLoader()
        await loader.load_component(expensive_component_function)
    """
    
    def __init__(self):
        self.loaded_components = set()
    
    async def load_component(self, component_id: str, loader_func: Callable, *args, **kwargs):
        """
        Load a component lazily.
        
        Args:
            component_id: Unique identifier for the component
            loader_func: Function that creates/loads the component
            *args, **kwargs: Arguments to pass to loader_func
        """
        if component_id not in self.loaded_components:
            # Simulate async loading with small delay
            await asyncio.sleep(0.01)
            
            if asyncio.iscoroutinefunction(loader_func):
                await loader_func(*args, **kwargs)
            else:
                loader_func(*args, **kwargs)
            
            self.loaded_components.add(component_id)
    
    def is_loaded(self, component_id: str) -> bool:
        """Check if component is already loaded"""
        return component_id in self.loaded_components
    
    def reset(self):
        """Reset all loaded components"""
        self.loaded_components.clear()


class VirtualScroller:
    """
    Virtual scrolling for long lists to improve performance.
    Only renders visible items + buffer.
    """
    
    def __init__(self, item_height: int = 60, visible_count: int = 10, buffer: int = 5):
        """
        Initialize virtual scroller.
        
        Args:
            item_height: Height of each item in pixels
            visible_count: Number of items visible at once
            buffer: Number of extra items to render above/below
        """
        self.item_height = item_height
        self.visible_count = visible_count
        self.buffer = buffer
        self.scroll_position = 0
    
    def get_visible_range(self, total_items: int) -> tuple[int, int]:
        """
        Get the range of items that should be rendered.
        
        Args:
            total_items: Total number of items in the list
            
        Returns:
            Tuple of (start_index, end_index)
        """
        # Calculate visible range based on scroll position
        start_index = max(0, (self.scroll_position // self.item_height) - self.buffer)
        end_index = min(
            total_items,
            start_index + self.visible_count + (self.buffer * 2)
        )
        
        return start_index, end_index
    
    def update_scroll(self, position: int):
        """Update scroll position"""
        self.scroll_position = position


# Global instances for common use
global_debouncer = Debouncer(delay=0.5)
global_throttler = Throttler(interval=1.0)
global_lazy_loader = LazyLoader()


# Convenience decorators
def debounce(delay: float = 0.3):
    """
    Decorator to debounce a function.
    
    Usage:
        @debounce(0.5)
        def search(query):
            # Will only execute 0.5s after last call
            ...
    """
    debouncer = Debouncer(delay)
    
    def decorator(func):
        return debouncer.debounce(func)
    
    return decorator


def throttle(interval: float = 1.0):
    """
    Decorator to throttle a function.
    
    Usage:
        @throttle(1.0)
        def refresh():
            # Will execute at most once per second
            ...
    """
    throttler = Throttler(interval)
    
    def decorator(func):
        return throttler.throttle(func)
    
    return decorator
