import pygame
import os
import json
import random

class GameConfig:
    def __init__(self):
        self.data = {}

    def load(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def get_entity(self, name):
        for e in self.data.get('entities', []):
            if e.get('name') == name:
                return e
        return {}

    def get_prop(self, entity_name, prop_name, default_value):
        e = self.get_entity(entity_name)
        return e.get('properties', {}).get(prop_name, default_value)

class AssetManager:
    def __init__(self):
        self.images = {}

    def load_assets(self, data):
        base_dir = os.path.join(os.path.dirname(__file__), 'assets')
        for entity in data.get('entities', []):
            name = entity.get('name')
            img_name = entity.get('image')
            scale = entity.get('properties', {}).get('IMAGE_SCALE', 1.0)
            
            if name and img_name:
                path = os.path.join(base_dir, img_name)
                try:
                    img = pygame.image.load(path).convert_alpha()
                    w = int(img.get_width() * scale)
                    h = int(img.get_height() * scale)
                    img = pygame.transform.scale(img, (w, h))
                    self.images[name] = img
                except Exception:
                    w = int(1024 * scale)
                    h = int(1024 * scale)
                    surf = pygame.Surface((w, h), pygame.SRCALPHA)
                    surf.fill((255, 0, 255, 128))
                    self.images[name] = surf

    def get_image(self, name):
        return self.images.get(name)

class ObjectPool:
    def __init__(self, create_func):
        self.pool = []
        self.create_func = create_func
        
    def get(self, *args, **kwargs):
        if self.pool:
            obj = self.pool.pop()
        else:
            obj = self.create_func()
        obj.init(*args, **kwargs)
        return obj
        
    def return_to_pool(self, obj):
        obj.kill()
        self.pool.append(obj)

class FSM:
    def __init__(self):
        self.states = {}
        self.current_state = None
        self.previous_state = None
        
    def add(self, name, state):
        self.states[name] = state
        
    def change(self, name):
        if self.current_state:
            self.states[self.current_state].exit()
            self.previous_state = self.current_state
        self.current_state = name
        self.states[self.current_state].enter()

class State:
    def __init__(self, game):
        self.game = game
    def enter(self): return
    def exit(self): return
    def handle_event(self, event): return
    def update(self, dt): return
    def draw(self, screen): return

class UIManager:
    def __init__(self):
        self.elements = []
        
    def add(self, element):
        self.elements.append(element)
        
    def clear(self):
        self.elements.clear()
        
    def draw(self, screen):
        for el in self.elements:
            el.draw(screen)
            
    def handle_event(self, event):
        for el in self.elements:
            el.handle_event(event)

class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image, x, y, pool=None, **kwargs):
        groups = kwargs.get('groups') or []
        super().__init__(*groups)
        self.pool = pool
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.centerx = int(x)
        self.rect.centery = int(y)
        
        shrink_x = -self.rect.width * 0.2
        shrink_y = -self.rect.height * 0.2
        self.hitbox = self.rect.inflate(shrink_x, shrink_y)
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.centery = self.rect.centery

    def update(self, dt):
        return

