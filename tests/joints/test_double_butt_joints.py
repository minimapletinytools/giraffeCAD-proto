"""
Tests for double butt joint construction functions.
"""

import pytest
from sympy import Rational
from giraffe import *
from code_goes_here.example_shavings import create_canonical_example_opposing_double_butt_joint_timbers


class TestSplinedOpposingDoubleButtJoint:
    """Test cut_splined_opposing_double_butt_joint function."""

    def test_arrangement_validation(self):
        """Canonical arrangement passes the cardinal-and-opposing-butts check."""
        arrangement = create_canonical_example_opposing_double_butt_joint_timbers()
        assert arrangement.check_face_aligned_cardinal_and_opposing_butts() is None

    def test_stub_raises_not_implemented(self):
        """Stubbed function raises NotImplementedError after passing validation."""
        arrangement = create_canonical_example_opposing_double_butt_joint_timbers()
        with pytest.raises(NotImplementedError):
            cut_splined_opposing_double_butt_joint(arrangement)
