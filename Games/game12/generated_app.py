import pygame
import sys
import os
import json
import math
import random
import heapq

# ==========================================
# CONFIGURATION & ASSET MANAGEMENT
# ==========================================

class GameConfig:
    def __init__(self):
        self.game_name = "Rogue Survival"
        self.fps = 60
        self.screen_size = (1280, 720)
        self.entities = {}

    def load(self, data):
        self.game_name = data.get('game_name', self.game_name)
        cfg = data.get('config', {})
        self.fps = cfg.get('FPS', self.fps)
        self.screen_size = tuple(cfg.get('SCREEN_SIZE', self.screen_size))
        
        for entity in data.get('entities', []):
            name = entity.get('name')
            if name:
                self.entities[name] = entity

    def get_entity(self, name):
        return self.entities.get(name) or {}

    def get_prop(self, entity_name, prop_name, default_value):
        entity = self.get_entity(entity_name)
        props = entity.get('properties', {})
        return props.get(prop_name, default_value)


class AssetManager:
    def __init__(self):
        self.images = {}
        self.base_dir = os.path.join(os.path.dirname(__file__), 'assets')

    def load_assets(self, config_data):
        for entity in config_data.get('entities', []):
            filename = entity.get('image')
            props = entity.get('properties', {})
            scale = props.get('IMAGE_SCALE', 1.0)
            
            if filename and filename not in self.images:
                filepath = os.path.join(self.base_dir, filename)
                try:
                    image = pygame.image.load(filepath).convert_alpha()
                    
                    bounding_rect = image.get_bounding_rect()
                    if bounding_rect.width > 0 and bounding_rect.height > 0:
                        image = image.subsurface(bounding_rect).copy()
                    
                    new_size = (int(image.get_width() * scale), int(image.get_height() * scale))
                    if new_size[0] > 0 and new_size[1] > 0:
                        image = pygame.transform.scale(image, new_size)
                        
                    self.images[filename] = image
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")
                    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                    surf.fill((255, 0, 255))
                    self.images[filename] = surf

    def get_image(self, filename):
        return self.images.get(filename)

# ==========================================
# UTILITIES
# ==========================================

class ObjectPool:
    def __init__(self, create_func):
        self.pool = []
        self.create_func = create_func

    def get(self, *args, **kwargs):
        if self.pool:
            obj = self.pool.pop()
            obj.__init__(*args, **kwargs)
            return obj
        return self.create_func(*args, **kwargs)

    def release(self, obj):
        if obj.groups():
            obj.kill()
        if obj not in self.pool:
            self.pool.append(obj)

