"""
GiraffeCAD - Timber construction functions
Contains functions for creating and manipulating timbers
"""

import warnings
from code_goes_here.timber import *
from code_goes_here.moothymoth import *

# ============================================================================
# Timber Creation Functions
# ============================================================================

def create_timber(bottom_position: V3, length: Numeric, size: V2, 
                  length_direction: Direction3D, width_direction: Direction3D, name: Optional[str] = None) -> Timber:
    """
    Creates a timber at bottom_position with given dimensions and rotates it 
    to the length_direction and width_direction
    
    Args:
        bottom_position: Position of the bottom point of the timber
        length: Length of the timber
        size: Cross-sectional size (width, height)
        length_direction: Direction vector for the timber's length axis
        width_direction: Direction vector for the timber's width axis
        name: Optional name for this timber (used for rendering/debugging)
    """
    return timber_from_directions(length, size, bottom_position, length_direction, width_direction, name=name)

def create_axis_aligned_timber(bottom_position: V3, length: Numeric, size: V2,
                              length_direction: TimberFace, width_direction: Optional[TimberFace] = None, 
                              name: Optional[str] = None) -> Timber:
    """
    Creates an axis-aligned timber using TimberFace to reference directions
    in the world coordinate system.
    
    Args:
        bottom_position: Position of the bottom point of the timber
        length: Length of the timber
        size: Cross-sectional size (width, height)
        length_direction: Direction for the timber's length axis
        width_direction: Optional direction for the timber's width axis.
                        If not provided, defaults to RIGHT (+X) unless length_direction
                        is RIGHT, in which case TOP (+Z) is used.
        name: Optional name for this timber (used for rendering/debugging)
    
    Returns:
        New timber with the specified axis-aligned orientation
    """
    # Convert TimberFace to direction vectors
    length_vec = length_direction.get_direction()
    
    # Determine width direction if not provided
    if width_direction is None:
        # Default to RIGHT (+X) unless length is in +X direction
        if length_direction == TimberFace.RIGHT:
            width_direction = TimberFace.TOP
        else:
            width_direction = TimberFace.RIGHT
    
    if length_direction == TimberFace.BOTTOM:
        # print a warning, this is usually not what you want
        warnings.warn("Creating an axis-aligned timber with length_direction == BOTTOM. This is usually not what you want. Consider using length_direction == TOP instead.")
    
    width_vec = width_direction.get_direction()
    
    return create_timber(bottom_position, length, size, length_vec, width_vec, name=name)

def create_vertical_timber_on_footprint_corner(footprint: Footprint, corner_index: int, 
                                               length: Numeric, location_type: FootprintLocation,
                                               size: V2, name: Optional[str] = None) -> Timber:
    """
    Creates a vertical timber (post) on a footprint boundary corner.
    
    The post is positioned on an orthogonal boundary corner (where two boundary sides 
    are perpendicular) according to the location type:
    
    Location types:
    - INSIDE: Post has one vertex of bottom face on the boundary corner, with 2 edges 
              aligned with the 2 boundary sides, post extends inside the boundary
    - OUTSIDE: Post positioned with opposite vertex on the boundary corner, extends outside
    - CENTER: Post center is on the boundary corner, with 2 edges parallel to boundary sides
    
    Args:
        footprint: The footprint to place the timber on
        corner_index: Index of the boundary corner
        length: Length of the vertical timber (height)
        location_type: Where to position the timber relative to the boundary corner
        size: Timber size (width, depth) as a 2D vector
        name: Optional name for this timber (used for rendering/debugging)
        
    Returns:
        Timber positioned vertically on the footprint boundary corner
    """
    # Get the boundary corner point
    corner = footprint.corners[corner_index]
    
    # Get the two boundary sides meeting at this corner
    # Previous side: from corner_index-1 to corner_index
    # Next side: from corner_index to corner_index+1
    n_corners = len(footprint.corners)
    prev_corner = footprint.corners[(corner_index - 1) % n_corners]
    next_corner = footprint.corners[(corner_index + 1) % n_corners]
    
    # Calculate direction vectors for the two sides
    # Keep as exact values - don't convert to float
    outgoing_dir = Matrix([next_corner[0] - corner[0], 
                          next_corner[1] - corner[1]])
    
    # Normalize the direction vector
    from sympy import sqrt
    outgoing_len_sq = outgoing_dir[0]**2 + outgoing_dir[1]**2
    outgoing_len = sqrt(outgoing_len_sq)
    outgoing_dir_normalized = outgoing_dir / outgoing_len
    
    # Timber dimensions - keep as exact values from size parameter
    timber_width = size[0]   # Face direction (X-axis of timber)
    timber_depth = size[1]   # Height direction (Y-axis of timber)
    
    # Vertical direction (length)
    length_direction = create_v3(0, 0, 1)
    
    # Align timber face direction with outgoing boundary side
    # Face direction is in the XY plane along the outgoing side
    width_direction = create_v3(outgoing_dir_normalized[0], outgoing_dir_normalized[1], 0)
    
    # Calculate bottom position based on location type
    # Keep corner coordinates exact
    corner_x = corner[0]
    corner_y = corner[1]
    
    if location_type == FootprintLocation.INSIDE:
        # Position so one vertex of bottom face is on the boundary corner
        # Post extends inside the boundary
        # The corner vertex is at the origin of the timber's local coords
        bottom_position = create_v3(corner_x, corner_y, 0)
        
    elif location_type == FootprintLocation.OUTSIDE:
        # Position so the opposite vertex is on the boundary corner
        # Need to offset by the full diagonal of the timber base
        # Offset = -timber_width in face direction, -timber_depth in perpendicular direction
        # Use exact arithmetic: outgoing_dir_normalized components are rationals for axis-aligned
        offset_x = -timber_width * outgoing_dir_normalized[0] - timber_depth * (-outgoing_dir_normalized[1])
        offset_y = -timber_width * outgoing_dir_normalized[1] - timber_depth * outgoing_dir_normalized[0]
        bottom_position = create_v3(corner_x + offset_x, corner_y + offset_y, 0)
        
    else:  # CENTER
        # Position so center of bottom face is on the boundary corner
        # Offset by half dimensions in both directions
        from sympy import Rational
        offset_x = -timber_width/Rational(2) * outgoing_dir_normalized[0] - timber_depth/Rational(2) * (-outgoing_dir_normalized[1])
        offset_y = -timber_width/Rational(2) * outgoing_dir_normalized[1] - timber_depth/Rational(2) * outgoing_dir_normalized[0]
        bottom_position = create_v3(corner_x + offset_x, corner_y + offset_y, 0)
    
    return create_timber(bottom_position, length, size, length_direction, width_direction, name=name)

