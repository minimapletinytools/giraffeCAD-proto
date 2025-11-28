


# non goals
- rectangular timbers only, which is to say they have a true dimension which all joints are aligned to
    - that is to say, scribing to non-true dimesions is not supported
    - that is also to say, we won't try and build a OOP hierarchy of increasingly specific parts
        - part > box (adds dimension) > timber (fixed orientation) > cut timber (adds joints)
- timbers are spatially unaware and all substractive joint operations asume the timbers to intersect intersect in a realistic way
- no symmetries, instead these should be manually programmed
- imperative ;__;
- timbers are semi-hardcode to work in the standard orientation only
    - tenons can only be on the top/bottom faces
    - no overgeneralizing with TimberReferenceFace TimberReferenceEdge
- only rectangular tenons


# Concepts

## Coordinate System
XY is the "ground" and Z is "up" 
RHS coordinate system
We will say +X is "right" and +Y is "forward"
We may also say +X is "east" and +Y is "north"

## Features
We will refer to the following geometric concepts and their corresponding physical features

- Point : Vertex
- Line : Edge
- Plane : Face

since faces live on solid objects, they are "sided" objects. We say 2 faces are *oriented* if they share the same normal, and *opposite* if their normals are opposites.


## Footprint
A support class representing the footprint of the structure in the XY plane to help position and orient timbers. Footprints are always defined at Z=0 and timbers defined on the footprint are always above Z=0.


```
class Footprint:
    # a list of points defining the corners of the footprint, the last point is connected to the first point
    corners : list[V2]
    
    def sides() -> list[tuple[V2, V2]]:
        # Returns a list of sides (line segments) starting from (corner[0], corner[1])
        # Each side is a tuple of (start_point, end_point)
    
    def isValid() -> bool:
        # Checks to ensure a footprint has at least 3 corners and no intersecting sides
    
    def containsPoint(point: V2) -> bool:
        # Checks to see if a point is contained within the footprint
    
    def nearestCorner(point: V2) -> tuple[int, V2]:
        # Returns (index, corner) of the nearest corner to a point
    
    def nearestBoundary(point: V2) -> tuple[int, tuple[V2, V2], float]:
        # Returns (index, side, distance) of the nearest side to a point
```

```
class TimberLocationType(Enum):
    INSIDE = 1
    CENTER = 2
    OUTSIDE = 3
```

### Inside, Outside and Corners

Footprints consist of a set of boundary corners that form a non intersecting boundary consisting of boundary sides. This boundary defines an inside and outside to the boundary which are used to position timbers around the boundary. 

Timbers are positioned either on boundary sides or boundary corners. They can either be positioned "inside", "outside", "on center". Each boundary corner and boundary side also have a notion of inside and outside. 

For boundary sides, the inside side is simply the side of the boundary side that is towards the inside of the boundary and the outside the opposite.

For boundary corners it is a little more complicated because we want to orient vertices of posts around the inside/outside of the boundary corner. This is elaborated in more detail below.


#### Mudsills go on boundary sides

A mudsill on a boundary side of a footprint will have its length run from one boundary corner to the other boundary corner of the boundary side.

A mudsill on the inside/outside of a boundary side will have an edge lying on the boundary side with the mudsill on the inside/outside side of the boundary side.

A mudsill on center of a boundary side will have its midline lying on the same plane 

#### Posts go on points on boundary sides

A post can be positioned on a point along a boundary side. 

If the post is on center, it will have its center of the bottom face lying on the point, and 2 of the edges of the bottom face will be parallel to the boundary side.

If the post is inside/outside, it will have one edge of the bottom face lying on the boundary side with the center of that edge coincident with the point, with the rest of the post inside/outside of the boundary side.

#### Posts go on boundary corners

A post can be positioned on the inside/outside of a boundary corner IF the boundary corner is orthogonal, i.e. the two boundary sides coming out of the boundary corner are perpendicular.

If it is on the inside of the boundary corner, position the post such that it overlaps with the inside of the boundary, has one vertex of its bottom face lying on the boundary corner, and has 2 edges of its bottom face aligning with the 2 boundary sides coming out of the boundary corner. 

