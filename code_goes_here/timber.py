"""
GiraffeCAD - Timber types, enums, constants, and core classes
Contains all core data structures and type definitions for the timber framing system
"""

from sympy import Matrix, Abs, Rational, Integer, Expr, sqrt, simplify
from .moothymoth import (
    Orientation,
    Transform,
    EPSILON_GENERIC,
    zero_test,
    are_vectors_parallel,
    are_vectors_perpendicular,
    V2,
    V3,
    Direction3D,
    Numeric,
    create_v2,
    create_v3,
    normalize_vector,
    cross_product,
    vector_magnitude
)
from .footprint import Footprint
from .meowmeowcsg import MeowMeowCSG, HalfPlane, Prism, Cylinder, Union as CSGUnion, Difference as CSGDifference
from enum import Enum
from typing import List, Optional, Tuple, Union, TYPE_CHECKING, Dict
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# ============================================================================
# Constants
# ============================================================================

# Epsilon constants are now imported from moothymoth module

# Thresholds for geometric decisions
OFFSET_TEST_POINT = Rational(1, 1000)  # Small offset (0.001) for testing inward direction on footprint

# ============================================================================
# Enums and Basic Types
# ============================================================================


# TODO move to footprint?
class FootprintLocation(Enum):
    INSIDE = 1
    CENTER = 2
    OUTSIDE = 3

class TimberFace(Enum):
    TOP = 1 # the face vector with normal vector in the +Z axis direction
    BOTTOM = 2 # the face vector with normal vector in the -Z axis direction
    RIGHT = 3 # the face vector with normal vector in the +X axis direction
    FRONT = 4 # the face vector with normal vector in the +Y axis direction
    LEFT = 5 # the face vector with normal vector in the -X axis direction
    BACK = 6 # the face vector with normal vector in the -Y axis direction
    
    def get_direction(self) -> Direction3D:
        """Get the direction vector for this face in world coordinates."""
        if self == TimberFace.TOP:
            return create_v3(0, 0, 1)
        elif self == TimberFace.BOTTOM:
            return create_v3(0, 0, -1)
        elif self == TimberFace.RIGHT:
            return create_v3(1, 0, 0)
        elif self == TimberFace.LEFT:
            return create_v3(-1, 0, 0)
        elif self == TimberFace.FRONT:
            return create_v3(0, 1, 0)
        else:  # BACK
            return create_v3(0, -1, 0)
    
    def is_perpendicular(self, other: 'TimberFace') -> bool:
        """
        Check if two faces are perpendicular to each other.
        
        Perpendicular face pairs (orthogonal axes):
        - X-axis faces (RIGHT, LEFT) <-> Y-axis faces (FRONT, BACK)
        - X-axis faces (RIGHT, LEFT) <-> Z-axis faces (TOP, BOTTOM)
        - Y-axis faces (FRONT, BACK) <-> Z-axis faces (TOP, BOTTOM)
        """
        # Define axis groups
        x_faces = {TimberFace.RIGHT, TimberFace.LEFT}
        y_faces = {TimberFace.FRONT, TimberFace.BACK}
        z_faces = {TimberFace.TOP, TimberFace.BOTTOM}
        
        # Two faces are perpendicular if they are on different axes
        self_in_x = self in x_faces
        self_in_y = self in y_faces
        self_in_z = self in z_faces
        
        other_in_x = other in x_faces
        other_in_y = other in y_faces
        other_in_z = other in z_faces
        
        # Perpendicular if on different axes
        return (self_in_x and (other_in_y or other_in_z)) or \
               (self_in_y and (other_in_x or other_in_z)) or \
               (self_in_z and (other_in_x or other_in_y))
    
    def get_opposite_face(self) -> 'TimberFace':
        """
        Get the opposite face (the face on the opposite side of the timber).
        
        Opposite pairs:
        - TOP <-> BOTTOM
        - RIGHT <-> LEFT
        - FRONT <-> BACK
        """
        if self == TimberFace.TOP:
            return TimberFace.BOTTOM
        elif self == TimberFace.BOTTOM:
            return TimberFace.TOP
        elif self == TimberFace.RIGHT:
            return TimberFace.LEFT
        elif self == TimberFace.LEFT:
            return TimberFace.RIGHT
        elif self == TimberFace.FRONT:
            return TimberFace.BACK
        else:  # BACK
            return TimberFace.FRONT

class TimberReferenceEnd(Enum):
    TOP = 1
    BOTTOM = 2
    
    def to_timber_face(self) -> TimberFace:
        """Convert TimberReferenceEnd to TimberFace."""
        return TimberFace(self.value)

class TimberReferenceLongFace(Enum):
    RIGHT = 3
    FRONT = 4
    LEFT = 5
    BACK = 6
    
    def to_timber_face(self) -> TimberFace:
        """Convert TimberReferenceLongFace to TimberFace."""
        return TimberFace(self.value)
    
    def is_perpendicular(self, other: 'TimberReferenceLongFace') -> bool:
        """
        Check if two long faces are perpendicular to each other.
        
        Perpendicular face pairs:
        - RIGHT <-> FRONT, RIGHT <-> BACK
        - LEFT <-> FRONT, LEFT <-> BACK
        """
        return self.to_timber_face().is_perpendicular(other.to_timber_face())

    def rotate_right(self) -> 'TimberReferenceLongFace':
        """Rotate the long face right (90 degrees clockwise)."""
        return TimberReferenceLongFace(self.value + 1 % 4)
    
    def rotate_left(self) -> 'TimberReferenceLongFace':
        """Rotate the long face left (90 degrees counter-clockwise)."""
        return TimberReferenceLongFace(self.value - 1 % 4)

class TimberReferenceLongEdge(Enum):
    RIGHT_FRONT = 7
    FRONT_LEFT = 8
    LEFT_BACK = 9
    BACK_RIGHT = 10
    FRONT_RIGHT = 11
    RIGHT_BACK = 12
    BACK_LEFT = 13
    LEFT_FRONT = 14

class StickoutReference(Enum):
    """
    Defines how stickout is measured relative to timber connection points.
    
    CENTER_LINE: Stickout measured from centerline of the timber (default)
        joined timber
        | |
        |||===== created timber
        | |
    
    INSIDE: Stickout measured from inside face of the timber
        joined timber
        | |
        | |===== created timber
        | |
    
    OUTSIDE: Stickout measured from outside face of the timber
        joined timber
        | |
        |====== created timber
        | |
    """
    CENTER_LINE = 1
    INSIDE = 2
    OUTSIDE = 3

