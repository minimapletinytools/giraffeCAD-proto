#!/usr/bin/env python3
"""
Supersimple GiraffeCAD Example 2

Creates two 1-meter posts with different orientations:
- One facing directly up (vertical)
- One facing directly forward (horizontal)
Separated by 1 meter left and right from midpoint, then joined with a connecting timber.
"""

from giraffe import *

def create_supersimple_structure2() -> list[CutTimber]:
    """
    Create a supersimple structure with two differently oriented posts and a connecting timber.
    
    Returns:
        list[CutTimber]: List of CutTimber objects representing the structure
    """
    
    # Define timber sizes (all 4x4 inch posts converted to meters)
    INCH_TO_METER = 0.0254
    post_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)  # 4x4 inch
    
    # Create first post - vertical (facing up)
    # Position: 0.5 meters to the left of center
    post1 = create_timber(
        bottom_position=create_vector3d(-0.5, 0, 0),        # Left of center
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),          # Facing UP (vertical)
        face_direction=create_vector3d(1, 0, 0)             # Face oriented east
    )
    post1.name = "Vertical Post"
    
    # Create second post - horizontal forward (facing north)
    # Position: 0.5 meters to the right of center
    post2 = create_timber(
        bottom_position=create_vector3d(0.5, 0, 0),         # Right of center
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(0, 1, 0),          # Facing FORWARD (north)
        face_direction=create_vector3d(0, 0, 1)             # Face oriented up
    )
    post2.name = "Horizontal Post"
    
    # Join the two posts with a connecting timber
    # Connect at mid-length of each post (0.5m along each)
    joining_timber = join_timbers(
        timber1=post1,
        timber2=post2,
        location_on_timber1=0.5,                           # Middle of vertical post (at 0.5m height)
        symmetric_stickout=0.1,                            # 10cm stickout on each end
        offset_from_timber1=0.0,                           # No offset from timber1's centerline
        location_on_timber2=0.5,                           # Middle of horizontal post (0.5m along its length)
    )
    joining_timber.name = "Connecting Timber"
    
    # Create CutTimber objects
    cut_post1 = CutTimber(post1)
    cut_post2 = CutTimber(post2)
    cut_joining = CutTimber(joining_timber)
    
    return [cut_post1, cut_post2, cut_joining]

def main():
    """Main function to demonstrate the supersimple structure with different orientations."""
    print("Creating supersimple structure 2 (different orientations)...")
    
    cut_timbers = create_supersimple_structure2()
    
    print(f"\nCreated supersimple structure 2 with {len(cut_timbers)} timbers:")
    for i, cut_timber in enumerate(cut_timbers, 1):
        timber = cut_timber.timber
        length_dir = timber.length_direction
        print(f"  {i}. {timber.name}:")
        print(f"     Length: {timber.length:.3f}m")
        print(f"     Size: ({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m)")
        print(f"     Position: ({float(timber.bottom_position[0]):.1f}, "
              f"{float(timber.bottom_position[1]):.1f}, "
              f"{float(timber.bottom_position[2]):.1f})")
        print(f"     Length Direction: ({float(length_dir[0]):.1f}, "
              f"{float(length_dir[1]):.1f}, "
              f"{float(length_dir[2]):.1f})")
    
    print(f"\nReturned {len(cut_timbers)} cut timbers ready for rendering.")
    print("\nNote: This example demonstrates different timber orientations:")
    print("  - Vertical Post: pointing up in Z direction")
    print("  - Horizontal Post: pointing forward in Y direction") 
    print("  - Connecting Timber: joins them at their midpoints")
    
    return cut_timbers

if __name__ == "__main__":
    main() 