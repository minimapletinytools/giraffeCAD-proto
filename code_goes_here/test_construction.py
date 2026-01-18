"""
Tests for GiraffeCAD timber framing system
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs, Float, Rational
from code_goes_here.moothymoth import Orientation
from code_goes_here.footprint import Footprint
from giraffe import *
from .helperonis import (
    create_standard_vertical_timber,
    create_standard_horizontal_timber,
    assert_vectors_perpendicular
)
from code_goes_here.moothymoth import inches, feet

# ============================================================================
# Tests for construction.py - Timber Creation and Manipulation
# ============================================================================

class TestTimberCreation:
    """Test timber creation functions."""
    
    def test_create_timber(self):
        """Test basic create_timber function."""
        position = create_v3(Rational(1), Rational(1), Rational(0))
        size = create_v2(Rational("0.2"), Rational("0.3"))
        length_dir = create_v3(Rational(0), Rational(0), Rational(1))
        width_dir = create_v3(Rational(1), Rational(0), Rational(0))
        
        timber = create_timber(position, Rational("2.5"), size, length_dir, width_dir)
        
        assert timber.length == Rational("2.5")
        assert timber.bottom_position[0] == Rational(1)
        assert timber.bottom_position[1] == Rational(1)
        assert timber.bottom_position[2] == Rational(0)
    
    def test_create_axis_aligned_timber(self):
        """Test axis-aligned timber creation with explicit width_direction."""
        position = create_v3(0, 0, 0)  # Use exact integers
        size = create_v2(Rational(1, 10), Rational(1, 10))  # 0.1 as exact rational
        
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
        position = create_v3(0, 0, 0)
        size = create_v2(Rational(1, 10), Rational(1, 10))
        
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
            TimberFace.FRONT  # Length in +Y
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
        position = create_v3(0, 0, 0)
        size = create_v2(Rational(1, 10), Rational(1, 10))
        
        # Even with length in +X, we can explicitly set width to +Y
        timber = create_axis_aligned_timber(
            position, 3, size,
            TimberFace.RIGHT,    # Length in +X
            TimberFace.FRONT   # Explicit width in +Y (not the default +Z)
        )
        
        assert timber.length_direction[0] == 1  # Length in +X
        assert timber.width_direction[1] == 1    # Width in +Y (explicit)
    
    def test_create_vertical_timber_on_footprint_corner(self):
        """Test vertical timber creation on footprint corner with INSIDE, OUTSIDE, and CENTER."""
        # Create a square footprint with exact integer corners
        corners = [
            create_v2(0, 0),  # Corner 0: Bottom-left
            create_v2(3, 0),  # Corner 1: Bottom-right  
            create_v2(3, 4),  # Corner 2: Top-right
            create_v2(0, 4)   # Corner 3: Top-left
        ]
        footprint = Footprint(corners)
        
        # Post size: 9cm x 9cm (exact rational)
        size = create_v2(Rational(9, 100), Rational(9, 100))
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
            create_v2(0, 0),  # Corner 0: Bottom-left
            create_v2(4, 0),  # Corner 1: Bottom-right
            create_v2(4, 3),  # Corner 2: Top-right
            create_v2(0, 3)   # Corner 3: Top-left
        ]
        footprint = Footprint(corners)
        
        # Post size: 10cm x 10cm (exact rational)
        size = create_v2(Rational(1, 10), Rational(1, 10))
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
            create_v2(Rational(0), Rational(0)),
            create_v2(Rational(3), Rational(0)),
            create_v2(Rational(3), Rational(4)),
            create_v2(Rational(0), Rational(4))
        ]
        footprint = Footprint(corners)
        
        # Default size for test
        size = create_v2(Rational(3, 10), Rational(3, 10))
        
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
            create_v2(0, 0),  # Bottom-left
            create_v2(2, 0),  # Bottom-right
            create_v2(2, 2),  # Top-right
            create_v2(0, 2)   # Top-left
        ]
        footprint = Footprint(corners)
        
        # Define timber size: width (vertical) x height (perpendicular to boundary)
        # For a horizontal timber: size[0] = width (vertical), size[1] = height (horizontal perpendicular)
        timber_width = Rational(3, 10)   # Vertical dimension (face direction = up)
        timber_height = Rational(2, 10)  # Perpendicular to boundary in XY plane
        size = create_v2(timber_width, timber_height)
        
        # Test bottom boundary side (from corner 0 to corner 1)
        # This side has inward normal pointing up: (0, 1, 0)
        
        # Test INSIDE positioning
        timber_inside = create_horizontal_timber_on_footprint(
            footprint, 0, FootprintLocation.INSIDE, size, length=Rational(2)
        )
        # Timber should extend inward (in +Y direction)
        # Bottom position Y should be half timber height (perpendicular dimension) inside the footprint
        assert timber_inside.bottom_position[1] == timber_height / Rational(2)
        assert timber_inside.bottom_position[0] == 0  # X unchanged
        assert timber_inside.bottom_position[2] == 0  # Z at ground
        
        # Test OUTSIDE positioning
        timber_outside = create_horizontal_timber_on_footprint(
            footprint, 0, FootprintLocation.OUTSIDE, size, length=Rational(2)
        )
        # Timber should extend outward (in -Y direction)
        # Bottom position Y should be half timber height (perpendicular dimension) outside the footprint
        # Note: get_inward_normal returns floats, so the result is Float
        assert timber_outside.bottom_position[1] == -timber_height / Rational(2)
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
        assert timber_inside_right.bottom_position[0] == Rational(2) - timber_height / Rational(2)
        assert timber_inside_right.bottom_position[1] == Rational(0)  # Y unchanged
        
        timber_outside_right = create_horizontal_timber_on_footprint(
            footprint, 1, FootprintLocation.OUTSIDE, size, length=Rational(2)
        )
        # Timber should extend outward (in +X direction)
        # Use timber_height (size[1]) as it's the dimension perpendicular to boundary
        assert timber_outside_right.bottom_position[0] == Rational(2) + timber_height / Rational(2)
        assert timber_outside_right.bottom_position[1] == Rational(0)  # Y unchanged
        
        timber_center_right = create_horizontal_timber_on_footprint(
            footprint, 1, FootprintLocation.CENTER, size, length=Rational(2)
        )
        # Centerline should be on the boundary side
        assert timber_center_right.bottom_position[0] == Rational(2)  # X on boundary
        assert timber_center_right.bottom_position[1] == Rational(0)  # Y unchanged
    
    def test_stretch_timber(self):
        """Test timber extension creation with correct length calculation."""
        # Create a vertical timber from Z=0 to Z=10
        original_timber = create_standard_vertical_timber(height=10, size=(0.2, 0.2), position=(0, 0, 0))
        
        # Extend from top with 2 units of overlap and 5 units of extension
        # overlap_length = 2.0 (overlaps with last 2 units of original timber)
        # extend_length = 5.0 (extends 5 units beyond the end)
        extended = stretch_timber(
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
        
        front = TimberFace.FRONT.get_direction()
        assert forward[1] == Rational(1)
        
        back = TimberFace.BACK.get_direction()
        assert back[1] == -Rational(1)



class TestJoinTimbers:
    """Test timber joining functions."""
    
    def test_join_timbers_basic(self):
        """Test basic timber joining."""
        timber1 = create_standard_vertical_timber(height=3, size=(0.2, 0.2), position=(0, 0, 0))
        timber2 = create_standard_vertical_timber(height=2, size=(0.2, 0.2), position=(2, 0, 0))
        
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
        assert_vectors_perpendicular(length_dir, width_dir)
        
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
        timber1 = create_standard_vertical_timber(height=3, size=(0.2, 0.2), position=(0, 0, 0))
        timber2 = create_standard_vertical_timber(height=3, size=(0.2, 0.2), position=(2, 0, 0))
        
        # Create a horizontal beam connecting them, specifying "face up" (0,0,1)
        # The joining direction is horizontal [1,0,0], so [0,0,1] is NOT perpendicular
        # The function should automatically project it onto the perpendicular plane
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational("1.5"),  # Midpoint of timber1
            stickout=Stickout(Rational("0.1"), Rational("0.1")),  # Symmetric stickout
            location_on_timber2=Rational("1.5"),   # Same height on timber2
            orientation_width_vector=create_v3(0, 0, 1)  # "Face up" - not perpendicular to joining direction
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
        timber1 = create_standard_vertical_timber(height=3, size=(0.2, 0.2), position=(0, 0, 0))
        timber2 = create_standard_vertical_timber(height=3, size=(0.2, 0.2), position=(2, 1, 0))
        
        # Provide an orientation vector at an angle: [1, 1, 1]
        # This should be projected onto the plane perpendicular to the joining direction
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational("1.5"),
            stickout=Stickout(Rational(0), Rational(0)),
            location_on_timber2=Rational("1.5"),
            orientation_width_vector=create_v3(1, 1, 1)  # Angled vector
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
        timber1 = create_standard_horizontal_timber(direction='x', length=3, size=(0.2, 0.2), position=(0, 0, 0))
        timber2 = create_standard_horizontal_timber(direction='x', length=3, size=(0.2, 0.2), position=(0, 2, 0))
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
            size=create_v2(Rational("0.15"), Rational("0.15")),
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
            size=create_v2(Rational("0.15"), Rational("0.15")),
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
        timber1 = create_standard_vertical_timber(height=3, size=(0.15, 0.15), position=(0, 0, 0))
        
        # Timber2: 3D rotation not aligned with timber1's coordinate grid
        timber2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.15"), Rational("0.15")),
            bottom_position=create_v3(Rational(2), Rational(2), Rational(0)),
            length_direction=create_v3(1, 1, 1),  # 3D diagonal (will be normalized)
            width_direction=create_v3(1, -1, 0)    # Perpendicular in 3D (will be normalized)
        )
        
        # Verify they are NOT face-aligned
        assert not are_timbers_face_aligned(timber1, timber2), "Timbers should not be face-aligned"
        
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
                size=create_v2(Rational("0.15"), Rational("0.15")),
                orientation_face_on_timber1=TimberFace.TOP
            )
    
    def test_join_perpendicular_on_face_parallel_timbers_auto_size(self):
        """Test automatic size determination in join_perpendicular_on_face_parallel_timbers."""
        # Create two vertical posts with 1" x 2" cross-section
        post1 = create_standard_vertical_timber(height=3, size=(inches(1), inches(2)), position=(0, 0, 0))
        # Post2 is 5 feet away in the X direction
        post2 = create_standard_vertical_timber(height=3, size=(inches(1), inches(2)), position=(feet(5), 0, 0))
        
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
        timber1 = create_standard_vertical_timber(height=1, size=(0.1, 0.1), position=(-0.5, 0, 0))
        
        timber2 = timber_from_directions(
            length=1,  # Integer
            size=create_v2(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            bottom_position=create_v3(Rational(1, 2), 0, 0),   # Exact rationals
            length_direction=create_v3(0, 1, 0),  # Integers (horizontal north)
            width_direction=create_v3(0, 0, 1)     # Integers
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
        
        # Verify directions are orthogonal to each other
        assert_vectors_perpendicular(length_dir, width_dir)
        assert_vectors_perpendicular(length_dir, height_dir)
        assert_vectors_perpendicular(width_dir, height_dir)

    def test_create_timber_creates_orthogonal_matrix(self):
        """Test that create_timber creates valid orthogonal orientation matrices."""
        # Test with arbitrary (but orthogonal) input directions using exact inputs
        length_dir = create_v3(1, 1, 0)  # Will be normalized (integers)
        width_dir = create_v3(0, 0, 1)    # Up direction (integers)
        
        timber = create_timber(
            bottom_position=create_v3(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_v2(Rational(1, 10), Rational(1, 10)),  # Exact rationals
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
        length_dir = create_v3(2, 0, 1)         # Not orthogonal to width_dir (integers)
        width_dir = create_v3(0, 1, 2)           # Not orthogonal to length_dir (integers)
        
        timber = create_timber(
            bottom_position=create_v3(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_v2(Rational(1, 10), Rational(1, 10)),  # Exact rationals
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
        timber_size = create_v2(Rational(1, 10), Rational(1, 10))  # 10cm x 10cm
        
        base_timbers = []
        positions = [
            create_v3(-1, 0, base_z),    # Left
            create_v3(0, 0, base_z),     # Center  
            create_v3(1, 0, base_z),     # Right
            create_v3(0, -1, base_z),    # Back
            create_v3(0, 1, base_z),     # Front
        ]
        
        # Create base timbers - all horizontal and face-aligned
        for i, pos in enumerate(positions):
            timber = timber_from_directions(
                length=2,  # 2m long
                size=timber_size,
                bottom_position=pos,
                length_direction=create_v3(1, 0, 0),  # All point east
                width_direction=create_v3(0, 1, 0),    # All face north
                name=f"Base_Timber_{i}"
            )
            base_timbers.append(timber)
        
        # Create a beam at a higher level
        beam_z = Rational(3, 2)  # 1.5m height
        beam = timber_from_directions(
            length=4,  # 4m long beam
            size=create_v2(Rational(15, 100), Rational(15, 100)),  # 15cm x 15cm
            bottom_position=create_v3(-2, 0, beam_z),
            length_direction=create_v3(1, 0, 0),  # East direction
            width_direction=create_v3(0, 1, 0),    # North facing
            name="Top_Beam"
        )
        
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
                size=create_v2(Rational(8, 100), Rational(8, 100))  # 8cm x 8cm posts
                # Note: orientation_face_on_timber1 not specified - uses default projection
            )
            # Note: Cannot set name after construction since Timber is frozen
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
                size=create_v2(Rational(6, 100), Rational(6, 100)),  # 6cm x 6cm
                orientation_face_on_timber1=TimberFace.TOP
            )
            # Note: Cannot set name after construction since Timber is frozen
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



class TestHelperFunctions:
    """Test helper functions for timber operations."""
    
    def test_timber_get_closest_oriented_face_axis_aligned(self):
        """Test Timber.get_closest_oriented_face() with axis-aligned timber."""
        # Create an axis-aligned timber (standard orientation)
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),  # width=0.2, height=0.3
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Z-up (length)
            width_direction=create_v3(1, 0, 0)     # X-right (face/width)
        )
        
                # Test alignment with each cardinal direction
        # Note: CORRECTED timber coordinate system:
        # - TOP/BOTTOM faces are along length_direction (Z-axis)
        # - RIGHT/LEFT faces are along width_direction (X-axis)  
        # - FRONT/BACK faces are along height_direction (Y-axis)

        # Target pointing in +Z (length direction) should align with TOP face
        target_length_pos = create_v3(0, 0, 1)
        aligned_face = timber.get_closest_oriented_face(target_length_pos)
        assert aligned_face == TimberFace.TOP

        # Target pointing in -Z (negative length direction) should align with BOTTOM face
        target_length_neg = create_v3(0, 0, -1)
        aligned_face = timber.get_closest_oriented_face(target_length_neg)
        assert aligned_face == TimberFace.BOTTOM

        # Target pointing in +X (face direction) should align with RIGHT face
        target_face_pos = create_v3(1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_face_pos)
        assert aligned_face == TimberFace.RIGHT

        # Target pointing in -X (negative face direction) should align with LEFT face
        target_face_neg = create_v3(-1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_face_neg)
        assert aligned_face == TimberFace.LEFT

        # Target pointing in +Y (height direction) should align with FRONT face
        target_height_pos = create_v3(0, 1, 0)
        aligned_face = timber.get_closest_oriented_face(target_height_pos)
        assert aligned_face == TimberFace.FRONT

        # Target pointing in -Y (negative height direction) should align with BACK face
        target_height_neg = create_v3(0, -1, 0)
        aligned_face = timber.get_closest_oriented_face(target_height_neg)
        assert aligned_face == TimberFace.BACK
    
    def test_timber_get_closest_oriented_face_rotated(self):
        """Test Timber.get_closest_oriented_face() with rotated timber."""
        # Create a timber rotated 90 degrees around Z axis
        # length_direction stays Z-up, but width_direction becomes Y-forward
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Z-up (length)
            width_direction=create_v3(0, 1, 0)     # Y-forward (face/width)
        )
        
                # Now the timber's faces are rotated (CORRECTED):
        # TOP face points in +Z direction (length_direction)
        # BOTTOM face points in -Z direction (negative length_direction)
        # RIGHT face points in +Y direction (width_direction)
        # LEFT face points in -Y direction (negative width_direction)
        # FRONT face points in -X direction (height_direction)
        # BACK face points in +X direction (negative height_direction)

        # Target pointing in +Y direction should align with RIGHT face
        target_y_pos = create_v3(0, 1, 0)
        aligned_face = timber.get_closest_oriented_face(target_y_pos)
        assert aligned_face == TimberFace.RIGHT

        # Target pointing in -Y direction should align with LEFT face
        target_y_neg = create_v3(0, -1, 0)
        aligned_face = timber.get_closest_oriented_face(target_y_neg)
        assert aligned_face == TimberFace.LEFT

        # Target pointing in -X direction should align with FRONT face
        target_x_neg = create_v3(-1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_x_neg)
        assert aligned_face == TimberFace.FRONT

        # Target pointing in +X direction should align with BACK face
        target_x_pos = create_v3(1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_x_pos)
        assert aligned_face == TimberFace.BACK
    
    def test_timber_get_closest_oriented_face_horizontal(self):
        """Test Timber.get_closest_oriented_face() with horizontal timber."""
        # Create a horizontal timber lying along X axis
        # Note: create_standard_horizontal_timber uses width_direction=[0,1,0] by default,
        # so we need to use timber_from_directions here for width_direction=[0,0,1]
        timber = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),   # X-right (length)
            width_direction=create_v3(0, 0, 1)      # Z-up (face/width)
        )
        
        # For this horizontal timber (CORRECTED):
        # TOP face points in +X direction (length_direction)
        # BOTTOM face points in -X direction (negative length_direction)
        # RIGHT face points in +Z direction (width_direction)
        # LEFT face points in -Z direction (negative width_direction)
        # FRONT face points in -Y direction (height_direction)  
        # BACK face points in +Y direction (negative height_direction)
        
        # Target pointing in +Z should align with RIGHT face
        target_z_pos = create_v3(0, 0, 1)
        aligned_face = timber.get_closest_oriented_face(target_z_pos)
        assert aligned_face == TimberFace.RIGHT
        
        # Target pointing in -Z should align with LEFT face
        target_z_neg = create_v3(0, 0, -1)
        aligned_face = timber.get_closest_oriented_face(target_z_neg)
        assert aligned_face == TimberFace.LEFT
        
        # Target pointing in +X (length direction) should align with TOP face
        target_x_pos = create_v3(1, 0, 0)
        aligned_face = timber.get_closest_oriented_face(target_x_pos)
        assert aligned_face == TimberFace.TOP
        
        # Target pointing in +Y should align with BACK face
        target_y_pos = create_v3(0, 1, 0)
        aligned_face = timber.get_closest_oriented_face(target_y_pos)
        assert aligned_face == TimberFace.BACK
    
    def test_timber_get_closest_oriented_face_diagonal(self):
        """Test Timber.get_closest_oriented_face() with diagonal target direction."""
        # Create an axis-aligned timber
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        
                # Test with diagonal direction that's closer to +Z than +X
        # This should align with TOP face (Z-direction)
        target_diagonal_z = normalize_vector(create_v3(Rational("0.3"), 0, 1))  # Mostly +Z, little bit +X
        aligned_face = timber.get_closest_oriented_face(target_diagonal_z)
        assert aligned_face == TimberFace.TOP

        # Test with diagonal direction that's closer to +X than +Z
        # This should align with RIGHT face (X-direction)
        target_diagonal_x = normalize_vector(create_v3(1, 0, Rational("0.3")))  # Mostly +X, little bit +Z
        aligned_face = timber.get_closest_oriented_face(target_diagonal_x)
        assert aligned_face == TimberFace.RIGHT
    
    def test_timber_get_face_direction(self):
        """Test Timber.get_face_direction() method."""
        # Create an axis-aligned timber
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
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
        
        # FRONT should be the height direction
        front_dir = timber.get_face_direction(TimberFace.FRONT)
        assert front_dir == timber.height_direction
        
        # BACK should be the negative height direction
        back_dir = timber.get_face_direction(TimberFace.BACK)
        assert back_dir == -timber.height_direction
    
    def test_timber_get_face_direction_for_ends(self):
        """Test using Timber.get_face_direction() for timber ends."""
        # Create a timber
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        
        # Test TOP end direction (using TimberFace.TOP)
        top_dir = timber.get_face_direction(TimberFace.TOP)
        assert top_dir == timber.length_direction
        
        # Test BOTTOM end direction (using TimberFace.BOTTOM)
        bottom_dir = timber.get_face_direction(TimberFace.BOTTOM)
        assert bottom_dir == -timber.length_direction
    
    def test_timber_get_face_direction_with_timber_reference_end(self):
        """Test that Timber.get_face_direction() accepts TimberReferenceEnd."""
        # Create a timber
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        
        # Test TOP end direction using TimberReferenceEnd.TOP
        top_dir = timber.get_face_direction(TimberReferenceEnd.TOP)
        assert top_dir == timber.length_direction
        
        # Test BOTTOM end direction using TimberReferenceEnd.BOTTOM
        bottom_dir = timber.get_face_direction(TimberReferenceEnd.BOTTOM)
        assert bottom_dir == -timber.length_direction
        
        # Verify that results are the same whether using TimberFace or TimberReferenceEnd
        assert timber.get_face_direction(TimberReferenceEnd.TOP) == timber.get_face_direction(TimberFace.TOP)
        assert timber.get_face_direction(TimberReferenceEnd.BOTTOM) == timber.get_face_direction(TimberFace.BOTTOM)
    
    def test_timber_get_size_in_face_normal_axis_with_timber_reference_end(self):
        """Test that Timber.get_size_in_face_normal_axis() accepts TimberReferenceEnd."""
        # Create a timber
        timber = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        
        # Test that TimberReferenceEnd works
        top_size = timber.get_size_in_face_normal_axis(TimberReferenceEnd.TOP)
        assert top_size == timber.length
        
        bottom_size = timber.get_size_in_face_normal_axis(TimberReferenceEnd.BOTTOM)
        assert bottom_size == timber.length
        
        # Verify that results are the same whether using TimberFace or TimberReferenceEnd
        assert timber.get_size_in_face_normal_axis(TimberReferenceEnd.TOP) == timber.get_size_in_face_normal_axis(TimberFace.TOP)
        assert timber.get_size_in_face_normal_axis(TimberReferenceEnd.BOTTOM) == timber.get_size_in_face_normal_axis(TimberFace.BOTTOM)
    
    def test_timber_reference_end_to_timber_face_conversion(self):
        """Test TimberReferenceEnd.to_timber_face() conversion method."""
        # Test TOP conversion
        assert TimberReferenceEnd.TOP.to_timber_face() == TimberFace.TOP
        
        # Test BOTTOM conversion
        assert TimberReferenceEnd.BOTTOM.to_timber_face() == TimberFace.BOTTOM
    
    def testare_timbers_parallel(self):
        """Test are_timbers_parallel helper function."""
        # Create two timbers with parallel length directions
        timber1 = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        
        timber2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.15"), Rational("0.25")),
            bottom_position=create_v3(2, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Same direction
            width_direction=create_v3(0, 1, 0)      # Different face direction
        )
        
        # Should be parallel (parallel length directions)
        assert are_timbers_parallel(timber1, timber2)
        
        # Create a timber with opposite direction (still parallel)
        timber3 = timber_from_directions(
            length=Rational("1.5"),
            size=create_v2(Rational("0.1"), Rational("0.2")),
            bottom_position=create_v3(-1, 0, 0),
            length_direction=create_v3(0, 0, -1),  # Opposite direction
            width_direction=create_v3(1, 0, 0)
        )
        
        # Should still be parallel (anti-parallel is still parallel)
        assert are_timbers_parallel(timber1, timber3)
        
        # Create a timber with perpendicular direction
        timber4 = timber_from_directions(
            length=Rational("2.5"),
            size=create_v2(Rational("0.3"), Rational("0.3")),
            bottom_position=create_v3(1, 1, 0),
            length_direction=create_v3(1, 0, 0),   # Perpendicular
            width_direction=create_v3(0, 0, 1)
        )
        
        # Should NOT be parallel
        assert not are_timbers_parallel(timber1, timber4)
    
    def testare_timbers_orthogonal(self):
        """Test are_timbers_orthogonal helper function."""
        # Create two timbers with perpendicular length directions
        timber1 = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        
        timber2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.15"), Rational("0.25")),
            bottom_position=create_v3(2, 0, 0),
            length_direction=create_v3(1, 0, 0),   # X-right (perpendicular to timber1)
            width_direction=create_v3(0, 0, 1)      # Z-up
        )
        
        # Should be orthogonal
        assert are_timbers_orthogonal(timber1, timber2)
        
        # Create a timber with parallel direction
        timber3 = timber_from_directions(
            length=Rational("1.5"),
            size=create_v2(Rational("0.1"), Rational("0.2")),
            bottom_position=create_v3(-1, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Same as timber1
            width_direction=create_v3(1, 0, 0)
        )
        
        # Should NOT be orthogonal
        assert not are_timbers_orthogonal(timber1, timber3)
        
        # Test with Y-direction
        timber4 = timber_from_directions(
            length=Rational("2.5"),
            size=create_v2(Rational("0.3"), Rational("0.3")),
            bottom_position=create_v3(1, 1, 0),
            length_direction=create_v3(0, 1, 0),   # Y-forward (perpendicular to timber1)
            width_direction=create_v3(1, 0, 0)
        )
        
        # Should be orthogonal
        assert are_timbers_orthogonal(timber1, timber4)
    
    def testare_timbers_face_aligned(self):
        """Test are_timbers_face_aligned helper function."""
        # Create a reference timber with standard orientation
        timber1 = timber_from_directions(
            length=Rational(2),
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Z-up
            width_direction=create_v3(1, 0, 0)      # X-right
        )
        # timber1 directions: length=[0,0,1], face=[1,0,0], height=[0,1,0]
        
        # Test 1: Timber with same orientation - should be face-aligned
        timber2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.15"), Rational("0.25")),
            bottom_position=create_v3(2, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Same as timber1
            width_direction=create_v3(1, 0, 0)      # Same as timber1
        )
        assert are_timbers_face_aligned(timber1, timber2)
        
        # Test 2: Timber rotated 90° around Z - should be face-aligned  
        # (length stays Z, but face becomes Y, height becomes -X)
        timber3 = timber_from_directions(
            length=Rational("1.5"),
            size=create_v2(Rational("0.1"), Rational("0.2")),
            bottom_position=create_v3(-1, 0, 0),
            length_direction=create_v3(0, 0, 1),   # Same Z
            width_direction=create_v3(0, 1, 0)      # Y direction
        )
        assert are_timbers_face_aligned(timber1, timber3)
        
        # Test 3: Timber rotated 90° around X - should be face-aligned
        # (length becomes -Y, face stays X, height becomes Z) 
        timber4 = timber_from_directions(
            length=Rational("2.5"),
            size=create_v2(Rational("0.3"), Rational("0.3")),
            bottom_position=create_v3(1, 1, 0),
            length_direction=create_v3(0, -1, 0),  # -Y direction
            width_direction=create_v3(1, 0, 0)      # Same X
        )
        assert are_timbers_face_aligned(timber1, timber4)
        
        # Test 4: Timber with perpendicular orientation but face-aligned
        # (length becomes X, face becomes Z, height becomes Y)
        timber5 = timber_from_directions(
            length=Rational("1.8"),
            size=create_v2(Rational("0.2"), Rational("0.2")),
            bottom_position=create_v3(0, 2, 0),
            length_direction=create_v3(1, 0, 0),   # X direction  
            width_direction=create_v3(0, 0, 1)      # Z direction
        )
        assert are_timbers_face_aligned(timber1, timber5)
        
        # Test 5: Timber with arbitrary 3D rotation - should NOT be face-aligned
        # Using a rotation that doesn't align any direction with cardinal axes
        import math
        # Create a rotation that's 30° around X, then 45° around the new Y
        cos30 = math.cos(math.pi/6)
        sin30 = math.sin(math.pi/6)
        cos45 = math.cos(math.pi/4)
        sin45 = math.sin(math.pi/4)
        
        # This creates a timber whose directions don't align with any cardinal axes
        timber6 = timber_from_directions(
            length=Rational(1),
            size=create_v2(Rational("0.1"), Rational("0.1")),
            bottom_position=create_v3(0, 0, 2),
            length_direction=create_v3(sin45*cos30, sin45*sin30, cos45),  # Complex 3D direction
            width_direction=create_v3(cos45*cos30, cos45*sin30, -sin45)    # Perpendicular complex direction
        )
        assert not are_timbers_face_aligned(timber1, timber6)
        
        # Test 6: Verify that 45° rotation in XY plane IS face-aligned 
        # (because height direction is still Z, parallel to timber1's length direction)
        cos45_xy = math.cos(math.pi/4)
        sin45_xy = math.sin(math.pi/4)
        timber7 = timber_from_directions(
            length=Rational(1),
            size=create_v2(Rational("0.1"), Rational("0.1")),
            bottom_position=create_v3(0, 0, 2),
            length_direction=create_v3(cos45_xy, sin45_xy, 0),  # 45° in XY plane
            width_direction=create_v3(-sin45_xy, cos45_xy, 0)    # Perpendicular in XY
        )
        # This SHOULD be face-aligned because height direction = [0,0,1] = timber1.length_direction
        assert are_timbers_face_aligned(timber1, timber7)
        
        # Test 8: Verify face-aligned timbers can be orthogonal
        # timber1 length=[0,0,1], timber5 length=[1,0,0] - these are orthogonal but face-aligned
        assert are_timbers_face_aligned(timber1, timber5)
        assert are_timbers_orthogonal(timber1, timber5)
        
        # Test 9: Verify face-aligned timbers can be parallel  
        # timber1 and timber2 have same length direction - parallel and face-aligned
        assert are_timbers_face_aligned(timber1, timber2)
        assert are_timbers_parallel(timber1, timber2)
    
    def testare_timbers_parallel_rational(self):
        """Test are_timbers_parallel with rational (exact) values."""
        from sympy import Rational
        
        # Create timbers with exact rational directions
        timber1 = timber_from_directions(
            length=2,
            size=create_v2(Rational(1, 5), Rational(3, 10)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        timber2 = timber_from_directions(
            length=3,
            size=create_v2(Rational(1, 10), Rational(1, 4)),
            bottom_position=create_v3(2, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Parallel
            width_direction=create_v3(0, 1, 0)
        )
        
        # Should be parallel (exact comparison)
        assert are_timbers_parallel(timber1, timber2)
        
        # Test anti-parallel (should still be parallel)
        timber3 = timber_from_directions(
            length=Rational(3, 2),
            size=create_v2(Rational(1, 10), Rational(1, 5)),
            bottom_position=create_v3(-1, 0, 0),
            length_direction=create_v3(0, 0, -1),  # Anti-parallel
            width_direction=create_v3(1, 0, 0)
        )
        
        assert are_timbers_parallel(timber1, timber3)
        
        # Test perpendicular (should not be parallel)
        timber4 = timber_from_directions(
            length=2,
            size=create_v2(Rational(3, 10), Rational(3, 10)),
            bottom_position=create_v3(1, 1, 0),
            length_direction=create_v3(1, 0, 0),  # Perpendicular
            width_direction=create_v3(0, 0, 1)
        )
        
        assert not are_timbers_parallel(timber1, timber4)
    
    def testare_timbers_parallel_float(self):
        """Test are_timbers_parallel with float (fuzzy) values."""
        import math
        
        # Create timbers with float directions
        timber1 = create_standard_vertical_timber(height=2, size=(0.2, 0.3), position=(0, 0, 0))
        
        # Slightly off parallel (within tolerance)
        small_angle = 1e-11
        timber2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.15"), Rational("0.25")),
            bottom_position=create_v3(Rational(2), Rational(0), Rational(0)),
            length_direction=create_v3(math.sin(small_angle), Rational(0), math.cos(small_angle)),
            width_direction=create_v3(math.cos(small_angle), Rational(0), -math.sin(small_angle))
        )
        
        # Should be parallel (fuzzy comparison)
        assert are_timbers_parallel(timber1, timber2)
    
    def testare_timbers_orthogonal_rational(self):
        """Test are_timbers_orthogonal with rational (exact) values."""
        from sympy import Rational
        
        # Create timbers with exact rational perpendicular directions
        timber1 = timber_from_directions(
            length=2,
            size=create_v2(Rational(1, 5), Rational(3, 10)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        timber2 = timber_from_directions(
            length=3,
            size=create_v2(Rational(15, 100), Rational(1, 4)),
            bottom_position=create_v3(2, 0, 0),
            length_direction=create_v3(1, 0, 0),  # Perpendicular
            width_direction=create_v3(0, 0, 1)
        )
        
        # Should be orthogonal (exact comparison)
        assert are_timbers_orthogonal(timber1, timber2)
        
        # Test non-orthogonal
        timber3 = timber_from_directions(
            length=Rational(3, 2),
            size=create_v2(Rational(1, 10), Rational(1, 5)),
            bottom_position=create_v3(-1, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Parallel to timber1
            width_direction=create_v3(1, 0, 0)
        )
        
        assert not are_timbers_orthogonal(timber1, timber3)
    
    def testare_timbers_orthogonal_float(self):
        """Test are_timbers_orthogonal with float (fuzzy) values."""
        import math
        
        # Create timbers with float perpendicular directions
        timber1 = create_standard_vertical_timber(height=2, size=(0.2, 0.3), position=(0, 0, 0))
        
        # Nearly perpendicular (within tolerance)
        small_offset = 1e-11
        timber2 = timber_from_directions(
            length=Rational(3),
            size=create_v2(Rational("0.15"), Rational("0.25")),
            bottom_position=create_v3(Rational(2), Rational(0), Rational(0)),
            length_direction=create_v3(Rational(1), Rational(0), small_offset),
            width_direction=create_v3(Rational(0), Rational(1), Rational(0))
        )
        
        # Should be orthogonal (fuzzy comparison)
        assert are_timbers_orthogonal(timber1, timber2)
    
    def testare_timbers_face_aligned_exact_equality(self):
        """Test are_timbers_face_aligned with exact equality (no tolerance)."""
        # Create two face-aligned timbers using exact rational values
        timber1 = timber_from_directions(
            length=2,  # Integer
            size=create_v2(Rational(1, 5), Rational(3, 10)),  # Exact rationals
            bottom_position=create_v3(0, 0, 0),  # Integers
            length_direction=create_v3(0, 0, 1),   # Vertical - integers
            width_direction=create_v3(1, 0, 0)      # East - integers
        )
        
        timber2 = timber_from_directions(
            length=3,  # Integer
            size=create_v2(Rational(3, 20), Rational(1, 4)),  # Exact rationals
            bottom_position=create_v3(2, 0, 0),  # Integers
            length_direction=create_v3(1, 0, 0),   # East (perpendicular to timber1) - integers
            width_direction=create_v3(0, 0, 1)      # Up - integers
        )
        
        # These should be face-aligned with exact equality (no tolerance)
        assert are_timbers_face_aligned(timber1, timber2, tolerance=None)
        
        # Create a non-face-aligned timber (3D rotation with no aligned axes)
        # Using a timber rotated in 3D such that none of its axes align with timber1's axes
        timber3 = timber_from_directions(
            length=2,  # Integer
            size=create_v2(Rational(1, 5), Rational(1, 5)),  # Exact rationals
            bottom_position=create_v3(3, 3, 0),  # Integers
            length_direction=create_v3(1, 1, 1),   # 3D diagonal (will be normalized to Float)
            width_direction=create_v3(1, -1, 0)     # Perpendicular in 3D (will be normalized to Float)
        )
        
        # timber1 and timber3 should NOT be face-aligned
        # Note: timber3's normalized directions contain Float values, but the new
        # system automatically handles this without warnings
        result = are_timbers_face_aligned(timber1, timber3, tolerance=None)
        assert not result
        
        # Test with tolerance parameter (no warning)
        assert are_timbers_face_aligned(timber1, timber2, tolerance=1e-10)
    
    # COMMENTED OUT: Tests for deleted helper functions
    # def test_project_point_on_timber_centerline(self):
    #     """Test _project_point_on_timber_centerline helper function."""
    #     pass
    
    # def test_calculate_mortise_position_from_tenon_intersection(self):
    #     """Test _calculate_mortise_position_from_tenon_intersection helper function."""
    #     pass

    def test_do_xy_cross_section_on_parallel_timbers_overlap(self):
        """Test do_xy_cross_section_on_parallel_timbers_overlap function."""
        from sympy import Rational
        
        # Test 1: Two aligned timbers that overlap
        timber1 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber1'
        )
        
        timber2 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(5, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber2'
        )
        
        assert do_xy_cross_section_on_parallel_timbers_overlap(timber1, timber2), \
            "Aligned timbers at same cross-section should overlap"
        
        # Test 2: Two aligned timbers that don't overlap (separated in Y)
        timber3 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(5, 10, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber3'
        )
        
        assert not do_xy_cross_section_on_parallel_timbers_overlap(timber1, timber3), \
            "Timbers separated in Y should not overlap"
        
        # Test 3: Two rotated timbers that overlap
        timber4 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber4'
        )
        
        timber5 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 0, 1),  # Rotated 90 degrees
            name='timber5'
        )
        
        assert do_xy_cross_section_on_parallel_timbers_overlap(timber4, timber5), \
            "Rotated timbers at same position should overlap"
        
        # Test 4: Timbers that just touch at edge (should overlap)
        timber6 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber6'
        )
        
        # timber6 spans Y: -2 to 2
        # timber7 at Y=4 spans Y: 2 to 6, so they just touch
        timber7 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, Rational(4), 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber7'
        )
        
        assert do_xy_cross_section_on_parallel_timbers_overlap(timber6, timber7), \
            "Timbers touching at edge should overlap"
        
        # Test 5: Timbers with small gap (should not overlap)
        timber8 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, Rational(4) + Rational('0.01'), 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber8'
        )
        
        assert not do_xy_cross_section_on_parallel_timbers_overlap(timber6, timber8), \
            "Timbers with small gap should not overlap"
        
        # Test 6: Anti-parallel timbers (same direction but opposite ends)
        timber9 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber9'
        )
        
        timber10 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(20, 0, 0),
            length_direction=create_v3(-1, 0, 0),  # Opposite direction
            width_direction=create_v3(0, 1, 0),
            name='timber10'
        )
        
        assert do_xy_cross_section_on_parallel_timbers_overlap(timber9, timber10), \
            "Anti-parallel timbers at same cross-section should overlap"
        
        # Test 7: Offset rotated timbers
        timber11 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(6)),  # 4 wide, 6 high
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name='timber11'
        )
        
        # Rotated 90 degrees and offset
        timber12 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(6), Rational(4)),  # 6 wide, 4 high
            bottom_position=create_v3(Rational(4), 0, 0),  # Offset in X
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(0, 1, 0),  # Rotated 90 degrees
            name='timber12'
        )
        
        # timber11: X spans -2 to 2, Y spans -3 to 3
        # timber12: X spans 1 to 7, Y spans -2 to 2
        # They should overlap in the region X: 1 to 2, Y: -2 to 2
        assert do_xy_cross_section_on_parallel_timbers_overlap(timber11, timber12), \
            "Offset rotated timbers with partial overlap should overlap"
        
        # Test 8: Assertion error for non-parallel timbers
        timber13 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),
            width_direction=create_v3(0, 1, 0),
            name='timber13'
        )
        
        timber14 = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 1, 0),  # Perpendicular
            width_direction=create_v3(1, 0, 0),
            name='timber14'
        )
        
        # Should raise assertion error for non-parallel timbers
        try:
            do_xy_cross_section_on_parallel_timbers_overlap(timber13, timber14)
            assert False, "Should have raised AssertionError for non-parallel timbers"
        except AssertionError as e:
            assert "must be parallel" in str(e)


class TestTimberFootprintOrientation:
    """Test timber inside/outside face determination relative to footprint."""
    
    def test_get_inside_outside_faces(self):
        """Test get_inside_face and get_outside_face for various timber configurations."""
        # Create a square footprint
        corners = [
            create_v2(0, 0),
            create_v2(10, 0),
            create_v2(10, 10),
            create_v2(0, 10)
        ]
        footprint = Footprint(corners)
        
        # Test configurations: (description, bottom_pos, length_dir, width_dir, length, expected_inside, expected_outside)
        test_cases = [
            # Horizontal timber near bottom edge (y=1), running along X
            ("bottom_edge", 
             create_v3(1, 1, 0), create_v3(1, 0, 0), create_v3(0, 1, 0), Rational(8),
             TimberFace.RIGHT, TimberFace.LEFT),
            
            # Timber near right edge (x=9), running along Y
            ("right_edge", 
             create_v3(9, 1, 0), create_v3(0, 1, 0), create_v3(-1, 0, 0), Rational(8),
             TimberFace.TOP, TimberFace.BOTTOM),
            
            # Horizontal timber near top edge (y=9), running along X
            ("top_edge", 
             create_v3(1, 9, 0), create_v3(1, 0, 0), create_v3(0, -1, 0), Rational(8),
             TimberFace.BOTTOM, TimberFace.TOP),
            
            # Timber near left edge (x=1), running along Y
            ("left_edge", 
             create_v3(1, 1, 0), create_v3(0, 1, 0), create_v3(1, 0, 0), Rational(8),
             TimberFace.TOP, TimberFace.BOTTOM),
            
            # Vertical timber near bottom edge
            ("vertical", 
             create_v3(5, 1, 0), create_v3(0, 0, 1), create_v3(0, 1, 0), Rational(3),
             TimberFace.RIGHT, TimberFace.LEFT),
        ]
        
        for description, bottom_pos, length_dir, width_dir, length, expected_inside, expected_outside in test_cases:
            timber = timber_from_directions(
                length=length,
                size=create_v2(Rational("0.2"), Rational("0.3")),
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
            create_v2(0, 0),
            create_v2(10, 0),
            create_v2(10, 10),
            create_v2(0, 10)
        ]
        footprint = Footprint(corners)
        
        # Diagonal timber from (1,1) going toward (9,9), but oriented so width points inward
        timber = timber_from_directions(
            length=Rational("11.31"),  # ~8*sqrt(2)
            size=create_v2(Rational("0.2"), Rational("0.3")),
            bottom_position=create_v3(1, 1, 0),
            length_direction=normalize_vector(create_v3(1, 1, 0)),  # Diagonal
            width_direction=normalize_vector(create_v3(-1, 1, 0))   # Perpendicular to length, pointing "inward-ish"
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
        timber = create_standard_vertical_timber(height=10, size=(4, 4), position=(0, 0, 0), name="Test Timber")
        
        # Split at 30% (distance 3)
        bottom_timber, top_timber = split_timber(timber, Rational(3))
        
        # Check bottom timber
        assert bottom_timber.length == Rational(3)
        assert bottom_timber.size[0] == Rational(4)
        assert bottom_timber.size[1] == Rational(4)
        assert bottom_timber.bottom_position == create_v3(Rational(0), Rational(0), Rational(0))
        assert bottom_timber.length_direction == create_v3(Rational(0), Rational(0), Rational(1))
        assert bottom_timber.width_direction == create_v3(Rational(1), Rational(0), Rational(0))
        assert bottom_timber.name == "Test Timber_bottom"
        
        # Check top timber
        assert top_timber.length == Rational(7)
        assert top_timber.size[0] == Rational(4)
        assert top_timber.size[1] == Rational(4)
        assert top_timber.bottom_position == create_v3(Rational(0), Rational(0), Rational(3))
        assert top_timber.length_direction == create_v3(Rational(0), Rational(0), Rational(1))
        assert top_timber.width_direction == create_v3(Rational(1), Rational(0), Rational(0))
        assert top_timber.name == "Test Timber_top"
    
    def test_split_timber_horizontal(self):
        """Test splitting a horizontal timber"""
        # Create a horizontal timber along X axis
        timber = timber_from_directions(
            length=Rational(20),
            size=create_v2(Rational(6), Rational(4)),
            bottom_position=create_v3(Rational(5), Rational(10), Rational(2)),
            length_direction=create_v3(Rational(1), Rational(0), Rational(0)),
            width_direction=create_v3(Rational(0), Rational(1), Rational(0))
        )
        
        # Split at 8 units from bottom
        bottom_timber, top_timber = split_timber(timber, Rational(8))
        
        # Check bottom timber
        assert bottom_timber.length == Rational(8)
        assert bottom_timber.bottom_position == create_v3(Rational(5), Rational(10), Rational(2))
        
        # Check top timber
        assert top_timber.length == Rational(12)
        assert top_timber.bottom_position == create_v3(Rational(13), Rational(10), Rational(2))  # 5 + 8
    
    def test_split_timber_diagonal(self):
        """Test splitting a diagonal timber"""
        # Create a diagonal timber at 45 degrees
        length_dir = normalize_vector(create_v3(Rational(1), Rational(1), Rational(0)))
        
        timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(Rational(0), Rational(0), Rational(0)),
            length_direction=length_dir,
            width_direction=normalize_vector(create_v3(Rational(-1), Rational(1), Rational(0)))
        )
        
        # Split at 4 units from bottom
        bottom_timber, top_timber = split_timber(timber, Rational(4))
        
        # Check lengths
        assert bottom_timber.length == Rational(4)
        assert top_timber.length == Rational(6)
        
        # Check positions
        assert bottom_timber.bottom_position == create_v3(Rational(0), Rational(0), Rational(0))
        
        # Top timber should start at 4 units along the diagonal
        expected_top_pos = create_v3(Rational(0), Rational(0), Rational(0)) + Rational(4) * length_dir
        assert top_timber.bottom_position == expected_top_pos
        
        # Both should maintain same orientation
        assert bottom_timber.length_direction == length_dir
        assert top_timber.length_direction == length_dir
    
    def test_split_timber_with_rational(self):
        """Test splitting with exact rational arithmetic"""
        # Create a timber with rational values
        timber = timber_from_directions(
            length=Rational(10, 1),
            size=create_v2(Rational(4, 1), Rational(4, 1)),
            bottom_position=create_v3(Rational(0), Rational(0), Rational(0)),
            length_direction=create_v3(Rational(0), Rational(0), Rational(1)),
            width_direction=create_v3(Rational(1), Rational(0), Rational(0))
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
        timber = timber_from_directions(
            length=Rational(10),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(Rational(0), Rational(0), Rational(0)),
            length_direction=create_v3(Rational(0), Rational(0), Rational(1)),
            width_direction=create_v3(Rational(1), Rational(0), Rational(0))
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
        timber = timber_from_directions(
            length=Rational(15),
            size=create_v2(Rational(6), Rational(8)),
            bottom_position=create_v3(Rational(1), Rational(2), Rational(3)),
            length_direction=normalize_vector(create_v3(Rational(0), Rational(1), Rational(1))),
            width_direction=normalize_vector(create_v3(Rational(1), Rational(0), Rational(0)))
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