# ============================================================================
# Joint Construction Data Structures
# ============================================================================

@dataclass(frozen=True)
class DistanceFromFace:
    face: TimberFace
    distance: Numeric
@dataclass(frozen=True)
class DistanceFromLongFace:
    face: TimberReferenceLongFace
    distance: Numeric
@dataclass(frozen=True)
class DistanceFromEnd:
    end: TimberReferenceEnd
    distance: Numeric
@dataclass(frozen=True)
class DistanceFromLongEdge:
    """
    Position defined by distances from two adjacent long faces.
    This identifies a point on the cross-section by measuring from two perpendicular long faces.
    The 2 faces MUST be perpendicular to each other.
    """
    face1: DistanceFromLongFace
    face2: DistanceFromLongFace

    def get_long_edge(self) -> TimberReferenceLongEdge:
        """
        Get the long edge from the two faces.
        """
        f1 = self.face1.face
        f2 = self.face2.face
        
        if f1 == TimberReferenceLongFace.RIGHT and f2 == TimberReferenceLongFace.FRONT:
            return TimberReferenceLongEdge.RIGHT_FRONT
        elif f1 == TimberReferenceLongFace.FRONT and f2 == TimberReferenceLongFace.LEFT:
            return TimberReferenceLongEdge.FRONT_LEFT
        elif f1 == TimberReferenceLongFace.LEFT and f2 == TimberReferenceLongFace.BACK:
            return TimberReferenceLongEdge.LEFT_BACK
        elif f1 == TimberReferenceLongFace.BACK and f2 == TimberReferenceLongFace.RIGHT:
            return TimberReferenceLongEdge.BACK_RIGHT
        elif f1 == TimberReferenceLongFace.FRONT and f2 == TimberReferenceLongFace.RIGHT:
            return TimberReferenceLongEdge.FRONT_RIGHT
        elif f1 == TimberReferenceLongFace.RIGHT and f2 == TimberReferenceLongFace.BACK:
            return TimberReferenceLongEdge.RIGHT_BACK
        elif f1 == TimberReferenceLongFace.BACK and f2 == TimberReferenceLongFace.LEFT:
            return TimberReferenceLongEdge.BACK_LEFT
        elif f1 == TimberReferenceLongFace.LEFT and f2 == TimberReferenceLongFace.FRONT:
            return TimberReferenceLongEdge.LEFT_FRONT
        else:
            raise ValueError(f"Invalid faces: {f1} and {f2}")
    
    def is_valid(self) -> bool:
        """
        Check if the two faces are perpendicular to each other.
        """
        return self.face1.face.is_perpendicular(self.face2.face)

    

# TODO write better comments or give this a better name. wtf is this?
@dataclass(frozen=True)
class FaceAlignedJoinedTimberOffset:
    reference_face: TimberFace
    centerline_offset: Optional[Numeric]
    face_offset: Optional[Numeric]


# TODO this is really only needed for JoinTimbers so move it near that function
# TODO rename to ButtStickout or something like that...
@dataclass(frozen=True)
class Stickout:
    """
    Defines how much a timber extends beyond connection points.
    
    For symmetric stickout, set stickout1 = stickout2.
    For asymmetric stickout, use different values.
    Default is no stickout (0, 0) from CENTER_LINE.
    
    StickoutReference modes:
    
    CENTER_LINE: Stickout measured from centerline of the joined timber
        joined timber
        | |
        |||===== created timber
        | |
    
    INSIDE: Stickout measured from inside face of the joined timber
        joined timber
        | |
        | |===== created timber
        | |
    
    OUTSIDE: Stickout measured from outside face of the joined timber
        joined timber
        | |
        |====== created timber
        | |
    
    Args:
        stickout1: Extension beyond the first connection point (default: 0)
        stickout2: Extension beyond the second connection point (default: 0)
        stickoutReference1: How stickout1 is measured (default: CENTER_LINE)
        stickoutReference2: How stickout2 is measured (default: CENTER_LINE)
    
    Examples:
        # Symmetric stickout from centerline
        s = Stickout.symmetric(0.2)  # Both sides extend 0.2m from centerline
        
        # No stickout
        s = Stickout.nostickout()  # Both sides are 0
        
        # Asymmetric stickout
        s = Stickout(0.1, 0.4)  # Left extends 0.1m, right extends 0.4m from centerline
        
        # Stickout from outside faces
        s = Stickout(0.1, 0.2, StickoutReference.OUTSIDE, StickoutReference.OUTSIDE)
    """
    stickout1: Numeric = 0
    stickout2: Numeric = 0
    stickoutReference1: 'StickoutReference' = None
    stickoutReference2: 'StickoutReference' = None
    
    def __post_init__(self):
        """Set default stickout references if not provided."""
        if self.stickoutReference1 is None:
            object.__setattr__(self, 'stickoutReference1', StickoutReference.CENTER_LINE)
        if self.stickoutReference2 is None:
            object.__setattr__(self, 'stickoutReference2', StickoutReference.CENTER_LINE)
    
    @classmethod
    def symmetric(cls, value: Numeric, reference: 'StickoutReference' = None) -> 'Stickout':
        """
        Create a symmetric stickout where both sides extend by the same amount.
        
        Args:
            value: The stickout distance for both sides
            reference: How stickout is measured (default: CENTER_LINE)
            
        Returns:
            Stickout instance with stickout1 = stickout2 = value
        """
        if reference is None:
            reference = StickoutReference.CENTER_LINE
        return cls(value, value, reference, reference)
    
    @classmethod
    def nostickout(cls) -> 'Stickout':
        """
        Create a stickout with no extension on either side.
        
        Returns:
            Stickout instance with stickout1 = stickout2 = 0
        """
        return cls(0, 0)

# ============================================================================
# Backward Compatibility Aliases
# ============================================================================
# These functions are now defined in moothymoth.py
# Keep old names as aliases for backward compatibility

create_v2 = create_v2  # Alias for backward compatibility
create_v3 = create_v3  # Alias for backward compatibility

# ============================================================================
# Core Classes
# ============================================================================


