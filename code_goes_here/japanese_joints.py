"""
GiraffeCAD - Japanese Joint Construction Functions
Contains traditional Japanese timber joint implementations
"""

from __future__ import annotations  # Enable deferred annotation evaluation

from code_goes_here.timber import *
from code_goes_here.timber import _compute_timber_orientation  # Private function, needs explicit import
from code_goes_here.construction import *
from code_goes_here.moothymoth import (
    Orientation,
    EPSILON_GENERIC,
    zero_test,
    construction_parallel_check,
    construction_perpendicular_check
)
from code_goes_here.meowmeowcsg import (
    ConvexPolygonExtrusion,
    Prism,
    Difference
)


# ============================================================================
# Japanese Joint Construction Functions
# ============================================================================


# see diagram below
def draw_gooseneck_polygon(length: Numeric, small_width: Numeric, large_width: Numeric, head_length: Numeric) -> List[V2]:
    """
    Draw the gooseneck shape. 
    """
    return [
            Matrix([small_width/2, 0]),
            Matrix([small_width/2, length-head_length]),
            Matrix([large_width/2, length-head_length]),
            Matrix([small_width/2, length]),
            Matrix([-small_width/2, length]),
            Matrix([-large_width/2, length-head_length]),
            Matrix([-small_width/2, length-head_length]),
            Matrix([-small_width/2, 0]),
        ]

