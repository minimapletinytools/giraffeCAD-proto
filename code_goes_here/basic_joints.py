"""
GiraffeCAD - Basic joint construction functions
Contains functions for creating joints between timbers
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
    _are_timbers_face_orthogonal
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
        Joint object containing the two CutTimbers
        
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
    if construction_parallel_check(directionA, directionB):
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
    if zero_test(denom):
        raise ValueError("Cannot compute intersection point (degenerate case)")
    
    # Parameters for closest points on each line
    t = (b * e - c * d) / denom
    s = (a * e - b * d) / denom
    
    # Get the closest points on each centerline
    pointA = endA_position + directionA * t
    pointB = endB_position + directionB * s
    
    # The intersection point is the midpoint between the two closest points
    intersection_point = (pointA + pointB) / 2
    
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
    cutA = HalfPlaneCut(
        timber=timberA,
        transform=Transform(position=intersection_point, orientation=timberA.orientation),
        half_plane=HalfPlane(normal=local_normalA, offset=local_offsetA),
        maybe_end_cut=timberA_end
    )
    
    cutB = HalfPlaneCut(
        timber=timberB,
        transform=Transform(position=intersection_point, orientation=timberB.orientation),
        half_plane=HalfPlane(normal=local_normalB, offset=local_offsetB),
        maybe_end_cut=timberB_end
    )
    
    # Create CutTimbers with cuts passed at construction
    cut_timberA = CutTimber(timberA, cuts=[cutA])
    cut_timberB = CutTimber(timberB, cuts=[cutB])
    
    # Create and return the Joint with all data at construction
    joint = Joint(
        cut_timbers={"timberA": cut_timberA, "timberB": cut_timberB},
        jointAccessories={}
    )
    
    return joint

def cut_basic_miter_joint_on_face_aligned_timbers(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic miter joint between two timbers such that the 2 ends meet at a 90 degree angle miter corner.
    """
    # Assert that the timber length axes are perpendicular (90-degree corner)
    assert _are_directions_perpendicular(timberA.length_direction, timberB.length_direction), \
        "Timbers must have perpendicular length axes (90-degree angle) for this joint type"
    
    return cut_basic_miter_joint(timberA, timberA_end, timberB, timberB_end)


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
    
    # Check that timbers are not parallel (butt joints require timbers to be at an angle)
    assert not construction_parallel_check(receiving_timber.length_direction, butt_timber.length_direction), \
        "Timbers cannot be parallel for a butt joint"
    
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
        # For long faces (LEFT, RIGHT, FRONT, BACK), center is at mid-length
        from sympy import Rational
        face_center = receiving_timber.bottom_position + (receiving_timber.length / Rational(2)) * receiving_timber.length_direction
        
        # Offset to the face surface
        if receiving_face == TimberFace.RIGHT:
            face_center = face_center + (receiving_timber.size[0] / Rational(2)) * receiving_timber.width_direction
        elif receiving_face == TimberFace.LEFT:
            face_center = face_center - (receiving_timber.size[0] / Rational(2)) * receiving_timber.width_direction
        elif receiving_face == TimberFace.FRONT:
            face_center = face_center + (receiving_timber.size[1] / Rational(2)) * receiving_timber.height_direction
        else:  # BACK
            face_center = face_center - (receiving_timber.size[1] / Rational(2)) * receiving_timber.height_direction
    
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
    cut = HalfPlaneCut(
        timber=butt_timber,
        transform=Transform(position=face_center, orientation=butt_timber.orientation),
        half_plane=HalfPlane(normal=local_normal, offset=local_offset),
        maybe_end_cut=butt_end
    )
    
    # Create CutTimber for the butt timber with cut passed at construction
    cut_butt = CutTimber(butt_timber, cuts=[cut])
    
    # Create CutTimber for the receiving timber (no cuts)
    cut_receiving = CutTimber(receiving_timber, cuts=[])
    
    # Create and return the Joint with all data at construction
    joint = Joint(
        cut_timbers={"receiving_timber": cut_receiving, "butt_timber": cut_butt},
        jointAccessories={}
    )
    
    return joint


