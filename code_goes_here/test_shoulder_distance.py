"""
Unit tests for _calculate_distance_from_timber_end_to_shoulder_plane function.

Tests various timber orientations and joint configurations to ensure
the shoulder distance calculation is correct for all cases.
"""

import pytest
from sympy import Float
from giraffe import (
    _calculate_distance_from_timber_end_to_shoulder_plane,
    create_timber, 
    create_vector3d,
    create_vector2d,
    TimberReferenceEnd
)
from code_goes_here.moothymoth import inches


class TestShoulderDistanceCalculation:
    """Test shoulder distance calculation for different timber orientations."""
    
    def setup_method(self):
        """Set up common test data."""
        # Standard 4x4 inch timber dimensions (in meters)
        self.timber_size = create_vector2d(inches(4), inches(4))  # 0.1016m x 0.1016m
        self.expected_half_dimension = inches(2)  # 0.0508m
        
    def test_vertical_tenon_into_horizontal_mortise_x_direction(self):
        """Test vertical timber with tenon into horizontal timber (X-aligned)."""
        # Vertical timber (going up in Z)
        vertical_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 0, 1),  # Up in Z
            width_direction=create_vector3d(0, 1, 0)  # Face forward in Y
        )
        
        # Horizontal timber (going in X direction)
        horizontal_timber = create_timber(
            bottom_position=create_vector3d(-0.5, 0, 0),
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(1, 0, 0),  # East in X
            width_direction=create_vector3d(0, 0, 1)  # Face up in Z
        )
        
        # Test bottom tenon (vertical timber bottom end)
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            vertical_timber, horizontal_timber, TimberReferenceEnd.BOTTOM
        )
        
        print(f"Vertical->Horizontal (X): {distance} (expected: {self.expected_half_dimension})")
        assert abs(distance - self.expected_half_dimension) < 1e-6, \
            f"Expected {self.expected_half_dimension}, got {distance}"
    
    def test_vertical_tenon_into_horizontal_mortise_y_direction(self):
        """Test vertical timber with tenon into horizontal timber (Y-aligned)."""
        # Vertical timber (going up in Z)
        vertical_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 0, 1),  # Up in Z
            width_direction=create_vector3d(0, 1, 0)  # Face forward in Y
        )
        
        # Horizontal timber (going in Y direction)
        horizontal_timber = create_timber(
            bottom_position=create_vector3d(0, -0.5, 0),
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 1, 0),  # North in Y
            width_direction=create_vector3d(1, 0, 0)  # Face right in X
        )
        
        # Test bottom tenon (vertical timber bottom end)
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            vertical_timber, horizontal_timber, TimberReferenceEnd.BOTTOM
        )
        
        print(f"Vertical->Horizontal (Y): {distance} (expected: {self.expected_half_dimension})")
        assert abs(distance - self.expected_half_dimension) < 1e-6, \
            f"Expected {self.expected_half_dimension}, got {distance}"
    
    def test_horizontal_tenon_into_vertical_mortise_x_direction(self):
        """Test horizontal timber (X-aligned) with tenon into vertical timber - MISALIGNED case."""
        # Horizontal timber (going in X direction) - this is actually misaligned because
        # the TOP end is far from the vertical timber centerline
        horizontal_timber = create_timber(
            bottom_position=create_vector3d(-0.5, 0, 0),  # Same Y and Z as vertical
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(1, 0, 0),  # East in X
            width_direction=create_vector3d(0, 0, 1)  # Face up in Z
        )
        
        # Vertical timber (going up in Z)
        vertical_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 0, 1),  # Up in Z
            width_direction=create_vector3d(0, 1, 0)  # Face forward in Y
        )
        
        # Test right tenon (horizontal timber right end at [0.5, 0, 0])
        # Distance from [0.5, 0, 0] to vertical timber face should be 0.5 + face_offset
        expected_distance = 0.5 + inches(2)  # 0.5 + 0.0508
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            horizontal_timber, vertical_timber, TimberReferenceEnd.TOP
        )
        
        print(f"Horizontal(X)->Vertical: {distance} (expected: {expected_distance})")
        assert abs(distance - expected_distance) < 1e-6, \
            f"Expected {expected_distance}, got {distance}"
    
    def test_horizontal_tenon_into_vertical_mortise_y_direction(self):
        """Test horizontal timber (Y-aligned) with tenon into vertical timber - MISALIGNED case."""
        # Horizontal timber (going in Y direction) - this is actually misaligned
        horizontal_timber = create_timber(
            bottom_position=create_vector3d(0, -0.5, 0),  # Same X and Z as vertical
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 1, 0),  # North in Y
            width_direction=create_vector3d(0, 0, 1)  # Face up in Z
        )
        
        # Vertical timber (going up in Z)
        vertical_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 0, 1),  # Up in Z
            width_direction=create_vector3d(0, 1, 0)  # Face forward in Y
        )
        
        # Test top tenon (horizontal timber top end at [0, 0.5, 0])
        # Distance should be 0.5 + face_offset
        expected_distance = 0.5 + inches(2)  # 0.5508
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            horizontal_timber, vertical_timber, TimberReferenceEnd.TOP
        )
        
        print(f"Horizontal(Y)->Vertical: {distance} (expected: {expected_distance})")
        assert abs(distance - expected_distance) < 1e-6, \
            f"Expected {expected_distance}, got {distance}"
    
    def test_perpendicular_horizontal_timbers_x_into_y(self):
        """Test horizontal timber (X-aligned) with tenon into horizontal timber (Y-aligned) - ALIGNED case."""
        # First timber going in X direction - positioned to be ALIGNED with Y timber
        timber_x = create_timber(
            bottom_position=create_vector3d(-0.5, 0, 0),  # Same Y and Z as timber_y
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(1, 0, 0),  # East in X
            width_direction=create_vector3d(0, 0, 1)  # Face up in Z
        )
        
        # Second timber going in Y direction
        timber_y = create_timber(
            bottom_position=create_vector3d(0, -0.5, 0),  # Same X and Z as timber_x
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 1, 0),  # North in Y
            width_direction=create_vector3d(0, 0, 1)  # Face up in Z
        )
        
        # Test tenon from X timber TOP end [0.5, 0, 0] into Y timber
        # Distance should be 0.5 + face_offset = 0.5508
        expected_distance = 0.5 + inches(2)
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            timber_x, timber_y, TimberReferenceEnd.TOP
        )
        
        print(f"Horizontal(X)->Horizontal(Y): {distance} (expected: {expected_distance})")
        assert abs(distance - expected_distance) < 1e-6, \
            f"Expected {expected_distance}, got {distance}"
    
    def test_perpendicular_horizontal_timbers_y_into_x(self):
        """Test horizontal timber (Y-aligned) with tenon into horizontal timber (X-aligned) - ALIGNED case."""
        # First timber going in Y direction - positioned to be ALIGNED with X timber
        timber_y = create_timber(
            bottom_position=create_vector3d(0, -0.5, 0),  # Same X and Z as timber_x
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(0, 1, 0),  # North in Y
            width_direction=create_vector3d(0, 0, 1)  # Face up in Z
        )
        
        # Second timber going in X direction
        timber_x = create_timber(
            bottom_position=create_vector3d(-0.5, 0, 0),  # Same Y and Z as timber_y
            length=1.0,
            size=self.timber_size,
            length_direction=create_vector3d(1, 0, 0),  # East in X
            width_direction=create_vector3d(0, 0, 1)  # Face up in Z
        )
        
        # Test tenon from Y timber TOP end [0, 0.5, 0] into X timber
        # This is a bit different - Y timber TOP end is [0, 0.5, 0], 
        # X timber centerline is at y=0, so distance to intersection is 0.5
        # But X timber's RIGHT face (receiving mortise) is at x=0.0508
        # Since Y timber centerline passes through x=0, the calculation is different
        expected_distance = 0.5 - inches(2)  # 0.4492
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            timber_y, timber_x, TimberReferenceEnd.TOP
        )
        
        print(f"Horizontal(Y)->Horizontal(X): {distance} (expected: {expected_distance})")
        assert abs(distance - expected_distance) < 1e-6, \
            f"Expected {expected_distance}, got {distance}"
    
    def test_different_timber_sizes(self):
        """Test with different timber sizes to ensure calculation scales correctly."""
        # Larger timber (6x6 inches)
        large_size = create_vector2d(inches(6), inches(6))
        expected_large_half = inches(3)
        
        # Smaller timber (2x4 inches) 
        small_size = create_vector2d(inches(2), inches(4))
        expected_small_half_width = inches(1)  # Half of 2 inches
        
        # Large timber (tenon)
        large_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=large_size,
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(0, 1, 0)
        )
        
        # Small timber (mortise) - positioned to intersect large timber's front face
        small_timber = create_timber(
            bottom_position=create_vector3d(-0.5, 0, 0),
            length=1.0,
            size=small_size,
            length_direction=create_vector3d(1, 0, 0),
            width_direction=create_vector3d(0, 0, 1)
        )
        
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            large_timber, small_timber, TimberReferenceEnd.BOTTOM
        )
        
        print(f"Large->Small timber: {distance} (expected: {expected_small_half_width})")
        # Should be half the width of the mortise timber (small timber width)
        assert abs(distance - expected_small_half_width) < 1e-6, \
            f"Expected {expected_small_half_width}, got {distance}"
    
    def test_misaligned_timbers_example2_geometry(self):
        """Test misaligned timbers like in supersimple_example2 where centerlines don't intersect."""
        # Recreate the exact geometry from supersimple_example2
        post_size = create_vector2d(inches(4), inches(4))
        
        # Vertical timber at origin
        vertical_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=post_size,
            length_direction=create_vector3d(0, 0, 1),  # Up in Z
            width_direction=create_vector3d(1, 0, 0)     # Face east
        )
        
        # Horizontal timber positioned to intersect vertical at mid-height
        # BUT with centerline offset (not aligned with vertical centerline)
        horizontal_timber = create_timber(
            bottom_position=create_vector3d(0, -0.5, 0.5),  # Offset position!
            length=1.0,
            size=post_size,
            length_direction=create_vector3d(0, 1, 0),   # North in Y
            width_direction=create_vector3d(0, 0, 1)      # Face up
        )
        
        # Test horizontal timber tenon into vertical timber mortise
        # The horizontal timber's BOTTOM end (at y=-0.5) has a tenon
        # that goes into the vertical timber's FORWARD face
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            horizontal_timber, vertical_timber, TimberReferenceEnd.BOTTOM
        )
        
        # The shoulder plane should be at the FORWARD face of the vertical timber
        # Distance from horizontal timber bottom end to vertical timber forward face
        
        # Expected calculation:
        # - Horizontal timber bottom end is at (0, -0.5, 0.5)
        # - Vertical timber forward face is at y = +0.0508 (half timber width from centerline)
        # - Distance along horizontal timber centerline = 0.5 + 0.0508 = 0.5508
        expected_distance = 0.5 + inches(2)  # 0.5 + 0.0508 = 0.5508
        
        print(f"Misaligned timbers (Example2): {distance} (expected: {expected_distance})")
        
        # This test should FAIL with the current face_offset approach
        # but PASS with the correct projection-based calculation
        assert abs(distance - expected_distance) < 1e-6, \
            f"Expected {expected_distance}, got {distance}"
    
    def test_supersimple_example5_geometry(self):
        """Test the exact geometry from supersimple_example5."""
        # Recreate the exact geometry from supersimple_example5
        post_size = create_vector2d(inches(4), inches(4))
        
        # Vertical timber
        vertical_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=0.9,
            size=post_size,
            length_direction=create_vector3d(0, 0, 1),
            width_direction=create_vector3d(0, 1, 0)
        )
        
        # Bottom horizontal timber
        bottom_timber = create_timber(
            bottom_position=create_vector3d(-0.5, 0, 0),
            length=1.0,
            size=post_size,
            length_direction=create_vector3d(1, 0, 0),
            width_direction=create_vector3d(0, 0, 1)
        )
        
        # Top horizontal timber  
        top_timber = create_timber(
            bottom_position=create_vector3d(-0.5, 0, 0.9),
            length=1.0,
            size=post_size,
            length_direction=create_vector3d(1, 0, 0),
            width_direction=create_vector3d(0, 0, 1)
        )
        
        # Test bottom joint (vertical into bottom horizontal)
        bottom_distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            vertical_timber, bottom_timber, TimberReferenceEnd.BOTTOM
        )
        
        # Test top joint (vertical into top horizontal)
        top_distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            vertical_timber, top_timber, TimberReferenceEnd.TOP
        )
        
        expected = inches(2)  # Half of 4 inch timber
        
        print(f"Example5 bottom joint: {bottom_distance} (expected: {expected})")
        print(f"Example5 top joint: {top_distance} (expected: {expected})")
        
        assert abs(bottom_distance - expected) < 1e-6, \
            f"Bottom joint: Expected {expected}, got {bottom_distance}"
        assert abs(top_distance - expected) < 1e-6, \
            f"Top joint: Expected {expected}, got {top_distance}"
    
    def test_truly_aligned_timbers(self):
        """Test truly aligned timbers where tenon end coincides with projected point."""
        post_size = create_vector2d(inches(4), inches(4))
        
        # Vertical timber at origin
        vertical_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=post_size,
            length_direction=create_vector3d(0, 0, 1),  # Up in Z
            width_direction=create_vector3d(0, 1, 0)     # Face forward in Y
        )
        
        # Horizontal timber positioned so its LEFT end is exactly at the vertical timber
        # This matches the supersimple_example5 pattern
        horizontal_timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0.5),  # LEFT end at vertical timber
            length=1.0,
            size=post_size,
            length_direction=create_vector3d(1, 0, 0),   # East in X
            width_direction=create_vector3d(0, 0, 1)      # Face up in Z
        )
        
        # Test BOTTOM tenon (horizontal timber left end coincides with vertical timber)
        distance = _calculate_distance_from_timber_end_to_shoulder_plane(
            horizontal_timber, vertical_timber, TimberReferenceEnd.BOTTOM
        )
        
        expected = inches(2)  # Just the face offset
        
        print(f"Truly aligned timbers: {distance} (expected: {expected})")
        assert abs(distance - expected) < 1e-6, \
            f"Expected {expected}, got {distance}"


