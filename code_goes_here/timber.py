"""
GiraffeCAD - Timber types, enums, constants, and core classes
Contains all core data structures and type definitions for the timber framing system
"""

from sympy import Matrix, Abs, Rational, Integer, Expr, sqrt, simplify
from .moothymoth import Orientation
from .footprint import Footprint
from .meowmeowcsg import MeowMeowCSG, HalfPlane, Prism, Cylinder, Union as CSGUnion, Difference as CSGDifference
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
# Constants
# ============================================================================

# TODO refine these ab it, be more consistent abotu float vs rationals here
# TODO also make sure that sympy can easily compare float with rational and vice versa... 
# TODO maybe better to have helper functions for all of these comparisons especially if the answer for the above is no
# Epsilon values for numerical comparisons
# TODO name this EPISLOT_FLOAT_PARALLEL
EPSILON_FLOAT = 1e-10  # Tolerance for float comparisons (orthogonality, alignment checks)
# TODO DELETE relpace with the above, this is just perpendicular check epsilon
EPSILON_DIRECTION = 1e-6  # Tolerance for direction dot product checks
EPSILON_PARALLEL = Rational(1, 1000)  # Threshold for checking if vectors are nearly parallel/perpendicular (0.001)
EPSILON_DEGENERATE = Rational(1, 10000)  # Threshold for detecting degenerate geometric cases (0.0001)
EPSILON_PLANE_PARALLEL = Rational(1, 100000)  # Threshold for detecting if plane is parallel to centerline (0.00001)

# Thresholds for geometric decisions
THRESHOLD_PERPENDICULAR_VS_PARALLEL = Rational(1, 2)  # Threshold (0.5) for determining if joining timber is more perpendicular than parallel
THRESHOLD_SKEW_LINE_WARNING = Rational(1, 10)  # Distance threshold (0.1) for issuing skew line warning
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
# Joint Construction Data Structures
# ============================================================================

class DistanceFromFace:
    face: TimberFace
    distance: Numeric
@dataclass
class DistanceFromLongFace:
    face: TimberReferenceLongFace
    distance: Numeric
@dataclass
class DistanceFromEnd:
    end: TimberReferenceEnd
    distance: Numeric
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

    

# TODO write better comments or give this a better name. wtf is this?
@dataclass
class FaceAlignedJoinedTimberOffset:
    reference_face: TimberFace
    centerline_offset: Optional[Numeric]
    face_offset: Optional[Numeric]


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
                 length_direction: Direction3D, width_direction: Direction3D, name: Optional[str] = None):
        """
        Args:
            length: Length of the timber
            size: Cross-sectional size (width, height) as 2D vector, width is the X dimension (left to right), height is the Y dimension (front to back)
            bottom_position: Position of the bottom point (center of cross-section) as 3D vector
            length_direction: Direction vector for the length axis as 3D vector, the +length direction is the +Z direction
            width_direction: Direction vector for the width axis as 3D vector, the +width direction is the +X direction
            name: Optional name for this timber (used for rendering/debugging)
        """
        self.length: Numeric = length
        self.size: V2 = size
        self.bottom_position: V3 = bottom_position
        self.name: Optional[str] = name
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
        if face_orthogonal.norm() < EPSILON_FLOAT:
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
    
    def get_bottom_center_position(self) -> V3:
        """
        Get the 3D position of the center of the bottom cross-section of the timber.
        
        Returns:
            3D position vector at the center of the bottom cross-section
        """
        return self.bottom_position
    
    def get_top_center_position(self) -> V3:
        """
        Get the 3D position of the center of the top cross-section of the timber.
        
        Returns:
            3D position vector at the center of the top cross-section
        """
        return self.bottom_position + self.length_direction * self.length
    
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
        top_position = self.get_top_center_position()
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
        top_position = self.get_top_center_position()
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
# Joint Related Types and Functions
# ============================================================================


