"""
Oscar's Shed - A simple timber frame shed structure
Built using the GiraffeCAD API
"""

from sympy import Rational
import sys
sys.path.append('..')

from giraffe import (
    create_vector2d, create_vector3d,
    create_horizontal_timber_on_footprint,
    create_vertical_timber_on_footprint_side,
    join_timbers,
    cut_basic_miter_joint,
    FootprintLocation, CutTimber, Stickout, TimberReferenceEnd
)
from footprint import Footprint

# ============================================================================
# PARAMETERS - Modify these to adjust the shed design
# ============================================================================

# Footprint dimensions (in feet, will convert to meters)
# the "front/back" of the shed is along the X axis (i.e. the front is wider than it is deep)
# the "sides" of the shed are along the Y axis
base_width = 8.0      # Long dimension (X direction)
base_length = 4.0     # Short dimension (Y direction)

# Post parameters
post_inset = 2.5 / 12      # 6 inches = 0.5 feet, inset from corners on long side
post_back_height = 4    # Height of back posts (feet)
post_front_height = 5   # Height of front posts (feet)

# Timber size definitions (in inches)
# Format: (vertical dimension, horizontal depth)
INCH_TO_METERS = 0.0254
small_timber_size = (4 * INCH_TO_METERS, 2.5 * INCH_TO_METERS)   # 4" vertical x 2.5" depth
med_timber_size = (4 * INCH_TO_METERS, 4 * INCH_TO_METERS)       # 4" x 4"
big_timber_size = (6 * INCH_TO_METERS, 4 * INCH_TO_METERS)       # 6" vertical x 4" depth

# Timber dimensions (in meters for consistency with GiraffeCAD defaults)
# Note: 1 foot = 0.3048 meters
FEET_TO_METERS = 0.3048


