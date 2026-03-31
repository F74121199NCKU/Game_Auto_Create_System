import pygame
import os
import math
import random
import json
from collections import deque
from typing import Dict, Any, List, Optional, Tuple, Callable

# RAG Module Integration (Strictly Enforced) - START
# object_pool.py
class ObjectPool:
    def __init__(self, item_type: type, initial_size: int = 10):
        self._item_type = item_type
        self._pool = deque()
        self.extend(initial_size)

    def extend(self, count: int):
        for _ in range(count):
            self._pool.append(self._item_type())

    def get(self) -> Any:
        if not self._pool:
            self.extend(1)  # Auto-extend if pool is empty
        item = self._pool.popleft()
        item.reset()  # Call reset method if it exists
        return item

    def release(self, item: Any):
        self._pool.append(item)

# sprite_manager.py
class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image: Optional[pygame.Surface] = None, size: Tuple[int, int] = (32, 32)):
        super().__init__()
        self.image = image
        if self.image is None:
            self.image = pygame.Surface(size, pygame.SRCALPHA)
            self.image.fill((0, 0, 0, 0)) # Transparent by default
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(self.rect.center) # Use Vector2 for float precision
        self.mask = pygame.mask.from_surface(self.image)

    def set_position(self, x: float, y: float):
        self.pos.x = x
        self.pos.y = y
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def move_ip(self, dx: float, dy: float):
        self.pos.x += dx
        self.pos.y += dy
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, self.rect)

    def reset(self):
        self.kill() # Remove from all groups
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA) # Default empty
        self.image.fill((0,0,0,0))
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)


# camera_player_center.py
class CameraScrollGroup(pygame.sprite.Group):
    def __init__(self, world_size: Tuple[int, int], screen_size: Tuple[int, int], margin: int = 100):
        super().__init__()
        self.world_size = world_size
        self.screen_size = screen_size
        self.half_width = screen_size[0] // 2
        self.half_height = screen_size[1] // 2
        self.camera_offset = pygame.math.Vector2(0, 0)
        self.margin = margin # Frustum culling margin

    def set_focus(self, target_rect: pygame.Rect):
        center_x = target_rect.centerx
        center_y = target_rect.centery
        desired_offset_x = center_x - self.half_width
        desired_offset_y = center_y - self.half_height
        self.camera_offset.x = max(0, min(desired_offset_x, self.world_size[0] - self.screen_size[0]))
        self.camera_offset.y = max(0, min(desired_offset_y, self.world_size[1] - self.screen_size[1]))

    def custom_draw(self, surface: pygame.Surface, background_image: pygame.Surface):
        surface.blit(background_image, (-self.camera_offset.x, -self.camera_offset.y))
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.bottom):
            display_rect = sprite.rect.move(-self.camera_offset.x, -self.camera_offset.y)
            if display_rect.right > -self.margin and \
               display_rect.left < self.screen_size[0] + self.margin and \
               display_rect.bottom > -self.margin and \
               display_rect.top < self.screen_size[1] + self.margin:
                surface.blit(sprite.image, display_rect)

# collision.py
class CollisionManager:
    @staticmethod
    def apply_sprite_vs_group(sprite: GameSprite, group: pygame.sprite.Group,
                              kill_target: bool = False, on_collide: Optional[Callable[[GameSprite, GameSprite], None]] = None) -> List[GameSprite]:
        hit_sprites = pygame.sprite.spritecollide(sprite, group, False, pygame.sprite.collide_mask)
        for hit_sprite in hit_sprites:
            if on_collide:
                on_collide(sprite, hit_sprite)
            if kill_target:
                hit_sprite.kill()
        return hit_sprites

    @staticmethod
    def apply_group_vs_group(group1: pygame.sprite.Group, group2: pygame.sprite.Group,
                             kill_group1: bool = False, kill_group2: bool = False,
                             on_collide: Optional[Callable[[GameSprite, GameSprite], None]] = None) -> Dict[GameSprite, List[GameSprite]]:
        collided_pairs = pygame.sprite.groupcollide(group1, group2, False, False, pygame.sprite.collide_mask)
        for sprite1, hit_sprites2 in collided_pairs.items():
            for sprite2 in hit_sprites2:
                if on_collide:
                    on_collide(sprite1, sprite2)
                if kill_group1:
                    sprite1.kill()
                if kill_group2:
                    sprite2.kill()
        return collided_pairs
