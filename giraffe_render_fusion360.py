"""
Fusion 360 rendering module for GiraffeCAD timber framing system.

This module provides functions to render timber structures in Autodesk Fusion 360
using the Fusion 360 Python API.
"""

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
from typing import Optional
from sympy import Matrix, Float
from giraffe import CutTimber, Timber
from moothymoth import Orientation


def get_fusion_app() -> Optional[adsk.core.Application]:
    """Get the Fusion 360 application instance."""
    try:
        app = adsk.core.Application.get()
        return app
    except:
        return None


def get_active_design() -> Optional[adsk.fusion.Design]:
    """Get the active design in Fusion 360."""
    app = get_fusion_app()
    if not app:
        return None
    
    try:
        design = app.activeProduct
        if isinstance(design, adsk.fusion.Design):
            return design
        else:
            return None
    except:
        return None


def create_matrix3d_from_orientation(position: Matrix, orientation: Orientation) -> adsk.core.Matrix3D:
    """
    Convert sympy position vector and Orientation to Fusion 360 Matrix3D.
    
    Args:
        position: 3x1 sympy Matrix representing position
        orientation: Orientation object with 3x3 rotation matrix
        
    Returns:
        adsk.core.Matrix3D for use in Fusion 360
    """
    app = get_fusion_app()
    if not app:
        raise RuntimeError("Cannot access Fusion 360 application")
    
    # Create Fusion 360 Matrix3D
    matrix3d = adsk.core.Matrix3D.create()
    
    # Extract rotation matrix values (convert sympy expressions to floats)
    # The orientation matrix columns are [face_direction, height_direction, length_direction]
    # For Fusion 360, we want to create a coordinate system where:
    # - X-axis (col 0) = face_direction (width of timber)
    # - Y-axis (col 1) = height_direction (height of timber)  
    # - Z-axis (col 2) = length_direction (length of timber for extrusion)
    r00 = float(orientation.matrix[0, 0])  # face_direction.x
    r01 = float(orientation.matrix[0, 1])  # height_direction.x
    r02 = float(orientation.matrix[0, 2])  # length_direction.x
    r10 = float(orientation.matrix[1, 0])  # face_direction.y
    r11 = float(orientation.matrix[1, 1])  # height_direction.y
    r12 = float(orientation.matrix[1, 2])  # length_direction.y
    r20 = float(orientation.matrix[2, 0])  # face_direction.z
    r21 = float(orientation.matrix[2, 1])  # height_direction.z
    r22 = float(orientation.matrix[2, 2])  # length_direction.z
    
    # Extract translation values
    tx = float(position[0])
    ty = float(position[1])
    tz = float(position[2])
    
    # Debug output
    print(f"Creating transformation matrix:")
    print(f"  Position: ({tx:.3f}, {ty:.3f}, {tz:.3f})")
    print(f"  Face dir:   ({r00:.3f}, {r10:.3f}, {r20:.3f})")
    print(f"  Height dir: ({r01:.3f}, {r11:.3f}, {r21:.3f})")
    print(f"  Length dir: ({r02:.3f}, {r12:.3f}, {r22:.3f})")
    
    # Set the matrix values (4x4 transformation matrix in row-major order)
    matrix3d.setWithArray([
        r00, r01, r02, tx,   # First row:  [face.x, height.x, length.x, pos.x]
        r10, r11, r12, ty,   # Second row: [face.y, height.y, length.y, pos.y]
        r20, r21, r22, tz,   # Third row:  [face.z, height.z, length.z, pos.z]
        0.0, 0.0, 0.0, 1.0   # Fourth row: [0, 0, 0, 1]
    ])
    
    return matrix3d


