"""
Japanese Joints Examples

This module demonstrates traditional Japanese timber joints:
- Lapped Gooseneck Joint (腰掛鎌継ぎ / Koshikake Kama Tsugi) - for splicing beams end-to-end
- Dovetail Butt Joint (蟻仕口 / Ari Shiguchi) - for connecting timbers at right angles

Each function creates and returns a Frame object with the joint example.
"""

from giraffe import *
from code_goes_here.patternbook import PatternBook, PatternMetadata


def create_japanese_joints_patternbook() -> PatternBook:
    """
    Create a PatternBook with Japanese joint patterns.
    
    Each pattern has groups: ["japanese_joints", "{joint_type}"]
    
    Returns:
        PatternBook: PatternBook containing Japanese joint patterns
    """
    patterns = [
        (PatternMetadata("gooseneck_simple", ["japanese_joints", "gooseneck"], "frame"),
         lambda center: create_simple_gooseneck_example()),
        
        (PatternMetadata("dovetail_butt", ["japanese_joints", "dovetail"], "frame"),
         lambda center: create_dovetail_butt_joint_example()),
    ]
    
    return PatternBook(patterns=patterns)



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
        gooseneck_timber_face=TimberLongFace.RIGHT,
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
        dovetail_timber_face=TimberLongFace.RIGHT,  # Dovetail visible on right face (perpendicular to receiving timber Z-axis)
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
    
    # TODO: Implement create_lapped_gooseneck_splice_example
    # print("\n1. Creating 4\"x4\" x 3' timber splice with lapped gooseneck joint...")
    # frame1 = create_lapped_gooseneck_splice_example()
    # frames.append(frame1)
    # print(f"   Frame created: {frame1.name}")
    # print(f"   Number of timbers: {len(frame1.cut_timbers)}")
    # for timber in frame1.cut_timbers:
    #     print(f"   - {timber.name}: {len(timber.cuts)} cut(s)")
    
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