If it is on the outside of the boundary corner, then position the post first on the inside of the boundary corner, and take the vertex of its bottom face that is opposite to the vertex lying on the boundary corner and move it so that the opposite vertex is instead on the boundary corner.


## Timber

QUESTION should we attach meta info to Timbers, it would be nice if timbers were aware of their location on the footprint to assist in finding reference faces for joint operations

```
class Timber:
    length : float
    size : V2
    bottom_position : V3
    length_direction : TimberFace
    face_direction : TimberFace
    # nominal_size : V2
```


### timber position and orientation

Timbers are referenced in their own local coordinate system

The *bottom point* of a timber is on the bottom face of the timber and in the center of its cross section. The bottom point is located at the origin of the timber's local coordinate system.

The *centerline* of the timber is the line that runs from bottom to top.

By default, a timber is oriented with its bottom cross section centered on the XY plane and running up in the Y direction
To orient the timber we position the +Z and +X axis. We will call these the "length vector" and "face vector" respectively
A timber may be rotated in space, but we will continue to refer to the axis of the timber in its default orientation. 
We also have names for each axis

Z axis - *length axis* of the timber
X axis - *width axis* of the timber
Y axis - *height axis* of the timber


We say a timber is *axis aligned* if its length vector is parallel to the +Z axis and its face vectors are parallel to either the X or Y axis.

We say two timbers are *face parallel* if each of the 6 faces of one timber is parallel with one of the 6 faces of the other timber. 

So it follows 2 axis aligned timbers are face parallel.

we often do not care to distinguish between 2 opposing faces on a timber thus

- the *width-sides* of a timber are the 2 faces perpendicular to its local X axis
- the *height-sides* of a timber are the 2 faces perpendicular to its local Y axis
- the *ends* of a timber are the 2 faces perpendicular to its local Z axis

When we do care about referencing a specific face, we may do so relative to its local coordinate system

```
class TimberFace(Enum):
    TOP = 1 # the face vector with normal vector in the +Z axis direction
    BOTTOM = 2 # the face vector with normal vector in the -Z axis direction
    RIGHT = 3 # the face vector with normal vector in the +X axis direction
    FORWARD = 4 # the face vector with normal vector in the +Y axis direction
    LEFT = 5 # the face vector with normal vector in the -X axis direction
    BACK = 6 # the face vector with normal vector in the -Y axis direction
```

Or we may do so relative to the footprint

- TODO inside/outside






#### 

```

#### timber reference features

Each face is named and faces are grouped into "ends" and "long edges"

```
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
```


#### measurements from reference features
Measurements are then taken from these faces 

```
struct DistanceFromFace(Enum):
    face : TimberFace
    distance : float

struct DistanceFromLongFace(Enum):
    face : TimberReferenceLongFace
    distance : float

struct DistanceFromEnd(Enum):
    end : TimberReferenceEnd
    distance : float

struct DistanceFromLongEdge(Enum):
    edge : TimberReferenceLongEdge
    distance1 : float
    distance2 : float
```


### operations

```
create_timber(bottom_position : V3,  length : float, size : V2, length_direction : V3, face_direction : V3) -> Timber

# creates a timber at bottom_position with given dimensions and rotates it to the length_direction and face_direction (using TimberFace to reference directions in the world coordinate system)
create_axis_aligned_timber(bottom_position : V3, length : float, size : V2, length_direction : TimberFace, face_direction : TimberFace) -> Timber

# AKA create_post
# the length is in the up (+Z) direction
# positions a post on a boundary corner with INSIDE/OUTSIDE/CENTER logic
create_vertical_timber_on_footprint_corner(footprint: Footprint, corner_index: int, length: float, location_type: TimberLocationType, size: V2) -> Timber

# AKA create_post
# the length is in the up (+Z) direction
# positions a post at a point along a boundary side with INSIDE/OUTSIDE/CENTER logic
create_vertical_timber_on_footprint_side(footprint: Footprint, side_index: int, distance_along_side: float, length: float, location_type: TimberLocationType, size: V2) -> Timber

# AKA create_mudsill
# the left (-X) face is lying on the XY plane
# the mudsill starts at corner_index and goes to corner_index + 1
# length is optional - if not provided, it is calculated from the boundary side length
create_horizontal_timber_on_footprint(footprint: Footprint, corner_index: int, location_type: TimberLocationType, size: V2, length: Optional[float] = None) -> Timber

