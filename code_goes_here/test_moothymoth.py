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
    INCH_TO_METER, FOOT_TO_METER, SHAKU_TO_METER
)
import random
from .conftest import generate_random_orientation, assert_is_valid_rotation_matrix


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
            assert_is_valid_rotation_matrix(orientation.matrix)
    
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
        """Test millimeters with float input."""
        result = mm(25.4)
        # Float conversion creates exact Rational from binary representation
        assert isinstance(result, Rational)
        # Check it's approximately 0.0254 meters (1 inch)
        assert abs(float(result) - 0.0254) < 1e-10
    
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
        # Verify it's approximately 303.03mm
        assert abs(float(result) - 0.30303030) < 0.00001
    
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
        # Verify it's approximately 30.303mm
        assert abs(float(result) - 0.030303030) < 0.000001
    
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
        # Verify it's approximately 3.0303mm
        assert abs(float(result) - 0.0030303030) < 0.0000001
    
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
        
        # Verify approximate metric values
        assert abs(float(width) - 0.0381) < 0.0001  # ~38.1mm
        assert abs(float(height) - 0.0889) < 0.0001  # ~88.9mm
    
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
        
        # Verify approximate metric values
        assert abs(float(width) - 0.12121212) < 0.00001  # ~121.2mm
        assert abs(float(height) - 0.12121212) < 0.00001  # ~121.2mm