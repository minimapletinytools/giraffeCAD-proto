"""
Test script for rendering all basic joint examples in FreeCAD.
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
    """Main function."""
    print("="*60)
    print("GiraffeCAD FreeCAD - All Basic Joints Test")
    print("="*60)
    
    # Create all joint examples
    print("\nCreating all joint examples...")
    cut_timbers = create_all_joint_examples()
    
    print(f"Total timbers created: {len(cut_timbers)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers in FreeCAD...")
    success_count = render_multiple_timbers(cut_timbers)
    
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(cut_timbers)} timbers")
    print("="*60)
    print("\nJoints are spaced 2m apart along the X axis")
    print("Check the Model tree on the left to see all joint components")


# Run the test
if __name__ == "__main__":
    main()
else:
    # If imported as a module, also run main
    main()

