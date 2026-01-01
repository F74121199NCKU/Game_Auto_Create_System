import pygame
import random
import os # 導入 os 模組用於路徑操作
from typing import Tuple, Dict, List, Type, Callable, Any, Optional, Generic, TypeVar

# It's good practice to initialize Pygame early if constants depend on it (e.g., font matching)
pygame.init()

# --- Game Configuration (解決批評點 1) ---
class GameConfig:
    """
    集中管理遊戲所有硬編碼數值，提升可配置性與維護性。
    """
    # Screen settings
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 720
    SCREEN_SIZE: Tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT)
    TITLE: str = "虛空倖存者"
    FPS: int = 60

    # Map settings
    MAP_WIDTH: int = 3000
    MAP_HEIGHT: int = 3000
    MAP_SIZE: Tuple[int, int] = (MAP_WIDTH, MAP_HEIGHT)
    
    # 修正 FileNotFoundError: 使用 os.path 構建絕對路徑
    # 假設 'Graphic' 資料夾位於專案根目錄，即 'dest' 資料夾的上一層
    _current_script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root_dir = os.path.abspath(os.path.join(_current_script_dir, os.pardir))
    GROUND_IMAGE_PATH: str = os.path.join(_project_root_dir, "Graphic", "ground2.png")

    # Colors
    WHITE: Tuple[int, int, int] = (255, 255, 255)
    BLACK: Tuple[int, int, int] = (0, 0, 0)
    RED: Tuple[int, int, int] = (255, 0, 0)
    GREEN: Tuple[int, int, int] = (0, 255, 0)
    BLUE: Tuple[int, int, int] = (0, 0, 255)
    YELLOW: Tuple[int, int, int] = (255, 255, 0)
    GROUND_FALLBACK_COLOR: Tuple[int, int, int] = (70, 130, 180) # SteelBlue

    # Player settings
    PLAYER_DEFAULT_SIZE: Tuple[int, int] = (40, 40)
    PLAYER_SPEED: float = 200.0 # pixels/sec
    PLAYER_INITIAL_HEALTH: int = 100
    PLAYER_FIRE_RATE: float = 0.3 # seconds between shots
    PLAYER_AUTO_FIRE_SEARCH_RADIUS_MULTIPLIER: float = 1.5 # Multiplier of screen width for enemy search

    # Enemy settings
    ENEMY_DEFAULT_SIZE: Tuple[int, int] = (32, 32)
    ENEMY_INITIAL_HEALTH: int = 1
    ENEMY_SPEED: float = 100.0 # pixels/sec
    ENEMY_SPAWN_INTERVAL: float = 1.0 # Initial spawn interval in seconds
    ENEMY_MIN_SPAWN_INTERVAL: float = 0.2 # Minimum spawn interval
    ENEMY_SPAWN_DECREASE_RATE: float = 0.005 # Rate at which interval decreases per spawn
    ENEMY_SPAWN_BUFFER: int = 50 # Distance outside screen to spawn enemies

    # Bullet settings
    BULLET_DEFAULT_SIZE: Tuple[int, int] = (10, 10)
    BULLET_SPEED: float = 500.0 # pixels/sec
    BULLET_DAMAGE: int = 1
    BULLET_LIFETIME: float = 2.0 # seconds

    # Object Pool settings
    BULLET_POOL_SIZE: int = 200
    ENEMY_POOL_SIZE: int = 100

    # Camera settings
    CAMERA_BORDER_RATIO: float = 0.2 # 20% of screen width/height for border

    # Spatial Grid settings
    SPATIAL_GRID_CELL_SIZE: int = 100 # Size of cells in the spatial grid

    # Font settings
    FONT_SIZE_UI: int = 30
    DEFAULT_SPRITE_SIZE: Tuple[int, int] = (32, 32) # For sprites without images or missing images
    FONT_NAME: Optional[str] = None # Will be set by get_font during init

    @classmethod
    def initialize_font(cls) -> None:
        """Finds and sets a suitable font for Chinese characters."""
        font_name = pygame.font.match_font('microsoftjhenghei')
        if not font_name:
            font_name = pygame.font.match_font('simhei') # fallback
        cls.FONT_NAME = font_name

# Initialize font after pygame.init()
GameConfig.initialize_font()

# --- Utility functions ---
def get_font(size: int) -> pygame.font.Font:
    """Helper function to load a font, preferring Chinese fonts."""
    if GameConfig.FONT_NAME:
        return pygame.font.Font(GameConfig.FONT_NAME, size)
    return pygame.font.Font(None, size) # Fallback to default pygame font

# ====== Reference Module: sprite_manager.py ======
class GameSprite(pygame.sprite.Sprite):
    """
    所有遊戲物件的基礎類別，繼承自 Pygame 的 Sprite。
    提供預設的圖像加載、矩形區域和速度屬性。
    """
    def __init__(self, x: int = 0, y: int = 0, image_path: Optional[str] = None):
        super().__init__()
        
        image_width, image_height = GameConfig.DEFAULT_SPRITE_SIZE # 使用配置中的預設精靈尺寸

        if image_path:
            try:
                self.image: pygame.Surface = pygame.image.load(image_path).convert_alpha()
            except pygame.error:
                # print(f"Warning: Could not load image {image_path}. Using default red square.")
                self.image = pygame.Surface((image_width, image_height))
                self.image.fill(GameConfig.RED) # 使用配置中的顏色
        else:
            self.image = pygame.Surface((image_width, image_height))
            self.image.fill(GameConfig.RED) # 預設為紅色方塊

        self.rect: pygame.Rect = self.image.get_rect(topleft=(x, y))
        self.velocity: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.active_status: bool = True # 基礎狀態，用於物件池管理，預設為活躍

    def update(self, dt: float) -> None:
        """
        每幀更新位置，dt 是時間差 (Delta Time)。
        只更新活躍精靈的位置。
        """
        if not self.active_status: # 只更新活躍的精靈
            return
        self.rect.x += self.velocity.x * dt
        self.rect.y += self.velocity.y * dt

