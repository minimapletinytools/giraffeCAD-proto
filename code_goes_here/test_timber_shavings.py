"""
Tests for timber_shavings module (random timber-related helpers).
"""

import pytest
from code_goes_here.timber_shavings import get_point_on_face_global, project_point_onto_face_global
from code_goes_here.timber import timber_from_directions, TimberFace
from code_goes_here.moothymoth import create_v3, create_v2
from sympy import Rational


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


class TestProjectPointOntoFace:
    """Tests for project_point_onto_face_global helper function"""
    
    def test_project_point_on_face_surface(self):
        """Test projecting a point that's exactly on the face surface"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Point exactly on RIGHT face (x=5)
        point = create_v3(5, 0, 50)
        distance = project_point_onto_face_global(point, TimberFace.RIGHT, timber)
        
        # Should be 0 (on the surface)
        assert distance == Rational(0)
    
    def test_project_point_inside_timber(self):
        """Test projecting a point inside the timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Point at x=2 (3 units inside from RIGHT face which is at x=5)
        point = create_v3(2, 0, 50)
        distance = project_point_onto_face_global(point, TimberFace.RIGHT, timber)
        
        # Should be positive (inside the timber)
        assert distance == Rational(3)
    
    def test_project_point_outside_timber(self):
        """Test projecting a point outside the timber"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # Point at x=8 (3 units outside from RIGHT face which is at x=5)
        point = create_v3(8, 0, 50)
        distance = project_point_onto_face_global(point, TimberFace.RIGHT, timber)
        
        # Should be negative (outside the timber)
        assert distance == Rational(-3)
    
    def test_project_point_on_left_face(self):
        """Test projection onto LEFT face"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 10),
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # LEFT face is at x=-5
        # Point at x=-2 (3 units inside from LEFT face)
        point = create_v3(-2, 0, 50)
        distance = project_point_onto_face_global(point, TimberFace.LEFT, timber)
        
        # Should be positive (inside the timber from LEFT face)
        assert distance == Rational(3)
    
    def test_project_point_on_front_face(self):
        """Test projection onto FRONT face"""
        timber = timber_from_directions(
            length=Rational(100),
            size=create_v2(10, 20),  # 10" wide (X), 20" height (Y)
            bottom_position=create_v3(0, 0, 0),
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # FRONT face is at y=10
        # Point at y=5 (5 units inside from FRONT face)
        point = create_v3(0, 5, 50)
        distance = project_point_onto_face_global(point, TimberFace.FRONT, timber)
        
        # Should be positive (inside the timber from FRONT face)
        assert distance == Rational(5)
    
    def test_project_point_with_offset_timber(self):
        """Test projection on a timber not centered at origin"""
        timber = timber_from_directions(
            length=Rational(48),
            size=create_v2(6, 6),
            bottom_position=create_v3(10, 20, 5),  # Offset position
            length_direction=create_v3(0, 0, 1),
            width_direction=create_v3(1, 0, 0)
        )
        
        # RIGHT face is at x=10+3=13
        # Point at x=11 (2 units inside from RIGHT face)
        point = create_v3(11, 20, 20)
        distance = project_point_onto_face_global(point, TimberFace.RIGHT, timber)
        
        # Should be positive (inside the timber)
        assert distance == Rational(2)