class Cut:
    # debug reference to the base timber we are cutting
    # each Cut is tied to a timber so this is very reasonable to store here
    _timber : Timber

    # set these values by computing them relative to the timber features using helper functions 
    origin : V3
    orientation : Orientation

    # end cuts are special as they set the length of the timber
    # you can only have an end cut on one end of the timber, you can't have an end cut on both ends at once (maybe we should support this?)
    maybeEndCut : Optional[TimberReferenceEnd]

    def __init__(self, timber: Timber, origin: V3, orientation: Orientation, 
                 maybe_end_cut: Optional[TimberReferenceEnd] = None):
        """
        Create a Cut with all required parameters.
        
        Args:
            timber: The timber being cut
            origin: Origin point of the cut
            orientation: Orientation of the cut
            maybe_end_cut: Optional end cut designation (TOP or BOTTOM)
        """
        self._timber = timber
        self.origin = origin
        self.orientation = orientation
        self.maybeEndCut = maybe_end_cut

    # get the "end" position of the cut on the centerline of the timber
    # the "end" position should be the minimal (as in closest to the other end) such point on the centerline of the timber such that the entire timber lies on one side of the orthogonal plane (to the centerline) through the end position
    def get_end_position(self) -> V3:
        """
        Determine the end position of the cut by finding where the cut intersects the timber.
        
        This is computed by:
        1. Getting the negative CSG (the cut volume)
        2. Intersecting it with the timber's finite prism (to constrain the cut to the timber bounds)
        3. Finding the minimal boundary of this intersection
        4. Projecting onto the timber's centerline
        
        The returned point is on the timber's centerline at the distance where the cut boundary is located.
        
        Returns:
            The end position on the timber's centerline where the cut intersects
            
        Raises:
            ValueError: If maybeEndCut is None (this cut is not an end cut)
        """
        if self.maybeEndCut is None:
            raise ValueError("get_end_position can only be called on end cuts (maybeEndCut must be set)")
        
        # Get the negative CSG representing the cut volume (in LOCAL coordinates)
        negative_csg = self.get_negative_csg()
        
        # Get the timber prism in LOCAL coordinates (semi-infinite at this end since we pass [self])
        timber_prism = _create_timber_prism_csg_local(self._timber, [self])
        
        # The timber with the cut applied: timber - cut_volume
        from .meowmeowcsg import Difference, HalfPlane
        cut_result = Difference(timber_prism, [negative_csg])
        
        # Determine the search direction based on which end is being cut
        # Search direction is in the timber's LOCAL coordinate system
        # In local coords, the timber's length direction is the Z-axis (third column of orientation matrix)
        # But since we're working in the timber's local space where it's axis-aligned,
        # we use the GLOBAL length_direction as the search direction in the LOCAL CSG space
        if self.maybeEndCut == TimberReferenceEnd.TOP:
            # For top end cuts, find the point closest to bottom (minimum distance along length)
            # To minimize the distance, search in the +length_direction
            search_direction = self._timber.length_direction
        elif self.maybeEndCut == TimberReferenceEnd.BOTTOM:
            # For bottom end cuts, find the point closest to top (maximum distance along length)
            # To maximize the distance, search in the -length_direction
            search_direction = -self._timber.length_direction
        else:
            raise ValueError(f"Invalid end cut: {self.maybeEndCut}")
        
        # For HalfPlane cuts, we can directly compute the intersection with the centerline
        # rather than using minimal_boundary_in_direction (which only works for certain directions)
        if isinstance(negative_csg, HalfPlane):
            # HalfPlane is in LOCAL coordinates (oriented basis) relative to timber.bottom_position
            # In the timber's LOCAL coordinate system:
            # - The centerline is along the Z-axis: P_local(t) = (0, 0, t)
            # - The length direction is (0, 0, 1) in local coordinates
            # The half-plane is: local_normal · P_local >= local_offset
            # At the boundary: local_normal · P_local = local_offset
            # Substituting: local_normal · (0, 0, t) = local_offset
            # This gives: local_normal[2] * t = local_offset
            # Solving for t: t = local_offset / local_normal[2]
            
            local_normal = negative_csg.normal
            local_offset = negative_csg.offset
            
            # The Z-component of the local normal (dot product with local length direction (0,0,1))
            normal_z_component = local_normal[2, 0]
            
            if abs(normal_z_component) < EPSILON_PLANE_PARALLEL:
                # Plane is parallel to the timber - no unique intersection
                raise ValueError("Cut plane is parallel to timber centerline")
            
            # Distance along centerline in local coordinates (along Z-axis)
            t = local_offset / normal_z_component
            
            # Convert back to global coordinates
            # In global coords: end_position = bottom_position + t * length_direction
            length_dir_norm = normalize_vector(self._timber.length_direction)
            end_position = self._timber.bottom_position + length_dir_norm * t
            
            return end_position
        else:
            # For other CSG types, use minimal_boundary_in_direction
            boundary_point = cut_result.minimal_boundary_in_direction(search_direction)
            
            # Project the boundary point onto the timber's centerline to get the end position
            # The end position is at: bottom_position + length_direction * distance
            # where distance = (boundary_point - bottom_position) · length_direction / |length_direction|^2
            length_dir_norm = normalize_vector(self._timber.length_direction)
            distance_along_centerline = ((boundary_point - self._timber.bottom_position).T * length_dir_norm)[0, 0]
            
            end_position = self._timber.bottom_position + length_dir_norm * distance_along_centerline
            
            return end_position

    # returns the negative CSG of the cut (the part of the timber that is removed by the cut)
    @abstractmethod
    def get_negative_csg(self) -> MeowMeowCSG:
        pass


