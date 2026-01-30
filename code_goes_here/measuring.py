"""
Measuring and geometric primitives for GiraffeCAD.

Geometric features are things like points, lines, planes, etc. 

Timber features are named geometric features on a timber, e.g. the centerline, the top face, etc. See `TimberFeature` enum in `timber.py` for a list of all timber features.

When marking on timbers, we want to do things like measure from a reference edge, or measure into a face. The types defined in `MarkedTimberFeature` are exactly the features that we care about when marking on timbers.

All measuring functions should follow the following naming convention:

- `mark_*` : functions that take measurements relative to a (LOCAL) feature of a timber and outputs a feature in GLOBAL space

- `???_*` : functions that take feature(s) in GLOBAL space and outputs features in GLOBAL space

- `measure_*` : functions that take a feature in GLOBAL space and outputs a measurement relative to a (LOCAL) feature of a timber
- `scribe_*` : functions that take multiple measurements relative to (LOCAL) features of timbers and outputs a measurement relative to a (LOCAL) feature of a timber


- `???_*` : functions that take feature(s) in GLOBAL space and outputs features in GLOBAL space

OR put more simply: 
- `mark_*` means LOCAL to GLOBAL
- `measure_*` means GLOBAL to LOCAL
- `scribe_*` means LOCAL to LOCAL
- `???_*` means GLOBAL to GLOBAL

In addition we have `measure_by_*` methods which take specific features where as `measure_*` methods tend to be more generic and work with any feature.

Using these functions, we can take measurements relative to features on one timber and mark them onto another timber. Measurements always exist in some context, and together with their context, they become colloqial ways to refer to features as it is easier to understand and work with measurements than it is to work with features directly. So measuring and marking functions are precisely used to convert between these expressions!

For example, if we `my_feature = mark_into_face(mm(10), TimberFace.RIGHT, timberA)` we mean the feature that is a plane 10mm into and parallel with the right face of the timber.
And then if we `measure_onto_face(my_feature, timberB, TimberFace.RIGHT)` we mean find the distance from the feature above to the right face of timberB

Measuring features assumes the features are "comparable". In most cases this means the features are parallel such that measurements can be taken in the orthognal axis. If the features are not "comparable" the functions will assert! 

Some features are signed and oriented. These features follow the following sign conventions:

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
from abc import ABC, abstractmethod
from .moothymoth import *
from .timber import *



# ============================================================================
# Geometric Feature Types
# ============================================================================

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

@dataclass(frozen=True)
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

# TODO rename to LineOnPlane
@dataclass(frozen=True)
class HalfPlane:
    """
    Represents an oriented half-plane with origin in 3D space.
    """
    normal: Direction3D # this is the + direction of any measurements
    point_on_line: V3
    line_direction: Direction3D # MUST be perpendicular to the normal

    def __repr__(self) -> str:
        return f"HalfPlane(normal={self.normal}, point_on_line={self.point_on_line}, line_direction={self.line_direction})"



# ============================================================================
# Measurement Classes
# ============================================================================

@dataclass(frozen=True)
class Measurement(ABC):
    @abstractmethod
    def mark(self) -> Union[UnsignedPlane, Plane, Line, Point, HalfPlane]:
        pass

@dataclass(frozen=True)
class DistanceFromFace(Measurement):
    """
    Represents a distance from a face on a timber with + being AWAY from the face.
    """
    distance: Numeric
    timber: Timber
    face: TimberFace
    

    def mark(self) -> UnsignedPlane:
        """
        Convert the distance from a face to an unsigned plane.
        """
        return UnsignedPlane(self.face.normal, self.timber.get_bottom_position_global() + self.face.normal * self.distance)

@dataclass(frozen=True)
class DistanceFromPointAwayFromFace(Measurement):
    """
    Represents a distance from a point away from a face on a timber with + being AWAY from the face (that is the negative face normal direction is the + axis of the measurement)
    If the point is not supplied, the center of the face is used.
    """
    distance: Numeric
    timber: Timber
    face: TimberFace
    point: Optional[V3] = None
    
    def mark(self) -> Line:
        pass
    
@dataclass(frozen=True)
class DistanceFromLongEdgeOnFace(Measurement):
    """
    Represents a distance from a long edge on a timber with + being AWAY from the edge.
    """
    distance: Numeric
    timber: Timber
    edge: TimberLongEdge
    face: TimberFace
    
    def mark(self) -> Line:
        pass

# ============================================================================
# Helper Functions
# ============================================================================

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

# ============================================================================
# Marking functions
# ============================================================================




def mark_face(timber: Timber, face: TimberFace) -> Plane:
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
        >>> plane = mark_face(timber, TimberFace.RIGHT)
        >>> # plane.normal points in +X direction (outward from RIGHT face)
        >>> # plane.point is at the center of the RIGHT face surface
    """
    # Get the face normal (pointing OUT of the timber)
    face_normal = timber.get_face_direction_global(face)
    
    # Get a point on the face surface (at the center)
    face_point = get_point_on_face_global(face, timber)
    
    return Plane(face_normal, face_point)


