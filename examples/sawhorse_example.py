from giraffe import *

# Define timber dimensions (inches converted to meters)
INCH_TO_METER = 0.0254

feet_size = create_vector2d(4 * INCH_TO_METER, 6 * INCH_TO_METER)
beam_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)
post_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)
stretcher_size = create_vector2d(4 * INCH_TO_METER, 4 * INCH_TO_METER)

tenon_thickness = 1 * INCH_TO_METER
tenon_length = 2 * INCH_TO_METER

# Define constants for the sawhorse (converted to meters)
bottom_width = 24 * INCH_TO_METER
bottom_length = 48 * INCH_TO_METER
top_beam_length = 100 * INCH_TO_METER
top_beam_surface_position = 50 * INCH_TO_METER

def create_sawhorse() -> list[CutTimber]:
    """
    Create a complete sawhorse structure with joints.
    
    Returns:
        list[CutTimber]: List of CutTimber objects representing the complete sawhorse
    """
    # define footprint
    footprint = Footprint(
        boundary = [
            create_vector2d(-bottom_width / 2, -bottom_length / 2),
            create_vector2d(bottom_width / 2, -bottom_length / 2),
            create_vector2d(bottom_width / 2, bottom_length / 2),
            create_vector2d(-bottom_width / 2, bottom_length / 2),
        ]
    )

    # now create 2 "mudsills on the INSIDE of the footprint, one on the left boundary and one on the right boundary
    # Create mudsill on the left boundary (index 3: bottom-left to top-left)
    left_mudsill = create_horizontal_timber_on_footprint(
        footprint, 
        corner_index=3, 
        location_type=TimberLocationType.INSIDE,
        size=feet_size,
        length=bottom_length
    )
    left_mudsill.name = "Left Mudsill"
    
    # Create mudsill on the right boundary (index 1: top-right to bottom-right)  
    right_mudsill = create_horizontal_timber_on_footprint(
        footprint, 
        corner_index=1, 
        location_type=TimberLocationType.INSIDE,
        size=feet_size,
        length=bottom_length
    )
    right_mudsill.name = "Right Mudsill"
    
    # next create a "beam" that is running from left to right centered on the origin and top_beam_surface_position-stretcher_size[1]/2 above the origin
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(-top_beam_length / 2, 0, top_beam_surface_position - float(stretcher_size[1]) / 2),
        length=top_beam_length,
        size=beam_size,
        length_direction=TimberFace.RIGHT,
        face_direction=TimberFace.TOP
    )
    beam.name = "Top Beam"

    # connect the 2 feet to the beam with posts. The posts are centered on the feet
    
    # Connect left foot to beam
    offset_left = FaceAlignedJoinedTimberOffset(
        reference_face=TimberFace.TOP,
        centerline_offset=None,
        face_offset=None
    )
    
    left_post = join_perpendicular_on_face_parallel_timbers(
        timber1=left_mudsill,
        timber2=beam,
        location_on_timber1=left_mudsill.length / 2,  # Center of the mudsill
        stickout=Stickout(float(post_size[0]) / 2, float(post_size[0]) / 2),  # Symmetric: half the post width on each side
        offset_from_timber1=offset_left,
        size=post_size,
        orientation_face_on_timber1=TimberFace.TOP
    )
    left_post.name = "Left Post"
    
    # Connect right foot to beam
    offset_right = FaceAlignedJoinedTimberOffset(
        reference_face=TimberFace.TOP,
        centerline_offset=None,
        face_offset=None
    )
    
    right_post = join_perpendicular_on_face_parallel_timbers(
        timber1=right_mudsill,
        timber2=beam,
        location_on_timber1=right_mudsill.length / 2,  # Center of the mudsill
        stickout=Stickout(float(post_size[0]) / 2, float(post_size[0]) / 2),  # Symmetric: half the post width on each side
        offset_from_timber1=offset_right,
        size=post_size,
        orientation_face_on_timber1=TimberFace.TOP
    )
    right_post.name = "Right Post"

    # now create the stretcher that runs between the middle of the 2 posts using the join_perpendicular_on_face_parallel_timbers
    offset_stretcher = FaceAlignedJoinedTimberOffset(
        reference_face=TimberFace.TOP,
        centerline_offset=None,
        face_offset=None
    )
    
    stretcher = join_perpendicular_on_face_parallel_timbers(
        timber1=left_post,
        timber2=right_post,
        location_on_timber1=left_post.length / 2,  # Middle of the post
        stickout=Stickout(float(stretcher_size[0]) / 2, float(stretcher_size[0]) / 2),  # Symmetric: half the stretcher width on each side
        offset_from_timber1=offset_stretcher,
        size=stretcher_size,
        orientation_face_on_timber1=TimberFace.TOP
    )
    stretcher.name = "Stretcher"

    # Create CutTimber objects for all timbers (names will be inherited from the timbers)
    cut_left_mudsill = CutTimber(left_mudsill)
    cut_right_mudsill = CutTimber(right_mudsill)
    cut_beam = CutTimber(beam)
    cut_left_post = CutTimber(left_post)
    cut_right_post = CutTimber(right_post)
    cut_stretcher = CutTimber(stretcher)

    # next create mortise and tenon joints between the posts and the mudsills
    mudsill_left_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=left_mudsill,
        tenon_timber=left_post,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon comes from bottom of post
        tenon_thickness=tenon_thickness,
        tenon_length=tenon_length
    )
    mudsill_left_joint.name = "Left Post to Mudsill Joint"

    mudsill_right_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=right_mudsill,
        tenon_timber=right_post,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon comes from bottom of post
        tenon_thickness=tenon_thickness,
        tenon_length=tenon_length
    )
    mudsill_right_joint.name = "Right Post to Mudsill Joint"

    # next create mortise and tenon joints between the posts and the stretcher
    stretcher_left_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=left_post,
        tenon_timber=stretcher,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon comes from bottom end of stretcher
        tenon_thickness=tenon_thickness,
        tenon_length=tenon_length
    )
    stretcher_left_joint.name = "Left Post to Stretcher Joint"

    stretcher_right_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=right_post,
        tenon_timber=stretcher,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon comes from top end of stretcher
        tenon_thickness=tenon_thickness,
        tenon_length=tenon_length
    )
    stretcher_right_joint.name = "Right Post to Stretcher Joint"

    # now create mortise and tenon joints between the posts and the beam
    beam_left_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=beam,
        tenon_timber=left_post,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon comes from bottom end of beam
        tenon_thickness=tenon_thickness,
        tenon_length=tenon_length
    )
    beam_left_joint.name = "Left Post to Beam Joint"

    beam_right_joint = simple_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=beam,
        tenon_timber=right_post,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon comes from top end of beam
        tenon_thickness=tenon_thickness,
        tenon_length=tenon_length
    )
    beam_right_joint.name = "Right Post to Beam Joint"

    # Apply joints to the cut timbers
    # Each joint affects multiple timbers, so we need to add the cut operations to the appropriate timbers
    
    # Mudsill joints
    for timber, cuts in mudsill_left_joint.timber_cuts:
        if timber == left_mudsill:
            cut_left_mudsill.joints.extend(cuts)
        elif timber == left_post:
            cut_left_post.joints.extend(cuts)
    
    for timber, cuts in mudsill_right_joint.timber_cuts:
        if timber == right_mudsill:
            cut_right_mudsill.joints.extend(cuts)
        elif timber == right_post:
            cut_right_post.joints.extend(cuts)
    
    # Stretcher joints
    for timber, cuts in stretcher_left_joint.timber_cuts:
        if timber == left_post:
            cut_left_post.joints.extend(cuts)
        elif timber == stretcher:
            cut_stretcher.joints.extend(cuts)
    
    for timber, cuts in stretcher_right_joint.timber_cuts:
        if timber == right_post:
            cut_right_post.joints.extend(cuts)
        elif timber == stretcher:
            cut_stretcher.joints.extend(cuts)
    
    # Beam joints
    for timber, cuts in beam_left_joint.timber_cuts:
        if timber == left_post:
            cut_left_post.joints.extend(cuts)
        elif timber == beam:
            cut_beam.joints.extend(cuts)
    
    for timber, cuts in beam_right_joint.timber_cuts:
        if timber == right_post:
            cut_right_post.joints.extend(cuts)
        elif timber == beam:
            cut_beam.joints.extend(cuts)

    # Return all cut timbers
    return [
        cut_left_mudsill,
        cut_right_mudsill,
        cut_beam,
        cut_left_post,
        cut_right_post,
        cut_stretcher
    ]

def main():
    """Main function that creates and returns the sawhorse cut timbers."""
    cut_timbers = create_sawhorse()
    
    print(f"Created sawhorse with {len(cut_timbers)} timbers:")
    for i, cut_timber in enumerate(cut_timbers):
        timber = cut_timber.timber
        print(f"  {i+1}. Timber: {timber.name} "
              f"length={timber.length:.3f}m, "
              f"size=({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m), "
              f"joints={len(cut_timber.joints)}, "
              f"position={timber.bottom_position}")
    
    return cut_timbers

if __name__ == "__main__":
    timbers = main()
    print(f"\nReturned {len(timbers)} cut timbers ready for rendering or further processing.")