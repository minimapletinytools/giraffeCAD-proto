"""
Random timber-related helper functions.

Contains utility functions for working with timbers that don't fit into a more specific category.
"""

from .moothymoth import *
from .timber import *



# ============================================================================
# Various geometric helper functions that should all be replaced with marking/measuring functions
# TODO DELETE ME 
# ============================================================================

# DEPRECATED
def get_point_on_face_global(face: TimberFace, timber: Timber) -> V3:
    """
    Get a point on the timber face. Useful for projecting points onto the face.
    
    Args:
        face: The face to get a point on
        timber: The timber
        
    Returns:
        A point on the face surface in global coordinates
    """
    return timber.get_bottom_position_global() + timber.get_face_direction_global(face) * timber.get_size_in_face_normal_axis(face) / 2


# DEPRECATED
def project_point_onto_face_global(point_global: V3, face: TimberFace, timber: Timber) -> Numeric:
    """
    Project a point onto a timber face and return the signed distance.
    
    Returns the signed distance from the face to the point, measured along the face normal.
    Positive means the point is inside the timber (in the direction of the face normal).
    Negative means the point is outside the timber (opposite to the face normal).
    
    Args:
        point: Point in global coordinates to project
        face: The face to project onto
        timber: The timber
        
    Returns:
        Signed distance from face to point along the face normal (positive = into timber)
    """
    # Get a reference point on the face surface
    face_point_global = get_point_on_face_global(face, timber)
    
    # Get the face normal (pointing OUT of the timber)
    face_direction_global = timber.get_face_direction_global(face)
    
    # Calculate signed distance: how far from the face is the point?
    # Positive if point is in the direction opposite to face_direction (inside timber)
    # Negative if point is in the direction of face_direction (outside timber)
    distance = (face_direction_global.T * (face_point_global - point_global))[0, 0]
    
    return distance



# ============================================================================
# Helper Functions for Creating Joint Accessories
# ============================================================================

def create_peg_going_into_face(
    timber: Timber,
    face: TimberLongFace,
    distance_from_bottom: Numeric,
    distance_from_centerline: Numeric,
    peg_size: Numeric,
    peg_shape: PegShape,
    forward_length: Numeric,
    stickout_length: Numeric
) -> Peg:
    """
    Create a peg that goes into a specified long face of a timber.
    
    The peg is created in the local space of the timber, with the insertion end
    at the timber's surface and pointing inward perpendicular to the face.
    
    Args:
        timber: The timber to insert the peg into
        face: Which long face the peg enters from (RIGHT, LEFT, FRONT, or BACK)
        distance_from_bottom: Distance along the timber's length from the bottom end
        distance_from_centerline: Distance from the timber's centerline along the face
        peg_size: Size/diameter of the peg (for square pegs, this is the side length)
        peg_shape: Shape of the peg (SQUARE or ROUND)
        forward_length: How far the peg reaches in the forward direction
        stickout_length: How far the peg sticks out in the back direction
        
    Returns:
        Peg object positioned and oriented appropriately in timber's local space
    """
    # Get the face direction in local space (timber coordinate system)
    # In local coords: X = width, Y = height, Z = length
    face_normal_local = face.to.face().get_direction()
    
    # Position the peg on the timber's surface
    # Start at centerline, then move along length and offset from centerline
    position_local = create_v3(0, 0, distance_from_bottom)
    
    # Offset from centerline depends on which face we're on
    if face == TimberLongFace.RIGHT:
        # RIGHT face: offset in +X (width) direction, surface at +width/2
        position_local = create_v3(
            timber.size[0] / Rational(2),  # At right surface
            distance_from_centerline,  # Offset in height direction
            distance_from_bottom
        )
        # Peg points inward (-X direction in local space)
        length_dir = create_v3(-1, 0, 0)
        width_dir = create_v3(0, 1, 0)
        
    elif face == TimberLongFace.LEFT:
        # LEFT face: offset in -X (width) direction
        position_local = create_v3(
            -timber.size[0] / Rational(2),  # At left surface
            distance_from_centerline,  # Offset in height direction
            distance_from_bottom
        )
        # Peg points inward (+X direction in local space)
        length_dir = create_v3(1, 0, 0)
        width_dir = create_v3(0, 1, 0)
        
    elif face == TimberLongFace.FRONT:
        # FRONT face: offset in +Y (height) direction
        position_local = create_v3(
            distance_from_centerline,  # Offset in width direction
            timber.size[1] / Rational(2),  # At forward surface
            distance_from_bottom
        )
        # Peg points inward (-Y direction in local space)
        length_dir = create_v3(0, -1, 0)
        width_dir = create_v3(1, 0, 0)
        
    else:  # BACK
        # BACK face: offset in -Y (height) direction
        position_local = create_v3(
            distance_from_centerline,  # Offset in width direction
            -timber.size[1] / Rational(2),  # At back surface
            distance_from_bottom
        )
        # Peg points inward (+Y direction in local space)
        length_dir = create_v3(0, 1, 0)
        width_dir = create_v3(1, 0, 0)
    
    # Compute peg orientation (peg's Z-axis points into the timber)
    peg_orientation = compute_timber_orientation(length_dir, width_dir)
    peg_transform = Transform(position=position_local, orientation=peg_orientation)
    
    return Peg(
        transform=peg_transform,
        size=peg_size,
        shape=peg_shape,
        forward_length=forward_length,
        stickout_length=stickout_length
    )


def create_wedge_in_timber_end(
    timber: Timber,
    end: TimberReferenceEnd,
    position: V3,
    shape: WedgeShape
) -> Wedge:
    """
    Create a wedge at the end of a timber.
    
    The wedge is created in the local space of the timber. In identity orientation,
    the point of the wedge goes in the length direction (Z-axis in local space).
    
    Args:
        timber: The timber to insert the wedge into
        end: Which end of the timber (TOP or BOTTOM)
        position: Position in the timber's cross-section (X, Y in local space, Z ignored)
        shape: Specification of wedge dimensions
        
    Returns:
        Wedge object positioned and oriented appropriately in timber's local space
    """
    # Determine wedge position and orientation based on which end
    if end == TimberReferenceEnd.TOP:
        # At top end, wedge points downward into timber (-Z in local space)
        # Position at the top of the timber
        wedge_position = create_v3(
            position[0],  # X position (cross-section)
            position[1],  # Y position (cross-section)
            timber.length  # At the top end
        )
        # Wedge points downward
        length_dir = create_v3(0, 0, -1)
        width_dir = create_v3(1, 0, 0)
        
    else:  # BOTTOM
        # At bottom end, wedge points upward into timber (+Z in local space)
        # Position at the bottom of the timber
        wedge_position = create_v3(
            position[0],  # X position (cross-section)
            position[1],  # Y position (cross-section)
            0  # At the bottom end
        )
        # Wedge points upward
        length_dir = create_v3(0, 0, 1)
        width_dir = create_v3(1, 0, 0)
    
    # Compute wedge orientation
    wedge_orientation = compute_timber_orientation(length_dir, width_dir)
    wedge_transform = Transform(position=wedge_position, orientation=wedge_orientation)
    
    return Wedge(
        transform=wedge_transform,
        base_width=shape.base_width,
        tip_width=shape.tip_width,
        height=shape.height,
        length=shape.length
    )

