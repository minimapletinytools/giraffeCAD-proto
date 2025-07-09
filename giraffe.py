"""
GiraffeCAD - Timber framing CAD system
Based on the API specification in morenotes.md
"""

import math
from enum import Enum

# Vector classes
class V2:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return f"V2({self.x}, {self.y})"

class V3:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    
    def __repr__(self):
        return f"V3({self.x}, {self.y}, {self.z})"

# Enums
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

# Footprint class
class Footprint:
    def __init__(self, boundary):
        """
        Initialize footprint with boundary points.
        
        Args:
            boundary: List of V2 points defining the boundary
        """
        self.boundary = boundary
    
    def get_boundary_segment(self, index):
        """Get the boundary segment from index to index+1"""
        start = self.boundary[index]
        end = self.boundary[(index + 1) % len(self.boundary)]
        return start, end
    
    def get_segment_length(self, index):
        """Get the length of a boundary segment"""
        start, end = self.get_boundary_segment(index)
        dx = end.x - start.x
        dy = end.y - start.y
        return math.sqrt(dx*dx + dy*dy)

# Timber class
class Timber:
    def __init__(self, name, length, width, height, position=V3(0, 0, 0), orientation=None):
        """
        Initialize a timber.
        
        Args:
            name: Name of the timber
            length: Length in Z direction
            width: Width in X direction  
            height: Height in Y direction
            position: Position in 3D space
            orientation: Timber orientation (optional)
        """
        self.name = name
        self.length = length
        self.width = width
        self.height = height
        self.position = position
        self.orientation = orientation
        self.true_dimension = V2(width, height)
        self.bound_dimension = V2(width, height)
    
    def __repr__(self):
        return f"Timber('{self.name}', length={self.length}, width={self.width}, height={self.height})"

# Timber creation functions
def create_vertical_timber_on_footprint(footprint, footprint_index, length, location_type=TimberLocationType.INSIDE):
    """
    Create a vertical timber (post) on the footprint.
    
    Args:
        footprint: Footprint object
        footprint_index: Index of the boundary point
        length: Length of the timber in Z direction
        location_type: Where to place the timber relative to the boundary
    
    Returns:
        Timber object
    """
    point = footprint.boundary[footprint_index]
    
    # For now, use default dimensions
    width = 3  # inches
    height = 3  # inches
    
    position = V3(point.x, point.y, 0)
    
    timber = Timber(f"post_{footprint_index}", length, width, height, position)
    print(f"Created vertical timber: {timber}")
    return timber

def create_horizontal_timber_on_footprint(footprint, footprint_index, length, location_type=TimberLocationType.INSIDE):
    """
    Create a horizontal timber (mudsill) on the footprint.
    
    Args:
        footprint: Footprint object
        footprint_index: Index of the boundary segment (0-3 for a rectangle)
        length: Length of the mudsill
        location_type: Where to place the mudsill relative to the boundary
    
    Returns:
        Timber object
    """
    # Get the boundary segment
    start_point, end_point = footprint.get_boundary_segment(footprint_index)
    
    # Calculate the actual length of the boundary segment
    segment_length = footprint.get_segment_length(footprint_index)
    
    # For mudsills, we use the segment length as the timber length
    # and standard dimensions for width and height
    width = 3  # inches
    height = 3  # inches
    
    # Position the mudsill at the start point
    position = V3(start_point.x, start_point.y, 0)
    
    # Create the mudsill
    mudsill_name = f"mudsill_{footprint_index}"
    mudsill = Timber(mudsill_name, segment_length, width, height, position)
    
    print(f"Created horizontal timber: {mudsill}")
    print(f"  From ({start_point.x}, {start_point.y}) to ({end_point.x}, {end_point.y})")
    print(f"  Location type: {location_type.name}")
    
    return mudsill

def create_axis_aligned_timber(bottom_position, length, size, length_direction, face_direction):
    """
    Create a timber aligned to the coordinate axes.
    
    Args:
        bottom_position: V3 position of the bottom center of the timber
        length: Length of the timber in the length_direction
        size: V2 size (width, height) of the timber cross section
        length_direction: TimberFace indicating the length direction
        face_direction: TimberFace indicating the face direction
    
    Returns:
        Timber object
    """
    # Create the timber with the given dimensions
    timber = Timber(
        name=f"timber_{length_direction.name}_{face_direction.name}",
        length=length,
        width=size.x,
        height=size.y,
        position=bottom_position
    )
    
    print(f"Created axis-aligned timber: {timber}")
    print(f"  Position: {bottom_position}")
    print(f"  Length direction: {length_direction.name}")
    print(f"  Face direction: {face_direction.name}")
    
    return timber 

# FaceAlignedJoinedTimberOffset class
class FaceAlignedJoinedTimberOffset:
    def __init__(self, reference_face, centerline_offset=None, face_offset=None):
        """
        Determines the offset of timberX from timberA.
        
        Args:
            reference_face: TimberFace - the reference face for the offset
            centerline_offset: float - offset between centerlines (optional)
            face_offset: float - offset between faces (optional)
        """
        self.reference_face = reference_face
        self.centerline_offset = centerline_offset
        self.face_offset = face_offset

def join_perpendicular_on_face_aligned_timbers(timber1, timber2, location_on_timber1, symmetric_stickout, offset_from_timber1, orientation_face_on_timber1=TimberFace.TOP):
    """
    Join two face-aligned timbers with a perpendicular timber.
    
    Args:
        timber1: First timber
        timber2: Second timber  
        location_on_timber1: Location along timber1's length vector where join is made
        symmetric_stickout: Distance from centerline to ends of created timber
        offset_from_timber1: FaceAlignedJoinedTimberOffset object
        orientation_face_on_timber1: Face on timber1 for orientation (default TOP)
    
    Returns:
        Timber object representing the connecting timber
    """
    # Calculate the height needed for the connecting timber
    # It should span from timber1 to timber2
    timber1_top = timber1.position.z + timber1.length
    timber2_bottom = timber2.position.z
    
    connecting_length = timber1_top - timber2_bottom
    
    # Calculate position based on offset
    if offset_from_timber1.centerline_offset is not None:
        # Use centerline offset
        if offset_from_timber1.reference_face == TimberFace.RIGHT:
            x_offset = offset_from_timber1.centerline_offset
        elif offset_from_timber1.reference_face == TimberFace.LEFT:
            x_offset = -offset_from_timber1.centerline_offset
        else:
            x_offset = 0
    else:
        x_offset = 0
    
    # Position the connecting timber
    connecting_position = V3(
        timber1.position.x + x_offset,
        timber1.position.y,
        timber2_bottom
    )
    
    # Create the connecting timber
    connecting_timber = Timber(
        name=f"connecting_{timber1.name}_{timber2.name}",
        length=connecting_length,
        width=3,  # Default width
        height=3,  # Default height
        position=connecting_position
    )
    
    print(f"Created connecting timber: {connecting_timber}")
    print(f"  Connecting {timber1.name} to {timber2.name}")
    print(f"  Location on timber1: {location_on_timber1}")
    print(f"  Symmetric stickout: {symmetric_stickout}")
    print(f"  Orientation face: {orientation_face_on_timber1.name}")
    
    return connecting_timber 