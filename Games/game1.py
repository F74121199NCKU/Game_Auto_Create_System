import pygame
import random
import collections
import enum
from pygame.math import Vector2

# --- RAG 類別定義開始 ---
# 基礎精靈類別: GameSprite
# 負責處理位置與移動，並維持 pygame 的 Sprite 屬性一致性。
class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image=None, rect=None, pos=None, velocity=None):
        super().__init__()
        # 如果沒有 image，則建立一個透明的 1x1 Surface
        self.image = image if image is not None else pygame.Surface((1, 1), pygame.SRCALPHA)
        # 如果沒有 rect，則從 image 獲取
        self.rect = rect if rect is not None else self.image.get_rect()
        # pos 使用 Vector2 以確保高精度的位置運算 (相對於整數像素)
        self.pos = pos if pos is not None else Vector2(self.rect.topleft)
        self.velocity = velocity if velocity is not None else Vector2(0, 0)
        # 重要指令: GameSprite 類別中不處理自動更新。
        # 子類別應在邏輯中自行更新，並確保 rect 與 pos 保持同步。

    def update(self, dt):
        # 基礎更新邏輯：在子類別中根據速度與時間步長進行運算。
        # 由於貪食蛇是格子運動，我們通常直接手動更新 pos/rect，而不依賴此處的自動更新。
        pass

# 物件池類別: ObjectPool
# 用於管理頻繁創建與銷毀的物件（如食物），提高記憶體與效能表現。
class ObjectPool:
    def __init__(self, object_factory, initial_size=10):
        self._object_factory = object_factory
        self._pool = collections.deque()
        self._active_objects = set()
        for _ in range(initial_size):
            self._pool.append(self._object_factory()) # 預先生成物件緩衝

    def get(self, *args, **kwargs):
        # 從物件池中獲取物件，若池空則創建新物件。
        if not self._pool:
            obj = self._object_factory()
        else:
            obj = self._pool.popleft()

        # 如果物件有 'reset' 方法，則呼叫它來初始化物件狀態。
        if hasattr(obj, 'reset'):
            obj.reset(*args, **kwargs)
        
        self._active_objects.add(obj)
        return obj

    def release(self, obj):
        # 將物件歸還至物件池中。
        if obj in self._active_objects:
            self._active_objects.remove(obj)
            self._pool.append(obj)
            # 將精靈從所有群組中移除，避免它繼續在畫面上渲染。
            obj.kill() 

# --- RAG 類別定義結束 ---

# 遊戲狀態枚舉 (Game States)
class GameStates(enum.Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3
    RULES = 4

# 遊戲常數設定
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
GRID_SIZE = 20 # 貪食蛇與食物的大小（格點尺寸）
INITIAL_FPS = 5 # 初始每秒幀數，用來控制蛇的移動速度 (低速開始)
MAX_FPS = 20 # 最高限制速度
FPS_INCREMENT_SCORE_THRESHOLD = 50 # 每獲得 50 分時提升速度
FPS_INCREMENT_VALUE = 1 # 每次提升的 FPS 值

BACKGROUND_COLOR = (0, 0, 0) # 黑色
TEXT_COLOR = (255, 255, 255) # 白色
SNAKE_COLOR = (0, 255, 0) # 綠色
FOOD_COLOR = (255, 0, 0) # 紅色

# 字體設定：優先使用微軟正黑體以支援中文
FONT_NAME = "microsoftjhenghei" 
try:
    pygame.font.match_font(FONT_NAME)
except:
    FONT_NAME = "simhei"
    try:
        pygame.font.match_font(FONT_NAME)
    except:
        FONT_NAME = None # 若找不到字體則回退至預設系統字體

FONT_SIZE_HUD = 24 
FONT_SIZE_MENU_TITLE = 48 
FONT_SIZE_MENU_BUTTON = 32 

BUTTON_BG_COLOR = (50, 50, 50) # 深灰色
BUTTON_HOVER_COLOR = (100, 100, 100) # 亮灰色
BUTTON_TEXT_COLOR = (255, 255, 255) 
BUTTON_WIDTH = 200 
BUTTON_HEIGHT = 50 
BUTTON_MARGIN = 10 

# 遊戲物件類別: 蛇身段
class SnakeSegment(GameSprite):
    def __init__(self, grid_size=GRID_SIZE, color=SNAKE_COLOR):
        image = pygame.Surface((grid_size, grid_size))
        image.fill(color)
        rect = image.get_rect()
        # 初始時放置在畫面外，待邏輯更新位置。
        super().__init__(image=image, rect=rect, pos=Vector2(-grid_size, -grid_size), velocity=Vector2(0,0))
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))

