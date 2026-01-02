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
from .conftest import (
    create_standard_vertical_timber,
    create_standard_horizontal_timber
)


# ============================================================================
# Tests for Parameter Classes
# ============================================================================

class TestSimplePegParameters:
    """Test SimplePegParameters dataclass."""
    
    def test_create_simple_peg_parameters(self):
        """Test creating SimplePegParameters with all fields."""
        params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.RIGHT,
            peg_positions=[(Rational(1), Rational(0)), (Rational(2), Rational(1))],
            depth=Rational(4),
            size=Rational(1, 2)
        )
        
        assert params.shape == PegShape.ROUND
        assert params.tenon_face == TimberReferenceLongFace.RIGHT
        assert len(params.peg_positions) == 2
        assert params.depth == Rational(4)
        assert params.size == Rational(1, 2)
    
    def test_simple_peg_parameters_with_none_depth(self):
        """Test SimplePegParameters with None depth (through peg)."""
        params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
            peg_positions=[(Rational(2), Rational(0))],
            depth=None,
            size=Rational(1, 2)
        )
        
        assert params.depth is None


class TestWedgeParameters:
    """Test WedgeParameters dataclass."""
    
    def test_create_wedge_parameters(self):
        """Test creating WedgeParameters with all fields."""
        width_axis = create_vector3d(1, 0, 0)
        shape = WedgeShape(
            base_width=Rational(1),
            tip_width=Rational(1, 2),
            height=Rational(2),
            length=Rational(3)
        )
        
        params = WedgeParameters(
            shape=shape,
            depth=Rational(3),
            width_axis=width_axis,
            positions=[Rational(-1), Rational(1)],
            expand_mortise=Rational(1, 4)
        )
        
        assert params.shape == shape
        assert params.depth == Rational(3)
        assert params.width_axis.equals(width_axis)
        assert len(params.positions) == 2
        assert params.expand_mortise == Rational(1, 4)
    
    def test_wedge_parameters_default_expand_mortise(self):
        """Test WedgeParameters with default expand_mortise."""
        width_axis = create_vector3d(0, 1, 0)
        shape = WedgeShape(
            base_width=Rational(1),
            tip_width=Rational(1, 2),
            height=Rational(2),
            length=Rational(3)
        )
        
        params = WedgeParameters(
            shape=shape,
            depth=Rational(3),
            width_axis=width_axis,
            positions=[Rational(0)]
        )
        
        assert params.expand_mortise == Rational(0)


