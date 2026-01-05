import pygame
import sys
import math
import random
from collections import defaultdict
import os

# --- Pygame Initialization (Moved to Game class where possible) ---
pygame.init()
pygame.mixer.init()

# --- RAG Module Implementations (Integrated into single file) ---

# RAG Module: sprite_manager.py - GameSprite Base Class
class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image, x, y, size=None):
        super().__init__()
        if image:
            self.original_image = image
            if size:
                self.original_image = pygame.transform.scale(self.original_image, size)
            self.image = self.original_image.copy()
            self.rect = self.image.get_rect(center=(x, y))
        else: # For sprites without a visual image, e.g., placeholders or purely logic-based
            self.image = pygame.Surface((1,1), pygame.SRCALPHA)
            self.rect = self.image.get_rect(center=(x,y))

        self.pos = pygame.math.Vector2(x, y)
        self.hitbox = self.rect.copy() # A separate hitbox might be useful for precise collision

    def update(self, dt, *args, **kwargs):
        # Base update method, to be overridden by subclasses
        pass

    def draw(self, surface, camera_offset=(0, 0)):
        # Draw the sprite onto the surface, applying camera offset
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        surface.blit(self.image, draw_pos)

    def rotate_to_direction(self, direction_vector):
        """Rotates the sprite image to face a given direction vector."""
        if direction_vector.length_squared() > 0:
            angle = math.degrees(math.atan2(-direction_vector.y, direction_vector.x))
            self.image = pygame.transform.rotate(self.original_image, angle)
            # Update rect center after rotation, crucial for maintaining position
            self.rect = self.image.get_rect(center=self.pos)


# RAG Module: object_pool.py - ObjectPool Class
class ObjectPool:
    def __init__(self, item_class, initial_size, *args, **kwargs):
        self.item_class = item_class
        self.pool = []
        self.active = []
        self.inactive = []
        self.init_args = args
        self.init_kwargs = kwargs
        self._grow(initial_size)

    def _grow(self, count):
        for _ in range(count):
            item = self.item_class(*self.init_args, **self.init_kwargs)
            item.active = False # Custom attribute to track pool status
            self.pool.append(item)
            self.inactive.append(item)

    def get(self):
        if not self.inactive:
            self._grow(len(self.pool) // 2 + 1) # Grow pool dynamically
            # print(f"Growing pool for {self.item_class.__name__} to {len(self.pool)} items.")

        item = self.inactive.pop(0)
        item.active = True
        self.active.append(item)
        return item

    def release(self, item):
        if item in self.active:
            self.active.remove(item)
            item.active = False
            self.inactive.append(item)
            # Reset item state if necessary, e.g., set invisible or default position
            if hasattr(item, 'reset'):
                item.reset()
        else:
            print(f"Warning: Attempted to release an item not in active list: {item}")

    def get_all_active(self):
        return self.active

    def get_all_inactive(self):
        return self.inactive


# RAG Module: collision.py - CollisionManager
class CollisionManager:
    def __init__(self):
        pass

    def apply_sprite_vs_group(self, sprite, group, kill_sprite_on_hit=False, kill_group_on_hit=False):
        """
        Detects collisions between a single sprite and a group of sprites.
        Returns a list of sprites from the group that collided.
        Optionally kills sprites on collision.
        """
        collided_sprites = pygame.sprite.spritecollide(sprite, group, False, pygame.sprite.collide_rect)
        if collided_sprites:
            if kill_sprite_on_hit:
                sprite.kill()
            for s in collided_sprites:
                if kill_group_on_hit:
                    s.kill()
        return collided_sprites

    def apply_group_vs_group(self, group1, group2, kill1_on_hit=False, kill2_on_hit=False):
        """
        Detects collisions between two groups of sprites.
        Returns a dictionary mapping sprites from group1 to lists of sprites from group2 they collided with.
        Optionally kills sprites on collision.
        """
        collisions = pygame.sprite.groupcollide(group1, group2, kill1_on_hit, kill2_on_hit, pygame.sprite.collide_rect)
        return collisions

# RAG Module: camera_player_center.py - Camera & Y-Sort Group
class Camera(pygame.sprite.Group):
    def __init__(self, width, height, ground_surf):
        super().__init__()
        self.camera_width = width
        self.camera_height = height
        self.camera_rect = pygame.Rect(0, 0, width, height)
        self.offset = pygame.math.Vector2(0, 0)
        self.ground_surf = ground_surf
        self.ground_rect = self.ground_surf.get_rect()

    def update_offset(self, target_pos):
        """
        Updates the camera's offset to center on the target_pos.
        """
        self.offset.x = -(target_pos.x - self.camera_width / 2)
        self.offset.y = -(target_pos.y - self.camera_height / 2)

    def custom_draw(self, surface, debug=False):
        # Draw scrolling background
        surface.blit(self.ground_surf, self.offset)

        # Y-Sort for depth
        sorted_sprites = sorted(self.sprites(), key=lambda sprite: sprite.rect.bottom)

        for sprite in sorted_sprites:
            # Frustum Culling with 100px margin
            draw_rect = sprite.rect.move(self.offset.x, self.offset.y)
            culling_rect = self.camera_rect.inflate(200, 200) # 100px margin on each side (2*100)
            if draw_rect.colliderect(culling_rect):
                sprite.draw(surface, self.offset) # Use sprite's own draw method with offset


# --- UI Elements ---
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color, text_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.action = action
        self.is_hovered = False

    def draw(self, surface):
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, current_color, self.rect, border_radius=5)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.action:
                self.action()
                return True
        return False


