"""
GiraffeCAD Fusion 360 Examples Runner - automatically reloads all modules.

This script provides multiple example rendering functions with automatic module reloading,
so you can make changes to your code and re-run this script without restarting Fusion 360.

TO CHANGE WHICH EXAMPLE RENDERS:
Edit the EXAMPLE_TO_RENDER variable below (around line 44).
"""

import traceback
import adsk.core
import adsk.fusion
import sys
import os

# Add the local libs directory, current script directory, and parent directory to sys.path
script_dir = os.path.dirname(os.path.realpath(__file__))
libs_dir = os.path.join(script_dir, 'libs')
parent_dir = os.path.dirname(script_dir)

# Add paths in order of priority
if libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# ============================================================================
# CONFIGURATION: Change this to render different examples
# ============================================================================
#EXAMPLE_TO_RENDER = 'basic_joints' 
#EXAMPLE_TO_RENDER = 'mortise_and_tenon'
#EXAMPLE_TO_RENDER = 'gooseneck'
EXAMPLE_TO_RENDER = 'oscar_shed'
#EXAMPLE_TO_RENDER = 'irrational_angles'

# Import our GiraffeCAD modules from parent directory
try:
    # Import from parent directory - these files are NOT copied locally
    # Note: We only import basic functions here, the rest are imported after reload
    from examples.oscarshed import create_oscarshed
    from examples.reference.basic_joints_example import create_all_joint_examples
    # Import just one function from mortise_and_tenon_joint_examples to test module accessibility
    from examples.mortise_and_tenon_joint_examples import example_basic_mortise_and_tenon
    from examples.japanese_joints_example import create_simple_gooseneck_example
    from examples.irrational_angles_example import create_all_irrational_examples
    from giraffe_render_fusion360 import get_active_design, clear_design, render_frame
    
    # Test that core dependencies are available
    import sympy
    from code_goes_here.moothymoth import Orientation
    from giraffe import CutTimber
    
    import_success = True
    import_error = None
except ImportError as e:
    # Handle import error gracefully for when running in Fusion 360
    import_success = False
    import_error = str(e)

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui = app.userInterface


def reload_all_modules():
    """Reload all GiraffeCAD modules in dependency order."""
    print("="*70)
    print("GiraffeCAD Fusion 360 - Examples Runner")
    print("="*70)
    print("\nReloading all GiraffeCAD modules...")
    app.log("Reloading all GiraffeCAD modules...")
    
    import importlib
    
    # List of modules to reload in dependency order
    modules_to_reload = [
        'code_goes_here.moothymoth',
        'code_goes_here.footprint',
        'code_goes_here.meowmeowcsg',
        'code_goes_here.timber',
        'code_goes_here.construction',
        'code_goes_here.rendering_utils',
        'code_goes_here.joint_shavings',
        'code_goes_here.basic_joints',
        'code_goes_here.mortise_and_tenon_joint',
        'code_goes_here.japanese_joints',
        'giraffe',
        'giraffe_render_freecad',
        'giraffe_render_fusion360',  # Add this so the rendering module itself gets reloaded
        'examples.reference.basic_joints_example',
        'examples.mortise_and_tenon_joint_examples',
        'examples.horsey_example',
        'examples.oscarshed',
        'examples.japanese_joints_example',
        'examples.irrational_angles_example',
        'examples.MeowMeowCSG_examples',
    ]
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            try:
                importlib.reload(sys.modules[module_name])
            except Exception as e:
                print(f"  ⚠ Error reloading {module_name}: {e}")
                app.log(f"  ⚠ Error reloading {module_name}: {e}")
        else:
            print(f"  - {module_name} not loaded yet")
    
    print("\nModule reload complete.\n")
    app.log("Module reload complete.")


