"""CS201（数据结构与算法 B）3B1B 风格短视频的制作入口：复用 cs101/cinematic/make.py 的配音、渲染、混流流程，
只换片目、目录与产物前缀；场景照样继承 cs101/cinematic/cine.py 的 Lesson（渲染时 make.py 把它放进 PYTHONPATH）。

用法（cwd 任意）：
  python cs201/cinematic/make.py --lesson kmp                 # 1080p60 成片 → cs201/out/cs201_cine_kmp/
  python cs201/cinematic/make.py --lesson kmp --quality draft # 480p15 预览
测试：(cd cs201/cinematic && python -m unittest test_*.py)
配音校对（Mac）：python cs101/cinematic/asr_check.py --course cs201 [ids]
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"                  # cs201/out
PREFIX = "cs201_cine_"
LESSONS = {"linked": ("linked.json", "linked_scene.py", "LinkedLesson"),
           "infix": ("infix.json", "infix_scene.py", "InfixLesson"),
           "kmp": ("kmp.json", "kmp_scene.py", "KMPLesson"),
           "hash": ("hash.json", "hash_scene.py", "HashLesson"),
           "trav": ("trav.json", "trav_scene.py", "TravLesson"),
           "bst": ("bst.json", "bst_scene.py", "BSTLesson"),
           "heap": ("heap.json", "heap_scene.py", "HeapLesson"),
           "huffman": ("huffman.json", "huffman_scene.py", "HuffmanLesson"),
           "topo": ("topo.json", "topo_scene.py", "TopoLesson"),
           "floyd": ("floyd.json", "floyd_scene.py", "FloydLesson"),
           "mst": ("mst.json", "mst_scene.py", "MSTLesson"),
           "qsort": ("qsort.json", "qsort_scene.py", "QSortLesson"),
           "bit": ("bit.json", "bit_scene.py", "BITLesson"),
           "scc": ("scc.json", "scc_scene.py", "SCCLesson"),
           "aoe": ("aoe.json", "aoe_scene.py", "AOELesson"),
           "bford": ("bford.json", "bford_scene.py", "BFordLesson"),
           "bigo": ("bigo.json", "bigo_scene.py", "BigOLesson"),
           "forest": ("forest.json", "forest_scene.py", "ForestLesson"),
           "trie": ("trie.json", "trie_scene.py", "TrieLesson"),
           "radix": ("radix.json", "radix_scene.py", "RadixLesson"),
           "manacher": ("manacher.json", "manacher_scene.py", "ManacherLesson"),
           "slidemax": ("slidemax.json", "slidemax_scene.py", "SlideMaxLesson")}

_spec = importlib.util.spec_from_file_location("cine_make", HERE.parent.parent / "cs101" / "cinematic" / "make.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
base.HERE, base.OUT, base.PREFIX, base.LESSONS = HERE, OUT, PREFIX, LESSONS

if __name__ == "__main__":
    sys.exit(base.main())
