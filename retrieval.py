from typing import List, Dict, Tuple, Any, Set
import heapq
import math
from app.models import CargoSystem, Item, Container, Position


class RTreeNode:
    def __init__(self, bounds, is_leaf=True):
        self.bounds = bounds  # (min_x, min_y, min_z, max_x, max_y, max_z)
        self.is_leaf = is_leaf
        self.entries = []  # For leaf: (bounds, item_id); For non-leaf: (bounds, child_node)


class RTreeIndex:
    def __init__(self, max_entries=5):
        self.root = RTreeNode((0, 0, 0, 0, 0, 0), True)
        self.max_entries = max_entries

    def insert(self, item_id, bounds):
        """Insert item with its 3D bounds"""
        self._insert(self.root, item_id, bounds)

    def _insert(self, node, item_id, bounds):
        if node.is_leaf:
            node.entries.append((bounds, item_id))
            node.bounds = self._expand_bounds(node.bounds, bounds)

            if len(node.entries) > self.max_entries:
                self._split_node(node)
        else:
            # Choose best subtree
            best_idx = self._choose_subtree(node, bounds)
            child = node.entries[best_idx][1]

            self._insert(child, item_id, bounds)

            # Update parent bounds
            node.entries[best_idx] = (child.bounds, child)
            node.bounds = self._merge_all_bounds([entry[0] for entry in node.entries])

    def _choose_subtree(self, node, bounds):
        min_enlargement = float('inf')
        best_idx = 0

        for i, (child_bounds, _) in enumerate(node.entries):
            enlarged = self._expand_bounds(child_bounds, bounds)
            enlargement = self._calculate_volume(enlarged) - self._calculate_volume(child_bounds)

            if enlargement < min_enlargement:
                min_enlargement = enlargement
                best_idx = i

        return best_idx

    def _split_node(self, node):
        # Linear split
        entries = node.entries
        node.entries = []

        # Choose seeds
        min_margin = float('inf')
        seed_idx1, seed_idx2 = 0, 0

        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                margin = self._calculate_margin(
                    self._expand_bounds(entries[i][0], entries[j][0])
                )
                if margin < min_margin:
                    min_margin = margin
                    seed_idx1, seed_idx2 = i, j

        # Create two groups
        group1 = [entries[seed_idx1]]
        group2 = [entries[seed_idx2]]

        remaining = [entry for i, entry in enumerate(entries)
                     if i != seed_idx1 and i != seed_idx2]

        # Distribute remaining entries
        while remaining:
            if len(group1) >= self.max_entries // 2:
                group2.extend(remaining)
                break

            if len(group2) >= self.max_entries // 2:
                group1.extend(remaining)
                break

            # Choose next entry based on minimum enlargement
            selected_idx = 0
            selected_group = 1
            min_diff = float('inf')

            for i, entry in enumerate(remaining):
                bounds1 = self._merge_all_bounds([e[0] for e in group1] + [entry[0]])
                bounds2 = self._merge_all_bounds([e[0] for e in group2] + [entry[0]])

                enlargement1 = self._calculate_volume(bounds1) - self._calculate_volume(
                    self._merge_all_bounds([e[0] for e in group1])
                )

                enlargement2 = self._calculate_volume(bounds2) - self._calculate_volume(
                    self._merge_all_bounds([e[0] for e in group2])
                )

                diff = abs(enlargement1 - enlargement2)

                if diff < min_diff:
                    min_diff = diff
                    selected_idx = i
                    selected_group = 1 if enlargement1 < enlargement2 else 2

            if selected_group == 1:
                group1.append(remaining[selected_idx])
            else:
                group2.append(remaining[selected_idx])

            remaining.pop(selected_idx)

        # Create new nodes
        if node.is_leaf:
            node1 = RTreeNode(self._merge_all_bounds([e[0] for e in group1]), True)
            node2 = RTreeNode(self._merge_all_bounds([e[0] for e in group2]), True)

            node1.entries = group1
            node2.entries = group2
        else:
            node1 = RTreeNode(self._merge_all_bounds([e[0] for e in group1]), False)
            node2 = RTreeNode(self._merge_all_bounds([e[0] for e in group2]), False)

            node1.entries = group1
            node2.entries = group2

        # Update parent or create new root
        if node == self.root:
            new_root = RTreeNode(
                self._merge_all_bounds([node1.bounds, node2.bounds]),
                False
            )
            new_root.entries = [(node1.bounds, node1), (node2.bounds, node2)]
            self.root = new_root

        return (node1, node2)

    def query(self, bounds):
        """Query items within or intersecting bounds"""
        result = []
        self._query(self.root, bounds, result)
        return result

    def _query(self, node, bounds, result):
        if not self._intersects(node.bounds, bounds):
            return

        if node.is_leaf:
            for entry_bounds, item_id in node.entries:
                if self._intersects(entry_bounds, bounds):
                    result.append(item_id)
        else:
            for _, child in node.entries:
                self._query(child, bounds, result)

    def _expand_bounds(self, bounds1, bounds2):
        """Expand bounds1 to include bounds2"""
        min_x1, min_y1, min_z1, max_x1, max_y1, max_z1 = bounds1
        min_x2, min_y2, min_z2, max_x2, max_y2, max_z2 = bounds2

        return (
            min(min_x1, min_x2),
            min(min_y1, min_y2),
            min(min_z1, min_z2),
            max(max_x1, max_x2),
            max(max_y1, max_y2),
            max(max_z1, max_z2)
        )

    def _merge_all_bounds(self, bounds_list):
        """Merge multiple bounds"""
        if not bounds_list:
            return (0, 0, 0, 0, 0, 0)

        result = bounds_list[0]
        for bounds in bounds_list[1:]:
            result = self._expand_bounds(result, bounds)

        return result

    def _calculate_volume(self, bounds):
        """Calculate volume of bounds"""
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        return max(0, max_x - min_x) * max(0, max_y - min_y) * max(0, max_z - min_z)

    def _calculate_margin(self, bounds):
        """Calculate margin (sum of edge lengths) of bounds"""
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        return (max_x - min_x) + (max_y - min_y) + (max_z - min_z)

    def _intersects(self, bounds1, bounds2):
        """Check if two bounds intersect"""
        min_x1, min_y1, min_z1, max_x1, max_y1, max_z1 = bounds1
        min_x2, min_y2, min_z2, max_x2, max_y2, max_z2 = bounds2

        return (
                min_x1 <= max_x2 and max_x1 >= min_x2 and
                min_y1 <= max_y2 and max_y1 >= min_y2 and
                min_z1 <= max_z2 and max_z1 >= min_z2
        )


