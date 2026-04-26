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
    I want to make a fast-paced 2D top-down shooting game in Python using pygame, just like "Soul Knight". It needs to be a flat top-down view, so there is no jumping, gravity, or high/low terrain—just characters moving around on a flat floor. 

    Please give me the COMPLETE, fully runnable Python code in a single file. Don't leave any missing parts, "pass", or "TODO" comments. I want to be able to run it immediately!

    Here is how the game should work:
    1. Stats & Combat: Characters have Health (HP), Energy (MP), Attack (ATK), and Armor (DEF). Armor works like a regenerating shield: when hit, Armor takes damage first. If the player hides and doesn't get hit for a while, the Armor slowly recharges. Damage is simply Attack minus Armor. But make sure it always does at least 1 damage, otherwise enemies will be unkillable!
    2. Controls: I use W, A, S, D to move. The player character must ALWAYS face my mouse pointer. Left-clicking shoots bullets towards the mouse. Right-clicking temporarily boosts my Armor.
    3. The Dodge Roll (Crucial!): Pressing Space makes the character roll quickly. During this roll, the character MUST be completely invincible so I can dodge straight through enemy bullets safely. Pressing Q uses a special skill that costs Energy.
    4. Enemies & Drops: There are melee monsters that run straight at me to hit me, and ranged monsters that stay back and shoot bullets at me. When they die, they drop gold coins and blue energy orbs. 
    5. Rooms: The map has different connected rooms. If I walk into a monster room, the doors lock immediately! I have to defeat every single monster to unlock the doors, and a reward chest should appear. There are also safe rooms with friendly NPCs where I can talk to them and spend my gold coins to upgrade my stats.
    6. The Boss: The last room has a huge Boss. It has a ton of HP and shoots crazy circle bullet patterns all over the place. If I kill it, show a "Victory" screen. If I die, show a "Game Over" screen.
    7. Balance: Please make sure the numbers make sense! The game should feel fair—not too easy, but I shouldn't die in one hit either. Please write clean code using good classes, with English variables and comments. Keep the game running smoothly without lagging even if there are lots of bullets!
    """

    #user_request = input("Please enter the game you want to create (e.g., Snake): ")
    if user_request:
        generate_whole(user_request)