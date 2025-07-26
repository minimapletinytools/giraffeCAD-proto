"""This file acts as the main module for this script."""

import traceback
import adsk.core
import adsk.fusion
import sys
import os

# Add the local libs directory and parent directory to sys.path
script_dir = os.path.dirname(os.path.realpath(__file__))
libs_dir = os.path.join(script_dir, 'libs')
parent_dir = os.path.dirname(script_dir)

# Add paths in order of priority
if libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import our GiraffeCAD modules from parent directory
try:
    # Import from parent directory - these files are NOT copied locally
    from sawhorse_example import create_sawhorse
    from giraffe_render_fusion360 import render_multiple_timbers, clear_design
    
    # Test that core dependencies are available
    import sympy
    from moothymoth import Orientation
    from giraffe import CutTimber
    
    import_success = True
    import_error = None
except ImportError as e:
    # Handle import error gracefully for when running in Fusion 360
    create_sawhorse = None
    render_multiple_timbers = None
    clear_design = None
    import_success = False
    import_error = str(e)

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui = app.userInterface


def run(_context: str):
    """This function is called by Fusion when the script is run."""

    try:
        # Check if imports were successful
        if not import_success:
            ui.messageBox(f'Failed to import required modules: {import_error}\n\n'
                         f'Make sure the GiraffeCAD modules are in the parent directory and '
                         f'sympy is installed in the libs/ folder.')
            return

        # Clear the current design first
        ui.messageBox('Clearing current design and creating sawhorse...')
        
        if clear_design():
            ui.messageBox('Design cleared successfully')
        else:
            ui.messageBox('Warning: Could not clear design completely')

        # Create the sawhorse timbers
        try:
            cut_timbers = create_sawhorse()
            ui.messageBox(f'Created sawhorse with {len(cut_timbers)} timbers')
        except Exception as e:
            ui.messageBox(f'Error creating sawhorse: {str(e)}')
            app.log(f'Sawhorse creation failed:\n{traceback.format_exc()}')
            return

        # Render the timbers in Fusion 360
        try:
            success_count = render_multiple_timbers(cut_timbers, "Sawhorse_Timber")
            
            if success_count == len(cut_timbers):
                ui.messageBox(f'Successfully rendered all {success_count} timbers!')
            else:
                ui.messageBox(f'Rendered {success_count} out of {len(cut_timbers)} timbers. Check TEXT COMMANDS for details.')
                
            # Log detailed information
            app.log(f'Sawhorse rendering complete: {success_count}/{len(cut_timbers)} timbers rendered')
            
            for i, cut_timber in enumerate(cut_timbers):
                timber = cut_timber.timber
                app.log(f'  Timber {i+1}: length={timber.length:.3f}m, '
                       f'size=({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m), '
                       f'joints={len(cut_timber.joints)}')
                       
        except Exception as e:
            ui.messageBox(f'Error rendering timbers: {str(e)}')
            app.log(f'Rendering failed:\n{traceback.format_exc()}')
            return

        # Final success message
        ui.messageBox(f'Sawhorse complete! Created and rendered {len(cut_timbers)} timbers with joints.')

    except Exception as e:  #pylint:disable=broad-except
        # Write the error message to the TEXT COMMANDS window and show in dialog
        error_msg = f'Script failed:\n{traceback.format_exc()}'
        app.log(error_msg)
        ui.messageBox(f'Error: {str(e)}\n\nSee TEXT COMMANDS for full details.')


def stop(_context: str):
    """This function is called by Fusion when the script is stopped."""
    try:
        # Clean up any resources if needed
        pass
    except:  #pylint:disable=bare-except
        app.log(f'Stop failed:\n{traceback.format_exc()}')
