import pygame
import os
import sys
import json
import math
import random

class GameConfig:
    def __init__(self, data):
        self.data = data or {}

    def get_config(self, key, default_value):
        return self.data.get('config', {}).get(key, default_value)

    def get_entity(self, name):
        entities = self.data.get('entities', [])
        for e in entities:
            if e.get('name') == name:
                return e
        return {}

    def get_prop(self, entity_name, prop_name, default_value):
        entity = self.get_entity(entity_name) or {}
        return entity.get('properties', {}).get(prop_name, default_value)


class AudioManager:
    def __init__(self):
        try:
            pygame.mixer.init()
            self.enabled = True
        except Exception as e:
            print(f"Audio init failed: {e}")
            self.enabled = False
        self.sounds = {}

    def play_music(self, filename):
        if not self.enabled or not filename: return
        try:
            full_path = os.path.join(os.path.dirname(__file__), 'assets', filename)
            if os.path.exists(full_path):
                pygame.mixer.music.load(full_path)
                pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Failed to play music: {e}")

    def play_sound(self, filename):
        if not self.enabled or not filename: return
        if filename not in self.sounds:
            full_path = os.path.join(os.path.dirname(__file__), 'assets', filename)
            if os.path.exists(full_path):
                try:
                    self.sounds[filename] = pygame.mixer.Sound(full_path)
                except Exception as e:
                    print(f"Failed to load sound {filename}: {e}")
                    self.sounds[filename] = None
            else:
                self.sounds[filename] = None
                
        sound = self.sounds.get(filename)
        if sound:
            try:
                sound.play()
            except Exception:
                pass


class AssetManager:
    def __init__(self):
        self.images = {}
        self.explosions = []

    def load_assets(self, config: GameConfig):
        base_path = os.path.join(os.path.dirname(__file__), 'assets')
        entities = config.data.get('entities', [])
        
        for ent in entities:
            name = ent.get('name')
            filename = ent.get('image')
            if not name or not filename:
                continue
                
            scale = config.get_prop(name, 'IMAGE_SCALE', 1.0)
            full_path = os.path.join(base_path, filename)
            
            try:
                img = pygame.image.load(full_path).convert_alpha()
                if name == "Explosion Effect":
                    frames = config.get_prop(name, 'ANIMATION_FRAMES', 6)
                    w = img.get_width() // frames
                    h = img.get_height()
                    scaled_w = int(w * scale)
                    scaled_h = int(h * scale)
                    
                    for i in range(frames):
                        frame_surf = img.subsurface((i * w, 0, w, h))
                        frame_surf = pygame.transform.scale(frame_surf, (scaled_w, scaled_h))
                        self.explosions.append(frame_surf)
                    self.images[name] = self.explosions[0] 
                else:
                    new_size = (int(img.get_width() * scale), int(img.get_height() * scale))
                    img = pygame.transform.scale(img, new_size)
                    self.images[name] = img
            except Exception as e:
                print(f"Failed to load asset {filename}: {e}")
                
        if "Game Background" not in self.images:
            bg = pygame.Surface((1280, 720))
            bg.fill((10, 10, 30))
            self.images["Game Background"] = bg

    def get(self, name):
        return self.images.get(name)


class ObjectPool:
    def __init__(self, create_func):
        self.pool = []
        self.create_func = create_func

    def get(self):
        if self.pool:
            return self.pool.pop()
        return self.create_func()

    def release(self, obj):
        self.pool.append(obj)


class FSM:
    def __init__(self):
        self.states = {}
        self.current_state = None
        self.previous_state = None

    def add(self, name, state_instance):
        self.states[name] = state_instance

    def change(self, name):
        if self.current_state and hasattr(self.states[self.current_state], 'exit'):
            self.states[self.current_state].exit()
            
        self.previous_state = self.current_state
        self.current_state = name
        
        if hasattr(self.states[self.current_state], 'enter'):
            self.states[self.current_state].enter()


