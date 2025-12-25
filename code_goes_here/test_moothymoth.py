"""
Tests for moothymoth.py module.

This module contains tests for the Orientation class which represents
3D rotations using sympy matrices.
"""

import pytest
import math
from sympy import Matrix, pi, simplify, Abs, eye, det
from code_goes_here.moothymoth import Orientation
import random


def generate_random_orientation() -> Orientation:
    """
    Generate a random valid rotation matrix as an Orientation.
    
    Uses the method of generating random unit quaternions and converting
    to rotation matrix to ensure we get valid rotation matrices.
    
    Returns:
        Orientation: A randomly oriented Orientation object
    """
    # Generate random unit quaternion (Shepperd's method)
    u1, u2, u3 = [random.random() for _ in range(3)]
    
    # Convert to unit quaternion components
    q0 = math.sqrt(1 - u1) * math.sin(2 * math.pi * u2)
    q1 = math.sqrt(1 - u1) * math.cos(2 * math.pi * u2)
    q2 = math.sqrt(u1) * math.sin(2 * math.pi * u3)
    q3 = math.sqrt(u1) * math.cos(2 * math.pi * u3)
    
    # Convert quaternion to rotation matrix
    matrix = [
        [1 - 2*(q2**2 + q3**2), 2*(q1*q2 - q0*q3), 2*(q1*q3 + q0*q2)],
        [2*(q1*q2 + q0*q3), 1 - 2*(q1**2 + q3**2), 2*(q2*q3 - q0*q1)],
        [2*(q1*q3 - q0*q2), 2*(q2*q3 + q0*q1), 1 - 2*(q1**2 + q2**2)]
    ]
    
    return Orientation(matrix)


class TestOrientation:
    """Test cases for the Orientation class."""
    
    def test_init_default(self):
        """Test default initialization creates identity matrix."""
        orientation = Orientation()
        expected = Matrix.eye(3)
        assert orientation.matrix == expected
    
    def test_init_with_matrix(self):
        """Test initialization with a custom matrix."""
        matrix = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        orientation = Orientation(matrix)
        assert orientation.matrix == Matrix(matrix)
    
    def test_init_invalid_shape(self):
        """Test initialization with invalid matrix shape raises error."""
        with pytest.raises(ValueError, match="Rotation matrix must be 3x3"):
            Orientation([[1, 0], [0, 1]])
    
    def test_multiply_basic(self):
        """Test basic multiplication of orientations."""
        orient1 = Orientation.rotate_left()  # 90° CCW around Z
        orient2 = Orientation.rotate_left()  # Another 90° CCW around Z
        result = orient1.multiply(orient2)
        
        # Two 90° rotations should equal 180° rotation (left * left = backward)
        expected = Orientation.left()  # 180° rotation
        assert simplify(result.matrix - expected.matrix).norm() < 1e-10
    
    def test_multiply_operator(self):
        """Test multiplication using * operator."""
        orient1 = Orientation.rotate_right()
        orient2 = Orientation.rotate_right()
        result1 = orient1 * orient2
        result2 = orient1.multiply(orient2)
        assert result1.matrix == result2.matrix
    
    def test_multiply_type_error(self):
        """Test multiplication with non-Orientation raises error."""
        orientation = Orientation.identity()
        with pytest.raises(TypeError, match="Can only multiply with another Orientation"):
            orientation.multiply("not an orientation")
    
    def test_invert_basic(self):
        """Test basic inversion of orientations."""
        orientation = Orientation.rotate_left()
        inverted = orientation.invert()
        
        # Left rotation inverted should be right rotation
        expected = Orientation.rotate_right()
        assert simplify(inverted.matrix - expected.matrix).norm() < 1e-10
    
    def test_invert_identity_property(self):
        """Test that orientation * invert = identity."""
        for _ in range(5):  # Test with multiple random orientations
            orientation = generate_random_orientation()
            inverted = orientation.invert()
            result = orientation * inverted
            
            # Should be very close to identity
            identity = Matrix.eye(3)
            diff = simplify(result.matrix - identity)
            assert float(diff.norm()) < 1e-10
    
    def test_invert_double_invert(self):
        """Test that double inversion returns original."""
        orientation = generate_random_orientation()
        double_inverted = orientation.invert().invert()
        
        diff = simplify(orientation.matrix - double_inverted.matrix)
        assert float(diff.norm()) < 1e-10


