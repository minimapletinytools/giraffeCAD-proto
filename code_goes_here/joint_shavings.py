"""
Joint Helper Functions (joint_shavings.py)

Collection of helper functions for validating and checking timber joint configurations.
These functions help ensure that joints are geometrically valid and sensibly constructed.
"""

from typing import Optional, Tuple, List, Union
from code_goes_here.timber import Timber, TimberReferenceEnd, TimberFace, TimberReferenceLongFace
from code_goes_here.moothymoth import EPSILON_GENERIC, are_vectors_parallel, Numeric, Transform, create_v3, create_v2, Orientation, V2, V3, are_vectors_perpendicular, zero_test
from code_goes_here.meowmeowcsg import Prism, HalfPlane, MeowMeowCSG, SolidUnion, ConvexPolygonExtrusion
from code_goes_here.construction import are_timbers_face_aligned, do_xy_cross_section_on_parallel_timbers_overlap
from sympy import Abs, Rational



    

def orientation_pointing_towards_face_sitting_on_face(towards_face : TimberFace, sitting_face : TimberFace) -> 'Orientation':
    """
    marking orientations live within a timber's local space and are used to help mark joint features on the timber. They can be anything, but in general they should be chosen such that:
    for marking_transforms on the surface of the timber the "+y" should point into the timber
    """
    assert are_vectors_perpendicular(towards_face.get_direction(), sitting_face.get_direction())
    return Orientation.from_z_and_y(towards_face.get_direction(), -sitting_face.get_direction())

    

def find_opposing_face_on_another_timber(reference_timber: Timber, reference_face: TimberReferenceLongFace, target_timber: Timber) -> TimberFace:
    """
    Find the opposing face on another timber. Assumes that the target_timber has a face parallel to the reference face on the reference_timber.
    """
    target_face = target_timber.get_closest_oriented_face_from_global_direction(-reference_timber.get_face_direction_global(reference_face))

    # assert that the target_face is parallel to the reference_face
    assert are_vectors_parallel(reference_timber.get_face_direction_global(reference_face), target_timber.get_face_direction_global(target_face)), \
        f"Target face {target_face} is not parallel to reference face {reference_face} on timber {reference_timber.name}"
    
    return target_face

def find_face_plane_intersection_on_centerline(face: TimberFace, face_timber: Timber, to_timber: Timber, to_timber_end: TimberReferenceEnd) -> Numeric:
    """
    Find the distance from to_timber_end on to_timber to the face on face_timber.
    
    This method "scribes" a measurement from a specific end of one timber (to_timber) 
    along its centerline to where it intersects (or would intersect) with a face of 
    another timber (face_timber). This is useful for finding shoulder plane positions 
    in various butt joints.
    
    The distance is measured along to_timber's length direction from the specified end.
    Positive distance means the face is in the direction away from the end (into the timber).
    
    Args:
        face: The face on face_timber to measure to
        face_timber: The timber whose face we're measuring to
        to_timber: The timber we're measuring from
        to_timber_end: Which end of to_timber to measure from (TOP or BOTTOM)
    
    Returns:
        The signed distance along to_timber's centerline from to_timber_end to 
        the plane of the specified face on face_timber
    
    Example:
        >>> # Find where to place a shoulder on timber_a when it butts against timber_b's FRONT face
        >>> shoulder_distance = find_face_plane_intersection_on_centerline(
        ...     face=TimberFace.FRONT,
        ...     face_timber=timber_b,
        ...     to_timber=timber_a,
        ...     to_timber_end=TimberReferenceEnd.TOP
        ... )
    """
    
    # Get the center point on the face of face_timber
    # A face center is at mid-length for long faces, mid-cross-section for the face surface
    face_direction = face_timber.get_face_direction_global(face)
    face_offset = face_timber.get_size_in_face_normal_axis(face) / Rational(2)
    
    # For long faces (LEFT, RIGHT, FRONT, BACK), the center is at mid-length
    # For end faces (TOP, BOTTOM), the center is at the end
    if face == TimberFace.TOP or face == TimberFace.BOTTOM:
        # End face: use the end center position
        if face == TimberFace.TOP:
            face_center_point = face_timber.get_top_center_position_global()
        else:  # BOTTOM
            face_center_point = face_timber.get_bottom_center_position_global()
    else:
        # Long face: center is at mid-length, offset by face normal
        face_center_point = (face_timber.get_bottom_position_global() + 
                            face_timber.get_length_direction_global() * (face_timber.length / Rational(2)) +
                            face_direction * face_offset)
    
    # Get the end position on to_timber
    if to_timber_end == TimberReferenceEnd.TOP:
        end_position = to_timber.get_top_center_position_global()
        # Direction from end into timber is negative length direction
        into_timber_direction = -to_timber.get_length_direction_global()
    else:  # BOTTOM
        end_position = to_timber.get_bottom_center_position_global()
        # Direction from end into timber is positive length direction
        into_timber_direction = to_timber.get_length_direction_global()
    
    # Calculate the vector from the end position to the face center
    vector_to_face = face_center_point - end_position
    
    # Project this vector onto the into_timber_direction to get the signed distance
    # Distance is positive if the face is in the direction away from the end
    signed_distance = (vector_to_face.T * into_timber_direction)[0, 0]
    
    return signed_distance

