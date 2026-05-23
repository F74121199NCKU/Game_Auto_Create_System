import os
import sys
import json
import math
import random
import pygame

try:
    from collision import CollisionManager
except ImportError:
    # Fallback RAG integration for CollisionManager
    class CollisionManager:
        def __init__(self, game):
            self.game = game

        def apply_sprite_vs_group(self, sprite, group, axis):
            hits = pygame.sprite.spritecollide(sprite, group, False, collided=lambda s1, s2: s1.hitbox.colliderect(s2.hitbox))
            if hits:
                hit_sprite = hits[0]
                if axis == 'x':
                    if sprite.vel_x > 0: 
                        sprite.hitbox.right = hit_sprite.hitbox.left
                    else: 
                        sprite.hitbox.left = hit_sprite.hitbox.right
                    sprite.vel_x *= -1
                elif axis == 'y':
                    if sprite.vel_y > 0: 
                        sprite.hitbox.bottom = hit_sprite.hitbox.top
                    else: 
                        sprite.hitbox.top = hit_sprite.hitbox.bottom
                    sprite.vel_y *= -1
                return hit_sprite
            return None

# ==========================================
# CONFIGURATION & DATA MANAGEMENT
# ==========================================
class GameConfig:
    def __init__(self):
        self.data = {}

    def get_entity(self, name):
        for e in self.data.get('entities', []):
            if e.get('name') == name:
                return e
        return None

    def get_prop(self, entity_name, prop_name, default_value):
        entity = self.get_entity(entity_name) or {}
        props = entity.get('properties', {})
        return props.get(prop_name, default_value)

class AssetManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                pass

    def load_assets(self, data):
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        
        # Load Images
        for ent in data.get('entities', []):
            filename = ent.get('image')
            if filename:
                path = os.path.join(assets_dir, filename)
                try:
                    img = pygame.image.load(path).convert_alpha()
                    
                    bounding_rect = img.get_bounding_rect()
                    if bounding_rect.width > 0 and bounding_rect.height > 0:
                        img = img.subsurface(bounding_rect).copy()

                    scale = ent.get('properties', {}).get('IMAGE_SCALE', 1.0)
                    if scale != 1.0:
                        new_width = max(1, int(img.get_width() * scale))
                        new_height = max(1, int(img.get_height() * scale))
                        img = pygame.transform.scale(img, (new_width, new_height))
                        
                    self.images[ent['name']] = img
                except Exception:
                    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                    surf.fill((255, 0, 255))
                    self.images[ent['name']] = surf
                    
        # Load Audio / SFX
        sfx_files = {
            'BLOCK_DESTROY_SFX': 'block_destroy.wav',
            'WALL_HIT_SFX': 'wall_hit.wav',
            'LIFE_LOST_SFX': 'life_lost.wav'
        }
        for name, filename in sfx_files.items():
            path = os.path.join(assets_dir, filename)
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except Exception:
                    self.sounds[name] = None

    def get(self, name):
        return self.images.get(name)

    def play_sfx(self, name):
        if name in self.sounds and self.sounds[name]:
            try:
                self.sounds[name].play()
            except Exception:
                pass

# ==========================================
# STATE MACHINE & OBJECT POOL
# ==========================================
class StateMachine:
    def __init__(self):
        self.states = {}
        self.current_state = None
        self.state_name = None

    def add(self, name, state):
        self.states[name] = state

    def change(self, name):
        if self.current_state:
            self.current_state.exit()
        self.state_name = name
        self.current_state = self.states[name]
        self.current_state.enter()

    def update(self, dt):
        if self.current_state:
            self.current_state.update(dt)

    def draw(self, surface):
        if self.current_state:
            self.current_state.draw(surface)

    def handle_event(self, event):
        if self.current_state:
            self.current_state.handle_event(event)

class ObjectPool:
    def __init__(self, create_func, size):
        self.pool = [create_func() for _ in range(size)]
        
    def get(self):
        for obj in self.pool:
            if not obj.active:
                obj.active = True
                return obj
        return None

# ==========================================
# CORE ENTITIES
# ==========================================
class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image, pos, pool=None, **kwargs):
        groups = kwargs.get('groups') or []
        super().__init__(*groups)
        self.pool = pool
        self.image = image
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.copy()
        self.is_one_way = False

    def update_rect_from_hitbox(self):
        self.rect.centerx = self.hitbox.centerx
        self.rect.midbottom = self.hitbox.midbottom

