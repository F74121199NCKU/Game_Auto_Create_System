import sys
import subprocess
import os
import time
from google.genai import types                      #type:ignore

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
            capture_output = True,
            text = True,
            cwd = folder,
            timeout = 10,               # Testing duration
            encoding = 'utf-8', 
            errors = 'ignore'           # Ignore undecodable characters
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
def error_solving(error_msg: str, breaking_file: str, skeleton: str, max_turns: int = 1) -> None:
    """
    Implements the dynamic testing phase.
    A Tester reports the bug by analyzing the crash and project skeletons.
    A Programmer fixes it through a dialogue chain.
    """
    if not os.path.exists(breaking_file):
        print(f"❌ [Error Solving] Fatal Error: The specified file '{breaking_file}' does not exist.")
        return

    filename = os.path.basename(breaking_file)
    with open(breaking_file, "r", encoding='utf-8') as f:
        current_code = f.read()
    
    print(f"🐞 [Chat Chain] Starting Multi-Agent Dynamic Debugging for {filename}...")

    for turn in range(max_turns):
        print(f"🔄 Debugging Turn {turn + 1}")

        # ---------------------------------------------------------
        # 1. Tester Agent (Instructor) analyzes the crash
        # ---------------------------------------------------------
        tester_prompt = f"""
        You are a Senior Software Test Engineer (QA).
        Analyze the following Python Traceback error against the source code of `{filename}`.
        You must also cross-reference the `[PROJECT API SKELETONS]` to see if the error is caused by incorrect function calls, missing parameters, or mismatched interfaces across files.

        【COMMON PYGAME PITFALLS TO CHECK】
        1. Rect Tuple Error: `rect.center` is a tuple. It DOES NOT have `.x` or `.y`. Must suggest using `rect.centerx` or `rect.centery`.
        2. Transparency Error: AI often wrongly uses `set_colorkey`. If transparency is an issue, suggest using `.convert_alpha()`.
        3. State Machine Args: `fsm.change()` should NOT receive extra keyword arguments like `return_to_state`.
        4. Missing Groups: If an entity is retrieved from an ObjectPool, check if it was properly added to a Pygame sprite group.

        【YOUR TASK】
        DO NOT WRITE THE FULL REPAIRED CODE. Just provide the diagnosis and an actionable step-by-step fix plan for `{filename}`.
        CRITICAL INSTRUCTION: You MUST fix the ROOT CAUSE of the issue. 
        Do NOT simply add 'try...except' blocks, 'if obj is None: raise Error', or other defensive mechanisms to bypass the error. 
        If the issue is a naming mismatch, fix the string. If it's a missing parameter, add the parameter.

        【Traceback Error】
        {error_msg}

        【Current Source Code of {filename}】
        {current_code}

        【PROJECT API SKELETONS (READ-ONLY)】
        {skeleton}
        """
        
        tester_feedback = safe_generate_content(
            model_id=MODEL_SMART,
            contents=tester_prompt,
            config=types.GenerateContentConfig(safety_settings=safety_settings)
        ).text.strip()
        
        print(f"🎯 Tester Diagnosis:\n{tester_feedback}")


        # ---------------------------------------------------------
        # 2. Programmer Agent (Assistant) fixes the code
        # ---------------------------------------------------------
        programmer_prompt = f"""
        You are a Senior Python Programmer / Runtime Exception Specialist.
        You just received a bug report and action plan from the Tester regarding `{filename}`.

        【Tester Diagnosis】
        {tester_feedback}

        【Current Source Code of {filename}】
        {current_code}

        【PROJECT API SKELETONS (READ-ONLY)】
        Review these skeletons to ensure you are calling functions and initializing classes correctly according to what actually exists in other files.
        {skeleton}

        【CRITICAL RULES】
        1. Fix the bug in `{filename}` EXACTLY based on the Tester's diagnosis.
        2. DO NOT remove existing Object-Oriented structure or test hooks.
        3. Defensive Pygame: NEVER use `rect.center.x` or `rect.center.y`. Always use `rect.centerx` or `rect.centery`.
        4. Ensure your imports and class usage match the `[PROJECT API SKELETONS]`.
        5. Output format: Return the complete, fixed Python code wrapped in a SINGLE ```python markdown block.
        6. DO NOT add any conversational text, pleasantries, or explanations outside the code block.
        """

        programmer_response = safe_generate_content(
            model_id = MODEL_SMART,
            contents = programmer_prompt,
            config = types.GenerateContentConfig(safety_settings = safety_settings)
        ).text
        
        current_code = clean_code(programmer_response)
        
        # We do 1 turn of precise Q&A per error_solving call
        break 

    # Overwrite and save the repaired file
    with open(breaking_file, "w", encoding='utf-8') as f:
        f.write(current_code)
        
    print(f"✅ Code for {filename} has been updated and saved!")