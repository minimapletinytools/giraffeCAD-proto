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

# Test that core dependencies are available at startup
try:
    # Test basic imports to ensure path setup is working
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
        # Check if imports were successful
        if not import_success:
            ui.messageBox(f'Failed to import required modules: {import_error}\n\n'
                         f'Make sure the GiraffeCAD modules are in the parent directory and '
                         f'sympy is installed in the libs/ folder.')
            return

        # Force reload all GiraffeCAD modules to avoid caching issues
        print("Force reloading GiraffeCAD modules to avoid cache...")
        app.log("Force reloading GiraffeCAD modules to avoid cache...")
        
        try:
            import importlib
            import sys
            
            # List of modules to reload in dependency order
            modules_to_reload = [
                'moothymoth',
                'giraffe', 
                'giraffe_render_fusion360',
                'sawhorse_example'
            ]
            
            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    print(f"  Reloading {module_name}...")
                    importlib.reload(sys.modules[module_name])
                else:
                    print(f"  {module_name} not in cache, will import fresh")
            
            # Re-import the functions we need after reload
            from sawhorse_example import create_sawhorse
            from supersimple_example import create_supersimple_structure
            from giraffe_render_fusion360 import render_CutTimber, get_active_design, clear_design, render_multiple_timbers_two_pass
            
            print("✓ Module reload complete")
            app.log("Module reload complete")
            
        except Exception as reload_error:
            print(f"Warning: Module reload failed: {reload_error}")
            app.log(f"Warning: Module reload failed: {reload_error}")
            # Continue anyway with cached modules

        # Clear the current design first
        print('Clearing current design and creating sawhorse...')
        app.log('Starting sawhorse generation...')
        
        if clear_design():
            print('Design cleared successfully')
        else:
            print('Warning: Could not clear design completely')

        # Create the sawhorse timbers
        try:
            #cut_timbers = create_sawhorse()
            cut_timbers = create_supersimple_structure()
            print(f'Created sawhorse with {len(cut_timbers)} timbers')
            app.log(f'Created sawhorse with {len(cut_timbers)} timbers')
        except Exception as e:
            ui.messageBox(f'Error creating sawhorse: {str(e)}')
            app.log(f'Sawhorse creation failed:\n{traceback.format_exc()}')
            return

        # Render the timbers in Fusion 360 using two-pass rendering approach
        try:
            print(f"Starting two-pass rendering of {len(cut_timbers)} sawhorse timbers...")
            app.log(f"Starting two-pass rendering of {len(cut_timbers)} sawhorse timbers...")
            
            # Use the dedicated two-pass rendering function (imported after reload)
            success_count = render_multiple_timbers_two_pass(cut_timbers, "Sawhorse_Timber")
            
            # Log detailed information
            app.log(f'Sawhorse rendering complete: {success_count}/{len(cut_timbers)} timbers rendered')
            
            for i, cut_timber in enumerate(cut_timbers):
                timber = cut_timber.timber
                app.log(f'  Timber {i+1}: {timber.name} - length={timber.length:.3f}m, '
                       f'size=({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m), '
                       f'joints={len(cut_timber.joints)}')
            
            # Show final result dialog
            if success_count == len(cut_timbers):
                ui.messageBox(f'✅ Sawhorse Complete!\n\nSuccessfully created and rendered all {success_count} timbers with joints.\n\nComponents created:\n' + 
                             '\n'.join(f'• {ct.name or f"Timber {i+1}"}' for i, ct in enumerate(cut_timbers)))
            else:
                ui.messageBox(f'⚠️ Sawhorse Partially Complete\n\nRendered {success_count} out of {len(cut_timbers)} timbers.\n\nCheck TEXT COMMANDS for detailed error information.')
                       
        except Exception as e:
            ui.messageBox(f'Error rendering sawhorse timbers: {str(e)}')
            app.log(f'Sawhorse rendering failed:\n{traceback.format_exc()}')
            return

    except Exception as e:  #pylint:disable=broad-except
        # Write the error message to the TEXT COMMANDS window and show in dialog
        error_msg = f'Script failed:\n{traceback.format_exc()}'
        app.log(error_msg)
        ui.messageBox(f'Error: {str(e)}\n\nSee TEXT COMMANDS for full details.')


