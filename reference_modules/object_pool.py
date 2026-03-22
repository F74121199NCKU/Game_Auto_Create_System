# tags: optimization, memory, pool
class ObjectPool:
    """Simple Object Pool used to reuse bullets or enemies, avoiding frequent memory allocation"""
    def __init__(self, cls, size=100):
        # Pre-instantiate a batch of objects
        self.pool = [cls() for _ in range(size)]
        self.active = []

    def get(self, *args, **kwargs):
        """Retrieve an object from the pool and initialize it"""
        if self.pool:
            obj = self.pool.pop()
            # Assumes objects have an 'init' method to reset their state
            if hasattr(obj, 'init'):
                obj.init(*args, **kwargs)
            self.active.append(obj)
            return obj
        return None # Pool is empty

    def release(self, obj):
        """Return the object to the pool for reuse"""
        if obj in self.active:
            self.active.remove(obj)
            self.pool.append(obj)