def cut_basic_splice_joint_on_aligned_timbers(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd, splice_point: Optional[V3] = None) -> Joint:
    """
    Creates a basic splice joint between two timbers with parallel (aligned) length axes.
    Both timbers are cut at the splice plane, creating a butt joint connection.

    Args:
        timberA: First timber to join
        timberA_end: Which end of timberA to cut (TOP or BOTTOM)
        timberB: Second timber to join
        timberB_end: Which end of timberB to cut (TOP or BOTTOM)
        splice_point: Optional point where the splice occurs. If not provided, 
                     calculated as the midpoint between the two timber ends.
                     If provided but not on timberA's centerline, it will be projected onto it.

    Returns:
        Joint object containing the two CutTimbers

    Raises:
        ValueError: If the timbers are not parallel (aligned)
    """
    import warnings
    from code_goes_here.construction import _are_directions_parallel
    
    # Assert that the length axes are parallel
    if not _are_directions_parallel(timberA.length_direction, timberB.length_direction):
        raise ValueError("Timbers must have parallel length axes for a splice joint")
    
    # Get the end positions for each timber
    if timberA_end == TimberReferenceEnd.TOP:
        endA_position = timberA.get_top_center_position()
        directionA = timberA.length_direction
    else:  # BOTTOM
        endA_position = timberA.get_bottom_center_position()
        directionA = -timberA.length_direction
    
    if timberB_end == TimberReferenceEnd.TOP:
        endB_position = timberB.get_top_center_position()
        directionB = timberB.length_direction
    else:  # BOTTOM
        endB_position = timberB.get_bottom_center_position()
        directionB = -timberB.length_direction
    
    # Normalize length direction for later use
    length_dir_norm = normalize_vector(timberA.length_direction)
    
    # Calculate or validate the splice point
    if splice_point is None:
        # Calculate as the midpoint between the two timber ends
        splice_point = (endA_position + endB_position) / 2
    else:
        # Project the splice point onto timberA's centerline if it's not already on it
        # Vector from timberA's bottom to the splice point
        to_splice = splice_point - timberA.bottom_position
        
        # Project onto the centerline
        distance_along_centerline = (to_splice.T * length_dir_norm)[0, 0]
        projected_point = timberA.bottom_position + length_dir_norm * distance_along_centerline
        
        # Check if the point needed projection (warn if not on centerline)
        distance_from_centerline = vector_magnitude(splice_point - projected_point)
        if not zero_test(distance_from_centerline):
            warnings.warn(f"Splice point was not on timberA's centerline (distance: {float(distance_from_centerline)}). Projecting onto centerline.")
            splice_point = projected_point
    
    # Check if timber cross sections overlap (approximate check using bounding boxes)
    # Project both timber cross-sections onto a plane perpendicular to the length direction
    # For simplicity, we'll warn if the centerlines are far apart
    centerline_distance = vector_magnitude(
        (splice_point - timberA.bottom_position) - 
        length_dir_norm * ((splice_point - timberA.bottom_position).T * length_dir_norm)[0, 0] -
        ((splice_point - timberB.bottom_position) - 
         length_dir_norm * ((splice_point - timberB.bottom_position).T * length_dir_norm)[0, 0])
    )
    
    # Approximate overlap check: centerlines should be close
    max_dimension = max(timberA.size[0], timberA.size[1], timberB.size[0], timberB.size[1])
    from sympy import Rational
    if centerline_distance > max_dimension / Rational(2):
        warnings.warn(f"Timber cross sections may not overlap (centerline distance: {float(centerline_distance)}). Check joint geometry.")
    
    # Create the splice plane perpendicular to the length direction
    # The plane normal is the length direction (or its negative, depending on orientation)
    # For each timber, the half-plane normal should point away from the material we're keeping
    
    # Use normalized length direction as the plane normal
    # The splice plane is perpendicular to the timber axes
    plane_normal = normalize_vector(timberA.length_direction)
    
    # For timberA: the half-plane normal should point away from the material we're keeping
    # If timberA_end is TOP, we're cutting the top, so normal points up (+length_direction)
    # If timberA_end is BOTTOM, we're cutting the bottom, so normal points down (-length_direction)
    if timberA_end == TimberReferenceEnd.TOP:
        normalA = plane_normal
    else:  # BOTTOM
        normalA = -plane_normal
    
    # For timberB: determine the normal based on which end is being cut
    # The key insight: in a splice joint, the two normals should always point AWAY from each other
    # (opposite directions), regardless of the timber orientations or which ends are being cut.
    # 
    # We need to check which way timberB's length direction points relative to timberA
    alignment = (timberA.length_direction.T * timberB.length_direction)[0, 0]
    
    if alignment > 0:
        # Same orientation: timberB points in same direction as timberA
        # If timberA TOP is cut with normal +plane_normal, timberB BOTTOM should be cut with -plane_normal
        # If timberA TOP is cut with normal +plane_normal, timberB TOP should be cut with +plane_normal (same)
        # But in a splice, we want opposite normals, so:
        if timberB_end == TimberReferenceEnd.TOP:
            # Both TOP ends meet: they point in the same direction, so use same normal as timberA
            normalB = normalA
        else:  # BOTTOM
            # TOP meets BOTTOM: opposite ends meet, so use opposite normal
            normalB = -normalA
    else:
        # Opposite orientation: timberB points in opposite direction to timberA
        # The plane normal for timberB is based on timberB's own length direction
        plane_normalB = normalize_vector(timberB.length_direction)
        if timberB_end == TimberReferenceEnd.TOP:
            normalB = plane_normalB
        else:  # BOTTOM
            normalB = -plane_normalB
    
    # Convert to LOCAL coordinates for timberA
    local_normalA = timberA.orientation.matrix.T * normalA
    local_offsetA = (splice_point.T * normalA)[0, 0] - (normalA.T * timberA.bottom_position)[0, 0]
    
    # Convert to LOCAL coordinates for timberB
    local_normalB = timberB.orientation.matrix.T * normalB
    local_offsetB = (splice_point.T * normalB)[0, 0] - (normalB.T * timberB.bottom_position)[0, 0]
    
    # Create the HalfPlaneCuts
    cutA = HalfPlaneCut(
        timber=timberA,
        transform=Transform(position=splice_point, orientation=timberA.orientation),
        half_plane=HalfPlane(normal=local_normalA, offset=local_offsetA),
        maybe_end_cut=timberA_end
    )
    
    cutB = HalfPlaneCut(
        timber=timberB,
        transform=Transform(position=splice_point, orientation=timberB.orientation),
        half_plane=HalfPlane(normal=local_normalB, offset=local_offsetB),
        maybe_end_cut=timberB_end
    )
    
    # Create CutTimbers with cuts passed at construction
    cut_timberA = CutTimber(timberA, cuts=[cutA])
    cut_timberB = CutTimber(timberB, cuts=[cutB])
    
    # Create and return the Joint with all data at construction
    joint = Joint(
        cut_timbers={"timberA": cut_timberA, "timberB": cut_timberB},
        jointAccessories={}
    )
    
    return joint


