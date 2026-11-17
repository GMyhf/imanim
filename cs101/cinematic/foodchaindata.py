"""食物链片的数据层：讲义 W09 2.6 节 DSU 与 food_chain 原样 + 插桩版（逐句记录查了哪两对、连了哪三对、各结点归属）。

扩展域约定与讲义一致：动物 x（1-indexed 输入，减一后为 0-indexed）拆成三个结点——
x 同类域、x+n 猎物域（x 吃的那一类）、x+2n 天敌域（吃 x 的那一类）；两个结点同一集合 = 代表同一类动物。
片中主数据取讲义样例（n = 100，七句话，三句假话）。

补写（讲义没有）：food_chain_trace（插桩版，逻辑与讲义逐行相同，third=False 时故意删掉「x 吃 y」的第三对合并，
用来演示少连一对的后果）、groups / species_sets 等取快照的辅助函数。
"""
from __future__ import annotations

N = 100
SAMPLE = [(1, 101, 1), (2, 1, 2), (2, 2, 3), (2, 3, 3), (1, 1, 3), (2, 3, 1), (1, 5, 5)]   # 讲义样例
SHOW = [1, 2, 3]                     # 画面上画出三个域的动物（第七句的 5 只说不画）


# ------------------------------------------------------------------ 讲义原样
class DSU:
    """带路径压缩 + 按大小合并的并查集。
    单次操作近似 O(α(n))，α 是反阿克曼函数，实际上 ≤ 4。"""

    def __init__(self, n):
        self.parent = list(range(n))
        self.size = [1] * n
        self.count = n                    # 当前集合个数

    def find(self, x):
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:     # 第二趟做路径压缩（迭代，不怕深）
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False                  # 本来就在一组
        if self.size[rx] < self.size[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        self.size[rx] += self.size[ry]
        self.count -= 1
        return True

    def connected(self, x, y):
        return self.find(x) == self.find(y)


def food_chain(n, statements):
    """statements: (d, x, y)，d=1 表示同类，d=2 表示 x 吃 y。1-indexed 输入。
    返回假话条数。"""
    d = DSU(3 * n)
    lies = 0
    for kind, x, y in statements:
        if x < 1 or x > n or y < 1 or y > n:
            lies += 1
            continue
        x -= 1
        y -= 1
        if kind == 1:                                  # x 与 y 同类
            if d.connected(x, y + n) or d.connected(x, y + 2 * n):
                lies += 1
            else:
                d.union(x, y)
                d.union(x + n, y + n)
                d.union(x + 2 * n, y + 2 * n)
        else:                                          # x 吃 y
            # 假话：x 与 y 同类，或 y 反过来吃 x（x 落在 y 的猎物域）
            if x == y or d.connected(x, y) or d.connected(x, y + n):
                lies += 1
            else:
                d.union(x + n, y)                      # y 是 x 的猎物
                d.union(x, y + 2 * n)                  # x 是 y 的天敌
                d.union(x + 2 * n, y + n)              # x 的天敌是 y 的猎物
    return lies


# ------------------------------------------------------------------ 插桩版（补写）
def node(n, x, dom):
    """动物 x（1-indexed）的第 dom 个域（0 同类、1 猎物、2 天敌）在 DSU 里的下标。"""
    return (x - 1) + dom * n


def groups(d, n, animals=SHOW):
    """快照：{(动物, 域): 所在集合的根}；编号超过 n 的动物跳过。"""
    return {(a, k): d.find(node(n, a, k)) for a in animals if 1 <= a <= n for k in range(3)}


def food_chain_trace(n=N, statements=SAMPLE, third=True, animals=SHOW):
    """与讲义 food_chain 逐行相同的插桩版。每句话记一条：

    {"stmt", "lie", "why"（"range" / "self" / "check0" / "check1" / None）, "checks": [((动物, 域), (动物, 域), 是否连通)],
     "unions": [((动物, 域), (动物, 域), union 返回值)], "groups": 本句之后 animals 各结点的根, "count": 集合个数}
    检查按讲义 or 的短路顺序记录：前一项为真就不再查后一项。third=False 删掉「x 吃 y」的第三对合并。
    """
    d = DSU(3 * n)
    lies, log = 0, []
    for kind, x, y in statements:
        rec = {"stmt": (kind, x, y), "lie": False, "why": None, "checks": [], "unions": []}
        if x < 1 or x > n or y < 1 or y > n:
            lies += 1
            rec.update(lie=True, why="range")
        else:
            if kind == 1:
                pairs = [((x, 0), (y, 1)), ((x, 0), (y, 2))]
                todo = [((x, 0), (y, 0)), ((x, 1), (y, 1)), ((x, 2), (y, 2))]
            else:
                pairs = [((x, 0), (y, 0)), ((x, 0), (y, 1))]
                todo = [((x, 1), (y, 0)), ((x, 0), (y, 2)), ((x, 2), (y, 1))]
                if not third:
                    todo = todo[:2]
            if kind == 2 and x == y:
                rec.update(lie=True, why="self")
            else:
                for k, (p, q) in enumerate(pairs):
                    c = d.connected(node(n, *p), node(n, *q))
                    rec["checks"].append((p, q, c))
                    if c:
                        rec.update(lie=True, why=f"check{k}")
                        break
            if rec["lie"]:
                lies += 1
            else:
                for p, q in todo:
                    rec["unions"].append((p, q, d.union(node(n, *p), node(n, *q))))
        rec["groups"] = groups(d, n, animals)
        rec["count"] = d.count
        rec["lies"] = lies
        log.append(rec)
    return log


def lies_of(n=N, statements=SAMPLE, third=True):
    return food_chain_trace(n, statements, third)[-1]["lies"] if statements else 0


def species_sets(rec, animals=SHOW):
    """把一条记录里 animals 的 3×len 个结点按集合分组（每组按 (动物, 域) 排序，组按最小元素排序）。"""
    by = {}
    for key, r in rec["groups"].items():
        by.setdefault(r, []).append(key)
    return sorted(sorted(v) for v in by.values())


def lie_lines(n=N, statements=SAMPLE, third=True):
    """第几句（从 1 数）是假话。"""
    return [k + 1 for k, r in enumerate(food_chain_trace(n, statements, third)) if r["lie"]]


if __name__ == "__main__":
    print(food_chain(N, SAMPLE), lies_of(), lies_of(third=False), lie_lines(), lie_lines(third=False))
    for r in food_chain_trace():
        print(r["stmt"], r["lie"], r["why"], r["checks"], r["unions"], r["count"])
    print(species_sets(food_chain_trace()[2]))
    print(species_sets(food_chain_trace(third=False)[2]))
