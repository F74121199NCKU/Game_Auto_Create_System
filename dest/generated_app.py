import pygame
import random
import math
import enum
import os
import json
import sys
from typing import Dict, Any, List, Tuple, Callable, Optional, Set

# --- Game Data Configuration ---
# Centralized configuration for game entities and mechanics.
# This would ideally be loaded from a JSON/YAML file in a real game.
class GameData:
    SCREEN_WIDTH: int = 800
    SCREEN_HEIGHT: int = 600
    GAME_TITLE: str = "星際突襲 (Interstellar Assault)"
    FPS: int = 60

    # Colors
    WHITE: Tuple[int, int, int] = (255, 255, 255)
    BLACK: Tuple[int, int, int] = (0, 0, 0)
    RED: Tuple[int, int, int] = (255, 0, 0)
    GREEN: Tuple[int, int, int] = (0, 255, 0)
    BLUE: Tuple[int, int, int] = (0, 0, 255)
    YELLOW: Tuple[int, int, int] = (255, 255, 0)
    ORANGE: Tuple[int, int, int] = (255, 165, 0)
    GREY: Tuple[int, int, int] = (150, 150, 150)
    LIGHT_GREY: Tuple[int, int, int] = (200, 200, 200)
    TRANSPARENT_BLUE: Tuple[int, int, int, int] = (50, 50, 200, 150)
    TRANSPARENT_RED: Tuple[int, int, int, int] = (255, 0, 0, 150)

    # Player Configuration
    PLAYER_CONFIG: Dict[str, Any] = {
        "initial_health": 3,
        "speed": 300,
        "base_fire_rate": 0.2,  # seconds per shot
        "invulnerability_duration": 1.5,  # seconds after damage
        "bullet_speed": 600,
        "bullet_damage": 1,
        "max_weapon_level": 4,
    }
    SHIELD_DURATION: float = 5  # seconds

    # Enemy Configurations
    ENEMY_TYPES: Dict[str, Dict[str, Any]] = {
        "basic_fighter": {
            "health": 1,
            "speed": 150,
            "score": 10,
            "fire_rate": 1.0,
            "bullet_type": "normal",
            "bullet_speed": 400,
            "bullet_damage": 1,
            "image_name": "enemy_basic",
            "sway_magnitude": 0.0, # Added for consistency
            "sway_speed_factor": 0.0 # Added for consistency
        },
        "heavy_bomber": {
            "health": 3,
            "speed": 100,
            "score": 50,
            "fire_rate": 2.0,
            "bullet_type": "spread",
            "bullet_speed": 350,
            "bullet_damage": 1,
            "image_name": "enemy_bomber",
            "sway_magnitude": 50.0,  # Moved from hardcoded
            "sway_speed_factor": 0.5  # Moved from hardcoded
        },
        "chaser": {
            "health": 2,
            "speed_initial": 180,
            "speed_chasing": 250,
            "score": 25,
            "fire_rate": 0,  # No shooting
            "bullet_type": None,
            "bullet_speed": 0,
            "bullet_damage": 0,
            "image_name": "enemy_chaser",
            "sway_magnitude": 0.0, # Added for consistency
            "sway_speed_factor": 0.0 # Added for consistency
        }
    }

    # Boss Configurations
    BOSS_TYPES: Dict[str, Dict[str, Any]] = {
        "boss1": {
            "health": 50,
            "speed": 70,
            "score": 500,
            "phase1_fire_rate": 0.5,  # seconds per wave
            "phase2_laser_fire_rate": 3.0,  # seconds per laser burst trigger
            "laser_duration": 1.0,  # seconds
            "laser_damage_per_frame": 0.05,  # Damage amount per frame while in laser
            "image_name": "boss1",
            "bullet_type_phase1": "spread_boss", # Explicitly define bullet types for phases
            "bullet_type_phase2": "laser",
        }
    }

    # Player Weapon Level Configurations
    PLAYER_WEAPON_CONFIGS: Dict[int, List[Dict[str, Any]]] = {
        1: [
            {"offset_x": 0, "offset_y": 0, "angle_degrees": 0, "piercing": False}
        ],
        2: [
            {"offset_x": -0.25, "offset_y": 0, "angle_degrees": 0, "piercing": False},
            {"offset_x": 0.25, "offset_y": 0, "angle_degrees": 0, "piercing": False}
        ],
        3: [
            {"offset_x": 0, "offset_y": 0, "angle_degrees": 0, "piercing": False},
            {"offset_x": -0.3, "offset_y": 0, "angle_degrees": -10, "piercing": False},
            {"offset_x": 0.3, "offset_y": 0, "angle_degrees": 10, "piercing": False}
        ],
        4: [ # Quad shot with slight spread and piercing
            {"offset_x": -0.375, "offset_y": 0, "angle_degrees": -15, "piercing": True},
            {"offset_x": -0.125, "offset_y": 0, "angle_degrees": -5, "piercing": True},
            {"offset_x": 0.125, "offset_y": 0, "angle_degrees": 5, "piercing": True},
            {"offset_x": 0.375, "offset_y": 0, "angle_degrees": 15, "piercing": True}
        ]
    }

    # Power-up Configurations
    POWERUP_PROBABILITY: float = 0.2
    POWERUP_TYPES: List[str] = ["firepower", "shield", "extra_life", "score_boost"]
    POWERUP_EFFECTS: Dict[str, Dict[str, Any]] = {
        "firepower": {"action": "upgrade_weapon"},
        "shield": {"action": "activate_shield", "duration": SHIELD_DURATION},
        "extra_life": {"action": "heal", "amount": 1},
        "score_boost": {"action": "add_score", "amount": 100}
    }

    # Background
    BASE_BACKGROUND_SCROLL_SPEED: int = 50

    # Wave Management
    WAVE_INTERVAL: int = 10  # seconds
    BOSS_SPAWN_INTERVAL_WAVES: int = 3  # Boss every 3 regular waves (after first)
    WAVE_CONFIG: Dict[str, Any] = { # Moved from hardcoded in WaveManager
        "initial_basic_fighters": 5,
        "basic_fighter_increment": 1,
        "initial_heavy_bombers": 1,
        "heavy_bomber_increment": 0.5,
        "initial_chasers": 0,
        "chaser_increment": 0.33
    }

    # File Paths
    HIGH_SCORE_FILE: str = "interstellar_assault_highscores.json"
    HIGH_SCORE_LIMIT: int = 10 # Moved from hardcoded in ScoreManager

    # UI Layout Constants
    MENU_LINE_HEIGHT: int = 40 # Moved from hardcoded in UIComponent
    MAIN_MENU_START_Y_OFFSET: int = 300 # Moved from hardcoded in UIComponent
    PAUSE_MENU_START_Y_OFFSET: int = 300 # Moved from hardcoded in UIComponent
    GAMEOVER_SCORES_TITLE_Y_OFFSET: int = 250
    GAMEOVER_SCORES_START_Y_OFFSET: int = 300
    GAMEOVER_MENU_OFFSET_FROM_SCORES: int = 30

    # Object Pool Initial Sizes (Moved from hardcoded)
    PLAYER_BULLET_POOL_SIZE: int = 50
    ENEMY_BULLET_POOL_SIZE: int = 100
    ENEMY_POOL_SIZE: int = 20
    BOSS_POOL_SIZE: int = 1
    POWERUP_POOL_SIZE: int = 10
    PARTICLE_POOL_SIZE: int = 200

    # Image sizes and colors for dummy resource loading
    # (In a real game, this would be derived from actual image files)
    IMAGE_DEFINITIONS: Dict[str, Tuple[Tuple[int, int], Tuple[int, int, int, int], bool]] = {
        "player_ship": ((64, 64), BLUE, True),
        "player_bullet": ((8, 16), YELLOW, True),
        "player_shield": ((70, 70), TRANSPARENT_BLUE, True),
        "enemy_basic": ((48, 48), RED, True),
        "enemy_bomber": ((64, 64), ORANGE, True),
        "enemy_chaser": ((40, 40), GREEN, True),
        "boss1": ((128, 128), GREY, True),
        "enemy_bullet_normal": ((10, 20), RED, True),
        "enemy_bullet_spread": ((12, 12), ORANGE, True),
        "enemy_laser": ((40, 600), TRANSPARENT_RED, True),
        "powerup_firepower": ((30, 30), YELLOW, True),
        "powerup_shield": ((30, 30), BLUE, True),
        "powerup_extra_life": ((30, 30), GREEN, True),
        "powerup_score_boost": ((30, 30), WHITE, True),
        "particle_explosion": ((5, 5), ORANGE, True),
        "particle_hit": ((3, 3), WHITE, True),
        "particle_trail": ((3, 3), YELLOW, True),
        "bg_stars_far": ((SCREEN_WIDTH, SCREEN_HEIGHT * 2), (0, 0, 30), True),
        "bg_stars_near": ((SCREEN_WIDTH, SCREEN_HEIGHT * 2), (0, 0, 60), True),
        "placeholder": ((32, 32), RED, True)
    }


# --- Generic Object Pool ---
class GenericObjectPool:
    def __init__(self, create_func: Callable[[], Any], initial_size: int):
        self._pool: List[Any] = []
        self.create_func: Callable[[], Any] = create_func
        self._active_count: int = 0

        for _ in range(initial_size):
            obj = self.create_func()
            obj.deactivate()
            self._pool.append(obj)

    def get(self, *args: Any, **kwargs: Any) -> Any:
        for obj in self._pool:
            if not obj.is_active():
                obj.activate(*args, **kwargs)
                self._active_count += 1
                # Ensure the object has a back-reference to its pool, if it expects one.
                # This handles cases where create_func doesn't set it immediately (e.g., Bullet(), Particle(), PowerUp())
                if hasattr(obj, 'bullet_pool'): # For Bullet
                    obj.bullet_pool = self
                elif hasattr(obj, 'pool'): # For Particle, PowerUp
                    obj.pool = self
                return obj

        new_obj = self.create_func()
        new_obj.activate(*args, **kwargs)
        self._pool.append(new_obj)
        self._active_count += 1
        # Also ensure back-reference for newly created objects
        if hasattr(new_obj, 'bullet_pool'):
            new_obj.bullet_pool = self
        elif hasattr(new_obj, 'pool'):
            new_obj.pool = self
        return new_obj

    def return_obj(self, obj: Any) -> None:
        if obj.is_active():
            obj.deactivate()
            self._active_count -= 1

    def get_active(self) -> List[Any]:
        return [obj for obj in self._pool if obj.is_active()]

    def reset(self) -> None:
        for obj in self._pool:
            obj.deactivate()
        self._active_count = 0


# --- Event System (Observer Pattern) ---
class EventManager:
    _instance: Optional["EventManager"] = None

    def __new__(cls) -> "EventManager":
        if cls._instance is None:
            cls._instance = super(EventManager, cls).__new__(cls)
            cls._instance.subscribers: Dict["GameEvent", List[Callable[..., None]]] = {}
        return cls._instance

    def register(self, event_type: "GameEvent", callback: Callable[..., None]) -> None:
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def unregister(self, event_type: "GameEvent", callback: Callable[..., None]) -> None:
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    def post(self, event_type: "GameEvent", *args: Any, **kwargs: Any) -> None:
        if event_type in self.subscribers:
            for callback in list(self.subscribers[event_type]):
                callback(*args, **kwargs)


# Define custom event types
class GameEvent(enum.Enum):
    PLAYER_DAMAGED = 1
    PLAYER_DIED = 2
    ENEMY_DIED = 3
    POWERUP_COLLECTED = 4
    SCORE_CHANGED = 5
    GAME_OVER = 6
    GAME_START = 7
    GAME_PAUSED = 8
    GAME_RESUMED = 9
    PLAYER_WEAPON_UPGRADED = 10
    PLAYER_SHIELD_ACTIVATED = 11
    PLAYER_HEALTH_GAINED = 12
    BOSS_ACTIVATE_LASER = 13


# --- Game States ---
class GameState(enum.Enum):
    RULES = 0
    MAIN_MENU = 1
    OPTIONS = 2
    GAMEPLAY = 3
    PAUSE_MENU = 4
    GAME_OVER = 5
    HIGH_SCORES = 6 # Added for explicit High Score screen


