"""
Tests for moothymoth.py module.

This module contains tests for the Orientation class which represents
3D rotations using sympy matrices.
"""

import pytest
import math
from sympy import Matrix, pi, simplify, Abs, eye, det, Rational
from code_goes_here.moothymoth import (
    Orientation,
    inches, feet, mm, cm, m,
    shaku, sun, bu,
    INCH_TO_METER, FOOT_TO_METER, SHAKU_TO_METER,
    create_v3
)
import random
from .testing_shavings import generate_random_orientation, assert_is_valid_rotation_matrix


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
        
        # Two 90° rotations should equal 180° rotation
        expected = Orientation(Matrix([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))  # 180° rotation
        assert simplify(result.matrix - expected.matrix) == Matrix.zeros(3, 3)
    
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
        assert simplify(inverted.matrix - expected.matrix) == Matrix.zeros(3, 3)
    
    def test_invert_identity_property(self):
        """Test that orientation * invert = identity."""
        for _ in range(5):  # Test with multiple random orientations
            orientation = generate_random_orientation()
            inverted = orientation.invert()
            result = orientation * inverted
            
            # Should be very close to identity
            identity = Matrix.eye(3)
            diff = simplify(result.matrix - identity)
            # For randomly generated orientations with float components, check that each element is close to 0
            for i in range(3):
                for j in range(3):
                    assert abs(float(diff[i, j])) < 1e-10
    
    def test_invert_double_invert(self):
        """Test that double inversion returns original."""
        orientation = generate_random_orientation()
        double_inverted = orientation.invert().invert()
        
        diff = simplify(orientation.matrix - double_inverted.matrix)
        # For randomly generated orientations with float components, check that each element is close to 0
        for i in range(3):
            for j in range(3):
                assert abs(float(diff[i, j])) < 1e-10


class TestOrientationFromVectors:
    """Test creating Orientations from direction vectors."""
    
    def test_from_z_and_y_basic(self):
        """Test from_z_and_y with basic orthogonal vectors."""
        z_dir = create_v3(0, 0, 1)  # Up
        y_dir = create_v3(0, 1, 0)  # North
        orient = Orientation.from_z_and_y(z_dir, y_dir)
        
        # Check the matrix columns are correct
        assert orient.matrix[:, 2] == z_dir  # Z column
        assert orient.matrix[:, 1] == y_dir  # Y column
        # X should be y × z = [0,1,0] × [0,0,1] = [1,0,0]
        assert orient.matrix[:, 0] == create_v3(1, 0, 0)
        assert_is_valid_rotation_matrix(orient.matrix)
    
    def test_from_z_and_x_basic(self):
        """Test from_z_and_x with basic orthogonal vectors."""
        z_dir = create_v3(0, 0, 1)  # Up
        x_dir = create_v3(1, 0, 0)  # East
        orient = Orientation.from_z_and_x(z_dir, x_dir)
        
        # Check the matrix columns are correct
        assert orient.matrix[:, 2] == z_dir  # Z column
        assert orient.matrix[:, 0] == x_dir  # X column
        # Y should be z × x = [0,0,1] × [1,0,0] = [0,1,0]
        assert orient.matrix[:, 1] == create_v3(0, 1, 0)
        assert_is_valid_rotation_matrix(orient.matrix)
    
    def test_from_x_and_y_basic(self):
        """Test from_x_and_y with basic orthogonal vectors."""
        x_dir = create_v3(1, 0, 0)  # East
        y_dir = create_v3(0, 1, 0)  # North
        orient = Orientation.from_x_and_y(x_dir, y_dir)
        
        # Check the matrix columns are correct
        assert orient.matrix[:, 0] == x_dir  # X column
        assert orient.matrix[:, 1] == y_dir  # Y column
        # Z should be x × y = [1,0,0] × [0,1,0] = [0,0,1]
        assert orient.matrix[:, 2] == create_v3(0, 0, 1)
        assert_is_valid_rotation_matrix(orient.matrix)
    
    def test_from_z_and_y_gives_identity(self):
        """Test that standard up/north vectors give identity."""
        orient = Orientation.from_z_and_y(
            create_v3(0, 0, 1),  # Z up
            create_v3(0, 1, 0)   # Y north
        )
        # This should give identity matrix
        assert orient.matrix == Matrix.eye(3)
    
    def test_from_vectors_consistency(self):
        """Test all three methods give same result for same orientation."""
        # All three should produce identity when given standard basis vectors
        orient_zy = Orientation.from_z_and_y(create_v3(0, 0, 1), create_v3(0, 1, 0))
        orient_zx = Orientation.from_z_and_x(create_v3(0, 0, 1), create_v3(1, 0, 0))
        orient_xy = Orientation.from_x_and_y(create_v3(1, 0, 0), create_v3(0, 1, 0))
        
        assert orient_zy.matrix == Matrix.eye(3)
        assert orient_zx.matrix == Matrix.eye(3)
        assert orient_xy.matrix == Matrix.eye(3)


class TestOrientationConstants:
    """Test the static orientation constants."""
    
    def test_identity_is_eye(self):
        """Test identity constant is 3x3 identity matrix."""
        assert Orientation.identity().matrix == Matrix.eye(3)
    
    def test_rotate_left_right_are_inverses(self):
        """Test rotate_left and rotate_right are inverses."""
        left = Orientation.rotate_left()
        right = Orientation.rotate_right()
        
        result = left * right
        identity = Matrix.eye(3)
        assert simplify(result.matrix - identity) == Matrix.zeros(3, 3)


class TestEulerAngles:
    """Test Euler angle functionality."""
    
    def test_from_euleryZYX_zero_angles(self):
        """Test from_euleryZYX with zero angles gives identity."""
        orientation = Orientation.from_euleryZYX(0, 0, 0)
        expected = Matrix.eye(3)
        assert simplify(orientation.matrix - expected) == Matrix.zeros(3, 3)
    
    def test_from_euleryZYX_yaw_only(self):
        """Test from_euleryZYX with only yaw rotation."""
        # 90° yaw should match rotate_left
        orientation = Orientation.from_euleryZYX(pi/2, 0, 0)
        expected = Orientation.rotate_left().matrix
        assert simplify(orientation.matrix - expected) == Matrix.zeros(3, 3)
    
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
            Orientation.identity(),
            Orientation.rotate_left(), 
            generate_random_orientation()
        ]
        
        for orientation in orientations:
            assert_is_valid_rotation_matrix(orientation.matrix)
    
    def test_orthogonality(self):
        """Test all orientation matrices are orthogonal (R * R^T = I)."""
        for _ in range(3):  # Test with random orientations
            orientation = generate_random_orientation()
            matrix = orientation.matrix
            
            product = simplify(matrix * matrix.T)
            identity = Matrix.eye(3)
            
            diff = product - identity
            # For randomly generated orientations with float components, check that each element is close to 0
            for i in range(3):
                for j in range(3):
                    assert abs(float(diff[i, j])) < 1e-10
    
    def test_inverse_equals_transpose(self):
        """Test that inverse equals transpose for rotation matrices."""
        orientation = generate_random_orientation()
        
        inverse_matrix = orientation.invert().matrix
        transpose_matrix = orientation.matrix.T
        
        diff = simplify(inverse_matrix - transpose_matrix)
        # For randomly generated orientations with float components, check that each element is close to 0
        for i in range(3):
            for j in range(3):
                assert abs(float(diff[i, j])) < 1e-10


