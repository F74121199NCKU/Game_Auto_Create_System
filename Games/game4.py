import pygame
import random
import math
from collections import deque
import json # Not directly used for parsing in final code, but for reference.

# --- RAG Modules (CRITICAL INSTRUCTION: DO NOT MODIFY CORE LOGIC) ---
# --- object_pool.py ---
class ObjectPool:
    """
    An object pool for managing reusable objects.
    Reduces the overhead of creating and destroying objects frequently.
    """
    def __init__(self, obj_class, initial_size=10):
        self.obj_class = obj_class
        self._pool = deque()
        self._active = [] # Keep track of active objects if needed for iteration
        self._initial_size = initial_size
        self._create_initial_objects()

    def _create_initial_objects(self):
        for _ in range(self._initial_size):
            self._pool.append(self.obj_class())

    def get(self):
        """
        Retrieves an object from the pool. If the pool is empty, a new object is created.
        """
        if not self._pool:
            # print(f"Pool for {self.obj_class.__name__} exhausted, creating new object.")
            obj = self.obj_class()
        else:
            obj = self._pool.popleft()
        self._active.append(obj)
        return obj

    def release(self, obj):
        """
        Releases an object back into the pool.
        """
        if obj in self._active:
            self._active.remove(obj)
        # Reset object state before releasing it
        if hasattr(obj, 'reset'):
            obj.reset()
        self._pool.append(obj)

    def get_active(self):
        """
        Returns a list of currently active objects.
        """
        return list(self._active)

    def size(self):
        """
        Returns the current number of objects in the pool.
        """
        return len(self._pool)

    def active_count(self):
        """
        Returns the number of currently active objects.
        """
        return len(self._active)

# --- sprite_manager.py ---
class GameSprite(pygame.sprite.Sprite):
    """
    A base class for all game sprites, providing basic position management
    and a placeholder for update/draw logic.
    """
    def __init__(self, image=None, position=(0, 0)):
        super().__init__()
        self.image = image if image else pygame.Surface((32, 32), pygame.SRCALPHA)
        if not image:
            self.image.fill((255, 0, 255, 128)) # Default magenta for debugging
        self.rect = self.image.get_rect(center=position)
        self.pos = pygame.math.Vector2(position) # CRITICAL: Floating point position

    def update(self, dt):
        """
        Placeholder for sprite-specific update logic.
        dt is the time elapsed since the last frame in seconds.
        """
        # CRITICAL: Update rect from float position
        self.rect.center = round(self.pos.x), round(self.pos.y)
        pass

    def draw(self, surface):
        """
        Placeholder for sprite-specific draw logic.
        """
        surface.blit(self.image, self.rect)

    def reset(self):
        """
        Resets the sprite's state for reuse from an object pool.
        To be overridden by subclasses.
        """
        self.kill() # Remove from all groups
        self.pos = pygame.math.Vector2(0, 0) # Reset position
        self.rect.center = (0, 0)
        # Additional state reset logic for subclasses

# --- mouse_camera.py ---
class MouseCameraGroup(pygame.sprite.Group):
    """
    A sprite group that implements camera movement based on mouse position
    near screen edges, and Y-sorting for drawing.
    """
    def __init__(self, map_width, map_height, screen_width, screen_height, camera_speed=500):
        super().__init__()
        self.map_width = map_width
        self.map_height = map_height
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.camera_speed = camera_speed  # Pixels per second

        self.offset = pygame.math.Vector2(0, 0)  # Current camera offset (top-left of screen view on map)
        self.camera_center_on_map = pygame.math.Vector2(map_width / 2, map_height / 2)
        self.set_camera_offset_to_center_map()

        # Define edge scrolling area (e.g., 50 pixels from edge)
        self.edge_margin = 50

    def set_camera_offset_to_center_map(self):
        """Centers the camera on the map."""
        self.offset.x = max(0, min(self.map_width - self.screen_width, self.map_width / 2 - self.screen_width / 2))
        self.offset.y = max(0, min(self.map_height - self.screen_height, self.map_height / 2 - self.screen_height / 2))
        self.camera_center_on_map.x = self.offset.x + self.screen_width / 2
        self.camera_center_on_map.y = self.offset.y + self.screen_height / 2

    def center_camera(self, target_pos):
        """
        Centers the camera on a specific map position.
        target_pos: pygame.math.Vector2 representing the map coordinates.
        """
        # Calculate new offset so target_pos is at the screen center
        new_offset_x = target_pos.x - self.screen_width / 2
        new_offset_y = target_pos.y - self.screen_height / 2

        # Clamp the offset to map boundaries
        self.offset.x = max(0, min(self.map_width - self.screen_width, new_offset_x))
        self.offset.y = max(0, min(self.map_height - self.screen_height, new_offset_y))
        self.camera_center_on_map.x = self.offset.x + self.screen_width / 2
        self.camera_center_on_map.y = self.offset.y + self.screen_height / 2

    def mouse_control(self, mouse_pos, dt):
        """
        Updates camera offset based on mouse position near screen edges.
        """
        camera_move = pygame.math.Vector2(0, 0)

        # Horizontal movement
        if mouse_pos[0] < self.edge_margin:
            camera_move.x = -1
        elif mouse_pos[0] > self.screen_width - self.edge_margin:
            camera_move.x = 1

        # Vertical movement
        if mouse_pos[1] < self.edge_margin:
            camera_move.y = -1
        elif mouse_pos[1] > self.screen_height - self.edge_margin:
            camera_move.y = 1

        # Apply movement, scaled by dt and speed
        if camera_move.length() > 0:
            camera_move.normalize_ip()
            new_offset_x = self.offset.x + camera_move.x * self.camera_speed * dt
            new_offset_y = self.offset.y + camera_move.y * self.camera_speed * dt

            # Clamp offset to map boundaries
            self.offset.x = max(0, min(self.map_width - self.screen_width, new_offset_x))
            self.offset.y = max(0, min(self.map_height - self.screen_height, new_offset_y))
            self.camera_center_on_map.x = self.offset.x + self.screen_width / 2
            self.camera_center_on_map.y = self.offset.y + self.screen_height / 2

    def get_map_coords(self, screen_coords):
        """
        Converts screen coordinates to map coordinates.
        """
        return pygame.math.Vector2(screen_coords[0] + self.offset.x, screen_coords[1] + self.offset.y)

    def get_screen_coords(self, map_coords):
        """
        Converts map coordinates to screen coordinates.
        """
        return pygame.math.Vector2(map_coords.x - self.offset.x, map_coords.y - self.offset.y)

    def custom_draw(self, surface, background_surface=None):
        """
        Draws sprites with Y-sorting and camera offset.
        Optionally draws a background surface.
        CRITICAL: Frustum Culling Margin - 100px.
        The `pygame.sprite.Group` blits its sprites. Pygame's `blit` itself handles
        clipping, meaning only parts of the image that are on the surface are drawn.
        To explicitly "retain at least 100px buffer", we would typically inflate the
        visible rect for game logic or modify the blit loop. However, the instruction
        "嚴禁修改 模組核心邏輯" (strictly forbidden to modify module core logic) prevents
        altering the internal sprite iteration/blit condition.
        Thus, the interpretation is that the `update` method is called for all sprites,
        and `custom_draw` will blit them. Any sprites whose rects are within the screen
        plus Pygame's internal clipping buffer will be rendered. For logic (e.g., enemy AI),
        all active sprites (within the group) are updated regardless of immediate screen visibility,
        effectively creating a larger active zone than just the screen.
        """
        # If a background surface is provided, blit the visible portion
        if background_surface:
            # Create a rect representing the visible portion of the background on the map
            source_rect = pygame.Rect(self.offset.x, self.offset.y, self.screen_width, self.screen_height)
            surface.blit(background_surface, (0, 0), source_rect)
        else:
            surface.fill((0, 0, 0)) # Default fill if no background

        # Sort sprites by their bottom for pseudo-3D effect
        sprites_to_draw = sorted(self.sprites(), key=lambda sprite: sprite.rect.bottom)

        for sprite in sprites_to_draw:
            # Apply camera offset to sprite's rect for drawing
            adjusted_rect = sprite.rect.move(-self.offset.x, -self.offset.y)
            # Pygame's blit handles actual clipping, so we don't need manual frustum culling here
            surface.blit(sprite.image, adjusted_rect)

    def update(self, dt):
        """
        Updates all sprites in the group.
        """
        for sprite in self.sprites():
            sprite.update(dt)

