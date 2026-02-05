"""
Tests for cutcsg.py module.

This module contains tests for the CSG primitives and operations.
"""

import pytest
from sympy import Matrix, Rational, simplify, sqrt, cos, sin, pi
from code_goes_here.rule import Orientation, Transform, create_v3
from code_goes_here.cutcsg import (
    HalfSpace, RectangularPrism, Cylinder, SolidUnion, Difference, ConvexPolygonExtrusion
)
from .testing_shavings import assert_is_valid_rotation_matrix
import random


# ============================================================================
# Helper Functions for Random Shape Generation and Boundary Point Testing
# ============================================================================

def generate_random_prism():
    """Generate a random prism with random size, orientation, position, and distances."""
    size = Matrix([Rational(random.randint(2, 10)), Rational(random.randint(2, 10))])
    orientation = Orientation()  # Identity orientation for simplicity
    position = Matrix([Rational(random.randint(-50, 50)), 
                      Rational(random.randint(-50, 50)), 
                      Rational(random.randint(-50, 50))])
    start_dist = Rational(random.randint(0, 10))
    end_dist = Rational(random.randint(15, 30))
    
    transform = Transform(position=position, orientation=orientation)
    return RectangularPrism(size=size, transform=transform,
                start_distance=start_dist, end_distance=end_dist)


def generate_random_cylinder():
    """Generate a random cylinder with random axis, radius, position, and distances."""
    # Use simple axis directions for predictability
    axes = [Matrix([1, 0, 0]), Matrix([0, 1, 0]), Matrix([0, 0, 1])]
    axis = random.choice(axes)
    radius = Rational(random.randint(2, 8))
    position = Matrix([Rational(random.randint(-50, 50)), 
                      Rational(random.randint(-50, 50)), 
                      Rational(random.randint(-50, 50))])
    start_dist = Rational(random.randint(0, 10))
    end_dist = Rational(random.randint(15, 30))
    
    return Cylinder(axis_direction=axis, radius=radius, position=position,
                   start_distance=start_dist, end_distance=end_dist)


def generate_random_halfspace():
    """Generate a random half-plane with random normal and offset."""
    # Use simple normalized normals for predictability
    normals = [Matrix([1, 0, 0]), Matrix([0, 1, 0]), Matrix([0, 0, 1]),
               Matrix([1, 1, 0]) / sqrt(2), Matrix([1, 0, 1]) / sqrt(2)]
    normal = random.choice(normals)
    offset = Rational(random.randint(-20, 20))
    
    return HalfSpace(normal=normal, offset=offset)


def generate_random_convex_polygon_extrusion():
    """Generate a random extruded convex polygon with 3-6 vertices."""
    num_vertices = random.randint(3, 6)
    
    # Generate a regular polygon for simplicity and guaranteed convexity
    radius = Rational(random.randint(3, 8))
    vertices = []
    for i in range(num_vertices):
        angle = 2 * pi * i / num_vertices
        x = radius * cos(angle)
        y = radius * sin(angle)
        vertices.append(Matrix([x, y]))
    
    start_distance = Rational(random.randint(0, 5))
    end_distance = start_distance + Rational(random.randint(10, 25))
    orientation = Orientation()  # Identity for simplicity
    position = Matrix([Rational(random.randint(-30, 30)), 
                      Rational(random.randint(-30, 30)), 
                      Rational(random.randint(-30, 30))])
    
    transform = Transform(position=position, orientation=orientation)
    return ConvexPolygonExtrusion(points=vertices, start_distance=start_distance,
                                  end_distance=end_distance,
                                  transform=transform)


def generate_prism_boundary_points(prism):
    """Generate points on the boundary of a prism: corners, edge midpoints, face centers."""
    points = []
    hw = prism.size[0] / 2  # half width
    hh = prism.size[1] / 2  # half height
    
    # Extract orientation axes
    width_dir = Matrix([prism.transform.orientation.matrix[0, 0],
                       prism.transform.orientation.matrix[1, 0],
                       prism.transform.orientation.matrix[2, 0]])
    height_dir = Matrix([prism.transform.orientation.matrix[0, 1],
                        prism.transform.orientation.matrix[1, 1],
                        prism.transform.orientation.matrix[2, 1]])
    length_dir = Matrix([prism.transform.orientation.matrix[0, 2],
                        prism.transform.orientation.matrix[1, 2],
                        prism.transform.orientation.matrix[2, 2]])
    
    # 8 corners (if finite)
    if prism.start_distance is not None and prism.end_distance is not None:
        for z in [prism.start_distance, prism.end_distance]:
            for x_sign in [-1, 1]:
                for y_sign in [-1, 1]:
                    point = (prism.transform.position + 
                            width_dir * (x_sign * hw) + 
                            height_dir * (y_sign * hh) + 
                            length_dir * z)
                    points.append(point)
    
    # 6 face centers (if finite)
    if prism.start_distance is not None and prism.end_distance is not None:
        z_mid = (prism.start_distance + prism.end_distance) / 2
        # Top and bottom faces
        points.append(prism.transform.position + length_dir * prism.start_distance)
        points.append(prism.transform.position + length_dir * prism.end_distance)
        # Side faces
        points.append(prism.transform.position + width_dir * hw + length_dir * z_mid)
        points.append(prism.transform.position + width_dir * (-hw) + length_dir * z_mid)
        points.append(prism.transform.position + height_dir * hh + length_dir * z_mid)
        points.append(prism.transform.position + height_dir * (-hh) + length_dir * z_mid)
    
    return points


def generate_prism_non_boundary_points(prism):
    """Generate points NOT on the boundary of a prism: center and far-away point."""
    points = []
    
    # Center point (if finite)
    if prism.start_distance is not None and prism.end_distance is not None:
        length_dir = Matrix([prism.transform.orientation.matrix[0, 2],
                            prism.transform.orientation.matrix[1, 2],
                            prism.transform.orientation.matrix[2, 2]])
        z_mid = (prism.start_distance + prism.end_distance) / 2
        points.append(prism.transform.position + length_dir * z_mid)
    
    # Far-away point
    points.append(prism.transform.position + Matrix([Rational(1000), Rational(1000), Rational(1000)]))
    
    return points


def generate_cylinder_boundary_points(cylinder):
    """Generate points on cylinder boundary: caps, surface, and round edges."""
    points = []
    
    # Normalize axis
    axis = cylinder.axis_direction / cylinder.axis_direction.norm()
    
    # Find perpendicular vectors for constructing points on circles
    if abs(axis[0]) < Rational(1, 2):
        perp1 = Matrix([1, 0, 0])
    else:
        perp1 = Matrix([0, 1, 0])
    
    perp1 = perp1 - axis * (perp1.T * axis)[0, 0]
    perp1 = perp1 / perp1.norm()
    perp2 = axis.cross(perp1)
    perp2 = perp2 / perp2.norm()
    
    # Cap centers (if finite)
    if cylinder.start_distance is not None:
        points.append(cylinder.position + axis * cylinder.start_distance)
    if cylinder.end_distance is not None:
        points.append(cylinder.position + axis * cylinder.end_distance)
    
    # Points on cap circumferences (round edges) - 8 points per cap
    for angle_frac in [0, Rational(1, 4), Rational(1, 2), Rational(3, 4)]:
        angle = 2 * pi * angle_frac
        radial = cylinder.radius * (perp1 * cos(angle) + perp2 * sin(angle))
        
        if cylinder.start_distance is not None:
            points.append(cylinder.position + axis * cylinder.start_distance + radial)
        if cylinder.end_distance is not None:
            points.append(cylinder.position + axis * cylinder.end_distance + radial)
    
    # Points on cylindrical surface (if finite)
    if cylinder.start_distance is not None and cylinder.end_distance is not None:
        z_mid = (cylinder.start_distance + cylinder.end_distance) / 2
        for angle_frac in [0, Rational(1, 4), Rational(1, 2), Rational(3, 4)]:
            angle = 2 * pi * angle_frac
            radial = cylinder.radius * (perp1 * cos(angle) + perp2 * sin(angle))
            points.append(cylinder.position + axis * z_mid + radial)
    
    return points


