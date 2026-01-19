"""
GiraffeCAD - Japanese Joint Construction Functions
Contains traditional Japanese timber joint implementations
"""
import warnings

from code_goes_here.timber import *
from code_goes_here.timber import _compute_timber_orientation  # Private function, needs explicit import
from code_goes_here.construction import *
from code_goes_here.joint_shavings import (
    check_timber_overlap_for_splice_joint_is_sensible,
    chop_lap_on_timber_end,
    chop_timber_end_with_prism,
    measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber,
    find_opposing_face_on_another_timber,
    chop_profile_on_timber_face
)
from code_goes_here.moothymoth import (
    Orientation,
    EPSILON_GENERIC,
    zero_test,
    are_vectors_parallel,
    are_vectors_perpendicular
)
from code_goes_here.meowmeowcsg import (
    ConvexPolygonExtrusion,
    Prism,
    Difference,
    Union,
    translate_profiles,
    adopt_csg
)


# ============================================================================
# Japanese Joint Construction Functions
# ============================================================================


# see diagram below
def draw_gooseneck_polygon_NONCONVEX(length: Numeric, small_width: Numeric, large_width: Numeric, head_length: Numeric) -> List[V2]:
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

# see diagram below
def draw_gooseneck_polygon_CONVEX(length: Numeric, small_width: Numeric, large_width: Numeric, head_length: Numeric) -> List[List[V2]]:
    """
    Draw the gooseneck shape as multiple convex polygons.
    
    Returns a list of convex polygons that together form the gooseneck shape.
    This can be used with chop_profile_on_timber_face which accepts List[List[V2]]
    for creating non-convex profiles via union of convex shapes.
    """
    # Decompose the gooseneck into 2 convex polygons
    # Center rectangle and head trapezoid
    
    # Center neck rectangle
    center_rect = [
        Matrix([small_width/2, 0]),
        Matrix([small_width/2, length-head_length]),
        Matrix([-small_width/2, length-head_length]),
        Matrix([-small_width/2, 0]),
    ]
    
    # Head trapezoid (single shape)
    head_trap = [
        Matrix([-large_width/2, length-head_length]),
        Matrix([large_width/2, length-head_length]),
        Matrix([small_width/2, length]),
        Matrix([-small_width/2, length]),
    ]
    
    return [center_rect, head_trap]