r'''

 ___     ___
    |   |                                     T  
    |   |                                     |
  __|   |__                                   |
  \       /        T                          | gooseneck_length
  .\     /.        | gooseneck_head_length    |
  . \___/ .        ⊥                          ⊥
  . .   . .
  . .   . .
  . |---| .        gooseneck_small_width
  .       .
  |-------|        gooseneck_large_width 


          lap length 
             |-|
__________________________
   |__|______|_              | <- goosneck_depth
_______________|__________
               ^
               end of receiving timber
'''
def cut_lapped_gooseneck_joint(
    gooseneck_timber: Timber,
    receiving_timber: Timber,
    receiving_timber_end: TimberReferenceEnd,
    gooseneck_timber_face: TimberReferenceLongFace,
    gooseneck_length: Numeric,
    gooseneck_small_width: Numeric,
    gooseneck_large_width: Numeric,
    gooseneck_head_length: Numeric,
    lap_length: Numeric = Rational(0), # 0 just means no lap
    gooseneck_lateral_offset: Numeric = Rational(0),
    gooseneck_depth: Optional[Numeric] = None
) -> Joint:
    """
    WIP NOT WORKING YET 
    
    Creates a lapped gooseneck joint (腰掛鎌継ぎ / Koshikake Kama Tsugi) between two timbers.
    
    This is a traditional Japanese timber joint that combines a lap joint with a gooseneck-shaped
    profile. The gooseneck profile provides mechanical interlock while the lap provides additional
    bearing surface.
    
    Args:
        gooseneck_timber: The timber that will have the gooseneck feature cut into it
        receiving_timber: The timber that receives the gooseneck. The top/bot of this timber also determines the position of the gooseneck joint
        receiving_timber_end: The end to cut on the receiving timber, which will also determine the end of the gooseneck timber
        gooseneck_timber_face: The face on the gooseneck timber where the gooseneck profile is visible
        gooseneck_length: Length of the gooseneck shape (does not include lap length)
        gooseneck_small_width: Width of the narrow end of the gooseneck taper
        gooseneck_large_width: Width of the wide end of the gooseneck taper
        gooseneck_head_length: Length of the head portion of the gooseneck
        lap_length: Length of the lap portion of the joint
        gooseneck_depth: Optional depth of the gooseneck cut. If None, defaults to half the timber dimension
                        perpendicular to the gooseneck_timber_face
    
    Returns:
        Joint object containing the two CutTimbers with the gooseneck cuts applied
    
    Raises:
        ValueError: If the parameters are invalid or the timbers are not properly positioned
        
    Notes:
        - The gooseneck profile creates a mechanical interlock that resists pulling apart
        - The lap provides additional bearing surface for compression loads
        - This joint is traditionally used for connecting beams end-to-end
    """
    
    # ========================================================================
    # Parameter validation
    # ========================================================================
    
    # Validate positive dimensions
    if gooseneck_length <= 0:
        raise ValueError(f"gooseneck_length must be positive, got {gooseneck_length}")
    if gooseneck_small_width <= 0:
        raise ValueError(f"gooseneck_small_width must be positive, got {gooseneck_small_width}")
    if gooseneck_large_width <= 0:
        raise ValueError(f"gooseneck_large_width must be positive, got {gooseneck_large_width}")
    if gooseneck_head_length <= 0:
        raise ValueError(f"gooseneck_head_length must be positive, got {gooseneck_head_length}")
    if lap_length <= 0:
        raise ValueError(f"lap_length must be positive, got {lap_length}")
    
    # Validate that large_width > small_width (gooseneck taper requirement)
    if gooseneck_large_width <= gooseneck_small_width:
        raise ValueError(
            f"gooseneck_large_width ({gooseneck_large_width}) must be greater than "
            f"gooseneck_small_width ({gooseneck_small_width})"
        )
    
    # Validate gooseneck_depth if provided
    if gooseneck_depth is not None and gooseneck_depth <= 0:
        raise ValueError(f"gooseneck_depth must be positive if provided, got {gooseneck_depth}")

    # Validate timbers are parallel
    if not are_timbers_parallel(gooseneck_timber, receiving_timber):
        raise ValueError(
            "Timbers must be parallel for gooseneck joint construction (face-parallel required). "
            f"Got gooseneck_timber axes: {gooseneck_timber.axis}, receiving_timber axes: {receiving_timber.axis}"
        )

    gooseneck_timber_end = TimberReferenceEnd.TOP if receiving_timber_end == TimberReferenceEnd.BOTTOM else TimberReferenceEnd.TOP

    # TODO check that the timbers overlap in a sensible way, e.g. something like this:
    #             |==================| <- gooseneck timber
    # receiving_timber_end -> |==================| <- receiving timber


    # compute the starting position for the gooseneck shape in global space
    gooseneck_direction_global = -receiving_timber.get_face_direction(receiving_timber_end)
    # TODO should lateral offset be different sign depending which face_direction?
    gooseneck_lateral_offset_direction_global = receiving_timber.get_face_direction(gooseneck_timber_face.rotate_right())
    gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global = receiving_timber.bottom_position + gooseneck_direction_global * lap_length + gooseneck_lateral_offset_direction_global * gooseneck_lateral_offset
    # project gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global onto the gooseneck_timber_face
    gooseneck_starting_position_global = receiving_timber.project_global_point_onto_timber_face_global(gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global, gooseneck_timber_face)
    gooseneck_drawing_normal_global = gooseneck_timber.get_face_direction(gooseneck_timber_face)

    # now cut the gooseneck shape into the gooseneck_timber
    gooseneck_shape = draw_gooseneck_polygon(gooseneck_length, gooseneck_small_width, gooseneck_large_width, gooseneck_head_length)

    # ========================================================================
    # Determine gooseneck depth default
    # ========================================================================
    
    if gooseneck_depth is None:
        # Default to half the dimension perpendicular to the specified face
        gooseneck_depth = gooseneck_timber.get_size_in_face_normal_axis(
            gooseneck_timber_face.to_timber_face()
        ) / 2

    # ========================================================================
    # Create gooseneck CSG geometry
    # ========================================================================
    
    # Create orientation for the gooseneck extrusion
    # The gooseneck polygon is in the XY plane where:
    #   - Y axis is along the gooseneck length (gooseneck_direction_global)
    #   - Z axis is the extrusion depth direction (pointing INWARD into the timber)
    #   - X axis is the width direction (perpendicular to both)
    # We flip the normal direction so Z points inward instead of outward
    gooseneck_width_direction_global = normalize_vector(cross_product(gooseneck_direction_global, gooseneck_drawing_normal_global))
    gooseneck_orientation = _compute_timber_orientation(
        length_direction=-gooseneck_drawing_normal_global,  # Z-axis points inward (negative of outward normal)
        width_direction=gooseneck_width_direction_global    # X-axis = width direction
    )
    gooseneck_transform = Transform(position=gooseneck_starting_position_global, orientation=gooseneck_orientation)
    
    # Create the gooseneck shape as a ConvexPolygonExtrusion
    # Now Z-axis points inward, so we extrude in the +Z direction (into the timber)
    # start_distance=0 means start at the face, end_distance=depth means extrude inward by depth
    gooseneck_shape_csg_on_gooseneck_timber = ConvexPolygonExtrusion(
        points=gooseneck_shape,
        transform=gooseneck_transform,
        start_distance=Rational(0),           # Start at the face
        end_distance=gooseneck_depth          # Extrude inward into timber by gooseneck_depth
    )
    
    # Create a larger prism that encompasses the region outside the gooseneck
    # This prism should cover the area we want to remove (everything but the gooseneck)
    # Make it larger than the gooseneck in all dimensions
    gooseneck_outside_width = gooseneck_large_width * Rational(2)  # Make it wider than the widest part
    gooseneck_outside_height = (gooseneck_length + lap_length) * Rational(2)  # Make it longer
    gooseneck_outside_csg_on_gooseneck_timber = Prism(
        size=create_v2(gooseneck_outside_width, gooseneck_outside_height),
        transform=gooseneck_transform,
        start_distance=Rational(0),           # Start at the face
        end_distance=gooseneck_depth          # Extrude inward by the same depth
    )
    
    # Create the cut for the gooseneck timber: remove everything except the gooseneck shape
    # This creates a "negative" that cuts away the material around the gooseneck
    gooseneck_timber_final_negative_csg = Difference(
        base=gooseneck_outside_csg_on_gooseneck_timber,
        subtract=[gooseneck_shape_csg_on_gooseneck_timber]  # subtract expects a list
    )

    # Create the matching pocket in the receiving timber
    # This is just the gooseneck shape extruded (a positive cut to remove material)
    receiving_timber_gooseneck_shape_csg = ConvexPolygonExtrusion(
        points=gooseneck_shape,
        transform=gooseneck_transform,
        start_distance=Rational(0),           # Start at the face
        end_distance=gooseneck_depth          # Extrude inward into timber by gooseneck_depth
    )
    



    
    # ========================================================================
    # Create the cuts on both timbers
    # ========================================================================
    
    # Create CutTimber for the gooseneck timber
    gooseneck_cut_timber = CutTimber(
        timber=gooseneck_timber,
        cuts=[CSGCut(
            timber=gooseneck_timber,
            transform=Transform(position=gooseneck_timber.bottom_position, orientation=gooseneck_timber.orientation),
            negative_csg=gooseneck_timber_final_negative_csg,
            maybe_end_cut=None
        )]
    )
    
    # Create CutTimber for the receiving timber  
    receiving_cut_timber = CutTimber(
        timber=receiving_timber,
        cuts=[CSGCut(
            timber=receiving_timber,
            transform=Transform(position=receiving_timber.bottom_position, orientation=receiving_timber.orientation),
            negative_csg=receiving_timber_gooseneck_shape_csg,
            maybe_end_cut=None
        )]
    )
    
    # Return the joint
    return Joint(
        cut_timbers={
            "gooseneck_timber": gooseneck_cut_timber,
            "receiving_timber": receiving_cut_timber
        },
        jointAccessories={}
    )


# ============================================================================
# Aliases for Japanese joint functions
# ============================================================================

# Japanese name alias
cut_腰掛鎌継ぎ = cut_lapped_gooseneck_joint
cut_koshikake_kama_tsugi = cut_lapped_gooseneck_joint

