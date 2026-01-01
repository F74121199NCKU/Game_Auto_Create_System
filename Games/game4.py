import pygame
import sys
from enum import Enum, auto
import math
import json

# --- RAG 模組整合 (Reference Modules) ---
# object_pool.py
class ObjectPool:
    def __init__(self, obj_class, initial_size):
        self.obj_class = obj_class
        self.pool = []
        self.in_use = []
        self._create_objects(initial_size)

    def _create_objects(self, count):
        for _ in range(count):
            # Objects from pool should be able to be initialized with minimal/dummy args,
            # then fully configured via a reset_state method.
            self.pool.append(self.obj_class())

    def get(self, *args, **kwargs):
        if not self.pool:
            # Optionally grow the pool if empty
            # print(f"Pool for {self.obj_class.__name__} is empty, creating 1 new object.")
            self._create_objects(1)
        obj = self.pool.pop()
        # Re-initialize the object with specific runtime arguments via reset_state
        obj.reset_state(*args, **kwargs) 
        self.in_use.append(obj)
        return obj

    def release(self, obj):
        if obj in self.in_use:
            self.in_use.remove(obj)
            obj.kill() # Remove from any sprite groups it's a member of
            self.pool.append(obj)
        else:
            print(f"Warning: Object {obj} not found in active objects for release.")

    def get_in_use(self):
        return self.in_use

# sprite_manager.py
class GameSprite(pygame.sprite.Sprite):
    def __init__(self, x, y, width=None, height=None, image_path=None, image_surface=None, **kwargs):
        super().__init__()
        
        # Determine the image source
        if image_path:
            self.image = pygame.image.load(image_path).convert_alpha()
        elif image_surface:
            self.image = image_surface.convert_alpha() if image_surface.get_flags() & pygame.SRCALPHA else image_surface.convert()
        else:
            # Default to a generic placeholder if no image provided
            self.image = pygame.Surface((width or 10, height or 10), pygame.SRCALPHA)
            self.image.fill((255, 0, 255, 128)) # Pink transparent placeholder
            
        # Scale image if width and height are provided and an image was loaded/created
        if width is not None and height is not None and (image_path or image_surface):
            self.image = pygame.transform.scale(self.image, (width, height))
            
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos = pygame.math.Vector2(x, y) # 浮點數座標
        self.initial_pos = pygame.math.Vector2(x, y) # for reset
        self.original_image = self.image.copy() # Store original for potential rotation/scaling or alpha resets
        self.z_index = kwargs.get('z_index', 0) # For Y-sorting or custom layer sorting

    def update(self, dt, **kwargs):
        # Base update for GameSprite can be empty or handle basic animation/state
        pass

    def draw(self, surface, offset):
        # Draw the sprite on the surface, applying camera offset
        surface.blit(self.image, self.rect.topleft + offset)

