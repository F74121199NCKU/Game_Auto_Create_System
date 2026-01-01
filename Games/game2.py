import pygame
import random
import enum
import collections
import math
from typing import List, Tuple, Dict, Any, Optional, Set, Callable, TypeVar, Deque, Protocol, TYPE_CHECKING, Generic
#太空射擊遊戲

# To avoid circular imports for type hinting in states, especially GameState objects needing GameContext
if TYPE_CHECKING:
    from __main__ import Game # Assuming Game is in the same file for simplicity

# --- Configuration Constants ---
SCREEN_WIDTH: int = 800
SCREEN_HEIGHT: int = 600
FPS: int = 60

# Colors
WHITE: Tuple[int, int, int] = (255, 255, 255)
BLACK: Tuple[int, int, int] = (0, 0, 0)
RED: Tuple[int, int, int] = (255, 0, 0)
GREEN: Tuple[int, int, int] = (0, 255, 0)
BLUE: Tuple[int, int, int] = (0, 0, 255)
YELLOW: Tuple[int, int, int] = (255, 255, 0)
LIGHT_GREY: Tuple[int, int, int] = (200, 200, 200)
ORANGE: Tuple[int, int, int] = (255, 165, 0)

# Game Entities & Values (from Technical Proposal)
PLAYER_SPEED: float = 300.0  # pixels/sec
PLAYER_INITIAL_HP: int = 3
PLAYER_FIRE_RATE: float = 0.2  # seconds per shot (0.2s = 5 shots/sec)
PLAYER_COLLISION_BOX_SIZE: Tuple[int, int] = (50, 50)
PLAYER_START_POS: pygame.math.Vector2 = pygame.math.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 70)

BULLET_SPEED: float = 600.0  # pixels/sec
BULLET_DAMAGE: int = 1
BULLET_COLLISION_BOX_SIZE: Tuple[int, int] = (10, 20)

ENEMY_SPEED: float = 100.0  # pixels/sec
ENEMY_INITIAL_HP: int = 1
ENEMY_SCORE_VALUE: int = 100
ENEMY_DAMAGE_ON_PLAYER_COLLISION: int = 1
ENEMY_COLLISION_BOX_SIZE: Tuple[int, int] = (40, 40)

ENEMY_SPAWN_INTERVAL_INITIAL: float = 2.0  # seconds
ENEMY_SPAWN_INTERVAL_MIN: float = 0.5  # seconds
ENEMY_SPAWN_RATE_RAMP_DURATION: float = 60.0  # Seconds over which spawn rate ramps up

PARALLAX_BACKGROUND_SPEEDS: List[int] = [10, 25, 50]  # For 3 layers of stars

# UI & System Configuration Constants
DEFAULT_FONT: Optional[str] = None # Uses pygame's default font
FONT_SIZES: Dict[str, int] = {
    "title": 72,
    "large": 72,
    "medium": 48,
    "small": 28,
    "options": 48,
    "game_over_score": 48,
    "game_over_options": 40,
    "score_health": 36,
}
UI_COLORS: Dict[str, Tuple[int, int, int]] = {
    "title": YELLOW,
    "main_text": WHITE,
    "highlight_text": WHITE,
    "normal_text": LIGHT_GREY,
    "health_good": GREEN,
    "health_bad": RED,
}
UI_SPACING: Dict[str, int] = {
    "line_height_small": 5,
    "line_height_medium": 10,
    "line_height_large": 20,
    "menu_option_gap": 70,
    "game_over_score_offset_y": -50,
    "game_over_options_offset_y": 50,
    "score_display_x": 10,
    "score_display_y": 10,
    "health_display_x_offset": 10,
    "health_display_y": 10,
}

SPATIAL_GRID_CELL_SIZE: int = 100 # Cell size for collision partitioning

# --- Pygame Initialization (Moved to Game class) ---
# pygame.init()
# pygame.mixer.init()
# pygame.font.init()
# SCREEN: pygame.Surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
# pygame.display.set_caption("星際突襲者 (Star Raider)")
# CLOCK: pygame.time.Clock = pygame.time.Clock()

# --- Utility Functions & Classes ---