def create_vertical_timber_on_footprint_side(footprint: Footprint, side_index: int, 
                                            distance_along_side: Numeric,
                                            length: Numeric, location_type: FootprintLocation, 
                                            size: V2, name: Optional[str] = None) -> Timber:
    """
    Creates a vertical timber (post) positioned at a point along a footprint boundary side.
    
    The post is placed at a specified distance along the boundary side from the starting corner.
    
    Location types:
    - INSIDE: One edge of bottom face lies on boundary side, center of edge at the point, post extends inside
    - OUTSIDE: One edge of bottom face lies on boundary side, center of edge at the point, post extends outside
    - CENTER: Center of bottom face is on the point, 2 edges of bottom face parallel to boundary side
    
    Args:
        footprint: The footprint to place the timber on
        side_index: Index of the boundary side (from corner[side_index] to corner[side_index+1])
        distance_along_side: Distance from the starting corner along the side (0 = at start corner)
        length: Length of the vertical timber (height)
        location_type: Where to position the timber relative to the boundary side
        size: Timber size (width, depth) as a 2D vector
        name: Optional name for this timber (used for rendering/debugging)
        
    Returns:
        Timber positioned vertically at the specified point on the footprint boundary side
    """
    # Get the boundary side endpoints
    start_corner = footprint.corners[side_index]
    end_corner = footprint.corners[(side_index + 1) % len(footprint.corners)]
    
    # Calculate direction along the boundary side - keep exact
    side_dir = Matrix([end_corner[0] - start_corner[0], 
                       end_corner[1] - start_corner[1]])
    
    # Normalize the direction vector
    from sympy import sqrt
    side_len_sq = side_dir[0]**2 + side_dir[1]**2
    side_len = sqrt(side_len_sq)
    side_dir_normalized = side_dir / side_len
    
    # Calculate the point along the side
    point_x = start_corner[0] + side_dir_normalized[0] * distance_along_side
    point_y = start_corner[1] + side_dir_normalized[1] * distance_along_side
    
    # Calculate inward normal (perpendicular to side, pointing inward)
    # For a 2D vector (dx, dy), the perpendicular is (-dy, dx) or (dy, -dx)
    # We need to determine which one points inward
    perp_x = -side_dir_normalized[1]  # Left perpendicular
    perp_y = side_dir_normalized[0]
    
    # Test if this perpendicular points inward
    test_point = Matrix([point_x + perp_x * OFFSET_TEST_POINT,
                        point_y + perp_y * OFFSET_TEST_POINT])
    
    if footprint.contains_point(test_point):
        # Left perpendicular points inward
        inward_x = perp_x
        inward_y = perp_y
    else:
        # Right perpendicular points inward
        inward_x = side_dir_normalized[1]
        inward_y = -side_dir_normalized[0]
    
    # Timber dimensions - keep as exact values from size parameter
    timber_width = size[0]   # Width in face direction (parallel to boundary side)
    timber_depth = size[1]   # Depth perpendicular to boundary side
    
    # Vertical direction (length)
    length_direction = create_v3(0, 0, 1)
    
    # Face direction is parallel to the boundary side
    width_direction = create_v3(side_dir_normalized[0], side_dir_normalized[1], 0)
    
    # Calculate bottom position based on location type
    if location_type == FootprintLocation.CENTER:
        # Center of bottom face is on the point
        # No offset needed since timber local origin is at center of bottom face
        bottom_position = create_v3(point_x, point_y, 0)
        
    elif location_type == FootprintLocation.INSIDE:
        # One edge of bottom face lies on boundary side
        # Center of that edge is at the point
        # Post extends inside (in direction of inward normal)
        # Offset the center by half depth in the inward direction
        from sympy import Rational
        bottom_position = create_v3(point_x + inward_x * timber_depth / Rational(2), 
                                         point_y + inward_y * timber_depth / Rational(2), 
                                         0)
        
    else:  # OUTSIDE
        # One edge of bottom face lies on boundary side
        # Center of that edge is at the point
        # Post extends outside (opposite of inward normal)
        # Offset the center by half depth in the outward direction
        from sympy import Rational
        bottom_position = create_v3(point_x - inward_x * timber_depth / Rational(2), 
                                         point_y - inward_y * timber_depth / Rational(2), 
                                         0)
    
    return create_timber(bottom_position, length, size, length_direction, width_direction, name=name)

