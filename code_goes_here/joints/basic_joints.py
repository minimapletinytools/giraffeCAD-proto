"""
GiraffeCAD - Basic joint construction functions
Contains cut_basic_* wrapper functions that forward to the original joint functions.

These are temporary wrappers that will be simplified later.
"""

from typing import Optional, List, Tuple
from code_goes_here.timber import *
from code_goes_here.rule import *
from .plain_joints import (
    cut_plain_miter_joint,
    cut_plain_miter_joint_on_face_aligned_timbers,
    cut_plain_butt_joint_on_face_aligned_timbers,
    cut_plain_butt_splice_joint_on_aligned_timbers,
    cut_plain_cross_lap_joint,
    cut_plain_house_joint,
    cut_plain_splice_lap_joint_on_aligned_timbers,
)
from .mortise_and_tenon_joint import (
    cut_mortise_and_tenon_joint_on_face_aligned_timbers_DEPRECATED,
    SimplePegParameters,
)
from .japanese_joints import (
    cut_lapped_gooseneck_joint,
    cut_housed_dovetail_butt_joint,
    cut_mitered_and_keyed_lap_joint,
)


# ============================================================================
# Plain Joint Wrappers
# ============================================================================

def cut_basic_miter_joint(timberA: TimberLike, timberA_end: TimberReferenceEnd, timberB: TimberLike, timberB_end: TimberReferenceEnd) -> Joint:
    """Wrapper for cut_plain_miter_joint."""
    assert isinstance(timberA_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberA_end).__name__}"
    assert isinstance(timberB_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberB_end).__name__}"
    return cut_plain_miter_joint(timberA, timberA_end, timberB, timberB_end)


def cut_basic_miter_joint_on_face_aligned_timbers(timberA: TimberLike, timberA_end: TimberReferenceEnd, timberB: TimberLike, timberB_end: TimberReferenceEnd) -> Joint:
    """Wrapper for cut_plain_miter_joint_on_face_aligned_timbers."""
    assert isinstance(timberA_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberA_end).__name__}"
    assert isinstance(timberB_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberB_end).__name__}"
    return cut_plain_miter_joint_on_face_aligned_timbers(timberA, timberA_end, timberB, timberB_end)


def cut_basic_butt_joint_on_face_aligned_timbers(receiving_timber: TimberLike, butt_timber: TimberLike, butt_end: TimberReferenceEnd) -> Joint:
    """Wrapper for cut_plain_butt_joint_on_face_aligned_timbers."""
    assert isinstance(butt_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(butt_end).__name__}"
    return cut_plain_butt_joint_on_face_aligned_timbers(receiving_timber, butt_timber, butt_end)


def cut_basic_butt_splice_joint_on_aligned_timbers(timberA: TimberLike, timberA_end: TimberReferenceEnd, timberB: TimberLike, timberB_end: TimberReferenceEnd) -> Joint:
    """Wrapper for cut_plain_butt_splice_joint_on_aligned_timbers."""
    assert isinstance(timberA_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberA_end).__name__}"
    assert isinstance(timberB_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberB_end).__name__}"
    return cut_plain_butt_splice_joint_on_aligned_timbers(timberA, timberA_end, timberB, timberB_end)


def cut_basic_cross_lap_joint(timberA: TimberLike, timberB: TimberLike) -> Joint:
    """Wrapper for cut_plain_cross_lap_joint."""
    return cut_plain_cross_lap_joint(timberA, timberB)


def cut_basic_house_joint(housing_timber: TimberLike, housed_timber: TimberLike) -> Joint:
    """Wrapper for cut_plain_house_joint."""
    return cut_plain_house_joint(housing_timber, housed_timber)


def cut_basic_splice_lap_joint_on_aligned_timbers(
    top_lap_timber: TimberLike,
    top_lap_timber_end: TimberReferenceEnd,
    bottom_lap_timber: TimberLike,
    bottom_lap_timber_end: TimberReferenceEnd,
    top_lap_timber_face: TimberFace
) -> Joint:
    """Wrapper for cut_plain_splice_lap_joint_on_aligned_timbers."""
    assert isinstance(top_lap_timber_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(top_lap_timber_end).__name__}"
    assert isinstance(bottom_lap_timber_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(bottom_lap_timber_end).__name__}"
    lap_length = top_lap_timber.get_size_in_face_normal_axis(top_lap_timber_face)
    return cut_plain_splice_lap_joint_on_aligned_timbers(
        top_lap_timber,
        top_lap_timber_end,
        bottom_lap_timber,
        bottom_lap_timber_end,
        top_lap_timber_face.to.long_face(),
        lap_length,
        top_lap_shoulder_position_from_top_lap_shoulder_timber_end = lap_length
    )


# ============================================================================
# Mortise and Tenon Joint Wrappers
# ============================================================================