def generate_cylinder_non_boundary_points(cylinder):
    """Generate points NOT on cylinder boundary: center and far-away point."""
    points = []
    
    # Center point (if finite)
    if cylinder.start_distance is not None and cylinder.end_distance is not None:
        axis = cylinder.axis_direction / cylinder.axis_direction.norm()
        z_mid = (cylinder.start_distance + cylinder.end_distance) / 2
        points.append(cylinder.position + axis * z_mid)
    
    # Far-away point
    points.append(cylinder.position + Matrix([Rational(1000), Rational(1000), Rational(1000)]))
    
    return points


def generate_halfspace_boundary_points(halfspace):
    """Generate points on the half-plane boundary."""
    points = []
    
    # Plane origin
    points.append(halfspace.normal * halfspace.offset)
    
    # Find two perpendicular vectors in the plane
    normal = halfspace.normal / halfspace.normal.norm()
    if abs(normal[0]) < Rational(1, 2):
        perp1 = Matrix([1, 0, 0])
    else:
        perp1 = Matrix([0, 1, 0])
    
    perp1 = perp1 - normal * (perp1.T * normal)[0, 0]
    perp1 = perp1 / perp1.norm()
    perp2 = normal.cross(perp1)
    perp2 = perp2 / perp2.norm()
    
    # Random points on the plane
    plane_origin = halfspace.normal * halfspace.offset
    for i in range(5):
        offset_x = Rational(random.randint(-20, 20))
        offset_y = Rational(random.randint(-20, 20))
        points.append(plane_origin + perp1 * offset_x + perp2 * offset_y)
    
    return points


def generate_halfspace_non_boundary_points(halfspace):
    """Generate points NOT on half-plane boundary: points on both sides of plane."""
    points = []
    normal_normalized = halfspace.normal / halfspace.normal.norm()
    plane_origin = halfspace.normal * halfspace.offset
    
    # Point on positive side (in direction of normal, inside half-plane)
    points.append(plane_origin + normal_normalized * Rational(10))
    
    # Point on negative side (opposite to normal, outside half-plane)
    points.append(plane_origin - normal_normalized * Rational(10))
    
    return points


def generate_convex_polygon_boundary_points(extrusion):
    """Generate points on convex polygon extrusion boundary: vertices, edges, faces."""
    points = []
    
    # Only generate boundary points for finite extrusions
    if extrusion.start_distance is None or extrusion.end_distance is None:
        return points
    
    # All vertices at z=start_distance and z=end_distance
    for vertex_2d in extrusion.points:
        # Bottom (z=start_distance)
        point_local = Matrix([vertex_2d[0], vertex_2d[1], extrusion.start_distance])
        point_global = extrusion.transform.position + extrusion.transform.orientation.matrix * point_local
        points.append(point_global)
        
        # Top (z=end_distance)
        point_local = Matrix([vertex_2d[0], vertex_2d[1], extrusion.end_distance])
        point_global = extrusion.transform.position + extrusion.transform.orientation.matrix * point_local
        points.append(point_global)
    
    # Face centers on top and bottom
    if len(extrusion.points) > 0:
        # Calculate centroid
        centroid_x = sum(p[0] for p in extrusion.points) / len(extrusion.points)
        centroid_y = sum(p[1] for p in extrusion.points) / len(extrusion.points)
        
        # Bottom face center
        point_local = Matrix([centroid_x, centroid_y, extrusion.start_distance])
        point_global = extrusion.transform.position + extrusion.transform.orientation.matrix * point_local
        points.append(point_global)
        
        # Top face center
        point_local = Matrix([centroid_x, centroid_y, extrusion.end_distance])
        point_global = extrusion.transform.position + extrusion.transform.orientation.matrix * point_local
        points.append(point_global)
    
    # Edge midpoints (on vertical edges)
    for vertex_2d in extrusion.points:
        z_mid = (extrusion.start_distance + extrusion.end_distance) / 2
        point_local = Matrix([vertex_2d[0], vertex_2d[1], z_mid])
        point_global = extrusion.transform.position + extrusion.transform.orientation.matrix * point_local
        points.append(point_global)
    
    return points


def generate_convex_polygon_non_boundary_points(extrusion):
    """Generate points NOT on convex polygon boundary: interior and far-away points."""
    points = []
    
    # Only generate interior points for finite extrusions
    if extrusion.start_distance is not None and extrusion.end_distance is not None:
        # Interior point at mid-height
        if len(extrusion.points) > 0:
            centroid_x = sum(p[0] for p in extrusion.points) / len(extrusion.points)
            centroid_y = sum(p[1] for p in extrusion.points) / len(extrusion.points)
            z_mid = (extrusion.start_distance + extrusion.end_distance) / 2
            
            point_local = Matrix([centroid_x, centroid_y, z_mid])
            point_global = extrusion.transform.position + extrusion.transform.orientation.matrix * point_local
            points.append(point_global)
    
    # Far-away point
    points.append(extrusion.transform.position + Matrix([Rational(1000), Rational(1000), Rational(1000)]))
    
    return points


class TestConstructors:
    """Test the RectangularPrism and Cylinder constructors."""
    
    def test_prism_constructor_finite(self):
        """Test creating a finite prism."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        
        assert prism.size == size
        assert prism.transform.orientation == orientation
        assert prism.start_distance == 0
        assert prism.end_distance == 10
    
    def test_prism_constructor_semi_infinite(self):
        """Test creating a semi-infinite prism."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), end_distance=10)
        
        assert prism.start_distance is None
        assert prism.end_distance == 10
    
    def test_prism_constructor_infinite(self):
        """Test creating an infinite prism."""
        size = Matrix([4, 6])
        prism = RectangularPrism(size=size, transform=Transform.identity())
        
        assert prism.start_distance is None
        assert prism.end_distance is None
    
    def test_cylinder_constructor_finite(self):
        """Test creating a finite cylinder."""
        axis = Matrix([1, 0, 0])
        radius = Rational(5)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=-5, end_distance=5)
        
        assert cylinder.axis_direction == axis
        assert cylinder.radius == radius
        assert cylinder.start_distance == -5
        assert cylinder.end_distance == 5
    
    def test_cylinder_constructor_infinite(self):
        """Test creating an infinite cylinder."""
        axis = Matrix([1, 0, 0])
        radius = Rational(5)
        cylinder = Cylinder(axis_direction=axis, radius=radius)
        
        assert cylinder.start_distance is None
        assert cylinder.end_distance is None


