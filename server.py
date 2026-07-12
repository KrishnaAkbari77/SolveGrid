from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlparse


from database import DEFAULT_DB_PATH, get_history, init_db, log_solve
from sudoku_solver import grid_to_string, parse_grid, solve


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"



class SolverHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/history":
            self._send_json({"history": get_history()})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/sudoku/solve":
                self._solve_sudoku()
            elif path == "/api/sudoku/upload_and_solve":
                self._upload_and_solve()
            elif path == "/api/history/clear":
                self._clear_history()
            else:
                self._send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _solve_sudoku(self) -> None:
        payload = self._read_json()
        raw = payload.get("digits", "")
        original = parse_grid(raw)
        working = [row[:] for row in original]
        start = time.perf_counter()
        solved = solve(working)
        elapsed = time.perf_counter() - start
        if not solved:
            self._send_json({"error": "Sudoku puzzle has no solution"}, status=422)
            return
        log_solve("sudoku", elapsed, input_summary=grid_to_string(original))
        self._send_json(
            {
                "grid": working,
                "digits": grid_to_string(working),
                "time_taken_seconds": elapsed,
            }
        )

    def _upload_and_solve(self) -> None:
        payload = self._read_json()
        b64_string = payload.get("image", "")
        if not b64_string:
            self._send_json({"error": "No image provided"}, status=400)
            return
            
        try:
            import cv2
            import numpy as np
            from image_pipeline import extract_digits
            import base64
        except ImportError as exc:
            self._send_json({"error": f"Missing dependency: {exc}"}, status=500)
            return
            
        try:
            img_data = b64_string.split(',')[1] if ',' in b64_string else b64_string
            img_bytes = base64.b64decode(img_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                self._send_json({"error": "Failed to decode image"}, status=400)
                return
                
            grid, warped = extract_digits(img)
            
            working = [row[:] for row in grid]
            start = time.perf_counter()
            solved = solve(working)
            elapsed = time.perf_counter() - start
            
            if solved:
                log_solve("sudoku", elapsed, input_summary=grid_to_string(grid))
                for r in range(9):
                    for c in range(9):
                        if grid[r][c] == 0:
                            digit_str = str(working[r][c])
                            cell_w, cell_h = warped.shape[1] // 9, warped.shape[0] // 9
                            x = c * cell_w + int(cell_w * 0.3)
                            y = r * cell_h + int(cell_h * 0.7)
                            cv2.putText(warped, digit_str, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                            
            success, encoded_img = cv2.imencode('.png', warped)
            result_b64 = "data:image/png;base64," + base64.b64encode(encoded_img).decode('utf-8')
            
            if not solved:
                self._send_json({
                    "error": "OCR extracted conflicting digits. Please correct them manually and press Solve.",
                    "grid": grid,
                    "digits": grid_to_string(grid),
                    "image": result_b64
                }, status=422)
                return
            
            self._send_json({
                "grid": working,
                "digits": grid_to_string(working),
                "time_taken_seconds": elapsed,
                "image": result_b64
            })
            
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _clear_history(self) -> None:
        init_db(DEFAULT_DB_PATH)
        with sqlite3.connect(DEFAULT_DB_PATH) as conn:
            conn.execute("DELETE FROM solves")
            conn.commit()
        self._send_json({"ok": True})


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), SolverHandler)
    print(f"Open http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
