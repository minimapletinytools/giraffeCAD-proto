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
from typing import Any, Dict, Optional, List


def _find_project_root_from_argv() -> "Path | None":
    """Walk up from the target file path (argv[1]) to find the GiraffeCAD project root."""
    if len(sys.argv) < 2:
        return None
    candidate = Path(sys.argv[1]).resolve().parent
    while True:
        if (candidate / "code_goes_here").is_dir():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            return None
        candidate = parent


_project_root = _find_project_root_from_argv()
if _project_root is not None:
    _project_root_str = str(_project_root)
    if _project_root_str not in sys.path:
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
    from code_goes_here.cutcsg import SolidUnion, Difference

    if isinstance(csg, SolidUnion):
        if not csg.children:
            return 1
        return 1 + max(_compute_csg_depth(child) for child in csg.children)

    if isinstance(csg, Difference):
        depths: List[int] = [_compute_csg_depth(csg.base)]
        depths.extend(_compute_csg_depth(child) for child in csg.subtract)
        return 1 + max(depths)

    return 1


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
    from code_goes_here.cutcsg import adopt_csg
    from code_goes_here.rule import Transform
    from code_goes_here.triangles import triangulate_cutcsg

    global_csg = adopt_csg(cut_timber.timber.transform, Transform.identity(), local_csg)
    triangle_mesh = triangulate_cutcsg(global_csg).mesh

    vertices = triangle_mesh.vertices.reshape(-1).tolist()
    indices = triangle_mesh.faces.reshape(-1).tolist()

    bounds = triangle_mesh.bounds
    dims = bounds[1] - bounds[0]

    timber = cut_timber.timber
    return {
        "name": get_timber_display_name(timber),
        "timberKey": timber_key,
        "hash": geometry_hash,
        "vertices": vertices,
        "indices": indices,
        "prism_length": round(float(getattr(timber, "length", dims[2])), 6),
        "prism_width": round(float(getattr(timber, "size", [dims[0], dims[1]])[0]), 6),
        "prism_height": round(float(getattr(timber, "size", [dims[0], dims[1]])[1]), 6),
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
            log_stderr("[reload]   Module changes to code_goes_here/ will NOT be picked up until runner restarts.")

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
