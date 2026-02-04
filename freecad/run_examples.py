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
EXAMPLE_TO_RENDER = 'oscar_shed'
#EXAMPLE_TO_RENDER = 'mortise_and_tenon'
#EXAMPLE_TO_RENDER = 'construction'
#EXAMPLE_TO_RENDER = 'horsey'
#EXAMPLE_TO_RENDER = 'japanese_joints'
#EXAMPLE_TO_RENDER = 'csg'

# CSG Configuration (only used when EXAMPLE_TO_RENDER = 'csg')
CSG_EXAMPLE_TO_RENDER = 'shoulder_notch'  # Options: 'cube_cutout', 'halfspace_cut', 'positioned_cube', 'lap_cut_timber', 'union_cubes', 'hexagon_extrusion', 'gooseneck_profile', 'shoulder_notch'

# Japanese Joints Configuration (only used when EXAMPLE_TO_RENDER = 'japanese_joints')
# Uncomment ONE of the following lines to select which joint example to render:
JAPANESE_JOINT_EXAMPLE = 'gooseneck_simple'    # Simple vertical gooseneck joint (3"x3" x 2')
#JAPANESE_JOINT_EXAMPLE = 'dovetail_butt'       # Dovetail butt joint / T-joint (4"x4" x 3')


def reload_all_modules():
    """Reload all GiraffeCAD modules in dependency order."""
    print("="*70)
    print("GiraffeCAD FreeCAD - Examples Runner")
    print("="*70)
    print("\nReloading all GiraffeCAD modules...")
    
    # AGGRESSIVE MODULE CLEANUP: Delete ALL GiraffeCAD-related modules
    # This ensures no stale class references remain after reload
    modules_to_delete = []
    for module_name in list(sys.modules.keys()):
        # Delete any module that starts with our project prefixes
        if (module_name.startswith('code_goes_here') or 
            module_name.startswith('examples') or 
            module_name == 'giraffe' or
            module_name.startswith('giraffe.') or
            module_name == 'giraffe_render_freecad'):
            modules_to_delete.append(module_name)
    
    print(f"  Deleting {len(modules_to_delete)} cached modules...")
    
    for module_name in modules_to_delete:
        del sys.modules[module_name]
    
    # List of modules to reload in dependency order
    modules_to_reload = [
        'code_goes_here',  # Reload the package itself first
        'code_goes_here.moothymoth',
        'code_goes_here.footprint',
        'code_goes_here.meowmeowcsg',
        'code_goes_here.timber',
        'code_goes_here.measuring',
        'code_goes_here.construction',
        'code_goes_here.rendering_utils',
        'code_goes_here.joint_shavings',
        'code_goes_here.basic_joints',
        'code_goes_here.mortise_and_tenon_joint',
        'code_goes_here.japanese_joints',
        'code_goes_here.patternbook',
        'giraffe',
        'examples',  # Reload the examples package
        'examples.reference',  # Reload examples.reference subpackage
        'giraffe_render_freecad',
        'examples.reference.basic_joints_example',
        'examples.mortise_and_tenon_joint_examples',
        'examples.horsey_example',
        'examples.oscarshed',
        'examples.japanese_joints_example',
        'examples.irrational_angles_example',
        'examples.construction_examples',
        'examples.MeowMeowCSG_examples',
    ]
    
    # Re-import all modules in dependency order
    for module_name in modules_to_reload:
        try:
            # Use __import__ to load the module fresh
            importlib.import_module(module_name)
        except Exception as e:
            print(f"  ⚠ Error reloading {module_name}: {e}")
    
    print("\nModule reload complete.\n")


def render_basic_joints():
    """
    Render all basic joint examples using PatternBook.
    
    Includes: miter joints, butt joints, splice joints, and house joints.
    """
    from giraffe_render_freecad import render_frame, clear_document
    from examples.reference.basic_joints_example import create_basic_joints_patternbook
    from code_goes_here.moothymoth import m
    
    print("="*60)
    print("GiraffeCAD FreeCAD - All Basic Joints")
    print("="*60)
    
    # Create pattern book and raise all patterns in "basic_joints" group
    print("\nCreating basic joints pattern book...")
    book = create_basic_joints_patternbook()
    
    print("\nRaising all patterns in 'basic_joints' group...")
    frame = book.raise_pattern_group("basic_joints", separation_distance=m(2))
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers in FreeCAD...")
    success_count = render_frame(frame)
    
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print("="*60)
    print("\nJoints are spaced 2m apart along the X axis")
    print("Check the Model tree on the left to see all joint components")
    print("\nJoint types rendered:")
    print("  - Miter Joint (67°)")
    print("  - Miter Joint (Face Aligned)")
    print("  - Butt Joint")
    print("  - Splice Joint")
    print("  - Splice Lap Joint")
    print("  - House Joint")
    print("  - Cross Lap Joint")


