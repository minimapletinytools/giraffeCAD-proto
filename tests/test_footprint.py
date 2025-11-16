"""
Tests for footprint.py module.

This module contains tests for the Footprint class in the GiraffeCAD system.
"""

import pytest
from sympy import Matrix
from footprint import Footprint
from giraffe import create_vector2d


class TestFootprint:
    """Test Footprint class."""
    
    def test_footprint_creation(self):
        """Test basic footprint creation."""
        corners = [
            create_vector2d(0, 0),  # Use exact integers
            create_vector2d(1, 0),  # Use exact integers
            create_vector2d(1, 1),  # Use exact integers
            create_vector2d(0, 1)   # Use exact integers
        ]
        footprint = Footprint(corners)
        
        assert len(footprint.corners) == 4
        assert footprint.corners[0][0] == 0
        assert footprint.corners[0][1] == 0
    
    def test_footprint_sides(self):
        """Test sides() method."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(1, 0),
            create_vector2d(1, 1),
            create_vector2d(0, 1)
        ]
        footprint = Footprint(corners)
        
        sides = footprint.sides()
        
        assert len(sides) == 4
        # Check first side
        assert sides[0][0] == corners[0]
        assert sides[0][1] == corners[1]
        # Check last side wraps around
        assert sides[3][0] == corners[3]
        assert sides[3][1] == corners[0]
    
    def test_footprint_isValid_valid_footprint(self):
        """Test isValid() with a valid footprint."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(1, 0),
            create_vector2d(1, 1),
            create_vector2d(0, 1)
        ]
        footprint = Footprint(corners)
        
        assert footprint.isValid() == True
    
    def test_footprint_isValid_too_few_corners(self):
        """Test isValid() with too few corners."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(1, 0)
        ]
        footprint = Footprint(corners)
        
        assert footprint.isValid() == False
    
    def test_footprint_isValid_self_intersecting(self):
        """Test isValid() with self-intersecting sides."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(1, 1),
            create_vector2d(1, 0),
            create_vector2d(0, 1)
        ]
        footprint = Footprint(corners)
        
        assert footprint.isValid() == False
    
    def test_footprint_containsPoint_inside(self):
        """Test containsPoint() with point inside."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(2, 0),
            create_vector2d(2, 2),
            create_vector2d(0, 2)
        ]
        footprint = Footprint(corners)
        
        assert footprint.containsPoint(create_vector2d(1, 1)) == True
    
    def test_footprint_containsPoint_outside(self):
        """Test containsPoint() with point outside."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(2, 0),
            create_vector2d(2, 2),
            create_vector2d(0, 2)
        ]
        footprint = Footprint(corners)
        
        assert footprint.containsPoint(create_vector2d(3, 3)) == False
    
    def test_footprint_nearestCorner(self):
        """Test nearestCorner() method."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(2, 0),
            create_vector2d(2, 2),
            create_vector2d(0, 2)
        ]
        footprint = Footprint(corners)
        
        # Point closest to corner 0
        idx, corner = footprint.nearestCorner(create_vector2d(0.1, 0.1))
        assert idx == 0
        assert corner == corners[0]
        
        # Point closest to corner 2
        idx, corner = footprint.nearestCorner(create_vector2d(1.9, 1.9))
        assert idx == 2
        assert corner == corners[2]
    
    def test_footprint_nearestBoundary(self):
        """Test nearestBoundary() method."""
        corners = [
            create_vector2d(0, 0),
            create_vector2d(2, 0),
            create_vector2d(2, 2),
            create_vector2d(0, 2)
        ]
        footprint = Footprint(corners)
        
        # Point closest to first side (bottom edge)
        idx, side, dist = footprint.nearestBoundary(create_vector2d(1, -0.5))
        assert idx == 0
        assert side == (corners[0], corners[1])
        assert abs(dist - 0.5) < 1e-6
        
        # Point closest to third side (top edge)
        idx, side, dist = footprint.nearestBoundary(create_vector2d(1, 2.5))
        assert idx == 2
        assert side == (corners[2], corners[3])
        assert abs(dist - 0.5) < 1e-6
    
    def test_footprint_getInwardNormal(self):
        """Test getInwardNormal() method with exact arithmetic."""
        # Create a counter-clockwise square footprint using exact integers
        corners = [
            create_vector2d(0, 0),  # Bottom-left - exact integers
            create_vector2d(2, 0),  # Bottom-right - exact integers
            create_vector2d(2, 2),  # Top-right - exact integers
            create_vector2d(0, 2)   # Top-left - exact integers
        ]
        footprint = Footprint(corners)
        
        # Test bottom edge (should point up/inward: y+)
        # For axis-aligned edges, normals may be SymPy types
        nx, ny, nz = footprint.getInwardNormal(0)
        assert float(nx) == 0.0
        assert float(ny) == 1.0
        assert float(nz) == 0.0
        
        # Test right edge (should point left/inward: x-)
        nx, ny, nz = footprint.getInwardNormal(1)
        assert float(nx) == -1.0
        assert float(ny) == 0.0
        assert float(nz) == 0.0
        
        # Test top edge (should point down/inward: y-)
        nx, ny, nz = footprint.getInwardNormal(2)
        assert float(nx) == 0.0
        assert float(ny) == -1.0
        assert float(nz) == 0.0
        
        # Test left edge (should point right/inward: x+)
        nx, ny, nz = footprint.getInwardNormal(3)
        assert float(nx) == 1.0
        assert float(ny) == 0.0
        assert float(nz) == 0.0