class GameSprite(pygame.sprite.Sprite):
    def __init__(self, image, pos_x, pos_y, pool=None, **kwargs):
        groups = kwargs.get('groups') or []
        super().__init__(*groups)
        self.image = image
        if not self.image:
            self.image = pygame.Surface((50, 50))
            self.image.fill((255, 0, 255))
            
        self.rect = self.image.get_rect(center=(int(pos_x), int(pos_y)))
        
        shrink_x = self.rect.width * 0.2
        shrink_y = self.rect.height * 0.2
        self.hitbox = self.rect.inflate(-shrink_x, -shrink_y)
        
        self.pos = pygame.math.Vector2(pos_x, pos_y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.pool = pool

    def update_physics(self, dt, bounds_rect=None):
        self.pos.x += self.velocity.x * dt
        self.rect.centerx = int(self.pos.x)
        self.hitbox.centerx = self.rect.centerx
        
        if bounds_rect:
            if self.hitbox.left < bounds_rect.left:
                self.hitbox.left = bounds_rect.left
                self.rect.centerx = self.hitbox.centerx
                self.pos.x = self.rect.centerx
            elif self.hitbox.right > bounds_rect.right:
                self.hitbox.right = bounds_rect.right
                self.rect.centerx = self.hitbox.centerx
                self.pos.x = self.rect.centerx

        self.pos.y += self.velocity.y * dt
        self.rect.centery = int(self.pos.y)
        self.hitbox.centery = self.rect.centery
        
        if bounds_rect:
            if self.hitbox.top < bounds_rect.top:
                self.hitbox.top = bounds_rect.top
                self.rect.centery = self.hitbox.centery
                self.pos.y = self.rect.centery
            elif self.hitbox.bottom > bounds_rect.bottom:
                self.hitbox.bottom = bounds_rect.bottom
                self.rect.centery = self.hitbox.centery
                self.pos.y = self.rect.centery

    def kill(self):
        super().kill()
        if self.pool:
            self.pool.release(self)


class Particle(GameSprite):
    def __init__(self, pool=None, **kwargs):
        img = pygame.Surface((6, 6), pygame.SRCALPHA)
        img.fill((255, 150, 0))
        super().__init__(img, 0, 0, pool=pool, **kwargs)
        self.base_image = img
        self.image = img.copy()
        self.lifetime = 0
        self.max_lifetime = 1
        
    def reset(self, x, y, color, lifetime):
        self.pos.x = x
        self.pos.y = y
        self.rect.centerx = int(x)
        self.rect.centery = int(y)
        self.velocity.x = random.uniform(-100, -200)
        self.velocity.y = random.uniform(-20, 20)
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.base_image.fill(color)
        self.image = self.base_image.copy()
        self.image.set_alpha(255)

    def update(self, dt):
        self.update_physics(dt)
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
        else:
            alpha = max(0, int(255 * (self.lifetime / self.max_lifetime)))
            self.image.set_alpha(alpha)


class Player(GameSprite):
    def __init__(self, game, pool=None, **kwargs):
        img = game.assets.get("Player Ship")
        super().__init__(img, 200, game.screen_size[1] // 2, pool=pool, **kwargs)
        self.game = game
        
        self.speed = game.config.get_config('PLAYER_SPEED', 300.0)
        self.max_hp = game.config.get_config('PLAYER_MAX_HP', 3)
        self.current_hp = self.max_hp
        
        self.fire_cooldown = game.config.get_config('PLAYER_FIRE_COOLDOWN', 0.2)
        self.last_shot = 0
        self.score = 0
        self.trail_timer = 0

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.velocity.x = 0
        self.velocity.y = 0

        joystick_x = 0
        joystick_y = 0
        joystick_shoot = False
        
        if self.game.joysticks:
            joystick = self.game.joysticks[0]
            joystick_x = joystick.get_axis(0)
            joystick_y = joystick.get_axis(1)
            
            if joystick.get_numhats() > 0:
                hat = joystick.get_hat(0)
                if hat[0] != 0: joystick_x = hat[0]
                if hat[1] != 0: joystick_y = -hat[1]
                
            if abs(joystick_x) < 0.2: joystick_x = 0
            if abs(joystick_y) < 0.2: joystick_y = 0
            
            if joystick.get_button(0):
                joystick_shoot = True

        if keys[pygame.K_w] or keys[pygame.K_UP] or joystick_y < -0.2:
            self.velocity.y = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN] or joystick_y > 0.2:
            self.velocity.y = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT] or joystick_x < -0.2:
            self.velocity.x = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT] or joystick_x > 0.2:
            self.velocity.x = self.speed

        bounds = pygame.Rect(0, 0, 10000, 10000)
        self.update_physics(dt, bounds)

        self.trail_timer += dt
        if self.trail_timer > 0.05:
            self.trail_timer = 0
            p = self.game.particle_pool.get()
            color = (255, random.randint(100, 200), 0)
            p.reset(self.rect.left, self.rect.centery + random.randint(-4, 4), color, random.uniform(0.3, 0.6))
            self.game.all_sprites.add(p)

        if keys[pygame.K_SPACE] or joystick_shoot:
            self.shoot()

    def shoot(self):
        current_time = pygame.time.get_ticks() / 1000.0
        if current_time - self.last_shot >= self.fire_cooldown:
            self.last_shot = current_time
            proj = self.game.player_proj_pool.get()
            proj.reset(self.rect.right, self.rect.centery)
            self.game.player_projectiles.add(proj)
            self.game.all_sprites.add(proj)
            
            sfx = self.game.config.get_prop('Player Ship', 'SHOOT_SFX', 'shoot.wav')
            self.game.audio.play_sound(sfx)