# RAG Module Integration (Strictly Enforced) - END

# --- Configuration ---
GAME_CONFIG = {
  "game_name": "Pixel Arena Survivor",
  "game_rules": [
    "Control your hero with WASD keys to move.",
    "The hero automatically shoots magical energy balls every 1.5 seconds at the nearest zombie enemy.",
    "Zombies continuously spawn from the screen edges every 2 seconds and move directly towards your hero.",
    "Hitting a zombie with an energy ball destroys it and drops a gold coin worth 10 points.",
    "Colliding with a zombie damages your hero (1 HP loss) and grants 1 second of invulnerability; the zombie involved in the collision is also destroyed.",
    "Collect gold coins to increase your score. Each coin is worth 10 points and disappears after 5 seconds if not collected.",
    "Your hero starts with 3 HP.",
    "The game ends when your hero's HP reaches 0 (Game Over). Aim for the highest score!"
  ],
  "entities": [
    {
      "name": "Player",
      "variables": {
        "max_hp": 3,
        "initial_position": [400, 300],
        "speed_pixels_per_sec": 200,
        "attack_cooldown_sec": 1.5,
        "invulnerability_duration_sec": 1.0,
        "image_asset": "player.png",
        "colorkey": [255, 255, 255]
      }
    },
    {
      "name": "EnergyBall",
      "variables": {
        "speed_pixels_per_sec": 400,
        "damage": 1,
        "lifespan_sec": 2.5,
        "image_asset": "energy_ball.png",
        "colorkey": [255, 255, 255]
      }
    },
    {
      "name": "Zombie",
      "variables": {
        "hp": 1,
        "speed_pixels_per_sec": 100,
        "spawn_interval_sec": 2.0,
        "image_asset": "zombie.png",
        "colorkey": [255, 255, 255]
      }
    },
    {
      "name": "GoldCoin",
      "variables": {
        "score_value": 10,
        "lifespan_sec": 5.0,
        "image_asset": "coin.png",
        "colorkey": [255, 255, 255]
      }
    }
  ],
  "game_states": {
    "main_menu": {
      "title": "Pixel Arena Survivor",
      "buttons": ["START", "RULES", "QUIT"]
    },
    "paused": {
      "overlay_text": "PAUSED",
      "buttons": ["RESUME", "RESTART", "RULES", "EXIT"]
    },
    "game_over": {
      "overlay_text": "GAME OVER",
      "buttons": ["RESTART", "MAIN MENU"]
    }
  },
  "display_settings": {
    "screen_width": 800,
    "screen_height": 600,
    "fps": 60
  },
  "audio_settings": {
    "master_volume": 0.5,
    "music": {
      "main_menu": "main_menu_bgm.ogg",
      "gameplay": "gameplay_bgm.ogg",
      "game_over": "game_over_bgm.ogg"
    },
    "sfx": {
      "player_shoot": "shoot.wav",
      "enemy_hit": "hit.wav",
      "coin_collect": "coin.wav",
      "player_damage": "damage.wav"
    }
  }
}

SCREEN_WIDTH = GAME_CONFIG["display_settings"]["screen_width"]
SCREEN_HEIGHT = GAME_CONFIG["display_settings"]["screen_height"]
FPS = GAME_CONFIG["display_settings"]["fps"]
GAME_TITLE = GAME_CONFIG["game_name"]
WORLD_WIDTH = SCREEN_WIDTH * 2
WORLD_HEIGHT = SCREEN_HEIGHT * 2
WORLD_RECT = pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)

class ResourceManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_resources()
        return cls._instance

    def _init_resources(self):
        self.images = {}
        self.fonts = {}
        font_path = pygame.font.match_font('arial') or pygame.font.get_default_font()
        self.fonts['small'] = pygame.font.Font(font_path, 18)
        self.fonts['medium'] = pygame.font.Font(font_path, 24)
        self.fonts['large'] = pygame.font.Font(font_path, 36)
        self.fonts['title'] = pygame.font.Font(font_path, 48)

    def get_image(self, name: str, size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        if name not in self.images:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, 'assets', name)
            try:
                # Requirement: Use convert_alpha() and set_colorkey((255, 255, 255))
                img = pygame.image.load(path).convert_alpha()
                img.set_colorkey((255, 255, 255))
                self.images[name] = img
            except:
                img = pygame.Surface(size or (32, 32))
                # 如果是背景圖，填滿深灰色；否則填滿紫色
                if "background" in name:
                    img.fill((40, 40, 40)) 
                else:
                    img.fill((255, 0, 255))
                self.images[name] = img
        
        img = self.images[name]
        if size:
            return pygame.transform.scale(img, size)
        return img

    def get_font(self, size_key: str):
        return self.fonts.get(size_key, self.fonts['medium'])

class AudioManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_audio()
        return cls._instance

    def _init_audio(self):
        self.master_volume = GAME_CONFIG["audio_settings"]["master_volume"]
        self.sfx = {}
        for key, filename in GAME_CONFIG["audio_settings"]["sfx"].items():
            try:
                self.sfx[key] = pygame.mixer.Sound(os.path.join('assets', filename))
                self.sfx[key].set_volume(self.master_volume)
            except: pass

    def play_music(self, track_key: str):
        filename = GAME_CONFIG["audio_settings"]["music"].get(track_key)
        if filename:
            try:
                pygame.mixer.music.load(os.path.join('assets', filename))
                pygame.mixer.music.play(-1)
            except: pass

    def stop_music(self): pygame.mixer.music.stop()
    def pause_music(self): pygame.mixer.music.pause()
    def unpause_music(self): pygame.mixer.music.unpause()
    def play_sfx(self, key: str):
        if key in self.sfx: self.sfx[key].play()

class Button(GameSprite):
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font, bg_image: pygame.Surface, action: Callable):
        super().__init__(image=pygame.transform.scale(bg_image, rect.size), size=rect.size)
        self.rect = rect
        self.text = text
        self.font = font
        self.action = action
        self.base_image = self.image.copy()
        self.hover_image = self.image.copy()
        overlay = pygame.Surface(self.hover_image.get_size(), pygame.SRCALPHA)
        overlay.fill((100, 100, 255, 100))
        self.hover_image.blit(overlay, (0, 0))
        self._render_text()

    def _render_text(self):
        txt_surf = self.font.render(self.text, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=self.base_image.get_rect().center)
        self.base_image.blit(txt_surf, txt_rect)
        self.hover_image.blit(txt_surf, txt_rect)

    def update(self, dt: float):
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            self.image = self.hover_image
        else:
            self.image = self.base_image

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()

player_data = GAME_CONFIG["entities"][0]["variables"]
projectile_data = GAME_CONFIG["entities"][1]["variables"]
zombie_data = GAME_CONFIG["entities"][2]["variables"]
coin_data = GAME_CONFIG["entities"][3]["variables"]