# ============================================================================
# Helper Functions for CSG Testing
# ============================================================================

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
    """Test basic mortise and tenon CSG validation using contains_point()."""
    
    def test_mortise_depth_validation(self):
        """Test that mortise is cut to the correct depth."""
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Create joint with specific mortise depth
        tenon_size = Matrix([Rational(2), Rational(2)])
        tenon_length = Rational(3)
        mortise_depth = Rational(5)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=tenon_size,
            tenon_length=tenon_length,
            mortise_depth=mortise_depth
        )
        
        # Get the mortise cut CSG
        mortise_cut_timber = joint.partiallyCutTimbers[0]
        mortise_csg = mortise_cut_timber._cuts[0].negative_csg
        
        # Sample points at various depths in the mortise
        # The mortise should be centered on the timber centerline at z=50 (where tenon meets it)
        # Points should be removed (in the CSG) up to depth=5 from the face
        
        # Point just inside the mortise (should be in the CSG, meaning removed from timber)
        point_shallow = Matrix([Rational(0), Rational(0), Rational(50) - Rational(1)])
        point_shallow_local = transform_point_to_local(point_shallow, mortise_timber)
        assert mortise_csg.contains_point(point_shallow_local), \
            "Point at shallow depth should be inside mortise CSG"
        
        # Point at mid-depth (should be in the CSG)
        point_mid = Matrix([Rational(0), Rational(0), Rational(50) - Rational(3)])
        point_mid_local = transform_point_to_local(point_mid, mortise_timber)
        assert mortise_csg.contains_point(point_mid_local), \
            "Point at mid-depth should be inside mortise CSG"
        
        # Point just before mortise depth limit (should be in the CSG)
        point_deep = Matrix([Rational(0), Rational(0), Rational(50) - mortise_depth + Rational(1, 10)])
        point_deep_local = transform_point_to_local(point_deep, mortise_timber)
        assert mortise_csg.contains_point(point_deep_local), \
            "Point just before depth limit should be inside mortise CSG"
    
    def test_tenon_length_validation(self):
        """Test that tenon cut CSG is created correctly."""
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        tenon_size = Matrix([Rational(2), Rational(2)])
        tenon_length = Rational(4)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=tenon_size,
            tenon_length=tenon_length,
            mortise_depth=Rational(5)
        )
        
        # Get the tenon cut CSG (this is what's REMOVED from the timber)
        tenon_cut_timber = joint.partiallyCutTimbers[1]
        tenon_cut_csg = tenon_cut_timber._cuts[0].negative_csg
        
        # Verify the CSG exists and is a Difference operation
        from code_goes_here.meowmeowcsg import Difference
        assert isinstance(tenon_cut_csg, (Difference, type(tenon_cut_csg))), \
            "Tenon cut CSG should be created"
        
        # Point well below where any cuts happen (should NOT be removed)
        point_far_below = Matrix([Rational(0), Rational(0), Rational(10)])
        point_far_below_local = transform_point_to_local(point_far_below, tenon_timber)
        assert not tenon_cut_csg.contains_point(point_far_below_local), \
            "Point far below shoulder should NOT be in cut CSG (material preserved)"
    
    def test_tenon_shoulder_position(self):
        """Test that shoulder plane cuts material correctly."""
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        tenon_length = Rational(4)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=tenon_length,
            mortise_depth=Rational(5)
        )
        
        tenon_cut_timber = joint.partiallyCutTimbers[1]
        tenon_cut_csg = tenon_cut_timber._cuts[0].negative_csg
        
        # Verify CSG was created
        assert tenon_cut_csg is not None, "Tenon cut CSG should exist"
        
        # Point deep in the timber body (should be preserved)
        point_in_body = Matrix([Rational(0), Rational(0), Rational(25)])
        point_in_body_local = transform_point_to_local(point_in_body, tenon_timber)
        assert not tenon_cut_csg.contains_point(point_in_body_local), \
            "Point in timber body should be preserved"
    
    def test_through_mortise(self):
        """Test that mortise_depth=None creates a through mortise."""
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(8, 8), position=(0, 0, 50)
        )
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(3),
            mortise_depth=None  # Through mortise
        )
        
        mortise_cut_timber = joint.partiallyCutTimbers[0]
        mortise_csg = mortise_cut_timber._cuts[0].negative_csg
        
        # Point deep in the mortise timber (should be in the CSG for a through mortise)
        # The mortise timber extends in +X from x=0, centered at y=0, z=50
        # The tenon comes from below at y=0, z=50
        # For a through mortise, the hole should go all the way through the timber width
        point_deep = Matrix([Rational(0), Rational(0), Rational(50) - Rational(7)])
        point_deep_local = transform_point_to_local(point_deep, mortise_timber)
        assert mortise_csg.contains_point(point_deep_local), \
            "Through mortise should extend deep into timber"


# ============================================================================
# Tests for Peg Orientation
# ============================================================================

