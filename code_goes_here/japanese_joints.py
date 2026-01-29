"""
GiraffeCAD - Japanese Joint Construction Functions
Contains traditional Japanese timber joint implementations
"""
import warnings

from code_goes_here.timber import *
from code_goes_here.construction import *
from code_goes_here.joint_shavings import *
from code_goes_here.measuring import mark_top_center_position
from code_goes_here.moothymoth import *
from code_goes_here.meowmeowcsg import *

# Aliases for backwards compatibility
CSGUnion = SolidUnion


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
    gooseneck_timber_face: TimberLongFace,
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
    opposing_face = gooseneck_timber.get_closest_oriented_face_from_global_direction(
        -receiving_timber.get_face_direction_global(receiving_timber_end)
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
    gooseneck_direction_global = -receiving_timber.get_face_direction_global(receiving_timber_end)
    gooseneck_lateral_offset_direction_global = receiving_timber.get_face_direction_global(gooseneck_timber_face.rotate_right())

    # Get the receiving timber end position
    if receiving_timber_end == TimberReferenceEnd.TOP:
        receiving_timber_end_position_global = mark_top_center_position(receiving_timber).position
    else:  # BOTTOM
        receiving_timber_end_position_global = receiving_timber.get_bottom_position_global()
    
    # Move from the receiving timber end by gooseneck_length (inward) to get the gooseneck starting position
    gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global = receiving_timber_end_position_global + gooseneck_direction_global * lap_length + gooseneck_lateral_offset_direction_global * gooseneck_lateral_offset

    # project gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global onto the gooseneck_timber_face
    gooseneck_starting_position_global = receiving_timber.project_global_point_onto_timber_face_global(gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global, gooseneck_timber_face)
    gooseneck_drawing_normal_global = gooseneck_timber.get_face_direction_global(gooseneck_timber_face)

    # now cut the gooseneck shape into the gooseneck_timber
    gooseneck_shape = draw_gooseneck_polygon(gooseneck_length, gooseneck_small_width, gooseneck_large_width, gooseneck_head_length)

    # ========================================================================
    # Determine gooseneck depth default
    # ========================================================================
    
    if gooseneck_depth is None:
        # Default to half the dimension perpendicular to the specified face
        gooseneck_depth = gooseneck_timber.get_size_in_face_normal_axis(
            gooseneck_timber_face.to.face()
        ) / 2

    # ========================================================================
    # Calculate lap positions and depths
    # ========================================================================
    
    # Extract the length component from gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global
    # This gives us the distance from the receiving timber's bottom position along its length axis
    gooseneck_starting_position_on_receiving_timber = (
        (gooseneck_starting_position_on_receiving_timber_centerline_with_lateral_offset_global - receiving_timber.get_bottom_position_global()).T 
        * receiving_timber.get_length_direction_global()
    )[0, 0]
    
    # Compute lap end position: move by lap_length in the direction away from receiving timber end
    # (opposite of gooseneck_direction_global, which points inward from the end)
    lap_direction = -gooseneck_direction_global
    lap_end_position_on_receiving_timber = gooseneck_starting_position_on_receiving_timber + lap_length
    
    # Compute gooseneck depth relative to the opposing face on the receiving timber
    # This accounts for any offset or rotation between the timbers
    receiving_timber_lap_depth = scribe_distance_from_face_on_timber_wrt_opposing_face_on_another_timber(
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
    receiving_timber_lap_face_direction = -gooseneck_timber.get_face_direction_global(gooseneck_timber_face)
    receiving_timber_lap_face = receiving_timber.get_closest_oriented_face_from_global_direction(receiving_timber_lap_face_direction)
    
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
        (gooseneck_lap_start_global - gooseneck_timber.get_bottom_position_global()).T 
        * gooseneck_timber.get_length_direction_global()
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
    
    # Create the gooseneck profile CSG cut using chop_profile_on_timber_face
    # This creates a CSG that removes the gooseneck shape from the timber
    gooseneck_profile_csg = chop_profile_on_timber_face(
        timber=gooseneck_timber,
        end=gooseneck_timber_end,
        face=gooseneck_timber_face.to.face(),
        profile=gooseneck_shape,
        depth=gooseneck_depth,
        profile_y_offset_from_end=-gooseneck_profile_y_position
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
    # Use the generic adopt_csg function to handle all CSG types (SolidUnion, Difference, RectangularPrism, etc.)
    gooseneck_csg_on_receiving_timber = adopt_csg(gooseneck_timber, receiving_timber, gooseneck_profile_csg) 


    
    # Create Cut objects for each timber
    receiving_timber_cut_obj = Cut(
        timber=receiving_timber,
        transform=Transform.identity(), 
        maybe_end_cut=receiving_timber_end,
        negative_csg=CSGUnion([receiving_timber_lap_csg, gooseneck_csg_on_receiving_timber])
    )

    
    gooseneck_timber_cut_obj = Cut(
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
    dovetail_timber_face: TimberLongFace,
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
            f"Got dovetail_timber length_direction: {dovetail_timber.get_length_direction_global().T}, "
            f"receiving_timber length_direction: {receiving_timber.get_length_direction_global().T}"
        )

    # Assert timbers are face aligned
    if not are_timbers_face_aligned(dovetail_timber, receiving_timber):
        raise ValueError(
            "Timbers must be face-aligned for dovetail butt joint. "
        )


    # assert that dovetail_timber_face is perpendicular to receiving_timber.get_length_direction_global()
    if are_vectors_parallel(dovetail_timber.get_face_direction_global(dovetail_timber_face), receiving_timber.get_length_direction_global()):
        raise ValueError(
            "Dovetail timber face must be perpendicular to receiving timber length direction for dovetail butt joint. "
            "The face should be oriented such that the dovetail profile is visible when looking along the receiving timber. "
            "Try rotating the dovetail face by 90 degrees. "
            f"Got dovetail_timber_face direction: {dovetail_timber.get_face_direction_global(dovetail_timber_face).T}, "
            f"receiving_timber length_direction: {receiving_timber.get_length_direction_global().T}"
        )
    
    # ========================================================================
    # Calculate default depth if not provided
    # ========================================================================
    
    if dovetail_depth is None:
        # Default: half the timber dimension perpendicular to the dovetail face
        dovetail_depth = dovetail_timber.get_size_in_face_normal_axis(dovetail_timber_face.to.face()) / Rational(2)
    
    # ========================================================================
    # Create the dovetail profile (simple trapezoid)
    # TODO move into separate function
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
    # create the marking transform
    # it is on the centerline of the dovetail face where it intersects the inset shoulder of the mortise timber
    # ========================================================================

    receiving_timber_shoulder_face = receiving_timber.get_closest_oriented_face_from_global_direction(-dovetail_timber.get_face_direction_global(dovetail_timber_end.to.face()))
    shoulder_distance_from_end = scribe_face_plane_onto_centerline(
        face=receiving_timber_shoulder_face,
        face_timber=receiving_timber,
        to_timber=dovetail_timber,
        to_timber_end=dovetail_timber_end
    ) - receiving_timber_shoulder_inset

    offset_to_dovetail_face = dovetail_timber.get_size_in_face_normal_axis(dovetail_timber_face) / Rational(2) * dovetail_timber.get_face_direction_global(dovetail_timber_face)
    
    marking_transform_position = dovetail_timber.get_bottom_position_global() + shoulder_distance_from_end * dovetail_timber.get_length_direction_global() + offset_to_dovetail_face
    marking_transform_orientation = orientation_pointing_towards_face_sitting_on_face(towards_face=dovetail_timber_end.to.face(), sitting_face=dovetail_timber_face.to.face())
    dovetail_timber_marking_transform = Transform(position=marking_transform_position, orientation=marking_transform_orientation)


    # ========================================================================
    # Cut dovetail shape into dovetail timber
    # ========================================================================
    
    # Create the dovetail profile CSG using chop_profile_on_timber_face
    # This creates the profile extrusion
    dovetail_profile_csg = chop_profile_on_timber_face(
        timber=dovetail_timber,
        end=dovetail_timber_end,
        face=dovetail_timber_face.to.face(),
        profile=dovetail_profile,
        depth=dovetail_depth,
        profile_y_offset_from_end=shoulder_distance_from_end
    )

    # dovetail housing prism
    dovetail_housing_prism = chop_timber_end_with_prism(
        timber=dovetail_timber,
        end=dovetail_timber_end,
        distance_from_end_to_cut=shoulder_distance_from_end
    )
    
    # ========================================================================
    # Cut shoulder notch on receiving timber
    # ========================================================================
    
    # Calculate where along the receiving timber the shoulder should be
    (_, receiving_timber_notch_center) = scribe_centerline_onto_centerline(dovetail_timber, receiving_timber)
    
    # Create shoulder notch if inset is specified
    if receiving_timber_shoulder_inset > 0:
        # Notch dimensions match the dovetail timber's cross-section at the housing
        # Width is the length of the housing (shoulder_distance_from_end on dovetail timber)
        notch_width = dovetail_timber.get_size_in_face_normal_axis(dovetail_timber_face.rotate_right().to.face())
        
        # Depth is the amount of inset
        notch_depth = receiving_timber_shoulder_inset
        
        receiving_timber_shoulder_notch = chop_shoulder_notch_on_timber_face(
            timber=receiving_timber,
            notch_face=receiving_timber_shoulder_face,
            distance_along_timber=receiving_timber_notch_center,
            notch_width=notch_width,
            notch_depth=notch_depth
        )
    
    # ========================================================================
    # Adopt the dovetail socket CSG to the receiving timber
    # ========================================================================
    
    # Transform the dovetail profile CSG from dovetail_timber coordinates to receiving_timber coordinates
    dovetail_socket_csg = adopt_csg(dovetail_timber, receiving_timber, dovetail_profile_csg)
    
    # ========================================================================
    # Create Cut objects for each timber
    # ========================================================================
    
    dovetail_timber_cut_obj = Cut(
        timber=dovetail_timber,
        transform=Transform.identity(),
        maybe_end_cut=dovetail_timber_end,
        negative_csg=Difference(dovetail_housing_prism, [dovetail_profile_csg])
    )
    
    # Combine shoulder notch and dovetail socket if shoulder inset is specified
    if receiving_timber_shoulder_inset > 0:
        receiving_timber_negative_csg = CSGUnion([receiving_timber_shoulder_notch, dovetail_socket_csg])
    else:
        receiving_timber_negative_csg = dovetail_socket_csg
    
    receiving_timber_cut_obj = Cut(
        timber=receiving_timber,
        transform=Transform.identity(),
        maybe_end_cut=None,  # No end cut on receiving timber
        negative_csg=receiving_timber_negative_csg
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