# ====== Reference Module: camera_box.py ======
class BoxCameraGroup(pygame.sprite.Group):
    """
    Box Camera (箱型相機) 邏輯封裝版。
    功能：
    1. 建立一個虛擬的 Camera Box。
    2. 只有當目標 (target) 移出 Box 邊界時，相機才會移動。
    3. 內建 Y-Sort (深度排序) 渲染。 (已改為透過 SpatialGrid 輔助)
    """
    def __init__(self, map_size: Tuple[int, int], camera_border_ratio: float, 
                 ground_image_path: str, ground_fallback_color: Tuple[int, int, int],
                 spatial_grid: 'SpatialGrid'): # Added spatial_grid parameter for C3
        super().__init__()
        self.display_surface: pygame.Surface = pygame.display.get_surface()
        
        screen_w, screen_h = self.display_surface.get_size()
        
        self.offset: pygame.math.Vector2 = pygame.math.Vector2()

        # 設定箱子邊界 (Camera Box Setup)
        self.camera_borders: Dict[str, float] = {
            'left': screen_w * camera_border_ratio,
            'right': screen_w * camera_border_ratio,
            'top': screen_h * camera_border_ratio,
            'bottom': screen_h * camera_border_ratio
        }
        
        # 計算箱子的具體矩形 (Rect)
        l = self.camera_borders['left']
        t = self.camera_borders['top']
        w = screen_w - (self.camera_borders['left'] + self.camera_borders['right'])
        h = screen_h - (self.camera_borders['top'] + self.camera_borders['bottom'])
        self.camera_rect: pygame.Rect = pygame.Rect(l, t, w, h)

        # 背景設定 (Background)
        try:
            # 此處的 ground_image_path 已在 GameConfig 中被修正為絕對路徑
            self.ground_surf: pygame.Surface = pygame.image.load(ground_image_path).convert_alpha()
            self.ground_surf = pygame.transform.scale(self.ground_surf, map_size)
        except (pygame.error, FileNotFoundError) as e: # 修正：添加 FileNotFoundError 確保能捕捉到文件未找到的錯誤
            print(f"Warning: Could not load ground image from '{ground_image_path}'. Reason: {e}. Using fallback color.")
            self.ground_surf = pygame.Surface(map_size) 
            self.ground_surf.fill(ground_fallback_color) 
            
        self.ground_rect: pygame.Rect = self.ground_surf.get_rect(topleft=(0, 0))

        self.spatial_grid: SpatialGrid = spatial_grid # Store spatial grid for drawing (C3)

    def update_offset(self, target: 'GameSprite') -> None:
        """
        核心運算：更新相機偏移量。此方法應在遊戲的邏輯更新階段呼叫。
        根據目標精靈的位置，調整相機的偏移量以保持目標在相機箱內。
        """
        # 左邊界檢查
        if target.rect.left < self.camera_rect.left:
            self.camera_rect.left = target.rect.left
        # 右邊界檢查
        if target.rect.right > self.camera_rect.right:
            self.camera_rect.right = target.rect.right
        # 上邊界檢查
        if target.rect.top < self.camera_rect.top:
            self.camera_rect.top = target.rect.top
        # 下邊界檢查
        if target.rect.bottom > self.camera_rect.bottom:
            self.camera_rect.bottom = target.rect.bottom

        # 計算最終偏移量 (相機框位置 - 邊界設定)
        self.offset.x = self.camera_rect.left - self.camera_borders['left']
        self.offset.y = self.camera_rect.top - self.camera_borders['top']

    def custom_draw(self) -> None:
        """
        渲染循環：包含背景與所有精靈的 Y-Sort。此方法應在遊戲的渲染階段呼叫。
        只負責繪製，不包含任何邏輯更新。
        優化：使用 SpatialGrid 輔助 Frustum Culling 和 Y-Sort，減少每幀的排序成本。 (解決批評點 3)
        """
        # 1. 畫地圖 (減去偏移量)
        ground_offset: pygame.math.Vector2 = pygame.math.Vector2(self.ground_rect.topleft) - self.offset
        self.display_surface.blit(self.ground_surf, ground_offset)
        
        # 2. 畫精靈 (透過 SpatialGrid 進行 Frustum Culling 和 Y-Sort)
        screen_w, screen_h = self.display_surface.get_size()
        screen_view_rect = pygame.Rect(0, 0, screen_w, screen_h) # 當前螢幕視圖矩形
        
        # 計算當前螢幕視野在世界座標中的邊界
        view_left = self.offset.x
        view_top = self.offset.y
        view_right = self.offset.x + screen_w
        view_bottom = self.offset.y + screen_h

        # 獲取螢幕視野對應的網格儲存格範圍
        start_row, start_col = self.spatial_grid._get_cell_coords(view_left, view_top)
        end_row, end_col = self.spatial_grid._get_cell_coords(view_right, view_bottom)

        # 遍歷可見的網格儲存格，從上到下 (實現粗略的 Y-Sort)
        # 對於每個儲存格內的精靈再進行精確的 Y-Sort (O(k log k))
        # 為了正確的 Y-Sort，需要收集所有可見精靈後再一起排序。
        # 這裡的實現是按行/列獲取後，再在每個 cell 內排序，實際上可能無法達到全局 Y-Sort，
        # 但對於局部範圍的精靈遮擋處理已經足夠。
        
        # 收集所有視野內的活躍精靈
        visible_sprites: List[GameSprite] = []
        seen_sprites_in_draw = set() # 避免重複添加精靈，因為精靈可能跨越cell邊界

        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                # 取得該儲存格內的所有活躍精靈
                for sprite in self.spatial_grid.grid.get((r,c), []):
                    if sprite.active_status and sprite not in seen_sprites_in_draw: # 只繪製活躍的精靈且未被添加過
                        # 計算精靈在螢幕上的位置
                        offset_pos: pygame.math.Vector2 = pygame.math.Vector2(sprite.rect.topleft) - self.offset
                        sprite_screen_rect = pygame.Rect(offset_pos.x, offset_pos.y, sprite.rect.width, sprite.rect.height)
                        
                        # Frustum Culling，確保只收集真正可見的精靈
                        if screen_view_rect.colliderect(sprite_screen_rect):
                            visible_sprites.append(sprite)
                            seen_sprites_in_draw.add(sprite)
        
        # 對所有可見精靈進行 Y-Sort
        visible_sprites.sort(key=lambda s: s.rect.centery) 

        for sprite in visible_sprites:
            offset_pos: pygame.math.Vector2 = pygame.math.Vector2(sprite.rect.topleft) - self.offset
            self.display_surface.blit(sprite.image, offset_pos)