def find_projected_intersection_on_centerlines(timberA: Timber, timberB: Timber, timberA_end: TimberReferenceEnd = TimberReferenceEnd.BOTTOM, timberB_end: TimberReferenceEnd = TimberReferenceEnd.BOTTOM) -> (Numeric, Numeric):
    """
    Find the projected intersection of the centerlines of two timbers.
    That is to say ,there is 1 unique line that connects the centerlines of the two timbers, 
    this function finds the point on each centerline that is closest to the other centerline.

    Args:
        timberA: First timber
        timberB: Second timber
        timberA_end: Which end of timberA to measure from (defaults to BOTTOM)
        timberB_end: Which end of timberB to measure from (defaults to BOTTOM)

    Returns:
        a tuple of the respective points on each timber 
        (distance from timberA_end, distance from timberB_end)
    """
    # Get the starting points for each centerline (at the specified ends)
    if timberA_end == TimberReferenceEnd.TOP:
        pointA = timberA.get_bottom_position_global() + timberA.length * timberA.get_length_direction_global()
    else:  # BOTTOM
        pointA = timberA.get_bottom_position_global()
    
    if timberB_end == TimberReferenceEnd.TOP:
        pointB = timberB.get_bottom_position_global() + timberB.length * timberB.get_length_direction_global()
    else:  # BOTTOM
        pointB = timberB.get_bottom_position_global()
    
    # Direction vectors for each centerline
    dirA = timberA.get_length_direction_global()
    dirB = timberB.get_length_direction_global()
    
    # Solve for closest points on two 3D lines using the standard formula
    # Line A: pointA + t_A * dirA
    # Line B: pointB + t_B * dirB
    # We need to find t_A and t_B such that the connecting vector is perpendicular to both directions
    
    w = pointA - pointB  # Vector between starting points
    
    a = dirA.dot(dirA)  # Should be 1 for normalized directions
    b = dirA.dot(dirB)
    c = dirB.dot(dirB)  # Should be 1 for normalized directions
    d = w.dot(dirA)
    e = w.dot(dirB)
    
    denominator = a * c - b * b
    
    # Check if lines are parallel (denominator near zero)
    if zero_test(denominator):
        # Lines are parallel - any perpendicular works, use starting points
        distanceA = Rational(0)
        distanceB = Rational(0)
    else:
        # Calculate parameters for closest points
        t_A = (b * e - c * d) / denominator
        t_B = (a * e - b * d) / denominator
        
        # Return distances from the specified ends
        distanceA = t_A
        distanceB = t_B
    
    return (distanceA, distanceB) 

# TODO this can be replaced with your magical scribe1d function lol
def measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
    reference_timber: Timber,
    reference_face: TimberReferenceLongFace,
    reference_depth_from_face: Numeric,
    target_timber: Timber
) -> Numeric:
    """
    Measure the distance from a plane (at a given depth from a timber long face) to the opposing face on another timber.

    Expects the target timber to have a long face parallel to the reference face.
    
    This is useful for calculating depths for lap cuts between 2 timbers.
    For example, in a splice lap joint, the top timber's cutting plane may not align perfectly with the
    bottom timber's cross-section due to rotation.
    
    Args:
        reference_timber: The timber with the reference face
        reference_face: The long face on the reference timber (not an end face)
        reference_depth_from_face: Distance from the reference face (inward) where the cutting plane is
        target_timber: The timber whose opposing face we want to measure to (must have a long face parallel to reference_face)
        
    Returns:
        The distance from the cutting plane to the target timber's opposing face
        
    Example:
        >>> # Measure how deep to cut the bottom timber based on where the top timber's cut plane is
        >>> bottom_depth = measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
        ...     reference_timber=top_timber,
        ...     reference_face=TimberReferenceLongFace.BACK,
        ...     reference_depth_from_face=lap_depth,
        ...     target_timber=bottom_timber
        ... )
    """
    from sympy import Rational
    
    # Assert that the target timber has a long face parallel to the reference face
    reference_face_direction = reference_timber.get_face_direction_global(reference_face)
    target_long_faces = [TimberReferenceLongFace.RIGHT, TimberReferenceLongFace.LEFT, 
                         TimberReferenceLongFace.FRONT, TimberReferenceLongFace.BACK]
    
    has_parallel_face = False
    for target_face in target_long_faces:
        target_face_direction = target_timber.get_face_direction_global(target_face)
        if are_vectors_parallel(reference_face_direction, target_face_direction):
            has_parallel_face = True
            break
    
    assert has_parallel_face, \
        f"Target timber {target_timber.name} must have a long face parallel to reference face {reference_face.name} " \
        f"on timber {reference_timber.name}. Reference face direction: {reference_face_direction.T}"
    
    # Get a point on the reference face
    reference_face_offset = reference_timber.get_size_in_face_normal_axis(reference_face) / Rational(2)
    reference_face_point = reference_timber.get_bottom_position_global() + reference_face_direction * reference_face_offset
    
    # Calculate the cutting plane point (moved inward by reference_depth_from_face)
    cutting_plane_point = reference_face_point - reference_face_direction * reference_depth_from_face
    cutting_plane_normal = reference_face_direction
    
    # Find the opposing face on the target timber
    target_face_direction = -reference_face_direction  # Opposite direction
    target_face = target_timber.get_closest_oriented_face_from_global_direction(target_face_direction)
    
    # Get a point on the target timber's opposing face
    target_face_offset = target_timber.get_size_in_face_normal_axis(target_face) / Rational(2)
    target_face_point = target_timber.get_bottom_position_global() + target_timber.get_face_direction_global(target_face) * target_face_offset
    
    # Calculate the signed distance from the cutting plane to the target face point
    # Distance = (target_face_point - cutting_plane_point) · cutting_plane_normal
    distance_vector = target_face_point - cutting_plane_point
    signed_distance = (distance_vector.T * cutting_plane_normal)[0, 0]
    
    # Return the absolute distance (depth is always positive)
    return Abs(signed_distance)


