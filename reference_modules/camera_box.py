# tags: camera, box-camera, scroll, y-sort
import pygame

class BoxCameraGroup(pygame.sprite.Group):
    """
    Encapsulated Box Camera logic.
    Features:
    1. Creates a virtual Camera Box.
    2. The camera only moves when the target moves outside the Box boundaries.
    3. Built-in Y-Sort (depth sorting) rendering.
    """
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        
        # 1. Dynamically get screen size to adapt to any window size
        screen_w, screen_h = self.display_surface.get_size()
        
        self.offset = pygame.math.Vector2()

        # 2. Camera Box Setup
        # Set boundaries as 20% of the window size as a buffer
        self.camera_borders = {
            'left': screen_w * 0.2,
            'right': screen_w * 0.2,
            'top': screen_h * 0.2,
            'bottom': screen_h * 0.2
        }
        
        # Calculate the actual Rect for the camera box
        l = self.camera_borders['left']
        t = self.camera_borders['top']
        w = screen_w - (self.camera_borders['left'] + self.camera_borders['right'])
        h = screen_h - (self.camera_borders['top'] + self.camera_borders['bottom'])
        self.camera_rect = pygame.Rect(l, t, w, h)

        # 3. Background Setup
        try:
            self.ground_surf = pygame.image.load("Graphic/ground2.png").convert_alpha()
            self.ground_surf = pygame.transform.scale(self.ground_surf, (2000, 2000))
        except Exception:
            # Fallback: Draw a teal floor if the image is missing
            self.ground_surf = pygame.Surface((2000, 2000))
            self.ground_surf.fill((70, 130, 180)) 
            
        self.ground_rect = self.ground_surf.get_rect(topleft=(0, 0))

    def box_target_camera(self, target):
        """Core Calculation: Update camera offset based on target position"""
        
        # Check left border
        if target.rect.left < self.camera_rect.left:
            self.camera_rect.left = target.rect.left
        # Check right border
        if target.rect.right > self.camera_rect.right:
            self.camera_rect.right = target.rect.right
        # Check top border
        if target.rect.top < self.camera_rect.top:
            self.camera_rect.top = target.rect.top
        # Check bottom border
        if target.rect.bottom > self.camera_rect.bottom:
            self.camera_rect.bottom = target.rect.bottom

        # Calculate final offset (box position minus border settings)
        self.offset.x = self.camera_rect.left - self.camera_borders['left']
        self.offset.y = self.camera_rect.top - self.camera_borders['top']

    def custom_draw(self, target):
        """Rendering loop: Background and Y-Sort sprites"""
        
        self.box_target_camera(target)

        # 1. Draw Map (subtracting the offset)
        ground_offset = self.ground_rect.topleft - self.offset
        self.display_surface.blit(self.ground_surf, ground_offset)
        
        # 2. Draw Sprites (Y-Sort: sorted by centery)
        # Crucial for 2D games to ensure objects block those behind them
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)
            
        # (Debug) Uncomment the line below to visualize the invisible camera box
        # pygame.draw.rect(self.display_surface, (255, 0, 0), self.camera_rect, 2)