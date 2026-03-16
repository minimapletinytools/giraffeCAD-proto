"""
Triangle meshing and raw raycasting for CutCSG.

This module is the float-boundary adapter between the exact symbolic CutCSG
model and trimesh. All SymPy-to-float conversion happens here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple, Union

import numpy as np
import trimesh
from sympy import Expr

from .cutcsg import (
    ConvexPolygonExtrusion,
    CutCSG,
    Cylinder,
    Difference,
    HalfSpace,
    RectangularPrism,
    SolidUnion,
)
from .rule import Matrix, Numeric, Transform, V2, V3


TRIANGLES_FLOAT_DIGITS = 6
TRIANGLES_PRISM_INFINITE_EXTENT = 1000.0
TRIANGLES_HALF_SPACE_INFINITE_EXTENT = TRIANGLES_PRISM_INFINITE_EXTENT * 10.0
TRIANGLES_CYLINDER_SECTIONS = 32
TRIANGLES_RAY_EPSILON = 1e-8


Float3 = Tuple[float, float, float]


@dataclass(frozen=True)
class TriangleMesh:
    mesh: trimesh.Trimesh
    face_sources: Optional[Tuple[str, ...]] = None

    @property
    def vertices(self) -> np.ndarray:
        return self.mesh.vertices

    @property
    def faces(self) -> np.ndarray:
        return self.mesh.faces

    @property
    def face_normals(self) -> np.ndarray:
        return self.mesh.face_normals


@dataclass(frozen=True)
class RaycastHit:
    position: Float3
    normal: Float3
    distance: float
    face_index: int
    triangle: Tuple[Float3, Float3, Float3]


# TODO DELETE ME
MeshableTarget = Union[TriangleMesh, CutCSG]


def triangulate_cutcsg(csg: CutCSG) -> TriangleMesh:
    return _triangulate_with_label(csg, label=type(csg).__name__)


def mesh_cutcsg(csg: CutCSG) -> TriangleMesh:
    return triangulate_cutcsg(csg)


# TODO raycast on TriangleMesh only
def raw_raycast_first(target: MeshableTarget, origin: V3, direction: V3) -> Optional[RaycastHit]:
    hits = raw_raycast_all(target, origin, direction)
    if not hits:
        return None
    return hits[0]


# TODO raycast on TriangleMesh only
def raw_raycast_all(target: MeshableTarget, origin: V3, direction: V3) -> list[RaycastHit]:
    triangle_mesh = target if isinstance(target, TriangleMesh) else triangulate_cutcsg(target)
    mesh = triangle_mesh.mesh

    origin_array = _vector3_to_numpy(origin)
    direction_array = _vector3_to_numpy(direction)
    direction_norm = np.linalg.norm(direction_array)
    if direction_norm <= TRIANGLES_RAY_EPSILON:
        raise ValueError("Ray direction must be non-zero")
    direction_unit = direction_array / direction_norm

    triangles = np.asarray(mesh.triangles, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)

    hits: list[RaycastHit] = []
    for face_index, triangle in enumerate(triangles):
        hit = _ray_intersect_triangle(origin_array, direction_unit, triangle)
        if hit is None:
            continue
        distance, position = hit
        hits.append(
            RaycastHit(
                position=_tuple3(position),
                normal=_tuple3(normals[face_index]),
                distance=round(float(distance), TRIANGLES_FLOAT_DIGITS),
                face_index=face_index,
                triangle=(
                    _tuple3(triangle[0]),
                    _tuple3(triangle[1]),
                    _tuple3(triangle[2]),
                ),
            )
        )

    hits.sort(key=lambda item: item.distance)
    return hits


def _triangulate_with_label(csg: CutCSG, label: str) -> TriangleMesh:
    if isinstance(csg, RectangularPrism):
        mesh = _mesh_rectangular_prism(csg)
        return TriangleMesh(mesh=mesh, face_sources=tuple(label for _ in range(len(mesh.faces))))
    if isinstance(csg, Cylinder):
        mesh = _mesh_cylinder(csg)
        return TriangleMesh(mesh=mesh, face_sources=tuple(label for _ in range(len(mesh.faces))))
    if isinstance(csg, ConvexPolygonExtrusion):
        mesh = _mesh_convex_polygon_extrusion(csg)
        return TriangleMesh(mesh=mesh, face_sources=tuple(label for _ in range(len(mesh.faces))))
    if isinstance(csg, HalfSpace):
        mesh = _mesh_half_space(csg)
        return TriangleMesh(mesh=mesh, face_sources=tuple(label for _ in range(len(mesh.faces))))
    if isinstance(csg, SolidUnion):
        return _mesh_union(csg)
    if isinstance(csg, Difference):
        return _mesh_difference(csg)
    raise TypeError(f"Unsupported CutCSG type for triangulation: {type(csg).__name__}")


def _mesh_union(csg: SolidUnion) -> TriangleMesh:
    child_meshes = [triangulate_cutcsg(child).mesh for child in csg.children]
    result_mesh = _run_boolean("union", child_meshes)
    return TriangleMesh(mesh=result_mesh)


def _mesh_difference(csg: Difference) -> TriangleMesh:
    meshes = [triangulate_cutcsg(csg.base).mesh]
    meshes.extend(triangulate_cutcsg(child).mesh for child in csg.subtract)
    result_mesh = _run_boolean("difference", meshes)
    return TriangleMesh(mesh=result_mesh)


def _run_boolean(operation: str, meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if len(meshes) < 2:
        if not meshes:
            raise ValueError("Boolean operations require at least one mesh")
        return _finalize_mesh(meshes[0].copy())

    copied_meshes = [_finalize_mesh(mesh.copy()) for mesh in meshes]
    try:
        if operation == "union":
            result = trimesh.boolean.union(copied_meshes, engine="manifold", check_volume=False)
        elif operation == "difference":
            result = trimesh.boolean.difference(copied_meshes, engine="manifold", check_volume=False)
        else:
            raise ValueError(f"Unsupported boolean operation: {operation}")
    except BaseException as exc:
        raise RuntimeError(f"trimesh boolean {operation} failed: {exc}") from exc

    if result is None:
        raise RuntimeError(f"trimesh boolean {operation} returned no mesh")

    if isinstance(result, trimesh.Scene):
        geometry = list(result.geometry.values())
        if not geometry:
            raise RuntimeError(f"trimesh boolean {operation} returned an empty scene")
        result = trimesh.util.concatenate(geometry)

    return _finalize_mesh(result)


def _mesh_rectangular_prism(prism: RectangularPrism) -> trimesh.Trimesh:
    start_distance, end_distance = _finite_extent_pair(prism.start_distance, prism.end_distance)
    length = end_distance - start_distance
    if length <= 0:
        raise ValueError("RectangularPrism must have positive length after finite conversion")

    extents = [
        _numeric_to_float(prism.size[0]),
        _numeric_to_float(prism.size[1]),
        length,
    ]
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation([0.0, 0.0, (start_distance + end_distance) / 2.0])
    mesh.apply_transform(_transform_to_numpy(prism.transform))
    return _finalize_mesh(mesh)


def _mesh_cylinder(cylinder: Cylinder) -> trimesh.Trimesh:
    start_distance, end_distance = _finite_extent_pair(cylinder.start_distance, cylinder.end_distance)
    height = end_distance - start_distance
    if height <= 0:
        raise ValueError("Cylinder must have positive height after finite conversion")

    mesh = trimesh.creation.cylinder(
        radius=_numeric_to_float(cylinder.radius),
        height=height,
        sections=TRIANGLES_CYLINDER_SECTIONS,
    )

    axis = _normalize_vector(_vector3_to_numpy(cylinder.axis_direction))
    center = _vector3_to_numpy(cylinder.position) + axis * ((start_distance + end_distance) / 2.0)
    transform = np.eye(4)
    transform[:3, :3] = _basis_from_z_axis(axis)
    transform[:3, 3] = center
    mesh.apply_transform(transform)
    return _finalize_mesh(mesh)


def _mesh_half_space(half_space: HalfSpace) -> trimesh.Trimesh:
    unit_normal = _normalize_vector(_vector3_to_numpy(half_space.normal))
    plane_point = _half_space_point_on_plane(half_space)

    transform = np.eye(4)
    transform[:3, :3] = _basis_from_z_axis(unit_normal)
    transform[:3, 3] = plane_point + unit_normal * (TRIANGLES_HALF_SPACE_INFINITE_EXTENT / 2.0)

    mesh = trimesh.creation.box(
        extents=[
            TRIANGLES_HALF_SPACE_INFINITE_EXTENT * 2.0,
            TRIANGLES_HALF_SPACE_INFINITE_EXTENT * 2.0,
            TRIANGLES_HALF_SPACE_INFINITE_EXTENT,
        ]
    )
    mesh.apply_transform(transform)
    return _finalize_mesh(mesh)


def _mesh_convex_polygon_extrusion(extrusion: ConvexPolygonExtrusion) -> trimesh.Trimesh:
    if not extrusion.is_valid():
        raise ValueError("ConvexPolygonExtrusion must be valid before triangulation")

    start_distance, end_distance = _finite_extent_pair(extrusion.start_distance, extrusion.end_distance)
    if end_distance <= start_distance:
        raise ValueError("ConvexPolygonExtrusion must have positive height after finite conversion")

    ordered_points = _polygon_points_ccw(extrusion.points)
    point_count = len(ordered_points)
    bottom_z = start_distance
    top_z = end_distance

    vertices: list[list[float]] = []
    for point in ordered_points:
        vertices.append([_numeric_to_float(point[0]), _numeric_to_float(point[1]), bottom_z])
    for point in ordered_points:
        vertices.append([_numeric_to_float(point[0]), _numeric_to_float(point[1]), top_z])

    faces: list[list[int]] = []
    for index in range(1, point_count - 1):
        faces.append([0, index + 1, index])
        faces.append([point_count, point_count + index, point_count + index + 1])

    for index in range(point_count):
        next_index = (index + 1) % point_count
        bottom_a = index
        bottom_b = next_index
        top_a = point_count + index
        top_b = point_count + next_index
        faces.append([bottom_a, bottom_b, top_b])
        faces.append([bottom_a, top_b, top_a])

    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=False)
    mesh.apply_transform(_transform_to_numpy(extrusion.transform))
    return _finalize_mesh(mesh)


def _finite_extent_pair(
    start_distance: Optional[Numeric], end_distance: Optional[Numeric]
) -> Tuple[float, float]:
    start = -TRIANGLES_PRISM_INFINITE_EXTENT if start_distance is None else _numeric_to_float(start_distance)
    end = TRIANGLES_PRISM_INFINITE_EXTENT if end_distance is None else _numeric_to_float(end_distance)
    return start, end


def _half_space_point_on_plane(half_space: HalfSpace) -> np.ndarray:
    normal = _vector3_to_numpy(half_space.normal)
    normal_dot = float(np.dot(normal, normal))
    if normal_dot <= TRIANGLES_RAY_EPSILON:
        raise ValueError("HalfSpace normal must be non-zero")
    scale = _numeric_to_float(half_space.offset) / normal_dot
    return normal * scale


def _basis_from_z_axis(direction: np.ndarray) -> np.ndarray:
    z_axis = _normalize_vector(direction)
    helper = np.array([1.0, 0.0, 0.0], dtype=float)
    if abs(float(np.dot(helper, z_axis))) > 0.9:
        helper = np.array([0.0, 1.0, 0.0], dtype=float)
    x_axis = np.cross(helper, z_axis)
    x_axis = _normalize_vector(x_axis)
    y_axis = np.cross(z_axis, x_axis)
    y_axis = _normalize_vector(y_axis)
    return np.column_stack((x_axis, y_axis, z_axis))


def _transform_to_numpy(transform: Transform) -> np.ndarray:
    matrix = np.eye(4)
    matrix[:3, :3] = _matrix3_to_numpy(transform.orientation.matrix)
    matrix[:3, 3] = _vector3_to_numpy(transform.position)
    return matrix


def _vector3_to_numpy(vector: V3) -> np.ndarray:
    return np.asarray([_numeric_to_float(vector[index]) for index in range(3)], dtype=float)


def _matrix3_to_numpy(matrix: Matrix) -> np.ndarray:
    return np.asarray(
        [[_numeric_to_float(matrix[row, col]) for col in range(3)] for row in range(3)],
        dtype=float,
    )


def _numeric_to_float(value: Numeric) -> float:
    if isinstance(value, Expr):
        evaluated = value.evalf(TRIANGLES_FLOAT_DIGITS)
        return round(float(evaluated), TRIANGLES_FLOAT_DIGITS)
    return round(float(value), TRIANGLES_FLOAT_DIGITS)


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= TRIANGLES_RAY_EPSILON:
        raise ValueError("Vector must be non-zero")
    return vector / norm


def _polygon_points_ccw(points: Iterable[V2]) -> list[V2]:
    ordered = list(points)
    signed_area = 0.0
    for index, point in enumerate(ordered):
        next_point = ordered[(index + 1) % len(ordered)]
        signed_area += _numeric_to_float(point[0]) * _numeric_to_float(next_point[1])
        signed_area -= _numeric_to_float(next_point[0]) * _numeric_to_float(point[1])
    if signed_area < 0:
        ordered.reverse()
    return ordered


def _finalize_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=False)
    return mesh


def _ray_intersect_triangle(
    origin: np.ndarray, direction: np.ndarray, triangle: np.ndarray
) -> Optional[Tuple[float, np.ndarray]]:
    vertex0 = triangle[0]
    vertex1 = triangle[1]
    vertex2 = triangle[2]

    edge1 = vertex1 - vertex0
    edge2 = vertex2 - vertex0
    pvec = np.cross(direction, edge2)
    determinant = float(np.dot(edge1, pvec))
    if abs(determinant) <= TRIANGLES_RAY_EPSILON:
        return None

    inv_determinant = 1.0 / determinant
    tvec = origin - vertex0
    u_coord = float(np.dot(tvec, pvec)) * inv_determinant
    if u_coord < 0.0 or u_coord > 1.0:
        return None

    qvec = np.cross(tvec, edge1)
    v_coord = float(np.dot(direction, qvec)) * inv_determinant
    if v_coord < 0.0 or (u_coord + v_coord) > 1.0:
        return None

    distance = float(np.dot(edge2, qvec)) * inv_determinant
    if distance <= TRIANGLES_RAY_EPSILON:
        return None

    hit_position = origin + direction * distance
    return distance, hit_position


def _tuple3(values: object) -> Float3:
    array = np.asarray(values, dtype=float)
    return (
        round(float(array[0]), TRIANGLES_FLOAT_DIGITS),
        round(float(array[1]), TRIANGLES_FLOAT_DIGITS),
        round(float(array[2]), TRIANGLES_FLOAT_DIGITS),
    )