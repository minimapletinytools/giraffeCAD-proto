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
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


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


from code_goes_here.patternbook import PatternBook  # noqa: E402
from code_goes_here.timber import Frame  # noqa: E402


TARGET_MODULE_NAME = "_horsey_viewer_target"


@dataclass
class RunnerState:
    file_path: Path
    module: Any
    frame: Frame


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


def serialize_frame(frame: Frame) -> Dict[str, Any]:
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


def build_placeholder_geometry(frame: Frame) -> Dict[str, Any]:
    return {
        "kind": "placeholder-geometry",
        "frame_name": frame.name if hasattr(frame, "name") else None,
        "meshes": [
            {
                "name": get_timber_display_name(cut_timber.timber),
                "status": "placeholder",
            }
            for cut_timber in frame.cut_timbers
        ],
    }


def load_module_from_path(file_path: Path) -> Any:
    if TARGET_MODULE_NAME in sys.modules:
        del sys.modules[TARGET_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(TARGET_MODULE_NAME, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[TARGET_MODULE_NAME] = module

    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
    return module


def frame_from_patternbook(patternbook: PatternBook) -> Frame:
    pattern_names = patternbook.list_patterns()
    if not pattern_names:
        raise ValueError("PatternBook is empty")
    first_pattern = pattern_names[0]
    result = patternbook.raise_pattern(first_pattern)
    if not isinstance(result, Frame):
        raise TypeError(
            f"First pattern '{first_pattern}' returned {type(result).__name__}, expected Frame"
        )
    return result


def resolve_frame_from_module(module: Any) -> Frame:
    if hasattr(module, "example"):
        example = getattr(module, "example")
        if isinstance(example, Frame):
            return example
        if isinstance(example, PatternBook):
            return frame_from_patternbook(example)

    if hasattr(module, "build_frame") and callable(module.build_frame):
        with contextlib.redirect_stdout(sys.stderr):
            frame = module.build_frame()
        if isinstance(frame, Frame):
            return frame
        raise TypeError(f"build_frame() returned {type(frame).__name__}, expected Frame")

    if hasattr(module, "patternbook"):
        patternbook = getattr(module, "patternbook")
        if isinstance(patternbook, PatternBook):
            return frame_from_patternbook(patternbook)

    raise AttributeError(
        "Module must expose a module-level 'example' Frame, a 'patternbook', or a build_frame() function"
    )


def load_runner_state(file_path: str) -> RunnerState:
    resolved_path = Path(file_path).resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {resolved_path}")

    module = load_module_from_path(resolved_path)
    frame = resolve_frame_from_module(module)
    return RunnerState(file_path=resolved_path, module=module, frame=frame)


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


def get_member_result(frame: Frame, member_name: str) -> Dict[str, Any]:
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
        next_state = load_runner_state(next_path)
        result = {
            "examplePath": str(next_state.file_path),
            "frame": {
                "name": next_state.frame.name,
                "timber_count": len(next_state.frame.cut_timbers),
                "accessories_count": len(next_state.frame.accessories),
            },
        }
        return next_state, make_success_response(request_id, command, result), False

    if command == "get_frame":
        return state, make_success_response(request_id, command, serialize_frame(state.frame)), False

    if command == "get_geometry":
        return state, make_success_response(request_id, command, build_placeholder_geometry(state.frame)), False

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
