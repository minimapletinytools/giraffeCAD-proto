"""
Test script for rendering Oscar's Shed in FreeCAD.
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

# Import Oscar's Shed example
from examples.oscarshed import create_oscarshed


def main():
    """Main function."""
    print("="*60)
    print("GiraffeCAD FreeCAD - Oscar's Shed")
    print("="*60)
    
    # Create Oscar's Shed
    print("\nCreating Oscar's Shed structure...")
    cut_timbers = create_oscarshed()
    
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
    print("\nOscar's Shed: 8ft x 4ft timber frame structure")
    print("Check the Model tree on the left to see all components:")
    print("  - 4 mudsills (with miter joints)")
    print("  - 6 posts (butt joints to mudsills)")
    print("  - Girts (side and front)")
    print("  - Top plates (with rafter pockets)")
    print("  - 3 joists")
    print("  - 5 rafters")


# Run the test
if __name__ == "__main__":
    main()
else:
    # If imported as a module, also run main
    main()

