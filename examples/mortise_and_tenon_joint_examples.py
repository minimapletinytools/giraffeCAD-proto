"""
Example usage of mortise and tenon joint functions
"""

from sympy import Matrix, Rational
from code_goes_here.rule import inches, Transform
from code_goes_here.timber import (
    Timber, TimberReferenceEnd, TimberFace, TimberLongFace, Peg, Wedge,
    PegShape, timber_from_directions,
    create_v3, V2, CutTimber, Frame
)
from code_goes_here.joints.mortise_and_tenon_joint import (
    cut_mortise_and_tenon_joint_on_face_aligned_timbers,
    cut_mortise_and_tenon_many_options_do_not_call_me_directly,
    cut_mortise_and_tenon_many_options_do_not_call_me_directly_NEWVERSION,
    SimplePegParameters
)
from code_goes_here.construction import (
    create_axis_aligned_timber,
    create_canonical_brace_joint_timbers,
    create_canonical_butt_joint_timbers,
)
from code_goes_here.joints.basic_joints import cut_basic_miter_joint
from code_goes_here.patternbook import PatternBook, PatternMetadata, make_pattern_from_joint, make_pattern_from_frame


def example_basic_mortise_and_tenon(position=None):
    """
    Create a basic mortise and tenon joint using canonical butt joint timbers (4"x5"x4').
    Tenon on butt timber (Y), mortise in receiving timber (X).
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_v3(0, 0, 0)

    arrangement = create_canonical_butt_joint_timbers(position)
    tenon_size = Matrix([inches(2), inches(2)])
    tenon_length = inches(3)  # 3" long tenon
    mortise_depth = inches(7, 2)  # 3.5" deep mortise (slightly deeper than tenon)

    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=arrangement.butt_timber,
        mortise_timber=arrangement.receiving_timber,
        tenon_end=arrangement.butt_timber_end,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth
    )
    return joint


def example_4x6_into_6x8_mortise_and_tenon(position=None):
    """
    Create a mortise and tenon joint with a 4x6 tenon timber going into a 6x8 mortise timber.
    
    Configuration:
    - Tenon timber: 4x6 inch vertical post, 4 feet long
    - Mortise timber: 6x8 inch horizontal beam, 4 feet long
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x6 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(6)]),  # 4" x 6"
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        ticket="4x6 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x8 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_v3(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(8)]),  # 6" x 8"
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FRONT,
        ticket="6x8 Horizontal Beam"
    )
    
    tenon_size = Matrix([inches(4), inches(2)])  # 4" x 2" tenon
    tenon_length = inches(3)  # 3" long tenon
    mortise_depth = inches(7, 2)  # 3.5" deep mortise
    
    # Create the joint
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth
    )
    
    return joint


def example_through_tenon_with_6_inch_stickout(position=None):
    """
    Create a through tenon where the tenon sticks out 6 inches beyond the mortise timber.
    
    Configuration:
    - Tenon timber: 4x4 inch vertical post, 4 feet long
    - Mortise timber: 6x6 inch horizontal beam, 4 feet long
    - Through tenon extends 6 inches beyond the far side of the mortise timber
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        ticket="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_v3(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FRONT,
        ticket="6x6 Horizontal Beam"
    )
    
    # Define through tenon dimensions
    # Tenon goes through entire mortise timber (6 inches) plus 6 inches stickout
    tenon_size = Matrix([inches(5, 2), inches(5, 2)])  # 2.5" x 2.5" tenon
    tenon_length = inches(12)  # 6" through timber + 6" stickout = 12" total
    mortise_depth = None  # Through mortise (None means it goes all the way through)
    
    # Create the joint
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth
    )
    
    return joint


def example_full_size_4x4_tenon(position=None):
    """
    Create a mortise and tenon joint where a 4x4 tenon timber has a full-size 4x4 tenon
    going into a 6x6 mortise timber.
    
    Configuration:
    - Tenon timber: 4x4 inch vertical post, 4 feet long
    - Mortise timber: 6x6 inch horizontal beam, 4 feet long
    - Tenon: Full 4x4 inch cross-section (same as timber)
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        ticket="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_v3(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FRONT,
        ticket="6x6 Horizontal Beam"
    )
    
    # Define full-size tenon dimensions
    tenon_size = Matrix([inches(4), inches(4)])  # Full 4" x 4" tenon (same as timber)
    tenon_length = inches(4)  # 4" long tenon
    mortise_depth = inches(5)  # 5" deep mortise (slightly deeper than tenon)
    
    # Create the joint
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth
    )
    
    return joint


