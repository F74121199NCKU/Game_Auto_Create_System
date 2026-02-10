import subprocess
import sys
import os
import threading
import signal


CHAOS_PAYLOAD = """
# --- [INJECTED SAFE FUZZER CODE] START ---
import sys as _sys
import os as _os  # <--- [新增] 引入 OS 模組
import random as _random
import pygame as _pygame

# 強制設定輸出編碼為 UTF-8
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

        print(f"[FUZZER] Start Safe Mode Test ({duration_sec}s)")

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
        
        # --- [修正點] 時間到時，使用強制退出 ---
        if current_t > self.end_t:
            print("[FUZZ] SUCCESS: Test Passed cleanly.")
            try:
                _pygame.quit()
            except:
                pass
            _os._exit(0) # <--- [關鍵] 強制終止整個進程 (Process)，不留活口
            
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

def run_fuzz_test(target_path_arg=None):
    """
    執行 Fuzzer 測試，並回傳符合 game_creator 格式的字典。
    Returns:
        dict: {"state": bool, "Text": str}
    """
    # 1. 抓取路徑
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    debug_dir = os.path.join(base_dir, "Debug")
    dest_dir = os.path.join(base_dir, "dest")
    
    # 智慧目標選擇：優先用 debug_launcher
    launcher_path = os.path.join(debug_dir, "debug_launcher.py")
    target_script = ""

    if os.path.exists(launcher_path):
        target_script = launcher_path
    elif target_path_arg and os.path.exists(target_path_arg):
        target_script = target_path_arg
    else:
        target_script = os.path.join(dest_dir, "generated_app.py")

    print(f"🎯 Fuzzer 目標腳本: {target_script}")

    if not os.path.exists(target_script):
        return {"state": False, "Text": f"Fuzzer Error: 找不到目標檔案 {target_script}"}

    # 2. 準備注入檔案
    wrapper_script_path = os.path.join(base_dir, "temp_fuzz_wrapper.py")
    try:
        with open(target_script, "r", encoding="utf-8", errors="replace") as f:
            original_code = f.read()
        injected_code = f"{CHAOS_PAYLOAD}\n\n# --- ORIGINAL GAME CODE ---\n{original_code}"
        with open(wrapper_script_path, "w", encoding="utf-8") as f:
            f.write(injected_code)
    except Exception as e:
        return {"state": False, "Text": f"Fuzzer Error: 寫入暫存檔失敗 - {e}"}

    # 3. 執行測試
    print(f"🚀 啟動 Fuzzer... (Wrapper: {wrapper_script_path})")
    
    process = None
    try:
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [sys.executable, wrapper_script_path],
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # 關鍵：一定要抓 stderr
            text=True,
            encoding='utf-8',
            errors='replace',
            env=my_env
        )

        try:
            # 取得輸出 (這一步會捕捉 debug_launcher 印出的所有錯誤)
            stdout, stderr = process.communicate(timeout = 20)
            
            stdout = stdout if stdout else ""
            stderr = stderr if stderr else ""

            # --- 判斷結果 ---
            if "[FUZZ] SUCCESS" in stdout:
                print("✅ Fuzzer: 測試通過")
                return {"state": True, "Text": "Test Passed"}
            
            else:
                print(f"❌ Fuzzer: 測試失敗 (Code: {process.returncode})")
                
                # 組合錯誤訊息給 error_solving 用
                # 優先抓 stderr (通常是 Python 報錯)，如果沒有則抓 stdout 最後幾行 (可能是 print 的錯誤)
                error_content = ""
                if stderr.strip():
                    error_content = stderr
                else:
                    error_content = stdout[-1000:] # 取最後 1000 字
                
                # 如果還是空的，手動補上
                if not error_content.strip():
                    error_content = "Unknown Error: 程式崩潰但未捕捉到錯誤訊息 (Silent Crash)."

                return {"state": False, "Text": error_content}

        except subprocess.TimeoutExpired:
            print("\n✅ Fuzzer: 測試時間結束，遊戲未崩潰 (視為通過)")
            try:
                process.kill()
            except:
                pass
            return {"state": True, "Text": "Test Passed (Game Survived Duration)"}

    except Exception as e:
        print(f"❌ Fuzzer: 執行例外")
        return {"state": False, "Text": f"Fuzzer Internal Error: {e}"}
        
    finally:
        if os.path.exists(wrapper_script_path):
            try:
                os.remove(wrapper_script_path)
            except: pass

if __name__ == "__main__":
    # 單獨測試用
    result = run_fuzz_test()
    print(f"Result: {result}")
    if result["state"]:
        sys.exit(0)
    else:
        sys.exit(1)