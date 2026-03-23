"""
Ticket system for timber identification and tracking.

A Ticket is a simple identifier attached to timbers for naming and tracking purposes.
"""

from dataclasses import dataclass
from typing import Optional

from code_goes_here.rule import Direction3D, Numeric


@dataclass(frozen=True)
class Ticket:
    """Identifier for a timber.
    
    Tickets provide a simple name-based identification system for timbers.
    They are immutable to ensure consistency throughout the timber framing system.
    
    Attributes:
        name: Human-readable name for the timber (default: "[no-name]")
    """
    name: str = "[no-name]"

    # TODO is this how I want to do parents?
    parent: "Ticket" = None  # Optional reference to a parent ticket for hierarchical relationships


@dataclass(frozen=True)
class FolderTIcket(Ticket):
    """A Ticket that represents a folder or grouping of timbers.
    
    This can be used to organize timbers into logical groups, such as all timbers in a particular wall or roof section.
    """
    pass



class AssemblyFreedom:
    """
    
    Always interpreted in global space

    """

    # simple case, allows 2 directional DOFs, we can add more complex cases later if needed
    direction_freedom_1: Optional[Direction3D]
    direction_freedom_2: Optional[Direction3D]

    def invert(self) -> "AssemblyFreedom":
        """Return a new AssemblyFreedom with the allowed directions inverted."""
        return AssemblyFreedom(
            direction_freedom_1=self.direction_freedom_1.invert() if self.direction_freedom_1 else None,
            direction_freedom_2=self.direction_freedom_2.invert() if self.direction_freedom_2 else None,
        )

class JointTicket(Ticket):
    pass