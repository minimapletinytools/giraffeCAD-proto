#!/usr/bin/env python3
"""
Supersimple GiraffeCAD Example 5

Creates three 1-meter timbers for advanced mortise and tenon testing:
- Vertical timber (post) in the middle facing up (Z direction)
- Horizontal timber at the bottom with mortise to receive vertical post
- Horizontal timber at the top with mortise to receive vertical post

The vertical post connects into mortises on both the top and bottom horizontal pieces.
"""

from giraffe import *

def create_supersimple_structure5() -> list[CutTimber]:
    """
    Create a supersimple structure with three timbers: a vertical post connecting 
    into mortises on top and bottom horizontal pieces.
    
    Returns:
        list[CutTimber]: List of CutTimber objects representing the structure
    """
    
    # Define timber sizes (all 4x4 inch posts converted to meters)
    INCH_TO_METER = 0.0254
    post_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)  # 4x4 inch
    
    # Step 1: Create bottom horizontal timber first
    # Positioned at origin level
    bottom_timber = create_timber(
        bottom_position=create_vector3d(-0.5, 0, 0),        # Centered at origin
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(1, 0, 0),          # Facing EAST (horizontal)
        face_direction=create_vector3d(0, 1, 0)             # Face oriented north
    )
    bottom_timber.name = "Bottom Horizontal Timber"
    
    # Step 2: Create top horizontal timber second
    # Positioned at the top level
    top_timber = create_timber(
        bottom_position=create_vector3d(-0.5, 0, 0.9),      # 90cm above origin (above vertical post)
        length=1.0,                                         # 1 meter long
        size=post_size,
        length_direction=create_vector3d(1, 0, 0),          # Facing EAST (horizontal)
        face_direction=create_vector3d(0, 1, 0)             # Face oriented north
    )
    top_timber.name = "Top Horizontal Timber"
    
    # Step 3: Create joint timbers list for the horizontal pieces
    horizontal_timbers = [bottom_timber, top_timber]
    
    # Step 4: Create vertical timber (post) that intersects the middle
    # Positioned so it extends from the top of bottom piece to bottom of top piece
    vertical_timber = create_timber(
        bottom_position=create_vector3d(0, 0, 0),        
        length=0.9,                                         # 80cm long (fits between top and bottom pieces)
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),          # Facing UP (vertical)
        face_direction=create_vector3d(1, 0, 0)             # Face oriented east
    )
    vertical_timber.name = "Vertical Post"
    
    # Step 5: Create CutTimber objects
    cut_vertical = CutTimber(vertical_timber)
    cut_bottom = CutTimber(bottom_timber)
    cut_top = CutTimber(top_timber)
    
    # Step 6: Use joint function to create connections between vertical and horizontal timbers
    # Mortise dimensions (slightly larger than post to allow insertion)
    mortise_width = 2 * INCH_TO_METER   # 2 inches wide
    mortise_height = 2 * INCH_TO_METER  # 2 inches high
    mortise_depth = 2 * INCH_TO_METER   # 2 inches deep
    
    # Create mapping of timbers to their CutTimber objects for helper function
    cut_timber_map = {
        bottom_timber: cut_bottom,
        top_timber: cut_top,
        vertical_timber: cut_vertical
    }
    
    # Step 7: Create joints and apply using helper function
    # Create joint between vertical post and bottom horizontal timber
    bottom_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=bottom_timber,               # Bottom timber gets the mortise
        tenon_timber=vertical_timber,               # Vertical timber acts as tenon
        tenon_end=TimberReferenceEnd.BOTTOM,        # Bottom end of vertical timber
        tenon_thickness=mortise_width,              # Match mortise width
        tenon_length=mortise_depth                 # Tenon length (mortise depth = tenon length)
    )
    bottom_joint.name = "Bottom Joint (Vertical to Bottom Horizontal)"
    
    # Apply bottom joint cuts using helper function
    apply_joint_to_cut_timbers(bottom_joint, cut_timber_map)
    
    # Create joint between vertical post and top horizontal timber
    top_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=top_timber,                  # Top timber gets the mortise
        tenon_timber=vertical_timber,               # Vertical timber acts as tenon
        tenon_end=TimberReferenceEnd.TOP,           # Top end of vertical timber
        tenon_thickness=mortise_width,              # Match mortise width
        tenon_length=mortise_depth                 # Tenon length (mortise depth = tenon length)
    )
    top_joint.name = "Top Joint (Vertical to Top Horizontal)"
    
    # Apply top joint cuts using helper function
    apply_joint_to_cut_timbers(top_joint, cut_timber_map)
    
    return [cut_vertical, cut_bottom, cut_top]

def main():
    """Main function to demonstrate the supersimple structure with vertical post and mortised horizontals."""
    print("Creating supersimple structure 5 (vertical post with top and bottom mortised horizontals)...")
    
    cut_timbers = create_supersimple_structure5()
    
    print(f"\nCreated supersimple structure 5 with {len(cut_timbers)} timbers:")
    for i, cut_timber in enumerate(cut_timbers, 1):
        timber = cut_timber.timber
        length_dir = timber.length_direction
        joint_count = len(cut_timber.joints)
        print(f"  {i}. {timber.name}:")
        print(f"     Length: {timber.length:.3f}m")
        print(f"     Size: ({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m)")
        print(f"     Position: ({float(timber.bottom_position[0]):.1f}, "
              f"{float(timber.bottom_position[1]):.1f}, "
              f"{float(timber.bottom_position[2]):.1f})")
        print(f"     Length Direction: ({float(length_dir[0]):.1f}, "
              f"{float(length_dir[1]):.1f}, "
              f"{float(length_dir[2]):.1f})")
        print(f"     Joints: {joint_count} cut operations")
    
    print(f"\nReturned {len(cut_timbers)} cut timbers ready for rendering.")
    print("\nNote: This example demonstrates a vertical post with mortised connections:")
    print("  - Vertical Post: pointing up in Z direction, positioned between horizontals")
    print("  - Bottom Horizontal: with mortise on TOP face to receive vertical post") 
    print("  - Top Horizontal: with mortise on BOTTOM face to receive vertical post")
    print("  - The vertical post should fit into both mortises when assembled")
    
    return cut_timbers

if __name__ == "__main__":
    main()