# --- Game Entities ---
class Player(GameSprite):
    def __init__(self, x, y, knife_pool, projectiles_group, camera_group, asset_manager):
        player_image = asset_manager.get_image("player.png")
        super().__init__(player_image, x, y, size=(64, 64))

        self.knife_pool = knife_pool
        self.projectiles_group = projectiles_group
        self.camera_group = camera_group # For adding projectiles to camera

        # Player stats from JSON
        self.max_health = 100
        self.health = self.max_health
        self.movement_speed = 200 # pixels/second
        self.attack_interval = 1.0 # seconds between attacks
        self.attack_damage = 10
        self.xp = 0
        self.level = 1
        self.xp_to_next_level_base = 100
        self.xp_to_next_level_growth_rate = 1.2
        self.xp_gem_pickup_range = 50

        self.last_attack_time = pygame.time.get_ticks() / 1000.0
        self.target_direction = pygame.math.Vector2(1, 0) # Default knife direction

        self.current_xp_needed = self.xp_to_next_level_base
        self.kills = 0

        self.invulnerable_timer = 0.0 # For temporary invulnerability after taking damage
        self.invulnerability_duration = 0.5 # seconds

    def update(self, dt, input_state, mouse_pos, screen_center_x, screen_center_y):
        # Handle invulnerability
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
            # Simple blinking effect for invulnerability
            if int(self.invulnerable_timer * 10) % 2 == 0:
                self.image.set_alpha(100) # Partially transparent
            else:
                self.image.set_alpha(255) # Opaque
        else:
            self.image.set_alpha(255)

        # Calculate movement direction
        move_dir = pygame.math.Vector2(0, 0)
        if input_state['up']:
            move_dir.y -= 1
        if input_state['down']:
            move_dir.y += 1
        if input_state['left']:
            move_dir.x -= 1
        if input_state['right']:
            move_dir.x += 1

        if move_dir.length_squared() > 0:
            move_dir.normalize_ip()

        # Apply X movement
        self.pos.x += move_dir.x * self.movement_speed * dt
        self.rect.centerx = round(self.pos.x)

        # Apply Y movement
        self.pos.y += move_dir.y * self.movement_speed * dt
        self.rect.centery = round(self.pos.y)

        # Update hitbox to match rect
        self.hitbox.center = self.rect.center

        # Update target direction based on mouse position
        screen_player_pos = pygame.math.Vector2(screen_center_x, screen_center_y) # Player is always in center of camera view
        self.target_direction = pygame.math.Vector2(mouse_pos) - screen_player_pos
        if self.target_direction.length_squared() > 0:
            self.target_direction.normalize_ip()
            self.rotate_to_direction(self.target_direction)


        # Auto-attack logic
        current_time = pygame.time.get_ticks() / 1000.0
        if current_time - self.last_attack_time >= self.attack_interval:
            self.attack()
            self.last_attack_time = current_time

    def attack(self):
        knife = self.knife_pool.get()
        if knife:
            knife.init_projectile(self.pos.x, self.pos.y, self.target_direction.copy(), self.attack_damage)
            self.projectiles_group.add(knife) # Add to render group
            self.camera_group.add(knife) # Add to camera for rendering

    def take_damage(self, amount):
        if self.invulnerable_timer <= 0:
            self.health -= amount
            if self.health < 0:
                self.health = 0
            self.invulnerable_timer = self.invulnerability_duration
            return True # Damage taken
        return False # Invulnerable

    def gain_xp(self, amount):
        self.xp += amount
        if self.xp >= self.current_xp_needed:
            # Signal for level up
            return True
        return False

    def level_up(self):
        self.level += 1
        self.xp -= self.current_xp_needed # Deduct remaining XP
        self.current_xp_needed = round(self.xp_to_next_level_base * (self.xp_to_next_level_growth_rate ** (self.level - 1)))
        if self.xp < 0: # In case growth rate makes it less than 0 after deduction
            self.xp = 0
        # print(f"Player Leveled Up to Lv.{self.level}! Next XP needed: {self.current_xp_needed}")

    def apply_upgrade(self, upgrade_name):
        if upgrade_name == "Increase_Attack_Speed":
            self.attack_interval = max(0.1, self.attack_interval - 0.1) # Min attack interval 0.1s
            # print(f"Attack Speed Increased! New interval: {self.attack_interval:.2f}s")
        elif upgrade_name == "Increase_Damage":
            self.attack_damage += 5
            # print(f"Attack Damage Increased! New damage: {self.attack_damage}")
        elif upgrade_name == "Restore_Health":
            self.health = min(self.max_health, self.health + 20)
            # print(f"Health Restored! Current health: {self.health}")
        elif upgrade_name == "Increase_Max_Health": # Example of future expansion
            self.max_health += 20
            self.health = min(self.max_health, self.health + 20) # Also heal a bit
            # print(f"Max Health Increased! New Max HP: {self.max_health}")
        elif upgrade_name == "Increase_Movement_Speed": # Example of future expansion
            self.movement_speed += 20
            # print(f"Movement Speed Increased! New Speed: {self.movement_speed}")

