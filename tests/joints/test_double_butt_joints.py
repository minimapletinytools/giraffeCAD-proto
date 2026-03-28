"""
Tests for double butt joint construction functions.
"""

from sympy import Rational
from giraffe import *
from code_goes_here.example_shavings import create_canonical_example_opposing_double_butt_joint_timbers


class TestSplinedOpposingDoubleButtJoint:
    """Test cut_splined_opposing_double_butt_joint function."""

    def test_arrangement_validation(self):
        """Canonical arrangement passes the cardinal-and-opposing-butts check."""
        arrangement = create_canonical_example_opposing_double_butt_joint_timbers()
        assert arrangement.check_face_aligned_cardinal_and_opposing_butts() is None

    def test_returns_joint_with_three_cut_timbers(self):
        """Implemented function returns all three cut timbers with one cut each."""
        arrangement = create_canonical_example_opposing_double_butt_joint_timbers()
        joint = cut_splined_opposing_double_butt_joint(arrangement)

        assert set(joint.cut_timbers.keys()) == {"receiving_timber", "butt_timber_1", "butt_timber_2"}
        assert len(joint.cut_timbers["receiving_timber"].cuts) == 1
        assert len(joint.cut_timbers["butt_timber_1"].cuts) == 1
        assert len(joint.cut_timbers["butt_timber_2"].cuts) == 1

    def test_slot_point_removed_on_all_three_members(self):
        """A point known to lie inside the default slot should be removed from all three timbers."""
        arrangement = create_canonical_example_opposing_double_butt_joint_timbers()
        joint = cut_splined_opposing_double_butt_joint(arrangement)

        receiving_center_global = (
            arrangement.receiving_timber.get_bottom_position_global()
            + arrangement.receiving_timber.get_length_direction_global() * arrangement.receiving_timber.length / Rational(2)
        )

        slot_direction_global = arrangement.receiving_timber.get_face_direction_global(TimberReferenceEnd.TOP)
        joint_plane_normal_global = normalize_vector(
            cross_product(
                arrangement.butt_timber_1.get_length_direction_global(),
                arrangement.receiving_timber.get_length_direction_global(),
            )
        )
        slot_face_on_butt_1 = arrangement.butt_timber_1.get_closest_oriented_long_face_from_global_direction(
            slot_direction_global
        )
        slot_depth_axis_dimension = arrangement.butt_timber_1.get_size_in_face_normal_axis(slot_face_on_butt_1)
        default_slot_depth = slot_depth_axis_dimension / Rational(2)

        # Use the slot center point implied by default parameters in the joint function.
        slot_sample_point_global = receiving_center_global + slot_direction_global * (
            slot_depth_axis_dimension / Rational(2) - default_slot_depth / Rational(2)
        ) + joint_plane_normal_global * Rational(0)

        for key in ["receiving_timber", "butt_timber_1", "butt_timber_2"]:
            cut_timber = joint.cut_timbers[key]
            rendered_csg = cut_timber.render_timber_with_cuts_csg_local()
            slot_sample_point_local = cut_timber.timber.transform.global_to_local(slot_sample_point_global)
            assert not rendered_csg.contains_point(slot_sample_point_local), (
                f"Slot sample point should be cut out of {key}"
            )

        far_point_on_receiving_global = (
            receiving_center_global
            + arrangement.receiving_timber.get_length_direction_global() * inches(12)
        )
        receiving_csg = joint.cut_timbers["receiving_timber"].render_timber_with_cuts_csg_local()
        far_point_on_receiving_local = arrangement.receiving_timber.transform.global_to_local(far_point_on_receiving_global)
        assert receiving_csg.contains_point(far_point_on_receiving_local), (
            "Receiving timber should still contain points far from the slot"
        )

    def test_shoulder_inset_moves_butt_end_cut_inward(self):
        """Increasing shoulder inset should move the butt end cut inward by that inset."""
        arrangement = create_canonical_example_opposing_double_butt_joint_timbers()

        joint_flush = cut_splined_opposing_double_butt_joint(
            arrangement,
            shoulder_symmetric_inset=Rational(0),
        )
        joint_inset = cut_splined_opposing_double_butt_joint(
            arrangement,
            shoulder_symmetric_inset=inches(1),
        )

        butt_1_flush_end_cut = joint_flush.cut_timbers["butt_timber_1"].cuts[0].maybe_top_end_cut
        butt_1_inset_end_cut = joint_inset.cut_timbers["butt_timber_1"].cuts[0].maybe_top_end_cut

        assert butt_1_flush_end_cut is not None
        assert butt_1_inset_end_cut is not None
        assert zero_test((butt_1_inset_end_cut.offset - butt_1_flush_end_cut.offset) - inches(1)), (
            "Top-end shoulder cut offset should increase by the shoulder inset (butt protrudes further)"
        )

    def test_receiving_timber_gets_shoulder_notches_when_inset_positive(self):
        """Positive shoulder inset should add receiving-side shoulder notch cuts."""
        arrangement = create_canonical_example_opposing_double_butt_joint_timbers()

        joint_flush = cut_splined_opposing_double_butt_joint(
            arrangement,
            shoulder_symmetric_inset=Rational(0),
        )
        joint_inset = cut_splined_opposing_double_butt_joint(
            arrangement,
            shoulder_symmetric_inset=inches(1),
        )

        receiving_flush_negative_csg = joint_flush.cut_timbers["receiving_timber"].cuts[0].negative_csg
        receiving_inset_negative_csg = joint_inset.cut_timbers["receiving_timber"].cuts[0].negative_csg

        assert not isinstance(receiving_flush_negative_csg, CSGUnion)
        assert isinstance(receiving_inset_negative_csg, CSGUnion)
        assert len(receiving_inset_negative_csg.children) == 3
