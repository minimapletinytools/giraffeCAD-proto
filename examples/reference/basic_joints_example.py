"""
Basic Joints Examples - Demonstration of all joint types in GiraffeCAD

This file contains one example function for each joint type.
Each joint is created from 90x90mm timbers that are 1m long,
axis-aligned with one timber going in +Y and another in +X direction.
"""

from sympy import Matrix, Rational
import sys
sys.path.append('../..')

from giraffe import (
    Timber, CutTimber, Joint,
    TimberReferenceEnd, TimberFace,
    create_vector3d
)
from code_goes_here.basic_joints import (
    cut_basic_miter_joint,
    cut_basic_miter_joint_on_face_aligned_timbers,
    cut_basic_corner_joint_on_face_aligned_timbers,
    cut_basic_butt_joint_on_face_aligned_timbers,
    cut_basic_splice_joint_on_aligned_timbers,
    cut_basic_cross_lap_joint,
    cut_basic_house_joint
)

# Type alias
V3 = Matrix

# Standard timber dimensions (90mm x 90mm, 1m long)
TIMBER_SIZE = Rational(90, 1000)  # 90mm in meters
TIMBER_LENGTH = Rational(1)  # 1m


def make_miter_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a basic miter joint example with non-axis-aligned timbers.
    Two timbers meet at their ends with a miter cut, at 77 degrees apart.
    This demonstrates the general miter joint (non-face-aligned case).
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    from sympy import cos, sin, pi, sqrt
    
    half_length = TIMBER_LENGTH / 2
    
    # Angle in radians (67 degrees)
    angle_deg = 67
    angle_rad = angle_deg * pi / 180
    
    # TimberA extends at 0 degrees (along +X axis)
    direction_A = Matrix([1, 0, 0])
    
    # TimberB extends at 77 degrees from TimberA (rotated counterclockwise in XY plane)
    direction_B = Matrix([cos(angle_rad), sin(angle_rad), 0])
    
    # Calculate perpendicular directions in XY plane for width directions
    # For direction (dx, dy, 0), perpendicular is (-dy, dx, 0)
    width_A = Matrix([0, 1, 0])  # Perpendicular to direction_A
    width_B = Matrix([-sin(angle_rad), cos(angle_rad), 0])  # Perpendicular to direction_B
    
    # TimberA extends from position in direction_A
    timberA = Timber(
        name="MiterJoint_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - direction_A * half_length,
        length_direction=direction_A,
        width_direction=width_A
    )
    
    # TimberB extends from position in direction_B
    timberB = Timber(
        name="MiterJoint_TimberB",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - direction_B * half_length,
        length_direction=direction_B,
        width_direction=width_B
    )
    
    # Create miter joint at the ends that meet at position
    joint = cut_basic_miter_joint(timberA, TimberReferenceEnd.TOP, timberB, TimberReferenceEnd.TOP)
    
    return joint.partiallyCutTimbers


