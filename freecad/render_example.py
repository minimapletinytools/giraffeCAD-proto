"""
Example script demonstrating GiraffeCAD rendering in FreeCAD.

This script renders the basic joints examples from examples/reference/basic_joints_example.py
in FreeCAD, showing all the different joint types supported by GiraffeCAD.

SETUP (one-time):
1. Open FreeCAD
2. Go to Edit → Preferences → Python → Macro
3. Click "Add" under "Macro path"
4. Navigate to and select the freecad/ folder
5. Click OK

TO RUN:
1. Open FreeCAD
2. Go to Macro → Macros...
3. Select "render_example.py" from the list
4. Click "Execute"

The rendered structures will appear in the 3D view!
"""

import sys
import os
import importlib

# Add GiraffeCAD to path
script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Also add the current directory (freecad/) to path for FreeCAD macro mode
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import and reload the FreeCAD renderer to bypass cache
import giraffe_render_freecad
importlib.reload(giraffe_render_freecad)
from giraffe_render_freecad import render_multiple_timbers, clear_document

# Import the basic joints examples
from examples.reference.basic_joints_example import create_all_joint_examples


def main():
    """Main function to run the example."""
    print("\n" + "="*60)
    print("GiraffeCAD FreeCAD - Basic Joints Examples")
    print("="*60)
    print("Rendering all basic joint types...")
    print()
    
    # Create all joint examples from basic_joints_example.py
    cut_timbers = create_all_joint_examples()
    
    print()
    print(f"Total timbers created: {len(cut_timbers)}")
    
    # Clear the document and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers in FreeCAD...")
    success_count = render_multiple_timbers(cut_timbers)
    
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(cut_timbers)} timbers")
    print("="*60)
    
    # Instructions for viewing
    print("\nTo view the rendered structure:")
    print("1. Press 'V' then '0' to view from front")
    print("2. Press 'V' then '2' to view from top")
    print("3. Use middle mouse button to rotate view")
    print("4. Use scroll wheel to zoom")
    print("5. Check the Model tree on the left to see all joints")
    print("\nJoints are spaced 2m apart along the X axis:")
    print("  - Miter Joint (67°) at x=0.0m")
    print("  - Miter Joint (Face Aligned) at x=2.0m")
    print("  - Butt Joint at x=4.0m")
    print("  - Splice Joint at x=6.0m")
    print("  - House Joint at x=8.0m")


# Run the example
if __name__ == "__main__":
    main()
else:
    # If imported as a module, also run main
    main()

