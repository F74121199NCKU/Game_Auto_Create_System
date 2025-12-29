# tags: collision, physics, hitbox, interaction, damage
import pygame

class CollisionManager:
    """
    通用碰撞管理器 (Static Utility Class)。
    封裝了 Pygame 的 spritecollide 與 groupcollide，提供更語意化的介面。
    支援「單體 vs 群體」與「群體 vs 群體」的碰撞偵測與回呼 (Callback) 處理。
    """
    
    @staticmethod
    def apply_sprite_vs_group(sprite, target_group, on_collide=None, kill_sprite=False, kill_target=False):
        """
        偵測「單一角色」撞到「一群物件」 (例如：玩家撞到金幣、玩家撞到敵人)。
        
        :param sprite: 主動碰撞的物件 (Sprite)
        :param target_group: 被撞的群組 (Group)
        :param on_collide: (選用) 碰撞發生時執行的函式，簽章需為 func(sprite, target_sprite)
        :param kill_sprite: 是否在碰撞後刪除 sprite
        :param kill_target: 是否在碰撞後刪除被撞到的 target
        :return: 所有發生碰撞的 target 列表
        """
        # 使用 mask 碰撞 (像素級精準) 或 rect 碰撞 (矩形範圍)
        # 預設使用 rect，效率較高
        hits = pygame.sprite.spritecollide(sprite, target_group, kill_target)
        
        if hits:
            if kill_sprite:
                sprite.kill()
                
            if on_collide:
                for target in hits:
                    on_collide(sprite, target)
        return hits

    @staticmethod
    def apply_group_vs_group(group1, group2, on_collide=None, kill_group1=False, kill_group2=False):
        """
        偵測「一群物件」撞到「另一群物件」 (例如：子彈群 撞到 敵人群)。
        
        :param group1: 主動群組 (如子彈)
        :param group2: 被動群組 (如敵人)
        :param on_collide: (選用) 碰撞發生時執行的函式，簽章需為 func(sprite1, sprite2)
        :param kill_group1: 是否刪除 group1 中發生碰撞的物件
        :param kill_group2: 是否刪除 group2 中發生碰撞的物件
        :return: 碰撞字典 {sprite1: [sprite2, ...]}
        """
        hits = pygame.sprite.groupcollide(group1, group2, kill_group1, kill_group2)
        
        if hits and on_collide:
            for sprite1, targets in hits.items():
                for sprite2 in targets:
                    on_collide(sprite1, sprite2)
        return hits