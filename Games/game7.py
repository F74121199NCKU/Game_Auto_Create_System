import pygame
import random
import json
import math
from collections import deque

# --- RAG 模組整合 (嚴格遵守，直接包含) ---

# --- object_pool.py ---
class ObjectPool:
    def __init__(self, item_class, initial_size=10):
        self.item_class = item_class
        self.pool = deque()
        self._create_items(initial_size)
        self.active_items = []

    def _create_items(self, count):
        for _ in range(count):
            self.pool.append(self.item_class())

    def get(self, *args, **kwargs):
        if not self.pool:
            # Optionally, expand the pool if empty
            # print(f"Pool for {self.item_class.__name__} exhausted, expanding...")
            self._create_items(1) # Create one more item
        item = self.pool.popleft()
        item.reset(*args, **kwargs) # Call reset on the item
        self.active_items.append(item)
        return item

    def release(self, item):
        if item in self.active_items:
            self.active_items.remove(item)
            self.pool.append(item)
        else:
            # print(f"Warning: Attempted to release an item not from the active pool: {item}")
            pass # Item was not active, perhaps already released or not from this pool

    def get_active_items(self):
        return list(self.active_items) # Return a copy to prevent modification issues during iteration

    def clear_all(self):
        """Releases all active items back to the pool."""
        for item in list(self.active_items): # Iterate over a copy
            self.release(item)


# --- sprite_manager.py ---
class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image_path=None, size=(32, 32), color=None, initial_pos=(0, 0)):
        super().__init__()
        self.image = None
        self.size = size
        self.color = color
        
        if image_path:
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, size)
            except pygame.error:
                # print(f"Warning: Could not load image from {image_path}. Using fallback color.")
                self.image = self._create_fallback_image(size, color or (255, 0, 255)) # Magenta fallback
        elif color:
            self.image = self._create_fallback_image(size, color)
        else:
            self.image = self._create_fallback_image(size, (255, 0, 255)) # Default magenta

        self.pos = pygame.math.Vector2(initial_pos) # Use Vector2 for float positions
        self.rect = self.image.get_rect(topleft=(int(self.pos.x), int(self.pos.y)))
        self.velocity = pygame.math.Vector2(0, 0)
        self.layer = 0 # For Y-sorting or custom drawing order

    def _create_fallback_image(self, size, color):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(color)
        return surf

    def update(self, dt):
        # Update self.pos using velocity and dt
        self.pos += self.velocity * dt
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))

    def draw(self, surface, offset=(0, 0)):
        # Draw the sprite relative to the camera offset
        surface.blit(self.image, (self.rect.x + offset[0], self.rect.y + offset[1]))

    def set_position(self, x, y):
        self.pos.x = x
        self.pos.y = y
        self.rect.topleft = (int(x), int(y))

    def set_velocity(self, vx, vy):
        self.velocity.x = vx
        self.velocity.y = vy

    def set_layer(self, layer):
        self.layer = layer


# --- collision.py ---
class CollisionManager:
    @staticmethod
    def apply_sprite_vs_group(sprite, group, callback=None, kill_on_collide=False):
        """
        Checks for collisions between a single sprite and a group of sprites.
        Args:
            sprite (pygame.sprite.Sprite): The single sprite to check.
            group (pygame.sprite.Group): The group of sprites to check against.
            callback (callable, optional): A function to call if a collision occurs.
                                            It will receive (sprite, collided_sprite).
            kill_on_collide (bool): If True, the collided sprite will be killed (removed from group).
        Returns:
            list: A list of sprites from the group that collided with the single sprite.
        """
        collided_sprites = pygame.sprite.spritecollide(sprite, group, kill_on_collide)
        if callback:
            for collided in collided_sprites:
                callback(sprite, collided)
        return collided_sprites

    @staticmethod
    def apply_group_vs_group(group1, group2, callback=None, kill_on_collide1=False, kill_on_collide2=False):
        """
        Checks for collisions between two groups of sprites.
        Args:
            group1 (pygame.sprite.Group): The first group of sprites.
            group2 (pygame.sprite.Group): The second group of sprites.
            callback (callable, optional): A function to call if a collision occurs.
                                            It will receive (sprite1, sprite2).
            kill_on_collide1 (bool): If True, sprites from group1 involved in collision will be killed.
            kill_on_collide2 (bool): If True, sprites from group2 involved in collision will be killed.
        Returns:
            dict: A dictionary mapping sprites from group1 to a list of sprites from group2 they collided with.
        """
        collisions = pygame.sprite.groupcollide(group1, group2, kill_on_collide1, kill_on_collide2)
        if callback:
            for sprite1, collided_list in collisions.items():
                for sprite2 in collided_list:
                    callback(sprite1, sprite2)
        return collisions

    @staticmethod
    def check_collision_rect(rect1, rect2):
        """Checks for collision between two pygame.Rect objects."""
        return rect1.colliderect(rect2)

    @staticmethod
    def check_point_in_rect(point, rect):
        """Checks if a point (x, y) is inside a pygame.Rect object."""
        return rect.collidepoint(point)

