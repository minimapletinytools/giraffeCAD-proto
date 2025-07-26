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
    # Matrix3D constructor takes 16 values for a 4x4 transformation matrix
    # arranged in row-major order
    matrix3d = adsk.core.Matrix3D.create()
    
    # Extract rotation matrix values (convert sympy expressions to floats)
    r00 = float(orientation.matrix[0, 0])
    r01 = float(orientation.matrix[0, 1]) 
    r02 = float(orientation.matrix[0, 2])
    r10 = float(orientation.matrix[1, 0])
    r11 = float(orientation.matrix[1, 1])
    r12 = float(orientation.matrix[1, 2])
    r20 = float(orientation.matrix[2, 0])
    r21 = float(orientation.matrix[2, 1])
    r22 = float(orientation.matrix[2, 2])
    
    # Extract translation values
    tx = float(position[0])
    ty = float(position[1])
    tz = float(position[2])
    
    # Set the matrix values (4x4 transformation matrix)
    matrix3d.setWithArray([
        r00, r01, r02, tx,   # First row
        r10, r11, r12, ty,   # Second row  
        r20, r21, r22, tz,   # Third row
        0.0, 0.0, 0.0, 1.0   # Fourth row
    ])
    
    return matrix3d


def render_CutTimber(cut_timber: CutTimber, component_name: Optional[str] = None) -> bool:
    """
    Render a CutTimber as a rectangular prism in Fusion 360.
    
    Args:
        cut_timber: The CutTimber object to render
        component_name: Optional name for the component (defaults to "Timber")
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the active design
        design = get_active_design()
        if not design:
            print("Error: No active design found in Fusion 360")
            return False
        
        # Get the root component
        root_comp = design.rootComponent
        
        # Create a new component for this timber
        if component_name is None:
            component_name = "Timber"
        
        occurrence = root_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        timber_component = occurrence.component
        timber_component.name = component_name
        
        # Get timber properties
        timber = cut_timber.timber
        length = timber.length
        width = float(timber.size[0])  # X dimension
        height = float(timber.size[1])  # Y dimension
        
        # Convert units from meters to centimeters (Fusion 360 default)
        length_cm = length * 100
        width_cm = width * 100
        height_cm = height * 100
        
        # Create the transformation matrix for the timber
        transform = create_matrix3d_from_orientation(timber.bottom_position, timber.orientation)
        
        # Create a sketch on the XY plane of the component
        sketches = timber_component.sketches
        xy_plane = timber_component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Draw a rectangle representing the timber's cross-section
        # The rectangle is centered at origin and extends from -width/2 to +width/2 
        # and -height/2 to +height/2
        rect_lines = sketch.sketchCurves.sketchLines
        
        # Define rectangle corners (in cm)
        x1 = -width_cm / 2
        y1 = -height_cm / 2
        x2 = width_cm / 2
        y2 = height_cm / 2
        
        # Create rectangle
        point1 = adsk.core.Point3D.create(x1, y1, 0)
        point2 = adsk.core.Point3D.create(x2, y1, 0)
        point3 = adsk.core.Point3D.create(x2, y2, 0)
        point4 = adsk.core.Point3D.create(x1, y2, 0)
        
        rect_lines.addByTwoPoints(point1, point2)
        rect_lines.addByTwoPoints(point2, point3)
        rect_lines.addByTwoPoints(point3, point4)
        rect_lines.addByTwoPoints(point4, point1)
        
        # Find the profile for extrusion
        profile = None
        for prof in sketch.profiles:
            profile = prof
            break
        
        if not profile:
            print("Error: Could not create profile for extrusion")
            return False
        
        # Create an extrusion
        extrudes = timber_component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        # Set the extrusion distance (timber length in cm)
        distance = adsk.core.ValueInput.createByReal(length_cm)
        extrude_input.setDistanceExtent(False, distance)
        
        # Create the extrusion
        extrude = extrudes.add(extrude_input)
        
        if not extrude:
            print("Error: Could not create extrusion")
            return False
        
        # Apply the transformation to position the timber correctly
        # Scale the transformation from meters to centimeters
        transform_cm = adsk.core.Matrix3D.create()
        
        # Copy the rotation part
        for i in range(3):
            for j in range(3):
                transform_cm.setCell(i, j, transform.getCell(i, j))
        
        # Scale and copy the translation part (convert from meters to cm)
        transform_cm.setCell(0, 3, transform.getCell(0, 3) * 100)
        transform_cm.setCell(1, 3, transform.getCell(1, 3) * 100) 
        transform_cm.setCell(2, 3, transform.getCell(2, 3) * 100)
        transform_cm.setCell(3, 3, 1.0)
        
        # Set the occurrence transform
        occurrence.transform = transform_cm
        
        # Set the timber material/appearance (optional)
        timber_body = extrude.bodies.item(0)
        if timber_body:
            timber_body.name = f"{component_name}_Body"
            
            # Try to apply a wood material if available
            try:
                materials = design.materials
                wood_material = None
                
                # Look for existing wood materials
                for material in materials:
                    if "wood" in material.name.lower() or "timber" in material.name.lower():
                        wood_material = material
                        break
                
                if wood_material:
                    timber_body.material = wood_material
            except:
                # Material assignment failed, but that's OK
                pass
        
        print(f"Successfully rendered timber: {component_name}")
        return True
        
    except Exception as e:
        print(f"Error rendering timber: {str(e)}")
        print("Full traceback:")
        print(traceback.format_exc())
        return False


def render_multiple_timbers(cut_timbers: list[CutTimber], base_name: str = "Timber") -> int:
    """
    Render multiple CutTimber objects in Fusion 360.
    
    Args:
        cut_timbers: List of CutTimber objects to render
        base_name: Base name for components (will be numbered)
        
    Returns:
        int: Number of timbers successfully rendered
    """
    success_count = 0
    
    for i, cut_timber in enumerate(cut_timbers):
        component_name = f"{base_name}_{i+1:03d}"
        if render_CutTimber(cut_timber, component_name):
            success_count += 1
        else:
            print(f"Failed to render timber {i+1}")
    
    print(f"Successfully rendered {success_count} out of {len(cut_timbers)} timbers")
    return success_count


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