class TestTimberOrientations:
    """Test timber-specific orientation methods."""
    
    def test_facing_west_is_identity(self):
        """Test facing_west is the identity orientation."""
        orient = Orientation.facing_west()
        assert orient.matrix == Matrix.eye(3)
    
    def test_pointing_up_is_identity(self):
        """Test pointing_up has LENGTH pointing upward (+Z)."""
        orient = Orientation.pointing_up()
        # Length points up (+Z)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, 0, 1])
        # Width points north (+Y)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([0, 1, 0])
        # Facing points west (-X)
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([-1, 0, 0])
    
    def test_facing_west_directions(self):
        """Test facing_west timber directions (identity)."""
        orient = Orientation.facing_west()
        # Length along +X (local)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([1, 0, 0])
        # Width along +Y (local)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([0, 1, 0])
        # Facing +Z (up)
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([0, 0, 1])
    
    def test_facing_east_directions(self):
        """Test facing_east timber directions (180° around Z)."""
        orient = Orientation.facing_east()
        # Length along -X (local becomes +X global/east)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([-1, 0, 0])
        # Width along -Y (local becomes +Y global/north)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([0, -1, 0])
        # Facing +Z (up)
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([0, 0, 1])
    
    def test_facing_north_directions(self):
        """Test facing_north timber directions (90° CCW around Z)."""
        orient = Orientation.facing_north()
        # Length along +Y (north)  
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, 1, 0])
        # Width along -X (west)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([-1, 0, 0])
        # Facing +Z (up)
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([0, 0, 1])
    
    def test_facing_south_directions(self):
        """Test facing_south timber directions (90° CW around Z)."""
        orient = Orientation.facing_south()
        # Length along -Y (south)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, -1, 0])
        # Width along +X (east)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([1, 0, 0])
        # Facing +Z (up)
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([0, 0, 1])
    
    def test_pointing_down_directions(self):
        """Test pointing_down has LENGTH pointing downward (-Z)."""
        orient = Orientation.pointing_down()
        # Length points down (-Z)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, 0, -1])
        # Width points north (+Y)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([0, 1, 0])
        # Facing points east (+X)
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([1, 0, 0])
    
    def test_pointing_forward_directions(self):
        """Test pointing_forward: +X points to +Z, facing upward."""
        orient = Orientation.pointing_forward()
        # Length should map to +Z (up)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, 0, 1])
        # Width along +Y
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([0, 1, 0])
        # Facing direction
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([-1, 0, 0])
    
    def test_pointing_backward_directions(self):
        """Test pointing_backward: +X points to +Z, facing upward, rotated 180°."""
        orient = Orientation.pointing_backward()
        # Length should map to +Z (up)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, 0, 1])
        # Width along -Y
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([0, -1, 0])
        # Facing direction
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([1, 0, 0])
    
    def test_pointing_left_directions(self):
        """Test pointing_left: +X points to +Z, facing upward, rotated 90° CCW."""
        orient = Orientation.pointing_left()
        # Length should map to +Z (up)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, 0, 1])
        # Width along -X (west/left)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([-1, 0, 0])
        # Facing direction maps to [0,-1,0]
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([0, -1, 0])
    
    def test_pointing_right_directions(self):
        """Test pointing_right: +X points to +Z, facing upward, rotated 90° CW."""
        orient = Orientation.pointing_right()
        # Length should map to +Z (up)
        assert orient.matrix * Matrix([1, 0, 0]) == Matrix([0, 0, 1])
        # Width along +X (east/right)
        assert orient.matrix * Matrix([0, 1, 0]) == Matrix([1, 0, 0])
        # Facing direction maps to [0,1,0]
        assert orient.matrix * Matrix([0, 0, 1]) == Matrix([0, 1, 0])
    
    def test_horizontal_timbers_all_face_up(self):
        """Test that all horizontal timber orientations have facing = +Z (up)."""
        horizontal_orientations = [
            Orientation.facing_east(),
            Orientation.facing_west(),
            Orientation.facing_north(),
            Orientation.facing_south()
        ]
        
        facing_vector = Matrix([0, 0, 1])  # Original facing direction
        expected_up = Matrix([0, 0, 1])     # Should always point up
        
        for orient in horizontal_orientations:
            result = orient.matrix * facing_vector
            assert result == expected_up, f"Failed for orientation: {orient}"
    
    def test_all_pointing_verticals_length_points_up(self):
        """Test that pointing_forward/backward/left/right all have length (+X) pointing to +Z."""
        vertical_orientations = [
            Orientation.pointing_forward(),
            Orientation.pointing_backward(),
            Orientation.pointing_left(),
            Orientation.pointing_right()
        ]
        
        length_vector = Matrix([1, 0, 0])  # Length direction
        expected_up = Matrix([0, 0, 1])     # Should point up (+Z)
        
        for orient in vertical_orientations:
            result = orient.matrix * length_vector
            assert result == expected_up, f"Failed for orientation: {orient}"
    
    def test_all_timber_orientations_are_valid_rotations(self):
        """Test that all timber orientations are valid rotation matrices."""
        timber_orientations = [
            Orientation.facing_east(),
            Orientation.facing_west(),
            Orientation.facing_north(),
            Orientation.facing_south(),
            Orientation.pointing_up(),
            Orientation.pointing_down(),
            Orientation.pointing_forward(),
            Orientation.pointing_backward(),
            Orientation.pointing_left(),
            Orientation.pointing_right()
        ]
        
        for orient in timber_orientations:
            assert_is_valid_rotation_matrix(orient.matrix)
    
    def test_facing_east_is_180_from_west(self):
        """Test facing_east is 180° rotation from facing_west."""
        east = Orientation.facing_east()
        west = Orientation.facing_west()
        
        # east * east should give identity (180° + 180° = 360°)
        result = east * east
        identity = Matrix.eye(3)
        assert simplify(result.matrix - identity) == Matrix.zeros(3, 3)
    
    def test_facing_north_south_are_90_apart(self):
        """Test facing_north and facing_south are 90° rotations from west."""
        north = Orientation.facing_north()
        south = Orientation.facing_south()
        
        # north * north * north * north should be identity (4 * 90° = 360°)
        result = north * north * north * north
        identity = Matrix.eye(3)
        assert simplify(result.matrix - identity) == Matrix.zeros(3, 3)