class TestOrientationConstants:
    """Test the static orientation constants."""
    
    def test_identity_is_eye(self):
        """Test identity constant is 3x3 identity matrix."""
        assert Orientation.identity().matrix == Matrix.eye(3)
    
    def test_directional_constants_exist(self):
        """Test all directional constants can be accessed."""
        constants = ['identity', 'right', 'east', 'left', 'west', 
                    'forward', 'north', 'backward', 'south', 'up', 'down']
        
        for const_name in constants:
            orientation = getattr(Orientation, const_name)()
            assert isinstance(orientation, Orientation)
            assert orientation.matrix.shape == (3, 3)
    
    def test_east_west_self_inverses(self):
        """Test east and west orientations are self-inverses."""
        east = Orientation.east()
        west = Orientation.west()
        identity = Matrix.eye(3)
        
        # East is identity, so east * east = identity
        result_east = east * east
        assert simplify(result_east.matrix - identity).norm() < 1e-10
        
        # West is 180° rotation, so west * west = identity  
        result_west = west * west
        assert simplify(result_west.matrix - identity).norm() < 1e-10
    
    def test_north_south_are_inverses(self):
        """Test north and south orientations are inverses."""
        north = Orientation.north()
        south = Orientation.south()
        
        result = north * south
        identity = Matrix.eye(3)
        assert simplify(result.matrix - identity).norm() < 1e-10
    
    def test_up_down_are_inverses(self):
        """Test up and down orientations are inverses."""
        up = Orientation.up()
        down = Orientation.down()
        
        result = up * down
        identity = Matrix.eye(3)
        assert simplify(result.matrix - identity).norm() < 1e-10
    
    def test_rotate_left_right_are_inverses(self):
        """Test rotate_left and rotate_right are inverses."""
        left = Orientation.rotate_left()
        right = Orientation.rotate_right()
        
        result = left * right
        identity = Matrix.eye(3)
        assert simplify(result.matrix - identity).norm() < 1e-10


class TestEulerAngles:
    """Test Euler angle functionality."""
    
    def test_from_euleryZYX_zero_angles(self):
        """Test from_euleryZYX with zero angles gives identity."""
        orientation = Orientation.from_euleryZYX(0, 0, 0)
        expected = Matrix.eye(3)
        assert simplify(orientation.matrix - expected).norm() < 1e-10
    
    def test_from_euleryZYX_yaw_only(self):
        """Test from_euleryZYX with only yaw rotation."""
        # 90° yaw should match rotate_left
        orientation = Orientation.from_euleryZYX(pi/2, 0, 0)
        expected = Orientation.rotate_left().matrix
        assert simplify(orientation.matrix - expected).norm() < 1e-10
    
    def test_from_euleryZYX_pitch_only(self):
        """Test from_euleryZYX with only pitch rotation."""
        orientation = Orientation.from_euleryZYX(0, pi/2, 0)
        
        # Verify it's a valid rotation matrix
        matrix = orientation.matrix
        # Check determinant is 1
        assert simplify(det(matrix)) == 1
        
        # Check orthogonality: R * R^T = I
        should_be_identity = simplify(matrix * matrix.T)
        identity = Matrix.eye(3)
        assert should_be_identity == identity
    
    def test_from_euleryZYX_roll_only(self):
        """Test from_euleryZYX with only roll rotation."""
        orientation = Orientation.from_euleryZYX(0, 0, pi/2)
        
        # Verify it's a valid rotation matrix
        matrix = orientation.matrix
        assert simplify(det(matrix)) == 1


class TestRotationMatrixProperties:
    """Test mathematical properties of rotation matrices."""
    
    def test_determinant_is_one(self):
        """Test all orientation matrices have determinant 1."""
        orientations = [
            Orientation.identity(), Orientation.north(), Orientation.up(),
            Orientation.rotate_left(), generate_random_orientation()
        ]
        
        for orientation in orientations:
            det_val = float(simplify(det(orientation.matrix)))
            assert abs(det_val - 1.0) < 1e-10
    
    def test_orthogonality(self):
        """Test all orientation matrices are orthogonal (R * R^T = I)."""
        for _ in range(3):  # Test with random orientations
            orientation = generate_random_orientation()
            matrix = orientation.matrix
            
            product = simplify(matrix * matrix.T)
            identity = Matrix.eye(3)
            
            diff_norm = float((product - identity).norm())
            assert diff_norm < 1e-10
    
    def test_inverse_equals_transpose(self):
        """Test that inverse equals transpose for rotation matrices."""
        orientation = generate_random_orientation()
        
        inverse_matrix = orientation.invert().matrix
        transpose_matrix = orientation.matrix.T
        
        diff = simplify(inverse_matrix - transpose_matrix)
        assert float(diff.norm()) < 1e-10


class TestReprAndString:
    """Test string representation."""
    
    def test_repr_contains_matrix(self):
        """Test __repr__ contains the matrix."""
        orientation = Orientation.identity()
        repr_str = repr(orientation)
        
        assert "Orientation(" in repr_str
        assert "Matrix(" in repr_str
        assert "1" in repr_str  # Should contain identity matrix elements 