# create a timber extension by extending the given timber, the end is the end of the timber to extend
# overlap_length is the length of the timber to overlap with the existing timber
# extend_length is the length of the timber to extend
create_timber_extension(timber: Timber, end: TimberEnd, overlap_length: float, extend_length: float) -> Timber

# Stickout class defines how much a timber extends beyond connection points
# For symmetric stickout, use Stickout.symmetric(value) or set stickout1 = stickout2
# For asymmetric stickout, use Stickout(value1, value2)
# For no stickout, use Stickout.nostickout() or Stickout()
@dataclass
class Stickout:
    stickout1: float = 0  # Extension beyond the first connection point
    stickout2: float = 0  # Extension beyond the second connection point
    
    @classmethod
    def symmetric(value: float) -> Stickout:
        """Create symmetric stickout where both sides extend by the same amount."""
        return Stickout(value, value)
    
    @classmethod
    def nostickout() -> Stickout:
        """Create stickout with no extension on either side."""
        return Stickout(0, 0)

# Examples:
# Stickout.symmetric(0.2)      # Both sides extend 0.2m
# Stickout.nostickout()        # No stickout on either side
# Stickout(0.1, 0.4)           # Asymmetric: 0.1m on side 1, 0.4m on side 2
# Stickout()                   # Also creates no stickout (default)

# the bottom face of the created timber is parallel to the face of timber1 that it is joined to.
# orientation_face_vector determines the orientation of the created timber by. The orientation_face_vector will lie on the plane created by the length_vector and face_vector of the created timber. In practice, just set this to the face_vector you want for the created timber. 
# if location_on_timber2 is not provided, the height is determined by projecting location_on_timber1 to the Z axis of timber2
# stickout defines how much the timber extends beyond the connection points (stickout1 at timber1, stickout2 at timber2)
# offset_from_timber1 is in the direction of the cross product of the length vectors of timber1 and the created timber. If this is 0, then the centerline axis of the created timber is coincident with the centerline axis of timber1/2
# an offset of 0 means the center lines of timber1/timber2 and the created timber are coincident
# size is optional - if not provided, determined from timber1's size based on orientation:
#   - It will attempt to match timber1's size such that the created timber shares a common dimension in the same axis with timber1
join_timbers(timber1: Timber, timber2: Timber, location_on_timber1: float, stickout: Stickout, offset_from_timber1: float, location_on_timber2: float?, orientation_face_vector: V3?, size: V2?) -> Timber

# determines the offset of timberX from timberA
# if centerline_offset is provided, the offset is between the centerlines of timberA and timberX and in the direction of the reference_face
# if face_offset is provided, the offset is between the reference_face of timberA and the matching aligned face of timberX in the direction of the reference_face
class FaceAlignedJoinedTimberOffset:
    reference_face : TimberFace
    centerline_offset : float?
    face_offset : float?

# the bottom face of the created timber is parallel to the face of timber1 that it is joined to.
# orientation_face_on_timber1 is a face on timber1. The face_vector of the created timber will match orientation_face_on_timber1. If no such orientation is possible the function will warn and the TOP face will be used instead.
# location_on_timber1 is the location along the length vector of timber1 where the join is made (starting from the bottom of the timber)
# size is the cross-sectional dimensions (width, height) of the joining timber
# the timber length is calculated as: distance between timber1 and timber2 centerlines + stickout.stickout1 + stickout.stickout2
join_perpendicular_on_face_parallel_timbers(timber1: Timber, timber2: Timber, location_on_timber1: float, stickout: Stickout, offset_from_timber1: FaceAlignedJoinedTimberOffset, size: V2, orientation_face_on_timber1 = TimberFace.TOP : TimberFace) -> Timber
```

## joint construction operations

to ease in the construction of various types of joints, we define a set of joint construction operation that can be combined to form a joint.

```
class TimberCutOperation:
    # the timber that the operation is applied to
    timber : Timber
    # TODO some cut function