def check_timber_overlap_for_splice_joint_is_sensible(
    timberA: Timber,
    timberB: Timber,
    timberA_end: TimberReferenceEnd,
    timberB_end: TimberReferenceEnd
) -> Optional[str]:
    """
    Check if two timbers overlap in a sensible way for a splice joint.
    
    A sensible splice joint configuration requires:
    1. The joint ends are pointing in opposite directions (anti-parallel)
    2. The joint end planes either touch each other or go past each other
    3. The joint end planes have not gone so far past each other that they reach 
       the opposite end of the other timber
    
    ASCII diagram of a sensible splice joint:
    A |==================| <- timberA_end
       timberB_end -> |==================| B
    
    Args:
        timberA: First timber in the splice joint
        timberB: Second timber in the splice joint
        timberA_end: Which end of timberA is being joined (TOP or BOTTOM)
        timberB_end: Which end of timberB is being joined (TOP or BOTTOM)
    
    Returns:
        Optional[str]: None if the configuration is sensible, otherwise a string
                      explaining why the configuration fails the sensibility check
    
    Example:
        >>> error = check_timber_overlap_for_splice_joint_is_sensible(
        ...     gooseneck, receiving, TimberReferenceEnd.BOTTOM, TimberReferenceEnd.TOP
        ... )
        >>> if error:
        ...     print(f"Joint configuration error: {error}")
    """
    # Get the length directions for both timbers
    timberA_length_direction = timberA.get_length_direction_global()
    timberB_length_direction = timberB.get_length_direction_global()
    
    # First, check that timbers are parallel (not perpendicular or skewed)
    dot_product = timberA_length_direction.dot(timberB_length_direction)
    
    if not are_vectors_parallel(timberA_length_direction, timberB_length_direction):
        return (
            f"Timbers are not parallel. TimberA length direction {timberA_length_direction.T} "
            f"and timberB length direction {timberB_length_direction.T} must be parallel "
            f"(dot product should be ±1, got {float(dot_product):.3f})"
        )
    
    # Get the end positions and directions in world coordinates
    # Note: end_direction points AWAY from the timber (outward from the end)
    if timberA_end == TimberReferenceEnd.TOP:
        timberA_end_pos = timberA.get_top_center_position_global()
        timberA_end_direction = timberA.get_length_direction_global()  # Points away from timber
        timberA_opposite_end_pos = timberA.get_bottom_position_global()
    else:  # BOTTOM
        timberA_end_pos = timberA.get_bottom_position_global()
        timberA_end_direction = -timberA.get_length_direction_global()  # Points away from timber
        timberA_opposite_end_pos = timberA.get_top_center_position_global()
    
    if timberB_end == TimberReferenceEnd.TOP:
        timberB_end_pos = timberB.get_top_center_position_global()
        timberB_end_direction = timberB.get_length_direction_global()  # Points away from timber
        timberB_opposite_end_pos = timberB.get_bottom_position_global()
    else:  # BOTTOM
        timberB_end_pos = timberB.get_bottom_position_global()
        timberB_end_direction = -timberB.get_length_direction_global()  # Points away from timber
        timberB_opposite_end_pos = timberB.get_top_center_position_global()
    
    # Check 1: The joint ends must be pointing in opposite directions (anti-parallel)
    # For a proper splice joint, the specified ends should point towards each other
    # (dot product of end directions should be close to -1)
    end_dot_product = timberA_end_direction.dot(timberB_end_direction)
    
    if end_dot_product > 0:
        return (
            f"Joint ends are pointing in the same direction (dot product = {float(end_dot_product):.3f}). "
            f"For a splice joint, the ends should point in opposite directions (dot product should be -1). "
            f"TimberA {timberA_end.name} end direction: {timberA_end_direction.T}, "
            f"TimberB {timberB_end.name} end direction: {timberB_end_direction.T}"
        )
    
    # Check 2: The joint ends should either touch or overlap (not be separated)
    # Vector from timberA end to timberB end
    end_to_end_vector = timberB_end_pos - timberA_end_pos
    
    # Project this vector onto timberA's end direction
    # If positive, timberB end is in the direction timberA end is pointing (they overlap or touch)
    # If negative, timberB end is behind timberA end (they're separated)
    projection_A = end_to_end_vector.dot(timberA_end_direction)
    
    # Also check from timberB's perspective
    projection_B = -end_to_end_vector.dot(timberB_end_direction)
    
    # For a valid splice, at least one timber should be extending towards or past the other
    # Both projections should be >= 0 (allowing for small numerical errors)
    gap_threshold = -EPSILON_GENERIC * 10  # Allow small numerical errors
    
    if projection_A < gap_threshold and projection_B < gap_threshold:
        return (
            f"Joint ends are separated by a gap. The ends should touch or overlap. "
            f"Distance from timberA end to timberB end along timberA direction: {float(projection_A):.6f}. "
            f"Distance from timberB end to timberA end along timberB direction: {float(projection_B):.6f}"
        )
    
    # Check 3: The joint ends should not have gone so far past each other that they 
    # reach the opposite end of the other timber
    
    # Check if timberA end has passed through timberB's opposite end
    # Vector from timberB's opposite end to timberA's end
    vector_to_timberA_end = timberA_end_pos - timberB_opposite_end_pos
    # Project onto timberB's end direction (pointing from joined end towards opposite end)
    penetration_into_B = vector_to_timberA_end.dot(-timberB_end_direction)
    
    # If positive and large, timberA has penetrated through timberB
    if penetration_into_B > timberB.length + EPSILON_GENERIC:
        return (
            f"TimberA end has penetrated too far through timberB. "
            f"TimberA end extends {float(penetration_into_B):.3f} past timberB's joined end, "
            f"but timberB is only {float(timberB.length):.3f} long. "
            f"The joint should not extend past the opposite end of the timber."
        )
    
    # Check if timberB end has passed through timberA's opposite end
    vector_to_timberB_end = timberB_end_pos - timberA_opposite_end_pos
    penetration_into_A = vector_to_timberB_end.dot(-timberA_end_direction)
    
    if penetration_into_A > timberA.length + EPSILON_GENERIC:
        return (
            f"TimberB end has penetrated too far through timberA. "
            f"TimberB end extends {float(penetration_into_A):.3f} past timberA's joined end, "
            f"but timberA is only {float(timberA.length):.3f} long. "
            f"The joint should not extend past the opposite end of the timber."
        )
    
    # All checks passed
    return None


