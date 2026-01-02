"""
GiraffeCAD FreeCAD Examples Runner - automatically reloads all modules.

This script provides multiple example rendering functions with automatic module reloading,
so you can make changes to your code and re-run this macro without restarting FreeCAD.

SETUP (one-time):
1. Open FreeCAD
2. Go to Edit → Preferences → Python → Macro
3. Click "Add" under "Macro path"
4. Navigate to and select the freecad/ folder
5. Click OK

TO RUN:
1. Open FreeCAD
2. Go to Macro → Macros...
3. Select "run_examples.py" from the list
4. Click "Execute"

TO CHANGE WHICH EXAMPLE RENDERS:
Edit the EXAMPLE_TO_RENDER variable below.
"""

import sys
import os
import importlib

# Add GiraffeCAD to path
script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


# ============================================================================
# CONFIGURATION: Change this to render different examples
# ============================================================================
#EXAMPLE_TO_RENDER = 'basic_joints' 
#EXAMPLE_TO_RENDER = 'oscar_shed'
#EXAMPLE_TO_RENDER = 'mortise_and_tenon'
EXAMPLE_TO_RENDER = 'csg'

# CSG Configuration (only used when EXAMPLE_TO_RENDER = 'csg')
CSG_EXAMPLE_TO_RENDER = 'hexagon_extrusion'  # Options: 'cube_cutout', 'halfplane_cut', 'positioned_cube', 'union_cubes', 'hexagon_extrusion'


def reload_all_modules():
    """Reload all GiraffeCAD modules in dependency order."""
    print("="*70)
    print("GiraffeCAD FreeCAD - Examples Runner")
    print("="*70)
    print("\nReloading all GiraffeCAD modules...")
    
    # List of modules to reload in dependency order
    modules_to_reload = [
        'code_goes_here.moothymoth',
        'code_goes_here.footprint',
        'code_goes_here.meowmeowcsg',
        'code_goes_here.timber',
        'code_goes_here.construction',
        'code_goes_here.basic_joints',
        'code_goes_here.mortise_and_tenon_joint',
        'giraffe',
        'giraffe_render_freecad',
        'examples.reference.basic_joints_example',
        'examples.mortise_and_tenon_joint_examples',
        'examples.oscarshed',
        'examples.test_MeowMeowCSG_examples',
    ]
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            try:
                importlib.reload(sys.modules[module_name])
                print(f"  ✓ Reloaded {module_name}")
            except Exception as e:
                print(f"  ⚠ Error reloading {module_name}: {e}")
        else:
            print(f"  - {module_name} not loaded yet")
    
    print("\nModule reload complete.\n")


def render_basic_joints():
    """
    Render all basic joint examples.
    
    Includes: miter joints, butt joints, splice joints, and house joints.
    """
    from giraffe_render_freecad import render_multiple_timbers, clear_document
    from examples.reference.basic_joints_example import create_all_joint_examples
    
    print("="*60)
    print("GiraffeCAD FreeCAD - All Basic Joints")
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
    print("\nJoint types rendered:")
    print("  - Miter Joint (67°)")
    print("  - Miter Joint (Face Aligned)")
    print("  - Butt Joint")
    print("  - Splice Joint")
    print("  - House Joint")


def render_mortise_and_tenon():
    """
    Render mortise and tenon joint examples with pegs.
    
    Includes various mortise and tenon configurations with accessories like pegs.
    """
    from giraffe_render_freecad import render_multiple_timbers, clear_document
    from examples.mortise_and_tenon_joint_examples import create_all_mortise_and_tenon_examples
    
    print("="*70)
    print("GiraffeCAD FreeCAD - Mortise and Tenon Joint Examples")
    print("="*70)
    
    # Create mortise and tenon examples (including accessories like pegs)
    print("\nCreating all mortise and tenon joint examples...")
    cut_timbers, accessories = create_all_mortise_and_tenon_examples(return_accessories=True)
    
    print(f"Total timbers created: {len(cut_timbers)}")
    print(f"Total accessories (pegs/wedges): {len(accessories)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers and accessories in FreeCAD...")
    success_count = render_multiple_timbers(cut_timbers, joint_accessories=accessories)
    
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(cut_timbers)} timbers")
    print(f"Successfully rendered {len(accessories)} accessories")
    print("="*70)
    print("\nExamples rendered (configured in mortise_and_tenon_joint_examples.py):")
    print("  - Mortise and tenon joints with pegs")
    print("\nCheck the Model tree on the left to see all timbers, cuts, and accessories")


