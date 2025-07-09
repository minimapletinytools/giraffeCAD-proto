from giraffe import *

# Define timber dimensions
feet_size = V2(4,6)
beam_size = V2(4,4)
post_size = V2(4,4)
stretcher_size = V2(4,4)

# Define constants for the sawhorse
bottom_width = 24  
bottom_length = 48 
top_beam_length = 100
top_beam_surface_position = 50

def main():
    # define footprint
    footprint = Footprint(
        boundary = [
            V2(-bottom_width / 2, -bottom_length / 2),
            V2(bottom_width / 2, -bottom_length / 2),
            V2(bottom_width / 2, bottom_length / 2),
            V2(-bottom_width / 2, bottom_length / 2),
        ]
    )

    # now create 2 "mudsills on the INSIDE of the footprint, one on the left boundary and one on the right boundary
    # Create mudsill on the left boundary (index 3: bottom-left to top-left)
    left_mudsill = create_horizontal_timber_on_footprint(
        footprint, 
        footprint_index=3, 
        length=bottom_length, 
        location_type=TimberLocationType.INSIDE
    )
    
    # Create mudsill on the right boundary (index 1: top-right to bottom-right)  
    right_mudsill = create_horizontal_timber_on_footprint(
        footprint, 
        footprint_index=1, 
        length=bottom_length, 
        location_type=TimberLocationType.INSIDE
    )
    
    # next create a "beam" that is running from left to right centered on the origin and top_beam_surface_position-stretcher_size.y/2 above the origin
    beam = create_axis_aligned_timber(
        bottom_position=V3(-top_beam_length / 2, 0, top_beam_surface_position - stretcher_size.y / 2),
        length=top_beam_length,
        size=beam_size,
        length_direction=TimberFace.RIGHT,
        face_direction=TimberFace.TOP
    )

    # connect the 2 feet to the beam with posts. The posts are centered on the feet
    
    # Create offset for centering posts on feet
    left_offset = FaceAlignedJoinedTimberOffset(
        reference_face=TimberFace.RIGHT,
        centerline_offset=0  # Centered on the foot
    )
    
    right_offset = FaceAlignedJoinedTimberOffset(
        reference_face=TimberFace.LEFT,
        centerline_offset=0  # Centered on the foot
    )
    
    # Connect left foot to beam
    left_post = join_perpendicular_on_face_aligned_timbers(
        timber1=left_mudsill,
        timber2=beam,
        location_on_timber1=left_mudsill.length,  # Top of the mudsill
        symmetric_stickout=post_size.x / 2,  # Half the post width
        offset_from_timber1=left_offset,
        orientation_face_on_timber1=TimberFace.TOP
    )
    
    # Connect right foot to beam
    right_post = join_perpendicular_on_face_aligned_timbers(
        timber1=right_mudsill,
        timber2=beam,
        location_on_timber1=right_mudsill.length,  # Top of the mudsill
        symmetric_stickout=post_size.x / 2,  # Half the post width
        offset_from_timber1=right_offset,
        orientation_face_on_timber1=TimberFace.TOP
    )

    # now create the stretcher that runs between the middle of the 2 posts using the join_perpendicular_on_face_aligned_timbers
    stretcher = join_perpendicular_on_face_aligned_timbers(
        timber1=left_post,
        timber2=right_post,
        location_on_timber1=left_post.length / 2,  # Middle of the post
        symmetric_stickout=stretcher_size.x / 2,  # Half the post width
        offset_from_timber1=FaceAlignedJoinedTimberOffset(
            reference_face=TimberFace.RIGHT,
            centerline_offset=0  # Centered on the post
        ),
        orientation_face_on_timber1=TimberFace.TOP
    )


if __name__ == "__main__":
    main()