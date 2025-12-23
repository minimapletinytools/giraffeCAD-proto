"""
GiraffeCAD - Timber framing CAD system
Based on the API specification in morenotes.md
"""

from sympy import Matrix, Abs, Rational, Integer, Expr, sqrt, simplify
from moothymoth import Orientation
from footprint import Footprint
from meowmeowcsg import MeowMeowCSG, HalfPlane, Prism, Cylinder, Union as CSGUnion, Difference as CSGDifference
from enum import Enum
from typing import List, Optional, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass
from abc import abstractmethod

# Type aliases for vectors using sympy
V2 = Matrix  # 2D vector - 2x1 Matrix
V3 = Matrix  # 3D vector - 3x1 Matrix  
Direction3D = Matrix  # 3D direction vector - 3x1 Matrix
Numeric = Union[float, int, Expr]  # Numeric values (SymPy Expr type STRONGLY preferred, there's really no reason to ever be using floats or ints. Always use Rational)

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
    FORWARD = 4 # the face vector with normal vector in the +Y axis direction
    LEFT = 5 # the face vector with normal vector in the -X axis direction
    BACK = 6 # the face vector with normal vector in the -Y axis direction
    
    def get_direction(self) -> Direction3D:
        """Get the direction vector for this face in world coordinates."""
        if self == TimberFace.TOP:
            return create_vector3d(0, 0, 1)
        elif self == TimberFace.BOTTOM:
            return create_vector3d(0, 0, -1)
        elif self == TimberFace.RIGHT:
            return create_vector3d(1, 0, 0)
        elif self == TimberFace.LEFT:
            return create_vector3d(-1, 0, 0)
        elif self == TimberFace.FORWARD:
            return create_vector3d(0, 1, 0)
        else:  # BACK
            return create_vector3d(0, -1, 0)
    
    def is_perpendicular(self, other: 'TimberFace') -> bool:
        """
        Check if two faces are perpendicular to each other.
        
        Perpendicular face pairs (orthogonal axes):
        - X-axis faces (RIGHT, LEFT) <-> Y-axis faces (FORWARD, BACK)
        - X-axis faces (RIGHT, LEFT) <-> Z-axis faces (TOP, BOTTOM)
        - Y-axis faces (FORWARD, BACK) <-> Z-axis faces (TOP, BOTTOM)
        """
        # Define axis groups
        x_faces = {TimberFace.RIGHT, TimberFace.LEFT}
        y_faces = {TimberFace.FORWARD, TimberFace.BACK}
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

class TimberReferenceEnd(Enum):
    TOP = 1
    BOTTOM = 2

class TimberReferenceLongFace(Enum):
    RIGHT = 3
    FORWARD = 4
    LEFT = 5
    BACK = 6
    
    def to_timber_face(self) -> TimberFace:
        """Convert TimberReferenceLongFace to TimberFace."""
        return TimberFace(self.value)
    
    def is_perpendicular(self, other: 'TimberReferenceLongFace') -> bool:
        """
        Check if two long faces are perpendicular to each other.
        
        Perpendicular face pairs:
        - RIGHT <-> FORWARD, RIGHT <-> BACK
        - LEFT <-> FORWARD, LEFT <-> BACK
        """
        return self.to_timber_face().is_perpendicular(other.to_timber_face())

class TimberReferenceLongEdge(Enum):
    RIGHT_FORWARD = 7
    FORWARD_LEFT = 8
    LEFT_BACK = 9
    BACK_RIGHT = 10
    FORWARD_RIGHT = 11
    RIGHT_BACK = 12
    BACK_LEFT = 13
    LEFT_FORWARD = 14

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
# Data Structures
# ============================================================================



# you can probable delete these?
@dataclass
class DistanceFromFace:
    face: TimberFace
    distance: Numeric

# you can probable delete these?

@dataclass
class DistanceFromLongFace:
    face: TimberReferenceLongFace
    distance: Numeric

# you can probable delete these?
@dataclass
class DistanceFromEnd:
    end: TimberReferenceEnd
    distance: Numeric

# you can probable delete these?
@dataclass
class StandardMortise:
    # StandardMortise is a rectangular pocket cut into a face of a timber
    mortise_face: TimberFace

    # Position relative to timber end and long face
    pos_rel_to_end: DistanceFromEnd
    pos_rel_to_long_face: Optional[DistanceFromLongFace]

    # Cross-sectional dimensions (perpendicular to mortise depth)
    # These are generic dimension names because depending on mortise orientation,
    # they may align with different timber axes
    size1: Numeric  # First cross-section dimension (in the axis perpendicular to pos_rel_to_long_face.face1)
    size2: Numeric  # Second cross-section dimension (in the axis perpendicular to pos_rel_to_long_face.face2)

    depth: Numeric  # How deep the mortise goes into the timber, measured relative to the mortise face

@dataclass
class FaceAlignedJoinedTimberOffset:
    reference_face: TimberFace
    centerline_offset: Optional[Numeric]
    face_offset: Optional[Numeric]


