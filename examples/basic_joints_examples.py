"""
Example usage of basic joint construction functions
Uses canonical timber configurations from construction.py
"""

from sympy import Matrix, Rational
from code_goes_here.rule import inches, Transform
from code_goes_here.timber import (
    Timber, TimberReferenceEnd, TimberFace, TimberLongFace, Peg, Wedge,
    PegShape, timber_from_directions,
    create_v3, V2, CutTimber, Frame
)
from code_goes_here.ticket import Ticket
from code_goes_here.joints.basic_joints import (
    cut_basic_miter_joint,
    cut_basic_miter_joint_on_face_aligned_timbers,
    cut_basic_butt_joint_on_face_aligned_timbers,
    cut_basic_butt_splice_joint_on_aligned_timbers,
    cut_basic_cross_lap_joint,
    cut_basic_house_joint,
    cut_basic_splice_lap_joint_on_aligned_timbers,
    cut_basic_mortise_and_tenon_joint_on_face_aligned_timbers,
    cut_basic_lapped_gooseneck_joint,
    cut_basic_housed_dovetail_butt_joint,
    cut_basic_mitered_and_keyed_lap_joint,
)
from code_goes_here.construction import (
    create_canonical_right_angle_corner_joint_timbers,
    create_canonical_butt_joint_timbers,
    create_canonical_splice_joint_timbers,
    create_canonical_cross_joint_timbers,
    _CANONICAL_EXAMPLE_TIMBER_LENGTH,
    _CANONICAL_EXAMPLE_TIMBER_SIZE,
)
from code_goes_here.patternbook import PatternBook, PatternMetadata


def example_basic_miter_joint(position=None):
    """
    Create a basic miter joint using canonical corner joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_right_angle_corner_joint_timbers(position)
    joint = cut_basic_miter_joint(
        timberA=arrangement.timber1,
        timberA_end=arrangement.timber1_end,
        timberB=arrangement.timber2,
        timberB_end=arrangement.timber2_end
    )
    
    return joint


def example_basic_miter_joint_face_aligned(position=None):
    """
    Create a basic miter joint on face-aligned timbers using canonical corner joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_right_angle_corner_joint_timbers(position)
    joint = cut_basic_miter_joint_on_face_aligned_timbers(
        timberA=arrangement.timber1,
        timberA_end=arrangement.timber1_end,
        timberB=arrangement.timber2,
        timberB_end=arrangement.timber2_end
    )
    
    return joint


def example_basic_butt_joint(position=None):
    """
    Create a basic butt joint using canonical butt joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_butt_joint_timbers(position)
    joint = cut_basic_butt_joint_on_face_aligned_timbers(
        receiving_timber=arrangement.receiving_timber,
        butt_timber=arrangement.butt_timber,
        butt_end=arrangement.butt_timber_end
    )
    
    return joint


def example_basic_butt_splice_joint(position=None):
    """
    Create a basic butt splice joint using canonical splice joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_splice_joint_timbers(position)
    joint = cut_basic_butt_splice_joint_on_aligned_timbers(
        timberA=arrangement.timber1,
        timberA_end=arrangement.timber1_end,
        timberB=arrangement.timber2,
        timberB_end=arrangement.timber2_end
    )
    
    return joint


def example_basic_cross_lap_joint(position=None):
    """
    Create a basic cross lap joint using canonical cross joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_cross_joint_timbers(position=position)
    joint = cut_basic_cross_lap_joint(
        timberA=arrangement.timber1,
        timberB=arrangement.timber2
    )
    
    return joint


def example_basic_house_joint(position=None):
    """
    Create a basic house joint using canonical cross joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_cross_joint_timbers(position=position)
    joint = cut_basic_house_joint(
        housing_timber=arrangement.timber1,
        housed_timber=arrangement.timber2
    )
    
    return joint


def example_basic_splice_lap_joint(position=None):
    """
    Create a basic splice lap joint using canonical splice joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_splice_joint_timbers(position)
    # Use the FRONT face for the lap
    joint = cut_basic_splice_lap_joint_on_aligned_timbers(
        top_lap_timber=arrangement.timber1,
        top_lap_timber_end=arrangement.timber1_end,
        bottom_lap_timber=arrangement.timber2,
        bottom_lap_timber_end=arrangement.timber2_end,
        top_lap_timber_face=TimberLongFace.FRONT
    )
    
    return joint


def example_basic_mortise_and_tenon_joint(position=None):
    """
    Create a basic mortise and tenon joint using canonical butt joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_butt_joint_timbers(position)
    joint = cut_basic_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=arrangement.butt_timber,
        mortise_timber=arrangement.receiving_timber,
        tenon_end=arrangement.butt_timber_end,
        use_peg=False
    )
    
    return joint


