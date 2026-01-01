import google.generativeai as genai
import sys
import os

from config import * # 包含 API Key, Models, Safety Settings
from tools import clean_code, code_to_py
from rag_system.core import get_rag_context

# 多次生成確保程式碼完整
def loop_game_generate(code: str, response_planner: str, times_remain: int = 2) -> str:
    current_code = code
    
    """
    for i in range(times_remain):
        print(f"🔄 正在進行第 {i+1} 輪優化架構審查...")

        # 審計階段 (The Auditor)
        audit_prompt = (
            "你是一個嚴格的 Python 程式碼審查員 (Senior Code Reviewer)。"
            "請檢視以下的 Pygame 程式碼，並根據「資工系高效能架構」標準進行審查。\n"
            "【審查重點】\n"
            "1. 是否有濫用全域變數 (Global Variables)？\n"
            "2. 是否有硬編碼 (Hard-coding) 的數值？\n"
            "3. Game Loop 是否混合了邏輯與渲染 (Update/Draw 沒分離)？\n"
            "4. 是否缺乏物件導向 (OOP) 設計？\n"
            "5. 變數命名是否清晰？\n\n"
            "【輸出要求】\n"
            "請條列出 **3 個最嚴重、必須修正的問題點**。只要列出問題，不要寫程式碼。"
            f"\n\n待審查程式碼:\n{current_code}"
        )
        
        model_auditor = genai.GenerativeModel(MODEL_SMART)
        audit_response = model_auditor.generate_content(audit_prompt, safety_settings = safety_settings)
        critique = audit_response.text

        # 重構階段 (The Refactorer)
        model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp')
        refine_prompt = (
            "你是一個資深的 Python 遊戲重構工程師。"
            "請根據「原始程式碼」以及「審查員的批評」，重寫並優化程式碼。\n\n"
            f"【原始程式碼】\n{current_code}\n\n"
            f"【審查員的批評 (待修復清單)】\n{critique}\n\n"
            "【任務指令】\n"
            "1. 請針對上述批評點進行重構 (Refactoring)。\n"
            "2. 保持程式碼完整性，確保可以直接執行。\n"
            "3. 確保所有類別與函式都有 Type Hinting。\n"
            "4. 只輸出 Python 程式碼，不要輸出解釋文字。"
            "【自動化測試定義 - 必須遵守】"
            "   - 必須定義 `self.game_active` (bool) 作為標準測試接口，預設為 False。"
            "   - **關鍵邏輯**：在 `run()` 方法的最開頭，必須檢查 `if self.game_active:`。"
            "   - 如果 `self.game_active` 為 True，**必須強制跳過選單**，直接呼叫 `self.change_state(PLAYING)` 或執行遊戲主迴圈。"
            "   - 這對自動化測試debug至關重要，請務必實作。"
        )

        model_refiner = genai.GenerativeModel(MODEL_FAST)
        refine_response = model_refiner.generate_content(refine_prompt, safety_settings=safety_settings)
        
        if len(refine_response.text) > 100:
            current_code = clean_code(refine_response.text)
        else:
            print("❌ 優化失敗，生成內容不完整，跳過此輪。")
    """
    return current_code

# 優化提示詞與安全檢測
def complete_prompt(user_prompt: str) -> str:
    print("🛡️ 正在進行輸入安全檢查與優化...")
    
    model = genai.GenerativeModel(MODEL_FAST)
    
    system_instruction = (
        "你是一個 AI 遊戲需求分析師與安全官。"
        "【規則 1：安全過濾 (Security)】"
        "若包含惡意指令 (刪除、攻擊、色情)，直接回傳 'INVALID'。"
        "【規則 2：需求具體化 (Specification)】"
        "如果輸入模糊 (如 '做個遊戲')，請自行構思一個經典遊戲 (如: 貪食蛇、俄羅斯方塊等)。"
        "並且，你必須**主動建議技術細節**，例如："
        "   - '建議使用 Object Pool 管理子彈'"
        "   - '建議使用 Spatial Grid 優化大量敵人'"
        "【規則 3：格式化輸出】"
        "請輸出一段清晰的遊戲開發指令，包含：遊戲名稱、核心玩法、以及建議使用的技術模組。"
        "直接輸出優化後的提示詞，不要包含其他解釋。"
    )
    
    try:
        response = model.generate_content(f"{system_instruction}\n\n使用者原始輸入: {user_prompt}")
        refined_prompt = response.text.strip()
        
        if refined_prompt.startswith("INVALID"):
            print(f"⚠️ 警告：{refined_prompt}")
            return "" 
            
        print(f"✨ 提示詞已優化")
        return refined_prompt

    except Exception as e:
        print(f"❌ 發生錯誤 : {e}")
        return ""

