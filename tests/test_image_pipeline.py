import numpy as np

from image_pipeline import split_grid


def test_split_grid_returns_expected_cells():
    image = np.arange(36).reshape(6, 6)
    cells = split_grid(image, 3, 3)

    assert len(cells) == 3
    assert len(cells[0]) == 3
    assert cells[0][0].shape == (2, 2)
    assert cells[2][2].tolist() == [[28, 29], [34, 35]]
