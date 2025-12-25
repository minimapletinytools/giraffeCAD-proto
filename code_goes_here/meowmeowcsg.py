"""
MeowMeowCSG - Constructive Solid Geometry operations for GiraffeCAD

This module provides CSG primitives and operations for representing timber cuts
and geometry operations. All operations use SymPy symbolic math for exact computation.
"""

from sympy import Matrix, Rational, Expr, sqrt, oo
from typing import List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from .moothymoth import Orientation

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


    # ALL IMPLEMENTATIONS ARE UNTESTED LOL
    @abstractmethod
    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary of the CSG in the given direction.
        
        Returns a point on the CSG boundary that is minimal (most negative) along the given direction.
        In other words, finds the point P on the CSG surface where P·direction is minimized.
        
        Args:
            direction: Direction vector to minimize along (does not need to be normalized)
            
        Returns:
            A point on the CSG boundary that is minimal in the given direction
            This may return any point, rather than the origin point projected onto the boundary like you'd expect :(
            
        Raises:
            ValueError: If the CSG is infinite/unbounded in the negative direction
        """
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
    
    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary point of the half-plane in the given direction.
        
        For a half-plane, there is only a minimal boundary when the direction is exactly
        opposite (anti-parallel) to the normal vector. In all other cases, the half-plane
        is unbounded in that direction.
        
        Args:
            direction: Direction to minimize along
            
        Returns:
            Point at offset distance along normal (when direction is opposite to normal)
            
        Raises:
            ValueError: If direction is not exactly opposite to the normal
        """
        # Normalize both vectors for comparison
        dir_norm = direction.norm()
        if dir_norm == 0:
            raise ValueError("Direction vector cannot be zero")
        dir_normalized = direction / dir_norm
        
        normal_norm = self.normal.norm()
        normal_normalized = self.normal / normal_norm
        
        # Check if direction is exactly opposite to normal (anti-parallel)
        # direction should equal -k * normal for some positive k
        # Equivalently: dir_normalized should equal -normal_normalized
        diff = dir_normalized + normal_normalized
        
        # Check if the difference is zero (within tolerance for symbolic computation)
        if diff.norm() > Rational(1, 10000):
            raise ValueError("HalfPlane is unbounded except in the direction exactly opposite to its normal")
        
        # Return the origin point on the plane boundary
        return self.normal * self.offset