if __name__ == "__main__":
    # Run the tests directly for debugging
    test_instance = TestShoulderDistanceCalculation()
    test_instance.setup_method()
    
    print("Running shoulder distance calculation tests...\n")
    
    try:
        test_instance.test_vertical_tenon_into_horizontal_mortise_x_direction()
        print("✓ Vertical->Horizontal(X) passed\n")
    except AssertionError as e:
        print(f"✗ Vertical->Horizontal(X) failed: {e}\n")
    
    try:
        test_instance.test_vertical_tenon_into_horizontal_mortise_y_direction()
        print("✓ Vertical->Horizontal(Y) passed\n")
    except AssertionError as e:
        print(f"✗ Vertical->Horizontal(Y) failed: {e}\n")
    
    try:
        test_instance.test_horizontal_tenon_into_vertical_mortise_x_direction()
        print("✓ Horizontal(X)->Vertical passed\n")
    except AssertionError as e:
        print(f"✗ Horizontal(X)->Vertical failed: {e}\n")
    
    try:
        test_instance.test_horizontal_tenon_into_vertical_mortise_y_direction()
        print("✓ Horizontal(Y)->Vertical passed\n")
    except AssertionError as e:
        print(f"✗ Horizontal(Y)->Vertical failed: {e}\n")
    
    try:
        test_instance.test_perpendicular_horizontal_timbers_x_into_y()
        print("✓ Horizontal(X)->Horizontal(Y) passed\n")
    except AssertionError as e:
        print(f"✗ Horizontal(X)->Horizontal(Y) failed: {e}\n")
    
    try:
        test_instance.test_perpendicular_horizontal_timbers_y_into_x()
        print("✓ Horizontal(Y)->Horizontal(X) passed\n")
    except AssertionError as e:
        print(f"✗ Horizontal(Y)->Horizontal(X) failed: {e}\n")
    
    try:
        test_instance.test_different_timber_sizes()
        print("✓ Different timber sizes passed\n")
    except AssertionError as e:
        print(f"✗ Different timber sizes failed: {e}\n")
    
    try:
        test_instance.test_misaligned_timbers_example2_geometry()
        print("✓ Misaligned timbers (Example2) passed\n")
    except AssertionError as e:
        print(f"✗ Misaligned timbers (Example2) failed: {e}\n")
    
    try:
        test_instance.test_supersimple_example5_geometry()
        print("✓ SuperSimple Example5 geometry passed\n")
    except AssertionError as e:
        print(f"✗ SuperSimple Example5 geometry failed: {e}\n")
    
    try:
        test_instance.test_truly_aligned_timbers()
        print("✓ Truly aligned timbers passed\n")
    except AssertionError as e:
        print(f"✗ Truly aligned timbers failed: {e}\n")
    
    print("Test run complete!")