def make_miter_joint_face_aligned_example(position: V3) -> list[CutTimber]:
    """
    Create a miter joint for face-aligned timbers.
    Similar to basic miter but specifically for face-aligned configurations.
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    half_length = TIMBER_LENGTH / 2
    
    # TimberA extends in +X direction
    timberA = Timber(
        name="MiterFaceAligned_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([half_length, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # TimberB extends in +Y direction
    timberB = Timber(
        name="MiterFaceAligned_TimberB",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([0, half_length, 0]),
        length_direction=Matrix([0, 1, 0]),
        width_direction=Matrix([-1, 0, 0])
    )
    
    joint = cut_basic_miter_joint_on_face_aligned_timbers(
        timberA, TimberReferenceEnd.TOP, 
        timberB, TimberReferenceEnd.TOP
    )
    
    return joint.partiallyCutTimbers


def make_corner_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a corner joint for face-aligned timbers.
    One timber is cut at an angle, the other remains uncut.
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    half_length = TIMBER_LENGTH / 2
    
    # TimberA extends in +X direction
    timberA = Timber(
        name="CornerJoint_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([half_length, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # TimberB extends in +Y direction
    timberB = Timber(
        name="CornerJoint_TimberB",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([0, half_length, 0]),
        length_direction=Matrix([0, 1, 0]),
        width_direction=Matrix([-1, 0, 0])
    )
    
    joint = cut_basic_corner_joint_on_face_aligned_timbers(
        timberA, TimberReferenceEnd.TOP,
        timberB, TimberReferenceEnd.TOP
    )
    
    return joint.partiallyCutTimbers


def make_butt_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a butt joint where one timber butts into another.
    The butt timber is cut square; the receiving timber is uncut.
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    half_length = TIMBER_LENGTH / 2
    
    # Receiving timber extends in +X direction (horizontal)
    receiving_timber = Timber(
        name="ButtJoint_Receiving",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([half_length, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # Butt timber extends in +Y direction, meeting the receiving timber
    butt_timber = Timber(
        name="ButtJoint_Butt",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([0, half_length, 0]),
        length_direction=Matrix([0, 1, 0]),
        width_direction=Matrix([-1, 0, 0])
    )
    
    joint = cut_basic_butt_joint_on_face_aligned_timbers(
        receiving_timber, 
        butt_timber, 
        TimberReferenceEnd.TOP
    )
    
    return joint.partiallyCutTimbers


def make_splice_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a splice joint where two aligned timbers are joined end-to-end.
    Both timbers are cut at angles to create a scarf joint.
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    half_length = TIMBER_LENGTH / 2
    
    # TimberA extends from left in +X direction
    timberA = Timber(
        name="SpliceJoint_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([TIMBER_LENGTH, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # TimberB extends from position in +X direction (aligned with A)
    timberB = Timber(
        name="SpliceJoint_TimberB",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position,
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    joint = cut_basic_splice_joint_on_aligned_timbers(
        timberA, TimberReferenceEnd.TOP,
        timberB, TimberReferenceEnd.BOTTOM,
        splice_point=position  # Meet at the specified position
    )
    
    return joint.partiallyCutTimbers


def make_house_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a housed joint (also called housing joint or dado joint).
    One timber (housing timber) gets a rectangular groove cut into it,
    and the other timber (housed timber) fits into that groove.
    
    This is commonly used for shelves fitting into uprights.
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    half_length = TIMBER_LENGTH / 2
    offset = Rational(20, 1000) 
    
    # Housing timber (beam) extends in +X direction
    # This is the timber that gets the groove cut into it
    housing_timber = Timber(
        name="HouseJoint_Housing",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([half_length, 0, 0]) + Matrix([0, 0, offset]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # Housed timber (shelf) extends in +Y direction, crossing through the housing timber
    # This timber fits into the groove and remains uncut
    # Offset by 45mm vertically so they intersect properly
    housed_timber = Timber(
        name="HouseJoint_Housed",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([0, half_length, 0]) - Matrix([0, 0, offset]),
        length_direction=Matrix([0, 1, 0]),
        width_direction=Matrix([-1, 0, 0])
    )
    
    # Create house joint
    joint = cut_basic_house_joint(housing_timber, housed_timber)
    
    return joint.partiallyCutTimbers


def make_cross_lap_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a cross lap joint where two timbers cross each other.
    Each timber is notched halfway through so they fit together flush.
    
    NOTE: This joint type is not yet implemented in basic_joints.py
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint (empty until implemented)
    """
    # TODO: Implement when cut_basic_cross_lap_joint is complete
    print("  (Cross Lap Joint not yet implemented - skipped)")
    return []
    
    # Implementation will look like this once available:
    # half_length = TIMBER_LENGTH / 2
    # 
    # timberA = Timber(
    #     name="CrossLap_TimberA",
    #     length=TIMBER_LENGTH,
    #     size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
    #     bottom_position=position - Matrix([half_length, 0, 0]),
    #     length_direction=Matrix([1, 0, 0]),
    #     width_direction=Matrix([0, 1, 0])
    # )
    # 
    # timberB = Timber(
    #     name="CrossLap_TimberB",
    #     length=TIMBER_LENGTH,
    #     size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
    #     bottom_position=position - Matrix([0, half_length, 0]),
    #     length_direction=Matrix([0, 1, 0]),
    #     width_direction=Matrix([-1, 0, 0])
    # )
    # 
    # joint = cut_basic_cross_lap_joint(
    #     timberA, timberB,
    #     cut_ratio=Rational(1, 2)
    # )
    # 
    # return joint.partiallyCutTimbers