def _compute_timber_orientation(length_direction: Direction3D, width_direction: Direction3D) -> Orientation:
    """Compute the orientation matrix from length and width directions
    
    Args:
        length_direction: Direction vector for the length axis as 3D vector, the +length direction is the +Z direction
        width_direction: Direction vector for the width axis as 3D vector, the +width direction is the +X direction
        
    Returns:
        Orientation object representing the timber's orientation in 3D space
    """
    # Normalize the length direction first (this will be our primary axis)
    length_norm = normalize_vector(length_direction)
    
    # Orthogonalize face direction relative to length direction using Gram-Schmidt
    face_input = normalize_vector(width_direction)
    
    # Project face_input onto length_norm and subtract to get orthogonal component
    projection = length_norm * (face_input.dot(length_norm))
    face_orthogonal = face_input - projection
    
    # Check if face_orthogonal is too small (vectors were nearly parallel)
    if zero_test(face_orthogonal.norm()):
        # Choose an arbitrary orthogonal direction
        # Find a vector that's not parallel to length_norm
        if Abs(length_norm[0]) < Rational(9, 10):  # Threshold comparison
            temp_vector = create_v3(1, 0, 0)
        else:
            temp_vector = create_v3(0, 1, 0)
        
        # Project and orthogonalize
        projection = length_norm * (temp_vector.dot(length_norm))
        face_orthogonal = temp_vector - projection
    
    # Normalize the orthogonalized face direction
    face_norm = normalize_vector(face_orthogonal)
    
    # Cross product to get the third axis (guaranteed to be orthogonal)
    height_norm = normalize_vector(cross_product(length_norm, face_norm))
    
    # Create rotation matrix [face_norm, height_norm, length_norm]
    rotation_matrix = Matrix([
        [face_norm[0], height_norm[0], length_norm[0]],
        [face_norm[1], height_norm[1], length_norm[1]],
        [face_norm[2], height_norm[2], length_norm[2]]
    ])
    
    # Convert to Orientation
    return Orientation(rotation_matrix)


# TODO rename to create_timber (or maybe hew lolololol) + add defaults
def timber_from_directions(length: Numeric, size: V2, bottom_position: V3,
                          length_direction: Direction3D, width_direction: Direction3D,
                          name: Optional[str] = None) -> 'Timber':
    """Factory function to create a Timber with computed orientation from direction vectors
    
    This is the main way to construct Timber instances. It takes direction vectors
    and computes the proper orientation matrix automatically.
    
    Args:
        length: Length of the timber
        size: Cross-sectional size (width, height) as 2D vector, width is the X dimension (left to right), height is the Y dimension (front to back)
        bottom_position: Position of the bottom point (center of cross-section) as 3D vector
        length_direction: Direction vector for the length axis as 3D vector, the +length direction is the +Z direction
        width_direction: Direction vector for the width axis as 3D vector, the +width direction is the +X direction
        name: Optional name for this timber (used for rendering/debugging)
        
    Returns:
        Timber instance with computed orientation
    """
    orientation = _compute_timber_orientation(length_direction, width_direction)
    transform = Transform(position=bottom_position, orientation=orientation)
    return Timber(length=length, size=size, transform=transform, name=name)


