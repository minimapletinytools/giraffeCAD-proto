# FreeCAD Test Scripts

This directory contains test scripts for rendering GiraffeCAD models in FreeCAD.

## Quick Start - Use the Launchers

For the best development experience, use the **launcher macros** which automatically reload all modules:

### Mortise and Tenon Test
```python
# In FreeCAD: Macro → Macros → run_mortise_and_tenon.py → Execute
```

### Basic Joints Test
```python
# In FreeCAD: Macro → Macros → run_basic_joints.py → Execute
```

## Why Use Launchers?

The launcher scripts (`run_*.py`) provide automatic module reloading:

✅ **No FreeCAD restart needed** - Make code changes and re-run the macro  
✅ **Reloads all modules** - GiraffeCAD modules, renderers, examples, and test scripts  
✅ **Saves development time** - Instant feedback on code changes

### Without Launchers
❌ Must restart FreeCAD after every code change  
❌ Python module caching prevents updates from being picked up  
❌ Slow development cycle

## File Structure

### Launcher Scripts (Use These!)
- **`run_mortise_and_tenon.py`** - Launcher for mortise & tenon test (with module reload)
- **`run_basic_joints.py`** - Launcher for basic joints test (with module reload)

### Test Scripts (Called by Launchers)
- **`test_mortise_and_tenon.py`** - Mortise & tenon rendering logic
- **`test_basic_joints.py`** - Basic joints rendering logic

### Renderer
- **`giraffe_render_freecad.py`** - FreeCAD rendering engine for GiraffeCAD

## Usage

### Method 1: FreeCAD GUI (Recommended)

1. Open FreeCAD
2. Go to **Macro → Macros...**
3. Navigate to this directory (`freecad/`)
4. Select `run_mortise_and_tenon.py` or `run_basic_joints.py`
5. Click **Execute**

**Making Changes:**
- Edit your code in any GiraffeCAD module
- Re-run the same launcher macro in FreeCAD
- Changes are automatically reloaded!

### Method 2: Command Line

```bash
# From the freecad/ directory
freecad run_mortise_and_tenon.py
# or
freecad run_basic_joints.py
```

## What Gets Reloaded

The launcher scripts reload modules in dependency order:

1. `code_goes_here.moothymoth` - Core math/orientation
2. `code_goes_here.footprint` - 2D footprints
3. `code_goes_here.meowmeowcsg` - CSG operations
4. `code_goes_here.timber` - Timber data structures
5. `code_goes_here.construction` - Construction functions
6. `code_goes_here.basic_joints` - Basic joint functions
7. `code_goes_here.mortise_and_tenon_joint` - Mortise & tenon functions
8. `giraffe` - Main API module
9. `giraffe_render_freecad` - FreeCAD renderer
10. `examples.*` - Example modules
11. `test_*` - The test script itself

## Troubleshooting

**Import Errors:**
- Make sure you're running from the `freecad/` directory
- Check that the parent directory contains `code_goes_here/` and `examples/`

**Module Not Reloading:**
- Check the console output to see which modules were reloaded
- If a module shows "not loaded yet", it will be imported fresh

**FreeCAD Crashes:**
- Some changes (like dataclass structure changes) may still require a FreeCAD restart
- For most code changes, the launcher should work fine

## Output Example

```
======================================================================
GiraffeCAD FreeCAD - Mortise and Tenon Test Launcher
======================================================================

Reloading all GiraffeCAD modules...
  ✓ Reloaded code_goes_here.moothymoth
  ✓ Reloaded code_goes_here.timber
  ✓ Reloaded code_goes_here.construction
  ✓ Reloaded code_goes_here.mortise_and_tenon_joint
  ✓ Reloaded giraffe_render_freecad
  ✓ Reloaded examples.mortise_and_tenon_joint_examples
  ✓ Reloaded test_mortise_and_tenon

Module reload complete. Running test...

Creating basic mortise and tenon joint...
Total timbers created: 2

Rendering timbers in FreeCAD...
Successfully rendered 2/2 timbers
```