def render_basic_joints():
    """Render all basic joint examples."""
    from giraffe_render_fusion360 import render_frame, clear_design
    from examples.reference.basic_joints_example import create_all_joint_examples
    
    print("="*60)
    print("GiraffeCAD Fusion 360 - All Basic Joints")
    print("="*60)
    app.log("🦒 GIRAFFETEST: BASIC JOINTS 🦒")
    
    # Create all joint examples
    print("\nCreating all joint examples...")
    frame = create_all_joint_examples()
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    
    # Clear and render
    print("\nClearing Fusion 360 design...")
    if not clear_design():
        print("Failed to prepare design - aborting rendering")
        return
    
    print("\nRendering timbers in Fusion 360...")
    success_count = render_frame(frame, "Joint")
    
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print("="*60)
    
    ui.messageBox(
        f'Basic Joints rendering complete!\n\n' +
        f'Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers',
        'Rendering Complete',
        adsk.core.MessageBoxButtonTypes.OKButtonType,
        adsk.core.MessageBoxIconTypes.InformationIconType
    )


def render_mortise_and_tenon():
    """Render mortise and tenon joint examples with pegs."""
    from giraffe_render_fusion360 import render_frame, clear_design
    from examples.mortise_and_tenon_joint_examples import create_all_mortise_and_tenon_examples
    
    print("="*70)
    print("GiraffeCAD Fusion 360 - Mortise and Tenon Joint Examples")
    print("="*70)
    app.log("🦒 GIRAFFETEST: MORTISE AND TENON 🦒")
    
    # Create mortise and tenon examples
    print("\nCreating all mortise and tenon joint examples...")
    frame = create_all_mortise_and_tenon_examples()
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    print(f"Total accessories (pegs/wedges): {len(frame.accessories)}")
    
    # Clear and render
    print("\nClearing Fusion 360 design...")
    if not clear_design():
        print("Failed to prepare design - aborting rendering")
        return
    
    print("\nRendering timbers and accessories in Fusion 360...")
    success_count = render_frame(frame, "MortiseTenon")
    
    total_objects = len(frame.cut_timbers) + len(frame.accessories)
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{total_objects} objects")
    print("="*70)
    
    ui.messageBox(
        f'Mortise and Tenon rendering complete!\n\n' +
        f'Successfully rendered {success_count}/{total_objects} objects\n' +
        f'({len(frame.cut_timbers)} timbers + {len(frame.accessories)} accessories)',
        'Rendering Complete',
        adsk.core.MessageBoxButtonTypes.OKButtonType,
        adsk.core.MessageBoxIconTypes.InformationIconType
    )


def render_gooseneck():
    """Render Japanese gooseneck joint example."""
    from giraffe_render_fusion360 import render_frame, clear_design
    from examples.japanese_joints_example import create_simple_gooseneck_example
    
    print("="*70)
    print("GiraffeCAD Fusion 360 - Japanese Gooseneck Joint")
    print("="*70)
    app.log("🦒 GIRAFFETEST: JAPANESE GOOSENECK 🦒")
    
    # Create Japanese joint example
    print("\nCreating Japanese lapped gooseneck joint example...")
    frame = create_simple_gooseneck_example()
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    
    # Clear and render
    print("\nClearing Fusion 360 design...")
    if not clear_design():
        print("Failed to prepare design - aborting rendering")
        return
    
    print("\nRendering timbers in Fusion 360...")
    success_count = render_frame(frame, "Gooseneck")
    
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print("="*70)
    
    ui.messageBox(
        f'Japanese Gooseneck Joint rendering complete!\n\n' +
        f'Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers\n\n' +
        f'Traditional Lapped Gooseneck Joint (腰掛鎌継ぎ)',
        'Rendering Complete',
        adsk.core.MessageBoxButtonTypes.OKButtonType,
        adsk.core.MessageBoxIconTypes.InformationIconType
    )


def render_oscar_shed():
    """Render Oscar's Shed - a complete timber frame structure."""
    from giraffe_render_fusion360 import render_frame, clear_design
    from examples.oscarshed import create_oscarshed
    
    print("="*60)
    print("GiraffeCAD Fusion 360 - Oscar's Shed")
    print("="*60)
    app.log("🦒 GIRAFFETEST: OSCAR'S SHED 🦒")
    
    # Create Oscar's Shed
    print("\nCreating Oscar's Shed structure...")
    frame = create_oscarshed()
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    print(f"Total accessories (pegs): {len(frame.accessories)}")
    
    # Clear and render
    print("\nClearing Fusion 360 design...")
    if not clear_design():
        print("Failed to prepare design - aborting rendering")
        return
    
    print("\nRendering timbers and accessories in Fusion 360...")
    success_count = render_frame(frame, "OscarShed_Timber")
    
    total_objects = len(frame.cut_timbers) + len(frame.accessories)
    print("\n" + "="*60)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{total_objects} objects")
    print("="*60)
    
    ui.messageBox(
        f'Oscar\'s Shed rendering complete!\n\n' +
        f'Successfully rendered {success_count}/{total_objects} objects\n' +
        f'({len(frame.cut_timbers)} timbers + {len(frame.accessories)} accessories)\n\n' +
        f'8ft x 4ft timber frame structure',
        'Rendering Complete',
        adsk.core.MessageBoxButtonTypes.OKButtonType,
        adsk.core.MessageBoxIconTypes.InformationIconType
    )


