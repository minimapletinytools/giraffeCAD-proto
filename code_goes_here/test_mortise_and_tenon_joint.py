"""
Tests for mortise and tenon joint construction functions
"""

import pytest
from sympy import Matrix, Rational, simplify
from code_goes_here.moothymoth import Orientation
from code_goes_here.timber import (
    Timber, TimberReferenceEnd, TimberFace, TimberReferenceLongFace,
    V2, V3, Numeric, PegShape, WedgeShape,
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
            length=Rational(6)
        )
        
        assert params.shape == PegShape.ROUND
        assert params.tenon_face == TimberReferenceLongFace.RIGHT
        assert len(params.peg_positions) == 2
        assert params.depth == Rational(4)
        assert params.length == Rational(6)
    
    def test_simple_peg_parameters_with_none_depth(self):
        """Test SimplePegParameters with None depth (through peg)."""
        params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
            peg_positions=[(Rational(2), Rational(0))],
            depth=None,
            length=Rational(8)
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
# Tests for Mortise and Tenon Joint Functions
# ============================================================================

class TestSimpleMortiseAndTenon:
    """Test cut_mortise_and_tenon_joint_on_face_aligned_timbers function."""
    
    def test_cut_mortise_and_tenon_joint_on_face_aligned_timbers_orthogonal_timbers(self):
        """Test simple mortise and tenon with orthogonal face-aligned timbers."""
        # Create a vertical post (tenon timber) extending upward from origin
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 6), position=(0, 0, 0)
        )
        
        # Create a horizontal beam (mortise timber) extending in +X direction
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 8), position=(0, 0, 50)
        )
        
        # Create the joint
        tenon_size = Matrix([Rational(2), Rational(3)])
        tenon_length = Rational(4)
        mortise_depth = Rational(5)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=tenon_size,
            tenon_length=tenon_length,
            mortise_depth=mortise_depth
        )
        
        # Check that joint was created
        assert joint is not None
        assert len(joint.partiallyCutTimbers) == 2
        
        # Check mortise timber has cuts
        mortise_cut_timber = joint.partiallyCutTimbers[0]
        assert mortise_cut_timber.timber == mortise_timber
        assert len(mortise_cut_timber._cuts) == 1
        
        # Check tenon timber has cuts (1 CSG cut that is also an end cut)
        tenon_cut_timber = joint.partiallyCutTimbers[1]
        assert tenon_cut_timber.timber == tenon_timber
        assert len(tenon_cut_timber._cuts) == 1
        
        # Check that the tenon cut is an end cut
        assert tenon_cut_timber._cuts[0].maybe_end_cut == TimberReferenceEnd.TOP
    
    def test_cut_mortise_and_tenon_joint_on_face_aligned_timbers_through_mortise(self):
        """Test simple mortise and tenon with through mortise (depth=None)."""
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='y', length=100, size=(6, 6), position=(0, 0, 60)
        )
        
        # Create the joint with through mortise
        tenon_size = Matrix([Rational(2), Rational(2)])
        tenon_length = Rational(3)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=tenon_size,
            tenon_length=tenon_length,
            mortise_depth=None  # Through mortise
        )
        
        # Check that joint was created successfully
        assert joint is not None
        assert len(joint.partiallyCutTimbers) == 2
        
        # Verify mortise cut exists
        mortise_cut_timber = joint.partiallyCutTimbers[0]
        assert len(mortise_cut_timber._cuts) >= 1
    
    def test_cut_mortise_and_tenon_joint_on_face_aligned_timbers_small_tenon(self):
        """Test simple mortise and tenon with small tenon relative to timber."""
        # Create large timbers
        tenon_timber = create_standard_vertical_timber(
            height=200, size=(10, 10), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=200, size=(12, 12), position=(0, 0, 100)
        )
        
        # Create small tenon
        tenon_size = Matrix([Rational(2), Rational(2)])
        tenon_length = Rational(3)
        mortise_depth = Rational(4)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=tenon_size,
            tenon_length=tenon_length,
            mortise_depth=mortise_depth
        )
        
        assert joint is not None
        assert len(joint.partiallyCutTimbers) == 2
    
    def test_cut_mortise_and_tenon_joint_on_face_aligned_timbers_bottom_end(self):
        """Test simple mortise and tenon on bottom end of tenon timber."""
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 6), position=(0, 0, 50)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 8), position=(0, 0, 50)
        )
        
        # Create joint on bottom end
        tenon_size = Matrix([Rational(2), Rational(3)])
        tenon_length = Rational(4)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.BOTTOM,
            size=tenon_size,
            tenon_length=tenon_length,
            mortise_depth=Rational(5)
        )
        
        # Check that joint was created
        assert joint is not None
        
        # Check that the end cut is on the correct end
        tenon_cut_timber = joint.partiallyCutTimbers[1]
        assert len(tenon_cut_timber._cuts) == 1
        assert tenon_cut_timber._cuts[0].maybe_end_cut == TimberReferenceEnd.BOTTOM


