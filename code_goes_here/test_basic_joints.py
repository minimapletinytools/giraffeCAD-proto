"""
Tests for GiraffeCAD timber framing system
"""

import pytest
from sympy import Matrix, sqrt, simplify, Abs, Float, Rational, pi
from giraffe import *
from giraffe import _has_rational_components, _are_directions_perpendicular, _are_directions_parallel, _are_timbers_face_parallel, _are_timbers_face_orthogonal, _are_timbers_face_aligned
from .conftest import (
    create_standard_vertical_timber,
    create_standard_horizontal_timber,
    create_centered_horizontal_timber,
    assert_is_valid_rotation_matrix,
    assert_vectors_perpendicular,
    TimberGeometryHelpers
)



# ============================================================================
# Tests for basic_joints.py - Joint Construction Functions
# ============================================================================

class TestMiterJoint:
    """Test cut_basic_miter_joint function."""

    @staticmethod
    def assert_miter_joint_normals_are_opposite(joint, timberA, timberB):
        """
        Helper function to assert that miter joint cut normals are opposite in global space.
        
        Args:
            joint: The joint result from cut_basic_miter_joint_on_face_aligned_timbers
            timberA: First timber in the joint
            timberB: Second timber in the joint
        """
        # Get the local normals from the cuts
        normal_A_local = joint.cut_timbers[0]._cuts[0].half_plane.normal
        normal_B_local = joint.cut_timbers[1]._cuts[0].half_plane.normal
        
        # Convert to global coordinates
        normal_A_global = timberA.local_direction_to_global(normal_A_local)
        normal_B_global = timberB.local_direction_to_global(normal_B_local)
        
        # For a miter joint, the normals should be opposite in global space
        assert normal_A_global.equals(-normal_B_global), "Normals should be opposite in global space"
    
    @staticmethod
    def assert_miter_joint_end_positions_on_boundaries(joint, timberA, timberB):
        """
        Helper function to assert that the end positions of both cut timbers are on the 
        boundaries of both half planes.
        
        For a miter joint, the end position where timber A is cut should lie on the boundary
        of both timber A's cut plane and timber B's cut plane (and vice versa).
        
        Args:
            joint: The joint result from cut_basic_miter_joint_on_face_aligned_timbers
            timberA: First timber in the joint
            timberB: Second timber in the joint
        """
        # Get the end position of the cut on timberA (in global coordinates)
        end_position_A_global = timberA.get_centerline_position_from_bottom(-3)
        
        # Get the end position of the cut on timberB (in global coordinates)
        end_position_B_global = timberB.get_centerline_position_from_bottom(-3)
        
        # see that end_position_A_global is NOT in cut timberA but is in cut timberB
        assert not joint.cut_timbers[0].render_timber_with_cuts_csg_local().contains_point(timberA.global_to_local(end_position_A_global))
        assert joint.cut_timbers[1].render_timber_with_cuts_csg_local().contains_point(timberB.global_to_local(end_position_A_global))
        # see that end_position_B_global is NOT in cut timberB but is in cut timberA
        assert not joint.cut_timbers[1].render_timber_with_cuts_csg_local().contains_point(timberB.global_to_local(end_position_B_global))
        assert joint.cut_timbers[0].render_timber_with_cuts_csg_local().contains_point(timberA.global_to_local(end_position_B_global))


    @staticmethod
    def get_timber_bottom_position_after_cutting_local(timber: CutTimber) -> V3:
        prism = timber._extended_timber_without_cuts_csg_local()
        assert isinstance(prism, Prism)
        return prism.get_bottom_position()

    def test_basic_miter_joint_on_orthoganal_timbers(self):
        """Test basic miter joint on face-aligned timbers."""
        # Create two orthognal timbers meeting at the origin
        timberA = create_standard_horizontal_timber(direction='x', length=100, size=(6, 6), position=(0, 0, 0))
        timberB = create_standard_horizontal_timber(direction='y', length=100, size=(6, 6), position=(0, 0, 0))
        
        # Create miter joint
        joint = cut_basic_miter_joint_on_face_aligned_timbers(timberA, TimberReferenceEnd.BOTTOM, timberB, TimberReferenceEnd.BOTTOM)

        # check very basic stuff
        assert joint is not None
        assert len(joint.cut_timbers) == 2
        assert joint.cut_timbers[0].timber == timberA
        assert joint.cut_timbers[0]._cuts[0].maybe_end_cut == TimberReferenceEnd.BOTTOM
        assert joint.cut_timbers[1].timber == timberB
        assert joint.cut_timbers[1]._cuts[0].maybe_end_cut == TimberReferenceEnd.BOTTOM

        # check that the two cuts are half plane cuts and the planes are opposite
        assert isinstance(joint.cut_timbers[0]._cuts[0], HalfPlaneCut)
        assert isinstance(joint.cut_timbers[1]._cuts[0], HalfPlaneCut)

        # Convert normals to global space and check if they are opposite
        self.assert_miter_joint_normals_are_opposite(joint, timberA, timberB)

        # Check that the end positions of both cut timbers are on the boundaries of both half planes
        self.assert_miter_joint_end_positions_on_boundaries(joint, timberA, timberB)

        # check that the "corner" point of the miter is contained on the boundary of both half plane
        corner_point_global = create_vector3d(Rational(-3), Rational(-3), Rational(0))
        corner_point_local_A = timberA.global_to_local(corner_point_global)
        corner_point_local_B = timberB.global_to_local(corner_point_global)
        assert joint.cut_timbers[0]._cuts[0].half_plane.is_point_on_boundary(corner_point_local_A)
        assert joint.cut_timbers[1]._cuts[0].half_plane.is_point_on_boundary(corner_point_local_B)

        # check that the "bottom" point of timberA (after cutting) is contained in timberB but not timber A
        # This point is at (0, -3, 0) in global coordinates, which is:
        # - On the "cut away" side of timber A (should NOT be contained)
        # - On the "kept" side of timber B (should be contained)
        bottom_point_A_after_cutting_global = create_vector3d(Rational(0), Rational(-3), Rational(0))
        bottom_point_A_after_cutting_local_A = timberA.global_to_local(bottom_point_A_after_cutting_global)
        bottom_point_A_after_cutting_local_B = timberB.global_to_local(bottom_point_A_after_cutting_global)
        assert not joint.cut_timbers[0]._cuts[0].half_plane.contains_point(bottom_point_A_after_cutting_local_A)
        assert joint.cut_timbers[1]._cuts[0].half_plane.contains_point(bottom_point_A_after_cutting_local_B)

    def test_basic_miter_joint_on_various_angles(self): 
        """Test miter joints with timbers at 90-degree angle in various orientations."""
        # Note: cut_basic_miter_joint_on_face_aligned_timbers requires perpendicular timbers (90-degree angle)
        # We test various orientations of perpendicular timber pairs
        
        test_cases = [
            # (timberA_direction, timberB_direction, description)
            ('x', 'y', 'X and Y perpendicular'),
            ('x', '-y', 'X and -Y perpendicular'),
            ('-x', 'y', '-X and Y perpendicular'),
            ('-x', '-y', '-X and -Y perpendicular'),
        ]
        
        for dirA, dirB, description in test_cases:
            # Create timberA and timberB in perpendicular directions
            timberA = create_standard_horizontal_timber(direction=dirA, length=100, size=(6, 6), position=(0, 0, 0))
            timberB = create_standard_horizontal_timber(direction=dirB, length=100, size=(6, 6), position=(0, 0, 0))
            
            # Create miter joint
            joint = cut_basic_miter_joint_on_face_aligned_timbers(timberA, TimberReferenceEnd.BOTTOM, timberB, TimberReferenceEnd.BOTTOM)
            
            # Verify the joint was created
            assert joint is not None, f"Failed to create joint for {description}"
            assert len(joint.cut_timbers) == 2
            
            # Verify the cuts are half plane cuts
            assert isinstance(joint.cut_timbers[0]._cuts[0], HalfPlaneCut)
            assert isinstance(joint.cut_timbers[1]._cuts[0], HalfPlaneCut)
            
            # Verify normals are opposite in global space
            self.assert_miter_joint_normals_are_opposite(joint, timberA, timberB)
            
            # Verify end positions are on boundaries of both half planes
            self.assert_miter_joint_end_positions_on_boundaries(joint, timberA, timberB)

    def test_basic_miter_joint_on_parallel_timbers(self):
        """Test that creating miter joint between parallel timbers raises an error."""
        # Create three timbers: two parallel (+X) and one anti-parallel (-X)
        timberA = create_standard_horizontal_timber(direction='x', length=100, size=(6, 6), position=(0, 0, 0))
        timberB = create_standard_horizontal_timber(direction='x', length=100, size=(6, 6), position=(0, 0, 0))
        timberC = create_standard_horizontal_timber(direction='-x', length=100, size=(6, 6), position=(0, 0, 0))
        
        # Attempting to create a miter joint between parallel timbers should raise an AssertionError
        # because the function requires perpendicular timbers
        with pytest.raises(AssertionError, match="perpendicular"):
            cut_basic_miter_joint_on_face_aligned_timbers(timberA, TimberReferenceEnd.BOTTOM, timberB, TimberReferenceEnd.BOTTOM)
        
        # Test with anti-parallel timbers as well
        with pytest.raises(AssertionError, match="perpendicular"):
            cut_basic_miter_joint_on_face_aligned_timbers(timberA, TimberReferenceEnd.BOTTOM, timberC, TimberReferenceEnd.BOTTOM)


        

