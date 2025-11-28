
# Coordinate System
GiraffeCAD uses a right-hand coordinate system.

- XY is the "ground" and Z is "up" 

- +X/-x is also "right"/"left"
- +Y/-Y is also "forward"/"back"
- +Z/-Z is also "up"/"down" or "top"/"bottom"


# Features
We will refer to the following geometric concepts and their corresponding physical features

- Point / Vertex
- Line / Edge
- Plane / Face

Since faces live on solid objects, they are "sided" objects:

- we say 2 faces are *oriented* if they share the same normal, and *opposite* if their normals are opposites



# Timber

A *Timber* is one of the fundamental building blocks of your structure and the majority of GiraffeCAD is designed around this class.

```
class Timber:
    length : float
    size : V2
    bottom_position : V3
    length_direction : TimberFace
    width_direction : TimberFace
```


## timber position and orientation

Timbers are referenced in their own local coordinate system.

The *bottom point* of a timber is on the bottom face of the timber and in the center of its cross section. The bottom point is located at the origin of the timber's local coordinate system.

The *centerline* of the timber is the line that runs from bottom to top.

By default, a timber is oriented with its bottom cross section centered on the XY plane and running up in the Y direction. We use the following names for each axis

- Z axis: *length axis* of the timber
- X axis: *width axis* of the timber
- Y axis: *height axis* of the timber

To orient the timber we position, we often position the +Z and +X axis of the timber.

- We say a timber is *axis aligned* if its length vector is parallel to the +Z axis and its face vectors are parallel to either the X or Y axis.
- We say two timbers are *face parallel* if each of the 6 faces of one timber is parallel with one of the 6 faces of the other timber. 

So it follows 2 axis aligned timbers are face parallel.

we often do not care to distinguish between 2 opposing faces on a timber thus

- the *width-sides* of a timber are the 2 faces perpendicular to its local X axis
- the *height-sides* of a timber are the 2 faces perpendicular to its local Y axis
- the *ends* of a timber are the 2 faces perpendicular to its local Z axis

When we do care about referencing a specific face, we may do so relative to its local coordinate system. We may refer to each face with the following names:

```
class TimberFace(Enum):
    TOP = 1 # the face vector with normal vector in the +Z axis direction
    BOTTOM = 2 # the face vector with normal vector in the -Z axis direction
    RIGHT = 3 # the face vector with normal vector in the +X axis direction
    FORWARD = 4 # the face vector with normal vector in the +Y axis direction
    LEFT = 5 # the face vector with normal vector in the -X axis direction
    BACK = 6 # the face vector with normal vector in the -Y axis direction
```

When taking measurements from a timber, we measure from a *reference feature* of the timber. Since timbers are stick-like (根) objects rather than box-like (块) objects, we distinguish between faces/edges on the ends of the timber and on the sides of the timber. We refer to features on the sides of the timber as *long*.


```
class TimberReferenceEnd(Enum):
    TOP = 1
    BOTTOM = 2
```

```
class TimberReferenceLongEdge(Enum):
    RIGHT_FORWARD = 7
    FORWARD_LEFT = 8
    LEFT_BACK = 9
    BACK_RIGHT = 10
```

```
class TimberReferenceLongFace(Enum):
    RIGHT = 3
    FORWARD = 4
    LEFT = 5
    BACK = 6
```


### measuring from reference features (TODO DELETE this section, these classes don't exist yet)

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

## member names

When timbers are part of a structure, they may be referred to as members. Members have no logical distinction from each other as far as GiraffeCAD is concerned, but the concepts are useful for explaining the intended use of various functions and you may also want to use these names to organize your projects. The remainder of this doc will assume knowledge of various member names to elaborate certain concepts.


# Footprint

A support class representing the footprint of the structure in the XY plane to help position and orient timbers. Footprints are always defined at Z=0 and timbers defined on the footprint are always above Z=0.


```
class Footprint:
    # a list of points defining the corners of the footprint, the last point is connected to the first point
    corners : list[V2]
```

## inside, outside, sides and corners

Footprints consist of a set of boundary corners that form a non intersecting boundary consisting of boundary sides. This boundary defines an inside and outside to the boundary which are used to position timbers around the boundary. 


```
class FootprintLocation(Enum):
    INSIDE = 1
    CENTER = 2
    OUTSIDE = 3
```

Timbers are positioned either on boundary sides or boundary corners. They can either be positioned "inside", "outside", "on center". Each boundary corner and boundary side also have a notion of inside and outside. 
For boundary sides, the inside side is simply the side of the boundary side that is towards the inside of the boundary and the outside the opposite.
For boundary corners it is a little more complicated because we want to orient vertices of posts around the inside/outside of the boundary corner. This is elaborated in the "From a Footprint" section of "Creating Timbers"




## timber position and orientation relative to footprint

TODO


# Creating Timbers

## Out of Nowhere

TODO create_timber create_axis_aligned_timber

## From a Footprint

It is often best to create your timbers from a footprint. Mudsills and Posts can be created on the *inside*, *outside* and *center* of a footprint.



### mudsills go on boundary sides

- A mudsill on a boundary side of a footprint will have its length run from one boundary corner to the other boundary corner of the boundary side.
- A mudsill on the inside/outside of a boundary side will have an edge lying on the boundary side with the mudsill on the inside/outside side of the boundary side.
- A mudsill on center of a boundary side will have its midline lying on the same plane 

create_horizontal_timber_on_footprint

### posts go on points on boundary sides

- A post can be positioned on a point along a boundary side. 
- If the post is on center, it will have its center of the bottom face lying on the point, and 2 of the edges of the bottom face will be parallel to the boundary side.
- If the post is inside/outside, it will have one edge of the bottom face lying on the boundary side with the center of that edge coincident with the point, with the rest of the post inside/outside of the boundary side.

create_vertical_timber_on_footprint_side

### posts go on boundary corners

- A post can be positioned on the inside/outside of a boundary corner IF the boundary corner is orthogonal, i.e. the two boundary sides coming out of the boundary corner are perpendicular.
- If it is on the inside of the boundary corner, position the post such that it overlaps with the inside of the boundary, has one vertex of its bottom face lying on the boundary corner, and has 2 edges of its bottom face aligning with the 2 boundary sides coming out of the boundary corner. 
- If it is on the outside of the boundary corner, then position the post first on the inside of the boundary corner, and take the vertex of its bottom face that is opposite to the vertex lying on the boundary corner and move it so that the opposite vertex is instead on the boundary corner.

create_vertical_timber_on_footprint_corner


## Joining Timbers
 
TODO

## Extending or Splitting Timbers

TODO



# Joints 