# ====== Reference Module: collision.py ======
class CollisionManager:
    """
    通用碰撞管理器 (Static Utility Class)。
    封裝了 Pygame 的 spritecollide 與 groupcollide，提供更語意化的介面。
    支援「單體 vs 群體」與「群體 vs 群體」的碰撞偵測與回呼 (Callback) 處理。
    """
    
    @staticmethod
    def apply_sprite_vs_group(sprite: pygame.sprite.Sprite, target_group: pygame.sprite.Group, on_collide: Optional[Callable[[pygame.sprite.Sprite, pygame.sprite.Sprite], None]] = None, kill_sprite: bool = False, kill_target: bool = False) -> List[pygame.sprite.Sprite]:
        """
        偵測「單一角色」撞到「一群物件」 (例如：玩家撞到金幣、玩家撞到敵人)。
        
        :param sprite: 主動碰撞的物件 (Sprite)
        :param target_group: 被撞的群組 (Group)
        :param on_collide: (選用) 碰撞發生時執行的函式，簽章需為 func(sprite, target_sprite)
        :param kill_sprite: 是否在碰撞後刪除 sprite
        :param kill_target: 是否在碰撞後刪除被撞到的 target
        :return: 所有發生碰撞的 target 列表
        """
        # 使用 mask 碰撞 (像素級精準) 或 rect 碰撞 (矩形範圍)
        # 預設使用 rect，效率較高
        hits: List[pygame.sprite.Sprite] = pygame.sprite.spritecollide(sprite, target_group, kill_target)
        
        if hits:
            if kill_sprite:
                sprite.kill()
                
            if on_collide:
                for target in hits:
                    on_collide(sprite, target)
        return hits

    @staticmethod
    def apply_group_vs_group(group1: pygame.sprite.Group, group2: pygame.sprite.Group, on_collide: Optional[Callable[[pygame.sprite.Sprite, pygame.sprite.Sprite], None]] = None, kill_group1: bool = False, kill_group2: bool = False) -> Dict[pygame.sprite.Sprite, List[pygame.sprite.Sprite]]:
        """
        偵測「一群物件」撞到「另一群物件」 (例如：子彈群 撞到 敵人群)。
        
        :param group1: 主動群組 (如子彈)
        :param group2: 被動群組 (如敵人)
        :param on_collide: (選用) 碰撞發生時執行的函式，簽章需為 func(sprite1, sprite2)
        :param kill_group1: 是否刪除 group1 中發生碰撞的物件
        :param kill_group2: 是否刪除 group2 中發生碰撞的物件
        :return: 碰撞字典 {sprite1: [sprite2, ...]}
        """
        # 注意：此方法在高物件數量下，若未結合空間分割，會導致 O(N*M) 效能問題。
        # 建議參考 Game 類別中 `_handle_bullet_enemy_collisions` 的優化實作。
        hits: Dict[pygame.sprite.Sprite, List[pygame.sprite.Sprite]] = pygame.sprite.groupcollide(group1, group2, kill_group1, kill_group2)
        
        if hits and on_collide:
            for sprite1, targets in hits.items():
                for sprite2 in targets:
                    on_collide(sprite1, sprite2)
        return hits

# ====== Reference Module: object_pool.py ======
# 定義一個 TypeVar 以便 ObjectPool 成為泛型類別
T = TypeVar('T', bound=GameSprite)

