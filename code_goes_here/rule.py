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
from sympy import Matrix, cos, sin, pi, Float, Rational, Integer, Abs, S, sympify, Expr
from typing import Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import warnings


# ============================================================================
# Type Aliases
# ============================================================================

# Type aliases for vectors using sympy, these are just to provide some semantic 
# clarity in the interfaces and are not enforced by the type system.
V2 = Matrix  # 2D vector - 2x1 Matrix
V3 = Matrix  # 3D vector - 3x1 Matrix  
Direction3D = Matrix  # 3D direction vector - 3x1 Matrix

# TODO come up with a cute name for this or get rid of it
Numeric = Expr  # All numeric values must be SymPy expressions (use Integer for whole numbers, Rational for fractions)


# ============================================================================
# Safe SymPy Utilities - Timeout Protection & Complexity Detection
# ============================================================================

def is_complex_expr(expr) -> bool:
    """
    Detect if a SymPy expression is complex enough to potentially cause slow operations.
    
    Uses heuristics:
    - String length > 200 characters (very long expressions)
    - Node count > 100 in expression tree
    - Contains transcendental functions (sin, cos, exp, log)
    - Contains sqrt with string length > 100
    """
    from sympy import sin, cos, exp, log, sqrt
    
    if not hasattr(expr, 'has'):
        return False
    
    # Check for transcendental functions
    has_transcendental = any(expr.has(f) for f in [sin, cos, exp, log])
    if has_transcendental:
        return True
    
    # Check string length - very long expressions are always complex
    expr_str = str(expr)
    if len(expr_str) > 200:
        return True
    
    # Check for sqrt with long expressions
    if expr.has(sqrt) and len(expr_str) > 100:
        return True
    
    # Check node count in expression tree
    try:
        n_nodes = len(list(expr.preorder_traversal()))
        if n_nodes > 100:
            return True
    except:
        # If we can't traverse the tree but the expression is long, assume complex
        if len(expr_str) > 150:
            return True
    
    return False

def with_timeout_fallback(symbolic_func, numerical_func, timeout_seconds=0.1):
    """
    Execute symbolic_func with timeout, falling back to numerical_func if it takes too long.
    
    Args:
        symbolic_func: Callable that performs symbolic computation
        numerical_func: Callable that performs numerical fallback
        timeout_seconds: Timeout in seconds (default 0.1s)
    
    Returns:
        Result from symbolic_func or numerical_func
    """
    import signal
    
    class TimeoutException(Exception):
        pass
    
    def timeout_handler(signum, frame):
        raise TimeoutException()
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    
    try:
        result = symbolic_func()
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        return result
    except TimeoutException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        return numerical_func()
    except Exception as e:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        # For non-timeout exceptions, try numerical fallback
        try:
            return numerical_func()
        except:
            raise e  # Re-raise original exception if fallback also fails


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
            position=create_v3(Integer(0), Integer(0), Integer(0)),
            orientation=Orientation.identity()
        )
    
    # TODO consider renaming to do_transform
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
    
    # TODO consider renaming to undo_transform
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

    # TODO consider renaming to leave_parent_transform
    def to_global_transform(self, old_parent: 'Transform') -> 'Transform':
        """
        Convert this transform to global coordinates relative to a parent transform.
        """
        return old_parent * self

    def invert(self) -> 'Transform':
        """
        Return the inverse of this transform.
        
        For a transform T that converts local to global (global = T * local),
        the inverse converts global to local (local = T^-1 * global).
        """
        # Invert the orientation (transpose for rotation matrices)
        inv_orientation = self.orientation.invert()
        # Transform the position by the inverted orientation and negate
        inv_position = -(inv_orientation.matrix * self.position)
        return Transform(position=inv_position, orientation=inv_orientation)
    
    def __mul__(self, other: 'Transform') -> 'Transform':
        """
        Compose two transforms: result = self * other.
        
        This applies other first, then self.
        Equivalent to: global = self.local_to_global(other.local_to_global(local))
        """
        new_orientation = self.orientation * other.orientation
        new_position = self.orientation.matrix * other.position + self.position
        return Transform(position=new_position, orientation=new_orientation)
    
    # TODO consider renaming to become_child_transform
    def to_local_transform(self, new_parent: 'Transform') -> 'Transform':
        """
        Convert this transform to local coordinates relative to a parent transform.
        """
        return new_parent.invert() * self

# ============================================================================
# Safe SymPy Wrapper Functions - Protected Operations
# ============================================================================