# TODO change this to just mark edge
def mark_long_edge(timber: Timber, edge: TimberLongEdge) -> Line:
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
        >>> line = mark_long_edge(timber, TimberLongEdge.RIGHT_FRONT)
        >>> # line.direction points in the timber's length direction
        >>> # line.point is at the RIGHT_FRONT edge, halfway along the length
    """
    
    if edge == TimberLongEdge.CENTERLINE:
        return mark_centerline(timber)
    
    # Map edge enum to the two faces it connects
    edge_to_faces = {
        TimberLongEdge.RIGHT_FRONT: (TimberFace.RIGHT, TimberFace.FRONT),
        TimberLongEdge.FRONT_LEFT: (TimberFace.FRONT, TimberFace.LEFT),
        TimberLongEdge.LEFT_BACK: (TimberFace.LEFT, TimberFace.BACK),
        TimberLongEdge.BACK_RIGHT: (TimberFace.BACK, TimberFace.RIGHT),
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


def mark_centerline(timber: Timber) -> Line:
    """
    Measure the center line of a timber, returning a Line through the timber's center.
    
    The line runs along the timber's length direction (+Z in timber local coordinates),
    positioned at the center of the timber's cross-section.
    
    Args:
        timber: The timber to measure
        
    Returns:
        Line with direction pointing in the timber's +Z direction and point at the centerline
        
    Example:
        >>> line = mark_centerline(timber)
        >>> # line.direction points in the timber's length direction
        >>> # line.point is at the center of the timber (halfway along length, centered in cross-section)
    """
    # Get the timber's length direction
    length_direction = timber.get_length_direction_global()
    
    # Get the center position (at mid-length)
    center_position = timber.get_bottom_position_global() + length_direction * timber.length / 2
    
    return Line(length_direction, center_position)

def mark_edge_on_face(timber: Timber, edge: TimberLongEdge, face: TimberFace) -> HalfPlane:
    # TODO
    pass

def mark_position_on_centerline_from_bottom(timber: Timber, distance: Numeric) -> Point:
    """
    Mark a position at a specific point along the timber's centerline, measured from the bottom.
    
    Args:
        timber: The timber to mark on
        distance: Distance along the timber's length direction from the bottom position
        
    Returns:
        Point on the timber's centerline at the specified distance from bottom
    """
    position = timber.get_bottom_position_global() + timber.get_length_direction_global() * distance
    return Point(position)


def mark_position_on_centerline_from_top(timber: Timber, distance: Numeric) -> Point:
    """
    Mark a position at a specific point along the timber's centerline, measured from the top.
    
    Args:
        timber: The timber to mark on
        distance: Distance along the timber's length direction from the top position
        
    Returns:
        Point on the timber's centerline at the specified distance from top
    """
    position = timber.get_bottom_position_global() + timber.get_length_direction_global() * (timber.length - distance)
    return Point(position)


def mark_bottom_center_position(timber: Timber) -> Point:
    """
    Mark the position of the center of the bottom cross-section of the timber.
    
    Args:
        timber: The timber to mark on
        
    Returns:
        Point at the center of the bottom cross-section
    """
    return Point(timber.get_bottom_position_global())


def mark_top_center_position(timber: Timber) -> Point:
    """
    Mark the position of the center of the top cross-section of the timber.
    
    Args:
        timber: The timber to mark on
        
    Returns:
        Point at the center of the top cross-section
    """
    position = timber.get_bottom_position_global() + timber.get_length_direction_global() * timber.length
    return Point(position)

def mark_into_face(distance: Numeric, face: TimberFace, timber: Timber) -> UnsignedPlane:
    """
    Measure a distance from a face on a timber.
    """

    # First pick any point on the face
    point_on_face = get_point_on_face_global(face, timber)

    # Measure INTO the face
    point_on_plane = point_on_face - timber.get_face_direction_global(face) * distance

    return UnsignedPlane(timber.get_face_direction_global(face), point_on_plane)


def measure_onto_face(feature: Union[UnsignedPlane, Plane, Line, Point, HalfPlane], timber: Timber, face: TimberFace) -> Numeric:
    """
    Mark a feature from a face on a timber.
    
    Returns the distance from the face to the feature, measured INTO the timber.
    Positive means the feature is inside the timber (deeper than the face surface).
    Negative means the feature is outside the timber (shallower than the face surface).
    
    This is the inverse of mark_into_face:
    If feature = mark_into_face(d, face, timber), then measure_onto_face(feature, timber, face) = d
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
    # Get a reference point on the face surface
    face_point_global = get_point_on_face_global(face, timber)
    
    # Get the face normal (pointing OUT of the timber)
    face_direction_global = timber.get_face_direction_global(face)
    
    # Calculate signed distance: how far from the face is the point?
    # Positive if point is in the direction opposite to face_direction (inside timber)
    # Negative if point is in the direction of face_direction (outside timber)
    distance = (face_direction_global.T * (face_point_global - feature_point))[0, 0]
    
    return distance


