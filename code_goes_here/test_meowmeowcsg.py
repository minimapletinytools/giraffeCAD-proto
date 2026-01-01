"""
Tests for meowmeowcsg.py module.

This module contains tests for the CSG primitives and operations.
"""

import pytest
from sympy import Matrix, Rational, simplify
from code_goes_here.moothymoth import Orientation
from code_goes_here.meowmeowcsg import (
    HalfPlane, Prism, Cylinder, Union, Difference
)
from .conftest import assert_is_valid_rotation_matrix


class TestMinimalBoundary:
    """Test minimal_boundary_in_direction for CSG primitives."""
    
    def test_prism_minimal_boundary_x_direction(self):
        """Test prism minimal boundary in X direction."""
        # Create a prism along Z axis from z=0 to z=10, with 4x6 cross-section
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation (Z-axis aligned)
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        # Minimal boundary in +X direction should be at one of the corners
        direction = Matrix([1, 0, 0])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # With identity orientation: width (4) along X, height (6) along Y
        # So half-width = 2, half-height = 3
        assert boundary[0] == -2  # Minimal x coordinate
        assert abs(boundary[1]) <= 3  # Within Y range
        assert boundary[2] in [0, 10]  # At one of the ends
    
    def test_prism_minimal_boundary_negative_x_direction(self):
        """Test prism minimal boundary in negative X direction."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        # Minimal boundary in -X direction should be at positive x
        direction = Matrix([-1, 0, 0])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # The x-coordinate should be positive (opposite corner from +X test)
        # With identity orientation: width (4) is along X, so half-width = 2
        assert boundary[0] == 2  # At the positive extreme
    
    def test_prism_minimal_boundary_z_direction(self):
        """Test prism minimal boundary in Z direction (along axis)."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=Rational(5), end_distance=Rational(15))
        
        # Minimal boundary in +Z direction should be at z=5 (start)
        direction = Matrix([0, 0, 1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        assert boundary[2] == 5
    
    def test_prism_minimal_boundary_diagonal_direction(self):
        """Test prism minimal boundary in diagonal direction."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        # Minimal boundary in diagonal direction
        direction = Matrix([1, 1, 1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Should be at one of the corners with negative x, y, z components
        # With identity orientation: width (4) along X, height (6) along Y
        assert boundary[0] == -2  # Minimal x (half-width = 2)
        assert boundary[1] == -3  # Minimal y (half-height = 3)
        assert boundary[2] == 0   # Start (minimal z)
    
    def test_prism_infinite_raises_error(self):
        """Test that infinite prism raises error."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation)  # Infinite in both directions
        
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="infinite in both directions"):
            prism.minimal_boundary_in_direction(direction)
    
    def test_prism_semi_infinite_negative_direction_works(self):
        """Test semi-infinite prism works when querying opposite to infinite direction."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, end_distance=10)  # Infinite in negative direction
        
        # Query in +Z (away from infinite direction) should work
        direction = Matrix([0, 0, 1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (z=10)
        assert boundary[2] == 10
    
    def test_prism_semi_infinite_negative_direction_raises_error(self):
        """Test semi-infinite prism raises error when querying in infinite direction."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, end_distance=10)  # Infinite in negative direction
        
        # Query in -Z (toward infinite direction) should raise error
        direction = Matrix([0, 0, -1])
        with pytest.raises(ValueError, match="infinite in negative direction"):
            prism.minimal_boundary_in_direction(direction)
    
    def test_prism_semi_infinite_positive_direction_works(self):
        """Test semi-infinite prism works when querying opposite to infinite direction."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=5)  # Infinite in positive direction
        
        # Query in -Z (away from infinite direction) should work
        direction = Matrix([0, 0, -1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (z=5)
        assert boundary[2] == 5
    
    def test_prism_semi_infinite_positive_direction_raises_error(self):
        """Test semi-infinite prism raises error when querying in infinite direction."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, start_distance=5)  # Infinite in positive direction
        
        # Query in +Z (toward infinite direction) should raise error
        direction = Matrix([0, 0, 1])
        with pytest.raises(ValueError, match="infinite in positive direction"):
            prism.minimal_boundary_in_direction(direction)
    
    def test_prism_semi_infinite_perpendicular_direction(self):
        """Test semi-infinite prism works for perpendicular directions."""
        size = Matrix([4, 6])
        orientation = Orientation()  # Identity orientation
        prism = Prism(size=size, orientation=orientation, end_distance=10)  # Infinite in negative Z
        
        # Query in X direction (perpendicular to axis) should work
        direction = Matrix([1, 0, 0])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Should work and return a point on the finite end
        assert boundary[2] == 10
    
    def test_cylinder_minimal_boundary_x_direction(self):
        """Test cylinder minimal boundary in X direction."""
        # Cylinder along Z axis, radius 3, from z=0 to z=10
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # Minimal boundary in +X direction should be at x=-3 (leftmost point)
        direction = Matrix([1, 0, 0])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        assert boundary[0] == -3
        assert boundary[1] == 0  # On the x-axis side
        # Should be at one of the ends
        assert boundary[2] == 0 or boundary[2] == 10
    
    def test_cylinder_minimal_boundary_z_direction(self):
        """Test cylinder minimal boundary in Z direction (along axis)."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=Rational(5), end_distance=Rational(15))
        
        # Minimal boundary in +Z direction should be at z=5
        direction = Matrix([0, 0, 1])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        assert boundary[2] == 5
        # Radial position can be anywhere on the circle
        radial_dist = (boundary[0]**2 + boundary[1]**2)**Rational(1, 2)
        assert simplify(radial_dist - radius) == 0
    
    def test_cylinder_minimal_boundary_diagonal(self):
        """Test cylinder minimal boundary in diagonal direction."""
        axis = Matrix([0, 0, 1])
        radius = Rational(2)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=0, end_distance=10)
        
        # Minimal in (1, 1, 1) direction
        direction = Matrix([1, 1, 1])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        # Should be at start (z=0) and radially opposite to (1,1) direction
        assert boundary[2] == 0
        # The radial component should be opposite to (1, 1) normalized
        # which is (-sqrt(2), -sqrt(2)) * radius/sqrt(2) = (-radius, -radius)
        # But since we're normalizing, it's proportional
        assert boundary[0] < 0  # Negative x
        assert boundary[1] < 0  # Negative y
    
    def test_cylinder_infinite_raises_error(self):
        """Test that infinite cylinder raises error."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius)  # Infinite
        
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="infinite in both directions"):
            cylinder.minimal_boundary_in_direction(direction)
    
    def test_cylinder_semi_infinite_negative_direction_works(self):
        """Test semi-infinite cylinder works when querying opposite to infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, end_distance=10)  # Infinite in negative direction
        
        # Query in +X (away from infinite direction) should work
        direction = Matrix([1, 0, 0])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (x=10)
        assert boundary[0] == 10
    
    def test_cylinder_semi_infinite_negative_direction_raises_error(self):
        """Test semi-infinite cylinder raises error when querying in infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, end_distance=10)  # Infinite in negative direction
        
        # Query in -X (toward infinite direction) should raise error
        direction = Matrix([-1, 0, 0])
        with pytest.raises(ValueError, match="infinite in negative direction"):
            cylinder.minimal_boundary_in_direction(direction)
    
    def test_cylinder_semi_infinite_positive_direction_works(self):
        """Test semi-infinite cylinder works when querying opposite to infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=-5)  # Infinite in positive direction
        
        # Query in -X (away from infinite direction) should work
        direction = Matrix([-1, 0, 0])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (x=-5)
        assert boundary[0] == -5
    
    def test_cylinder_semi_infinite_positive_direction_raises_error(self):
        """Test semi-infinite cylinder raises error when querying in infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, start_distance=-5)  # Infinite in positive direction
        
        # Query in +X (toward infinite direction) should raise error
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="infinite in positive direction"):
            cylinder.minimal_boundary_in_direction(direction)
    
    def test_cylinder_semi_infinite_perpendicular_direction(self):
        """Test semi-infinite cylinder works for perpendicular directions."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = Cylinder(axis_direction=axis, radius=radius, end_distance=10)  # Infinite in negative Z
        
        # Query in X direction (perpendicular to axis) should work
        direction = Matrix([1, 0, 0])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        # Should work and return a point on the finite end
        assert boundary[2] == 10
        assert boundary[0] == -3  # At minimal X position on the circle
    
    def test_halfplane_minimal_boundary_opposite_direction(self):
        """Test half-plane minimal boundary when direction is opposite to normal."""
        # Half-plane with normal in +Z direction at z=5
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Minimal boundary in -Z direction (opposite to normal)
        direction = Matrix([0, 0, -1])
        boundary = halfplane.minimal_boundary_in_direction(direction)
        
        # Should return point on the plane at offset distance along normal
        assert boundary[2] == 5
        assert boundary[0] == 0
        assert boundary[1] == 0
    
    def test_halfplane_minimal_boundary_scaled_opposite_direction(self):
        """Test half-plane with scaled opposite direction."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Scaled opposite direction should also work
        direction = Matrix([0, 0, -3])
        boundary = halfplane.minimal_boundary_in_direction(direction)
        
        assert boundary[2] == 5
    
    def test_halfplane_same_direction_raises_error(self):
        """Test that half-plane in same direction as normal raises error."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Direction same as normal (unbounded)
        direction = Matrix([0, 0, 1])
        with pytest.raises(ValueError, match="unbounded except in the direction exactly opposite"):
            halfplane.minimal_boundary_in_direction(direction)
    
    def test_halfplane_perpendicular_raises_error(self):
        """Test that half-plane perpendicular to direction raises error."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Direction perpendicular to normal (in XY plane)
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="unbounded except in the direction exactly opposite"):
            halfplane.minimal_boundary_in_direction(direction)
    
    def test_halfplane_diagonal_raises_error(self):
        """Test that half-plane with non-opposite diagonal direction raises error."""
        normal = Matrix([0, 0, 1])
        offset = Rational(5)
        halfplane = HalfPlane(normal, offset)
        
        # Diagonal direction (not exactly opposite to normal)
        direction = Matrix([1, 1, -1])
        with pytest.raises(ValueError, match="unbounded except in the direction exactly opposite"):
            halfplane.minimal_boundary_in_direction(direction)
    
    def test_union_minimal_boundary(self):
        """Test union minimal boundary."""
        # Two prisms at different locations
        size = Matrix([2, 2])
        orientation = Orientation()  # Identity orientation
        
        prism1 = Prism(size=size, orientation=orientation, start_distance=0, end_distance=5)
        prism2 = Prism(size=size, orientation=orientation, start_distance=10, end_distance=15)
        
        union = Union([prism1, prism2])
        
        # Minimal in +Z direction should be from prism1 (z=0)
        direction = Matrix([0, 0, 1])
        boundary = union.minimal_boundary_in_direction(direction)
        
        assert boundary[2] == 0
    
    def test_union_empty_raises_error(self):
        """Test that empty union raises error."""
        union = Union([])
        
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="empty union"):
            union.minimal_boundary_in_direction(direction)
    
    def test_difference_minimal_boundary(self):
        """Test difference minimal boundary."""
        # Base prism
        size = Matrix([10, 10])
        orientation = Orientation()  # Identity orientation
        base = Prism(size=size, orientation=orientation, start_distance=0, end_distance=10)
        
        # Subtract a smaller prism (doesn't affect the minimal boundary)
        subtract = Prism(size=Matrix([2, 2]), orientation=orientation, start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Minimal boundary should be same as base
        direction = Matrix([1, 0, 0])
        boundary = diff.minimal_boundary_in_direction(direction)
        
        # With identity orientation: width (10) along X, so half-width = 5
        assert boundary[0] == -5  # Half of base width


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