# --- camera_player_center.py (Adapted for this game) ---
# The CameraScrollGroup will be used to manage sprites and provide sorting,
# but its drawing logic will be heavily customized in GamePlayingState for FoW.
class CameraScrollGroup(pygame.sprite.Group):
    def __init__(self, target_sprite, screen_width, screen_height):
        super().__init__()
        self.target_sprite = target_sprite
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.offset = pygame.math.Vector2(0, 0)
        # Background surface is not used directly for this game's FoW logic,
        # but the variable is kept for compatibility with the original module structure if needed.
        self.ground_surf = pygame.Surface((1,1)) 

    def center_target_camera(self):
        if self.target_sprite:
            # Calculate offset to center the target_sprite
            self.offset.x = self.screen_width / 2 - self.target_sprite.rect.centerx
            self.offset.y = self.screen_height / 2 - self.target_sprite.rect.centery
        return self.offset

    def draw(self, surface, current_fov_map, tile_size):
        # This draw method is heavily customized for FoW and frustum culling
        # It takes fov_map and tile_size to decide what to draw.

        # Calculate camera frustum (visible area + margin for culling)
        margin = 100 # Add 100px margin for frustum culling
        cam_left = -self.offset.x - margin
        cam_top = -self.offset.y - margin
        cam_right = cam_left + self.screen_width + 2 * margin
        cam_bottom = cam_top + self.screen_height + 2 * margin
        
        # Filter sprites that are within the camera frustum and are visible in FoW
        visible_sprites = []
        for sprite in self.sprites():
            # Check if sprite rect (adjusted by offset) is within frustum
            # sprite_screen_rect = sprite.rect.move(self.offset.x, self.offset.y) # Not used, direct rect check is better
            
            if cam_left <= sprite.rect.x + sprite.rect.width and \
               sprite.rect.x <= cam_right and \
               cam_top <= sprite.rect.y + sprite.rect.height and \
               sprite.rect.y <= cam_bottom:

                # Get sprite's grid coordinates
                # Use sprite.pos for float accuracy, then convert to grid int
                grid_x = int(sprite.pos.x + sprite.size[0] / 2) // tile_size
                grid_y = int(sprite.pos.y + sprite.size[1] / 2) // tile_size

                # Check FoW status
                if 0 <= grid_y < len(current_fov_map) and \
                   0 <= grid_x < len(current_fov_map[0]) and \
                   current_fov_map[grid_y][grid_x] == FovState.VISIBLE:
                    visible_sprites.append(sprite)
        
        # Sort visible sprites by their layer (Y-sort for same layer)
        visible_sprites.sort(key=lambda s: (s.layer, s.rect.bottom))

        # Draw the filtered and sorted sprites
        for sprite in visible_sprites:
            sprite.draw(surface, self.offset)