class TestPrismPositionMethods:
    """Test RectangularPrism get_bottom_position and get_top_position methods."""
    
    def test_get_bottom_position_finite_prism(self):
        """Test get_bottom_position on a finite prism."""
        # Create a prism with identity orientation
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        position = Matrix([10, 20, 30])
        start_distance = Rational(5)
        end_distance = Rational(15)
        transform = Transform(position=position, orientation=orientation)
        prism = RectangularPrism(size=size, transform=transform, 
                     start_distance=start_distance, end_distance=end_distance)
        
        # Bottom position should be position - (0, 0, start_distance) in local frame
        # With identity orientation, this is position - Matrix([0, 0, start_distance])
        bottom = prism.get_bottom_position()
        expected_bottom = Matrix([10, 20, 25])  # 30 - 5 = 25
        assert bottom.equals(expected_bottom), f"Expected {expected_bottom.T}, got {bottom.T}"
    
    def test_get_top_position_finite_prism(self):
        """Test get_top_position on a finite prism."""
        # Create a prism with identity orientation
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        position = Matrix([10, 20, 30])
        start_distance = Rational(5)
        end_distance = Rational(15)
        transform = Transform(position=position, orientation=orientation)
        prism = RectangularPrism(size=size, transform=transform, 
                     start_distance=start_distance, end_distance=end_distance)
        
        # Top position should be position + (0, 0, end_distance) in local frame
        # With identity orientation, this is position + Matrix([0, 0, end_distance])
        top = prism.get_top_position()
        expected_top = Matrix([10, 20, 45])  # 30 + 15 = 45
        assert top.equals(expected_top), f"Expected {expected_top.T}, got {top.T}"
    
    def test_get_bottom_position_rotated_prism(self):
        """Test get_bottom_position on a rotated prism."""
        # Create a prism with a specific rotation
        # Rotation matrix: local X -> global Z, local Y -> global Y, local Z -> global X
        # This is: [[0, 0, 1], [0, 1, 0], [1, 0, 0]]
        size = Matrix([4, 6])
        rotation = Matrix([
            [0, 0, 1],   # X column: local X maps to global Z
            [0, 1, 0],   # Y column: local Y maps to global Y  
            [1, 0, 0]    # Z column: local Z maps to global X
        ])
        orientation = Orientation(rotation)
        position = Matrix([10, 20, 30])
        start_distance = Rational(5)
        end_distance = Rational(15)
        transform = Transform(position=position, orientation=orientation)
        prism = RectangularPrism(size=size, transform=transform,
                     start_distance=start_distance, end_distance=end_distance)
        
        # With this rotation: local Z becomes global X
        # So bottom should be position - rotation * [0, 0, 5]
        # rotation * [0, 0, 5] = 5 * (third column) = 5 * [1, 0, 0] = [5, 0, 0]
        # position - [5, 0, 0] = [10, 20, 30] - [5, 0, 0] = [5, 20, 30]
        bottom = prism.get_bottom_position()
        expected_bottom = Matrix([5, 20, 30])
        assert bottom.equals(expected_bottom), f"Expected {expected_bottom.T}, got {bottom.T}"
    
    def test_get_bottom_position_infinite_prism_raises_error(self):
        """Test that get_bottom_position raises error for infinite prism."""
        size = Matrix([4, 6])
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=None, end_distance=10)
        
        with pytest.raises(ValueError, match="infinite prism"):
            prism.get_bottom_position()
    
    def test_get_top_position_infinite_prism_raises_error(self):
        """Test that get_top_position raises error for infinite prism."""
        size = Matrix([4, 6])
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=None)
        
        with pytest.raises(ValueError, match="infinite prism"):
            prism.get_top_position()


class TestHalfspaceContainsPoint:
    """Test HalfSpace contains_point and is_point_on_boundary methods."""
    
    def test_halfspace_contains_point_on_positive_side(self):
        """Test that a point on the positive side is contained."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal, offset)
        
        # Point at z=10 (above the plane at z=5)
        point = Matrix([0, 0, 10])
        assert halfspace.contains_point(point) == True
    
    def test_halfspace_contains_point_on_boundary(self):
        """Test that a point on the boundary is contained."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal, offset)
        
        # Point at z=5 (on the plane)
        point = Matrix([1, 2, 5])
        assert halfspace.contains_point(point) == True
    
    def test_halfspace_contains_point_on_negative_side(self):
        """Test that a point on the negative side is not contained."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal, offset)
        
        # Point at z=0 (below the plane at z=5)
        point = Matrix([0, 0, 0])
        assert halfspace.contains_point(point) == False
    
    def test_halfspace_is_point_on_boundary(self):
        """Test boundary detection."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal, offset)
        
        # Point on boundary
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 5])) == True
        assert halfspace.is_point_on_boundary(Matrix([1, 1, 5])) == True
        
        # Point not on boundary
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 6])) == False
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 4])) == False
    
    def test_halfspace_diagonal_normal(self):
        """Test half-plane with diagonal normal."""
        normal = Matrix([1, 1, 1])
        offset = Rational(0)
        halfspace = HalfSpace(normal, offset)
        
        # Point where x+y+z > 0
        assert halfspace.contains_point(Matrix([1, 0, 0])) == True
        assert halfspace.contains_point(Matrix([1, 1, 1])) == True
        
        # Point where x+y+z = 0
        assert halfspace.contains_point(Matrix([0, 0, 0])) == True
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 0])) == True
        
        # Point where x+y+z < 0
        assert halfspace.contains_point(Matrix([-1, 0, 0])) == False


class TestPrismContainsPoint:
    """Test RectangularPrism contains_point and is_point_on_boundary methods."""
    
    def test_prism_contains_point_inside(self):
        """Test that a point inside the prism is contained."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        
        # Point inside: within ±2 in x, ±3 in y, 0-10 in z
        point = Matrix([0, 0, 5])
        assert prism.contains_point(point) == True
    
    def test_prism_contains_point_on_face(self):
        """Test that a point on a face is contained."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        
        # Point on face (x = 2, which is half-width)
        point = Matrix([2, 0, 5])
        assert prism.contains_point(point) == True
    
    def test_prism_contains_point_outside(self):
        """Test that a point outside the prism is not contained."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        
        # Point outside in x direction
        point = Matrix([3, 0, 5])
        assert prism.contains_point(point) == False
        
        # Point outside in z direction
        point = Matrix([0, 0, 11])
        assert prism.contains_point(point) == False
    
    def test_prism_is_point_on_boundary_face(self):
        """Test boundary detection on prism faces."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        
        # On width face (x = ±2)
        assert prism.is_point_on_boundary(Matrix([2, 0, 5])) == True
        assert prism.is_point_on_boundary(Matrix([-2, 0, 5])) == True
        
        # On height face (y = ±3)
        assert prism.is_point_on_boundary(Matrix([0, 3, 5])) == True
        assert prism.is_point_on_boundary(Matrix([0, -3, 5])) == True
        
        # On end caps (z = 0 or 10)
        assert prism.is_point_on_boundary(Matrix([0, 0, 0])) == True
        assert prism.is_point_on_boundary(Matrix([0, 0, 10])) == True
    
    def test_prism_is_point_on_boundary_inside(self):
        """Test that interior points are not on boundary."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        
        # Interior point
        assert prism.is_point_on_boundary(Matrix([0, 0, 5])) == False
    
    def test_prism_semi_infinite_contains(self):
        """Test semi-infinite prism containment."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = RectangularPrism(size=size, transform=Transform.identity(), end_distance=10)  # Infinite in negative direction
        
        # Point at z = -100 should be contained
        assert prism.contains_point(Matrix([0, 0, -100])) == True
        
        # Point at z = 100 should not be contained
        assert prism.contains_point(Matrix([0, 0, 100])) == False


