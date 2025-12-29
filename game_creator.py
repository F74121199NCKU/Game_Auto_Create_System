# game_creator.py 
import sys
from llm_agent import complete_prompt, generate_py
from Debug.fuzz_tester import run_fuzz_test
from Debug.executor import compile_and_debug, error_solving
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
    wrong = True
    while debug_times > 0:
        debug_times -= 1
        
        print(f"\n--- 進入第 {3 - debug_times} 輪測試 ---")

        # [階段一] 基本執行測試 (Executor)
        exec_result = compile_and_debug(filepath)
        
        if not exec_result["state"]:
            print(f"🔧 [Executor] 執行失敗，正在修復...")
            code_content = error_solving(exec_result["Text"], code_content)
            continue

        # [階段二] Fuzz 壓力測試 (Fuzz Tester)
        fuzz_result = run_fuzz_test()

        if fuzz_result["state"]:
            print("🎉 恭喜！遊戲通過所有測試 ！")
            wrong = False
            break
        else:
            print(f"🔧 [Fuzzer] 測試失敗，正在修復邏輯錯誤...")
            code_content = error_solving(fuzz_result["Text"], code_content)
            
    if debug_times == 0 and wrong :
        print("⚠️ 非常抱歉，自動修復次數耗盡，請檢查 dest/generated_app.py 進行手動調整。")

if __name__ == "__main__":
    print("🎮 AI Game Creator")
    user_request = input("請輸入你想製作的遊戲 (例如: 貪食蛇): ")
    if user_request:
        generate_whole(user_request)