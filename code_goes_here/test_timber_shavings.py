"""
Tests for timber_shavings module (random timber-related helpers).
"""

import pytest
from code_goes_here.timber_shavings import *
from code_goes_here.timber import *
from code_goes_here.moothymoth import create_v3, create_v2
from sympy import Rational


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
            face=TimberLongFace.RIGHT,
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
            face=TimberLongFace.LEFT,
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
            face=TimberLongFace.FRONT,
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
            face=TimberLongFace.BACK,
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
            face=TimberLongFace.RIGHT,
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

