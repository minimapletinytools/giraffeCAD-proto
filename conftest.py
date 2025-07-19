"""
Pytest configuration and shared fixtures for giraffeCAD-proto tests.
"""

import pytest
import numpy as np
from pathlib import Path


@pytest.fixture
def sample_data_dir():
    """Fixture providing path to sample test data directory."""
    return Path(__file__).parent / "tests" / "data"


@pytest.fixture
def tolerance():
    """Fixture providing floating point tolerance for numerical comparisons."""
    return 1e-10


@pytest.fixture
def sample_vectors():
    """Fixture providing common test vectors for 3D operations."""
    return {
        'zero': np.array([0.0, 0.0, 0.0]),
        'unit_x': np.array([1.0, 0.0, 0.0]),
        'unit_y': np.array([0.0, 1.0, 0.0]),
        'unit_z': np.array([0.0, 0.0, 1.0]),
        'arbitrary': np.array([1.5, 2.3, -0.7])
    }


@pytest.fixture
def sample_angles():
    """Fixture providing common test angles in various formats."""
    return {
        'zero': (0.0, 0.0, 0.0),
        'quarter_turn_z': (0.0, 0.0, np.pi/2),
        'quarter_turn_y': (0.0, np.pi/2, 0.0),
        'quarter_turn_x': (np.pi/2, 0.0, 0.0),
        'arbitrary': (0.1, 0.2, 0.3)
    } 