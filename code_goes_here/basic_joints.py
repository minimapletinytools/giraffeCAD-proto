"""
GiraffeCAD - Basic joint construction functions
Contains functions for creating joints between timbers
"""

from code_goes_here.timber import *
from code_goes_here.construction import *

# Explicitly import private helper functions used by joint functions
from code_goes_here.construction import (
    _are_directions_perpendicular,
    _are_timbers_face_aligned,
    _are_timbers_face_orthogonal,
    _calculate_mortise_position_from_tenon_intersection,
    _calculate_distance_from_timber_end_to_shoulder_plane
)

# ============================================================================
# Joint Construction Functions
# ============================================================================


def cut_basic_miter_joint(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic miter joint between two timbers such that the 2 ends meet and each has a miter cut at half the angle between the two timbers.
    
    Args:
        timberA: First timber to join
        timberA_end: Which end of timberA to cut (TOP or BOTTOM)
        timberB: Second timber to join
        timberB_end: Which end of timberB to cut (TOP or BOTTOM)
        
    Returns:
        Joint object containing the two PartiallyCutTimbers
        
    Raises:
        ValueError: If the timbers are parallel or if they don't intersect
    """
    import warnings
    
    # Get the end directions for each timber (pointing outward from the timber)
    if timberA_end == TimberReferenceEnd.TOP:
        directionA = timberA.length_direction
        endA_position = timberA.get_top_center_position()
    else:  # BOTTOM
        directionA = -timberA.length_direction 
        endA_position = timberA.get_bottom_center_position()
    
    if timberB_end == TimberReferenceEnd.TOP:
        directionB = timberB.length_direction
        endB_position = timberB.get_top_center_position()
    else:  # BOTTOM
        directionB = -timberB.length_direction
        endB_position = timberB.get_bottom_center_position()
    
    # Check that the timbers are not parallel
    cross = cross_product(directionA, directionB)
    if vector_magnitude(cross) < EPSILON_PARALLEL:
        raise ValueError("Timbers cannot be parallel for a miter joint")
    
    # Find the intersection point (or closest point) between the two timber centerlines
    # Using the formula for closest point between two lines in 3D
    # Line 1: P1 = endA_position + t * directionA
    # Line 2: P2 = endB_position + s * directionB
    
    w0 = endA_position - endB_position
    a = directionA.dot(directionA)  # always >= 0
    b = directionA.dot(directionB)
    c = directionB.dot(directionB)  # always >= 0
    d = directionA.dot(w0)
    e = directionB.dot(w0)
    
    denom = a * c - b * b
    if abs(denom) < EPSILON_DEGENERATE:
        raise ValueError("Cannot compute intersection point (degenerate case)")
    
    # Parameters for closest points on each line
    t = (b * e - c * d) / denom
    s = (a * e - b * d) / denom
    
    # Get the closest points on each centerline
    pointA = endA_position + directionA * t
    pointB = endB_position + directionB * s
    
    # The intersection point is the midpoint between the two closest points
    intersection_point = (pointA + pointB) / 2
    
    # TODO what's this for??? delete this... linse are allowed to be skew
    # Warn if the lines don't actually intersect (skew lines)
    distance_between = vector_magnitude(pointA - pointB)
    if distance_between > THRESHOLD_SKEW_LINE_WARNING:
        warnings.warn(f"Timber centerlines are skew lines (closest distance: {float(distance_between)}). Using midpoint of closest approach.")
    
    # Create the miter plane normal
    # Normalize the directions first
    normA = normalize_vector(directionA)
    normB = normalize_vector(directionB)
    
    # The bisecting direction is the normalized sum of the two directions
    # This points "into" the joint (towards the acute angle)
    # IMPORTANT: The bisector lives IN the miter plane (it's the line you draw on the wood)
    bisector = normalize_vector(normA + normB)
    
    # The plane formed by the two timber directions has normal:
    plane_normal = cross_product(normA, normB)
    
    # The miter plane:
    # 1. Contains the bisector line
    # 2. Is perpendicular to the plane formed by directionA and directionB
    # Therefore, the miter plane's normal is perpendicular to both the bisector
    # and the plane_normal. This is the cross product: bisector × plane_normal
    miter_normal = normalize_vector(cross_product(bisector, plane_normal))
    
    # The miter plane passes through the intersection point
    # Both timbers will be cut by this same plane, but each timber needs its half-plane
    # normal oriented to point "away from" that timber (into the material to remove).
    
    # For each timber, we need to create a HalfPlaneCut with the miter plane
    # The key is that the half-plane normal must be oriented so that:
    # 1. It represents the miter plane (normal perpendicular to the bisector line)
    # 2. The normal points "away from" the timber (into the material to remove)
    #
    # The miter_normal is perpendicular to both the bisector and the plane formed by
    # the two timbers. For each timber, we need to determine which orientation of the
    # miter plane normal points "away from" that timber.
    #
    # If directionA · miter_normal > 0, then miter_normal points away from timberA,
    # so we use +miter_normal. Otherwise, we use -miter_normal.
    
    # For timberA: check if miter_normal points away from or towards the timber
    dot_A = (normA.T * miter_normal)[0, 0]
    if dot_A > 0:
        # Miter normal points away from timberA (in the direction of timberA's end)
        # This is what we want - the half-plane removes material in this direction
        normalA = miter_normal
    else:
        # Miter normal points towards timberA, so flip it
        normalA = -miter_normal
    
    # Convert to LOCAL coordinates for timberA
    # Transform normal: local_normal = orientation^T * global_normal
    # Transform offset: local_offset = global_offset - (global_normal · timber.bottom_position)
    local_normalA = timberA.orientation.matrix.T * normalA
    local_offsetA = (intersection_point.T * normalA)[0, 0] - (normalA.T * timberA.bottom_position)[0, 0]
    
    # For timberB: check if miter_normal points away from or towards the timber
    dot_B = (normB.T * miter_normal)[0, 0]
    if dot_B > 0:
        # Miter normal points away from timberB (in the direction of timberB's end)
        normalB = miter_normal
    else:
        # Miter normal points towards timberB, so flip it
        normalB = -miter_normal
    
    # Convert to LOCAL coordinates for timberB
    local_normalB = timberB.orientation.matrix.T * normalB
    local_offsetB = (intersection_point.T * normalB)[0, 0] - (normalB.T * timberB.bottom_position)[0, 0]
    
    # Create the HalfPlaneCuts (in LOCAL coordinates relative to each timber)
    cutA = HalfPlaneCut()
    cutA._timber = timberA
    cutA.origin = intersection_point
    cutA.orientation = timberA.orientation
    cutA.maybeEndCut = timberA_end
    cutA.half_plane = HalfPlane(normal=local_normalA, offset=local_offsetA)
    
    cutB = HalfPlaneCut()
    cutB._timber = timberB
    cutB.origin = intersection_point
    cutB.orientation = timberB.orientation
    cutB.maybeEndCut = timberB_end
    cutB.half_plane = HalfPlane(normal=local_normalB, offset=local_offsetB)
    
    # Create PartiallyCutTimbers
    cut_timberA = PartiallyCutTimber(timberA, name=f"TimberA_Miter")
    cut_timberA._cuts.append(cutA)
    
    cut_timberB = PartiallyCutTimber(timberB, name=f"TimberB_Miter")
    cut_timberB._cuts.append(cutB)
    
    # Create and return the Joint
    joint = Joint()
    joint.partiallyCutTimbers = [cut_timberA, cut_timberB]
    joint.jointAccessories = []
    
    return joint

def cut_basic_miter_joint_on_face_aligned_timbers(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic miter joint between two timbers such that the 2 ends meet at a 90 degree angle miter corner.
    """
    # Assert that the timber length axes are perpendicular (90-degree corner)
    assert _are_directions_perpendicular(timberA.length_direction, timberB.length_direction), \
        "Timbers must have perpendicular length axes (90-degree angle) for this joint type"
    
    return cut_basic_miter_joint(timberA, timberA_end, timberB, timberB_end)
    

def cut_basic_corner_joint_on_face_aligned_timbers(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic end joint between two timbers such that the 2 ends meet at a 90 degree angle corner.
    """
    return cut_basic_miter_joint_on_face_aligned_timbers(timberA, timberA_end, timberB, timberB_end)



def cut_basic_butt_joint_on_face_aligned_timbers(receiving_timber: Timber, butt_timber: Timber, butt_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic butt joint between two timbers. The butt timber is cut flush with the face 
    of the receiving timber. The receiving timber has no cuts.
    
    Args:
        receiving_timber: The timber that receives the butt (remains uncut)
        butt_timber: The timber whose end is cut to meet the receiving timber's face
        butt_end: Which end of the butt timber to cut (TOP or BOTTOM)
        
    Returns:
        Joint object containing the cut butt timber and uncut receiving timber
    """
    assert _are_timbers_face_aligned(receiving_timber, butt_timber), \
        "Timbers must be face-aligned (orientations related by 90-degree rotations) for this joint type"
    
    # Get the direction of the butt end (pointing outward from the timber)
    if butt_end == TimberReferenceEnd.TOP:
        butt_direction = butt_timber.length_direction
        butt_end_position = butt_timber.get_top_center_position()
    else:  # BOTTOM
        butt_direction = -butt_timber.length_direction
        butt_end_position = butt_timber.get_bottom_center_position()
    
    # Find which face of the receiving timber the butt is approaching
    # The butt approaches opposite to its end direction
    receiving_face = receiving_timber.get_closest_oriented_face(-butt_direction)
    receiving_face_direction = receiving_timber.get_face_direction(receiving_face)
    
    # Compute the center position of the receiving face
    if receiving_face == TimberFace.TOP:
        face_center = receiving_timber.get_top_center_position()
    elif receiving_face == TimberFace.BOTTOM:
        face_center = receiving_timber.get_bottom_center_position()
    else:
        # For long faces (LEFT, RIGHT, FORWARD, BACK), center is at mid-length
        face_center = receiving_timber.bottom_position + (receiving_timber.length / 2) * receiving_timber.length_direction
        
        # Offset to the face surface
        if receiving_face == TimberFace.RIGHT:
            face_center = face_center + (receiving_timber.size[0] / 2) * receiving_timber.width_direction
        elif receiving_face == TimberFace.LEFT:
            face_center = face_center - (receiving_timber.size[0] / 2) * receiving_timber.width_direction
        elif receiving_face == TimberFace.FORWARD:
            face_center = face_center + (receiving_timber.size[1] / 2) * receiving_timber.height_direction
        else:  # BACK
            face_center = face_center - (receiving_timber.size[1] / 2) * receiving_timber.height_direction
    
    # The cutting plane is at the receiving face, with normal pointing INWARD
    # (toward the receiving timber body). This ensures we remove material on the
    # butt timber that's on the opposite side from the receiving timber.
    # For example, if a post sits on top of a mudsill (mudsill's top face),
    # we remove the part of the post that extends below the mudsill.
    global_normal = -receiving_face_direction
    
    # Convert to LOCAL coordinates for the butt timber
    local_normal = butt_timber.orientation.matrix.T * global_normal
    local_offset = (face_center.T * global_normal)[0, 0] - (global_normal.T * butt_timber.bottom_position)[0, 0]
    
    # Create the HalfPlaneCut for the butt timber
    cut = HalfPlaneCut()
    cut._timber = butt_timber
    cut.origin = face_center
    cut.orientation = butt_timber.orientation
    cut.maybeEndCut = butt_end
    cut.half_plane = HalfPlane(normal=local_normal, offset=local_offset)
    
    # Create PartiallyCutTimber for the butt timber
    cut_butt = PartiallyCutTimber(butt_timber, name=f"ButtTimber")
    cut_butt._cuts.append(cut)
    
    # Create PartiallyCutTimber for the receiving timber (no cuts)
    cut_receiving = PartiallyCutTimber(receiving_timber, name=f"ReceivingTimber")
    
    # Create and return the Joint
    joint = Joint()
    joint.partiallyCutTimbers = [cut_receiving, cut_butt]
    joint.jointAccessories = []
    
    return joint


def cut_basic_splice_joint_on_aligned_timbers(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd, splice_point: Optional[V3]) -> Joint:
    """
    Creates a basic splice joint between two timbers. The butt timber is extended to meet the face of the receiving timber.

    If splice_point is not provided, it is calculated as the midpoint of the two timbers.

    If splice_point is provided, it should be on the centerline of timberA. If not, it is projected onto it..
    """
    # TODO assert length axis are parallel 
    # TODO check that timber cross sections overlap and if not, output a warning
    # if splice_point is not provided, calculate it as the midpoint of the two timbers
    # TODO check that splice_point is on the centerline of timberA, if not, output a warning and project it onto the centerline
    # create the splice plane based on the position of the splice point
    # return the cut by the splice plane on both timbers as a joint
    return None



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
    
    # Create the joint
    joint = Joint()
    
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
    

