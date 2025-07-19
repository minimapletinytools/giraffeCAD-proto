#!/usr/bin/env python3
"""
Example usage of GiraffeCAD - Timber framing CAD system
"""

import numpy as np
from spatialmath import SE2, SE3
from giraffe import *

def main():
    """Example of creating a simple timber frame structure"""
    
    # Create a rectangular footprint using SE2
    footprint_points = [
        SE2([0.0, 0.0]),    # Bottom left
        SE2([5.0, 0.0]),    # Bottom right  
        SE2([5.0, 3.0]),    # Top right
        SE2([0.0, 3.0])     # Top left
    ]
    footprint = Footprint(footprint_points)
    
    print("Created footprint with 4 corners")
    
    # Create vertical posts at each corner
    posts = []
    for i in range(4):
        post = create_vertical_timber_on_footprint(
            footprint=footprint,
            footprint_index=i,
            length=2.5,  # 2.5m tall
            location_type=TimberLocationType.INSIDE
        )
        posts.append(post)
        print(f"Created post {i+1} at position {post.bottom_position.t}")
    
    # Create horizontal beams connecting the posts
    beams = []
    for i in range(4):
        beam = create_horizontal_timber_on_footprint(
            footprint=footprint,
            footprint_index=i,
            length=5.0 if i % 2 == 0 else 3.0,  # 5m for long sides, 3m for short sides
            location_type=TimberLocationType.CENTER
        )
        beams.append(beam)
        print(f"Created beam {i+1} at position {beam.bottom_position.t}")
    
    # Create a simple mortise and tenon joint between a post and beam
    if posts and beams:
        joint = simple_mortise_and_tenon_joint(
            mortise_timber=posts[0],
            tenon_timber=beams[0],
            tenon_thickness=0.1,  # 10cm thick tenon
            tenon_length=0.2,     # 20cm long tenon
            tenon_depth=0.15      # 15cm deep mortise
        )
        print("Created mortise and tenon joint between post 1 and beam 1")
    
    # Example of joining two timbers with a connecting timber
    if len(posts) >= 2:
        connector = join_timbers(
            timber1=posts[0],
            timber2=posts[1],
            location_on_timber1=1.0,  # 1m from bottom
            symmetric_stickout=0.1,    # 10cm stickout on each side
            offset_from_timber1=0.0   # No offset
        )
        print(f"Created connector timber at position {connector.bottom_position.t}")
    
    print("\nTimber frame structure created successfully!")
    print(f"Total components: {len(posts)} posts, {len(beams)} beams")

if __name__ == "__main__":
    main() 