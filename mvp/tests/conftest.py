"""测试路径引导（pytest / unittest 双兼容，零依赖）。

约定：本文件不做任何断言，只把 mvp/ 根目录插入 sys.path，
使 `pipeline` / `audio` 在两种运行方式下都能导入：
  1) python tests/run_tests.py            （标准库 unittest，当前唯一可用方式）
  2) pytest mvp/tests                      （将来若装了 pytest）

本机 t314 环境没有 pytest（约定最小依赖，不安装任何包）。
"""

from __future__ import annotations

import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
if str(MVP_ROOT) not in sys.path:
    sys.path.insert(0, str(MVP_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