class TestButtJoint:
    """Test cut_basic_butt_joint_on_face_aligned_timbers function."""

    def test_basic_butt_joint_on_face_aligned_timbers(self):
        """Test butt joint between two perpendicular timbers."""
        # Create two perpendicular timbers meeting at the origin
        # timberA extends along +X (bottom at origin, top at x=100)
        # timberB extends along +Y (bottom at origin, top at y=100)
        timberA = create_standard_horizontal_timber(direction='x', length=100, size=(6, 6), position=(0, 0, 0))
        timberB = create_standard_horizontal_timber(direction='y', length=100, size=(6, 6), position=(0, 0, 0))

        # Create butt joint - timberB butts into timberA at timberB's BOTTOM end
        joint = cut_basic_butt_joint_on_face_aligned_timbers(timberA, timberB, TimberReferenceEnd.BOTTOM)

        # Verify joint structure
        assert joint is not None
        assert len(joint.cut_timbers) == 2
        assert joint.cut_timbers[0].timber == timberA
        assert joint.cut_timbers[1].timber == timberB

        # In a butt joint, the receiving timber (timberA) should have no cuts
        assert len(joint.cut_timbers[0]._cuts) == 0, "Receiving timber should have no cuts"

        # The butt timber (timberB) should have exactly one cut at the specified end
        assert len(joint.cut_timbers[1]._cuts) == 1, "Butt timber should have one cut"
        assert joint.cut_timbers[1]._cuts[0].maybe_end_cut == TimberReferenceEnd.BOTTOM

        # Verify the cut is a half plane cut
        assert isinstance(joint.cut_timbers[1]._cuts[0], HalfPlaneCut)

        # Verify that the cut normal in global space is parallel or anti-parallel to timberB's length direction
        # For an end cut (butt joint), the cut plane is perpendicular to the timber's length axis,
        # so the normal is parallel/anti-parallel to the length direction
        cut_normal_local = joint.cut_timbers[1]._cuts[0].half_plane.normal
        cut_normal_global = timberB.local_direction_to_global(cut_normal_local)
        
        dot_with_length = (cut_normal_global.T * timberB.length_direction)[0, 0]
        from sympy import simplify, Abs
        assert simplify(Abs(dot_with_length)) == 1, \
            "Cut normal should be parallel or anti-parallel to butt timber's length direction"
        
        # Verify the cut creates a valid CSG geometry
        # (this is a basic sanity check that the cut can be rendered)
        try:
            csg = joint.cut_timbers[1].render_timber_with_cuts_csg_local()
            assert csg is not None, "Should be able to render the cut timber"
        except Exception as e:
            pytest.fail(f"Failed to render cut timber: {e}")

        # TODO enable after fixing nearest_point_on_face_to_point_global
        # TODO not sure if it should be FRONT or BACK face
        # test that the point on the face of timberA where the butt meets is on the boundary of timberB after cutting
        #nearest_point_on_face_to_point_global = TimberGeometryHelpers.nearest_point_on_face_to_point_global(timberA, TimberFace.BACK, create_vector3d(Rational(0), Rational(0), Rational(0)))
        #nearest_point_on_face_to_point_local = timberB.global_to_local(nearest_point_on_face_to_point_global)
        #assert joint.cut_timbers[1].render_timber_with_cuts_csg_local().contains_point(nearest_point_on_face_to_point_local)




    def test_basic_butt_joint_on_parallel_timbers(self):
        """Test that creating butt joint between parallel timbers raises an error.
        
        The cut_basic_butt_joint_on_face_aligned_timbers function validates that timbers
        are not parallel, as butt joints require timbers at an angle.
        """
        # Create three timbers: two parallel (+X) and one anti-parallel (-X)
        timberA = create_standard_horizontal_timber(direction='x', length=100, size=(6, 6), position=(0, 0, 0))
        timberB = create_standard_horizontal_timber(direction='x', length=100, size=(6, 6), position=(0, 0, 0))
        timberC = create_standard_horizontal_timber(direction='-x', length=100, size=(6, 6), position=(0, 0, 0))
        
        # Attempting to create a butt joint between parallel timbers should raise an AssertionError
        # because the function requires perpendicular timbers
        with pytest.raises(AssertionError, match="parallel"):
            cut_basic_butt_joint_on_face_aligned_timbers(timberA, timberB, TimberReferenceEnd.BOTTOM)
        
        # Test with anti-parallel timbers as well
        with pytest.raises(AssertionError, match="parallel"):
            cut_basic_butt_joint_on_face_aligned_timbers(timberA, timberC, TimberReferenceEnd.BOTTOM)


