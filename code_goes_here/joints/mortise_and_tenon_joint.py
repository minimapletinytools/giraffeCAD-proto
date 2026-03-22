"""
GiraffeCAD - Mortise and Tenon Joint Construction Functions
Contains various mortise and tenon joint implementations
"""

from __future__ import annotations  # Enable deferred annotation evaluation

import warnings
from functools import wraps

from code_goes_here.timber import *
from code_goes_here.measuring import (
    locate_top_center_position,
    locate_bottom_center_position,
    locate_position_on_centerline_from_bottom,
    locate_position_on_centerline_from_top,
    locate_into_face,
    locate_face,
    locate_centerline,
    locate_edge,
    locate_plane_from_edge_in_direction,
    mark_distance_from_end_along_centerline,
    mark_plane_from_edge_in_direction,
    get_point_on_face_global,
    Space,
    Plane,
    Line,
)
from code_goes_here.construction import *
from code_goes_here.timber_shavings import are_timbers_plane_aligned
from code_goes_here.rule import *
from code_goes_here.rule import safe_transform_vector, safe_dot_product
from code_goes_here.cutcsg import CutCSG, RectangularPrism, HalfSpace, Difference, adopt_csg
from .joint_shavings import chop_shoulder_notch_aligned_with_timber
from .build_a_butt_joint_shavings import locate_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber


# ============================================================================
# Helepers
# ============================================================================


def _does_shoulder_plane_need_notching(
    arrangement: ButtJointTimberArrangement,
    mortise_shoulder_distance_from_centerline: Numeric,
) -> bool:
    """
    Determines whether a shoulder notch is needed on the mortise timber.

    For plane-aligned timbers, checks whether the shoulder is inset from the
    mortise face surface. For non-plane-aligned timbers, always returns True.
    """
    mortise_timber = arrangement.receiving_timber
    tenon_timber = arrangement.butt_timber
    tenon_end = arrangement.butt_timber_end

    # we could check if the shoulder plane intersects the timber here, but then you'd have an unsupported tenon shoulder which is likely unintentional and certainly rare.
    # so just assume it does intersect and a notch is required
    if not are_timbers_plane_aligned(mortise_timber, tenon_timber):
        return True

    tenon_end_direction = tenon_timber.get_face_direction_global(
        TimberFace.TOP if tenon_end == TimberReferenceEnd.TOP else TimberFace.BOTTOM
    )
    mortise_face = mortise_timber.get_closest_oriented_long_face_from_global_direction(
        -tenon_end_direction
    ).to.face()
    face_half_size = mortise_timber.get_size_in_face_normal_axis(mortise_face) / Integer(2)
    return (
        mortise_shoulder_distance_from_centerline < face_half_size
        and not zero_test(face_half_size - mortise_shoulder_distance_from_centerline)
    )