def _create_timber_prism_csg_local(timber: Timber, cuts: list) -> MeowMeowCSG:
    """
    Helper function to create a prism CSG for a timber in LOCAL coordinates, 
    optionally extending ends with cuts to infinity.
    
    LOCAL coordinates means distances are relative to timber.bottom_position.
    This is used for rendering (where the prism is created at origin and then transformed)
    and for CSG operations (where cuts are also in local coordinates).
    
    Args:
        timber: The timber to create a prism for
        cuts: List of cuts on this timber (used to determine if ends should be infinite)
        
    Returns:
        Prism CSG representing the timber (possibly semi-infinite or infinite) in LOCAL coordinates
    """
    from .meowmeowcsg import create_prism
    
    # Check if bottom end has cuts
    has_bottom_cut = any(
        cut.maybeEndCut == TimberReferenceEnd.BOTTOM 
        for cut in cuts
    )
    
    # Check if top end has cuts  
    has_top_cut = any(
        cut.maybeEndCut == TimberReferenceEnd.TOP
        for cut in cuts
    )
    
    # In local coordinates:
    # - bottom is at 0
    # - top is at timber.length
    # - if an end has cuts, extend to infinity in that direction
    
    start_distance = None if has_bottom_cut else 0
    end_distance = None if has_top_cut else timber.length
    
    # Create a prism representing the timber in local coordinates
    return create_prism(
        size=timber.size,
        orientation=Orientation.identity(),
        start_distance=start_distance,
        end_distance=end_distance
    )


class CutTimber:
    def __init__(self, timber: Timber, cuts: List['Cut'] = None):
        """
        Create a CutTimber from a Timber.
        
        Args:
            timber: The timber to be cut
            cuts: Optional list of cuts to apply (default: empty list)
        """
        self._timber = timber
        self._cuts = cuts if cuts is not None else []
        self.joints = []  # List of joints this timber participates in
    
    @property
    def timber(self) -> Timber:
        """Get the underlying timber."""
        return self._timber

    @property
    def name(self) -> Optional[str]:
        """Get the name from the underlying timber."""
        return self._timber.name

    # this one returns the timber without cuts where ends with joints are infinite in length
    def _extended_timber_without_cuts_csg(self) -> MeowMeowCSG:
        """
        Returns a CSG representation of the timber without any cuts applied.
        
        If an end has cuts on it (indicated by maybeEndCut), that end is extended to infinity.
        This allows joints to extend the timber as needed during the CSG cutting operations.
        
        Uses LOCAL coordinates (relative to timber.bottom_position).
        All cuts on this timber are also in LOCAL coordinates.
        
        Returns:
            Prism CSG representing the timber (possibly semi-infinite or infinite) in LOCAL coordinates
        """
        return _create_timber_prism_csg_local(self._timber, self._cuts)

    # this one returns the timber without cuts where ends with joints are cut to length based on Cut::get_end_position
    # use this for rendering the timber without cuts for development
    def render_timber_without_cuts_csg(self) -> MeowMeowCSG:
        """
        Returns a CSG representation of the timber without cuts applied, but with ends
        positioned according to any end cuts.
        
        If an end has an end cut, the timber is cut to the position returned by
        Cut::get_end_position(). Otherwise, the timber's original end position is used.
        
        This is useful for rendering the timber geometry during development/debugging
        without showing all the joint cuts.
        
        Returns:
            Prism CSG representing the timber (finite at both ends)
            
        Raises:
            AssertionError: If any end has more than one end cut
        """
        from .meowmeowcsg import create_prism
        
        # Find all end cuts for each end
        bottom_cuts = [cut for cut in self._cuts if cut.maybeEndCut == TimberReferenceEnd.BOTTOM]
        top_cuts = [cut for cut in self._cuts if cut.maybeEndCut == TimberReferenceEnd.TOP]
        
        # Assert that each end has at most one end cut
        assert len(bottom_cuts) <= 1, f"Bottom end has {len(bottom_cuts)} end cuts, expected at most 1"
        assert len(top_cuts) <= 1, f"Top end has {len(top_cuts)} end cuts, expected at most 1"
        
        # Normalize the length direction
        length_dir_norm = normalize_vector(self._timber.length_direction)
        
        # Determine start and end distances in the timber's LOCAL coordinate system
        # The timber's origin (bottom_position) is at the origin of its local coords
        # So distances are relative to the bottom, not global coordinates
        
        if bottom_cuts:
            # Use the end cut's position - project relative to bottom_position
            bottom_end_pos = bottom_cuts[0].get_end_position()
            # Distance from bottom_position along length direction
            bottom_distance = ((bottom_end_pos - self._timber.bottom_position).T * length_dir_norm)[0, 0]
        else:
            # No cut at bottom, so start at 0 in local coordinates
            bottom_distance = 0
        
        if top_cuts:
            # Use the end cut's position - project relative to bottom_position
            top_end_pos = top_cuts[0].get_end_position()
            # Distance from bottom_position along length direction
            top_distance = ((top_end_pos - self._timber.bottom_position).T * length_dir_norm)[0, 0]
        else:
            # No cut at top, so end at timber's full length in local coordinates
            top_distance = self._timber.length
        
        # Create a finite prism representing the timber in its local coordinate system
        return create_prism(
            size=self._timber.size,
            orientation=self._timber.orientation,
            start_distance=bottom_distance,
            end_distance=top_distance
        )

    # thi sone returns the timber with all cuts applied
    def render_timber_with_cuts_csg(self) -> MeowMeowCSG:
        starting_csg = self._extended_timber_without_cuts_csg()
        # TODO difference each cut from starting_CSG?
        pass

