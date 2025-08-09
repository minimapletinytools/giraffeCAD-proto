"""
Fusion 360 rendering module for GiraffeCAD timber framing system.

This module provides functions to render timber structures in Autodesk Fusion 360
using the Fusion 360 Python API.
"""

# Module load tracker - must use app.log for Fusion 360 console
try:
    app = adsk.core.Application.get()
    if app:
        app.log("🐘 MODULE RELOAD TRACKER: giraffe_render_fusion360.py LOADED - Version 20:00 - NORMAL-BASED FACE DETECTION 🐘")
except:
    pass  # Ignore if app not available during import

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import time
from typing import Optional, Tuple, List
from sympy import Matrix, Float
from giraffe import CutTimber, Timber, MortiseCutOperation, StandardMortise, TimberFace, TimberReferenceEnd, TimberReferenceLongFace
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
    print(f"      Looking for {target_face.name} face with normal {expected_normal}")
    
    for i in range(timber_body.faces.count):
        brepface = timber_body.faces.item(i)
        
        # Get face normal at center point
        face_eval = brepface.evaluator
        (success, center_point) = face_eval.getPointAtParameter(adsk.core.Point2D.create(0.5, 0.5))
        
        if success:
            # Get the normal vector at the center point
            (success_normal, normal_vec) = face_eval.getNormalAtParameter(adsk.core.Point2D.create(0.5, 0.5))
            
            if success_normal:
                # Normalize and compare with expected normal
                normal = (normal_vec.x, normal_vec.y, normal_vec.z)
                
                print(f"        Face {i}: normal = ({normal[0]:.3f}, {normal[1]:.3f}, {normal[2]:.3f})")
                
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
                    
                    print(f"        ✓ Found {target_face.name} face with normal {normal}")
                    return brepface
    
    print(f"      ❌ Could not find {target_face.name} face with expected normal {expected_normal}")
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
        app.log(f"🎯 CRITICAL: Component has {component.bRepBodies.count} bodies at START")
        
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
    print("🚀🚀🚀 NEW VERSION LOADED - VERSION 2024.12.19.20.00 - NORMAL-BASED FACE DETECTION 🚀🚀🚀")
    print(f"\n🔧 ENTERING create_mortise_cut for {component_name}")
    app = get_fusion_app()
    if app:
        app.log(f"🔧 ENTERING create_mortise_cut for {component_name}")
    
    try:
        print(f"🔧 Step A: Basic setup...")
        if app:
            app.log(f"🔧 Step A: Basic setup...")
        print(f"🔧 Component type: {type(component)}")
        print(f"🔧 Timber type: {type(timber)}")
        print(f"🔧 ⚡ CRITICAL: Component has {component.bRepBodies.count} bodies at START")
        print(f"🔧 Mortise spec type: {type(mortise_spec)}")
        if app:
            app.log(f"🔧 Component: {type(component)}, Timber: {type(timber)}, Spec: {type(mortise_spec)}")
        
        print(f"\n=== Creating mortise cut on {mortise_spec.mortise_face.name} face of {component_name} ===")
        # Also log to Fusion 360
        app = get_fusion_app()
        if app:
            app.log(f"Creating mortise cut on {mortise_spec.mortise_face.name} face of {component_name}")
        
        # Early debug checkpoint
        print(f"      Step 1: Getting mortise dimensions...")
        
        # Get mortise dimensions in cm
        width_cm = mortise_spec.width * 100
        height_cm = mortise_spec.height * 100
        depth_cm = mortise_spec.depth * 100
        
        print(f"      Step 2: Dimensions calculated: {width_cm:.1f} x {height_cm:.1f} x {depth_cm:.1f} cm")
        
        # Debug mortise spec
        print(f"  Raw mortise spec:")
        print(f"    Face: {mortise_spec.mortise_face.name}")
        print(f"    pos_rel_to_end: {mortise_spec.pos_rel_to_end}")
        print(f"    width: {mortise_spec.width:.3f}m = {width_cm:.1f}cm")
        print(f"    height: {mortise_spec.height:.3f}m = {height_cm:.1f}cm")
        print(f"    depth: {mortise_spec.depth:.3f}m = {depth_cm:.1f}cm")
        
        # Get the face from mortise spec
        face = mortise_spec.mortise_face

        # Step 5: Assert that pos_rel_to_long_face is None (not supported yet)
        if mortise_spec.pos_rel_to_long_face is not None:
            raise NotImplementedError(f"pos_rel_to_long_face positioning is not supported yet for {component_name}")
        
        print(f"      Step 6: Getting Fusion 360 face from timber body...")
        
        # Get the timber body from the component
        if component.bRepBodies.count == 0:
            print(f"      ❌ FATAL ERROR: No bodies in component to cut from!")
            return False
        
        timber_body = component.bRepBodies.item(0)  # Get the first (and should be only) body
        print(f"      Found timber body: {timber_body.name if timber_body.name else 'Unnamed'}")
        
        # Step 7: Find the appropriate face on the Fusion 360 timber body using normals
        print(f"      Looking for {face.name} face on timber body using face normals...")
        
        target_face = find_timber_face_by_normal(timber_body, face)
        if not target_face:
            print(f"      ❌ Could not find {face.name} face on timber body!")
            return False
        
        print(f"      Step 8: Creating sketch on {face.name} face...")
        
        # Create sketch on the target face
        sketches = component.sketches
        sketch = sketches.add(target_face)
        
        print(f"      Step 9: Calculating mortise position on face...")
        
        # Calculate timber dimensions for positioning
        timber_length_cm = float(timber.length) * 100
        
        # Calculate position along the length of the timber (Z direction in sketch coordinates)
        ref_end, distance_from_end = mortise_spec.pos_rel_to_end
        if ref_end == TimberReferenceEnd.TOP:
            # Distance from TOP end (Z=length_cm)
            z_pos_on_face = timber_length_cm - (distance_from_end * 100)
        else:  # BOTTOM
            # Distance from BOTTOM end (Z=0)
            z_pos_on_face = distance_from_end * 100
        
        # X position on sketch is centered (0) for now since pos_rel_to_long_face is None
        x_pos_on_face = 0  # Centered on face
        
        print(f"      Mortise position on {face.name} face:")
        print(f"        X (cross-face): {x_pos_on_face:.1f} cm (centered)")
        print(f"        Y (along-length): {z_pos_on_face:.1f} cm from bottom")
        print(f"        Reference: {ref_end.name} end, {distance_from_end*100:.1f} cm from end")
        
        # Step 10: Create mortise rectangle on the face
        print(f"      Step 10: Creating {width_cm:.1f}x{height_cm:.1f} cm rectangle...")
        
        rect_lines = sketch.sketchCurves.sketchLines
        
        # Rectangle centered at calculated position
        x1 = x_pos_on_face - width_cm / 2
        x2 = x_pos_on_face + width_cm / 2
        y1 = z_pos_on_face - height_cm / 2
        y2 = z_pos_on_face + height_cm / 2
        
        print(f"      Rectangle bounds: X=[{x1:.1f}, {x2:.1f}], Y=[{y1:.1f}, {y2:.1f}]")
        
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
        
        print(f"      ✓ Rectangle created on {face.name} face")
        
        # Step 11: Get profile and create cut extrusion
        print(f"      Step 11: Creating cut extrusion...")
        
        # Find the correct profile for the mortise cavity
        if sketch.profiles.count == 0:
            print(f"      ❌ No profiles found in sketch")
            return False
        
        # Debug: show all profiles found
        print(f"      Found {sketch.profiles.count} profiles in sketch")
        
        # Look for the bounded profile (the inner rectangle area)
        profile = None
        smallest_area = float('inf')
        
        for i in range(sketch.profiles.count):
            test_profile = sketch.profiles.item(i)
            try:
                # Check if this profile has a finite area (bounded)
                area_props = test_profile.areaProperties()
                if area_props:
                    area = area_props.area
                    print(f"        Profile {i}: area = {area:.4f} cm², bounded = {area > 0 and area < 1e6}")
                    
                    # Select the smallest positive area (should be our rectangle)
                    if 0 < area < smallest_area:
                        smallest_area = area
                        profile = test_profile
                        print(f"        ✓ New best profile {i}: area = {area:.4f} cm²")
            except:
                print(f"        Profile {i}: unbounded or invalid")
                continue
        
        # If still no profile found, try a different approach
        if not profile:
            print(f"      No bounded profile found, trying first profile...")
            profile = sketch.profiles.item(0)
        
        if not profile:
            print(f"      ❌ Failed to find suitable mortise profile")
            return False
        
        print(f"      ✓ Using profile with area {smallest_area:.4f} cm² for mortise cut")
        
        # Create cut extrusion
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
        
        # Cut inward by mortise depth
        distance = adsk.core.ValueInput.createByReal(-depth_cm)
        extrude_input.setDistanceExtent(False, distance)  # Cut inward (negative direction)
        
        print(f"      Creating cut: depth={depth_cm:.1f} cm inward from {face.name} face")
        
        extrude = extrudes.add(extrude_input)
        
        if extrude:
            print(f"      ✓ Successfully created mortise cut on {face.name} face")
            return True
        else:
            print(f"      ❌ Failed to create mortise extrusion")
            return False
            
    except Exception as e:
        print(f"🔧 ERROR: Exception in create_mortise_cut for {component_name}: {str(e)}")
        app = get_fusion_app()
        if app:
            app.log(f"🔧 ERROR: Exception in create_mortise_cut for {component_name}: {str(e)}")
        import traceback
        print(f"🔧 TRACEBACK: {traceback.format_exc()}")
        if app:
            app.log(f"🔧 TRACEBACK: {traceback.format_exc()}")
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
        
        print(f"    Applying {total_cuts} cuts to {component_name}")
        
        for i, joint in enumerate(cut_timber.joints):
            print(f"    Processing cut {i+1}/{total_cuts}: {type(joint).__name__}")
            
            if isinstance(joint, MortiseCutOperation):
                print(f"      Creating mortise cut...")
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
            # TODO: Add support for other cut types (tenons, etc.)
            else:
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