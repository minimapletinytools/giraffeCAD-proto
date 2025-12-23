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
from typing import Optional, List
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
    Render a Prism CSG at the origin in the component's local coordinate system.
    
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
        
        # Get orientation axes
        orientation_matrix = prism.orientation.matrix
        width_dir = Matrix([orientation_matrix[0, 0], orientation_matrix[1, 0], orientation_matrix[2, 0]])
        height_dir = Matrix([orientation_matrix[0, 1], orientation_matrix[1, 1], orientation_matrix[2, 1]])
        length_dir = Matrix([orientation_matrix[0, 2], orientation_matrix[1, 2], orientation_matrix[2, 2]])
        
        # Calculate the center position of the prism in local space
        if prism.start_distance is None or prism.end_distance is None:
            raise ValueError("Cannot render infinite prism - must have finite start and end distances")
        
        start_dist = float(prism.start_distance)
        end_dist = float(prism.end_distance)
        length = end_dist - start_dist
        center_dist = (start_dist + end_dist) / 2
        
        # Center position along the length axis
        center_pos = length_dir * center_dist
        
        # Create a sketch on the XY plane
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Calculate the four corner points of the rectangle in the sketch's coordinate system
        # We need to project the prism's cross-section onto the XY plane
        # For now, assume the prism is axis-aligned (orientation is identity or close to it)
        # TODO: Handle arbitrary orientations properly
        
        # Create rectangle centered at origin in the sketch
        corner1 = adsk.core.Point3D.create(-width/2, -height/2, 0)
        corner2 = adsk.core.Point3D.create(width/2, height/2, 0)
        rect = sketch.sketchCurves.sketchLines.addTwoPointRectangle(corner1, corner2)
        
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
            print("Failed to create extrusion")
            return None
        
        body = extrude.bodies.item(0)
        
        # Transform the body to the correct position and orientation
        # First translate to center position
        transform = adsk.core.Matrix3D.create()
        
        # The body was extruded along +Z from the XY plane
        # We need to:
        # 1. Translate it so the start of extrusion is at start_distance
        # 2. Rotate it to match the orientation
        # 3. Translate to center_pos
        
        # For now, just translate to center (assuming standard orientation)
        cx = float(center_pos[0])
        cy = float(center_pos[1])
        cz = float(center_pos[2])
        
        # Adjust Z to account for extrusion starting at Z=0
        # The extrusion creates a body from Z=0 to Z=length
        # We need to shift it so it spans from start_dist to end_dist
        transform.translation = adsk.core.Vector3D.create(cx, cy, cz - length/2 + center_dist)
        
        # Apply transformation
        move_features = component.features.moveFeatures
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(body)
        move_input = move_features.createInput(bodies, transform)
        move_features.add(move_input)
        
        return body
        
    except Exception as e:
        print(f"Error rendering prism: {e}")
        traceback.print_exc()
        return None


def render_meowmeowcsg_component(csg: MeowMeowCSG, component_name: str = "CSG_Component", 
                                  position: Optional[Matrix] = None,
                                  orientation: Optional[Orientation] = None) -> Optional[adsk.fusion.Occurrence]:
    """
    Render a MeowMeowCSG object as a new component in Fusion 360.
    
    This creates all geometry in local space first, then transforms the entire
    component to global space based on the provided position and orientation.
    
    Args:
        csg: MeowMeowCSG object to render
        component_name: Name for the created component
        position: Position vector for the component in global space (default: origin)
        orientation: Orientation for the component in global space (default: identity)
        
    Returns:
        Created Occurrence, or None if creation failed
    """
    design = get_active_design()
    if not design:
        print("No active design found")
        return None
    
    try:
        # Default position and orientation
        if position is None:
            position = Matrix([0, 0, 0])
        if orientation is None:
            orientation = Orientation()
        
        # Create a new component
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
        
        # Transform the entire occurrence to global space
        global_transform = create_matrix3d_from_orientation(position, orientation)
        occurrence.transform = global_transform
        
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
            
        except Exception as e:
            print(f"Error performing difference with child {i}: {e}")
            continue
    
    return base_body


def render_cut_timber(cut_timber: CutTimber, component_name: Optional[str] = None) -> Optional[adsk.fusion.Occurrence]:
    """
    Render a CutTimber using its CSG representation.
    
    This renders the timber with all cuts applied in local space, then transforms
    to global space based on the timber's position and orientation.
    
    Args:
        cut_timber: CutTimber object to render
        component_name: Optional name for the component (defaults to "Timber_X")
        
    Returns:
        Created Occurrence, or None if rendering failed
    """
    if component_name is None:
        component_name = f"Timber_{id(cut_timber)}"
    
    # Get the CSG representation
    # For now, use render_timber_without_cuts_csg which gives us a finite prism
    csg = cut_timber.render_timber_without_cuts_csg()
    
    # Get timber position and orientation
    position = cut_timber._timber.bottom_position
    orientation = cut_timber._timber.orientation
    
    # Render the CSG as a component
    return render_meowmeowcsg_component(csg, component_name, position, orientation)


def render_multiple_timbers(cut_timbers: List[CutTimber], base_name: str = "Timber") -> int:
    """
    Render multiple CutTimber objects in Fusion 360.
    
    Args:
        cut_timbers: List of CutTimber objects to render
        base_name: Base name for the components
        
    Returns:
        Number of successfully rendered timbers
    """
    success_count = 0
    
    for i, cut_timber in enumerate(cut_timbers):
        component_name = f"{base_name}_{i}"
        
        try:
            occurrence = render_cut_timber(cut_timber, component_name)
            
            if occurrence is not None:
                success_count += 1
                print(f"✓ Rendered {component_name}")
            else:
                print(f"✗ Failed to render {component_name}")
                
        except Exception as e:
            print(f"✗ Error rendering {component_name}: {e}")
            traceback.print_exc()
    
    return success_count
