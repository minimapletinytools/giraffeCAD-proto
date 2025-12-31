"""
Test script for rendering mortise and tenon joint examples in FreeCAD.

NOTE: To automatically reload all modules, use run_mortise_and_tenon.py instead.
This allows you to make code changes without restarting FreeCAD.
"""

import sys
import os

# Add GiraffeCAD to path
script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Also add the current directory (freecad/) to path for FreeCAD macro mode
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the FreeCAD renderer and examples
from giraffe_render_freecad import render_multiple_timbers, clear_document
from examples.mortise_and_tenon_joint_examples import example_basic_mortise_and_tenon


def create_mortise_and_tenon_example():
    """
    Create a basic mortise and tenon joint example.
    """
    print("\nCreating basic mortise and tenon joint...")
    joint = example_basic_mortise_and_tenon()
    
    # Extract the cut timbers from the joint
    all_cut_timbers = []
    for cut_timber in joint.partiallyCutTimbers:
        all_cut_timbers.append(cut_timber)
    
    return all_cut_timbers


def main():
    """Main function."""
    print("="*70)
    print("GiraffeCAD FreeCAD - Mortise and Tenon Joint Test")
    print("="*70)
    
    # Create mortise and tenon example
    cut_timbers = create_mortise_and_tenon_example()
    
    print(f"\nTotal timbers created: {len(cut_timbers)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers in FreeCAD...")
    success_count = render_multiple_timbers(cut_timbers)
    
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(cut_timbers)} timbers")
    print("="*70)
    print("\nConfiguration:")
    print("  • Vertical post (tenon timber) with bottom at origin")
    print("  • Horizontal beam (mortise timber) centered at origin along X axis")
    print("\nCheck the Model tree on the left to see both timbers and their cuts")


# Run the test
if __name__ == "__main__":
    main()
else:
    # If imported as a module, also run main
    main()

