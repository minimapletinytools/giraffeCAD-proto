"""
Tests for joint_shavings.py - Helper functions for joint validation
"""

import pytest
from sympy import Rational
from code_goes_here.joint_shavings import (
    check_timber_overlap_for_splice_joint_is_sensible, 
    chop_timber_end_with_prism,
    chop_timber_end_with_half_plane,
    chop_lap_on_timber_end,
    scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber,
    find_opposing_face_on_another_timber,
    chop_shoulder_notch_on_timber_face,
    deprecated_find_face_plane_intersection_on_centerline,
    scribe_face_plane_onto_centerline,
    find_projected_intersection_on_centerlines
)
from code_goes_here.timber import timber_from_directions, TimberReferenceEnd, TimberFace, TimberLongFace
from code_goes_here.moothymoth import create_v3, create_v2, inches, are_vectors_parallel
from code_goes_here.meowmeowcsg import SolidUnion, RectangularPrism, HalfSpace

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
        # For timbers pointing opposite directions, join matching ends (TOP to TOP)
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
    
    def test_valid_same_direction_opposite_ends(self):
        """Test that same direction timbers can have valid splice when joining opposite ends (oscarshed case)."""
        timber_length = inches(36)
        timber_size = create_v2(inches(4), inches(4))
        
        # Both timbers pointing east (e.g., split from same timber)
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
        
        # Valid: joining TOP to BOTTOM when both point same direction
        # (ends face towards each other)
        error = check_timber_overlap_for_splice_joint_is_sensible(
            timberA, timberB, TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        assert error is None, f"Expected no error for same direction opposite ends (oscarshed case), but got: {error}"
    
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


class TestChopTimberEndWithHalfspace:
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
        assert len(lap_csg.children) == 2, "Lap CSG should have 2 children (RectangularPrism and HalfSpace)"
        
        # Find the RectangularPrism and HalfSpace in the union
        prism = None
        half_plane = None
        for child in lap_csg.children:
            if isinstance(child, RectangularPrism):
                prism = child
            elif isinstance(child, HalfSpace):
                half_plane = child
        
        assert prism is not None, "Lap CSG should contain a RectangularPrism"
        assert half_plane is not None, "Lap CSG should contain a HalfSpace"
        
        # Verify geometry based on the implementation:
        # For TOP end with shoulder_distance=6", lap_length=12":
        # - Timber end at 48" from bottom
        # - Shoulder at 48" - 6" = 42" from bottom
        # - Lap extends from shoulder in +Z direction by lap_length = 42" + 12" = 54" from bottom
        # - RectangularPrism from 42" to 54", HalfSpace at 54"
        expected_shoulder_z = inches(42)  # 48" - 6"
        expected_lap_end_z = inches(54)   # 42" + 12"
        
        # Check that prism extends from shoulder to lap end
        assert prism.start_distance == expected_shoulder_z, \
            f"RectangularPrism should start at shoulder (z={expected_shoulder_z}), got {prism.start_distance}"
        assert prism.end_distance == expected_lap_end_z, \
            f"RectangularPrism should end at lap end (z={expected_lap_end_z}), got {prism.end_distance}"
        
        # Check that half plane coincides with lap end
        assert half_plane.offset == expected_lap_end_z, \
            f"HalfSpace should be at lap end (z={expected_lap_end_z}), got {half_plane.offset}"
        
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


class TestMeasureDistanceFromFaceOnTimberWrtOpposingFaceOnAnotherTimber:
    """Tests for scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber function."""
    
    def test_aligned_parallel_timbers_same_size(self):
        """Test measuring distance between two aligned, parallel timbers of the same size."""
        # Create two 4x6 timbers, face-aligned, pointing opposite directions
        timber_size = create_v2(inches(4), inches(6))
        
        # Top timber pointing east (left to right), centered at x=18, y=0, z=6
        top_timber = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(0, 0, inches(6)),  # Positioned 6 inches above bottom timber
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="top_timber"
        )
        
        # Bottom timber pointing west (right to left), need to flip width_direction to make height_direction opposite
        # For opposing BACK/FRONT faces, we need opposite height_directions
        bottom_timber = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(inches(36), 0, 0),
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, -1, 0),  # Flipped to get height_direction = (0,0,1)
            name="bottom_timber"
        )
        
        # Measure distance from BACK face of top timber with 2" depth to opposing FRONT face of bottom timber
        # Top timber's BACK face points in -Z direction (down): (0, 0, -1)
        # Bottom timber's FRONT face points in +Z direction (up): (0, 0, 1)
        depth_from_top = inches(2)
        
        distance = scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberLongFace.BACK,
            reference_depth_from_face=depth_from_top,
            target_timber=bottom_timber
        )
        
        # Expected distance calculation:
        # - Top timber: height_direction = (0,0,1), bottom at z=6"
        # - Top timber's BACK face center is at z = 6" + (-1)*(6"/2) = 6" - 3" = 3"
        # - With 2" depth inward (opposite of BACK normal): cutting plane at z = 3" + 2" = 5"
        # - Bottom timber: height_direction = (0,0,1), bottom at z=0"
        # - Bottom timber's FRONT face center is at z = 0" + 1*(6"/2) = 3"
        # - Distance = |5" - 3"| = 2"
        expected_distance = inches(2)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_aligned_parallel_timbers_different_sizes(self):
        """Test measuring distance between two aligned timbers of different sizes."""
        # Create two timbers, face-aligned but different sizes
        # Top timber: 4x6
        top_timber = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(6)),
            bottom_position=create_v3(0, 0, inches(8)),  # Positioned 8 inches above bottom timber
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="top_timber"
        )
        
        # Bottom timber: 6x8
        bottom_timber = timber_from_directions(
            length=inches(48),
            size=create_v2(inches(6), inches(8)),
            bottom_position=create_v3(inches(36), 0, 0),
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="bottom_timber"
        )
        
        # Measure distance from BACK face of top timber with 3" depth
        depth_from_top = inches(3)
        
        distance = scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberLongFace.BACK,
            reference_depth_from_face=depth_from_top,
            target_timber=bottom_timber
        )
        
        # Expected distance calculation:
        # - Top timber's BACK face is at z=8" + 6"/2 = 11"
        # - With 3" depth inward: cutting plane at z = 11" - 3" = 8"
        # - Bottom timber's FRONT face is at z=0" + 8"/2 = 4"
        # - Distance = |8" - 4"| = 4"
        expected_distance = inches(4)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_vertical_timbers(self):
        """Test measuring distance between two vertical face-aligned timbers."""
        # Create two vertical timbers (posts), face-aligned
        # Top timber pointing down
        top_timber = timber_from_directions(
            length=inches(96),
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(0, 0, inches(144)),  # 12 feet up
            length_direction=create_v3(0, 0, -1),  # Pointing down
            width_direction=create_v3(1, 0, 0),
            name="top_timber"
        )
        
        # Bottom timber pointing up
        bottom_timber = timber_from_directions(
            length=inches(96),
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="bottom_timber"
        )
        
        # Measure distance from RIGHT face of top timber with 2" depth
        depth_from_top = inches(2)
        
        distance = scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberLongFace.RIGHT,
            reference_depth_from_face=depth_from_top,
            target_timber=bottom_timber
        )
        
        # Expected distance calculation:
        # - Top timber's RIGHT face is at x=0 + 6"/2 = 3"
        # - With 2" depth inward: cutting plane at x = 3" - 2" = 1"
        # - Bottom timber's LEFT face is at x=0 - 6"/2 = -3"
        # - Distance = |1" - (-3")| = 4"
        expected_distance = inches(4)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_assertion_fails_for_non_parallel_face_timbers(self):
        """Test that the function asserts when target timber has no long face parallel to reference face."""
        # Create two timbers that are NOT face-aligned
        # To be non-face-aligned, none of timber1's directions can be parallel to any of timber2's directions
        from sympy import sqrt
        
        # Top timber at standard orientation
        top_timber = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(6)),
            bottom_position=create_v3(0, 0, inches(6)),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="top_timber"
        )
        
        # Bottom timber with arbitrary non-axis-aligned orientation
        # Use directions that don't align with any of the top timber's axes
        # length_direction = (1,1,1)/sqrt(3), width_direction = (1,-1,0)/sqrt(2)
        v1 = create_v3(1, 1, 1)
        v1_norm = v1 / sqrt(3)
        v2 = create_v3(1, -1, 0)
        v2_norm = v2 / sqrt(2)
        
        bottom_timber = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(6)),
            bottom_position=create_v3(inches(36), 0, 0),
            length_direction=v1_norm,
            width_direction=v2_norm,
            name="bottom_timber"
        )
        
        # Should raise an AssertionError
        with pytest.raises(AssertionError) as excinfo:
            scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
                reference_timber=top_timber,
                reference_face=TimberLongFace.BACK,
                reference_depth_from_face=inches(2),
                target_timber=bottom_timber
            )
        
        # Check that the error message mentions parallel faces
        assert "parallel" in str(excinfo.value).lower()
    
    def test_with_rational_arithmetic(self):
        """Test that the function works correctly with exact Rational arithmetic."""
        # Create two timbers with Rational dimensions
        top_timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(2), Rational(3)),
            bottom_position=create_v3(0, 0, Rational(3)),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="top_timber"
        )
        
        bottom_timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(2), Rational(3)),
            bottom_position=create_v3(Rational(10), 0, 0),
            length_direction=create_v3(-1, 0, 0),
            width_direction=create_v3(0, -1, 0),  # Flipped to get opposing height_direction
            name="bottom_timber"
        )
        
        # Measure with Rational depth
        depth = Rational(1, 2)
        
        distance = scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberLongFace.BACK,
            reference_depth_from_face=depth,
            target_timber=bottom_timber
        )
        
        # Expected: 
        # - Top timber: height_dir=(0,0,1), bottom at z=3
        # - Top BACK face at z = 3 + (-1)*(3/2) = 3 - 3/2 = 3/2
        # - Cut plane at z = 3/2 + 1/2 = 2
        # - Bottom timber: height_dir=(0,0,1), bottom at z=0
        # - Bottom FRONT face at z = 0 + 1*(3/2) = 3/2
        # - Distance = |2 - 3/2| = 1/2
        expected_distance = Rational(1, 2)
        assert distance == expected_distance, \
            f"Expected exact rational {expected_distance}, got {distance}"


