# Dijkstra on a 2D grid of Node objects.
# Edge cost = height difference between neighbors.

import heapq
import math
from itertools import count

GAINESVILLE_FL = (29.6516, -82.3248)  # center of cell (0, 0)
CELL_SIZE_M = 30                      # meters between cell centers
METERS_PER_DEG_LAT = 111_320


class Node:
    def __init__(self, row, col, height=0, is_wall=False):
        self.row = row
        self.col = col
        self.height = height
        self.is_wall = is_wall

        # search state
        self.cost = math.inf    # cost from start
        self.previous = None    # node we got our cost from
        self.settled = False    # cost is final

    def edge_cost(self, other):
        return abs(self.height - other.height)

    def reset(self):
        self.cost = math.inf
        self.previous = None
        self.settled = False

    @property
    def pos(self):
        return (self.row, self.col)

    def __repr__(self):
        prev = self.previous.pos if self.previous else None
        state = "settled" if self.settled else "unsettled"
        return (f"Node({self.row},{self.col} h={self.height} "
                f"cost={self.cost} from={prev} {state})")


class Grid:
    # heights: 2D list, None = wall
    # origin: (lat, lon) of cell (0, 0), the top-left / north-west cell
    # rows run south, columns run east
    def __init__(self, heights, walls=None, origin=GAINESVILLE_FL,
                 cell_size_m=CELL_SIZE_M):
        walls = set(walls or [])
        self.nodes = [
            [Node(r, c,
                  height=(h if h is not None else 0),
                  is_wall=(h is None or (r, c) in walls))
             for c, h in enumerate(row)]
            for r, row in enumerate(heights)
        ]
        self.rows = len(self.nodes)
        self.cols = len(self.nodes[0]) if self.rows else 0

        # meters -> degrees at the origin's latitude (fine for small areas)
        self.origin = origin
        self.lat_step = cell_size_m / METERS_PER_DEG_LAT
        self.lon_step = cell_size_m / (
            METERS_PER_DEG_LAT * math.cos(math.radians(origin[0])))

    def __getitem__(self, pos):
        r, c = pos
        return self.nodes[r][c]

    def in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def neighbors(self, node, diagonal=False):
        steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            steps += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in steps:
            r, c = node.row + dr, node.col + dc
            if self.in_bounds(r, c) and not self.nodes[r][c].is_wall:
                yield self.nodes[r][c]

    def reset(self):
        for row in self.nodes:
            for node in row:
                node.reset()

    # start, goal: (row, col). No goal = settle the whole grid.
    # Returns goal node, or None if no goal / unreachable.
    def dijkstra(self, start, goal=None, diagonal=False):
        self.reset()
        source = self[start]
        if source.is_wall:
            raise ValueError(f"Start {start} is a wall")
        target = self[goal] if goal is not None else None

        source.cost = 0
        tiebreak = count()
        heap = [(0, next(tiebreak), source)]

        while heap:
            _, _, current = heapq.heappop(heap)
            if current.settled:
                continue  # stale entry
            current.settled = True

            if current is target:
                break

            for nb in self.neighbors(current, diagonal):
                if nb.settled:
                    continue
                new_cost = current.cost + current.edge_cost(nb)
                if new_cost < nb.cost:
                    nb.cost = new_cost
                    nb.previous = current
                    heapq.heappush(heap, (new_cost, next(tiebreak), nb))

        if target is not None and target.cost == math.inf:
            return None
        return target

    # follow previous pointers back from goal; call after dijkstra()
    def path_to(self, goal):
        node = self[goal]
        if node.cost == math.inf:
            return []
        path = []
        while node is not None:
            path.append(node)
            node = node.previous
        return path[::-1]

    # (row, col) in, list of (row, col) out; [] if unreachable
    def shortest_path(self, start, goal, diagonal=False):
        if self.dijkstra(start, goal, diagonal) is None:
            return []
        return [node.pos for node in self.path_to(goal)]

    # (row, col) -> (lat, lon) of the cell center
    def cell_to_latlon(self, pos):
        r, c = pos
        lat0, lon0 = self.origin
        return (lat0 - r * self.lat_step, lon0 + c * self.lon_step)

    # (lat, lon) -> (row, col) of the cell containing it
    def latlon_to_cell(self, lat, lon):
        lat0, lon0 = self.origin
        r = round((lat0 - lat) / self.lat_step)
        c = round((lon - lon0) / self.lon_step)
        if not self.in_bounds(r, c):
            raise ValueError(f"({lat}, {lon}) is outside the grid")
        return (r, c)

    # (lat, lon) in, list of (lat, lon) out; [] if unreachable
    def shortest_path_latlon(self, start, goal, diagonal=False):
        start_cell = self.latlon_to_cell(*start)
        goal_cell = self.latlon_to_cell(*goal)
        return [self.cell_to_latlon(p)
                for p in self.shortest_path(start_cell, goal_cell, diagonal)]

    def render(self, path=()):
        on_path = {n.pos for n in path}
        lines = []
        for row in self.nodes:
            cells = []
            for n in row:
                if n.is_wall:
                    cells.append("  ##")
                elif n.pos in on_path:
                    cells.append(f" *{n.height:>2}")
                else:
                    cells.append(f"{n.height:>4}")
            lines.append("".join(cells))
        return "\n".join(lines)


#if __name__ == "__main__":
    # heights; None = wall
    #heights = [
    #    [0, 1, 2, 9, 9],
    #    [5, None, 3, 9, 9],
    #    [6, None, 4, 5, 6],
    #    [9, 9, None, None, 7],
    #    [9, 9, 9, 8, 8],
    #]

    #grid = Grid(heights)
    #start, goal = (0, 0), (4, 4)

    #coords = grid.shortest_path(start, goal)
    #if not coords:
        #print("No path found.")
    #else:
        path = grid.path_to(goal)
        settled = sum(n.settled for row in grid.nodes for n in row)
        print(f"Shortest cost {start} -> {goal}: {grid[goal].cost}")
        print("Path coordinates:", coords)
        print("Step costs:",
              [a.edge_cost(b) for a, b in zip(path, path[1:])])
        print("Nodes settled:", settled)
        print()
        print(grid.render(path))
        print()
        print("Goal node:", grid[goal])

        start_ll = grid.cell_to_latlon(start)
        goal_ll = grid.cell_to_latlon(goal)
        print()
        print(f"Lat/lon path ({CELL_SIZE_M} m cells):")
        for lat, lon in grid.shortest_path_latlon(start_ll, goal_ll):
            print(f"  ({lat:.6f}, {lon:.6f})")