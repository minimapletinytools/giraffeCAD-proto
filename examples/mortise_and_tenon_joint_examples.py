"""
Example usage of mortise and tenon joint functions
"""

from sympy import Matrix, Rational
from code_goes_here.timber import (
    Timber, TimberReferenceEnd, TimberFace, timber_from_directions,
    create_vector3d, V2
)
from code_goes_here.mortise_and_tenon_joint import cut_simple_mortise_and_tenon
from code_goes_here.construction import create_axis_aligned_timber


def example_basic_mortise_and_tenon():
    """
    Create a basic mortise and tenon joint between a vertical post and horizontal beam.
    
    Configuration:
    - Tenon timber (vertical post): bottom point at origin (0,0,0), extends upward
    - Mortise timber (horizontal beam): centered at origin, extends along X axis
    """
    # Create a vertical post (tenon timber) with bottom at origin
    post = create_axis_aligned_timber(
        bottom_position=create_vector3d(0, 0, 0),
        length=Rational(100),
        size=Matrix([Rational(4), Rational(6)]),
        length_direction=TimberFace.TOP,  # Points upward in +Z direction
        width_direction=TimberFace.RIGHT,  # Width in +X direction
        name="Vertical Post"
    )
    
    # Create a horizontal beam (mortise timber) centered at origin
    # The beam extends along X axis with its center (not bottom) at origin
    beam_length = Rational(200)
    beam = create_axis_aligned_timber(
        bottom_position=create_vector3d(-beam_length / 2, 0, 0),  # Start at -100 so center is at 0
        length=beam_length,
        size=Matrix([Rational(6), Rational(8)]),
        length_direction=TimberFace.RIGHT,  # Points in +X direction
        width_direction=TimberFace.FORWARD,  # Width in +Y direction
        name="Horizontal Beam"
    )
    
    # Define tenon dimensions
    tenon_size = Matrix([Rational(2), Rational(3)])  # 2" x 3" tenon
    tenon_length = Rational(4)  # 4" long tenon
    mortise_depth = Rational(5)  # 5" deep mortise (slightly deeper than tenon)
    
    # Create the joint
    joint = cut_simple_mortise_and_tenon(
        tenon_timber=post,
        mortise_timber=beam,
        tenon_end=TimberReferenceEnd.TOP,  # Tenon cut on top end of post
        size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth
    )
    
    return joint


if __name__ == "__main__":
    # Run the example
    print("Creating basic mortise and tenon joint...")
    print("  Tenon timber: vertical post with bottom at origin (0,0,0)")
    print("  Mortise timber: horizontal beam centered at origin along X axis")
    
    joint = example_basic_mortise_and_tenon()
    print(f"\n✅ Created joint with {len(joint.partiallyCutTimbers)} timbers")
    
    # Display timber details
    for i, cut_timber in enumerate(joint.partiallyCutTimbers):
        timber = cut_timber.timber
        print(f"\n  Timber {i+1}: {timber.name}")
        print(f"    Position: ({float(timber.bottom_position[0])}, {float(timber.bottom_position[1])}, {float(timber.bottom_position[2])})")
        print(f"    Length: {float(timber.length)}")
        print(f"    Size: {float(timber.size[0])} x {float(timber.size[1])}")
        print(f"    Cuts: {len(cut_timber._cuts)}")