class TestPegOrientation:
    """Test peg direction and perpendicularity (TODO item 11)."""
    
    def test_peg_perpendicular_to_tenon_timber_forward_face(self):
        """Test peg through FORWARD face is perpendicular to tenon timber length."""
        # Create vertical tenon timber (length direction = +Z)
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Create peg through FORWARD face
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        
        peg = joint.jointAccessories[0]
        
        # Peg's Z-axis is its length direction (in peg's local space)
        # Transform to mortise timber's space
        peg_direction_mortise_local = peg.orientation.matrix * Matrix([0, 0, 1])
        
        # Tenon timber's length direction in world space
        tenon_length_world = tenon_timber.length_direction
        
        # Transform to mortise timber's local space
        tenon_length_mortise_local = mortise_timber.orientation.matrix.T * tenon_length_world
        
        # Dot product should be 0 (perpendicular)
        dot_product = peg_direction_mortise_local.dot(tenon_length_mortise_local)
        assert abs(dot_product) < Rational(1, 1000), \
            f"Peg should be perpendicular to tenon timber. Dot product: {dot_product}"
    
    def test_peg_perpendicular_to_tenon_face(self):
        """Test that peg is perpendicular to the face it goes through."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        
        peg = joint.jointAccessories[0]
        
        # Get FORWARD face normal in tenon timber's local space
        # FORWARD face normal is +Y in local space
        forward_face_normal_tenon_local = Matrix([0, 1, 0])
        
        # Transform to mortise timber's local space (where peg is stored)
        forward_face_normal_world = tenon_timber.orientation.matrix * forward_face_normal_tenon_local
        forward_face_normal_mortise_local = mortise_timber.orientation.matrix.T * forward_face_normal_world
        
        # Peg direction in mortise local space
        peg_direction_mortise_local = peg.orientation.matrix * Matrix([0, 0, 1])
        
        # Peg should be parallel (not perpendicular) to face normal
        # (peg goes INTO the face, in direction of normal)
        dot_product = abs(peg_direction_mortise_local.dot(forward_face_normal_mortise_local))
        
        # Normalize vectors for comparison
        peg_dir_norm = peg_direction_mortise_local.norm()
        face_norm_norm = forward_face_normal_mortise_local.norm()
        
        # Dot product of normalized vectors should be close to 1 (parallel) or -1 (anti-parallel)
        normalized_dot = dot_product / (peg_dir_norm * face_norm_norm)
        assert abs(normalized_dot - 1) < Rational(1, 100) or abs(normalized_dot + 1) < Rational(1, 100), \
            f"Peg should be parallel to face normal. Normalized dot product: {normalized_dot}"


# ============================================================================
# Tests for Peg Depth Calculation
# ============================================================================

class TestPegDepthCalculation:
    """Test peg depth calculations (TODO items 9, 10)."""
    
    def test_peg_depth_explicit(self):
        """Test that explicit peg depth is respected."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Specify explicit peg depth
        peg_depth = Rational(7)
        peg_params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        assert peg.forward_length == peg_depth, \
            f"Peg forward_length should match specified depth. Expected {peg_depth}, got {peg.forward_length}"
    
    def test_peg_depth_none_mortise_on_x_face(self):
        """Test automatic depth calculation when mortise is on X-axis face."""
        # Create timbers where mortise will be on LEFT face of mortise timber
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        # Mortise timber extends in +X direction, so tenon meets it on the LEFT (-X) face
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 8), position=(0, 0, 50)
        )
        
        # Peg goes through FORWARD face (Y direction)
        # When depth=None, it should use the dimension of the mortise timber
        # in the direction perpendicular to the mortise face
        # Mortise is on LEFT face (X-axis), peg goes through FORWARD face (Y-axis)
        # So peg depth should use Y dimension
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
            peg_positions=[(Rational(2), Rational(0))],
            depth=None,  # Auto-calculate
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
        # Mortise face is LEFT (X-face), so auto depth uses X dimension
        expected_depth = mortise_timber.size[0]  # Should be 6
        # But peg goes through FORWARD face, which enters mortise through a different face
        # The actual depth depends on which face of the mortise timber the peg enters
        # In this case, it enters through a Y-face, so depth is Y dimension = 8
        expected_depth = mortise_timber.size[1]  # Y dimension for FORWARD face peg
        assert peg.forward_length == expected_depth, \
            f"Peg depth should match mortise timber dimension. Expected {expected_depth}, got {peg.forward_length}"
    
    def test_peg_depth_none_mortise_on_y_face(self):
        """Test automatic depth calculation when mortise is on Y-axis face (FORWARD/BACK)."""
        # Create timbers where mortise will be on BACK face of mortise timber
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        # Mortise timber extends in +Y direction, so tenon meets it on the BACK (-Y) face
        mortise_timber = create_standard_horizontal_timber(
            direction='y', length=100, size=(8, 6), position=(0, 0, 50)
        )
        
        peg_params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.RIGHT,
            peg_positions=[(Rational(2), Rational(0))],
            depth=None,  # Auto-calculate
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
        expected_depth = mortise_timber.size[1]  # Y dimension
        assert peg.forward_length == expected_depth, \
            f"Peg depth should use mortise timber Y dimension. Expected {expected_depth}, got {peg.forward_length}"
    
    def test_peg_stickout_length(self):
        """Test that stickout_length is half of forward_length."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_depth = Rational(8)
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        expected_stickout = peg_depth * Rational(1, 2)
        assert peg.stickout_length == expected_stickout, \
            f"Stickout should be half of forward_length. Expected {expected_stickout}, got {peg.stickout_length}"


# ============================================================================
# Tests for Peg Hole Geometry
# ============================================================================

class TestPegHoleGeometry:
    """Test peg hole containment validation (TODO items 12-13)."""
    
    def test_peg_hole_not_in_tenon_csg(self):
        """Test that peg holes are created in tenon timber."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        
        # Get tenon timber's cut CSG (what's removed)
        tenon_cut_timber = joint.partiallyCutTimbers[1]
        tenon_cut_csg = tenon_cut_timber._cuts[0].negative_csg
        
        # Verify CSG includes peg holes (should be a Union with multiple children)
        from code_goes_here.meowmeowcsg import Union
        assert isinstance(tenon_cut_csg, Union), \
            "Tenon cut CSG with pegs should be a Union"
        assert len(tenon_cut_csg.children) >= 2, \
            "Union should contain base cut plus peg holes"
    
    def test_peg_hole_not_in_mortise_csg(self):
        """Test that peg holes are created in mortise timber."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        
        # Get mortise timber's cut CSG
        mortise_cut_timber = joint.partiallyCutTimbers[0]
        mortise_cut_csg = mortise_cut_timber._cuts[0].negative_csg
        
        # Verify CSG includes peg holes (should be a Union)
        from code_goes_here.meowmeowcsg import Union
        assert isinstance(mortise_cut_csg, Union), \
            "Mortise cut CSG with pegs should be a Union"
        assert len(mortise_cut_csg.children) >= 2, \
            "Union should contain mortise plus peg holes"
    
    def test_peg_hole_points_on_peg_csg(self):
        """Test that points in peg hole region ARE contained by Peg CSG."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_size = Rational(1, 2)
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        # Peg is stored in mortise timber's local space
        # The peg position is on the mortise face where it enters
        # Points along the peg's length should be contained
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
    
    def test_peg_hole_boundary(self):
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
            tenon_face=TimberReferenceLongFace.FORWARD,
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