# --- collision.py ---
class CollisionManager:
    """
    Manages collision detection and resolution between groups of sprites.
    Supports sprite-vs-group and group-vs-group collision.
    """
    def __init__(self):
        pass # No complex spatial partitioning for now, as it's outside the module scope
             # but mentioned as a future optimization in the plan.
             # The existing pygame.sprite.groupcollide and spritecollide are efficient enough
             # for most cases for this scale.

    def apply_sprite_vs_group(self, sprite, group, callback=None, dokill=False):
        """
        Detects collisions between a single sprite and a group of sprites.
        Args:
            sprite (pygame.sprite.Sprite): The single sprite.
            group (pygame.sprite.Group): The group to check against.
            callback (function, optional): A function to call for each collision,
                                          takes (sprite, collided_sprite).
            dokill (bool): If True, removes collided sprites from their groups.
                           Can be an integer (1 or 2) to control which sprite is killed.
                           1: kill sprite; 2: kill collided_sprite; 0 or False: kill none.
        Returns:
            list: A list of sprites from the group that collided with the single sprite.
        """
        # pygame.sprite.spritecollide returns a list of sprites from the group that intersected sprite
        collided_sprites = pygame.sprite.spritecollide(sprite, group, dokill)

        if callback:
            for collided in collided_sprites:
                callback(sprite, collided)
        return collided_sprites

    def apply_group_vs_group(self, group1, group2, callback=None, dokill=False):
        """
        Detects collisions between two groups of sprites.
        Args:
            group1 (pygame.sprite.Group): The first group.
            group2 (pygame.sprite.Group): The second group.
            callback (function, optional): A function to call for each collision,
                                          takes (sprite1, sprite2).
            dokill (bool): If True, removes collided sprites from their groups.
                           Can be an integer (1 or 2) to control which group is killed.
                           1: kill sprites from group1; 2: kill sprites from group2;
                           0 or False: kill none.
        Returns:
            dict: A dictionary mapping sprites from group1 to lists of sprites from group2
                  that they collided with.
        """
        # pygame.sprite.groupcollide returns a dict where keys are sprites from group1
        # that collided, and values are lists of sprites from group2 that they collided with.
        collided = pygame.sprite.groupcollide(
            group1, group2, 
            (dokill == 1 or dokill is True), # dokill1 (for group1)
            (dokill == 2 or dokill is True)  # dokill2 (for group2)
        )

        if callback:
            for sprite1, collided_list in collided.items():
                for sprite2 in collided_list:
                    callback(sprite1, sprite2)
        return collided

# --- End RAG Modules ---

# --- Game Constants ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
MAP_WIDTH = 2000
MAP_HEIGHT = 2000
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (150, 150, 150)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
TRANSPARENT_BLACK = (0, 0, 0, 128) # For pause menu overlay

# Game specific constants from JSON
INITIAL_GOLD = 100
GOLD_PER_KILL = 15
WIN_KILL_COUNT = 50

# Entity specific constants
CC_MAX_HP = 500
CC_SIZE = 64
CC_INITIAL_POS = pygame.math.Vector2(MAP_WIDTH / 2, MAP_HEIGHT / 2)

TOWER_MAX_HP = 150
TOWER_BUILD_COST = 50
TOWER_ATTACK_DAMAGE = 25
TOWER_ATTACK_SPEED = 1.0 # seconds
TOWER_ATTACK_RANGE = 200 # pixels
TOWER_SIZE = 48

ENEMY_MAX_HP = 50
ENEMY_MOVE_SPEED = 50 # pixels/second
ENEMY_ATTACK_DAMAGE_TO_BUILDING = 50
ENEMY_ATTACK_FREQUENCY = 1.0 # seconds
ENEMY_SIZE = 32

BULLET_DAMAGE = 25
BULLET_MOVE_SPEED = 300 # pixels/second
BULLET_SIZE = 8

# UI/Font settings
FONT_NAME = pygame.font.match_font('microsoftjhenghei', 'simhei') # CRITICAL: Chinese font
FONT_XL = 60
FONT_L = 48
FONT_M = 32
FONT_S = 24
FONT_XS = 18

# --- Event Bus ---
class EventBus:
    """A simple event bus for decoupling components."""
    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_type, listener):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type, listener):
        if event_type in self._listeners:
            self._listeners[event_type].remove(listener)

    def publish(self, event_type, **kwargs):
        if event_type in self._listeners:
            for listener in self._listeners[event_type]:
                listener(**kwargs)

# Define event types
EVENT_GOLD_CHANGED = "GOLD_CHANGED"
EVENT_KILL_COUNT_CHANGED = "KILL_COUNT_CHANGED"
EVENT_CC_HP_CHANGED = "CC_HP_CHANGED"
EVENT_GAME_MESSAGE = "GAME_MESSAGE" # For in-game notifications

# --- Game States ---
class BaseState:
    """Base class for all game states."""
    def __init__(self, game, state_manager):
        self.game = game
        self.state_manager = state_manager

    def enter(self, **kwargs):
        """Called when entering the state."""
        pass

    def exit(self):
        """Called when exiting the state."""
        pass

    def handle_input(self, event):
        """Handles user input for the state."""
        pass

    def update(self, dt):
        """Updates the state's logic."""
        pass

    def draw(self, screen):
        """Draws the state's elements to the screen."""
        pass