class TestSpliceJoint:
    """Test cut_basic_splice_joint_on_aligned_timbers function."""
    
    def test_basic_splice_joint_same_orientation(self):
        """Test basic splice joint with two aligned timbers with same orientation."""
        # Create two timbers aligned along the X axis
        # TimberA extends from x=0 to x=50
        timberA = create_standard_horizontal_timber(direction='x', length=50, size=(6, 6), position=(0, 0, 0))
        # TimberB extends from x=50 to x=100 (meeting at x=50)
        timberB = create_standard_horizontal_timber(direction='x', length=50, size=(6, 6), position=(50, 0, 0))
        
        # Create splice joint at x=50 (where they meet)
        # TimberA TOP meets TimberB BOTTOM
        joint = cut_basic_splice_joint_on_aligned_timbers(
            timberA, TimberReferenceEnd.TOP, 
            timberB, TimberReferenceEnd.BOTTOM
        )
        
        # Verify joint structure
        assert joint is not None
        assert len(joint.cut_timbers) == 2
        
        cutA = joint.cut_timbers[0]._cuts[0]
        cutB = joint.cut_timbers[1]._cuts[0]
        
        # Verify both cuts are end cuts
        assert cutA.maybe_end_cut == TimberReferenceEnd.TOP
        assert cutB.maybe_end_cut == TimberReferenceEnd.BOTTOM
        
        # Verify both cuts have the same origin (the splice point)
        assert cutA.origin[0] == cutB.origin[0]
        assert cutA.origin[1] == cutB.origin[1]
        assert cutA.origin[2] == cutB.origin[2]
        
        # The origin should be at (50, 0, 0) - the midpoint
        assert cutA.origin[0] == Rational(50)
        assert cutA.origin[1] == Rational(0)
        assert cutA.origin[2] == Rational(0)
        
        # Verify the cut planes are perpendicular to the timber axis (X axis)
        # In global coordinates, the plane normal should be ±(1, 0, 0)
        global_normalA = timberA.orientation.matrix * cutA.half_plane.normal
        global_normalB = timberB.orientation.matrix * cutB.half_plane.normal
        
        # For aligned timbers with same orientation:
        # - TimberA: cut at TOP, normal points +X (away from timber body)
        # - TimberB: cut at BOTTOM, normal points -X (away from timber body)
        # So they should be opposite
        assert simplify(global_normalA + global_normalB).norm() == 0, \
            f"Normals should be opposite! A={global_normalA.T}, B={global_normalB.T}"
        
    def test_splice_joint_with_custom_point(self):
        """Test splice joint with explicitly specified splice point."""
        # Create two timbers along Z axis
        timberA = create_standard_vertical_timber(height=100, size=(4, 4), position=(0, 0, 0))
        timberB = create_standard_vertical_timber(height=100, size=(4, 4), position=(0, 0, 100))
        
        # Specify splice point at z=120 (not the midpoint)
        splice_point = Matrix([Rational(0), Rational(0), Rational(120)])
        
        joint = cut_basic_splice_joint_on_aligned_timbers(
            timberA, TimberReferenceEnd.TOP,
            timberB, TimberReferenceEnd.BOTTOM,
            splice_point
        )
        
        # Verify the splice occurred at the specified point
        cutA = joint.cut_timbers[0]._cuts[0]
        
        assert cutA.origin[0] == Rational(0)
        assert cutA.origin[1] == Rational(0)
        assert cutA.origin[2] == Rational(120)
        
    def test_splice_joint_opposite_orientation(self):
        """Test splice joint with two aligned timbers with opposite orientations."""
        # TimberA points in +X direction
        timberA = timber_from_directions(
            length=Rational(60),
            size=Matrix([Rational(6), Rational(6)]),
            bottom_position=Matrix([Rational(0), Rational(0), Rational(0)]),
            length_direction=Matrix([Rational(1), Rational(0), Rational(0)]),
            width_direction=Matrix([Rational(0), Rational(1), Rational(0)])
        )
        
        # TimberB points in -X direction (opposite orientation)
        # Bottom is at x=100, top at x=40
        timberB = timber_from_directions(
            length=Rational(60),
            size=Matrix([Rational(6), Rational(6)]),
            bottom_position=Matrix([Rational(100), Rational(0), Rational(0)]),
            length_direction=Matrix([Rational(-1), Rational(0), Rational(0)]),
            width_direction=Matrix([Rational(0), Rational(1), Rational(0)])
        )
        
        # Create splice joint (should meet in the middle at x=50)
        joint = cut_basic_splice_joint_on_aligned_timbers(
            timberA, TimberReferenceEnd.TOP,
            timberB, TimberReferenceEnd.TOP
        )
        
        assert joint is not None
        assert len(joint.cut_timbers) == 2
        
        # Verify the splice point is between the two timbers
        cutA = joint.cut_timbers[0]._cuts[0]
        
        # Should be at the midpoint between x=60 and x=40 = x=50
        assert cutA.origin[0] == Rational(50)
        
    def test_splice_joint_non_aligned_timbers_raises_error(self):
        """Test that non-aligned (non-parallel) timbers raise a ValueError."""
        # Create two perpendicular timbers
        timberA = timber_from_directions(
            length=Rational(50),
            size=Matrix([Rational(4), Rational(4)]),
            bottom_position=Matrix([Rational(0), Rational(0), Rational(0)]),
            length_direction=Matrix([Rational(1), Rational(0), Rational(0)]),
            width_direction=Matrix([Rational(0), Rational(1), Rational(0)])
        )
        
        timberB = timber_from_directions(
            length=Rational(50),
            size=Matrix([Rational(4), Rational(4)]),
            bottom_position=Matrix([Rational(50), Rational(0), Rational(0)]),
            length_direction=Matrix([Rational(0), Rational(1), Rational(0)]),  # Perpendicular!
            width_direction=Matrix([Rational(1), Rational(0), Rational(0)])
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="must have parallel length axes"):
            cut_basic_splice_joint_on_aligned_timbers(
                timberA, TimberReferenceEnd.TOP,
                timberB, TimberReferenceEnd.BOTTOM
            )