# TODO when you add actual dimensions on top of perfect timber within dimensions, you probably want a version that sizes to the actual dimensions...
def chop_timber_end_with_prism(timber: Timber, end: TimberReferenceEnd, distance_from_end_to_cut: Numeric) -> Prism:
    """
    Create a Prism CSG for chopping off material from a timber end (in local coordinates).
    
    Creates a CSG prism in the timber's local coordinate system that starts at 
    distance_from_end_to_cut from the timber end and extends to infinity in the timber 
    length direction. The prism has the same cross-section size as the timber.
    
    This is useful when you need a volumetric cut that exactly matches the timber's 
    cross-section (e.g., for CSGCut objects in compound cuts).
    
    Args:
        timber: The timber to create a chop prism for
        end: Which end to chop from (TOP or BOTTOM)
        distance_from_end_to_cut: Distance from the end where the cut begins
    
    Returns:
        Prism: A CSG prism in local coordinates representing the material beyond 
               distance_from_end_to_cut from the end, extending to infinity
    
    Example:
        >>> # Chop everything beyond 2 inches from the top of a timber
        >>> chop_prism = chop_timber_end_with_prism(my_timber, TimberReferenceEnd.TOP, Rational(2))
        >>> # This creates a semi-infinite prism starting 2 inches from the top
    """
    # In timber local coordinates:
    # - Bottom is at 0
    # - Top is at timber.length
    # - Z-axis points along the length direction (bottom to top)
    
    if end == TimberReferenceEnd.TOP:
        # For TOP end:
        # - Start at (timber.length - distance_from_end_to_cut)
        # - Extend to infinity in the +Z direction (beyond the top)
        start_distance_local = timber.length - distance_from_end_to_cut
        end_distance_local = None  # Infinite in +Z direction
    else:  # BOTTOM
        # For BOTTOM end:
        # - Start at infinity in the -Z direction (below the bottom)
        # - End at distance_from_end_to_cut from the bottom
        start_distance_local = None  # Infinite in -Z direction
        end_distance_local = distance_from_end_to_cut
    
    # Create the prism with identity transform (local coordinates)
    return Prism(
        size=timber.size,
        transform=Transform.identity(),
        start_distance=start_distance_local,
        end_distance=end_distance_local
    )


def chop_timber_end_with_half_plane(timber: Timber, end: TimberReferenceEnd, distance_from_end_to_cut: Numeric) -> HalfPlane:
    """
    Create a HalfPlane CSG for chopping off material from a timber end (in local coordinates).
    
    Creates a half-plane cut in the timber's local coordinate system, perpendicular to the 
    timber's length direction, positioned at distance_from_end_to_cut from the specified end.
    The half-plane removes everything beyond that distance.
    
    This is simpler and more efficient than a prism-based cut when you just need a planar
    cut perpendicular to the timber's length (e.g., for simple butt joints or splice joints).
    
    Args:
        timber: The timber to create a chop half-plane for
        end: Which end to chop from (TOP or BOTTOM)
        distance_from_end_to_cut: Distance from the end where the cut plane is positioned
    
    Returns:
        HalfPlane: A half-plane in local coordinates that removes material beyond 
                   distance_from_end_to_cut from the end
    
    Example:
        >>> # Chop everything beyond 2 inches from the top of a timber
        >>> chop_plane = chop_timber_end_with_half_plane(my_timber, TimberReferenceEnd.TOP, Rational(2))
        >>> # This creates a half-plane 2 inches from the top, removing everything beyond
    """
    # In timber local coordinates:
    # - Bottom is at 0
    # - Top is at timber.length
    # - Z-axis (local) points along the length direction (bottom to top)
    
    # The half-plane is perpendicular to the length direction (Z-axis in local coords)
    # Normal vector in local coordinates is always +Z or -Z
    
    if end == TimberReferenceEnd.TOP:
        # For TOP end:
        # - Cut plane is at (timber.length - distance_from_end_to_cut)
        # - Normal points in +Z direction (away from the timber body, toward the top)
        # - We want to remove everything beyond this point (in +Z direction)
        # - HalfPlane keeps points where normal·P >= offset
        # - So normal should point in +Z and offset should be the cut position
        normal = create_v3(0, 0, 1)
        # note offset is measured from the timber bottom position, not the timber top end position
        offset = timber.length - distance_from_end_to_cut
    else:  # BOTTOM
        # For BOTTOM end:
        # - Cut plane is at distance_from_end_to_cut from bottom
        # - Normal points in -Z direction (away from the timber body, toward the bottom)
        # - We want to remove everything beyond this point (in -Z direction)
        # - HalfPlane keeps points where normal·P >= offset
        # - So normal should point in -Z and offset should be negative of cut position
        normal = create_v3(0, 0, -1)
        offset = -distance_from_end_to_cut
    
    return HalfPlane(normal=normal, offset=offset)

