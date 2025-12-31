"""
Launcher macro for mortise and tenon test - automatically reloads all modules.

This is a thin wrapper that reloads the actual test script, so you can make
changes to test_mortise_and_tenon.py and re-run this macro without restarting FreeCAD.
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

print("="*70)
print("GiraffeCAD FreeCAD - Mortise and Tenon Test Launcher")
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
    'examples.mortise_and_tenon_joint_examples',
    'test_mortise_and_tenon'  # Reload the test script itself
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

print("\nModule reload complete. Running test...\n")

# Import and run the test after reloading
import test_mortise_and_tenon
importlib.reload(test_mortise_and_tenon)
test_mortise_and_tenon.main()

