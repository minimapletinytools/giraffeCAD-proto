"""
Tests for mortise and tenon joint construction functions
"""

import pytest
from typing import List
from sympy import Matrix, Rational, simplify, sin, cos, pi
from code_goes_here.rule import Orientation, create_v2, inches, radians, are_vectors_parallel, zero_test, safe_dot_product, normalize_vector
from code_goes_here.timber import (
    Timber, TimberReferenceEnd, TimberFace, TimberLongFace,
    V2, V3, Numeric, PegShape, WedgeShape, Peg,
    timber_from_directions, create_v3
)
from code_goes_here.construction import ButtJointTimberArrangement
from code_goes_here.timber_shavings import are_timbers_plane_aligned
from code_goes_here.joints.mortise_and_tenon_joint import (
    SimplePegParameters,
    WedgeParameters,
    PegPositionSpace,
    _does_shoulder_plane_need_notching,
    cut_mortise_and_tenon_joint_on_FAT,
    cut_mortise_and_tenon_joint_on_PAT,
    measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber,
)
from tests.testing_shavings import (
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
        height=100, size=(4, 4), position=(0, 0, 0), ticket="tenon_timber"
    )
    mortise_timber = create_centered_horizontal_timber(
        direction='x', length=100, size=(6, 6), name="mortise_timber"
    )
    return (tenon_timber, mortise_timber)


# ============================================================================
# Helper Functions for CSG Testing
# ============================================================================

