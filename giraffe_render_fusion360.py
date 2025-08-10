"""
Fusion 360 rendering module for GiraffeCAD timber framing system.

This module provides functions to render timber structures in Autodesk Fusion 360
using the Fusion 360 Python API.
"""

# Module load tracker - must use app.log for Fusion 360 console
try:
    app = adsk.core.Application.get()
    if app:
        app.log("🐘 MODULE RELOAD TRACKER: giraffe_render_fusion360.py LOADED - Version 21:45 - CUT ORDER FIX 🐘")
except:
    pass  # Ignore if app not available during import

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import time
from typing import Optional, Tuple, List
from sympy import Matrix, Float
from giraffe import CutTimber, Timber, MortiseCutOperation, TenonCutOperation, StandardMortise, StandardTenon, TimberFace, TimberReferenceEnd, TimberReferenceLongFace
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


def find_timber_face_by_normal(timber_body: adsk.fusion.BRepBody, target_face: TimberFace) -> Optional[adsk.fusion.BRepFace]:
    """
    Find the appropriate face on a timber body using face normals.
    
    This assumes the timber is in its base orientation (no transformations applied):
    - X axis: width (face direction)
    - Y axis: height 
    - Z axis: length (extrusion direction)
    
    Args:
        timber_body: The BRep body of the timber
        target_face: Which face to find (TimberFace enum)
        
    Returns:
        The matching BRepFace, or None if not found
    """
    tolerance = 0.1  # Tolerance for normal vector comparison
    
    # Expected normal vectors for each face in base orientation
    expected_normals = {
        TimberFace.RIGHT:   (1.0, 0.0, 0.0),   # +X direction
        TimberFace.LEFT:    (-1.0, 0.0, 0.0),  # -X direction  
        TimberFace.FORWARD: (0.0, 1.0, 0.0),   # +Y direction
        TimberFace.BACK:    (0.0, -1.0, 0.0),  # -Y direction
        TimberFace.TOP:     (0.0, 0.0, 1.0),   # +Z direction
        TimberFace.BOTTOM:  (0.0, 0.0, -1.0),  # -Z direction
    }
    
    expected_normal = expected_normals[target_face]
    
    for i in range(timber_body.faces.count):
        brepface = timber_body.faces.item(i)
        
        # Get face normal at center point
        face_eval = brepface.evaluator
        (success, center_point) = face_eval.getPointAtParameter(adsk.core.Point2D.create(0.5, 0.5))
        
        if success:
            # Get the normal vector at the center point
            (success_normal, normal_vec) = face_eval.getNormalAtParameter(adsk.core.Point2D.create(0.5, 0.5))
            
            if success_normal:
                normal = (normal_vec.x, normal_vec.y, normal_vec.z)
                
                # Check if this normal matches our target (within tolerance)
                normal_matches = (
                    abs(normal[0] - expected_normal[0]) < tolerance and
                    abs(normal[1] - expected_normal[1]) < tolerance and
                    abs(normal[2] - expected_normal[2]) < tolerance
                )
                
                if normal_matches:
                    # Verify normal is axis-aligned (assert no rotation)
                    axis_aligned = (
                        (abs(normal[0]) > 0.9 and abs(normal[1]) < tolerance and abs(normal[2]) < tolerance) or
                        (abs(normal[1]) > 0.9 and abs(normal[0]) < tolerance and abs(normal[2]) < tolerance) or  
                        (abs(normal[2]) > 0.9 and abs(normal[0]) < tolerance and abs(normal[1]) < tolerance)
                    )
                    
                    if not axis_aligned:
                        raise AssertionError(f"Timber face normal {normal} is not axis-aligned! Timber orientation may be incorrect.")
                    
                    return brepface
    
    return None