def cut_basic_mortise_and_tenon_joint_on_face_aligned_timbers(
    tenon_timber: TimberLike,
    mortise_timber: TimberLike,
    tenon_end: TimberReferenceEnd,
    use_peg: bool = False,
) -> Joint:
    """Wrapper for cut_mortise_and_tenon_joint_on_face_aligned_timbers_DEPRECATED."""
    assert isinstance(tenon_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(tenon_end).__name__}"
    # this is the "side" of the joint
    joint_side_mortise_timber_face = mortise_timber.get_closest_oriented_face_from_global_direction(cross_product(mortise_timber.get_length_direction_global(), tenon_timber.get_face_direction_global(tenon_end.to.face())))
    joint_side_tenon_timber_face = tenon_timber.get_closest_oriented_face_from_global_direction(mortise_timber.get_face_direction_global(joint_side_mortise_timber_face))

    # the sizing XY depends on the orientation of the tenon timber relative to the mortise timber
    mortise_length_on_tenon_timber_face = tenon_timber.get_closest_oriented_face_from_global_direction(mortise_timber.get_length_direction_global())

    mortise_timber_entry_face = joint_side_mortise_timber_face.to.long_face().rotate_right().to.face()

    tenon_mortise_length_size = tenon_timber.get_size_in_face_normal_axis(mortise_length_on_tenon_timber_face)*Rational(3,4)
    tenon_mortise_width_size = mortise_timber.get_size_in_face_normal_axis(joint_side_mortise_timber_face)*Rational(1,3)

    if mortise_length_on_tenon_timber_face == TimberLongFace.FRONT or mortise_length_on_tenon_timber_face == TimberLongFace.BACK:
        tenon_size = Matrix([tenon_mortise_length_size, tenon_mortise_width_size])
    else:
        tenon_size = Matrix([tenon_mortise_width_size, tenon_mortise_length_size])
        

    tenon_length = mortise_timber.get_size_in_face_normal_axis(mortise_timber_entry_face)
    mortise_depth = tenon_length

    tenon_position = create_v3(0, 0, 0)
    peg_parameters = None
    if use_peg: 
        peg_parameters = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=joint_side_tenon_timber_face.to.long_face(),
            peg_positions=[(tenon_length / 3, Integer(0))],
            size=inches(1, 2),
            depth=None,
            tenon_hole_offset=inches(Rational(1, 16))
        )
    

    return cut_mortise_and_tenon_joint_on_face_aligned_timbers_DEPRECATED(
        tenon_timber,
        mortise_timber,
        tenon_end,
        tenon_size,
        tenon_length,
        mortise_depth,
        tenon_position,
        peg_parameters
    )


# ============================================================================
# Japanese Joint Wrappers
# ============================================================================

def cut_basic_lapped_gooseneck_joint(
    gooseneck_timber: TimberLike,
    receiving_timber: TimberLike,
    receiving_timber_end: TimberReferenceEnd,
    gooseneck_timber_face: TimberLongFace,
) -> Joint:
    """Wrapper for cut_lapped_gooseneck_joint."""
    assert isinstance(receiving_timber_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(receiving_timber_end).__name__}"
    assert isinstance(gooseneck_timber_face, TimberLongFace), f"expected TimberLongFace, got {type(gooseneck_timber_face).__name__}"
    width = gooseneck_timber.get_size_in_face_normal_axis(gooseneck_timber_face.rotate_right())
    gooseneck_length = width*Rational(2)
    gooseneck_small_width = width*Rational(1, 4)
    gooseneck_large_width = width*Rational(1, 2)
    gooseneck_head_length = width*Rational(1, 2)

    return cut_lapped_gooseneck_joint(
        gooseneck_timber,
        receiving_timber,
        receiving_timber_end,
        gooseneck_timber_face,
        gooseneck_length,
        gooseneck_small_width,
        gooseneck_large_width,
        gooseneck_head_length
    )


def cut_basic_housed_dovetail_butt_joint(
    dovetail_timber: TimberLike,
    receiving_timber: TimberLike,
    dovetail_timber_end: TimberReferenceEnd,
    dovetail_timber_face: TimberLongFace,
    receiving_timber_shoulder_inset: Numeric,
    dovetail_length: Numeric,
    dovetail_small_width: Numeric,
    dovetail_large_width: Numeric,
) -> Joint:
    """Wrapper for cut_housed_dovetail_butt_joint."""
    assert isinstance(dovetail_timber_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(dovetail_timber_end).__name__}"
    assert isinstance(dovetail_timber_face, TimberLongFace), f"expected TimberLongFace, got {type(dovetail_timber_face).__name__}"
    width = dovetail_timber.get_size_in_face_normal_axis(dovetail_timber_face.rotate_right())
    dovetail_length = width/Integer(2)
    dovetail_small_width = width*Rational(1, 2)
    dovetail_large_width = width*Rational(2, 3)

    return cut_housed_dovetail_butt_joint(
        dovetail_timber,
        receiving_timber,
        dovetail_timber_end,
        dovetail_timber_face,
        receiving_timber_shoulder_inset,
        dovetail_length,
        dovetail_small_width,
        dovetail_large_width
    )


def cut_basic_mitered_and_keyed_lap_joint(
    timberA: TimberLike,
    timberA_end: TimberReferenceEnd,
    timberA_reference_miter_face: TimberLongFace,
    timberB: TimberLike,
    timberB_end: TimberReferenceEnd,
) -> Joint:
    """Wrapper for cut_mitered_and_keyed_lap_joint."""
    assert isinstance(timberA_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberA_end).__name__}"
    assert isinstance(timberA_reference_miter_face, TimberLongFace), f"expected TimberLongFace, got {type(timberA_reference_miter_face).__name__}"
    assert isinstance(timberB_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(timberB_end).__name__}"
    return cut_mitered_and_keyed_lap_joint(
        timberA,
        timberA_end,
        timberA_reference_miter_face,
        timberB,
        timberB_end
    )
