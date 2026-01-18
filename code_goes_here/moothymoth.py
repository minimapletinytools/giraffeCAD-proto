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
from sympy import Matrix, cos, sin, pi, Float, Rational, Abs, S, sympify, Expr
from typing import Optional, Union
from dataclasses import dataclass, field
import warnings


# ============================================================================
# Type Aliases
# ============================================================================

# Type aliases for vectors using sympy, these are just to provide some semantic 
# clarity in the interfaces and are not enforced by the type system.
V2 = Matrix  # 2D vector - 2x1 Matrix
V3 = Matrix  # 3D vector - 3x1 Matrix  
Direction3D = Matrix  # 3D direction vector - 3x1 Matrix

Numeric = Union[float, int, Expr]  # Numeric values (SymPy Expr type STRONGLY preferred, there's really no reason to ever be using floats or ints. Always use Rational)


# ============================================================================
# Transform Class
# ============================================================================

@dataclass(frozen=True)
class Transform:
    """
    Represents a 3D transformation with position and orientation.
    Encapsulates both translation and rotation for objects in 3D space.
    """
    position: V3
    orientation: 'Orientation'
    
    @classmethod
    def identity(cls) -> 'Transform':
        """Create an identity transform at origin with identity orientation."""
        return cls(
            position=create_v3(0, 0, 0),
            orientation=Orientation.identity()
        )
    
    def local_to_global(self, local_point: V3) -> V3:
        """
        Convert a point from local coordinates to global world coordinates.
        
        Args:
            local_point: A point in local coordinates
            
        Returns:
            The same point in global world coordinates
        """
        # Rotate to global frame, then translate to position
        # global = R * local + position
        return self.orientation.matrix * local_point + self.position
    
    def global_to_local(self, global_point: V3) -> V3:
        """
        Convert a point from global world coordinates to local coordinates.
        
        Args:
            global_point: A point in global world coordinates
            
        Returns:
            The same point in local coordinates
        """
        # Translate to origin, then rotate to local frame
        # local = R^T * (global - position)
        translated = global_point - self.position
        return self.orientation.matrix.T * translated


# ============================================================================
# Helper Functions for Vector Operations
# ============================================================================

def create_v2(x: Numeric, y: Numeric) -> V2:
    """Create a 2D vector"""
    return Matrix([x, y])

def create_v3(x: Numeric, y: Numeric, z: Numeric) -> V3:
    """Create a 3D vector"""
    return Matrix([x, y, z])

def normalize_vector(vec: Matrix) -> Matrix:
    """Normalize a vector using SymPy's exact computation"""
    norm = vec.norm()
    if norm == 0:
        return vec
    return vec / norm

def cross_product(v1: V3, v2: V3) -> V3:
    """Calculate cross product of two 3D vectors"""
    return Matrix([
        v1[1]*v2[2] - v1[2]*v2[1],
        v1[2]*v2[0] - v1[0]*v2[2], 
        v1[0]*v2[1] - v1[1]*v2[0]
    ])

def vector_magnitude(vec: Matrix):
    """Calculate magnitude of a vector using SymPy's exact computation"""
    return vec.norm()


# ============================================================================
# Unit Conversion Constants
# ============================================================================

# Conversion factors to meters (exact Rationals)
INCH_TO_METER = Rational(254, 10000)      # 0.0254 m (exact by definition)
FOOT_TO_METER = Rational(3048, 10000)     # 0.3048 m (exact by definition)
SHAKU_TO_METER = Rational(10, 33)         # ~0.303030... m (1 shaku = 10/33 m, traditional)

# Note: The traditional Japanese shaku is defined as 10/33 meters
# This gives approximately 303.03mm, and ensures exact rational arithmetic


# ============================================================================
# Epsilon Constants for Numerical Comparisons
# ============================================================================

# Epsilon constants for numerical comparisons
EPSILON_GENERIC = Float('1e-8')      # Generic epsilon threshold for float comparisons
SYMPY_EXPR_EPSILON = Float('1e-12')  # Epsilon for SymPy expressions when .equals() returns None


# ============================================================================
# Dimensional Helper Functions
# ============================================================================