@dataclass(frozen=True)
class Timber:
    """Represents a timber in the timber framing system (immutable)
    
    Note: Use timber_from_directions() factory function to construct Timber instances from
    length_direction and width_direction vectors. This class is frozen to ensure immutability
    after construction.
    
    Alternatively, if you already have a Transform object, you can construct
    Timber directly by passing: Timber(length, size, transform, name)
    """
    length: Numeric
    size: V2
    transform: Transform
    name: Optional[str] = None
    
    @property
    def bottom_position(self) -> V3:
        """Get the bottom position (center of bottom cross-section) from the transform."""
        return self.transform.position
    
    @property
    def orientation(self) -> Orientation:
        """Get the orientation from the transform."""
        return self.transform.orientation
    
    # TODO rename to get_length_direction_global and convert to class method
    @property
    def length_direction(self) -> Direction3D:
        """Get the length direction vector from the orientation matrix"""
        # Length direction is the 3rd column (index 2) of the rotation matrix
        # The +length direction is the +Z direction
        return Matrix([
            self.orientation.matrix[0, 2],
            self.orientation.matrix[1, 2],
            self.orientation.matrix[2, 2]
        ])
    
    # TODO rename to get_width_direction_global and convert to class method
    @property
    def width_direction(self) -> Direction3D:
        """Get the face direction vector from the orientation matrix"""
        # Face direction is the 1st column (index 0) of the rotation matrix
        # The +face direction is the +X direction
        return Matrix([
            self.orientation.matrix[0, 0],
            self.orientation.matrix[1, 0],
            self.orientation.matrix[2, 0]
        ])
    
    # TODO rename to get_height_direction_global and convert to class method
    @property
    def height_direction(self) -> Direction3D:
        """Get the height direction vector from the orientation matrix"""
        # Height direction is the 2nd column (index 1) of the rotation matrix
        # The +height direction is the +Y direction
        return Matrix([
            self.orientation.matrix[0, 1],
            self.orientation.matrix[1, 1],
            self.orientation.matrix[2, 1]
        ])
    
    # TODO DELETE or rename to get_centerline_position_from_bottom_global
    def get_centerline_position_from_bottom(self, distance: Numeric) -> V3:
        """
        Get the 3D position at a specific point along the timber's centerline, measured from the bottom.
        
        Args:
            distance: Distance along the timber's length direction from the bottom position
            
        Returns:
            3D position vector on the timber's centerline at the specified distance from bottom
        """
        return self.bottom_position + self.length_direction * distance
    
    # TODO DELETE or rename to get_centerline_position_from_top_global
    def get_centerline_position_from_top(self, distance: Numeric) -> V3:
        """
        Get the 3D position at a specific point along the timber's centerline, measured from the top.
        
        Args:
            distance: Distance along the timber's length direction from the top position
            
        Returns:
            3D position vector on the timber's centerline at the specified distance from top
        """
        return self.bottom_position + self.length_direction * (self.length - distance)
    
    # TODO DELETE or rename to get_bottom_center_position_global
    def get_bottom_center_position(self) -> V3:
        """
        Get the 3D position of the center of the bottom cross-section of the timber.
        
        Returns:
            3D position vector at the center of the bottom cross-section
        """
        return self.bottom_position
    
    # TODO DELETE or rename to get_top_center_position_global
    def get_top_center_position(self) -> V3:
        """
        Get the 3D position of the center of the top cross-section of the timber.
        
        Returns:
            3D position vector at the center of the top cross-section
        """
        return self.bottom_position + self.length_direction * self.length
    
    # TODO DELETE move this method onto Transform
    def global_to_local(self, global_point: V3) -> V3:
        """
        Convert a point from global world coordinates to timber-local coordinates.
        
        In the timber's local coordinate system:
        - Origin is at the bottom_position (center of bottom face)
        - Local X-axis is the width_direction
        - Local Y-axis is the height_direction
        - Local Z-axis is the length_direction
        
        Args:
            global_point: A point in global world coordinates
            
        Returns:
            The same point in timber-local coordinates
        """
        return self.transform.global_to_local(global_point)
    
    # TODO DELETE move this method onto Transform
    def local_to_global(self, local_point: V3) -> V3:
        """
        Convert a point from timber-local coordinates to global world coordinates.
        
        In the timber's local coordinate system:
        - Origin is at the bottom_position (center of bottom face)
        - Local X-axis is the width_direction
        - Local Y-axis is the height_direction
        - Local Z-axis is the length_direction
        
        Args:
            local_point: A point in timber-local coordinates
            
        Returns:
            The same point in global world coordinates
        """
        return self.transform.local_to_global(local_point)

    # TODO DELETE move this method onto Transform
    def local_direction_to_global(self, local_direction: Direction3D) -> Direction3D:
        """
        Convert a direction vector from timber-local coordinates to global world coordinates.
        
        Direction vectors are transformed differently from points - they are not affected by
        translation, only by rotation.
        
        In the timber's local coordinate system:
        - Local X-axis is the width_direction
        - Local Y-axis is the height_direction
        - Local Z-axis is the length_direction
        
        Args:
            local_direction: A direction vector in timber-local coordinates
            
        Returns:
            The same direction vector in global world coordinates
        """
        # Direction vectors only need rotation (no translation)
        # global_direction = R * local_direction
        return self.orientation.matrix * local_direction
    
    # TODO rename to get_face_direction_global
    def get_face_direction(self, face: Union[TimberFace, TimberReferenceEnd, TimberReferenceLongFace]) -> Direction3D:
        """
        Get the world direction vector for a specific face of this timber.
        
        Args:
            face: The face to get the direction for (can be TimberFace, TimberReferenceEnd, or TimberReferenceLongFace)
            
        Returns:
            Direction vector pointing outward from the specified face in world coordinates
        """
        # Convert TimberReferenceEnd or TimberReferenceLongFace to TimberFace if needed
        if isinstance(face, (TimberReferenceEnd, TimberReferenceLongFace)):
            face = face.to_timber_face()
        
        if face == TimberFace.TOP:
            return self.length_direction
        elif face == TimberFace.BOTTOM:
            return -self.length_direction
        elif face == TimberFace.RIGHT:
            return self.width_direction
        elif face == TimberFace.LEFT:
            return -self.width_direction
        elif face == TimberFace.FRONT:
            return self.height_direction
        else:  # BACK
            return -self.height_direction

    def get_size_in_face_normal_axis(self, face: Union[TimberFace, TimberReferenceEnd, TimberReferenceLongFace]) -> Numeric:
        """
        Get the size of the timber in the direction normal to the specified face.
        
        Args:
            face: The face to get the size for (can be TimberFace, TimberReferenceEnd, or TimberReferenceLongFace)
        """
        # Convert TimberReferenceEnd or TimberReferenceLongFace to TimberFace if needed
        if isinstance(face, (TimberReferenceEnd, TimberReferenceLongFace)):
            face = face.to_timber_face()
        
        if face == TimberFace.TOP or face == TimberFace.BOTTOM:
            return self.length
        elif face == TimberFace.RIGHT or face == TimberFace.LEFT:
            return self.size[0]
        else:  # FRONT or BACK
            return self.size[1]
    
    # TODO rename get_closest_oriented_face_from_global_direction
    def get_closest_oriented_face(self, target_direction: Direction3D) -> TimberFace:
        """
        Find which face of this timber best aligns with the target direction.
        
        The target_direction should point "outwards" from the desired face (not into it).
        
        Args:
            target_direction: Direction vector to match against
            
        Returns:
            The TimberFace that best aligns with the target direction
        """
        faces = [TimberFace.TOP, TimberFace.BOTTOM, TimberFace.RIGHT, 
                TimberFace.LEFT, TimberFace.FRONT, TimberFace.BACK]
        
        best_face = faces[0]
        best_alignment = target_direction.dot(self.get_face_direction(faces[0]))
        
        for face in faces[1:]:
            face_direction = self.get_face_direction(face)
            alignment = target_direction.dot(face_direction)
            if alignment > best_alignment:
                best_alignment = alignment
                best_face = face
        
        return best_face 
    
    # UNTESTED
    # TODO rename to get_inside_face_from_footprint
    def get_inside_face(self, footprint: Footprint) -> TimberFace:
        """
        Get the inside face of this timber relative to the footprint.
        
        This method finds which face of the timber is oriented toward the interior
        of the footprint by:
        1. Finding the nearest boundary of the footprint to the timber's centerline
        2. Getting the inward normal of that boundary
        3. Finding which timber face best aligns with that inward direction
        
        Args:
            footprint: The footprint to determine inside/outside orientation
            
        Returns:
            The TimberFace that points toward the inside of the footprint
        """
        # Project timber's centerline onto XY plane for footprint comparison
        bottom_2d = create_v2(self.bottom_position[0], self.bottom_position[1])
        top_position = self.get_top_center_position()
        top_2d = create_v2(top_position[0], top_position[1])
        
        # Find nearest boundary to timber's centerline
        boundary_idx, boundary_side, distance = footprint.nearest_boundary_from_line(bottom_2d, top_2d)
        
        # Get the inward normal of that boundary
        inward_x, inward_y, inward_z = footprint.get_inward_normal(boundary_idx)
        inward_normal = create_v3(inward_x, inward_y, inward_z)
        
        # Find which face of the timber aligns with the inward direction
        return self.get_closest_oriented_face(inward_normal)

    # UNTESTED
    # TODO rename to get_outside_face_from_footprint
    def get_outside_face(self, footprint: Footprint) -> TimberFace:
        """
        Get the outside face of this timber relative to the footprint.
        
        This method finds which face of the timber is oriented toward the exterior
        of the footprint by:
        1. Finding the nearest boundary of the footprint to the timber's centerline
        2. Getting the inward normal of that boundary
        3. Finding which timber face best aligns with the opposite (outward) direction
        
        Args:
            footprint: The footprint to determine inside/outside orientation
            
        Returns:
            The TimberFace that points toward the outside of the footprint
        """
        # Project timber's centerline onto XY plane for footprint comparison
        bottom_2d = create_v2(self.bottom_position[0], self.bottom_position[1])
        top_position = self.get_top_center_position()
        top_2d = create_v2(top_position[0], top_position[1])
        
        # Find nearest boundary to timber's centerline
        boundary_idx, boundary_side, distance = footprint.nearest_boundary_from_line(bottom_2d, top_2d)
        
        # Get the inward normal of that boundary
        inward_x, inward_y, inward_z = footprint.get_inward_normal(boundary_idx)
        inward_normal = create_v3(inward_x, inward_y, inward_z)
        
        # Find which face of the timber aligns with the outward direction (negative of inward)
        outward_normal = -inward_normal
        return self.get_closest_oriented_face(outward_normal)
    
    def get_transform_matrix(self) -> Matrix:
        """Get the 4x4 transformation matrix for this timber"""
        # Create 4x4 transformation matrix
        transform = Matrix([
            [self.orientation.matrix[0,0], self.orientation.matrix[0,1], self.orientation.matrix[0,2], self.bottom_position[0]],
            [self.orientation.matrix[1,0], self.orientation.matrix[1,1], self.orientation.matrix[1,2], self.bottom_position[1]],
            [self.orientation.matrix[2,0], self.orientation.matrix[2,1], self.orientation.matrix[2,2], self.bottom_position[2]],
            [0, 0, 0, 1]
        ])
        return transform


    def project_global_point_onto_timber_face_global(self, global_point: V3, face: Union[TimberFace, TimberReferenceEnd, TimberReferenceLongFace]) -> V3:
        """
        Project a point from global coordinates onto the timber's face and return result in global coordinates.
        
        Args:
            global_point: The point to project in global coordinates (3x1 Matrix)
            face: The face to project onto (can be TimberFace, TimberReferenceEnd, or TimberReferenceLongFace)
        """
        # Convert TimberReferenceEnd or TimberReferenceLongFace to TimberFace if needed
        if isinstance(face, (TimberReferenceEnd, TimberReferenceLongFace)):
            face = face.to_timber_face()
        
        # Convert global point to local coordinates
        local_point = self.global_to_local(global_point)
        
        # project the 0,0 point onto the face
        face_zero_local = face.get_direction() * self.get_size_in_face_normal_axis(face) / 2
        local_point_face_component = (local_point-face_zero_local).dot(face.get_direction()) * face.get_direction()
        local_point_projected = local_point - local_point_face_component
        return self.transform.local_to_global(local_point_projected)


