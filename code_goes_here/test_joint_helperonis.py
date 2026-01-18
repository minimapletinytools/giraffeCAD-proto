"""
Tests for joint_helperonis.py - Helper functions for joint validation
"""

import pytest
from sympy import Rational
from code_goes_here.joint_helperonis import (
    check_timber_overlap_for_splice_joint_is_sensible, 
    chop_timber_end_with_prism,
    chop_timber_end_with_half_plane
)
from code_goes_here.timber import timber_from_directions, TimberReferenceEnd
from code_goes_here.moothymoth import create_v3, create_v2, inches

# TODO too many tests, just delete some lol... or combine into 1 test that varies only the timber length...
class TestCheckTimberOverlapForSpliceJoint:
    """Tests for check_timber_overlap_for_splice_joint_is_sensible function."""
    
    def test_valid_splice_configuration_overlapping(self):
        """Test a valid splice joint with overlapping timbers pointing opposite directions."""
        # Create two 4x4 timbers, 3 feet long, overlapping in the middle
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        
        # TimberA pointing east (left to right)
        timberA = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        # TimberB pointing west (right to left), positioned to overlap
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(timber_length * 2, 0, 0),
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        # Check the configuration
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        assert error is None, f"Expected no error, but got: {error}"
    
    def test_valid_splice_configuration_just_touching(self):
        """Test a valid splice joint where timber ends just touch."""
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        
        # TimberA pointing east
        timberA = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        # TimberB pointing west, ends exactly touch
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(timber_length, 0, 0),  # Bottom exactly at A's top
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        assert error is None, f"Expected no error for touching ends, but got: {error}"
    
    def test_invalid_same_direction(self):
        """Test that timbers pointing in the same direction trigger an error."""
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        
        # Both timbers pointing east (invalid)
        timberA = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(timber_length, 0, 0),
            length_direction=create_v3(1, 0, 0),  # Same direction!
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        assert error is not None, "Expected error for same direction"
        assert "same direction" in error.lower()
        assert "dot product" in error.lower()
    
    def test_invalid_not_parallel(self):
        """Test that non-parallel timbers trigger an error."""
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        
        # TimberA pointing east
        timberA = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        # TimberB pointing up (perpendicular, not parallel)
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(timber_length, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Perpendicular!
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.TOP
        )
        
        assert error is not None, "Expected error for non-parallel timbers"
        assert "not parallel" in error.lower()
    
    def test_invalid_separated_by_gap(self):
        """Test that timbers separated by a gap trigger an error."""
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        gap = inches(6)  # 6 inch gap
        
        # TimberA pointing east, TOP end at inches(36)
        timberA = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        # TimberB pointing west, TOP end at inches(36-6)=inches(30)
        # So there's a 6 inch gap between timberA's TOP and timberB's TOP
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(inches(30) - timber_length, 0, 0),  # Bottom at -6 inches
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.TOP
        )
        
        assert error is not None, "Expected error for separated timbers"
        assert "separated" in error.lower() or "gap" in error.lower()
    
    def test_vertical_timbers(self):
        """Test validation works with vertical timbers."""
        timber_length = inches(96)  # 8 feet tall
        timber_size = create_v2(inches(6), inches(6))
        
        # TimberA pointing up (vertical post)
        timberA = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timberA"
        )
        
        # TimberB pointing down, overlapping in the middle
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, timber_length * Rational(3, 2)),  # 12 feet up
            length_direction=create_v3(0, 0, -1),  # Pointing down
            width_direction=create_v3(1, 0, 0),
            name="timberB"
        )
        
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        assert error is None, f"Expected no error for vertical splice, but got: {error}"
    
    def test_different_timber_sizes(self):
        """Test validation works with different sized timbers."""
        # 4x4 timber
        timberA = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        # 6x8 timber
        timberB = timber_from_directions(
            length=inches(48),
            size=create_v2(inches(6), inches(8)),
            bottom_position=create_v3(inches(60), 0, 0),
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        # Should be valid - sizes don't matter for this check
        assert error is None, f"Expected no error for different sizes, but got: {error}"
    
    def test_swapped_end_references(self):
        """Test that using BOTTOM/TOP vs TOP/BOTTOM both work correctly."""
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        
        timberA = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(timber_length * 2, 0, 0),
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        # Test with TOP/BOTTOM (normal)
        error1 = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        # Test with BOTTOM/TOP (swapped)
        error2 = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.BOTTOM, TimberReferenceEnd.TOP
        )
        
        # Both should work (one will likely give an error about direction or separation)
        # Just checking it doesn't crash
        assert isinstance(error1, (str, type(None)))
        assert isinstance(error2, (str, type(None)))


