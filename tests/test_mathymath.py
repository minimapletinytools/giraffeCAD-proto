# ABANDONED see moothymoth.py
"""
Tests for mathymath.py module.

This module contains tests for the mathymath library which deals with
general rigid bodies in 3D space and specialized fractional rotations.
"""

import pytest
import numpy as np
from mathymath import Rational_Orientation, Orientation
from spatialmath import UnitQuaternion


class TestRationalOrientation:
    """Test cases for the Rational_Orientation class."""
    
    def test_init(self):
        """Test initialization of Rational_Orientation."""
        # TODO: Implement test for initialization
        pass

    def test_identity(self):
        """Test identity orientation."""
        # Create an identity Rational_Orientation (all zero rotations)
        identity_rational = Rational_Orientation([0.0, 0.0, 0.0])
        
        # Convert to Orientation
        orientation = identity_rational.to_orientation()
        
        # Convert to UnitQuaternion
        quaternion = orientation.to_quaternion()
        
        # Create identity quaternion for comparison
        identity_quaternion = UnitQuaternion()
        
        # Check that the resulting quaternion is the identity quaternion
        # UnitQuaternion identity is [1, 0, 0, 0] (w, x, y, z)
        np.testing.assert_allclose(quaternion.s, identity_quaternion.s, atol=1e-10)
        np.testing.assert_allclose(quaternion.v, identity_quaternion.v, atol=1e-10)
    
    def test_mul_basic(self):
        """Test multiplication of Rational_Orientation objects."""
        
        # Test Case 1: Identity × Identity = Identity
        identity1 = Rational_Orientation([0.0, 0.0, 0.0])
        identity2 = Rational_Orientation([0.0, 0.0, 0.0])
        result1 = identity1 * identity2
        
        # Should result in identity orientation
        expected_quat1 = UnitQuaternion()
        actual_quat1 = result1.to_quaternion()
        np.testing.assert_allclose(actual_quat1.s, expected_quat1.s, atol=1e-10)
        np.testing.assert_allclose(actual_quat1.v, expected_quat1.v, atol=1e-10)
        np.testing.assert_allclose(result1.rot_Q, [0.0, 0.0, 0.0], atol=1e-10)
        
        # Test Case 2: Identity × Z-rotation = Z-rotation 
        identity = Rational_Orientation([0.0, 0.0, 0.0])
        z_rot_90 = Rational_Orientation([0.0, 0.0, 0.5])  # 90° around Z (π/2 radians)
        result2 = identity * z_rot_90
        
        # Should result in the same Z rotation
        # The rational component should be preserved: [0, 0, 0.5]
        np.testing.assert_allclose(result2.rot_Q, [0.0, 0.0, 0.5], atol=1e-10)
        # The quaternion component should be identity since it's a pure rational rotation
        identity_quat = UnitQuaternion()
        np.testing.assert_allclose(result2.rot_R.s, identity_quat.s, atol=1e-10)
        np.testing.assert_allclose(result2.rot_R.v, identity_quat.v, atol=1e-10)
        
        # Test Case 3: Z-rotation × Z-rotation = Combined Z-rotation
        z_rot_45_1 = Rational_Orientation([0.0, 0.0, 0.25])  # 45° around Z (π/4 radians)
        z_rot_45_2 = Rational_Orientation([0.0, 0.0, 0.25])  # 45° around Z (π/4 radians)
        result3 = z_rot_45_1 * z_rot_45_2
        
        # Should result in 90° Z rotation: 0.25 + 0.25 = 0.5
        np.testing.assert_allclose(result3.rot_Q, [0.0, 0.0, 0.5], atol=1e-10)
        # The quaternion component should be identity since it's a pure rational rotation
        np.testing.assert_allclose(result3.rot_R.s, identity_quat.s, atol=1e-10)
        np.testing.assert_allclose(result3.rot_R.v, identity_quat.v, atol=1e-10)
    

# TODO: Add more test classes for other classes in mathymath.py as they are discovered
# TODO: Add integration tests for complex mathematical operations
# TODO: Add property-based tests using hypothesis for mathematical properties 