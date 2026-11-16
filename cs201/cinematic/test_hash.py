"""散列表片数字的独立对撞：讲义程序输出 / 独立模拟 / 枚举概率 / ASL 表 / 旁白数字。

用法（cwd = cs201/cinematic）：PYTHONPATH=../../cs101/cinematic python -m unittest test_hash
"""
import json
import random
import re
import unittest
from fractions import Fraction
from pathlib import Path

import hashdata as H


class HashTest(unittest.TestCase):
    def test_lecture_hashtable_output(self):
        h = H.HashTable()
        names = ["cat", "dog", "lion", "tiger", "bird", "cow", "goat", "pig", "chicken"]
        for k, v in zip(H.KEYS, names):
            h[k] = v
        # 讲义注释里的程序输出
        self.assertEqual(h.slots, [77, 44, 55, 20, 26, 93, 17, None, None, 31, 54])
        self.assertEqual(h.slots, H.TABLE)
        self.assertEqual(h[20], "chicken")
        self.assertEqual(h[17], "tiger")
        self.assertIsNone(h[99])
        self.assertEqual(H.LOAD_N, 9)

    def test_oj_samples(self):
        self.assertEqual(H.insert_hash_table([24, 13, 66, 77], 5), [4, 3, 1, 2])      # 17968 样例
        self.assertEqual(H.quadratic([24, 13, 35, 15, 14], 11), [2, 3, 1, 4, 7])     # 17975 样例
        self.assertEqual([p[-1] for p in H.Q_PATHS], [2, 3, 1, 4, 7])
        self.assertEqual([p[-1] for p in H.QL_PATHS], H.insert_hash_table(H.Q_KEYS, H.Q_M))

    def test_paths_random(self):
        rng = random.Random(5)
        for _ in range(300):
            m = rng.choice([7, 11, 13, 17])
            keys = rng.sample(range(200), rng.randint(1, m))
            paths, table = H.linear_paths(keys, m)
            self.assertEqual([p[-1] for p in paths], H.insert_hash_table(keys, m))
            h = H.HashTable()
            if m == 11:
                for k in keys:
                    h[k] = k
                self.assertEqual(h.slots, table)
            for k in keys:                                   # 查找路径 = 插入路径
                seen, ok = H.lookup_path(table, k)
                self.assertTrue(ok)
                self.assertEqual(seen, paths[keys.index(k)])
            if len(keys) <= m // 2:
                qp, _, qt = H.quad_paths(keys, m)
                self.assertEqual([p[-1] for p in qp], H.quadratic(keys, m))

    def test_scene_numbers(self):
        self.assertEqual(H.DIRECT, [54, 26, 93, 17, 77, 31])
        self.assertEqual(dict(H.COLLIDED), {44: [0, 1], 55: [0, 1, 2], 20: [9, 10, 0, 1, 2, 3]})
        self.assertEqual(H.FIND20, [9, 10, 0, 1, 2, 3])
        self.assertEqual((H.FIND99, H.FOUND99), ([0, 1, 2, 3, 4, 5, 6], False))
        # 聚集概率：枚举下一个关键字的 11 个基地址，独立模拟线性探测落点
        land = {}
        for h0 in range(H.M):
            t = list(H.TABLE)
            p = h0
            while t[p] is not None:
                p = (p + 1) % H.M
            land[p] = land.get(p, 0) + 1
        self.assertEqual(land, H.ODDS)
        self.assertEqual(H.ODDS, {7: 10, 8: 1})
        self.assertEqual(sorted(p[-1] for p in H.QL_PATHS), [2, 3, 4, 5, 6])
        self.assertEqual(H.CHAINS[1], [14, 1, 27, 79])
        self.assertEqual(sum(map(len, H.CHAINS)), 12)
        # dsa-modernization 10.3.5 节表：线性探测成功 ASL
        for a, v in [(0.25, 1.17), (0.5, 1.5), (0.7, 2.17), (0.8, 3.0), (0.9, 5.5), (0.95, 10.5)]:
            self.assertAlmostEqual(H.asl_linear_hit(a), v, places=2)

    def test_narration_numbers(self):
        beats = {b["id"]: b["narration"] for b in
                 json.loads((Path(__file__).parent / "hash.json").read_text(encoding="utf-8"))["beats"]}
        cn = {0: "零", 1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十",
              11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五", 17: "十七", 20: "二十", 24: "二十四",
              26: "二十六", 27: "二十七", 31: "三十一", 35: "三十五", 44: "四十四", 54: "五十四", 55: "五十五",
              77: "七十七", 79: "七十九", 93: "九十三", 99: "九十九"}
        mf = beats["modfn"]
        self.assertIn(f"表长是{cn[H.M]}", mf)
        self.assertIn(f"五十四除以十一余{cn[54 % 11]}", mf)
        for k in H.DIRECT[1:]:
            self.assertIn(f"{cn[k]}放{cn[k % H.M]}号", mf)
        self.assertIn(f"这{cn[len(H.DIRECT)]}个关键字", mf)
        co = beats["collide"]
        self.assertIn(f"四十四，除以十一余{cn[44 % 11]}", co)
        self.assertIn(f"挪到{cn[H.COLLIDED[1][1][-1]]}号", co)
        self.assertIn(f"二十余{cn[20 % 11]}", co)
        self.assertIn(f"挪到{cn[H.COLLIDED[2][1][-1]]}号才找到空位，看了{cn[len(H.COLLIDED[2][1])]}个槽", co)
        cl = beats["cluster"]
        self.assertIn(f"连续{cn[H.LOAD_N]}个槽", cl)
        self.assertIn(f"十一分之{cn[H.ODDS[7]]}", cl)
        self.assertIn(f"十一分之{cn[H.ODDS[8]]}", cl)
        lk = beats["lookup"]
        self.assertIn(f"比较了{cn[len(H.FIND20)]}次", lk)
        self.assertIn(f"比了{cn[len(H.FIND99)]}次都不是", lk)
        self.assertIn(f"十一分之{cn[H.LOAD_N]}", lk)
        q = beats["quad"]
        self.assertIn("、".join(cn[k] for k in H.Q_KEYS), q)
        self.assertIn(f"三十五跳到{cn[H.Q_PATHS[2][-1]]}号，十四跳到{cn[H.Q_PATHS[4][-1]]}号", q)
        ch = beats["chain"]
        self.assertIn(f"表长{cn[H.C_M]}，{cn[len(H.C_KEYS)]}个关键字", ch)
        self.assertIn("、".join(cn[k] for k in H.CHAINS[1]), ch)
        self.assertIn(f"长度为{cn[len(H.CHAINS[1])]}的链", ch)
        ld = beats["load"]
        for a, s in [(0.5, "零点五时是一点五次"), (0.8, "零点八时变成三次"), (0.9, "零点九时是五点五次")]:
            self.assertIn(s, ld)
        self.assertEqual(Fraction(H.asl_linear_hit(0.8)).limit_denominator(10), 3)
        for bid, text in beats.items():
            self.assertIsNone(re.search(r"\d", text), bid)


if __name__ == "__main__":
    unittest.main()
