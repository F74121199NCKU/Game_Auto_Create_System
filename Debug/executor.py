import sys
import subprocess
import os
import time
from google.genai import types      #type: ignore

# Import modules
# Ensure Project.toolbox.config contains the 'client' object we defined earlier
from toolbox.config import client, MODEL_SMART, safety_settings
from toolbox.tools import code_to_py, clean_code, safe_generate_content

# Game execution and preliminary debugging (Runtime Check)
def compile_and_debug(full_path: str) -> dict:
    folder = os.path.dirname(full_path)      
    filename = os.path.basename(full_path) 
    print(f" Executing and debugging {filename} in folder {folder} ...")

    try:
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            cwd=folder,
            timeout=10,               # Testing duration
            encoding='utf-8', 
            errors='ignore'           # Ignore undecodable characters
        )
        if result.returncode == 0:
            print("Game execution finished (Unusual - Main loop should normally be interrupted by timeout)")
            return {
                "state": True,
                "Text": None
            }
        else:
            print("Execution failed. Error occurred!")
            return {
                "state": False,
                "Text": result.stderr
            }
    except subprocess.TimeoutExpired:
        # For a game, a timeout is usually good as it means the main loop is running.
        print("Game continues running (Stable)")
        return {
                "state": True,
                "Text": None
        }
    except Exception as e:
        print(f"System error occurred: {e}")  
        return {
            "state": False,
            "Text": str(e)
        }

# Multi-Agent Error Solving
def error_solving(error_msg: str, code_content: str, max_turns: int = 1) -> str:
    """
    Implements the dynamic testing phase from ChatDev.
    A Tester reports the bug, and a Programmer fixes it through a dialogue chain.
    """
    current_code = code_content
    
    print("🐞 [Chat Chain] Starting Multi-Agent Dynamic Debugging...")

    for turn in range(max_turns):
        print(f"🔄 Debugging Turn {turn + 1}")

        # 1. Tester Agent (Instructor) analyzes the crash
        tester_prompt = (
            "You are a Senior Software Test Engineer."
            "Analyze the following Python Traceback error against the source code.\n"
            "Identify the EXACT line and cause of the crash. Give specific instructions on how to fix it.\n"
            "DO NOT WRITE THE FULL REPAIRED CODE. Just provide the diagnosis and action plan."
            f"\n\n【Traceback Error】\n{error_msg}\n\n【Current Source Code】\n{current_code}"
        )
        
        tester_feedback = safe_generate_content(
            model_id = MODEL_SMART,
            contents = tester_prompt,
            config = types.GenerateContentConfig(safety_settings = safety_settings)
        ).text.strip()
        
        print(f"🎯 Tester Diagnosis:\n{tester_feedback}")
        print("⏳ Waiting for API cooldown (15 seconds)...")
        time.sleep(15)


        # 2. Programmer Agent (Assistant) fixes the code
        programmer_prompt = (
            "You are a Python Runtime Exception Specialist (Programmer)."
            "You just received a bug report and action plan from the Tester.\n"
            f"【Tester Diagnosis】\n{tester_feedback}\n\n"
            f"【Current Source Code】\n{current_code}\n\n"
            "【CRITICAL RULES】\n"
            "1. Fix the bug based on the Tester's diagnosis.\n"
            "2. DO NOT remove existing Object-Oriented structure or automated test hooks (`self.game_active`).\n"
            "3. Output ONLY the fixed complete Python code without markdown tags or explanations."
        )

        programmer_response = safe_generate_content(
            model_id = MODEL_SMART,
            contents=programmer_prompt,
            config=types.GenerateContentConfig(safety_settings=safety_settings)
        ).text
        
        current_code = clean_code(programmer_response)
        
        # In a more advanced version, we could re-run the code here to check if it's fixed.
        # But for now, we rely on the external game_creator.py loop to test the new code.
        break # We do 1 turn of precise Q&A per error_solving call to fit your existing game_creator loop

    # Overwrite and save the repaired file
    code_to_py(current_code) 
    return current_code