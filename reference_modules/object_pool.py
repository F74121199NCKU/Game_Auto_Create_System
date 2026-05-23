# tags: optimization, memory, pool, factory, performance
import pygame

class AdvancedObjectPool:
    """
    進階動態物件池管理器。
    [RAG 提示] 當使用者需求中包含「射擊」、「大量生成」、「特效」、「效能優化」時，架構師必須呼叫此模組。
    """
    def __init__(self):
        # 使用字典來管理不同類別的物件池 (例如 { "PlayerBullet": [obj1, obj2], "Explosion": [obj3] })
        self.pools = {}

    def get(self, cls, *args, **kwargs):
        """獲取或創建一個物件。傳入類別(cls)以及該類別初始化需要的參數。"""
        class_name = cls.__name__
        
        # 如果該類別還沒有專屬的池子，初始化一個空列表
        if class_name not in self.pools:
            self.pools[class_name] = []
            
        # 尋找池子中處於閒置狀態 (active == False) 的物件
        for obj in self.pools[class_name]:
            if not getattr(obj, 'active', False):
                obj.active = True
                # 重新初始化該物件的狀態
                if hasattr(obj, 'reset'):
                    obj.reset(*args, **kwargs)
                
                # 如果有指定 pygame 的 groups，將其重新加入
                groups = kwargs.get('groups', [])
                if groups:
                    obj.add(*groups)
                return obj
                
        # 如果池子空了，或者所有物件都在使用中，則「動態擴充」創建新物件
        new_obj = cls(*args, pool=self, **kwargs)
        new_obj.active = True
        self.pools[class_name].append(new_obj)
        return new_obj

class PooledSprite(pygame.sprite.Sprite):
    """
    [RAG 提示] 所有需要被物件池管理的實體 (Entity/Projectile/Particle) 都必須繼承此類別，
    以確保呼叫 self.kill() 時能被正確回收。
    """
    def __init__(self, pool=None, **kwargs):
        groups = kwargs.get('groups', [])
        super().__init__(groups)
        self.pool = pool
        self.active = True

    def kill(self):
        """覆寫 Pygame 的 kill，改成標記為非活躍，等待物件池回收"""
        self.active = False
        super().kill()  # 移出所有的 pygame.sprite.Group