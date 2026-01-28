"""
Random timber-related helper functions.

Contains utility functions for working with timbers that don't fit into a more specific category.
"""

from .moothymoth import *
from .timber import *


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
