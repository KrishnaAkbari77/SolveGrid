# SolveGrid

An automated Sudoku solver that reads a puzzle from a photo and solves it using a backtracking algorithm — with a web interface for upload, manual correction, and solve history tracking.

## What it does

1. Upload a photo of a Sudoku puzzle.
2. OpenCV finds the grid, corrects perspective, and splits it into 81 cells.
3. Tesseract OCR reads the digit in each cell.
4. A backtracking algorithm solves the puzzle.
5. If OCR misreads a digit (common with smudges or bad lighting), you can manually correct it in the grid before solving.
6. Every solve is logged to a local SQLite database, viewable as solve-time trends on a dashboard.

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript |
| Backend | Python 3 |
| Image processing | OpenCV, NumPy |
| OCR | Tesseract (via `pytesseract`) |
| Solver | Custom backtracking algorithm |
| Storage | SQLite |
| Analytics | pandas, matplotlib |

## Project structure

```
SolveGrid/
├── server.py            # Web server, API endpoints for solving + history
├── sudoku_solver.py      # Backtracking algorithm
├── image_pipeline.py     # Grid detection, perspective warp, cell cleanup, OCR
├── database.py           # SQLite read/write for solve history
├── dashboard.py           # pandas + matplotlib analytics on solve history
├── frontend/              # index.html, app.js, styles.css
├── tests/                 # Test suite
├── run_tests.py           # Test runner
├── requirements.txt
└── solves.db              # SQLite database file
```

## Setup

### 1. Install Tesseract OCR

This app expects Tesseract installed at:
```
C:\Program Files\Tesseract-OCR\tesseract.exe
```
(Windows path — adjust `image_pipeline.py` if you're on Mac/Linux.)

### 2. Install Python dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Run the server

```powershell
python server.py
```

### 4. Open the app

Go to `http://127.0.0.1:8091` in your browser.

## Usage

1. Open the **Sudoku** tab.
2. Upload a clear photo of a Sudoku grid.
3. The app extracts digits automatically and fills the board.
4. If any digit was misread, click the cell and correct it manually.
5. Click **Solve Sudoku**.
6. The solve is logged automatically — check the dashboard for solve-time history.

## Running tests

```powershell
python run_tests.py
```


