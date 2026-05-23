# tags: physics, platformer, top-down, collision_resolution, gravity, movement
import pygame

class KinematicPhysicsSprite(pygame.sprite.Sprite):
    """
    2D 運動學與碰撞解析基礎類別。
    [RAG 提示] 當遊戲需要「重力」、「平台跳躍」、「撞牆停止」、「滑行」時，
    實體必須繼承此類別，並使用 `move_and_collide` 來取代傳統的 `self.rect.x += v`。
    """
    def __init__(self, image, pos, groups=None):
        super().__init__(groups or [])
        self.image = image
        self.rect = self.image.get_rect(center=pos)
        
        # 物理屬性
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = pygame.math.Vector2(0, 0)
        self.gravity = 0.0  # 俯視角遊戲設為 0，平台跳躍遊戲設為例如 900
        self.friction = 0.8 # 模擬地面摩擦阻力
        self.max_speed = 400.0

        # 碰撞判定盒 (比圖片稍微小一點，避免邊角卡牆)
        self.hitbox = self.rect.inflate(-int(self.rect.width * 0.2), -int(self.rect.height * 0.2))

    def apply_gravity(self, dt):
        """套用重力加速度"""
        self.velocity.y += self.gravity * dt

    def apply_friction(self):
        """套用摩擦力阻尼"""
        self.velocity.x *= self.friction
        if self.gravity == 0:  # 如果是俯視角遊戲，Y 軸也有摩擦力
            self.velocity.y *= self.friction

    def move_and_collide(self, dt, solid_group):
        """
        [核心] X/Y 軸分離式碰撞檢測與防穿牆處理
        :param dt: Delta Time
        :param solid_group: 包含所有牆壁、地板的 pygame.sprite.Group
        """
        # 限制最大速度
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)

        # 1. 先處理 X 軸移動與碰撞
        self.hitbox.x += self.velocity.x * dt
        self._collide_with_solids(solid_group, 'x')

        # 2. 再處理 Y 軸移動與碰撞
        self.hitbox.y += self.velocity.y * dt
        self._collide_with_solids(solid_group, 'y')

        # 3. 讓繪圖用的 rect 對齊物理 hitbox 的中心
        self.rect.center = self.hitbox.center

    def _collide_with_solids(self, solid_group, direction):
        """內部的碰撞解析邏輯"""
        for sprite in solid_group:
            # 確保不會跟自己做碰撞判定
            if sprite is self or not getattr(sprite, 'active', True): 
                continue
                
            # 這裡假設環境物件也有 hitbox，如果沒有則退回使用 rect
            target_rect = getattr(sprite, 'hitbox', sprite.rect)
            
            if self.hitbox.colliderect(target_rect):
                if direction == 'x':
                    # 向右移動撞牆
                    if self.velocity.x > 0:
                        self.hitbox.right = target_rect.left
                    # 向左移動撞牆
                    elif self.velocity.x < 0:
                        self.hitbox.left = target_rect.right
                    self.velocity.x = 0  # 撞牆後 X 軸動能歸零
                    
                elif direction == 'y':
                    # 向下移動撞地板
                    if self.velocity.y > 0:
                        self.hitbox.bottom = target_rect.top
                    # 向上移動撞天花板
                    elif self.velocity.y < 0:
                        self.hitbox.top = target_rect.bottom
                    self.velocity.y = 0  # 撞地後 Y 軸動能歸零