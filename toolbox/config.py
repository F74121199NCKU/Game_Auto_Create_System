from google import genai
from google.genai import types
import sys
import os
import re

# API Key setup
API_KEY = input("Please enter your Google Gemini API Key: ").strip()
client = genai.Client(api_key=API_KEY)


# Global 
EMBEDDING_MODEL     = "models/gemini-embedding-001" 
MODEL_NORMAL        = 'gemini-2.5-flash'
MODEL_SMART         = 'gemini-3.1-pro-preview'
CHAOS_PAYLOAD = """
# --- [INJECTED SAFE FUZZER CODE] START ---
import sys as _sys
import os as _os
import random as _random
import pygame as _pygame

# Force output encoding to UTF-8
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

        # 加入 flush=True 確保字串立刻送出
        print(f"[FUZZER] Start Safe Mode Test ({duration_sec}s)", flush=True)

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
            # 移除 _pygame.mouse.set_pos((x, y)) 以避免底層 Thread Crash
        except: pass

    def update(self):
        current_t = _pygame.time.get_ticks()
        
        # --- [Fix Point] Forcibly exit when time is up ---
        if current_t > self.end_t:
            # 【關鍵修復】加入 flush=True 確保這句話一定會被 fuzz_tester 擷取到
            print("[FUZZ] SUCCESS: Test Passed cleanly.", flush=True)
            try:
                _pygame.quit()
            except:
                pass
            _os._exit(0) # 暴力退出前，字串已經安全送出了
            
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
                self._post_click(rand_x, rand_y)
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
        except Exception as e:
            import traceback
            print(f"[FUZZ] CRASH DETECTED: {e}", flush=True)
            traceback.print_exc()
            _os._exit(1)  # Force exit with error code so Executor catches it

import threading
_t = threading.Thread(target=_fuzzer_loop, daemon=True)
_t.start()
# --- [INJECTED SAFE FUZZER CODE] END ---
"""

# Safety Standards
safety_settings = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
]

