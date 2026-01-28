"""
Tests for the measuring module (geometric primitives).
"""

import pytest
from code_goes_here.measuring import Point, Line, Plane, UnsignedPlane, get_point_on_feature, measure_into_face, mark_onto_face, gauge_distance_between_faces, measure_face, measure_long_edge, measure_center_line
from code_goes_here.timber import timber_from_directions, TimberFace, TimberLongEdge
from code_goes_here.moothymoth import create_v3, create_v2, Transform, Orientation
from sympy import Matrix, Rational


class TestPoint:
    """Tests for Point class"""
    
    def test_point_creation(self):
        """Test creating a point"""
        pos = create_v3(1, 2, 3)
        point = Point(pos)
        assert point.position.equals(pos)
    
    def test_point_is_frozen(self):
        """Test that Point is immutable"""
        point = Point(create_v3(1, 2, 3))
        with pytest.raises(Exception):
            point.position = create_v3(4, 5, 6)
    
    def test_point_repr(self):
        """Test Point string representation"""
        point = Point(create_v3(1, 2, 3))
        assert "Point" in repr(point)
        assert "position" in repr(point)


class TestLine:
    """Tests for Line class"""
    
    def test_line_creation(self):
        """Test creating a line"""
        direction = create_v3(0, 0, 1)
        point = create_v3(1, 2, 3)
        line = Line(direction, point)
        assert line.direction.equals(direction)
        assert line.point.equals(point)
    
    def test_line_is_frozen(self):
        """Test that Line is immutable"""
        line = Line(create_v3(0, 0, 1), create_v3(1, 2, 3))
        with pytest.raises(Exception):
            line.direction = create_v3(1, 0, 0)
    
    def test_line_repr(self):
        """Test Line string representation"""
        line = Line(create_v3(0, 0, 1), create_v3(1, 2, 3))
        assert "Line" in repr(line)
        assert "direction" in repr(line)
        assert "point" in repr(line)


class TestPlane:
    """Tests for Plane class"""
    
    def test_plane_creation(self):
        """Test creating a plane"""
        normal = create_v3(0, 0, 1)
        point = create_v3(1, 2, 3)
        plane = Plane(normal, point)
        assert plane.normal.equals(normal)
        assert plane.point.equals(point)
    
    def test_plane_is_frozen(self):
        """Test that Plane is immutable"""
        plane = Plane(create_v3(0, 0, 1), create_v3(1, 2, 3))
        with pytest.raises(Exception):
            plane.normal = create_v3(1, 0, 0)
    
    def test_plane_repr(self):
        """Test Plane string representation"""
        plane = Plane(create_v3(0, 0, 1), create_v3(1, 2, 3))
        assert "Plane" in repr(plane)
        assert "normal" in repr(plane)
        assert "point" in repr(plane)
    
    def test_plane_from_transform_and_direction_identity(self):
        """Test creating plane from identity transform"""
        transform = Transform.identity()
        local_direction = create_v3(0, 1, 0)
        
        plane = Plane.from_transform_and_direction(transform, local_direction)
        
        # For identity transform, global direction should equal local direction
        assert plane.normal.equals(local_direction)
        # Point should be at origin
        assert plane.point.equals(create_v3(0, 0, 0))
    
    def test_plane_from_transform_and_direction_rotated(self):
        """Test creating plane from rotated transform"""
        # Create a transform rotated 90 degrees around Z axis
        # This transforms local +X to global +Y and local +Y to global -X
        orientation = Orientation(Matrix([
            [0, -1, 0],
            [1,  0, 0],
            [0,  0, 1]
        ]))
        position = create_v3(5, 0, 0)
        transform = Transform(position, orientation)
        
        # Local direction pointing in +X
        local_direction = create_v3(1, 0, 0)
        
        plane = Plane.from_transform_and_direction(transform, local_direction)
        
        # After rotation, local +X becomes global +Y
        expected_normal = create_v3(0, 1, 0)
        assert plane.normal.equals(expected_normal)
        # Point should be at transform position
        assert plane.point.equals(position)
    
    def test_plane_from_transform_and_direction_translated(self):
        """Test that plane point is at transform position"""
        position = create_v3(10, 20, 30)
        transform = Transform(position, Orientation.identity())
        local_direction = create_v3(0, 0, 1)
        
        plane = Plane.from_transform_and_direction(transform, local_direction)
        
        assert plane.point.equals(position)
        assert plane.normal.equals(local_direction)