class TestGenericMortiseAndTenon:
    """Test cut_mortise_and_tenon_many_options_do_not_call_me_directly function."""
    
    def test_generic_function_with_defaults(self):
        """Test generic function with default parameters."""
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Call generic function
        tenon_size = Matrix([Rational(2), Rational(2)])
        tenon_length = Rational(3)
        
        joint = cut_mortise_and_tenon_many_options_do_not_call_me_directly(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=tenon_size,
            tenon_length=tenon_length
        )
        
        assert joint is not None
        assert len(joint.partiallyCutTimbers) == 2
        assert len(joint.jointAccessories) == 0
    
    def test_generic_function_accepts_peg_parameters(self):
        """Test that generic function accepts and creates pegs."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Create peg parameters
        peg_params = SimplePegParameters(
            shape=PegShape.ROUND,
            tenon_face=TimberReferenceLongFace.RIGHT,
            peg_positions=[(Rational(1), Rational(0))],
            depth=Rational(4),
            length=Rational(6)
        )
        
        # Should create joint with peg accessories
        joint = cut_mortise_and_tenon_many_options_do_not_call_me_directly(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(3),
            peg_parameters=peg_params
        )
        
        # Verify joint has accessories (pegs)
        assert len(joint.jointAccessories) == 1
        assert joint.jointAccessories[0].shape == PegShape.ROUND
    
    def test_generic_function_rejects_wedge_parameters(self):
        """Test that generic function rejects wedge parameters (not yet supported)."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Create wedge parameters
        wedge_shape = WedgeShape(
            base_width=Rational(1),
            tip_width=Rational(1, 2),
            height=Rational(2),
            length=Rational(3)
        )
        wedge_params = WedgeParameters(
            shape=wedge_shape,
            depth=Rational(3),
            width_axis=create_vector3d(1, 0, 0),
            positions=[Rational(0)]
        )
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Wedge parameters not yet supported"):
            cut_mortise_and_tenon_many_options_do_not_call_me_directly(
                tenon_timber=tenon_timber,
                mortise_timber=mortise_timber,
                tenon_end=TimberReferenceEnd.TOP,
                size=Matrix([Rational(2), Rational(2)]),
                tenon_length=Rational(3),
                wedge_parameters=wedge_params
            )
    
    def test_generic_function_rejects_tenon_rotation(self):
        """Test that generic function rejects non-identity tenon rotation (not yet supported)."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Create non-identity rotation (45 degree rotation around Z axis)
        from sympy import cos, sin, pi
        angle = pi / 4
        rotation_matrix = Matrix([
            [cos(angle), -sin(angle), 0],
            [sin(angle), cos(angle), 0],
            [0, 0, 1]
        ])
        non_identity_rotation = Orientation(rotation_matrix)
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Tenon rotation not yet supported"):
            cut_mortise_and_tenon_many_options_do_not_call_me_directly(
                tenon_timber=tenon_timber,
                mortise_timber=mortise_timber,
                tenon_end=TimberReferenceEnd.TOP,
                size=Matrix([Rational(2), Rational(2)]),
                tenon_length=Rational(3),
                tenon_rotation=non_identity_rotation
            )
    
    def test_generic_function_validates_mortise_depth(self):
        """Test that generic function validates mortise_depth >= tenon_length."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        tenon_length = Rational(5)
        invalid_mortise_depth = Rational(3)  # Less than tenon_length
        
        # Should raise assertion error
        with pytest.raises(AssertionError, match="Mortise depth.*must be >= tenon length"):
            cut_mortise_and_tenon_many_options_do_not_call_me_directly(
                tenon_timber=tenon_timber,
                mortise_timber=mortise_timber,
                tenon_end=TimberReferenceEnd.TOP,
                size=Matrix([Rational(2), Rational(2)]),
                tenon_length=tenon_length,
                mortise_depth=invalid_mortise_depth
            )