class TestCylinderContainsPoint:
    """Test Cylinder contains_point and is_point_on_boundary methods."""
    
    def test_cylinder_contains_point_inside(self):
        """Test that a point inside the cylinder is contained."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # Point inside: radial distance < 3, z in [0, 10]
        point = Matrix([1, 1, 5])
        assert cylinder.contains_point(point) == True
    
    def test_cylinder_contains_point_on_surface(self):
        """Test that a point on the cylindrical surface is contained."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # Point on surface: radial distance = 3
        point = Matrix([3, 0, 5])
        assert cylinder.contains_point(point) == True
    
    def test_cylinder_contains_point_outside_radially(self):
        """Test that a point outside radially is not contained."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # Point outside: radial distance > 3
        point = Matrix([4, 0, 5])
        assert cylinder.contains_point(point) == False
    
    def test_cylinder_contains_point_outside_axially(self):
        """Test that a point outside axially is not contained."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # Point outside in z direction
        point = Matrix([0, 0, 11])
        assert cylinder.contains_point(point) == False
    
    def test_cylinder_is_point_on_boundary_surface(self):
        """Test boundary detection on cylindrical surface."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # On cylindrical surface (radial distance = 3)
        assert cylinder.is_point_on_boundary(Matrix([3, 0, 5])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, 3, 5])) == True
    
    def test_cylinder_is_point_on_boundary_end_caps(self):
        """Test boundary detection on cylinder end caps."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # On end caps
        assert cylinder.is_point_on_boundary(Matrix([0, 0, 0])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, 0, 10])) == True
        assert cylinder.is_point_on_boundary(Matrix([1, 1, 0])) == True
    
    def test_cylinder_is_point_on_boundary_inside(self):
        """Test that interior points are not on boundary."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # Interior point
        assert cylinder.is_point_on_boundary(Matrix([0, 0, 5])) == False
        assert cylinder.is_point_on_boundary(Matrix([1, 0, 5])) == False
    
    def test_cylinder_semi_infinite_contains(self):
        """Test semi-infinite cylinder containment."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, end_distance=10)  # Infinite in negative direction
        
        # Point at z = -100 should be contained (if within radius)
        assert cylinder.contains_point(Matrix([1, 0, -100])) == True
        
        # Point at z = 100 should not be contained
        assert cylinder.contains_point(Matrix([1, 0, 100])) == False


class TestUnionContainsPoint:
    """Test SolidUnion contains_point and is_point_on_boundary methods."""
    
    def test_union_contains_point_in_first_child(self):
        """Test that a point in the first child is contained."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=5)
        prism2 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=10, end_distance=15)
        
        union = SolidUnion([prism1, prism2])
        
        # Point in first prism
        assert union.contains_point(Matrix([0, 0, 3])) == True
    
    def test_union_contains_point_in_second_child(self):
        """Test that a point in the second child is contained."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=5)
        prism2 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=10, end_distance=15)
        
        union = SolidUnion([prism1, prism2])
        
        # Point in second prism
        assert union.contains_point(Matrix([0, 0, 12])) == True
    
    def test_union_contains_point_outside_all(self):
        """Test that a point outside all children is not contained."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=5)
        prism2 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=10, end_distance=15)
        
        union = SolidUnion([prism1, prism2])
        
        # Point between the two prisms
        assert union.contains_point(Matrix([0, 0, 7])) == False
    
    def test_union_is_point_on_boundary(self):
        """Test boundary detection for union."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=5)
        prism2 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=10, end_distance=15)
        
        union = SolidUnion([prism1, prism2])
        
        # Point on boundary of first prism
        assert union.is_point_on_boundary(Matrix([1, 0, 3])) == True
        
        # Point on boundary of second prism
        assert union.is_point_on_boundary(Matrix([1, 0, 12])) == True
    
    def test_union_is_point_on_boundary_interior(self):
        """Test that interior points are not on boundary."""
        size = Matrix([4, 4])
        orientation = Orientation()
        
        prism1 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        prism2 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=5, end_distance=15)
        
        union = SolidUnion([prism1, prism2])
        
        # Point strictly inside first prism (not on boundary)
        assert union.is_point_on_boundary(Matrix([0, 0, 3])) == False
        
        # Point strictly inside second prism (not on boundary)
        assert union.is_point_on_boundary(Matrix([0, 0, 12])) == False
    
    def test_union_is_point_on_boundary_overlapping(self):
        """Test boundary detection when prisms overlap."""
        size = Matrix([4, 4])
        orientation = Orientation()
        
        # Two overlapping prisms
        prism1 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=10)
        prism2 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=5, end_distance=15)
        
        union = SolidUnion([prism1, prism2])
        
        # Point on outer boundary of union (on prism1 face, not inside prism2)
        assert union.is_point_on_boundary(Matrix([2, 0, 3])) == True
        
        # Point on outer boundary of union (on prism2 face, not inside prism1)
        assert union.is_point_on_boundary(Matrix([2, 0, 12])) == True
        
        # Point in overlap region is NOT on boundary (it's interior to the union)
        # At z=5, this is inside prism1 and on the start face of prism2
        # Since it's strictly inside prism1, it's not on the union boundary
        assert union.is_point_on_boundary(Matrix([0, 0, 5])) == False
    
    def test_union_is_point_on_boundary_outside(self):
        """Test that points outside all children are not on boundary."""
        size = Matrix([2, 2])
        orientation = Orientation()
        
        prism1 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=0, end_distance=5)
        prism2 = RectangularPrism(size=size, transform=Transform.identity(), start_distance=10, end_distance=15)
        
        union = SolidUnion([prism1, prism2])
        
        # Point between the two prisms (not on boundary)
        assert union.is_point_on_boundary(Matrix([0, 0, 7])) == False
        
        # Point far outside
        assert union.is_point_on_boundary(Matrix([10, 10, 10])) == False


num_random_samples = 10

