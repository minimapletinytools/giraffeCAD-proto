"""
Basic Joints Examples - Demonstration of all joint types in GiraffeCAD

This file contains one example function for each joint type.
Each joint is created from 90x90mm timbers that are 1m long,
axis-aligned with one timber going in +Y and another in +X direction.
"""

from sympy import Matrix, Rational
from typing import Union, List
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
    
    joint = cut_basic_butt_splice_joint_on_aligned_timbers(
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


def make_splice_lap_joint_example(position: V3) -> list[CutTimber]:
    """
    Create a splice lap joint example.
    Two timbers meet end-to-end with interlocking lap notches.
    
    Args:
        position: Center position of the joint (V3)
        
    Returns:
        List of CutTimber objects representing the joint
    """
    half_length = TIMBER_LENGTH / 2
    lap_length = TIMBER_SIZE * 3  # Lap extends 3x the timber width
    shoulder_distance = TIMBER_SIZE  # Shoulder starts 1x timber width from end
    
    # TimberA extends in +X direction from the center
    timberA = timber_from_directions(
        length=TIMBER_LENGTH,
        size=create_v2(TIMBER_SIZE, TIMBER_SIZE),
        bottom_position=position - create_v3(half_length, 0, 0),
        length_direction=create_v3(1, 0, 0),
        width_direction=create_v3(0, 1, 0),
        name="splice_lap_timberA"
    )
    
    # TimberB extends in +X direction, positioned to meet timberA end-to-end
    timberB = timber_from_directions(
        length=TIMBER_LENGTH,
        size=create_v2(TIMBER_SIZE, TIMBER_SIZE),
        bottom_position=position + create_v3(half_length, 0, 0),
        length_direction=create_v3(1, 0, 0),
        width_direction=create_v3(0, 1, 0),
        name="splice_lap_timberB"
    )
    
    # Create the splice lap joint
    # TimberA has material removed from BOTTOM face
    # TimberB has material removed from TOP face (opposite)
    joint = cut_basic_splice_lap_joint_on_aligned_timbers(
        top_lap_timber=timberA,
        top_lap_timber_end=TimberReferenceEnd.TOP,
        bottom_lap_timber=timberB,
        bottom_lap_timber_end=TimberReferenceEnd.BOTTOM,
        top_lap_timber_face=TimberFace.RIGHT,
        lap_length=lap_length,
        top_lap_shoulder_position_from_top_lap_shoulder_timber_end=lap_length/2,
        lap_depth=None  # Use default (half thickness)
    )
    
    return list(joint.cut_timbers.values())


def create_basic_joints_patternbook() -> PatternBook:
    """
    Create a PatternBook with all basic joint patterns.
    
    Each pattern has groups: ["basic_joints", "{joint_type}"]
    For example: ["basic_joints", "miter"] or ["basic_joints", "butt"]
    
    Returns:
        PatternBook: PatternBook containing all basic joint patterns
    """
    patterns = [
        (PatternMetadata("miter_joint", ["basic_joints", "miter"], "frame"),
         lambda center: Frame(cut_timbers=make_miter_joint_example(center), name="Miter Joint (67°)")),
        
        (PatternMetadata("miter_joint_face_aligned", ["basic_joints", "miter"], "frame"),
         lambda center: Frame(cut_timbers=make_miter_joint_face_aligned_example(center), name="Miter Joint (Face Aligned)")),
        
        (PatternMetadata("butt_joint", ["basic_joints", "butt"], "frame"),
         lambda center: Frame(cut_timbers=make_butt_joint_example(center), name="Butt Joint")),
        
        (PatternMetadata("splice_joint", ["basic_joints", "splice"], "frame"),
         lambda center: Frame(cut_timbers=make_splice_joint_example(center), name="Splice Joint")),
        
        (PatternMetadata("splice_lap_joint", ["basic_joints", "splice_lap"], "frame"),
         lambda center: Frame(cut_timbers=make_splice_lap_joint_example(center), name="Splice Lap Joint")),
        
        (PatternMetadata("house_joint", ["basic_joints", "house"], "frame"),
         lambda center: Frame(cut_timbers=make_house_joint_example(center), name="House Joint")),
        
        (PatternMetadata("cross_lap_joint", ["basic_joints", "cross_lap"], "frame"),
         lambda center: Frame(cut_timbers=make_cross_lap_joint_example(center), name="Cross Lap Joint")),
    ]
    
    return PatternBook(patterns=patterns)


def create_all_joint_examples() -> Union[Frame, List[CutCSG]]:
    """
    Create joint examples with automatic spacing starting from the origin.
    
    This now uses the PatternBook to raise all patterns in the "basic_joints" group.
    
    Returns:
        Frame or List[CutCSG]: Frame object containing all cut timbers for the enabled joints, or list of CSG objects
    """
    book = create_basic_joints_patternbook()
    
    # Raise all patterns in the "basic_joints" group with 2m spacing
    frame = book.raise_pattern_group("basic_joints", separation_distance=Rational(2))
    
    return frame


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
        num_cuts = len(cut_timber.cuts)
        print(f"{i+1:2d}. {timber.name:30s} | Cuts: {num_cuts} | Length: {float(timber.length):.2f}m")
