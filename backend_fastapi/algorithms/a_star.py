#Heuristic: |height(node) - height(goal)|. Any path from a node to the goal has
#to climb or descend by at least that much in total, so the heuristic never
#overestimates and never drops by more than an edge's cost



import heapq
import math
from itertools import count
import ee
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns


from bridges import Bridges
from bridges.data_src_dependent import data_source

class Node:
    def __init__(self, row, col, height=0, is_wall=False):
        self.row = row
        self.col = col
        self.height = height          # used to compute edge costs
        self.is_wall = is_wall        # impassable if True

        # A* state
        self.cost = math.inf          # g: best-known cost from the start
        self.heuristic = 0            # h: estimated cost from here to the goal
        self.previous = None          # the Node we got our cost from
        self.settled = False          # True once our cost is final

    @property
    def estimate(self):
        #f = g + h: estimated total cost of a path through this node.
        return self.cost + self.heuristic

    def edge_cost(self, other):
        #Cost of moving between this node and a neighbor.
        return abs(self.height - other.height)

    def reset(self):
        #Clear search state so the grid can be reused for another search.
        self.cost = math.inf
        self.heuristic = 0
        self.previous = None
        self.settled = False

    @property
    def pos(self):
        return (self.row, self.col)

    def __repr__(self):
        prev = self.previous.pos if self.previous else None
        state = "settled" if self.settled else "unsettled"
        return (f"Node({self.row},{self.col} h={self.height} "
                f"cost={self.cost} est={self.estimate} from={prev} {state})")


class Grid:
    def __init__(self, heights, walls=None):
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

    @staticmethod
    def heuristic(node, goal):
        """Admissible, consistent estimate of the cost from node to goal."""
        return abs(node.height - goal.height)

    def astar(self, start, goal, diagonal=False):
        self.reset()
        source, target = self[start], self[goal]
        if source.is_wall:
            raise ValueError(f"Start {start} is a wall")
        if target.is_wall:
            return None

        source.cost = 0
        source.heuristic = self.heuristic(source, target)
        tiebreak = count()            # avoids comparing Node objects in the heap
        # Order by f, then prefer larger g (deeper nodes) to break ties.
        heap = [(source.estimate, 0, next(tiebreak), source)]

        while heap:
            _, _, _, current = heapq.heappop(heap)
            if current.settled:
                continue              # stale heap entry
            current.settled = True

            if current is target:
                return target

            for nb in self.neighbors(current, diagonal):
                if nb.settled:
                    continue
                new_cost = current.cost + current.edge_cost(nb)
                if new_cost < nb.cost:
                    nb.cost = new_cost
                    nb.heuristic = self.heuristic(nb, target)
                    nb.previous = current
                    heapq.heappush(
                        heap, (nb.estimate, -new_cost, next(tiebreak), nb))

        return None

    def path_to(self, goal):
        #Walk `previous` pointers back from goal. Call after astar().
        node = self[goal]
        if node.cost == math.inf:
            return []
        path = []
        while node is not None:
            path.append(node)
            node = node.previous
        return path[::-1]

    def shortest_path(self, start, goal, diagonal=False):

        #Run A* from `start` to `goal`, both (row, col), and return the path as a
        #list of (row, col) coordinates, start to goal inclusive. Returns [] if
        #the goal can't be reached.

        if self.astar(start, goal, diagonal) is None:
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


class SRTMElevationData:

    def __init__(self, bbox, scale_meters=400):
        min_lat, min_lon, max_lat, max_lon = bbox
        region = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])

        srtm = (
            ee.Image("USGS/SRTMGL1_003")
            .select("elevation")
            .reproject(crs="EPSG:4326", scale=scale_meters)
        )

        rect = srtm.sampleRectangle(region=region, defaultValue=0)
        self.data = rect.get("elevation").getInfo()
        self.rows = len(self.data)
        self.cols = len(self.data[0]) if self.rows > 0 else 0
        self.xll = min_lon
        self.yll = min_lat
        self.cellsize = (max_lat - min_lat) / self.rows


def execute_astar(from_coord, to_coord):
    ee.Initialize(project="vocal-etching-286420")

    # Decrease scale_meters (down to 30) for smaller land equivalent length per cell
    ele_obj = SRTMElevationData(
        [
            from_coord[0], 
            from_coord[1],
            to_coord[0],
            to_coord[1],
        ],
        scale_meters=30,
    )
    converted_heights = np.empty((ele_obj.rows, ele_obj.cols), dtype=np.int32)
    
    for i in range(0, ele_obj.rows):
        for j in range(0, ele_obj.cols):
            converted_heights[i][j] = ele_obj.data[i][j]

    # (87, 63) was the bottom-right corner of the 89x65 BRIDGES grid;
    # use (ele_obj.rows - 2, ele_obj.cols - 2) to span the full higher-res grid
    if (from_coord[0] < to_coord[0] and from_coord[1] > to_coord[1]):
        start, goal = (1, 1), (ele_obj.rows - 2, ele_obj.cols - 2)
    if (from_coord[0] > to_coord[0] and from_coord[1] > to_coord[1]):
        start, goal = (ele_obj.rows - 2, 1), (1, ele_obj.cols - 2)
    if (from_coord[0] < to_coord[0] and from_coord[1] < to_coord[1]):
        start, goal = (1, ele_obj.cols - 2), (ele_obj.rows - 2, 1)
    if (from_coord[0] > to_coord[0] and from_coord[1] < to_coord[1]):
            start, goal = (ele_obj.rows - 2, ele_obj.cols - 2), (1, 1)
    grid = Grid(converted_heights)
    coords = grid.shortest_path(start, goal)
    toReturn = []

    for elem in grid.path_to(goal):
        toReturn.append([elem.col, elem.row])

    return toReturn

if __name__ == "__main__":
    ee.Initialize(project="vocal-etching-286420")

    # Decrease scale_meters (down to 30) for smaller land equivalent length per cell
    ele_obj = SRTMElevationData(
        [
            42.476746000000000, 
            -96.98138000000000,
            42.508577297430456,
            -96.94531249997696,
        ],
        scale_meters=30,
    )
    print("Width: " + str(ele_obj.cols))
    print("Height: " + str(ele_obj.rows))
    print(
        "Coordinate of lower left corner: "
        + str(ele_obj.xll)
        + ", "
        + str(ele_obj.yll)
    )
    print("Spatial resolution: " + str(ele_obj.cellsize))
    converted_heights = np.empty((ele_obj.rows, ele_obj.cols), dtype=np.int32)
    
    
    for i in range(0, ele_obj.rows):
        for j in range(0, ele_obj.cols):
            converted_heights[i][j] = ele_obj.data[i][j]
    print("array created!")

    # (87, 63) was the bottom-right corner of the 89x65 BRIDGES grid;
    # use (ele_obj.rows - 2, ele_obj.cols - 2) to span the full higher-res grid
    start, goal = (1, 1), (ele_obj.rows - 2, ele_obj.cols - 2)
    grid = Grid(converted_heights)
    coords = grid.shortest_path(start, goal)

    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(converted_heights, cmap='viridis')

    for elem in grid.path_to(goal):
        rect = patches.Rectangle((elem.col, elem.row), 1, 1, linewidth=1, edgecolor='black', facecolor='black')
        ax.add_patch(rect)
        print(elem.col, " ", elem.row)


    plt.show()