class Player(GameSprite):
    def __init__(self, resource_manager: ResourceManager):
        super().__init__()
        self.resource_manager = resource_manager
        self.image = self.resource_manager.get_image(player_data["image_asset"], (48, 48))
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.pos = pygame.math.Vector2(player_data["initial_position"])
        self.max_hp = player_data["max_hp"]
        self.hp = self.max_hp
        self.speed = player_data["speed_pixels_per_sec"]
        self.attack_cooldown = player_data["attack_cooldown_sec"]
        self.invuln_dur = player_data["invulnerability_duration_sec"]
        self.current_cooldown = 0.0
        self.invuln_timer = 0.0
        self.is_invuln = False
        self.score = 0

    def update(self, dt: float, enemies: pygame.sprite.Group, proj_pool: ObjectPool, proj_group: pygame.sprite.Group, cam_group: CameraScrollGroup):
        keys = pygame.key.get_pressed()
        move = pygame.math.Vector2(0, 0)
        if keys[pygame.K_w]: move.y -= 1
        if keys[pygame.K_s]: move.y += 1
        if keys[pygame.K_a]: move.x -= 1
        if keys[pygame.K_d]: move.x += 1

        if move.length_squared() > 0:
            move.normalize_ip()
            self.pos += move * self.speed * dt
            self.pos.x = max(24, min(self.pos.x, WORLD_WIDTH - 24))
            self.pos.y = max(24, min(self.pos.y, WORLD_HEIGHT - 24))
            self.rect.center = (int(self.pos.x), int(self.pos.y))

        if self.is_invuln:
            self.invuln_timer -= dt
            if self.invuln_timer <= 0: self.is_invuln = False

        self.current_cooldown -= dt
        if self.current_cooldown <= 0:
            self.current_cooldown = self.attack_cooldown
            self.auto_attack(enemies, proj_pool, proj_group, cam_group)

    def auto_attack(self, enemies, proj_pool, proj_group, cam_group):
        if not enemies: return
        target = min(enemies, key=lambda e: (self.pos - e.pos).length_squared())
        proj = proj_pool.get()
        proj.setup(self.pos.x, self.pos.y, target.pos)
        proj_group.add(proj)
        cam_group.add(proj)
        AudioManager().play_sfx("player_shoot")

    def take_damage(self):
        if not self.is_invuln:
            self.hp -= 1
            self.is_invuln = True
            self.invuln_timer = self.invuln_dur
            AudioManager().play_sfx("player_damage")
            return True
        return False

    def reset(self):
        self.hp = self.max_hp
        self.score = 0
        self.pos = pygame.math.Vector2(player_data["initial_position"])
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.current_cooldown = 0.0
        self.invuln_timer = 0.0
        self.is_invuln = False

class EnergyBall(GameSprite):
    def __init__(self, resource_manager: ResourceManager):
        super().__init__()
        self.resource_manager = resource_manager
        self.active = False

    def setup(self, start_x, start_y, target_pos):
        self.image = self.resource_manager.get_image(projectile_data["image_asset"], (16, 16))
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.pos = pygame.math.Vector2(start_x, start_y)
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        direction = target_pos - self.pos
        if direction.length_squared() > 0:
            self.velocity = direction.normalize() * projectile_data["speed_pixels_per_sec"]
        else:
            self.velocity = pygame.math.Vector2(0, -projectile_data["speed_pixels_per_sec"])
        self.life_timer = projectile_data["lifespan_sec"]
        self.active = True

    def update(self, dt: float, pool: ObjectPool):
        if not self.active: return
        self.pos += self.velocity * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.life_timer -= dt
        if self.life_timer <= 0 or not WORLD_RECT.colliderect(self.rect):
            self.active = False
            self.kill()
            pool.release(self)

    def reset(self):
        super().reset()
        self.active = False

class Zombie(GameSprite):
    def __init__(self, resource_manager: ResourceManager):
        super().__init__()
        self.resource_manager = resource_manager
        self.active = False

    def setup(self, x, y):
        self.image = self.resource_manager.get_image(zombie_data["image_asset"], (32, 32))
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.pos = pygame.math.Vector2(x, y)
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.hp = zombie_data["hp"]
        self.active = True

    def update(self, dt: float, player_pos: pygame.math.Vector2):
        if not self.active: return
        direction = player_pos - self.pos
        if direction.length_squared() > 0:
            self.pos += direction.normalize() * zombie_data["speed_pixels_per_sec"] * dt
            self.rect.center = (int(self.pos.x), int(self.pos.y))

    def take_damage(self, amount: int):
        self.hp -= amount
        if self.hp <= 0:
            self.active = False
            return True
        return False

    def reset(self):
        super().reset()
        self.active = False

