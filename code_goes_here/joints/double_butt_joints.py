"""
GiraffeCAD - Double butt joint construction functions
Contains functions for creating joints where two butt timbers meet a single receiving timber.
"""

from code_goes_here.timber import *
from code_goes_here.construction import *
from code_goes_here.rule import *
from .joint_shavings import *


def cut_splined_opposing_double_butt_joint(arrangement: DoubleButtJointTimberArrangement) -> Joint:
    """
    Creates a splined opposing double butt joint.

    Two butt timbers approach the receiving timber from opposite cardinal directions.
    All three timbers must be face-aligned, each butt timber must be perpendicular to the
    receiving timber, and the two butt timbers must be antiparallel.

    Args:
        arrangement: Double butt joint arrangement with butt_timber_1, butt_timber_2,
            receiving_timber, butt_timber_1_end, butt_timber_2_end.

    Returns:
        Joint containing all three cut timbers.

    Raises:
        AssertionError: If the arrangement fails the cardinal-and-opposing-butts check.
    """
    error = arrangement.check_face_aligned_cardinal_and_opposing_butts()
    assert error is None, error

    raise NotImplementedError("cut_splined_opposing_double_butt_joint is not yet implemented")
