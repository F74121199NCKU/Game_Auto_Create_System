import pygame
import sys
import random
import math
from collections import deque
from pygame.math import Vector2
import json
import enum
import os # For dummy asset creation

pygame.init() # Initialize Pygame modules globally, including font module

# --- RAG Module 1: object_pool.py ---
class ObjectPool:
    """
    ObjectPool class for managing reusable game objects.
    Reduces the overhead of object creation and destruction.
    """
    def __init__(self, cls, initial_size, *args, **kwargs):
        """
        Initializes the object pool.

        Args:
            cls (type): The class of objects to be pooled.
            initial_size (int): The initial number of objects to create in the pool.
            *args: Positional arguments to pass to the object's constructor.
            **kwargs: Keyword arguments to pass to the object's constructor.
        """
        self.cls = cls
        self.args = args
        self.kwargs = kwargs
        self.pool = deque()
        self._total_objects = 0 # Track total objects created by this pool
        self._active_objects_count = 0 # Track objects currently in use
        self._create_objects(initial_size)
        print(f"ObjectPool for {cls.__name__} initialized with {initial_size} objects.")

    def _create_objects(self, count):
        """Creates new objects and adds them to the pool."""
        for _ in range(count):
            # Pass None as the first argument for the pool reference in __init__
            # This allows the init method of the object to set the actual pool reference.
            obj = self.cls(None, *self.args, **self.kwargs) # Ensure cls.__init__ can take 'None' for pool_ref
            obj.is_active = False # Custom attribute to track activity state
            self.pool.append(obj)
            self._total_objects += 1

    def get(self, *args, **kwargs):
        """
        Retrieves an object from the pool. If the pool is empty, a new object is created.

        Args:
            *args: Positional arguments to pass to the object's init/reset method.
            **kwargs: Keyword arguments to pass to the object's init/reset method.

        Returns:
            object: An active object from the pool.
        """
        if not self.pool:
            # print(f"Pool for {self.cls.__name__} exhausted, creating new object.")
            self._create_objects(1)
            
        obj = self.pool.popleft()
        obj.is_active = True
        self._active_objects_count += 1
        if hasattr(obj, 'init'):
            obj.init(*args, **kwargs)
        return obj

    def release(self, obj):
        """
        Releases an object back into the pool.

        Args:
            obj (object): The object to be released.
        """
        if obj.is_active: # Only release if currently active
            obj.is_active = False
            self._active_objects_count -= 1
            if hasattr(obj, 'reset'): # Optional: reset object state before returning to pool
                obj.reset()
            self.pool.append(obj)
        else:
            print(f"Warning: Attempted to release an inactive object of type {self.cls.__name__}.")

    def count_active(self):
        """Returns the number of objects currently in use (not in the pool)."""
        return self._active_objects_count

    def count_total(self):
        """Returns the total number of objects managed by this pool (active + available)."""
        return self._total_objects

# --- RAG Module 2: sprite_manager.py ---
class GameSprite(pygame.sprite.Sprite):
    """
    Base class for all game sprites, extending Pygame's Sprite.
    Provides common attributes like image, rect, and an 'is_active' flag
    for use with object pools.
    """
    def __init__(self, image, initial_pos=(0, 0)):
        """
        Initializes the GameSprite.

        Args:
            image (pygame.Surface): The surface to use for the sprite.
            initial_pos (tuple): (x, y) initial position for the sprite.
        """
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=initial_pos)
        self.pos = Vector2(initial_pos)  # Use Vector2 for float precision
        self.is_active = True  # Flag for object pool management

    def update(self, dt):
        """
        Abstract update method. Should be overridden by subclasses.
        Args:
            dt (float): Delta time, time elapsed since last frame in seconds.
        """
        pass

    def draw(self, screen):
        """
        Abstract draw method. Can be overridden by subclasses for custom drawing.
        Args:
            screen (pygame.Surface): The surface to draw the sprite on.
        """
        screen.blit(self.image, self.rect)

