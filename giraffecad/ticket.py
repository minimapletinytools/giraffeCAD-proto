"""Ticket system for hierarchical naming and metadata.

Tickets are immutable labels that can be attached to timbers, joints, accessories,
and feature concepts. The base class contains shared hierarchy behavior and
subclasses represent concrete ticket categories.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from giraffecad.rule import Direction3D


@dataclass(frozen=True)
class Ticket(ABC):
    """Base ticket shared by all ticket categories.

    The category is represented by the concrete subclass rather than an enum field.
    """

    name: str = "[no-name]"
    parent: Optional["Ticket"] = None

    @abstractmethod
    def is_concept(self) -> bool:
        """Concept tickets represent logical entities such as joints/features."""
        raise NotImplementedError

    @abstractmethod
    def is_construction(self) -> bool:
        """Construction tickets represent physical entities or organization."""
        raise NotImplementedError

@dataclass(frozen=True)
class ConstructionTicket(Ticket):
    """Base class for physical/object-hierarchy tickets."""

    def is_concept(self) -> bool:
        return False

    def is_construction(self) -> bool:
        return True


@dataclass(frozen=True)
class ConceptTicket(Ticket):
    """Base class for logical/conceptual tickets."""

    def is_concept(self) -> bool:
        return True

    def is_construction(self) -> bool:
        return False


@dataclass(frozen=True)
class FolderTicket(ConstructionTicket):
    """Ticket that represents a grouping node in the hierarchy."""


@dataclass(frozen=True)
class TimberTicket(ConstructionTicket):
    """Ticket metadata for physical timber members."""

    material: Optional[str] = None
    reference_faces: Optional[tuple[str, ...]] = None


@dataclass(frozen=True)
class AccessoryTicket(ConstructionTicket):
    """Ticket metadata for accessories (pegs, wedges, hardware, etc.)."""


@dataclass(frozen=True)
class BoardTicket(ConstructionTicket):
    """Ticket metadata for board-like members."""

@dataclass(frozen=True)
class AssemblyFreedom:
    """Assembly DOF in global space (up to two allowed insertion directions)."""

    direction_freedom_1: Optional[Direction3D] = None
    direction_freedom_2: Optional[Direction3D] = None

    @staticmethod
    def _invert_direction(direction: Optional[Direction3D]) -> Optional[Direction3D]:
        if direction is None:
            return None
        return -direction

    def invert(self) -> "AssemblyFreedom":
        """Return a new AssemblyFreedom with each allowed direction inverted."""
        return AssemblyFreedom(
            direction_freedom_1=self._invert_direction(self.direction_freedom_1),
            direction_freedom_2=self._invert_direction(self.direction_freedom_2),
        )


@dataclass(frozen=True)
class JointTicket(ConceptTicket):
    """Concept ticket metadata for joints and assembly sequencing."""

    joint_type: Optional[str] = None
    assembly_order: Optional[int] = None
    assembly_freedom: Optional[AssemblyFreedom] = None