"""
MeowMeowCSG - Constructive Solid Geometry operations for GiraffeCAD

This module provides CSG primitives and operations for representing timber cuts
and geometry operations. All operations use SymPy symbolic math for exact computation.
"""

from sympy import Matrix, Rational, Expr, sqrt, oo
from typing import List, Optional, Union
from dataclasses import dataclass, field
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

    @abstractmethod
    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the CSG object.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is inside or on the boundary of the CSG object, False otherwise
        """
        pass

    @abstractmethod
    def is_point_on_boundary(self, point: V3) -> bool:
        """
        Check if a point is on the boundary of the CSG object.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is on the boundary of the CSG object, False otherwise
        """
        pass


@dataclass(frozen=True)
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

    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the half-plane.
        
        A point P is in the half-plane if (P · normal) >= offset
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is in the half-plane (including boundary), False otherwise
        """
        # Compute dot product: point · normal
        dot_product = (point.T * self.normal)[0, 0]
        return dot_product >= self.offset

    def is_point_on_boundary(self, point: V3) -> bool:
        """
        Check if a point is on the boundary of the half-plane.
        
        A point P is on the boundary if (P · normal) == offset
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is on the boundary plane, False otherwise
        """
        # Compute dot product: point · normal
        dot_product = (point.T * self.normal)[0, 0]
        return dot_product == self.offset


