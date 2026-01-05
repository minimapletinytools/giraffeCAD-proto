"""
Tests for mortise and tenon joint construction functions
"""

import pytest
from typing import List
from sympy import Matrix, Rational, simplify
from code_goes_here.moothymoth import Orientation
from code_goes_here.timber import (
    Timber, TimberReferenceEnd, TimberFace, TimberReferenceLongFace,
    V2, V3, Numeric, PegShape, WedgeShape, Peg,
    timber_from_directions, create_vector3d
)
from code_goes_here.mortise_and_tenon_joint import (
    SimplePegParameters,
    WedgeParameters,
    cut_mortise_and_tenon_many_options_do_not_call_me_directly,
    cut_mortise_and_tenon_joint_on_face_aligned_timbers
)
from .helperonis import (
    create_standard_vertical_timber,
    create_standard_horizontal_timber,
    assert_vectors_perpendicular
)



# ============================================================================
# Helper Functions for CSG Testing
# ============================================================================

# TODO DELETE replace with timber.global_to_local
def transform_point_to_local(point_world: V3, timber: Timber) -> V3:
    """Transform a point from world coordinates to timber local coordinates."""
    return timber.orientation.matrix.T * (point_world - timber.bottom_position)


def sample_points_in_box(center: V3, size: V3, num_samples: int = 5) -> List[V3]:
    """
    Generate test points within a box.
    
    Args:
        center: Center of the box (3x1 Matrix)
        size: Size of the box [width, height, depth] (3x1 Matrix)
        num_samples: Number of samples per dimension
        
    Returns:
        List of points distributed throughout the box
    """
    points = []
    half_size = size / 2
    
    # Sample along each axis
    for i in range(num_samples):
        t = Rational(i, num_samples - 1) if num_samples > 1 else Rational(1, 2)
        offset = (t - Rational(1, 2)) * 2  # Map [0,1] to [-1, 1]
        
        # Sample along X axis
        points.append(center + Matrix([half_size[0] * offset, 0, 0]))
        # Sample along Y axis  
        points.append(center + Matrix([0, half_size[1] * offset, 0]))
        # Sample along Z axis
        points.append(center + Matrix([0, 0, half_size[2] * offset]))
    
    # Add center point
    points.append(center)
    
    return points


# ============================================================================
# Tests for Mortise and Tenon Joint Geometry
# ============================================================================

class TestMortiseAndTenonGeometry:
    pass
    



# ============================================================================
# Tests for Peg Orientation
# ============================================================================