# ============================================================================
# Joint Related Types and Functions
# ============================================================================


@dataclass(frozen=True)
class Cut(ABC):
    # debug reference to the base timber we are cutting
    # each Cut is tied to a timber so this is very reasonable to store here
    timber: Timber

    # set these values by computing them relative to the timber features using helper functions 
    transform: Transform

    # end cuts are special as they set the length of the timber
    # you can only have an end cut on one end of the timber, you can't have an end cut on both ends at once (maybe we should support this?)
    maybe_end_cut: Optional[TimberReferenceEnd]

    # returns the negative CSG of the cut (the part of the timber that is removed by the cut)
    # in LOCAL coordinates (relative to timber.bottom_position)
    @abstractmethod
    def get_negative_csg_local(self) -> MeowMeowCSG:
        pass


def _create_timber_prism_csg_local(timber: Timber, cuts: list) -> MeowMeowCSG:
    """
    Helper function to create a prism CSG for a timber in LOCAL coordinates, 
    extending ends with cuts to infinity.
    
    LOCAL coordinates means distances are relative to timber.bottom_position.
    This is used for rendering (where the prism is created at origin and then transformed)
    and for CSG operations (where cuts are also in local coordinates).
    
    Args:
        timber: The timber to create a prism for
        cuts: List of cuts on this timber (used to determine if ends should be infinite)
        
    Returns:
        Prism CSG representing the timber (possibly semi-infinite or infinite) in LOCAL coordinates
    """
    from .meowmeowcsg import Prism
    
    # Check if bottom end has cuts
    has_bottom_cut = any(
        cut.maybe_end_cut == TimberReferenceEnd.BOTTOM 
        for cut in cuts
    )
    
    # Check if top end has cuts  
    has_top_cut = any(
        cut.maybe_end_cut == TimberReferenceEnd.TOP
        for cut in cuts
    )
    
    # In local coordinates:
    # - bottom is at 0
    # - top is at timber.length
    # - if an end has cuts, extend to infinity in that direction
    
    start_distance = None if has_bottom_cut else 0
    end_distance = None if has_top_cut else timber.length
    
    # Create a prism representing the timber in local coordinates
    # The prism needs to use the timber's orientation to properly represent
    # timbers in any direction (horizontal, vertical, diagonal, etc.)
    return Prism(
        size=timber.size,
        transform=Transform.identity(),
        start_distance=start_distance,
        end_distance=end_distance
    )


