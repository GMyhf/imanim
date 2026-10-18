"""零依赖测试跑把（本机 t314 环境无 pytest，约定最小依赖不装包）。

用法（任选其一，工作目录不限）：
  D:/Dev/Project1/.local/t314/Scripts/python.exe D:/Dev/Project1/mvp/tests/run_tests.py
  D:/Dev/Project1/.local/t314/Scripts/python.exe D:/Dev/Project1/mvp/tests/run_tests.py -k review
  或：cd mvp && python -m unittest discover -s tests -t tests

退出码：0 = 全绿（含 xfail 命中）；非 0 = 有失败/错误/意外通过。
控制台是 GBK：这里只把无法编码的字符替换掉，中文断言信息不靠 stdout 校验。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MVP_ROOT = HERE.parent
for p in (str(MVP_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)


def build_suite(pattern: str = "test_*.py") -> unittest.TestSuite:
    return unittest.defaultTestLoader.discover(start_dir=str(HERE), pattern=pattern,
                                               top_level_dir=str(HERE))


def main(argv: list[str]) -> int:
    pattern = "test_*.py"
    if len(argv) > 1 and argv[1] == "-k":
        pattern = f"test_*{argv[2]}*.py"
    elif len(argv) > 1:
        pattern = argv[1] if argv[1].startswith("test_") else f"test_*{argv[1]}*.py"

    try:  # GBK 控制台下打印中文不崩
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

    suite = build_suite(pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    expected = list(getattr(result, "expectedFailures", []) or [])
    unexpected = list(getattr(result, "unexpectedSuccesses", []) or [])
    skipped = list(result.skipped)
    run = result.testsRun
    passed = run - len(result.failures) - len(result.errors) - len(skipped) - len(expected) - len(unexpected)

    print()
    print("=" * 62)
    print(f"suite           : {pattern}")
    print(f"total run       : {run}")
    print(f"passed          : {passed}")
    print(f"failed          : {len(result.failures)}")
    print(f"errors          : {len(result.errors)}")
    print(f"skipped         : {len(skipped)}")
    print(f"xfail (expected failure): {len(expected)}")
    print(f"unexpected pass (bug 可能已修): {len(unexpected)}")
    print(f"exit code       : {0 if not (result.failures or result.errors or unexpected) else 1}")
    print("=" * 62)
    for t, _tb in result.failures + result.errors:
        print("FAIL/ERROR:", t.id())
    for t, _r in skipped:
        print("SKIP:", t.id(), "|", _r)
    for t, _r in expected:
        print("XFAIL:", t.id())
    for t in unexpected:
        print("XPASS:", t.id())

    return 0 if not (result.failures or result.errors or unexpected) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