def compute_peg_positions(
    arrangement: ButtJointTimberArrangement,
    shoulder_plane: Plane,
    peg_parameters: SimplePegParameters,
    tenon_position: V2,
) -> List[PegPositionResult]:
    """
    Compute peg positions in global space for a mortise and tenon joint.

    Uses the arrangement's front_face_on_butt_timber as the peg face on the tenon.
    All computations are done in global space, using the measure/mark pattern where possible.

    Args:
        arrangement: Butt joint arrangement (butt_timber = tenon, receiving_timber = mortise).
                     Must have front_face_on_butt_timber set.
        shoulder_plane: The shoulder plane in global space (from
                        locate_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber).
        peg_parameters: Peg configuration (shape, positions, size, depth, offset).
        tenon_position: Offset of tenon center from timber centerline in tenon local cross-section (X, Y).

    Returns:
        List of PegPositionResult, one per peg_position entry.
    """
    tenon_timber = arrangement.butt_timber
    mortise_timber = arrangement.receiving_timber
    tenon_end = arrangement.butt_timber_end

    assert arrangement.front_face_on_butt_timber is not None, (
        "arrangement.front_face_on_butt_timber must be set to determine the peg face"
    )
    tenon_face: TimberLongFace = arrangement.front_face_on_butt_timber
    peg_face: TimberFace = tenon_face.to.face()

    # --- Measure/mark: shoulder reference point in global space ---
    shoulder_mark = mark_distance_from_end_along_centerline(shoulder_plane, tenon_timber, tenon_end)
    shoulder_point_global = shoulder_mark.measure().position

    tenon_right = tenon_timber.get_face_direction_global(TimberFace.RIGHT)
    tenon_front = tenon_timber.get_face_direction_global(TimberFace.FRONT)
    marking_origin_global = (
        shoulder_point_global
        + tenon_right * tenon_position[0]
        + tenon_front * tenon_position[1]
    )

    # --- Directions for shoulder-distance and lateral axes ---
    tenon_end_direction = tenon_timber.get_face_direction_global(tenon_end)

    # Measure/mark: tenon face plane (gives surface point + normal)
    tenon_face_plane = locate_face(tenon_timber, peg_face)
    peg_face_normal_global = tenon_face_plane.normal

    # Measure/mark: tenon and mortise centerlines for axis directions
    tenon_centerline = locate_centerline(tenon_timber)
    mortise_centerline = locate_centerline(mortise_timber)

    # Peg orientation: Z axis = drilling direction (inward from face).
    # The peg drills INTO the timber, so Z points opposite to the face normal.
    # The ray direction (outward from face, toward mortise) is separate.
    peg_drill_direction = -peg_face_normal_global
    peg_ray_direction = peg_face_normal_global

    # Choose the face-aligned Y basis from the requested timber space.
    orient_space, ccw_rotation_angle = peg_parameters.peg_orientation
    if orient_space == PegPositionSpace.TENON:
        peg_y_base = tenon_centerline.direction
    else:
        # Mortise space: use mortise length axis, oriented to agree with tenon end direction
        mortise_len_dir = mortise_centerline.direction
        if safe_dot_product(mortise_len_dir, tenon_end_direction) < 0:
            mortise_len_dir = -mortise_len_dir
        peg_y_base = mortise_len_dir

    # Apply CCW rotation around the drill axis (Z) on top of the face-aligned basis.
    if zero_test(ccw_rotation_angle):
        peg_orientation_global = Orientation.from_z_and_y(
            z_direction=peg_drill_direction,
            y_direction=peg_y_base,
        )
    else:
        base_orientation = Orientation.from_z_and_y(
            z_direction=peg_drill_direction,
            y_direction=peg_y_base,
        )
        rotation_around_z = Orientation.from_angle_axis(ccw_rotation_angle, peg_drill_direction)
        peg_orientation_global = Orientation(rotation_around_z.matrix * base_orientation.matrix)

    # Lateral direction in tenon space: the cross-section axis perpendicular to
    # both the peg face normal and the tenon length axis.
    # For RIGHT/LEFT face → lateral is FRONT direction; for FRONT/BACK face → lateral is RIGHT direction.
    if tenon_face in [TimberLongFace.RIGHT, TimberLongFace.LEFT]:
        tenon_lateral_direction = tenon_front
    else:
        tenon_lateral_direction = tenon_right

    results: List[PegPositionResult] = []

    for distance_from_shoulder, distance_from_centerline in peg_parameters.peg_positions:
        # --- Interpret distance_from_shoulder via peg_position_space[0] ---
        if peg_parameters.peg_position_space[0] == PegPositionSpace.TENON:
            shoulder_axis = tenon_end_direction
        else:
            # MORTISE: use mortise length direction, oriented to agree with tenon end direction
            mortise_len_dir = mortise_centerline.direction
            if safe_dot_product(mortise_len_dir, tenon_end_direction) < 0:
                mortise_len_dir = -mortise_len_dir
            shoulder_axis = mortise_len_dir

        # --- Interpret distance_from_centerline via peg_position_space[1] ---
        if peg_parameters.peg_position_space[1] == PegPositionSpace.TENON:
            lateral_axis = tenon_lateral_direction
        else:
            # MORTISE: use mortise length direction
            lateral_axis = mortise_centerline.direction

        # --- Compute peg center position (before snapping to face surface) ---
        peg_center_global = (
            marking_origin_global
            + shoulder_axis * distance_from_shoulder
            + lateral_axis * distance_from_centerline
        )

        # --- Snap to tenon face surface using locate_face plane ---
        dist_to_face = safe_dot_product(
            tenon_face_plane.normal,
            tenon_face_plane.point - peg_center_global,
        )
        peg_pos_on_tenon_face_global = peg_center_global + tenon_face_plane.normal * dist_to_face

        # --- Apply tenon_hole_offset (shift tenon hole toward shoulder) ---
        offset_direction = -tenon_end_direction  # toward shoulder
        peg_pos_on_tenon_face_with_offset_global = (
            peg_pos_on_tenon_face_global + offset_direction * peg_parameters.tenon_hole_offset
        )

        # --- Project peg ray onto mortise timber surface (ray-AABB intersection) ---
        # Transform the peg ray into mortise timber local coordinates.
        ray_origin_local = mortise_timber.transform.global_to_local(peg_pos_on_tenon_face_global)
        ray_dir_local = safe_transform_vector(mortise_timber.transform.orientation.matrix.T, peg_ray_direction)

        # Mortise timber local AABB: X ∈ [-w/2, w/2], Y ∈ [-h/2, h/2], Z ∈ [0, length]
        box_mins = [-mortise_timber.size[0] / 2, -mortise_timber.size[1] / 2, Integer(0)]
        box_maxs = [mortise_timber.size[0] / 2, mortise_timber.size[1] / 2, mortise_timber.length]

        t_enter_vals = []
        t_exit_vals = []
        for axis in range(3):
            d = ray_dir_local[axis]
            if zero_test(d):
                assert box_mins[axis] <= ray_origin_local[axis] <= box_maxs[axis], (
                    f"Peg ray is parallel to mortise timber axis {axis} but peg position is "
                    f"outside the mortise timber bounds on that axis"
                )
            else:
                t1 = (box_mins[axis] - ray_origin_local[axis]) / d
                t2 = (box_maxs[axis] - ray_origin_local[axis]) / d
                t_enter_vals.append(min(t1, t2))
                t_exit_vals.append(max(t1, t2))

        assert t_enter_vals and t_exit_vals, (
            "Peg ray is parallel to all three mortise timber axes"
        )
        t_enter = max(t_enter_vals)
        t_exit = min(t_exit_vals)
        assert t_exit > t_enter, (
            "Peg ray does not intersect the mortise timber; "
            "check that the peg position and direction are correct"
        )

        # The peg entry face is the mortise timber surface in the peg direction.
        # If the peg origin is inside the mortise (t_enter < 0), the drilling entry
        # is the exit face (t_exit). Otherwise it is the entry face (t_enter).
        peg_entry_t = t_exit if t_enter < 0 else t_enter
        peg_pos_on_mortise_face_global = peg_pos_on_tenon_face_global + peg_ray_direction * peg_entry_t

        # --- Compute depth (full chord through mortise, or explicit) ---
        if peg_parameters.depth is not None:
            peg_depth = peg_parameters.depth
        else:
            peg_depth = t_exit - t_enter
        stickout_length = peg_depth * Rational(1, 2)

        results.append(PegPositionResult(
            tenon_face_position_global=peg_pos_on_tenon_face_global,
            tenon_face_position_with_offset_global=peg_pos_on_tenon_face_with_offset_global,
            mortise_entry_position_global=peg_pos_on_mortise_face_global,
            orientation_global=peg_orientation_global,
            peg_depth=peg_depth,
            stickout_length=stickout_length,
        ))

    return results


