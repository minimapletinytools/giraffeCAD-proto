"""
Japanese Joints Examples

This module demonstrates traditional Japanese timber joints:
- Lapped Gooseneck Joint (腰掛鎌継ぎ / Koshikake Kama Tsugi) - for splicing beams end-to-end
- Dovetail Butt Joint (蟻仕口 / Ari Shiguchi) - for connecting timbers at right angles

Each function creates and returns a Frame object with the joint example.
"""

from typing import Optional
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
         lambda center: create_simple_gooseneck_example(position=center)),
        
        (PatternMetadata("dovetail_butt", ["japanese_joints", "dovetail"], "frame"),
         lambda center: create_dovetail_butt_joint_example(position=center)),
    ]
    
    return PatternBook(patterns=patterns)



def create_simple_gooseneck_example(position: Optional[V3] = None):
    """
    Create a gooseneck splice joint example using canonical 4"x5"x4' timbers.
    
    Args:
        position: Center position of the joint (V3). Defaults to origin.
    """
    # Create splice joint arrangement using canonical function
    # This creates two horizontal timbers meeting end-to-end
    arrangement = create_canonical_splice_joint_timbers(position=position)
    
    # Rename timbers for clarity in this joint context
    from dataclasses import replace
    gooseneck_timber = replace(arrangement.timber1, name="gooseneck_timber")
    receiving_timber = replace(arrangement.timber2, name="receiving_timber")

    # Create the gooseneck joint using parameters appropriate for canonical timber size
    joint = cut_lapped_gooseneck_joint(
        gooseneck_timber=gooseneck_timber,
        receiving_timber=receiving_timber,
        receiving_timber_end=arrangement.timber2_end,
        gooseneck_timber_face=TimberLongFace.RIGHT,
        gooseneck_length=inches(6),        # 6" gooseneck length
        gooseneck_small_width=inches(1),   # 1" narrow end
        gooseneck_large_width=inches(3),   # 3" wide end
        gooseneck_head_length=inches(2),   # 2" head length
        lap_length=inches(3),              # 3" lap length
        gooseneck_depth=inches(2)          # 2" depth
    )
    
    frame = Frame.from_joints(
        [joint],
        name="Lapped Gooseneck Splice Joint"
    )
    
    return frame


def create_dovetail_butt_joint_example(position: Optional[V3] = None):
    """
    Create a dovetail butt joint (蟻仕口 / Ari Shiguchi) using canonical 4"x5"x4' timbers.
    
    This is a traditional Japanese joint where a dovetail-shaped tenon on one timber
    fits into a matching dovetail socket on another timber. The dovetail shape provides
    mechanical resistance to pulling apart.
    
    Configuration:
        - Creates a butt joint connection where one timber butts into another
    
    Args:
        position: Center position of the joint (V3). Defaults to origin.
    """
    # Create butt joint arrangement using canonical function
    # This creates a receiving timber and a butt timber meeting at their centers
    arrangement = create_canonical_butt_joint_timbers(position=position)
    
    # Rename timbers for clarity in this joint context
    from dataclasses import replace
    receiving_timber = arrangement.receiving_timber
    dovetail_timber = replace(arrangement.butt_timber, name="dovetail_timber")
    
    # Create the dovetail butt joint using parameters appropriate for canonical timber size
    joint = cut_housed_dovetail_butt_joint(
        dovetail_timber=dovetail_timber,
        receiving_timber=receiving_timber,
        dovetail_timber_end=arrangement.butt_timber_end,
        dovetail_timber_face=TimberLongFace.RIGHT,
        receiving_timber_shoulder_inset=inches(Rational(1, 2)),  # 0.5" shoulder inset
        dovetail_length=inches(4),                                # 4" long dovetail tenon
        dovetail_small_width=inches(Rational(3, 2)),             # 1.5" narrow end
        dovetail_large_width=inches(3),                          # 3" wide end
        dovetail_lateral_offset=Rational(0),                     # Centered
        dovetail_depth=inches(Rational(5, 2))                    # 2.5" deep cut
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
