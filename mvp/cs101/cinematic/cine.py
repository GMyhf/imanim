"""CS101 3B1B 风格短视频的公共骨架：配色、字体、beat 计时、画面字幕。

各片场景继承 Lesson：每个 beat 先调用 self.beat(id)，用 self.left() 给收尾动画定时长，
最后 self.finish()。make.py 通过环境变量 CINE_TIMING / CINE_MARKS 与场景交换时间轴。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from manim import *  # noqa: F403

BG = "#0f1117"
config.background_color = BG
FONT = os.environ.get("CINE_FONT", "Noto Sans CJK SC")
MONO = os.environ.get("CINE_MONO", "Noto Sans Mono CJK SC")
LEAD, TAIL = 0.35, 0.6          # 每个 beat：配音前留白 / 配音后留白（秒）
SUB_Y = -3.5                    # 字幕基线；画面内容不下探到 -3.0 以下

C_BLUE, C_TEAL, C_YELLOW = "#58C4DD", "#5CD0B3", "#F4D345"
C_RED, C_PURPLE, C_GREEN, C_GREY = "#FC6255", "#B48EE0", "#83C167", "#8A91A0"
NCOLOR = {1: C_GREY, 2: C_TEAL, 3: C_YELLOW, 4: C_RED, 5: C_PURPLE, 6: C_BLUE}


def T(s, size=36, color=WHITE, **kw):
    return Text(s, font=FONT, font_size=size, color=color, **kw)


def split_cue(c: dict, limit: int = 22) -> list[dict]:
    """长句按标点拆成短字幕，时间按字数比例分配。"""
    s = c["text"]
    if len(s) <= limit:
        return [c]
    mid = len(s) / 2
    cuts = [i + 1 for i, ch in enumerate(s[:-1]) if ch in "；，、：。"]
    if not cuts:
        return [c]
    k = min(cuts, key=lambda i: abs(i - mid))
    t = c["start"] + (c["end"] - c["start"]) * k / len(s)
    return (split_cue({"start": c["start"], "end": t, "text": s[:k]}, limit)
            + split_cue({"start": t, "end": c["end"], "text": s[k:]}, limit))


class Lesson(MovingCameraScene):
    """beat 计时 + 画面内字幕的公共骨架。"""

    def setup(self):
        super().setup()
        path = os.environ.get("CINE_TIMING")
        timing = json.loads(Path(path).read_text(encoding="utf-8")) if path else []
        self.dur = {t["id"]: t["seconds"] for t in timing}
        self.cues_by_beat = {t["id"]: [x for c in t["cues"] for x in split_cue(c)] for t in timing}
        self.marks, self.cur, self.t0 = {}, None, 0.0
        self.subs: list[Mobject] = []
        self.beat_cues: list[dict] = []

    @property
    def now(self) -> float:
        return self.renderer.time

    def _load_subs(self, cues: list[dict]):
        """字幕在 beat 开始时一次建好、常驻场景，只靠透明度切换。

        不能在动画中途增删子对象：Cairo 渲染器在每次 play 开始时就固定了要绘制的对象列表，
        中途换进来的字幕不画、换下去的还在画，会叠字。
        """
        self.clear_subs()
        self.beat_cues = cues
        for i, c in enumerate(cues):
            end = min(c["end"] + 0.15, cues[i + 1]["start"]) if i + 1 < len(cues) else c["end"] + 0.15
            m = T(c["text"].rstrip("。；，"), 30, "#D8DCE6").move_to([0, SUB_Y, 0]).set_opacity(0)
            m.add_updater(lambda mob, dt, a=c["start"], b=end: mob.set_opacity(
                float(np.clip(min(self.now - a, b - self.now) / 0.12, 0, 1))))
            self.subs.append(m)
        self.add(*self.subs)

    def clear_subs(self):
        self.remove(*self.subs)
        self.subs = []

    def beat(self, bid: str) -> float:
        """进入下一个 beat：先把上一个 beat 补足到配音结束，再记起点。返回本 beat 的配音时长。"""
        self._pad()
        self.cur, self.t0 = bid, self.now
        self.marks[bid] = self.t0
        base = self.t0 + LEAD
        self._load_subs([{**c, "start": base + c["start"], "end": base + c["end"]}
                         for c in self.cues_by_beat.get(bid, [])])
        self.wait(LEAD)
        return self.dur.get(bid, 8.0)

    def left(self) -> float:
        """本 beat 剩余的配音时间（用来给收尾动画定时长）。"""
        return max(0.0, self.t0 + LEAD + self.dur.get(self.cur, 8.0) - self.now)

    def _pad(self):
        if self.cur is None:
            return
        rem = self.t0 + LEAD + self.dur.get(self.cur, 8.0) + TAIL - self.now
        if rem > 1 / 60:
            self.wait(rem)

    def finish(self):
        self._pad()
        self.wait(0.8)
        out = os.environ.get("CINE_MARKS")
        if out:
            Path(out).write_text(json.dumps({**self.marks, "_lead": LEAD, "_total": self.now}, indent=1),
                                 encoding="utf-8")

    def cue_times(self) -> list[dict]:
        """当前 beat 的字幕句（绝对时间），供动画按句对齐。"""
        return self.beat_cues

    def wait_until(self, t: float):
        if t - self.now > 1 / 60:
            self.wait(t - self.now)

