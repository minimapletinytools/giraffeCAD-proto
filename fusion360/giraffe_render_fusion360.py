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
from code_goes_here.moothymoth import Orientation
from code_goes_here.meowmeowcsg import (
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


def render_prism_in_local_space(component: adsk.fusion.Component, prism: Prism, infinite_extent: float = 10000.0) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a Prism CSG in the component's local coordinate system with its orientation and position applied.
    
    The prism is first rendered axis-aligned where:
    - Width (size[0]) is along X axis
    - Height (size[1]) is along Y axis
    - Length is along Z axis from start_distance to end_distance
    
    Then the prism's orientation matrix is applied to rotate it, and finally it's translated to its position.
    
    Args:
        component: Fusion 360 component to create geometry in
        prism: Prism CSG object
        infinite_extent: Extent to use for infinite dimensions (in cm)
        
    Returns:
        Created BRepBody, or None if creation failed
    """
    try:
        # Extract dimensions
        width = float(prism.size[0])
        height = float(prism.size[1])
        
        # Get start and end distances along the length axis
        # For infinite prisms, use the provided extent
        LARGE_NUMBER = infinite_extent
        
        if prism.start_distance is None and prism.end_distance is None:
            # Fully infinite prism - extend both ways
            start_dist = -LARGE_NUMBER
            end_dist = LARGE_NUMBER
            print(f"  Warning: Rendering fully infinite prism, cropping to ±{LARGE_NUMBER}")
        elif prism.start_distance is None:
            # Semi-infinite extending in negative direction
            end_dist = float(prism.end_distance)
            start_dist = end_dist - 2 * LARGE_NUMBER
            print(f"  Warning: Rendering semi-infinite prism (negative), cropping start to {start_dist}")
        elif prism.end_distance is None:
            # Semi-infinite extending in positive direction
            start_dist = float(prism.start_distance)
            end_dist = start_dist + 2 * LARGE_NUMBER
            print(f"  Warning: Rendering semi-infinite prism (positive), cropping end to {end_dist}")
        else:
            # Finite prism
            start_dist = float(prism.start_distance)
            end_dist = float(prism.end_distance)
        
        length = end_dist - start_dist
        
        # Create a sketch on the XY plane
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Create rectangle centered at origin in the XY plane
        # This represents the cross-section in the prism's local coordinate system
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
        
        # Apply the prism's orientation and position
        orientation_matrix = prism.orientation.matrix
        
        # Check if transformation is needed
        is_identity = (orientation_matrix == Matrix.eye(3))
        is_at_origin = (prism.position == Matrix([0, 0, 0]))
        
        app = get_fusion_app()
        if app:
            # log start and end distances
            app.log(f"  render_prism_in_local_space: Start distance: {prism.start_distance}")
            app.log(f"  render_prism_in_local_space: End distance: {prism.end_distance}")
            app.log(f"  render_prism_in_local_space: Position: {prism.position.T}")
            app.log(f"  render_prism_in_local_space: Identity: {is_identity}, At origin: {is_at_origin}")
        
        # Only apply transformation if needed (non-identity rotation or non-zero position)
        if not is_identity or not is_at_origin:
            transform = create_matrix3d_from_orientation(prism.position, prism.orientation)
            
            # Apply the transformation to the body
            move_features = component.features.moveFeatures
            bodies = adsk.core.ObjectCollection.create()
            bodies.add(body)
            move_input = move_features.createInput(bodies, transform)
            move_input.defineAsFreeMove(transform)
            move_features.add(move_input)
        
        return body
        
    except Exception as e:
        print(f"Error rendering prism: {e}")
        traceback.print_exc()
        return None


def render_meowmeowcsg_component_at_origin(csg: MeowMeowCSG, component_name: str = "CSG_Component", timber: Optional[Timber] = None, infinite_extent: float = 10000.0) -> Optional[adsk.fusion.Occurrence]:
    """
    Render a MeowMeowCSG object as a new component in Fusion 360 AT THE ORIGIN.
    
    This creates all geometry in local space at the origin. Transforms should be applied
    separately in a later pass for better reliability.
    
    Args:
        csg: MeowMeowCSG object to render
        component_name: Name for the created component
        timber: Optional timber object (needed for coordinate transformations during cuts)
        infinite_extent: Extent to use for infinite geometry (in cm)
        
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
        body = render_csg_in_local_space(component, csg, timber, infinite_extent)
        
        if body is None:
            print(f"Failed to render CSG in local space for {component_name}")
            return None
        
        return occurrence
        
    except Exception as e:
        print(f"Error rendering MeowMeowCSG component: {e}")
        traceback.print_exc()
        return None


def render_csg_in_local_space(component: adsk.fusion.Component, csg: MeowMeowCSG, timber: Optional[Timber] = None, infinite_extent: float = 10000.0) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a CSG object in the component's (timber's) local coordinate system.
    
    This recursively processes CSG operations (Union, Difference, etc.) and
    creates the corresponding Fusion 360 geometry.
    
    Args:
        component: Component to render into
        csg: CSG object to render
        timber: Optional timber object (needed for coordinate transformations during cuts)
        infinite_extent: Extent to use for infinite geometry (in cm)
        
    Returns:
        Created BRepBody, or None if creation failed
    """
    app = get_fusion_app()
    
    if isinstance(csg, Prism):
        if app:
            app.log(f"  render_csg_in_local_space: Rendering Prism with orientation")
        return render_prism_in_local_space(component, csg, infinite_extent)
    
    elif isinstance(csg, Cylinder):
        if app:
            app.log(f"  render_csg_in_local_space: Rendering Cylinder with orientation")
        return render_cylinder_in_local_space(component, csg)
    
    elif isinstance(csg, HalfPlane):
        # HalfPlane is typically used for cutting operations, not standalone rendering
        print("Warning: HalfPlane rendering not implemented (typically used in Difference operations)")
        if app:
            app.log("Warning: HalfPlane standalone rendering not implemented")
        return None
    
    elif isinstance(csg, Union):
        if app:
            app.log(f"  render_csg_in_local_space: Rendering Union with {len(csg.children)} children")
        return render_union_at_origin(component, csg, timber, infinite_extent)
    
    elif isinstance(csg, Difference):
        if app:
            app.log(f"  render_csg_in_local_space: Rendering Difference (base={type(csg.base).__name__}, {len(csg.subtract)} subtractions)")
        return render_difference_at_origin(component, csg, timber, infinite_extent)
    
    else:
        print(f"Unknown CSG type: {type(csg)}")
        if app:
            app.log(f"Unknown CSG type: {type(csg)}")
        return None


def render_cylinder_in_local_space(component: adsk.fusion.Component, cylinder: Cylinder) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a Cylinder CSG in the component's local coordinate system with orientation and position applied.
    
    The cylinder is created with its axis aligned along +Z, then rotated to match axis_direction
    and translated to the cylinder's position.
    
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
        
        # Get axis direction (normalized)
        axis_dir = cylinder.axis_direction
        axis_norm = axis_dir.norm()
        axis_normalized = axis_dir / axis_norm
        
        # Create a sketch on the XY plane
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # Create circle centered at origin
        center = adsk.core.Point3D.create(0, 0, 0)
        circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(center, radius)
        
        # Get the profile for extrusion
        profile = sketch.profiles.item(0)
        
        # Create extrusion along +Z axis initially
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        # Set extrusion distance
        distance = adsk.core.ValueInput.createByReal(length)
        extrude_input.setDistanceExtent(False, distance)
        
        # Set start offset to position the cylinder correctly along its axis
        start_offset = adsk.core.ValueInput.createByReal(start_dist)
        extrude_input.startExtent = adsk.fusion.OffsetStartDefinition.create(start_offset)
        
        # Create the extrusion
        extrude = extrudes.add(extrude_input)
        
        if not extrude or not extrude.bodies or extrude.bodies.count == 0:
            print("Failed to create cylinder extrusion")
            return None
        
        body = extrude.bodies.item(0)
        
        # Now we need to rotate the cylinder from +Z axis to the axis_direction
        # and translate it to the cylinder's position
        z_axis = Matrix([0, 0, 1])
        
        # Check if axis is already along Z
        dot_with_z = (axis_normalized.T * z_axis)[0, 0]
        is_aligned_with_z = abs(float(dot_with_z) - 1.0) < 0.001
        
        # Check if position is at origin
        is_at_origin = (cylinder.position == Matrix([0, 0, 0]))
        
        app = get_fusion_app()
        if app:
            app.log(f"  render_cylinder_in_local_space: Position: {cylinder.position.T}")
            app.log(f"  render_cylinder_in_local_space: Aligned with Z: {is_aligned_with_z}, At origin: {is_at_origin}")
        
        # Only apply transformation if needed
        if not is_aligned_with_z or not is_at_origin:
            # Calculate rotation matrix if not aligned with Z
            if not is_aligned_with_z:
                # Use Rodrigues' rotation formula
                # Rotation axis: cross product of z_axis and axis_normalized
                rotation_axis = z_axis.cross(axis_normalized)
                rotation_axis_norm = rotation_axis.norm()
                
                if rotation_axis_norm > 0.001:  # Not parallel
                    rotation_axis_unit = rotation_axis / rotation_axis_norm
                    
                    # Rotation angle
                    import math
                    cos_angle = float(dot_with_z)
                    angle = math.acos(max(-1.0, min(1.0, cos_angle)))  # Clamp to avoid numerical errors
                    
                    # Create rotation matrix using Rodrigues' formula
                    K = Matrix([
                        [0, -rotation_axis_unit[2], rotation_axis_unit[1]],
                        [rotation_axis_unit[2], 0, -rotation_axis_unit[0]],
                        [-rotation_axis_unit[1], rotation_axis_unit[0], 0]
                    ])
                    
                    rotation_matrix = Matrix.eye(3) + math.sin(angle) * K + (1 - math.cos(angle)) * (K * K)
                    cylinder_orientation = Orientation(rotation_matrix)
                else:
                    # Parallel but might be anti-parallel, use identity
                    cylinder_orientation = Orientation.identity()
            else:
                # Already aligned with Z, use identity orientation
                cylinder_orientation = Orientation.identity()
            
            # Apply rotation and translation
            transform = create_matrix3d_from_orientation(cylinder.position, cylinder_orientation)
            
            # Apply the transformation
            move_features = component.features.moveFeatures
            bodies = adsk.core.ObjectCollection.create()
            bodies.add(body)
            move_input = move_features.createInput(bodies, transform)
            move_input.defineAsFreeMove(transform)
            move_features.add(move_input)
        
        return body
        
    except Exception as e:
        print(f"Error rendering cylinder: {e}")
        traceback.print_exc()
        return None


def render_union_at_origin(component: adsk.fusion.Component, union: Union, timber: Optional[Timber] = None, infinite_extent: float = 10000.0) -> Optional[adsk.fusion.BRepBody]:
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
    result_body = render_csg_in_local_space(component, union.children[0], timber, infinite_extent)
    
    if result_body is None:
        print("Failed to render first child of union")
        return None
    
    # Union with remaining children
    for i, child in enumerate(union.children[1:], start=1):
        child_body = render_csg_in_local_space(component, child, timber, infinite_extent)
        
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


def transform_halfplane_to_component_space(half_plane: HalfPlane, timber_orientation: Orientation) -> Tuple[adsk.core.Vector3D, float]:
    """
    Prepare a HalfPlane for rendering in Fusion 360's component space.
    
    The HalfPlane is already in the timber's LOCAL coordinate system where:
    - X-component is along width direction
    - Y-component is along height direction
    - Z-component is along length direction
    
    The Fusion 360 component also renders in this same axis-aligned space (prism is created
    axis-aligned at origin, then the occurrence is transformed). So we can use the local
    normal and offset directly without any additional transformation.
    
    Args:
        half_plane: HalfPlane in timber's local coordinates
        timber_orientation: Timber's orientation matrix (not used, kept for API compatibility)
        
    Returns:
        Tuple of (component_space_normal_vector, component_space_offset)
    """
    # Extract local normal and offset
    local_normal = half_plane.normal
    local_offset = half_plane.offset
    
    # The local normal is already in the correct space for component rendering
    # No transformation needed!
    component_normal = local_normal
    component_offset = local_offset
    
    # Debug logging
    app = get_fusion_app()
    if app:
        app.log(f"      HalfPlane normal (local/component): ({local_normal[0,0]:.4f}, {local_normal[1,0]:.4f}, {local_normal[2,0]:.4f})")
        app.log(f"      HalfPlane offset (local/component): {local_offset:.4f}")
    
    # Convert to Fusion 360 types
    component_normal_vector = adsk.core.Vector3D.create(
        float(component_normal[0,0]),
        float(component_normal[1,0]),
        float(component_normal[2,0])
    )
    
    return component_normal_vector, float(component_offset)


def apply_halfplane_cut(component: adsk.fusion.Component, body: adsk.fusion.BRepBody, half_plane: HalfPlane, timber: Optional[Timber] = None, infinite_extent: float = 10000.0) -> bool:
    """
    Apply a HalfPlane cut to a body using a large box and boolean difference.
    
    The HalfPlane is defined in global coordinates but must be transformed to the timber's
    local coordinate system for rendering.
    
    Args:
        component: Component containing the body
        body: Body to cut
        half_plane: HalfPlane defining the cut (in global coordinates)
        timber: Timber object (needed for coordinate transformation)
        infinite_extent: Extent to use for the cutting box (in cm)
        
    Returns:
        True if cut was applied successfully
    """
    app = get_fusion_app()
    
    try:
        if app:
            app.log(f"    apply_halfplane_cut: Starting (global coords)")
            
        # Log global coordinates
        global_nx = float(half_plane.normal[0])
        global_ny = float(half_plane.normal[1])
        global_nz = float(half_plane.normal[2])
        global_d = float(half_plane.offset)
        if app:
            app.log(f"      Global: normal=({global_nx:.4f}, {global_ny:.4f}, {global_nz:.4f}), offset={global_d:.4f}")
        
        # Transform to local coordinates if timber is provided
        # The body is rendered axis-aligned, then the occurrence is transformed later
        # Cuts must be in the body's local space to be correct after transform
        if timber is not None:
            plane_normal, plane_offset = transform_halfplane_to_component_space(half_plane, timber.orientation)
            if app:
                app.log(f"      Local:  normal=({plane_normal.x:.4f}, {plane_normal.y:.4f}, {plane_normal.z:.4f}), offset={plane_offset:.4f}")
        else:
            # No transformation - use global coordinates directly
            plane_normal = adsk.core.Vector3D.create(global_nx, global_ny, global_nz)
            plane_offset = global_d
            if app:
                app.log(f"      WARNING: No timber provided, using global coordinates")
        
        # The plane equation is: normal · P = offset
        # We need to find a point on the plane within the timber's bounds
        # The timber's centerline in local coords is along the Z-axis: (0, 0, z)
        # Find where the plane intersects the centerline:
        # normal · (0, 0, z) = offset
        # normal_z * z = offset
        # z = offset / normal_z
        #
        # However, if normal_z is close to 0, the plane is parallel to the centerline
        # In that case, use the origin (0, 0, 0) projected onto the plane
        
        if abs(plane_normal.z) > 0.01:
            # Plane intersects the centerline at z = offset / normal_z
            z_intersect = plane_offset / plane_normal.z
            plane_point = adsk.core.Point3D.create(0, 0, z_intersect)
        else:
            # Plane is parallel to centerline, use normal * offset / |normal|^2
            normal_mag_sq = plane_normal.x**2 + plane_normal.y**2 + plane_normal.z**2
            plane_point = adsk.core.Point3D.create(
                plane_normal.x * plane_offset / normal_mag_sq,
                plane_normal.y * plane_offset / normal_mag_sq,
                plane_normal.z * plane_offset / normal_mag_sq
            )
        
        if app:
            app.log(f"    Creating cutting half-space at point ({plane_point.x:.4f}, {plane_point.y:.4f}, {plane_point.z:.4f})")
        
        # Create a large box representing the half-space to subtract
        # The box extends from the plane in the direction of -normal (the "outside" to remove)
        try:
            # Use the provided extent for the cutting box
            BOX_SIZE = infinite_extent * 2  # Double for safety
            
            # Create a sketch on XY plane to make the cutting box
            sketches = component.sketches
            xy_plane = component.xYConstructionPlane
            sketch = sketches.add(xy_plane)
            
            # Create a large rectangle centered at origin
            corner1 = adsk.core.Point3D.create(-BOX_SIZE, -BOX_SIZE, 0)
            corner2 = adsk.core.Point3D.create(BOX_SIZE, BOX_SIZE, 0)
            rect = sketch.sketchCurves.sketchLines.addTwoPointRectangle(corner1, corner2)
            
            # Get the profile for extrusion
            profile = sketch.profiles.item(0)
            
            # Extrude the box
            extrudes = component.features.extrudeFeatures
            extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            
            # Extrude a very large distance
            distance = adsk.core.ValueInput.createByReal(BOX_SIZE)
            extrude_input.setDistanceExtent(False, distance)
            
            # Create the extrusion
            extrude = extrudes.add(extrude_input)
            
            if not extrude or not extrude.bodies or extrude.bodies.count == 0:
                print("    Failed to create cutting box")
                if app:
                    app.log("    ERROR: Failed to create cutting box")
                return False
            
            cutting_box = extrude.bodies.item(0)
            
            if app:
                app.log(f"    Cutting box created, now positioning it...")
            
            # Transform the cutting box to align with the half-plane
            # We need to position it so the cutting plane is at plane_point with normal plane_normal
            # The box currently extends from Z=0 to Z=BOX_SIZE
            # We want to position it so that Z=0 aligns with our cutting plane
            
            # Create transformation matrix
            # We need to:
            # 1. Rotate so Z-axis aligns with -plane_normal (because we want the Z=0 face to be the cutting plane)
            # 2. Translate so the Z=0 face passes through plane_point
            
            # Build rotation matrix to align Z-axis with +plane_normal
            # In giraffe.py, we do Difference(timber, [HalfPlane])
            # HalfPlane represents points where normal · P >= offset (material to REMOVE)
            # Difference removes those points, so we remove where normal · P >= offset
            # Therefore, the cutting box should represent the region where normal · P >= offset
            # The box extends from Z=0 in the +Z direction
            # So we align Z-axis with +normal to remove the correct half-space
            new_z = adsk.core.Vector3D.create(plane_normal.x, plane_normal.y, plane_normal.z)
            new_z.normalize()
            
            # Choose an arbitrary X axis perpendicular to new_z
            if abs(new_z.z) < 0.9:
                new_x = adsk.core.Vector3D.create(0, 0, 1)
            else:
                new_x = adsk.core.Vector3D.create(1, 0, 0)
            
            # Make new_x perpendicular to new_z
            temp = new_z.crossProduct(new_x)
            new_y = temp
            new_y.normalize()
            new_x = new_y.crossProduct(new_z)
            new_x.normalize()
            
            # Create transformation matrix
            transform = adsk.core.Matrix3D.create()
            
            if app:
                app.log(f"    Aligning cutting box:")
                app.log(f"      From: origin=(0,0,0), Z=(0,0,1)")
                app.log(f"      To: origin=({plane_point.x:.4f},{plane_point.y:.4f},{plane_point.z:.4f}), Z=({new_z.x:.4f},{new_z.y:.4f},{new_z.z:.4f})")
            
            transform.setToAlignCoordinateSystems(
                adsk.core.Point3D.create(0, 0, 0),
                adsk.core.Vector3D.create(1, 0, 0),
                adsk.core.Vector3D.create(0, 1, 0),
                adsk.core.Vector3D.create(0, 0, 1),
                plane_point,
                new_x,
                new_y,
                new_z
            )
            
            # Create a move feature to position the cutting box
            move_features = component.features.moveFeatures
            bodies_to_move = adsk.core.ObjectCollection.create()
            bodies_to_move.add(cutting_box)
            move_input = move_features.createInput(bodies_to_move, transform)
            move_features.add(move_input)
            
            if app:
                app.log(f"    Cutting box positioned, performing boolean cut...")
            
            # Perform boolean difference: body - cutting_box
            combine_features = component.features.combineFeatures
            tools = adsk.core.ObjectCollection.create()
            tools.add(cutting_box)
            combine_input = combine_features.createInput(body, tools)
            combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            combine_input.isKeepToolBodies = False
            
            combine_features.add(combine_input)
            
            if app:
                app.log(f"    Boolean cut complete")
            
        except Exception as e:
            print(f"    ERROR during half-plane cut: {e}")
            if app:
                app.log(f"    ERROR during half-plane cut: {e}")
            traceback.print_exc()
            return False
        
        time.sleep(0.05)
        adsk.doEvents()
        
        return True
        
    except Exception as e:
        print(f"  Error applying HalfPlane cut: {e}")
        traceback.print_exc()
        return False


def render_difference_at_origin(component: adsk.fusion.Component, difference: Difference, timber: Optional[Timber] = None, infinite_extent: float = 10000.0) -> Optional[adsk.fusion.BRepBody]:
    """
    Render a Difference CSG operation at the origin.
    
    For HalfPlane cuts, uses split operations instead of creating infinite solids.
    For other CSG types, creates the solid and performs boolean difference.
    
    Args:
        component: Component to render into
        difference: Difference CSG object
        timber: Optional timber object (needed for coordinate transformations during cuts)
        infinite_extent: Extent to use for infinite geometry (in cm)
        
    Returns:
        Resulting BRepBody after subtraction, or None if creation failed
    """
    app = get_fusion_app()
    
    if app:
        app.log(f"render_difference_at_origin: Starting - base type={type(difference.base).__name__}, {len(difference.subtract)} cuts")
    
    # Render the base body
    base_body = render_csg_in_local_space(component, difference.base, timber, infinite_extent)
    
    if base_body is None:
        print("Failed to render base of difference")
        if app:
            app.log("ERROR: Failed to render base of difference")
        return None
    
    if app:
        app.log(f"render_difference_at_origin: Base body created successfully, now applying {len(difference.subtract)} cuts")
    
    # Subtract each child
    for i, subtract_csg in enumerate(difference.subtract):
        # Special handling for HalfPlane cuts
        if isinstance(subtract_csg, HalfPlane):
            print(f"  Applying HalfPlane cut {i+1}/{len(difference.subtract)} using split operation")
            if app:
                app.log(f"  Applying HalfPlane cut {i+1}/{len(difference.subtract)} using split operation")
            success = apply_halfplane_cut(component, base_body, subtract_csg, timber, infinite_extent)
            if not success:
                print(f"  Failed to apply HalfPlane cut {i+1}")
                if app:
                    app.log(f"  ERROR: Failed to apply HalfPlane cut {i+1}")
            else:
                if app:
                    app.log(f"  SUCCESS: Applied HalfPlane cut {i+1}")
            continue
        
        # For other CSG types, render and perform boolean difference
        print(f"  Applying {type(subtract_csg).__name__} cut {i+1}/{len(difference.subtract)} using boolean difference")
        if app:
            app.log(f"  Applying {type(subtract_csg).__name__} cut {i+1}/{len(difference.subtract)} using boolean difference")
        
        subtract_body = render_csg_in_local_space(component, subtract_csg, timber, infinite_extent)
        
        if subtract_body is None:
            print(f"  Failed to render subtract child {i+1}")
            if app:
                app.log(f"  ERROR: Failed to render subtract child {i+1}")
            continue
        
        if app:
            app.log(f"    Subtract body created, performing combine cut operation...")
        
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
            
            if app:
                app.log(f"    SUCCESS: Boolean cut applied for child {i+1}")
            
            # Give Fusion 360 time to process the difference
            time.sleep(0.05)
            adsk.doEvents()
            
        except Exception as e:
            print(f"  Error performing difference with child {i+1}: {e}")
            if app:
                app.log(f"  ERROR performing difference with child {i+1}: {e}")
            continue
    
    if app:
        app.log(f"render_difference_at_origin: COMPLETE - all {len(difference.subtract)} cuts processed")
    
    return base_body


def apply_timber_transform(occurrence: adsk.fusion.Occurrence, position: Matrix, 
                           orientation: Orientation, component_name: str) -> bool:
    """
    Apply a transform to move a timber occurrence from origin to its final position.
    
    Uses occurrence.transform2 to set the transform, which properly records it.
    
    Args:
        occurrence: The occurrence to transform
        position: Target position vector
        orientation: Target orientation
        component_name: Name for debugging
        
    Returns:
        True if transform was applied successfully
    """
    try:
        # Get the design
        design = get_active_design()
        if not design:
            print(f"Error: No active design for {component_name}")
            return False
        
        # Create the transformation matrix
        global_transform = create_matrix3d_from_orientation(position, orientation)
        
        # Set the transform using transform2 property
        # transform2 is the proper way to set occurrence transforms and records them
        occurrence.transform2 = global_transform
        
        # Give Fusion 360 time to process
        time.sleep(0.05)
        adsk.doEvents()
        
        # Verify the transform was applied correctly
        applied_transform = occurrence.transform2
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
            return False
        
        return True
        
    except Exception as e:
        print(f"Error applying transform to {component_name}: {e}")
        traceback.print_exc()
        return False


def calculate_structure_extents(cut_timbers: List[CutTimber]) -> float:
    """
    Calculate the bounding box extent of all timbers in the structure.
    
    Args:
        cut_timbers: List of CutTimber objects
        
    Returns:
        Maximum extent (half-size of bounding box) in cm
    """
    if not cut_timbers:
        return 1000.0  # Default 10m
    
    # Find min and max coordinates across all timbers
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    
    for cut_timber in cut_timbers:
        timber = cut_timber._timber
        
        # Get the 8 corners of the timber bounding box
        # Bottom corners
        bottom_pos = timber.bottom_position
        
        # Top position
        top_pos = bottom_pos + timber.length_direction * timber.length
        
        # Width and height directions
        width_dir = Matrix([
            timber.orientation.matrix[0, 0],
            timber.orientation.matrix[1, 0],
            timber.orientation.matrix[2, 0]
        ])
        height_dir = Matrix([
            timber.orientation.matrix[0, 1],
            timber.orientation.matrix[1, 1],
            timber.orientation.matrix[2, 1]
        ])
        
        # Half-size offsets
        half_width = timber.size[0] / 2
        half_height = timber.size[1] / 2
        
        # All 8 corners
        corners = [
            bottom_pos + width_dir * half_width + height_dir * half_height,
            bottom_pos + width_dir * half_width - height_dir * half_height,
            bottom_pos - width_dir * half_width + height_dir * half_height,
            bottom_pos - width_dir * half_width - height_dir * half_height,
            top_pos + width_dir * half_width + height_dir * half_height,
            top_pos + width_dir * half_width - height_dir * half_height,
            top_pos - width_dir * half_width + height_dir * half_height,
            top_pos - width_dir * half_width - height_dir * half_height,
        ]
        
        # Update min/max
        for corner in corners:
            x, y, z = float(corner[0]), float(corner[1]), float(corner[2])
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            min_z = min(min_z, z)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            max_z = max(max_z, z)
    
    # Calculate extent (maximum half-dimension)
    extent_x = (max_x - min_x) / 2
    extent_y = (max_y - min_y) / 2
    extent_z = (max_z - min_z) / 2
    
    extent = max(extent_x, extent_y, extent_z)
    
    app = get_fusion_app()
    if app:
        app.log(f"Structure extents: {extent_x:.2f} x {extent_y:.2f} x {extent_z:.2f} cm")
        app.log(f"Maximum extent: {extent:.2f} cm")
    
    return extent


def check_body_extents(body: adsk.fusion.BRepBody, max_allowed_extent: float, component_name: str) -> bool:
    """
    Check if a body extends beyond the allowed extent and warn if so.
    
    Args:
        body: Body to check
        max_allowed_extent: Maximum allowed extent in cm
        component_name: Name of component for warning message
        
    Returns:
        True if within bounds, False if too large
    """
    try:
        if not body or not body.boundingBox:
            return True
        
        bbox = body.boundingBox
        extent_x = (bbox.maxPoint.x - bbox.minPoint.x) / 2
        extent_y = (bbox.maxPoint.y - bbox.minPoint.y) / 2
        extent_z = (bbox.maxPoint.z - bbox.minPoint.z) / 2
        
        max_extent = max(extent_x, extent_y, extent_z)
        
        if max_extent > max_allowed_extent:
            print(f"⚠️  WARNING: {component_name} extends {max_extent:.2f} cm (exceeds limit of {max_allowed_extent:.2f} cm)")
            app = get_fusion_app()
            if app:
                app.log(f"⚠️  WARNING: {component_name} extends {max_extent:.2f} cm (exceeds limit of {max_allowed_extent:.2f} cm)")
            return False
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not check extents for {component_name}: {e}")
        return True


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
    
    # Calculate structure extents for intelligent sizing of infinite geometry
    print(f"\n=== Calculating structure extents ===")
    if app:
        app.log(f"=== Calculating structure extents ===")
    
    structure_extent = calculate_structure_extents(cut_timbers)
    infinite_geometry_extent = structure_extent * 10  # 10x for infinite geometry
    validation_extent = structure_extent * 5  # 5x for validation warnings
    
    print(f"Structure extent: {structure_extent:.2f} cm")
    print(f"Infinite geometry will extend to: {infinite_geometry_extent:.2f} cm")
    print(f"Validation threshold: {validation_extent:.2f} cm")
    
    if app:
        app.log(f"Infinite geometry extent: {infinite_geometry_extent:.2f} cm")
        app.log(f"Validation threshold: {validation_extent:.2f} cm")
    
    # PASS 1: Create all geometry at origin with cuts applied
    print(f"\n=== PASS 1: Creating geometry at origin (with cuts) ===")
    if app:
        app.log(f"=== PASS 1: Creating geometry at origin (with cuts) ===")
    
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
            
            # Get the timber with cuts applied in LOCAL coordinates
            # Local coordinates means the prism distances are relative to the timber's bottom_position
            # and all cuts are also in local coordinates. This allows us to render at origin and then transform.
            csg = cut_timber.render_timber_with_cuts_csg_local()
            
            if cut_timber._cuts:
                print(f"  Applying {len(cut_timber._cuts)} cut(s)")
                if app:
                    app.log(f"  Applying {len(cut_timber._cuts)} cut(s)")
            
            # Render at origin (no transform yet)
            # Pass timber info for coordinate transformations
            if app:
                app.log(f"  About to render CSG (type: {type(csg).__name__})")
            
            occurrence = render_meowmeowcsg_component_at_origin(csg, component_name, cut_timber._timber, infinite_geometry_extent)
            
            if occurrence is not None:
                # Validate geometry extents
                component = occurrence.component
                if component.bRepBodies.count > 0:
                    for body_idx in range(component.bRepBodies.count):
                        body = component.bRepBodies.item(body_idx)
                        check_body_extents(body, validation_extent, component_name)
                
                created_components.append((occurrence, cut_timber, component_name))
                print(f"  ✓ Created {component_name}")
                if app:
                    app.log(f"  ✓ Created {component_name} - CSG rendered successfully")
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
    
    # PASS 2: No longer needed - cuts are applied in Pass 1
    print(f"\n=== PASS 2: CSG operations (already applied in Pass 1) ===")
    if app:
        app.log(f"=== PASS 2: CSG operations (already applied in Pass 1) ===")
    
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
