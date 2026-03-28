"""
GiraffeCAD - Double butt joint construction functions
Contains functions for creating joints where two butt timbers meet a single receiving timber.
"""

from code_goes_here.timber import *
from code_goes_here.construction import *
from code_goes_here.rule import *
from .joint_shavings import *


def cut_splined_opposing_double_butt_joint(arrangement: DoubleButtJointTimberArrangement,
                                           # thickness is in the axis perpendicular to the joint plane
                                           slot_thickness: Numeric,
                                           # depth is in the axis of the receiving timber, measured from the face of the butt timber that aligns with slot_facing_end_on_receiving_timber
                                           slot_depth: Numeric,
                                           # length is in the axis parallel to the butt timbers
                                           spline_length: Numeric,
                                           # REQUIRED: the slot faces this end of the receiving timber
                                           slot_facing_end_on_receiving_timber: TimberReferenceEnd,
                                           # the spline has this much extra depth beyond the slot depth; defaults to 1/4 of slot_depth
                                           spline_extra_depth=None,
                                           # the slot extends this much beyond the spline on each end for clearance
                                           slot_symmetric_extra_length=mm(3),
                                           # inset the shoulder plane on both sides by this amount, flush with faces of receiving timber if 0
                                           shoulder_symmetric_inset=Rational(0),
                                           # offset the slot by this much, measured relative to receiving timber centerline in the axis perpendicular to the joint plane
                                           slot_lateral_offset=Rational(0),
                                           ) -> Joint:
    """
    Creates a splined opposing double butt joint.

    Two butt timbers approach the receiving timber from opposite cardinal directions.
    All three timbers must be face-aligned, each butt timber must be perpendicular to the
    receiving timber, and the two butt timbers must be antiparallel.

    Args:
        arrangement: Double butt joint arrangement with butt_timber_1, butt_timber_2,
            receiving_timber, butt_timber_1_end, butt_timber_2_end.

    Returns:
        Joint containing all three cut timbers.

    Raises:
        AssertionError: If the arrangement fails the cardinal-and-opposing-butts check.
    """
    error = arrangement.check_face_aligned_cardinal_and_opposing_butts()
    assert error is None, error

    assert isinstance(slot_facing_end_on_receiving_timber, TimberReferenceEnd), (
        f"slot_facing_end_on_receiving_timber must be TimberReferenceEnd, got "
        f"{type(slot_facing_end_on_receiving_timber).__name__}"
    )

    butt_timber_1 = arrangement.butt_timber_1
    butt_timber_2 = arrangement.butt_timber_2
    receiving_timber = arrangement.receiving_timber

    butt_length_direction_global = butt_timber_1.get_length_direction_global()
    receiving_length_direction_global = receiving_timber.get_length_direction_global()
    slot_direction_global = receiving_timber.get_face_direction_global(slot_facing_end_on_receiving_timber)
    joint_plane_normal_global = normalize_vector(
        cross_product(butt_length_direction_global, receiving_length_direction_global)
    )

    slot_face_on_butt_1 = butt_timber_1.get_closest_oriented_long_face_from_global_direction(slot_direction_global)
    slot_face_on_butt_2 = butt_timber_2.get_closest_oriented_long_face_from_global_direction(slot_direction_global)

    slot_face_direction_1 = butt_timber_1.get_face_direction_global(slot_face_on_butt_1)
    slot_face_direction_2 = butt_timber_2.get_face_direction_global(slot_face_on_butt_2)

    assert are_vectors_parallel(slot_face_direction_1, slot_direction_global), (
        "slot-facing face on butt_timber_1 must align with slot_direction"
    )
    assert are_vectors_parallel(slot_face_direction_2, slot_direction_global), (
        "slot-facing face on butt_timber_2 must align with slot_direction"
    )

    slot_depth_axis_dimension = butt_timber_1.get_size_in_face_normal_axis(slot_face_on_butt_1)
    slot_thickness_axis_dimension = butt_timber_1.get_size_in_direction_3d(joint_plane_normal_global)

    if spline_extra_depth is None:
        spline_extra_depth = slot_depth / Rational(4)

    assert safe_compare(slot_thickness, Comparison.GT), "slot_thickness must be > 0"
    assert safe_compare(slot_depth, Comparison.GT), "slot_depth must be > 0"
    assert safe_compare(slot_depth_axis_dimension - slot_depth, Comparison.GE), (
        "slot_depth must be <= butt timber thickness along slot depth axis"
    )
    assert safe_compare(spline_length, Comparison.GT), "spline_length must be > 0"
    effective_slot_depth = slot_depth + spline_extra_depth
    assert safe_compare(slot_thickness_axis_dimension - slot_thickness, Comparison.GE), (
        "slot_thickness must be <= butt timber thickness along joint-plane-normal axis"
    )
    assert safe_compare(spline_extra_depth, Comparison.GE), "spline_extra_depth must be >= 0"
    assert safe_compare(slot_symmetric_extra_length, Comparison.GE), "slot_symmetric_extra_length must be >= 0"

    slot_length = spline_length + Rational(2) * slot_symmetric_extra_length
    assert safe_compare(slot_length, Comparison.GT), "slot_length must be > 0"

    def _locate_butt_end_center_global(timber: Timber, end: TimberReferenceEnd) -> V3:
        if end == TimberReferenceEnd.TOP:
            return locate_top_center_position(timber).position
        return timber.get_bottom_position_global()

    butt_end_center_1_global = _locate_butt_end_center_global(butt_timber_1, arrangement.butt_timber_1_end)
    butt_end_center_2_global = _locate_butt_end_center_global(butt_timber_2, arrangement.butt_timber_2_end)

    entry_face_point_1_global = (
        butt_end_center_1_global
        + slot_face_direction_1 * (butt_timber_1.get_size_in_face_normal_axis(slot_face_on_butt_1) / Rational(2))
    )
    entry_face_point_2_global = (
        butt_end_center_2_global
        + slot_face_direction_2 * (butt_timber_2.get_size_in_face_normal_axis(slot_face_on_butt_2) / Rational(2))
    )

    slot_center_from_butt_1_global = entry_face_point_1_global - slot_direction_global * (slot_depth / Rational(2))
    slot_center_from_butt_2_global = entry_face_point_2_global - slot_direction_global * (slot_depth / Rational(2))
    slot_center_global = (
        slot_center_from_butt_1_global + slot_center_from_butt_2_global
    ) / Rational(2) + joint_plane_normal_global * slot_lateral_offset

    slot_marking_orientation_global = Orientation.from_z_and_y(
        z_direction=butt_length_direction_global,
        y_direction=slot_direction_global,
    )
    slot_marking_transform_global = Transform(
        position=slot_center_global,
        orientation=slot_marking_orientation_global,
    )

    slot_negative_csg_global = RectangularPrism(
        size=create_v2(slot_thickness, slot_depth),
        transform=slot_marking_transform_global,
        start_distance=-(slot_length / Rational(2)),
        end_distance=slot_length / Rational(2),
    )

    extended_slot_negative_csg_global = RectangularPrism(
        size=create_v2(slot_thickness, effective_slot_depth),
        transform=Transform(
            position=slot_marking_transform_global.position + slot_direction_global * (effective_slot_depth - slot_depth) / 2,
            orientation=slot_marking_transform_global.orientation,
        ),
        start_distance=-(slot_length / Rational(2)),
        end_distance=slot_length / Rational(2),
    )

    def _make_shoulder_end_cut(timber: Timber, timber_end: TimberReferenceEnd) -> HalfSpace:
        butt_end_direction_global = timber.get_face_direction_global(timber_end)
        receiving_face = receiving_timber.get_closest_oriented_face_from_global_direction(-butt_end_direction_global)
        receiving_face_center_global = get_point_on_face_global(receiving_face, receiving_timber)

        distance_from_bottom = safe_dot_product(
            receiving_face_center_global - timber.get_bottom_position_global(),
            timber.get_length_direction_global(),
        )
        if timber_end == TimberReferenceEnd.TOP:
            distance_from_end = timber.length - distance_from_bottom
        else:
            distance_from_end = distance_from_bottom

        distance_from_end = distance_from_end - shoulder_symmetric_inset
        assert safe_compare(distance_from_end, Comparison.GE), "shoulder cut distance must be >= 0"
        assert safe_compare(timber.length - distance_from_end, Comparison.GE), (
            "shoulder cut distance from end exceeds timber length"
        )
        return Cutting.make_end_cut(timber, timber_end, distance_from_end)

    butt_1_shoulder_end_cut = _make_shoulder_end_cut(butt_timber_1, arrangement.butt_timber_1_end)
    butt_2_shoulder_end_cut = _make_shoulder_end_cut(butt_timber_2, arrangement.butt_timber_2_end)

    receiving_slot_negative_csg_local = adopt_csg(None, receiving_timber.transform, extended_slot_negative_csg_global)
    butt_1_slot_negative_csg_local = adopt_csg(None, butt_timber_1.transform, slot_negative_csg_global)
    butt_2_slot_negative_csg_local = adopt_csg(None, butt_timber_2.transform, slot_negative_csg_global)

    receiving_negative_csg_parts = [receiving_slot_negative_csg_local]

    if safe_compare(shoulder_symmetric_inset, Comparison.GT):
        def _make_receiving_shoulder_notch_local(
            butting_timber: Timber,
            butting_timber_end: TimberReferenceEnd,
        ) -> CutCSG:
            butt_end_direction_global = butting_timber.get_face_direction_global(butting_timber_end)
            receiving_face = receiving_timber.get_closest_oriented_long_face_from_global_direction(
                -butt_end_direction_global
            )
            receiving_face_half_size = receiving_timber.get_size_in_face_normal_axis(receiving_face) / Rational(2)
            shoulder_distance_from_centerline = receiving_face_half_size - shoulder_symmetric_inset

            assert safe_compare(shoulder_distance_from_centerline, Comparison.GE), (
                "shoulder_symmetric_inset is too large for receiving timber half size"
            )

            return chop_shoulder_notch_aligned_with_timber(
                notch_timber=receiving_timber,
                butting_timber=butting_timber,
                butting_timber_end=butting_timber_end,
                distance_from_centerline=shoulder_distance_from_centerline,
            )

        receiving_negative_csg_parts.append(
            _make_receiving_shoulder_notch_local(butt_timber_1, arrangement.butt_timber_1_end)
        )
        receiving_negative_csg_parts.append(
            _make_receiving_shoulder_notch_local(butt_timber_2, arrangement.butt_timber_2_end)
        )

    receiving_negative_csg_local = (
        receiving_negative_csg_parts[0]
        if len(receiving_negative_csg_parts) == 1
        else CSGUnion(children=receiving_negative_csg_parts)
    )

    receiving_cut = Cutting(
        timber=receiving_timber,
        maybe_top_end_cut=None,
        maybe_bottom_end_cut=None,
        negative_csg=receiving_negative_csg_local,
    )
    butt_1_cut = Cutting(
        timber=butt_timber_1,
        maybe_top_end_cut=butt_1_shoulder_end_cut if arrangement.butt_timber_1_end == TimberReferenceEnd.TOP else None,
        maybe_bottom_end_cut=butt_1_shoulder_end_cut if arrangement.butt_timber_1_end == TimberReferenceEnd.BOTTOM else None,
        negative_csg=butt_1_slot_negative_csg_local,
    )
    butt_2_cut = Cutting(
        timber=butt_timber_2,
        maybe_top_end_cut=butt_2_shoulder_end_cut if arrangement.butt_timber_2_end == TimberReferenceEnd.TOP else None,
        maybe_bottom_end_cut=butt_2_shoulder_end_cut if arrangement.butt_timber_2_end == TimberReferenceEnd.BOTTOM else None,
        negative_csg=butt_2_slot_negative_csg_local,
    )

    spline_transform = Transform(
        position=slot_marking_transform_global.position + slot_direction_global * (effective_slot_depth-slot_depth)/2,
        orientation=slot_marking_transform_global.orientation,
    )

    spline = Spline(
                transform=spline_transform,
                thickness=slot_thickness,
                depth=effective_slot_depth,
                length=spline_length,
            )
    
    return Joint(
        cut_timbers={
            "receiving_timber": CutTimber(receiving_timber, cuts=[receiving_cut]),
            "butt_timber_1": CutTimber(butt_timber_1, cuts=[butt_1_cut]),
            "butt_timber_2": CutTimber(butt_timber_2, cuts=[butt_2_cut]),
        },
        jointAccessories={
            "spline": spline,
        },
    )


