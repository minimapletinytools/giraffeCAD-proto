"""
GiraffeCAD - Build-a-Butt-Joint Helpers
Shared helpers for computing shoulder planes and marking spaces for butt joints.
"""

from __future__ import annotations

from code_goes_here.timber import *
from code_goes_here.measuring import (
    locate_centerline,
    locate_plane_from_edge_in_direction,
    mark_distance_from_end_along_centerline,
    Space,
    Plane,
    Line,
)
from code_goes_here.construction import *
from code_goes_here.rule import *
from code_goes_here.rule import safe_dot_product


# ============================================================================
# Shoulder Plane
# ============================================================================

def locate_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(arrangement: ButtJointTimberArrangement, distance_from_centerline: Numeric) -> Plane:
    """
    Computes the shoulder plane of the mortise timber, offset from its centerline toward the tenon.

    The shoulder plane is parallel to the mortise timber's length axis and offset from
    the mortise centerline in the mortise cross-section toward the tenon. Its reference
    point is chosen using the tenon centerline relation.

    Args:
        arrangement: Butt joint arrangement (receiving_timber = mortise, butt_timber = tenon).
        distance_from_centerline: Signed offset from the mortise centerline toward the tenon.
            0 = plane through the mortise centerline. Positive = toward tenon.

    Returns:
        Plane parallel to the mortise length axis, offset by distance_from_centerline
        from the mortise centerline toward the tenon.
    """
    mortise_timber = arrangement.receiving_timber
    tenon_timber = arrangement.butt_timber
    tenon_end = arrangement.butt_timber_end

    mortise_centerline = locate_centerline(mortise_timber)
    tenon_end_direction = tenon_timber.get_face_direction_global(tenon_end)
    if tenon_end == TimberReferenceEnd.TOP:
        tenon_end_position = tenon_timber.get_bottom_position_global() + tenon_timber.get_length_direction_global() * tenon_timber.length
    else:
        tenon_end_position = tenon_timber.get_bottom_position_global()
    tenon_centerline = Line(-tenon_end_direction, tenon_end_position)
    mortise_length_dir = mortise_timber.get_length_direction_global()

    # Find M = closest point on mortise centerline to tenon centerline
    w = mortise_centerline.point - tenon_centerline.point
    a = safe_dot_product(mortise_centerline.direction, mortise_centerline.direction)
    b = safe_dot_product(mortise_centerline.direction, tenon_centerline.direction)
    c = safe_dot_product(tenon_centerline.direction, tenon_centerline.direction)
    d = safe_dot_product(w, mortise_centerline.direction)
    e = safe_dot_product(w, tenon_centerline.direction)

    denom = a * c - b * b
    denom_is_zero = fast_zero_test(denom)
    if denom_is_zero:
        M = mortise_centerline.point
    else:
        t_mortise = (b * e - c * d) / denom
        M = mortise_centerline.point + mortise_centerline.direction * t_mortise

    # Find P = intersection of tenon centerline with cross-section plane at M
    plane_dot_dir = safe_dot_product(mortise_length_dir, tenon_centerline.direction)
    plane_dot_dir_is_zero = fast_zero_test(plane_dot_dir)
    if plane_dot_dir_is_zero:
        if denom_is_zero:
            P = tenon_centerline.point
        else:
            s_tenon = (a * e - b * d) / denom
            P = tenon_centerline.point + tenon_centerline.direction * s_tenon
    else:
        s = safe_dot_product(mortise_length_dir, M - tenon_centerline.point) / plane_dot_dir
        P = tenon_centerline.point + tenon_centerline.direction * s

    tenon_dir = tenon_centerline.direction
    proj = tenon_dir - mortise_length_dir * safe_dot_product(tenon_dir, mortise_length_dir)
    proj_len_sq = safe_dot_product(proj, proj)
    if not fast_zero_test(proj_len_sq):
        direction_in_plane = normalize_vector(proj)
    else:
        MP = P - M
        mp_len_sq = safe_dot_product(MP, MP)
        if not fast_zero_test(mp_len_sq):
            direction_in_plane = normalize_vector(MP)
        else:
            direction_in_plane = mortise_timber.get_width_direction_global()

    return locate_plane_from_edge_in_direction(
        mortise_timber, TimberCenterline.CENTERLINE, direction_in_plane, distance_from_centerline
    )


# ============================================================================
# Butt Joint Shoulder Result
# ============================================================================

@dataclass(frozen=True)
class ButtJointShoulderResult:
    """
    Result of computing a butt joint shoulder plane and its associated marking space.

    Attributes:
        shoulder_plane: The shoulder plane (normal points from mortise centerline toward tenon).
        butt_direction: Direction the butt timber is pointing into the receiving timber.
        marking_space: Located where tenon centerline intersects the shoulder plane, oriented with:
            +X = shoulder_plane.normal (from mortise centerline toward tenon)
            +Y = caller-provided up_direction (orthogonalized)
            +Z = derived via right-hand rule
    """
    shoulder_plane: Plane
    butt_direction: Direction3D
    marking_space: Space


def compute_butt_joint_shoulder(
    arrangement: ButtJointTimberArrangement,
    distance_from_centerline: Numeric,
    up_direction: Direction3D,
) -> ButtJointShoulderResult:
    """
    Compute the shoulder plane and an oriented marking space for a butt joint.

    The marking space is positioned where the tenon (butt) timber's centerline
    intersects the shoulder plane, oriented with:
        +X = shoulder_plane.normal (from mortise centerline toward tenon)
        +Y = up_direction (orthogonalized against +X)
        +Z = right-hand rule cross product

    Args:
        arrangement: Butt joint arrangement (receiving_timber = mortise, butt_timber = tenon).
        distance_from_centerline: Signed offset from the mortise centerline toward the tenon.
            0 = plane through the mortise centerline. Positive = toward tenon.
        up_direction: Direction for +Y axis of the marking space. Will be orthogonalized
            against the shoulder plane normal.

    Returns:
        ButtJointShoulderResult with the shoulder plane, intersection point, and marking space.
    """
    tenon_timber = arrangement.butt_timber
    tenon_end = arrangement.butt_timber_end

    shoulder_plane = locate_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
        arrangement, distance_from_centerline
    )

    shoulder_from_tenon_end_mark = mark_distance_from_end_along_centerline(
        shoulder_plane, tenon_timber, tenon_end
    )
    shoulder_point_global = shoulder_from_tenon_end_mark.measure().position

    orientation = Orientation.from_x_and_y(
        x_direction=shoulder_plane.normal,
        y_direction=up_direction,
    )
    marking_space = Space(
        transform=Transform(position=shoulder_point_global, orientation=orientation)
    )

    butt_direction = tenon_timber.get_face_direction_global(tenon_end)

    return ButtJointShoulderResult(
        shoulder_plane=shoulder_plane,
        butt_direction=butt_direction,
        marking_space=marking_space,
    )
