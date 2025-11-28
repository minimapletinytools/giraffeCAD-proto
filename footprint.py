"""
Footprint class for GiraffeCAD - Represents the 2D footprint of a structure
"""

from typing import List, Tuple
from sympy import Matrix

# Type aliases for vectors using sympy
V2 = Matrix  # 2D vector - 2x1 Matrix


class Footprint:
    """A support class representing the footprint of the structure in the XY plane"""
    
    def __init__(self, corners: List[V2]):
        """
        Args:
            corners: List of points defining the corners, last point connects to first
        """
        self.corners: List[V2] = corners
    
    def sides(self) -> List[Tuple[V2, V2]]:
        """
        Returns a list of sides (line segments) connecting consecutive corners.
        
        Returns:
            List of tuples, each containing two points (start, end) representing a side
        """
        result = []
        for i in range(len(self.corners)):
            start = self.corners[i]
            end = self.corners[(i + 1) % len(self.corners)]
            result.append((start, end))
        return result
    
    def is_valid(self) -> bool:
        """
        Checks if the footprint is valid.
        A valid footprint has at least 3 corners and no intersecting sides.
        
        Returns:
            True if valid, False otherwise
        """
        # Check minimum number of corners
        if len(self.corners) < 3:
            return False
        
        # Check for self-intersecting sides
        sides = self.sides()
        n = len(sides)
        
        for i in range(n):
            for j in range(i + 2, n):
                # Don't check adjacent sides (they share a point)
                if j == (i + n - 1) % n:
                    continue
                    
                # Check if side i intersects with side j
                if self._segments_intersect(sides[i], sides[j]):
                    return False
        
        return True
    
    def _segments_intersect(self, seg1: Tuple[V2, V2], seg2: Tuple[V2, V2]) -> bool:
        """
        Check if two line segments intersect (excluding endpoints).
        
        Args:
            seg1: First segment (p1, p2)
            seg2: Second segment (p3, p4)
            
        Returns:
            True if segments intersect, False otherwise
        """
        p1, p2 = seg1
        p3, p4 = seg2
        
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        x3, y3 = p3[0], p3[1]
        x4, y4 = p4[0], p4[1]
        
        # Calculate the direction of the cross products
        def ccw(ax, ay, bx, by, cx, cy):
            return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)
        
        # Check if segments intersect
        return (ccw(x1, y1, x3, y3, x4, y4) != ccw(x2, y2, x3, y3, x4, y4) and
                ccw(x1, y1, x2, y2, x3, y3) != ccw(x1, y1, x2, y2, x4, y4))
    
    def contains_point(self, point: V2) -> bool:
        """
        Check if a point is contained within the footprint boundary using ray casting algorithm.
        
        Args:
            point: 2D point to check
            
        Returns:
            True if point is inside or on the boundary, False otherwise
        """
        x, y = point[0], point[1]
        n = len(self.corners)
        inside = False
        
        p1x, p1y = self.corners[0][0], self.corners[0][1]
        
        for i in range(1, n + 1):
            p2x, p2y = self.corners[i % n][0], self.corners[i % n][1]
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside
    
    def nearest_corner(self, point: V2) -> Tuple[int, V2]:
        """
        Find the nearest corner to a given point.
        
        Args:
            point: 2D point to measure from
            
        Returns:
            Tuple of (index, corner) where index is the corner index and corner is the V2 point
        """
        if not self.corners:
            raise ValueError("Footprint has no corners")
        
        min_distance = None
        nearest_idx = 0
        
        for i, corner in enumerate(self.corners):
            dx = point[0] - corner[0]
            dy = point[1] - corner[1]
            distance = (dx * dx + dy * dy) ** 0.5
            
            if min_distance is None or distance < min_distance:
                min_distance = distance
                nearest_idx = i
        
        return nearest_idx, self.corners[nearest_idx]
    
    def nearest_boundary(self, point: V2) -> Tuple[int, Tuple[V2, V2], float]:
        """
        Find the nearest side (line segment) to a given point.
        
        Args:
            point: 2D point to measure from
            
        Returns:
            Tuple of (index, side, distance) where:
                - index is the side index
                - side is a tuple (start_corner, end_corner)
                - distance is the perpendicular distance to the side
        """
        if len(self.corners) < 2:
            raise ValueError("Footprint must have at least 2 corners")
        
        sides = self.sides()
        min_distance = None
        nearest_idx = 0
        
        px, py = point[0], point[1]
        
        for i, (start, end) in enumerate(sides):
            # Calculate distance from point to line segment
            x1, y1 = start[0], start[1]
            x2, y2 = end[0], end[1]
            
            # Vector from start to end
            dx = x2 - x1
            dy = y2 - y1
            
            # If the segment has zero length, distance is to the point
            if dx == 0 and dy == 0:
                distance = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
            else:
                # Parameter t of the projection of point onto the line
                t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
                
                # Closest point on the segment
                closest_x = x1 + t * dx
                closest_y = y1 + t * dy
                
                # Distance to closest point
                distance = ((px - closest_x) ** 2 + (py - closest_y) ** 2) ** 0.5
            
            if min_distance is None or distance < min_distance:
                min_distance = distance
                nearest_idx = i
        
        return nearest_idx, sides[nearest_idx], min_distance
    
    def get_inward_normal(self, side_index: int) -> Tuple[float, float, float]:
        """
        Get the inward-pointing normal vector for a boundary side.
        
        The inward normal is perpendicular to the boundary side and points toward
        the interior of the footprint.
        
        Args:
            side_index: Index of the boundary side
            
        Returns:
            Tuple of (x, y, z) representing the normalized 3D inward normal vector
        """
        if side_index < 0 or side_index >= len(self.corners):
            raise ValueError(f"Invalid side_index: {side_index}")
        
        # Get the start and end points of the side
        start = self.corners[side_index]
        end = self.corners[(side_index + 1) % len(self.corners)]
        
        # Calculate direction vector along the side
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # Normalize the direction
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-10:
            raise ValueError(f"Side {side_index} has zero length")
        
        dx /= length
        dy /= length
        
        # Calculate perpendicular vector (left perpendicular in 2D)
        # For direction (dx, dy), left perpendicular is (-dy, dx)
        left_perp_x = -dy
        left_perp_y = dx
        
        # Test if this perpendicular points inward by checking if a point
        # slightly offset in this direction is inside the polygon
        midpoint_x = (start[0] + end[0]) / 2
        midpoint_y = (start[1] + end[1]) / 2
        
        # Create a test point offset slightly in the perpendicular direction
        offset = 0.001  # Small offset for testing
        test_x = midpoint_x + left_perp_x * offset
        test_y = midpoint_y + left_perp_y * offset
        
        # Create a test point vector
        test_point = Matrix([test_x, test_y])
        
        # Check if test point is inside
        if self.contains_point(test_point):
            # Left perpendicular points inward
            return (left_perp_x, left_perp_y, 0.0)
        else:
            # Right perpendicular points inward
            return (dy, -dx, 0.0)

