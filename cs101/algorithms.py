"""Executable traces for the search and DP lessons (no rendering dependencies)."""
from collections import deque
from copy import deepcopy

DIRECTIONS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]
SEARCH_GRID = ['W..WW', '.W..W', '.....', 'WW...']
TRIANGLE = [[7], [3, 8], [8, 1, 0], [2, 7, 4, 4], [4, 5, 2, 6, 5]]


def bfs_trace(grid):
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError('Expected a nonempty rectangular grid')
    rows, cols = len(grid), len(grid[0])
    visited, groups, pending = set(), {}, deque()
    events, count = [], 0

    def snapshot(action, current=None, added=()):
        events.append({'action': action, 'grid': list(grid), 'count': count,
                       'current': list(current) if current is not None else None,
                       'added': [list(p) for p in added], 'queue': [list(p) for p in pending],
                       'groups': [[r, c, k] for (r, c), k in sorted(groups.items())]})

    snapshot('initial')
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != 'W' or (r, c) in visited:
                continue
            count += 1
            visited.add((r, c))
            groups[r, c] = count
            pending.append((r, c))
            snapshot('new', (r, c), [(r, c)])
            while pending:
                x, y = pending.popleft()
                added = []
                for dx, dy in DIRECTIONS:
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < rows and 0 <= ny < cols and grid[nx][ny] == 'W'
                            and (nx, ny) not in visited):
                        visited.add((nx, ny))  # Mark on enqueue, so each cell enters only once.
                        groups[nx, ny] = count
                        pending.append((nx, ny))
                        added.append((nx, ny))
                snapshot('visit', (x, y), added)
    snapshot('done')
    return events


def dp_trace(triangle):
    if not triangle or any(len(row) != i + 1 for i, row in enumerate(triangle)):
        raise ValueError('Expected a triangular matrix')
    best = deepcopy(triangle)
    known = [[False] * len(row) for row in triangle]
    events = []

    def snapshot(action, cell=None, children=(), chosen=None):
        events.append({'action': action, 'triangle': deepcopy(triangle),
                       'best': deepcopy(best), 'known': deepcopy(known),
                       'cell': list(cell) if cell else None,
                       'children': [list(p) for p in children],
                       'chosen': list(chosen) if chosen else None})

    snapshot('initial')
    known[-1] = [True] * len(known[-1])
    snapshot('base')
    for r in range(len(triangle) - 2, -1, -1):
        for c in range(r + 1):
            left, right = (r + 1, c), (r + 1, c + 1)
            chosen = left if best[r + 1][c] >= best[r + 1][c + 1] else right
            best[r][c] = triangle[r][c] + best[chosen[0]][chosen[1]]
            known[r][c] = True
            snapshot('update', (r, c), (left, right), chosen)
    path, c = [], 0
    for r in range(len(triangle)):
        path.append([r, c])
        if r < len(triangle) - 1 and best[r + 1][c + 1] > best[r + 1][c]:
            c += 1
    events[-1]['path'] = path
    return events


def lesson_trace(kind, beats):
    """Beat steps index real state transitions; no hand-authored computed values."""
    if kind == 'search':
        events = bfs_trace(SEARCH_GRID)
        quiz = bfs_trace(['W.', '.W'])
    elif kind == 'dp':
        events = dp_trace(TRIANGLE)
    else:
        raise ValueError(kind)
    result = []
    for beat in beats:
        b = deepcopy(beat)
        source = quiz if kind == 'search' and b.get('quiz') else events
        b['states'] = [deepcopy(source[i]) for i in b['steps']]
        result.append(b)
    return result