class GameStateManager:
    def __init__(self, game):
        self.game = game
        self.states = {}
        self.current_state = None
        self.state_stack = [] # For pause/rules where we return to previous state

    def add_state(self, name, state_instance):
        self.states[name] = state_instance

    def change_state(self, state_name, **kwargs):
        if self.current_state:
            self.current_state.exit()

        if state_name not in self.states:
            raise ValueError(f"State '{state_name}' not found.")

        self.current_state = self.states[state_name]
        # CRITICAL: Use setdefault to prevent parameter conflict - this is handled by the state's enter method itself
        self.current_state.enter(**kwargs)
        self.state_stack.clear() # Clear stack on main state change
        self.state_stack.append(self.current_state)

    def push_state(self, state_name, **kwargs):
        if self.current_state:
            # Current state remains active underneath the new state, but paused
            # We don't call exit on it, but its update/draw won't be called directly by main loop.
            # Its draw will be called by GameStateManager.draw.
            self.state_stack.append(self.states[state_name])
            self.current_state = self.states[state_name]
            self.current_state.enter(**kwargs)

    def pop_state(self, **kwargs):
        if len(self.state_stack) > 1:
            self.current_state.exit()
            self.state_stack.pop()
            self.current_state = self.state_stack[-1]
            # When returning to a previous state from stack, re-enter it (e.g., to unpause)
            # Use setdefault to prevent parameter conflict within the state's enter method
            self.current_state.enter(**kwargs) 
        elif len(self.state_stack) == 1:
            print("Cannot pop the last state (main menu should be base).")

    def handle_input(self, event):
        if self.current_state:
            self.current_state.handle_input(event)

    def update(self, dt):
        if self.current_state:
            self.current_state.update(dt)

    def draw(self, screen):
        # Draw all states in the stack from bottom up, so overlays appear correctly
        for state in self.state_stack:
            state.draw(screen)

class Button:
    def __init__(self, rect, text, font, on_click, color=GRAY, hover_color=LIGHT_GRAY, text_color=BLACK):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.on_click = on_click
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False

    def handle_input(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.on_click()

    def draw(self, surface):
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, current_color, self.rect, border_radius=5)
        pygame.draw.rect(surface, BLACK, self.rect, 2, border_radius=5) # Border

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

class MainMenuState(BaseState):
    def __init__(self, game, state_manager):
        super().__init__(game, state_manager)
        self.font_title = pygame.font.Font(FONT_NAME, FONT_XL)
        self.font_button = pygame.font.Font(FONT_NAME, FONT_L)

        self.buttons = []
        self._setup_buttons()

    def _setup_buttons(self):
        button_width = 300
        button_height = 70
        button_spacing = 20
        start_y = SCREEN_HEIGHT / 2 - (button_height * 1.5 + button_spacing) # Adjust for title

        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y, button_width, button_height), # Fix: Added width and height
            "開始遊戲", self.font_button, self.game.start_game
        ))
        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y + button_height + button_spacing, button_width, button_height), # Fix: Added width and height
            "遊戲規則", self.font_button, lambda: self.state_manager.push_state("RULES_SCREEN")
        ))
        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y + (button_height + button_spacing) * 2, button_width, button_height), # Fix: Added width and height
            "結束遊戲", self.font_button, self.game.quit_game
        ))

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_input(event)

    def draw(self, screen):
        screen.fill(DARK_GRAY) # Simple background for menu

        title_surface = self.font_title.render("末日要塞：RTS塔防", True, YELLOW)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4))
        screen.blit(title_surface, title_rect)

        for button in self.buttons:
            button.draw(screen)

class RulesState(BaseState):
    def __init__(self, game, state_manager):
        super().__init__(game, state_manager)
        self.font_title = pygame.font.Font(FONT_NAME, FONT_L)
        self.font_text = pygame.font.Font(FONT_NAME, FONT_S)
        self.font_button = pygame.font.Font(FONT_NAME, FONT_M)

        self.rules_text = [
            "玩家需在 4000x4000 地圖中央防禦指揮中心。",
            "透過滑鼠游標移動到視窗邊緣進行相機捲動，探索地圖。",
            "初始金幣 100，每擊殺一個敵人獲得 15 金幣。",
            "使用滑鼠左鍵點擊地圖建造防禦塔，每個防禦塔消耗 50 金幣。",
            "金幣不足或該位置已被佔用則無法建造。",
            "敵人從地圖邊緣生成，移動至最近的建築物，並優先攻擊指揮中心。",
            "防禦塔會自動射擊攻擊範圍內最近的敵人。",
            "敵人接觸建築物後，每秒對其造成 50 點傷害。",
            "防禦塔生命值為 150 點，指揮中心生命值為 500 點。",
            "指揮中心血量歸零時，遊戲失敗。",
            "累積擊殺 50 個敵人時，遊戲勝利。",
            "遊戲結束時，顯示結局文字，提供「重新開始」與「返回主選單」選項。",
            "按下 'P' 或 'ESC' 鍵可暫停遊戲。"
        ]
        
        # Define button dimensions for the back button
        back_button_width = 200
        back_button_height = 50
        self.back_button = Button(
            (SCREEN_WIDTH / 2 - back_button_width / 2, SCREEN_HEIGHT - 100, back_button_width, back_button_height), # Fix: Added width and height
            "返回", self.font_button, lambda: self.state_manager.pop_state()
        )

    def handle_input(self, event):
        self.back_button.handle_input(event)

    def draw(self, screen):
        # Draw transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(TRANSPARENT_BLACK)
        screen.blit(overlay, (0,0))

        title_surface = self.font_title.render("遊戲規則", True, WHITE)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH / 2, 80))
        screen.blit(title_surface, title_rect)

        y_offset = title_rect.bottom + 40
        for line in self.rules_text:
            text_surface = self.font_text.render(line, True, LIGHT_GRAY)
            text_rect = text_surface.get_rect(midtop=(SCREEN_WIDTH / 2, y_offset))
            screen.blit(text_surface, text_rect)
            y_offset += text_rect.height + 10

        self.back_button.draw(screen)

