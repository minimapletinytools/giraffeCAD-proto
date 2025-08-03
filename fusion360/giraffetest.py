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
    from supersimple_example import create_supersimple_structure
    from supersimple_example2 import create_supersimple_structure2
    from giraffe_render_fusion360 import get_active_design, clear_design, render_multiple_timbers
    
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

# Global variables for command handlers
handlers = []


class GiraffeTestCommandHandler(adsk.core.CommandEventHandler):
    """Command handler for GiraffeTest shortcut."""
    
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        """Called when the command is executed."""
        try:
            # Run the main script functionality
            run('shortcut')
        except Exception as e:
            ui.messageBox(f'Error running GiraffeTest: {str(e)}')


def create_giraffe_command():
    """Create the GiraffeTest command with keyboard shortcut."""
    command_created = False
    shortcut_created = False
    
    try:
        # Get the CommandDefinitions collection
        cmdDefs = ui.commandDefinitions
        
        # Check if command already exists and remove it
        existingCmd = cmdDefs.itemById('giraffeTestCmd')
        if existingCmd:
            print("Removing existing GiraffeCAD command...")
            existingCmd.deleteMe()
        
        # Create the command definition
        cmdDef = cmdDefs.addButtonDefinition(
            'giraffeTestCmd',
            'GiraffeCAD Test',
            'Run GiraffeCAD sawhorse generation',
            ''  # No icon resource for now
        )
        
        # Connect the command handler
        cmdHandler = GiraffeTestCommandHandler()
        cmdDef.commandCreated.add(cmdHandler)
        handlers.append(cmdHandler)
        
        command_created = True
        print("GiraffeCAD command created successfully")
        app.log("GiraffeCAD command created successfully")
        
        # Try to add keyboard shortcut
        try:
            shortcuts = ui.keyboardShortcuts
            
            # Check if shortcut already exists and remove it
            existing_shortcut = shortcuts.itemById('giraffeTestCmd')
            if existing_shortcut:
                print("Removing existing shortcut...")
                existing_shortcut.deleteMe()
            
            # Try different shortcut combinations if the first one fails
            shortcut_attempts = [
                ('Ctrl+Shift+G', 'Ctrl+Shift+G'),
                ('Ctrl+Alt+G', 'Ctrl+Alt+G'),
                ('Ctrl+Shift+M', 'Ctrl+Shift+M'),  # M for "My script" as in your example
                ('F9', 'F9')
            ]
            
            for shortcut_key, display_name in shortcut_attempts:
                try:
                    shortcut = shortcuts.add('giraffeTestCmd', shortcut_key)
                    shortcut_created = True
                    print(f"GiraffeCAD shortcut created: {display_name}")
                    app.log(f"GiraffeCAD shortcut created: {display_name}")
                    break
                except Exception as shortcut_error:
                    print(f"Failed to create shortcut {shortcut_key}: {str(shortcut_error)}")
                    continue
            
            if not shortcut_created:
                print("Could not create any keyboard shortcut - all attempts failed")
                app.log("Could not create any keyboard shortcut - all attempts failed")
                
        except Exception as shortcut_error:
            print(f"Shortcut creation failed: {str(shortcut_error)}")
            app.log(f"Shortcut creation failed: {str(shortcut_error)}")
            import traceback
            print(f"Shortcut error traceback: {traceback.format_exc()}")
        
        return command_created
        
    except Exception as e:
        print(f"Failed to create GiraffeCAD command: {str(e)}")
        app.log(f"Failed to create GiraffeCAD command: {str(e)}")
        import traceback
        print(f"Command creation error traceback: {traceback.format_exc()}")
        return False


