"""
Test examples for CutCSG rendering.

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
from code_goes_here.cutcsg import *
from code_goes_here.rule import Orientation, Transform, inches, feet
from code_goes_here.timber import Timber, TimberReferenceEnd, TimberFace, timber_from_directions
from code_goes_here.joint_shavings import chop_lap_on_timber_end, chop_profile_on_timber_face, chop_shoulder_notch_on_timber_face
from code_goes_here.japanese_joints import draw_gooseneck_polygon


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
        transform=Transform(
            position=Matrix([0, 0, 0]),  # Cross-section center at origin
            orientation=Orientation(eye(3))  # Identity orientation
        )
    )
    
    # Create a 1x1x1 cube to cut out (cross-section centered at origin)
    small_cube = Prism(
        size=Matrix([1, 1]),  # 1m x 1m cross-section
        start_distance=0,      # Start at Z=0 (relative to position)
        end_distance=1,        # End at Z=1 (relative to position)
        transform=Transform(
            position=Matrix([0, 0, 0]),  # Cross-section center at origin
            orientation=Orientation(eye(3))  # Identity orientation
        )
    )
    
    # Create the difference
    result = Difference(
        base=large_cube,
        subtract=[small_cube]
    )
    
    return result


def example_cube_with_halfspace_cut():
    """
    1x1x1 cube with bottom half removed by HalfSpace at Z=0.5.
    
    Cube: X=[-0.5, 0.5], Y=[-0.5, 0.5], Z=[0, 1] (centered at origin in XY)
    HalfSpace keeps points where Z >= 0.5
    Result: Top half only, X=[-0.5, 0.5], Y=[-0.5, 0.5], Z=[0.5, 1]
    
    Returns:
        Difference CSG object
    """
    # Create a 1x1x1 cube (cross-section centered at origin)
    cube = Prism(
        size=Matrix([1, 1]),  # 1m x 1m cross-section
        start_distance=0,      # Start at Z=0 (relative to position)
        end_distance=1,        # End at Z=1 (relative to position)
        transform=Transform(
            position=Matrix([0, 0, 0]),  # Cross-section center at origin
            orientation=Orientation(eye(3))  # Identity orientation
        )
    )
    
    # Create a halfspace that removes Z < 0.5
    # Plane equation: normal · P >= offset
    # HalfSpace with normal=(0,0,1) and offset=0.5 keeps points where z >= 0.5
    # When used in Difference, it removes points where z < 0.5
    halfspace = HalfSpace(
        normal=Matrix([0, 0, 1]),  # Normal pointing up (+Z)
        offset=Rational(1, 2)  # Plane at Z = 0.5
    )
    
    # Create the difference (remove bottom half)
    result = Difference(
        base=cube,
        subtract=[halfspace]
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
        transform=Transform(
            position=Matrix([2, 3, 1]),  # Center at (2, 3, 1)
            orientation=Orientation(eye(3))  # Identity orientation
        )
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
        transform=Transform(
            position=Matrix([0, 0, 0]),
            orientation=Orientation(eye(3))
        )
    )
    
    # Second cube offset by 1m in X (cross-section centered at (1,0,0))
    cube2 = Prism(
        size=Matrix([1, 1]),
        start_distance=0,
        end_distance=1,
        transform=Transform(
            position=Matrix([1, 0, 0]),
            orientation=Orientation(eye(3))
        )
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
        start_distance=0,  # Start at Z=0
        end_distance=1,    # End at Z=1 (1 meter tall)
        transform=Transform.identity()
    )
    
    return hexagon


def example_lap_cut_on_timber():
    """
    4"x4"x4' timber with a 4" lap cut on the top end.
    
    Creates a timber and cuts a lap joint on it using chop_lap_on_timber_end.
    The lap is cut from the BACK face at the TOP end of the timber.
    
    Dimensions (in meters):
    - Timber: 0.1016m x 0.1016m x 1.2192m (4" x 4" x 4')
    - Lap depth: 0.1016m (4", which is the full height)
    - Lap length: 0.3048m (12" = 1')
    - Shoulder position: 0.1016m (4" from the top end)
    
    Returns:
        Difference CSG object (timber with lap cut removed)
    """
    # Convert inches and feet to meters
    # 1 inch = 0.0254 meters, 1 foot = 0.3048 meters
    inch = Rational(254, 10000)  # 0.0254 meters
    foot = Rational(3048, 10000)  # 0.3048 meters
    
    # Create a 4"x4"x4' timber
    timber_width = 4 * inch  # 4"
    timber_height = 4 * inch  # 4"
    timber_length = 4 * foot  # 4'
    
    # Create timber extending along X-axis
    timber = timber_from_directions(
        length=timber_length,
        size=Matrix([timber_width, timber_height]),
        bottom_position=Matrix([0, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0]),
        name='lap_test_timber'
    )
    
    # Create the lap cut parameters
    lap_depth = 2 * inch  # Cut 2" (half the height)
    lap_length = 1 * foot  # 1 foot long lap
    shoulder_distance = 4 * inch  # Shoulder is 4" from the top end
    
    # Create the lap cut CSG (in timber's local coordinates)
    lap_cut_csg = chop_lap_on_timber_end(
        lap_timber=timber,
        lap_timber_end=TimberReferenceEnd.TOP,
        lap_timber_face=TimberFace.BACK,
        lap_length=lap_length,
        lap_shoulder_position_from_lap_timber_end=shoulder_distance,
        lap_depth=lap_depth
    )
    
    # Create the base timber prism (in local coordinates)
    timber_prism = Prism(
        size=timber.size,
        transform=Transform.identity(),
        start_distance=0,
        end_distance=None
    )
    
    # Create the difference (timber with lap cut removed)
    result = Difference(
        base=timber_prism,
        subtract=[lap_cut_csg]
    )
    
    return result


def example_gooseneck_profile_cut():
    """
    2"x6"x4' timber with a gooseneck profile cut on the FRONT face at the TOP end.
    
    Creates a timber and cuts a gooseneck profile using chop_profile_on_timber_face.
    The gooseneck is a traditional Japanese joint feature with a tapered profile.
    
    Dimensions (in meters):
    - Timber: 0.0508m x 0.1524m x 1.2192m (2" x 6" x 4')
    - Gooseneck length: 0.2032m (8")
    - Gooseneck small width: 0.0254m (1")
    - Gooseneck large width: 0.0508m (2")
    - Gooseneck head length: 0.0508m (2")
    - Gooseneck depth: 0.0254m (1", cuts into the timber)
    
    Returns:
        Difference CSG object (timber with gooseneck profile cut removed)
    """
    # Create a 2"x6"x4' timber
    timber_width = inches(2)   # 2"
    timber_height = inches(6)  # 6"
    timber_length = feet(4)    # 4'
    
    # Create timber extending along Z-axis (vertical)
    timber = timber_from_directions(
        length=timber_length,
        size=Matrix([timber_width, timber_height]),
        bottom_position=Matrix([0, 0, 0]),
        length_direction=Matrix([0, 0, 1]),  # Vertical
        width_direction=Matrix([1, 0, 0]),   # Along X
        name='gooseneck_test_timber'
    )
    
    # Define gooseneck parameters
    gooseneck_length = inches(8)       # 8"
    gooseneck_small_width = inches(1)  # 1"
    gooseneck_large_width = inches(2)  # 2"
    gooseneck_head_length = inches(2)  # 2"
    gooseneck_depth = inches(1)        # 1" deep into the timber
    
    # Create the gooseneck profile (returns List[List[V2]] for multiple convex shapes)
    gooseneck_profiles = draw_gooseneck_polygon(
        length=gooseneck_length,
        small_width=gooseneck_small_width,
        large_width=gooseneck_large_width,
        head_length=gooseneck_head_length
    )
    
    # Create the gooseneck cut CSG (in timber's local coordinates)
    # The profile is positioned so its head is at the timber end
    gooseneck_cut_csg = chop_profile_on_timber_face(
        timber=timber,
        end=TimberReferenceEnd.TOP,
        face=TimberFace.RIGHT,
        profile=gooseneck_profiles,
        depth=gooseneck_depth,
        profile_y_offset_from_end=gooseneck_length
    )
    
    # Create the base timber prism (in local coordinates)
    timber_prism = Prism(
        size=timber.size,
        transform=Transform.identity(),
        start_distance=0,
        end_distance=timber.length
    )
    
    # Create the difference (timber with gooseneck cut removed)
    result = Difference(
        base=timber_prism,
        subtract=[gooseneck_cut_csg]
    )
    
    return result


def example_shoulder_notch_on_timber():
    """
    4"x4"x4' vertical timber with a 1" deep x 4" wide shoulder notch on the right face.
    
    Creates a vertical timber and cuts a rectangular shoulder notch in the center
    using chop_shoulder_notch_on_timber_face.
    
    Dimensions (in meters):
    - Timber: 0.1016m x 0.1016m x 1.2192m (4" x 4" x 4')
    - Notch depth: 0.0254m (1")
    - Notch width: 0.1016m (4")
    - Notch center position: 0.6096m (24" = 2' from bottom, center of timber)
    
    Returns:
        Difference CSG object (timber with shoulder notch removed)
    """
    # Create a 4"x4"x4' vertical timber
    timber_width = inches(4)   # 4"
    timber_height = inches(4)  # 4"
    timber_length = feet(4)    # 4'
    
    # Create vertical timber extending along Z-axis
    timber = timber_from_directions(
        length=timber_length,
        size=Matrix([timber_width, timber_height]),
        bottom_position=Matrix([0, 0, 0]),
        length_direction=Matrix([0, 0, 1]),  # Vertical (along Z)
        width_direction=Matrix([1, 0, 0]),   # Width along X
        name='shoulder_notch_test_timber'
    )
    
    # Define notch parameters
    notch_depth = inches(1)    # 1" deep into the timber
    notch_width = inches(4)    # 4" wide along timber length
    notch_center = timber_length / Rational(2)  # Center of timber (2' from bottom)
    
    # Create the shoulder notch CSG (in timber's local coordinates)
    notch_cut_csg = chop_shoulder_notch_on_timber_face(
        timber=timber,
        notch_face=TimberFace.RIGHT,
        distance_along_timber=notch_center,
        notch_width=notch_width,
        notch_depth=notch_depth
    )
    
    # Create the base timber prism (in local coordinates)
    timber_prism = Prism(
        size=timber.size,
        transform=Transform.identity(),
        start_distance=0,
        end_distance=timber.length
    )
    
    # Create the difference (timber with shoulder notch removed)
    result = Difference(
        base=timber_prism,
        subtract=[notch_cut_csg]
    )
    
    return result


# Dictionary for easy example selection
EXAMPLES = {
    'cube_cutout': {
        'name': 'Cube with Cube Cutout',
        'description': '2x2x2 cube with 1x1x1 cube removed (both centered at origin)',
        'function': example_cube_with_cube_cutout
    },
    'halfspace_cut': {
        'name': 'Cube with HalfSpace Cut',
        'description': '1x1x1 cube with bottom half removed by HalfSpace at Z=0.5',
        'function': example_cube_with_halfspace_cut
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
    },
    'lap_cut_timber': {
        'name': 'Lap Cut on Timber',
        'description': '4"x4"x4\' timber with 4" lap cut on top end (tests chop_lap_on_timber_end)',
        'function': example_lap_cut_on_timber
    },
    'gooseneck_profile': {
        'name': 'Gooseneck Profile Cut',
        'description': '2"x6"x4\' timber with gooseneck profile cut (tests chop_profile_on_timber_face)',
        'function': example_gooseneck_profile_cut
    },
    'shoulder_notch': {
        'name': 'Shoulder Notch on Timber',
        'description': '4"x4"x4\' vertical timber with 1" deep x 4" wide notch on right face (tests chop_shoulder_notch_on_timber_face)',
        'function': example_shoulder_notch_on_timber
    }
}


def create_csg_examples_patternbook():
    """
    Create a PatternBook with all CSG example patterns.
    
    Each pattern has groups: ["csg", "{example_type}"]
    
    Returns:
        PatternBook: PatternBook containing all CSG example patterns
    """
    from code_goes_here.patternbook import PatternBook, PatternMetadata
    
    patterns = []
    for key, info in EXAMPLES.items():
        # Determine the example type from the key
        example_type = key.replace('_', ' ')
        
        patterns.append((
            PatternMetadata(key, ["csg", key], "csg"),
            lambda center, func=info['function']: func()  # CSG examples don't use center position
        ))
    
    return PatternBook(patterns=patterns)


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