class PlayingState(BaseState):
    def __init__(self, game, state_manager):
        super().__init__(game, state_manager)
        self.last_mouse_pos = (0, 0)
        self.building_mode = False
        self.font_hud = pygame.font.Font(FONT_NAME, FONT_S)
        self.font_build_price = pygame.font.Font(FONT_NAME, FONT_XS)

        # Cache images for performance (prototypes are in Game class)
        self.tower_image_local = pygame.Surface((TOWER_SIZE, TOWER_SIZE), pygame.SRCALPHA)
        self.tower_image_local.fill((0, 0, 255, 180)) # Blue for tower
        pygame.draw.rect(self.tower_image_local, (0, 0, 150), self.tower_image_local.get_rect(), 2)

        # Build button
        self.build_button_rect = pygame.Rect(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 60, 140, 50)
        self.build_button = Button(
            self.build_button_rect,
            f"建造 ({TOWER_BUILD_COST}金)", self.font_build_price, self._toggle_build_mode
        )
        self.build_button.color = (0, 150, 0) # Green for build button
        self.build_button.hover_color = (0, 200, 0)

    def enter(self, **kwargs):

        # [新增] 檢查是否有傳入 resume 參數
        if kwargs.get('resume'):
            return

        # Reset game state only when entering PlayingState from Main Menu or Restart
        if self.state_manager.state_stack[0] == self: # If playing state is the first (base) state
            self.game.reset_game() 

    def _toggle_build_mode(self):
        self.building_mode = not self.building_mode

    def handle_input(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.last_mouse_pos = event.pos
            self.build_button.handle_input(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.build_button.rect.collidepoint(event.pos):
                self.build_button.on_click()
            elif self.building_mode:
                map_coords = self.game.camera_group.get_map_coords(event.pos)
                # Align to grid center, not top-left
                grid_pos_tuple = self.game.grid_system.get_grid_pos(map_coords)
                world_snap_pos = self.game.grid_system.get_world_coords(grid_pos_tuple)

                if self.game.player_manager.can_afford(TOWER_BUILD_COST):
                    if self.game.grid_system.is_grid_free(grid_pos_tuple):
                        self.game.player_manager.spend_gold(TOWER_BUILD_COST)
                        new_tower = self.game.defense_tower_pool.get()
                        if new_tower:
                            # Pass prototype tower image and bullet image to the new tower
                            new_tower.activate(world_snap_pos, self.game.all_enemies, 
                                               self.game.bullet_pool, self.game.all_bullets, 
                                               self.tower_image_local, self.game.bullet_image_proto,
                                               self.game.camera_group # <--- [新增] 傳入相機群組
                            )
                            self.game.all_buildings.add(new_tower)
                            self.game.all_towers.add(new_tower)
                            self.game.camera_group.add(new_tower)
                            self.game.grid_system.place_object(grid_pos_tuple, new_tower)
                            self.building_mode = False # Exit build mode after building
                        else:
                            self.game.event_bus.publish(EVENT_GAME_MESSAGE, message="建造失敗: 無法取得防禦塔實體", color=RED)
                    else:
                        self.game.event_bus.publish(EVENT_GAME_MESSAGE, message="建造失敗: 網格已被佔用", color=RED)
                else:
                    self.game.event_bus.publish(EVENT_GAME_MESSAGE, message="建造失敗: 金幣不足", color=RED)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.state_manager.push_state("PAUSED_STATE")

    def update(self, dt):
        self.game.camera_group.mouse_control(self.last_mouse_pos, dt) # Continuous camera scroll

        self.game.wave_manager.update(dt) # Spawn enemies

        # Update all active sprites
        self.game.camera_group.update(dt) # This updates all sprites including enemies, towers, bullets

        # CRITICAL: Enemy targeting logic 
        # Enemies target nearest building (CommandCenter > DefenseTower)
        for enemy in self.game.all_enemies:
            # Only if target is dead or not set, find a new one
            if not enemy.target_building or not enemy.target_building.alive():
                closest_building = None
                min_dist_sq = float('inf')

                # Prioritize Command Center
                if self.game.command_center.alive():
                    dist_to_cc_sq = (enemy.pos - self.game.command_center.pos).length_squared()
                    if dist_to_cc_sq < min_dist_sq:
                        min_dist_sq = dist_to_cc_sq
                        closest_building = self.game.command_center

                # Then check other towers
                for tower in self.game.all_towers:
                    if tower.alive(): # Only consider active towers
                        dist_to_tower_sq = (enemy.pos - tower.pos).length_squared()
                        if dist_to_tower_sq < min_dist_sq:
                            min_dist_sq = dist_to_tower_sq
                            closest_building = tower
                
                enemy.target_building = closest_building
            
        # Collision detection
        # Bullet vs Enemy
        self.game.collision_manager.apply_group_vs_group(
            self.game.all_bullets, self.game.all_enemies,
            self._handle_bullet_enemy_collision, dokill=False # Bullets and enemies handled manually
        )

        # Enemy vs Building (CommandCenter + DefenseTowers)
        self.game.collision_manager.apply_group_vs_group(
            self.game.all_enemies, self.game.all_buildings,
            self._handle_enemy_building_collision, dokill=False # Enemies don't die on collision, buildings don't die immediately
        )

        # Check game win/lose conditions
        if self.game.player_manager.kills >= WIN_KILL_COUNT:
            self.state_manager.change_state("GAME_OVER_STATE", success=True)
        elif self.game.command_center.current_hp <= 0:
            self.state_manager.change_state("GAME_OVER_STATE", success=False)

        # Remove dead sprites from groups and release to pool
        # Iterate over camera_group which contains all renderable active sprites
        # sprite.kill() ensures removal from all groups it's in.
        for sprite in list(self.game.camera_group):
            if not sprite.alive():
                if isinstance(sprite, BasicEnemy):
                    self.game.enemy_pool.release(sprite)
                elif isinstance(sprite, Bullet):
                    self.game.bullet_pool.release(sprite)
                elif isinstance(sprite, DefenseTower):
                    # Crucially remove from grid system BEFORE releasing
                    if sprite.grid_pos: # Check if grid_pos was actually set
                        self.game.grid_system.remove_object(sprite.grid_pos)
                    self.game.defense_tower_pool.release(sprite)
                # CommandCenter is not pooled. Its death leads to game over and reset_game handles its re-creation.
                # No explicit release for CommandCenter.


    def _handle_bullet_enemy_collision(self, bullet, enemy):
        if bullet.alive() and enemy.alive():
            enemy.take_damage(bullet.damage)
            bullet.kill() # Bullet is destroyed
            # bullet is automatically released by cleanup loop

            if not enemy.alive():
                self.game.player_manager.add_gold(GOLD_PER_KILL)
                self.game.player_manager.add_kill()
                # enemy is automatically released by cleanup loop


    def _handle_enemy_building_collision(self, enemy, building):
        # Enemy is actively colliding with a building. Apply damage over time.
        if enemy.alive() and building.alive() and enemy.rect.colliderect(building.rect):
            enemy.attack_building(building, self.game.dt)
            # Building will be removed by cleanup loop if HP <= 0


    def draw(self, screen):
        # Draw game map and entities
        self.game.camera_group.custom_draw(screen, self.game.background_map)

        # Draw build preview if in build mode
        if self.building_mode:
            map_coords = self.game.camera_group.get_map_coords(self.last_mouse_pos)
            grid_pos_tuple = self.game.grid_system.get_grid_pos(map_coords)
            world_snap_pos = self.game.grid_system.get_world_coords(grid_pos_tuple) # Get world center of grid cell
            screen_snap_pos = self.game.camera_group.get_screen_coords(world_snap_pos)

            preview_image = self.tower_image_local.copy()
            if self.game.player_manager.can_afford(TOWER_BUILD_COST) and \
               self.game.grid_system.is_grid_free(grid_pos_tuple):
                preview_image.set_alpha(150) # Buildable (green tint)
                pygame.draw.rect(preview_image, GREEN, preview_image.get_rect(), 3)
            else:
                preview_image.set_alpha(50) # Not Buildable (red tint)
                pygame.draw.rect(preview_image, RED, preview_image.get_rect(), 3)

            preview_rect = preview_image.get_rect(center=screen_snap_pos)
            screen.blit(preview_image, preview_rect)


        # Draw HUD elements (fixed on screen)
        # Gold
        gold_text = self.font_hud.render(f"金幣: {self.game.player_manager.gold}", True, WHITE)
        screen.blit(gold_text, (10, 10))

        # Kills
        kills_text = self.font_hud.render(f"擊殺: {self.game.player_manager.kills}/{WIN_KILL_COUNT}", True, WHITE)
        screen.blit(kills_text, (SCREEN_WIDTH - kills_text.get_width() - 10, 10))

        # Command Center HP
        cc_hp_text = self.font_hud.render(
            f"指揮中心: {max(0, self.game.command_center.current_hp)}/{self.game.command_center.max_hp}", True, YELLOW)
        cc_hp_rect = cc_hp_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 40))
        screen.blit(cc_hp_text, cc_hp_rect)

        # Build button
        self.build_button.draw(screen)

        # Display game messages (e.g., "Gold insufficient")
        if self.game.game_message_timer > 0:
            msg_surf = self.font_hud.render(self.game.game_message, True, self.game.game_message_color)
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH / 2, 50))
            screen.blit(msg_surf, msg_rect)


