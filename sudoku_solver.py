"""Sudoku solving and image/manual-entry helpers."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from database import log_solve
from image_pipeline import find_largest_contour, preprocess, split_grid, warp_perspective

Grid = list[list[int]]


def _require_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("install opencv-python to use Sudoku image helpers") from exc
    return cv2


def valid(grid: Grid, row: int, col: int, num: int) -> bool:
    if any(grid[row][c] == num for c in range(9)):
        return False
    if any(grid[r][col] == num for r in range(9)):
        return False

    box_r = (row // 3) * 3
    box_c = (col // 3) * 3
    return all(
        grid[r][c] != num
        for r in range(box_r, box_r + 3)
        for c in range(box_c, box_c + 3)
    )


def find_empty(grid: Grid) -> tuple[int, int] | None:
    for row in range(9):
        for col in range(9):
            if grid[row][col] == 0:
                return row, col
    return None


def solve(grid: Grid) -> bool:
    empty = find_empty(grid)
    if empty is None:
        return True

    row, col = empty
    for num in range(1, 10):
        if valid(grid, row, col, num):
            grid[row][col] = num
            if solve(grid):
                return True
            grid[row][col] = 0
    return False


def parse_grid(raw: str) -> Grid:
    digits = [int(ch) for ch in raw if ch.isdigit()]
    if len(digits) != 81:
        raise ValueError("Sudoku input must contain exactly 81 digits")
    return [digits[i : i + 9] for i in range(0, 81, 9)]


def grid_to_string(grid: Grid) -> str:
    return "".join(str(value) for row in grid for value in row)


def extract_sudoku_cells(image_path: str | Path) -> tuple[np.ndarray, list[list[np.ndarray]]]:
    cv2 = _require_cv2()
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"could not read image: {image_path}")

    processed = preprocess(image)
    contour = find_largest_contour(processed)
    warped = warp_perspective(image, contour)
    return warped, split_grid(warped, 9, 9)


def overlay_solution(warped_image: np.ndarray, original_grid: Grid, solved_grid: Grid) -> np.ndarray:
    cv2 = _require_cv2()
    output = warped_image.copy()
    height, width = output.shape[:2]
    cell_h = height // 9
    cell_w = width // 9

    for row in range(9):
        for col in range(9):
            if original_grid[row][col] == 0:
                text = str(solved_grid[row][col])
                x = col * cell_w + cell_w // 3
                y = row * cell_h + (2 * cell_h) // 3
                cv2.putText(output, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (40, 120, 40), 2)
    return output


def solve_and_log(grid: Grid) -> Grid:
    start = time.perf_counter()
    working = [row[:] for row in grid]
    if not solve(working):
        raise ValueError("Sudoku puzzle has no solution")
    elapsed = time.perf_counter() - start
    log_solve("sudoku", elapsed, input_summary=grid_to_string(grid))
    return working
