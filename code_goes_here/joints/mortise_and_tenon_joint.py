"""
GiraffeCAD - Mortise and Tenon Joint Construction Functions
Contains various mortise and tenon joint implementations
"""

from __future__ import annotations  # Enable deferred annotation evaluation

import warnings
from functools import wraps

from code_goes_here.timber import *
from code_goes_here.measuring import (
    measure_top_center_position,
    measure_bottom_center_position,
    measure_position_on_centerline_from_bottom,
    measure_position_on_centerline_from_top,
    measure_into_face,
    measure_centerline,
    measure_edge,
    measure_plane_from_edge_in_direction,
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


# ============================================================================
# Helepers
# ============================================================================

def measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(arrangement: ButtJointTimberArrangement, distance_from_centerline: Numeric) -> Plane:
    """
    Measure the shoulder plane of the mortise timber from the centerline towards the tenon timber.

    The shoulder plane is perpendicular to the mortise timber length axis and
    offset from the mortise centerline in the cross-section direction toward
    the tenon timber centerline.

    The returned Plane's point lies at the intersection of the tenon centerline
    with the plane (offset by distance_from_centerline from the mortise centerline).

    Args:
        arrangement: Butt joint arrangement (receiving_timber = mortise, butt_timber = tenon)
        distance_from_centerline: Signed offset from the mortise centerline toward
            the tenon. 0 = plane through the mortise centerline. Positive = toward tenon.
    """
    mortise_timber = arrangement.receiving_timber
    tenon_timber = arrangement.butt_timber
    tenon_end = arrangement.butt_timber_end

    mortise_centerline = measure_centerline(mortise_timber)
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
    if zero_test(denom):
        M = mortise_centerline.point
    else:
        t_mortise = (b * e - c * d) / denom
        M = mortise_centerline.point + mortise_centerline.direction * t_mortise

    # Find P = intersection of tenon centerline with cross-section plane at M
    plane_dot_dir = safe_dot_product(mortise_length_dir, tenon_centerline.direction)
    if zero_test(plane_dot_dir):
        if zero_test(denom):
            P = tenon_centerline.point
        else:
            s_tenon = (a * e - b * d) / denom
            P = tenon_centerline.point + tenon_centerline.direction * s_tenon
    else:
        s = safe_dot_product(mortise_length_dir, M - tenon_centerline.point) / plane_dot_dir
        P = tenon_centerline.point + tenon_centerline.direction * s

    # Direction from M toward P in the cross-section
    MP = P - M
    mp_len_sq = safe_dot_product(MP, MP)
    if zero_test(mp_len_sq):
        # Centerlines intersect (or are parallel). Use the tenon direction
        # projected into the mortise cross-section as fallback.
        tenon_dir = tenon_centerline.direction
        proj = tenon_dir - mortise_length_dir * safe_dot_product(tenon_dir, mortise_length_dir)
        proj_len_sq = safe_dot_product(proj, proj)
        if zero_test(proj_len_sq):
            direction_in_plane = mortise_timber.get_width_direction_global()
        else:
            direction_in_plane = normalize_vector(proj)
    else:
        direction_in_plane = normalize_vector(MP)

    return measure_plane_from_edge_in_direction(
        mortise_timber, TimberCenterline.CENTERLINE, direction_in_plane, distance_from_centerline
    )

# ============================================================================
# Parameter Classes for Mortise and Tenon Joints
# ============================================================================


# TODO add tenon bore offset parameter, it could be none | auto | Numeric
@dataclass(frozen=True)
class SimplePegParameters:
    """
    Parameters for simple pegs in mortise and tenon joints.
    
    Attributes:
        shape: Shape specification for the peg (from PegShape enum)
        tenon_face: The face on the TENON timber that the pegs will be perpendicular to
                    (only valid if tenon_rotation is identity)
        peg_positions: List of (distance_from_shoulder, distance_from_centerline) tuples
                       - First value: distance along length axis measured from shoulder of tenon
                       - Second value: distance in perpendicular axis measured from center
        size: Peg diameter (for round pegs) or side length (for square pegs)
        depth: Depth measured from mortise face where peg goes in (None means all the way through the mortise timber)
        tenon_hole_offset: Offset distance of the hole in the tenon towards the shoulder so that the peg tightens the joint up. You should usually set this to 1-2mm
    """
    shape: PegShape
    # TODO rename to peg_face_on_tenon
    tenon_face: TimberLongFace
    peg_positions: List[Tuple[Numeric, Numeric]]
    size: Numeric
    depth: Optional[Numeric] = None
    tenon_hole_offset: Numeric = Rational(0)


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


def _deprecated_mortise_tenon(fn):
    """Mark a mortise-and-tenon function as deprecated in favor of cut_mortise_and_tenon_joint_on_FAT."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{fn.__name__} is deprecated; use cut_mortise_and_tenon_joint_on_FAT with ButtJointTimberArrangement instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return fn(*args, **kwargs)
    return wrapper


@_deprecated_mortise_tenon
def cut_mortise_and_tenon_DEPRECATED(
    tenon_timber: TimberLike,
    mortise_timber: TimberLike,
    tenon_end: TimberReferenceEnd,
    tenon_size: V2,
    tenon_length: Numeric,
    mortise_depth: Optional[Numeric] = None,
    mortise_shoulder_inset: Numeric = Rational(0),
    tenon_position: Optional[V2] = None,
    tenon_rotation: Optional[Orientation] = None,
    wedge_parameters: Optional[WedgeParameters] = None,
    peg_parameters: Optional[SimplePegParameters] = None
) -> Joint:
    """
    Generic mortise and tenon joint creation function with support for various options.
    
    This is the internal implementation function that handles all mortise and tenon variants.
    DO NOT call this directly - use the specific wrapper functions instead.
    
    Requirements:
        - Timbers must be face-aligned (orientations related by 90-degree rotations)
    
    Args:
        tenon_timber: Timber that will receive the tenon cut
        mortise_timber: Timber that will receive the mortise cut
        tenon_end: Which end of the tenon timber gets the tenon (TOP or BOTTOM)
        tenon_size: Cross-sectional size of tenon (X, Y) in tenon timber's local space
        tenon_length: Length of tenon extending from mortise face
        mortise_depth: Depth of mortise (None = through mortise, >= tenon_length)
        mortise_shoulder_inset: Inset distance from mortise face to shoulder plane (not yet supported, must be 0)
        tenon_position: Position of tenon in local coordinates of tenon timber (0,0 = centered on centerline)
        tenon_rotation: Rotation of tenon (default identity, currently must be identity)
        wedge_parameters: Optional wedge configuration (not yet supported)
        peg_parameters: Optional peg configuration (not yet supported)
        
    Returns:
        Joint object containing the two CutTimbers and any accessories (in global space)
        
    Raises:
        AssertionError: If unsupported parameters are provided or if timbers are not face-aligned
    """
    assert isinstance(tenon_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(tenon_end).__name__}"
    # ========================================================================
    # Set default values
    # ========================================================================

    # Set default tenon_position if not provided (centered)
    if tenon_position is None:
        tenon_position = Matrix([Rational(0), Rational(0)])
    
    # Set default tenon_rotation if not provided
    if tenon_rotation is None:
        tenon_rotation = Orientation.identity()

    # ========================================================================
    # Validate parameters
    # ========================================================================
    
    # Assert unsupported features
    assert wedge_parameters is None, "Wedge parameters not yet supported"
    assert tenon_rotation.matrix.equals(Orientation.identity().matrix), \
        "Tenon rotation not yet supported (must be identity)"
    assert mortise_shoulder_inset == 0, "Mortise shoulder inset not yet supported"
    
    # Assert timbers are face-aligned
    assert are_timbers_face_aligned(tenon_timber, mortise_timber), \
        "Timbers must be face-aligned for mortise and tenon joints"
    
    # Validate mortise_depth if provided
    if mortise_depth is not None:
        assert mortise_depth >= tenon_length, \
            f"Mortise depth ({mortise_depth}) must be >= tenon length ({tenon_length})"

    
    # ========================================================================
    # Step 1: Determine tenon directional centerline (this line starts at the where the tenon intersects the defined end of the timber and runs down the center of the tenon!)
    # ========================================================================
    
    # Get the direction of the tenon end in world coordinates
    tenon_end_direction = tenon_timber.get_face_direction_global(
        TimberFace.TOP if tenon_end == TimberReferenceEnd.TOP else TimberFace.BOTTOM
    )

    # Get the tenon end point in world coordinates
    if tenon_end == TimberReferenceEnd.TOP:
        tenon_end_point = measure_top_center_position(tenon_timber).position
    else:  # BOTTOM
        tenon_end_point = measure_bottom_center_position(tenon_timber).position
    
    # Apply tenon_position offset to get the actual tenon centerline start point
    tenon_x_direction = tenon_timber.get_face_direction_global(TimberFace.RIGHT)
    tenon_y_direction = tenon_timber.get_face_direction_global(TimberFace.FRONT)
    tenon_x_offset = tenon_x_direction * tenon_position[0]
    tenon_y_offset = tenon_y_direction * tenon_position[1]
    tenon_centerline_start_global = tenon_end_point + tenon_x_offset + tenon_y_offset
    
    # Tenon centerline direction (pointing from the tenon end toward the mortise)
    # The tenon extends OPPOSITE to tenon_end_direction (back into the timber toward the mortise)
    tenon_centerline_direction_global = -tenon_end_direction
    
    # ========================================================================
    # Step 2: Calculate mortise face plane
    # ========================================================================
    
    # Find which face of the mortise timber receives the mortise
    mortise_face = mortise_timber.get_closest_oriented_long_face_from_global_direction(-tenon_end_direction).to.face()

    # Get the mortise face normal (pointing outward from mortise timber)
    mortise_face_normal = mortise_timber.get_face_direction_global(mortise_face)
    
    # Get the mortise face offset (distance from centerline to face)
    if mortise_face in [TimberFace.RIGHT, TimberFace.LEFT]:
        face_offset = mortise_timber.size[0] / 2
    elif mortise_face in [TimberFace.FRONT, TimberFace.BACK]:
        face_offset = mortise_timber.size[1] / 2
    else:
        raise ValueError(f"Invalid mortise face: {mortise_face}")
    
    # We need a point on the mortise face plane. For simplicity, use the mortise timber's bottom position as the reference
    mortise_face_plane_point_global = mortise_timber.get_bottom_position_global() + mortise_face_normal * face_offset

    # ========================================================================
    # Step 3: Intersect the tenon centerline with the mortise face plane
    # ========================================================================
    
    # Check that tenon direction is not parallel to mortise face
    denominator = tenon_centerline_direction_global.dot(mortise_face_normal)
    assert abs(denominator) > EPSILON_GENERIC, \
        f"Tenon direction is parallel to mortise face (dot product: {denominator})"

  
    # Calculate intersection parameter t
    # Line: P = tenon_centerline_start_global + t * tenon_centerline_direction_global
    # Plane: (P - mortise_face_plane_point_global) · mortise_face_normal = 0
    # Solving: t = (mortise_face_plane_point_global - tenon_centerline_start_global) · mortise_face_normal / denominator
    t = (mortise_face_plane_point_global - tenon_centerline_start_global).dot(mortise_face_normal) / denominator
    
    # Calculate the actual intersection point
    intersection_point_global = tenon_centerline_start_global + tenon_centerline_direction_global * t


    # ========================================================================
    # Step 4: WARN that the tenon is pointing towards the mortise
    # this calculation is a little weird since it's more of a semantic check rather than a geometric check
    # ========================================================================
    
    # Calculate the center of the tenon timber centerline
    tenon_timber_center_global = tenon_timber.get_bottom_position_global() + tenon_timber.get_length_direction_global() * (tenon_timber.length / Rational(2))
    
    # Calculate signed distances from mortise face plane
    # Positive distance means on the side of the outward normal
    distance_tenon_end = (tenon_centerline_start_global - mortise_face_plane_point_global).dot(mortise_face_normal)
    distance_tenon_center = (tenon_timber_center_global - mortise_face_plane_point_global).dot(mortise_face_normal)
    
    # Check if both are on the same side of the plane (same sign)
    same_side = (distance_tenon_end * distance_tenon_center) > 0
    
    # Check if tenon is pointing away from mortise face
    # The tenon is pointing away if moving along the centerline increases the distance to the plane
    # This happens when: (tenon is on positive side AND direction is positive) OR (tenon is on negative side AND direction is negative)
    # Equivalently: distance_tenon_end and dot_product have the same sign
    dot_product = tenon_centerline_direction_global.dot(mortise_face_normal)
    pointing_away = (distance_tenon_end * dot_product) > 0
    
    # a weaker less semantic, more geometric check might be to check if both ends of the tenon timber are on the same side AND the tenon end is pointing away from the mortise face
    if same_side and pointing_away:
        print(f"⚠️  Warning: The tenon end seems to be pointing AWAY from the mortise timber.")
        print(f"    Are you sure you chose the right end of the tenon timber?")
        print(f"    Tenon end: {tenon_end}, Mortise face: {mortise_face}")
        print(f"    (Both the tenon end and tenon timber center are on the same side of the mortise face,")
        print(f"     AND the tenon end is pointing away from the mortise)")
    
    
    # ========================================================================
    # Step 4: Check if intersection is within mortise timber face bounds
    # ========================================================================
    
    # Transform intersection point to mortise timber's local coordinate system
    intersection_point_mortise_timber_local = safe_transform_vector(mortise_timber.orientation.matrix.T, (intersection_point_global - mortise_timber.get_bottom_position_global()))
    
    # NOTE should only check one axis, checking both is fine too...

    # Check bounds in the local XY plane (the face is perpendicular to one of these axes)
    # Determine which local axes define the face bounds
    half_width = mortise_timber.size[0] / 2
    half_height = mortise_timber.size[1] / 2
    
    # Check if the intersection is within the timber cross-section bounds
    x_in_bounds = abs(intersection_point_mortise_timber_local[0]) <= half_width
    y_in_bounds = abs(intersection_point_mortise_timber_local[1]) <= half_height
    
    if not (x_in_bounds and y_in_bounds):
        print(f"Warning: Mortise intersection at local position ({float(intersection_point_mortise_timber_local[0]):.4f}, "
              f"{float(intersection_point_mortise_timber_local[1]):.4f}, {float(intersection_point_mortise_timber_local[2]):.4f}) "
              f"is outside mortise timber face bounds (±{float(half_width):.4f}, ±{float(half_height):.4f})")
    
    # ========================================================================
    # Create mortise cut (CSGCut with RectangularPrism)
    # Mortise is a rectangular hole cut into the mortise timber
    # The hole matches the shape of the tenon but the depth might be different 
    # ========================================================================
    

    # TODO handle mortise_shoulder_inset 
    # TODO handle mortise_shoulder_relief_housing_cut : ReliefHousingCut
    

    # Determine mortise depth (if not specified, make it a through mortise)
    # NOTE `(tenon_length + mortise_timber.size[0] + mortise_timber.size[1])` is fine but better to be more precise and use the exact dimension of the mortise timber that the tenon is going through
    actual_mortise_depth = mortise_depth if mortise_depth is not None else (tenon_length + mortise_timber.size[0] + mortise_timber.size[1])
    
    # Create the mortise prism in the mortise timber's LOCAL coordinate system
    # We create a prism representing the tenon volume
    relative_orientation = Orientation(safe_transform_vector(mortise_timber.orientation.matrix.T, tenon_timber.orientation.matrix))
    
    # The intersection_point_global is already the tenon center position in world coordinates
    # (with tenon_position offset already applied)
    # Transform it to mortise timber's local coordinates
    tenon_origin_local = safe_transform_vector(mortise_timber.orientation.matrix.T, (intersection_point_global - mortise_timber.get_bottom_position_global()))
    
    # Create a prism representing the tenon volume (in mortise timber's local space)
    from code_goes_here.cutcsg import RectangularPrism
    from code_goes_here.rule import Transform
    tenon_transform = Transform(position=tenon_origin_local, orientation=relative_orientation)
    tenon_prism_in_mortise_local = RectangularPrism(
        size=tenon_size,
        transform=tenon_transform,
        start_distance= -actual_mortise_depth if tenon_end == TimberReferenceEnd.BOTTOM else 0,
        end_distance= actual_mortise_depth if tenon_end == TimberReferenceEnd.TOP else 0
    )
    
    # Create the Cut for the mortise
    mortise_cut = Cutting(
        timber=mortise_timber,
        maybe_top_end_cut=None,
        maybe_bottom_end_cut=None,
        negative_csg=tenon_prism_in_mortise_local
    )
    
    # ========================================================================
    # Create tenon cut (single CSG cut)
    # ========================================================================
    
    # The tenon is created by:
    # 1. Creating a prism representing the infinite timber end beyond the shoulder
    # 2. Subtracting the tenon prism from it
    # 3. Using the result as a single CSG cut
    
    # Calculate the shoulder plane position in world coordinates
    if tenon_end == TimberReferenceEnd.TOP:
        shoulder_plane_point_global = measure_top_center_position(tenon_timber).position - tenon_timber.get_length_direction_global() * t
    else:  # BOTTOM
        shoulder_plane_point_global = measure_bottom_center_position(tenon_timber).position + tenon_timber.get_length_direction_global() * t
    
    # Apply tenon_position offset to shoulder plane point
    tenon_x_direction = tenon_timber.get_face_direction_global(TimberFace.RIGHT)
    tenon_y_direction = tenon_timber.get_face_direction_global(TimberFace.FRONT)
    tenon_x_offset_vec = tenon_x_direction * tenon_position[0]
    tenon_y_offset_vec = tenon_y_direction * tenon_position[1]
    shoulder_plane_point_with_offset_global = shoulder_plane_point_global + tenon_x_offset_vec + tenon_y_offset_vec
    
    # Convert shoulder plane point to tenon timber's local coordinates
    shoulder_plane_point_with_offset_local = safe_transform_vector(tenon_timber.orientation.matrix.T, (shoulder_plane_point_with_offset_global - tenon_timber.get_bottom_position_global()))
    
    # Create infinite prism representing the timber end beyond the shoulder
    # This extends from the shoulder to infinity in the tenon direction
    from code_goes_here.cutcsg import Difference, HalfSpace
    
    if tenon_end == TimberReferenceEnd.TOP:
        # For top end, the timber end extends from shoulder to +infinity
        timber_end_prism = RectangularPrism(
            size=tenon_timber.size,
            transform=Transform.identity(),
            start_distance=shoulder_plane_point_with_offset_local[2],  # Z coordinate in local space (with offset)
            end_distance=None  # Infinite
        )
    else:  # BOTTOM
        # For bottom end, the timber end extends from -infinity to shoulder
        timber_end_prism = RectangularPrism(
            size=tenon_timber.size,
            transform=Transform.identity(),
            start_distance=None,  # Infinite
            end_distance=shoulder_plane_point_with_offset_local[2]  # Z coordinate in local space (with offset)
        )
    
    # Create tenon prism in local coordinates (with offset)
    # The tenon extends from the shoulder plane
    if tenon_end == TimberReferenceEnd.TOP:
        tenon_start = shoulder_plane_point_with_offset_local[2]
        tenon_end_dist = tenon_start + tenon_length
    else:  # BOTTOM
        tenon_end_dist = shoulder_plane_point_with_offset_local[2]
        tenon_start = tenon_end_dist - tenon_length
    
    tenon_transform_local = Transform(
        position=Matrix([tenon_position[0], tenon_position[1], Rational(0)]),
        orientation=Orientation.identity()
    )
    tenon_prism_local = RectangularPrism(
        size=tenon_size,
        transform=tenon_transform_local,
        start_distance=tenon_start,
        end_distance=tenon_end_dist
    )
    
    # Create shoulder plane half-plane to cut away material beyond the shoulder
    # The shoulder plane is perpendicular to the timber length direction (Z axis in local coords)
    if tenon_end == TimberReferenceEnd.TOP:
        # For top end, we want to keep material below the shoulder (negative Z)
        # Normal points down (-Z) to keep points where Z <= shoulder_z
        shoulder_plane_normal = Matrix([Rational(0), Rational(0), Rational(-1)])
        shoulder_plane_offset = -shoulder_plane_point_with_offset_local[2]
    else:  # BOTTOM
        # For bottom end, we want to keep material above the shoulder (positive Z)
        # Normal points up (+Z) to keep points where Z >= shoulder_z
        shoulder_plane_normal = Matrix([Rational(0), Rational(0), Rational(1)])
        shoulder_plane_offset = shoulder_plane_point_with_offset_local[2]
    
    shoulder_half_plane = HalfSpace(
        normal=shoulder_plane_normal,
        offset=shoulder_plane_offset
    )
    
    # Create the cut CSG: timber_end - tenon - shoulder_plane
    # This represents everything beyond the shoulder except the tenon itself
    tenon_cut_csg = Difference(
        base=timber_end_prism,
        subtract=[tenon_prism_local, shoulder_half_plane]
    )
    
    # Create a redundant end cut that points away from the timber
    # This doesn't actually cut any additional material, but marks that this end has a cut
    if tenon_end == TimberReferenceEnd.TOP:
        # At the top, create a half space that removes everything above the timber end
        # (which is already removed by the negative_csg)
        redundant_end_cut = HalfSpace(normal=create_v3(0, 0, 1), offset=tenon_timber.length)
    else:  # BOTTOM
        # At the bottom, create a half space that removes everything below the timber end
        redundant_end_cut = HalfSpace(normal=create_v3(0, 0, -1), offset=Rational(0))
    
    # Create a single CSG cut with the redundant end cut marker
    tenon_cut = Cutting(
        timber=tenon_timber,
        maybe_top_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.TOP else None,
        maybe_bottom_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.BOTTOM else None,
        negative_csg=tenon_cut_csg
    )
    
    tenon_cuts = [tenon_cut]
    
    # ========================================================================
    # Create peg holes and accessories if pegs are specified
    # Note: Peg holes are created in timber local space, but accessories
    # are stored in global space for direct rendering without transformation
    # ========================================================================
    
    joint_accessories = {}
    
    if peg_parameters is not None:
        # Assert tenon_rotation is identity (required for peg positioning)
        assert tenon_rotation.matrix.equals(Orientation.identity().matrix), \
            "Pegs require tenon_rotation to be identity"
        
        # Get peg diameter/size from parameters
        peg_size = peg_parameters.size
        
        # Determine which axis the peg travels along and offset axes
        # For simplicity with face-aligned timbers, work directly in local coords
        if peg_parameters.tenon_face in [TimberLongFace.RIGHT, TimberLongFace.LEFT]:
            # Peg travels along X axis
            peg_length_axis_index = 0
            lateral_position_index = 1  # Y for distance_from_centerline
            shoulder_offset_axis_index = 2  # Z for distance_from_shoulder
            peg_sign = 1 if peg_parameters.tenon_face == TimberLongFace.RIGHT else -1
        elif peg_parameters.tenon_face in [TimberLongFace.FRONT, TimberLongFace.BACK]:
            # Peg travels along Y axis
            peg_length_axis_index = 1
            lateral_position_index = 0  # X for distance_from_centerline
            shoulder_offset_axis_index = 2  # Z for distance_from_shoulder
            peg_sign = 1 if peg_parameters.tenon_face == TimberLongFace.FRONT else -1
        else:
            raise ValueError(f"Invalid peg face: {peg_parameters.tenon_face}")
        

        # Create orientation for peg prism using timber orientation methods
        # The peg position is at the timber SURFACE, and the peg extends INTO the timber
        # So the peg's Z-axis must point INTO the timber (opposite of surface normal)
        
        if peg_length_axis_index == 0:  # Peg through X face
            if peg_sign == 1:  # RIGHT face (surface at +X)
                # Peg extends INTO timber in -X direction (west)
                peg_orientation_tenon_local = Orientation.pointing_forward()
            else:  # LEFT face (surface at -X)
                # Peg extends INTO timber in +X direction (east)
                peg_orientation_tenon_local = Orientation.pointing_backward()
        else:  # Peg through Y face
            if peg_sign == 1:  # FRONT face (surface at +Y)
                # Peg extends INTO timber in -Y direction (south)
                peg_orientation_tenon_local = Orientation.pointing_left()
            else:  # BACK face (surface at -Y)
                # Peg extends INTO timber in +Y direction (north)
                peg_orientation_tenon_local = Orientation.pointing_right()
        
        # Create peg holes for each peg position
        peg_holes_in_tenon_local = []
        peg_holes_in_mortise_local = []
         
        for peg_idx, (distance_from_shoulder, distance_from_centerline) in enumerate(peg_parameters.peg_positions):
            # Calculate peg insertion point in tenon timber's local space
            # Start at the tenon position offset, then add the peg-specific offsets
            peg_pos_on_tenon_face_local = Matrix([Rational(0), Rational(0), Rational(0)])
            
            # Add tenon position offset
            peg_pos_on_tenon_face_local[0] = tenon_position[0]
            peg_pos_on_tenon_face_local[1] = tenon_position[1]
            
            # Add distance from shoulder (along length axis)
            # Also apply tenon_hole_offset to shift the hole towards the shoulder (tightens joint)
            if tenon_end == TimberReferenceEnd.TOP:
                peg_pos_on_tenon_face_local[2] = shoulder_plane_point_with_offset_local[2] + distance_from_shoulder
                peg_pos_on_tenon_face_local_z_with_peg_offset = - peg_parameters.tenon_hole_offset
            else:  # BOTTOM
                peg_pos_on_tenon_face_local[2] = shoulder_plane_point_with_offset_local[2] - distance_from_shoulder
                peg_pos_on_tenon_face_local_z_with_peg_offset = peg_parameters.tenon_hole_offset
            
            # Add distance from centerline (along lateral position axis)
            peg_pos_on_tenon_face_local[lateral_position_index] = peg_pos_on_tenon_face_local[lateral_position_index] + distance_from_centerline
            
            # Move to the tenon face surface (where peg enters)
            if peg_parameters.tenon_face == TimberLongFace.RIGHT:
                peg_pos_on_tenon_face_local[0] = tenon_timber.size[0] / 2
            elif peg_parameters.tenon_face == TimberLongFace.LEFT:
                peg_pos_on_tenon_face_local[0] = -tenon_timber.size[0] / 2
            elif peg_parameters.tenon_face == TimberLongFace.FRONT:
                peg_pos_on_tenon_face_local[1] = tenon_timber.size[1] / 2
            elif peg_parameters.tenon_face == TimberLongFace.BACK:
                peg_pos_on_tenon_face_local[1] = -tenon_timber.size[1] / 2
            
            # Calculate the peg depth into the mortise timber
            # If not specified, use the dimension of the mortise timber perpendicular to the mortise face
            if peg_parameters.depth is not None:
                peg_depth = peg_parameters.depth
            else:
                # Determine which dimension based on which face the mortise is on
                if mortise_face in [TimberFace.RIGHT, TimberFace.LEFT]:
                    peg_depth = mortise_timber.size[0]  # X dimension
                elif mortise_face in [TimberFace.FRONT, TimberFace.BACK]:
                    peg_depth = mortise_timber.size[1]  # Y dimension
                else:  # TOP or BOTTOM
                    assert False, "Invalid mortise face"
            
            stickout_length = peg_depth * Rational(1, 2)  # Stickout is 0.5 times the depth
            

            peg_pos_on_tenon_face_local_with_peg_offset = peg_pos_on_tenon_face_local + create_v3(Rational(0), Rational(0), peg_pos_on_tenon_face_local_z_with_peg_offset)

            # Create peg hole prism in tenon local space
            # The peg position is ON the tenon face, and extends into the tenon
            peg_transform_tenon = Transform(
                position=peg_pos_on_tenon_face_local_with_peg_offset,
                orientation=peg_orientation_tenon_local
            )
            peg_hole_tenon = RectangularPrism(
                size=Matrix([peg_size, peg_size]),
                transform=peg_transform_tenon,
                start_distance=0,
                # TODO substract distance between tenon face and mortise face to get depth from tenon face
                end_distance=peg_depth  # Stops at mortise face
            )
            peg_holes_in_tenon_local.append(peg_hole_tenon)
            

            # Next we cut the peg hole in themortise timber

            # Transform peg position to global space
            peg_pos_on_tenon_face_global = tenon_timber.get_bottom_position_global() + safe_transform_vector(tenon_timber.orientation.matrix, peg_pos_on_tenon_face_local)
            peg_orientation_global = Orientation(safe_transform_vector(tenon_timber.orientation.matrix, peg_orientation_tenon_local.matrix))
            peg_direction_global = peg_orientation_global.matrix[:, 2] # Z-axis of peg in global space

            # Calculate where the peg intersects the mortise timber
            # The peg starts at the tenon face points in the peg's Z-axis direction
            
            # Get the tenon face normal (where the peg enters the tenon timber)
            # TODO rename to tenon_peg_entry_face
            tenon_face = peg_parameters.tenon_face.to.face()
            tenon_face_direction = tenon_timber.get_face_direction_global(tenon_face)
            tenon_face_normal = tenon_face_direction
            
            # Find which face of the mortise timber the peg enters
            # Pick the face whose normal has the largest dot product with the tenon face normal
            best_face = None
            best_dot_product = -float('inf')
            
            for face in [TimberFace.RIGHT, TimberFace.LEFT, TimberFace.FRONT, TimberFace.BACK]:
                # Skip the mortise face itself (where the tenon enters) surely it's not this face
                if face == mortise_face:
                    continue
                
                # Get face normal
                face_direction = mortise_timber.get_face_direction_global(face)
                face_normal = face_direction
                
                # Calculate dot product with tenon face normal
                dot_product_with_tenon_face = tenon_face_normal.dot(face_normal)
                
                # Keep track of the face with the largest dot product with tenon face
                if dot_product_with_tenon_face > best_dot_product:
                    best_dot_product = dot_product_with_tenon_face
                    best_face = face
            
            assert best_face is not None, "Could not find mortise peg entry face"
            
            # Now calculate the intersection point on the best face
            mortise_peg_entry_face = best_face
            
            # Get the face normal and offset
            peg_entry_face_direction = mortise_timber.get_face_direction_global(mortise_peg_entry_face)
            peg_entry_face_normal = peg_entry_face_direction
            
            if mortise_peg_entry_face in [TimberFace.RIGHT, TimberFace.LEFT]:
                peg_entry_face_offset = mortise_timber.size[0] / 2
            elif mortise_peg_entry_face in [TimberFace.FRONT, TimberFace.BACK]:
                peg_entry_face_offset = mortise_timber.size[1] / 2
            else:  # TOP or BOTTOM
                peg_entry_face_offset = mortise_timber.length / 2
            

            # Calculate the point where the peg enters on the mortise peg entry face plane


            # Get a point on the mortise peg entry face plane (any point)
            peg_entry_face_plane_point_global = mortise_timber.get_bottom_position_global() + peg_entry_face_normal * peg_entry_face_offset
            
            # Ray-plane intersection to find where peg enters the mortise face
            # Ray: P = peg_pos_on_tenon_face_global + t * peg_direction_global
            # Plane: (P - peg_entry_face_plane_point_global) · peg_entry_face_normal = 0
            denominator = peg_direction_global.dot(peg_entry_face_normal)
            
            # The peg should not be parallel to the entry face
            assert abs(denominator) > EPSILON_GENERIC, \
                f"Peg direction is parallel to mortise peg entry face {mortise_peg_entry_face} (dot product: {denominator}), pick a different tenon face or direction for the peg"
            
            # intersect the line from the peg entry point on the tenon face with the plane of the mortise peg entry face
            t_peg = (peg_entry_face_plane_point_global - peg_pos_on_tenon_face_global).dot(peg_entry_face_normal) / denominator
            
            # Calculate the intersection point on the mortise peg entry face
            peg_pos_on_mortise_face_global = peg_pos_on_tenon_face_global + peg_direction_global * t_peg
            
            # Transform the intersection point to mortise timber's local coordinates
            peg_pos_on_mortise_face_local = safe_transform_vector(mortise_timber.orientation.matrix.T, (peg_pos_on_mortise_face_global - mortise_timber.get_bottom_position_global()))
            
            # Transform peg orientation to mortise local space (peg_orientation_global already calculated above)
            peg_orientation_mortise_local = Orientation(safe_transform_vector(mortise_timber.orientation.matrix.T, peg_orientation_global.matrix))
            
            # Create peg hole prism in mortise local space
            # The peg position is ON the mortise face, and extends forward into the mortise
            peg_transform_mortise = Transform(
                position=peg_pos_on_mortise_face_local,
                orientation=peg_orientation_mortise_local
            )
            peg_hole_mortise = RectangularPrism(
                size=Matrix([peg_size, peg_size]),
                transform=peg_transform_mortise,
                start_distance=Rational(0),  # Starts at mortise face
                end_distance=peg_depth  # Extends into mortise
            )
            peg_holes_in_mortise_local.append(peg_hole_mortise)
            
            # Create peg accessory in global space
            # Internal calculations were done in mortise local space for clarity,
            # but the final accessory is stored in global space
            
            # Transform peg position from mortise local space to global space
            peg_pos_global = mortise_timber.get_bottom_position_global() + safe_transform_vector(mortise_timber.orientation.matrix, peg_pos_on_mortise_face_local)
            
            # Transform peg orientation from mortise local space to global space
            peg_orientation_global = Orientation(safe_transform_vector(mortise_timber.orientation.matrix, peg_orientation_mortise_local.matrix))
            
            # forward_length: how deep the peg goes into the mortise
            # stickout_length: how much of the peg remains outside (in the tenon)
            peg_accessory = Peg(
                transform=Transform(position=peg_pos_global, orientation=peg_orientation_global),
                size=peg_size,
                shape=peg_parameters.shape,
                forward_length=peg_depth,
                stickout_length=stickout_length
            )
            joint_accessories[f"peg_{peg_idx}"] = peg_accessory
        
        # Union the peg holes to the existing tenon/mortise timber cut CSGs
        if peg_holes_in_tenon_local or peg_holes_in_mortise_local:
            from code_goes_here.cutcsg import SolidUnion
        
        if peg_holes_in_tenon_local:
            # Union peg holes into the negative cut CSG for tenon (single union with all children)
            tenon_cut_with_pegs_csg = CSGUnion(children=[tenon_cut_csg] + peg_holes_in_tenon_local)
            tenon_cut = Cutting(
                timber=tenon_timber,
                maybe_top_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.TOP else None,
                maybe_bottom_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.BOTTOM else None,
                negative_csg=tenon_cut_with_pegs_csg
            )
            tenon_cuts = [tenon_cut]
        
        if peg_holes_in_mortise_local:
            # Union peg holes into the negative cut CSG for mortise (single union with all children)
            mortise_cut_with_pegs_csg = CSGUnion(children=[tenon_prism_in_mortise_local] + peg_holes_in_mortise_local)
            mortise_cut = Cutting(
                timber=mortise_timber,
                maybe_top_end_cut=None,
                maybe_bottom_end_cut=None,
                negative_csg=mortise_cut_with_pegs_csg
            )
    
    # ========================================================================
    # Create CutTimber objects and Joint
    # ========================================================================
    
    mortise_cut_timber = CutTimber(mortise_timber, cuts=[mortise_cut])
    tenon_cut_timber = CutTimber(tenon_timber, cuts=tenon_cuts)
    
    return Joint(
        cut_timbers={"tenon_timber": tenon_cut_timber, "mortise_timber": mortise_cut_timber},
        jointAccessories=joint_accessories
    )



# TODO rename to cut_mortise_and_tenon
def cut_mortise_and_tenon_many_options_do_not_call_me_directly_NEWVERSION(
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
    Generic mortise and tenon joint creation function with support for various options.
    
    Args:
        arrangement: Butt joint timber arrangement (butt_timber = tenon, receiving_timber = mortise)
        tenon_size: Cross-sectional size of tenon (X, Y) in tenon timber's local space
        tenon_length: Length of tenon extending from mortise face. you may need to set this a little longer than you think for angled joints.
        mortise_depth: Depth of mortise (None = through mortise) this is measured different depending on the value of crop_tenon_to_mortise_orientation_on_angled_joints
        mortise_shoulder_distance_from_centerline: Signed distance from the mortise
            centerline to the shoulder plane, measured within the mortise cross-section
            in the direction toward the tenon centerline. 0 = shoulder at the mortise
            centerline. Positive pushes the shoulder toward the tenon.
        tenon_position: Position of tenon in local coordinates of tenon timber (0,0 = centered on centerline)
        wedge_parameters: Optional wedge configuration (not yet supported)
        peg_parameters: Optional peg configuration. TODO: peg X position is measured in the tenon length axis, whereas peg Y position is measured in the mortise length axis! This makes positioning pegs on angled braces a lot easier.

        crop_tenon_to_mortise_orientation_on_angled_joints: if true, "crops" the tenon so it's depth in the mortise face axis is equal to mortise_depth, and the pointy end of the tenon is cropped to the mortise hole right where the tenon edge and joint shoulder meet. If false, the mortise hole is sized to the tenon with its depth in the tenon axis direction measured from the shoulder is mortise_depth.
        
    Returns:
        Joint object containing the two CutTimbers and any accessories (in global space)
    """
    tenon_timber = arrangement.butt_timber
    mortise_timber = arrangement.receiving_timber
    tenon_end = arrangement.butt_timber_end

    # Default tenon_position to centered (0, 0)
    if tenon_position is None:
        tenon_position = Matrix([Rational(0), Rational(0)])

    # TODO default mortise depth if mortise_depth is None

    # -------------------------------------------------------------------------
    # Step 2: Determine which face of the mortise timber the tenon enters from
    # TODO remove, calculate directly from tenon_end_direction and mortise_shoulder_distance_from_centerline
    # -------------------------------------------------------------------------
    tenon_end_direction = tenon_timber.get_face_direction_global(
        TimberFace.TOP if tenon_end == TimberReferenceEnd.TOP else TimberFace.BOTTOM
    )
    mortise_face = mortise_timber.get_closest_oriented_long_face_from_global_direction(
        -tenon_end_direction
    ).to.face()


    # -------------------------------------------------------------------------
    # Step 3: Shoulder plane from centerline toward tenon
    # -------------------------------------------------------------------------
    shoulder_plane = measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
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
    # Step 5: Determine the angle of the mortise timber to the tenon timber
    # -------------------------------------------------------------------------
    mortise_face_normal = mortise_timber.get_face_direction_global(mortise_face)
    cos_angle = safe_dot_product(
        normalize_vector(mortise_face_normal), normalize_vector(tenon_end_direction)
    )

    # -------------------------------------------------------------------------
    # Tenon prism (origin at marking_space) and shoulder half-space
    # -------------------------------------------------------------------------
    from sympy import sqrt

    # Back-extension from shoulder so prism fully contains tenon at oblique angles
    sin_angle_sq = Integer(1) - cos_angle * cos_angle
    sin_angle = sqrt(sin_angle_sq) if sin_angle_sq >= 0 else Integer(1)
    sin_angle_safe = max(sin_angle, Rational(1, 10000))  # avoid division by zero when parallel
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

        # Crop 2: depth of tenon — plane parallel to shoulder, mortise_depth from shoulder (into mortise).
        # Remove tenon where dot(p, tenon_end_direction) >= dot(origin, tenon_end_direction) + depth
        mortise_depth_crop_global = HalfSpace(
            normal=-mortise_face_normal,
            offset=mortise_depth - safe_dot_product(mortise_face_normal, get_point_on_face_global(mortise_face, mortise_timber)),
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

    face_half_size = mortise_timber.get_size_in_face_normal_axis(mortise_face) / Integer(2)
    needs_shoulder_notch = (
        mortise_shoulder_distance_from_centerline < face_half_size
        and not zero_test(face_half_size - mortise_shoulder_distance_from_centerline)
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
    tenon_length_direction_global = safe_transform_vector(
        marking_space.transform.orientation.matrix, Matrix([Integer(0), Integer(0), Integer(1)])
    )
    tip_position_global = marking_space.transform.position + tenon_length_direction_global * max(tenon_length, max(tenon_size[0], tenon_size[1])/sin_angle_safe)
    tip_position_local = tenon_timber.transform.global_to_local(tip_position_global)
    tip_z_local = tip_position_local[2]
    redundant_end_cut = (
        HalfSpace(normal=create_v3(Integer(0), Integer(0), Integer(1)), offset=tip_z_local)
        if tenon_end == TimberReferenceEnd.TOP
        else HalfSpace(normal=create_v3(Integer(0), Integer(0), Integer(-1)), offset=-tip_z_local)
    )
    tenon_cut = Cutting(
        timber=tenon_timber,
        maybe_top_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.TOP else None,
        maybe_bottom_end_cut=redundant_end_cut if tenon_end == TimberReferenceEnd.BOTTOM else None,
        negative_csg=tenon_cut_csg,
    )

    joint_accessories = {}
    if peg_parameters is not None:
        peg_size = peg_parameters.size
        if peg_parameters.tenon_face in [TimberLongFace.RIGHT, TimberLongFace.LEFT]:
            peg_length_axis_index = 0
            lateral_position_index = 1
            shoulder_offset_axis_index = 2
            peg_sign = 1 if peg_parameters.tenon_face == TimberLongFace.RIGHT else -1
        elif peg_parameters.tenon_face in [TimberLongFace.FRONT, TimberLongFace.BACK]:
            peg_length_axis_index = 1
            lateral_position_index = 0
            shoulder_offset_axis_index = 2
            peg_sign = 1 if peg_parameters.tenon_face == TimberLongFace.FRONT else -1
        else:
            raise ValueError(f"Invalid peg face: {peg_parameters.tenon_face}")

        if peg_length_axis_index == 0:
            if peg_sign == 1:
                peg_orientation_tenon_local = Orientation.pointing_forward()
            else:
                peg_orientation_tenon_local = Orientation.pointing_backward()
        else:
            if peg_sign == 1:
                peg_orientation_tenon_local = Orientation.pointing_left()
            else:
                peg_orientation_tenon_local = Orientation.pointing_right()

        shoulder_plane_point_with_offset_local = tenon_timber.transform.global_to_local(marking_origin_global)
        peg_holes_in_tenon_local = []
        peg_holes_in_mortise_local = []

        for peg_idx, (distance_from_shoulder, distance_from_centerline) in enumerate(peg_parameters.peg_positions):
            peg_pos_on_tenon_face_local = Matrix([Rational(0), Rational(0), Rational(0)])
            peg_pos_on_tenon_face_local[0] = tenon_position[0]
            peg_pos_on_tenon_face_local[1] = tenon_position[1]
            if tenon_end == TimberReferenceEnd.TOP:
                peg_pos_on_tenon_face_local[2] = shoulder_plane_point_with_offset_local[2] + distance_from_shoulder
                peg_pos_on_tenon_face_local_z_with_peg_offset = -peg_parameters.tenon_hole_offset
            else:
                peg_pos_on_tenon_face_local[2] = shoulder_plane_point_with_offset_local[2] - distance_from_shoulder
                peg_pos_on_tenon_face_local_z_with_peg_offset = peg_parameters.tenon_hole_offset
            peg_pos_on_tenon_face_local[lateral_position_index] = peg_pos_on_tenon_face_local[lateral_position_index] + distance_from_centerline
            if peg_parameters.tenon_face == TimberLongFace.RIGHT:
                peg_pos_on_tenon_face_local[0] = tenon_timber.size[0] / 2
            elif peg_parameters.tenon_face == TimberLongFace.LEFT:
                peg_pos_on_tenon_face_local[0] = -tenon_timber.size[0] / 2
            elif peg_parameters.tenon_face == TimberLongFace.FRONT:
                peg_pos_on_tenon_face_local[1] = tenon_timber.size[1] / 2
            elif peg_parameters.tenon_face == TimberLongFace.BACK:
                peg_pos_on_tenon_face_local[1] = -tenon_timber.size[1] / 2

            if peg_parameters.depth is not None:
                peg_depth = peg_parameters.depth
            else:
                if mortise_face in [TimberFace.RIGHT, TimberFace.LEFT]:
                    peg_depth = mortise_timber.size[0]
                elif mortise_face in [TimberFace.FRONT, TimberFace.BACK]:
                    peg_depth = mortise_timber.size[1]
                else:
                    assert False, "Invalid mortise face"
            stickout_length = peg_depth * Rational(1, 2)

            peg_pos_on_tenon_face_local_with_peg_offset = peg_pos_on_tenon_face_local + create_v3(Rational(0), Rational(0), peg_pos_on_tenon_face_local_z_with_peg_offset)
            peg_transform_tenon = Transform(
                position=peg_pos_on_tenon_face_local_with_peg_offset,
                orientation=peg_orientation_tenon_local
            )
            peg_hole_tenon = RectangularPrism(
                size=Matrix([peg_size, peg_size]),
                transform=peg_transform_tenon,
                start_distance=0,
                end_distance=peg_depth
            )
            peg_holes_in_tenon_local.append(peg_hole_tenon)

            peg_pos_on_tenon_face_global = tenon_timber.get_bottom_position_global() + safe_transform_vector(tenon_timber.orientation.matrix, peg_pos_on_tenon_face_local)
            peg_orientation_global = Orientation(safe_transform_vector(tenon_timber.orientation.matrix, peg_orientation_tenon_local.matrix))
            peg_direction_global = peg_orientation_global.matrix[:, 2]
            tenon_face = peg_parameters.tenon_face.to.face()
            tenon_face_direction = tenon_timber.get_face_direction_global(tenon_face)
            tenon_face_normal = tenon_face_direction
            best_face = None
            best_dot_product = -float('inf')
            for face in [TimberFace.RIGHT, TimberFace.LEFT, TimberFace.FRONT, TimberFace.BACK]:
                if face == mortise_face:
                    continue
                face_direction = mortise_timber.get_face_direction_global(face)
                face_normal = face_direction
                dot_product_with_tenon_face = tenon_face_normal.dot(face_normal)
                if dot_product_with_tenon_face > best_dot_product:
                    best_dot_product = dot_product_with_tenon_face
                    best_face = face
            assert best_face is not None, "Could not find mortise peg entry face"
            mortise_peg_entry_face = best_face
            peg_entry_face_direction = mortise_timber.get_face_direction_global(mortise_peg_entry_face)
            peg_entry_face_normal = peg_entry_face_direction
            if mortise_peg_entry_face in [TimberFace.RIGHT, TimberFace.LEFT]:
                peg_entry_face_offset = mortise_timber.size[0] / 2
            elif mortise_peg_entry_face in [TimberFace.FRONT, TimberFace.BACK]:
                peg_entry_face_offset = mortise_timber.size[1] / 2
            else:
                peg_entry_face_offset = mortise_timber.length / 2
            peg_entry_face_plane_point_global = mortise_timber.get_bottom_position_global() + peg_entry_face_normal * peg_entry_face_offset
            denominator = peg_direction_global.dot(peg_entry_face_normal)
            assert abs(denominator) > EPSILON_GENERIC, (
                f"Peg direction is parallel to mortise peg entry face {mortise_peg_entry_face} (dot product: {denominator}), pick a different tenon face or direction for the peg"
            )
            t_peg = (peg_entry_face_plane_point_global - peg_pos_on_tenon_face_global).dot(peg_entry_face_normal) / denominator
            peg_pos_on_mortise_face_global = peg_pos_on_tenon_face_global + peg_direction_global * t_peg
            peg_pos_on_mortise_face_local = safe_transform_vector(mortise_timber.orientation.matrix.T, (peg_pos_on_mortise_face_global - mortise_timber.get_bottom_position_global()))
            peg_orientation_mortise_local = Orientation(safe_transform_vector(mortise_timber.orientation.matrix.T, peg_orientation_global.matrix))
            peg_transform_mortise = Transform(
                position=peg_pos_on_mortise_face_local,
                orientation=peg_orientation_mortise_local
            )
            peg_hole_mortise = RectangularPrism(
                size=Matrix([peg_size, peg_size]),
                transform=peg_transform_mortise,
                start_distance=Rational(0),
                end_distance=peg_depth
            )
            peg_holes_in_mortise_local.append(peg_hole_mortise)
            peg_pos_global = mortise_timber.get_bottom_position_global() + safe_transform_vector(mortise_timber.orientation.matrix, peg_pos_on_mortise_face_local)
            peg_orientation_global = Orientation(safe_transform_vector(mortise_timber.orientation.matrix, peg_orientation_mortise_local.matrix))
            peg_accessory = Peg(
                transform=Transform(position=peg_pos_global, orientation=peg_orientation_global),
                size=peg_size,
                shape=peg_parameters.shape,
                forward_length=peg_depth,
                stickout_length=stickout_length
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


# TODO FINISH
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

    require_check(arrangement.check_plane_aligned())

    if arrangement.front_face_on_butt_timber is not None and peg_parameters is not None:
        assert arrangement.front_face_on_butt_timber.to.face() == peg_parameters.tenon_face.to.face(), "if front_face_on_butt_timber is specified, it must match peg tenon face"


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
    shoulder_plane_at_face = measure_mortise_timber_shoulder_plane_from_centerline_towards_tenon_timber(
        arrangement, face_half_size
    )
    inset_plane = measure_into_face(mortise_shoulder_inset, mortise_face, arrangement.receiving_timber)
    inset_marking = mark_plane_from_edge_in_direction(inset_plane, arrangement.receiving_timber, TimberCenterline.CENTERLINE)
    mortise_shoulder_distance_from_centerline = inset_marking.distance

    return cut_mortise_and_tenon_many_options_do_not_call_me_directly_NEWVERSION(
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


# TODO update all calls to cut_mortise_and_tenon_joint_on_FAT
@_deprecated_mortise_tenon
def cut_mortise_and_tenon_joint_on_face_aligned_timbers_DEPRECATED(
    tenon_timber: TimberLike,
    mortise_timber: TimberLike,
    tenon_end: TimberReferenceEnd,
    tenon_size: V2,
    tenon_length: Numeric,
    mortise_depth: Optional[Numeric] = None,
    tenon_position: Optional[V2] = None,
    peg_parameters: Optional[SimplePegParameters] = None,
) -> Joint:
    """
    Creates a mortise and tenon joint with optional pegs.
    
    This is the recommended function for mortise and tenon joints.
    Requires face-aligned and orthogonal timbers.
    
    Args:
        tenon_timber: Timber that will receive the tenon cut
        mortise_timber: Timber that will receive the mortise cut
        tenon_end: Which end of the tenon timber gets the tenon (TOP or BOTTOM)
        tenon_size: Cross-sectional size of tenon (X, Y) in tenon timber's local space
        tenon_length: Length of tenon extending from mortise face
        mortise_depth: Depth of mortise (None = through mortise)
        tenon_position: Offset of tenon center from timber centerline (X, Y) in tenon timber's local space
                       Default is (0, 0) for centered tenon
        peg_parameters: Optional parameters for pegs to secure the joint (SimplePegParameters)
        
    Returns:
        Joint object containing the two CutTimbers and any peg accessories (in global space)
        
    Raises:
        AssertionError: If timbers are not properly oriented for this joint type
        AssertionError: If tenon size + position exceeds timber cross-section bounds
        
    Example:
        >>> # Create a mortise and tenon with 2x2 inch tenon, 3 inches long, with pegs
        >>> joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers_DEPRECATED(
        ...     tenon_timber=vertical_post,
        ...     mortise_timber=horizontal_beam,
        ...     tenon_end=TimberReferenceEnd.TOP,
        ...     tenon_size=Matrix([Rational(2), Rational(2)]),
        ...     tenon_length=Rational(3),
        ...     mortise_depth=Rational(4),  # or None for through mortise
        ...     tenon_position=Matrix([Rational(0), Rational(0)]),  # centered
        ...     peg_parameters=SimplePegParameters(...)  # optional pegs
        ... )
    """
    assert isinstance(tenon_end, TimberReferenceEnd), f"expected TimberReferenceEnd, got {type(tenon_end).__name__}"
    # Default tenon_position to centered (0, 0)
    if tenon_position is None:
        tenon_position = Matrix([Rational(0), Rational(0)])
    
    return cut_mortise_and_tenon_DEPRECATED(
        tenon_timber=tenon_timber,
        mortise_timber=mortise_timber,
        tenon_end=tenon_end,
        tenon_size=tenon_size,
        tenon_length=tenon_length,
        mortise_depth=mortise_depth,
        tenon_position=tenon_position,
        tenon_rotation=Orientation.identity(),
        wedge_parameters=None,
        peg_parameters=peg_parameters
    )


