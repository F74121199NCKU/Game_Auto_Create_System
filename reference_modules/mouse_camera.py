# tags: camera, mouse-control, rts-camera, edge-panning, y-sort
import pygame

class MouseCameraGroup(pygame.sprite.Group):
    """
    Mouse-controlled camera (RTS Style / Edge Panning).
    
    Features:
    1. Automatic scrolling when the mouse cursor hits the window edge.
    2. Implements a "Mouse Lock/Bounce" mechanic for an infinite scrolling feel.
    3. Built-in Y-Sort (depth sorting) rendering.
    
    Applicable genres: RTS, Simulation, Tower Defense.
    """
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        
        # 1. Camera offset and speed settings
        self.offset = pygame.math.Vector2()
        self.mouse_speed = 0.5 # Scroll speed modifier

        # 2. Edge Thresholds
        # Determines how many pixels from the edge trigger scrolling
        self.camera_borders = {
            'left': 100,
            'right': 100,
            'top': 100,
            'bottom': 100
        }

        # 3. Background Setup
        try:
            self.ground_surf = pygame.image.load("Graphic/ground2.png").convert_alpha()
            self.ground_surf = pygame.transform.scale(self.ground_surf, (2500, 2500))
        except Exception:
            self.ground_surf = pygame.Surface((2500, 2500))
            self.ground_surf.fill((50, 60, 50)) # Dark gray floor
            
        self.ground_rect = self.ground_surf.get_rect(topleft=(0, 0))

    def mouse_control(self):
        """Core Logic: Detect mouse position and update camera offset"""
        mouse = pygame.math.Vector2(pygame.mouse.get_pos())
        mouse_offset_vector = pygame.math.Vector2()

        # Get screen size and boundary definitions
        screen_w, screen_h = self.display_surface.get_size()
        left_border = self.camera_borders['left']
        top_border = self.camera_borders['top']
        right_border = screen_w - self.camera_borders['right']
        bottom_border = screen_h - self.camera_borders['bottom']

        # --- Logic Block: Determine if mouse is in edge zone and calculate shift ---
        if top_border < mouse.y < bottom_border:
            if mouse.x < left_border:
                mouse_offset_vector.x = mouse.x - left_border
                pygame.mouse.set_pos((left_border, mouse.y))
            if mouse.x > right_border:
                mouse_offset_vector.x = mouse.x - right_border
                pygame.mouse.set_pos((right_border, mouse.y))
        elif mouse.y < top_border:
            if mouse.x < left_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(left_border, top_border)
                pygame.mouse.set_pos((left_border, top_border))
            if mouse.x > right_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(right_border, top_border)
                pygame.mouse.set_pos((right_border, top_border))
        elif mouse.y > bottom_border:
            if mouse.x < left_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(left_border, bottom_border)
                pygame.mouse.set_pos((left_border, bottom_border))
            if mouse.x > right_border:
                mouse_offset_vector = mouse - pygame.math.Vector2(right_border, bottom_border)
                pygame.mouse.set_pos((right_border, bottom_border))

        if left_border < mouse.x < right_border:
            if mouse.y < top_border:
                mouse_offset_vector.y = mouse.y - top_border
                pygame.mouse.set_pos((mouse.x, top_border))
            if mouse.y > bottom_border:
                mouse_offset_vector.y = mouse.y - bottom_border
                pygame.mouse.set_pos((mouse.x, bottom_border))

        # Update total camera offset
        self.offset += mouse_offset_vector * self.mouse_speed

    def custom_draw(self):
        """Rendering loop: Run mouse control logic and Y-Sort drawing"""
        
        self.mouse_control()

        # 1. Draw Map
        ground_offset = self.ground_rect.topleft - self.offset
        self.display_surface.blit(self.ground_surf, ground_offset)
        
        # 2. Draw Sprites (Y-Sort)
        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.centery):
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)