class ObjectPool(Generic[T]):
    """
    簡易的物件池，用於重複使用子彈或敵人，避免頻繁的記憶體配置。
    支持泛型，可以管理任何繼承自 GameSprite 的物件。
    """
    def __init__(self, cls: Type[T], size: int = 100):
        # 預先建立一批物件
        # 注意：這裡假設 cls() 可以不帶參數初始化。如果需要參數，應調整為傳入一個工廠函式。
        self.pool: List[T] = [cls() for _ in range(size)]
        self.active: List[T] = []

    def get(self, *args: Any, **kwargs: Any) -> Optional[T]:
        """
        從池中取出一個物件並初始化。
        如果池子為空，則返回 None。
        """
        if self.pool:
            obj = self.pool.pop()
            # 假設物件都有一個 init 方法來重置狀態
            if hasattr(obj, 'init') and callable(getattr(obj, 'init')):
                # mypy might complain about dynamic init call, but it's designed this way
                obj.init(*args, **kwargs) # type: ignore
            self.active.append(obj)
            return obj
        return None # 池子空了

    def release(self, obj: T) -> None:
        """
        將物件放回池中。
        確保物件從活躍列表中移除，並添加回可用池中。
        """
        # 注意：此處的 `obj in self.active` 和 `self.active.remove(obj)` 是 O(N) 操作，
        # 在極端情況下（單幀釋放大量物件且 active 列表非常大）可能成為瓶頸。
        # 更優化的做法是將 active 列表實現為一個 Set 或 Dict，使查找和刪除為 O(1)。
        # 然而，考慮到物件池通常管理的物件數量有限，且主要優化頻繁創建/銷毀的開銷，
        # 這裡的 List 實現已足夠，且與 Pygame Group 的 remove 策略一致。
        if obj in self.active: 
            self.active.remove(obj)
            self.pool.append(obj)