class Paddle(GameSprite):
    def __init__(self, image, pos, game, pool=None, **kwargs):
        super().__init__(image, pos, pool=pool, **kwargs)
        self.game = game
        self.is_one_way = False
        self.hitbox = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)
        
    def update(self, dt):
        mouse_x, _ = pygame.mouse.get_pos()
        self.hitbox.centerx = mouse_x
        
        if self.hitbox.left < 0:
            self.hitbox.left = 0
        if self.hitbox.right > self.game.screen.get_width():
            self.hitbox.right = self.game.screen.get_width()
            
        self.update_rect_from_hitbox()

class Ball(GameSprite):
    def __init__(self, image, pos, game, pool=None, **kwargs):
        super().__init__(image, pos, pool=pool, **kwargs)
        self.game = game
        self.is_one_way = False
        self.hitbox = self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)
        
        self.base_speed = self.game.config.get_prop('Ball', 'BALL_INITIAL_SPEED', 7.0)
        self.speed_factor = self.game.config.get_prop('Ball', 'BALL_SPEED_INCREASE_FACTOR', 1.1)
        self.vel_x = 0
        self.vel_y = 0
        self.active = False
        
    def reset_to_paddle(self):
        self.active = False
        
    def launch(self):
        if not self.active:
            self.active = True
            speed_val = self.base_speed * 60
            self.vel_x = random.choice([-1, 1]) * (speed_val * 0.7)
            self.vel_y = -speed_val
            
    def update(self, dt):
        if not self.active:
            if hasattr(self.game, 'paddle') and self.game.paddle:
                self.hitbox.midbottom = (self.game.paddle.hitbox.centerx, self.game.paddle.hitbox.top - 5)
                self.update_rect_from_hitbox()
            return
            
        self.hitbox.x += self.vel_x * dt
        self.check_collisions('x')
        
        self.hitbox.y += self.vel_y * dt
        self.check_collisions('y')
        
        self.update_rect_from_hitbox()
        
    def _hitbox_collide(self, s1, s2):
        return s1.hitbox.colliderect(s2.hitbox)
        
    def check_collisions(self, axis):
        screen_w = self.game.screen.get_width()
        
        if axis == 'x':
            # Wall Collisions
            if self.hitbox.left < 0:
                self.hitbox.left = 0
                self.vel_x = abs(self.vel_x)
                self.game.asset_manager.play_sfx('WALL_HIT_SFX')
            elif self.hitbox.right > screen_w:
                self.hitbox.right = screen_w
                self.vel_x = -abs(self.vel_x)
                self.game.asset_manager.play_sfx('WALL_HIT_SFX')
                
            # RAG Collision Integration for Groups
            hit_block = self.game.collision_manager.apply_sprite_vs_group(self, self.game.blocks, 'x')
            if hit_block:
                self.game.asset_manager.play_sfx('BLOCK_DESTROY_SFX')
                self.game.destroy_block(hit_block)
                
        elif axis == 'y':
            # Ceiling
            if self.hitbox.top < 0:
                self.hitbox.top = 0
                self.vel_y = abs(self.vel_y)
                self.game.asset_manager.play_sfx('WALL_HIT_SFX')
                
            # RAG Collision Integration for Groups
            hit_block = self.game.collision_manager.apply_sprite_vs_group(self, self.game.blocks, 'y')
            if hit_block:
                self.game.asset_manager.play_sfx('BLOCK_DESTROY_SFX')
                self.game.destroy_block(hit_block)
                
            # Paddle Collision
            if self.vel_y > 0 and hasattr(self.game, 'paddle') and self.game.paddle and self._hitbox_collide(self, self.game.paddle):
                self.hitbox.bottom = self.game.paddle.hitbox.top
                self.vel_y *= -1
                self.game.asset_manager.play_sfx('WALL_HIT_SFX')
                
                diff = self.hitbox.centerx - self.game.paddle.hitbox.centerx
                max_diff = (self.game.paddle.hitbox.width / 2)
                ratio = diff / (max_diff if max_diff != 0 else 1)
                
                speed = math.hypot(self.vel_x, self.vel_y)
                self.vel_x = ratio * speed * 0.85
                
                if abs(self.vel_y) < speed * 0.2:
                    self.vel_y = -speed * 0.2
                
                norm = math.hypot(self.vel_x, self.vel_y)
                if norm != 0:
                    self.vel_x = (self.vel_x / norm) * (speed * self.speed_factor)
                    self.vel_y = (self.vel_y / norm) * (speed * self.speed_factor)

