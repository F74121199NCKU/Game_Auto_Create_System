import google.generativeai as genai
import sys
import os

from config import * # 包含 API Key, Models, Safety Settings
from utils import clean_code, code_to_py
from rag_system.core import get_rag_context


# 多次生成確保程式碼完整
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
    
    # 2. 遊戲企劃師
    system_instruction_planner = (
        "你是一個精通 Python Pygame 的資深技術企劃師。"
        "你的任務是根據「使用者需求」與「現有的參考程式碼 (Reference Code)」，規劃一份技術企劃書。"
        f"\n\n【現有參考程式碼 (Reference Modules)】\n{rag_context}\n\n"
        "【企劃書輸出要求】"
        "1. **Technical Architecture**: 你必須明確指出要如何使用上述的 Reference Modules。"
        "2. **Game Rules**: 描述遊戲流程。"
        "3. **Entities**: 定義數值。"
        "【限制】"
        "如果上述參考程式碼是空的，就依照你的通用知識規劃。"
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
    system_instruction_designer = (
        "你是一個資深的 Python 遊戲架構師。"
        "你的任務是根據企劃書，撰寫一個單一檔案的 Pygame 遊戲。"
        "【RAG 強制規範 - 絕對遵守】"
        f"我已讀取了內部的參考模組，內容如下：\n{rag_context}\n"
        "1. **你必須直接將上述參考模組的 Class (如 ObjectPool, GameSprite) 包含在你的最終程式碼中**。"
        "2. 嚴禁修改這些參考模組的核心邏輯。"
        "3. 在實作遊戲邏輯時，必須繼承或呼叫這些模組。"
        "【一般規範】"
        "1. 完整的單一檔案，包含 `import pygame`。"
        "2. 使用 `pygame.math.Vector2` 處理座標。"
        "3. 確保包含 `if __name__ == '__main__':`。"
        "4. 不要輸出 Markdown 標記。"
    )
    
    model_designer = genai.GenerativeModel('models/gemini-2.5-flash')
    response_designer = model_designer.generate_content(
        f"{system_instruction_designer}\n\n企劃書: {response_planner.text}",
        safety_settings=safety_settings
    )
    
    if not response_designer.text:
        print("❌ 程式碼生成失敗，請稍後再試。")
        sys.exit(1)
        
    code_content = loop_game_generate(response_designer.text, response_planner.text)
    code_content = clean_code(code_content)
    
    print("✅ 程式碼已生成完畢。")

    # 遊戲偵錯師 (Static Analysis)
    system_instruction_debugger = (
        "你是一個嚴格的 Python 程式碼審查員 (Code Reviewer)。"
        "【審查標準 (Strict Rules)】"
        "1. **Anti-Pattern 1 (No Globals):** 嚴禁使用 `global` 關鍵字。"
        "2. **Anti-Pattern 2 (No Spaghetti Loop):** 檢查 Game Loop 是否乾淨。"
        "3. **RAG Compliance:** 檢查程式碼是否正確使用了提供的 Reference Modules。"
        "4. **Security:** 檢查是否有危險呼叫。"
        "【輸出格式】"
        "直接輸出修正後的完整 Python 程式碼。不要輸出 Markdown 解釋。"
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