# camera_player_center.py
class CameraScrollGroup(pygame.sprite.Group):
    def __init__(self, camera_width, camera_height, level_width, level_height, margin=100, bg_image_path=None):
        super().__init__()
        self.camera_rect = pygame.Rect(0, 0, camera_width, camera_height)
        self.level_width = level_width
        self.level_height = level_height
        self.margin = margin  # Distance from the edge before camera starts moving
        
        self.bg_image = None
        if bg_image_path:
            try:
                self.bg_image = pygame.image.load(bg_image_path).convert()
            except pygame.error as e:
                print(f"Warning: Could not load background image '{bg_image_path}': {e}")
                # Create a placeholder if image fails to load
                self.bg_image = pygame.Surface((self.camera_rect.width, self.camera_rect.height))
                self.bg_image.fill((135, 206, 235)) # Sky blue placeholder

    def custom_draw(self, surface, target_sprite):
        # Adjust camera_rect to center on target_sprite, clamping within level bounds
        target_center_x = target_sprite.rect.centerx
        target_center_y = target_sprite.rect.centery

        # Horizontal clamping
        self.camera_rect.centerx = target_center_x
        self.camera_rect.left = max(0, self.camera_rect.left)
        self.camera_rect.right = min(self.level_width, self.camera_rect.right)

        # Vertical clamping (keep camera fixed vertically if level is not tall enough, or center)
        self.camera_rect.centery = target_center_y
        self.camera_rect.top = max(0, self.camera_rect.top)
        self.camera_rect.bottom = min(self.level_height, self.camera_rect.bottom)
        
        # Calculate offset for drawing sprites
        offset = pygame.math.Vector2(-self.camera_rect.x, -self.camera_rect.y)
        
        # Draw background
        if self.bg_image:
            bg_width = self.bg_image.get_width()
            bg_height = self.bg_image.get_height()
            
            # Calculate where to start drawing the background
            start_x = (self.camera_rect.x // bg_width) * bg_width
            start_y = (self.camera_rect.y // bg_height) * bg_height
            
            # Draw enough tiles to cover the screen
            for x in range(start_x, self.camera_rect.x + self.camera_rect.width + bg_width, bg_width):
                for y in range(start_y, self.camera_rect.y + self.camera_rect.height + bg_height, bg_height):
                    surface.blit(self.bg_image, (x + offset.x, y + offset.y))

        # Sort sprites by z_index (and then y-coordinate for Y-sorting)
        sorted_sprites = sorted(self.sprites(), key=lambda sprite: (sprite.z_index, sprite.rect.bottom))

        # Draw visible sprites with frustum culling + margin
        for sprite in sorted_sprites:
            # Create a larger cull rect for the margin
            cull_rect = self.camera_rect.inflate(self.margin * 2, self.margin * 2)
            if cull_rect.colliderect(sprite.rect):
                surface.blit(sprite.image, sprite.rect.topleft + offset)
    
    def get_offset(self):
        return pygame.math.Vector2(-self.camera_rect.x, -self.camera_rect.y)

# collision.py
class CollisionManager:
    def __init__(self):
        pass

    def apply_sprite_vs_sprite(self, sprite1, sprite2, on_collide=None):
        if sprite1.rect.colliderect(sprite2.rect):
            if on_collide:
                on_collide(sprite1, sprite2)
            return True
        return False

    def apply_sprite_vs_group(self, sprite, group, on_collide=None):
        collided_sprites = pygame.sprite.spritecollide(sprite, group, False)
        if collided_sprites:
            if on_collide:
                for collided_sprite in collided_sprites:
                    on_collide(sprite, collided_sprite)
            return True
        return False

    def apply_group_vs_group(self, group1, group2, on_collide=None):
        collisions = pygame.sprite.groupcollide(group1, group2, False, False)
        if collisions:
            if on_collide:
                for sprite1, collided_sprites in collisions.items():
                    for sprite2 in collided_sprites:
                        on_collide(sprite1, sprite2)
            return True
        return False

# --- 遊戲特定常量 ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)

# --- 遊戲狀態管理 ---
class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    RULES = auto()
    WIN = auto()
    LOSE = auto()

# --- UI 系統 ---
class FontManager:
    def __init__(self):
        pygame.font.init()
        # 嘗試加載微軟正黑體，如果找不到則使用宋體或系統預設字體
        self.font_name = pygame.font.match_font('microsoftjhenghei') or \
                         pygame.font.match_font('simhei') or \
                         pygame.font.get_default_font()
        self.fonts = {}

    def get_font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(self.font_name, size)
        return self.fonts[size]

class Button:
    def __init__(self, rect, text, font, text_color, bg_color, hover_color, on_click=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.text_color = text_color
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.current_bg_color = bg_color
        self.on_click = on_click
        self.text_surface = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def draw(self, surface):
        pygame.draw.rect(surface, self.current_bg_color, self.rect, border_radius=5)
        surface.blit(self.text_surface, self.text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                self.current_bg_color = self.hover_color
            else:
                self.current_bg_color = self.bg_color
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                    return True
        return False

class Menu:
    def __init__(self, font_manager, title_text, options, callback_func, screen_width, screen_height):
        self.font_manager = font_manager
        self.title_text = title_text
        self.options = options # List of (text, action_id)
        self.callback_func = callback_func
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.buttons = []
        self._create_buttons()

    def _create_buttons(self):
        self.buttons.clear()
        button_width = 200
        button_height = 50
        spacing = 20
        total_height = len(self.options) * button_height + (len(self.options) - 1) * spacing
        start_y = (self.screen_height - total_height) // 2

        for i, (text, action_id) in enumerate(self.options):
            rect = pygame.Rect(
                (self.screen_width - button_width) // 2,
                start_y + i * (button_height + spacing),
                button_width,
                button_height
            )
            button = Button(
                rect,
                text,
                self.font_manager.get_font(24),
                WHITE,
                BLUE,
                LIGHT_GRAY,
                lambda aid=action_id: self.callback_func(aid) # Use lambda to capture action_id
            )
            self.buttons.append(button)

    def draw(self, surface):
        # Draw semi-transparent background overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) # Dark transparent
        surface.blit(overlay, (0, 0))

        # Draw title
        title_font = self.font_manager.get_font(48)
        title_surface = title_font.render(self.title_text, True, WHITE)
        title_rect = title_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 4))
        surface.blit(title_surface, title_rect)

        for button in self.buttons:
            button.draw(surface)

    def handle_event(self, event):
        for button in self.buttons:
            if button.handle_event(event):
                return True # Button was clicked
        return False

class RulesScreen:
    def __init__(self, font_manager, game_rules, screen_width, screen_height, return_callback):
        self.font_manager = font_manager
        self.game_rules = game_rules
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.return_callback = return_callback
        self.back_button = Button(
            pygame.Rect((screen_width - 150) // 2, screen_height - 100, 150, 40),
            "返回",
            font_manager.get_font(20),
            WHITE, BLUE, LIGHT_GRAY,
            self.return_callback
        )

    def draw(self, surface):
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        title_font = self.font_manager.get_font(40)
        title_surface = title_font.render("遊戲規則", True, WHITE)
        title_rect = title_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 6))
        surface.blit(title_surface, title_rect)

        text_font = self.font_manager.get_font(20)
        y_offset = title_rect.bottom + 30
        for rule in self.game_rules:
            text_surface = text_font.render(rule, True, WHITE)
            text_rect = text_surface.get_rect(midtop=(self.screen_width // 2, y_offset))
            surface.blit(text_surface, text_rect)
            y_offset += text_rect.height + 10
        
        self.back_button.draw(surface)

    def handle_event(self, event):
        if self.back_button.handle_event(event):
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.return_callback()
            return True
        return False

# --- 遊戲實體 ---
class Player(GameSprite):
    def __init__(self, x, y, platforms_group, player_config, gravity_val):
        super().__init__(x=x, y=y, width=40, height=40, image_path="assets/player.png", z_index=10)
        self.color = (0, 128, 255) # For internal use if no image
        self.platforms_group = platforms_group
        self.gravity = gravity_val

        # Player Physics Parameters (from JSON)
        self.max_horizontal_speed = player_config["max_horizontal_speed"]
        self.jump_force = player_config["jump_force"] # Negative for upwards
        self.horizontal_acceleration = player_config["horizontal_acceleration"]
        self.ground_friction_coefficient = player_config["ground_friction_coefficient"]
        self.air_damping_coefficient = player_config["air_damping_coefficient"]
        self.jump_buffer_time = player_config["jump_buffer_time"] # seconds
        self.coyote_time = player_config["coyote_time"] # seconds
        self.max_health = player_config["initial_health"]

        self.velocity = pygame.math.Vector2(0, 0)
        self.on_ground = False
        self.health = self.max_health
        self.facing_right = True
        self.jump_buffer_timer = 0
        self.coyote_timer = 0
        self.can_jump = False
        self.invincible_timer = 0 # For temporary invincibility after taking damage

    def handle_input(self, keys, dt):
        horizontal_input = 0
        if (keys[pygame.K_a] or keys[pygame.K_LEFT]):
            horizontal_input -= 1
            self.facing_right = False
        if (keys[pygame.K_d] or keys[pygame.K_RIGHT]):
            horizontal_input += 1
            self.facing_right = True

        # Apply horizontal acceleration
        if horizontal_input != 0:
            self.velocity.x += horizontal_input * self.horizontal_acceleration * dt
            # Clamp horizontal speed
            self.velocity.x = max(-self.max_horizontal_speed, min(self.velocity.x, self.max_horizontal_speed))
        else:
            # Apply friction/damping
            if self.on_ground:
                # Use pow for more realistic exponential decay
                self.velocity.x *= math.pow(self.ground_friction_coefficient, dt * 60) # Multiply by 60 for FPS-independent decay
            else:
                self.velocity.x *= math.pow(self.air_damping_coefficient, dt * 60) # Slower decay in air

        # Jump buffer logic
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]):
            if self.jump_buffer_timer <= 0: # Only start if not already counting down from a previous press
                self.jump_buffer_timer = self.jump_buffer_time 
        
        # Actual jump execution
        if self.jump_buffer_timer > 0 and self.can_jump:
            self.velocity.y = self.jump_force
            self.on_ground = False
            self.coyote_timer = 0 # Consume coyote time on successful jump
            self.jump_buffer_timer = 0 # Consume jump buffer on successful jump

    def _move_and_collide(self, dt):
        # --- [X 軸處理] ---
        # 1. 先只移動 X
        self.pos.x += self.velocity.x * dt
        self.rect.centerx = round(self.pos.x)
        
        # 2. 檢查 X 軸碰撞 (這時候 Y 還沒動，所以不會陷進地板)
        collisions_x = pygame.sprite.spritecollide(self, self.platforms_group, False)
        for platform in collisions_x:
            if self.velocity.x > 0: # 向右撞牆
                self.rect.right = platform.rect.left
            elif self.velocity.x < 0: # 向左撞牆
                self.rect.left = platform.rect.right
            self.pos.x = self.rect.centerx # 碰撞後修正浮點數座標
            self.velocity.x = 0

        # --- [Y 軸處理] ---
        # 3. 再移動 Y
        self.pos.y += self.velocity.y * dt
        self.rect.centery = round(self.pos.y)
        
        # 4. 檢查 Y 軸碰撞
        self.on_ground = False # 先假設在空中
        collisions_y = pygame.sprite.spritecollide(self, self.platforms_group, False)
        for platform in collisions_y:
            if self.velocity.y > 0: # 掉落地板
                self.rect.bottom = platform.rect.top
                self.on_ground = True
                self.coyote_timer = self.coyote_time 
            elif self.velocity.y < 0: # 頂到天花板
                self.rect.top = platform.rect.bottom
            self.pos.y = self.rect.centery # 碰撞後修正浮點數座標
            self.velocity.y = 0

        # 更新跳躍狀態
        self.can_jump = self.on_ground or self.coyote_timer > 0

    def update_physics(self, dt):
        # Apply gravity
        self.velocity.y += self.gravity * dt
        

        self._move_and_collide(dt)
        # Apply velocity to position
        #self.pos += self.velocity * dt

        # Update rect position (rounded for display)
        #self.rect.center = round(self.pos.x), round(self.pos.y)

    def check_platform_collisions(self):
        # Store original rect position for collision resolution
        original_rect_x = self.rect.centerx
        original_rect_y = self.rect.centery

        # Move X first
        self.rect.centerx = round(self.pos.x)
        collisions_x = pygame.sprite.spritecollide(self, self.platforms_group, False)
        for platform in collisions_x:
            if self.velocity.x > 0: # Moving right
                self.rect.right = platform.rect.left
            elif self.velocity.x < 0: # Moving left
                self.rect.left = platform.rect.right
            self.pos.x = self.rect.centerx # Synchronize pos with rect after collision
            self.velocity.x = 0

        # Move Y next
        self.rect.centery = round(self.pos.y)
        self.on_ground = False # Assume not on ground unless proven otherwise
        collisions_y = pygame.sprite.spritecollide(self, self.platforms_group, False)
        for platform in collisions_y:
            if self.velocity.y > 0: # Falling (hit ground)
                self.rect.bottom = platform.rect.top
                self.on_ground = True
                self.coyote_timer = self.coyote_time # Reset coyote time only if truly landing
            elif self.velocity.y < 0: # Jumping (hit ceiling)
                self.rect.top = platform.rect.bottom
            self.pos.y = self.rect.centery # Synchronize pos with rect after collision
            self.velocity.y = 0

        # Update can_jump state based on on_ground and coyote time
        # Do not decrement coyote_timer here; let the main update loop handle it once per frame.
        self.can_jump = self.on_ground or self.coyote_timer > 0 # Allow jump if on ground OR in coyote time

    def take_damage(self, amount):
        if self.invincible_timer <= 0:
            self.health -= amount
            self.invincible_timer = 1.0 # 1 second invincibility
            # No need to trigger game over here, main game loop checks player.health

    def update(self, dt):
        # Decrement timers
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt
        if not self.on_ground and self.coyote_timer > 0:
            self.coyote_timer -= dt
        
        # Decrement invincibility timer
        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        self.update_physics(dt)
        #self.check_platform_collisions() # Must happen after physics update for position

        # Visual feedback for invincibility (blinking)
        if self.invincible_timer > 0:
            if int(self.invincible_timer * 10) % 2 == 0:
                self.image.set_alpha(100) # Make semi-transparent
            else:
                self.image.set_alpha(255)
        else:
            if self.image.get_alpha() != 255: # Only reset if not already opaque to avoid constant calls
                self.image.set_alpha(255) # Fully opaque when not invincible

    def draw_hud(self, surface, font_manager):
        health_font = font_manager.get_font(24)
        health_text = f"HP: {self.health}/{self.max_health}"
        health_surface = health_font.render(health_text, True, WHITE)
        surface.blit(health_surface, (10, 10))

class Platform(GameSprite):
    def __init__(self, x, y, width, height):
        # Create a simple colored rect image
        image = pygame.Surface((width, height))
        image.fill((100, 200, 100)) # Greenish platform
        super().__init__(x=x, y=y, width=width, height=height, image_surface=image, z_index=0)

class SpikeTrap(GameSprite):
    def __init__(self):
        # Initialize GameSprite with dummy values for pooled objects, as reset_state will set actual values
        super().__init__(x=0, y=0, width=40, height=40, image_path="assets/spike_trap.png", z_index=5)
        self.start_pos = pygame.math.Vector2(0, 0)
        self.end_pos = pygame.math.Vector2(0, 0)
        self.movement_speed = 0
        self.direction = 1 # 1 for moving towards end_pos, -1 for moving towards start_pos
        self.reset_state() # Call reset_state to ensure default values are set, will be overwritten by pool.get()

    def reset_state(self, x=0, y=0, width=40, height=40, movement_range=0, movement_speed=0):
        # Configure the sprite for reuse
        self.pos.x = x
        self.pos.y = y
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        
        # Ensure image is reloaded/scaled in case it was modified (e.g., alpha)
        self.image = pygame.image.load("assets/spike_trap.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (width, height))
        self.original_image = self.image.copy() # Reset original_image
        self.image.set_alpha(255) # Ensure full opacity
        
        self.start_pos = pygame.math.Vector2(x, y)
        self.end_pos = pygame.math.Vector2(x + movement_range, y) # Horizontal movement
        self.movement_speed = movement_speed
        self.direction = 1 # Reset direction
        
        # Update rect size to match new dimensions
        self.rect.width = width
        self.rect.height = height

    def update(self, dt):
        # Update position based on direction and speed
        self.pos.x += self.movement_speed * self.direction * dt

        # Check for turning points
        if self.direction == 1 and self.pos.x >= self.end_pos.x:
            self.direction = -1
            self.pos.x = self.end_pos.x # Snap to boundary to prevent overshooting
        elif self.direction == -1 and self.pos.x <= self.start_pos.x:
            self.direction = 1
            self.pos.x = self.start_pos.x # Snap to boundary

        self.rect.center = round(self.pos.x), round(self.pos.y)

class Flag(GameSprite):
    def __init__(self, x, y):
        super().__init__(x=x, y=y, width=50, height=80, image_path="assets/flag.png", z_index=5)
        # Redundant initializations removed as GameSprite handles them

# --- 遊戲主類別 ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("方塊跳躍者 (Block Jumper)")
        self.clock = pygame.time.Clock()
        self.font_manager = FontManager()

        self.game_active = False  # Auto-Test Hook: Default to False for menu
        self.current_state = GameState.MENU

        # Load JSON config
        self.config = json.loads(json_data_raw)
        self.game_rules_list = self.config["game_rules"]
        self.entities_config = self.config["entities"]
        
        # Extract specific entity configurations for easier access
        self.player_config_data = self.entities_config[0]["variables"]
        self.spiketrap_config_data = self.entities_config[1]["variables"]
        self.game_world_config = self.entities_config[2]["variables"]

        # Game World Parameters
        self.gravity = self.game_world_config["gravity_acceleration"]
        self.level_width = self.game_world_config["level_width_pixels"]
        self.level_height = self.game_world_config["level_height_pixels"]

        # Initialize common game components
        self.collision_manager = CollisionManager()
        pygame.mouse.set_visible(True) # UI & Display: Cursor visible

        self._init_game_assets()
        self._init_menus()

        self.player = None
        self.platforms = pygame.sprite.Group()
        self.spike_traps = pygame.sprite.Group()
        self.flags = pygame.sprite.Group()
        # self.all_sprites is not strictly needed for update/draw if CameraScrollGroup does both.
        # If specific updates are not done via group.update(), explicit calls are necessary.
        # Here, player.update() and spike_traps.update() are called explicitly.

        self.camera_group = CameraScrollGroup(
            SCREEN_WIDTH, SCREEN_HEIGHT,
            self.level_width,
            self.level_height,
            margin=100,
            bg_image_path="assets/background.png" # Placeholder background image
        )

        # ObjectPool for SpikeTraps
        self.spike_trap_pool = ObjectPool(SpikeTrap, 5) # Initial size, no specific args here

    def _init_game_assets(self):
        # Create dummy assets if not exist
        asset_paths = {
            "assets/player.png": (40, 40),
            "assets/spike_trap.png": (40, 40),
            "assets/platform_placeholder.png": (1, 1), # Dummy, platforms are generated
            "assets/flag.png": (50, 80),
            "assets/background.png": (SCREEN_WIDTH, SCREEN_HEIGHT) # Needs to be larger or tiled
        }
        for path, size in asset_paths.items():
            try:
                with open(path, 'rb') as f: pass
            except FileNotFoundError:
                print(f"Asset not found: {path}. Creating a dummy placeholder.")
                dummy_surface = pygame.Surface(size)
                if "player" in path: dummy_surface.fill(BLUE)
                elif "spike" in path: dummy_surface.fill(RED)
                elif "flag" in path: dummy_surface.fill(GREEN)
                elif "background" in path: dummy_surface.fill((135, 206, 235)) # Sky blue
                else: dummy_surface.fill(GRAY)
                # Create 'assets' directory if it doesn't exist
                import os
                os.makedirs(os.path.dirname(path), exist_ok=True)
                pygame.image.save(dummy_surface, path)

    def _init_menus(self):
        # Main Menu
        main_menu_options = [
            ("開始遊戲", "start"),
            ("遊戲規則", "rules"),
            ("離開遊戲", "exit")
        ]
        self.main_menu = Menu(self.font_manager, "方塊跳躍者", main_menu_options, self._main_menu_callback, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Pause Menu
        pause_menu_options = [
            ("繼續遊戲", "continue"),
            ("重新開始", "restart"),
            ("遊戲規則", "rules"),
            ("返回主選單", "main_menu")
        ]
        self.pause_menu = Menu(self.font_manager, "遊戲暫停", pause_menu_options, self._pause_menu_callback, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Win/Lose Screen
        win_lose_options = [
            ("重新開始", "restart"),
            ("返回主選單", "main_menu")
        ]
        self.win_menu = Menu(self.font_manager, "恭喜！你成功抵達終點！", win_lose_options, self._win_lose_menu_callback, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.lose_menu = Menu(self.font_manager, "遊戲結束！你的方塊碎了！", win_lose_options, self._win_lose_menu_callback, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Rules Screen
        self.rules_screen = RulesScreen(self.font_manager, self.game_rules_list, SCREEN_WIDTH, SCREEN_HEIGHT, self._return_from_rules)
        self.previous_state_before_rules = GameState.MENU # To know where to return to

    def _main_menu_callback(self, action):
        if action == "start":
            self.change_state(GameState.PLAYING)
            self.reset_game()
        elif action == "rules":
            self.previous_state_before_rules = GameState.MENU
            self.change_state(GameState.RULES)
        elif action == "exit":
            self.running = False

    def _pause_menu_callback(self, action):
        if action == "continue":
            self.change_state(GameState.PLAYING)
        elif action == "restart":
            self.change_state(GameState.PLAYING)
            self.reset_game()
        elif action == "rules":
            self.previous_state_before_rules = GameState.PAUSED
            self.change_state(GameState.RULES)
        elif action == "main_menu":
            self.change_state(GameState.MENU)

    def _win_lose_menu_callback(self, action):
        if action == "restart":
            self.change_state(GameState.PLAYING)
            self.reset_game()
        elif action == "main_menu":
            self.change_state(GameState.MENU)

    def _return_from_rules(self):
        self.change_state(self.previous_state_before_rules)

    def change_state(self, new_state, **kwargs):
        # 狀態機安全: 使用 kwargs.setdefault()
        current_state = self.current_state
        if new_state == GameState.PLAYING:
            kwargs.setdefault('message', '遊戲開始！')
        elif new_state == GameState.PAUSED:
            kwargs.setdefault('message', '遊戲已暫停。')
        elif new_state == GameState.WIN:
            kwargs.setdefault('message', '恭喜獲勝！')
        elif new_state == GameState.LOSE:
            kwargs.setdefault('message', '遊戲失敗！')
        elif new_state == GameState.RULES:
            kwargs.setdefault('message', '查看規則。')
        elif new_state == GameState.MENU:
            kwargs.setdefault('message', '返回主選單。')

        print(f"Changing state from {current_state} to {new_state}. Message: {kwargs.get('message')}")
        self.current_state = new_state

    def reset_game(self):
        # Clear all existing sprites
        self.platforms.empty()
        self.spike_traps.empty()
        self.flags.empty()
        self.camera_group.empty() # Also clear camera group as it holds all rendered sprites

        # Release all currently used spike traps back to the pool
        # Iterate over a copy of the group to avoid issues with modification during iteration
        for trap in list(self.spike_traps):
            self.spike_trap_pool.release(trap)
        self.spike_traps.empty() # Ensure group is empty after releasing

        # Create level entities
        self._create_level()

        # Player setup
        player_start_x = 100
        player_start_y = self.level_height - 150 # Start player above the first platform
        
        self.player = Player(player_start_x, player_start_y, self.platforms, self.player_config_data, self.gravity)
        self.camera_group.add(self.player)

        # Add other entities to camera group for rendering
        self.camera_group.add(self.platforms, self.spike_traps, self.flags)

    def _create_level(self):
        level_platforms = [
            (50, self.level_height - 100, 200, 40), # Starting platform
            (300, self.level_height - 200, 150, 40),
            (600, self.level_height - 150, 200, 40),
            (900, self.level_height - 250, 100, 40),
            (1200, self.level_height - 300, 300, 40),
            (1600, self.level_height - 200, 100, 40),
            (1900, self.level_height - 100, 200, 40),
            (2200, self.level_height - 350, 250, 40),
            (2600, self.level_height - 250, 150, 40),
            (3000, self.level_height - 150, 300, 40), # Platform before flag
            (self.level_width - 200, self.level_height - 100, 100, 40) # Small platform for flag
        ]
        for x, y, w, h in level_platforms:
            platform = Platform(x, y, w, h)
            self.platforms.add(platform)

        level_spike_traps = [
            (400, self.level_height - 180, 40, 40, 100), # x, y, w, h, movement_range
            (1000, self.level_height - 230, 40, 40, 150),
            (1700, self.level_height - 200, 40, 40, 200),
            (2300, self.level_height - 330, 40, 40, 100)
        ]
        # For each trap, get from pool and add to group
        trap_speed = self.spiketrap_config_data["movement_speed"] # from JSON
        for x, y, w, h, rng in level_spike_traps:
            spike = self.spike_trap_pool.get(x=x, y=y, width=w, height=h, movement_range=rng, movement_speed=trap_speed)
            self.spike_traps.add(spike)

        # Victory Flag
        flag_x = self.level_width - 100 # Position it slightly left of max width
        flag_y = self.level_height - 180 # Adjust Y to be on the last platform
        flag = Flag(flag_x, flag_y)
        self.flags.add(flag)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.current_state == GameState.MENU:
                self.main_menu.handle_event(event)
            elif self.current_state == GameState.PAUSED:
                self.pause_menu.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.change_state(GameState.PLAYING)
            elif self.current_state == GameState.RULES:
                self.rules_screen.handle_event(event)
            elif self.current_state == GameState.WIN:
                self.win_menu.handle_event(event)
            elif self.current_state == GameState.LOSE:
                self.lose_menu.handle_event(event)
            elif self.current_state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN and (event.key == pygame.K_p or event.key == pygame.K_ESCAPE):
                    self.change_state(GameState.PAUSED)
            
    def update(self, dt):
        if self.current_state == GameState.PLAYING:
            keys = pygame.key.get_pressed()
            self.player.handle_input(keys, dt)
            self.player.update(dt) # Player's internal physics and collision checks

            self.spike_traps.update(dt) # Update spike traps movement

            # Collision detection (player vs. traps, player vs. flag)
            # Player vs SpikeTraps
            if self.player.invincible_timer <= 0: # Only check collision if not invincible
                self.collision_manager.apply_sprite_vs_group(
                    self.player, self.spike_traps, self._on_player_spike_collision
                )

            # Player vs Flag
            self.collision_manager.apply_sprite_vs_group(
                self.player, self.flags, self._on_player_flag_collision
            )

            # Check game over conditions
            if self.player.health <= 0:
                self.change_state(GameState.LOSE)

    def _on_player_spike_collision(self, player, spike):
        player.take_damage(self.spiketrap_config_data["damage_per_hit"])
        # Optionally, knockback player
        if player.facing_right:
            player.velocity.x = -150
        else:
            player.velocity.x = 150
        player.velocity.y = -200 # Upwards knockback

    def _on_player_flag_collision(self, player, flag):
        self.change_state(GameState.WIN)

    def draw(self):
        self.screen.fill(BLACK) # Clear screen

        if self.current_state == GameState.PLAYING:
            self.camera_group.custom_draw(self.screen, self.player)
            self.player.draw_hud(self.screen, self.font_manager)
        elif self.current_state == GameState.MENU:
            self.main_menu.draw(self.screen)
        elif self.current_state == GameState.PAUSED:
            # Draw game state behind menu
            self.camera_group.custom_draw(self.screen, self.player)
            self.player.draw_hud(self.screen, self.font_manager)
            self.pause_menu.draw(self.screen)
        elif self.current_state == GameState.RULES:
            # Draw underlying menu if coming from there, or a basic background
            if self.previous_state_before_rules == GameState.PAUSED:
                self.camera_group.custom_draw(self.screen, self.player)
                self.player.draw_hud(self.screen, self.font_manager)
            self.rules_screen.draw(self.screen)
        elif self.current_state == GameState.WIN:
            self.win_menu.draw(self.screen)
        elif self.current_state == GameState.LOSE:
            self.lose_menu.draw(self.screen)

        pygame.display.flip()

    def run(self):
        self.running = True
        
        # Auto-Test Hook: Skip menu if game_active is True
        if self.game_active:
            print("Auto-test mode: Skipping menu, starting game directly.")
            self.change_state(GameState.PLAYING)
            self.reset_game()
        else:
            self.change_state(GameState.MENU) # Ensure we start in menu if not auto-test

        while self.running:
            raw_dt = self.clock.tick(FPS) / 1000.0 # Delta time in seconds
            dt = min(raw_dt, 0.05) # 強制 dt 最大不超過 0.05 秒 (防止穿牆與瞬移)
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()

# --- JSON 企劃書數據 (嵌入在代碼中以符合輸出要求) ---
json_data_raw = """
{
  "game_name": "方塊跳躍者 (Block Jumper)",
  "technical_architecture": {
    "used_modules": [
      "sprite_manager.py",
      "camera_player_center.py",
      "collision.py"
    ],
    "implementation_details": "遊戲核心使用 sprite_manager.py 作為所有遊戲物件的基底，camera_player_center.py 實現玩家中心視角的平滑捲動與 Y-Sort 渲染，而 collision.py 則用於處理玩家與平台、陷阱、勝利旗幟之間的碰撞偵測與反應。重力、摩擦力及精確的地面檢測邏輯將在玩家物件中自行實作，並透過遊戲狀態機管理主選單、遊戲進行、暫停及結算流程。"
  },
  "game_rules": [
    "玩家操控方塊角色在2D平台世界中左右移動與跳躍。",
    "玩家受重力與摩擦力影響。",
    "躲避移動的尖刺陷阱，碰到會扣血。",
    "利用不同高度的平台前進。",
    "勝利條件：玩家抵達地圖最右邊的旗幟處。",
    "失敗條件：玩家血量歸零。",
    "遊戲中可按 'P' 或 'ESC' 鍵暫停，進入暫停選單。"
  ],
  "entities": [
    {
      "name": "Player",
      "variables": {
        "initial_health": 100,
        "max_horizontal_speed": 400,
        "jump_force": -850,
        "horizontal_acceleration": 300,
        "ground_friction_coefficient": 0.85,
        "air_damping_coefficient": 0.95,
        "jump_buffer_time": 0.1,
        "coyote_time": 0.1
      }
    },
    {
      "name": "SpikeTrap",
      "variables": {
        "movement_speed": 120,
        "damage_per_hit": 20,
        "movement_range_type": "oscillating"
      }
    },
    {
      "name": "GameWorld",
      "variables": {
        "gravity_acceleration": 900,
        "level_width_pixels": 4000,
        "level_height_pixels": 1000
      }
    }
  ]
}
"""

# --- 主程式進入點 ---
if __name__ == '__main__':
    game = Game()
    game.game_active = False # Auto-Test Hook: Explicitly set to False for menu
    game.run()