@dataclass
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
        
        if f1 == TimberReferenceLongFace.RIGHT and f2 == TimberReferenceLongFace.FORWARD:
            return TimberReferenceLongEdge.RIGHT_FORWARD
        elif f1 == TimberReferenceLongFace.FORWARD and f2 == TimberReferenceLongFace.LEFT:
            return TimberReferenceLongEdge.FORWARD_LEFT
        elif f1 == TimberReferenceLongFace.LEFT and f2 == TimberReferenceLongFace.BACK:
            return TimberReferenceLongEdge.LEFT_BACK
        elif f1 == TimberReferenceLongFace.BACK and f2 == TimberReferenceLongFace.RIGHT:
            return TimberReferenceLongEdge.BACK_RIGHT
        elif f1 == TimberReferenceLongFace.FORWARD and f2 == TimberReferenceLongFace.RIGHT:
            return TimberReferenceLongEdge.FORWARD_RIGHT
        elif f1 == TimberReferenceLongFace.RIGHT and f2 == TimberReferenceLongFace.BACK:
            return TimberReferenceLongEdge.RIGHT_BACK
        elif f1 == TimberReferenceLongFace.BACK and f2 == TimberReferenceLongFace.LEFT:
            return TimberReferenceLongEdge.BACK_LEFT
        elif f1 == TimberReferenceLongFace.LEFT and f2 == TimberReferenceLongFace.FORWARD:
            return TimberReferenceLongEdge.LEFT_FORWARD
        else:
            raise ValueError(f"Invalid faces: {f1} and {f2}")
    
    def is_valid(self) -> bool:
        """
        Check if the two faces are perpendicular to each other.
        """
        return self.face1.face.is_perpendicular(self.face2.face)

    



# TODO this is really only needed for JoinTimbers so move it near that function
# TODO rename to ButtStickout or something like that...
@dataclass
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
# Helper Functions for Vector Operations
# ============================================================================

def create_vector2d(x: Numeric, y: Numeric) -> V2:
    """Create a 2D vector"""
    return Matrix([x, y])

def create_vector3d(x: Numeric, y: Numeric, z: Numeric) -> V3:
    """Create a 3D vector"""
    return Matrix([x, y, z])

def normalize_vector(vec: Matrix) -> Matrix:
    """Normalize a vector using SymPy's exact computation"""
    norm = vec.norm()
    if norm == 0:
        return vec
    return vec / norm

def cross_product(v1: V3, v2: V3) -> V3:
    """Calculate cross product of two 3D vectors"""
    return Matrix([
        v1[1]*v2[2] - v1[2]*v2[1],
        v1[2]*v2[0] - v1[0]*v2[2], 
        v1[0]*v2[1] - v1[1]*v2[0]
    ])

def vector_magnitude(vec: Matrix):
    """Calculate magnitude of a vector using SymPy's exact computation"""
    return vec.norm()

# ============================================================================
# Core Classes
# ============================================================================

class Timber:
    """Represents a timber in the timber framing system"""
    
    def __init__(self, length: Numeric, size: V2, bottom_position: V3, 
                 length_direction: Direction3D, width_direction: Direction3D):
        """
        Args:
            length: Length of the timber
            size: Cross-sectional size (width, height) as 2D vector, width is the X dimension (left to right), height is the Y dimension (front to back)
            bottom_position: Position of the bottom point (center of cross-section) as 3D vector
            length_direction: Direction vector for the length axis as 3D vector, the +length direction is the +Z direction
            width_direction: Direction vector for the width axis as 3D vector, the +width direction is the +X direction
        """
        self.length: Numeric = length
        self.size: V2 = size
        self.bottom_position: V3 = bottom_position
        self.name: Optional[str] = None
        self.orientation: Orientation
        
        # Calculate orientation matrix from input directions
        self._compute_orientation(length_direction, width_direction)
    
    def _compute_orientation(self, length_direction: Direction3D, width_direction: Direction3D):
        """Compute the orientation matrix from length and face directions"""
        # Normalize the length direction first (this will be our primary axis)
        length_norm = normalize_vector(length_direction)
        
        # Orthogonalize face direction relative to length direction using Gram-Schmidt
        face_input = normalize_vector(width_direction)
        
        # Project face_input onto length_norm and subtract to get orthogonal component
        projection = length_norm * (face_input.dot(length_norm))
        face_orthogonal = face_input - projection
        
        # Check if face_orthogonal is too small (vectors were nearly parallel)
        if face_orthogonal.norm() < 1e-10:  # Epsilon comparison - use float
            # Choose an arbitrary orthogonal direction
            # Find a vector that's not parallel to length_norm
            if Abs(length_norm[0]) < 0.9:  # Threshold comparison - use float
                temp_vector = create_vector3d(1, 0, 0)
            else:
                temp_vector = create_vector3d(0, 1, 0)
            
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
        self.orientation = Orientation(rotation_matrix)
    
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
    
    def get_centerline_position_from_bottom(self, distance: Numeric) -> V3:
        """
        Get the 3D position at a specific point along the timber's centerline, measured from the bottom.
        
        Args:
            distance: Distance along the timber's length direction from the bottom position
            
        Returns:
            3D position vector on the timber's centerline at the specified distance from bottom
        """
        return self.bottom_position + self.length_direction * distance
    
    def get_centerline_position_from_top(self, distance: Numeric) -> V3:
        """
        Get the 3D position at a specific point along the timber's centerline, measured from the top.
        
        Args:
            distance: Distance along the timber's length direction from the top position
            
        Returns:
            3D position vector on the timber's centerline at the specified distance from top
        """
        return self.bottom_position + self.length_direction * (self.length - distance)
    
    # TODO overload this method so it can take TimberReferenceEnd as an argument, or allow TimberReferenceEnd to auto cast into TimberFace
    def get_face_direction(self, face: TimberFace) -> Direction3D:
        """
        Get the world direction vector for a specific face of this timber.
        
        Args:
            face: The face to get the direction for
            
        Returns:
            Direction vector pointing outward from the specified face in world coordinates
        """
        if face == TimberFace.TOP:
            return self.length_direction
        elif face == TimberFace.BOTTOM:
            return -self.length_direction
        elif face == TimberFace.RIGHT:
            return self.width_direction
        elif face == TimberFace.LEFT:
            return -self.width_direction
        elif face == TimberFace.FORWARD:
            return self.height_direction
        else:  # BACK
            return -self.height_direction
    
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
                TimberFace.LEFT, TimberFace.FORWARD, TimberFace.BACK]
        
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
        bottom_2d = create_vector2d(self.bottom_position[0], self.bottom_position[1])
        top_position = self.bottom_position + self.length_direction * self.length
        top_2d = create_vector2d(top_position[0], top_position[1])
        
        # Find nearest boundary to timber's centerline
        boundary_idx, boundary_side, distance = footprint.nearest_boundary_from_line(bottom_2d, top_2d)
        
        # Get the inward normal of that boundary
        inward_x, inward_y, inward_z = footprint.get_inward_normal(boundary_idx)
        inward_normal = create_vector3d(inward_x, inward_y, inward_z)
        
        # Find which face of the timber aligns with the inward direction
        return self.get_closest_oriented_face(inward_normal)

    # UNTESTED
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
        bottom_2d = create_vector2d(self.bottom_position[0], self.bottom_position[1])
        top_position = self.bottom_position + self.length_direction * self.length
        top_2d = create_vector2d(top_position[0], top_position[1])
        
        # Find nearest boundary to timber's centerline
        boundary_idx, boundary_side, distance = footprint.nearest_boundary_from_line(bottom_2d, top_2d)
        
        # Get the inward normal of that boundary
        inward_x, inward_y, inward_z = footprint.get_inward_normal(boundary_idx)
        inward_normal = create_vector3d(inward_x, inward_y, inward_z)
        
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

