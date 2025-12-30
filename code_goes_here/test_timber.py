"""
Tests for GiraffeCAD timber framing system
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs, Float, Rational
from code_goes_here.moothymoth import Orientation
from code_goes_here.footprint import Footprint
from giraffe import *
from giraffe import _has_rational_components, _are_directions_perpendicular, _are_directions_parallel, _are_timbers_face_parallel, _are_timbers_face_orthogonal, _are_timbers_face_aligned, _project_point_on_timber_centerline, _calculate_mortise_position_from_tenon_intersection
from .conftest import (
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
        
        timber = timber_from_directions(length, size, position, length_dir, width_dir)
        
        assert timber.length == 3
        assert timber.size.shape == (2, 1)
        assert timber.bottom_position.shape == (3, 1)
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
        input_length_dir = create_vector3d(0, 0, 1)  # Up - exact integers
        input_width_dir = create_vector3d(1, 0, 0)    # East - exact integers
        
        timber = timber_from_directions(
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
        
        timber = timber_from_directions(
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
        timber = timber_from_directions(
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
        input_length_dir = create_vector3d(Rational(0), Rational(0), Rational(5))  # Up, but length 5
        input_width_dir = create_vector3d(Rational(3), Rational(0), Rational(0))    # East, but length 3
        
        timber = timber_from_directions(
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
        timber = timber_from_directions(
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
        timber = timber_from_directions(
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
        timber = timber_from_directions(
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
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),  # East
            width_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        post2 = timber_from_directions(
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
        post1 = timber_from_directions(
            length=Rational(3),
            size=create_vector2d(Rational("0.2"), Rational("0.2")),
            bottom_position=create_vector3d(0, 0, 0),
            length_direction=create_vector3d(1, 0, 0),  # East
            width_direction=create_vector3d(0, 0, 1)     # Up
        )
        
        post2 = timber_from_directions(
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
        from code_goes_here.meowmeowcsg import Prism
        assert isinstance(csg, Prism)
        
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
        assert simplify(csg.orientation.matrix - Orientation.identity().matrix).norm() == 0
    
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
    
    def test_extended_timber_minimal_boundary(self):
        """Test that minimal_boundary_in_direction works on the CSG in local coordinates."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        csg = cut_timber._extended_timber_without_cuts_csg_local()
        
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
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        csg = cut_timber._extended_timber_without_cuts_csg_local()
        
        # In LOCAL coordinates (relative to bottom_position):
        # Start distance is 0
        assert csg.start_distance == 0
        
        # End distance is the timber's length
        assert csg.end_distance == 80
        
        # In LOCAL coordinates, the prism is always axis-aligned (identity orientation)
        # The timber's orientation transforms from local to global coordinates
        from code_goes_here.moothymoth import Orientation
        assert simplify(csg.orientation.matrix - Orientation.identity().matrix).norm() == 0
    
    def test_render_timber_without_cuts_no_end_cuts(self):
        """Test render_timber_without_cuts_csg with no end cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        cut_timber = CutTimber(timber)
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg_local()
        
        # Should be a finite prism with original dimensions in LOCAL coordinates
        # Local coordinates are relative to bottom_position
        from code_goes_here.meowmeowcsg import Prism
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
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add a bottom end cut at z=15
        cut_end_position = Matrix([Rational(0), Rational(0), Rational(15)])
        bottom_cut = MockCut(timber, cut_end_position, TimberReferenceEnd.BOTTOM)
        cut_timber = CutTimber(timber, cuts=[bottom_cut])
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg_local()
        
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
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add a top end cut at z=100
        cut_end_position = Matrix([Rational(0), Rational(0), Rational(100)])
        top_cut = MockCut(timber, cut_end_position, TimberReferenceEnd.TOP)
        cut_timber = CutTimber(timber, cuts=[top_cut])
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg_local()
        
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
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add both end cuts
        bottom_cut_pos = Matrix([Rational(0), Rational(0), Rational(20)])
        top_cut_pos = Matrix([Rational(0), Rational(0), Rational(90)])
        bottom_cut = MockCut(timber, bottom_cut_pos, TimberReferenceEnd.BOTTOM)
        top_cut = MockCut(timber, top_cut_pos, TimberReferenceEnd.TOP)
        cut_timber = CutTimber(timber, cuts=[bottom_cut, top_cut])
        
        # Get the CSG
        csg = cut_timber.render_timber_without_cuts_csg_local()
        
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
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add two bottom end cuts (invalid!)
        cut1 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(15)]), TimberReferenceEnd.BOTTOM)
        cut2 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(20)]), TimberReferenceEnd.BOTTOM)
        cut_timber = CutTimber(timber, cuts=[cut1, cut2])
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Bottom end has 2 end cuts"):
            cut_timber.render_timber_without_cuts_csg_local()
    
    def test_render_timber_without_cuts_multiple_top_cuts_error(self):
        """Test that multiple top end cuts raises an assertion error."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(10)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add two top end cuts (invalid!)
        cut1 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(100)]), TimberReferenceEnd.TOP)
        cut2 = MockCut(timber, Matrix([Rational(0), Rational(0), Rational(95)]), TimberReferenceEnd.TOP)
        cut_timber = CutTimber(timber, cuts=[cut1, cut2])
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Top end has 2 end cuts"):
            cut_timber.render_timber_without_cuts_csg_local()
    
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
        
        # Should be a Prism (since no cuts means no Difference operation)
        from code_goes_here.meowmeowcsg import Prism
        assert isinstance(csg, Prism)
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
        from code_goes_here.meowmeowcsg import HalfPlane
        # Create a half plane that cuts perpendicular to the timber length
        # Normal pointing in +Z direction, offset at 50
        half_plane = HalfPlane(
            normal=Matrix([Rational(0), Rational(0), Rational(1)]),
            offset=Rational(50)
        )
        cut = HalfPlaneCut(
            timber=timber,
            origin=Matrix([Rational(0), Rational(0), Rational(0)]),
            orientation=Orientation.identity(),
            half_plane=half_plane,
            maybe_end_cut=None
        )
        
        cut_timber = CutTimber(timber, cuts=[cut])
        
        # Get the CSG with cuts applied
        csg = cut_timber.render_timber_with_cuts_csg_local()
        
        # Should be a Difference operation
        from code_goes_here.meowmeowcsg import Difference
        assert isinstance(csg, Difference)
        assert isinstance(csg.base, Prism)
        assert len(csg.subtract) == 1
        assert isinstance(csg.subtract[0], HalfPlane)
    
    def test_render_timber_with_cuts_multiple_cuts(self):
        """Test render_timber_with_cuts_csg_local with multiple cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(0)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add two cuts
        from code_goes_here.meowmeowcsg import HalfPlane
        half_plane1 = HalfPlane(
            normal=Matrix([Rational(0), Rational(0), Rational(1)]),
            offset=Rational(25)
        )
        cut1 = HalfPlaneCut(
            timber=timber,
            origin=Matrix([Rational(0), Rational(0), Rational(0)]),
            orientation=Orientation.identity(),
            half_plane=half_plane1,
            maybe_end_cut=None
        )
        
        half_plane2 = HalfPlane(
            normal=Matrix([Rational(0), Rational(0), Rational(-1)]),
            offset=Rational(-75)
        )
        cut2 = HalfPlaneCut(
            timber=timber,
            origin=Matrix([Rational(0), Rational(0), Rational(0)]),
            orientation=Orientation.identity(),
            half_plane=half_plane2,
            maybe_end_cut=None
        )
        
        cut_timber = CutTimber(timber, cuts=[cut1, cut2])
        
        # Get the CSG with cuts applied
        csg = cut_timber.render_timber_with_cuts_csg_local()
        
        # Should be a Difference operation
        from code_goes_here.meowmeowcsg import Difference
        assert isinstance(csg, Difference)
        assert isinstance(csg.base, Prism)
        assert len(csg.subtract) == 2
        assert all(isinstance(sub, HalfPlane) for sub in csg.subtract)
    
    def test_render_timber_with_cuts_with_end_cuts(self):
        """Test render_timber_with_cuts_csg_local with end cuts."""
        length = Rational(100)
        size = Matrix([Rational(4), Rational(6)])
        bottom_position = Matrix([Rational(0), Rational(0), Rational(0)])
        length_direction = Matrix([Rational(0), Rational(0), Rational(1)])
        width_direction = Matrix([Rational(1), Rational(0), Rational(0)])
        
        timber = timber_from_directions(length, size, bottom_position, length_direction, width_direction)
        
        # Add an end cut at the top
        from code_goes_here.meowmeowcsg import HalfPlane
        half_plane = HalfPlane(
            normal=Matrix([Rational(0), Rational(0), Rational(-1)]),
            offset=Rational(-50)
        )
        end_cut = HalfPlaneCut(
            timber=timber,
            origin=Matrix([Rational(0), Rational(0), Rational(0)]),
            orientation=Orientation.identity(),
            half_plane=half_plane,
            maybe_end_cut=TimberReferenceEnd.TOP
        )
        
        cut_timber = CutTimber(timber, cuts=[end_cut])
        
        # Get the CSG with cuts applied
        csg = cut_timber.render_timber_with_cuts_csg_local()
        
        # Should be a Difference operation
        from code_goes_here.meowmeowcsg import Difference, Prism
        assert isinstance(csg, Difference)
        assert isinstance(csg.base, Prism)
        
        # Base prism should be semi-infinite at the top (end_distance = None)
        assert csg.base.start_distance == 0
        assert csg.base.end_distance is None
        
        # Should have one cut
        assert len(csg.subtract) == 1
        assert isinstance(csg.subtract[0], HalfPlane)