@dataclass(frozen=True)
class Prism(MeowMeowCSG):
    """
    A prism with rectangular cross-section, optionally infinite in one or both ends.
    Note,they are parameterized similar to the Timber class which is atypical for such a primitive.
    
    The prism is defined by:
    - A position (translation from origin)
    - A cross-section size (width (x-axis)) x height (y-axis)) in the local XY plane
    - An orientation (rotation matrix defining the local coordinate system)
    - Start and end distances along the local Z-axis from the position

    So the center point of the size cross section is at position and the timber extends out in -z by start_distance and +z by end_distance.
    
    Use None for start_distance or end_distance to make the prism infinite in that direction.
    
    The orientation matrix defines the local coordinate system where:
    - X-axis (first column) is the width direction (size[0])
    - Y-axis (second column) is the height direction (size[1])
    - Z-axis (third column) is the length/axis direction
    
    Args:
        size: Cross-section dimensions [width, height] (2x1 Matrix)
        orientation: Orientation matrix defining the prism's coordinate system
        position: Position of the prism origin in global coordinates (3x1 Matrix, default: origin)
        start_distance: Distance from position along Z-axis to start of prism (None = 
        -infinite)
        end_distance: Distance from position along Z-axis to end of prism (None = infinite)
    """
    size: V2
    orientation: Orientation
    position: V3 = field(default_factory=lambda: Matrix([0, 0, 0]))  # Position in global coordinates
    start_distance: Optional[Numeric] = None  # None means infinite in negative direction
    end_distance: Optional[Numeric] = None    # None means infinite in positive direction

    def get_bottom_position(self) -> V3:
        """
        Get the position of the bottom of the prism (at start_distance).
        Only valid for prisms with finite start_distance.
        
        Returns:
            The 3D position at the bottom of the prism
            
        Raises:
            ValueError: If start_distance is None (infinite prism)
        """
        if self.start_distance is None:
            raise ValueError("Cannot get bottom position of infinite prism (start_distance is None)")
        return self.position - self.orientation.matrix * Matrix([0, 0, self.start_distance])
    
    def get_top_position(self) -> V3:
        """
        Get the position of the top of the prism (at end_distance).
        Only valid for prisms with finite end_distance.
        
        Returns:
            The 3D position at the top of the prism
            
        Raises:
            ValueError: If end_distance is None (infinite prism)
        """
        if self.end_distance is None:
            raise ValueError("Cannot get top position of infinite prism (end_distance is None)")
        return self.position + self.orientation.matrix * Matrix([0, 0, self.end_distance])
    
    def __repr__(self) -> str:
        return (f"Prism(size={self.size.T}, orientation={self.orientation}, "
                f"position={self.position.T}, start={self.start_distance}, end={self.end_distance})")
    
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
                    corner = (self.position + 
                             length_dir * distance + 
                             width_dir * (w_sign * half_width) + 
                             height_dir * (h_sign * half_height))
                    
                    dot = (corner.T * direction)[0, 0]
                    if min_dot is None or dot < min_dot:
                        min_dot = dot
                        min_point = corner
        
        return min_point

    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the prism.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is inside or on the boundary of the prism, False otherwise
        """
        # Transform point to local coordinates
        # Local origin is at self.position
        local_point = point - self.position
        
        # Extract axes from orientation matrix
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
        
        # Project onto local axes
        x_coord = (local_point.T * width_dir)[0, 0]
        y_coord = (local_point.T * height_dir)[0, 0]
        z_coord = (local_point.T * length_dir)[0, 0]
        
        # Check bounds in each dimension
        half_width = self.size[0] / 2
        half_height = self.size[1] / 2
        
        # Check width and height bounds
        if abs(x_coord) > half_width or abs(y_coord) > half_height:
            return False
        
        # Check length bounds
        if self.start_distance is not None and z_coord < self.start_distance:
            return False
        if self.end_distance is not None and z_coord > self.end_distance:
            return False
        
        return True

    def is_point_on_boundary(self, point: V3) -> bool:
        """
        Check if a point is on the boundary of the prism.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is on the boundary of the prism, False otherwise
        """
        # First check if point is contained
        if not self.contains_point(point):
            return False
        
        # Transform point to local coordinates
        local_point = point - self.position
        
        # Extract axes from orientation matrix
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
        
        # Project onto local axes
        x_coord = (local_point.T * width_dir)[0, 0]
        y_coord = (local_point.T * height_dir)[0, 0]
        z_coord = (local_point.T * length_dir)[0, 0]
        
        # Check if on any face
        half_width = self.size[0] / 2
        half_height = self.size[1] / 2
        
        # On width faces
        if abs(x_coord) == half_width:
            return True
        
        # On height faces
        if abs(y_coord) == half_height:
            return True
        
        # On length faces (if finite)
        if self.start_distance is not None and z_coord == self.start_distance:
            return True
        if self.end_distance is not None and z_coord == self.end_distance:
            return True
        
        return False


@dataclass(frozen=True)
class Cylinder(MeowMeowCSG):
    """
    A cylinder with circular cross-section, optionally infinite in one or both ends.
    
    The cylinder is defined by:
    - A position (translation from origin)
    - An axis direction
    - A radius
    - Start and end distances along the axis from the position
    
    So the center point of the radius cross section is at position and the cylinder extends out in -z by start_distance and +z by end_distance.

    Use None for start_distance or end_distance to make the cylinder infinite in that direction.
    
    Args:
        axis_direction: Direction of the cylinder's axis (3x1 Matrix)
        radius: Radius of the cylinder
        position: Position of the cylinder origin in global coordinates (3x1 Matrix, default: origin)
        start_distance: Distance from position to start of cylinder (None = -infinite)
        end_distance: Distance from position to end of cylinder (None = infinite)
    """
    axis_direction: Direction3D  # direction of the cylinder's axis, which is the +Z local axis
    radius: Numeric
    position: V3 = field(default_factory=lambda: Matrix([0, 0, 0]))  # Position in global coordinates
    start_distance: Optional[Numeric] = None  # None means infinite in negative direction
    end_distance: Optional[Numeric] = None    # None means infinite in positive direction
    
    def __repr__(self) -> str:
        return (f"Cylinder(axis={self.axis_direction.T}, "
                f"radius={self.radius}, "
                f"position={self.position.T}, "
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
                candidates.append(self.position + axis * self.start_distance + radial * self.radius)
            if self.end_distance is not None:
                candidates.append(self.position + axis * self.end_distance + radial * self.radius)
            
            # Return the one with minimum dot product
            min_point = min(candidates, key=lambda p: (p.T * direction)[0, 0])
            return min_point
        else:
            # Minimal radial point is opposite to perpendicular component
            radial_dir = -dir_perp / dir_perp_norm
            
            # Check points on the finite end cap(s) at the minimal radial position
            candidates = []
            if self.start_distance is not None:
                candidates.append(self.position + axis * self.start_distance + radial_dir * self.radius)
            if self.end_distance is not None:
                candidates.append(self.position + axis * self.end_distance + radial_dir * self.radius)
            
            # Return the one with minimum dot product
            min_point = min(candidates, key=lambda p: (p.T * direction)[0, 0])
            return min_point

    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the cylinder.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is inside or on the boundary of the cylinder, False otherwise
        """
        # Transform point to local coordinates
        local_point = point - self.position
        
        # Normalize axis
        axis = self.axis_direction / self.axis_direction.norm()
        
        # Project onto axis to get axial coordinate
        axial_coord = (local_point.T * axis)[0, 0]
        
        # Check axial bounds
        if self.start_distance is not None and axial_coord < self.start_distance:
            return False
        if self.end_distance is not None and axial_coord > self.end_distance:
            return False
        
        # Calculate radial distance from axis
        axial_projection = axis * axial_coord
        radial_vector = local_point - axial_projection
        radial_distance = radial_vector.norm()
        
        # Check if within radius
        return radial_distance <= self.radius

    def is_point_on_boundary(self, point: V3) -> bool:
        """
        Check if a point is on the boundary of the cylinder.
        
        A point is on the boundary if it's either:
        1. On the cylindrical surface (at radius distance from axis)
        2. On one of the end caps (if finite)
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is on the boundary of the cylinder, False otherwise
        """
        # First check if point is contained
        if not self.contains_point(point):
            return False
        
        # Transform point to local coordinates
        local_point = point - self.position
        
        # Normalize axis
        axis = self.axis_direction / self.axis_direction.norm()
        
        # Project onto axis to get axial coordinate
        axial_coord = (local_point.T * axis)[0, 0]
        
        # Calculate radial distance from axis
        axial_projection = axis * axial_coord
        radial_vector = local_point - axial_projection
        radial_distance = radial_vector.norm()
        
        # On cylindrical surface
        if radial_distance == self.radius:
            return True
        
        # On end caps (if finite and at the end)
        if self.start_distance is not None and axial_coord == self.start_distance:
            return True
        if self.end_distance is not None and axial_coord == self.end_distance:
            return True
        
        return False