# ============================================================================
# Parameter Classes for Mortise and Tenon Joints
# ============================================================================


class PegPositionSpace(Enum):
    """Which timber's coordinate space to use when interpreting peg positions and orientations."""
    TENON = 1
    MORTISE = 2

# TODO add tenon bore offset parameter, it could be none | auto | Numeric
@dataclass(frozen=True)
class SimplePegParameters:
    """
    Parameters for simple pegs in mortise and tenon joints.
    
    Attributes:
        shape: Shape specification for the peg (from PegShape enum)
        peg_positions: List of (distance_from_shoulder, distance_from_centerline) tuples
                       - First value: distance along length axis measured from shoulder of tenon
                       - Second value: distance in perpendicular axis measured from center
        peg_position_space: Controls which timber's coordinate system is used to interpret each
                    component of peg_positions. A tuple of (shoulder_axis_space, lateral_axis_space).
                    - shoulder_axis_space (first element): controls distance_from_shoulder direction.
                      TENON = along tenon length axis. MORTISE = along mortise length axis.
                    - lateral_axis_space (second element): controls distance_from_centerline direction.
                      TENON = perpendicular to peg face normal and tenon length axis.
                      MORTISE = along mortise length axis.
        size: Peg diameter (for round pegs) or side length (for square pegs)
        depth: Depth measured from mortise face where peg goes in (None means all the way through the mortise timber)
        tenon_hole_offset: Offset distance of the hole in the tenon towards the shoulder so that the peg tightens the joint up. You should usually set this to 1-2mm
        peg_orientation: Controls which timber's face axes the peg cross-section is aligned to, plus an
                         optional CCW rotation around the drill axis. A tuple of (space, ccw_rotation_angle).
                         - space: TENON = align peg Y axis with the tenon length axis.
                                  MORTISE = align peg Y axis with the mortise length axis.
                         - ccw_rotation_angle: counter-clockwise rotation (in radians) around the drill
                           axis applied on top of the face-aligned basis. 0 = no rotation.
    """
    shape: PegShape
    peg_positions: List[Tuple[Numeric, Numeric]]
    size: Numeric
    depth: Optional[Numeric] = None
    tenon_hole_offset: Numeric = Rational(0)
    peg_position_space: Tuple[PegPositionSpace, PegPositionSpace] = (PegPositionSpace.TENON, PegPositionSpace.TENON)
    peg_orientation: Tuple[PegPositionSpace, Numeric] = (PegPositionSpace.TENON, Rational(0))