def create_oscarshed() -> list[CutTimber]:
    """
    Create Oscar's Shed structure.
    
    Returns:
        list[CutTimber]: List of CutTimber objects representing the complete shed
    """
    # Convert dimensions to meters
    base_width_m = base_width * FEET_TO_METERS
    base_length_m = base_length * FEET_TO_METERS
    post_inset_m = post_inset * FEET_TO_METERS
    post_back_height_m = post_back_height * FEET_TO_METERS
    post_front_height_m = post_front_height * FEET_TO_METERS

    # ============================================================================
    # BUILD THE STRUCTURE
    # ============================================================================

    # Create the footprint (rectangular, counter-clockwise from bottom-left)
    footprint_corners = [
        create_vector2d(0, 0),                      # Corner 0: Front-left
        create_vector2d(base_width_m, 0),           # Corner 1: Front-right
        create_vector2d(base_width_m, base_length_m),  # Corner 2: Back-right
        create_vector2d(0, base_length_m)           # Corner 3: Back-left
    ]
    footprint = Footprint(footprint_corners)

    # ============================================================================
    # Create mudsills on all 4 sides (INSIDE the footprint)
    # ============================================================================
    
    mudsill_size = create_vector2d(big_timber_size[0], big_timber_size[1])

    # Front mudsill (corner 0 to corner 1) - along X axis
    # Length is automatically calculated from boundary side
    mudsill_front = create_horizontal_timber_on_footprint(
        footprint, 0, FootprintLocation.INSIDE, mudsill_size
    )
    mudsill_front.name = "Front Mudsill"

    # Right mudsill (corner 1 to corner 2) - along Y axis
    mudsill_right = create_horizontal_timber_on_footprint(
        footprint, 1, FootprintLocation.INSIDE, mudsill_size
    )
    mudsill_right.name = "Right Mudsill"

    # Back mudsill (corner 2 to corner 3) - along X axis
    mudsill_back = create_horizontal_timber_on_footprint(
        footprint, 2, FootprintLocation.INSIDE, mudsill_size
    )
    mudsill_back.name = "Back Mudsill"

    # Left mudsill (corner 3 to corner 0) - along Y axis
    mudsill_left = create_horizontal_timber_on_footprint(
        footprint, 3, FootprintLocation.INSIDE, mudsill_size
    )
    mudsill_left.name = "Left Mudsill"

    # ============================================================================
    # Create miter joints at all four corners of the mudsill rectangle
    # ============================================================================
    
    # Corner 0 (front-left): Front mudsill BOTTOM meets Left mudsill TOP
    # Front mudsill goes from corner 0 to corner 1 (BOTTOM=corner 0, TOP=corner 1)
    # Left mudsill goes from corner 3 to corner 0 (BOTTOM=corner 3, TOP=corner 0)
    joint_corner_0 = cut_basic_miter_joint(
        mudsill_front, TimberReferenceEnd.BOTTOM,
        mudsill_left, TimberReferenceEnd.TOP
    )
    
    # Corner 1 (front-right): Front mudsill TOP meets Right mudsill BOTTOM
    # Front mudsill goes from corner 0 to corner 1 (BOTTOM=corner 0, TOP=corner 1)
    # Right mudsill goes from corner 1 to corner 2 (BOTTOM=corner 1, TOP=corner 2)
    joint_corner_1 = cut_basic_miter_joint(
        mudsill_front, TimberReferenceEnd.TOP,
        mudsill_right, TimberReferenceEnd.BOTTOM
    )
    
    # Corner 2 (back-right): Right mudsill TOP meets Back mudsill BOTTOM
    # Right mudsill goes from corner 1 to corner 2 (BOTTOM=corner 1, TOP=corner 2)
    # Back mudsill goes from corner 2 to corner 3 (BOTTOM=corner 2, TOP=corner 3)
    joint_corner_2 = cut_basic_miter_joint(
        mudsill_right, TimberReferenceEnd.TOP,
        mudsill_back, TimberReferenceEnd.BOTTOM
    )
    
    # Corner 3 (back-left): Back mudsill TOP meets Left mudsill BOTTOM
    # Back mudsill goes from corner 2 to corner 3 (BOTTOM=corner 2, TOP=corner 3)
    # Left mudsill goes from corner 3 to corner 0 (BOTTOM=corner 3, TOP=corner 0)
    joint_corner_3 = cut_basic_miter_joint(
        mudsill_back, TimberReferenceEnd.TOP,
        mudsill_left, TimberReferenceEnd.BOTTOM
    )

    # ============================================================================
    # Create posts at corners (inset 6 inches from corners on long side)
    # ============================================================================

    # Post size: 4" x 4" (med_timber_size)
    post_size = create_vector2d(med_timber_size[0], med_timber_size[1])
    
    # Front-left post (on front boundary side, inset from left corner)
    # Side 0 goes from corner 0 (front-left) to corner 1 (front-right)
    post_front_left = create_vertical_timber_on_footprint_side(
        footprint, 
        side_index=0,
        distance_along_side=post_inset_m,
        length=post_front_height_m,
        location_type=FootprintLocation.INSIDE,
        size=post_size
    )
    post_front_left.name = "Front Left Post"

    # Front-right post (on front boundary side, inset from right corner)
    post_front_right = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=0,
        distance_along_side=base_width_m - post_inset_m,
        length=post_front_height_m,
        location_type=FootprintLocation.INSIDE,
        size=post_size
    )
    post_front_right.name = "Front Right Post"

    # Back-right post (on back boundary side, inset from right corner)
    # Side 2 goes from corner 2 (back-right) to corner 3 (back-left)
    post_back_right = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,
        distance_along_side=post_inset_m,
        length=post_back_height_m,
        location_type=FootprintLocation.INSIDE,
        size=post_size
    )
    post_back_right.name = "Back Right Post"

    # Back-left post (on back boundary side, inset from left corner)
    post_back_left = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,
        distance_along_side=base_width_m - post_inset_m,
        length=post_back_height_m,
        location_type=FootprintLocation.INSIDE,
        size=post_size
    )
    post_back_left.name = "Back Left Post"

    # ============================================================================
    # Create additional back posts for uniform spacing
    # ============================================================================
    
    # Calculate positions for 2 additional back posts
    # We want 4 posts total with uniform spacing between them
    # The outer posts are at post_inset_m and (base_width_m - post_inset_m)
    # Space between outer posts: base_width_m - 2*post_inset_m
    # With 4 posts, there are 3 equal gaps
    
    back_post_spacing = (base_width_m - 2 * post_inset_m) / 3
    
    # Middle-right post (2nd from right)
    post_back_middle_right_position = post_inset_m + back_post_spacing
    
    post_back_middle_right = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,  # Back side
        distance_along_side=post_back_middle_right_position,
        length=post_back_height_m,
        location_type=FootprintLocation.INSIDE,
        size=post_size
    )
    post_back_middle_right.name = "Back Middle-Right Post"
    
    # Middle-left post (3rd from right)
    post_back_middle_left_position = post_inset_m + 2 * back_post_spacing
    
    post_back_middle_left = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,  # Back side
        distance_along_side=post_back_middle_left_position,
        length=post_back_height_m,
        location_type=FootprintLocation.INSIDE,
        size=post_size
    )
    post_back_middle_left.name = "Back Middle-Left Post"

    # ============================================================================
    # Create side girts (running from back to front along the short dimension)
    # ============================================================================
    
    side_girt_size = create_vector2d(med_timber_size[0], med_timber_size[1])

    # Side girt stickout: 1.5 inches on back side, 0 on front side
    side_girt_stickout_back_inches = 1.5
    side_girt_stickout_back_m = side_girt_stickout_back_inches * INCH_TO_METERS
    side_girt_stickout = Stickout(side_girt_stickout_back_m, 0)  # Asymmetric: 1.5" on back, 0 on front
    
    
    # Left side girt (connects back-left post to front-left post)
    # Top of girt aligns with top of back post
    side_girt_left = join_timbers(
        timber1=post_back_left,        # Back post (timber1)
        timber2=post_front_left,       # Front post (timber2)
        location_on_timber1=post_back_height_m,   # At top of back post
        stickout=side_girt_stickout,   # 1.5" stickout on back, none on front
        location_on_timber2=post_back_height_m,    # Same height on front post
        lateral_offset=0.0,       # No lateral offset
        size=side_girt_size
    )
    side_girt_left.name = "Left Side Girt"
    
    # Right side girt (connects back-right post to front-right post)
    side_girt_right = join_timbers(
        timber1=post_back_right,       # Back post (timber1)
        timber2=post_front_right,      # Front post (timber2)
        location_on_timber1=post_back_height_m,   # At top of back post
        stickout=side_girt_stickout,   # 1.5" stickout on back, none on front
        location_on_timber2=post_back_height_m,    # Same height on front post
        lateral_offset=0.0,       # No lateral offset
        size=side_girt_size
    )
    side_girt_right.name = "Right Side Girt"

    # ============================================================================
    # Create front girt (running left to right along the long dimension)
    # ============================================================================
    
    front_girt_size = create_vector2d(med_timber_size[0], med_timber_size[1])
    
    # Front girt is positioned 2 inches below the side girts
    # Side girts attach to front posts at post_back_height_m
    front_girt_drop_inches = 2.0
    front_girt_drop_m = front_girt_drop_inches * INCH_TO_METERS
    front_girt_height_on_posts = post_back_height_m - front_girt_drop_m
    
    # Front girt stickout: symmetric on both ends (left and right)
    front_girt_stickout_inches = 1.5
    front_girt_stickout_m = front_girt_stickout_inches * INCH_TO_METERS
    front_girt_stickout = Stickout.symmetric(front_girt_stickout_m)
    
    # Front girt connects left front post to right front post
    front_girt = join_timbers(
        timber1=post_front_left,       # Left front post (timber1)
        timber2=post_front_right,      # Right front post (timber2)
        location_on_timber1=front_girt_height_on_posts,   # 2" below side girts
        stickout=front_girt_stickout,  # 1.5" stickout on both sides
        location_on_timber2=front_girt_height_on_posts,   # Same height on right post
        lateral_offset=0.0,       # No lateral offset
        size=front_girt_size
    )
    front_girt.name = "Front Girt"

    # ============================================================================
    # Create top plates (running left to right on top of posts)
    # ============================================================================
    
    # Top plate size: 6" x 4" (same as mudsills, 6" vertical)
    top_plate_size = create_vector2d(big_timber_size[0], big_timber_size[1])
    
    # Top plate stickout: 1 foot on each side (symmetric)
    top_plate_stickout_feet = 1.0
    top_plate_stickout_m = top_plate_stickout_feet * FEET_TO_METERS
    top_plate_stickout = Stickout.symmetric(top_plate_stickout_m)
    
    # Front top plate (connects left front post to right front post)
    # Sits on top of the front posts
    top_plate_front = join_timbers(
        timber1=post_front_left,       # Left front post (timber1)
        timber2=post_front_right,      # Right front post (timber2)
        location_on_timber1=post_front_height_m,   # At top of front post
        stickout=top_plate_stickout,   # 1 foot stickout on both sides
        location_on_timber2=post_front_height_m,   # Same height on right post
        lateral_offset=0.0,       # No lateral offset
        size=top_plate_size,
        orientation_width_vector=create_vector3d(0, 0, 1)
    )
    top_plate_front.name = "Front Top Plate"
    
    # Back top plate (connects left back post to right back post)
    # Sits on top of the back posts
    top_plate_back = join_timbers(
        timber1=post_back_left,        # Left back post (timber1)
        timber2=post_back_right,       # Right back post (timber2)
        location_on_timber1=post_back_height_m,    # At top of back post
        stickout=top_plate_stickout,   # 1 foot stickout on both sides
        location_on_timber2=post_back_height_m,    # Same height on right post
        lateral_offset=0.0,       # No lateral offset
        size=top_plate_size,
        orientation_width_vector=create_vector3d(0, 0, 1)
    )
    top_plate_back.name = "Back Top Plate"

    # ============================================================================
    # Create joists (running from front to back, between mudsills)
    # ============================================================================
    
    # Joist size: 4" x 4"
    joist_size = create_vector2d(med_timber_size[0], med_timber_size[1])
    joist_width = med_timber_size[0]
    
    # Calculate spacing: 3 joists with 4 equal gaps (left side, 2 between joists, right side)
    num_joists = 3
    num_gaps = 4
    gap_spacing = (base_width_m - num_joists * joist_width) / num_gaps
    
    # Joist positions along X axis (from left edge, which is where mudsills start)
    joist_positions_along_mudsill = [
        gap_spacing + joist_width / 2,                      # Joist 1
        2 * gap_spacing + 1.5 * joist_width,                # Joist 2
        3 * gap_spacing + 2.5 * joist_width                 # Joist 3
    ]
    
    # No stickout on joists (flush with mudsills)
    joist_stickout = Stickout.nostickout()
    
    # Calculate vertical offset to make joists flush with top of mudsills
    # Top of mudsill = mudsill_centerline + mudsill_height/2
    # Top of joist = joist_centerline + joist_height/2
    # To align tops: joist_offset = (mudsill_height - joist_height) / 2
    mudsill_height = big_timber_size[0]  # 6" vertical
    joist_height = med_timber_size[0]    # 4" vertical
    joist_vertical_offset = (mudsill_height - joist_height) / 2  # = 1"
    
    # Create the 3 joists
    joists = []
    
    for i, location_along_mudsill in enumerate(joist_positions_along_mudsill, start=1):
        # Joists connect from front mudsill to back mudsill
        # Mudsills start at X=0 and run along X axis, so the location is just the X position
        
        joist = join_timbers(
            timber1=mudsill_front,             # Front mudsill (timber1)
            timber2=mudsill_back,              # Back mudsill (timber2)
            location_on_timber1=location_along_mudsill,    # Distance along front mudsill
            stickout=joist_stickout,           # No stickout
            location_on_timber2=mudsill_back.length - location_along_mudsill,    # Reversed distance along back mudsill (measured from opposite end)
            lateral_offset=joist_vertical_offset,     # Offset upward to align tops
            size=joist_size,
            orientation_width_vector=create_vector3d(0, 0, 1)  # Face up
        )
        joist.name = f"Joist {i}"
        joists.append(joist)

    # ============================================================================
    # Create rafters (running from back top plate to front top plate)
    # ============================================================================
    
    # Rafter size: 4" x 4"
    rafter_size = create_vector2d(med_timber_size[0], med_timber_size[1])
    rafter_width = med_timber_size[0]  # Width of rafter (for spacing calculation)
    
    # Calculate positions for 5 rafters with outer faces flush with ends of top plates
    # The centerline of the first rafter is at rafter_width/2
    # The centerline of the last rafter is at (base_width_m - rafter_width/2)
    # Distance between outer rafter centerlines: base_width_m - rafter_width
    # With 5 rafters, there are 4 gaps between centerlines
    
    num_rafters = 5
    rafter_centerline_spacing = (top_plate_front.length - rafter_width) / (num_rafters-1)
    
    # Rafter positions along the top plates (X axis)
    rafter_positions_along_top_plate = []
    for i in range(num_rafters):
        position = rafter_width / 2 + i * rafter_centerline_spacing
        rafter_positions_along_top_plate.append(position)
    
    # No stickout on rafters (flush with top plates)
    rafter_stickout = Stickout.symmetric(12 * INCH_TO_METERS)
    
    # Create the 5 rafters
    rafters = []
    
    for i, location_along_top_plate in enumerate(rafter_positions_along_top_plate, start=1):
        # Rafters connect from back top plate to front top plate
        # Top plates run along X axis, so the location is the X position
        
        rafter = join_timbers(
            timber1=top_plate_back,        # Back top plate (timber1)
            timber2=top_plate_front,       # Front top plate (timber2)
            location_on_timber1=location_along_top_plate,  # Position along back top plate (reversed)
            stickout=rafter_stickout,      # No stickout
            location_on_timber2=location_along_top_plate,  # Same position on front top plate
            lateral_offset=0.0,       # No vertical offset (centerline to centerline)
            size=rafter_size,
            orientation_width_vector=create_vector3d(0, 0, 1)  # Face up
        )
        rafter.name = f"Rafter {i}"
        rafters.append(rafter)
    
    # Offset all rafters upwards by 2 inches
    rafter_vertical_offset_inches = 3.0
    rafter_vertical_offset_m = rafter_vertical_offset_inches * INCH_TO_METERS
    
    for rafter in rafters:
        # Move the rafter up by adding to the Z component of bottom_position
        rafter.bottom_position = create_vector3d(
            rafter.bottom_position[0],
            rafter.bottom_position[1],
            rafter.bottom_position[2] + rafter_vertical_offset_m
        )

    # ============================================================================
    # Wrap all timbers in CutTimber objects and return
    # ============================================================================
    
    cut_timbers = []
    
    # Add mudsills (with miter joints applied)
    # Each mudsill participates in 2 joints (one at each end)
    # We need to collect all cuts for each mudsill and create a single PartiallyCutTimber
    
    # Create PartiallyCutTimbers for each mudsill
    from giraffe import PartiallyCutTimber
    
    pct_mudsill_front = PartiallyCutTimber(mudsill_front, "Front Mudsill")
    pct_mudsill_right = PartiallyCutTimber(mudsill_right, "Right Mudsill")
    pct_mudsill_back = PartiallyCutTimber(mudsill_back, "Back Mudsill")
    pct_mudsill_left = PartiallyCutTimber(mudsill_left, "Left Mudsill")
    
    # Add cuts from joint_corner_0 (Front BOTTOM, Left TOP)
    pct_mudsill_front._cuts.append(joint_corner_0.partiallyCutTimbers[0]._cuts[0])
    pct_mudsill_left._cuts.append(joint_corner_0.partiallyCutTimbers[1]._cuts[0])
    
    # Add cuts from joint_corner_1 (Front TOP, Right BOTTOM)
    pct_mudsill_front._cuts.append(joint_corner_1.partiallyCutTimbers[0]._cuts[0])
    pct_mudsill_right._cuts.append(joint_corner_1.partiallyCutTimbers[1]._cuts[0])
    
    # Add cuts from joint_corner_2 (Right TOP, Back BOTTOM)
    pct_mudsill_right._cuts.append(joint_corner_2.partiallyCutTimbers[0]._cuts[0])
    pct_mudsill_back._cuts.append(joint_corner_2.partiallyCutTimbers[1]._cuts[0])
    
    # Add cuts from joint_corner_3 (Back TOP, Left BOTTOM)
    pct_mudsill_back._cuts.append(joint_corner_3.partiallyCutTimbers[0]._cuts[0])
    pct_mudsill_left._cuts.append(joint_corner_3.partiallyCutTimbers[1]._cuts[0])
    
    # Add the mudsills with all their cuts
    cut_timbers.append(pct_mudsill_front)
    cut_timbers.append(pct_mudsill_right)
    cut_timbers.append(pct_mudsill_back)
    cut_timbers.append(pct_mudsill_left)
    
    # Add posts
    cut_timbers.append(CutTimber(post_front_left))
    cut_timbers.append(CutTimber(post_front_right))
    cut_timbers.append(CutTimber(post_back_right))
    cut_timbers.append(CutTimber(post_back_middle_right))
    cut_timbers.append(CutTimber(post_back_middle_left))
    cut_timbers.append(CutTimber(post_back_left))
    
    # Add side girts
    cut_timbers.append(CutTimber(side_girt_left))
    cut_timbers.append(CutTimber(side_girt_right))
    
    # Add front girt
    cut_timbers.append(CutTimber(front_girt))
    
    # Add top plates
    cut_timbers.append(CutTimber(top_plate_front))
    cut_timbers.append(CutTimber(top_plate_back))
    
    # Add joists
    for joist in joists:
        cut_timbers.append(CutTimber(joist))
    
    # Add rafters
    for rafter in rafters:
        cut_timbers.append(CutTimber(rafter))
    
    return cut_timbers


