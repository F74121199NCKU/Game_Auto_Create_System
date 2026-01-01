import sys
import subprocess
import os
import google.generativeai as genai

# 引入模組
from config import *
from tools import code_to_py, clean_code

# 遊戲編譯與初步偵錯 (Runtime Check)
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
            timeout = 10,             # 測試時間
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
    except Exception as e:
        print(f"❌ 發生系統錯誤: {e}")  
        return {
            "state": False,
            "Text": str(e)
        }

# 遊戲除錯 (Runtime Error Fixing)
def error_solving(error_msg, code_content) -> str:
    system_instruction_error_solver = (
        "你是一個 Python 執行期錯誤修復專家 (Runtime Exception Specialist)。"
        "你的任務是根據「完整的 Python 原始碼」以及「控制台錯誤訊息 (Traceback/Stderr)」，修復導致程式崩潰的錯誤。"
        "【修復策略與規範】"
        "1. **Traceback 優先:** 針對報錯的那一行進行精準修復。"
        "2. **禁止鴕鳥心態:** 嚴禁為了解決錯誤而直接刪除功能。"
        "3. **保持架構完整:** 維持原有的 OOP 架構。"
        "【輸出格式】"
        "直接輸出修復後、可直接執行的完整 Python 程式碼 (Full Code)。"
        "嚴禁輸出 Markdown 標記，嚴禁輸出任何解釋文字。"
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
    code_content = clean_code(response_debugger.text)
    code_to_py(code_content) # 存檔覆蓋
    return code_content