def safe_norm(vec: Matrix):
    """
    Compute vector norm with timeout protection and numerical fallback.
    
    For simple expressions: Returns exact symbolic result
    For complex expressions: Freeze constants as Floats then lambdify
    """
    from sympy import sqrt, lambdify, Float, Number
    from fractions import Fraction
    
    def freeze_constants(expr, prec=53):
        """Replace all numeric constants with Float equivalents to avoid slow evaluation"""
        return expr.xreplace({
            n: Float(n, prec) for n in expr.atoms(Number)
        })
    
    def compute_numerical():
        """Compute norm numerically by freezing constants first, then lambdify"""
        try:
            norm_squared = 0.0
            for c in vec:
                # Get free symbols (should be empty for closed-form expressions)
                syms = list(c.free_symbols)
                if syms:
                    # Has free symbols, can't evaluate numerically
                    return Integer(1)
                else:
                    # Freeze all constants to Float first - this avoids slow symbolic evaluation
                    c_frozen = freeze_constants(c, prec=15)
                    # Now lambdify should be fast since all constants are already floats
                    f = lambdify((), c_frozen, modules=['math'])
                    val = float(f())
                norm_squared += val ** 2
            
            return sqrt(Rational(norm_squared).limit_denominator(10**9))
        except Exception:
            # Fallback: assume unit vector
            return Integer(1)
    
    # Quick check: if vector contains complex expressions, go straight to numerical
    is_complex = any(is_complex_expr(component) for component in vec)
    
    if is_complex:
        # For complex expressions, freeze constants then lambdify
        # This avoids SymPy's slow symbolic evaluation entirely
        return compute_numerical()
    
    # Try symbolic norm with timeout, fall back to numerical if it times out
    def symbolic():
        return vec.norm()
    
    return with_timeout_fallback(symbolic, compute_numerical, timeout_seconds=0.1)

def safe_det(matrix: Matrix):
    """
    Compute matrix determinant with timeout protection.
    """
    # Check if matrix contains complex expressions
    is_complex = any(is_complex_expr(elem) for elem in matrix)
    
    if is_complex:
        return matrix.det().evalf()
    
    def symbolic():
        return matrix.det()
    
    def numerical():
        return matrix.det().evalf()
    
    return with_timeout_fallback(symbolic, numerical, timeout_seconds=0.2)

def safe_simplify(expr, timeout_seconds=0.5):
    """
    Simplify with timeout protection.
    """
    from sympy import simplify as sp_simplify
    
    if is_complex_expr(expr):
        # Don't even try to simplify complex expressions
        return expr
    
    def symbolic():
        return sp_simplify(expr)
    
    def numerical():
        return expr  # Return original if simplification times out
    
    return with_timeout_fallback(symbolic, numerical, timeout_seconds)

class Comparison(Enum):
    """Enum for safe comparison operations"""
    GT = ">"      # Greater than
    LT = "<"      # Less than
    GE = ">="     # Greater than or equal
    LE = "<="     # Less than or equal
    EQ = "=="     # Equal
    NE = "!="     # Not equal

def safe_compare(expr, comparison: Comparison):
    """
    Safely evaluate a comparison by freezing constants first.
    
    Args:
        expr: SymPy expression to compare against zero
        comparison: Comparison enum value (e.g., Comparison.GT for > 0)
    
    Returns:
        Boolean result of the comparison with zero
    """
    from sympy import Float, Number, lambdify
    
    def freeze_constants(e, prec=53):
        """Replace all numeric constants with Float equivalents"""
        return e.xreplace({
            n: Float(n, prec) for n in e.atoms(Number)
        })
    
    def apply_comparison(val: float, comp: Comparison) -> bool:
        """Apply comparison operation to a float value"""
        if comp == Comparison.GT:
            return val > 0
        elif comp == Comparison.LT:
            return val < 0
        elif comp == Comparison.GE:
            return val >= 0
        elif comp == Comparison.LE:
            return val <= 0
        elif comp == Comparison.EQ:
            return abs(val) < 1e-10
        elif comp == Comparison.NE:
            return abs(val) >= 1e-10
        else:
            raise ValueError(f"Unknown comparison: {comp}")
    
    # For complex expressions, freeze constants and evaluate numerically
    if is_complex_expr(expr):
        try:
            # Freeze constants first
            expr_frozen = freeze_constants(expr, prec=15)
            # Convert to numerical function
            f = lambdify((), expr_frozen, modules=['math'])
            val = float(f())
            return apply_comparison(val, comparison)
        except Exception:
            # If anything fails, default to False for safety
            return False
    
    # For simple expressions, use direct comparison
    try:
        if comparison == Comparison.GT:
            return bool(expr > 0)
        elif comparison == Comparison.LT:
            return bool(expr < 0)
        elif comparison == Comparison.GE:
            return bool(expr >= 0)
        elif comparison == Comparison.LE:
            return bool(expr <= 0)
        elif comparison == Comparison.EQ:
            return bool(expr == 0)
        elif comparison == Comparison.NE:
            return bool(expr != 0)
        else:
            raise ValueError(f"Unknown comparison: {comparison}")
    except:
        # Fallback to numerical evaluation with freeze_constants
        try:
            expr_frozen = freeze_constants(expr, prec=15)
            f = lambdify((), expr_frozen, modules=['math'])
            val = float(f())
            return apply_comparison(val, comparison)
        except:
            return False