class PausedState(BaseState):
    def __init__(self, game, state_manager):
        super().__init__(game, state_manager)
        self.font_title = pygame.font.Font(FONT_NAME, FONT_L)
        self.font_button = pygame.font.Font(FONT_NAME, FONT_M)

        self.buttons = []
        self._setup_buttons()

    def _setup_buttons(self):
        button_width = 250
        button_height = 60
        button_spacing = 15
        start_y = SCREEN_HEIGHT / 2 - (button_height * 2 + button_spacing * 1.5)

        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y, button_width, button_height), # Fix: Added width and height
            "繼續遊戲", self.font_button, lambda: self.state_manager.pop_state(resume = True)   #<-新增
        ))
        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y + button_height + button_spacing, button_width, button_height), # Fix: Added width and height
            "重新開始", self.font_button, lambda: self.state_manager.change_state("PLAYING_STATE")
        ))
        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y + (button_height + button_spacing) * 2, button_width, button_height), # Fix: Added width and height
            "遊戲規則", self.font_button, lambda: self.state_manager.push_state("RULES_SCREEN")
        ))
        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y + (button_height + button_spacing) * 3, button_width, button_height), # Fix: Added width and height
            "回主選單", self.font_button, lambda: self.state_manager.change_state("MAIN_MENU_STATE")
        ))

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_input(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.state_manager.pop_state() # Resume game

    def draw(self, screen):
        # Draw previous state (PlayingState) beneath, which is already handled by GameStateManager.draw loop
        
        # Draw transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(TRANSPARENT_BLACK)
        screen.blit(overlay, (0, 0))

        title_surface = self.font_title.render("遊戲暫停", True, WHITE)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4))
        screen.blit(title_surface, title_rect)

        for button in self.buttons:
            button.draw(screen)

class GameOverState(BaseState):
    def __init__(self, game, state_manager):
        super().__init__(game, state_manager)
        self.font_result = pygame.font.Font(FONT_NAME, FONT_XL)
        self.font_stats = pygame.font.Font(FONT_NAME, FONT_M)
        self.font_button = pygame.font.Font(FONT_NAME, FONT_L)
        self.success = False
        self.final_kills = 0
        self.final_gold = 0

        self.buttons = []
        self._setup_buttons()

    def _setup_buttons(self):
        button_width = 300
        button_height = 70
        button_spacing = 20
        start_y = SCREEN_HEIGHT * 0.7 - button_height

        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y, button_width, button_height), # Fix: Added width and height
            "重新開始", self.font_button, lambda: self.state_manager.change_state("PLAYING_STATE")
        ))
        self.buttons.append(Button(
            (SCREEN_WIDTH / 2 - button_width / 2, start_y + button_height + button_spacing, button_width, button_height), # Fix: Added width and height
            "返回主選單", self.font_button, lambda: self.state_manager.change_state("MAIN_MENU_STATE")
        ))

    def enter(self, **kwargs):
        self.success = kwargs.setdefault('success', False) # CRITICAL: using setdefault
        self.final_kills = self.game.player_manager.kills
        self.final_gold = self.game.player_manager.gold

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_input(event)

    def draw(self, screen):
        screen.fill(DARK_GRAY)

        result_text = "勝利!" if self.success else "失敗!"
        result_color = GREEN if self.success else RED
        result_surface = self.font_result.render(result_text, True, result_color)
        result_rect = result_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4))
        screen.blit(result_surface, result_rect)

        stats_text = f"總擊殺數: {self.final_kills}"
        stats_surface = self.font_stats.render(stats_text, True, WHITE)
        stats_rect = stats_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2.5))
        screen.blit(stats_surface, stats_rect)

        gold_text = f"剩餘金幣: {self.final_gold}"
        gold_surface = self.font_stats.render(gold_text, True, WHITE)
        gold_rect = gold_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2.5 + 40))
        screen.blit(gold_surface, gold_rect)

        for button in self.buttons:
            button.draw(screen)

# --- Game Entities ---
class CommandCenter(GameSprite):
    def __init__(self, position, image):
        super().__init__(image, position)
        self.max_hp = CC_MAX_HP
        self.current_hp = self.max_hp
        self.is_building = True # For enemy targeting priority
        self.grid_pos = None # To be set by grid system

    def take_damage(self, amount):
        if self.current_hp > 0:
            self.current_hp -= amount
            if self.current_hp <= 0:
                self.current_hp = 0
                self.die()

    def die(self):
        self.kill() # Remove from all groups
        # Game over logic will check CC HP

    def reset(self):
        super().reset()

        # [新增] 這裡要手動把位置修復回地圖中央
        self.pos = pygame.math.Vector2(CC_INITIAL_POS) 
        self.rect.center = round(self.pos.x), round(self.pos.y)

        self.max_hp = CC_MAX_HP
        self.current_hp = self.max_hp
        self.is_building = True
        self.grid_pos = None # Reset grid_pos
        # Note: This sprite is typically re-added by Game.reset_game manually.