def example_basic_mortise_and_tenon_joint_with_peg(position=None):
    """
    Create a basic mortise and tenon joint with peg using canonical butt joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_butt_joint_timbers(position)
    joint = cut_basic_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=arrangement.butt_timber,
        mortise_timber=arrangement.receiving_timber,
        tenon_end=arrangement.butt_timber_end,
        use_peg=True
    )
    
    return joint


def example_basic_lapped_gooseneck_joint(position=None):
    """
    Create a basic lapped gooseneck joint.
    Uses canonical timbers - receiving timber is vertical, gooseneck timber is horizontal.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    # Create receiving timber (vertical, like a post)
    receiving_timber = timber_from_directions(
        length=_CANONICAL_EXAMPLE_TIMBER_LENGTH,
        size=_CANONICAL_EXAMPLE_TIMBER_SIZE,
        bottom_position=position,
        length_direction=create_v3(0, 0, 1),  # +Z direction (vertical)
        width_direction=create_v3(1, 0, 0),   # RIGHT face points in +X
        ticket="receiving_timber"
    )
    
    # Create gooseneck timber (horizontal, extending from receiving timber)
    gooseneck_timber = timber_from_directions(
        length=_CANONICAL_EXAMPLE_TIMBER_LENGTH,
        size=_CANONICAL_EXAMPLE_TIMBER_SIZE,
        bottom_position=position + create_v3(0, _CANONICAL_EXAMPLE_TIMBER_LENGTH / 2, 0),
        length_direction=create_v3(0, 1, 0),  # +Y direction (horizontal)
        width_direction=create_v3(0, 0, 1),   # RIGHT face points in +Z
        ticket="gooseneck_timber"
    )
    
    joint = cut_basic_lapped_gooseneck_joint(
        gooseneck_timber=gooseneck_timber,
        receiving_timber=receiving_timber,
        receiving_timber_end=TimberReferenceEnd.BOTTOM,
        gooseneck_timber_face=TimberLongFace.TOP
    )
    
    return joint