def create_horizontal_timber_on_footprint(footprint: Footprint, corner_index: int,
                                        location_type: FootprintLocation, 
                                        size: V2,
                                        length: Optional[Numeric] = None, name: Optional[str] = None) -> Timber:
    """
    Creates a horizontal timber (mudsill) on the footprint boundary side.
    
    The mudsill runs from corner_index to corner_index + 1 along the boundary side.
    With the face ends of the mudsill timber starting/ending on the footprint corners.
    
    Location types:
    - INSIDE: One edge of the timber lies on the boundary side, timber is on the inside
    - OUTSIDE: One edge of the timber lies on the boundary side, timber is on the outside
    - CENTER: The centerline of the timber lies on the boundary side
    
    Args:
        footprint: The footprint to place the timber on
        corner_index: Index of the starting boundary corner
        location_type: Where to position the timber relative to the boundary side
        size: Timber size (width, height) as a 2D vector
        length: Length of the timber (optional; if not provided, uses boundary side length)
        name: Optional name for this timber (used for rendering/debugging)
        
    Returns:
        Timber positioned on the footprint boundary side
    """
    # Get the footprint points
    start_point = footprint.corners[corner_index]
    end_point = footprint.corners[(corner_index + 1) % len(footprint.corners)]
        
    length_direction = normalize_vector(Matrix([end_point[0] - start_point[0], end_point[1] - start_point[1], 0]))

    # Calculate length from boundary side if not provided
    if length is None:
        from sympy import sqrt
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        length = sqrt(dx**2 + dy**2)
    
    # Get the inward normal from the footprint
    inward_x, inward_y, inward_z = footprint.get_inward_normal(corner_index)
    inward_normal = create_v3(inward_x, inward_y, inward_z)
    
    # Face direction is up (Z+)
    width_direction = create_v3(0, 0, 1)
    
    # The timber's orientation will be:
    #   X-axis (width/size[0]) = width_direction = (0, 0, 1) = vertical (up)
    #   Y-axis (height/size[1]) = length × face = perpendicular to boundary in XY plane
    #   Z-axis (length) = length_direction = along boundary side
    # Therefore, size[1] is the dimension perpendicular to the boundary
    timber_height = size[1]
    
    # Calculate bottom position based on location type
    # Start at the start_point on the boundary side - keep exact
    bottom_position = create_v3(start_point[0], start_point[1], 0)
    
    # Apply offset based on location type
    if location_type == FootprintLocation.INSIDE:
        # Position so one edge lies on the boundary side, timber extends inward
        # Move the centerline inward by half the timber height (perpendicular dimension)
        from sympy import Rational
        bottom_position = bottom_position + inward_normal * (timber_height / Rational(2))
    elif location_type == FootprintLocation.OUTSIDE:
        # Position so one edge lies on the boundary side, timber extends outward
        # Move the centerline outward by half the timber height (perpendicular dimension)
        from sympy import Rational
        bottom_position = bottom_position - inward_normal * (timber_height / Rational(2))
    # For CENTER, no offset needed - centerline is already on the boundary side
    
    return create_timber(bottom_position, length, size, length_direction, width_direction, name=name)