class CutTimber:
    """A timber with cuts applied to it."""
    
    # Declare members
    timber: Timber
    cuts: List['Cut']
    joints: List  # List of joints this timber participates in
    
    def __init__(self, timber: Timber, cuts: List['Cut'] = None):
        """
        Create a CutTimber from a Timber.
        
        Args:
            timber: The timber to be cut
            cuts: Optional list of cuts to apply (default: empty list)
        """
        self.timber = timber
        self.cuts = cuts if cuts is not None else []
        self.joints = []  # List of joints this timber participates in

    @property
    def name(self) -> Optional[str]:
        """Get the name from the underlying timber."""
        return self.timber.name

    # this one returns the timber without cuts where ends with joints are infinite in length
    def _extended_timber_without_cuts_csg_local(self) -> MeowMeowCSG:
        """
        Returns a CSG representation of the timber without any cuts applied.
        
        If an end has cuts on it (indicated by maybeEndCut), that end is extended to infinity.
        This allows joints to extend the timber as needed during the CSG cutting operations.
        
        Uses LOCAL coordinates (relative to timber.bottom_position).
        All cuts on this timber are also in LOCAL coordinates.
        
        Returns:
            Prism CSG representing the timber (possibly semi-infinite or infinite) in LOCAL coordinates
        """
        return _create_timber_prism_csg_local(self.timber, self.cuts)

    # this one returns the timber with all cuts applied
    def render_timber_with_cuts_csg_local(self) -> MeowMeowCSG:
        """
        Returns a CSG representation of the timber with all cuts applied.

        
        Returns:
            Difference CSG representing the timber with all cuts subtracted
        """
        # Start with the timber prism (possibly with infinite ends where cuts exist)
        starting_csg = self._extended_timber_without_cuts_csg_local()
        
        # If there are no cuts, just return the starting CSG
        if not self.cuts:
            return starting_csg
        
        # Collect all the negative CSGs (volumes to be removed) from the cuts
        negative_csgs = [cut.get_negative_csg_local() for cut in self.cuts]
        
        # Return the difference: timber - all cuts
        from .meowmeowcsg import Difference
        return Difference(starting_csg, negative_csgs)


# TODO rename to just Accessory
@dataclass(frozen=True)
class JointAccessory(ABC):
    """Base class for joint accessories like wedges, drawbores, etc."""
    
    @abstractmethod
    def render_csg_local(self) -> MeowMeowCSG:
        """
        Generate CSG representation of the accessory in local space.
        
        The local space is defined by the accessory's orientation and position,
        where the CSG is generated at the origin with identity orientation.
        
        Returns:
            MeowMeowCSG: The CSG representation of the accessory in local space
        """
        pass


# ============================================================================
# Joint Accessory Types: Pegs and Wedges
# ============================================================================

class PegShape(Enum):
    """Shape of a peg."""
    SQUARE = "square"
    ROUND = "round"


# TODO add a get_local_csg function that returns the CSG of the peg at the origin 
@dataclass(frozen=True)
class Peg(JointAccessory):
    """
    Represents a peg used in timber joinery (e.g., draw bore pegs, komisen).
    
    The peg is stored in GLOBAL SPACE with absolute position and orientation.
    In identity orientation, the peg points in the +Z direction,
    with the insertion end at the origin.

    By convention, the origin of the peg is on the mortise face that the peg is going into.
    This is why there are 2 lengths parameters, one for how deep the peg goes past the mortise face, and one for how far the peg sticks out of the mortise face.
    
    Attributes:
        transform: Transform (position and orientation) of the peg in global space
        size: Size/diameter of the peg (for square pegs, this is the side length)
        shape: Shape of the peg (SQUARE or ROUND)
        forward_length: How far the peg reaches in the forward direction (into the mortise)
        stickout_length: How far the peg "sticks out" in the back direction (outside the mortise)
    """
    transform: Transform
    # for square pegs, this is the side length
    # for round pegs, this is the diameter
    size: Numeric
    shape: PegShape

    # how far the peg reaches in the forward direction
    forward_length: Numeric

    # how far the peg "sticks out" in the back direction
    stickout_length: Numeric
    
    def render_csg_local(self) -> MeowMeowCSG:
        """
        Generate CSG representation of the peg in local space.
        
        The peg is centered at the origin with identity orientation,
        extending from -stickout_length to forward_length along the Z axis.
        
        Returns:
            MeowMeowCSG: The CSG representation of the peg
        """
        if self.shape == PegShape.SQUARE:
            # Square peg - use Prism with square cross-section
            return Prism(
                size=create_v2(self.size, self.size),
                transform=Transform.identity(),
                start_distance=-self.stickout_length,
                end_distance=self.forward_length
            )
        else:  # PegShape.ROUND
            # Round peg - use Cylinder
            radius = self.size / 2
            return Cylinder(
                axis_direction=create_v3(0, 0, 1),
                radius=radius,
                position=create_v3(0, 0, 0),
                start_distance=-self.stickout_length,
                end_distance=self.forward_length
            )


@dataclass(frozen=True)
class WedgeShape:
    """Specification for wedge dimensions."""
    base_width: Numeric # width of the base of the trapezoid in the X axis
    tip_width: Numeric # width of the tip of the trapezoid in the X axis
    height: Numeric # height of the trapezoid in the Y axis
    length: Numeric  # From bottom to top of trapezoid in the Z axis


# TODO add a get_local_csg function that returns the CSG of the wedge at the origin 
@dataclass(frozen=True)
class Wedge(JointAccessory):
    r"""
    Represents a wedge used in timber joinery (e.g., wedged tenons).
    
    The wedge is stored in local space of a timber. In identity orientation,
    the pointy end of the wedge goes in the length direction of the timber.
    
    The profile of the wedge (trapezoidal shape) is in the Y axis 
    (height in Y). The width of the wedge is in the X axis.
    The origin (0,0) is at the bottom center of the longer side of the triangle.
    
    Visual representation (looking at wedge from the side):
         +z
          _______
         / \      \
        /   \      \  +y
   -x  /_____\______\ 
          ↑
        origin
    
    Attributes:
        transform: Transform (position and orientation) of the wedge in local timber space
        base_width: Width at the base (wider end) of the wedge
        tip_width: Width at the tip (narrower end, where triangle is cut)
        height: Height of the wedge (in Y axis)
        length: Length from base to tip
    """
    transform: Transform
    base_width: Numeric
    tip_width: Numeric
    height: Numeric
    length: Numeric
    
    @property
    def width(self) -> Numeric:
        """Alias for base_width for convenience."""
        return self.base_width
    
    def render_csg_local(self) -> MeowMeowCSG:
        """
        Generate CSG representation of the wedge in local space.
        
        The wedge is created using CSG operations with half-planes to form
        a trapezoidal prism. The base is at z=0 and extends to z=length.
        The wedge tapers from base_width to tip_width in the X direction,
        and has a trapezoidal profile in the YZ plane.
        
        For now, this creates a simplified bounding box representation.
        TODO: Implement proper trapezoidal shape using half-plane intersections.
        
        Returns:
            MeowMeowCSG: The CSG representation of the wedge
        """
        # Create a rectangular prism bounding box
        # The origin is at the bottom center of the base (z=0, y=0, x=0)
        # The prism extends from z=0 to z=length
        # Width (x): centered, so from -base_width/2 to +base_width/2
        # Height (y): from 0 to height
        
        # For Prism, position is the center of the cross-section at the reference point
        # The cross-section is centered in XY, so position should be at the center
        wedge_transform = Transform(
            position=create_v3(0, self.height / Rational(2), 0),
            orientation=Orientation.identity()
        )
        return Prism(
            size=create_v2(self.base_width, self.height),
            transform=wedge_transform,
            start_distance=0,
            end_distance=self.length
        )