class SpatialGrid:
    def __init__(self, cell_size=100):
        self.cell_size = cell_size
        self.grid = {}

    def clear(self):
        self.grid.clear()

    def _get_cell_coords(self, rect):
        min_x = int(rect.left // self.cell_size)
        max_x = int(rect.right // self.cell_size)
        min_y = int(rect.top // self.cell_size)
        max_y = int(rect.bottom // self.cell_size)
        return min_x, max_x, min_y, max_y

    def insert(self, entity):
        min_x, max_x, min_y, max_y = self._get_cell_coords(entity.hitbox)
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                cell = (x, y)
                if cell not in self.grid:
                    self.grid[cell] = []
                self.grid[cell].append(entity)

    def query_rect(self, rect):
        found = set()
        min_x, max_x, min_y, max_y = self._get_cell_coords(rect)
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                cell = (x, y)
                if cell in self.grid:
                    for entity in self.grid[cell]:
                        found.add(entity)
        return list(found)

class CollisionManager:
    @staticmethod
    def apply_sprite_vs_group(sprite, group, collided=None):
        if collided is None:
            collided = lambda s, o: s.hitbox.colliderect(o.hitbox)
        return [other for other in group if collided(sprite, other)]

    @staticmethod
    def apply_group_vs_group(group1, group2, collided=None):
        collisions = []
        for sprite1 in group1:
            for sprite2 in group2:
                if collided is None:
                    if sprite1.hitbox.colliderect(sprite2.hitbox):
                        collisions.append((sprite1, sprite2))
                else:
                    if collided(sprite1, sprite2):
                        collisions.append((sprite1, sprite2))
        return collisions

class CameraGroup(pygame.sprite.Group):
    def __init__(self, screen_size):
        super().__init__()
        self.offset = pygame.math.Vector2()
        self.screen_width = screen_size[0]
        self.screen_height = screen_size[1]
        self.bg_image = None

    def set_bg(self, image):
        self.bg_image = image
        
    def center_on_target(self, target):
        self.offset.x = target.rect.centerx - self.screen_width // 2
        self.offset.y = target.rect.centery - self.screen_height // 2

    def custom_draw(self, surface, target):
        self.center_on_target(target)

        if self.bg_image:
            bg_w = self.bg_image.get_width()
            bg_h = self.bg_image.get_height()
            start_x = -int(self.offset.x % bg_w)
            start_y = -int(self.offset.y % bg_h)
            for x in range(start_x - bg_w, self.screen_width + bg_w, bg_w):
                for y in range(start_y - bg_h, self.screen_height + bg_h, bg_h):
                    surface.blit(self.bg_image, (x, y))

        for sprite in sorted(self.sprites(), key=lambda sprite: sprite.rect.bottom):
            offset_pos = sprite.rect.topleft - self.offset
            surface.blit(sprite.image, offset_pos)

# ==========================================
# PATHFINDING
# ==========================================

class AStarPathfinder:
    def __init__(self, cell_size=50):
        self.cell_size = cell_size

    def get_path(self, start_pos, target_pos, obstacles):
        def get_coord(pos):
            return (int(pos[0] // self.cell_size), int(pos[1] // self.cell_size))
        
        start = get_coord(start_pos)
        target = get_coord(target_pos)
        
        if start == target:
            return []

        blocked = set()
        for obs in obstacles:
            ox, oy = get_coord(obs.hitbox.center)
            blocked.add((ox, oy))
        
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self._heuristic(start, target)}
        
        iterations = 0
        while open_set and iterations < 200:
            iterations += 1
            _, current = heapq.heappop(open_set)
            
            if current == target:
                return self._reconstruct_path(came_from, current)
                
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor in blocked:
                    continue
                
                tentative_g = g_score[current] + math.hypot(dx, dy)
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, target)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    
        return []

    def _heuristic(self, a, b):
        return math.hypot(a[0]-b[0], a[1]-b[1])

    def _reconstruct_path(self, came_from, current):
        path = []
        while current in came_from:
            path.append((current[0] * self.cell_size + self.cell_size//2, 
                         current[1] * self.cell_size + self.cell_size//2))
            current = came_from[current]
        path.reverse()
        return path

class FlowFieldPathfinder:
    def __init__(self, cell_size=100):
        self.cell_size = cell_size
        self.flow_field = {}
        self.target = None

    def update(self, target_pos, obstacles):
        self.flow_field.clear()
        
        def get_coord(pos):
            return (int(pos[0] // self.cell_size), int(pos[1] // self.cell_size))
            
        self.target = get_coord(target_pos)
        
        blocked = set()
        for obs in obstacles:
            ox, oy = get_coord(obs.hitbox.center)
            blocked.add((ox, oy))
            
        queue = [self.target]
        cost_so_far = {self.target: 0}
        
        iterations = 0
        while queue and iterations < 1000:
            current = queue.pop(0)
            iterations += 1
            
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor in blocked:
                    continue
                new_cost = cost_so_far[current] + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    queue.append(neighbor)
                    
                    dir_x = current[0] - neighbor[0]
                    dir_y = current[1] - neighbor[1]
                    norm = math.hypot(dir_x, dir_y)
                    if norm > 0:
                        self.flow_field[neighbor] = (dir_x/norm, dir_y/norm)

    def get_dir(self, pos):
        coord = (int(pos[0] // self.cell_size), int(pos[1] // self.cell_size))
        return self.flow_field.get(coord, None)

# ==========================================
# GAME ENTITIES
# ==========================================

class GameSprite(pygame.sprite.Sprite):
    def __init__(self, pool=None, groups=None, **kwargs):
        super().__init__(groups or [])
        self.pool = pool

class Entity(GameSprite):
    def __init__(self, image, pos, pool=None, groups=None, is_static=False, is_one_way=False, **kwargs):
        super().__init__(pool=pool, groups=groups, **kwargs)
        self.image = image
        self.rect = self.image.get_rect(center=pos)
        
        if is_static:
            self.hitbox = self.rect.copy()
        else:
            self.hitbox = self.rect.inflate(-int(self.rect.width * 0.2), -int(self.rect.height * 0.2))
            
        self.hitbox.center = self.rect.center
        self.is_static = is_static
        self.is_one_way = is_one_way
        self.vel_x = 0
        self.vel_y = 0

    def update_rect_from_hitbox(self):
        self.rect.centerx = self.hitbox.centerx
        self.rect.midbottom = self.hitbox.midbottom

    def move(self, dx, dy, obstacles):
        if dx != 0:
            self.hitbox.x += dx
            self.check_collisions(obstacles, 'x', dx)
        if dy != 0:
            self.hitbox.y += dy
            self.check_collisions(obstacles, 'y', dy)
        self.update_rect_from_hitbox()

    def check_collisions(self, obstacles, direction, delta):
        hit_obs = CollisionManager.apply_sprite_vs_group(self, obstacles)
        for obstacle in hit_obs:
            if obstacle.is_one_way:
                if direction == 'y' and delta > 0:
                    if self.hitbox.bottom - delta <= obstacle.hitbox.top:
                        self.hitbox.bottom = obstacle.hitbox.top
                        self.vel_y = 0
            else:
                if direction == 'x':
                    if delta > 0:
                        self.hitbox.right = obstacle.hitbox.left
                    elif delta < 0:
                        self.hitbox.left = obstacle.hitbox.right
                elif direction == 'y':
                    if delta > 0:
                        self.hitbox.bottom = obstacle.hitbox.top
                        self.vel_y = 0
                    elif delta < 0:
                        self.hitbox.top = obstacle.hitbox.bottom

class Player(Entity):
    def __init__(self, pos, image, config, pool=None, groups=None, **kwargs):
        super().__init__(image, pos, pool=pool, groups=groups, is_static=False, **kwargs)
        self.speed = config.get_prop('Player', 'PLAYER_SPEED', 5.0)
        self.max_hp = config.get_prop('Player', 'PLAYER_HP', 100)
        self.hp = self.max_hp
        self.cooldown_max = config.get_prop('Player', 'PLAYER_COOLDOWN', 0.5) * 60
        self.cooldown = 0
        self.xp = 0
        self.level = 1
        self.damage = config.get_prop('PlayerProjectile', 'PROJECTILE_DAMAGE', 15)

    def update(self, obstacles, keys):
        dx, dy = 0, 0
        if keys[pygame.K_w]: dy -= self.speed
        if keys[pygame.K_s]: dy += self.speed
        if keys[pygame.K_a]: dx -= self.speed
        if keys[pygame.K_d]: dx += self.speed

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.move(dx, dy, obstacles)
        
        if self.cooldown > 0:
            self.cooldown -= 1

    def shoot(self, target_pos, offset, proj_pool, proj_group, all_sprites, proj_image, config):
        if self.cooldown <= 0:
            self.cooldown = self.cooldown_max
            start_pos = (self.hitbox.centerx, self.hitbox.centery)
            real_target = (target_pos[0] + offset.x, target_pos[1] + offset.y)
            angle = math.atan2(real_target[1] - start_pos[1], real_target[0] - start_pos[0])
            
            proj = proj_pool.get(start_pos, angle, proj_image, config, pool=proj_pool, damage=self.damage)
            proj_group.add(proj)
            all_sprites.add(proj)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0

class Enemy(Entity):
    def __init__(self, pos, image, config, entity_name, pool=None, groups=None, **kwargs):
        super().__init__(image, pos, pool=pool, groups=groups, is_static=False, **kwargs)
        if 'Elite' in entity_name:
            ent = 'ELITE'
        else:
            ent = 'ENEMY'
            
        self.speed = config.get_prop(entity_name, f'{ent}_SPEED', 3.0)
        self.hp = config.get_prop(entity_name, f'{ent}_HP', 20)
        self.damage = config.get_prop(entity_name, f'{ent}_DAMAGE', 10)
        attack_cd = config.get_prop(entity_name, f'{ent}_ATTACK_COOLDOWN', 2.0)
        self.attack_cd_max = attack_cd * 60
        self.attack_cd = 0
        self.push_vec = pygame.math.Vector2(0, 0)

    def update(self, player, obstacles, pathfinders=None):
        pass

class RegularEnemy(Enemy):
    def __init__(self, pos, image, config, pool=None, groups=None, **kwargs):
        super().__init__(pos, image, config, 'RegularEnemy', pool=pool, groups=groups, **kwargs)

    def update(self, player, obstacles, pathfinders=None):
        if self.attack_cd > 0:
            self.attack_cd -= 1

        move_x, move_y = 0, 0
        if pathfinders and pathfinders.get('flow_field'):
            ff = pathfinders['flow_field']
            direction = ff.get_dir(self.hitbox.center)
            if direction:
                move_x, move_y = direction[0] * self.speed, direction[1] * self.speed
            else:
                dx = player.hitbox.centerx - self.hitbox.centerx
                dy = player.hitbox.centery - self.hitbox.centery
                dist = math.hypot(dx, dy)
                if dist > 0:
                    move_x, move_y = (dx / dist) * self.speed, (dy / dist) * self.speed
        
        move_x += self.push_vec.x
        move_y += self.push_vec.y
        self.push_vec *= 0.8
        
        self.move(move_x, move_y, obstacles)

class EliteEnemy(Enemy):
    def __init__(self, pos, image, config, pool=None, groups=None, **kwargs):
        super().__init__(pos, image, config, 'EliteEnemy', pool=pool, groups=groups, **kwargs)
        self.path = []
        self.path_cd = 0

    def update(self, player, obstacles, pathfinders=None):
        if self.attack_cd > 0:
            self.attack_cd -= 1

        move_x, move_y = 0, 0
        
        if pathfinders and pathfinders.get('astar'):
            if self.path_cd <= 0:
                self.path = pathfinders['astar'].get_path(self.hitbox.center, player.hitbox.center, obstacles)
                self.path_cd = 30
            else:
                self.path_cd -= 1

            if self.path:
                target = self.path[0]
                dx = target[0] - self.hitbox.centerx
                dy = target[1] - self.hitbox.centery
                dist = math.hypot(dx, dy)
                if dist < 10:
                    self.path.pop(0)
                if dist > 0:
                    move_x, move_y = (dx / dist) * self.speed, (dy / dist) * self.speed
            else:
                dx = player.hitbox.centerx - self.hitbox.centerx
                dy = player.hitbox.centery - self.hitbox.centery
                dist = math.hypot(dx, dy)
                if dist > 0:
                    move_x, move_y = (dx / dist) * self.speed, (dy / dist) * self.speed
                    
        move_x += self.push_vec.x
        move_y += self.push_vec.y
        self.push_vec *= 0.8
        
        self.move(move_x, move_y, obstacles)

class PlayerProjectile(Entity):
    def __init__(self, pos, angle, image, config, pool=None, groups=None, damage=None, **kwargs):
        super().__init__(image, pos, pool=pool, groups=groups, is_static=False, **kwargs)
        self.speed = config.get_prop('PlayerProjectile', 'PROJECTILE_SPEED', 8.0)
        self.damage = damage if damage is not None else config.get_prop('PlayerProjectile', 'PROJECTILE_DAMAGE', 15)
        lifetime_sec = config.get_prop('PlayerProjectile', 'PROJECTILE_LIFETIME', 1.5)
        self.lifetime = lifetime_sec * 60
        self.dx = math.cos(angle) * self.speed
        self.dy = math.sin(angle) * self.speed
        self.active = True

    def update(self, obstacles, **kwargs):
        if not self.active: return
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.active = False
            return
        
        self.move(self.dx, self.dy, obstacles)
        
        hit_obs = CollisionManager.apply_sprite_vs_group(self, obstacles)
        if hit_obs:
            self.active = False

class ExperienceGem(Entity):
    def __init__(self, pos, image, config, pool=None, groups=None, **kwargs):
        super().__init__(image, pos, pool=pool, groups=groups, is_static=True, **kwargs)
        self.value = config.get_prop('ExperienceGem', 'XP_VALUE', 10)
        self.active = True

    def update(self, *args, **kwargs):
        pass

class StaticObstacle(Entity):
    def __init__(self, pos, image, config, entity_name, pool=None, groups=None, **kwargs):
        col_type = config.get_prop(entity_name, 'COLLISION_TYPE', 'solid')
        is_one_way = (col_type == 'one_way')
        super().__init__(image, pos, pool=pool, groups=groups, is_static=True, is_one_way=is_one_way, **kwargs)

# ==========================================
# UI COMPONENTS
# ==========================================

class UIButton:
    def __init__(self, rect, image, text, callback):
        self.rect = pygame.Rect(rect)
        self.image = pygame.transform.scale(image, (self.rect.width, self.rect.height))
        self.text = text
        self.callback = callback
        self.font = pygame.font.Font(None, 36)
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered and self.callback:
                self.callback()

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        color = (255, 255, 0) if self.hovered else (255, 255, 255)
        text_surf = self.font.render(self.text, True, color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

class UIManager:
    def __init__(self):
        self.elements = []

    def add(self, element):
        self.elements.append(element)

    def handle_event(self, event):
        for el in self.elements:
            el.handle_event(event)

    def draw(self, surface):
        for el in self.elements:
            el.draw(surface)

    def clear(self):
        self.elements.clear()

# ==========================================
# GAME STATES & FSM
# ==========================================

class State:
    def __init__(self, fsm):
        self.fsm = fsm
    def enter(self): pass
    def exit(self): pass
    def update(self): pass
    def draw(self, surface): pass
    def handle_event(self, event): pass

class StartupMenuState(State):
    def enter(self):
        self.ui = UIManager()
        cx = self.fsm.game.config.screen_size[0] // 2
        cy = self.fsm.game.config.screen_size[1] // 2
        
        btn_img1 = self.fsm.game.assets.get_image("[sprite]button_game_start.png")
        btn_img2 = self.fsm.game.assets.get_image("[sprite]button_rules.png")
        btn_img3 = self.fsm.game.assets.get_image("[sprite]button_quit.png")
        
        self.ui.add(UIButton((cx - 100, cy - 80, 200, 50), btn_img1, "GAME START", lambda: self.fsm.change("PLAYING")))
        self.ui.add(UIButton((cx - 100, cy, 200, 50), btn_img2, "RULES", lambda: self.fsm.change("RULES")))
        self.ui.add(UIButton((cx - 100, cy + 80, 200, 50), btn_img3, "QUIT", lambda: sys.exit()))

    def handle_event(self, event):
        self.ui.handle_event(event)

    def draw(self, surface):
        surface.fill((30, 30, 40))
        self.ui.draw(surface)

class RulesState(State):
    def enter(self):
        self.ui = UIManager()
        cx = self.fsm.game.config.screen_size[0] // 2
        cy = self.fsm.game.config.screen_size[1] // 2
        btn_img = self.fsm.game.assets.get_image("[sprite]button_back_to_main.png")
        self.ui.add(UIButton((cx - 100, cy + 200, 200, 50), btn_img, "BACK", lambda: self.fsm.change("STARTUP_MENU")))
        self.font = pygame.font.Font(None, 32)

    def handle_event(self, event):
        self.ui.handle_event(event)

    def draw(self, surface):
        surface.fill((30, 30, 40))
        rules = [
            "ROGUE SURVIVAL - RULES",
            "WASD to Move. Mouse to Aim & Shoot automatically.",
            "Survive the waves of enemies.",
            "Collect Gems to Level Up.",
            "Press ESC to pause."
        ]
        for i, text in enumerate(rules):
            surf = self.font.render(text, True, (200, 200, 200))
            rect = surf.get_rect(center=(self.fsm.game.config.screen_size[0]//2, 100 + i * 40))
            surface.blit(surf, rect)
        self.ui.draw(surface)

class PauseMenuState(State):
    def enter(self):
        self.ui = UIManager()
        cx = self.fsm.game.config.screen_size[0] // 2
        cy = self.fsm.game.config.screen_size[1] // 2
        
        i1 = self.fsm.game.assets.get_image("[sprite]button_continue.png")
        i2 = self.fsm.game.assets.get_image("[sprite]button_restart.png")
        i3 = self.fsm.game.assets.get_image("[sprite]button_rules.png")
        i4 = self.fsm.game.assets.get_image("[sprite]button_back_to_main.png")
        
        self.ui.add(UIButton((cx - 125, cy - 120, 250, 50), i1, "CONTINUE", lambda: self.fsm.change("PLAYING")))
        self.ui.add(UIButton((cx - 125, cy - 50, 250, 50), i2, "RESTART", self.restart_game))
        self.ui.add(UIButton((cx - 125, cy + 20, 250, 50), i3, "RULES", lambda: self.fsm.change("RULES")))
        self.ui.add(UIButton((cx - 125, cy + 90, 250, 50), i4, "BACK TO MAIN MENU", self.back_to_main))

    def restart_game(self):
        self.fsm.get_state("PLAYING")._setup_new_game()
        self.fsm.change("PLAYING")

    def back_to_main(self):
        self.fsm.get_state("PLAYING").game_started = False
        self.fsm.change("STARTUP_MENU")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_ESCAPE or event.key == pygame.K_p):
            self.fsm.change("PLAYING")
        self.ui.handle_event(event)

    def draw(self, surface):
        overlay = pygame.Surface(self.fsm.game.config.screen_size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        self.ui.draw(surface)

class GameOverState(State):
    def enter(self):
        self.ui = UIManager()
        cx = self.fsm.game.config.screen_size[0] // 2
        cy = self.fsm.game.config.screen_size[1] // 2
        i1 = self.fsm.game.assets.get_image("[sprite]button_restart.png")
        i2 = self.fsm.game.assets.get_image("[sprite]button_back_to_main.png")
        
        self.ui.add(UIButton((cx - 125, cy, 250, 50), i1, "RESTART", self.restart_game))
        self.ui.add(UIButton((cx - 125, cy + 70, 250, 50), i2, "BACK TO MAIN MENU", self.back_to_main))
        self.font = pygame.font.Font(None, 64)

    def restart_game(self):
        self.fsm.get_state("PLAYING")._setup_new_game()
        self.fsm.change("PLAYING")

    def back_to_main(self):
        self.fsm.get_state("PLAYING").game_started = False
        self.fsm.change("STARTUP_MENU")

    def handle_event(self, event):
        self.ui.handle_event(event)

    def draw(self, surface):
        surface.fill((50, 10, 10))
        text = self.font.render("GAME OVER", True, (255, 50, 50))
        surface.blit(text, text.get_rect(center=(self.fsm.game.config.screen_size[0]//2, self.fsm.game.config.screen_size[1]//2 - 100)))
        self.ui.draw(surface)

class LevelUpState(State):
    def enter(self):
        self.ui = UIManager()
        cx = self.fsm.game.config.screen_size[0] // 2
        cy = self.fsm.game.config.screen_size[1] // 2
        btn_img = self.fsm.game.assets.get_image("[sprite]button_continue.png")
        
        self.ui.add(UIButton((cx - 150, cy - 80, 300, 50), btn_img, "SELECT UPGRADE: DAMAGE", lambda: self.apply_upgrade('damage')))
        self.ui.add(UIButton((cx - 150, cy, 300, 50), btn_img, "SELECT UPGRADE: SPEED", lambda: self.apply_upgrade('speed')))
        self.ui.add(UIButton((cx - 150, cy + 80, 300, 50), btn_img, "SELECT UPGRADE: HEALTH", lambda: self.apply_upgrade('health')))
        self.font = pygame.font.Font(None, 48)

    def apply_upgrade(self, upgrade_type):
        playing = self.fsm.get_state("PLAYING")
        if upgrade_type == 'damage':
            playing.player.damage += 5
        elif upgrade_type == 'speed':
            playing.player.speed += 1.0
        elif upgrade_type == 'health':
            playing.player.max_hp += 20
            playing.player.hp += 20
            
        playing.wave += 1
        playing.start_wave()
        self.fsm.change("PLAYING")

    def handle_event(self, event):
        self.ui.handle_event(event)

    def draw(self, surface):
        surface.fill((10, 50, 10))
        text = self.font.render("LEVEL CLEAR!", True, (50, 255, 50))
        surface.blit(text, text.get_rect(center=(self.fsm.game.config.screen_size[0]//2, self.fsm.game.config.screen_size[1]//2 - 150)))
        self.ui.draw(surface)

class PlayingState(State):
    def __init__(self, fsm):
        super().__init__(fsm)
        self.game_started = False
        self.proj_pool = ObjectPool(PlayerProjectile)
        self.gem_pool = ObjectPool(ExperienceGem)
        self.enemy_pool = ObjectPool(RegularEnemy)
        self.elite_pool = ObjectPool(EliteEnemy)
        self.font = pygame.font.Font(None, 36)
        self.flow_field = FlowFieldPathfinder(cell_size=100)
        self.astar = AStarPathfinder(cell_size=50)

    def enter(self):
        if not self.game_started:
            self._setup_new_game()
            self.game_started = True

    def _setup_new_game(self):
        self.all_sprites = CameraGroup(self.fsm.game.config.screen_size)
        self.all_sprites.set_bg(self.fsm.game.assets.get_image("[background]game_map_tile.png"))
        
        self.obstacles = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.gems = pygame.sprite.Group()
        
        self.spatial_grid = SpatialGrid(200)

        p_img = self.fsm.game.assets.get_image("[sprite]player.png")
        self.player = Player((0, 0), p_img, self.fsm.game.config)
        self.all_sprites.add(self.player)

        self._generate_level()
        self.all_sprites.center_on_target(self.player)
        self.wave = 1
        self.start_wave()

    def _generate_level(self):
        wall_img = self.fsm.game.assets.get_image("[background]wall_tile.png")
        plat_img = self.fsm.game.assets.get_image("[background]platform_one_way.png")
        
        for _ in range(15):
            x = random.randint(-1000, 1000)
            y = random.randint(-1000, 1000)
            if math.hypot(x, y) < 200: continue
            
            is_plat = random.choice([True, False])
            img = plat_img if is_plat else wall_img
            name = "Platform" if is_plat else "WallObstacle"
            obs = StaticObstacle((x, y), img, self.fsm.game.config, name)
            self.obstacles.add(obs)
            self.all_sprites.add(obs)

    def start_wave(self):
        enemy_count = 5 + self.wave * 2
        e_img = self.fsm.game.assets.get_image("[sprite]enemy_basic.png")
        elite_img = self.fsm.game.assets.get_image("[sprite]enemy_elite.png")
        if not elite_img:
            elite_img = e_img
        
        for _ in range(enemy_count):
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(500, 800)
            x = self.player.hitbox.centerx + math.cos(angle) * dist
            y = self.player.hitbox.centery + math.sin(angle) * dist
            
            enemy = self.enemy_pool.get((x, y), e_img, self.fsm.game.config, pool=self.enemy_pool)
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)

        elite_count = self.wave // 2 + 1
        for _ in range(elite_count):
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(600, 900)
            x = self.player.hitbox.centerx + math.cos(angle) * dist
            y = self.player.hitbox.centery + math.sin(angle) * dist
            
            elite = self.elite_pool.get((x, y), elite_img, self.fsm.game.config, pool=self.elite_pool)
            self.enemies.add(elite)
            self.all_sprites.add(elite)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_ESCAPE or event.key == pygame.K_p):
            self.fsm.change("PAUSE_MENU")

    def update(self):
        keys = pygame.key.get_pressed()
        self.player.update(self.obstacles.sprites(), keys)

        mouse_pos = pygame.mouse.get_pos()
        p_img = self.fsm.game.assets.get_image("[sprite]projectile_bullet.png")
        self.player.shoot(mouse_pos, self.all_sprites.offset, self.proj_pool, self.projectiles, self.all_sprites, p_img, self.fsm.game.config)

        self.spatial_grid.clear()
        for e in self.enemies:
            self.spatial_grid.insert(e)

        self.flow_field.update(self.player.hitbox.center, self.obstacles.sprites())
        pathfinders = {'flow_field': self.flow_field, 'astar': self.astar}

        enemy_collisions = CollisionManager.apply_group_vs_group(self.enemies.sprites(), self.enemies.sprites())
        for e1, e2 in enemy_collisions:
            if e1 != e2:
                dist = math.hypot(e1.hitbox.centerx - e2.hitbox.centerx, e1.hitbox.centery - e2.hitbox.centery)
                if 0 < dist < 40:
                    force = (40 - dist) / 80.0
                    dx = (e1.hitbox.centerx - e2.hitbox.centerx) / dist
                    dy = (e1.hitbox.centery - e2.hitbox.centery) / dist
                    e1.push_vec.x += dx * force
                    e1.push_vec.y += dy * force

        enemy_list = self.enemies.sprites()
        for e1 in enemy_list:
            e1.update(self.player, self.obstacles.sprites(), pathfinders=pathfinders)

        hit_enemies = CollisionManager.apply_sprite_vs_group(self.player, self.enemies.sprites())
        for e1 in hit_enemies:
            if e1.attack_cd <= 0:
                self.player.take_damage(e1.damage)
                e1.attack_cd = e1.attack_cd_max
                if self.player.hp <= 0:
                    self.fsm.change("GAME_OVER")
                    return

        for p in self.projectiles.sprites():
            p.update(self.obstacles.sprites())
            if not p.active:
                if p.pool:
                    p.pool.release(p)
                else:
                    p.kill()
                continue
                
            nearby_enemies = self.spatial_grid.query_rect(p.hitbox)
            hit_enem = CollisionManager.apply_sprite_vs_group(p, nearby_enemies)
            for e in hit_enem:
                e.hp -= p.damage
                p.active = False
                if e.hp <= 0:
                    gem_img = self.fsm.game.assets.get_image("[sprite]item_xp_gem.png")
                    gem = self.gem_pool.get(e.rect.center, gem_img, self.fsm.game.config, pool=self.gem_pool)
                    self.gems.add(gem)
                    self.all_sprites.add(gem)
                    if e.pool:
                        e.pool.release(e)
                    else:
                        e.kill()
                if p.pool:
                    p.pool.release(p)
                else:
                    p.kill()
                break

        hit_gems = CollisionManager.apply_sprite_vs_group(self.player, self.gems.sprites())
        for g in hit_gems:
            self.player.xp += g.value
            if g.pool:
                g.pool.release(g)
            else:
                g.kill()

        if len(self.enemies) == 0:
            self.fsm.change("LEVEL_UP")

    def draw(self, surface):
        self.all_sprites.custom_draw(surface, self.player)
        
        hp_text = self.font.render(f"HP: {self.player.hp}/{self.player.max_hp}", True, (255, 50, 50))
        wave_text = self.font.render(f"WAVE: {self.wave}", True, (255, 255, 255))
        xp_text = self.font.render(f"XP: {self.player.xp}", True, (50, 255, 255))
        
        surface.blit(hp_text, (10, 10))
        surface.blit(wave_text, (10, 40))
        surface.blit(xp_text, (10, 70))


class FSM:
    def __init__(self, game):
        self.game = game
        self.states = {}
        self.current_state = None

    def add(self, name, state):
        self.states[name] = state

    def change(self, name):
        if self.current_state:
            self.states[self.current_state].exit()
        self.current_state = name
        self.states[self.current_state].enter()

    def get_state(self, name):
        return self.states.get(name)

    def update(self):
        if self.current_state:
            self.states[self.current_state].update()

    def draw(self, surface):
        if self.current_state:
            self.states[self.current_state].draw(surface)

    def handle_event(self, event):
        if self.current_state:
            self.states[self.current_state].handle_event(event)

# ==========================================
# MAIN GAME CLASS
# ==========================================

class Game:
    def __init__(self):
        pygame.init()
        
        self.config = GameConfig()
        self._read_json_only()
        
        self.screen = pygame.display.set_mode(self.config.screen_size)
        pygame.display.set_caption(self.config.game_name)
        
        self.assets = AssetManager()
        raw_data = {"entities": []}
        for name, ent in self.config.entities.items():
            raw_data["entities"].append(ent)
        self.assets.load_assets(raw_data)
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.fsm = FSM(self)
        self.fsm.add('STARTUP_MENU', StartupMenuState(self.fsm))
        self.fsm.add('PLAYING', PlayingState(self.fsm))
        self.fsm.add('PAUSE_MENU', PauseMenuState(self.fsm))
        self.fsm.add('RULES', RulesState(self.fsm))
        self.fsm.add('GAME_OVER', GameOverState(self.fsm))
        self.fsm.add('LEVEL_UP', LevelUpState(self.fsm))

    def _read_json_only(self):
        config_path = os.path.join(os.path.dirname(__file__), 'game_config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.config.load(data)
        except Exception as e:
            print(f"Error loading config: {e}")

    def run(self):
        if getattr(self.fsm, 'current_state', None) is None:
            self.fsm.change('STARTUP_MENU')

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.fsm.handle_event(event)

            self.fsm.update()
            
            self.screen.fill((0, 0, 0))
            self.fsm.draw(self.screen)
            pygame.display.flip()
            
            self.clock.tick(self.config.fps)
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()