# TODO DELETE replace with timber.global_to_local
def transform_point_to_local(point_world: V3, timber: Timber) -> V3:
    """Transform a point from world coordinates to timber local coordinates."""
    return timber.orientation.matrix.T * (point_world - timber.get_bottom_position_global())


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
        arrangement = ButtJointTimberArrangement(
            receiving_timber=mortise_timber,
            butt_timber=tenon_timber,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
            front_face_on_butt_timber=None,
        )
        joint = cut_mortise_and_tenon_joint_on_FAT(
            arrangement=arrangement,
            tenon_size=Matrix([Rational(2), Rational(2)]),
            tenon_length=tenon_length,
            mortise_depth=mortise_depth,
        )
        
        # Get the CSGs for the cut timbers (these are the REMAINING material after cuts)
        tenon_csg = joint.cut_timbers["tenon_timber"].render_timber_with_cuts_csg_local()
        mortise_csg = joint.cut_timbers["mortise_timber"].render_timber_with_cuts_csg_local()

        joint_shoulder_global = create_v3(Rational(0), Rational(0), Rational(3))
        
        # Verify basic tenon geometry: tenon should exist from z=0 upward
        # Test that center points are in the tenon at the bottom
        for z in [Rational(0), Rational(1), Rational(2), Rational(3)]:
            point_global = joint_shoulder_global - create_v3(Rational(0), Rational(0), z)
            point_tenon_local = tenon_timber.transform.global_to_local(point_global)
            point_mortise_local = mortise_timber.transform.global_to_local(point_global)
            assert tenon_csg.contains_point(point_tenon_local), \
                f"Point at z={z} should be in tenon centerline"
            assert not mortise_csg.contains_point(point_mortise_local), \
                f"Point at z={z} should not be in mortise centerline"
        
        for z in [Rational(4.2), Rational(4.8)]:
            point_global = joint_shoulder_global - create_v3(Rational(0), Rational(0), z)
            point_tenon_local = tenon_timber.transform.global_to_local(point_global)
            point_mortise_local = mortise_timber.transform.global_to_local(point_global)
            assert not tenon_csg.contains_point(point_tenon_local), \
                f"Point at z={z} should not be in tenon centerline"
            assert not mortise_csg.contains_point(point_mortise_local), \
                f"Point at z={z} should not be in mortise centerline"
        
        for z in [Rational(5), Rational(6)]:
            point_global = joint_shoulder_global - create_v3(Rational(0), Rational(0), z)
            point_tenon_local = tenon_timber.transform.global_to_local(point_global)
            point_mortise_local = mortise_timber.transform.global_to_local(point_global)
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
            peg_positions=[(distance_from_shoulder, Rational(0))],
            depth=peg_depth,
            size=Rational(1, 2)
        )
        
        arrangement = ButtJointTimberArrangement(
            receiving_timber=mortise_timber,
            butt_timber=tenon_timber,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
            front_face_on_butt_timber=TimberLongFace.FRONT,
        )
        joint = cut_mortise_and_tenon_joint_on_FAT(
            arrangement=arrangement,
            tenon_size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params,
        )

        assert joint.cut_timbers["tenon_timber"].timber == tenon_timber
        assert joint.cut_timbers["mortise_timber"].timber == mortise_timber
        assert len(joint.cut_timbers["tenon_timber"].cuts) == 1
        assert len(joint.cut_timbers["mortise_timber"].cuts) == 1
        # Tenon cut has a redundant end cut marker (points away from timber, doesn't cut anything extra)
        assert joint.cut_timbers["tenon_timber"].cuts[0].maybe_bottom_end_cut is not None
        assert joint.cut_timbers["tenon_timber"].cuts[0].maybe_top_end_cut is None
        assert joint.cut_timbers["mortise_timber"].cuts[0].maybe_top_end_cut is None
        assert joint.cut_timbers["mortise_timber"].cuts[0].maybe_bottom_end_cut is None
        
        peg = joint.jointAccessories["peg_0"]
        assert isinstance(peg, Peg), "Expected peg to be a Peg instance"
        
        # check that the peg is orthogonal to get_face_direction(TimberFace.FRONT)
        assert_vectors_parallel(peg.transform.orientation.matrix[:, 2], tenon_timber.get_face_direction_global(TimberFace.FRONT))
        f"Peg forward_length should match specified depth. Expected {peg_depth}, got {peg.forward_length}"
        assert peg.stickout_length == peg_depth * Rational(1, 2), \
            f"Peg stickout_length should be half of forward_length by default. Expected {peg_depth * Rational(1, 2)}, got {peg.stickout_length}"

        # check that the peg is positioned at the correct distance from the shoulder
        assert peg.transform.position[2] == shoulder_plane_x_global - distance_from_shoulder

        # Get tenon timber's cut CSG (what's removed)
        tenon_cut_timber = joint.cut_timbers["mortise_timber"]
        tenon_cut_csg = tenon_cut_timber.cuts[0].negative_csg
        
        # Verify CSG includes peg holes (should be a SolidUnion with multiple children)
        from code_goes_here.cutcsg import SolidUnion
        assert isinstance(tenon_cut_csg, SolidUnion), \
            "Tenon cut CSG with pegs should be a SolidUnion"
        assert len(tenon_cut_csg.children) >= 2, \
            "SolidUnion should contain base cut plus peg holes"

    # 🐪
    def test_peg_geometry(self, simple_T_configuration):
        """Test points on peg hole boundary using is_point_on_boundary()."""
        tenon_timber, mortise_timber = simple_T_configuration
        
        peg_size = Rational(1, 2)
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            peg_positions=[(Rational(2), Rational(0))],
            depth=None,
            size=peg_size
        )
        
        arrangement = ButtJointTimberArrangement(
            receiving_timber=mortise_timber,
            butt_timber=tenon_timber,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
            front_face_on_butt_timber=TimberLongFace.FRONT,
        )
        joint = cut_mortise_and_tenon_joint_on_FAT(
            arrangement=arrangement,
            tenon_size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params,
        )
        
        peg = joint.jointAccessories["peg_0"]
        assert isinstance(peg, Peg), "Expected peg to be a Peg instance"
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
            point_in_peg_hole_tenon_local = tenon_timber.transform.global_to_local(point_in_peg_hole)
            point_in_peg_hole_mortise_local = mortise_timber.transform.global_to_local(point_in_peg_hole)
            
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
            peg_positions=[
                (Rational(1), Rational(0)),
                (Rational(2), Rational(1, 2)),
                (Rational(3), Rational(-1, 2))
            ],
            depth=Rational(5),
            size=Rational(1, 2)
        )
        
        arrangement = ButtJointTimberArrangement(
            receiving_timber=mortise_timber,
            butt_timber=tenon_timber,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
            front_face_on_butt_timber=TimberLongFace.FRONT,
        )
        joint = cut_mortise_and_tenon_joint_on_FAT(
            arrangement=arrangement,
            tenon_size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params,
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
            assert isinstance(peg, Peg), "Expected peg to be a Peg instance"
            assert peg.forward_length == Rational(5), \
                f"Each peg should have depth 5, got {peg.forward_length}"
    
    # 🐪
    def test_peg_depth_from_mortise_surface_projection(self):
        """Peg depth (auto) is the full chord through the mortise timber in the peg direction.

        Uses a non-square mortise (width=4 in peg direction, height=10) so the test
        distinguishes the correct axis (size[0]=4) from the other (size[1]=10).
        """
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0), ticket="tenon_timber"
        )
        # The peg face is FRONT of the vertical tenon, whose normal is +Y globally.
        # The mortise runs along +X; its local X dimension (size[0]=4) is in the +Y direction.
        mortise_timber = create_centered_horizontal_timber(
            direction='x', length=100, size=(4, 10), name="mortise_timber"
        )
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            peg_positions=[(Rational(2), Rational(0))],
            depth=None,  # auto: computed from chord through mortise timber
            size=Rational(1, 2),
        )
        arrangement = ButtJointTimberArrangement(
            receiving_timber=mortise_timber,
            butt_timber=tenon_timber,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
            front_face_on_butt_timber=TimberLongFace.FRONT,
        )
        joint = cut_mortise_and_tenon_joint_on_FAT(
            arrangement=arrangement,
            tenon_size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params,
        )
        peg = joint.jointAccessories["peg_0"]
        # The peg travels in the +Y direction through the mortise.
        # The mortise chord in that direction equals size[0]=4, not size[1]=10.
        assert peg.forward_length == mortise_timber.size[0], (
            f"Peg depth should equal the chord through the mortise in the peg direction "
            f"({mortise_timber.size[0]}), got {peg.forward_length}"
        )

    # 🐪
    def test_peg_with_tenon_hole_offset(self, simple_T_configuration):
        """Test that tenon_hole_offset shifts the peg hole in the tenon towards the shoulder."""
        tenon_timber, mortise_timber = simple_T_configuration
        
        distance_from_shoulder = Rational(2)
        offset = Rational(1, 4)  # 0.25 units offset
        
        # Create joint with offset
        peg_params_with_offset = SimplePegParameters(
            shape=PegShape.SQUARE,
            peg_positions=[(distance_from_shoulder, Rational(0))],
            depth=Rational(5),
            size=Rational(1, 2),
            tenon_hole_offset=offset
        )
        
        arrangement = ButtJointTimberArrangement(
            receiving_timber=mortise_timber,
            butt_timber=tenon_timber,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
            front_face_on_butt_timber=TimberLongFace.FRONT,
        )
        joint_with_offset = cut_mortise_and_tenon_joint_on_FAT(
            arrangement=arrangement,
            tenon_size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params_with_offset,
        )
        
        # Create joint without offset for comparison
        peg_params_no_offset = SimplePegParameters(
            shape=PegShape.SQUARE,
            peg_positions=[(distance_from_shoulder, Rational(0))],
            depth=Rational(5),
            size=Rational(1, 2),
            tenon_hole_offset=Rational(0)
        )
        
        joint_no_offset = cut_mortise_and_tenon_joint_on_FAT(
            arrangement=arrangement,
            tenon_size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params_no_offset,
        )
        
        # TODO test actual stuff here

    # 🐪
    def test_peg_orientation_mortise_space_face_aligned(self):
        """When peg_orientation uses MORTISE space the peg X and Y axes must be
        face-aligned with the mortise timber, even when tenon and mortise are not
        face-aligned with each other.

        Uses the canonical brace arrangement: brace_timber runs at 45° in the XY
        plane (tenon), timber1 runs along +Y (mortise).  They are NOT face-aligned.
        The peg face is FRONT of the brace timber (normal = +Z globally).
        Requesting MORTISE orientation means the peg Y-axis must be parallel to
        the mortise length axis (+Y), not the brace length axis.
        """
        from code_goes_here.example_shavings import create_canonical_example_brace_joint_timbers
        from code_goes_here.rule import are_vectors_parallel

        brace_arrangement = create_canonical_example_brace_joint_timbers()
        brace_timber = brace_arrangement.brace_timber
        timber1 = brace_arrangement.timber1

        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            peg_positions=[(inches(1), Rational(0))],
            size=inches(1, 2),
            depth=inches(4),
            peg_orientation=(PegPositionSpace.MORTISE, Rational(0)),
        )

        arrangement = ButtJointTimberArrangement(
            butt_timber=brace_timber,
            receiving_timber=timber1,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
            front_face_on_butt_timber=TimberLongFace.RIGHT,
        )
        joint = cut_mortise_and_tenon_joint_on_PAT(
            arrangement=arrangement,
            tenon_size=Matrix([inches(2), inches(2)]),
            tenon_length=inches(4),
            mortise_depth=inches(3),
            peg_parameters=peg_params,
            mortise_shoulder_inset=inches(1, 2),
        )

        peg = joint.jointAccessories["peg_0"]
        assert isinstance(peg, Peg)

        # The peg's Y column (index 1) must be parallel to the mortise length axis (+Y)
        mortise_length_dir = timber1.get_length_direction_global()
        peg_y_axis = peg.transform.orientation.matrix[:, 1]
        assert are_vectors_parallel(peg_y_axis, mortise_length_dir), (
            f"Peg Y axis should be parallel to mortise length direction {mortise_length_dir}, "
            f"got {peg_y_axis}"
        )

        # It must NOT be parallel to the brace (tenon) length axis
        brace_length_dir = brace_timber.get_length_direction_global()
        assert not are_vectors_parallel(peg_y_axis, brace_length_dir), (
            f"Peg Y axis should NOT be parallel to brace (tenon) length direction {brace_length_dir}"
        )


