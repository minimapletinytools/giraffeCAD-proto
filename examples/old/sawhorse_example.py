from giraffe import *

# Define timber dimensions using dimensional helpers
feet_size = create_v2(inches(4), inches(6))
beam_size = create_v2(inches(4), inches(4))
post_size = create_v2(inches(4), inches(4))
stretcher_size = create_v2(inches(4), inches(4))

tenon_size = create_v2(inches(1), inches(1))  # Square tenon cross-section
tenon_length = inches(2)

# Define constants for the sawhorse
bottom_width = inches(24)
bottom_length = inches(48)
top_beam_length = inches(100)
top_beam_surface_position = inches(50)

def create_sawhorse() -> Frame:
    """
    Create a complete sawhorse structure with joints.
    
    Returns:
        Frame: Frame object containing all cut timbers for the complete sawhorse
    """
    # define footprint
    footprint = Footprint(
        corners=[  # type: ignore[arg-type]
            create_v2(-bottom_width / 2, -bottom_length / 2),
            create_v2(bottom_width / 2, -bottom_length / 2),
            create_v2(bottom_width / 2, bottom_length / 2),
            create_v2(-bottom_width / 2, bottom_length / 2),
        ]
    )

    # now create 2 "mudsills on the INSIDE of the footprint, one on the left boundary and one on the right boundary
    # Create mudsill on the left boundary (index 3: bottom-left to top-left)
    left_mudsill = create_horizontal_timber_on_footprint(
        footprint, 
        corner_index=3, 
        location_type=FootprintLocation.INSIDE,
        size=feet_size,
        length=bottom_length,
        name="Left Mudsill"
    )
    
    # Create mudsill on the right boundary (index 1: top-right to bottom-right)  
    right_mudsill = create_horizontal_timber_on_footprint(
        footprint, 
        corner_index=1, 
        location_type=FootprintLocation.INSIDE,
        size=feet_size,
        length=bottom_length,
        name="Right Mudsill"
    )
    
    # next create a "beam" that is running from left to right centered on the origin and top_beam_surface_position-stretcher_size[1]/2 above the origin
    beam = create_axis_aligned_timber(
        bottom_position=create_v3(-top_beam_length / 2, 0, top_beam_surface_position - stretcher_size[1] / 2),
        length=top_beam_length,
        size=beam_size,
        length_direction=TimberFace.RIGHT,
        width_direction=TimberFace.TOP,
        name="Top Beam"
    )

    # connect the 2 feet to the beam with posts. The posts are centered on the feet
    
    # Connect left foot to beam
    left_post = join_perpendicular_on_face_parallel_timbers(
        timber1=left_mudsill,
        timber2=beam,
        location_on_timber1=left_mudsill.length / 2,  # Center of the mudsill
        stickout=Stickout(post_size[0] / 2, post_size[0] / 2),  # Symmetric: half the post width on each side
        lateral_offset_from_centerline_timber1=Rational(0),
        size=post_size,
        feature_to_mark_on_joining_timber=None,
        orientation_face_on_timber1=TimberFace.TOP,
        name="Left Post"
    )
    
    # Connect right foot to beam
    right_post = join_perpendicular_on_face_parallel_timbers(
        timber1=right_mudsill,
        timber2=beam,
        location_on_timber1=right_mudsill.length / 2,  # Center of the mudsill
        stickout=Stickout(post_size[0] / 2, post_size[0] / 2),  # Symmetric: half the post width on each side
        lateral_offset_from_centerline_timber1=Rational(0),
        size=post_size,
        feature_to_mark_on_joining_timber=None,
        orientation_face_on_timber1=TimberFace.TOP,
        name="Right Post"
    )

    # now create the stretcher that runs between the middle of the 2 posts using the join_perpendicular_on_face_parallel_timbers
    stretcher = join_perpendicular_on_face_parallel_timbers(
        timber1=left_post,
        timber2=right_post,
        location_on_timber1=left_post.length / 2,  # Middle of the post
        stickout=Stickout(stretcher_size[0] / 2, stretcher_size[0] / 2),  # Symmetric: half the stretcher width on each side
        lateral_offset_from_centerline_timber1=Rational(0),
        size=stretcher_size,
        feature_to_mark_on_joining_timber=None,
        orientation_face_on_timber1=TimberFace.TOP,
        name="Stretcher"
    )

    # Create CutTimber objects for all timbers (names will be inherited from the timbers)
    cut_left_mudsill = CutTimber(left_mudsill)
    cut_right_mudsill = CutTimber(right_mudsill)
    cut_beam = CutTimber(beam)
    cut_left_post = CutTimber(left_post)
    cut_right_post = CutTimber(right_post)
    cut_stretcher = CutTimber(stretcher)

    # next create mortise and tenon joints between the posts and the mudsills
    mudsill_left_joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=left_mudsill,
        tenon_timber=left_post,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon comes from bottom of post
        tenon_size=tenon_size,
        tenon_length=tenon_length
    )

    mudsill_right_joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=right_mudsill,
        tenon_timber=right_post,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon comes from bottom of post
        tenon_size=tenon_size,
        tenon_length=tenon_length
    )

    # next create mortise and tenon joints between the posts and the stretcher
    stretcher_left_joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=left_post,
        tenon_timber=stretcher,
        tenon_end=TimberReferenceEnd.BOTTOM,  # Tenon comes from bottom end of stretcher
        tenon_size=tenon_size,
        tenon_length=tenon_length
    )

    stretcher_right_joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=right_post,
        tenon_timber=stretcher,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon comes from top end of stretcher
        tenon_size=tenon_size,
        tenon_length=tenon_length
    )

    # now create mortise and tenon joints between the posts and the beam
    beam_left_joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=beam,
        tenon_timber=left_post,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon comes from bottom end of beam
        tenon_size=tenon_size,
        tenon_length=tenon_length
    )

    beam_right_joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
        mortise_timber=beam,
        tenon_timber=right_post,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon comes from top end of beam
        tenon_size=tenon_size,
        tenon_length=tenon_length
    )

    # Apply joints to the cut timbers
    # Each joint affects multiple timbers, so we need to add the cut operations to the appropriate timbers
    
    # Mudsill joints
    cut_left_mudsill.joints.extend(mudsill_left_joint.cut_timbers["mortise_timber"].cuts)
    cut_left_post.joints.extend(mudsill_left_joint.cut_timbers["tenon_timber"].cuts)
    
    cut_right_mudsill.joints.extend(mudsill_right_joint.cut_timbers["mortise_timber"].cuts)
    cut_right_post.joints.extend(mudsill_right_joint.cut_timbers["tenon_timber"].cuts)
    
    # Stretcher joints
    cut_left_post.joints.extend(stretcher_left_joint.cut_timbers["mortise_timber"].cuts)
    cut_stretcher.joints.extend(stretcher_left_joint.cut_timbers["tenon_timber"].cuts)
    
    cut_right_post.joints.extend(stretcher_right_joint.cut_timbers["mortise_timber"].cuts)
    cut_stretcher.joints.extend(stretcher_right_joint.cut_timbers["tenon_timber"].cuts)
    
    # Beam joints
    cut_left_post.joints.extend(beam_left_joint.cut_timbers["mortise_timber"].cuts)
    cut_beam.joints.extend(beam_left_joint.cut_timbers["tenon_timber"].cuts)
    
    cut_right_post.joints.extend(beam_right_joint.cut_timbers["mortise_timber"].cuts)
    cut_beam.joints.extend(beam_right_joint.cut_timbers["tenon_timber"].cuts)

    # Return all cut timbers in a Frame
    return Frame(
        cut_timbers=[
            cut_left_mudsill,
            cut_right_mudsill,
            cut_beam,
            cut_left_post,
            cut_right_post,
            cut_stretcher
        ],
        name="Sawhorse"
    )

def main():
    """Main function that creates and returns the sawhorse frame."""
    frame = create_sawhorse()
    
    print(f"Created sawhorse with {len(frame.cut_timbers)} timbers:")
    for i, cut_timber in enumerate(frame.cut_timbers):
        timber = cut_timber.timber
        print(f"  {i+1}. Timber: {timber.name} "
              f"length={timber.length:.3f}m, "
              f"size=({float(timber.size[0]):.3f}m x {float(timber.size[1]):.3f}m), "
              f"joints={len(cut_timber.joints)}, "
              f"position={timber.get_bottom_position_global()}")
    
    return frame

if __name__ == "__main__":
    frame = main()
    print(f"\nReturned Frame '{frame.name}' with {len(frame.cut_timbers)} cut timbers ready for rendering or further processing.")