"""
supersimple_example3.py

Single timber with arbitrary rotation for testing Fusion 360 matrix issues.
"""

import sys
sys.path.insert(0, '.')

from giraffe import *
from moothymoth import Orientation

def create_supersimple_structure3():
    """
    Create a single timber rotated at a funny angle.
    
    Returns:
        List[CutTimber]: List containing one rotated timber
    """
    # Create a timber with an arbitrary rotation
    # Let's rotate 30 degrees around Z, then 45 degrees around the new Y
    
    # Start with identity orientation
    orientation = Orientation.identity()
    
    # Rotate 30 degrees around Z axis (yaw)
    from sympy import pi, cos, sin
    angle_z = pi / 6  # 30 degrees
    rotation_z = Orientation(Matrix([
        [cos(angle_z), -sin(angle_z), 0],
        [sin(angle_z), cos(angle_z), 0],
        [0, 0, 1]
    ]))
    
    # Rotate 45 degrees around Y axis (pitch)
    angle_y = pi / 4  # 45 degrees
    rotation_y = Orientation(Matrix([
        [cos(angle_y), 0, sin(angle_y)],
        [0, 1, 0],
        [-sin(angle_y), 0, cos(angle_y)]
    ]))
    
    # Combine the rotations: first Z, then Y
    final_orientation = rotation_y.multiply(rotation_z)
    
    # Extract the direction vectors from the final orientation
    length_direction = Matrix([final_orientation.matrix[0, 2], 
                              final_orientation.matrix[1, 2], 
                              final_orientation.matrix[2, 2]])
    width_direction = Matrix([final_orientation.matrix[0, 0], 
                            final_orientation.matrix[1, 0], 
                            final_orientation.matrix[2, 0]])
    
    # Create timber at origin with this orientation
    timber = Timber(
        bottom_position=create_vector3d(0, 0, 0),
        length_direction=length_direction,
        width_direction=width_direction,
        length=1.0,  # 1 meter long
        size=create_vector2d(0.1, 0.05)  # 10cm wide, 5cm thick
    )
    timber.name = "Funny Angle Timber"
    
    # Create a CutTimber with no cuts
    cut_timber = CutTimber(timber=timber)
    
    print(f"Created timber with orientation:")
    print(f"  Length direction: ({float(timber.length_direction[0]):.3f}, {float(timber.length_direction[1]):.3f}, {float(timber.length_direction[2]):.3f})")
    print(f"  Face direction:   ({float(timber.width_direction[0]):.3f}, {float(timber.width_direction[1]):.3f}, {float(timber.width_direction[2]):.3f})")
    print(f"  Height direction: ({float(timber.height_direction[0]):.3f}, {float(timber.height_direction[1]):.3f}, {float(timber.height_direction[2]):.3f})")
    
    return [cut_timber]

if __name__ == "__main__":
    cut_timbers = create_supersimple_structure3()
    print(f"Created {len(cut_timbers)} timber(s)") 