class TestMortiseAndTenonEdgeCases:
    """Test edge cases and special configurations."""
    
    def test_mortise_and_tenon_with_exact_mortise_depth(self):
        """Test mortise and tenon where mortise_depth exactly equals tenon_length."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Mortise depth exactly equals tenon length
        tenon_length = Rational(4)
        mortise_depth = Rational(4)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=tenon_length,
            mortise_depth=mortise_depth
        )
        
        assert joint is not None
        assert len(joint.partiallyCutTimbers) == 2
    
    def test_mortise_and_tenon_with_large_tenon(self):
        """Test mortise and tenon with tenon size close to timber size."""
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(6, 6), position=(0, 0, 0)
        )
        
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(8, 8), position=(0, 0, 50)
        )
        
        # Large tenon (almost as big as timber cross-section)
        tenon_size = Matrix([Rational(5), Rational(5)])
        tenon_length = Rational(4)
        
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=tenon_size,
            tenon_length=tenon_length,
            mortise_depth=Rational(5)
        )
        
        assert joint is not None
        assert len(joint.partiallyCutTimbers) == 2


class TestPegAccessories:
    """Tests for peg accessories in mortise and tenon joints."""
    
    def test_peg_orientation_perpendicular_to_tenon_timber(self):
        """Test that pegs are oriented perpendicular to the tenon timber."""
        from code_goes_here.mortise_and_tenon_joint import (
            SimplePegParameters, cut_mortise_and_tenon_joint_on_face_aligned_timbers
        )
        from code_goes_here.timber import PegShape, TimberReferenceLongFace, Peg
        
        # Create a vertical tenon timber (pointing up in +Z)
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        
        # Create a horizontal mortise timber (along +X axis)
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Create peg parameters - peg goes through FORWARD face
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
            peg_positions=[
                (Rational(2), Rational(0))  # 2 units from shoulder, centered
            ],
            depth=Rational(5),
            length=Rational(6)
        )
        
        # Create joint with peg
        joint = cut_mortise_and_tenon_joint_on_face_aligned_timbers(
            tenon_timber=tenon_timber,
            mortise_timber=mortise_timber,
            tenon_end=TimberReferenceEnd.TOP,
            size=Matrix([Rational(2), Rational(2)]),
            tenon_length=Rational(4),
            mortise_depth=Rational(4),
            peg_parameters=peg_params
        )
        
        # Verify joint has accessories
        assert len(joint.jointAccessories) == 1
        
        peg = joint.jointAccessories[0]
        assert isinstance(peg, Peg)
        
        # The tenon timber is vertical (length direction = +Z)
        # The peg goes through the FORWARD face, which means it should be
        # perpendicular to the length direction
        
        # Peg orientation should transform the +Z axis (peg's length direction)
        # to be perpendicular to the tenon timber's length direction
        peg_length_direction_local = peg.orientation.matrix * Matrix([0, 0, 1])
        
        # The tenon timber's length direction is +Z in its local space
        tenon_length_direction_local = Matrix([0, 0, 1])
        
        # Peg should be perpendicular to tenon length direction
        dot_product = peg_length_direction_local.dot(tenon_length_direction_local)
        
        # Dot product should be close to 0 (perpendicular)
        assert abs(float(dot_product)) < 0.001, \
            f"Peg is not perpendicular to tenon timber. Dot product: {float(dot_product)}"
        
        print(f"✓ Peg orientation is perpendicular to tenon timber")
        print(f"  Peg direction (local): {[float(x) for x in peg_length_direction_local]}")
        print(f"  Tenon direction (local): {[float(x) for x in tenon_length_direction_local]}")
        print(f"  Dot product: {float(dot_product)}")
    
    def test_peg_position_is_not_at_origin(self):
        """Test that peg position is not at the origin."""
        from code_goes_here.mortise_and_tenon_joint import (
            SimplePegParameters, cut_mortise_and_tenon_joint_on_face_aligned_timbers
        )
        from code_goes_here.timber import PegShape, TimberReferenceLongFace
        
        # Create timbers
        tenon_timber = create_standard_vertical_timber(
            height=100, size=(4, 4), position=(0, 0, 0)
        )
        mortise_timber = create_standard_horizontal_timber(
            direction='x', length=100, size=(6, 6), position=(0, 0, 50)
        )
        
        # Create peg parameters
        peg_params = SimplePegParameters(
            shape=PegShape.SQUARE,
            tenon_face=TimberReferenceLongFace.FORWARD,
            peg_positions=[(Rational(2), Rational(0))],
            depth=Rational(5),
            length=Rational(6)
        )
        
        # Create joint with peg
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
        
        # Peg position should not be at the origin (it should be somewhere along the tenon)
        peg_position = peg.position
        distance_from_origin = float((peg_position.T * peg_position)[0, 0] ** 0.5)
        
        assert distance_from_origin > 1.0, \
            f"Peg is too close to origin. Distance: {distance_from_origin}"
        
        print(f"✓ Peg position is not at origin")
        print(f"  Peg position (local): {[float(x) for x in peg.position]}")
        print(f"  Distance from origin: {distance_from_origin}")