def example_offset_corner_tenon(position=None):
    """
    Create a mortise and tenon joint with the tenon offset to one corner of the tenon timber.
    
    Configuration:
    - Tenon timber: 4x4 inch vertical post, 4 feet long
    - Mortise timber: 6x6 inch horizontal beam, 4 feet long
    - Tenon: 2x2 inch positioned at the corner (+X, +Y) of the tenon timber
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        ticket="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_v3(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FRONT,
        ticket="6x6 Horizontal Beam"
    )
    
    # Define offset corner tenon dimensions
    # 2x2 inch tenon positioned at corner (+1, +1) in 4x4 timber
    # Timber half-size is 2", tenon half-size is 1"
    # Position at (+1, +1) places tenon bounds at [0, 2] in both X and Y
    tenon_size = Matrix([inches(2), inches(2)])  # 2" x 2" tenon
    tenon_length = inches(3)  # 3" long tenon
    mortise_depth = inches(7, 2)  # 3.5" deep mortise
    tenon_position = Matrix([inches(1), inches(1)])  # Offset to +X, +Y corner
    
    # Create the joint
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        tenon_position=tenon_position
    )
    
    return joint


def example_mortise_and_tenon_with_pegs(position=None):
    """
    Create a mortise and tenon joint with pegs securing the joint.
    
    Configuration:
    - Tenon timber: 4x4 inch vertical post, 4 feet long
    - Mortise timber: 6x6 inch horizontal beam, 4 feet long
    - Tenon: 2x2 inch centered tenon
    - Pegs: Two 1/2 inch square pegs through the tenon face
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        ticket="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_v3(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FRONT,
        ticket="6x6 Horizontal Beam"
    )
    
    # Define tenon dimensions
    tenon_size = Matrix([inches(2), inches(2)])  # 2" x 2" tenon
    tenon_length = inches(3)  # 3" long tenon
    mortise_depth = inches(7, 2)  # 3.5" deep mortise
    
    # Define peg parameters
    # Two pegs through the FRONT face, offset from the centerline
    # - First peg: 1" from shoulder, -0.5" from centerline
    # - Second peg: 2" from shoulder, +0.5" from centerline
    peg_params = SimplePegParameters(
        shape=PegShape.SQUARE,
        tenon_face=TimberLongFace.FRONT,
        # LOLOL 2 pegs...
        peg_positions=[
            (inches(1), inches(-1, 2)),  # 1" from shoulder, -0.5" from centerline
            (inches(2), inches(1, 2))    # 2" from shoulder, +0.5" from centerline
        ],
        #depth=inches(4),  # 4" deep into mortise timber
        size=inches(1, 2)  # 0.5" peg diameter/side length
    )
    
    # Create the joint with pegs
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        peg_parameters=peg_params
    )
    
    return joint


