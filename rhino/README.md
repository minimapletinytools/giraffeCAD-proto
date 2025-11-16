UNTESTED CUZ RIHNO LICENSE EXPIERD LOL 

# GiraffeCAD for Rhinoceros 3D

This directory contains the Rhino Python implementation for rendering GiraffeCAD timber frame structures in Rhinoceros 3D.

## Files

- **`giraffe_render_rhino.py`** - Core rendering module that converts GiraffeCAD timbers to Rhino geometry
- **`render_oscarshed.py`** - Script to render Oscar's Shed in Rhino
- **`test_render.py`** - Simple test script with 3 basic timbers

## Requirements

- Rhinoceros 3D (Version 6 or later recommended)
- Rhino Python (included with Rhino)
- GiraffeCAD modules (in parent directory)

## How to Use

### Method 1: Using RunPythonScript Command

1. **Open Rhinoceros 3D**

2. **Run a script:**
   - Type `RunPythonScript` in the Rhino command line
   - Browse to one of the Python files in this directory:
     - `test_render.py` - Simple test with 3 timbers
     - `render_oscarshed.py` - Render Oscar's 8x3.5 ft shed

3. **View the result:**
   - Timbers will be created on the "GiraffeCAD" layer
   - You can hide/show this layer as needed
   - Objects are named according to their function (e.g., "Front Mudsill", "Front Left Post")

### Method 2: Using Rhino's Python Editor

1. **Open the Python Editor:**
   - Type `EditPythonScript` in Rhino command line
   - Or go to Tools → PythonScript → Edit...

2. **Open a script:**
   - File → Open
   - Select `render_oscarshed.py` or `test_render.py`

3. **Run the script:**
   - Click the green "Run" button
   - Or press F5

## Current Features

✅ **Timber Creation**
- Creates box geometry for each timber
- Correctly positions and orients timbers in 3D space
- Assigns names to timber objects
- Organizes timbers on "GiraffeCAD" layer

✅ **Supported Structures**
- Oscar's Shed (8 timbers: 4 mudsills + 4 posts)
- Any structure created with GiraffeCAD API

## Not Yet Implemented

⚠️ **Joints and Cuts**
- Mortise cuts
- Tenon cuts
- Other joinery operations

These will be added in future versions.

## Oscar's Shed Structure

When you run `render_oscarshed.py`, you'll get:

- **Footprint:** 8 ft × 3.5 ft (2.438m × 1.067m)
- **4 Mudsills:** Horizontal timbers on all 4 sides (INSIDE footprint)
  - Front Mudsill
  - Right Mudsill
  - Back Mudsill
  - Left Mudsill
- **4 Posts:** Vertical timbers at corners (inset 6" from corners)
  - Front Left Post (5.5 ft tall)
  - Front Right Post (5.5 ft tall)
  - Back Left Post (5.0 ft tall)
  - Back Right Post (5.0 ft tall)

## Troubleshooting

### "Module not found" errors

If you get import errors, make sure:
1. The GiraffeCAD files are in the parent directory
2. The script can access `giraffe.py`, `footprint.py`, and `moothymoth.py`
3. Python can find the `sympy` library

### Objects appear in wrong location

- Check your Rhino units (type `Units` in command line)
- GiraffeCAD uses meters internally
- Make sure you're in the correct view (type `Top`, `Front`, or `Perspective`)

### Script runs but nothing appears

- Check if the "GiraffeCAD" layer is visible
- Type `SelLayer` and select "GiraffeCAD" to select all objects on that layer
- Type `Zoom` → `Selected` to zoom to the created objects

## Customization

You can modify parameters in `examples/oscarshed.py`:

```python
# Footprint dimensions (in feet)
base_width = 8.0      # Long dimension
base_length = 3.5     # Short dimension

# Post parameters
post_inset = 0.5      # 6 inches from corners
post_back_height = 5.0    # Back posts height
post_front_height = 5.5   # Front posts height
```

After modifying, just run `render_oscarshed.py` again.

## API Overview

### Rendering Functions

```python
# Render a single timber
guid = render_timber(timber, name="My Timber", layer="GiraffeCAD")

# Render a CutTimber (timber with joints)
guid = render_cut_timber(cut_timber, name="Post", layer="GiraffeCAD")

# Render multiple timbers
count = render_multiple_timbers(cut_timbers, base_name="Timber", layer="GiraffeCAD")

# Clear all objects from GiraffeCAD layer
clear_giraffeCAD_objects()
```

## Future Development

Planned features:
- [ ] Mortise and tenon geometry
- [ ] Joint visualization
- [ ] Material assignments
- [ ] Automated cutting plans
- [ ] BOM (Bill of Materials) export

## Support

For issues or questions, refer to the main GiraffeCAD documentation in the parent directory.

