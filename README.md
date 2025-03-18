# GiraffeCAD notes


# Helpers
## ReferenceCorner
### properties
- corner: V3
- rotation: Quaternion 
### derived properties
- orientation: V3 (x = length, y = width, z = height)

## Footprint
### properties
- corners: List[(float, float)]
### derived properties
- oriented_corners: `List[ReferenceCorner]`
### method
- contains_point(point: (float, float)) -> bool


# Members
## Timber
### properties
- box
- ref corner 
### derived properties
- bottom_face   
### methods
- fromReferenceCorner(l: float, w: float, h: float)

# Joints
## mortise and tenon
### requirements
- timbers must have orthogonal orientation
- tenon box cross section must completely be contained in mortise box
### parameters
- mortise: timber
- tenon: timber
- tenon_insertion_dir: orientation
- tenon_crosssection_size: (float, float)
	- this is relative to the mortise timber orientation! Y is in the direction of the mortise timber, X is orthogonal to it
- tenon_insertion_depth: float
- fixation_type: "none" | "drawbore" | "tusk"
- drawbore_position: float
	- offset of drawbore relative to shoulder of mortise
- drawbore_offset: float
	- default = 10% of size
	- offset of drawbore hole in tenon 
- drawbore_shape: "round" | "square"
- drawbore_size: float
	- diameter of drawbore hole or width of drawbore square mortise
- tusk_size: (float, float)
	- size of tusk tenon, Y is in the direction of the mortise timber, X is orthogonal to it
### operation
- validate_parameters
- mortise
	- create square on mortise timber face with size of tenon cross section
		- extrude mortise to tenon insertion depth
	- position drawbore hole on mortise timber face
		- extrude
- tenon
	- substract shoulder of mortise and beyond from tenon
	- create square on tenon timber face with size of tenon cross section
		- extrude tenon to tenon insertion depth
	- position drawbore or tusk hole on tenon
		- extrude


# Utility Functions
## Member creation
- create_post_from_ReferenceCorner(corner: ReferenceCorner, size: (float, float, float)) -> Timber
- create_mudsill_from_ReferenceCorner(cornerA: ReferenceCorner, cornerB: ReferenceCorner, size: (float, float, float)) -> Timber
    - mudsill points from A to B
- create_girt_to_span_posts(postA: Timber, postB: Timber, startHeight: float, size: (float, float)) -> Timber
    - postA and postB must be parallel
    - reference corner is same as PostA rotated towards postB + Z*startHeight
    - size is (length, width)
    - girt Z points from A to B
    - girt size passes through to outside faces on posts
- create_plate_over_posts(postA: Timber, postB: Timber, size: (float, float), stickout: float) -> Timber
    - postA and postB must be parallel and end at the same Z position
    - reference corner Z is orientated from PostA to PostB and X is pointed in Z direction of postA
    - size is (length, width)
    - plate Z points from A to B
    - plate "height" (Z) passes through to outside faces on posts + stickout
- create_brace(timberA: Timber, timberB: Timber, size: (float, float), angle: float) -> Timber
    - timberA and timberB must be orthogonal
    - TODO which side is brace on
    - reference corner is Z orientated TODO
    - size is (length, width)
    - brace "height" (Z) passes through to outside faces on timbers (the longer of the 2 choices)


# OPEN Qs
- reduce mortise and tenon to minimal requirements so you can do non rectangle timbers
	- may need separate function for roundo ones
	- minimal req is 1 timber and 1 external face (face actually determines direction of tenon)
-need orientation helper methods
	-outer footprint utility


# pseudocode for timber cube

```python
# constants (units in inches)
TIMBER_SIZE = 3
LENGTH = 5*12
WIDTH = 7*12
HEIGHT = 8*12

# first define the boundary
footprint : Footprint = [(0, 0), (0, WIDTH), (LENGTH, WIDTH), (LENGTH, 0)]

# create posts at each corner
posts : List[Timber] = []

# TODO orient and size timbers correctl
for corner in footprint:
	posts.append(Timber(corner, TIMBER_SIZE, HEIGHT))

# create floor girts
floor_girts : List[Timber] = []

# TODO size floor girts correctly
for post in posts:
	floor_girt.append(Timber(post, LENGTH, TIMBER_SIZE, TIMBER_SIZE))

# create outside tie beams 
outside_tie_beams : List[Timber] = []

# TODO size outside tie beams correctly
for (post1, post2) in (posts[1], posts[2]), (posts[3], posts[0]):
	outside_tie_beams.append(Timber(post1, post2, TIMBER_SIZE, TIMBER_SIZE))

# create eave plates
eave_plates : List[Timber] = []

# TODO size eave plates correctly
for (post1, post2) in (posts[0], posts[1]), (posts[2], posts[3]):
	eave_plates.append(Timber(post1, post2, LENGTH, TIMBER_SIZE))

# create rafters
rafter_plates : List[Timber] = []

# TODO size rafter plates correctly
# TODO uniformly divide eave plates and attach rafters
```
