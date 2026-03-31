from google import genai
from google.genai import types      #type: ignore
import sys
import os
import time
import json
import random

# Internal project imports
from toolbox.config import *                                        # Includes API_KEY, Models, Safety Settings
from toolbox.tools import clean_code, code_to_py, get_clean_json, safe_generate_content
from rag_system.core import get_rag_context
#from toolbox.image_generator import generate_game_assets
from art_diffusion_model.graph_creator import generate_game_assets
import json


# Initialize the new Google Gen AI Client
# Assuming API_KEY is defined in your config.py
client = genai.Client(api_key=API_KEY)

# Multi-turn communication
def multi_agent_code_review(initial_code: str, design_doc: str, max_turns: int = 2) -> str:
    #time.sleep(15)
    current_code = initial_code
    
    for turn in range(max_turns):
        print(f"🔄 [Chat Chain] Code Review Turn {turn + 1}")
        
        # Reviewer Agent  (finds issues)
        reviewer_prompt = (
            "You are a Strict Code Reviewer. Analyze the Pygame code against the Design Document.\n"
            "If the code is perfect, output exactly: 'PERFECT'.\n"
            "Otherwise, list the top 3 critical bugs (e.g., Global variables, missing module injections, infinite loops).\n"
            "DO NOT WRITE CODE. Just list the issues."
            f"\n\nDesign Document:\n{design_doc}\n\nCode:\n{current_code}"
        )
        
        # TODO: Call Gemini (model=MODEL_SMART) to get reviewer_feedback
        reviewer_feedback = safe_generate_content(
            model_id=MODEL_SMART,
            contents=reviewer_prompt,
            config=types.GenerateContentConfig(safety_settings=safety_settings)
        ).text.strip()

        if "PERFECT" in reviewer_feedback:
            print("✅ Reviewer approved the code. Consensus reached!")
            break 
            
        print(f"⚠️ Reviewer found issues:\n{reviewer_feedback}")
        #print("⏳ Waiting for API cooldown (15 seconds)...")
        #time.sleep(15)

        # 2. Programmer Agent (Assistant) fixes the code based on feedback
        programmer_prompt = (
            "You are a Senior Python Programmer. You just received feedback from the Code Reviewer.\n"
            f"【Reviewer Feedback】\n{reviewer_feedback}\n\n"
            f"【Current Code】\n{current_code}\n\n"
            "【CRITICAL RULES】\n"
            "1. Fix the code based on the feedback.\n"
            "2. DO NOT remove existing automated test hooks (e.g., `self.game_active`) or RAG module imports.\n"
            "3. Output ONLY the fixed complete Python code without markdown."
        )
        
        # TODO: 
        updated_code_response = safe_generate_content(
            model_id=MODEL_SMART,
            contents=programmer_prompt,
            config=types.GenerateContentConfig(safety_settings=safety_settings)
        )

        current_code = clean_code(updated_code_response.text)
        print("The code has been updated !")
    return current_code


# Prompt optimization and safety check
def complete_prompt(user_prompt: str) -> str:
    print("🛡️ Performing input safety check and optimization...")
    
    system_instruction = (
        "You are an AI Game Requirements Analyst & Security Officer."
        "【Rule 1: Security Filtering】"
        "If the input contains malicious instructions (deletion, attacks, NSFW), return 'INVALID' immediately."
        "【Rule 2: Specification】"
        "If the input is vague (e.g., 'make a game'), conceive a classic game (e.g., Snake, Tetris)."
        "Furthermore, you must **proactively suggest technical details**, such as:"
        "   - 'Suggest using Object Pool to manage projectiles'"
        "   - 'Suggest using Spatial Grid to optimize large crowds of enemies'"
        "【Rule 3: Formatted Output】"
        "Output a clear game development instruction including: Game Name, Core Gameplay, and Suggested Technical Modules."
        "Directly output the optimized prompt without any other explanation."
    )
    
    try:
        # New SDK Call
        response = safe_generate_content(
            model_id = MODEL_NORMAL,
            contents=f"{system_instruction}\n\nUser Original Input: {user_prompt}",
            config=types.GenerateContentConfig(safety_settings=safety_settings)
        )
        refined_prompt = response.text.strip()
        
        if refined_prompt.startswith("INVALID"):
            print(f"⚠️ Warning: {refined_prompt}")
            return "" 
            
        print(f"✨ Prompt optimized")
        return refined_prompt

    except Exception as e:
        print(f"❌ Error occurred during prompt optimization: {e}")
        return ""