def cut_basic_cross_lap_joint(timberA: Timber, timberB: Timber, timberA_cut_face: Optional[TimberFace] = None, timberB_cut_face: Optional[TimberFace] = None, cut_ratio: Numeric = Rational(1, 2)) -> Joint:
    """
    Creates a basic cross lap joint between two timbers.

    Args:
        timberA: First timber to join
        timberB: Second timber to join
        timberA_cut_face: Optional face of timberA to cut the lap from. If not provided, the face is chosen automatically to minimize the amount of material removed.
        timberB_cut_face: Optional face of timberB to cut the lap from. If not provided, the face is chosen automatically to minimize the amount of material removed.
        cut_ratio: ratio [0,1] of timberA : timberB to cut the lap from. 
            example: if cut_ratio is 1, then timberA is cut entirely such that timberB fits into the cut and timberB is not cut at all.
        

    Returns:
        Joint object containing the two CutTimbers

    Raises:
        AssertionError: If timbers don't intersect, are parallel, or face normals are invalid
    """
    from code_goes_here.meowmeowcsg import Difference, Prism, HalfPlane
    
    # Verify that cut_ratio is in valid range [0, 1]
    assert 0 <= cut_ratio <= 1, f"cut_ratio must be in range [0, 1], got {cut_ratio}"
    
    # Verify that the timbers are not parallel (their length directions must differ)
    dot_product = (timberA.length_direction.T * timberB.length_direction)[0, 0]
    assert abs(abs(dot_product) - 1) > Rational(1, 1000000), \
        "Timbers must not be parallel (their length directions must differ)"
    
    # Check that the timbers intersect when extended infinitely
    # Calculate closest points between two lines in 3D
    d1 = timberA.length_direction
    d2 = timberB.length_direction
    p1 = timberA.bottom_position
    p2 = timberB.bottom_position
    w = p1 - p2
    
    a = (d1.T * d1)[0, 0]
    b = (d1.T * d2)[0, 0]
    c = (d2.T * d2)[0, 0]
    d = (d1.T * w)[0, 0]
    e = (d2.T * w)[0, 0]
    
    denom = a * c - b * b
    
    if abs(denom) < Rational(1, 1000000):
        # Lines are parallel (already checked above)
        t = -(d1.T * w)[0, 0] / a if a > 0 else 0
        closest_on_1 = p1 + t * d1
        distance = (p2 - closest_on_1).norm()
    else:
        t1 = (b * e - c * d) / denom
        t2 = (a * e - b * d) / denom
        
        closest_on_1 = p1 + t1 * d1
        closest_on_2 = p2 + t2 * d2
        
        distance = (closest_on_1 - closest_on_2).norm()
    
    # Check if timbers are close enough to intersect
    max_separation = (timberA.size[0] + timberA.size[1] + 
                     timberB.size[0] + timberB.size[1]) / 2
    
    assert float(distance) < float(max_separation), \
        f"Timbers do not intersect (closest distance: {float(distance):.4f}m, max allowed: {float(max_separation):.4f}m)"
    

    # TODO this is wrong, don't use closest to centeline, instead, find the axis perpendicular to the length axis of both timbers and choose the faces on that axis. Choose face on that axis on timberA that's closest to timberB and then pick the opposite face on timberB.
    # Auto-select cut faces if not provided
    # Choose the face that minimizes material removal (face closest to the other timber)
    if timberA_cut_face is None:
        # Find which face of timberA is closest to timberB's centerline
        # Check all 4 faces and pick the one with smallest distance
        timberA_cut_face = _find_closest_face_to_timber(timberA, timberB)
    
    if timberB_cut_face is None:
        timberB_cut_face = _find_closest_face_to_timber(timberB, timberA)
    
    # Get face normals (pointing outward from the timber) in GLOBAL space
    # get_face_direction returns the direction vector in world coordinates
    normalA = timberA.get_face_direction(timberA_cut_face)
    normalB = timberB.get_face_direction(timberB_cut_face)
    
    # Verify that the face normals oppose each other (point toward each other)
    # For a valid cross lap joint, the normals must strictly oppose (dot product < 0)
    # This ensures the cutting plane can properly separate the two timber volumes
    normal_dot = (normalA.T * normalB)[0, 0]
    
    # The faces must be opposing (normals pointing toward each other)
    # Perpendicular faces (dot product = 0) are NOT valid for cross lap joints
    assert normal_dot < 0, \
        f"Face normals must oppose each other (dot product < 0, got {float(normal_dot):.4f})"
    
    # Create the cutting plane by lerping between the two faces
    # Get the position of each face (center point on the face)
    # Calculate face center positions
    faceA_position = _get_face_center_position(timberA, timberA_cut_face)
    faceB_position = _get_face_center_position(timberB, timberB_cut_face)
    
    # The cutting plane position is interpolated based on cut_ratio
    # cut_ratio = 0: plane at faceA (timberB is cut entirely)
    # cut_ratio = 0.5: plane halfway between faces
    # cut_ratio = 1: plane at faceB (timberA is cut entirely)
    cutting_plane_position = faceA_position * (1 - cut_ratio) + faceB_position * cut_ratio
    
    # The cutting plane normal should be interpolated between the two face normals
    # cut_ratio = 0: normal is normalA (pointing from faceA)
    # cut_ratio = 1: normal is -normalB (pointing toward faceB from the opposite direction)
    # Since normalA and normalB oppose each other (normalA · normalB < 0), we interpolate:
    cutting_plane_normal = normalA * (1 - cut_ratio) - normalB * cut_ratio
    cutting_plane_normal_normalized = cutting_plane_normal / cutting_plane_normal.norm()
    
    # Calculate the offset for the cutting plane
    # offset = normal · point_on_plane
    cutting_plane_offset = (cutting_plane_normal_normalized.T * cutting_plane_position)[0, 0]
    
    # Create cuts for both timbers
    cuts_A = []
    cuts_B = []
    
    # TimberA: Cut by (timberB prism) intersected with (region on the timberB side of cutting plane)
    # The HalfPlane keeps points where normal·P >= offset
    # We want to keep the region on the timberB side (positive normal direction from A)
    # So we use the cutting plane as-is
    
    if cut_ratio > 0:  # Only cut timberA if cut_ratio > 0
        # Transform timberB prism to timberA's local coordinates
        relative_orientation_B_in_A = Orientation(timberA.orientation.matrix.T * timberB.orientation.matrix)
        timberB_origin_in_A_local = timberA.orientation.matrix.T * (timberB.bottom_position - timberA.bottom_position)
        
        # Create timberB prism in timberA's local coordinates (infinite extent)
        transform_B_in_A = Transform(position=timberB_origin_in_A_local, orientation=relative_orientation_B_in_A)
        timberB_prism_in_A = Prism(
            size=timberB.size,
            transform=transform_B_in_A,
            start_distance=None,  # Infinite
            end_distance=None     # Infinite
        )
        
        # Transform cutting plane to timberA's local coordinates
        cutting_plane_normal_in_A = timberA.orientation.matrix.T * cutting_plane_normal_normalized
        cutting_plane_position_in_A = timberA.orientation.matrix.T * (cutting_plane_position - timberA.bottom_position)
        cutting_plane_offset_in_A = (cutting_plane_normal_in_A.T * cutting_plane_position_in_A)[0, 0]
        
        # Create HalfPlane that keeps the region on the positive side of the plane
        # (toward timberB from the cutting plane)
        half_plane_A = HalfPlane(
            normal=cutting_plane_normal_in_A,
            offset=cutting_plane_offset_in_A
        )
        
        # TimberA is cut by: (timberB prism) intersected with half_plane
        # This means: Difference(timberA, Difference(timberB_prism, half_plane))
        # Which simplifies to: Difference(timberA, timberB_prism ∩ half_plane_positive_region)
        # The CSG for this is: subtract (timberB_prism AND above_cutting_plane)
        # Which is: subtract Difference(timberB_prism, NOT(half_plane))
        # Since HalfPlane keeps >= side, we want to subtract the >= side
        # So: negative_csg = Difference(timberB_prism, half_plane) keeps the < side
        # Actually, we want to subtract: timberB_prism ∩ (normal·P >= offset region)
        # 
        # Let me think again: we want to remove from timberA the intersection of timberB_prism 
        # with the region on the timberB side of cutting plane.
        # The cutting plane normal points from A to B.
        # HalfPlane(normal, offset) keeps points where normal·P >= offset (positive side)
        # So we want to subtract: Difference(timberB_prism, NOT(half_plane))
        # Which is the same as: (timberB_prism) with everything on the negative side removed
        # That's just: subtract Difference(timberB_prism, inverse_half_plane)
        
        # Actually, simpler: subtract (timberB_prism ∩ positive_half_space)
        # In CSG: we can't directly intersect with HalfPlane
        # But Difference(A, B) - Difference(A, C) = A ∩ C if B contains C...
        # 
        # Even simpler approach: use two cuts
        # Cut 1: Subtract timberB prism
        # Cut 2: Add back the negative side using inverse half plane
        # Actually that's complicated too.
        #
        # Cleanest approach: Just use Difference(timberB_prism, inverse_halfplane)
        # inverse_halfplane keeps points where normal·P < offset
        # Which is HalfPlane(-normal, -offset) keeps points where -normal·P >= -offset, i.e., normal·P <= offset
        
        inverse_half_plane_A = HalfPlane(
            normal=-cutting_plane_normal_in_A,
            offset=-cutting_plane_offset_in_A
        )
        
        # Subtract the portion of timberB that's on the positive side of cutting plane
        negative_csg_A = Difference(
            base=timberB_prism_in_A,
            subtract=[inverse_half_plane_A]  # Remove the negative side, keeping positive side
        )
        
        cut_A = CSGCut(
            timber=timberA,
            transform=Transform(position=timberA.bottom_position, orientation=timberA.orientation),
            negative_csg=negative_csg_A,
            maybe_end_cut=None
        )
        cuts_A.append(cut_A)
    
    # TimberB: Cut by (timberA prism) intersected with (region on the timberA side of cutting plane)
    if cut_ratio < 1:  # Only cut timberB if cut_ratio < 1
        # Transform timberA prism to timberB's local coordinates
        relative_orientation_A_in_B = Orientation(timberB.orientation.matrix.T * timberA.orientation.matrix)
        timberA_origin_in_B_local = timberB.orientation.matrix.T * (timberA.bottom_position - timberB.bottom_position)
        
        # Create timberA prism in timberB's local coordinates (infinite extent)
        transform_A_in_B = Transform(position=timberA_origin_in_B_local, orientation=relative_orientation_A_in_B)
        timberA_prism_in_B = Prism(
            size=timberA.size,
            transform=transform_A_in_B,
            start_distance=None,  # Infinite
            end_distance=None     # Infinite
        )
        
        # Transform cutting plane to timberB's local coordinates
        cutting_plane_normal_in_B = timberB.orientation.matrix.T * cutting_plane_normal_normalized
        cutting_plane_position_in_B = timberB.orientation.matrix.T * (cutting_plane_position - timberB.bottom_position)
        cutting_plane_offset_in_B = (cutting_plane_normal_in_B.T * cutting_plane_position_in_B)[0, 0]
        
        # For timberB, we want to subtract the region on the negative side (timberA side) of the plane
        # So we use the inverse half plane (keeps normal·P <= offset, the negative side)
        half_plane_B = HalfPlane(
            normal=cutting_plane_normal_in_B,
            offset=cutting_plane_offset_in_B
        )
        
        # Subtract the portion of timberA that's on the negative side of cutting plane
        negative_csg_B = Difference(
            base=timberA_prism_in_B,
            subtract=[half_plane_B]  # Remove the positive side, keeping negative side
        )
        
        cut_B = CSGCut(
            timber=timberB,
            transform=Transform(position=timberB.bottom_position, orientation=timberB.orientation),
            negative_csg=negative_csg_B,
            maybe_end_cut=None
        )
        cuts_B.append(cut_B)
    
    # Create CutTimbers
    cut_timberA = CutTimber(timberA, cuts=cuts_A)
    cut_timberB = CutTimber(timberB, cuts=cuts_B)
    
    # Create and return the Joint
    joint = Joint(
        cut_timbers={"timberA": cut_timberA, "timberB": cut_timberB},
        jointAccessories={}
    )
    
    return joint