def example_basic_housed_dovetail_butt_joint(position=None):
    """
    Create a basic housed dovetail butt joint.
    Uses canonical timbers - dovetail timber is horizontal, receiving timber is vertical.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    from sympy import Integer
    
    # Create receiving timber (vertical, like a post)
    receiving_timber = timber_from_directions(
        length=_CANONICAL_EXAMPLE_TIMBER_LENGTH,
        size=_CANONICAL_EXAMPLE_TIMBER_SIZE,
        bottom_position=position,
        length_direction=create_v3(0, 0, 1),  # +Z direction (vertical)
        width_direction=create_v3(1, 0, 0),   # RIGHT face points in +X
        ticket="receiving_timber"
    )
    
    # Create dovetail timber (horizontal, extending from receiving timber)
    dovetail_timber = timber_from_directions(
        length=_CANONICAL_EXAMPLE_TIMBER_LENGTH,
        size=_CANONICAL_EXAMPLE_TIMBER_SIZE,
        bottom_position=position + create_v3(0, _CANONICAL_EXAMPLE_TIMBER_LENGTH / 2, 0),
        length_direction=create_v3(0, 1, 0),  # +Y direction (horizontal)
        width_direction=create_v3(0, 0, 1),   # RIGHT face points in +Z
        ticket="dovetail_timber"
    )
    
    # Calculate dovetail parameters based on timber size
    width = dovetail_timber.get_size_in_direction(TimberLongFace.TOP.rotate_right())
    dovetail_length = width / Integer(2)
    dovetail_small_width = width * Rational(1, 2)
    dovetail_large_width = width * Rational(2, 3)
    receiving_timber_shoulder_inset = inches(1)  # 1 inch inset
    
    joint = cut_basic_housed_dovetail_butt_joint(
        dovetail_timber=dovetail_timber,
        receiving_timber=receiving_timber,
        dovetail_timber_end=TimberReferenceEnd.BOTTOM,
        dovetail_timber_face=TimberLongFace.TOP,
        receiving_timber_shoulder_inset=receiving_timber_shoulder_inset,
        dovetail_length=dovetail_length,
        dovetail_small_width=dovetail_small_width,
        dovetail_large_width=dovetail_large_width
    )
    
    return joint


def example_basic_mitered_and_keyed_lap_joint(position=None):
    """
    Create a basic mitered and keyed lap joint using canonical corner joint timbers.
    """
    if position is None:
        position = create_v3(0, 0, 0)
    
    arrangement = create_canonical_right_angle_corner_joint_timbers(position)
    joint = cut_basic_mitered_and_keyed_lap_joint(
        timberA=arrangement.timber1,
        timberA_end=arrangement.timber1_end,
        timberA_reference_miter_face=TimberLongFace.RIGHT,
        timberB=arrangement.timber2,
        timberB_end=arrangement.timber2_end
    )
    
    return joint


def create_basic_joints_patternbook() -> PatternBook:
    """
    Create a PatternBook with all basic joint patterns.
    
    Each pattern has groups: ["basic_joints", "{variant}"]
    For example: ["basic_joints", "miter"] or ["basic_joints", "butt"]
    
    Returns:
        PatternBook: PatternBook containing all basic joint patterns
    """
    def make_pattern_from_joint(joint_func):
        """Helper to convert a joint function to a pattern lambda that handles translation."""
        def pattern_lambda(center):
            # Create joint at origin
            joint = joint_func()
            
            # Translate all timbers to center position
            translated_timbers = []
            for timber in joint.cut_timbers.values():
                new_position = timber.timber.get_bottom_position_global() + center
                # Get ticket - preserve the original ticket object
                translated_timber = Timber(
                    ticket=timber.timber.ticket,
                    transform=Transform(position=new_position, orientation=timber.timber.orientation),
                    size=timber.timber.size,
                    length=timber.timber.length
                )
                translated_timbers.append(CutTimber(timber=translated_timber, cuts=timber.cuts))
            
            # Translate accessories
            translated_accessories = []
            if joint.jointAccessories:
                for accessory in joint.jointAccessories.values():
                    translated_transform = Transform(
                        position=accessory.transform.position + center,
                        orientation=accessory.transform.orientation
                    )
                    if isinstance(accessory, Peg):
                        translated_accessory = Peg(
                            transform=translated_transform,
                            size=accessory.size,
                            shape=accessory.shape,
                            forward_length=accessory.forward_length,
                            stickout_length=accessory.stickout_length
                        )
                    elif isinstance(accessory, Wedge):
                        translated_accessory = Wedge(
                            transform=translated_transform,
                            base_width=accessory.base_width,
                            tip_width=accessory.tip_width,
                            height=accessory.height,
                            length=accessory.length,
                            stickout_length=accessory.stickout_length
                        )
                    else:
                        translated_accessory = accessory
                    translated_accessories.append(translated_accessory)
            
            return Frame(cut_timbers=translated_timbers, accessories=translated_accessories)
        
        return pattern_lambda
    
    patterns = [
        (PatternMetadata("basic_miter", ["basic_joints", "miter"], "frame"),
         make_pattern_from_joint(example_basic_miter_joint)),
        
        (PatternMetadata("basic_miter_face_aligned", ["basic_joints", "miter"], "frame"),
         make_pattern_from_joint(example_basic_miter_joint_face_aligned)),
        
        (PatternMetadata("basic_butt", ["basic_joints", "butt"], "frame"),
         make_pattern_from_joint(example_basic_butt_joint)),
        
        (PatternMetadata("basic_butt_splice", ["basic_joints", "splice"], "frame"),
         make_pattern_from_joint(example_basic_butt_splice_joint)),
        
        (PatternMetadata("basic_cross_lap", ["basic_joints", "lap"], "frame"),
         make_pattern_from_joint(example_basic_cross_lap_joint)),
        
        (PatternMetadata("basic_house", ["basic_joints", "house"], "frame"),
         make_pattern_from_joint(example_basic_house_joint)),
        
        (PatternMetadata("basic_splice_lap", ["basic_joints", "lap"], "frame"),
         make_pattern_from_joint(example_basic_splice_lap_joint)),
        
        (PatternMetadata("basic_mortise_tenon", ["basic_joints", "mortise_tenon"], "frame"),
         make_pattern_from_joint(example_basic_mortise_and_tenon_joint)),
        
        (PatternMetadata("basic_mortise_tenon_peg", ["basic_joints", "mortise_tenon"], "frame"),
         make_pattern_from_joint(example_basic_mortise_and_tenon_joint_with_peg)),
        
        (PatternMetadata("basic_gooseneck", ["basic_joints", "japanese"], "frame"),
         make_pattern_from_joint(example_basic_lapped_gooseneck_joint)),
        
        (PatternMetadata("basic_dovetail", ["basic_joints", "japanese"], "frame"),
         make_pattern_from_joint(example_basic_housed_dovetail_butt_joint)),
        
        (PatternMetadata("basic_mitered_keyed_lap", ["basic_joints", "japanese"], "frame"),
         make_pattern_from_joint(example_basic_mitered_and_keyed_lap_joint)),
    ]
    
    return PatternBook(patterns=patterns)


def create_all_basic_joints_examples():
    """
    Create basic joint examples with automatic spacing.
    
    This uses the PatternBook to raise all patterns in the "basic_joints" group.
    
    Returns:
        Frame: Frame object containing all cut timbers and accessories for the examples
    """
    book = create_basic_joints_patternbook()
    
    # Raise all patterns in the "basic_joints" group with 6 feet spacing
    frame = book.raise_pattern_group("basic_joints", separation_distance=inches(72))
    
    return frame