# ============================================================================
# Timber Creation Functions
# ============================================================================

def create_timber(bottom_position: V3, length: Numeric, size: V2, 
                  length_direction: Direction3D, width_direction: Direction3D) -> Timber:
    """
    Creates a timber at bottom_position with given dimensions and rotates it 
    to the length_direction and width_direction
    """
    return Timber(length, size, bottom_position, length_direction, width_direction)

def create_axis_aligned_timber(bottom_position: V3, length: Numeric, size: V2,
                              length_direction: TimberFace, width_direction: Optional[TimberFace] = None) -> Timber:
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
        print("WARNING: creating an axis-aligned timber with length_direction == BOTTOM. This is usually not what you want. Consider using length_direction == TOP instead.")
    
    width_vec = width_direction.get_direction()
    
    return create_timber(bottom_position, length, size, length_vec, width_vec)

def create_vertical_timber_on_footprint_corner(footprint: Footprint, corner_index: int, 
                                               length: Numeric, location_type: FootprintLocation,
                                               size: V2) -> Timber:
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
    length_direction = create_vector3d(0, 0, 1)
    
    # Align timber face direction with outgoing boundary side
    # Face direction is in the XY plane along the outgoing side
    width_direction = create_vector3d(outgoing_dir_normalized[0], outgoing_dir_normalized[1], 0)
    
    # Calculate bottom position based on location type
    # Keep corner coordinates exact
    corner_x = corner[0]
    corner_y = corner[1]
    
    if location_type == FootprintLocation.INSIDE:
        # Position so one vertex of bottom face is on the boundary corner
        # Post extends inside the boundary
        # The corner vertex is at the origin of the timber's local coords
        bottom_position = create_vector3d(corner_x, corner_y, 0)
        
    elif location_type == FootprintLocation.OUTSIDE:
        # Position so the opposite vertex is on the boundary corner
        # Need to offset by the full diagonal of the timber base
        # Offset = -timber_width in face direction, -timber_depth in perpendicular direction
        # Use exact arithmetic: outgoing_dir_normalized components are rationals for axis-aligned
        offset_x = -timber_width * outgoing_dir_normalized[0] - timber_depth * (-outgoing_dir_normalized[1])
        offset_y = -timber_width * outgoing_dir_normalized[1] - timber_depth * outgoing_dir_normalized[0]
        bottom_position = create_vector3d(corner_x + offset_x, corner_y + offset_y, 0)
        
    else:  # CENTER
        # Position so center of bottom face is on the boundary corner
        # Offset by half dimensions in both directions
        offset_x = -timber_width/2 * outgoing_dir_normalized[0] - timber_depth/2 * (-outgoing_dir_normalized[1])
        offset_y = -timber_width/2 * outgoing_dir_normalized[1] - timber_depth/2 * outgoing_dir_normalized[0]
        bottom_position = create_vector3d(corner_x + offset_x, corner_y + offset_y, 0)
    
    return create_timber(bottom_position, length, size, length_direction, width_direction)

