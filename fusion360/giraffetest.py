"""This file acts as the main module for this script."""

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

# Import our GiraffeCAD modules from parent directory
try:
    # Import from parent directory - these files are NOT copied locally
    from examples.sawhorse_example import create_sawhorse
    from examples.oscarshed import create_oscarshed
    from giraffe_render_fusion360_OLD import get_active_design, clear_design, render_multiple_timbers
    
    # Test that core dependencies are available
    import sympy
    from moothymoth import Orientation
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


def run(_context: str):
    """This function is called by Fusion when the script is run."""



    try:
        # Check for import errors first
        if not import_success:
            ui.messageBox(f'Import Error: {import_error}', 'GiraffeCAD Import Failed')
            return

        # Force reload all GiraffeCAD modules to avoid caching issues
        print("Force reloading GiraffeCAD modules to avoid cache...")
        app.log("Force reloading GiraffeCAD modules to avoid cache...")
        app.log("ORIG MODULE LOADED 5:39")
        
        try:
            import importlib
            import sys
            
            # List of modules to reload in dependency order
            modules_to_reload = [
                'moothymoth',
                'footprint',
                'giraffe', 
                'giraffe_render_fusion360_OLD',
                'examples.sawhorse_example',
                'examples.oscarshed'
            ]
            
            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    print(f"  Reloading {module_name}...")
                    importlib.reload(sys.modules[module_name])
                else:
                    print(f"  {module_name} not in cache, will import fresh")
            
            # Re-import the functions we need after reload to get fresh versions
            from examples.sawhorse_example import create_sawhorse
            from examples.oscarshed import create_oscarshed
            from giraffe_render_fusion360_OLD import get_active_design, clear_design, render_multiple_timbers
            
            print("✓ Module reload complete")
            app.log("Module reload complete")
            
        except Exception as reload_error:
            print(f"Error reloading modules: {reload_error}")
            app.log(f"Error reloading modules: {reload_error}")

        # Run Oscar's Shed structure generation
        try:
            print("🦓 GIRAFFETEST: OSCAR'S SHED - 8x3.5 ft Timber Frame Structure 🦓")
            app.log("🦓 GIRAFFETEST: OSCAR'S SHED - 8x3.5 ft Timber Frame Structure 🦓")
            print("Starting Oscar's Shed generation...")
            cut_timbers = create_oscarshed()
            print(f"Created structure with {len(cut_timbers)} timbers")
            
            # Clear design first to start fresh
            clear_design()
            
            # Render the timbers in Fusion 360 using three-pass rendering approach  
            print(f"Starting three-pass rendering of {len(cut_timbers)} Oscar's Shed timbers...")
            app.log(f"Starting three-pass rendering of {len(cut_timbers)} Oscar's Shed timbers...")
            
            # Use the three-pass rendering function with transforms enabled to test full workflow
            success_count = render_multiple_timbers(cut_timbers, "OscarShed_Timber", apply_transforms=True)
            
            # Log detailed information
            app.log(f"Oscar's Shed rendering complete: {success_count}/{len(cut_timbers)} timbers rendered")
            
            # Show final summary  
            print(f"Oscar's Shed rendering complete: {success_count}/{len(cut_timbers)} timbers rendered")
            
        except Exception as rendering_error:
            print(f"❌ Error during Oscar's Shed rendering: {rendering_error}")
            app.log(f"Error during Oscar's Shed rendering: {rendering_error}")
            import traceback
            print(traceback.format_exc())
            ui.messageBox(f"Error during Oscar's Shed rendering:\n{rendering_error}", 'Rendering Error')

    except Exception as e:
        print(f"Unexpected error in run(): {str(e)}")
        app.log(f"Unexpected error in run(): {str(e)}")
        ui.messageBox(f'Unexpected error:\n{str(e)}', 'GiraffeCAD Error')


def stop(_context: str):
    """This function is called by Fusion when the script is stopped."""
    try:
        print("GiraffeCAD script stopped")
        app.log("GiraffeCAD script stopped")
        
    except:  #pylint:disable=bare-except
        app.log(f'Stop failed:\n{traceback.format_exc()}')
