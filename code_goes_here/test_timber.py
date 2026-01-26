"""
Tests for GiraffeCAD timber framing system
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs, Float, Rational
from code_goes_here.moothymoth import Orientation
from giraffe import *
from .testing_shavings import (
    create_standard_vertical_timber,
    create_standard_horizontal_timber,
    assert_is_valid_rotation_matrix,
    assert_vectors_perpendicular,
    assert_vectors_parallel,
    assert_vector_normalized,
    MockCut
)


# ============================================================================
# Tests for timber.py - Types, Enums, Constants, and Core Classes
# ============================================================================

class TestVectorHelpers:
    """Test vector helper functions."""
    
    def test_create_v2(self):
        """Test 2D vector creation."""
        v = create_v2(Rational(3, 2), Rational(5, 2))  # 1.5, 2.5 as exact rationals
        assert v.shape == (2, 1)
        assert v[0] == Rational(3, 2)
        assert v[1] == Rational(5, 2)
    
    def test_create_v3(self):
        """Test 3D vector creation."""
        v = create_v3(1, 2, 3)  # Use exact integers
        assert v.shape == (3, 1)
        assert v[0] == 1
        assert v[1] == 2
        assert v[2] == 3
    
    def test_normalize_vector(self):
        """Test vector normalization."""
        v = create_v3(3, 4, 0)  # Use integers for exact computation
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
        v = create_v3(0, 0, 0)  # Use exact integers
        normalized = normalize_vector(v)
        assert normalized == v  # Should return original zero vector
    
    def test_cross_product(self):
        """Test cross product calculation."""
        v1 = create_v3(1, 0, 0)  # Use exact integers
        v2 = create_v3(0, 1, 0)  # Use exact integers
        cross = cross_product(v1, v2)
        
        expected = create_v3(0, 0, 1)  # Use exact integers
        assert cross[0] == 0
        assert cross[1] == 0
        assert cross[2] == 1
    
    def test_vector_magnitude(self):
        """Test vector magnitude calculation."""
        v = create_v3(3, 4, 0)  # Use integers for exact computation
        magnitude = vector_magnitude(v)
        assert magnitude == 5



class TestTimber:
    """Test Timber class."""
    
    def test_timber_creation(self):
        """Test basic timber creation."""
        length = 3  # Use exact integer
        size = create_v2(Rational(1, 10), Rational(1, 10))  # 0.1 as exact rational
        position = create_v3(0, 0, 0)  # Use exact integers
        length_dir = create_v3(0, 0, 1)  # Use exact integers
        width_dir = create_v3(1, 0, 0)   # Use exact integers
        
        timber = timber_from_directions(length, size, position, length_dir, width_dir)
        
        assert timber.length == 3
        assert timber.size.shape == (2, 1)
        assert timber.get_bottom_position_global().shape == (3, 1)
        assert isinstance(timber.orientation, Orientation)
    
    def test_timber_orientation_computation(self):
        """Test that timber orientation is computed correctly."""
        # Create vertical timber facing east
        timber = create_standard_vertical_timber(height=2, size=(0.1, 0.1), position=(0, 0, 0))
        
        # Check that orientation matrix is reasonable
        matrix = timber.orientation.matrix
        assert matrix.shape == (3, 3)
        
        # Check that it's a valid rotation matrix
        assert_is_valid_rotation_matrix(matrix)
    
    def test_get_transform_matrix(self):
        """Test 4x4 transformation matrix generation."""
        timber = create_standard_vertical_timber(height=1, size=(0.1, 0.1), position=(1, 2, 3))
        
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
        input_length_dir = create_v3(0, 0, 1)  # Up - exact integers
        input_width_dir = create_v3(1, 0, 0)    # East - exact integers
        
        timber = timber_from_directions(
            length=2,  # Use exact integer
            size=create_v2(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_v3(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            width_direction=input_width_dir
        )
        
        # Verify that the property getters return the correct normalized directions
        length_dir = timber.get_length_direction_global()
        width_dir = timber.get_width_direction_global()
        height_dir = timber.get_height_direction_global()
        
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
        input_length_dir = create_v3(0, 1, 0)  # North - exact integers
        input_width_dir = create_v3(0, 0, 1)    # Up - exact integers
        
        timber = timber_from_directions(
            length=3,  # Use exact integer
            size=create_v2(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_v3(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            width_direction=input_width_dir
        )
        
        length_dir = timber.get_length_direction_global()
        width_dir = timber.get_width_direction_global()
        height_dir = timber.get_height_direction_global()
        
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
        timber = timber_from_directions(
            length=Rational(1),
            size=create_v2(Rational("0.1"), Rational("0.1")),
            bottom_position=create_v3(Rational(0), Rational(0), Rational(0)),
            length_direction=create_v3(Rational(1), Rational(1), Rational(0)),  # Non-axis-aligned
            width_direction=create_v3(Rational(0), Rational(0), Rational(1))     # Up
        )
        
        length_dir = timber.get_length_direction_global()
        width_dir = timber.get_width_direction_global()
        height_dir = timber.get_height_direction_global()
        
        # Check that each vector has unit length
        assert_vector_normalized(length_dir)
        assert_vector_normalized(width_dir)
        assert_vector_normalized(height_dir)
        
        # Check that vectors are orthogonal
        assert_vectors_perpendicular(length_dir, width_dir)
        assert_vectors_perpendicular(length_dir, height_dir)
        assert_vectors_perpendicular(width_dir, height_dir)
    
    def test_orientation_handles_non_normalized_inputs(self):
        """Test that orientation computation works with non-normalized input vectors."""
        # Use vectors that aren't unit length
        input_length_dir = create_v3(Rational(0), Rational(0), Rational(5))  # Up, but length 5
        input_width_dir = create_v3(Rational(3), Rational(0), Rational(0))    # East, but length 3
        
        timber = timber_from_directions(
            length=Rational(1),
            size=create_v2(Rational("0.1"), Rational("0.1")),
            bottom_position=create_v3(Rational(0), Rational(0), Rational(0)),
            length_direction=input_length_dir,
            width_direction=input_width_dir
        )
        
        # Despite non-normalized inputs, the output should be normalized
        length_dir = timber.get_length_direction_global()
        width_dir = timber.get_width_direction_global()
        
        # Check that directions are normalized (can be Rational(1) or Float(1))
        assert length_dir[0] == 0
        assert length_dir[1] == 0
        assert length_dir[2] == 1
        
        assert width_dir[0] == 1
        assert width_dir[1] == 0
        assert width_dir[2] == 0
    
    def test_get_centerline_position_from_bottom_global(self):
        """Test the get_centerline_position_from_bottom method."""
        timber = timber_from_directions(
            length=Rational(5),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(Rational(1), Rational(2), Rational(3)),
            length_direction=create_v3(Rational(0), Rational(1), Rational(0)),  # North
            width_direction=create_v3(Rational(0), Rational(0), Rational(1))     # Up
        )
        
        # Test at bottom position (position = 0)
        pos_at_bottom = timber.get_centerline_position_from_bottom_global(Rational(0))
        assert pos_at_bottom[0] == 1
        assert pos_at_bottom[1] == 2
        assert pos_at_bottom[2] == 3
        
        # Test at midpoint (position = 2.5)
        pos_at_middle = timber.get_centerline_position_from_bottom_global(Rational("2.5"))
        assert pos_at_middle[0] == 1
        assert pos_at_middle[1] == Rational("4.5")  # 2.0 + 2.5 * 1.0
        assert pos_at_middle[2] == 3
        
        # Test at top (position = 5.0)
        pos_at_top = timber.get_centerline_position_from_bottom_global(Rational(5))
        assert pos_at_top[0] == 1
        assert pos_at_top[1] == 7  # 2.0 + 5.0 * 1.0
        assert pos_at_top[2] == 3
        
        # Test with negative position (beyond bottom)
        pos_neg = timber.get_centerline_position_from_bottom_global(-Rational(1))
        assert pos_neg[0] == 1
        assert pos_neg[1] == 1  # 2.0 + (-1.0) * 1.0
        assert pos_neg[2] == 3
    
    def test_get_centerline_position_from_bottom_global(self):
        """Test get_centerline_position_from_bottom method."""
        timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(Rational(1), Rational(2), Rational(3)),
            length_direction=create_v3(Rational(0), Rational(0), Rational(1)),  # Up
            width_direction=create_v3(Rational(1), Rational(0), Rational(0))     # East
        )
        
        # Test position at bottom (0)
        pos_bottom = timber.get_centerline_position_from_bottom_global(Rational(0))
        assert pos_bottom[0] == 1
        assert pos_bottom[1] == 2
        assert pos_bottom[2] == 3
        
        # Test position at 3.0 from bottom
        pos_3 = timber.get_centerline_position_from_bottom_global(Rational(3))
        assert pos_3[0] == 1
        assert pos_3[1] == 2
        assert pos_3[2] == 6  # 3.0 + 3.0
        
        # Test position at top (10)
        pos_top = timber.get_centerline_position_from_bottom_global(Rational(10))
        assert pos_top[0] == 1
        assert pos_top[1] == 2
        assert pos_top[2] == 13  # 3.0 + 10.0
    
    def test_get_centerline_position_from_top_global(self):
        """Test get_centerline_position_from_top method."""
        timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(Rational(1), Rational(2), Rational(3)),
            length_direction=create_v3(Rational(0), Rational(0), Rational(1)),  # Up
            width_direction=create_v3(Rational(1), Rational(0), Rational(0))     # East
        )
        
        # Test position at top (0 from top = 10 from bottom)
        pos_top = timber.get_centerline_position_from_top_global(Rational(0))
        assert pos_top[0] == 1
        assert pos_top[1] == 2
        assert pos_top[2] == 13  # 3.0 + 10.0
        
        # Test position at 3.0 from top (= 7.0 from bottom)
        pos_3 = timber.get_centerline_position_from_top_global(Rational(3))
        assert pos_3[0] == 1
        assert pos_3[1] == 2
        assert pos_3[2] == 10  # 3.0 + 7.0
        
        # Test at bottom (10 from top = 0 from bottom)
        pos_bottom = timber.get_centerline_position_from_top_global(Rational(10))
        assert pos_bottom[0] == 1
        assert pos_bottom[1] == 2
        assert pos_bottom[2] == 3  # 3.0 + 0.0

    def test_get_size_in_face_normal_axis(self):
        """Test get_size_in_face_normal_axis method returns correct dimensions for each face."""
        # Create a timber with distinct dimensions:
        # length = 10, width (size[0]) = 0.2, height (size[1]) = 0.3
        timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(Rational(0), Rational(0), Rational(0)),
            length_direction=create_v3(Rational(0), Rational(0), Rational(1)),  # Up (Z-axis)
            width_direction=create_v3(Rational(1), Rational(0), Rational(0))     # East (X-axis)
        )
        
        # TOP and BOTTOM faces are perpendicular to the length direction (Z-axis)
        # So they should return the length
        assert timber.get_size_in_face_normal_axis(TimberFace.TOP) == Rational(10)
        assert timber.get_size_in_face_normal_axis(TimberFace.BOTTOM) == Rational(10)
        
        # RIGHT and LEFT faces are perpendicular to the width direction (X-axis)
        # So they should return the width (size[0])
        assert timber.get_size_in_face_normal_axis(TimberFace.RIGHT) == Rational("0.2")
        assert timber.get_size_in_face_normal_axis(TimberFace.LEFT) == Rational("0.2")
        
        # FRONT and BACK faces are perpendicular to the height direction (Y-axis)
        # So they should return the height (size[1])
        assert timber.get_size_in_face_normal_axis(TimberFace.FRONT) == Rational("0.3")
        assert timber.get_size_in_face_normal_axis(TimberFace.BACK) == Rational("0.3")


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
        assert TimberFace.FRONT.value == 4
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
        post1 = create_standard_vertical_timber(height=2, size=(0.15, 0.15), position=(0, 0, 0))
        post2 = create_standard_vertical_timber(height=2, size=(0.15, 0.15), position=(2.5, 0, 0))
        
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
        post1 = create_standard_vertical_timber(height=2, size=(0.2, 0.2), position=(0, 0, 0))
        post2 = create_standard_vertical_timber(height=2, size=(0.2, 0.2), position=(2, 0, 0))
        
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
        post1 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.2"), Rational("0.2")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # East
            width_direction=create_v3(0, 0, 1)     # Up
        )
        
        post2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.2"), Rational("0.2")),
            bottom_position=create_v3(0, 2, 0),  # 2m north
            length_direction=create_v3(1, 0, 0),  # East (parallel)
            width_direction=create_v3(0, 0, 1)     # Up
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
            size=create_v2(Rational("0.2"), Rational("0.2")),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        # Expected length: distance (2.0) + effective_stickout1 (0.1 + 0.1) + effective_stickout2 (0.1 + 0.1)
        # = 2.0 + 0.2 + 0.2 = 2.4
        assert abs(beam.length - Rational("2.4")) < 1e-10
    
    def test_stickout_reference_outside_face_aligned(self):
        """Test OUTSIDE stickout reference with face-aligned timbers."""
        from giraffe import StickoutReference, join_perpendicular_on_face_parallel_timbers, FaceAlignedJoinedTimberOffset, TimberFace
        
        # Create two parallel horizontal posts 2.0 meters apart
        post1 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.2"), Rational("0.2")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # East
            width_direction=create_v3(0, 0, 1)     # Up
        )
        
        post2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.2"), Rational("0.2")),
            bottom_position=create_v3(0, 2, 0),  # 2m north
            length_direction=create_v3(1, 0, 0),  # East (parallel)
            width_direction=create_v3(0, 0, 1)     # Up
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
            size=create_v2(Rational("0.2"), Rational("0.2")),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        # Expected length: distance (2.0) + effective_stickout1 (0.2 - 0.1) + effective_stickout2 (0.2 - 0.1)
        # = 2.0 + 0.1 + 0.1 = 2.2
        assert abs(beam.length - Rational("2.2")) < 1e-10
    
    def test_timber_face_is_perpendicular(self):
        """Test TimberFace.is_perpendicular() method."""
        # Test X-axis faces perpendicular to Y-axis faces
        assert TimberFace.RIGHT.is_perpendicular(TimberFace.FRONT)
        assert TimberFace.RIGHT.is_perpendicular(TimberFace.BACK)
        assert TimberFace.LEFT.is_perpendicular(TimberFace.FRONT)
        assert TimberFace.LEFT.is_perpendicular(TimberFace.BACK)
        assert TimberFace.FRONT.is_perpendicular(TimberFace.RIGHT)
        assert TimberFace.FRONT.is_perpendicular(TimberFace.LEFT)
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
        assert TimberFace.FRONT.is_perpendicular(TimberFace.TOP)
        assert TimberFace.FRONT.is_perpendicular(TimberFace.BOTTOM)
        assert TimberFace.BACK.is_perpendicular(TimberFace.TOP)
        assert TimberFace.BACK.is_perpendicular(TimberFace.BOTTOM)
        assert TimberFace.TOP.is_perpendicular(TimberFace.FRONT)
        assert TimberFace.TOP.is_perpendicular(TimberFace.BACK)
        assert TimberFace.BOTTOM.is_perpendicular(TimberFace.FRONT)
        assert TimberFace.BOTTOM.is_perpendicular(TimberFace.BACK)
        
        # Test non-perpendicular pairs (opposite faces on same axis)
        assert not TimberFace.RIGHT.is_perpendicular(TimberFace.LEFT)
        assert not TimberFace.LEFT.is_perpendicular(TimberFace.RIGHT)
        assert not TimberFace.FRONT.is_perpendicular(TimberFace.BACK)
        assert not TimberFace.BACK.is_perpendicular(TimberFace.FRONT)
        assert not TimberFace.TOP.is_perpendicular(TimberFace.BOTTOM)
        assert not TimberFace.BOTTOM.is_perpendicular(TimberFace.TOP)
        
        # Test same face (not perpendicular to itself)
        assert not TimberFace.RIGHT.is_perpendicular(TimberFace.RIGHT)
        assert not TimberFace.LEFT.is_perpendicular(TimberFace.LEFT)
        assert not TimberFace.FRONT.is_perpendicular(TimberFace.FRONT)
        assert not TimberFace.BACK.is_perpendicular(TimberFace.BACK)
        assert not TimberFace.TOP.is_perpendicular(TimberFace.TOP)
        assert not TimberFace.BOTTOM.is_perpendicular(TimberFace.BOTTOM)
    
    def test_timber_reference_long_face_to_timber_face(self):
        """Test TimberReferenceLongFace.to_timber_face() method."""
        assert TimberReferenceLongFace.RIGHT.to_timber_face() == TimberFace.RIGHT
        assert TimberReferenceLongFace.FRONT.to_timber_face() == TimberFace.FRONT
        assert TimberReferenceLongFace.LEFT.to_timber_face() == TimberFace.LEFT
        assert TimberReferenceLongFace.BACK.to_timber_face() == TimberFace.BACK
    
    def test_timber_reference_long_face_is_perpendicular(self):
        """Test TimberReferenceLongFace.is_perpendicular() method."""
        # Test perpendicular pairs
        assert TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.FRONT)
        assert TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.BACK)
        assert TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.FRONT)
        assert TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.BACK)
        assert TimberReferenceLongFace.FRONT.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert TimberReferenceLongFace.FRONT.is_perpendicular(TimberReferenceLongFace.LEFT)
        assert TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.LEFT)
        
        # Test non-perpendicular pairs (opposite faces)
        assert not TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.LEFT)
        assert not TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert not TimberReferenceLongFace.FRONT.is_perpendicular(TimberReferenceLongFace.BACK)
        assert not TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.FRONT)
        
        # Test same face (not perpendicular to itself)
        assert not TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.RIGHT)
        assert not TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.LEFT)
        assert not TimberReferenceLongFace.FRONT.is_perpendicular(TimberReferenceLongFace.FRONT)
        assert not TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.BACK)
    
    def test_timber_reference_long_face_rotate_right(self):
        """Test TimberReferenceLongFace.rotate_right() method."""
        # Test single rotation clockwise (when viewed from above/+Z)
        # RIGHT (3) -> FRONT (4) -> LEFT (5) -> BACK (6) -> RIGHT (3)
        assert TimberReferenceLongFace.RIGHT.rotate_right() == TimberReferenceLongFace.FRONT
        assert TimberReferenceLongFace.FRONT.rotate_right() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.LEFT.rotate_right() == TimberReferenceLongFace.BACK
        assert TimberReferenceLongFace.BACK.rotate_right() == TimberReferenceLongFace.RIGHT
        
        # Test chaining: rotating right 4 times should return to original
        assert TimberReferenceLongFace.RIGHT.rotate_right().rotate_right().rotate_right().rotate_right() == TimberReferenceLongFace.RIGHT
        assert TimberReferenceLongFace.FRONT.rotate_right().rotate_right().rotate_right().rotate_right() == TimberReferenceLongFace.FRONT
        assert TimberReferenceLongFace.LEFT.rotate_right().rotate_right().rotate_right().rotate_right() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.BACK.rotate_right().rotate_right().rotate_right().rotate_right() == TimberReferenceLongFace.BACK
        
        # Test rotating right twice (180 degrees) gives opposite face
        assert TimberReferenceLongFace.RIGHT.rotate_right().rotate_right() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.LEFT.rotate_right().rotate_right() == TimberReferenceLongFace.RIGHT
        assert TimberReferenceLongFace.FRONT.rotate_right().rotate_right() == TimberReferenceLongFace.BACK
        assert TimberReferenceLongFace.BACK.rotate_right().rotate_right() == TimberReferenceLongFace.FRONT
    
    def test_timber_reference_long_face_rotate_left(self):
        """Test TimberReferenceLongFace.rotate_left() method."""
        # Test single rotation counter-clockwise (when viewed from above/+Z)
        # RIGHT (3) -> BACK (6) -> LEFT (5) -> FRONT (4) -> RIGHT (3)
        assert TimberReferenceLongFace.RIGHT.rotate_left() == TimberReferenceLongFace.BACK
        assert TimberReferenceLongFace.BACK.rotate_left() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.LEFT.rotate_left() == TimberReferenceLongFace.FRONT
        assert TimberReferenceLongFace.FRONT.rotate_left() == TimberReferenceLongFace.RIGHT
        
        # Test chaining: rotating left 4 times should return to original
        assert TimberReferenceLongFace.RIGHT.rotate_left().rotate_left().rotate_left().rotate_left() == TimberReferenceLongFace.RIGHT
        assert TimberReferenceLongFace.FRONT.rotate_left().rotate_left().rotate_left().rotate_left() == TimberReferenceLongFace.FRONT
        assert TimberReferenceLongFace.LEFT.rotate_left().rotate_left().rotate_left().rotate_left() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.BACK.rotate_left().rotate_left().rotate_left().rotate_left() == TimberReferenceLongFace.BACK
        
        # Test rotating left twice (180 degrees) gives opposite face
        assert TimberReferenceLongFace.RIGHT.rotate_left().rotate_left() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.LEFT.rotate_left().rotate_left() == TimberReferenceLongFace.RIGHT
        assert TimberReferenceLongFace.FRONT.rotate_left().rotate_left() == TimberReferenceLongFace.BACK
        assert TimberReferenceLongFace.BACK.rotate_left().rotate_left() == TimberReferenceLongFace.FRONT
    
    def test_timber_reference_long_face_rotate_right_left_inverse(self):
        """Test that rotate_right() and rotate_left() are inverses of each other."""
        # Test that rotating right then left returns to original
        assert TimberReferenceLongFace.RIGHT.rotate_right().rotate_left() == TimberReferenceLongFace.RIGHT
        assert TimberReferenceLongFace.FRONT.rotate_right().rotate_left() == TimberReferenceLongFace.FRONT
        assert TimberReferenceLongFace.LEFT.rotate_right().rotate_left() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.BACK.rotate_right().rotate_left() == TimberReferenceLongFace.BACK
        
        # Test that rotating left then right returns to original
        assert TimberReferenceLongFace.RIGHT.rotate_left().rotate_right() == TimberReferenceLongFace.RIGHT
        assert TimberReferenceLongFace.FRONT.rotate_left().rotate_right() == TimberReferenceLongFace.FRONT
        assert TimberReferenceLongFace.LEFT.rotate_left().rotate_right() == TimberReferenceLongFace.LEFT
        assert TimberReferenceLongFace.BACK.rotate_left().rotate_right() == TimberReferenceLongFace.BACK
        
        # Test multiple rotations in opposite directions cancel out
        assert TimberReferenceLongFace.RIGHT.rotate_right().rotate_right().rotate_left().rotate_left() == TimberReferenceLongFace.RIGHT
        assert TimberReferenceLongFace.FRONT.rotate_left().rotate_left().rotate_left().rotate_right().rotate_right().rotate_right() == TimberReferenceLongFace.FRONT
    
    def test_timber_reference_long_face_rotate_perpendicularity(self):
        """Test that rotating by 90 degrees produces perpendicular faces."""
        # Single rotation should produce perpendicular face
        assert TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.RIGHT.rotate_right())
        assert TimberReferenceLongFace.RIGHT.is_perpendicular(TimberReferenceLongFace.RIGHT.rotate_left())
        assert TimberReferenceLongFace.FRONT.is_perpendicular(TimberReferenceLongFace.FRONT.rotate_right())
        assert TimberReferenceLongFace.FRONT.is_perpendicular(TimberReferenceLongFace.FRONT.rotate_left())
        assert TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.LEFT.rotate_right())
        assert TimberReferenceLongFace.LEFT.is_perpendicular(TimberReferenceLongFace.LEFT.rotate_left())
        assert TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.BACK.rotate_right())
        assert TimberReferenceLongFace.BACK.is_perpendicular(TimberReferenceLongFace.BACK.rotate_left())
    
    def test_distance_from_long_edge_is_valid(self):
        """Test DistanceFromLongEdge.is_valid() method."""
        # Valid cases - perpendicular faces
        valid_edge1 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.FRONT, distance=Rational(2))
        )
        assert valid_edge1.is_valid()
        
        valid_edge2 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.BACK, distance=Rational(2))
        )
        assert valid_edge2.is_valid()
        
        valid_edge3 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FRONT, distance=Rational(1)),
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
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FRONT, distance=Rational(1)),
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
        
        # RIGHT + FRONT -> RIGHT_FRONT
        edge1 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.FRONT, distance=Rational(2))
        )
        assert edge1.get_long_edge() == TimberReferenceLongEdge.RIGHT_FRONT
        
        # FRONT + LEFT -> FRONT_LEFT
        edge2 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FRONT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(2))
        )
        assert edge2.get_long_edge() == TimberReferenceLongEdge.FRONT_LEFT
        
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
        
        # FRONT + RIGHT -> FRONT_RIGHT
        edge5 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.FRONT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.RIGHT, distance=Rational(2))
        )
        assert edge5.get_long_edge() == TimberReferenceLongEdge.FRONT_RIGHT
        
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
        
        # LEFT + FRONT -> LEFT_FRONT
        edge8 = DistanceFromLongEdge(
            face1=DistanceFromLongFace(face=TimberReferenceLongFace.LEFT, distance=Rational(1)),
            face2=DistanceFromLongFace(face=TimberReferenceLongFace.FRONT, distance=Rational(2))
        )
        assert edge8.get_long_edge() == TimberReferenceLongEdge.LEFT_FRONT
    
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
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction, name='test_timber')
        cut_timber = CutTimber(timber)
        
        # Get the CSG
        csg = cut_timber._extended_timber_without_cuts_csg_local()
        
        # Should be a finite prism
        from code_goes_here.meowmeowcsg import RectangularPrism
        assert isinstance(csg, RectangularPrism)
        
        # In LOCAL coordinates (relative to bottom_position):
        # Start should be at 0 (local bottom)
        assert csg.start_distance == 0
        
        # End should be at timber's length (local top)
        assert csg.end_distance == 100
        
        # Size should match timber
        assert csg.size == size
        # In LOCAL coordinates, the prism is always axis-aligned (identity orientation)
        # The timber's orientation transforms from local to global coordinates
        from code_goes_here.moothymoth import Orientation
        assert simplify(csg.transform.orientation.matrix - Orientation.identity().matrix).norm() == 0
    
    def test_extended_timber_without_cuts_positioned(self):
        """Test that CSG works correctly for timber at different position."""
        # Create a timber at a different position
        length = Rational(50)
        size = Matrix([Rational(3), Rational(4)])
        bottom_position = Matrix([Rational(5), Rational(10), Rational(20)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        csg = cut_timber._extended_timber_without_cuts_csg_local()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Start distance is 0 (at bottom)
        assert csg.start_distance == 0
        
        # End distance is the timber's length
        assert csg.end_distance == 50
    
    def test_extended_timber_horizontal(self):
        """Test CSG for a horizontal timber in local coordinates."""
        length = Rational(80)
        size = Matrix([Rational(5), Rational(5)])
        bottom_position = Matrix([Rational(10), Rational(20), Rational(5)])
        length_direction = Matrix([Rational(1), Rational(0), Rational(0)])  # Along X
        width_direction = Matrix([Rational(0), Rational(1), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        csg = cut_timber._extended_timber_without_cuts_csg_local()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Start distance is 0
        assert csg.start_distance == 0
        
        # End distance is the timber's length
        assert csg.end_distance == 80
        
        # the csg is in local coordinates, so it should have identity orientation
        from code_goes_here.moothymoth import Orientation
        assert csg.transform.orientation.matrix.equals(Orientation.identity().matrix)
    
    def test_render_timber_with_cuts_no_cuts(self):
        """Test render_timber_with_cuts_csg_local with no cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(0)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber, cuts=[])
        
        # Get the CSG with cuts applied (should be same as without cuts since there are none)
        csg = cut_timber.render_timber_with_cuts_csg_local()
        
        # Should be a RectangularPrism (since no cuts means no Difference operation)
        from code_goes_here.meowmeowcsg import RectangularPrism
        assert isinstance(csg, RectangularPrism)
        assert csg.size == size
        assert csg.start_distance == 0
        assert csg.end_distance == length
    
    def test_render_timber_with_cuts_one_cut(self):
        """Test render_timber_with_cuts_csg_local with one cut."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add a cut (a simple half-plane cut at z=50 in local coordinates)
        from code_goes_here.meowmeowcsg import HalfSpace
        # Create a half plane that cuts perpendicular to the timber length
        # Normal pointing in +Z direction, offset at 50
        half_plane = HalfSpace(
            normal=Matrix([Rational(0), Rational(0), Rational(1)]),
            offset=Rational(50)
        )
        cut = HalfSpaceCut(
            timber=timber,
            transform=Transform(
                position=Matrix([Rational(0), Rational(0), Rational(0)]),
                orientation=Orientation.identity()
            ),
            half_plane=half_plane,
            maybe_end_cut=None
        )
        
        cut_timber = CutTimber(timber, cuts=[cut])
        
        # Get the CSG with cuts applied
        csg = cut_timber.render_timber_with_cuts_csg_local()
        
        # Should be a Difference operation
        from code_goes_here.meowmeowcsg import Difference
        assert isinstance(csg, Difference)
        assert isinstance(csg.base, RectangularPrism)
        assert len(csg.subtract) == 1
        assert isinstance(csg.subtract[0], HalfSpace)
    
    def test_render_timber_with_cuts_multiple_cuts(self):
        """Test render_timber_with_cuts_csg_local with multiple cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(0)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add two cuts
        from code_goes_here.meowmeowcsg import HalfSpace
        half_plane1 = HalfSpace(
            normal=Matrix([Rational(0), Rational(0), Rational(1)]),
            offset=Rational(25)
        )
        cut1 = HalfSpaceCut(
            timber=timber,
            transform=Transform(
                position=Matrix([Rational(0), Rational(0), Rational(0)]),
                orientation=Orientation.identity()
            ),
            half_plane=half_plane1,
            maybe_end_cut=None
        )
        
        half_plane2 = HalfSpace(
            normal=Matrix([Rational(0), Rational(0), Rational(-1)]),
            offset=Rational(-75)
        )
        cut2 = HalfSpaceCut(
            timber=timber,
            transform=Transform(
                position=Matrix([Rational(0), Rational(0), Rational(0)]),
                orientation=Orientation.identity()
            ),
            half_plane=half_plane2,
            maybe_end_cut=None
        )
        
        cut_timber = CutTimber(timber, cuts=[cut1, cut2])
        
        # Get the CSG with cuts applied
        csg = cut_timber.render_timber_with_cuts_csg_local()
        
        # Should be a Difference operation
        from code_goes_here.meowmeowcsg import Difference
        assert isinstance(csg, Difference)
        assert isinstance(csg.base, RectangularPrism)
        assert len(csg.subtract) == 2
        assert all(isinstance(sub, HalfSpace) for sub in csg.subtract)
    
    def test_render_timber_with_cuts_with_end_cuts(self):
        """Test render_timber_with_cuts_csg_local with end cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(0)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add an end cut at the top
        from code_goes_here.meowmeowcsg import HalfSpace
        half_plane = HalfSpace(
            normal=Matrix([Rational(0), Rational(0), Rational(-1)]),
            offset=Rational(-50)
        )
        end_cut = HalfSpaceCut(
            timber=timber,
            transform=Transform(
                position=Matrix([Rational(0), Rational(0), Rational(0)]),
                orientation=Orientation.identity()
            ),
            half_plane=half_plane,
            maybe_end_cut=TimberReferenceEnd.TOP
        )
        
        cut_timber = CutTimber(timber, cuts=[end_cut])
        
        # Get the CSG with cuts applied
        csg = cut_timber.render_timber_with_cuts_csg_local()
        
        # Should be a Difference operation
        from code_goes_here.meowmeowcsg import Difference, RectangularPrism
        assert isinstance(csg, Difference)
        assert isinstance(csg.base, RectangularPrism)
        
        # Base prism should be semi-infinite at the top (end_distance = None)
        assert csg.base.start_distance == 0
        assert csg.base.end_distance is None
        
        # Should have one cut
        assert len(csg.subtract) == 1
        assert isinstance(csg.subtract[0], HalfSpace)


# ============================================================================
# Tests for Peg and Wedge Joint Accessories
# ============================================================================

class TestPegShape:
    """Test PegShape enum."""
    
    def test_peg_shape_enum(self):
        """Test PegShape enum values."""
        assert PegShape.SQUARE.value == "square"
        assert PegShape.ROUND.value == "round"


class TestPeg:
    """Test Peg class."""
    
    def test_peg_creation(self):
        """Test basic Peg creation."""
        orientation = Orientation.identity()
        position = create_v3(1, 2, 3)
        
        peg = Peg(
            transform=Transform(position=position, orientation=orientation),
            size=Rational(2),
            shape=PegShape.SQUARE,
            forward_length=Rational(10),
            stickout_length=Rational(1)
        )
        
        assert peg.transform.orientation == orientation
        assert peg.transform.position == position
        assert peg.size == Rational(2)
        assert peg.shape == PegShape.SQUARE
        assert peg.forward_length == Rational(10)
        assert peg.stickout_length == Rational(1)
    
    def test_peg_is_frozen(self):
        """Test that Peg is immutable."""
        peg = Peg(
            transform=Transform.identity(),
            size=Rational(2),
            shape=PegShape.ROUND,
            forward_length=Rational(10),
            stickout_length=Rational(1)
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            peg.size = Rational(3)
    
    def test_peg_render_csg_local_square(self):
        """Test rendering square peg CSG in local space."""
        peg = Peg(
            transform=Transform.identity(),
            size=Rational(2),
            shape=PegShape.SQUARE,
            forward_length=Rational(10),
            stickout_length=Rational(1)
        )
        
        csg = peg.render_csg_local()
        
        # Should return a RectangularPrism
        from .meowmeowcsg import RectangularPrism
        assert isinstance(csg, RectangularPrism)
        
        # Verify dimensions
        assert csg.size[0] == Rational(2)  # width
        assert csg.size[1] == Rational(2)  # height
        assert csg.start_distance == Rational(-1)  # stickout_length
        assert csg.end_distance == Rational(10)  # forward_length
    
    def test_peg_render_csg_local_round(self):
        """Test rendering round peg CSG in local space."""
        peg = Peg(
            transform=Transform.identity(),
            size=Rational(4),
            shape=PegShape.ROUND,
            forward_length=Rational(12),
            stickout_length=Rational(2)
        )
        
        csg = peg.render_csg_local()
        
        # Should return a Cylinder
        from .meowmeowcsg import Cylinder
        assert isinstance(csg, Cylinder)
        
        # Verify dimensions
        assert csg.radius == Rational(2)  # diameter / 2
        assert csg.start_distance == Rational(-2)  # stickout_length
        assert csg.end_distance == Rational(12)  # forward_length


class TestWedge:
    """Test Wedge class."""
    
    def test_wedge_creation(self):
        """Test basic Wedge creation."""
        orientation = Orientation.identity()
        position = create_v3(1, 2, 3)
        
        wedge = Wedge(
            transform=Transform(position=position, orientation=orientation),
            base_width=Rational(5),
            tip_width=Rational(1),
            height=Rational(2),
            length=Rational(10)
        )
        
        assert wedge.transform.orientation == orientation
        assert wedge.transform.position == position
        assert wedge.base_width == Rational(5)
        assert wedge.tip_width == Rational(1)
        assert wedge.height == Rational(2)
        assert wedge.length == Rational(10)
    
    def test_wedge_width_property(self):
        """Test that width property is an alias for base_width."""
        wedge = Wedge(
            transform=Transform.identity(),
            base_width=Rational(5),
            tip_width=Rational(1),
            height=Rational(2),
            length=Rational(10)
        )
        
        assert wedge.width == wedge.base_width
        assert wedge.width == Rational(5)
    
    def test_wedge_is_frozen(self):
        """Test that Wedge is immutable."""
        wedge = Wedge(
            transform=Transform.identity(),
            base_width=Rational(5),
            tip_width=Rational(1),
            height=Rational(2),
            length=Rational(10)
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            wedge.base_width = Rational(6)
    
    def test_wedge_render_csg_local(self):
        """Test rendering wedge CSG in local space."""
        wedge = Wedge(
            transform=Transform.identity(),
            base_width=Rational(5),
            tip_width=Rational(1),
            height=Rational(2),
            length=Rational(10)
        )
        
        csg = wedge.render_csg_local()
        
        # Should return a RectangularPrism (simplified bounding box for now)
        from .meowmeowcsg import RectangularPrism
        assert isinstance(csg, RectangularPrism)
        
        # Verify dimensions match the base dimensions
        assert csg.size[0] == Rational(5)  # base_width
        assert csg.size[1] == Rational(2)  # height
        assert csg.start_distance == 0
        assert csg.end_distance == Rational(10)  # length


class TestCreatePegGoingIntoFace:
    """Test create_peg_going_into_face helper function."""
    
    def setup_method(self):
        """Create a standard vertical timber for testing."""
        self.timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(Rational(10), Rational(15)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
    
    def test_peg_into_right_face(self):
        """Test creating a peg going into the RIGHT face."""
        peg = create_peg_going_into_face(
            timber=self.timber,
            face=TimberReferenceLongFace.RIGHT,
            distance_from_bottom=Rational(50),
            distance_from_centerline=Rational(0),
            peg_size=Rational(2),
            peg_shape=PegShape.ROUND,
            forward_length=Rational(8),
            stickout_length=Rational(1)
        )
        
        assert peg.size == Rational(2)
        assert peg.shape == PegShape.ROUND
        assert peg.forward_length == Rational(8)
        assert peg.stickout_length == Rational(1)
        
        # Position should be at the right surface (width/2 = 5)
        assert peg.transform.position[0] == Rational(5)  # X = width/2
        assert peg.transform.position[1] == Rational(0)  # Y = distance_from_centerline
        assert peg.transform.position[2] == Rational(50)  # Z = distance_from_bottom
    
    def test_peg_into_left_face(self):
        """Test creating a peg going into the LEFT face."""
        peg = create_peg_going_into_face(
            timber=self.timber,
            face=TimberReferenceLongFace.LEFT,
            distance_from_bottom=Rational(30),
            distance_from_centerline=Rational(2),
            peg_size=Rational(2),
            peg_shape=PegShape.ROUND,
            forward_length=Rational(8),
            stickout_length=Rational(1)
        )
        
        # Position should be at the left surface (-width/2 = -5)
        assert peg.transform.position[0] == Rational(-5)  # X = -width/2
        assert peg.transform.position[1] == Rational(2)  # Y = distance_from_centerline
        assert peg.transform.position[2] == Rational(30)  # Z = distance_from_bottom
    
    def test_peg_into_forward_face(self):
        """Test creating a peg going into the FRONT face."""
        peg = create_peg_going_into_face(
            timber=self.timber,
            face=TimberReferenceLongFace.FRONT,
            distance_from_bottom=Rational(40),
            distance_from_centerline=Rational(-1),
            peg_size=Rational(2),
            peg_shape=PegShape.ROUND,
            forward_length=Rational(8),
            stickout_length=Rational(1)
        )
        
        # Position should be at the forward surface (height/2 = 7.5)
        assert peg.transform.position[0] == Rational(-1)  # X = distance_from_centerline
        assert peg.transform.position[1] == Rational(15, 2)  # Y = height/2 = 7.5
        assert peg.transform.position[2] == Rational(40)  # Z = distance_from_bottom
    
    def test_peg_into_back_face(self):
        """Test creating a peg going into the BACK face."""
        peg = create_peg_going_into_face(
            timber=self.timber,
            face=TimberReferenceLongFace.BACK,
            distance_from_bottom=Rational(60),
            distance_from_centerline=Rational(3),
            peg_size=Rational(2),
            peg_shape=PegShape.ROUND,
            forward_length=Rational(8),
            stickout_length=Rational(1)
        )
        
        # Position should be at the back surface (-height/2 = -7.5)
        assert peg.transform.position[0] == Rational(3)  # X = distance_from_centerline
        assert peg.transform.position[1] == Rational(-15, 2)  # Y = -height/2 = -7.5
        assert peg.transform.position[2] == Rational(60)  # Z = distance_from_bottom
    
    def test_square_peg(self):
        """Test creating a square peg."""
        peg = create_peg_going_into_face(
            timber=self.timber,
            face=TimberReferenceLongFace.RIGHT,
            distance_from_bottom=Rational(50),
            distance_from_centerline=Rational(0),
            peg_size=Rational(3),
            peg_shape=PegShape.SQUARE,
            forward_length=Rational(8),
            stickout_length=Rational(1)
        )
        
        assert peg.shape == PegShape.SQUARE
        assert peg.size == Rational(3)


class TestProjectGlobalPointOntoTimberFace:
    """Test Timber.project_global_point_onto_timber_face_global() method."""
    
    def test_project_onto_top_face_axis_aligned(self):
        """Test projecting a point onto the top face of an axis-aligned timber."""
        # Create a simple vertical timber
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        
        # Project a point in the middle of the timber onto the top face
        global_point = create_v3(0, 0, Rational("0.5"))  # Halfway up the timber
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.TOP)
        
        # The projected point should be at the top face (Z = length = 2)
        # In local coords, top face is at Z = length/2 = 1
        # In global coords (since timber bottom is at 0,0,0), top face center is at 0,0,1
        expected_global = create_v3(0, 0, 1)
        assert projected_global == expected_global
    
    def test_project_onto_bottom_face_axis_aligned(self):
        """Test projecting a point onto the bottom face."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Project a point onto the bottom face
        global_point = create_v3(Rational("0.05"), Rational("0.1"), Rational("0.5"))
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.BOTTOM)
        
        # Bottom face is at Z = -length/2 = -1 in local coords
        # In global coords, that's 0,0,-1 relative to bottom_position (0,0,0)
        # So the projected point should maintain X,Y but be at Z = -1
        expected_global = create_v3(Rational("0.05"), Rational("0.1"), -1)
        assert projected_global == expected_global
    
    def test_project_onto_right_face_axis_aligned(self):
        """Test projecting a point onto the right face."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Project a point in the middle onto the right face
        global_point = create_v3(0, 0, 0)  # Center of timber
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.RIGHT)
        
        # Right face is at X = width/2 = 0.1 in local coords
        # In global coords (axis-aligned), that's 0.1, 0, 0
        expected_global = create_v3(Rational("0.1"), 0, 0)
        assert projected_global == expected_global
    
    def test_project_onto_left_face_axis_aligned(self):
        """Test projecting a point onto the left face."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Project a point onto the left face
        global_point = create_v3(Rational("0.05"), Rational("0.1"), Rational("0.5"))
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.LEFT)
        
        # Left face is at X = -width/2 = -0.1 in local coords
        expected_global = create_v3(Rational("-0.1"), Rational("0.1"), Rational("0.5"))
        assert projected_global == expected_global
    
    def test_project_onto_front_face_axis_aligned(self):
        """Test projecting a point onto the front face."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Project a point onto the front face
        global_point = create_v3(0, 0, 0)
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.FRONT)
        
        # Front face is at Y = height/2 = 0.15 in local coords
        expected_global = create_v3(0, Rational("0.15"), 0)
        assert projected_global == expected_global
    
    def test_project_onto_back_face_axis_aligned(self):
        """Test projecting a point onto the back face."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Project a point onto the back face
        global_point = create_v3(Rational("0.05"), Rational("0.05"), Rational("0.5"))
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.BACK)
        
        # Back face is at Y = -height/2 = -0.15 in local coords
        expected_global = create_v3(Rational("0.05"), Rational("-0.15"), Rational("0.5"))
        assert projected_global == expected_global
    
    def test_project_point_already_on_face(self):
        """Test that projecting a point already on the face returns the same point."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Point already on the top face (Z = 1 in global coords)
        global_point = create_v3(Rational("0.05"), Rational("0.1"), 1)
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.TOP)
        
        # Should return the same point in global coords
        expected_global = create_v3(Rational("0.05"), Rational("0.1"), 1)
        assert projected_global == expected_global
    
    def test_project_onto_rotated_timber(self):
        """Test projecting onto a face of a rotated timber."""
        # Create a timber pointing east (along X-axis)
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),   # X-direction (east)
            width_direction=create_v3(0, 1, 0)      # Y-direction (north)
        )
        
        # Project a point in the middle onto the TOP face
        # In global coords, center of timber is at origin
        global_point = create_v3(0, 0, 0)
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.TOP)
        
        # For this timber, local Z-axis (length) points in global X direction
        # So top face center in local coords (0, 0, 1) maps to global (1, 0, 0)
        expected_global = create_v3(1, 0, 0)
        assert projected_global == expected_global
    
    def test_project_with_offset_bottom_position(self):
        """Test projection on a timber with non-zero bottom position."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(5, 10, 20),  # Offset position
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Project center of timber (in global coords: 5, 10, 20) onto top face
        global_point = create_v3(5, 10, 20)
        projected_global = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.TOP)
        
        # Top face in local coords is at Z=1, which in global should be at (5, 10, 21)
        expected_global = create_v3(5, 10, 21)
        assert projected_global == expected_global
    
    def test_project_accepts_timber_reference_end(self):
        """Test that the method accepts TimberReferenceEnd as well as TimberFace."""
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        global_point = create_v3(0, 0, 0)
        
        # Should work with TimberReferenceEnd.TOP
        projected_with_end = timber.project_global_point_onto_timber_face_global(global_point, TimberReferenceEnd.TOP)
        projected_with_face = timber.project_global_point_onto_timber_face_global(global_point, TimberFace.TOP)
        
        # Both should give the same result
        assert projected_with_end == projected_with_face


