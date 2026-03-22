# tags: sprite, rendering, group
import pygame

class GameSprite(pygame.sprite.Sprite):
    """Base class for all game objects, inheriting from Pygame's Sprite"""
    def __init__(self, x, y, image_path=None):
        super().__init__()
        if image_path:
            # Load image if a path is provided
            self.image = pygame.image.load(image_path).convert_alpha()
        else:
            # Fallback: Create a red square if no image is available
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 0))
        
        # Create a Rect area for collision detection
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velocity = pygame.math.Vector2(0, 0)

    def update(self, dt):
        """Update position per frame; 'dt' is Delta Time"""
        self.rect.x += self.velocity.x * dt
        self.rect.y += self.velocity.y * dt