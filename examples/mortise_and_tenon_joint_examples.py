"""
Example usage of mortise and tenon joint functions
"""

from sympy import Matrix, Rational
from code_goes_here.moothymoth import inches
from code_goes_here.timber import (
    Timber, TimberReferenceEnd, TimberFace, TimberReferenceLongFace,
    PegShape, timber_from_directions,
    create_vector3d, V2, CutTimber, PartiallyCutTimber
)
from code_goes_here.mortise_and_tenon_joint import (
    cut_mortise_and_tenon_joint_on_face_aligned_timbers,
    SimplePegParameters
)
from code_goes_here.construction import create_axis_aligned_timber


def example_basic_mortise_and_tenon(position=None):
    """
    Create a basic mortise and tenon joint between a vertical post and horizontal beam.
    
    Configuration:
    - Tenon timber (vertical post): 4x4 inch, 4 feet long, bottom point at origin (0,0,0), extends upward
    - Mortise timber (horizontal beam): 4x4 inch, 4 feet long, centered at origin, extends along X axis
    
    Args:
        position: Optional offset position (V3) to translate the joint
    """
    if position is None:
        position = create_vector3d(0, 0, 0)
    
    # Timber dimensions: 4x4 inches, 4 feet (48 inches) long
    timber_size = Matrix([inches(4), inches(4)])  # 4" x 4" cross section
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) with bottom at position
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=timber_size,
        length_direction=TimberFace.TOP,  # Points upward in +Z direction
        width_direction=TimberFace.RIGHT,  # Width in +X direction
        name="Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) centered at position
    # The beam extends along X axis with its center (not bottom) at position
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(position[0] - timber_length / 2, position[1], position[2]),  # Start at -24 inches from position so center is at position
        length=timber_length,
        size=timber_size,
        length_direction=TimberFace.RIGHT,  # Points in +X direction
        width_direction=TimberFace.FORWARD,  # Width in +Y direction
        name="Horizontal Beam"
    )
    
    tenon_size = Matrix([inches(2), inches(2)])
    tenon_length = inches(3)  # 3" long tenon
    mortise_depth = inches(7, 2)  # 3.5" deep mortise (slightly deeper than tenon)
    
    # Create the joint
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon cut on top end of post
        size=tenon_size,
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
        position = create_vector3d(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x6 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(6)]),  # 4" x 6"
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        name="4x6 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x8 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(8)]),  # 6" x 8"
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FORWARD,
        name="6x8 Horizontal Beam"
    )
    
    tenon_size = Matrix([inches(4), inches(2)])  # 4" x 2" tenon
    tenon_length = inches(3)  # 3" long tenon
    mortise_depth = inches(7, 2)  # 3.5" deep mortise
    
    # Create the joint
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,
        size=tenon_size,
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
        position = create_vector3d(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        name="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FORWARD,
        name="6x6 Horizontal Beam"
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
        size=tenon_size,
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
        position = create_vector3d(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        name="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FORWARD,
        name="6x6 Horizontal Beam"
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
        size=tenon_size,
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
        position = create_vector3d(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        name="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FORWARD,
        name="6x6 Horizontal Beam"
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
        size=tenon_size,
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
        position = create_vector3d(0, 0, 0)
    
    timber_length = inches(48)  # 4 feet = 48 inches
    
    # Create a vertical post (tenon timber) - 4x4 inches
    post = create_axis_aligned_timber(
        bottom_position=position,
        length=timber_length,
        size=Matrix([inches(4), inches(4)]),
        length_direction=TimberFace.TOP,
        width_direction=TimberFace.RIGHT,
        name="4x4 Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) - 6x6 inches
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(position[0] - timber_length / 2, position[1], position[2]),
        length=timber_length,
        size=Matrix([inches(6), inches(6)]),
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.FORWARD,
        name="6x6 Horizontal Beam"
    )
    
    # Define tenon dimensions
    tenon_size = Matrix([inches(2), inches(2)])  # 2" x 2" tenon
    tenon_length = inches(3)  # 3" long tenon
    mortise_depth = inches(7, 2)  # 3.5" deep mortise
    
    # Define peg parameters
    # Two pegs through the FORWARD face, offset from the centerline
    # - First peg: 1" from shoulder, -0.5" from centerline
    # - Second peg: 2" from shoulder, +0.5" from centerline
    peg_params = SimplePegParameters(
        shape=PegShape.SQUARE,
        tenon_face=TimberReferenceLongFace.FORWARD,
        # LOLOL 2 pegs...
        peg_positions=[
            (inches(1), inches(-1, 2)),  # 1" from shoulder, -0.5" from centerline
            (inches(2), inches(1, 2))    # 2" from shoulder, +0.5" from centerline
        ],
        depth=inches(4),  # 4" deep into mortise timber
        length=inches(5)  # 5" total peg length
    )
    
    # Create the joint with pegs
    joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.BOTTOM,
        size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        peg_parameters=peg_params
    )
    
    return joint


def create_all_mortise_and_tenon_examples(return_accessories: bool = False):
    """
    Create mortise and tenon joint examples with automatic spacing.
    
    To enable/disable specific examples, just comment/uncomment lines in the EXAMPLES_TO_RENDER list below.
    Examples will be positioned sequentially starting at the origin with 6 feet spacing.
    
    Args:
        return_accessories: If True, return (timbers, accessories) tuple. If False, return just timbers.
    
    Returns:
        If return_accessories=False: List of all CutTimber objects for the enabled examples
        If return_accessories=True: Tuple of (List[CutTimber], List[(JointAccessory, Timber)])
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
        for timber in joint.partiallyCutTimbers:
            new_position = timber.timber.bottom_position + create_vector3d(current_position_x, 0, 0)
            translated_timber = Timber(
                name=timber.timber.name,
                bottom_position=new_position,
                orientation=timber.timber.orientation,
                size=timber.timber.size,
                length=timber.timber.length
            )
            all_timbers.append(PartiallyCutTimber(timber=translated_timber, cuts=timber._cuts))
            translated_timbers.append(translated_timber)
        
        # Collect joint accessories (already in timber-relative coordinates)
        if joint.jointAccessories:
            for accessory in joint.jointAccessories:
                # Accessories are stored relative to a timber
                # For now, we'll associate with the first timber (typically the mortise timber)
                # TODO: Better timber association logic - track which timber each accessory belongs to
                if translated_timbers:
                    associated_timber = translated_timbers[0]
                    all_accessories.append((accessory, associated_timber))
        
        print(f"Created {example_name} at x={float(current_position_x/inches(1)):.1f}\"")
        
        # Move to next position
        current_position_x += SPACING
    
    if return_accessories:
        return all_timbers, all_accessories
    else:
        return all_timbers


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
        print(f"✅ Created joint with {len(joint.partiallyCutTimbers)} timbers")
        
        # Display timber details
        for i, cut_timber in enumerate(joint.partiallyCutTimbers):
            timber = cut_timber._timber
            print(f"\n  Timber {i+1}: {timber.name}")
            print(f"    Position: ({float(timber.bottom_position[0]):.1f}, {float(timber.bottom_position[1]):.1f}, {float(timber.bottom_position[2]):.1f})")
            print(f"    Length: {float(timber.length):.1f} inches")
            print(f"    Size: {float(timber.size[0]):.1f} x {float(timber.size[1]):.1f} inches")
            print(f"    Cuts: {len(cut_timber._cuts)}")
    
    print(f"\n{'='*60}")
    print("✅ All examples completed successfully!")
    print('='*60)

