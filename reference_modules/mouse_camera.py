# tags: camera, mouse-control, rts-camera, edge-panning, y-sort
import pygame

class MouseCameraGroup(pygame.sprite.Group):
    """
    滑鼠控制相機 (RTS Style / Edge Panning)。
    
    功能：
    1. 當滑鼠游標移動到視窗邊緣時，相機自動捲動。
    2. 實作了「滑鼠鎖定/回彈」機制，當游標超出邊界時會自動彈回，產生無限捲動的手感。
    3. 內建 Y-Sort (深度排序) 渲染。
    
    適用遊戲類型：RTS (即時戰略)、模擬經營、塔防遊戲。
    """
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        
        # 1. 相機偏移量與速度設定
        self.offset = pygame.math.Vector2()
        self.mouse_speed = 0.5 # 捲動速度 (可依需求調整)

        # 2. 設定邊界觸發範圍 (Edge Thresholds)
        # 代表滑鼠距離邊緣多少像素時會觸發移動
        self.camera_borders = {
            'left': 100,
            'right': 100,
            'top': 100,
            'bottom': 100
        }

        # 3. 背景設定 (防呆載入)
        try:
            self.ground_surf = pygame.image.load("Graphic/ground2.png").convert_alpha()
            # 預設做一張很大的地圖供捲動
            self.ground_surf = pygame.transform.scale(self.ground_surf, (2500, 2500))
        except Exception:
            self.ground_surf = pygame.Surface((2500, 2500))
            self.ground_surf.fill((50, 60, 50)) # 深灰色地面
            
        self.ground_rect = self.ground_surf.get_rect(topleft=(0, 0))

    def mouse_control(self):
        """核心邏輯：偵測滑鼠位置並更新相機偏移量"""
        mouse = pygame.math.Vector2(pygame.mouse.get_pos())
        mouse_offset_vector = pygame.math.Vector2()

        # 取得畫面大小與邊界定義
        screen_w, screen_h = self.display_surface.get_size()
        left_border = self.camera_borders['left']
        top_border = self.camera_borders['top']
        right_border = screen_w - self.camera_borders['right']
        bottom_border = screen_h - self.camera_borders['bottom']

        # --- 邏輯區塊：判定滑鼠是否在邊界區域並計算偏移 ---
        if top_border < mouse.y < bottom_border:
            if mouse.x < left_border:
                mouse_offset_vector.x = mouse.x - left_border
                pygame.mouse.set_pos((left_border, mouse.y))
            if mouse.x > right_border:
                mouse_offset_vector.x = mouse.x - right_border
                pygame.mouse.set_pos((right_border, mouse.y))
        elif mouse.y < top_border:
            if mouse.x < left_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(left_border, top_border)
                pygame.mouse.set_pos((left_border, top_border))
            if mouse.x > right_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(right_border, top_border)
                pygame.mouse.set_pos((right_border, top_border))
        elif mouse.y > bottom_border:
            if mouse.x < left_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(left_border, bottom_border)
                pygame.mouse.set_pos((left_border, bottom_border))
            if mouse.x > right_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(right_border, bottom_border)
                pygame.mouse.set_pos((right_border, bottom_border))

        if left_border < mouse.x < right_border:
            if mouse.y < top_border:
                mouse_offset_vector.y = mouse.y - top_border
                pygame.mouse.set_pos((mouse.x, top_border))
            if mouse.y > bottom_border:
                mouse_offset_vector.y = mouse.y - bottom_border
                pygame.mouse.set_pos((mouse.x, bottom_border))

        # 更新相機總偏移量
        self.offset += mouse_offset_vector * self.mouse_speed

    def custom_draw(self):
        """渲染循環：呼叫滑鼠控制 + Y-Sort 繪製"""
        
        # 每一幀都執行滑鼠偵測
        self.mouse_control()

        # 1. 畫地圖
        ground_offset = self.ground_rect.topleft - self.offset
        self.display_surface.blit(self.ground_surf, ground_offset)
        
        # 2. 畫角色 (Y-Sort)
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)