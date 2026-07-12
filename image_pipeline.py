from __future__ import annotations

from typing import Iterable

import numpy as np


def _require_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("install opencv-python to use image processing functions") from exc
    return cv2


def preprocess(image: np.ndarray) -> np.ndarray:
    """Convert an image to a high-contrast thresholded grayscale image."""
    cv2 = _require_cv2()
    if image is None:
        raise ValueError("image must not be None")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2,
    )


def find_largest_contour(image: np.ndarray) -> np.ndarray:
    """Find the largest four-corner contour in a preprocessed image."""
    cv2 = _require_cv2()
    contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[np.ndarray] = []

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 1000:
            candidates.append(approx.reshape(4, 2))

    if not candidates:
        raise ValueError("no four-corner grid contour found")

    return max(candidates, key=cv2.contourArea)


def _order_corners(corners: Iterable[Iterable[float]]) -> np.ndarray:
    points = np.asarray(corners, dtype=np.float32)
    if points.shape != (4, 2):
        raise ValueError("corners must have shape (4, 2)")

    ordered = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).ravel()
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(diffs)]
    ordered[3] = points[np.argmax(diffs)]
    return ordered


def warp_perspective(image: np.ndarray, corners: np.ndarray, size: int = 450) -> np.ndarray:
    """Flatten a tilted grid into a straight-on square image."""
    cv2 = _require_cv2()
    ordered = _order_corners(corners)
    destination = np.array(
        [[0, 0], [size - 1, 0], [size - 1, size - 1], [0, size - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(ordered, destination)
    return cv2.warpPerspective(image, matrix, (size, size))


def split_grid(image: np.ndarray, rows: int, cols: int) -> list[list[np.ndarray]]:
    """Split an image into a rows x cols grid using numpy slicing."""
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive")

    height, width = image.shape[:2]
    cell_h = height // rows
    cell_w = width // cols
    if cell_h == 0 or cell_w == 0:
        raise ValueError("image is too small for requested grid")

    return [
        [image[r * cell_h : (r + 1) * cell_h, c * cell_w : (c + 1) * cell_w] for c in range(cols)]
        for r in range(rows)
    ]


def extract_digits(image: np.ndarray) -> tuple[list[list[int]], np.ndarray]:
    """Process image and use OCR to extract 9x9 Sudoku digits using a fast 1D column composite. Returns (grid, warped_image)."""
    try:
        import pytesseract
        import os
        tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tess_path):
            pytesseract.pytesseract.tesseract_cmd = tess_path
    except ImportError as exc:
        raise RuntimeError("install pytesseract for OCR") from exc
        
    contour = find_largest_contour(preprocess(image))
    warped = warp_perspective(image, contour, size=450)
    cells = split_grid(warped, 9, 9)
    
    cv2 = _require_cv2()
    grid = [[0]*9 for _ in range(9)]
    
    cell_h, cell_w = cells[0][0].shape[:2]
    margin = int(cell_h * 0.15)
    crop_h = cell_h - 2 * margin
    crop_w = cell_w - 2 * margin
    pad = 40  # HUGE padding to completely prevent vertical bleeding/grouping
    block_h = crop_h + pad
    
    composite_img = np.full((81 * block_h, crop_w), 255, dtype=np.uint8)
    empty_cells = [False] * 81
    
    for r in range(9):
        for c in range(9):
            idx = r * 9 + c
            cell = cells[r][c]
            cell_cropped = cell[margin:cell_h-margin, margin:cell_w-margin]
            
            gray = cv2.cvtColor(cell_cropped, cv2.COLOR_BGR2GRAY) if cell_cropped.ndim == 3 else cell_cropped
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
            
            # Remove any connected components that touch the border to eliminate grid lines
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh, connectivity=8)
            clean_thresh = np.zeros_like(thresh)
            h_thresh, w_thresh = thresh.shape
            
            for label in range(1, num_labels):
                x, y, w, h, area = stats[label]
                if x == 0 or y == 0 or (x + w) == w_thresh or (y + h) == h_thresh:
                    continue
                if area < (crop_h * crop_w * 0.02):
                    continue
                clean_thresh[labels == label] = 255
            
            # Stricter empty-cell check on the clean image
            if cv2.countNonZero(clean_thresh) == 0:
                empty_cells[idx] = True
            else:
                empty_cells[idx] = False
                inv_thresh = cv2.bitwise_not(clean_thresh)
                # Paste the digit centered in the padded block
                start_y = idx * block_h + pad // 2
                composite_img[start_y : start_y + crop_h, 0 : crop_w] = inv_thresh

    config = '--psm 6 -c tessedit_char_whitelist=123456789'
    data = pytesseract.image_to_data(composite_img, output_type=pytesseract.Output.DICT, config=config)
    
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if text.isdigit():
            y = data['top'][i]
            # Since each block is very tall, we can reliably identify it by its top coordinate
            idx = y // block_h
            if 0 <= idx < 81 and not empty_cells[idx]:
                r = idx // 9
                c = idx % 9
                digit_chars = [ch for ch in text if ch.isdigit()]
                if digit_chars:
                    grid[r][c] = int(digit_chars[0])
                    
    return grid, warped