@dataclass(frozen=True)
class PegPositionResult:
    """
    Computed geometry for a single peg, all positions and orientations in global space.

    Attributes:
        tenon_face_position_global: Center of the peg hole on the tenon face (no draw-bore offset).
        tenon_face_position_with_offset_global: Center of the peg hole on the tenon face,
            shifted toward the shoulder by tenon_hole_offset for draw-bore tightening.
        mortise_entry_position_global: Center of the peg hole on the mortise entry face.
        orientation_global: Orientation of the peg (Z-axis = drill direction into the timber).
        peg_depth: Depth of the peg hole (full chord through the mortise, or explicit depth).
        stickout_length: Length the peg protrudes beyond the mortise entry face.
    """
    tenon_face_position_global: V3
    tenon_face_position_with_offset_global: V3
    mortise_entry_position_global: V3
    orientation_global: Orientation
    peg_depth: Numeric
    stickout_length: Numeric


@dataclass(frozen=True)
class WedgeParameters:
    """
    Parameters for wedges in mortise and tenon joints.
    
    Attributes:
        shape: Shape specification for the wedge
        depth: Depth of the wedge cut (may differ from length of wedge)
        width_axis: Wedges run along this axis. When looking perpendicular to this
                    and the length axis, you see the trapezoidal "sides" of the wedges
        positions: Positions from center of timber in the width axis
        expand_mortise: Amount to fan out bottom of mortise to fit wedges
                        - 0 means straight sides (default)
                        - X means expand both sides of mortise bottom by X (total), the shoulder of the mortise remains the original size
    """
    shape: WedgeShape
    depth: Numeric
    width_axis: Direction3D
    positions: List[Numeric]
    expand_mortise: Numeric = Rational(0)


# ============================================================================
# Mortise and Tenon Joint Construction Functions
# ============================================================================


