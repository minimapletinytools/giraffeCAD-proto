#!/usr/bin/env python3
"""
Debug script to test matrix creation logic outside of Fusion 360
"""

import sys
sys.path.insert(0, '.')

from supersimple_example3 import create_supersimple_structure3
from supersimple_example4 import create_supersimple_structure4
from sympy import Matrix
import numpy as np

def debug_matrix_creation(timber, name):
    """Debug the matrix creation process for a timber"""
    print(f"\n=== {name} ===")
    print(f"Position: {[float(timber.bottom_position[i]) for i in range(3)]}")
    print(f"Length dir: {[float(timber.length_direction[i]) for i in range(3)]}")
    print(f"Face dir: {[float(timber.face_direction[i]) for i in range(3)]}")
    print(f"Height dir: {[float(timber.height_direction[i]) for i in range(3)]}")
    
    # Recreate the matrix creation logic from giraffe_render_fusion360.py
    position_cm = Matrix([
        timber.bottom_position[0] * 100,
        timber.bottom_position[1] * 100,
        timber.bottom_position[2] * 100
    ])
    
    orientation = timber.orientation
    
    # Get the column vectors from the orientation matrix (same as giraffe_render_fusion360.py)
    face_dir = [float(orientation.matrix[0, 0]), float(orientation.matrix[1, 0]), float(orientation.matrix[2, 0])]
    height_dir = [float(orientation.matrix[0, 1]), float(orientation.matrix[1, 1]), float(orientation.matrix[2, 1])]
    length_dir = [float(orientation.matrix[0, 2]), float(orientation.matrix[1, 2]), float(orientation.matrix[2, 2])]
    
    # Extract translation values
    tx = float(position_cm[0])
    ty = float(position_cm[1])
    tz = float(position_cm[2])
    
    print(f"Matrix components:")
    print(f"  Face dir (X):   {face_dir}")
    print(f"  Height dir (Y): {height_dir}")
    print(f"  Length dir (Z): {length_dir}")
    print(f"  Translation:    [{tx:.3f}, {ty:.3f}, {tz:.3f}]")
    
    # Build the 4x4 transformation matrix (row-major order)
    matrix_4x4 = [
        [face_dir[0], height_dir[0], length_dir[0], tx],
        [face_dir[1], height_dir[1], length_dir[1], ty],
        [face_dir[2], height_dir[2], length_dir[2], tz],
        [0.0, 0.0, 0.0, 1.0]
    ]
    
    print(f"4x4 Transform Matrix:")
    for i, row in enumerate(matrix_4x4):
        print(f"  Row {i}: [{row[0]:8.3f}, {row[1]:8.3f}, {row[2]:8.3f}, {row[3]:8.3f}]")
    
    # Test a point transformation
    # Transform a point at the origin to see where it goes
    test_point = [0, 0, 0, 1]  # origin in homogeneous coordinates
    
    # Matrix multiplication: result = matrix * point
    result = [0, 0, 0, 0]
    for i in range(4):
        for j in range(4):
            result[i] += matrix_4x4[i][j] * test_point[j]
    
    print(f"Origin (0,0,0) transforms to: ({result[0]:.3f}, {result[1]:.3f}, {result[2]:.3f})")
    
    # Check if the rotation part is orthogonal
    rotation_3x3 = np.array([[face_dir[0], height_dir[0], length_dir[0]],
                            [face_dir[1], height_dir[1], length_dir[1]],
                            [face_dir[2], height_dir[2], length_dir[2]]])
    
    det = np.linalg.det(rotation_3x3)
    print(f"Rotation matrix determinant: {det:.6f} (should be ~1.0)")
    
    # Check orthogonality
    should_be_identity = np.dot(rotation_3x3, rotation_3x3.T)
    is_orthogonal = np.allclose(should_be_identity, np.eye(3), atol=1e-6)
    print(f"Rotation matrix is orthogonal: {is_orthogonal}")
    
    return matrix_4x4

def main():
    print("Debug: Matrix creation for working vs failing timbers")
    
    # Test example 3 (works)
    cut3 = create_supersimple_structure3()[0]
    timber3 = cut3.timber
    matrix3 = debug_matrix_creation(timber3, "SUPERSIMPLE_EXAMPLE3 (WORKS)")
    
    # Test example 4 (fails)
    cut4 = create_supersimple_structure4()[0] 
    timber4 = cut4.timber
    matrix4 = debug_matrix_creation(timber4, "SUPERSIMPLE_EXAMPLE4 (FAILS)")
    
    print(f"\n=== COMPARISON ===")
    print(f"Both matrices should be valid 4x4 transformation matrices.")
    print(f"If the matrices look correct, the issue might be in Fusion 360's API handling.")

if __name__ == "__main__":
    main() 