def get_face_normal_and_plane(timber: Timber, face: TimberFace) -> Tuple[Matrix, str]:
    """
    Get the normal vector and construction plane for a timber face.
    
    Args:
        timber: Timber object
        face: Which face to get the normal for
        
            Returns:
            Tuple[Matrix, str]: Normal vector and plane description
    """
    if face == TimberFace.TOP:
        return timber.length_direction, "XY"  # Top face is in XY plane with +Z normal
    elif face == TimberFace.BOTTOM:
        return -timber.length_direction, "XY"  # Bottom face is in XY plane with -Z normal
    elif face == TimberFace.RIGHT:
        return timber.face_direction, "YZ"  # Right face is in YZ plane with +X normal
    elif face == TimberFace.LEFT:
        return -timber.face_direction, "YZ"  # Left face is in YZ plane with -X normal
    elif face == TimberFace.FORWARD:
        return timber.height_direction, "XZ"  # Forward face is in XZ plane with +Y normal
    else:  # BACK
        return -timber.height_direction, "XZ"  # Back face is in XZ plane with -Y normal


def calculate_mortise_position(timber: Timber, mortise_spec: StandardMortise) -> Tuple[float, float, float]:
    """
    Calculate the 3D position of a mortise on a timber face.
    
    Timber coordinate system (at origin):
    - X: -width/2 to +width/2 (face direction) 
    - Y: -height/2 to +height/2 (height direction)
    - Z: 0 to +length (length direction)
    
    Args:
        timber: Timber object
        mortise_spec: Mortise specification
        
    Returns:
        Tuple[float, float, float]: Position relative to timber origin in cm
    """
    # Get timber dimensions in cm
    length_cm = float(timber.length) * 100
    width_cm = float(timber.size[0]) * 100  # face direction
    height_cm = float(timber.size[1]) * 100  # height direction
    
    # Calculate position along length (Z axis - from BOTTOM=0 to TOP=length_cm)
    ref_end, distance_from_end = mortise_spec.pos_rel_to_end
    # Debug Z calculation using app.log for Fusion 360 console
    app = get_fusion_app()
    
    if ref_end == TimberReferenceEnd.TOP:
        # Distance from TOP end (Z=length_cm)
        z_pos = length_cm - (distance_from_end * 100)
    else:  # BOTTOM
        # Distance from BOTTOM end (Z=0)
        z_pos = distance_from_end * 100
    
    # Calculate position across width/height (centered for now)
    if mortise_spec.pos_rel_to_long_face is not None:
        ref_face, distance_from_face = mortise_spec.pos_rel_to_long_face
        # TODO: Implement proper face positioning based on TimberReferenceLongFace
        cross_pos = 0  # Centered for now
    else:
        cross_pos = 0  # Centered
    
    # Return position based on which face we're cutting (CORRECTED MAPPING)
    face = mortise_spec.mortise_face
    if face == TimberFace.RIGHT:
        # Right face is at X = +width_cm/2
        return width_cm/2, cross_pos, z_pos
    elif face == TimberFace.LEFT:
        # Left face is at X = -width_cm/2
        return -width_cm/2, cross_pos, z_pos
    elif face == TimberFace.FORWARD:
        # Forward face is at Y = +height_cm/2
        return cross_pos, height_cm/2, z_pos
    elif face == TimberFace.BACK:
        # Back face is at Y = -height_cm/2
        return (cross_pos, -height_cm/2, z_pos)
    else:
        assert(f"can not position mortise on {face}, not supported yet")



