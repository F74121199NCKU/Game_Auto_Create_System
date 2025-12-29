# game_creator.py 
import sys
from llm_agent import complete_prompt, generate_py
from executor import compile_and_debug, error_solving

def generate_whole(user_prompt: str):
    # 1. 優化提示詞
    user_prompt = complete_prompt(user_prompt)
    if not user_prompt:
        print("⚠️ 輸入非法提示詞或者發生未知錯誤，請重新提供提示詞")
        return
    
    # 2. 生成並儲存程式碼 (Agent 工作)
    filepath, code_content = generate_py(user_prompt)
    
    # 3. 執行與自動修復迴圈 (Executor 工作)
    debug_times = 3
    while debug_times > 0:
        debug_times -= 1
        
        # 嘗試編譯執行
        debug_result = compile_and_debug(filepath)
        
        if debug_result["state"]:
            print("🎉 遊戲可正確執行！")
            break
        else:
            print(f"🔧 偵測到錯誤，進行第 {3 - debug_times} 次自動修復...")
            # AI 修復程式碼
            code_content = error_solving(debug_result["Text"], code_content)
            
    if debug_times == 0:
        print("⚠️ 非常抱歉，自動修復次數耗盡，請檢查 dest/generated_app.py 進行手動調整。")

if __name__ == "__main__":
    print("🎮 AI Game Creator")
    user_request = input("請輸入你想製作的遊戲 (例如: 貪食蛇): ")
    if user_request:
        generate_whole(user_request)