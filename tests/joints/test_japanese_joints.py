"""
Tests for Japanese joint construction functions (mitered and keyed lap joint).
"""

import pytest
from sympy import Matrix, Rational, Integer, simplify, pi, Abs
from giraffecad import *
from giraffecad.rule import inches, degrees, are_vectors_parallel, safe_dot_product, normalize_vector
from giraffecad.ticket import TimberTicket
from giraffecad.example_shavings import (
    create_canonical_example_corner_joint_timbers,
    create_canonical_example_right_angle_corner_joint_timbers,
)
from giraffecad.joints.japanese_joints import cut_mitered_and_keyed_lap_joint
from tests.testing_shavings import (
    create_standard_horizontal_timber,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_right_angle_arrangement(front_face=TimberLongFace.RIGHT, position=None):
    """Create a right-angle corner arrangement with renamed timbers."""
    from dataclasses import replace as dc_replace
    arrangement = create_canonical_example_right_angle_corner_joint_timbers(position=position)
    timberA = dc_replace(arrangement.timber1, ticket=TimberTicket("timberA"))
    timberB = dc_replace(arrangement.timber2, ticket=TimberTicket("timberB"))
    return dc_replace(
        arrangement,
        timber1=timberA,
        timber2=timberB,
        front_face_on_timber1=front_face,
    )


def _make_angled_arrangement(angle_deg, front_face=TimberLongFace.RIGHT, position=None):
    """Create a corner arrangement at the given angle (degrees) with renamed timbers."""
    from dataclasses import replace as dc_replace
    arrangement = create_canonical_example_corner_joint_timbers(
        corner_angle=degrees(Integer(angle_deg)), position=position
    )
    timberA = dc_replace(arrangement.timber1, ticket=TimberTicket("timberA"))
    timberB = dc_replace(arrangement.timber2, ticket=TimberTicket("timberB"))
    return dc_replace(
        arrangement,
        timber1=timberA,
        timber2=timberB,
        front_face_on_timber1=front_face,
    )


def _assert_joint_structure(joint, num_keys, num_laps):
    """Validate basic joint structure: two cut timbers, expected accessories."""
    assert joint is not None
    assert len(joint.cut_timbers) == 2
    assert "timberA" in joint.cut_timbers
    assert "timberB" in joint.cut_timbers

    # Each timber should have exactly one cutting
    assert len(joint.cut_timbers["timberA"].cuts) == 1
    assert len(joint.cut_timbers["timberB"].cuts) == 1
    assert isinstance(joint.cut_timbers["timberA"].cuts[0], Cutting)
    assert isinstance(joint.cut_timbers["timberB"].cuts[0], Cutting)

    # Keys = num_laps - 1
    expected_keys = num_laps - 1
    assert len(joint.jointAccessories) == expected_keys, (
        f"Expected {expected_keys} key accessories for {num_laps} laps, "
        f"got {len(joint.jointAccessories)}"
    )
    for i in range(expected_keys):
        assert f"key_{i}" in joint.jointAccessories
        assert isinstance(joint.jointAccessories[f"key_{i}"], Wedge)


def _assert_end_cuts_match_arrangement(joint, arrangement):
    """Verify that end cuts are on the correct ends per the arrangement."""
    cutA = joint.cut_timbers["timberA"].cuts[0]
    cutB = joint.cut_timbers["timberB"].cuts[0]

    if arrangement.timber1_end == TimberReferenceEnd.TOP:
        assert cutA.maybe_top_end_cut is not None
        assert cutA.maybe_bottom_end_cut is None
    else:
        assert cutA.maybe_bottom_end_cut is not None
        assert cutA.maybe_top_end_cut is None

    if arrangement.timber2_end == TimberReferenceEnd.TOP:
        assert cutB.maybe_top_end_cut is not None
        assert cutB.maybe_bottom_end_cut is None
    else:
        assert cutB.maybe_bottom_end_cut is not None
        assert cutB.maybe_top_end_cut is None


def _assert_miter_boundary_point(joint, timberA, timberB, point_global):
    """Assert a point on the miter boundary is on the boundary of both rendered timbers."""
    csgA = joint.cut_timbers["timberA"].render_timber_with_cuts_csg_local()
    csgB = joint.cut_timbers["timberB"].render_timber_with_cuts_csg_local()
    ptA = timberA.transform.global_to_local(point_global)
    ptB = timberB.transform.global_to_local(point_global)
    assert csgA.is_point_on_boundary(ptA), (
        f"Expected point {point_global.T} to be on timberA boundary"
    )
    assert csgB.is_point_on_boundary(ptB), (
        f"Expected point {point_global.T} to be on timberB boundary"
    )


# ============================================================================
# Tests for cut_mitered_and_keyed_lap_joint
# ============================================================================

class TestMiteredAndKeyedLapJoint:
    """Test cut_mitered_and_keyed_lap_joint function."""

    def test_basic_right_angle_joint(self):
        """Test basic joint at 90 degrees — structure, end cuts, accessories, miter separation."""
        arrangement = _make_right_angle_arrangement()
        timberA = arrangement.timber1
        timberB = arrangement.timber2
        num_laps = 3

        joint = cut_mitered_and_keyed_lap_joint(
            arrangement=arrangement,
            num_laps=num_laps,
            lap_thickness=inches(Rational(3, 4)),
            lap_start_distance_from_reference_miter_face=inches(Rational(1, 2)),
            distance_between_lap_and_outside=inches(Rational(1, 2)),
        )

        _assert_joint_structure(joint, num_keys=num_laps - 1, num_laps=num_laps)
        _assert_end_cuts_match_arrangement(joint, arrangement)

        # Both timbers should be renderable without error
        csgA = joint.cut_timbers["timberA"].render_timber_with_cuts_csg_local()
        csgB = joint.cut_timbers["timberB"].render_timber_with_cuts_csg_local()
        assert csgA is not None
        assert csgB is not None

        
        # Each key wedge accessory has a transform; its position center should
        # be in the void (not contained in either timber).
        for key_name, accessory in joint.jointAccessories.items():
            assert isinstance(accessory, Wedge)
            key_center_global = accessory.transform.position
            ptA = timberA.transform.global_to_local(key_center_global)
            ptB = timberB.transform.global_to_local(key_center_global)
            assert not csgA.contains_point(ptA), (
                f"{key_name} center should not be inside timberA (key void)"
            )
            assert not csgB.contains_point(ptB), (
                f"{key_name} center should not be inside timberB (key void)"
            )

        # TODO test finger locations and keys


    def test_multiple_angles(self):
        """Test that the joint is constructable at several valid angles."""
        for angle_deg in [60, 75, 90, 110, 130]:
            arrangement = _make_angled_arrangement(angle_deg)
            joint = cut_mitered_and_keyed_lap_joint(
                arrangement=arrangement,
                num_laps=2,
            )
            _assert_joint_structure(joint, num_keys=1, num_laps=2)
            _assert_end_cuts_match_arrangement(joint, arrangement)

            # Ensure renderable
            csgA = joint.cut_timbers["timberA"].render_timber_with_cuts_csg_local()
            csgB = joint.cut_timbers["timberB"].render_timber_with_cuts_csg_local()
            assert csgA is not None
            assert csgB is not None
        
        # TODO test finger locations and keys

    # ------------------------------------------------------------------
    # Parameter variation tests
    # ------------------------------------------------------------------

    def test_num_laps_2_produces_one_key(self):
        """Minimum valid num_laps=2 should produce exactly 1 key."""
        arrangement = _make_right_angle_arrangement()
        joint = cut_mitered_and_keyed_lap_joint(
            arrangement=arrangement,
            num_laps=2,
        )
        _assert_joint_structure(joint, num_keys=1, num_laps=2)

    def test_num_laps_4_produces_three_keys(self):
        """num_laps=4 should produce exactly 3 keys."""
        arrangement = _make_right_angle_arrangement()
        joint = cut_mitered_and_keyed_lap_joint(
            arrangement=arrangement,
            num_laps=4,
        )
        _assert_joint_structure(joint, num_keys=3, num_laps=4)

    # ------------------------------------------------------------------
    # Error / validation tests
    # ------------------------------------------------------------------


    # 🐪
    def test_num_laps_below_2_raises(self):
        """num_laps < 2 should raise ValueError."""
        arrangement = _make_right_angle_arrangement()
        with pytest.raises(ValueError, match="num_laps must be at least 2"):
            cut_mitered_and_keyed_lap_joint(
                arrangement=arrangement,
                num_laps=1,
            )

    # 🐪
    def test_angle_too_shallow_raises(self):
        """Angles below 45 degrees should raise ValueError."""
        arrangement = _make_angled_arrangement(30)
        with pytest.raises(ValueError, match="Angle between timbers"):
            cut_mitered_and_keyed_lap_joint(
                arrangement=arrangement,
                num_laps=2,
            )

    # 🐪
    def test_parallel_timbers_raises(self):
        """Parallel timbers (angle ~0 or ~180) should raise."""
        timberA = create_standard_horizontal_timber(direction='x', length=100, size=(4, 5), position=(0, 0, 0), ticket="timberA")
        timberB = create_standard_horizontal_timber(direction='x', length=100, size=(4, 5), position=(0, 0, 0), ticket="timberB")

        arrangement = CornerJointTimberArrangement(
            timber1=timberA,
            timber2=timberB,
            timber1_end=TimberReferenceEnd.BOTTOM,
            timber2_end=TimberReferenceEnd.BOTTOM,
            front_face_on_timber1=TimberLongFace.RIGHT,
        )
        with pytest.raises((ValueError, AssertionError)):
            cut_mitered_and_keyed_lap_joint(
                arrangement=arrangement,
                num_laps=2,
            )