def render_mortise_and_tenon():
    """
    Render mortise and tenon joint examples with pegs using PatternBook.
    
    Includes various mortise and tenon configurations with accessories like pegs.
    """
    from giraffe_render_freecad import render_frame, clear_document
    from examples.mortise_and_tenon_joint_examples import create_mortise_and_tenon_patternbook
    from code_goes_here.moothymoth import inches
    
    print("="*70)
    print("GiraffeCAD FreeCAD - Mortise and Tenon Joint Examples")
    print("="*70)
    
    # Create pattern book and raise all patterns in "mortise_tenon" group
    print("\nCreating mortise and tenon pattern book...")
    book = create_mortise_and_tenon_patternbook()
    
    print("\nRaising all patterns in 'mortise_tenon' group...")
    frame = book.raise_pattern_group("mortise_tenon", separation_distance=inches(72))
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    print(f"Total accessories (pegs/wedges): {len(frame.accessories)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers and accessories in FreeCAD...")
    success_count = render_frame(frame)
    
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print(f"Successfully rendered {len(frame.accessories)} accessories")
    print("="*70)
    print("\nExamples rendered:")
    print("  - Basic 4x4 mortise and tenon")
    print("  - 4x6 into 6x8 mortise and tenon")
    print("  - Through tenon with stickout")
    print("  - Full size 4x4 tenon")
    print("  - Offset corner tenon")
    print("  - Mortise and tenon with pegs")
    print("\nCheck the Model tree on the left to see all timbers, cuts, and accessories")


def render_construction():
    """
    Render construction examples using PatternBook.
    
    Tests various reference features (centerline, faces, edges) for positioning.
    """
    from giraffe_render_freecad import render_frame, clear_document
    from examples.construction_examples import create_construction_patternbook
    
    print("="*70)
    print("GiraffeCAD FreeCAD - Construction Examples")
    print("="*70)
    
    # Create pattern book and raise pattern
    print("\nCreating construction pattern book...")
    book = create_construction_patternbook()
    
    print("\nRaising 'posts_with_beam_centerline' pattern...")
    frame = book.raise_pattern("posts_with_beam_centerline")
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers in FreeCAD...")
    success_count = render_frame(frame)
    
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print("="*70)
    print("\nExample rendered:")
    print("  - Construction example: Two 4x4x8 posts with beam using centerline reference")


def render_oscar_shed():
    """
    Render Oscar's Shed using PatternBook.
    
    An 8ft x 4ft shed with mudsills, posts, girts, top plates, joists, and rafters.
    """
    from giraffe_render_freecad import render_frame, clear_document
    from examples.oscarshed import create_oscar_shed_patternbook
    
    print("="*60)
    print("GiraffeCAD FreeCAD - Oscar's Shed")
    print("="*60)
    
    # Create pattern book and raise pattern
    print("\nCreating Oscar's Shed pattern book...")
    book = create_oscar_shed_patternbook()
    
    print("\nRaising 'oscar_shed' pattern...")
    frame = book.raise_pattern("oscar_shed")
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    print(f"Total accessories (pegs): {len(frame.accessories)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers and accessories in FreeCAD...")
    success_count = render_frame(frame)
    
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print(f"Successfully rendered {len(frame.accessories)} accessories")
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


def render_horsey():
    """
    Render Horsey Sawhorse using PatternBook.
    
    A sawhorse with two horizontal beams, two vertical posts, a stretcher, and a top plate.
    All connected with mortise and tenon joints with pegs.
    """
    from giraffe_render_freecad import render_frame, clear_document
    from examples.horsey_example import create_horsey_patternbook
    
    print("="*60)
    print("GiraffeCAD FreeCAD - Horsey Sawhorse")
    print("="*60)
    
    # Create pattern book and raise pattern
    print("\nCreating Horsey Sawhorse pattern book...")
    book = create_horsey_patternbook()
    
    print("\nRaising 'sawhorse' pattern...")
    frame = book.raise_pattern("sawhorse")
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    print(f"Total accessories (pegs): {len(frame.accessories)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers and accessories in FreeCAD...")
    success_count = render_frame(frame)
    
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print(f"Successfully rendered {len(frame.accessories)} accessories")
    print("="*60)
    print("\nHorsey Sawhorse: Simple sawhorse with mortise & tenon joints")
    print("Check the Model tree on the left to see all components:")
    print("  - 2 horizontal beams (feet)")
    print("  - 2 vertical posts")
    print("  - 1 horizontal stretcher")
    print("  - 1 top plate")
    print("  - Mortise & tenon joints with pegs")