def render_irrational_angles():
    """Render irrational angles test examples."""
    from giraffe_render_fusion360 import render_frame, clear_design
    from examples.irrational_angles_example import create_all_irrational_examples
    
    print("="*70)
    print("GiraffeCAD Fusion 360 - Irrational Angles Test")
    print("="*70)
    app.log("🦒 GIRAFFETEST: IRRATIONAL ANGLES 🦒")
    
    # Create irrational angles examples
    print("\nCreating irrational angles test examples...")
    frame = create_all_irrational_examples()
    
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    
    # Clear and render
    print("\nClearing Fusion 360 design...")
    if not clear_design():
        print("Failed to prepare design - aborting rendering")
        return
    
    print("\nRendering timbers in Fusion 360...")
    success_count = render_frame(frame, "Irrational")
    
    print("\n" + "="*70)
    print(f"Rendering Complete!")
    print(f"Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers")
    print("="*70)
    
    ui.messageBox(
        f'Irrational Angles Test rendering complete!\n\n' +
        f'Successfully rendered {success_count}/{len(frame.cut_timbers)} timbers\n\n' +
        f'Tests CSG alignment at irrational angles:\n' +
        f'• 37° (arbitrary)\n' +
        f'• 45° (√2)\n' +
        f'• 60° (√3)\n' +
        f'• Golden angle (arctan(φ))',
        'Rendering Complete',
        adsk.core.MessageBoxButtonTypes.OKButtonType,
        adsk.core.MessageBoxIconTypes.InformationIconType
    )


def run(_context: str):
    """This function is called by Fusion when the script is run."""
    try:
        # Check for import errors first
        if not import_success:
            ui.messageBox(f'Import Error: {import_error}', 'GiraffeCAD Import Failed')
            return

        # Reload all modules
        reload_all_modules()
        
        # Dispatch to the selected example
        examples = {
            'basic_joints': render_basic_joints,
            'mortise_and_tenon': render_mortise_and_tenon,
            'gooseneck': render_gooseneck,
            'oscar_shed': render_oscar_shed,
            'irrational_angles': render_irrational_angles,
        }
        
        if EXAMPLE_TO_RENDER not in examples:
            error_msg = (
                f"ERROR: Unknown example '{EXAMPLE_TO_RENDER}'\n\n" +
                f"Available examples:\n" +
                "\n".join(f"  • {name}" for name in examples.keys()) +
                "\n\nEdit EXAMPLE_TO_RENDER in giraffetest.py to change the example."
            )
            print(error_msg)
            app.log(error_msg)
            ui.messageBox(error_msg, 'Configuration Error')
            return
        
        print(f"\nRunning example: {EXAMPLE_TO_RENDER}\n")
        app.log(f"Running example: {EXAMPLE_TO_RENDER}")
        examples[EXAMPLE_TO_RENDER]()
        
        print("\n" + "="*70)
        print("To render a different example, edit EXAMPLE_TO_RENDER in giraffetest.py")
        print(f"Available: {', '.join(examples.keys())}")
        print("="*70)

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        app.log(f"ERROR: {error_msg}")
        ui.messageBox(f'Unexpected error:\n{str(e)}', 'GiraffeCAD Error')


def stop(_context: str):
    """This function is called by Fusion when the script is stopped."""
    try:
        print("GiraffeCAD script stopped")
        app.log("GiraffeCAD script stopped")
        
    except:  #pylint:disable=bare-except
        app.log(f'Stop failed:\n{traceback.format_exc()}')