def stretch_timber(timber: Timber, end: TimberReferenceEnd, overlap_length: Numeric, 
                  extend_length: Numeric) -> Timber:
    """
    Creates a new timber extending the original timber by a given length.

    The original timber is conceptually discarded and replaced with a new timber that is the original timber plus the extension.

    Args:
        end: The end of the timber to extend
        overlap_length: Length of timber to overlap with existing timber
        extend_length: Length of timber to extend beyond the end of the original timber (does not include the overlap length)
    """
    # Calculate new position based on end
    if end == TimberReferenceEnd.TOP:
        # Extend from top
        extension_vector = timber.get_length_direction_global() * (timber.length - overlap_length)
        new_bottom_position = timber.get_bottom_position_global() + extension_vector
    else:  # BOTTOM
        # Extend from bottom
        extension_vector = timber.get_length_direction_global() * extend_length
        new_bottom_position = timber.get_bottom_position_global() - extension_vector
    
    # Create new timber with extended length
    new_length = timber.length + extend_length + overlap_length
    
    return timber_from_directions(new_length, timber.size, new_bottom_position, 
                                   timber.get_length_direction_global(), timber.get_width_direction_global())

# TODO add some sorta splice stickout parameter
def split_timber(
    timber: Timber, 
    distance_from_bottom: Numeric,
    name1: Optional[str] = None,
    name2: Optional[str] = None
) -> Tuple[Timber, Timber]:
    """
    Split a timber into two timbers at the specified distance from the bottom.
    
    The original timber is conceptually discarded and replaced with two new timbers:
    - The first timber extends from the original bottom to the split point
    - The second timber extends from the split point to the original top
    
    Both timbers maintain the same cross-sectional size and orientation as the original.
    You will often follow this with a splice joint to join the two timbers together.
    
    Args:
        timber: The timber to split
        distance_from_bottom: Distance along the timber's length where to split (0 < distance < timber.length)
        name1: Optional name for the bottom timber (defaults to "{original_name}_bottom")
        name2: Optional name for the top timber (defaults to "{original_name}_top")
        
    Returns:
        Tuple of (bottom_timber, top_timber) where:
        - bottom_timber starts at the same position as the original
        - top_timber starts at the top end of bottom_timber
        
    Example:
        If a timber has length 10 and is split at distance 3:
        - bottom_timber has length 3, same origin as original
        - top_timber has length 7, origin at distance 3 from original origin
    """
    # Validate input
    assert 0 < distance_from_bottom < timber.length, \
        f"Split distance {distance_from_bottom} must be between 0 and {timber.length}"
    
    # Determine names for the split timbers
    bottom_name = name1 if name1 is not None else (f"{timber.name}_bottom" if timber.name else "split_bottom")
    top_name = name2 if name2 is not None else (f"{timber.name}_top" if timber.name else "split_top")
    
    # Create first timber (bottom part)
    bottom_timber = timber_from_directions(
        length=distance_from_bottom,
        size=create_v2(timber.size[0], timber.size[1]),
        bottom_position=timber.get_bottom_position_global(),
        length_direction=timber.get_length_direction_global(),
        width_direction=timber.get_width_direction_global(),
        name=bottom_name
    )
    
    # Calculate the bottom position of the second timber
    # It's at the top of the first timber
    top_of_first = timber.get_bottom_position_global() + distance_from_bottom * timber.get_length_direction_global()
    
    # Create second timber (top part)
    top_timber = timber_from_directions(
        length=timber.length - distance_from_bottom,
        size=create_v2(timber.size[0], timber.size[1]),
        bottom_position=top_of_first,
        length_direction=timber.get_length_direction_global(),
        width_direction=timber.get_width_direction_global(),
        name=top_name
    )
    
    return (bottom_timber, top_timber)

