"""
Fusion 360 rendering module for GiraffeCAD timber framing system.

This module provides functions to render timber structures in Autodesk Fusion 360
using the Fusion 360 Python API.
"""

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import time
from typing import Optional, Tuple, List
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


def create_timber_geometry(component: adsk.fusion.Component, timber: Timber, component_name: str) -> bool:
    """
    Create the basic rectangular geometry for a timber at the origin.
    
    Args:
        component: Fusion 360 component to create geometry in
        timber: Timber object with dimensions
        component_name: Name for debugging output
        
    Returns:
        bool: True if geometry creation was successful
    """
    try:
        length = timber.length
        width = float(timber.size[0])
        height = float(timber.size[1])
        
        # Convert to cm
        length_cm = length * 100
        width_cm = width * 100
        height_cm = height * 100
        
        # Create sketch on XY plane
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Create rectangle centered at origin
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
        
        # Get the profile for extrusion
        profile = sketch.profiles.item(0) if sketch.profiles.count > 0 else None
        if not profile:
            print(f"Failed to create profile for {component_name}")
            return False
        
        # Create extrusion
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(length_cm)
        extrude_input.setDistanceExtent(False, distance)
        extrude = extrudes.add(extrude_input)
        
        if extrude:
            print(f"✓ Created geometry for {component_name}")
            return True
        else:
            print(f"✗ Failed to create extrusion for {component_name}")
            return False
            
    except Exception as e:
        print(f"Error creating geometry for {component_name}: {str(e)}")
        return False


def verify_and_retry_transform(occurrence: adsk.fusion.Occurrence, expected_transform: adsk.core.Matrix3D, component_name: str) -> bool:
    """
    Verify that a transform was applied correctly and retry if needed.
    
    Args:
        occurrence: The occurrence to verify
        expected_transform: The expected transformation matrix
        component_name: Name for debugging output
        
    Returns:
        bool: True if transform is correctly applied
    """
    # Verify transform was applied correctly
    applied_transform = occurrence.transform
    expected_tx = expected_transform.getCell(0, 3)
    expected_ty = expected_transform.getCell(1, 3)
    expected_tz = expected_transform.getCell(2, 3)
    applied_tx = applied_transform.getCell(0, 3)
    applied_ty = applied_transform.getCell(1, 3)
    applied_tz = applied_transform.getCell(2, 3)
    
    # Check all translation components
    translation_ok = (abs(applied_tx - expected_tx) < 0.001 and 
                    abs(applied_ty - expected_ty) < 0.001 and 
                    abs(applied_tz - expected_tz) < 0.001)
    
    if translation_ok:
        print(f"✓ Transform applied successfully")
        return True
    else:
        print(f"✗ Transform verification failed for {component_name}")
        print(f"  Expected translation: ({expected_tx:.3f}, {expected_ty:.3f}, {expected_tz:.3f})")
        print(f"  Applied translation:  ({applied_tx:.3f}, {applied_ty:.3f}, {applied_tz:.3f})")
        
        # Try re-applying the transform as a fix
        print(f"  Attempting to re-apply transform...")
        occurrence.transform = expected_transform
        time.sleep(0.1)
        adsk.doEvents()
        
        # Verify again
        reapplied_transform = occurrence.transform
        reapplied_tx = reapplied_transform.getCell(0, 3)
        reapplied_ty = reapplied_transform.getCell(1, 3)
        reapplied_tz = reapplied_transform.getCell(2, 3)
        
        translation_fixed = (abs(reapplied_tx - expected_tx) < 0.001 and 
                           abs(reapplied_ty - expected_ty) < 0.001 and 
                           abs(reapplied_tz - expected_tz) < 0.001)
        
        if translation_fixed:
            print(f"  ✓ Re-application successful")
            return True
        else:
            print(f"  ✗ Re-application also failed")
            return False


def apply_timber_transform(occurrence: adsk.fusion.Occurrence, timber: Timber, component_name: str) -> bool:
    """
    Apply the correct transform to a timber occurrence.
    
    Args:
        occurrence: The occurrence to transform
        timber: Timber object with position and orientation
        component_name: Name for debugging output
        
    Returns:
        bool: True if transform was applied successfully
    """
    try:
        print(f"Applying transform to: {component_name}")
        
        # Create transform matrix with unit conversion to cm
        position_cm = Matrix([
            timber.bottom_position[0] * 100,
            timber.bottom_position[1] * 100,
            timber.bottom_position[2] * 100
        ])
        transform_cm = create_matrix3d_from_orientation(position_cm, timber.orientation)
        
        # Apply the transform
        occurrence.transform = transform_cm
        
        # For non-axis-aligned timbers, add extra processing time
        time.sleep(0.1)
        adsk.doEvents()
        
        # Verify and retry if needed
        return verify_and_retry_transform(occurrence, transform_cm, component_name)
        
    except Exception as e:
        print(f"Error applying transform to {component_name}: {str(e)}")
        return False


def render_single_timber(cut_timber: CutTimber, root_component: adsk.fusion.Component, component_name: str = None) -> Tuple[bool, Optional[adsk.fusion.Occurrence]]:
    """
    Render a single CutTimber object in Fusion 360.
    
    Args:
        cut_timber: CutTimber object to render
        root_component: Root component to create the timber in
        component_name: Optional name for the component
        
    Returns:
        Tuple[bool, Optional[adsk.fusion.Occurrence]]: Success status and created occurrence
    """
    try:
        timber = cut_timber.timber
        name = component_name or cut_timber.name or "Timber"
        
        print(f"Rendering timber: {name}")
        
        # Create component at origin
        occurrence = root_component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        timber_component = occurrence.component
        timber_component.name = name
        
        # Create basic timber geometry
        geometry_success = create_timber_geometry(timber_component, timber, name)
        if not geometry_success:
            print(f"Failed to create geometry for {name}")
            return False, None
        
        # Apply transform
        transform_success = apply_timber_transform(occurrence, timber, name)
        if not transform_success:
            print(f"Failed to apply transform for {name}")
            # Note: we don't return False here because the geometry was created
        
        return True, occurrence
        
    except Exception as e:
        print(f"Error rendering single timber {component_name}: {str(e)}")
        return False, None


def render_multiple_timbers(cut_timbers: List[CutTimber], base_name: str = "Timber") -> int:
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
            
            # Create component at origin
            occurrence = root_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            timber_component = occurrence.component
            timber_component.name = component_name
            
            # Create geometry
            geometry_success = create_timber_geometry(timber_component, cut_timber.timber, component_name)
            if geometry_success:
                created_components.append((occurrence, cut_timber.timber, component_name))
        
        # Force refresh after all geometry creation
        adsk.doEvents()
        
        # PASS 2: Apply all transforms
        print(f"\n=== PASS 2: Applying transforms ===")
        
        success_count = 0
        for occurrence, timber, component_name in created_components:
            transform_success = apply_timber_transform(occurrence, timber, component_name)
            if transform_success:
                success_count += 1
        
        # Final refresh with extra time for non-axis-aligned timbers to settle
        time.sleep(0.2)
        adsk.doEvents()
        
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