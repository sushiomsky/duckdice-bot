"""
Observer pattern for betting engine events.

Provides interfaces and base classes for creating different UI/interface implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Callable
from .events import BettingEvent, EventType


class EventObserver(ABC):
    """
    Abstract base class for event observers.
    
    Implement this to create custom interfaces (CLI, TUI, GUI, Web, etc.)
    """
    
    @abstractmethod
    def on_event(self, event: BettingEvent) -> None:
        """
        Called when an event is emitted by the engine.
        
        Args:
            event: The betting event that occurred
        """
        pass
    
    def supports_event_type(self, event_type: EventType) -> bool:
        """
        Check if this observer wants to receive events of a specific type.
        
        Override this to filter events. Default is to receive all events.
        
        Args:
            event_type: The type of event
            
        Returns:
            True if this observer wants to receive this event type
        """
        return True


class EventEmitter:
    """
    Event emitter that manages observers and distributes events.
    
    The betting engine uses this to emit events to registered observers.
    """
    
    def __init__(self):
        self._observers: List[EventObserver] = []
        self._event_callbacks: List[Callable[[BettingEvent], None]] = []
    
    def add_observer(self, observer: EventObserver) -> None:
        """
        Register an observer to receive events.
        
        Args:
            observer: The observer to register
        """
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer: EventObserver) -> None:
        """
        Unregister an observer.
        
        Args:
            observer: The observer to remove
        """
        if observer in self._observers:
            self._observers.remove(observer)
    
    def add_callback(self, callback: Callable[[BettingEvent], None]) -> None:
        """
        Register a simple callback function for events.
        
        Args:
            callback: Function that takes a BettingEvent
        """
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[BettingEvent], None]) -> None:
        """
        Unregister a callback function.
        
        Args:
            callback: The callback to remove
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    def emit(self, event: BettingEvent) -> None:
        """
        Emit an event to all registered observers and callbacks.
        
        Args:
            event: The event to emit
        """
        # Notify observers
        for observer in self._observers:
            if observer.supports_event_type(event.event_type):
                try:
                    observer.on_event(event)
                except Exception as e:
                    # Don't let observer errors crash the engine
                    print(f"Error in observer {observer.__class__.__name__}: {e}")
        
        # Notify callbacks
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                # Don't let callback errors crash the engine
                print(f"Error in event callback: {e}")
    
    def clear(self) -> None:
        """Remove all observers and callbacks"""
        self._observers.clear()
        self._event_callbacks.clear()


class CompositeObserver(EventObserver):
    """
    Observer that delegates to multiple sub-observers.
    
    Useful for combining multiple interface components.
    """
    
    def __init__(self):
        self._sub_observers: List[EventObserver] = []
    
    def add_observer(self, observer: EventObserver) -> None:
        """Add a sub-observer"""
        if observer not in self._sub_observers:
            self._sub_observers.append(observer)
    
    def remove_observer(self, observer: EventObserver) -> None:
        """Remove a sub-observer"""
        if observer in self._sub_observers:
            self._sub_observers.remove(observer)
    
    def on_event(self, event: BettingEvent) -> None:
        """Delegate event to all sub-observers"""
        for observer in self._sub_observers:
            if observer.supports_event_type(event.event_type):
                observer.on_event(event)


class FilteredObserver(EventObserver):
    """
    Observer that filters events by type before delegating.
    
    Wraps another observer and only passes through specified event types.
    """
    
    def __init__(self, wrapped_observer: EventObserver, allowed_types: List[EventType]):
        self._wrapped = wrapped_observer
        self._allowed_types = set(allowed_types)
    
    def on_event(self, event: BettingEvent) -> None:
        """Only pass event if type is allowed"""
        if event.event_type in self._allowed_types:
            self._wrapped.on_event(event)
    
    def supports_event_type(self, event_type: EventType) -> bool:
        """Check if event type is in allowed list"""
        return event_type in self._allowed_types
