"""
Tests for the measuring module (geometric primitives).
"""

import pytest
from code_goes_here.measuring import Point, Line, Plane
from code_goes_here.moothymoth import create_v3, Transform, Orientation
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