class GoldCoin(GameSprite):
    def __init__(self, resource_manager: ResourceManager):
        super().__init__()
        self.resource_manager = resource_manager
        self.active = False

    def setup(self, x, y):
        self.image = self.resource_manager.get_image(coin_data["image_asset"], (24, 24))
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.pos = pygame.math.Vector2(x, y)
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.life_timer = coin_data["lifespan_sec"]
        self.active = True

    def update(self, dt: float, pool: ObjectPool):
        if not self.active: return
        self.life_timer -= dt
        if self.life_timer <= 0:
            self.active = False
            self.kill()
            pool.release(self)

    def reset(self):
        super().reset()
        self.active = False

class EnemySpawner:
    def __init__(self):
        self.interval = zombie_data["spawn_interval_sec"]
        self.timer = self.interval

    def update(self, dt, group, pool, cam):
        self.timer -= dt
        if self.timer <= 0:
            self.timer = self.interval
            side = random.choice(['t', 'b', 'l', 'r'])
            if side == 't': x, y = random.uniform(0, WORLD_WIDTH), 0
            elif side == 'b': x, y = random.uniform(0, WORLD_WIDTH), WORLD_HEIGHT
            elif side == 'l': x, y = 0, random.uniform(0, WORLD_HEIGHT)
            else: x, y = WORLD_WIDTH, random.uniform(0, WORLD_HEIGHT)
            z = pool.get()
            z.setup(x, y)
            group.add(z)
            cam.add(z)

class GameState:
    def __init__(self, game): self.game = game
    def enter(self, **kwargs): pass
    def exit(self): pass
    def handle_event(self, event): pass
    def update(self, dt): pass
    def draw(self, surface): pass

