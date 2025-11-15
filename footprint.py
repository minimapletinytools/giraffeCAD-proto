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
    
    def boundaries(self) -> List[Tuple[V2, V2]]:
        """
        Returns a list of boundaries (line segments) connecting consecutive corners.
        
        Returns:
            List of tuples, each containing two points (start, end) representing a boundary
        """
        result = []
        for i in range(len(self.corners)):
            start = self.corners[i]
            end = self.corners[(i + 1) % len(self.corners)]
            result.append((start, end))
        return result
    
    def isValid(self) -> bool:
        """
        Checks if the footprint is valid.
        A valid footprint has at least 3 corners and no intersecting boundaries.
        
        Returns:
            True if valid, False otherwise
        """
        # Check minimum number of corners
        if len(self.corners) < 3:
            return False
        
        # Check for self-intersecting boundaries
        boundaries = self.boundaries()
        n = len(boundaries)
        
        for i in range(n):
            for j in range(i + 2, n):
                # Don't check adjacent boundaries (they share a point)
                if j == (i + n - 1) % n:
                    continue
                    
                # Check if boundary i intersects with boundary j
                if self._segments_intersect(boundaries[i], boundaries[j]):
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
        
        # Convert to float for numerical computation
        x1, y1 = float(p1[0]), float(p1[1])
        x2, y2 = float(p2[0]), float(p2[1])
        x3, y3 = float(p3[0]), float(p3[1])
        x4, y4 = float(p4[0]), float(p4[1])
        
        # Calculate the direction of the cross products
        def ccw(ax, ay, bx, by, cx, cy):
            return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)
        
        # Check if segments intersect
        return (ccw(x1, y1, x3, y3, x4, y4) != ccw(x2, y2, x3, y3, x4, y4) and
                ccw(x1, y1, x2, y2, x3, y3) != ccw(x1, y1, x2, y2, x4, y4))
    
    def containsPoint(self, point: V2) -> bool:
        """
        Check if a point is contained within the footprint boundary using ray casting algorithm.
        
        Args:
            point: 2D point to check
            
        Returns:
            True if point is inside or on the boundary, False otherwise
        """
        x, y = float(point[0]), float(point[1])
        n = len(self.corners)
        inside = False
        
        p1x, p1y = float(self.corners[0][0]), float(self.corners[0][1])
        
        for i in range(1, n + 1):
            p2x, p2y = float(self.corners[i % n][0]), float(self.corners[i % n][1])
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside
    
    def nearestCorner(self, point: V2) -> Tuple[int, V2]:
        """
        Find the nearest corner to a given point.
        
        Args:
            point: 2D point to measure from
            
        Returns:
            Tuple of (index, corner) where index is the corner index and corner is the V2 point
        """
        if not self.corners:
            raise ValueError("Footprint has no corners")
        
        min_distance = float('inf')
        nearest_idx = 0
        
        for i, corner in enumerate(self.corners):
            dx = float(point[0] - corner[0])
            dy = float(point[1] - corner[1])
            distance = (dx * dx + dy * dy) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                nearest_idx = i
        
        return nearest_idx, self.corners[nearest_idx]
    
    def nearestBoundary(self, point: V2) -> Tuple[int, Tuple[V2, V2], float]:
        """
        Find the nearest boundary (line segment) to a given point.
        
        Args:
            point: 2D point to measure from
            
        Returns:
            Tuple of (index, boundary, distance) where:
                - index is the boundary index
                - boundary is a tuple (start_corner, end_corner)
                - distance is the perpendicular distance to the boundary
        """
        if len(self.corners) < 2:
            raise ValueError("Footprint must have at least 2 corners")
        
        boundaries = self.boundaries()
        min_distance = float('inf')
        nearest_idx = 0
        
        px, py = float(point[0]), float(point[1])
        
        for i, (start, end) in enumerate(boundaries):
            # Calculate distance from point to line segment
            x1, y1 = float(start[0]), float(start[1])
            x2, y2 = float(end[0]), float(end[1])
            
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
            
            if distance < min_distance:
                min_distance = distance
                nearest_idx = i
        
        return nearest_idx, boundaries[nearest_idx], min_distance

