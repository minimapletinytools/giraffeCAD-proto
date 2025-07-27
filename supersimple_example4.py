#!/usr/bin/env python3
"""
Supersimple GiraffeCAD Example 4

Renders ONLY the angled connecting timber from supersimple_example2
to isolate whether the multi-timber rendering is the issue.
"""

from giraffe import *

def create_supersimple_structure4() -> list[CutTimber]:
    """
    Create only the angled connecting timber from supersimple_example2.
    
    Returns:
        list[CutTimber]: List containing just the connecting timber
    """
    
    # Define timber sizes (same as supersimple_example2)
    INCH_TO_METER = 0.0254
    post_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)  # 4x4 inch
    
    # Recreate the same posts (needed for join_timbers calculation)
    # but we won't return them - just use them to create the joining timber
    
    # Create first post - vertical (facing up)
    post1 = create_timber(
        bottom_position=create_vector3d(-0.5, 0, 0),        # Left of center
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),          # Facing UP (vertical)
        face_direction=create_vector3d(1, 0, 0)             # Face oriented east
    )
    post1.name = "Vertical Post"
    
    # Create second post - horizontal forward (facing north)
    post2 = create_timber(
        bottom_position=create_vector3d(0.5, 0, 0),         # Right of center
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(0, 1, 0),          # Facing FORWARD (north)
        face_direction=create_vector3d(0, 0, 1)             # Face oriented up
    )
    post2.name = "Horizontal Post"
    
    # Join the two posts with a connecting timber (same parameters as supersimple_example2)
    joining_timber = join_timbers(
        timber1=post1,
        timber2=post2,
        location_on_timber1=0.5,                           # Middle of vertical post (at 0.5m height)
        symmetric_stickout=0.1,                            # 10cm stickout on each end
        offset_from_timber1=0.0,                           # No offset from timber1's centerline
        location_on_timber2=0.5,                           # Middle of horizontal post (0.5m along its length)
    )
    joining_timber.name = "Connecting Timber (Isolated)"
    
    # Create CutTimber object ONLY for the joining timber
    cut_joining = CutTimber(joining_timber)
    
    print(f"Created isolated connecting timber:")
    print(f"  Position: ({float(joining_timber.bottom_position[0]):.3f}, {float(joining_timber.bottom_position[1]):.3f}, {float(joining_timber.bottom_position[2]):.3f})")
    print(f"  Length direction: ({float(joining_timber.length_direction[0]):.3f}, {float(joining_timber.length_direction[1]):.3f}, {float(joining_timber.length_direction[2]):.3f})")
    print(f"  Face direction:   ({float(joining_timber.face_direction[0]):.3f}, {float(joining_timber.face_direction[1]):.3f}, {float(joining_timber.face_direction[2]):.3f})")
    print(f"  Height direction: ({float(joining_timber.height_direction[0]):.3f}, {float(joining_timber.height_direction[1]):.3f}, {float(joining_timber.height_direction[2]):.3f})")
    
    # Return ONLY the connecting timber
    return [cut_joining]

def main():
    """Main function to demonstrate the isolated connecting timber."""
    print("Creating isolated connecting timber (from supersimple_example2)...")
    
    cut_timbers = create_supersimple_structure4()
    
    print(f"\nCreated isolated connecting timber with {len(cut_timbers)} timber(s):")
    for i, cut_timber in enumerate(cut_timbers, 1):
        timber = cut_timber.timber
        length_dir = timber.length_direction
        print(f"  {i}. {timber.name}:")
        print(f"     Length: {timber.length:.3f}m")
        print(f"     Size: ({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m)")
        print(f"     Position: ({float(timber.bottom_position[0]):.3f}, "
              f"{float(timber.bottom_position[1]):.3f}, "
              f"{float(timber.bottom_position[2]):.3f})")
        print(f"     Length Direction: ({float(length_dir[0]):.3f}, "
              f"{float(length_dir[1]):.3f}, "
              f"{float(length_dir[2]):.3f})")
    
    print(f"\nThis timber should render at an angle if single-timber rendering works correctly.")
    
    return cut_timbers

if __name__ == "__main__":
    main() 