class EventManager:
    """A simple singleton event manager for observer pattern."""
    _instance: Optional['EventManager'] = None

    def __new__(cls) -> 'EventManager':
        if cls._instance is None:
            cls._instance = super(EventManager, cls).__new__(cls)
            cls._instance._subscribers: Dict[str, List[Callable[[Any], None]]] = collections.defaultdict(list)
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register a callback for an event type."""
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Unregister a callback for an event type."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def post(self, event_type: str, data: Any = None) -> None:
        """Notify all subscribers of an event."""
        # Iterate over a copy to allow callbacks to unsubscribe themselves
        for callback in list(self._subscribers[event_type]):
            callback(data)

# EVENT_MANAGER: EventManager = EventManager() # Moved instantiation to Game class

T = TypeVar('T', bound='GameObject') # Type variable for GenericObjectPool

class GenericObjectPool(Generic[T]): # Inherit from typing.Generic to make the class subscriptable
    """A generic object pool for recycling game objects."""
    def __init__(self, object_factory: Callable[[], T], initial_size: int = 10):
        self._object_factory: Callable[[], T] = object_factory
        self._pool: Deque[T] = collections.deque()
        self._active_objects: List[T] = []
        self.warmup(initial_size)

    def warmup(self, size: int) -> None:
        """Pre-populate the pool with objects."""
        for _ in range(size):
            self._pool.append(self._object_factory())

    def get(self) -> T:
        """Retrieve an object from the pool."""
        if not self._pool:
            # If pool is empty, create a new object.
            obj = self._object_factory()
        else:
            obj = self._pool.popleft()
        obj.reset()  # Reset object state before reuse
        obj.is_active = True
        self._active_objects.append(obj)
        return obj

    def return_obj(self, obj: T) -> None:
        """Return an object to the pool."""
        if obj in self._active_objects:
            obj.is_active = False
            self._active_objects.remove(obj)
            self._pool.append(obj)
        else:
            # Object was not managed by this pool or already returned
            pass # Consider adding a warning if this happens, but for production, often silenced.

    def get_all_active(self) -> List[T]:
        """Get a list of all currently active objects from the pool."""
        return [obj for obj in self._active_objects if obj.is_active]

# --- Game Entities ---

class GameObject(pygame.sprite.Sprite):
    """Base class for all game entities."""
    def __init__(self, image: Optional[pygame.Surface] = None, position: Optional[pygame.math.Vector2] = None,
                 velocity: Optional[pygame.math.Vector2] = None, collision_size: Optional[Tuple[int, int]] = None):
        super().__init__()
        
        # Ensure image is always a surface with alpha support
        if image:
            self.original_image: pygame.Surface = image.convert_alpha()
        elif collision_size:
            self.original_image = pygame.Surface(collision_size, pygame.SRCALPHA).convert_alpha()
            self.original_image.fill((0, 0, 0, 0)) # Start transparent
        else: # Fallback if no image or size specified
            self.original_image = pygame.Surface((1,1), pygame.SRCALPHA).convert_alpha()
            self.original_image.fill((0,0,0,0)) # Tiny transparent image

        self.image: pygame.Surface = self.original_image
        self.rect: pygame.Rect = self.image.get_rect()

        self.position: pygame.math.Vector2 = position.copy() if position else pygame.math.Vector2(0, 0)
        self.velocity: pygame.math.Vector2 = velocity.copy() if velocity else pygame.math.Vector2(0, 0)
        self.rect.center = (int(self.position.x), int(self.position.y))

        self.is_active: bool = False  # For object pool management

    def update(self, dt: float) -> None:
        """Update the object's position based on velocity and delta time."""
        if not self.is_active:
            return

        self.position += self.velocity * dt
        self.rect.center = (int(self.position.x), int(self.position.y))

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the object to the screen."""
        if self.is_active:
            screen.blit(self.image, self.rect)

    def reset(self) -> None:
        """Reset the object's state for reuse from the pool."""
        self.position = pygame.math.Vector2(0, 0)
        self.velocity = pygame.math.Vector2(0, 0)
        self.is_active = False
        self.image = self.original_image  # Restore original image if it was modified
        self.rect = self.image.get_rect(center=(int(self.position.x), int(self.position.y))) # Update rect center after position reset

