"""
Joint Helper Functions (joint_helperonis.py)

Collection of helper functions for validating and checking timber joint configurations.
These functions help ensure that joints are geometrically valid and sensibly constructed.
"""

from typing import Optional
from code_goes_here.timber import Timber, TimberReferenceEnd
from code_goes_here.moothymoth import EPSILON_GENERIC, construction_parallel_check, Numeric, Transform, create_v3
from code_goes_here.meowmeowcsg import Prism, HalfPlane


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
    
    if not construction_parallel_check(timberA_length_direction, timberB_length_direction):
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
