import re
import sys
import os
import time
import json
import random
from google import genai
from google.genai import types                                      #type: ignore
from toolbox.config import *                                        # Includes API_KEY, Models, Safety Settings
from rag_system.core import get_rag_context
#from toolbox.image_generator import generate_game_assets
from art_diffusion_model.graph_creator import generate_game_assets
from toolbox.tools import clean_code, code_to_py, get_clean_json, safe_generate_content


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
            "You are a Strict Code Reviewer and QA Tester."
            "First, read the Design Document. Extract the CORE GAMEPLAY MECHANICS (e.g., Invulnerability, Auto-Attack, Scoring, specific collisions)."
            "Second, read the generated Python code."
            "\n\n【YOUR TASK】"
            "\n1. Do a line-by-line verification."
            "\n2. If ANY mechanic from the Design Doc is missing, reject the code and output: 'MISSING LOGIC: [Describe what is missing]'."

            "\n\n【STRICT REVIEW CHECKLIST】"
            "\n1. **Asset Integrity**: Ensure EVERY `load_image` uses EXACT filenames from the list (e.g., `[sprite]player_mage_idle.png`). NO 'Graphic/' or other prefixes allowed."
            "\n2. **Constructor Contract**: Every class inheriting from `GameSprite` MUST accept `pool=None` and call `super().__init__(pool=pool, **kwargs)`. Check for `TypeError` risks."
            "\n3. **FSM Sequence**: States MUST be added via `fsm.add()` BEFORE calling `fsm.change()`. FSM must not change state in `__init__`."
            "\n4. **Menu Compliance**: Startup Menu MUST have 3 buttons; Pause Menu MUST have 4 buttons (including 'Rules' and 'Restart')."
            "\n5. **Null Safety**: Check for math operations on potentially `None` config values. Ensure `get_prop` has numeric defaults."
            "\n6. **Spawning**: Confirm `camera.center_on_target()` is called immediately after level generation."
            "\n7. Method Consistency: Ensure that every method called in the FSM state lambdas (like ui_manager.handle_event) is actually DEFINED in the corresponding class. Check for missing delegation logic in managers."
            "\n8. JSON Target: Verify the code explicitly attempts to load game_config.json. Flag param.json as a bug."
            "\n9. Scale Implementation: Ensure pygame.transform.scale is actively used on get_image outputs based on JSON configuration. 1024px default loading without scaling is a CRITICAL BUG."
            "\n10. NoneType Defense: Check all dynamic dictionary assignments (e.g., data = lookup()). If they lack an or {} fallback before .get() is called, flag it as an AttributeError risk."
            "\n11. Spacing/Tag Bug: Check if string keys in AssetManager exactly match available_assets_str without injecting stray spaces."
            "\n12. Transparency: Ensure `set_colorkey` is NEVER used in the code. Verify that ALL image loading uses `.convert_alpha()`."
            "\n13. UI Text Dynamic Rendering: Verify that UI button classes explicitly instantiate `pygame.font.Font`, render the text string, and blit it onto the center of the button surface."

            "\n\n【Output Protocol】"
            "\n- If the code passes ALL checks, output: 'PERFECT'."
            "\n- Otherwise, list the Top 3 CRITICAL bugs only. Be concise. DO NOT write code."

            f"\n\nDesign Document:\n{design_doc}"
            f"\n\nCode:\n{current_code}"
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
            "You are a Senior Python Programmer / Refactoring Expert."
            "You must fix the code based on the Reviewer's feedback while maintaining structural integrity."

            "\n\n【ANTI-LAZINESS & IMPLEMENTATION RULE】(CRITICAL)"
            "\n- You MUST write the ACTUAL, complete logic for any missing features flagged by the Reviewer."
            "\n- DO NOT use placeholders like `pass`, `...`, or `# TODO: implement this`. If a UI panel or a timer is missing, YOU must write the Pygame rendering and update logic for it."

            "\n\n【DEFENSIVE CODING RULES】"
            "\n1. **Inheritance**: Always use `def __init__(self, ..., pool=None, **kwargs):` and pass them to super."
            "\n2. **Safe Retrieval**: Use the pattern `config.get_prop('Entity', 'Key', default_value)` to prevent NoneType math errors."
            "\n3. **Safe Iteration**: Use `groups = kwargs.get('groups') or []` for any sprite group handling."
            "\n4. **Asset Reliability**: Use `os.path.join(os.path.dirname(__file__), 'assets', filename)` for absolute path safety."
            "\n5. **State Machine**: Ensure all `fsm.add()` calls occur in `Game.__init__` before any gameplay logic starts."
            "\n6. AttributeError (Missing Methods): If a class lacks a method called by the FSM or another manager, identify the missing 'Delegation' logic (e.g., UIManager needs to pass events to Buttons)."
            "\n7. Error Fixes: If feedback mentions FileNotFoundError, rename the target file to game_config.json. If feedback mentions AttributeError or NoneType, immediately add or {} to the failing dictionary retrieval."
            "\n8. Scaling Fixes: Apply pygame.transform.scale using IMAGE_SCALE from config if the Reviewer flags oversized images."
            "\n9. Transparency Fixes: Remove any `set_colorkey` calls and chain `.convert_alpha()` right after `pygame.image.load()`."
            "\n10. Font Fixes: If buttons lack text, add `self.font = pygame.font.Font(None, 36)` and blit `self.font.render(text, True, (255,255,255))` in the draw method."

            "\n\n【Constraints】"
            "\n- DO NOT remove `self.game_active` or RAG module imports."
            "\n- DO NOT add explanatory text or markdown blocks."
            "\n- Output ONLY the complete fixed Python code."

            f"\n\n【Reviewer Feedback】\n{reviewer_feedback}"
            f"\n\n【Current Code】\n{current_code}"
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
        "You are a Senior Technical Architect. Your goal is to produce a **DENSE technical specification**."
        "Avoid introductory filler. Go straight to technical facts."

        "\n\n### 1. MANDATORY MENU SYSTEM (STRICT)"
        "\n- **Startup Menu**: MUST implement EXACTLY 3 buttons: 「GAME START」, 「RULES」, 「QUIT」."
        "\n- **Pause Menu (P/ESC)**: MUST implement EXACTLY 4 buttons: 「CONTINUE」, 「RESTART」, 「BACK TO MAIN MENU」, 「RULES」."

        "\n\n### 2. ASSET TAXONOMY & MAPPING (CRITICAL)"
        "\n- **Classification**: [background] is strictly for map/floor/wall tiles. [sprite] is for ALL other assets (Entities, UI, Buttons) to allow background removal."
        "\n- **Naming convention**: Filenames MUST match `[category]name.png` EXACTLY. NO leading/trailing spaces (e.g., `[sprite]player.png`)."

        "\n\n### 3. TECHNICAL ARCHITECTURE"
        "\n- **RAG Integration**: Explicitly state which modules (ObjectPool, SpatialGrid) handle which logic."
        "\n- **JSON Properties**: Define constants for Speed, HP, and Cooldown using UPPER_SNAKE_CASE."

        "\n\n### 4. GAMEPLAY LOGIC"
        "\n- **Win/Loss Conditions**: Define logic (e.g., `enemy_count == 0` for level clear)."
        "\n- **Hitbox Rule**: Specify hitboxes are 20% smaller than visual assets for 'Juicy' feel."

        "\n\n### 5. DYNAMIC IMAGE SCALING (MATHEMATICAL RULE)"
        "\n- **Base Resolution**: Assume ALL generated visual assets are 1024x1024 pixels."
        "\n- **IMAGE_SCALE Calculation**: You MUST logically assign a float for EVERY entity based on a 1280x720 screen."
        "\n  - Player/Enemy: ~0.08 (approx 80px)."
        "\n  - Projectiles/Items: ~0.02 (approx 20px)."
        "\n  - UI Buttons: ~0.15."
        "\n  - Backgrounds: ~1.25 (to fill screen)."

        f"\n\n【Reference Modules (RAG Context)】\n{rag_context}\n\n"

        "【Output Format: Part 1 - Technical Spec (Markdown)】"
        "\n1. Architecture Mapping: List which RAG function will be used for which feature."
        "\n2. State Logic Table: Define states (Menu, Playing, Pause, Rules, GameOver) and their specific transition triggers."
        "\n3. Asset & Entity Table: For each entity/UI element, list its EXACT filename (with `[sprite]` or `[background]`) and its numeric properties (Speed, HP, etc.). **DO NOT leave these to the programmer's imagination.**"
        "\n4. Collision Matrix: Define exactly what happens when A hits B."
        "\n5. Architecture: Use ObjectPool for projectiles and CameraScrollGroup for centering."

        "\n\n【Output Format: Part 2 - Parameters (JSON Code Block)】"
        "\n- The JSON configuration file MUST be implicitly designed for the filename `game_config.json`."
        "\n- **IMAGE_SCALE (CRITICAL)**: You MUST include this key for EVERY entity."
        "\n- **Asset Tags**: Every image MUST start with `[sprite]` or `[background]`. No extra spaces."
        "\n Follow the Schema below."
        "\n```json"
        "\n{"
        "\n  \"game_name\": \"...\", "
        "\n  \"config\": {\"FPS\": 60, \"SCREEN_SIZE\": [1280, 720]},"
        "\n  \"entities\": [ { \"name\": \"Player\", \"image\": \"[sprite]mage.png\", \"properties\": {\"IMAGE_SCALE\": 0.08} } ]"
        "\n}"
        "\n```"

        "\n\n【Core Constraints】"
        "\n- Use **Bullet Points** only. No paragraphs."
        "\n- Mandatory: Implement 'ESC' for Pause logic."
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

    json_match = re.search(r'```json\n(.*?)\n```', response_planner.text, re.DOTALL)
    if json_match:
        json_content = json_match.group(1)
        json_path = os.path.join(folder, "game_config.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        print("✅ Successfully extract and store game_config.json")
    else:
        print("⚠️ Warning! Extract JSON file failed.")

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
        "You are a Senior Pygame Architect. Your goal is to build a high-polish, robust single-file game. "
        "Output the complete Python code wrapped in a markdown code block. Do not add any explanatory text before or after the code block."
        "Before writing the code, you MUST output a <THINKING> block. Explicitly list every mechanic requested in the Design Document and state exactly which class and method will implement them."

        "\n\n### 1. INITIALIZATION SEQUENCE (CRITICAL)"
        "You MUST follow this order in `Game.__init__` to prevent 'Purple Screen' and 'NoneType' errors:"
        "\n1. `pygame.init()`."
        "\n2. **Data First**: Call a private method `self._read_json_only()` (which YOU must define) to load 'game_config.json' with `encoding='utf-8'` into `GameConfig`."
        "\n3. **Display Second**: Call `pygame.display.set_mode()` using values from the loaded config."
        "\n4. **Assets Third**: Call `asset_manager.load_assets(data)`. This ensures `.convert_alpha()` works correctly."

        "\n\n### 2. DATA SAFETY & NULL PROTECTION"
        "\n- **AttributeError Prevention**: When fetching entity data, ALWAYS use `player_data = config.get_entity('Player') or {}`. NEVER assume dictionary lookups succeed."
        "\n- **Property Guard**: Use `config.get_prop('Name', 'Key', default_value)` to ensure math operations NEVER hit `None`."
        "\n- **Zero-Argument Init**: `Game.__init__(self)` MUST NOT require arguments."
        "\n- **Pygame Rect Attributes**: NEVER use `rect.center.x` or `rect.center.y`. You MUST use `rect.centerx` or `rect.centery`. Tuples do not have .x or .y attributes in Python."
        
        "\n\n### 3. ASSET PROCESSING (GREEN SCREEN & SCALE)"
        "\n- **Alpha Transparency**: DO NOT use set_colorkey(). Since assets are pre-processed with rembg, they already have an alpha channel."
        "\n- **Loading Rule**: You MUST use `image = pygame.image.load(path).convert_alpha()` for ALL assets. This ensures perfect transparency without color collision bugs.\n"
        "\n- **Scaling**: Retrieve `IMAGE_SCALE` from JSON. Use `pygame.transform.scale()` inside the `AssetManager` or Entity `__init__`. Do not hardcode scale values.\n"

        "\n\n### 4. JUICY PHYSICS & GAME FEEL"
        "\n- **Axis Separation**: Move X -> Check X Collision -> Move Y -> Check Y Collision. Use `pygame.math.Vector2` for `self.pos`."
        "\n- **Hitboxes**: Hitboxes MUST be 20% smaller than visual sprites."

        "\n\n### 5. FSM SEQUENCE & MENUS"
        "\n- **Lazy FSM**: `FSM` MUST NOT call `self.change()` inside its `__init__`."
        "\n- **Registration First**: Use `fsm.add()` to register ALL states BEFORE calling `fsm.change()`."
        "\n- **Menu Buttons**: Startup Menu (3 buttons), Pause Menu P/ESC (4 buttons)."
        "\n- **UI Delegation**: Any UIManager MUST implement a `handle_event` that iterates and calls `handle_event()` on all active UI elements."
        "\n- **State Transition Rule**: Strict strictly use `self.fsm.change('STATE_NAME')` with NO extra keyword arguments (e.g., NO `return_to_state`)."
        "\n- **Resume Logic**: `PlayingState.enter()` MUST NOT call a full game reset (like `_setup_new_game()`). Game initialization should only happen when transitioning from MENU or RESTART."

        "\n\n### 6. ASSET MANAGEMENT & EXACT FILENAMES"
        "\n- **Exact Pathing**: Use `os.path.join(os.path.dirname(__file__), 'assets', filename)`."
        "\n- **No Prefixes**: DO NOT add 'Graphic/'. Use filenames exactly as listed."
        f"\n- **Filenames**: {available_assets_str}"
    
        "\n\n### 7.【CRITICAL UI RENDERING RULE】"
        "\n1. AI-generated images for buttons are BLANK FRAMES. They do NOT contain text."
        "\n2. YOU MUST write Python code in your UI classes to dynamically render text using `pygame.font.Font`."
        "\n3. In the `draw` method, AFTER blitting the button's image, render the text and center it perfectly (`text_rect.center = self.rect.center`)."

        "\n\n### 8. EXECUTION"
        "\nParse JSON logic -> Apply Constructor Contract -> Apply Data Safety -> Output complete Python code."
        "\n\nCRITICAL: Start your code response directly with the python markdown tag and `import pygame`. Do not say 'Here is the code'."
        "\n- When you retrieve an entity from an ObjectPool (e.g., `pool.get()`), you MUST immediately add it to its corresponding Pygame sprite groups (e.g., `self.enemies.add(alien)`). If it is not added to the groups, it will never render or update."
        
        "\n\n### 9. FSM INITIALIZATION & EXTERNAL TESTING (CRITICAL)"
        "\n- The game MUST NOT contain any test-specific variables like `game_active`."
        "\n- In `Game.run()`, DO NOT blindly hardcode `self.fsm.change('STARTUP_MENU')` before the loop."
        "\n- Instead, you MUST use Lazy Initialization. Check if a state is already set before the `while True:` loop:"
        "\n  ```python"
        "\n  if getattr(self.fsm, 'current_state', None) is None:"
        "\n      self.fsm.change('STARTUP_MENU')"
        "\n  ```"
        "\n- This allows an external test script to inject a state (like 'PLAYING') before calling `run()`."
    )
    
    # SDK Call for Architect
    response_designer = safe_generate_content(
        model_id = MODEL_SMART,
        contents=f"{system_game_designer}\n\nDesign Document: {response_planner.text}",
        config=types.GenerateContentConfig(safety_settings=safety_settings)
    )
    
    try:
        if not response_designer or not response_designer.text:
            print("❌ Code generation failed. Please try again later.")
            # 印出 API 回傳的原始物件，看看是不是被 Safety 擋住了
            print(f"🔍 [除錯資訊] API 原始回傳結果: {response_designer}")
            
            # 嘗試印出中斷原因 (Finish Reason)
            if hasattr(response_designer, 'candidates') and len(response_designer.candidates) > 0:
                print(f"🚨 中斷原因: {response_designer.candidates[0].finish_reason}")
                
            sys.exit(1)
    except Exception as e:
        print(f"❌ 讀取 API 回傳值時發生例外錯誤: {e}")
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
        "You are a Game Art Director. Plan a JSON array for SDXL assets."
        "【Prompt Rule】: Use COMMA-SEPARATED TAGS for 'pos_prompt'. Focus on visual keywords only."
        "Example: 'knight, 16-bit pixel art, silver armor, blue runes, glowing, pure white background, flat lighting'."
        "【Constraints】: No full sentences. Max 30 words per prompt. Ensure 'size' is [1024, 1024]."
        
        "\n\nCRITICAL TAXONOMY: You MUST prefix every filename EXACTLY with either [background] or [sprite]. \n"
        "- Use [background] ONLY for static map tiles, floors, and walls. DO NOT add any solid color background tags to them.\n"
        "- Use [sprite] for EVERYTHING else (including Characters, Enemies, Projectiles, UI Panels, Buttons, and Items) because they require background removal.\n"
        
        "CRITICAL CHROMA KEY RULE: For EVERY [sprite] asset, you MUST append 'isolated on a pure white background' to its 'pos_prompt'. rembg will handle the transparency conversion.\n"
        "CRITICAL FORMATTING: There MUST NOT be any leading or trailing spaces in the prefix or the filename (e.g., [sprite]button.png, NOT [sprite] button.png ).\n"
        
        "\n\nCRITICAL UI RULE: For any asset that is a button, panel, or menu (e.g., filenames containing 'button' or 'ui'), you MUST generate BLANK frames ready for text overlay.\n"
        "- Add 'blank frame, empty container, no text, no icons, centered UI element' to the 'pos_prompt'.\n"
        "- You MUST ADD 'text, letters, words, alphabet, signature, watermark, typography' to the 'neg_prompt' to strictly prevent the AI from generating gibberish text.\n"

        "\n\n【Asset Classification Rules】:\n"
        "1. [background]: Static tiles/floors. PROMPT: '16-bit pixel art texture, top-down, seamless, full frame, no borders'.\n"
        "2. [sprite]: Characters, UI, Items. PROMPT: MUST include isolated on a pure white background.\n"
        "【Naming Convention】: Use '[sprite]name.png' or '[background]name.png'. NO spaces between tag and name.\n"

        "\n\n【REQUIRED JSON SCHEMA】\n"
        "You MUST output a valid JSON array. Each object MUST contain EXACTLY these keys: 'filename', 'pos_prompt', 'neg_prompt', 'size'.\n"
        "Example:\n"
        "[\n"
        "  {\n"
        "    \"filename\": \"[sprite]player_ship.png\",\n"
        "    \"pos_prompt\": \"pixel art spaceship, silver, isolated on a pure white background, flat lighting, no shadows on floor\",\n"
        "    \"neg_prompt\": \"blurry, low quality, 3d render\",\n"
        "    \"size\": [1024, 1024]\n"
        "  }\n"
        "]\n"
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
            if 'filename' in asset:
                asset['filename'] = asset['filename'].replace("[sprite] ", "[sprite]").replace("[background] ", "[background]")
            else:
                # 如果 AI 漏寫了，給一個防呆預設值，或者嘗試抓取 'name'
                fallback_name = asset.get('name', asset.get('image', 'unknown_asset.png'))
                asset['filename'] = fallback_name.replace("[sprite] ", "[sprite]").replace("[background] ", "[background]")
                
        print(f"✅ [Art Director] Successfully planned {len(asset_list)} assets.")
        return asset_list

    except Exception as e:
        print(f"❌ [Art Director] Failed to parse asset JSON: {e}")
        # Return an empty list to avoid crashing the main workflow
        return []