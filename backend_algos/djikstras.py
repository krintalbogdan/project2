import heapq
import math
from itertools import count


class Node:
    def __init__(self, row, col, height=0, is_wall=False):
        self.row = row
        self.col = col
        self.height = height          # used to compute edge costs
        self.is_wall = is_wall        # impassable if True

        # Dijkstra state
        self.cost = math.inf          # current best-known cost from the start
        self.previous = None          # the Node we got our cost from
        self.settled = False          # True once our cost is final

    def edge_cost(self, other):
        #Cost of moving between this node and a neighbor.
        return abs(self.height - other.height)

    def reset(self):
        #Clear Dijkstra state so the grid can be reused for another search.
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
    def __init__(self, heights, walls=None):

        #heights: 2D list of numbers (height of each cell).
        #         Use None in a cell to make it a wall.
        #walls:   optional iterable of (row, col) to mark as walls.

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

    def dijkstra(self, start, goal=None, diagonal=False):

        #Run Dijkstra from `start` (row, col). If `goal` is given, stop early once
        #it's settled. Returns the goal Node (or None if no goal / unreachable).

        self.reset()
        source = self[start]
        if source.is_wall:
            raise ValueError(f"Start {start} is a wall")
        target = self[goal] if goal is not None else None

        source.cost = 0
        tiebreak = count()            # avoids comparing Node objects in the heap
        heap = [(0, next(tiebreak), source)]

        while heap:
            cost, _, current = heapq.heappop(heap)
            if current.settled:
                continue              # stale heap entry
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

    def path_to(self, goal):
        #Walk `previous` pointers back from goal. Call after dijkstra().
        node = self[goal]
        if node.cost == math.inf:
            return []
        path = []
        while node is not None:
            path.append(node)
            node = node.previous
        return path[::-1]

    def shortest_path(self, start, goal, diagonal=False):

        #Run Dijkstra from `start` to `goal` and return the path as a list of
        #(row, col) coordinates, start to goal inclusive. Returns [] if the goal
        #can't be reached.

        if self.dijkstra(start, goal, diagonal) is None:
            return []
        return [node.pos for node in self.path_to(goal)]

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
    # Numbers are heights; None = wall.
    # Edge cost = |height difference| between neighbors.
    #heights = [
        #[0, 1, 2, 9, 9],
        #[5, None, 3, 9, 9],
        #[6, None, 4, 5, 6],
        #[9, 9, None, None, 7],
        #[9, 9, 9, 8, 8],
    #]

    #grid = Grid(heights)
    #start, goal = (0, 0), (4, 4)

    #coords = grid.shortest_path(start, goal)
    #if not coords:
        #print("No path found.")
    #else:
        #end = grid[goal]
        #path = grid.path_to(goal)
        #print(f"Shortest cost {start} -> {goal}: {end.cost}")
        #print("Path coordinates:", coords)
        #print("Step costs:",
        #      [a.edge_cost(b) for a, b in zip(path, path[1:])])
        #print()
        #print(grid.render(path))
        #print()
        #print("Goal node:", end)