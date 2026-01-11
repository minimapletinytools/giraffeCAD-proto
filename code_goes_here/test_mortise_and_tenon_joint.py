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
    timber_from_directions, create_v3
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
    create_centered_horizontal_timber,
    assert_vectors_parallel
)

# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def simple_T_configuration():
    """
    Creates a simple T-configuration with a vertical tenon timber 
    and a horizontal mortise timber centered at the top.
    
    Returns:
        tuple: (tenon_timber, mortise_timber)
            - tenon_timber: Vertical 4x4 timber, height 100, at origin
            - mortise_timber: Horizontal 6x6 timber, length 100, along x-axis
    """
    tenon_timber = create_standard_vertical_timber(
        height=100, size=(4, 4), position=(0, 0, 0)
    )
    mortise_timber = create_centered_horizontal_timber(
        direction='x', length=100, size=(6, 6)
    )
    return (tenon_timber, mortise_timber)


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
    
    def test_mortise_tenon_centerline_containment(self, simple_T_configuration):
        """
        Test points along the tenon centerline to verify correct joint geometry.
        
        Measuring from the shoulder of the joint along the centerline of the tenon timber, we expect:
        - Points in [0,4] should be in tenon but not mortise (tenon part)
        - Points in (4,5) should be in neither (gap between tenon and mortise  depth)
        - Points in [5,6] should be in neither (inside the mortise hole)
        
        This tests that the tenon length and mortise depth are correctly implemented.
        """
        tenon_timber, mortise_timber = simple_T_configuration
        
        mortise_depth = Rational(5)
        tenon_length = Rational(4)
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=tenon_length,
            mortise_depth=mortise_depth
        )
        
        # Get the CSGs for the cut timbers (these are the REMAINING material after cuts)
        tenon_csg = joint.cut_timbers["tenon_timber"].render_timber_with_cuts_csg_local()
        mortise_csg = joint.cut_timbers["mortise_timber"].render_timber_with_cuts_csg_local()

        joint_shoulder_global = create_v3(Rational(0), Rational(0), Rational(3))
        
        # Verify basic tenon geometry: tenon should exist from z=0 upward
        # Test that center points are in the tenon at the bottom
        for z in [Rational(0), Rational(1), Rational(2), Rational(3)]:
            point_global = joint_shoulder_global - create_v3(Rational(0), Rational(0), z)
            point_tenon_local = tenon_timber.global_to_local(point_global)
            point_mortise_local = mortise_timber.global_to_local(point_global)
            assert tenon_csg.contains_point(point_tenon_local), \
                f"Point at z={z} should be in tenon centerline"
            assert not mortise_csg.contains_point(point_mortise_local), \
                f"Point at z={z} should not be in mortise centerline"
        
        for z in [Rational(4.2), Rational(4.8)]:
            point_global = joint_shoulder_global - create_v3(Rational(0), Rational(0), z)
            point_tenon_local = tenon_timber.global_to_local(point_global)
            point_mortise_local = mortise_timber.global_to_local(point_global)
            assert not tenon_csg.contains_point(point_tenon_local), \
                f"Point at z={z} should not be in tenon centerline"
            assert not mortise_csg.contains_point(point_mortise_local), \
                f"Point at z={z} should not be in mortise centerline"
        
        for z in [Rational(5), Rational(6)]:
            point_global = joint_shoulder_global - create_v3(Rational(0), Rational(0), z)
            point_tenon_local = tenon_timber.global_to_local(point_global)
            point_mortise_local = mortise_timber.global_to_local(point_global)
            assert not tenon_csg.contains_point(point_tenon_local), \
                f"Point at z={z} should not be in tenon centerline"
            assert mortise_csg.contains_point(point_mortise_local), \
                f"Point at z={z} should be in mortise centerline"
    



# ============================================================================
# Tests for Peg Orientation
# ============================================================================