class TestFindOpposingFaceOnAnotherTimber:
    """Tests for find_opposing_face_on_another_timber function."""
    
    def test_face_aligned_timbers(self):
        """Test finding opposing face on two face-aligned timbers."""
        # Create two 4x6 timbers that are face-aligned
        timber_size = create_v2(inches(4), inches(6))
        
        # Timber A pointing east (along X-axis)
        timber_a = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # East
            width_direction=create_v3(0, 1, 0),   # North
            name="timber_a"
        )
        # Timber A has:
        # - length_direction = (1, 0, 0) = East
        # - width_direction = (0, 1, 0) = North
        # - height_direction = (0, 0, 1) = Up
        # - RIGHT face points North: (0, 1, 0)
        # - LEFT face points South: (0, -1, 0)
        # - FRONT face points Up: (0, 0, 1)
        # - BACK face points Down: (0, 0, -1)
        
        # Timber B pointing east, offset in Y direction (north)
        timber_b = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(0, inches(10), 0),  # 10 inches north
            length_direction=create_v3(1, 0, 0),  # East
            width_direction=create_v3(0, 1, 0),   # North
            name="timber_b"
        )
        # Timber B has same orientation as Timber A
        # - RIGHT face points North: (0, 1, 0)
        # - LEFT face points South: (0, -1, 0)
        
        # Find opposing face: Timber A's RIGHT face (North) should oppose Timber B's LEFT face (South)
        opposing_face = find_opposing_face_on_another_timber(
            reference_timber=timber_a,
            reference_face=TimberLongFace.RIGHT,
            target_timber=timber_b
        )
        
        # The opposing face should be LEFT (which points South, opposite of RIGHT which points North)
        assert opposing_face == TimberFace.LEFT, \
            f"Expected LEFT face, got {opposing_face}"
        
        # Verify the faces are parallel by checking their directions
        reference_direction = timber_a.get_face_direction_global(TimberLongFace.RIGHT)
        target_direction = timber_b.get_face_direction_global(opposing_face)
        assert are_vectors_parallel(reference_direction, target_direction), \
            "Reference and target faces should be parallel"
    
    def test_timbers_at_30_degrees_in_xy_plane(self):
        """Test finding opposing face on two timbers at 30 degrees to each other in the XY plane."""
        from sympy import cos, sin, pi, sqrt
        
        # Both timbers lying flat in XY plane (height points up in Z)
        timber_size = create_v2(inches(4), inches(6))
        
        # Timber A pointing along X-axis (East)
        timber_a = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # East
            width_direction=create_v3(0, 1, 0),   # North
            name="timber_a"
        )
        # Timber A:
        # - length_direction = (1, 0, 0) = East
        # - width_direction = (0, 1, 0) = North  
        # - height_direction = (0, 0, 1) = Up
        # - RIGHT face points North: (0, 1, 0)
        # - BACK face points Down: (0, 0, -1)
        # - FRONT face points Up: (0, 0, 1)
        
        # Timber B at 30 degrees counterclockwise from X-axis in XY plane
        # length_direction at 30 degrees: (cos(30°), sin(30°), 0)
        angle = pi / 6  # 30 degrees in radians
        length_dir_b = create_v3(cos(angle), sin(angle), 0)
        
        # width_direction perpendicular to length in XY plane: (-sin(30°), cos(30°), 0)
        width_dir_b = create_v3(-sin(angle), cos(angle), 0)
        
        timber_b = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(inches(20), 0, 0),
            length_direction=length_dir_b,
            width_direction=width_dir_b,
            name="timber_b"
        )
        # Timber B:
        # - length_direction = (cos(30°), sin(30°), 0) ≈ (0.866, 0.5, 0)
        # - width_direction = (-sin(30°), cos(30°), 0) ≈ (-0.5, 0.866, 0)
        # - height_direction = (0, 0, 1) = Up (same as Timber A)
        # - FRONT face points Up: (0, 0, 1) - parallel to Timber A's FRONT
        # - BACK face points Down: (0, 0, -1) - parallel to Timber A's BACK
        
        # Find opposing face: Timber A's FRONT face (Up) should oppose Timber B's BACK face (Down)
        opposing_face = find_opposing_face_on_another_timber(
            reference_timber=timber_a,
            reference_face=TimberLongFace.FRONT,
            target_timber=timber_b
        )
        
        # The opposing face should be BACK (which points Down, opposite of FRONT which points Up)
        assert opposing_face == TimberFace.BACK, \
            f"Expected BACK face, got {opposing_face}"
        
        # Verify the faces are parallel by checking their directions
        reference_direction = timber_a.get_face_direction_global(TimberLongFace.FRONT)
        target_direction = timber_b.get_face_direction_global(opposing_face)
        assert are_vectors_parallel(reference_direction, target_direction), \
            "Reference and target faces should be parallel"
        
        # Also verify that they point in opposite directions
        dot_product = reference_direction.dot(target_direction)
        assert dot_product < 0, \
            f"Faces should point in opposite directions (negative dot product), got {dot_product}"
    
    def test_assertion_fails_for_non_parallel_faces(self):
        """Test that the function raises an assertion error when no parallel face exists."""
        timber_size = create_v2(inches(4), inches(6))
        
        # Timber A pointing east
        timber_a = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # East
            width_direction=create_v3(0, 1, 0),   # North
            name="timber_a"
        )
        
        # Timber B pointing up (perpendicular to Timber A)
        # This timber has no faces parallel to Timber A's RIGHT face
        timber_b = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(inches(20), 0, 0),
            length_direction=create_v3(0, 0, 1),  # Up
            width_direction=create_v3(1, 0, 0),   # East
            name="timber_b"
        )
        # Timber B:
        # - length_direction = (0, 0, 1) = Up
        # - width_direction = (1, 0, 0) = East
        # - height_direction = (0, 1, 0) = North
        # - RIGHT face points East: (1, 0, 0)
        # - FRONT face points North: (0, 1, 0)
        # - BACK face points South: (0, -1, 0)
        # None of these are parallel to Timber A's RIGHT face which points North (0, 1, 0)
        # Actually wait, FRONT points North which IS parallel to Timber A's RIGHT
        
        # Let me use a more complex orientation
        from sympy import sqrt
        
        # Timber B with non-axis-aligned orientation
        timber_b = timber_from_directions(
            length=inches(36),
            size=timber_size,
            bottom_position=create_v3(inches(20), 0, 0),
            length_direction=create_v3(1, 1, 1) / sqrt(3),  # Diagonal direction
            width_direction=create_v3(-1, 1, 0) / sqrt(2),  # Perpendicular in a different plane
            name="timber_b"
        )
        
        # Should raise an AssertionError because no face on timber_b is parallel to timber_a's RIGHT face
        with pytest.raises(AssertionError) as excinfo:
            find_opposing_face_on_another_timber(
                reference_timber=timber_a,
                reference_face=TimberLongFace.RIGHT,
                target_timber=timber_b
            )
        
        # Check that the error message mentions parallel
        assert "parallel" in str(excinfo.value).lower()


