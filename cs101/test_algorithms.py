"""Independent oracles for the algorithm values shown in the videos."""
import ast
from itertools import product
import json
from pathlib import Path
import random
import unittest

from algorithms import bfs_trace, dp_trace, TRIANGLE


def component_oracle(grid):
    # Union-find, independent of the BFS implementation and traversal order.
    water = {(r, c) for r, row in enumerate(grid) for c, value in enumerate(row) if value == 'W'}
    parent = {p: p for p in water}
    def root(p):
        while parent[p] != p:
            p = parent[p]
        return p
    for a in water:
        for b in water:
            if max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1:
                parent[root(a)] = root(b)
    return len({root(p) for p in water})


def brute_paths(a):
    # Enumerate every complete route instead of applying a DP recurrence.
    sums = []
    for turns in product((0, 1), repeat=len(a) - 1):
        c, total = 0, a[0][0]
        for r, turn in enumerate(turns, start=1):
            c += turn
            total += a[r][c]
        sums.append(total)
    return max(sums)


class AlgorithmsTest(unittest.TestCase):
    def test_all_three_by_three_grids(self):
        for bits in product('.W', repeat=9):
            grid = [''.join(bits[i:i+3]) for i in (0, 3, 6)]
            events = bfs_trace(grid)
            self.assertEqual(events[-1]['count'], component_oracle(grid))
            added = [tuple(p) for e in events for p in e.get('added', [])]
            self.assertEqual(len(added), len(set(added)))
            self.assertEqual(len(added), bits.count('W'))
            self.assertTrue(all(len(e['queue']) == len({tuple(p) for p in e['queue']}) for e in events))

    def test_original_pond_samples(self):
        self.assertEqual(bfs_trace(['W.', '.W'])[-1]['count'], 1)
        grid = ['W........WW.', '.WWW.....WWW', '....WW...WW.', '.........WW.',
                '.........W..', '..W......W..', '.W.W.....WW.', 'W.W.W.....W.',
                '.W.W......W.', '..W.......W.']
        self.assertEqual(bfs_trace(grid)[-1]['count'], 3)

    def test_dp_against_exhaustive_routes(self):
        rng = random.Random(2760)
        for n in range(1, 8):
            for _ in range(30):
                a = [[rng.randint(-9, 20) for _ in range(r+1)] for r in range(n)]
                states = dp_trace(a)
                last = states[-1]
                self.assertEqual(last['best'][0][0], brute_paths(a))
                path = last.get('path', [[0, 0]])
                self.assertEqual(sum(a[r][c] for r, c in path), last['best'][0][0])
                self.assertTrue(all(b[0] == a[0]+1 and b[1]-a[1] in (0, 1)
                                    for a, b in zip(path, path[1:])))

    def test_original_triangle(self):
        self.assertEqual(dp_trace(TRIANGLE)[-1]['best'][0][0], 30)
        self.assertEqual(brute_paths(TRIANGLE), 30)

    def test_displayed_code_is_valid_python(self):
        for filename in ('lesson.json', 'search.json', 'dp.json'):
            lesson = json.loads((Path(__file__).parent / filename).read_text())
            for beat in lesson['beats']:
                ast.parse(beat.get('code', 'pass'))


if __name__ == '__main__':
    unittest.main()
