import sys
import os

current_script_dir = os.path.dirname(os.path.abspath(__file__))

# Strategy A: Assume I am currently in the root directory (Case when running via Fuzzer)
path_strategy_a = os.path.join(current_script_dir, "dest")

# Strategy B: Assume I am currently in the Debug subfolder (Case when running manually)
path_strategy_b = os.path.join(os.path.dirname(current_script_dir), "dest")
dest_folder_path = None

if os.path.exists(path_strategy_a):
    print(f"📍 [Path Detection] Detected running in project root directory (Fuzzer mode)")
    dest_folder_path = path_strategy_a
elif os.path.exists(path_strategy_b):
    print(f"📍 [Path Detection] Detected running in Debug subdirectory (Manual mode)")
    dest_folder_path = path_strategy_b
else:
    # --- If neither is found, print detailed debugging information ---
    print("="*40)
    print("❌ Critical Error: 'dest' folder not found!")
    print(f"   Current location: {current_script_dir}")
    print(f"   Attempted Path A: {path_strategy_a}")
    print(f"   Attempted Path B: {path_strategy_b}")
    print("="*40)
    sys.exit(1) # Return error code 1

# Add 'dest' to the system search path
if dest_folder_path not in sys.path:
    sys.path.append(dest_folder_path)

try:
    from generated_app import Game
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

class AutoStartGame(Game):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError as e:
            if "game_name" in str(e):
                super().__init__(game_name="Auto Test Game", *args, **kwargs)
            else:
                raise e 
                
        # Make sure the game initializes entities properly when entering PLAYING state
        if hasattr(self, 'needs_restart'):
            self.needs_restart = True

if __name__ == "__main__":
    game = AutoStartGame()
    
    # Injecting the PLAYING state directly into the FSM before running
    print("📍 [Debug Launcher] Injecting 'PLAYING' state to bypass menus...")
    try:
        game.fsm.change('PLAYING')
    except Exception as e:
        print(f"⚠️ Warning: Could not inject PLAYING state directly: {e}")
        
    game.run()