def cut_mortise_and_tenon_joint(
    arrangement: ButtJointTimberArrangement,
    tenon_size: V2,
    tenon_length: Numeric,
    mortise_depth: Optional[Numeric] = None,

    mortise_shoulder_distance_from_centerline: Numeric = Rational(0),

    tenon_position: Optional[V2] = None,
    wedge_parameters: Optional[WedgeParameters] = None,
    peg_parameters: Optional[SimplePegParameters] = None,

    crop_tenon_to_mortise_orientation_on_angled_joints: bool = False,
) -> Joint:
    """
    Creates a mortise and tenon joint with full control over all parameters.

    This is the generic implementation used by all specialized variants
    (`cut_mortise_and_tenon_joint_on_PAT`, `cut_mortise_and_tenon_joint_on_FAT`).
    Prefer those variants for common cases.

    Args:
        arrangement: Butt joint timber arrangement (butt_timber = tenon, receiving_timber = mortise).
        tenon_size: Cross-sectional size of the tenon (X, Y) in the tenon timber's local space.
        tenon_length: Length of the tenon extending from the mortise entry face. For angled
            joints, set this slightly longer than expected to ensure full penetration.
        mortise_depth: Depth of the mortise (None = through mortise). Measurement differs
            depending on crop_tenon_to_mortise_orientation_on_angled_joints.
        mortise_shoulder_distance_from_centerline: Signed distance from the mortise
            centerline to the shoulder plane, measured within the mortise cross-section
            in the direction toward the tenon centerline. 0 = shoulder at the mortise
            centerline. Positive pushes the shoulder toward the tenon.
        tenon_position: Offset of the tenon center from the timber centerline in the tenon's
            local cross-section. (0, 0) = centered on the centerline.
        wedge_parameters: Wedge configuration (not currently used).
        peg_parameters: Peg configuration for draw-bore tightening (optional). Note: peg
            distance_from_shoulder is measured along the tenon axis, while
            distance_from_centerline is measured along the mortise axis — this makes
            positioning pegs on angled braces easier.
        crop_tenon_to_mortise_orientation_on_angled_joints: If True, the tenon is cropped
            so its depth along the mortise face axis equals mortise_depth and its tip is
            trimmed to the mortise hole boundary. If False, mortise depth is measured along
            the tenon axis from the shoulder.

    Returns:
        Joint object containing the two CutTimbers and any accessories, all in global space.
    """
    tenon_timber = arrangement.butt_timber
    mortise_timber = arrangement.receiving_timber
    tenon_end = arrangement.butt_timber_end

    # Default tenon_position to centered (0, 0)
    if tenon_position is None:
        tenon_position = Matrix([Rational(0), Rational(0)])

    # TODO default mortise depth if mortise_depth is None

    # -------------------------------------------------------------------------
    # Step 3: Shoulder plane from centerline toward tenon
    # -------------------------------------------------------------------------
    shoulder_plane = locate_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
        arrangement, mortise_shoulder_distance_from_centerline
    )
    shoulder_from_tenon_end_mark = mark_distance_from_end_along_centerline(shoulder_plane, tenon_timber, tenon_end)

    tenon_end_direction = tenon_timber.get_face_direction_global(tenon_end)
    shoulder_point_global = shoulder_from_tenon_end_mark.measure().position

    tenon_right = tenon_timber.get_face_direction_global(TimberFace.RIGHT)
    tenon_front = tenon_timber.get_face_direction_global(TimberFace.FRONT)
    marking_origin_global = (
        shoulder_point_global
        + tenon_right * tenon_position[0]
        + tenon_front * tenon_position[1]
    )

    # -------------------------------------------------------------------------
    # Step 4: Define marking_space (global Space at shoulder, toward tenon end)
    # -------------------------------------------------------------------------
    tenon_orientation = compute_timber_orientation(
        normalize_vector(tenon_end_direction), tenon_timber.get_width_direction_global()
    )
    tenon_base_transform = Transform(position=marking_origin_global, orientation=tenon_orientation)
    marking_space: Space = Space(transform=tenon_base_transform)

    # -------------------------------------------------------------------------
    # Step 5: Determine the angle between the mortise entry direction and tenon
    # -------------------------------------------------------------------------
    mortise_face_normal = shoulder_plane.normal
    cos_angle = safe_dot_product(
        normalize_vector(mortise_face_normal), normalize_vector(tenon_end_direction)
    )

    # -------------------------------------------------------------------------
    # Tenon prism (origin at marking_space) and shoulder half-space
    # -------------------------------------------------------------------------
    from sympy import Abs, sqrt

    # Back-extension from shoulder so prism fully contains tenon at oblique angles
    sin_angle_sq = Integer(1) - cos_angle * cos_angle
    sin_angle_safe = Rational(1, 10000) if fast_zero_test(sin_angle_sq) else sqrt(Abs(sin_angle_sq))
    back_extension = max(tenon_size[0], tenon_size[1]) / sin_angle_safe

    tenon_prism_global = RectangularPrism(
        size=tenon_size,
        transform=marking_space.transform,
        start_distance=-back_extension,
        end_distance=tenon_length,
    )

    tenon_prism_cropping_csgs: Optional[List[CutCSG]] = None
    do_cropping = crop_tenon_to_mortise_orientation_on_angled_joints and not zero_test(cos_angle)
    if do_cropping:
        # Compute mortise_face locally — cropping is only used for plane-aligned timbers
        mortise_face = mortise_timber.get_closest_oriented_long_face_from_global_direction(
            -tenon_end_direction
        ).to.face()
        mortise_face_direction = mortise_timber.get_face_direction_global(mortise_face)

        mortise_oblique_end = mortise_timber.get_closest_oriented_end_face_from_global_direction(tenon_end_direction)
        joint_angle_axis_face = tenon_timber.get_closest_oriented_long_face_from_global_direction(mortise_timber.get_face_direction_global(mortise_oblique_end))
        joint_angle_axis_index = tenon_timber.get_size_index_in_long_face_normal_axis(joint_angle_axis_face)

        mortise_hole_length_oblique_direction = mortise_timber.get_face_direction_global(mortise_oblique_end)
        end_crop_distance = tenon_size[joint_angle_axis_index] / sin_angle_safe / Rational(2)

        # Crop 1: far end of prism perpendicular to mortise face
        mortise_hole_end_crop_global = HalfSpace(
            normal=mortise_hole_length_oblique_direction,
            offset=end_crop_distance + safe_dot_product(mortise_hole_length_oblique_direction, shoulder_point_global),
        )

        # Crop 2: depth of tenon — plane parallel to the mortise face surface,
        # mortise_depth measured from the face inward.
        mortise_depth_crop_global = HalfSpace(
            normal=-mortise_face_direction,
            offset=mortise_depth - safe_dot_product(mortise_face_direction, get_point_on_face_global(mortise_face, mortise_timber)),
        )

        tenon_prism_cropping_csgs = [mortise_hole_end_crop_global, mortise_depth_crop_global]

    # Shoulder half-space: plane through centerline ∩ shoulder (marking origin), normal = shoulder plane normal
    shoulder_half_space_global = HalfSpace(
        normal=-shoulder_plane.normal,
        offset=safe_dot_product(-shoulder_plane.normal, marking_space.transform.position),
    )

    tenon_prism_cropped = (
        tenon_prism_global
        if tenon_prism_cropping_csgs is None
        else Difference(base=tenon_prism_global, subtract=tenon_prism_cropping_csgs)
    )

    # Convert from global to tenon timber local (orig_timber=None => CSG is in global space)
    tenon_prism_local = adopt_csg(None, tenon_timber.transform, tenon_prism_cropped)
    shoulder_half_space_local = adopt_csg(None, tenon_timber.transform, shoulder_half_space_global)

    # -------------------------------------------------------------------------
    # mortise hole
    # -------------------------------------------------------------------------

    mortise_hole_prism_global = None

    if do_cropping:
        mortise_hole_size = create_v2(0,0)
        mortise_hole_size[1] = tenon_size[joint_angle_axis_index] / sin_angle_safe
        opp_index = 1 if joint_angle_axis_index == 0 else 0
        mortise_hole_size[0] = tenon_size[opp_index]

        mortise_hole_orientation = Orientation.from_z_and_y(
            z_direction=-mortise_face_normal,
            y_direction=mortise_hole_length_oblique_direction,
        )

        mortise_hole_transform = Transform(
            position=marking_space.transform.position,
            orientation=mortise_hole_orientation,
        )
        
        mortise_hole_prism_global = RectangularPrism(
            size=mortise_hole_size,
            transform=mortise_hole_transform,
            start_distance=-back_extension,
            end_distance=mortise_depth,
        )
    else:
        mortise_hole_prism_global = RectangularPrism(
            size=tenon_size,
            transform=marking_space.transform,
            start_distance=-back_extension,
            end_distance=mortise_depth,
        )

    # -------------------------------------------------------------------------
    # shoulder notch on mortise timber (when shoulder is inset from face)
    # -------------------------------------------------------------------------

    needs_shoulder_notch = _does_shoulder_plane_need_notching(
        arrangement, mortise_shoulder_distance_from_centerline
    )

    shoulder_notch_local = None
    if needs_shoulder_notch:
        from sympy import acos
        approach_angle_radians = acos(Abs(cos_angle))
        shoulder_notch_local = chop_shoulder_notch_aligned_with_timber(
            notch_timber=mortise_timber,
            butting_timber=tenon_timber,
            butting_timber_end=tenon_end,
            distance_from_centerline=mortise_shoulder_distance_from_centerline,
            notch_wall_relief_cut_angle_radians=approach_angle_radians,
        )

    # -------------------------------------------------------------------------
    # make the final cut CSGs
    # -------------------------------------------------------------------------

    tenon_cut_csg = Difference(
        base=shoulder_half_space_local,
        subtract=[tenon_prism_local],
    )

    mortise_hole_prism_local = adopt_csg(None, mortise_timber.transform, mortise_hole_prism_global)

    if shoulder_notch_local is not None:
        mortise_negative_csg = CSGUnion(children=[mortise_hole_prism_local, shoulder_notch_local])
    else:
        mortise_negative_csg = mortise_hole_prism_local

    mortise_cut = Cutting(
        timber=mortise_timber,
        maybe_top_end_cut=None,
        maybe_bottom_end_cut=None,
        negative_csg=mortise_negative_csg,
    )

    # Redundant end cut at the tip of the tenon prism (in tenon timber local)
    tenon_length_direction_global = tenon_timber.get_face_direction_global(tenon_end)
    tip_position_global = marking_space.transform.position + tenon_length_direction_global * max(tenon_length, max(tenon_size[0], tenon_size[1])/cos_angle)
    tip_position_local = tenon_timber.transform.global_to_local(tip_position_global)
    tip_z_local = tip_position_local[2]
    redundant_end_cut = (
        HalfSpace(normal=create_v3(Integer(0), Integer(0), Integer(1)), offset=tip_z_local)
        if tenon_end == TimberReferenceEnd.TOP
        else HalfSpace(normal=create_v3(Integer(0), Integer(0), Integer(-1)), offset=-tip_z_local)
    )
    print(f"Redundant end cut at z={tip_z_local} in tenon local space to ensure clean tip")
    tenon_cut = Cutting(
        timber=tenon_timber,
        maybe_top_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.TOP else None,
        maybe_bottom_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.BOTTOM else None,
        negative_csg=tenon_cut_csg,
    )

    joint_accessories = {}
    if peg_parameters is not None:
        peg_results = compute_peg_positions(
            arrangement=arrangement,
            shoulder_plane=shoulder_plane,
            peg_parameters=peg_parameters,
            tenon_position=tenon_position,
        )

        peg_size = peg_parameters.size
        peg_holes_in_tenon_local = []
        peg_holes_in_mortise_local = []

        for peg_idx, peg_result in enumerate(peg_results):
            # Create peg hole CSG in tenon local space (using offset position for draw-bore tightening)
            peg_hole_tenon_global = RectangularPrism(
                size=Matrix([peg_size, peg_size]),
                transform=Transform(
                    position=peg_result.tenon_face_position_with_offset_global,
                    orientation=peg_result.orientation_global,
                ),
                start_distance=0,
                end_distance=peg_result.peg_depth,
            )
            peg_holes_in_tenon_local.append(adopt_csg(None, tenon_timber.transform, peg_hole_tenon_global))

            # Create peg hole CSG in mortise local space
            peg_hole_mortise_global = RectangularPrism(
                size=Matrix([peg_size, peg_size]),
                transform=Transform(
                    position=peg_result.mortise_entry_position_global,
                    orientation=peg_result.orientation_global,
                ),
                start_distance=Rational(0),
                end_distance=peg_result.peg_depth,
            )
            peg_holes_in_mortise_local.append(adopt_csg(None, mortise_timber.transform, peg_hole_mortise_global))

            # Create Peg accessory in global space (positioned at mortise entry)
            peg_accessory = Peg(
                transform=Transform(
                    position=peg_result.mortise_entry_position_global,
                    orientation=peg_result.orientation_global,
                ),
                size=peg_size,
                shape=peg_parameters.shape,
                forward_length=peg_result.peg_depth,
                stickout_length=peg_result.stickout_length,
            )
            joint_accessories[f"peg_{peg_idx}"] = peg_accessory

        if peg_holes_in_tenon_local:
            tenon_cut_with_pegs_csg = CSGUnion(children=[tenon_cut_csg] + peg_holes_in_tenon_local)
            tenon_cut = Cutting(
                timber=tenon_timber,
                maybe_top_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.TOP else None,
                maybe_bottom_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.BOTTOM else None,
                negative_csg=tenon_cut_with_pegs_csg
            )
        if peg_holes_in_mortise_local:
            mortise_cut_with_pegs_csg = CSGUnion(children=[mortise_negative_csg] + peg_holes_in_mortise_local)
            mortise_cut = Cutting(
                timber=mortise_timber,
                maybe_top_end_cut=None,
                maybe_bottom_end_cut=None,
                negative_csg=mortise_cut_with_pegs_csg
            )

    tenon_cut_timber = CutTimber(timber=tenon_timber, cuts=[tenon_cut])
    mortise_cut_timber = CutTimber(mortise_timber, cuts=[mortise_cut])

    return Joint(
        cut_timbers={
            tenon_timber.ticket.name: tenon_cut_timber,
            mortise_timber.ticket.name: mortise_cut_timber,
        },
        jointAccessories=joint_accessories,
    ) 


