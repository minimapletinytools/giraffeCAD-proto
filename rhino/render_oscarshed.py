"""
Render Oscar's Shed in Rhinoceros 3D.

This script imports the Oscar's Shed design from GiraffeCAD and renders it in Rhino.

To use:
1. Open Rhinoceros 3D
2. Type "RunPythonScript" in the command line
3. Browse to and select this file
4. The shed will be rendered on the "GiraffeCAD" layer
"""

import sys
import os

# Add parent directory to path to import GiraffeCAD modules
script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import GiraffeCAD modules
from examples.oscarshed import create_oscarshed

# Import Rhino renderer from same directory
sys.path.insert(0, script_dir)
from giraffe_render_rhino import render_multiple_timbers, clear_giraffeCAD_objects

def main():
    """Main function to render Oscar's Shed."""
    print("\n" + "="*60)
    print("GIRAFFECD: Rendering Oscar's Shed in Rhino")
    print("="*60 + "\n")
    
    # Clear previous GiraffeCAD objects
    print("Clearing previous GiraffeCAD objects...")
    clear_giraffeCAD_objects()
    
    # Create Oscar's Shed structure
    print("Creating Oscar's Shed structure...")
    cut_timbers = create_oscarshed()
    print(f"Created {len(cut_timbers)} timbers\n")
    
    # Render in Rhino
    success_count = render_multiple_timbers(cut_timbers, "OscarShed", "GiraffeCAD")
    
    print("\n" + "="*60)
    print(f"COMPLETE: {success_count}/{len(cut_timbers)} timbers rendered")
    print("="*60 + "\n")
    
    return success_count

# Run the main function
if __name__ == "__main__":
    main()

