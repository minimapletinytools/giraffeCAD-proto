"""
Test examples for MeowMeowCSG rendering.

These examples create simple CSG operations to test and verify
rendering backends (FreeCAD, Fusion 360, Rhino, etc.).

All dimensions are in METERS (GiraffeCAD convention).

NOTE: Prism positioning follows the Timber convention:
- The 'position' parameter specifies the CENTER of the cross-section (in XY)
- The cross-section extends ±size/2 around this center point
- 'start_distance' and 'end_distance' define Z extents RELATIVE to position.Z
- So a prism at position=(0,0,0) with size=[1,1] spans X=[-0.5,0.5], Y=[-0.5,0.5]
"""

from sympy import Matrix, eye, Rational, sqrt
from code_goes_here.meowmeowcsg import Prism, HalfPlane, Difference, Union, ConvexPolygonExtrusion
from code_goes_here.moothymoth import Orientation


def example_cube_with_cube_cutout():
    """
    2x2x2 cube with 1x1x1 cube cut out, both centered at origin.
    
    Large cube: X=[-1, 1], Y=[-1, 1], Z=[0, 2]
    Small cube: X=[-0.5, 0.5], Y=[-0.5, 0.5], Z=[0, 1]
    Result: Hollow bottom corner of large cube
    
    Returns:
        Difference CSG object
    """
    # Create a 2x2x2 cube (bottom cross-section centered at origin, rising to Z=2)
    large_cube = Prism(
        size=Matrix([2, 2]),  # 2m x 2m cross-section
        start_distance=0,      # Start at Z=0 (relative to position)
        end_distance=2,        # End at Z=2 (relative to position)
        position=Matrix([0, 0, 0]),  # Cross-section center at origin
        orientation=Orientation(eye(3))  # Identity orientation
    )
    
    # Create a 1x1x1 cube to cut out (cross-section centered at origin)
    small_cube = Prism(
        size=Matrix([1, 1]),  # 1m x 1m cross-section
        start_distance=0,      # Start at Z=0 (relative to position)
        end_distance=1,        # End at Z=1 (relative to position)
        position=Matrix([0, 0, 0]),  # Cross-section center at origin
        orientation=Orientation(eye(3))  # Identity orientation
    )
    
    # Create the difference
    result = Difference(
        base=large_cube,
        subtract=[small_cube]
    )
    
    return result


def example_cube_with_halfplane_cut():
    """
    1x1x1 cube with bottom half removed by HalfPlane at Z=0.5.
    
    Cube: X=[-0.5, 0.5], Y=[-0.5, 0.5], Z=[0, 1] (centered at origin in XY)
    HalfPlane keeps points where Z >= 0.5
    Result: Top half only, X=[-0.5, 0.5], Y=[-0.5, 0.5], Z=[0.5, 1]
    
    Returns:
        Difference CSG object
    """
    # Create a 1x1x1 cube (cross-section centered at origin)
    cube = Prism(
        size=Matrix([1, 1]),  # 1m x 1m cross-section
        start_distance=0,      # Start at Z=0 (relative to position)
        end_distance=1,        # End at Z=1 (relative to position)
        position=Matrix([0, 0, 0]),  # Cross-section center at origin
        orientation=Orientation(eye(3))  # Identity orientation
    )
    
    # Create a halfplane that removes Z < 0.5
    # Plane equation: normal · P >= offset
    # HalfPlane with normal=(0,0,1) and offset=0.5 keeps points where z >= 0.5
    # When used in Difference, it removes points where z < 0.5
    halfplane = HalfPlane(
        normal=Matrix([0, 0, 1]),  # Normal pointing up (+Z)
        offset=Rational(1, 2)  # Plane at Z = 0.5
    )
    
    # Create the difference (remove bottom half)
    result = Difference(
        base=cube,
        subtract=[halfplane]
    )
    
    return result


def example_cube_at_position():
    """
    Simple 1x1x1 cube centered at (2, 3, 1).
    
    Cube: X=[1.5, 2.5], Y=[2.5, 3.5], Z=[0.5, 1.5]
    This tests position transformation without cuts.
    
    Returns:
        Prism CSG object
    """
    cube = Prism(
        size=Matrix([1, 1]),  # 1m x 1m cross-section
        start_distance=Rational(-1, 2),   # Start at Z=-0.5 (relative to position Z=1)
        end_distance=Rational(1, 2),      # End at Z=0.5 (relative to position Z=1)
        position=Matrix([2, 3, 1]),  # Center at (2, 3, 1)
        orientation=Orientation(eye(3))  # Identity orientation
    )
    
    return cube


