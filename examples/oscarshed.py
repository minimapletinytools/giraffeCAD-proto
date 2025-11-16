"""
Oscar's Shed - A simple timber frame shed structure
Built using the GiraffeCAD API
"""

from sympy import Rational
import sys
sys.path.append('..')

from giraffe import (
    create_vector2d, create_vector3d,
    create_axis_aligned_horizontal_timber_on_footprint,
    create_vertical_timber_on_footprint_side,
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

# Timber size definitions (in inches)
INCH_TO_METERS = 0.0254
small_timber_size = (4 * INCH_TO_METERS, 2.5 * INCH_TO_METERS)   # 2.5" x 4"
med_timber_size = (4 * INCH_TO_METERS, 4 * INCH_TO_METERS)       # 4" x 4"
big_timber_size = (6 * INCH_TO_METERS, 4 * INCH_TO_METERS)       # 4" x 6"

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
    mudsill_front = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 0, base_width_m, TimberLocationType.INSIDE, mudsill_size
    )
    mudsill_front.name = "Front Mudsill"

    # Right mudsill (corner 1 to corner 2) - along Y axis
    mudsill_right = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 1, base_length_m, TimberLocationType.INSIDE, mudsill_size
    )
    mudsill_right.name = "Right Mudsill"

    # Back mudsill (corner 2 to corner 3) - along X axis
    mudsill_back = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 2, base_width_m, TimberLocationType.INSIDE, mudsill_size
    )
    mudsill_back.name = "Back Mudsill"

    # Left mudsill (corner 3 to corner 0) - along Y axis
    mudsill_left = create_axis_aligned_horizontal_timber_on_footprint(
        footprint, 3, base_length_m, TimberLocationType.INSIDE, mudsill_size
    )
    mudsill_left.name = "Left Mudsill"

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
        location_type=TimberLocationType.INSIDE,
        size=post_size
    )
    post_front_left.name = "Front Left Post"

    # Front-right post (on front boundary side, inset from right corner)
    post_front_right = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=0,
        distance_along_side=base_width_m - post_inset_m,
        length=post_front_height_m,
        location_type=TimberLocationType.INSIDE,
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
        location_type=TimberLocationType.INSIDE,
        size=post_size
    )
    post_back_right.name = "Back Right Post"

    # Back-left post (on back boundary side, inset from left corner)
    post_back_left = create_vertical_timber_on_footprint_side(
        footprint,
        side_index=2,
        distance_along_side=base_width_m - post_inset_m,
        length=post_back_height_m,
        location_type=TimberLocationType.INSIDE,
        size=post_size
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

