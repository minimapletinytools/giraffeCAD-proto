"""
Oscar's Shed - A simple timber frame shed structure
Built using the GiraffeCAD API
"""

from sympy import Rational
from dataclasses import replace
import sys
sys.path.append('..')

from giraffe import (
    create_vector2d, create_vector3d,
    create_horizontal_timber_on_footprint,
    create_vertical_timber_on_footprint_side,
    join_timbers,
    split_timber,
    cut_basic_miter_joint,
    cut_basic_butt_joint_on_face_aligned_timbers,
    cut_basic_splice_joint_on_aligned_timbers,
    cut_basic_house_joint_DEPRECATED,
    cut_basic_house_joint,
    cut_mortise_and_tenon_joint_on_face_aligned_timbers,
    FootprintLocation, CutTimber, Stickout, TimberReferenceEnd,
    SimplePegParameters, PegShape, TimberReferenceLongFace,
    inches, feet, Rational, Matrix
)
from code_goes_here.footprint import Footprint
from code_goes_here.timber import Frame

# ============================================================================
# PARAMETERS - Modify these to adjust the shed design
# ============================================================================

# Footprint dimensions (using dimensional helpers)
# the "front/back" of the shed is along the X axis (i.e. the front is wider than it is deep)
# the "sides" of the shed are along the Y axis
base_width = feet(8)      # Long dimension (X direction)
base_length = feet(4)     # Short dimension (Y direction)

# Post parameters
post_inset = inches(5)      # 3 inch inset from corners (2 inches is half the width of a 4x4 post so 2+3=5)
post_back_height = feet(4)    # Height of back posts
post_front_height = feet(5)   # Height of front posts

# Timber size definitions using dimensional helpers
# Format: (vertical dimension, horizontal depth)
small_timber_size = (inches(4), inches(Rational(5, 2)))   # 4" vertical x 2.5" depth
med_timber_size = (inches(4), inches(4))                   # 4" x 4"
big_timber_size = (inches(6), inches(4))                   # 6" vertical x 4" depth