class TestGetPointOnFeature:
    """Tests for get_point_on_feature helper function"""
    
    def test_get_point_on_point_feature(self):
        """Test getting point from Point feature"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        test_position = create_v3(1, 2, 3)
        point_feature = Point(test_position)
        
        result = get_point_on_feature(point_feature, timber)
        assert result.equals(test_position)
    
    def test_get_point_on_plane_feature(self):
        """Test getting point from Plane feature"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        test_point = create_v3(5, 5, 5)
        plane_feature = Plane(create_v3(1, 0, 0), test_point)
        
        result = get_point_on_feature(plane_feature, timber)
        assert result.equals(test_point)


class TestMeasureFromFace:
    """Tests for measure_into_face function"""
    
    def test_measure_zero_distance_from_face(self):
        """Test measuring zero distance creates plane at face surface"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        plane = measure_into_face(Rational(0), TimberFace.RIGHT, timber)
        
        # Should be an UnsignedPlane
        assert isinstance(plane, UnsignedPlane)
        # Normal should point in the face direction (outward)
        assert plane.normal.equals(create_v3(1, 0, 0))
        # Point should be at the face surface (x=5)
        assert plane.point[0] == Rational(5)
    
    def test_measure_positive_distance_from_face(self):
        """Test measuring positive distance INTO the face"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        plane = measure_into_face(Rational(3), TimberFace.RIGHT, timber)
        
        # Point should be 3 units inside from face (x=5-3=2)
        assert plane.point[0] == Rational(2)
        assert plane.normal.equals(create_v3(1, 0, 0))


class TestMarkFromFace:
    """Tests for mark_onto_face function"""
    
    def test_mark_onto_face_round_trip(self):
        """Test that mark_onto_face is inverse of measure_into_face"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Test round trip for various distances
        for distance in [Rational(0), Rational(5), Rational(10), Rational(-2)]:
            plane = measure_into_face(distance, TimberFace.RIGHT, timber)
            marked = mark_onto_face(plane, TimberFace.RIGHT, timber)
            assert marked == distance
    
    def test_mark_point_from_face(self):
        """Test marking a point feature from a face"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Point at x=2 (3 units inside from RIGHT face which is at x=5)
        point = Point(create_v3(2, 0, 0))
        distance = mark_onto_face(point, TimberFace.RIGHT, timber)
        
        assert distance == Rational(3)