def render_japanese_joints():
    """
    Render traditional Japanese timber joints using PatternBook.
    
    Available joints:
    - Lapped Gooseneck Joint (腰掛鎌継ぎ / Koshikake Kama Tsugi) - splices beams end-to-end
    - Dovetail Butt Joint (蟻仕口 / Ari Shiguchi) - connects timbers at right angles
    
    Change JAPANESE_JOINT_EXAMPLE at the top of this file to select which joint to render.
    """
    from giraffe_render_freecad import render_frame, clear_document
    from examples.japanese_joints_example import create_japanese_joints_patternbook
    
    # Select which example to render based on configuration
    joint_examples = {
        'gooseneck_simple': {
            'pattern_name': 'gooseneck_simple',
            'title': 'Japanese Lapped Gooseneck Joint - Simple',
            'description': 'Creating simple vertical post splice...',
            'details': [
                'Lapped Gooseneck Joint (腰掛鎌継ぎ / Koshikake Kama Tsugi)',
                '  - Two 3"x3" x 2\' timbers spliced vertically',
                '  - Simplified version for easier visualization',
                '  - Gooseneck profile creates mechanical interlock'
            ]
        },
        'dovetail_butt': {
            'pattern_name': 'dovetail_butt',
            'title': 'Japanese Dovetail Butt Joint',
            'description': 'Creating T-joint with dovetail connection...',
            'details': [
                'Dovetail Butt Joint (蟻仕口 / Ari Shiguchi)',
                '  - Two 4"x4" x 3\' timbers at right angles',
                '  - Dovetail shape resists pulling apart',
                '  - Used for T-joints and corner connections'
            ]
        }
    }
    
    if JAPANESE_JOINT_EXAMPLE not in joint_examples:
        print(f"ERROR: Unknown Japanese joint example '{JAPANESE_JOINT_EXAMPLE}'")
        print(f"Available examples: {list(joint_examples.keys())}")
        print("\nEdit JAPANESE_JOINT_EXAMPLE in run_examples.py to change the joint.")
        return
    
    example_config = joint_examples[JAPANESE_JOINT_EXAMPLE]
    
    print("="*70)
    print(f"GiraffeCAD FreeCAD - {example_config['title']}")
    print("="*70)
    
    # Create pattern book and raise the selected pattern
    print(f"\n{example_config['description']}")
    print("Creating Japanese joints pattern book...")
    book = create_japanese_joints_patternbook()
    
    print(f"Raising '{example_config['pattern_name']}' pattern...")
    frame = book.raise_pattern(example_config['pattern_name'])
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    print(f"Total accessories: {len(frame.accessories)}")
    
    # Clear and render
    print("\nClearing FreeCAD document...")
    clear_document()
    
    print("\nRendering timbers in FreeCAD...")
    success_count = render_frame(frame)
    
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print("="*70)
    for detail in example_config['details']:
        print(detail)
    print("="*70)


def render_csg():
    """
    Render CSG test examples using PatternBook.
    
    Tests basic CSG operations like cuts, unions, and extrusions.
    Edit CSG_EXAMPLE_TO_RENDER to choose which example to render.
    """
    from giraffe_render_freecad import render_csg_shape, clear_document, get_active_document
    from examples.MeowMeowCSG_examples import create_csg_examples_patternbook, EXAMPLES
    
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
    
    # Create pattern book and raise the selected pattern
    print("Creating CSG examples pattern book...")
    book = create_csg_examples_patternbook()
    
    print(f"Raising '{CSG_EXAMPLE_TO_RENDER}' pattern...")
    csg = book.raise_pattern(CSG_EXAMPLE_TO_RENDER)
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
        'construction': render_construction,
        'horsey': render_horsey,
        'oscar_shed': render_oscar_shed,
        'japanese_joints': render_japanese_joints,
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