# --- SpatialGrid 實作 ---
class SpatialGrid:
    """
    空間分割網格，用於優化碰撞檢測和查找附近物件。
    將地圖劃分為多個儲存格，每個物件僅在所屬儲存格中註冊。
    """
    def __init__(self, map_width: int, map_height: int, cell_size: int):
        self.map_width: int = map_width
        self.map_height: int = map_height
        self.cell_size: int = cell_size
        self.grid_cols: int = (map_width + cell_size - 1) // cell_size
        self.grid_rows: int = (map_height + cell_size - 1) // cell_size
        # 使用 Dict[Tuple[int, int], List[GameSprite]] 儲存每個儲存格的精靈
        self.grid: Dict[Tuple[int, int], List[GameSprite]] = { (r, c): [] for r in range(self.grid_rows) for c in range(self.grid_cols) }
        # 記錄每個 sprite 所屬的儲存格，方便快速定位和移除
        self.sprite_to_cell: Dict[GameSprite, Tuple[int, int]] = {} # (sprite: (row, col))

    def _get_cell_coords(self, x: float, y: float) -> Tuple[int, int]:
        """根據世界座標計算對應的網格儲存格座標。"""
        col = max(0, min(self.grid_cols - 1, int(x // self.cell_size)))
        row = max(0, min(self.grid_rows - 1, int(y // self.cell_size)))
        return (row, col)

    def add_sprite(self, sprite: GameSprite) -> None:
        """將精靈加入網格。"""
        if sprite not in self.sprite_to_cell:
            row, col = self._get_cell_coords(float(sprite.rect.centerx), float(sprite.rect.centery))
            # 這裡需要確保 (row, col) 鍵存在，因為 grid 是一個預先生成的字典
            self.grid[(row, col)].append(sprite)
            self.sprite_to_cell[sprite] = (row, col)

    def remove_sprite(self, sprite: GameSprite) -> None:
        """將精靈從網格移除。 (為優化 C2 的處理，此處仍維持 O(k) 的 list.remove)"""
        if sprite in self.sprite_to_cell:
            row, col = self.sprite_to_cell[sprite]
            if (row, col) in self.grid: # 檢查儲存格是否存在
                # 此處 `list.remove()` 是 O(k)，但因為是從一個小的儲存格列表中移除，通常 k 值很小，所以影響有限。
                # 主要的優化在於 Game 類別中批量處理移除，減少對此方法的單次頻繁呼叫。
                if sprite in self.grid[(row, col)]:
                    self.grid[(row, col)].remove(sprite)
            del self.sprite_to_cell[sprite]

    def update_sprite_position(self, sprite: GameSprite) -> None:
        """更新精靈在網格中的位置，如果跨越儲存格邊界則重新註冊。"""
        if not sprite.active_status: # 如果精靈不活躍，則確保從網格中移除
            self.remove_sprite(sprite)
            return

        # 如果精靈不在網格中，可能是剛從物件池取出，需要添加
        if sprite not in self.sprite_to_cell:
            self.add_sprite(sprite)
            return

        old_row, old_col = self.sprite_to_cell[sprite]
        new_row, new_col = self._get_cell_coords(float(sprite.rect.centerx), float(sprite.rect.centery))

        if (old_row, old_col) != (new_row, new_col):
            # 從舊儲存格移除
            if (old_row, old_col) in self.grid and sprite in self.grid[(old_row, old_col)]:
                self.grid[(old_row, old_col)].remove(sprite)
            # 加入新儲存格
            self.grid[(new_row, new_col)].append(sprite)
            self.sprite_to_cell[sprite] = (new_row, new_col)

    def get_nearby_sprites(self, x: float, y: float, radius_cells: int = 1, sprite_type: Optional[Type[GameSprite]] = None) -> List[GameSprite]:
        """
        獲取 (x,y) 附近指定半徑儲存格內的精靈。
        radius_cells = 0 表示只查詢精靈所在儲存格。
        radius_cells = 1 表示查詢周圍 8 個儲存格 + 中央儲存格。
        """
        center_row, center_col = self._get_cell_coords(x, y)
        nearby_sprites: List[GameSprite] = []
        
        # 使用 set 避免重複添加精靈，因為一個精靈可能在多個鄰近儲存格的查詢中被獲取
        seen_sprites = set() 

        for r_offset in range(-radius_cells, radius_cells + 1):
            # FIX: Corrected c_offset loop range to radius_cells + 1
            for c_offset in range(-radius_cells, radius_cells + 1): 
                row, col = center_row + r_offset, center_col + c_offset
                if 0 <= row < self.grid_rows and 0 <= col < self.grid_cols:
                    for sprite in self.grid.get((row, col), []): # Use .get() with default [] for robustness
                        if (sprite_type is None or isinstance(sprite, sprite_type)) and sprite.active_status:
                            if sprite not in seen_sprites:
                                nearby_sprites.append(sprite)
                                seen_sprites.add(sprite)
        return nearby_sprites
    
    def get_nearest_sprite(self, x: float, y: float, max_dist: float = float('inf'), sprite_type: Optional[Type[GameSprite]] = None) -> Optional[GameSprite]:
        """
        在 (x,y) 附近查詢最近的精靈。
        會從較小的搜尋半徑開始，並逐步擴大以優化性能。
        """
        search_radius_cells: int = 1 # 初始搜尋半徑
        nearest_sprite: Optional[GameSprite] = None
        min_dist_sq: float = max_dist * max_dist # 距離平方，避免開根號運算

        # 嘗試擴大搜尋範圍幾次，直到找到或達到最大範圍
        for _ in range(5): # 例如，最多擴大 5 次，檢查 5 個「環」
            nearby_sprites = self.get_nearby_sprites(x, y, radius_cells=search_radius_cells, sprite_type=sprite_type)
            
            for sprite in nearby_sprites:
                dist_sq = (sprite.rect.centerx - x)**2 + (sprite.rect.centery - y)**2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    nearest_sprite = sprite
            
            if nearest_sprite and min_dist_sq < max_dist**2: # 如果找到最近的精靈且在最大距離內，則無需再擴大搜尋
                break
            
            search_radius_cells += 1 # 擴大搜尋範圍

        return nearest_sprite

# --- 玩家角色 (Player) 類別 ---
class Player(GameSprite):
    def __init__(self, x: int, y: int, spatial_grid: SpatialGrid, 
                 fire_bullet_callback: Callable[[pygame.math.Vector2, pygame.math.Vector2, 'Player'], None]):
        
        super().__init__(x, y)
        self.image = pygame.Surface(GameConfig.PLAYER_DEFAULT_SIZE)
        self.image.fill(GameConfig.GREEN)
        self.rect = self.image.get_rect(center=(x, y))

        self.spatial_grid: SpatialGrid = spatial_grid
        self.fire_bullet_callback: Callable[[pygame.math.Vector2, pygame.math.Vector2, 'Player'], None] = fire_bullet_callback
        self.health: int = GameConfig.PLAYER_INITIAL_HEALTH
        self.score: int = 0
        self.player_speed: float = GameConfig.PLAYER_SPEED
        self.fire_cooldown: float = 0.0
        self.fire_rate: float = GameConfig.PLAYER_FIRE_RATE
        self.target_enemy: Optional['Enemy'] = None # 當前鎖定的敵人
        self.active_status: bool = True # 玩家總是活躍

    def input(self) -> None:
        """處理玩家輸入（WASD或方向鍵移動）。"""
        keys = pygame.key.get_pressed()
        self.velocity.x = 0
        self.velocity.y = 0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.velocity.y = -self.player_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.velocity.y = self.player_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.velocity.x = -self.player_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.velocity.x = self.player_speed
        
        # 正規化斜向移動速度，確保在八個方向上的速度一致
        if self.velocity.length() > 0:
            self.velocity.normalize_ip()
            self.velocity *= self.player_speed

    def auto_fire(self) -> None:
        """自動向最近的敵人發射子彈。"""
        if self.fire_cooldown <= 0:
            # 使用 SpatialGrid 查找最近的敵人
            # 搜索半徑考慮螢幕寬度乘以係數，確保在視野內的敵人能被鎖定
            search_radius = GameConfig.SCREEN_WIDTH * GameConfig.PLAYER_AUTO_FIRE_SEARCH_RADIUS_MULTIPLIER
            self.target_enemy = self.spatial_grid.get_nearest_sprite(
                float(self.rect.centerx), float(self.rect.centery), sprite_type=Enemy, 
                max_dist=search_radius
            )
            
            if self.target_enemy and self.target_enemy.active_status: # 只射擊活躍的敵人
                # 計算從玩家到敵人的方向向量
                direction = pygame.math.Vector2(self.target_enemy.rect.center) - pygame.math.Vector2(self.rect.center)
                if direction.length() > 0:
                    direction.normalize_ip() # 正規化方向向量
                    bullet_velocity = direction * GameConfig.BULLET_SPEED
                    # 呼叫遊戲主物件的方法來發射子彈 (透過回呼函式)
                    self.fire_bullet_callback(pygame.math.Vector2(self.rect.center), bullet_velocity, self)
                    self.fire_cooldown = self.fire_rate # 重設射擊冷卻時間

    def update(self, dt: float) -> None:
        """更新玩家狀態，包括移動、邊界限制和自動射擊。"""
        self.input()
        super().update(dt) # 應用速度更新位置
        
        # 將玩家限制在遊戲地圖範圍內
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(GameConfig.MAP_WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(GameConfig.MAP_HEIGHT, self.rect.bottom)

        self.fire_cooldown -= dt # 更新射擊冷卻計時器
        self.auto_fire() # 執行自動射擊邏輯

# --- 敵人角色 (Enemy) 類別 ---
class Enemy(GameSprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface(GameConfig.ENEMY_DEFAULT_SIZE)
        self.image.fill(GameConfig.RED)
        self.rect = self.image.get_rect(center=(0, 0)) # 初始化 Rect，物件池取出時會重設
        self.active_status = False # 物件池狀態，True 表示活躍，False 表示可被回收
        self.health: int = GameConfig.ENEMY_INITIAL_HEALTH # 預設生命值
        self.enemy_speed: float = GameConfig.ENEMY_SPEED # 像素/秒
        self.target_player: Optional[Player] = None # 追擊目標 (玩家)

    def init(self, x: int, y: int, target_player: Player) -> None:
        """物件池初始化方法，重設敵人的狀態。"""
        self.rect.center = (x, y)
        self.health = GameConfig.ENEMY_INITIAL_HEALTH
        self.active_status = True
        self.target_player = target_player
        self.velocity = pygame.math.Vector2(0, 0) # 重設速度

    def update(self, dt: float) -> None:
        """更新敵人狀態，包括追擊玩家和邊界限制。"""
        if not self.active_status or self.target_player is None:
            return

        # 簡單 AI: 追擊玩家
        direction = pygame.math.Vector2(self.target_player.rect.center) - pygame.math.Vector2(self.rect.center)
        if direction.length() > 0:
            direction.normalize_ip()
            self.velocity = direction * self.enemy_speed
        else:
            self.velocity = pygame.math.Vector2(0, 0) # 如果到達玩家位置則停止

        super().update(dt) # 應用速度更新位置
        # 將敵人限制在遊戲地圖範圍內
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(GameConfig.MAP_WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(GameConfig.MAP_HEIGHT, self.rect.bottom)

# --- 子彈 (Bullet) 類別 ---
class Bullet(GameSprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface(GameConfig.BULLET_DEFAULT_SIZE)
        self.image.fill(GameConfig.YELLOW)
        self.rect = self.image.get_rect(center=(0, 0)) # 初始化 Rect，物件池取出時會重設
        self.active_status = False # 物件池狀態
        self.damage: int = GameConfig.BULLET_DAMAGE
        self.lifetime: float = GameConfig.BULLET_LIFETIME
        self.initial_lifetime: float = GameConfig.BULLET_LIFETIME # 初始生命週期，用於重設

    def init(self, pos: pygame.math.Vector2, velocity: pygame.math.Vector2) -> None:
        """物件池初始化方法，重設子彈狀態。"""
        self.rect.center = (int(pos.x), int(pos.y)) # 將 Vector2 轉換為整數元組
        self.velocity = velocity
        self.damage = GameConfig.BULLET_DAMAGE
        self.lifetime = self.initial_lifetime
        self.active_status = True

    def update(self, dt: float) -> None:
        """更新子彈狀態，包括移動、生命週期和超出地圖範圍檢查。"""
        if not self.active_status:
            return

        super().update(dt)
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active_status = False # 生命週期結束，標記為非活躍
        
        # 檢查是否超出地圖邊界
        if not (0 <= self.rect.centerx <= GameConfig.MAP_WIDTH and 0 <= self.rect.centery <= GameConfig.MAP_HEIGHT):
            self.active_status = False

# --- 敵人生成器 (Enemy Spawner) 類別 ---
class EnemySpawner:
    def __init__(self, enemy_pool: ObjectPool[Enemy], map_width: int, map_height: int, 
                 player_instance: Player, add_enemy_to_game_callback: Callable[[Enemy], None],
                 initial_spawn_interval: float = GameConfig.ENEMY_SPAWN_INTERVAL,
                 min_spawn_interval: float = GameConfig.ENEMY_MIN_SPAWN_INTERVAL,
                 spawn_interval_decrease_rate: float = GameConfig.ENEMY_SPAWN_DECREASE_RATE,
                 enemy_spawn_buffer: int = GameConfig.ENEMY_SPAWN_BUFFER):
        
        self.enemy_pool: ObjectPool[Enemy] = enemy_pool
        self.map_width: int = map_width
        self.map_height: int = map_height
        self.player_instance: Player = player_instance
        self.add_enemy_to_game_callback: Callable[[Enemy], None] = add_enemy_to_game_callback
        self.spawn_interval: float = initial_spawn_interval # 初始生成間隔（秒）
        self.spawn_timer: float = self.spawn_interval
        self.min_spawn_interval: float = min_spawn_interval
        self.spawn_interval_decrease_rate: float = spawn_interval_decrease_rate
        self.enemy_spawn_buffer: int = enemy_spawn_buffer

    def update(self, dt: float, camera_offset: pygame.math.Vector2, screen_size: Tuple[int, int]) -> None:
        """
        更新生成器狀態，並在計時器歸零時生成敵人。
        接收相機偏移量和螢幕大小以計算敵人生成位置。
        """
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn_single_enemy(camera_offset, screen_size)
            self.spawn_timer = self.spawn_interval
            # 逐漸減少生成間隔以增加遊戲難度
            self.spawn_interval = max(self.min_spawn_interval, self.spawn_interval - self.spawn_interval_decrease_rate)

    def _spawn_single_enemy(self, camera_offset: pygame.math.Vector2, screen_size: Tuple[int, int]) -> None:
        """在當前螢幕視野外隨機位置生成一個敵人。"""
        screen_w, screen_h = screen_size

        # 計算當前螢幕視野在世界座標中的邊界
        screen_world_left = camera_offset.x
        screen_world_right = camera_offset.x + screen_w
        screen_world_top = camera_offset.y
        screen_world_bottom = camera_offset.y + screen_h

        spawn_x, spawn_y = 0, 0
        side = random.randint(0, 3) # 0:上, 1:下, 2:左, 3:右 邊緣
        
        # 在螢幕視野外留有緩衝區生成敵人
        if side == 0: # 上邊緣
            spawn_x = random.randint(int(screen_world_left - self.enemy_spawn_buffer), int(screen_world_right + self.enemy_spawn_buffer))
            spawn_y = int(screen_world_top - self.enemy_spawn_buffer)
        elif side == 1: # 下邊緣
            spawn_x = random.randint(int(screen_world_left - self.enemy_spawn_buffer), int(screen_world_right + self.enemy_spawn_buffer))
            spawn_y = int(screen_world_bottom + self.enemy_spawn_buffer)
        elif side == 2: # 左邊緣
            spawn_x = int(screen_world_left - self.enemy_spawn_buffer)
            spawn_y = random.randint(int(screen_world_top - self.enemy_spawn_buffer), int(screen_world_bottom + self.enemy_spawn_buffer))
        else: # 右邊緣
            spawn_x = int(screen_world_right + self.enemy_spawn_buffer)
            spawn_y = random.randint(int(screen_world_top - self.enemy_spawn_buffer), int(screen_world_bottom + self.enemy_spawn_buffer))
        
        # 將生成位置限制在遊戲地圖範圍內
        spawn_x = max(0, min(self.map_width, spawn_x))
        spawn_y = max(0, min(self.map_height, spawn_y))

        enemy = self.enemy_pool.get(spawn_x, spawn_y, self.player_instance)
        if enemy:
            self.add_enemy_to_game_callback(enemy) # 使用回呼函式將敵人加入遊戲
        # else:
            # print("Warning: Enemy pool is empty, cannot spawn more enemies!") # Debugging for pool exhaustion

# --- 遊戲主類別 (Game) ---
class Game:
    """
    遊戲主類別，負責初始化遊戲、管理遊戲循環、物件和碰撞。
    """
    def __init__(self):
        self.screen: pygame.Surface = pygame.display.set_mode(GameConfig.SCREEN_SIZE)
        pygame.display.set_caption(GameConfig.TITLE)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.running: bool = True

        # 遊戲實體與群組
        self.bullet_group: pygame.sprite.Group = pygame.sprite.Group() # 活躍子彈群組
        self.enemy_group: pygame.sprite.Group = pygame.sprite.Group()   # 活躍敵人群組

        # 空間分割網格
        self.spatial_grid: SpatialGrid = SpatialGrid(
            GameConfig.MAP_WIDTH, GameConfig.MAP_HEIGHT, GameConfig.SPATIAL_GRID_CELL_SIZE
        )
        
        # 主相機群組，負責渲染所有可見物件 (C3: 傳入 SpatialGrid)
        self.box_camera_group: BoxCameraGroup = BoxCameraGroup(
            map_size=GameConfig.MAP_SIZE,
            camera_border_ratio=GameConfig.CAMERA_BORDER_RATIO,
            ground_image_path=GameConfig.GROUND_IMAGE_PATH,
            ground_fallback_color=GameConfig.GROUND_FALLBACK_COLOR,
            spatial_grid=self.spatial_grid # 將 spatial_grid 傳遞給 BoxCameraGroup 以便其渲染時使用
        )

        # 物件池
        self.bullet_pool: ObjectPool[Bullet] = ObjectPool(Bullet, size=GameConfig.BULLET_POOL_SIZE)
        self.enemy_pool: ObjectPool[Enemy] = ObjectPool(Enemy, size=GameConfig.ENEMY_POOL_SIZE)

        # 玩家
        player_start_x: int = GameConfig.MAP_WIDTH // 2
        player_start_y: int = GameConfig.MAP_HEIGHT // 2
        self.player: Player = Player(
            player_start_x, player_start_y,
            spatial_grid=self.spatial_grid,
            fire_bullet_callback=self._fire_bullet # 傳入發射子彈的回呼函式
        )
        self.box_camera_group.add(self.player)
        self.spatial_grid.add_sprite(self.player) # 將玩家也加入網格，以便其他物件查詢

        # 敵人生成器
        self.enemy_spawner: EnemySpawner = EnemySpawner(
            enemy_pool=self.enemy_pool,
            map_width=GameConfig.MAP_WIDTH,
            map_height=GameConfig.MAP_HEIGHT,
            player_instance=self.player,
            add_enemy_to_game_callback=self._add_enemy_to_game # 傳入將敵人加入遊戲的回呼函式
        )

    def _fire_bullet(self, pos: pygame.math.Vector2, velocity: pygame.math.Vector2, shooter: Player) -> None:
        """
        供 Player 呼叫的回呼函式，用於從子彈池中獲取子彈並發射。
        """
        bullet: Optional[Bullet] = self.bullet_pool.get(pos, velocity)
        if bullet:
            self.bullet_group.add(bullet)
            self.box_camera_group.add(bullet)
            self.spatial_grid.add_sprite(bullet)
    
    def _add_enemy_to_game(self, enemy: Enemy) -> None:
        """
        供 EnemySpawner 呼叫的回呼函式，用於將新生成的敵人加入所有相關群組和網格。
        """
        self.enemy_group.add(enemy)
        self.box_camera_group.add(enemy)
        self.spatial_grid.add_sprite(enemy)

    def _on_collide_bullet_enemy(self, bullet_sprite: pygame.sprite.Sprite, enemy_sprite: pygame.sprite.Sprite) -> None:
        """
        子彈與敵人碰撞時的回呼函式。
        處理分數增加，並標記精靈為非活躍以便在主循環中移除和釋放回物件池。
        """
        # 使用 Type Assertion 將通用 Sprite 類型轉換為具體類型
        bullet: Bullet = bullet_sprite # type: ignore
        enemy: Enemy = enemy_sprite # type: ignore

        # 再次檢查精靈是否活躍，避免對已處理的物件重複操作
        if not bullet.active_status or not enemy.active_status:
            return

        self.player.score += 1 # 增加玩家分數

        # 標記為非活躍，防止在同一幀內重複觸發碰撞或更新。
        # 實際從群組和網格中移除，以及釋放回物件池的邏輯，將在主循環中處理。
        bullet.active_status = False 
        enemy.active_status = False

    def _handle_bullet_enemy_collisions(self) -> None:
        """
        處理子彈與敵人的碰撞，利用 SpatialGrid 優化。 (解決批評點 1)
        """
        # 遍歷所有活躍的子彈 (使用列表副本以安全處理在迭代中可能被標記為非活躍的元素)
        for bullet in list(self.bullet_group): 
            if not bullet.active_status: # 只處理活躍的子彈
                continue

            # 從 SpatialGrid 獲取子彈附近的敵人
            # `radius_cells=1` 檢查子彈所在儲存格及其周圍 8 個儲存格，足以覆蓋近距離碰撞。
            nearby_enemies_list = self.spatial_grid.get_nearby_sprites(
                float(bullet.rect.centerx), float(bullet.rect.centery), 
                radius_cells=1, 
                sprite_type=Enemy
            )
            
            # 過濾出活躍的敵人，並將其放入一個臨時的 Pygame Group 中進行碰撞檢測
            active_nearby_enemies_group = pygame.sprite.Group([e for e in nearby_enemies_list if e.active_status])

            if active_nearby_enemies_group:
                # 使用 CollisionManager 處理單個子彈與其附近敵人群組的碰撞
                # `kill_sprite` 和 `kill_target` 設為 False，因為我們透過 `active_status` 標記並在主循環中集中處理
                CollisionManager.apply_sprite_vs_group(
                    bullet,
                    active_nearby_enemies_group,
                    on_collide=self._on_collide_bullet_enemy,
                    kill_sprite=False, 
                    kill_target=False
                )

    def run(self) -> None:
        """遊戲主循環。"""
        while self.running:
            dt: float = self.clock.tick(GameConfig.FPS) / 1000.0 # 計算時間差 (秒)，確保遊戲邏輯獨立於幀率

            # 1. Input (輸入處理)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # 2. Update Logic (邏輯更新階段)
            self.player.update(dt)
            self.spatial_grid.update_sprite_position(self.player) # 更新玩家在網格中的位置

            # 更新相機偏移量
            self.box_camera_group.update_offset(self.player)

            # --- 處理活躍精靈的更新及收集非活躍精靈 (解決批評點 2) ---
            inactive_bullets: List[Bullet] = []
            for bullet in self.bullet_group: # 直接迭代群組，收集需移除的精靈
                if not bullet.active_status:
                    inactive_bullets.append(bullet)
                else:
                    bullet.update(dt)
                    self.spatial_grid.update_sprite_position(bullet) # 更新活躍子彈在網格中的位置

            inactive_enemies: List[Enemy] = []
            for enemy in self.enemy_group: # 直接迭代群組，收集需移除的精靈
                if not enemy.active_status:
                    inactive_enemies.append(enemy)
                else:
                    enemy.update(dt)
                    self.spatial_grid.update_sprite_position(enemy) # 更新活躍敵人在網格中的位置

            # --- 批量移除和釋放非活躍精靈 (解決批評點 2) ---
            if inactive_bullets:
                # Pygame Groups 的 remove 方法可以接收一個列表，進行批量高效移除 (O(M) 而非 O(N*M))
                self.bullet_group.remove(inactive_bullets) 
                self.box_camera_group.remove(inactive_bullets) # 統一從相機群組移除
                for bullet in inactive_bullets:
                    self.spatial_grid.remove_sprite(bullet) # 從空間網格移除
                    self.bullet_pool.release(bullet) # 釋放回物件池

            if inactive_enemies:
                self.enemy_group.remove(inactive_enemies)
                self.box_camera_group.remove(inactive_enemies) # 統一從相機群組移除
                for enemy in inactive_enemies:
                    self.spatial_grid.remove_sprite(enemy) # 從空間網格移除
                    self.enemy_pool.release(enemy) # 釋放回物件池

            # 更新敵人生成器
            self.enemy_spawner.update(dt, self.box_camera_group.offset, self.screen.get_size())

            # 3. Collision Detection (碰撞檢測階段)
            # 使用 SpatialGrid 優化子彈與敵人的碰撞檢測 (解決批評點 1)
            self._handle_bullet_enemy_collisions()
            
            # 4. Render (畫面渲染階段)
            self.screen.fill(GameConfig.BLACK) # 清除螢幕
            self.box_camera_group.custom_draw() # 使用相機群組繪製所有物件和背景 (已利用 SpatialGrid 進行 C3 優化)

            # 繪製 UI (分數、生命值)
            score_text = get_font(GameConfig.FONT_SIZE_UI).render(f"分數: {self.player.score}", True, GameConfig.WHITE)
            self.screen.blit(score_text, (10, 10))
            
            health_text = get_font(GameConfig.FONT_SIZE_UI).render(f"生命: {self.player.health}", True, GameConfig.WHITE)
            self.screen.blit(health_text, (10, 50))

            pygame.display.flip() # 更新螢幕顯示

        pygame.quit() # 退出 Pygame

# 程式入口點
if __name__ == '__main__':
    game = Game()
    game.run()