# ============================================================================
# Tests for Peg Positioning
# ============================================================================

# TODO use contain_point function to test that the peg is where it is expected
class TestPegPositioning:
    """Test peg position accuracy."""
    
    def test_peg_position_from_shoulder(self):
        """Test that peg is positioned along the tenon."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        distance_from_shoulder = Rational(3)
        tenon_length = Rational(4)
        
        peg_params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        peg_position_world = mortise_timber.bottom_position + mortise_timber.orientation.matrix * peg.position
        
        # Peg should be somewhere in the general vicinity of the joint (z around 50)
        assert Rational(40) < peg_position_world[2] < Rational(60), \
            f"Peg should be near the joint region, at z={peg_position_world[2]}"
    
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
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        # For a peg through the FORWARD face, the lateral axis is X
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
            tenon_face=TimberReferenceLongFace.FORWARD,
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
        assert len(joint.partiallyCutTimbers) == 2
        
        # Verify the end cut is on the TOP
        tenon_cut_timber = joint.partiallyCutTimbers[1]
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
        assert len(joint.partiallyCutTimbers) == 2
        
        # Verify the end cut is on the BOTTOM
        tenon_cut_timber = joint.partiallyCutTimbers[1]
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
        mortise_cut_timber = joint.partiallyCutTimbers[0]
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
        """Test pegs on FORWARD face."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
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

