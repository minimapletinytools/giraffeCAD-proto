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
    measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber
)
from code_goes_here.timber import timber_from_directions, TimberReferenceEnd, TimberFace, TimberReferenceLongFace
from code_goes_here.moothymoth import create_v3, create_v2, inches
from code_goes_here.meowmeowcsg import Union, Prism, HalfPlane

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


class TestChopLapOnTimberEnd:
    """Tests for chop_lap_on_timber_end function."""
    
    def test_lap_on_right_face_geometry(self):
        """
        Test lap joint cut on RIGHT face of a timber.
        
        Creates a 4"x6" timber that is 4 ft long.
        Lap length is 1ft, shoulder 6" from end, lap face is RIGHT.
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
        lap_depth = inches(2)  # 2" depth (half of 4" width for half-lap)
        lap_face = TimberFace.RIGHT  # Cut on RIGHT face
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
        
        # Verify the CSG is a Union
        assert isinstance(lap_csg, Union), "Lap CSG should be a Union"
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
        
        # Test point 1: 6" down from timber end (at shoulder), on the lap face
        # RIGHT face is at x=+2", this point should be IN the CSG (material removed)
        point1 = create_v3(inches(2), 0, expected_shoulder_z)
        assert lap_csg.contains_point(point1), \
            "Point at shoulder on RIGHT face should be in the removed region"
        
        # Test point 2: From point1, move 2" left (to x=0), should be ON BOUNDARY
        point2 = create_v3(0, 0, expected_shoulder_z)
        assert lap_csg.contains_point(point2), \
            "Point at boundary (x=0) at shoulder should be on boundary (contained)"
        
        # Test point 3: From point2, go 3" down from shoulder (to z=39")
        # This is BELOW the prism start (shoulder at 42"), so should NOT be in CSG
        point3 = create_v3(0, 0, expected_shoulder_z - inches(3))
        assert not lap_csg.contains_point(point3), \
            "Point 3\" below shoulder (outside lap region) should NOT be in the removed region"


class TestMeasureDistanceFromFaceOnTimberWrtOpposingFaceOnAnotherTimber:
    """Tests for measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber function."""
    
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
        
        distance = measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberReferenceLongFace.BACK,
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
        
        distance = measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberReferenceLongFace.BACK,
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
        
        distance = measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberReferenceLongFace.RIGHT,
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
            measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
                reference_timber=top_timber,
                reference_face=TimberReferenceLongFace.BACK,
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
        
        distance = measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
            reference_timber=top_timber,
            reference_face=TimberReferenceLongFace.BACK,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
