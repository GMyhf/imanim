"""Pilot renderer for paired queue/stack traces. Driven only by plan.json."""
import json
import os
from pathlib import Path

from manim import (
    Scene, Text, VGroup, RoundedRectangle, Rectangle, Line, Arrow,
    FadeIn, FadeOut, Transform, Indicate, UP, DOWN, LEFT, RIGHT, config,
)

BG, INK, DIM = '#F5F7FB', '#16243A', '#596B82'
BLUE, ORANGE, RED = '#2463C7', '#B54E12', '#BB3042'


def label(text, size=28, color=INK, font='Hiragino Sans GB', max_width=None):
    obj = Text(text, font=font, font_size=size, color=color)
    if max_width and obj.width > max_width:
        obj.scale_to_fit_width(max_width)
    return obj


class StackQueue(Scene):
    def construct(self):
        self.camera.background_color = BG
        plan = json.loads(Path(os.environ['CS101_PLAN']).read_text(encoding='utf-8'))
        self.add(label('CS101  /  数据结构入门', 21, DIM).to_corner(UP + LEFT, buff=0.35))
        self.add(label('04099 · 队列和栈', 19, DIM).to_corner(UP + RIGHT, buff=0.35))
        self.add(Line([-6.7, 2.65, 0], [6.7, 2.65, 0], color='#DBE3EF'))
        self.add(label('来源：2020fall-cs101 · OpenJudge 04099', 16, DIM).move_to([0, -3.82, 0]))
        for name, y, color, rule in [('队列  QUEUE', 1.25, BLUE, '队首 ← 取出     右端加入 → 队尾'),
                                    ('栈  STACK', -0.85, ORANGE, '栈底                  栈顶：加入 / 取出')]:
            self.add(RoundedRectangle(width=7.8, height=1.8, corner_radius=0.18,
                     stroke_color='#D9E2EF', fill_color='#FFFFFF', fill_opacity=1).move_to([-2.6, y, 0]))
            self.add(label(name, 25, color).move_to([-4.65, y + .57, 0]))
            self.add(label(rule, 19, DIM).move_to([-2.65, y - .58, 0]))
        self.add(RoundedRectangle(width=4.65, height=3.9, corner_radius=.18,
                 stroke_color='#D9E2EF', fill_color='#EAF0F8', fill_opacity=1).move_to([4.1, .2, 0]))
        self.add(label('PYTHON · 当前操作', 22, BLUE).move_to([4.1, 1.83, 0]))
        self.add(Line([2, 1.5, 0], [6.2, 1.5, 0], color='#D1DBEA'))
        self.rows = {}
        for key, y, color in [('queue', 1.25, BLUE), ('stack', -.85, ORANGE)]:
            self.rows[key] = self.row([], y, color)
            self.add(self.rows[key])
        title = label('', 35)
        code = VGroup()
        caption = label('', 29)
        removed = VGroup()
        progress = Rectangle(width=.01, height=.045, stroke_width=0, fill_color=BLUE, fill_opacity=1)
        progress.move_to([-6.7, -3.98, 0])
        total = sum(s['seconds'] for s in plan['shots'])
        progress.add_updater(lambda m: m.stretch_to_fit_width(max(.01, 13.4 * min(self.time / total, 1)))
                             .move_to([-6.7 + m.width / 2, -3.98, 0]))
        self.add(progress)
        for shot in plan['shots']:
            start = self.time
            b = shot['visuals'][0]['props']
            self.remove(title, caption, code, *removed.submobjects)
            title = label(shot['title'], 35, max_width=12.8).move_to([0, 3.15, 0])
            caption = label(b['caption'], 30, BLUE, max_width=12.5).move_to([0, -2.35, 0])
            code = VGroup(*[label(line or ' ', 23, font='Menlo', max_width=4.15)
                            for line in b.get('code', '# 观察两个容器的变化').splitlines()])
            code.arrange(DOWN, aligned_edge=LEFT, buff=.16).move_to([4.1, .35, 0])
            self.add(title, caption, code)
            cue_objects = [(start + cue['start'], start + cue['end'],
                            label(cue['text'], 27, INK, max_width=12.8).move_to([0, -3.2, 0]))
                           for cue in shot['subtitles']]
            subtitle_layer = VGroup()
            def update_subtitles(layer, cues=cue_objects):
                active = next((obj for begin, end, obj in cues if begin <= self.time < end), None)
                if active is not None and list(layer.submobjects) != [active]:
                    layer.submobjects = [active]
                elif active is None:
                    layer.submobjects = []
            subtitle_layer.add_updater(update_subtitles)
            self.add(subtitle_layer)
            animations = []
            removed = VGroup()
            for key, y, color in [('queue', 1.25, BLUE), ('stack', -.85, ORANGE)]:
                old = self.rows[key]
                after = self.row(b['after'][key], y, color)
                if b['action'] in ('pop', 'empty_pop'):
                    value = b['removed'][key]
                    if value != 'error':
                        idx = 0 if key == 'queue' else len(b['before'][key]) - 1
                        flying = self.card(value, color).move_to([-4.9 + idx * 1.08, y, 0])
                        self.add(flying)
                        # Take the actual selected element out of the row before reflowing survivors.
                        old.remove(old[idx])
                        animations.append(flying.animate.move_to([.25, y, 0]))
                        removed.add(flying)
                        tag = label('取出', 17, color).move_to([.25, y + .5, 0])
                    else:
                        tag = label('error', 25, RED).move_to([.25, y, 0])
                    removed.add(tag)
                    animations.append(FadeIn(tag))
                animations.append(Transform(old, after))
            self.play(*animations, run_time=.85)
            if b['action'] == 'explain_queue':
                self.play(Indicate(self.rows['queue'], color=BLUE), run_time=.5)
            elif b['action'] == 'explain_stack':
                self.play(Indicate(self.rows['stack'], color=ORANGE), run_time=.5)
            left = start + shot['seconds'] - self.time
            if left > 1e-6:
                self.wait(left)
            self.remove(subtitle_layer)

    def card(self, value, color):
        return VGroup(RoundedRectangle(width=.85, height=.72, corner_radius=.1,
                      stroke_color=color, fill_color=color, fill_opacity=.10),
                      label(str(value), 32, color))

    def row(self, values, y, color):
        if not values:
            return VGroup(label('空', 24, DIM).move_to([-3, y, 0]))
        return VGroup(*[self.card(v, color).move_to([-4.9 + i * 1.08, y, 0])
                        for i, v in enumerate(values)])