def create_vertical_timber_on_footprint_side(footprint: Footprint, side_index: int, 
                                            distance_along_side: Numeric,
                                            length: Numeric, location_type: FootprintLocation, 
                                            size: V2) -> Timber:
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
    test_point = Matrix([point_x + perp_x * Rational(1, 1000),
                        point_y + perp_y * Rational(1, 1000)])
    
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
    length_direction = create_vector3d(0, 0, 1)
    
    # Face direction is parallel to the boundary side
    width_direction = create_vector3d(side_dir_normalized[0], side_dir_normalized[1], 0)
    
    # Calculate bottom position based on location type
    if location_type == FootprintLocation.CENTER:
        # Center of bottom face is on the point
        # No offset needed since timber local origin is at center of bottom face
        bottom_position = create_vector3d(point_x, point_y, 0)
        
    elif location_type == FootprintLocation.INSIDE:
        # One edge of bottom face lies on boundary side
        # Center of that edge is at the point
        # Post extends inside (in direction of inward normal)
        # Offset the center by half depth in the inward direction
        bottom_position = create_vector3d(point_x + inward_x * timber_depth / 2, 
                                         point_y + inward_y * timber_depth / 2, 
                                         0)
        
    else:  # OUTSIDE
        # One edge of bottom face lies on boundary side
        # Center of that edge is at the point
        # Post extends outside (opposite of inward normal)
        # Offset the center by half depth in the outward direction
        bottom_position = create_vector3d(point_x - inward_x * timber_depth / 2, 
                                         point_y - inward_y * timber_depth / 2, 
                                         0)
    
    return create_timber(bottom_position, length, size, length_direction, width_direction)

def create_horizontal_timber_on_footprint(footprint: Footprint, corner_index: int,
                                        location_type: FootprintLocation, 
                                        size: V2,
                                        length: Optional[Numeric] = None) -> Timber:
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
    inward_normal = create_vector3d(inward_x, inward_y, inward_z)
    
    # Face direction is up (Z+)
    width_direction = create_vector3d(0, 0, 1)
    
    # The timber's orientation will be:
    #   X-axis (width/size[0]) = width_direction = (0, 0, 1) = vertical (up)
    #   Y-axis (height/size[1]) = length × face = perpendicular to boundary in XY plane
    #   Z-axis (length) = length_direction = along boundary side
    # Therefore, size[1] is the dimension perpendicular to the boundary
    timber_height = size[1]
    
    # Calculate bottom position based on location type
    # Start at the start_point on the boundary side - keep exact
    bottom_position = create_vector3d(start_point[0], start_point[1], 0)
    
    # Apply offset based on location type
    if location_type == FootprintLocation.INSIDE:
        # Position so one edge lies on the boundary side, timber extends inward
        # Move the centerline inward by half the timber height (perpendicular dimension)
        bottom_position = bottom_position + inward_normal * (timber_height / 2)
    elif location_type == FootprintLocation.OUTSIDE:
        # Position so one edge lies on the boundary side, timber extends outward
        # Move the centerline outward by half the timber height (perpendicular dimension)
        bottom_position = bottom_position - inward_normal * (timber_height / 2)
    # For CENTER, no offset needed - centerline is already on the boundary side
    
    return create_timber(bottom_position, length, size, length_direction, width_direction)

