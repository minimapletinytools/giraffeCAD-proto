"""
Tests for giraffe.py module.

This module contains tests for the GiraffeCAD timber framing CAD system.
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs, Float, Rational
from moothymoth import Orientation
from giraffe import *
from giraffe import _timber_face_to_vector


class TestVectorHelpers:
    """Test vector helper functions."""
    
    def test_create_vector2d(self):
        """Test 2D vector creation."""
        v = create_vector2d(Rational(3, 2), Rational(5, 2))  # 1.5, 2.5 as exact rationals
        assert v.shape == (2, 1)
        assert v[0] == Rational(3, 2)
        assert v[1] == Rational(5, 2)
    
    def test_create_vector3d(self):
        """Test 3D vector creation."""
        v = create_vector3d(1, 2, 3)  # Use exact integers
        assert v.shape == (3, 1)
        assert v[0] == 1
        assert v[1] == 2
        assert v[2] == 3
    
    def test_normalize_vector(self):
        """Test vector normalization."""
        v = create_vector3d(3, 4, 0)  # Use integers for exact computation
        normalized = normalize_vector(v)
        
        # Should have magnitude 1
        magnitude = vector_magnitude(normalized)
        assert magnitude == 1
        
        # Should preserve direction ratios exactly
        assert normalized[0] == Rational(3, 5)  # 3/5
        assert normalized[1] == Rational(4, 5)  # 4/5
        assert normalized[2] == 0
    
    def test_normalize_zero_vector(self):
        """Test normalization of zero vector."""
        v = create_vector3d(0, 0, 0)  # Use exact integers
        normalized = normalize_vector(v)
        assert normalized == v  # Should return original zero vector
    
    def test_cross_product(self):
        """Test cross product calculation."""
        v1 = create_vector3d(1, 0, 0)  # Use exact integers
        v2 = create_vector3d(0, 1, 0)  # Use exact integers
        cross = cross_product(v1, v2)
        
        expected = create_vector3d(0, 0, 1)  # Use exact integers
        assert cross[0] == 0
        assert cross[1] == 0
        assert cross[2] == 1
    
    def test_vector_magnitude(self):
        """Test vector magnitude calculation."""
        v = create_vector3d(3, 4, 0)  # Use integers for exact computation
        magnitude = vector_magnitude(v)
        assert magnitude == 5


class TestFootprint:
    """Test Footprint class."""
    
    def test_footprint_creation(self):
        """Test basic footprint creation."""
        boundary = [
            create_vector2d(0, 0),  # Use exact integers
            create_vector2d(1, 0),  # Use exact integers
            create_vector2d(1, 1),  # Use exact integers
            create_vector2d(0, 1)   # Use exact integers
        ]
        footprint = Footprint(boundary)
        
        assert len(footprint.boundary) == 4
        assert footprint.boundary[0][0] == 0
        assert footprint.boundary[0][1] == 0
    
    def test_footprint_boundary(self):
        """Test FootprintBoundary creation."""
        boundary = FootprintBoundary(0)
        assert boundary.start_index == 0


class TestTimber:
    """Test Timber class."""
    
    def test_timber_creation(self):
        """Test basic timber creation."""
        length = 3  # Use exact integer
        size = create_vector2d(Rational(1, 10), Rational(1, 10))  # 0.1 as exact rational
        position = create_vector3d(0, 0, 0)  # Use exact integers
        length_dir = create_vector3d(0, 0, 1)  # Use exact integers
        face_dir = create_vector3d(1, 0, 0)   # Use exact integers
        
        timber = Timber(length, size, position, length_dir, face_dir)
        
        assert timber.length == 3
        assert timber.size.shape == (2, 1)
        assert timber.bottom_position.shape == (3, 1)
        assert isinstance(timber.orientation, Orientation)
    
    def test_timber_orientation_computation(self):
        """Test that timber orientation is computed correctly."""
        # Create vertical timber facing east
        timber = Timber(
            length=2,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=create_vector3d(0, 0, 1),  # Up - exact integers
            face_direction=create_vector3d(1, 0, 0)     # East - exact integers
        )
        
        # Check that orientation matrix is reasonable
        matrix = timber.orientation.matrix
        assert matrix.shape == (3, 3)
        
        # Check that it's a valid rotation matrix (determinant = 1) - keep epsilon as float
        det_val = float(simplify(matrix.det()))
        assert abs(det_val - 1.0) < 1e-10
    
    def test_get_transform_matrix(self):
        """Test 4x4 transformation matrix generation."""
        timber = Timber(
            length=1,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(1, 2, 3),  # Use exact integers
            length_direction=create_vector3d(0, 0, 1), # Use exact integers
            face_direction=create_vector3d(1, 0, 0)    # Use exact integers
        )
        
        transform = timber.get_transform_matrix()
        assert transform.shape == (4, 4)
        
        # Check translation part (exact comparison since we used integers)
        assert transform[0, 3] == 1
        assert transform[1, 3] == 2
        assert transform[2, 3] == 3
        assert transform[3, 3] == 1
    
    def test_orientation_computed_from_directions(self):
        """Test that orientation is correctly computed from input face and length directions."""
        # Test with standard vertical timber facing east
        input_length_dir = create_vector3d(0, 0, 1)  # Up - exact integers
        input_face_dir = create_vector3d(1, 0, 0)    # East - exact integers
        
        timber = Timber(
            length=2,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        # Verify that the property getters return the correct normalized directions
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check that returned directions match input exactly (exact integers now)
        assert length_dir[0] == 0
        assert length_dir[1] == 0
        assert length_dir[2] == 1  # Exact integer from input
        
        assert face_dir[0] == 1    # Exact integer from input
        assert face_dir[1] == 0
        assert face_dir[2] == 0
        
        # Height direction should be cross product of length x face = Z x X = Y
        assert height_dir[0] == 0
        assert height_dir[1] == 1  # Exact integer from calculation
        assert height_dir[2] == 0
    
    def test_orientation_with_horizontal_timber(self):
        """Test orientation computation with a horizontal timber."""
        # Horizontal timber running north, facing up
        input_length_dir = create_vector3d(0, 1, 0)  # North - exact integers
        input_face_dir = create_vector3d(0, 0, 1)    # Up - exact integers
        
        timber = Timber(
            length=3,  # Use exact integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # 0.1 as exact rational
            bottom_position=create_vector3d(0, 0, 0),  # Use exact integers
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check length direction (north) - exact integers now
        assert length_dir[0] == 0
        assert length_dir[1] == 1
        assert length_dir[2] == 0
        
        # Check face direction (up) - exact integers now
        assert face_dir[0] == 0
        assert face_dir[1] == 0
        assert face_dir[2] == 1
        
        # Height direction should be Y x Z = +X (east) - exact integers now
        assert height_dir[0] == 1
        assert height_dir[1] == 0
        assert height_dir[2] == 0
    
    def test_orientation_directions_are_orthonormal(self):
        """Test that the computed direction vectors form an orthonormal basis."""
        timber = Timber(
            length=1.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 1.0, 0.0),  # Non-axis-aligned
            face_direction=create_vector3d(0.0, 0.0, 1.0)     # Up
        )
        
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check that each vector has unit length
        length_mag = float(sqrt(sum(x**2 for x in length_dir)))
        face_mag = float(sqrt(sum(x**2 for x in face_dir)))
        height_mag = float(sqrt(sum(x**2 for x in height_dir)))
        
        assert abs(length_mag - 1.0) < 1e-10
        assert abs(face_mag - 1.0) < 1e-10
        assert abs(height_mag - 1.0) < 1e-10
        
        # Check that vectors are orthogonal (dot products = 0)
        length_face_dot = float(sum(length_dir[i] * face_dir[i] for i in range(3)))
        length_height_dot = float(sum(length_dir[i] * height_dir[i] for i in range(3)))
        face_height_dot = float(sum(face_dir[i] * height_dir[i] for i in range(3)))
        
        assert abs(length_face_dot) < 1e-10
        assert abs(length_height_dot) < 1e-10
        assert abs(face_height_dot) < 1e-10
    
    def test_orientation_handles_non_normalized_inputs(self):
        """Test that orientation computation works with non-normalized input vectors."""
        # Use vectors that aren't unit length
        input_length_dir = create_vector3d(0.0, 0.0, 5.0)  # Up, but length 5
        input_face_dir = create_vector3d(3.0, 0.0, 0.0)    # East, but length 3
        
        timber = Timber(
            length=1.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        # Despite non-normalized inputs, the output should be normalized
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        
        # Check that directions are normalized
        assert length_dir[0] == 0
        assert length_dir[1] == 0
        assert length_dir[2] == Float('1.0')
        
        assert face_dir[0] == Float('1.0')
        assert face_dir[1] == 0
        assert face_dir[2] == 0
    
    def test_get_position_on_timber(self):
        """Test the get_position_on_timber method."""
        timber = Timber(
            length=5.0,
            size=create_vector2d(0.2, 0.3),
            bottom_position=create_vector3d(1.0, 2.0, 3.0),
            length_direction=create_vector3d(0.0, 1.0, 0.0),  # North
            face_direction=create_vector3d(0.0, 0.0, 1.0)     # Up
        )
        
        # Test at bottom position (position = 0)
        pos_at_bottom = timber.get_position_on_timber(0.0)
        assert pos_at_bottom[0] == Float('1.0')
        assert pos_at_bottom[1] == Float('2.0')
        assert pos_at_bottom[2] == Float('3.0')
        
        # Test at midpoint (position = 2.5)
        pos_at_middle = timber.get_position_on_timber(2.5)
        assert pos_at_middle[0] == Float('1.0')
        assert pos_at_middle[1] == Float('4.5')  # 2.0 + 2.5 * 1.0
        assert pos_at_middle[2] == Float('3.0')
        
        # Test at top (position = 5.0)
        pos_at_top = timber.get_position_on_timber(5.0)
        assert pos_at_top[0] == Float('1.0')
        assert pos_at_top[1] == Float('7.0')  # 2.0 + 5.0 * 1.0
        assert pos_at_top[2] == Float('3.0')
        
        # Test with negative position (beyond bottom)
        pos_neg = timber.get_position_on_timber(-1.0)
        assert pos_neg[0] == Float('1.0')
        assert pos_neg[1] == Float('1.0')  # 2.0 + (-1.0) * 1.0
        assert pos_neg[2] == Float('3.0')


class TestTimberCreation:
    """Test timber creation functions."""
    
    def test_create_timber(self):
        """Test basic create_timber function."""
        position = create_vector3d(1.0, 1.0, 0.0)
        size = create_vector2d(0.2, 0.3)
        length_dir = create_vector3d(0.0, 0.0, 1.0)
        face_dir = create_vector3d(1.0, 0.0, 0.0)
        
        timber = create_timber(position, 2.5, size, length_dir, face_dir)
        
        assert timber.length == 2.5
        assert float(timber.bottom_position[0]) == 1.0
        assert float(timber.bottom_position[1]) == 1.0
        assert float(timber.bottom_position[2]) == 0.0
    
    def test_create_axis_aligned_timber(self):
        """Test axis-aligned timber creation."""
        position = create_vector3d(0, 0, 0)  # Use exact integers
        size = create_vector2d(Rational(1, 10), Rational(1, 10))  # 0.1 as exact rational
        
        timber = create_axis_aligned_timber(
            position, 3, size,  # Use exact integer for length
            TimberFace.TOP,    # Length direction (up)
            TimberFace.RIGHT   # Face direction (east)
        )
        
        assert timber.length == 3  # Exact integer
        # Check that directions are correct
        assert timber.length_direction[2] == 1  # Up (exact integer)
        assert timber.face_direction[0] == 1    # East (exact integer)
    
    def test_create_vertical_timber_on_footprint(self):
        """Test vertical timber creation on footprint."""
        boundary = [
            create_vector2d(0, 0),  # Use exact integers
            create_vector2d(3, 0),  # Use exact integers
            create_vector2d(3, 4),  # Use exact integers
            create_vector2d(0, 4)   # Use exact integers
        ]
        footprint = Footprint(boundary)
        
        timber = create_vertical_timber_on_footprint(footprint, 0, Rational(5, 2))  # 2.5 as exact rational
        
        assert timber.length == Rational(5, 2)  # Exact rational
        # Should be at footprint point 0
        assert timber.bottom_position[0] == Float('0.0')  # Keep as Float since footprint uses floats internally
        assert timber.bottom_position[1] == Float('0.0')  # Keep as Float since footprint uses floats internally
        assert timber.bottom_position[2] == 0  # Exact integer
        # Should be vertical
        assert timber.length_direction[2] == 1  # Exact integer
    
    def test_create_horizontal_timber_on_footprint(self):
        """Test horizontal timber creation on footprint."""
        boundary = [
            create_vector2d(0.0, 0.0),
            create_vector2d(3.0, 0.0),
            create_vector2d(3.0, 4.0),
            create_vector2d(0.0, 4.0)
        ]
        footprint = Footprint(boundary)
        
        timber = create_axis_aligned_horizontal_timber_on_footprint(
            footprint, 0, 3.0, TimberLocationType.INSIDE
        )
        
        assert timber.length == 3.0
        # Should be horizontal in X direction
        assert timber.length_direction[0] == Float('1.0')
        assert timber.length_direction[2] == 0
    
    def test_create_timber_extension(self):
        """Test timber extension creation."""
        original_timber = Timber(
            length=2.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 1.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        # Extend from top
        extended = create_timber_extension(original_timber, TimberReferenceEnd.TOP, 0.5, 1.0)
        
        assert extended.length == 2.5  # 2.0 + 1.0 - 0.5
        # Bottom position should have moved up
        assert float(extended.bottom_position[2]) == 2.5  # 1.0 + (2.0 - 0.5)


class TestJointConstruction:
    """Test joint construction functions."""
    
    def test_simple_mortise_and_tenon_joint(self):
        """Test simple mortise and tenon joint creation."""
        mortise_timber = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),
            face_direction=create_vector3d(0.0, 1.0, 0.0)
        )
        
        tenon_timber = Timber(
            length=2.0,
            size=create_vector2d(0.15, 0.15),
            bottom_position=create_vector3d(0.0, 0.0, 0.5),
            length_direction=create_vector3d(0.0, 0.0, 1.0),
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        joint = simple_mortise_and_tenon_joint(
            mortise_timber, tenon_timber, 
            tenon_thickness=0.05,
            tenon_length=0.1,
            tenon_depth=0.08
        )
        
        assert isinstance(joint, Joint)
        assert len(joint.timber_cuts) == 2
        # Check that both timbers are included
        timbers = [cut[0] for cut in joint.timber_cuts]
        assert mortise_timber in timbers
        assert tenon_timber in timbers


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_timber_face_to_vector(self):
        """Test TimberFace to vector conversion."""
        # Test all faces
        top = _timber_face_to_vector(TimberFace.TOP)
        assert float(top[2]) == 1.0
        
        bottom = _timber_face_to_vector(TimberFace.BOTTOM)
        assert float(bottom[2]) == -1.0
        
        right = _timber_face_to_vector(TimberFace.RIGHT)
        assert float(right[0]) == 1.0
        
        left = _timber_face_to_vector(TimberFace.LEFT)
        assert float(left[0]) == -1.0
        
        forward = _timber_face_to_vector(TimberFace.FORWARD)
        assert float(forward[1]) == 1.0
        
        back = _timber_face_to_vector(TimberFace.BACK)
        assert float(back[1]) == -1.0


class TestJoinTimbers:
    """Test timber joining functions."""
    
    def test_join_timbers_basic(self):
        """Test basic timber joining."""
        timber1 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),  # Vertical
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        timber2 = Timber(
            length=2.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(2.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),  # Vertical
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=1.5,  # Midpoint of timber1
            symmetric_stickout=0.1,
            offset_from_timber1=0.0,
            location_on_timber2=1.0   # Explicit position on timber2
        )
        
        assert isinstance(joining_timber, Timber)
        # Length direction should be from pos1=[0,0,1.5] to pos2=[2,0,1.0], so direction=[2,0,-0.5]
        # Normalized: [0.970, 0, -0.243] approximately
        length_dir = joining_timber.length_direction
        assert abs(float(length_dir[0]) - 0.970) < 0.1  # X component ~0.97
        assert abs(float(length_dir[1])) < 0.1          # Y component ~0
        assert abs(float(length_dir[2]) + 0.243) < 0.1  # Z component ~-0.24
        
        # Face direction should be orthogonal to length direction
        # With improved orthogonalization, this should be Y axis [0, 1, 0]
        face_dir = joining_timber.face_direction
        assert abs(float(face_dir[0])) < 0.1        # X component should be ~0
        assert abs(float(face_dir[1]) - 1.0) < 0.1  # Y component should be ~1
        assert abs(float(face_dir[2])) < 0.1        # Z component should be ~0
        
        # Verify the joining timber is positioned correctly
        # pos1 = [0, 0, 1.5] (location 1.5 on timber1), pos2 = [2, 0, 1.0] (location 1.0 on timber2)
        # center would be [1, 0, 1.25], but bottom_position is at the start of the timber
        # The timber should span from one connection point to the other with stickout
        
        # Check that the timber actually spans the connection points correctly
        # The timber should start before pos1 and end after pos2 (or vice versa)
        timber_start = joining_timber.bottom_position
        timber_end = joining_timber.get_position_on_timber(joining_timber.length)
        
        # Verify timber spans the connection region
        assert float(joining_timber.length) > 2.0  # Should be longer than just the span between points

    # helper function to create 2 parallel timbers 
    def make_parallel_timbers(self):
        timber1 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),  # Horizontal in X
            face_direction=create_vector3d(0.0, 0.0, 1.0)     # Up
        )
        
        timber2 = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 2.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),  # Parallel to timber1
            face_direction=create_vector3d(0.0, 0.0, 1.0)
        )

        return timber1, timber2
    
    def test_join_perpendicular_on_face_aligned_timbers_position_is_correct(self):
        """Test perpendicular joining of face-aligned timbers."""
        timber1, timber2 = self.make_parallel_timbers()
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )

        joining_timber2 = join_perpendicular_on_face_aligned_timbers(
            timber1, timber2,
            location_on_timber1=1.5,
            symmetric_stickout=0,
            offset_from_timber1=offset,
            size=create_vector2d(0.15, 0.15),
            orientation_face_on_timber1=TimberFace.TOP
        )
   
        assert joining_timber2.bottom_position == timber1.get_position_on_timber(1.5)
        print(joining_timber2.orientation)
        
        
    def test_join_perpendicular_on_face_aligned_timbers_length_is_correct(self):
        """Test perpendicular joining of face-aligned timbers."""
        timber1, timber2 = self.make_parallel_timbers()
        
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=None,
            face_offset=None
        )
        
        joining_timber2 = join_perpendicular_on_face_aligned_timbers(
            timber1, timber2,
            location_on_timber1=1.5,
            symmetric_stickout=1.2,
            offset_from_timber1=offset,
            size=create_vector2d(0.15, 0.15),
            orientation_face_on_timber1=TimberFace.TOP
        )
        
        assert isinstance(joining_timber2, Timber)
        # Length should be centerline distance (2.0) + 2 * symmetric_stickout (2 * 1.2 = 2.4) = 4.4
        assert abs(joining_timber2.length - 4.4) < 1e-10

    def test_join_timbers_creates_orthogonal_rotation_matrix(self):
        """Test that join_timbers creates valid orthogonal orientation matrices."""
        # Create two non-parallel timbers to ensure non-trivial orientation
        # Use exact integer/rational inputs for exact SymPy results
        timber1 = Timber(
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            bottom_position=create_vector3d(Rational(-1, 2), 0, 0),  # Exact rationals
            length_direction=create_vector3d(0, 0, 1),  # Integers (vertical)
            face_direction=create_vector3d(1, 0, 0)     # Integers
        )
        
        timber2 = Timber(
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            bottom_position=create_vector3d(Rational(1, 2), 0, 0),   # Exact rationals
            length_direction=create_vector3d(0, 1, 0),  # Integers (horizontal north)
            face_direction=create_vector3d(0, 0, 1)     # Integers
        )
        
        joining_timber = join_timbers(
            timber1, timber2,
            location_on_timber1=Rational(1, 2),     # Exact rational
            symmetric_stickout=Rational(1, 10),     # Exact rational
            offset_from_timber1=0,                  # Integer
            location_on_timber2=Rational(1, 2)     # Exact rational
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
        face_dir = joining_timber.face_direction  
        height_dir = joining_timber.height_direction
        
        assert simplify(length_dir.norm() - 1) == 0, "Length direction should be unit vector"
        assert simplify(face_dir.norm() - 1) == 0, "Face direction should be unit vector"
        assert simplify(height_dir.norm() - 1) == 0, "Height direction should be unit vector"
        
        # Verify directions are orthogonal to each other (exact SymPy comparison)
        assert simplify(length_dir.dot(face_dir)) == 0, "Length and face directions should be orthogonal"
        assert simplify(length_dir.dot(height_dir)) == 0, "Length and height directions should be orthogonal"
        assert simplify(face_dir.dot(height_dir)) == 0, "Face and height directions should be orthogonal"

    def test_create_timber_creates_orthogonal_matrix(self):
        """Test that create_timber creates valid orthogonal orientation matrices."""
        # Test with arbitrary (but orthogonal) input directions using exact inputs
        length_dir = create_vector3d(1, 1, 0)  # Will be normalized (integers)
        face_dir = create_vector3d(0, 0, 1)    # Up direction (integers)
        
        timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            length_direction=length_dir,
            face_direction=face_dir
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
        length_dir = create_vector3d(2, 0, 1)         # Not orthogonal to face_dir (integers)
        face_dir = create_vector3d(0, 1, 2)           # Not orthogonal to length_dir (integers)
        
        timber = create_timber(
            bottom_position=create_vector3d(0, 0, 0),  # Integers
            length=1,  # Integer
            size=create_vector2d(Rational(1, 10), Rational(1, 10)),  # Exact rationals
            length_direction=length_dir,
            face_direction=face_dir
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


class TestTimberCutOperations:
    """Test timber cut operations."""
    
    def test_tenon_cut_operation(self):
        """Test tenon cut operation creation."""
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        tenon_spec = StandardTenon(
            shoulder_plane=OrientedShoulderPlane(
                direction=TimberReferenceEnd.TOP,
                distance=0.05,
                orientation=Orientation.identity()
            ),
            pos_rel_to_long_edge=None,
            width=0.04,
            height=0.04,
            depth=0.06
        )
        
        cut_op = TenonCutOperation(timber, tenon_spec)
        
        assert cut_op.timber == timber
        assert cut_op.tenon_spec.width == 0.04
    
    def test_mortise_cut_operation(self):
        """Test mortise cut operation creation."""
        timber = Timber(
            length=3.0,
            size=create_vector2d(0.2, 0.2),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(1.0, 0.0, 0.0),
            face_direction=create_vector3d(0.0, 1.0, 0.0)
        )
        
        mortise_spec = StandardMortise(
            mortise_face=TimberFace.TOP,
            pos_rel_to_end=(TimberReferenceEnd.BOTTOM, 0.5),
            pos_rel_to_long_face=(TimberReferenceLongFace.RIGHT, 0.1),
            width=0.04,
            height=0.06,
            depth=0.08
        )
        
        cut_op = MortiseCutOperation(timber, mortise_spec)
        
        assert cut_op.timber == timber
        assert cut_op.mortise_spec.width == 0.04


class TestEnumsAndDataStructures:
    """Test enums and data structures."""
    
    def test_timber_location_type_enum(self):
        """Test TimberLocationType enum."""
        assert TimberLocationType.INSIDE.value == 1
        assert TimberLocationType.CENTER.value == 2
        assert TimberLocationType.OUTSIDE.value == 3
    
    def test_timber_face_enum(self):
        """Test TimberFace enum."""
        assert TimberFace.TOP.value == 1
        assert TimberFace.BOTTOM.value == 2
        assert TimberFace.RIGHT.value == 3
        assert TimberFace.FORWARD.value == 4
        assert TimberFace.LEFT.value == 5
        assert TimberFace.BACK.value == 6
    
    def test_standard_tenon_dataclass(self):
        """Test StandardTenon dataclass."""
        shoulder_plane = OrientedShoulderPlane(
            direction=TimberReferenceEnd.TOP,
            distance=0.1,
            orientation=Orientation.identity()
        )
        
        tenon = StandardTenon(
            shoulder_plane=shoulder_plane,
            pos_rel_to_long_edge=None,
            width=0.05,
            height=0.05,
            depth=0.08
        )
        
        assert tenon.width == 0.05
        assert tenon.height == 0.05
        assert tenon.depth == 0.08
    
    def test_face_aligned_joined_timber_offset(self):
        """Test FaceAlignedJoinedTimberOffset dataclass."""
        offset = FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.TOP,
            centerline_offset=0.05,
            face_offset=0.02
        )
        
        assert offset.reference_face == TimberFace.TOP
        assert offset.centerline_offset == 0.05
        assert offset.face_offset == 0.02
