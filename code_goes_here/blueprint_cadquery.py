"""
GiraffeCAD - Blueprint export module (STL and STEP)

Exports CutTimber and Frame objects to standard CAD interchange formats.

STL export uses trimesh (triangle mesh). STEP export uses cadquery/OCP
(OpenCascade) to produce exact B-rep geometry.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Union

from .cutcsg import (
    ConvexPolygonExtrusion,
    CutCSG,
    Cylinder,
    Difference,
    HalfSpace,
    RectangularPrism,
    SolidUnion,
    adopt_csg,
)
from .rule import Transform
from .rendering_utils import sympy_to_float
from .timber import CutTimber, Frame

try:
    import numpy as np
    import trimesh

    _TRIMESH_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]
    trimesh = None  # type: ignore[assignment]
    _TRIMESH_AVAILABLE = False

try:
    import cadquery as cq  # type: ignore[import-untyped]

    _CADQUERY_AVAILABLE = True
except ImportError:
    cq = None  # type: ignore[assignment]
    _CADQUERY_AVAILABLE = False


# ---------------------------------------------------------------------------
# STL export
# ---------------------------------------------------------------------------


def _cut_timber_to_trimesh(cut_timber: CutTimber) -> "trimesh.Trimesh":
    """Return a trimesh in global coordinates for a single CutTimber."""
    from .triangles import triangulate_cutcsg

    local_csg = cut_timber.render_timber_with_cuts_csg_local()
    global_csg = adopt_csg(cut_timber.timber.transform, Transform.identity(), local_csg)
    return triangulate_cutcsg(global_csg).mesh


def export_cut_timber_stl(cut_timber: CutTimber, filepath: Union[str, Path]) -> None:
    """Export a single CutTimber to an STL file (global coordinates, metres).

    Args:
        cut_timber: The timber (with cuts applied) to export.
        filepath: Destination path. Parent directories are created if needed.
    """
    if not _TRIMESH_AVAILABLE:
        raise ImportError(
            "trimesh and numpy are required for STL export. "
            "Install them with: pip install trimesh numpy"
        )
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    mesh = _cut_timber_to_trimesh(cut_timber)
    mesh.export(str(filepath), file_type="stl")


def export_frame_stl(
    frame: Frame,
    output_dir: Union[str, Path],
    *,
    combined: bool = False,
) -> List[Path]:
    """Export every timber in a Frame to STL files.

    Args:
        frame: The frame to export.
        output_dir: Directory for the STL files.
        combined: If True, also write a single ``_combined.stl`` with all
            timbers merged into one mesh.

    Returns:
        List of paths written.
    """
    if not _TRIMESH_AVAILABLE:
        raise ImportError(
            "trimesh and numpy are required for STL export. "
            "Install them with: pip install trimesh numpy"
        )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    meshes: list[trimesh.Trimesh] = []
    for i, ct in enumerate(frame.cut_timbers):
        name = ct.timber.ticket.name or f"timber_{i}"
        mesh = _cut_timber_to_trimesh(ct)
        meshes.append(mesh)
        dest = output_dir / f"{name}.stl"
        mesh.export(str(dest), file_type="stl")
        written.append(dest)

    if combined and meshes:
        merged = trimesh.util.concatenate(meshes)
        dest = output_dir / "_combined.stl"
        merged.export(str(dest), file_type="stl")
        written.append(dest)

    return written


# ---------------------------------------------------------------------------
# STEP export helpers
# ---------------------------------------------------------------------------

# GiraffeCAD uses metres; cadquery/OCP/STEP uses millimetres
_M_TO_MM = 1000.0
_STEP_HALF_SPACE_EXTENT = 10_000.0  # mm — large box stand-in for HalfSpace


def _to_mm(val) -> float:
    """Convert a SymPy linear value (in metres) to float millimetres."""
    return sympy_to_float(val) * _M_TO_MM


def _csg_to_cadquery(csg: CutCSG) -> "cq.Workplane":
    """Recursively convert a CutCSG tree (in global coords) to a cadquery solid."""
    import sys
    try:
        if isinstance(csg, RectangularPrism):
            return _prism_to_cq(csg)
        if isinstance(csg, Cylinder):
            return _cylinder_to_cq(csg)
        if isinstance(csg, ConvexPolygonExtrusion):
            return _extrusion_to_cq(csg)
        if isinstance(csg, HalfSpace):
            return _halfspace_to_cq(csg)
        if isinstance(csg, SolidUnion):
            return _union_to_cq(csg)
        if isinstance(csg, Difference):
            return _difference_to_cq(csg)
        raise TypeError(f"Unsupported CutCSG type for STEP export: {type(csg).__name__}")
    except Exception as exc:
        print(
            f"[blueprint] STEP error in {type(csg).__name__}: {exc}",
            file=sys.stderr, flush=True,
        )
        if isinstance(csg, (RectangularPrism, ConvexPolygonExtrusion)):
            m = csg.transform.orientation.matrix
            p = csg.transform.position
            print(
                f"[blueprint]   transform matrix:\n"
                f"    [{float(m[0,0]):.15f}, {float(m[0,1]):.15f}, {float(m[0,2]):.15f}]\n"
                f"    [{float(m[1,0]):.15f}, {float(m[1,1]):.15f}, {float(m[1,2]):.15f}]\n"
                f"    [{float(m[2,0]):.15f}, {float(m[2,1]):.15f}, {float(m[2,2]):.15f}]\n"
                f"    position: [{float(p[0])}, {float(p[1])}, {float(p[2])}]",
                file=sys.stderr, flush=True,
            )
        if isinstance(csg, Cylinder):
            print(
                f"[blueprint]   axis: [{float(csg.axis_direction[0])}, {float(csg.axis_direction[1])}, {float(csg.axis_direction[2])}]"
                f"  pos: [{float(csg.position[0])}, {float(csg.position[1])}, {float(csg.position[2])}]",
                file=sys.stderr, flush=True,
            )
        if isinstance(csg, HalfSpace):
            print(
                f"[blueprint]   normal: [{float(csg.normal[0])}, {float(csg.normal[1])}, {float(csg.normal[2])}]"
                f"  offset: {float(csg.offset)}",
                file=sys.stderr, flush=True,
            )
        raise


def _rotation_matrix_from_z_to_dir(dx: float, dy: float, dz: float) -> list[list[float]]:
    """Build an orthogonal 3x3 rotation matrix that maps +Z to (dx, dy, dz)."""
    import math
    import numpy as _np
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    if norm < 1e-12:
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    dx, dy, dz = dx / norm, dy / norm, dz / norm
    # new_z = target direction
    new_z = _np.array([dx, dy, dz])
    # pick an arbitrary vector not parallel to new_z for cross product
    if abs(dx) < 0.9:
        ref = _np.array([1.0, 0.0, 0.0])
    else:
        ref = _np.array([0.0, 1.0, 0.0])
    new_x = _np.cross(ref, new_z)
    new_x /= _np.linalg.norm(new_x)
    new_y = _np.cross(new_z, new_x)
    rot = _np.column_stack([new_x, new_y, new_z])
    return _orthogonalize_rotation(rot.tolist())


def _apply_rotation_and_translation(wp: "cq.Workplane", rot: list[list[float]], tx: float, ty: float, tz: float) -> "cq.Workplane":
    """Apply an orthogonalized rotation + translation to a workplane solid via gp_Trsf."""
    from OCP.gp import gp_Trsf, gp_Mat, gp_XYZ  # type: ignore[import-untyped]
    trsf = gp_Trsf()
    mat = gp_Mat(
        rot[0][0], rot[0][1], rot[0][2],
        rot[1][0], rot[1][1], rot[1][2],
        rot[2][0], rot[2][1], rot[2][2],
    )
    trsf.SetValues(
        mat.Value(1, 1), mat.Value(1, 2), mat.Value(1, 3), tx,
        mat.Value(2, 1), mat.Value(2, 2), mat.Value(2, 3), ty,
        mat.Value(3, 1), mat.Value(3, 2), mat.Value(3, 3), tz,
    )
    moved_shape = wp.val().moved(cq.Location(trsf))
    return cq.Workplane("XY").newObject([moved_shape])


def _orthogonalize_rotation(rot: list[list[float]]) -> list[list[float]]:
    """Re-orthogonalize a 3x3 rotation matrix via SVD to satisfy OpenCascade."""
    import numpy as _np
    u, _, vt = _np.linalg.svd(_np.array(rot, dtype=float))
    r = u @ vt
    # Ensure proper rotation (det = +1), not reflection
    if _np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    return r.tolist()


def _transform_workplane(wp: "cq.Workplane", transform: Transform) -> "cq.Workplane":
    """Apply a GiraffeCAD Transform to a cadquery Workplane via gp_Trsf."""
    m = transform.orientation.matrix
    p = transform.position
    rot = [
        [sympy_to_float(m[0, 0]), sympy_to_float(m[0, 1]), sympy_to_float(m[0, 2])],
        [sympy_to_float(m[1, 0]), sympy_to_float(m[1, 1]), sympy_to_float(m[1, 2])],
        [sympy_to_float(m[2, 0]), sympy_to_float(m[2, 1]), sympy_to_float(m[2, 2])],
    ]
    rot = _orthogonalize_rotation(rot)
    px, py, pz = _to_mm(p[0]), _to_mm(p[1]), _to_mm(p[2])
    return _apply_rotation_and_translation(wp, rot, px, py, pz)


def _prism_to_cq(prism: RectangularPrism) -> "cq.Workplane":
    w = _to_mm(prism.size[0])
    h = _to_mm(prism.size[1])
    start = _to_mm(prism.start_distance) if prism.start_distance is not None else -_STEP_HALF_SPACE_EXTENT
    end = _to_mm(prism.end_distance) if prism.end_distance is not None else _STEP_HALF_SPACE_EXTENT
    length = end - start

    box = cq.Workplane("XY").box(w, h, length, centered=(True, True, False)).translate((0, 0, start))
    return _transform_workplane(box, prism.transform)


def _cylinder_to_cq(cyl: Cylinder) -> "cq.Workplane":
    r = _to_mm(cyl.radius)
    start = _to_mm(cyl.start_distance) if cyl.start_distance is not None else -_STEP_HALF_SPACE_EXTENT
    end = _to_mm(cyl.end_distance) if cyl.end_distance is not None else _STEP_HALF_SPACE_EXTENT
    length = end - start

    wp = cq.Workplane("XY").circle(r).extrude(length).translate((0, 0, start))

    ax = sympy_to_float(cyl.axis_direction[0])
    ay = sympy_to_float(cyl.axis_direction[1])
    az = sympy_to_float(cyl.axis_direction[2])
    px = _to_mm(cyl.position[0])
    py = _to_mm(cyl.position[1])
    pz = _to_mm(cyl.position[2])

    rot = _rotation_matrix_from_z_to_dir(ax, ay, az)
    return _apply_rotation_and_translation(wp, rot, px, py, pz)


def _extrusion_to_cq(ext: ConvexPolygonExtrusion) -> "cq.Workplane":
    pts = [(_to_mm(p[0]), _to_mm(p[1])) for p in ext.points]
    start = _to_mm(ext.start_distance) if ext.start_distance is not None else -_STEP_HALF_SPACE_EXTENT
    end = _to_mm(ext.end_distance) if ext.end_distance is not None else _STEP_HALF_SPACE_EXTENT
    length = end - start

    wp = cq.Workplane("XY").workplane(offset=start).polyline(pts).close().extrude(length)
    return _transform_workplane(wp, ext.transform)


def _halfspace_to_cq(hs: HalfSpace) -> "cq.Workplane":
    """Approximate a HalfSpace as a very large box on the 'kept' side."""
    import math

    nx = sympy_to_float(hs.normal[0])
    ny = sympy_to_float(hs.normal[1])
    nz = sympy_to_float(hs.normal[2])
    offset = _to_mm(hs.offset)
    norm = math.sqrt(nx * nx + ny * ny + nz * nz)
    if norm < 1e-12:
        raise ValueError("HalfSpace normal is zero")
    nx, ny, nz = nx / norm, ny / norm, nz / norm

    extent = _STEP_HALF_SPACE_EXTENT
    # Box starts at (offset - extent) in the normal direction and extends 2*extent
    box = cq.Workplane("XY").box(extent * 2, extent * 2, extent * 2, centered=(True, True, False))
    box = box.translate((0, 0, offset / norm - extent))

    rot = _rotation_matrix_from_z_to_dir(nx, ny, nz)
    return _apply_rotation_and_translation(box, rot, 0.0, 0.0, 0.0)


def _union_to_cq(union: SolidUnion) -> "cq.Workplane":
    children = [_csg_to_cadquery(c) for c in union.children]
    if not children:
        raise ValueError("SolidUnion has no children")
    # Filter out empty results (e.g. from boolean ops that fully subtracted a solid)
    non_empty = [c for c in children if c.solids().size() > 0]
    if not non_empty:
        raise ValueError("SolidUnion: all children produced empty solids")
    result = non_empty[0]
    for child in non_empty[1:]:
        result = result.union(child)
    return result


def _difference_to_cq(diff: Difference) -> "cq.Workplane":
    result = _csg_to_cadquery(diff.base)
    for sub in diff.subtract:
        sub_wp = _csg_to_cadquery(sub)
        if sub_wp.solids().size() > 0:
            result = result.cut(sub_wp)
    return result


# ---------------------------------------------------------------------------
# STEP export public API
# ---------------------------------------------------------------------------


def export_cut_timber_step(cut_timber: CutTimber, filepath: Union[str, Path]) -> None:
    """Export a single CutTimber to a STEP file (global coordinates, millimetres).

    Requires cadquery. Install with: ``pip install cadquery``

    Args:
        cut_timber: The timber (with cuts applied) to export.
        filepath: Destination path. Parent directories are created if needed.
    """
    if not _CADQUERY_AVAILABLE:
        raise ImportError(
            "cadquery is required for STEP export. "
            "Install it with: pip install cadquery"
        )
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    local_csg = cut_timber.render_timber_with_cuts_csg_local()
    global_csg = adopt_csg(cut_timber.timber.transform, Transform.identity(), local_csg)
    wp = _csg_to_cadquery(global_csg)
    cq.exporters.export(wp, str(filepath), cq.exporters.ExportTypes.STEP)


def export_frame_step(
    frame: Frame,
    output_dir: Union[str, Path],
    *,
    combined: bool = False,
) -> List[Path]:
    """Export every timber in a Frame to individual STEP files.

    Requires cadquery. Install with: ``pip install cadquery``

    Geometry is in millimetres (standard STEP/CAD convention).

    Args:
        frame: The frame to export.
        output_dir: Directory for the STEP files.
        combined: If True, also write a single ``_combined.step`` containing
            all timbers as a compound shape.

    Returns:
        List of paths written.
    """
    if not _CADQUERY_AVAILABLE:
        raise ImportError(
            "cadquery is required for STEP export. "
            "Install it with: pip install cadquery"
        )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    workplanes: list[cq.Workplane] = []
    for i, ct in enumerate(frame.cut_timbers):
        name = ct.timber.ticket.name or f"timber_{i}"
        local_csg = ct.render_timber_with_cuts_csg_local()
        global_csg = adopt_csg(ct.timber.transform, Transform.identity(), local_csg)
        wp = _csg_to_cadquery(global_csg)
        workplanes.append(wp)
        dest = output_dir / f"{name}.step"
        cq.exporters.export(wp, str(dest), cq.exporters.ExportTypes.STEP)
        written.append(dest)

    if combined and workplanes:
        assembly = cq.Assembly()
        for i, wp in enumerate(workplanes):
            name = frame.cut_timbers[i].timber.ticket.name or f"timber_{i}"
            assembly.add(wp, name=name)
        dest = output_dir / "_combined.step"
        assembly.save(str(dest))
        written.append(dest)

    return written