def _get_face_center_position(timber: Timber, face: TimberFace) -> V3:
    """
    Helper function to calculate the center position of a timber face.
    
    Args:
        timber: The timber object
        face: The face to get the center position for
        
    Returns:
        3D position vector at the center of the specified face
    """
    if face == TimberFace.TOP:
        return timber.get_top_center_position()
    elif face == TimberFace.BOTTOM:
        return timber.get_bottom_center_position()
    else:
        # For long faces (LEFT, RIGHT, FRONT, BACK), center is at mid-length
        from sympy import Rational
        face_center = timber.bottom_position + (timber.length / Rational(2)) * timber.length_direction
        
        # Offset to the face surface
        if face == TimberFace.RIGHT:
            face_center = face_center + (timber.size[0] / Rational(2)) * timber.width_direction
        elif face == TimberFace.LEFT:
            face_center = face_center - (timber.size[0] / Rational(2)) * timber.width_direction
        elif face == TimberFace.FRONT:
            face_center = face_center + (timber.size[1] / Rational(2)) * timber.height_direction
        else:  # BACK
            face_center = face_center - (timber.size[1] / Rational(2)) * timber.height_direction
        
        return face_center


def _find_closest_face_to_timber(timber: Timber, other_timber: Timber) -> TimberFace:
    """
    Helper function to find which face of timber is closest to other_timber's centerline.
    Returns the face that minimizes material removal for a cross lap joint.
    Uses the 4 side faces (not the end faces TOP/BOTTOM).
    """
    # Get the centerline point of other_timber (midpoint)
    from sympy import Rational
    other_center = other_timber.bottom_position + other_timber.length_direction * (other_timber.length / Rational(2))
    
    # Check distance from each side face to the other timber's center
    # Don't include TOP/BOTTOM as those are the end faces
    faces = [TimberFace.RIGHT, TimberFace.LEFT, 
             TimberFace.FRONT, TimberFace.BACK]
    
    min_distance = None
    closest_face = TimberFace.RIGHT  # Default
    
    for face in faces:
        face_center = _get_face_center_position(timber, face)
        distance = (face_center - other_center).norm()
        
        if min_distance is None or distance < min_distance:
            min_distance = distance
            closest_face = face
    
    return closest_face


