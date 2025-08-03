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

@dataclass
class StandardTenon:
    shoulder_plane: ShoulderPlane
    pos_rel_to_long_edge: Optional[Tuple[TimberReferenceLongEdge, V2]]
    width: float
    height: float
    depth: float

@dataclass
class MultiTenon:
    tenons: List[StandardTenon]

@dataclass
class StandardMortise:
    mortise_face: TimberFace
    pos_rel_to_end: Tuple[TimberReferenceEnd, float]
    pos_rel_to_long_face: Optional[Tuple[TimberReferenceLongFace, float]]
    width: float
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

def simple_mortise_and_tenon_joint(mortise_timber: Timber, tenon_timber: Timber,
                                  tenon_thickness: float, tenon_length: float,
                                  tenon_depth: float):
    """
    Creates a mortise and tenon joint
    The tenon is centered on the tenon_timber and the mortise is cut out of the mortise_timber
    """
    # Create the joint
    joint = Joint()
    
    # Create tenon specification
    tenon_spec = StandardTenon(
        shoulder_plane=ShoulderPlane(
            reference_end=TimberReferenceEnd.BOTTOM,
            distance=0,  # Use integer instead of 0.0
            normal=create_vector3d(0, 0, 1)
        ),
        pos_rel_to_long_edge=None,  # Centered
        width=tenon_thickness,
        height=tenon_thickness,
        depth=tenon_length
    )
    
    # Create mortise specification
    mortise_spec = StandardMortise(
        mortise_face=TimberFace.TOP,
        pos_rel_to_end=(TimberReferenceEnd.BOTTOM, 0),  # Use integer instead of 0.0
        pos_rel_to_long_face=None,  # Centered
        width=tenon_thickness,
        height=tenon_length,
        depth=tenon_depth
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
