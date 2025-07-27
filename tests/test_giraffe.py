"""
Tests for giraffe.py module.

This module contains tests for the GiraffeCAD timber framing CAD system.
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs
from moothymoth import Orientation
from giraffe import *
from giraffe import _timber_face_to_vector


class TestVectorHelpers:
    """Test vector helper functions."""
    
    def test_create_vector2d(self):
        """Test 2D vector creation."""
        v = create_vector2d(1.5, 2.5)
        assert v.shape == (2, 1)
        assert float(v[0]) == 1.5
        assert float(v[1]) == 2.5
    
    def test_create_vector3d(self):
        """Test 3D vector creation."""
        v = create_vector3d(1.0, 2.0, 3.0)
        assert v.shape == (3, 1)
        assert float(v[0]) == 1.0
        assert float(v[1]) == 2.0
        assert float(v[2]) == 3.0
    
    def test_normalize_vector(self):
        """Test vector normalization."""
        v = create_vector3d(3.0, 4.0, 0.0)
        normalized = normalize_vector(v)
        
        # Should have magnitude 1
        magnitude = vector_magnitude(normalized)
        assert abs(magnitude - 1.0) < 1e-10
        
        # Should preserve direction ratios
        assert abs(float(normalized[0]) - 0.6) < 1e-10  # 3/5
        assert abs(float(normalized[1]) - 0.8) < 1e-10  # 4/5
        assert abs(float(normalized[2])) < 1e-10
    
    def test_normalize_zero_vector(self):
        """Test normalization of zero vector."""
        v = create_vector3d(0.0, 0.0, 0.0)
        normalized = normalize_vector(v)
        assert normalized == v  # Should return original zero vector
    
    def test_cross_product(self):
        """Test cross product calculation."""
        v1 = create_vector3d(1.0, 0.0, 0.0)
        v2 = create_vector3d(0.0, 1.0, 0.0)
        cross = cross_product(v1, v2)
        
        expected = create_vector3d(0.0, 0.0, 1.0)
        assert float(cross[0]) == 0.0
        assert float(cross[1]) == 0.0
        assert float(cross[2]) == 1.0
    
    def test_vector_magnitude(self):
        """Test vector magnitude calculation."""
        v = create_vector3d(3.0, 4.0, 0.0)
        magnitude = vector_magnitude(v)
        assert abs(magnitude - 5.0) < 1e-10


class TestFootprint:
    """Test Footprint class."""
    
    def test_footprint_creation(self):
        """Test basic footprint creation."""
        boundary = [
            create_vector2d(0.0, 0.0),
            create_vector2d(1.0, 0.0),
            create_vector2d(1.0, 1.0),
            create_vector2d(0.0, 1.0)
        ]
        footprint = Footprint(boundary)
        
        assert len(footprint.boundary) == 4
        assert footprint.boundary[0][0] == 0.0
        assert footprint.boundary[0][1] == 0.0
    
    def test_footprint_boundary(self):
        """Test FootprintBoundary creation."""
        boundary = FootprintBoundary(0)
        assert boundary.start_index == 0


class TestTimber:
    """Test Timber class."""
    
    def test_timber_creation(self):
        """Test basic timber creation."""
        length = 3.0
        size = create_vector2d(0.1, 0.1)
        position = create_vector3d(0.0, 0.0, 0.0)
        length_dir = create_vector3d(0.0, 0.0, 1.0)
        face_dir = create_vector3d(1.0, 0.0, 0.0)
        
        timber = Timber(length, size, position, length_dir, face_dir)
        
        assert timber.length == 3.0
        assert timber.size.shape == (2, 1)
        assert timber.bottom_position.shape == (3, 1)
        assert isinstance(timber.orientation, Orientation)
    
    def test_timber_orientation_computation(self):
        """Test that timber orientation is computed correctly."""
        # Create vertical timber facing east
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),  # Up
            face_direction=create_vector3d(1.0, 0.0, 0.0)     # East
        )
        
        # Check that orientation matrix is reasonable
        matrix = timber.orientation.matrix
        assert matrix.shape == (3, 3)
        
        # Check that it's a valid rotation matrix (determinant = 1)
        det_val = float(simplify(matrix.det()))
        assert abs(det_val - 1.0) < 1e-10
    
    def test_get_transform_matrix(self):
        """Test 4x4 transformation matrix generation."""
        timber = Timber(
            length=1.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(1.0, 2.0, 3.0),
            length_direction=create_vector3d(0.0, 0.0, 1.0),
            face_direction=create_vector3d(1.0, 0.0, 0.0)
        )
        
        transform = timber.get_transform_matrix()
        assert transform.shape == (4, 4)
        
        # Check translation part
        assert float(transform[0, 3]) == 1.0
        assert float(transform[1, 3]) == 2.0
        assert float(transform[2, 3]) == 3.0
        assert float(transform[3, 3]) == 1.0
    
    def test_orientation_computed_from_directions(self):
        """Test that orientation is correctly computed from input face and length directions."""
        # Test with standard vertical timber facing east
        input_length_dir = create_vector3d(0.0, 0.0, 1.0)  # Up
        input_face_dir = create_vector3d(1.0, 0.0, 0.0)    # East
        
        timber = Timber(
            length=2.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        # Verify that the property getters return the correct normalized directions
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check that returned directions match input (within tolerance)
        assert abs(float(length_dir[0]) - 0.0) < 1e-10
        assert abs(float(length_dir[1]) - 0.0) < 1e-10
        assert abs(float(length_dir[2]) - 1.0) < 1e-10
        
        assert abs(float(face_dir[0]) - 1.0) < 1e-10
        assert abs(float(face_dir[1]) - 0.0) < 1e-10
        assert abs(float(face_dir[2]) - 0.0) < 1e-10
        
        # Height direction should be cross product of length x face = Z x X = Y
        assert abs(float(height_dir[0]) - 0.0) < 1e-10
        assert abs(float(height_dir[1]) - 1.0) < 1e-10
        assert abs(float(height_dir[2]) - 0.0) < 1e-10
    
    def test_orientation_with_horizontal_timber(self):
        """Test orientation computation with a horizontal timber."""
        # Horizontal timber running north, facing up
        input_length_dir = create_vector3d(0.0, 1.0, 0.0)  # North
        input_face_dir = create_vector3d(0.0, 0.0, 1.0)    # Up
        
        timber = Timber(
            length=3.0,
            size=create_vector2d(0.1, 0.1),
            bottom_position=create_vector3d(0.0, 0.0, 0.0),
            length_direction=input_length_dir,
            face_direction=input_face_dir
        )
        
        length_dir = timber.length_direction
        face_dir = timber.face_direction
        height_dir = timber.height_direction
        
        # Check length direction (north)
        assert abs(float(length_dir[0]) - 0.0) < 1e-10
        assert abs(float(length_dir[1]) - 1.0) < 1e-10
        assert abs(float(length_dir[2]) - 0.0) < 1e-10
        
        # Check face direction (up)
        assert abs(float(face_dir[0]) - 0.0) < 1e-10
        assert abs(float(face_dir[1]) - 0.0) < 1e-10
        assert abs(float(face_dir[2]) - 1.0) < 1e-10
        
        # Height direction should be Y x Z = +X (east)
        assert abs(float(height_dir[0]) - 1.0) < 1e-10
        assert abs(float(height_dir[1]) - 0.0) < 1e-10
        assert abs(float(height_dir[2]) - 0.0) < 1e-10
    
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
        assert abs(float(length_dir[0]) - 0.0) < 1e-10
        assert abs(float(length_dir[1]) - 0.0) < 1e-10
        assert abs(float(length_dir[2]) - 1.0) < 1e-10
        
        assert abs(float(face_dir[0]) - 1.0) < 1e-10
        assert abs(float(face_dir[1]) - 0.0) < 1e-10
        assert abs(float(face_dir[2]) - 0.0) < 1e-10
    
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
        assert abs(float(pos_at_bottom[0]) - 1.0) < 1e-10
        assert abs(float(pos_at_bottom[1]) - 2.0) < 1e-10
        assert abs(float(pos_at_bottom[2]) - 3.0) < 1e-10
        
        # Test at midpoint (position = 2.5)
        pos_at_middle = timber.get_position_on_timber(2.5)
        assert abs(float(pos_at_middle[0]) - 1.0) < 1e-10
        assert abs(float(pos_at_middle[1]) - 4.5) < 1e-10  # 2.0 + 2.5 * 1.0
        assert abs(float(pos_at_middle[2]) - 3.0) < 1e-10
        
        # Test at top (position = 5.0)
        pos_at_top = timber.get_position_on_timber(5.0)
        assert abs(float(pos_at_top[0]) - 1.0) < 1e-10
        assert abs(float(pos_at_top[1]) - 7.0) < 1e-10  # 2.0 + 5.0 * 1.0
        assert abs(float(pos_at_top[2]) - 3.0) < 1e-10
        
        # Test with negative position (beyond bottom)
        pos_neg = timber.get_position_on_timber(-1.0)
        assert abs(float(pos_neg[0]) - 1.0) < 1e-10
        assert abs(float(pos_neg[1]) - 1.0) < 1e-10  # 2.0 + (-1.0) * 1.0
        assert abs(float(pos_neg[2]) - 3.0) < 1e-10


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
        position = create_vector3d(0.0, 0.0, 0.0)
        size = create_vector2d(0.1, 0.1)
        
        timber = create_axis_aligned_timber(
            position, 3.0, size, 
            TimberFace.TOP,    # Length direction (up)
            TimberFace.RIGHT   # Face direction (east)
        )
        
        assert timber.length == 3.0
        # Check that directions are correct
        assert abs(float(timber.length_direction[2]) - 1.0) < 1e-10  # Up
        assert abs(float(timber.face_direction[0]) - 1.0) < 1e-10    # East
    
    def test_create_vertical_timber_on_footprint(self):
        """Test vertical timber creation on footprint."""
        boundary = [
            create_vector2d(0.0, 0.0),
            create_vector2d(3.0, 0.0),
            create_vector2d(3.0, 4.0),
            create_vector2d(0.0, 4.0)
        ]
        footprint = Footprint(boundary)
        
        timber = create_vertical_timber_on_footprint(footprint, 0, 2.5)
        
        assert timber.length == 2.5
        # Should be at footprint point 0
        assert float(timber.bottom_position[0]) == 0.0
        assert float(timber.bottom_position[1]) == 0.0
        assert float(timber.bottom_position[2]) == 0.0
        # Should be vertical
        assert abs(float(timber.length_direction[2]) - 1.0) < 1e-10
    
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
        assert abs(float(timber.length_direction[0]) - 1.0) < 1e-10
        assert abs(float(timber.length_direction[2])) < 1e-10
    
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
            offset_from_timber1=0.0
        )
        
        assert isinstance(joining_timber, Timber)
        # Should be approximately horizontal
        assert abs(float(joining_timber.length_direction[2])) < 0.1

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