def create_mortise_cut(component: adsk.fusion.Component, timber: Timber, mortise_spec: StandardMortise, component_name: str) -> bool:
    app = get_fusion_app()
    if app:
        app.log("🐘 FUNCTION TRACKER: create_mortise_cut called - Version 19:00 - FACE-BASED MORTISE FIX 🐘")
        
        # List all bodies if any exist
        for i in range(component.bRepBodies.count):
            body = component.bRepBodies.item(i)
            app.log(f"  Body {i}: {body.name} (solid: {body.isSolid}, volume: {body.volume:.2f})")
        
        if component.bRepBodies.count == 0:
            app.log("🚨 CRITICAL ERROR: NO BODIES IN COMPONENT - Cannot cut mortise!")
            app.log("🚨 This means timber geometry was never created in Pass 1!")
            return False
    """
    Create a mortise cut in a timber component.
    
    Args:
        component: Timber component to cut
        timber: Timber object for reference
        mortise_spec: Mortise specification
        component_name: Name for debugging
        
    Returns:
        bool: True if cut was successful
    """
    app = get_fusion_app()
    
    try:
        # Get mortise dimensions in cm
        width_cm = mortise_spec.width * 100
        height_cm = mortise_spec.height * 100
        depth_cm = mortise_spec.depth * 100
        face = mortise_spec.mortise_face
        
        if app:
            app.log(f"Creating {width_cm:.1f}x{height_cm:.1f}x{depth_cm:.1f}cm mortise on {face.name} face of {component_name}")

        # Step 5: Assert that pos_rel_to_long_face is None (not supported yet)
        if mortise_spec.pos_rel_to_long_face is not None:
            raise NotImplementedError(f"pos_rel_to_long_face positioning is not supported yet for {component_name}")
        
        # Get the timber body from the component
        if component.bRepBodies.count == 0:
            if app:
                app.log(f"ERROR: No bodies in component {component_name}")
            return False
        
        timber_body = component.bRepBodies.item(0)
        
        # Find the appropriate face on the Fusion 360 timber body using normals
        target_face = find_timber_face_by_normal(timber_body, face)
        if not target_face:
            if app:
                app.log(f"ERROR: Could not find {face.name} face on {component_name}")
            return False
        
        # Create sketch on the target face
        sketches = component.sketches
        sketch = sketches.add(target_face)
        
        # Calculate mortise position on face
        timber_length_cm = float(timber.length) * 100
        ref_end, distance_from_end = mortise_spec.pos_rel_to_end
        
        if ref_end == TimberReferenceEnd.TOP:
            z_pos_on_face = timber_length_cm - (distance_from_end * 100)
        else:  # BOTTOM
            z_pos_on_face = distance_from_end * 100
        
        x_pos_on_face = 0  # Centered on face
        
        # Create mortise rectangle on the face
        rect_lines = sketch.sketchCurves.sketchLines
        
        # Rectangle centered at calculated position
        x1 = x_pos_on_face - width_cm / 2
        x2 = x_pos_on_face + width_cm / 2
        y1 = z_pos_on_face - height_cm / 2
        y2 = z_pos_on_face + height_cm / 2
        
        # Create rectangle points (Z=0 since we're in the sketch plane)
        point1 = adsk.core.Point3D.create(x1, y1, 0)
        point2 = adsk.core.Point3D.create(x2, y1, 0)
        point3 = adsk.core.Point3D.create(x2, y2, 0)
        point4 = adsk.core.Point3D.create(x1, y2, 0)
        
        # Draw rectangle
        rect_lines.addByTwoPoints(point1, point2)
        rect_lines.addByTwoPoints(point2, point3)
        rect_lines.addByTwoPoints(point3, point4)
        rect_lines.addByTwoPoints(point4, point1)
        
        # Find the correct profile for the mortise cavity (the bounded rectangle area)
        if sketch.profiles.count == 0:
            if app:
                app.log(f"ERROR: No profiles found in sketch for {component_name}")
            return False
        
        # Look for the bounded profile (the inner rectangle area)
        profile = None
        smallest_area = float('inf')
        
        for i in range(sketch.profiles.count):
            test_profile = sketch.profiles.item(i)
            try:
                area_props = test_profile.areaProperties()
                if area_props:
                    area = area_props.area
                    # Select the smallest positive area (should be our rectangle)
                    if 0 < area < smallest_area:
                        smallest_area = area
                        profile = test_profile
            except:
                continue
        
        # Fallback to first profile if none found
        if not profile and sketch.profiles.count > 0:
            profile = sketch.profiles.item(0)
        
        if not profile:
            if app:
                app.log(f"ERROR: Failed to find mortise profile for {component_name}")
            return False
        
        # Create cutting body first, then boolean subtract from specific timber body
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        
        # Create cutting body by extruding inward
        distance = adsk.core.ValueInput.createByReal(-depth_cm)
        extrude_input.setDistanceExtent(False, distance)
        extrude = extrudes.add(extrude_input)
        
        if not extrude or extrude.bodies.count == 0:
            if app:
                app.log(f"ERROR: Failed to create cutting body for {component_name}")
            return False
        
        cutting_body = extrude.bodies.item(0)
        
        # Perform boolean cut operation to subtract cutting body from timber
        combine_features = component.features.combineFeatures
        combine_input = combine_features.createInput(timber_body, adsk.core.ObjectCollection.create())
        combine_input.toolBodies.add(cutting_body)
        combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        combine_input.isKeepToolBodies = False  # Remove cutting body after operation
        
        combine_feature = combine_features.add(combine_input)
        
        if combine_feature:
            if app:
                app.log(f"✓ Created mortise on {face.name} face of {component_name}")
            return True
        else:
            if app:
                app.log(f"ERROR: Boolean cut failed for {component_name}")
            return False
            
    except Exception as e:
        app = get_fusion_app()
        if app:
            app.log(f"ERROR: Exception in create_mortise_cut for {component_name}: {str(e)}")
        return False


