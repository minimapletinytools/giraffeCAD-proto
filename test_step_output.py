#!/usr/bin/env python3
"""
Manual test script for STEP output.

Usage:
    python test_step_output.py                    # exports oscarshed (default)
    python test_step_output.py horsey             # exports horsey sawhorse
    python test_step_output.py oscarshed          # exports oscarshed

Output goes to step_test_output/ in the current directory.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "patterns" / "structures"))

from code_goes_here.blueprint import export_frame_step, export_cut_timber_step, _OCP_AVAILABLE


def main():
    if not _OCP_AVAILABLE:
        print("ERROR: OCP (cadquery-ocp) is not installed.")
        print("Install with: pip install cadquery-ocp")
        sys.exit(1)

    pattern = sys.argv[1] if len(sys.argv) > 1 else "oscarshed"
    output_dir = Path("step_test_output") / pattern

    print(f"Building frame: {pattern}")
    t0 = time.time()

    if pattern == "horsey":
        from horsey_example import create_sawhorse
        frame = create_sawhorse()
    elif pattern == "oscarshed":
        from oscarshed import create_oscarshed
        frame = create_oscarshed()
    else:
        print(f"Unknown pattern: {pattern}")
        print("Available: oscarshed, horsey")
        sys.exit(1)

    t_build = time.time() - t0
    print(f"  Frame built in {t_build:.2f}s ({len(frame.cut_timbers)} timbers)")

    # Export individual timbers
    print(f"Exporting individual STEP files to {output_dir}/")
    t0 = time.time()
    written = export_frame_step(frame, output_dir, combined=True)
    t_export = time.time() - t0

    print(f"  Exported {len(written)} files in {t_export:.2f}s:")
    for p in written:
        size_kb = p.stat().st_size / 1024
        print(f"    {p.name}  ({size_kb:.1f} KB)")

    # Also export first timber individually as a quick sanity check
    print("\nSingle-timber export test:")
    ct = frame.cut_timbers[0]
    name = ct.timber.ticket.name or "timber_0"
    single_path = output_dir / f"_single_{name}.step"
    t0 = time.time()
    export_cut_timber_step(ct, single_path)
    t_single = time.time() - t0
    size_kb = single_path.stat().st_size / 1024
    print(f"  {single_path.name}  ({size_kb:.1f} KB) in {t_single:.2f}s")

    print("\nDone! Open the .step files in your CAD viewer to verify.")


if __name__ == "__main__":
    main()