class TestDifferenceContainsPoint:
    """Test Difference contains_point and is_point_on_boundary methods."""
    
    def test_difference_contains_point_in_base_not_subtracted(self):
        """Test that a point in base but not in subtract is contained."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point in base but outside subtract region
        assert diff.contains_point(Matrix([4, 4, 5])) == True
    
    def test_difference_contains_point_subtracted(self):
        """Test that a point in subtract region is not contained."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point in subtract region
        assert diff.contains_point(Matrix([0, 0, 5])) == False
    
    def test_difference_contains_point_outside_base(self):
        """Test that a point outside base is not contained."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point outside base
        assert diff.contains_point(Matrix([10, 10, 5])) == False
    
    def test_difference_is_point_on_boundary_base(self):
        """Test boundary detection on base boundary."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point on base boundary (not in subtract region)
        assert diff.is_point_on_boundary(Matrix([5, 4, 5])) == True
    
    def test_difference_is_point_on_boundary_subtract(self):
        """Test boundary detection on subtract boundary."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point on subtract boundary (creates new boundary in difference)
        # At x=1 (edge of subtract), y=0, z=5
        assert diff.is_point_on_boundary(Matrix([1, 0, 5])) == True
    
    def test_difference_is_point_on_boundary_interior(self):
        """Test that interior points are not on boundary."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point in base but not on boundary (not near subtract)
        assert diff.is_point_on_boundary(Matrix([4, 4, 5])) == False
    
    def test_difference_is_point_on_boundary_strictly_inside_subtract(self):
        """Test that points strictly inside subtract are not contained or on boundary."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([4, 4])
        orientation = Orientation()
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point strictly inside subtract (not on subtract boundary)
        point = Matrix([Rational(1, 2), Rational(1, 2), 5])
        assert diff.contains_point(point) == False
        assert diff.is_point_on_boundary(point) == False
    
    def test_difference_contains_point_on_subtract_boundary(self):
        """Test that points on subtract boundary are contained in the difference."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([4, 4])
        orientation = Orientation()
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        subtract = RectangularPrism(size=size_subtract, transform=Transform.identity(), start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point on subtract boundary should be contained (forms the cut surface)
        point = Matrix([2, 0, 5])  # On width face of subtract
        assert diff.contains_point(point) == True
        assert diff.is_point_on_boundary(point) == True
    
    def test_difference_with_halfspace_boundary(self):
        """Test boundary detection when subtracting with a half-plane."""
        size_base = Matrix([10, 10])
        orientation = Orientation()
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        # Half-plane at z=5, normal pointing in +z direction
        half_plane = HalfSpace(normal=Matrix([0, 0, 1]), offset=5)
        
        diff = Difference(base, [half_plane])
        
        # Point on half-plane boundary (z=5) should be on difference boundary
        assert diff.is_point_on_boundary(Matrix([0, 0, 5])) == True
        assert diff.is_point_on_boundary(Matrix([3, 3, 5])) == True
        
        # Point strictly below plane (inside difference) should not be on boundary
        assert diff.is_point_on_boundary(Matrix([0, 0, 3])) == False
        
        # Point strictly above plane (removed by difference) should not be contained
        assert diff.contains_point(Matrix([0, 0, 7])) == False
    
    def test_difference_multiple_subtracts(self):
        """Test boundary detection with multiple subtract objects."""
        size_base = Matrix([10, 10])
        orientation = Orientation()
        
        base = RectangularPrism(size=size_base, transform=Transform.identity(), start_distance=0, end_distance=10)
        # Two small prisms to subtract
        subtract1 = RectangularPrism(size=Matrix([2, 2]), transform=Transform(position=Matrix([2, 2, 0]), orientation=Orientation()), 
                         start_distance=2, end_distance=8)
        subtract2 = RectangularPrism(size=Matrix([2, 2]), transform=Transform(position=Matrix([-2, -2, 0]), orientation=Orientation()),
                         start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract1, subtract2])
        
        # Points on subtract1 boundary
        assert diff.is_point_on_boundary(Matrix([3, 2, 5])) == True
        
        # Points on subtract2 boundary
        assert diff.is_point_on_boundary(Matrix([-1, -2, 5])) == True
        
        # Point on base boundary (not near subtracts)
        assert diff.is_point_on_boundary(Matrix([5, 0, 0])) == True
    
    def test_difference_nested_differences(self):
        """Test boundary detection with nested difference operations."""
        orientation = Orientation()
        
        # Create base prism
        base = RectangularPrism(size=Matrix([10, 10]), transform=Transform.identity(), 
                    start_distance=0, end_distance=10)
        
        # Create a subtract prism at the center
        subtract_inner = RectangularPrism(size=Matrix([2, 2]), transform=Transform.identity(),
                              start_distance=3, end_distance=7)
        
        # Create a nested difference (prism with hole in center)
        inner_diff = Difference(base, [subtract_inner])
        
        # Now subtract another prism from a different location
        # Place it off to the side so it doesn't overlap with subtract_inner
        subtract_outer = RectangularPrism(size=Matrix([2, 2]), transform=Transform(position=Matrix([4, 0, 0]), orientation=orientation),
                              start_distance=1, end_distance=9)
        
        outer_diff = Difference(inner_diff, [subtract_outer])
        
        # Point on inner subtract boundary (the central hole)
        # This should still be on boundary in outer_diff
        assert outer_diff.is_point_on_boundary(Matrix([1, 0, 5])) == True
        
        # Point on outer subtract boundary (the side hole)
        assert outer_diff.is_point_on_boundary(Matrix([5, 0, 5])) == True
        
        # Point in the remaining material (not on any boundary)
        assert outer_diff.is_point_on_boundary(Matrix([Rational(-7, 2), 0, 5])) == False
    
    def test_difference_shape_minus_itself_should_be_empty(self):
        """Test that subtracting a shape from itself results in an empty shape.
        
        This test demonstrates a bug: when you subtract a shape from itself,
        the result should contain NO points (not even boundary points).
        Currently, this fails for points on the boundary.
        """
        orientation = Orientation()
        
        # Create a prism
        prism = RectangularPrism(size=Matrix([10, 10]), transform=Transform(position=create_v3(0, 0, 0), orientation=orientation),
                     start_distance=Rational(0), end_distance=Rational(10))
        
        # Subtract the prism from itself
        empty_diff = Difference(prism, [prism])
        
        # Test interior points - should NOT be contained
        interior_points = [
            Matrix([0, 0, 5]),           # Center
            Matrix([1, 1, 5]),           # Off-center interior
            Matrix([Rational(-2), 2, 3]) # Another interior point
        ]
        
        for point in interior_points:
            assert empty_diff.contains_point(point) == False, \
                f"Interior point {point.T} should NOT be in empty difference"
        
        # Test boundary points - should NOT be contained (THIS WILL FAIL)
        boundary_points = [
            Matrix([5, 0, 5]),     # On width face
            Matrix([0, 5, 5]),     # On height face
            Matrix([0, 0, 0]),     # On bottom face
            Matrix([0, 0, 10]),    # On top face
            Matrix([5, 5, 0]),     # Corner on bottom
            Matrix([5, 5, 10]),    # Corner on top
        ]
        
        for point in boundary_points:
            # This assertion is EXPECTED TO FAIL - that's the bug we're testing for
            assert empty_diff.contains_point(point) == False, \
                f"Boundary point {point.T} should NOT be in empty difference"
        
        # Test exterior points - should NOT be contained
        exterior_points = [
            Matrix([20, 0, 5]),      # Outside in x
            Matrix([0, 20, 5]),      # Outside in y
            Matrix([0, 0, 20]),      # Outside in z
            Matrix([100, 100, 100])  # Far away
        ]
        
        for point in exterior_points:
            assert empty_diff.contains_point(point) == False, \
                f"Exterior point {point.T} should NOT be in empty difference"


