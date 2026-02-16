"""
Ticket system for timber identification and tracking.

A Ticket is a simple identifier attached to timbers for naming and tracking purposes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    """Identifier for a timber.
    
    Tickets provide a simple name-based identification system for timbers.
    They are immutable to ensure consistency throughout the timber framing system.
    
    Attributes:
        name: Human-readable name for the timber (default: "[no-name]")
    """
    name: str = "[no-name]"