# ============================================================================
# Main execution (when run as standalone script)
# ============================================================================

if __name__ == "__main__":
    print(f"Creating Oscar's Shed: {base_width} ft x {base_length} ft")
    print(f"  ({base_width * FEET_TO_METERS:.3f} m x {base_length * FEET_TO_METERS:.3f} m)")
    
    cut_timbers = create_oscarshed()
    
    print(f"\nCreated {len(cut_timbers)} timbers:")
    for ct in cut_timbers:
        print(f"  - {ct.timber.name}")
    
    # ============================================================================
    # Summary
    # ============================================================================
    
    print("\n" + "="*60)
    print("OSCAR'S SHED - STRUCTURE SUMMARY")
    print("="*60)
    print(f"Footprint: {base_width} ft x {base_length} ft")
    print(f"Mudsills: 4 (all INSIDE footprint, with miter joints at all 4 corners)")
    print(f"Posts: 6 total")
    print(f"  - Front posts: 2 posts, {post_front_height} ft tall")
    print(f"  - Back posts: 4 posts, {post_back_height} ft tall (uniformly spaced)")
    print(f"  - Post inset: {post_inset} ft from corners (outer posts only)")
    print(f"Side Girts: 2 (running from back to front)")
    print(f"  - Stickout: 1.5 inches on back, 0 on front")
    print(f"Front Girt: 1 (running left to right)")
    print(f"  - Position: 2 inches below side girts")
    print(f"  - Stickout: 1.5 inches on both sides (symmetric)")
    print(f"Top Plates: 2 (one front, one back)")
    print(f"  - Size: 6\" x 4\" (6\" vertical, same as mudsills)")
    print(f"  - Position: On top of posts")
    print(f"  - Stickout: 1 foot on both sides (symmetric)")
    print(f"Joists: 3 (running from front to back between mudsills)")
    print(f"  - Size: 4\" x 4\"")
    print(f"  - Spacing: Evenly spaced with equal gaps")
    print(f"  - Position: Tops flush with tops of mudsills")
    print(f"  - No stickout (flush with mudsills lengthwise)")
    print(f"Rafters: 5 (running from back to front on top plates)")
    print(f"  - Size: 4\" x 4\"")
    print(f"  - Spacing: Uniformly spaced")
    print(f"  - Position: 2 inches above top plates (offset upwards)")
    print(f"  - Outside faces of outer rafters flush with ends of top plates")
    print(f"  - No stickout (flush with top plates lengthwise)")
    print("="*60)

