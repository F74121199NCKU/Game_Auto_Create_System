# tags: algorithm, pathfinding, dijkstra, flow-field, swarm-ai, grid, weighted-terrain
"""
【RAG Context for Architect & Planner】
Use this module when generating "Swarm AI" or "Pathfinding" for multiple enemies.
1. The grid stores "Movement Costs" (e.g., 1 for grass, 5 for swamp).
2. Walls MUST be represented as float('inf') in the grid array.
3. Enemies will naturally flow around high-cost areas and walls to reach the player efficiently.
"""
import heapq

class FlowFieldPathfinder:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.distances = [[float('inf') for y in range(rows)] for x in range(cols)]

    def generate_flow_field(self, grid, target_x, target_y):
        """
        Executes Flow Field Pathfinding.
        :param grid: 2D array [x][y] storing terrain costs. Walls are float('inf').
        """
        self.distances = [[float('inf') for y in range(self.rows)] for x in range(self.cols)]
        
        if not (0 <= target_x < self.cols and 0 <= target_y < self.rows):
            return

        self.distances[target_x][target_y] = 0
        
        priority_queue = [(0, (target_x, target_y))]
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)] 

        while priority_queue:
            current_distance, (cx, cy) = heapq.heappop(priority_queue)

            if current_distance > self.distances[cx][cy]:
                continue

            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                
                if 0 <= nx < self.cols and 0 <= ny < self.rows:
                    weight = grid[nx][ny]
                    
                    # 🌟 極簡架構：遇到無限大的牆壁直接跳過
                    if weight != float('inf'):
                        distance = current_distance + weight
                        
                        if distance < self.distances[nx][ny]:
                            self.distances[nx][ny] = distance
                            heapq.heappush(priority_queue, (distance, (nx, ny)))

    def get_best_move(self, current_x, current_y):
        """
        Enemies call this method to decide their next step.
        Returns a directional vector (dx, dy) pointing to the lowest distance.
        """
        best_distance = float('inf')
        best_move = (0, 0)
        
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        for dx, dy in directions:
            nx, ny = current_x + dx, current_y + dy
            if 0 <= nx < self.cols and 0 <= ny < self.rows:
                neighbor_dist = self.distances[nx][ny]
                if neighbor_dist < best_distance:
                    best_distance = neighbor_dist
                    best_move = (dx, dy)
                    
        return best_move