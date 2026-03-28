"""
GiraffeCAD - Double butt joint construction functions
Contains functions for creating joints where two butt timbers meet a single receiving timber.
"""

from code_goes_here.timber import *
from code_goes_here.construction import *
from code_goes_here.rule import *
from .joint_shavings import *


def cut_splined_opposing_double_butt_joint(arrangement: DoubleButtJointTimberArrangement,
                                           # the slot facing this end of the receiving timber
                                           slot_facing_end_on_receiving_timber: TimberReferenceEnd,
                                           # thickness is in the axis perpendicular to the joint plane
                                           slot_thickness: Numeric,
                                           # depth is in the axis of the receiving timber, measured from the face of the butt timber that alines with slot_facing_end_on_receiving_timber
                                           slot_depth: Numeric,
                                           # length is in the axis parallel to the butt timbers
                                           spline_length: Numeric,
                                           # the spline has this much extra depth beyond the slot depth
                                           spline_extra_depth: Optional[Numeric],
                                           # the slot extends this much beyond the spline on each end so that there is clearance 
                                           slot_symmetric_extra_length: Optional[Numeric],
                                           # inset the shoulder plane on both sides by this amount, flush with faces of receiving timber if 0
                                           shoulder_symmetric_inset: Optional[Numeric],
                                           # offset the solt by this much, measured relative to receiving timber centerline and in the axis perpendicular to the joint plane and 
                                           slot_lateral_offset = 0,
                                           ) -> Joint:
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

    # slot face on butt1
    slot_direction = arrangement.receiving_timber.get_face_direction_global(slot_facing_end_on_receiving_timber)
    slot_face_butt1 = arrangement.butt_timber_1.get_face_global(arrangement.butt_timber_1_end)
    slot_face_butt2 = arrangement.butt_timber_2.get_face_global(arrangement.butt_timber_2_end)

    # TODO assert that the 2 solt faces on the butt timbers are in the same plane

    # build negative CSG by creating a prism that covers the entire symmetric slot 
    # this should be centered the receiving timber centerline with lateral offset applied. he length position on the receiving timber is determined by where the slot butt face intersects the receiving timber
    slot_length = spline_length + 2*slot_symmetric_extra_length
    
    # create shoulder planes for butt1 and butt2 with the receiving timbemr and shoulder_symmetric_inset to generate the end cuts

    # create a CSG for the spline accesory, it should match the slot except 

    raise NotImplementedError("cut_splined_opposing_double_butt_joint is not yet implemented")