class DefenseTower(GameSprite):
    def __init__(self):
        # Image is set during activation, so init with default or None
        super().__init__(None, (0, 0))
        self.max_hp = TOWER_MAX_HP
        self.current_hp = self.max_hp
        self.attack_damage = TOWER_ATTACK_DAMAGE
        self.attack_speed = TOWER_ATTACK_SPEED
        self.attack_range = TOWER_ATTACK_RANGE
        self.cooldown_timer = 0.0
        self.is_building = True # For enemy targeting priority

        # Dependencies to be injected via activate
        self.bullet_pool = None 
        self.all_enemies = None 
        self.all_bullets_group = None 
        self.camera_group = None # <--- [新增] 1. 預留 camera_group 的位置
        self.grid_pos = None # Stored grid position for grid system management
        self.bullet_image_prototype = None

    def activate(self, position, all_enemies_group, bullet_pool, all_bullets_group, tower_image, bullet_image_prototype, camera_group):# <--- [修改] 2. 增加參數
        self.pos = pygame.math.Vector2(position)
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.image = tower_image # Set image on activation
        self.current_hp = self.max_hp
        self.cooldown_timer = 0.0
        self.bullet_pool = bullet_pool
        self.all_enemies = all_enemies_group
        self.all_bullets_group = all_bullets_group
        self.camera_group = camera_group # <--- [新增] 3. 儲存 camera_group 引用
        self.bullet_image_prototype = bullet_image_prototype
        # Grid pos is set by GridSystem, passed in as position for now.
        # This will be overridden by grid_system.place_object
        self.grid_pos = pygame.math.Vector2(position) 

    def update(self, dt):
        super().update(dt) # Updates self.rect from self.pos
        if not self.alive(): return

        self.cooldown_timer -= dt
        if self.cooldown_timer <= 0:
            target_enemy = self._find_nearest_enemy()
            if target_enemy:
                self._shoot(target_enemy)
                self.cooldown_timer = self.attack_speed

    def _find_nearest_enemy(self):
        nearest_enemy = None
        min_dist_sq = self.attack_range ** 2

        for enemy in self.all_enemies:
            if enemy.alive():
                dist_sq = (enemy.pos - self.pos).length_squared()
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    nearest_enemy = enemy
        return nearest_enemy

    def _shoot(self, target_enemy):
        bullet = self.bullet_pool.get()
        if bullet:
            # Pass target_enemy.pos instead of target_enemy directly for simpler fixed-point targeting
            # For complex homing, we'd pass the enemy object and update bullet's target in its own update
            bullet.activate(self.pos, target_enemy.pos, self.attack_damage, self.attack_range, self.bullet_image_prototype)
            self.all_bullets_group.add(bullet)
            self.camera_group.add(bullet)      # <--- [關鍵修正] 4. 這是讓子彈會動且看得到的關鍵！

    def take_damage(self, amount):
        if self.current_hp > 0:
            self.current_hp -= amount
            if self.current_hp <= 0:
                self.current_hp = 0
                self.die()

    def die(self):
        self.kill() # Remove from all groups

    def reset(self):
        super().reset()
        self.max_hp = TOWER_MAX_HP
        self.current_hp = self.max_hp
        self.attack_damage = TOWER_ATTACK_DAMAGE
        self.attack_speed = TOWER_ATTACK_SPEED
        self.attack_range = TOWER_ATTACK_RANGE
        self.cooldown_timer = 0.0
        self.is_building = True
        self.bullet_pool = None
        self.all_enemies = None
        self.all_bullets_group = None
        self.camera_group = None # <--- [新增] 重置引用
        self.grid_pos = None
        self.bullet_image_prototype = None


class BasicEnemy(GameSprite):
    def __init__(self):
        super().__init__(None, (0, 0))
        self.max_hp = ENEMY_MAX_HP
        self.current_hp = self.max_hp
        self.move_speed = ENEMY_MOVE_SPEED
        self.attack_damage = ENEMY_ATTACK_DAMAGE_TO_BUILDING
        self.attack_frequency = ENEMY_ATTACK_FREQUENCY
        self.attack_cooldown_timer = 0.0
        self.target_building = None 

    def activate(self, position, image):
        self.pos = pygame.math.Vector2(position)
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.image = image
        self.current_hp = self.max_hp
        self.attack_cooldown_timer = 0.0
        self.target_building = None

    def update(self, dt):
        super().update(dt)
        if not self.alive(): return

        if self.target_building and self.target_building.alive():
            # Calculate direction towards the target building
            direction = self.target_building.pos - self.pos
            
            # If enemy is not yet colliding, move towards target
            if not self.rect.colliderect(self.target_building.rect):
                if direction.length_squared() > 0: # Avoid division by zero if already at target
                    direction.normalize_ip()
                    self.pos += direction * self.move_speed * dt
            # If colliding, attack logic is handled by _handle_enemy_building_collision
        else:
            # If no target or target died, it will be reassigned by PlayingState's update loop
            pass

    def take_damage(self, amount):
        if self.current_hp > 0:
            self.current_hp -= amount
            if self.current_hp <= 0:
                self.current_hp = 0
                self.die()

    def attack_building(self, building, dt):
        self.attack_cooldown_timer -= dt
        if self.attack_cooldown_timer <= 0:
            building.take_damage(self.attack_damage)
            self.attack_cooldown_timer = self.attack_frequency

    def die(self):
        self.kill() # Remove from all groups

    def reset(self):
        super().reset()
        self.max_hp = ENEMY_MAX_HP
        self.current_hp = self.max_hp
        self.move_speed = ENEMY_MOVE_SPEED
        self.attack_damage = ENEMY_ATTACK_DAMAGE_TO_BUILDING
        self.attack_frequency = ENEMY_ATTACK_FREQUENCY
        self.attack_cooldown_timer = 0.0
        self.target_building = None


class Bullet(GameSprite):
    def __init__(self):
        super().__init__(None, (0, 0))
        self.damage = BULLET_DAMAGE
        self.move_speed = BULLET_MOVE_SPEED
        self.velocity = pygame.math.Vector2(0, 0)
        self.target_pos = pygame.math.Vector2(0, 0) # The fixed point the bullet aims for
        self.origin_pos = pygame.math.Vector2(0,0)
        self.range_limit_sq = 0 # Squared range for efficiency

    def activate(self, start_pos, target_pos, damage, range_limit, image):
        self.pos = pygame.math.Vector2(start_pos)
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.image = image # Set bullet image on activation

        self.damage = damage
        self.target_pos = pygame.math.Vector2(target_pos) 
        self.origin_pos = pygame.math.Vector2(start_pos)
        self.range_limit_sq = range_limit ** 2

        # Calculate initial velocity towards target
        direction = (self.target_pos - self.pos)
        if direction.length_squared() > 0: # Avoid division by zero
            direction.normalize_ip()
            self.velocity = direction * self.move_speed
        else:
            self.velocity = pygame.math.Vector2(0,0) # If already at target, don't move.

    def update(self, dt):
        super().update(dt)
        if not self.alive(): return

        # Move
        self.pos += self.velocity * dt

        # Check if out of range from origin
        if (self.pos - self.origin_pos).length_squared() > self.range_limit_sq:
            self.die() # Remove if out of range
            return

    def die(self):
        self.kill() # Remove from all groups

    def reset(self):
        super().reset()
        self.damage = BULLET_DAMAGE
        self.move_speed = BULLET_MOVE_SPEED
        self.velocity = pygame.math.Vector2(0, 0)
        self.target_pos = pygame.math.Vector2(0, 0)
        self.origin_pos = pygame.math.Vector2(0,0)
        self.range_limit_sq = 0