class TestMeasureMortiseShoulderPlane:
    """Tests for measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber"""

    def test_perpendicular_intersecting_centerlines(self):
        """90-degree butt joint where centerlines intersect at origin.

        Receiving (mortise) timber along +X, butt (tenon) timber along +Y.
        Both timbers are 4"x5"x48" centered at origin.
        Direction from mortise centerline toward tenon = +Y.

        With distance_from_centerline = 0, the plane passes through the
        mortise centerline. With distance = 1, the plane is 1" toward the tenon.
        """
        from code_goes_here.example_shavings import create_canonical_example_butt_joint_timbers
        arrangement = create_canonical_example_butt_joint_timbers()

        plane_at_center = measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
            arrangement, Rational(0)
        )
        # The plane normal points AWAY from the tenon (into the mortise interior).
        # Tenon runs in +Y, so normal is -Y.
        assert are_vectors_parallel(plane_at_center.normal, create_v3(0, -1, 0)), \
            f"Plane normal should point away from tenon (-Y), got {plane_at_center.normal}"
        mortise_length_dir = arrangement.receiving_timber.get_length_direction_global()
        mortise_center = arrangement.receiving_timber.get_bottom_position_global() + mortise_length_dir * arrangement.receiving_timber.length / 2
        assert plane_at_center.point.equals(mortise_center), \
            f"At distance 0, plane point should be the mortise centerline midpoint, got {plane_at_center.point} vs {mortise_center}"

        # Positive distance moves the plane TOWARD the tenon (+Y),
        # but the direction_in_plane is -Y, so the point moves in -Y.
        # The shoulder conceptually moves toward the tenon, so positive distance
        # means the plane point goes away from centerline toward tenon face.
        plane_offset = measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
            arrangement, Rational(1)
        )
        expected_offset_point = mortise_center + create_v3(0, -1, 0)
        assert plane_offset.point.equals(expected_offset_point), \
            f"At distance 1, plane point should be offset 1 in -Y (normal dir), got {plane_offset.point} vs {expected_offset_point}"

    def test_angled_non_intersecting_centerlines(self):
        """40-degree butt joint where centerlines do NOT intersect.

        Mortise timber along +X at origin, tenon timber at 40 degrees in the
        XY plane offset 3" in +Z so the centerlines are skew (non-intersecting).
        """
        from sympy import Integer
        angle_rad = radians(Rational(2, 9) * pi)  # 40 degrees

        mortise_timber = timber_from_directions(
            length=inches(48), size=create_v2(inches(4), inches(5)),
            bottom_position=create_v3(-inches(24), Integer(0), Integer(0)),
            length_direction=create_v3(Integer(1), Integer(0), Integer(0)),
            width_direction=create_v3(Integer(0), Integer(0), Integer(1)),
            ticket="mortise"
        )
        tenon_length_dir = create_v3(cos(angle_rad), sin(angle_rad), Integer(0))
        tenon_timber = timber_from_directions(
            length=inches(48), size=create_v2(inches(4), inches(5)),
            bottom_position=create_v3(-inches(24) * cos(angle_rad), -inches(24) * sin(angle_rad), inches(3)),
            length_direction=tenon_length_dir,
            width_direction=create_v3(Integer(0), Integer(0), Integer(1)),
            ticket="tenon"
        )
        arrangement = ButtJointTimberArrangement(
            butt_timber=tenon_timber,
            receiving_timber=mortise_timber,
            butt_timber_end=TimberReferenceEnd.TOP,
        )

        plane = measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
            arrangement, Rational(0)
        )
        # The plane normal should be in the mortise cross-section, pointing
        # toward the tenon (which is offset at +Z=3").
        mortise_length_dir = mortise_timber.get_length_direction_global()
        assert zero_test(safe_dot_product(plane.normal, mortise_length_dir)), \
            "Plane normal should be perpendicular to the mortise length direction"
        assert safe_dot_product(plane.normal, create_v3(Integer(0), Integer(0), Integer(1))) > 0, \
            "Plane normal should have a +Z component (toward the tenon which is at +Z=3)"

        plane_positive = measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
            arrangement, inches(1)
        )
        plane_negative = measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
            arrangement, -inches(1)
        )
        direction_to_tenon = plane_positive.point - plane.point
        assert safe_dot_product(direction_to_tenon, create_v3(Integer(0), Integer(0), Integer(1))) > 0, \
            "Positive distance should offset toward the tenon (which is at +Z)"
        direction_away = plane_negative.point - plane.point
        assert safe_dot_product(direction_away, create_v3(Integer(0), Integer(0), Integer(1))) < 0, \
            "Negative distance should offset away from the tenon"