# --- Resource Management ---
class ResourceManager:
    _images: Dict[str, pygame.Surface] = {}
    _sounds: Dict[str, pygame.mixer.Sound] = {}
    _music: Dict[str, Any] = {} # Using Any for the DummyMusic class
    _fonts: Dict[Tuple[str, int], pygame.font.Font] = {}

    @staticmethod
    def _create_dummy_surface(size: Tuple[int, int], color: Tuple[int, int, int, Optional[int]], alpha: bool) -> pygame.Surface:
        """Creates a dummy pygame.Surface for simulation."""
        surf = pygame.Surface(size, pygame.SRCALPHA if alpha else 0)
        surf.fill(color)
        if alpha:
            surf = surf.convert_alpha()
        else:
            surf = surf.convert()
        return surf

    @staticmethod
    def _create_dummy_sound() -> pygame.mixer.Sound:
        """Creates a dummy pygame.mixer.Sound for simulation."""
        sample_rate = 22050
        duration = 0.1
        num_samples = int(sample_rate * duration)
        sine_wave = [int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(num_samples)]
        buffer = bytearray()
        for sample in sine_wave:
            buffer.extend(sample.to_bytes(2, byteorder='little', signed=True))
        sound = pygame.mixer.Sound(buffer=buffer)
        sound.set_volume(0.1)
        return sound

    @staticmethod
    def _create_dummy_music() -> Any: # Returns an instance of DummyMusic
        """Creates a dummy music placeholder that simulates play/stop/pause logic."""
        class DummyMusic:
            _playing: bool
            _paused: bool
            _volume: float
            def __init__(self) -> None:
                self._playing = False
                self._paused = False
                self._volume = 0.5
            def play(self, loops: int = -1, start: float = 0.0) -> None:
                self._playing = True
                self._paused = False
            def stop(self) -> None:
                self._playing = False
                self._paused = False
            def pause(self) -> None:
                if self._playing: self._paused = True
            def unpause(self) -> None:
                if self._playing: self._paused = False
            def set_volume(self, volume: float) -> None:
                self._volume = volume
            def get_volume(self) -> float: return self._volume
            def fadeout(self, ms: int) -> None:
                self.stop()
            def get_busy(self) -> bool: return self._playing and not self._paused
        return DummyMusic()

    @staticmethod
    def load_image(name: str, size: Tuple[int, int], color: Tuple[int, int, int, Optional[int]], alpha: bool) -> pygame.Surface:
        if name not in ResourceManager._images:
            image = ResourceManager._create_dummy_surface(size, color, alpha)
            ResourceManager._images[name] = image
        return ResourceManager._images[name]

    @staticmethod
    def get_image(name: str) -> Optional[pygame.Surface]:
        return ResourceManager._images.get(name)

    @staticmethod
    def load_sound(name: str) -> pygame.mixer.Sound:
        if name not in ResourceManager._sounds:
            sound = ResourceManager._create_dummy_sound()
            ResourceManager._sounds[name] = sound
        return ResourceManager._sounds[name]

    @staticmethod
    def get_sound(name: str) -> Optional[pygame.mixer.Sound]:
        return ResourceManager._sounds.get(name)

    @staticmethod
    def load_music(name: str) -> Any:
        if name not in ResourceManager._music:
            music = ResourceManager._create_dummy_music()
            ResourceManager._music[name] = music
        return ResourceManager._music[name]

    @staticmethod
    def get_music(name: str) -> Any:
        return ResourceManager._music.get(name)

    @staticmethod
    def load_font(name: str, size: int) -> pygame.font.Font:
        key = (name, size)
        if key not in ResourceManager._fonts:
            try:
                font = pygame.font.Font(pygame.font.match_font(name), size)
            except:
                font = pygame.font.Font(None, size)
            ResourceManager._fonts[key] = font
        return ResourceManager._fonts[key]

    @staticmethod
    def get_font(name: str, size: int) -> Optional[pygame.font.Font]:
        return ResourceManager._fonts.get((name, size))

    @staticmethod
    def init_resources() -> None:
        for name, (size, color, alpha) in GameData.IMAGE_DEFINITIONS.items():
            ResourceManager.load_image(name, size, color, alpha)

        ResourceManager.load_sound("player_shoot")
        ResourceManager.load_sound("enemy_shoot")
        ResourceManager.load_sound("explosion")
        ResourceManager.load_sound("player_hit")
        ResourceManager.load_sound("powerup_collect")
        ResourceManager.load_sound("game_over")
        ResourceManager.load_sound("menu_select")
        ResourceManager.load_sound("menu_navigate")

        ResourceManager.load_music("main_menu_music")
        ResourceManager.load_music("gameplay_music")
        ResourceManager.load_music("boss_music")

        ResourceManager.load_font("Arial", 48)
        ResourceManager.load_font("Arial", 36)
        ResourceManager.load_font("Arial", 24)
        ResourceManager.load_font("Arial", 18)


# --- Audio Mixer ---
class AudioMixer:
    _instance: Optional["AudioMixer"] = None
    sfx_volume: float
    music_volume: float
    _current_dummy_music: Any

    def __new__(cls) -> "AudioMixer":
        if cls._instance is None:
            cls._instance = super(AudioMixer, cls).__new__(cls)
            cls._instance.sfx_volume = 0.5
            cls._instance.music_volume = 0.3
            pygame.mixer.init()
            cls._instance._current_dummy_music = None
        return cls._instance

    def play_sfx(self, name: str) -> None:
        sfx = ResourceManager.get_sound(name)
        if sfx:
            sfx.set_volume(self.sfx_volume)
            sfx.play()

    def play_music(self, name: str, loops: int = -1, start: float = 0.0) -> None:
        music = ResourceManager.get_music(name)
        if music:
            if self._current_dummy_music:
                self._current_dummy_music.stop()
            self._current_dummy_music = music
            self._current_dummy_music.set_volume(self.music_volume)
            self._current_dummy_music.play(loops, start)

    def stop_music(self) -> None:
        if self._current_dummy_music:
            self._current_dummy_music.stop()
            self._current_dummy_music = None

    def pause_music(self) -> None:
        if self._current_dummy_music:
            self._current_dummy_music.pause()

    def unpause_music(self) -> None:
        if self._current_dummy_music:
            self._current_dummy_music.unpause()

    def set_sfx_volume(self, volume: float) -> None:
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in ResourceManager._sounds.values():
             sound.set_volume(self.sfx_volume)

    def set_music_volume(self, volume: float) -> None:
        self.music_volume = max(0.0, min(1.0, volume))
        if self._current_dummy_music:
            self._current_dummy_music.set_volume(self.music_volume)


# --- Base Game Objects and Components ---

class Activatable:
    """Mixin for objects that can be activated/deactivated for object pooling."""
    _is_active: bool

    def __init__(self) -> None:
        self._is_active = False

    def activate(self, *args: Any, **kwargs: Any) -> None:
        self._is_active = True

    def deactivate(self) -> None:
        self._is_active = False
        # When an object deactivates, remove it from the spatial grid
        game_instance = Game.get_instance()
        if game_instance and hasattr(game_instance, 'spatial_grid') and game_instance.spatial_grid:
            game_instance.spatial_grid.remove_object(self)

    def is_active(self) -> bool:
        return self._is_active


class GameObject(Activatable):
    image_name: str
    image: Optional[pygame.Surface]
    rect: pygame.Rect
    pos: pygame.math.Vector2
    vel: pygame.math.Vector2
    _grid_cells: Set[Tuple[int, int]] # Used internally by SpatialGrid

    def __init__(self, image_name: str, initial_pos: Tuple[int, int]) -> None:
        super().__init__()
        self.image_name = image_name
        self.image = ResourceManager.get_image(image_name)
        if self.image:
            self.rect = self.image.get_rect(center=initial_pos)
        else:
            self.image = ResourceManager.get_image("placeholder") # Fallback
            if not self.image: # Should not happen after init_resources
                self.image = ResourceManager._create_dummy_surface((32,32), GameData.RED, True)
            self.rect = pygame.Rect(0, 0, 32, 32)
            self.rect.center = initial_pos

        self.pos = pygame.math.Vector2(self.rect.center)
        self.vel = pygame.math.Vector2(0, 0)
        self._grid_cells = set() # Initialize empty set

    def update(self, dt: float) -> None:
        if not self.is_active():
            return
        self.pos += self.vel * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        # Spatial grid update for this object is handled in the main game loop
        # by calling Game.spatial_grid.add_object(self) after its update.

    def draw(self, screen: pygame.Surface) -> None:
        if self.is_active() and self.image:
            screen.blit(self.image, self.rect)

    def is_offscreen(self) -> bool:
        return self.rect.right < 0 or self.rect.left > GameData.SCREEN_WIDTH or \
               self.rect.bottom < 0 or self.rect.top > GameData.SCREEN_HEIGHT

    def get_collider_rect(self) -> pygame.Rect:
        return self.rect


class HealthComponent:
    _max_health: int
    _current_health: int
    _is_invincible: bool
    _invincibility_timer: float
    _invincibility_duration: float

    def __init__(self, max_health: int, invincibility_duration: float = 0) -> None:
        self._max_health = max_health
        self._current_health = max_health
        self._is_invincible = False
        self._invincibility_timer = 0.0
        self._invincibility_duration = invincibility_duration

    def get_health(self) -> int:
        return self._current_health

    def get_max_health(self) -> int:
        return self._max_health

    def is_alive(self) -> bool:
        return self._current_health > 0

    def take_damage(self, amount: float) -> bool: # Changed to float for boss laser
        if self._is_invincible:
            return False

        self._current_health -= amount
        self._current_health = max(0, math.floor(self._current_health)) # Round down for int health
        self._is_invincible = True
        self._invincibility_timer = self._invincibility_duration
        return True

    def heal(self, amount: int) -> None:
        self._current_health += amount
        self._current_health = min(self._max_health, self._current_health)

    def update(self, dt: float) -> None:
        if self._is_invincible:
            self._invincibility_timer -= dt
            if self._invincibility_timer <= 0:
                self._is_invincible = False

    def is_invincible(self) -> bool:
        return self._is_invincible

    def reset(self, max_health: Optional[int] = None) -> None:
        if max_health is not None:
            self._max_health = max_health
        self._current_health = self._max_health
        self._is_invincible = False
        self._invincibility_timer = 0.0