@dataclass(frozen=True)
class Joint:
    cut_timbers: Dict[str, CutTimber]
    jointAccessories: Dict[str, JointAccessory] = field(default_factory=dict)


@dataclass(frozen=True)
class Frame:
    """
    Represents a complete timber frame structure with all cut timbers and accessories.
    
    In traditional timber framing, a 'frame' is the complete structure ready for raising.
    This class encapsulates all the timbers that have been cut with their joints,
    plus any accessories like pegs, wedges, or drawbores.
    
    Attributes:
        cut_timbers: List of CutTimber objects representing all timbers in the frame
        accessories: List of JointAccessory objects (already in global space)
        name: Optional name for this frame (e.g., "Oscar's Shed", "Main Frame")
    """
    cut_timbers: List[CutTimber]
    accessories: List[JointAccessory] = field(default_factory=list)
    name: Optional[str] = None
    
    @classmethod
    def from_joints(cls, joints: List[Joint], 
                    additional_unjointed_timbers: List[Timber] = None,
                    name: Optional[str] = None) -> 'Frame':
        """
        Create a Frame from a list of joints and optional additional unjointed timbers.
        
        This constructor extracts all cut timbers and accessories from the joints,
        and combines cut timbers that share the same underlying timber reference.
        
        Args:
            joints: List of Joint objects
            additional_unjointed_timbers: Optional list of Timber objects that don't 
                                         participate in any joints (default: empty list)
            name: Optional name for the frame
            
        Returns:
            Frame: A new Frame object with merged cut timbers and collected accessories
            
        Raises:
            ValueError: If two timbers with the same name but same underlying timber 
                       have different references (indicates a bug)
        
        Warnings:
            Prints a warning if two timbers with the same name have different underlying 
            timber references and the underlying timbers are actually different.
        """
        import warnings
        
        if additional_unjointed_timbers is None:
            additional_unjointed_timbers = []
        
        # Dictionary to group CutTimber objects by their underlying Timber reference (identity)
        # Key: id(timber), Value: List of CutTimber objects
        timber_ref_to_cut_timbers: Dict[int, List[CutTimber]] = {}
        
        # Extract cut timbers from all joints
        for joint in joints:
            for cut_timber in joint.cut_timbers.values():
                timber_id = id(cut_timber.timber)
                if timber_id not in timber_ref_to_cut_timbers:
                    timber_ref_to_cut_timbers[timber_id] = []
                timber_ref_to_cut_timbers[timber_id].append(cut_timber)
        
        # Check for name conflicts
        # Build a mapping from name to list of timber references
        name_to_timber_refs: Dict[str, List[Timber]] = {}
        for timber_id, cut_timber_list in timber_ref_to_cut_timbers.items():
            timber = cut_timber_list[0].timber  # Get timber from first CutTimber
            timber_name = timber.name
            if timber_name is not None:
                if timber_name not in name_to_timber_refs:
                    name_to_timber_refs[timber_name] = []
                # Only add if not already in the list (check by identity)
                if not any(t is timber for t in name_to_timber_refs[timber_name]):
                    name_to_timber_refs[timber_name].append(timber)
        
        # Check for conflicts
        for timber_name, timber_refs in name_to_timber_refs.items():
            if len(timber_refs) > 1:
                # Multiple timbers with the same name
                # Check if the underlying timbers are actually different
                for i in range(len(timber_refs)):
                    for j in range(i + 1, len(timber_refs)):
                        timber_i = timber_refs[i]
                        timber_j = timber_refs[j]
                        
                        # Compare using structural equality (==)
                        if timber_i == timber_j:
                            # Same timber data but different references - this is a bug
                            raise ValueError(
                                f"Error: Found two timber references with the same name '{timber_name}' "
                                f"that have identical underlying timber data. This indicates a bug "
                                f"where the same timber was created multiple times instead of reusing "
                                f"the same reference."
                            )
                        else:
                            # Different timber data with the same name - just a warning
                            warnings.warn(
                                f"Warning: Found multiple timbers with the same name '{timber_name}' "
                                f"but different properties (length, size, position, or orientation). "
                                f"This may indicate an error in timber naming. "
                                f"Timber 1: length={timber_i.length}, size={timber_i.size}, "
                                f"position={timber_i.bottom_position}. "
                                f"Timber 2: length={timber_j.length}, size={timber_j.size}, "
                                f"position={timber_j.bottom_position}."
                            )
        
        # Merge cut timbers with the same underlying timber reference
        merged_cut_timbers: List[CutTimber] = []
        for timber_id, cut_timber_list in timber_ref_to_cut_timbers.items():
            timber = cut_timber_list[0].timber
            
            # Collect all cuts from all CutTimber instances for this timber
            all_cuts: List[Cut] = []
            for cut_timber in cut_timber_list:
                all_cuts.extend(cut_timber.cuts)
            
            # Create a single merged CutTimber
            merged_cut_timber = CutTimber(timber, cuts=all_cuts)
            merged_cut_timbers.append(merged_cut_timber)
        
        # Add additional unjointed timbers as CutTimbers with no cuts
        for timber in additional_unjointed_timbers:
            merged_cut_timbers.append(CutTimber(timber, cuts=[]))
        
        # Collect all accessories from all joints
        all_accessories: List[JointAccessory] = []
        for joint in joints:
            all_accessories.extend(joint.jointAccessories.values())
        
        # Create and return the Frame
        return cls(
            cut_timbers=merged_cut_timbers,
            accessories=all_accessories,
            name=name
        )
    
    def __post_init__(self):
        """Validate that the frame contains no floating point numbers."""
        self._check_no_floats()
    
    def _check_no_floats(self):
        """
        Check that all numeric values in the frame use SymPy Rationals, not floats.
        
        Raises:
            AssertionError: If any float values are found in the frame
        """
        # Check all cut timbers
        for cut_timber in self.cut_timbers:
            timber = cut_timber.timber
            self._check_timber_no_floats(timber)
            
            # Check all cuts on this timber
            for cut in cut_timber.cuts:
                self._check_cut_no_floats(cut)
        
        # Check all accessories
        for accessory in self.accessories:
            self._check_accessory_no_floats(accessory)
    
    def _check_timber_no_floats(self, timber: Timber):
        """Check a single timber for float values."""
        self._check_numeric_value(timber.length, f"Timber '{timber.name}' length")
        self._check_vector(timber.size, f"Timber '{timber.name}' size")
        self._check_vector(timber.transform.position, f"Timber '{timber.name}' transform.position")
        # Note: orientation.matrix is checked as part of the matrix
        self._check_matrix(timber.transform.orientation.matrix, f"Timber '{timber.name}' transform.orientation")
    
    def _check_accessory_no_floats(self, accessory: JointAccessory):
        """Check an accessory for float values."""
        if isinstance(accessory, Peg):
            self._check_vector(accessory.transform.position, f"Peg transform.position")
            self._check_numeric_value(accessory.size, f"Peg size")
            self._check_numeric_value(accessory.forward_length, f"Peg forward_length")
            self._check_numeric_value(accessory.stickout_length, f"Peg stickout_length")
            self._check_matrix(accessory.transform.orientation.matrix, f"Peg transform.orientation")
        elif isinstance(accessory, Wedge):
            self._check_vector(accessory.transform.position, f"Wedge transform.position")
            self._check_numeric_value(accessory.base_width, f"Wedge base_width")
            self._check_numeric_value(accessory.tip_width, f"Wedge tip_width")
            self._check_numeric_value(accessory.height, f"Wedge height")
            self._check_numeric_value(accessory.length, f"Wedge length")
            self._check_matrix(accessory.transform.orientation.matrix, f"Wedge transform.orientation")
    
    def _check_cut_no_floats(self, cut: Cut):
        """Check a cut for float values."""
        if isinstance(cut, HalfPlaneCut):
            half_plane = cut.half_plane
            self._check_vector(half_plane.normal, "HalfPlaneCut normal")
            self._check_numeric_value(half_plane.offset, "HalfPlaneCut offset")
        elif isinstance(cut, CSGCut):
            # CSGCut contains arbitrary CSG - would need recursive checking
            # For now, we'll skip deep CSG validation
            pass
    
    def _check_numeric_value(self, value: Numeric, description: str):
        """Check that a numeric value is not a float."""
        if isinstance(value, float):
            raise AssertionError(
                f"Float detected in Frame: {description} = {value}. "
                f"All numeric values must use SymPy Rational, not float."
            )
        # Also check if it's a SymPy expression containing floats
        if isinstance(value, Expr):
            # Check if any atoms in the expression are floats
            if any(isinstance(atom, float) or (hasattr(atom, 'is_Float') and atom.is_Float) 
                   for atom in value.atoms()):
                raise AssertionError(
                    f"Float detected in Frame: {description} contains float in expression {value}. "
                    f"All numeric values must use SymPy Rational, not float."
                )
    
    def _check_vector(self, vec: Matrix, description: str):
        """Check that all elements in a vector are not floats."""
        for i in range(vec.rows):
            self._check_numeric_value(vec[i], f"{description}[{i}]")
    
    def _check_matrix(self, mat: Matrix, description: str):
        """Check that all elements in a matrix are not floats."""
        for i in range(mat.rows):
            for j in range(mat.cols):
                self._check_numeric_value(mat[i, j], f"{description}[{i},{j}]")


