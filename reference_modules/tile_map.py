# tags: procedural-generation, maze, dfs, tilemap, grid-system
import pygame
import random

class MazeManager:
    """
    迷宮生成與管理模組。
    封裝了 DFS 迷宮生成演算法與基本的網格繪圖功能。
    
    功能：
    1. 使用 Iterative DFS 演算法生成保證連通的迷宮。
    2. 提供標準化的地圖繪製方法。
    """
    
    # 顏色定義 (Class Constants)
    WALL_COLOR = (0, 0, 0)          # 牆 (黑)
    PATH_COLOR = (255, 255, 255)    # 路 (白)
    START_COLOR = (0, 255, 0)       # 起點 (綠)
    END_COLOR = (255, 0, 0)         # 終點 (紅)
    
    # 格子定義
    TILE_WALL = 1
    TILE_PATH = 0
    TILE_START = 2
    TILE_END = 3

    def __init__(self, tile_size=20):
        """
        :param tile_size: 每個格子的像素大小 (預設 20)
        """
        self.tile_size = tile_size

    def create_path_dfs(self, width, height):
        """
        使用深度優先搜尋 (DFS) 生成迷宮地圖。
        
        :param width: 網格寬度 (Grid Cols)
        :param height: 網格高度 (Grid Rows)
        :return: 二維陣列 (List of Lists)
        """
        # 初始化牆壁 
        grid = [[self.TILE_WALL for _ in range(width)] for _ in range(height)]
        
        start_x, start_y = 1, 1
        grid[start_y][start_x] = self.TILE_PATH
        
        stack = [(start_x, start_y)]    # 記錄走過的地方
        directions = [(0, -2), (0, 2), (-2, 0), (2, 0)]

        # DFS 演算法挖掘過程 
        while stack:
            current_x, current_y = stack[-1]
            possible_moves = []
            for dx, dy in directions:
                nx, ny = current_x + dx, current_y + dy
                if 1 <= nx < width - 1 and 1 <= ny < height - 1:
                    if grid[ny][nx] == self.TILE_WALL:
                        possible_moves.append((dx, dy))
            
            if possible_moves:
                dx, dy = random.choice(possible_moves)
                # 打通牆壁 (中間格與目標格)
                grid[current_y + dy // 2][current_x + dx // 2] = self.TILE_PATH
                grid[current_y + dy][current_x + dx] = self.TILE_PATH
                stack.append((current_x + dx, current_y + dy))
            else:
                stack.pop()

        # 設定起點與終點
        grid[1][1] = self.TILE_START
        grid[height - 2][width - 2] = self.TILE_END

        return grid

    def draw_map(self, surface, map_data):
        """
        繪製整個迷宮地圖到指定的 Surface 上。
        
        :param surface: 目標繪圖畫布 (通常是 screen)
        :param map_data: create_path_dfs 產生的二維陣列
        """
        # 先填滿背景色 (路徑色)，這樣只需要畫牆壁和特殊點，優化效能
        surface.fill(self.PATH_COLOR)

        for row_index, row in enumerate(map_data):
            for col_index, tile in enumerate(row):
                rect = pygame.Rect(
                    col_index * self.tile_size, 
                    row_index * self.tile_size, 
                    self.tile_size, 
                    self.tile_size
                )
                
                if tile == self.TILE_WALL:
                    pygame.draw.rect(surface, self.WALL_COLOR, rect)
                elif tile == self.TILE_START:
                    pygame.draw.rect(surface, self.START_COLOR, rect)
                elif tile == self.TILE_END:
                    pygame.draw.rect(surface, self.END_COLOR, rect)