def cut_basic_house_joint(housing_timber: Timber, housed_timber: Timber, housing_timber_cut_face: Optional[TimberFace] = None, housed_timber_cut_face: Optional[TimberFace] = None) -> Joint:
    """
    Creates a basic housed joint (also called housing joint or dado joint) where the 
    housing_timber is notched to fit the housed_timber. The housed timber fits completely
    into a notch cut in the housing timber.
    
    This is implemented as a cross lap joint with cut_ratio=1, meaning only the housing
    timber is cut.
    
    Args:
        housing_timber: Timber that will receive the housing cut (gets the groove)
        housed_timber: Timber that will be housed (fits into the groove, remains uncut)
        housing_timber_cut_face: Optional face of housing timber to cut. If not provided, automatically chosen.
        housed_timber_cut_face: Optional face of housed timber (for reference). If not provided, automatically chosen.
        
    Returns:
        Joint object containing both timbers
        
    Raises:
        AssertionError: If timbers don't intersect or are parallel
        
    Example:
        A shelf (housed_timber) fitting into the side of a cabinet (housing_timber).
        The cabinet side gets a groove cut into it to receive the shelf.
    """
    # Use cross lap joint with cut_ratio=1 (only cut housing_timber, not housed_timber)
    return cut_basic_cross_lap_joint(
        timberA=housing_timber,
        timberB=housed_timber,
        timberA_cut_face=housing_timber_cut_face,
        timberB_cut_face=housed_timber_cut_face,
        cut_ratio=Rational(1, 1)  # Cut only timberA (housing timber) completely
    )