class ShootingComponent:
    owner: Any
    bullet_pool: GenericObjectPool
    fire_rate: float
    bullet_type: Optional[str]
    bullet_speed: float
    bullet_damage: int
    bullet_image_name: str
    _last_shot_time: float
    _weapon_level: int
    event_manager: EventManager
    audio_mixer: AudioMixer
    player_weapon_configs: Dict[int, List[Dict[str, Any]]]

    def __init__(self, owner: Any, bullet_pool: GenericObjectPool, fire_rate: float,
                 bullet_type: Optional[str], bullet_speed: float, bullet_damage: int,
                 bullet_image_name: str, event_manager: EventManager, audio_mixer: AudioMixer,
                 player_weapon_configs: Dict[int, List[Dict[str, Any]]]) -> None:
        self.owner = owner
        self.bullet_pool = bullet_pool
        self.fire_rate = fire_rate
        self.bullet_type = bullet_type
        self.bullet_speed = bullet_speed
        self.bullet_damage = bullet_damage
        self.bullet_image_name = bullet_image_name
        self._last_shot_time = 0.0
        self._weapon_level = 1
        self.event_manager = event_manager
        self.audio_mixer = audio_mixer
        self.player_weapon_configs = player_weapon_configs

    def can_shoot(self, current_time: float) -> bool:
        return current_time - self._last_shot_time >= self.fire_rate

    def shoot(self, current_time: float) -> bool:
        if self.can_shoot(current_time):
            self._last_shot_time = current_time
            if isinstance(self.owner, Player):
                self._player_shoot_logic()
            elif isinstance(self.owner, Boss):
                self._boss_shoot_logic()
            else:  # Generic enemy shoot logic
                self._enemy_shoot_logic()
            return True
        return False

    def _player_shoot_logic(self) -> None:
        player_pos = self.owner.pos
        player_width = self.owner.rect.width

        weapon_config = self.player_weapon_configs.get(self._weapon_level, self.player_weapon_configs[1])

        for bullet_data in weapon_config:
            offset_x_factor = bullet_data["offset_x"]
            angle_degrees = bullet_data["angle_degrees"]
            piercing = bullet_data["piercing"]

            # Calculate bullet position
            bullet_offset_x = player_width * offset_x_factor
            bullet_pos = player_pos + pygame.math.Vector2(bullet_offset_x, -player_width / 2)

            # Calculate bullet velocity with angle
            angle_rad = math.radians(angle_degrees - 90) # -90 because 0 degrees is right, 90 is down. We want 0 to be up.
            bullet_dir = pygame.math.Vector2(math.cos(angle_rad), math.sin(angle_rad))
            bullet_vel = bullet_dir * self.bullet_speed

            self._create_bullet(bullet_pos, bullet_vel, piercing)

        self.audio_mixer.play_sfx("player_shoot")

    def _enemy_shoot_logic(self) -> None:
        enemy_pos = self.owner.pos
        enemy_width = self.owner.rect.width

        if self.bullet_type == "normal":
            bullet_vel = pygame.math.Vector2(0, self.bullet_speed)
            self._create_bullet(enemy_pos + pygame.math.Vector2(0, enemy_width / 2), bullet_vel)
        elif self.bullet_type == "spread":
            bullet_vel_c = pygame.math.Vector2(0, self.bullet_speed)
            bullet_vel_l = pygame.math.Vector2(-0.3, 1).normalize() * self.bullet_speed
            bullet_vel_r = pygame.math.Vector2(0.3, 1).normalize() * self.bullet_speed
            self._create_bullet(enemy_pos + pygame.math.Vector2(0, enemy_width / 2), bullet_vel_c)
            self._create_bullet(enemy_pos + pygame.math.Vector2(-enemy_width / 4, enemy_width / 2), bullet_vel_l)
            self._create_bullet(enemy_pos + pygame.math.Vector2(enemy_width / 4, enemy_width / 2), bullet_vel_r)

        self.audio_mixer.play_sfx("enemy_shoot")

    def _boss_shoot_logic(self) -> None:
        boss_pos = self.owner.pos
        boss_width = self.owner.rect.width
        boss_config = GameData.BOSS_TYPES["boss1"] # Assuming only Boss1 for now

        if self.bullet_type == boss_config["bullet_type_phase1"]: # Phase 1 spread
            num_bullets = random.randint(5, 7)
            for _ in range(num_bullets):
                angle_offset = random.uniform(-0.5, 0.5)
                bullet_dir = pygame.math.Vector2(math.sin(angle_offset), math.cos(angle_offset)).normalize()
                bullet_vel = bullet_dir * self.bullet_speed
                self._create_bullet(boss_pos + pygame.math.Vector2(0, boss_width / 2), bullet_vel)
        elif self.bullet_type == boss_config["bullet_type_phase2"]: # Phase 2 laser
            self.event_manager.post(GameEvent.BOSS_ACTIVATE_LASER, self.owner,
                                    boss_config["laser_damage_per_frame"], boss_config["laser_duration"])

        self.audio_mixer.play_sfx("enemy_shoot")

    def _create_bullet(self, pos: pygame.math.Vector2, vel: pygame.math.Vector2, piercing: bool = False) -> Any:
        bullet = self.bullet_pool.get(pos, vel, self.bullet_damage, self.owner.__class__.__name__, self.bullet_image_name, piercing)
        return bullet

    def set_weapon_level(self, level: int) -> None:
        self._weapon_level = level
        self.event_manager.post(GameEvent.PLAYER_WEAPON_UPGRADED, level)

    def get_weapon_level(self) -> int:
        return self._weapon_level

    def reset(self) -> None:
        self._weapon_level = 1
        self._last_shot_time = 0.0


class PlayerInputComponent:
    player: "Player"

    def __init__(self, player: "Player") -> None:
        self.player = player

    def handle_input(self, event: pygame.event.Event) -> None:
        # Player is guaranteed to be active when this is called from gameplay state
        player_speed = GameData.PLAYER_CONFIG["speed"]

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w or event.key == pygame.K_UP:
                self.player.vel.y = -player_speed
            if event.key == pygame.K_s or event.key == pygame.K_DOWN:
                self.player.vel.y = player_speed
            if event.key == pygame.K_a or event.key == pygame.K_LEFT:
                self.player.vel.x = -player_speed
            if event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                self.player.vel.x = player_speed
            if event.key == pygame.K_SPACE:
                self.player.is_firing = True

        elif event.type == pygame.KEYUP:
            if (event.key == pygame.K_w or event.key == pygame.K_s or
                    event.key == pygame.K_UP or event.key == pygame.K_DOWN):
                self.player.vel.y = 0
            if (event.key == pygame.K_a or event.key == pygame.K_d or
                    event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT):
                self.player.vel.x = 0
            if event.key == pygame.K_SPACE:
                self.player.is_firing = False

        if self.player.vel.length() > player_speed:
            self.player.vel.normalize_ip()
            self.player.vel *= player_speed


class StateMachineComponent:
    current_state: str
    state_map: Dict[str, Callable[[Any, float, float, float], None]]
    state_timer: float
    target_state_duration: float

    def __init__(self, initial_state: str, state_map: Dict[str, Callable[[Any, float, float, float], None]]) -> None:
        self.current_state = initial_state
        self.state_map = state_map
        self.state_timer = 0.0
        self.target_state_duration = 0.0

    def set_state(self, new_state: str, duration: float = 0.0) -> None:
        if new_state not in self.state_map:
            raise ValueError(f"State '{new_state}' not defined in state_map.")
        self.current_state = new_state
        self.state_timer = 0.0
        self.target_state_duration = duration

    def update(self, dt: float, owner: Any) -> None:
        self.state_timer += dt
        state_handler = self.state_map.get(self.current_state)
        if state_handler:
            state_handler(owner, dt, self.state_timer, self.target_state_duration)

    def is_in_state(self, state: str) -> bool:
        return self.current_state == state

    def reset(self, initial_state: str) -> None:
        self.current_state = initial_state
        self.state_timer = 0.0
        self.target_state_duration = 0.0


# --- Specific Game Entities ---

class Bullet(GameObject):
    bullet_pool: Optional[GenericObjectPool] # Changed to Optional
    damage: int
    shooter_type: str
    piercing: bool

    def __init__(self, bullet_pool: Optional[GenericObjectPool] = None) -> None: # Made pool optional
        super().__init__("player_bullet", (0, 0)) # Placeholder image_name, updated on activate
        self.bullet_pool = bullet_pool
        self.damage = 0
        self.shooter_type = ""
        self.piercing = False

    def activate(self, pos: pygame.math.Vector2, vel: pygame.math.Vector2, damage: int,
                 shooter_type: str, image_name: str, piercing: bool = False) -> None:
        super().activate()
        self.pos = pygame.math.Vector2(pos)
        self.rect.center = (int(pos.x), int(pos.y))
        self.vel = pygame.math.Vector2(vel)
        self.damage = damage
        self.shooter_type = shooter_type
        self.image_name = image_name
        self.image = ResourceManager.get_image(image_name) # Ensure image is set here
        if not self.image: self.image = ResourceManager.get_image("placeholder")
        self.rect = self.image.get_rect(center=self.pos) # Update rect size based on actual image
        self.piercing = piercing

    def deactivate(self) -> None:
        super().deactivate()
        self.vel = pygame.math.Vector2(0, 0)
        self.shooter_type = ""
        self.piercing = False

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.is_offscreen():
            if self.bullet_pool: # Added check for self.bullet_pool before calling return_obj
                self.bullet_pool.return_obj(self)


