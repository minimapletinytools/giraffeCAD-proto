"""
Tests for giraffe.py module.

This module contains tests for the GiraffeCAD timber framing CAD system.
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs, Float, Rational
from moothymoth import Orientation
from footprint import Footprint
from giraffe import *
from giraffe import _has_rational_components, _are_directions_perpendicular, _are_directions_parallel, _are_timbers_face_parallel, _are_timbers_face_orthogonal, _are_timbers_face_aligned, _project_point_on_timber_centerline, _calculate_mortise_position_from_tenon_intersection
from footprint import Footprint


class TestVectorHelpers:
    """Test vector helper functions."""
    
    def test_create_vector2d(self):
        """Test 2D vector creation."""
        v = create_vector2d(Rational(3, 2), Rational(5, 2))  # 1.5, 2.5 as exact rationals
        assert v.shape == (2, 1)
        assert v[0] == Rational(3, 2)
        assert v[1] == Rational(5, 2)
    
    def test_create_vector3d(self):
        """Test 3D vector creation."""
        v = create_vector3d(1, 2, 3)  # Use exact integers
        assert v.shape == (3, 1)
        assert v[0] == 1
        assert v[1] == 2
        assert v[2] == 3
    
    def test_normalize_vector(self):
        """Test vector normalization."""
        v = create_vector3d(3, 4, 0)  # Use integers for exact computation
        normalized = normalize_vector(v)
        
        # Should have magnitude 1
        magnitude = vector_magnitude(normalized)
        assert magnitude == 1
        
        # Should preserve direction ratios exactly
        assert normalized[0] == Rational(3, 5)  # 3/5
        assert normalized[1] == Rational(4, 5)  # 4/5
        assert normalized[2] == 0
    
    def test_normalize_zero_vector(self):
        """Test normalization of zero vector."""
        v = create_vector3d(0, 0, 0)  # Use exact integers
        normalized = normalize_vector(v)
        assert normalized == v  # Should return original zero vector
    
    def test_cross_product(self):
        """Test cross product calculation."""
        v1 = create_vector3d(1, 0, 0)  # Use exact integers
        v2 = create_vector3d(0, 1, 0)  # Use exact integers
        cross = cross_product(v1, v2)
        
        expected = create_vector3d(0, 0, 1)  # Use exact integers
        assert cross[0] == 0
        assert cross[1] == 0
        assert cross[2] == 1
    
    def test_vector_magnitude(self):
        """Test vector magnitude calculation."""
        v = create_vector3d(3, 4, 0)  # Use integers for exact computation
        magnitude = vector_magnitude(v)
        assert magnitude == 5


class TestTimber:
    """Test Timber class."""
    
    def test_timber_creation(self):
        """Test basic timber creation."""
        length = 3  # Use exact integer
        size = create_vector2d(Rational(1, 10), Rational(1, 10))  # 0.1 as exact rational
        position = create_vector3d(0, 0, 0)  # Use exact integers
        length_dir = create_vector3d(0, 0, 1)  # Use exact integers
        width_dir = create_vector3d(1, 0, 0)   # Use exact integers
        
        timber = Timber(length, size, position, length_dir, width_dir)
        
        assert timber.length == 3
        assert timber.size.shape == (2, 1)
        assert timber.bottom_position.shape == (3, 1)
        assert isinstance(timber.orientation, Orientation)
    
    def test_timber_orientation_computation(self):
        """Test that timber orientation is computed correctly."""
        # Create vertical timber facing east
        timber = Timber(
            length=2,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=create_vector3d(0, 0, 1),  # Up - exact integers
            width_direction=create_vector3d(1, 0, 0)     # East - exact integers
        )
        
        # Check that orientation matrix is reasonable
        matrix = timber.orientation.matrix
        assert matrix.shape == (3, 3)
        
        # Check that it's a valid rotation matrix (determinant = 1) - keep epsilon as float
        det_val = float(simplify(matrix.det()))
        assert abs(det_val - Rational(1)) < 1e-10
    
    def test_get_transform_matrix(self):
        """Test 4x4 transformation matrix generation."""
        timber = Timber(
            length=1,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(1, 2, 3),  # Use exact integers
            length_direction=create_vector3d(0, 0, 1), # Use exact integers
            width_direction=create_vector3d(1, 0, 0)    # Use exact integers
        )
        
        transform = timber.get_transform_matrix()
        assert transform.shape == (4, 4)
        
        # Check translation part (exact comparison since we used integers)
        assert transform[0, 3] == 1
        assert transform[1, 3] == 2
        assert transform[2, 3] == 3
        assert transform[3, 3] == 1
    
    def test_orientation_computed_from_directions(self):
        """Test that orientation is correctly computed from input face and length directions."""
        # Test with standard vertical timber facing east
        input_length_dir = create_vector3d(0, 0, 1)  # Up - exact integers
        input_width_dir = create_vector3d(1, 0, 0)    # East - exact integers
        
        timber = Timber(
            length=2,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            width_direction=input_width_dir
        )
        
        # Verify that the property getters return the correct normalized directions
        length_dir = timber.length_direction
        width_dir = timber.width_direction
        height_dir = timber.height_direction
        
        # Check that returned directions match input exactly (exact integers now)
        assert length_dir[0] == 0
        assert length_dir[1] == 0
        assert length_dir[2] == 1  # Exact integer from input
        
        assert width_dir[0] == 1    # Exact integer from input
        assert width_dir[1] == 0
        assert width_dir[2] == 0
        
        # Height direction should be cross product of length x face = Z x X = Y
        assert height_dir[0] == 0
        assert height_dir[1] == 1  # Exact integer from calculation
        assert height_dir[2] == 0
    
    def test_orientation_with_horizontal_timber(self):
        """Test orientation computation with a horizontal timber."""
        # Horizontal timber running north, facing up
        input_length_dir = create_vector3d(0, 1, 0)  # North - exact integers
        input_width_dir = create_vector3d(0, 0, 1)    # Up - exact integers
        
        timber = Timber(
            length=3,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            width_direction=input_width_dir
        )
        
        length_dir = timber.length_direction
        width_dir = timber.width_direction
        height_dir = timber.height_direction
        
        # Check length direction (north) - exact integers now
        assert length_dir[0] == 0
        assert length_dir[1] == 1
        assert length_dir[2] == 0
        
        # Check face direction (up) - exact integers now
        assert width_dir[0] == 0
        assert width_dir[1] == 0
        assert width_dir[2] == 1
        
        # Height direction should be Y x Z = +X (east) - exact integers now
        assert height_dir[0] == 1
        assert height_dir[1] == 0
        assert height_dir[2] == 0
    
    def test_orientation_directions_are_orthonormal(self):
        """Test that the computed direction vectors form an orthonormal basis."""
        timber = Timber(
            length=Rational(1),
            size=create_vector2d(Rational("0.1"), Rational("0.1")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(1), Rational(1), Rational(0)),  # Non-axis-aligned
            width_direction=create_vector3d(Rational(0), Rational(0), Rational(1))     # Up
        )
        
        length_dir = timber.length_direction
        width_dir = timber.width_direction
        height_dir = timber.height_direction
        
        # Check that each vector has unit length
        length_mag = float(sqrt(sum(x**2 for x in length_dir)))
        face_mag = float(sqrt(sum(x**2 for x in width_dir)))
        height_mag = float(sqrt(sum(x**2 for x in height_dir)))
        
        assert abs(length_mag - Rational(1)) < 1e-10
        assert abs(face_mag - Rational(1)) < 1e-10
        assert abs(height_mag - Rational(1)) < 1e-10
        
        # Check that vectors are orthogonal (dot products = 0)
        length_face_dot = float(sum(length_dir[i] * width_dir[i] for i in range(3)))
        length_height_dot = float(sum(length_dir[i] * height_dir[i] for i in range(3)))
        face_height_dot = float(sum(width_dir[i] * height_dir[i] for i in range(3)))
        
        assert abs(length_face_dot) < 1e-10
        assert abs(length_height_dot) < 1e-10
        assert abs(face_height_dot) < 1e-10
    
    def test_orientation_handles_non_normalized_inputs(self):
        """Test that orientation computation works with non-normalized input vectors."""
        # Use vectors that aren't unit length
        input_length_dir = create_vector3d(Rational(0), Rational(0), Rational(5))  # Up, but length 5
        input_width_dir = create_vector3d(Rational(3), Rational(0), Rational(0))    # East, but length 3
        
        timber = Timber(
            length=Rational(1),
            size=create_vector2d(Rational("0.1"), Rational("0.1")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=input_length_dir,
            width_direction=input_width_dir
        )
        
        # Despite non-normalized inputs, the output should be normalized
        length_dir = timber.length_direction
        width_dir = timber.width_direction
        
        # Check that directions are normalized (can be Rational(1) or Float(1))
        assert length_dir[0] == 0
        assert length_dir[1] == 0
        assert length_dir[2] == 1
        
        assert width_dir[0] == 1
        assert width_dir[1] == 0
        assert width_dir[2] == 0
    
    def test_get_centerline_position_from_bottom(self):
        """Test the get_centerline_position_from_bottom method."""
        timber = Timber(
            length=Rational(5),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(Rational(1), Rational(2), Rational(3)),
            length_direction=create_vector3d(Rational(0), Rational(1), Rational(0)),  # North
            width_direction=create_vector3d(Rational(0), Rational(0), Rational(1))     # Up
        )
        
        # Test at bottom position (position = 0)
        pos_at_bottom = timber.get_centerline_position_from_bottom(Rational(0))
        assert pos_at_bottom[0] == 1
        assert pos_at_bottom[1] == 2
        assert pos_at_bottom[2] == 3
        
        # Test at midpoint (position = 2.5)
        pos_at_middle = timber.get_centerline_position_from_bottom(Rational("2.5"))
        assert pos_at_middle[0] == 1
        assert pos_at_middle[1] == Rational("4.5")  # 2.0 + 2.5 * 1.0
        assert pos_at_middle[2] == 3
        
        # Test at top (position = 5.0)
        pos_at_top = timber.get_centerline_position_from_bottom(Rational(5))
        assert pos_at_top[0] == 1
        assert pos_at_top[1] == 7  # 2.0 + 5.0 * 1.0
        assert pos_at_top[2] == 3
        
        # Test with negative position (beyond bottom)
        pos_neg = timber.get_centerline_position_from_bottom(-Rational(1))
        assert pos_neg[0] == 1
        assert pos_neg[1] == 1  # 2.0 + (-1.0) * 1.0
        assert pos_neg[2] == 3
    
    def test_get_centerline_position_from_bottom(self):
        """Test get_centerline_position_from_bottom method."""
        timber = Timber(
            length=Rational(10),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(Rational(1), Rational(2), Rational(3)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Up
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))     # East
        )
        
        # Test position at bottom (0)
        pos_bottom = timber.get_centerline_position_from_bottom(Rational(0))
        assert pos_bottom[0] == 1
        assert pos_bottom[1] == 2
        assert pos_bottom[2] == 3
        
        # Test position at 3.0 from bottom
        pos_3 = timber.get_centerline_position_from_bottom(Rational(3))
        assert pos_3[0] == 1
        assert pos_3[1] == 2
        assert pos_3[2] == 6  # 3.0 + 3.0
        
        # Test position at top (10)
        pos_top = timber.get_centerline_position_from_bottom(Rational(10))
        assert pos_top[0] == 1
        assert pos_top[1] == 2
        assert pos_top[2] == 13  # 3.0 + 10.0
    
    def test_get_centerline_position_from_top(self):
        """Test get_centerline_position_from_top method."""
        timber = Timber(
            length=Rational(10),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(Rational(1), Rational(2), Rational(3)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Up
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))     # East
        )
        
        # Test position at top (0 from top = 10 from bottom)
        pos_top = timber.get_centerline_position_from_top(Rational(0))
        assert pos_top[0] == 1
        assert pos_top[1] == 2
        assert pos_top[2] == 13  # 3.0 + 10.0
        
        # Test position at 3.0 from top (= 7.0 from bottom)
        pos_3 = timber.get_centerline_position_from_top(Rational(3))
        assert pos_3[0] == 1
        assert pos_3[1] == 2
        assert pos_3[2] == 10  # 3.0 + 7.0
        
        # Test at bottom (10 from top = 0 from bottom)
        pos_bottom = timber.get_centerline_position_from_top(Rational(10))
        assert pos_bottom[0] == 1
        assert pos_bottom[1] == 2
        assert pos_bottom[2] == 3  # 3.0 + 0.0


class TestTimberCreation:
    """Test timber creation functions."""
    
    def test_create_timber(self):
        """Test basic create_timber function."""
        position = create_vector3d(Rational(1), Rational(1), Rational(0))
        size = create_vector2d(Rational("0.2"), Rational("0.3"))
        length_dir = create_vector3d(Rational(0), Rational(0), Rational(1))
        width_dir = create_vector3d(Rational(1), Rational(0), Rational(0))
        
        timber = create_timber(position, Rational("2.5"), size, length_dir, width_dir)
        
        assert timber.length == Rational("2.5")
        assert timber.bottom_position[0] == Rational(1)
        assert timber.bottom_position[1] == Rational(1)
        assert timber.bottom_position[2] == Rational(0)
    
    def test_create_axis_aligned_timber(self):
        """Test axis-aligned timber creation with explicit width_direction."""
        position = create_vector3d(0, 0, 0)  # Use exact integers
        size = create_vector2d(Rational(1, 10), Rational(1, 10))  # 0.1 as exact rational
        
        timber = create_axis_aligned_timber(
            position, 3, size,  # Use exact integer for length
            TimberFace.TOP,    # Length direction (up)
            TimberFace.RIGHT   # Width direction (east)
        )
        
        assert timber.length == 3  # Exact integer
        # Check that directions are correct
        assert timber.length_direction[2] == 1  # Up (exact integer)
        assert timber.width_direction[0] == 1    # East (exact integer)
    
    def test_create_axis_aligned_timber_default_width(self):
        """Test axis-aligned timber creation with default width_direction."""
        position = create_vector3d(0, 0, 0)
        size = create_vector2d(Rational(1, 10), Rational(1, 10))
        
        # Test with length in +Z direction (default width should be +X)
        timber1 = create_axis_aligned_timber(
            position, 3, size,
            TimberFace.TOP  # Length in +Z
            # width_direction not provided - should default to RIGHT (+X)
        )
        
        assert timber1.length_direction[2] == 1  # Length in +Z
        assert timber1.width_direction[0] == 1    # Width in +X (default)
        
        # Test with length in +Y direction (default width should be +X)
        timber2 = create_axis_aligned_timber(
            position, 3, size,
            TimberFace.FORWARD  # Length in +Y
            # width_direction not provided - should default to RIGHT (+X)
        )
        
        assert timber2.length_direction[1] == 1  # Length in +Y
        assert timber2.width_direction[0] == 1    # Width in +X (default)
        
        # Test with length in +X direction (default width should be +Z)
        timber3 = create_axis_aligned_timber(
            position, 3, size,
            TimberFace.RIGHT  # Length in +X
            # width_direction not provided - should default to TOP (+Z)
        )
        
        assert timber3.length_direction[0] == 1  # Length in +X
        assert timber3.width_direction[2] == 1    # Width in +Z (special case)
    
    def test_create_axis_aligned_timber_explicit_overrides_default(self):
        """Test that explicit width_direction overrides the default."""
        position = create_vector3d(0, 0, 0)
        size = create_vector2d(Rational(1, 10), Rational(1, 10))
        
        # Even with length in +X, we can explicitly set width to +Y
        timber = create_axis_aligned_timber(
            position, 3, size,
            TimberFace.RIGHT,    # Length in +X
            TimberFace.FORWARD   # Explicit width in +Y (not the default +Z)
        )
        
        assert timber.length_direction[0] == 1  # Length in +X
        assert timber.width_direction[1] == 1    # Width in +Y (explicit)
    
    def test_create_vertical_timber_on_footprint_corner(self):
        """Test vertical timber creation on footprint corner with INSIDE, OUTSIDE, and CENTER."""
        # Create a square footprint with exact integer corners
        corners = [
            create_vector2d(0, 0),  # Corner 0: Bottom-left
            create_vector2d(3, 0),  # Corner 1: Bottom-right  
            create_vector2d(3, 4),  # Corner 2: Top-right
            create_vector2d(0, 4)   # Corner 3: Top-left
        ]
        footprint = Footprint(corners)
        
        # Post size: 9cm x 9cm (exact rational)
        size = create_vector2d(Rational(9, 100), Rational(9, 100))
        post_height = Rational(5, 2)  # 2.5 meters
        
        # Test INSIDE positioning
        # Vertex of bottom face is at corner, post extends inside
        timber_inside = create_vertical_timber_on_footprint_corner(
            footprint, 0, post_height, FootprintLocation.INSIDE, size
        )
        
        assert timber_inside.length == Rational(5, 2)
        # For INSIDE, vertex is at corner (0, 0) - exact!
        assert timber_inside.bottom_position[0] == 0
        assert timber_inside.bottom_position[1] == 0
        assert timber_inside.bottom_position[2] == 0
        # Should be vertical
        assert timber_inside.length_direction[2] == 1
        # Face direction should align with outgoing boundary side (+X)
        # For axis-aligned case, direction is exactly 1
        assert timber_inside.width_direction[0] == 1
        assert timber_inside.width_direction[1] == 0
        assert timber_inside.width_direction[2] == 0
        
        # Test CENTER positioning  
        # Center of bottom face is at corner
        timber_center = create_vertical_timber_on_footprint_corner(
            footprint, 0, post_height, FootprintLocation.CENTER, size
        )
        
        assert timber_center.length == Rational(5, 2)
        # For CENTER, offset by half dimensions: -9/200 in both X and Y - exact!
        assert timber_center.bottom_position[0] == Rational(-9, 200)
        assert timber_center.bottom_position[1] == Rational(-9, 200)
        assert timber_center.bottom_position[2] == 0
        # Should be vertical
        assert timber_center.length_direction[2] == 1
        # Face direction should align with outgoing boundary side (+X)
        # For axis-aligned case, direction is exactly 1
        assert timber_center.width_direction[0] == 1
        assert timber_center.width_direction[1] == 0
        
        # Test OUTSIDE positioning
        # Opposite vertex is at corner, post extends outside
        timber_outside = create_vertical_timber_on_footprint_corner(
            footprint, 0, post_height, FootprintLocation.OUTSIDE, size
        )
        
        assert timber_outside.length == Rational(5, 2)
        # For OUTSIDE, offset by full dimensions: -9/100 in both X and Y - exact!
        assert timber_outside.bottom_position[0] == Rational(-9, 100)
        assert timber_outside.bottom_position[1] == Rational(-9, 100)
        assert timber_outside.bottom_position[2] == 0
        # Should be vertical
        assert timber_outside.length_direction[2] == 1
        # Face direction should align with outgoing boundary side (+X)
        # For axis-aligned case, direction is exactly 1
        assert timber_outside.width_direction[0] == 1
        assert timber_outside.width_direction[1] == 0
    
    def test_create_vertical_timber_on_footprint_side(self):
        """Test vertical timber creation on footprint side with INSIDE, OUTSIDE, and CENTER."""
        # Create a square footprint with exact integer corners
        corners = [
            create_vector2d(0, 0),  # Corner 0: Bottom-left
            create_vector2d(4, 0),  # Corner 1: Bottom-right
            create_vector2d(4, 3),  # Corner 2: Top-right
            create_vector2d(0, 3)   # Corner 3: Top-left
        ]
        footprint = Footprint(corners)
        
        # Post size: 10cm x 10cm (exact rational)
        size = create_vector2d(Rational(1, 10), Rational(1, 10))
        post_height = Rational(3, 1)  # 3 meters
        
        # Place post 1 meter along the bottom side (from corner 0 to corner 1)
        distance_along_side = Rational(1, 1)
        
        # Test CENTER positioning
        # Center of bottom face is on the point (1, 0)
        timber_center = create_vertical_timber_on_footprint_side(
            footprint, 0, distance_along_side, post_height, FootprintLocation.CENTER, size
        )
        
        assert timber_center.length == Rational(3, 1)
        # For CENTER, center is exactly at (1, 0) - exact!
        assert timber_center.bottom_position[0] == 1
        assert timber_center.bottom_position[1] == 0
        assert timber_center.bottom_position[2] == 0
        # Should be vertical
        assert timber_center.length_direction[2] == 1
        # Face direction should be parallel to the side (along +X)
        assert timber_center.width_direction[0] == 1
        assert timber_center.width_direction[1] == 0
        
        # Test INSIDE positioning
        # One edge center is at the point, post extends inside (toward +Y)
        timber_inside = create_vertical_timber_on_footprint_side(
            footprint, 0, distance_along_side, post_height, FootprintLocation.INSIDE, size
        )
        
        assert timber_inside.length == Rational(3, 1)
        # For INSIDE, offset by half depth inward (toward +Y)
        assert timber_inside.bottom_position[0] == 1
        assert timber_inside.bottom_position[1] == size[1] / 2
        assert timber_inside.bottom_position[2] == 0
        # Should be vertical
        assert timber_inside.length_direction[2] == 1
        # Face direction parallel to side
        assert timber_inside.width_direction[0] == 1
        assert timber_inside.width_direction[1] == 0
        
        # Test OUTSIDE positioning
        # One edge center is at the point, post extends outside (toward -Y)
        timber_outside = create_vertical_timber_on_footprint_side(
            footprint, 0, distance_along_side, post_height, FootprintLocation.OUTSIDE, size
        )
        
        assert timber_outside.length == Rational(3, 1)
        # For OUTSIDE, offset by half depth outward (toward -Y)
        assert timber_outside.bottom_position[0] == 1
        assert timber_outside.bottom_position[1] == -size[1] / 2
        assert timber_outside.bottom_position[2] == 0
        # Should be vertical
        assert timber_outside.length_direction[2] == 1
        # Face direction parallel to side
        assert timber_outside.width_direction[0] == 1
        assert timber_outside.width_direction[1] == 0
    
    def test_create_horizontal_timber_on_footprint(self):
        """Test horizontal timber creation on footprint."""
        corners = [
            create_vector2d(Rational(0), Rational(0)),
            create_vector2d(Rational(3), Rational(0)),
            create_vector2d(Rational(3), Rational(4)),
            create_vector2d(Rational(0), Rational(4))
        ]
        footprint = Footprint(corners)
        
        # Default size for test
        size = create_vector2d(Rational(3, 10), Rational(3, 10))
        
        timber = create_horizontal_timber_on_footprint(
            footprint, 0, FootprintLocation.INSIDE, size, length=Rational(3)
        )
        
        assert timber.length == Rational(3)
        # Should be horizontal in X direction
        assert timber.length_direction[0] == 1
        assert timber.length_direction[2] == 0
    
    def test_create_horizontal_timber_on_footprint_location_types(self):
        """Test horizontal timber positioning with INSIDE, OUTSIDE, and CENTER location types."""
        # Create a square footprint with exact integer coordinates
        corners = [
            create_vector2d(0, 0),  # Bottom-left
            create_vector2d(2, 0),  # Bottom-right
            create_vector2d(2, 2),  # Top-right
            create_vector2d(0, 2)   # Top-left
        ]
        footprint = Footprint(corners)
        
        # Define timber size: width (vertical) x height (perpendicular to boundary)
        # For a horizontal timber: size[0] = width (vertical), size[1] = height (horizontal perpendicular)
        timber_width = Rational(3, 10)   # Vertical dimension (face direction = up)
        timber_height = Rational(2, 10)  # Perpendicular to boundary in XY plane
        size = create_vector2d(timber_width, timber_height)
        
        # Test bottom boundary side (from corner 0 to corner 1)
        # This side has inward normal pointing up: (0, 1, 0)
        
        # Test INSIDE positioning
        timber_inside = create_horizontal_timber_on_footprint(
            footprint, 0, FootprintLocation.INSIDE, size, length=Rational(2)
        )
        # Timber should extend inward (in +Y direction)
        # Bottom position Y should be half timber height (perpendicular dimension) inside the footprint
        # Note: get_inward_normal returns floats, so the result is Float
        assert timber_inside.bottom_position[1] == Float(timber_height / 2)
        assert timber_inside.bottom_position[0] == 0  # X unchanged
        assert timber_inside.bottom_position[2] == 0  # Z at ground
        
        # Test OUTSIDE positioning
        timber_outside = create_horizontal_timber_on_footprint(
            footprint, 0, FootprintLocation.OUTSIDE, size, length=Rational(2)
        )
        # Timber should extend outward (in -Y direction)
        # Bottom position Y should be half timber height (perpendicular dimension) outside the footprint
        # Note: get_inward_normal returns floats, so the result is Float
        assert timber_outside.bottom_position[1] == Float(-timber_height / 2)
        assert timber_outside.bottom_position[0] == 0  # X unchanged
        assert timber_outside.bottom_position[2] == 0  # Z at ground
        
        # Test CENTER positioning
        timber_center = create_horizontal_timber_on_footprint(
            footprint, 0, FootprintLocation.CENTER, size, length=Rational(2)
        )
        # Centerline should be on the boundary side
        assert timber_center.bottom_position[1] == Rational(0)  # Y on boundary
        assert timber_center.bottom_position[0] == Rational(0)  # X unchanged
        assert timber_center.bottom_position[2] == Rational(0)  # Z at ground
        
        # Verify all timbers have correct length direction (along +X for bottom side)
        assert timber_inside.length_direction[0] == Rational(1)
        assert timber_inside.length_direction[1] == Rational(0)
        assert timber_inside.length_direction[2] == Rational(0)
        
        assert timber_outside.length_direction[0] == Rational(1)
        assert timber_outside.length_direction[1] == Rational(0)
        assert timber_outside.length_direction[2] == Rational(0)
        
        assert timber_center.length_direction[0] == Rational(1)
        assert timber_center.length_direction[1] == Rational(0)
        assert timber_center.length_direction[2] == Rational(0)
        
        # Test right boundary side (from corner 1 to corner 2)
        # This side has inward normal pointing left: (-1, 0, 0)
        
        timber_inside_right = create_horizontal_timber_on_footprint(
            footprint, 1, FootprintLocation.INSIDE, size, length=Rational(2)
        )
        # Timber should extend inward (in -X direction)
        # Use timber_height (size[1]) as it's the dimension perpendicular to boundary
        assert timber_inside_right.bottom_position[0] == Float(Rational(2) - timber_height / 2)
        assert timber_inside_right.bottom_position[1] == Rational(0)  # Y unchanged
        
        timber_outside_right = create_horizontal_timber_on_footprint(
            footprint, 1, FootprintLocation.OUTSIDE, size, length=Rational(2)
        )
        # Timber should extend outward (in +X direction)
        # Use timber_height (size[1]) as it's the dimension perpendicular to boundary
        assert timber_outside_right.bottom_position[0] == Float(Rational(2) + timber_height / 2)
        assert timber_outside_right.bottom_position[1] == Rational(0)  # Y unchanged
        
        timber_center_right = create_horizontal_timber_on_footprint(
            footprint, 1, FootprintLocation.CENTER, size, length=Rational(2)
        )
        # Centerline should be on the boundary side
        assert timber_center_right.bottom_position[0] == Rational(2)  # X on boundary
        assert timber_center_right.bottom_position[1] == Rational(0)  # Y unchanged
    
    def test_extend_timber(self):
        """Test timber extension creation with correct length calculation."""
        # Create a vertical timber from Z=0 to Z=10
        original_timber = Timber(
            length=Rational(10),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Vertical (up)
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))     # East
        )
        
        # Extend from top with 2 units of overlap and 5 units of extension
        # overlap_length = 2.0 (overlaps with last 2 units of original timber)
        # extend_length = 5.0 (extends 5 units beyond the end)
        extended = extend_timber(
            original_timber, 
            TimberReferenceEnd.TOP, 
            overlap_length=Rational(2), 
            extend_length=Rational(5)
        )
        
        # Verify length: original_length + extend_length + overlap_length
        # = 10.0 + 5.0 + 2.0 = 17.0
        assert extended.length == Rational(17), f"Expected length Rational(17), got {extended.length}"
        
        # Verify bottom position moved up by (original_length - overlap_length)
        # = 0.0 + (10.0 - 2.0) = 8.0
        assert extended.bottom_position[2] == Rational(8), \
            f"Expected bottom Z at Rational(8), got {float(extended.bottom_position[2])}"


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_timber_face_get_direction(self):
        """Test TimberFace.get_direction() method."""
        # Test all faces
        top = TimberFace.TOP.get_direction()
        assert top[2] == Rational(1)
        
        bottom = TimberFace.BOTTOM.get_direction()
        assert bottom[2] == -Rational(1)
        
        right = TimberFace.RIGHT.get_direction()
        assert right[0] == Rational(1)
        
        left = TimberFace.LEFT.get_direction()
        assert left[0] == -Rational(1)
        
        forward = TimberFace.FORWARD.get_direction()
        assert forward[1] == Rational(1)
        
        back = TimberFace.BACK.get_direction()
        assert back[1] == -Rational(1)


class TestJoinTimbers:
    """Test timber joining functions."""
    
    def test_join_timbers_basic(self):
        """Test basic timber joining."""
        timber1 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Vertical
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        timber2 = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(2), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Vertical
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational("1.5"),  # Midpoint of timber1
            stickout=Stickout(Rational("0.1"), Rational("0.1")),  # Symmetric stickout
            location_on_timber2=Rational(1),   # Explicit position on timber2
            lateral_offset=Rational(0)
        )
        
        assert isinstance(joining_timber, Timber)
        # Length direction should be from pos1=[0,0,1.5] to pos2=[2,0,1.0], so direction=[2,0,-0.5]
        # Normalized: [0.970, 0, -0.243] approximately
        length_dir = joining_timber.length_direction
        assert abs(float(length_dir[0]) - Rational("0.970")) < Rational("0.1")  # X component ~0.97
        assert abs(float(length_dir[1])) < Rational("0.1")          # Y component ~0
        assert abs(float(length_dir[2]) + Rational("0.243")) < Rational("0.1")  # Z component ~-0.24
        
        # Face direction should be orthogonal to length direction
        # Default behavior: projects timber1's length direction [0,0,1] onto perpendicular plane
        # Result should be perpendicular to joining direction
        width_dir = joining_timber.width_direction
        dot_product = length_dir.dot(width_dir)
        assert simplify(dot_product) == 0 or abs(float(dot_product)) < 1e-6, \
            "Face direction should be perpendicular to length direction"
        
        # Verify the joining timber is positioned correctly
        # pos1 = [0, 0, 1.5] (location 1.5 on timber1), pos2 = [2, 0, 1.0] (location 1.0 on timber2)
        # center would be [1, 0, 1.25], but bottom_position is at the start of the timber
        # The timber should span from one connection point to the other with stickout
        
        # Check that the timber actually spans the connection points correctly
        # The timber should start before pos1 and end after pos2 (or vice versa)
        timber_start = joining_timber.bottom_position
        timber_end = joining_timber.get_centerline_position_from_bottom(joining_timber.length)
        
        # Verify timber spans the connection region
        assert joining_timber.length > Rational(2)  # Should be longer than just the span between points

    def test_join_timbers_with_non_perpendicular_orientation_vector(self):
        """Test that join_timbers automatically projects non-perpendicular orientation_width_vector."""
        # Create two vertical posts
        timber1 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Vertical (Z-up)
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(2), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Vertical (Z-up)
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        # Create a horizontal beam connecting them, specifying "face up" (0,0,1)
        # The joining direction is horizontal [1,0,0], so [0,0,1] is NOT perpendicular
        # The function should automatically project it onto the perpendicular plane
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational("1.5"),  # Midpoint of timber1
            stickout=Stickout(Rational("0.1"), Rational("0.1")),  # Symmetric stickout
            location_on_timber2=Rational("1.5"),   # Same height on timber2
            orientation_width_vector=create_vector3d(0, 0, 1)  # "Face up" - not perpendicular to joining direction
        )
        
        # Verify the timber was created successfully (no assertion error)
        assert isinstance(joining_timber, Timber)
        
        # The joining direction should be horizontal [1,0,0] (normalized)
        length_dir = joining_timber.length_direction
        assert abs(float(length_dir[0]) - Rational(1)) < 1e-6, "Length direction should be [1,0,0]"
        assert abs(float(length_dir[1])) < 1e-6
        assert abs(float(length_dir[2])) < 1e-6
        
        # The width direction should be perpendicular to the joining direction
        # Since we specified [0,0,1] and joining is [1,0,0], projection should give [0,0,1]
        width_dir = joining_timber.width_direction
        dot_product = length_dir.dot(width_dir)
        assert abs(float(dot_product)) < 1e-6, "Width direction should be perpendicular to length direction"
        
        # The projected width direction should be close to [0,0,1] (our desired "face up")
        assert abs(float(width_dir[0])) < 1e-6, "Width X component should be ~0"
        assert abs(float(width_dir[1])) < 1e-6, "Width Y component should be ~0"
        assert abs(abs(float(width_dir[2])) - Rational(1)) < 1e-6, "Width Z component should be ~±1"

    def test_join_timbers_with_angled_orientation_vector(self):
        """Test projection of angled orientation_width_vector onto perpendicular plane."""
        # Create two vertical posts
        timber1 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Vertical
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(2), Rational(1), Rational(0)),  # Offset in both X and Y
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),  # Vertical
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        # Provide an orientation vector at an angle: [1, 1, 1]
        # This should be projected onto the plane perpendicular to the joining direction
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational("1.5"),
            stickout=Stickout(Rational(0), Rational(0)),
            location_on_timber2=Rational("1.5"),
            orientation_width_vector=create_vector3d(1, 1, 1)  # Angled vector
        )
        
        # Verify the timber was created successfully
        assert isinstance(joining_timber, Timber)
        
        # Verify width direction is perpendicular to length direction
        length_dir = joining_timber.length_direction
        width_dir = joining_timber.width_direction
        dot_product = length_dir.dot(width_dir)
        assert abs(float(dot_product)) < 1e-6, "Width direction should be perpendicular to length direction"

    # helper function to create 2 parallel timbers 
    def make_parallel_timbers(self):
        timber1 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(1), Rational(0), Rational(0)),  # Horizontal in X
            width_direction=create_vector3d(Rational(0), Rational(0), Rational(1))     # Up
        )
        
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(Rational(0), Rational(2), Rational(0)),
            length_direction=create_vector3d(Rational(1), Rational(0), Rational(0)),  # Parallel to timber1
            width_direction=create_vector3d(Rational(0), Rational(0), Rational(1))
        )

        return timber1, timber2
    
    def test_join_perpendicular_on_face_parallel_timbers_position_is_correct(self):
        """Test perpendicular joining of face-aligned timbers."""
        timber1, timber2 = self.make_parallel_timbers()
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )

        joining_timber2 = join_perpendicular_on_face_parallel_timbers(
            timber1, timber2,
            location_on_timber1=Rational("1.5"),
            stickout=Stickout(0, 0),  # No stickout
            offset_from_timber1=offset,
            size=create_vector2d(Rational("0.15"), Rational("0.15")),
            orientation_face_on_timber1=TimberFace.TOP
        )
   
        assert joining_timber2.bottom_position == timber1.get_centerline_position_from_bottom(Rational("1.5"))
        print(joining_timber2.orientation)
        
        
    def test_join_perpendicular_on_face_parallel_timbers_length_is_correct(self):
        """Test perpendicular joining of face-aligned timbers."""
        timber1, timber2 = self.make_parallel_timbers()
        
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        joining_timber2 = join_perpendicular_on_face_parallel_timbers(
            timber1, timber2,
            location_on_timber1=Rational("1.5"),
            stickout=Stickout(Rational("1.2"), Rational("1.2")),  # Symmetric stickout
            offset_from_timber1=offset,
            size=create_vector2d(Rational("0.15"), Rational("0.15")),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        assert isinstance(joining_timber2, Timber)
        # Length should be centerline distance (2.0) + stickout1 (1.2) + stickout2 (1.2) = 4.4
        assert abs(joining_timber2.length - Rational("4.4")) < 1e-10
    
    def test_join_perpendicular_on_face_parallel_timbers_assertion(self):
        """Test that join_perpendicular_on_face_parallel_timbers asserts when timbers are not face-aligned."""
        import pytest
        
        # Create two timbers that are NOT face-aligned
        # Timber1: vertical, facing east
        timber1 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.15"), Rational("0.15")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(0, 0, 1),  # Vertical
            width_direction=create_vector3d(1, 0, 0)     # East
        )
        
        # Timber2: 3D rotation not aligned with timber1's coordinate grid
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.15"), Rational("0.15")),
            bottom_position=create_vector3d(Rational(2), Rational(2), Rational(0)),
            length_direction=create_vector3d(1, 1, 1),  # 3D diagonal (will be normalized)
            width_direction=create_vector3d(1, -1, 0)    # Perpendicular in 3D (will be normalized)
        )
        
        # Verify they are NOT face-aligned
        assert not _are_timbers_face_aligned(timber1, timber2), "Timbers should not be face-aligned"
        
        # Now try to join them - should raise AssertionError
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        with pytest.raises(AssertionError, match="must be face-aligned"):
            join_perpendicular_on_face_parallel_timbers(
                timber1, timber2,
                location_on_timber1=Rational("1.5"),
                stickout=Stickout(Rational(0), Rational(0)),
                offset_from_timber1=offset,
                size=create_vector2d(Rational("0.15"), Rational("0.15")),
                orientation_face_on_timber1=TimberFace.TOP
            )
    
    def test_join_perpendicular_on_face_parallel_timbers_auto_size(self):
        """Test automatic size determination in join_perpendicular_on_face_parallel_timbers."""
        # Constants using exact rationals
        # 1 inch = 0.0254 m = 254/10000 m = 127/5000 m
        INCH_TO_METERS = Rational(127, 5000)
        # 1 foot = 0.3048 m = 3048/10000 m = 381/1250 m
        FEET_TO_METERS = Rational(381, 1250)
        
        # Create two vertical posts with 1" x 2" cross-section
        # size[0] = width (1 inch), size[1] = height (2 inches)
        post1 = Timber(
            length=3,  # 3 meters tall (exact integer)
            size=create_vector2d(1 * INCH_TO_METERS, 2 * INCH_TO_METERS),  # 1" x 2"
            bottom_position=create_vector3d(0, 0, 0),  # Exact integers
            length_direction=create_vector3d(0, 0, 1),  # Vertical (Z+)
            width_direction=create_vector3d(1, 0, 0)     # East (X+)
        )
        
        # Post2 is 5 feet away in the X direction
        post2 = Timber(
            length=3,  # Exact integer
            size=create_vector2d(1 * INCH_TO_METERS, 2 * INCH_TO_METERS),  # 1" x 2"
            bottom_position=create_vector3d(5 * FEET_TO_METERS, 0, 0),  # 5 feet in X (exact rational)
            length_direction=create_vector3d(0, 0, 1),  # Vertical (Z+)
            width_direction=create_vector3d(1, 0, 0)     # East (X+)
        )
        
        # Join perpendicular with size=None (auto-determine)
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        beam = join_perpendicular_on_face_parallel_timbers(
            timber1=post1,
            timber2=post2,
            location_on_timber1=Rational(3, 2),  # 1.5m up the post (exact rational)
            stickout=Stickout.nostickout(),
            offset_from_timber1=offset,
            size=None,  # Auto-determine size
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        # The beam runs horizontally (X direction) connecting the two vertical posts
        # The beam should match the post's cross-section dimensions
        # Since the beam is perpendicular to the posts, it should use post1's size
        # The beam's face direction aligns with the TOP face of post1 (which is Z+)
        # So the beam should have the same cross-section as the post
        assert beam.size[0] == post1.size[0], f"Expected beam width {post1.size[0]}, got {beam.size[0]}"
        assert beam.size[1] == post1.size[1], f"Expected beam height {post1.size[1]}, got {beam.size[1]}"
        
        # Verify the beam's orientation
        # The beam runs in X direction (from post1 to post2)
        assert beam.length_direction[0] == 1, "Beam should run in X+ direction"
        assert beam.length_direction[1] == 0, "Beam Y component should be 0"
        assert beam.length_direction[2] == 0, "Beam Z component should be 0"
        
        # The beam's face direction should align with TOP of post1 (Z+)
        # Since orientation_face_on_timber1=TOP, the beam's right face aligns with the top face of post1
        assert beam.width_direction[0] == 0, "Beam face X component should be 0"
        assert beam.width_direction[1] == 0, "Beam face Y component should be 0"
        assert beam.width_direction[2] == 1, "Beam should face up (Z+)"
        
        # Verify the beam connects the posts at the correct height
        expected_bottom_z = Rational(3, 2)  # At 1.5m up post1 (exact rational)
        assert beam.bottom_position[2] == expected_bottom_z, \
            f"Beam should be at Z={expected_bottom_z}, got Z={beam.bottom_position[2]}"

    def test_join_timbers_creates_orthogonal_rotation_matrix(self):
        """Test that join_timbers creates valid orthogonal orientation matrices."""
        # Create two non-parallel timbers to ensure non-trivial orientation
        # Use exact integer/rational inputs for exact SymPy results
        timber1 = Timber(
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            bottom_position=create_vector3d(Rational(-1, 2), 0, 0),  # Exact rationals
            length_direction=create_vector3d(0, 0, 1),  # Integers (vertical)
            width_direction=create_vector3d(1, 0, 0)     # Integers
        )
        
        timber2 = Timber(
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            bottom_position=create_vector3d(Rational(1, 2), 0, 0),   # Exact rationals
            length_direction=create_vector3d(0, 1, 0),  # Integers (horizontal north)
            width_direction=create_vector3d(0, 0, 1)     # Integers
        )
        
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational(1, 2),     # Exact rational
            stickout=Stickout(Rational(1, 10), Rational(1, 10)),  # Exact symmetric stickout
            location_on_timber2=Rational(1, 2),     # Exact rational
            lateral_offset=0                  # Integer
        )
        
        # Get the orientation matrix
        orientation_matrix = joining_timber.orientation.matrix
        
        # Check that it's orthogonal: M * M^T = I (exact SymPy comparison)
        product = orientation_matrix * orientation_matrix.T
        identity = Matrix.eye(3)
        
        # Check that M * M^T = I exactly
        assert simplify(product - identity) == Matrix.zeros(3, 3), "M * M^T should equal identity matrix"
        
        # Check determinant is exactly 1 (proper rotation, not reflection)
        det = orientation_matrix.det()
        assert simplify(det - 1) == 0, "Determinant should be exactly 1"
        
        # Verify direction vectors are unit length (exact SymPy comparison)
        length_dir = joining_timber.length_direction
        width_dir = joining_timber.width_direction  
        height_dir = joining_timber.height_direction
        
        assert simplify(length_dir.norm() - 1) == 0, "Length direction should be unit vector"
        assert simplify(width_dir.norm() - 1) == 0, "Face direction should be unit vector"
        assert simplify(height_dir.norm() - 1) == 0, "Height direction should be unit vector"
        
        # Verify directions are orthogonal to each other (exact SymPy comparison)
        assert simplify(length_dir.dot(width_dir)) == 0, "Length and face directions should be orthogonal"
        assert simplify(length_dir.dot(height_dir)) == 0, "Length and height directions should be orthogonal"
        assert simplify(width_dir.dot(height_dir)) == 0, "Face and height directions should be orthogonal"

    def test_create_timber_creates_orthogonal_matrix(self):
        """Test that create_timber creates valid orthogonal orientation matrices."""
        # Test with arbitrary (but orthogonal) input directions using exact inputs
        length_dir = create_vector3d(1, 1, 0)  # Will be normalized (integers)
        width_dir = create_vector3d(0, 0, 1)    # Up direction (integers)
        
        timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            length_direction=length_dir,
            width_direction=width_dir
        )
        
        # Get the orientation matrix
        orientation_matrix = timber.orientation.matrix
        
        # Check that it's orthogonal: M * M^T = I (exact SymPy comparison)
        product = orientation_matrix * orientation_matrix.T
        identity = Matrix.eye(3)
        
        # Check that M * M^T = I exactly
        assert simplify(product - identity) == Matrix.zeros(3, 3), "M * M^T should equal identity matrix"
        
        # Check determinant is exactly 1
        det = orientation_matrix.det()
        assert simplify(det - 1) == 0, "Determinant should be exactly 1"

    def test_orthogonal_matrix_with_non_orthogonal_input(self):
        """Test that orthogonal matrix is created even with non-orthogonal input directions."""
        # Use non-orthogonal input directions to test the orthogonalization process
        # Using exact rational numbers for exact results
        length_dir = create_vector3d(2, 0, 1)         # Not orthogonal to width_dir (integers)
        width_dir = create_vector3d(0, 1, 2)           # Not orthogonal to length_dir (integers)
        
        timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            length_direction=length_dir,
            width_direction=width_dir
        )
        
        # The resulting orientation should still be orthogonal
        orientation_matrix = timber.orientation.matrix
        
        # Check orthogonality using exact SymPy comparison
        product = orientation_matrix * orientation_matrix.T
        identity = Matrix.eye(3)
        
        # Check that M * M^T = I exactly
        assert simplify(product - identity) == Matrix.zeros(3, 3), "M * M^T should equal identity matrix"
        
        # Check determinant is exactly 1
        det = orientation_matrix.det()
        assert simplify(det - 1) == 0, "Determinant should be exactly 1"

    def test_join_perpendicular_face_aligned_timbers_comprehensive(self):
        """Test comprehensive face-aligned timber joining with random configurations."""
        import random
        from sympy import Rational
        
        # Set a fixed seed for reproducible tests
        random.seed(42)
        
        # Create several horizontal timbers at the same Z level (face-aligned on their top faces)
        base_z = Rational(1, 10)  # 0.1m height
        timber_size = create_vector2d(Rational(1, 10), Rational(1, 10))  # 10cm x 10cm
        
        base_timbers = []
        positions = [
            create_vector3d(-1, 0, base_z),    # Left
            create_vector3d(0, 0, base_z),     # Center  
            create_vector3d(1, 0, base_z),     # Right
            create_vector3d(0, -1, base_z),    # Back
            create_vector3d(0, 1, base_z),     # Front
        ]
        
        # Create base timbers - all horizontal and face-aligned
        for i, pos in enumerate(positions):
            timber = Timber(
                length=2,  # 2m long
                size=timber_size,
                bottom_position=pos,
                length_direction=create_vector3d(1, 0, 0),  # All point east
                width_direction=create_vector3d(0, 1, 0)     # All face north
            )
            timber.name = f"Base_Timber_{i}"
            base_timbers.append(timber)
        
        # Create a beam at a higher level
        beam_z = Rational(3, 2)  # 1.5m height
        beam = Timber(
            length=4,  # 4m long beam
            size=create_vector2d(Rational(15, 100), Rational(15, 100)),  # 15cm x 15cm
            bottom_position=create_vector3d(-2, 0, beam_z),
            length_direction=create_vector3d(1, 0, 0),  # East direction
            width_direction=create_vector3d(0, 1, 0)     # North facing
        )
        beam.name = "Top_Beam"
        
        # Verify that base timbers are face-aligned (same top face Z coordinate)
        for timber in base_timbers:
            top_face_z = timber.bottom_position[2] + timber.height_direction[2] * timber.size[1]
            expected_top_z = base_z + timber_size[1]  # base_z + height
            assert simplify(top_face_z - expected_top_z) == 0, f"Base timber {timber.name} not at expected height"
        
        # Test joining multiple base timbers to the beam
        joining_timbers = []
        locations_used = []  # Store for later verification
        
        # Use deterministic rational positions instead of random floats
        rational_positions = [
            Rational(1, 4),    # 0.25
            Rational(1, 2),    # 0.5
            Rational(3, 4),    # 0.75
            Rational(2, 3),    # 0.667...
            Rational(1, 3),    # 0.333...
        ]
        
        rational_stickouts = [
            Rational(1, 40),   # 0.025
            Rational(3, 100),  # 0.03
            Rational(1, 25),   # 0.04
            Rational(1, 20),   # 0.05
            Rational(3, 50),   # 0.06
        ]
        
        for i, base_timber in enumerate(base_timbers):
            # Use exact rational position along the base timber
            location_on_base = rational_positions[i]
            locations_used.append(location_on_base)
            
            # Use exact rational stickout
            stickout = rational_stickouts[i]
            
            # Create offset configuration
            offset = FaceAlignedJoinedTimberOffset(
                reference_face=TimberFace.TOP,
                centerline_offset=None,
                face_offset=None
            )
            
            # Join base timber to beam
            # Let the function determine the orientation automatically by projecting
            # timber1's length direction onto the perpendicular plane
            joining_timber = join_perpendicular_on_face_parallel_timbers(
                timber1=base_timber,
                timber2=beam,
                location_on_timber1=location_on_base,
                stickout=Stickout(stickout, stickout),  # Symmetric stickout
                offset_from_timber1=offset,
                size=create_vector2d(Rational(8, 100), Rational(8, 100))  # 8cm x 8cm posts
                # Note: orientation_face_on_timber1 not specified - uses default projection
            )
            joining_timber.name = f"Post_{i}"
            joining_timbers.append(joining_timber)
        
        # Verify properties of joining timbers
        for i, joining_timber in enumerate(joining_timbers):
            base_timber = base_timbers[i]
            location_used = locations_used[i]
            
            # 1. Verify the joining timber is approximately vertical (perpendicular to horizontal base)
            # For horizontal base timbers, the joining timber should be mostly vertical
            length_dir = joining_timber.length_direction
            vertical_component = abs(float(length_dir[2]))  # Z component
            assert vertical_component > Rational("0.8"), f"Post_{i} should be mostly vertical, got length_direction={[float(x) for x in length_dir]}"
            
            # 2. Verify the joining timber connects to the correct position on the base timber
            expected_base_pos = base_timber.get_centerline_position_from_bottom(location_used)
            
            # The joining timber should start from approximately the top face of the base timber
            expected_start_z = expected_base_pos[2] + base_timber.size[1]  # Top of base timber
            actual_start_z = joining_timber.bottom_position[2]
            
            # Use exact comparison for rational arithmetic - allow for stickout adjustments
            start_z_diff = abs(actual_start_z - expected_start_z)
            assert start_z_diff < Rational("0.2"), f"Post_{i} should start near top of base timber, diff={float(start_z_diff)}"
            
            # 3. Verify the joining timber connects to the beam
            # The top of the joining timber should be near the beam
            joining_top = joining_timber.get_top_center_position()
            beam_bottom_z = beam.bottom_position[2]
            
            # Should connect somewhere on or near the beam - use exact comparison
            beam_connection_diff = abs(joining_top[2] - beam_bottom_z)
            assert beam_connection_diff < Rational("0.2"), f"Post_{i} should connect near beam level, diff={float(beam_connection_diff)}"
            
            # 4. Verify orthogonality of orientation matrix
            orientation_matrix = joining_timber.orientation.matrix
            product = orientation_matrix * orientation_matrix.T
            identity = Matrix.eye(3)
            
            # Check orthogonality with tolerance for floating-point precision
            diff_matrix = product - identity
            max_error = max([abs(float(diff_matrix[i, j])) for i in range(3) for j in range(3)])
            assert max_error < 1e-12, f"Post_{i} orientation matrix should be orthogonal, max error: {max_error}"
            
            # 5. Verify determinant is 1 (proper rotation)
            det = orientation_matrix.det()
            det_error = abs(float(det - 1))
            assert det_error < 1e-12, f"Post_{i} orientation matrix determinant should be 1, error: {det_error}"
        
        # Test cross-connections between base timbers
        cross_connections = []
        
        # Use deterministic pairs and rational parameters for cross-connections
        cross_connection_configs = [
            (0, 2, Rational(1, 3), Rational(1, 20)),   # Left to Right, loc=0.333, stickout=0.05
            (1, 3, Rational(1, 2), Rational(3, 40)),   # Center to Back, loc=0.5, stickout=0.075
            (2, 4, Rational(2, 3), Rational(1, 10)),   # Right to Front, loc=0.667, stickout=0.1
        ]
        
        # Connect some base timbers to each other horizontally
        for i, (timber1_idx, timber2_idx, loc1, stickout) in enumerate(cross_connection_configs):
            timber1 = base_timbers[timber1_idx]
            timber2 = base_timbers[timber2_idx]
            
            offset = FaceAlignedJoinedTimberOffset(
                reference_face=TimberFace.TOP,
                centerline_offset=None,
                face_offset=None
            )
            
            cross_timber = join_perpendicular_on_face_parallel_timbers(
                timber1=timber1,
                timber2=timber2,
                location_on_timber1=loc1,
                stickout=Stickout(stickout, stickout),  # Symmetric stickout
                offset_from_timber1=offset,
                size=create_vector2d(Rational(6, 100), Rational(6, 100)),  # 6cm x 6cm
                orientation_face_on_timber1=TimberFace.TOP
            )
            cross_timber.name = f"Cross_{i}"
            cross_connections.append(cross_timber)
        
        # Verify cross-connections
        for i, cross_timber in enumerate(cross_connections):
            # Cross-connections between horizontal face-aligned timbers should also be horizontal
            length_dir = cross_timber.length_direction
            horizontal_component = (float(length_dir[0])**2 + float(length_dir[1])**2)**Rational("0.5")
            assert horizontal_component > Rational("0.8"), f"Cross_{i} should be mostly horizontal for face-aligned horizontal timbers"
            
            # Should be at the same Z level as the base timbers (face-aligned)
            cross_z = cross_timber.bottom_position[2]
            expected_z = base_z + timber_size[1]  # Top face level of base timbers
            z_level_diff = abs(cross_z - expected_z)
            assert z_level_diff <= Rational("0.15"), f"Cross_{i} should be at the same level as base timbers, diff={float(z_level_diff)}"
            
            # Verify orthogonality with tolerance for floating-point precision
            orientation_matrix = cross_timber.orientation.matrix
            product = orientation_matrix * orientation_matrix.T
            identity = Matrix.eye(3)
            diff_matrix = product - identity
            max_error = max([abs(float(diff_matrix[i, j])) for i in range(3) for j in range(3)])
            assert max_error < 1e-12, f"Cross_{i} orientation matrix should be orthogonal, max error: {max_error}"
        
        print(f"✅ Successfully tested {len(joining_timbers)} vertical posts and {len(cross_connections)} cross-connections")
        print(f"   All joining timbers maintain proper face alignment and orthogonal orientation matrices")


class TestEnumsAndDataStructures:
    """Test enums and data structures."""
    
    def test_timber_location_type_enum(self):
        """Test FootprintLocation enum."""
        assert FootprintLocation.INSIDE.value == 1
        assert FootprintLocation.CENTER.value == 2
        assert FootprintLocation.OUTSIDE.value == 3
    
    def test_timber_face_enum(self):
        """Test TimberFace enum."""
        assert TimberFace.TOP.value == 1
        assert TimberFace.BOTTOM.value == 2
        assert TimberFace.RIGHT.value == 3
        assert TimberFace.FORWARD.value == 4
        assert TimberFace.LEFT.value == 5
        assert TimberFace.BACK.value == 6

    
    def test_face_aligned_joined_timber_offset(self):
        """Test FaceAlignedJoinedTimberOffset dataclass."""
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=Rational("0.05"),
            face_offset=Rational("0.02")
        )
        
        assert offset.reference_face == TimberFace.TOP
        assert offset.centerline_offset == Rational("0.05")
        assert offset.face_offset == Rational("0.02")
    
    def test_stickout_with_join_timbers(self):
        """Test that stickout produces correct timber length in join_timbers."""
        # Create two vertical posts 2.5 meters apart
        post1 = Timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=Rational(2),
            size=create_vector2d(Rational("0.15"), Rational("0.15")),
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(1, 0, 0)
        )
        
        post2 = Timber(
            bottom_position=create_vector3d(Rational("2.5"), 0, 0),
            length=Rational(2),
            size=create_vector2d(Rational("0.15"), Rational("0.15")),
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(1, 0, 0)
        )
        
        # Join with asymmetric stickout: 0.1m on post1 side, 0.3m on post2 side
        stickout1 = Rational("0.1")
        stickout2 = Rational("0.3")
        beam = join_timbers(
            timber1=post1,
            timber2=post2,
            location_on_timber1=Rational(1),
            stickout=Stickout(stickout1, stickout2),
            location_on_timber2=Rational(1),
            lateral_offset=Rational(0)
        )
        
        # Expected length: distance between posts (2.5m) + stickout1 (0.1m) + stickout2 (0.3m)
        expected_length = Rational("2.5") + stickout1 + stickout2
        assert abs(beam.length - expected_length) < 1e-10
        assert abs(beam.length - Rational("2.9")) < 1e-10
    
    def test_stickout_reference_assertions(self):
        """Test that join_timbers asserts when non-CENTER_LINE references are used."""
        import pytest
        from giraffe import StickoutReference
        
        # Create two posts 2.0 meters apart
        post1 = Timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(1, 0, 0)
        )
        
        post2 = Timber(
            bottom_position=create_vector3d(Rational(2), 0, 0),
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(1, 0, 0)
        )
        
        # Try to use INSIDE reference - should assert
        with pytest.raises(AssertionError, match="CENTER_LINE stickout reference"):
            join_timbers(
                timber1=post1,
                timber2=post2,
                location_on_timber1=Rational(1),
                stickout=Stickout(Rational("0.1"), Rational("0.1"), StickoutReference.INSIDE, StickoutReference.CENTER_LINE),
                location_on_timber2=Rational(1),
                lateral_offset=Rational(0)
            )
        
        # Try to use OUTSIDE reference - should assert
        with pytest.raises(AssertionError, match="CENTER_LINE stickout reference"):
            join_timbers(
                timber1=post1,
                timber2=post2,
                location_on_timber1=Rational(1),
                stickout=Stickout(Rational("0.1"), Rational("0.1"), StickoutReference.CENTER_LINE, StickoutReference.OUTSIDE),
                location_on_timber2=Rational(1),
                lateral_offset=Rational(0)
            )
    
    def test_stickout_reference_inside_face_aligned(self):
        """Test INSIDE stickout reference with face-aligned timbers."""
        from giraffe import StickoutReference, join_perpendicular_on_face_parallel_timbers, FaceAlignedJoinedTimberOffset, TimberFace
        
        # Create two parallel horizontal posts 2.0 meters apart
        post1 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),  # East
            width_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        post2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 2, 0),  # 2m north
            length_direction=create_vector3d(1, 0, 0),  # East (parallel)
            width_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        # Join with INSIDE reference
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        beam = join_perpendicular_on_face_parallel_timbers(
            post1, post2,
            location_on_timber1=Rational("1.5"),
            stickout=Stickout(Rational("0.1"), Rational("0.1"), StickoutReference.INSIDE, StickoutReference.INSIDE),
            offset_from_timber1=offset,
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        # Expected length: distance (2.0) + effective_stickout1 (0.1 + 0.1) + effective_stickout2 (0.1 + 0.1)
        # = 2.0 + 0.2 + 0.2 = 2.4
        assert abs(beam.length - Rational("2.4")) < 1e-10
    
    def test_stickout_reference_outside_face_aligned(self):
        """Test OUTSIDE stickout reference with face-aligned timbers."""
        from giraffe import StickoutReference, join_perpendicular_on_face_parallel_timbers, FaceAlignedJoinedTimberOffset, TimberFace
        
        # Create two parallel horizontal posts 2.0 meters apart
        post1 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),  # East
            width_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        post2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 2, 0),  # 2m north
            length_direction=create_vector3d(1, 0, 0),  # East (parallel)
            width_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        # Join with OUTSIDE reference
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        beam = join_perpendicular_on_face_parallel_timbers(
            post1, post2,
            location_on_timber1=Rational("1.5"),
            stickout=Stickout(Rational("0.2"), Rational("0.2"), StickoutReference.OUTSIDE, StickoutReference.OUTSIDE),
            offset_from_timber1=offset,
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        # Expected length: distance (2.0) + effective_stickout1 (0.2 - 0.1) + effective_stickout2 (0.2 - 0.1)
        # = 2.0 + 0.1 + 0.1 = 2.2
        assert abs(beam.length - Rational("2.2")) < 1e-10
    
    def test_timber_face_is_perpendicular(self):
        """Test TimberFace.is_perpendicular() method."""
        # Test X-axis faces perpendicular to Y-axis faces
        assert TimberFace.RIGHT.is_perpendicular(TimberFace.FORWARD)
        assert TimberFace.RIGHT.is_perpendicular(TimberFace.BACK)
        assert TimberFace.LEFT.is_perpendicular(TimberFace.FORWARD)
        assert TimberFace.LEFT.is_perpendicular(TimberFace.BACK)
        assert TimberFace.FORWARD.is_perpendicular(TimberFace.RIGHT)
        assert TimberFace.FORWARD.is_perpendicular(TimberFace.LEFT)
        assert TimberFace.BACK.is_perpendicular(TimberFace.RIGHT)
        assert TimberFace.BACK.is_perpendicular(TimberFace.LEFT)
        
        # Test X-axis faces perpendicular to Z-axis faces
        assert TimberFace.RIGHT.is_perpendicular(TimberFace.TOP)
        assert TimberFace.RIGHT.is_perpendicular(TimberFace.BOTTOM)
        assert TimberFace.LEFT.is_perpendicular(TimberFace.TOP)
        assert TimberFace.LEFT.is_perpendicular(TimberFace.BOTTOM)
        assert TimberFace.TOP.is_perpendicular(TimberFace.RIGHT)
        assert TimberFace.TOP.is_perpendicular(TimberFace.LEFT)
        assert TimberFace.BOTTOM.is_perpendicular(TimberFace.RIGHT)
        assert TimberFace.BOTTOM.is_perpendicular(TimberFace.LEFT)
        
        # Test Y-axis faces perpendicular to Z-axis faces
        assert TimberFace.FORWARD.is_perpendicular(TimberFace.TOP)
        assert TimberFace.FORWARD.is_perpendicular(TimberFace.BOTTOM)
        assert TimberFace.BACK.is_perpendicular(TimberFace.TOP)
        assert TimberFace.BACK.is_perpendicular(TimberFace.BOTTOM)
        assert TimberFace.TOP.is_perpendicular(TimberFace.FORWARD)
        assert TimberFace.TOP.is_perpendicular(TimberFace.BACK)
        assert TimberFace.BOTTOM.is_perpendicular(TimberFace.FORWARD)
        assert TimberFace.BOTTOM.is_perpendicular(TimberFace.BACK)
        
        # Test non-perpendicular pairs (opposite faces on same axis)
        assert not TimberFace.RIGHT.is_perpendicular(TimberFace.LEFT)
        assert not TimberFace.LEFT.is_perpendicular(TimberFace.RIGHT)
        assert not TimberFace.FORWARD.is_perpendicular(TimberFace.BACK)
        assert not TimberFace.BACK.is_perpendicular(TimberFace.FORWARD)
        assert not TimberFace.TOP.is_perpendicular(TimberFace.BOTTOM)
        assert not TimberFace.BOTTOM.is_perpendicular(TimberFace.TOP)
        
        # Test same face (not perpendicular to itself)
        assert not TimberFace.RIGHT.is_perpendicular(TimberFace.RIGHT)
        assert not TimberFace.LEFT.is_perpendicular(TimberFace.LEFT)
        assert not TimberFace.FORWARD.is_perpendicular(TimberFace.FORWARD)
        assert not TimberFace.BACK.is_perpendicular(TimberFace.BACK)
        assert not TimberFace.TOP.is_perpendicular(TimberFace.TOP)
        assert not TimberFace.BOTTOM.is_perpendicular(TimberFace.BOTTOM)
    
    def test_timber_reference_long_face_to_timber_face(self):
        """Test TimberReferenceLongFace.to_timber_face() method."""
        assert TimberReferenceLongFace.RIGHT.to_timber_face() == TimberFace.RIGHT
        assert TimberReferenceLongFace.FORWARD.to_timber_face() == TimberFace.FORWARD
        assert TimberReferenceLongFace.LEFT.to_timber_face() == TimberFace.LEFT
        assert TimberReferenceLongFace.BACK.to_timber_face() == TimberFace.BACK
    
    def test_timber_reference_long_face_is_perpendicular(self):
        """Test TimberReferenceLongFace.is_perpendicular() method."""
        # Test perpendicular pairs
        assert TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.FORWARD)
        assert TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.BACK)
        assert TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.FORWARD)
        assert TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.BACK)
        assert TimberReferenceLongFace.FORWARD.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert TimberReferenceLongFace.FORWARD.is_perpendicular(TimberReferenceLongFace.LEFT)
        assert TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.LEFT)
        
        # Test non-perpendicular pairs (opposite faces)
        assert not TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.LEFT)
        assert not TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert not TimberReferenceLongFace.FORWARD.is_perpendicular(TimberReferenceLongFace.BACK)
        assert not TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.FORWARD)
        
        # Test same face (not perpendicular to itself)
        assert not TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert not TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.LEFT)
        assert not TimberReferenceLongFace.FORWARD.is_perpendicular(TimberReferenceLongFace.FORWARD)
        assert not TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.BACK)
    
    def test_distance_from_long_edge_is_valid(self):
        """Test DistanceFromLongEdge.is_valid() method."""
        # Valid cases - perpendicular faces
        valid_edge1 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.FORWARD, distance=Rational(2))
        )
        assert valid_edge1.is_valid()
        
        valid_edge2 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.BACK, distance=Rational(2))
        )
        assert valid_edge2.is_valid()
        
        valid_edge3 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FORWARD, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(2))
        )
        assert valid_edge3.is_valid()
        
        # Invalid cases - opposite faces (not perpendicular)
        invalid_edge1 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(2))
        )
        assert not invalid_edge1.is_valid()
        
        invalid_edge2 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FORWARD, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.BACK, distance=Rational(2))
        )
        assert not invalid_edge2.is_valid()
        
        # Invalid cases - same face
        invalid_edge3 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(2))
        )
        assert not invalid_edge3.is_valid()
    
    def test_distance_from_long_edge_get_long_edge(self):
        """Test DistanceFromLongEdge.get_long_edge() method."""
        # Test all 8 valid combinations
        
        # RIGHT + FORWARD -> RIGHT_FORWARD
        edge1 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.FORWARD, distance=Rational(2))
        )
        assert edge1.get_long_edge() == TimberReferenceLongEdge.RIGHT_FORWARD
        
        # FORWARD + LEFT -> FORWARD_LEFT
        edge2 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FORWARD, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(2))
        )
        assert edge2.get_long_edge() == TimberReferenceLongEdge.FORWARD_LEFT
        
        # LEFT + BACK -> LEFT_BACK
        edge3 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.BACK, distance=Rational(2))
        )
        assert edge3.get_long_edge() == TimberReferenceLongEdge.LEFT_BACK
        
        # BACK + RIGHT -> BACK_RIGHT
        edge4 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.BACK, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(2))
        )
        assert edge4.get_long_edge() == TimberReferenceLongEdge.BACK_RIGHT
        
        # FORWARD + RIGHT -> FORWARD_RIGHT
        edge5 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FORWARD, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(2))
        )
        assert edge5.get_long_edge() == TimberReferenceLongEdge.FORWARD_RIGHT
        
        # RIGHT + BACK -> RIGHT_BACK
        edge6 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.BACK, distance=Rational(2))
        )
        assert edge6.get_long_edge() == TimberReferenceLongEdge.RIGHT_BACK
        
        # BACK + LEFT -> BACK_LEFT
        edge7 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.BACK, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(2))
        )
        assert edge7.get_long_edge() == TimberReferenceLongEdge.BACK_LEFT
        
        # LEFT + FORWARD -> LEFT_FORWARD
        edge8 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.FORWARD, distance=Rational(2))
        )
        assert edge8.get_long_edge() == TimberReferenceLongEdge.LEFT_FORWARD
    
    def test_distance_from_long_edge_get_long_edge_invalid(self):
        """Test DistanceFromLongEdge.get_long_edge() with invalid face combinations."""
        # Test invalid combination (opposite faces)
        invalid_edge = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(2))
        )
        
        try:
            invalid_edge.get_long_edge()
            assert False, "Should have raised ValueError for invalid face combination"
        except ValueError as e:
            assert "Invalid faces" in str(e)


class TestHelperFunctions:
    """Test helper functions for timber operations."""
    
    def test_timber_get_closest_oriented_face_axis_aligned(self):
        """Test Timber.get_closest_oriented_face() with axis-aligned timber."""
        # Create an axis-aligned timber (standard orientation)
        timber = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),  # width=0.2, height=0.3
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),  # Z-up (length)
            width_direction=create_vector3d(1, 0, 0)     # X-right (face/width)
        )
        
                # Test alignment with each cardinal direction
        # Note: CORRECTED timber coordinate system:
        # - TOP/BOTTOM faces are along length_direction (Z-axis)
        # - RIGHT/LEFT faces are along width_direction (X-axis)  
        # - FORWARD/BACK faces are along height_direction (Y-axis)

        # Target pointing in +Z (length direction) should align with TOP face
        target_length_pos = create_vector3d(0, 0, 1)
        aligned_face = timber.get_closest_oriented_face(target_length_pos)
        assert aligned_face == TimberFace.TOP

        # Target pointing in -Z (negative length direction) should align with BOTTOM face
        target_length_neg = create_vector3d(0, 0, -1)
        aligned_face = timber.get_closest_oriented_face(target_length_neg)
        assert aligned_face == TimberFace.BOTTOM

        # Target pointing in +X (face direction) should align with RIGHT face
        target_face_pos = create_vector3d(1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_face_pos)
        assert aligned_face == TimberFace.RIGHT

        # Target pointing in -X (negative face direction) should align with LEFT face
        target_face_neg = create_vector3d(-1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_face_neg)
        assert aligned_face == TimberFace.LEFT

        # Target pointing in +Y (height direction) should align with FORWARD face
        target_height_pos = create_vector3d(0, 1, 0)
        aligned_face = timber.get_closest_oriented_face(target_height_pos)
        assert aligned_face == TimberFace.FORWARD

        # Target pointing in -Y (negative height direction) should align with BACK face
        target_height_neg = create_vector3d(0, -1, 0)
        aligned_face = timber.get_closest_oriented_face(target_height_neg)
        assert aligned_face == TimberFace.BACK
    
    def test_timber_get_closest_oriented_face_rotated(self):
        """Test Timber.get_closest_oriented_face() with rotated timber."""
        # Create a timber rotated 90 degrees around Z axis
        # length_direction stays Z-up, but width_direction becomes Y-forward
        timber = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),  # Z-up (length)
            width_direction=create_vector3d(0, 1, 0)     # Y-forward (face/width)
        )
        
                # Now the timber's faces are rotated (CORRECTED):
        # TOP face points in +Z direction (length_direction)
        # BOTTOM face points in -Z direction (negative length_direction)
        # RIGHT face points in +Y direction (width_direction)
        # LEFT face points in -Y direction (negative width_direction)
        # FORWARD face points in -X direction (height_direction)
        # BACK face points in +X direction (negative height_direction)

        # Target pointing in +Y direction should align with RIGHT face
        target_y_pos = create_vector3d(0, 1, 0)
        aligned_face = timber.get_closest_oriented_face(target_y_pos)
        assert aligned_face == TimberFace.RIGHT

        # Target pointing in -Y direction should align with LEFT face
        target_y_neg = create_vector3d(0, -1, 0)
        aligned_face = timber.get_closest_oriented_face(target_y_neg)
        assert aligned_face == TimberFace.LEFT

        # Target pointing in -X direction should align with FORWARD face
        target_x_neg = create_vector3d(-1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_x_neg)
        assert aligned_face == TimberFace.FORWARD

        # Target pointing in +X direction should align with BACK face
        target_x_pos = create_vector3d(1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_x_pos)
        assert aligned_face == TimberFace.BACK
    
    def test_timber_get_closest_oriented_face_horizontal(self):
        """Test Timber.get_closest_oriented_face() with horizontal timber."""
        # Create a horizontal timber lying along X axis
        timber = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),   # X-right (length)
            width_direction=create_vector3d(0, 0, 1)      # Z-up (face/width)
        )
        
        # For this horizontal timber (CORRECTED):
        # TOP face points in +X direction (length_direction)
        # BOTTOM face points in -X direction (negative length_direction)
        # RIGHT face points in +Z direction (width_direction)
        # LEFT face points in -Z direction (negative width_direction)
        # FORWARD face points in -Y direction (height_direction)  
        # BACK face points in +Y direction (negative height_direction)
        
        # Target pointing in +Z should align with RIGHT face
        target_z_pos = create_vector3d(0, 0, 1)
        aligned_face = timber.get_closest_oriented_face(target_z_pos)
        assert aligned_face == TimberFace.RIGHT
        
        # Target pointing in -Z should align with LEFT face
        target_z_neg = create_vector3d(0, 0, -1)
        aligned_face = timber.get_closest_oriented_face(target_z_neg)
        assert aligned_face == TimberFace.LEFT
        
        # Target pointing in +X (length direction) should align with TOP face
        target_x_pos = create_vector3d(1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_x_pos)
        assert aligned_face == TimberFace.TOP
        
        # Target pointing in +Y should align with BACK face
        target_y_pos = create_vector3d(0, 1, 0)
        aligned_face = timber.get_closest_oriented_face(target_y_pos)
        assert aligned_face == TimberFace.BACK
    
    def test_timber_get_closest_oriented_face_diagonal(self):
        """Test Timber.get_closest_oriented_face() with diagonal target direction."""
        # Create an axis-aligned timber
        timber = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
                # Test with diagonal direction that's closer to +Z than +X
        # This should align with TOP face (Z-direction)
        target_diagonal_z = normalize_vector(create_vector3d(Rational("0.3"), 0, 1))  # Mostly +Z, little bit +X
        aligned_face = timber.get_closest_oriented_face(target_diagonal_z)
        assert aligned_face == TimberFace.TOP

        # Test with diagonal direction that's closer to +X than +Z
        # This should align with RIGHT face (X-direction)
        target_diagonal_x = normalize_vector(create_vector3d(1, 0, Rational("0.3")))  # Mostly +X, little bit +Z
        aligned_face = timber.get_closest_oriented_face(target_diagonal_x)
        assert aligned_face == TimberFace.RIGHT
    
    def test_timber_get_face_direction(self):
        """Test Timber.get_face_direction() method."""
        # Create an axis-aligned timber
        timber = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        # Test that face directions match expected values (CORRECTED MAPPING)
        top_dir = timber.get_face_direction(TimberFace.TOP)
        assert top_dir == timber.length_direction
        
        bottom_dir = timber.get_face_direction(TimberFace.BOTTOM)
        assert bottom_dir == -timber.length_direction
        
        right_dir = timber.get_face_direction(TimberFace.RIGHT)
        assert right_dir == timber.width_direction
        
        left_dir = timber.get_face_direction(TimberFace.LEFT)
        assert left_dir == -timber.width_direction
        
        # FORWARD should be the height direction
        forward_dir = timber.get_face_direction(TimberFace.FORWARD)
        assert forward_dir == timber.height_direction
        
        # BACK should be the negative height direction
        back_dir = timber.get_face_direction(TimberFace.BACK)
        assert back_dir == -timber.height_direction
    
    def test_timber_get_face_direction_for_ends(self):
        """Test using Timber.get_face_direction() for timber ends."""
        # Create a timber
        timber = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        # Test TOP end direction (using TimberFace.TOP)
        top_dir = timber.get_face_direction(TimberFace.TOP)
        assert top_dir == timber.length_direction
        
        # Test BOTTOM end direction (using TimberFace.BOTTOM)
        bottom_dir = timber.get_face_direction(TimberFace.BOTTOM)
        assert bottom_dir == -timber.length_direction
    
    def test_are_timbers_face_parallel(self):
        """Test _are_timbers_face_parallel helper function."""
        # Create two timbers with parallel length directions
        timber1 = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.15"), Rational("0.25")),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same direction
            width_direction=create_vector3d(0, 1, 0)      # Different face direction
        )
        
        # Should be parallel (parallel length directions)
        assert _are_timbers_face_parallel(timber1, timber2)
        
        # Create a timber with opposite direction (still parallel)
        timber3 = Timber(
            length=Rational("1.5"),
            size=create_vector2d(Rational("0.1"), Rational("0.2")),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, -1),  # Opposite direction
            width_direction=create_vector3d(1, 0, 0)
        )
        
        # Should still be parallel (anti-parallel is still parallel)
        assert _are_timbers_face_parallel(timber1, timber3)
        
        # Create a timber with perpendicular direction
        timber4 = Timber(
            length=Rational("2.5"),
            size=create_vector2d(Rational("0.3"), Rational("0.3")),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=create_vector3d(1, 0, 0),   # Perpendicular
            width_direction=create_vector3d(0, 0, 1)
        )
        
        # Should NOT be parallel
        assert not _are_timbers_face_parallel(timber1, timber4)
    
    def test_are_timbers_face_orthogonal(self):
        """Test _are_timbers_face_orthogonal helper function."""
        # Create two timbers with perpendicular length directions
        timber1 = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.15"), Rational("0.25")),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(1, 0, 0),   # X-right (perpendicular to timber1)
            width_direction=create_vector3d(0, 0, 1)      # Z-up
        )
        
        # Should be orthogonal
        assert _are_timbers_face_orthogonal(timber1, timber2)
        
        # Create a timber with parallel direction
        timber3 = Timber(
            length=Rational("1.5"),
            size=create_vector2d(Rational("0.1"), Rational("0.2")),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same as timber1
            width_direction=create_vector3d(1, 0, 0)
        )
        
        # Should NOT be orthogonal
        assert not _are_timbers_face_orthogonal(timber1, timber3)
        
        # Test with Y-direction
        timber4 = Timber(
            length=Rational("2.5"),
            size=create_vector2d(Rational("0.3"), Rational("0.3")),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=create_vector3d(0, 1, 0),   # Y-forward (perpendicular to timber1)
            width_direction=create_vector3d(1, 0, 0)
        )
        
        # Should be orthogonal
        assert _are_timbers_face_orthogonal(timber1, timber4)
    
    def test_are_timbers_face_aligned(self):
        """Test _are_timbers_face_aligned helper function."""
        # Create a reference timber with standard orientation
        timber1 = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)      # X-right
        )
        # timber1 directions: length=[0,0,1], face=[1,0,0], height=[0,1,0]
        
        # Test 1: Timber with same orientation - should be face-aligned
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.15"), Rational("0.25")),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same as timber1
            width_direction=create_vector3d(1, 0, 0)      # Same as timber1
        )
        assert _are_timbers_face_aligned(timber1, timber2)
        
        # Test 2: Timber rotated 90° around Z - should be face-aligned  
        # (length stays Z, but face becomes Y, height becomes -X)
        timber3 = Timber(
            length=Rational("1.5"),
            size=create_vector2d(Rational("0.1"), Rational("0.2")),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same Z
            width_direction=create_vector3d(0, 1, 0)      # Y direction
        )
        assert _are_timbers_face_aligned(timber1, timber3)
        
        # Test 3: Timber rotated 90° around X - should be face-aligned
        # (length becomes -Y, face stays X, height becomes Z) 
        timber4 = Timber(
            length=Rational("2.5"),
            size=create_vector2d(Rational("0.3"), Rational("0.3")),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=create_vector3d(0, -1, 0),  # -Y direction
            width_direction=create_vector3d(1, 0, 0)      # Same X
        )
        assert _are_timbers_face_aligned(timber1, timber4)
        
        # Test 4: Timber with perpendicular orientation but face-aligned
        # (length becomes X, face becomes Z, height becomes Y)
        timber5 = Timber(
            length=Rational("1.8"),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 2, 0),
            length_direction=create_vector3d(1, 0, 0),   # X direction  
            width_direction=create_vector3d(0, 0, 1)      # Z direction
        )
        assert _are_timbers_face_aligned(timber1, timber5)
        
        # Test 5: Timber with arbitrary 3D rotation - should NOT be face-aligned
        # Using a rotation that doesn't align any direction with cardinal axes
        import math
        # Create a rotation that's 30° around X, then 45° around the new Y
        cos30 = math.cos(math.pi/6)
        sin30 = math.sin(math.pi/6)
        cos45 = math.cos(math.pi/4)
        sin45 = math.sin(math.pi/4)
        
        # This creates a timber whose directions don't align with any cardinal axes
        timber6 = Timber(
            length=Rational(1),
            size=create_vector2d(Rational("0.1"), Rational("0.1")),
            bottom_position=create_vector3d(0, 0, 2),
            length_direction=create_vector3d(sin45*cos30, sin45*sin30, cos45),  # Complex 3D direction
            width_direction=create_vector3d(cos45*cos30, cos45*sin30, -sin45)    # Perpendicular complex direction
        )
        assert not _are_timbers_face_aligned(timber1, timber6)
        
        # Test 6: Verify that 45° rotation in XY plane IS face-aligned 
        # (because height direction is still Z, parallel to timber1's length direction)
        cos45_xy = math.cos(math.pi/4)
        sin45_xy = math.sin(math.pi/4)
        timber7 = Timber(
            length=Rational(1),
            size=create_vector2d(Rational("0.1"), Rational("0.1")),
            bottom_position=create_vector3d(0, 0, 2),
            length_direction=create_vector3d(cos45_xy, sin45_xy, 0),  # 45° in XY plane
            width_direction=create_vector3d(-sin45_xy, cos45_xy, 0)    # Perpendicular in XY
        )
        # This SHOULD be face-aligned because height direction = [0,0,1] = timber1.length_direction
        assert _are_timbers_face_aligned(timber1, timber7)
        
        # Test 8: Verify face-aligned timbers can be orthogonal
        # timber1 length=[0,0,1], timber5 length=[1,0,0] - these are orthogonal but face-aligned
        assert _are_timbers_face_aligned(timber1, timber5)
        assert _are_timbers_face_orthogonal(timber1, timber5)
        
        # Test 9: Verify face-aligned timbers can be parallel  
        # timber1 and timber2 have same length direction - parallel and face-aligned
        assert _are_timbers_face_aligned(timber1, timber2)
        assert _are_timbers_face_parallel(timber1, timber2)
    
    def test_has_rational_components(self):
        """Test _has_rational_components helper function."""
        from sympy import Rational, Float
        
        # Test with rational components
        rational_vec = create_vector3d(Rational(1, 2), Rational(3, 4), Rational(1, 1))
        assert _has_rational_components(rational_vec)
        
        # Test with integer components
        int_vec = create_vector3d(1, 0, 1)
        assert _has_rational_components(int_vec)
        
        # Test with float components
        float_vec = create_vector3d(Float("0.5"), Float("0.75"), Float(1))
        assert not _has_rational_components(float_vec)
        
        # Test with mixed components (has at least one Float, so not all rational)
        mixed_vec = create_vector3d(Rational(1, 2), Float("0.75"), 1)
        assert not _has_rational_components(mixed_vec)
    
    def test_are_directions_perpendicular_rational(self):
        """Test _are_directions_perpendicular with rational (exact) values."""
        from sympy import Rational
        
        # Test perpendicular rational vectors (should use exact comparison)
        v1 = create_vector3d(1, 0, 0)
        v2 = create_vector3d(0, 1, 0)
        assert _are_directions_perpendicular(v1, v2)
        
        # Test with rational components
        v3 = create_vector3d(Rational(1, 2), Rational(1, 2), 0)
        v3 = normalize_vector(v3)
        v4 = create_vector3d(Rational(-1, 2), Rational(1, 2), 0)
        v4 = normalize_vector(v4)
        assert _are_directions_perpendicular(v3, v4)
        
        # Test non-perpendicular rational vectors
        v5 = create_vector3d(1, 0, 0)
        v6 = create_vector3d(1, 1, 0)
        v6 = normalize_vector(v6)
        assert not _are_directions_perpendicular(v5, v6)
    
    def test_are_directions_perpendicular_float(self):
        """Test _are_directions_perpendicular with float (fuzzy) values."""
        import math
        
        # Test perpendicular float vectors (should use tolerance)
        v1 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v2 = create_vector3d(Rational(0), Rational(1), Rational(0))
        assert _are_directions_perpendicular(v1, v2)
        
        # Test nearly perpendicular vectors (within tolerance)
        angle = math.pi / 2 + 1e-11  # Very close to 90 degrees
        v3 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v4 = create_vector3d(math.cos(angle), math.sin(angle), Rational(0))
        assert _are_directions_perpendicular(v3, v4)
        
        # Test not perpendicular (outside tolerance)
        v5 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v6 = create_vector3d(Rational("0.1"), Rational("0.99"), Rational(0))  # About 84 degrees
        assert not _are_directions_perpendicular(v5, v6)
    
    def test_are_directions_perpendicular_explicit_tolerance(self):
        """Test _are_directions_perpendicular with explicit tolerance."""
        # Test with custom tolerance
        v1 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v2 = create_vector3d(Rational("0.01"), Rational(1), Rational(0))  # Nearly perpendicular
        
        # Should pass with loose tolerance
        assert _are_directions_perpendicular(v1, v2, tolerance=Rational("0.1"))
        
        # Should fail with tight tolerance
        assert not _are_directions_perpendicular(v1, v2, tolerance=1e-6)
    
    def test_are_directions_parallel_rational(self):
        """Test _are_directions_parallel with rational (exact) values."""
        from sympy import Rational
        
        # Test parallel rational vectors (same direction)
        v1 = create_vector3d(1, 0, 0)
        v2 = create_vector3d(2, 0, 0)
        v2 = normalize_vector(v2)
        assert _are_directions_parallel(v1, v2)
        
        # Test anti-parallel rational vectors (opposite direction)
        v3 = create_vector3d(1, 0, 0)
        v4 = create_vector3d(-1, 0, 0)
        assert _are_directions_parallel(v3, v4)
        
        # Test with rational components
        v5 = create_vector3d(Rational(1, 2), Rational(1, 2), 0)
        v5 = normalize_vector(v5)
        v6 = create_vector3d(Rational(3, 4), Rational(3, 4), 0)
        v6 = normalize_vector(v6)
        assert _are_directions_parallel(v5, v6)
        
        # Test non-parallel rational vectors
        v7 = create_vector3d(1, 0, 0)
        v8 = create_vector3d(0, 1, 0)
        assert not _are_directions_parallel(v7, v8)
    
    def test_are_directions_parallel_float(self):
        """Test _are_directions_parallel with float (fuzzy) values."""
        import math
        
        # Test parallel float vectors (same direction)
        v1 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v2 = create_vector3d(Rational("2.5"), Rational(0), Rational(0))
        v2 = normalize_vector(v2)
        assert _are_directions_parallel(v1, v2)
        
        # Test anti-parallel float vectors (opposite direction)
        v3 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v4 = create_vector3d(-Rational("3.7"), Rational(0), Rational(0))
        v4 = normalize_vector(v4)
        assert _are_directions_parallel(v3, v4)
        
        # Test nearly parallel vectors (within tolerance)
        small_angle = 1e-11
        v5 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v6 = create_vector3d(math.cos(small_angle), math.sin(small_angle), Rational(0))
        assert _are_directions_parallel(v5, v6)
        
        # Test not parallel (outside tolerance)
        v7 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v8 = create_vector3d(Rational("0.9"), Rational("0.1"), Rational(0))  # About 6 degrees
        v8 = normalize_vector(v8)
        assert not _are_directions_parallel(v7, v8)
    
    def test_are_directions_parallel_explicit_tolerance(self):
        """Test _are_directions_parallel with explicit tolerance."""
        # Test with custom tolerance
        v1 = create_vector3d(Rational(1), Rational(0), Rational(0))
        v2 = create_vector3d(Rational("0.99"), Rational("0.01"), Rational(0))  # Nearly parallel
        v2 = normalize_vector(v2)
        
        # Should pass with loose tolerance
        assert _are_directions_parallel(v1, v2, tolerance=Rational("0.1"))
        
        # Should fail with tight tolerance
        assert not _are_directions_parallel(v1, v2, tolerance=1e-6)
    
    def test_are_timbers_face_parallel_rational(self):
        """Test _are_timbers_face_parallel with rational (exact) values."""
        from sympy import Rational
        
        # Create timbers with exact rational directions
        timber1 = Timber(
            length=2,
            size=create_vector2d(Rational(1, 5), Rational(3, 10)),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(1, 0, 0)
        )
        
        timber2 = Timber(
            length=3,
            size=create_vector2d(Rational(1, 10), Rational(1, 4)),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(0, 0, 1),  # Parallel
            width_direction=create_vector3d(0, 1, 0)
        )
        
        # Should be parallel (exact comparison)
        assert _are_timbers_face_parallel(timber1, timber2)
        
        # Test anti-parallel (should still be parallel)
        timber3 = Timber(
            length=Rational(3, 2),
            size=create_vector2d(Rational(1, 10), Rational(1, 5)),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, -1),  # Anti-parallel
            width_direction=create_vector3d(1, 0, 0)
        )
        
        assert _are_timbers_face_parallel(timber1, timber3)
        
        # Test perpendicular (should not be parallel)
        timber4 = Timber(
            length=2,
            size=create_vector2d(Rational(3, 10), Rational(3, 10)),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=create_vector3d(1, 0, 0),  # Perpendicular
            width_direction=create_vector3d(0, 0, 1)
        )
        
        assert not _are_timbers_face_parallel(timber1, timber4)
    
    def test_are_timbers_face_parallel_float(self):
        """Test _are_timbers_face_parallel with float (fuzzy) values."""
        import math
        
        # Create timbers with float directions
        timber1 = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        # Slightly off parallel (within tolerance)
        small_angle = 1e-11
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.15"), Rational("0.25")),
            bottom_position=create_vector3d(Rational(2), Rational(0), Rational(0)),
            length_direction=create_vector3d(math.sin(small_angle), Rational(0), math.cos(small_angle)),
            width_direction=create_vector3d(math.cos(small_angle), Rational(0), -math.sin(small_angle))
        )
        
        # Should be parallel (fuzzy comparison)
        assert _are_timbers_face_parallel(timber1, timber2)
    
    def test_are_timbers_face_orthogonal_rational(self):
        """Test _are_timbers_face_orthogonal with rational (exact) values."""
        from sympy import Rational
        
        # Create timbers with exact rational perpendicular directions
        timber1 = Timber(
            length=2,
            size=create_vector2d(Rational(1, 5), Rational(3, 10)),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(1, 0, 0)
        )
        
        timber2 = Timber(
            length=3,
            size=create_vector2d(Rational(15, 100), Rational(1, 4)),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(1, 0, 0),  # Perpendicular
            width_direction=create_vector3d(0, 0, 1)
        )
        
        # Should be orthogonal (exact comparison)
        assert _are_timbers_face_orthogonal(timber1, timber2)
        
        # Test non-orthogonal
        timber3 = Timber(
            length=Rational(3, 2),
            size=create_vector2d(Rational(1, 10), Rational(1, 5)),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, 1),  # Parallel to timber1
            width_direction=create_vector3d(1, 0, 0)
        )
        
        assert not _are_timbers_face_orthogonal(timber1, timber3)
    
    def test_are_timbers_face_orthogonal_float(self):
        """Test _are_timbers_face_orthogonal with float (fuzzy) values."""
        import math
        
        # Create timbers with float perpendicular directions
        timber1 = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        # Nearly perpendicular (within tolerance)
        small_offset = 1e-11
        timber2 = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.15"), Rational("0.25")),
            bottom_position=create_vector3d(Rational(2), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(1), Rational(0), small_offset),
            width_direction=create_vector3d(Rational(0), Rational(1), Rational(0))
        )
        
        # Should be orthogonal (fuzzy comparison)
        assert _are_timbers_face_orthogonal(timber1, timber2)
    
    def test_are_timbers_face_aligned_exact_equality(self):
        """Test _are_timbers_face_aligned with exact equality (no tolerance)."""
        # Create two face-aligned timbers using exact rational values
        timber1 = Timber(
            length=2,  # Integer
            size=create_vector2d(Rational(1, 5), Rational(3, 10)),  # Exact rationals
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length_direction=create_vector3d(0, 0, 1),   # Vertical - integers
            width_direction=create_vector3d(1, 0, 0)      # East - integers
        )
        
        timber2 = Timber(
            length=3,  # Integer
            size=create_vector2d(Rational(3, 20), Rational(1, 4)),  # Exact rationals
            bottom_position=create_vector3d(2, 0, 0),  # Integers
            length_direction=create_vector3d(1, 0, 0),   # East (perpendicular to timber1) - integers
            width_direction=create_vector3d(0, 0, 1)      # Up - integers
        )
        
        # These should be face-aligned with exact equality (no tolerance)
        assert _are_timbers_face_aligned(timber1, timber2, tolerance=None)
        
        # Create a non-face-aligned timber (3D rotation with no aligned axes)
        # Using a timber rotated in 3D such that none of its axes align with timber1's axes
        timber3 = Timber(
            length=2,  # Integer
            size=create_vector2d(Rational(1, 5), Rational(1, 5)),  # Exact rationals
            bottom_position=create_vector3d(3, 3, 0),  # Integers
            length_direction=create_vector3d(1, 1, 1),   # 3D diagonal (will be normalized to Float)
            width_direction=create_vector3d(1, -1, 0)     # Perpendicular in 3D (will be normalized to Float)
        )
        
        # timber1 and timber3 should NOT be face-aligned
        # Note: This will trigger a warning because timber3's normalized directions contain Float values
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _are_timbers_face_aligned(timber1, timber3, tolerance=None)
            assert not result
            # Check that a warning was issued
            assert len(w) > 0
            assert "non-rational values" in str(w[0].message)
        
        # Test with tolerance parameter (no warning)
        assert _are_timbers_face_aligned(timber1, timber2, tolerance=1e-10)
    
    def test_project_point_on_timber_centerline(self):
        """Test _project_point_on_timber_centerline helper function."""
        # Create a timber along Z-axis
        timber = Timber(
            length=Rational(4),
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(1, 2, 0),    # Offset from origin
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)
        )
        
        # Test point directly on the centerline
        point_on_line = create_vector3d(1, 2, 2)  # 2 units up from bottom
        t, projected = _project_point_on_timber_centerline(point_on_line, timber)
        
        assert abs(t - Rational(2)) < 1e-10  # Should be 2 units along timber
        assert (projected - point_on_line).norm() < 1e-10  # Should project to itself
        
        # Test point off the centerline
        point_off_line = create_vector3d(3, 5, Rational("1.5"))  # 1.5 units up, but offset in X and Y
        t, projected = _project_point_on_timber_centerline(point_off_line, timber)
        
        assert abs(t - Rational("1.5")) < 1e-10  # Should be 1.5 units along timber
        expected_projection = create_vector3d(1, 2, Rational("1.5"))  # On centerline at same Z
        assert (projected - expected_projection).norm() < 1e-10
        
        # Test point before timber start (negative t)
        point_before = create_vector3d(1, 2, -1)  # 1 unit below bottom
        t, projected = _project_point_on_timber_centerline(point_before, timber)
        
        assert abs(t - (-Rational(1))) < 1e-10  # Should be -1 units
        assert (projected - point_before).norm() < 1e-10
        
        # Test point beyond timber end
        point_beyond = create_vector3d(1, 2, 5)  # 5 units up (beyond length of 4)
        t, projected = _project_point_on_timber_centerline(point_beyond, timber)
        
        assert abs(t - Rational(5)) < 1e-10  # Should be 5 units
        assert (projected - point_beyond).norm() < 1e-10
    
    def test_calculate_mortise_position_from_tenon_intersection(self):
        """Test _calculate_mortise_position_from_tenon_intersection helper function."""
        # Create a vertical mortise timber (post)
        mortise_timber = Timber(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            width_direction=create_vector3d(1, 0, 0)
        )
        
        # Create a horizontal tenon timber (beam) that intersects the post
        tenon_timber = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.15"), Rational("0.25")),
            bottom_position=create_vector3d(-Rational("0.5"), 0, Rational("1.5")),  # Starts at X=-0.5, intersects post at Z=1.5
            length_direction=create_vector3d(1, 0, 0),    # X-right
            width_direction=create_vector3d(0, 0, 1)
        )
        
        # Test with BOTTOM end of tenon timber
        ref_end, distance = _calculate_mortise_position_from_tenon_intersection(
            mortise_timber, tenon_timber, TimberReferenceEnd.BOTTOM
        )
        
        # The tenon BOTTOM is at (-0.5, 0, 1.5), which projects to (0, 0, 1.5) on the mortise centerline
        # Distance from mortise bottom (0, 0, 0) is 1.5
        # Distance from mortise top (0, 0, 3) is 1.5, so both are equal
        # Function should choose BOTTOM when distances are equal
        assert ref_end == TimberReferenceEnd.BOTTOM
        assert abs(distance - Rational("1.5")) < 1e-10
        
        # Test with TOP end of tenon timber  
        ref_end, distance = _calculate_mortise_position_from_tenon_intersection(
            mortise_timber, tenon_timber, TimberReferenceEnd.TOP
        )
        
        # The tenon TOP is at (1.5, 0, 1.5), which also projects to (0, 0, 1.5) on the mortise centerline
        # Same result as above
        assert ref_end == TimberReferenceEnd.BOTTOM
        assert abs(distance - Rational("1.5")) < 1e-10
        
        # Test with tenon closer to mortise top
        tenon_timber_high = Timber(
            length=Rational(2),
            size=create_vector2d(Rational("0.15"), Rational("0.25")),
            bottom_position=create_vector3d(-Rational("0.5"), 0, Rational("2.8")),  # Higher intersection
            length_direction=create_vector3d(1, 0, 0),
            width_direction=create_vector3d(0, 0, 1)
        )
        
        ref_end, distance = _calculate_mortise_position_from_tenon_intersection(
            mortise_timber, tenon_timber_high, TimberReferenceEnd.BOTTOM
        )
        
        # Intersection at Z=2.8, distance from bottom=2.8, distance from top=0.2
        # Should reference from TOP since it's closer
        assert ref_end == TimberReferenceEnd.TOP
        assert abs(distance - Rational("0.2")) < 1e-10


class TestTimberFootprintOrientation:
    """Test timber inside/outside face determination relative to footprint."""
    
    def test_get_inside_outside_faces(self):
        """Test get_inside_face and get_outside_face for various timber configurations."""
        # Create a square footprint
        corners = [
            create_vector2d(0, 0),
            create_vector2d(10, 0),
            create_vector2d(10, 10),
            create_vector2d(0, 10)
        ]
        footprint = Footprint(corners)
        
        # Test configurations: (description, bottom_pos, length_dir, width_dir, length, expected_inside, expected_outside)
        test_cases = [
            # Horizontal timber near bottom edge (y=1), running along X
            ("bottom_edge", 
             create_vector3d(1, 1, 0), create_vector3d(1, 0, 0), create_vector3d(0, 1, 0), Rational(8),
             TimberFace.RIGHT, TimberFace.LEFT),
            
            # Timber near right edge (x=9), running along Y
            ("right_edge", 
             create_vector3d(9, 1, 0), create_vector3d(0, 1, 0), create_vector3d(-1, 0, 0), Rational(8),
             TimberFace.TOP, TimberFace.BOTTOM),
            
            # Horizontal timber near top edge (y=9), running along X
            ("top_edge", 
             create_vector3d(1, 9, 0), create_vector3d(1, 0, 0), create_vector3d(0, -1, 0), Rational(8),
             TimberFace.BOTTOM, TimberFace.TOP),
            
            # Timber near left edge (x=1), running along Y
            ("left_edge", 
             create_vector3d(1, 1, 0), create_vector3d(0, 1, 0), create_vector3d(1, 0, 0), Rational(8),
             TimberFace.TOP, TimberFace.BOTTOM),
            
            # Vertical timber near bottom edge
            ("vertical", 
             create_vector3d(5, 1, 0), create_vector3d(0, 0, 1), create_vector3d(0, 1, 0), Rational(3),
             TimberFace.RIGHT, TimberFace.LEFT),
        ]
        
        for description, bottom_pos, length_dir, width_dir, length, expected_inside, expected_outside in test_cases:
            timber = Timber(
                length=length,
                size=create_vector2d(Rational("0.2"), Rational("0.3")),
                bottom_position=bottom_pos,
                length_direction=length_dir,
                width_direction=width_dir
            )
            
            inside_face = timber.get_inside_face(footprint)
            outside_face = timber.get_outside_face(footprint)
            
            assert inside_face == expected_inside, \
                f"{description}: Expected inside face {expected_inside}, got {inside_face}"
            assert outside_face == expected_outside, \
                f"{description}: Expected outside face {expected_outside}, got {outside_face}"
    
    def test_get_inside_face_diagonal_timber(self):
        """Test get_inside_face for timber at diagonal orientation."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(10, 0),
            create_vector2d(10, 10),
            create_vector2d(0, 10)
        ]
        footprint = Footprint(corners)
        
        # Diagonal timber from (1,1) going toward (9,9), but oriented so width points inward
        timber = Timber(
            length=Rational("11.31"),  # ~8*sqrt(2)
            size=create_vector2d(Rational("0.2"), Rational("0.3")),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=normalize_vector(create_vector3d(1, 1, 0)),  # Diagonal
            width_direction=normalize_vector(create_vector3d(-1, 1, 0))   # Perpendicular to length, pointing "inward-ish"
        )
        
        inside_face = timber.get_inside_face(footprint)
        outside_face = timber.get_outside_face(footprint)
        
        # Should determine a consistent inside/outside face based on nearest boundary
        # The exact face depends on which boundary is closest, but they should be opposite
        assert inside_face != outside_face
        
        # Verify that the inside and outside faces are opposite
        inside_dir = timber.get_face_direction(inside_face)
        outside_dir = timber.get_face_direction(outside_face)
        # Dot product should be negative (opposite directions)
        assert inside_dir.dot(outside_dir) < 0


