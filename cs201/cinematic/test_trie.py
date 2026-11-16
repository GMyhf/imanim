"""字典树片的独立对撞：讲义测试代码的输出、独立写的 dict 版字典树、Python set / startswith 暴力、
随机词典上的插入删除往返，以及旁白稿里写死的数。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_trie
"""
import json
import random
import string
import unittest
from pathlib import Path

import triedata as D

NARR = " ".join(b["narration"] for b in json.loads((Path(__file__).parent / "trie.json").read_text("utf-8"))["beats"])


def prefixes(words):
    return {w[:k] for w in words for k in range(len(w) + 1)}


class TrieTest(unittest.TestCase):
    def test_lecture_demo(self):
        # 讲义 __main__：search('do') True, search('bat') False, starts_with('an') True, 删 geek 后 search False
        t = D.build()
        self.assertTrue(t.search("do"))
        self.assertFalse(t.search("bat"))
        self.assertTrue(t.starts_with("an"))
        t.delete("geek")
        self.assertFalse(t.search("geek"))

    def test_structure(self):
        self.assertEqual(D.N_NODES, len(prefixes(D.WORDS)))       # 结点 = 所有不同前缀（含空串 = 根）
        self.assertEqual((D.N_NODES, D.N_CHARS, D.SLOTS, D.USED), (17, 19, 442, 16))
        self.assertEqual(D.ROOT_KIDS, ["a", "b", "d", "g"])
        self.assertEqual(list(D.FULL), sorted(D.FULL))              # 深度优先 + 孩子按字母 = 字典序
        self.assertEqual({p for p, c in D.FULL.items() if c}, set(D.WORDS))
        news = {w: [p for p, k in tr if k == "new"] for w, tr in D.INSERTS}
        self.assertEqual(news["ant"], ["ant"])
        self.assertEqual(news["dad"], ["da", "dad"])
        self.assertEqual(sum(len(v) for v in news.values()), D.N_NODES - 1)

    def test_search_and_prefix(self):
        self.assertEqual(D.SEARCH["do"], (["d", "do"], None, True, True))
        self.assertEqual(D.SEARCH["bat"], (["b", "ba"], 2, False, False))
        self.assertEqual(D.SEARCH["an"], (["a", "an"], None, False, True))
        self.assertEqual(D.COMPLETE, {"an": ["and", "ant"], "d": ["dad", "do"]})
        self.assertEqual(D.STEPS_ANT, {6: 3, 600: 3, 60000: 3})

    def test_random_against_set(self):
        rng = random.Random(2452)
        for _ in range(60):
            # 不重复的词：讲义删除在有重复插入时有缺陷（见 test_word_count_duplicates）
            words = list(dict.fromkeys("".join(rng.choice("abcd") for _ in range(rng.randint(1, 5)))
                                       for _ in range(rng.randint(1, 30))))
            t = D.build(words)
            pool = {"".join(rng.choice("abcde") for _ in range(rng.randint(0, 5))) for _ in range(80)}
            for q in pool:
                self.assertEqual(t.search(q), q in set(words))
                self.assertEqual(t.starts_with(q), any(w.startswith(q) for w in words))
                self.assertEqual(D.complete(t, q), sorted({w for w in words if w.startswith(q)}))
                self.assertLessEqual(D.steps_to_find(t, q), len(q))
            # 删到只剩一半：结构必须和直接插入剩下的词完全一样（多删的结点都拆干净了）
            keep = list(words)
            for w in rng.sample(words, len(words) // 2):
                D.delete_trace(t, w)
                keep.remove(w)
            self.assertEqual(D.snapshot(t), D.snapshot(D.build(keep)))

    def test_word_count_duplicates(self):
        """插入计数没问题；但讲义的删除在递归终点减完计数后没再看计数是否仍大于零，
        「apple」插两次删一次，整条路径都被拆了。片子只用不重复的六个词，不受影响；这里把缺陷钉住。"""
        t = D.build(["apple", "apple", "app"])
        self.assertEqual(D.snapshot(t)["apple"], 2)
        t.delete("apple")
        self.assertFalse(t.search("apple"))          # 讲义行为：另一份 apple 也没了（应为 True）
        self.assertTrue(t.search("app"))

        class Fixed(D.Trie):                          # 终点改成「计数为零且没有孩子」才拆
            def _delete_recursive(self, current, word, index):
                if index == len(word):
                    if current.word_count == 0:
                        return False
                    current.word_count -= 1
                    return current.word_count == 0 and all(c is None for c in current.children)
                return super()._delete_recursive(current, word, index)
        f = Fixed()
        for w in ["apple", "apple", "app"]:
            f.insert(w)
        f.delete("apple")
        self.assertTrue(f.search("apple"))
        f.delete("apple")
        self.assertFalse(f.search("apple"))
        self.assertTrue(f.search("app"))
        self.assertNotIn("appl", D.snapshot(f))

    def test_delete_trace(self):
        self.assertEqual(D.DEL_GEEK, ["geek", "gee", "ge", "g"])
        self.assertEqual(D.DEL_ANT, ["ant"])

    def test_random_dictionary(self):
        for n in D.DICT_SIZES[1:]:
            d = D.random_dictionary(n)
            self.assertEqual(len(d), n)
            self.assertIn("ant", d)
            self.assertTrue(all(set(w) <= set(string.ascii_lowercase) for w in d))

    def test_narration(self):
        self.assertIn("、".join(D.WORDS), NARR)
        for s in ("十七个结点", "四百四十二格", "十六格", "四格", "六百个、六万个", "走三步", "计数是一", "计数是零"):
            self.assertIn(s, NARR)
        self.assertEqual(len(D.ROOT_KIDS), 4)


if __name__ == "__main__":
    unittest.main()