class MainMenuState(GameState):
    def enter(self, **kwargs):
        self.game.audio_manager.play_music("main_menu")
        self.bg = self.game.resource_manager.get_image("main_menu_background.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        btn_img = self.game.resource_manager.get_image("button_generic.png")
        f = self.game.resource_manager.get_font('medium')
        # Requirement: reset=True must be passed to PlayingState transition
        self.btns = [
            Button(pygame.Rect(300, 250, 200, 50), "START", f, btn_img, lambda: self.game.change_state(self.game.playing_state, reset=True)),
            Button(pygame.Rect(300, 320, 200, 50), "RULES", f, btn_img, lambda: self.game.change_state(self.game.rules_state, prev="main_menu")),
            Button(pygame.Rect(300, 390, 200, 50), "QUIT", f, btn_img, lambda: setattr(self.game, 'running', False))
        ]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.game.change_state(self.game.playing_state, reset=True)
        for b in self.btns: b.handle_event(event)

    def update(self, dt):
        for b in self.btns: b.update(dt)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        t = self.game.resource_manager.get_font('title').render(GAME_CONFIG["game_states"]["main_menu"]["title"], True, (255, 255, 255))
        surface.blit(t, t.get_rect(center=(400, 150)))
        for b in self.btns: b.draw(surface)

class RulesState(GameState):
    def enter(self, **kwargs):
        self.prev = kwargs.get('prev', 'main_menu')
        self.bg = self.game.resource_manager.get_image("rules_background.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        def back(): self.game.change_state(self.game.main_menu_state if self.prev == 'main_menu' else self.game.paused_state)
        self.btn = Button(pygame.Rect(325, 520, 150, 50), "BACK", self.game.resource_manager.get_font('medium'), self.game.resource_manager.get_image("button_generic.png"), back)

    def handle_event(self, event): self.btn.handle_event(event)
    def update(self, dt): self.btn.update(dt)
    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        f_m = self.game.resource_manager.get_font('medium')
        for i, line in enumerate(GAME_CONFIG["game_rules"]):
            s = f_m.render(line, True, (255, 255, 255))
            surface.blit(s, s.get_rect(center=(400, 100 + i * 40)))
        self.btn.draw(surface)

class PlayingState(GameState):
    def enter(self, **kwargs):
        if kwargs.get('reset'): self.game.reset_game()
        self.game.audio_manager.play_music("gameplay")
        self.bg = self.game.resource_manager.get_image("arena_background.png", (WORLD_WIDTH, WORLD_HEIGHT))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in [pygame.K_p, pygame.K_ESCAPE]: self.game.change_state(self.game.paused_state)

    def update(self, dt):
        self.game.player.update(dt, self.game.enemies, self.game.energy_ball_pool, self.game.player_projectiles, self.game.camera_group)
        self.game.enemies.update(dt, self.game.player.pos)
        for p in self.game.player_projectiles: p.update(dt, self.game.energy_ball_pool)
        for c in self.game.coins: c.update(dt, self.game.coin_pool)
        self.game.enemy_spawner.update(dt, self.game.enemies, self.game.zombie_pool, self.game.camera_group)
        self.game.camera_group.set_focus(self.game.player.rect)

        CollisionManager.apply_group_vs_group(self.game.player_projectiles, self.game.enemies, on_collide=self.game.on_projectile_hit)
        CollisionManager.apply_sprite_vs_group(self.game.player, self.game.enemies, on_collide=self.game.on_player_hit)
        CollisionManager.apply_sprite_vs_group(self.game.player, self.game.coins, on_collide=self.game.on_coin_collect)

        if self.game.player.hp <= 0: self.game.change_state(self.game.game_over_state)

    def draw(self, surface):
        self.game.camera_group.custom_draw(surface, self.bg)
        self._draw_hud(surface)

    def _draw_hud(self, surface):
        f = self.game.resource_manager.get_font('medium')
        full = self.game.resource_manager.get_image("heart_full.png", (32, 32))
        empty = self.game.resource_manager.get_image("heart_empty.png", (32, 32))
        for i in range(self.game.player.max_hp):
            surface.blit(full if i < self.game.player.hp else empty, (10 + i * 35, 10))
        sc = f.render(f"SCORE: {self.game.player.score}", True, (255, 255, 255))
        surface.blit(sc, sc.get_rect(topright=(790, 10)))

class PausedState(GameState):
    def enter(self, **kwargs):
        self.game.audio_manager.pause_music()
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 150))
        btn_img = self.game.resource_manager.get_image("button_generic.png")
        f = self.game.resource_manager.get_font('medium')
        self.btns = [
            Button(pygame.Rect(300, 200, 200, 50), "RESUME", f, btn_img, lambda: self.game.change_state(self.game.playing_state)),
            Button(pygame.Rect(300, 270, 200, 50), "RESTART", f, btn_img, lambda: self.game.change_state(self.game.playing_state, reset=True)),
            Button(pygame.Rect(300, 340, 200, 50), "RULES", f, btn_img, lambda: self.game.change_state(self.game.rules_state, prev="paused")),
            Button(pygame.Rect(300, 410, 200, 50), "EXIT", f, btn_img, lambda: self.game.change_state(self.game.main_menu_state))
        ]

    def exit(self): self.game.audio_manager.unpause_music()
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in [pygame.K_p, pygame.K_ESCAPE]: self.game.change_state(self.game.playing_state)
        for b in self.btns: b.handle_event(event)
    def update(self, dt):
        for b in self.btns: b.update(dt)
    def draw(self, surface):
        self.game.playing_state.draw(surface)
        surface.blit(self.overlay, (0, 0))
        for b in self.btns: b.draw(surface)

