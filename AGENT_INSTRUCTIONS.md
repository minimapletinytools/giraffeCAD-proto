# GiraffeCAD Agent Instructions

Copy this file into your project's `.github/copilot-instructions.md` (or `.cursorrules`) to give your AI coding agent context for designing timber frames with GiraffeCAD.

---

## Imports

Always import via the top-level `giraffe` module:
```python
from giraffe import *
```

## Numeric Values

- **Always use SymPy `Rational` — never Python floats.**
- Use the `inches()` and `feet()` helpers for imperial measurements:
  ```python
  inches(3)               # 3 inches
  inches(3, 2)            # 3/2 inches = 1.5"
  feet(Rational(7, 2))    # 3.5 feet
  ```
- Use `Matrix([...])` for vectors, always with `Rational` or `Integer` values.

## Creating Timbers

Use `timber_from_directions` or `create_axis_aligned_timber`:
```python
post = timber_from_directions(
    length=feet(2),
    size=Matrix([inches(4), inches(4)]),
    bottom_position=create_v3(0, 0, 0),
    length_direction=create_v3(0, 0, 1),   # +Z = up
    width_direction=create_v3(1, 0, 0),    # +X = right face
    ticket="post"
)
```

Timber axes:
- **Z** = length direction (bottom → top)
- **+X** = `TimberFace.RIGHT`
- **+Y** = `TimberFace.FRONT`

## Arranging Joints

Use `ButtJointTimberArrangement` to describe which timber has the tenon (`butt_timber`) and which has the mortise (`receiving_timber`):
```python
arrangement = ButtJointTimberArrangement(
    butt_timber=post,
    receiving_timber=beam,
    butt_timber_end=TimberReferenceEnd.TOP,
    front_face_on_butt_timber=TimberLongFace.FRONT,  # required when using pegs
)
```

## Cutting Joints

Prefer the `_on_FAT` (face-aligned and orthogonal) or `_on_PAT` (plane-aligned) variants when timbers are axis-aligned:
```python
joint = cut_mortise_and_tenon_joint_on_FAT(
    arrangement=arrangement,
    tenon_size=Matrix([inches(2), inches(2)]),
    tenon_length=inches(3),
    mortise_depth=inches(7, 2),
)
```

## Pegs

```python
peg_params = SimplePegParameters(
    shape=PegShape.SQUARE,
    peg_positions=[(inches(1), Rational(0))],  # (distance_from_shoulder, lateral_offset)
    size=inches(5, 8),
    depth=inches(4),           # None = full through-mortise
    tenon_hole_offset=inches(1, 16),  # draw-bore offset, typically 1–2mm
)
```

`peg.stickout_length` = `depth / 2` by default.

## Combining into a Frame

Use `Frame.from_joints` to merge cuts on shared timbers across multiple joints:
```python
frame = Frame.from_joints([joint1, joint2, joint3], name="my_frame")
```

## PatternBook (for rendering / export)

Wrap designs in a `PatternBook` for rendering support:
```python
book = PatternBook(patterns=[
    (PatternMetadata("my_frame", ["group", "variant"], "frame"),
     make_pattern_from_frame(my_frame_fn)),
])
frame = book.raise_pattern_group("group", separation_distance=inches(72))
```
