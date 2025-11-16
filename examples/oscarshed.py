"""
Oscar's Shed - A simple timber frame shed structure
Built using the GiraffeCAD API
"""

from sympy import Rational
import sys
sys.path.append('..')

from giraffe import (
    create_vector2d, create_vector3d, create_timber,
    create_axis_aligned_horizontal_timber_on_footprint,
    TimberLocationType, CutTimber
)
from footprint import Footprint

# ============================================================================
# PARAMETERS - Modify these to adjust the shed design
# ============================================================================

# Footprint dimensions (in feet, will convert to meters)
base_width = 8.0      # Long dimension (X direction)
base_length = 3.5     # Short dimension (Y direction)

# Post parameters
post_inset = 0.5      # 6 inches = 0.5 feet, inset from corners on long side
post_back_height = 5.0    # Height of back posts (feet)
post_front_height = 5.5   # Height of front posts (feet) - 6 inches taller

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

    # Front mudsill (corner 0 to corner 1) - along X axis
    mudsill_front = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 0, base_width_m, TimberLocationType.INSIDE
    )
    mudsill_front.name = "Front Mudsill"

    # Right mudsill (corner 1 to corner 2) - along Y axis
    mudsill_right = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 1, base_length_m, TimberLocationType.INSIDE
    )
    mudsill_right.name = "Right Mudsill"

    # Back mudsill (corner 2 to corner 3) - along X axis
    mudsill_back = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 2, base_width_m, TimberLocationType.INSIDE
    )
    mudsill_back.name = "Back Mudsill"

    # Left mudsill (corner 3 to corner 0) - along Y axis
    mudsill_left = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 3, base_length_m, TimberLocationType.INSIDE
    )
    mudsill_left.name = "Left Mudsill"

    # ============================================================================
    # Create posts at corners (inset 6 inches from corners on long side)
    # ============================================================================

    # Post dimensions (using default post size from giraffe.py: 9cm x 9cm)
    post_size = create_vector2d(Rational(9, 100), Rational(9, 100))  # 9cm x 9cm
    post_width = float(post_size[0])  # 0.09m
    
    # Offset posts so their edge (not center) is on the boundary
    # Posts extend inward from the boundary
    post_boundary_offset = post_width / 2  # Half the post width

    # Front-left post (inset from left corner on front side)
    # Edge on front boundary (Y=0), extending inward
    post_front_left = create_timber(
        bottom_position=create_vector3d(post_inset_m, post_boundary_offset, 0),
        length=post_front_height_m,
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),  # Vertical (Z+)
        face_direction=create_vector3d(1, 0, 0)     # Face right (X+)
    )
    post_front_left.name = "Front Left Post"

    # Front-right post (inset from right corner on front side)
    # Edge on front boundary (Y=0), extending inward
    post_front_right = create_timber(
        bottom_position=create_vector3d(base_width_m - post_inset_m, post_boundary_offset, 0),
        length=post_front_height_m,
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),  # Vertical (Z+)
        face_direction=create_vector3d(1, 0, 0)     # Face right (X+)
    )
    post_front_right.name = "Front Right Post"

    # Back-right post (inset from right corner on back side)
    # Edge on back boundary (Y=base_length_m), extending inward
    post_back_right = create_timber(
        bottom_position=create_vector3d(base_width_m - post_inset_m, base_length_m - post_boundary_offset, 0),
        length=post_back_height_m,
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),  # Vertical (Z+)
        face_direction=create_vector3d(1, 0, 0)     # Face right (X+)
    )
    post_back_right.name = "Back Right Post"

    # Back-left post (inset from left corner on back side)
    # Edge on back boundary (Y=base_length_m), extending inward
    post_back_left = create_timber(
        bottom_position=create_vector3d(post_inset_m, base_length_m - post_boundary_offset, 0),
        length=post_back_height_m,
        size=post_size,
        length_direction=create_vector3d(0, 0, 1),  # Vertical (Z+)
        face_direction=create_vector3d(1, 0, 0)     # Face right (X+)
    )
    post_back_left.name = "Back Left Post"

    # ============================================================================
    # Wrap all timbers in CutTimber objects and return
    # ============================================================================
    
    cut_timbers = []
    
    # Add mudsills
    cut_timbers.append(CutTimber(mudsill_front))
    cut_timbers.append(CutTimber(mudsill_right))
    cut_timbers.append(CutTimber(mudsill_back))
    cut_timbers.append(CutTimber(mudsill_left))
    
    # Add posts
    cut_timbers.append(CutTimber(post_front_left))
    cut_timbers.append(CutTimber(post_front_right))
    cut_timbers.append(CutTimber(post_back_right))
    cut_timbers.append(CutTimber(post_back_left))
    
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
    print(f"Mudsills: 4 (all INSIDE footprint)")
    print(f"Posts: 4 total")
    print(f"  - Front posts: {post_front_height} ft tall")
    print(f"  - Back posts: {post_back_height} ft tall")
    print(f"  - Post inset: {post_inset} ft from corners")
    print("="*60)