def inches(numerator, denominator=1):
    """
    Create a Rational measurement in meters from inches.
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        inches(1, 32)        # 1/32 inch
        inches(4)            # 4 inches
        inches(3.5)          # 3.5 inches (converted to Rational)
        inches("1.5")        # 1.5 inches from string
        inches("1/32")       # Parses fraction string
    """
    return Rational(numerator, denominator) * INCH_TO_METER


def feet(numerator, denominator=1):
    """
    Create a Rational measurement in meters from feet.
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        feet(8)              # 8 feet
        feet(1, 2)           # 1/2 foot
        feet(6.5)            # 6.5 feet (converted to Rational)
    """
    return Rational(numerator, denominator) * FOOT_TO_METER


def mm(numerator, denominator=1):
    """
    Create a Rational measurement in meters from millimeters.
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        mm(90)               # 90 millimeters
        mm(1, 2)             # 1/2 millimeter
        mm(25.4)             # 25.4 millimeters (converted to Rational)
    """
    return Rational(numerator, denominator) / 1000


def cm(numerator, denominator=1):
    """
    Create a Rational measurement in meters from centimeters.
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        cm(9)                # 9 centimeters
        cm(1, 2)             # 1/2 centimeter
        cm(2.54)             # 2.54 centimeters (converted to Rational)
    """
    return Rational(numerator, denominator) / 100


def m(numerator, denominator=1):
    """
    Create a Rational measurement in meters.
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        m(1)                 # 1 meter
        m(1, 2)              # 1/2 meter
        m(2.5)               # 2.5 meters (converted to Rational)
    """
    return Rational(numerator, denominator)


def shaku(numerator, denominator=1):
    """
    Create a Rational measurement in meters from shaku (尺).
    Traditional Japanese carpentry unit.
    
    1 shaku ≈ 303.03 mm (exactly 10/33 meters)
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        shaku(1)             # 1 shaku
        shaku(3, 2)          # 3/2 shaku (1.5 shaku)
        shaku(2.5)           # 2.5 shaku (converted to Rational)
    """
    return Rational(numerator, denominator) * SHAKU_TO_METER


def sun(numerator, denominator=1):
    """
    Create a Rational measurement in meters from sun (寸).
    Traditional Japanese carpentry unit.
    
    1 sun = 1/10 shaku ≈ 30.303 mm
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        sun(1)               # 1 sun
        sun(5)               # 5 sun
        sun(1, 2)            # 1/2 sun
    """
    return Rational(numerator, denominator) * SHAKU_TO_METER / 10


def bu(numerator, denominator=1):
    """
    Create a Rational measurement in meters from bu (分).
    Traditional Japanese carpentry unit.
    
    1 bu = 1/10 sun = 1/100 shaku ≈ 3.0303 mm
    
    Args:
        numerator: The numerator (can be int, float, str, or Rational)
        denominator: The denominator (default=1)
    
    Returns:
        Rational value in meters
    
    Examples:
        bu(1)                # 1 bu
        bu(5)                # 5 bu
        bu(1, 2)             # 1/2 bu
    """
    return Rational(numerator, denominator) * SHAKU_TO_METER / 100


# ============================================================================
# Zero Test Helper Functions
# ============================================================================

def zero_test(value) -> bool:
    """
    Test if a value is zero using SymPy's equals() method or float comparison.
    
    Args:
        value: The value to test (SymPy expression, Rational, Float, or numeric)
    
    Returns:
        True if value is (approximately) zero
    
    Behavior:
    - If value contains Float: Use epsilon comparison (EPSILON_GENERIC)
    - If value has .equals() method: Try exact symbolic comparison
    - For plain floats/ints: Use epsilon comparison (EPSILON_GENERIC)
    """
    # Check if value contains Float components (use epsilon comparison for floats)
    if hasattr(value, 'has') and value.has(Float):
        return Abs(value) < EPSILON_GENERIC
    
    # Try SymPy exact equality for symbolic/Rational values
    if hasattr(value, 'equals'):
        result = value.equals(0)
        if result is True:
            return True
        elif result is False:
            return False
        # result is None - couldn't determine, fall back to epsilon
        return Abs(value) < EPSILON_GENERIC
    
    # For plain Python floats/ints
    return Abs(value) < EPSILON_GENERIC


