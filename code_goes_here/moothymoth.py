'''
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
'''

import sympy as sp
from sympy import Matrix, cos, sin, pi, Float, Rational, Abs
from typing import Optional, Union
from dataclasses import dataclass, field
import warnings


# ============================================================================
# Epsilon Constants for Numerical Comparisons
# ============================================================================

# Epsilon constants for numerical comparisons
EPSILON_PARALLEL = Float('1e-4')  # Threshold for checking if vectors are nearly parallel/perpendicular
EPSILON_GENERIC = Float('1e-8')   # Generic epsilon threshold for all other comparisons


# ============================================================================
# Zero Test Helper Functions
# ============================================================================

def zero_test(value, always_exact: bool = False, epsilon: Optional[Float] = None) -> bool:
    """
    Test if a value is zero, with options for exact or epsilon-based checking.
    
    Args:
        value: The value to test (SymPy expression, Rational, Float, or numeric)
        always_exact: If True, force exact checking (raises assertion if epsilon provided)
        epsilon: If provided, use epsilon-based comparison
    
    Returns:
        True if value is (approximately) zero
    
    Behavior:
    - If value is Rational and epsilon is None: exact check (value == 0)
    - If always_exact is True: assert epsilon is None, warn if value is not Rational, do exact check
    - If epsilon is provided: check if |value| < epsilon
    """
    if always_exact:
        assert epsilon is None, "Cannot provide epsilon when always_exact=True"
        if not isinstance(value, Rational):
            warnings.warn(f"exact_zero_test called with non-Rational value {type(value).__name__}. Proceeding with exact check.")
        return value == 0
    
    if epsilon is None:
        if isinstance(value, Rational):
            return value == 0
        else:
            # Default to epsilon-based check for non-Rational values
            return Abs(value) < EPSILON_GENERIC
    
    return Abs(value) < epsilon


def epsilon_zero_test(value, epsilon: Float = EPSILON_GENERIC) -> bool:
    """
    Test if a value is approximately zero using epsilon comparison.
    
    Args:
        value: The value to test
        epsilon: Epsilon threshold (defaults to EPSILON_GENERIC)
    
    Returns:
        True if |value| < epsilon
    """
    return zero_test(value, always_exact=False, epsilon=epsilon)


def exact_zero_test(value) -> bool:
    """
    Test if a value is exactly zero. Warns if value is not Rational.
    
    Args:
        value: The value to test
    
    Returns:
        True if value == 0 (exact comparison)
    """
    return zero_test(value, always_exact=True, epsilon=None)


def equality_test(value, expected, always_exact: bool = False, epsilon: Optional[Float] = None) -> bool:
    """
    Test if a value equals an expected value, with options for exact or epsilon-based checking.
    
    Args:
        value: The value to test (SymPy expression, Rational, Float, or numeric)
        expected: The expected value to compare against
        always_exact: If True, force exact checking (raises assertion if epsilon provided)
        epsilon: If provided, use epsilon-based comparison
    
    Returns:
        True if value is (approximately) equal to expected
    
    Behavior:
    - If value and expected are Rational and epsilon is None: exact check (value == expected)
    - If always_exact is True: assert epsilon is None, warn if not Rational, do exact check
    - If epsilon is provided: check if |value - expected| < epsilon
    """
    if always_exact:
        assert epsilon is None, "Cannot provide epsilon when always_exact=True"
        if not (isinstance(value, Rational) and isinstance(expected, Rational)):
            warnings.warn(f"exact_equality_test called with non-Rational values {type(value).__name__} and {type(expected).__name__}. Proceeding with exact check.")
        return value == expected
    
    if epsilon is None:
        if isinstance(value, Rational) and isinstance(expected, Rational):
            return value == expected
        else:
            # Default to epsilon-based check for non-Rational values
            return Abs(value - expected) < EPSILON_GENERIC
    
    return Abs(value - expected) < epsilon


