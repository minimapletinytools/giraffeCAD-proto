"""
GiraffeCAD - Timber framing CAD system
Based on the API specification in morenotes.md

This is the main entry point that imports and re-exports all giraffeCAD functionality.
"""

# Import everything from the organized modules
from .rule import *
from .cutcsg import *
from .timber import *
from .footprint import *
from .construction import *
from .joints.joint_shavings import *
from .joints.plain_joints import *
from .joints.basic_joints import *
from .joints.mortise_and_tenon_joint import *
from .joints.japanese_joints import *
from .joints.double_butt_joints import *
from .measuring import *
from .patternbook import *
from .triangles import *
from .blueprint import *

# Explicitly import private helper functions that are used by tests
# These start with _ so they won't be included in "import *" by default
from .timber import (
    _create_timber_prism_csg_local
)
