"""
Tiny House 120 sqft - A 15' x 8' timber frame tiny house
Posts are on the INSIDE of the footprint. Front is the 15' side.
"""

from sympy import Rational, Integer, sqrt
from typing import Optional

from giraffe import *
from code_goes_here.timber import Frame
from code_goes_here.patternbook import PatternBook, PatternMetadata

# ============================================================================
# PARAMETERS
# ============================================================================

# Footprint dimensions
# Front/back is 15' along X axis, sides are 8' along Y axis
house_width = feet(15)    # X direction (front/back)
house_depth = feet(8)     # Y direction (sides)

# Lumber sizes (nominal -> actual: 3.5" x 3.5" and 3.5" x 5.5")
size_4x4 = create_v2(inches(Rational(7, 2)), inches(Rational(7, 2)))
size_4x6 = create_v2(inches(Rational(7, 2)), inches(Rational(11, 2)))

# Post parameters
post_size = size_4x4
corner_post_height = feet(11)

# Beam parameters — all horizontal members are 4x6 with 6" (5.5") in Z
# With orientation_width_vector=(0,0,1), size[0] maps to Z axis
beam_size = create_v2(inches(Rational(11, 2)), inches(Rational(7, 2)))  # 5.5" in Z, 3.5" across
bottom_beam_height = inches(6)   # Bottom of beam at 6" above ground
mid_beam_height = feet(7)        # Mid-height perimeter beam at 7'
top_plate_height = feet(11)      # Top plates at 11'

# Non-corner posts reach the top of the mid-height beam (7' + 5.5")
non_corner_post_height = mid_beam_height + beam_size[0]



def create_tinyhouse120_patternbook() -> PatternBook:
    patterns = [
        (PatternMetadata("tinyhouse120", ["tinyhouse", "complete_structures"], "frame"),
         lambda center: create_tinyhouse120(center=center)),
    ]
    return PatternBook(patterns=patterns)


patternbook = create_tinyhouse120_patternbook()


