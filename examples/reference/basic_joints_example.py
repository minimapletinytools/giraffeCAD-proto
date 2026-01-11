"""
Basic Joints Examples - Demonstration of all joint types in GiraffeCAD

This file contains one example function for each joint type.
Each joint is created from 90x90mm timbers that are 1m long,
axis-aligned with one timber going in +Y and another in +X direction.
"""

from sympy import Matrix, Rational
import sys
sys.path.append('../..')

from giraffe import *

# Standard timber dimensions (90mm x 90mm, 1m long)
TIMBER_SIZE = mm(90)  # 90mm
TIMBER_LENGTH = m(1)  # 1m


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
    timberA = timber_from_directions(
        name="MiterJoint_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - direction_A * half_length,
        length_direction=direction_A,
        width_direction=width_A
    )
    
    # TimberB extends from position in direction_B
    timberB = timber_from_directions(
        name="MiterJoint_TimberB",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - direction_B * half_length,
        length_direction=direction_B,
        width_direction=width_B
    )
    
    # Create miter joint at the ends that meet at position
    joint = cut_basic_miter_joint(timberA, TimberReferenceEnd.TOP, timberB, TimberReferenceEnd.TOP)
    
    return list(joint.cut_timbers.values())


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
    timberA = timber_from_directions(
        name="MiterFaceAligned_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([half_length, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # TimberB extends in +Y direction
    timberB = timber_from_directions(
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
    
    return list(joint.cut_timbers.values())


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
    receiving_timber = timber_from_directions(
        name="ButtJoint_Receiving",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([half_length, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # Butt timber extends in +Y direction, meeting the receiving timber
    butt_timber = timber_from_directions(
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
    
    return list(joint.cut_timbers.values())


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
    timberA = timber_from_directions(
        name="SpliceJoint_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([TIMBER_LENGTH, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])
    )
    
    # TimberB extends from position in +X direction (aligned with A)
    timberB = timber_from_directions(
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
    
    return list(joint.cut_timbers.values())


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
    offset = mm(20) 
    
    # Housing timber (beam) extends in +X direction
    # This is the timber that gets the groove cut into it
    housing_timber = timber_from_directions(
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
    housed_timber = timber_from_directions(
        name="HouseJoint_Housed",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([0, half_length, 0]) - Matrix([0, 0, offset]),
        length_direction=Matrix([0, 1, 0]),
        width_direction=Matrix([-1, 0, 0])
    )
    
    # Create house joint
    joint = cut_basic_house_joint(housing_timber, housed_timber)
    
    return list(joint.cut_timbers.values())


def make_cross_lap_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a cross lap joint where two timbers cross each other.
    Each timber is notched halfway through (cut_ratio=0.5) so they fit together flush.
    TimberA is positioned lower, TimberB is positioned higher, and they overlap in the middle.
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    half_length = TIMBER_LENGTH / 2
    half_height = TIMBER_SIZE / 2
    
    # TimberA extends in +X direction, bottom at Z=0 (relative to position)
    # Height direction is +Z, so top face is at Z=TIMBER_SIZE
    timberA = timber_from_directions(
        name="CrossLap_TimberA",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([half_length, 0, 0]),
        length_direction=Matrix([1, 0, 0]),
        width_direction=Matrix([0, 1, 0])  # Height direction becomes +Z
    )
    
    # TimberB extends in +Y direction, bottom at Z=half_height (relative to position)
    # This creates an overlap from Z=half_height to Z=TIMBER_SIZE
    # Height direction is +Z, so top face is at Z=half_height+TIMBER_SIZE
    timberB = timber_from_directions(
        name="CrossLap_TimberB",
        length=TIMBER_LENGTH,
        size=Matrix([TIMBER_SIZE, TIMBER_SIZE]),
        bottom_position=position - Matrix([0, half_length, 0]),
        length_direction=Matrix([0, 1, 0]),
        width_direction=Matrix([-1, 0, 0])  # Height direction becomes +Z
    )
    
    # Create cross lap joint with cut_ratio=0.5 (each timber cut halfway)
    # The function will auto-select FRONT face of timberA (+Z) and BACK face of timberB (-Z)
    # which oppose each other (dot product = -1 < 0)
    joint = cut_basic_cross_lap_joint(
        timberA, timberB,
        cut_ratio=Rational(1, 2),
        # these are coplanar timbers so it can not infer which side to cut
        # (you can determine which face is which by deriving from the length and width direction... or just ask the AI to help you figure it out)
        timberA_cut_face=TimberFace.FRONT,
        timberB_cut_face=TimberFace.BACK
    )
    
    return list(joint.cut_timbers.values())


def create_all_joint_examples() -> Frame:
    """
    Create joint examples with automatic spacing starting from the origin.
    
    To enable/disable specific joints, just comment/uncomment lines in the JOINTS_TO_RENDER list below.
    Joints will be positioned sequentially starting at the origin with 2m spacing.
    
    Returns:
        Frame: Frame object containing all cut timbers for the enabled joints
    """
    
    # ============================================================================
    # CONFIGURATION: Comment out lines to disable specific joints
    # 
    # Example: To render only Miter and House joints:
    #   JOINTS_TO_RENDER = [
    #       ("Miter Joint (67°)", make_miter_joint_example),
    #       # ("Miter Joint (Face Aligned)", make_miter_joint_face_aligned_example),
    #       # ("Butt Joint", make_butt_joint_example),
    #       # ("Splice Joint", make_splice_joint_example),
    #       ("House Joint", make_house_joint_example),
    #   ]
    # Result: Joints will be at x=0.0m and x=2.0m (automatically spaced)
    # ============================================================================
    JOINTS_TO_RENDER = [
        ("Miter Joint (67°)", make_miter_joint_example),
        ("Miter Joint (Face Aligned)", make_miter_joint_face_aligned_example),
        ("Butt Joint", make_butt_joint_example),
        ("Splice Joint", make_splice_joint_example),
        ("House Joint", make_house_joint_example),
        ("Cross Lap Joint", make_cross_lap_joint_example),  # Not yet implemented
    ]
    
    # Spacing between joints (in meters)
    SPACING = Rational(2)
    
    # ============================================================================
    # Render enabled joints starting from origin
    # ============================================================================
    all_timbers = []
    current_position_x = 0
    
    for joint_name, joint_function in JOINTS_TO_RENDER:
        position = create_v3(current_position_x, 0, 0)
        timbers = joint_function(position)
        all_timbers.extend(timbers)
        
        print(f"Created {joint_name} at x={float(current_position_x):.1f}m")
        
        # Move to next position
        current_position_x += SPACING
    
    return Frame(
        cut_timbers=all_timbers,
        name="Basic Joints Examples"
    )


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
    frame = create_all_joint_examples()
    
    print()
    print("="*70)
    print(f"Total timbers created: {len(frame.cut_timbers)}")
    print("="*70)
    
    # Print summary of each timber
    for i, cut_timber in enumerate(frame.cut_timbers):
        timber = cut_timber.timber
        num_cuts = len(cut_timber._cuts)
        print(f"{i+1:2d}. {timber.name:30s} | Cuts: {num_cuts} | Length: {float(timber.length):.2f}m")