def run(_context: str):
    """This function is called by Fusion when the script is run."""

    try:
        # If this is the initial script run (not from shortcut), create the command
        if _context != 'shortcut':
            if create_giraffe_command():
                # Check what was actually created by looking at the logs
                ui.messageBox('🎯 GiraffeCAD Command Created!\n\n'
                            'Check the TEXT COMMANDS panel for shortcut details.\n'
                            'If a shortcut was created, you can use it to quickly regenerate.\n\n'
                            'Running initial sawhorse generation now...',
                            'GiraffeCAD Ready')
            else:
                #ui.messageBox('Warning: Could not create command.\n'
                #            'Check the TEXT COMMANDS panel for error details.\n'
                #            'Running sawhorse generation anyway...',
                #            'Command Creation Failed')
        
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
                'sawhorse_example',
                'supersimple_example',
                'supersimple_example2',
                'supersimple_example3',
                'supersimple_example4'
            ]
            
            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    print(f"  Reloading {module_name}...")
                    importlib.reload(sys.modules[module_name])
                else:
                    print(f"  {module_name} not in cache, will import fresh")
            
            # Re-import the functions we need after reload to get fresh versions
            from sawhorse_example import create_sawhorse
            from supersimple_example import create_supersimple_structure
            from supersimple_example2 import create_supersimple_structure2
            from supersimple_example3 import create_supersimple_structure3
            from supersimple_example4 import create_supersimple_structure4
            from giraffe_render_fusion360 import get_active_design, clear_design, render_multiple_timbers
            
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
            cut_timbers = create_sawhorse()
            #cut_timbers = create_supersimple_structure2()
            print(f'Created structure with {len(cut_timbers)} timbers')
            app.log(f'Created structure with {len(cut_timbers)} timbers')
        except Exception as e:
            ui.messageBox(f'Error creating structure: {str(e)}')
            app.log(f'Structure creation failed:\n{traceback.format_exc()}')
            return

        # Render the timbers in Fusion 360 using two-pass rendering approach
        try:
            print(f"Starting two-pass rendering of {len(cut_timbers)} sawhorse timbers...")
            app.log(f"Starting two-pass rendering of {len(cut_timbers)} sawhorse timbers...")
            
            # Use the two-pass rendering function (imported after reload)
            success_count = render_multiple_timbers(cut_timbers, "Sawhorse_Timber")
            
            # Log detailed information
            app.log(f'Sawhorse rendering complete: {success_count}/{len(cut_timbers)} timbers rendered')
            
            # Show final summary
            ui.messageBox(f'🎯 GiraffeCAD Fusion 360 Integration\n\n'
                        f'✅ Successfully rendered {success_count} out of {len(cut_timbers)} sawhorse timbers\n\n'
                        f'Structure: Sawhorse with posts, beam, and stretcher\n'
                        f'Rendering: Two-pass approach for reliable transforms\n'
                        f'Check the timeline for created components.',
                        'Sawhorse Rendering Complete')
            
        except Exception as render_error:
            error_msg = f'❌ Error during sawhorse rendering: {render_error}'
            print(error_msg)
            app.log(error_msg)
            ui.messageBox(f'Error during sawhorse rendering:\n\n{render_error}', 
                        'Rendering Error')

    except Exception as e:
        error_msg = f'❌ Unexpected error in run function: {str(e)}'
        print(error_msg)
        app.log(error_msg)
        ui.messageBox(f'Unexpected error:\n\n{str(e)}\n\nCheck the TEXT COMMANDS panel for detailed logs.', 
                      'Unexpected Error')


def run_debug(_context: str):
    """Debug function to test two-pass rendering with simple timbers."""
    
    # Clear design first
    if clear_design():
        print('Design cleared successfully')
    
    # Create simple debug timbers
    try:
        print("Creating debug timbers...")
        
        # Import render function for debug use
        from giraffe_render_fusion360 import render_multiple_timbers
        from giraffe import create_timber, CutTimber, create_vector2d, create_vector3d
        
        # Create two simple test timbers
        timber1 = create_timber(
            bottom_position=create_vector3d(0, 0, 0),
            length=1.0,
            size=create_vector2d(0.1, 0.2),
            length_direction=create_vector3d(1, 0, 0),  # X direction
            face_direction=create_vector3d(0, 0, 1)      # Up
        )
        timber1.name = "Test Timber 1"
        
        timber2 = create_timber(
            bottom_position=create_vector3d(0, 1, 0),
            length=1.0, 
            size=create_vector2d(0.1, 0.2),
            length_direction=create_vector3d(0, 1, 0),  # Y direction  
            face_direction=create_vector3d(0, 0, 1)      # Up
        )
        timber2.name = "Test Timber 2"
        
        cut_timbers = [CutTimber(timber1), CutTimber(timber2)]
        
        # Render using two-pass approach
        success_count = render_multiple_timbers(cut_timbers, "Debug_Timber")
        
        print(f"Debug rendering complete: {success_count}/{len(cut_timbers)} timbers rendered")
        
    except Exception as debug_error:
        print(f"Error in debug rendering: {debug_error}")
        import traceback
        print(traceback.format_exc())


def stop(_context: str):
    """This function is called by Fusion when the script is stopped."""
    try:
        # Clean up command and shortcut
        cmdDefs = ui.commandDefinitions
        existingCmd = cmdDefs.itemById('giraffeTestCmd')
        if existingCmd:
            existingCmd.deleteMe()
        
        # Clean up keyboard shortcut
        try:
            shortcuts = ui.keyboardShortcuts
            shortcut = shortcuts.itemById('giraffeTestCmd')
            if shortcut:
                shortcut.deleteMe()
        except:
            # Shortcut cleanup may fail, but it's not critical
            pass
        
        # Clear handlers
        global handlers
        handlers.clear()
        
        print("GiraffeCAD command and shortcut cleaned up")
        app.log("GiraffeCAD command and shortcut cleaned up")
        
    except:  #pylint:disable=bare-except
        app.log(f'Stop failed:\n{traceback.format_exc()}')
