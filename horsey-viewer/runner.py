#!/usr/bin/env python3
"""
Persistent stdio runner for the Horsey Viewer VS Code extension.

Protocol:
- stdin: newline-delimited JSON requests
- stdout: newline-delimited JSON responses/events only
- stderr: logs, warnings, tracebacks
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple


def _find_project_root_from_argv() -> "Tuple[Path | None, bool]":
    """Walk up from the target file path (argv[1]) to find the project root and type.
    Returns (root_path, is_local_dev) or (None, False)."""
    if len(sys.argv) < 2:
        return None, False
    candidate = Path(sys.argv[1]).resolve().parent
    while True:
        if (candidate / "giraffecad").is_dir():
            return candidate, True
        if (candidate / ".giraffe.yaml").is_file():
            return candidate, False
        parent = candidate.parent
        if parent == candidate:
            return None, False
        candidate = parent


_project_root, _is_local_dev = _find_project_root_from_argv()
if _project_root is not None:
    _project_root_str = str(_project_root)
    if _is_local_dev and _project_root_str not in sys.path:
        sys.path.insert(0, _project_root_str)

    # If we're not running from the venv, re-exec with the venv python so all
    # dependencies (sympy etc.) are available.
    def _find_venv_python(root: Path) -> "Path | None":
        for rel in (".venv/bin/python3", ".venv/bin/python", "venv/bin/python3", "venv/bin/python"):
            p = root / rel
            if p.exists():
                return p
        return None

    _venv_python = _find_venv_python(_project_root)
    if _venv_python is not None and Path(sys.executable).resolve() != _venv_python.resolve():
        os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)
        # os.execv replaces the current process; code below never runs if it succeeds


# Enable milestone emission so pattern scripts can report progress to the viewer.
os.environ["HORSEY_VIEWER_MILESTONES"] = "1"

TARGET_MODULE_NAME = "_horsey_viewer_target"


@dataclass
class ProfilingStats:
    """Timing data collected during runner operations (seconds)."""
    reload_s: Optional[float] = None
    geometry_s: Optional[float] = None


@dataclass
class RunnerState:
    file_path: Path
    module: Any
    frame: Any
    mesh_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)


def log_stderr(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def emit_message(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload), flush=True)


def serialize_sympy(obj: Any) -> Any:
    if hasattr(obj, "evalf"):
        return str(obj)
    if hasattr(obj, "__float__"):
        try:
            return float(obj)
        except Exception:
            return str(obj)
    return obj if isinstance(obj, (str, int, float, bool)) or obj is None else str(obj)


def serialize_vector(vec: Any) -> Any:
    if vec is None:
        return None
    try:
        return [serialize_sympy(vec[i, 0]) for i in range(vec.shape[0])]
    except Exception:
        return str(vec)


def get_timber_display_name(timber: Any) -> str:
    if hasattr(timber, "ticket") and hasattr(timber.ticket, "name"):
        return timber.ticket.name
    if hasattr(timber, "name"):
        return timber.name
    return type(timber).__name__


def _compute_csg_depth(csg: Any) -> int:
    from giraffecad.cutcsg import SolidUnion, Difference

    if isinstance(csg, SolidUnion):
        if not csg.children:
            return 1
        return 1 + max(_compute_csg_depth(child) for child in csg.children)

    if isinstance(csg, Difference):
        depths: List[int] = [_compute_csg_depth(csg.base)]
        depths.extend(_compute_csg_depth(child) for child in csg.subtract)
        return 1 + max(depths)

    return 1


def _count_csg_nodes_and_features(csg: Any) -> Tuple[int, int]:
    """Return (node_count, named_feature_count) for the CSG tree."""
    from giraffecad.cutcsg import SolidUnion, Difference, HalfSpace, RectangularPrism

    nodes = 1
    features = 0

    if isinstance(csg, HalfSpace):
        if getattr(csg, "named_feature", None) is not None:
            features += 1
    elif isinstance(csg, RectangularPrism):
        nf = getattr(csg, "named_features", None)
        if nf is not None:
            features += len(nf)

    if isinstance(csg, SolidUnion):
        for child in csg.children:
            cn, cf = _count_csg_nodes_and_features(child)
            nodes += cn
            features += cf
    elif isinstance(csg, Difference):
        cn, cf = _count_csg_nodes_and_features(csg.base)
        nodes += cn
        features += cf
        for sub in csg.subtract:
            cn, cf = _count_csg_nodes_and_features(sub)
            nodes += cn
            features += cf

    return (nodes, features)


def serialize_cut_timber(cut_timber: Any) -> Dict[str, Any]:
    timber = cut_timber.timber
    return {
        "name": get_timber_display_name(timber),
        "length": serialize_sympy(timber.length),
        "width": serialize_sympy(timber.size[0]),
        "height": serialize_sympy(timber.size[1]),
        "bottom_position": serialize_vector(timber.get_bottom_position_global()),
        "length_direction": serialize_vector(timber.get_length_direction_global()),
        "width_direction": serialize_vector(timber.get_width_direction_global()),
        "height_direction": serialize_vector(timber.get_height_direction_global()),
        "cuts_count": len(cut_timber.cuts) if hasattr(cut_timber, "cuts") else 0,
    }


def prism_to_mesh(prism: Any) -> Dict[str, Any]:
    """Convert a RectangularPrism to a flat vertex list + index list triangle mesh.

    Vertex layout (8 corners, indices 0-7):
        0: -hw, -hh, z0    1: +hw, -hh, z0    2: +hw, +hh, z0    3: -hw, +hh, z0
        4: -hw, -hh, z1    5: +hw, -hh, z1    6: +hw, +hh, z1    7: -hw, +hh, z1
    where z0 = -start_distance (bottom) and z1 = end_distance (top) in local Z.
    """
    hw = float(prism.size[0]) / 2.0
    hh = float(prism.size[1]) / 2.0
    z0 = -float(prism.start_distance) if prism.start_distance is not None else 0.0
    z1 = float(prism.end_distance) if prism.end_distance is not None else 0.0

    M = prism.transform.orientation.matrix
    P = prism.transform.position
    # Convert SymPy values to Python floats once
    m = [[float(M[r, c]) for c in range(3)] for r in range(3)]
    p = [float(P[0]), float(P[1]), float(P[2])]

    def g(x: float, y: float, z: float) -> list:
        return [
            p[0] + m[0][0] * x + m[0][1] * y + m[0][2] * z,
            p[1] + m[1][0] * x + m[1][1] * y + m[1][2] * z,
            p[2] + m[2][0] * x + m[2][1] * y + m[2][2] * z,
        ]

    verts = [
        g(-hw, -hh, z0),  # 0
        g( hw, -hh, z0),  # 1
        g( hw,  hh, z0),  # 2
        g(-hw,  hh, z0),  # 3
        g(-hw, -hh, z1),  # 4
        g( hw, -hh, z1),  # 5
        g( hw,  hh, z1),  # 6
        g(-hw,  hh, z1),  # 7
    ]

    # 12 triangles with outward-facing CCW normals (verified via cross-product)
    indices = [
        0, 2, 1,   0, 3, 2,  # bottom (-Z face)
        4, 5, 6,   4, 6, 7,  # top    (+Z face)
        0, 1, 5,   0, 5, 4,  # front  (-Y face)
        3, 7, 6,   3, 6, 2,  # back   (+Y face)
        3, 0, 4,   3, 4, 7,  # left   (-X face)
        1, 2, 6,   1, 6, 5,  # right  (+X face)
    ]

    return {
        "vertices": [coord for v in verts for coord in v],  # flat [x0,y0,z0, x1,y1,z1, ...]
        "indices": indices,
    }


def _cut_timber_to_triangle_mesh_payload(
    cut_timber: Any,
    local_csg: Any,
    timber_key: str,
    geometry_hash: str,
) -> Dict[str, Any]:
    from giraffecad.cutcsg import adopt_csg
    from giraffecad.rule import Transform
    from giraffecad.triangles import triangulate_cutcsg

    global_csg = adopt_csg(cut_timber.timber.transform, Transform.identity(), local_csg)
    triangle_mesh = triangulate_cutcsg(global_csg).mesh

    vertices = triangle_mesh.vertices.reshape(-1).tolist()
    indices = triangle_mesh.faces.reshape(-1).tolist()

    bounds = triangle_mesh.bounds
    dims = bounds[1] - bounds[0]

    timber = cut_timber.timber
    csg_nodes, csg_features = _count_csg_nodes_and_features(local_csg)
    return {
        "name": get_timber_display_name(timber),
        "memberName": get_timber_display_name(timber),
        "memberType": "timber",
        "memberKey": timber_key,
        "timberKey": timber_key,
        "hash": geometry_hash,
        "vertices": vertices,
        "indices": indices,
        "prism_length": round(float(getattr(timber, "length", dims[2])), 6),
        "prism_width": round(float(getattr(timber, "size", [dims[0], dims[1]])[0]), 6),
        "prism_height": round(float(getattr(timber, "size", [dims[0], dims[1]])[1]), 6),
        "csg_nodes": csg_nodes,
        "csg_features": csg_features,
    }


def _accessory_to_triangle_mesh_payload(
    accessory: Any,
    local_csg: Any,
    accessory_key: str,
    accessory_name: str,
    geometry_hash: str,
) -> Dict[str, Any]:
    from giraffecad.cutcsg import adopt_csg
    from giraffecad.rule import Transform
    from giraffecad.triangles import triangulate_cutcsg

    if hasattr(accessory, "transform"):
        global_csg = adopt_csg(accessory.transform, Transform.identity(), local_csg)
    else:
        # Accessories that already carry global-space CSG (e.g. CSGAccessory)
        # do not need an additional transform adoption.
        global_csg = local_csg
    triangle_mesh = triangulate_cutcsg(global_csg).mesh

    vertices = triangle_mesh.vertices.reshape(-1).tolist()
    indices = triangle_mesh.faces.reshape(-1).tolist()

    bounds = triangle_mesh.bounds
    dims = bounds[1] - bounds[0]

    return {
        "name": accessory_name,
        "memberName": accessory_name,
        "memberType": "accessory",
        "memberKey": accessory_key,
        "timberKey": accessory_key,
        "hash": geometry_hash,
        "vertices": vertices,
        "indices": indices,
        "prism_length": round(float(dims[2]), 6),
        "prism_width": round(float(dims[0]), 6),
        "prism_height": round(float(dims[1]), 6),
    }


def build_real_geometry(state: RunnerState, enable_hash_geometry_check: bool = True) -> Dict[str, Any]:
    """Build triangle mesh geometry for every cut timber, reusing unchanged cached meshes."""
    frame = state.frame
    meshes = []
    changed_keys = []
    remesh_metrics = []
    seen_keys = set()
    key_counts: Dict[str, int] = {}

    for cut_timber in frame.cut_timbers:
        try:
            timber = cut_timber.timber
            if enable_hash_geometry_check and hasattr(cut_timber, "get_viewer_cache_key_base") and callable(cut_timber.get_viewer_cache_key_base):
                key_base = str(cut_timber.get_viewer_cache_key_base())
            else:
                key_base = get_timber_display_name(timber)

            occurrence = key_counts.get(key_base, 0)
            key_counts[key_base] = occurrence + 1
            timber_key = f"{key_base}#{occurrence}"

            local_csg = cut_timber.render_timber_with_cuts_csg_local()
            geometry_hash = None
            if enable_hash_geometry_check and hasattr(cut_timber, "deep_hash") and callable(cut_timber.deep_hash):
                geometry_hash = str(cut_timber.deep_hash())
            elif enable_hash_geometry_check:
                geometry_hash = repr(local_csg)

            cached = state.mesh_cache.get(timber_key) if enable_hash_geometry_check else None
            if cached is not None and cached.get("hash") == geometry_hash:
                mesh_payload = cached["mesh"]
            else:
                remesh_t0 = time.monotonic()
                csg_depth = _compute_csg_depth(local_csg)
                mesh_payload = _cut_timber_to_triangle_mesh_payload(
                    cut_timber,
                    local_csg,
                    timber_key,
                    geometry_hash,
                )
                remesh_s = time.monotonic() - remesh_t0
                triangle_count = len(mesh_payload.get("indices", [])) // 3
                state.mesh_cache[timber_key] = {
                    "hash": geometry_hash,
                    "mesh": mesh_payload,
                    "local_csg": local_csg,
                    "cut_timber": cut_timber,
                }
                changed_keys.append(timber_key)
                remesh_metrics.append({
                    "timberKey": timber_key,
                    "remesh_s": remesh_s,
                    "csg_depth": csg_depth,
                    "triangle_count": triangle_count,
                })

            meshes.append(mesh_payload)
            seen_keys.add(timber_key)
        except Exception as exc:
            log_stderr(f"Warning: skipping geometry for {get_timber_display_name(cut_timber.timber)}: {exc}")

    accessories = list(frame.accessories) if hasattr(frame, "accessories") and frame.accessories else []
    for accessory in accessories:
        try:
            accessory_type = type(accessory).__name__
            key_base = f"accessory:{accessory_type}"

            occurrence = key_counts.get(key_base, 0)
            key_counts[key_base] = occurrence + 1
            accessory_key = f"{key_base}#{occurrence}"
            accessory_name = f"{accessory_type} {occurrence + 1}"

            local_csg = accessory.render_csg_local()
            geometry_hash = None
            if enable_hash_geometry_check and hasattr(accessory, "deep_hash") and callable(accessory.deep_hash):
                geometry_hash = str(accessory.deep_hash())
            elif enable_hash_geometry_check:
                geometry_hash = repr(local_csg)

            cached = state.mesh_cache.get(accessory_key) if enable_hash_geometry_check else None
            if cached is not None and cached.get("hash") == geometry_hash:
                mesh_payload = cached["mesh"]
            else:
                remesh_t0 = time.monotonic()
                csg_depth = _compute_csg_depth(local_csg)
                mesh_payload = _accessory_to_triangle_mesh_payload(
                    accessory,
                    local_csg,
                    accessory_key,
                    accessory_name,
                    geometry_hash,
                )
                remesh_s = time.monotonic() - remesh_t0
                triangle_count = len(mesh_payload.get("indices", [])) // 3
                state.mesh_cache[accessory_key] = {
                    "hash": geometry_hash,
                    "mesh": mesh_payload,
                }
                changed_keys.append(accessory_key)
                remesh_metrics.append({
                    "timberKey": accessory_key,
                    "memberType": "accessory",
                    "remesh_s": remesh_s,
                    "csg_depth": csg_depth,
                    "triangle_count": triangle_count,
                })

            meshes.append(mesh_payload)
            seen_keys.add(accessory_key)
        except Exception as exc:
            log_stderr(f"Warning: skipping geometry for accessory {type(accessory).__name__}: {exc}")

    removed_keys = []
    for cached_key in list(state.mesh_cache.keys()):
        if cached_key not in seen_keys:
            removed_keys.append(cached_key)
            del state.mesh_cache[cached_key]

    return {
        "kind": "triangle-geometry",
        "meshes": meshes,
        "changedKeys": changed_keys,
        "removedKeys": removed_keys,
        "remeshMetrics": remesh_metrics,
        "counts": {
            "totalTimbers": len(meshes),
            "changedTimbers": len(changed_keys),
            "removedTimbers": len(removed_keys),
            "totalAccessories": len(accessories),
            "totalMembers": len(meshes),
        },
        "options": {
            "enableHashGeometryCheck": enable_hash_geometry_check,
        },
    }


def serialize_frame(frame: Any) -> Dict[str, Any]:
    accessories = list(frame.accessories) if hasattr(frame, "accessories") and frame.accessories else []
    timbers = [serialize_cut_timber(cut_timber) for cut_timber in frame.cut_timbers]
    return {
        "name": frame.name if hasattr(frame, "name") else None,
        "timber_count": len(frame.cut_timbers),
        "accessories_count": len(accessories),
        "timbers": timbers,
        "accessories": [
            {
                "type": type(accessory).__name__,
            }
            for accessory in accessories
        ],
    }


def build_placeholder_geometry(frame: Any) -> Dict[str, Any]:
    # kept for reference – use build_real_geometry instead
    dummy_state = RunnerState(file_path=Path("."), module=None, frame=frame)
    return build_real_geometry(dummy_state)


def _module_file_path(module: Any) -> Optional[Path]:
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return None
    try:
        return Path(module_file).resolve()
    except Exception:
        return None


def _is_venv_path(path: Path) -> bool:
    path_parts = path.parts
    return ".venv" in path_parts or "venv" in path_parts


def _purge_project_modules(project_root: Path, keep_paths: set[Path], verbose: bool = False) -> None:
    """Aggressively purge all project modules from sys.modules to force clean reloads.
    
    This ensures that modified code is actually reflected when reloading, preventing
    stale cached implementations from being used due to import chain caching.
    """
    removable: list[str] = []
    removed_count = 0

    for module_name, module in list(sys.modules.items()):
        module_path = _module_file_path(module)
        if module_path is None:
            continue

        if module_path in keep_paths:
            continue

        if _is_venv_path(module_path):
            continue

        if project_root not in module_path.parents and module_path != project_root:
            continue

        removable.append(module_name)

    # Remove all project modules
    for module_name in removable:
        sys.modules.pop(module_name, None)
        removed_count += 1

    if verbose:
        if removed_count > 0:
            log_stderr(f"[reload] Purged {removed_count} project module(s): {', '.join(sorted(removable))}")
        else:
            log_stderr("[reload] No project modules to purge (first load or all already clean)")


def _looks_like_frame(value: Any) -> bool:
    return hasattr(value, "cut_timbers") and hasattr(value, "accessories")


def _looks_like_patternbook(value: Any) -> bool:
    return callable(getattr(value, "list_patterns", None)) and callable(getattr(value, "raise_pattern", None))


def _is_valid_module_part(name: str) -> bool:
    return name.isidentifier() and not name.startswith("_")


def _module_name_for_path(file_path: Path) -> str:
    if _project_root is None:
        return TARGET_MODULE_NAME

    try:
        rel = file_path.resolve().relative_to(_project_root)
    except ValueError:
        return TARGET_MODULE_NAME

    if rel.suffix != ".py":
        return TARGET_MODULE_NAME

    parts = list(rel.with_suffix("").parts)
    if not parts:
        return TARGET_MODULE_NAME
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return TARGET_MODULE_NAME
    if not all(_is_valid_module_part(part) for part in parts):
        return TARGET_MODULE_NAME
    return ".".join(parts)


def load_module_from_path(file_path: Path, verbose: bool = False) -> Any:
    """Load a Python module from file path with aggressive cache invalidation.
    
    This function ensures that:
    1. Python's import cache is invalidated
    2. All project modules are purged from sys.modules
    3. The target module and its dependencies are loaded fresh
    """
    # Step 1: Invalidate Python's built-in import caches
    importlib.invalidate_caches()
    
    # Step 2: Aggressively purge project modules
    if _project_root is not None:
        keep_paths = {Path(__file__).resolve(), file_path.resolve()}
        _purge_project_modules(_project_root, keep_paths, verbose=verbose)
    else:
        if verbose:
            log_stderr("[reload] WARNING: _project_root is None — project module purge skipped!")
            log_stderr(f"[reload]   sys.argv = {sys.argv}")
            log_stderr("[reload]   Module changes to giraffecad/ will NOT be picked up until runner restarts.")

    # Step 3: Ensure target module doesn't exist in sys.modules
    module_name = _module_name_for_path(file_path)
    if TARGET_MODULE_NAME in sys.modules:
        del sys.modules[TARGET_MODULE_NAME]
    if module_name in sys.modules:
        del sys.modules[module_name]

    # Step 4: Load the module fresh
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    if module_name != TARGET_MODULE_NAME:
        sys.modules[TARGET_MODULE_NAME] = module

    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
    
    if verbose:
        log_stderr(f"[reload] Loaded module: {module_name} from {file_path}")
    
    return module


def frame_from_patternbook(patternbook: Any) -> Any:
    pattern_names = patternbook.list_patterns()
    if not pattern_names:
        raise ValueError("PatternBook is empty")
    first_pattern = pattern_names[0]
    with contextlib.redirect_stdout(sys.stderr):
        result = patternbook.raise_pattern(first_pattern)
    if not _looks_like_frame(result):
        raise TypeError(
            f"First pattern '{first_pattern}' returned {type(result).__name__}, expected frame-like object"
        )
    return result


def resolve_frame_from_module(module: Any) -> Any:
    if hasattr(module, "example"):
        example = getattr(module, "example")
        if _looks_like_frame(example):
            return example
        if _looks_like_patternbook(example):
            return frame_from_patternbook(example)

    if hasattr(module, "build_frame") and callable(module.build_frame):
        with contextlib.redirect_stdout(sys.stderr):
            frame = module.build_frame()
        if _looks_like_frame(frame):
            return frame
        raise TypeError(f"build_frame() returned {type(frame).__name__}, expected frame-like object")

    if hasattr(module, "patternbook"):
        patternbook = getattr(module, "patternbook")
        if _looks_like_patternbook(patternbook):
            return frame_from_patternbook(patternbook)

    raise AttributeError(
        "Module must expose a module-level 'example' Frame, a 'patternbook', or a build_frame() function"
    )


def load_runner_state(file_path: str, previous_mesh_cache: Optional[Dict[str, Dict[str, Any]]] = None) -> RunnerState:
    resolved_path = Path(file_path).resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {resolved_path}")

    module = load_module_from_path(resolved_path, verbose=True)
    frame = resolve_frame_from_module(module)
    return RunnerState(
        file_path=resolved_path,
        module=module,
        frame=frame,
        mesh_cache=previous_mesh_cache if previous_mesh_cache is not None else {},
    )


def make_ready_event(state: RunnerState) -> Dict[str, Any]:
    frame_summary = serialize_frame(state.frame)
    return {
        "type": "ready",
        "examplePath": str(state.file_path),
        "commands": ["ping", "reload_example", "get_frame", "get_geometry", "get_member", "shutdown"],
        "frame": {
            "name": frame_summary["name"],
            "timber_count": frame_summary["timber_count"],
            "accessories_count": frame_summary["accessories_count"],
        },
    }


def make_success_response(request_id: Any, command: str, result: Any) -> Dict[str, Any]:
    return {
        "id": request_id,
        "ok": True,
        "command": command,
        "result": result,
    }


def make_error_response(request_id: Any, command: str, exc: Exception) -> Dict[str, Any]:
    return {
        "id": request_id,
        "ok": False,
        "command": command,
        "error": {
            "message": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    }


def get_member_result(frame: Any, member_name: str) -> Dict[str, Any]:
    for cut_timber in frame.cut_timbers:
        if get_timber_display_name(cut_timber.timber) == member_name:
            return {
                "member": serialize_cut_timber(cut_timber),
                "geometry": {
                    "kind": "placeholder-member-geometry",
                    "name": member_name,
                },
            }
    raise KeyError(f"No timber named '{member_name}' in frame")


def _feature_face_normal_local(feature: Any) -> "Optional[List[float]]":
    """Compute the outward face normal in timber-local coordinates for a CSGFeature."""
    from giraffecad.cutcsg import RectangularPrismFeature, HalfSpaceFeature, PrismFace

    if isinstance(feature, RectangularPrismFeature):
        m = feature.owner.transform.orientation.matrix
        width_dir = [float(m[i, 0]) for i in range(3)]
        height_dir = [float(m[i, 1]) for i in range(3)]
        length_dir = [float(m[i, 2]) for i in range(3)]
        face_normals = {
            PrismFace.RIGHT: width_dir,
            PrismFace.LEFT: [-c for c in width_dir],
            PrismFace.FRONT: height_dir,
            PrismFace.BACK: [-c for c in height_dir],
            PrismFace.TOP: length_dir,
            PrismFace.BOTTOM: [-c for c in length_dir],
        }
        return face_normals.get(feature.face)

    if isinstance(feature, HalfSpaceFeature):
        n = feature.owner.normal
        return [float(n[0]), float(n[1]), float(n[2])]

    return None


# Epsilon for raycast point → CSG boundary matching.  Three.js raycaster
# produces float hit points that will never land exactly on a SymPy-exact
# face.  This needs to be generous enough to absorb float→mesh error.
_FEATURE_RAYCAST_EPSILON = 1e-4


def _find_feature_at_point(state: RunnerState, member_key: str, point_world: List[float]) -> Dict[str, Any]:
    """Look up a CSG feature at a world-space point on a cached timber.

    Uses pure-float comparison with _FEATURE_RAYCAST_EPSILON to match the
    raycast hit point against prism face boundaries.
    """
    from giraffecad.cutcsg import RectangularPrism, Difference, SolidUnion, HalfSpace, PrismFace

    cached = state.mesh_cache.get(member_key)
    if cached is None or "cut_timber" not in cached or "local_csg" not in cached:
        log_stderr(f"[find_feature] cache miss for {member_key!r}")
        return {"featureName": None}

    cut_timber = cached["cut_timber"]
    local_csg = cached["local_csg"]
    timber = cut_timber.timber

    csg_nodes, csg_features = _count_csg_nodes_and_features(local_csg)
    log_stderr(f"[find_feature] {member_key}: csg_nodes={csg_nodes}, csg_features={csg_features}, world_point={point_world}")

    # Convert world point → timber-local using plain floats
    m = timber.orientation.matrix
    pos = timber.transform.position
    dx = point_world[0] - float(pos[0])
    dy = point_world[1] - float(pos[1])
    dz = point_world[2] - float(pos[2])
    # local = m^T * (world - position)   (m is orthonormal rotation)
    lx = float(m[0, 0]) * dx + float(m[1, 0]) * dy + float(m[2, 0]) * dz
    ly = float(m[0, 1]) * dx + float(m[1, 1]) * dy + float(m[2, 1]) * dz
    lz = float(m[0, 2]) * dx + float(m[1, 2]) * dy + float(m[2, 2]) * dz
    log_stderr(f"[find_feature] local_point=({lx:.6f}, {ly:.6f}, {lz:.6f})")

    # Walk the CSG tree collecting all named features, match with float epsilon
    result = _match_features_float(local_csg, lx, ly, lz)
    if result is None:
        log_stderr(f"[find_feature] no feature matched")
        return {"featureName": None}

    feature_name, feature_type, normal_local = result
    log_stderr(f"[find_feature] matched: {feature_name!r} ({feature_type})")

    # Rotate local normal to world
    normal_world = None
    if normal_local is not None:
        normal_world = [
            float(m[0, 0]) * normal_local[0] + float(m[0, 1]) * normal_local[1] + float(m[0, 2]) * normal_local[2],
            float(m[1, 0]) * normal_local[0] + float(m[1, 1]) * normal_local[1] + float(m[1, 2]) * normal_local[2],
            float(m[2, 0]) * normal_local[0] + float(m[2, 1]) * normal_local[1] + float(m[2, 2]) * normal_local[2],
        ]

    return {
        "featureName": feature_name,
        "featureType": feature_type,
        "faceNormalWorld": normal_world,
        "memberKey": member_key,
    }


def _match_features_float(csg: Any, lx: float, ly: float, lz: float) -> "Optional[tuple[str, str, Optional[List[float]]]]":
    """Walk the CSG tree and find a named feature near (lx, ly, lz) using float epsilon.

    Returns (feature_name, feature_type, normal_local) or None.
    """
    from giraffecad.cutcsg import RectangularPrism, Difference, SolidUnion, HalfSpace, PrismFace

    eps = _FEATURE_RAYCAST_EPSILON

    if isinstance(csg, Difference):
        # Check base first, then subtract children
        result = _match_features_float(csg.base, lx, ly, lz)
        if result is not None:
            return result
        for sub in csg.subtract:
            result = _match_features_float(sub, lx, ly, lz)
            if result is not None:
                return result
        return None

    if isinstance(csg, SolidUnion):
        for child in csg.children:
            result = _match_features_float(child, lx, ly, lz)
            if result is not None:
                return result
        return None

    if isinstance(csg, RectangularPrism) and csg.named_features:
        # Project point onto prism's local axes (prism transform is relative to timber-local)
        pm = csg.transform.orientation.matrix
        pp = csg.transform.position
        rdx = lx - float(pp[0])
        rdy = ly - float(pp[1])
        rdz = lz - float(pp[2])
        # prism-local = pm^T * (timber_local - prism_position)
        px = float(pm[0, 0]) * rdx + float(pm[1, 0]) * rdy + float(pm[2, 0]) * rdz
        py = float(pm[0, 1]) * rdx + float(pm[1, 1]) * rdy + float(pm[2, 1]) * rdz
        pz = float(pm[0, 2]) * rdx + float(pm[1, 2]) * rdy + float(pm[2, 2]) * rdz

        hw = float(csg.size[0]) / 2.0
        hh = float(csg.size[1]) / 2.0
        sd = float(csg.start_distance) if csg.start_distance is not None else None
        ed = float(csg.end_distance) if csg.end_distance is not None else None

        # Build face → check mapping
        face_checks = {
            PrismFace.RIGHT:  abs(px - hw) < eps,
            PrismFace.LEFT:   abs(px + hw) < eps,
            PrismFace.FRONT:  abs(py - hh) < eps,
            PrismFace.BACK:   abs(py + hh) < eps,
            PrismFace.TOP:    ed is not None and abs(pz - ed) < eps,
            PrismFace.BOTTOM: sd is not None and abs(pz - sd) < eps,
        }

        # Prism-local face normals (in prism-local space)
        width_dir = [float(pm[i, 0]) for i in range(3)]
        height_dir = [float(pm[i, 1]) for i in range(3)]
        length_dir = [float(pm[i, 2]) for i in range(3)]
        face_normals = {
            PrismFace.RIGHT: width_dir,
            PrismFace.LEFT: [-c for c in width_dir],
            PrismFace.FRONT: height_dir,
            PrismFace.BACK: [-c for c in height_dir],
            PrismFace.TOP: length_dir,
            PrismFace.BOTTOM: [-c for c in length_dir],
        }

        for name, face in csg.named_features:
            if face_checks.get(face, False):
                return (name, "RectangularPrismFeature", face_normals.get(face))

    if isinstance(csg, HalfSpace) and getattr(csg, "named_feature", None) is not None:
        n = csg.normal
        nf = [float(n[i]) for i in range(3)]
        offset = float(csg.offset)
        # dot(point, normal) - offset ≈ 0 means on the plane
        dot_val = nf[0] * lx + nf[1] * ly + nf[2] * lz
        if abs(dot_val - offset) < eps:
            return (csg.named_feature, "HalfSpaceFeature", nf)

    return None


def handle_request(state: RunnerState, request: Dict[str, Any]) -> tuple[RunnerState, Dict[str, Any], bool]:
    request_id = request.get("id")
    command = request.get("command")
    payload = request.get("payload") or {}

    if not isinstance(command, str):
        raise ValueError("Request must include a string 'command'")

    if command == "ping":
        return state, make_success_response(request_id, command, {"pong": True}), False

    if command == "reload_example":
        next_path = payload.get("filePath", str(state.file_path))
        t0 = time.monotonic()
        next_state = load_runner_state(next_path, state.mesh_cache)
        reload_s = time.monotonic() - t0
        frame_name = next_state.frame.name if hasattr(next_state.frame, "name") else "?"
        log_stderr(f"[reload] Frame loaded: '{frame_name}', {len(next_state.frame.cut_timbers)} timbers")
        result = {
            "examplePath": str(next_state.file_path),
            "frame": {
                "name": next_state.frame.name,
                "timber_count": len(next_state.frame.cut_timbers),
                "accessories_count": len(next_state.frame.accessories),
            },
            "profiling": {"reload_s": reload_s},
        }
        return next_state, make_success_response(request_id, command, result), False

    if command == "get_frame":
        return state, make_success_response(request_id, command, serialize_frame(state.frame)), False

    if command == "get_geometry":
        enable_hash_geometry_check = bool(payload.get("enableHashGeometryCheck", True))
        t0 = time.monotonic()
        geometry = build_real_geometry(state, enable_hash_geometry_check=enable_hash_geometry_check)
        geometry_s = time.monotonic() - t0
        geometry["profiling"] = {"geometry_s": geometry_s}
        return state, make_success_response(request_id, command, geometry), False

    if command == "get_member":
        member_name = payload.get("name")
        if not isinstance(member_name, str) or not member_name:
            raise ValueError("get_member requires payload.name")
        return state, make_success_response(request_id, command, get_member_result(state.frame, member_name)), False

    if command == "find_feature_at_point":
        member_key = payload.get("memberKey")
        point_list = payload.get("point")
        if not isinstance(member_key, str) or not isinstance(point_list, list) or len(point_list) != 3:
            raise ValueError("find_feature_at_point requires payload.memberKey (str) and payload.point ([x,y,z])")
        result = _find_feature_at_point(state, member_key, point_list)
        return state, make_success_response(request_id, command, result), False

    if command == "shutdown":
        return state, make_success_response(request_id, command, {"shutting_down": True}), True

    raise ValueError(f"Unknown command: {command}")


def main() -> None:
    if len(sys.argv) < 2:
        emit_message({
            "type": "fatal_error",
            "error": "No example file path provided",
        })
        sys.exit(1)

    target_path = sys.argv[1]

    log_stderr(f"[startup] runner.py ready. executable={sys.executable}")
    log_stderr(f"[startup] _project_root={_project_root}")
    log_stderr(f"[startup] target={target_path}")

    try:
        state = load_runner_state(target_path)
    except Exception as exc:
        emit_message({
            "type": "fatal_error",
            "error": {
                "message": str(exc),
                "type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            },
        })
        sys.exit(1)

    emit_message(make_ready_event(state))

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        request_id = None
        command = "unknown"
        try:
            request = json.loads(line)
            request_id = request.get("id")
            command = request.get("command", "unknown")
            state, response, should_exit = handle_request(state, request)
            emit_message(response)
            if should_exit:
                return
        except Exception as exc:
            emit_message(make_error_response(request_id, command, exc))


if __name__ == "__main__":
    main()
