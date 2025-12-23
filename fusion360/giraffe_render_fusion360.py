"""
Fusion 360 rendering module for GiraffeCAD timber framing system using CSG.

This module provides functions to render timber structures in Autodesk Fusion 360
using the MeowMeowCSG system for constructive solid geometry operations.
"""

# Module load tracker - must use app.log for Fusion 360 console
try:
    app = adsk.core.Application.get()
    if app:
        app.log("🦒 MODULE RELOAD TRACKER: giraffe_render_fusion360.py LOADED - CSG Version 🦒")
except:
    pass  # Ignore if app not available during import

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import time
from typing import Optional, List, Tuple
from sympy import Matrix, Float
from giraffe import CutTimber, Timber
from moothymoth import Orientation
from meowmeowcsg import (
    MeowMeowCSG, HalfPlane, Prism, Cylinder, Union, Difference
)


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


def clear_design():
    """Clear all objects from the current design."""
    design = get_active_design()
    if not design:
        print("No active design found")
        return
    
    root = design.rootComponent
    
    # Remove all occurrences
    while root.occurrences.count > 0:
        root.occurrences.item(0).deleteMe()
    
    # Remove all bodies
    while root.bRepBodies.count > 0:
        root.bRepBodies.item(0).deleteMe()
    
    print("Design cleared")


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
    # The orientation matrix columns are [width_direction, height_direction, length_direction]
    # For Fusion 360, we want to create a coordinate system where:
    # - X-axis (col 0) = width_direction
    # - Y-axis (col 1) = height_direction  
    # - Z-axis (col 2) = length_direction
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
    
    # Set the matrix values (4x4 transformation matrix in row-major order)
    matrix3d.setWithArray([
        r00, r01, r02, tx,
        r10, r11, r12, ty,
        r20, r21, r22, tz,
        0.0, 0.0, 0.0, 1.0
    ])
    
    return matrix3d


def render_prism_at_origin(component: adsk.fusion.Component, prism: Prism) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a Prism CSG in the component's local coordinate system.
    
    The prism is rendered in its LOCAL coordinate system where:
    - Width (size[0]) is along X axis
    - Height (size[1]) is along Y axis
    - Length is along Z axis from start_distance to end_distance
    
    NO transformations are applied here - the prism's orientation is stored in the
    Prism object and will be applied later when the entire occurrence is transformed.
    
    Args:
        component: Fusion 360 component to create geometry in
        prism: Prism CSG object
        
    Returns:
        Created BRepBody, or None if creation failed
    """
    try:
        # Extract dimensions
        width = float(prism.size[0])
        height = float(prism.size[1])
        
        # Get start and end distances along the length axis
        if prism.start_distance is None or prism.end_distance is None:
            raise ValueError("Cannot render infinite prism - must have finite start and end distances")
        
        start_dist = float(prism.start_distance)
        end_dist = float(prism.end_distance)
        length = end_dist - start_dist
        
        # Create a sketch on the XY plane
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Create rectangle centered at origin in the XY plane
        # This represents the cross-section of the timber in its local coordinate system
        corner1 = adsk.core.Point3D.create(-width/2, -height/2, 0)
        corner2 = adsk.core.Point3D.create(width/2, height/2, 0)
        rect = sketch.sketchCurves.sketchLines.addTwoPointRectangle(corner1, corner2)
        
        # Get the profile for extrusion
        profile = sketch.profiles.item(0)
        
        # Create extrusion along +Z axis
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        # Set extrusion to go from start_dist to end_dist along Z
        distance = adsk.core.ValueInput.createByReal(length)
        extrude_input.setDistanceExtent(False, distance)
        
        # Set the start position to start_dist (so extrusion goes from start_dist to end_dist)
        start_offset = adsk.core.ValueInput.createByReal(start_dist)
        extrude_input.startExtent = adsk.fusion.OffsetStartDefinition.create(start_offset)
        
        # Create the extrusion
        extrude = extrudes.add(extrude_input)
        
        if not extrude or not extrude.bodies or extrude.bodies.count == 0:
            print("Failed to create extrusion")
            return None
        
        body = extrude.bodies.item(0)
        
        # DO NOT apply any transformations here!
        # The body is now in the component's local coordinate system.
        # The occurrence will be transformed later to position and orient it in global space.
        
        return body
        
    except Exception as e:
        print(f"Error rendering prism: {e}")
        traceback.print_exc()
        return None


def render_meowmeowcsg_component_at_origin(csg: MeowMeowCSG, component_name: str = "CSG_Component") -> Optional[adsk.fusion.Occurrence]:
    """
    Render a MeowMeowCSG object as a new component in Fusion 360 AT THE ORIGIN.
    
    This creates all geometry in local space at the origin. Transforms should be applied
    separately in a later pass for better reliability.
    
    Args:
        csg: MeowMeowCSG object to render
        component_name: Name for the created component
        
    Returns:
        Created Occurrence, or None if creation failed
    """
    design = get_active_design()
    if not design:
        print("No active design found")
        return None
    
    try:
        # Create a new component at origin
        root = design.rootComponent
        transform = adsk.core.Matrix3D.create()
        occurrence = root.occurrences.addNewComponent(transform)
        component = occurrence.component
        component.name = component_name
        
        # Render the CSG in local space
        body = render_csg_in_local_space(component, csg)
        
        if body is None:
            print(f"Failed to render CSG in local space for {component_name}")
            return None
        
        return occurrence
        
    except Exception as e:
        print(f"Error rendering MeowMeowCSG component: {e}")
        traceback.print_exc()
        return None


def render_csg_in_local_space(component: adsk.fusion.Component, csg: MeowMeowCSG) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a CSG object in the component's local coordinate system.
    
    This recursively processes CSG operations (Union, Difference, etc.) and
    creates the corresponding Fusion 360 geometry.
    
    Args:
        component: Component to render into
        csg: CSG object to render
        
    Returns:
        Created BRepBody, or None if creation failed
    """
    if isinstance(csg, Prism):
        return render_prism_at_origin(component, csg)
    
    elif isinstance(csg, Cylinder):
        return render_cylinder_at_origin(component, csg)
    
    elif isinstance(csg, HalfPlane):
        # HalfPlane is typically used for cutting operations, not standalone rendering
        print("Warning: HalfPlane rendering not implemented (typically used in Difference operations)")
        return None
    
    elif isinstance(csg, Union):
        return render_union_at_origin(component, csg)
    
    elif isinstance(csg, Difference):
        return render_difference_at_origin(component, csg)
    
    else:
        print(f"Unknown CSG type: {type(csg)}")
        return None