class TestGaugeDistanceBetweenFaces:
    """Tests for gauge_distance_between_faces function"""
    
    def test_gauge_all_face_combinations_on_face_aligned_timbers(self):
        """
        Test gauging distance between all face combinations on two face-aligned vertical timbers.
        
        Creates two vertical 4x6 timbers side by side:
        - timber1 centered at x=0, y=0 (width=4" along X, height=6" along Y)
        - timber2 centered at x=10", y=0 (width=4" along X, height=6" along Y)
        
        Tests all 36 face combinations (6 faces × 6 faces) to verify:
        - Parallel face pairs return correct distances
        - Non-parallel face pairs raise assertions
        """
        # Create timber1: vertical 4x6 at origin
        # - Width (X): from -2 to +2 (4 inches)
        # - Height (Y): from -3 to +3 (6 inches)
        # - Length (Z): from 0 to 100
        timber1 = timber_from_directions(
            length=Rational(100),
            size=create_v2(4, 6),  # 4" wide (X), 6" height (Y)
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Vertical
            width_direction=create_v3(1, 0, 0),   # Width along X
            name="timber1"
        )
        
        # Create timber2: vertical 4x6 at x=10
        # - Width (X): from 8 to 12 (4 inches)
        # - Height (Y): from -3 to +3 (6 inches)
        # - Length (Z): from 0 to 100
        timber2 = timber_from_directions(
            length=Rational(100),
            size=create_v2(4, 6),  # 4" wide (X), 6" height (Y)
            bottom_position=create_v3(10, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Vertical
            width_direction=create_v3(1, 0, 0),   # Width along X
            name="timber2"
        )
        
        # Define expected distances for parallel face pairs
        # Distance is measured from reference face INTO the reference timber
        expected_results = {
            # RIGHT face of timber1 (at x=2) to LEFT face of timber2 (at x=8): gap = 6"
            # From RIGHT face, positive INTO timber1 means going in -X direction
            # Target at x=8, reference at x=2, so distance = 2-8 = -6 (target is away from timber)
            (TimberFace.RIGHT, TimberFace.LEFT): Rational(-6),
            
            # LEFT face of timber1 (at x=-2) to RIGHT face of timber2 (at x=12)
            # From LEFT face, positive INTO timber1 means going in +X direction
            # Target at x=12, reference at x=-2, so distance = 12-(-2) = 14
            (TimberFace.LEFT, TimberFace.RIGHT): Rational(14),
            
            # RIGHT faces (both at x=2 and x=12, parallel, facing same direction +X)
            # From RIGHT of timber1 (x=2) to RIGHT of timber2 (x=12)
            # Into timber1 from RIGHT means -X, target at x=12, ref at x=2: distance = 2-12 = -10
            (TimberFace.RIGHT, TimberFace.RIGHT): Rational(-10),
            
            # LEFT faces (both at x=-2 and x=8, parallel, facing same direction -X)
            # From LEFT of timber1 (x=-2) to LEFT of timber2 (x=8)
            # Into timber1 from LEFT means +X, target at x=8, ref at x=-2: distance = 8-(-2) = 10
            (TimberFace.LEFT, TimberFace.LEFT): Rational(10),
            
            # FRONT faces (both at y=3, parallel, facing same direction +Y)
            # From FRONT of timber1 to FRONT of timber2 (both at y=3)
            # Into timber1 from FRONT means -Y, target at y=3, ref at y=3: distance = 0
            (TimberFace.FRONT, TimberFace.FRONT): Rational(0),
            
            # BACK faces (both at y=-3, parallel, facing same direction -Y)
            # From BACK of timber1 to BACK of timber2 (both at y=-3)
            # Into timber1 from BACK means +Y, target at y=-3, ref at y=-3: distance = 0
            (TimberFace.BACK, TimberFace.BACK): Rational(0),
            
            # FRONT to BACK (antiparallel, facing each other)
            # FRONT at y=3, BACK at y=-3 (same for both timbers since they're aligned)
            # From FRONT (y=3) of timber1, into timber means -Y direction
            # Target BACK of timber2 at y=-3, ref FRONT at y=3: distance = 3-(-3) = 6
            (TimberFace.FRONT, TimberFace.BACK): Rational(6),
            
            # BACK to FRONT (antiparallel, facing each other)
            # From BACK (y=-3) of timber1, into timber means +Y direction
            # Target FRONT of timber2 at y=3, ref BACK at y=-3: distance = 3-(-3) = 6
            (TimberFace.BACK, TimberFace.FRONT): Rational(6),
            
            # TOP faces (both at z=50, parallel, facing same direction +Z)
            (TimberFace.TOP, TimberFace.TOP): Rational(0),
            
            # BOTTOM faces (both at z=-50, parallel, facing same direction -Z)
            (TimberFace.BOTTOM, TimberFace.BOTTOM): Rational(0),
            
            # TOP to BOTTOM (antiparallel)
            # TOP face point at z=50, BOTTOM face point at z=-50
            # From TOP of timber1, into timber means -Z direction
            # Target BOTTOM of timber2 at z=-50, ref TOP at z=50
            # distance = 50-(-50) = 100
            (TimberFace.TOP, TimberFace.BOTTOM): Rational(100),
            
            # BOTTOM to TOP (antiparallel)
            # From BOTTOM of timber1, into timber means +Z direction
            # Target TOP of timber2 at z=50, ref BOTTOM at z=-50
            # distance = 50-(-50) = 100
            (TimberFace.BOTTOM, TimberFace.TOP): Rational(100),
        }
        
        # Test all 36 face combinations
        all_faces = [TimberFace.RIGHT, TimberFace.LEFT, TimberFace.FRONT, 
                     TimberFace.BACK, TimberFace.TOP, TimberFace.BOTTOM]
        
        for face1 in all_faces:
            for face2 in all_faces:
                if (face1, face2) in expected_results:
                    # Parallel faces - should return expected distance
                    distance = gauge_distance_between_faces(timber1, face1, timber2, face2)
                    expected = expected_results[(face1, face2)]
                    assert distance == expected, \
                        f"gauge_distance_between_faces({face1.name}, {face2.name}) = {distance}, expected {expected}"
                else:
                    # Non-parallel faces - should raise assertion
                    with pytest.raises(AssertionError, match="Faces must be parallel"):
                        gauge_distance_between_faces(timber1, face1, timber2, face2)


class TestMeasureFace:
    """Tests for measure_face function"""
    
    def test_measure_face_right(self):
        """Test measuring the RIGHT face of a vertical timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 20),  # 10" wide (X), 20" height (Y)
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Vertical
            width_direction=create_v3(1, 0, 0),   # Width along X
            name="test_timber"
        )
        
        plane = measure_face(timber, TimberFace.RIGHT)
        
        # Should be a Plane
        assert isinstance(plane, Plane)
        # Normal should point outward (+X for RIGHT face)
        assert plane.normal.equals(create_v3(1, 0, 0))
        # Point should be at the face surface (x=5, y=0, z=0)
        assert plane.point[0] == Rational(5)
        assert plane.point[1] == Rational(0)
        assert plane.point[2] == Rational(0)
    
    def test_measure_face_front(self):
        """Test measuring the FRONT face of a vertical timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 20),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        plane = measure_face(timber, TimberFace.FRONT)
        
        # Normal should point outward (+Y for FRONT face)
        assert plane.normal.equals(create_v3(0, 1, 0))
        # Point should be at the face surface (x=0, y=10, z=0)
        assert plane.point[0] == Rational(0)
        assert plane.point[1] == Rational(10)
        assert plane.point[2] == Rational(0)