class TestConvexPolygonExtrusion:
    """Test ConvexPolygonExtrusion class."""
    
    def test_constructor_square(self):
        """Test creating a square extrusion."""
        # Square with corners at (±1, ±1)
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()  # Identity orientation
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance, 
                                          end_distance=end_distance, transform=Transform.identity())
        
        assert extrusion.points == points
        assert extrusion.start_distance == start_distance
        assert extrusion.end_distance == end_distance
        assert extrusion.transform.orientation == orientation
    
    def test_is_valid_enough_points(self):
        """Test that is_valid requires at least 3 points."""
        # Triangle (valid)
        points_valid = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([0, 1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(5)
        orientation = Orientation()
        
        extrusion_valid = ConvexPolygonExtrusion(points=points_valid, start_distance=start_distance,
                                                 end_distance=end_distance, transform=Transform.identity())
        assert extrusion_valid.is_valid() == True
        
        # Only 2 points (invalid)
        points_invalid = [
            Matrix([0, 0]),
            Matrix([1, 0])
        ]
        extrusion_invalid = ConvexPolygonExtrusion(points=points_invalid, start_distance=start_distance,
                                                   end_distance=end_distance, transform=Transform.identity())
        assert extrusion_invalid.is_valid() == False
    
    def test_is_valid_distance_configuration(self):
        """Test that is_valid requires valid distance configuration."""
        points = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([0, 1])
        ]
        orientation = Orientation()
        
        # Valid: end > start (valid)
        extrusion_valid = ConvexPolygonExtrusion(points=points, start_distance=Rational(0),
                                                 end_distance=Rational(5), transform=Transform.identity())
        assert extrusion_valid.is_valid() == True
        
        # Invalid: end = start (no volume)
        extrusion_zero = ConvexPolygonExtrusion(points=points, start_distance=Rational(5),
                                               end_distance=Rational(5), transform=Transform.identity())
        assert extrusion_zero.is_valid() == False
        
        # Invalid: end < start
        extrusion_negative = ConvexPolygonExtrusion(points=points, start_distance=Rational(5),
                                                    end_distance=Rational(0), transform=Transform.identity())
        assert extrusion_negative.is_valid() == False
        
        # Valid: infinite in both directions
        extrusion_infinite = ConvexPolygonExtrusion(points=points, start_distance=None,
                                                    end_distance=None, transform=Transform.identity())
        assert extrusion_infinite.is_valid() == True
    
    def test_is_valid_convex_polygon(self):
        """Test that is_valid accepts convex polygons."""
        orientation = Orientation()
        start_distance = Rational(0)
        end_distance = Rational(5)
        
        # Convex square (counter-clockwise)
        points_ccw = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        extrusion_ccw = ConvexPolygonExtrusion(points=points_ccw, start_distance=start_distance,
                                               end_distance=end_distance, transform=Transform.identity())
        assert extrusion_ccw.is_valid() == True
        
        # Convex square (clockwise)
        points_cw = [
            Matrix([1, 1]),
            Matrix([1, -1]),
            Matrix([-1, -1]),
            Matrix([-1, 1])
        ]
        extrusion_cw = ConvexPolygonExtrusion(points=points_cw, start_distance=start_distance,
                                              end_distance=end_distance, transform=Transform.identity())
        assert extrusion_cw.is_valid() == True
        
        # Convex hexagon
        points_hex = [
            Matrix([2, 0]),
            Matrix([1, sqrt(3)]),
            Matrix([-1, sqrt(3)]),
            Matrix([-2, 0]),
            Matrix([-1, -sqrt(3)]),
            Matrix([1, -sqrt(3)])
        ]
        extrusion_hex = ConvexPolygonExtrusion(points=points_hex, start_distance=start_distance,
                                               end_distance=end_distance, transform=Transform.identity())
        assert extrusion_hex.is_valid() == True
    
    def test_is_valid_non_convex_polygon(self):
        """Test that is_valid rejects non-convex (concave) polygons."""
        orientation = Orientation()
        
        # Non-convex polygon (indented square - concave)
        # Makes an arrow shape pointing right
        points_concave = [
            Matrix([0, 2]),
            Matrix([2, 0]),
            Matrix([0, -2]),
            Matrix([1, 0])  # This point makes it concave
        ]
        extrusion_concave = ConvexPolygonExtrusion(points=points_concave, start_distance=Rational(0),
                                                   end_distance=Rational(5), transform=Transform.identity())
        assert extrusion_concave.is_valid() == False
    
    def test_is_valid_collinear_points(self):
        """Test that is_valid rejects collinear points."""
        orientation = Orientation()
        
        # All points on a line
        points_collinear = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([2, 0])
        ]
        extrusion_collinear = ConvexPolygonExtrusion(points=points_collinear, start_distance=Rational(0),
                                                     end_distance=Rational(5), transform=Transform.identity())
        assert extrusion_collinear.is_valid() == False
    
    def test_contains_point_inside_square(self):
        """Test that a point inside a square extrusion is contained."""
        # Unit square centered at origin
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Point inside
        assert extrusion.contains_point(Matrix([0, 0, 5])) == True
    
    def test_contains_point_on_face_square(self):
        """Test that a point on a face is contained."""
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Point on top face (z = end_distance)
        assert extrusion.contains_point(Matrix([0, 0, 10])) == True
        
        # Point on bottom face (z = start_distance)
        assert extrusion.contains_point(Matrix([0, 0, 0])) == True
    
    def test_contains_point_outside_square(self):
        """Test that a point outside is not contained."""
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Outside in XY plane
        assert extrusion.contains_point(Matrix([2, 0, 5])) == False
        
        # Outside in Z direction
        assert extrusion.contains_point(Matrix([0, 0, 11])) == False
        assert extrusion.contains_point(Matrix([0, 0, -1])) == False
    
    def test_contains_point_triangle(self):
        """Test containment for a triangular extrusion."""
        # Right triangle with vertices at origin, (1,0), (0,1)
        points = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([0, 1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(5)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Point inside triangle
        assert extrusion.contains_point(Matrix([Rational(1, 4), Rational(1, 4), Rational(5, 2)])) == True
        
        # Point outside triangle but in XY bounding box
        assert extrusion.contains_point(Matrix([Rational(3, 4), Rational(3, 4), Rational(5, 2)])) == False
    
    def test_is_point_on_boundary_top_bottom(self):
        """Test boundary detection on top and bottom faces."""
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # On bottom face (z = start_distance)
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 0])) == True
        
        # On top face (z = end_distance)
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 10])) == True
    
    def test_is_point_on_boundary_side_face(self):
        """Test boundary detection on side faces."""
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # On edge at x=1 (right edge)
        assert extrusion.is_point_on_boundary(Matrix([1, 0, 5])) == True
        
        # On edge at y=-1 (bottom edge)
        assert extrusion.is_point_on_boundary(Matrix([0, -1, 5])) == True
    
    def test_is_point_on_boundary_inside(self):
        """Test that interior points are not on boundary."""
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Interior point
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 5])) == False
    
    def test_repr(self):
        """Test string representation."""
        points = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([0, 1])
        ]
        start_distance = Rational(0)
        end_distance = Rational(5)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        repr_str = repr(extrusion)
        assert "ConvexPolygonExtrusion" in repr_str
        assert "3 points" in repr_str
        assert "5" in repr_str


