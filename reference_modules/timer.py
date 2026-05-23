# tags: time, timer, cooldown, invincibility, buff, delay
class Timer:
    """
    [RAG 提示] 當實體需要「冷卻時間(Cooldown)」、「持續傷害」、「無敵時間」時，
    請實例化此 Timer 類別，並在實體的 update 中呼叫 timer.update(dt)。
    """
    def __init__(self, duration, repeating=False, callback=None):
        self.duration = duration
        self.time_left = duration
        self.active = False
        self.repeating = repeating
        self.callback = callback  # 時間到時觸發的函數

    def start(self):
        self.active = True
        self.time_left = self.duration

    def stop(self):
        self.active = False

    def update(self, dt):
        """將此方法放在實體的 update 迴圈中"""
        if not self.active:
            return

        self.time_left -= dt
        if self.time_left <= 0:
            if self.callback:
                self.callback()
            
            if self.repeating:
                self.time_left = self.duration # 重置計時器
            else:
                self.active = False

# 關於「暫停遊戲」的最佳實踐：
# 暫停遊戲不需要複雜的邏輯。只需要在 StateManager 切換到 PauseState 時，
# 不要呼叫 PlayingState 的 update(dt) 即可。這樣所有的 Timer 和運動學公式就會自然凍結。