# ============================================================================
# Cut Classes
# ============================================================================

@dataclass(frozen=True)
class HalfPlaneCut(Cut):
    """
    A half plane cut is a cut that is defined by a half plane.
    """
    half_plane: HalfPlane
    
    def get_negative_csg_local(self) -> MeowMeowCSG:
        return self.half_plane


@dataclass(frozen=True)
class CSGCut(Cut):
    """
    A CSG cut is a cut defined by an arbitrary CSG object.
    This allows for more complex cuts like grooves, dados, and other shapes
    that can't be represented by a simple half-plane.
    
    The CSG object represents the volume to be REMOVED from the timber (negative CSG).
    """
    negative_csg: MeowMeowCSG
    
    def get_negative_csg_local(self) -> MeowMeowCSG:
        return self.negative_csg


# ============================================================================
# Helper Functions for Creating Joint Accessories
# ============================================================================

def create_peg_going_into_face(
    timber: Timber,
    face: TimberReferenceLongFace,
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
    face_normal_local = face.to_timber_face().get_direction()
    
    # Position the peg on the timber's surface
    # Start at centerline, then move along length and offset from centerline
    position_local = create_v3(0, 0, distance_from_bottom)
    
    # Offset from centerline depends on which face we're on
    if face == TimberReferenceLongFace.RIGHT:
        # RIGHT face: offset in +X (width) direction, surface at +width/2
        position_local = create_v3(
            timber.size[0] / Rational(2),  # At right surface
            distance_from_centerline,  # Offset in height direction
            distance_from_bottom
        )
        # Peg points inward (-X direction in local space)
        length_dir = create_v3(-1, 0, 0)
        width_dir = create_v3(0, 1, 0)
        
    elif face == TimberReferenceLongFace.LEFT:
        # LEFT face: offset in -X (width) direction
        position_local = create_v3(
            -timber.size[0] / Rational(2),  # At left surface
            distance_from_centerline,  # Offset in height direction
            distance_from_bottom
        )
        # Peg points inward (+X direction in local space)
        length_dir = create_v3(1, 0, 0)
        width_dir = create_v3(0, 1, 0)
        
    elif face == TimberReferenceLongFace.FRONT:
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
    peg_orientation = _compute_timber_orientation(length_dir, width_dir)
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
    wedge_orientation = _compute_timber_orientation(length_dir, width_dir)
    wedge_transform = Transform(position=wedge_position, orientation=wedge_orientation)
    
    return Wedge(
        transform=wedge_transform,
        base_width=shape.base_width,
        tip_width=shape.tip_width,
        height=shape.height,
        length=shape.length
    )

