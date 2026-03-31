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
    #user_request = input("Please enter the game you want to create (e.g., Snake): ")
    
    #Example for testing
    user_request = """
    Create a 2D Pixel Art Survival Arena game using Pygame.

    【Visual & Asset Requirements】
    The game MUST use generated image assets for the following entities:
    1. Player: "A pixel art brave hero standing, RPG style"
    2. Enemy: "A pixel art creepy zombie monster"
    3. Collectible: "A pixel art shiny gold coin"
    (Note: The Art Director should generate these assets, and the Architect MUST load them and apply `.set_colorkey((255, 255, 255))` to remove the white background.)

    【Core Gameplay Mechanics】
    1. Movement: The player controls the hero using WASD keys to move around the screen.
    2. Auto-Attack: The player automatically shoots a magical energy ball towards the nearest enemy every 1.5 seconds.
    3. Enemy AI: Zombies spawn from random edges of the 800x600 screen every 2 seconds. They constantly calculate the vector to move directly towards the player.
    4. Scoring System: When an energy ball hits a zombie, the zombie is destroyed and drops a gold coin. Collecting the coin adds 10 points to the score.
    5. Health System: The player starts with 3 HP. If a zombie collides with the player, the player takes damage, gets a brief 1-second invulnerability, and the zombie is destroyed.

    【Game States & Technical Rules】
    1. State Machine: Must have a "Main Menu" (Press SPACE to start) -> "Playing" -> "Game Over" (Shows final score, Press R to restart).
    2. Optimization: Use Pygame `pygame.sprite.Group` for all collision detections (Player vs Enemy, Projectile vs Enemy, Player vs Coin).
    """

    user_request = input("Please enter the game you want to create (e.g., Snake): ")

    if user_request:
        generate_whole(user_request)