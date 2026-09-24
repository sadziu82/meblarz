import numpy as np
import pytest

from parts.preview_mesh import mesh_geometry, ray_mesh


MESH = 'assets/handles/gtv_ua_337_160.obj'


@pytest.mark.parametrize('vertical,size', [(False, (180, 26.5, 25)), (True, (25, 26.5, 180))])
def test_manufacturer_handle_mesh_bounds_and_normals(vertical, size):
    vertices, normals = mesh_geometry(MESH, *size, vertical)
    assert len(vertices) == 7196 * 3
    np.testing.assert_allclose(vertices.min(0), [0, 0, 0], atol=1e-5)
    np.testing.assert_allclose(vertices.max(0), size, atol=1e-5)
    assert np.isfinite(normals).all()
    assert np.all(np.linalg.norm(normals, axis=1) <= 1.0001)


def test_picking_hits_curved_grip_but_not_empty_space_under_it():
    vertices, _ = mesh_geometry(MESH, 180, 26.5, 25)
    assert ray_mesh(np.array([90, -10, 12.5]), np.array([0, 1, 0]), vertices) is not None
    assert ray_mesh(np.array([90, 20, -10]), np.array([0, 0, 1]), vertices) is None