class TestShoulderNotchingDecision:
    """Tests for _does_shoulder_plane_need_notching."""

    def test_does_shoulder_plane_need_notching(self, simple_T_configuration):
        """Uses face/plane-aligned logic when aligned, and always True when not plane-aligned."""
        tenon_timber, mortise_timber = simple_T_configuration

        aligned_arrangement = ButtJointTimberArrangement(
            receiving_timber=mortise_timber,
            butt_timber=tenon_timber,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
        )
        assert are_timbers_plane_aligned(mortise_timber, tenon_timber)

        tenon_end_direction = tenon_timber.get_face_direction_global(TimberReferenceEnd.BOTTOM)
        mortise_face = mortise_timber.get_closest_oriented_long_face_from_global_direction(
            -tenon_end_direction
        ).to.face()
        face_half_size = mortise_timber.get_size_in_face_normal_axis(mortise_face) / Rational(2)

        assert _does_shoulder_plane_need_notching(aligned_arrangement, face_half_size - Rational(1))
        assert not _does_shoulder_plane_need_notching(aligned_arrangement, face_half_size)

        non_plane_mortise = timber_from_directions(
            length=Rational(100),
            size=create_v2(Rational(6), Rational(6)),
            bottom_position=create_v3(-Rational(50), Rational(0), Rational(0)),
            length_direction=create_v3(Rational(1), Rational(0), Rational(0)),
            width_direction=create_v3(Rational(0), Rational(0), Rational(1)),
            ticket="non_plane_mortise",
        )
        non_plane_tenon = timber_from_directions(
            length=Rational(100),
            size=create_v2(Rational(4), Rational(4)),
            bottom_position=create_v3(Rational(0), Rational(0), Rational(0)),
            length_direction=create_v3(Rational(0), Rational(1), Rational(0)),
            width_direction=normalize_vector(create_v3(Rational(1), Rational(0), Rational(1))),
            ticket="non_plane_tenon",
        )
        non_plane_arrangement = ButtJointTimberArrangement(
            receiving_timber=non_plane_mortise,
            butt_timber=non_plane_tenon,
            butt_timber_end=TimberReferenceEnd.BOTTOM,
        )

        assert not are_timbers_plane_aligned(non_plane_mortise, non_plane_tenon)
        assert _does_shoulder_plane_need_notching(non_plane_arrangement, Rational(100))