class TestSplitTimber:
    """Test the split_timber method"""
    
    def test_split_timber_basic(self):
        """Test basic timber splitting at midpoint"""
        # Create a simple vertical timber
        timber = Timber(
            length=Rational(10),
            size=create_vector2d(Rational(4), Rational(4)),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        timber.name = "Test Timber"
        
        # Split at 30% (distance 3)
        bottom_timber, top_timber = split_timber(timber, Rational(3))
        
        # Check bottom timber
        assert bottom_timber.length == Rational(3)
        assert bottom_timber.size[0] == Rational(4)
        assert bottom_timber.size[1] == Rational(4)
        assert bottom_timber.bottom_position == create_vector3d(Rational(0), Rational(0), Rational(0))
        assert bottom_timber.length_direction == create_vector3d(Rational(0), Rational(0), Rational(1))
        assert bottom_timber.width_direction == create_vector3d(Rational(1), Rational(0), Rational(0))
        assert bottom_timber.name == "Test Timber_bottom"
        
        # Check top timber
        assert top_timber.length == Rational(7)
        assert top_timber.size[0] == Rational(4)
        assert top_timber.size[1] == Rational(4)
        assert top_timber.bottom_position == create_vector3d(Rational(0), Rational(0), Rational(3))
        assert top_timber.length_direction == create_vector3d(Rational(0), Rational(0), Rational(1))
        assert top_timber.width_direction == create_vector3d(Rational(1), Rational(0), Rational(0))
        assert top_timber.name == "Test Timber_top"
    
    def test_split_timber_horizontal(self):
        """Test splitting a horizontal timber"""
        # Create a horizontal timber along X axis
        timber = Timber(
            length=Rational(20),
            size=create_vector2d(Rational(6), Rational(4)),
            bottom_position=create_vector3d(Rational(5), Rational(10), Rational(2)),
            length_direction=create_vector3d(Rational(1), Rational(0), Rational(0)),
            width_direction=create_vector3d(Rational(0), Rational(1), Rational(0))
        )
        
        # Split at 8 units from bottom
        bottom_timber, top_timber = split_timber(timber, Rational(8))
        
        # Check bottom timber
        assert bottom_timber.length == Rational(8)
        assert bottom_timber.bottom_position == create_vector3d(Rational(5), Rational(10), Rational(2))
        
        # Check top timber
        assert top_timber.length == Rational(12)
        assert top_timber.bottom_position == create_vector3d(Rational(13), Rational(10), Rational(2))  # 5 + 8
    
    def test_split_timber_diagonal(self):
        """Test splitting a diagonal timber"""
        # Create a diagonal timber at 45 degrees
        length_dir = normalize_vector(create_vector3d(Rational(1), Rational(1), Rational(0)))
        
        timber = Timber(
            length=Rational(10),
            size=create_vector2d(Rational(4), Rational(4)),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=length_dir,
            width_direction=normalize_vector(create_vector3d(Rational(-1), Rational(1), Rational(0)))
        )
        
        # Split at 4 units from bottom
        bottom_timber, top_timber = split_timber(timber, Rational(4))
        
        # Check lengths
        assert bottom_timber.length == Rational(4)
        assert top_timber.length == Rational(6)
        
        # Check positions
        assert bottom_timber.bottom_position == create_vector3d(Rational(0), Rational(0), Rational(0))
        
        # Top timber should start at 4 units along the diagonal
        expected_top_pos = create_vector3d(Rational(0), Rational(0), Rational(0)) + Rational(4) * length_dir
        assert top_timber.bottom_position == expected_top_pos
        
        # Both should maintain same orientation
        assert bottom_timber.length_direction == length_dir
        assert top_timber.length_direction == length_dir
    
    def test_split_timber_with_rational(self):
        """Test splitting with exact rational arithmetic"""
        # Create a timber with rational values
        timber = Timber(
            length=Rational(10, 1),
            size=create_vector2d(Rational(4, 1), Rational(4, 1)),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        # Split at exact rational point
        split_distance = Rational(3, 1)
        bottom_timber, top_timber = split_timber(timber, split_distance)
        
        # Check exact rational values
        assert bottom_timber.length == Rational(3, 1)
        assert top_timber.length == Rational(7, 1)
        assert top_timber.bottom_position[2] == Rational(3, 1)
    
    def test_split_timber_invalid_distance(self):
        """Test that invalid split distances raise assertions"""
        timber = Timber(
            length=Rational(10),
            size=create_vector2d(Rational(4), Rational(4)),
            bottom_position=create_vector3d(Rational(0), Rational(0), Rational(0)),
            length_direction=create_vector3d(Rational(0), Rational(0), Rational(1)),
            width_direction=create_vector3d(Rational(1), Rational(0), Rational(0))
        )
        
        # Test split at 0 (should fail)
        try:
            split_timber(timber, Rational(0))
            assert False, "Should have raised assertion for distance = 0"
        except AssertionError:
            pass
        
        # Test split at length (should fail)
        try:
            split_timber(timber, Rational(10))
            assert False, "Should have raised assertion for distance = length"
        except AssertionError:
            pass
        
        # Test split beyond length (should fail)
        try:
            split_timber(timber, Rational(15))
            assert False, "Should have raised assertion for distance > length"
        except AssertionError:
            pass
        
        # Test negative distance (should fail)
        try:
            split_timber(timber, Rational(-5))
            assert False, "Should have raised assertion for negative distance"
        except AssertionError:
            pass
    
    def test_split_timber_preserves_orientation(self):
        """Test that both resulting timbers preserve the original orientation"""
        # Create a timber with non-standard orientation
        timber = Timber(
            length=Rational(15),
            size=create_vector2d(Rational(6), Rational(8)),
            bottom_position=create_vector3d(Rational(1), Rational(2), Rational(3)),
            length_direction=normalize_vector(create_vector3d(Rational(0), Rational(1), Rational(1))),
            width_direction=normalize_vector(create_vector3d(Rational(1), Rational(0), Rational(0)))
        )
        
        bottom_timber, top_timber = split_timber(timber, Rational(5))
        
        # Both should have same orientation as original
        assert bottom_timber.length_direction == timber.length_direction
        assert bottom_timber.width_direction == timber.width_direction
        assert bottom_timber.height_direction == timber.height_direction
        
        assert top_timber.length_direction == timber.length_direction
        assert top_timber.width_direction == timber.width_direction
        assert top_timber.height_direction == timber.height_direction
        
        # Both should have same size as original
        assert bottom_timber.size[0] == timber.size[0]
        assert bottom_timber.size[1] == timber.size[1]
        assert top_timber.size[0] == timber.size[0]
        assert top_timber.size[1] == timber.size[1]


class MockCut:
    """Mock Cut implementation for testing."""
    def __init__(self, timber: Timber, end_position: V3, maybe_end_cut: Optional[TimberReferenceEnd] = None):
        self._timber = timber
        self._end_position = end_position
        self.maybeEndCut = maybe_end_cut
        self.origin = Matrix([0, 0, 0])
        self.orientation = Orientation()
    
    def get_end_position(self) -> V3:
        return self._end_position
    
    def get_negative_csg(self):
        # Not needed for these tests
        pass


class TestCutTimber:
    """Test CutTimber CSG operations."""
    
    def test_extended_timber_without_cuts_finite(self):
        """Test _extended_timber_without_cuts_csg for a timber with no cuts (finite)."""
        # Create a simple timber
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber, 'test_timber')
        
        # Get the CSG
        csg = cut_timber._extended_timber_without_cuts_csg()
        
        # Should be a finite prism
        from meowmeowcsg import Prism
        assert isinstance(csg, Prism)
        
        # In LOCAL coordinates (relative to bottom_position):
        # Start should be at 0 (local bottom)
        assert csg.start_distance == 0
        
        # End should be at timber's length (local top)
        assert csg.end_distance == 100
        
        # Size should match timber
        assert csg.size == size
        # Orientation should be the timber's Orientation object
        assert csg.orientation == timber.orientation
    
    def test_extended_timber_without_cuts_positioned(self):
        """Test that CSG works correctly for timber at different position."""
        # Create a timber at a different position
        length = Rational(50)
        size = Matrix([Rational(3), Rational(4)])
        bottom_position = Matrix([Rational(5), Rational(10), Rational(20)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        csg = cut_timber._extended_timber_without_cuts_csg()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Start distance is 0 (at bottom)
        assert csg.start_distance == 0
        
        # End distance is the timber's length
        assert csg.end_distance == 50
    
    def test_extended_timber_minimal_boundary(self):
        """Test that minimal_boundary_in_direction works on the CSG in local coordinates."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        csg = cut_timber._extended_timber_without_cuts_csg()
        
        # Query minimal boundary in +Z direction (along timber axis)
        # Note: boundary is in local coordinates (relative to bottom_position)
        direction = Matrix([Rational(0), Rational(0), Rational(1)])
        boundary = csg.minimal_boundary_in_direction(direction)
        
        # In local coordinates, bottom is at z=0 (not z=10)
        assert boundary[2] == 0
    
    def test_extended_timber_horizontal(self):
        """Test CSG for a horizontal timber in local coordinates."""
        length = Rational(80)
        size = Matrix([Rational(5), Rational(5)])
        bottom_position = Matrix([Rational(10), Rational(20), Rational(5)])
        length_direction = Matrix([Rational(1), Rational(0), Rational(0)])  # Along X
        width_direction = Matrix([Rational(0), Rational(1), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        csg = cut_timber._extended_timber_without_cuts_csg()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Start distance is 0
        assert csg.start_distance == 0
        
        # End distance is the timber's length
        assert csg.end_distance == 80
        
        # Orientation should be the timber's Orientation object
        assert csg.orientation == timber.orientation
    
    def test_render_timber_without_cuts_no_end_cuts(self):
        """Test render_timber_without_cuts_csg with no end cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg()
        
        # Should be a finite prism with original dimensions in LOCAL coordinates
        # Local coordinates are relative to bottom_position
        from meowmeowcsg import Prism
        assert isinstance(csg, Prism)
        assert csg.start_distance == 0    # local: start at bottom (0)
        assert csg.end_distance == 100    # local: end at length (100)
    
    def test_render_timber_without_cuts_bottom_end_cut(self):
        """Test render_timber_without_cuts_csg with a bottom end cut."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        # Add a bottom end cut at z=15
        cut_end_position = Matrix([Rational(0), Rational(0), Rational(15)])
        bottom_cut = MockCut(timber, cut_end_position, TimberReferenceEnd.BOTTOM)
        cut_timber._cuts.append(bottom_cut)
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Bottom should be at cut position: z=15 → local = 15 - 10 = 5
        # Top at original: z=110 → local = 110 - 10 = 100 (timber length)
        assert csg.start_distance == 5    # local: (15 - 10)
        assert csg.end_distance == 100    # local: length
    
    def test_render_timber_without_cuts_top_end_cut(self):
        """Test render_timber_without_cuts_csg with a top end cut."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        # Add a top end cut at z=100
        cut_end_position = Matrix([Rational(0), Rational(0), Rational(100)])
        top_cut = MockCut(timber, cut_end_position, TimberReferenceEnd.TOP)
        cut_timber._cuts.append(top_cut)
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Bottom at original: z=10 → local = 0
        # Top at cut position: z=100 → local = 100 - 10 = 90
        assert csg.start_distance == 0    # local: 0 (no bottom cut)
        assert csg.end_distance == 90     # local: (100 - 10)
    
    def test_render_timber_without_cuts_both_end_cuts(self):
        """Test render_timber_without_cuts_csg with both end cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        # Add both end cuts
        bottom_cut_pos = Matrix([Rational(0), Rational(0), Rational(20)])
        top_cut_pos = Matrix([Rational(0), Rational(0), Rational(90)])
        bottom_cut = MockCut(timber, bottom_cut_pos, TimberReferenceEnd.BOTTOM)
        top_cut = MockCut(timber, top_cut_pos, TimberReferenceEnd.TOP)
        cut_timber._cuts.append(bottom_cut)
        cut_timber._cuts.append(top_cut)
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Bottom at cut position: z=20 → local = 20 - 10 = 10
        # Top at cut position: z=90 → local = 90 - 10 = 80
        assert csg.start_distance == 10   # local: (20 - 10)
        assert csg.end_distance == 80     # local: (90 - 10)
    
    def test_render_timber_without_cuts_multiple_bottom_cuts_error(self):
        """Test that multiple bottom end cuts raises an assertion error."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        # Add two bottom end cuts (invalid!)
        cut1 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(15)]), TimberReferenceEnd.BOTTOM)
        cut2 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(20)]), TimberReferenceEnd.BOTTOM)
        cut_timber._cuts.append(cut1)
        cut_timber._cuts.append(cut2)
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Bottom end has 2 end cuts"):
            cut_timber.render_timber_without_cuts_csg()
    
    def test_render_timber_without_cuts_multiple_top_cuts_error(self):
        """Test that multiple top end cuts raises an assertion error."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = Timber(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        # Add two top end cuts (invalid!)
        cut1 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(100)]), TimberReferenceEnd.TOP)
        cut2 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(95)]), TimberReferenceEnd.TOP)
        cut_timber._cuts.append(cut1)
        cut_timber._cuts.append(cut2)
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Top end has 2 end cuts"):
            cut_timber.render_timber_without_cuts_csg()


class TestMiterJoint:
    """Test cut_basic_miter_joint function."""
    
    def test_basic_miter_joint_orthogonal_through_origin(self):
        """Test basic miter joint with two orthogonal axis-aligned timbers through origin."""
        # Create two timbers of the same size through the origin
        # TimberA extends in +X direction
        timberA = Timber(
            length=Rational(100),
            size=Matrix([Rational(4), Rational(6)]),
            bottom_position=Matrix([Rational(-50), Rational(0), Rational(0)]),
            length_direction=Matrix([Rational(1), Rational(0), Rational(0)]),
            width_direction=Matrix([Rational(0), Rational(1), Rational(0)])
        )
        
        # TimberB extends in +Y direction
        timberB = Timber(
            length=Rational(100),
            size=Matrix([Rational(4), Rational(6)]),
            bottom_position=Matrix([Rational(0), Rational(-50), Rational(0)]),
            length_direction=Matrix([Rational(0), Rational(1), Rational(0)]),
            width_direction=Matrix([Rational(-1), Rational(0), Rational(0)])
        )
        
        # Create miter joint at the TOP ends (which meet at origin)
        joint = cut_basic_miter_joint(timberA, TimberReferenceEnd.TOP, timberB, TimberReferenceEnd.TOP)
        
        # Get the cuts
        cutA = joint.partiallyCutTimbers[0]._cuts[0]
        cutB = joint.partiallyCutTimbers[1]._cuts[0]
        
        # Check that both cuts are end cuts
        assert cutA.maybeEndCut == TimberReferenceEnd.TOP
        assert cutB.maybeEndCut == TimberReferenceEnd.TOP
        
        # Check that the half-plane normals are in LOCAL coordinates
        # For orthogonal timbers in +X and +Y directions:
        # - TimberA end direction (global): (+1, 0, 0)
        # - TimberB end direction (global): (0, +1, 0)
        # - Bisector (into joint, global): (+1, +1, 0) normalized = (1/√2, 1/√2, 0)
        #   NOTE: The bisector lives IN the miter plane (it's the line you draw on the wood)
        # - Plane formed by the two directions has normal: (1, 0, 0) × (0, 1, 0) = (0, 0, 1)
        # - Miter plane normal = bisector × plane_normal = (1/√2, 1/√2, 0) × (0, 0, 1)
        #   = (1/√2 * 1 - 0 * 0, 0 * 0 - 1/√2 * 1, 1/√2 * 0 - 1/√2 * 0)
        #   = (1/√2, -1/√2, 0)
        # 
        # TimberA's local basis (columns of orientation):
        #   X (width): (0, 1, 0), Y (height): (0, 0, 1), Z (length): (1, 0, 0)
        # TimberB's local basis:
        #   X (width): (-1, 0, 0), Y (height): (0, 0, 1), Z (length): (0, 1, 0)
        #
        # Local normal = orientation^T * global_normal
        #
        # For timberA: local_normal = orientation^T * (1/√2, -1/√2, 0)
        #   = (1/√2 * 0 + (-1/√2) * 1 + 0 * 0, 1/√2 * 0 + (-1/√2) * 0 + 0 * 1, 1/√2 * 1 + (-1/√2) * 0 + 0 * 0)
        #   = (-1/√2, 0, 1/√2)
        #
        # For timberB: local_normal = orientation^T * (1/√2, -1/√2, 0)
        #   = (1/√2 * -1 + (-1/√2) * 0 + 0 * 0, 1/√2 * 0 + (-1/√2) * 0 + 0 * 1, 1/√2 * 0 + (-1/√2) * 1 + 0 * 0)
        #   = (-1/√2, 0, -1/√2)
        
        # Import sqrt for comparison
        from sympy import sqrt
        
        expected_component = 1 / sqrt(2)
        
        # Check timberA local normal
        # Actual: (-√2/2, 0, √2/2)
        assert simplify(cutA.half_plane.normal[0] + expected_component) == 0  # Negative component
        assert cutA.half_plane.normal[1] == Rational(0)
        assert simplify(cutA.half_plane.normal[2] - expected_component) == 0
        
        # Check timberB local normal
        # Actual: (√2/2, 0, √2/2)
        assert simplify(cutB.half_plane.normal[0] - expected_component) == 0  # Positive component
        assert cutB.half_plane.normal[1] == Rational(0)
        assert simplify(cutB.half_plane.normal[2] - expected_component) == 0
        
        # Check the local offsets
        # Actual values from debug: both are 25*sqrt(2)
        # This makes sense because the miter plane passes through the origin (0, 0, 0)
        # and both timbers are positioned 50 units away from the origin along their axes
        expected_offset = 25 * sqrt(2)
        assert simplify(cutA.half_plane.offset - expected_offset) == 0
        assert simplify(cutB.half_plane.offset - expected_offset) == 0
        
        # Check that both cuts have the same origin (the intersection point)
        assert cutA.origin[0] == cutB.origin[0]
        assert cutA.origin[1] == cutB.origin[1]
        assert cutA.origin[2] == cutB.origin[2]
        
        # The origin should be at (0, 0, 0)
        assert cutA.origin[0] == Rational(0)
        assert cutA.origin[1] == Rational(0)
        assert cutA.origin[2] == Rational(0)
        
        # Check that the miter plane is at 45 degrees to each timber
        # Need to transform local normals back to global to compare with global timber directions
        # global_normal = orientation * local_normal
        global_normalA = timberA.orientation.matrix * cutA.half_plane.normal
        global_normalB = timberB.orientation.matrix * cutB.half_plane.normal
        
        # For orthogonal timbers, the angle between the miter normal and each timber direction
        # should be 45 degrees
        directionA = Matrix([Rational(1), Rational(0), Rational(0)])
        directionB = Matrix([Rational(0), Rational(1), Rational(0)])
        
        cos_angle_A = (global_normalA.T * directionA)[0, 0]
        cos_angle_B = (global_normalB.T * directionB)[0, 0]
        
        # Both should equal 1/√2 (cosine of 45 degrees)
        assert simplify(cos_angle_A - 1/sqrt(2)) == 0
        assert simplify(cos_angle_B - 1/sqrt(2)) == 0
        
        # For a proper miter joint where both timbers are being cut:
        # - TimberA extends in +X, being cut at top (positive end)
        # - TimberB extends in +Y, being cut at top (positive end)
        # - They meet at the origin
        # - The miter plane should bisect the angle between them
        # - Each normal should point AWAY from its timber (into the material being removed for that timber)
        # - The normals will be OPPOSITE in global space because the timbers are on opposite sides
        #
        # The HalfPlane represents the material to REMOVE (negative CSG).
        # For TimberA: we remove the region beyond the miter plane (away from timberB)
        # For TimberB: we remove the region beyond the miter plane (away from timberA)
        
        # Verify that the global normals are opposite (same plane, opposite orientations)
        assert simplify(global_normalA + global_normalB).norm() == 0, \
            f"Global normals should be opposite! A={global_normalA.T}, B={global_normalB.T}"
        
        # Verify they point in the expected direction
        # The miter plane normal is perpendicular to the bisector (1/√2, 1/√2, 0)
        # For orthogonal timbers in XY plane, the miter normal is (1/√2, -1/√2, 0) or its opposite
        expected_global_normalA = Matrix([1/sqrt(2), -1/sqrt(2), Rational(0)])
        expected_global_normalB = Matrix([-1/sqrt(2), 1/sqrt(2), Rational(0)])
        assert simplify(global_normalA - expected_global_normalA).norm() == 0, \
            f"Global normal A should be {expected_global_normalA.T}, got {global_normalA.T}"
        assert simplify(global_normalB - expected_global_normalB).norm() == 0, \
            f"Global normal B should be {expected_global_normalB.T}, got {global_normalB.T}"
        
        # Get end positions and verify they match
        endA = cutA.get_end_position()
        endB = cutB.get_end_position()
        
        # Both end positions should be at the origin
        assert endA[0] == Rational(0)
        assert endA[1] == Rational(0)
        assert endA[2] == Rational(0)
        
        assert endB[0] == Rational(0)
        assert endB[1] == Rational(0)
        assert endB[2] == Rational(0)
        
        # Test that the two cut timbers DO NOT intersect
        # Get the CSGs for both timbers with cuts applied
        cut_timberA = joint.partiallyCutTimbers[0]
        cut_timberB = joint.partiallyCutTimbers[1]
        
        # Render the timbers without cuts first (just the basic prisms)
        prismA = cut_timberA.render_timber_without_cuts_csg()
        prismB = cut_timberB.render_timber_without_cuts_csg()
        
        print(f"\nDEBUG: PrismA bounds: start={prismA.start_distance}, end={prismA.end_distance}")
        print(f"DEBUG: PrismB bounds: start={prismB.start_distance}, end={prismB.end_distance}")
        
        # For a proper miter with no overlap:
        # - TimberA should extend from x=-50 to x=0 (cut at the origin)
        # - TimberB should extend from y=-50 to y=0 (cut at the origin)
        # - They should meet at exactly (0,0,0) with no overlap
        #
        # In local coordinates:
        # - TimberA: length direction is +X, so it goes from z=0 to z=50 in local coords
        #   After miter cut at origin (global x=0), it should end at z=50 (which is at global x=0)
        # - TimberB: length direction is +Y, so it goes from z=0 to z=50 in local coords
        #   After miter cut at origin (global y=0), it should end at z=50 (which is at global y=0)
        
        # Check a few points to ensure no overlap
        # Point at (10, 10, 0) should NOT be in either timber (it's beyond both miter cuts)
        test_point1 = Matrix([Rational(10), Rational(10), Rational(0)])
        
        # Convert test_point1 to TimberA's local coordinates
        # local_point = orientation^T * (global_point - bottom_position)
        test_point1_localA = timberA.orientation.matrix.T * (test_point1 - timberA.bottom_position)
        print(f"\nDEBUG: Point (10,10,0) in TimberA local coords: {test_point1_localA.T}")
        
        # For this point to be in the timber (before cuts):
        # - X should be in [-width/2, width/2] = [-2, 2]
        # - Y should be in [-height/2, height/2] = [-3, 3]
        # - Z should be in [0, 50]
        print(f"  X in range? {-2 <= test_point1_localA[0] <= 2}")
        print(f"  Y in range? {-3 <= test_point1_localA[1] <= 3}")
        print(f"  Z in range? {0 <= test_point1_localA[2] <= 50}")
        
        # Check if point is removed by the miter cut
        # The half-plane normal (local) is (1/√2, 0, 1/√2), offset is 50/√2
        # Point should be removed if: normal · point >= offset
        dot_product = (cutA.half_plane.normal.T * test_point1_localA)[0, 0]
        is_removed = dot_product >= cutA.half_plane.offset
        print(f"  Dot product: {float(dot_product)}, offset: {float(cutA.half_plane.offset)}")
        print(f"  Is removed by cut? {is_removed}")
        
        # The point (10, 10, 0) should be removed by the miter cut on TimberA
        # because it's beyond the miter plane (x + y > 0)
        assert is_removed, "Point (10,10,0) should be removed by TimberA's miter cut"
    
    def test_miter_joint_parallel_timbers_raises_error(self):
        """Test that parallel timbers raise a ValueError."""
        # Create two parallel timbers
        timberA = Timber(
            length=Rational(100),
            size=Matrix([Rational(4), Rational(6)]),
            bottom_position=Matrix([Rational(0), Rational(0), Rational(0)]),
            length_direction=Matrix([Rational(1), Rational(0), Rational(0)]),
            width_direction=Matrix([Rational(0), Rational(1), Rational(0)])
        )
        
        timberB = Timber(
            length=Rational(100),
            size=Matrix([Rational(4), Rational(6)]),
            bottom_position=Matrix([Rational(0), Rational(10), Rational(0)]),
            length_direction=Matrix([Rational(1), Rational(0), Rational(0)]),
            width_direction=Matrix([Rational(0), Rational(1), Rational(0)])
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="cannot be parallel"):
            cut_basic_miter_joint(timberA, TimberReferenceEnd.TOP, timberB, TimberReferenceEnd.TOP)
