# game_creator.py 
import time
import sys
from core.llm_agent import complete_prompt, generate_py
from Debug.fuzz_tester import run_fuzz_test
from Debug.executor import compile_and_debug, error_solving

def generate_whole(user_prompt: str):
    # 1. Optimize prompt
    user_prompt = complete_prompt(user_prompt)
    if not user_prompt:
        print("⚠️ Invalid prompt or unknown error occurred. Please provide the prompt again.")
        return
    
    # 2. Generate and save code (Agent task)
    filepath, code_content = generate_py(user_prompt)
    
    # 3. Execution and auto-repair loop (Executor task)
    max_attempts = 3  # Set maximum number of detection attempts (3 times)
    wrong = True      # Default state is failing/wrong

    for current_attempt in range(1, max_attempts + 1):
        print(f"\n--- Entering Round {current_attempt} / {max_attempts} ---")

        # [Phase 1] (Executor: Compile & Run)
        exec_result = compile_and_debug(filepath)
        
        if not exec_result["state"]:
            # --- Failure Handling ---
            if current_attempt < max_attempts:
                print(f"🔧 [Executor] Execution failed. Performing repair attempt #{current_attempt}...")
                code_content = error_solving(exec_result["Text"], code_content)
                # After repair, use continue to enter the next loop iteration (restart from Executor)
                continue
            else:
                print("❌ [Executor] Final test failed. No more repair attempts remaining.")
                break # Last attempt reached, break the loop

        # [Phase 2] Fuzz Stress Testing (Fuzz Tester: Runtime Logic)
        # This part is only reached if the Executor phase passes
        fuzz_result = run_fuzz_test()

        if fuzz_result["state"]:
            # --- Success ---
            print("🎉 Congratulations! The game passed all tests!")
            wrong = False
            break # All tests passed, exit loop
        else:
            # --- Failure Handling ---
            if current_attempt < max_attempts:
                print(f"🔧 [Fuzzer] Test failed. Performing logic repair attempt #{current_attempt}...")
                code_content = error_solving(fuzz_result["Text"], code_content)
                # After repair, use continue to next round (ensuring repaired code still passes Executor)
                continue
            else:
                print("❌ [Fuzzer] Final test failed. No more repair attempts remaining.")
                break

    # [Final Result Determination]
    if wrong:
        print("\n⚠️ Sorry, auto-repair attempts exhausted. Unable to debug correctly.")
        print("Please check dest/generated_app.py for manual adjustments.")

if __name__ == "__main__":
    print("🎮 AI Game Creator")
    user_request = input("Please enter the game you want to create (e.g., Snake): ")
    
    #Example for testing
    user_request = """
    Develop a 2D Top-Down Sci-Fi Space Shooter with wave survival mechanics using Pygame.

    1. Core Movement & Aiming: The player controls a spaceship using WASD for 8-way movement. The spaceship must smoothly rotate to always face the current mouse cursor position.
    2. Combat System: Clicking the left mouse button fires high-speed lasers towards the cursor. You MUST heavily utilize the 'Object Pool' design pattern to manage all laser projectiles and prevent memory leaks.
    3. Enemy Mechanics: 
    - Type A 'Asteroids': Drift slowly towards the player. When destroyed, they split into two smaller, faster asteroids.
    - Type B 'Alien Drones': Spawn periodically and actively calculate the shortest path to chase the player.
    - Spawn Logic: Enemies constantly spawn from just outside the four edges of the screen. The spawn rate increases by 10% every 15 seconds.
    4. Performance Optimization: Since there will be many projectiles and enemies, you must implement efficient collision detection (e.g., Spatial Grid concept or optimized Sprite Group collisions) to handle Laser-to-Enemy and Enemy-to-Player impacts.
    5. Game States & UI: 
    - Must implement a complete state machine: Main Menu (Start, Quit) -> Playing -> Paused (Press 'P' or 'ESC') -> Game Over.
    - HUD: Clearly display the player's current HP (starts at 3), Score, and a Survival Timer.
    6. Win/Loss Conditions: 
    - Loss: If player HP drops to 0, show the Game Over screen with the final score and a 'Restart' option.
    - Win: Survive for exactly 120 seconds. Show a 'Victory' screen with a 'Restart' option.
    """
    
    if user_request:
        generate_whole(user_request)