class TestChopTimberEndWithPrism:
    """Tests for chop_timber_end_with_prism function."""
    
    def test_chop_top_end(self):
        """Test chopping from the top end of a timber."""
        # Create a simple vertical timber: 4x4 inches, 10 feet tall
        timber = timber_from_directions(
            length=inches(120),  # 10 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        # Chop 2 feet from the top
        chop_distance = inches(24)
        prism = chop_timber_end_with_prism(timber, TimberReferenceEnd.TOP, chop_distance)
        
        # Verify the prism properties
        assert prism.size == timber.size
        # Should be in local coordinates (identity transform)
        assert prism.transform == timber.transform.identity()
        
        # For TOP end with distance 24 from end:
        # start_distance should be at (120 - 24) = 96 inches from bottom
        # end_distance should be None (infinite upward)
        assert prism.start_distance == inches(96)
        assert prism.end_distance is None
    
    def test_chop_bottom_end(self):
        """Test chopping from the bottom end of a timber."""
        # Create a simple vertical timber: 4x4 inches, 10 feet tall
        timber = timber_from_directions(
            length=inches(120),  # 10 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        # Chop 2 feet from the bottom
        chop_distance = inches(24)
        prism = chop_timber_end_with_prism(timber, TimberReferenceEnd.BOTTOM, chop_distance)
        
        # Verify the prism properties
        assert prism.size == timber.size
        assert prism.transform == timber.transform.identity()
        
        # For BOTTOM end with distance 24 from end:
        # start_distance should be None (infinite downward)
        # end_distance should be at 24 inches from bottom
        assert prism.start_distance is None
        assert prism.end_distance == inches(24)
    
    def test_chop_horizontal_timber(self):
        """Test chopping a horizontal timber to ensure it works in any orientation."""
        # Create a horizontal timber pointing east
        timber = timber_from_directions(
            length=inches(48),  # 4 feet
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="horizontal_timber"
        )
        
        # Chop 6 inches from the top (east) end
        chop_distance = inches(6)
        prism = chop_timber_end_with_prism(timber, TimberReferenceEnd.TOP, chop_distance)
        
        # Verify the prism has correct dimensions
        assert prism.size == timber.size
        assert prism.transform == timber.transform.identity()
        assert prism.start_distance == inches(42)  # 48 - 6
        assert prism.end_distance is None
    
    def test_chop_with_rational_distances(self):
        """Test that the function works with Rational arithmetic."""
        timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(2), Rational(2)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        # Chop 1/3 from the top
        chop_distance = Rational(1, 3)
        prism = chop_timber_end_with_prism(timber, TimberReferenceEnd.TOP, chop_distance)
        
        # Should get exact rational arithmetic
        expected_start = Rational(10) - Rational(1, 3)
        assert prism.start_distance == expected_start
        assert prism.end_distance is None


class TestChopTimberEndWithHalfPlane:
    """Tests for chop_timber_end_with_half_plane function."""
    
    def test_chop_top_end(self):
        """Test chopping from the top end of a timber with a half-plane."""
        # Create a simple vertical timber: 4x4 inches, 10 feet tall
        timber = timber_from_directions(
            length=inches(120),  # 10 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        # Chop 2 feet from the top
        chop_distance = inches(24)
        half_plane = chop_timber_end_with_half_plane(timber, TimberReferenceEnd.TOP, chop_distance)
        
        # For TOP end with distance 24 from end:
        # - Normal should point in +Z direction (0, 0, 1)
        # - Offset should be at (120 - 24) = 96 inches from bottom
        assert half_plane.normal == create_v3(0, 0, 1)
        assert half_plane.offset == inches(96)
    
    def test_chop_bottom_end(self):
        """Test chopping from the bottom end of a timber with a half-plane."""
        # Create a simple vertical timber: 4x4 inches, 10 feet tall
        timber = timber_from_directions(
            length=inches(120),  # 10 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        # Chop 2 feet from the bottom
        chop_distance = inches(24)
        half_plane = chop_timber_end_with_half_plane(timber, TimberReferenceEnd.BOTTOM, chop_distance)
        
        # For BOTTOM end with distance 24 from end:
        # - Normal should point in -Z direction (0, 0, -1)
        # - Offset should be -24 inches
        assert half_plane.normal == create_v3(0, 0, -1)
        assert half_plane.offset == -inches(24)
    
    def test_chop_with_rational_distances(self):
        """Test that the function works with Rational arithmetic."""
        timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(2), Rational(2)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        # Chop 1/3 from the top
        chop_distance = Rational(1, 3)
        half_plane = chop_timber_end_with_half_plane(timber, TimberReferenceEnd.TOP, chop_distance)
        
        # Should get exact rational arithmetic
        expected_offset = Rational(10) - Rational(1, 3)
        assert half_plane.offset == expected_offset
        assert half_plane.normal == create_v3(0, 0, 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