class TestPegStuff:
    # 🐪
    def test_simple_peg_basic_stuff(self):
        """Test that peg is perpendicular to the face it goes through."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_depth = Rational(7)
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(Rational(2), Rational(0))],
            depth=peg_depth,
            size=Rational(1, 2)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        peg = joint.jointAccessories[0]
        
        # check that the peg is orthogonal to get_face_direction(TimberFace.FRONT)
        assert_vectors_perpendicular(peg.orientation.matrix[:, 2], tenon_timber.get_face_direction(TimberFace.FRONT))
        f"Peg forward_length should match specified depth. Expected {peg_depth}, got {peg.forward_length}"
        assert peg.stickout_length == peg_depth * Rational(1, 2), \
            f"Peg stickout_length should be half of forward_length by default. Expected {peg_depth * Rational(1, 2)}, got {peg.stickout_length}"


        
        # Get tenon timber's cut CSG (what's removed)
        tenon_cut_timber = joint.cut_timbers[1]
        tenon_cut_csg = tenon_cut_timber._cuts[0].negative_csg
        
        # Verify CSG includes peg holes (should be a Union with multiple children)
        from code_goes_here.meowmeowcsg import Union
        assert isinstance(tenon_cut_csg, Union), \
            "Tenon cut CSG with pegs should be a Union"
        assert len(tenon_cut_csg.children) >= 2, \
            "Union should contain base cut plus peg holes"

    def test_peg_geometry(self):
        """Test points on peg hole boundary using is_point_on_boundary()."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_size = Rational(1, 2)
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(Rational(2), Rational(0))],
            depth=Rational(5),
            size=peg_size
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        peg = joint.jointAccessories[0]
        peg_csg = peg.render_csg_local()

        # Sample points within the peg's CSG
        peg_center_points = [
            peg.position + peg.orientation.matrix * Matrix([0, 0, Rational(1)]),  # 1 unit along peg
            peg.position + peg.orientation.matrix * Matrix([0, 0, Rational(2)]),  # 2 units along peg
            peg.position + peg.orientation.matrix * Matrix([0, 0, Rational(3)]),  # 3 units along peg
        ]
        
        for point_local in peg_center_points:
            # Transform to peg's local space (peg CSG is in its own local coords)
            point_peg_local = peg.orientation.matrix.T * (point_local - peg.position)
            assert peg_csg.contains_point(point_peg_local), \
                f"Point along peg centerline should be in peg CSG"
    
        # For a square peg, points on the edge should be on boundary
        # Peg is peg_size x peg_size in cross-section
        half_size = peg_size / 2
        
        # Point on the edge of the square peg at z=1
        point_on_edge = peg.position + peg.orientation.matrix * Matrix([half_size, 0, Rational(1)])
        point_on_edge_peg_local = peg.orientation.matrix.T * (point_on_edge - peg.position)
        
        # This point should be on the boundary of the peg
        assert peg_csg.contains_point(point_on_edge_peg_local), \
            "Point on peg edge should be contained in peg CSG"
        assert peg_csg.is_point_on_boundary(point_on_edge_peg_local), \
            "Point on peg edge should be on boundary of peg CSG"

    
    def test_peg_position_from_shoulder(self):
        """Test that peg is positioned along the tenon."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )

        mortise_timber_x_size = Rational(6)
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, mortise_timber_x_size), position=(0, 0, 50)
        )
        shoulder_plane_x_global = mortise_timber_x_size / Rational(2)

        
        distance_from_shoulder = Rational(4)
        tenon_length = Rational(4)
        
        peg_params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(distance_from_shoulder, Rational(0))],
            depth=Rational(5),
            size=Rational(1, 2)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=tenon_length,
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        peg = joint.jointAccessories[0]
        
        # Verify peg exists and has reasonable position
        assert peg.position is not None, "Peg should have a position"
        
        # Transform peg position from mortise local to world
        peg_position_world = peg.position
        print(peg_position_world)
        
        # TODO uncomment once you fix peg positioning...
        #assert peg_position_world[0] == shoulder_plane_x_global - distance_from_shoulder
    
    def test_peg_position_from_centerline(self):
        """Test that peg is offset by correct distance from centerline."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        distance_from_centerline = Rational(1, 2)
        
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(Rational(2), distance_from_centerline)],
            depth=Rational(5),
            size=Rational(1, 4)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        peg = joint.jointAccessories[0]
        
        # The peg should be offset from the tenon centerline
        # For a peg through the FRONT face, the lateral axis is X
        # Transform peg position to world coords
        peg_position_world = mortise_timber.bottom_position + mortise_timber.orientation.matrix * peg.position
        
        # Expected X position: tenon is centered at x=0, offset by distance_from_centerline
        expected_x_world = distance_from_centerline
        
        x_diff = abs(peg_position_world[0] - expected_x_world)
        assert x_diff < Rational(1, 10), \
            f"Peg should be at x={expected_x_world}, but is at x={peg_position_world[0]}"
    
    def test_multiple_pegs(self):
        """Test joint with multiple pegs at different positions."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[
                (Rational(1), Rational(0)),
                (Rational(2), Rational(1, 2)),
                (Rational(3), Rational(-1, 2))
            ],
            depth=Rational(5),
            size=Rational(1, 2)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        # Should have 3 peg accessories
        assert len(joint.jointAccessories) == 3, \
            f"Should have 3 pegs, got {len(joint.jointAccessories)}"
        
        # All should be Peg objects
        for accessory in joint.jointAccessories:
            assert isinstance(accessory, Peg), \
                "All accessories should be Peg objects"
        
        # Each peg should have correct depth
        for peg in joint.jointAccessories:
            assert peg.forward_length == Rational(5), \
                f"Each peg should have depth 5, got {peg.forward_length}"


# ============================================================================
# Tests for Various Joint Configurations
# ============================================================================

class TestJointConfigurations:
    """Test various joint setups and configurations."""
    
    def test_joint_with_top_end_tenon(self):
        """Test joint with tenon_end=TimberReferenceEnd.TOP."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(5)
        )
        
        assert joint is not None
        assert len(joint.cut_timbers) == 2
        
        # Verify the end cut is on the TOP
        tenon_cut_timber = joint.cut_timbers[1]
        assert tenon_cut_timber._cuts[0].maybe_end_cut == TimberReferenceEnd.TOP
    
    def test_joint_with_bottom_end_tenon(self):
        """Test joint with tenon_end=TimberReferenceEnd.BOTTOM."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 50)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(5)
        )
        
        assert joint is not None
        assert len(joint.cut_timbers) == 2
        
        # Verify the end cut is on the BOTTOM
        tenon_cut_timber = joint.cut_timbers[1]
        assert tenon_cut_timber._cuts[0].maybe_end_cut == TimberReferenceEnd.BOTTOM
    
    def test_joint_with_offset_tenon(self):
        """Test tenon_position parameter with non-zero offset."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(6, 6), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(8, 8), position=(0, 0, 50)
        )
        
        # Offset the tenon from center
        tenon_position = Matrix([Rational(1), Rational(-1)])
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(5),
            tenon_position=tenon_position
        )
        
        assert joint is not None
        
        # Get the mortise CSG
        mortise_cut_timber = joint.cut_timbers[0]
        mortise_csg = mortise_cut_timber._cuts[0].negative_csg
        
        # The mortise should be offset according to tenon_position
        # Test that the center of the mortise is offset
        # The mortise is at z=50 where the tenon meets it
        # In world coords, the offset point should be in the mortise
        point_at_offset = Matrix([tenon_position[0], tenon_position[1], Rational(50)])
        point_at_offset_local = transform_point_to_local(point_at_offset, mortise_timber)
        
        assert mortise_csg.contains_point(point_at_offset_local), \
            "Offset tenon position should result in offset mortise"
    
    def test_joint_with_pegs_on_forward_face(self):
        """Test pegs on FRONT face."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(Rational(2), Rational(0))],
            depth=Rational(5),
            size=Rational(1, 2)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        assert len(joint.jointAccessories) == 1

