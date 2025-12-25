"""
GiraffeCAD - Basic joint construction functions
Contains functions for creating joints between timbers
"""

from code_goes_here.timber import *
from code_goes_here.construction import *
from code_goes_here.moothymoth import Orientation

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
    cutA = HalfPlaneCut(
        timber=timberA,
        origin=intersection_point,
        orientation=timberA.orientation,
        half_plane=HalfPlane(normal=local_normalA, offset=local_offsetA),
        maybe_end_cut=timberA_end
    )
    
    cutB = HalfPlaneCut(
        timber=timberB,
        origin=intersection_point,
        orientation=timberB.orientation,
        half_plane=HalfPlane(normal=local_normalB, offset=local_offsetB),
        maybe_end_cut=timberB_end
    )
    
    # Create PartiallyCutTimbers with cuts passed at construction
    cut_timberA = PartiallyCutTimber(timberA, cuts=[cutA])
    cut_timberB = PartiallyCutTimber(timberB, cuts=[cutB])
    
    # Create and return the Joint with all data at construction
    joint = Joint(
        partially_cut_timbers=[cut_timberA, cut_timberB],
        joint_accessories=[]
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
    cut = HalfPlaneCut(
        timber=butt_timber,
        origin=face_center,
        orientation=butt_timber.orientation,
        half_plane=HalfPlane(normal=local_normal, offset=local_offset),
        maybe_end_cut=butt_end
    )
    
    # Create PartiallyCutTimber for the butt timber with cut passed at construction
    cut_butt = PartiallyCutTimber(butt_timber, cuts=[cut])
    
    # Create PartiallyCutTimber for the receiving timber (no cuts)
    cut_receiving = PartiallyCutTimber(receiving_timber, cuts=[])
    
    # Create and return the Joint with all data at construction
    joint = Joint(
        partially_cut_timbers=[cut_receiving, cut_butt],
        joint_accessories=[]
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
        Joint object containing the two PartiallyCutTimbers

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
        if distance_from_centerline > EPSILON_DEGENERATE:
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
    if centerline_distance > max_dimension / 2:
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
        origin=splice_point,
        orientation=timberA.orientation,
        half_plane=HalfPlane(normal=local_normalA, offset=local_offsetA),
        maybe_end_cut=timberA_end
    )
    
    cutB = HalfPlaneCut(
        timber=timberB,
        origin=splice_point,
        orientation=timberB.orientation,
        half_plane=HalfPlane(normal=local_normalB, offset=local_offsetB),
        maybe_end_cut=timberB_end
    )
    
    # Create PartiallyCutTimbers with cuts passed at construction
    cut_timberA = PartiallyCutTimber(timberA, cuts=[cutA])
    cut_timberB = PartiallyCutTimber(timberB, cuts=[cutB])
    
    # Create and return the Joint with all data at construction
    joint = Joint(
        partially_cut_timbers=[cut_timberA, cut_timberB],
        joint_accessories=[]
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
        Joint object containing the two PartiallyCutTimbers

    Raises:
    """

    # TODO
    # assert the 2 infinitely extended timbers overlap
    # assert that the 2 timbers are not parallel
    # if timberA/B_cut_face is not provided, choose a face that would minimize the amount of material removed
    # assert that the normals of timberA_cut_face and timberB_cut_face have dot product in the range (0,1] otherwise the cut would not be valid
    # pick the cutting plane by lerping the cut faces based on the cut_ratio (so if cut_ratio is 1, the cutface would be timberB_cut_face)
    # cut timberA by the CSG (timberB prism - cutting plane)
    # do the same for timberB (timberA prism + cutting plane)
    pass


def cut_basic_house_joint(housing_timber: Timber, housed_timber: Timber) -> Joint:
    """
    Creates a basic housed joint (also called housing joint or dado joint) where the 
    housing_timber is notched to fit the housed_timber. The housed timber fits completely
    into a rectangular groove cut in the housing timber.
    
    This is commonly used for:
    - Shelves fitting into uprights
    - Cross members fitting into beams
    - Floor joists fitting into sill plates
    
    Args:
        housing_timber: Timber that will receive the housing cut (gets the groove)
        housed_timber: Timber that will be housed (fits into the groove, remains uncut)
        
    Returns:
        Joint object containing both timbers
        
    Raises:
        AssertionError: If timbers don't intersect or are parallel
        
    Example:
        A shelf (housed_timber) fitting into the side of a cabinet (housing_timber).
        The cabinet side gets a groove cut into it to receive the shelf.
    """
    from code_goes_here.meowmeowcsg import Difference, create_prism
    
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
    
    # Create a prism for the housed timber in GLOBAL coordinates
    # We'll use an infinite prism to ensure it cuts through the housing timber completely
    housed_prism_global = create_prism(
        size=housed_timber.size,
        orientation=housed_timber.orientation,
        start_distance=None,  # Infinite in both directions
        end_distance=None
    )
    
    # Transform the global CSG to LOCAL coordinates of the housing timber
    # This requires transforming the housed prism's orientation relative to housing timber
    
    # Calculate the relative transformation
    # housed_prism in housing_timber's local frame = housing_orientation^T * housed_orientation
    relative_orientation = Orientation(housing_timber.orientation.matrix.T * housed_timber.orientation.matrix)
    
    # Transform the housed timber's position to housing timber's local coordinates
    housed_origin_local = housing_timber.orientation.matrix.T * (housed_timber.bottom_position - housing_timber.bottom_position)
    
    # Create the housed prism in housing timber's LOCAL coordinate system
    housed_prism_local = create_prism(
        size=housed_timber.size,
        orientation=relative_orientation,
        start_distance=None,  # Infinite
        end_distance=None
    )
    
    # Create the CSG cut for the housing timber
    cut = CSGCut(
        timber=housing_timber,
        origin=housing_timber.bottom_position,  # Reference point (not used for CSG cuts)
        orientation=housing_timber.orientation,
        negative_csg=housed_prism_local,  # Subtract the housed timber's volume
        maybe_end_cut=None  # Not an end cut
    )
    
    # Create PartiallyCutTimber for the housing timber (with cut)
    cut_housing = PartiallyCutTimber(housing_timber, cuts=[cut])
    
    # Create PartiallyCutTimber for the housed timber (no cuts)
    cut_housed = PartiallyCutTimber(housed_timber, cuts=[])
    
    # Create and return the Joint
    joint = Joint(
        partially_cut_timbers=[cut_housing, cut_housed],
        joint_accessories=[]
    )
    
    return joint

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
    