# TODO rename to create/raise_joining_timber
def join_timbers(timber1: Timber, timber2: Timber, 
                location_on_timber1: Numeric,
                location_on_timber2: Optional[Numeric] = None,
                lateral_offset: Numeric = Integer(0),
                stickout: Stickout = Stickout.nostickout(),
                size: Optional[V2] = None,
                orientation_width_vector: Optional[Direction3D] = None, 
                name: Optional[str] = None) -> Timber:
    """
    Joins two timbers by creating a connecting timber from centerline to centerline.
    
    This function creates a timber that connects the centerline of timber1 to the centerline
    of timber2. The joining timber's length direction goes from timber1 to timber2, and its
    position can be laterally offset from this centerline-to-centerline path.
    
    Args:
        timber1: First timber to join (start point)
        timber2: Second timber to join (end point)
        location_on_timber1: Position along timber1's length where the joining timber starts
        location_on_timber2: Optional position along timber2's length where the joining timber ends.
                            If not provided, uses the same Z-height as location_on_timber1.
        lateral_offset: Lateral offset of the joining timber perpendicular to the direct 
                       centerline-to-centerline path. The offset direction is determined by the
                       cross product of timber1's length direction and the joining direction.
                       Defaults to Integer(0) (no offset).
        stickout: How much the joining timber extends beyond each connection point (both sides).
                  Always measured from centerlines in this function.
                  Defaults to Stickout.nostickout() if not provided.
        size: Optional size (width, height) of the joining timber. If not provided,
              determined from timber1's size based on orientation.
        orientation_width_vector: Optional width direction hint for the created timber in global space.
                                 Will be automatically projected onto the plane perpendicular to the 
                                 joining direction (from timber1 to timber2). This is useful for 
                                 specifying orientation like "face up" for rafters.
                                 If not provided, uses timber1's length direction projected onto
                                 the perpendicular plane.
                                 If the provided vector is parallel to the joining direction, falls back
                                 to timber1's width direction.
        name: Optional name for this timber (used for rendering/debugging)
        
    Returns:
        New timber connecting timber1 and timber2 along their centerlines
    """
    # Calculate position on timber1
    pos1 = timber1.get_centerline_position_from_bottom_global(location_on_timber1)
    
    # Calculate position on timber2
    if location_on_timber2 is not None:
        pos2 = timber2.get_centerline_position_from_bottom_global(location_on_timber2)
    else:
        # Project location_on_timber1 to timber2's Z axis
        pos2 = Matrix([pos1[0], pos1[1], timber2.get_bottom_position_global()[2] + location_on_timber1])
    
    # Calculate length direction (from timber1 to timber2)
    length_direction = pos2 - pos1
    length_direction = normalize_vector(length_direction)
    
    # Calculate face direction (width direction for the created timber)
    if orientation_width_vector is not None:
        reference_direction = orientation_width_vector
    else:
        # Default: use timber1's length direction
        reference_direction = timber1.get_length_direction_global()
    
    # Check if reference direction is parallel to the joining direction
    if _are_directions_parallel(reference_direction, length_direction):
        # If parallel, cannot project - use a perpendicular fallback
        if orientation_width_vector is not None:
            warnings.warn(f"orientation_width_vector {orientation_width_vector} is parallel to the joining direction {length_direction}. Using timber1's width direction instead.")
            reference_direction = timber1.get_width_direction_global()
        else:
            warnings.warn("timber1's length direction is parallel to the joining direction. Using timber1's width direction instead.")
            reference_direction = timber1.get_width_direction_global()
    
    # Project reference direction onto the plane perpendicular to the joining direction
    # Formula: v_perp = v - (v·n)n
    dot_product = reference_direction.dot(length_direction)
    width_direction = reference_direction - dot_product * length_direction
    width_direction = normalize_vector(width_direction)
    
    # TODO TEST THIS IT'S PROBABLY WRONG
    # Determine size if not provided
    if size is None:
        # Check the orientation of the created timber relative to timber1
        # Dot product of the created timber's face direction with timber1's length direction
        dot_product = Abs(width_direction.dot(timber1.get_length_direction_global()))
        
        if dot_product < Rational(1, 2):  # < 0.5, meaning more perpendicular than parallel
            # The created timber is joining perpendicular to timber1
            # Its X dimension (width, along width_direction) should match the dimension 
            # of the face it's joining to on timber1, which is timber1's width (size[0])
            size = create_v2(timber1.size[0], timber1.size[1])
        else:
            # For other orientations, use timber1's size as-is
            size = create_v2(timber1.size[0], timber1.size[1])
    
    # Assert that join_timbers only uses CENTER_LINE stickout reference
    assert stickout.stickoutReference1 == StickoutReference.CENTER_LINE, \
        "join_timbers only supports CENTER_LINE stickout reference. Use join_perpendicular_on_face_parallel_timbers for INSIDE/OUTSIDE references."
    assert stickout.stickoutReference2 == StickoutReference.CENTER_LINE, \
        "join_timbers only supports CENTER_LINE stickout reference. Use join_perpendicular_on_face_parallel_timbers for INSIDE/OUTSIDE references."
    
    # Calculate timber length with stickout (always from centerline in join_timbers)
    centerline_distance = vector_magnitude(pos2 - pos1)
    timber_length = centerline_distance + stickout.stickout1 + stickout.stickout2
    
    # Apply lateral offset
    if lateral_offset != 0:
        # Calculate offset direction (cross product of length vectors)
        offset_dir = normalize_vector(cross_product(timber1.get_length_direction_global(), length_direction))
    
    # Calculate the bottom position (start of timber)
    # Start from pos1 and move backward by stickout1 (always centerline)
    bottom_pos = pos1 - length_direction * stickout.stickout1
    
    # Apply offset to bottom position as well (if any offset was applied to center)
    if lateral_offset != 0:
        bottom_pos += offset_dir * lateral_offset
    
    return create_timber(bottom_pos, timber_length, size, length_direction, width_direction, name=name)

