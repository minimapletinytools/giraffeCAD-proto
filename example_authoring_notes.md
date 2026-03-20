
- Japanese joint constructors follow the same repo convention as the other joint modules: accept an arrangement object first, validate with the arrangement check method immediately, then unpack local aliases.
- For splice-style Japanese joints, use `SpliceJointTimberArrangement.front_face_on_timber1` as the visible profile face on timber1; for butt-style Japanese joints, use `ButtJointTimberArrangement.front_face_on_butt_timber`.
- For corner-style Japanese joints like the mitered and keyed lap joint, use `CornerJointTimberArrangement.front_face_on_timber1` as the reference miter face on timber1 and validate with `check_plane_aligned()` before any angle-specific checks.
- When migrating call sites, preserve wrapper convenience APIs if they exist, but update direct pattern usage to construct the arrangement explicitly so orientation choices are visible at the call site.
- For plane-aligned corner joints that are not strictly 90° (e.g., tongue-and-fork corner joint), validate with `CornerJointTimberArrangement.check_plane_aligned()` and separately assert timbers are not parallel.
- For end-cut positioning in corner joints, a robust pattern is: find the entry face on the opposite timber from the approach direction, then cut to the **opposite** face of that timber (`entry_face.get_opposite_face()`).
- For “keep a protrusion, remove cheeks” geometry (tenon/tongue style), use `Difference(base=shoulder_half_space, subtract=[prism])` in timber-local coordinates via `adopt_csg(None, timber.transform, csg_global)`.
- `safe_compare` uses `Comparison.GE` / `Comparison.GT` enum members (not `GTE`), so prefer those constants to avoid runtime enum errors.
