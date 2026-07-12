
from __future__ import annotations

from pathlib import Path
import importlib.util
import traceback


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures = 0
    for test_path in sorted(Path("tests").glob("test_*.py")):
        module = _load_module(test_path)
        for name in dir(module):
            if not name.startswith("test_"):
                continue
            test = getattr(module, name)
            try:
                if "tmp_path" in test.__code__.co_varnames[: test.__code__.co_argcount]:
                    import tempfile

                    with tempfile.TemporaryDirectory() as tmp:
                        test(Path(tmp))
                else:
                    test()
                print(f"PASS {test_path.name}::{name}")
            except Exception:
                failures += 1
                print(f"FAIL {test_path.name}::{name}")
                traceback.print_exc()
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