# TODO change offset_from_timber1 to lateral_offset_from_timber1
# TODO rename to create/raise_joining_timber_perpendicular_on_face_parallel_timbers
def join_perpendicular_on_face_parallel_timbers(timber1: Timber, timber2: Timber,
                                                location_on_timber1: Numeric,
                                                stickout: Stickout,
                                                offset_from_timber1: FaceAlignedJoinedTimberOffset,
                                                size: V2,
                                                orientation_face_on_timber1: Optional[TimberFace] = None, 
                                                name: Optional[str] = None) -> Timber:
    """
    Joins two face-aligned timbers with a perpendicular timber.
    
    Args:
        timber1: First timber to join
        timber2: Second timber to join (face-aligned with timber1)
        location_on_timber1: Position along timber1's length where the joining timber attaches
        stickout: How much the joining timber extends beyond each connection point
        offset_from_timber1: Offset configuration from timber1
        size: Cross-sectional size (width, height) of the joining timber
        orientation_face_on_timber1: Optional face of timber1 to orient against. If provided,
                                     the width direction of the created timber will align with this face.
                                     If not provided, uses timber1's length direction projected onto
                                     the perpendicular plane.
        name: Optional name for this timber (used for rendering/debugging)
        
    Returns:
        New timber that joins timber1 and timber2
    """
    # Verify that the two timbers are face-aligned
    assert are_timbers_face_aligned(timber1, timber2), \
        "timber1 and timber2 must be face-aligned (share at least one parallel direction)"
    
    # Auto-determine size if not provided
    if size is None:
        # Use timber1's size as the default
        size = timber1.size
    
    # Calculate position on timber1
    pos1 = timber1.get_centerline_position_from_bottom_global(location_on_timber1)
    
    # Project pos1 onto timber2's centerline to find location_on_timber2
    # Vector from timber2's bottom to pos1
    to_pos1 = pos1 - timber2.get_bottom_position_global()
    
    # Project this onto timber2's length direction to find the parameter t
    location_on_timber2 = to_pos1.dot(timber2.get_length_direction_global()) / timber2.get_length_direction_global().dot(timber2.get_length_direction_global())
    
    # Clamp location_on_timber2 to be within the timber's length
    location_on_timber2 = max(0, min(timber2.length, location_on_timber2))
    
    # Convert TimberFace to a direction vector for orientation (if provided)
    orientation_width_vector = orientation_face_on_timber1.get_direction() if orientation_face_on_timber1 is not None else None
    
    # Extract the centerline offset (use 0 if not provided)
    offset_value = offset_from_timber1.centerline_offset if offset_from_timber1.centerline_offset is not None else 0
    
    # Convert INSIDE/OUTSIDE stickout references to CENTER_LINE
    # For face-aligned timbers, we know the joining direction
    pos2 = timber2.get_centerline_position_from_bottom_global(location_on_timber2)
    joining_direction = normalize_vector(pos2 - pos1)
    
    # Determine which dimension of the created timber is perpendicular to the joining direction
    # The created timber will have:
    # - length_direction = joining_direction
    # - width_direction = orientation_width_vector
    # - height_direction = cross(length_direction, width_direction)
    
    # To determine which dimension (width=size[0] or height=size[1]) affects the stickout,
    # we need to see which one is aligned with the joining direction's perpendicular plane
    # For simplicity, we'll use the dot product to determine which axis is more aligned
    
    # Determine perpendicular size for stickout conversion
    # Only needed if stickout references are not CENTER_LINE
    if stickout.stickoutReference1 != StickoutReference.CENTER_LINE or stickout.stickoutReference2 != StickoutReference.CENTER_LINE:
        # Need to determine which dimension is perpendicular
        if orientation_width_vector is not None:
            # The width (size[0]) is along the width_direction
            # The height (size[1]) is along the height_direction (perpendicular to both)
            height_direction = normalize_vector(cross_product(joining_direction, orientation_width_vector))
            
            # Check which dimension is more perpendicular to timber1's length direction
            # This determines which face is "inside" (facing timber1)
            face_dot = Abs(orientation_width_vector.dot(timber1.get_length_direction_global()))
            height_dot = Abs(height_direction.dot(timber1.get_length_direction_global()))
            
            # Use the dimension that's more perpendicular to timber1's length
            if face_dot < height_dot:
                # Face direction is more perpendicular, so width (size[0]) affects inside/outside
                perpendicular_size = size[0]
            else:
                # Height direction is more perpendicular, so height (size[1]) affects inside/outside
                perpendicular_size = size[1]
        else:
            # Without orientation specified, default to using width
            perpendicular_size = size[0]
    else:
        # Not needed for CENTER_LINE stickout
        perpendicular_size = 0
    
    # Convert stickout references to centerline offsets
    centerline_stickout1 = stickout.stickout1
    centerline_stickout2 = stickout.stickout2
    
    if stickout.stickoutReference1 == StickoutReference.INSIDE:
        # INSIDE: Extends from the face closest to timber2
        # Add half the perpendicular size
        centerline_stickout1 = stickout.stickout1 + perpendicular_size / 2
    elif stickout.stickoutReference1 == StickoutReference.OUTSIDE:
        # OUTSIDE: Extends from the face away from timber2
        # Subtract half the perpendicular size
        centerline_stickout1 = stickout.stickout1 - perpendicular_size / 2
    
    if stickout.stickoutReference2 == StickoutReference.INSIDE:
        # INSIDE: Extends from the face closest to timber1
        centerline_stickout2 = stickout.stickout2 + perpendicular_size / 2
    elif stickout.stickoutReference2 == StickoutReference.OUTSIDE:
        # OUTSIDE: Extends from the face away from timber1
        centerline_stickout2 = stickout.stickout2 - perpendicular_size / 2
    
    # Create a new Stickout with CENTER_LINE reference
    centerline_stickout = Stickout(
        centerline_stickout1,
        centerline_stickout2,
        StickoutReference.CENTER_LINE,
        StickoutReference.CENTER_LINE
    )
    
    # Call join_timbers to do the actual work
    return join_timbers(
        timber1=timber1,
        timber2=timber2,
        location_on_timber1=location_on_timber1,
        stickout=centerline_stickout,
        location_on_timber2=location_on_timber2,
        lateral_offset=offset_value,
        orientation_width_vector=orientation_width_vector,
        size=size,
        name=name
    )