class Enemy(GameSprite):
    def __init__(self, game, pool=None, **kwargs):
        img = game.assets.get("Red Alien Scout")
        super().__init__(img, 0, 0, pool=pool, **kwargs)
        self.game = game
        self.speed = game.config.get_config('ENEMY_SCOUT_SPEED', 150.0)
        self.hp = game.config.get_config('ENEMY_SCOUT_HP', 1)
        self.fire_cooldown = game.config.get_config('ENEMY_FIRE_COOLDOWN', 1.5)
        self.last_shot = 0

    def reset(self, x, y):
        self.pos.x = x
        self.pos.y = y
        self.rect.centerx = int(x)
        self.rect.centery = int(y)
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.centery = self.rect.centery
        self.velocity.x = -self.speed
        self.velocity.y = math.sin(x * 0.01) * (self.speed * 0.5) 
        self.last_shot = pygame.time.get_ticks() / 1000.0
        
    def update(self, dt):
        self.velocity.y = math.sin(self.pos.x * 0.01) * (self.speed * 0.5)
        self.update_physics(dt)
        
        camera = self.game.camera_group
        if self.rect.right < camera.offset.x - 200:
            self.kill()

        current_time = pygame.time.get_ticks() / 1000.0
        if current_time - self.last_shot >= self.fire_cooldown:
            self.last_shot = current_time
            proj = self.game.enemy_proj_pool.get()
            proj.reset(self.rect.left, self.rect.centery)
            self.game.enemy_projectiles.add(proj)
            self.game.all_sprites.add(proj)
            
            sfx = self.game.config.get_prop('Red Alien Scout', 'SHOOT_SFX', 'enemy_shoot.wav')
            self.game.audio.play_sound(sfx)


class Projectile(GameSprite):
    def __init__(self, game, is_player, pool=None, **kwargs):
        img_name = "Blue Plasma Bolt" if is_player else "Red Energy Orb"
        img = game.assets.get(img_name)
        super().__init__(img, 0, 0, pool=pool, **kwargs)
        self.game = game
        self.is_player = is_player
        
        if is_player:
            self.speed = game.config.get_config('PLAYER_PROJECTILE_SPEED', 600.0)
        else:
            self.speed = game.config.get_config('ENEMY_PROJECTILE_SPEED', 400.0)

    def reset(self, x, y):
        self.pos.x = x
        self.pos.y = y
        self.rect.centerx = int(x)
        self.rect.centery = int(y)
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.centery = self.rect.centery
        self.velocity.x = self.speed if self.is_player else -self.speed
        self.velocity.y = 0

    def update(self, dt):
        self.update_physics(dt)
        camera = self.game.camera_group
        screen_w = self.game.screen_size[0]
        screen_h = self.game.screen_size[1]
        
        if (self.rect.right < camera.offset.x - 200 or 
            self.rect.left > camera.offset.x + screen_w + 200 or
            self.rect.bottom < camera.offset.y - 200 or 
            self.rect.top > camera.offset.y + screen_h + 200):
            self.kill()


