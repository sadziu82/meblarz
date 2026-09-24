"""Cached triangle meshes for purchased hardware; dimensions come from its library."""
from functools import lru_cache
from pathlib import Path

import numpy as np


@lru_cache(maxsize=64)
def mesh_geometry(path, width, depth, height, vertical=False):
    source = Path(path)
    if not source.is_absolute():
        source = Path(__file__).parents[1] / source
    vertices, faces = [], []
    for line in source.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append([float(v) for v in fields[1:4]])
        elif fields[0] == 'f':
            ids = [int(v.split('/')[0]) - 1 for v in fields[1:]]
            faces.extend((ids[0], ids[i], ids[i+1]) for i in range(1, len(ids)-1))
    v = np.asarray(vertices, dtype=np.float32)
    f = np.asarray(faces, dtype=np.int32)
    if vertical:
        # Rotate the horizontal handle 90° in the front plane, preserving winding.
        v = np.column_stack((1 - v[:, 2], v[:, 1], v[:, 0]))
    v *= np.array([width, depth, height], dtype=np.float32)
    triangles = v[f]
    face_normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals = np.zeros_like(v)
    for corner in range(3):
        np.add.at(normals, f[:, corner], face_normals)
    lengths = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(lengths[:, None], 1e-12)
    return np.ascontiguousarray(triangles.reshape(-1, 3)), np.ascontiguousarray(normals[f].reshape(-1, 3))


def board_mesh(board):
    return mesh_geometry(board.preview_mesh, board.width, board.depth, board.height,
                         board.preview_shape == 'mesh_vertical')


def ray_mesh(origin, direction, vertices):
    """Nearest double-sided triangle hit, avoiding selection through the grip gap."""
    tri = vertices.reshape(-1, 3, 3)
    a, b = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    p = np.cross(direction, b)
    det = np.einsum('ij,ij->i', a, p)
    valid = np.abs(det) > 1e-8
    inv = np.zeros_like(det)
    inv[valid] = 1 / det[valid]
    delta = origin - tri[:, 0]
    u = np.einsum('ij,ij->i', delta, p) * inv
    q = np.cross(delta, a)
    v = q @ direction * inv
    t = np.einsum('ij,ij->i', b, q) * inv
    valid &= (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0)
    return float(t[valid].min()) if valid.any() else None