def render_multiple_timbers(cut_timbers: list[CutTimber], base_name: str = "Timber") -> int:
    """
    Render multiple CutTimber objects in Fusion 360 using a two-pass approach.
    
    Pass 1: Create all geometry at the origin
    Pass 2: Apply all transforms
    
    This approach is more reliable with Fusion 360's occurrence system.
    
    Args:
        cut_timbers: List of CutTimber objects to render
        base_name: Base name for components (will be numbered)
        
    Returns:
        int: Number of timbers successfully rendered
    """
    try:
        print(f"Starting two-pass rendering of {len(cut_timbers)} timbers...")
        
        # Get the active design
        design = get_active_design()
        if not design:
            print("Error: No active design found in Fusion 360")
            return 0
        
        root_comp = design.rootComponent
        created_components = []
        
        # PASS 1: Create all geometry without transforms
        print(f"\n=== PASS 1: Creating geometry ===")
        
        for i, cut_timber in enumerate(cut_timbers):
            component_name = cut_timber.name if cut_timber.name else f"{base_name}_{i+1:03d}"
            print(f"Creating geometry for: {component_name}")
            
            timber = cut_timber.timber
            length = timber.length
            width = float(timber.size[0])
            height = float(timber.size[1])
            
            # Convert to cm
            length_cm = length * 100
            width_cm = width * 100
            height_cm = height * 100
            
            # Create component at origin
            occurrence = root_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            timber_component = occurrence.component
            timber_component.name = component_name
            
            # Create sketch and extrusion (same as before)
            sketches = timber_component.sketches
            xy_plane = timber_component.xYConstructionPlane
            sketch = sketches.add(xy_plane)
            
            rect_lines = sketch.sketchCurves.sketchLines
            x1, y1 = -width_cm / 2, -height_cm / 2
            x2, y2 = width_cm / 2, height_cm / 2
            
            point1 = adsk.core.Point3D.create(x1, y1, 0)
            point2 = adsk.core.Point3D.create(x2, y1, 0)
            point3 = adsk.core.Point3D.create(x2, y2, 0)
            point4 = adsk.core.Point3D.create(x1, y2, 0)
            
            rect_lines.addByTwoPoints(point1, point2)
            rect_lines.addByTwoPoints(point2, point3)
            rect_lines.addByTwoPoints(point3, point4)
            rect_lines.addByTwoPoints(point4, point1)
            
            profile = sketch.profiles.item(0) if sketch.profiles.count > 0 else None
            if not profile:
                print(f"Failed to create profile for {component_name}")
                continue
            
            extrudes = timber_component.features.extrudeFeatures
            extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            distance = adsk.core.ValueInput.createByReal(length_cm)
            extrude_input.setDistanceExtent(False, distance)
            extrude = extrudes.add(extrude_input)
            
            if extrude:
                # Store reference for transform pass
                transform = create_matrix3d_from_orientation(timber.bottom_position, timber.orientation)
                transform_cm = adsk.core.Matrix3D.create()
                
                # Scale translation to cm
                for row in range(3):
                    for col in range(3):
                        transform_cm.setCell(row, col, transform.getCell(row, col))
                transform_cm.setCell(0, 3, transform.getCell(0, 3) * 100)
                transform_cm.setCell(1, 3, transform.getCell(1, 3) * 100)
                transform_cm.setCell(2, 3, transform.getCell(2, 3) * 100)
                transform_cm.setCell(3, 3, 1.0)
                
                created_components.append((occurrence, transform_cm, component_name))
                print(f"✓ Created geometry for {component_name}")
            else:
                print(f"✗ Failed to create extrusion for {component_name}")
        
        # Force refresh after all geometry creation
        adsk.doEvents()
        
        # PASS 2: Apply all transforms
        print(f"\n=== PASS 2: Applying transforms ===")
        
        for occurrence, transform_cm, component_name in created_components:
            print(f"Applying transform to: {component_name}")
            
            occurrence.transform = transform_cm
            
            # Verify
            applied_transform = occurrence.transform
            expected_tx = transform_cm.getCell(0, 3)
            applied_tx = applied_transform.getCell(0, 3)
            
            if abs(applied_tx - expected_tx) < 0.001:
                print(f"✓ Transform applied successfully")
            else:
                print(f"✗ Transform verification failed for {component_name}")
        
        # Final refresh
        adsk.doEvents()
        
        success_count = len(created_components)
        print(f"\n=== SUMMARY ===")
        print(f"Successfully rendered {success_count} out of {len(cut_timbers)} timbers")
        return success_count
        
    except Exception as e:
        print(f"Error in two-pass rendering: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0


def clear_design() -> bool:
    """
    Clear all components from the active design.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        design = get_active_design()
        if not design:
            return False
        
        root_comp = design.rootComponent
        
        # Remove all occurrences
        while root_comp.occurrences.count > 0:
            occurrence = root_comp.occurrences.item(0)
            occurrence.deleteMe()
        
        # Remove all bodies in root component
        while root_comp.bRepBodies.count > 0:
            body = root_comp.bRepBodies.item(0)
            body.deleteMe()
        
        # Remove all sketches in root component  
        while root_comp.sketches.count > 0:
            sketch = root_comp.sketches.item(0)
            sketch.deleteMe()
        
        print("Design cleared successfully")
        return True
        
    except Exception as e:
        print(f"Error clearing design: {str(e)}")
        return False 