import pygame
import random
import collections
import enum
from pygame.math import Vector2

# --- RAG 模組開始 ---
# 參考模組: GameSprite
# 必須直接包含並使用。嚴禁修改模組核心邏輯，僅能繼承或呼叫。
class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image=None, rect=None, pos=None, velocity=None):
        super().__init__()
        # 確保 image 總是 Surface 物件
        self.image = image if image is not None else pygame.Surface((1, 1), pygame.SRCALPHA)
        # 確保 rect 總是 Rect 物件
        self.rect = rect if rect is not None else self.image.get_rect()
        # pos 必須是 Vector2 以支援浮點數座標 (關鍵指令要求)
        self.pos = pos if pos is not None else Vector2(self.rect.topleft)
        self.velocity = velocity if velocity is not None else Vector2(0, 0)
        # CRITICAL INSTRUCTION: GameSprite 核心模組不允許修改。
        # 子類別需確保在初始化後，rect 與 pos 保持同步。

    def update(self, dt):
        # 基礎更新方法，用於連續移動的精靈。
        # 對於格狀移動的貪食蛇，其移動將直接更新 pos/rect，故此方法可能不會被直接使用。
        pass

# 參考模組: ObjectPool
# 必須直接包含並使用。嚴禁修改模組核心邏輯，僅能繼承或呼叫。
class ObjectPool:
    def __init__(self, object_factory, initial_size=10):
        self._object_factory = object_factory
        self._pool = collections.deque()
        self._active_objects = set()
        for _ in range(initial_size):
            self._pool.append(self._object_factory()) # 預先填充物件池

    def get(self, *args, **kwargs):
        # 從物件池中取得一個物件。如果物件池為空，則創建一個新的。
        if not self._pool:
            obj = self._object_factory()
        else:
            obj = self._pool.popleft()

        # 如果物件有一個 'reset' 方法，則呼叫它以重新初始化其狀態
        if hasattr(obj, 'reset'):
            obj.reset(*args, **kwargs)
        
        self._active_objects.add(obj)
        return obj

    def release(self, obj):
        # 將物件釋放回物件池。
        if obj in self._active_objects:
            self._active_objects.remove(obj)
            self._pool.append(obj)
            # 將精靈從其目前所屬的所有精靈群組中移除。
            # 這對於物件池與精靈群組的整合至關重要。
            obj.kill() 
        # else: 物件不在活動集中 (例如，已釋放或不屬於此物件池)。
# --- RAG 模組結束 ---

# 遊戲狀態 (Game States)
class GameStates(enum.Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3
    RULES = 4

# 遊戲設定 (根據企劃書 JSON 與說明)
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
GRID_SIZE = 20 # 所有遊戲物件的基礎單位大小
INITIAL_FPS = 5 # 初始遊戲幀率，代表蛇的移動速度 (適度降低，增加遊戲友好性)
MAX_FPS = 20 # 蛇的最大速度 (調整為 20，避免過快難以操作)
FPS_INCREMENT_SCORE_THRESHOLD = 50 # 每當分數達到此閾值的倍數時，速度提升一次
FPS_INCREMENT_VALUE = 1 # 每次速度提升的 FPS 值

BACKGROUND_COLOR = (0, 0, 0) # 黑色
TEXT_COLOR = (255, 255, 255) # 白色
SNAKE_COLOR = (0, 255, 0) # 綠色
FOOD_COLOR = (255, 0, 0) # 紅色

# CRITICAL INSTRUCTION: 中文字體
FONT_NAME = "microsoftjhenghei" # 優先使用微軟正黑體
# 如果 'microsoftjhenghei' 不可用，嘗試 'simhei' 或其他系統通用字體
# 或者 fallback 到 pygame 預設字體
try:
    pygame.font.match_font(FONT_NAME)
except:
    FONT_NAME = "simhei"
    try:
        pygame.font.match_font(FONT_NAME)
    except:
        FONT_NAME = None # Fallback to default if no specific font is found


FONT_SIZE_HUD = 24 # HUD 字體大小
FONT_SIZE_MENU_TITLE = 48 # 選單標題字體大小
FONT_SIZE_MENU_BUTTON = 32 # 選單按鈕字體大小

BUTTON_BG_COLOR = (50, 50, 50) # 按鈕背景色 (深灰色)
BUTTON_HOVER_COLOR = (100, 100, 100) # 按鈕懸停色 (淺灰色)
BUTTON_TEXT_COLOR = (255, 255, 255) # 按鈕文字色
BUTTON_WIDTH = 200 # 按鈕寬度
BUTTON_HEIGHT = 50 # 按鈕高度
BUTTON_MARGIN = 10 # 按鈕間距

# 遊戲實體: 蛇身節點
class SnakeSegment(GameSprite):
    def __init__(self, grid_size=GRID_SIZE, color=SNAKE_COLOR):
        image = pygame.Surface((grid_size, grid_size))
        image.fill(color)
        rect = image.get_rect()
        # 初始設定為一個預設的螢幕外位置，實際位置會在蛇身中設定
        super().__init__(image=image, rect=rect, pos=Vector2(-grid_size, -grid_size), velocity=Vector2(0,0))
        # CRITICAL INSTRUCTION: 物理與數學 - 確保 rect 始終與 pos 同步
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))

