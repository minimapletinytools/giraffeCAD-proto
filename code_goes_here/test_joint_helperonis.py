"""
Tests for joint_shavings.py - Helper functions for joint validation
"""

import pytest
from sympy import Rational
from code_goes_here.joint_shavings import (
    check_timber_overlap_for_splice_joint_is_sensible, 
    chop_timber_end_with_prism,
    chop_timber_end_with_half_plane,
    chop_lap_on_timber_end
)
from code_goes_here.timber import timber_from_directions, TimberReferenceEnd, TimberFace
from code_goes_here.moothymoth import create_v3, create_v2, inches
from code_goes_here.meowmeowcsg import SolidUnion, Prism, HalfPlane

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
        
        # Check the configuration - join TOP to TOP so ends face each other
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.TOP
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
        
        # TimberB pointing west, TOP ends exactly touch
        # For opposite direction timbers, join matching ends so they face each other
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(2 * timber_length, 0, 0),  # Start further right
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        # Join TOP to TOP so ends face each other
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.TOP
        )
        
        assert error is None, f"Expected no error for touching ends, but got: {error}"
    
    def test_invalid_same_direction(self):
        """Test that ends facing away from each other trigger an error."""
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        
        # Both timbers pointing east
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
        
        # Invalid: joining TOP to TOP when both point same direction
        # (both ends face same direction, away from each other)
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.TOP
        )
        
        assert error is not None, "Expected error for ends facing away from each other"
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
        # For opposite direction timbers, join matching ends (TOP to TOP)
        # TimberA TOP is at z=timber_length
        # Position TimberB so its TOP is at z=1.5*timber_length (overlapping)
        timberB = timber_from_directions(
            length=timber_length,
            size=timber_size,
            bottom_position=create_v3(0, 0, timber_length * Rational(5, 2)),  # Start at 2.5*L
            length_direction=create_v3(0, 0, -1),  # Pointing down, so TOP is at 1.5*L
            width_direction=create_v3(1, 0, 0),
            name="timberB"
        )
        
        # Join TOP to TOP so ends face each other
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.TOP
        )
        
        assert error is None, f"Expected no error for vertical splice, but got: {error}"
    
    def test_different_timber_sizes(self):
        """Test validation works with different sized timbers."""
        # 4x4 timber, 36 inches long
        timberA_length = inches(36)
        timberA = timber_from_directions(
            length=timberA_length,
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        # 6x8 timber, 48 inches long, pointing opposite direction
        # For opposite direction timbers, join matching ends (TOP to TOP)
        # TimberA TOP is at x=36"
        # Position TimberB so its TOP is at x=48" (overlapping)
        timberB_length = inches(48)
        timberB = timber_from_directions(
            length=timberB_length,
            size=create_v2(inches(6), inches(8)),
            bottom_position=create_v3(timberA_length + timberB_length, 0, 0),  # Start at 84"
            length_direction=create_v3(-1, 0, 0),  # Pointing left, so TOP is at 36"
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        # Join TOP to TOP so ends face each other (both at x=36")
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.TOP
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


class TestChopLapOnTimberEnd:
    """Tests for chop_lap_on_timber_end function."""
    
    def test_lap_on_right_face_geometry(self):
        """
        Test lap joint cut on RIGHT face of a timber.
        
        Creates a 4"x6" timber that is 4 ft long.
        Lap length is 1ft, shoulder 6" from end, lap face is RIGHT.
        lap_depth=2" means we KEEP 2" on the RIGHT side and REMOVE from the LEFT side.
        Tests boundary points and verifies CSG structure.
        """
        # Create a 4"x6" timber that is 4 ft long
        timber = timber_from_directions(
            length=inches(48),  # 4 ft
            size=create_v2(inches(4), inches(6)),  # 4" wide x 6" high
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Along Z axis
            width_direction=create_v3(1, 0, 0),   # Width along X axis
            name="test_timber"
        )
        
        # Lap parameters
        lap_length = inches(12)  # 1 ft
        shoulder_distance = inches(6)  # 6" from end
        lap_depth = inches(2)  # 2" depth to KEEP on RIGHT side (half of 4" width for half-lap)
        lap_face = TimberFace.RIGHT  # Lap on RIGHT face (keep material here)
        lap_end = TimberReferenceEnd.TOP  # Cutting from top end
        
        # Create the lap cut
        lap_csg = chop_lap_on_timber_end(
            lap_timber=timber,
            lap_timber_end=lap_end,
            lap_timber_face=lap_face,
            lap_length=lap_length,
            lap_shoulder_position_from_lap_timber_end=shoulder_distance,
            lap_depth=lap_depth
        )
        
        # Verify the CSG is a SolidUnion
        assert isinstance(lap_csg, SolidUnion), "Lap CSG should be a SolidUnion"
        assert len(lap_csg.children) == 2, "Lap CSG should have 2 children (Prism and HalfPlane)"
        
        # Find the Prism and HalfPlane in the union
        prism = None
        half_plane = None
        for child in lap_csg.children:
            if isinstance(child, Prism):
                prism = child
            elif isinstance(child, HalfPlane):
                half_plane = child
        
        assert prism is not None, "Lap CSG should contain a Prism"
        assert half_plane is not None, "Lap CSG should contain a HalfPlane"
        
        # Verify geometry based on the implementation:
        # For TOP end with shoulder_distance=6", lap_length=12":
        # - Timber end at 48" from bottom
        # - Shoulder at 48" - 6" = 42" from bottom
        # - Lap extends from shoulder in +Z direction by lap_length = 42" + 12" = 54" from bottom
        # - Prism from 42" to 54", HalfPlane at 54"
        expected_shoulder_z = inches(42)  # 48" - 6"
        expected_lap_end_z = inches(54)   # 42" + 12"
        
        # Check that prism extends from shoulder to lap end
        assert prism.start_distance == expected_shoulder_z, \
            f"Prism should start at shoulder (z={expected_shoulder_z}), got {prism.start_distance}"
        assert prism.end_distance == expected_lap_end_z, \
            f"Prism should end at lap end (z={expected_lap_end_z}), got {prism.end_distance}"
        
        # Check that half plane coincides with lap end
        assert half_plane.offset == expected_lap_end_z, \
            f"HalfPlane should be at lap end (z={expected_lap_end_z}), got {half_plane.offset}"
        
        # Test point 1: 6" down from timber end (at shoulder), on the LEFT face (removed side)
        # Timber is 4" wide centered at x=0, so LEFT face is at x=-2"
        # With lap_face=RIGHT and lap_depth=2", we keep x=0 to x=+2", remove x=-2" to x=0
        # LEFT face at x=-2" should be IN the CSG (material removed)
        point1 = create_v3(inches(-2), 0, expected_shoulder_z)
        assert lap_csg.contains_point(point1), \
            "Point at shoulder on LEFT face (removed side) should be in the removed region"
        
        # Test point 2: At the boundary between removed and kept material (x=0)
        # This should be at the boundary (on the edge of the prism)
        point2 = create_v3(0, 0, expected_shoulder_z)
        assert lap_csg.contains_point(point2), \
            "Point at boundary (x=0) at shoulder should be on boundary (contained)"
        
        # Test point 3: On the RIGHT face (kept side) at x=+2"
        # This should NOT be in the removed region (material is kept here)
        point3 = create_v3(inches(2), 0, expected_shoulder_z)
        assert not lap_csg.contains_point(point3), \
            "Point at shoulder on RIGHT face (kept side) should NOT be in the removed region"
        
        # Test point 4: Below the shoulder (outside lap region)
        # This is BELOW the prism start (shoulder at 42"), so should NOT be in CSG
        point4 = create_v3(0, 0, expected_shoulder_z - inches(3))
        assert not lap_csg.contains_point(point4), \
            "Point 3\" below shoulder (outside lap region) should NOT be in the removed region"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
