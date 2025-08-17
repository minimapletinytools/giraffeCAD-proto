#!/usr/bin/env python3
"""
Supersimple GiraffeCAD Example

Creates two 1-meter vertical posts separated by 2 meters on the X axis,
connected by a horizontal beam in the middle.
"""

from giraffe import *

def create_supersimple_structure() -> list[CutTimber]:
    """
    Create a supersimple structure with two posts and a connecting beam.
    
    Returns:
        list[CutTimber]: List of CutTimber objects representing the structure
    """
    
    # Define timber sizes (all 4x4 inch posts converted to meters)
    INCH_TO_METER = 0.0254
    post_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)  # 4x4 inch
    beam_size = create_vector2d(4 * INCH_TO_METER, 6 * INCH_TO_METER)  # 4x6 inch
    
    # Create first post at origin
    post1 = create_timber(
        bottom_position=create_vector3d(0, 0, 0),           # At origin
        length=1.0,                                         # 1 meter tall
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),          # Vertical (up in Z)
        face_direction=create_vector3d(1, 0, 0)             # Facing east (X direction)
    )
    post1.name = "Post 1"
    
    # Create second post 2 meters away on X axis
    post2 = create_timber(
        bottom_position=create_vector3d(2, 0, 0),           # 2 meters on X axis
        length=1.0,                                         # 1 meter tall
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),          # Vertical (up in Z)
        face_direction=create_vector3d(1, 0, 0)             # Facing east (X direction)
    )
    post2.name = "Post 2"
    
    # Create horizontal beam connecting the posts at mid-height (0.5m)
    beam = create_timber(
        bottom_position=create_vector3d(0, 0, 0.5),         # Start at post1, mid-height
        length=2.0,                                         # 2 meters long (distance between posts)
        size=beam_size,
        length_direction=create_vector3d(1, 0, 0),          # Horizontal in X direction
        face_direction=create_vector3d(0, 0, 1)             # Facing up (Z direction)
    )
    beam.name = "Connecting Beam"
    
    # Create CutTimber objects (no joints in this simple example)
    cut_post1 = CutTimber(post1)
    cut_post2 = CutTimber(post2)
    cut_beam = CutTimber(beam)
    
    return [cut_post1, cut_post2, cut_beam]

def main():
    """Main function to demonstrate the supersimple structure."""
    print("Creating supersimple structure...")
    
    cut_timbers = create_supersimple_structure()
    
    print(f"\nCreated supersimple structure with {len(cut_timbers)} timbers:")
    for i, cut_timber in enumerate(cut_timbers, 1):
        timber = cut_timber.timber
        print(f"  {i}. {timber.name}: length={timber.length:.3f}m, "
              f"size=({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m), "
              f"position=({float(timber.bottom_position[0]):.1f}, "
              f"{float(timber.bottom_position[1]):.1f}, "
              f"{float(timber.bottom_position[2]):.1f})")
    
    print(f"\nReturned {len(cut_timbers)} cut timbers ready for rendering.")
    return cut_timbers

if __name__ == "__main__":
    main() 