def chop_lap_on_timber_end(
    lap_timber: Timber,
    lap_timber_end: TimberReferenceEnd,
    lap_timber_face: TimberFace,
    lap_length: Numeric,
    lap_shoulder_position_from_lap_timber_end: Numeric,
    lap_depth: Numeric
) -> MeowMeowCSG:
    """
    Create CSG cuts for a lap joint between two timber ends.
    
    Creates material removal volumes for both timbers in a lap joint configuration where
    one timber (top lap) has material removed from one face, and the other timber (bottom lap)
    has material removed from the opposite face so they interlock.
    
        lap_timber_face
        v           |--------| lap_length
    ╔════════════════════════╗          -
    ║face_lap_timber         ║          | lap_depth
    ║               ╔════════╝          -
    ║               ║
    ║               ║
    ╚═══════════════╝
                    ^ lap_shoulder_position_from_lap_timber_end
    
    Args:
        lap_timber: The timber that will have material removed from the specified face
        lap_timber_end: Which end of the top lap timber is being joined
        lap_timber_face: Which face of the top lap timber to remove material from
        lap_length: Length of the lap region along the timber length
        lap_shoulder_position_from_lap_timber_end: Distance from the timber end to the shoulder (inward)
        lap_depth: Depth of material to remove (measured from lap_timber_face)
    
    Returns:
        MeowMeowCSG representing material to remove from the timber
        CSG is in local coordinates of the timber
    
    Example:
        >>> # Create a half-lap joint
        >>> top_csg = chop_lap_on_timber_end(
        ...     timber_a, TimberReferenceEnd.TOP,
        ...     TimberFace.BOTTOM, lap_length=4, lap_depth=2, shoulder_pos=1
        ... )
    """
    from sympy import Rational
    
    # Step 1: Determine the end positions and shoulder position of the top lap timber
    if lap_timber_end == TimberReferenceEnd.TOP:
        lap_end_pos = lap_timber.get_top_center_position_global()
        lap_direction = lap_timber.get_length_direction_global() 
    else:  # BOTTOM
        lap_end_pos = lap_timber.get_bottom_center_position_global()
        lap_direction = -lap_timber.get_length_direction_global()
    
    # Calculate the shoulder position (where the lap starts)
    shoulder_pos_global = lap_end_pos - lap_direction * lap_shoulder_position_from_lap_timber_end
    
    # Calculate the end of the lap (shoulder + lap_length)
    lap_end_pos_global = shoulder_pos_global + lap_direction * lap_length
    
    # Step 3: Create half-plane cuts to remove the ends beyond the lap region
    # Top lap: remove everything beyond the shoulder position (towards the timber end)
    lap_end_distance_from_bottom = ((lap_end_pos_global - lap_timber.get_bottom_position_global()).T * lap_timber.get_length_direction_global())[0, 0]
    lap_shoulder_distance_from_bottom = ((shoulder_pos_global - lap_timber.get_bottom_position_global()).T * lap_timber.get_length_direction_global())[0, 0]
    
    lap_shoulder_distance_from_end = (lap_timber.length - lap_end_distance_from_bottom
                                         if lap_timber_end == TimberReferenceEnd.TOP 
                                         else lap_end_distance_from_bottom)
                                  
    lap_half_plane = chop_timber_end_with_half_plane(lap_timber, lap_timber_end, lap_shoulder_distance_from_end)
    
    
    # Step 4: Determine the orientation of the lap based on lap_timber_face
    
    # For the top lap timber: remove material on the specified face
    # The prism should extend from shoulder to lap_end in length direction
    # And remove lap_depth of material perpendicular to the face
    
    # Calculate the prism dimensions and position for top lap
    # Start and end distances in local coordinates
    # Ensure start <= end for Prism
    prism_start = min(lap_shoulder_distance_from_bottom, lap_end_distance_from_bottom)
    prism_end = max(lap_shoulder_distance_from_bottom, lap_end_distance_from_bottom)
    
    # Step 5: Find where the two laps meet based on lap_depth
    # The top lap removes material from lap_timber_face
    # The bottom lap removes material from the opposite side
    
    # For a face-based lap, we need to offset the prism perpendicular to the face
    # Get the face direction and offset
    if lap_timber_face == TimberFace.TOP or lap_timber_face == TimberFace.BOTTOM:
        raise ValueError("cannot cut lap on end faces")
    elif lap_timber_face == TimberFace.LEFT or lap_timber_face == TimberFace.RIGHT:
        # Lap is on a width face (X-axis in local coords)
        # Remove material from the OPPOSITE side of lap_timber_face
        # lap_depth is the thickness of material we KEEP on the lap_timber_face side
        if lap_timber_face == TimberFace.RIGHT:
            # Keep lap_depth on RIGHT side, remove from LEFT side
            # Remove from x = -size[0]/2 to x = +size[0]/2 - lap_depth
            removal_width = lap_timber.size[0] - lap_depth
            x_offset = -lap_timber.size[0] / Rational(2) + removal_width / Rational(2)
        else:  # LEFT
            # Keep lap_depth on LEFT side, remove from RIGHT side
            # Remove from x = -size[0]/2 + lap_depth to x = +size[0]/2
            removal_width = lap_timber.size[0] - lap_depth
            x_offset = lap_timber.size[0] / Rational(2) - removal_width / Rational(2)
        
        lap_prism = Prism(
            size=create_v2(removal_width, lap_timber.size[1]),
            transform=Transform(position=create_v3(x_offset, 0, 0), orientation=Orientation.identity()),
            start_distance=prism_start,
            end_distance=prism_end
        )
    else:  # FRONT or BACK
        # Lap is on a height face (Y-axis in local coords)
        # Remove material from the OPPOSITE side of lap_timber_face
        # lap_depth is the thickness of material we KEEP on the lap_timber_face side
        if lap_timber_face == TimberFace.FRONT:
            # Keep lap_depth on FRONT side, remove from BACK side
            # Remove from y = -size[1]/2 to y = +size[1]/2 - lap_depth
            removal_height = lap_timber.size[1] - lap_depth
            y_offset = -lap_timber.size[1] / Rational(2) + removal_height / Rational(2)
        else:  # BACK
            # Keep lap_depth on BACK side, remove from FRONT side
            # Remove from y = -size[1]/2 + lap_depth to y = +size[1]/2
            removal_height = lap_timber.size[1] - lap_depth
            y_offset = lap_timber.size[1] / Rational(2) - removal_height / Rational(2)
        
        lap_prism = Prism(
            size=create_v2(lap_timber.size[0], removal_height),
            transform=Transform(position=create_v3(0, y_offset, 0), orientation=Orientation.identity()),
            start_distance=prism_start,
            end_distance=prism_end
        )
    
    # Step 7: Union the half-plane cuts with the prism cuts
    lap_csg = SolidUnion([lap_prism, lap_half_plane])

    return lap_csg

