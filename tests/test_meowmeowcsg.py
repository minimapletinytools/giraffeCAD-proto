"""
Tests for meowmeowcsg.py module.

This module contains tests for the CSG primitives and operations.
"""

import pytest
from sympy import Matrix, Rational, simplify
from meowmeowcsg import (
    HalfPlane, Prism, Cylinder, Union, Difference,
    create_prism, create_cylinder
)


class TestMinimalBoundary:
    """Test minimal_boundary_in_direction for CSG primitives."""
    
    def test_prism_minimal_boundary_x_direction(self):
        """Test prism minimal boundary in X direction."""
        # Create a prism along Z axis from z=0 to z=10, with 4x6 cross-section
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, start_distance=0, end_distance=10)
        
        # Minimal boundary in +X direction should be at one of the corners
        direction = Matrix([1, 0, 0])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Check that it's at one of the corners (minimal x coordinate)
        # The cross-section has half-dimensions of 2 and 3
        assert abs(boundary[0]) == 3 or abs(boundary[0]) == 2
        assert abs(boundary[1]) == 3 or abs(boundary[1]) == 2
        assert boundary[2] in [0, 10]  # At one of the ends
    
    def test_prism_minimal_boundary_negative_x_direction(self):
        """Test prism minimal boundary in negative X direction."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, start_distance=0, end_distance=10)
        
        # Minimal boundary in -X direction should be at positive x
        direction = Matrix([-1, 0, 0])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # The x-coordinate should be positive (opposite corner from +X test)
        assert boundary[0] == 3  # At the positive extreme
    
    def test_prism_minimal_boundary_z_direction(self):
        """Test prism minimal boundary in Z direction (along axis)."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, start_distance=Rational(5), end_distance=Rational(15))
        
        # Minimal boundary in +Z direction should be at z=5 (start)
        direction = Matrix([0, 0, 1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        assert boundary[2] == 5
    
    def test_prism_minimal_boundary_diagonal_direction(self):
        """Test prism minimal boundary in diagonal direction."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, start_distance=0, end_distance=10)
        
        # Minimal boundary in diagonal direction
        direction = Matrix([1, 1, 1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Should be at one of the corners with negative x, y, z components
        # (The exact mapping depends on the basis vectors)
        assert boundary[0] == -3  # Minimal x
        assert boundary[1] == -2  # Minimal y
        assert boundary[2] == 0   # Start (minimal z)
    
    def test_prism_infinite_raises_error(self):
        """Test that infinite prism raises error."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation)  # Infinite in both directions
        
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="infinite in both directions"):
            prism.minimal_boundary_in_direction(direction)
    
    def test_prism_semi_infinite_negative_direction_works(self):
        """Test semi-infinite prism works when querying opposite to infinite direction."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, end_distance=10)  # Infinite in negative direction
        
        # Query in +Z (away from infinite direction) should work
        direction = Matrix([0, 0, 1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (z=10)
        assert boundary[2] == 10
    
    def test_prism_semi_infinite_negative_direction_raises_error(self):
        """Test semi-infinite prism raises error when querying in infinite direction."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, end_distance=10)  # Infinite in negative direction
        
        # Query in -Z (toward infinite direction) should raise error
        direction = Matrix([0, 0, -1])
        with pytest.raises(ValueError, match="infinite in negative direction"):
            prism.minimal_boundary_in_direction(direction)
    
    def test_prism_semi_infinite_positive_direction_works(self):
        """Test semi-infinite prism works when querying opposite to infinite direction."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, start_distance=5)  # Infinite in positive direction
        
        # Query in -Z (away from infinite direction) should work
        direction = Matrix([0, 0, -1])
        boundary = prism.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (z=5)
        assert boundary[2] == 5
    
    def test_prism_semi_infinite_positive_direction_raises_error(self):
        """Test semi-infinite prism raises error when querying in infinite direction."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, start_distance=5)  # Infinite in positive direction
        
        # Query in +Z (toward infinite direction) should raise error
        direction = Matrix([0, 0, 1])
        with pytest.raises(ValueError, match="infinite in positive direction"):
            prism.minimal_boundary_in_direction(direction)
    
    def test_prism_semi_infinite_perpendicular_direction(self):
        """Test semi-infinite prism works for perpendicular directions."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, end_distance=10)  # Infinite in negative Z
        
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
        cylinder = create_cylinder(axis, radius, start_distance=0, end_distance=10)
        
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
        cylinder = create_cylinder(axis, radius, start_distance=Rational(5), end_distance=Rational(15))
        
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
        cylinder = create_cylinder(axis, radius, start_distance=0, end_distance=10)
        
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
        cylinder = create_cylinder(axis, radius)  # Infinite
        
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="infinite in both directions"):
            cylinder.minimal_boundary_in_direction(direction)
    
    def test_cylinder_semi_infinite_negative_direction_works(self):
        """Test semi-infinite cylinder works when querying opposite to infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = create_cylinder(axis, radius, end_distance=10)  # Infinite in negative direction
        
        # Query in +X (away from infinite direction) should work
        direction = Matrix([1, 0, 0])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (x=10)
        assert boundary[0] == 10
    
    def test_cylinder_semi_infinite_negative_direction_raises_error(self):
        """Test semi-infinite cylinder raises error when querying in infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = create_cylinder(axis, radius, end_distance=10)  # Infinite in negative direction
        
        # Query in -X (toward infinite direction) should raise error
        direction = Matrix([-1, 0, 0])
        with pytest.raises(ValueError, match="infinite in negative direction"):
            cylinder.minimal_boundary_in_direction(direction)
    
    def test_cylinder_semi_infinite_positive_direction_works(self):
        """Test semi-infinite cylinder works when querying opposite to infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = create_cylinder(axis, radius, start_distance=-5)  # Infinite in positive direction
        
        # Query in -X (away from infinite direction) should work
        direction = Matrix([-1, 0, 0])
        boundary = cylinder.minimal_boundary_in_direction(direction)
        
        # Should be at the finite end (x=-5)
        assert boundary[0] == -5
    
    def test_cylinder_semi_infinite_positive_direction_raises_error(self):
        """Test semi-infinite cylinder raises error when querying in infinite direction."""
        axis = Matrix([1, 0, 0])
        radius = Rational(3)
        cylinder = create_cylinder(axis, radius, start_distance=-5)  # Infinite in positive direction
        
        # Query in +X (toward infinite direction) should raise error
        direction = Matrix([1, 0, 0])
        with pytest.raises(ValueError, match="infinite in positive direction"):
            cylinder.minimal_boundary_in_direction(direction)
    
    def test_cylinder_semi_infinite_perpendicular_direction(self):
        """Test semi-infinite cylinder works for perpendicular directions."""
        axis = Matrix([0, 0, 1])
        radius = Rational(3)
        cylinder = create_cylinder(axis, radius, end_distance=10)  # Infinite in negative Z
        
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
        orientation = Matrix([0, 0, 1])
        
        prism1 = create_prism(size, orientation, start_distance=0, end_distance=5)
        prism2 = create_prism(size, orientation, start_distance=10, end_distance=15)
        
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
        orientation = Matrix([0, 0, 1])
        base = create_prism(size, orientation, start_distance=0, end_distance=10)
        
        # Subtract a smaller prism (doesn't affect the minimal boundary)
        subtract = create_prism(Matrix([2, 2]), orientation, start_distance=2, end_distance=8)
        
        diff = Difference(base, [subtract])
        
        # Minimal boundary should be same as base
        direction = Matrix([1, 0, 0])
        boundary = diff.minimal_boundary_in_direction(direction)
        
        assert boundary[0] == -5  # Half of base width


class TestCreateFunctions:
    """Test the create_prism and create_cylinder functions."""
    
    def test_create_prism_finite(self):
        """Test creating a finite prism."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, start_distance=0, end_distance=10)
        
        assert prism.size == size
        assert prism.orientation == orientation
        assert prism.start_distance == 0
        assert prism.end_distance == 10
    
    def test_create_prism_semi_infinite(self):
        """Test creating a semi-infinite prism."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation, end_distance=10)
        
        assert prism.start_distance is None
        assert prism.end_distance == 10
    
    def test_create_prism_infinite(self):
        """Test creating an infinite prism."""
        size = Matrix([4, 6])
        orientation = Matrix([0, 0, 1])
        prism = create_prism(size, orientation)
        
        assert prism.start_distance is None
        assert prism.end_distance is None
    
    def test_create_cylinder_finite(self):
        """Test creating a finite cylinder."""
        axis = Matrix([1, 0, 0])
        radius = Rational(5)
        cylinder = create_cylinder(axis, radius, start_distance=-5, end_distance=5)
        
        assert cylinder.axis_direction == axis
        assert cylinder.radius == radius
        assert cylinder.start_distance == -5
        assert cylinder.end_distance == 5
    
    def test_create_cylinder_infinite(self):
        """Test creating an infinite cylinder."""
        axis = Matrix([1, 0, 0])
        radius = Rational(5)
        cylinder = create_cylinder(axis, radius)
        
        assert cylinder.start_distance is None
        assert cylinder.end_distance is None

