"""
GiraffeCAD - Timber framing CAD system
Based on the API specification in morenotes.md
"""

from sympy import Matrix, sqrt, simplify, Float, Abs, Rational, Expr
from moothymoth import Orientation
from enum import Enum
from typing import List, Optional, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass

# Type aliases for vectors using sympy
V2 = Matrix  # 2D vector - 2x1 Matrix
V3 = Matrix  # 3D vector - 3x1 Matrix  
Direction3D = Matrix  # 3D direction vector - 3x1 Matrix

# ============================================================================
# Enums and Basic Types
# ============================================================================

class TimberLocationType(Enum):
    INSIDE = 1
    CENTER = 2
    OUTSIDE = 3

class TimberFace(Enum):
    TOP = 1
    BOTTOM = 2
    RIGHT = 3
    FORWARD = 4
    LEFT = 5
    BACK = 6

class TimberReferenceEnd(Enum):
    TOP = 1
    BOTTOM = 2

class TimberReferenceLongFace(Enum):
    RIGHT = 3
    FORWARD = 4
    LEFT = 5
    BACK = 6

class TimberReferenceLongEdge(Enum):
    RIGHT_FORWARD = 7
    FORWARD_LEFT = 8
    LEFT_BACK = 9
    BACK_RIGHT = 10

# ============================================================================
# Data Structures
# ============================================================================

# the shoulder plane is defined by the normal of a plane that is distance away from the center point of the TimberReferenceEnd face of the timber
# the "cut" side is in the direction of the normal which should always point towards reference_end
@dataclass
class ShoulderPlane:
    reference_end: TimberReferenceEnd
    distance: float
    normal: V3
    
    @classmethod
    def create(cls, reference_end: TimberReferenceEnd, distance: float, normal: Optional[V3] = None) -> 'ShoulderPlane':
        """
        Create a ShoulderPlane with automatic normal determination.
        
        Args:
            reference_end: Which end of the timber the plane references
            distance: Distance from the reference end
            normal: Optional normal vector. If not provided, determined from reference_end
            
        Returns:
            ShoulderPlane instance
        """
        if normal is None:
            if reference_end == TimberReferenceEnd.TOP:
                # Normal points toward TOP (upward)
                normal = create_vector3d(0, 0, 1)
            else:  # TimberReferenceEnd.BOTTOM
                # Normal points toward BOTTOM (downward)
                normal = create_vector3d(0, 0, -1)
        
        return cls(reference_end=reference_end, distance=distance, normal=normal)

@dataclass
class StandardTenon:
    shoulder_plane: ShoulderPlane
    pos_rel_to_long_edge: Optional[Tuple[TimberReferenceLongEdge, V2]]
    width: float
    height: float
    length: float  # How far the tenon extends beyond the shoulder plane

@dataclass
class MultiTenon:
    tenons: List[StandardTenon]

@dataclass
class StandardMortise:
    mortise_face: TimberFace
    pos_rel_to_end: Tuple[TimberReferenceEnd, float]
    pos_rel_to_long_face: Optional[Tuple[TimberReferenceLongFace, float]]
    # in the long face axis
    width: float
    # in the end axis
    height: float
    depth: float

@dataclass
class FaceAlignedJoinedTimberOffset:
    reference_face: TimberFace
    centerline_offset: Optional[float]
    face_offset: Optional[float]

@dataclass
class DistanceFromFace:
    face: TimberFace
    distance: float

@dataclass
class DistanceFromLongFace:
    face: TimberReferenceLongFace
    distance: float

@dataclass
class DistanceFromEnd:
    end: TimberReferenceEnd
    distance: float

@dataclass
class DistanceFromLongEdge:
    edge: TimberReferenceLongEdge
    distance1: float
    distance2: float

# ============================================================================
# Helper Functions for Vector Operations
# ============================================================================

def create_vector2d(x: float, y: float) -> V2:
    """Create a 2D vector"""
    return Matrix([x, y])

def create_vector3d(x: float, y: float, z: float) -> V3:
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

class Footprint:
    """A support class representing the footprint of the structure in the XY plane"""
    
    def __init__(self, boundary: List[V2]):
        """
        Args:
            boundary: List of points defining the boundary, last point connects to first
        """
        self.boundary: List[V2] = boundary

