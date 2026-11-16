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


AUDIT_TEXT = (Text, MarkupText, Paragraph, MathTex, SingleStringMathTex, DecimalNumber)


def _family_points(m):
    return [x for x in m.get_family() if len(x.points)]


def _visible(m, thresh: float = 0.05) -> bool:
    for x in _family_points(m):
        f = x.fill_rgbas[:, 3].max() if len(getattr(x, "fill_rgbas", [])) else 0
        s = x.stroke_rgbas[:, 3].max() if len(getattr(x, "stroke_rgbas", [])) else 0
        if max(f, s) > thresh:
            return True
    return False


def _opaque(m) -> bool:
    rg = getattr(m, "fill_rgbas", None)
    return rg is not None and len(rg) and float(rg[:, 3].min()) >= 0.6 and m.width > 0.05 and m.height > 0.05


def _bbox(m):
    return (m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1])


def _area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _inter(a, b):
    return _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def _label(m) -> str:
    for attr in ("text", "tex_string"):
        v = getattr(m, attr, None)
        if isinstance(v, str) and v.strip():
            return v.strip()[:30]
    if isinstance(m, DecimalNumber):
        return f"数字 {m.get_value():g}"
    return f"{type(m).__name__}@({m.get_x():.1f},{m.get_y():.1f})"


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
        if not self._endcard():             # 有片尾卡时它的淡出就是收尾停顿
            self.wait(0.8)
        audit = os.environ.get("CINE_AUDIT")
        if audit:
            Path(audit).write_text(json.dumps(getattr(self, "audit_log", []), ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        out = os.environ.get("CINE_MARKS")
        if out:
            Path(out).write_text(json.dumps({**self.marks, "_lead": LEAD, "_total": self.now}, indent=1),
                                 encoding="utf-8")

    def _endcard(self):
        """约 3 秒静默片尾卡：「下一支：<标题>」+ 系列网址。

        make.py 经 CINE_ENDCARD 传 {"next": 标题或 null, "last": 是否本系列最后一支, "url": 系列网址}；
        没设这个变量（直接用 manim 渲染场景）就不加。起点记进 marks 的 _endcard。
        """
        raw = os.environ.get("CINE_ENDCARD")
        if not raw:
            return False
        info = json.loads(raw)
        self.clear_subs()
        self.cur = "_endcard"
        self.marks["_endcard"] = self.now
        frame = getattr(self.camera, "frame", None)
        rest = [m for m in self.mobjects if m is not frame]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=0.5, audit=False)
            self.remove(*rest)
        if frame is not None:                       # 场景里推拉过镜头的，片尾卡回到正中
            frame.move_to(ORIGIN).set(width=config.frame_width)
        parts = []
        if info.get("next"):
            head, _, tail = info["next"].partition("：")
            parts.append(T("下一支", 28, C_GREY))
            parts.append(T(head, 56, C_YELLOW))
            if tail:
                parts.append(T(tail, 34, WHITE))
        elif info.get("last"):
            parts.append(T("本系列完", 56, C_YELLOW))
            parts.append(T("回到目录，挑一支再看一遍", 30, C_GREY))
        card = VGroup(*parts).arrange(DOWN, buff=0.32).move_to([0, 0.6, 0]) if parts else VGroup()
        url = Text(info["url"], font=MONO, font_size=30, color=C_BLUE).move_to([0, -1.9 if parts else 0, 0])
        rule = Line([-2.2, 0, 0], [2.2, 0, 0], color=C_GREY, stroke_width=1.5).next_to(url, UP, buff=0.35)
        for m in (card, url):
            if m.width > config.frame_width - 1.2:
                m.scale_to_fit_width(config.frame_width - 1.2)
        self.play(FadeIn(card, shift=UP * 0.2), Create(rule), FadeIn(url), run_time=0.7)
        self.wait(1.5)
        self.play(FadeOut(VGroup(card, rule, url)), run_time=0.4, audit=False)
        return True

    # ------------------------------------------------------------ 画面自动检查
    def play(self, *args, audit: bool = True, **kwargs):
        """audit=False：这一段是故意的过渡（如同参节点合并、全屏波纹），结束状态不做画面检查。"""
        super().play(*args, **kwargs)
        if audit and os.environ.get("CINE_AUDIT"):
            self._audit()

    def _audit(self):
        """每段动画结束后按几何关系查四类问题：文字出画、文字互相重叠、文字被后画的不透明形状盖住、内容压字幕带。

        渲染顺序 = get_mobject_family_members() 的顺序（后画的盖在上面）。LaggedStart 把子对象重新加到
        场景最上层导致的遮挡（斐波那契片的教训）就靠第三条抓出来。
        """
        if not hasattr(self, "audit_log"):
            self.audit_log, self._audit_seen = [], set()
        fam = self.get_mobject_family_members()
        order = {id(m): i for i, m in enumerate(fam)}
        sub_ids = {id(x) for s in self.subs for x in s.get_family()}
        texts = []

        def collect(m):
            if id(m) in sub_ids:
                return
            if isinstance(m, AUDIT_TEXT):
                if _visible(m, 0.3):                    # 透明度 < 0.3 的文字当装饰（如片头背景），不查
                    texts.append(m)
                return
            for s in m.submobjects:
                collect(s)
        for m in self.mobjects:
            collect(m)
        hw, hh = config.frame_width / 2, config.frame_height / 2

        def note(kind, *objs):
            detail = " | ".join(o if isinstance(o, str) else _label(o) for o in objs)
            key = (self.cur, kind, detail)
            if key not in self._audit_seen:
                self._audit_seen.add(key)
                self.audit_log.append({"t": round(self.now, 2), "beat": self.cur, "kind": kind, "detail": detail})
        boxes = [(t, _bbox(t)) for t in texts]
        for t, (x0, y0, x1, y1) in boxes:
            if x0 < -hw + 0.03 or x1 > hw - 0.03 or y0 < -hh + 0.03 or y1 > hh - 0.03:
                note("出画", t, f"x∈[{x0:.2f},{x1:.2f}] y∈[{y0:.2f},{y1:.2f}]")
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i][1], boxes[j][1]
                inter = _inter(a, b)
                if inter > 0.2 * min(_area(a), _area(b)) and inter > 0.004:
                    note("文字重叠", boxes[i][0], boxes[j][0])
        tfam = {id(x) for t in texts for x in t.get_family()}
        shapes = [m for m in fam if id(m) not in tfam and id(m) not in sub_ids and len(m.points) and _opaque(m)]
        for t, tb in boxes:
            last = max(order.get(id(x), -1) for x in t.get_family())
            for s in shapes:
                if order[id(s)] > last and _inter(_bbox(s), tb) > 0.6 * _area(tb):
                    note("文字被遮挡", t)
                    break
        if any(_visible(s) for s in self.subs):
            for m in self.mobjects:
                if id(m) in sub_ids or not _visible(m):
                    continue
                if _bbox(m)[1] < SUB_Y + 0.3:
                    note("压字幕带", m)

    def cue_times(self) -> list[dict]:
        """当前 beat 的字幕句（绝对时间），供动画按句对齐。"""
        return self.beat_cues

    def wait_until(self, t: float):
        if t - self.now > 1 / 60:
            self.wait(t - self.now)

