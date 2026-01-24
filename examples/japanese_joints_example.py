"""
Japanese Joints Examples

This module demonstrates traditional Japanese timber joints:
- Lapped Gooseneck Joint (腰掛鎌継ぎ / Koshikake Kama Tsugi) - for splicing beams end-to-end
- Dovetail Butt Joint (蟻仕口 / Ari Shiguchi) - for connecting timbers at right angles

Each function creates and returns a Frame object with the joint example.
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
    # For a splice joint, timbers point opposite directions
    # Position so gooseneck TOP (at 36") overlaps with receiving BOTTOM
    # Receiving BOTTOM at 30" creates 6" of overlap (receiving extends from 30" to -6")
    receiving_timber = timber_from_directions(
        length=timber_length,
        size=create_v2(timber_width, timber_height),
        bottom_position=create_v3(timber_length - inches(6), 0, 0),  # BOTTOM at 30" for 6" overlap
        length_direction=create_v3(-1, 0, 0),  # Pointing west (opposite of gooseneck)
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
        name="gooseneck_timber"
    )
    
    # Create second timber above the first
    receiving_timber = timber_from_directions(
        length=timber_length,
        size=create_v2(timber_width, timber_height),
        bottom_position=create_v3(0, 0, timber_length),
        length_direction=create_v3(0, 0, 1),  # Also vertical
        width_direction=create_v3(1, 0, 0),
        name="receiving_timber"
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


def create_dovetail_butt_joint_example():
    """
    Create a dovetail butt joint (蟻仕口 / Ari Shiguchi) connecting two 4"x4" x 3' timbers at right angles.
    
    This is a traditional Japanese joint where a dovetail-shaped tenon on one timber
    fits into a matching dovetail socket on another timber. The dovetail shape provides
    mechanical resistance to pulling apart.
    
    Configuration:
        - Receiving timber: 4"x4" x 3', vertical
        - Dovetail timber: 4"x4" x 3', horizontal, butts against center of receiving timber
        - Creates a T-joint connection
    
    Visual layout (side view):
                   |
                   |  Receiving Timber (vertical)
                   |
        =====[dovetail tenon]  Dovetail Timber (horizontal)
                   |
                   |
    """
    
    # Timber dimensions
    timber_size = create_v2(inches(4), inches(4))  # 4" x 4"
    timber_length = feet(3)  # 3 feet
    
    # Create vertical receiving timber
    # This timber runs vertically and will have the dovetail socket cut into it
    receiving_timber = timber_from_directions(
        length=timber_length,
        size=timber_size,
        bottom_position=create_v3(0, 0, 0),
        length_direction=create_v3(0, 0, 1),  # Vertical (Z-axis)
        width_direction=create_v3(1, 0, 0),   # Width along X-axis
        name="receiving_timber"
    )
    
    # Create horizontal dovetail timber
    # This timber runs horizontally and will have the dovetail tenon cut on its end
    # Position it so it butts against the center of the receiving timber
    receiving_center_height = timber_length / Rational(2)
    
    dovetail_timber = timber_from_directions(
        length=timber_length,
        size=timber_size,
        bottom_position=create_v3(0, inches(4), receiving_center_height),  # Start 4" away (timber width)
        length_direction=create_v3(0, -1, 0),  # Pointing toward receiving timber (negative Y)
        width_direction=create_v3(1, 0, 0),    # Width along X-axis
        name="dovetail_timber"
    )
    
    # Joint parameters
    dovetail_length = inches(3)                  # 3 inch long dovetail tenon
    dovetail_small_width = inches(1)             # 1 inch narrow end (at tip)
    dovetail_large_width = inches(2)             # 2 inch wide end (at base)
    dovetail_depth = inches(2)                   # 2 inch deep cut
    receiving_timber_shoulder_inset = inches(Rational(1, 2))  # 0.5 inch shoulder inset
    
    # Create the dovetail butt joint
    joint = cut_lapped_dovetail_butt_joint(
        dovetail_timber=dovetail_timber,
        receiving_timber=receiving_timber,
        dovetail_timber_end=TimberReferenceEnd.BOTTOM,  # Cut on the end pointing toward receiving timber
        dovetail_timber_face=TimberReferenceLongFace.FRONT,  # Dovetail visible on front face
        receiving_timber_shoulder_inset=receiving_timber_shoulder_inset,
        dovetail_length=dovetail_length,
        dovetail_small_width=dovetail_small_width,
        dovetail_large_width=dovetail_large_width,
        dovetail_lateral_offset=Rational(0),  # Centered
        dovetail_depth=dovetail_depth
    )
    
    # Create a frame from the joint
    frame = Frame.from_joints(
        [joint],
        name="Dovetail Butt Joint Example (蟻仕口 / Ari Shiguchi)"
    )
    
    return frame


if __name__ == "__main__":
    print("Creating Japanese Joint Examples...")
    print("=" * 70)
    
    frames = []
    
    print("\n1. Creating 4\"x4\" x 3' timber splice with lapped gooseneck joint...")
    frame1 = create_lapped_gooseneck_splice_example()
    frames.append(frame1)
    print(f"   Frame created: {frame1.name}")
    print(f"   Number of timbers: {len(frame1.cut_timbers)}")
    for timber in frame1.cut_timbers:
        print(f"   - {timber.name}: {len(timber.cuts)} cut(s)")
    
    print("\n2. Creating simplified vertical post splice example...")
    frame2 = create_simple_gooseneck_example()
    frames.append(frame2)
    print(f"   Frame created: {frame2.name}")
    print(f"   Number of timbers: {len(frame2.cut_timbers)}")
    for timber in frame2.cut_timbers:
        print(f"   - {timber.name}: {len(timber.cuts)} cut(s)")
    
    print("\n3. Creating dovetail butt joint (T-joint) example...")
    frame3 = create_dovetail_butt_joint_example()
    frames.append(frame3)
    print(f"   Frame created: {frame3.name}")
    print(f"   Number of timbers: {len(frame3.cut_timbers)}")
    for timber in frame3.cut_timbers:
        print(f"   - {timber.name}: {len(timber.cuts)} cut(s)")
    
    print("\n" + "=" * 70)
    print("All examples created successfully!")
    print("\nTraditional Japanese Timber Joints:")
    print("  • Lapped Gooseneck Joint (腰掛鎌継ぎ / Koshikake Kama Tsugi)")
    print("    - Splices beams end-to-end")
    print("    - Gooseneck profile resists tension")
    print("    - Lap provides compression bearing")
    print("")
    print("  • Dovetail Butt Joint (蟻仕口 / Ari Shiguchi)")
    print("    - Connects timbers at right angles")
    print("    - Dovetail shape resists pulling apart")
    print("    - Used for T-joints and corner connections")
    print("")
    print(f"Total frames created: {len(frames)}")