class PartiallyCutTimber(CutTimber):
    pass

class JointAccessory:
    """Base class for joint accessories like wedges, drawbores, etc."""
    pass

class Joint:
    partiallyCutTimbers : List[PartiallyCutTimber]
    jointAccessories : List[JointAccessory]
    
    def __init__(self, partially_cut_timbers: List[PartiallyCutTimber], 
                 joint_accessories: List[JointAccessory] = None):
        """
        Create a Joint with all required parameters.
        
        Args:
            partially_cut_timbers: List of PartiallyCutTimber objects in this joint
            joint_accessories: Optional list of joint accessories (default: empty list)
        """
        self.partiallyCutTimbers = partially_cut_timbers
        self.jointAccessories = joint_accessories if joint_accessories is not None else []


# ============================================================================
# Cut Classes
# ============================================================================

class HalfPlaneCut(Cut):
    """
    A half plane cut is a cut that is defined by a half plane.
    """
    half_plane : HalfPlane
    
    def __init__(self, timber: Timber, origin: V3, orientation: Orientation, 
                 half_plane: HalfPlane, maybe_end_cut: Optional[TimberReferenceEnd] = None):
        """
        Create a HalfPlaneCut with all required parameters.
        
        Args:
            timber: The timber being cut
            origin: Origin point of the cut
            orientation: Orientation of the cut
            half_plane: The half plane defining the cut
            maybe_end_cut: Optional end cut designation (TOP or BOTTOM)
        """
        super().__init__(timber, origin, orientation, maybe_end_cut)
        self.half_plane = half_plane
    
    def get_negative_csg(self) -> MeowMeowCSG:
        return self.half_plane


class CSGCut(Cut):
    """
    A CSG cut is a cut defined by an arbitrary CSG object.
    This allows for more complex cuts like grooves, dados, and other shapes
    that can't be represented by a simple half-plane.
    
    The CSG object represents the volume to be REMOVED from the timber (negative CSG).
    """
    negative_csg: MeowMeowCSG
    
    def __init__(self, timber: Timber, origin: V3, orientation: Orientation,
                 negative_csg: MeowMeowCSG, maybe_end_cut: Optional[TimberReferenceEnd] = None):
        """
        Create a CSGCut with all required parameters.
        
        Args:
            timber: The timber being cut
            origin: Origin point of the cut (reference point)
            orientation: Orientation of the cut
            negative_csg: The CSG object defining the volume to remove
            maybe_end_cut: Optional end cut designation (TOP or BOTTOM)
        """
        super().__init__(timber, origin, orientation, maybe_end_cut)
        self.negative_csg = negative_csg
    
    def get_negative_csg(self) -> MeowMeowCSG:
        return self.negative_csg