class Explosion(GameSprite):
    def __init__(self, game, pool=None, **kwargs):
        self.frames = game.assets.explosions
        super().__init__(self.frames[0] if self.frames else None, 0, 0, pool=pool, **kwargs)
        self.game = game
        self.anim_speed = game.config.get_prop('Explosion Effect', 'ANIMATION_SPEED', 0.05)
        self.timer = 0
        self.current_frame = 0

    def reset(self, x, y):
        self.pos.x = x
        self.pos.y = y
        self.rect.centerx = int(x)
        self.rect.centery = int(y)
        self.timer = 0
        self.current_frame = 0
        if self.frames:
            self.image = self.frames[0]

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.anim_speed:
            self.timer = 0
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.kill()
            else:
                self.image = self.frames[self.current_frame]


class UIButton:
    def __init__(self, image, x, y, text, on_click):
        self.image = image
        if not self.image:
            self.image = pygame.Surface((200, 50))
            self.image.fill((100, 100, 100))
        self.rect = self.image.get_rect(center=(x, y))
        self.text = text
        self.font = pygame.font.Font(None, 40)
        self.on_click = on_click
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.on_click:
                self.on_click()

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        color = (255, 255, 0) if self.is_hovered else (255, 255, 255)
        text_surf = self.font.render(self.text, True, color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class UIManager:
    def __init__(self):
        self.buttons = []

    def handle_event(self, event):
        for btn in self.buttons:
            btn.handle_event(event)

    def draw(self, surface):
        for btn in self.buttons:
            btn.draw(surface)


class CameraScrollGroup(pygame.sprite.Group):
    def __init__(self, bg_image, screen_size):
        super().__init__()
        self.bg_image = bg_image
        self.screen_size = screen_size
        self.offset = pygame.math.Vector2(0, 0)
        self.target = None

    def center_on_target(self, target=None):
        if target is not None:
            self.target = target
        if self.target is not None:
            self.offset.x = self.target.rect.centerx - self.screen_size[0] // 2
            self.offset.y = self.target.rect.centery - self.screen_size[1] // 2

    def custom_draw(self, surface, dt):
        self.center_on_target()

        if self.bg_image:
            bg_w = self.bg_image.get_width()
            bg_h = self.bg_image.get_height()
            if bg_w > 0 and bg_h > 0:
                mod_x = int(self.offset.x * 0.5) % bg_w
                mod_y = int(self.offset.y * 0.5) % bg_h
                surface.blit(self.bg_image, (-mod_x, -mod_y))
                surface.blit(self.bg_image, (bg_w - mod_x, -mod_y))
                surface.blit(self.bg_image, (-mod_x, bg_h - mod_y))
                surface.blit(self.bg_image, (bg_w - mod_x, bg_h - mod_y))
        else:
            surface.fill((0, 0, 0))

        for sprite in self.sprites():
            offset_pos = sprite.rect.topleft - self.offset
            surface.blit(sprite.image, offset_pos)


class StartupMenuState:
    def __init__(self, game):
        self.game = game
        self.ui = UIManager()
        cx = game.screen_size[0] // 2
        cy = game.screen_size[1] // 2
        
        self.ui.buttons.extend([
            UIButton(game.assets.get("UI Button - GAME START"), cx, cy - 80, "START GAME", self.on_start),
            UIButton(game.assets.get("UI Button - RULES"), cx, cy, "RULES", self.on_rules),
            UIButton(game.assets.get("UI Button - QUIT"), cx, cy + 80, "QUIT", self.on_quit)
        ])
        self.font = pygame.font.Font(None, 72)

    def on_start(self):
        self.game._setup_new_game()
        self.game.fsm.change('PLAYING')

    def on_rules(self):
        self.game.fsm.change('MENU_RULES')

    def on_quit(self):
        pygame.quit()
        sys.exit()

    def enter(self): 
        bgm_file = self.game.config.get_prop('Game Background', 'BGM', 'bgm.ogg')
        if bgm_file:
            self.game.audio.play_music(bgm_file)

    def exit(self): pass

    def handle_event(self, event):
        self.ui.handle_event(event)

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill((10, 10, 30))
        title = self.font.render(self.game.config.data.get('game_name', 'Starfire Defender'), True, (255, 200, 0))
        t_rect = title.get_rect(center=(self.game.screen_size[0]//2, 150))
        surface.blit(title, t_rect)
        self.ui.draw(surface)


class PlayingState:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, game.config.get_config('UI_SCORE_FONT_SIZE', 32))
        self.score_color = tuple(game.config.get_config('UI_SCORE_COLOR', [255, 255, 255]))
        self.enemy_spawn_timer = 0

    def enter(self): pass
    def exit(self): pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.game.fsm.change('MENU_PAUSE')
                
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 7: 
                self.game.fsm.change('MENU_PAUSE')

    def update(self, dt):
        self.game.all_sprites.update(dt)
        
        self.enemy_spawn_timer -= dt
        if self.enemy_spawn_timer <= 0:
            self.enemy_spawn_timer = 1.0 + random.random()
            enemy = self.game.enemy_pool.get()
            camera = self.game.camera_group
            spawn_y = random.randint(int(camera.offset.y + 50), int(camera.offset.y + self.game.screen_size[1] - 50))
            enemy.reset(camera.offset.x + self.game.screen_size[0] + 50, spawn_y)
            self.game.enemies.add(enemy)
            self.game.all_sprites.add(enemy)

        self.check_collisions()

        if self.game.player.current_hp <= 0:
            self.spawn_explosion(self.game.player.rect.centerx, self.game.player.rect.centery)
            self.game.fsm.change('GAME_OVER')

    def check_collisions(self):
        for p_proj in self.game.player_projectiles.sprites():
            for e_proj in self.game.enemy_projectiles.sprites():
                if p_proj.hitbox.colliderect(e_proj.hitbox):
                    self.spawn_explosion((p_proj.rect.centerx + e_proj.rect.centerx)//2, 
                                         (p_proj.rect.centery + e_proj.rect.centery)//2)
                    p_proj.kill()
                    e_proj.kill()
                    break

        for p_proj in self.game.player_projectiles.sprites():
            for enemy in self.game.enemies.sprites():
                if p_proj.hitbox.colliderect(enemy.hitbox):
                    self.spawn_explosion(enemy.rect.centerx, enemy.rect.centery)
                    p_proj.kill()
                    enemy.kill()
                    self.game.player.score += 100
                    break

        for e_proj in self.game.enemy_projectiles.sprites():
            if e_proj.hitbox.colliderect(self.game.player.hitbox):
                self.spawn_explosion(self.game.player.rect.centerx, self.game.player.rect.centery)
                e_proj.kill()
                self.game.player.current_hp -= 1

        for enemy in self.game.enemies.sprites():
            if enemy.hitbox.colliderect(self.game.player.hitbox):
                self.spawn_explosion(enemy.rect.centerx, enemy.rect.centery)
                enemy.kill()
                self.game.player.current_hp -= 1

    def spawn_explosion(self, x, y):
        exp = self.game.explosion_pool.get()
        exp.reset(x, y)
        self.game.all_sprites.add(exp)
        
        sfx = self.game.config.get_prop('Explosion Effect', 'SFX', 'explosion.wav')
        self.game.audio.play_sound(sfx)

    def draw(self, surface, dt):
        self.game.camera_group.custom_draw(surface, dt)
        
        score_surf = self.font.render(f"SCORE: {self.game.player.score}", True, self.score_color)
        surface.blit(score_surf, (20, 20))
        
        hp_surf = self.font.render(f"HP: {self.game.player.current_hp}/{self.game.player.max_hp}", True, (255, 50, 50))
        surface.blit(hp_surf, (20, 60))


class PauseMenuState:
    def __init__(self, game):
        self.game = game
        self.ui = UIManager()
        cx = game.screen_size[0] // 2
        cy = game.screen_size[1] // 2
        
        self.ui.buttons.extend([
            UIButton(game.assets.get("UI Button - CONTINUE"), cx, cy - 100, "CONTINUE", self.on_continue),
            UIButton(game.assets.get("UI Button - RESTART"), cx, cy - 20, "RESTART", self.on_restart),
            UIButton(game.assets.get("UI Button - RULES"), cx, cy + 60, "RULES", self.on_rules),
            UIButton(game.assets.get("UI Button - BACK TO MAIN MENU"), cx, cy + 140, "MAIN MENU", self.on_main_menu)
        ])
        
        self.overlay = pygame.Surface(game.screen_size, pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 180))

    def on_continue(self):
        self.game.fsm.change('PLAYING')
        
    def on_restart(self):
        self.game._setup_new_game()
        self.game.fsm.change('PLAYING')
        
    def on_rules(self):
        self.game.fsm.change('MENU_RULES')
        
    def on_main_menu(self):
        self.game.fsm.change('STARTUP_MENU')

    def enter(self): 
        if self.game.audio.enabled:
            pygame.mixer.music.pause()
            
    def exit(self): 
        if self.game.audio.enabled:
            pygame.mixer.music.unpause()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                self.game.fsm.change('PLAYING')
                
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 7:
                self.game.fsm.change('PLAYING')
                
        self.ui.handle_event(event)

    def update(self, dt): pass

    def draw(self, surface):
        self.game.states['PLAYING'].draw(surface, 0)
        surface.blit(self.overlay, (0, 0))
        self.ui.draw(surface)


class RulesMenuState:
    def __init__(self, game):
        self.game = game
        self.ui = UIManager()
        cx = game.screen_size[0] // 2
        self.ui.buttons.append(
            UIButton(game.assets.get("UI Button - BACK"), cx, self.game.screen_size[1] - 80, "BACK", self.on_back)
        )
        self.font = pygame.font.Font(None, 40)
        self.rules = [
            "HOW TO PLAY:",
            "- WASD or ARROW KEYS or GAMEPAD to Move",
            "- SPACEBAR or GAMEPAD BUTTON to Fire",
            "- P or ESC to Pause",
            "- Destroy Alien Scouts to gain points",
            "- Avoid Red Energy Orbs and crashing",
            "- Survive as long as possible!"
        ]
        self.return_state = 'STARTUP_MENU'

    def enter(self): 
        if self.game.fsm.previous_state:
            self.return_state = self.game.fsm.previous_state
        else:
            self.return_state = 'STARTUP_MENU'
            
    def exit(self): pass

    def on_back(self):
        self.game.fsm.change(self.return_state)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()
        self.ui.handle_event(event)

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill((20, 20, 40))
        for i, text in enumerate(self.rules):
            surf = self.font.render(text, True, (255, 255, 255))
            rect = surf.get_rect(center=(self.game.screen_size[0]//2, 150 + i * 50))
            surface.blit(surf, rect)
        self.ui.draw(surface)


class GameOverState:
    def __init__(self, game):
        self.game = game
        self.ui = UIManager()
        cx = game.screen_size[0] // 2
        cy = game.screen_size[1] // 2
        
        self.ui.buttons.extend([
            UIButton(game.assets.get("UI Button - RESTART"), cx, cy + 50, "RESTART", self.on_restart),
            UIButton(game.assets.get("UI Button - BACK TO MAIN MENU"), cx, cy + 130, "MAIN MENU", self.on_main_menu)
        ])
        self.font_large = pygame.font.Font(None, 100)
        self.font_small = pygame.font.Font(None, 50)

    def on_restart(self):
        self.game._setup_new_game()
        self.game.fsm.change('PLAYING')

    def on_main_menu(self):
        self.game.fsm.change('STARTUP_MENU')

    def enter(self): 
        sfx = self.game.config.get_prop('Game Background', 'GAME_OVER_SFX', 'game_over.wav')
        self.game.audio.play_sound(sfx)
        
    def exit(self): pass

    def handle_event(self, event):
        self.ui.handle_event(event)

    def update(self, dt): pass

    def draw(self, surface):
        self.game.states['PLAYING'].draw(surface, 0)
        overlay = pygame.Surface(self.game.screen_size, pygame.SRCALPHA)
        overlay.fill((100, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        
        go_surf = self.font_large.render("GAME OVER", True, (255, 50, 50))
        go_rect = go_surf.get_rect(center=(self.game.screen_size[0]//2, 200))
        surface.blit(go_surf, go_rect)
        
        sc_surf = self.font_small.render(f"FINAL SCORE: {self.game.player.score}", True, (255, 255, 255))
        sc_rect = sc_surf.get_rect(center=(self.game.screen_size[0]//2, 300))
        surface.blit(sc_surf, sc_rect)
        
        self.ui.draw(surface)


class Game:
    def __init__(self):
        pygame.init()
        self._read_json_only()
        
        self.screen_size = self.config.get_config('SCREEN_SIZE', [1280, 720])
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption(self.config.data.get('game_name', 'Starfire Defender'))
        
        self.audio = AudioManager()
        
        try:
            pygame.joystick.init()
            self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            for joystick in self.joysticks:
                joystick.init()
        except Exception:
            self.joysticks = []
        
        self.assets = AssetManager()
        self.assets.load_assets(self.config)
        
        self.fsm = FSM()
        
        self.player_proj_pool = ObjectPool(lambda: self._create_pooled_projectile(True))
        self.enemy_proj_pool = ObjectPool(lambda: self._create_pooled_projectile(False))
        self.enemy_pool = ObjectPool(lambda: self._create_pooled_enemy())
        self.explosion_pool = ObjectPool(lambda: self._create_pooled_explosion())
        self.particle_pool = ObjectPool(lambda: Particle(pool=self.particle_pool))

        self._setup_new_game()

        self.states = {
            'STARTUP_MENU': StartupMenuState(self),
            'PLAYING': PlayingState(self),
            'MENU_PAUSE': PauseMenuState(self),
            'MENU_RULES': RulesMenuState(self),
            'GAME_OVER': GameOverState(self)
        }
        
        for name, state in self.states.items():
            self.fsm.add(name, state)

    def _read_json_only(self):
        path = os.path.join(os.path.dirname(__file__), 'game_config.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except Exception:
            raw_data = {}
        self.config = GameConfig(raw_data)

    def _create_pooled_projectile(self, is_player):
        pool = self.player_proj_pool if is_player else self.enemy_proj_pool
        return Projectile(self, is_player, pool=pool)

    def _create_pooled_enemy(self):
        return Enemy(self, pool=self.enemy_pool)
        
    def _create_pooled_explosion(self):
        return Explosion(self, pool=self.explosion_pool)

    def _setup_new_game(self):
        self.camera_group = CameraScrollGroup(self.assets.get("Game Background"), self.screen_size)
        self.all_sprites = self.camera_group
        
        self.enemies = pygame.sprite.Group()
        self.player_projectiles = pygame.sprite.Group()
        self.enemy_projectiles = pygame.sprite.Group()
        
        self.player = Player(self)
        self.all_sprites.add(self.player)
        self.camera_group.center_on_target(self.player)

    def run(self):
        if getattr(self.fsm, 'current_state', None) is None:
            self.fsm.change('STARTUP_MENU')
            
        clock = pygame.time.Clock()
        fps = self.config.get_config('FPS', 60)
        
        while True:
            dt = clock.tick(fps) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                current_state_obj = self.states.get(self.fsm.current_state)
                if current_state_obj:
                    current_state_obj.handle_event(event)
                    
            current_state_obj = self.states.get(self.fsm.current_state)
            if current_state_obj:
                current_state_obj.update(dt)
                
            current_state_obj = self.states.get(self.fsm.current_state)
                
            self.screen.fill((0, 0, 0))
            if current_state_obj:
                if self.fsm.current_state == 'PLAYING':
                    current_state_obj.draw(self.screen, dt)
                else:
                    current_state_obj.draw(self.screen)
                    
            pygame.display.flip()

if __name__ == '__main__':
    Game().run()