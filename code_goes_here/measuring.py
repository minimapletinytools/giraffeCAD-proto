"""
Measuring and geometric primitives for GiraffeCAD.

Geometric features are things like points, lines, planes, etc. 

Timber features are named geometric features on a timber, e.g. the centerline, the top face, etc. See `TimberFeature` enum in `timber.py` for a list of all timber features.

When marking on timbers, we want to do things like measure from a reference edge, or measure into a face. The types defined in `MarkedTimberFeature` are exactly the features that we care about when marking on timbers.

All measuring functions should follow the following naming convention:

- measure_* : functions that take measurements relative to a (LOCAL) feature of a timber and outputs a feature in GLOBAL space
- mark_* : functions that take a feature in GLOBAL space and outputs a measurement relative to a (LOCAL) feature of a timber
- scribe_* : functions that take multiple measurements relative to (LOCAL) features of timbers and outputs a measurement relative to a (LOCAL) feature of a timber

OR put more simply: 
- measure_* means LOCAL to GLOBAL
- mark_* means GLOBAL to LOCAL
- scribe_* means LOCAL to LOCAL

Using these functions, we can take measurements relative to features on one timber and mark them onto another timber. Measurements always exist in some context, and together with their context, they become colloqial ways to refer to features as it is easier to understand and work with measurements than it is to work with features directly. So measuring and marking functions are precisely used to convert between these expressions!

For example, if we `my_feature = measure_into_face(mm(10), TimberFace.RIGHT, timberA)` we mean the feature that is a plane 10mm into and parallel with the right face of the timber.
And then if we `mark_onto_face(my_feature, TimberFace.RIGHT, timberB)` we mean find the distance from the feature above to the right face of timberB

Marking features assumes the features are "comparable", which in most cases means the features are parallel such that measurements can be taken in the orthognal axis. If the features are not "comparable" the functions will assert! 

Some features are signed and oriented. Timber features follow the following sign conventions:

- markings from timber faces are along the normal pointing INTO the timber i.e. positive is into the face
- markings from timber halfplanes aligning with a timber edge 
    - positive X is towards the face 
    - for long faces postivie Y is (usually) in the direction of the timber, sometimes it's the opposite so watch out!
    - for end faces, use RHS rule with +Z ponting in the direction of the end
- markings from timber corners
    - TODO but also we never do this so who cares

Features are also located (i.e. lines and planes have an "origin" point). This information is currently not used in any of these functions. Timber Features follow the following location conventions:

- timber faces are located at the center of the face surface
- timber edges are located on the bottom face of the timber

A `Point` is just a `V3` and sometimes you might find yourself measuring a `Point` and simply using its contained `V3` directly! This is OK. We still wrap it in a `Point` to help ensure encapsulation of measuring and marking functions. In particular, some of these functions can take many different types of features and we want to be intentional about passing `Points` into these functions!

Finally, note that the feature classes in this module should NOT be used for anything besides measuring and marking!!
"""

from dataclasses import dataclass
from typing import Union
from .moothymoth import *
from .timber import *
from .timber_shavings import get_point_on_face_global, project_point_onto_face_global

# Type alias for all measurable geometric features on timbers
MarkedTimberFeature = Union['Point', 'Line', 'Plane', 'UnsignedPlane', 'HalfPlane']

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


def measure_face(timber: Timber, face: TimberFace) -> Plane:
    """
    Measure a face on a timber, returning a Plane centered on the face pointing outward.
    
    The plane's normal points OUT of the timber (away from the timber's interior),
    and the plane's point is positioned at the center of the face surface.
    
    Args:
        timber: The timber to measure
        face: The face to measure
        
    Returns:
        Plane with normal pointing outward from the face and point at the face center
        
    Example:
        >>> plane = measure_face(timber, TimberFace.RIGHT)
        >>> # plane.normal points in +X direction (outward from RIGHT face)
        >>> # plane.point is at the center of the RIGHT face surface
    """
    # Get the face normal (pointing OUT of the timber)
    face_normal = timber.get_face_direction_global(face)
    
    # Get a point on the face surface (at the center)
    face_point = get_point_on_face_global(face, timber)
    
    return Plane(face_normal, face_point)


def measure_long_edge(timber: Timber, edge: TimberLongEdge) -> Line:
    """
    Measure a long edge on a timber, returning a Line centered on the edge pointing in +Z.
    
    The line runs along the timber's length direction (+Z in timber local coordinates),
    positioned at the specified edge (intersection of two long faces).
    
    Args:
        timber: The timber to measure
        edge: The long edge to measure
        
    Returns:
        Line with direction pointing in the timber's +Z direction and point at the edge center
        
    Example:
        >>> line = measure_long_edge(timber, TimberLongEdge.RIGHT_FRONT)
        >>> # line.direction points in the timber's length direction
        >>> # line.point is at the RIGHT_FRONT edge, halfway along the length
    """
    # Map edge enum to the two faces it connects
    edge_to_faces = {
        TimberLongEdge.RIGHT_FRONT: (TimberFace.RIGHT, TimberFace.FRONT),
        TimberLongEdge.FRONT_LEFT: (TimberFace.FRONT, TimberFace.LEFT),
        TimberLongEdge.LEFT_BACK: (TimberFace.LEFT, TimberFace.BACK),
        TimberLongEdge.BACK_RIGHT: (TimberFace.BACK, TimberFace.RIGHT),
        TimberLongEdge.FRONT_RIGHT: (TimberFace.FRONT, TimberFace.RIGHT),
        TimberLongEdge.RIGHT_BACK: (TimberFace.RIGHT, TimberFace.BACK),
        TimberLongEdge.BACK_LEFT: (TimberFace.BACK, TimberFace.LEFT),
        TimberLongEdge.LEFT_FRONT: (TimberFace.LEFT, TimberFace.FRONT),
    }
    
    if edge not in edge_to_faces:
        raise ValueError(f"Unknown edge: {edge}")
    
    face1, face2 = edge_to_faces[edge]
    
    # Get the timber's length direction (always +Z in local coords, the direction from BOTTOM to TOP)
    length_direction = timber.get_length_direction_global()
    
    # Calculate edge position by finding the intersection of the two faces
    # The edge is at the corner where both face normals point away from
    face1_normal = timber.get_face_direction_global(face1)
    face2_normal = timber.get_face_direction_global(face2)
    
    # Get the timber's bottom center position
    bottom_center = timber.get_bottom_position_global()
    
    # Calculate offset from center to edge
    # Edge is at +/- (size/2) in the directions of both face normals
    face1_offset = face1_normal * timber.get_size_in_face_normal_axis(face1) / 2
    face2_offset = face2_normal * timber.get_size_in_face_normal_axis(face2) / 2
    
    # Edge position is at the corner (both offsets applied)
    edge_position = bottom_center + face1_offset + face2_offset
    
    return Line(length_direction, edge_position)


