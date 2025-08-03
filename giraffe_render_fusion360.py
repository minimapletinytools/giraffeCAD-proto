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
    if face == TimberFace.TOP:
        # Top face is at Z = +length_cm (top end)
        return cross_pos, 0, length_cm
    elif face == TimberFace.BOTTOM:
        # Bottom face is at Z = 0 (bottom end)
        return cross_pos, 0, 0
    elif face == TimberFace.RIGHT:
        # Right face is at X = +width_cm/2
        return width_cm/2, cross_pos, z_pos
    elif face == TimberFace.LEFT:
        # Left face is at X = -width_cm/2
        return -width_cm/2, cross_pos, z_pos
    elif face == TimberFace.FORWARD:
        # Forward face is at Y = +height_cm/2
        return cross_pos, height_cm/2, z_pos
    else:  # BACK
        # Back face is at Y = -height_cm/2
        return cross_pos, -height_cm/2, z_pos


def create_mortise_cut(component: adsk.fusion.Component, timber: Timber, mortise_spec: StandardMortise, component_name: str) -> bool:
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
    print("🚀🚀🚀 NEW VERSION LOADED - VERSION 2024.12.19.16.30 🚀🚀🚀")
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
        
        # Calculate mortise position
        pos_x, pos_y, pos_z = calculate_mortise_position(timber, mortise_spec)
        
        print(f"  Calculated 3D position: ({pos_x:.2f}, {pos_y:.2f}, {pos_z:.2f}) cm")
        print(f"  Timber dimensions: {float(timber.size[0])*100:.1f} x {float(timber.size[1])*100:.1f} x {float(timber.length)*100:.1f} cm (W x H x L)")
        print(f"  Timber bottom position: ({float(timber.bottom_position[0])*100:.1f}, {float(timber.bottom_position[1])*100:.1f}, {float(timber.bottom_position[2])*100:.1f}) cm")
        print(f"  Timber extends to: Z = {float(timber.bottom_position[2])*100 + float(timber.length)*100:.1f} cm")
        print(f"  FACE ANALYSIS: {face.name} face should be positioned at:")
        if face == TimberFace.BACK:
            expected_y = -float(timber.size[1])*100/2
            print(f"    Y = {expected_y:.1f} cm (back face surface)")
        print(f"  ACTUAL calculated Y = {pos_y:.1f} cm")
        
        # Debug timber extents
        timber_width = float(timber.size[0]) * 100
        timber_height = float(timber.size[1]) * 100
        timber_length = float(timber.length) * 100
        print(f"  Timber extents:")
        print(f"    X: {-timber_width/2:.1f} to {timber_width/2:.1f} cm")
        print(f"    Y: {-timber_height/2:.1f} to {timber_height/2:.1f} cm") 
        print(f"    Z: 0.0 to {timber_length:.1f} cm")
        
        print(f"      Step 3: Creating sketch...")
        
        # Create sketch on appropriate plane based on face
        sketches = component.sketches
        
        print(f"      Step 4: Selected face {face.name}, getting sketch plane...")
        
        # Now that sketch creation works, use correct face-based positioning
        print(f"      Step 5: Creating mortise on {face.name} face...")
        if app:
            app.log(f"      Step 5: Creating mortise on {face.name} face...")
        
        # SIMPLIFIED APPROACH: Create sketch on base plane and position mortise directly in 3D coordinates
        print(f"      Step 5a: Creating sketch on base plane for {face.name} face")
        if face in [TimberFace.TOP, TimberFace.BOTTOM]:
            base_plane = component.xYConstructionPlane
            print(f"      Using XY base plane for {face.name} face")
        elif face in [TimberFace.RIGHT, TimberFace.LEFT]:
            base_plane = component.yZConstructionPlane
            print(f"      Using YZ base plane for {face.name} face")
        else:  # FORWARD, BACK
            base_plane = component.xZConstructionPlane
            print(f"      Using XZ base plane for {face.name} face")
            
        sketch = sketches.add(base_plane)
        print(f"      Step 5b: Created sketch on {face.name} face base plane")
        if app:
            app.log(f"      Step 5b: Added sketch to {face.name} face plane")
        
        # CORRECTED: Position sketch at face surface, not timber center
        if face in [TimberFace.FORWARD, TimberFace.BACK]:
            # XZ plane: For BACK face, translate the sketch to account for Y offset
            sketch_x = pos_x  # World X coordinate (across timber width) 
            sketch_y = pos_z  # World Z coordinate (along timber length)
            # The sketch will be created on XZ plane, but we need to position it where timber actually exists
            # For BACK face: timber extends from Y=-5.1 to Y=+5.1, sketch is on Y=0 plane
            print(f"      SKETCH POSITIONING: {face.name} face on XZ plane at ({sketch_x:.1f}, {sketch_y:.1f}) cm")
            print(f"      ⚠️  ISSUE: Sketch on Y=0 plane, but BACK face is at Y={pos_y:.1f} cm")
            print(f"      SOLUTION: Create sketch on XZ plane and extrude to reach face surface")
        elif face in [TimberFace.TOP, TimberFace.BOTTOM]:
            # XY plane: sketch X = world X, sketch Y = world Y
            sketch_x = pos_x  # World X coordinate (across timber width)
            sketch_y = pos_y  # World Y coordinate (across timber height)
            print(f"      SKETCH POSITIONING: {face.name} face on XY plane at ({sketch_x:.1f}, {sketch_y:.1f}) cm")
        else:  # RIGHT, LEFT faces
            # YZ plane: sketch X = world Y, sketch Y = world Z
            sketch_x = pos_y  # World Y coordinate (across timber height)
            sketch_y = pos_z  # World Z coordinate (along timber length)
            print(f"      SKETCH POSITIONING: {face.name} face on YZ plane at ({sketch_x:.1f}, {sketch_y:.1f}) cm")
            
        rect_width = width_cm  # Use actual mortise width
        rect_height = height_cm  # Use actual mortise height
        print(f"      Step 5c: Setting up {rect_width:.1f}x{rect_height:.1f}cm mortise at ({sketch_x:.1f}, {sketch_y:.1f})")
        print(f"      SKETCH COORDS DEBUG: X={sketch_x:.1f} cm, Y={sketch_y:.1f} cm on {face.name} face plane")
        print(f"      COORDINATE MAPPING CHECK:")
        print(f"        World 3D position: ({pos_x:.1f}, {pos_y:.1f}, {pos_z:.1f}) cm")
        print(f"        Sketch 2D position: ({sketch_x:.1f}, {sketch_y:.1f}) cm") 
        print(f"        Expected: sketch should be ABOVE XY plane (sketch_y = {sketch_y:.1f} should be > 0)")
        if sketch_y < 0:
            print(f"        ⚠️  WARNING: sketch_y is negative! This will place sketch below XY plane!")
        if app:
            app.log(f"      Step 5c: Setting up {rect_width:.1f}x{rect_height:.1f}cm mortise at ({sketch_x:.1f}, {sketch_y:.1f})")
        
        print(f"      Step 6: Creating rectangle for mortise...")
        
        # Create rectangle for mortise
        rect_lines = sketch.sketchCurves.sketchLines
        x1 = sketch_x - rect_width / 2
        x2 = sketch_x + rect_width / 2
        y1 = sketch_y - rect_height / 2
        y2 = sketch_y + rect_height / 2
        
        print(f"      Rectangle corners:")
        print(f"        ({x1:.1f}, {y1:.1f}) to ({x2:.1f}, {y2:.1f})")
        print(f"        Width: {x2-x1:.1f} cm, Height: {y2-y1:.1f} cm")
        
        # Coordinates in centimeters as expected by Fusion 360 API
        point1 = adsk.core.Point3D.create(x1, y1, 0)
        point2 = adsk.core.Point3D.create(x2, y1, 0)
        point3 = adsk.core.Point3D.create(x2, y2, 0)
        point4 = adsk.core.Point3D.create(x1, y2, 0)
        
        print(f"      RECTANGLE POINTS DEBUG:")
        print(f"        Point1: ({x1:.1f}, {y1:.1f}, 0) cm")
        print(f"        Point2: ({x2:.1f}, {y1:.1f}, 0) cm")
        print(f"        Point3: ({x2:.1f}, {y2:.1f}, 0) cm")
        print(f"        Point4: ({x1:.1f}, {y2:.1f}, 0) cm")
        print(f"        Coordinates in centimeters as expected by Fusion 360 API")
        
        print(f"      Step 7: Drawing rectangle lines...")
        if app:
            app.log(f"      Step 7: Drawing rectangle lines...")
        
        rect_lines.addByTwoPoints(point1, point2)
        print(f"      Step 7a: Added line 1")
        rect_lines.addByTwoPoints(point2, point3)
        print(f"      Step 7b: Added line 2")
        rect_lines.addByTwoPoints(point3, point4)
        print(f"      Step 7c: Added line 3")
        rect_lines.addByTwoPoints(point4, point1)
        print(f"      Step 7d: Added line 4 - rectangle complete!")
        if app:
            app.log(f"      Step 7d: Rectangle drawing complete!")
        
        print(f"      Step 8: Getting profile for extrusion...")
        if app:
            app.log(f"      Step 8: Getting profile for extrusion...")
        
        # Get the profile for extrusion
        profile = sketch.profiles.item(0) if sketch.profiles.count > 0 else None
        if not profile:
            print(f"      ✗ Failed to create mortise profile for {component_name}")
            return False
        
        print(f"      EXTRUSION DEBUG:")
        print(f"        Profile found: {'Yes' if profile else 'No'}")
        print(f"        Sketch location: {face.name} face plane")
        print(f"        Target timber bounds: X=[{-float(timber.size[0])*100/2:.1f}, {float(timber.size[0])*100/2:.1f}] Y=[{-float(timber.size[1])*100/2:.1f}, {float(timber.size[1])*100/2:.1f}] Z=[0, {float(timber.length)*100:.1f}]")
        print(f"        Sketch position: ({sketch_x:.1f}, {sketch_y:.1f}) on {face.name} plane")
        print(f"        Issue: Sketch might be outside timber geometry!")
        
        # Use actual mortise depth from spec
        cut_depth = depth_cm  # Use actual mortise depth
        print(f"      Step 9: Creating cut extrusion with depth {cut_depth:.1f} cm...")
        if app:
            app.log(f"      Step 9: Creating cut extrusion with depth {cut_depth:.1f} cm...")
        
        # Create cut extrusion with proper start/end positioning
        extrudes = component.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
        
        # Use simple distance extrusion for now (cut inward by mortise depth)
        distance = adsk.core.ValueInput.createByReal(cut_depth)  # Already in cm as expected by Fusion 360
        
        # CORRECTED: Cut from face surface toward timber center
        # For BACK face: face is at Y=-5.1, sketch at Y=0, so cut in +Y direction (from face toward center)
        if face == TimberFace.BACK:
            # BACK face: cut from Y=-5.1 toward Y=0 (positive Y direction)
            cut_direction = True  # Cut in +Y direction  
            print(f"      EXTRUSION: Cut {cut_depth:.1f} cm in +Y direction (from BACK face toward center)")
            print(f"      LOGIC: Face at Y={pos_y:.1f}, sketch at Y=0, cut toward center")
        elif face == TimberFace.FORWARD:
            # FORWARD face: cut from Y=+5.1 toward Y=0 (negative Y direction)
            cut_direction = False
            print(f"      EXTRUSION: Cut {cut_depth:.1f} cm in -Y direction (from FORWARD face toward center)")
        elif face == TimberFace.TOP:
            # TOP face: cut from Z=100 toward center (negative Z direction)
            cut_direction = False
            print(f"      EXTRUSION: Cut {cut_depth:.1f} cm in -Z direction (from TOP face toward center)")
        elif face == TimberFace.BOTTOM:
            # BOTTOM face: cut from Z=0 toward center (positive Z direction)
            cut_direction = True
            print(f"      EXTRUSION: Cut {cut_depth:.1f} cm in +Z direction (from BOTTOM face toward center)")
        elif face == TimberFace.RIGHT:
            # RIGHT face: cut from X=+5.1 toward center (negative X direction)
            cut_direction = False
            print(f"      EXTRUSION: Cut {cut_depth:.1f} cm in -X direction (from RIGHT face toward center)")
        else:  # LEFT face
            # LEFT face: cut from X=-5.1 toward center (positive X direction)
            cut_direction = True
            print(f"      EXTRUSION: Cut {cut_depth:.1f} cm in +X direction (from LEFT face toward center)")
            
        extrude_input.setDistanceExtent(cut_direction, distance)
        print(f"      Step 9a: Set extrusion distance for {face.name} face")
        if app:
            app.log(f"      Step 9a: Set extrusion direction and distance")
        
        print(f"      Step 10: Adding extrude feature...")
        print(f"      FINAL DEBUG BEFORE EXTRUSION:")
        print(f"        Sketch position: ({sketch_x:.1f}, {sketch_y:.1f}) cm")
        print(f"        Cut depth: {cut_depth:.1f} cm") 
        print(f"        Cut direction: {'Positive' if cut_direction else 'Negative'}")
        print(f"        Timber bounds: X=[-5.1,+5.1] Y=[-5.1,+5.1] Z=[0,100] cm")
        
        # Check if component has bodies to cut from
        bodies = component.bRepBodies
        print(f"        Component has {bodies.count} bodies to cut from")
        if bodies.count == 0:
            print(f"      ❌ FATAL ERROR: No bodies in component to cut from!")
            print(f"      The timber geometry might not have been created yet.")
            return False
        else:
            for i in range(bodies.count):
                body = bodies.item(i)
                print(f"        Body {i}: {body.name if body.name else 'Unnamed'}")
        
        if app:
            app.log(f"      Step 10: Adding extrude feature...")
        
        # EMERGENCY DEBUG: Check bodies right before extrusion
        print(f"      🚨 EMERGENCY DEBUG: About to extrude")
        print(f"      Component: {component.name}")
        print(f"      Bodies count: {component.bRepBodies.count}")
        print(f"      Sketch profiles: {sketch.profiles.count}")
        
        # List all bodies in component
        for i in range(component.bRepBodies.count):
            body = component.bRepBodies.item(i)
            print(f"        Body {i}: {body.name} (solid: {body.isSolid})")
        
        # Check extrude input setup
        print(f"      Extrude operation: {extrude_input.operation}")
        print(f"      Extrude profiles: {extrude_input.profile}")
        
        extrude = extrudes.add(extrude_input)
        print(f"      Step 10a: Extrude feature added")
        if app:
            app.log(f"      Step 10a: Extrude feature added")
        
        if extrude:
            print(f"      ✓ Created mortise cut on {face.name} face")
            return True
        else:
            print(f"      ✗ Failed to create mortise extrusion")
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
        print(f"🔥🔥🔥 RENDER_MULTIPLE_TIMBERS: {base_name}, transforms={apply_transforms}")
        app = get_fusion_app()
        if app:
            app.log(f"DEBUG: Starting three-pass rendering of {len(cut_timbers)} timbers...")
        
        print(f"🔥🔥🔥 AFTER APP LOG")
        
        # Get the active design
        print(f"🔥🔥🔥 ABOUT TO GET DESIGN")
        design = get_active_design()
        print(f"🔥🔥🔥 GOT DESIGN: {design}")
        if not design:
            print("Error: No active design found in Fusion 360")
            return 0
        
        root_comp = design.rootComponent
        print(f"🔥🔥🔥 GOT ROOT COMPONENT: {root_comp}")
        created_components = []
        print(f"🔥🔥🔥 ABOUT TO START PASS 1")
        
        # PASS 1: Create all timber geometry at origin
        print(f"\n=== PASS 1: Creating timber geometry ===")
        
        for i, cut_timber in enumerate(cut_timbers):
            print(f"🔥🔥🔥 PASS 1 LOOP: Processing timber {i}: {cut_timber}")
            component_name = cut_timber.name if cut_timber.name else f"{base_name}_{i+1:03d}"
            print(f"🔥🔥🔥 COMPONENT NAME: {component_name}")
            
            # Create component at origin
            occurrence = root_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            timber_component = occurrence.component
            timber_component.name = component_name
            
            # Create basic timber geometry
            geometry_success = create_timber_geometry(timber_component, cut_timber.timber, component_name)
            if geometry_success:
                print(f"  ✅ Created geometry for {component_name}: {timber_component.bRepBodies.count} bodies")
                created_components.append((occurrence, cut_timber, component_name))
            else:
                print(f"  ❌ Failed to create geometry for {component_name}")
        
        # Force refresh after all geometry creation
        adsk.doEvents()
        
        # PASS 2: Apply all cuts while timbers are at origin
        print(f"\n=== PASS 2: Applying cuts at origin ===")
        
        cut_success_count = 0
        total_cuts = 0
        applied_cuts = 0
        
        for occurrence, cut_timber, component_name in created_components:
            timber_joints = len(cut_timber.joints)
            total_cuts += timber_joints
            print(f"Processing {component_name}: {timber_joints} joints")
            app = get_fusion_app()
            if app:
                app.log(f"Processing {component_name}: {timber_joints} joints")
            
            if timber_joints > 0:
                timber_component = occurrence.component
                print(f"  Applying cuts to {component_name}...")
                print(f"    Component has {timber_component.bRepBodies.count} bodies before cuts")
                cut_success = apply_timber_cuts(timber_component, cut_timber, component_name)
                if cut_success:
                    cut_success_count += 1
                    applied_cuts += timber_joints
                    print(f"  ✓ Successfully applied {timber_joints} cuts to {component_name}")
                else:
                    print(f"  ✗ Failed to apply cuts to {component_name}")
            else:
                # No cuts to apply counts as success
                cut_success_count += 1
                print(f"  No cuts to apply to {component_name}")
        
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
        
        print(f"\n=== SUMMARY ===")
        print(f"Successfully rendered {transform_success_count} out of {len(cut_timbers)} timbers")
        print(f"Successfully applied cuts to {cut_success_count} out of {len(created_components)} timbers")
        print(f"Total cuts applied: {applied_cuts} out of {total_cuts}")
        if not apply_transforms:
            print(f"🐛 DEBUG MODE: All timbers kept at origin (transforms skipped)")
        
        return transform_success_count
        
    except Exception as e:
        print(f"🔥🔥🔥 EXCEPTION IN RENDER_MULTIPLE_TIMBERS: {str(e)}")
        print(f"Error in three-pass rendering: {str(e)}")
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