class TestHouseJoint:
    """Test cut_basic_house_joint function."""
    
    def test_basic_house_joint_perpendicular_timbers(self):
        """Test that a house joint between two perpendicular timbers is created correctly."""


        # create 2 timbers in an X shape
        housing_timber = create_centered_horizontal_timber(direction='x', length=100, size=(10, 10), zoffset=1)
        housed_timber = create_centered_horizontal_timber(direction='y', length=100, size=(10, 10), zoffset=-1)

        joint = cut_basic_house_joint(housing_timber, housed_timber)
        assert joint is not None
        assert len(joint.cut_timbers) == 2
        assert joint.cut_timbers[0].timber == housing_timber
        assert joint.cut_timbers[1].timber == housed_timber

        assert len(joint.cut_timbers[0]._cuts) == 1
        assert len(joint.cut_timbers[1]._cuts) == 0
        
        assert joint.cut_timbers[0]._cuts[0].maybe_end_cut is None

        # test that the origin point lies in the housed timber but not the housing timber
        origin = create_vector3d(Rational(0), Rational(0), Rational(0))
        assert not joint.cut_timbers[0].render_timber_with_cuts_csg_local().contains_point(housing_timber.global_to_local(origin))
        assert joint.cut_timbers[1].render_timber_with_cuts_csg_local().contains_point(housed_timber.global_to_local(origin))
        


    def test_house_joint_prism_matches_housed_timber_global_space(self):
        """
        Test that the prism being cut from the housing timber matches the housed timber
        when both are compared in global coordinates.
        """
        from code_goes_here.meowmeowcsg import Prism
        
        # Create housing timber (vertical post)
        housing_timber = create_standard_vertical_timber(height=200, size=(10, 10), position=(0, 0, 0))
        
        # Create housed timber (horizontal beam intersecting the post)
        housed_timber = timber_from_directions(
            length=Rational(80),
            size=Matrix([Rational(6), Rational(6)]),  # 6 x 6 beam
            bottom_position=Matrix([Rational(-20), Rational(0), Rational(100)]),
            length_direction=Matrix([Rational(1), Rational(0), Rational(0)]),  # Horizontal
            width_direction=Matrix([Rational(0), Rational(1), Rational(0)])
        )
        
        # Create the housed joint
        # Explicitly specify opposing faces: housing.FRONT (+Y) vs housed.LEFT (-Y)
        joint = cut_basic_house_joint(
            housing_timber, housed_timber,
            housing_timber_cut_face=TimberFace.FRONT,
            housed_timber_cut_face=TimberFace.LEFT
        )
        
        # Get the housing timber with its cut
        housing_cut_timber = joint.cut_timbers[0]
        cut = housing_cut_timber._cuts[0]
        
        assert isinstance(cut, CSGCut), "Cut should be a CSGCut"
        
        # Get the negative CSG (the prism being cut away)
        # This is in the housing timber's LOCAL coordinate system
        # Note: The new implementation uses a Difference(Prism, HalfPlane) for the cross lap joint
        from code_goes_here.meowmeowcsg import Difference
        cut_csg_local = cut.negative_csg
        assert isinstance(cut_csg_local, Difference), "Negative CSG should be a Difference (cross lap implementation)"
        
        # Extract the base prism from the Difference
        cut_prism_local = cut_csg_local.base
        assert isinstance(cut_prism_local, Prism), "Base of Difference should be a Prism"
        
        # ===================================================================
        # Compare the cut prism with the housed timber in GLOBAL space
        # ===================================================================
        
        # 1. The prism's size should match the housed timber's size
        assert cut_prism_local.size[0] == housed_timber.size[0], \
            f"Cut prism width should match housed timber width: {cut_prism_local.size[0]} vs {housed_timber.size[0]}"
        assert cut_prism_local.size[1] == housed_timber.size[1], \
            f"Cut prism height should match housed timber height: {cut_prism_local.size[1]} vs {housed_timber.size[1]}"
        
        # 2. Check the prism's orientation in global space
        # cut_prism_local.orientation is relative to housing timber's local frame
        # Global orientation = housing_orientation * local_orientation
        cut_prism_global_orientation = housing_timber.orientation.multiply(cut_prism_local.orientation)
        
        # The prism's orientation should match the housed timber's orientation
        # (they should be aligned in the same direction)
        orientation_diff = cut_prism_global_orientation.matrix - housed_timber.orientation.matrix
        orientation_diff_norm = simplify(orientation_diff.norm())
        
        assert orientation_diff_norm == 0, \
            f"Cut prism orientation should exactly match housed timber orientation in global space. Difference: {orientation_diff_norm}"
        
        # 3. Check that the prism extends along the housed timber's length direction
        # The prism's length direction (in housing timber's local coords) should match
        # the housed timber's length direction (also in housing timber's local coords)
        
        housed_length_dir_in_housing_local = housing_timber.orientation.matrix.T * housed_timber.length_direction
        prism_length_dir_in_housing_local = cut_prism_local.orientation.matrix[:, 2]  # Z-axis of prism
        
        # These should be parallel (same or opposite direction)
        dot = simplify((housed_length_dir_in_housing_local.T * prism_length_dir_in_housing_local)[0, 0])
        assert abs(dot) == 1, \
            f"Cut prism length direction should be exactly parallel to housed timber length direction. Dot product: {dot}"
    