def a_star_3d(start, goal, obstacles, dimensions):
    """3D A* pathfinding to navigate to an item"""
    # Create a simple grid for navigation
    width, height, depth = dimensions
    grid = [[[0 for _ in range(depth)] for _ in range(height)] for _ in range(width)]

    # Mark obstacles in the grid
    for obstacle in obstacles:
        ox, oy, oz = obstacle
        grid[ox][oy][oz] = 1

    # Define valid moves (6-connected in 3D)
    moves = [
        (1, 0, 0), (-1, 0, 0),
        (0, 1, 0), (0, -1, 0),
        (0, 0, 1), (0, 0, -1)
    ]

    # A* implementation
    open_set = []
    closed_set = set()
    g_score = {}
    f_score = {}
    came_from = {}

    start_tuple = (start.x, start.y, start.z)
    goal_tuple = (goal.x, goal.y, goal.z)

    g_score[start_tuple] = 0
    f_score[start_tuple] = heuristic(start_tuple, goal_tuple)

    heapq.heappush(open_set, (f_score[start_tuple], start_tuple))

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal_tuple:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)

            path.reverse()
            return [Position(x, y, z) for x, y, z in path]

        closed_set.add(current)

        cx, cy, cz = current
        for dx, dy, dz in moves:
            nx, ny, nz = cx + dx, cy + dy, cz + dz

            if not (0 <= nx < width and 0 <= ny < height and 0 <= nz < depth):
                continue

            if grid[nx][ny][nz] == 1:
                continue

            neighbor = (nx, ny, nz)

            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + 1

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal_tuple)

                if all(item[1] != neighbor for item in open_set):
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

    # No path found
    return []


def heuristic(a, b):
    """Manhattan distance heuristic for A*"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def optimize_retrieval(item_id: str, cargo_system: CargoSystem):
    """Use R-tree to locate item and A* to find optimal retrieval path"""
    if item_id not in cargo_system.items:
        return []

    item = cargo_system.items[item_id]

    if not item.container_id or item.container_id not in cargo_system.containers:
        return []

    container = cargo_system.containers[item.container_id]

    # Create R-tree index for all items in the container
    rtree = RTreeIndex()
    obstacles = []

    for i in container.items:
        if i.id != item_id and i.position:
            bounds = (
                i.position.x,
                i.position.y,
                i.position.z,
                i.position.x + i.dimensions.width,
                i.position.y + i.dimensions.height,
                i.position.z + i.dimensions.depth
            )
            rtree.insert(i.id, bounds)
            obstacles.append((int(i.position.x), int(i.position.y), int(i.position.z)))

    # Define start and goal positions
    start = Position(0, 0, 0)  # Container entrance
    goal = item.position

    dimensions = (
        int(container.dimensions.width),
        int(container.dimensions.height),
        int(container.dimensions.depth)
    )

    # Use A* to find path
    path = a_star_3d(start, goal, obstacles, dimensions)

    # Convert to API response format
    return [pos.to_dict() for pos in path]
