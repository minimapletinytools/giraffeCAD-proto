"""
Prompt log for tinyhouse120.py — tracking all design prompts.
"""

prompts = [
    # ---- Prompt 1: Initial structure ----
    """
lets create a 120 sqft tiny house. the footprint is 15' x 8' with posts on the
INSIDE of the footprint. the FRONT of the house is the 15' side

there are no mudsills, instead there are 4 (on the 15' side) by 3 (on the 8' side) posts.

create size vars for 4x4 and 4x6 these are the nominal dimension of lumber we'll be
using. they are actually 3.5"/5.5"

The posts are 4x4

the 4 corner posts are 11' tall

the non corner posts are 8' tall

connect each post to its neighbor around the perimeter with 4x6 with 6 dimension
pointing in the Z axis since load is in that direction. the bottom of these beams
should be 6" above the ground

at 7' connect the corner posts around the perimeter to each other using a beam

at 11 connect the pair of front corner posts to the back corner posts with a top plate
(sticking out by 6 inches) then 3 inches above this, connect the left and right corner
posts pairs to each other with another top plate. the top plates are 4x6 again with 6
in the +z dimension
""",

    # ---- Prompt 1b: Fix beam orientation ----
    """
all horizontal members should be 4x6 actually... and they should be rotated so that
the 6 dimension is in the Z axis, you have them wrong right now.
""",

    # ---- Prompt 2: Shorten posts, adjust top plates, add mid-wall beams ----
    """
shorten the non corner posts a bit so they dont stick out past the mid beams

lower the L/R top plates a bit so that they sit on top of the F/B top plates and
overlap by 3 inches

then in between the mid plates and floor beams, (right in the middle of each of the
posts) connect a post from the floor beam to the mid plate
""",

    # ---- Prompt 3: Replace horizontal mid-wall with vertical studs, add upper studs ----
    """
remove the horizontal members you added between the main vertical posts. They should
be vertical members instead, between the floor joint and the mid plate.

lastly, between the midplates and the top plates add vertical posts between the 2.
they should be evenly spaced, 2 on the L/R sides and 4 on the F/B sides
""",

    # ---- Prompt 4: King posts, ridge beam, and rafters ----
    """
on the side top plates, add a king post on each end, then have a 16 foot 4x6 ridge
beam on top of the king posts. Will this be strong enough to support the roof?

add 6 sets of rafters on the ridge beam onto the front/back top plates. They should
intersect the beams/plate by about 1 inch, they should start from the very edge of the
beam and be evenly spaced.
""",

    # ---- Prompt 5: Shorten king posts ----
    """
shorten the king post by 6 inches
""",

    # ---- Prompt 6: Extend/raise rafters ----
    """
extend the rafters by 1 foot. they should be higher up on the top plates as well.
right now they intersect entirely, they should be sitting above intersecting by
about just 1 inch
""",

    # ---- Prompt 7: Put extension on eave side ----
    """
good but you extended them on the wrong side, they should extend on the other side
to form eaves
""",

    # ---- Prompt 8: Add ridge support beam/post ----
    """
ok, so yeah I guess the 4x6 ridge beam is'nt strong enough... we will add support
fo it.. create one beam that spans from the middle of the 2 F/B top plats then
create a "king post" from that beam to the ridge beam to support it.
""",

    # ---- Prompt 9: Inset outer rafters and re-space ----
    """
the rafters right now overhang the ends of the ridge beam and top plates. The outer
ones need to be inset inwards by half the dimension of the rafter. Please adjust the
spacing of the rest of the rafters accordingly.
""",

    # ---- Prompt 10: Use join_timbers for center king post ----
    """
instead of creating the center king post axis-aligned directly, use join_timbers
joining the ridge beam and the center support beam.
""",

    # ---- Prompt 11: Add more floor joists ----
    """
now lets create some more floor joists. they run from front to back add 5 of them,
they should line up with the main posts and the inbetween posts. the floor joists
should also be 4x6
""",

    # ---- Prompt 12: Floor joists via join_timbers ----
    """
you got the joints kind of wrong... you need to use join_timbers.

between FM1 and FM2,

then join the middle of beam_front_1/2/3 to the back ones.
""",

    # ---- Prompt 13: Add FM/BM joists ----
    """
still need ones connecting FM1/2 to BM1/2

they should be at the same height as the other joists
""",

    # ---- Prompt 14: Use join_timbers for studs ----
    """
for the various studs, instead of creating the posts directly, use join_timbers.

also no need to validate the number of timbers; I'll do that manually.
""",

    # ---- Prompt 15: Add loft beams at FM/BM intersections ----
    """
next create 2 loft beams that connect the two mid beams together. They should be
positioned right where FM1/2 and BM1/2 intersect the mid beams.
""",
]
