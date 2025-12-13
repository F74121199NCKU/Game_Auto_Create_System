import google.generativeai as genai     #type: ignore
from groq import Groq # type: ignore
import sys
import subprocess
import os
import re

#設定 API Key
api_key_user = input("Please enter your own Google Gemini API Key: ").strip()
genai.configure(api_key = api_key_user)

#model types
MODEL_FAST = 'models/gemini-2.5-flash'
MODEL_SMART = 'models/gemini-2.5-flash'
MODEL_CREATIVE = 'models/gemini-2.5-flash'
MODEL_VISION = 'models/gemini-2.5-flash'

#安全設定
safety_settings = [
    { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

#多次生成確保程式碼完整
def loop_game_generate(code: str, response_planner: str, times_remain: int = 2) -> str:
    current_code = code

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
        )

        model_refiner = genai.GenerativeModel(MODEL_FAST)
        refine_response = model_refiner.generate_content(refine_prompt, safety_settings=safety_settings)
        
        if len(refine_response.text) > 100:
            current_code = clean_code(refine_response.text)
        else:
            print("❌ 優化失敗，生成內容不完整，跳過此輪。")

    return current_code

#儲存為 .py 檔案
def code_to_py(code, filename = "generated_app.py", folder = "dest"):
    os.makedirs(folder, exist_ok = True)
    file_path = os.path.join(folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    print(f"📁 檔案已儲存至: {file_path}")
    return file_path 

#刪除LLM提供的垃圾訊息
def clean_code(raw_text: str) -> str:                       
    clean_text = re.sub(r'^```python\s*', '', raw_text)   
    clean_text = re.sub(r'^```\s*', '', clean_text)       
    clean_text = re.sub(r'```$', '', clean_text)          
    return clean_text.strip()

#優化提示詞與安全檢測
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
    print(f"🔄 正在撰寫程式")
    
    #遊戲企劃師
    system_instruction_planner = (
        "你是一個精通 Python Pygame 的資深技術企劃師 (Technical Game Designer)。"
        #"你的任務是將使用者的模糊需求，轉化為一份「可被 RAG 系統執行」的技術企劃書。"
        "你的任務是將**用戶所提出的不夠詳盡的需求**，轉化為一份「可被系統執行」的企業級技術企劃書。"
        "【輸入資訊】"
        "1. 使用者需求 (User Request)"
        "2. 系統能力清單 (System Manifest): 這是一份 JSON，列出了我們現有的程式模組 (如 ObjectPool, ShootingComponent)。"
        
        "【企劃書輸出要求】"
        "請輸出 Markdown 格式，必須包含以下章節："
        "1. **Game Overview**: 遊戲名稱與核心玩法簡述。"
        "2. **Technical Architecture (關鍵)**: "
        "   - 請根據 System Manifest，明確列出此遊戲需要載入哪些模組？"
        "   - 格式範例: '- [Load] ShootingComponent: 用於玩家發射子彈'"
        "   - 格式範例: '- [Load] SpatialGrid: 用於大量敵人碰撞優化'"
        "3. **Game Rules & Logic**: 詳細描述狀態流程 (State Flow: Menu -> Play -> GameOver)。"
        "4. **Entities & Values**: 定義角色數值 (如 Player Speed = 300, Fire Rate = 0.2)。"
        
        "【思考限制】"
        "不要天馬行空地幻想不存在的功能。盡量利用 Manifest 中已有的組件來組合遊戲。"
        "如果 Manifest 中沒有適合的組件，才允許描述需要從頭撰寫的邏輯。"
    )
    model_planner = genai.GenerativeModel(MODEL_CREATIVE)
    response_planner = model_planner.generate_content(f"{system_instruction_planner}\n\n使用者需求: {user_prompt}",
                                              safety_settings = safety_settings)
    print("✅ 企劃書1已生成完畢。")

    system_instruction_planner = (
        "你是一個精通 Python Pygame 的資深技術企劃師 (Technical Game Designer)。"
        #"你的任務是將初步計劃書不夠詳盡的需求，轉化為一份「可被 RAG 系統執行」的企業級技術企劃書。"
        "你的任務是將 **初步計劃書延伸，使其更詳盡**，並且是「可被系統執行」的企業級技術企劃書。"
        "【輸入資訊】"
        "1. 使用者需求 (User Request)"
        "2. 系統能力清單 (System Manifest): 這是一份 JSON，列出了我們現有的程式模組 (如 ObjectPool, ShootingComponent)。"
        
        "【企劃書輸出要求】"
        "請輸出 Markdown 格式，必須包含以下章節："
        "1. **Game Overview**: 遊戲名稱與核心玩法簡述。"
        "2. **Technical Architecture (關鍵)**: "
        "   - 請根據 System Manifest，明確列出此遊戲需要載入哪些模組？"
        "   - 格式範例: '- [Load] ShootingComponent: 用於玩家發射子彈'"
        "   - 格式範例: '- [Load] SpatialGrid: 用於大量敵人碰撞優化'"
        "3. **Game Rules & Logic**: 詳細描述狀態流程 (State Flow: Menu -> Play -> GameOver)。"
        "4. **Entities & Values**: 定義角色數值 (如 Player Speed = 300, Fire Rate = 0.2)。"
        
        "【思考限制】"
        "不要天馬行空地幻想不存在的功能。盡量利用 Manifest 中已有的組件來組合遊戲。"
        "如果 Manifest 中沒有適合的組件，才允許描述需要從頭撰寫的邏輯。"
    )
    response_planner = model_planner.generate_content(f"{system_instruction_planner}\n\n初步企劃書: {response_planner.text}",
                                              safety_settings = safety_settings)
    print("✅ 企劃書2已生成完畢。")

    folder = "dest"
    filename = "game_design_document.txt"
    os.makedirs(folder, exist_ok = True)
    filename = os.path.join(folder, filename)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response_planner.text)

    #遊戲工程師
    system_instruction_designer = (
        "你是一個資深的 Python 遊戲架構師 (Architect)。你的任務是根據企劃書，"
        "撰寫一個高品質、高效能的 Pygame 單一執行檔。"
        
        #"【RAG 核心指令 - 絕對遵守】"
        #"1. 我會提供你數個 'Reference Modules' (參考模組)，其中包含核心引擎、物件池等實作。"
        #"2. 你必須將這些模組的 Class 整合進最終程式碼中，**嚴禁修改參考模組的核心邏輯**。"
        #"3. 你只能在具體的遊戲邏輯 (如 class Enemy(Sprite)) 中繼承或呼叫這些模組。"
        
        "【架構與設計模式規範】"
        "1. **Game Loop:** 嚴格遵守 'Update (Logic) -> Draw (Render)' 分離原則。所有移動必須乘上 `dt` (Delta Time)。"
        "2. **Object Pool:** 若遊戲涉及頻繁生成的物件（如子彈、粒子），必須使用提供的 GenericObjectPool，嚴禁使用 `new Bullet()`。"
        "3. **Event System:** 使用觀察者模式 (Observer Pattern) 或簡單的 Callback 處理跨物件溝通（例如：玩家死亡通知 UI），避免在 Player 類別中直接 import UI。"
        "4. **State Machine:** 使用 Enum 與字典映射 (Dict Mapping) 來管理遊戲狀態 (MENU, PLAYING, GAME_OVER)，嚴禁在主迴圈寫巨大的 if-else 巢狀結構。"
        "5. **Object-Oriented Programming:** 使用 Class 與繼承來組織遊戲物件，避免大量的全域變數與函式。"

        "【效能優化規範 (Hard Constraints)】"
        "1. **Vector2:** 所有座標與速度計算必須使用 `pygame.math.Vector2`。"
        "2. **Spatial Partitioning:** 若同畫面物件超過 50 個，必須實作簡單的網格 (Spatial Grid) 或只對視窗內的物件進行碰撞檢查。"
        "3. **Rendering:** 載入圖片務必使用 `.convert()` 或 `.convert_alpha()`。"
        
        "【輸出格式規範】"
        "1. 輸出為單一 Python 檔案，包含所有 import。"
        "2. 不要在代碼塊外輸出任何文字、解釋或 Markdown 標記 (如 ```python)。"
        "3. 確保包含 `if __name__ == '__main__':` 區塊。"
        "4. 必須包含一個基於 GUI (pygame_gui 或自行繪製) 的規則說明頁面，按任意鍵開始遊戲。"
    )
    
    model_designer = genai.GenerativeModel(MODEL_SMART)
    response_designer = model_designer.generate_content(f"{system_instruction_designer}\n\n企劃書: {response_planner.text}",
                                               safety_settings = safety_settings)
    if not response_designer.text:
        print("❌ 程式碼生成失敗，請稍後再試。")
        sys.exit(1)
    code_content = loop_game_generate(response_designer.text, response_planner.text)
    
    # 清理可能殘留的 Markdown 標記
    code_content = clean_code(code_content)
    print("✅ 程式碼已生成完畢。")

    #遊戲偵錯師
    system_instruction_debugger = (
        "你是一個嚴格的 Python 程式碼審查員 (Code Reviewer)，專門負責 Pygame 架構審查。"
        "你的目標不是修復簡單的語法錯誤，而是確保程式碼符合「資工系專題」的高級架構規範。"
        
        "【審查標準 (Strict Rules)】"
        "1. **Anti-Pattern 1 (No Globals):** 嚴禁使用 `global` 關鍵字。所有變數必須封裝在 `class Game` 或其他類別中。若發現 `global`，請強制重構為類別屬性。"
        "2. **Anti-Pattern 2 (No Spaghetti Loop):** 檢查 Game Loop 是否乾淨。邏輯運算應委派給 `sprite.update(dt)`，繪圖應委派給 `sprite.draw()`。主迴圈不應包含大量邏輯判斷。"
        "3. **RAG Compliance (關鍵):** 檢查程式碼是否正確使用了提供的 Reference Modules (如 ObjectPool)。"
        "   - 錯誤範例: `bullets.append(Bullet())` (未使用 Pool)"
        "   - 正確範例: `pool.get(pos, dir)`"
        "4. **Security:** 檢查是否有危險的 `eval()`, `exec()`, 或 `subprocess` 呼叫，直接刪除該段代碼。"
        
        "【輸出格式】"
        "直接輸出修正後的完整 Python 程式碼 (Full Code)。不要輸出 Markdown 解釋，不要廢話。"
    )
    model_debugger = genai.GenerativeModel(MODEL_SMART)
    response_debugger = model_debugger.generate_content(f"{system_instruction_debugger}\n\n企劃書: {response_planner.text}\n\n程式碼: {code_content}",
                                               safety_settings = safety_settings)
    code_content = response_debugger.text

    # 清理可能殘留的 Markdown 標記
    code_content = clean_code(code_content)
    print("✅ 程式碼已偵錯完畢。")


    #儲存為 .py 檔案
    filepath = code_to_py(code_content)
    return filepath, code_content

#遊戲編譯與初步偵錯(error)
def compile_and_debug(full_path: str) -> dict:
    folder = os.path.dirname(full_path)      
    filename = os.path.basename(full_path) 
    print(f"🔄 正在執行並偵錯 {filename} 在 {folder}資料夾中 ...")

    try:
        result = subprocess.run(
            [sys.executable, filename],
            capture_output = True,
            text = True,
            cwd = folder,
            timeout = 10,             #測試時間
            encoding = 'utf-8', 
            errors = 'ignore'         # 忽略無法解碼的字元
        )
        if result.returncode == 0:
            print("✅ 遊戲執行完畢(Unusual)")
            return {
                "state": True,
                "Text": None
            }
        else:
            print("❌ 程式執行失敗，發生錯誤！")
            return {
                "state": False,
                "Text": result.stderr
            }
    except subprocess.TimeoutExpired:
        print("✅ 遊戲可持續執行")
        return {
                "state": True,
                "Text": None
        }
    except Exception as e:                  #TimeoutExpired 以外的錯誤
        print(f"❌ 發生系統錯誤: {e}")  
        return {
            "state": False,
            "Text": str(e)
        }

#遊戲除錯
def error_solving(error_msg, code_content) -> str:
    system_instruction_error_solver = (
        "你是一個 Python 執行期錯誤修復專家 (Runtime Exception Specialist)。"
        "你的任務是根據「完整的 Python 原始碼」以及「控制台錯誤訊息 (Traceback/Stderr)」，修復導致程式崩潰的錯誤。"
        
        "【輸入資料說明】"
        "1. 錯誤代碼 (Traceback): 這是 Python 解譯器報出的真實錯誤，包含錯誤類型與行號。"
        "2. 原始碼 (Source Code): 目前會崩潰的程式碼。"
        
        "【修復策略與規範 - 必須嚴格遵守】"
        "1. **Traceback 優先:** 仔細閱讀錯誤訊息中的 File, Line, 和 Error Type。針對報錯的那一行進行精準修復。"
        "2. **禁止鴕鳥心態 (No Feature Removal):** 嚴禁為了解決錯誤而直接刪除整段邏輯或功能。例如：如果 `draw()` 報錯，你必須修復繪圖邏輯，而不是把 `draw()` 函式清空。"
        "3. **常見錯誤處置指引:**"
        "   - **AttributeError:** 通常是因為變數忘記加 `self.`，或者忘記在 `__init__` 中初始化。請檢查 `__init__` 是否漏寫。"
        "   - **UnboundLocalError:** 這是變數作用域問題。請檢查是否在函式內使用了全域變數但忘記 `self.` 或傳遞參數。"
        "   - **ModuleNotFoundError:** 如果引用了不存在的第三方函式庫，請將其替換為標準庫或 Pygame 內建功能，或者直接實作該功能的簡易版本。"
        "   - **RecursionError:** 檢查是否有函式無限遞迴呼叫，或 Game Loop 邏輯寫死。"
        "4. **保持架構完整:** 修正錯誤時，必須維持原有的 OOP 架構與 Class 結構，不要破壞 RAG 系統生成的模組化設計。"
        
        "【輸出格式】"
        "直接輸出修復後、可直接執行的完整 Python 程式碼 (Full Code)。"
        "嚴禁輸出 Markdown 標記 (如 ```python)，嚴禁輸出任何解釋文字。"
    )
    model = genai.GenerativeModel(MODEL_SMART)
    response_debugger = model.generate_content(f"""
            {system_instruction_error_solver}

            === 執行期錯誤報告 (Runtime Error Traceback) ===
            {error_msg}
            ==============================================

            === 原始程式碼 (Source Code) ===
            {code_content}
            ==============================================

            請根據上方的錯誤報告，修復原始程式碼。
            """
    )
    code_content = response_debugger.text
    code_content = clean_code(code_content)
    code_to_py(code_content)
    return code_content

# 主流程
def generate_whole(user_prompt: str):
    user_prompt = complete_prompt(user_prompt)
    if not user_prompt:
        print("⚠️ 輸入非法提示詞或者發生未知錯誤，請重新提供提示詞")
        return
    
    filepath, code_content = generate_py(user_prompt)
    debug_times = 3
    while debug_times > 0:
        debug_times -= 1
        debug_result = compile_and_debug(filepath)
        if debug_result["state"]:
            print("🎉 遊戲可正確執行")
            break
        else:
            print(f"進行第 {3 - debug_times} 次偵錯...")
            code_content = error_solving(debug_result["Text"], code_content)
    if debug_times == 0:
        print("⚠️ 非常抱歉，無法成功偵錯，請提供其他提示詞")
# 執行
if __name__ == "__main__":
    user_request = input("請輸入你想製作的遊戲 (例如: 貪食蛇): ")
    generate_whole(user_request)