@dataclass(frozen=True)
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

    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the union.
        
        A point is in the union if it's in ANY of the children.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is in any of the children, False otherwise
        """
        return any(child.contains_point(point) for child in self.children)

    def is_point_on_boundary(self, point: V3) -> bool:
        """
        Check if a point is on the boundary of the union.
        
        A point is on the boundary if it's on the boundary of at least one child
        and not in the interior of any other child.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is on the boundary of the union, False otherwise
        """
        # Point must be contained in the union
        if not self.contains_point(point):
            return False
        
        # Check if on boundary of any child and not strictly inside all others
        on_any_boundary = False
        for child in self.children:
            if child.contains_point(point):
                if child.is_point_on_boundary(point):
                    on_any_boundary = True
                else:
                    # Point is strictly inside this child, so not on union boundary
                    return False
        
        return on_any_boundary


@dataclass(frozen=True)
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
    
    # TODO this is probably still broken
    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary point of the difference in the given direction.
        
        For a difference operation (base - subtract), the minimal boundary can be:
        1. On the original base boundary (if not removed by subtraction)
        2. On a new boundary created by the subtraction (e.g., a cut plane)
        
        We check all potential boundaries and return the most minimal one.
        
        For Prism - HalfPlane specifically, we:
        1. Check all corners of the prism that remain after subtraction
        2. Check points on the half-plane boundary that intersect the prism
        """
        from sympy import simplify
        
        min_point = None
        min_dot = None
        
        # Strategy: Check a set of candidate points on the difference surface
        # and find the one with minimum dot product with the direction
        
        # 1. Check if base's minimal boundary is still valid (not removed)
        try:
            base_boundary = self.base.minimal_boundary_in_direction(direction)
            if self.contains_point(base_boundary):
                min_point = base_boundary
                min_dot = simplify((min_point.T * direction)[0, 0])
        except ValueError:
            # Base doesn't have a minimal boundary in this direction
            pass
        
        # 2. For Prism base, check all corners (some may have been removed by subtraction)
        if isinstance(self.base, Prism):
            # Generate all 8 corners (or 4 corners for semi-infinite prisms)
            width = self.base.size[0]
            height = self.base.size[1]
            
            # Half-dimensions from center
            hw = width / 2
            hh = height / 2
            
            # Local offsets for the 4 corners of the cross-section
            corner_offsets = [
                Matrix([hw, hh]),
                Matrix([hw, -hh]),
                Matrix([-hw, hh]),
                Matrix([-hw, -hh])
            ]
            
            # Check corners at both ends (if finite)
            z_values = []
            if self.base.start_distance is not None:
                z_values.append(self.base.start_distance)
            if self.base.end_distance is not None:
                z_values.append(self.base.end_distance)
            
            for z in z_values:
                for offset in corner_offsets:
                    # Corner in local coordinates
                    corner_local = Matrix([offset[0], offset[1], z])
                    # Transform to global coordinates
                    corner_global = self.base.position + self.base.orientation.matrix * corner_local
                    
                    # Check if this corner is in the difference (not removed by subtraction)
                    if self.contains_point(corner_global):
                        dot = simplify((corner_global.T * direction)[0, 0])
                        if min_dot is None or dot < min_dot:
                            min_point = corner_global
                            min_dot = dot
        
        # 3. For HalfPlane subtract, check if the plane intersects the base
        # and find points on that intersection
        for sub in self.subtract:
            if isinstance(sub, HalfPlane):
                # For HalfPlane, we need to find points on the plane that are in the base
                # and have minimal dot product with the direction
                
                # Try to get a point on the plane
                # The plane is defined by: normal · point >= offset
                # A point on the boundary is: point = normal * offset
                point_on_plane = sub.normal * sub.offset
                
                # Check if this specific point is on the difference boundary
                if self.base.contains_point(point_on_plane) and self.is_point_on_boundary(point_on_plane):
                    dot = simplify((point_on_plane.T * direction)[0, 0])
                    if min_dot is None or dot < min_dot:
                        min_point = point_on_plane
                        min_dot = dot
        
        if min_point is None:
            raise ValueError("Could not find minimal boundary for difference in the given direction")
        
        return min_point

    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the difference.
        
        A point is in the difference if it's in the base and NOT in any of the subtract objects.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is in base but not in any subtract objects, False otherwise
        """
        # Point must be in base
        if not self.base.contains_point(point):
            return False
        
        # Point must not be in any subtract object
        return not any(sub.contains_point(point) for sub in self.subtract)

    def is_point_on_boundary(self, point: V3) -> bool:
        """
        Check if a point is on the boundary of the difference.
        
        A point is on the boundary if:
        1. It's contained in the difference (base - subtract), AND
        2. Either:
           a. It's on the boundary of the base, OR
           b. It's strictly inside the base but on the boundary of at least one subtract object
        
        Note: For case 2b, the point creates a new boundary surface (the "hole" surface).
        The point must be on the subtract boundary but NOT inside the subtract (i.e., on the
        surface of the hole facing the remaining material).
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is on the boundary of the difference, False otherwise
        """
        # Point must be contained in base
        if not self.base.contains_point(point):
            return False
        
        # Check if point is in any subtract region (strictly inside, not just boundary)
        in_subtract_interior = False
        on_subtract_boundary = False
        
        for sub in self.subtract:
            if sub.contains_point(point):
                if sub.is_point_on_boundary(point):
                    on_subtract_boundary = True
                else:
                    # Point is strictly inside a subtract object
                    in_subtract_interior = True
                    break
        
        # If point is strictly inside any subtract, it's not on the difference boundary
        if in_subtract_interior:
            return False
        
        # If point is on subtract boundary, it's on the difference boundary
        if on_subtract_boundary:
            return True
        
        # Otherwise, check if it's on the base boundary
        return self.base.is_point_on_boundary(point)





@dataclass(frozen=True)
class ConvexPolygonExtrusion(MeowMeowCSG):
    """
    An extruded Convex Polygon shape.
    
    """
    # list of ordered (x,y) points in the polygon with the last point connecting to the first point
    # must be convex!!
    points: List[V2] 
    # length of the extrusion along the +Z axis
    length: Numeric 
    orientation: Orientation
    position: V3 = field(default_factory=lambda: Matrix([0, 0, 0]))  # Position in global coordinates

    def __repr__(self) -> str:
        return (f"ConvexPolygonExtrusion({len(self.points)} points, "
                f"length={self.length}, position={self.position.T})")
    
    def is_valid(self) -> bool:
        """
        Check if the ConvexPolygonExtrusion is valid
        
        Checks:
        1. At least 3 points
        2. Positive length
        3. Polygon is convex (all turns go the same direction)
        
        Returns:
            True if valid, False otherwise
        """
        if len(self.points) < 3 or self.length <= 0:
            return False
        
        # Check convexity: all cross products of consecutive edges should have the same sign
        # For a convex polygon, as we traverse the vertices, we should always turn the same way
        n = len(self.points)
        
        # Compute 2D cross product for each triplet of consecutive points
        def cross_product(i):
            p0, p1, p2 = self.points[i], self.points[(i + 1) % n], self.points[(i + 2) % n]
            edge1, edge2 = p1 - p0, p2 - p1
            return edge1[0] * edge2[1] - edge1[1] * edge2[0]
        
        # Generate all cross products and filter out zeros (collinear points)
        cross_products = [cross_product(i) for i in range(n)]
        non_zero_crosses = [cp for cp in cross_products if cp != 0]
        
        # Reject if all collinear, otherwise check all turns go the same direction
        return (len(non_zero_crosses) > 0 and 
                (all(cp > 0 for cp in non_zero_crosses) or 
                 all(cp < 0 for cp in non_zero_crosses)))

    def minimal_boundary_in_direction(self, direction: Direction3D) -> V3:
        """
        Get the minimal boundary point of the extruded polygon in the given direction.
        
        We check all vertices at both the start (z=0) and end (z=length) faces
        and return the one with minimum dot product with the direction.
        
        Args:
            direction: Direction to minimize along
            
        Returns:
            Point on the boundary with minimum dot product with direction
        """
        min_dot = None
        min_point = None
        
        # Check all vertices at both z=0 and z=length
        for z_offset in [0, self.length]:
            for point_2d in self.points:
                # Create 3D point in local coordinates, then transform to global
                point_local = Matrix([point_2d[0], point_2d[1], z_offset])
                point_global = self.position + self.orientation.matrix * point_local
                
                dot = (point_global.T * direction)[0, 0]
                if min_dot is None or dot < min_dot:
                    min_dot = dot
                    min_point = point_global
        
        return min_point

    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the extruded polygon.
        
        A point is inside if:
        1. Its Z coordinate (in local space) is between 0 and length
        2. Its XY coordinates (in local space) are inside the convex polygon
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is inside or on the boundary, False otherwise
        """
        # Transform point to local coordinates
        local_point = point - self.position
        local_coords = self.orientation.invert().matrix * local_point
        
        x_coord = local_coords[0]
        y_coord = local_coords[1]
        z_coord = local_coords[2]
        
        # Check Z bounds
        if z_coord < 0 or z_coord > self.length:
            return False
        
        # Check if (x_coord, y_coord) is inside the convex polygon
        # For a convex polygon, a point is inside if it's on the correct side
        # of all edges
        point_2d = Matrix([x_coord, y_coord])
        
        for i in range(len(self.points)):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % len(self.points)]
            
            # Edge vector from p1 to p2
            edge = p2 - p1
            
            # Vector from p1 to test point
            to_point = point_2d - p1
            
            # Cross product in 2D: edge × to_point
            # If polygon vertices are ordered counter-clockwise, 
            # cross product should be >= 0 for point to be inside
            cross = edge[0] * to_point[1] - edge[1] * to_point[0]
            
            if cross < 0:
                return False
        
        return True

    def is_point_on_boundary(self, point: V3) -> bool:
        """
        Check if a point is on the boundary of the extruded polygon.
        
        A point is on the boundary if it's contained and either:
        1. On the top or bottom face (z = 0 or z = length)
        2. On one of the side faces (on an edge of the polygon)
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is on the boundary, False otherwise
        """
        # First check if point is contained
        if not self.contains_point(point):
            return False
        
        # Transform point to local coordinates
        local_point = point - self.position
        local_coords = self.orientation.invert().matrix * local_point
        
        x_coord = local_coords[0]
        y_coord = local_coords[1]
        z_coord = local_coords[2]
        
        # Check if on top or bottom face
        if z_coord == 0 or z_coord == self.length:
            return True
        
        # Check if on any edge of the polygon (side face)
        point_2d = Matrix([x_coord, y_coord])
        
        for i in range(len(self.points)):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % len(self.points)]
            
            # Check if point is on the line segment from p1 to p2
            # Use parametric form: p = p1 + t*(p2-p1), where 0 <= t <= 1
            edge = p2 - p1
            to_point = point_2d - p1
            
            # If edge is zero-length, skip it
            edge_length_sq = edge[0]**2 + edge[1]**2
            if edge_length_sq == 0:
                continue
            
            # Project to_point onto edge
            t = (to_point[0] * edge[0] + to_point[1] * edge[1]) / edge_length_sq
            
            # Check if projection is on the segment and point is on the line
            if 0 <= t <= 1:
                closest_point = p1 + edge * t
                distance_sq = (point_2d[0] - closest_point[0])**2 + (point_2d[1] - closest_point[1])**2
                if distance_sq == 0:
                    return True
        
        return False