def epsilon_equality_test(value, expected, epsilon: Float = EPSILON_GENERIC) -> bool:
    """
    Test if a value is approximately equal to an expected value using epsilon comparison.
    
    Args:
        value: The value to test
        expected: The expected value
        epsilon: Epsilon threshold (defaults to EPSILON_GENERIC)
    
    Returns:
        True if |value - expected| < epsilon
    """
    return equality_test(value, expected, always_exact=False, epsilon=epsilon)


def exact_equality_test(value, expected) -> bool:
    """
    Test if a value is exactly equal to an expected value. Warns if values are not Rational.
    
    Args:
        value: The value to test
        expected: The expected value
    
    Returns:
        True if value == expected (exact comparison)
    """
    return equality_test(value, expected, always_exact=True, epsilon=None)


# ============================================================================
# Parallel and Perpendicular Check Functions
# ============================================================================

def construction_parallel_check(vector1: Matrix, vector2: Matrix, always_exact: bool = False, epsilon: Optional[Float] = None) -> bool:
    """
    Check if two vectors are parallel.
    
    For normalized vectors: dot product ≈ ±1 means parallel
    
    Args:
        vector1: First direction vector
        vector2: Second direction vector
        always_exact: If True, force exact checking (raises assertion if epsilon provided)
        epsilon: Threshold for parallel check (defaults to EPSILON_PARALLEL if None)
    
    Returns:
        True if |abs(dot_product) - 1| < epsilon (vectors are parallel)
    """
    if epsilon is None and not always_exact:
        epsilon = EPSILON_PARALLEL
    
    # Compute dot product
    dot_product = vector1.dot(vector2)
    
    # Check if |abs(dot_product) - 1| is approximately zero
    # This is equivalent to checking if abs(dot_product) is approximately 1
    deviation = Abs(Abs(dot_product) - 1)
    
    return zero_test(deviation, always_exact=always_exact, epsilon=epsilon)


def construction_perpendicular_check(vector1: Matrix, vector2: Matrix, always_exact: bool = False, epsilon: Optional[Float] = None) -> bool:
    """
    Check if two vectors are perpendicular.
    
    For any vectors: dot product ≈ 0 means perpendicular
    
    Args:
        vector1: First direction vector
        vector2: Second direction vector
        always_exact: If True, force exact checking (raises assertion if epsilon provided)
        epsilon: Threshold for perpendicular check (defaults to EPSILON_PARALLEL if None)
    
    Returns:
        True if |dot_product| < epsilon (vectors are perpendicular)
    """
    if epsilon is None and not always_exact:
        epsilon = EPSILON_PARALLEL
    
    # Compute dot product
    dot_product = vector1.dot(vector2)
    
    # Check if dot product is approximately zero
    return zero_test(dot_product, always_exact=always_exact, epsilon=epsilon)


# ============================================================================
# Orientation Class
# ============================================================================

