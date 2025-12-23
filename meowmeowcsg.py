"""
MeowMeowCSG - Constructive Solid Geometry operations for GiraffeCAD

This module provides CSG primitives and operations for representing timber cuts
and geometry operations. All operations use SymPy symbolic math for exact computation.
"""

from sympy import Matrix, Rational, Expr
from typing import List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Type aliases (matching giraffe.py)
V2 = Matrix  # 2D vector - 2x1 Matrix
V3 = Matrix  # 3D vector - 3x1 Matrix  
Direction3D = Matrix  # 3D direction vector - 3x1 Matrix
Numeric = Union[float, int, Expr]  # Numeric values (prefer Rational for exact computation)


class MeowMeowCSG(ABC):
    """Base class for all CSG operations."""
    
    @abstractmethod
    def __repr__(self) -> str:
        """String representation for debugging."""
        pass


@dataclass
class HalfPlane(MeowMeowCSG):
    """
    An infinite half-plane defined by a normal vector and offset from origin.
    
    The half-plane includes all points P such that: (P - origin) · normal >= offset
    where origin is provided externally when evaluating the CSG.
    
    The offset represents the signed distance from the origin along the normal direction
    where the plane is located. Positive offset moves the plane in the direction of the normal.
    
    Args:
        normal: Normal vector pointing into the half-space (3x1 Matrix)
        offset: Distance from origin along normal direction where plane is located (default: 0)
    """
    normal: Direction3D
    offset: Numeric = 0
    
    def __repr__(self) -> str:
        return f"HalfPlane(normal={self.normal.T}, offset={self.offset})"


@dataclass
class Prism(MeowMeowCSG):
    """
    A prism with rectangular cross-section, optionally infinite in one or both ends.
    
    The prism is defined by:
    - A cross-section size (width x height) in the plane perpendicular to the orientation
    - An orientation direction (the axis of the prism)
    - Start and end distances along the orientation from the origin
    
    Use None for start_distance or end_distance to make the prism infinite in that direction.
    
    The cross-section orientation is determined by the orientation vector, similar to
    how Timber orientation works. The size[0] is the width and size[1] is the height
    of the rectangular cross-section.
    
    Args:
        size: Cross-section dimensions [width, height] (2x1 Matrix)
        orientation: Direction of the prism's axis (3x1 Matrix)
        start_distance: Distance from origin to start of prism (None = infinite)
        end_distance: Distance from origin to end of prism (None = infinite)
    """
    size: V2
    orientation: Direction3D
    start_distance: Optional[Numeric] = None  # None means infinite in negative direction
    end_distance: Optional[Numeric] = None    # None means infinite in positive direction
    
    def __repr__(self) -> str:
        return (f"Prism(size={self.size.T}, orientation={self.orientation.T}, "
                f"start={self.start_distance}, end={self.end_distance})")


@dataclass
class Cylinder(MeowMeowCSG):
    """
    A cylinder with circular cross-section, optionally infinite in one or both ends.
    
    The cylinder is defined by:
    - An axis direction
    - A radius
    - Start and end distances along the axis from the origin
    
    Use None for start_distance or end_distance to make the cylinder infinite in that direction.
    
    Args:
        axis_direction: Direction of the cylinder's axis (3x1 Matrix)
        radius: Radius of the cylinder
        start_distance: Distance from origin to start of cylinder (None = infinite)
        end_distance: Distance from origin to end of cylinder (None = infinite)
    """
    axis_direction: Direction3D  # direction of the cylinder's axis, which is the +Z local axis
    radius: Numeric
    start_distance: Optional[Numeric] = None  # None means infinite in negative direction
    end_distance: Optional[Numeric] = None    # None means infinite in positive direction
    
    def __repr__(self) -> str:
        return (f"Cylinder(axis={self.axis_direction.T}, "
                f"radius={self.radius}, "
                f"start={self.start_distance}, end={self.end_distance})")


@dataclass
class Union(MeowMeowCSG):
    """
    CSG union operation - combines multiple CSG objects.
    
    The union represents the set of all points that are in ANY of the child CSG objects.
    
    Args:
        children: List of CSG objects to union together
    """
    children: List[MeowMeowCSG]
    
    def __repr__(self) -> str:
        return f"Union({len(self.children)} children)"


@dataclass
class Difference(MeowMeowCSG):
    """
    CSG difference operation - subtracts multiple CSG objects from a base object.
    
    The difference represents: base - subtract[0] - subtract[1] - ...
    All points in base that are NOT in any of the subtract objects.
    
    Args:
        base: The base CSG object to subtract from
        subtract: List of CSG objects to subtract from the base
    """
    base: MeowMeowCSG
    subtract: List[MeowMeowCSG]
    
    def __repr__(self) -> str:
        return f"Difference(base={self.base}, subtract={len(self.subtract)} objects)"


# Helper functions for creating common CSG primitives

def create_prism(size: V2, orientation: Direction3D,
                start_distance: Optional[Numeric] = None,
                end_distance: Optional[Numeric] = None) -> Prism:
    """
    Create a prism with optional bounds.
    
    This single constructor handles all cases:
    - Finite prism: provide both start_distance and end_distance
    - Semi-infinite prism: provide only end_distance (infinite in negative direction)
    - Infinite prism: omit both distances (infinite in both directions)
    
    Args:
        size: Cross-section dimensions [width, height] (2x1 Matrix)
        orientation: Direction of the prism's axis
        start_distance: Distance from origin to start of prism (None = infinite in negative direction)
        end_distance: Distance from origin to end of prism (None = infinite in positive direction)
        
    Returns:
        Prism with specified extent
        
    Examples:
        # Finite prism
        create_prism(size, orientation, start_distance=0, end_distance=10)
        
        # Semi-infinite prism (infinite in negative direction)
        create_prism(size, orientation, end_distance=10)
        
        # Infinite prism
        create_prism(size, orientation)
    """
    return Prism(
        size=size,
        orientation=orientation,
        start_distance=start_distance,
        end_distance=end_distance
    )


def create_cylinder(axis_direction: Direction3D, radius: Numeric,
                   start_distance: Optional[Numeric] = None,
                   end_distance: Optional[Numeric] = None) -> Cylinder:
    """
    Create a cylinder with optional bounds.
    
    This single constructor handles all cases:
    - Finite cylinder: provide both start_distance and end_distance
    - Semi-infinite cylinder: provide only end_distance (infinite in negative direction)
    - Infinite cylinder: omit both distances (infinite in both directions)
    
    Args:
        axis_direction: Direction of the cylinder's axis
        radius: Radius of the cylinder
        start_distance: Distance from origin to start of cylinder (None = infinite in negative direction)
        end_distance: Distance from origin to end of cylinder (None = infinite in positive direction)
        
    Returns:
        Cylinder with specified extent
        
    Examples:
        # Finite cylinder
        create_cylinder(axis_direction, radius, start_distance=0, end_distance=10)
        
        # Semi-infinite cylinder (infinite in negative direction)
        create_cylinder(axis_direction, radius, end_distance=10)
        
        # Infinite cylinder
        create_cylinder(axis_direction, radius)
    """
    return Cylinder(
        axis_direction=axis_direction,
        radius=radius,
        start_distance=start_distance,
        end_distance=end_distance
    )