class Player(GameObject):
    """The player's spaceship."""
    def __init__(self, bullet_pool: 'GenericObjectPool[Bullet]', sound_manager: 'SoundManager', position: pygame.math.Vector2 = PLAYER_START_POS, image: Optional[pygame.Surface] = None):
        player_image: pygame.Surface = image if image else self._create_player_image()
        super().__init__(image=player_image, position=position.copy(), collision_size=PLAYER_COLLISION_BOX_SIZE)
        self.max_health: int = PLAYER_INITIAL_HP
        self.health: int = self.max_health
        self.speed: float = PLAYER_SPEED
        self.fire_rate: float = PLAYER_FIRE_RATE
        self.fire_cooldown_timer: float = 0.0 # Time since last shot
        self.bullet_pool: GenericObjectPool[Bullet] = bullet_pool
        self.sound_manager: 'SoundManager' = sound_manager

    def _create_player_image(self) -> pygame.Surface:
        """Create a simple polygonal image for the player."""
        img = pygame.Surface(PLAYER_COLLISION_BOX_SIZE, pygame.SRCALPHA).convert_alpha()
        points = [
            (PLAYER_COLLISION_BOX_SIZE[0] // 2, 0),
            (0, PLAYER_COLLISION_BOX_SIZE[1]),
            (PLAYER_COLLISION_BOX_SIZE[0], PLAYER_COLLISION_BOX_SIZE[1])
        ]
        pygame.draw.polygon(img, BLUE, points)
        pygame.draw.rect(img, LIGHT_GREY, (PLAYER_COLLISION_BOX_SIZE[0] // 2 - 5, int(PLAYER_COLLISION_BOX_SIZE[1] * 0.7), 10, 20))
        return img

    def update(self, dt: float) -> None:
        """Update player movement based on input, check boundaries, and update cooldowns."""
        if not self.is_active:
            return

        self.fire_cooldown_timer += dt # Accumulate dt for fire rate

        # Handle movement input
        keys = pygame.key.get_pressed()
        self.velocity.x = 0.0 # Reset velocity each frame, then apply input
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.velocity.x = -self.speed
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity.x = self.speed

        super().update(dt)  # Apply velocity

        # Boundary check
        if self.rect.left < 0:
            self.rect.left = 0
            self.position.x = float(self.rect.centerx)
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.position.x = float(self.rect.centerx)

    def shoot(self) -> None:
        """Handle player shooting logic."""
        if self.fire_cooldown_timer >= self.fire_rate:
            bullet = self.bullet_pool.get()
            bullet.position = pygame.math.Vector2(self.position.x, self.rect.top)
            bullet.rect.center = (int(bullet.position.x), int(bullet.position.y))
            bullet.velocity = pygame.math.Vector2(0, -BULLET_SPEED)
            bullet.is_player_bullet = True
            bullet.damage = BULLET_DAMAGE
            self.fire_cooldown_timer = 0.0 # Reset cooldown
            self.sound_manager.play_sound("player_shot")

    def take_damage(self, amount: int) -> None:
        """Reduce player health and trigger death event if HP drops to zero."""
        self.health -= amount
        self.sound_manager.play_sound("player_hit")
        if self.health <= 0:
            self.health = 0
            self.is_active = False
            self.sound_manager.event_manager.post("PLAYER_DIED") # Post via event manager

    def reset(self) -> None:
        """Reset player state for a new game."""
        super().reset()
        self.position = PLAYER_START_POS.copy()
        self.health = self.max_health
        self.fire_cooldown_timer = 0.0
        self.is_active = True  # Player is always active in PlayState initially
        self.rect.center = (int(self.position.x), int(self.position.y))

class Bullet(GameObject):
    """A bullet fired by the player."""
    def __init__(self, image: Optional[pygame.Surface] = None): # Bullet doesn't need manager directly
        bullet_image: pygame.Surface = image if image else self._create_bullet_image()
        super().__init__(image=bullet_image, collision_size=BULLET_COLLISION_BOX_SIZE)
        self.damage: int = BULLET_DAMAGE
        self.is_player_bullet: bool = True  # To distinguish player vs enemy bullets

    def _create_bullet_image(self) -> pygame.Surface:
        """Create a simple rectangular image for the bullet."""
        img = pygame.Surface(BULLET_COLLISION_BOX_SIZE, pygame.SRCALPHA).convert_alpha()
        pygame.draw.rect(img, YELLOW, (0, 0, BULLET_COLLISION_BOX_SIZE[0], BULLET_COLLISION_BOX_SIZE[1]))
        return img

    def update(self, dt: float) -> None:
        """Update bullet position and mark for recycling if out of screen."""
        super().update(dt)
        # Check if bullet is out of screen
        if not (0 <= self.rect.bottom and self.rect.top <= SCREEN_HEIGHT and \
                0 <= self.rect.right and self.rect.left <= SCREEN_WIDTH):
            self.is_active = False  # Mark for recycling by the game loop

    def reset(self) -> None:
        """Reset bullet state for reuse."""
        super().reset()
        self.damage = BULLET_DAMAGE
        self.is_player_bullet = True
        self.rect = self.image.get_rect(center=(int(self.position.x), int(self.position.y)))

class Enemy(GameObject):
    """An enemy spaceship."""
    def __init__(self, event_manager: 'EventManager', sound_manager: 'SoundManager', image: Optional[pygame.Surface] = None):
        enemy_image: pygame.Surface = image if image else self._create_enemy_image()
        super().__init__(image=enemy_image, collision_size=ENEMY_COLLISION_BOX_SIZE)
        self.max_health: int = ENEMY_INITIAL_HP
        self.health: int = self.max_health
        self.score_value: int = ENEMY_SCORE_VALUE
        self.damage_on_player_collision: int = ENEMY_DAMAGE_ON_PLAYER_COLLISION
        self.speed: float = ENEMY_SPEED
        self.velocity: pygame.math.Vector2 = pygame.math.Vector2(0, self.speed)  # Always move down
        self.event_manager: 'EventManager' = event_manager
        self.sound_manager: 'SoundManager' = sound_manager

    def _create_enemy_image(self) -> pygame.Surface:
        """Create a simple polygonal image for the enemy."""
        img = pygame.Surface(ENEMY_COLLISION_BOX_SIZE, pygame.SRCALPHA).convert_alpha()
        points = [
            (ENEMY_COLLISION_BOX_SIZE[0] // 2, ENEMY_COLLISION_BOX_SIZE[1]),
            (0, 0),
            (ENEMY_COLLISION_BOX_SIZE[0], 0)
        ]
        pygame.draw.polygon(img, RED, points)
        return img

    def update(self, dt: float) -> None:
        """Update enemy position and mark for recycling if out of screen."""
        super().update(dt)
        # Check if enemy is out of screen
        if self.rect.top > SCREEN_HEIGHT:
            self.is_active = False  # Mark for recycling by the game loop

    def take_damage(self, amount: int) -> None:
        """Reduce enemy health and trigger destruction event if HP drops to zero."""
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.is_active = False
            self.event_manager.post("ENEMY_DESTROYED", {"position": self.position.copy(), "score": self.score_value})
            self.sound_manager.play_sound("enemy_explosion")

    def reset(self) -> None:
        """Reset enemy state for reuse."""
        super().reset()
        self.health = self.max_health
        self.score_value = ENEMY_SCORE_VALUE
        self.damage_on_player_collision = ENEMY_DAMAGE_ON_PLAYER_COLLISION
        # Spawn just above screen at a random X position
        self.position.x = float(random.randint(self.rect.width // 2, SCREEN_WIDTH - self.rect.width // 2))
        self.position.y = float(-self.rect.height)
        self.velocity = pygame.math.Vector2(0, self.speed)  # Reset velocity
        self.is_active = True  # Ready to be used by spawner
        self.rect.center = (int(self.position.x), int(self.position.y))

class Particle(GameObject):
    """A single particle for effects like explosions."""
    def __init__(self, size: int, color: Tuple[int, int, int]):
        # Create a base image for the particle once
        particle_image = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA).convert_alpha()
        pygame.draw.circle(particle_image, color, (size, size), size)
        super().__init__(image=particle_image, collision_size=(size * 2, size * 2))

        self.initial_color: Tuple[int, int, int] = color
        self.lifetime: float = 0.0
        self.age: float = 0.0
        self.current_alpha: int = 255
        self.base_size: int = size

    def update(self, dt: float) -> None:
        """Update particle position and age, and calculate alpha."""
        super().update(dt)
        self.age += dt
        if self.age >= self.lifetime:
            self.is_active = False
        
        normalized_age: float = self.age / self.lifetime
        self.current_alpha = max(0, 255 - int(255 * normalized_age))
        if self.current_alpha > 0:
            self.image.set_alpha(self.current_alpha)
        else:
            self.is_active = False

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the particle to the screen."""
        if self.is_active and self.current_alpha > 0:
            screen.blit(self.image, self.rect)

    def reset(self) -> None:
        """Reset particle for reuse. Note: image properties (color/size) are fixed once created."""
        super().reset()
        self.lifetime = 0.0
        self.age = 0.0
        self.current_alpha = 255
        self.image.set_alpha(255)

# --- Game Systems ---

class SpatialGrid:
    """A spatial partitioning system for optimized collision detection."""
    def __init__(self, width: int, height: int, cell_size: int):
        self.width: int = width
        self.height: int = height
        self.cell_size: int = cell_size
        self.grid_cols: int = math.ceil(width / cell_size)
        self.grid_rows: int = math.ceil(height / cell_size)
        self.grid: List[List[List[GameObject]]] = [[[] for _ in range(self.grid_cols)] for _ in range(self.grid_rows)]

    def _get_cells(self, rect: pygame.Rect) -> Tuple[int, int, int, int]:
        """Determine which grid cells an object's bounding box occupies."""
        min_col = max(0, int(rect.left // self.cell_size))
        max_col = min(self.grid_cols - 1, int(rect.right // self.cell_size))
        min_row = max(0, int(rect.top // self.cell_size))
        max_row = min(self.grid_rows - 1, int(rect.bottom // self.cell_size))
        return min_col, max_col, min_row, max_row

    def add_object(self, obj: GameObject) -> None:
        """Add an active object to the grid."""
        if not obj.is_active: return
        min_col, max_col, min_row, max_row = self._get_cells(obj.rect)
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                self.grid[row][col].append(obj)

    def clear(self) -> None:
        """Clear all objects from the grid (to be called each frame)."""
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                self.grid[row][col].clear()

    def get_nearby_objects(self, obj: GameObject) -> Set[GameObject]:
        """Get a set of potential colliders for a given object."""
        if not obj.is_active: return set()
        nearby: Set[GameObject] = set()
        min_col, max_col, min_row, max_row = self._get_cells(obj.rect)
        # Check object's own cells and adjacent cells
        for row in range(max(0, min_row - 1), min(self.grid_rows, max_row + 2)):
            for col in range(max(0, min_col - 1), min(self.grid_cols, max_col + 2)):
                for potential_collider in self.grid[row][col]:
                    if potential_collider != obj and potential_collider.is_active:
                        nearby.add(potential_collider)
        return nearby

class CollisionManager:
    """Manages collision detection using a spatial grid."""
    def __init__(self, spatial_grid: SpatialGrid):
        self.spatial_grid: SpatialGrid = spatial_grid

    def check_collisions_between_groups(self, group1: List[GameObject], group2: List[GameObject]) -> List[Tuple[GameObject, GameObject]]:
        """
        Checks for collisions between objects in group1 and group2,
        leveraging the spatial grid for efficiency.
        Returns a list of (obj1, obj2) tuples that have collided.
        """
        collided_pairs: List[Tuple[GameObject, GameObject]] = []
        group2_set: Set[GameObject] = set(group2)
        for obj1 in group1:
            if not obj1.is_active: continue
            potential_colliders = self.spatial_grid.get_nearby_objects(obj1)
            for obj2 in potential_colliders:
                if obj2 in group2_set and obj2.is_active and obj1.rect.colliderect(obj2.rect):
                    collided_pairs.append((obj1, obj2))
        return collided_pairs

class CombatSystem:
    """Handles combat-related logic, specifically collision responses."""
    def __init__(self, player: Player, bullet_pool: GenericObjectPool[Bullet], enemy_pool: GenericObjectPool[Enemy],
                 event_manager: EventManager, sound_manager: 'SoundManager'): # Changed type hint here
        self.player: Player = player
        self.bullet_pool: GenericObjectPool[Bullet] = bullet_pool
        self.enemy_pool: GenericObjectPool[Enemy] = enemy_pool
        self.event_manager: EventManager = event_manager
        self.sound_manager: 'SoundManager' = sound_manager

    def resolve_bullet_enemy_collisions(self, collisions: List[Tuple[GameObject, GameObject]]) -> None:
        """Applies damage and recycles objects for bullet-enemy collisions."""
        for bullet_obj, enemy_obj in collisions:
            if not isinstance(bullet_obj, Bullet) or not isinstance(enemy_obj, Enemy):
                continue

            bullet: Bullet = bullet_obj
            enemy: Enemy = enemy_obj

            if bullet.is_active and enemy.is_active and bullet.is_player_bullet:
                bullet.is_active = False
                self.bullet_pool.return_obj(bullet)
                enemy.take_damage(bullet.damage)

    def resolve_player_enemy_collisions(self, collisions: List[Tuple[GameObject, GameObject]]) -> None:
        """Applies damage and recycles objects for player-enemy collisions."""
        for player_obj, enemy_obj in collisions:
            if not isinstance(player_obj, Player) or not isinstance(enemy_obj, Enemy):
                continue

            player: Player = player_obj
            enemy: Enemy = enemy_obj

            if player.is_active and enemy.is_active:
                enemy.is_active = False
                self.enemy_pool.return_obj(enemy)
                player.take_damage(enemy.damage_on_player_collision)
                self.event_manager.post("ENEMY_DESTROYED", {"position": enemy.position.copy(), "score": 0})
                self.sound_manager.play_sound("enemy_explosion")

class ScoreSystem:
    """Manages and displays the player's score."""
    def __init__(self, event_manager: EventManager):
        self.score: int = 0
        self.font: pygame.font.Font = pygame.font.Font(DEFAULT_FONT, FONT_SIZES["score_health"])
        self.event_manager: EventManager = event_manager
        self.event_manager.subscribe("ENEMY_DESTROYED", self._on_enemy_destroyed)

    def _on_enemy_destroyed(self, data: Dict[str, Any]) -> None:
        """Callback for enemy destruction event."""
        self.add_score(data["score"])

    def add_score(self, points: int) -> None:
        """Add points to the current score."""
        self.score += points
        self.event_manager.post("SCORE_UPDATED", self.score)

    def reset(self) -> None:
        """Reset the score to zero."""
        self.score = 0
        self.event_manager.post("SCORE_UPDATED", self.score)

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the current score on the screen."""
        score_text = self.font.render(f"Score: {self.score}", True, UI_COLORS["main_text"])
        screen.blit(score_text, (UI_SPACING["score_display_x"], UI_SPACING["score_display_y"]))

class HealthSystem:
    """Manages and displays the player's health."""
    def __init__(self, player: Player):
        self.player: Player = player
        self.font: pygame.font.Font = pygame.font.Font(DEFAULT_FONT, FONT_SIZES["score_health"])

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the player's current health on the screen."""
        color = UI_COLORS["health_good"] if self.player.health > 1 else UI_COLORS["health_bad"]
        health_text = self.font.render(f"HP: {self.player.health}/{self.player.max_health}", True, color)
        screen.blit(health_text, (SCREEN_WIDTH - health_text.get_width() - UI_SPACING["health_display_x_offset"], UI_SPACING["health_display_y"]))

class ParallaxBackground:
    """Creates a multi-layered scrolling starfield background."""
    def __init__(self, screen_size: Tuple[int, int], speeds: List[int]):
        self.screen_size: Tuple[int, int] = screen_size
        self.layers: List[Dict[str, Any]] = []
        for i, speed in enumerate(speeds):
            layer_image = self._create_star_field(screen_size, num_stars=100 * (i + 1), star_size=i + 1)
            self.layers.append({
                "image": layer_image,
                "speed": float(speed),
                "y": 0.0,
                "y2": float(-screen_size[1])
            })

    def _create_star_field(self, size: Tuple[int, int], num_stars: int, star_size: int) -> pygame.Surface:
        """Generates a random starfield image."""
        surface = pygame.Surface(size, pygame.SRCALPHA).convert_alpha()
        surface.fill((0, 0, 0, 0))
        for _ in range(num_stars):
            x = random.randint(0, size[0])
            y = random.randint(0, size[1])
            color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255))
            pygame.draw.circle(surface, color, (x, y), star_size // 2)
        return surface

    def update(self, dt: float) -> None:
        """Update background layer positions for scrolling."""
        for layer in self.layers:
            layer["y"] += layer["speed"] * dt
            layer["y2"] += layer["speed"] * dt
            if layer["y"] >= self.screen_size[1]:
                layer["y"] = layer["y2"] - self.screen_size[1]
            if layer["y2"] >= self.screen_size[1]:
                layer["y2"] = layer["y"] - self.screen_size[1]

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the background layers to the screen."""
        for layer in self.layers:
            screen.blit(layer["image"], (0, int(layer["y"])))
            screen.blit(layer["image"], (0, int(layer["y2"])))

class ParticleSystem:
    """Manages and renders visual particle effects (e.g., explosions)."""
    def __init__(self, event_manager: EventManager):
        self._active_particles: List[Particle] = []
        self.event_manager: EventManager = event_manager
        self.event_manager.subscribe("ENEMY_DESTROYED", self._on_enemy_destroyed)

    def _on_enemy_destroyed(self, data: Dict[str, Any]) -> None:
        """Callback for enemy destruction event, adds an explosion."""
        self.add_explosion(data["position"])

    def add_explosion(self, position: pygame.math.Vector2) -> None:
        """Add a new explosion effect at a given position."""
        for _ in range(random.randint(5, 15)):
            particle = Particle(size=random.randint(2, 5), color=random.choice([RED, YELLOW, ORANGE]))
            
            speed: float = random.uniform(50, 150)
            angle: float = random.uniform(0, 2 * math.pi)
            velocity: pygame.math.Vector2 = pygame.math.Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
            lifetime: float = random.uniform(0.3, 1.0)
            
            particle.position = position.copy()
            particle.velocity = velocity
            particle.lifetime = lifetime
            particle.is_active = True
            self._active_particles.append(particle)

    def update(self, dt: float) -> None:
        """Update particle positions and remove expired particles."""
        particles_to_keep: List[Particle] = []
        for p in self._active_particles:
            p.update(dt)
            if p.is_active:
                particles_to_keep.append(p)
        self._active_particles = particles_to_keep

    def draw(self, screen: pygame.Surface) -> None:
        """Draw active particles to the screen."""
        for p in self._active_particles:
            p.draw(screen)

    def reset(self) -> None:
        """Clears all active particles."""
        self._active_particles.clear()

class SoundManager:
    """A singleton manager for loading and playing sound effects."""
    _instance: Optional['SoundManager'] = None

    def __new__(cls) -> 'SoundManager':
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
            cls._instance._sounds: Dict[str, pygame.mixer.Sound] = {}
            # Pre-load silent placeholders in case real files are missing
            cls._instance.load_sound("player_shot", "assets/player_shot.wav")
            cls._instance.load_sound("enemy_explosion", "assets/enemy_explosion.wav")
            cls._instance.load_sound("player_hit", "assets/player_hit.wav")
            # The sound manager needs access to the EventManager to post events like "PLAYER_DIED"
            # However, direct access should ideally be through dependency injection or GameContext.
            # For now, if EventManager is also a singleton, we can get its instance directly here.
            # If EventManager is created in Game, we'd need to pass it later or ensure its creation order.
            # Given the Game class design, EventManager is created before SoundManager is fully initialized
            # (SoundManager's __init__ is never called, only __new__), so it will need to be set later.
            cls._instance.event_manager: Optional[EventManager] = None # Will be set by Game class
        return cls._instance

    def set_event_manager(self, event_manager: EventManager) -> None:
        """Sets the event manager for this SoundManager instance."""
        self.event_manager = event_manager

    def load_sound(self, name: str, path: str) -> None:
        """Load a sound file, or create a silent placeholder if not found."""
        try:
            self._sounds[name] = pygame.mixer.Sound(path)
        except (pygame.error, FileNotFoundError): # Catch both pygame.error and FileNotFoundError
            print(f"Warning: Could not load sound '{path}'. Using silent placeholder.")
            self._sounds[name] = pygame.mixer.Sound(buffer=b'\x00' * 8) 

    def play_sound(self, name: str, loops: int = 0, volume: float = 1.0) -> None:
        """Play a loaded sound."""
        if name in self._sounds:
            channel = pygame.mixer.find_channel(True)
            if channel:
                channel.set_volume(volume)
                channel.play(self._sounds[name], loops)
        else:
            print(f"Warning: Sound '{name}' not found or not loaded.")

# SOUND_MANAGER: SoundManager = SoundManager() # Moved instantiation to Game class

# --- Game States (Refactored using State Pattern) ---

class GameState(enum.Enum):
    """Enumeration of possible game states."""
    INTRO = 0
    MAIN_MENU = 1
    PLAYING = 2
    GAME_OVER = 3

class GameContextProtocol(Protocol):
    """
    Protocol for the GameContext to minimize coupling between states and the main Game object.
    States only interact with the parts of Game they actually need, defined here.
    """
    is_running: bool
    bullet_pool: GenericObjectPool['Bullet']
    enemy_pool: GenericObjectPool['Enemy']
    score_system: ScoreSystem
    event_manager: EventManager
    sound_manager: 'SoundManager' # Changed type hint here
    
    def quit_game(self) -> None: ...

class BaseGameState:
    """Abstract base class for all game states."""
    def __init__(self, state_manager: 'StateManager'):
        self.state_manager: 'StateManager' = state_manager
        self.game_context: Optional[GameContextProtocol] = None
        self.event_manager: Optional[EventManager] = None # Added for convenience in states
        self.sound_manager: Optional['SoundManager'] = None # Changed type hint here

    def set_game_context(self, context: GameContextProtocol) -> None:
        """Sets the game context (e.g., the main Game instance) for the state."""
        self.game_context = context
        self.event_manager = context.event_manager
        self.sound_manager = context.sound_manager


    def enter(self) -> None:
        """Called when entering this state."""
        pass

    def handle_input(self, event: pygame.event.Event) -> None:
        """Handles input events for this state."""
        pass

    def update(self, dt: float) -> None:
        """Updates the game logic for this state."""
        pass

    def draw(self, screen: pygame.Surface) -> None:
        """Draws the screen for this state."""
        screen.fill(BLACK) # Default background

    def exit(self) -> None:
        """Called when exiting this state."""
        pass

class IntroState(BaseGameState):
    def __init__(self, state_manager: 'StateManager'):
        super().__init__(state_manager)
        self.intro_font_large: pygame.font.Font
        self.intro_font_medium: pygame.font.Font
        self.intro_font_small: pygame.font.Font
        self.rules_text: List[str] = []

    def enter(self) -> None:
        self.intro_font_large = pygame.font.Font(None, FONT_SIZES["large"])
        self.intro_font_medium = pygame.font.Font(None, FONT_SIZES["medium"])
        self.intro_font_small = pygame.font.Font(None, FONT_SIZES["small"])
        self.rules_text = [
            "星際突襲者",
            "",
            "遊戲規則:",
            "  - 駕駛太空船，擊毀敵機來獲取分數。",
            "  - 左右箭頭鍵/A/D: 移動太空船。",
            "  - 空白鍵: 發射雷射子彈。",
            "  - 避免與敵機碰撞，否則會損失生命值。",
            "  - 生命值歸零時，遊戲結束。",
            "",
            "按任意鍵進入主選單"
        ]

    def handle_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self.state_manager.set_state(GameState.MAIN_MENU)

    def draw(self, screen: pygame.Surface) -> None:
        super().draw(screen)
        y_offset: int = 100
        for i, line in enumerate(self.rules_text):
            if i == 0:
                text_surface = self.intro_font_large.render(line, True, UI_COLORS["title"])
            elif i < 3:
                text_surface = self.intro_font_medium.render(line, True, UI_COLORS["main_text"])
            else:
                text_surface = self.intro_font_small.render(line, True, UI_COLORS["normal_text"])
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            screen.blit(text_surface, text_rect)
            y_offset += text_surface.get_height() + UI_SPACING["line_height_small"]
            if i == 0: y_offset += UI_SPACING["line_height_large"]
            if i == 2: y_offset += UI_SPACING["line_height_medium"]

class MainMenuState(BaseGameState):
    def __init__(self, state_manager: 'StateManager'):
        super().__init__(state_manager)
        self.menu_font_title: pygame.font.Font
        self.menu_font_options: pygame.font.Font
        self.selected_option: int = 0
        self.options: List[str] = ["開始遊戲", "離開"]

    def enter(self) -> None:
        self.menu_font_title = pygame.font.Font(None, FONT_SIZES["title"])
        self.menu_font_options = pygame.font.Font(None, FONT_SIZES["options"])
        self.selected_option = 0

    def handle_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP or event.key == pygame.K_w:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                if self.selected_option == 0:
                    self.state_manager.set_state(GameState.PLAYING)
                elif self.selected_option == 1:
                    if self.game_context:
                        self.game_context.quit_game()

    def draw(self, screen: pygame.Surface) -> None:
        super().draw(screen)
        title_text = self.menu_font_title.render("星際突襲者", True, UI_COLORS["title"])
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        screen.blit(title_text, title_rect)

        for i, option in enumerate(self.options):
            color = UI_COLORS["highlight_text"] if i == self.selected_option else UI_COLORS["normal_text"]
            option_text = self.menu_font_options.render(option, True, color)
            option_rect = option_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + i * UI_SPACING["menu_option_gap"]))
            screen.blit(option_text, option_rect)

class PlayScene:
    """Encapsulates all game logic and entities for the PLAYING state."""
    def __init__(self, bullet_pool: GenericObjectPool[Bullet], enemy_pool: GenericObjectPool[Enemy],
                 score_system: ScoreSystem, event_manager: EventManager, sound_manager: 'SoundManager'): # Changed type hint here
        # Core Systems (Managers that aren't entities)
        self.event_manager: EventManager = event_manager
        self.sound_manager: 'SoundManager' = sound_manager

        # Game Entities
        self.player: Player = Player(bullet_pool, self.sound_manager)

        # Game Systems
        self.parallax_background: ParallaxBackground = ParallaxBackground((SCREEN_WIDTH, SCREEN_HEIGHT), PARALLAX_BACKGROUND_SPEEDS)
        self.particle_system: ParticleSystem = ParticleSystem(self.event_manager)
        self.score_system: ScoreSystem = score_system
        self.health_system: HealthSystem = HealthSystem(self.player)
        self.spatial_grid: SpatialGrid = SpatialGrid(SCREEN_WIDTH, SCREEN_HEIGHT, cell_size=SPATIAL_GRID_CELL_SIZE)
        self.collision_manager: CollisionManager = CollisionManager(self.spatial_grid)
        self.combat_system: CombatSystem = CombatSystem(self.player, bullet_pool, enemy_pool, self.event_manager, self.sound_manager)

        # Entity and Spawning Managers
        self.enemy_spawn_manager: EnemySpawnManager = EnemySpawnManager(enemy_pool)
        self.game_entity_manager: GameEntityManager = GameEntityManager(bullet_pool, enemy_pool)

    def reset(self) -> None:
        """Resets all game elements for a new game session."""
        self.player.reset()
        self.score_system.reset()
        self.game_entity_manager.reset()
        self.enemy_spawn_manager.reset()
        self.particle_system.reset()

    def handle_input(self, event: pygame.event.Event) -> None:
        """Handles input specific to the playing state."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self.player.is_active:
                self.player.shoot()

    def update(self, dt: float) -> None:
        """Updates all game logic and entities for the PLAYING state."""
        self.enemy_spawn_manager.update(dt)
        self.parallax_background.update(dt)
        self.player.update(dt)
        self.game_entity_manager.update_and_recycle(dt)
        self.particle_system.update(dt)

        self.spatial_grid.clear()
        if self.player.is_active:
            self.spatial_grid.add_object(self.player)
        for bullet in self.game_entity_manager.get_all_active_bullets():
            self.spatial_grid.add_object(bullet)
        for enemy in self.game_entity_manager.get_all_active_enemies():
            self.spatial_grid.add_object(enemy)

        active_bullets = self.game_entity_manager.get_all_active_bullets()
        active_enemies = self.game_entity_manager.get_all_active_enemies()

        bullet_enemy_collisions = self.collision_manager.check_collisions_between_groups(active_bullets, active_enemies)
        self.combat_system.resolve_bullet_enemy_collisions(bullet_enemy_collisions)

        player_enemies_collision = self.collision_manager.check_collisions_between_groups([self.player], active_enemies)
        self.combat_system.resolve_player_enemy_collisions(player_enemies_collision)

    def draw(self, screen: pygame.Surface) -> None:
        """Draws all game elements for the PLAYING state."""
        screen.fill(BLACK)
        self.parallax_background.draw(screen)

        if self.player.is_active:
            self.player.draw(screen)

        self.game_entity_manager.draw_all(screen)
        self.particle_system.draw(screen)
        self.score_system.draw(screen)
        self.health_system.draw(screen)

class PlayingState(BaseGameState):
    def __init__(self, state_manager: 'StateManager'):
        super().__init__(state_manager)
        self.play_scene: Optional[PlayScene] = None
        self._on_player_died_callback = self._player_died_callback

    def enter(self) -> None:
        if self.game_context:
            if not self.play_scene:
                self.play_scene = PlayScene(self.game_context.bullet_pool, self.game_context.enemy_pool,
                                            self.game_context.score_system, self.game_context.event_manager, self.game_context.sound_manager)
            self.play_scene.reset()
        if self.event_manager: # Check if event_manager is set from game_context
            self.event_manager.subscribe("PLAYER_DIED", self._on_player_died_callback)

    def _player_died_callback(self, data: Any) -> None:
        self.state_manager.set_state(GameState.GAME_OVER)

    def handle_input(self, event: pygame.event.Event) -> None:
        if self.play_scene:
            self.play_scene.handle_input(event)

    def update(self, dt: float) -> None:
        if self.play_scene:
            self.play_scene.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        if self.play_scene:
            self.play_scene.draw(screen)

    def exit(self) -> None:
        if self.event_manager: # Check if event_manager is set from game_context
            self.event_manager.unsubscribe("PLAYER_DIED", self._on_player_died_callback)
        if self.play_scene and self.play_scene.player.is_active:
             self.play_scene.player.is_active = False

class GameOverState(BaseGameState):
    def __init__(self, state_manager: 'StateManager'):
        super().__init__(state_manager)
        self.game_over_font_title: pygame.font.Font
        self.game_over_font_score: pygame.font.Font
        self.game_over_font_options: pygame.font.Font
        self.final_score: int = 0
        self.selected_option: int = 0
        self.options: List[str] = ["重新開始", "返回主選單"]

    def enter(self) -> None:
        self.game_over_font_title = pygame.font.Font(None, FONT_SIZES["title"])
        self.game_over_font_score = pygame.font.Font(None, FONT_SIZES["game_over_score"])
        self.game_over_font_options = pygame.font.Font(None, FONT_SIZES["game_over_options"])
        
        if self.game_context:
            self.final_score = self.game_context.score_system.score
        self.selected_option = 0

    def handle_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP or event.key == pygame.K_w:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                if self.selected_option == 0:
                    self.state_manager.set_state(GameState.PLAYING)
                elif self.selected_option == 1:
                    self.state_manager.set_state(GameState.MAIN_MENU)

    def draw(self, screen: pygame.Surface) -> None:
        super().draw(screen)
        game_over_text = self.game_over_font_title.render("遊戲結束", True, UI_COLORS["health_bad"])
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        screen.blit(game_over_text, game_over_rect)

        score_text = self.game_over_font_score.render(f"最終得分: {self.final_score}", True, UI_COLORS["main_text"])
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + UI_SPACING["game_over_score_offset_y"]))
        screen.blit(score_text, score_rect)

        for i, option in enumerate(self.options):
            color = UI_COLORS["highlight_text"] if i == self.selected_option else UI_COLORS["normal_text"]
            option_text = self.game_over_font_options.render(option, True, color)
            option_rect = option_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + i * UI_SPACING["menu_option_gap"] + UI_SPACING["game_over_options_offset_y"]))
            screen.blit(option_text, option_rect)

class StateManager:
    """Manages the overall game state transitions and logic."""
    def __init__(self, initial_state: GameState):
        self._states: Dict[GameState, BaseGameState] = {}
        self._current_state: Optional[BaseGameState] = None
        self._game_context: Optional[GameContextProtocol] = None

        self._states[GameState.INTRO] = IntroState(self)
        self._states[GameState.MAIN_MENU] = MainMenuState(self)
        self._states[GameState.PLAYING] = PlayingState(self)
        self._states[GameState.GAME_OVER] = GameOverState(self)

        self.set_state(initial_state)

    def set_game_context(self, context: GameContextProtocol) -> None:
        """Sets a reference to the main Game object for state interactions."""
        self._game_context = context
        for state in self._states.values():
            state.set_game_context(context)

    def set_state(self, new_state_enum: GameState) -> None:
        """Transitions the game to a new state."""
        if self._current_state and type(self._current_state) is type(self._states[new_state_enum]):
            return

        print(f"Transitioning from {self._current_state.__class__.__name__ if self._current_state else 'None'} to {new_state_enum.name}")
        if self._current_state:
            self._current_state.exit()

        self._current_state = self._states[new_state_enum]
        self._current_state.enter()

    def handle_input(self, event: pygame.event.Event) -> None:
        """Passes input events to the current state's handler."""
        if self._current_state:
            self._current_state.handle_input(event)

    def update(self, dt: float) -> None:
        """Calls the current state's update method."""
        if self._current_state:
            self._current_state.update(dt)

    def draw(self, screen: pygame.Surface) -> None:
        """Calls the current state's draw method."""
        if self._current_state:
            self._current_state.draw(screen)

class EnemySpawnManager:
    """Manages the spawning of enemies based on time and difficulty."""
    def __init__(self, enemy_pool: GenericObjectPool[Enemy]):
        self.enemy_pool: GenericObjectPool[Enemy] = enemy_pool
        self.spawn_timer: float = 0.0
        self.enemy_spawn_interval: float = ENEMY_SPAWN_INTERVAL_INITIAL
        self.game_timer: float = 0.0

    def update(self, dt: float) -> None:
        """Updates the spawn logic and attempts to spawn enemies."""
        self.game_timer += dt
        self.spawn_timer += dt

        current_difficulty_factor: float = min(1.0, self.game_timer / ENEMY_SPAWN_RATE_RAMP_DURATION)
        self.enemy_spawn_interval = max(
            ENEMY_SPAWN_INTERVAL_MIN,
            ENEMY_SPAWN_INTERVAL_INITIAL - (ENEMY_SPAWN_INTERVAL_INITIAL - ENEMY_SPAWN_INTERVAL_MIN) * current_difficulty_factor
        )

        if self.spawn_timer >= self.enemy_spawn_interval:
            self.enemy_pool.get()
            self.spawn_timer = 0.0

    def reset(self) -> None:
        """Resets the spawn manager for a new game."""
        self.spawn_timer = 0.0
        self.enemy_spawn_interval = ENEMY_SPAWN_INTERVAL_INITIAL
        self.game_timer = 0.0

class GameEntityManager:
    """Manages updating and recycling for a collection of game objects (bullets and enemies)."""
    def __init__(self, bullet_pool: GenericObjectPool[Bullet], enemy_pool: GenericObjectPool[Enemy]):
        self.bullet_pool: GenericObjectPool[Bullet] = bullet_pool
        self.enemy_pool: GenericObjectPool[Enemy] = enemy_pool

    def update_and_recycle(self, dt: float) -> None:
        """Updates all active objects and returns inactive ones to their pools."""
        active_bullets = self.bullet_pool.get_all_active()
        for bullet in active_bullets:
            bullet.update(dt)
            if not bullet.is_active:
                self.bullet_pool.return_obj(bullet)

        active_enemies = self.enemy_pool.get_all_active()
        for enemy in active_enemies:
            enemy.update(dt)
            if not enemy.is_active:
                self.enemy_pool.return_obj(enemy)
    
    def get_all_active_bullets(self) -> List[Bullet]:
        """Returns a list of all currently active bullets."""
        return self.bullet_pool.get_all_active()

    def get_all_active_enemies(self) -> List[Enemy]:
        """Returns a list of all currently active enemies."""
        return self.enemy_pool.get_all_active()
    
    def draw_all(self, screen: pygame.Surface) -> None:
        """Draws all active bullets and enemies."""
        for bullet in self.bullet_pool.get_all_active():
            bullet.draw(screen)
        for enemy in self.enemy_pool.get_all_active():
            enemy.draw(screen)

    def reset(self) -> None:
        """Returns all active entities to their pools."""
        for bullet in list(self.bullet_pool.get_all_active()):
            self.bullet_pool.return_obj(bullet)
        for enemy in list(self.enemy_pool.get_all_active()):
            self.enemy_pool.return_obj(enemy)

# --- Main Game Class ---

class Game:
    """The main game class, orchestrating all game elements and logic."""
    def __init__(self):
        # Initialize Pygame modules
        pygame.init()
        pygame.mixer.init()
        pygame.font.init()

        self.screen: pygame.Surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("星際突襲者 (Star Raider)")
        self.clock: pygame.time.Clock = pygame.time.Clock()

        self.is_running: bool = True

        # Managers (instantiated once, owned by Game)
        self.event_manager: EventManager = EventManager()
        self.sound_manager: SoundManager = SoundManager()
        self.sound_manager.set_event_manager(self.event_manager) # Set event manager for SoundManager

        # Global Object Pools (factories now explicitly pass managers)
        self.bullet_pool: GenericObjectPool[Bullet] = GenericObjectPool(Bullet, initial_size=50)
        self.enemy_pool: GenericObjectPool[Enemy] = GenericObjectPool(
            lambda: Enemy(self.event_manager, self.sound_manager), initial_size=20
        )
        
        self.score_system: ScoreSystem = ScoreSystem(self.event_manager)

        self.state_manager: StateManager = StateManager(GameState.INTRO)
        self.state_manager.set_game_context(self) # Pass self as GameContext

    def quit_game(self) -> None:
        """Signals the main loop to terminate."""
        self.is_running = False

    def handle_input(self) -> None:
        """Processes all Pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            self.state_manager.handle_input(event)

    def run(self) -> None:
        """The main game loop."""
        while self.is_running:
            dt: float = self.clock.tick(FPS) / 1000.0

            self.handle_input()
            self.state_manager.update(dt)
            self.state_manager.draw(self.screen) # Pass self.screen

            pygame.display.flip()

        pygame.quit()

# --- Main Execution ---
if __name__ == '__main__':
    game = Game()
    game.run()