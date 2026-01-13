"""
Japanese Joints Examples - Lapped Gooseneck Joint (腰掛鎌継ぎ / Koshikake Kama Tsugi)

This example demonstrates a traditional Japanese timber joint that splices two beams end-to-end.
The gooseneck profile provides mechanical interlock while the lap provides bearing surface.
"""

from giraffe import *


def create_lapped_gooseneck_splice_example():
    """
    Create a lapped gooseneck joint splicing two 4"x4" timbers, each 3 feet long.
    
    This is a traditional Japanese joint used to extend beams. The gooseneck profile
    creates a mechanical interlock that resists tension, while the lap provides
    compression bearing surface.
    """
    
    # Timber dimensions
    timber_width = inches(4)      # 4 inches
    timber_height = inches(4)     # 4 inches
    timber_length = inches(36)    # 3 feet = 36 inches
    
    # Create first timber (gooseneck timber)
    # This will have the gooseneck feature protruding from it
    gooseneck_timber = timber_from_directions(
        length=timber_length,
        size=create_v2(timber_width, timber_height),
        bottom_position=create_v3(0, 0, 0),
        length_direction=create_v3(1, 0, 0),  # Pointing east along X-axis
        width_direction=create_v3(0, 1, 0),   # Width along Y-axis (north)
        name="gooseneck_timber"
    )
    
    # Create second timber (receiving timber)
    # This will have a pocket cut to receive the gooseneck
    # Position it so its bottom end meets the top end of the gooseneck timber
    receiving_timber = timber_from_directions(
        length=timber_length,
        size=create_v2(timber_width, timber_height),
        bottom_position=create_v3(timber_length, 0, 0),  # Start where first timber ends
        length_direction=create_v3(1, 0, 0),   # Also pointing east
        width_direction=create_v3(0, 1, 0),
        name="receiving_timber"
    )
    
    # Joint parameters - scaled appropriately for 4"x4" timber
    gooseneck_length = inches(6)          # Length of the gooseneck profile
    gooseneck_small_width = inches(1)     # Narrow end of the taper
    gooseneck_large_width = inches(2.5)   # Wide end of the taper  
    gooseneck_head_length = inches(1.5)   # Length of the head/hook portion
    lap_length = inches(3)                # Length of the lap overlap
    gooseneck_depth = inches(1.5)         # How deep the gooseneck cuts into the timber
    
    # Create the lapped gooseneck joint
    joint = cut_lapped_gooseneck_joint(
        gooseneck_timber=gooseneck_timber,
        receiving_timber=receiving_timber,
        receiving_timber_end=TimberReferenceEnd.BOTTOM,  # Cut on the bottom end of receiving timber
        gooseneck_timber_face=TimberReferenceLongFace.FRONT,  # Gooseneck visible on front face
        gooseneck_length=gooseneck_length,
        gooseneck_small_width=gooseneck_small_width,
        gooseneck_large_width=gooseneck_large_width,
        gooseneck_head_length=gooseneck_head_length,
        lap_length=lap_length,
        gooseneck_depth=gooseneck_depth,
        gooseneck_lateral_offset=Rational(0)  # Centered on the timber
    )
    
    # Create a frame from the joint
    frame = Frame.from_joints(
        [joint],
        name="Lapped Gooseneck Splice Example"
    )
    
    return frame


def create_simple_gooseneck_example():
    """
    Create a simpler example with smaller dimensions for easier visualization.
    """
    
    # Smaller timber dimensions for testing
    timber_width = inches(3)
    timber_height = inches(3)
    timber_length = inches(24)  # 2 feet
    
    # Create first timber
    gooseneck_timber = timber_from_directions(
        length=timber_length,
        size=create_v2(timber_width, timber_height),
        bottom_position=create_v3(0, 0, 0),
        length_direction=create_v3(0, 0, 1),  # Vertical
        width_direction=create_v3(1, 0, 0),
        name="post_1"
    )
    
    # Create second timber above the first
    receiving_timber = timber_from_directions(
        length=timber_length,
        size=create_v2(timber_width, timber_height),
        bottom_position=create_v3(0, 0, timber_length),
        length_direction=create_v3(0, 0, 1),  # Also vertical
        width_direction=create_v3(1, 0, 0),
        name="post_2"
    )
    
    # Smaller joint parameters for the smaller timber
    joint = cut_lapped_gooseneck_joint(
        gooseneck_timber=gooseneck_timber,
        receiving_timber=receiving_timber,
        receiving_timber_end=TimberReferenceEnd.BOTTOM,
        gooseneck_timber_face=TimberReferenceLongFace.RIGHT,
        gooseneck_length=inches(4),
        gooseneck_small_width=inches("0.75"),
        gooseneck_large_width=inches(2),
        gooseneck_head_length=inches(1),
        lap_length=inches(2),
        gooseneck_depth=inches(1)
    )
    
    frame = Frame.from_joints(
        [joint],
        name="Simple Vertical Post Splice"
    )
    
    return frame


if __name__ == "__main__":
    print("Creating Japanese Lapped Gooseneck Joint Examples...")
    print("=" * 70)
    
    # Create the main example
    print("\n1. Creating 4\"x4\" x 3' timber splice with lapped gooseneck joint...")
    frame1 = create_lapped_gooseneck_splice_example()
    print(f"   Frame created: {frame1.name}")
    print(f"   Number of timbers: {len(frame1.cut_timbers)}")
    for timber in frame1.cut_timbers:
        print(f"   - {timber.name}: {len(timber.cuts)} cut(s)")
    
    # Create the simpler example
    print("\n2. Creating simplified vertical post splice example...")
    frame2 = create_simple_gooseneck_example()
    print(f"   Frame created: {frame2.name}")
    print(f"   Number of timbers: {len(frame2.cut_timbers)}")
    for timber in frame2.cut_timbers:
        print(f"   - {timber.name}: {len(timber.cuts)} cut(s)")
    
    print("\n" + "=" * 70)
    print("Examples created successfully!")
    print("\nThese examples demonstrate the traditional Japanese lapped gooseneck joint")
    print("(腰掛鎌継ぎ / Koshikake Kama Tsugi) used to splice beams end-to-end.")
    print("\nThe gooseneck profile creates a mechanical interlock that resists pulling")
    print("apart, while the lap provides additional bearing surface for compression.")