class TestCrossLapJoint:
    """Test cut_basic_house_joint function."""
    
    def test_basic_cross_lap_joint_perpendicular_timbers(self):
        """Test that a cross lap joint between two perpendicular timbers is created correctly."""


        # create 2 timbers in an X shape
        timberA = create_centered_horizontal_timber(direction='x', length=100, size=(10, 10), zoffset=1)
        timberB = create_centered_horizontal_timber(direction='y', length=100, size=(10, 10), zoffset=-1)

        joint = cut_basic_cross_lap_joint(timberA, timberB)

        assert joint is not None
        assert len(joint.cut_timbers) == 2
        assert joint.cut_timbers[0].timber == timberA
        assert joint.cut_timbers[1].timber == timberB
        assert len(joint.cut_timbers[0]._cuts) == 1
        assert len(joint.cut_timbers[1]._cuts) == 1
        assert joint.cut_timbers[0]._cuts[0].maybe_end_cut is None
        assert joint.cut_timbers[1]._cuts[0].maybe_end_cut is None

        # test that the origin point lies on the boundary of both timbers
        origin = create_vector3d(Rational(0), Rational(0), Rational(0))
        assert joint.cut_timbers[0].render_timber_with_cuts_csg_local().contains_point(timberA.global_to_local(origin))
        assert joint.cut_timbers[1].render_timber_with_cuts_csg_local().contains_point(timberB.global_to_local(origin))

        # TODO enable this when you fix is_point_on_boundary
        #assert joint.cut_timbers[0].render_timber_with_cuts_csg_local().is_point_on_boundary(timberA.global_to_local(origin))
        #assert joint.cut_timbers[1].render_timber_with_cuts_csg_local().is_point_on_boundary(timberB.global_to_local(origin))

        # above origin
        origin = create_vector3d(Rational(0), Rational(0), Rational(1))
        assert joint.cut_timbers[0].render_timber_with_cuts_csg_local().contains_point(timberA.global_to_local(origin))
        assert not joint.cut_timbers[1].render_timber_with_cuts_csg_local().contains_point(timberB.global_to_local(origin))

        # below origin
        origin = create_vector3d(Rational(0), Rational(0), Rational(-1))
        assert not joint.cut_timbers[0].render_timber_with_cuts_csg_local().contains_point(timberA.global_to_local(origin))
        assert joint.cut_timbers[1].render_timber_with_cuts_csg_local().contains_point(timberB.global_to_local(origin))
        
