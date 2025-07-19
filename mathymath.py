"""
Mathymath is a math library intended for dealing with general rigid bodies in 3D space 
and additionally specialized to deal with fractional rotations.

The library uses RHS coordinates with Z facing up, Y facing north, and X facing east.
The main class is the Orientation class which stores rotation in 2 components.

Coordinate System (RHS):

(up) Z 
     ^  ^ Y (north)
     | /
     |/
     +-----> X (east)
    /
   /
  v
-Y (south)

RHS = Right Hand System
- X-axis: points east
- Y-axis: points north  
- Z-axis: points up
- Thumb = X, Index = Y, Middle = Z
"""

import numpy as np
from typing import Union, Tuple, Optional, List
from spatialmath import SE3, SO3, UnitQuaternion



class Rational_Orientation:
    """
    Represents a 3D orientation in ZYX euler angles with only rational components (stored as radians/pi i.e. just the rational pi multiplier)
    All components are assumed to have no floating point roundoff error
    """
    def __init__(self, rot_Q: Union[Tuple[float, float, float], List[float], np.ndarray]):
        self.rot_Q = np.array(rot_Q, dtype=float)

    def __mul__(self, other: 'Rational_Orientation') -> 'Orientation':
        """
        Multiply 2 Rational_Orientation and return an Orientation as there may be irrational components
        We preserve as much of the rational components as we can.
        """
        if not isinstance(other, Rational_Orientation):
            raise TypeError("Can only multiply Rational_Orientation with another Rational_Orientation")

        r1x, r1y, r1z = self.rot_Q
        r2x, r2y, r2z = other.rot_Q

        eps = 1e-12
        def is_zero(x):
            return abs(x) < eps

        r1x_id = is_zero(r1x)
        r1y_id = is_zero(r1y)
        r1z_id = is_zero(r1z)
        r2x_id = is_zero(r2x)
        r2y_id = is_zero(r2y)
        r2z_id = is_zero(r2z)

        # TODO if there is floating point roundoff error, just convert to Orientation
        # TODO handle special case of 90 degree rotations where we can preserve rational components in more cases

        # Case 1: r1y and r1x are identity
        if r1y_id and r1x_id:
            new_rz = r1z + r2z
            return Orientation([r2x, r2y, new_rz], UnitQuaternion())

        # Case 2: r1x and r2z are identity
        if r1x_id and r2z_id:
            new_ry = r1y + r2y
            return Orientation([r2x, new_ry, r1z], UnitQuaternion())

        # Case 3: r2z and r2y are identity
        if r2z_id and r2y_id:
            new_rx = r1x + r2x
            return Orientation([new_rx, r1y, r1z], UnitQuaternion())

        # Fallback: use quaternion composition
        return Orientation(self.rot_Q, SO3.RzRyRx(r2z, r2y, r2x))

    def to_orientation(self) -> 'Orientation':
        """
        Convert a Rational_Orientation to an Orientation
        """
        return Orientation(self.rot_Q, UnitQuaternion())