# Alias for convenience
draw_gooseneck_polygon = draw_gooseneck_polygon_CONVEX


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
    Creates a lapped gooseneck joint (腰掛鎌継ぎ / Koshikake Kama Tsugi) between two timbers.
    
    This is a traditional Japanese timber joint that combines a lap joint with a gooseneck-shaped
    profile. The gooseneck profile provides mechanical interlock while the lap provides additional
    bearing surface.
    
    Args:
        gooseneck_timber: The timber that will have the gooseneck feature cut into it
        receiving_timber: The timber that receives the gooseneck. The top/bot of this timber also determines the position of the gooseneck joint
        receiving_timber_end: The end to cut on the receiving timber, which will also determine the end of the gooseneck timber (or you could add a optional parameter for this)
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

    # Find the opposing end on the gooseneck timber (the end that faces the receiving timber end)
    # We can use find_opposing_face_on_another_timber even though it's typed for long faces -
    # the logic works for end faces too
    opposing_face = gooseneck_timber.get_closest_oriented_face(
        -receiving_timber.get_face_direction(receiving_timber_end)
    )
    
    # Convert TimberFace to TimberReferenceEnd (TOP or BOTTOM)
    if opposing_face == TimberFace.TOP:
        gooseneck_timber_end = TimberReferenceEnd.TOP
    elif opposing_face == TimberFace.BOTTOM:
        gooseneck_timber_end = TimberReferenceEnd.BOTTOM
    else:
        raise ValueError(
            f"Expected opposing face to be an end face (TOP or BOTTOM), but got {opposing_face}. "
            f"This suggests the timbers are not properly oriented for a splice joint. "
            f"Should not be possible because of parallel check earlier."
        )

    # Check that the timbers overlap in a sensible way for a splice joint:
    #             |==================| <- gooseneck timber / end
    # receiving_timber_end -> |==================| <- receiving timber
    overlap_error = check_timber_overlap_for_splice_joint_is_sensible(
        gooseneck_timber, receiving_timber, gooseneck_timber_end, receiving_timber_end
    )
    if overlap_error:
        warnings.warn(f"Gooseneck joint configuration may not be sensible: {overlap_error}")

    # compute the starting position for the gooseneck shape in global space
    gooseneck_direction_global = -receiving_timber.get_face_direction(receiving_timber_end)
    gooseneck_lateral_offset_direction_global = receiving_timber.get_face_direction(gooseneck_timber_face.rotate_right())

    # Get the receiving timber end position
    if receiving_timber_end == TimberReferenceEnd.TOP:
        receiving_timber_end_position_global = receiving_timber.get_top_center_position()
    else:  # BOTTOM
        receiving_timber_end_position_global = receiving_timber.bottom_position
    
    # Move from the receiving timber end by gooseneck_length (inward) to get the gooseneck starting position
    gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global = receiving_timber_end_position_global + gooseneck_direction_global * lap_length + gooseneck_lateral_offset_direction_global * gooseneck_lateral_offset

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
    # Calculate lap positions and depths
    # ========================================================================
    
    # Extract the length component from gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global
    # This gives us the distance from the receiving timber's bottom position along its length axis
    gooseneck_starting_position_on_receiving_timber = (
        (gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global - receiving_timber.bottom_position).T 
        * receiving_timber.length_direction
    )[0, 0]
    
    # Compute lap end position: move by lap_length in the direction away from receiving timber end
    # (opposite of gooseneck_direction_global, which points inward from the end)
    lap_direction = -gooseneck_direction_global
    lap_end_position_on_receiving_timber = gooseneck_starting_position_on_receiving_timber + lap_length
    
    # Compute gooseneck depth relative to the opposing face on the receiving timber
    # This accounts for any offset or rotation between the timbers
    receiving_timber_lap_depth = measure_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
        reference_timber=gooseneck_timber,
        reference_face=gooseneck_timber_face,
        reference_depth_from_face=gooseneck_depth,
        target_timber=receiving_timber
    )
    
    # ========================================================================
    # Cut laps on both timbers
    # ========================================================================
    
    # Calculate shoulder position for receiving timber (distance from end to shoulder)
    if receiving_timber_end == TimberReferenceEnd.TOP:
        receiving_timber_shoulder_from_end = receiving_timber.length - gooseneck_starting_position_on_receiving_timber
    else:  # BOTTOM
        receiving_timber_shoulder_from_end = gooseneck_starting_position_on_receiving_timber
    
    # Get the receiving timber face that opposes the gooseneck face
    receiving_timber_lap_face_direction = -gooseneck_timber.get_face_direction(gooseneck_timber_face)
    receiving_timber_lap_face = receiving_timber.get_closest_oriented_face(receiving_timber_lap_face_direction)
    
    # Cut lap on receiving timber
    receiving_timber_lap_csg = chop_lap_on_timber_end(
        lap_timber=receiving_timber,
        lap_timber_end=receiving_timber_end,
        lap_timber_face=receiving_timber_lap_face,
        lap_length=lap_length,
        lap_shoulder_position_from_lap_timber_end=receiving_timber_shoulder_from_end,
        lap_depth=receiving_timber_lap_depth
    )
    
    # Calculate shoulder position for gooseneck timber
    # The gooseneck timber's lap starts at the point where it meets the receiving timber's lap end
    # and extends by lap_length in the direction of the gooseneck timber end
    gooseneck_lap_start_global = receiving_timber_end_position_global 
    
    # Project onto gooseneck timber's length axis
    gooseneck_lap_start_on_gooseneck_timber = (
        (gooseneck_lap_start_global - gooseneck_timber.bottom_position).T 
        * gooseneck_timber.length_direction
    )[0, 0]
    
    if gooseneck_timber_end == TimberReferenceEnd.TOP:
        gooseneck_timber_lap_shoulder_from_end = gooseneck_timber.length - gooseneck_lap_start_on_gooseneck_timber
    else:  # BOTTOM
        gooseneck_timber_lap_shoulder_from_end = gooseneck_lap_start_on_gooseneck_timber

    # Cut lap on gooseneck timber
    gooseneck_timber_lap_csg = chop_lap_on_timber_end(
        lap_timber=gooseneck_timber,
        lap_timber_end=gooseneck_timber_end,
        lap_timber_face=TimberFace(gooseneck_timber_face.value),
        lap_length=lap_length+gooseneck_length,
        lap_shoulder_position_from_lap_timber_end=gooseneck_timber_lap_shoulder_from_end,
        lap_depth=gooseneck_depth
    )
    
    # ========================================================================
    # Cut gooseneck shape into gooseneck timber
    # ========================================================================
    
    # Translate the gooseneck profile to the correct position
    # The profile coordinate system has Y-axis pointing into the timber from the end
    # Y=0 is at the timber end, Y increases going into the timber
    # draw_gooseneck_polygon creates profiles with base at Y=0 and head at Y=gooseneck_length
    #
    # The lap shoulder is at gooseneck_timber_lap_shoulder_from_end from the end
    # The gooseneck profile should start lap_length inward from the shoulder
    # So: gooseneck base position = shoulder + lap_length
    gooseneck_profile_y_position = gooseneck_timber_lap_shoulder_from_end + lap_length
    
    gooseneck_profiles_translated = translate_profiles(
        gooseneck_shape,
        Matrix([0, gooseneck_profile_y_position])
    )
    
    # Create the gooseneck profile CSG cut using chop_profile_on_timber_face
    # This creates a CSG that removes the gooseneck shape from the timber
    gooseneck_profile_csg = chop_profile_on_timber_face(
        timber=gooseneck_timber,
        end=gooseneck_timber_end,
        face=TimberFace(gooseneck_timber_face.value),
        profile=gooseneck_profiles_translated,
        depth=gooseneck_depth
    )

    # use chop_timber_end_with_prism to create a prism starting from gooseneck_profile_y_position
    gooseneck_profile_prism = chop_timber_end_with_prism(
        timber=gooseneck_timber,
        end=gooseneck_timber_end,
        distance_from_end_to_cut=-gooseneck_profile_y_position
    )

    # difference the gooseneck profile prism with the gooseneck profile csg
    gooseneck_profile_difference_csg = Difference(gooseneck_profile_prism, [gooseneck_profile_csg])
    
    # Union the gooseneck profile cut with the lap cut
    # Both cuts need to be applied to the gooseneck timber
    gooseneck_timber_combined_csg = Union([gooseneck_timber_lap_csg, gooseneck_profile_difference_csg])


    # Transform the gooseneck profile CSG from gooseneck_timber coordinates to receiving_timber coordinates
    # Use the generic adopt_csg function to handle all CSG types (Union, Difference, Prism, etc.)
    gooseneck_csg_on_receiving_timber = adopt_csg(gooseneck_timber, receiving_timber, gooseneck_profile_csg) 


    
    # Create CSGCut objects for each timber
    receiving_timber_cut_obj = CSGCut(
        timber=receiving_timber,
        transform=Transform.identity(), 
        maybe_end_cut=receiving_timber_end,
        negative_csg=Union([receiving_timber_lap_csg, gooseneck_csg_on_receiving_timber])
    )

    
    gooseneck_timber_cut_obj = CSGCut(
        timber=gooseneck_timber,
        transform=Transform.identity(), 
        maybe_end_cut=gooseneck_timber_end,
        negative_csg=gooseneck_timber_combined_csg
    )
    
    # Create CutTimber objects with the cuts
    receiving_timber_cut = CutTimber(
        timber=receiving_timber,
        cuts=[receiving_timber_cut_obj]
    )
    
    gooseneck_timber_cut = CutTimber(
        timber=gooseneck_timber,
        cuts=[gooseneck_timber_cut_obj]
    )
    
    return Joint(
        cut_timbers={
            receiving_timber.name: receiving_timber_cut,
            gooseneck_timber.name: gooseneck_timber_cut
        },
        jointAccessories={}
    )

# ============================================================================
# Aliases for Japanese joint functions
# ============================================================================

# Japanese name alias
cut_腰掛鎌継ぎ = cut_lapped_gooseneck_joint
cut_koshikake_kama_tsugi = cut_lapped_gooseneck_joint

