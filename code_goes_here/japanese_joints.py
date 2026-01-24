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
    chop_profile_on_timber_face,
    chop_shoulder_notch_on_timber_face
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
    Union as CSGUnion,
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

    # TODO why is this going off in our example
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
    gooseneck_timber_combined_csg = CSGUnion([gooseneck_timber_lap_csg, gooseneck_profile_difference_csg])


    # Transform the gooseneck profile CSG from gooseneck_timber coordinates to receiving_timber coordinates
    # Use the generic adopt_csg function to handle all CSG types (Union, Difference, Prism, etc.)
    gooseneck_csg_on_receiving_timber = adopt_csg(gooseneck_timber, receiving_timber, gooseneck_profile_csg) 


    
    # Create CSGCut objects for each timber
    receiving_timber_cut_obj = CSGCut(
        timber=receiving_timber,
        transform=Transform.identity(), 
        maybe_end_cut=receiving_timber_end,
        negative_csg=CSGUnion([receiving_timber_lap_csg, gooseneck_csg_on_receiving_timber])
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

def cut_lapped_dovetail_butt_joint(
    dovetail_timber: Timber,
    receiving_timber: Timber,
    dovetail_timber_end: TimberReferenceEnd,
    dovetail_timber_face: TimberReferenceLongFace,
    receiving_timber_shoulder_inset: Numeric,
    dovetail_length: Numeric,
    dovetail_small_width: Numeric,
    dovetail_large_width: Numeric,
    dovetail_lateral_offset: Numeric = Rational(0),
    dovetail_depth: Optional[Numeric] = None
) -> Joint:
    """
    Creates a dovetail butt joint (蟻継ぎ / Ari Tsugi) between two orthogonal timbers.
    
    This is a traditional Japanese timber joint where a dovetail-shaped tenon on one timber
    fits into a matching dovetail socket on another timber. The dovetail shape provides
    mechanical resistance to pulling apart.
    
    Args:
        dovetail_timber: The timber that will have the dovetail tenon
        receiving_timber: The timber that receives the dovetail socket (must be orthogonal)
        dovetail_timber_end: The end of the dovetail timber where the dovetail is cut
        dovetail_timber_face: The face on the dovetail timber where the dovetail profile is visible
        receiving_timber_shoulder_inset: Distance to inset the shoulder notch on the receiving timber
        dovetail_length: Length of the dovetail tenon
        dovetail_small_width: Width of the narrow end of the dovetail (at the tip)
        dovetail_large_width: Width of the wide end of the dovetail (at the base)
        dovetail_lateral_offset: Lateral offset of the dovetail from center (default 0)
        dovetail_depth: Depth of the dovetail cut. If None, defaults to half the timber dimension
    
    Returns:
        Joint object containing the two CutTimbers with the dovetail cuts applied
    
    Raises:
        ValueError: If the parameters are invalid or the timbers are not orthogonal
    
    Notes:
        - The dovetail provides mechanical resistance to pulling apart
        - Timbers must be orthogonal (at 90 degrees) for this joint
        - No lap is used in this joint (unlike the lapped gooseneck joint)
    """
    
    # ========================================================================
    # Parameter validation
    # ========================================================================
    
    # Validate positive dimensions
    if dovetail_length <= 0:
        raise ValueError(f"dovetail_length must be positive, got {dovetail_length}")
    if dovetail_small_width <= 0:
        raise ValueError(f"dovetail_small_width must be positive, got {dovetail_small_width}")
    if dovetail_large_width <= 0:
        raise ValueError(f"dovetail_large_width must be positive, got {dovetail_large_width}")
    if receiving_timber_shoulder_inset < 0:
        raise ValueError(f"receiving_timber_shoulder_inset must be non-negative, got {receiving_timber_shoulder_inset}")
    
    # Validate that large_width > small_width (dovetail taper requirement)
    if dovetail_large_width <= dovetail_small_width:
        raise ValueError(
            f"dovetail_large_width ({dovetail_large_width}) must be greater than "
            f"dovetail_small_width ({dovetail_small_width})"
        )
    
    # Validate dovetail_depth if provided
    if dovetail_depth is not None and dovetail_depth <= 0:
        raise ValueError(f"dovetail_depth must be positive if provided, got {dovetail_depth}")
    
    # Assert timbers are orthogonal (not parallel)
    if not are_timbers_orthogonal(dovetail_timber, receiving_timber):
        raise ValueError(
            "Timbers must be orthogonal (perpendicular) for dovetail butt joint. "
            f"Got dovetail_timber length_direction: {dovetail_timber.length_direction.T}, "
            f"receiving_timber length_direction: {receiving_timber.length_direction.T}"
        )

    # Assert timbers are face aligned
    if not are_timbers_face_aligned(dovetail_timber, receiving_timber):
        raise ValueError(
            "Timbers must be face-aligned for dovetail butt joint. "
        )
    
    # ========================================================================
    # Calculate default depth if not provided
    # ========================================================================
    
    if dovetail_depth is None:
        # Default: half the timber dimension perpendicular to the dovetail face
        face_enum = TimberFace(dovetail_timber_face.value)
        if face_enum == TimberFace.LEFT or face_enum == TimberFace.RIGHT:
            dovetail_depth = dovetail_timber.size[0] / Rational(2)
        else:  # FRONT or BACK
            dovetail_depth = dovetail_timber.size[1] / Rational(2)
    
    # ========================================================================
    # Create the dovetail profile (simple trapezoid)
    # ========================================================================
    
    # Dovetail profile in 2D (X = lateral, Y = along timber length from end)
    # Y=0 is at the timber end, Y increases going into the timber
    # Small width at Y=0 (tip), large width at Y=dovetail_length (base)
    
    dovetail_profile = [
        # Tip (narrow end at the timber end)
        Matrix([-dovetail_small_width / Rational(2) + dovetail_lateral_offset, 0]),
        Matrix([dovetail_small_width / Rational(2) + dovetail_lateral_offset, 0]),
        # Base (wide end)
        Matrix([dovetail_large_width / Rational(2) + dovetail_lateral_offset, dovetail_length]),
        Matrix([-dovetail_large_width / Rational(2) + dovetail_lateral_offset, dovetail_length]),
    ]
    
    # ========================================================================
    # Cut dovetail shape into dovetail timber (positive tenon)
    # ========================================================================
    
    # Create the dovetail profile CSG using chop_profile_on_timber_face
    # This creates the profile extrusion
    dovetail_profile_csg = chop_profile_on_timber_face(
        timber=dovetail_timber,
        end=dovetail_timber_end,
        face=TimberFace(dovetail_timber_face.value),
        profile=dovetail_profile,
        depth=dovetail_depth
    )
    
    # ========================================================================
    # Find where the dovetail timber meets the receiving timber (shoulder position)
    # ========================================================================
    
    # Get the end position and direction of the dovetail timber
    if dovetail_timber_end == TimberReferenceEnd.TOP:
        dovetail_end_position = dovetail_timber.get_top_center_position()
        dovetail_direction = dovetail_timber.length_direction
    else:  # BOTTOM
        dovetail_end_position = dovetail_timber.get_bottom_center_position()
        dovetail_direction = -dovetail_timber.length_direction
    
    # Find which face of the receiving timber the dovetail is approaching
    # The dovetail approaches opposite to its end direction
    receiving_face_for_shoulder = receiving_timber.get_closest_oriented_face(-dovetail_direction)
    
    # Calculate the center position of the receiving face (shoulder surface)
    # For long faces (LEFT, RIGHT, FRONT, BACK), center is at mid-length
    shoulder_face_center = receiving_timber.bottom_position + (receiving_timber.length / Rational(2)) * receiving_timber.length_direction
    
    # Offset to the face surface
    if receiving_face_for_shoulder == TimberFace.RIGHT:
        shoulder_face_center = shoulder_face_center + (receiving_timber.size[0] / Rational(2)) * receiving_timber.width_direction
    elif receiving_face_for_shoulder == TimberFace.LEFT:
        shoulder_face_center = shoulder_face_center - (receiving_timber.size[0] / Rational(2)) * receiving_timber.width_direction
    elif receiving_face_for_shoulder == TimberFace.FRONT:
        shoulder_face_center = shoulder_face_center + (receiving_timber.size[1] / Rational(2)) * receiving_timber.height_direction
    elif receiving_face_for_shoulder == TimberFace.BACK:
        shoulder_face_center = shoulder_face_center - (receiving_timber.size[1] / Rational(2)) * receiving_timber.height_direction
    # For TOP/BOTTOM faces (shouldn't happen for orthogonal butt joints, but handle it)
    elif receiving_face_for_shoulder == TimberFace.TOP:
        shoulder_face_center = receiving_timber.get_top_center_position()
    else:  # BOTTOM
        shoulder_face_center = receiving_timber.get_bottom_center_position()
    
    # Calculate distance from dovetail timber's bottom to the shoulder surface
    distance_from_dovetail_bottom_to_shoulder = (
        (shoulder_face_center - dovetail_timber.bottom_position).T 
        * dovetail_timber.length_direction
    )[0, 0]
    
    # Calculate distance from the specified end to the shoulder (for the cuts)
    if dovetail_timber_end == TimberReferenceEnd.TOP:
        distance_from_end_to_shoulder = dovetail_timber.length - distance_from_dovetail_bottom_to_shoulder
    else:  # BOTTOM
        distance_from_end_to_shoulder = distance_from_dovetail_bottom_to_shoulder
    
    # The dovetail extends `dovetail_length` from the shoulder surface
    # So we cut back to: shoulder_distance + dovetail_length
    distance_from_end_to_cut = distance_from_end_to_shoulder + dovetail_length
    
    # Create a prism to remove everything beyond the dovetail
    dovetail_end_prism = chop_timber_end_with_prism(
        timber=dovetail_timber,
        end=dovetail_timber_end,
        distance_from_end_to_cut=distance_from_end_to_cut
    )
    
    # The dovetail tenon is: end_prism MINUS dovetail_profile
    # This creates a positive dovetail tenon shape
    dovetail_tenon_csg = Difference(dovetail_end_prism, [dovetail_profile_csg])
    
    # Distance along receiving timber from its bottom to the shoulder surface
    # (We already calculated shoulder_face_center above)
    distance_along_receiving = (
        (shoulder_face_center - receiving_timber.bottom_position).T 
        * receiving_timber.length_direction
    )[0, 0]
    
    # ========================================================================
    # Cut shoulder notch on receiving timber
    # ========================================================================
    
    # The shoulder notch is where the dovetail timber's body sits
    # It should be inset by receiving_timber_shoulder_inset
    # The notch should match the dovetail timber's cross-section
    
    # Determine which face of the receiving timber to notch
    # This is the face that opposes the dovetail timber face direction
    dovetail_face_direction = dovetail_timber.get_face_direction(dovetail_timber_end.to_timber_face())
    receiving_notch_face = receiving_timber.get_closest_oriented_face(-dovetail_face_direction)
    print(f"receiving_notch_face: {receiving_notch_face}")
    
    # Width of the shoulder notch is the width of the dovetail timber perpendicular to dovetail face
    face_enum = TimberFace(dovetail_timber_face.value)
    if face_enum == TimberFace.LEFT or face_enum == TimberFace.RIGHT:
        # Dovetail is on a width face, so shoulder width is the height
        shoulder_notch_width = dovetail_timber.size[1]
    else:  # FRONT or BACK
        # Dovetail is on a height face, so shoulder width is the width
        shoulder_notch_width = dovetail_timber.size[0]
    
    # Create the shoulder notch
    shoulder_notch_csg = chop_shoulder_notch_on_timber_face(
        timber=receiving_timber,
        notch_face=receiving_notch_face,
        distance_along_timber=distance_along_receiving,
        notch_width=shoulder_notch_width,
        notch_depth=receiving_timber_shoulder_inset
    )
    
    # ========================================================================
    # Adopt the dovetail socket CSG to the receiving timber
    # ========================================================================
    
    # The dovetail profile CSG needs to be transformed from dovetail timber coords
    # to receiving timber coords to create the socket
    dovetail_socket_csg = adopt_csg(dovetail_timber, receiving_timber, dovetail_profile_csg)
    
    # Combine shoulder notch and dovetail socket
    receiving_timber_combined_csg = CSGUnion([shoulder_notch_csg, dovetail_socket_csg])
    
    # ========================================================================
    # Create CSGCut objects for each timber
    # ========================================================================
    
    dovetail_timber_cut_obj = CSGCut(
        timber=dovetail_timber,
        transform=Transform.identity(),
        maybe_end_cut=dovetail_timber_end,
        negative_csg=dovetail_tenon_csg
    )
    
    receiving_timber_cut_obj = CSGCut(
        timber=receiving_timber,
        transform=Transform.identity(),
        maybe_end_cut=None,  # No end cut on receiving timber
        negative_csg=receiving_timber_combined_csg
    )
    
    # Create CutTimber objects
    dovetail_timber_cut = CutTimber(
        timber=dovetail_timber,
        cuts=[dovetail_timber_cut_obj]
    )
    
    receiving_timber_cut = CutTimber(
        timber=receiving_timber,
        cuts=[receiving_timber_cut_obj]
    )
    
    return Joint(
        cut_timbers={
            dovetail_timber.name: dovetail_timber_cut,
            receiving_timber.name: receiving_timber_cut
        },
        jointAccessories={}
    )



# ============================================================================
# Aliases for Japanese joint functions
# ============================================================================

cut_腰掛鎌継ぎ = cut_lapped_gooseneck_joint
cut_koshikake_kama_tsugi = cut_lapped_gooseneck_joint

cut_蟻仕口 = cut_lapped_dovetail_butt_joint
cut_ari_shiguchi = cut_lapped_dovetail_butt_joint