class Orientation:
    """
    Represents a 3D orientation with rational and irrational rotation components.
    
    Attributes:
        rot_Q: Rational rotation component, stored as euler angles
        rot_R: Irrational rotation component, stored as a quaternion

    the resulting rotation is rot_Q * rot_R
    """
    
    def __init__(self, rot_Q: Union[Tuple[float, float, float], List[float], np.ndarray], 
                 rot_R: Union[UnitQuaternion, np.ndarray]):
        """
        Initialize an Orientation object.
        
        Args:
            rot_Q: Rational rotation component (euler angles in radians)
            rot_R: Irrational rotation component (quaternion)
        """
        self.rot_Q = np.array(rot_Q, dtype=float)  # rational rotation component
        self.rot_R = rot_R  # irrational rotation component
    
    @classmethod
    def identity(cls) -> 'Orientation':
        """Create an identity orientation."""
        return cls([0.0, 0.0, 0.0], UnitQuaternion())
    
    def __mul__(self, other: 'Orientation') -> 'Orientation':
        """
        Multiply two orientations: r1 * r2 = r3
        
        The multiplication follows these rules:
        - If r1.rot_R is not identity: rX.rot_Q = r1.rot_Q and rX.rot_R = r1.rot_R * r2.rot_Q * r2.rot_R
        - If r1.rot_R is identity: rX.rot_Q = r1.rot_Q * r2.rot_Q and rX.rot_R = r2.rot_R
        """
        if not isinstance(other, Orientation):
            raise TypeError("Can only multiply Orientation objects")
        
        # Check if r1.rot_R is identity
        if isinstance(self.rot_R, UnitQuaternion):
            is_identity = np.allclose(self.rot_R.A[:3, :3], np.eye(3), atol=1e-10)
        else:
            is_identity = np.allclose(self.rot_R, [1, 0, 0, 0], atol=1e-10)
            
        if is_identity:
            # r1.rot_R is identity
            new_rot_Q = self.rot_Q * other.rot_Q
            new_rot_R = other.rot_R
        else:
            # r1.rot_R is not identity
            new_rot_Q = self.rot_Q.copy()
            # Combine the rotations: r1.rot_R * r2.rot_Q * r2.rot_R
            # First apply r2.rot_Q as a quaternion using SO3
            r2_so3 = SO3.RzRyRx(other.rot_Q[2], other.rot_Q[1], other.rot_Q[0])
            r2_quat = UnitQuaternion(r2_so3)
            combined_rot = self.rot_R * r2_quat * other.rot_R
            new_rot_R = combined_rot
        
        return Orientation(new_rot_Q, new_rot_R)
    
    def __str__(self) -> str:
        """String representation of the orientation."""
        return f"Orientation(rot_Q={self.rot_Q}, rot_R={self.rot_R})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Orientation(rot_Q={self.rot_Q.tolist()}, rot_R={self.rot_R})"
    
    def to_quaternion(self) -> UnitQuaternion:
        """
        Get the resulting rotation rot_Q * rot_R as a quaternion.
        
        Returns:
            Combined quaternion representing the total rotation
        """
        # Convert rot_Q (euler angles) to quaternion using SO3
        q_so3 = SO3.RzRyRx(self.rot_Q[2], self.rot_Q[1], self.rot_Q[0])
        q_quat = UnitQuaternion(q_so3)
        # Combine with rot_R
        return q_quat * self.rot_R
    
    def get_rational_euler_angles(self) -> np.ndarray:
        """
        Get the resulting rotation rot_Q * rot_R in euler angles.
        
        Returns:
            Euler angles [roll, pitch, yaw] in radians
        """
        combined_quat = self.to_quaternion()
        return combined_quat.eul()
    
    def exact_eq(self, other: 'Orientation') -> bool:
        """
        Check if two orientations are exactly equal.
        
        Args:
            other: Another Orientation object
            
        Returns:
            True if orientations are exactly equal
        """
        if not isinstance(other, Orientation):
            return False
        
        # Compare rational components
        rot_Q_equal = np.array_equal(self.rot_Q, other.rot_Q)
        
        # Compare irrational components
        if isinstance(self.rot_R, UnitQuaternion) and isinstance(other.rot_R, UnitQuaternion):
            rot_R_equal = np.array_equal(self.rot_R.A, other.rot_R.A)
        else:
            rot_R_equal = np.array_equal(self.rot_R, other.rot_R)
        
        return rot_Q_equal and rot_R_equal
    
    def fuzzy_eq(self, other: 'Orientation', epsilon: float = 1e-10) -> bool:
        """
        Check if two orientations are approximately equal within epsilon.
        
        Args:
            other: Another Orientation object
            epsilon: Tolerance for comparison
            
        Returns:
            True if orientations are approximately equal
        """
        if not isinstance(other, Orientation):
            return False
        
        # Compare rational components
        rot_Q_equal = np.allclose(self.rot_Q, other.rot_Q, atol=epsilon)
        
        # Compare irrational components
        if isinstance(self.rot_R, UnitQuaternion) and isinstance(other.rot_R, UnitQuaternion):
            rot_R_equal = np.allclose(self.rot_R.A, other.rot_R.A, atol=epsilon)
        else:
            rot_R_equal = np.allclose(self.rot_R, other.rot_R, atol=epsilon)
        
        return rot_Q_equal and rot_R_equal
    
    
    def rotate_point(self, point: SE3) -> SE3:
        """
        Rotate a 3D point using this orientation.
        
        Args:
            point: 3D point as numpy array [x, y, z]
            
        Returns:
            Rotated point
        """
        combined_quat = self.to_quaternion()
        # Convert to SO3 for point rotation
        so3_rotation = SO3(combined_quat)
        return so3_rotation * point

    def x(self) -> SE3:
        self.rotate_point(SE3(1,0,0))
    def y(self) -> SE3:
        self.rotate_point(SE3(0,1,0))
    def z(self) -> SE3:
        self.rotate_point(SE3(0,0,1))
    

    