class TestMeasureLongEdge:
    """Tests for measure_long_edge function"""
    
    def test_measure_long_edge_right_front(self):
        """Test measuring the RIGHT_FRONT edge of a vertical timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 20),  # 10" wide (X), 20" height (Y)
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Vertical
            width_direction=create_v3(1, 0, 0),   # Width along X
            name="test_timber"
        )
        
        line = measure_long_edge(timber, TimberLongEdge.RIGHT_FRONT)
        
        # Should be a Line
        assert isinstance(line, Line)
        # Direction should be along timber length (+Z)
        assert line.direction.equals(create_v3(0, 0, 1))
        # Point should be at the edge (x=5, y=10, z=0)
        assert line.point[0] == Rational(5)   # Right face at x=5
        assert line.point[1] == Rational(10)  # Front face at y=10
        assert line.point[2] == Rational(0)   # At bottom
    
    def test_measure_long_edge_left_back(self):
        """Test measuring the LEFT_BACK edge of a vertical timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 20),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        line = measure_long_edge(timber, TimberLongEdge.LEFT_BACK)
        
        # Direction should be along timber length (+Z)
        assert line.direction.equals(create_v3(0, 0, 1))
        # Point should be at the edge (x=-5, y=-10, z=0)
        assert line.point[0] == Rational(-5)   # Left face at x=-5
        assert line.point[1] == Rational(-10)  # Back face at y=-10
        assert line.point[2] == Rational(0)    # At bottom
    
    def test_measure_long_edge_horizontal_timber(self):
        """Test measuring edge on a horizontal timber"""
        # Horizontal timber pointing in +X direction
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(4, 6),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(1, 0, 0),  # Horizontal, pointing east
            width_direction=create_v3(0, 1, 0),
            name="test_timber"
        )
        
        line = measure_long_edge(timber, TimberLongEdge.RIGHT_FRONT)
        
        # Direction should be along timber length (+X in this case)
        assert line.direction.equals(create_v3(1, 0, 0))
        # Point should be at the edge
        assert line.point[0] == Rational(0)   # At bottom
        assert line.point[1] == Rational(2)   # Right face (width/2)
        assert line.point[2] == Rational(3)   # Front face (height/2)


class TestMeasureCenterLine:
    """Tests for measure_center_line function"""
    
    def test_measure_center_line_vertical(self):
        """Test measuring the center line of a vertical timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 20),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),  # Vertical
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        line = measure_center_line(timber)
        
        # Should be a Line
        assert isinstance(line, Line)
        # Direction should be along timber length (+Z)
        assert line.direction.equals(create_v3(0, 0, 1))
        # Point should be at the center (x=0, y=0, z=50)
        assert line.point[0] == Rational(0)
        assert line.point[1] == Rational(0)
        assert line.point[2] == Rational(50)  # Mid-length
    
    def test_measure_center_line_horizontal(self):
        """Test measuring the center line of a horizontal timber"""
        timber = timber_from_directions(
            length=Rational(48),
            size=create_v2(4, 6),
            bottom_position=create_v3(10, 20, 5),  # Offset position
            length_direction=create_v3(1, 0, 0),   # Horizontal, pointing east
            width_direction=create_v3(0, 1, 0),
            name="test_timber"
        )
        
        line = measure_center_line(timber)
        
        # Direction should be along timber length (+X)
        assert line.direction.equals(create_v3(1, 0, 0))
        # Point should be at the center
        assert line.point[0] == Rational(34)  # 10 + 48/2 = 34
        assert line.point[1] == Rational(20)  # Centered in Y
        assert line.point[2] == Rational(5)   # Centered in Z
    
    def test_measure_center_line_diagonal(self):
        """Test measuring the center line of a diagonally oriented timber"""
        # Timber pointing in diagonal direction
        from code_goes_here.moothymoth import normalize_vector
        
        direction = normalize_vector(create_v3(1, 1, 1))  # Diagonal
        timber = timber_from_directions(
            length=Rational(60),
            size=create_v2(4, 4),
            bottom_position=create_v3(0, 0, 0),
            length_direction=direction,
            width_direction=create_v3(1, 0, 0),
            name="test_timber"
        )
        
        line = measure_center_line(timber)
        
        # Direction should be along timber length (diagonal)
        assert line.direction.equals(direction)
        # Point should be at mid-length along the diagonal
        expected_point = direction * Rational(30)  # 60/2 = 30
        assert line.point.equals(expected_point)
