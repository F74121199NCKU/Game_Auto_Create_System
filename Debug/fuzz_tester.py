import os
import sys
import subprocess
import signal
import threading


current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from toolbox.config import CHAOS_PAYLOAD

# Note: Make sure CHAOS_PAYLOAD is defined somewhere globally in your system.
# CHAOS_PAYLOAD = """ ... """

def run_fuzz_test(main_file_path: str) -> dict:
    """
    Executes Fuzzer test by injecting a chaos payload into the main script.
    Returns:
        dict: {"state": bool, "Text": str}
    """
    
    #  Fail-fast path resolution & Environment setup
    assert os.path.exists(main_file_path), f"[Fuzzer Error] Target main script is missing: {main_file_path}"
    
    dest_dir = os.path.dirname(main_file_path)
    print(f"🎯 [Fuzzer] Target Script: {main_file_path}")

    my_env = os.environ.copy()
    my_env["PYTHONIOENCODING"] = "utf-8"
    my_env["PYTHONUNBUFFERED"] = "1"
    my_env["FUZZER_START_STATE"] = "PLAYING" 

    # Prepare Injection Wrapper in the SAME directory as main.py
    wrapper_script_path = os.path.join(dest_dir, "temp_fuzz_wrapper.py")
    
    try:
        with open(main_file_path, "r", encoding="utf-8") as f:
            original_code = f.read()
            
        injected_code = f"{CHAOS_PAYLOAD}\n\n# --- ORIGINAL GAME CODE START ---\n{original_code}"
        
        with open(wrapper_script_path, "w", encoding="utf-8") as f:
            f.write(injected_code)
            
    except Exception as e:
        return {"state": False, "Text": f"Fuzzer Error: Failed to setup wrapper - {e}"}

    print(f"🚀 [Fuzzer] Launching Chaos Test... (Wrapper: {wrapper_script_path})")
    process = None
    
    try:
        process = subprocess.Popen(
            [sys.executable, wrapper_script_path],
            cwd = dest_dir, 
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE, 
            text = True,
            encoding = 'utf-8',
            errors = 'replace',
            env = my_env
        )

        try:
            # Capture output with a timeout
            stdout, stderr = process.communicate(timeout = 15)
            stdout = stdout if stdout else ""
            stderr = stderr if stderr else ""

            # Evaluate Results
            if process.returncode == 0:
                print("✅ [Fuzzer] Test Passed (Game exited normally with Return Code 0)")
                return {"state": True, "Text": "Test Passed (Normal Exit)"}
                
            elif "[FUZZ] SUCCESS" in stdout:
                print("✅ [Fuzzer] Test Passed (Success token found)")
                return {"state": True, "Text": "Test Passed"}
                
            else:
                print(f"❌ [Fuzzer] Test Failed (Return Code: {process.returncode})")
                
                # Priority: stderr > stdout
                error_content = stderr.strip() if stderr.strip() else stdout[-1000:].strip()
                if not error_content:
                    error_content = "Unknown Error: Program crashed without capturing error messages (Silent Crash)."

                return {"state": False, "Text": error_content}

        except subprocess.TimeoutExpired:
            print("\n✅ [Fuzzer] Test duration ended, game survived without crashing.")
            process.kill()
            return {"state": True, "Text": "Test Passed (Game Survived Duration)"}

    except Exception as e:
        print(f"❌ [Fuzzer] Execution Exception")
        return {"state": False, "Text": f"Fuzzer Internal Error: {e}"}
        
    # Clean up the temporary wrapper
    finally:
        if os.path.exists(wrapper_script_path):
            try:
                os.remove(wrapper_script_path)
            except Exception as e:
                print(f"⚠️ [Fuzzer] Could not remove temp file: {e}")

if __name__ == "__main__":
    # Standalone execution logic (Ignored when imported by other modules)
    print("==================================================")
    print("[DEBUG] Running Fuzz Tester in Standalone Mode")
    print("==================================================")
    
    # Calculate path relative to this script
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    test_path = os.path.join(project_root, "dest", "main.py")

    result = run_fuzz_test(test_path)
    print(f"\n[DEBUG] Final Result Dictionary: {result}")
    
    if result["state"]:
        sys.exit(0)
    else:
        sys.exit(1)