@dataclass(frozen=True)
class Orientation:
    """
    Represents a 3D rotation using a 3x3 rotation matrix.
    Uses sympy for symbolic mathematics.
    """
    matrix: Matrix = field(default_factory=lambda: Matrix.eye(3))
    
    def __post_init__(self):
        """Convert to Matrix and validate that the matrix is 3x3."""
        # Convert to Matrix if necessary (handles list/tuple inputs)
        if not isinstance(self.matrix, Matrix):
            object.__setattr__(self, 'matrix', Matrix(self.matrix))
        
        if self.matrix.shape != (3, 3):
            raise ValueError("Rotation matrix must be 3x3")
    
    def multiply(self, other: 'Orientation') -> 'Orientation':
        """
        Multiply this orientation with another orientation.
        Returns a new Orientation representing the combined rotation.
        """
        if not isinstance(other, Orientation):
            raise TypeError("Can only multiply with another Orientation")
        return Orientation(self.matrix * other.matrix)
    
    def invert(self) -> 'Orientation':
        """
        Return the inverse of this orientation.
        For rotation matrices, the inverse is the transpose.
        """
        return Orientation(self.matrix.T)
    
    def __mul__(self, other: 'Orientation') -> 'Orientation':
        """Allow using * operator for multiplication"""
        return self.multiply(other)
    
    def __repr__(self) -> str:
        return f"Orientation(\n{self.matrix}\n)"
    
    # Static constants for cardinal directions
    @classmethod
    def identity(cls) -> 'Orientation':
        """Identity orientation - facing east (+X)"""
        return cls()
    
    @classmethod  
    def right(cls) -> 'Orientation':
        """Facing east (+X) - same as identity"""
        return cls()
    
    @classmethod
    def east(cls) -> 'Orientation':
        """Facing east (+X) - same as identity"""
        return cls()
    
    @classmethod
    def left(cls) -> 'Orientation':
        """Facing west (-X) - 180° rotation around Z axis"""
        matrix = Matrix([
            [-1, 0, 0],
            [0, -1, 0], 
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def west(cls) -> 'Orientation':
        """Facing west (-X)"""
        return cls.left()
    
    @classmethod
    def forward(cls) -> 'Orientation':
        """Facing north (+Y) - 90° counterclockwise rotation around Z axis"""
        matrix = Matrix([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def north(cls) -> 'Orientation':
        """Facing north (+Y)"""
        return cls.forward()
    
    @classmethod
    def backward(cls) -> 'Orientation':
        """Facing south (-Y) - 90° clockwise rotation around Z axis"""
        matrix = Matrix([
            [0, 1, 0],
            [-1, 0, 0],
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def south(cls) -> 'Orientation':
        """Facing south (-Y)"""
        return cls.backward()
    
    @classmethod
    def up(cls) -> 'Orientation':
        """Facing up (+Z) - 90° rotation around Y axis"""
        matrix = Matrix([
            [0, 0, 1],
            [0, 1, 0],
            [-1, 0, 0]
        ])
        return cls(matrix)
    
    @classmethod
    def down(cls) -> 'Orientation':
        """Facing down (-Z) - -90° rotation around Y axis"""
        matrix = Matrix([
            [0, 0, -1],
            [0, 1, 0],
            [1, 0, 0]
        ])
        return cls(matrix)
    
    @classmethod
    def rotate_right(cls) -> 'Orientation':
        """Rotate right: +X axis rotates to -Y axis (clockwise around Z)"""
        matrix = Matrix([
            [0, 1, 0],
            [-1, 0, 0],
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def rotate_left(cls) -> 'Orientation':
        """Rotate left: +X axis rotates to +Y axis (counterclockwise around Z)"""
        matrix = Matrix([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def from_euleryZYX(cls, yaw: Union[float, int, sp.Basic], pitch: Union[float, int, sp.Basic], roll: Union[float, int, sp.Basic]) -> 'Orientation':
        """
        Create an Orientation from Euler angles using ZYX rotation sequence.
        
        Args:
            yaw: Rotation around Z-axis (radians)
            pitch: Rotation around Y-axis (radians) 
            roll: Rotation around X-axis (radians)
            
        Returns:
            Orientation object with combined rotation matrix
            
        The rotation sequence is:
        1. Yaw (Z-axis rotation)
        2. Pitch (Y-axis rotation)
        3. Roll (X-axis rotation)
        """
        # Individual rotation matrices
        Rz = Matrix([
            [cos(yaw), -sin(yaw), 0],
            [sin(yaw), cos(yaw), 0],
            [0, 0, 1]
        ])
        
        Ry = Matrix([
            [cos(pitch), 0, sin(pitch)],
            [0, 1, 0],
            [-sin(pitch), 0, cos(pitch)]
        ])
        
        Rx = Matrix([
            [1, 0, 0],
            [0, cos(roll), -sin(roll)],
            [0, sin(roll), cos(roll)]
        ])
        
        # Combined rotation: R = Rz * Ry * Rx
        combined_matrix = Rz * Ry * Rx
        return cls(combined_matrix)