# 遊戲程式碼生成  
def generate_py(user_prompt) -> str:
    # 1. 先去資料庫撈程式碼 (RAG 步驟)
    rag_context = get_rag_context(user_prompt)
    
    # 2. 遊戲企劃師 (Planner) - 完整企劃書 + JSON 混合版本
    system_instruction_planner = (
        "你是一個精通 Python Pygame 的資深技術企劃師。"
        "你的任務是根據「使用者需求」與「現有的參考程式碼 (Reference Code)」，撰寫一份詳盡的技術企劃書。"
        f"\n\n【現有參考程式碼 (Reference Modules)】\n{rag_context}\n\n"
        
        "【輸出格式規範】"
        "請將回覆分為兩個部分："
        "**第一部分：完整企劃說明書 (Markdown 格式)**"
        "   - 請使用繁體中文，詳細說明遊戲架構、邏輯與設計思路。"
        "   - 必須包含以下章節："
        "     1. **遊戲概念與架構分析**: 說明如何運用 RAG 模組 (如 Camera, Collision) 來實現需求。"
        "     2. **遊戲流程**: 詳細描述從「主選單」->「遊戲進行」->「暫停」->「結算(勝利/失敗)」->「重新開始」的完整循環。"
        "     3. **操作與 UI 設計**: 定義按鍵 (包含 P/ESC 暫停)、HUD 資訊顯示、選單按鈕佈局。"
        "     4. **實體數值設計**: 定義玩家、敵人、建築物的具體數值 (速度、血量、價格等)。"
        
        "**第二部分：結構化參數配置 (JSON Code Block)**"
        "   - 在企劃書的最後，提供一個 JSON 區塊，供程式後續解析使用。"
        "   - **必須** 將 JSON 包裹在 Markdown 程式碼區塊中，格式如下："
        "     ```json"
        "     {"
        "       \"game_name\": \"...\", "
        "       ... (依照下方 Schema)"
        "     }"
        "     ```"

        "【JSON Schema 要求】"
        "JSON 結構必須符合："
        "{"
        "  \"game_name\": \"遊戲名稱\","
        "  \"technical_architecture\": {"
        "    \"used_modules\": [\"列出必須使用的 RAG 模組檔名，如 mouse_camera.py\"],"
        "    \"implementation_details\": \"簡述技術整合重點\""
        "  },"
        "  \"game_rules\": [\"規則清單...\"],"
        "  \"entities\": ["
        "    {\"name\": \"Player\", \"variables\": \"...\"},"
        "    {\"name\": \"Enemy\", \"variables\": \"...\"}"
        "  ]"
        "}"

        "【企劃核心要求】"
        "1. **失敗與勝利條件**: 必須明確定義 (例如：塔被毀導致失敗、擊殺數達標導致勝利)。"
        "2. **強制暫停機制**: 必須實作 'P' 或 'ESC' 鍵暫停，暫停後顯示選單 (繼續/重來/規則/離開)。"
        "3. **完整選單系統**: 遊戲開始前要有主選單，主選單必須包含以下四者，「開始遊戲」、「結束遊戲」、「規則，結束後要有結算畫面並支援「重新開始」。"
        "4. **RAG 模組應用**: 在 `used_modules` 中精準列出需要的檔案 (如 `mouse_camera.py`, `collision.py`)。"
    )
    
    model_planner = genai.GenerativeModel('models/gemini-2.5-flash')
    response_planner = model_planner.generate_content(
        f"{system_instruction_planner}\n\n使用者需求: {user_prompt}",
        safety_settings=safety_settings
    )
    print("✅ 企劃書已生成完畢。")

    folder = "dest"
    filename = "game_design_document.txt"
    os.makedirs(folder, exist_ok = True)
    filename = os.path.join(folder, filename)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response_planner.text)

    # 3. 遊戲工程師
    # 1. 遊戲架構師 (Designer) - 優化版
    system_game_designer = (
        "你是一個資深的 Python Pygame 遊戲架構師。任務是根據 JSON 企劃書與參考模組，撰寫單一檔案的遊戲程式碼。"
        
        "【核心指令 (CRITICAL INSTRUCTIONS)】"
        "1. **RAG 模組整合 (嚴格執行)**:"
        "   - 必須直接包含並使用提供的參考模組 (ObjectPool, GameSprite 等)。"
        "   - **嚴禁修改** 模組核心邏輯，僅能繼承或呼叫。"
        
        "2. **架構與依賴注入 (Architecture)**:"
        "   - **物件池分離**: `ObjectPool` 僅用於 `get/release`。渲染必須用 `pygame.sprite.Group`。"
        "     - 初始化時必須同時傳入 `pool` (生產) 與 `group` (渲染)。"
        "     - 寫法範例: `def __init__(self, projectile_pool, projectiles_group): ...`"
        "   - **狀態機安全**: `change_state` 呼叫 `enter(**kwargs)` 時，**必須**使用 `kwargs.setdefault()` 避免參數衝突。"

        "3. **物理與迴圈穩定性 (Physics & Loop Stability)**:"
    "   - **Delta Time 限制 (防止穿牆)**: 在 `Game.run` 迴圈中，**必須** 限制 `dt` 最大值。"
    "     - 強制寫法: `dt = min(self.clock.tick(FPS) / 1000.0, 0.05)` (上限 0.05秒)，防止視窗拖動或卡頓時造成的物體瞬移。"
    "   - **浮點數座標**: 禁止直接操作 `rect.x/y`。必須維護 `self.pos` (Vector2) 並在運算後同步至 `rect`。"
    "   - **分離軸運動 (Separated Axis Movement)** (防止卡牆/滑步):"
    "     - **嚴禁** 同時更新 X 和 Y 後才檢查碰撞 (這會導致角色陷進地板滑行)。"
    "     - **必須** 採用嚴格順序: 1. 移動 X -> 2. 檢查/修正 X 碰撞 -> 3. 移動 Y -> 4. 檢查/修正 Y 碰撞。"

        "4. **自動化測試接口 (Auto-Test Hook)**:"
        "   - `Game.__init__`: 預設 `self.game_active = False`。"
        "   - `Game.run()`: 開頭必須檢查 `if self.game_active:`，若為 True 則**強制跳過選單**直接開始遊戲。"
        "   - `if __name__ == '__main__':`: 必須顯式設定 `game.game_active = False` 以顯示選單。"

        "5. **UI 與顯示規範 (UI & Display)**:"
        "   - **中文字體**: 必須使用 `pygame.font.match_font('microsoftjhenghei')` 或 `simhei` 避免亂碼。"
        "   - **游標**: 嚴禁隱藏滑鼠 (`set_visible(False)`)，除非已實作自定義游標。"
        "   - **相機剔除**: Frustum Culling 必須保留至少 100px 緩衝區 (Margin)。"
        "   - **初始鏡頭**: `reset_game` 時相機必須立即對準玩家基地。"

        "6. **完整選單系統 (Menu System)**:"
        "   - **Main Menu**: 開始、規則、離開。"
        "   - **Pause Menu** (P/ESC): 繼續、重來、規則、回主選單。"
        "   - **Game Over**: 顯示 SUCCESS/FAIL，包含重來、回主選單、離開。"
        "   - 確保所有狀態下都能呼叫 Menu 並正確切換。"

        "【輸入處理】"
        "解析輸入的 JSON (`technical_architecture`, `game_rules`)，產出單一 `import pygame` 的完整 Python 檔案，不含 Markdown。"
    )
    
    model_designer = genai.GenerativeModel('models/gemini-2.5-flash')
    response_designer = model_designer.generate_content(
        f"{system_game_designer}\n\n企劃書: {response_planner.text}",
        safety_settings=safety_settings
    )
    
    if not response_designer.text:
        print("❌ 程式碼生成失敗，請稍後再試。")
        sys.exit(1)
    
    code_content = response_designer.text
    #code_content = loop_game_generate(response_designer.text, response_planner.text)
    code_content = clean_code(code_content)
    
    print("✅ 程式碼已生成完畢。")

    # 遊戲偵錯師 (Static Analysis)
    # 3. 遊戲偵錯師 (Static Analysis / Code Reviewer)
    system_instruction_debugger = (
        "你是一個嚴格的 Python Code Reviewer。你的任務是分析輸入的 Pygame 程式碼，修正所有邏輯錯誤、崩潰風險與架構問題，並直接輸出修正後的完整程式碼。"
        
        "【核心審查規則 (CRITICAL RULES)】"
        "1. **架構規範**: 嚴禁 Global 變數；Game Loop 邏輯須封裝；正確引用 RAG 模組。"
        "2. **物件池安全 (Object Pool)**:"
        "   - `ObjectPool` 僅有 `get()`/`release()`，**無** `add()`。"
        "   - **分離原則**: 必須同時傳入 `pool` (生成用) 與 `group` (渲染用)。禁止將物件 add 進 pool。"
        "   - **回收機制**: 物件 `kill()` 時必須呼叫 `pool.release(obj)`。"
        "3. **物理與數學**: 禁止直接修改 `rect.x/y` (整數精度遺失)，必須使用 `Vector2` (`self.pos`) 運算後同步至 Rect。"
        "4. **狀態機安全**: `change_state` 呼叫 `enter(**kwargs)` 時，必須使用 `kwargs.setdefault()` 防止參數衝突 (TypeError)。"
        "5. **啟動配置**: `Game.__init__` 中 `game_active` 預設為 `False`。`if __name__ == '__main__':` 須顯式設為 `False` 以顯示選單。"

        "【常見錯誤偵測 (Common Errors)】"
        "主動掃描並修復以下模式："
        "1. **AttributeError/NameError**: 檢查變數拼寫 (Snake_case)；檢查 State 是否存取了未注入的 Context 變數 (如 `self.spatial_grid` vs `self.context.spatial_grid`)。"
        "2. **UnboundLocalError**: 確保變數在所有邏輯分支 (if/else) 都有定義。"
        "3. **TypeError (參數與初始化衝突)**:"
        "   - **Argument Conflict**: `enter(**kwargs)` 若有具名參數衝突，改用 `kwargs.setdefault()`。"
        "   - **Multiple Values for Argument**: 若出現 `TypeError: GameSprite.__init__() got multiple values for argument 'pos'`，這表示 `super().__init__` 呼叫時參數重複。"
        "     - **修正**: 檢查是否同時用了位置參數 (`x, y`) 與關鍵字參數 (`pos=...`)，或父類別定義變更。確保呼叫簽名 (Signature) 完全匹配。"
        "4. **NoneType Crash**: 存取物件屬性前 (如 `target.rect`) 必先檢查 `if target:`。"
        "5. **Dependency Injection**: 確保所有外部依賴 (Manager, Group) 都已透過 `__init__` 正確傳遞。"
        
        "【輸出格式】"
        "直接輸出修正後的完整 Python 程式碼 (純文字)，不含 Markdown 標記或解釋。"
    )
    model_debugger = genai.GenerativeModel(MODEL_SMART)
    response_debugger = model_debugger.generate_content(
        f"{system_instruction_debugger}\n\n企劃書: {response_planner.text}\n\n程式碼: {code_content}",
        safety_settings = safety_settings
    )
    code_content = clean_code(response_debugger.text)
    print("✅ 程式碼已偵錯完畢。")

    filepath = code_to_py(code_content)
    return filepath, code_content