class Button(GameSprite):
    def __init__(self, x, y, img_name, text, callback, game, pool=None, **kwargs):
        img = game.asset_manager.get_image(img_name)
        if not img:
            img = pygame.Surface((200, 50), pygame.SRCALPHA)
            img.fill((100, 100, 100))
        else:
            img = img.copy()
            
        super().__init__(img, x, y, pool=pool, **kwargs)
        self.text = text
        self.callback = callback
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        
        if self.text:
            text_surf = self.font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(self.image.get_width() // 2, self.image.get_height() // 2))
            self.image.blit(text_surf, text_rect)
            
    def draw(self, screen):
        screen.blit(self.image, self.rect)
            
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.rect.collidepoint(mx, my):
                self.callback()

class MenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.ui = UIManager()
        
    def enter(self):
        self.ui.clear()
        w, h = self.game.screen.get_size()
        cx, cy = w // 2, h // 2
        self.ui.add(Button(cx, cy - 80, 'Button_GameStart', 'GAME START', lambda: self.game.fsm.change('PLAYING'), self.game))
        self.ui.add(Button(cx, cy, 'Button_Rules', 'RULES', lambda: self.game.fsm.change('RULES'), self.game))
        self.ui.add(Button(cx, cy + 80, 'Button_Quit', 'QUIT', lambda: self.game.fsm.change('QUIT'), self.game))

    def handle_event(self, event):
        self.ui.handle_event(event)
        
    def draw(self, screen):
        screen.fill((20, 20, 25))
        self.ui.draw(screen)

class QuitState(State):
    def enter(self):
        self.game.running = False

class PauseState(State):
    def __init__(self, game):
        super().__init__(game)
        self.ui = UIManager()
        
    def enter(self):
        self.ui.clear()
        w, h = self.game.screen.get_size()
        cx, cy = w // 2, h // 2
        self.ui.add(Button(cx, cy - 120, 'Button_Continue', 'CONTINUE', lambda: self.game.fsm.change('PLAYING'), self.game))
        self.ui.add(Button(cx, cy - 40, 'Button_Restart', 'RESTART', self.restart, self.game))
        self.ui.add(Button(cx, cy + 40, 'Button_Rules', 'RULES', lambda: self.game.fsm.change('RULES'), self.game))
        self.ui.add(Button(cx, cy + 120, 'Button_BackToMainMenu', 'BACK TO MAIN MENU', self.main_menu, self.game))
        
    def restart(self):
        self.game.playing_state.needs_reset = True
        self.game.fsm.change('PLAYING')
        
    def main_menu(self):
        self.game.playing_state.needs_reset = True
        self.game.fsm.change('MENU')
        
    def handle_event(self, event):
        self.ui.handle_event(event)
        
    def draw(self, screen):
        self.game.playing_state.draw(screen)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        self.ui.draw(screen)

class RulesState(State):
    def __init__(self, game):
        super().__init__(game)
        self.ui = UIManager()
        pygame.font.init()
        self.font = pygame.font.Font(None, 48)
        
    def enter(self):
        self.ui.clear()
        w, h = self.game.screen.get_size()
        self.ui.add(Button(w // 2, h - 100, 'Button_BackToMainMenu', 'BACK', self.back, self.game))
        
    def back(self):
        prev = getattr(self.game.fsm, 'previous_state', 'MENU')
        if prev == 'PAUSE':
            self.game.fsm.change('PAUSE')
        else:
            self.game.fsm.change('MENU')
            
    def handle_event(self, event):
        self.ui.handle_event(event)
        
    def draw(self, screen):
        screen.fill((30, 30, 50))
        lines = [
            "ELEMENTAL BOLT - RULES",
            "WASD to Move, Mouse to Aim & Shoot.",
            "P or ESC to Pause.",
            "Defeat all enemies to spawn the Portal.",
            "Hit the Portal to proceed to the next level.",
            "Don't lose all your HP!"
        ]
        w = screen.get_width()
        for i, line in enumerate(lines):
            surf = self.font.render(line, True, (255, 255, 255))
            r = surf.get_rect(center=(w // 2, 100 + i * 50))
            screen.blit(surf, r)
        self.ui.draw(screen)

class UpgradeState(State):
    def __init__(self, game):
        super().__init__(game)
        self.ui = UIManager()
        pygame.font.init()
        self.font = pygame.font.Font(None, 64)
        
    def enter(self):
        self.ui.clear()
        w, h = self.game.screen.get_size()
        self.ui.add(Button(w // 2, h // 2 + 100, 'Button_Continue', 'NEXT LEVEL', self.next_level, self.game))
        
    def next_level(self):
        self.game.playing_state.needs_reset = True
        self.game.fsm.change('PLAYING')
        
    def handle_event(self, event):
        self.ui.handle_event(event)
        
    def draw(self, screen):
        screen.fill((20, 50, 20))
        surf = self.font.render("LEVEL CLEAR!", True, (255, 255, 0))
        r = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
        screen.blit(surf, r)
        self.ui.draw(screen)

class GameOverState(State):
    def __init__(self, game):
        super().__init__(game)
        self.ui = UIManager()
        pygame.font.init()
        self.font = pygame.font.Font(None, 64)
        
    def enter(self):
        self.ui.clear()
        w, h = self.game.screen.get_size()
        self.ui.add(Button(w // 2, h // 2 + 100, 'Button_BackToMainMenu', 'MAIN MENU', self.main_menu, self.game))
        
    def main_menu(self):
        self.game.playing_state.needs_reset = True
        self.game.fsm.change('MENU')
        
    def handle_event(self, event):
        self.ui.handle_event(event)
        
    def draw(self, screen):
        screen.fill((50, 20, 20))
        surf = self.font.render("GAME OVER", True, (255, 50, 50))
        r = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
        screen.blit(surf, r)
        self.ui.draw(screen)

class CameraScrollGroup(pygame.sprite.Group):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        self.offset = pygame.math.Vector2(0, 0)
        self.shake_duration = 0
        self.shake_intensity = 0
        w, h = screen.get_size()
        self.half_w = w // 2
        self.half_h = h // 2

    def center_on_target(self, target):
        self.offset.x = target.rect.centerx - self.half_w
        self.offset.y = target.rect.centery - self.half_h
        
    def update_camera(self, target, dt):
        self.offset.x += (target.rect.centerx - self.offset.x - self.half_w) * 5 * dt
        self.offset.y += (target.rect.centery - self.offset.y - self.half_h) * 5 * dt
        
        if self.shake_duration > 0:
            self.shake_duration -= dt
            self.offset.x += random.uniform(-self.shake_intensity, self.shake_intensity)
            self.offset.y += random.uniform(-self.shake_intensity, self.shake_intensity)
            
    def apply_shake(self, duration=0.2, intensity=10):
        self.shake_duration = duration
        self.shake_intensity = intensity
        
    def draw(self, surface):
        for sprite in self.sprites():
            if hasattr(sprite, 'image'):
                offset_pos = sprite.rect.topleft - self.offset
                surface.blit(sprite.image, offset_pos)

class MazeManager:
    def generate(self, w, h):
        grid = [[0 for _ in range(w)] for _ in range(h)]
        for x in range(w):
            grid[0][x] = 1
            grid[h-1][x] = 1
        for y in range(h):
            grid[y][0] = 1
            grid[y][w-1] = 1
            
        for _ in range(w * h // 6):
            rx, ry = random.randint(2, w-3), random.randint(2, h-3)
            if not (w//2 - 2 <= rx <= w//2 + 2 and h//2 - 2 <= ry <= h//2 + 2):
                grid[ry][rx] = 1
        return grid

class Wall(GameSprite):
    def __init__(self, x, y, game, pool=None, **kwargs):
        img = game.asset_manager.get_image('Forest_Wall_Tile')
        super().__init__(img, x, y, pool=pool, **kwargs)

class Floor(GameSprite):
    def __init__(self, x, y, game, pool=None, **kwargs):
        img = game.asset_manager.get_image('Forest_Floor_Tile')
        super().__init__(img, x, y, pool=pool, **kwargs)

class Portal(GameSprite):
    def __init__(self, x, y, game, pool=None, **kwargs):
        img = game.asset_manager.get_image('Portal')
        super().__init__(img, x, y, pool=pool, **kwargs)

class EnemyDeathParticle(GameSprite):
    def __init__(self, game, pool=None, **kwargs):
        surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 50, 50), (10, 10), 10)
        super().__init__(surf, 0, 0, pool=pool, **kwargs)
        self.game = game
        self.life = 0
        
    def init(self, x, y):
        self.rect.centerx = int(x)
        self.rect.centery = int(y)
        self.life = 0.5
        
    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            if self.pool:
                self.pool.return_to_pool(self)
            else:
                self.game.particle_pool.return_to_pool(self)

class MagicBolt(GameSprite):
    def __init__(self, game, pool=None, **kwargs):
        img = game.asset_manager.get_image('Magic Bolt')
        super().__init__(img, 0, 0, pool=pool, **kwargs)
        self.game = game
        self.speed = game.config.get_prop('Magic Bolt', 'SPEED', 600.0)
        self.dir = pygame.math.Vector2(0, 0)
        self.pos = pygame.math.Vector2(0, 0)
        self.owner = ''
        
    def init(self, x, y, direction, owner):
        self.pos = pygame.math.Vector2(x, y)
        self.hitbox.centerx = int(x)
        self.hitbox.centery = int(y)
        self.rect.centerx = self.hitbox.centerx
        self.rect.centery = self.hitbox.centery
        self.dir = direction
        self.owner = owner
        
    def update(self, dt):
        self.pos.x += self.dir.x * self.speed * dt
        self.pos.y += self.dir.y * self.speed * dt
        self.hitbox.centerx = int(self.pos.x)
        self.hitbox.centery = int(self.pos.y)
        self.rect.centerx = self.hitbox.centerx
        self.rect.centery = self.hitbox.centery

class Player(GameSprite):
    def __init__(self, x, y, game, pool=None, **kwargs):
        img = game.asset_manager.get_image('Player')
        super().__init__(img, x, y, pool=pool, **kwargs)
        self.game = game
        self.pos = pygame.math.Vector2(x, y)
        
        player_data = game.config.get_entity('Player') or {}
        props = player_data.get('properties', {})
        self.hp = props.get('HP', 100)
        self.max_hp = self.hp
        self.speed = props.get('SPEED', 300.0)
        self.cooldown = props.get('COOLDOWN', 0.5)
        self.timer = 0.0
        self.invulnerable_timer = 0.0
        
    def update(self, dt):
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
            
        self.timer -= dt
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1
        
        vec = pygame.math.Vector2(dx, dy)
        if vec.length() > 0:
            vec = vec.normalize()
            
        vx = vec.x * self.speed * dt
        vy = vec.y * self.speed * dt
        
        if vx != 0:
            self.pos.x += vx
            self.hitbox.centerx = int(self.pos.x)
            self.game.collision_manager.check_x_collisions(self, vx)
            self.pos.x = self.hitbox.centerx
            
        if vy != 0:
            self.pos.y += vy
            self.hitbox.centery = int(self.pos.y)
            self.game.collision_manager.check_y_collisions(self, vy)
            self.pos.y = self.hitbox.centery
            
        self.rect.centerx = self.hitbox.centerx
        self.rect.centery = self.hitbox.centery

        mouse_pressed = pygame.mouse.get_pressed()
        if mouse_pressed[0] and self.timer <= 0:
            mx, my = pygame.mouse.get_pos()
            cam_x = self.game.camera.offset.x
            cam_y = self.game.camera.offset.y
            target = pygame.math.Vector2(mx + cam_x, my + cam_y)
            dir_vec = target - self.pos
            if dir_vec.length() > 0:
                dir_vec = dir_vec.normalize()
                bolt = self.game.projectile_pool.get(self.pos.x, self.pos.y, dir_vec, 'Player')
                self.game.projectiles.add(bolt)
                self.game.playing_state.all_sprites.add(bolt)
                self.timer = self.cooldown

class Enemy(GameSprite):
    def __init__(self, x, y, type_name, game, pool=None, **kwargs):
        img = game.asset_manager.get_image(type_name)
        super().__init__(img, x, y, pool=pool, **kwargs)
        self.game = game
        self.type_name = type_name
        self.pos = pygame.math.Vector2(x, y)
        
        # Prepare stun flash graphics
        self.original_image = self.image.copy()
        self.flash_image = self.image.copy()
        flash_surface = pygame.Surface(self.flash_image.get_size(), pygame.SRCALPHA)
        flash_surface.fill((255, 50, 50, 100))
        self.flash_image.blit(flash_surface, (0, 0))
        self.stun_timer = 0.0

        enemy_data = game.config.get_entity(type_name) or {}
        props = enemy_data.get('properties', {})
        self.hp = props.get('HP', 30)
        self.speed = props.get('SPEED', 100.0)
        self.cooldown = props.get('COOLDOWN', 2.0)
        self.timer = self.cooldown
        
        self.stuck_timer = 0.0
        self.wander_dir = pygame.math.Vector2(0, 0)
        
    def apply_stun(self, duration):
        self.stun_timer = duration

    def update(self, dt):
        if self.stun_timer > 0:
            self.stun_timer -= dt
            # Hit reaction animation flash
            if int(self.stun_timer * 15) % 2 == 0:
                self.image = self.flash_image
            else:
                self.image = self.original_image
            return # Pause tracking/movement while stunned
            
        self.image = self.original_image
        
        player = self.game.playing_state.player
        if not player: return
        
        vec = player.pos - self.pos
        dist = vec.length()
        
        if self.stuck_timer > 0:
            self.stuck_timer -= dt
            move_vec = self.wander_dir
        else:
            move_vec = vec.normalize() if dist > 0 else pygame.math.Vector2(0, 0)
        
        if self.type_name == 'Fire Demon':
            if dist < 400:
                self.timer -= dt
                if self.timer <= 0:
                    if dist > 0:
                        dir_vec = vec.normalize()
                        bolt = self.game.projectile_pool.get(self.pos.x, self.pos.y, dir_vec, 'Enemy')
                        self.game.projectiles.add(bolt)
                        self.game.playing_state.all_sprites.add(bolt)
                    self.timer = self.cooldown
            if dist > 300 or self.stuck_timer > 0:
                self._move(move_vec, dt)
        else:
            self._move(move_vec, dt)
            
    def _move(self, vec, dt):
        dx = vec.x * self.speed * dt
        dy = vec.y * self.speed * dt
        
        hit_x = False
        if dx != 0:
            self.pos.x += dx
            self.hitbox.centerx = int(self.pos.x)
            hit_x = self.game.collision_manager.check_x_collisions(self, dx)
            self.pos.x = self.hitbox.centerx
            
        hit_y = False
        if dy != 0:
            self.pos.y += dy
            self.hitbox.centery = int(self.pos.y)
            hit_y = self.game.collision_manager.check_y_collisions(self, dy)
            self.pos.y = self.hitbox.centery
            
        if (hit_x or hit_y) and self.stuck_timer <= 0:
            self.stuck_timer = 0.5
            if hit_x and not hit_y:
                self.wander_dir = pygame.math.Vector2(0, 1 if vec.y >= 0 else -1)
            elif hit_y and not hit_x:
                self.wander_dir = pygame.math.Vector2(1 if vec.x >= 0 else -1, 0)
            else:
                self.wander_dir = pygame.math.Vector2(random.choice([-1, 1]), random.choice([-1, 1]))
                if self.wander_dir.length() > 0:
                    self.wander_dir = self.wander_dir.normalize()

        self.rect.centerx = self.hitbox.centerx
        self.rect.centery = self.hitbox.centery

class CollisionManager:
    def __init__(self, game):
        self.game = game
        
    def check_x_collisions(self, entity, dx):
        hit = False
        for wall in self.game.playing_state.walls:
            if entity.hitbox.colliderect(wall.hitbox):
                hit = True
                if dx > 0:
                    entity.hitbox.right = wall.hitbox.left
                elif dx < 0:
                    entity.hitbox.left = wall.hitbox.right
        return hit
                    
    def check_y_collisions(self, entity, dy):
        hit = False
        for wall in self.game.playing_state.walls:
            if entity.hitbox.colliderect(wall.hitbox):
                hit = True
                if dy > 0:
                    entity.hitbox.bottom = wall.hitbox.top
                elif dy < 0:
                    entity.hitbox.top = wall.hitbox.bottom
        return hit

    def update(self):
        for proj in list(self.game.projectiles):
            hit_wall = False
            for wall in self.game.playing_state.walls:
                if proj.hitbox.colliderect(wall.hitbox):
                    hit_wall = True
                    break
            if hit_wall:
                self.game.projectile_pool.return_to_pool(proj)
                continue
                
            if proj.owner == 'Player':
                for enemy in self.game.playing_state.enemies:
                    if proj.hitbox.colliderect(enemy.hitbox):
                        enemy.hp -= 20
                        enemy.pos -= proj.dir * 10
                        enemy.apply_stun(0.4) # Stun reaction on hit
                        self.game.projectile_pool.return_to_pool(proj)
                        if enemy.hp <= 0:
                            part = self.game.particle_pool.get(enemy.pos.x, enemy.pos.y)
                            self.game.playing_state.all_sprites.add(part)
                            enemy.kill()
                        break
            elif proj.owner == 'Enemy':
                player = self.game.playing_state.player
                if player and proj.hitbox.colliderect(player.hitbox):
                    if player.invulnerable_timer <= 0:
                        player.hp -= 10
                        player.invulnerable_timer = 0.5
                        self.game.camera.apply_shake(0.2, 10)
                    self.game.projectile_pool.return_to_pool(proj)

        player = self.game.playing_state.player
        if player:
            for enemy in self.game.playing_state.enemies:
                if player.hitbox.colliderect(enemy.hitbox):
                    if player.invulnerable_timer <= 0:
                        player.hp -= 10
                        player.invulnerable_timer = 1.0
                        self.game.camera.apply_shake(0.2, 10)
                    vec = enemy.pos - player.pos
                    if vec.length() > 0:
                        enemy.pos += vec.normalize() * 5
                    enemy.apply_stun(0.5) # Stun reaction on player collision
                    break
                    
        portal = self.game.playing_state.portal
        if portal and player:
            if player.hitbox.colliderect(portal.hitbox):
                self.game.fsm.change('UPGRADE_MENU')

class HUD:
    def __init__(self, game):
        self.game = game
        self.hp_bar_img = game.asset_manager.get_image('HUD_HealthBar')
        self.level_frame_img = game.asset_manager.get_image('HUD_LevelDisplay')
        if not self.hp_bar_img:
            self.hp_bar_img = pygame.Surface((200, 30))
            self.hp_bar_img.fill((255, 0, 0))
        if not self.level_frame_img:
            self.level_frame_img = pygame.Surface((150, 50))
            self.level_frame_img.fill((100, 100, 100))
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        
    def draw(self, screen):
        player = self.game.playing_state.player
        if not player: return
        
        hp_ratio = max(0, player.hp / max(1, player.max_hp))
        w = int(self.hp_bar_img.get_width() * hp_ratio)
        h = self.hp_bar_img.get_height()
        if w > 0:
            surf = pygame.transform.scale(self.hp_bar_img, (w, h))
            screen.blit(surf, (20, 20))
            
        txt = self.font.render(f"HP: {int(player.hp)}/{int(player.max_hp)}", True, (255, 255, 255))
        screen.blit(txt, (30, 25))
        
        frame_x = screen.get_width() - self.level_frame_img.get_width() - 20
        screen.blit(self.level_frame_img, (frame_x, 20))
        lvl_txt = self.font.render(f"LEVEL {self.game.playing_state.level_num}", True, (255, 255, 255))
        screen.blit(lvl_txt, (frame_x + 20, 30))

class PlayingState(State):
    def __init__(self, game):
        super().__init__(game)
        self.game.playing_state = self
        self.needs_reset = True
        self.level_num = 1
        self.hud = HUD(game)
        self.portal = None

    def enter(self):
        if self.needs_reset:
            self._setup_new_game()
            self.needs_reset = False

    def _setup_new_game(self):
        if hasattr(self.game, 'projectiles'):
            for p in list(self.game.projectiles):
                self.game.projectile_pool.return_to_pool(p)
                
        prev = getattr(self.game.fsm, 'previous_state', 'MENU')
        if prev in ['MENU', 'GAME_OVER']:
            self.level_num = 1
        elif prev == 'UPGRADE_MENU':
            self.level_num += 1

        self.all_sprites = CameraScrollGroup(self.game.screen)
        self.game.camera = self.all_sprites
        self.walls = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.game.projectiles = pygame.sprite.Group()
        
        maze_mgr = MazeManager()
        w_grid, h_grid = 25, 25
        grid = maze_mgr.generate(w_grid, h_grid)
        self.portal = None
        
        img_wall = self.game.asset_manager.get_image('Forest_Wall_Tile')
        tile_w = int(img_wall.get_width() * 0.8) if img_wall else 100
        tile_h = int(img_wall.get_height() * 0.8) if img_wall else 100
        
        for y, row in enumerate(grid):
            for x, val in enumerate(row):
                if val == 0:
                    px = x * tile_w
                    py = y * tile_h
                    floor = Floor(px, py, self.game)
                    self.all_sprites.add(floor)
                    
        for y, row in enumerate(grid):
            for x, val in enumerate(row):
                if val == 1:
                    px = x * tile_w
                    py = y * tile_h
                    wall = Wall(px, py, self.game)
                    self.walls.add(wall)
                    self.all_sprites.add(wall)

        player_x = (w_grid // 2) * tile_w
        player_y = (h_grid // 2) * tile_h
        self.player = Player(player_x, player_y, self.game)
        self.all_sprites.add(self.player)
        
        self.game.camera.center_on_target(self.player)
        
        num_slimes = 3 + self.level_num * 2
        num_demons = 3 + self.level_num
        
        for _ in range(num_slimes):
            rx = random.randint(2, w_grid - 3) * tile_w
            ry = random.randint(2, h_grid - 3) * tile_h
            e = Enemy(rx, ry, 'Green Slime', self.game)
            self.enemies.add(e)
            self.all_sprites.add(e)
            
        for _ in range(num_demons):
            rx = random.randint(2, w_grid - 3) * tile_w
            ry = random.randint(2, h_grid - 3) * tile_h
            e = Enemy(rx, ry, 'Fire Demon', self.game)
            self.enemies.add(e)
            self.all_sprites.add(e)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_p, pygame.K_ESCAPE):
                self.game.fsm.change('PAUSE')

    def update(self, dt):
        self.all_sprites.update(dt)
        if self.player:
            self.all_sprites.update_camera(self.player, dt)
        self.game.collision_manager.update()
        
        if self.player.hp <= 0:
            self.needs_reset = True
            self.game.fsm.change('GAME_OVER')
            
        if len(self.enemies) == 0 and self.portal is None:
            self.portal = Portal(self.player.pos.x, self.player.pos.y - 150, self.game)
            self.all_sprites.add(self.portal)

    def draw(self, screen):
        screen.fill((0, 0, 0))
        self.all_sprites.draw(screen)
        self.hud.draw(screen)

class Game:
    def __init__(self):
        pygame.init()
        self._read_json_only()
        
        cfg = self.config.data.get('config', {})
        screen_size = cfg.get('SCREEN_SIZE', [1280, 720])
        self.screen = pygame.display.set_mode((screen_size[0], screen_size[1]))
        
        self.asset_manager = AssetManager()
        self.asset_manager.load_assets(self.config.data)
        
        self.projectile_pool = ObjectPool(lambda: MagicBolt(self))
        self.particle_pool = ObjectPool(lambda: EnemyDeathParticle(self))
        self.collision_manager = CollisionManager(self)
        
        self.fsm = FSM()
        self.fsm.add('MENU', MenuState(self))
        self.fsm.add('PLAYING', PlayingState(self))
        self.fsm.add('PAUSE', PauseState(self))
        self.fsm.add('RULES', RulesState(self))
        self.fsm.add('UPGRADE_MENU', UpgradeState(self))
        self.fsm.add('GAME_OVER', GameOverState(self))
        self.fsm.add('QUIT', QuitState(self))
        
        self.clock = pygame.time.Clock()
        self.fps = cfg.get('FPS', 60)
        self.running = True

    def _read_json_only(self):
        self.config = GameConfig()
        config_path = os.path.join(os.path.dirname(__file__), 'game_config.json')
        if os.path.exists(config_path):
            self.config.load(config_path)

    def run(self):
        if getattr(self.fsm, 'current_state', None) is None:
            self.fsm.change('MENU')
            
        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.fsm.current_state:
                    self.fsm.states[self.fsm.current_state].handle_event(event)
                    
            if self.fsm.current_state:
                self.fsm.states[self.fsm.current_state].update(dt)
                self.fsm.states[self.fsm.current_state].draw(self.screen)
                
            pygame.display.flip()
            
        pygame.quit()

if __name__ == '__main__':
    Game().run()