class TestBoundaryDetectionComprehensive:
    """Comprehensive tests for is_point_on_boundary across all CSG shapes."""
    
    # ========================================================================
    # RectangularPrism Boundary Tests
    # ========================================================================
    
    def test_prism_all_corners_on_boundary(self):
        """Test that all 8 corners of a finite prism are on the boundary."""
        size = Matrix([Rational(4), Rational(6)])
        orientation = Orientation()
        prism = RectangularPrism(size=size, transform=Transform(position=create_v3(0, 0, 0), orientation=orientation), start_distance=Rational(0), end_distance=Rational(10))
        
        # Generate all 8 corners
        hw, hh = Rational(2), Rational(3)
        corners = []
        for z in [Rational(0), Rational(10)]:
            for x in [-hw, hw]:
                for y in [-hh, hh]:
                    corners.append(Matrix([x, y, z]))
        
        # All corners should be on boundary
        for corner in corners:
            assert prism.is_point_on_boundary(corner) == True, \
                f"Corner {corner.T} should be on boundary"
    
    def test_prism_edge_points_on_boundary(self):
        """Test that points along prism edges are on the boundary."""
        size = Matrix([Rational(4), Rational(6)])
        orientation = Orientation()
        prism = RectangularPrism(size=size, transform=Transform(position=create_v3(0, 0, 0), orientation=orientation), start_distance=Rational(0), end_distance=Rational(10))
        
        hw, hh = Rational(2), Rational(3)
        
        # Test edge midpoints (12 edges)
        # 4 edges on bottom face
        assert prism.is_point_on_boundary(Matrix([0, hh, 0])) == True
        assert prism.is_point_on_boundary(Matrix([0, -hh, 0])) == True
        assert prism.is_point_on_boundary(Matrix([hw, 0, 0])) == True
        assert prism.is_point_on_boundary(Matrix([-hw, 0, 0])) == True
        
        # 4 edges on top face
        assert prism.is_point_on_boundary(Matrix([0, hh, 10])) == True
        assert prism.is_point_on_boundary(Matrix([0, -hh, 10])) == True
        assert prism.is_point_on_boundary(Matrix([hw, 0, 10])) == True
        assert prism.is_point_on_boundary(Matrix([-hw, 0, 10])) == True
        
        # 4 vertical edges
        assert prism.is_point_on_boundary(Matrix([hw, hh, 5])) == True
        assert prism.is_point_on_boundary(Matrix([hw, -hh, 5])) == True
        assert prism.is_point_on_boundary(Matrix([-hw, hh, 5])) == True
        assert prism.is_point_on_boundary(Matrix([-hw, -hh, 5])) == True
    
    def test_prism_face_centers_on_boundary(self):
        """Test that face centers are on the boundary."""
        size = Matrix([Rational(4), Rational(6)])
        orientation = Orientation()
        prism = RectangularPrism(size=size, transform=Transform(position=create_v3(0, 0, 0), orientation=orientation), start_distance=Rational(0), end_distance=Rational(10))
        
        hw, hh = Rational(2), Rational(3)
        
        # 6 face centers
        assert prism.is_point_on_boundary(Matrix([0, 0, 0])) == True  # Bottom
        assert prism.is_point_on_boundary(Matrix([0, 0, 10])) == True  # Top
        assert prism.is_point_on_boundary(Matrix([hw, 0, 5])) == True  # Right
        assert prism.is_point_on_boundary(Matrix([-hw, 0, 5])) == True  # Left
        assert prism.is_point_on_boundary(Matrix([0, hh, 5])) == True  # Front
        assert prism.is_point_on_boundary(Matrix([0, -hh, 5])) == True  # Back
    
    def test_prism_interior_not_on_boundary(self):
        """Test that interior points are NOT on the boundary."""
        size = Matrix([Rational(4), Rational(6)])
        orientation = Orientation()
        prism = RectangularPrism(size=size, transform=Transform(position=create_v3(0, 0, 0), orientation=orientation), start_distance=Rational(0), end_distance=Rational(10))
        
        # Center point should not be on boundary
        assert prism.is_point_on_boundary(Matrix([0, 0, 5])) == False
        
        # Other interior points
        assert prism.is_point_on_boundary(Matrix([Rational(1), Rational(1), Rational(5)])) == False
    
    def test_prism_exterior_not_on_boundary(self):
        """Test that exterior points are NOT on the boundary."""
        size = Matrix([Rational(4), Rational(6)])
        orientation = Orientation()
        prism = RectangularPrism(size=size, transform=Transform(position=create_v3(0, 0, 0), orientation=orientation), start_distance=Rational(0), end_distance=Rational(10))
        
        # Far-away point
        assert prism.is_point_on_boundary(Matrix([100, 100, 100])) == False
        
        # Just outside the prism
        assert prism.is_point_on_boundary(Matrix([3, 0, 5])) == False
        assert prism.is_point_on_boundary(Matrix([0, 4, 5])) == False
        assert prism.is_point_on_boundary(Matrix([0, 0, 11])) == False
    
    # ========================================================================
    # Cylinder Boundary Tests
    # ========================================================================
    
    def test_cylinder_cap_centers_on_boundary(self):
        """Test that cylinder cap centers are on the boundary."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, 
                           start_distance=Rational(0), end_distance=Rational(10))
        
        # Bottom cap center
        assert cylinder.is_point_on_boundary(Matrix([0, 0, 0])) == True
        
        # Top cap center
        assert cylinder.is_point_on_boundary(Matrix([0, 0, 10])) == True
    
    def test_cylinder_cap_circumference_on_boundary(self):
        """Test that points on cap circumferences are on the boundary."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, 
                           start_distance=Rational(0), end_distance=Rational(10))
        
        # Points on bottom cap circumference
        assert cylinder.is_point_on_boundary(Matrix([3, 0, 0])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, 3, 0])) == True
        assert cylinder.is_point_on_boundary(Matrix([-3, 0, 0])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, -3, 0])) == True
        
        # Points on top cap circumference
        assert cylinder.is_point_on_boundary(Matrix([3, 0, 10])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, 3, 10])) == True
        assert cylinder.is_point_on_boundary(Matrix([-3, 0, 10])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, -3, 10])) == True
    
    def test_cylinder_surface_points_on_boundary(self):
        """Test that points on the cylindrical surface are on the boundary."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, 
                           start_distance=Rational(0), end_distance=Rational(10))
        
        # Points on cylindrical surface at mid-height
        assert cylinder.is_point_on_boundary(Matrix([3, 0, 5])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, 3, 5])) == True
        assert cylinder.is_point_on_boundary(Matrix([-3, 0, 5])) == True
        assert cylinder.is_point_on_boundary(Matrix([0, -3, 5])) == True
    
    def test_cylinder_round_edges_on_boundary(self):
        """Test that points on round edges (cap circumferences) are on boundary."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, 
                           start_distance=Rational(0), end_distance=Rational(10))
        
        # Points on the round edge at bottom
        assert cylinder.is_point_on_boundary(Matrix([3, 0, 0])) == True
        
        # Points on the round edge at top
        assert cylinder.is_point_on_boundary(Matrix([3, 0, 10])) == True
    
    def test_cylinder_interior_not_on_boundary(self):
        """Test that interior points are NOT on the boundary."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, 
                           start_distance=Rational(0), end_distance=Rational(10))
        
        # Center point
        assert cylinder.is_point_on_boundary(Matrix([0, 0, 5])) == False
        
        # Interior point not on axis
        assert cylinder.is_point_on_boundary(Matrix([1, 1, 5])) == False
    
    def test_cylinder_exterior_not_on_boundary(self):
        """Test that exterior points are NOT on the boundary."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, 
                           start_distance=Rational(0), end_distance=Rational(10))
        
        # Far-away point
        assert cylinder.is_point_on_boundary(Matrix([100, 100, 100])) == False
        
        # Just outside radially
        assert cylinder.is_point_on_boundary(Matrix([4, 0, 5])) == False
        
        # Just outside axially
        assert cylinder.is_point_on_boundary(Matrix([0, 0, 11])) == False
    
    # ========================================================================
    # HalfSpace Boundary Tests
    # ========================================================================
    
    def test_halfspace_origin_on_boundary(self):
        """Test that the plane origin is on the boundary."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal=normal, offset=offset)
        
        # Plane origin (normal * offset)
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 5])) == True
    
    def test_halfspace_random_plane_points_on_boundary(self):
        """Test that random points on the plane are on the boundary."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal=normal, offset=offset)
        
        # Points on the plane (z = 5)
        assert halfspace.is_point_on_boundary(Matrix([10, 20, 5])) == True
        assert halfspace.is_point_on_boundary(Matrix([-15, 7, 5])) == True
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 5])) == True
        assert halfspace.is_point_on_boundary(Matrix([100, -50, 5])) == True
    
    def test_halfspace_positive_side_not_on_boundary(self):
        """Test that points on the positive side (inside) are NOT on boundary."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal=normal, offset=offset)
        
        # Points above the plane (z > 5) are inside but not on boundary
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 6])) == False
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 10])) == False
        assert halfspace.is_point_on_boundary(Matrix([5, 5, 20])) == False
    
    def test_halfspace_negative_side_not_on_boundary(self):
        """Test that points on the negative side (outside) are NOT on boundary."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfspace = HalfSpace(normal=normal, offset=offset)
        
        # Points below the plane (z < 5) are outside and not on boundary
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 4])) == False
        assert halfspace.is_point_on_boundary(Matrix([0, 0, 0])) == False
        assert halfspace.is_point_on_boundary(Matrix([5, 5, -10])) == False
    
    # ========================================================================
    # ConvexPolygonExtrusion Boundary Tests
    # ========================================================================
    
    def test_convex_polygon_vertices_on_boundary(self):
        """Test that all vertices at both ends are on the boundary."""
        points = [
            Matrix([2, 0]),
            Matrix([0, 2]),
            Matrix([-2, 0]),
            Matrix([0, -2])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Vertices at z=start_distance
        assert extrusion.is_point_on_boundary(Matrix([2, 0, 0])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, 2, 0])) == True
        assert extrusion.is_point_on_boundary(Matrix([-2, 0, 0])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, -2, 0])) == True
        
        # Vertices at z=end_distance
        assert extrusion.is_point_on_boundary(Matrix([2, 0, 10])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, 2, 10])) == True
        assert extrusion.is_point_on_boundary(Matrix([-2, 0, 10])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, -2, 10])) == True
    
    def test_convex_polygon_edge_points_on_boundary(self):
        """Test that points along vertical edges are on the boundary."""
        points = [
            Matrix([2, 0]),
            Matrix([0, 2]),
            Matrix([-2, 0]),
            Matrix([0, -2])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Points along vertical edges at mid-height
        assert extrusion.is_point_on_boundary(Matrix([2, 0, 5])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, 2, 5])) == True
        assert extrusion.is_point_on_boundary(Matrix([-2, 0, 5])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, -2, 5])) == True
    
    def test_convex_polygon_face_points_on_boundary(self):
        """Test that points on top/bottom faces are on the boundary."""
        points = [
            Matrix([2, 0]),
            Matrix([0, 2]),
            Matrix([-2, 0]),
            Matrix([0, -2])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Points on bottom face (z=start_distance)
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 0])) == True
        assert extrusion.is_point_on_boundary(Matrix([1, 0, 0])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, 1, 0])) == True
        
        # Points on top face (z=end_distance)
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 10])) == True
        assert extrusion.is_point_on_boundary(Matrix([1, 0, 10])) == True
        assert extrusion.is_point_on_boundary(Matrix([0, 1, 10])) == True
    
    def test_convex_polygon_interior_not_on_boundary(self):
        """Test that interior points are NOT on the boundary."""
        points = [
            Matrix([2, 0]),
            Matrix([0, 2]),
            Matrix([-2, 0]),
            Matrix([0, -2])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Interior point at mid-height
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 5])) == False
        assert extrusion.is_point_on_boundary(Matrix([Rational(1, 2), Rational(1, 2), 5])) == False
    
    def test_convex_polygon_exterior_not_on_boundary(self):
        """Test that exterior points are NOT on the boundary."""
        points = [
            Matrix([2, 0]),
            Matrix([0, 2]),
            Matrix([-2, 0]),
            Matrix([0, -2])
        ]
        start_distance = Rational(0)
        end_distance = Rational(10)
        orientation = Orientation()
        extrusion = ConvexPolygonExtrusion(points=points, start_distance=start_distance,
                                          end_distance=end_distance, transform=Transform.identity())
        
        # Far-away point
        assert extrusion.is_point_on_boundary(Matrix([100, 100, 100])) == False
        
        # Just outside the polygon
        assert extrusion.is_point_on_boundary(Matrix([3, 0, 5])) == False
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 11])) == False
    
    # ========================================================================
    # Random Shape Tests
    # ========================================================================
    
    
    def test_random_prisms_boundary_points(self):
        """Test boundary detection on 25 random prisms."""
        random.seed(42)  # For reproducibility
        
        for i in range(num_random_samples):
            prism = generate_random_prism()
            
            # Get boundary points
            boundary_points = generate_prism_boundary_points(prism)
            
            # All boundary points should be on boundary
            for point in boundary_points:
                assert prism.is_point_on_boundary(point) == True, \
                    f"RectangularPrism {i}: Point {point.T} should be on boundary"
            
            # Get non-boundary points
            non_boundary_points = generate_prism_non_boundary_points(prism)
            
            # Non-boundary points should NOT be on boundary
            for point in non_boundary_points:
                assert prism.is_point_on_boundary(point) == False, \
                    f"RectangularPrism {i}: Point {point.T} should NOT be on boundary"
    
    def test_random_cylinders_boundary_points(self):
        """Test boundary detection on 25 random cylinders."""
        random.seed(43)  # For reproducibility
        
        for i in range(num_random_samples):
            cylinder = generate_random_cylinder()
            
            # Get boundary points
            boundary_points = generate_cylinder_boundary_points(cylinder)
            
            # All boundary points should be on boundary
            for point in boundary_points:
                assert cylinder.is_point_on_boundary(point) == True, \
                    f"Cylinder {i}: Point {point.T} should be on boundary"
            
            # Get non-boundary points
            non_boundary_points = generate_cylinder_non_boundary_points(cylinder)
            
            # Non-boundary points should NOT be on boundary
            for point in non_boundary_points:
                assert cylinder.is_point_on_boundary(point) == False, \
                    f"Cylinder {i}: Point {point.T} should NOT be on boundary"
    
    def test_random_halfspaces_boundary_points(self):
        """Test boundary detection on 25 random half-planes."""
        random.seed(44)  # For reproducibility
        
        for i in range(num_random_samples):
            halfspace = generate_random_halfspace()
            
            # Get boundary points
            boundary_points = generate_halfspace_boundary_points(halfspace)
            
            # All boundary points should be on boundary
            for point in boundary_points:
                assert halfspace.is_point_on_boundary(point) == True, \
                    f"HalfSpace {i}: Point {point.T} should be on boundary"
            
            # Get non-boundary points - these are NOT on boundary
            non_boundary_points = generate_halfspace_non_boundary_points(halfspace)
            
            # Non-boundary points should NOT be on boundary
            for point in non_boundary_points:
                assert halfspace.is_point_on_boundary(point) == False, \
                    f"HalfSpace {i}: Point {point.T} should NOT be on boundary"
    
    def test_random_convex_polygons_boundary_points(self):
        """Test boundary detection on 25 random convex polygon extrusions."""
        random.seed(45)  # For reproducibility
        
        for i in range(num_random_samples):
            extrusion = generate_random_convex_polygon_extrusion()
            
            # Get boundary points
            boundary_points = generate_convex_polygon_boundary_points(extrusion)
            
            # All boundary points should be on boundary
            for point in boundary_points:
                assert extrusion.is_point_on_boundary(point) == True, \
                    f"ConvexPolygon {i}: Point {point.T} should be on boundary"
            
            # Get non-boundary points
            non_boundary_points = generate_convex_polygon_non_boundary_points(extrusion)
            
            # Non-boundary points should NOT be on boundary
            for point in non_boundary_points:
                assert extrusion.is_point_on_boundary(point) == False, \
                    f"ConvexPolygon {i}: Point {point.T} should NOT be on boundary"