def example_brace_joint(position=None):
    """
    Create a brace joint with mortise and tenon connections.
    
    Configuration:
    - Creates a canonical brace joint arrangement (two 90-degree corner timbers + brace)
    - Plain miter joint between timber1 and timber2 at the corner
    - The brace timber connects the midpoints of the two corner timbers
    - Mortise and tenon joints connect the brace to both corner timbers
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    # Create the brace joint timber arrangement
    brace_arrangement = create_canonical_brace_joint_timbers(position)
    timber1 = brace_arrangement.timber1
    timber2 = brace_arrangement.timber2
    brace_timber = brace_arrangement.brace_timber
    
    # Plain miter joint between the two corner timbers
    miter_joint = cut_basic_miter_joint(
        timber1,
        brace_arrangement.timber1_end,
        timber2,
        brace_arrangement.timber2_end,
    )
    
    # Define tenon dimensions (smaller than full timber size)
    tenon_size = Matrix([inches(2), inches(2)])  # 2" x 2" tenon
    tenon_length = inches(5)  # 2" long tenon
    mortise_depth = inches(2)  # 3" deep mortise

        
    # Define peg parameters
    # Two pegs through the FRONT face, offset from the centerline
    # - First peg: 1" from shoulder, -0.5" from centerline
    # - Second peg: 2" from shoulder, +0.5" from centerline
    peg_params = SimplePegParameters(
        shape=PegShape.SQUARE,
        tenon_face=TimberLongFace.RIGHT,
        peg_positions=[
            (inches(1), inches(0)),  # 1" from shoulder, -0.5" from centerline
        ],
        #depth=inches(4),  # 4" deep into mortise timber
        size=inches(1, 2)  # 0.5" peg diameter/side length
    )
    
    
    # Create mortise and tenon joint between brace (tenon) and timber1 (mortise)
    # The brace connects to timber1 at its midpoint
    joint1 = cut_mortise_and_tenon_many_options_do_not_call_me_directly_NEWVERSION(
        tenon_timber=brace_timber,
        mortise_timber=timber1,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon on the end of brace that connects to timber1
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        crop_tenon_to_mortise_orientation_on_angled_joints = True,
        peg_parameters=peg_params
    )
    
    # Create mortise and tenon joint between brace (tenon) and timber2 (mortise)
    # The brace connects to timber2 at its midpoint
    joint2 = cut_mortise_and_tenon_many_options_do_not_call_me_directly_NEWVERSION(
        tenon_timber=brace_timber,
        mortise_timber=timber2,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon on the end of brace that connects to timber2
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        crop_tenon_to_mortise_orientation_on_angled_joints = True,
        peg_parameters=peg_params
    )
    
    # Combine miter + both mortise-and-tenon joints into a single Frame
    # Frame.from_joints will handle merging cuts on timbers that appear in multiple joints
    return Frame.from_joints([miter_joint, joint1, joint2], name="Brace Joint with Mortise and Tenon")


def create_mortise_and_tenon_patternbook() -> PatternBook:
    """
    Create a PatternBook with all mortise and tenon joint patterns.
    
    Each pattern has groups: ["mortise_tenon", "{variant}"]
    For example: ["mortise_tenon", "basic"] or ["mortise_tenon", "with_pegs"]
    
    Returns:
        PatternBook: PatternBook containing all mortise and tenon joint patterns
    """
    patterns = [
        (PatternMetadata("basic_4x4", ["mortise_tenon", "basic"], "frame"),
         make_pattern_from_joint(example_basic_mortise_and_tenon)),
        
        (PatternMetadata("4x6_into_6x8", ["mortise_tenon", "different_sizes"], "frame"),
         make_pattern_from_joint(example_4x6_into_6x8_mortise_and_tenon)),
        
        (PatternMetadata("through_tenon", ["mortise_tenon", "through"], "frame"),
         make_pattern_from_joint(example_through_tenon_with_6_inch_stickout)),
        
        (PatternMetadata("full_size_4x4", ["mortise_tenon", "full_size"], "frame"),
         make_pattern_from_joint(example_full_size_4x4_tenon)),
        
        (PatternMetadata("offset_corner", ["mortise_tenon", "offset"], "frame"),
         make_pattern_from_joint(example_offset_corner_tenon)),
        
        (PatternMetadata("with_pegs", ["mortise_tenon", "pegs"], "frame"),
         make_pattern_from_joint(example_mortise_and_tenon_with_pegs)),
        
        (PatternMetadata("brace_joint", ["mortise_tenon", "brace"], "frame"),
         make_pattern_from_frame(example_brace_joint)),
    ]
    
    return PatternBook(patterns=patterns)


def create_all_mortise_and_tenon_examples():
    """
    Create mortise and tenon joint examples with automatic spacing.
    
    This now uses the PatternBook to raise all patterns in the "mortise_tenon" group.
    
    Returns:
        Frame: Frame object containing all cut timbers and accessories for the examples
    """
    book = create_mortise_and_tenon_patternbook()
    
    # Raise all patterns in the "mortise_tenon" group with 6 feet spacing
    frame = book.raise_pattern_group("mortise_tenon", separation_distance=inches(72))
    
    return frame


def create_all_mortise_and_tenon_examples_OLD():
    """
    OLD VERSION - Create mortise and tenon joint examples with automatic spacing.
    
    To enable/disable specific examples, just comment/uncomment lines in the EXAMPLES_TO_RENDER list below.
    Examples will be positioned sequentially starting at the origin with 6 feet spacing.
    
    Returns:
        Frame: Frame object containing all cut timbers and accessories for the examples
    """
    
    # ============================================================================
    # CONFIGURATION: Comment out lines to disable specific examples
    # 
    # Example: To render only basic and peg examples:
    #   EXAMPLES_TO_RENDER = [
    #       ("Basic M&T (4x4)", example_basic_mortise_and_tenon),
    #       # ("4x6 into 6x8", example_4x6_into_6x8_mortise_and_tenon),
    #       # ("Through Tenon", example_through_tenon_with_6_inch_stickout),
    #       # ("Full Size 4x4", example_full_size_4x4_tenon),
    #       # ("Offset Corner", example_offset_corner_tenon),
    #       ("With Pegs", example_mortise_and_tenon_with_pegs),
    #   ]
    # Result: Examples will be at x=0" and x=72" (automatically spaced)
    # ============================================================================
    EXAMPLES_TO_RENDER = [
        #("Basic M&T (4x4)", example_basic_mortise_and_tenon),
        #("4x6 into 6x8", example_4x6_into_6x8_mortise_and_tenon),
        #("Through Tenon", example_through_tenon_with_6_inch_stickout),
        #("Full Size 4x4", example_full_size_4x4_tenon),
        #("Offset Corner", example_offset_corner_tenon),
        ("With Pegs", example_mortise_and_tenon_with_pegs),
    ]
    
    # Spacing between examples (in inches)
    SPACING = inches(72)  # 6 feet
    
    # ============================================================================
    # Render enabled examples starting from origin
    # ============================================================================
    all_timbers = []
    all_accessories = []  # List of (accessory, timber) tuples
    current_position_x = 0
    
    for example_name, example_function in EXAMPLES_TO_RENDER:
        joint = example_function()
        
        # Keep track of translated timbers for this joint
        translated_timbers = []
        
        # Translate timbers to current position
        for timber in joint.cut_timbers.values():
            new_position = timber.timber.get_bottom_position_global() + create_v3(current_position_x, 0, 0)
            translated_timber = Timber(
                ticket=timber.timber.ticket.name,
                transform=Transform(position=new_position, orientation=timber.timber.orientation),
                size=timber.timber.size,
                length=timber.timber.length
            )
            all_timbers.append(CutTimber(timber=translated_timber, cuts=timber.cuts))
            translated_timbers.append(translated_timber)
        
        # Collect joint accessories (already in global coordinates)
        if joint.jointAccessories:
            for accessory in joint.jointAccessories.values():
                # Accessories are stored in global space, so they need to be translated
                # to match the translated position of the joint
                translation_offset = create_v3(current_position_x, 0, 0)
                translated_transform = Transform(
                    position=accessory.transform.position + translation_offset,
                    orientation=accessory.transform.orientation
                )
                translated_accessory = Peg(
                    transform=translated_transform,
                    size=accessory.size,
                    shape=accessory.shape,
                    forward_length=accessory.forward_length,
                    stickout_length=accessory.stickout_length
                )
                all_accessories.append(translated_accessory)
        
        print(f"Created {example_name} at x={float(current_position_x/inches(1)):.1f}\"")
        
        # Move to next position
        current_position_x += SPACING
    
    return Frame(
        cut_timbers=all_timbers,
        accessories=all_accessories,
        ticket="M&T Examples"
    )


if __name__ == "__main__":
    # Run all examples
    examples = [
        ("Basic 4x4 Mortise and Tenon", example_basic_mortise_and_tenon),
        ("4x6 into 6x8 Mortise and Tenon", example_4x6_into_6x8_mortise_and_tenon),
        ("Through Tenon with 6\" Stickout", example_through_tenon_with_6_inch_stickout),
        ("Full-Size 4x4 Tenon into 6x6", example_full_size_4x4_tenon),
        ("Offset Corner Tenon (2x2 in 4x4)", example_offset_corner_tenon),
        ("Mortise and Tenon with Pegs", example_mortise_and_tenon_with_pegs),
    ]
    
    for example_name, example_func in examples:
        print(f"\n{'='*60}")
        print(f"Creating {example_name}...")
        print('='*60)
        
        joint = example_func()
        print(f"✅ Created joint with {len(joint.cut_timbers)} timbers")
        
        # Display timber details
        for i, cut_timber in enumerate(joint.cut_timbers.values()):
            timber = cut_timber.timber
            print(f"\n  Timber {i+1}: {timber.ticket.name}")
            print(f"    Position: ({float(timber.get_bottom_position_global()[0]):.1f}, {float(timber.get_bottom_position_global()[1]):.1f}, {float(timber.get_bottom_position_global()[2]):.1f})")
            print(f"    Length: {float(timber.length):.1f} inches")
            print(f"    Size: {float(timber.size[0]):.1f} x {float(timber.size[1]):.1f} inches")
            print(f"    Cuts: {len(cut_timber.cuts)}")
    
    print(f"\n{'='*60}")
    print("✅ All examples completed successfully!")
    print('='*60)