def equality_test(value, expected) -> bool:
    """
    Test if a value equals an expected value using SymPy's equals() method or float comparison.
    
    Args:
        value: The value to test (SymPy expression, Rational, Float, or numeric)
        expected: The expected value to compare against
    
    Returns:
        True if value is (approximately) equal to expected
    
    Behavior:
    - If value or expected contains Float: Use epsilon comparison (EPSILON_GENERIC)
    - If both have .equals() method: Try exact symbolic comparison
    - For plain floats/ints: Use epsilon comparison (EPSILON_GENERIC)
    """
    # Check if either value contains Float components (use epsilon comparison for floats)
    has_float = False
    if hasattr(value, 'has') and value.has(Float):
        has_float = True
    if hasattr(expected, 'has') and expected.has(Float):
        has_float = True
    
    if has_float:
        return Abs(value - expected) < EPSILON_GENERIC
    
    # Try SymPy exact equality for symbolic/Rational values
    if hasattr(value, 'equals') and hasattr(expected, 'equals'):
        diff = value - expected
        result = diff.equals(0)
        if result is True:
            return True
        elif result is False:
            return False
        # result is None - couldn't determine, fall back to epsilon
        return Abs(value - expected) < EPSILON_GENERIC
    
    # For plain Python floats/ints
    return Abs(value - expected) < EPSILON_GENERIC


# ============================================================================
# Parallel and Perpendicular Check Functions
# ============================================================================

def are_vectors_parallel(vector1: Matrix, vector2: Matrix) -> bool:
    """
    Check if two vectors are parallel.
    
    For normalized vectors: dot product ≈ ±1 means parallel
    
    Args:
        vector1: First direction vector
        vector2: Second direction vector
    
    Returns:
        True if |abs(dot_product) - 1| is approximately zero (vectors are parallel)
    """
    # Compute dot product
    dot_product = vector1.dot(vector2)
    
    # Check if |abs(dot_product) - 1| is approximately zero
    # This is equivalent to checking if abs(dot_product) is approximately 1
    deviation = Abs(Abs(dot_product) - 1)
    
    return zero_test(deviation)

def are_vectors_perpendicular(vector1: Matrix, vector2: Matrix) -> bool:
    """
    Check if two vectors are perpendicular.
    
    For any vectors: dot product ≈ 0 means perpendicular
    
    Args:
        vector1: First direction vector
        vector2: Second direction vector
    
    Returns:
        True if dot_product is approximately zero (vectors are perpendicular)
    """
    # Compute dot product
    dot_product = vector1.dot(vector2)
    
    # Check if dot product is approximately zero
    return zero_test(dot_product)


# ============================================================================
# Orientation Class
# ============================================================================