class Block(GameSprite):
    def __init__(self, image, pos, pool=None, **kwargs):
        super().__init__(image, pos, pool=pool, **kwargs)
        self.hitbox = self.rect.copy()
        self.is_one_way = False

class Particle(GameSprite):
    def __init__(self, image, pool=None, **kwargs):
        super().__init__(image, (-1000, -1000), pool=pool, **kwargs)
        self.active = False
        self.lifetime = 0
        
    def reset(self, x, y):
        self.active = True
        self.lifetime = 0.5 
        self.hitbox.centerx = x
        self.hitbox.centery = y
        self.update_rect_from_hitbox()
        
    def update(self, dt):
        if self.active:
            self.lifetime -= dt
            if self.lifetime <= 0:
                self.active = False
                self.kill()

# ==========================================
# UI & MANAGERS
# ==========================================
class UIButton(GameSprite):
    def __init__(self, image, pos, text, callback, font=None, pool=None, **kwargs):
        super().__init__(image, pos, pool=pool, **kwargs)
        self.text = text
        self.callback = callback
        self.font = font if font else pygame.font.Font(None, 36)
        self.hitbox = self.rect.copy()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        if self.text and self.font:
            text_surf = self.font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect()
            text_rect.center = self.rect.center
            surface.blit(text_surf, text_rect)

class UIManager:
    def __init__(self):
        self.elements = []
        
    def add(self, element):
        self.elements.append(element)
        
    def clear(self):
        self.elements.clear()
        
    def handle_event(self, event):
        for el in self.elements:
            if hasattr(el, 'handle_event'):
                el.handle_event(event)
                
    def draw(self, surface):
        for el in self.elements:
            el.draw(surface)

# ==========================================
# GAME STATES
# ==========================================
class State:
    def __init__(self, game):
        self.game = game
    def enter(self): pass
    def exit(self): pass
    def update(self, dt): pass
    def draw(self, surface): pass
    def handle_event(self, event): pass

class StartupMenuState(State):
    def enter(self):
        self.ui = UIManager()
        btn_img = self.game.asset_manager.get('UIButton')
        font = self.game.font
        cx = self.game.screen.get_width() // 2 - btn_img.get_width() // 2
        cy = 200
        
        self.ui.add(UIButton(btn_img, (cx, cy), "GAME START", self.action_start, font))
        self.ui.add(UIButton(btn_img, (cx, cy + 100), "RULES", self.action_rules, font))
        self.ui.add(UIButton(btn_img, (cx, cy + 200), "QUIT", self.action_quit, font))
        
    def action_start(self):
        self.game.setup_new_game()
        self.game.fsm.change('PLAYING')
        
    def action_rules(self):
        self.game.fsm.change('RULES')
        
    def action_quit(self):
        self.game.fsm.change('QUIT_GAME')

    def handle_event(self, event):
        self.ui.handle_event(event)

    def draw(self, surface):
        bg = self.game.asset_manager.get('GameBackground')
        if bg:
            surface.blit(bg, (0, 0))
        self.ui.draw(surface)

class PlayingState(State):
    def enter(self):
        pass
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_p, pygame.K_ESCAPE):
                self.game.fsm.change('PAUSED')
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(self.game, 'ball') and not self.game.ball.active:
                self.game.ball.launch()

    def update(self, dt):
        self.game.all_sprites.update(dt)
        
        if hasattr(self.game, 'ball') and self.game.ball:
            if self.game.ball.hitbox.top > self.game.screen.get_height():
                self.game.asset_manager.play_sfx('LIFE_LOST_SFX')
                self.game.lives -= 1
                if self.game.lives <= 0:
                    self.game.fsm.change('GAME_OVER_LOSS')
                else:
                    self.game.ball.reset_to_paddle()
                
        if len(self.game.blocks) == 0:
            self.game.fsm.change('GAME_OVER_WIN')

    def draw(self, surface):
        bg = self.game.asset_manager.get('GameBackground')
        if bg:
            surface.blit(bg, (0, 0))
        self.game.all_sprites.draw(surface)
        
        score_text = self.game.font.render(f"Score: {self.game.score}", True, (255, 255, 255))
        lives_text = self.game.font.render(f"Lives: {self.game.lives}", True, (255, 255, 255))
        surface.blit(score_text, (20, 20))
        surface.blit(lives_text, (self.game.screen.get_width() - 150, 20))