def cut_mortise_and_tenon_joint_on_PAT(
    arrangement: ButtJointTimberArrangement,
    tenon_size: V2,
    tenon_length: Numeric,
    mortise_depth: Optional[Numeric] = None,
    tenon_position: Optional[V2] = None,
    mortise_shoulder_inset: Numeric = Rational(0),
    wedge_parameters: Optional[WedgeParameters] = None,
    peg_parameters: Optional[SimplePegParameters] = None,
    crop_tenon_to_mortise_orientation_on_angled_joints = False,
) -> Joint:
    """
    Creates a mortise and tenon joint for plane-aligned timbers (PAT).

    PAT (plane-aligned timbers) means both timbers lie in the same plane. The timbers may
    meet at any angle — use `cut_mortise_and_tenon_joint_on_FAT` for the standard 90-degree
    case.

    Like the generic `cut_mortise_and_tenon_joint`, but accepts `mortise_shoulder_inset`
    measured from the mortise entry face surface (the intuitive user-facing parameter),
    converting it internally to `mortise_shoulder_distance_from_centerline`.

    Args:
        arrangement: Butt joint timber arrangement (butt_timber = tenon, receiving_timber = mortise).
            Must satisfy arrangement.check_plane_aligned().
        tenon_size: Cross-sectional size of the tenon (X, Y) in the tenon timber's local space.
        tenon_length: Length of the tenon extending from the mortise entry face. For angled
            joints, set this slightly longer than expected.
        mortise_depth: Depth of the mortise (None = through mortise).
        tenon_position: Offset of the tenon center from the timber centerline in the tenon's
            local cross-section. (0, 0) = centered on the centerline.
        mortise_shoulder_inset: Distance from the mortise entry face to the shoulder plane,
            measured perpendicular to the face inward. 0 = shoulder flush with the entry face.
        wedge_parameters: Wedge configuration (not currently used).
        peg_parameters: Peg configuration for draw-bore tightening (optional).
        crop_tenon_to_mortise_orientation_on_angled_joints: If True, the tenon tip is cropped
            to the mortise hole boundary. If False, mortise depth is measured along the tenon axis.

    Returns:
        Joint object containing the two CutTimbers and any accessories.

    Raises:
        CheckFailure: If the arrangement is not plane-aligned.
    """

    require_check(arrangement.check_plane_aligned())

    # -------------------------------------------------------------------------
    # Step 2: Determine which face of the mortise timber the tenon enters from
    # -------------------------------------------------------------------------
    tenon_end_direction = arrangement.butt_timber.get_face_direction_global(
        TimberFace.TOP if arrangement.butt_timber_end == TimberReferenceEnd.TOP else TimberFace.BOTTOM
    )
    mortise_face = arrangement.receiving_timber.get_closest_oriented_long_face_from_global_direction(
        -tenon_end_direction
    ).to.face()
    
    # Convert inset (measured from the face surface toward centerline) to distance
    # from centerline (measured toward the tenon). The face surface sits at
    # face_half_size from the centerline in the toward-tenon direction.
    face_half_size = arrangement.receiving_timber.get_size_in_face_normal_axis(mortise_face) / Integer(2)
    inset_plane = locate_into_face(mortise_shoulder_inset, mortise_face, arrangement.receiving_timber)
    inset_marking = mark_plane_from_edge_in_direction(inset_plane, arrangement.receiving_timber, TimberCenterline.CENTERLINE)
    mortise_shoulder_distance_from_centerline = inset_marking.distance

    return cut_mortise_and_tenon_joint(
        arrangement=arrangement,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        mortise_shoulder_distance_from_centerline=mortise_shoulder_distance_from_centerline,
        tenon_position=tenon_position,
        wedge_parameters=wedge_parameters,
        peg_parameters=peg_parameters,
        crop_tenon_to_mortise_orientation_on_angled_joints=crop_tenon_to_mortise_orientation_on_angled_joints,
    )

    