def safe_dot_product(vec1: Matrix, vec2: Matrix):
    """
    Safely compute dot product (vec1.T * vec2)[0, 0].
    Bypasses SymPy's matrix multiplication entirely to avoid property checking freezes.
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Scalar result of dot product
    """
    from sympy import Float, Number
    
    # Check if we need to use numerical evaluation
    has_complex = (any(is_complex_expr(elem) for elem in vec1) or 
                   any(is_complex_expr(elem) for elem in vec2))
    
    if has_complex:
        # Freeze constants in both vectors
        def freeze_elem(e):
            if not hasattr(e, 'atoms'):
                return e
            return e.xreplace({n: Float(n, 15) for n in e.atoms(Number)})
        
        vec1_frozen = [freeze_elem(e) for e in vec1]
        vec2_frozen = [freeze_elem(e) for e in vec2]
        
        # Compute dot product manually to bypass SymPy's matrix multiplication
        result = sum(v1 * v2 for v1, v2 in zip(vec1_frozen, vec2_frozen))
        return result
    
    # For simple expressions, use standard approach but still compute manually
    result = sum(v1 * v2 for v1, v2 in zip(vec1, vec2))
    return result


def safe_transform_vector(matrix: Matrix, vector: Matrix) -> Matrix:
    """
    Safely compute matrix * vector (or matrix * matrix) transformation.
    Always uses manual multiplication to completely avoid SymPy's property checking.
    
    Args:
        matrix: Left matrix
        vector: Right matrix (can be a column vector or another matrix)
    
    Returns:
        Result of matrix multiplication
    """
    from sympy import Float, Number
    
    # Check if we need to freeze constants
    has_complex = (any(is_complex_expr(elem) for elem in matrix) or 
                   any(is_complex_expr(elem) for elem in vector))
    
    # Prepare data - freeze if complex
    def freeze_elem(e):
        if not hasattr(e, 'atoms'):
            return e
        return e.xreplace({n: Float(n, 15) for n in e.atoms(Number)})
    
    if has_complex:
        mat_data = [[freeze_elem(matrix[i, j]) for j in range(matrix.cols)] for i in range(matrix.rows)]
        vec_data = [[freeze_elem(vector[i, j]) for j in range(vector.cols)] for i in range(vector.rows)]
    else:
        mat_data = [[matrix[i, j] for j in range(matrix.cols)] for i in range(matrix.rows)]
        vec_data = [[vector[i, j] for j in range(vector.cols)] for i in range(vector.rows)]
    
    # ALWAYS compute manually to avoid SymPy's matrix multiplication property checking
    # Handle both matrix-vector (Nx1) and matrix-matrix (NxM) multiplication
    result = []
    for i in range(len(mat_data)):
        row = []
        for k in range(len(vec_data[0])):  # Iterate over columns of second matrix
            elem = sum(mat_data[i][j] * vec_data[j][k] for j in range(len(vec_data)))
            row.append(elem)
        result.append(row)
    
    # If result is a single column, return as column vector
    if len(result[0]) == 1:
        return Matrix([row[0] for row in result])
    else:
        return Matrix(result)

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
    """Normalize a vector using safe norm computation with numerical fallback"""
    from sympy import sqrt
    from fractions import Fraction
    
    # Use safe norm
    norm = safe_norm(vec)
    
    if zero_test(norm):
        return vec
    
    # Check if we got a Float result (needs conversion to rational)
    # For symbolic expressions like sqrt(3) or Rational values, use exact division
    if isinstance(norm, Float):
        # Normalize numerically and convert to rationals
        norm_val = float(norm)
        if abs(norm_val) < 1e-15:
            return vec
        
        normalized = []
        for component in vec:
            comp_val = float(component.evalf()) / norm_val
            frac = Fraction(comp_val).limit_denominator(10**9)
            normalized.append(Rational(frac.numerator, frac.denominator))
        return Matrix(normalized)
    
    # For symbolic expressions (sqrt, Rational, Integer), use exact symbolic division
    return vec / norm