# --- RAG Module 3: camera_player_center.py ---
class CameraScrollGroup(pygame.sprite.Group):
    """
    A sprite group that implements camera scrolling, keeping a focus sprite (e.g., player)
    centered on the screen. Also supports Y-sorting for depth perception and frustum culling.
    """
    def __init__(self, screen_width, screen_height, focus_sprite, world_size=None, culling_margin=100):
        """
        Initializes the CameraScrollGroup.

        Args:
            screen_width (int): The width of the game screen.
            screen_height (int): The height of the game screen.
            focus_sprite (GameSprite): The sprite that the camera will follow (usually the player).
            world_size (tuple, optional): (width, height) of the total game world.
                                          If None, the world is considered infinite. Defaults to None.
            culling_margin (int): Extra pixel buffer for frustum culling. Sprites outside
                                  this margin will not be drawn.
        """
        super().__init__()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.half_width = screen_width // 2
        self.half_height = screen_height // 2
        self.offset = Vector2(0, 0)
        self.focus_sprite = focus_sprite
        self.world_size = world_size
        self.culling_margin = culling_margin
        
        # Background surface (e.g., ground texture)
        self.ground_surf = pygame.Surface((100, 100))
        self.ground_surf.fill((30, 30, 30)) # Default dark grey
        
        # Initial camera position
        self.offset.x = self.focus_sprite.pos.x - self.half_width
        self.offset.y = self.focus_sprite.pos.y - self.half_height

    def set_ground_texture(self, texture_path):
        """Sets the background ground texture."""
        try:
            self.ground_surf = pygame.image.load(texture_path).convert_alpha()
        except pygame.error:
            print(f"Warning: Could not load ground texture from {texture_path}. Using default.")

    def custom_draw(self, surface):
        """
        Draws sprites with camera offset, Y-sorting, and frustum culling.
        Also draws a pseudo-infinite background.

        Args:
            surface (pygame.Surface): The surface to draw on (usually the main screen).
        """
        # Update camera offset based on focus sprite
        self.offset.x = self.focus_sprite.pos.x - self.half_width
        self.offset.y = self.focus_sprite.pos.y - self.half_height

        # Clamp camera to world boundaries if world_size is defined
        if self.world_size:
            self.offset.x = max(0, min(self.offset.x, self.world_size[0] - self.screen_width))
            self.offset.y = max(0, min(self.offset.y, self.world_size[1] - self.screen_height))

        # --- Draw pseudo-infinite background ---
        tile_width, tile_height = self.ground_surf.get_size()
        
        # Calculate the top-left corner of the visible area in world coordinates
        cam_x, cam_y = self.offset.x, self.offset.y

        # Determine which tile indices are visible
        start_x_tile = int(cam_x / tile_width)
        start_y_tile = int(cam_y / tile_height)
        end_x_tile = int((cam_x + self.screen_width) / tile_width) + 1
        end_y_tile = int((cam_y + self.screen_height) / tile_height) + 1

        for x in range(start_x_tile, end_x_tile):
            for y in range(start_y_tile, end_y_tile):
                # Calculate screen position for each tile
                screen_x = x * tile_width - cam_x
                screen_y = y * tile_height - cam_y
                surface.blit(self.ground_surf, (screen_x, screen_y))

        # --- Draw sprites with Y-sorting and frustum culling ---
        # Sort sprites by their bottom-most point (centery is a good approximation for 2D top-down)
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            # Frustum Culling: Only draw sprites that are within or near the screen view
            if sprite.is_active: # Only draw active sprites
                # Add margin to culling bounds
                cull_left = self.offset.x - self.culling_margin
                cull_right = self.offset.x + self.screen_width + self.culling_margin
                cull_top = self.offset.y - self.culling_margin
                cull_bottom = self.offset.y + self.screen_height + self.culling_margin

                if cull_left <= sprite.rect.right and \
                   cull_right >= sprite.rect.left and \
                   cull_top <= sprite.rect.bottom and \
                   cull_bottom >= sprite.rect.top:
                    # Apply offset to sprite's position
                    surface.blit(sprite.image, sprite.rect.topleft - self.offset)

# --- RAG Module 4: collision.py ---
class CollisionManager:
    """
    Manages collision detection and resolution between sprites and groups.
    Provides methods for common collision patterns.
    """
    def __init__(self):
        pass # No specific initialization needed for this manager itself

    def apply_sprite_vs_group(self, sprite, group, callback=None, dokill=False):
        """
        Checks for collisions between a single sprite and a group of sprites.

        Args:
            sprite (pygame.sprite.Sprite): The single sprite to check.
            group (pygame.sprite.Group): The group of sprites to check against.
            callback (callable, optional): A function to call if a collision occurs.
                                          It should accept (sprite, collided_sprite) as arguments.
            dokill (bool): If True, collided sprites in the group will be removed. Defaults to False.

        Returns:
            list: A list of sprites from the group that collided with the single sprite.
        """
        collided_sprites = pygame.sprite.spritecollide(sprite, group, dokill)
        if callback:
            for collided_sprite in collided_sprites:
                callback(sprite, collided_sprite)
        return collided_sprites

    def apply_group_vs_group(self, group1, group2, callback=None, dokill1=False, dokill2=False):
        """
        Checks for collisions between two groups of sprites.

        Args:
            group1 (pygame.sprite.Group): The first group.
            group2 (pygame.sprite.Group): The second group.
            callback (callable, optional): A function to call if a collision occurs.
                                          It should accept (sprite1, sprite2) as arguments.
            dokill1 (bool): If True, sprites in group1 that collide will be removed. Defaults to False.
            dokill2 (bool): If True, sprites in group2 that collide will be removed. Defaults to False.

        Returns:
            dict: A dictionary mapping sprites from group1 to a list of sprites from group2 that they collided with.
        """
        collided_dict = pygame.sprite.groupcollide(group1, group2, dokill1, dokill2)
        if callback:
            for sprite1, collided_list in collided_dict.items():
                for sprite2 in collided_list:
                    callback(sprite1, sprite2)
        return collided_dict

# --- Game Enums/States ---
class GameState(enum.Enum):
    MAIN_MENU = 1
    RULES = 2
    GAME_RUNNING = 3
    PAUSED = 4
    LEVEL_UP = 5
    GAME_OVER = 6

# --- Utility Functions ---
def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

# --- Constants and Configuration ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)
RED = (200, 0, 0)
GREEN = (0, 200, 0)
BLUE = (0, 0, 200)
YELLOW = (255, 255, 0)
TRANSPARENT_BLACK = (0, 0, 0, 150) # For pause/level-up overlays

# Fonts (CRITICAL: Chinese font)
try:
    # Ensure font module is initialized before matching/loading fonts
    pygame.font.init() 
    FONT_PATH = pygame.font.match_font('microsoftjhenghei') or \
                pygame.font.match_font('simhei') or \
                pygame.font.get_default_font()
    FONT_SM = pygame.font.Font(FONT_PATH, 24)
    FONT_MD = pygame.font.Font(FONT_PATH, 36)
    FONT_LG = pygame.font.Font(FONT_PATH, 48)
    FONT_XL = pygame.font.Font(FONT_PATH, 72)