class TestChopShoulderNotchOnTimberFace:
    """Tests for chop_shoulder_notch_on_timber_face function."""
    
    def test_shoulder_notch_on_each_face(self):
        """
        Test that shoulder notch correctly removes material from the specified face only.
        
        For each long face (LEFT, RIGHT, FRONT, BACK), create a notch and verify:
        - A point on the notched face (in the middle) IS contained in the notch CSG (will be removed)
        - Points on the other three faces are NOT contained in the notch CSG (will remain)
        """
        # Create a vertical 4"x4"x4' timber
        timber_width = inches(4)
        timber_height = inches(4)
        timber_length = inches(48)  # 4 feet
        
        timber = timber_from_directions(
            length=timber_length,
            size=create_v2(timber_width, timber_height),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Vertical (along Z)
            width_direction=create_v3(1, 0, 0),   # Width along X
            name='test_timber'
        )
        # Timber orientation:
        # - width_direction (X): RIGHT face at +X, LEFT face at -X
        # - height_direction (Y): FRONT face at +Y, BACK face at -Y
        # - length_direction (Z): TOP face at +Z, BOTTOM face at -Z
        
        # Notch parameters
        notch_depth = inches(1)    # 1" deep into the timber
        notch_width = inches(4)    # 4" wide along timber length
        notch_center = timber_length / Rational(2)  # Middle of timber (24" from bottom)
        
        # Test each long face
        long_faces = [TimberFace.LEFT, TimberFace.RIGHT, TimberFace.FRONT, TimberFace.BACK]
        
        for notch_face in long_faces:
            # Create the shoulder notch on this face
            notch_csg = chop_shoulder_notch_on_timber_face(
                timber=timber,
                notch_face=notch_face,
                distance_along_timber=notch_center,
                notch_width=notch_width,
                notch_depth=notch_depth
            )
            
            # Verify it's a RectangularPrism
            assert isinstance(notch_csg, RectangularPrism), f"Expected RectangularPrism, got {type(notch_csg).__name__}"
            
            # Define test points on each face at the middle of the timber
            # All points are at the center height (notch_center) and centered on the timber cross-section
            # but offset to be on the surface of each face
            half_width = timber_width / Rational(2)
            half_height = timber_height / Rational(2)
            
            # Points on each face (on the surface, at the middle of timber length)
            test_points = {
                TimberFace.RIGHT: create_v3(half_width, 0, notch_center),
                TimberFace.LEFT: create_v3(-half_width, 0, notch_center),
                TimberFace.FRONT: create_v3(0, half_height, notch_center),
                TimberFace.BACK: create_v3(0, -half_height, notch_center)
            }
            
            # Test each point
            for test_face, test_point in test_points.items():
                point_contained = notch_csg.contains_point(test_point)
                
                if test_face == notch_face:
                    # Point on the notched face should be contained in the notch CSG (will be removed)
                    assert point_contained, \
                        f"Point on notched face {notch_face.name} should be contained in notch CSG, but was not"
                else:
                    # Points on other faces should NOT be contained in the notch CSG (will remain)
                    assert not point_contained, \
                        f"Point on face {test_face.name} should NOT be contained in notch on {notch_face.name}, but was"


