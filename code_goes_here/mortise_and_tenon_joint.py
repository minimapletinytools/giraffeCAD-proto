"""
GiraffeCAD - Mortise and Tenon Joint Construction Functions
Contains various mortise and tenon joint implementations
"""

from code_goes_here.timber import *
from code_goes_here.construction import *
from code_goes_here.moothymoth import (
    Orientation,
    EPSILON_GENERIC,
    zero_test,
    construction_parallel_check,
    construction_perpendicular_check
)

# Explicitly import private helper functions used by joint functions
from code_goes_here.construction import (
    _are_directions_perpendicular,
    _are_timbers_face_aligned,
    _are_timbers_face_orthogonal,
    _calculate_mortise_position_from_tenon_intersection,
    _calculate_distance_from_timber_end_to_shoulder_plane
)

# ============================================================================
# Mortise and Tenon Joint Construction Functions
# ============================================================================



f""" impl notes

this function is very generic and does a bunch of things. in particluar we want the following variants which will all call into this function;

      -mortise and tenon
      -through mortise and tenon
      -wedged mortise and tenon
      -wedged through mortise and tenon
      -fox wedge mortise and tenon
      -draw bore mortise and tenon
      -Hōzo-zashi Komisen-dome (ほぞ差し込み栓止め)
        -same as draw bore but with komisen peg,
      -tusked mortise and tenon (explicitly not supported, will be a separate function due to needing to support more angles of insertion)

so we need to support the folowing features:


PEGS
pegs (could be round or rectangular), rectangular pegs can be inserted at an angle
class RoundPeg
class RectangularPeg:
    size1: Numeric # consistent rule of which axis this is w.r.t to the tenon timber
    size2: Numeric # consistent rule of which axis this is w.r.t to the tenon timber
    rotation: angle in degrees # clockwise rotation when looking at the peg from the insertion side
pegs are always orthogonal to the length axis of the 2 timbers, but they can go in from either side, specified 

"""



def cut_mortise_and_tenon_joint(mortise_timber: Timber, tenon_timber: Timber,
                                 tenon_end: TimberReferenceEnd) -> Joint:
    """
    Creates a mortise and tenon joint between two timbers.
    
    Args:
        mortise_timber: Timber that will receive the mortise cut
        tenon_timber: Timber that will receive the tenon cut
        tenon_end: Which end of the tenon timber the tenon will be cut from
        
    Returns:
        Joint object containing the two PartiallyCutTimbers
        
    Raises:
        NotImplementedError: This function is not yet implemented
    """
    # TODO: Implement this function
    raise NotImplementedError("cut_mortise_and_tenon_joint is not yet implemented")



def cut_simple_mortise_and_tenon_joint_on_face_aligned_timbers(mortise_timber: Timber, tenon_timber: Timber,
                                                          tenon_end: TimberReferenceEnd,
                                                          tenon_thickness: Numeric, tenon_length: Numeric) -> Joint:
    """
    Creates a mortise and tenon joint for face-aligned timbers.
    
    Args:
        mortise_timber: Timber that will receive the mortise cut
        tenon_timber: Timber that will receive the tenon cut
        tenon_end: Which end of the tenon timber the tenon will be cut from
        tenon_thickness: Width and height of the tenon
        tenon_length: Length of the tenon extending from mortise face of the mortise timber
        
    Raises:
        AssertionError: If timbers are not properly oriented for this joint type
    """
    # Verify that the timbers are face-aligned and orthogonal
    # Face-aligned means they share the same coordinate grid alignment  
    assert _are_timbers_face_aligned(mortise_timber, tenon_timber), \
        "Timbers must be face-aligned (orientations related by 90-degree rotations) for this joint type"
    
    # Verify that the timbers are orthogonal (perpendicular length directions)
    # This is required for proper mortise and tenon joint geometry
    assert _are_timbers_face_orthogonal(mortise_timber, tenon_timber), \
        "Timbers must be orthogonal (perpendicular length directions) for this joint type"
    
    # TODO: Create the joint (when implemented, use new Joint constructor)
    # joint = Joint(partially_cut_timbers=[...], joint_accessories=[])
    
    # Compute the mortise face by finding which face of the mortise timber 
    # aligns with the tenon end face
    tenon_end_direction = tenon_timber.get_face_direction(TimberFace.TOP if tenon_end == TimberReferenceEnd.TOP else TimberFace.BOTTOM)
    mortise_face = mortise_timber.get_closest_oriented_face(-tenon_end_direction)
    
    # Calculate the correct mortise position based on tenon timber intersection
    mortise_ref_end, mortise_distance = _calculate_mortise_position_from_tenon_intersection(
        mortise_timber, tenon_timber, tenon_end
    )
    
    # Calculate tenon shoulder plane distance to position it at the mortise timber face
    tenon_shoulder_distance = _calculate_distance_from_timber_end_to_shoulder_plane(tenon_timber, mortise_timber, tenon_end)
    
    # TODO FINISH
    raise NotImplementedError("Not implemented")