class TestCreateWedgeInTimberEnd:
    """Test create_wedge_in_timber_end helper function."""
    
    def setup_method(self):
        """Create a standard vertical timber for testing."""
        self.timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(Rational(10), Rational(15)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        self.wedge_spec = WedgeShape(
            base_width=Rational(5),
            tip_width=Rational(1),
            height=Rational(2),
            length=Rational(10)
        )
    
    def test_wedge_at_top_end(self):
        """Test creating a wedge at the TOP end."""
        wedge = create_wedge_in_timber_end(
            timber=self.timber,
            end=TimberReferenceEnd.TOP,
            position=create_v3(Rational(2), Rational(3), 0),
            shape=self.wedge_spec
        )
        
        assert wedge.base_width == Rational(5)
        assert wedge.tip_width == Rational(1)
        assert wedge.height == Rational(2)
        assert wedge.length == Rational(10)
        assert wedge.width == Rational(5)  # Test width property
        
        # Position should be at the top end (Z = length)
        assert wedge.transform.position[0] == Rational(2)  # X from position
        assert wedge.transform.position[1] == Rational(3)  # Y from position
        assert wedge.transform.position[2] == Rational(100)  # Z = timber length
    
    def test_wedge_at_bottom_end(self):
        """Test creating a wedge at the BOTTOM end."""
        wedge = create_wedge_in_timber_end(
            timber=self.timber,
            end=TimberReferenceEnd.BOTTOM,
            position=create_v3(Rational(-1), Rational(2), 0),
            shape=self.wedge_spec
        )
        
        # Position should be at the bottom end (Z = 0)
        assert wedge.transform.position[0] == Rational(-1)  # X from position
        assert wedge.transform.position[1] == Rational(2)  # Y from position
        assert wedge.transform.position[2] == Rational(0)  # Z = 0 (bottom)
    
    def test_wedge_at_centerline(self):
        """Test creating a wedge at the timber centerline."""
        wedge = create_wedge_in_timber_end(
            timber=self.timber,
            end=TimberReferenceEnd.TOP,
            position=create_v3(0, 0, 0),  # Center of cross-section
            shape=self.wedge_spec
        )
        
        # Position should be at center of top end
        assert wedge.transform.position[0] == Rational(0)
        assert wedge.transform.position[1] == Rational(0)
        assert wedge.transform.position[2] == Rational(100)


class TestWedgeShape:
    """Test WedgeShape specification class."""
    
    def test_wedge_shape_creation(self):
        """Test WedgeShape creation."""
        shape = WedgeShape(
            base_width=Rational(6),
            tip_width=Rational(2),
            height=Rational(3),
            length=Rational(12)
        )
        
        assert shape.base_width == Rational(6)
        assert shape.tip_width == Rational(2)
        assert shape.height == Rational(3)
        assert shape.length == Rational(12)
    
    def test_wedge_shape_is_frozen(self):
        """Test that WedgeShape is immutable."""
        shape = WedgeShape(
            base_width=Rational(5),
            tip_width=Rational(1),
            height=Rational(2),
            length=Rational(10)
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            shape.base_width = Rational(7)



class TestFrameFromJoints:
    """Test Frame.from_joints constructor."""
    
    def test_from_joints_simple(self):
        """Test creating a frame from a list of joints."""
        # Create two simple timbers
        timber1 = create_axis_aligned_timber(
            bottom_position=create_v3(0, 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Timber 1"
        )
        
        timber2 = create_axis_aligned_timber(
            bottom_position=create_v3(Rational(10), 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Timber 2"
        )
        
        # Create mock cuts for each timber
        cut1 = MockCut(timber1, create_v3(0, 0, 0))
        cut2 = MockCut(timber2, create_v3(0, 0, 0))
        
        # Create CutTimbers
        cut_timber1 = CutTimber(timber1, cuts=[cut1])
        cut_timber2 = CutTimber(timber2, cuts=[cut2])
        
        # Create a joint
        joint = Joint(
            cut_timbers={"timber1": cut_timber1, "timber2": cut_timber2},
            jointAccessories={}
        )
        
        # Create frame from joints
        frame = Frame.from_joints([joint], name="Test Frame")
        
        # Verify frame has 2 cut timbers
        assert len(frame.cut_timbers) == 2
        assert frame.name == "Test Frame"
        assert len(frame.accessories) == 0
        
        # Verify each timber appears once
        timber_names = [ct.timber.name for ct in frame.cut_timbers]
        assert "Timber 1" in timber_names
        assert "Timber 2" in timber_names
    
    def test_from_joints_merges_same_timber(self):
        """Test that cut timbers with the same underlying timber reference are merged."""
        # Create a single timber
        timber = create_axis_aligned_timber(
            bottom_position=create_v3(0, 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Shared Timber"
        )
        
        # Create different cuts for the same timber
        cut1 = MockCut(timber, create_v3(0, 0, 0))
        cut2 = MockCut(timber, create_v3(0, 0, 0))
        cut3 = MockCut(timber, create_v3(0, 0, 0))
        
        # Create multiple CutTimber instances for the same timber
        cut_timber1 = CutTimber(timber, cuts=[cut1])
        cut_timber2 = CutTimber(timber, cuts=[cut2, cut3])
        
        # Create two joints that both reference the same timber
        joint1 = Joint(
            cut_timbers={"timber": cut_timber1},
            jointAccessories={}
        )
        
        joint2 = Joint(
            cut_timbers={"timber": cut_timber2},
            jointAccessories={}
        )
        
        # Create frame from joints
        frame = Frame.from_joints([joint1, joint2])
        
        # Verify only one cut timber in the frame (merged)
        assert len(frame.cut_timbers) == 1
        
        # Verify all cuts are present
        merged_cut_timber = frame.cut_timbers[0]
        assert len(merged_cut_timber.cuts) == 3
        assert cut1 in merged_cut_timber.cuts
        assert cut2 in merged_cut_timber.cuts
        assert cut3 in merged_cut_timber.cuts
    
    def test_from_joints_collects_accessories(self):
        """Test that accessories from all joints are collected."""
        timber = create_axis_aligned_timber(
            bottom_position=create_v3(0, 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Timber"
        )
        
        # Create a peg accessory
        peg = Peg(
            transform=Transform(
                position=create_v3(0, 0, Rational(50)),
                orientation=Orientation.identity()
            ),
            size=Rational(1),
            shape=PegShape.ROUND,
            forward_length=Rational(10),
            stickout_length=Rational(2)
        )
        
        # Create a wedge accessory
        wedge = Wedge(
            transform=Transform(
                position=create_v3(0, 0, Rational(100)),
                orientation=Orientation.identity()
            ),
            base_width=Rational(2),
            tip_width=Rational(1),
            height=Rational(3),
            length=Rational(5)
        )
        
        # Create joints with accessories
        joint1 = Joint(
            cut_timbers={"timber": CutTimber(timber, cuts=[])},
            jointAccessories={"peg": peg}
        )
        
        joint2 = Joint(
            cut_timbers={"timber": CutTimber(timber, cuts=[])},
            jointAccessories={"wedge": wedge}
        )
        
        # Create frame from joints
        frame = Frame.from_joints([joint1, joint2])
        
        # Verify accessories are collected
        assert len(frame.accessories) == 2
        assert peg in frame.accessories
        assert wedge in frame.accessories
    
    def test_from_joints_with_additional_unjointed_timbers(self):
        """Test adding additional unjointed timbers to the frame."""
        # Create a timber with a joint
        timber1 = create_axis_aligned_timber(
            bottom_position=create_v3(0, 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Jointed Timber"
        )
        
        # Create an unjointed timber
        timber2 = create_axis_aligned_timber(
            bottom_position=create_v3(Rational(10), 0, 0),
            length=Rational(50),
            size=create_v2(Rational(2), Rational(2)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Unjointed Timber"
        )
        
        # Create a joint with timber1
        joint = Joint(
            cut_timbers={"timber1": CutTimber(timber1, cuts=[MockCut(timber1, create_v3(0, 0, 0))])},
            jointAccessories={}
        )
        
        # Create frame with additional unjointed timber
        frame = Frame.from_joints([joint], additional_unjointed_timbers=[timber2])
        
        # Verify both timbers are in the frame
        assert len(frame.cut_timbers) == 2
        
        timber_names = [ct.timber.name for ct in frame.cut_timbers]
        assert "Jointed Timber" in timber_names
        assert "Unjointed Timber" in timber_names
        
        # Verify unjointed timber has no cuts
        unjointed_ct = [ct for ct in frame.cut_timbers if ct.timber.name == "Unjointed Timber"][0]
        assert len(unjointed_ct.cuts) == 0
    
    def test_from_joints_warns_on_different_timbers_same_name(self):
        """Test that a warning is issued when different timbers have the same name."""
        # Create two different timbers with the same name
        timber1 = create_axis_aligned_timber(
            bottom_position=create_v3(0, 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Post"
        )
        
        timber2 = create_axis_aligned_timber(
            bottom_position=create_v3(Rational(10), 0, 0),
            length=Rational(80),  # Different length
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Post"  # Same name
        )
        
        # Create joints
        joint1 = Joint(
            cut_timbers={"timber1": CutTimber(timber1, cuts=[])},
            jointAccessories={}
        )
        
        joint2 = Joint(
            cut_timbers={"timber2": CutTimber(timber2, cuts=[])},
            jointAccessories={}
        )
        
        # Create frame - should issue a warning
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            frame = Frame.from_joints([joint1, joint2])
            
            # Verify a warning was issued
            assert len(w) == 1
            assert "multiple timbers with the same name" in str(w[0].message).lower()
            assert "Post" in str(w[0].message)
    
    def test_from_joints_errors_on_duplicate_timber_data(self):
        """Test that an error is raised when same timber data exists with different references."""
        # Create two timbers with identical data
        timber1 = create_axis_aligned_timber(
            bottom_position=create_v3(0, 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Post"
        )
        
        # Create an identical timber (same data, different object)
        timber2 = create_axis_aligned_timber(
            bottom_position=create_v3(0, 0, 0),
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            length_direction=TimberFace.TOP,
            width_direction=TimberFace.RIGHT,
            name="Post"
        )
        
        # Verify they are different objects but equal data
        assert timber1 is not timber2
        assert timber1 == timber2
        
        # Create joints
        joint1 = Joint(
            cut_timbers={"timber1": CutTimber(timber1, cuts=[])},
            jointAccessories={}
        )
        
        joint2 = Joint(
            cut_timbers={"timber2": CutTimber(timber2, cuts=[])},
            jointAccessories={}
        )
        
        # Create frame - should raise an error
        with pytest.raises(ValueError) as exc_info:
            Frame.from_joints([joint1, joint2])
        
        assert "identical underlying timber data" in str(exc_info.value).lower()
        assert "Post" in str(exc_info.value)
    
    def test_from_joints_empty_list(self):
        """Test creating a frame from an empty list of joints."""
        frame = Frame.from_joints([], name="Empty Frame")
        
        assert len(frame.cut_timbers) == 0
        assert len(frame.accessories) == 0
        assert frame.name == "Empty Frame"