def example_union_of_cubes():
    """
    Two 1x1x1 cubes joined together along X-axis (touching edge-to-edge).
    
    Cube 1: X=[-0.5, 0.5], Y=[-0.5, 0.5], Z=[0, 1]
    Cube 2: X=[0.5, 1.5], Y=[-0.5, 0.5], Z=[0, 1]
    Result: 2x1x1 rectangular block along X-axis
    
    Returns:
        Union CSG object
    """
    # First cube (cross-section centered at origin)
    cube1 = Prism(
        size=Matrix([1, 1]),
        start_distance=0,
        end_distance=1,
        position=Matrix([0, 0, 0]),
        orientation=Orientation(eye(3))
    )
    
    # Second cube offset by 1m in X (cross-section centered at (1,0,0))
    cube2 = Prism(
        size=Matrix([1, 1]),
        start_distance=0,
        end_distance=1,
        position=Matrix([1, 0, 0]),
        orientation=Orientation(eye(3))
    )
    
    result = Union(children=[cube1, cube2])
    
    return result


def example_hexagon_extrusion():
    """
    Regular hexagon extruded to 1m height, centered at origin.
    
    The hexagon has a radius of 0.5m (distance from center to vertices).
    Vertices are positioned at 60-degree intervals starting from the positive X-axis.
    Extruded from Z=0 to Z=1.
    
    Returns:
        ConvexPolygonExtrusion CSG object
    """
    # Create regular hexagon with radius 0.5m
    # Vertices at angles: 0°, 60°, 120°, 180°, 240°, 300°
    radius = Rational(1, 2)  # 0.5 meters
    
    hexagon_points = [
        Matrix([radius, 0]),                           # 0°
        Matrix([radius/2, radius * sqrt(3)/2]),        # 60°
        Matrix([-radius/2, radius * sqrt(3)/2]),       # 120°
        Matrix([-radius, 0]),                          # 180°
        Matrix([-radius/2, -radius * sqrt(3)/2]),      # 240°
        Matrix([radius/2, -radius * sqrt(3)/2])        # 300°
    ]
    
    hexagon = ConvexPolygonExtrusion(
        points=hexagon_points,
        length=1,  # 1 meter tall
        position=Matrix([0, 0, 0]),  # Bottom face at Z=0
        orientation=Orientation(eye(3))  # Identity orientation
    )
    
    return hexagon


# Dictionary for easy example selection
EXAMPLES = {
    'cube_cutout': {
        'name': 'Cube with Cube Cutout',
        'description': '2x2x2 cube with 1x1x1 cube removed (both centered at origin)',
        'function': example_cube_with_cube_cutout
    },
    'halfplane_cut': {
        'name': 'Cube with HalfPlane Cut',
        'description': '1x1x1 cube with bottom half removed by HalfPlane at Z=0.5',
        'function': example_cube_with_halfplane_cut
    },
    'positioned_cube': {
        'name': 'Positioned Cube',
        'description': '1x1x1 cube centered at (2, 3, 1) - tests positioning',
        'function': example_cube_at_position
    },
    'union_cubes': {
        'name': 'Union of Two Cubes',
        'description': 'Two 1x1x1 cubes joined edge-to-edge along X-axis',
        'function': example_union_of_cubes
    },
    'hexagon_extrusion': {
        'name': 'Hexagon Extrusion',
        'description': 'Regular hexagon (0.5m radius) extruded to 1m height',
        'function': example_hexagon_extrusion
    }
}


def get_example(example_key: str):
    """
    Get a CSG example by key.
    
    Args:
        example_key: Key from EXAMPLES dictionary
        
    Returns:
        CSG object
    """
    if example_key not in EXAMPLES:
        raise ValueError(f"Unknown example: {example_key}. Available: {list(EXAMPLES.keys())}")
    
    return EXAMPLES[example_key]['function']()


def list_examples():
    """Print all available examples."""
    print("Available CSG Examples:")
    print("=" * 60)
    for key, info in EXAMPLES.items():
        print(f"  {key:20s} - {info['name']}")
        print(f"  {' '*20}   {info['description']}")
    print("=" * 60)


if __name__ == "__main__":
    # When run directly, list all examples
    list_examples()