class TestPegStuff:
    # 🐪
    def test_simple_peg_basic_stuff(self, simple_T_configuration):
        """Test that peg is perpendicular to the face it goes through."""
        tenon_timber, mortise_timber = simple_T_configuration
        
        peg_depth = Rational(7)
        distance_from_shoulder = Rational(2)
        mortise_timber_x_size = mortise_timber.size[0]
        shoulder_plane_x_global = mortise_timber_x_size / Rational(2)
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(distance_from_shoulder, Rational(0))],
            depth=peg_depth,
            size=Rational(1, 2)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )

        assert joint.cut_timbers["tenon_timber"].timber == tenon_timber
        assert joint.cut_timbers["mortise_timber"].timber == mortise_timber
        assert len(joint.cut_timbers["tenon_timber"]._cuts) == 1
        assert len(joint.cut_timbers["mortise_timber"]._cuts) == 1
        assert joint.cut_timbers["tenon_timber"]._cuts[0].maybe_end_cut == TimberReferenceEnd.BOTTOM
        assert joint.cut_timbers["mortise_timber"]._cuts[0].maybe_end_cut == None
        
        peg = joint.jointAccessories["peg_0"]
        
        # check that the peg is orthogonal to get_face_direction(TimberFace.FRONT)
        assert_vectors_parallel(peg.transform.orientation.matrix[:, 2], tenon_timber.get_face_direction(TimberFace.FRONT))
        f"Peg forward_length should match specified depth. Expected {peg_depth}, got {peg.forward_length}"
        assert peg.stickout_length == peg_depth * Rational(1, 2), \
            f"Peg stickout_length should be half of forward_length by default. Expected {peg_depth * Rational(1, 2)}, got {peg.stickout_length}"

        # check that the peg is positioned at the correct distance from the shoulder
        assert peg.transform.position[2] == shoulder_plane_x_global - distance_from_shoulder

        # Get tenon timber's cut CSG (what's removed)
        tenon_cut_timber = joint.cut_timbers["mortise_timber"]
        tenon_cut_csg = tenon_cut_timber._cuts[0].negative_csg
        
        # Verify CSG includes peg holes (should be a Union with multiple children)
        from code_goes_here.meowmeowcsg import Union
        assert isinstance(tenon_cut_csg, Union), \
            "Tenon cut CSG with pegs should be a Union"
        assert len(tenon_cut_csg.children) >= 2, \
            "Union should contain base cut plus peg holes"

    # 🐪
    def test_peg_geometry(self, simple_T_configuration):
        """Test points on peg hole boundary using is_point_on_boundary()."""
        tenon_timber, mortise_timber = simple_T_configuration
        
        peg_size = Rational(1, 2)
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(Rational(2), Rational(0))],
            depth=None,
            size=peg_size
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        peg = joint.jointAccessories["peg_0"]
        peg_csg = peg.render_csg_local()

        # Sample points within the peg's CSG
        peg_center_points = [
            peg.transform.position + peg.transform.orientation.matrix * Matrix([0, 0, Rational(1)]),  # 1 unit along peg
            peg.transform.position + peg.transform.orientation.matrix * Matrix([0, 0, Rational(2)]),  # 2 units along peg
            peg.transform.position + peg.transform.orientation.matrix * Matrix([0, 0, Rational(3)]),  # 3 units along peg
        ]
        
        for point_local in peg_center_points:
            # Transform to peg's local space (peg CSG is in its own local coords)
            point_peg_local = peg.transform.orientation.matrix.T * (point_local - peg.transform.position)
            assert peg_csg.contains_point(point_peg_local), \
                f"Point along peg centerline should be in peg CSG"
    
        # For a square peg, points on the edge should be on boundary
        # Peg is peg_size x peg_size in cross-section
        half_size = peg_size / 2
        
        # Point on the edge of the square peg at z=1
        point_on_edge = peg.transform.position + peg.transform.orientation.matrix * Matrix([half_size, 0, Rational(1)])
        point_on_edge_peg_local = peg.transform.orientation.matrix.T * (point_on_edge - peg.transform.position)

        # see that the peg total length is equal to 1.5 times the mortise width
        assert peg.forward_length + peg.stickout_length == Rational(3, 2) * mortise_timber.size[0]
        
        # This point should be on the boundary of the peg
        assert peg_csg.contains_point(point_on_edge_peg_local), \
            "Point on peg edge should be contained in peg CSG"
        assert peg_csg.is_point_on_boundary(point_on_edge_peg_local), \
            "Point on peg edge should be on boundary of peg CSG"

        
        
        
        for i in range(0,10):
            # Test that a point inside the peg hole is NOT contained in the timber CSGs
            point_in_peg_hole = peg.transform.position + peg.transform.orientation.matrix * Matrix([0, 0, Rational(i)])
            point_in_peg_hole_tenon_local = tenon_timber.global_to_local(point_in_peg_hole)
            point_in_peg_hole_mortise_local = mortise_timber.global_to_local(point_in_peg_hole)
            
            tenon_csg = joint.cut_timbers["tenon_timber"].render_timber_with_cuts_csg_local()
            mortise_csg = joint.cut_timbers["mortise_timber"].render_timber_with_cuts_csg_local()
            
            assert not tenon_csg.contains_point(point_in_peg_hole_tenon_local), \
                "Point inside peg hole should not be contained in tenon timber"
            assert not mortise_csg.contains_point(point_in_peg_hole_mortise_local), \
                "Point inside peg hole should not be contained in mortise timber"
            
    
    
    # 🐪
    def test_multiple_pegs(self, simple_T_configuration):
        """Test joint with multiple pegs at different positions."""
        tenon_timber, mortise_timber = simple_T_configuration
        
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
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        # Should have 3 peg accessories
        assert len(joint.jointAccessories) == 3, \
            f"Should have 3 pegs, got {len(joint.jointAccessories)}"
        
        # All should be Peg objects
        for accessory in joint.jointAccessories.values():
            assert isinstance(accessory, Peg), \
                "All accessories should be Peg objects"
        
        # Each peg should have correct depth
        for peg in joint.jointAccessories.values():
            assert peg.forward_length == Rational(5), \
                f"Each peg should have depth 5, got {peg.forward_length}"
    
    # 🐪
    def test_peg_with_tenon_hole_offset(self, simple_T_configuration):
        """Test that tenon_hole_offset shifts the peg hole in the tenon towards the shoulder."""
        tenon_timber, mortise_timber = simple_T_configuration
        
        distance_from_shoulder = Rational(2)
        offset = Rational(1, 4)  # 0.25 units offset
        
        # Create joint with offset
        peg_params_with_offset = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(distance_from_shoulder, Rational(0))],
            depth=Rational(5),
            size=Rational(1, 2),
            tenon_hole_offset=offset
        )
        
        joint_with_offset = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params_with_offset
        )
        
        # Create joint without offset for comparison
        peg_params_no_offset = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FRONT,
            peg_positions=[(distance_from_shoulder, Rational(0))],
            depth=Rational(5),
            size=Rational(1, 2),
            tenon_hole_offset=Rational(0)
        )
        
        joint_no_offset = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params_no_offset
        )
        
        # TODO test actual stuff here