def chop_lap_on_timber_ends(
    top_lap_timber: Timber,
    top_lap_timber_end: TimberReferenceEnd,
    bottom_lap_timber: Timber,
    bottom_lap_timber_end: TimberReferenceEnd,
    top_lap_timber_face: TimberFace,
    lap_length: Numeric,
    top_lap_shoulder_position_from_top_lap_shoulder_timber_end: Numeric,
    lap_depth: Numeric
) -> Tuple[MeowMeowCSG, MeowMeowCSG]:
    """
    Create CSG cuts for a lap joint between two timber ends.
    
    Creates material removal volumes for both timbers in a lap joint configuration where
    one timber (top lap) has material removed from one face, and the other timber (bottom lap)
    has material removed from the opposite face so they interlock.
    
        top_lap_timber_face
        v           |--------| lap_length
    ╔════════════════════════╗╔══════╗  -
    ║face_lap_timber         ║║      ║  | lap_depth
    ║               ╔════════╝║      ║  -
    ║               ║╔════════╝      ║ 
    ║               ║║      timberB  ║ 
    ╚═══════════════╝╚═══════════════╝
                    ^ top_lap_shoulder_position_from_top_lap_shoulder_timber_end
    
    Args:
        top_lap_timber: The timber that will have material removed from the specified face
        top_lap_timber_end: Which end of the top lap timber is being joined
        bottom_lap_timber: The timber that will have material removed from the opposite face
        bottom_lap_timber_end: Which end of the bottom lap timber is being joined
        top_lap_timber_face: Which face of the top lap timber to remove material from
        lap_length: Length of the lap region along the timber length
        top_lap_shoulder_position_from_top_lap_shoulder_timber_end: Distance from the timber end to the shoulder (inward)
        lap_depth: Depth of material to remove (measured from top_lap_timber_face)
    
    Returns:
        Tuple of (top_lap_csg, bottom_lap_csg) representing material to remove from each timber
        Both CSGs are in local coordinates of their respective timbers
    
    Example:
        >>> # Create a half-lap joint
        >>> top_csg, bottom_csg = chop_lap_on_timber_ends(
        ...     timber_a, TimberReferenceEnd.TOP,
        ...     timber_b, TimberReferenceEnd.BOTTOM,
        ...     TimberFace.BOTTOM, lap_length=4, lap_depth=2, shoulder_pos=1
        ... )
    """

    # Assert that the 2 timbers are face aligned
    assert are_timbers_face_aligned(top_lap_timber, bottom_lap_timber), \
        f"Timbers must be face-aligned for a splice lap joint. " \
        f"{top_lap_timber.name} and {bottom_lap_timber.name} orientations are not related by 90-degree rotations."
    
    # Assert the 2 timbers are parallel (either same direction or opposite)
    assert are_vectors_parallel(top_lap_timber.get_length_direction_global(), bottom_lap_timber.get_length_direction_global()), \
        f"Timbers must be parallel for a splice lap joint. " \
        f"{top_lap_timber.name} length_direction {top_lap_timber.get_length_direction_global().T} and " \
        f"{bottom_lap_timber.name} length_direction {bottom_lap_timber.get_length_direction_global().T} are not parallel."
    
    # Assert the 2 timber cross sections overlap at least a little
    assert do_xy_cross_section_on_parallel_timbers_overlap(top_lap_timber, bottom_lap_timber), \
        f"Timber cross sections should overlap for a splice lap joint or there is nothing to cut! " \
        f"{top_lap_timber.name} and {bottom_lap_timber.name} cross sections do not overlap."

    
    top_lap_csg = chop_lap_on_timber_end(top_lap_timber, top_lap_timber_end, top_lap_timber_face, lap_length, top_lap_shoulder_position_from_top_lap_shoulder_timber_end, lap_depth)

    # Step 2: Find the corresponding face on the bottom lap timber
    # Get top_lap_timber_face direction in global space
    top_lap_face_direction_global = top_lap_timber.get_face_direction_global(top_lap_timber_face)
    
    # Negate it to get the direction for the bottom timber face
    bottom_lap_face_direction_global = -top_lap_face_direction_global
    
    # Find which face of the bottom timber aligns with this direction
    bottom_lap_timber_face = bottom_lap_timber.get_closest_oriented_face_from_global_direction(bottom_lap_face_direction_global)
    
    # Step 3: Calculate the depth for the bottom lap
    # The bottom lap depth is measured from the bottom timber's face to the top timber's cutting plane
    # This accounts for any rotation or offset between the timbers
    bottom_lap_depth = measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
        reference_timber=top_lap_timber,
        reference_face=TimberReferenceLongFace(top_lap_timber_face.value),
        reference_depth_from_face=lap_depth,
        target_timber=bottom_lap_timber
    )
    
    # Step 4: Calculate the shoulder position for the bottom lap timber
    # Starting from scratch to avoid confusion between timber END and lap END
    #
    # For interlocking splice lap joint:
    # - Top timber SHOULDER → Bottom timber LAP END
    # - Top timber LAP END → Bottom timber SHOULDER
    
    # Calculate top timber's shoulder and lap end positions in global space
    if top_lap_timber_end == TimberReferenceEnd.TOP:
        top_timber_end_pos = top_lap_timber.get_top_center_position_global()
        top_lap_direction = top_lap_timber.get_length_direction_global() 
    else:  # BOTTOM
        top_timber_end_pos = top_lap_timber.get_bottom_center_position_global()
        top_lap_direction = -top_lap_timber.get_length_direction_global() 
    
    # Top timber shoulder: move inward from timber end by shoulder distance
    top_shoulder_global = top_timber_end_pos - top_lap_direction * top_lap_shoulder_position_from_top_lap_shoulder_timber_end
    
    # Top timber lap end: move outward from shoulder by lap_length
    top_lap_end_global = top_shoulder_global + top_lap_direction * lap_length
    
    # For bottom timber: swap shoulder and lap end
    # Bottom timber shoulder = Top timber lap END
    bottom_shoulder_global = top_lap_end_global
    
    # Project bottom shoulder position onto bottom timber's length axis
    bottom_shoulder_from_bottom_timber_bottom = ((bottom_shoulder_global - bottom_lap_timber.get_bottom_position_global()).T * bottom_lap_timber.get_length_direction_global())[0, 0]
    
    # Calculate shoulder distance from bottom timber's reference end
    if bottom_lap_timber_end == TimberReferenceEnd.TOP:
        # Measuring from top end
        bottom_lap_shoulder_position_from_bottom_timber_end = bottom_lap_timber.length - bottom_shoulder_from_bottom_timber_bottom
    else:  # BOTTOM
        # Measuring from bottom end
        bottom_lap_shoulder_position_from_bottom_timber_end = bottom_shoulder_from_bottom_timber_bottom

    bottom_lap_csg = chop_lap_on_timber_end(bottom_lap_timber, bottom_lap_timber_end, bottom_lap_timber_face, lap_length, bottom_lap_shoulder_position_from_bottom_timber_end, bottom_lap_depth)
    return (top_lap_csg, bottom_lap_csg)


