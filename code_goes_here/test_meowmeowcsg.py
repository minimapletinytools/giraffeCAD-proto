"""
Tests for meowmeowcsg.py module.

This module contains tests for the CSG primitives and operations.
"""

import pytest
from sympy import Matrix, Rational, simplify, sqrt
from code_goes_here.moothymoth import Orientation
from code_goes_here.meowmeowcsg import (
    HalfPlane, Prism, Cylinder, Union, Difference, ConvexPolygonExtrusion
)
from .conftest import assert_is_valid_rotation_matrix


class TestConstructors:
    """Test the Prism and Cylinder constructors."""
    
    def test_prism_constructor_finite(self):
        """Test creating a finite prism."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        assert prism.size == size
        assert prism.orientation == orientation
        assert prism.start_distance == 0
        assert prism.end_distance == 10
    
    def test_prism_constructor_semi_infinite(self):
        """Test creating a semi-infinite prism."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, end_distance=10)
        
        assert prism.start_distance is None
        assert prism.end_distance == 10
    
    def test_prism_constructor_infinite(self):
        """Test creating an infinite prism."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation)
        
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
    """Test Prism get_bottom_position and get_top_position methods."""
    
    def test_get_bottom_position_finite_prism(self):
        """Test get_bottom_position on a finite prism."""
        # Create a prism with identity orientation
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        position = Matrix([10, 20, 30])
        start_distance = Rational(5)
        end_distance = Rational(15)
        prism = Prism(size=size, orientation=orientation, position=position, 
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
        prism = Prism(size=size, orientation=orientation, position=position, 
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
        prism = Prism(size=size, orientation=orientation, position=position,
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
        orientation = Orientation()
        prism = Prism(size=size, orientation=orientation, start_distance=None, end_distance=10)
        
        with pytest.raises(ValueError, match="infinite prism"):
            prism.get_bottom_position()
    
    def test_get_top_position_infinite_prism_raises_error(self):
        """Test that get_top_position raises error for infinite prism."""
        size = Matrix([4, 6])
        orientation = Orientation()
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=None)
        
        with pytest.raises(ValueError, match="infinite prism"):
            prism.get_top_position()


class TestHalfPlaneContainsPoint:
    """Test HalfPlane contains_point and is_point_on_boundary methods."""
    
    def test_halfplane_contains_point_on_positive_side(self):
        """Test that a point on the positive side is contained."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Point at z=10 (above the plane at z=5)
        point = Matrix([0, 0, 10])
        assert halfplane.contains_point(point) == True
    
    def test_halfplane_contains_point_on_boundary(self):
        """Test that a point on the boundary is contained."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Point at z=5 (on the plane)
        point = Matrix([1, 2, 5])
        assert halfplane.contains_point(point) == True
    
    def test_halfplane_contains_point_on_negative_side(self):
        """Test that a point on the negative side is not contained."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Point at z=0 (below the plane at z=5)
        point = Matrix([0, 0, 0])
        assert halfplane.contains_point(point) == False
    
    def test_halfplane_is_point_on_boundary(self):
        """Test boundary detection."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Point on boundary
        assert halfplane.is_point_on_boundary(Matrix([0, 0, 5])) == True
        assert halfplane.is_point_on_boundary(Matrix([1, 1, 5])) == True
        
        # Point not on boundary
        assert halfplane.is_point_on_boundary(Matrix([0, 0, 6])) == False
        assert halfplane.is_point_on_boundary(Matrix([0, 0, 4])) == False
    
    def test_halfplane_diagonal_normal(self):
        """Test half-plane with diagonal normal."""
        normal = Matrix([1, 1, 1])
        offset = Rational(0)
        halfplane = HalfPlane(normal, offset)
        
        # Point where x+y+z > 0
        assert halfplane.contains_point(Matrix([1, 0, 0])) == True
        assert halfplane.contains_point(Matrix([1, 1, 1])) == True
        
        # Point where x+y+z = 0
        assert halfplane.contains_point(Matrix([0, 0, 0])) == True
        assert halfplane.is_point_on_boundary(Matrix([0, 0, 0])) == True
        
        # Point where x+y+z < 0
        assert halfplane.contains_point(Matrix([-1, 0, 0])) == False


class TestPrismContainsPoint:
    """Test Prism contains_point and is_point_on_boundary methods."""
    
    def test_prism_contains_point_inside(self):
        """Test that a point inside the prism is contained."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        # Point inside: within ±2 in x, ±3 in y, 0-10 in z
        point = Matrix([0, 0, 5])
        assert prism.contains_point(point) == True
    
    def test_prism_contains_point_on_face(self):
        """Test that a point on a face is contained."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        # Point on face (x = 2, which is half-width)
        point = Matrix([2, 0, 5])
        assert prism.contains_point(point) == True
    
    def test_prism_contains_point_outside(self):
        """Test that a point outside the prism is not contained."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
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
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
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
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        # Interior point
        assert prism.is_point_on_boundary(Matrix([0, 0, 5])) == False
    
    def test_prism_semi_infinite_contains(self):
        """Test semi-infinite prism containment."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, end_distance=10)  # Infinite in negative direction
        
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
    """Test Union contains_point and is_point_on_boundary methods."""
    
    def test_union_contains_point_in_first_child(self):
        """Test that a point in the first child is contained."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = Prism(size=size, orientation=orientation, start_distance=0, end_distance=5)
        prism2 = Prism(size=size, orientation=orientation, start_distance=10, end_distance=15)
        
        union = Union([prism1, prism2])
        
        # Point in first prism
        assert union.contains_point(Matrix([0, 0, 3])) == True
    
    def test_union_contains_point_in_second_child(self):
        """Test that a point in the second child is contained."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = Prism(size=size, orientation=orientation, start_distance=0, end_distance=5)
        prism2 = Prism(size=size, orientation=orientation, start_distance=10, end_distance=15)
        
        union = Union([prism1, prism2])
        
        # Point in second prism
        assert union.contains_point(Matrix([0, 0, 12])) == True
    
    def test_union_contains_point_outside_all(self):
        """Test that a point outside all children is not contained."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = Prism(size=size, orientation=orientation, start_distance=0, end_distance=5)
        prism2 = Prism(size=size, orientation=orientation, start_distance=10, end_distance=15)
        
        union = Union([prism1, prism2])
        
        # Point between the two prisms
        assert union.contains_point(Matrix([0, 0, 7])) == False
    
    def test_union_is_point_on_boundary(self):
        """Test boundary detection for union."""
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = Prism(size=size, orientation=orientation, start_distance=0, end_distance=5)
        prism2 = Prism(size=size, orientation=orientation, start_distance=10, end_distance=15)
        
        union = Union([prism1, prism2])
        
        # Point on boundary of first prism
        assert union.is_point_on_boundary(Matrix([1, 0, 3])) == True
        
        # Point on boundary of second prism
        assert union.is_point_on_boundary(Matrix([1, 0, 12])) == True