@dataclass(frozen=True)
class Orientation:
    """
    Represents a 3D rotation using a 3x3 rotation matrix.
    Uses sympy for symbolic mathematics.
    I guess we never slerp and don't care about memory usage so apparently we're using matrices to implement this class.
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

    def flip(self, flip_x: bool = False, flip_y: bool = False, flip_z: bool = False) -> 'Orientation':
        """
        Return the orientation with the given axes flipped.
        """
        new_matrix = self.matrix.copy()
        if flip_x:
            new_matrix[0, :] = -new_matrix[0, :]
        if flip_y:
            new_matrix[:, 0] = -new_matrix[:, 0]
        if flip_z:
            new_matrix[:, 2] = -new_matrix[:, 2]
        return Orientation(new_matrix)
    
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
    
    # ========================================================================
    # TIMBER ORIENTATION METHODS
    # ========================================================================
    #
    # TODO prefix all these method with orient_timber_
    #
    # These methods provide orientations specifically for orienting timbers.
    # 
    # CANONICAL CONVENTIONS:
    # - facing_* methods: HORIZONTAL timbers with LENGTH along the horizontal plane
    #   and FACING (top) pointing up (+Z). The name indicates which direction the
    #   LENGTH axis points. Example: facing_east has Length pointing +X (east).
    # 
    # - pointing_* methods: Timbers with LENGTH pointing in the named direction.
    #   Example: pointing_up has Length pointing +Z (up), pointing_down has Length
    #   pointing -Z (down).
    #
    # COORDINATE SYSTEM (timber local space):
    # - Timber LENGTH runs along local +X axis (column 0 of rotation matrix)
    # - Timber WIDTH runs along local +Y axis (column 1 of rotation matrix)
    # - Timber HEIGHT/FACING runs along local +Z axis (column 2 of rotation matrix)
    # ========================================================================
    
    @classmethod
    def facing_west(cls) -> 'Orientation':
        """
        Horizontal timber with top face up.
        This is the IDENTITY orientation.
        
        - Length: +X (local) = -X (west) in global
        - Width: +Y (local) = -Y (south) in global
        - Facing: +Z (up)
        """
        return cls()  # Identity matrix
    
    @classmethod
    def facing_east(cls) -> 'Orientation':
        """
        Horizontal timber with top face up.
        180° rotation around Z axis from facing_west.
        
        - Length: +X (local) = +X (east) in global
        - Width: +Y (local) = +Y (north) in global  
        - Facing: +Z (up)
        """
        matrix = Matrix([
            [-1, 0, 0],
            [0, -1, 0],
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def facing_north(cls) -> 'Orientation':
        """
        Horizontal timber with top face up.
        90° counterclockwise rotation around Z axis from facing_west.
        
        - Length: +X (local) = +Y (north) in global
        - Width: +Y (local) = -X (west) in global
        - Facing: +Z (up)
        """
        matrix = Matrix([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def facing_south(cls) -> 'Orientation':
        """
        Horizontal timber with top face up.
        90° clockwise rotation around Z axis from facing_west.
        
        - Length: +X (local) = -Y (south) in global
        - Width: +Y (local) = +X (east) in global
        - Facing: +Z (up)
        """
        matrix = Matrix([
            [0, 1, 0],
            [-1, 0, 0],
            [0, 0, 1]
        ])
        return cls(matrix)
    
    @classmethod
    def pointing_up(cls) -> 'Orientation':
        """
        Vertical timber with LENGTH pointing upward (+Z).
        This is the same as pointing_forward.
        
        - Length (local +X) → +Z (up) in global
        - Width (local +Y) → +Y (north) in global
        - Facing (local +Z) → -X (west) in global
        """
        matrix = Matrix([
            [0, 0, -1],
            [0, 1, 0],
            [1, 0, 0]
        ])
        return cls(matrix)
    
    @classmethod
    def pointing_down(cls) -> 'Orientation':
        """
        Vertical timber with LENGTH pointing downward (-Z).
        
        - Length (local +X) → -Z (down) in global
        - Width (local +Y) → +Y (north) in global
        - Facing (local +Z) → +X (east) in global
        """
        matrix = Matrix([
            [0, 0, 1],
            [0, 1, 0],
            [-1, 0, 0]
        ])
        return cls(matrix)
    
    @classmethod
    def pointing_forward(cls) -> 'Orientation':
        """
        Vertical timber with LENGTH pointing upward (+Z).
        Identical to pointing_up.
        
        - Length (local +X) → +Z (up) in global
        - Width (local +Y) → +Y (north) in global
        - Facing (local +Z) → -X (west) in global
        """
        matrix = Matrix([
            [0, 0, -1],
            [0, 1, 0],
            [1, 0, 0]
        ])
        return cls(matrix)
    
    @classmethod
    def pointing_backward(cls) -> 'Orientation':
        """
        Vertical timber with LENGTH pointing upward (+Z), rotated 180° from pointing_forward.
        
        - Length (local +X) → +Z (up) in global
        - Width (local +Y) → -Y (south) in global
        - Facing (local +Z) → +X (east) in global
        """
        matrix = Matrix([
            [0, 0, 1],
            [0, -1, 0],
            [1, 0, 0]
        ])
        return cls(matrix)
    
    @classmethod
    def pointing_left(cls) -> 'Orientation':
        """
        Vertical timber with LENGTH pointing upward (+Z), rotated 90° CCW from pointing_forward.
        
        - Length (local +X) → +Z (up) in global
        - Width (local +Y) → -X (west) in global
        - Facing (local +Z) → -Y (south) in global
        """
        matrix = Matrix([
            [0, -1, 0],
            [0, 0, -1],
            [1, 0, 0]
        ])
        return cls(matrix)
    
    @classmethod
    def pointing_right(cls) -> 'Orientation':
        """
        Vertical timber with LENGTH pointing upward (+Z), rotated 90° CW from pointing_forward.
        
        - Length (local +X) → +Z (up) in global
        - Width (local +Y) → +X (east) in global
        - Facing (local +Z) → +Y (north) in global
        """
        matrix = Matrix([
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 0]
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