except Exception as e:
    print(f"Error loading Chinese font: {e}. Falling back to default.")
    FONT_PATH = pygame.font.get_default_font()
    FONT_SM = pygame.font.Font(FONT_PATH, 24)
    FONT_MD = pygame.font.Font(FONT_PATH, 36)
    FONT_LG = pygame.font.Font(FONT_PATH, 48)
    FONT_XL = pygame.font.Font(FONT_PATH, 72)

# --- UI Components ---
class Button:
    def __init__(self, text, x, y, width, height, font, action=None,
                 bg_color=GRAY, hover_color=LIGHT_GRAY, text_color=WHITE):
        self.text = text
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.font = font
        self.action = action
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.current_bg_color = bg_color

    def draw(self, screen):
        self.current_bg_color = self.hover_color if self.rect.collidepoint(pygame.mouse.get_pos()) else self.bg_color
        pygame.draw.rect(screen, self.current_bg_color, self.rect, border_radius=5)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.action:
                    self.action()
                return True
        return False

# --- Game Entities ---
class Player(GameSprite):
    def __init__(self, game_data, initial_pos):
        player_image = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(player_image, BLUE, (16, 16), 16)
        super().__init__(player_image, initial_pos)

        self.data = game_data['entities'][0]['variables']
        self.hp = self.data['initial_hp']
        self.max_hp = self.data['max_hp']
        self.speed = self.data['movement_speed']
        self.exp = self.data['initial_exp']
        self.level = 1
        self.exp_to_level_up = self.data['exp_to_level_up']
        self.exp_level_up_increase_rate = self.data['exp_level_up_increase_rate']
        self.knife_damage = self.data['knife_initial_damage']
        self.knife_attack_interval = self.data['knife_initial_attack_interval'] # seconds per knife
        self.collision_radius = self.data['collision_radius']

        self.velocity = Vector2(0, 0)
        self.last_attack_time = 0.0 # Time when last knife was fired
        self.invincibility_duration = 0.5 # seconds
        self.invincible_timer = 0.0
        self.is_invincible = False
        self.blink_interval = 0.1 # for visual feedback when invincible

    def update(self, dt):
        if self.is_invincible:
            self.invincible_timer -= dt
            if self.invincible_timer <= 0:
                self.is_invincible = False
        
        # Movement
        self.pos += self.velocity * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))

        # Auto-attack
        current_time = pygame.time.get_ticks() / 1000.0
        if current_time - self.last_attack_time >= self.knife_attack_interval:
            self.last_attack_time = current_time
            return True # Signal to fire knife
        return False # No knife fired

    def take_damage(self, amount):
        if not self.is_invincible:
            self.hp = max(0, self.hp - amount)
            self.is_invincible = True
            self.invincible_timer = self.invincibility_duration
            if self.hp <= 0:
                print("Player defeated!")
                return True # Player defeated
        return False

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_to_level_up:
            self.exp -= self.exp_to_level_up # Carry over remaining exp
            self.level_up()
            return True # Signal level up
        return False

    def level_up(self):
        self.level += 1
        self.exp_to_level_up *= (1 + self.exp_level_up_increase_rate)
        self.exp_to_level_up = int(self.exp_to_level_up)
        print(f"Player Leveled Up! New level: {self.level}, Next EXP: {self.exp_to_level_up}")

    def apply_upgrade(self, upgrade_type):
        upgrades = self.data['upgrade_options']
        if upgrade_type == "damage_increase":
            self.knife_damage += upgrades['damage_increase']
            print(f"Upgrade: Knife Damage +{upgrades['damage_increase']} (Current: {self.knife_damage})")
        elif upgrade_type == "attack_speed_interval_decrease":
            self.knife_attack_interval = max(0.1, self.knife_attack_interval - upgrades['attack_speed_interval_decrease'])
            print(f"Upgrade: Attack Interval -{upgrades['attack_speed_interval_decrease']} (Current: {self.knife_attack_interval:.2f})")
        elif upgrade_type == "health_recovery_percentage":
            heal_amount = self.max_hp * upgrades['health_recovery_percentage']
            self.hp = min(self.max_hp, self.hp + heal_amount)
            print(f"Upgrade: Health Recovered +{int(heal_amount)} (Current: {self.hp}/{self.max_hp})")
        
    def draw(self, screen):
        if self.is_invincible and int(pygame.time.get_ticks() / (self.blink_interval * 1000)) % 2 == 0:
            return # Blink effect
        super().draw(screen)