def measure_center_line(timber: Timber) -> Line:
    """
    Measure the center line of a timber, returning a Line through the timber's center.
    
    The line runs along the timber's length direction (+Z in timber local coordinates),
    positioned at the center of the timber's cross-section.
    
    Args:
        timber: The timber to measure
        
    Returns:
        Line with direction pointing in the timber's +Z direction and point at the centerline
        
    Example:
        >>> line = measure_center_line(timber)
        >>> # line.direction points in the timber's length direction
        >>> # line.point is at the center of the timber (halfway along length, centered in cross-section)
    """
    # Get the timber's length direction
    length_direction = timber.get_length_direction_global()
    
    # Get the center position (at mid-length)
    center_position = timber.get_bottom_position_global() + length_direction * timber.length / 2
    
    return Line(length_direction, center_position)

def measure_into_face(distance: Numeric, face: TimberFace, timber: Timber) -> UnsignedPlane:
    """
    Measure a distance from a face on a timber.
    """

    # First pick any point on the face
    point_on_face = get_point_on_face_global(face, timber)

    # Measure INTO the face
    point_on_plane = point_on_face - timber.get_face_direction_global(face) * distance

    return UnsignedPlane(timber.get_face_direction_global(face), point_on_plane)


def mark_onto_face(feature: Union[UnsignedPlane, Plane, Line, Point, HalfPlane], face: TimberFace, timber: Timber) -> Numeric:
    """
    Mark a feature from a face on a timber.
    
    Returns the distance from the face to the feature, measured INTO the timber.
    Positive means the feature is inside the timber (deeper than the face surface).
    Negative means the feature is outside the timber (shallower than the face surface).
    
    This is the inverse of measure_into_face:
    If feature = measure_into_face(d, face, timber), then mark_onto_face(feature, face, timber) = d
    """

    # TODO assert that UnsignedPlane/Plane/HalfPlane/Line are parallel to the face
    if isinstance(feature, UnsignedPlane) or isinstance(feature, Plane) or isinstance(feature, HalfPlane):
        assert are_vectors_parallel(feature.normal, timber.get_face_direction_global(face)), \
            f"Feature must be parallel to the face. Feature {feature} is not parallel to face {face} on timber {timber}"
    elif isinstance(feature, Line):
        assert are_vectors_perpendicular(feature.direction, timber.get_face_direction_global(face)), \
            f"Feature must be parallel to the face. Feature {feature} is not parallel to face {face} on timber {timber}"

    # Pick a point on the feature
    feature_point = get_point_on_feature(feature, timber)

    # Project the feature point onto the face to get the signed distance
    distance = project_point_onto_face_global(feature_point, face, timber)
    
    return distance


def gauge_distance_between_faces(reference_timber: Timber, reference_timber_face: TimberFace, target_timber: Timber, target_timber_face: TimberFace) -> Numeric:
    """
    Gauge the distance between two faces on two timbers.
    
    Measures the signed distance from the reference face to the target face along the reference face's normal.
    Positive distance means the target face is in the direction INTO the reference timber (along the inward normal).
    Negative distance means the target face is in the opposite direction (away from the reference timber).
    
    The two faces must be parallel or antiparallel (facing each other or facing the same direction).
    
    Args:
        reference_timber: The timber with the reference face
        reference_timber_face: The face on the reference timber to measure from
        target_timber: The timber with the target face
        target_timber_face: The face on the target timber to measure to
        
    Returns:
        Signed distance from reference face to target face (positive = into reference timber)
        
    Example:
        >>> # Two face-aligned timbers with a 5" gap between their FRONT faces
        >>> distance = gauge_distance_between_faces(timber1, TimberFace.FRONT, timber2, TimberFace.BACK)
    """
    from code_goes_here.construction import are_vectors_parallel
    
    # Get face normals
    reference_face_normal = reference_timber.get_face_direction_global(reference_timber_face)
    target_face_normal = target_timber.get_face_direction_global(target_timber_face)
    
    # Assert that the faces are parallel (or antiparallel)
    assert are_vectors_parallel(reference_face_normal, target_face_normal), \
        f"Faces must be parallel. Reference face {reference_timber_face.name} on {reference_timber.name} " \
        f"has normal {reference_face_normal.T}, target face {target_timber_face.name} on {target_timber.name} " \
        f"has normal {target_face_normal.T}"
    
    # Create a plane at the target face
    target_face_plane = Plane(target_face_normal, get_point_on_face_global(target_timber_face, target_timber))
    
    # Measure the distance from the reference face to the target face plane
    distance = mark_onto_face(target_face_plane, reference_timber_face, reference_timber)
    
    return distance