#!/usr/bin/env python3
"""
Test script to verify that all GiraffeCAD dependencies work locally.
This simulates what Fusion 360 will do when importing our modules.
"""

import sys
import os

# Add the local libs directory to sys.path (same as in giraffetest.py)
script_dir = os.path.dirname(os.path.realpath(__file__))
libs_dir = os.path.join(script_dir, 'libs')

if libs_dir not in sys.path:
    sys.path.insert(0, libs_dir)

def test_dependencies():
    """Test that all dependencies can be imported."""
    print("Testing dependency imports...")
    
    try:
        import sympy
        print(f"✓ sympy {sympy.__version__} imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import sympy: {e}")
        return False
    
    try:
        import numpy
        print(f"✓ numpy {numpy.__version__} imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import numpy: {e}")
        return False
    
    try:
        import mpmath
        print(f"✓ mpmath {mpmath.__version__} imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import mpmath: {e}")
        return False
    
    return True

def test_giraffe_modules():
    """Test that GiraffeCAD modules can be imported."""
    print("\nTesting GiraffeCAD module imports...")
    
    try:
        from moothymoth import Orientation
        print("✓ moothymoth.Orientation imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import moothymoth: {e}")
        return False
    
    try:
        from giraffe import CutTimber, Timber, create_vector3d
        print("✓ giraffe core classes imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import giraffe: {e}")
        return False
    
    try:
        from sawhorse_example import create_sawhorse
        print("✓ sawhorse_example imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import sawhorse_example: {e}")
        return False
    
    # Note: We can't test giraffe_render_fusion360 outside of Fusion 360
    # because it depends on adsk modules
    print("✓ Core GiraffeCAD modules ready (giraffe_render_fusion360 requires Fusion 360)")
    
    return True

def test_sawhorse_creation():
    """Test that we can create a sawhorse."""
    print("\nTesting sawhorse creation...")
    
    try:
        from sawhorse_example import create_sawhorse
        cut_timbers = create_sawhorse()
        
        print(f"✓ Created sawhorse with {len(cut_timbers)} timbers:")
        for i, cut_timber in enumerate(cut_timbers):
            timber = cut_timber.timber
            print(f"    {i+1}. Length={timber.length:.3f}m, "
                  f"Size=({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m), "
                  f"Joints={len(cut_timber.joints)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create sawhorse: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Run all tests."""
    print("GiraffeCAD Local Dependency Test")
    print("=" * 40)
    
    all_passed = True
    
    if not test_dependencies():
        all_passed = False
    
    if not test_giraffe_modules():
        all_passed = False
    
    if not test_sawhorse_creation():
        all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! Ready for Fusion 360.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    main() 