def extend_timber(timber: Timber, end: TimberReferenceEnd, overlap_length: Numeric, 
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
        extension_vector = timber.length_direction * (timber.length - overlap_length)
        new_bottom_position = timber.bottom_position + extension_vector
    else:  # BOTTOM
        # Extend from bottom
        extension_vector = timber.length_direction * extend_length
        new_bottom_position = timber.bottom_position - extension_vector
    
    # Create new timber with extended length
    new_length = timber.length + extend_length + overlap_length
    
    return Timber(new_length, timber.size, new_bottom_position, 
                 timber.length_direction, timber.width_direction)

# TODO add some sorta splice stickout parameter
def split_timber(timber: Timber, distance_from_bottom: Numeric) -> Tuple[Timber, Timber]:
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
    
    # Create first timber (bottom part)
    bottom_timber = Timber(
        length=distance_from_bottom,
        size=create_vector2d(timber.size[0], timber.size[1]),
        bottom_position=timber.bottom_position,
        length_direction=timber.length_direction,
        width_direction=timber.width_direction
    )
    bottom_timber.name = f"{timber.name}_bottom" if timber.name else "split_bottom"
    
    # Calculate the bottom position of the second timber
    # It's at the top of the first timber
    top_of_first = timber.bottom_position + distance_from_bottom * timber.length_direction
    
    # Create second timber (top part)
    top_timber = Timber(
        length=timber.length - distance_from_bottom,
        size=create_vector2d(timber.size[0], timber.size[1]),
        bottom_position=top_of_first,
        length_direction=timber.length_direction,
        width_direction=timber.width_direction
    )
    top_timber.name = f"{timber.name}_top" if timber.name else "split_top"
    
    return (bottom_timber, top_timber)

def join_timbers(timber1: Timber, timber2: Timber, 
                location_on_timber1: Numeric,
                location_on_timber2: Optional[Numeric] = None,
                lateral_offset: Numeric = Integer(0),
                stickout: Stickout = Stickout.nostickout(),
                size: Optional[V2] = None,
                orientation_width_vector: Optional[Direction3D] = None) -> Timber:
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
        
    Returns:
        New timber connecting timber1 and timber2 along their centerlines
    """
    # Calculate position on timber1
    pos1 = timber1.get_centerline_position_from_bottom(location_on_timber1)
    
    # Calculate position on timber2
    if location_on_timber2 is not None:
        pos2 = timber2.get_centerline_position_from_bottom(location_on_timber2)
    else:
        # Project location_on_timber1 to timber2's Z axis
        pos2 = Matrix([pos1[0], pos1[1], timber2.bottom_position[2] + location_on_timber1])
    
    # Calculate length direction (from timber1 to timber2)
    length_direction = pos2 - pos1
    length_direction = normalize_vector(length_direction)
    
    # Calculate face direction (width direction for the created timber)
    if orientation_width_vector is not None:
        reference_direction = orientation_width_vector
    else:
        # Default: use timber1's length direction
        reference_direction = timber1.length_direction
    
    # Check if reference direction is parallel to the joining direction
    if _are_directions_parallel(reference_direction, length_direction):
        # If parallel, cannot project - use a perpendicular fallback
        if orientation_width_vector is not None:
            print(f"WARNING: orientation_width_vector {orientation_width_vector} is parallel to the joining direction {length_direction}. Using timber1's width direction instead.")
            reference_direction = timber1.width_direction
        else:
            print("WARNING: timber1's length direction is parallel to the joining direction. Using timber1's width direction instead.")
            reference_direction = timber1.width_direction
    
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
        dot_product = Abs(width_direction.dot(timber1.length_direction))
        
        if dot_product < Rational(1, 2):  # < 0.5, meaning more perpendicular than parallel
            # The created timber is joining perpendicular to timber1
            # Its X dimension (width, along width_direction) should match the dimension 
            # of the face it's joining to on timber1, which is timber1's width (size[0])
            size = create_vector2d(timber1.size[0], timber1.size[1])
        else:
            # For other orientations, use timber1's size as-is
            size = create_vector2d(timber1.size[0], timber1.size[1])
    
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
        offset_dir = normalize_vector(cross_product(timber1.length_direction, length_direction))
    
    # Calculate the bottom position (start of timber)
    # Start from pos1 and move backward by stickout1 (always centerline)
    bottom_pos = pos1 - length_direction * stickout.stickout1
    
    # Apply offset to bottom position as well (if any offset was applied to center)
    if lateral_offset != 0:
        bottom_pos += offset_dir * lateral_offset
    
    return create_timber(bottom_pos, timber_length, size, length_direction, width_direction)

def join_perpendicular_on_face_parallel_timbers(timber1: Timber, timber2: Timber,
                                                location_on_timber1: Numeric,
                                                stickout: Stickout,
                                                offset_from_timber1: FaceAlignedJoinedTimberOffset,
                                                size: V2,
                                                orientation_face_on_timber1: Optional[TimberFace] = None) -> Timber:
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
        
    Returns:
        New timber that joins timber1 and timber2
    """
    # Verify that the two timbers are face-aligned
    assert _are_timbers_face_aligned(timber1, timber2), \
        "timber1 and timber2 must be face-aligned (share at least one parallel direction)"
    
    # Auto-determine size if not provided
    if size is None:
        # Use timber1's size as the default
        size = timber1.size
    
    # Calculate position on timber1
    pos1 = timber1.get_centerline_position_from_bottom(location_on_timber1)
    
    # Project pos1 onto timber2's centerline to find location_on_timber2
    # Vector from timber2's bottom to pos1
    to_pos1 = pos1 - timber2.bottom_position
    
    # Project this onto timber2's length direction to find the parameter t
    location_on_timber2 = to_pos1.dot(timber2.length_direction) / timber2.length_direction.dot(timber2.length_direction)
    
    # Clamp location_on_timber2 to be within the timber's length
    location_on_timber2 = max(0, min(timber2.length, location_on_timber2))
    
    # Convert TimberFace to a direction vector for orientation (if provided)
    orientation_width_vector = orientation_face_on_timber1.get_direction() if orientation_face_on_timber1 is not None else None
    
    # Extract the centerline offset (use 0 if not provided)
    offset_value = offset_from_timber1.centerline_offset if offset_from_timber1.centerline_offset is not None else 0
    
    # Convert INSIDE/OUTSIDE stickout references to CENTER_LINE
    # For face-aligned timbers, we know the joining direction
    pos2 = timber2.get_centerline_position_from_bottom(location_on_timber2)
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
            face_dot = Abs(orientation_width_vector.dot(timber1.length_direction))
            height_dot = Abs(height_direction.dot(timber1.length_direction))
            
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
        size=size
    )

# ============================================================================
# Joint Construction Functions
# ============================================================================

class JointAccessory:
    """Base class for joint accessories like wedges, drawbores, etc."""
    pass

class Joint:
    partiallyCutTimbers : List['PartiallyCutTimber']
    jointAccessories : List[JointAccessory]


class BasicMiterJoint(Joint):
    """
    A basic miter joint between two timbers such that the 2 ends meet at a 90 degree angle miter corner.
    """
    def __init__(self, timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd):
        super().__init__()
        self.timberA = timberA
        self.timberA_end = timberA_end
        self.timberB = timberB