def cut_plain_splined_opposing_double_butt_joint(
    arrangement: DoubleButtJointTimberArrangement,
    slot_facing_end_on_receiving_timber: TimberReferenceEnd,
) -> Joint:
    """
    Plain/default recipe for splined opposing double butt joints.

    Defaults applied here:
    - slot_thickness = 1/3 of receiving timber thickness in the axis perpendicular to the joint plane
    - slot_depth = 1/2 of butt_timber_1 width in the slot-depth axis
    - spline_length = 4x the receiving timber width in the axis parallel to butt timbers
    - spline_extra_depth = 1/4 of slot_depth
    - slot_symmetric_extra_length = 3 mm
    - shoulder_symmetric_inset = 0
    - slot_lateral_offset = 0
    """
    butt_timber_1 = arrangement.butt_timber_1
    receiving_timber = arrangement.receiving_timber

    butt_length_direction_global = butt_timber_1.get_length_direction_global()
    receiving_length_direction_global = receiving_timber.get_length_direction_global()
    slot_direction_global = receiving_timber.get_face_direction_global(
        slot_facing_end_on_receiving_timber
    )
    joint_plane_normal_global = normalize_vector(
        cross_product(butt_length_direction_global, receiving_length_direction_global)
    )

    slot_face_on_butt_1 = butt_timber_1.get_closest_oriented_long_face_from_global_direction(
        slot_direction_global
    )

    slot_thickness = receiving_timber.get_size_in_direction_3d(
        joint_plane_normal_global
    ) / Rational(3)
    slot_depth = butt_timber_1.get_size_in_face_normal_axis(slot_face_on_butt_1) / Rational(2)
    spline_length = receiving_timber.get_size_in_direction_3d(
        butt_length_direction_global
    ) * Integer(4)

    return cut_splined_opposing_double_butt_joint(
        arrangement=arrangement,
        slot_facing_end_on_receiving_timber=slot_facing_end_on_receiving_timber,
        slot_thickness=slot_thickness,
        slot_depth=slot_depth,
        spline_length=spline_length,
        spline_extra_depth=None,
        slot_symmetric_extra_length=mm(3),
        shoulder_symmetric_inset=Rational(0),
        slot_lateral_offset=Rational(0),
    )