def create_tinyhouse120(center: Optional[V3] = None):
    """
    Create a 120 sqft tiny house frame (15' x 8').
    No joints yet — just timbers placed in position.
    """
    if center is None:
        center = create_v3(Rational(0), Rational(0), Rational(0))

    # ========================================================================
    # FOOTPRINT (counter-clockwise from front-left)
    # ========================================================================
    footprint_corners = [
        create_v2(center[0] + Rational(0), center[1] + Rational(0)),          # Corner 0: Front-left
        create_v2(center[0] + house_width, center[1] + Rational(0)),          # Corner 1: Front-right
        create_v2(center[0] + house_width, center[1] + house_depth),          # Corner 2: Back-right
        create_v2(center[0] + Rational(0), center[1] + house_depth),          # Corner 3: Back-left
    ]
    footprint = Footprint(footprint_corners)  # type: ignore[arg-type]

    # ========================================================================
    # POSTS — 4 columns (along 15' front/back) x 3 rows (along 8' sides)
    #
    # Layout (top view, Y points into screen):
    #
    #   Back (side 2):   BL ------- BM1 ------ BM2 ------- BR
    #                     |                                  |
    #   Left (side 3):  ML                                  MR  :Right (side 1)
    #                     |                                  |
    #   Front (side 0):  FL ------- FM1 ------ FM2 ------- FR
    #
    # 4 posts on 15' sides: evenly spaced (at corners + 2 intermediate)
    # 3 posts on 8' sides: at corners + 1 intermediate (middle)
    # ========================================================================

    # Spacing for 4 posts on 15' side: corners at ends, so 3 equal gaps
    front_back_spacing = house_width / Integer(3)
    # Spacing for 3 posts on 8' side: corners at ends, so 2 equal gaps
    side_spacing = house_depth / Integer(2)

    # --- Corner posts (11' tall) ---
    post_FL = create_vertical_timber_on_footprint_corner(
        footprint, corner_index=0, length=corner_post_height,
        location_type=FootprintLocation.INSIDE, size=post_size,
        ticket="Front-Left Corner Post"
    )
    post_FR = create_vertical_timber_on_footprint_corner(
        footprint, corner_index=1, length=corner_post_height,
        location_type=FootprintLocation.INSIDE, size=post_size,
        ticket="Front-Right Corner Post"
    )
    post_BR = create_vertical_timber_on_footprint_corner(
        footprint, corner_index=2, length=corner_post_height,
        location_type=FootprintLocation.INSIDE, size=post_size,
        ticket="Back-Right Corner Post"
    )
    post_BL = create_vertical_timber_on_footprint_corner(
        footprint, corner_index=3, length=corner_post_height,
        location_type=FootprintLocation.INSIDE, size=post_size,
        ticket="Back-Left Corner Post"
    )

    # --- Front intermediate posts (8' tall) ---
    # Side 0 goes from corner 0 (FL) to corner 1 (FR)
    post_FM1 = create_vertical_timber_on_footprint_side(
        footprint, side_index=0, distance_along_side=front_back_spacing,
        length=non_corner_post_height, location_type=FootprintLocation.INSIDE,
        size=post_size, ticket="Front-Middle-Left Post"
    )
    post_FM2 = create_vertical_timber_on_footprint_side(
        footprint, side_index=0, distance_along_side=Integer(2) * front_back_spacing,
        length=non_corner_post_height, location_type=FootprintLocation.INSIDE,
        size=post_size, ticket="Front-Middle-Right Post"
    )

    # --- Back intermediate posts (8' tall) ---
    # Side 2 goes from corner 2 (BR) to corner 3 (BL)
    # distance_along_side is measured from corner 2 (BR)
    post_BM1 = create_vertical_timber_on_footprint_side(
        footprint, side_index=2, distance_along_side=front_back_spacing,
        length=non_corner_post_height, location_type=FootprintLocation.INSIDE,
        size=post_size, ticket="Back-Middle-Right Post"
    )
    post_BM2 = create_vertical_timber_on_footprint_side(
        footprint, side_index=2, distance_along_side=Integer(2) * front_back_spacing,
        length=non_corner_post_height, location_type=FootprintLocation.INSIDE,
        size=post_size, ticket="Back-Middle-Left Post"
    )

    # --- Side intermediate posts (8' tall, middle of 8' sides) ---
    # Side 1 goes from corner 1 (FR) to corner 2 (BR)
    post_MR = create_vertical_timber_on_footprint_side(
        footprint, side_index=1, distance_along_side=side_spacing,
        length=non_corner_post_height, location_type=FootprintLocation.INSIDE,
        size=post_size, ticket="Right-Middle Post"
    )
    # Side 3 goes from corner 3 (BL) to corner 0 (FL)
    post_ML = create_vertical_timber_on_footprint_side(
        footprint, side_index=3, distance_along_side=side_spacing,
        length=non_corner_post_height, location_type=FootprintLocation.INSIDE,
        size=post_size, ticket="Left-Middle Post"
    )

    # Collect all posts for convenience
    all_posts = [
        post_FL, post_FM1, post_FM2, post_FR,
        post_MR,
        post_BR, post_BM1, post_BM2, post_BL,
        post_ML,
    ]

    # ========================================================================
    # BOTTOM PERIMETER BEAMS — 4x6 connecting each post to its neighbor
    # around the perimeter, bottom of beam at 6" above ground.
    # 6" dimension (5.5" actual) in +Z direction.
    #
    # location_on_timber = height from post bottom where beam centerline is.
    # Beam is 5.5" tall, bottom at 6" means centerline at 6" + 5.5"/2 = 8.75"
    # ========================================================================
    beam_centerline_height = bottom_beam_height + beam_size[0] / Integer(2)

    # Front perimeter: FL -> FM1 -> FM2 -> FR
    beam_front_1 = join_timbers(
        timber1=post_FL, timber2=post_FM1,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Front Bottom Beam 1"
    )
    beam_front_2 = join_timbers(
        timber1=post_FM1, timber2=post_FM2,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Front Bottom Beam 2"
    )
    beam_front_3 = join_timbers(
        timber1=post_FM2, timber2=post_FR,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Front Bottom Beam 3"
    )

    # Right perimeter: FR -> MR -> BR
    beam_right_1 = join_timbers(
        timber1=post_FR, timber2=post_MR,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Right Bottom Beam 1"
    )
    beam_right_2 = join_timbers(
        timber1=post_MR, timber2=post_BR,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Right Bottom Beam 2"
    )

    # Back perimeter: BR -> BM1 -> BM2 -> BL
    beam_back_1 = join_timbers(
        timber1=post_BR, timber2=post_BM1,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Back Bottom Beam 1"
    )
    beam_back_2 = join_timbers(
        timber1=post_BM1, timber2=post_BM2,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Back Bottom Beam 2"
    )
    beam_back_3 = join_timbers(
        timber1=post_BM2, timber2=post_BL,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Back Bottom Beam 3"
    )

    # Left perimeter: BL -> ML -> FL
    beam_left_1 = join_timbers(
        timber1=post_BL, timber2=post_ML,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Left Bottom Beam 1"
    )
    beam_left_2 = join_timbers(
        timber1=post_ML, timber2=post_FL,
        location_on_timber1=beam_centerline_height,
        location_on_timber2=beam_centerline_height,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Left Bottom Beam 2"
    )

    # ========================================================================
    # FLOOR JOISTS — join_timbers front-to-back, using beam segment midpoints.
    # - FM1<->FM2 zone uses beam_front_2 midpoint
    # - Also connect midpoints of beam_front_1/2/3 to corresponding back beams
    #   (back segments are reversed in X: 1<->3, 2<->2, 3<->1).
    # ========================================================================
    floor_joist_1 = join_timbers(
        timber1=beam_front_1,
        timber2=beam_back_3,
        location_on_timber1=beam_front_1.length / Integer(2),
        location_on_timber2=beam_back_3.length / Integer(2),
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Floor Joist 1",
    )
    floor_joist_2 = join_timbers(
        timber1=beam_front_2,
        timber2=beam_back_2,
        location_on_timber1=beam_front_2.length / Integer(2),
        location_on_timber2=beam_back_2.length / Integer(2),
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Floor Joist 2",
    )
    floor_joist_3 = join_timbers(
        timber1=beam_front_3,
        timber2=beam_back_1,
        location_on_timber1=beam_front_3.length / Integer(2),
        location_on_timber2=beam_back_1.length / Integer(2),
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Floor Joist 3",
    )
    floor_joist_4 = join_timbers(
        timber1=beam_front_2,
        timber2=beam_back_2,
        location_on_timber1=Integer(0),
        location_on_timber2=beam_back_2.length,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Floor Joist FM1-BM",
    )
    floor_joist_5 = join_timbers(
        timber1=beam_front_2,
        timber2=beam_back_2,
        location_on_timber1=beam_front_2.length,
        location_on_timber2=Integer(0),
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Floor Joist FM2-BM",
    )

    floor_joists = [floor_joist_1, floor_joist_2, floor_joist_3, floor_joist_4, floor_joist_5]

    # ========================================================================
    # MID-HEIGHT PERIMETER BEAM at 7' — connects corner posts only
    # ========================================================================
    mid_beam_centerline = mid_beam_height + beam_size[0] / Integer(2)

    mid_beam_front = join_timbers(
        timber1=post_FL, timber2=post_FR,
        location_on_timber1=mid_beam_centerline,
        location_on_timber2=mid_beam_centerline,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Mid-Height Front Beam"
    )
    mid_beam_right = join_timbers(
        timber1=post_FR, timber2=post_BR,
        location_on_timber1=mid_beam_centerline,
        location_on_timber2=mid_beam_centerline,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Mid-Height Right Beam"
    )
    mid_beam_back = join_timbers(
        timber1=post_BR, timber2=post_BL,
        location_on_timber1=mid_beam_centerline,
        location_on_timber2=mid_beam_centerline,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Mid-Height Back Beam"
    )
    mid_beam_left = join_timbers(
        timber1=post_BL, timber2=post_FL,
        location_on_timber1=mid_beam_centerline,
        location_on_timber2=mid_beam_centerline,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Mid-Height Left Beam"
    )

    # ========================================================================
    # LOFT BEAMS — 2 beams connecting front/back mid-height beams, aligned with
    # FM1/FM2 (and corresponding BM intersections).
    # ========================================================================
    loft_beam_front_pos_1 = beam_front_1.length
    loft_beam_front_pos_2 = beam_front_1.length + beam_front_2.length

    # mid_beam_back runs in opposite X direction (BR -> BL), so mirror positions
    loft_beam_back_pos_1 = mid_beam_back.length - loft_beam_front_pos_1
    loft_beam_back_pos_2 = mid_beam_back.length - loft_beam_front_pos_2

    loft_beam_1 = join_timbers(
        timber1=mid_beam_front,
        timber2=mid_beam_back,
        location_on_timber1=loft_beam_front_pos_1,
        location_on_timber2=loft_beam_back_pos_1,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Loft Beam FM1-BM"
    )
    loft_beam_2 = join_timbers(
        timber1=mid_beam_front,
        timber2=mid_beam_back,
        location_on_timber1=loft_beam_front_pos_2,
        location_on_timber2=loft_beam_back_pos_2,
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Loft Beam FM2-BM"
    )

    # ========================================================================
    # TOP PLATES at 11'
    #
    # First layer: front-to-back plates connecting FL->BL and FR->BR
    #   at 11' (top of corner posts), with 6" stickout
    #   4x6 with 6" in +Z
    #
    # Second layer: left-to-right plates connecting FL->FR and BL->BR
    #   3" above the first layer (i.e. at 11' + 5.5" + 3")
    #   sitting on TOP of the first layer plates
    # ========================================================================
    top_plate_size = beam_size

    # First layer: front-to-back (along Y axis), 6" stickout on both ends
    top_plate_stickout = Stickout.symmetric(inches(6))

    top_plate_left = join_timbers(
        timber1=post_FL, timber2=post_BL,
        location_on_timber1=top_plate_height,
        location_on_timber2=top_plate_height,
        stickout=top_plate_stickout,
        size=top_plate_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Top Plate Left (Front-to-Back)"
    )
    top_plate_right = join_timbers(
        timber1=post_FR, timber2=post_BR,
        location_on_timber1=top_plate_height,
        location_on_timber2=top_plate_height,
        stickout=top_plate_stickout,
        size=top_plate_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Top Plate Right (Front-to-Back)"
    )

    # Second layer: left-to-right (along X axis)
    # Sits on top of F/B plates with 3" overlap into the F/B plates.
    # F/B plate top = top_plate_height + 5.5"/2
    # L/R plate bottom = F/B plate top - 3"
    # L/R plate centerline = L/R plate bottom + 5.5"/2
    second_plate_centerline = (top_plate_height + top_plate_size[0] / Integer(2)) - inches(3) + top_plate_size[0] / Integer(2)

    top_plate_front = join_timbers(
        timber1=post_FL, timber2=post_FR,
        location_on_timber1=second_plate_centerline,
        location_on_timber2=second_plate_centerline,
        stickout=top_plate_stickout,
        size=top_plate_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Top Plate Front (Left-to-Right)"
    )
    top_plate_back = join_timbers(
        timber1=post_BL, timber2=post_BR,
        location_on_timber1=second_plate_centerline,
        location_on_timber2=second_plate_centerline,
        stickout=top_plate_stickout,
        size=top_plate_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Top Plate Back (Left-to-Right)"
    )

    # ========================================================================
    # LOWER WALL STUDS — vertical 4x4 posts via join_timbers
    # from bottom beam spans up to the mid-height perimeter beams.
    # ========================================================================
    lower_stud_front_1 = join_timbers(
        timber1=beam_front_1, timber2=mid_beam_front,
        location_on_timber1=beam_front_1.length / Integer(2),
        location_on_timber2=beam_front_1.length / Integer(2),
        size=post_size,
        ticket="Front Lower Stud 1"
    )
    lower_stud_front_3 = join_timbers(
        timber1=beam_front_3, timber2=mid_beam_front,
        location_on_timber1=beam_front_3.length / Integer(2),
        location_on_timber2=beam_front_1.length + beam_front_2.length + beam_front_3.length / Integer(2),
        size=post_size,
        ticket="Front Lower Stud 3"
    )

    # Window members in FM1-FM2 bay (replace middle lower stud)
    window_member_upper = join_timbers(
        timber1=post_FM1, timber2=post_FM2,
        location_on_timber1=non_corner_post_height * Rational(4, 5),
        location_on_timber2=non_corner_post_height * Rational(4, 5),
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Front Window Member Upper"
    )
    window_member_lower = join_timbers(
        timber1=post_FM1, timber2=post_FM2,
        location_on_timber1=non_corner_post_height * Rational(2, 5),
        location_on_timber2=non_corner_post_height * Rational(2, 5),
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Front Window Member Lower"
    )

    lower_stud_right_1 = join_timbers(
        timber1=beam_right_1, timber2=mid_beam_right,
        location_on_timber1=beam_right_1.length / Integer(2),
        location_on_timber2=beam_right_1.length / Integer(2),
        size=post_size,
        ticket="Right Lower Stud 1"
    )
    lower_stud_right_2 = join_timbers(
        timber1=beam_right_2, timber2=mid_beam_right,
        location_on_timber1=beam_right_2.length / Integer(2),
        location_on_timber2=beam_right_1.length + beam_right_2.length / Integer(2),
        size=post_size,
        ticket="Right Lower Stud 2"
    )

    lower_stud_back_1 = join_timbers(
        timber1=beam_back_1, timber2=mid_beam_back,
        location_on_timber1=beam_back_1.length / Integer(2),
        location_on_timber2=beam_back_1.length / Integer(2),
        size=post_size,
        ticket="Back Lower Stud 1"
    )
    lower_stud_back_2 = join_timbers(
        timber1=beam_back_2, timber2=mid_beam_back,
        location_on_timber1=beam_back_2.length / Integer(2),
        location_on_timber2=beam_back_1.length + beam_back_2.length / Integer(2),
        size=post_size,
        ticket="Back Lower Stud 2"
    )
    lower_stud_back_3 = join_timbers(
        timber1=beam_back_3, timber2=mid_beam_back,
        location_on_timber1=beam_back_3.length / Integer(2),
        location_on_timber2=beam_back_1.length + beam_back_2.length + beam_back_3.length / Integer(2),
        size=post_size,
        ticket="Back Lower Stud 3"
    )

    lower_stud_left_1 = join_timbers(
        timber1=beam_left_1, timber2=mid_beam_left,
        location_on_timber1=beam_left_1.length / Integer(2),
        location_on_timber2=beam_left_1.length / Integer(2),
        size=post_size,
        ticket="Left Lower Stud 1"
    )
    lower_stud_left_2 = join_timbers(
        timber1=beam_left_2, timber2=mid_beam_left,
        location_on_timber1=beam_left_2.length / Integer(2),
        location_on_timber2=beam_left_1.length + beam_left_2.length / Integer(2),
        size=post_size,
        ticket="Left Lower Stud 2"
    )

    # ========================================================================
    # UPPER WALL STUDS — vertical 4x4 posts between mid-height beams
    # and top plates, evenly spaced: 4 on F/B sides, 2 on L/R sides.
    #
    # Front/back top plate (second layer) centerline = second_plate_centerline
    # Left/right top plate (first layer) centerline = top_plate_height
    # ========================================================================

    def _lerp_xy(t1, t2, frac, z):
        """Linearly interpolate XY between two posts at fraction frac, at given Z."""
        p1 = t1.get_bottom_position_global()
        p2 = t2.get_bottom_position_global()
        return create_v3(
            p1[0] + (p2[0] - p1[0]) * frac,
            p1[1] + (p2[1] - p1[1]) * frac,
            z,
        )

    # Upper studs via join_timbers. Top plates have 6" symmetric stickout.
    top_plate_stickout_amount = inches(6)

    upper_studs_front = []
    for i in range(1, 5):
        frac = Rational(i, 5)
        upper_studs_front.append(join_timbers(
            timber1=mid_beam_front,
            timber2=top_plate_front,
            location_on_timber1=mid_beam_front.length * frac,
            location_on_timber2=top_plate_stickout_amount + mid_beam_front.length * frac,
            size=post_size,
            ticket=f"Front Upper Stud {i}"
        ))

    upper_studs_back = []
    for i in range(1, 5):
        frac = Rational(i, 5)
        upper_studs_back.append(join_timbers(
            timber1=mid_beam_back,
            timber2=top_plate_back,
            location_on_timber1=mid_beam_back.length * frac,
            location_on_timber2=top_plate_stickout_amount + mid_beam_back.length * (Integer(1) - frac),
            size=post_size,
            ticket=f"Back Upper Stud {i}"
        ))

    upper_studs_right = []
    for i in range(1, 3):
        frac = Rational(i, 3)
        upper_studs_right.append(join_timbers(
            timber1=mid_beam_right,
            timber2=top_plate_right,
            location_on_timber1=mid_beam_right.length * frac,
            location_on_timber2=top_plate_stickout_amount + mid_beam_right.length * frac,
            size=post_size,
            ticket=f"Right Upper Stud {i}"
        ))

    upper_studs_left = []
    for i in range(1, 3):
        frac = Rational(i, 3)
        upper_studs_left.append(join_timbers(
            timber1=mid_beam_left,
            timber2=top_plate_left,
            location_on_timber1=mid_beam_left.length * frac,
            location_on_timber2=top_plate_stickout_amount + mid_beam_left.length * (Integer(1) - frac),
            size=post_size,
            ticket=f"Left Upper Stud {i}"
        ))

    # ========================================================================
    # KING POSTS — on the side (L/R) top plates at their midpoints,
    # supporting the ridge beam at the gable ends.
    # ========================================================================
    king_post_height = feet(Rational(5, 2))
    king_post_bottom_z = top_plate_height + beam_size[0] / Integer(2)  # top of side plates

    king_post_left = create_axis_aligned_timber(
        _lerp_xy(post_FL, post_BL, Rational(1, 2), king_post_bottom_z),
        king_post_height, post_size,
        TimberFace.TOP, ticket="Left King Post"
    )
    king_post_right = create_axis_aligned_timber(
        _lerp_xy(post_FR, post_BR, Rational(1, 2), king_post_bottom_z),
        king_post_height, post_size,
        TimberFace.TOP, ticket="Right King Post"
    )

    # ========================================================================
    # RIDGE BEAM — 16' 4x6 on top of king posts, running along X (the 15' dir)
    # centered on the house with ~6" overhang each side.
    # ========================================================================
    ridge_length = feet(16)
    ridge_bottom_z = king_post_bottom_z + king_post_height  # top of king posts
    ridge_center_x = center[0] + house_width / Integer(2)
    ridge_y = center[1] + house_depth / Integer(2)
    ridge_start_x = ridge_center_x - ridge_length / Integer(2)

    ridge_beam = create_axis_aligned_timber(
        create_v3(ridge_start_x, ridge_y, ridge_bottom_z),
        ridge_length, beam_size,
        TimberFace.RIGHT,  # extends in +X
        ticket="Ridge Beam"
    )

    # ========================================================================
    # CENTER RIDGE SUPPORT
    # - One beam between the midpoints of front/back top plates
    # - One vertical king post from that beam up to the ridge beam
    # ========================================================================
    top_plate_mid_x = top_plate_front.get_bottom_position_global()[0] + top_plate_front.length / Integer(2)
    center_support_beam = join_timbers(
        timber1=top_plate_front,
        timber2=top_plate_back,
        location_on_timber1=top_plate_front.length / Integer(2),
        location_on_timber2=top_plate_back.length / Integer(2),
        size=beam_size,
        orientation_width_vector=create_v3(Integer(0), Integer(0), Integer(1)),
        ticket="Center Ridge Support Beam"
    )

    center_king_post = join_timbers(
        timber1=center_support_beam,
        timber2=ridge_beam,
        location_on_timber1=center_support_beam.length / Integer(2),
        location_on_timber2=ridge_beam.length / Integer(2),
        size=post_size,
        ticket="Center King Post"
    )

    # ========================================================================
    # RAFTERS — 6 sets (12 rafters), evenly spaced along the ridge beam,
    # starting from the very edge. Each set has a front rafter and a back
    # rafter sloping from the ridge down to the F/B top plates.
    # Rafters are 4x4, intersecting ridge and plate by ~1".
    # ========================================================================
    rafter_size = post_size

    # Reference surfaces
    ridge_top_z = ridge_bottom_z + beam_size[0]          # top of ridge beam
    plate_top_z = second_plate_centerline + beam_size[0] / Integer(2)  # top of F/B plates

    # Rafter anchor Z: mostly above each member, with ~1" overlap into it.
    # Since rafter depth is 3.5", centerline should be at top + (3.5"/2 - 1")
    embed_depth = inches(1)
    rafter_vertical_half = rafter_size[0] / Integer(2)
    rafter_ridge_z = ridge_top_z + rafter_vertical_half - embed_depth
    rafter_plate_z = plate_top_z + rafter_vertical_half - embed_depth

    # Extend each rafter by 1' toward the eave side (past the plate),
    # not past the ridge side.
    extra_rafter_length = feet(1)

    # Y positions of front/back plates (from corner post centers)
    front_plate_y = post_FL.get_bottom_position_global()[1]
    back_plate_y = post_BL.get_bottom_position_global()[1]

    rafter_edge_inset = rafter_size[0] / Integer(2)
    usable_rafter_span_x = ridge_length - Integer(2) * rafter_edge_inset

    rafters = []
    for i in range(6):
        x = ridge_start_x + rafter_edge_inset + i * usable_rafter_span_x / Integer(5)

        # Front rafter: from front plate up to ridge
        front_bottom = create_v3(x, front_plate_y, rafter_plate_z)
        front_top = create_v3(x, ridge_y, rafter_ridge_z)
        front_delta = front_top - front_bottom
        front_len = sqrt(front_delta[0]**2 + front_delta[1]**2 + front_delta[2]**2) + extra_rafter_length
        front_dir = normalize_vector(front_delta)
        front_eave_bottom = front_bottom - front_dir * extra_rafter_length
        rafters.append(timber_from_directions(
            length=front_len, size=rafter_size,
            bottom_position=front_eave_bottom,
            length_direction=front_dir,
            width_direction=create_v3(Integer(1), Integer(0), Integer(0)),
            ticket=f"Front Rafter {i + 1}"
        ))

        # Back rafter: from back plate up to ridge
        back_bottom = create_v3(x, back_plate_y, rafter_plate_z)
        back_top = create_v3(x, ridge_y, rafter_ridge_z)
        back_delta = back_top - back_bottom
        back_len = sqrt(back_delta[0]**2 + back_delta[1]**2 + back_delta[2]**2) + extra_rafter_length
        back_dir = normalize_vector(back_delta)
        back_eave_bottom = back_bottom - back_dir * extra_rafter_length
        rafters.append(timber_from_directions(
            length=back_len, size=rafter_size,
            bottom_position=back_eave_bottom,
            length_direction=back_dir,
            width_direction=create_v3(Integer(1), Integer(0), Integer(0)),
            ticket=f"Back Rafter {i + 1}"
        ))

    # ========================================================================
    # COLLECT ALL TIMBERS (no joints yet)
    # ========================================================================
    all_beams = [
        # Bottom perimeter
        beam_front_1, beam_front_2, beam_front_3,
        beam_right_1, beam_right_2,
        beam_back_1, beam_back_2, beam_back_3,
        beam_left_1, beam_left_2,
        # Floor joists
        *floor_joists,
        # Mid-height perimeter
        mid_beam_front, mid_beam_right, mid_beam_back, mid_beam_left,
        # Loft beams
        loft_beam_1, loft_beam_2,
        # Window members
        window_member_upper, window_member_lower,
        # Top plates
        top_plate_left, top_plate_right,
        top_plate_front, top_plate_back,
        # Center support
        center_support_beam,
        # Ridge
        ridge_beam,
    ]

    all_studs = [
        # Lower wall studs
        lower_stud_front_1, lower_stud_front_3,
        lower_stud_right_1, lower_stud_right_2,
        lower_stud_back_1, lower_stud_back_2, lower_stud_back_3,
        lower_stud_left_1, lower_stud_left_2,
        # Upper wall studs
        *upper_studs_front, *upper_studs_back,
        *upper_studs_right, *upper_studs_left,
        # King posts
        king_post_left, king_post_right,
        center_king_post,
    ]

    all_timbers = all_posts + all_beams + all_studs + rafters

    return Frame.from_joints(
        joints=[],
        additional_unjointed_timbers=all_timbers,
        name="Tiny House 120"
    )