```

### tenon

A tenon consists of a shoulder plan, a tenon direction (bottom to top), and additive geometry built in the volume of the timber in the tenon direction past the shoulder plane. Depth can be measured from the the shoulder plane. For angled shoulder planes, the distance is measured from where the shoulder plane meets the reference long edge. The tenon direction must be provided is usually determined by the joint operation (i.e. always in the direction of the length vector of timber the tenon is intended to it into).

```
class ShoulderPlane:
    direction : TimberEnd
    # distance is measured from the TimberEnd face
    distance : float
    orientation : EulerAngles
```

#### standard tenon

A standard tenon is a rectangular cross section that extrudes from the shoulder plane and along the Z axis of the timber. The cross section position is measured from a long edge of the timber or the centerline of the timber. 

```
class StandardTenon:
    shoulder_plane : ShoulderPlane
    # if not provided, the cross section is centered on the centerline of the timber
    pos_rel_to_long_edge : (TimberReferenceLongEdge, V2)?
    # in the X axis
    width : float 
    # in the Y axis
    height : float
    # in the Z axis
    depth : float
```

TODO drawbore tenon may define a bore hole always runs perpendicular to the extrusion direction of the tenon and the length of the tenon. 

#### multi-tenon

a multi-tenon is a set of tenons that have been unioned together. They must all share the same shoulder plane. this is useful for more complex joints

```
class MultiTenon:
    tenons : list[StandardTenon]
```

### mortise

A mortise is substractive geometry from the a timber. There is no need for a multi mortise as you can just apply multiple mortise operations.

#### standard mortise

a standard mortise consists of a rectangular cross section on a long face of the timber. The cross section is defined by a width (XY dimension), a length (Z dimension), and depth (extrusion depth from face). The cross section dimensions are measured from a reference long edge or centerline of the timber and the end of the timber. 

```
class StandardMortise:
    mortise_face : TimberFace
    pos_rel_to_end : (TimberReferenceEnd, float)
    # if TimberReferenceLongFace is not provided, then the mortise is centered on the centerline of the timber
    pos_rel_to_long_face : (TimberReferenceLongFace, float)?
    # in the reference_long_face axis
    width : float 
    # in the reference_end axis
    height : float
    # in the mortise_face axis
    depth : float
```

TODO drawbore mortise a standard mortise with a bore hole. It always runs perpendicular to the extrusion direction of the mortise and the Z axis of the timber.

## joints

Joints connect 1 or more timbers together through substractively modifications on the timbers. In addition, joints my define accesories to support the joints (e.g. a wedge)
A timber may have any number of joints. 


```
# for stuff like wedges, drawbores, etc
class JointAccessory:
    # TODO

class Joint:
    timber_cuts : list[(Timber,[TimberCutOperation, JointAccessory])]    
```



```
# creates a mortise and tenon joint. the tenon is centered on the tenon_timber and the mortise is cut out of the mortise_timber based on the tenon position
# tenon_length is in the length direction of the mortise_timber
# tenon_depth is the depth is how deep the tenon extends into the mortise_timber
# TODO provide optional drawbore arguments
simple_mortise_and_tenon_joint_on_face_aligned_timbers(mortise_timber: Timber, tenon_timber: Timber, tenon_end: TimberReferenceEnd, tenon_thickness: float, tenon_length: float, tenon_depth: float)
```

To store joints on the timber, we have:
```
class CutTimber:
    timber : Timber
    joints : list[TimberCutOperation]
```

# V1.5 NOTES


#### more configurable or complicated joints 
- mortise_and_tenon_joint 
    - option for tusk and drawbore
    - can handle angled shoulder
    - position tenon needs: top_relative_face: TimberFace, side_relative_face: TimberFace, 
    - position mortise needs: side_relative_face: TimberFace, 
- rafter_joint 
    - a basic substractive joint that cuts the rafter from the ridge beam, purlins, plates etc
- wedged_dovetail_mortise_and_tenon_joint
- splice_joint
    - TODO figure out how to handle this, you want to define it as a single timber in most cases but sometimes you want to treat it as 2 timbers
- drop_in_joist
    - supports straight and dovetailed cutouts


# V2 Notes


Currently we have

TimberReferenceLongEdge (X/Y axis faces)
TimberReferenceEnd (Z axis faces)

We can generalize to arbitrary faces with 

TimberReferenceCorner TimberReferenceFace TimberReferenceEdge

However, I think Timbers are by definition in the standard orientation, so instead timbers derive from some Box object