# --- Game Managers ---
class PlayerManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._gold = INITIAL_GOLD
        self._kills = 0

    @property
    def gold(self):
        return self._gold

    @gold.setter
    def gold(self, value):
        self._gold = max(0, value) # Gold cannot be negative
        self.event_bus.publish(EVENT_GOLD_CHANGED, gold=self._gold)

    @property
    def kills(self):
        return self._kills

    @kills.setter
    def kills(self, value):
        self._kills = value
        self.event_bus.publish(EVENT_KILL_COUNT_CHANGED, kills=self._kills)

    def add_gold(self, amount):
        self.gold += amount

    def spend_gold(self, amount):
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False

    def can_afford(self, amount):
        return self.gold >= amount

    def add_kill(self):
        self.kills += 1

    def reset(self):
        self.gold = INITIAL_GOLD
        self.kills = 0

class WaveManager:
    def __init__(self, enemy_pool, all_enemies_group, camera_group, event_bus, enemy_image_proto):
        self.enemy_pool = enemy_pool
        self.all_enemies_group = all_enemies_group
        self.camera_group = camera_group
        self.event_bus = event_bus
        self.enemy_image_prototype = enemy_image_proto # Pass a reference to the image surface

        self.current_wave = 0
        self.enemies_spawned_in_wave = 0
        self.wave_timer = 0.0
        self.spawn_interval = 2.0 # Time between individual enemy spawns
        self.wave_delay = 10.0 # Time between waves (after previous wave cleared)

        self.enemy_spawn_queue = deque()
        self.is_spawning_wave = False
        self.num_enemies_per_wave_base = 5
        self.num_enemies_per_wave_growth = 2 # Each wave adds this many more enemies

    def start_next_wave(self):
        self.current_wave += 1
        num_enemies_to_spawn = self.num_enemies_per_wave_base + (self.current_wave - 1) * self.num_enemies_per_wave_growth
        self.event_bus.publish(EVENT_GAME_MESSAGE, message=f"第 {self.current_wave} 波敵人來襲!", color=RED)
        print(f"Starting Wave {self.current_wave} with {num_enemies_to_spawn} enemies.")
        for _ in range(num_enemies_to_spawn):
            self.enemy_spawn_queue.append(1) # Add a placeholder to queue for each enemy
        self.enemies_spawned_in_wave = 0
        self.wave_timer = self.spawn_interval
        self.is_spawning_wave = True

    def update(self, dt):
        if self.is_spawning_wave:
            self.wave_timer -= dt
            if self.wave_timer <= 0 and self.enemy_spawn_queue:
                self.spawn_enemy()
                self.enemies_spawned_in_wave += 1
                self.enemy_spawn_queue.popleft()
                self.wave_timer = self.spawn_interval # Reset timer for next enemy

            # Check if all enemies in current wave have been spawned AND all active enemies are dead
            if not self.enemy_spawn_queue and len(self.all_enemies_group) == 0:
                self.is_spawning_wave = False
                self.wave_timer = self.wave_delay # Start delay for next wave
                if self.current_wave <= (WIN_KILL_COUNT / self.num_enemies_per_wave_base): # Roughly check if we are near win condition
                    self.event_bus.publish(EVENT_GAME_MESSAGE, message=f"第 {self.current_wave} 波已清除! 下一波在 {self.wave_delay} 秒後.", color=GREEN)
                print(f"Wave {self.current_wave} cleared. Next wave in {self.wave_delay} seconds.")
        elif self.current_wave == 0 or (not self.is_spawning_wave and len(self.all_enemies_group) == 0): # If first wave or previous wave cleared
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.start_next_wave()
        
    def spawn_enemy(self):
        enemy = self.enemy_pool.get()
        if enemy:
            # Spawn from a random point on map edges
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top':
                spawn_pos = (random.randint(0, MAP_WIDTH), 0)
            elif side == 'bottom':
                spawn_pos = (random.randint(0, MAP_WIDTH), MAP_HEIGHT)
            elif side == 'left':
                spawn_pos = (0, random.randint(0, MAP_HEIGHT))
            else: # 'right'
                spawn_pos = (MAP_WIDTH, random.randint(0, MAP_HEIGHT))
            
            enemy.activate(spawn_pos, self.enemy_image_prototype) # Use the prototype image
            self.all_enemies_group.add(enemy)
            self.camera_group.add(enemy)
        else:
            self.event_bus.publish(EVENT_GAME_MESSAGE, message="敵人生成失敗: 物件池枯竭", color=RED)

    def reset(self):
        self.current_wave = 0
        self.enemies_spawned_in_wave = 0
        self.wave_timer = 0.0
        self.enemy_spawn_queue.clear()
        self.is_spawning_wave = False