class TestScribeFaceOnCenterline:
    """Tests for scribe_face_plane_onto_centerline function."""
    
    def test_horizontal_timbers_butt_joint(self):
        """
        Test scribing from timber_a's TOP end to timber_b's LEFT face.
        
        Classic butt joint scenario: horizontal timber approaching a vertical face.
        """
        # Create timber_a pointing east (horizontal)
        timber_a = timber_from_directions(
            length=inches(48),  # 4 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, inches(4)),  # 4 inches above ground
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="timber_a"
        )
        # timber_a's TOP end is at (48", 0, 4"), centerline runs along x-axis
        
        # Create timber_b vertical with LEFT face that will intersect timber_a's centerline
        timber_b = timber_from_directions(
            length=inches(96),  # 8 feet tall
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(inches(60), 0, 0),  # Bottom at x=60"
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_b"
        )
        # timber_b's LEFT face is at x = 60" - 3" = 57" (normal pointing in -x direction)
        
        # Scribe from timber_a's TOP end to timber_b's LEFT face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.LEFT,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.TOP
        )
        
        # Expected calculation (true geometric intersection):
        # - timber_a's centerline: P = (48", 0, 4") + t*(-1, 0, 0) [measuring from TOP, going backward]
        # - timber_b's LEFT face plane: normal = (-1, 0, 0), plane at x = 57"
        # - Intersection: -1 * (x - 57") = 0 => x = 57"
        # - From line: 48" - t = 57" => t = -9"
        # - Negative means we need to go backward from the TOP end (past the end)
        expected_distance = inches(-9)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_vertical_timbers_face_to_face(self):
        """
        Test scribing between a vertical timber and a horizontal timber's vertical face.
        """
        # Create timber_a pointing up
        timber_a = timber_from_directions(
            length=inches(96),  # 8 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_a"
        )
        # timber_a's TOP end is at (0, 0, 96"), centerline runs along z-axis
        
        # Create timber_b horizontal so its BACK face (pointing down) intersects timber_a's centerline
        timber_b = timber_from_directions(
            length=inches(48),  # 4 feet
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(inches(-10), 0, inches(50)),  # BACK face at z=50"-3"=47"
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="timber_b"
        )
        # timber_b's BACK face is at z = 50" - 3" = 47" (normal pointing in -z direction, downward)
        
        # Scribe from timber_a's TOP end to timber_b's BACK face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.BACK,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.TOP
        )
        
        # Expected calculation (true geometric intersection):
        # - timber_a's centerline: P = (0, 0, 96") + t*(0, 0, -1) [measuring from TOP, going down]
        # - timber_b's BACK face plane: normal = (0, 0, -1), plane at z = 47"
        # - Intersection: -1 * (z - 47") = 0 => z = 47"
        # - From line: 96" - t = 47" => t = 49"
        # - Positive means going into the timber from the TOP end
        expected_distance = inches(49)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_scribe_from_bottom_end(self):
        """Test scribing from the BOTTOM end of a timber."""
        # Create timber_a pointing up
        timber_a = timber_from_directions(
            length=inches(96),  # 8 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, inches(12)),  # Bottom at z=12"
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_a"
        )
        # timber_a's BOTTOM end is at (0, 0, 12"), centerline runs along z-axis
        # timber_a's TOP end is at (0, 0, 108")
        
        # Create timber_b horizontal with FRONT face (pointing up) intersecting timber_a's centerline
        timber_b = timber_from_directions(
            length=inches(48),  # 4 feet
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(0, 0, 0),  # FRONT face at z=3"
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="timber_b"
        )
        # timber_b's FRONT face is at z = 0" + 3" = 3" (normal pointing in +z direction, upward)
        
        # Scribe from timber_a's BOTTOM end to timber_b's FRONT face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.FRONT,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.BOTTOM
        )
        
        # Expected calculation (true geometric intersection):
        # - timber_a's centerline: P = (0, 0, 12") + t*(0, 0, 1) [measuring from BOTTOM, going up]
        # - timber_b's FRONT face plane: normal = (0, 0, 1), plane at z = 3"
        # - Intersection: 1 * (z - 3") = 0 => z = 3"
        # - From line: 12" + t = 3" => t = -9"
        # - Negative means going backward from the BOTTOM end (below the timber)
        expected_distance = inches(-9)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_scribe_to_end_face_top(self):
        """Test scribing to an upward-pointing face."""
        # Create timber_a vertical
        timber_a = timber_from_directions(
            length=inches(48),  # 4 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_a"
        )
        # timber_a's TOP end is at (0, 0, 48"), centerline runs along z-axis
        
        # Create timber_b horizontal with its FRONT face (pointing up) intersecting timber_a's centerline
        timber_b = timber_from_directions(
            length=inches(60),  # 5 feet
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(inches(-10), 0, inches(27)),  # FRONT face at z=27"+3"=30"
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="timber_b"
        )
        # timber_b's FRONT face is at z = 27" + 3" = 30" (normal pointing in +z direction, upward)
        
        # Scribe from timber_a's TOP end to timber_b's FRONT face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.FRONT,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.TOP
        )
        
        # Expected calculation (true geometric intersection):
        # - timber_a's centerline: P = (0, 0, 48") + t*(0, 0, -1) [measuring from TOP, going down]
        # - timber_b's FRONT face plane: normal = (0, 0, 1), plane at z = 30"
        # - Intersection: 1 * (z - 30") = 0 => z = 30"
        # - From line: 48" - t = 30" => t = 18"
        # - Positive means going into the timber from the TOP end
        expected_distance = inches(18)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_scribe_to_long_face(self):
        """Test scribing to a long face (FRONT/BACK/LEFT/RIGHT)."""
        # Create timber_a horizontal
        timber_a = timber_from_directions(
            length=inches(36),  # 3 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="timber_a"
        )
        # timber_a's TOP end is at x=36"
        
        # Create timber_b vertical
        timber_b = timber_from_directions(
            length=inches(96),  # 8 feet
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(inches(50), 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_b"
        )
        # timber_b's LEFT face is at x = 50" - 3" = 47"
        # timber_b's LEFT face center (mid-length) is at (47", 0, 48")
        
        # Scribe from timber_a's TOP end to timber_b's LEFT face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.LEFT,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.TOP
        )
        
        # Expected calculation:
        # - timber_a's TOP end position: (36", 0, 0)
        # - timber_b's LEFT face center: (47", 0, 48")
        # - Vector from timber_a TOP to timber_b LEFT face: (11", 0, 48")
        # - timber_a's into_timber_direction from TOP = -length_direction = (-1, 0, 0)
        # - Signed distance = (11", 0, 48") · (-1, 0, 0) = -11"
        # Negative means moving in opposite direction along timber_a
        expected_distance = inches(-11)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_with_rational_arithmetic(self):
        """Test that the function works correctly with exact Rational arithmetic."""
        # Create timber_a vertical with Rational dimensions
        timber_a = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(2), Rational(2)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_a"
        )
        # timber_a's TOP end is at (0, 0, 10), centerline runs along z-axis
        
        # Create timber_b horizontal with its BACK face (pointing down) intersecting timber_a's centerline
        timber_b = timber_from_directions(
            length=Rational(20),
            size=create_v2(Rational(3), Rational(3)),
            bottom_position=create_v3(Rational(-5), 0, Rational(7) + Rational(3)/2),  # BACK face at z=7
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="timber_b"
        )
        # timber_b's BACK face is at z = 7 + 3/2 - 3/2 = 7 (normal pointing in -z direction, downward)
        
        # Scribe from timber_a's TOP end to timber_b's BACK face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.BACK,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.TOP
        )
        
        # Expected calculation (true geometric intersection):
        # - timber_a's centerline: P = (0, 0, 10) + t*(0, 0, -1) [measuring from TOP, going down]
        # - timber_b's BACK face plane: normal = (0, 0, -1), plane at z = 7
        # - Intersection: -1 * (z - 7) = 0 => z = 7
        # - From line: 10 - t = 7 => t = 3
        # - Positive means going into the timber from the TOP end
        expected_distance = Rational(3)
        assert distance == expected_distance, \
            f"Expected exact rational {expected_distance}, got {distance}"
    
    def test_positive_distance_into_timber(self):
        """Test a case where the intersection is in the positive direction (into the timber)."""
        # Create timber_a pointing east
        timber_a = timber_from_directions(
            length=inches(48),  # 4 feet
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # Pointing east
            width_direction=create_v3(0, 1, 0),
            name="timber_a"
        )
        # timber_a's TOP end is at (48", 0, 0), centerline runs along x-axis
        
        # Create timber_b vertical with LEFT face that intersects at x=36" (before timber_a's TOP end)
        timber_b = timber_from_directions(
            length=inches(60),  # 5 feet
            size=create_v2(inches(6), inches(6)),
            bottom_position=create_v3(inches(36), 0, 0),  # LEFT face at x=36"-3"=33"
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_b"
        )
        # timber_b's LEFT face is at x = 36" - 3" = 33" (normal pointing in -x direction)
        
        # Scribe from timber_a's TOP end to timber_b's LEFT face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.LEFT,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.TOP
        )
        
        # Expected calculation (true geometric intersection):
        # - timber_a's centerline: P = (48", 0, 0) + t*(-1, 0, 0) [measuring from TOP, going backward]
        # - timber_b's LEFT face plane: normal = (-1, 0, 0), plane at x = 33"
        # - Intersection: -1 * (x - 33") = 0 => x = 33"
        # - From line: 48" - t = 33" => t = 15"
        # - Positive means going into the timber from the TOP end (backward toward BOTTOM)
        expected_distance = inches(15)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"
    
    def test_different_timber_sizes(self):
        """Test scribing between timbers of different cross-sectional sizes."""
        # Create small timber_a
        timber_a = timber_from_directions(
            length=inches(24),  # 2 feet
            size=create_v2(inches(2), inches(4)),  # 2x4
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_a"
        )
        # timber_a's TOP end is at z=24"
        
        # Create larger timber_b
        timber_b = timber_from_directions(
            length=inches(48),  # 4 feet
            size=create_v2(inches(8), inches(8)),  # 8x8
            bottom_position=create_v3(0, 0, inches(36)),  # Start at z=36"
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="timber_b"
        )
        # timber_b's BOTTOM face (end face) is at z=36"
        # timber_b's BOTTOM face center: (0, 0, 36")
        
        # Scribe from timber_a's TOP end to timber_b's BOTTOM face
        distance = scribe_face_plane_onto_centerline(
            face=TimberFace.BOTTOM,
            face_timber=timber_b,
            to_timber=timber_a,
            to_timber_end=TimberReferenceEnd.TOP
        )
        
        # Expected calculation (true geometric intersection):
        # - timber_a's centerline: P = (0, 0, 24") + t*(0, 0, -1) [measuring from TOP, going down]
        # - timber_b's BOTTOM face plane: normal = (0, 0, -1), plane at z = 36"
        # - Intersection: -1 * (z - 36") = 0 => z = 36"
        # - From line: 24" - t = 36" => t = -12", but due to the direction alignment calculation:
        # - numerator = (0,0,-1) · ((0,0,36") - (0,0,24")) = -12"
        # - denominator = (0,0,-1) · (0,0,-1) = 1
        # - t = -12" / 1 = -12"
        # - signed_distance = -12" * ((0,0,1) · (0,0,-1)) = -12" * (-1) = 12"
        # - Positive means the plane is farther along (above the TOP end)
        expected_distance = inches(12)
        assert distance == expected_distance, \
            f"Expected distance {expected_distance}, got {distance}"