class FootprintBoundary:
    """Represents a boundary line from start_index to start_index + 1"""
    
    def __init__(self, start_index: int):
        self.start_index: int = start_index

class Timber:
    """Represents a timber in the timber framing system"""
    
    def __init__(self, length: Union[float, int, Expr], size: V2, bottom_position: V3, 
                 length_direction: Direction3D, face_direction: Direction3D):
        """
        Args:
            length: Length of the timber
            size: Cross-sectional size (width, height) as 2D vector
            bottom_position: Position of the bottom point (center of cross-section) as 3D vector
            length_direction: Direction vector for the length axis as 3D vector
            face_direction: Direction vector for the face axis as 3D vector
        """
        self.length: float = length
        self.size: V2 = size
        self.bottom_position: V3 = bottom_position
        self.name: Optional[str] = None
        self.orientation: Orientation
        
        # Calculate orientation matrix from input directions
        self._compute_orientation(length_direction, face_direction)
    
    def _compute_orientation(self, length_direction: Direction3D, face_direction: Direction3D):
        """Compute the orientation matrix from length and face directions"""
        # Normalize the length direction first (this will be our primary axis)
        length_norm = normalize_vector(length_direction)
        
        # Orthogonalize face direction relative to length direction using Gram-Schmidt
        face_input = normalize_vector(face_direction)
        
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
        return Matrix([
            self.orientation.matrix[0, 2],
            self.orientation.matrix[1, 2],
            self.orientation.matrix[2, 2]
        ])
    
    @property
    def face_direction(self) -> Direction3D:
        """Get the face direction vector from the orientation matrix"""
        # Face direction is the 1st column (index 0) of the rotation matrix
        return Matrix([
            self.orientation.matrix[0, 0],
            self.orientation.matrix[1, 0],
            self.orientation.matrix[2, 0]
        ])
    
    @property
    def height_direction(self) -> Direction3D:
        """Get the height direction vector from the orientation matrix"""
        # Height direction is the 2nd column (index 1) of the rotation matrix
        return Matrix([
            self.orientation.matrix[0, 1],
            self.orientation.matrix[1, 1],
            self.orientation.matrix[2, 1]
        ])
    
    def get_position_on_timber(self, position: float) -> V3:
        """
        Get the 3D position at a specific point along the timber's length.
        
        Args:
            position: Distance along the timber's length direction from the bottom position
            
        Returns:
            3D position vector at the specified position along the timber
        """
        return self.bottom_position + self.length_direction * position
    
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

class TimberCutOperation:
    """Base class for timber cut operations"""
    
    def __init__(self, timber: Timber):
        self.timber: Timber = timber

class TenonCutOperation(TimberCutOperation):
    """Tenon cut operation"""
    
    def __init__(self, timber: Timber, tenon_spec: StandardTenon):
        super().__init__(timber)
        self.tenon_spec = tenon_spec

class MortiseCutOperation(TimberCutOperation):
    """Mortise cut operation"""
    
    def __init__(self, timber: Timber, mortise_spec: StandardMortise):
        super().__init__(timber)
        self.mortise_spec = mortise_spec

class JointAccessory:
    """Base class for joint accessories like wedges, drawbores, etc."""
    pass

class Joint:
    """Represents a joint connecting timbers"""
    
    def __init__(self):
        self.name: Optional[str] = None
        self.timber_cuts: List[Tuple[Timber, List[Union[TimberCutOperation, JointAccessory]]]] = []

class CutTimber:
    """A timber with applied cuts/joints"""
    
    def __init__(self, timber: Timber):
        self.timber: Timber = timber
        self.name: Optional[str] = timber.name
        self.joints: List[TimberCutOperation] = []

# ============================================================================
# Timber Creation Functions
# ============================================================================

def create_timber(bottom_position: V3, length: float, size: V2, 
                  length_direction: Direction3D, face_direction: Direction3D) -> Timber:
    """
    Creates a timber at bottom_position with given dimensions and rotates it 
    to the length_direction and face_direction
    """
    return Timber(length, size, bottom_position, length_direction, face_direction)

