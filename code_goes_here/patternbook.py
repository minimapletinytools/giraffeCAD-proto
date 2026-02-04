"""
PatternBook - Helper structure for generating and organizing example patterns

This module provides a convenient way to organize multiple patterns (frames or CSG objects)
and raise them at different positions for visualization and testing.
"""

from sympy import Rational
from typing import List, Tuple, Optional, Callable, Union, Literal
from dataclasses import dataclass, field
from .moothymoth import V3, create_v3
from .timber import Frame, CutTimber
from .meowmeowcsg import MeowMeowCSG


# Type alias for pattern functions
PatternLambda = Callable[[V3], Union[Frame, MeowMeowCSG]]


@dataclass(frozen=True)
class PatternMetadata:
    """
    Metadata describing a pattern in the pattern book.
    
    Attributes:
        pattern_name: Unique name for this pattern
        pattern_group_names: List of group names to organize related patterns
        pattern_type: Type of pattern - either 'frame' or 'csg'
    """
    pattern_name: str
    pattern_group_names: List[str] = field(default_factory=list)
    pattern_type: Literal['frame', 'csg'] = 'frame'
    
    def __post_init__(self):
        """Validate pattern type."""
        if self.pattern_type not in ['frame', 'csg']:
            raise ValueError(f"pattern_type must be 'frame' or 'csg', got: {self.pattern_type}")


@dataclass
class PatternBook:
    """
    A collection of patterns with functions to raise them at different positions.
    
    Patterns can be either Frame objects or MeowMeowCSG objects, and can be organized
    into groups for batch visualization with spacing.
    
    Attributes:
        patterns: List of (PatternMetadata, PatternLambda) pairs
    """
    patterns: List[Tuple[PatternMetadata, PatternLambda]] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate pattern names are unique."""
        names = [metadata.pattern_name for metadata, _ in self.patterns]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate pattern names found: {set(duplicates)}")
    
    def raise_pattern(self, pattern_name: str, center: Optional[V3] = None) -> Union[Frame, MeowMeowCSG]:
        """
        Raise a single pattern by name at the specified center location.
        
        Args:
            pattern_name: Name of the pattern to raise
            center: Center location for the pattern (default: origin)
            
        Returns:
            Frame or MeowMeowCSG object at the specified location
            
        Raises:
            ValueError: If pattern_name is not found
        """
        if center is None:
            center = create_v3(0, 0, 0)
        
        # Find the pattern by name
        for metadata, pattern_lambda in self.patterns:
            if metadata.pattern_name == pattern_name:
                return pattern_lambda(center)
        
        # Pattern not found
        available_names = [m.pattern_name for m, _ in self.patterns]
        raise ValueError(f"Pattern '{pattern_name}' not found. Available patterns: {available_names}")
    
    def raise_pattern_group(
        self, 
        group_name: str, 
        separation_distance: Union[float, int, Rational],
        start_center: Optional[V3] = None
    ) -> Union[Frame, List[MeowMeowCSG]]:
        """
        Raise all patterns in a group, separated by the specified distance along the X-axis.
        
        For frame patterns: Breaks apart individual frames and builds a megaframe from all of them.
        For CSG patterns: Returns a list of CSG objects.
        
        Args:
            group_name: Name of the group to raise
            separation_distance: Distance between pattern centers along X-axis
            start_center: Starting center location (default: origin)
            
        Returns:
            For frame patterns: A single Frame containing all cut timbers from all patterns
            For CSG patterns: A list of MeowMeowCSG objects
            
        Raises:
            ValueError: If group_name is not found or if frame and CSG patterns are mixed
        """
        if start_center is None:
            start_center = create_v3(0, 0, 0)
        
        # Convert separation_distance to Rational
        if not isinstance(separation_distance, Rational):
            separation_distance = Rational(separation_distance)
        
        # Find all patterns in the group (check if group_name is in pattern_group_names list)
        group_patterns = [
            (metadata, pattern_lambda) 
            for metadata, pattern_lambda in self.patterns 
            if group_name in metadata.pattern_group_names
        ]
        
        if not group_patterns:
            available_groups = self.list_groups()
            raise ValueError(f"Group '{group_name}' not found. Available groups: {available_groups}")
        
        # Check that all patterns in the group have the same type
        pattern_types = set(metadata.pattern_type for metadata, _ in group_patterns)
        if len(pattern_types) > 1:
            raise ValueError(
                f"Cannot mix frame and CSG patterns in the same group. "
                f"Group '{group_name}' contains types: {pattern_types}"
            )
        
        pattern_type = list(pattern_types)[0]
        
        # Raise all patterns with appropriate spacing
        results = []
        for i, (metadata, pattern_lambda) in enumerate(group_patterns):
            # Calculate center position for this pattern
            offset = create_v3(i * separation_distance, 0, 0)
            center = start_center + offset
            
            # Raise the pattern
            result = pattern_lambda(center)
            results.append(result)
        
        # Process results based on pattern type
        if pattern_type == 'frame':
            # Combine all frames into a megaframe
            return self._combine_frames(results, group_name)
        else:  # pattern_type == 'csg'
            # Return list of CSG objects
            return results
    
    def _combine_frames(self, frames: List[Frame], group_name: str) -> Frame:
        """
        Combine multiple Frame objects into a single megaframe.
        
        Extracts all cut_timbers and accessories from all frames and combines them
        into a single Frame object.
        
        Args:
            frames: List of Frame objects to combine
            group_name: Name for the combined frame
            
        Returns:
            A single Frame containing all cut timbers and accessories
        """
        all_cut_timbers = []
        all_accessories = []
        
        for frame in frames:
            all_cut_timbers.extend(frame.cut_timbers)
            all_accessories.extend(frame.accessories)
        
        # Create megaframe
        megaframe = Frame(
            cut_timbers=all_cut_timbers,
            accessories=all_accessories,
            name=f"{group_name}_combined"
        )
        
        return megaframe
    
    def list_patterns(self) -> List[str]:
        """
        List all pattern names in the book.
        
        Returns:
            List of pattern names
        """
        return [metadata.pattern_name for metadata, _ in self.patterns]
    
    def list_groups(self) -> List[str]:
        """
        List all unique group names in the book.
        
        Returns:
            List of group names (flattened from all patterns)
        """
        groups = set()
        for metadata, _ in self.patterns:
            groups.update(metadata.pattern_group_names)
        return sorted(list(groups))
    
    def get_patterns_in_group(self, group_name: str) -> List[str]:
        """
        Get all pattern names in a specific group.
        
        Args:
            group_name: Name of the group
            
        Returns:
            List of pattern names in the group
        """
        return [
            metadata.pattern_name 
            for metadata, _ in self.patterns 
            if group_name in metadata.pattern_group_names
        ]
