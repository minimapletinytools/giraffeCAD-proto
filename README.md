# HorseCoAD

HorseCoAD is a Code Aided Design library for programmatically designing timber framed structures.

HorseCoAD is written as an **AI friendly** library meaning it was designed to be easily understood and used by AI agents. 

## Current State

HorseCoAD is intended to ship with its own viewing app as a VSCode extension.
Until then, HorseCoAD designs is visualized by writing to Fusion 360 and FreeCAD via their scripting APIs. This is intended to be replaced with exporting to common CAD file formats in the future as the scripting API workflow for most CAD programs is clunky.


## Trying out Examples

### FreeCAD Integration

To render structures in FreeCAD (open source, free):

1. **Install FreeCAD** (version 0.19 or later)
   - Download from https://www.freecad.org/
   - Or use package manager: `brew install freecad` (macOS)

2. **Set up macro folder** (one-time setup):
   - Open FreeCAD
   - Go to **Edit** → **Preferences** → **Python** → **Macro**
   - Click **Add** under "Macro path"
   - Navigate to and select: `/path/to/giraffeCAD-proto/freecad`
   - Click **OK**

3. **Run the renderer**:
   - Open FreeCAD
   - Go to **Macro** → **Macros...**
   - Select `render_example.py` from the list
   - Click **Execute**
   
   The rendered structure will appear in FreeCAD's 3D view!

### Fusion 360 Integration

To render the example in Autodesk Fusion 360:

#### 1. Setup Fusion 360 Script Environment

1. Navigate to the `fusion360/` directory in the project
2. Install local dependencies for Fusion 360's isolated Python environment:

```bash
cd fusion360
pip install --target libs sympy
```

#### 2. Add Script to Fusion 360

1. Open Autodesk Fusion 360
2. Go to **Design** workspace
3. Click **Utilities** → **ADD-INS** → **Scripts and Add-Ins** (or just `s` and type in "scripts and add-ins")
4. Click the **+** button next to "My Scripts"
5. Navigate to the `fusion360/` folder and select it
6. You should now see "giraffetest" in your scripts list

#### 3. Run the Script

1. Select "giraffetest" from the scripts list
2. Click **Run**
3. The script will:
   - Clear any existing design
   - Generate the sawhorse geometry using your selected example
   - Render all timbers as 3D components in Fusion 360
   - Apply proper transformations and positioning

#### 4. What You'll See

TODO
