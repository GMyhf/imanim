"""字典树片的数据：2026spring 树讲义附录 B「前缀树（Trie / 字典树）深度解析」的 Python 实现（TrieNode 用
word_count 代替 isEndOfWord；insert / search / starts_with / _delete_recursive 原样照搬），只在旁边加事件记录。
画面里结点的位置、插入时新建 / 复用的结点、查找走到哪一步停、删除时哪些结点被拆，全部从这里来。

结点在画面上用「从根到它的路径字符串」当名字：根是 ""，and 的 d 是 "and"。
"""
from __future__ import annotations

import random
import string


# ---------------------------------------------------------------- 讲义实现（原样）
class TrieNode:
    def __init__(self):
        self.children = [None] * 26
        # self.isEndOfWord = False  # 传统做法
        self.word_count = 0       # 在这个实现中，用 word_count 代替 isEndOfWord


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def _char_to_index(self, ch):
        """将字符映射到 0-25 的索引"""
        return ord(ch) - ord('a')

    def insert(self, word):
        """插入单词"""
        current = self.root
        for char in word:
            index = self._char_to_index(char)
            if not current.children[index]:
                current.children[index] = TrieNode()
            current = current.children[index]
        # 标记单词结束
        current.word_count += 1

    def search(self, word):
        """搜索完整单词是否存在"""
        current = self.root
        for char in word:
            index = self._char_to_index(char)
            if not current.children[index]:
                return False
            current = current.children[index]
        return current.word_count > 0

    def starts_with(self, prefix):
        """检查是否存在以给定前缀开头的单词"""
        current = self.root
        for char in prefix:
            index = self._char_to_index(char)
            if not current.children[index]:
                return False
            current = current.children[index]
        return True

    def delete(self, word):
        """删除单词（简化逻辑版）"""
        return self._delete_recursive(self.root, word, 0)

    def _delete_recursive(self, current, word, index):
        if index == len(word):
            if current.word_count == 0:
                return False  # 单词不存在
            current.word_count -= 1
            # 如果没有子节点，说明可以被父节点物理删除
            return all(child is None for child in current.children)
        char_idx = self._char_to_index(word[index])
        node = current.children[char_idx]
        if not node:
            return False
        should_delete_child = self._delete_recursive(node, word, index + 1)
        if should_delete_child:
            current.children[char_idx] = None
            # 如果当前节点不再是单词结尾，且没有其他子节点，则继续向上删除
            return current.word_count == 0 and all(child is None for child in current.children)
        return False


# 讲义测试代码里的六个词
WORDS = ["and", "ant", "do", "geek", "dad", "ball"]


# ---------------------------------------------------------------- 插桩：把讲义 Trie 的状态读成画面用的数据
def snapshot(trie: Trie) -> dict:
    """路径名 → word_count，按字典序（深度优先、孩子按 a..z）排列。"""
    out = {}

    def go(node, path):
        out[path] = node.word_count
        for i, c in enumerate(node.children):
            if c is not None:
                go(c, path + chr(ord('a') + i))
    go(trie.root, "")
    return out


def insert_trace(trie: Trie, word: str) -> list:
    """插入前先看路径上每一步是复用还是新建，再调用讲义的 insert。返回 [(路径名, 'reuse'|'new')]。"""
    steps, cur = [], trie.root
    for k, ch in enumerate(word):
        i = trie._char_to_index(ch)
        nxt = cur.children[i]
        steps.append((word[:k + 1], "reuse" if nxt is not None else "new"))
        cur = nxt if nxt is not None else None
        if cur is None:
            steps += [(word[:j + 1], "new") for j in range(k + 1, len(word))]
            break
    trie.insert(word)
    return steps


def search_trace(trie: Trie, word: str) -> tuple:
    """沿路走：返回 (走到的路径名列表, 在哪一步断了（None 表示走完）, 讲义 search 的结果, starts_with 的结果)。"""
    path, cur = [], trie.root
    broke = None
    for k, ch in enumerate(word):
        nxt = cur.children[trie._char_to_index(ch)]
        if nxt is None:
            broke = k
            break
        cur = nxt
        path.append(word[:k + 1])
    return path, broke, trie.search(word), trie.starts_with(word)


def steps_to_find(trie: Trie, word: str) -> int:
    """查找走过的结点数（逐字比较的次数）。"""
    path, broke, _, _ = search_trace(trie, word)
    return len(path) + (1 if broke is not None else 0)


def complete(trie: Trie, prefix: str) -> list:
    """自动补全：走到前缀结点，再深度优先（孩子按 a..z）收集 word_count > 0 的路径——天然字典序。"""
    cur = trie.root
    for ch in prefix:
        cur = cur.children[trie._char_to_index(ch)]
        if cur is None:
            return []
    out = []

    def go(node, path):
        if node.word_count > 0:
            out.append(path)
        for i, c in enumerate(node.children):
            if c is not None:
                go(c, path + chr(ord('a') + i))
    go(cur, prefix)
    return out


def delete_trace(trie: Trie, word: str) -> list:
    """调用讲义的 delete，前后对比快照，返回被物理删除的结点（从深到浅）。"""
    before = snapshot(trie)
    trie.delete(word)
    after = snapshot(trie)
    return sorted((p for p in before if p not in after), key=len, reverse=True)


def build(words=WORDS) -> Trie:
    t = Trie()
    for w in words:
        t.insert(w)
    return t


def random_dictionary(n: int, seed: int = 2026, must=("ant",)) -> list:
    rng = random.Random(seed)
    out = set(must)
    while len(out) < n:
        out.add("".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(2, 9))))
    return sorted(out)


# ---------------------------------------------------------------- 画面要用的数
_t = Trie()
INSERTS = [(w, insert_trace(_t, w)) for w in WORDS]       # 每个词插入时的新建 / 复用
FULL = snapshot(_t)                                       # 六个词插完的整棵树
N_NODES = len(FULL)                                       # 含根：17
N_CHARS = sum(len(w) for w in WORDS)                      # 19
SLOTS = N_NODES * 26                                      # 442
USED = N_NODES - 1                                        # 用到的指针格 = 非根结点数：16
ROOT_KIDS = [p for p in FULL if len(p) == 1]              # a b d g
SEARCH = {w: search_trace(_t, w) for w in ("do", "bat", "an")}
COMPLETE = {p: complete(_t, p) for p in ("an", "d")}
DICT_SIZES = (6, 600, 60000)
STEPS_ANT = {n: steps_to_find(build(random_dictionary(n) if n != 6 else WORDS), "ant") for n in DICT_SIZES}
_d = build()
DEL_GEEK = delete_trace(_d, "geek")                       # geek gee ge g
DEL_ANT = delete_trace(_d, "ant")                         # ant
