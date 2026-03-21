"""
Double Butt Joints Examples - Demonstration of double butt joint types in GiraffeCAD

This file contains one example function for each double butt joint type.
Each joint is created from 4"x5" timbers that are 4' long.
"""

from sympy import Rational
from typing import Union, List

from code_goes_here.rule import V3, create_v3
from code_goes_here.timber import CutTimber, Frame
from code_goes_here.joints.double_butt_joints import cut_splined_opposing_double_butt_joint
from code_goes_here.example_shavings import create_canonical_example_opposing_double_butt_joint_timbers
from code_goes_here.patternbook import PatternBook, PatternMetadata


def make_splined_opposing_double_butt_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a splined opposing double butt joint example.

    Two butt timbers approach a receiving timber (post) from opposite directions.

    Args:
        position: Center position of the joint (V3)

    Returns:
        List of CutTimber objects representing the joint (empty while stubbed)
    """
    arrangement = create_canonical_example_opposing_double_butt_joint_timbers(position=position)
    try:
        joint = cut_splined_opposing_double_butt_joint(arrangement)
        return list(joint.cut_timbers.values())
    except NotImplementedError:
        return []


def create_double_butt_joints_patternbook() -> PatternBook:
    """
    Create a PatternBook with all double butt joint patterns.

    Returns:
        PatternBook containing all double butt joint patterns
    """
    patterns = [
        (PatternMetadata("splined_opposing_double_butt_joint", ["double_butt_joints", "splined_opposing"], "frame"),
         lambda center: Frame(cut_timbers=make_splined_opposing_double_butt_joint_example(center), name="Splined Opposing Double Butt Joint")),
    ]

    return PatternBook(patterns=patterns)


patternbook = create_double_butt_joints_patternbook()


def create_all_double_butt_joint_examples() -> Union[Frame, List]:
    """
    Create double butt joint examples with automatic spacing starting from the origin.

    Returns:
        Frame or List: Frame object containing all cut timbers, or list of CSG objects
    """
    book = create_double_butt_joints_patternbook()
    frame = book.raise_pattern_group("double_butt_joints", separation_distance=Rational(2))
    return frame


example = create_all_double_butt_joint_examples()
