"""
GiraffeCAD - Timber framing CAD system
Based on the API specification in morenotes.md

This is the main entry point that imports and re-exports all giraffeCAD functionality.
"""

# Import everything from the organized modules
from code_goes_here.timber import *
from code_goes_here.construction import *
from code_goes_here.basic_joints import *
from code_goes_here.mortise_and_tenon_joint import *
from code_goes_here.japanese_joints import *

# Import dimensional helper functions for convenient unit conversion
# and SymPy utilities for exact arithmetic
from code_goes_here.moothymoth import (
    inches, feet, mm, cm, m,
    shaku, sun, bu,
    Rational, S, sympify,
    V2, V3, Direction3D, Numeric,
    create_v2, create_v3,
    normalize_vector, cross_product, vector_magnitude,
    Orientation, Transform
)

# Explicitly import private helper functions that are used by tests
# These start with _ so they won't be included in "import *" by default
from code_goes_here.timber import (
    _create_timber_prism_csg_local
)