def run_debug(_context: str):
    """Debug function - creates a simple 1x2x5 timber, rotated 45 degrees, translated 10 units right."""

    try:
        # Check if imports were successful
        if not import_success:
            ui.messageBox(f'Failed to import required modules: {import_error}\n\n'
                         f'Make sure the GiraffeCAD modules are in the parent directory and '
                         f'sympy is installed in the libs/ folder.')
            return

        # Import additional modules needed for this debug test
        from giraffe import create_timber, create_vector2d, create_vector3d, CutTimber
        from moothymoth import Orientation
        import sympy as sp
        
        # Clear the current design first
        ui.messageBox('Clearing current design and creating debug timber...')
        
        if clear_design():
            ui.messageBox('Design cleared successfully')
        else:
            ui.messageBox('Warning: Could not clear design completely')

        # Create debug timbers: two 1x2x5 rectangular prisms with different rotations
        # Dimensions: 1m wide (face direction), 2m high, 5m long (length direction)
        timber_size = create_vector2d(1.0, 2.0)  # width x height
        timber_length = 5.0
        
        # === FIRST TIMBER: 45 degrees around Z-axis ===
        # Position: 10 units to the right (positive X)
        position1 = create_vector3d(10.0, 0.0, 0.0)
        
        # Create rotation: 45 degrees around Z-axis (yaw)
        # This will rotate the timber 45 degrees in the XY plane
        rotation_angle = sp.pi / 4  # 45 degrees in radians
        rotated_orientation1 = Orientation.from_euleryZYX(rotation_angle, 0, 0)
        
        # Get the rotated directions from the orientation
        length_direction1 = create_vector3d(
            float(rotated_orientation1.matrix[0, 2]),
            float(rotated_orientation1.matrix[1, 2]),
            float(rotated_orientation1.matrix[2, 2])
        )
        face_direction1 = create_vector3d(
            float(rotated_orientation1.matrix[0, 0]),
            float(rotated_orientation1.matrix[1, 0]),
            float(rotated_orientation1.matrix[2, 0])
        )
        
        # Create the first timber
        timber1 = create_timber(
            bottom_position=position1,
            length=timber_length,
            size=timber_size,
            length_direction=length_direction1,
            face_direction=face_direction1
        )
        timber1.name = "Debug Timber 1 (45° around Z-axis)"
        
        # === SECOND TIMBER: 45 degrees around Y-axis ===
        # Position: 10 units forward (positive Y) and 5 units up (positive Z)
        position2 = create_vector3d(0.0, 10.0, 5.0)
        
        # Create rotation: 45 degrees around Y-axis (pitch)
        # This will tilt the timber 45 degrees up/down
        rotated_orientation2 = Orientation.from_euleryZYX(0, rotation_angle, 0)
        
        # Get the rotated directions from the orientation
        length_direction2 = create_vector3d(
            float(rotated_orientation2.matrix[0, 2]),
            float(rotated_orientation2.matrix[1, 2]),
            float(rotated_orientation2.matrix[2, 2])
        )
        face_direction2 = create_vector3d(
            float(rotated_orientation2.matrix[0, 0]),
            float(rotated_orientation2.matrix[1, 0]),
            float(rotated_orientation2.matrix[2, 0])
        )
        
        # Create the second timber
        timber2 = create_timber(
            bottom_position=position2,
            length=timber_length,
            size=timber_size,
            length_direction=length_direction2,
            face_direction=face_direction2
        )
        timber2.name = "Debug Timber 2 (45° around Y-axis)"
        
        # Create CutTimber wrappers
        cut_timber1 = CutTimber(timber1)
        cut_timber2 = CutTimber(timber2)
        cut_timbers = [cut_timber1, cut_timber2]
        
        ui.messageBox(f'Created 2 debug timbers:\n'
                     f'1. 45° rotation around Z-axis (position: 10,0,0)\n'
                     f'2. 45° rotation around Y-axis (position: 0,10,5)\n'
                     f'Both are 1x2x5m in size')

        # Render the timbers in Fusion 360
        try:
            from giraffe_render_fusion360 import render_multiple_timbers, render_multiple_timbers_two_pass
            
            # Try the two-pass approach to fix the transform interference issue
            ui.messageBox('Using two-pass rendering to avoid transform interference...')
            success_count = render_multiple_timbers_two_pass(cut_timbers, "Debug_Timber")
            
            if success_count == len(cut_timbers):
                ui.messageBox(f'Successfully rendered all {success_count} debug timbers!')
            else:
                ui.messageBox(f'Rendered {success_count} out of {len(cut_timbers)} debug timbers. Check TEXT COMMANDS for details.')
                
            # Log detailed information
            app.log(f'Debug timber rendering: {success_count}/{len(cut_timbers)} timbers rendered')
            
            for i, cut_timber in enumerate(cut_timbers):
                timber = cut_timber.timber
                app.log(f'  Timber {i+1}: {timber.name}')
                app.log(f'    Size: {float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m x {timber.length:.3f}m')
                app.log(f'    Position: ({float(timber.bottom_position[0]):.3f}, {float(timber.bottom_position[1]):.3f}, {float(timber.bottom_position[2]):.3f})')
                app.log(f'    Length direction: ({float(timber.length_direction[0]):.3f}, {float(timber.length_direction[1]):.3f}, {float(timber.length_direction[2]):.3f})')
                app.log(f'    Face direction: ({float(timber.face_direction[0]):.3f}, {float(timber.face_direction[1]):.3f}, {float(timber.face_direction[2]):.3f})')
                       
        except Exception as e:
            ui.messageBox(f'Error rendering debug timbers: {str(e)}')
            app.log(f'Debug rendering failed:\n{traceback.format_exc()}')
            return

        # Final success message
        ui.messageBox(f'Debug complete! Created 2 timbers with different 45° rotations:\n'
                     f'• Timber 1: Rotated around Z-axis (horizontal spin)\n'
                     f'• Timber 2: Rotated around Y-axis (vertical tilt)')

    except Exception as e:  #pylint:disable=broad-except
        # Write the error message to the TEXT COMMANDS window and show in dialog
        error_msg = f'Debug script failed:\n{traceback.format_exc()}'
        app.log(error_msg)
        ui.messageBox(f'Error: {str(e)}\n\nSee TEXT COMMANDS for full details.')


def stop(_context: str):
    """This function is called by Fusion when the script is stopped."""
    try:
        # Clean up any resources if needed
        pass
    except:  #pylint:disable=bare-except
        app.log(f'Stop failed:\n{traceback.format_exc()}')
