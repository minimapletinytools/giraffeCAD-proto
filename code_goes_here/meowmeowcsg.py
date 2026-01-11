"""
MeowMeowCSG - Constructive Solid Geometry operations for GiraffeCAD

This module provides CSG primitives and operations for representing timber cuts
and geometry operations. All operations use SymPy symbolic math for exact computation.
"""

from sympy import Matrix, Rational, Expr, sqrt, oo
from typing import List, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from .moothymoth import Orientation, Transform, V2, V3, Direction3D, Numeric


class MeowMeowCSG(ABC):
    """Base class for all CSG operations."""
    
    @abstractmethod
    def __repr__(self) -> str:
        """String representation for debugging."""
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
    - A transform (position and orientation in global coordinates)
    - A cross-section size (width (x-axis)) x height (y-axis)) in the local XY plane
    - Start and end distances along the local Z-axis from the position

    So the center point of the size cross section is at position and the timber extends out in -z by start_distance and +z by end_distance.
    
    Use None for start_distance or end_distance to make the prism infinite in that direction.
    
    The orientation matrix defines the local coordinate system where:
    - X-axis (first column) is the width direction (size[0])
    - Y-axis (second column) is the height direction (size[1])
    - Z-axis (third column) is the length/axis direction
    
    Args:
        size: Cross-section dimensions [width, height] (2x1 Matrix)
        transform: Transform (position and orientation) in global coordinates (default: identity)
        start_distance: Distance from position along Z-axis to start of prism (None = 
        -infinite)
        end_distance: Distance from position along Z-axis to end of prism (None = infinite)
    """
    size: V2
    transform: Transform = field(default_factory=Transform.identity)
    start_distance: Optional[Numeric] = None  # starting distance of the prism in the direction of the +Z axis. None means infinite in negative direction
    end_distance: Optional[Numeric] = None    # ending distance of the prism in the direction of the +Z axis. None means infinite in positive direction

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
        return self.transform.position - self.transform.orientation.matrix * Matrix([0, 0, self.start_distance])
    
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
        return self.transform.position + self.transform.orientation.matrix * Matrix([0, 0, self.end_distance])
    
    def __repr__(self) -> str:
        return (f"Prism(size={self.size.T}, transform={self.transform}, "
                f"start={self.start_distance}, end={self.end_distance})")
    
    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the prism.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is inside or on the boundary of the prism, False otherwise
        """
        # Transform point to local coordinates
        # Local origin is at self.transform.position
        local_point = point - self.transform.position
        
        # Extract axes from orientation matrix
        width_dir = Matrix([
            self.transform.orientation.matrix[0, 0],
            self.transform.orientation.matrix[1, 0],
            self.transform.orientation.matrix[2, 0]
        ])
        height_dir = Matrix([
            self.transform.orientation.matrix[0, 1],
            self.transform.orientation.matrix[1, 1],
            self.transform.orientation.matrix[2, 1]
        ])
        length_dir = Matrix([
            self.transform.orientation.matrix[0, 2],
            self.transform.orientation.matrix[1, 2],
            self.transform.orientation.matrix[2, 2]
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
        local_point = point - self.transform.position
        
        # Extract axes from orientation matrix
        width_dir = Matrix([
            self.transform.orientation.matrix[0, 0],
            self.transform.orientation.matrix[1, 0],
            self.transform.orientation.matrix[2, 0]
        ])
        height_dir = Matrix([
            self.transform.orientation.matrix[0, 1],
            self.transform.orientation.matrix[1, 1],
            self.transform.orientation.matrix[2, 1]
        ])
        length_dir = Matrix([
            self.transform.orientation.matrix[0, 2],
            self.transform.orientation.matrix[1, 2],
            self.transform.orientation.matrix[2, 2]
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
    # TODO consider just making this a Transform object, even though we don't care about one of the DOFs
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
    
    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the difference.
        
        A point is in the difference if it's in the base and NOT strictly inside any subtract object.
        Special case: if a point is on the boundary of both base and subtract, it's excluded.
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is in base but not in any subtract objects, False otherwise
        """
        # Point must be in base
        if not self.base.contains_point(point):
            return False
        
        # Check if on base boundary
        on_base_boundary = self.base.is_point_on_boundary(point)
        
        # Point must not be strictly inside any subtract object
        # Also, if point is on boundary of both base and subtract, exclude it
        for sub in self.subtract:
            if sub.contains_point(point):
                if not sub.is_point_on_boundary(point):
                    # Point is strictly inside a subtract object
                    return False
                elif on_base_boundary:
                    # Point is on boundary of both base and subtract - exclude it
                    return False
        
        return True

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
    An extruded Convex Polygon shape, optionally infinite in one or both ends.
    
    The extrusion is defined by:
    - A list of ordered (x,y) points in the polygon (must be convex!)
    - A transform (position and orientation in global coordinates)
    - Start and end distances along the local Z-axis from the position
    
    The polygon is in the local XY plane at the position, and the extrusion extends
    out in -z by start_distance and +z by end_distance.
    
    Use None for start_distance or end_distance to make the extrusion infinite in that direction.
    
    Args:
        points: List of ordered (x,y) points in the polygon (last connects to first, must be convex)
        transform: Transform (position and orientation) in global coordinates (default: identity)
        start_distance: Distance from position along Z-axis to start of extrusion (None = -infinite)
        end_distance: Distance from position along Z-axis to end of extrusion (None = infinite)
    """
    points: List[V2] 
    transform: Transform = field(default_factory=Transform.identity)
    start_distance: Optional[Numeric] = None  # starting distance in the direction of the -Z axis. None means infinite in negative direction
    end_distance: Optional[Numeric] = None    # ending distance in the direction of the +Z axis. None means infinite in positive direction

    def get_bottom_position(self) -> V3:
        """
        Get the position of the bottom of the extrusion (at start_distance).
        Only valid for extrusions with finite start_distance.
        
        Returns:
            The 3D position at the bottom of the extrusion
            
        Raises:
            ValueError: If start_distance is None (infinite extrusion)
        """
        if self.start_distance is None:
            raise ValueError("Cannot get bottom position of infinite extrusion (start_distance is None)")
        return self.transform.position - self.transform.orientation.matrix * Matrix([0, 0, self.start_distance])
    
    def get_top_position(self) -> V3:
        """
        Get the position of the top of the extrusion (at end_distance).
        Only valid for extrusions with finite end_distance.
        
        Returns:
            The 3D position at the top of the extrusion
            
        Raises:
            ValueError: If end_distance is None (infinite extrusion)
        """
        if self.end_distance is None:
            raise ValueError("Cannot get top position of infinite extrusion (end_distance is None)")
        return self.transform.position + self.transform.orientation.matrix * Matrix([0, 0, self.end_distance])

    def __repr__(self) -> str:
        return (f"ConvexPolygonExtrusion({len(self.points)} points, "
                f"transform={self.transform}, start={self.start_distance}, end={self.end_distance})")
    
    def is_valid(self) -> bool:
        """
        Check if the ConvexPolygonExtrusion is valid
        
        Checks:
        1. At least 3 points
        2. Valid distance configuration (if both finite, end > start)
        3. Polygon is convex (all turns go the same direction)
        
        Returns:
            True if valid, False otherwise
        """
        if len(self.points) < 3:
            return False
        
        # Check distance configuration
        if self.start_distance is not None and self.end_distance is not None:
            if self.end_distance <= self.start_distance:
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

    def contains_point(self, point: V3) -> bool:
        """
        Check if a point is contained within the extruded polygon.
        
        A point is inside if:
        1. Its Z coordinate (in local space) is between start_distance and end_distance
        2. Its XY coordinates (in local space) are inside the convex polygon
        
        Args:
            point: Point to test (3x1 Matrix)
            
        Returns:
            True if the point is inside or on the boundary, False otherwise
        """
        # Transform point to local coordinates
        local_point = point - self.transform.position
        local_coords = self.transform.orientation.invert().matrix * local_point
        
        x_coord = local_coords[0]
        y_coord = local_coords[1]
        z_coord = local_coords[2]
        
        # Check Z bounds
        if self.start_distance is not None and z_coord < self.start_distance:
            return False
        if self.end_distance is not None and z_coord > self.end_distance:
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
        1. On the top or bottom face (z = start_distance or z = end_distance, if finite)
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
        local_point = point - self.transform.position
        local_coords = self.transform.orientation.invert().matrix * local_point
        
        x_coord = local_coords[0]
        y_coord = local_coords[1]
        z_coord = local_coords[2]
        
        # Check if on top or bottom face (if finite)
        if self.start_distance is not None and z_coord == self.start_distance:
            return True
        if self.end_distance is not None and z_coord == self.end_distance:
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