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
    cut_plain_house_joint_DEPRECATED,
    cut_plain_splice_lap_joint_on_aligned_timbers,
)
from .mortise_and_tenon_joint import (
    cut_mortise_and_tenon_joint_on_face_aligned_timbers,
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
    return cut_plain_miter_joint(timberA, timberA_end, timberB, timberB_end)


def cut_basic_miter_joint_on_face_aligned_timbers(timberA: TimberLike, timberA_end: TimberReferenceEnd, timberB: TimberLike, timberB_end: TimberReferenceEnd) -> Joint:
    """Wrapper for cut_plain_miter_joint_on_face_aligned_timbers."""
    return cut_plain_miter_joint_on_face_aligned_timbers(timberA, timberA_end, timberB, timberB_end)


def cut_basic_butt_joint_on_face_aligned_timbers(receiving_timber: TimberLike, butt_timber: TimberLike, butt_end: TimberReferenceEnd) -> Joint:
    """Wrapper for cut_plain_butt_joint_on_face_aligned_timbers."""
    return cut_plain_butt_joint_on_face_aligned_timbers(receiving_timber, butt_timber, butt_end)


def cut_basic_butt_splice_joint_on_aligned_timbers(timberA: TimberLike, timberA_end: TimberReferenceEnd, timberB: TimberLike, timberB_end: TimberReferenceEnd) -> Joint:
    """Wrapper for cut_plain_butt_splice_joint_on_aligned_timbers."""
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
    lap_length = top_lap_timber.get_size_in_direction(top_lap_timber_face)
    return cut_plain_splice_lap_joint_on_aligned_timbers(
        top_lap_timber,
        top_lap_timber_end,
        bottom_lap_timber,
        bottom_lap_timber_end,
        top_lap_timber_face,
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
    """Wrapper for cut_mortise_and_tenon_joint_on_face_aligned_timbers."""

    # TODO FINISH THESE
    tenon_size = tenon_timber.size
    tenon_length = tenon_timber.get_size_in_direction(TimberLongFace.FRONT)
    mortise_depth = mortise_timber.get_size_in_direction(TimberLongFace.FRONT)

    tenon_position = create_v3(0, 0, 0)
    peg_parameters = None
    if use_peg:
        peg_parameters = SimplePegParameters(
            shape=PegShape.SQUARE,

            # TODO FINISH ALL WRONG 
            tenon_face=TimberLongFace.FRONT,
            peg_positions=[(inches(1), inches(-1, 2))],
            size=inches(1, 2),
            depth=inches(7, 2),

            tenon_hole_offset=inches(Rational(1, 16))
        )
    

    return cut_mortise_and_tenon_joint_on_face_aligned_timbers(
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

    width = gooseneck_timber.get_size_in_direction(gooseneck_timber_face.rotate_right())
    gooseneck_length = width*Rational(2)
    gooseneck_small_width: width*Rational(1, 4)
    gooseneck_large_width: width*Rational(1, 2)
    gooseneck_head_length: width*Rational(1, 2)

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

    width = dovetail_timber.get_size_in_direction(dovetail_timber_face.rotate_right())
    dovetail_length = width/Integer(2)
    dovetail_small_width: width*Rational(1, 2)
    dovetail_large_width: width*Rational(2, 3)

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
    return cut_mitered_and_keyed_lap_joint(
        timberA,
        timberA_end,
        timberA_reference_miter_face,
        timberB,
        timberB_end
    )