def render_oscar_shed():
    """
    Render Oscar's Shed - a complete timber frame structure.
    
    An 8ft x 4ft shed with mudsills, posts, girts, top plates, joists, and rafters.
    """
    from giraffe_render_freecad import render_multiple_timbers, clear_document
    from examples.oscarshed import create_oscarshed
    
    print("="*60)
    print("GiraffeCAD FreeCAD - Oscar's Shed")
    print("="*60)
    
    # Create Oscar's Shed (including accessories like pegs)
    print("\nCreating Oscar's Shed structure...")
    cut_timbers, accessories = create_oscarshed()
    
    print(f"Total timbers created: {len(cut_timbers)}")
    print(f"Total accessories (pegs): {len(accessories)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers and accessories in FreeCAD...")
    success_count = render_multiple_timbers(cut_timbers, joint_accessories=accessories)
    
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(cut_timbers)} timbers")
    print(f"Successfully rendered {len(accessories)} accessories")
    print("="*60)
    print("\nOscar's Shed: 8ft x 4ft timber frame structure")
    print("Check the Model tree on the left to see all components:")
    print("  - 4 mudsills (with miter joints)")
    print("  - 6 posts (mortise & tenon joints to mudsills)")
    print("  - 2 side girts")
    print("  - 1 front girt (with mortise & tenon joints and pegs, spliced in middle)")
    print("  - 2 top plates (with rafter pockets)")
    print("  - 3 joists")
    print("  - 5 rafters")


def render_csg():
    """
    Render CSG test examples.
    
    Tests basic CSG operations like cuts, unions, and extrusions.
    Edit CSG_EXAMPLE_TO_RENDER to choose which example to render.
    """
    from giraffe_render_freecad import render_csg_shape, clear_document, get_active_document
    from examples.test_MeowMeowCSG_examples import EXAMPLES, get_example
    
    print("="*60)
    print("GiraffeCAD FreeCAD - CSG Test")
    print("="*60)
    
    # Get example info
    if CSG_EXAMPLE_TO_RENDER not in EXAMPLES:
        print(f"ERROR: Unknown example '{CSG_EXAMPLE_TO_RENDER}'")
        print(f"Available examples: {list(EXAMPLES.keys())}")
        return
    
    example_info = EXAMPLES[CSG_EXAMPLE_TO_RENDER]
    print(f"Example: {example_info['name']}")
    print(f"Description: {example_info['description']}")
    print()
    
    # Get CSG object
    csg = get_example(CSG_EXAMPLE_TO_RENDER)
    print(f"CSG Type: {type(csg).__name__}")
    print()
    
    # Clear document
    print("Clearing FreeCAD document...")
    clear_document()
    print("Document cleared")
    print()
    
    # Get document
    doc = get_active_document()
    if not doc:
        print("ERROR: Could not get active document")
        return
    
    # Render CSG
    print("Rendering CSG...")
    try:
        # Use a reasonable extent for infinite geometry (10m = 10000mm)
        shape = render_csg_shape(csg, timber=None, infinite_extent=10.0)
        
        if shape is None:
            print("ERROR: Failed to create shape")
            return
        
        # Create FreeCAD object
        obj = doc.addObject("Part::Feature", f"CSG_{CSG_EXAMPLE_TO_RENDER}")
        obj.Shape = shape
        
        # Print bounding box info
        bbox = shape.BoundBox
        print(f"Shape created successfully!")
        print(f"Bounding box (mm):")
        print(f"  X: [{bbox.XMin:.1f}, {bbox.XMax:.1f}]  (width: {bbox.XLength:.1f})")
        print(f"  Y: [{bbox.YMin:.1f}, {bbox.YMax:.1f}]  (depth: {bbox.YLength:.1f})")
        print(f"  Z: [{bbox.ZMin:.1f}, {bbox.ZMax:.1f}]  (height: {bbox.ZLength:.1f})")
        print()
        
        doc.recompute()
        
    except Exception as e:
        print(f"ERROR during rendering: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("="*60)
    print("Rendering Complete!")
    print("="*60)
    print()
    print("Tips:")
    print("  - Use View → Standard Views to change perspective")
    print("  - Check the bounding box dimensions to verify size")
    print("  - For cuts, verify that material was removed")
    print()
    print(f"To test another CSG example, edit CSG_EXAMPLE_TO_RENDER in run_examples.py")
    print(f"Available: {', '.join(EXAMPLES.keys())}")


def main():
    """Main function - reload modules and render selected example."""
    # Reload all modules first
    reload_all_modules()
    
    # Render the selected example
    examples = {
        'basic_joints': render_basic_joints,
        'mortise_and_tenon': render_mortise_and_tenon,
        'oscar_shed': render_oscar_shed,
        'csg': render_csg,
    }
    
    if EXAMPLE_TO_RENDER not in examples:
        print(f"ERROR: Unknown example '{EXAMPLE_TO_RENDER}'")
        print(f"Available examples: {list(examples.keys())}")
        print("\nEdit EXAMPLE_TO_RENDER in run_examples.py to change the example.")
        return
    
    print(f"Running example: {EXAMPLE_TO_RENDER}\n")
    examples[EXAMPLE_TO_RENDER]()
    
    print("\n" + "="*70)
    print("To render a different example, edit EXAMPLE_TO_RENDER in run_examples.py")
    print(f"Available: {', '.join(examples.keys())}")
    print("="*70)


# Run when executed
if __name__ == "__main__":
    main()
else:
    # If imported as a module, also run main
    main()