class Player(GameObject):
    health_comp: HealthComponent
    shooting_comp: ShootingComponent
    input_comp: PlayerInputComponent
    is_firing: bool
    _shield_active: bool
    _shield_timer: float
    max_weapon_level: int
    event_manager: EventManager
    audio_mixer: AudioMixer
    _current_alpha: int # For flashing effect

    def __init__(self, bullet_pool: GenericObjectPool, event_manager: EventManager, audio_mixer: AudioMixer) -> None:
        super().__init__("player_ship", (GameData.SCREEN_WIDTH // 2, GameData.SCREEN_HEIGHT - 100))
        player_config = GameData.PLAYER_CONFIG
        self.health_comp = HealthComponent(player_config["initial_health"], player_config["invulnerability_duration"])
        self.shooting_comp = ShootingComponent(
            self, bullet_pool, player_config["base_fire_rate"], "normal",
            player_config["bullet_speed"], player_config["bullet_damage"],
            "player_bullet", event_manager, audio_mixer, GameData.PLAYER_WEAPON_CONFIGS
        )
        self.input_comp = PlayerInputComponent(self)
        self.is_firing = False
        self._shield_active = False
        self._shield_timer = 0.0
        self.max_weapon_level = player_config["max_weapon_level"]
        self.event_manager = event_manager
        self.audio_mixer = audio_mixer
        self._current_alpha = 255 # For flashing effect

        event_manager.register(GameEvent.PLAYER_SHIELD_ACTIVATED, self._on_shield_activated)
        event_manager.register(GameEvent.PLAYER_WEAPON_UPGRADED, self._on_weapon_upgraded)
        event_manager.register(GameEvent.PLAYER_HEALTH_GAINED, self._on_health_gained)

    def activate(self, pos: Optional[pygame.math.Vector2] = None) -> None: # Changed to Vector2
        super().activate()
        if pos:
            self.pos = pygame.math.Vector2(pos)
        else:
            self.pos = pygame.math.Vector2(GameData.SCREEN_WIDTH // 2, GameData.SCREEN_HEIGHT - 100) # Default if no pos given
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.health_comp.reset(GameData.PLAYER_CONFIG["initial_health"])
        self.shooting_comp.reset()
        self.is_firing = False
        self._shield_active = False
        self._shield_timer = 0.0
        self._current_alpha = 255

    def deactivate(self) -> None:
        super().deactivate()
        self.vel = pygame.math.Vector2(0, 0)
        self.is_firing = False
        self._current_alpha = 255

    def update(self, dt: float) -> None:
        if not self.is_active():
            return

        self.health_comp.update(dt)

        if self._shield_active:
            self._shield_timer -= dt
            if self._shield_timer <= 0:
                self._shield_active = False

        # Update flashing state
        if self.health_comp.is_invincible() and not self._shield_active:
            # Flash every 100ms
            if int(pygame.time.get_ticks() / 100) % 2 == 0:
                self._current_alpha = 255
            else:
                self._current_alpha = 0
        else:
            self._current_alpha = 255 # Fully visible when not invincible or shielded

        new_pos = self.pos + self.vel * dt
        new_pos.x = max(self.rect.width / 2, min(GameData.SCREEN_WIDTH - self.rect.width / 2, new_pos.x))
        new_pos.y = max(self.rect.height / 2, min(GameData.SCREEN_HEIGHT - self.rect.height / 2, new_pos.y))
        self.pos = new_pos
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        if self.is_firing:
            self.shooting_comp.shoot(pygame.time.get_ticks() / 1000.0)

        if not self.health_comp.is_alive():
            self.event_manager.post(GameEvent.PLAYER_DIED)
            # The game state will change, no need to deactivate here.
            # Player will be deactivated via reset_game_state_dependent_components.

    def draw(self, screen: pygame.Surface) -> None:
        if not self.is_active():
            return

        if self.image:
            # Apply alpha based on calculated _current_alpha
            temp_image = self.image.copy()
            temp_image.set_alpha(self._current_alpha)
            screen.blit(temp_image, self.rect)

        if self._shield_active:
            shield_image = ResourceManager.get_image("player_shield")
            if shield_image:
                shield_rect = shield_image.get_rect(center=self.rect.center)
                screen.blit(shield_image, shield_rect)

    def take_damage(self, amount: float) -> bool: # Changed to float for consistency
        if self._shield_active:
            return False

        if self.health_comp.take_damage(amount):
            self.audio_mixer.play_sfx("player_hit")
            self.event_manager.post(GameEvent.PLAYER_DAMAGED, self.health_comp.get_health(), self.pos) # Pass player pos
            if not self.health_comp.is_alive():
                self.event_manager.post(GameEvent.PLAYER_DIED)
            return True
        return False

    def heal(self, amount: int) -> None:
        self.health_comp.heal(amount)
        self.event_manager.post(GameEvent.PLAYER_HEALTH_GAINED, self.health_comp.get_health())

    def upgrade_weapon(self) -> None:
        current_level = self.shooting_comp.get_weapon_level()
        if current_level < self.max_weapon_level:
            self.shooting_comp.set_weapon_level(current_level + 1)

    def activate_shield(self, duration: float) -> None:
        self._shield_active = True
        self._shield_timer = duration
        self.event_manager.post(GameEvent.PLAYER_SHIELD_ACTIVATED, duration)

    def _on_shield_activated(self, duration: float) -> None:
        pass

    def _on_weapon_upgraded(self, new_level: int) -> None:
        pass

    def _on_health_gained(self, current_health: int) -> None:
        pass

    def is_shield_active(self) -> bool:
        return self._shield_active

    def get_weapon_level(self) -> int:
        return self.shooting_comp.get_weapon_level()


class Enemy(GameObject):
    enemy_type: str
    health_comp: HealthComponent
    score_value: int
    shooting_comp: Optional[ShootingComponent]
    state_machine: Optional[StateMachineComponent]
    bullet_pool: GenericObjectPool
    event_manager: EventManager
    audio_mixer: AudioMixer
    speed: float # Store original speed for chaser logic
    _sway_magnitude: float # Moved from hardcoded
    _sway_speed_factor: float # Moved from hardcoded

    def __init__(self, bullet_pool: GenericObjectPool, event_manager: EventManager, audio_mixer: AudioMixer) -> None:
        super().__init__("enemy_basic", (0, 0)) # Placeholder
        self.enemy_type = "placeholder"
        self.health_comp = HealthComponent(1)
        self.score_value = 0
        self.shooting_comp = None
        self.state_machine = None
        self.bullet_pool = bullet_pool
        self.event_manager = event_manager
        self.audio_mixer = audio_mixer
        self.speed = 0.0

        # Chaser specific attributes
        self._chase_target: Optional[pygame.math.Vector2] = None
        self._chase_lock_threshold_y: float = GameData.SCREEN_HEIGHT / 3

        # Bomber specific attributes
        self._sway_timer: float = 0.0
        self._sway_magnitude = 0.0 # Initialized here, updated in activate
        self._sway_speed_factor = 0.0 # Initialized here, updated in activate


    def activate(self, pos: pygame.math.Vector2, enemy_type_key: str) -> None:
        super().activate()
        enemy_data = GameData.ENEMY_TYPES[enemy_type_key]

        self.enemy_type = enemy_type_key
        self.pos = pygame.math.Vector2(pos)
        self.health_comp.reset(enemy_data["health"])
        self.vel = pygame.math.Vector2(0, enemy_data["speed"])
        self.speed = float(enemy_data["speed"]) # Store base speed
        self.score_value = enemy_data["score"]

        self.image_name = enemy_data["image_name"]
        self.image = ResourceManager.get_image(self.image_name)
        if not self.image:
            self.image = ResourceManager.get_image("placeholder")
        self.rect = self.image.get_rect(center=self.pos)

        # Apply specific enemy type configurations
        self._sway_magnitude = float(enemy_data["sway_magnitude"])
        self._sway_speed_factor = float(enemy_data["sway_speed_factor"])


        if enemy_data["bullet_type"]:
            enemy_bullet_image = "enemy_bullet_normal" if enemy_data["bullet_type"] == "normal" else "enemy_bullet_spread"
            self.shooting_comp = ShootingComponent(
                self, self.bullet_pool, float(enemy_data["fire_rate"]), enemy_data["bullet_type"],
                float(enemy_data["bullet_speed"]), int(enemy_data["bullet_damage"]),
                enemy_bullet_image, self.event_manager, self.audio_mixer, GameData.PLAYER_WEAPON_CONFIGS
            )
        else:
            self.shooting_comp = None

        if self.enemy_type == "basic_fighter":
            self.state_machine = StateMachineComponent("move_down", {
                "move_down": self._state_move_down_and_shoot
            })
        elif self.enemy_type == "heavy_bomber":
            self.state_machine = StateMachineComponent("move_down_sway", {
                "move_down_sway": self._state_move_down_sway_and_shoot
            })
            self._sway_timer = 0.0
        elif self.enemy_type == "chaser":
            self.state_machine = StateMachineComponent("wait_and_track", {
                "wait_and_track": self._state_wait_then_track_player
            })
            self.vel.y = float(GameData.ENEMY_TYPES["chaser"]["speed_initial"]) # Use initial speed
            self._chase_target = None

    def deactivate(self) -> None:
        super().deactivate()
        self.vel = pygame.math.Vector2(0, 0)
        self.shooting_comp = None
        self.state_machine = None
        self._chase_target = None
        self.speed = 0.0

    def update(self, dt: float, player_pos: Optional[pygame.math.Vector2] = None) -> None:
        if not self.is_active():
            return

        self.health_comp.update(dt)
        if not self.health_comp.is_alive():
            self.event_manager.post(GameEvent.ENEMY_DIED, self.score_value, self.pos, is_boss=False)
            self.deactivate()
            return

        if self.state_machine:
            if self.enemy_type == "chaser" and self.state_machine.is_in_state("wait_and_track"):
                self._chase_target = player_pos
            self.state_machine.update(dt, self)

        super().update(dt) # Calls GameObject.update which updates pos and rect

        if self.rect.top > GameData.SCREEN_HEIGHT:
            self.deactivate()

        if self.shooting_comp and self.rect.top < GameData.SCREEN_HEIGHT and self.rect.bottom > 0:
            self.shooting_comp.shoot(pygame.time.get_ticks() / 1000.0)

    def take_damage(self, amount: int) -> bool:
        if self.health_comp.take_damage(amount):
            return True
        return False

    # --- Enemy State Machine Callbacks ---
    def _state_move_down_and_shoot(self, owner: "Enemy", dt: float, timer: float, duration: float) -> None:
        owner.vel.x = 0
        owner.vel.y = owner.speed

    def _state_move_down_sway_and_shoot(self, owner: "Enemy", dt: float, timer: float, duration: float) -> None:
        owner.vel.y = owner.speed
        owner._sway_timer += dt
        owner.vel.x = math.sin(owner._sway_timer * owner._sway_speed_factor) * owner._sway_magnitude

        # Simple bounds check for sway to keep within screen, optional
        # if owner.pos.x < owner.rect.width / 2 or owner.pos.x > GameData.SCREEN_WIDTH - owner.rect.width / 2:
        #    owner._sway_speed_factor *= -1

    def _state_wait_then_track_player(self, owner: "Enemy", dt: float, timer: float, duration: float) -> None:
        chaser_config = GameData.ENEMY_TYPES["chaser"]
        if owner.pos.y < owner._chase_lock_threshold_y:
            owner.vel.y = float(chaser_config["speed_initial"]) # Move down normally
        else:
            if owner._chase_target:
                target_direction = (owner._chase_target - owner.pos).normalize()
                owner.vel = target_direction * float(chaser_config["speed_chasing"])
            else:
                owner.vel = pygame.math.Vector2(0, float(chaser_config["speed_initial"]))


class Boss(Enemy):
    laser_active: bool
    laser_damage_per_frame: float
    laser_duration: float
    laser_timer: float
    _target_pos_x: int
    _move_speed_factor: float
    _boss_start_y: int
    _move_timer: float
    target_y: float
    _is_at_target_y: bool

    def __init__(self, bullet_pool: GenericObjectPool, event_manager: EventManager, audio_mixer: AudioMixer) -> None:
        super().__init__(bullet_pool, event_manager, audio_mixer)
        self.enemy_type = "boss1" # Set enemy_type for Boss
        self.image_name = GameData.BOSS_TYPES["boss1"]["image_name"] # Set image for Boss
        self.image = ResourceManager.get_image(self.image_name)
        if not self.image:
            self.image = ResourceManager.get_image("placeholder")
        self.rect = self.image.get_rect(center=(0,0)) # placeholder rect

        self.laser_active = False
        self.laser_damage_per_frame = 0.0
        self.laser_duration = 0.0
        self.laser_timer = 0.0
        self._target_pos_x = GameData.SCREEN_WIDTH // 2
        self._move_speed_factor = 1.0
        self._boss_start_y = -100

        self.event_manager.register(GameEvent.BOSS_ACTIVATE_LASER, self._on_activate_laser)

    def activate(self, pos: pygame.math.Vector2, boss_type_key: str) -> None:
        super().activate(pos, boss_type_key) # Call parent activate, will use boss_type_key for general enemy fields

        boss_config = GameData.BOSS_TYPES[boss_type_key]
        self.health_comp.reset(boss_config["health"]) # Set max health specifically for boss

        self.shooting_comp = ShootingComponent(
            self, self.bullet_pool, float(boss_config["phase1_fire_rate"]), boss_config["bullet_type_phase1"],
            float(GameData.ENEMY_TYPES["basic_fighter"]["bullet_speed"]), int(GameData.ENEMY_TYPES["basic_fighter"]["bullet_damage"]), # Using basic fighter bullet as a base for phase 1 spread
            "enemy_bullet_normal", self.event_manager, self.audio_mixer, GameData.PLAYER_WEAPON_CONFIGS
        )

        self.state_machine = StateMachineComponent("phase1_move_and_attack", {
            "phase1_move_and_attack": self._state_phase1_move_and_attack,
            "phase2_laser_attack": self._state_phase2_laser_attack
        })
        self._move_timer = 0.0
        self.target_y = GameData.SCREEN_HEIGHT / 4
        self._is_at_target_y = False
        self.vel.y = float(boss_config["speed"])
        self.vel.x = 0.0

        self.laser_active = False
        self.laser_timer = 0.0

    def deactivate(self) -> None:
        super().deactivate()
        self.laser_active = False
        self.laser_timer = 0.0

    def update(self, dt: float, player_pos: Optional[pygame.math.Vector2] = None) -> None:
        if not self.is_active():
            return

        self.health_comp.update(dt)
        if not self.health_comp.is_alive():
            self.event_manager.post(GameEvent.ENEMY_DIED, self.score_value, self.pos, is_boss=True)
            self.deactivate()
            return

        boss_config = GameData.BOSS_TYPES["boss1"] # Assuming current boss is Boss1

        # Phase transition check
        if self.health_comp.get_health() <= boss_config["health"] / 2 and self.state_machine and \
           self.state_machine.current_state == "phase1_move_and_attack":
            self.state_machine.set_state("phase2_laser_attack")
            if self.shooting_comp:
                self.shooting_comp.fire_rate = float(boss_config["phase2_laser_fire_rate"])
                self.shooting_comp.bullet_type = boss_config["bullet_type_phase2"] # Use laser bullet type
            self.vel = pygame.math.Vector2(0, 0)
            self.laser_timer = 0.0

        if self.state_machine:
            self.state_machine.update(dt, self)

        # Only update position via GameObject.update if not currently firing laser
        # and not in a state that explicitly manages its position (e.g. phase 2 stationary)
        if (self.state_machine and not self.state_machine.is_in_state("phase2_laser_attack")) or not self.laser_active:
            super().update(dt) # Calls GameObject.update

        if self.laser_active:
            self.laser_timer += dt
            if self.laser_timer >= self.laser_duration:
                self.laser_active = False

        if self.shooting_comp and self.rect.top < GameData.SCREEN_HEIGHT and self.rect.bottom > 0:
            current_time = pygame.time.get_ticks() / 1000.0
            if self.state_machine and self.state_machine.is_in_state("phase1_move_and_attack"):
                self.shooting_comp.shoot(current_time)
            elif self.state_machine and self.state_machine.is_in_state("phase2_laser_attack") and not self.laser_active:
                self.shooting_comp.shoot(current_time)

    def draw(self, screen: pygame.Surface) -> None:
        super().draw(screen)
        if self.laser_active:
            laser_image = ResourceManager.get_image("enemy_laser")
            if laser_image:
                laser_rect = laser_image.get_rect(midtop=(self.pos.x, self.rect.bottom))
                screen.blit(laser_image, laser_rect)

    # --- Boss State Machine Callbacks ---
    def _state_phase1_move_and_attack(self, owner: "Boss", dt: float, timer: float, duration: float) -> None:
        boss_config = GameData.BOSS_TYPES["boss1"]
        if not owner._is_at_target_y:
            owner.vel.y = float(boss_config["speed"])
            if owner.pos.y >= owner.target_y:
                owner.pos.y = owner.target_y
                owner.vel.y = 0.0
                owner._is_at_target_y = True
        else:
            owner._move_timer += dt
            owner.vel.x = math.sin(owner._move_timer * 0.5) * owner._move_speed_factor * float(boss_config["speed"])
            # Bounce logic for horizontal movement
            if owner.pos.x < owner.rect.width / 2:
                owner.pos.x = owner.rect.width / 2
                owner._move_speed_factor *= -1
            elif owner.pos.x > GameData.SCREEN_WIDTH - owner.rect.width / 2:
                owner.pos.x = GameData.SCREEN_WIDTH - owner.rect.width / 2
                owner._move_speed_factor *= -1


    def _state_phase2_laser_attack(self, owner: "Boss", dt: float, timer: float, duration: float) -> None:
        owner.vel = pygame.math.Vector2(0, 0) # Remain stationary

    def _on_activate_laser(self, boss_instance: "Boss", damage: float, duration: float) -> None:
        if boss_instance == self:
            self.laser_active = True
            self.laser_damage_per_frame = damage
            self.laser_duration = duration
            self.laser_timer = 0.0

    def get_laser_rect(self) -> Optional[pygame.Rect]:
        if self.is_active() and self.laser_active:
            laser_image = ResourceManager.get_image("enemy_laser")
            if laser_image:
                return laser_image.get_rect(midtop=(self.pos.x, self.rect.bottom))
        return None


# --- Particle System ---
class Particle(GameObject):
    pool: Optional[GenericObjectPool] # Changed to Optional
    lifetime: float
    fade_speed: float
    max_lifetime: float

    def __init__(self, pool: Optional[GenericObjectPool] = None) -> None: # Made pool optional
        super().__init__("particle_explosion", (0, 0))
        self.pool = pool
        self.lifetime = 0.0
        self.fade_speed = 0.0
        self.max_lifetime = 0.0

    def activate(self, pos: pygame.math.Vector2, vel: pygame.math.Vector2,
                 lifetime: float, image_name: str, initial_color: Optional[Tuple[int, int, int]] = None) -> None:
        super().activate()
        self.pos = pygame.math.Vector2(pos)
        self.rect.center = (int(pos.x), int(pos.y))
        self.vel = pygame.math.Vector2(vel)
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.image_name = image_name

        self.image = ResourceManager.get_image(image_name)
        if not self.image: # Create a dummy surface if image not found
            self.image = ResourceManager._create_dummy_surface((5,5), initial_color if initial_color else GameData.WHITE, True)
        self.rect = self.image.get_rect(center=self.pos) # Update rect to match image size

        self.image.set_alpha(255) # Reset alpha for pooled particles

    def deactivate(self) -> None:
        super().deactivate()
        self.vel = pygame.math.Vector2(0, 0)
        self.lifetime = 0.0
        self.max_lifetime = 0.0
        if self.image: # Ensure image exists before setting alpha
            self.image.set_alpha(255)

    def update(self, dt: float) -> None:
        if not self.is_active():
            return

        super().update(dt) # Calls GameObject.update
        self.lifetime -= dt

        if self.lifetime < self.max_lifetime * 0.5: # Start fading in the last half of lifetime
            if self.image:
                current_alpha = self.image.get_alpha()
                if current_alpha is not None:
                    fade_amount = 255 / (self.max_lifetime * 0.5) * dt
                    new_alpha = max(0, int(current_alpha - fade_amount))
                    self.image.set_alpha(new_alpha)

        if self.lifetime <= 0 and self.pool: # Added check for self.pool before calling return_obj
            self.pool.return_obj(self)


class ParticleSystemComponent:
    particle_pool: GenericObjectPool
    event_manager: EventManager
    audio_mixer: AudioMixer

    def __init__(self, event_manager: EventManager, audio_mixer: AudioMixer) -> None:
        self.event_manager = event_manager
        self.audio_mixer = audio_mixer
        
        # FIX: The original code had a circular reference:
        # self.particle_pool = GenericObjectPool(lambda: Particle(self.particle_pool), ...)
        # self.particle_pool was not yet assigned when the lambda was executed during GenericObjectPool.__init__
        # Fix involves:
        # 1. Particle.__init__ accepts optional pool.
        # 2. Create the pool with a lambda that creates Particle without a pool.
        # 3. Iterate through initially created particles and set their pool reference.
        # 4. For new particles obtained via get(), set their pool reference immediately.
        self.particle_pool = GenericObjectPool(lambda: Particle(), initial_size=GameData.PARTICLE_POOL_SIZE)
        for particle in self.particle_pool._pool: # Access internal list to set pool for initial objects
            particle.pool = self.particle_pool

        event_manager.register(GameEvent.ENEMY_DIED, self.create_explosion_particles)
        event_manager.register(GameEvent.PLAYER_DAMAGED, self.create_hit_particles)
        event_manager.register(GameEvent.POWERUP_COLLECTED, self.create_collect_particles)

    def update(self, dt: float) -> None:
        for particle in self.particle_pool.get_active():
            particle.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        for particle in self.particle_pool.get_active():
            particle.draw(screen)

    def create_explosion_particles(self, score_value: int, pos: pygame.math.Vector2, is_boss: bool = False) -> None:
        num_particles = 20 if not is_boss else 50
        for _ in range(num_particles):
            speed = random.uniform(50, 150)
            angle = random.uniform(0, 2 * math.pi)
            vel = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * speed
            lifetime = random.uniform(0.5, 1.5)
            particle = self.particle_pool.get(pos, vel, lifetime, "particle_explosion", GameData.ORANGE)
            # particle.pool = self.particle_pool # No longer explicitly needed here if GenericObjectPool.get handles it
        self.audio_mixer.play_sfx("explosion")

    def create_hit_particles(self, current_health: int, player_pos: pygame.math.Vector2) -> None:
        num_particles = 5
        for _ in range(num_particles):
            speed = random.uniform(20, 80)
            angle = random.uniform(0, 2 * math.pi)
            vel = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * speed
            lifetime = random.uniform(0.3, 0.8)
            particle = self.particle_pool.get(player_pos, vel, lifetime, "particle_hit", GameData.WHITE)
            # particle.pool = self.particle_pool # No longer explicitly needed here if GenericObjectPool.get handles it

    def create_collect_particles(self, powerup_type: str, player_pos: pygame.math.Vector2) -> None:
        color_map: Dict[str, Tuple[int, int, int]] = {
            "firepower": GameData.YELLOW,
            "shield": GameData.BLUE,
            "extra_life": GameData.GREEN,
            "score_boost": GameData.WHITE
        }
        color = color_map.get(powerup_type, GameData.WHITE)
        num_particles = 10
        for _ in range(num_particles):
            speed = random.uniform(30, 100)
            angle = random.uniform(math.pi / 2 - 0.5, math.pi / 2 + 0.5)
            vel = pygame.math.Vector2(math.cos(angle), -math.sin(angle)) * speed
            lifetime = random.uniform(0.6, 1.2)
            particle = self.particle_pool.get(player_pos, vel, lifetime, "particle_hit", color)
            # particle.pool = self.particle_pool # No longer explicitly needed here if GenericObjectPool.get handles it


# --- PowerUp System ---

class PowerUp(GameObject):
    pool: Optional[GenericObjectPool] # Changed to Optional
    type: str

    def __init__(self, pool: Optional[GenericObjectPool] = None) -> None: # Made pool optional
        super().__init__("powerup_firepower", (0, 0))
        self.pool = pool
        self.type = ""

    def activate(self, pos: pygame.math.Vector2, powerup_type: str) -> None:
        super().activate()
        self.pos = pygame.math.Vector2(pos)
        self.rect.center = (int(pos.x), int(pos.y))
        self.vel = pygame.math.Vector2(0, GameData.ENEMY_TYPES["basic_fighter"]["speed"] * 0.7)
        self.type = powerup_type

        image_map: Dict[str, str] = {
            "firepower": "powerup_firepower",
            "shield": "powerup_shield",
            "extra_life": "powerup_extra_life",
            "score_boost": "powerup_score_boost"
        }
        self.image_name = image_map.get(powerup_type, "powerup_firepower")
        self.image = ResourceManager.get_image(self.image_name)
        if not self.image: # Fallback for unknown image_name from config
            self.image = ResourceManager.get_image("placeholder")
        self.rect = self.image.get_rect(center=self.pos)

    def deactivate(self) -> None:
        super().deactivate()
        self.vel = pygame.math.Vector2(0, 0)
        self.type = ""

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.is_offscreen():
            if self.pool: # Added check for self.pool before calling return_obj
                self.pool.return_obj(self)


class PowerUpSystem:
    powerup_pool: GenericObjectPool
    event_manager: EventManager
    audio_mixer: AudioMixer

    def __init__(self, event_manager: EventManager, audio_mixer: AudioMixer) -> None:
        self.event_manager = event_manager
        self.audio_mixer = audio_mixer

        # Fix circular dependency for powerup_pool
        self.powerup_pool = GenericObjectPool(lambda: PowerUp(), initial_size=GameData.POWERUP_POOL_SIZE) # Used GameData
        for powerup in self.powerup_pool._pool:
            powerup.pool = self.powerup_pool

        event_manager.register(GameEvent.ENEMY_DIED, self._maybe_spawn_powerup)

    def update(self, dt: float, player: Player) -> None:
        for powerup in self.powerup_pool.get_active():
            powerup.update(dt) # Calls GameObject.update
            # Power-up collision is handled here, as it directly affects player.
            # Spatial grid check could also be used here if power-ups interacted with other things.
            if powerup.is_active() and player.is_active() and powerup.get_collider_rect().colliderect(player.get_collider_rect()):
                self._apply_powerup_effect(powerup.type, player)
                self.powerup_pool.return_obj(powerup)
                self.event_manager.post(GameEvent.POWERUP_COLLECTED, powerup.type, player.pos)
                self.audio_mixer.play_sfx("powerup_collect")

    def draw(self, screen: pygame.Surface) -> None:
        for powerup in self.powerup_pool.get_active():
            powerup.draw(screen)

    def _maybe_spawn_powerup(self, score_value: int, pos: pygame.math.Vector2, is_boss: bool = False) -> None:
        if is_boss:
            self.spawn_powerup(pos, "firepower")
            return

        if random.random() < GameData.POWERUP_PROBABILITY:
            chosen_type = random.choice(GameData.POWERUP_TYPES)
            self.spawn_powerup(pos, chosen_type)

    def spawn_powerup(self, pos: pygame.math.Vector2, powerup_type: str) -> None:
        self.powerup_pool.get(pos, powerup_type)

    def _apply_powerup_effect(self, powerup_type: str, player: Player) -> None:
        effect_data = GameData.POWERUP_EFFECTS.get(powerup_type)
        if not effect_data:
            return

        action = effect_data["action"]
        if action == "upgrade_weapon":
            player.upgrade_weapon()
        elif action == "activate_shield":
            player.activate_shield(float(effect_data["duration"]))
        elif action == "heal":
            player.heal(int(effect_data["amount"]))
        elif action == "add_score":
            self.event_manager.post(GameEvent.SCORE_CHANGED, int(effect_data["amount"]))

    def reset(self) -> None:
        self.powerup_pool.reset()


# --- Wave Manager ---
class WaveManager:
    enemy_pool: GenericObjectPool
    boss_pool: GenericObjectPool
    player_ref: "Player" # Player is passed as reference, assumed to exist
    event_manager: EventManager
    wave_timer: float
    current_wave: int
    enemies_remaining_to_spawn_current_wave: List[Tuple[str, float]] # (enemy_type_key, time_to_spawn)
    spawned_enemies: List[Enemy] # Keep track of currently active enemies

    def __init__(self, enemy_pool: GenericObjectPool, boss_pool: GenericObjectPool,
                 player_ref: "Player", event_manager: EventManager) -> None:
        self.enemy_pool = enemy_pool
        self.boss_pool = boss_pool
        self.player_ref = player_ref
        self.event_manager = event_manager

        self.wave_timer = 0.0
        self.current_wave = 0
        self.enemies_remaining_to_spawn_current_wave = []
        self.spawned_enemies = []

        self.event_manager.register(GameEvent.ENEMY_DIED, self._on_enemy_died_wave)

    def reset(self) -> None:
        self.wave_timer = 0.0
        self.current_wave = 0
        self.enemies_remaining_to_spawn_current_wave = []
        self.spawned_enemies = []
        self.enemy_pool.reset()
        self.boss_pool.reset()

    def update(self, dt: float) -> None:
        self.wave_timer += dt

        # Remove inactive enemies from tracking list
        self.spawned_enemies = [e for e in self.spawned_enemies if e.is_active()]

        # Process staggered enemy spawns
        new_enemies_to_spawn: List[Tuple[str, float]] = []
        spawn_now_list: List[Tuple[str, pygame.math.Vector2]] = [] # To store (enemy_type, spawn_pos)
        for enemy_data, time_to_spawn in self.enemies_remaining_to_spawn_current_wave:
            if time_to_spawn <= self.wave_timer:
                spawn_pos = pygame.math.Vector2(random.uniform(50, GameData.SCREEN_WIDTH - 50), -random.uniform(50, 100))
                spawn_now_list.append((enemy_data, spawn_pos))
            else:
                new_enemies_to_spawn.append((enemy_data, time_to_spawn))
        self.enemies_remaining_to_spawn_current_wave = new_enemies_to_spawn

        for enemy_type, spawn_pos in spawn_now_list:
            enemy = self.enemy_pool.get(spawn_pos, enemy_type)
            if enemy:
                self.spawned_enemies.append(enemy)

        # Trigger next wave if all current enemies spawned and killed, and interval passed
        if not self.spawned_enemies and not self.enemies_remaining_to_spawn_current_wave and self.wave_timer >= GameData.WAVE_INTERVAL:
            self.current_wave += 1
            self.wave_timer = 0.0 # Reset timer for next wave countdown

            if (self.current_wave - 1) % GameData.BOSS_SPAWN_INTERVAL_WAVES == 0 and self.current_wave > 1:
                self._spawn_boss()
            else:
                self._spawn_wave(self.current_wave)

    def _on_enemy_died_wave(self, score_value: int, pos: pygame.math.Vector2, is_boss: bool = False) -> None:
        # The `spawned_enemies` list is cleaned up in `update`.
        # No explicit counter is needed here if `spawned_enemies` correctly reflects active enemies.
        pass

    def _spawn_wave(self, wave_number: int) -> None:
        wave_config = GameData.WAVE_CONFIG

        num_basic = wave_config["initial_basic_fighters"] + math.floor(wave_number * wave_config["basic_fighter_increment"])
        num_bomber = wave_config["initial_heavy_bombers"] + math.floor(wave_number * wave_config["heavy_bomber_increment"])
        num_chaser = wave_config["initial_chasers"] + math.floor(wave_number * wave_config["chaser_increment"])

        enemies_to_schedule: List[Tuple[str, float]] = [] # (enemy_type_key, spawn_delay_s)

        current_delay = 0.0
        for _ in range(num_basic):
            current_delay += random.uniform(0.1, 0.5)
            enemies_to_schedule.append(("basic_fighter", current_delay))
        for _ in range(num_bomber):
            current_delay += random.uniform(0.5, 1.0)
            enemies_to_schedule.append(("heavy_bomber", current_delay))
        for _ in range(num_chaser):
            current_delay += random.uniform(0.7, 1.5)
            enemies_to_schedule.append(("chaser", current_delay))

        # Sort by delay to ensure correct staggering
        enemies_to_schedule.sort(key=lambda x: x[1])
        self.enemies_remaining_to_spawn_current_wave = enemies_to_schedule


    def _spawn_boss(self) -> None:
        boss_pos = pygame.math.Vector2(GameData.SCREEN_WIDTH // 2, -100)
        boss = self.boss_pool.get(boss_pos, "boss1")
        if boss:
            self.spawned_enemies.append(boss)

    def get_active_enemies(self) -> List[Enemy]:
        # Returns all active enemies from both pools for iteration in game loop
        return self.enemy_pool.get_active() + self.boss_pool.get_active()


# --- Score Manager ---
class ScoreManager:
    current_score: int
    high_scores: List[Dict[str, Any]]
    event_manager: EventManager

    def __init__(self, event_manager: EventManager) -> None:
        self.current_score = 0
        self.high_scores = []
        self.event_manager = event_manager
        self._load_high_scores()

        event_manager.register(GameEvent.ENEMY_DIED, self._on_enemy_died)
        event_manager.register(GameEvent.SCORE_CHANGED, self._on_score_changed)

    def reset(self) -> None:
        self.current_score = 0

    def _on_enemy_died(self, score_value: int, pos: pygame.math.Vector2, is_boss: bool = False) -> None:
        self.add_score(score_value)

    def _on_score_changed(self, amount: int) -> None:
        self.add_score(amount)

    def add_score(self, amount: int) -> None:
        self.current_score += amount

    def get_current_score(self) -> int:
        return self.current_score

    def _load_high_scores(self) -> None:
        if os.path.exists(GameData.HIGH_SCORE_FILE):
            with open(GameData.HIGH_SCORE_FILE, 'r', encoding='utf-8') as f:
                try:
                    self.high_scores = json.load(f)
                    self.high_scores.sort(key=lambda x: x['score'], reverse=True)
                except json.JSONDecodeError:
                    self.high_scores = []
        else:
            self.high_scores = []

    def save_high_scores(self) -> None:
        with open(GameData.HIGH_SCORE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.high_scores, f, ensure_ascii=False, indent=4)

    def add_high_score(self, name: str, score: int) -> None:
        self.high_scores.append({'name': name, 'score': score})
        self.high_scores.sort(key=lambda x: x['score'], reverse=True)
        self.high_scores = self.high_scores[:GameData.HIGH_SCORE_LIMIT] # Used GameData
        self.save_high_scores()

    def get_high_scores(self) -> List[Dict[str, Any]]:
        return self.high_scores


# --- UI Component ---
class UIComponent:
    screen: pygame.Surface
    font_large: pygame.font.Font
    font_medium: pygame.font.Font
    font_small: pygame.font.Font
    font_xsmall: pygame.font.Font
    player_health_text: str
    player_score_text: str
    player_weapon_level_text: str
    current_input_text: str
    audio_mixer: AudioMixer

    def __init__(self, screen: pygame.Surface, audio_mixer: AudioMixer) -> None:
        self.screen = screen
        self.font_large = ResourceManager.get_font("Arial", 48) or pygame.font.Font(None, 48)
        self.font_medium = ResourceManager.get_font("Arial", 36) or pygame.font.Font(None, 36)
        self.font_small = ResourceManager.get_font("Arial", 24) or pygame.font.Font(None, 24)
        self.font_xsmall = ResourceManager.get_font("Arial", 18) or pygame.font.Font(None, 18)
        self.audio_mixer = audio_mixer

        self.player_health_text = ""
        self.player_score_text = ""
        self.player_weapon_level_text = ""
        self.current_input_text = ""

    def update_hud(self, health: int, score: int, weapon_level: int) -> None:
        self.player_health_text = f"HP: {health}"
        self.player_score_text = f"Score: {score}"
        self.player_weapon_level_text = f"Weapon: Lv{weapon_level}"

    def draw_hud(self, player_ref: Optional["Player"]) -> None:
        # Only draw HUD if player is active in game
        if player_ref and player_ref.is_active():
            health_surf = self.font_small.render(self.player_health_text, True, GameData.GREEN)
            score_surf = self.font_small.render(self.player_score_text, True, GameData.WHITE)
            weapon_surf = self.font_small.render(self.player_weapon_level_text, True, GameData.YELLOW)

            self.screen.blit(health_surf, (10, 10))
            self.screen.blit(score_surf, (GameData.SCREEN_WIDTH - score_surf.get_width() - 10, 10))
            self.screen.blit(weapon_surf, (10, 40))

    def draw_rules_screen(self) -> None:
        self.screen.fill(GameData.BLACK)
        title_surf = self.font_large.render(GameData.GAME_TITLE, True, GameData.WHITE)
        rules_title_surf = self.font_medium.render("Game Rules", True, GameData.YELLOW)

        self.screen.blit(title_surf, title_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 100)))
        self.screen.blit(rules_title_surf, rules_title_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 200)))

        rules_text = [
            "駕駛飛船向上飛行，消滅敵機，躲避子彈。",
            "移動: W, A, S, D 或方向鍵",
            "射擊: 空格鍵",
            "暫停: ESC",
            "",
            "擊敗敵人可獲得分數，並有機會掉落道具。",
            "火力強化: 提升武器等級，增加子彈數量和穿透力。",
            "護盾: 5秒無敵狀態。",
            "額外生命: 恢復1點生命值。",
            "分數加成: 立即獲得額外分數。",
            "",
            "生命值歸零則遊戲結束。",
            "",
            "按任意鍵開始遊戲..."
        ]

        y_offset = 250
        for line in rules_text:
            line_surf = self.font_small.render(line, True, GameData.LIGHT_GREY)
            self.screen.blit(line_surf, line_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, y_offset)))
            y_offset += 30

    def draw_main_menu(self, menu_selection: int) -> None:
        self.screen.fill(GameData.BLACK)
        title_surf = self.font_large.render(GameData.GAME_TITLE, True, GameData.WHITE)
        self.screen.blit(title_surf, title_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 200)))

        menu_options = ["開始遊戲", "設定", "高分榜", "離開"]
        self.draw_menu_options(menu_options, menu_selection, start_y=GameData.MAIN_MENU_START_Y_OFFSET, line_height=GameData.MENU_LINE_HEIGHT)

    def draw_options_menu(self, menu_selection: int, sfx_volume: float, music_volume: float) -> None:
        self.screen.fill(GameData.BLACK)
        title_surf = self.font_medium.render("設定", True, GameData.WHITE)
        self.screen.blit(title_surf, title_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 100)))

        sfx_vol_percent = int(sfx_volume * 100)
        music_vol_percent = int(music_volume * 100)

        menu_options = [
            f"音效音量: {sfx_vol_percent}%",
            f"背景音樂音量: {music_vol_percent}%",
            "返回"
        ]
        self.draw_menu_options(menu_options, menu_selection, start_y=200, line_height=GameData.MENU_LINE_HEIGHT)

    def draw_pause_menu(self, menu_selection: int) -> None:
        overlay = pygame.Surface((GameData.SCREEN_WIDTH, GameData.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        title_surf = self.font_medium.render("遊戲暫停", True, GameData.WHITE)
        self.screen.blit(title_surf, title_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 200)))

        menu_options = ["繼續遊戲", "設定", "返回主菜單"]
        self.draw_menu_options(menu_options, menu_selection, start_y=GameData.PAUSE_MENU_START_Y_OFFSET, line_height=GameData.MENU_LINE_HEIGHT)

    def draw_game_over_screen(self, final_score: int, high_scores: List[Dict[str, Any]],
                             input_mode: bool, menu_selection: int) -> None:
        self.screen.fill(GameData.BLACK)
        game_over_surf = self.font_large.render("遊戲結束", True, GameData.RED)
        final_score_surf = self.font_medium.render(f"最終分數: {final_score}", True, GameData.WHITE)

        self.screen.blit(game_over_surf, game_over_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 100)))
        self.screen.blit(final_score_surf, final_score_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 180)))

        if input_mode:
            input_prompt = self.font_small.render("請輸入姓名:", True, GameData.YELLOW)
            input_text_surf = self.font_medium.render(self.current_input_text + "_", True, GameData.WHITE)

            self.screen.blit(input_prompt, input_prompt.get_rect(center=(GameData.SCREEN_WIDTH // 2, 250)))
            self.screen.blit(input_text_surf, input_text_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 300)))
        else:
            high_score_title_surf = self.font_medium.render("高分榜", True, GameData.YELLOW)
            self.screen.blit(high_score_title_surf, high_score_title_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, GameData.GAMEOVER_SCORES_TITLE_Y_OFFSET)))

            y_offset = GameData.GAMEOVER_SCORES_START_Y_OFFSET
            for i, entry in enumerate(high_scores):
                score_text = f"{i + 1}. {entry['name']:<10} {entry['score']:>6}"
                score_surf = self.font_small.render(score_text, True, GameData.WHITE)
                self.screen.blit(score_surf, score_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, y_offset)))
                y_offset += 30

            menu_options = ["重新開始", "返回主菜單"]
            self.draw_menu_options(menu_options, menu_selection, start_y=y_offset + GameData.GAMEOVER_MENU_OFFSET_FROM_SCORES, line_height=GameData.MENU_LINE_HEIGHT, text_color=GameData.LIGHT_GREY, selected_color=GameData.YELLOW)

    def draw_high_score_screen(self, high_scores: List[Dict[str, Any]]) -> None:
        self.screen.fill(GameData.BLACK)
        title_surf = self.font_large.render("高分榜", True, GameData.YELLOW)
        self.screen.blit(title_surf, title_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, 100)))

        y_offset = 180
        if not high_scores:
            no_scores_surf = self.font_small.render("目前無紀錄", True, GameData.LIGHT_GREY)
            self.screen.blit(no_scores_surf, no_scores_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, y_offset)))
            y_offset += 30
        else:
            for i, entry in enumerate(high_scores):
                score_text = f"{i + 1}. {entry['name']:<10} {entry['score']:>6}"
                score_surf = self.font_small.render(score_text, True, GameData.WHITE)
                self.screen.blit(score_surf, score_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, y_offset)))
                y_offset += 30

        back_option = self.font_small.render("按任意鍵返回主菜單", True, GameData.LIGHT_GREY)
        self.screen.blit(back_option, back_option.get_rect(center=(GameData.SCREEN_WIDTH // 2, GameData.SCREEN_HEIGHT - 50)))

    def draw_menu_options(self, options: List[str], selected_index: int,
                          start_y: int, line_height: int,
                          text_color: Tuple[int, int, int] = GameData.LIGHT_GREY,
                          selected_color: Tuple[int, int, int] = GameData.YELLOW) -> None:
        for i, option in enumerate(options):
            color = selected_color if i == selected_index else text_color
            text_surf = self.font_medium.render(option, True, color)
            self.screen.blit(text_surf, text_surf.get_rect(center=(GameData.SCREEN_WIDTH // 2, start_y + i * line_height)))


# --- Spatial Partitioning (Spatial Grid) ---
class SpatialGrid:
    cell_size: int
    num_cols: int
    num_rows: int
    grid: Dict[Tuple[int, int], Set[GameObject]] # (col, row) -> set of objects

    def __init__(self, screen_width: int, screen_height: int, cell_size: int) -> None:
        self.cell_size = cell_size
        self.num_cols = (screen_width + cell_size - 1) // cell_size
        self.num_rows = (screen_height + cell_size - 1) // cell_size
        self.grid = {}

    def _get_cells_for_rect(self, rect: pygame.Rect) -> Set[Tuple[int, int]]:
        min_col = max(0, rect.left // self.cell_size)
        max_col = min(self.num_cols - 1, rect.right // self.cell_size)
        min_row = max(0, rect.top // self.cell_size)
        max_row = min(self.num_rows - 1, rect.bottom // self.cell_size)

        cells = set()
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cells.add((col, row))
        return cells

    def add_object(self, obj: GameObject) -> None:
        """Adds or updates an object's position in the grid."""
        if not obj.is_active():
            # If object is not active, ensure it's removed from grid.
            self.remove_object(obj)
            return

        current_cells = self._get_cells_for_rect(obj.get_collider_rect())

        # If the object has moved to new cells, update its presence
        cells_to_remove = obj._grid_cells - current_cells
        cells_to_add = current_cells - obj._grid_cells

        for cell_coord in cells_to_remove:
            if cell_coord in self.grid:
                self.grid[cell_coord].discard(obj)
                if not self.grid[cell_coord]:
                    del self.grid[cell_coord] # Remove empty sets

        for cell_coord in cells_to_add:
            if cell_coord not in self.grid:
                self.grid[cell_coord] = set()
            self.grid[cell_coord].add(obj)

        obj._grid_cells = current_cells # Update object's internal record of its cells

    def remove_object(self, obj: GameObject) -> None:
        """Removes an object from all cells it currently occupies."""
        for cell_coord in obj._grid_cells:
            if cell_coord in self.grid:
                self.grid[cell_coord].discard(obj)
                if not self.grid[cell_coord]:
                    del self.grid[cell_coord]
        obj._grid_cells = set() # Clear object's internal record

    def clear(self) -> None:
        """Clears all objects from the grid."""
        self.grid.clear()


# --- Parallax Scrolling Component ---
class ParallaxScrollingComponent:
    layers: List[Dict[str, Any]]

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.layers = []

        self.bg_far_image = ResourceManager.get_image("bg_stars_far") or ResourceManager._create_dummy_surface((screen_width, screen_height * 2), GameData.BLACK, True)
        self.bg_near_image = ResourceManager.get_image("bg_stars_near") or ResourceManager._create_dummy_surface((screen_width, screen_height * 2), GameData.BLACK, True)

        self.layers.append({
            "image": self.bg_far_image,
            "speed_factor": 0.5,
            "y_offset": 0.0
        })
        self.layers.append({
            "image": self.bg_near_image,
            "speed_factor": 1.0,
            "y_offset": 0.0
        })

    def update(self, dt: float) -> None:
        for layer in self.layers:
            layer["y_offset"] += GameData.BASE_BACKGROUND_SCROLL_SPEED * layer["speed_factor"] * dt
            # Loop background image seamlessly
            # The image height is twice the screen height, so it takes two images to fill the screen
            # we need to make sure the offset wraps around correctly so the scrolling is continuous.
            if layer["y_offset"] >= layer["image"].get_height() / 2:
                layer["y_offset"] -= layer["image"].get_height() / 2
            elif layer["y_offset"] < -layer["image"].get_height() / 2: # handle negative speeds
                layer["y_offset"] += layer["image"].get_height() / 2


    def draw(self, screen: pygame.Surface) -> None:
        for layer in self.layers:
            # Draw the image twice to create a seamless loop
            screen.blit(layer["image"], (0, int(layer["y_offset"] - layer["image"].get_height() / 2)))
            screen.blit(layer["image"], (0, int(layer["y_offset"] + layer["image"].get_height() / 2)))


# --- Game Core Logic (Game Class / State Machine) ---
class Game:
    _instance: Optional["Game"] = None

    screen: pygame.Surface
    clock: pygame.time.Clock
    running: bool
    event_manager: EventManager
    audio_mixer: AudioMixer
    ui_manager: UIComponent
    score_manager: ScoreManager
    particle_system: ParticleSystemComponent
    spatial_grid: SpatialGrid # No longer Optional
    parallax_background: ParallaxScrollingComponent # No longer Optional

    # Core game component pools - no longer Optional, always initialized
    player_bullet_pool: GenericObjectPool
    enemy_bullet_pool: GenericObjectPool
    enemy_pool: GenericObjectPool
    boss_pool: GenericObjectPool
    powerup_system: PowerUpSystem
    wave_manager: WaveManager

    # Player instance - it's a single object, can be active/inactive
    player: Player # Changed to non-Optional, deactivated when not in gameplay

    game_state: GameState
    state_handlers: Dict[GameState, Callable[[List[pygame.event.Event], float], None]]
    menu_selection: int
    game_over_input_mode: bool

    _current_bg_music_name: Optional[str]


    @staticmethod
    def get_instance() -> "Game":
        if Game._instance is None:
            Game._instance = Game()
        return Game._instance

    def __init__(self) -> None:
        if Game._instance is not None:
            raise Exception("This class is a singleton!")
        Game._instance = self

        pygame.init()
        pygame.font.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((GameData.SCREEN_WIDTH, GameData.SCREEN_HEIGHT))
        pygame.display.set_caption(GameData.GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        ResourceManager.init_resources()

        # Initialize spatial_grid and parallax_background first,
        # as other components (via Activatable.deactivate) might depend on them during their own initialization.
        self.spatial_grid = SpatialGrid(GameData.SCREEN_WIDTH, GameData.SCREEN_HEIGHT, cell_size=64)
        self.parallax_background = ParallaxScrollingComponent(GameData.SCREEN_WIDTH, GameData.SCREEN_HEIGHT)

        self.event_manager = EventManager()
        self.audio_mixer = AudioMixer()
        self.ui_manager = UIComponent(self.screen, self.audio_mixer)
        self.score_manager = ScoreManager(self.event_manager)
        self.particle_system = ParticleSystemComponent(self.event_manager, self.audio_mixer) # This now runs after spatial_grid is initialized


        # Initialize all core game components/pools (no longer Optional)
        # FIX: Resolve circular dependency for player_bullet_pool
        self.player_bullet_pool = GenericObjectPool(lambda: Bullet(), initial_size=GameData.PLAYER_BULLET_POOL_SIZE)
        for bullet in self.player_bullet_pool._pool:
            bullet.bullet_pool = self.player_bullet_pool

        # FIX: Resolve circular dependency for enemy_bullet_pool
        self.enemy_bullet_pool = GenericObjectPool(lambda: Bullet(), initial_size=GameData.ENEMY_BULLET_POOL_SIZE)
        for bullet in self.enemy_bullet_pool._pool:
            bullet.bullet_pool = self.enemy_bullet_pool

        self.enemy_pool = GenericObjectPool(lambda: Enemy(self.enemy_bullet_pool, self.event_manager, self.audio_mixer), initial_size=GameData.ENEMY_POOL_SIZE)
        self.boss_pool = GenericObjectPool(lambda: Boss(self.enemy_bullet_pool, self.event_manager, self.audio_mixer), initial_size=GameData.BOSS_POOL_SIZE)
        self.player = Player(self.player_bullet_pool, self.event_manager, self.audio_mixer) # Player created, but not yet active
        self.powerup_system = PowerUpSystem(self.event_manager, self.audio_mixer)
        self.wave_manager = WaveManager(self.enemy_pool, self.boss_pool, self.player, self.event_manager) # Pass player instance directly

        self.game_state = GameState.RULES
        self.state_handlers = {
            GameState.RULES: self._handle_rules_state,
            GameState.MAIN_MENU: self._handle_main_menu_state,
            GameState.OPTIONS: self._handle_options_state,
            GameState.GAMEPLAY: self._handle_gameplay_state,
            GameState.PAUSE_MENU: self._handle_pause_menu_state,
            GameState.GAME_OVER: self._handle_game_over_state,
            GameState.HIGH_SCORES: self._handle_high_scores_state,
        }
        self.menu_selection = 0
        self.game_over_input_mode = False

        self._current_bg_music_name = None

        self.event_manager.register(GameEvent.PLAYER_DIED, self._on_player_died)
        self.event_manager.register(GameEvent.GAME_START, self._on_game_start)

        self._reset_game_state_dependent_components() # Initial reset to ensure clean state at start

    def _reset_game_state_dependent_components(self) -> None:
        """Resets all game components that depend on a fresh game state."""
        self.player.deactivate() # Deactivate player when not in active gameplay
        self.player_bullet_pool.reset()
        self.enemy_bullet_pool.reset()
        self.enemy_pool.reset()
        self.boss_pool.reset()
        self.powerup_system.reset()
        self.wave_manager.reset()
        self.spatial_grid.clear() # Clear the entire grid
        self.particle_system.particle_pool.reset()
        self.score_manager.reset()

    def _play_music(self, name: str) -> None:
        if self._current_bg_music_name != name:
            self.audio_mixer.stop_music()
            self.audio_mixer.play_music(name)
            self._current_bg_music_name = name

    def _stop_music(self) -> None:
        self.audio_mixer.stop_music()
        self._current_bg_music_name = None

    # --- Game State Handling ---
    def _handle_rules_state(self, events: List[pygame.event.Event], dt: float) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game_state = GameState.MAIN_MENU
                self.menu_selection = 0
                self._play_music("main_menu_music")
                self.audio_mixer.play_sfx("menu_select")
                break
        self.ui_manager.draw_rules_screen()

    def _handle_main_menu_state(self, events: List[pygame.event.Event], dt: float) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.audio_mixer.play_sfx("menu_navigate")
                if event.key == pygame.K_UP:
                    self.menu_selection = (self.menu_selection - 1) % 4
                elif event.key == pygame.K_DOWN:
                    self.menu_selection = (self.menu_selection + 1) % 4
                elif event.key == pygame.K_RETURN:
                    self.audio_mixer.play_sfx("menu_select")
                    if self.menu_selection == 0:  # Start Game
                        self.game_state = GameState.GAMEPLAY
                        self.event_manager.post(GameEvent.GAME_START) # This will call _on_game_start
                    elif self.menu_selection == 1:  # Options
                        self.game_state = GameState.OPTIONS
                        self.menu_selection = 0
                    elif self.menu_selection == 2:  # High Scores
                        self.game_state = GameState.HIGH_SCORES
                        self.score_manager._load_high_scores()
                    elif self.menu_selection == 3:  # Exit
                        self.running = False
        self.ui_manager.draw_main_menu(self.menu_selection)

    def _handle_options_state(self, events: List[pygame.event.Event], dt: float) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.audio_mixer.play_sfx("menu_navigate")
                if event.key == pygame.K_UP:
                    self.menu_selection = (self.menu_selection - 1) % 3
                elif event.key == pygame.K_DOWN:
                    self.menu_selection = (self.menu_selection + 1) % 3
                elif event.key == pygame.K_LEFT:
                    if self.menu_selection == 0:
                        self.audio_mixer.set_sfx_volume(self.audio_mixer.sfx_volume - 0.1)
                    elif self.menu_selection == 1:
                        self.audio_mixer.set_music_volume(self.audio_mixer.music_volume - 0.1)
                elif event.key == pygame.K_RIGHT:
                    if self.menu_selection == 0:
                        self.audio_mixer.set_sfx_volume(self.audio_mixer.sfx_volume + 0.1)
                    elif self.menu_selection == 1:
                        self.audio_mixer.set_music_volume(self.audio_mixer.music_volume + 0.1)
                elif event.key == pygame.K_RETURN:
                    self.audio_mixer.play_sfx("menu_select")
                    if self.menu_selection == 2:
                        self.game_state = GameState.MAIN_MENU
                        self.menu_selection = 0
        self.ui_manager.draw_options_menu(self.menu_selection, self.audio_mixer.sfx_volume, self.audio_mixer.music_volume)

    def _handle_gameplay_state(self, events: List[pygame.event.Event], dt: float) -> None:
        # All core components (pools, managers) are guaranteed to exist as non-Optional.
        # Player is guaranteed to be active after _on_game_start.

        # Handle player input
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game_state = GameState.PAUSE_MENU
                self.menu_selection = 0
                self.audio_mixer.pause_music()
                self.audio_mixer.play_sfx("menu_select")
                return # Exit early after state change
            self.player.input_comp.handle_input(event)

        # Update all active objects and add/update them in the spatial grid
        self.parallax_background.update(dt)

        self.player.update(dt)
        self.spatial_grid.add_object(self.player) # Update player in grid

        self.wave_manager.update(dt)
        for enemy in self.wave_manager.get_active_enemies():
            enemy.update(dt, player_pos=self.player.pos) # Player position for chaser logic
            self.spatial_grid.add_object(enemy) # Update enemy in grid

        self.powerup_system.update(dt, self.player) # Powerup-player collision handled internally
        for powerup in self.powerup_system.powerup_pool.get_active():
            self.spatial_grid.add_object(powerup) # Update powerup in grid

        for bullet in self.player_bullet_pool.get_active():
            bullet.update(dt)
            self.spatial_grid.add_object(bullet) # Update player bullet in grid

        for bullet in self.enemy_bullet_pool.get_active():
            bullet.update(dt)
            self.spatial_grid.add_object(bullet) # Update enemy bullet in grid

        self.particle_system.update(dt)

        # Perform collision checks using the spatial grid
        self._perform_collision_checks()

        self.ui_manager.update_hud(
            self.player.health_comp.get_health(),
            self.score_manager.get_current_score(),
            self.player.shooting_comp.get_weapon_level()
        )

        self.screen.fill(GameData.BLACK)
        self.parallax_background.draw(self.screen)

        for obj in self.powerup_system.powerup_pool.get_active():
            obj.draw(self.screen)
        for enemy in self.wave_manager.get_active_enemies():
            enemy.draw(self.screen)
        for bullet in self.player_bullet_pool.get_active():
            bullet.draw(self.screen)
        for bullet in self.enemy_bullet_pool.get_active():
            bullet.draw(self.screen)
        self.player.draw(self.screen) # Player draws last to be on top
        self.particle_system.draw(self.screen)

        self.ui_manager.draw_hud(self.player)

    def _perform_collision_checks(self) -> None:
        """
        Performs collision checks between active GameObjects using the spatial grid.
        This iterates through cells and checks pairs within each cell.
        """
        processed_pairs: Set[Tuple[int, int]] = set() # To avoid checking the same pair twice

        for objects_in_cell in self.spatial_grid.grid.values():
            cell_objects = list(objects_in_cell) # Convert to list for indexed access and iteration

            for i, obj1 in enumerate(cell_objects):
                for j in range(i + 1, len(cell_objects)):
                    obj2 = cell_objects[j]

                    if not obj1.is_active() or not obj2.is_active():
                        continue

                    # Create a canonical pair ID to prevent duplicate checks
                    id1, id2 = id(obj1), id(obj2)
                    if id1 > id2: id1, id2 = id2, id1 # Ensure consistent order
                    if (id1, id2) in processed_pairs:
                        continue
                    processed_pairs.add((id1, id2))

                    self._resolve_collision(obj1, obj2)

        # Handle Boss Laser separately as it's not a standard GameObject in the grid
        for enemy in self.wave_manager.get_active_enemies():
            if isinstance(enemy, Boss) and enemy.laser_active:
                laser_rect = enemy.get_laser_rect()
                if laser_rect and self.player.is_active() and self.player.get_collider_rect().colliderect(laser_rect):
                    self.player.take_damage(enemy.laser_damage_per_frame)


    def _resolve_collision(self, obj1: GameObject, obj2: GameObject) -> None:
        """Resolves collision between two game objects based on their types."""
        # Ensure objects are actually colliding by rects
        if not obj1.get_collider_rect().colliderect(obj2.get_collider_rect()):
            return

        # Player vs. Enemy or Enemy Bullet
        if isinstance(obj1, Player) or isinstance(obj2, Player):
            player = obj1 if isinstance(obj1, Player) else obj2
            other_obj = obj2 if isinstance(obj1, Player) else obj1

            if not player.is_active() or player.health_comp.is_invincible():
                return

            if isinstance(other_obj, Enemy): # Player vs. Enemy ship
                if not isinstance(other_obj, Boss): # Boss collision handled by laser, direct collision is rare
                    player.take_damage(1) # Player takes damage
                    # Enemy might also take damage on contact, or be destroyed. For simplicity, make enemy die.
                    if other_obj.take_damage(1): # Enemy takes 1 damage from player collision
                         self.particle_system.create_explosion_particles(0, other_obj.pos, is_boss=isinstance(other_obj, Boss))

            elif isinstance(other_obj, Bullet) and other_obj.shooter_type != "Player": # Player vs. Enemy Bullet
                if player.take_damage(other_obj.damage):
                    self.enemy_bullet_pool.return_obj(other_obj)

        # Player Bullet vs. Enemy
        elif isinstance(obj1, Bullet) and obj1.shooter_type == "Player" and isinstance(obj2, Enemy):
            player_bullet = obj1
            enemy = obj2
            if enemy.take_damage(player_bullet.damage):
                self.particle_system.create_explosion_particles(0, enemy.pos, is_boss=isinstance(enemy, Boss))
            if not player_bullet.piercing:
                self.player_bullet_pool.return_obj(player_bullet)

        elif isinstance(obj2, Bullet) and obj2.shooter_type == "Player" and isinstance(obj1, Enemy):
            player_bullet = obj2
            enemy = obj1
            if enemy.take_damage(player_bullet.damage):
                self.particle_system.create_explosion_particles(0, enemy.pos, is_boss=isinstance(enemy, Boss))
            if not player_bullet.piercing:
                self.player_bullet_pool.return_obj(player_bullet)


    def _handle_pause_menu_state(self, events: List[pygame.event.Event], dt: float) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.audio_mixer.play_sfx("menu_navigate")
                if event.key == pygame.K_UP:
                    self.menu_selection = (self.menu_selection - 1) % 3
                elif event.key == pygame.K_DOWN:
                    self.menu_selection = (self.menu_selection + 1) % 3
                elif event.key == pygame.K_RETURN:
                    self.audio_mixer.play_sfx("menu_select")
                    if self.menu_selection == 0:  # Resume Game
                        self.game_state = GameState.GAMEPLAY
                        self.audio_mixer.unpause_music()
                        self.event_manager.post(GameEvent.GAME_RESUMED)
                    elif self.menu_selection == 1:  # Options
                        self.game_state = GameState.OPTIONS
                        self.menu_selection = 0
                    elif self.menu_selection == 2:  # Return to Main Menu
                        self.game_state = GameState.MAIN_MENU
                        self.menu_selection = 0
                        self._stop_music()
                        self._play_music("main_menu_music")
                        self._reset_game_state_dependent_components() # Reset all game objects

        self.screen.fill(GameData.BLACK)
        self.parallax_background.draw(self.screen)

        for obj in self.powerup_system.powerup_pool.get_active():
            obj.draw(self.screen)
        for enemy in self.wave_manager.get_active_enemies():
            enemy.draw(self.screen)
        for bullet in self.player_bullet_pool.get_active():
            bullet.draw(self.screen)
        for bullet in self.enemy_bullet_pool.get_active():
            bullet.draw(self.screen)
        if self.player.is_active(): # Draw player only if active
            self.player.draw(self.screen)
        self.particle_system.draw(self.screen)

        self.ui_manager.draw_pause_menu(self.menu_selection)

    def _handle_game_over_state(self, events: List[pygame.event.Event], dt: float) -> None:
        final_score = self.score_manager.get_current_score()
        high_scores = self.score_manager.get_high_scores()

        if self.game_over_input_mode:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        self.ui_manager.current_input_text = self.ui_manager.current_input_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        player_name = self.ui_manager.current_input_text.strip()
                        if not player_name:
                            player_name = "UNK"
                        self.score_manager.add_high_score(player_name, final_score)
                        self.game_over_input_mode = False
                        self.menu_selection = 0 # Reset menu selection for next state
                        self.audio_mixer.play_sfx("menu_select")
                    elif event.unicode.isalnum() and len(self.ui_manager.current_input_text) < 10:
                        self.ui_manager.current_input_text += event.unicode
            self.ui_manager.draw_game_over_screen(final_score, high_scores, input_mode=True, menu_selection=self.menu_selection)
        else:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    self.audio_mixer.play_sfx("menu_navigate")
                    if event.key == pygame.K_UP:
                        self.menu_selection = (self.menu_selection - 1) % 2
                    elif event.key == pygame.K_DOWN:
                        self.menu_selection = (self.menu_selection + 1) % 2
                    elif event.key == pygame.K_RETURN:
                        self.audio_mixer.play_sfx("menu_select")
                        if self.menu_selection == 0:  # Restart Game
                            self.game_state = GameState.GAMEPLAY
                            self.event_manager.post(GameEvent.GAME_START)
                        elif self.menu_selection == 1:  # Return to Main Menu
                            self.game_state = GameState.MAIN_MENU
                            self.menu_selection = 0
                            self._stop_music()
                            self._play_music("main_menu_music")
                            self._reset_game_state_dependent_components()
            self.ui_manager.draw_game_over_screen(final_score, high_scores, input_mode=False, menu_selection=self.menu_selection)

    def _handle_high_scores_state(self, events: List[pygame.event.Event], dt: float) -> None:
        high_scores = self.score_manager.get_high_scores()
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.game_state = GameState.MAIN_MENU
                self.menu_selection = 0
                self.audio_mixer.play_sfx("menu_select")
                break
        self.ui_manager.draw_high_score_screen(high_scores)

    # --- Event Callbacks ---
    def _on_player_died(self) -> None:
        self.game_state = GameState.GAME_OVER
        self.audio_mixer.stop_music()
        self.audio_mixer.play_sfx("game_over")

        final_score = self.score_manager.get_current_score()
        high_scores = self.score_manager.get_high_scores()
        # Check if player made it to high score list
        if len(high_scores) < GameData.HIGH_SCORE_LIMIT or final_score > (high_scores[-1]['score'] if high_scores else -1):
            self.game_over_input_mode = True
            self.ui_manager.current_input_text = ""
        else:
            self.game_over_input_mode = False
            self.menu_selection = 0

    def _on_game_start(self) -> None:
        self._reset_game_state_dependent_components() # Ensure all game objects are reset
        self.player.activate(pygame.math.Vector2(GameData.SCREEN_WIDTH // 2, GameData.SCREEN_HEIGHT - 100)) # Activate player for new game
        self.ui_manager.update_hud(self.player.health_comp.get_health(), self.score_manager.get_current_score(), self.player.shooting_comp.get_weapon_level())
        self._play_music("gameplay_music")

    # --- Main Loop ---
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(GameData.FPS) / 1000.0
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            handler = self.state_handlers.get(self.game_state)
            if handler:
                handler(events, dt)
            else:
                print(f"Error: No handler for game state {self.game_state}")
                self.running = False

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# --- Main Execution Block ---
if __name__ == '__main__':
    game = Game.get_instance()
    game.run()