class PausedState(State):
    def enter(self):
        self.ui = UIManager()
        btn_img = self.game.asset_manager.get('UIButton')
        font = self.game.font
        cx = self.game.screen.get_width() // 2 - btn_img.get_width() // 2
        cy = 150
        
        self.ui.add(UIButton(btn_img, (cx, cy), "CONTINUE", self.action_continue, font))
        self.ui.add(UIButton(btn_img, (cx, cy + 100), "RESTART", self.action_restart, font))
        self.ui.add(UIButton(btn_img, (cx, cy + 200), "RULES", self.action_rules, font))
        self.ui.add(UIButton(btn_img, (cx, cy + 300), "MAIN MENU", self.action_menu, font))

    def action_continue(self):
        self.game.fsm.change('PLAYING')
    def action_restart(self):
        self.game.setup_new_game()
        self.game.fsm.change('PLAYING')
    def action_rules(self):
        self.game.fsm.change('RULES')
    def action_menu(self):
        self.game.fsm.change('STARTUP_MENU')

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_ESCAPE):
            self.game.fsm.change('PLAYING')
        self.ui.handle_event(event)

    def draw(self, surface):
        bg = self.game.asset_manager.get('GameBackground')
        if bg:
            surface.blit(bg, (0, 0))
        self.game.all_sprites.draw(surface)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        self.ui.draw(surface)

