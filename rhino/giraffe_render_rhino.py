"""
Rhino rendering module for GiraffeCAD timber framing system.

This module provides functions to render timber structures in Rhinoceros 3D
using the Rhino Python API (rhinoscriptsyntax and Rhino.Geometry).
"""

import rhinoscriptsyntax as rs
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
from typing import Optional, List, Tuple
import sys
import os

# Add parent directory to path to import GiraffeCAD modules
script_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from giraffe import CutTimber, Timber
from sympy import Matrix


def create_transform_from_timber(timber: Timber) -> rg.Transform:
    """
    Create a Rhino Transform from a GiraffeCAD Timber's position and orientation.
    
    Args:
        timber: Timber object with position and orientation
        
    Returns:
        Rhino.Geometry.Transform object
    """
    # Extract position
    px = float(timber.bottom_position[0])
    py = float(timber.bottom_position[1])
    pz = float(timber.bottom_position[2])
    
    # Extract orientation vectors
    # timber.orientation.matrix columns are [width_direction, height_direction, length_direction]
    # width_direction = width (X-axis of timber)
    # height_direction = height (Y-axis of timber)
    # length_direction = length (Z-axis of timber)
    
    face_x = float(timber.orientation.matrix[0, 0])
    face_y = float(timber.orientation.matrix[1, 0])
    face_z = float(timber.orientation.matrix[2, 0])
    
    height_x = float(timber.orientation.matrix[0, 1])
    height_y = float(timber.orientation.matrix[1, 1])
    height_z = float(timber.orientation.matrix[2, 1])
    
    length_x = float(timber.orientation.matrix[0, 2])
    length_y = float(timber.orientation.matrix[1, 2])
    length_z = float(timber.orientation.matrix[2, 2])
    
    # Create Rhino vectors
    face_vec = rg.Vector3d(face_x, face_y, face_z)
    height_vec = rg.Vector3d(height_x, height_y, height_z)
    length_vec = rg.Vector3d(length_x, length_y, length_z)
    
    # Create coordinate system at origin
    plane = rg.Plane(rg.Point3d.Origin, face_vec, height_vec)
    
    # Create transform from world to timber coordinate system
    transform = rg.Transform.PlaneToPlane(rg.Plane.WorldXY, plane)
    
    # Add translation
    translation = rg.Transform.Translation(px, py, pz)
    transform = translation * transform
    
    return transform


def create_timber_box(timber: Timber) -> Optional[rg.Brep]:
    """
    Create a box representing a timber.
    
    Args:
        timber: Timber object to create geometry for
        
    Returns:
        Rhino.Geometry.Brep representing the timber, or None if creation fails
    """
    try:
        # Get timber dimensions
        width = float(timber.size[0])   # face direction
        height = float(timber.size[1])  # height direction
        length = float(timber.length)   # length direction
        
        # Create box at origin in timber's local coordinate system
        # Box from origin extending in positive directions
        interval_x = rg.Interval(0, width)
        interval_y = rg.Interval(0, height)
        interval_z = rg.Interval(0, length)
        
        box = rg.Box(rg.Plane.WorldXY, interval_x, interval_y, interval_z)
        
        # Convert box to Brep
        brep = box.ToBrep()
        
        # Transform to timber's position and orientation
        transform = create_transform_from_timber(timber)
        brep.Transform(transform)
        
        return brep
        
    except Exception as e:
        print(f"Error creating timber box: {e}")
        return None


def render_timber(timber: Timber, name: Optional[str] = None, layer: Optional[str] = None) -> Optional[str]:
    """
    Render a single timber in Rhino.
    
    Args:
        timber: Timber object to render
        name: Optional name for the timber object
        layer: Optional layer name to place the timber on
        
    Returns:
        GUID of created object, or None if creation fails
    """
    # Create the timber geometry
    brep = create_timber_box(timber)
    if not brep:
        print(f"Failed to create geometry for timber: {name}")
        return None
    
    # Create layer if specified and doesn't exist
    if layer:
        if not rs.IsLayer(layer):
            rs.AddLayer(layer)
        # Make it the current layer
        rs.CurrentLayer(layer)
    
    # Add to Rhino document
    guid = sc.doc.Objects.AddBrep(brep)
    
    if guid:
        # Set object name if provided
        if name:
            rs.ObjectName(guid, name)
        
        print(f"Created timber: {name if name else 'Unnamed'}")
        return str(guid)
    else:
        print(f"Failed to add timber to document: {name}")
        return None


def render_cut_timber(cut_timber: CutTimber, name: Optional[str] = None, layer: Optional[str] = None) -> Optional[str]:
    """
    Render a CutTimber (timber with joints/cuts).
    
    Note: Currently only renders the base timber geometry, not the joints.
    Joint rendering will be added in future versions.
    
    Args:
        cut_timber: CutTimber object to render
        name: Optional name for the timber object
        layer: Optional layer name to place the timber on
        
    Returns:
        GUID of created object, or None if creation fails
    """
    # Use the timber's name if no name provided
    if not name and cut_timber.timber.name:
        name = cut_timber.timber.name
    
    # For now, just render the base timber
    # TODO: Apply mortise and tenon cuts
    return render_timber(cut_timber.timber, name, layer)


def render_multiple_timbers(cut_timbers: List[CutTimber], base_name: str = "Timber", 
                            layer: Optional[str] = "GiraffeCAD") -> int:
    """
    Render multiple CutTimber objects in Rhino.
    
    Args:
        cut_timbers: List of CutTimber objects to render
        base_name: Base name for timber objects (will be numbered)
        layer: Optional layer name to place all timbers on
        
    Returns:
        Number of successfully rendered timbers
    """
    success_count = 0
    
    print(f"\n{'='*60}")
    print(f"Rendering {len(cut_timbers)} timbers in Rhino...")
    print(f"{'='*60}\n")
    
    for i, ct in enumerate(cut_timbers):
        # Use timber's name if available, otherwise use base_name with index
        if ct.timber.name:
            name = ct.timber.name
        else:
            name = f"{base_name}_{i+1}"
        
        guid = render_cut_timber(ct, name, layer)
        if guid:
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Rendering complete: {success_count}/{len(cut_timbers)} timbers created")
    print(f"{'='*60}\n")
    
    return success_count


def clear_layer(layer_name: str):
    """
    Clear all objects from a specific layer.
    
    Args:
        layer_name: Name of the layer to clear
    """
    if rs.IsLayer(layer_name):
        # Select all objects on the layer
        objects = rs.ObjectsByLayer(layer_name)
        if objects:
            rs.DeleteObjects(objects)
            print(f"Cleared {len(objects)} objects from layer '{layer_name}'")


def clear_giraffeCAD_objects():
    """Clear all GiraffeCAD objects from the document."""
    clear_layer("GiraffeCAD")


# Test function
def test_render():
    """Test function to verify the renderer works."""
    from giraffe import create_timber, create_vector2d, create_vector3d
    from sympy import Rational
    
    print("Creating test timber...")
    
    # Create a simple vertical timber
    test_timber = create_timber(
        bottom_position=create_vector3d(0, 0, 0),
        length=2.0,
        size=create_vector2d(Rational(1, 10), Rational(1, 10)),
        length_direction=create_vector3d(0, 0, 1),
        width_direction=create_vector3d(1, 0, 0)
    )
    test_timber.name = "Test Timber"
    
    # Render it
    guid = render_timber(test_timber, "Test Timber", "GiraffeCAD")
    
    if guid:
        print("Test timber created successfully!")
    else:
        print("Failed to create test timber")


if __name__ == "__main__":
    # Run test when script is executed directly
    test_render()

