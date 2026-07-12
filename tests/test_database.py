from database import get_history, log_solve


def test_log_and_filter_history(tmp_path):
    db_path = tmp_path / "solves.db"
    log_solve("sudoku", 1.25, "test-grid", db_path=db_path)
    log_solve("cube", 2.5, "test-cube", db_path=db_path)

    all_rows = get_history(db_path=db_path)
    sudoku_rows = get_history("sudoku", db_path=db_path)

    assert len(all_rows) == 2
    assert len(sudoku_rows) == 1
    assert sudoku_rows[0]["puzzle_type"] == "sudoku"
    assert sudoku_rows[0]["input_summary"] == "test-grid"