# TODO DELETE
def cut_basic_house_joint_DEPRECATED(housing_timber: Timber, housed_timber: Timber, extend_housed_timber_to_infinity: bool = False) -> Joint:
    """
    DEPRECATED: Use cut_basic_house_joint() instead.
    
    Creates a basic housed joint (also called housing joint or dado joint) where the 
    housing_timber is notched to fit the housed_timber. The housed timber fits completely
    into a notch cut in the housing timber.
    
    Args:
        housing_timber: Timber that will receive the housing cut (gets the groove)
        housed_timber: Timber that will be housed (fits into the groove, remains uncut)
        extend_housed_timber_to_infinity: If True, the housed timber is extended to infinity in both directions, otherwise the finite timber is used
        
    Returns:
        Joint object containing both timbers
        
    Raises:
        AssertionError: If timbers don't intersect or are parallel
        
    Example:
        A shelf (housed_timber) fitting into the side of a cabinet (housing_timber).
        The cabinet side gets a groove cut into it to receive the shelf.
    """
    from code_goes_here.meowmeowcsg import Difference, Prism
    
    # Verify that the timbers are not parallel (their length directions must differ)
    dot_product = (housing_timber.length_direction.T * housed_timber.length_direction)[0, 0]
    assert abs(abs(dot_product) - 1) > Rational(1, 1000000), \
        "Timbers must not be parallel (their length directions must differ)"
    
    # Check that the timbers intersect when extended infinitely
    # For two lines to intersect, they must either:
    # 1. Actually intersect at a point, or
    # 2. Be skew lines that would intersect if one were translated
    # For housed joints, we require that they actually overlap in 3D space
    
    # A simple check: compute the closest points between the two timber centerlines
    # If the distance is less than the sum of half their cross-sections, they overlap
    
    # Direction vectors
    d1 = housing_timber.length_direction
    d2 = housed_timber.length_direction
    
    # Points on each line (use bottom positions)
    p1 = housing_timber.bottom_position
    p2 = housed_timber.bottom_position
    
    # Vector between the two line points
    w = p1 - p2
    
    # Calculate closest points between two lines in 3D
    # See: http://paulbourke.net/geometry/pointlineplane/
    a = (d1.T * d1)[0, 0]
    b = (d1.T * d2)[0, 0]
    c = (d2.T * d2)[0, 0]
    d = (d1.T * w)[0, 0]
    e = (d2.T * w)[0, 0]
    
    denom = a * c - b * b
    
    # If denom is very small, lines are parallel (already checked above)
    # Calculate parameters for closest points
    if abs(denom) < Rational(1, 1000000):
        # Lines are parallel, use simple distance check
        # Project p2 onto the line defined by p1 and d1
        t = -(d1.T * w)[0, 0] / a if a > 0 else 0
        closest_on_1 = p1 + t * d1
        distance = (p2 - closest_on_1).norm()
    else:
        t1 = (b * e - c * d) / denom
        t2 = (a * e - b * d) / denom
        
        closest_on_1 = p1 + t1 * d1
        closest_on_2 = p2 + t2 * d2
        
        distance = (closest_on_1 - closest_on_2).norm()
    
    # Check if timbers are close enough to intersect
    # They should intersect if the closest distance is less than the sum of half their cross-sections
    max_separation = (housing_timber.size[0] + housing_timber.size[1] + 
                     housed_timber.size[0] + housed_timber.size[1]) / 2
    
    assert float(distance) < float(max_separation), \
        f"Timbers do not intersect (closest distance: {float(distance):.4f}m, max allowed: {float(max_separation):.4f}m)"
    
    # Create a CSG difference: housing_timber - housed_timber
    # The housed timber's prism will be subtracted from the housing timber
    
    # Calculate the relative transformation
    # housed_prism in housing_timber's local frame = housing_orientation^T * housed_orientation
    relative_orientation = Orientation(housing_timber.orientation.matrix.T * housed_timber.orientation.matrix)
    
    # Transform the housed timber's position to housing timber's local coordinates
    housed_origin_local = housing_timber.orientation.matrix.T * (housed_timber.bottom_position - housing_timber.bottom_position)
    
    # Determine start and end distances based on extend_housed_timber_to_infinity
    if extend_housed_timber_to_infinity:
        # Use infinite prism to ensure it cuts through the housing timber completely
        start_distance = None
        end_distance = None
    else:
        # Use finite timber dimensions
        # The prism's position and orientation already place it in the housing timber's local space
        # So we just need the housed timber's own start (0) and end (length) distances
        start_distance = 0
        end_distance = housed_timber.length
    
    # Create the housed prism in housing timber's LOCAL coordinate system
    housed_transform_local = Transform(position=housed_origin_local, orientation=relative_orientation)
    housed_prism_local = Prism(
        size=housed_timber.size,
        transform=housed_transform_local,
        start_distance=start_distance,
        end_distance=end_distance
    )
    
    # Create the CSG cut for the housing timber
    cut = CSGCut(
        timber=housing_timber,
        transform=Transform(position=housing_timber.bottom_position, orientation=housing_timber.orientation),
        negative_csg=housed_prism_local,  # Subtract the housed timber's volume
        maybe_end_cut=None  # Not an end cut
    )
    
    # Create CutTimber for the housing timber (with cut)
    cut_housing = CutTimber(housing_timber, cuts=[cut])
    
    # Create CutTimber for the housed timber (no cuts)
    cut_housed = CutTimber(housed_timber, cuts=[])
    
    # Create and return the Joint
    joint = Joint(
        cut_timbers={"housing_timber": cut_housing, "housed_timber": cut_housed},
        jointAccessories={}
    )
    
    return joint
