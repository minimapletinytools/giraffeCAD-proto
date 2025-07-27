#!/usr/bin/env python3
"""
Debug the orientation computation process
"""

import sys
sys.path.insert(0, '.')

from giraffe import *
from moothymoth import Orientation
import numpy as np

def debug_orientation_computation():
    """Debug the orientation computation in supersimple_example4"""
    
    # Recreate the same setup as supersimple_example4
    INCH_TO_METER = 0.0254
    post_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)
    
    # Create the same posts
    post1 = create_timber(
        bottom_position=create_vector3d(-0.5, 0, 0),
        length=1.0,
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),  # UP
        face_direction=create_vector3d(1, 0, 0)     # EAST
    )
    
    post2 = create_timber(
        bottom_position=create_vector3d(0.5, 0, 0),
        length=1.0,
        size=post_size,
        length_direction=create_vector3d(0, 1, 0),  # NORTH
        face_direction=create_vector3d(0, 0, 1)     # UP
    )
    
    print("=== POST ORIENTATIONS ===")
    print(f"Post1 (vertical):")
    print(f"  Length dir: {[float(post1.length_direction[i]) for i in range(3)]}")
    print(f"  Face dir:   {[float(post1.face_direction[i]) for i in range(3)]}")
    print(f"  Height dir: {[float(post1.height_direction[i]) for i in range(3)]}")
    
    print(f"Post2 (horizontal):")
    print(f"  Length dir: {[float(post2.length_direction[i]) for i in range(3)]}")
    print(f"  Face dir:   {[float(post2.face_direction[i]) for i in range(3)]}")
    print(f"  Height dir: {[float(post2.height_direction[i]) for i in range(3)]}")
    
    # Let's manually trace through what join_timbers does
    print(f"\n=== TRACING join_timbers COMPUTATION ===")
    
    # Get positions on timbers (same parameters as supersimple_example4)
    location_on_timber1 = 0.5
    location_on_timber2 = 0.5
    symmetric_stickout = 0.1
    
    pos1 = post1.get_position_on_timber(location_on_timber1)
    pos2 = post2.get_position_on_timber(location_on_timber2)
    
    print(f"pos1 (on vertical post): {[float(pos1[i]) for i in range(3)]}")
    print(f"pos2 (on horizontal post): {[float(pos2[i]) for i in range(3)]}")
    
    # Length direction calculation
    length_direction = normalize_vector(pos2 - pos1)
    print(f"length_direction (pos2 - pos1): {[float(length_direction[i]) for i in range(3)]}")
    
    # Face direction calculation (from join_timbers)
    face_direction = create_vector3d(0, 0, 1)  # Default up direction
    print(f"face_direction (default up): {[float(face_direction[i]) for i in range(3)]}")
    
    # Check if these are orthogonal
    dot_product = sum(float(length_direction[i]) * float(face_direction[i]) for i in range(3))
    print(f"Dot product (should be 0 for orthogonal): {dot_product:.6f}")
    
    # Now let's trace through _compute_orientation manually
    print(f"\n=== MANUAL _compute_orientation ===")
    
    # Normalize (they should already be normalized)
    length_norm = normalize_vector(length_direction)
    face_norm = normalize_vector(face_direction)
    
    print(f"length_norm: {[float(length_norm[i]) for i in range(3)]}")
    print(f"face_norm: {[float(face_norm[i]) for i in range(3)]}")
    
    # Cross product to get height
    height_norm = normalize_vector(cross_product(length_norm, face_norm))
    print(f"height_norm (length × face): {[float(height_norm[i]) for i in range(3)]}")
    
    # Check if this creates a valid orthogonal matrix
    rotation_matrix = Matrix([
        [face_norm[0], height_norm[0], length_norm[0]],
        [face_norm[1], height_norm[1], length_norm[1]],
        [face_norm[2], height_norm[2], length_norm[2]]
    ])
    
    print(f"Rotation matrix:")
    for i in range(3):
        row = [float(rotation_matrix[i, j]) for j in range(3)]
        print(f"  [{row[0]:8.6f}, {row[1]:8.6f}, {row[2]:8.6f}]")
    
    # Check determinant and orthogonality
    rot_np = np.array([[float(rotation_matrix[i, j]) for j in range(3)] for i in range(3)])
    det = np.linalg.det(rot_np)
    is_orthogonal = np.allclose(np.dot(rot_np, rot_np.T), np.eye(3), atol=1e-6)
    
    print(f"Determinant: {det:.6f} (should be ~1.0)")
    print(f"Is orthogonal: {is_orthogonal}")

if __name__ == "__main__":
    debug_orientation_computation() 