class Knife(GameSprite):
    def __init__(self, knife_pool_placeholder, knives_collision_group_ref, all_updatable_sprites_ref, camera_drawing_group_ref): # CRITICAL: receives pool placeholder and groups
        knife_image = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.rect(knife_image, YELLOW, (0, 0, 16, 16))
        super().__init__(knife_image)
        self.knives_collision_group = knives_collision_group_ref
        self.all_updatable_sprites = all_updatable_sprites_ref
        self.camera_drawing_group = camera_drawing_group_ref
        self.knife_pool = None # Actual pool will be set in init()
        self.speed = 0
        self.damage = 0
        self.direction = Vector2(0, 0)
        self.lifetime = 0
        self.time_alive = 0.0
        self.is_active = False # Initial state for pooled objects

    def init(self, pos, direction, damage, speed, lifetime, knife_pool_ref): # Pool ref passed at activation
        self.pos = Vector2(pos)
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.direction = direction.normalize() if direction.length() > 0 else Vector2(0, -1)
        self.damage = damage
        self.speed = speed
        self.lifetime = lifetime
        self.time_alive = 0.0
        self.knife_pool = knife_pool_ref # Store the actual pool reference
        self.is_active = True
        
        # Add to all relevant groups
        self.knives_collision_group.add(self)
        self.all_updatable_sprites.add(self)
        self.camera_drawing_group.add(self)

    def update(self, dt):
        if not self.is_active:
            return

        self.pos += self.direction * self.speed * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))

        self.time_alive += dt
        if self.time_alive >= self.lifetime:
            self.die()

    def die(self):
        self.is_active = False
        # Remove from all relevant groups
        self.knives_collision_group.remove(self)
        self.all_updatable_sprites.remove(self)
        self.camera_drawing_group.remove(self)
        if self.knife_pool: # Ensure pool reference exists before releasing
            self.knife_pool.release(self)

    def reset(self):
        # Reset state for pooling
        self.speed = 0
        self.damage = 0
        self.direction = Vector2(0, 0)
        self.lifetime = 0
        self.time_alive = 0.0
        self.is_active = False
        self.knife_pool = None # Clear pool reference on reset
        # Ensure object is removed from groups on reset, as a safeguard
        if self in self.knives_collision_group: self.knives_collision_group.remove(self)
        if self in self.all_updatable_sprites: self.all_updatable_sprites.remove(self)
        if self in self.camera_drawing_group: self.camera_drawing_group.remove(self)

class Enemy(GameSprite):
    def __init__(self, enemy_pool_placeholder, enemies_collision_group_ref, all_updatable_sprites_ref, camera_drawing_group_ref): # CRITICAL: receives pool placeholder and groups
        enemy_image = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(enemy_image, RED, (16, 16), 16)
        super().__init__(enemy_image)
        self.enemies_collision_group = enemies_collision_group_ref
        self.all_updatable_sprites = all_updatable_sprites_ref
        self.camera_drawing_group = camera_drawing_group_ref
        self.enemy_pool = None # Actual pool will be set in init()
        self.hp = 0
        self.max_hp = 0
        self.speed = 0
        self.collision_damage = 0
        self.exp_drop = 0
        self.is_active = False # Initial state for pooled objects
        self.player_ref = None # To follow player

    def init(self, pos, hp, speed, collision_damage, exp_drop, player_ref, enemy_pool_ref): # Pool ref passed at activation
        self.pos = Vector2(pos)
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.collision_damage = collision_damage
        self.exp_drop = exp_drop
        self.player_ref = player_ref
        self.enemy_pool = enemy_pool_ref # Store the actual pool reference
        self.is_active = True
        
        # Add to all relevant groups
        self.enemies_collision_group.add(self)
        self.all_updatable_sprites.add(self)
        self.camera_drawing_group.add(self)

    def update(self, dt):
        if not self.is_active or not self.player_ref:
            return

        # Move towards player
        player_pos = self.player_ref.pos
        direction = player_pos - self.pos
        if direction.length() > 0:
            direction.normalize_ip()
            self.pos += direction * self.speed * dt
            self.rect.center = (round(self.pos.x), round(self.pos.y))

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.die()
            return True # Enemy defeated
        return False

    def die(self):
        self.is_active = False
        # Remove from all relevant groups
        self.enemies_collision_group.remove(self)
        self.all_updatable_sprites.remove(self)
        self.camera_drawing_group.remove(self)
        if self.enemy_pool:
            self.enemy_pool.release(self)

    def reset(self):
        # Reset state for pooling
        self.hp = 0
        self.max_hp = 0
        self.speed = 0
        self.collision_damage = 0
        self.exp_drop = 0
        self.is_active = False
        self.player_ref = None
        self.enemy_pool = None
        # Ensure object is removed from groups on reset, as a safeguard
        if self in self.enemies_collision_group: self.enemies_collision_group.remove(self)
        if self in self.all_updatable_sprites: self.all_updatable_sprites.remove(self)
        if self in self.camera_drawing_group: self.camera_drawing_group.remove(self)

class EnemySpawner:
    def __init__(self, game_data, enemy_pool, enemies_collision_group, player_ref):
        self.data = game_data['entities'][2]['variables'] # Assuming Enemy_SmallGrunt is the 3rd entity
        self.enemy_pool = enemy_pool
        self.enemies_collision_group = enemies_collision_group
        self.player_ref = player_ref
        self.spawn_interval = self.data['initial_spawn_frequency']
        self.last_spawn_time = 0.0

        self.active_enemies_count = 0

    def update(self, dt):
        current_time = pygame.time.get_ticks() / 1000.0
        if current_time - self.last_spawn_time >= self.spawn_interval:
            self.last_spawn_time = current_time
            self.spawn_enemy()
    
    def spawn_enemy(self):
        # Spawn enemy outside screen, relative to player
        player_pos = self.player_ref.pos
        
        # Choose a random direction to spawn from (4 quadrants)
        angle = random.uniform(0, 2 * math.pi)
        spawn_distance = max(SCREEN_WIDTH, SCREEN_HEIGHT) / 2 + 100 # At least 100px outside screen
        spawn_offset = Vector2(math.cos(angle), math.sin(angle)) * spawn_distance
        spawn_pos = player_pos + spawn_offset

        enemy = self.enemy_pool.get(
            spawn_pos,
            self.data['hp'],
            self.data['movement_speed'],
            self.data['collision_damage'],
            self.data['exp_drop'],
            self.player_ref,
            enemy_pool_ref=self.enemy_pool # CRITICAL: Pass the pool itself here in `init`
        )
        self.active_enemies_count += 1
        
    def enemy_killed(self):
        self.active_enemies_count = max(0, self.active_enemies_count - 1)

    def reset(self):
        self.last_spawn_time = 0.0
        self.active_enemies_count = 0
        # Ensure all active enemies are released back to pool
        for enemy in list(self.enemies_collision_group.sprites()): # Iterate over copy
            if enemy.is_active:
                enemy.die() # This will release it to pool and remove from group