def measure_by_intersecting_plane_onto_long_edge(plane: Union[UnsignedPlane, Plane], timber: Timber, edge: TimberLongEdge, end: TimberReferenceEnd) -> Numeric:
    """
    Intersect a plane with a long edge of a timber.

    Computes the true geometric intersection between the plane and the edge line,
    returning the signed distance from the specified end to the intersection point.

    Args:
        plane: the plane to intersect with
        timber: the timber whose edge we're intersecting
        edge: the edge to intersect with
        end: the end of the timber to measure from

    Returns the distance from timber_end to where the plane intersects the timber's long edge.
    Positive distance means the intersection is in the direction away from the end (into the timber).
    """
    
    # Get the edge line
    edge_line = mark_long_edge(timber, edge)
    
    # Get the end position on the edge
    # edge_line.point is at mid-length, so we need to offset by half the length
    if end == TimberReferenceEnd.TOP:
        end_position = edge_line.point + edge_line.direction * (timber.length / 2)
        # Direction from end into timber is negative length direction
        into_timber_direction = -timber.get_length_direction_global()
    else:  # BOTTOM
        end_position = edge_line.point - edge_line.direction * (timber.length / 2)
        # Direction from end into timber is positive length direction
        into_timber_direction = timber.get_length_direction_global()
    
    # Compute line-plane intersection using the standard formula
    # Line: P = end_position + t * into_timber_direction
    # Plane: plane.normal · (P - plane.point) = 0
    # Solving for t: t = plane.normal · (plane.point - end_position) / (plane.normal · into_timber_direction)
    
    numerator = (plane.normal.T * (plane.point - end_position))[0, 0]
    denominator = (plane.normal.T * into_timber_direction)[0, 0]
    
    # If denominator is zero, the line is parallel to the plane (no intersection)
    if zero_test(denominator):
        # Line is parallel to plane - this shouldn't happen in normal usage
        # Return None or raise an error to indicate no intersection
        raise ValueError(f"Edge is parallel to plane - no intersection exists")
    
    # Distance along the line from end_position to intersection
    signed_distance = numerator / denominator
    
    return signed_distance

