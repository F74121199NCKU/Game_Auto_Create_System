# tags: camera, scroll, follow, player-center, y-sort
import pygame

class CameraScrollGroup(pygame.sprite.Group):
    """
    Scrolling camera that follows the player with built-in Y-Sort depth sorting.
    Suitable for RPGs, adventure games, and large map exploration.
    """
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        
        # Camera offset
        self.offset = pygame.math.Vector2()
        
        # Get screen center point
        self.half_w = self.display_surface.get_size()[0] // 2
        self.half_h = self.display_surface.get_size()[1] // 2

        # Attempt to load ground image; fallback to green background if it fails
        try:
            self.ground_surf = pygame.image.load("Graphic/ground2.png").convert_alpha()
        except (FileNotFoundError, pygame.error):
            self.ground_surf = pygame.Surface((2000, 2000))
            self.ground_surf.fill((30, 100, 30)) # Dark green grass
            
        self.ground_rect = self.ground_surf.get_rect(topleft=(0, 0))

    def center_target_camera(self, target):
        """Calculate offset to ensure the target remains at the center of the screen"""
        self.offset.x = target.rect.centerx - self.half_w
        self.offset.y = target.rect.centery - self.half_h

    def custom_draw(self, player):
        """
        :param player: Target object for the camera to follow (must have a 'rect' attribute)
        """
        self.center_target_camera(player)

        # 1. Draw ground (subtracting the offset)
        ground_offset = self.ground_rect.topleft - self.offset
        self.display_surface.blit(self.ground_surf, ground_offset)

        # 2. Y-Sort loop: Rendering all objects based on depth (centery)
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)