def create_axis_aligned_timber(bottom_position: V3, length: float, size: V2,
                              length_direction: TimberFace, face_direction: TimberFace) -> Timber:
    """
    Creates an axis-aligned timber using TimberFace to reference directions
    in the world coordinate system
    """
    # Convert TimberFace to direction vectors
    length_vec = _timber_face_to_vector(length_direction)
    face_vec = _timber_face_to_vector(face_direction)
    
    return create_timber(bottom_position, length, size, length_vec, face_vec)

def create_vertical_timber_on_footprint(footprint: Footprint, footprint_index: int, 
                                       length: float, location_type: TimberLocationType = TimberLocationType.INSIDE) -> Timber:
    """
    Creates a vertical timber (post) on the footprint
    The length is in the up (+Z) direction
    The face is in the right (+X) direction
    """
    # Get the footprint point
    point = footprint.boundary[footprint_index]
    
    # Convert to 3D position
    bottom_position = create_vector3d(float(point[0]), float(point[1]), 0)
    
    # Default size for posts
    size = create_vector2d(Rational(9, 100), Rational(9, 100))  # 9cm x 9cm as exact rationals
    
    # Vertical direction
    length_direction = create_vector3d(0, 0, 1)
    face_direction = create_vector3d(1, 0, 0)
    
    return create_timber(bottom_position, length, size, length_direction, face_direction)

def create_axis_aligned_horizontal_timber_on_footprint(footprint: Footprint, footprint_index: int,
                                        length: float, location_type: TimberLocationType) -> Timber:
    """
    Creates an axis aligned horizontal timber (mudsill) on the footprint
    The left (-X) face is lying on the XY plane
    The mudsill starts at footprint_index and goes to footprint_index + 1
    """
    # Get the footprint points
    start_point = footprint.boundary[footprint_index]
    end_point = footprint.boundary[(footprint_index + 1) % len(footprint.boundary)]
    
    # Calculate direction vector
    direction = Matrix([float(end_point[0] - start_point[0]), float(end_point[1] - start_point[1]), 0])
    
    # Normalize
    direction_3d = normalize_vector(direction)
    
    # Position based on location type
    if location_type == TimberLocationType.INSIDE:
        # Place inside the footprint
        bottom_position = create_vector3d(float(start_point[0]), float(start_point[1]), 0)
    elif location_type == TimberLocationType.CENTER:
        # Center on the footprint line
        mid_x = float((start_point[0] + end_point[0]) / 2)
        mid_y = float((start_point[1] + end_point[1]) / 2)
        bottom_position = create_vector3d(mid_x, mid_y, 0)
    else:  # OUTSIDE
        # Place outside the footprint
        bottom_position = create_vector3d(float(start_point[0]), float(start_point[1]), 0)
    
    # Default size for horizontal timbers
    size = create_vector2d(Rational(3, 10), Rational(3, 10))  # 30cm x 30cm as exact rationals
    
    # Horizontal direction
    length_direction = direction_3d
    face_direction = create_vector3d(0, 0, 1)  # Up direction
    
    return create_timber(bottom_position, length, size, length_direction, face_direction)

