"""链表片的数据：讲义附录 A 的模板代码原样搬来，另写插桩版逐步记录指针位置，画面与旁白里的数字都从这里来。

讲义：数据结构与算法（B）2026fall 第 2 周《线性表》附录 A——E21 合并（哨兵）、E206 三指针反转、
E234 快慢指针找中点、E141/M142 Floyd 判圈与求环入口。test_linked.py 用 Python 列表、访问集合等独立做法对撞。
"""
from __future__ import annotations


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def build(vals, cycle_at=None):
    """按值建链表；cycle_at 给出时，尾结点接回第 cycle_at 个（0 起）结点，返回 (head, nodes)。"""
    nodes = [ListNode(v) for v in vals]
    for a, b in zip(nodes, nodes[1:]):
        a.next = b
    if cycle_at is not None and nodes:
        nodes[-1].next = nodes[cycle_at]
    return (nodes[0] if nodes else None), nodes


def to_list(head, limit=10_000):
    out = []
    while head and len(out) < limit:
        out.append(head.val)
        head = head.next
    return out


# ------------------------------------------------------------------ 讲义原版（附录 A 2.2 / 4.1 / 5.2 / M142）
class Solution:
    def reverseList(self, head: ListNode) -> ListNode:
        prev, curr = None, head
        while curr:
            nxt = curr.next     # ① 断链前先存后继（铁律 2）
            curr.next = prev    # ② 掉头
            prev = curr         # ③ prev 前进
            curr = nxt          # ④ curr 前进
        return prev             # curr 为 None 时，prev 是新表头

    def mergeTwoLists(self, list1: ListNode, list2: ListNode) -> ListNode:
        dummy = ListNode(0)      # 哨兵：不存数据，只为省掉分支
        tail = dummy
        while list1 and list2:
            if list1.val <= list2.val:   # ★ 用 <= 保证稳定性（相等时优先取 list1）
                tail.next = list1
                list1 = list1.next
            else:
                tail.next = list2
                list2 = list2.next
            tail = tail.next
        tail.next = list1 if list1 else list2   # 剩下那条整体挂上，不必逐个搬
        return dummy.next

    def middle(self, head: ListNode) -> ListNode:
        # 3. 快慢指针找中点 —— E234 / E876 / M148
        slow = fast = head
        while fast and fast.next:
            slow, fast = slow.next, fast.next.next
        return slow

    def hasCycle(self, head: ListNode) -> bool:
        # 4. 快慢指针判环 —— E141 / M142（Floyd 判圈）
        slow = fast = head
        while fast and fast.next:
            slow, fast = slow.next, fast.next.next
            if slow is fast: return True
        return False

    def detectCycle(self, head: ListNode) -> ListNode:
        # M142：模板 4 相遇后，一个指针回表头，两个都一步一步走，再相遇处就是环入口
        slow = fast = head
        while fast and fast.next:
            slow, fast = slow.next, fast.next.next
            if slow is fast:
                p = head
                while p is not slow:
                    p, slow = p.next, slow.next
                return p
        return None


# ------------------------------------------------------------------ 插桩版：画面逐步驱动
MERGE_A, MERGE_B = [1, 2, 4], [1, 3, 4]      # 讲义 E21 示例
REV = [1, 2, 3, 4, 5]                         # 讲义 E206 示例
CYC_VALS = list(range(1, 11))                 # 判圈示例：10 个结点
CYC_AT = 3                                    # 尾结点接回第 4 个（下标 3）：环外 3 个，环长 7


def merge_trace(a=MERGE_A, b=MERGE_B):
    """事件：("take", 'A'|'B', 下标, 值) 每次把一个结点接到 tail 后；("rest", 'A'|'B', 起始下标) 剩余整段挂上。"""
    ev, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            ev.append(("take", "A", i, a[i]))
            i += 1
        else:
            ev.append(("take", "B", j, b[j]))
            j += 1
    if i < len(a):
        ev.append(("rest", "A", i))
    elif j < len(b):
        ev.append(("rest", "B", j))
    return ev


def reverse_trace(vals=REV):
    """每轮四个动作后的 (prev, curr, nxt) 下标（None 记 -1），以及当轮被掉头的结点。"""
    head, nodes = build(vals)
    idx = {id(n): k for k, n in enumerate(nodes)}
    pos = lambda n: -1 if n is None else idx[id(n)]  # noqa: E731
    prev, curr, rounds = None, head, []
    while curr:
        nxt = curr.next
        curr.next = prev
        flipped = pos(curr)
        prev = curr
        curr = nxt
        rounds.append({"flip": flipped, "prev": pos(prev), "curr": pos(curr), "nxt": pos(nxt)})
    return to_list(prev), rounds


def middle_trace(n):
    """快慢指针找中点：每轮后 (slow, fast) 的位置（1 起；fast 跑出链表记 None）。"""
    head, nodes = build(list(range(1, n + 1)))
    idx = {id(x): k + 1 for k, x in enumerate(nodes)}
    slow = fast = head
    steps = [(1, 1)]
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        steps.append((idx[id(slow)], idx[id(fast)] if fast else None))
    return steps


def floyd_trace(vals=CYC_VALS, at=CYC_AT):
    """判圈 + 求环入口：phase1 每步 (slow, fast) 下标直到相遇；phase2 每步 (p, slow) 直到相遇。"""
    head, nodes = build(vals, at)
    idx = {id(x): k for k, x in enumerate(nodes)}
    slow = fast = head
    p1 = [(0, 0)]
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        p1.append((idx[id(slow)], idx[id(fast)]))
        if slow is fast:
            break
    p = head
    p2 = [(idx[id(p)], idx[id(slow)])]
    while p is not slow:
        p, slow = p.next, slow.next
        p2.append((idx[id(p)], idx[id(slow)]))
    meet = p1[-1][0]
    a = at                         # 环外结点数（表头到入口的步数）
    L = len(vals) - at             # 环长
    b = (meet - at) % L            # 入口到相遇点的步数
    return {"phase1": p1, "phase2": p2, "meet": meet, "entry": p2[-1][0], "a": a, "L": L, "b": b,
            "slow_steps": len(p1) - 1}


if __name__ == "__main__":
    print(merge_trace())
    print(reverse_trace())
    for n in (5, 6):
        print(n, middle_trace(n))
    print(floyd_trace())