def render_cylinder_at_origin(component: adsk.fusion.Component, cylinder: Cylinder) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a Cylinder CSG at the origin in the component's local coordinate system.
    
    Args:
        component: Fusion 360 component to create geometry in
        cylinder: Cylinder CSG object
        
    Returns:
        Created BRepBody, or None if creation failed
    """
    try:
        # Extract parameters
        radius = float(cylinder.radius)
        
        if cylinder.start_distance is None or cylinder.end_distance is None:
            raise ValueError("Cannot render infinite cylinder - must have finite start and end distances")
        
        start_dist = float(cylinder.start_distance)
        end_dist = float(cylinder.end_distance)
        length = end_dist - start_dist
        center_dist = (start_dist + end_dist) / 2
        
        # Get axis direction
        axis_dir = cylinder.axis_direction
        
        # Create a sketch on the XY plane
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Create circle centered at origin
        center = adsk.core.Point3D.create(0, 0, 0)
        circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(center, radius)
        
        # Get the profile for extrusion
        profile = sketch.profiles.item(0)
        
        # Create extrusion
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        # Set extrusion distance
        distance = adsk.core.ValueInput.createByReal(length)
        extrude_input.setDistanceExtent(False, distance)
        
        # Create the extrusion
        extrude = extrudes.add(extrude_input)
        
        if not extrude or not extrude.bodies or extrude.bodies.count == 0:
            print("Failed to create cylinder extrusion")
            return None
        
        body = extrude.bodies.item(0)
        
        # Transform the body to the correct position along the axis
        transform = adsk.core.Matrix3D.create()
        
        # Calculate center position
        cx = float(axis_dir[0]) * center_dist
        cy = float(axis_dir[1]) * center_dist
        cz = float(axis_dir[2]) * center_dist
        
        # Adjust for extrusion starting at Z=0
        transform.translation = adsk.core.Vector3D.create(cx, cy, cz - length/2 + center_dist)
        
        # Apply transformation
        move_features = component.features.moveFeatures
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(body)
        move_input = move_features.createInput(bodies, transform)
        move_features.add(move_input)
        
        return body
        
    except Exception as e:
        print(f"Error rendering cylinder: {e}")
        traceback.print_exc()
        return None


def render_union_at_origin(component: adsk.fusion.Component, union: Union) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a Union CSG operation at the origin.
    
    Args:
        component: Component to render into
        union: Union CSG object
        
    Returns:
        Combined BRepBody, or None if creation failed
    """
    if not union.children:
        print("Warning: Empty union")
        return None
    
    # Render the first child
    result_body = render_csg_in_local_space(component, union.children[0])
    
    if result_body is None:
        print("Failed to render first child of union")
        return None
    
    # Union with remaining children
    for i, child in enumerate(union.children[1:], start=1):
        child_body = render_csg_in_local_space(component, child)
        
        if child_body is None:
            print(f"Failed to render union child {i}")
            continue
        
        # Perform union operation
        try:
            combine_features = component.features.combineFeatures
            
            # Create tool collection with the child body
            tools = adsk.core.ObjectCollection.create()
            tools.add(child_body)
            
            # Create combine input (union operation)
            combine_input = combine_features.createInput(result_body, tools)
            combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
            combine_input.isKeepToolBodies = False
            
            # Execute the combine
            combine_features.add(combine_input)
            
            # Give Fusion 360 time to process the union
            time.sleep(0.05)
            adsk.doEvents()
            
        except Exception as e:
            print(f"Error performing union with child {i}: {e}")
            continue
    
    return result_body


