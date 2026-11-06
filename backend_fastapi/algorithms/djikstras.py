# Dijkstra on a 2D grid of Node objects.
# Edge cost = height difference between neighbors.

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

        #Run Dijkstra from `start` to `goal` and return the path as a list of
        #(row, col) coordinates, start to goal inclusive. Returns [] if the goal
        #can't be reached.

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


def execute_dijkstra(from_coord, to_coord):
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
    from_coord = [42.508577297430456,
               -96.98138000000000]
    to_coord = [42.476746000000000,
                     -96.94531249997696]
    ele_obj = SRTMElevationData(
        [
            from_coord[0],
           from_coord[1],
            to_coord[0],
             to_coord[1],
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

    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(converted_heights, cmap='viridis')

    for elem in grid.path_to(goal):
        rect = patches.Rectangle((elem.col, elem.row), 1, 1, linewidth=1, edgecolor='black', facecolor='black')
        ax.add_patch(rect)
        print(elem.col, " ", elem.row)


    plt.show()