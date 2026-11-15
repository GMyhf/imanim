"""Plan-driven grid-search and dynamic-programming visualizations."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene import label, BG, INK, DIM, BLUE, ORANGE
from manim import Scene, VGroup, RoundedRectangle, Rectangle, Line, ReplacementTransform, UP, LEFT, RIGHT, DOWN

GREEN, GOLD = '#16734C', '#B27A00'
PALETTE = (BLUE, ORANGE, GREEN)


class AlgorithmLesson(Scene):
    kind = ''

    def construct(self):
        self.camera.background_color = BG
        plan = json.loads(Path(os.environ['CS101_PLAN']).read_text(encoding='utf-8'))
        number = '18108 · 池塘数目' if self.kind == 'search' else '02760 · 数字三角形'
        self.add(label('CS101  /  算法入门', 21, DIM).to_corner(UP + LEFT, buff=.35),
                 label(number, 19, DIM).to_corner(UP + RIGHT, buff=.35),
                 Line([-6.7, 2.65, 0], [6.7, 2.65, 0], color='#DBE3EF'),
                 label('来源：2020fall-cs101 · ' + number, 16, DIM).move_to([0, -3.82, 0]))
        self.add(RoundedRectangle(width=7.9, height=4.45, corner_radius=.18,
                 stroke_color='#D9E2EF', fill_color='#FFFFFF', fill_opacity=1).move_to([-2.65, .15, 0]),
                 RoundedRectangle(width=4.65, height=4.45, corner_radius=.18,
                 stroke_color='#D9E2EF', fill_color='#EAF0F8', fill_opacity=1).move_to([4.1, .15, 0]),
                 label('PYTHON · 算法步骤', 22, BLUE).move_to([4.1, 2.05, 0]),
                 Line([2, 1.73, 0], [6.2, 1.73, 0], color='#D1DBEA'))
        progress = Rectangle(width=.01, height=.045, stroke_width=0, fill_color=BLUE, fill_opacity=1)
        total = sum(s['seconds'] for s in plan['shots'])
        progress.add_updater(lambda m: m.stretch_to_fit_width(max(.01, 13.4 * min(self.time / total, 1)))
                             .move_to([-6.7 + m.width / 2, -3.98, 0]))
        self.add(progress)
        previous = None
        for shot in plan['shots']:
            start = self.time
            b = shot['visuals'][0]['props']
            title = label(shot['title'], 34, max_width=12.7).move_to([0, 3.15, 0])
            caption = label(b['caption'], 28, BLUE, max_width=12.8).move_to([0, -2.53, 0])
            code = VGroup()
            advance = label('MM', 20, font='Menlo').width - label('M', 20, font='Menlo').width
            for row, line in enumerate(b['code'].splitlines()):
                indent = len(line) - len(line.lstrip(' '))
                text = label(line.lstrip(' ') or ' ', 20, font='Menlo')
                text.move_to([indent * advance + text.width / 2, -row * .32, 0])
                code.add(text)
            if code.width > 4.15:
                code.scale_to_fit_width(4.15)
            code.move_to([4.1, .65, 0])
            self.add(title, caption, code)
            cues = [(start + c['start'], start + c['end'],
                     label(c['text'], 27, max_width=12.8).move_to([0, -3.2, 0]))
                    for c in shot['subtitles']]
            layer = VGroup()
            def subtitles(m, cues=cues):
                active = next((obj for a, z, obj in cues if a <= self.time < z), None)
                m.submobjects = [active] if active is not None else []
            layer.add_updater(subtitles)
            self.add(layer)
            display, formula = None, None
            states = b['states']
            for index, state in enumerate(states):
                at = start + .6 + index * (shot['seconds'] - 1.8) / len(states)
                if self.time < at:
                    self.wait(at - self.time)
                new = self.grid(state, b) if self.kind == 'search' else self.triangle(state, b)
                if display is None:
                    if previous is not None:
                        self.remove(previous)
                    display = new
                    self.add(display)
                else:
                    self.play(ReplacementTransform(display, new), run_time=.6)
                    display = new
                if formula is not None:
                    self.remove(formula)
                formula = self.detail(state, b)
                self.add(formula)
            remaining = start + shot['seconds'] - self.time
            if remaining > 0:
                self.wait(remaining)
            self.remove(title, caption, code, formula, layer)
            previous = display

    def grid(self, state, beat):
        grid = state['grid']
        rows, cols = len(grid), len(grid[0])
        groups = {(r, c): k for r, c, k in state['groups']}
        current = tuple(state['current']) if state['current'] is not None else None
        result = VGroup()
        center_x, center_y, step = -3.2, .42, .78
        for r, row in enumerate(grid):
            for c, value in enumerate(row):
                p = (r, c)
                known = p in groups
                color = PALETTE[(groups[p] - 1) % 3] if known else '#7B8FA8' if value == 'W' else '#DCE3ED'
                diagonal = beat.get('diagonal') and p in ((0, 0), (1, 1))
                tile = RoundedRectangle(width=.68, height=.68, corner_radius=.08,
                       stroke_color=GOLD if p == current or diagonal else color,
                       stroke_width=4 if p == current or diagonal else 2,
                       fill_color=color, fill_opacity=.23 if known else .09 if value == 'W' else .4)
                text = label(value, 27, color if value == 'W' else DIM)
                pos = [center_x + (c - (cols - 1) / 2) * step,
                       center_y + ((rows - 1) / 2 - r) * step, 0]
                result.add(VGroup(tile, text).move_to(pos))
        for r in range(rows):
            result.add(label(str(r), 17, DIM).move_to([center_x - (cols + 1) / 2 * step,
                       center_y + ((rows - 1) / 2 - r) * step, 0]))
        for c in range(cols):
            result.add(label(str(c), 17, DIM).move_to([center_x + (c - (cols - 1) / 2) * step,
                       center_y + (rows + 1) / 2 * step, 0]))
        result.add(label('池塘数', 22, DIM).move_to([.05, 1.22, 0]),
                   label(str(state['count']), 45, BLUE).move_to([.05, .65, 0]),
                   label('已发现', 18, DIM).move_to([.05, -.15, 0]),
                   label(str(len(groups)) + ' 格', 26, BLUE).move_to([.05, -.62, 0]))
        pending = ' → '.join(f'({r},{c})' for r, c in state['queue']) or '空'
        result.add(label('待处理队列：' + pending, 22, INK, max_width=7.3).move_to([-2.65, -1.75, 0]))
        return result

    def triangle(self, state, beat):
        a, best, known = state['triangle'], state['best'], state['known']
        path = state.get('path', []) if beat.get('path') else []
        if beat.get('greedy'):
            path = [[0, 0], [1, 1], [2, 1], [3, 1], [4, 1]]
        path_set = {tuple(p) for p in path}
        current = tuple(state['cell']) if state['cell'] else None
        children = {tuple(p) for p in state['children']}
        chosen = tuple(state['chosen']) if state['chosen'] else None
        def pos(r, c):
            return [-2.65 + (c - r / 2) * 1.28, 1.88 - r * .78, 0]
        result = VGroup()
        for r in range(len(a) - 1):
            for c in range(len(a[r])):
                for child in ((r + 1, c), (r + 1, c + 1)):
                    parent_xy, child_xy = pos(r, c), pos(*child)
                    parent_xy[1] -= .32
                    child_xy[1] += .32
                    on_path = (r, c) in path_set and child in path_set
                    selected = not path and (r, c) == current and child == chosen
                    result.add(Line(parent_xy, child_xy, color=GREEN if on_path else GOLD if selected else '#CED8E7',
                                    stroke_width=4 if on_path or selected else 2))
        for r, row in enumerate(a):
            for c, value in enumerate(row):
                cell = (r, c)
                active = not path and (cell == current or cell in children)
                color = GREEN if cell in path_set else DIM if path else GOLD if active else BLUE if known[r][c] else DIM
                shown = value if path else best[r][c]
                tile = RoundedRectangle(width=.96, height=.63, corner_radius=.08,
                       stroke_color=color, stroke_width=3 if active or cell in path_set else 1.7,
                       fill_color=color, fill_opacity=.17 if active or cell in path_set else .06)
                result.add(VGroup(tile, label(str(shown), 28, color)).move_to(pos(r, c)))
        legend = '原始数值 · 高亮为选取路径' if path else '灰：原值   蓝：最大后缀和   金：当前依赖'
        result.add(label(legend, 19, DIM, max_width=7.4).move_to([-2.65, -1.82, 0]))
        return result

    def detail(self, state, beat):
        if self.kind == 'search':
            text = '八方向相邻 · 入队时标记'
            if state['action'] == 'done':
                text = '全部扫描完毕：' + str(state['count']) + ' 个池塘'
        elif beat.get('question'):
            text = '7 + max(23, 21) = ?'
        elif beat.get('path'):
            path = state['path']
            values = [state['triangle'][r][c] for r, c in path]
            text = ' + '.join(map(str, values)) + ' = ' + str(sum(values))
        elif beat.get('greedy'):
            text = '28 < 30：贪心失败'
        elif state['action'] == 'update':
            r, c = state['cell']
            a, best = state['triangle'], state['best']
            text = f'{a[r][c]} + max({best[r+1][c]}, {best[r+1][c+1]}) = {best[r][c]}'
        elif state['action'] == 'base':
            text = '底行：dp = 原值'
        else:
            text = '每步仅能走向相邻左下 / 右下'
        return label(text, 23, BLUE, max_width=4.15).move_to([4.1, -1.35, 0])


class SearchLesson(AlgorithmLesson):
    kind = 'search'


class DPLesson(AlgorithmLesson):
    kind = 'dp'