def render_difference_at_origin(component: adsk.fusion.Component, difference: Difference) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a Difference CSG operation at the origin.
    
    Args:
        component: Component to render into
        difference: Difference CSG object
        
    Returns:
        Resulting BRepBody after subtraction, or None if creation failed
    """
    # Render the base body
    base_body = render_csg_in_local_space(component, difference.base)
    
    if base_body is None:
        print("Failed to render base of difference")
        return None
    
    # Subtract each child
    for i, subtract_csg in enumerate(difference.subtract):
        subtract_body = render_csg_in_local_space(component, subtract_csg)
        
        if subtract_body is None:
            print(f"Failed to render subtract child {i}")
            continue
        
        # Perform difference operation
        try:
            combine_features = component.features.combineFeatures
            
            # Create tool collection with the subtract body
            tools = adsk.core.ObjectCollection.create()
            tools.add(subtract_body)
            
            # Create combine input (cut operation)
            combine_input = combine_features.createInput(base_body, tools)
            combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            combine_input.isKeepToolBodies = False
            
            # Execute the combine
            combine_features.add(combine_input)
            
            # Give Fusion 360 time to process the difference
            time.sleep(0.05)
            adsk.doEvents()
            
        except Exception as e:
            print(f"Error performing difference with child {i}: {e}")
            continue
    
    return base_body


def apply_timber_transform(occurrence: adsk.fusion.Occurrence, position: Matrix, 
                           orientation: Orientation, component_name: str) -> bool:
    """
    Apply a transform to move a timber occurrence from origin to its final position.
    
    Args:
        occurrence: The occurrence to transform
        position: Target position vector
        orientation: Target orientation
        component_name: Name for debugging
        
    Returns:
        True if transform was applied successfully
    """
    try:
        # Create the transformation matrix
        global_transform = create_matrix3d_from_orientation(position, orientation)
        
        # Apply the transform
        occurrence.transform = global_transform
        
        # Verify the transform was applied correctly
        applied_transform = occurrence.transform
        expected_tx = float(position[0])
        expected_ty = float(position[1])
        expected_tz = float(position[2])
        applied_tx = applied_transform.getCell(0, 3)
        applied_ty = applied_transform.getCell(1, 3)
        applied_tz = applied_transform.getCell(2, 3)
        
        translation_correct = (abs(applied_tx - expected_tx) < 0.001 and 
                              abs(applied_ty - expected_ty) < 0.001 and 
                              abs(applied_tz - expected_tz) < 0.001)
        
        if not translation_correct:
            print(f"⚠️  Transform verification failed for {component_name}")
            print(f"  Expected: ({expected_tx:.3f}, {expected_ty:.3f}, {expected_tz:.3f})")
            print(f"  Applied:  ({applied_tx:.3f}, {applied_ty:.3f}, {applied_tz:.3f})")
            
            # Try re-applying the transform
            print(f"  Attempting to re-apply transform...")
            occurrence.transform = global_transform
            time.sleep(0.1)
            adsk.doEvents()
            
            # Check again
            reapplied_transform = occurrence.transform
            reapplied_tx = reapplied_transform.getCell(0, 3)
            reapplied_ty = reapplied_transform.getCell(1, 3)
            reapplied_tz = reapplied_transform.getCell(2, 3)
            
            translation_fixed = (abs(reapplied_tx - expected_tx) < 0.001 and 
                               abs(reapplied_ty - expected_ty) < 0.001 and 
                               abs(reapplied_tz - expected_tz) < 0.001)
            
            if not translation_fixed:
                print(f"  ✗ Re-application also failed")
                return False
            else:
                print(f"  ✓ Re-application successful")
        
        return True
        
    except Exception as e:
        print(f"Error applying transform to {component_name}: {e}")
        return False


def render_multiple_timbers(cut_timbers: List[CutTimber], base_name: str = "Timber") -> int:
    """
    Render multiple CutTimber objects in Fusion 360 using a three-pass approach.
    
    Pass 1: Create all geometry at origin
    Pass 2: Apply CSG operations (cuts) at origin
    Pass 3: Transform all occurrences to final positions
    
    This approach is more reliable than transforming each timber immediately after creation,
    as it avoids Fusion 360's asynchronous update issues.
    
    Component names are automatically determined from:
    1. CutTimber.name if set
    2. CutTimber.timber.name if set
    3. {base_name}_{index} as fallback
    
    Args:
        cut_timbers: List of CutTimber objects to render
        base_name: Base name for the components (used if timber has no name)
        
    Returns:
        Number of successfully rendered timbers
    """
    app = get_fusion_app()
    
    if app:
        app.log(f"=== THREE-PASS RENDERING: {len(cut_timbers)} timbers ===")
    
    # PASS 1: Create all geometry at origin
    print(f"\n=== PASS 1: Creating geometry at origin ===")
    if app:
        app.log(f"=== PASS 1: Creating geometry at origin ===")
    
    created_components: List[Tuple[adsk.fusion.Occurrence, CutTimber, str]] = []
    
    for i, cut_timber in enumerate(cut_timbers):
        # Use the timber's name if available, otherwise use index
        if cut_timber.name:
            component_name = cut_timber.name
        elif hasattr(cut_timber, 'timber') and cut_timber.timber.name:
            component_name = cut_timber.timber.name
        else:
            component_name = f"{base_name}_{i}"
        
        try:
            print(f"Creating {component_name}...")
            if app:
                app.log(f"Creating {component_name}...")
            
            # Get the CSG representation
            csg = cut_timber.render_timber_without_cuts_csg()
            
            # Render at origin (no transform yet)
            occurrence = render_meowmeowcsg_component_at_origin(csg, component_name)
            
            if occurrence is not None:
                created_components.append((occurrence, cut_timber, component_name))
                print(f"  ✓ Created {component_name}")
                if app:
                    app.log(f"  ✓ Created {component_name}")
            else:
                print(f"  ✗ Failed to create {component_name}")
                if app:
                    app.log(f"  ✗ Failed to create {component_name}")
                    
        except Exception as e:
            print(f"  ✗ Error creating {component_name}: {e}")
            if app:
                app.log(f"  ✗ Error creating {component_name}: {e}")
            traceback.print_exc()
    
    # Force Fusion 360 to process all geometry creation
    time.sleep(0.2)
    adsk.doEvents()
    
    # PASS 2: Apply CSG operations (for now, skip - no cuts implemented yet)
    print(f"\n=== PASS 2: Applying CSG operations ===")
    if app:
        app.log(f"=== PASS 2: Applying CSG operations (skipped - using render_timber_without_cuts_csg) ===")
    print(f"  (Skipped - cuts not yet implemented in CSG rendering)")
    
    # Force refresh
    time.sleep(0.1)
    adsk.doEvents()
    
    # PASS 3: Apply all transforms to move to final positions
    print(f"\n=== PASS 3: Applying transforms ===")
    if app:
        app.log(f"=== PASS 3: Applying transforms to {len(created_components)} components ===")
    
    transform_success_count = 0
    
    for occurrence, cut_timber, component_name in created_components:
        try:
            print(f"Transforming {component_name}...")
            
            # Get timber position and orientation
            position = cut_timber._timber.bottom_position
            orientation = cut_timber._timber.orientation
            
            # Apply the transform
            success = apply_timber_transform(occurrence, position, orientation, component_name)
            
            if success:
                transform_success_count += 1
                print(f"  ✓ Transformed {component_name}")
                if app:
                    app.log(f"  ✓ Transformed {component_name}")
            else:
                print(f"  ✗ Failed to transform {component_name}")
                if app:
                    app.log(f"  ✗ Failed to transform {component_name}")
            
            # Small delay between transforms to avoid race conditions
            time.sleep(0.05)
            adsk.doEvents()
                    
        except Exception as e:
            print(f"  ✗ Error transforming {component_name}: {e}")
            if app:
                app.log(f"  ✗ Error transforming {component_name}: {e}")
            traceback.print_exc()
    
    # Final refresh
    time.sleep(0.2)
    adsk.doEvents()
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Created: {len(created_components)}/{len(cut_timbers)} timbers")
    print(f"Transformed: {transform_success_count}/{len(created_components)} components")
    
    if app:
        app.log(f"=== SUMMARY ===")
        app.log(f"Created: {len(created_components)}/{len(cut_timbers)} timbers")
        app.log(f"Transformed: {transform_success_count}/{len(created_components)} components")
    
    return transform_success_count