# TODO I think this is cutting on the wrong face...
def chop_profile_on_timber_face(timber: Timber, end: TimberReferenceEnd, face: TimberFace, profile: Union[List[V2], List[List[V2]]], depth: Numeric, profile_y_offset_from_end: Numeric = 0) -> Union[SolidUnion, ConvexPolygonExtrusion]:
    """
    Create a CSG extrusion of a profile (or multiple profiles) on a timber face.
    See the diagram below for understanding how to interpret the profile in the timber's local space based on the end and face arguments.


                            end
    timber                   v                                                  ^
    ╔════════════════════════╗                                                  -x
    ║face                    ║< (0,profile_y_offset_from_end) of the profile    +y ->
    ╚════════════════════════╝                                                  +x
                                                                                v


    Args:
        timber: The timber to create a profile for
        end: Which end to create the profile on (determines the origin and rotation of the profile)
        face: Which face to create the profile on (determines the origin, rotation, and extrusion direction of the profile)
        profile: Either a single profile (List[V2]) or multiple profiles (List[List[V2]]).
                 Multiple profiles are provided as a convenience for creating non-convex shapes
                 by unioning multiple convex polygon extrusions.
        depth: Depth to extrude the profile through the timber's face
        profile_y_offset_from_end: Offset in the Y direction (along timber length from end).
                                   The profile will be translated by -profile_y_offset_from_end,
                                   so the origin (0,0) in profile coordinates corresponds to
                                   (0, profile_y_offset_from_end) in the timber's end-face coordinate system.

    Returns:
        MeowMeowCSG representing the extruded profile(s) in the timber's local coordinates.
        If multiple profiles are provided, returns a SolidUnion of all extruded profiles.
        
    Notes:
        - The profile is positioned at the intersection of the specified end and face
        - Profile coordinates: X-axis points into timber from end, Y-axis across face, origin at (0,0) on face
        - The extrusion extends inward from the face by the specified depth
        - For non-convex shapes, provide multiple profiles (List[List[V2]]) which will be 
          individually extruded and unioned together
        - Each individual profile uses ConvexPolygonExtrusion, so complex non-convex shapes
          should be decomposed into multiple convex profiles
    """
    from sympy import Rational, Matrix
    from .moothymoth import Orientation, Transform, create_v3, cross_product, normalize_vector
    from .meowmeowcsg import ConvexPolygonExtrusion
    
    # Check if we have a single profile or multiple profiles
    # If the first element is a list, we have multiple profiles
    is_multiple_profiles = isinstance(profile, list) and len(profile) > 0 and isinstance(profile[0], list)
    
    if is_multiple_profiles:
        # Recursively call this function for each profile and union the results
        extrusions = []
        for single_profile in profile:
            extrusion = chop_profile_on_timber_face(timber, end, face, single_profile, depth, profile_y_offset_from_end)
            extrusions.append(extrusion)
        return SolidUnion(extrusions)
    
    # Single profile case - continue with original logic
    
    # Translate the profile by -profile_y_offset_from_end in the Y direction
    # This allows the user to specify profiles with arbitrary Y origins and position them correctly
    translated_profile = [point + create_v2(0, -profile_y_offset_from_end) for point in profile]
    
    # ========================================================================
    # Step 1: Determine the origin position in timber local coordinates
    # ========================================================================
    # The origin is at the intersection of the end and the face
    # In timber local coordinates:
    # - Local X-axis = width_direction
    # - Local Y-axis = height_direction
    # - Local Z-axis = length_direction (bottom to top)
    # - Origin is at bottom_position (center of bottom face)
    
    # Get Z coordinate based on end
    if end == TimberReferenceEnd.TOP:
        origin_z = timber.length
    else:  # BOTTOM
        origin_z = Rational(0)
    
    # Get X and Y offset based on face
    # The face determines where on the cross-section the origin is
    half_width = timber.size[0] / Rational(2)
    half_height = timber.size[1] / Rational(2)
    
    if face == TimberFace.TOP or face == TimberFace.BOTTOM:
        # For end faces, we can't really position a profile "on" them in the way described
        # This shouldn't happen based on the function's design
        raise ValueError(f"Face cannot be an end face (TOP or BOTTOM), got {face}")
    elif face == TimberFace.RIGHT:
        origin_x = half_width
        origin_y = Rational(0)
    elif face == TimberFace.LEFT:
        origin_x = -half_width
        origin_y = Rational(0)
    elif face == TimberFace.FRONT:
        origin_x = Rational(0)
        origin_y = half_height
    else:  # BACK
        origin_x = Rational(0)
        origin_y = -half_height
    
    origin_local = create_v3(origin_x, origin_y, origin_z)
    
    # ========================================================================
    # Step 2: Determine the profile coordinate system orientation
    # ========================================================================
    # The profile's coordinate system needs:
    # - X-axis: points along timber length (into timber from end)
    # - Y-axis: points across the face (perpendicular to length and face normal)
    # - Z-axis: points inward from face (extrusion direction)
    
    # Get face normal direction in timber local coordinates
    face_normal_local = face.get_direction()  # This gives the outward normal
    
    # Profile Y-axis: points towards the reference end
    if end == TimberReferenceEnd.TOP:
        profile_y_axis = create_v3(0, 0, 1)
    else:  # BOTTOM
        profile_y_axis = create_v3(0, 0, -1)
    
    # Profile Z-axis (extrusion): points outward from face (negative of face normal)
    profile_z_axis = face_normal_local
    
    # Profile Y-axis: perpendicular to X and Z, using right-hand rule
    # X = Y × Z (so that X, Y, Z form a right-handed system)
    profile_x_axis = cross_product(profile_y_axis, profile_z_axis)
    profile_x_axis = normalize_vector(profile_x_axis)
    
    # Create the orientation matrix for the profile
    # Columns are: X-axis, Y-axis, Z-axis
    profile_orientation_matrix = Matrix([
        [profile_x_axis[0], profile_y_axis[0], profile_z_axis[0]],
        [profile_x_axis[1], profile_y_axis[1], profile_z_axis[1]],
        [profile_x_axis[2], profile_y_axis[2], profile_z_axis[2]]
    ])
    
    profile_orientation = Orientation(profile_orientation_matrix)
    profile_transform = Transform(position=origin_local, orientation=profile_orientation)
    
    # ========================================================================
    # Step 3: Create the ConvexPolygonExtrusion
    # ========================================================================
    # The extrusion starts at the origin (start_distance=0) and extends 
    # inward by depth along the profile's Z-axis
    
    extrusion = ConvexPolygonExtrusion(
        points=translated_profile,
        transform=profile_transform,
        start_distance=-depth,
        end_distance=Rational(0),
    )
    
    return extrusion


