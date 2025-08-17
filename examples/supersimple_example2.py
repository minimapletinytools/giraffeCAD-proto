#!/usr/bin/env python3
"""
Supersimple GiraffeCAD Example 2

Creates two 1-meter perpendicular timbers for mortise and tenon testing:
- Vertical timber facing up (Z direction)
- Horizontal timber facing forward (Y direction) positioned to intersect vertical
Plus a simple mortise and tenon joint connecting them.
"""

from giraffe import *

def create_supersimple_structure2() -> list[CutTimber]:
    """
    Create a supersimple structure with two perpendicular intersecting timbers for mortise and tenon testing.
    
    Returns:
        list[CutTimber]: List of CutTimber objects representing the structure
    """
    
    # Define timber sizes (all 4x4 inch posts converted to meters)
    INCH_TO_METER = 0.0254
    post_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)  # 4x4 inch
    
    # Create first timber - vertical (facing up)
    # Positioned at origin
    vertical_timber = create_timber(
        bottom_position=create_vector3d(0, 0, 0),           # At origin
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),          # Facing UP (vertical)
        face_direction=create_vector3d(1, 0, 0)             # Face oriented east
    )
    vertical_timber.name = "Vertical Timber"
    
    # Create second timber - horizontal (facing north)
    # Positioned to intersect the vertical timber at its midpoint
    horizontal_timber = create_timber(
        bottom_position=create_vector3d(0, -0.5, 0.5),     # Positioned to intersect vertical at mid-height
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(0, 1, 0),          # Facing FORWARD (north)
        face_direction=create_vector3d(0, 0, 1)             # Face oriented up
    )
    horizontal_timber.name = "Horizontal Timber"
    
    # Create CutTimber objects
    cut_vertical = CutTimber(vertical_timber)
    cut_horizontal = CutTimber(horizontal_timber)
    
    # Add a simple mortise and tenon joint between the two perpendicular timbers
    # Tenon dimensions
    tenon_thickness = 2 * INCH_TO_METER  # 2 inches = ~5cm
    tenon_length = 3 * INCH_TO_METER     # 3 inches = ~7.6cm  
    tenon_depth = 2 * INCH_TO_METER      # 2 inches = ~5cm
    
    # Create mortise and tenon joint: 
    # - horizontal timber gets tenon on its BOTTOM end (pointing toward vertical timber)
    # - vertical timber gets mortise on its FORWARD face (where horizontal intersects)
    joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=vertical_timber,      # Vertical timber gets the mortise
        tenon_timber=horizontal_timber,      # Horizontal timber gets the tenon
        tenon_end=TimberReferenceEnd.BOTTOM, # Tenon from bottom end of horizontal timber
        tenon_thickness=tenon_thickness,
        tenon_length=tenon_depth
    )
    joint.name = "Perpendicular Timber Joint"
    
    # Apply joint cuts to the timbers
    for timber, cuts in joint.timber_cuts:
        if timber == vertical_timber:
            cut_vertical.joints.extend(cuts)
        elif timber == horizontal_timber:
            cut_horizontal.joints.extend(cuts)
    
    return [cut_vertical, cut_horizontal]

def main():
    """Main function to demonstrate the supersimple structure with perpendicular intersecting timbers."""
    print("Creating supersimple structure 2 (perpendicular timbers with mortise and tenon)...")
    
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
    print("\nNote: This example demonstrates perpendicular intersecting timbers:")
    print("  - Vertical Timber: pointing up in Z direction")
    print("  - Horizontal Timber: pointing forward in Y direction, intersecting vertical") 
    print("  - Mortise and Tenon Joint: connects the two perpendicular timbers")
    
    return cut_timbers

if __name__ == "__main__":
    main() 