def cut_mortise_and_tenon_joint_on_FAT(
    arrangement: ButtJointTimberArrangement,
    tenon_size: V2,
    tenon_length: Numeric,
    mortise_depth: Optional[Numeric] = None,
    tenon_position: Optional[V2] = None,
    mortise_shoulder_inset: Numeric = Rational(0),
    wedge_parameters: Optional[WedgeParameters] = None,
    peg_parameters: Optional[SimplePegParameters] = None,
) -> Joint:
    """
    Creates a mortise and tenon joint for face-aligned orthogonal timbers (FAT).

    FAT (face-aligned and orthogonal timbers) means both timbers are face-aligned
    (orientations related by 90-degree rotations) and their length axes are perpendicular.
    This is the standard configuration for timber-frame T-joints and corners. For angled
    joints in the same plane, use `cut_mortise_and_tenon_joint_on_PAT`.

    This is a stricter variant of `cut_mortise_and_tenon_joint_on_PAT` that enforces
    perpendicularity and does not support crop_tenon_to_mortise_orientation_on_angled_joints.

    Args:
        arrangement: Butt joint timber arrangement (butt_timber = tenon, receiving_timber = mortise).
            Must satisfy arrangement.check_face_aligned_and_orthogonal().
        tenon_size: Cross-sectional size of the tenon (X, Y) in the tenon timber's local space.
        tenon_length: Length of the tenon extending from the mortise entry face.
        mortise_depth: Depth of the mortise (None = through mortise).
        tenon_position: Offset of the tenon center from the timber centerline in the tenon's
            local cross-section. (0, 0) = centered on the centerline.
        mortise_shoulder_inset: Distance from the mortise entry face to the shoulder plane,
            measured perpendicular to the face inward. 0 = shoulder flush with the entry face.
        wedge_parameters: Wedge configuration (not currently used).
        peg_parameters: Peg configuration for draw-bore tightening (optional).

    Returns:
        Joint object containing the two CutTimbers and any accessories.

    Raises:
        CheckFailure: If the arrangement is not face-aligned and orthogonal.
    """

    require_check(arrangement.check_face_aligned_and_orthogonal())

    return cut_mortise_and_tenon_joint_on_PAT(
        arrangement=arrangement,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        tenon_position=tenon_position,
        mortise_shoulder_inset=mortise_shoulder_inset,
        wedge_parameters=wedge_parameters,
        peg_parameters=peg_parameters,
    )