# --- Game States Handlers (Menus, Game Play) ---
class BaseState:
    def __init__(self, game):
        self.game = game

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_input(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

class MainMenu(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.buttons = []
        self._setup_buttons()

    def _setup_buttons(self):
        self.buttons.clear()
        button_width, button_height = 250, 60
        gap = 20
        start_y = SCREEN_HEIGHT // 2 - (button_height * 3 + gap * 2) // 2

        self.buttons.append(Button("開始遊戲", SCREEN_WIDTH // 2, start_y, button_width, button_height, FONT_MD, self.game.start_game))
        self.buttons.append(Button("規則說明", SCREEN_WIDTH // 2, start_y + button_height + gap, button_width, button_height, FONT_MD, lambda: self.game.change_state(GameState.RULES)))
        self.buttons.append(Button("結束遊戲", SCREEN_WIDTH // 2, start_y + (button_height + gap) * 2, button_width, button_height, FONT_MD, self.game.quit_game))

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw(self, screen):
        screen.fill(BLACK)
        title_surf = FONT_XL.render(self.game.game_name, True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        screen.blit(title_surf, title_rect)

        for button in self.buttons:
            button.draw(screen)

class RulesMenu(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.back_button = Button("返回主選單", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80, 200, 50, FONT_MD, self.go_back)
        self.rules_text = []

    def enter(self, **kwargs):
        # CRITICAL: kwargs.setdefault()
        self.return_state = kwargs.setdefault('return_state', GameState.MAIN_MENU)
        self.rules_text = self.game.game_data['game_rules']
        if self.return_state == GameState.MAIN_MENU:
             self.back_button.text = "返回主選單"
        elif self.return_state == GameState.PAUSED:
             self.back_button.text = "返回暫停選單"

    def go_back(self):
        self.game.change_state(self.return_state)

    def handle_input(self, event):
        self.back_button.handle_event(event)

    def draw(self, screen):
        screen.fill(BLACK)
        title_surf = FONT_LG.render("遊戲規則", True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title_surf, title_rect)

        y_offset = 150
        for line in self.rules_text:
            text_surf = FONT_SM.render(line, True, WHITE)
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            screen.blit(text_surf, text_rect)
            y_offset += 30

        self.back_button.draw(screen)

class GameRunning(BaseState):
    def __init__(self, game):
        super().__init__(game)
        # Game state elements will be managed by Game class, not here.
        # This class primarily handles input and delegates updates/draws.

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.game.change_state(GameState.PAUSED)
        
        # Player movement input
        keys = pygame.key.get_pressed()
        player_speed = self.game.player.speed
        
        move_x = 0
        move_y = 0
        if keys[pygame.K_a]: move_x -= 1
        if keys[pygame.K_d]: move_x += 1
        if keys[pygame.K_w]: move_y -= 1
        if keys[pygame.K_s]: move_y += 1
        
        direction = Vector2(move_x, move_y)
        if direction.length() > 0:
            direction.normalize_ip()
        self.game.player.velocity = direction * player_speed


    def update(self, dt):
        game = self.game
        
        # Update game timer
        game.time_remaining = max(0, game.time_remaining - dt)
        if game.time_remaining <= 0 and game.player.hp > 0:
            game.change_state(GameState.GAME_OVER, victory=True, final_kills=game.kills, final_time=game.total_game_time_limit)
            return

        # Player update and knife firing
        if game.player.update(dt): # Returns True if it's time to fire a knife
            mouse_pos = pygame.mouse.get_pos()
            # Convert mouse pos to world coordinates for knife direction calculation
            world_mouse_pos = Vector2(mouse_pos) + game.camera_drawing_group.offset
            knife_direction = world_mouse_pos - game.player.pos
            
            # Fire knife using object pool
            knife_data = game.game_data['entities'][1]['variables'] # Assuming Knife is the 2nd entity
            new_knife = game.knife_pool.get(
                game.player.pos,
                knife_direction,
                game.player.knife_damage,
                knife_data['flight_speed'],
                knife_data['lifetime'],
                knife_pool_ref=game.knife_pool # CRITICAL: Pass the pool itself here in `init`
            )

        # Enemy spawner update
        game.enemy_spawner.update(dt)

        # Update all active sprites
        for sprite in game.all_updatable_sprites:
            if sprite.is_active:
                sprite.update(dt)

        # Collision detection (using CollisionManager)
        # Player vs Enemy
        game.collision_manager.apply_sprite_vs_group(game.player, game.enemies_collision_group, game.player_hit_enemy_callback)
        # Knife vs Enemy
        game.collision_manager.apply_group_vs_group(game.knives_collision_group, game.enemies_collision_group, game.knife_hit_enemy_callback)

        # Check player death condition
        if game.player.hp <= 0:
            game.change_state(GameState.GAME_OVER, victory=False, final_kills=game.kills, final_time=game.total_game_time_limit - game.time_remaining)
            return

        # Check for player level up
        # This checks if player.exp has reached/exceeded the threshold without adding more exp
        #if game.player.gain_exp(0) == True:
        #    game.change_state(GameState.LEVEL_UP)
        #    return

    def draw(self, screen):
        game = self.game
        game.camera_drawing_group.custom_draw(screen) # Draws background and sprites with offset/Y-sort

        # Draw HUD
        # HP Bar
        hp_bar_width = 200
        hp_bar_height = 20
        hp_ratio = game.player.hp / game.player.max_hp
        pygame.draw.rect(screen, RED, (10, 10, hp_bar_width, hp_bar_height), 2) # Outline
        pygame.draw.rect(screen, RED, (10, 10, hp_bar_width * hp_ratio, hp_bar_height)) # Fill
        hp_text = FONT_SM.render(f"HP: {int(game.player.hp)}/{int(game.player.max_hp)}", True, WHITE)
        screen.blit(hp_text, (10 + hp_bar_width + 10, 10))

        # EXP Bar
        exp_bar_width = 200
        exp_bar_height = 20
        exp_ratio = game.player.exp / game.player.exp_to_level_up
        pygame.draw.rect(screen, BLUE, (10, 40, exp_bar_width, exp_bar_height), 2) # Outline
        pygame.draw.rect(screen, BLUE, (10, 40, exp_bar_width * exp_ratio, exp_bar_height)) # Fill
        exp_text = FONT_SM.render(f"LVL {game.player.level} EXP: {int(game.player.exp)}/{int(game.player.exp_to_level_up)}", True, WHITE)
        screen.blit(exp_text, (10 + exp_bar_width + 10, 40))

        # Survival Timer
        minutes = int(game.time_remaining // 60)
        seconds = int(game.time_remaining % 60)
        timer_text = FONT_MD.render(f"{minutes:02}:{seconds:02}", True, WHITE)
        screen.blit(timer_text, (SCREEN_WIDTH - timer_text.get_width() - 10, 10))
        
        # Kills count
        kills_text = FONT_SM.render(f"擊殺: {game.kills}", True, WHITE)
        screen.blit(kills_text, (SCREEN_WIDTH - kills_text.get_width() - 10, 50))


class PauseMenu(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.buttons = []
        self._setup_buttons()

    def _setup_buttons(self):
        self.buttons.clear()
        button_width, button_height = 250, 60
        gap = 20
        start_y = SCREEN_HEIGHT // 2 - (button_height * 4 + gap * 3) // 2

        self.buttons.append(Button("繼續遊戲", SCREEN_WIDTH // 2, start_y, button_width, button_height, FONT_MD, lambda: self.game.change_state(GameState.GAME_RUNNING)))
        self.buttons.append(Button("重新開始", SCREEN_WIDTH // 2, start_y + button_height + gap, button_width, button_height, FONT_MD, lambda: self.game.start_game(reset=True)))
        self.buttons.append(Button("規則說明", SCREEN_WIDTH // 2, start_y + (button_height + gap) * 2, button_width, button_height, FONT_MD, lambda: self.game.change_state(GameState.RULES, return_state=GameState.PAUSED)))
        self.buttons.append(Button("返回主選單", SCREEN_WIDTH // 2, start_y + (button_height + gap) * 3, button_width, button_height, FONT_MD, lambda: self.game.change_state(GameState.MAIN_MENU)))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.game.change_state(GameState.GAME_RUNNING)
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        # Game logic should be frozen in PAUSED state
        pass

    def draw(self, screen):
        # Draw previous game state (blurred/darkened)
        self.game.state_handlers[GameState.GAME_RUNNING].draw(screen)

        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(TRANSPARENT_BLACK)
        screen.blit(overlay, (0, 0))

        title_surf = FONT_XL.render("遊戲暫停", True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        screen.blit(title_surf, title_rect)

        for button in self.buttons:
            button.draw(screen)

class LevelUpMenu(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.upgrade_buttons = []
        self.player_upgrades_data = self.game.game_data['entities'][0]['variables']['upgrade_options']

    def enter(self, **kwargs):
        self._setup_upgrade_options()

    def _setup_upgrade_options(self):
        self.upgrade_buttons.clear()
        
        available_upgrades = list(self.player_upgrades_data.keys())
        # Randomly pick 3 unique upgrades
        selected_upgrades = random.sample(available_upgrades, min(3, len(available_upgrades)))

        button_width, button_height = 300, 80
        gap = 30
        start_x = SCREEN_WIDTH // 2 - (button_width * 3 + gap * 2) // 2
        start_y = SCREEN_HEIGHT // 2 + 50

        for i, upgrade_key in enumerate(selected_upgrades):
            text = self._get_upgrade_text(upgrade_key)
            action = lambda key=upgrade_key: self._select_upgrade(key)
            self.upgrade_buttons.append(Button(text, start_x + (button_width + gap) * i + button_width // 2, start_y, button_width, button_height, FONT_MD, action))

    def _get_upgrade_text(self, upgrade_key):
        if upgrade_key == "damage_increase":
            return f"強力飛刀 (+{self.player_upgrades_data[upgrade_key]} 傷害)"
        elif upgrade_key == "attack_speed_interval_decrease":
            return f"極速投擲 (-{self.player_upgrades_data[upgrade_key]:.1f}s 攻擊間隔)"
        elif upgrade_key == "health_recovery_percentage":
            return f"生命恢復 (+{int(self.player_upgrades_data[upgrade_key]*100)}% 生命)"
        return upgrade_key # Fallback

    def _select_upgrade(self, upgrade_key):
        self.game.player.apply_upgrade(upgrade_key)
        self.game.change_state(GameState.GAME_RUNNING)

    def handle_input(self, event):
        for button in self.upgrade_buttons:
            button.handle_event(event)

    def update(self, dt):
        # Game logic should be frozen
        pass

    def draw(self, screen):
        # Draw previous game state (blurred/darkened)
        self.game.state_handlers[GameState.GAME_RUNNING].draw(screen)

        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(TRANSPARENT_BLACK)
        screen.blit(overlay, (0, 0))

        title_surf = FONT_XL.render("選擇升級", True, YELLOW)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        screen.blit(title_surf, title_rect)

        for button in self.upgrade_buttons:
            button.draw(screen)

class GameOverMenu(BaseState):
    def __init__(self, game):
        super().__init__(game)
        self.buttons = []
        self.victory_status = False
        self.final_kills = 0
        self.final_time = 0.0
        self._setup_buttons()

    def _setup_buttons(self):
        self.buttons.clear()
        button_width, button_height = 250, 60
        gap = 20
        start_y = SCREEN_HEIGHT // 2 + 80

        self.buttons.append(Button("重新開始", SCREEN_WIDTH // 2, start_y, button_width, button_height, FONT_MD, lambda: self.game.start_game(reset=True)))
        self.buttons.append(Button("返回主選單", SCREEN_WIDTH // 2, start_y + button_height + gap, button_width, button_height, FONT_MD, lambda: self.game.change_state(GameState.MAIN_MENU)))

    def enter(self, **kwargs):
        # CRITICAL: kwargs.setdefault()
        self.victory_status = kwargs.setdefault('victory', False)
        self.final_kills = kwargs.setdefault('final_kills', 0)
        self.final_time = kwargs.setdefault('final_time', 0.0)
        print(f"Game Over. Victory: {self.victory_status}, Kills: {self.final_kills}, Time: {self.final_time:.2f}s")


    def handle_input(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(BLACK)
        
        status_text = "勝利！" if self.victory_status else "遊戲結束！"
        status_color = GREEN if self.victory_status else RED
        
        title_surf = FONT_XL.render(status_text, True, status_color)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        screen.blit(title_surf, title_rect)

        # Display stats
        stats_y = SCREEN_HEIGHT // 2 - 30
        kills_surf = FONT_MD.render(f"擊殺數: {self.final_kills}", True, WHITE)
        kills_rect = kills_surf.get_rect(center=(SCREEN_WIDTH // 2, stats_y))
        screen.blit(kills_surf, kills_rect)

        time_surf = FONT_MD.render(f"生存時間: {int(self.final_time)} 秒", True, WHITE)
        time_rect = time_surf.get_rect(center=(SCREEN_WIDTH // 2, stats_y + 40))
        screen.blit(time_surf, time_rect)

        for button in self.buttons:
            button.draw(screen)

# --- Game Class ---
class Game:
    def __init__(self, game_data_path="game_plan.json"):
        # pygame.init() # Moved to global scope at the very top
        pygame.display.set_caption("刀鋒生存者 (Blade Survivor)")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_active = False # CRITICAL: Auto-test hook, default to False

        # Load game data from JSON
        with open(game_data_path, 'r', encoding='utf-8') as f:
            self.game_data = json.load(f)
        self.game_name = self.game_data['game_name']
        self.total_game_time_limit = self.game_data['victory_condition']['value']

        # Game state management
        self.current_state = GameState.MAIN_MENU
        self.state_handlers = {
            GameState.MAIN_MENU: MainMenu(self),
            GameState.RULES: RulesMenu(self),
            GameState.GAME_RUNNING: GameRunning(self),
            GameState.PAUSED: PauseMenu(self),
            GameState.LEVEL_UP: LevelUpMenu(self),
            GameState.GAME_OVER: GameOverMenu(self),
        }

        # Game entities and groups (initialized in reset_game)
        self.player = None
        self.knife_pool = None
        self.enemy_pool = None
        self.enemy_spawner = None

        self.knives_collision_group = pygame.sprite.Group() # For collision checks
        self.enemies_collision_group = pygame.sprite.Group() # For collision checks
        self.all_updatable_sprites = pygame.sprite.Group() # All sprites that need update() called
        self.camera_drawing_group = None # Initialized after player is created and is the actual CameraScrollGroup

        self.collision_manager = CollisionManager()

        self.time_remaining = 0.0
        self.kills = 0

    def reset_game(self):
        print("Resetting game...")
        self.knives_collision_group.empty()
        self.enemies_collision_group.empty()
        self.all_updatable_sprites.empty()
        if self.camera_drawing_group: # Clear the camera group if it exists
            self.camera_drawing_group.empty()
        
        # Player setup
        player_data = self.game_data['entities'][0]['variables']
        initial_player_pos = Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.player = Player(self.game_data, initial_player_pos)
        self.all_updatable_sprites.add(self.player)

        # Camera setup (CRITICAL: initial camera)
        self.camera_drawing_group = CameraScrollGroup(SCREEN_WIDTH, SCREEN_HEIGHT, self.player, culling_margin=100)
        self.camera_drawing_group.add(self.player) # Player is drawn by camera

        # Object Pools (CRITICAL: pool and group passed to entities' __init__)
        # Knife needs to know its collision group, updatable group, and camera group
        self.knife_pool = ObjectPool(Knife, 50, 
                                     self.knives_collision_group, 
                                     self.all_updatable_sprites, 
                                     self.camera_drawing_group)
        # Enemy needs to know its collision group, updatable group, and camera group
        self.enemy_pool = ObjectPool(Enemy, 50, 
                                     self.enemies_collision_group, 
                                     self.all_updatable_sprites, 
                                     self.camera_drawing_group)

        self.enemy_spawner = EnemySpawner(self.game_data, self.enemy_pool, self.enemies_collision_group, self.player)

        # Set ground texture (optional, for visual polish)
        ground_tile_path = os.path.join('assets', 'ground_tile.png')
        self.camera_drawing_group.set_ground_texture(ground_tile_path)

        self.time_remaining = self.total_game_time_limit
        self.kills = 0

    def start_game(self, reset=False):
        if reset or self.player is None:
            self.reset_game()
        self.change_state(GameState.GAME_RUNNING)

    def quit_game(self):
        self.running = False

    def change_state(self, new_state, **kwargs):
        # CRITICAL: kwargs.setdefault()
        if hasattr(self.state_handlers.get(self.current_state), 'exit'):
            self.state_handlers[self.current_state].exit()

        prev_state = self.current_state # Store previous state for rules menu return
        self.current_state = new_state
        print(f"Changing state to: {new_state.name} with kwargs: {kwargs}")

        # Set default values for parameters depending on the new state
        if new_state == GameState.GAME_OVER:
            kwargs.setdefault('victory', False)
            kwargs.setdefault('final_kills', self.kills)
            kwargs.setdefault('final_time', self.total_game_time_limit - self.time_remaining)
        elif new_state == GameState.RULES:
            kwargs.setdefault('return_state', prev_state) # Default to previous state if not specified
        
        if hasattr(self.state_handlers.get(new_state), 'enter'):
            self.state_handlers[new_state].enter(**kwargs)

    def player_hit_enemy_callback(self, player, enemy):
        if player.is_active and enemy.is_active: # Only process if both are active
            if player.take_damage(enemy.collision_damage):
                # Player was defeated
                self.change_state(GameState.GAME_OVER, victory=False, final_kills=self.kills, final_time=self.total_game_time_limit - self.time_remaining)
            
    def knife_hit_enemy_callback(self, knife, enemy):
        if knife.is_active and enemy.is_active: # Ensure both are still active before processing
            if enemy.take_damage(knife.damage):
                # Enemy was defeated
                self.kills += 1
                if self.player.gain_exp(enemy.exp_drop):
                    # Player leveled up, state change handled by Player.gain_exp
                    self.change_state(GameState.LEVEL_UP)
                    pass
            knife.die() # Release knife back to pool

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Delegate input handling to current state handler
            self.state_handlers[self.current_state].handle_input(event)
            
    def update(self, dt):
        # Delegate update logic to current state handler
        self.state_handlers[self.current_state].update(dt)

    def draw(self):
        # Delegate drawing logic to current state handler
        self.state_handlers[self.current_state].draw(self.screen)
        pygame.display.flip()

    def run(self):
        # CRITICAL: Auto-test hook
        if self.game_active:
            self.start_game() # Skip main menu and start directly

        while self.running:
            # CRITICAL: Delta Time clamping
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05) # Cap dt at 0.05 seconds (20 FPS minimum effective)

            self.handle_input()
            self.update(dt) # All states have an update method, even if empty to freeze logic.
            self.draw()

        pygame.quit()
        sys.exit()

# --- Main execution block ---
if __name__ == '__main__':
    # Create necessary assets directory if it doesn't exist
    assets_dir = 'assets'
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
    # Create dummy ground tile asset
    ground_tile_path = os.path.join(assets_dir, 'ground_tile.png')
    if not os.path.exists(ground_tile_path):
        print(f"Creating dummy asset: {ground_tile_path}")
        dummy_ground = pygame.Surface((100, 100))
        dummy_ground.fill((50, 50, 50))
        pygame.image.save(dummy_ground, ground_tile_path)

    # Create dummy game_plan.json if it doesn't exist
    game_data_file = 'game_plan.json'
    if os.path.exists(game_data_file): os.remove(game_data_file) # For testing, always recreate
    if not os.path.exists(game_data_file):
        print(f"Creating default game data file: {game_data_file}")
        default_game_data = {
            "game_name": "刀鋒生存者",
            "victory_condition": {
                "type": "survival_time",
                "value": 300
            },
            "game_rules": [
                "目標: 生存並擊敗敵人！",
                "WASD 移動, 滑鼠瞄準，自動攻擊。",
                "升級以強化你的角色。",
                "HP 歸零則遊戲結束。",
                "P/ESC 暫停遊戲。"
            ],
            "entities": [
                {
                    "name": "Player",
                    "variables": {
                        "initial_hp": 100,
                        "max_hp": 100,
                        "movement_speed": 150,
                        "initial_exp": 0,
                        "exp_to_level_up": 100,
                        "exp_level_up_increase_rate": 0.2,
                        "knife_initial_damage": 10,
                        "knife_initial_attack_interval": 1.0,
                        "collision_radius": 16,
                        "upgrade_options": {
                            "damage_increase": 5,
                            "attack_speed_interval_decrease": 0.1,
                            "health_recovery_percentage": 0.25
                        }
                    }
                },
                {
                    "name": "Knife",
                    "variables": {
                        "flight_speed": 400,
                        "lifetime": 2.0
                    }
                },
                {
                    "name": "Enemy_SmallGrunt",
                    "variables": {
                        "initial_spawn_frequency": 2.0,
                        "hp": 20,
                        "movement_speed": 80,
                        "collision_damage": 5,
                        "exp_drop": 20
                    }
                }
            ]
        }
        with open(game_data_file, 'w', encoding='utf-8') as f:
            json.dump(default_game_data, f, indent=4, ensure_ascii=False)
    
    # CRITICAL: `game.game_active = False` explicitly to show menu initially
    game = Game()
    game.game_active = False # Ensures main menu is shown on startup for manual play
    game.run()