def create_oscarshed():
    """
    Create Oscar's Shed structure.
    
    Returns:
        Frame: Frame object containing all cut timbers and accessories for the complete shed
    """
    # Note: Dimensions are already in meters from dimensional helpers
    
    # ============================================================================
    # BUILD THE STRUCTURE
    # ============================================================================

    # Create the footprint (rectangular, counter-clockwise from bottom-left)
    footprint_corners = [
        create_vector2d(Rational(0), Rational(0)),     # Corner 0: Front-left
        create_vector2d(base_width, Rational(0)),      # Corner 1: Front-right
        create_vector2d(base_width, base_length),      # Corner 2: Back-right
        create_vector2d(Rational(0), base_length)      # Corner 3: Back-left
    ]
    footprint = Footprint(footprint_corners)

    # ============================================================================
    # Create mudsills on all 4 sides (INSIDE the footprint)
    # ============================================================================
    
    mudsill_size = create_vector2d(big_timber_size[0], big_timber_size[1])

    # Front mudsill (corner 0 to corner 1) - along X axis
    # Length is automatically calculated from boundary side
    mudsill_front = create_horizontal_timber_on_footprint(
        footprint, 0, FootprintLocation.INSIDE, mudsill_size, name="Front Mudsill"
    )

    # Right mudsill (corner 1 to corner 2) - along Y axis
    mudsill_right = create_horizontal_timber_on_footprint(
        footprint, 1, FootprintLocation.INSIDE, mudsill_size, name="Right Mudsill"
    )

    # Back mudsill (corner 2 to corner 3) - along X axis
    mudsill_back = create_horizontal_timber_on_footprint(
        footprint, 2, FootprintLocation.INSIDE, mudsill_size, name="Back Mudsill"
    )

    # Left mudsill (corner 3 to corner 0) - along Y axis
    mudsill_left = create_horizontal_timber_on_footprint(
        footprint, 3, FootprintLocation.INSIDE, mudsill_size, name="Left Mudsill"
    )

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
        distance_along_side=post_inset,
        length=post_front_height,
        location_type=FootprintLocation.INSIDE,
        size=post_size,
        name="Front Left Post"
    )

    # Front-right post (on front boundary side, inset from right corner)
    post_front_right = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=0,
        distance_along_side=base_width - post_inset,
        length=post_front_height,
        location_type=FootprintLocation.INSIDE,
        size=post_size,
        name="Front Right Post"
    )

    # Back-right post (on back boundary side, inset from right corner)
    # Side 2 goes from corner 2 (back-right) to corner 3 (back-left)
    post_back_right = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,
        distance_along_side=post_inset,
        length=post_back_height,
        location_type=FootprintLocation.INSIDE,
        size=post_size,
        name="Back Right Post"
    )

    # Back-left post (on back boundary side, inset from left corner)
    post_back_left = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,
        distance_along_side=base_width - post_inset,
        length=post_back_height,
        location_type=FootprintLocation.INSIDE,
        size=post_size,
        name="Back Left Post"
    )

    # ============================================================================
    # Create additional back posts for uniform spacing
    # ============================================================================
    
    # Calculate positions for 2 additional back posts
    # We want 4 posts total with uniform spacing between them
    # The outer posts are at post_inset and (base_width - post_inset)
    # Space between outer posts: base_width - 2*post_inset
    # With 4 posts, there are 3 equal gaps
    
    back_post_spacing = (base_width - 2 * post_inset) / 3
    
    # Middle-right post (2nd from right)
    post_back_middle_right_position = post_inset + back_post_spacing
    
    post_back_middle_right = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,  # Back side
        distance_along_side=post_back_middle_right_position,
        length=post_back_height,
        location_type=FootprintLocation.INSIDE,
        size=post_size,
        name="Back Middle-Right Post"
    )
    
    # Middle-left post (3rd from right)
    post_back_middle_left_position = post_inset + 2 * back_post_spacing
    
    post_back_middle_left = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,  # Back side
        distance_along_side=post_back_middle_left_position,
        length=post_back_height,
        location_type=FootprintLocation.INSIDE,
        size=post_size,
        name="Back Middle-Left Post"
    )

    # ============================================================================
    # Create mortise and tenon joints where corner posts meet mudsills
    # ============================================================================
    # Each corner post's bottom end has a tenon that goes into the mudsill
    # Tenon size: 1x2 inches (2" along X axis, 1" along Y axis)
    # Tenon offset: 1" towards center (for clearance from miter joints)
    # Tenon length: 2 inches
    # Mortise depth: 3 inches (through mortise since mudsill is 4" deep)
    
    tenon_size = Matrix([inches(2), inches(1)])  # 2" along X (mudsill direction), 1" along Y
    tenon_length = inches(3)
    mortise_depth = inches(3.5)
    
    # Front-left post (left side, offset +1" towards center/right)
    tenon_offset_left = Matrix([inches(1), Rational(0)])  # +1" in X
    joint_post_front_left = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post_front_left,
        mortise_timber=mudsill_front,
        tenon_end=TimberReferenceEnd.BOTTOM,
        size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        tenon_position=tenon_offset_left
    )
    
    # Front-right post (right side, offset -1" towards center/left)
    tenon_offset_right = Matrix([inches(-1), Rational(0)])  # -1" in X
    joint_post_front_right = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post_front_right,
        mortise_timber=mudsill_front,
        tenon_end=TimberReferenceEnd.BOTTOM,
        size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        tenon_position=tenon_offset_right
    )
    
    # Back-right post (right side, offset -1" towards center/left)
    joint_post_back_right = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post_back_right,
        mortise_timber=mudsill_back,
        tenon_end=TimberReferenceEnd.BOTTOM,
        size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        tenon_position=tenon_offset_left
    )
    
    # Back-left post (left side, offset +1" towards center/right)
    joint_post_back_left = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=post_back_left,
        mortise_timber=mudsill_back,
        tenon_end=TimberReferenceEnd.BOTTOM,
        size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        tenon_position=tenon_offset_right
    )
    
    # ============================================================================
    # Middle posts still use butt joints
    # ============================================================================
    
    # Back middle-right post butts into back mudsill
    joint_post_back_middle_right = cut_basic_butt_joint_on_face_aligned_timbers(
        mudsill_back, post_back_middle_right, TimberReferenceEnd.BOTTOM
    )
    
    # Back middle-left post butts into back mudsill
    joint_post_back_middle_left = cut_basic_butt_joint_on_face_aligned_timbers(
        mudsill_back, post_back_middle_left, TimberReferenceEnd.BOTTOM
    )

    # ============================================================================
    # Create side girts (running from back to front along the short dimension)
    # ============================================================================
    
    side_girt_size = create_vector2d(med_timber_size[0], med_timber_size[1])

    # Side girt stickout: 1.5 inches on back side, 0 on front side
    side_girt_stickout_back = inches(Rational(3, 2))  # 1.5 inches
    side_girt_stickout = Stickout(side_girt_stickout_back, Rational(0))  # Asymmetric: 1.5" on back, 0 on front
    
    
    # Left side girt (connects back-left post to front-left post)
    # Top of girt aligns with top of back post
    side_girt_left = join_timbers(
        timber1=post_back_left,        # Back post (timber1)
        timber2=post_front_left,       # Front post (timber2)
        location_on_timber1=post_back_height,   # At top of back post
        stickout=side_girt_stickout,   # 1.5" stickout on back, none on front
        location_on_timber2=post_back_height,    # Same height on front post
        lateral_offset=0,       # No lateral offset
        size=side_girt_size,
        name="Left Side Girt"
    )
    
    # Right side girt (connects back-right post to front-right post)
    side_girt_right = join_timbers(
        timber1=post_back_right,       # Back post (timber1)
        timber2=post_front_right,      # Front post (timber2)
        location_on_timber1=post_back_height,   # At top of back post
        stickout=side_girt_stickout,   # 1.5" stickout on back, none on front
        location_on_timber2=post_back_height,    # Same height on front post
        lateral_offset=0,       # No lateral offset
        size=side_girt_size,
        name="Right Side Girt"
    )

    # ============================================================================
    # Create mortise and tenon joints where side girts meet front posts
    # ============================================================================
    # Side girts have tenons on the front end (TOP end) that go into the front posts
    # Tenon size: 1" x 2" (1" horizontal, 2" vertical)
    # Tenon length: 3 inches
    # Mortise depth: 3 inches
    # Peg: 5/8" square peg, 1 inch from shoulder, centered
    
    side_girt_tenon_size = Matrix([inches(2), inches(1)])  # 1" horizontal, 2" vertical
    side_girt_tenon_length = inches(3)
    side_girt_mortise_depth = inches(3.5)
    
    # Peg parameters: 5/8" square peg, 1" from shoulder, on centerline
    side_girt_peg_params_left = SimplePegParameters(
        shape=PegShape.SQUARE,
        tenon_face=TimberReferenceLongFace.FRONT,
        peg_positions=[(inches(1), Rational(0))],  # 1" from shoulder, centered
        size=inches(Rational(5, 8)),  # 5/8" square
        depth=inches(Rational(7, 2)),
        tenon_hole_offset=inches(Rational(1, 16))
    )
    # Create right side params by replacing just the tenon_face
    side_girt_peg_params_right = replace(
        side_girt_peg_params_left,
        tenon_face=TimberReferenceLongFace.BACK
    )
    
    # Left side girt TOP end meets front left post
    joint_side_girt_left = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=side_girt_left,
        mortise_timber=post_front_left,
        tenon_end=TimberReferenceEnd.TOP,
        size=side_girt_tenon_size,
        tenon_length=side_girt_tenon_length,
        mortise_depth=side_girt_mortise_depth,
        tenon_position=None,  # Centered
        peg_parameters=side_girt_peg_params_left
    )
    
    # Right side girt TOP end meets front right post
    joint_side_girt_right = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=side_girt_right,
        mortise_timber=post_front_right,
        tenon_end=TimberReferenceEnd.TOP,
        size=side_girt_tenon_size,
        tenon_length=side_girt_tenon_length,
        mortise_depth=side_girt_mortise_depth,
        tenon_position=None,  # Centered
        peg_parameters=side_girt_peg_params_right
    )
    
    # Collect joint accessories (pegs) for rendering
    # Accessories are already in global space, so just collect them
    side_girt_accessories = []
    if joint_side_girt_left.jointAccessories:
        side_girt_accessories.extend(joint_side_girt_left.jointAccessories)
    if joint_side_girt_right.jointAccessories:
        side_girt_accessories.extend(joint_side_girt_right.jointAccessories)

    # ============================================================================
    # Create front girt (running left to right along the long dimension)
    # ============================================================================
    
    front_girt_size = create_vector2d(med_timber_size[0], med_timber_size[1])
    
    # Front girt is positioned 2 inches below the side girts
    # Side girts attach to front posts at post_back_height
    front_girt_drop = inches(2)
    front_girt_height_on_posts = post_back_height - front_girt_drop
    
    # Front girt stickout: symmetric on both ends (left and right)
    front_girt_stickout = Stickout.symmetric(inches(Rational(3, 2)))  # 1.5 inches
    
    # Front girt connects left front post to right front post
    front_girt = join_timbers(
        timber1=post_front_left,       # Left front post (timber1)
        timber2=post_front_right,      # Right front post (timber2)
        location_on_timber1=front_girt_height_on_posts,   # 2" below side girts
        stickout=front_girt_stickout,  # 1.5" stickout on both sides
        location_on_timber2=front_girt_height_on_posts,   # Same height on right post
        lateral_offset=0,       # No lateral offset
        size=front_girt_size,
        name="Front Girt"
    )
    
    # ============================================================================
    # Split the front girt into two pieces and rejoin with a splice joint
    # ============================================================================    
    # Split the front girt at the midpoint
    front_girt_split_distance = front_girt.length / 2
    front_girt_left, front_girt_right = split_timber(
        front_girt, 
        front_girt_split_distance,
        name1="Front Girt Left",
        name2="Front Girt Right"
    )
    
    # Create a splice joint to rejoin the two pieces
    # The left piece's TOP end meets the right piece's BOTTOM end
    front_girt_splice_joint = cut_basic_splice_joint_on_aligned_timbers(
        front_girt_left, TimberReferenceEnd.TOP,
        front_girt_right, TimberReferenceEnd.BOTTOM
    )
    
    # ============================================================================
    # Create mortise and tenon joints where front girt pieces meet posts
    # ============================================================================
    # Tenon size: 1" x 2" (1" horizontal, 2" vertical)
    # Tenon length: 3 inches
    # Mortise depth: 3 inches
    # Peg: 5/8" square peg, 1 inch from shoulder, centered
    
    front_girt_tenon_size = Matrix([inches(2), inches(1)])
    front_girt_tenon_length = inches(3)
    front_girt_mortise_depth = inches(3.5)
    
    # Peg parameters: 5/8" square peg, 1" from shoulder, on centerline
    front_girt_peg_params = SimplePegParameters(
        shape=PegShape.SQUARE,
        tenon_face=TimberReferenceLongFace.FRONT,
        peg_positions=[(inches(1), Rational(0))],  # 1" from shoulder, centered
        size=inches(Rational(5, 8)),  # 5/8" square
        depth=inches(Rational(7, 2))  
    )
    
    # Left end: Front girt left piece BOTTOM meets left front post
    joint_front_girt_left = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=front_girt_left,
        mortise_timber=post_front_left,
        tenon_end=TimberReferenceEnd.BOTTOM,
        size=front_girt_tenon_size,
        tenon_length=front_girt_tenon_length,
        mortise_depth=front_girt_mortise_depth,
        tenon_position=None,  # Centered
        peg_parameters=front_girt_peg_params
    )
    
    # Right end: Front girt right piece TOP meets right front post
    joint_front_girt_right = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        tenon_timber=front_girt_right,
        mortise_timber=post_front_right,
        tenon_end=TimberReferenceEnd.TOP,
        size=front_girt_tenon_size,
        tenon_length=front_girt_tenon_length,
        mortise_depth=front_girt_mortise_depth,
        tenon_position=None,  # Centered
        peg_parameters=front_girt_peg_params
    )
    
    # Collect cuts for each piece:
    # - Left piece: tenon cuts (BOTTOM end) + splice cuts (TOP end)
    # - Right piece: tenon cuts (TOP end) + splice cuts (BOTTOM end)
    
    # The left piece gets cuts from joint and splice
    front_girt_left_cuts = []
    front_girt_left_cuts.extend(joint_front_girt_left.cut_timbers[0]._cuts)  # Tenon cuts
    front_girt_left_cuts.extend(front_girt_splice_joint.cut_timbers[0]._cuts)  # Splice cuts
    
    # The right piece gets cuts from joint and splice
    front_girt_right_cuts = []
    front_girt_right_cuts.extend(joint_front_girt_right.cut_timbers[0]._cuts)  # Tenon cuts
    front_girt_right_cuts.extend(front_girt_splice_joint.cut_timbers[1]._cuts)  # Splice cuts
    
    # Create CutTimbers for the split pieces with all their cuts
    pct_front_girt_left = CutTimber(front_girt_left, cuts=front_girt_left_cuts)
    pct_front_girt_right = CutTimber(front_girt_right, cuts=front_girt_right_cuts)
    
    # Collect joint accessories (pegs) for rendering
    # Accessories are already in global space, so just collect them
    front_girt_accessories = []
    if joint_front_girt_left.jointAccessories:
        front_girt_accessories.extend(joint_front_girt_left.jointAccessories)
    if joint_front_girt_right.jointAccessories:
        front_girt_accessories.extend(joint_front_girt_right.jointAccessories)

    # ============================================================================
    # Create top plates (running left to right on top of posts)
    # ============================================================================
    
    # Top plate size: 6" x 4" (same as mudsills, 6" vertical)
    top_plate_size = create_vector2d(big_timber_size[0], big_timber_size[1])
    
    # Top plate stickout: 1 foot on each side (symmetric)
    top_plate_stickout = Stickout.symmetric(feet(1))
    
    # Front top plate (connects left front post to right front post)
    # Sits on top of the front posts
    top_plate_front = join_timbers(
        timber1=post_front_left,       # Left front post (timber1)
        timber2=post_front_right,      # Right front post (timber2)
        location_on_timber1=post_front_height,   # At top of front post
        stickout=top_plate_stickout,   # 1 foot stickout on both sides
        location_on_timber2=post_front_height,   # Same height on right post
        lateral_offset=0,       # No lateral offset
        size=top_plate_size,
        orientation_width_vector=create_vector3d(0, 0, 1),
        name="Front Top Plate"
    )
    
    # Back top plate (connects left back post to right back post)
    # Sits on top of the back posts
    top_plate_back = join_timbers(
        timber1=post_back_left,        # Left back post (timber1)
        timber2=post_back_right,       # Right back post (timber2)
        location_on_timber1=post_back_height,    # At top of back post
        stickout=top_plate_stickout,   # 1 foot stickout on both sides
        location_on_timber2=post_back_height,    # Same height on right post
        lateral_offset=0,       # No lateral offset
        size=top_plate_size,
        orientation_width_vector=create_vector3d(0, 0, 1),
        name="Back Top Plate"
    )

    # ============================================================================
    # Create joists (running from front to back, between mudsills)
    # ============================================================================
    
    # Joist size: 4" x 4"
    joist_size = create_vector2d(med_timber_size[0], med_timber_size[1])
    joist_width = med_timber_size[0]
    
    # Calculate spacing: 3 joists with 4 equal gaps (left side, 2 between joists, right side)
    num_joists = 3
    num_gaps = 4
    gap_spacing = (base_width - num_joists * joist_width) / Rational(num_gaps)
    
    # Joist positions along X axis (from left edge, which is where mudsills start)
    joist_positions_along_mudsill = [
        gap_spacing + joist_width / Rational(2),                      # Joist 1
        Rational(2) * gap_spacing + Rational(3, 2) * joist_width,     # Joist 2
        Rational(3) * gap_spacing + Rational(5, 2) * joist_width      # Joist 3
    ]
    
    # No stickout on joists (flush with mudsills)
    joist_stickout = Stickout.nostickout()
    
    # Calculate vertical offset to make joists flush with top of mudsills
    # Top of mudsill = mudsill_centerline + mudsill_height/2
    # Top of joist = joist_centerline + joist_height/2
    # To align tops: joist_offset = (mudsill_height - joist_height) / 2
    mudsill_height = big_timber_size[0]  # 6" vertical
    joist_height = med_timber_size[0]    # 4" vertical
    joist_vertical_offset = (mudsill_height - joist_height) / Rational(2)  # = 1"
    
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
            orientation_width_vector=create_vector3d(0, 0, 1),  # Face up
            name=f"Joist {i}"
        )
        joists.append(joist)

    # ============================================================================
    # Create rafters (running from back top plate to front top plate)
    # ============================================================================
    
    # Rafter size: 4" x 4"
    rafter_size = create_vector2d(med_timber_size[0], med_timber_size[1])
    rafter_width = med_timber_size[0]  # Width of rafter (for spacing calculation)
    
    # Calculate positions for 5 rafters with outer faces flush with ends of top plates
    # The centerline of the first rafter is at rafter_width/2
    # The centerline of the last rafter is at (base_width - rafter_width/2)
    # Distance between outer rafter centerlines: base_width - rafter_width
    # With 5 rafters, there are 4 gaps between centerlines
    
    num_rafters = 5
    rafter_centerline_spacing = (top_plate_front.length - rafter_width) / Rational(num_rafters-1)
    
    # Rafter positions along the top plates (X axis)
    rafter_positions_along_top_plate = []
    for i in range(num_rafters):
        position = rafter_width / Rational(2) + i * rafter_centerline_spacing
        rafter_positions_along_top_plate.append(position)
    
    # Rafters have 12" stickout and are offset upwards by 3 inches from top plate centerlines
    rafter_stickout = Stickout.symmetric(inches(12))
    rafter_vertical_offset = inches(-3)
    
    # Create the 5 rafters
    rafters = []
    
    for i, location_along_top_plate in enumerate(rafter_positions_along_top_plate, start=1):
        # Rafters connect from back top plate to front top plate
        # Top plates run along X axis, so the location is the X position
        
        rafter = join_timbers(
            timber1=top_plate_back,        # Back top plate (timber1)
            timber2=top_plate_front,       # Front top plate (timber2)
            location_on_timber1=location_along_top_plate,  # Position along back top plate (reversed)
            stickout=rafter_stickout,      # 12" stickout
            location_on_timber2=location_along_top_plate,  # Same position on front top plate
            lateral_offset=rafter_vertical_offset,
            size=rafter_size,
            orientation_width_vector=create_vector3d(0, 0, 1),  # Face up
            name=f"Rafter {i}"
        )
        rafters.append(rafter)

    # ============================================================================
    # Create house joints for rafter pockets in top plates
    # ============================================================================
    
    # Create house joints for each rafter with both the front and back top plates
    # The top plates are the "housing timber" (receiving the pockets)
    # The rafters are the "housed timber" (fitting into the pockets)
    rafter_house_joints = []
    
    for i, rafter in enumerate(rafters, start=1):
        # TODO switch to not DEPRECATED one
        # Create house joint with back top plate
        joint_back = cut_basic_house_joint_DEPRECATED(
            housing_timber=top_plate_back,
            housed_timber=rafter,
            extend_housed_timber_to_infinity=False
        )
        
        # Create house joint with front top plate
        joint_front = cut_basic_house_joint_DEPRECATED(
            housing_timber=top_plate_front,
            housed_timber=rafter,
            extend_housed_timber_to_infinity=False
        )
        
        rafter_house_joints.append((joint_back, joint_front))

    # ============================================================================
    # Wrap all timbers in CutTimber objects and return
    # ============================================================================
    
    cut_timbers = []
    
    # Add mudsills (with miter joints applied)
    # Each mudsill participates in 2 joints (one at each end)
    # We need to collect all cuts for each mudsill and create a single CutTimber
    
    # Collect cuts for each mudsill from the corner joints and mortise joints
    
    # Collect cuts from corner miter joints
    # joint_corner_0: Front BOTTOM, Left TOP
    # joint_corner_1: Front TOP, Right BOTTOM
    # joint_corner_2: Right TOP, Back BOTTOM
    # joint_corner_3: Back TOP, Left BOTTOM
    
    # Also collect mortise cuts from post joints
    # For mortise and tenon joints: cut_timbers[0] is the TENON timber, cut_timbers[1] is the MORTISE timber
    
    # #region agent log
    import json
    import datetime
    try:
        with open('/Users/peter.lu/kitchen/faucet/giraffeCAD-proto/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({
                'location': 'oscarshed.py:699',
                'message': 'Collecting mudsill cuts from mortise-tenon joints',
                'data': {
                    'extracting_from': 'cut_timbers[1]',
                    'expecting': 'mortise_cuts_for_mudsill',
                    'joint_post_front_left_ct0_timber': joint_post_front_left.cut_timbers[0]._timber.name if hasattr(joint_post_front_left.cut_timbers[0]._timber, 'name') else 'unnamed',
                    'joint_post_front_left_ct1_timber': joint_post_front_left.cut_timbers[1]._timber.name if hasattr(joint_post_front_left.cut_timbers[1]._timber, 'name') else 'unnamed',
                    'ct0_cuts_count': len(joint_post_front_left.cut_timbers[0]._cuts),
                    'ct1_cuts_count': len(joint_post_front_left.cut_timbers[1]._cuts)
                },
                'timestamp': int(datetime.datetime.now().timestamp() * 1000),
                'sessionId': 'debug-session',
                'hypothesisId': 'H1_H3'
            }) + '\n')
    except: pass
    # #endregion
    
    mudsill_front_cuts = [
        joint_corner_0.cut_timbers[0]._cuts[0],  # Miter at corner 0
        joint_corner_1.cut_timbers[0]._cuts[0],  # Miter at corner 1
        joint_post_front_left.cut_timbers[1]._cuts[0],   # Mortise for front-left post
        joint_post_front_right.cut_timbers[1]._cuts[0],  # Mortise for front-right post
    ]
    
    mudsill_right_cuts = [
        joint_corner_1.cut_timbers[1]._cuts[0],  # Miter at corner 1
        joint_corner_2.cut_timbers[0]._cuts[0],  # Miter at corner 2
    ]
    
    mudsill_back_cuts = [
        joint_corner_2.cut_timbers[1]._cuts[0],  # Miter at corner 2
        joint_corner_3.cut_timbers[0]._cuts[0],  # Miter at corner 3
        joint_post_back_right.cut_timbers[1]._cuts[0],   # Mortise for back-right post
        joint_post_back_left.cut_timbers[1]._cuts[0],    # Mortise for back-left post
    ]
    
    mudsill_left_cuts = [
        joint_corner_0.cut_timbers[1]._cuts[0],  # Miter at corner 0
        joint_corner_3.cut_timbers[1]._cuts[0],  # Miter at corner 3
    ]
    
    # Create CutTimbers for each mudsill with all cuts at construction
    pct_mudsill_front = CutTimber(mudsill_front, cuts=mudsill_front_cuts)
    pct_mudsill_right = CutTimber(mudsill_right, cuts=mudsill_right_cuts)
    pct_mudsill_back = CutTimber(mudsill_back, cuts=mudsill_back_cuts)
    pct_mudsill_left = CutTimber(mudsill_left, cuts=mudsill_left_cuts)
    
    # Add the mudsills with all their cuts
    cut_timbers.append(pct_mudsill_front)
    cut_timbers.append(pct_mudsill_right)
    cut_timbers.append(pct_mudsill_back)
    cut_timbers.append(pct_mudsill_left)
    
    # Add posts with joint cuts
    # For mortise and tenon joints: cut_timbers[0] is the TENON timber, cut_timbers[1] is the MORTISE timber
    # For butt joints: cut_timbers[1] is the cut timber (post)
    
    # Front left post: has tenon into mudsill + mortise for front girt + mortise for side girt
    post_front_left_cuts = []
    # #region agent log
    import json
    import datetime
    try:
        with open('/Users/peter.lu/kitchen/faucet/giraffeCAD-proto/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({
                'location': 'oscarshed.py:739',
                'message': 'Collecting post cuts from multiple joints',
                'data': {
                    'post_name': 'post_front_left',
                    'from_mudsill_joint_extracting_from': 'cut_timbers[0]',
                    'from_mudsill_joint_expecting': 'tenon_cuts_for_post',
                    'mudsill_joint_ct0_timber': joint_post_front_left.cut_timbers[0]._timber.name,
                    'mudsill_joint_ct1_timber': joint_post_front_left.cut_timbers[1]._timber.name,
                    'from_girt_joints_extracting_from': 'cut_timbers[1]',
                    'from_girt_joints_expecting': 'mortise_cuts_for_post',
                    'front_girt_joint_ct0_timber': joint_front_girt_left.cut_timbers[0]._timber.name,
                    'front_girt_joint_ct1_timber': joint_front_girt_left.cut_timbers[1]._timber.name,
                    'side_girt_joint_ct0_timber': joint_side_girt_left.cut_timbers[0]._timber.name,
                    'side_girt_joint_ct1_timber': joint_side_girt_left.cut_timbers[1]._timber.name
                },
                'timestamp': int(datetime.datetime.now().timestamp() * 1000),
                'sessionId': 'debug-session',
                'hypothesisId': 'H1_H3_H4'
            }) + '\n')
    except: pass
    # #endregion
    post_front_left_cuts.extend(joint_post_front_left.cut_timbers[0]._cuts)  # Tenon into mudsill
    post_front_left_cuts.extend(joint_front_girt_left.cut_timbers[1]._cuts)  # Mortise for front girt
    post_front_left_cuts.extend(joint_side_girt_left.cut_timbers[1]._cuts)   # Mortise for side girt
    pct_post_front_left = CutTimber(post_front_left, cuts=post_front_left_cuts)
    
    # Front right post: has tenon into mudsill + mortise for front girt + mortise for side girt
    post_front_right_cuts = []
    post_front_right_cuts.extend(joint_post_front_right.cut_timbers[0]._cuts)  # Tenon into mudsill
    post_front_right_cuts.extend(joint_front_girt_right.cut_timbers[1]._cuts)  # Mortise for front girt
    post_front_right_cuts.extend(joint_side_girt_right.cut_timbers[1]._cuts)   # Mortise for side girt
    pct_post_front_right = CutTimber(post_front_right, cuts=post_front_right_cuts)
    
    # Add all posts
    cut_timbers.append(pct_post_front_left)       # Front left post with all cuts
    cut_timbers.append(pct_post_front_right)      # Front right post with all cuts
    cut_timbers.append(joint_post_back_right.cut_timbers[0])      # Corner post with M&T (tenon timber)
    cut_timbers.append(joint_post_back_middle_right.cut_timbers[1])  # Middle post with butt joint
    cut_timbers.append(joint_post_back_middle_left.cut_timbers[1])   # Middle post with butt joint
    cut_timbers.append(joint_post_back_left.cut_timbers[0])       # Corner post with M&T (tenon timber)
    
    # Add side girts (with mortise & tenon joints at front ends)
    # #region agent log
    import json
    import datetime
    try:
        with open('/Users/peter.lu/kitchen/faucet/giraffeCAD-proto/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({
                'location': 'oscarshed.py:760',
                'message': 'Adding girts to cut_timbers list',
                'data': {
                    'extracting_from': 'cut_timbers[0]',
                    'expecting': 'tenon_timber_girts',
                    'side_girt_left_ct0_timber': joint_side_girt_left.cut_timbers[0]._timber.name,
                    'side_girt_left_ct1_timber': joint_side_girt_left.cut_timbers[1]._timber.name,
                    'side_girt_right_ct0_timber': joint_side_girt_right.cut_timbers[0]._timber.name,
                    'side_girt_right_ct1_timber': joint_side_girt_right.cut_timbers[1]._timber.name
                },
                'timestamp': int(datetime.datetime.now().timestamp() * 1000),
                'sessionId': 'debug-session',
                'hypothesisId': 'H1_H3'
            }) + '\n')
    except: pass
    # #endregion
    cut_timbers.append(joint_side_girt_left.cut_timbers[0])  # Left side girt with tenon cuts
    cut_timbers.append(joint_side_girt_right.cut_timbers[0])  # Right side girt with tenon cuts
    
    # Add front girt pieces (with mortise & tenon joints at ends and splice joint in middle)
    cut_timbers.append(pct_front_girt_left)  # Left piece with tenon + splice cuts
    cut_timbers.append(pct_front_girt_right)  # Right piece with tenon + splice cuts
    
    # Add top plates with rafter pocket cuts
    # Collect all the cuts for each top plate from the house joints
    top_plate_back_cuts = []
    top_plate_front_cuts = []
    
    for joint_back, joint_front in rafter_house_joints:
        # joint_back.cut_timbers[0] is the housing timber (top_plate_back)
        # joint_front.cut_timbers[0] is the housing timber (top_plate_front)
        top_plate_back_cuts.extend(joint_back.cut_timbers[0]._cuts)
        top_plate_front_cuts.extend(joint_front.cut_timbers[0]._cuts)
    
    # Create CutTimbers for top plates with all cuts
    pct_top_plate_back = CutTimber(top_plate_back, cuts=top_plate_back_cuts)
    pct_top_plate_front = CutTimber(top_plate_front, cuts=top_plate_front_cuts)
    
    cut_timbers.append(pct_top_plate_back)
    cut_timbers.append(pct_top_plate_front)
    
    # Add joists
    for joist in joists:
        cut_timbers.append(CutTimber(joist))
    
    # Add rafters
    for rafter in rafters:
        cut_timbers.append(CutTimber(rafter))
    
    # Combine all accessories (pegs from front girt and side girts)
    all_accessories = front_girt_accessories + side_girt_accessories
    
    return Frame(
        cut_timbers=cut_timbers,
        accessories=all_accessories,
        name="Oscar's Shed"
    )


# ============================================================================
# Main execution (when run as standalone script)
# ============================================================================

if __name__ == "__main__":
    print(f"Creating Oscar's Shed: 8 ft x 4 ft")
    print(f"  ({float(base_width):.3f} m x {float(base_length):.3f} m)")
    
    frame = create_oscarshed()
    
    print(f"\nCreated {len(frame.cut_timbers)} timbers and {len(frame.accessories)} accessories:")
    for ct in frame.cut_timbers:
        print(f"  - {ct.timber.name}")
    if frame.accessories:
        print(f"\nAccessories:")
        for acc in frame.accessories:
            print(f"  - {type(acc).__name__}")
    
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
    print(f"Front Girt: 1 (running left to right, spliced in middle)")
    print(f"  - Position: 2 inches below side girts")
    print(f"  - Stickout: 1.5 inches on both sides (symmetric)")
    print(f"  - Split at midpoint with splice joint")
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
    print(f"  - Stickout: 12 inches on both ends (symmetric)")
    print(f"  - Top plates have housed joints (rafter pockets) for each rafter")
    print("="*60)