# --- tile_map.py (Renamed internally for clarity and direct inclusion) ---
class MazeManager:
    TILE_WALL = '#'
    TILE_PATH = '.'
    TILE_START = 'S'
    TILE_END = 'E'
    TILE_CHEST = 'C'
    TILE_TRAP = 'T'

    WALL_COLOR = (50, 50, 50)  # Dark grey
    PATH_COLOR = (150, 150, 150) # Light grey
    START_COLOR = (0, 255, 0) # Green
    END_COLOR = (255, 0, 0)   # Red
    CHEST_COLOR = (255, 255, 0) # Yellow
    TRAP_COLOR = (255, 100, 0)  # Orange

    # FoW Colors (Darkened versions)
    EXPLORED_WALL_COLOR = (25, 25, 25)
    EXPLORED_PATH_COLOR = (75, 75, 75)
    EXPLORED_START_COLOR = (0, 128, 0)
    EXPLORED_END_COLOR = (128, 0, 0)
    # Chests/Traps are not drawn as tiles in EXPLORED_INVISIBLE state, so their tile colors are less critical
    # But using explored path color is reasonable.
    EXPLORED_CHEST_COLOR = (128, 128, 0) 
    EXPLORED_TRAP_COLOR = (128, 50, 0)

    UNKNOWN_COLOR = (0, 0, 0) # Black

    def __init__(self, width, height, tile_size):
        if width % 2 == 0: width += 1  # Ensure odd dimensions for DFS
        if height % 2 == 0: height += 1
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.map_data = []
        self.start_pos = (0, 0) # Grid coordinates
        self.end_pos = (0, 0)   # Grid coordinates

    def create_path_dfs(self):
        # Initialize grid with all walls
        self.map_data = [[self.TILE_WALL for _ in range(self.width)] for _ in range(self.height)]

        # Choose a random starting point for DFS (must be odd coordinates)
        start_x = random.randrange(1, self.width, 2)
        start_y = random.randrange(1, self.height, 2)

        stack = [(start_x, start_y)]
        self.map_data[start_y][start_x] = self.TILE_PATH

        while stack:
            cx, cy = stack[-1]
            neighbors = []

            for dx, dy in [(0, 2), (0, -2), (2, 0), (-2, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and self.map_data[ny][nx] == self.TILE_WALL:
                    neighbors.append((nx, ny, cx + dx // 2, cy + dy // 2))

            if neighbors:
                nx, ny, wx, wy = random.choice(neighbors)
                self.map_data[ny][nx] = self.TILE_PATH
                self.map_data[wy][wx] = self.TILE_PATH # Carve path between current and next
                stack.append((nx, ny))
            else:
                stack.pop()
        
        # Place Start and End
        self._place_start_end()
        return self.map_data

    def _place_start_end(self):
        # Find all path tiles
        path_tiles = []
        for y in range(self.height):
            for x in range(self.width):
                if self.map_data[y][x] == self.TILE_PATH:
                    path_tiles.append((x, y))
        
        if not path_tiles:
            # Fallback if no paths found (shouldn't happen with valid DFS)
            # This should ideally not happen but defensively handle.
            # If map_data is all walls, choose default positions
            self.start_pos = (1, 1) if self.width > 2 else (0,0)
            self.end_pos = (self.width - 2, self.height - 2) if self.width > 2 else (0,0)
            if self.height > 2:
                self.end_pos = (self.end_pos[0], self.height - 2)
            else:
                self.end_pos = (self.end_pos[0], 0)

            # Ensure start/end are valid indices
            self.start_pos = (min(self.start_pos[0], self.width-1), min(self.start_pos[1], self.height-1))
            self.end_pos = (min(self.end_pos[0], self.width-1), min(self.end_pos[1], self.height-1))

            self.map_data[self.start_pos[1]][self.start_pos[0]] = self.TILE_START
            self.map_data[self.end_pos[1]][self.end_pos[0]] = self.TILE_END
            return

        # Choose start and end points far apart
        self.start_pos = random.choice(path_tiles)
        path_tiles.remove(self.start_pos)

        # Find the point farthest from start_pos for end_pos
        max_dist = -1
        farthest_pos = self.start_pos # Initialize in case path_tiles is very small after removing start_pos
        for p in path_tiles:
            dist = abs(p[0] - self.start_pos[0]) + abs(p[1] - self.start_pos[1]) # Manhattan distance
            if dist > max_dist:
                max_dist = dist
                farthest_pos = p
        
        # If path_tiles became empty, farthest_pos would still be start_pos, so handle this
        if farthest_pos == self.start_pos and path_tiles:
             self.end_pos = random.choice(path_tiles) # Fallback to any remaining path tile
        else:
             self.end_pos = farthest_pos


        self.map_data[self.start_pos[1]][self.start_pos[0]] = self.TILE_START
        self.map_data[self.end_pos[1]][self.end_pos[0]] = self.TILE_END

    def get_tile_color(self, tile_type, fov_state):
        if fov_state == FovState.UNKNOWN:
            return self.UNKNOWN_COLOR
        elif fov_state == FovState.EXPLORED_INVISIBLE:
            if tile_type == self.TILE_WALL: return self.EXPLORED_WALL_COLOR
            if tile_type == self.TILE_PATH: return self.EXPLORED_PATH_COLOR
            if tile_type == self.TILE_START: return self.EXPLORED_START_COLOR
            if tile_type == self.TILE_END: return self.EXPLORED_END_COLOR
            # Chests/Traps are not drawn as tiles in EXPLORED_INVISIBLE state,
            # so their underlying tile type will just be path_color for map rendering.
            return self.EXPLORED_PATH_COLOR # Fallback for other path-like tiles
        else: # FovState.VISIBLE
            if tile_type == self.TILE_WALL: return self.WALL_COLOR
            if tile_type == self.TILE_PATH: return self.PATH_COLOR
            if tile_type == self.TILE_START: return self.START_COLOR
            if tile_type == self.TILE_END: return self.END_COLOR
            # Chest/Trap tile will be drawn as path_color, then the sprite will be drawn over it.
            return self.PATH_COLOR # Default for visible path-like tiles


# --- 全局常量和設定 ---
FPS = 60
SCREEN_WIDTH, SCREEN_HEIGHT = 400, 300
TILE_SIZE = 32 # Each tile is 32x32 pixels

# FovState Enum (using class for simple constants)
class FovState:
    UNKNOWN = 0         # Completely dark, unexplored
    EXPLORED_INVISIBLE = 1 # Explored, but currently out of player's immediate vision (darkened)
    VISIBLE = 2         # Currently in player's immediate vision (normal brightness)

# Game States Enum
class GameState:
    MAIN_MENU = "MAIN_MENU"
    RULES = "RULES"
    GAME_PLAYING = "GAME_PLAYING"
    PAUSED = "PAUSED"
    WIN = "WIN"
    LOSE = "LOSE"

# --- UI 元素 ---
class Button:
    def __init__(self, rect, text, font, on_click_func, bg_color=(100, 100, 100), text_color=(255, 255, 255), hover_color=(150, 150, 150)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.on_click_func = on_click_func
        self.bg_color = bg_color
        self.text_color = text_color
        self.hover_color = hover_color
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click_func()
                return True
        return False

    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        current_color = self.hover_color if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, current_color, self.rect, border_radius=5)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

class FloatingText:
    def __init__(self, text, pos, font, color, duration=2.0, speed=(0, -20)):
        self.text = text
        self.pos = pygame.math.Vector2(pos)
        self.font = font
        self.color = color
        self.duration = duration
        self.time_elapsed = 0.0
        self.speed = pygame.math.Vector2(speed)

    def update(self, dt):
        self.time_elapsed += dt
        self.pos += self.speed * dt

    def draw(self, surface, offset=(0,0)):
        if self.is_finished():
            return
            
        alpha = max(0, 255 - int(255 * (self.time_elapsed / self.duration)))
        
        # Render text with full opacity (RGB)
        text_surf_full_opacity = self.font.render(self.text, True, self.color)
        
        # Create a new surface with alpha channel for the text and blit the full opacity text onto it
        text_surf_with_alpha = pygame.Surface(text_surf_full_opacity.get_size(), pygame.SRCALPHA)
        text_surf_with_alpha.blit(text_surf_full_opacity, (0, 0))
        text_surf_with_alpha.set_alpha(alpha)

        surface.blit(text_surf_with_alpha, (self.pos.x + offset[0], self.pos.y + offset[1]))

    def is_finished(self):
        return self.time_elapsed >= self.duration

# --- 遊戲實體 ---

class Player(GameSprite):
    def __init__(self, image_path, size, color, initial_pos_grid, tile_size, initial_health, visible_range_tiles):
        pixel_center_x = initial_pos_grid[0] * tile_size + tile_size // 2
        pixel_center_y = initial_pos_grid[1] * tile_size + tile_size // 2
        
        # Calculate topleft for GameSprite to center it in the tile
        initial_pos_topleft = (pixel_center_x - size[0] // 2, pixel_center_y - size[1] // 2)
        
        super().__init__(image_path, size, color, initial_pos_topleft)
        
        self.tile_size = tile_size
        self.current_grid_x, self.current_grid_y = initial_pos_grid
        self.health = initial_health
        self.max_health = initial_health
        self.collected_chests = 0
        self.visible_range_tiles = visible_range_tiles
        self.target_grid_pos = (self.current_grid_x, self.current_grid_y) # For smooth movement transition if needed
        self.last_move_time = pygame.time.get_ticks()
        self.move_cooldown = 200 # milliseconds between moves
        
        # The rect inherited from GameSprite is already set topleft.
        # If we want it centered to pixel_center_x, pixel_center_y, we re-set it here.
        # This is safe as GameSprite's __init__ already handles the Vector2 `self.pos`
        self.rect = self.image.get_rect(centerx=pixel_center_x, centery=pixel_center_y)
        # Ensure self.pos is consistent with the final rect.topleft
        self.pos.x = self.rect.x
        self.pos.y = self.rect.y
        self.velocity = pygame.math.Vector2(0, 0) # Player moves grid-based, velocity is effectively 0

    def reset(self, initial_pos_grid, initial_health, visible_range_tiles):
        self.current_grid_x, self.current_grid_y = initial_pos_grid
        pixel_center_x = initial_pos_grid[0] * self.tile_size + self.tile_size // 2
        pixel_center_y = initial_pos_grid[1] * self.tile_size + self.tile_size // 2
        
        self.set_position(pixel_center_x - self.size[0]//2, pixel_center_y - self.size[1]//2)
        self.rect.center = (pixel_center_x, pixel_center_y) # Re-center the rect
        
        self.health = initial_health
        self.max_health = initial_health # Reset max health too on new game
        self.collected_chests = 0
        self.visible_range_tiles = visible_range_tiles
        self.target_grid_pos = (self.current_grid_x, self.current_grid_y)
        self.velocity = pygame.math.Vector2(0,0)


    def move_grid(self, dx, dy, maze_manager, game_state_callback):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_move_time < self.move_cooldown:
            return False # Cooldown not finished

        target_x, target_y = self.current_grid_x + dx, self.current_grid_y + dy
        
        if 0 <= target_x < maze_manager.width and 0 <= target_y < maze_manager.height:
            target_tile_type = maze_manager.map_data[target_y][target_x]
            if target_tile_type != MazeManager.TILE_WALL:
                # Valid move
                self.current_grid_x = target_x
                self.current_grid_y = target_y
                
                # Update sprite pixel position, centering in the new tile
                new_pixel_center_x = target_x * self.tile_size + self.tile_size // 2
                new_pixel_center_y = target_y * self.tile_size + self.tile_size // 2
                
                self.set_position(new_pixel_center_x - self.size[0]//2, new_pixel_center_y - self.size[1]//2)
                self.rect.center = (new_pixel_center_x, new_pixel_center_y) # Keep rect centered
                self.last_move_time = current_time
                
                game_state_callback("player_moved") # Notify game state
                return True
        return False

    def take_damage(self, amount):
        self.health -= amount
        # print(f"Player took {amount} damage. Health: {self.health}")

    def collect_chest(self, effect_type, effect_value):
        self.collected_chests += 1
        if effect_type == "health_boost":
            self.health = min(self.max_health, self.health + effect_value)
            # print(f"Collected chest! Health +{effect_value}. Current health: {self.health}")
        elif effect_type == "score_boost":
            # print(f"Collected chest! Score +{effect_value}.")
            pass # Score is just chest count for now


class Chest(GameSprite):
    def __init__(self):
        super().__init__(image_path=None, size=(24, 24), color=MazeManager.CHEST_COLOR)
        self.grid_x = 0
        self.grid_y = 0
        self.effect_type = "health_boost"
        self.effect_value = 1
        self.is_active = False # Used by pool to indicate availability

    def reset(self, grid_x, grid_y, tile_size, effect_type, effect_value):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.effect_type = effect_type
        self.effect_value = effect_value
        
        # Center chest sprite within the tile
        pixel_center_x = grid_x * tile_size + tile_size // 2
        pixel_center_y = grid_y * tile_size + tile_size // 2
        
        self.set_position(pixel_center_x - self.size[0] // 2, pixel_center_y - self.size[1] // 2)
        self.rect.center = (pixel_center_x, pixel_center_y) # Update rect to be centered
        self.is_active = True

    def on_collect(self, player):
        if self.is_active:
            player.collect_chest(self.effect_type, self.effect_value)
            self.is_active = False # Deactivate after collection
            return True
        return False


class Trap(GameSprite):
    def __init__(self):
        super().__init__(image_path=None, size=(24, 24), color=MazeManager.TRAP_COLOR)
        self.grid_x = 0
        self.grid_y = 0
        self.damage_value = 1
        self.effect_type = "direct_damage"
        self.is_active = False # Used by pool to indicate availability

    def reset(self, grid_x, grid_y, tile_size, damage_value, effect_type):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.damage_value = damage_value
        self.effect_type = effect_type
        
        # Center trap sprite within the tile
        pixel_center_x = grid_x * tile_size + tile_size // 2
        pixel_center_y = grid_y * tile_size + tile_size // 2
        
        self.set_position(pixel_center_x - self.size[0] // 2, pixel_center_y - self.size[1] // 2)
        self.rect.center = (pixel_center_x, pixel_center_y) # Update rect to be centered
        self.is_active = True

    def on_trigger(self, player):
        if self.is_active:
            if self.effect_type == "direct_damage":
                player.take_damage(self.damage_value)
                self.is_active = False # Deactivate after trigger
                return True
        return False

# --- 有限狀態機 ---
class GameStateBase:
    def __init__(self, game):
        self.game = game

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass

class MainMenuState(GameStateBase):
    def __init__(self, game):
        super().__init__(game)
        self.buttons = []
        self.title_font = self.game.get_font(48)
        self.button_font = self.game.get_font(30)
        self._setup_ui()

    def _setup_ui(self):
        btn_width, btn_height = 200, 50
        center_x, start_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y, btn_width, btn_height), "開始遊戲", self.button_font,
            lambda: self.game.change_state(GameState.GAME_PLAYING, reset=True)))
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y + btn_height + 20, btn_width, btn_height), "規則", self.button_font,
            lambda: self.game.change_state(GameState.RULES)))
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y + 2 * (btn_height + 20), btn_width, btn_height), "離開遊戲", self.button_font,
            self.game.quit_game))

    def enter(self, **kwargs):
        pass

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.update(mouse_pos)

    def draw(self, surface):
        surface.fill((0, 0, 0)) # Black background
        
        title_surf = self.title_font.render("Roguelike 迷宮探險", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        surface.blit(title_surf, title_rect)

        for button in self.buttons:
            button.draw(surface)

class RulesState(GameStateBase):
    def __init__(self, game):
        super().__init__(game)
        self.title_font = self.game.get_font(36)
        self.text_font = self.game.get_font(20)
        self.button_font = self.game.get_font(30)
        self.back_button = None
        self._setup_ui()

    def _setup_ui(self):
        btn_width, btn_height = 200, 50
        center_x, bottom_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT - 70
        self.back_button = Button(
            (center_x - btn_width // 2, bottom_y, btn_width, btn_height), "返回主選單", self.button_font,
            lambda: self.game.change_state(GameState.MAIN_MENU))

    def handle_event(self, event):
        self.back_button.handle_event(event)

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        self.back_button.update(mouse_pos)

    def draw(self, surface):
        surface.fill((0, 0, 0)) # Black background

        title_surf = self.title_font.render("遊戲規則", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 50))
        surface.blit(title_surf, title_rect)

        rules_text = [
            "1. 玩家目標是從迷宮的起點 (綠色方塊) 安全抵達終點 (紅色方塊) 以取得勝利。",
            "2. 每次遊戲啟動時，迷宮會隨機生成，並保證所有路徑都是連通的。",
            "3. 玩家視野受限，僅能看到自身周圍 3 格範圍內的區域 (戰爭迷霧)。",
            "   已探索但不可見的區域會變暗顯示，未探索區域則完全隱藏。",
            "4. 迷宮中隨機分佈寶箱 (黃色方塊)，玩家拾取後可獲得生命恢復或分數增加等增益效果。",
            "5. 迷宮中隨機分佈陷阱 (紅色方塊)，玩家觸發後會受到傷害或負面狀態影響。",
            "6. 玩家生命值歸零時，遊戲失敗。",
            "7. 按下 'P' 或 'ESC' 鍵可暫停遊戲。",
            "8. 移動: W/A/S/D 或 方向鍵。",
        ]

        text_y = 120
        for line in rules_text:
            text_surf = self.text_font.render(line, True, (200, 200, 200))
            text_rect = text_surf.get_rect(centerx=SCREEN_WIDTH // 2, top=text_y)
            surface.blit(text_surf, text_rect)
            text_y += text_rect.height + 10

        self.back_button.draw(surface)

class GamePlayingState(GameStateBase):
    def __init__(self, game):
        super().__init__(game)
        self.maze_manager = None
        self.player = None
        self.chests_pool = ObjectPool(Chest, initial_size=20)
        self.traps_pool = ObjectPool(Trap, initial_size=20)
        self.all_sprites = pygame.sprite.Group() # All sprites for general management
        self.chests_group = pygame.sprite.Group() # For collision detection
        self.traps_group = pygame.sprite.Group()   # For collision detection
        
        # Camera is initialized with a dummy target, will be set correctly after player creation
        self.camera_group = CameraScrollGroup(None, SCREEN_WIDTH, SCREEN_HEIGHT)

        self.fov_map = [] # 2D array for Fog of War state
        # Get player config for visible range, assuming it's the first entity
        self.player_visible_range = game.config['entities'][0]['variables']['visible_range_tiles']
        
        self.floating_texts = []
        self.hud_font = self.game.get_font(24)

    def enter(self, **kwargs):
        reset_game = kwargs.setdefault('reset', False)
        if reset_game:
            self.reset_game()
        
        # Ensure camera target is set if it wasn't already (e.g., first entry)
        if self.player and not self.camera_group.target_sprite:
            self.camera_group.target_sprite = self.player
            self.camera_group.center_target_camera()
        
    def exit(self):
        pass # Nothing special to do on exit for now

    def reset_game(self):
        # Clear existing entities and pools
        self.chests_group.empty()
        self.traps_group.empty()
        self.all_sprites.empty()
        self.chests_pool.clear_all()
        self.traps_pool.clear_all()
        self.floating_texts.clear()
        self.camera_group.empty()

        # 1. Generate Maze
        maze_width = SCREEN_WIDTH // TILE_SIZE * 2 + 1 # Make it big enough, odd number
        maze_height = SCREEN_HEIGHT // TILE_SIZE * 2 + 1
        self.maze_manager = MazeManager(maze_width, maze_height, TILE_SIZE)
        self.maze_manager.create_path_dfs()

        # 2. Create Player
        player_config = self.game.config['entities'][0]['variables']
        player_size = (int(TILE_SIZE * 0.8), int(TILE_SIZE * 0.8))
        player_color = (0, 0, 255) # Blue
        # If player exists from previous game, reset it. Otherwise, create new.
        if self.player:
            self.player.reset(self.maze_manager.start_pos, player_config['initial_health'], player_config['visible_range_tiles'])
            # 【修正這裡】重新開始時，雖然物件還在，但因為上面 empty() 過了，必須重新加入群組！
            self.all_sprites.add(self.player)   # 建議加回 all_sprites
            self.camera_group.add(self.player)  # 必須加回 camera_group 才能被畫出來
        else:
            self.player = Player(player_config['image_path'], player_size, player_color,
                                 self.maze_manager.start_pos, TILE_SIZE,
                                 player_config['initial_health'], player_config['visible_range_tiles'])
            self.all_sprites.add(self.player)
            self.camera_group.add(self.player)
        
        self.camera_group.target_sprite = self.player # Set/Update camera target
        self.camera_group.center_target_camera() # Immediately center camera on player

        # 3. Place Chests and Traps
        self._place_items(self.maze_manager.map_data, self.maze_manager.start_pos, self.maze_manager.end_pos)

        # 4. Initialize Fog of War
        self.fov_map = [[FovState.UNKNOWN for _ in range(self.maze_manager.width)] for _ in range(self.maze_manager.height)]
        self._update_fov() # Initial FoV update

    def _place_items(self, map_data, start_pos, end_pos):
        path_tiles = []
        for y in range(self.maze_manager.height):
            for x in range(self.maze_manager.width):
                if map_data[y][x] == MazeManager.TILE_PATH:
                    if (x, y) != start_pos and (x, y) != end_pos:
                        path_tiles.append((x, y))
        
        random.shuffle(path_tiles)

        # Place Chests
        chest_count = min(10, len(path_tiles) // 5) # Max 10 chests, or 1/5 of paths
        chest_config = self.game.config['entities'][1]['variables']
        for _ in range(chest_count):
            if not path_tiles: break
            cx, cy = path_tiles.pop(0)
            effect_type = random.choice(chest_config['effect_type'])
            chest = self.chests_pool.get(cx, cy, TILE_SIZE, effect_type, chest_config['effect_value'])
            self.all_sprites.add(chest)
            self.chests_group.add(chest)
            self.camera_group.add(chest)

        # Place Traps
        trap_count = min(5, len(path_tiles) // 10) # Max 5 traps, or 1/10 of paths
        trap_config = self.game.config['entities'][2]['variables']
        for _ in range(trap_count):
            if not path_tiles: break
            tx, ty = path_tiles.pop(0)
            effect_type = random.choice(trap_config['effect_type'])
            trap = self.traps_pool.get(tx, ty, TILE_SIZE, trap_config['damage_value'], effect_type)
            self.all_sprites.add(trap)
            self.traps_group.add(trap)
            self.camera_group.add(trap)

    def _update_fov(self):
        # Convert previous VISIBLE areas to EXPLORED_INVISIBLE
        for y in range(self.maze_manager.height):
            for x in range(self.maze_manager.width):
                if self.fov_map[y][x] == FovState.VISIBLE:
                    self.fov_map[y][x] = FovState.EXPLORED_INVISIBLE

        # Set new VISIBLE areas around the player
        px, py = self.player.current_grid_x, self.player.current_grid_y
        fov_range = self.player_visible_range

        for y in range(max(0, py - fov_range), min(self.maze_manager.height, py + fov_range + 1)):
            for x in range(max(0, px - fov_range), min(self.maze_manager.width, px + fov_range + 1)):
                # Simple square FOV for now
                self.fov_map[y][x] = FovState.VISIBLE

    def _player_moved_callback(self, event_type):
        if event_type == "player_moved":
            self._update_fov()
            # Check for win condition
            if (self.player.current_grid_x, self.player.current_grid_y) == self.maze_manager.end_pos:
                self.game.change_state(GameState.WIN, outcome = "WIN")
    
    def _handle_chest_collision(self, player, chest):
        if chest.on_collect(player):
            self.chests_group.remove(chest)
            self.all_sprites.remove(chest)
            self.camera_group.remove(chest) # 【修正 5】從畫面中移除
            self.chests_pool.release(chest)
            self.floating_texts.append(FloatingText(
                "寶箱! HP+1", (player.rect.centerx, player.rect.top - 20), 
                self.game.get_font(20), (0, 255, 0)))

    def _handle_trap_collision(self, player, trap):
        if trap.on_trigger(player):
            self.traps_group.remove(trap)
            self.all_sprites.remove(trap)
            self.camera_group.remove(trap) # 【修正 6】從畫面中移除
            self.traps_pool.release(trap)
            self.floating_texts.append(FloatingText(
                "陷阱! HP-1", (player.rect.centerx, player.rect.top - 20), 
                self.game.get_font(20), (255, 0, 0)))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            dx, dy = 0, 0
            if event.key == pygame.K_w or event.key == pygame.K_UP:
                dy = -1
            elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
                dy = 1
            elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
                dx = -1
            elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                dx = 1
            elif event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.game.change_state(GameState.PAUSED)
                return

            if dx != 0 or dy != 0:
                self.player.move_grid(dx, dy, self.maze_manager, self._player_moved_callback)

    def update(self, dt):
        if not self.player: # Defensive check, should not happen if reset_game is called properly
            return

        self.camera_group.center_target_camera()
        self.player.update(dt) # Player update just handles rect sync, no real velocity movement

        # Handle collisions
        CollisionManager.apply_sprite_vs_group(self.player, self.chests_group, self._handle_chest_collision, kill_on_collide=False)
        CollisionManager.apply_sprite_vs_group(self.player, self.traps_group, self._handle_trap_collision, kill_on_collide=False)

        # Update floating texts
        self.floating_texts = [text for text in self.floating_texts if not text.is_finished()]
        for text in self.floating_texts:
            text.update(dt)

        # Check for game over conditions
        if self.player.health <= 0:
            self.game.change_state(GameState.LOSE)

    def _draw_hud(self, surface):
        # 1. 準備顯示文字
        # 顯示生命值 (紅色)
        hp_text = f"HP: {self.player.health} / {self.player.max_health}"
        hp_surf = self.hud_font.render(hp_text, True, (255, 50, 50)) # 紅色
        
        # 顯示寶箱數 (黃色)
        chest_text = f"Chests: {self.player.collected_chests}"
        chest_surf = self.hud_font.render(chest_text, True, (255, 255, 0)) # 黃色

        # 2. 畫在畫面上 (左上角)
        # HP 畫在 (10, 10)
        surface.blit(hp_surf, (10, 10))
        
        # 寶箱數畫在 HP 下面一點點 (10, 40)
        surface.blit(chest_surf, (10, 40))
    
    def draw(self, surface):
        surface.fill((0, 0, 0)) # Base black background for unknown areas

        if not self.maze_manager: # Defensive check
            return
            
        # Calculate camera frustum for tile culling (with margin)
        margin = 100
        cam_x, cam_y = -self.camera_group.offset.x, -self.camera_group.offset.y
        cam_left_tile = int(max(0, (cam_x - margin) // TILE_SIZE))
        cam_top_tile = int(max(0, (cam_y - margin) // TILE_SIZE))
        cam_right_tile = int(min(self.maze_manager.width, (cam_x + SCREEN_WIDTH + margin) // TILE_SIZE + 1))
        cam_bottom_tile = int(min(self.maze_manager.height, (cam_y + SCREEN_HEIGHT + margin) // TILE_SIZE + 1))

        # Draw map tiles based on FoW and camera offset
        for y in range(cam_top_tile, cam_bottom_tile):
            for x in range(cam_left_tile, cam_right_tile):
                tile_type = self.maze_manager.map_data[y][x]
                fov_state = self.fov_map[y][x]
                
                color = self.maze_manager.get_tile_color(tile_type, fov_state)
                
                # Special handling for start/end if visible or explored
                # These are only tile colors, not sprites
                if tile_type == MazeManager.TILE_START:
                    color = MazeManager.START_COLOR if fov_state == FovState.VISIBLE else MazeManager.EXPLORED_START_COLOR
                elif tile_type == MazeManager.TILE_END:
                    color = MazeManager.END_COLOR if fov_state == FovState.VISIBLE else MazeManager.EXPLORED_END_COLOR

                pygame.draw.rect(surface, color, (x * TILE_SIZE + self.camera_group.offset.x,
                                                  y * TILE_SIZE + self.camera_group.offset.y, # Corrected TILEN_SIZE to TILE_SIZE
                                                  TILE_SIZE, TILE_SIZE))

        # Draw sprites using CameraScrollGroup's draw (which filters by FoV and frustum)
        self.camera_group.draw(surface, self.fov_map, TILE_SIZE)

        # Draw HUD
        if self.player: # Only draw HUD if player exists
            self._draw_hud(surface)

        # Draw floating texts
        for text in self.floating_texts:
            # Floating texts should be drawn relative to game world, so apply camera offset
            text.draw(surface, self.camera_group.offset)

class PauseMenuState(GameStateBase):
    def __init__(self, game):
        super().__init__(game)
        self.buttons = []
        self.title_font = self.game.get_font(48)
        self.button_font = self.game.get_font(30)
        self._setup_ui()

    def _setup_ui(self):
        btn_width, btn_height = 200, 50
        center_x, start_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100
        
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y, btn_width, btn_height), "繼續遊戲", self.button_font,
            lambda: self.game.change_state(GameState.GAME_PLAYING)))
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y + btn_height + 20, btn_width, btn_height), "重新開始", self.button_font,
            lambda: self.game.change_state(GameState.GAME_PLAYING, reset=True))) # Restart immediately to game playing
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y + 2 * (btn_height + 20), btn_width, btn_height), "規則", self.button_font,
            lambda: self.game.change_state(GameState.RULES)))
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y + 3 * (btn_height + 20), btn_width, btn_height), "回主選單", self.button_font,
            lambda: self.game.change_state(GameState.MAIN_MENU)))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_p or event.key == pygame.K_ESCAPE):
            self.game.change_state(GameState.GAME_PLAYING)
            return

        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.update(mouse_pos)

    def draw(self, surface):
        # Draw previous game state dimmed
        # Ensure GamePlayingState exists and has a draw method before attempting to call it.
        if GameState.GAME_PLAYING in self.game.states and self.game.states[GameState.GAME_PLAYING]:
            self.game.states[GameState.GAME_PLAYING].draw(surface)
        
        # Dim overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150)) # Semi-transparent black
        surface.blit(overlay, (0, 0))

        title_surf = self.title_font.render("遊戲暫停", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        surface.blit(title_surf, title_rect)

        for button in self.buttons:
            button.draw(surface)

class GameOverState(GameStateBase):
    def __init__(self, game):
        super().__init__(game)
        self.outcome = "LOSE" # "WIN" or "LOSE"
        self.buttons = []
        self.title_font = self.game.get_font(48)
        self.result_font = self.game.get_font(36)
        self.stats_font = self.game.get_font(24)
        self.button_font = self.game.get_font(30)
        self.collected_chests = 0
        self.player_health = 0
        self._setup_ui()

    def _setup_ui(self):
        btn_width, btn_height = 200, 50
        center_x, start_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100
        
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y, btn_width, btn_height), "重新開始", self.button_font,
            lambda: self.game.change_state(GameState.GAME_PLAYING, reset=True)))
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y + btn_height + 20, btn_width, btn_height), "回主選單", self.button_font,
            lambda: self.game.change_state(GameState.MAIN_MENU)))
        self.buttons.append(Button(
            (center_x - btn_width // 2, start_y + 2 * (btn_height + 20), btn_width, btn_height), "離開遊戲", self.button_font,
            self.game.quit_game))

    def enter(self, **kwargs):
        self.outcome = kwargs.setdefault('outcome', "LOSE")
        # Ensure GamePlayingState and player exist before accessing stats
        game_playing_state = self.game.states.get(GameState.GAME_PLAYING)
        if game_playing_state and game_playing_state.player:
            self.collected_chests = game_playing_state.player.collected_chests
            self.player_health = game_playing_state.player.health
        else:
            self.collected_chests = 0
            self.player_health = 0


    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.update(mouse_pos)

    def draw(self, surface):
        surface.fill((0, 0, 0)) # Black background

        title_text = "恭喜勝利！" if self.outcome == "WIN" else "遊戲失敗！"
        title_color = (0, 255, 0) if self.outcome == "WIN" else (255, 0, 0)
        
        title_surf = self.title_font.render(title_text, True, title_color)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        surface.blit(title_surf, title_rect)

        stats_y = SCREEN_HEIGHT // 2 - 20
        stats_text = f"拾取寶箱數: {self.collected_chests}"
        stats_surf = self.stats_font.render(stats_text, True, (255, 255, 255))
        stats_rect = stats_surf.get_rect(center=(SCREEN_WIDTH // 2, stats_y))
        surface.blit(stats_surf, stats_rect)
        
        if self.outcome == "LOSE":
            hp_text = f"剩餘生命值: {max(0, self.player_health)}"
            hp_surf = self.stats_font.render(hp_text, True, (255, 255, 255))
            hp_rect = hp_surf.get_rect(center=(SCREEN_WIDTH // 2, stats_y + 40))
            surface.blit(hp_surf, hp_rect)

        for button in self.buttons:
            button.draw(surface)

# --- 主遊戲類 ---
class Game:
    def __init__(self, config_json=None): # Fix: Made config_json optional with a default of None
        pygame.init()

        # Fix: Load plan_json if config_json is not provided
        if config_json is None:
            config_json = json.loads(plan_json)

        pygame.display.set_caption(config_json['game_name'])
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_active = False # CRITICAL INSTRUCTION: Auto-test hook

        self.config = config_json

        # CRITICAL INSTRUCTION: Chinese font
        self.font_path = pygame.font.match_font('microsoftjhenghei') or \
                         pygame.font.match_font('simhei') or \
                         pygame.font.get_default_font()
        
        # CRITICAL INSTRUCTION: Mouse visible
        pygame.mouse.set_visible(True)

        self.fonts = {} # Cache fonts by size

        self.states = {}
        self.states[GameState.MAIN_MENU] = MainMenuState(self)
        self.states[GameState.RULES] = RulesState(self)
        self.states[GameState.GAME_PLAYING] = GamePlayingState(self)
        self.states[GameState.PAUSED] = PauseMenuState(self)
        self.states[GameState.WIN] = GameOverState(self)
        self.states[GameState.LOSE] = GameOverState(self)

        self.current_state = None
        self.change_state(GameState.MAIN_MENU) # Initial state

    def get_font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(self.font_path, size)
        return self.fonts[size]

    def change_state(self, new_state_name, **kwargs):
        if self.current_state:
            self.current_state.exit()
        
        self.current_state = self.states[new_state_name]
        # CRITICAL INSTRUCTION: kwargs.setdefault() for state machine safety
        self.current_state.enter(**kwargs) 

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.current_state.handle_event(event)

    def update(self, dt):
        self.current_state.update(dt)

    def draw(self):
        self.current_state.draw(self.screen)
        pygame.display.flip()

    def run(self):
        if self.game_active: # CRITICAL INSTRUCTION: Auto-test hook
            self.change_state(GameState.GAME_PLAYING, reset=True)

        while self.running:
            # CRITICAL INSTRUCTION: Delta Time Limitation
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05) 
            
            self.handle_events()
            self.update(dt)
            self.draw()

    def quit_game(self):
        self.running = False

# --- JSON 企劃書內容 (直接解析) ---
plan_json = """
{
  "game_name": "Roguelike 迷宮探險",
  "technical_architecture": {
    "used_modules": [
      "tile_map.py",
      "sprite_manager.py",
      "collision.py",
      "camera_player_center.py"
    ],
    "implementation_details": "遊戲核心使用 `tile_map.py` 進行迷宮生成與基礎瓦片管理。玩家、寶箱、陷阱等互動實體基於 `sprite_manager.py` 提供的 `GameSprite` 類別建立。實體間的互動與碰撞偵測由 `collision.py` 高效處理。相機系統以 `camera_player_center.py` 為基礎，提供玩家中心視角與精靈 Y-Sort 渲染，但其背景繪製邏輯將客製化以實作戰爭迷霧 (Fog of War) 功能，動態渲染可見與已探索區域的迷宮瓦片。遊戲的整體流程與狀態轉換將透過自定義的有限狀態機 (FSM) 實現，包含主選單、遊戲進行、暫停、規則、勝利及失敗等狀態。"
  },
  "game_rules": [
    "玩家目標是從迷宮的起點 (綠色方塊) 安全抵達終點 (紅色方塊) 以取得勝利。",
    "每次遊戲啟動時，迷宮會隨機生成，並保證所有路徑都是連通的。",
    "玩家視野受限，僅能看到自身周圍 3 格範圍內的區域 (戰爭迷霧)。已探索但不可見的區域會變暗顯示，未探索區域則完全隱藏。",
    "迷宮中隨機分佈寶箱 (黃色方塊)，玩家拾取後可獲得生命恢復或分數增加等增益效果。",
    "迷宮中隨機分佈陷阱 (紅色方塊)，玩家觸發後會受到傷害或負面狀態影響。",
    "玩家生命值歸零時，遊戲失敗。",
    "按下 'P' 或 'ESC' 鍵可暫停遊戲，進入暫停選單，提供繼續、重新開始、規則及離開選項。",
    "遊戲結束 (勝利或失敗) 後，會顯示結算畫面並提供重新開始或離開遊戲的選項。"
  ],
  "entities": [
    {
      "name": "Player",
      "variables": {
        "image_path": null,
        "initial_health": 3,
        "movement_speed_grid": 1,
        "collected_chests": 0,
        "visible_range_tiles": 3,
        "current_grid_x": 0,
        "current_grid_y": 0
      },
      "actions": ["move_grid(dx, dy)", "take_damage(amount)", "collect_chest(type)"]
    },
    {
      "name": "Chest",
      "variables": {
        "image_path": null,
        "grid_x": 0,
        "grid_y": 0,
        "effect_type": ["health_boost", "score_boost"],
        "effect_value": 1
      },
      "actions": ["on_collect(player)"]
    },
    {
      "name": "Trap",
      "variables": {
        "image_path": null,
        "grid_x": 0,
        "grid_y": 0,
        "damage_value": 1,
        "effect_type": ["direct_damage"],
        "is_active": true
      },
      "actions": ["on_trigger(player)"]
    }
  ]
}
"""

if __name__ == '__main__':
    config = json.loads(plan_json)
    game = Game(config)
    game.game_active = False # CRITICAL INSTRUCTION: Explicitly set to False for menu
    game.run()
    pygame.quit()