def measure_by_finding_closest_point_on_line_to_edge(line: Line, timber: Timber, edge: TimberLongEdge, end: TimberReferenceEnd) -> Numeric:
    """
    Find the closest point between a line and a timber edge.

    This computes the closest point on the timber edge to the given line, which is useful
    for finding where two centerlines come closest to each other (even if they don't intersect).

    Args:
        line: The line feature to measure from
        timber: The timber whose edge we're measuring to
        edge: The edge to measure to
        end: Which end of the timber to measure from

    Returns:
        The signed distance along the timber's length direction from the specified end to the closest point.
        Positive means the closest point is in the direction of the timber's length_direction (toward TOP).
        Negative means the closest point is opposite the timber's length_direction (toward BOTTOM).
        
        Asserts if lines are parallel
    """

    
    
    # Get the edge line
    edge_line = mark_long_edge(timber, edge)

    if are_vectors_parallel(line.direction, edge_line.direction):
        raise ValueError(f"Lines are parallel - no intersection exists")
    
    # Get the end position on the edge
    # edge_line.point is at mid-length, so we need to offset by half the length
    # edge_line.direction is the timber's length direction (points from BOTTOM to TOP)
    if end == TimberReferenceEnd.TOP:
        edge_end_position = edge_line.point + edge_line.direction * (timber.length / 2)
    else:  # BOTTOM
        edge_end_position = edge_line.point - edge_line.direction * (timber.length / 2)
    
    # Solve for closest points on two 3D lines using the standard formula
    # Line 1 (given line): line.point + s * line.direction
    # Line 2 (edge): edge_end_position + t * edge_line.direction
    # We need to find s and t such that the connecting vector is perpendicular to both directions
    
    w = line.point - edge_end_position  # Vector between starting points
    
    a = (line.direction.T * line.direction)[0, 0]  # Should be 1 for normalized directions
    b = (line.direction.T * edge_line.direction)[0, 0]
    c = (edge_line.direction.T * edge_line.direction)[0, 0]  # Should be 1 for normalized directions
    d = (w.T * line.direction)[0, 0]
    e = (w.T * edge_line.direction)[0, 0]
    
    denominator = a * c - b * b
    
    # Check if lines are parallel (denominator near zero)
    if zero_test(denominator):
        # Lines are parallel - any perpendicular works, use starting point (distance = 0)
        return Rational(0)
    
    # Calculate parameter for closest point on the edge
    # This gives us the distance along edge_line.direction from edge_end_position
    # edge_line.direction is the timber's length_direction (from BOTTOM to TOP)
    # So t is the signed distance along the timber's length direction from the specified end
    t = (a * e - b * d) / denominator
    
    return t

def measure_onto_centerline(feature: Union[UnsignedPlane, Plane, Line, Point, HalfPlane], timber: Timber) -> Numeric:
    """
    Measure a feature onto the centerline of a timber.

    Returns the distance from the bottom of the timber to the intersection/closest point.
    
    Args:
        feature: The feature to measure (Plane, Line, Point, etc.)
        timber: The timber whose centerline we're measuring to
        
    Returns:
        Distance from the BOTTOM end of the timber to where the feature intersects/is closest to the centerline.
        Positive means into the timber from the bottom.
    """
    if isinstance(feature, UnsignedPlane) or isinstance(feature, Plane):
        return measure_by_intersecting_plane_onto_long_edge(feature, timber, TimberLongEdge.CENTERLINE, TimberReferenceEnd.BOTTOM)
    elif isinstance(feature, Line):
        return measure_by_finding_closest_point_on_line_to_edge(feature, timber, TimberLongEdge.CENTERLINE, TimberReferenceEnd.BOTTOM)

    assert False, f"Not implemented for feature type {type(feature)}"

# TODO delete me or move to timber_shavings.py
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
    distance = measure_onto_face(target_face_plane, reference_timber, reference_timber_face)
    
    return distance