def cross_product(v1: V3, v2: V3) -> V3:
    """Calculate cross product of two 3D vectors"""
    return Matrix([
        v1[1]*v2[2] - v1[2]*v2[1],
        v1[2]*v2[0] - v1[0]*v2[2], 
        v1[0]*v2[1] - v1[1]*v2[0]
    ])

def vector_magnitude(vec: Matrix):
    """Calculate magnitude of a vector using safe norm computation"""
    return safe_norm(vec)


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

# maybe rename to zero_test_with_fuzzy_fallback
def zero_test(value) -> bool:
    """
    Test if a value is zero using SymPy's equals() method or float comparison.
    
    Args:
        value: The value to test (SymPy expression, Rational, Float, or numeric)
    
    Returns:
        True if value is either exactly zero or approximately zero if symbolic check fails.
    
    """
    return equality_test(value, 0)


# maybe rename to equality_test_with_fuzzy_fallback
def equality_test(value, expected) -> bool:
    """
    Test if a value equals an expected value using SymPy's equals() method or float comparison.
    
    Args:
        value: The value to test (SymPy expression, Rational, Float, or numeric)
        expected: The expected value to compare against
    
    Returns:
        True if value is (approximately) equal to expected
    
    Behavior:
    - If value or expected contains Float: Use epsilon comparison (SYMPY_EXPR_EPSILON)
    - If both have .equals() method: Try exact symbolic comparison with timeout
    - If symbolic check times out or returns None: Fall back to numerical comparison
    - For plain floats/ints: Use epsilon comparison (SYMPY_EXPR_EPSILON)
    """
    
    # Check if either value contains Float components
    has_float = False
    if hasattr(value, 'has') and value.has(Float):
        has_float = True
    if hasattr(expected, 'has') and expected.has(Float):
        has_float = True
    if has_float:
        return Abs(value - expected) < EPSILON_GENERIC
    
    # Try SymPy exact equality for symbolic/Rational values
    # For now, skip symbolic comparison entirely and use numerical to avoid freezes
    # TODO: Implement proper timeout that works with SymPy's internal operations
    if hasattr(value, 'equals') and hasattr(expected, 'equals'):
        # Fall back to numerical comparison using evalf()
        numerical_diff = Abs((value - expected).evalf())
        return numerical_diff < SYMPY_EXPR_EPSILON
    
    # should never reach here?
    return Abs(value - expected) < SYMPY_EXPR_EPSILON


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
        
    
    # TODO change veeryhting below to static methods....
    # Static constants for cardinal directions
    @classmethod
    def identity(cls) -> 'Orientation':
        """Identity orientation - facing east (+X)"""
        return cls()

    @classmethod
    def from_z_and_y(cls, z_direction: Direction3D, y_direction: Direction3D) -> 'Orientation':
        """
        Create an Orientation from z and y direction vectors.
        Computes x = y × z to complete the right-handed coordinate system.
        """
        x_direction = cross_product(y_direction, z_direction)
        return cls(Matrix([
            [x_direction[0], y_direction[0], z_direction[0]],
            [x_direction[1], y_direction[1], z_direction[1]],
            [x_direction[2], y_direction[2], z_direction[2]]
        ]))
    
    @classmethod
    def from_z_and_x(cls, z_direction: Direction3D, x_direction: Direction3D) -> 'Orientation':
        """
        Create an Orientation from z and x direction vectors.
        Computes y = z × x to complete the right-handed coordinate system.
        """
        y_direction = cross_product(z_direction, x_direction)
        return cls(Matrix([
            [x_direction[0], y_direction[0], z_direction[0]],
            [x_direction[1], y_direction[1], z_direction[1]],
            [x_direction[2], y_direction[2], z_direction[2]]
        ]))
    
    @classmethod
    def from_x_and_y(cls, x_direction: Direction3D, y_direction: Direction3D) -> 'Orientation':
        """
        Create an Orientation from x and y direction vectors.
        Computes z = x × y to complete the right-handed coordinate system.
        """
        z_direction = cross_product(x_direction, y_direction)
        return cls(Matrix([
            [x_direction[0], y_direction[0], z_direction[0]],
            [x_direction[1], y_direction[1], z_direction[1]],
            [x_direction[2], y_direction[2], z_direction[2]]
        ]))
            
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