class TestFlipOrientation:
    """Test cases for flip method."""
    
    def test_flip_no_flips(self):
        """Test flip with no flips returns the same orientation."""
        orientation = Orientation.facing_north()
        flipped = orientation.flip()
        
        # With no flips, should be identical
        assert flipped.matrix == orientation.matrix
    
    def test_flip_flip_x(self):
        """Test flip with flip_x negates the first row."""
        orientation = Orientation.identity()
        flipped = orientation.flip(flip_x=True)
        
        # Should negate first row (x-axis basis vector)
        expected = Matrix([
            [-1, 0, 0],  # First row negated
            [0, 1, 0],
            [0, 0, 1]
        ])
        assert flipped.matrix == expected
    
    def test_flip_flip_y(self):
        """Test flip with flip_y negates the first column."""
        orientation = Orientation.identity()
        flipped = orientation.flip(flip_y=True)
        
        # Should negate first column
        expected = Matrix([
            [-1, 0, 0],  # First column negated
            [0, 1, 0],
            [0, 0, 1]
        ])
        assert flipped.matrix == expected
    
    def test_flip_flip_z(self):
        """Test flip with flip_z negates the third column."""
        orientation = Orientation.identity()
        flipped = orientation.flip(flip_z=True)
        
        # Should negate third column (z-axis)
        expected = Matrix([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, -1]  # Third column negated
        ])
        assert flipped.matrix == expected
    
    def test_flip_flip_x_and_y(self):
        """Test flip with both flip_x and flip_y."""
        orientation = Orientation.identity()
        flipped = orientation.flip(flip_x=True, flip_y=True)
        
        # Should negate first row and first column
        # For identity: flip_x negates row 0, flip_y negates column 0
        # Starting: [[1,0,0], [0,1,0], [0,0,1]]
        # After flip_x: [[-1,0,0], [0,1,0], [0,0,1]]
        # After flip_y: [[1,0,0], [0,1,0], [0,0,1]] (negates first column of the result)
        expected = Matrix([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ])
        assert flipped.matrix == expected
    
    def test_flip_flip_all(self):
        """Test flip with all axes flipped."""
        orientation = Orientation.identity()
        flipped = orientation.flip(flip_x=True, flip_y=True, flip_z=True)
        
        # Identity after all flips
        expected = Matrix([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, -1]
        ])
        assert flipped.matrix == expected
    
    def test_flip_non_identity(self):
        """Test flip on a non-identity orientation."""
        # Start with facing_north (90° CCW rotation around Z)
        orientation = Orientation.facing_north()
        # Matrix is [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
        
        flipped = orientation.flip(flip_x=True)
        
        # Should negate first row
        expected = Matrix([
            [0, 1, 0],   # First row negated
            [1, 0, 0],
            [0, 0, 1]
        ])
        assert flipped.matrix == expected
    
    def test_flip_pointing_up(self):
        """Test flip on a vertical orientation."""
        orientation = Orientation.pointing_up()  # Length points +Z
        flipped = orientation.flip(flip_z=True)
        
        # Should negate third column (Facing direction)
        # pointing_up is [[0,0,-1], [0,1,0], [1,0,0]]
        # After flipping Z: [[0,0,1], [0,1,0], [1,0,0]]
        expected = Matrix([
            [0, 0, 1],
            [0, 1, 0],
            [1, 0, 0]
        ])
        assert flipped.matrix == expected
    
    def test_flip_double_flip_x(self):
        """Test that flipping X twice returns the original."""
        orientation = Orientation.facing_north()
        flipped_once = orientation.flip(flip_x=True)
        flipped_twice = flipped_once.flip(flip_x=True)
        
        # Double flip should return to original
        assert flipped_twice.matrix == orientation.matrix
    
    def test_flip_double_flip_y(self):
        """Test that flipping Y twice returns the original."""
        orientation = Orientation.facing_east()
        flipped_once = orientation.flip(flip_y=True)
        flipped_twice = flipped_once.flip(flip_y=True)
        
        # Double flip should return to original
        assert flipped_twice.matrix == orientation.matrix
    
    def test_flip_double_flip_z(self):
        """Test that flipping Z twice returns the original."""
        orientation = Orientation.facing_south()
        flipped_once = orientation.flip(flip_z=True)
        flipped_twice = flipped_once.flip(flip_z=True)
        
        # Double flip should return to original
        assert flipped_twice.matrix == orientation.matrix
    
    def test_flip_with_random_orientation(self):
        """Test flip preserves orientation properties on random matrices."""
        orientation = generate_random_orientation()
        flipped = orientation.flip(flip_x=True, flip_z=True)
        
        # The flipped matrix should still be a valid rotation matrix
        # Note: flipping may change determinant, so we just verify it's orthogonal
        matrix = flipped.matrix
        product = simplify(matrix * matrix.T)
        identity = Matrix.eye(3)
        
        diff = product - identity
        # Check orthogonality
        for i in range(3):
            for j in range(3):
                assert abs(float(diff[i, j])) < 1e-10
    
    def test_flip_immutability(self):
        """Test that flip doesn't modify the original orientation."""
        orientation = Orientation.facing_north()
        original_matrix = orientation.matrix.copy()
        
        # Call flip
        flipped = orientation.flip(flip_x=True, flip_y=True, flip_z=True)
        
        # Original should be unchanged
        assert orientation.matrix == original_matrix
        # Flipped should be different
        assert flipped.matrix != original_matrix


