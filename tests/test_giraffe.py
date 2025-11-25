"""
Tests for giraffe.py module.

This module contains tests for the GiraffeCAD timber framing CAD system.
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs, Float, Rational
from moothymoth import Orientation
from footprint import Footprint
from giraffe import *
from giraffe import _timber_face_to_vector, _find_aligned_face, _get_timber_face_direction, _get_tenon_end_direction, _are_timbers_face_parallel, _are_timbers_face_orthogonal, _are_timbers_face_aligned, _project_point_on_timber_centerline, _calculate_mortise_position_from_tenon_intersection


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
        face_dir = create_vector3d(1, 0, 0)   # Use exact integers
        
        timber = Timber(length, size, position, length_dir, face_dir)
        
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
            face_direction=create_vector3d(1, 0, 0)     # East - exact integers
        )
        
        # Check that orientation matrix is reasonable
        matrix = timber.orientation.matrix
        assert matrix.shape == (3, 3)
        
        # Check that it's a valid rotation matrix (determinant = 1) - keep epsilon as float
        det_val = float(simplify(matrix.det()))
        assert abs(det_val - 1.0) < 1e-10
    
    def test_get_transform_matrix(self):
        """Test 4x4 transformation matrix generation."""
        timber = Timber(
            length=1,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(1, 2, 3),  # Use exact integers
            length_direction=create_vector3d(0, 0, 1), # Use exact integers
            face_direction=create_vector3d(1, 0, 0)    # Use exact integers
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
        input_face_dir = create_vector3d(1, 0, 0)    # East - exact integers
        
        timber = Timber(
            length=2,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        # Verify that the property getters return the correct normalized directions
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check that returned directions match input exactly (exact integers now)
        assert length_dir[0] == 0
        assert length_dir[1] == 0
        assert length_dir[2] == 1  # Exact integer from input
        
        assert face_dir[0] == 1    # Exact integer from input
        assert face_dir[1] == 0
        assert face_dir[2] == 0
        
        # Height direction should be cross product of length x face = Z x X = Y
        assert height_dir[0] == 0
        assert height_dir[1] == 1  # Exact integer from calculation
        assert height_dir[2] == 0
    
    def test_orientation_with_horizontal_timber(self):
        """Test orientation computation with a horizontal timber."""
        # Horizontal timber running north, facing up
        input_length_dir = create_vector3d(0, 1, 0)  # North - exact integers
        input_face_dir = create_vector3d(0, 0, 1)    # Up - exact integers
        
        timber = Timber(
            length=3,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check length direction (north) - exact integers now
        assert length_dir[0] == 0
        assert length_dir[1] == 1
        assert length_dir[2] == 0
        
        # Check face direction (up) - exact integers now
        assert face_dir[0] == 0
        assert face_dir[1] == 0
        assert face_dir[2] == 1
        
        # Height direction should be Y x Z = +X (east) - exact integers now
        assert height_dir[0] == 1
        assert height_dir[1] == 0
        assert height_dir[2] == 0
    
    def test_orientation_directions_are_orthonormal(self):
        """Test that the computed direction vectors form an orthonormal basis."""
        timber = Timber(
            length=1.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 1.0, 0.0),  # Non-axis-aligned
            face_direction=create_vector3d(0.0, 0.0, 1.0)     # Up
        )
        
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check that each vector has unit length
        length_mag = float(sqrt(sum(x**2 for x in length_dir)))
        face_mag = float(sqrt(sum(x**2 for x in face_dir)))
        height_mag = float(sqrt(sum(x**2 for x in height_dir)))
        
        assert abs(length_mag - 1.0) < 1e-10
        assert abs(face_mag - 1.0) < 1e-10
        assert abs(height_mag - 1.0) < 1e-10
        
        # Check that vectors are orthogonal (dot products = 0)
        length_face_dot = float(sum(length_dir[i] * face_dir[i] for i in range(3)))
        length_height_dot = float(sum(length_dir[i] * height_dir[i] for i in range(3)))
        face_height_dot = float(sum(face_dir[i] * height_dir[i] for i in range(3)))
        
        assert abs(length_face_dot) < 1e-10
        assert abs(length_height_dot) < 1e-10
        assert abs(face_height_dot) < 1e-10
    
    def test_orientation_handles_non_normalized_inputs(self):
        """Test that orientation computation works with non-normalized input vectors."""
        # Use vectors that aren't unit length
        input_length_dir = create_vector3d(0.0, 0.0, 5.0)  # Up, but length 5
        input_face_dir = create_vector3d(3.0, 0.0, 0.0)    # East, but length 3
        
        timber = Timber(
            length=1.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        # Despite non-normalized inputs, the output should be normalized
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        
        # Check that directions are normalized
        assert length_dir[0] == 0
        assert length_dir[1] == 0
        assert length_dir[2] == Float('1.0')
        
        assert face_dir[0] == Float('1.0')
        assert face_dir[1] == 0
        assert face_dir[2] == 0
    
    def test_get_position_on_timber(self):
        """Test the get_position_on_timber method."""
        timber = Timber(
            length=5.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(1.0, 2.0, 3.0),
            length_direction=create_vector3d(0.0, 1.0, 0.0),  # North
            face_direction=create_vector3d(0.0, 0.0, 1.0)     # Up
        )
        
        # Test at bottom position (position = 0)
        pos_at_bottom = timber.get_position_on_timber(0.0)
        assert pos_at_bottom[0] == Float('1.0')
        assert pos_at_bottom[1] == Float('2.0')
        assert pos_at_bottom[2] == Float('3.0')
        
        # Test at midpoint (position = 2.5)
        pos_at_middle = timber.get_position_on_timber(2.5)
        assert pos_at_middle[0] == Float('1.0')
        assert pos_at_middle[1] == Float('4.5')  # 2.0 + 2.5 * 1.0
        assert pos_at_middle[2] == Float('3.0')
        
        # Test at top (position = 5.0)
        pos_at_top = timber.get_position_on_timber(5.0)
        assert pos_at_top[0] == Float('1.0')
        assert pos_at_top[1] == Float('7.0')  # 2.0 + 5.0 * 1.0
        assert pos_at_top[2] == Float('3.0')
        
        # Test with negative position (beyond bottom)
        pos_neg = timber.get_position_on_timber(-1.0)
        assert pos_neg[0] == Float('1.0')
        assert pos_neg[1] == Float('1.0')  # 2.0 + (-1.0) * 1.0
        assert pos_neg[2] == Float('3.0')
    
    def test_reverse_position_on_timber(self):
        """Test the reverse_position_on_timber utility method."""
        timber = Timber(
            length=10.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),  # Up
            face_direction=create_vector3d(1.0, 0.0, 0.0)     # East
        )
        
        # Test reversing a position at 3.0 from bottom -> should be 7.0 from top
        reversed_pos = timber.reverse_position_on_timber(3.0)
        assert reversed_pos == Float('7.0')
        
        # Test reversing a position at 7.0 from bottom -> should be 3.0 from top
        reversed_pos2 = timber.reverse_position_on_timber(7.0)
        assert reversed_pos2 == Float('3.0')
        
        # Test at bottom (0) -> should be at top (10)
        reversed_at_bottom = timber.reverse_position_on_timber(0.0)
        assert reversed_at_bottom == Float('10.0')
        
        # Test at top (10) -> should be at bottom (0)
        reversed_at_top = timber.reverse_position_on_timber(10.0)
        assert reversed_at_top == Float('0.0')
        
        # Test at midpoint (5) -> should be at midpoint (5)
        reversed_at_mid = timber.reverse_position_on_timber(5.0)
        assert reversed_at_mid == Float('5.0')


class TestTimberCreation:
    """Test timber creation functions."""
    
    def test_create_timber(self):
        """Test basic create_timber function."""
        position = create_vector3d(1.0, 1.0, 0.0)
        size = create_vector2d(0.2, 0.3)
        length_dir = create_vector3d(0.0, 0.0, 1.0)
        face_dir = create_vector3d(1.0, 0.0, 0.0)
        
        timber = create_timber(position, 2.5, size, length_dir, face_dir)
        
        assert timber.length == 2.5
        assert float(timber.bottom_position[0]) == 1.0
        assert float(timber.bottom_position[1]) == 1.0
        assert float(timber.bottom_position[2]) == 0.0
    
    def test_create_axis_aligned_timber(self):
        """Test axis-aligned timber creation."""
        position = create_vector3d(0, 0, 0)  # Use exact integers
        size = create_vector2d(Rational(1, 10), Rational(1, 10))  # 0.1 as exact rational
        
        timber = create_axis_aligned_timber(
            position, 3, size,  # Use exact integer for length
            TimberFace.TOP,    # Length direction (up)
            TimberFace.RIGHT   # Face direction (east)
        )
        
        assert timber.length == 3  # Exact integer
        # Check that directions are correct
        assert timber.length_direction[2] == 1  # Up (exact integer)
        assert timber.face_direction[0] == 1    # East (exact integer)
    
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
            footprint, 0, post_height, TimberLocationType.INSIDE, size
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
        assert timber_inside.face_direction[0] == 1
        assert timber_inside.face_direction[1] == 0
        assert timber_inside.face_direction[2] == 0
        
        # Test CENTER positioning  
        # Center of bottom face is at corner
        timber_center = create_vertical_timber_on_footprint_corner(
            footprint, 0, post_height, TimberLocationType.CENTER, size
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
        assert timber_center.face_direction[0] == 1
        assert timber_center.face_direction[1] == 0
        
        # Test OUTSIDE positioning
        # Opposite vertex is at corner, post extends outside
        timber_outside = create_vertical_timber_on_footprint_corner(
            footprint, 0, post_height, TimberLocationType.OUTSIDE, size
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
        assert timber_outside.face_direction[0] == 1
        assert timber_outside.face_direction[1] == 0
    
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
            footprint, 0, distance_along_side, post_height, TimberLocationType.CENTER, size
        )
        
        assert timber_center.length == Rational(3, 1)
        # For CENTER, center is exactly at (1, 0) - exact!
        assert timber_center.bottom_position[0] == 1
        assert timber_center.bottom_position[1] == 0
        assert timber_center.bottom_position[2] == 0
        # Should be vertical
        assert timber_center.length_direction[2] == 1
        # Face direction should be parallel to the side (along +X)
        assert timber_center.face_direction[0] == 1
        assert timber_center.face_direction[1] == 0
        
        # Test INSIDE positioning
        # One edge center is at the point, post extends inside (toward +Y)
        timber_inside = create_vertical_timber_on_footprint_side(
            footprint, 0, distance_along_side, post_height, TimberLocationType.INSIDE, size
        )
        
        assert timber_inside.length == Rational(3, 1)
        # For INSIDE, offset by half depth inward (toward +Y)
        assert timber_inside.bottom_position[0] == 1
        assert timber_inside.bottom_position[1] == size[1] / 2
        assert timber_inside.bottom_position[2] == 0
        # Should be vertical
        assert timber_inside.length_direction[2] == 1
        # Face direction parallel to side
        assert timber_inside.face_direction[0] == 1
        assert timber_inside.face_direction[1] == 0
        
        # Test OUTSIDE positioning
        # One edge center is at the point, post extends outside (toward -Y)
        timber_outside = create_vertical_timber_on_footprint_side(
            footprint, 0, distance_along_side, post_height, TimberLocationType.OUTSIDE, size
        )
        
        assert timber_outside.length == Rational(3, 1)
        # For OUTSIDE, offset by half depth outward (toward -Y)
        assert timber_outside.bottom_position[0] == 1
        assert timber_outside.bottom_position[1] == -size[1] / 2
        assert timber_outside.bottom_position[2] == 0
        # Should be vertical
        assert timber_outside.length_direction[2] == 1
        # Face direction parallel to side
        assert timber_outside.face_direction[0] == 1
        assert timber_outside.face_direction[1] == 0
    
    def test_create_horizontal_timber_on_footprint(self):
        """Test horizontal timber creation on footprint."""
        corners = [
            create_vector2d(0.0, 0.0),
            create_vector2d(3.0, 0.0),
            create_vector2d(3.0, 4.0),
            create_vector2d(0.0, 4.0)
        ]
        footprint = Footprint(corners)
        
        # Default size for test
        size = create_vector2d(Rational(3, 10), Rational(3, 10))
        
        timber = create_horizontal_timber_on_footprint(
            footprint, 0, TimberLocationType.INSIDE, size, length=3.0
        )
        
        assert timber.length == 3.0
        # Should be horizontal in X direction
        assert timber.length_direction[0] == Float('1.0')
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
            footprint, 0, TimberLocationType.INSIDE, size, length=2.0
        )
        # Timber should extend inward (in +Y direction)
        # Bottom position Y should be half timber height (perpendicular dimension) inside the footprint
        # Note: getInwardNormal returns floats, so the result is Float
        assert timber_inside.bottom_position[1] == Float(timber_height / 2)
        assert timber_inside.bottom_position[0] == 0  # X unchanged
        assert timber_inside.bottom_position[2] == 0  # Z at ground
        
        # Test OUTSIDE positioning
        timber_outside = create_horizontal_timber_on_footprint(
            footprint, 0, TimberLocationType.OUTSIDE, size, length=2.0
        )
        # Timber should extend outward (in -Y direction)
        # Bottom position Y should be half timber height (perpendicular dimension) outside the footprint
        # Note: getInwardNormal returns floats, so the result is Float
        assert timber_outside.bottom_position[1] == Float(-timber_height / 2)
        assert timber_outside.bottom_position[0] == 0  # X unchanged
        assert timber_outside.bottom_position[2] == 0  # Z at ground
        
        # Test CENTER positioning
        timber_center = create_horizontal_timber_on_footprint(
            footprint, 0, TimberLocationType.CENTER, size, length=2.0
        )
        # Centerline should be on the boundary side
        assert float(timber_center.bottom_position[1]) == 0.0  # Y on boundary
        assert float(timber_center.bottom_position[0]) == 0.0  # X unchanged
        assert float(timber_center.bottom_position[2]) == 0.0  # Z at ground
        
        # Verify all timbers have correct length direction (along +X for bottom side)
        assert float(timber_inside.length_direction[0]) == 1.0
        assert float(timber_inside.length_direction[1]) == 0.0
        assert float(timber_inside.length_direction[2]) == 0.0
        
        assert float(timber_outside.length_direction[0]) == 1.0
        assert float(timber_outside.length_direction[1]) == 0.0
        assert float(timber_outside.length_direction[2]) == 0.0
        
        assert float(timber_center.length_direction[0]) == 1.0
        assert float(timber_center.length_direction[1]) == 0.0
        assert float(timber_center.length_direction[2]) == 0.0
        
        # Test right boundary side (from corner 1 to corner 2)
        # This side has inward normal pointing left: (-1, 0, 0)
        
        timber_inside_right = create_horizontal_timber_on_footprint(
            footprint, 1, TimberLocationType.INSIDE, size, length=2.0
        )
        # Timber should extend inward (in -X direction)
        # Use timber_height (size[1]) as it's the dimension perpendicular to boundary
        assert timber_inside_right.bottom_position[0] == Float(2.0 - timber_height / 2)
        assert float(timber_inside_right.bottom_position[1]) == 0.0  # Y unchanged
        
        timber_outside_right = create_horizontal_timber_on_footprint(
            footprint, 1, TimberLocationType.OUTSIDE, size, length=2.0
        )
        # Timber should extend outward (in +X direction)
        # Use timber_height (size[1]) as it's the dimension perpendicular to boundary
        assert timber_outside_right.bottom_position[0] == Float(2.0 + timber_height / 2)
        assert float(timber_outside_right.bottom_position[1]) == 0.0  # Y unchanged
        
        timber_center_right = create_horizontal_timber_on_footprint(
            footprint, 1, TimberLocationType.CENTER, size, length=2.0
        )
        # Centerline should be on the boundary side
        assert float(timber_center_right.bottom_position[0]) == 2.0  # X on boundary
        assert float(timber_center_right.bottom_position[1]) == 0.0  # Y unchanged
    
    def test_create_timber_extension(self):
        """Test timber extension creation with correct length calculation."""
        # Create a vertical timber from Z=0 to Z=10
        original_timber = Timber(
            length=10.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),  # Vertical (up)
            face_direction=create_vector3d(1.0, 0.0, 0.0)     # East
        )
        
        # Extend from top with 2 units of overlap and 5 units of extension
        # overlap_length = 2.0 (overlaps with last 2 units of original timber)
        # extend_length = 5.0 (extends 5 units beyond the end)
        extended = create_timber_extension(
            original_timber, 
            TimberReferenceEnd.TOP, 
            overlap_length=2.0, 
            extend_length=5.0
        )
        
        # Verify length: original_length + extend_length + overlap_length
        # = 10.0 + 5.0 + 2.0 = 17.0
        assert extended.length == 17.0, f"Expected length 17.0, got {extended.length}"
        
        # Verify bottom position moved up by (original_length - overlap_length)
        # = 0.0 + (10.0 - 2.0) = 8.0
        assert float(extended.bottom_position[2]) == 8.0, \
            f"Expected bottom Z at 8.0, got {float(extended.bottom_position[2])}"


class TestJointConstruction:
    """Test joint construction functions."""
    
    def test_simple_mortise_and_tenon_joint_on_face_aligned_timbers(self):
        """Test simple mortise and tenon joint creation for face-aligned timbers."""
        mortise_timber = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),
            face_direction=create_vector3d(0.0, 1.0, 0.0)
        )
        
        tenon_timber = Timber(
            length=2.0,
            size=create_vector2d(0.15, 0.15),
            bottom_position=create_vector3d(0.0, 0.0, 0.5),
            length_direction=create_vector3d(0.0, 0.0, 1.0),
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
            mortise_timber, tenon_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            tenon_thickness=0.05,
            tenon_length=0.1
        )
        
        assert isinstance(joint, Joint)
        assert len(joint.timber_cuts) == 2
        # Check that both timbers are included
        timbers = [cut[0] for cut in joint.timber_cuts]
        assert mortise_timber in timbers
        assert tenon_timber in timbers


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_timber_face_to_vector(self):
        """Test TimberFace to vector conversion."""
        # Test all faces
        top = _timber_face_to_vector(TimberFace.TOP)
        assert float(top[2]) == 1.0
        
        bottom = _timber_face_to_vector(TimberFace.BOTTOM)
        assert float(bottom[2]) == -1.0
        
        right = _timber_face_to_vector(TimberFace.RIGHT)
        assert float(right[0]) == 1.0
        
        left = _timber_face_to_vector(TimberFace.LEFT)
        assert float(left[0]) == -1.0
        
        forward = _timber_face_to_vector(TimberFace.FORWARD)
        assert float(forward[1]) == 1.0
        
        back = _timber_face_to_vector(TimberFace.BACK)
        assert float(back[1]) == -1.0


class TestJoinTimbers:
    """Test timber joining functions."""
    
    def test_join_timbers_basic(self):
        """Test basic timber joining."""
        timber1 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),  # Vertical
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        timber2 = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(2.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),  # Vertical
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=1.5,  # Midpoint of timber1
            stickout=Stickout(0.1, 0.1),  # Symmetric stickout
            offset_from_timber1=0.0,
            location_on_timber2=1.0   # Explicit position on timber2
        )
        
        assert isinstance(joining_timber, Timber)
        # Length direction should be from pos1=[0,0,1.5] to pos2=[2,0,1.0], so direction=[2,0,-0.5]
        # Normalized: [0.970, 0, -0.243] approximately
        length_dir = joining_timber.length_direction
        assert abs(float(length_dir[0]) - 0.970) < 0.1  # X component ~0.97
        assert abs(float(length_dir[1])) < 0.1          # Y component ~0
        assert abs(float(length_dir[2]) + 0.243) < 0.1  # Z component ~-0.24
        
        # Face direction should be orthogonal to length direction
        # With improved orthogonalization, this should be Y axis [0, 1, 0]
        face_dir = joining_timber.face_direction
        assert abs(float(face_dir[0])) < 0.1        # X component should be ~0
        assert abs(float(face_dir[1]) - 1.0) < 0.1  # Y component should be ~1
        assert abs(float(face_dir[2])) < 0.1        # Z component should be ~0
        
        # Verify the joining timber is positioned correctly
        # pos1 = [0, 0, 1.5] (location 1.5 on timber1), pos2 = [2, 0, 1.0] (location 1.0 on timber2)
        # center would be [1, 0, 1.25], but bottom_position is at the start of the timber
        # The timber should span from one connection point to the other with stickout
        
        # Check that the timber actually spans the connection points correctly
        # The timber should start before pos1 and end after pos2 (or vice versa)
        timber_start = joining_timber.bottom_position
        timber_end = joining_timber.get_position_on_timber(joining_timber.length)
        
        # Verify timber spans the connection region
        assert float(joining_timber.length) > 2.0  # Should be longer than just the span between points

    # helper function to create 2 parallel timbers 
    def make_parallel_timbers(self):
        timber1 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),  # Horizontal in X
            face_direction=create_vector3d(0.0, 0.0, 1.0)     # Up
        )
        
        timber2 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 2.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),  # Parallel to timber1
            face_direction=create_vector3d(0.0, 0.0, 1.0)
        )

        return timber1, timber2
    
    def test_join_perpendicular_on_face_aligned_timbers_position_is_correct(self):
        """Test perpendicular joining of face-aligned timbers."""
        timber1, timber2 = self.make_parallel_timbers()
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )

        joining_timber2 = join_perpendicular_on_face_aligned_timbers(
            timber1, timber2,
            location_on_timber1=1.5,
            stickout=Stickout(0, 0),  # No stickout
            offset_from_timber1=offset,
            size=create_vector2d(0.15, 0.15),
            orientation_face_on_timber1=TimberFace.TOP
        )
   
        assert joining_timber2.bottom_position == timber1.get_position_on_timber(1.5)
        print(joining_timber2.orientation)
        
        
    def test_join_perpendicular_on_face_aligned_timbers_length_is_correct(self):
        """Test perpendicular joining of face-aligned timbers."""
        timber1, timber2 = self.make_parallel_timbers()
        
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        joining_timber2 = join_perpendicular_on_face_aligned_timbers(
            timber1, timber2,
            location_on_timber1=1.5,
            stickout=Stickout(1.2, 1.2),  # Symmetric stickout
            offset_from_timber1=offset,
            size=create_vector2d(0.15, 0.15),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        assert isinstance(joining_timber2, Timber)
        # Length should be centerline distance (2.0) + stickout1 (1.2) + stickout2 (1.2) = 4.4
        assert abs(joining_timber2.length - 4.4) < 1e-10
    
    def test_join_perpendicular_on_face_aligned_timbers_assertion(self):
        """Test that join_perpendicular_on_face_aligned_timbers asserts when timbers are not face-aligned."""
        import pytest
        
        # Create two timbers that are NOT face-aligned
        # Timber1: vertical, facing east
        timber1 = Timber(
            length=3.0,
            size=create_vector2d(0.15, 0.15),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0, 0, 1),  # Vertical
            face_direction=create_vector3d(1, 0, 0)     # East
        )
        
        # Timber2: diagonal at 45 degrees, not aligned with timber1's coordinate grid
        timber2 = Timber(
            length=3.0,
            size=create_vector2d(0.15, 0.15),
            bottom_position=create_vector3d(2.0, 2.0, 0.0),
            length_direction=create_vector3d(1, 1, 0),  # 45 degrees in XY plane (will be normalized)
            face_direction=create_vector3d(0, 0, 1)     # Up
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
            join_perpendicular_on_face_aligned_timbers(
                timber1, timber2,
                location_on_timber1=1.5,
                stickout=Stickout(0.0, 0.0),
                offset_from_timber1=offset,
                size=create_vector2d(0.15, 0.15),
                orientation_face_on_timber1=TimberFace.TOP
            )

    def test_join_timbers_creates_orthogonal_rotation_matrix(self):
        """Test that join_timbers creates valid orthogonal orientation matrices."""
        # Create two non-parallel timbers to ensure non-trivial orientation
        # Use exact integer/rational inputs for exact SymPy results
        timber1 = Timber(
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            bottom_position=create_vector3d(Rational(-1, 2), 0, 0),  # Exact rationals
            length_direction=create_vector3d(0, 0, 1),  # Integers (vertical)
            face_direction=create_vector3d(1, 0, 0)     # Integers
        )
        
        timber2 = Timber(
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            bottom_position=create_vector3d(Rational(1, 2), 0, 0),   # Exact rationals
            length_direction=create_vector3d(0, 1, 0),  # Integers (horizontal north)
            face_direction=create_vector3d(0, 0, 1)     # Integers
        )
        
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational(1, 2),     # Exact rational
            stickout=Stickout(Rational(1, 10), Rational(1, 10)),  # Exact symmetric stickout
            offset_from_timber1=0,                  # Integer
            location_on_timber2=Rational(1, 2)     # Exact rational
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
        face_dir = joining_timber.face_direction  
        height_dir = joining_timber.height_direction
        
        assert simplify(length_dir.norm() - 1) == 0, "Length direction should be unit vector"
        assert simplify(face_dir.norm() - 1) == 0, "Face direction should be unit vector"
        assert simplify(height_dir.norm() - 1) == 0, "Height direction should be unit vector"
        
        # Verify directions are orthogonal to each other (exact SymPy comparison)
        assert simplify(length_dir.dot(face_dir)) == 0, "Length and face directions should be orthogonal"
        assert simplify(length_dir.dot(height_dir)) == 0, "Length and height directions should be orthogonal"
        assert simplify(face_dir.dot(height_dir)) == 0, "Face and height directions should be orthogonal"

    def test_create_timber_creates_orthogonal_matrix(self):
        """Test that create_timber creates valid orthogonal orientation matrices."""
        # Test with arbitrary (but orthogonal) input directions using exact inputs
        length_dir = create_vector3d(1, 1, 0)  # Will be normalized (integers)
        face_dir = create_vector3d(0, 0, 1)    # Up direction (integers)
        
        timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            length_direction=length_dir,
            face_direction=face_dir
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
        length_dir = create_vector3d(2, 0, 1)         # Not orthogonal to face_dir (integers)
        face_dir = create_vector3d(0, 1, 2)           # Not orthogonal to length_dir (integers)
        
        timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            length_direction=length_dir,
            face_direction=face_dir
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
                face_direction=create_vector3d(0, 1, 0)     # All face north
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
            face_direction=create_vector3d(0, 1, 0)     # North facing
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
            joining_timber = join_perpendicular_on_face_aligned_timbers(
                timber1=base_timber,
                timber2=beam,
                location_on_timber1=location_on_base,
                stickout=Stickout(stickout, stickout),  # Symmetric stickout
                offset_from_timber1=offset,
                size=create_vector2d(Rational(8, 100), Rational(8, 100)),  # 8cm x 8cm posts
                orientation_face_on_timber1=TimberFace.TOP
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
            assert vertical_component > 0.8, f"Post_{i} should be mostly vertical, got length_direction={[float(x) for x in length_dir]}"
            
            # 2. Verify the joining timber connects to the correct position on the base timber
            expected_base_pos = base_timber.get_position_on_timber(location_used)
            
            # The joining timber should start from approximately the top face of the base timber
            expected_start_z = expected_base_pos[2] + base_timber.size[1]  # Top of base timber
            actual_start_z = joining_timber.bottom_position[2]
            
            # Use exact comparison for rational arithmetic - allow for stickout adjustments
            start_z_diff = abs(actual_start_z - expected_start_z)
            assert float(start_z_diff) < 0.2, f"Post_{i} should start near top of base timber, diff={float(start_z_diff)}"
            
            # 3. Verify the joining timber connects to the beam
            # The top of the joining timber should be near the beam
            joining_top = joining_timber.bottom_position + joining_timber.length_direction * joining_timber.length
            beam_bottom_z = beam.bottom_position[2]
            
            # Should connect somewhere on or near the beam - use exact comparison
            beam_connection_diff = abs(joining_top[2] - beam_bottom_z)
            assert float(beam_connection_diff) < 0.2, f"Post_{i} should connect near beam level, diff={float(beam_connection_diff)}"
            
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
            
            cross_timber = join_perpendicular_on_face_aligned_timbers(
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
            horizontal_component = (float(length_dir[0])**2 + float(length_dir[1])**2)**0.5
            assert horizontal_component > 0.8, f"Cross_{i} should be mostly horizontal for face-aligned horizontal timbers"
            
            # Should be at the same Z level as the base timbers (face-aligned)
            cross_z = cross_timber.bottom_position[2]
            expected_z = base_z + timber_size[1]  # Top face level of base timbers
            z_level_diff = abs(cross_z - expected_z)
            assert float(z_level_diff) <= 0.15, f"Cross_{i} should be at the same level as base timbers, diff={float(z_level_diff)}"
            
            # Verify orthogonality with tolerance for floating-point precision
            orientation_matrix = cross_timber.orientation.matrix
            product = orientation_matrix * orientation_matrix.T
            identity = Matrix.eye(3)
            diff_matrix = product - identity
            max_error = max([abs(float(diff_matrix[i, j])) for i in range(3) for j in range(3)])
            assert max_error < 1e-12, f"Cross_{i} orientation matrix should be orthogonal, max error: {max_error}"
        
        print(f"✅ Successfully tested {len(joining_timbers)} vertical posts and {len(cross_connections)} cross-connections")
        print(f"   All joining timbers maintain proper face alignment and orthogonal orientation matrices")


class TestTimberCutOperations:
    """Test timber cut operations."""
    
    def test_tenon_cut_operation(self):
        """Test tenon cut operation creation."""
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        tenon_spec = StandardTenon(
            shoulder_plane=ShoulderPlane.create(
                reference_end=TimberReferenceEnd.TOP,
                distance=0.05
            ),
            pos_rel_to_long_edge=None,
            width=0.04,
            height=0.04,
            length=0.06
        )
        
        cut_op = TenonCutOperation(timber, tenon_spec)
        
        assert cut_op.timber == timber
        assert cut_op.tenon_spec.width == 0.04
    
    def test_mortise_cut_operation(self):
        """Test mortise cut operation creation."""
        timber = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),
            face_direction=create_vector3d(0.0, 1.0, 0.0)
        )
        
        mortise_spec = StandardMortise(
            mortise_face=TimberFace.TOP,
            pos_rel_to_end=(TimberReferenceEnd.BOTTOM, 0.5),
            pos_rel_to_long_face=(TimberReferenceLongFace.RIGHT, 0.1),
            width=0.04,
            height=0.06,
            depth=0.08
        )
        
        cut_op = MortiseCutOperation(timber, mortise_spec)
        
        assert cut_op.timber == timber
        assert cut_op.mortise_spec.width == 0.04


class TestEnumsAndDataStructures:
    """Test enums and data structures."""
    
    def test_timber_location_type_enum(self):
        """Test TimberLocationType enum."""
        assert TimberLocationType.INSIDE.value == 1
        assert TimberLocationType.CENTER.value == 2
        assert TimberLocationType.OUTSIDE.value == 3
    
    def test_timber_face_enum(self):
        """Test TimberFace enum."""
        assert TimberFace.TOP.value == 1
        assert TimberFace.BOTTOM.value == 2
        assert TimberFace.RIGHT.value == 3
        assert TimberFace.FORWARD.value == 4
        assert TimberFace.LEFT.value == 5
        assert TimberFace.BACK.value == 6
    
    def test_standard_tenon_dataclass(self):
        """Test StandardTenon dataclass."""
        shoulder_plane = ShoulderPlane.create(
            reference_end=TimberReferenceEnd.TOP,
            distance=0.1
        )
        
        tenon = StandardTenon(
            shoulder_plane=shoulder_plane,
            pos_rel_to_long_edge=None,
            width=0.05,
            height=0.05,
            length=0.08
        )
        
        assert tenon.width == 0.05
        assert tenon.height == 0.05
        assert tenon.length == 0.08
    
    def test_face_aligned_joined_timber_offset(self):
        """Test FaceAlignedJoinedTimberOffset dataclass."""
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=0.05,
            face_offset=0.02
        )
        
        assert offset.reference_face == TimberFace.TOP
        assert offset.centerline_offset == 0.05
        assert offset.face_offset == 0.02
    
    def test_shoulder_plane_create_method(self):
        """Test ShoulderPlane.create method with automatic normal determination."""
        # Test TOP reference_end - should get upward normal
        plane_top = ShoulderPlane.create(
            reference_end=TimberReferenceEnd.TOP,
            distance=0.1
        )
        
        assert plane_top.reference_end == TimberReferenceEnd.TOP
        assert plane_top.distance == 0.1
        assert plane_top.normal == create_vector3d(0, 0, 1)  # Upward
        
        # Test BOTTOM reference_end - should get downward normal
        plane_bottom = ShoulderPlane.create(
            reference_end=TimberReferenceEnd.BOTTOM,
            distance=0.05
        )
        
        assert plane_bottom.reference_end == TimberReferenceEnd.BOTTOM
        assert plane_bottom.distance == 0.05
        assert plane_bottom.normal == create_vector3d(0, 0, -1)  # Downward
        
        # Test with explicit normal - should use provided normal
        custom_normal = create_vector3d(1, 0, 0)
        plane_custom = ShoulderPlane.create(
            reference_end=TimberReferenceEnd.TOP,
            distance=0.2,
            normal=custom_normal
        )
        
        assert plane_custom.reference_end == TimberReferenceEnd.TOP
        assert plane_custom.distance == 0.2
        assert plane_custom.normal == custom_normal
    
    
    def test_stickout_with_join_timbers(self):
        """Test that stickout produces correct timber length in join_timbers."""
        # Create two vertical posts 2.5 meters apart
        post1 = create_axis_aligned_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=2.0,
            size=create_vector2d(0.15, 0.15),
            length_direction=create_vector3d(0, 0, 1),
            face_direction=create_vector3d(1, 0, 0)
        )
        
        post2 = create_axis_aligned_timber(
            bottom_position=create_vector3d(2.5, 0, 0),
            length=2.0,
            size=create_vector2d(0.15, 0.15),
            length_direction=create_vector3d(0, 0, 1),
            face_direction=create_vector3d(1, 0, 0)
        )
        
        # Join with asymmetric stickout: 0.1m on post1 side, 0.3m on post2 side
        stickout1 = 0.1
        stickout2 = 0.3
        beam = join_timbers(
            timber1=post1,
            timber2=post2,
            location_on_timber1=1.0,
            stickout=Stickout(stickout1, stickout2),
            offset_from_timber1=0.0,
            location_on_timber2=1.0
        )
        
        # Expected length: distance between posts (2.5m) + stickout1 (0.1m) + stickout2 (0.3m)
        expected_length = 2.5 + stickout1 + stickout2
        assert abs(beam.length - expected_length) < 1e-10
        assert abs(beam.length - 2.9) < 1e-10
    
    def test_stickout_reference_assertions(self):
        """Test that join_timbers asserts when non-CENTER_LINE references are used."""
        import pytest
        from giraffe import StickoutReference
        
        # Create two posts 2.0 meters apart
        post1 = create_axis_aligned_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=2.0,
            size=create_vector2d(0.2, 0.2),
            length_direction=create_vector3d(0, 0, 1),
            face_direction=create_vector3d(1, 0, 0)
        )
        
        post2 = create_axis_aligned_timber(
            bottom_position=create_vector3d(2.0, 0, 0),
            length=2.0,
            size=create_vector2d(0.2, 0.2),
            length_direction=create_vector3d(0, 0, 1),
            face_direction=create_vector3d(1, 0, 0)
        )
        
        # Try to use INSIDE reference - should assert
        with pytest.raises(AssertionError, match="CENTER_LINE stickout reference"):
            join_timbers(
                timber1=post1,
                timber2=post2,
                location_on_timber1=1.0,
                stickout=Stickout(0.1, 0.1, StickoutReference.INSIDE, StickoutReference.CENTER_LINE),
                offset_from_timber1=0.0,
                location_on_timber2=1.0
            )
        
        # Try to use OUTSIDE reference - should assert
        with pytest.raises(AssertionError, match="CENTER_LINE stickout reference"):
            join_timbers(
                timber1=post1,
                timber2=post2,
                location_on_timber1=1.0,
                stickout=Stickout(0.1, 0.1, StickoutReference.CENTER_LINE, StickoutReference.OUTSIDE),
                offset_from_timber1=0.0,
                location_on_timber2=1.0
            )
    
    def test_stickout_reference_inside_face_aligned(self):
        """Test INSIDE stickout reference with face-aligned timbers."""
        from giraffe import StickoutReference, join_perpendicular_on_face_aligned_timbers, FaceAlignedJoinedTimberOffset, TimberFace
        
        # Create two parallel horizontal posts 2.0 meters apart
        post1 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),  # East
            face_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        post2 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0, 2, 0),  # 2m north
            length_direction=create_vector3d(1, 0, 0),  # East (parallel)
            face_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        # Join with INSIDE reference
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        beam = join_perpendicular_on_face_aligned_timbers(
            post1, post2,
            location_on_timber1=1.5,
            stickout=Stickout(0.1, 0.1, StickoutReference.INSIDE, StickoutReference.INSIDE),
            offset_from_timber1=offset,
            size=create_vector2d(0.2, 0.2),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        # Expected length: distance (2.0) + effective_stickout1 (0.1 + 0.1) + effective_stickout2 (0.1 + 0.1)
        # = 2.0 + 0.2 + 0.2 = 2.4
        assert abs(beam.length - 2.4) < 1e-10
    
    def test_stickout_reference_outside_face_aligned(self):
        """Test OUTSIDE stickout reference with face-aligned timbers."""
        from giraffe import StickoutReference, join_perpendicular_on_face_aligned_timbers, FaceAlignedJoinedTimberOffset, TimberFace
        
        # Create two parallel horizontal posts 2.0 meters apart
        post1 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),  # East
            face_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        post2 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0, 2, 0),  # 2m north
            length_direction=create_vector3d(1, 0, 0),  # East (parallel)
            face_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        # Join with OUTSIDE reference
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        beam = join_perpendicular_on_face_aligned_timbers(
            post1, post2,
            location_on_timber1=1.5,
            stickout=Stickout(0.2, 0.2, StickoutReference.OUTSIDE, StickoutReference.OUTSIDE),
            offset_from_timber1=offset,
            size=create_vector2d(0.2, 0.2),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        # Expected length: distance (2.0) + effective_stickout1 (0.2 - 0.1) + effective_stickout2 (0.2 - 0.1)
        # = 2.0 + 0.1 + 0.1 = 2.2
        assert abs(beam.length - 2.2) < 1e-10


class TestHelperFunctions:
    """Test helper functions for timber operations."""
    
    def test_find_aligned_face_axis_aligned_timber(self):
        """Test _find_aligned_face with axis-aligned timber."""
        # Create an axis-aligned timber (standard orientation)
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),  # width=0.2, height=0.3
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),  # Z-up (length)
            face_direction=create_vector3d(1, 0, 0)     # X-right (face/width)
        )
        
                # Test alignment with each cardinal direction
        # Note: CORRECTED timber coordinate system:
        # - TOP/BOTTOM faces are along length_direction (Z-axis)
        # - RIGHT/LEFT faces are along face_direction (X-axis)  
        # - FORWARD/BACK faces are along height_direction (Y-axis)

        # Target pointing in +Z (length direction) should align with TOP face
        target_length_pos = create_vector3d(0, 0, 1)
        aligned_face = _find_aligned_face(timber, target_length_pos)
        assert aligned_face == TimberFace.TOP

        # Target pointing in -Z (negative length direction) should align with BOTTOM face
        target_length_neg = create_vector3d(0, 0, -1)
        aligned_face = _find_aligned_face(timber, target_length_neg)
        assert aligned_face == TimberFace.BOTTOM

        # Target pointing in +X (face direction) should align with RIGHT face
        target_face_pos = create_vector3d(1, 0, 0)
        aligned_face = _find_aligned_face(timber, target_face_pos)
        assert aligned_face == TimberFace.RIGHT

        # Target pointing in -X (negative face direction) should align with LEFT face
        target_face_neg = create_vector3d(-1, 0, 0)
        aligned_face = _find_aligned_face(timber, target_face_neg)
        assert aligned_face == TimberFace.LEFT

        # Target pointing in +Y (height direction) should align with FORWARD face
        target_height_pos = create_vector3d(0, 1, 0)
        aligned_face = _find_aligned_face(timber, target_height_pos)
        assert aligned_face == TimberFace.FORWARD

        # Target pointing in -Y (negative height direction) should align with BACK face
        target_height_neg = create_vector3d(0, -1, 0)
        aligned_face = _find_aligned_face(timber, target_height_neg)
        assert aligned_face == TimberFace.BACK
    
    def test_find_aligned_face_rotated_timber(self):
        """Test _find_aligned_face with rotated timber."""
        # Create a timber rotated 90 degrees around Z axis
        # length_direction stays Z-up, but face_direction becomes Y-forward
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),  # Z-up (length)
            face_direction=create_vector3d(0, 1, 0)     # Y-forward (face/width)
        )
        
                # Now the timber's faces are rotated (CORRECTED):
        # TOP face points in +Z direction (length_direction)
        # BOTTOM face points in -Z direction (negative length_direction)
        # RIGHT face points in +Y direction (face_direction)
        # LEFT face points in -Y direction (negative face_direction)
        # FORWARD face points in -X direction (height_direction)
        # BACK face points in +X direction (negative height_direction)

        # Target pointing in +Y direction should align with RIGHT face
        target_y_pos = create_vector3d(0, 1, 0)
        aligned_face = _find_aligned_face(timber, target_y_pos)
        assert aligned_face == TimberFace.RIGHT

        # Target pointing in -Y direction should align with LEFT face
        target_y_neg = create_vector3d(0, -1, 0)
        aligned_face = _find_aligned_face(timber, target_y_neg)
        assert aligned_face == TimberFace.LEFT

        # Target pointing in -X direction should align with FORWARD face
        target_x_neg = create_vector3d(-1, 0, 0)
        aligned_face = _find_aligned_face(timber, target_x_neg)
        assert aligned_face == TimberFace.FORWARD

        # Target pointing in +X direction should align with BACK face
        target_x_pos = create_vector3d(1, 0, 0)
        aligned_face = _find_aligned_face(timber, target_x_pos)
        assert aligned_face == TimberFace.BACK
    
    def test_find_aligned_face_horizontal_timber(self):
        """Test _find_aligned_face with horizontal timber."""
        # Create a horizontal timber lying along X axis
        timber = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),   # X-right (length)
            face_direction=create_vector3d(0, 0, 1)      # Z-up (face/width)
        )
        
        # For this horizontal timber (CORRECTED):
        # TOP face points in +X direction (length_direction)
        # BOTTOM face points in -X direction (negative length_direction)
        # RIGHT face points in +Z direction (face_direction)
        # LEFT face points in -Z direction (negative face_direction)
        # FORWARD face points in -Y direction (height_direction)  
        # BACK face points in +Y direction (negative height_direction)
        
        # Target pointing in +Z should align with RIGHT face
        target_z_pos = create_vector3d(0, 0, 1)
        aligned_face = _find_aligned_face(timber, target_z_pos)
        assert aligned_face == TimberFace.RIGHT
        
        # Target pointing in -Z should align with LEFT face
        target_z_neg = create_vector3d(0, 0, -1)
        aligned_face = _find_aligned_face(timber, target_z_neg)
        assert aligned_face == TimberFace.LEFT
        
        # Target pointing in +X (length direction) should align with TOP face
        target_x_pos = create_vector3d(1, 0, 0)
        aligned_face = _find_aligned_face(timber, target_x_pos)
        assert aligned_face == TimberFace.TOP
        
        # Target pointing in +Y should align with BACK face
        target_y_pos = create_vector3d(0, 1, 0)
        aligned_face = _find_aligned_face(timber, target_y_pos)
        assert aligned_face == TimberFace.BACK
    
    def test_find_aligned_face_diagonal_target(self):
        """Test _find_aligned_face with diagonal target direction."""
        # Create an axis-aligned timber
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
                # Test with diagonal direction that's closer to +Z than +X
        # This should align with TOP face (Z-direction)
        target_diagonal_z = normalize_vector(create_vector3d(0.3, 0, 1))  # Mostly +Z, little bit +X
        aligned_face = _find_aligned_face(timber, target_diagonal_z)
        assert aligned_face == TimberFace.TOP

        # Test with diagonal direction that's closer to +X than +Z
        # This should align with RIGHT face (X-direction)
        target_diagonal_x = normalize_vector(create_vector3d(1, 0, 0.3))  # Mostly +X, little bit +Z
        aligned_face = _find_aligned_face(timber, target_diagonal_x)
        assert aligned_face == TimberFace.RIGHT
    
    def test_get_timber_face_direction(self):
        """Test _get_timber_face_direction helper function."""
        # Create an axis-aligned timber
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        # Test that face directions match expected values (CORRECTED MAPPING)
        top_dir = _get_timber_face_direction(timber, TimberFace.TOP)
        assert top_dir == timber.length_direction
        
        bottom_dir = _get_timber_face_direction(timber, TimberFace.BOTTOM)
        assert bottom_dir == -timber.length_direction
        
        right_dir = _get_timber_face_direction(timber, TimberFace.RIGHT)
        assert right_dir == timber.face_direction
        
        left_dir = _get_timber_face_direction(timber, TimberFace.LEFT)
        assert left_dir == -timber.face_direction
        
        # FORWARD should be the height direction
        forward_dir = _get_timber_face_direction(timber, TimberFace.FORWARD)
        assert forward_dir == timber.height_direction
        
        # BACK should be the negative height direction
        back_dir = _get_timber_face_direction(timber, TimberFace.BACK)
        assert back_dir == -timber.height_direction
    
    def test_get_tenon_end_direction(self):
        """Test _get_tenon_end_direction helper function."""
        # Create a timber
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        # Test TOP end direction
        top_dir = _get_tenon_end_direction(timber, TimberReferenceEnd.TOP)
        assert top_dir == timber.length_direction
        
        # Test BOTTOM end direction  
        bottom_dir = _get_tenon_end_direction(timber, TimberReferenceEnd.BOTTOM)
        assert bottom_dir == -timber.length_direction
    
    def test_are_timbers_face_parallel(self):
        """Test _are_timbers_face_parallel helper function."""
        # Create two timbers with parallel length directions
        timber1 = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        timber2 = Timber(
            length=3.0,
            size=create_vector2d(0.15, 0.25),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same direction
            face_direction=create_vector3d(0, 1, 0)      # Different face direction
        )
        
        # Should be parallel (parallel length directions)
        assert _are_timbers_face_parallel(timber1, timber2)
        
        # Create a timber with opposite direction (still parallel)
        timber3 = Timber(
            length=1.5,
            size=create_vector2d(0.1, 0.2),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, -1),  # Opposite direction
            face_direction=create_vector3d(1, 0, 0)
        )
        
        # Should still be parallel (anti-parallel is still parallel)
        assert _are_timbers_face_parallel(timber1, timber3)
        
        # Create a timber with perpendicular direction
        timber4 = Timber(
            length=2.5,
            size=create_vector2d(0.3, 0.3),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=create_vector3d(1, 0, 0),   # Perpendicular
            face_direction=create_vector3d(0, 0, 1)
        )
        
        # Should NOT be parallel
        assert not _are_timbers_face_parallel(timber1, timber4)
    
    def test_are_timbers_face_orthogonal(self):
        """Test _are_timbers_face_orthogonal helper function."""
        # Create two timbers with perpendicular length directions
        timber1 = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)      # X-right
        )
        
        timber2 = Timber(
            length=3.0,
            size=create_vector2d(0.15, 0.25),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(1, 0, 0),   # X-right (perpendicular to timber1)
            face_direction=create_vector3d(0, 0, 1)      # Z-up
        )
        
        # Should be orthogonal
        assert _are_timbers_face_orthogonal(timber1, timber2)
        
        # Create a timber with parallel direction
        timber3 = Timber(
            length=1.5,
            size=create_vector2d(0.1, 0.2),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same as timber1
            face_direction=create_vector3d(1, 0, 0)
        )
        
        # Should NOT be orthogonal
        assert not _are_timbers_face_orthogonal(timber1, timber3)
        
        # Test with Y-direction
        timber4 = Timber(
            length=2.5,
            size=create_vector2d(0.3, 0.3),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=create_vector3d(0, 1, 0),   # Y-forward (perpendicular to timber1)
            face_direction=create_vector3d(1, 0, 0)
        )
        
        # Should be orthogonal
        assert _are_timbers_face_orthogonal(timber1, timber4)
    
    def test_are_timbers_face_aligned(self):
        """Test _are_timbers_face_aligned helper function."""
        # Create a reference timber with standard orientation
        timber1 = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)      # X-right
        )
        # timber1 directions: length=[0,0,1], face=[1,0,0], height=[0,1,0]
        
        # Test 1: Timber with same orientation - should be face-aligned
        timber2 = Timber(
            length=3.0,
            size=create_vector2d(0.15, 0.25),
            bottom_position=create_vector3d(2, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same as timber1
            face_direction=create_vector3d(1, 0, 0)      # Same as timber1
        )
        assert _are_timbers_face_aligned(timber1, timber2)
        
        # Test 2: Timber rotated 90° around Z - should be face-aligned  
        # (length stays Z, but face becomes Y, height becomes -X)
        timber3 = Timber(
            length=1.5,
            size=create_vector2d(0.1, 0.2),
            bottom_position=create_vector3d(-1, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Same Z
            face_direction=create_vector3d(0, 1, 0)      # Y direction
        )
        assert _are_timbers_face_aligned(timber1, timber3)
        
        # Test 3: Timber rotated 90° around X - should be face-aligned
        # (length becomes -Y, face stays X, height becomes Z) 
        timber4 = Timber(
            length=2.5,
            size=create_vector2d(0.3, 0.3),
            bottom_position=create_vector3d(1, 1, 0),
            length_direction=create_vector3d(0, -1, 0),  # -Y direction
            face_direction=create_vector3d(1, 0, 0)      # Same X
        )
        assert _are_timbers_face_aligned(timber1, timber4)
        
        # Test 4: Timber with perpendicular orientation but face-aligned
        # (length becomes X, face becomes Z, height becomes Y)
        timber5 = Timber(
            length=1.8,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0, 2, 0),
            length_direction=create_vector3d(1, 0, 0),   # X direction  
            face_direction=create_vector3d(0, 0, 1)      # Z direction
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
            length=1.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0, 0, 2),
            length_direction=create_vector3d(sin45*cos30, sin45*sin30, cos45),  # Complex 3D direction
            face_direction=create_vector3d(cos45*cos30, cos45*sin30, -sin45)    # Perpendicular complex direction
        )
        assert not _are_timbers_face_aligned(timber1, timber6)
        
        # Test 6: Verify that 45° rotation in XY plane IS face-aligned 
        # (because height direction is still Z, parallel to timber1's length direction)
        cos45_xy = math.cos(math.pi/4)
        sin45_xy = math.sin(math.pi/4)
        timber7 = Timber(
            length=1.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0, 0, 2),
            length_direction=create_vector3d(cos45_xy, sin45_xy, 0),  # 45° in XY plane
            face_direction=create_vector3d(-sin45_xy, cos45_xy, 0)    # Perpendicular in XY
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
    
    def test_are_timbers_face_aligned_exact_equality(self):
        """Test _are_timbers_face_aligned with exact equality (no tolerance)."""
        # Create two face-aligned timbers using exact rational values
        timber1 = Timber(
            length=2,  # Integer
            size=create_vector2d(Rational(1, 5), Rational(3, 10)),  # Exact rationals
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length_direction=create_vector3d(0, 0, 1),   # Vertical - integers
            face_direction=create_vector3d(1, 0, 0)      # East - integers
        )
        
        timber2 = Timber(
            length=3,  # Integer
            size=create_vector2d(Rational(3, 20), Rational(1, 4)),  # Exact rationals
            bottom_position=create_vector3d(2, 0, 0),  # Integers
            length_direction=create_vector3d(1, 0, 0),   # East (perpendicular to timber1) - integers
            face_direction=create_vector3d(0, 0, 1)      # Up - integers
        )
        
        # These should be face-aligned with exact equality (no tolerance)
        assert _are_timbers_face_aligned(timber1, timber2, tolerance=None)
        
        # Create a non-face-aligned timber (diagonal)
        timber3 = Timber(
            length=2,  # Integer
            size=create_vector2d(Rational(1, 5), Rational(1, 5)),  # Exact rationals
            bottom_position=create_vector3d(3, 3, 0),  # Integers
            length_direction=create_vector3d(1, 1, 0),   # 45° diagonal (will be normalized to Float)
            face_direction=create_vector3d(0, 0, 1)      # Up - integers
        )
        
        # timber1 and timber3 should NOT be face-aligned
        # Note: This will trigger a warning because timber3's normalized length_direction contains Float values
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
            length=4.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(1, 2, 0),    # Offset from origin
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)
        )
        
        # Test point directly on the centerline
        point_on_line = create_vector3d(1, 2, 2)  # 2 units up from bottom
        t, projected = _project_point_on_timber_centerline(point_on_line, timber)
        
        assert abs(t - 2.0) < 1e-10  # Should be 2 units along timber
        assert (projected - point_on_line).norm() < 1e-10  # Should project to itself
        
        # Test point off the centerline
        point_off_line = create_vector3d(3, 5, 1.5)  # 1.5 units up, but offset in X and Y
        t, projected = _project_point_on_timber_centerline(point_off_line, timber)
        
        assert abs(t - 1.5) < 1e-10  # Should be 1.5 units along timber
        expected_projection = create_vector3d(1, 2, 1.5)  # On centerline at same Z
        assert (projected - expected_projection).norm() < 1e-10
        
        # Test point before timber start (negative t)
        point_before = create_vector3d(1, 2, -1)  # 1 unit below bottom
        t, projected = _project_point_on_timber_centerline(point_before, timber)
        
        assert abs(t - (-1.0)) < 1e-10  # Should be -1 units
        assert (projected - point_before).norm() < 1e-10
        
        # Test point beyond timber end
        point_beyond = create_vector3d(1, 2, 5)  # 5 units up (beyond length of 4)
        t, projected = _project_point_on_timber_centerline(point_beyond, timber)
        
        assert abs(t - 5.0) < 1e-10  # Should be 5 units
        assert (projected - point_beyond).norm() < 1e-10
    
    def test_calculate_mortise_position_from_tenon_intersection(self):
        """Test _calculate_mortise_position_from_tenon_intersection helper function."""
        # Create a vertical mortise timber (post)
        mortise_timber = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(0, 0, 1),   # Z-up
            face_direction=create_vector3d(1, 0, 0)
        )
        
        # Create a horizontal tenon timber (beam) that intersects the post
        tenon_timber = Timber(
            length=2.0,
            size=create_vector2d(0.15, 0.25),
            bottom_position=create_vector3d(-0.5, 0, 1.5),  # Starts at X=-0.5, intersects post at Z=1.5
            length_direction=create_vector3d(1, 0, 0),    # X-right
            face_direction=create_vector3d(0, 0, 1)
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
        assert abs(distance - 1.5) < 1e-10
        
        # Test with TOP end of tenon timber  
        ref_end, distance = _calculate_mortise_position_from_tenon_intersection(
            mortise_timber, tenon_timber, TimberReferenceEnd.TOP
        )
        
        # The tenon TOP is at (1.5, 0, 1.5), which also projects to (0, 0, 1.5) on the mortise centerline
        # Same result as above
        assert ref_end == TimberReferenceEnd.BOTTOM
        assert abs(distance - 1.5) < 1e-10
        
        # Test with tenon closer to mortise top
        tenon_timber_high = Timber(
            length=2.0,
            size=create_vector2d(0.15, 0.25),
            bottom_position=create_vector3d(-0.5, 0, 2.8),  # Higher intersection
            length_direction=create_vector3d(1, 0, 0),
            face_direction=create_vector3d(0, 0, 1)
        )
        
        ref_end, distance = _calculate_mortise_position_from_tenon_intersection(
            mortise_timber, tenon_timber_high, TimberReferenceEnd.BOTTOM
        )
        
        # Intersection at Z=2.8, distance from bottom=2.8, distance from top=0.2
        # Should reference from TOP since it's closer
        assert ref_end == TimberReferenceEnd.TOP
        assert abs(distance - 0.2) < 1e-10