def create_timber_extension(timber: Timber, end: TimberReferenceEnd, overlap_length: float, 
                           extend_length: float) -> Timber:
    """
    Creates a new timber extending the original timber by a given length
    Args:
        end: The end of the timber to extend
        overlap_length: Length of timber to overlap with existing timber
        extend_length: Length of timber to extend
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
    new_length = timber.length + extend_length - overlap_length
    
    return Timber(new_length, timber.size, new_bottom_position, 
                 timber.length_direction, timber.face_direction)

def join_timbers(timber1: Timber, timber2: Timber, location_on_timber1: float,
                symmetric_stickout: float, offset_from_timber1: float,
                location_on_timber2: Optional[float] = None,
                orientation_face_vector: Optional[Direction3D] = None) -> Timber:
    """
    Joins two timbers by creating a connecting timber
    """
    # Calculate position on timber1
    pos1 = timber1.get_position_on_timber(location_on_timber1)
    
    # Calculate position on timber2
    if location_on_timber2 is not None:
        pos2 = timber2.get_position_on_timber(location_on_timber2)
    else:
        # Project location_on_timber1 to timber2's Z axis
        pos2 = Matrix([pos1[0], pos1[1], timber2.bottom_position[2] + location_on_timber1])
    
    # Calculate center position
    center_pos = (pos1 + pos2) / 2
    
    # Calculate length direction (from timber1 to timber2)
    length_direction = pos2 - pos1
    length_direction = normalize_vector(length_direction)
    
    # Calculate face direction
    if orientation_face_vector is not None:
        face_direction = orientation_face_vector
    else:
        # Generate an orthogonal face direction
        # Choose a reference vector that's not parallel to length_direction
        up_vector = create_vector3d(0, 0, 1)    # Use integers for exact computation
        right_vector = create_vector3d(1, 0, 0)  # Use integers for exact computation
        
        # Check which reference vector is more orthogonal to length_direction using exact SymPy comparison
        up_dot = Abs(length_direction.dot(up_vector))     # Exact SymPy absolute value and dot product
        right_dot = Abs(length_direction.dot(right_vector))  # Exact SymPy absolute value and dot product
        
        # Use the more orthogonal reference vector (exact SymPy comparison)
        if up_dot < right_dot:
            reference_vector = up_vector
        else:
            reference_vector = right_vector
        
        # Generate orthogonal face direction using cross product
        face_direction = normalize_vector(cross_product(reference_vector, length_direction))
    
    # Calculate timber length (keep as exact SymPy expression)
    timber_length = vector_magnitude(pos2 - pos1) + 2 * symmetric_stickout
    
    # Default size
    size = create_vector2d(Rational(3, 10), Rational(3, 10))  # 30cm x 30cm as exact rationals
    
    # Apply offset
    if offset_from_timber1 != 0:
        # Calculate offset direction (cross product of length vectors)
        offset_dir = normalize_vector(cross_product(timber1.length_direction, length_direction))
        center_pos += offset_dir * offset_from_timber1
    
    # Calculate the bottom position (start of timber) from center position
    # Move backward from center by half the timber length
    bottom_pos = center_pos - length_direction * (timber_length / 2)
    
    return create_timber(bottom_pos, timber_length, size, length_direction, face_direction)

def join_perpendicular_on_face_aligned_timbers(timber1: Timber, timber2: Timber,
                                             location_on_timber1: float,
                                             symmetric_stickout: float,
                                             offset_from_timber1: FaceAlignedJoinedTimberOffset,
                                             size: V2,
                                             orientation_face_on_timber1: TimberFace = TimberFace.TOP) -> Timber:
    """
    Joins two face-aligned timbers with a perpendicular timber.
    
    Args:
        timber1: First timber to join
        timber2: Second timber to join (face-aligned with timber1)
        location_on_timber1: Position along timber1's length where the joining timber attaches
        symmetric_stickout: How much the joining timber extends beyond each side
        offset_from_timber1: Offset configuration from timber1
        size: Cross-sectional size (width, height) of the joining timber
        orientation_face_on_timber1: Which face of timber1 to orient against (default: TOP)
        
    Returns:
        New timber that joins timber1 and timber2
    """
    # Calculate position on timber1
    pos1 = timber1.get_position_on_timber(location_on_timber1)
    
    # For face-aligned timbers, find the point on timber2 that is in the perpendicular 
    # direction from pos1. We project pos1 onto timber2's centerline.
    
    # Get the direction from timber1 to timber2 (perpendicular direction)
    face_vector = _timber_face_to_vector(orientation_face_on_timber1)
    
    # Start from pos1 and move in the face direction to find intersection with timber2's centerline
    # We need to find where the line from pos1 in the face_vector direction intersects timber2
    
    # Timber2's centerline can be parameterized as: timber2.bottom_position + t * timber2.length_direction
    # The line from pos1 in face_vector direction is: pos1 + s * face_vector
    # We want to find s and t such that these are equal
    
    # This is a line-line intersection problem in 3D
    # For simplicity in the face-aligned case, we can project pos1 onto timber2's centerline
    
    # Vector from timber2's bottom to pos1
    to_pos1 = pos1 - timber2.bottom_position
    
    # Project this onto timber2's length direction to find the parameter t
    t = to_pos1.dot(timber2.length_direction) / timber2.length_direction.dot(timber2.length_direction)
    
    # Clamp t to be within the timber's length
    t = max(0, min(float(timber2.length), float(t)))
    
    # Calculate the corresponding position on timber2's centerline
    pos2 = timber2.bottom_position + timber2.length_direction * t
    
    # Calculate length direction: from timber1 toward timber2
    length_direction = normalize_vector(pos2 - pos1)
    
    # face_vector already calculated above
    
    # Calculate the distance between the centerlines of timber1 and timber2
    centerline_distance = float(vector_magnitude(pos2 - pos1))
    
    # Calculate timber length: distance between centerlines + symmetric stickout on both sides
    timber_length = centerline_distance + 2 * symmetric_stickout
    
    # Adjust starting position to account for stickout on the timber1 side
    pos1 = pos1 - length_direction * symmetric_stickout
    
    # Apply offset
    if offset_from_timber1.centerline_offset is not None:
        # Apply centerline offset
        offset_dir = normalize_vector(cross_product(timber1.length_direction, length_direction))
        pos1 += offset_dir * offset_from_timber1.centerline_offset
    
    return create_timber(pos1, timber_length, size, length_direction, face_vector)

# ============================================================================
# Joint Construction Functions
# ============================================================================

def simple_mortise_and_tenon_joint_on_face_aligned_timbers(mortise_timber: Timber, tenon_timber: Timber,
                                                          tenon_end: TimberReferenceEnd,
                                                          tenon_thickness: float, tenon_length: float):
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
    tenon_end_direction = _get_tenon_end_direction(tenon_timber, tenon_end)
    mortise_face = _find_aligned_face(mortise_timber, -tenon_end_direction)
    
    # Calculate the correct mortise position based on tenon timber intersection
    mortise_ref_end, mortise_distance = _calculate_mortise_position_from_tenon_intersection(
        mortise_timber, tenon_timber, tenon_end
    )
    
    # Calculate tenon shoulder plane distance to position it at the mortise timber face
    tenon_shoulder_distance = _calculate_distance_from_timber_end_to_shoulder_plane(tenon_timber, mortise_timber, tenon_end)
    
    # Create tenon specification
    tenon_spec = StandardTenon(
        shoulder_plane=ShoulderPlane.create(
            reference_end=tenon_end,
            distance=tenon_shoulder_distance
        ),
        pos_rel_to_long_edge=None,  # Centered
        width=tenon_thickness,
        height=tenon_thickness,
        length=tenon_length  # How far tenon extends beyond shoulder plane
    )
    
    # Create mortise specification
    mortise_spec = StandardMortise(
        mortise_face=mortise_face,
        pos_rel_to_end=(mortise_ref_end, mortise_distance),
        pos_rel_to_long_face=None,  # Centered
        width=tenon_thickness,
        height=tenon_length,
        depth=tenon_length  # Mortise depth equals tenon length
    )
    
    # Create cut operations
    tenon_cut = TenonCutOperation(tenon_timber, tenon_spec)
    mortise_cut = MortiseCutOperation(mortise_timber, mortise_spec)
    
    # Add cuts to joint
    joint.timber_cuts.append((tenon_timber, [tenon_cut]))
    joint.timber_cuts.append((mortise_timber, [mortise_cut]))
    
    return joint

# ============================================================================
# Helper Functions
# ============================================================================

def _timber_face_to_vector(face: TimberFace) -> Direction3D:
    """Convert TimberFace enum to direction vector"""
    if face == TimberFace.TOP:
        return create_vector3d(0, 0, 1)
    elif face == TimberFace.BOTTOM:
        return create_vector3d(0, 0, -1)
    elif face == TimberFace.RIGHT:
        return create_vector3d(1, 0, 0)
    elif face == TimberFace.LEFT:
        return create_vector3d(-1, 0, 0)
    elif face == TimberFace.FORWARD:
        return create_vector3d(0, 1, 0)
    else:  # BACK
        return create_vector3d(0, -1, 0)

def _get_timber_face_direction(timber: Timber, face: TimberFace) -> Direction3D:
    """Get the world direction vector for a specific face of a timber"""
    if face == TimberFace.TOP:
        return timber.length_direction
    elif face == TimberFace.BOTTOM:
        return -timber.length_direction
    elif face == TimberFace.RIGHT:
        return timber.face_direction
    elif face == TimberFace.LEFT:
        return -timber.face_direction
    elif face == TimberFace.FORWARD:
        return timber.height_direction
    else:  # BACK
        return -timber.height_direction

def _get_tenon_end_direction(timber: Timber, end: TimberReferenceEnd) -> Direction3D:
    """Get the world direction vector for a specific end of a timber"""
    if end == TimberReferenceEnd.TOP:
        return timber.length_direction
    else:  # BOTTOM
        return -timber.length_direction

def _find_aligned_face(mortise_timber: Timber, target_direction: Direction3D) -> TimberFace:
    """Find which face of the mortise timber best aligns with the target direction (direction points outwards from the face, as oppose to into the face)"""
    faces = [TimberFace.TOP, TimberFace.BOTTOM, TimberFace.RIGHT, TimberFace.LEFT, TimberFace.FORWARD, TimberFace.BACK]
    
    best_face = faces[0]
    face_direction = _get_timber_face_direction(mortise_timber, faces[0])
    best_alignment = float(target_direction.dot(face_direction))
    
    for face in faces[1:]:
        face_direction = _get_timber_face_direction(mortise_timber, face)
        # Use dot product to find best alignment - prefer faces pointing in same direction
        alignment = float(target_direction.dot(face_direction))
        if alignment > best_alignment:
            best_alignment = alignment
            best_face = face
    
    return best_face

def _are_timbers_face_parallel(timber1: Timber, timber2: Timber, tolerance: float = 1e-10) -> bool:
    """Check if two timbers have parallel length directions"""
    dot_product = float(Abs(timber1.length_direction.dot(timber2.length_direction)))
    return Abs(dot_product - 1) < tolerance

def _are_timbers_face_orthogonal(timber1: Timber, timber2: Timber, tolerance: float = 1e-10) -> bool:
    """Check if two timbers have orthogonal (perpendicular) length directions"""
    dot_product = float(Abs(timber1.length_direction.dot(timber2.length_direction)))
    return dot_product < tolerance

def _are_timbers_face_aligned(timber1: Timber, timber2: Timber, tolerance: float = 1e-10) -> bool:
    """
    Check if two timbers are face-aligned.
    
    Two timbers are face-aligned if any face of one timber is parallel to any face 
    of the other timber. This occurs when their orientations are related by 90-degree 
    rotations around any axis (i.e., they share the same coordinate grid alignment).
    
    Args:
        timber1: First timber
        timber2: Second timber  
        tolerance: Numerical tolerance for parallel check
        
    Returns:
        True if timbers are face-aligned, False otherwise
    """
    # Get the three orthogonal direction vectors for each timber
    dirs1 = [timber1.length_direction, timber1.face_direction, timber1.height_direction]
    dirs2 = [timber2.length_direction, timber2.face_direction, timber2.height_direction]
    
    # Check if any direction from timber1 is parallel to any direction from timber2
    for dir1 in dirs1:
        for dir2 in dirs2:
            dot_product = float(Abs(dir1.dot(dir2)))
            if Abs(dot_product - 1) < tolerance:
                return True
    
    return False

def _project_point_on_timber_centerline(point: V3, timber: Timber) -> Tuple[float, V3]:
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
    t = float(to_point.dot(length_dir) / length_dir.dot(length_dir))
    
    # Calculate the projected point
    projected_point = timber.bottom_position + timber.length_direction * t
    
    return t, projected_point

def _calculate_mortise_position_from_tenon_intersection(mortise_timber: Timber, tenon_timber: Timber, tenon_end: TimberReferenceEnd) -> Tuple[TimberReferenceEnd, float]:
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
    t = max(0, min(float(mortise_timber.length), t))
    
    # Determine which end to reference based on which is closer
    distance_from_bottom = t
    distance_from_top = float(mortise_timber.length) - t
    
    if distance_from_bottom <= distance_from_top:
        return TimberReferenceEnd.BOTTOM, distance_from_bottom
    else:
        return TimberReferenceEnd.TOP, distance_from_top


def _calculate_distance_from_timber_end_to_shoulder_plane(tenon_timber: Timber, mortise_timber: Timber, tenon_end: TimberReferenceEnd) -> float:
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
    tenon_end_direction = _get_tenon_end_direction(tenon_timber, tenon_end)
    mortise_face = _find_aligned_face(mortise_timber, -tenon_end_direction)
    
    # Calculate the distance from mortise centerline to mortise face
    if mortise_face in [TimberFace.RIGHT, TimberFace.LEFT]:
        # X direction faces
        face_offset = float(mortise_timber.size[0]) / 2  # Half width
    elif mortise_face in [TimberFace.FORWARD, TimberFace.BACK]:
        # Y direction faces  
        face_offset = float(mortise_timber.size[1]) / 2  # Half height
    else:
        # TOP/BOTTOM faces (shouldn't happen for typical tenon joints)
        assert False, "TOP/BOTTOM faces shouldn't happen for typical tenon joints"
    
    # Calculate the actual position of the mortise face at the intersection point
    face_vector = _timber_face_to_vector(mortise_face)
    mortise_face_point = projected_point + create_vector3d(face_vector[0], face_vector[1], face_vector[2]) * face_offset
    
    # Calculate the distance from tenon end to where the shoulder plane should be
    # 
    # The key insight is that the shoulder plane should be positioned at the mortise face,
    # but we need to measure the distance along the tenon timber centerline.
    #
    # For misaligned timbers, we need to find where the tenon centerline would intersect 
    # the plane containing the mortise face at the projected intersection point.
    
    face_normal = create_vector3d(face_vector[0], face_vector[1], face_vector[2])
    
    # Check if tenon direction is perpendicular to mortise face normal
    direction_dot_normal = float(tenon_timber.length_direction.dot(face_normal))
    
    if abs(direction_dot_normal) < 1e-6:
        # Case 1: Tenon direction is perpendicular to mortise face (typical orthogonal joints)
        # For this case, we need to check if the timbers are actually aligned (centerlines intersect)
        # vs. misaligned (centerlines don't intersect)
        
        # Distance from tenon end to the intersection point along tenon centerline
        to_intersection = projected_point - tenon_end_point
        distance_to_intersection = abs(float(to_intersection.dot(tenon_timber.length_direction)))
        
        # Check if this is an aligned case (tenon end is very close to the mortise timber)
        # For truly aligned cases, the distance should be essentially zero (within tolerance)
        alignment_threshold = 1e-3  # 1mm tolerance
        if distance_to_intersection < alignment_threshold:
            # Aligned case: shoulder distance is just the face offset
            distance_along_tenon = face_offset
        else:
            # Misaligned case: add the distance to intersection
            distance_along_tenon = distance_to_intersection + face_offset
        
    else:
        # Case 2: Tenon direction is not perpendicular to mortise face
        # Use line-plane intersection to find where tenon centerline meets mortise face plane
        
        point_to_plane = tenon_end_point - mortise_face_point
        t = -float(point_to_plane.dot(face_normal)) / direction_dot_normal
        
        # The distance from tenon end to shoulder plane is |t|
        distance_along_tenon = abs(t)
    
    return distance_along_tenon


def apply_joint_to_cut_timbers(joint: Joint, cut_timber_mapping: dict[Timber, CutTimber]) -> None:
    """
    Apply a joint's cuts to the appropriate CutTimber objects.
    
    This helper function extracts the common pattern of applying joint cuts
    to CutTimber objects that appears frequently in examples.
    
    Args:
        joint: The TimberJoint object containing cuts to apply
        cut_timber_mapping: Dictionary mapping Timber objects to their corresponding CutTimber objects
        
    Example:
        # Create joint
        joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(...)
        
        # Apply cuts using helper
        apply_joint_to_cut_timbers(joint, {
            timber1: cut_timber1,
            timber2: cut_timber2
        })
    """
    for timber, cuts in joint.timber_cuts:
        if timber in cut_timber_mapping:
            cut_timber_mapping[timber].joints.extend(cuts)
        else:
            # Log warning if timber not found in mapping
            print(f"Warning: Timber {timber.name if hasattr(timber, 'name') else 'unnamed'} not found in cut_timber_mapping")



