# tags: algorithm, pathfinding, a-star, smart-enemy, grid
"""
Use this module for Elite Enemies or Bosses that need to intelligently navigate around walls to reach the player.
This A* search is optimized for 2D Grids using heapq and supports terrain weights.
"""
import heapq

class AStarPathfinder:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows

    def heuristic(self, a, b):
        """Manhattan distance for 4-way grid movement"""
        (x1, y1) = a
        (x2, y2) = b
        return abs(x1 - x2) + abs(y1 - y2)

    def find_path(self, grid, start, goal, wall_value=1):
        """
        Calculates the shortest path using A*.
        :grid: 2D array [x][y] representing the map.
        :start: Tuple (x, y) starting grid coordinate.
        :goal: Tuple (x, y) target grid coordinate.
        :return: A list of (x, y) tuples representing the path. Empty list if no path.
        """
        frontier = []
        heapq.heappush(frontier, (0, start))
        
        came_from = {}
        cost_so_far = {}
        
        came_from[start] = None
        cost_so_far[start] = 0
        
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        while frontier:
            _, current = heapq.heappop(frontier)
            
            # Early exit: Reached the goal
            if current == goal:
                break
                
            cx, cy = current
            
            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                next_node = (nx, ny)
                
                # Boundary and Wall Check
                if 0 <= nx < self.cols and 0 <= ny < self.rows:
                    weight = grid[nx][ny] 
                    if weight != float('inf'): 
                        new_cost = cost_so_far[current] + weight
                        
                        if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                            cost_so_far[next_node] = new_cost
                            priority = new_cost + self.heuristic(next_node, goal)
                            heapq.heappush(frontier, (priority, next_node))
                            came_from[next_node] = current
                            
        # Reconstruct Path
        return self._reconstruct_path(came_from, start, goal)

    def _reconstruct_path(self, came_from, start, goal):
        """Backtracks from goal to start to return the sequence of steps"""
        if goal not in came_from:
            return [] # No path found
            
        current = goal
        path = []
        while current != start:
            path.append(current)
            current = came_from[current]
        # path.append(start) # Optional: include start pos
        path.reverse() # Reverse so it goes from start -> goal
        
        return path