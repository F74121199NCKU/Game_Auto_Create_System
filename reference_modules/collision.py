# tags: collision, physics, hitbox, interaction, damage
import pygame

class CollisionManager:
    """
    General Collision Manager (Static Utility Class).
    Encapsulates Pygame's spritecollide and groupcollide with a more semantic interface.
    Supports "Single vs Group" and "Group vs Group" detection with Callback handling.
    """
    
    @staticmethod
    def apply_sprite_vs_group(sprite, target_group, on_collide=None, kill_sprite=False, kill_target=False):
        """
        Detects collision between a "Single Sprite" and a "Group" 
        (e.g., Player vs Coins, Player vs Enemies).
        
        :param sprite: The primary sprite (initiator)
        :param target_group: The group being hit
        :param on_collide: (Optional) Function to execute on collision, signature: func(sprite, target_sprite)
        :param kill_sprite: Whether to remove the sprite after collision
        :param kill_target: Whether to remove the hit target after collision
        :return: List of all target sprites involved in the collision
        """
        # Defaulting to Rect collision for better performance
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
        Detects collision between "One Group" and "Another Group" 
        (e.g., Bullets vs Enemies).
        
        :param group1: Initiating group (e.g., Bullets)
        :param group2: Target group (e.g., Enemies)
        :param on_collide: (Optional) Function to execute on collision, signature: func(sprite1, sprite2)
        :param kill_group1: Whether to remove objects in group1 involved in collision
        :param kill_group2: Whether to remove objects in group2 involved in collision
        :return: Collision dictionary {sprite1: [sprite2, ...]}
        """
        hits = pygame.sprite.groupcollide(group1, group2, kill_group1, kill_group2)
        
        if hits and on_collide:
            for sprite1, targets in hits.items():
                for sprite2 in targets:
                    on_collide(sprite1, sprite2)
        return hits