# 遊戲物件類別: 食物
class Food(GameSprite):
    def __init__(self, grid_size=GRID_SIZE, color=FOOD_COLOR):
        image = pygame.Surface((grid_size, grid_size))
        image.fill(color)
        rect = image.get_rect()
        super().__init__(image=image, rect=rect, pos=Vector2(-grid_size, -grid_size), velocity=Vector2(0,0))
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        self._grid_size = grid_size
        self._color = color

    def reset(self, grid_pos):
        # 重新初始化食物位置。
        # grid_pos 傳入格點坐標 (col, row)。
        self.pos = Vector2(grid_pos[0] * self._grid_size, grid_pos[1] * self._grid_size)
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))

# UI 元件: 按鈕
class Button:
    def __init__(self, text, center_x, y, width, height, font, action=None,
                 bg_color=BUTTON_BG_COLOR, hover_color=BUTTON_HOVER_COLOR, text_color=BUTTON_TEXT_COLOR):
        self.rect = pygame.Rect(center_x - width // 2, y, width, height)
        self.font = font
        self.text = text
        self.action = action
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.current_color = self.bg_color

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
        else:
            self.current_color = self.bg_color

        pygame.draw.rect(screen, self.current_color, self.rect, border_radius=5)
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.action:
                    self.action()
                return True
        return False

# 遊戲主程式類別
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("經典貪食蛇遊戲")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.mouse.set_visible(True) 

        self.font_hud = pygame.font.Font(pygame.font.match_font(FONT_NAME), FONT_SIZE_HUD)
        self.font_menu_title = pygame.font.Font(pygame.font.match_font(FONT_NAME), FONT_SIZE_MENU_TITLE)
        self.font_menu_button = pygame.font.Font(pygame.font.match_font(FONT_NAME), FONT_SIZE_MENU_BUTTON)

        self.clock = pygame.time.Clock()
        self.running = True

        # 遊戲狀態初始化
        self.state = GameStates.MENU
        self.previous_state = None 

        self.game_active = False # 初始化為 False

        # 遊戲物件與數據
        self.snake_segments = collections.deque() 
        self.snake_direction = Vector2(0, 0)
        self.new_direction = Vector2(0, 0) 
        self.score = 0
        self.current_fps = INITIAL_FPS 
        self.snake_move_timer = 0 

        # 初始化物件池與精靈群組
        self.food_pool = ObjectPool(lambda: Food(GRID_SIZE, FOOD_COLOR), initial_size=5)
        self.all_sprites = pygame.sprite.Group() 
        self.food_sprite = None 

        # UI 按鈕設置
        self.buttons = []
        self._setup_menus() 

        # 啟動進入選單狀態
        self.change_state(GameStates.MENU)

    def _setup_menus(self):
        # 主選單按鈕
        self.main_menu_buttons = [
            Button("開始遊戲", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.PLAYING)),
            Button("遊戲規則", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.RULES, return_state=GameStates.MENU)),
            Button("結束遊戲", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT + BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, self.quit_game)
        ]

        # 暫停選單按鈕
        self.pause_menu_buttons = [
            Button("繼續遊戲", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 2 - BUTTON_MARGIN * 2, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.PLAYING)),
            Button("重新開始", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.PLAYING, reset=True)),
            Button("遊戲規則", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.RULES, return_state=GameStates.PAUSED)),
            Button("回到主選單", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT + BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.MENU)),
            Button("結束遊戲", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT * 2 + BUTTON_MARGIN * 2, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, self.quit_game)
        ]

        # 遊戲結束按鈕
        self.game_over_menu_buttons = [
            Button("重新開始", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT + BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.PLAYING, reset=True)),
            Button("回到主選單", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT * 2 + BUTTON_MARGIN * 2, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.MENU)),
            Button("結束遊戲", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT * 3 + BUTTON_MARGIN * 3, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, self.quit_game)
        ]
        
        # 規則說明頁按鈕
        self.rules_menu_buttons = [
            Button("返回", SCREEN_WIDTH // 2, SCREEN_HEIGHT - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, self._return_from_rules)
        ]

    def _return_from_rules(self):
        """從規則介面返回前一個狀態。"""
        if self.previous_state:
            self.change_state(self.previous_state)
        else:
            self.change_state(GameStates.MENU)

    def change_state(self, new_state, **kwargs):
        if self.state is not None:
            self._exit_state() 

        self.state = new_state
        kwargs.setdefault('reset', False) 
        kwargs.setdefault('return_state', GameStates.MENU) 

        self._enter_state(**kwargs) 

    def _enter_state(self, **kwargs):
        """進入新狀態時的行為。"""
        if self.state == GameStates.MENU:
            self.buttons = self.main_menu_buttons
            self.reset_game() 
        elif self.state == GameStates.PLAYING:
            self.buttons = [] 
            if kwargs['reset']: 
                self.reset_game()
        elif self.state == GameStates.PAUSED:
            self.buttons = self.pause_menu_buttons
        elif self.state == GameStates.GAME_OVER:
            self.buttons = self.game_over_menu_buttons
        elif self.state == GameStates.RULES:
            self.buttons = self.rules_menu_buttons
            self.previous_state = kwargs['return_state'] 

    def _exit_state(self):
        """離開當前狀態時的行為。"""
        self.buttons = [] 

    def reset_game(self):
        """重置遊戲狀態，清除蛇與食物。"""
        while self.snake_segments:
            segment = self.snake_segments.popleft() 
            self.all_sprites.remove(segment)
        
        if self.food_sprite:
            self.food_pool.release(self.food_sprite) 
            self.food_sprite = None

        # 初始化蛇的位置 (格點座標)
        initial_pos_grid = Vector2((SCREEN_WIDTH // 2 // GRID_SIZE) - 1, (SCREEN_HEIGHT // 2 // GRID_SIZE))
        self.snake_segments = collections.deque()
        for i in range(3): # 初始蛇長: 3
            segment = SnakeSegment(GRID_SIZE, SNAKE_COLOR)
            segment.pos = (initial_pos_grid - Vector2(i, 0)) * GRID_SIZE 
            segment.rect.topleft = (int(segment.pos.x), int(segment.pos.y))
            self.snake_segments.append(segment)
            self.all_sprites.add(segment)

        self.snake_direction = Vector2(1, 0) # 初始向右
        self.new_direction = Vector2(1, 0) 
        self.score = 0
        self.current_fps = INITIAL_FPS
        self.snake_move_timer = 0
        
        self.spawn_food() 

    def spawn_food(self):
        """在空白處生成食物。"""
        if self.food_sprite:
            self.food_pool.release(self.food_sprite) 
            self.food_sprite = None

        empty_positions = []
        for x in range(SCREEN_WIDTH // GRID_SIZE):
            for y in range(SCREEN_HEIGHT // GRID_SIZE):
                grid_pos = Vector2(x, y)
                is_occupied = False
                for segment in self.snake_segments:
                    if Vector2(segment.pos.x / GRID_SIZE, segment.pos.y / GRID_SIZE) == grid_pos:
                        is_occupied = True
                        break
                if not is_occupied:
                    empty_positions.append(grid_pos)
        
        if not empty_positions:
            # 如果沒有空間放食物，代表玩家獲勝（或填滿格點）
            print("無剩餘空間生成食物！")
            self.change_state(GameStates.GAME_OVER)
            return 

        food_grid_pos = random.choice(empty_positions)
        self.food_sprite = self.food_pool.get(food_grid_pos) 
        self.all_sprites.add(self.food_sprite) 

    def handle_input(self):
        """處理鍵盤與滑鼠事件。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.state == GameStates.PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        if self.snake_direction.y == 0: 
                            self.new_direction = Vector2(0, -1)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        if self.snake_direction.y == 0:
                            self.new_direction = Vector2(0, 1)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        if self.snake_direction.x == 0:
                            self.new_direction = Vector2(-1, 0)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        if self.snake_direction.x == 0:
                            self.new_direction = Vector2(1, 0)
                    elif event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                        self.change_state(GameStates.PAUSED)
            
            for button in self.buttons:
                if button.handle_event(event):
                    break 

            if self.state in [GameStates.PAUSED, GameStates.RULES] and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameStates.PAUSED:
                        self.change_state(GameStates.PLAYING)
                    elif self.state == GameStates.RULES:
                        self._return_from_rules()


    def update(self, dt):
        """更新遊戲邏輯（移動與碰撞）。"""
        if self.state == GameStates.PLAYING:
            self.snake_move_timer += dt
            # 根據 FPS 決定蛇的移動步長
            if self.snake_move_timer >= 1.0 / self.current_fps:
                self.snake_move_timer = 0
                self.snake_direction = self.new_direction 

                # 獲取蛇頭格點座標並計算新座標
                head_pos_grid = Vector2(self.snake_segments[0].pos.x / GRID_SIZE, self.snake_segments[0].pos.y / GRID_SIZE)
                new_head_grid = head_pos_grid + self.snake_direction
                
                new_head_segment = SnakeSegment(GRID_SIZE, SNAKE_COLOR)
                new_head_segment.pos = new_head_grid * GRID_SIZE 
                new_head_segment.rect.topleft = (int(new_head_segment.pos.x), int(new_head_segment.pos.y)) 

                # 將新蛇頭加入隊列與顯示群組
                self.snake_segments.appendleft(new_head_segment)
                self.all_sprites.add(new_head_segment) 

                # 碰撞檢測：
                # 1. 牆壁邊界
                if not (0 <= new_head_grid.x < SCREEN_WIDTH // GRID_SIZE and
                        0 <= new_head_grid.y < SCREEN_HEIGHT // GRID_SIZE):
                    self.change_state(GameStates.GAME_OVER)
                    return

                # 2. 蛇身碰撞 (不檢查剛加入的頭部，所以從 index 1 開始)
                for segment in list(self.snake_segments)[1:]: 
                    segment_grid_pos = Vector2(segment.pos.x / GRID_SIZE, segment.pos.y / GRID_SIZE)
                    if new_head_grid == segment_grid_pos:
                        self.change_state(GameStates.GAME_OVER)
                        return

                # 3. 吃到食物
                if self.food_sprite: 
                    food_grid_pos = Vector2(self.food_sprite.pos.x / GRID_SIZE, self.food_sprite.pos.y / GRID_SIZE)
                    if new_head_grid == food_grid_pos:
                        self.score += 10 
                        if self.score % FPS_INCREMENT_SCORE_THRESHOLD == 0 and self.current_fps < MAX_FPS:
                            self.current_fps += FPS_INCREMENT_VALUE
                        self.spawn_food() 
                    else:
                        # 沒吃到食物，移除蛇尾以保持長度
                        tail_segment = self.snake_segments.pop()
                        self.all_sprites.remove(tail_segment)

        # 更新所有精靈的狀態
        self.all_sprites.update(dt)

    def draw(self):
        """渲染畫面。"""
        self.screen.fill(BACKGROUND_COLOR)

        if self.state == GameStates.PLAYING:
            self.all_sprites.draw(self.screen) 

            # HUD 資訊
            score_text = self.font_hud.render(f"得分: {self.score}", True, TEXT_COLOR)
            self.screen.blit(score_text, (10, 10))
            speed_text = self.font_hud.render(f"速度: {self.current_fps}", True, TEXT_COLOR)
            self.screen.blit(speed_text, (SCREEN_WIDTH - speed_text.get_width() - 10, 10))

        elif self.state == GameStates.MENU:
            title_text = self.font_menu_title.render("經典貪食蛇遊戲", True, TEXT_COLOR)
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 3))
            self.screen.blit(title_text, title_rect)
            for button in self.buttons:
                button.draw(self.screen)

        elif self.state == GameStates.PAUSED:
            self.all_sprites.draw(self.screen)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128)) # 半透明黑色遮罩
            self.screen.blit(overlay, (0, 0))

            paused_text = self.font_menu_title.render("暫停中", True, TEXT_COLOR)
            paused_rect = paused_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 3))
            self.screen.blit(paused_text, paused_rect)
            for button in self.buttons:
                button.draw(self.screen)

        elif self.state == GameStates.GAME_OVER:
            game_over_text = self.font_menu_title.render("遊戲結束", True, TEXT_COLOR)
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 2))
            self.screen.blit(game_over_text, game_over_rect)

            final_score_text = self.font_menu_button.render(f"最終得分: {self.score}", True, TEXT_COLOR)
            final_score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT))
            self.screen.blit(final_score_text, final_score_rect)
            for button in self.buttons:
                button.draw(self.screen)

        elif self.state == GameStates.RULES:
            rules_title_text = self.font_menu_title.render("遊戲規則", True, TEXT_COLOR)
            rules_title_rect = rules_title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
            self.screen.blit(rules_title_text, rules_title_rect)

            rules_content = [
                "1. 控制蛇在 600x400 的空間中移動。",
                "2. 吃到紅色食物會增加長度與 10 分。",
                "3. 撞到牆壁或自己的身體則遊戲結束。",
                "4. 速度會隨著得分提高而逐漸加快。",
                "5. 按 'P' 或 'ESC' 可進入暫停選單。",
                "6. 使用方向鍵或 WASD 鍵進行移動。"
            ]
            y_offset = rules_title_rect.bottom + 20
            for rule in rules_content:
                rule_surface = self.font_hud.render(rule, True, TEXT_COLOR)
                rule_rect = rule_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                self.screen.blit(rule_surface, rule_rect)
                y_offset += rule_surface.get_height() + 5
            
            for button in self.buttons:
                button.draw(self.screen)

        pygame.display.flip() 

    def quit_game(self):
        self.running = False

    def run(self):
        """啟動遊戲主迴圈。"""
        if self.game_active:
            self.change_state(GameStates.PLAYING, reset=True) 
        else:
            pass 

        while self.running:
            # 限制更新頻率並計算 Delta Time
            dt = min(self.clock.tick(self.current_fps) / 1000.0, 0.05)
            
            self.handle_input()
            self.update(dt)
            self.draw()

        pygame.quit() 

if __name__ == '__main__':
    game = Game()
    game.game_active = False 
    game.run()