# ============================================================================
# Helper Functions
# ============================================================================

def are_timbers_parallel(timber1: Timber, timber2: Timber, tolerance: Optional[Numeric] = None) -> bool:
    """
    Check if two timbers have parallel length directions.
    
    Args:
        timber1: First timber
        timber2: Second timber
        tolerance: Optional tolerance for approximate comparison. If None, attempts exact comparison and uses default epsilon if not possible.
                   
    Returns:
        True if timbers have parallel length directions, False otherwise
    """
    dot_product = Abs(timber1.get_length_direction_global().dot(timber2.get_length_direction_global()))
    
    if tolerance is None:
        # Use automatic comparison (SymPy .equals() for symbolic, epsilon for floats)
        return equality_test(dot_product, 1)
    else:
        # Use provided tolerance for approximate comparison
        return Abs(dot_product - 1) < tolerance

def are_timbers_orthogonal(timber1: Timber, timber2: Timber, tolerance: Optional[Numeric] = None) -> bool:
    """
    Check if two timbers have orthogonal (perpendicular) length directions.
    
    Args:
        timber1: First timber
        timber2: Second timber
        tolerance: Optional tolerance for approximate comparison. If None, automatically
                   uses exact comparison for rational values or fuzzy comparison for floats.
                   
    Returns:
        True if timbers have orthogonal length directions, False otherwise
    """
    dot_product = timber1.get_length_direction_global().dot(timber2.get_length_direction_global())
    
    if tolerance is None:
        # Use automatic comparison (SymPy .equals() for symbolic, epsilon for floats)
        return zero_test(dot_product)
    else:
        # Use provided tolerance for approximate comparison
        return Abs(dot_product) < tolerance

def are_timbers_face_aligned(timber1: Timber, timber2: Timber, tolerance: Optional[Numeric] = None) -> bool:
    """
    Check if two timbers are face-aligned.
    
    Two timbers are face-aligned if any face of one timber is parallel to any face 
    of the other timber. This occurs when their orientations are related by 90-degree 
    rotations around any axis (i.e., they share the same coordinate grid alignment).
    
    Mathematically, timbers are face-aligned if any of their orthogonal direction 
    vectors (length_direction, width_direction, height_direction) are parallel to each other.
    
    Args:
        timber1: First timber
        timber2: Second timber  
        tolerance: Optional numerical tolerance for parallel check. If None, uses exact
                   equality (recommended when using SymPy Rational types). If provided,
                   uses approximate floating-point comparison.
        
    Returns:
        True if timbers are face-aligned, False otherwise
    """
    # Get the three orthogonal direction vectors for each timber
    dirs1 = [timber1.get_length_direction_global(), timber1.get_width_direction_global(), timber1.get_height_direction_global()]
    dirs2 = [timber2.get_length_direction_global(), timber2.get_width_direction_global(), timber2.get_height_direction_global()]
    
    # Check all pairs of directions
    for dir1 in dirs1:
        for dir2 in dirs2:
            dot_product = Abs(dir1.dot(dir2))
            
            if tolerance is None:
                # Use automatic comparison (SymPy .equals() for symbolic, epsilon for floats)
                if equality_test(dot_product, 1):
                    return True
            else:
                # Use provided tolerance for approximate comparison
                if Abs(dot_product - 1) < tolerance:
                    return True
    
    return False

  