class TestDifferenceContainsPoint:
    """Test Difference contains_point and is_point_on_boundary methods."""
    
    def test_difference_contains_point_in_base_not_subtracted(self):
        """Test that a point in base but not in subtract is contained."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = Prism(size=size_base, orientation=orientation, start_distance=0, end_distance=10)
        subtract = Prism(size=size_subtract, orientation=orientation, start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point in base but outside subtract region
        assert diff.contains_point(Matrix([4, 4, 5])) == True
    
    def test_difference_contains_point_subtracted(self):
        """Test that a point in subtract region is not contained."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = Prism(size=size_base, orientation=orientation, start_distance=0, end_distance=10)
        subtract = Prism(size=size_subtract, orientation=orientation, start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point in subtract region
        assert diff.contains_point(Matrix([0, 0, 5])) == False
    
    def test_difference_contains_point_outside_base(self):
        """Test that a point outside base is not contained."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = Prism(size=size_base, orientation=orientation, start_distance=0, end_distance=10)
        subtract = Prism(size=size_subtract, orientation=orientation, start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point outside base
        assert diff.contains_point(Matrix([10, 10, 5])) == False
    
    def test_difference_is_point_on_boundary_base(self):
        """Test boundary detection on base boundary."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = Prism(size=size_base, orientation=orientation, start_distance=0, end_distance=10)
        subtract = Prism(size=size_subtract, orientation=orientation, start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point on base boundary (not in subtract region)
        assert diff.is_point_on_boundary(Matrix([5, 4, 5])) == True
    
    def test_difference_is_point_on_boundary_subtract(self):
        """Test boundary detection on subtract boundary."""
        size_base = Matrix([10, 10])
        size_subtract = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        base = Prism(size=size_base, orientation=orientation, start_distance=0, end_distance=10)
        subtract = Prism(size=size_subtract, orientation=orientation, start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Point on subtract boundary (creates new boundary in difference)
        # At x=1 (edge of subtract), y=0, z=5
        assert diff.is_point_on_boundary(Matrix([1, 0, 5])) == True


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
        length = Rational(10)
        orientation = Orientation()  # Identity orientation
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
        assert extrusion.points == points
        assert extrusion.length == length
        assert extrusion.orientation == orientation
    
    def test_is_valid_enough_points(self):
        """Test that is_valid requires at least 3 points."""
        # Triangle (valid)
        points_valid = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([0, 1])
        ]
        length = Rational(5)
        orientation = Orientation()
        
        extrusion_valid = ConvexPolygonExtrusion(points=points_valid, length=length, orientation=orientation)
        assert extrusion_valid.is_valid() == True
        
        # Only 2 points (invalid)
        points_invalid = [
            Matrix([0, 0]),
            Matrix([1, 0])
        ]
        extrusion_invalid = ConvexPolygonExtrusion(points=points_invalid, length=length, orientation=orientation)
        assert extrusion_invalid.is_valid() == False
    
    def test_is_valid_positive_length(self):
        """Test that is_valid requires positive length."""
        points = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([0, 1])
        ]
        orientation = Orientation()
        
        # Positive length (valid)
        extrusion_valid = ConvexPolygonExtrusion(points=points, length=Rational(5), orientation=orientation)
        assert extrusion_valid.is_valid() == True
        
        # Zero length (invalid)
        extrusion_zero = ConvexPolygonExtrusion(points=points, length=0, orientation=orientation)
        assert extrusion_zero.is_valid() == False
        
        # Negative length (invalid)
        extrusion_negative = ConvexPolygonExtrusion(points=points, length=-5, orientation=orientation)
        assert extrusion_negative.is_valid() == False
    
    def test_is_valid_convex_polygon(self):
        """Test that is_valid accepts convex polygons."""
        orientation = Orientation()
        
        # Convex square (counter-clockwise)
        points_ccw = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        extrusion_ccw = ConvexPolygonExtrusion(points=points_ccw, length=Rational(5), orientation=orientation)
        assert extrusion_ccw.is_valid() == True
        
        # Convex square (clockwise)
        points_cw = [
            Matrix([1, 1]),
            Matrix([1, -1]),
            Matrix([-1, -1]),
            Matrix([-1, 1])
        ]
        extrusion_cw = ConvexPolygonExtrusion(points=points_cw, length=Rational(5), orientation=orientation)
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
        extrusion_hex = ConvexPolygonExtrusion(points=points_hex, length=Rational(5), orientation=orientation)
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
        extrusion_concave = ConvexPolygonExtrusion(points=points_concave, length=Rational(5), orientation=orientation)
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
        extrusion_collinear = ConvexPolygonExtrusion(points=points_collinear, length=Rational(5), orientation=orientation)
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
        length = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
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
        length = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
        # Point on top face (z = length)
        assert extrusion.contains_point(Matrix([0, 0, 10])) == True
        
        # Point on bottom face (z = 0)
        assert extrusion.contains_point(Matrix([0, 0, 0])) == True
    
    def test_contains_point_outside_square(self):
        """Test that a point outside is not contained."""
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        length = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
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
        length = Rational(5)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
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
        length = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
        # On bottom face (z = 0)
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 0])) == True
        
        # On top face (z = length)
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 10])) == True
    
    def test_is_point_on_boundary_side_face(self):
        """Test boundary detection on side faces."""
        points = [
            Matrix([1, 1]),
            Matrix([-1, 1]),
            Matrix([-1, -1]),
            Matrix([1, -1])
        ]
        length = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
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
        length = Rational(10)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
        # Interior point
        assert extrusion.is_point_on_boundary(Matrix([0, 0, 5])) == False
    
    def test_repr(self):
        """Test string representation."""
        points = [
            Matrix([0, 0]),
            Matrix([1, 0]),
            Matrix([0, 1])
        ]
        length = Rational(5)
        orientation = Orientation()
        
        extrusion = ConvexPolygonExtrusion(points=points, length=length, orientation=orientation)
        
        repr_str = repr(extrusion)
        assert "ConvexPolygonExtrusion" in repr_str
        assert "3 points" in repr_str
        assert "5" in repr_str