def create_all_joint_examples() -> list[CutTimber]:
    """
    Create all joint examples with spacing so they don't overlap.
    
    Returns:
        List of all CutTimber objects for all joints
    """
    all_timbers = []
    
    # Space joints 2 meters apart in the X direction
    spacing = Rational(2)
    
    # Joint 1: Miter Joint at origin
    position_1 = create_vector3d(0, 0, 0)
    all_timbers.extend(make_miter_joint_example(position_1))
    print(f"Created Miter Joint at {position_1.T}")
    
    # Joint 2: Miter Joint (Face Aligned)
    position_2 = create_vector3d(spacing, 0, 0)
    all_timbers.extend(make_miter_joint_face_aligned_example(position_2))
    print(f"Created Miter Joint (Face Aligned) at {position_2.T}")
    
    # Joint 3: Corner Joint
    position_3 = create_vector3d(spacing * 2, 0, 0)
    all_timbers.extend(make_corner_joint_example(position_3))
    print(f"Created Corner Joint at {position_3.T}")
    
    # Joint 4: Butt Joint
    position_4 = create_vector3d(spacing * 3, 0, 0)
    all_timbers.extend(make_butt_joint_example(position_4))
    print(f"Created Butt Joint at {position_4.T}")
    
    # Joint 5: Splice Joint
    position_5 = create_vector3d(spacing * 4, 0, 0)
    all_timbers.extend(make_splice_joint_example(position_5))
    print(f"Created Splice Joint at {position_5.T}")
    
    # Joint 6: House Joint (Housed/Housing/Dado Joint)
    position_6 = create_vector3d(spacing * 5, 0, 0)
    all_timbers.extend(make_house_joint_example(position_6))
    print(f"Created House Joint at {position_6.T}")
    
    # Joint 7: Cross Lap Joint (not yet implemented)
    position_7 = create_vector3d(spacing * 6, 0, 0)
    print(f"Skipping Cross Lap Joint at {position_7.T}")
    all_timbers.extend(make_cross_lap_joint_example(position_7))
    
    return all_timbers


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("GiraffeCAD - Basic Joints Examples")
    print("="*70)
    print(f"Timber dimensions: {float(TIMBER_SIZE*1000):.0f}mm x {float(TIMBER_SIZE*1000):.0f}mm")
    print(f"Timber length: {float(TIMBER_LENGTH):.1f}m")
    print()
    
    # Create all examples
    all_cut_timbers = create_all_joint_examples()
    
    print()
    print("="*70)
    print(f"Total timbers created: {len(all_cut_timbers)}")
    print("="*70)
    
    # Print summary of each timber
    for i, cut_timber in enumerate(all_cut_timbers):
        timber = cut_timber.timber
        num_cuts = len(cut_timber._cuts)
        print(f"{i+1:2d}. {timber.name:30s} | Cuts: {num_cuts} | Length: {float(timber.length):.2f}m")
    
    print()
    print("Examples are spaced 2m apart along the X-axis starting at origin.")
    print()
    print("Joint configurations:")
    print("  • Miter Joint: 67° angle (non-axis-aligned)")
    print("  • House Joint: Housing timber gets groove, housed timber fits in (like shelf in upright)")
    print("  • Other joints: Right angles (+X and +Y directions)")

