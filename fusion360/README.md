# GiraffeCAD Fusion 360 Integration

This directory contains a complete, self-contained Fusion 360 script for rendering timber frame structures created with GiraffeCAD.

## 🏗️ What's Included

### Core Files
- **`giraffetest.py`** - Main Fusion 360 script with example selector (run this in Fusion 360)
- **`giraffe_render_fusion360.py`** - Fusion 360 rendering engine
- **`giraffe_render_fusion360_OLD.py`** - Previous version (backup)

### Imported from Parent Directory
- **`../giraffe.py`** - Core GiraffeCAD timber framing library
- **`../code_goes_here/`** - Core modules (moothymoth, footprint, etc.)
- **`../examples/sawhorse_example.py`** - Sawhorse structure
- **`../examples/oscarshed.py`** - Oscar's Shed structure
- **`../examples/reference/basic_joints_example.py`** - Joint type demonstrations

### Local Dependencies
- **`libs/`** - Contains locally installed Python packages:
  - `sympy` - Symbolic mathematics
  - `mpmath` - Multiple precision arithmetic (sympy dependency)

### Test & Utility Files
- **`test_local.py`** - Test script to verify all dependencies work
- **`giraffetest.manifest`** - Fusion 360 script manifest
- **`ScriptIcon.svg`** - Script icon for Fusion 360

## 🚀 How to Use

### 1. In Fusion 360
1. Open Fusion 360
2. Go to **Utilities → Scripts and Add-ins**
3. Click **Scripts** tab
4. Click the **+** button next to "My Scripts"
5. Navigate to this `giraffetest` folder
6. Select the folder and click **OK**
7. The "giraffetest" script should now appear in your scripts list
8. Select it and click **Run**

### 2. What the Script Does
When you run the script, it will:

1. **Show a dialog** asking which example to render:
   - **YES** = Basic Joints Examples (5 different joint types)
   - **NO** = Oscar's Shed (8×4 ft timber frame structure)
   - **CANCEL** = Sawhorse (simple two-leg sawhorse)

2. **Clear the current design** (removes existing geometry)

3. **Generate the selected structure** with all joints

4. **Render in 3D** as properly positioned and oriented rectangular prisms

### 3. Available Examples

#### Basic Joints Examples (12 timbers)
Demonstrates 6 joint types, each with two 90×90mm timbers:
- **Miter Joint** - 67° angled cuts (non-axis-aligned)
- **Miter Joint (Face Aligned)** - Miter optimized for aligned faces
- **Corner Joint** - One timber cut, one straight
- **Butt Joint** - One timber butts into another
- **Splice Joint** - End-to-end scarf joint
- **House Joint** - Groove cut into housing timber, housed timber fits in (like shelf in upright)

All joints are spaced 2m apart along the X-axis for easy viewing.

#### Oscar's Shed (24 timbers)
Complete timber frame shed structure:
- 4 Mudsills with miter joints at corners
- 6 Posts (front and back)
- Side girts, front girt, top plates
- 3 Floor joists
- 5 Rafters

#### Sawhorse (6 timbers)
Simple traditional sawhorse:
- 2 mudsills (base rails)
- 2 vertical posts
- 1 top beam
- 1 horizontal stretcher

### 4. Expected Output
- **Components** named with appropriate prefixes (e.g., `Joint_001`, `OscarShed_Timber_001`)
- **Realistic dimensions** (90mm or custom sizes depending on example)
- **Proper assembly** with all joints and cuts visible

## 🧪 Testing

Run the test script to verify everything works:

```bash
python3 test_local.py
```

This will test:
- ✅ All dependencies import correctly
- ✅ GiraffeCAD modules load properly  
- ✅ Example structures can be created
- ✅ All timbers with joints are generated

You can also test examples directly:
```bash
# Test Basic Joints
cd ../examples/reference
python3 basic_joints_example.py

# Test Oscar's Shed
cd ../examples
python3 oscarshed.py
```

## 📐 Technical Details

### Coordinate System
- **RHS (Right-Hand System)** with Z pointing up
- **+X = East**, **+Y = North**, **+Z = Up**
- Units converted from inches to meters internally, then to cm for Fusion 360

### Dependencies Setup
Dependencies are installed locally using:
```bash
pip install --target ./libs sympy
```

This ensures Fusion 360's isolated Python environment can access them.

### Path Import Benefits
- **No file duplication** - GiraffeCAD modules are imported from the parent directory
- **Always up-to-date** - Changes to the main modules are immediately available
- **Cleaner structure** - Only dependencies and the main script are in the giraffetest folder
- **Easier maintenance** - Single source of truth for all GiraffeCAD code

### Architecture
```
fusion360/
├── giraffetest.py (main script with example selector)
├── giraffe_render_fusion360.py (Fusion 360 CSG rendering)
├── libs/ (local dependencies: sympy, mpmath)
└── imports from parent directory:
    ├── ../giraffe.py (timber framing API)
    ├── ../code_goes_here/ (core modules)
    │   ├── moothymoth.py (3D rotations)
    │   ├── footprint.py (2D layouts)
    │   ├── meowmeowcsg.py (CSG operations)
    │   ├── timber.py (timber class)
    │   ├── construction.py (timber helpers)
    │   └── basic_joints.py (joint functions)
    └── ../examples/
        ├── sawhorse_example.py
        ├── oscarshed.py
        └── reference/basic_joints_example.py
```

## 🔧 Troubleshooting

### Import Errors
If you get import errors:
1. Make sure all files are in the same directory
2. Check that `libs/` contains `sympy`, `numpy`, and `mpmath` folders
3. Run `test_local.py` to diagnose issues

### Rendering Issues
If timbers don't appear correctly:
1. Check the TEXT COMMANDS window in Fusion 360 for detailed error messages
2. Ensure you have an active design document
3. Try running the script on a new, empty design

### Missing Timbers
If some timbers don't render:
- Check the script output - it reports how many timbers were successfully created
- Each timber should become a separate component in the browser

## 🦒 About GiraffeCAD

GiraffeCAD is a Python library for programmatic timber frame design, featuring:
- **Precise joint definitions** (mortise & tenon, etc.)
- **3D timber positioning** and orientation
- **Symbolic math** for exact calculations
- **Fusion 360 integration** for 3D visualization

Perfect for traditional timber framing, furniture making, and architectural prototyping! 