class TestFindProjectedIntersectionOnCenterlines:
    """Tests for find_projected_intersection_on_centerlines function."""
    
    def test_orthogonal_timbers_t_joint(self):
        """Test with orthogonal timbers forming a T-joint."""
        # Vertical timber (receiving)
        timber_vertical = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Pointing up
            width_direction=create_v3(1, 0, 0),
            name="vertical"
        )
        
        # Horizontal timber intersecting at middle of vertical
        timber_horizontal = timber_from_directions(
            length=inches(24),
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, inches(12), inches(18)),  # 18" up on vertical
            length_direction=create_v3(0, -1, 0),  # Pointing toward vertical
            width_direction=create_v3(1, 0, 0),
            name="horizontal"
        )
        
        # Find closest points
        distA, distB = find_projected_intersection_on_centerlines(
            timber_vertical, timber_horizontal,
            TimberReferenceEnd.BOTTOM, TimberReferenceEnd.BOTTOM
        )
        
        # Vertical timber: closest point should be at 18" from bottom
        assert distA == inches(18)
        # Horizontal timber: closest point should be at 12" from its bottom (where it intersects)
        assert distB == inches(12)
    
    def test_parallel_timbers(self):
        """Test with parallel timbers - should return zero distances."""
        # Two parallel timbers
        timberA = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberA"
        )
        
        timberB = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, inches(6), 0),  # 6" away parallel
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name="timberB"
        )
        
        distA, distB = find_projected_intersection_on_centerlines(
            timberA, timberB,
            TimberReferenceEnd.BOTTOM, TimberReferenceEnd.BOTTOM
        )
        
        # For parallel lines, should return 0 (starting points)
        assert distA == Rational(0)
        assert distB == Rational(0)
    
    def test_with_different_reference_ends(self):
        """Test measuring from different reference ends (TOP vs BOTTOM)."""
        # Vertical timber
        timber_vertical = timber_from_directions(
            length=inches(36),
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="vertical"
        )
        
        # Horizontal timber at middle
        timber_horizontal = timber_from_directions(
            length=inches(24),
            size=create_v2(inches(4), inches(4)),
            bottom_position=create_v3(0, inches(12), inches(18)),
            length_direction=create_v3(0, -1, 0),
            width_direction=create_v3(1, 0, 0),
            name="horizontal"
        )
        
        # Measure from TOP of vertical timber
        distA, distB = find_projected_intersection_on_centerlines(
            timber_vertical, timber_horizontal,
            TimberReferenceEnd.TOP, TimberReferenceEnd.BOTTOM
        )
        
        # From TOP of vertical (36" high), intersection at 18" from bottom = 18" from top down
        assert distA == inches(-18)  # Negative because going down from top
        assert distB == inches(12)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