# 遊戲實體: 食物
class Food(GameSprite):
    def __init__(self, grid_size=GRID_SIZE, color=FOOD_COLOR):
        image = pygame.Surface((grid_size, grid_size))
        image.fill(color)
        rect = image.get_rect()
        # 初始設定為一個預設的螢幕外位置，實際位置會在 reset 被呼叫時設定
        super().__init__(image=image, rect=rect, pos=Vector2(-grid_size, -grid_size), velocity=Vector2(0,0))
        # CRITICAL INSTRUCTION: 物理與數學 - 確保 rect 始終與 pos 同步
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        self._grid_size = grid_size
        self._color = color

    def reset(self, grid_pos):
        # 重新初始化食物的狀態，以便從物件池中重複使用。
        # grid_pos 是一個 (col, row) 的網格座標。
        # CRITICAL INSTRUCTION: 物理與數學 - 浮點數座標 (透過 pos 維護，rect 同步)
        self.pos = Vector2(grid_pos[0] * self._grid_size, grid_pos[1] * self._grid_size)
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))
        # 在此遊戲中無需改變圖像或顏色，但可以在這裡添加相關邏輯。

# UI 元素: 按鈕
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

# 遊戲主類別
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("經典貪食蛇")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        # CRITICAL INSTRUCTION: 不隱藏滑鼠游標
        pygame.mouse.set_visible(True) 

        # CRITICAL INSTRUCTION: 中文字體處理
        self.font_hud = pygame.font.Font(pygame.font.match_font(FONT_NAME), FONT_SIZE_HUD)
        self.font_menu_title = pygame.font.Font(pygame.font.match_font(FONT_NAME), FONT_SIZE_MENU_TITLE)
        self.font_menu_button = pygame.font.Font(pygame.font.match_font(FONT_NAME), FONT_SIZE_MENU_BUTTON)

        self.clock = pygame.time.Clock()
        self.running = True

        # 遊戲狀態管理
        self.state = GameStates.MENU
        self.previous_state = None # 用於從「遊戲規則」頁面正確返回

        # CRITICAL INSTRUCTION: 自動化測試接口
        self.game_active = False # 預設為 False 以顯示選單

        # 遊戲實體數據
        self.snake_segments = collections.deque() # 儲存 SnakeSegment 物件
        self.snake_direction = Vector2(0, 0)
        self.new_direction = Vector2(0, 0) # 用於防止蛇立即反向移動
        self.score = 0
        self.current_fps = INITIAL_FPS # 遊戲當前幀率，控制蛇的速度
        self.snake_move_timer = 0 # 計時器，控制蛇每次移動的時間間隔

        # CRITICAL INSTRUCTION: 物件池分離 (food_pool) 與 SpriteGroup (all_sprites)
        self.food_pool = ObjectPool(lambda: Food(GRID_SIZE, FOOD_COLOR), initial_size=5)
        self.all_sprites = pygame.sprite.Group() # 用於渲染所有活動中的精靈 (蛇和食物)
        self.food_sprite = None # 當前活動的食物精靈

        # 選單元素
        self.buttons = []
        self._setup_menus() # 初始化所有選單的按鈕定義

        # 設定初始遊戲狀態為 MENU，並在 _enter_state 中執行 reset_game
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
            Button("回主選單", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT + BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.MENU)),
            Button("結束遊戲", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT * 2 + BUTTON_MARGIN * 2, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, self.quit_game)
        ]

        # 遊戲結束選單按鈕
        self.game_over_menu_buttons = [
            Button("重新開始", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT + BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.PLAYING, reset=True)),
            Button("回主選單", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT * 2 + BUTTON_MARGIN * 2, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, lambda: self.change_state(GameStates.MENU)),
            Button("結束遊戲", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + BUTTON_HEIGHT * 3 + BUTTON_MARGIN * 3, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, self.quit_game)
        ]
        
        # 遊戲規則頁面按鈕
        self.rules_menu_buttons = [
            Button("返回", SCREEN_WIDTH // 2, SCREEN_HEIGHT - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, self.font_menu_button, self._return_from_rules)
        ]

    def _return_from_rules(self):
        """從遊戲規則頁面返回到上一個狀態。"""
        if self.previous_state:
            self.change_state(self.previous_state)
        else: # 如果沒有記錄上一個狀態，預設返回主選單
            self.change_state(GameStates.MENU)

    # CRITICAL INSTRUCTION: 狀態機安全 - change_state 呼叫 enter 時，必須使用 kwargs.setdefault()
    def change_state(self, new_state, **kwargs):
        if self.state is not None:
            self._exit_state() # 離開當前狀態

        self.state = new_state
        # CRITICAL INSTRUCTION: 使用 kwargs.setdefault() 避免參數衝突
        kwargs.setdefault('reset', False) # 預設不重置遊戲
        kwargs.setdefault('return_state', GameStates.MENU) # 遊戲規則頁面的預設返回狀態

        self._enter_state(**kwargs) # 進入新狀態

    def _enter_state(self, **kwargs):
        """進入特定狀態時的初始化邏輯。"""
        if self.state == GameStates.MENU:
            self.buttons = self.main_menu_buttons
            self.reset_game() # 進入主選單時總是重置遊戲數據
        elif self.state == GameStates.PLAYING:
            self.buttons = [] # 遊戲進行中不顯示按鈕
            if kwargs['reset']: # 如果需要重置遊戲
                self.reset_game()
        elif self.state == GameStates.PAUSED:
            self.buttons = self.pause_menu_buttons
        elif self.state == GameStates.GAME_OVER:
            self.buttons = self.game_over_menu_buttons
        elif self.state == GameStates.RULES:
            self.buttons = self.rules_menu_buttons
            self.previous_state = kwargs['return_state'] # 記錄從哪個狀態進入規則頁面

    def _exit_state(self):
        """離開特定狀態時的清理邏輯。"""
        # 目前這些狀態不需要特別的退出清理，主要是清除按鈕列表。
        self.buttons = [] # 離開任何選單狀態時清除按鈕列表

    # CRITICAL INSTRUCTION: 初始鏡頭 (本遊戲不適用相機，但 reset_game 會重設遊戲狀態)
    def reset_game(self):
        """重置所有遊戲數據至初始狀態。"""
        # 清除所有現有的精靈和蛇身節點
        while self.snake_segments:
            # 蛇身節點在此遊戲中不回收到物件池，而是讓 GC 處理，但必須從渲染群組中移除
            segment = self.snake_segments.popleft() 
            self.all_sprites.remove(segment)
        
        if self.food_sprite:
            self.food_pool.release(self.food_sprite) # 釋放舊的食物回物件池
            self.food_sprite = None

        # 初始化蛇
        initial_pos_grid = Vector2((SCREEN_WIDTH // 2 // GRID_SIZE) - 1, (SCREEN_HEIGHT // 2 // GRID_SIZE))
        self.snake_segments = collections.deque()
        for i in range(3): # 初始長度: 3
            segment = SnakeSegment(GRID_SIZE, SNAKE_COLOR)
            # CRITICAL INSTRUCTION: 物理與數學 - 浮點數座標 (pos 維護，rect 同步)
            segment.pos = (initial_pos_grid - Vector2(i, 0)) * GRID_SIZE # 初始方向向右
            segment.rect.topleft = (int(segment.pos.x), int(segment.pos.y))
            self.snake_segments.append(segment)
            self.all_sprites.add(segment)

        self.snake_direction = Vector2(1, 0) # 初始方向: 向右
        self.new_direction = Vector2(1, 0) # 預設新方向也向右
        self.score = 0
        self.current_fps = INITIAL_FPS
        self.snake_move_timer = 0
        
        self.spawn_food() # 生成第一個食物

    def spawn_food(self):
        """在隨機空閒位置生成食物。"""
        if self.food_sprite:
            self.food_pool.release(self.food_sprite) # 如果有舊食物，先釋放回池中
            self.food_sprite = None

        # 尋找所有空閒的網格位置
        empty_positions = []
        for x in range(SCREEN_WIDTH // GRID_SIZE):
            for y in range(SCREEN_HEIGHT // GRID_SIZE):
                grid_pos = Vector2(x, y)
                is_occupied = False
                for segment in self.snake_segments:
                    # 檢查該網格點是否被蛇身佔據
                    # CRITICAL INSTRUCTION: 物理與數學 - 從 pos 獲取網格座標
                    if Vector2(segment.pos.x / GRID_SIZE, segment.pos.y / GRID_SIZE) == grid_pos:
                        is_occupied = True
                        break
                if not is_occupied:
                    empty_positions.append(grid_pos)
        
        if not empty_positions:
            # 如果沒有空閒位置，表示整個地圖都被蛇填滿了，這是一種勝利狀態 (或極端情況下遊戲結束)
            # 在經典貪食蛇中，這通常不會發生在遊戲結束前，但作為安全措施。
            print("沒有空閒位置可以生成食物！")
            self.change_state(GameStates.GAME_OVER) # 暫時視為遊戲結束
            return 

        food_grid_pos = random.choice(empty_positions)
        # CRITICAL INSTRUCTION: 物件池安全 - 從物件池獲取食物，並將其添加到渲染群組
        self.food_sprite = self.food_pool.get(food_grid_pos) # 從物件池獲取食物
        self.all_sprites.add(self.food_sprite) # 將食物添加到渲染群組

    def handle_input(self):
        """處理 Pygame 事件 (鍵盤、滑鼠)。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.state == GameStates.PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        if self.snake_direction.y == 0: # 防止立即反向移動
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
            
            # 在任何選單狀態下處理按鈕點擊
            for button in self.buttons:
                if button.handle_event(event):
                    break # 每次只處理一個按鈕點擊

            # 在暫停或規則頁面按下 ESC 可返回
            if self.state in [GameStates.PAUSED, GameStates.RULES] and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameStates.PAUSED:
                        self.change_state(GameStates.PLAYING)
                    elif self.state == GameStates.RULES:
                        self._return_from_rules()


    def update(self, dt):
        """根據遊戲狀態更新遊戲邏輯。"""
        if self.state == GameStates.PLAYING:
            self.snake_move_timer += dt
            # 根據當前 FPS (速度) 來判斷蛇是否該移動
            if self.snake_move_timer >= 1.0 / self.current_fps:
                self.snake_move_timer = 0
                self.snake_direction = self.new_direction # 應用新的移動方向

                # CRITICAL INSTRUCTION: 物理與數學 - 浮點數座標 (透過 pos 向量運算)
                # 獲取當前蛇頭的網格座標
                head_pos_grid = Vector2(self.snake_segments[0].pos.x / GRID_SIZE, self.snake_segments[0].pos.y / GRID_SIZE)
                # 計算新蛇頭的網格座標
                new_head_grid = head_pos_grid + self.snake_direction
                
                # 創建一個新的蛇頭節點
                new_head_segment = SnakeSegment(GRID_SIZE, SNAKE_COLOR)
                new_head_segment.pos = new_head_grid * GRID_SIZE # 更新浮點數位置
                new_head_segment.rect.topleft = (int(new_head_segment.pos.x), int(new_head_segment.pos.y)) # 同步到 rect

                # 將新蛇頭加入蛇身前端
                self.snake_segments.appendleft(new_head_segment)
                self.all_sprites.add(new_head_segment) # 將新蛇頭加入渲染群組

                # 碰撞檢測 (CRITICAL INSTRUCTION: 分離軸運動 - 對於格狀移動隱含處理)
                # 1. 邊界碰撞
                if not (0 <= new_head_grid.x < SCREEN_WIDTH // GRID_SIZE and
                        0 <= new_head_grid.y < SCREEN_HEIGHT // GRID_SIZE):
                    self.change_state(GameStates.GAME_OVER)
                    return

                # 2. 自身碰撞 (檢查新蛇頭是否與蛇身的其他部分重疊)
                # 遍歷除了新蛇頭本身以外的所有蛇身節點
                # 在 deque 中，index 0 是新頭部，因此從 index 1 開始檢查
                for segment in list(self.snake_segments)[1:]: 
                    segment_grid_pos = Vector2(segment.pos.x / GRID_SIZE, segment.pos.y / GRID_SIZE)
                    if new_head_grid == segment_grid_pos:
                        self.change_state(GameStates.GAME_OVER)
                        return

                # 3. 食物碰撞
                # CRITICAL INSTRUCTION: NoneType Crash - 存取物件屬性前必先檢查
                if self.food_sprite: # 確保有食物存在
                    food_grid_pos = Vector2(self.food_sprite.pos.x / GRID_SIZE, self.food_sprite.pos.y / GRID_SIZE)
                    if new_head_grid == food_grid_pos:
                        self.score += 10 # 增加分數
                        # 如果分數達到閾值且未達最大速度，則提升速度
                        if self.score % FPS_INCREMENT_SCORE_THRESHOLD == 0 and self.current_fps < MAX_FPS:
                            self.current_fps += FPS_INCREMENT_VALUE
                        self.spawn_food() # 生成新食物
                    else:
                        # 如果沒有吃到食物，移除蛇尾
                        tail_segment = self.snake_segments.pop()
                        self.all_sprites.remove(tail_segment) # 從渲染群組中移除蛇尾，確保其不再被繪製或更新

        # 更新所有精靈 (雖然蛇身節點不直接使用此方法，但對於其他遊戲的連續移動精靈有用)
        self.all_sprites.update(dt)

    def draw(self):
        """繪製所有遊戲元素和 UI。"""
        self.screen.fill(BACKGROUND_COLOR)

        if self.state == GameStates.PLAYING:
            self.all_sprites.draw(self.screen) # 繪製所有活動中的精靈

            # 繪製 HUD (分數與速度)
            score_text = self.font_hud.render(f"分數: {self.score}", True, TEXT_COLOR)
            self.screen.blit(score_text, (10, 10))
            speed_text = self.font_hud.render(f"速度: {self.current_fps}", True, TEXT_COLOR)
            self.screen.blit(speed_text, (SCREEN_WIDTH - speed_text.get_width() - 10, 10))

        elif self.state == GameStates.MENU:
            title_text = self.font_menu_title.render("經典貪食蛇", True, TEXT_COLOR)
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 3))
            self.screen.blit(title_text, title_rect)
            for button in self.buttons:
                button.draw(self.screen)

        elif self.state == GameStates.PAUSED:
            # 在半透明疊層下繪製遊戲畫面
            self.all_sprites.draw(self.screen)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128)) # 半透明黑色
            self.screen.blit(overlay, (0, 0))

            paused_text = self.font_menu_title.render("遊戲暫停", True, TEXT_COLOR)
            paused_rect = paused_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 3))
            self.screen.blit(paused_text, paused_rect)
            for button in self.buttons:
                button.draw(self.screen)

        elif self.state == GameStates.GAME_OVER:
            game_over_text = self.font_menu_title.render("遊戲結束", True, TEXT_COLOR)
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT * 2))
            self.screen.blit(game_over_text, game_over_rect)

            final_score_text = self.font_menu_button.render(f"最終分數: {self.score}", True, TEXT_COLOR)
            final_score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - BUTTON_HEIGHT))
            self.screen.blit(final_score_text, final_score_rect)
            for button in self.buttons:
                button.draw(self.screen)

        elif self.state == GameStates.RULES:
            rules_title_text = self.font_menu_title.render("遊戲規則", True, TEXT_COLOR)
            rules_title_rect = rules_title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
            self.screen.blit(rules_title_text, rules_title_rect)

            rules_content = [
                "玩家操控一條蛇，在600x400的視窗中移動。",
                "蛇吃到紅色方塊（食物）後，長度增加一節，分數加10分。",
                "蛇的頭部撞到遊戲邊界或撞到自己的身體時，遊戲結束。",
                "遊戲目標是盡可能獲得高分。",
                "分數每達到50分，蛇的移動速度會稍微提升。",
                "按 'P' 或 'ESC' 鍵可暫停遊戲。",
                "使用方向鍵或 WASD 控制方向。"
            ]
            y_offset = rules_title_rect.bottom + 20
            for rule in rules_content:
                rule_surface = self.font_hud.render(rule, True, TEXT_COLOR)
                rule_rect = rule_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                self.screen.blit(rule_surface, rule_rect)
                y_offset += rule_surface.get_height() + 5
            
            for button in self.buttons:
                button.draw(self.screen)

        pygame.display.flip() # 更新整個螢幕

    def quit_game(self):
        """設定旗標以退出遊戲主迴圈。"""
        self.running = False

    def run(self):
        """遊戲主迴圈。"""
        # CRITICAL INSTRUCTION: 自動化測試接口 (在主迴圈開始前檢查 game_active)
        if self.game_active:
            self.change_state(GameStates.PLAYING, reset=True) # 強制直接開始遊戲
        else:
            # 已經在 __init__ 中呼叫 change_state(GameStates.MENU)，因此這裡不需要重複呼叫
            pass 

        while self.running:
            # CRITICAL INSTRUCTION: Delta Time 限制 (防止穿牆)
            # 限制 dt 最大值為 0.05 秒，防止拖動視窗或卡頓時物體瞬移。
            # 對於格狀移動的貪食蛇，此限制主要用於穩定FPS計算，而非防止連續運動的穿牆。
            dt = min(self.clock.tick(self.current_fps) / 1000.0, 0.05)
            
            self.handle_input()
            self.update(dt)
            self.draw()

        pygame.quit() # 退出 Pygame 模組

if __name__ == '__main__':
    game = Game()
    # CRITICAL INSTRUCTION: if __name__ == '__main__': 必須顯式設定 game.game_active = False 以顯示選單。
    game.game_active = False 
    game.run()