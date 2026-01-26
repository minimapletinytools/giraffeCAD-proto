"""
Measuring and geometric primitives for GiraffeCAD.

Measuring functions follows the following pattern:

measure(measurement, feature, timber) -> feature in global space
mark(golbal feature, timber) -> measurement from some local feature on the timber

features on timbers follow the following sign conventions:

- measurements from timber faces are along the normal pointing INTO the timber i.e. positive is into the face
- measurements from timber halfplanes aligning with a timber edge 
    - positive X is towards the face 
    - for long faces postivie Y is (usually) in the direction of the timber, sometimes it's the opposite so watch out!
    - for end faces, use RHS rule with +Z ponting in the direction of the end
- measurements from timber corners
    - TODO but also we never do this so who cares

Note the Measuring feature classes are NOT used for CSG operations, they are only used for measurements and geometric calculations. 
"""

from dataclasses import dataclass
from typing import Union
from .moothymoth import *
from .timber import *

@dataclass(frozen=True)
class Point:
    """
    Represents a point in 3D space.
    """
    position: V3

    def __repr__(self) -> str:
        return f"Point(position={self.position})"


@dataclass(frozen=True)
class Line:
    """
    Represents an oriented line with origin in 3D space.
    """
    direction: Direction3D
    point: V3

    def __repr__(self) -> str:
        return f"Line(direction={self.direction}, point={self.point})"


@dataclass(frozen=True)
class Plane:
    """
    Represents an oriented plane with origin in 3D space.
    """
    normal: Direction3D
    point: V3

    def __repr__(self) -> str:
        return f"Plane(normal={self.normal}, point={self.point})"

    @staticmethod
    def from_transform_and_direction(transform: Transform, direction: Direction3D) -> 'Plane':
        """
        Create a plane from a transform and a direction.
        
        Args:
            transform: Transform defining the position and orientation
            direction: Direction in the transform's local coordinate system
            
        Returns:
            Plane with normal in global coordinates and point at transform position
        """
        return Plane(transform.orientation.matrix * direction, transform.position)

class UnsignedPlane(Plane):
    """
    Same as Plane but the sign on the normal should be ignored.
    """
    normal: Direction3D
    point: V3

    def __repr__(self) -> str:
        return f"UnsignedPlane(normal={self.normal}, point={self.point})"


    @staticmethod
    def from_transform_and_direction(transform: Transform, direction: Direction3D) -> 'UnsignedPlane':
        """
        Create an unsigned plane from a transform and a direction.
        
        Args:
            transform: Transform defining the position and orientation
            direction: Direction in the transform's local coordinate system
            
        Returns:
            UnsignedPlane with normal in global coordinates and point at transform position
        """
        return UnsignedPlane(transform.orientation.matrix * direction, transform.position)

@dataclass(frozen=True)
class HalfPlane:
    """
    Represents an oriented half-plane with origin in 3D space.
    """
    normal: Direction3D
    point_on_line: V3
    line_direction: Direction3D # MUST be perpendicular to the normal

    def __repr__(self) -> str:
        return f"HalfPlane(normal={self.normal}, point_on_line={self.point_on_line}, line_direction={self.line_direction})"


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


def project_point_onto_face_global(point: V3, face: TimberFace, timber: Timber) -> Numeric:
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
    face_point = get_point_on_face_global(face, timber)
    
    # Get the face normal (pointing OUT of the timber)
    face_direction = timber.get_face_direction_global(face)
    
    # Calculate signed distance: how far from the face is the point?
    # Positive if point is in the direction opposite to face_direction (inside timber)
    # Negative if point is in the direction of face_direction (outside timber)
    distance = (face_direction.T * (face_point - point))[0, 0]
    
    return distance

def get_point_on_feature(feature: Union[UnsignedPlane, Plane, Line, Point, HalfPlane], timber: Timber) -> V3:
    """
    Get a point on a feature.
    """

    if isinstance(feature, HalfPlane):
        return feature.point_on_line
    elif isinstance(feature, UnsignedPlane):
        return feature.point
    elif isinstance(feature, Plane):
        return feature.point
    elif isinstance(feature, Line):
        return feature.point
    elif isinstance(feature, Point):
        return feature.position

    raise ValueError(f"Unsupported feature type: {type(feature)}")

def measure_from_face(distance: Numeric, face: TimberFace, timber: Timber) -> UnsignedPlane:
    """
    Measure a distance from a face on a timber.
    """

    # First pick any point on the face
    point_on_face = get_point_on_face_global(face, timber)

    # Measure INTO the face
    point_on_plane = point_on_face - timber.get_face_direction_global(face) * distance

    return UnsignedPlane(timber.get_face_direction_global(face), point_on_plane)

def mark_from_face(feature: Union[UnsignedPlane, Plane, Line, Point, HalfPlane], face: TimberFace, timber: Timber) -> Numeric:
    """
    Mark a feature from a face on a timber.
    
    Returns the distance from the face to the feature, measured INTO the timber.
    Positive means the feature is inside the timber (deeper than the face surface).
    Negative means the feature is outside the timber (shallower than the face surface).
    
    This is the inverse of measure_from_face:
    If feature = measure_from_face(d, face, timber), then mark_from_face(feature, face, timber) = d
    """

    # Pick a point on the feature
    feature_point = get_point_on_feature(feature, timber)

    # Project the feature point onto the face to get the signed distance
    distance = project_point_onto_face_global(feature_point, face, timber)
    
    return distance