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
    max_attempts = 3  # 設定最大偵測次數 (想要偵測 3 次)
    wrong = True      # 預設狀態是錯誤的

    for current_attempt in range(1, max_attempts + 1):
        print(f"\n--- 進入第 {current_attempt} / {max_attempts} 輪測試 ---")

        # [階段一] (Executor: Compile & Run)
        exec_result = compile_and_debug(filepath)
        
        if not exec_result["state"]:
            # --- 失敗處理 ---
            if current_attempt < max_attempts:
                print(f"🔧 [Executor] 執行失敗，正在進行第 {current_attempt} 次修復...")
                code_content = error_solving(exec_result["Text"], code_content)
                # 修復完後，使用 continue 直接進入下一輪迴圈 (重新從 Executor 開始測)
                continue
            else:
                print("❌ [Executor] 最終測試失敗，已無修復機會。")
                break # 這是最後一次偵測，直接跳出

        # [階段二] Fuzz 壓力測試 (Fuzz Tester: Runtime Logic)
        # 只有當 Executor 通過時，才會進到這裡
        fuzz_result = run_fuzz_test()

        if fuzz_result["state"]:
            # --- 成功 ---
            print("🎉 恭喜！遊戲通過所有測試！")
            wrong = False
            break # 測試全部通過，跳出迴圈
        else:
            # --- 失敗處理 ---
            if current_attempt < max_attempts:
                print(f"🔧 [Fuzzer] 測試失敗，正在進行第 {current_attempt} 次邏輯修復...")
                code_content = error_solving(fuzz_result["Text"], code_content)
                # 修復完後，使用 continue 直接進入下一輪 (確保修復後的代碼也能通過 Executor)
                continue
            else:
                print("❌ [Fuzzer] 最終測試失敗，已無修復機會。")
                break

    # [最終結果判定]
    if wrong:
        print("\n⚠️ 非常抱歉，自動修復次數耗盡，無法正確偵錯。")
        print("請檢查 dest/generated_app.py 進行手動調整。")

if __name__ == "__main__":
    print("🎮 AI Game Creator")
    user_request = input("請輸入你想製作的遊戲 (例如: 貪食蛇): ")
    
    #測試用範例
    user_request = """
    幫我開發一款類似 Vampire Survivors 的 2D Roguelike 生存遊戲。1. 地圖與視角： 偽無限地圖（或是鏡頭跟隨玩家移動），背景無限延伸。2. 玩家操作：WASD 控制角色移動。3. 滑鼠游標: 控制攻擊的瞄準方向。4. 攻擊機制: 玩家不需要點擊滑鼠，角色會自動每隔 1 秒向「滑鼠游標當下的方向」發射一把飛刀。飛刀具有飛行速度與碰撞檢測。5. 敵人系統(1)敵人會源源不絕地從螢幕邊緣（視窗外）生成。(2)敵人會自動追蹤（移動向）玩家位置。(3)敵人碰到玩家會造成傷害。6.RPG 數值系統：(1)生命值 (HP)： 玩家有血量，被碰到會扣血，血量歸零則遊戲結束 (Game Over)。(2)經驗值 (XP)： 敵人死亡後會掉落經驗寶石 (Gem)。(3)升級機制： 玩家吃到寶石增加經驗條。升級時「遊戲暫停」，跳出 UI 選單讓玩家三選一：『增加攻速 (冷卻減少)』、『增加傷害』、『恢復血量』。7. 獲勝條件： 玩家存活滿 60 秒即獲勝。
    """
    if user_request:
        generate_whole(user_request)