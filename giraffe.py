"""
GiraffeCAD - Timber framing CAD system
Based on the API specification in morenotes.md

This is the main entry point that imports and re-exports all giraffeCAD functionality.
"""

# Import everything from the organized modules
from code_goes_here.rule import *
from code_goes_here.meowmeowcsg import *
from code_goes_here.timber import *
from code_goes_here.footprint import *
from code_goes_here.construction import *
from code_goes_here.joint_shavings import *
from code_goes_here.basic_joints import *
from code_goes_here.mortise_and_tenon_joint import *
from code_goes_here.japanese_joints import *
from code_goes_here.measuring import *
from code_goes_here.patternbook import *

# Explicitly import private helper functions that are used by tests
# These start with _ so they won't be included in "import *" by default
from code_goes_here.timber import (
    _create_timber_prism_csg_local
)