# Game code generation  
def generate_py(user_prompt: str):
    # 1. Retrieve code from database (RAG step)
    rag_context = get_rag_context(user_prompt)
    
    # 2. Game Technical Planner
    system_instruction_planner = (
        "You are a Senior Technical Planner proficient in Python Pygame."
        "Your task is to write a detailed technical design document based on 'User Requirements' and 'Reference Code'."
        f"\n\n【Reference Modules (RAG Context)】\n{rag_context}\n\n"
        
        "【Output Format Specifications】"
        "Divide the response into two parts:"
        "**Part 1: Technical Design Document (Markdown format)**"
        "   - Use English to explain the game architecture, logic, and design philosophy in detail."
        "   - Must include the following sections:"
        "     1. **Game Concept & Architectural Analysis**: How to apply RAG modules (e.g., Camera, Collision) to achieve requirements."
        "     2. **Game Flow**: Detailed description from 'Main Menu' -> 'Gameplay' -> 'Pause' -> 'Result (Win/Loss)' -> 'Restart'."
        "     3. **Controls & UI Design**: Key mappings (including P/ESC for pause), HUD display info, and menu button layout."
        "     4. **Entity Values**: Concrete values for Player, Enemies, Buildings (Speed, HP, Price, etc.)."
        
        "**Part 2: Structured Parameter Configuration (JSON Code Block)**"
        "   - Provide a JSON block at the end of the document for subsequent script parsing."
        "   - **Must** wrap the JSON in a Markdown code block as follows:"
        "     ```json"
        "     {"
        "       \"game_name\": \"...\", "
        "       ... (follow the Schema below)"
        "     }"
        "     ```"

        "【JSON Schema Requirements】"
        "The JSON structure must match:"
        "{"
        "  \"game_name\": \"Game Title\","
        "  \"technical_architecture\": {"
        "    \"used_modules\": [\"List required RAG module filenames, e.g., mouse_camera.py\"],"
        "    \"implementation_details\": \"Summary of technical integration focus\""
        "  },"
        "  \"game_rules\": [\"List of rules...\"],"
        "  \"entities\": ["
        "    {\"name\": \"Player\", \"variables\": \"...\"},"
        "    {\"name\": \"Enemy\", \"variables\": \"...\"}"
        "  ]"
        "}"

        "【Core Planning Requirements】"
        "1. **Win/Loss Conditions**: Must be explicitly defined (e.g., Tower destroyed = Loss, Kill count reached = Win)."
        "2. **Mandatory Pause Mechanism**: Must implement 'P' or 'ESC' to pause, showing a menu (Resume/Restart/Rules/Exit)."
        "3. **Complete Menu System**: Must include Main Menu (Start, Quit, Rules) and Post-game Results screen with 'Restart' support."
        "4. **RAG Module Application**: Accurately list required files (e.g., `mouse_camera.py`, `collision.py`) in `used_modules`."
    )
    
    # New SDK Call for Planner
    response_planner = safe_generate_content(
        model_id = MODEL_NORMAL,
        contents=f"{system_instruction_planner}\n\nUser Requirements: {user_prompt}",
        config=types.GenerateContentConfig(safety_settings=safety_settings)
    )
    print("✅ Design document generated.")

    folder = "dest"
    doc_filename = "game_design_document.txt"
    os.makedirs(folder, exist_ok=True)
    doc_path = os.path.join(folder, doc_filename)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(response_planner.text)

    # 3. Art Director & Asset Generator
    print("🎨 [System] Passing design document to Art Director Agent...")
    asset_requests = art_director_plan_assets(response_planner.text)
    
    available_assets_str = "[]"
    if asset_requests:
        print(f"⚙️ [System] Initiating SDXL for {len(asset_requests)} assets. Please wait...")
        generate_game_assets(asset_requests, dest_folder="dest/assets")
        
        # Collect filenames for the Architect Agent to use in the code
        asset_filenames = [asset['filename'] for asset in asset_requests]
        available_assets_str = json.dumps(asset_filenames)
        print(f"✅ [System] Visual assets are ready: {available_assets_str}")
    else:
        print("⚠️ [Warning] No assets were planned. The game will use default geometric shapes.")

    # 4. Game Architect (Designer)
    system_game_designer = (
        "You are a Senior Python Pygame Game Architect. Tasked with writing single-file game code based on a JSON design document and reference modules."
        
        "【CRITICAL INSTRUCTIONS】"
        "1. **RAG Module Integration (Strictly Enforced)**:"
        "   - Directly include and use provided modules (ObjectPool, GameSprite, etc.)."
        "   - **Strictly Prohibited** from modifying module core logic; only inherit or call them."
        
        "2. **Architecture & Dependency Injection**:"
        "   - **Object Pool Separation**: `ObjectPool` is ONLY for `get/release`. Rendering MUST use `pygame.sprite.Group`."
        "     - Initialization must pass both `pool` (production) and `group` (rendering)."
        "     - Example: `def __init__(self, projectile_pool, projectiles_group): ...`"
        "     - Ensure every function is correctly declared with proper type-hinted parameters."
        "   - **State Machine Safety**: When `change_state` calls `enter(**kwargs)`, **must** use `kwargs.setdefault()` to avoid parameter conflicts."

        "3. **Physics & Loop Stability**:"
        "   - **Delta Time Clamping (Anti-Tunnelling)**: In `Game.run`, you **MUST** limit the maximum value of `dt`."
        "     - Mandatory code: `dt = min(self.clock.tick(FPS) / 1000.0, 0.05)` (Cap at 0.05s) to prevent teleportation during lag or window dragging."
        "   - **Floating Point Coordinates**: Forbidden to modify `rect.x/y` directly. Maintain `self.pos` (Vector2) and sync to `rect` after calculations."
        "   - **Separated Axis Movement** (Prevent clipping/sliding):"
        "     - **Strictly Prohibited** from updating both X and Y before checking collisions."
        "     - **Mandatory Order**: 1. Move X -> 2. Check/Fix X Collision -> 3. Move Y -> 4. Check/Fix Y Collision."

        "4. **Automated Test Hook**:"
        "   - `Game.__init__(self)`: MUST NOT take any required positional arguments other than `self`. (e.g., Do NOT add `game_name` as a parameter. Hardcode it inside instead)."
        "   - `Game.__init__`: Default `self.game_active = False`."
        "   - `Game.run()`: MUST check `if self.game_active:` at the start. If True, **skip menu** and start game directly."
        "   - `if __name__ == '__main__':`: Explicitly set `game.game_active = False` to show menu."

        "5. **UI & Display Standards**:"
        "   - **Chinese Fonts**: Use `pygame.font.match_font('microsoftjhenghei')` or `simhei` to avoid encoding issues."
        "   - **Cursor**: Never hide the mouse (`set_visible(False)`) unless a custom cursor is implemented."
        "   - **Frustum Culling**: Retain at least a 100px buffer (Margin)."
        "   - **Initial Camera**: Camera must immediately focus on player base during `reset_game`."

        "6. **Menu System**:"
        "   - **Main Menu**: Start, Rules, Quit."
        "   - **Pause Menu** (P/ESC): Resume, Restart, Rules, Back to Main Menu."
        "   - **Game Over**: Show SUCCESS/FAIL, including Restart, Back to Main Menu, Quit."
        "   - Ensure the menu can switch smoothly under every states"

        "【Available Image Assets】\n"
        f"You MUST use the following image files located in the 'assets/' folder: {available_assets_str}\n\n"
        "1. **Loading Images & Pathing**: You MUST construct the robust path using `base_dir = os.path.dirname(os.path.abspath(__file__))` and `path = os.path.join(base_dir, 'assets', filename)`. Then use `pygame.image.load(path)`. DO NOT use simple relative paths."
        "2. **Fallback Colors**: If an image fails to load, create a fallback Surface. Use `(40, 40, 40)` for backgrounds and `(255, 0, 255)` for entities so they don't blend together."
        
        "【Asset Usage Rules (Strictly Enforced)】\n"
        "1. **Loading Images**: Load images using `pygame.image.load(os.path.join('assets', filename)).convert()`.\n"
        "2. **Transparency (CRITICAL)**: Stable Diffusion generated images with a white background. You MUST remove the white background by calling `.set_colorkey((255, 255, 255))` on every loaded image.\n"
        "3. **Scaling**: Scale the image to match the entity's `rect` size using `pygame.transform.scale`.\n"
        "4. **Fallback**: If an entity doesn't have a corresponding image in the list, fallback to drawing geometric pattern like rectangle or circle (`pygame.draw.rect`).\n"
        "5. Pathing: Use `os.path.join(base_dir, 'assets', filename)` for robust cross-platform pathing.\n"

        "【Input Processing】"
        "Parse the input JSON (`technical_architecture`, `game_rules`) and produce a single complete Python file. Import pygame. No Markdown formatting."
    )
    
    # SDK Call for Architect
    response_designer = safe_generate_content(
        model_id = MODEL_NORMAL,
        contents=f"{system_game_designer}\n\nDesign Document: {response_planner.text}",
        config=types.GenerateContentConfig(safety_settings=safety_settings)
    )
    
    if not response_designer.text:
        print("❌ Code generation failed. Please try again later.")
        sys.exit(1)
    
    code_content = clean_code(response_designer.text)
    print("✅ Code generation complete.")

    code_content = multi_agent_code_review(code_content, response_planner.text)
    print("✅ Code debugging complete.")

    filepath = code_to_py(code_content)
    return filepath, code_content