@dataclass
class Prism(MeowMeowCSG):
    """
    A prism with rectangular cross-section, optionally infinite in one or both ends.
    
    The prism is defined by:
    - A cross-section size (width x height) in the local XY plane
    - An orientation (rotation matrix defining the local coordinate system)
    - Start and end distances along the local Z-axis from the origin
    
    Use None for start_distance or end_distance to make the prism infinite in that direction.
    
    The orientation matrix defines the local coordinate system where:
    - X-axis (first column) is the width direction (size[0])
    - Y-axis (second column) is the height direction (size[1])
    - Z-axis (third column) is the length/axis direction
    
    Args:
        size: Cross-section dimensions [width, height] (2x1 Matrix)
        orientation: Orientation matrix defining the prism's coordinate system
        start_distance: Distance from origin to start of prism (None = infinite)
        end_distance: Distance from origin to end of prism (None = infinite)
    """
    size: V2
    orientation: Orientation
    start_distance: Optional[Numeric] = None  # None means infinite in negative direction
    end_distance: Optional[Numeric] = None    # None means infinite in positive direction
    
    def __repr__(self) -> str:
        return (f"Prism(size={self.size.T}, orientation={self.orientation}, "
                f"start={self.start_distance}, end={self.end_distance})")
    
    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary point of the prism in the given direction.
        
        For a finite prism, we check all 8 corners and return the one with minimum dot product
        with the direction. For semi-infinite prisms, we only raise an error if querying in the
        infinite direction.
        """
        # If infinite in both directions, always unbounded
        if self.start_distance is None and self.end_distance is None:
            raise ValueError("Cannot compute minimal boundary for prism that is infinite in both directions")
        
        # Extract axes from orientation matrix
        # X-axis (width direction) is first column
        # Y-axis (height direction) is second column
        # Z-axis (length/axis direction) is third column
        width_dir = Matrix([
            self.orientation.matrix[0, 0],
            self.orientation.matrix[1, 0],
            self.orientation.matrix[2, 0]
        ])
        height_dir = Matrix([
            self.orientation.matrix[0, 1],
            self.orientation.matrix[1, 1],
            self.orientation.matrix[2, 1]
        ])
        length_dir = Matrix([
            self.orientation.matrix[0, 2],
            self.orientation.matrix[1, 2],
            self.orientation.matrix[2, 2]
        ])
        
        # Check if we're querying in an infinite direction
        axis_component = (direction.T * length_dir)[0, 0]
        
        if self.start_distance is None and axis_component < 0:
            raise ValueError("Cannot compute minimal boundary for prism that is infinite in negative direction")
        if self.end_distance is None and axis_component > 0:
            raise ValueError("Cannot compute minimal boundary for prism that is infinite in positive direction")
        
        # Half dimensions
        half_width = self.size[0] / 2
        half_height = self.size[1] / 2
        
        # Generate corners from the finite end(s)
        min_dot = None
        min_point = None
        
        # Determine which ends to check
        ends_to_check = []
        if self.start_distance is not None:
            ends_to_check.append(self.start_distance)
        if self.end_distance is not None:
            ends_to_check.append(self.end_distance)
        
        for distance in ends_to_check:
            for w_sign in [-1, 1]:
                for h_sign in [-1, 1]:
                    corner = (length_dir * distance + 
                             width_dir * (w_sign * half_width) + 
                             height_dir * (h_sign * half_height))
                    
                    dot = (corner.T * direction)[0, 0]
                    if min_dot is None or dot < min_dot:
                        min_dot = dot
                        min_point = corner
        
        return min_point


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
    
    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary point of the cylinder in the given direction.
        
        For a finite cylinder, we find the point on the surface with minimum dot product
        with the direction vector. For semi-infinite cylinders, we only raise an error if 
        querying in the infinite direction.
        """
        # If infinite in both directions, always unbounded
        if self.start_distance is None and self.end_distance is None:
            raise ValueError("Cannot compute minimal boundary for cylinder that is infinite in both directions")
        
        # Normalize axis
        axis = self.axis_direction / self.axis_direction.norm()
        
        # Check if we're querying in an infinite direction
        axis_component = (direction.T * axis)[0, 0]
        
        if self.start_distance is None and axis_component < 0:
            raise ValueError("Cannot compute minimal boundary for cylinder that is infinite in negative direction")
        if self.end_distance is None and axis_component > 0:
            raise ValueError("Cannot compute minimal boundary for cylinder that is infinite in positive direction")
        
        # Decompose direction into parallel and perpendicular components to axis
        dir_parallel = axis_component * axis
        dir_perp = direction - dir_parallel
        
        # For the radial component, the minimal point on the circular cross-section
        # is in the opposite direction of dir_perp
        dir_perp_norm = dir_perp.norm()
        
        if dir_perp_norm == 0:
            # Direction is parallel to axis, minimal point is anywhere on the appropriate circle
            # Choose an arbitrary point on the circle
            if abs(axis[0]) < Rational(1, 2):
                perpendicular = Matrix([1, 0, 0])
            else:
                perpendicular = Matrix([0, 1, 0])
            
            radial = axis.cross(perpendicular)
            radial = radial / radial.norm()
            
            # Check the finite end cap(s)
            candidates = []
            if self.start_distance is not None:
                candidates.append(axis * self.start_distance + radial * self.radius)
            if self.end_distance is not None:
                candidates.append(axis * self.end_distance + radial * self.radius)
            
            # Return the one with minimum dot product
            min_point = min(candidates, key=lambda p: (p.T * direction)[0, 0])
            return min_point
        else:
            # Minimal radial point is opposite to perpendicular component
            radial_dir = -dir_perp / dir_perp_norm
            
            # Check points on the finite end cap(s) at the minimal radial position
            candidates = []
            if self.start_distance is not None:
                candidates.append(axis * self.start_distance + radial_dir * self.radius)
            if self.end_distance is not None:
                candidates.append(axis * self.end_distance + radial_dir * self.radius)
            
            # Return the one with minimum dot product
            min_point = min(candidates, key=lambda p: (p.T * direction)[0, 0])
            return min_point


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
    
    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary point of the union in the given direction.
        
        For a union, the minimal boundary is the minimum of all children's minimal boundaries.
        """
        if not self.children:
            raise ValueError("Cannot compute minimal boundary for empty union")
        
        min_dot = None
        min_point = None
        
        for child in self.children:
            try:
                point = child.minimal_boundary_in_direction(direction)
                dot = (point.T * direction)[0, 0]
                
                if min_dot is None or dot < min_dot:
                    min_dot = dot
                    min_point = point
            except ValueError:
                # Child is unbounded in this direction, skip it
                continue
        
        if min_point is None:
            raise ValueError("All children of union are unbounded in the given direction")
        
        return min_point


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
    
    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary point of the difference in the given direction.
        
        For a difference operation, the minimal boundary is determined by the base object
        (subtracting material doesn't extend the boundary in the negative direction).
        """
        return self.base.minimal_boundary_in_direction(direction)


# Helper functions for creating common CSG primitives

def create_prism(size: V2, orientation: Orientation,
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
        orientation: Orientation matrix defining the prism's coordinate system
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

