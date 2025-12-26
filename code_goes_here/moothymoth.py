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
from sympy import Matrix, cos, sin, pi
from typing import Optional, Union
from dataclasses import dataclass, field


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

