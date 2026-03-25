---
applyTo: "patterns/**, experiments/**"
---

<!-- The content below is kept in sync with AGENT_INSTRUCTIONS.md. If you edit one, edit the other. -->

# GiraffeCAD Agent Instructions

Copy this file into your project's `.github/copilot-instructions.md` (or `.cursorrules`) to give your AI coding agent context for designing timber frames with GiraffeCAD.

---

## Imports

Always import via the top-level `giraffe` module:
```python
from giraffe import *
```

## Numeric Values

- **Always use SymPy types (Rational or Float) — never Python floats.**
- Use the `inches()` and `feet()` helpers for imperial measurements:
  ```python
  inches(3)               # 3 inches
  inches(3, 2)            # 3/2 inches = 1.5"
  feet(Rational(7, 2))    # 3.5 feet
  ```
- Use `mm()`, `cm()` and `m()` for metric
- Use `degrees()` and `radians()` for angles
- Use `Matrix([...])` for vectors, always with `Rational` or `Integer` values.

## Philosophy

TODO point to docs

## Creating Timbers

Timbers for a typical structure are usually defined 

- first create a `Footprint` for the footprint of the structure.
- use methods in `footprint.py` to define timbers on the footprint
    - ... TODO
- use methods in `construction.py` to define remaining timbers
    - ... TODO
    - `create_axis_aligned_timber` for timbers aligned to cartesian axis
    - `timber_from_directions` for arbitrarily aligned timbers

TODO point to example

## Cutting Joints

TODO 

TODO always use joints for basic_joints which provide sensible default parameters if no specifics about the joint were provided

## Combining everything into a Frame

Use `Frame.from_joints` to merge cuts on shared timbers across multiple joints:
```python
frame = Frame.from_joints([joint1, joint2, joint3], name="my_frame")
```

TODO how to actually return the frame for rendering (not through a pattern)

## Creating new Patterns

