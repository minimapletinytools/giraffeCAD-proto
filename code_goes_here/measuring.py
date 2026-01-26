"""
Measuring and geometric primitives for GiraffeCAD.

Measuring functions follows the following pattern:

measure(measurement, feature, timber) -> feature in global space
mark(golbal feature, timber) -> measurement from some local feature on the timber

Note the Measuring feature classes are NOT used for CSG operations, they are only used for measurements and geometric calculations. 
"""

from dataclasses import dataclass
from .moothymoth import *

@dataclass(frozen=True)
class Point:
    """
    Represents a point in 3D space.
    """
    position: V3

    def __repr__(self) -> str:
        return f"Point(position={self.position})"


@dataclass(frozen=True)
class Line:
    """
    Represents an oriented line with origin in 3D space.
    """
    direction: Direction3D
    point: V3

    def __repr__(self) -> str:
        return f"Line(direction={self.direction}, point={self.point})"


@dataclass(frozen=True)
class Plane:
    """
    Represents an oriented plane with origin in 3D space.
    """
    normal: Direction3D
    point: V3

    def __repr__(self) -> str:
        return f"Plane(normal={self.normal}, point={self.point})"

    @classmethod
    def from_transform_and_direction(cls, transform: Transform, direction: Direction3D) -> 'Plane':
        """
        Create a plane from a transform and a direction.
        
        Args:
            transform: Transform defining the position and orientation
            direction: Direction in the transform's local coordinate system
            
        Returns:
            Plane with normal in global coordinates and point at transform position
        """
        return cls(transform.orientation.matrix * direction, transform.position)


@dataclass(frozen=True)
class HalfPlane:
    """
    Represents an oriented half-plane with origin in 3D space.
    """
    normal: Direction3D
    point_on_edge: V3
    edge_direction: Direction3D # MUST be perpendicular to the normal

    def __repr__(self) -> str:
        return f"HalfPlane(normal={self.normal}, point_on_edge={self.point_on_edge}, edge_direction={self.edge_direction})"