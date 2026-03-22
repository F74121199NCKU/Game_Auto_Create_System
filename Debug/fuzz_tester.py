import subprocess
import sys
import os
import threading
import signal
from toolbox.config import CHAOS_PAYLOAD

def run_fuzz_test(target_path_arg=None):
    """
    Executes Fuzzer test and returns a dictionary compatible with game_creator format.
    Returns:
        dict: {"state": bool, "Text": str}
    """

    # 1. Path resolution
    base_dir    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    debug_dir   = os.path.join(base_dir, "Debug")
    dest_dir    = os.path.join(base_dir, "dest")
    
    # Smart target selection: Priority given to debug_launcher
    launcher_path = os.path.join(debug_dir, "debug_launcher.py")
    target_script = ""

    if os.path.exists(launcher_path):
        target_script = launcher_path
    elif target_path_arg and os.path.exists(target_path_arg):
        target_script = target_path_arg
    else:
        target_script = os.path.join(dest_dir, "generated_app.py")

    print(f"🎯 Fuzzer Target Script: {target_script}")

    if not os.path.exists(target_script):
        return {"state": False, "Text": f"Fuzzer Error: Target file {target_script} not found"}

    # 2. Prepare Injection Wrapper
    wrapper_script_path = os.path.join(base_dir, "temp_fuzz_wrapper.py")
    try:
        with open(target_script, "r", encoding="utf-8-sig", errors="replace") as f:
            original_code = f.read()
        injected_code = f"{CHAOS_PAYLOAD}\n\n# --- ORIGINAL GAME CODE ---\n{original_code}"
        with open(wrapper_script_path, "w", encoding="utf-8") as f:
            f.write(injected_code)
    except Exception as e:
        return {"state": False, "Text": f"Fuzzer Error: Failed to write temporary file - {e}"}

    # 3. Execute Test
    print(f"🚀 Launching Fuzzer... (Wrapper: {wrapper_script_path})")
    
    process = None
    try:
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [sys.executable, wrapper_script_path],
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # Critical: Must capture stderr for Tracebacks
            text=True,
            encoding='utf-8',
            errors='replace',
            env=my_env
        )

        try:
            # Capture output (Captures all errors printed by debug_launcher)
            stdout, stderr = process.communicate(timeout=20)
            
            stdout = stdout if stdout else ""
            stderr = stderr if stderr else ""

            # --- Evaluation ---
            if "[FUZZ] SUCCESS" in stdout:
                print("✅ Fuzzer: Test Passed")
                return {"state": True, "Text": "Test Passed"}
            
            else:
                print(f"❌ Fuzzer: Test Failed (Return Code: {process.returncode})")
                
                # Compose error message for error_solving function
                # Priority given to stderr (Python Tracebacks), fallback to stdout trailing logs
                error_content = ""
                if stderr.strip():
                    error_content = stderr
                else:
                    error_content = stdout[-1000:] # Capture last 1000 characters
                
                # Manual fallback if content is empty
                if not error_content.strip():
                    error_content = "Unknown Error: Program crashed without capturing error messages (Silent Crash)."

                return {"state": False, "Text": error_content}

        except subprocess.TimeoutExpired:
            print("\n✅ Fuzzer: Test duration ended, game survived (Considered Passed)")
            try:
                process.kill()
            except:
                pass
            return {"state": True, "Text": "Test Passed (Game Survived Duration)"}

    except Exception as e:
        print(f"❌ Fuzzer: Execution Exception")
        return {"state": False, "Text": f"Fuzzer Internal Error: {e}"}
        
    finally:
        if os.path.exists(wrapper_script_path):
            try:
                os.remove(wrapper_script_path)
            except: pass

if __name__ == "__main__":
    # For standalone testing
    result = run_fuzz_test()
    print(f"Result: {result}")
    if result["state"]:
        sys.exit(0)
    else:
        sys.exit(1)