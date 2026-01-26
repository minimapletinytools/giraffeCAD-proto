"""
Tests for the measuring module (geometric primitives).
"""

import pytest
from code_goes_here.measuring import Point, Line, Plane, UnsignedPlane, get_point_on_face_global, get_point_on_feature, measure_from_face, mark_from_face
from code_goes_here.timber import timber_from_directions, TimberFace
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


class TestGetPointOnFace:
    """Tests for get_point_on_face_global helper function"""
    
    def test_get_point_on_right_face(self):
        """Test getting a point on the RIGHT face of a vertical timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        point = get_point_on_face_global(TimberFace.RIGHT, timber)
        
        # RIGHT face is at x=5 (half the width), should be at the center
        assert point[0] == Rational(5)
        assert point[1] == Rational(0)  # Centered in height
        assert point[2] == Rational(0)  # At bottom in length
    
    def test_get_point_on_top_face(self):
        """Test getting a point on the TOP face of a vertical timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        point = get_point_on_face_global(TimberFace.TOP, timber)
        
        # get_point_on_face_global returns a point at the center of the face
        # For TOP face, it's at the centerline (z=50) plus half the timber length
        assert point[0] == Rational(0)  # Centered in width
        assert point[1] == Rational(0)  # Centered in height
        assert point[2] == Rational(50)  # At centerline along length axis


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
    """Tests for measure_from_face function"""
    
    def test_measure_zero_distance_from_face(self):
        """Test measuring zero distance creates plane at face surface"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        plane = measure_from_face(Rational(0), TimberFace.RIGHT, timber)
        
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
        
        plane = measure_from_face(Rational(3), TimberFace.RIGHT, timber)
        
        # Point should be 3 units inside from face (x=5-3=2)
        assert plane.point[0] == Rational(2)
        assert plane.normal.equals(create_v3(1, 0, 0))


class TestMarkFromFace:
    """Tests for mark_from_face function"""
    
    def test_mark_from_face_round_trip(self):
        """Test that mark_from_face is inverse of measure_from_face"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Test round trip for various distances
        for distance in [Rational(0), Rational(5), Rational(10), Rational(-2)]:
            plane = measure_from_face(distance, TimberFace.RIGHT, timber)
            marked = mark_from_face(plane, TimberFace.RIGHT, timber)
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
        distance = mark_from_face(point, TimberFace.RIGHT, timber)
        
        assert distance == Rational(3)
