"""二进制与补码片数字的独立对撞：讲义输出、独立实现（字符串逐位加法、Python 内置进制转换）、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_binary
"""
import json
from pathlib import Path
import random
import unittest

import binarydata as S


def str_add(a: str, b: str) -> tuple[str, int]:
    """独立实现：两串等长位串逐位相加（字符串操作），返回 (低位结果, 最高位进位)。"""
    out, c = [], 0
    for x, y in zip(reversed(a), reversed(b)):
        s = int(x) + int(y) + c
        out.append(str(s % 2))
        c = s // 2
    return "".join(reversed(out)), c


def str_twos(x: int, bits=8) -> str:
    """独立实现：「从右照抄到第一个 1，其余取反」（讲义 4.2 的手算法）。"""
    s = format(abs(x), f"0{bits}b")
    if x >= 0:
        return s
    k = s.rfind("1")
    return "".join("1" if c == "0" else "0" for c in s[:k]) + s[k:]


class BinaryFacts(unittest.TestCase):
    def test_course_outputs(self):
        n = S.N
        self.assertEqual((bin(n), oct(n), hex(n)), ("0b11101001", "0o351", "0xe9"))
        self.assertEqual(S.from_remainders(S.div_steps(n)), "11101001")
        self.assertEqual([r for _, _, r in S.div_steps(n)], [1, 0, 0, 1, 0, 1, 1, 1])
        self.assertEqual(S.div_steps(n)[0], (233, 116, 1))
        self.assertEqual(S.weights("11101001"), [128, 64, 32, 8, 1])
        self.assertEqual(S.hex_groups("11101001"), [("1110", "e"), ("1001", "9")])
        self.assertEqual(S.hex_groups("10011100010"), [("0100", "4"), ("1110", "e"), ("0010", "2")])
        self.assertEqual(S.NEG5, {"原码": "10000101", "反码": "11111010", "补码": "11111011"})
        self.assertEqual([S.to_twos_complement(v) for v in (5, -5, -1)], ["00000101", "11111011", "11111111"])
        self.assertEqual(-5 & 0xFF, 251)
        lines = [S.add8_trace(a, b) for a, b in S.COURSE_ADDS]
        self.assertEqual([(t["r"], t["sa"], t["sb"], t["sr"]) for t in lines],
                         [("00100111", 17, 22, 39), ("00000111", 24, -17, 7), ("10000010", 127, 3, -126)])
        self.assertEqual(S.neg_steps(-7), ("00000111", "11111000", "11111001"))
        t = S.add8_trace(5, S.wheel_pos(-7))
        self.assertEqual((t["r"], t["sr"]), ("11111110", -2))
        self.assertEqual(S.add8_trace(127, 1)["r"], "10000000")
        self.assertEqual(S.c_int32(2147483647 + 1), -2147483648)
        self.assertEqual((~6, 6 & 3, 6 | 3, 6 ^ 3, 1 << 10, 1024 >> 3), (-7, 2, 7, 5, 1024, 128))
        self.assertEqual(S.clear_lowbit(12), 8)
        self.assertEqual(S.RANGE8, (-128, 127))
        self.assertEqual(S.to_signed8(0b11100100), -28)         # 讲义：1110 0100 是 −28

    def test_against_independent(self):
        rng = random.Random(7)
        for x in range(-128, 128):
            self.assertEqual(S.to_twos_complement(x), str_twos(x))
            self.assertEqual(S.to_signed8(int(S.to_twos_complement(x), 2)), x)
            self.assertEqual(S.neg_steps(x)[2] if x < 0 else S.to_twos_complement(x), str_twos(x))
            self.assertEqual(~x, -x - 1)
            self.assertEqual(S.wheel_pos(x), int(str_twos(x), 2))
        for _ in range(500):
            a, b = rng.randrange(256), rng.randrange(256)
            r, c = str_add(format(a, "08b"), format(b, "08b"))
            t = S.add8_trace(a, b)
            self.assertEqual((t["r"], t["dropped"]), (r, bool(c)))
            sa, sb = S.to_signed8(a), S.to_signed8(b)
            if -128 <= sa + sb <= 127:                           # 不溢出时补码加法结果正确
                self.assertEqual(t["sr"], sa + sb)
            else:
                self.assertNotEqual(t["sr"], sa + sb)
        for n in range(1, 2000):
            self.assertEqual(S.from_remainders(S.div_steps(n)), format(n, "b"))
            self.assertEqual(sum(S.weights(format(n, "b"))), n)
            self.assertEqual("".join(h for _, h in S.hex_groups(format(n, "b"))).lstrip("0"), format(n, "x"))
            self.assertEqual(S.from_remainders(S.div_steps(n, 8)), format(n, "o"))   # E02734
            self.assertEqual(S.is_pow2(n), bin(n).count("1") == 1)
            self.assertEqual(bin(S.clear_lowbit(n)).count("1"), bin(n).count("1") - 1)

    def test_wheel(self):
        self.assertEqual(S.wheel_pos(-1), 255)
        self.assertEqual(S.wheel_pos(-5), 251)
        self.assertEqual((5 + S.wheel_pos(-7)) % 256, S.wheel_pos(-2))
        self.assertEqual(S.wheel_pos(-7), 249)
        self.assertGreater(24 + 0b11101111, 255)                  # 走过底部（进位被丢掉）
        self.assertEqual((24 + 0b11101111) % 256, 7)

    def test_quiz(self):
        for q in S.quiz():
            self.assertEqual(len(set(q["options"])), len(q["options"]))
            self.assertTrue(0 <= q["answer"] < len(q["options"]))
        qs = S.quiz()
        self.assertEqual(qs[0]["options"][qs[0]["answer"]], "−2")
        self.assertEqual(qs[1]["options"][qs[1]["answer"]], "11111001")
        self.assertEqual(qs[2]["options"][qs[2]["answer"]], "−126")

    def test_narration_numbers(self):
        script = json.loads(Path(__file__).with_name("binary.json").read_text(encoding="utf-8"))
        text = "".join(b["narration"] for b in script["beats"])
        for s in ("二百三十三", "负二十三", "商一百一十六，余一", "一百二十八加六十四加三十二加八加一",
                  "二百五十六种", "二百五十一", "负一百二十八到一百二十七", "五加负七", "结果是负二",
                  "二百四十九格", "二十四加负十七", "正好是七", "一百二十七加一", "二十一亿四千七百四十八万三千六百四十七",
                  "得到负七", "得到八"):
            self.assertIn(s, text)
        self.assertEqual(S.TITLE_SIGNED, -23)
        self.assertEqual(S.add8_trace(127, 1)["sr"], -128)
        self.assertEqual(S.INT32_MAX, 2147483647)
        self.assertEqual(S.add8_trace(24, 0b11101111)["sr"], 7)


if __name__ == "__main__":
    unittest.main()
