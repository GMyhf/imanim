"""浮点数片数字的独立对撞：讲义打印结果、按定义手工编码 IEEE 754、有理数精确运算、旁白数字。

用法（cwd = cs101/cinematic）：python -m unittest test_float
"""
from decimal import Decimal
from fractions import Fraction
import json
import math
from pathlib import Path
import unittest

import floatdata as S


def encode(x: Fraction):
    """不经过 struct，按定义把正有理数舍入成双精度（就近取偶），返回 (存储指数, 52 位尾数整数)。"""
    e = 0
    while x >= 2:
        x /= 2
        e += 1
    while x < 1:
        x *= 2
        e -= 1
    scaled = (x - 1) * 2 ** 52
    q, r = divmod(scaled.numerator, scaled.denominator)
    r = Fraction(r, scaled.denominator)
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and q % 2 == 1):
        q += 1
    if q == 2 ** 52:
        q, e = 0, e + 1
    return e + 1023, q


class FloatFacts(unittest.TestCase):
    def test_lecture_outputs(self):
        # 讲义 4.4 节代码注释里的打印结果
        s, e, m = S.float_bits(-6.5)
        self.assertEqual((s, e, m[:8]), ("1", "10000000001", "10100000"))
        self.assertEqual(int(e, 2) - 1023, 2)
        self.assertEqual(S.TENTH_20, "0.10000000000000000555")
        self.assertEqual(S.TENTH_HEX, "0x1.999999999999ap-4")
        self.assertEqual(S.TENTH_DECIMAL, "0.1000000000000000055511151231257827021181583404541015625")
        self.assertEqual(S.SUM_REPR, "0.30000000000000004")
        self.assertFalse(S.SUM_EQ)
        self.assertTrue(S.ISCLOSE and S.ABS_EPS)
        self.assertEqual(S.DEC_SUM, "0.3")
        self.assertTrue(S.P53_COLLIDE)
        self.assertEqual((S.SQ_FLOAT, S.SQ_EXACT), (100000007, 100000006))
        self.assertTrue(S.HALF_QUARTER)

    def test_normalize(self):
        self.assertEqual(S.NORM_SHIFT, 6)
        self.assertEqual(S.NORM_MANT, "0001110101")
        self.assertEqual(S.normalize_value(), (1 + Fraction(int(S.NORM_MANT, 2), 2 ** 10)) * 2 ** 6)

    def test_minus_six_point_five(self):
        sgn, E, e, m, val = S.decode(S.EX)
        self.assertEqual((sgn, E, e), (1, 1025, 2))
        self.assertEqual(m, "101" + "0" * 49)
        self.assertEqual(val, Fraction(-13, 2))
        self.assertEqual(Fraction(int(S.EX_BIN.replace(".", ""), 2), 2), Fraction(13, 2))

    def test_independent_encoder(self):
        for txt in ("0.1", "0.2", "0.3", "6.5", "1e-9", "123.456"):
            E, q = encode(Fraction(Decimal(txt)))
            _, e, m = S.float_bits(float(txt))
            self.assertEqual((E, q), (int(e, 2), int(m, 2)), txt)
        # 0.1 + 0.2：两个存储值的精确和再舍入一次
        E, q = encode(Fraction(0.1) + Fraction(0.2))
        _, e, m = S.float_bits(S.SUM)
        self.assertEqual((E, q), (int(e, 2), int(m, 2)))

    def test_tenth_cycle(self):
        steps = S.doubling_steps()
        self.assertEqual([y for y, _, _ in steps[:6]],
                         [Fraction(1, 5), Fraction(2, 5), Fraction(4, 5), Fraction(8, 5), Fraction(6, 5), Fraction(2, 5)])
        self.assertEqual(S.binary_expansion(n=13), "0001100110011")
        self.assertEqual(S.cycle_start(), (1, 4))          # 从 0.2 起，0011 循环
        err = S.stored_error("0.1")
        self.assertGreater(err, 0)
        self.assertAlmostEqual(float(err), 5.55e-18, delta=0.01e-18)
        self.assertGreater(S.stored_error("0.2"), 0)

    def test_sum_grid(self):
        self.assertEqual(S.ULP_03, 2.0 ** -54)
        self.assertAlmostEqual(S.ULP_03, 5.55e-17, delta=0.01e-17)
        self.assertLess(Fraction(S.LOWER), Fraction(3, 10))
        self.assertEqual(S.SUM, S.UPPER)
        self.assertTrue(S.sum_is_tie())
        self.assertTrue(S.is_even(S.UPPER))
        self.assertFalse(S.is_even(S.LOWER))

    def test_gap(self):
        self.assertEqual(S.NMANT + 1, 53)
        self.assertEqual(S.GAP_AT_P53, 2.0)
        self.assertEqual(S.SQ_EXACT ** 2 <= S.SQ_X < (S.SQ_EXACT + 1) ** 2, True)
        self.assertGreater(S.SQ_FLOAT ** 2, S.SQ_X)

    def test_narration_numbers(self):
        text = "".join(b["narration"] for b in json.loads(
            Path(__file__).with_name("float.json").read_text(encoding="utf-8"))["beats"])
        for s in ("一位符号，十一位指数，五十二位尾数", "负一点一零一乘二的二次方", "偏移量一千零二十三",
                  "存成一千零二十五", "零点二，零点四，零点八", "一点六，取一，剩零点六", "一点二，取一，剩零点二",
                  "零零一一无限循环", "五点五五乘十的负十八次方", "五点五五乘十的负十七次方",
                  "恰好落在两格正中间", "五十三位有效数字", "相邻两格相差二", "得到一亿零七，多了一",
                  "一亿零六", "左移六位", "二的六次方", "十的负九次方"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
