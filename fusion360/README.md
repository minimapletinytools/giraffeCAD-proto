# GiraffeCAD Fusion 360 Integration

This directory contains a complete, self-contained Fusion 360 script for rendering timber frame structures created with GiraffeCAD.

## 🏗️ What's Included

### Core Files
- **`giraffetest.py`** - Main Fusion 360 script (run this in Fusion 360)
- **`../giraffe.py`** - Core GiraffeCAD timber framing library (imported from parent)
- **`../moothymoth.py`** - 3D orientation and rotation math using sympy (imported from parent)
- **`../giraffe_render_fusion360.py`** - Fusion 360 rendering engine (imported from parent)
- **`../sawhorse_example.py`** - Complete sawhorse example with joints (imported from parent)

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

1. **Clear the current design** (removes existing geometry)
2. **Create a sawhorse structure** with 6 timbers:
   - 2 mudsills (base rails)
   - 2 vertical posts
   - 1 top beam
   - 1 horizontal stretcher
3. **Generate mortise & tenon joints** between all connected timbers
4. **Render in 3D** as properly positioned and oriented rectangular prisms

### 3. Expected Output
- **6 components** named `Sawhorse_Timber_001` through `Sawhorse_Timber_006`
- **Realistic dimensions** (converted from inches to metric)
- **Proper assembly** with timbers positioned according to traditional timber framing

## 🧪 Testing

Run the test script to verify everything works:

```bash
python3 test_local.py
```

This will test:
- ✅ All dependencies import correctly
- ✅ GiraffeCAD modules load properly  
- ✅ Sawhorse creation works
- ✅ All 6 timbers with joints are generated

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
giraffetest/
├── giraffetest.py (main script)
├── libs/ (local dependencies: sympy, mpmath)
└── imports from parent directory:
    ├── ../sawhorse_example.py (creates timber structure)
    ├── ../giraffe.py (timber framing library)
    ├── ../moothymoth.py (3D math with sympy)
    └── ../giraffe_render_fusion360.py (renders in Fusion 360)
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