def do_xy_cross_section_on_parallel_timbers_overlap(timberA: Timber, timberB: Timber) -> bool:
    """
    Check if the cross-section of two parallel timbers overlap.
    
    Converts timberB into timberA's local space and checks if the XY cross-sections
    (defined by bottom_position and size) overlap.

    Args:
        timberA: First timber
        timberB: Second timber

    Returns:
        True if the cross-sections overlap, False otherwise
    """
    from sympy import Rational
    
    assert are_vectors_parallel(timberA.get_length_direction_global(), timberB.get_length_direction_global()), "Timbers must be parallel"

    # Convert timberB's bottom position into timberA's local space
    timberB_bottom_local = timberA.transform.global_to_local(timberB.get_bottom_position_global())
    
    # In timberA's local space:
    # - timberA's cross section is centered at (0, 0) in XY plane
    # - timberA spans from (-width/2, -height/2) to (width/2, height/2)
    timberA_x_min = -timberA.size[0] / Rational(2)
    timberA_x_max = timberA.size[0] / Rational(2)
    timberA_y_min = -timberA.size[1] / Rational(2)
    timberA_y_max = timberA.size[1] / Rational(2)
    
    # timberB's cross section is centered at (timberB_bottom_local.x, timberB_bottom_local.y)
    # We need to transform timberB's width and height directions into timberA's local space
    # to determine the extents of timberB's cross section
    
    # Get timberB's width and height directions in global space
    timberB_width_dir_global = timberB.get_width_direction_global()
    timberB_height_dir_global = timberB.get_height_direction_global()
    
    # Convert to timberA's local space (just rotate, don't translate)
    timberB_width_dir_local = timberA.orientation.matrix.T * timberB_width_dir_global
    timberB_height_dir_local = timberA.orientation.matrix.T * timberB_height_dir_global
    
    # Get the four corners of timberB's cross section in timberA's local space
    # Start from timberB's center in local space
    timberB_center_local_xy = create_v2(timberB_bottom_local[0], timberB_bottom_local[1])
    
    # Offset vectors for the corners (in timberA's local XY plane)
    half_width = timberB.size[0] / Rational(2)
    half_height = timberB.size[1] / Rational(2)
    
    # Corner offsets in timberA's local space
    offset_width_local = create_v2(timberB_width_dir_local[0], timberB_width_dir_local[1]) * half_width
    offset_height_local = create_v2(timberB_height_dir_local[0], timberB_height_dir_local[1]) * half_height
    
    # Four corners of timberB in timberA's local XY coordinates
    corner1 = timberB_center_local_xy + offset_width_local + offset_height_local
    corner2 = timberB_center_local_xy + offset_width_local - offset_height_local
    corner3 = timberB_center_local_xy - offset_width_local + offset_height_local
    corner4 = timberB_center_local_xy - offset_width_local - offset_height_local
    
    # Find axis-aligned bounding box of timberB in timberA's local space
    from sympy import Min, Max
    timberB_x_min = Min(corner1[0], corner2[0], corner3[0], corner4[0])
    timberB_x_max = Max(corner1[0], corner2[0], corner3[0], corner4[0])
    timberB_y_min = Min(corner1[1], corner2[1], corner3[1], corner4[1])
    timberB_y_max = Max(corner1[1], corner2[1], corner3[1], corner4[1])
    
    # Check if the axis-aligned bounding boxes overlap
    # Two rectangles overlap if they overlap in both X and Y dimensions
    x_overlap = timberA_x_max >= timberB_x_min and timberB_x_max >= timberA_x_min
    y_overlap = timberA_y_max >= timberB_y_min and timberB_y_max >= timberA_y_min
    
    return x_overlap and y_overlap





# =========================================
# internal helpers
# =========================================



def _are_directions_perpendicular(direction1: Direction3D, direction2: Direction3D, tolerance: Optional[Numeric] = None) -> bool:
    """
    Check if two direction vectors are perpendicular (orthogonal).
    
    Args:
        direction1: First direction vector
        direction2: Second direction vector
        tolerance: Optional tolerance for approximate comparison. If None, automatically
                   uses exact comparison for rational values or fuzzy comparison for floats.
    
    Returns:
        True if the directions are perpendicular, False otherwise
    """
    dot_product = direction1.dot(direction2)
    
    if tolerance is None:
        # Use automatic comparison (SymPy .equals() for symbolic, epsilon for floats)
        return zero_test(dot_product)
    else:
        # Use provided tolerance for approximate comparison
        return Abs(dot_product) < tolerance

def _are_directions_parallel(direction1: Direction3D, direction2: Direction3D, tolerance: Optional[Numeric] = None) -> bool:
    """
    Check if two direction vectors are parallel (or anti-parallel).
    
    Args:
        direction1: First direction vector
        direction2: Second direction vector
        tolerance: Optional tolerance for approximate comparison. If None, automatically
                   uses exact comparison for rational values or fuzzy comparison for floats.
    
    Returns:
        True if the directions are parallel, False otherwise
    """
    dot_product = direction1.dot(direction2)
    dot_mag = Abs(dot_product)
    
    if tolerance is None:
        # Use automatic comparison (SymPy .equals() for symbolic, epsilon for floats)
        return equality_test(dot_mag, 1)
    else:
        # Use provided tolerance for approximate comparison
        return Abs(dot_mag - 1) < tolerance