class RulesState(State):
    def enter(self):
        self.ui = UIManager()
        btn_img = self.game.asset_manager.get('UIButton')
        font = self.game.font
        cx = self.game.screen.get_width() // 2 - btn_img.get_width() // 2
        cy = self.game.screen.get_height() - 100
        self.ui.add(UIButton(btn_img, (cx, cy), "BACK", self.action_back, font))

    def action_back(self):
        if hasattr(self.game, 'paddle') and self.game.lives > 0 and len(self.game.blocks) > 0:
            self.game.fsm.change('PAUSED')
        else:
            self.game.fsm.change('STARTUP_MENU')

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_ESCAPE):
            self.action_back()
        self.ui.handle_event(event)

    def draw(self, surface):
        surface.fill((30, 30, 50))
        title = self.game.font.render("RULES", True, (255, 200, 0))
        t1 = self.game.font.render("Move mouse to control paddle.", True, (255, 255, 255))
        t2 = self.game.font.render("Click to launch ball.", True, (255, 255, 255))
        t3 = self.game.font.render("Destroy all blocks to win.", True, (255, 255, 255))
        t4 = self.game.font.render("Press P or ESC to pause.", True, (255, 255, 255))
        
        surface.blit(title, (self.game.screen.get_width()//2 - title.get_width()//2, 100))
        surface.blit(t1, (100, 200))
        surface.blit(t2, (100, 250))
        surface.blit(t3, (100, 300))
        surface.blit(t4, (100, 350))
        
        self.ui.draw(surface)

class GameOverLossState(State):
    def enter(self):
        self.ui = UIManager()
        btn_img = self.game.asset_manager.get('UIButton')
        font = self.game.font
        cx = self.game.screen.get_width() // 2 - btn_img.get_width() // 2
        cy = 300
        self.ui.add(UIButton(btn_img, (cx, cy), "RESTART", self.action_restart, font))
        self.ui.add(UIButton(btn_img, (cx, cy + 100), "MAIN MENU", self.action_menu, font))

    def action_restart(self):
        self.game.setup_new_game()
        self.game.fsm.change('PLAYING')
    def action_menu(self):
        self.game.fsm.change('STARTUP_MENU')

    def handle_event(self, event):
        self.ui.handle_event(event)

    def draw(self, surface):
        surface.fill((50, 0, 0))
        title = self.game.font.render("GAME OVER", True, (255, 0, 0))
        score = self.game.font.render(f"Final Score: {self.game.score}", True, (255, 255, 255))
        surface.blit(title, (self.game.screen.get_width()//2 - title.get_width()//2, 150))
        surface.blit(score, (self.game.screen.get_width()//2 - score.get_width()//2, 220))
        self.ui.draw(surface)

class GameOverWinState(State):
    def enter(self):
        self.ui = UIManager()
        btn_img = self.game.asset_manager.get('UIButton')
        font = self.game.font
        cx = self.game.screen.get_width() // 2 - btn_img.get_width() // 2
        cy = 300
        self.ui.add(UIButton(btn_img, (cx, cy), "NEXT LEVEL", self.action_restart, font))
        self.ui.add(UIButton(btn_img, (cx, cy + 100), "MAIN MENU", self.action_menu, font))

    def action_restart(self):
        self.game.setup_new_game()
        self.game.fsm.change('PLAYING')
    def action_menu(self):
        self.game.fsm.change('STARTUP_MENU')

    def handle_event(self, event):
        self.ui.handle_event(event)

    def draw(self, surface):
        surface.fill((0, 50, 0))
        title = self.game.font.render("LEVEL COMPLETE!", True, (0, 255, 0))
        score = self.game.font.render(f"Final Score: {self.game.score}", True, (255, 255, 255))
        surface.blit(title, (self.game.screen.get_width()//2 - title.get_width()//2, 150))
        surface.blit(score, (self.game.screen.get_width()//2 - score.get_width()//2, 220))
        self.ui.draw(surface)

class QuitGameState(State):
    def enter(self):
        self.game.game_active = False
        pygame.quit()
        sys.exit()

# ==========================================
# MAIN GAME CLASS
# ==========================================
class Game:
    def __init__(self):
        pygame.init()
        self._read_json_only()
        
        self.game_active = True
        
        screen_size = self.config.data.get('config', {}).get('SCREEN_SIZE', [1280, 720])
        self.screen = pygame.display.set_mode((screen_size[0], screen_size[1]))
        pygame.display.set_caption(self.config.data.get('game_name', 'Arcade Brick Breaker'))
        
        self.asset_manager = AssetManager()
        self.asset_manager.load_assets(self.config.data)
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        
        self.collision_manager = CollisionManager(self)
        
        self.all_sprites = pygame.sprite.Group()
        self.blocks = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()
        
        particle_img = self.asset_manager.get('ParticleBlockHit')
        self.particle_pool = ObjectPool(lambda: Particle(particle_img), 30)
        
        self.score = 0
        self.lives = 3
        
        self.fsm = StateMachine()
        self.fsm.add('STARTUP_MENU', StartupMenuState(self))
        self.fsm.add('PLAYING', PlayingState(self))
        self.fsm.add('PAUSED', PausedState(self))
        self.fsm.add('RULES', RulesState(self))
        self.fsm.add('GAME_OVER_LOSS', GameOverLossState(self))
        self.fsm.add('GAME_OVER_WIN', GameOverWinState(self))
        self.fsm.add('QUIT_GAME', QuitGameState(self))

    def _read_json_only(self):
        self.config = GameConfig()
        config_path = os.path.join(os.path.dirname(__file__), 'game_config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config.data = json.load(f)
        except Exception:
            self.config.data = {}

    def setup_new_game(self):
        self.all_sprites.empty()
        self.blocks.empty()
        self.particles.empty()
        
        consts = self.config.data.get('gameplay_constants', {})
        self.lives = consts.get('PLAYER_LIVES', 3)
        self.score = 0
        
        paddle_data = self.config.get_entity('PlayerPaddle') or {}
        paddle_img = self.asset_manager.get('PlayerPaddle')
        if paddle_img:
            self.paddle = Paddle(paddle_img, (self.screen.get_width()//2, self.screen.get_height() - 60), self)
            self.all_sprites.add(self.paddle)
            
        ball_img = self.asset_manager.get('Ball')
        if ball_img:
            self.ball = Ball(ball_img, (0, 0), self)
            self.all_sprites.add(self.ball)
            self.ball.reset_to_paddle()
            
        block_types = ['BlockBlue', 'BlockRed', 'BlockGreen']
        start_x, start_y = 120, 80
        pad_x, pad_y = 10, 10
        cols, rows = 12, 5
        
        for r in range(rows):
            for c in range(cols):
                b_name = random.choice(block_types)
                b_img = self.asset_manager.get(b_name)
                if b_img:
                    x = start_x + c * (b_img.get_width() + pad_x)
                    y = start_y + r * (b_img.get_height() + pad_y)
                    blk = Block(b_img, (x, y))
                    self.blocks.add(blk)
                    self.all_sprites.add(blk)

    def destroy_block(self, block):
        block.kill()
        self.score += 10
        
        particle = self.particle_pool.get()
        if particle:
            particle.reset(block.rect.centerx, block.rect.centery)
            self.particles.add(particle)
            self.all_sprites.add(particle)

    def run(self):
        if getattr(self.fsm, 'current_state', None) is None:
            self.fsm.change('STARTUP_MENU')
            
        while self.game_active:
            dt = self.clock.tick(self.config.data.get('config', {}).get('FPS', 60)) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.fsm.change('QUIT_GAME')
                self.fsm.handle_event(event)
                
            self.fsm.update(dt)
            
            self.screen.fill((0, 0, 0))
            self.fsm.draw(self.screen)
            pygame.display.flip()

if __name__ == '__main__':
    game = Game()
    game.run()