def cut_basic_miter_joint_on_face_aligned_timbers(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic miter joint between two timbers such that the 2 ends meet at a 90 degree angle miter corner.
    """
    # TODO assert length axis are perpendicular
    # TODO
    return None
    

def cut_basic_end_joint_on_face_aligned_timbers(timberA: Timber, timberA_end: TimberReferenceEnd, timberB: Timber, timberB_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic end joint between two timbers such that the 2 ends meet at a 90 degree angle corner.
    """
    return cut_basic_miter_joint_on_face_aligned_timbers(timberA, timberA_end, timberB, timberB_end)



def cut_basic_butt_joint_on_face_aligned_timbers(receiving_timber: Timber, butt_timber: Timber, butt_end: TimberReferenceEnd) -> Joint:
    """
    Creates a basic butt joint between two timbers. The butt timber is extended to meet the face of the receiving timber.
    """
    assert _are_timbers_face_aligned(shoulder_timber, butt_timber), \
        "Timbers must be face-aligned (orientations related by 90-degree rotations) for this joint type"
    # TODO
    return None


def cut_basic_splice_joint_on_aligned_timbers(timberA: Timber, timberB: Timber) -> Joint:
    """
    Creates a basic splice joint between two timbers. The butt timber is extended to meet the face of the receiving timber.
    """
    # TODO assert length axis are parallel 
    # TODO check that timber cross sections overlap and if not, output a warning
    # TODO
    return None



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
    
    # Create the joint
    joint = Joint()
    
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
    

# ============================================================================
# Helper Functions
# ============================================================================


def _has_rational_components(vector: Direction3D) -> bool:
    """
    Check if a direction vector contains only rational (exact) components.
    
    Args:
        vector: Direction vector to check
        
    Returns:
        True if all components are integers or rationals, False otherwise
    """
    for i in range(3):
        val = vector[i]
        if not isinstance(val, (int, Integer, Rational)):
            return False
    return True

def _are_timbers_face_parallel(timber1: Timber, timber2: Timber, tolerance: Optional[Numeric] = None) -> bool:
    """
    Check if two timbers have parallel length directions.
    
    Args:
        timber1: First timber
        timber2: Second timber
        tolerance: Optional tolerance for approximate comparison. If None, automatically
                   uses exact comparison for rational values or fuzzy comparison for floats.
                   
    Returns:
        True if timbers have parallel length directions, False otherwise
    """
    # Check if all components are rational
    is_rational = (_has_rational_components(timber1.length_direction) and 
                   _has_rational_components(timber2.length_direction))
    
    dot_product = Abs(timber1.length_direction.dot(timber2.length_direction))
    
    if tolerance is None:
        if is_rational:
            # Use exact comparison with simplify for symbolic math
            return simplify(dot_product - 1) == 0
        else:
            # Auto-use tolerance for float values
            tolerance = 1e-10
            return Abs(dot_product - 1) < tolerance
    else:
        # Use provided tolerance
        return Abs(dot_product - 1) < tolerance

def _are_timbers_face_orthogonal(timber1: Timber, timber2: Timber, tolerance: Optional[Numeric] = None) -> bool:
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
    # Check if all components are rational
    is_rational = (_has_rational_components(timber1.length_direction) and 
                   _has_rational_components(timber2.length_direction))
    
    dot_product = timber1.length_direction.dot(timber2.length_direction)
    
    if tolerance is None:
        if is_rational:
            # Use exact comparison with simplify for symbolic math
            return simplify(dot_product) == 0
        else:
            # Auto-use tolerance for float values
            tolerance = 1e-10
            return Abs(dot_product) < tolerance
    else:
        # Use provided tolerance
        return Abs(dot_product) < tolerance

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
    # Check if all components are rational
    is_rational = (_has_rational_components(direction1) and 
                   _has_rational_components(direction2))
    
    dot_product = direction1.dot(direction2)
    
    if tolerance is None:
        if is_rational:
            # Use exact comparison with simplify for symbolic math
            return simplify(dot_product) == 0
        else:
            # Auto-use tolerance for float values
            tolerance = 1e-10
            return Abs(dot_product) < tolerance
    else:
        # Use tolerance for approximate comparison
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
    # Check if all components are rational
    is_rational = (_has_rational_components(direction1) and 
                   _has_rational_components(direction2))
    
    dot_product = direction1.dot(direction2)
    dot_mag = Abs(dot_product)
    
    if tolerance is None:
        if is_rational:
            # Use exact comparison with simplify for symbolic math
            return simplify(dot_mag - 1) == 0
        else:
            # Auto-use tolerance for float values
            tolerance = 1e-10
            return abs(float(dot_mag) - 1.0) < tolerance
    else:
        # Use provided tolerance
        return abs(float(dot_mag) - 1.0) < tolerance

def _are_timbers_face_aligned(timber1: Timber, timber2: Timber, tolerance: Optional[Numeric] = None) -> bool:
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
    dirs1 = [timber1.length_direction, timber1.width_direction, timber1.height_direction]
    dirs2 = [timber2.length_direction, timber2.width_direction, timber2.height_direction]
    
    # Check if all values are rational (exact)
    all_rational = all(_has_rational_components(direction) for direction in dirs1 + dirs2)
    
    if tolerance is None and not all_rational:
        import warnings
        warnings.warn(
            "Using exact equality check for face alignment but timber direction vectors "
            "contain non-rational values (e.g., Float). Consider using exact Rational types "
            "or providing a tolerance parameter for approximate comparison.",
            UserWarning
        )
        # Auto-use a small tolerance when Float values are present
        effective_tolerance = 1e-10
    else:
        effective_tolerance = tolerance
    
    if effective_tolerance is None:
        # Use exact equality check (only for rational values)
        for dir1 in dirs1:
            for dir2 in dirs2:
                dot_product = Abs(dir1.dot(dir2))
                if dot_product == 1:
                    return True
    else:
        # Use tolerance-based comparison
        for dir1 in dirs1:
            for dir2 in dirs2:
                dot_product = Abs(dir1.dot(dir2))
                # Convert to float for numerical comparison
                if abs(float(dot_product) - 1.0) < effective_tolerance:
                    return True
    
    return False

def _project_point_on_timber_centerline(point: V3, timber: Timber) -> Tuple[Numeric, V3]:
    """
    Project a point onto a timber's centerline.
    
    Args:
        point: 3D point to project
        timber: Timber whose centerline to project onto
        
    Returns:
        Tuple of (parameter_t, projected_point) where:
        - parameter_t: Distance along timber from bottom_position (can be negative or > length)
        - projected_point: The actual projected point on the centerline
    """
    # Vector from timber's bottom to the point
    to_point = point - timber.bottom_position
    
    # Project this vector onto the timber's length direction
    length_dir = timber.length_direction
    t = to_point.dot(length_dir) / length_dir.dot(length_dir)
    
    # Calculate the projected point
    projected_point = timber.bottom_position + timber.length_direction * t
    
    return t, projected_point

def _calculate_mortise_position_from_tenon_intersection(mortise_timber: Timber, tenon_timber: Timber, tenon_end: TimberReferenceEnd) -> Tuple[TimberReferenceEnd, Numeric]:
    """
    Calculate the mortise position based on where the tenon timber intersects the mortise timber.
    
    Args:
        mortise_timber: Timber that will receive the mortise
        tenon_timber: Timber that will have the tenon
        tenon_end: Which end of the tenon timber the tenon comes from
        
    Returns:
        Tuple of (reference_end, distance) for the mortise position
    """
    # Get the tenon end point
    if tenon_end == TimberReferenceEnd.TOP:
        tenon_point = tenon_timber.bottom_position + tenon_timber.length_direction * tenon_timber.length
    else:  # BOTTOM
        tenon_point = tenon_timber.bottom_position
    
    # Project the tenon point onto the mortise timber's centerline
    t, projected_point = _project_point_on_timber_centerline(tenon_point, mortise_timber)
    
    # Clamp t to be within the mortise timber's length
    t = max(0, min(mortise_timber.length, t))
    
    # Determine which end to reference based on which is closer
    distance_from_bottom = t
    distance_from_top = mortise_timber.length - t
    
    if distance_from_bottom <= distance_from_top:
        return TimberReferenceEnd.BOTTOM, distance_from_bottom
    else:
        return TimberReferenceEnd.TOP, distance_from_top


def _calculate_distance_from_timber_end_to_shoulder_plane(tenon_timber: Timber, mortise_timber: Timber, tenon_end: TimberReferenceEnd) -> Numeric:
    """
    Calculate the distance from the tenon timber end to where the shoulder plane should be positioned.
    The shoulder plane should be at the face where the tenon timber meets the mortise timber.
    
    This function works for both aligned and misaligned timber configurations by:
    1. Finding where the tenon timber centerline intersects the mortise timber
    2. Calculating the position of the mortise timber face at that intersection
    3. Measuring the distance from the tenon end to that face along the tenon centerline
    
    Args:
        tenon_timber: Timber that will have the tenon
        mortise_timber: Timber that will receive the mortise
        tenon_end: Which end of the tenon timber the tenon comes from
        
    Returns:
        Distance from the tenon timber end to the shoulder plane position
    """
    # Get the tenon end point (where tenon starts)
    if tenon_end == TimberReferenceEnd.TOP:
        tenon_end_point = tenon_timber.bottom_position + tenon_timber.length_direction * tenon_timber.length
    else:  # BOTTOM
        tenon_end_point = tenon_timber.bottom_position
    
    # Project tenon end point onto mortise timber centerline to find intersection
    t, projected_point = _project_point_on_timber_centerline(tenon_end_point, mortise_timber)
    
    # Get the face direction from mortise timber to tenon timber
    tenon_end_direction = tenon_timber.get_face_direction(TimberFace.TOP if tenon_end == TimberReferenceEnd.TOP else TimberFace.BOTTOM)
    mortise_face = mortise_timber.get_closest_oriented_face(-tenon_end_direction)
    
    # Calculate the distance from mortise centerline to mortise face
    if mortise_face in [TimberFace.RIGHT, TimberFace.LEFT]:
        # X direction faces
        face_offset = mortise_timber.size[0] / 2  # Half width
    elif mortise_face in [TimberFace.FORWARD, TimberFace.BACK]:
        # Y direction faces  
        face_offset = mortise_timber.size[1] / 2  # Half height
    else:
        # TOP/BOTTOM faces (shouldn't happen for typical tenon joints)
        assert False, "TOP/BOTTOM faces shouldn't happen for typical tenon joints"
    
    # Calculate the actual position of the mortise face at the intersection point
    width_vector = mortise_face.get_direction()
    mortise_face_point = projected_point + create_vector3d(width_vector[0], width_vector[1], width_vector[2]) * face_offset
    
    # Calculate the distance from tenon end to where the shoulder plane should be
    # 
    # The key insight is that the shoulder plane should be positioned at the mortise face,
    # but we need to measure the distance along the tenon timber centerline.
    #
    # For misaligned timbers, we need to find where the tenon centerline would intersect 
    # the plane containing the mortise face at the projected intersection point.
    
    face_normal = create_vector3d(width_vector[0], width_vector[1], width_vector[2])
    
    # Check if tenon direction is perpendicular to mortise face normal
    direction_dot_normal = tenon_timber.length_direction.dot(face_normal)
    
    if abs(direction_dot_normal) < 1e-6:
        # Case 1: Tenon direction is perpendicular to mortise face (typical orthogonal joints)
        # Calculate distance from tenon end to projected point plus face offset
        
        # Distance from tenon end to the intersection point along tenon centerline
        to_intersection = projected_point - tenon_end_point
        distance_to_intersection = abs(to_intersection.dot(tenon_timber.length_direction))
        
        # Distance to shoulder plane = distance to intersection + face offset
        # This works for both aligned and misaligned cases
        distance_along_tenon = distance_to_intersection + face_offset
        
    else:
        # Case 2: Tenon direction is not perpendicular to mortise face
        # Use line-plane intersection to find where tenon centerline meets mortise face plane
        
        point_to_plane = tenon_end_point - mortise_face_point
        t = -point_to_plane.dot(face_normal) / direction_dot_normal
        
        # The distance from tenon end to shoulder plane is |t|
        distance_along_tenon = abs(t)
    
    return distance_along_tenon
  




# SCRATCH AREA FOR NEW JOINT OPERATIONS

class Cut:
    # debug reference to the base timber we are cutting
    # each Cut is tied to a timber so this is very reasonable to store here
    _timber : Timber

    # set these values by computing them relative to the timber features using helper functions 
    origin : V3
    orientation : Orientation

    # end cuts are special as they set the length of the timber
    maybeEndCut : Optional[TimberReferenceEnd]


    # get the "end" position of the cut on the centerline of the timber
    # the "end" position should be the minimal (as in closest to the other end) such point on the centerline of the timber such that the entire timber lies on one side of the orthogonal plane (to the centerline) through the end position
    @abstractmethod
    def get_end_position(self) -> V3:
        if self.maybeEndCut == TimberReferenceEnd.TOP:
            return self._timber.bottom_position + self._timber.length_direction * self._timber.length
        elif self.maybeEndCut == TimberReferenceEnd.BOTTOM:
            return self._timber.bottom_position
        else:
            raise ValueError(f"Invalid end cut: {self.maybeEndCut}")

    # returns the negative CSG of the cut (the part of the timber that is removed by the cut)
    @abstractmethod
    def get_negative_csg(self) -> MeowMeowCSG:
        pass


class CutTimber:
    def __init__(self, timber: Timber, name: str = None):
        """
        Create a CutTimber from a Timber.
        
        Args:
            timber: The timber to be cut
            name: Optional name for this timber (used for rendering/debugging)
        """
        self._timber = timber
        self._cuts = []
        self.name = name
        self.joints = []  # List of joints this timber participates in
    
    @property
    def timber(self) -> Timber:
        """Get the underlying timber."""
        return self._timber

    # this one returns the timber without cuts where ends with joints are infinite in length
    def _extended_timber_without_cuts_csg(self) -> MeowMeowCSG:
        """
        Returns a CSG representation of the timber without any cuts applied.
        
        If an end has cuts on it (indicated by maybeEndCut), that end is extended to infinity.
        This allows joints to extend the timber as needed during the CSG cutting operations.
        
        Returns:
            Prism CSG representing the timber (possibly semi-infinite or infinite)
        """
        from meowmeowcsg import create_prism
        
        # Check if bottom end has cuts
        has_bottom_cut = any(
            cut.maybeEndCut == TimberReferenceEnd.BOTTOM 
            for cut in self._cuts
        )
        
        # Check if top end has cuts  
        has_top_cut = any(
            cut.maybeEndCut == TimberReferenceEnd.TOP
            for cut in self._cuts
        )
        
        # Normalize the length direction
        length_dir_norm = normalize_vector(self._timber.length_direction)
        
        # Compute the distance from origin to bottom along the length direction
        # This is the projection of bottom_position onto length_direction
        bottom_distance = (self._timber.bottom_position.T * length_dir_norm)[0, 0]
        
        # Top distance is bottom_distance + length
        top_distance = bottom_distance + self._timber.length
        
        # Determine start and end distances in absolute coordinates
        # If an end has cuts, it extends to infinity in that direction
        start_distance = None if has_bottom_cut else bottom_distance
        end_distance = None if has_top_cut else top_distance
        
        # Create a prism representing the timber
        return create_prism(
            size=self._timber.size,
            orientation=self._timber.orientation,
            start_distance=start_distance,
            end_distance=end_distance
        )

    # this one returns the timber without cuts where ends with joints are cut to length based on Cut::get_end_position
    # use this for rendering the timber without cuts for development
    def render_timber_without_cuts_csg(self) -> MeowMeowCSG:
        # TODO
        # first find all cuts that are end cuts
        # assert that each end has no more than one end cut
        # for each end, if there is an end cut, use Cut::get_end_position to get the end position otherwise use the timber's original end position
        # finally construct a possible infinite in either end prism CSG and return it
        pass

    # thi sone returns the timber with all cuts applied
    def render_timber_with_cuts_csg(self) -> MeowMeowCSG:
        starting_csg = self._extended_timber_without_cuts_csg()
        # TODO difference each cut from starting_CSG?
        pass

class PartiallyCutTimber(CutTimber):
    pass

