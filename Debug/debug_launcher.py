import sys
import os

# ==========================================
# 🛑 智慧路徑修復區 (Smart Path Fixing)
# ==========================================

# 1. 抓出目前腳本所在位置
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 2. 智慧偵測：dest 資料夾到底在哪裡？
# 策略 A：假設我現在就在根目錄 (Fuzzer 執行時的情況)
path_strategy_a = os.path.join(current_script_dir, "dest")

# 策略 B：假設我現在在 Debug 子資料夾 (手動執行時的情況)
path_strategy_b = os.path.join(os.path.dirname(current_script_dir), "dest")

dest_folder_path = None

if os.path.exists(path_strategy_a):
    print(f"📍 [路徑偵測] 偵測到運行於專案根目錄 (Fuzzer模式)")
    dest_folder_path = path_strategy_a
elif os.path.exists(path_strategy_b):
    print(f"📍 [路徑偵測] 偵測到運行於 Debug 子目錄 (手動模式)")
    dest_folder_path = path_strategy_b
else:
    # --- 萬一真的都找不到，印出詳細除錯資訊 ---
    print("="*40)
    print("❌ 嚴重錯誤：找不到 'dest' 資料夾！")
    print(f"   目前位置: {current_script_dir}")
    print(f"   嘗試路徑 A: {path_strategy_a}")
    print(f"   嘗試路徑 B: {path_strategy_b}")
    print("="*40)
    sys.exit(1) # 回傳錯誤碼 1

# ==========================================
# 🚀 匯入與啟動
# ==========================================

# 3. 把 dest 加入搜尋路徑
if dest_folder_path not in sys.path:
    sys.path.append(dest_folder_path)

try:
    from generated_app import Game
except ImportError as e:
    print(f"❌ 匯入錯誤：{e}")
    sys.exit(1)

class AutoStartGame(Game):
    def __init__(self):
        super().__init__()
        # print("🚀 [TEST MODE] 強制跳過選單...") # 註解掉避免干擾 Fuzzer 輸出
        self.game_active = True 
        self.paused = False
        if hasattr(self, 'show_menu'):
            self.show_menu = False

if __name__ == "__main__":
    game = AutoStartGame()
    game.run()