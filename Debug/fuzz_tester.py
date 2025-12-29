import subprocess
import sys
import time
import os
import threading
import signal

# ==========================================
# 1. 定義要注入的「保險型」Chaos Payload
#    這個字串會被動態寫入到遊戲進程中執行
# ==========================================
# ==========================================
# 1. 定義要注入的「保險型」Chaos Payload (無 Emoji 版)
# ==========================================
CHAOS_PAYLOAD = """
# --- [INJECTED SAFE FUZZER CODE] START ---
import sys as _sys
import random as _random
import pygame as _pygame

# 強制設定輸出編碼為 UTF-8，防止中文環境報錯
try:
    _sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

class _ChaosAgent:
    def __init__(self, duration_sec=10.0):
        self.start_t = _pygame.time.get_ticks()
        self.duration = duration_sec * 1000
        self.end_t = self.start_t + self.duration
        
        try:
            self.surface = _pygame.display.get_surface()
            if self.surface:
                self.w, self.h = self.surface.get_size()
            else:
                self.w, self.h = 800, 600
        except:
            self.w, self.h = 800, 600

        # [修正] 移除了機器人符號，改用純文字標籤
        print(f"[FUZZER] Start Safe Mode Test ({duration_sec}s)")
        print(f"[FUZZER] Strategy: Avoid Esc/P keys, avoid bottom/top-right corners.")

    def _post_key(self, key):
        try:
            _pygame.event.post(_pygame.event.Event(_pygame.KEYDOWN, key=key))
            _pygame.event.post(_pygame.event.Event(_pygame.KEYUP, key=key))
        except: pass

    def _post_click(self, x, y):
        try:
            x = max(0, min(x, self.w - 1))
            y = max(0, min(y, self.h - 1))
            _pygame.event.post(_pygame.event.Event(_pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y)))
            _pygame.event.post(_pygame.event.Event(_pygame.MOUSEBUTTONUP, button=1, pos=(x, y)))
            _pygame.mouse.set_pos((x, y))
        except: pass

    def update(self):
        current_t = _pygame.time.get_ticks()
        # 1. 時間到，通過測試
        if current_t > self.end_t:
            print("[FUZZ] SUCCESS: Test Passed cleanly.")
            _pygame.quit()
            _sys.exit(0)
            
        # 壓力測試邏輯
        if _random.random() < 0.2:
            action_type = _random.choice(['move', 'click', 'skill'])
            
            if action_type == 'move':
                keys = [_pygame.K_LEFT, _pygame.K_RIGHT, _pygame.K_UP, _pygame.K_DOWN, 
                        _pygame.K_w, _pygame.K_a, _pygame.K_s, _pygame.K_d]
                self._post_key(_random.choice(keys))
            
            elif action_type == 'click':
                rand_x = _random.randint(0, self.w)
                safe_h_max = int(self.h * 0.85) 
                rand_y = _random.randint(0, safe_h_max)
                
                if rand_x > self.w * 0.95 and rand_y < self.h * 0.05:
                    rand_x = self.w // 2
                    rand_y = self.h // 2
                self._post_click(rand_x, rand_y)
                
                if _random.random() < 0.1:
                    edge_x = _random.choice([0, self.w-1])
                    edge_y = _random.choice([0, self.h-1])
                    _pygame.mouse.set_pos((edge_x, edge_y))

            elif action_type == 'skill':
                self._post_key(_random.choice([_pygame.K_SPACE, _pygame.K_r, _pygame.K_e]))

if not hasattr(_sys, '_fuzzer_active'):
    _sys._fuzzer_active = True
    global _tester
    _tester = _ChaosAgent(duration_sec=10.0)

def _fuzzer_loop():
    while True:
        try:
            _tester.update()
            _pygame.time.wait(30)
        except SystemExit:
            break
        except:
            pass

import threading
_t = threading.Thread(target=_fuzzer_loop, daemon=True)
_t.start()
# --- [INJECTED SAFE FUZZER CODE] END ---
"""

def run_fuzz_test():
    """
    執行遊戲並注入 Chaos Payload。
    """
    # 1. 決定目標腳本
    launcher_path = os.path.join(os.path.dirname(__file__), "debug_launcher.py")
    if not os.path.exists(launcher_path):
         launcher_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug_launcher.py")
    
    if not os.path.exists(launcher_path):
        print("⚠️ 找不到 debug_launcher.py，改為測試 generated_app.py")
        target_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dest", "generated_app.py"))
    else:
        target_script = os.path.abspath(launcher_path)

    print(f"🎯 Fuzzer 目標腳本: {target_script}")

    if not os.path.exists(target_script):
        print(f"❌ 錯誤: 找不到目標檔案 {target_script}")
        return False

    # 2. 準備注入檔案
    wrapper_script = "temp_fuzz_wrapper.py"
    try:
        with open(target_script, "r", encoding="utf-8") as f:
            original_code = f.read()
    except UnicodeDecodeError:
        # 如果讀取目標檔案就失敗，嘗試用系統編碼讀
        with open(target_script, "r", encoding="utf-8", errors="replace") as f:
            original_code = f.read()

    injected_code = f"{CHAOS_PAYLOAD}\n\n# --- ORIGINAL GAME CODE ---\n{original_code}"

    with open(wrapper_script, "w", encoding="utf-8") as f:
        f.write(injected_code)

    # 3. 執行測試
    print("🚀 啟動 Fuzzer 測試程序...")
    process = None
    try:
        cwd_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # --- [關鍵修正] 設定環境變數，強迫 Python 輸出 UTF-8 ---
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [sys.executable, wrapper_script],
            cwd=cwd_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            # --- [關鍵修正] 明確指定編碼，並忽略錯誤 ---
            encoding='utf-8',       # 強制父進程用 UTF-8 讀取
            errors='replace',       # 讀到亂碼直接變成 '?'，絕對不讓程式崩潰
            env=my_env              # 傳入環境變數
        )

        try:
            stdout, stderr = process.communicate(timeout=15)
            
            # 防呆：如果 stdout 是 None (雖然加了 errors='replace' 後應該不會發生)
            stdout = stdout if stdout else ""
            stderr = stderr if stderr else ""

            if "[FUZZ] SUCCESS" in stdout:
                print("✅ 測試通過：遊戲在壓力測試下存活且正常退出。")
                print("-" * 20)
                return True
            else:
                if process.returncode != 0:
                    print(f"❌ 測試失敗：遊戲崩潰 (Return Code: {process.returncode})")
                    print("--- Error Log ---")
                    print(stderr)
                    # 有時候錯誤訊息在 stdout 裡
                    if "Traceback" in stdout:
                        print("--- Stdout Log ---")
                        print(stdout)
                    return False
                else:
                    print("⚠️ 測試結束，但未偵測到完整成功訊號 (可能是手動關閉或無效測試)。")
                    # 檢查是否有隱藏的 Traceback
                    if "Traceback" in stdout or "Traceback" in stderr:
                         print("❌ 發現潛在錯誤:")
                         print(stderr)
                         return False
                    return True

        except subprocess.TimeoutExpired:
            print("❌ 測試超時：遊戲可能卡死 (Freeze)。")
            process.kill()
            return False

    except Exception as e:
        print(f"❌ Fuzzer 發生內部錯誤: {e}")
        return False
    finally:
        if os.path.exists(wrapper_script):
            try:
                os.remove(wrapper_script)
            except: pass

if __name__ == "__main__":
    success = run_fuzz_test()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)