class GameOverState(GameState):
    def enter(self, **kwargs):
        self.game.audio_manager.play_music("game_over")
        self.bg = self.game.resource_manager.get_image("game_over_background.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        btn_img = self.game.resource_manager.get_image("button_generic.png")
        f = self.game.resource_manager.get_font('medium')
        self.btns = [
            Button(pygame.Rect(300, 350, 200, 50), "RESTART", f, btn_img, lambda: self.game.change_state(self.game.playing_state, reset=True)),
            Button(pygame.Rect(300, 420, 200, 50), "MAIN MENU", f, btn_img, lambda: self.game.change_state(self.game.main_menu_state))
        ]

    def handle_event(self, event):
        for b in self.btns: b.handle_event(event)
    def update(self, dt):
        for b in self.btns: b.update(dt)
    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        f_l = self.game.resource_manager.get_font('large')
        t = f_l.render("GAME OVER", True, (255, 0, 0))
        surface.blit(t, t.get_rect(center=(400, 200)))
        s = f_l.render(f"FINAL SCORE: {self.game.player.score}", True, (255, 255, 255))
        surface.blit(s, s.get_rect(center=(400, 280)))
        for b in self.btns: b.draw(surface)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.resource_manager = ResourceManager()
        self.audio_manager = AudioManager()
        self.camera_group = CameraScrollGroup((WORLD_WIDTH, WORLD_HEIGHT), (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.enemies = pygame.sprite.Group()
        self.player_projectiles = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.energy_ball_pool = ObjectPool(lambda: EnergyBall(self.resource_manager), 20)
        self.zombie_pool = ObjectPool(lambda: Zombie(self.resource_manager), 10)
        self.coin_pool = ObjectPool(lambda: GoldCoin(self.resource_manager), 10)
        self.player = Player(self.resource_manager)
        self.enemy_spawner = EnemySpawner()
        self.main_menu_state = MainMenuState(self)
        self.playing_state = PlayingState(self)
        self.paused_state = PausedState(self)
        self.game_over_state = GameOverState(self)
        self.rules_state = RulesState(self)
        self.current_state = self.main_menu_state
        self.current_state.enter()
        self.running = True
        self.game_active = False

    def change_state(self, new_state, **kwargs):
        self.current_state.exit()
        self.current_state = new_state
        self.current_state.enter(**kwargs)

    def reset_game(self):
        for s in list(self.enemies): self.zombie_pool.release(s)
        for s in list(self.player_projectiles): self.energy_ball_pool.release(s)
        for s in list(self.coins): self.coin_pool.release(s)
        self.enemies.empty()
        self.player_projectiles.empty()
        self.coins.empty()
        self.camera_group.empty()
        self.player.reset()
        self.camera_group.add(self.player)
        self.enemy_spawner.timer = zombie_data["spawn_interval_sec"]

    def on_projectile_hit(self, proj, enemy):
        if proj.active and enemy.active:
            if enemy.take_damage(projectile_data["damage"]):
                self.audio_manager.play_sfx("enemy_hit")
                self.player.score += 10
                c = self.coin_pool.get()
                c.setup(enemy.pos.x, enemy.pos.y)
                self.coins.add(c)
                self.camera_group.add(c)
                enemy.kill()
                self.zombie_pool.release(enemy)
            proj.active = False
            proj.kill()
            self.energy_ball_pool.release(proj)

    def on_player_hit(self, player, enemy):
        if enemy.active:
            player.take_damage()
            enemy.active = False
            enemy.kill()
            self.zombie_pool.release(enemy)

    def on_coin_collect(self, player, coin):
        if coin.active:
            player.score += coin.score_value
            self.audio_manager.play_sfx("coin_collect")
            coin.active = False
            coin.kill()
            self.coin_pool.release(coin)

    def run(self):
        if self.game_active: self.change_state(self.playing_state, reset=True)
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running = False
                self.current_state.handle_event(event)
            self.current_state.update(dt)
            self.screen.fill((0, 0, 0))
            self.current_state.draw(self.screen)
            pygame.display.flip()
        pygame.quit()

if __name__ == '__main__':
    Game().run()