class Enemy(GameSprite):
    def __init__(self, x, y, player_ref, asset_manager):
        enemy_image = asset_manager.get_image("enemy.png")
        super().__init__(enemy_image, x, y, size=(48, 48))
        self.player_ref = player_ref # Reference to the player object

        self.health = 30
        self.movement_speed = 80 # pixels/second
        self.attack_damage_on_contact = 5
        self.xp_drop_value = 20

        self.last_attack_time = pygame.time.get_ticks() / 1000.0
        self.attack_cooldown = 0.5 # Cooldown for contact damage

    def update(self, dt):
        if not self.player_ref:
            return

        # FSM: CHASING state
        direction_to_player = self.player_ref.pos - self.pos
        if direction_to_player.length_squared() > 0:
            direction_to_player.normalize_ip()
            self.pos += direction_to_player * self.movement_speed * dt
            self.rotate_to_direction(direction_to_player) # Rotate enemy to face player

        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.hitbox.center = self.rect.center

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.kill() # Remove from all groups
            return True # Enemy defeated
        return False

class Knife(GameSprite):
    def __init__(self, asset_manager): # Asset manager passed to constructor for pooled items
        knife_image = asset_manager.get_image("knife.png")
        # Initialize with placeholder values, will be reset by init_projectile
        super().__init__(knife_image, 0, 0, size=(32, 16))
        self.speed = 500
        self.damage = 0
        self.lifetime_seconds = 1.0
        self.current_lifetime = 0.0
        self.direction = pygame.math.Vector2(0, 0)
        self.active = False # For ObjectPool management

    def init_projectile(self, x, y, direction, damage):
        self.pos.x = x
        self.pos.y = y
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.direction = direction
        self.damage = damage
        self.current_lifetime = self.lifetime_seconds
        self.active = True # Mark as active for pool
        self.rotate_to_direction(self.direction) # Rotate to direction of travel

    def update(self, dt):
        if not self.active:
            return False # Not active, no update needed, don't signal release

        self.pos += self.direction * self.speed * dt
        self.rect.center = round(self.pos.x), round(self.pos.y)
        self.hitbox.center = self.rect.center

        self.current_lifetime -= dt
        if self.current_lifetime <= 0:
            self.kill() # Remove from render group
            # Signal to Game class to release this back to pool
            return True # Indicates it should be released
        return False # Still active

    def reset(self):
        # Reset state for pooling
        self.active = False
        self.kill() # Ensure it's removed from any groups it might be in
        self.pos.x, self.pos.y = 0, 0
        self.rect.center = 0, 0
        self.direction = pygame.math.Vector2(0, 0)
        self.current_lifetime = 0.0


class XPGem(GameSprite):
    def __init__(self, x, y, xp_value, player_ref, asset_manager):
        gem_image = asset_manager.get_image("gem.png")
        super().__init__(gem_image, x, y, size=(24, 24))
        self.xp_value = xp_value
        self.player_ref = player_ref
        self.pickup_range = 30 # Default pickup range for the gem itself (player needs to be within this)
        self.despawn_time_seconds = 5.0
        self.current_lifetime = self.despawn_time_seconds

    def update(self, dt):
        if not self.player_ref:
            return

        # Player auto-pickup logic
        distance_to_player = self.pos.distance_to(self.player_ref.pos)
        if distance_to_player <= self.player_ref.xp_gem_pickup_range: # Use player's pickup range
            # Move towards player if within range (optional, for visual flair)
            move_dir = (self.player_ref.pos - self.pos)
            if move_dir.length_squared() > 0: # Prevent normalization of zero vector
                move_dir.normalize_ip()
            self.pos += move_dir * self.player_ref.movement_speed * 1.5 * dt # Faster than player
            self.rect.center = round(self.pos.x), round(self.pos.y)

        # Despawn logic
        self.current_lifetime -= dt
        if self.current_lifetime <= 0:
            self.kill()


# --- Game State Management ---
class GameState:
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

    def draw(self, surface):
        pass

class MainMenuState(GameState):
    def enter(self, **kwargs):
        self.buttons = []
        center_x = self.game.screen_width // 2
        y_start = self.game.screen_height // 2 - 100
        button_width = 250
        button_height = 60
        spacing = 20

        self.buttons.append(Button(center_x - button_width // 2, y_start, button_width, button_height,
                                   "開始遊戲", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("PLAYING", reset_game=True))) # Added reset_game=True here for fresh start
        self.buttons.append(Button(center_x - button_width // 2, y_start + button_height + spacing, button_width, button_height,
                                   "遊戲規則", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("RULES_SCREEN")))
        self.buttons.append(Button(center_x - button_width // 2, y_start + 2 * (button_height + spacing), button_width, button_height,
                                   "結束遊戲", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   self.game.quit_game))

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(self.game.colors['DARK_GRAY']) # Background color

        title_text = self.game.large_font.render("刀鋒倖存者", True, self.game.colors['YELLOW'])
        title_rect = title_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height // 4))
        surface.blit(title_text, title_rect)

        for button in self.buttons:
            button.draw(surface)