class GridSystem:
    def __init__(self, grid_size=TOWER_SIZE, map_width=MAP_WIDTH, map_height=MAP_HEIGHT):
        self.grid_size = grid_size
        self.map_width = map_width
        self.map_height = map_height
        self.grid_width = math.ceil(map_width / grid_size)
        self.grid_height = math.ceil(map_height / grid_size)
        self.occupied_cells = set() # Store (grid_x, grid_y) tuples

    def get_grid_pos(self, world_coords):
        """Converts world coordinates to grid coordinates."""
        grid_x = int(world_coords.x // self.grid_size)
        grid_y = int(world_coords.y // self.grid_size)
        return (grid_x, grid_y)

    def get_world_coords(self, grid_pos_tuple):
        """Converts grid coordinates to world coordinates (center of cell)."""
        grid_x, grid_y = grid_pos_tuple
        world_x = grid_x * self.grid_size + self.grid_size / 2
        world_y = grid_y * self.grid_size + self.grid_size / 2
        return pygame.math.Vector2(world_x, world_y)

    def is_grid_free(self, grid_pos_tuple):
        """Checks if a grid cell is free and within map boundaries."""
        grid_x, grid_y = grid_pos_tuple
        if not (0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height):
            return False # Out of bounds
        return grid_pos_tuple not in self.occupied_cells

    def place_object(self, grid_pos_tuple, obj):
        """Marks a grid cell as occupied."""
        if self.is_grid_free(grid_pos_tuple):
            self.occupied_cells.add(grid_pos_tuple)
            # Store the actual grid tuple on the object for easy removal later
            obj.grid_pos = grid_pos_tuple 
            return True
        return False

    def remove_object(self, grid_pos_tuple):
        """Frees a grid cell."""
        if grid_pos_tuple in self.occupied_cells:
            self.occupied_cells.remove(grid_pos_tuple)
            return True
        return False

    def reset(self):
        self.occupied_cells.clear()


# --- Main Game Class ---
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("末日要塞：RTS塔防")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0 # Delta time

        # CRITICAL: Auto-Test Hook
        self.game_active = False # Controls whether to skip menu on run()

        # Fonts (cached)
        self.font_s = pygame.font.Font(FONT_NAME, FONT_S)

        # Event Bus
        self.event_bus = EventBus()
        self.event_bus.subscribe(EVENT_GAME_MESSAGE, self._show_game_message)
        self.game_message = ""
        self.game_message_timer = 0.0
        self.game_message_duration = 3.0 # seconds
        self.game_message_color = WHITE

        # --- Game Managers and Groups ---
        self.player_manager = PlayerManager(self.event_bus)
        self.collision_manager = CollisionManager()
        self.grid_system = GridSystem()

        # Sprite Groups
        self.camera_group = MouseCameraGroup(MAP_WIDTH, MAP_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT) # Main drawing group (contains all active sprites)
        self.all_buildings = pygame.sprite.Group() # CommandCenter + DefenseTowers
        self.all_towers = pygame.sprite.Group() # Only DefenseTowers
        self.all_enemies = pygame.sprite.Group()
        self.all_bullets = pygame.sprite.Group()

        # Object Pools
        self.defense_tower_pool = ObjectPool(DefenseTower, initial_size=10)
        self.enemy_pool = ObjectPool(BasicEnemy, initial_size=20)
        self.bullet_pool = ObjectPool(Bullet, initial_size=50)

        # Prototype images for entities (passed to managers/entities)
        self.cc_image_proto = pygame.Surface((CC_SIZE, CC_SIZE), pygame.SRCALPHA)
        self.cc_image_proto.fill((255, 255, 0, 200))
        pygame.draw.rect(self.cc_image_proto, (150, 150, 0), self.cc_image_proto.get_rect(), 2)

        self.enemy_image_proto = pygame.Surface((ENEMY_SIZE, ENEMY_SIZE), pygame.SRCALPHA)
        self.enemy_image_proto.fill((255, 0, 0, 180))
        pygame.draw.circle(self.enemy_image_proto, (150, 0, 0), (ENEMY_SIZE//2, ENEMY_SIZE//2), ENEMY_SIZE//2 - 2)
        
        self.bullet_image_proto = pygame.Surface((BULLET_SIZE, BULLET_SIZE), pygame.SRCALPHA)
        self.bullet_image_proto.fill((255, 255, 255, 255)) # White for bullet
        pygame.draw.circle(self.bullet_image_proto, (200, 200, 200), (BULLET_SIZE//2, BULLET_SIZE//2), BULLET_SIZE//2 - 1)


        # Wave Manager
        self.wave_manager = WaveManager(self.enemy_pool, self.all_enemies, self.camera_group, self.event_bus, self.enemy_image_proto)
        
        # Command Center (Initialized here as it's a fixed unique entity)
        self.command_center = CommandCenter(CC_INITIAL_POS, self.cc_image_proto)
        self.all_buildings.add(self.command_center)
        self.camera_group.add(self.command_center)
        self.grid_system.place_object(self.grid_system.get_grid_pos(CC_INITIAL_POS), self.command_center)


        # Game State Manager
        self.state_manager = GameStateManager(self)
        self.main_menu_state = MainMenuState(self, self.state_manager)
        self.playing_state = PlayingState(self, self.state_manager)
        self.paused_state = PausedState(self, self.state_manager)
        self.rules_state = RulesState(self, self.state_manager)
        self.game_over_state = GameOverState(self, self.state_manager)

        self.state_manager.add_state("MAIN_MENU_STATE", self.main_menu_state)
        self.state_manager.add_state("PLAYING_STATE", self.playing_state)
        self.state_manager.add_state("PAUSED_STATE", self.paused_state)
        self.state_manager.add_state("RULES_SCREEN", self.rules_state)
        self.state_manager.add_state("GAME_OVER_STATE", self.game_over_state)

        # Initial state
        self.state_manager.change_state("MAIN_MENU_STATE")

        # Background map - a single large surface
        self.background_map = self._generate_background_map(MAP_WIDTH, MAP_HEIGHT)
        self.camera_group.set_camera_offset_to_center_map() # Initial camera to map center


    def _show_game_message(self, message, color=WHITE):
        self.game_message = message
        self.game_message_color = color
        self.game_message_timer = self.game_message_duration

    def _generate_background_map(self, width, height):
        bg = pygame.Surface((width, height))
        bg.fill((60, 80, 60)) # Dark green/forest color
        # Add some simple grid lines or texture
        for x in range(0, width, TOWER_SIZE):
            pygame.draw.line(bg, (50, 70, 50), (x, 0), (x, height))
        for y in range(0, height, TOWER_SIZE):
            pygame.draw.line(bg, (50, 70, 50), (0, y), (width, y))
        
        # Draw a central playable area or indication around CC
        pygame.draw.circle(bg, (80, 100, 80), self.command_center.pos, TOWER_ATTACK_RANGE * 2, 0)
        pygame.draw.circle(bg, (100, 120, 100), self.command_center.pos, TOWER_ATTACK_RANGE * 2, 2)
        
        return bg

    def start_game(self):
        # This will call PlayingState's enter, which then calls reset_game
        self.state_manager.change_state("PLAYING_STATE")

    def reset_game(self):
        # Reset all game entities and managers to their initial state
        print("Resetting game...")
        self.player_manager.reset()
        self.wave_manager.reset()
        self.grid_system.reset()

        # Clear all sprite groups and release to pools
        # Iterate over camera_group which contains all active visual sprites
        for sprite in list(self.camera_group): 
            sprite.kill() # This removes from all groups it's currently in
            # Check sprite type and release to appropriate pool / perform specific cleanup
            if isinstance(sprite, BasicEnemy):
                self.enemy_pool.release(sprite)
            elif isinstance(sprite, Bullet):
                self.bullet_pool.release(sprite)
            elif isinstance(sprite, DefenseTower):
                if sprite.grid_pos: # Ensure grid_pos was set
                    self.grid_system.remove_object(sprite.grid_pos)
                self.defense_tower_pool.release(sprite)
            # CommandCenter is not pooled. Its death leads to game over and reset_game handles its re-creation.
            # No explicit release for CommandCenter here.
        
        # Manually clear groups that are not just the camera_group for certainty (though kill() should handle it)
        self.all_buildings.empty()
        self.all_towers.empty()
        self.all_enemies.empty()
        self.all_bullets.empty()

        # Re-initialize Command Center as it's a unique entity and vital
        self.command_center.reset() # Resets its HP, etc.
        self.all_buildings.add(self.command_center)
        self.camera_group.add(self.command_center)
        self.grid_system.place_object(self.grid_system.get_grid_pos(CC_INITIAL_POS), self.command_center)

        # CRITICAL: Reset camera to command center
        self.camera_group.center_camera(self.command_center.pos)
        print("Game reset complete.")


    def quit_game(self):
        self.running = False

    def run(self):
        # CRITICAL: Auto-Test Hook for skipping menu
        if self.game_active:
            print("Auto-start game for testing.")
            self.start_game()
        
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0 # Delta time in seconds

            # Update game message timer
            if self.game_message_timer > 0:
                self.game_message_timer -= self.dt
                if self.game_message_timer <= 0:
                    self.game_message = ""


            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                self.state_manager.handle_input(event)

            self.state_manager.update(self.dt)
            self.state_manager.draw(self.screen)

            pygame.display.flip()

        pygame.quit()


# --- Main Execution ---
if __name__ == '__main__':
    game = Game()
    # CRITICAL: Auto-Test Hook: Explicitly set to False to ensure menu displays
    game.game_active = False 
    game.run()