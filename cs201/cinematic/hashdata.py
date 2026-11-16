"""散列表片的数据：讲义代码原样 + 插桩轨迹。画面和旁白里的每个数字都从这里来。

出处：2026spring-cs201 讲义 20250520_HashTable.md（1.3 处理冲突、1.5 HashTable 类、练习 17968 / 17975、
链地址法例题）；dsa-modernization book/ch10-search.md 10.3.3 聚集、10.3.5 效率分析（ASL 公式与表）。
"""
from __future__ import annotations


# ---------------------------------------------------------------- 讲义原样：1.5 节 HashTable（线性探测，"加 1" 再散列）
class HashTable:
    def __init__(self):
        self.size = 11
        self.slots = [None] * self.size
        self.data = [None] * self.size

    def put(self,key,data):
        hashvalue = self.hashfunction(key,len(self.slots))

        if self.slots[hashvalue] == None:
            self.slots[hashvalue] = key
            self.data[hashvalue] = data
        else:
            if self.slots[hashvalue] == key:
                self.data[hashvalue] = data #replace
            else:
                nextslot = self.rehash(hashvalue,len(self.slots))
                while self.slots[nextslot] != None and self.slots[nextslot] != key:
                    nextslot = self.rehash(nextslot,len(self.slots))

                if self.slots[nextslot] == None:
                    self.slots[nextslot] = key
                    self.data[nextslot] = data
                else:
                    self.data[nextslot] = data #replace

    def hashfunction(self,key,size):
        return key%size

    def rehash(self,oldhash,size):
        return (oldhash+1)%size

    def get(self,key):
        startslot = self.hashfunction(key,len(self.slots))

        data = None
        stop = False
        found = False
        position = startslot
        while self.slots[position] != None and not found and not stop:
                if self.slots[position] == key:
                    found = True
                    data = self.data[position]
                else:
                    position=self.rehash(position,len(self.slots))
                    if position == startslot:
                        stop = True
        return data

    def __getitem__(self,key):
        return self.get(key)

    def __setitem__(self,key,data):
        self.put(key,data)


# ---------------------------------------------------------------- 讲义原样：练习 17968（线性探查）
def insert_hash_table(keys, M):
    table = [0.5] * M  # 用 0.5 表示空位
    result = []

    for key in keys:
        index = key % M
        i = index

        while True:
            if table[i] == 0.5 or table[i] == key:
                result.append(i)
                table[i] = key
                break
            i = (i + 1) % M

    return result


# ---------------------------------------------------------------- 讲义原样：练习 17975（二次探查，去掉 stdin 读入）
def quadratic(num_list, m):
    mylist = [0.5] * m

    def generate_result():
        for num in num_list:
            pos = num % m
            current = mylist[pos]
            if current == 0.5 or current == num:
                mylist[pos] = num
                yield pos
            else:
                sign = 1
                cnt = 1
                while True:
                    now = pos + sign * (cnt ** 2)
                    current = mylist[now % m]
                    if current == 0.5 or current == num:
                        mylist[now % m] = num
                        yield now % m
                        break
                    sign *= -1
                    if sign == 1:
                        cnt += 1

    return list(generate_result())


# ---------------------------------------------------------------- 插桩：探查路径
def linear_paths(keys, m):
    """线性探测插入，每个关键字的探查路径（依次看过的槽，最后一个是落点）。"""
    table = [None] * m
    paths = []
    for k in keys:
        p = k % m
        path = [p]
        while table[p] is not None and table[p] != k:
            p = (p + 1) % m
            path.append(p)
        table[p] = k
        paths.append(path)
    return paths, table


def quad_paths(keys, m):
    """二次探测插入（增量 1², −1², 2², −2², …），每个关键字的探查路径与增量。"""
    table = [None] * m
    paths, incs = [], []
    for k in keys:
        h = k % m
        path, inc = [h], [0]
        cnt, sign = 1, 1
        while table[path[-1]] is not None and table[path[-1]] != k:
            d = sign * cnt * cnt
            path.append((h + d) % m)
            inc.append(d)
            sign = -sign
            if sign == 1:
                cnt += 1
        table[path[-1]] = k
        paths.append(path)
        incs.append(inc)
    return paths, incs, table


def lookup_path(table, key):
    """HashTable.get 的探查：依次比较过的槽，及是否找到。遇到空槽停（空槽不算一次比较）。"""
    m = len(table)
    start = pos = key % m
    seen = []
    while table[pos] is not None:
        seen.append(pos)
        if table[pos] == key:
            return seen, True
        pos = (pos + 1) % m
        if pos == start:
            break
    return seen, False


def next_slot_odds(table):
    """线性探测下，下一个关键字（基地址等概率）最终落到每个空槽的概率（分子，分母为表长）。"""
    m = len(table)
    odds = {}
    for h in range(m):
        p = h
        while table[p] is not None:
            p = (p + 1) % m
        odds[p] = odds.get(p, 0) + 1
    return odds


def chains(keys, m):
    out = [[] for _ in range(m)]
    for k in keys:
        out[k % m].append(k)
    return out


def asl_linear_hit(a):
    return 0.5 * (1 + 1 / (1 - a))


def asl_chain_hit(a):
    return 1 + a / 2


# ---------------------------------------------------------------- 片中用到的例子
KEYS = [54, 26, 93, 17, 77, 31, 44, 55, 20]                  # 讲义 1.5 节插入顺序
M = 11
PATHS, TABLE = linear_paths(KEYS, M)
DIRECT = [k for k, p in zip(KEYS, PATHS) if len(p) == 1]
COLLIDED = [(k, p) for k, p in zip(KEYS, PATHS) if len(p) > 1]
ODDS = next_slot_odds(TABLE)
FIND20, _ = lookup_path(TABLE, 20)
FIND99, FOUND99 = lookup_path(TABLE, 99)
LOAD_N = sum(x is not None for x in TABLE)

Q_KEYS, Q_M = [24, 13, 35, 15, 14], 11                     # 练习 17975 样例
Q_PATHS, Q_INCS, Q_TABLE = quad_paths(Q_KEYS, Q_M)
QL_PATHS, QL_TABLE = linear_paths(Q_KEYS, Q_M)              # 同一组关键字改用线性探测

C_KEYS, C_M = [19, 14, 23, 1, 68, 20, 84, 27, 55, 11, 10, 79], 13   # 链地址法例题
CHAINS = chains(C_KEYS, C_M)

ASL_POINTS = [0.5, 0.8, 0.9]

if __name__ == "__main__":
    print(TABLE, PATHS)
    print("direct", DIRECT, "collided", COLLIDED)
    print("odds", ODDS, "find20", FIND20, "find99", FIND99, FOUND99, "load", LOAD_N)
    print("quad", Q_PATHS, Q_INCS, [p[-1] for p in Q_PATHS], "linear", QL_PATHS)
    print("chains", CHAINS)
    print([(a, asl_linear_hit(a), asl_chain_hit(a)) for a in ASL_POINTS])
