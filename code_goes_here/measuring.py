"""
Measuring and geometric primitives for GiraffeCAD.

This module contains classes for representing geometric primitives like points, lines, and planes
in 3D space, useful for measurements and geometric calculations.
"""

from dataclasses import dataclass
from .moothymoth import V3, Direction3D, Transform

# TODO halfspace class

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

    @staticmethod
    def from_transform_and_direction(transform: Transform, direction: Direction3D) -> 'Plane':
        """
        Create a plane from a transform and a direction.
        
        Args:
            transform: Transform defining the position and orientation
            direction: Direction in the transform's local coordinate system
            
        Returns:
            Plane with normal in global coordinates and point at transform position
        """
        return Plane(transform.orientation.matrix * direction, transform.position)
