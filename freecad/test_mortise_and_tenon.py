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
from examples.mortise_and_tenon_joint_examples import create_all_mortise_and_tenon_examples


def create_mortise_and_tenon_example():
    """
    Create all mortise and tenon joint examples with spacing.
    """
    print("\nCreating all mortise and tenon joint examples...")
    all_cut_timbers = create_all_mortise_and_tenon_examples()
    
    return all_cut_timbers


def main():
    """Main function."""
    print("="*70)
    print("GiraffeCAD FreeCAD - All Mortise and Tenon Joint Examples")
    print("="*70)
    
    # Create mortise and tenon examples
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
    print("\nExamples rendered (spaced 72 inches apart):")
    print("  1. Basic 4x4 Mortise and Tenon")
    print("  2. 4x6 into 6x8 Mortise and Tenon")
    print("  3. Through Tenon with 6\" Stickout")
    print("  4. Full-Size 4x4 Tenon into 6x6")
    print("\nCheck the Model tree on the left to see all timbers and their cuts")


# Run the test
if __name__ == "__main__":
    main()
else:
    # If imported as a module, also run main
    main()

