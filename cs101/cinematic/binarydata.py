"""二进制与补码片的数据层：讲义 4.1–4.3 节的代码原样插桩，片中每个数字都从这里取。

讲义：计算概论（B）2026fall 第 3 周 计算机原理（1/2）第 4 节（课件 P26–P37）。
- 4.1 除基取余（233 → 1110 1001）、按权展开、四位一组成十六进制；
- 4.2 原码 / 反码 / 补码（以 8 位 −5 为例）、to_twos_complement、add8 / to_signed8 三道例题、5 − 7、127 + 1 溢出；
- 4.3 ~6 == −7、n & (n − 1) 清掉最低位的 1。
"""
from __future__ import annotations

BITS = 8
MASK = (1 << BITS) - 1          # 0xFF：讲义「(1 << 8) - 1 = 0xFF = 8 个 1」


# ------------------------------------------------------------------ 4.1 进制
def div_steps(n: int, base: int = 2) -> list[tuple[int, int, int]]:
    """讲义 E02734 手写除基取余插桩：返回 [(被除数, 商, 余数)]，余数从最低位到最高位。"""
    steps = []
    while n > 0:
        steps.append((n, n // base, n % base))
        n //= base
    return steps


def from_remainders(steps) -> str:
    """余数逆序读。"""
    return "".join(str(r) for _, _, r in reversed(steps)) or "0"


def weights(bits: str) -> list[int]:
    """按权展开：值为 1 的那些位的位置量（从高到低）。"""
    n = len(bits)
    return [1 << (n - 1 - i) for i, b in enumerate(bits) if b == "1"]


def hex_groups(bits: str) -> list[tuple[str, str]]:
    """从最低位起四位一组（最左一组不足补 0）→ [(四位串, 十六进制数字)]。"""
    pad = (-len(bits)) % 4
    s = "0" * pad + bits
    return [(s[i:i + 4], "0123456789abcdef"[int(s[i:i + 4], 2)]) for i in range(0, len(s), 4)]


# ------------------------------------------------------------------ 4.2 原码 / 反码 / 补码
def to_twos_complement(x, bits=8):
    """讲义原样。"""
    return format(x & ((1 << bits) - 1), f'0{bits}b')


def sign_magnitude(x, bits=8) -> str:
    """原码：最高位当符号位。"""
    return ("1" if x < 0 else "0") + format(abs(x), f"0{bits - 1}b")


def ones_complement(x, bits=8) -> str:
    """反码：负数为原码除符号位外取反。"""
    s = sign_magnitude(x, bits)
    if x >= 0:
        return s
    return "1" + "".join("1" if c == "0" else "0" for c in s[1:])


def invert(bits: str) -> str:
    return "".join("1" if c == "0" else "0" for c in bits)


def neg_steps(x: int, bits=8) -> tuple[str, str, str]:
    """负数补码的手算三步：|x| 的二进制 → 取反 → 加一。返回三串位。"""
    pos = format(abs(x), f"0{bits}b")
    inv = invert(pos)
    plus = format((int(inv, 2) + 1) & ((1 << bits) - 1), f"0{bits}b")
    return pos, inv, plus


def add8(a, b):
    """讲义原样：只保留低 8 位，最高位的进位被丢掉。"""
    return (a + b) & 0xFF


def to_signed8(u):
    """讲义原样：把 8 位串按补码解读。"""
    return u - 256 if u >= 128 else u


def add8_trace(a: int, b: int) -> dict:
    """逐位相加的过程（无符号 8 位串 a、b）：各位进位、是否有丢掉的最高位进位、结果。"""
    carry, carries = 0, []
    for i in range(BITS):
        s = ((a >> i) & 1) + ((b >> i) & 1) + carry
        carry = s >> 1
        carries.append(carry)
    r = add8(a, b)
    return {"a": format(a, "08b"), "b": format(b, "08b"), "r": format(r, "08b"),
            "carries": carries, "dropped": carries[-1] == 1,
            "sa": to_signed8(a), "sb": to_signed8(b), "sr": to_signed8(r)}


COURSE_ADDS = [(0b00010001, 0b00010110), (0b00011000, 0b11101111), (0b01111111, 0b00000011)]
SUB_EXAMPLE = (5, 7)            # 讲义「算 5 − 7」
RANGE8 = (-(1 << (BITS - 1)), (1 << (BITS - 1)) - 1)
INT32_MAX = (1 << 31) - 1


def c_int32(v: int) -> int:
    """模拟讲义 ctypes.c_int32(v).value：截成 32 位补码。"""
    v &= (1 << 32) - 1
    return v - (1 << 32) if v >= (1 << 31) else v


def wheel_pos(x: int, bits=8) -> int:
    """数 x 的补码在 2^bits 格圆环上的位置（= 当无符号数读的值）。"""
    return x & ((1 << bits) - 1)


# ------------------------------------------------------------------ 4.3 位运算
def clear_lowbit(n: int) -> int:
    return n & (n - 1)


def is_pow2(n: int) -> bool:
    return n > 0 and n & (n - 1) == 0


# ------------------------------------------------------------------ 片中用到的数
N = 233
TITLE_BITS = format(N, "08b")                    # 11101001
TITLE_SIGNED = to_signed8(N)                     # −23
NEG5 = {"原码": sign_magnitude(-5), "反码": ones_complement(-5), "补码": to_twos_complement(-5)}


def quiz() -> list[dict]:
    """建议的小测题（答案全部由上面的函数算出）。"""
    def num(v):
        return str(v).replace("-", "−")
    q1 = to_signed8(0b11111110)
    q2 = to_twos_complement(-7)
    t = add8_trace(0b01111111, 0b00000011)
    opts1 = [num(q1), "254", "−126", "2"]
    opts2 = [q2, "10000111", "11111000", "00000111"]
    opts3 = [num(t["sr"]), "130", "−127", "2"]
    return [
        {"q": "8 位补码 1111 1110 表示的整数是多少？", "options": opts1, "answer": opts1.index(num(q1)),
         "explain": "最高位是 1，是负数；再取一次补码：取反 0000 0001，加一 0000 0010 = 2，所以是 −2。"},
        {"q": "−7 的 8 位补码是哪一个？", "options": opts2, "answer": opts2.index(q2),
         "explain": "7 = 0000 0111，取反 1111 1000，再加一得 1111 1001。10000111 是原码，11111000 是反码。"},
        {"q": "8 位补码下计算 0111 1111 + 0000 0011（127 + 3），结果按补码读是多少？",
         "options": opts3, "answer": opts3.index(num(t["sr"])),
         "explain": f"结果位串 {t['r']}，最高位为 1；130 超出 −128 ~ 127，发生上溢，读出来是 {num(t['sr'])}。"},
    ]