class TestReprAndString:
    """Test string representation."""
    
    def test_repr_contains_matrix(self):
        """Test __repr__ contains the matrix."""
        orientation = Orientation.identity()
        repr_str = repr(orientation)
        
        assert "Orientation(" in repr_str
        assert "Matrix(" in repr_str
        assert "1" in repr_str  # Should contain identity matrix elements 


class TestDimensionalHelpers:
    """Test dimensional helper functions."""
    
    def test_inches_integer(self):
        """Test inches with integer input."""
        result = inches(1)
        expected = Rational(1) * INCH_TO_METER
        assert result == expected
    
    def test_inches_fraction(self):
        """Test inches with fractional input (1/32 inch)."""
        result = inches(1, 32)
        expected = Rational(1, 32) * INCH_TO_METER
        assert result == expected
    
    def test_inches_float(self):
        """Test inches with float input (converts to Rational)."""
        result = inches(3.5)
        expected = Rational(7, 2) * INCH_TO_METER
        assert result == expected
    
    def test_inches_string(self):
        """Test inches with string input."""
        result = inches("1.5")
        expected = Rational(3, 2) * INCH_TO_METER
        assert result == expected
    
    def test_inches_fraction_string(self):
        """Test inches with fraction string."""
        result = inches("1/32")
        expected = Rational(1, 32) * INCH_TO_METER
        assert result == expected
    
    def test_feet_integer(self):
        """Test feet with integer input."""
        result = feet(8)
        expected = Rational(8) * FOOT_TO_METER
        assert result == expected
    
    def test_feet_fraction(self):
        """Test feet with fractional input."""
        result = feet(1, 2)
        expected = Rational(1, 2) * FOOT_TO_METER
        assert result == expected
    
    def test_feet_float(self):
        """Test feet with float input."""
        result = feet(6.5)
        expected = Rational(13, 2) * FOOT_TO_METER
        assert result == expected
    
    def test_mm_integer(self):
        """Test millimeters with integer input."""
        result = mm(90)
        expected = Rational(90, 1000)
        assert result == expected
    
    def test_mm_fraction(self):
        """Test millimeters with fractional input."""
        result = mm(1, 2)
        expected = Rational(1, 2000)
        assert result == expected
    
    def test_mm_float(self):
        """Test millimeters with Rational input for exact comparison."""
        # Use exact Rational instead of float to avoid binary representation issues
        result = mm(Rational(254, 10))  # Exactly 25.4mm
        # Float conversion creates exact Rational from binary representation
        assert isinstance(result, Rational)
        # Check it equals exactly 1 inch
        expected = inches(1)
        assert result == expected
    
    def test_cm_integer(self):
        """Test centimeters with integer input."""
        result = cm(9)
        expected = Rational(9, 100)
        assert result == expected
    
    def test_cm_fraction(self):
        """Test centimeters with fractional input."""
        result = cm(1, 2)
        expected = Rational(1, 200)
        assert result == expected
    
    def test_m_integer(self):
        """Test meters with integer input."""
        result = m(1)
        expected = Rational(1)
        assert result == expected
    
    def test_m_fraction(self):
        """Test meters with fractional input."""
        result = m(1, 2)
        expected = Rational(1, 2)
        assert result == expected
    
    def test_m_float(self):
        """Test meters with float input."""
        result = m(2.5)
        expected = Rational(5, 2)
        assert result == expected
    
    def test_shaku_integer(self):
        """Test shaku with integer input."""
        result = shaku(1)
        expected = Rational(1) * SHAKU_TO_METER
        assert result == expected
    
    def test_shaku_fraction(self):
        """Test shaku with fractional input."""
        result = shaku(3, 2)
        expected = Rational(3, 2) * SHAKU_TO_METER
        assert result == expected
    
    def test_shaku_float(self):
        """Test shaku with float input."""
        result = shaku(2.5)
        expected = Rational(5, 2) * SHAKU_TO_METER
        assert result == expected
    
    def test_sun_integer(self):
        """Test sun with integer input (1 sun = 1/10 shaku)."""
        result = sun(1)
        expected = SHAKU_TO_METER / 10
        assert result == expected
    
    def test_sun_fraction(self):
        """Test sun with fractional input."""
        result = sun(1, 2)
        expected = Rational(1, 2) * SHAKU_TO_METER / 10
        assert result == expected
    
    def test_sun_multiple(self):
        """Test that 10 sun equals 1 shaku."""
        result_sun = sun(10)
        result_shaku = shaku(1)
        assert result_sun == result_shaku
    
    def test_bu_integer(self):
        """Test bu with integer input (1 bu = 1/100 shaku)."""
        result = bu(1)
        expected = SHAKU_TO_METER / 100
        assert result == expected
    
    def test_bu_fraction(self):
        """Test bu with fractional input."""
        result = bu(1, 2)
        expected = Rational(1, 2) * SHAKU_TO_METER / 100
        assert result == expected
    
    def test_bu_multiple(self):
        """Test that 10 bu equals 1 sun and 100 bu equals 1 shaku."""
        result_10bu = bu(10)
        result_1sun = sun(1)
        result_100bu = bu(100)
        result_1shaku = shaku(1)
        assert result_10bu == result_1sun
        assert result_100bu == result_1shaku
    
    def test_all_return_rational(self):
        """Test that all helper functions return Rational types."""
        # Test with integer inputs
        assert isinstance(inches(1), Rational)
        assert isinstance(feet(1), Rational)
        assert isinstance(mm(1), Rational)
        assert isinstance(cm(1), Rational)
        assert isinstance(m(1), Rational)
        assert isinstance(shaku(1), Rational)
        assert isinstance(sun(1), Rational)
        assert isinstance(bu(1), Rational)
        
        # Test with float inputs (should convert to Rational)
        assert isinstance(inches(1.5), Rational)
        assert isinstance(feet(6.5), Rational)
        assert isinstance(mm(25.4), Rational)
    
    def test_conversion_consistency(self):
        """Test that 1 inch equals 25.4 mm exactly."""
        result_inch = inches(1)
        result_mm = mm(Rational(254, 10))  # 25.4 mm
        assert result_inch == result_mm
    
    def test_practical_example_imperial(self):
        """Test a practical carpentry example with imperial units."""
        # 2x4 nominal dimensions (actual: 1.5" x 3.5")
        width = inches(3, 2)  # 1.5 inches
        height = inches(7, 2)  # 3.5 inches
        
        # Verify they're Rational
        assert isinstance(width, Rational)
        assert isinstance(height, Rational)
        
        # Verify exact metric values
        assert width == Rational(381, 10000)  # Exactly 38.1mm
        assert height == Rational(889, 10000)  # Exactly 88.9mm
    
    def test_practical_example_metric(self):
        """Test a practical carpentry example with metric units."""
        # Common timber: 90mm x 90mm
        width = mm(90)
        height = mm(90)
        
        assert isinstance(width, Rational)
        assert isinstance(height, Rational)
        assert width == Rational(9, 100)  # 0.09 meters
    
    def test_practical_example_japanese(self):
        """Test a practical carpentry example with Japanese traditional units."""
        # Common post: 4 sun x 4 sun (approximately 120mm x 120mm)
        width = sun(4)
        height = sun(4)
        
        assert isinstance(width, Rational)
        assert isinstance(height, Rational)
        
        # Verify they're equal and exact
        assert width == height
        assert width == Rational(4) * SHAKU_TO_METER / 10