def chop_shoulder_notch_on_timber_face(
    timber: Timber,
    notch_face: TimberFace,
    distance_along_timber: Numeric,
    notch_width: Numeric,
    notch_depth: Numeric
) -> Prism:
    """
    Create a rectangular shoulder notch on a timber face.
    
    This creates a rectangular notch/pocket on a specified face of a timber.
    The notch is centered at a specific position along the timber's length.
    
    Args:
        timber: The timber to notch
        notch_face: The face to cut the notch into (LEFT, RIGHT, FRONT, or BACK)
        distance_along_timber: Distance from the timber's BOTTOM end to the center of the notch
        notch_width: Width of the notch (measured along timber length direction)
        notch_depth: Depth of the notch (measured perpendicular to the face, into the timber)
    
    Returns:
        Prism representing the material to remove (in timber's local coordinates)
    
    Example:
        >>> # Create a 2" wide, 1" deep notch on the front face, 6" from bottom
        >>> notch = chop_shoulder_notch_on_timber_face(
        ...     timber, TimberFace.FRONT, inches(6), inches(2), inches(1)
        ... )
    """
    from sympy import Rational
    
    # Validate face is a long face (not TOP or BOTTOM)
    if notch_face == TimberFace.TOP or notch_face == TimberFace.BOTTOM:
        raise ValueError("Cannot cut shoulder notch on end faces (TOP or BOTTOM)")
    
    # Validate dimensions
    if notch_width <= 0:
        raise ValueError(f"notch_width must be positive, got {notch_width}")
    if notch_depth <= 0:
        raise ValueError(f"notch_depth must be positive, got {notch_depth}")
    if distance_along_timber < 0 or distance_along_timber > timber.length:
        raise ValueError(
            f"distance_along_timber must be between 0 and timber.length ({timber.length}), "
            f"got {distance_along_timber}"
        )
    
    # Calculate prism extent along timber length
    prism_start = distance_along_timber - notch_width / Rational(2)
    prism_end = distance_along_timber + notch_width / Rational(2)
    
    # Ensure start/end are within timber bounds
    prism_start = max(Rational(0), prism_start)
    prism_end = min(timber.length, prism_end)
    
    # Calculate prism position and size based on which face
    if notch_face == TimberFace.LEFT or notch_face == TimberFace.RIGHT:
        # Notch is on a width face (X-axis in local coords)
        # The notch removes material inward from the face
        if notch_face == TimberFace.RIGHT:
            # Notch starts at right face (-depth inward)
            # Prism center: size[0]/2 - depth/2
            x_offset = timber.size[0] / Rational(2) - notch_depth / Rational(2)
        else:  # LEFT
            # Notch starts at left face (-depth inward)
            # Prism center: -size[0]/2 + depth/2
            x_offset = -timber.size[0] / Rational(2) + notch_depth / Rational(2)
        
        notch_prism = Prism(
            size=create_v2(notch_depth, timber.size[1]),  # depth in X, full height in Y
            transform=Transform(position=create_v3(x_offset, 0, 0), orientation=Orientation.identity()),
            start_distance=prism_start,
            end_distance=prism_end
        )
    else:  # FRONT or BACK
        # Notch is on a height face (Y-axis in local coords)
        # The notch removes material inward from the face
        if notch_face == TimberFace.FRONT:
            # Notch starts at front face (-depth inward)
            # Prism center: size[1]/2 - depth/2
            y_offset = timber.size[1] / Rational(2) - notch_depth / Rational(2)
        else:  # BACK
            # Notch starts at back face (-depth inward)
            # Prism center: -size[1]/2 + depth/2
            y_offset = -timber.size[1] / Rational(2) + notch_depth / Rational(2)
        
        notch_prism = Prism(
            size=create_v2(timber.size[0], notch_depth),  # full width in X, depth in Y
            transform=Transform(position=create_v3(0, y_offset, 0), orientation=Orientation.identity()),
            start_distance=prism_start,
            end_distance=prism_end
        )
    
    return notch_prism