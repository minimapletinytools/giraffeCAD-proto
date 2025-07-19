# GiraffeCAD - Timber Framing CAD System

A Python-based CAD system for timber framing design and analysis, based on the API specification in `morenotes.md`.

## Features

- **Timber Creation**: Create timbers with custom dimensions, positions, and orientations
- **Footprint Support**: Define building footprints and place timbers relative to them
- **Joint System**: Create various types of joints including mortise and tenon
- **Spatial Math Integration**: Uses SE2 for 2D transformations and SE3 for 3D transformations
- **Type Safety**: Full type annotations for better development experience

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. The system requires:
   - `numpy` >= 1.21.0
   - `spatialmath-python` >= 1.1.0

## Quick Start

```python
import numpy as np
from giraffe import *

# Create a footprint
footprint_points = [
    SE2([0.0, 0.0]),
    SE2([5.0, 0.0]),
    SE2([5.0, 3.0]),
    SE2([0.0, 3.0])
]
footprint = Footprint(footprint_points)

# Create a vertical post
post = create_vertical_timber_on_footprint(
    footprint=footprint,
    footprint_index=0,
    length=2.5
)

# Create a horizontal beam
beam = create_horizontal_timber_on_footprint(
    footprint=footprint,
    footprint_index=0,
    length=5.0,
    location_type=TimberLocationType.CENTER
)

# Create a joint
joint = simple_mortise_and_tenon_joint(
    mortise_timber=post,
    tenon_timber=beam,
    tenon_thickness=0.1,
    tenon_length=0.2,
    tenon_depth=0.15
)
```

## Core Concepts

### Coordinate System
- XY is the "ground" plane
- Z is "up"
- Right-hand coordinate system
- +X is "right/east", +Y is "forward/north"

### Timber Orientation
Timbers are oriented using:
- **Length Direction**: The primary axis of the timber
- **Face Direction**: The secondary axis defining the face orientation
- **Bottom Position**: The center point of the bottom cross-section as SE3
- **Size**: Cross-sectional dimensions as SE2

### Footprint System
The footprint defines the boundary of the structure in the XY plane:
- List of SE2 transformations defining the boundary
- Last point connects to the first point
- Used for positioning timbers relative to the structure

### Joint System
Joints are created through cut operations:
- **TenonCutOperation**: Creates tenons (protruding parts)
- **MortiseCutOperation**: Creates mortises (recessed parts)
- **Joint**: Groups related cut operations

## API Reference

### Core Classes

- `Timber`: Represents a timber with position, orientation, and dimensions
- `Footprint`: Defines the building boundary
- `Joint`: Groups cut operations for connecting timbers
- `CutTimber`: A timber with applied cuts/joints

### Timber Creation Functions

- `create_timber()`: Create a timber with custom orientation
- `create_axis_aligned_timber()`: Create axis-aligned timbers
- `create_vertical_timber_on_footprint()`: Create vertical posts
- `create_horizontal_timber_on_footprint()`: Create horizontal beams
- `extend_timber()`: Extend existing timbers
- `join_timbers()`: Connect two timbers with a new timber
- `join_perpendicular_on_face_aligned_timbers()`: Join face-aligned timbers

### Joint Functions

- `simple_mortise_and_tenon_joint()`: Create basic mortise and tenon joints

## Example

Run the example script to see a complete timber frame structure:

```bash
python example.py
```

This creates a rectangular timber frame with:
- 4 vertical posts at the corners
- 4 horizontal beams connecting the posts
- A mortise and tenon joint
- A connecting timber between posts

## Development

The system is designed to be extensible. Key areas for extension:
- Additional joint types (dovetail, splice, etc.)
- More complex cut operations
- Visualization and export capabilities
- Analysis tools for structural integrity

## License

See LICENSE file for details.