class RulesScreenState(GameState):
    def enter(self, **kwargs):
        self.from_pause = kwargs.setdefault('from_pause', False) # Use setdefault to prevent TypeError
        self.rules_text = [
            "遊戲目標: 在敵人猛攻下存活 60 秒。",
            "",
            "操作方式:",
            "  - 移動: WASD 鍵",
            "  - 瞄準/攻擊: 滑鼠游標 (自動發射飛刀)",
            "  - 暫停/選單: P 鍵 或 ESC 鍵",
            "",
            "遊戲機制:",
            "  - 玩家會自動向滑鼠方向發射飛刀。",
            "  - 敵人從螢幕邊緣生成，追蹤並傷害玩家。",
            "  - 擊敗敵人掉落經驗寶石，拾取可升級。",
            "  - 升級時可選擇強化能力 (攻速, 傷害, 恢復生命等)。",
            "  - 生命值歸零則遊戲失敗。",
            "  - 成功存活 60 秒則遊戲勝利。"
        ]
        button_width = 200
        button_height = 50
        if self.from_pause:
            action = lambda: self.game.state_manager.change_state("PAUSED")
            button_text = "返回暫停選單"
        else:
            action = lambda: self.game.state_manager.change_state("MAIN_MENU")
            button_text = "返回主選單"

        self.back_button = Button(self.game.screen_width // 2 - button_width // 2, self.game.screen_height - 100, button_width, button_height,
                                  button_text, self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                  action)

    def handle_input(self, event):
        self.back_button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(self.game.colors['DARK_GRAY'])
        
        title_text = self.game.medium_font.render("遊戲規則", True, self.game.colors['WHITE'])
        title_rect = title_text.get_rect(center=(self.game.screen_width // 2, 50))
        surface.blit(title_text, title_rect)

        y_offset = 120
        for line in self.rules_text:
            text_surf = self.game.default_font.render(line, True, self.game.colors['LIGHT_GRAY'])
            text_rect = text_surf.get_rect(center=(self.game.screen_width // 2, y_offset))
            surface.blit(text_surf, text_rect)
            y_offset += 30

        self.back_button.draw(surface)


class PlayingState(GameState):
    def enter(self, **kwargs):
        reset_game = kwargs.setdefault('reset_game', False) # Use setdefault
        if reset_game:
            self.game.reset_game()
        # Ensure player input state is clear upon entering playing state if not a fresh game.
        # This is handled by main loop if not in PlayingState.
        # But ensure player exists if reset_game was False (e.g., continue from pause).
        if not self.game.player:
            # Fallback for unexpected scenarios where player might be None without reset_game
            self.game.reset_game()
        # print("Entering PLAYING state.")

    def exit(self):
        # print("Exiting PLAYING state.")
        pass # No specific exit actions needed here.

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.game.state_manager.change_state("PAUSED")
        # Continuous input (pygame.key.get_pressed) moved to update method for consistency

    def update(self, dt):
        # Update player movement input state using continuous key presses
        keys = pygame.key.get_pressed()
        self.game.player_input_state['up'] = keys[pygame.K_w]
        self.game.player_input_state['down'] = keys[pygame.K_s]
        self.game.player_input_state['left'] = keys[pygame.K_a]
        self.game.player_input_state['right'] = keys[pygame.K_d]

        self.game.game_time_left -= dt
        if self.game.game_time_left <= 0:
            self.game.game_time_left = 0
            self.game.state_manager.change_state("GAME_WIN")
            return

        # Update entities
        self.game.player.update(dt, self.game.player_input_state, pygame.mouse.get_pos(),
                                self.game.screen_width / 2, self.game.screen_height / 2)
        self.game.camera.update_offset(self.game.player.pos)

        # Update projectiles and release to pool if lifetime expires
        # Iterate over a copy to allow modification (release removes from group)
        for knife in list(self.game.projectiles_group):
            if knife.update(dt): # knife.update returns True if it should be released
                self.game.projectile_pool.release(knife)

        self.game.enemy_group.update(dt)
        self.game.xp_gem_group.update(dt)

        # Enemy spawning logic
        self.game.enemy_spawn_timer -= dt
        if self.game.enemy_spawn_timer <= 0:
            self.game.spawn_enemy()
            self.game.enemy_spawn_timer = self.game.current_enemy_spawn_frequency

        # Adjust enemy spawn frequency over time
        self.game.spawn_frequency_reduction_timer += dt
        if self.game.spawn_frequency_reduction_timer >= 10.0:
            self.game.current_enemy_spawn_frequency = max(self.game.min_enemy_spawn_frequency,
                                                           self.game.current_enemy_spawn_frequency - self.game.enemy_spawn_frequency_reduction_per_10_seconds)
            self.game.spawn_frequency_reduction_timer = 0
            # print(f"Enemy spawn freq reduced to {self.game.current_enemy_spawn_frequency:.2f}s")


        # --- Collision Detection ---
        # Player vs Enemy
        collided_enemies = self.game.collision_manager.apply_sprite_vs_group(self.game.player, self.game.enemy_group)
        current_time_sec = pygame.time.get_ticks() / 1000.0
        for enemy in collided_enemies:
            if current_time_sec - enemy.last_attack_time >= enemy.attack_cooldown:
                if self.game.player.take_damage(enemy.attack_damage_on_contact):
                    enemy.last_attack_time = current_time_sec # Only reset if damage was actually taken
                # print(f"Player took {enemy.attack_damage_on_contact} damage. HP: {self.game.player.health}")

        # Projectile vs Enemy
        # Note: kill1_on_hit and kill2_on_hit are False here because we manually release projectiles to pool
        # and enemies are killed by their take_damage method.
        projectile_enemy_collisions = self.game.collision_manager.apply_group_vs_group(
            self.game.projectiles_group, self.game.enemy_group, kill1_on_hit=False, kill2_on_hit=False)
        for projectile, enemies in projectile_enemy_collisions.items():
            if projectile.active: # Ensure it's an active pooled projectile
                for enemy in enemies:
                    if enemy.health > 0: # Only hit if enemy is alive
                        if enemy.take_damage(projectile.damage):
                            self.game.player.kills += 1
                            # If enemy is defeated, drop XP gem. Add to xp_gem_group AND camera.
                            gem = XPGem(enemy.pos.x, enemy.pos.y, enemy.xp_drop_value, self.game.player, self.game.asset_manager)
                            self.game.xp_gem_group.add(gem)
                            self.game.camera.add(gem)
                self.game.projectile_pool.release(projectile) # Release projectile after hitting any enemy

        # Player vs XP Gem
        collided_gems = self.game.collision_manager.apply_sprite_vs_group(self.game.player, self.game.xp_gem_group, kill_group_on_hit=True)
        for gem in collided_gems:
            # gem.kill() is already called by apply_sprite_vs_group if kill_group_on_hit=True
            if self.game.player.gain_xp(gem.xp_value):
                self.game.state_manager.change_state("LEVEL_UP_MENU")
                return # Crucial to stop update to prevent further logic while in level up menu

        # Check for game over
        if self.game.player.health <= 0:
            self.game.state_manager.change_state("GAME_OVER")

    def draw(self, surface):
        self.game.camera.custom_draw(surface) # Draw background and sorted sprites

        # Draw HUD
        self._draw_hud(surface)

    def _draw_hud(self, surface):
        player = self.game.player

        # Health Bar (Left Top)
        hp_bar_width = 200
        hp_bar_height = 20
        hp_ratio = player.health / player.max_health
        pygame.draw.rect(surface, self.game.colors['DARK_GRAY'], (10, 10, hp_bar_width, hp_bar_height)) # Background
        pygame.draw.rect(surface, self.game.colors['GREEN'], (10, 10, hp_bar_width * hp_ratio, hp_bar_height)) # Fill
        hp_text = self.game.small_font.render(f"HP: {player.health}/{player.max_health}", True, self.game.colors['WHITE'])
        surface.blit(hp_text, (10, 35))

        # XP Bar (Bottom Center)
        xp_bar_width = 400
        xp_bar_height = 20
        xp_ratio = player.xp / player.current_xp_needed if player.current_xp_needed > 0 else 1.0
        pygame.draw.rect(surface, self.game.colors['DARK_GRAY'], (self.game.screen_width // 2 - xp_bar_width // 2, self.game.screen_height - 30, xp_bar_width, xp_bar_height)) # Background
        pygame.draw.rect(surface, self.game.colors['YELLOW'], (self.game.screen_width // 2 - xp_bar_width // 2, self.game.screen_height - 30, xp_bar_width * xp_ratio, xp_bar_height)) # Fill
        xp_text = self.game.small_font.render(f"EXP: {player.xp}/{player.current_xp_needed} (Lv.{player.level})", True, self.game.colors['WHITE'])
        xp_text_rect = xp_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height - 55))
        surface.blit(xp_text, xp_text_rect)

        # Time Left (Right Top)
        minutes = int(self.game.game_time_left // 60)
        seconds = int(self.game.game_time_left % 60)
        time_text = self.game.default_font.render(f"時間: {minutes:02}:{seconds:02}", True, self.game.colors['WHITE'])
        time_rect = time_text.get_rect(topright=(self.game.screen_width - 10, 10))
        surface.blit(time_text, time_rect)

        # Kills (Right Top, below time)
        kills_text = self.game.default_font.render(f"擊殺: {player.kills}", True, self.game.colors['WHITE'])
        kills_rect = kills_text.get_rect(topright=(self.game.screen_width - 10, 45))
        surface.blit(kills_text, kills_rect)


class PausedState(GameState):
    def enter(self, **kwargs):
        self.buttons = []
        center_x = self.game.screen_width // 2
        y_start = self.game.screen_height // 2 - 100
        button_width = 250
        button_height = 60
        spacing = 20

        self.buttons.append(Button(center_x - button_width // 2, y_start, button_width, button_height,
                                   "繼續遊戲", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("PLAYING")))
        self.buttons.append(Button(center_x - button_width // 2, y_start + button_height + spacing, button_width, button_height,
                                   "重新開始", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("PLAYING", reset_game=True)))
        self.buttons.append(Button(center_x - button_width // 2, y_start + 2 * (button_height + spacing), button_width, button_height,
                                   "遊戲規則", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("RULES_SCREEN", from_pause=True)))
        self.buttons.append(Button(center_x - button_width // 2, y_start + 3 * (button_height + spacing), button_width, button_height,
                                   "離開遊戲", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("MAIN_MENU")))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.game.state_manager.change_state("PLAYING")
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        pass # Game logic is paused

    def draw(self, surface):
        # Draw previous game state (frozen)
        previous_state = self.game.state_manager.get_previous_state()
        if previous_state: # Ensure there was a previous state to draw
            previous_state.draw(surface)

        # Draw overlay
        overlay = pygame.Surface((self.game.screen_width, self.game.screen_height), pygame.SRCALPHA)
        overlay.fill(self.game.colors['TRANSPARENT_BLACK'])
        surface.blit(overlay, (0, 0))

        title_text = self.game.large_font.render("遊戲暫停", True, self.game.colors['WHITE'])
        title_rect = title_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height // 4))
        surface.blit(title_text, title_rect)

        for button in self.buttons:
            button.draw(surface)

class LevelUpState(GameState):
    def enter(self, **kwargs):
        # Ensure player leveled up
        self.game.player.level_up()

        self.buttons = []
        center_y = self.game.screen_height // 2 + 50
        button_width = 300
        button_height = 80
        spacing = 30

        # Randomly select 3 unique upgrade options
        available_upgrades = self.game.upgrade_options.copy()
        random.shuffle(available_upgrades)
        selected_upgrades = random.sample(available_upgrades, min(3, len(available_upgrades)))

        # Define button positions for 3 choices
        x_positions = [self.game.screen_width // 2 - button_width * 1.5 - spacing,
                       self.game.screen_width // 2 - button_width // 2,
                       self.game.screen_width // 2 + button_width // 2 + spacing]

        for i, upgrade_data in enumerate(selected_upgrades):
            btn_text = self._get_upgrade_description(upgrade_data['name'])
            # Using partial function to bind upgrade_data['name'] correctly to lambda
            self.buttons.append(Button(x_positions[i], center_y - button_height // 2, button_width, button_height,
                                       btn_text, self.game.default_font, self.game.colors['BLUE'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                       lambda u=upgrade_data['name']: self._select_upgrade(u)))

    def _get_upgrade_description(self, upgrade_name):
        descriptions = {
            "Increase_Attack_Speed": "攻速提升 (攻擊間隔-0.1s)",
            "Increase_Damage": "傷害提升 (飛刀傷害+5)",
            "Restore_Health": "恢復生命 (恢復20HP)",
            "Increase_Max_Health": "最大生命提升 (+20HP)", # Future expansion
            "Increase_Movement_Speed": "移動速度提升 (+20速度)" # Future expansion
        }
        return descriptions.get(upgrade_name, upgrade_name)

    def _select_upgrade(self, upgrade_name):
        self.game.player.apply_upgrade(upgrade_name)
        self.game.state_manager.change_state("PLAYING")

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        pass # Game logic is paused

    def draw(self, surface):
        # Draw previous game state (frozen)
        previous_state = self.game.state_manager.get_previous_state()
        if previous_state:
            previous_state.draw(surface)

        # Draw overlay
        overlay = pygame.Surface((self.game.screen_width, self.game.screen_height), pygame.SRCALPHA)
        overlay.fill(self.game.colors['TRANSPARENT_BLACK'])
        surface.blit(overlay, (0, 0))

        title_text = self.game.large_font.render("選擇升級", True, self.game.colors['YELLOW'])
        title_rect = title_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height // 4))
        surface.blit(title_text, title_rect)

        for button in self.buttons:
            button.draw(surface)

class GameOverState(GameState):
    def enter(self, **kwargs):
        self.final_kills = self.game.player.kills if self.game.player else 0 # Ensure player exists

        self.buttons = []
        center_x = self.game.screen_width // 2
        y_start = self.game.screen_height // 2 + 50
        button_width = 250
        button_height = 60
        spacing = 20

        self.buttons.append(Button(center_x - button_width // 2, y_start, button_width, button_height,
                                   "重新開始", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("PLAYING", reset_game=True)))
        self.buttons.append(Button(center_x - button_width // 2, y_start + button_height + spacing, button_width, button_height,
                                   "返回主選單", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("MAIN_MENU")))

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(self.game.colors['DARK_GRAY'])

        title_text = self.game.large_font.render("遊戲結束 - 失敗", True, self.game.colors['RED'])
        title_rect = title_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height // 4))
        surface.blit(title_text, title_rect)

        score_text = self.game.medium_font.render(f"總擊殺數: {self.final_kills}", True, self.game.colors['WHITE'])
        score_rect = score_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height // 2 - 30))
        surface.blit(score_text, score_rect)

        for button in self.buttons:
            button.draw(surface)

class GameWinState(GameState):
    def enter(self, **kwargs):
        self.final_kills = self.game.player.kills if self.game.player else 0

        self.buttons = []
        center_x = self.game.screen_width // 2
        y_start = self.game.screen_height // 2 + 50
        button_width = 250
        button_height = 60
        spacing = 20

        self.buttons.append(Button(center_x - button_width // 2, y_start, button_width, button_height,
                                   "重新開始", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("PLAYING", reset_game=True)))
        self.buttons.append(Button(center_x - button_width // 2, y_start + button_height + spacing, button_width, button_height,
                                   "返回主選單", self.game.medium_font, self.game.colors['GRAY'], self.game.colors['LIGHT_GRAY'], self.game.colors['WHITE'],
                                   lambda: self.game.state_manager.change_state("MAIN_MENU")))

    def handle_input(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill(self.game.colors['DARK_GRAY'])

        title_text = self.game.large_font.render("遊戲勝利 - 存活!", True, self.game.colors['GREEN'])
        title_rect = title_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height // 4))
        surface.blit(title_text, title_rect)

        score_text = self.game.medium_font.render(f"總擊殺數: {self.final_kills}", True, self.game.colors['WHITE'])
        score_rect = score_text.get_rect(center=(self.game.screen_width // 2, self.game.screen_height // 2 - 30))
        surface.blit(score_text, score_rect)

        for button in self.buttons:
            button.draw(surface)


class GameStateManager:
    def __init__(self, initial_state_name, states):
        self.states = states
        self.current_state = None
        self.previous_state = None
        self.change_state(initial_state_name)

    def change_state(self, state_name, **kwargs):
        if state_name not in self.states:
            print(f"Error: State '{state_name}' not found.")
            return

        if self.current_state:
            self.current_state.exit()
            # Only store previous state if current state is not a temporary overlay (like pause/level up showing prev screen)
            if not isinstance(self.current_state, (PausedState, LevelUpState)):
                self.previous_state = self.current_state
            # Special case for RulesScreen to remember where it came from
            if state_name == "RULES_SCREEN" and kwargs.get('from_pause', False):
                self.previous_state = self.states["PAUSED"]
            elif state_name == "RULES_SCREEN":
                 self.previous_state = self.states["MAIN_MENU"]

        self.current_state = self.states[state_name]
        # CRITICAL: Use setdefault for kwargs to avoid conflicts with state-specific parameters
        # This ensures internal state params like `from_pause` don't overwrite `reset_game`
        # and allows the state's `enter` method to use `kwargs.setdefault()` safely.
        self.current_state.enter(**kwargs)
        # print(f"Changed state to: {state_name} with kwargs: {kwargs}")

    def get_previous_state(self):
        return self.previous_state

    def handle_input(self, event):
        self.current_state.handle_input(event)

    def update(self, dt):
        self.current_state.update(dt)

    def draw(self, surface):
        self.current_state.draw(surface)


class AssetManager:
    """Manages loading and caching of game assets."""
    def __init__(self, screen_width, screen_height):
        self.images = {}
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._create_placeholder_assets()

    def _create_placeholder_assets(self):
        asset_folder = "assets"
        if not os.path.exists(asset_folder):
            os.makedirs(asset_folder)

        asset_files = {
            "player.png": ((0, 200, 0), (64, 64), 'circle'),  # Green circle
            "enemy.png": ((200, 0, 0), (48, 48), 'circle'),   # Red circle
            "knife.png": ((255, 255, 0), (32, 16), 'rect'),  # Yellow rectangle
            "gem.png": ((0, 0, 200), (24, 24), 'circle'),     # Blue circle
            "ground.png": ((50, 50, 50), (100, 100), 'rect')  # Dark gray rectangle
        }

        for filename, (color, size, shape) in asset_files.items():
            filepath = os.path.join(asset_folder, filename)
            if not os.path.exists(filepath):
                print(f"Warning: Asset '{filename}' not found. Creating placeholder.")
                if shape == 'circle':
                    surf = pygame.Surface(size, pygame.SRCALPHA)
                    pygame.draw.circle(surf, color, (size[0]//2, size[1]//2), min(size)//2)
                else: # 'rect' or default
                    surf = pygame.Surface(size)
                    surf.fill(color)
                pygame.image.save(surf, filepath)

    def get_image(self, filename, size=None):
        filepath = os.path.join("assets", filename)
        if filepath not in self.images:
            try:
                image = pygame.image.load(filepath).convert_alpha()
                if size:
                    image = pygame.transform.scale(image, size)
                self.images[filepath] = image
            except pygame.error:
                print(f"Error loading image: {filepath}. Using placeholder.")
                # Fallback to a simple surface if image cannot be loaded
                # This should ideally not happen if placeholders are created.
                size_fallback = size if size else (50, 50)
                image = pygame.Surface(size_fallback, pygame.SRCALPHA)
                pygame.draw.rect(image, (255, 0, 255), image.get_rect()) # Magenta placeholder
                self.images[filepath] = image
        return self.images[filepath]


# --- Main Game Class ---
class Game:
    def __init__(self):
        # Game Constants (moved from global scope)
        self.screen_width = 1280
        self.screen_height = 720
        self.fps = 60

        self.colors = {
            'WHITE': (255, 255, 255),
            'BLACK': (0, 0, 0),
            'RED': (255, 0, 0),
            'GREEN': (0, 255, 0),
            'BLUE': (0, 0, 255),
            'YELLOW': (255, 255, 0),
            'GRAY': (100, 100, 100),
            'LIGHT_GRAY': (200, 200, 200),
            'DARK_GRAY': (50, 50, 50),
            'ORANGE': (255, 165, 0),
            'TRANSPARENT_BLACK': (0, 0, 0, 150) # For overlay menus
        }

        # Screen setup
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("刀鋒倖存者 (Blade Survivor)")
        self.clock = pygame.time.Clock()
        self.running = True

        # Font Setup (Chinese support)
        font_path = pygame.font.match_font('microsoftjhenghei') or pygame.font.match_font('simhei')
        # Use None as path for default system font if specific Chinese fonts aren't found
        self.default_font = pygame.font.Font(font_path, 24)
        self.large_font = pygame.font.Font(font_path, 48)
        self.medium_font = pygame.font.Font(font_path, 36)
        self.small_font = pygame.font.Font(font_path, 18)

        # CRITICAL HOOK: Auto-test interface
        self.game_active = False # Default to False, menu will show

        # Asset Manager (loads and caches images)
        self.asset_manager = AssetManager(self.screen_width, self.screen_height)

        # RAG Module: Camera (ground_surf for pseudo-infinite background)
        self.ground_surf = self.asset_manager.get_image("ground.png", size=(2000, 2000))
        self.camera = Camera(self.screen_width, self.screen_height, self.ground_surf)

        # RAG Module: CollisionManager
        self.collision_manager = CollisionManager()

        # RAG Module: ObjectPool for Knives
        # Pass asset_manager to Knife's constructor for pooled objects
        self.projectile_pool = ObjectPool(Knife, initial_size=50, asset_manager=self.asset_manager)

        # Sprite Groups (for rendering and collision)
        self.player_group = pygame.sprite.GroupSingle()
        self.enemy_group = pygame.sprite.Group()
        self.projectiles_group = pygame.sprite.Group() # Active projectiles
        self.xp_gem_group = pygame.sprite.Group()

        # Player input state (managed by PlayingState)
        self.player_input_state = {
            'up': False, 'down': False, 'left': False, 'right': False
        }

        # Game State Manager
        self.states = {
            "MAIN_MENU": MainMenuState(self),
            "PLAYING": PlayingState(self),
            "PAUSED": PausedState(self),
            "LEVEL_UP_MENU": LevelUpState(self),
            "GAME_OVER": GameOverState(self),
            "GAME_WIN": GameWinState(self),
            "RULES_SCREEN": RulesScreenState(self)
        }
        self.state_manager = GameStateManager("MAIN_MENU", self.states)

        # Game variables (will be reset by reset_game)
        self.player = None
        self.game_time_left = 60.0
        self.enemy_spawn_timer = 2.0
        self.current_enemy_spawn_frequency = 2.0
        self.min_enemy_spawn_frequency = 0.5
        self.enemy_spawn_frequency_reduction_per_10_seconds = 0.1
        self.spawn_frequency_reduction_timer = 0.0

        self.upgrade_options = [
            {"name": "Increase_Attack_Speed", "effect": "decrease_attack_interval_by_0.1s"},
            {"name": "Increase_Damage", "effect": "increase_knife_damage_by_5"},
            {"name": "Restore_Health", "effect": "restore_20_health_up_to_max"}
            # Add future expansion options based on JSON, if desired
            # {"name": "Increase_Max_Health", "effect": "increase_max_health_by_20"},
            # {"name": "Increase_Movement_Speed", "effect": "increase_movement_speed_by_20"}
        ]

        self.reset_game() # Initial setup of game elements, ensures player is ready for PLAYING state.

    def reset_game(self):
        # Clear all existing sprites from groups
        self.player_group.empty()
        self.enemy_group.empty()
        self.projectiles_group.empty()
        self.xp_gem_group.empty()
        self.camera.empty() # Clear camera's internal group

        # Release all active projectiles back to pool
        for knife in list(self.projectile_pool.get_all_active()):
            self.projectile_pool.release(knife)

        # Re-initialize player
        self.player = Player(0, 0, self.projectile_pool, self.projectiles_group, self.camera, self.asset_manager)
        self.player_group.add(self.player)
        self.camera.add(self.player) # Add player to camera group

        # Reset game variables
        self.game_time_left = 60.0
        self.enemy_spawn_timer = 2.0
        self.current_enemy_spawn_frequency = 2.0
        self.spawn_frequency_reduction_timer = 0.0

        # Reset camera to point at player's initial position
        self.camera.update_offset(self.player.pos)


    def spawn_enemy(self):
        # Determine spawn position outside the screen
        side = random.choice(['top', 'bottom', 'left', 'right'])
        spawn_buffer = 75 # Pixels outside screen edge
        x, y = 0, 0

        # Calculate a point on the screen edge (relative to camera center)
        screen_center_x = self.player.pos.x
        screen_center_y = self.player.pos.y

        if side == 'top':
            x = random.uniform(screen_center_x - self.screen_width/2, screen_center_x + self.screen_width/2)
            y = screen_center_y - self.screen_height/2 - spawn_buffer
        elif side == 'bottom':
            x = random.uniform(screen_center_x - self.screen_width/2, screen_center_x + self.screen_width/2)
            y = screen_center_y + self.screen_height/2 + spawn_buffer
        elif side == 'left':
            x = screen_center_x - self.screen_width/2 - spawn_buffer
            y = random.uniform(screen_center_y - self.screen_height/2, screen_center_y + self.screen_height/2)
        elif side == 'right':
            x = screen_center_x + self.screen_width/2 + spawn_buffer
            y = random.uniform(screen_center_y - self.screen_height/2, screen_center_y + self.screen_height/2)

        enemy = Enemy(x, y, self.player, self.asset_manager)
        self.enemy_group.add(enemy)
        self.camera.add(enemy) # Add enemy to camera for rendering and Y-sorting


    def run(self):
        if self.game_active: # CRITICAL HOOK: Skip main menu if game_active is True
            # print("Auto-starting game (game_active is True).")
            self.state_manager.change_state("PLAYING", reset_game=True)
        else:
            self.state_manager.change_state("MAIN_MENU") # Ensure main menu is explicitly set

        while self.running:
            # CRITICAL: Delta Time Limit
            dt = min(self.clock.tick(self.fps) / 1000.0, 0.05) # Cap dt at 0.05s to prevent physics glitches

            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.state_manager.handle_input(event)
            
            # Update game state
            self.state_manager.update(dt)

            # Drawing
            self.screen.fill(self.colors['BLACK']) # Clear screen for menus
            self.state_manager.draw(self.screen)

            pygame.display.flip()

        self.quit_game()

    def quit_game(self):
        self.running = False


# --- Main execution ---
if __name__ == '__main__':
    game = Game()
    # CRITICAL HOOK: Explicitly set game_active to False to show the main menu
    game.game_active = False 
    game.run()
    pygame.quit()
    sys.exit()