# tags: state_machine, fsm, scene_manager, pause, menu, transition
import pygame

class State:
    """狀態的基礎類別。所有遊戲場景(Menu, Playing, Pause)都應繼承此類別。"""
    def __init__(self, game):
        self.game = game # 傳入主要的 Game 實體以存取全域變數(如畫面、資源)

    def enter(self):
        """進入此狀態時觸發 (例如：播放背景音樂、初始化UI)"""
        pass

    def exit(self):
        """離開此狀態時觸發 (例如：清除暫存、停止音樂)"""
        pass

    def handle_event(self, event):
        """處理 Pygame 事件 (鍵盤、滑鼠)"""
        pass

    def update(self, dt):
        """邏輯更新"""
        pass

    def draw(self, surface):
        """畫面渲染"""
        pass

class StateManager:
    """
    [RAG 提示] 當遊戲需要「選單」、「暫停」、「遊戲結束」等不同畫面切換時，
    必須使用 StateManager 來管理狀態，嚴禁在主迴圈使用大量的 if/else。
    """
    def __init__(self):
        self.states = {}
        self.current_state = None
        self.previous_state_name = None

    def add_state(self, state_name, state_obj):
        self.states[state_name] = state_obj

    def change_state(self, state_name):
        """切換狀態，會自動呼叫舊狀態的 exit() 與新狀態的 enter()"""
        if self.current_state:
            self.current_state.exit()
            # 記錄前一個狀態，方便「暫停」後能「返回」
            self.previous_state_name = self.current_state.__class__.__name__ 

        self.current_state = self.states.get(state_name)
        if self.current_state:
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