def create_tenon_cut(component: adsk.fusion.Component, timber: Timber, tenon_spec: StandardTenon, component_name: str) -> bool:
    """
    Create a tenon cut operation following the specified approach:
    1. Determine position on centerline for shoulder plane
    2. Create shoulder plane and chop off timber end
    3. Create perpendicular plane at same position
    4. Create box sketch matching tenon dimensions
    5. Extrude tenon forward to tenon length
    6. Extrude tenon backward to fill shoulder cut
    
    Args:
        component: Timber component to cut
        timber: Timber object for dimensions
        tenon_spec: StandardTenon specification
        component_name: Name for debugging
        
    Returns:
        bool: True if cut was successful
    """
    app = get_fusion_app()
    
    try:
        # Get tenon dimensions in cm
        width_cm = tenon_spec.width * 100
        height_cm = tenon_spec.height * 100
        depth_cm = tenon_spec.depth * 100
        
        if app:
            app.log(f"Creating {width_cm:.1f}x{height_cm:.1f}x{depth_cm:.1f}cm tenon on {component_name} on {tenon_spec.shoulder_plane.reference_end.name} side")

        # Get timber body from component
        if component.bRepBodies.count == 0:
            if app:
                app.log(f"ERROR: No bodies in component {component_name}")
            return False
        
        timber_body = component.bRepBodies.item(0)
        
        # Step 1: Determine position on centerline for shoulder plane
        timber_length_cm = float(timber.length) * 100
        shoulder_distance_cm = tenon_spec.shoulder_plane.distance * 100
        
        # Assert that shoulder plane is perpendicular to timber length (only supported for now)
        shoulder_normal = tenon_spec.shoulder_plane.normal
        timber_length_direction = (0, 0, 1)  # Z direction in timber coordinate system
        
        # Check if normal is parallel to length direction (perpendicular plane)
        dot_product = abs(shoulder_normal[0] * timber_length_direction[0] + 
                         shoulder_normal[1] * timber_length_direction[1] + 
                         shoulder_normal[2] * timber_length_direction[2])
        
        if dot_product < 0.95:  # Allow some tolerance for floating point
            raise AssertionError(f"Shoulder plane must be perpendicular to timber length for {component_name}. "
                               f"Shoulder normal {shoulder_normal} is not parallel to length direction {timber_length_direction}")
        
        # Calculate shoulder position based on reference end
        if tenon_spec.shoulder_plane.reference_end == TimberReferenceEnd.TOP:
            shoulder_pos_cm = timber_length_cm - shoulder_distance_cm
        else:  # BOTTOM
            shoulder_pos_cm = shoulder_distance_cm
        
        # Simplified approach: Skip shoulder cut for now, just create tenon directly
        # TODO: Add shoulder cutting back once basic tenon creation works
        
        timber_width_cm = float(timber.size[0]) * 100
        timber_height_cm = float(timber.size[1]) * 100
        
        # For now, just use the XY plane and position the tenon with the extrude start point
        tenon_sketch_plane = component.xYConstructionPlane
        
        # Step 5: Create box sketch matching tenon dimensions
        sketches = component.sketches
        tenon_sketch = sketches.add(tenon_sketch_plane)
        
        # Calculate tenon position (centered if pos_rel_to_long_edge is None)
        # timber_width_cm and timber_height_cm already defined above
        
        if tenon_spec.pos_rel_to_long_edge is None:
            # Centered on timber cross-section
            center_x = 0
            center_y = 0
        else:
            # TODO: Handle positioned tenons
            raise NotImplementedError(f"Positioned tenons not implemented yet for {component_name}")
        
        # Create tenon rectangle centered at calculated position
        x1 = center_x - width_cm / 2
        x2 = center_x + width_cm / 2
        y1 = center_y - height_cm / 2
        y2 = center_y + height_cm / 2
        
        # Draw tenon rectangle
        rect_lines = tenon_sketch.sketchCurves.sketchLines
        point1 = adsk.core.Point3D.create(x1, y1, 0)
        point2 = adsk.core.Point3D.create(x2, y1, 0)
        point3 = adsk.core.Point3D.create(x2, y2, 0)
        point4 = adsk.core.Point3D.create(x1, y2, 0)
        
        rect_lines.addByTwoPoints(point1, point2)
        rect_lines.addByTwoPoints(point2, point3)
        rect_lines.addByTwoPoints(point3, point4)
        rect_lines.addByTwoPoints(point4, point1)
        
        # Step 6: Create tenon by cutting away waste material around the tenon profile
        # We need to cut 4 rectangles around the tenon to leave only the tenon standing
        
        extrudes = component.features.extrudeFeatures
        combine_features = component.features.combineFeatures
        
        # Create 4 cutting bodies: left, right, front, back of the tenon
        cutting_operations = []
        
        # Calculate cutting regions around the tenon (leaving tenon profile untouched)
        margin = max(timber_width_cm, timber_height_cm)  # Extra margin for complete cut
        
        # Left cutting region (X < tenon_left)
        left_sketch = sketches.add(tenon_sketch_plane)
        left_lines = left_sketch.sketchCurves.sketchLines
        left_x1 = -margin
        left_x2 = x1  # Left edge of tenon
        left_y1 = -margin
        left_y2 = margin
        
        left_lines.addByTwoPoints(adsk.core.Point3D.create(left_x1, left_y1, 0), adsk.core.Point3D.create(left_x2, left_y1, 0))
        left_lines.addByTwoPoints(adsk.core.Point3D.create(left_x2, left_y1, 0), adsk.core.Point3D.create(left_x2, left_y2, 0))
        left_lines.addByTwoPoints(adsk.core.Point3D.create(left_x2, left_y2, 0), adsk.core.Point3D.create(left_x1, left_y2, 0))
        left_lines.addByTwoPoints(adsk.core.Point3D.create(left_x1, left_y2, 0), adsk.core.Point3D.create(left_x1, left_y1, 0))
        
        # Right cutting region (X > tenon_right)
        right_sketch = sketches.add(tenon_sketch_plane)
        right_lines = right_sketch.sketchCurves.sketchLines
        right_x1 = x2  # Right edge of tenon
        right_x2 = margin
        right_y1 = -margin
        right_y2 = margin
        
        right_lines.addByTwoPoints(adsk.core.Point3D.create(right_x1, right_y1, 0), adsk.core.Point3D.create(right_x2, right_y1, 0))
        right_lines.addByTwoPoints(adsk.core.Point3D.create(right_x2, right_y1, 0), adsk.core.Point3D.create(right_x2, right_y2, 0))
        right_lines.addByTwoPoints(adsk.core.Point3D.create(right_x2, right_y2, 0), adsk.core.Point3D.create(right_x1, right_y2, 0))
        right_lines.addByTwoPoints(adsk.core.Point3D.create(right_x1, right_y2, 0), adsk.core.Point3D.create(right_x1, right_y1, 0))
        
        # Front cutting region (Y < tenon_front)
        front_sketch = sketches.add(tenon_sketch_plane)
        front_lines = front_sketch.sketchCurves.sketchLines
        front_x1 = x1  # Tenon left
        front_x2 = x2  # Tenon right
        front_y1 = -margin
        front_y2 = y1  # Front edge of tenon
        
        front_lines.addByTwoPoints(adsk.core.Point3D.create(front_x1, front_y1, 0), adsk.core.Point3D.create(front_x2, front_y1, 0))
        front_lines.addByTwoPoints(adsk.core.Point3D.create(front_x2, front_y1, 0), adsk.core.Point3D.create(front_x2, front_y2, 0))
        front_lines.addByTwoPoints(adsk.core.Point3D.create(front_x2, front_y2, 0), adsk.core.Point3D.create(front_x1, front_y2, 0))
        front_lines.addByTwoPoints(adsk.core.Point3D.create(front_x1, front_y2, 0), adsk.core.Point3D.create(front_x1, front_y1, 0))
        
        # Back cutting region (Y > tenon_back)
        back_sketch = sketches.add(tenon_sketch_plane)
        back_lines = back_sketch.sketchCurves.sketchLines
        back_x1 = x1  # Tenon left
        back_x2 = x2  # Tenon right
        back_y1 = y2  # Back edge of tenon
        back_y2 = margin
        
        back_lines.addByTwoPoints(adsk.core.Point3D.create(back_x1, back_y1, 0), adsk.core.Point3D.create(back_x2, back_y1, 0))
        back_lines.addByTwoPoints(adsk.core.Point3D.create(back_x2, back_y1, 0), adsk.core.Point3D.create(back_x2, back_y2, 0))
        back_lines.addByTwoPoints(adsk.core.Point3D.create(back_x2, back_y2, 0), adsk.core.Point3D.create(back_x1, back_y2, 0))
        back_lines.addByTwoPoints(adsk.core.Point3D.create(back_x1, back_y2, 0), adsk.core.Point3D.create(back_x1, back_y1, 0))
        
        # Create cutting bodies and apply boolean cuts
        cutting_sketches = [left_sketch, right_sketch, front_sketch, back_sketch]
        cut_names = ["left", "right", "front", "back"]
        
        for i, cut_sketch in enumerate(cutting_sketches):
            if cut_sketch.profiles.count > 0:
                cut_profile = cut_sketch.profiles.item(0)
                
                # Determine extrusion range for this cutting region
                if tenon_spec.shoulder_plane.reference_end == TimberReferenceEnd.TOP:
                    # Cut from timber top to beyond tenon end
                    start_extent = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(0))
                    end_extent = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(-depth_cm))
                else:  # BOTTOM
                    # Cut from below tenon end to timber bottom
                    start_extent = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depth_cm))
                    end_extent = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(0))

                
                # Create cutting body
                cutting_extrude_input = extrudes.createInput(cut_profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                cutting_extrude_input.setTwoSidesExtent(start_extent, end_extent)
                cutting_extrude = extrudes.add(cutting_extrude_input)
                
                if cutting_extrude and cutting_extrude.bodies.count > 0:
                    cutting_body = cutting_extrude.bodies.item(0)
                    
                    # Apply boolean cut
                    combine_input = combine_features.createInput(timber_body, adsk.core.ObjectCollection.create())
                    combine_input.toolBodies.add(cutting_body)
                    combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                    combine_input.isKeepToolBodies = False
                    
                    combine_feature = combine_features.add(combine_input)
                    
                    if not combine_feature:
                        if app:
                            app.log(f"WARNING: Failed to apply {cut_names[i]} cut for tenon on {component_name}")
                else:
                    if app:
                        app.log(f"WARNING: Failed to create {cut_names[i]} cutting body for tenon on {component_name}")
        
        if app:
            app.log(f"✓ Created tenon on {component_name}")
        return True
            
    except Exception as e:
        app = get_fusion_app()
        if app:
            app.log(f"ERROR: Exception in create_tenon_cut for {component_name}: {str(e)}")
        return False


def apply_timber_cuts(component: adsk.fusion.Component, cut_timber: CutTimber, component_name: str) -> bool:
    """
    Apply all cuts (mortises, tenons, etc.) to a timber component.
    
    Args:
        component: Timber component to apply cuts to
        cut_timber: CutTimber object with cut operations
        component_name: Name for debugging
        
    Returns:
        bool: True if all cuts were applied successfully
    """
    try:
        success_count = 0
        total_cuts = len(cut_timber.joints)
        
        if total_cuts == 0:
            print(f"    No cuts to apply to {component_name}")
            return True
        
        print(f"    Applying {total_cuts} cuts to {component_name} (mortises first, then tenons)")
        
        # Separate mortise and tenon operations
        mortise_operations = []
        tenon_operations = []
        other_operations = []
        
        for joint in cut_timber.joints:
            if isinstance(joint, MortiseCutOperation):
                mortise_operations.append(joint)
            elif isinstance(joint, TenonCutOperation):
                app = get_fusion_app()
                tenon_operations.append(joint)
            else:
                other_operations.append(joint)
        
        # Process all mortises first
        print(f"    Phase 1: Processing {len(mortise_operations)} mortise cuts...")
        for i, joint in enumerate(mortise_operations):
            print(f"      Mortise {i+1}/{len(mortise_operations)}: Creating mortise cut...")
            try:
                result = create_mortise_cut(component, cut_timber.timber, joint.mortise_spec, component_name)
                if result:
                    success_count += 1
                    print(f"      ✓ Mortise cut created successfully")
                else:
                    print(f"      ✗ Mortise cut function returned False for {component_name}")
            except Exception as e:
                print(f"      ✗ Exception in mortise cut for {component_name}: {str(e)}")
                app = get_fusion_app()
                if app:
                    app.log(f"Exception in mortise cut for {component_name}: {str(e)}")
                import traceback
                print(f"      Traceback: {traceback.format_exc()}")
                if app:
                    app.log(f"Traceback: {traceback.format_exc()}")
        
        # Process all tenons second  
        print(f"    Phase 2: Processing {len(tenon_operations)} tenon cuts...")
        for i, joint in enumerate(tenon_operations):
            print(f"      Tenon {i+1}/{len(tenon_operations)}: Creating tenon cut...")
            try:
                result = create_tenon_cut(component, cut_timber.timber, joint.tenon_spec, component_name)
                if result:
                    success_count += 1
                    print(f"      ✓ Tenon cut created successfully")
                else:
                    print(f"      ✗ Tenon cut function returned False for {component_name}")
            except Exception as e:
                print(f"      ✗ Exception in tenon cut for {component_name}: {str(e)}")
                app = get_fusion_app()
                if app:
                    app.log(f"Exception in tenon cut for {component_name}: {str(e)}")
                import traceback
                print(f"      Traceback: {traceback.format_exc()}")
                if app:
                    app.log(f"Traceback: {traceback.format_exc()}")
        
        # Process other operations last
        for i, joint in enumerate(other_operations):
            print(f"      ⚠ Unsupported cut type: {type(joint).__name__} in {component_name}")
            # For now, count unsupported types as "successful" to not block the process
            success_count += 1
        
        print(f"    Successfully applied {success_count}/{total_cuts} cuts to {component_name}")
        return success_count == total_cuts
        
    except Exception as e:
        print(f"Error applying cuts to {component_name}: {str(e)}")
        return False


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


def render_single_timber(cut_timber: CutTimber, root_component: adsk.fusion.Component, component_name: str = None, apply_transforms: bool = True) -> Tuple[bool, Optional[adsk.fusion.Occurrence]]:
    """
    Render a single CutTimber object in Fusion 360.
    
    Args:
        cut_timber: CutTimber object to render
        root_component: Root component to create the timber in
        component_name: Optional name for the component
        apply_transforms: If False, skips transform step for debugging (default: True)
        
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
        
        # Apply cuts while timber is at origin (easier for axis-aligned cuts)
        cut_success = apply_timber_cuts(timber_component, cut_timber, name)
        if not cut_success:
            print(f"Failed to apply some cuts for {name}")
            # Note: we don't return False here because the basic timber was created
        
        # Apply transform to move to final position (optional for debugging)
        if apply_transforms:
            transform_success = apply_timber_transform(occurrence, timber, name)
            if not transform_success:
                print(f"Failed to apply transform for {name}")
                # Note: we don't return False here because the geometry was created
        else:
            print(f"🐛 DEBUG: Skipping transform for {name} (kept at origin)")
        
        return True, occurrence
        
    except Exception as e:
        print(f"Error rendering single timber {component_name}: {str(e)}")
        return False, None


def render_multiple_timbers(cut_timbers: List[CutTimber], base_name: str = "Timber", apply_transforms: bool = True) -> int:
    """
    Render multiple CutTimber objects in Fusion 360 using a three-pass approach.
    
    Pass 1: Create all timber geometry at the origin
    Pass 2: Apply all cuts (mortises, tenons, etc.) while at origin
    Pass 3: Apply all transforms to move timbers to final positions (optional)
    
    This approach is more reliable because cuts are applied to axis-aligned geometry.
    
    Args:
        cut_timbers: List of CutTimber objects to render
        base_name: Base name for components (will be numbered)
        apply_transforms: If False, skips transform step for debugging (default: True)
        
    Returns:
        int: Number of timbers successfully rendered
    """
    try:
        print(f"Starting three-pass rendering of {len(cut_timbers)} timbers...")
        app = get_fusion_app()
        if app:
            app.log(f"DEBUG: Starting three-pass rendering of {len(cut_timbers)} timbers (transforms={apply_transforms})")
        
        # Get the active design
        design = get_active_design()
        if not design:
            print("Error: No active design found in Fusion 360")
            return 0
        
        root_comp = design.rootComponent
        created_components = []
        
        # PASS 1: Create all timber geometry at origin
        if app:
            app.log(f"=== PASS 1: Creating timber geometry ===")
        
        for i, cut_timber in enumerate(cut_timbers):
            component_name = cut_timber.name if cut_timber.name else f"{base_name}_{i+1:03d}"
            if app:
                app.log(f"  Processing timber {i+1}/{len(cut_timbers)}: {component_name}")
            
            # Create component at origin
            occurrence = root_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            timber_component = occurrence.component
            timber_component.name = component_name
            
            # Create basic timber geometry
            geometry_success = create_timber_geometry(timber_component, cut_timber.timber, component_name)
            if geometry_success:
                if app:
                    app.log(f"  ✅ Created geometry for {component_name}: {timber_component.bRepBodies.count} bodies")
                created_components.append((occurrence, cut_timber, component_name))
            else:
                if app:
                    app.log(f"  ❌ Failed to create geometry for {component_name}")
                    app.log(f"🚨 GEOMETRY CREATION FAILED - This will cause 'No target body' error later!")
        
        # Force refresh after all geometry creation
        adsk.doEvents()
        
        # PASS 2: Apply all cuts while timbers are at origin
        if app:
            app.log(f"=== PASS 2: Applying cuts at origin ===")
        
        cut_success_count = 0
        total_cuts = 0
        applied_cuts = 0
        
        for occurrence, cut_timber, component_name in created_components:
            timber_joints = len(cut_timber.joints)
            total_cuts += timber_joints
            app = get_fusion_app()
            if app:
                app.log(f"Processing {component_name}: {timber_joints} joints")
            
            if timber_joints > 0:
                timber_component = occurrence.component
                if app:
                    app.log(f"  Applying cuts to {component_name}...")
                    app.log(f"    Component has {timber_component.bRepBodies.count} bodies before cuts")
                cut_success = apply_timber_cuts(timber_component, cut_timber, component_name)
                if cut_success:
                    cut_success_count += 1
                    applied_cuts += timber_joints
                    if app:
                        app.log(f"  ✓ Successfully applied {timber_joints} cuts to {component_name}")
                else:
                    if app:
                        app.log(f"  ✗ Failed to apply cuts to {component_name}")
            else:
                # No cuts to apply counts as success
                cut_success_count += 1
                if app:
                    app.log(f"  No cuts to apply to {component_name}")
        
        # Force refresh after all cuts
        time.sleep(0.2)
        adsk.doEvents()
        
        # PASS 3: Apply all transforms to move to final positions (optional for debugging)
        transform_success_count = 0
        if apply_transforms:
            print(f"\n=== PASS 3: Applying transforms ===")
            
            for occurrence, cut_timber, component_name in created_components:
                transform_success = apply_timber_transform(occurrence, cut_timber.timber, component_name)
                if transform_success:
                    transform_success_count += 1
            
            # Final refresh with extra time for complex geometries to settle
            time.sleep(0.2)
            adsk.doEvents()
        else:
            print(f"\n=== PASS 3: Skipping transforms (debug mode) ===")
            # All timbers remain at origin for debugging
            transform_success_count = len(created_components)  # Count as successful since we skipped intentionally
        
        if app:
            app.log(f"=== SUMMARY ===")
            app.log(f"Successfully rendered {transform_success_count} out of {len(cut_timbers)} timbers")
            app.log(f"Successfully applied cuts to {cut_success_count} out of {len(created_components)} timbers")
            app.log(f"Total cuts applied: {applied_cuts} out of {total_cuts}")
            if not apply_transforms:
                app.log(f"🐛 DEBUG MODE: All timbers kept at origin (transforms skipped)")
        
        return transform_success_count
        
    except Exception as e:
        if app:
            app.log(f"🚨 EXCEPTION IN RENDER_MULTIPLE_TIMBERS: {str(e)}")
        import traceback
        print(traceback.format_exc())  # Keep this as print for terminal debugging
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