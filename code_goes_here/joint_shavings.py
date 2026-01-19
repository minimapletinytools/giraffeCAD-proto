"""
Joint Helper Functions (joint_shavings.py)

Collection of helper functions for validating and checking timber joint configurations.
These functions help ensure that joints are geometrically valid and sensibly constructed.
"""

from typing import Optional, Tuple
from code_goes_here.timber import Timber, TimberReferenceEnd, TimberFace, TimberReferenceLongFace
from code_goes_here.moothymoth import EPSILON_GENERIC, are_vectors_parallel, Numeric, Transform, create_v3, create_v2, Orientation
from code_goes_here.meowmeowcsg import Prism, HalfPlane, MeowMeowCSG, Union
from code_goes_here.construction import are_timbers_face_aligned, do_xy_cross_section_on_parallel_timbers_overlap
from sympy import Abs, Rational

def find_opposing_face_on_another_timber(reference_timber: Timber, reference_face: TimberReferenceLongFace, target_timber: Timber) -> TimberFace:
    """
    Find the opposing face on another timber. Assumes that the target_timber has a face parallel to the reference face on the reference_timber.
    """
    target_face = target_timber.get_closest_oriented_face(-reference_timber.get_face_direction(reference_face))

    # assert that the target_face is parallel to the reference_face
    assert are_vectors_parallel(reference_timber.get_face_direction(reference_face), target_timber.get_face_direction(target_face)), \
        f"Target face {target_face} is not parallel to reference face {reference_face} on timber {reference_timber.name}"
    
    return target_face

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
    reference_face_direction = reference_timber.get_face_direction(reference_face)
    target_long_faces = [TimberReferenceLongFace.RIGHT, TimberReferenceLongFace.LEFT, 
                         TimberReferenceLongFace.FRONT, TimberReferenceLongFace.BACK]
    
    has_parallel_face = False
    for target_face in target_long_faces:
        target_face_direction = target_timber.get_face_direction(target_face)
        if are_vectors_parallel(reference_face_direction, target_face_direction):
            has_parallel_face = True
            break
    
    assert has_parallel_face, \
        f"Target timber {target_timber.name} must have a long face parallel to reference face {reference_face.name} " \
        f"on timber {reference_timber.name}. Reference face direction: {reference_face_direction.T}"
    
    # Get a point on the reference face
    reference_face_offset = reference_timber.get_size_in_face_normal_axis(reference_face) / Rational(2)
    reference_face_point = reference_timber.bottom_position + reference_face_direction * reference_face_offset
    
    # Calculate the cutting plane point (moved inward by reference_depth_from_face)
    cutting_plane_point = reference_face_point - reference_face_direction * reference_depth_from_face
    cutting_plane_normal = reference_face_direction
    
    # Find the opposing face on the target timber
    target_face_direction = -reference_face_direction  # Opposite direction
    target_face = target_timber.get_closest_oriented_face(target_face_direction)
    
    # Get a point on the target timber's opposing face
    target_face_offset = target_timber.get_size_in_face_normal_axis(target_face) / Rational(2)
    target_face_point = target_timber.bottom_position + target_timber.get_face_direction(target_face) * target_face_offset
    
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
    timberA_length_direction = timberA.length_direction
    timberB_length_direction = timberB.length_direction
    
    # Check 1: The joint ends must be pointing in opposite directions (anti-parallel)
    # For anti-parallel, the dot product should be close to -1
    dot_product = timberA_length_direction.dot(timberB_length_direction)
    
    if not are_vectors_parallel(timberA_length_direction, timberB_length_direction):
        return (
            f"Joint ends are not parallel. TimberA length direction {timberA_length_direction.T} "
            f"and timberB length direction {timberB_length_direction.T} must be parallel "
            f"(dot product should be ±1, got {float(dot_product):.3f})"
        )
    
    # Check if they're pointing in the same direction (should be opposite)
    if dot_product > 0:
        return (
            f"Joint ends are pointing in the same direction (dot product = {float(dot_product):.3f}). "
            f"For a splice joint, the ends should point in opposite directions (dot product should be -1)"
        )
    
    # Get the end positions in world coordinates
    if timberA_end == TimberReferenceEnd.TOP:
        timberA_end_pos = timberA.get_top_center_position()
        timberA_end_direction = timberA.length_direction  # Points away from timber
        timberA_opposite_end_pos = timberA.bottom_position
    else:  # BOTTOM
        timberA_end_pos = timberA.bottom_position
        timberA_end_direction = -timberA.length_direction  # Points away from timber
        timberA_opposite_end_pos = timberA.get_top_center_position()
    
    if timberB_end == TimberReferenceEnd.TOP:
        timberB_end_pos = timberB.get_top_center_position()
        timberB_end_direction = timberB.length_direction  # Points away from timber
        timberB_opposite_end_pos = timberB.bottom_position
    else:  # BOTTOM
        timberB_end_pos = timberB.bottom_position
        timberB_end_direction = -timberB.length_direction  # Points away from timber
        timberB_opposite_end_pos = timberB.get_top_center_position()
    
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
        lap_end_pos = lap_timber.get_top_center_position()
        lap_direction = lap_timber.length_direction 
    else:  # BOTTOM
        lap_end_pos = lap_timber.get_bottom_center_position()
        lap_direction = -lap_timber.length_direction
    
    # Calculate the shoulder position (where the lap starts)
    shoulder_pos_global = lap_end_pos - lap_direction * lap_shoulder_position_from_lap_timber_end
    
    # Calculate the end of the lap (shoulder + lap_length)
    lap_end_pos_global = shoulder_pos_global + lap_direction * lap_length
    
    # Step 3: Create half-plane cuts to remove the ends beyond the lap region
    # Top lap: remove everything beyond the shoulder position (towards the timber end)
    lap_end_distance_from_bottom = ((lap_end_pos_global - lap_timber.bottom_position).T * lap_timber.length_direction)[0, 0]
    lap_shoulder_distance_from_bottom = ((shoulder_pos_global - lap_timber.bottom_position).T * lap_timber.length_direction)[0, 0]
    
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
        # Remove lap_depth from the width dimension
        # Position offset in local Y=0, X depends on which face
        if lap_timber_face == TimberFace.RIGHT:
            # Remove from +X side
            x_offset = lap_timber.size[0] / Rational(2) - lap_depth / Rational(2)
        else:  # LEFT
            # Remove from -X side  
            x_offset = -lap_timber.size[0] / Rational(2) + lap_depth / Rational(2)
        
        lap_prism = Prism(
            size=create_v2(lap_depth, lap_timber.size[1]),
            transform=Transform(position=create_v3(x_offset, 0, 0), orientation=Orientation.identity()),
            start_distance=prism_start,
            end_distance=prism_end
        )
    else:  # FRONT or BACK
        # Lap is on a height face (Y-axis in local coords)
        # Remove lap_depth from the height dimension
        if lap_timber_face == TimberFace.FRONT:
            # Remove from +Y side
            y_offset = lap_timber.size[1] / Rational(2) - lap_depth / Rational(2)
        else:  # BACK
            # Remove from -Y side
            y_offset = -lap_timber.size[1] / Rational(2) + lap_depth / Rational(2)
        
        lap_prism = Prism(
            size=create_v2(lap_timber.size[0], lap_depth),
            transform=Transform(position=create_v3(0, y_offset, 0), orientation=Orientation.identity()),
            start_distance=prism_start,
            end_distance=prism_end
        )
    
    # Step 7: Union the half-plane cuts with the prism cuts
    lap_csg = Union([lap_prism, lap_half_plane])

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
    assert are_vectors_parallel(top_lap_timber.length_direction, bottom_lap_timber.length_direction), \
        f"Timbers must be parallel for a splice lap joint. " \
        f"{top_lap_timber.name} length_direction {top_lap_timber.length_direction.T} and " \
        f"{bottom_lap_timber.name} length_direction {bottom_lap_timber.length_direction.T} are not parallel."
    
    # Assert the 2 timber cross sections overlap at least a little
    assert do_xy_cross_section_on_parallel_timbers_overlap(top_lap_timber, bottom_lap_timber), \
        f"Timber cross sections should overlap for a splice lap joint or there is nothing to cut! " \
        f"{top_lap_timber.name} and {bottom_lap_timber.name} cross sections do not overlap."

    
    top_lap_csg = chop_lap_on_timber_end(top_lap_timber, top_lap_timber_end, top_lap_timber_face, lap_length, top_lap_shoulder_position_from_top_lap_shoulder_timber_end, lap_depth)

    # Step 2: Find the corresponding face on the bottom lap timber
    # Get top_lap_timber_face direction in global space
    top_lap_face_direction_global = top_lap_timber.get_face_direction(top_lap_timber_face)
    
    # Negate it to get the direction for the bottom timber face
    bottom_lap_face_direction_global = -top_lap_face_direction_global
    
    # Find which face of the bottom timber aligns with this direction
    bottom_lap_timber_face = bottom_lap_timber.get_closest_oriented_face(bottom_lap_face_direction_global)
    
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
        top_timber_end_pos = top_lap_timber.get_top_center_position()
        top_lap_direction = top_lap_timber.length_direction 
    else:  # BOTTOM
        top_timber_end_pos = top_lap_timber.get_bottom_center_position()
        top_lap_direction = -top_lap_timber.length_direction 
    
    # Top timber shoulder: move inward from timber end by shoulder distance
    top_shoulder_global = top_timber_end_pos - top_lap_direction * top_lap_shoulder_position_from_top_lap_shoulder_timber_end
    
    # Top timber lap end: move outward from shoulder by lap_length
    top_lap_end_global = top_shoulder_global + top_lap_direction * lap_length
    
    # For bottom timber: swap shoulder and lap end
    # Bottom timber shoulder = Top timber lap END
    bottom_shoulder_global = top_lap_end_global
    
    # Project bottom shoulder position onto bottom timber's length axis
    bottom_shoulder_from_bottom_timber_bottom = ((bottom_shoulder_global - bottom_lap_timber.bottom_position).T * bottom_lap_timber.length_direction)[0, 0]
    
    # Calculate shoulder distance from bottom timber's reference end
    if bottom_lap_timber_end == TimberReferenceEnd.TOP:
        # Measuring from top end
        bottom_lap_shoulder_position_from_bottom_timber_end = bottom_lap_timber.length - bottom_shoulder_from_bottom_timber_bottom
    else:  # BOTTOM
        # Measuring from bottom end
        bottom_lap_shoulder_position_from_bottom_timber_end = bottom_shoulder_from_bottom_timber_bottom

    bottom_lap_csg = chop_lap_on_timber_end(bottom_lap_timber, bottom_lap_timber_end, bottom_lap_timber_face, lap_length, bottom_lap_shoulder_position_from_bottom_timber_end, bottom_lap_depth)
    return (top_lap_csg, bottom_lap_csg)