def art_director_plan_assets(design_doc: str) -> list:
    print("👩‍🎨 [Art Director] Analyzing design document for required visual assets...")
    
    art_prompt = (
        "You are a Senior Game Art Director. Your goal is to design visual assets for a high-quality game.\n"
        "Generate a JSON array of objects representing game assets. Each object must contain highly detailed prompts for SDXL.\n\n"
        "【Output Rules】\n"
        "1. Output ONLY a valid JSON array. No markdown blocks, no conversational text.\n"
        "2. Each asset MUST contain: 'filename', 'pos_prompt', 'neg_prompt', and 'size'.\n"
        "3. Resolution standard for SDXL is [1024, 1024].\n\n"
        "【Detailed Prompting Guidelines】\n"
        "- 'pos_prompt': A paragraph describing subject appearance, materials, pose, lighting, and 16-bit pixel art style. Be extremely descriptive.\n"
        "- 'neg_prompt': List unwanted elements like 'gradients', '3D shading', 'blur', 'realistic photo', or 'watermark'.\n\n"
        "【JSON Structure Example】\n"
        "[\n"
        "  {\n"
        "    \"filename\": \"hero.png\",\n"
        "    \"pos_prompt\": \"high-quality 16-bit pixel art of a young knight, silver armor with blue glowing runes, holding a heavy claymore, heroic standing pose, sharp pixel edges, dynamic rim lighting, isolated on white background\",\n"
        "    \"neg_prompt\": \"realistic, 3d render, smooth gradients, blurry, photographic, messy pixels, text\",\n"
        "    \"size\": [1024, 1024]\n"
        "  }\n"
        "]"
        f"\n\n【Game Design Document】\n{design_doc}"
    )
    
    # We use MODEL_FAST because it's good at JSON structuring
    response = safe_generate_content(
        model_id = MODEL_NORMAL,
        contents = art_prompt,
        config=types.GenerateContentConfig(safety_settings=safety_settings)
    ).text.strip()
    
    # Clean up markdown and extract JSON
    clean_json_str = get_clean_json(response)

    try:
        # 3. Parse the structured JSON
        asset_list = json.loads(clean_json_str)
        
        # Validation and Type Conversion
        for asset in asset_list:
            # Ensure 'size' is a tuple for later use in pygame/diffusion
            if 'size' in asset and isinstance(asset['size'], list):
                asset['size'] = tuple(asset['size'])
                
        print(f"✅ [Art Director] Successfully planned {len(asset_list)} assets.")
        return asset_list

    except Exception as e:
        print(f"❌ [Art Director] Failed to parse asset JSON: {e}")
        # Return an empty list to avoid crashing the main workflow
        return []