import re
import os
import sys
import json
from google import genai
from toolbox.config import *                                        # Includes API_KEY, Models, Safety Settings
from google.genai import types                                      #type: ignore
from rag_system.core import get_rag_context
from art_diffusion_model.graph_creator import generate_game_assets
from toolbox.tools import clean_code, code_to_py, get_clean_json, safe_generate_content, abstract_program

client = genai.Client(api_key=API_KEY)

#Analyze the stderr to select which file is the breaking point
def detective(error: str, filepaths: list[str]) -> str:
    """
    Analyze the traceback to identify the single file that truly needs modification.
    Return the absolute path of the file that needs repair.
    """
    print("\n🔍 [Detective] Analyzing the traceback to find the root cause...")

    # catch all the file in the error
    mentioned_filenames = list(set(re.findall(r'File ".*?([^\\/]+\.py)"', error)))
    
    suspect_filepaths = []
    for fp in filepaths:
        if os.path.basename(fp) in mentioned_filenames:
            suspect_filepaths.append(fp)

    if not suspect_filepaths:
        print("⚠️ [Detective] No local file was found in the traceback; the default check is main.py")
        return filepaths[-1]
    elif len(suspect_filepaths) == 1:
        print(f"🎯 [Detective] With only a single suspect, the case can be directly identified: {os.path.basename(suspect_filepaths[0])}")
        return suspect_filepaths[0]

    suspects_context = ""
    for suspect_path in suspect_filepaths:
        filename = os.path.basename(suspect_path)
        with open(suspect_path, "r", encoding="utf-8") as f:
            suspects_context += f"\n--- [SUSPECT CODE: {filename}] ---\n```python\n{f.read()}\n```\n"

    detective_prompt = f"""
    You are an Expert Python Error Router.
    A Pygame application crashed. The traceback involves multiple files.
    Your ONLY task is to analyze the Traceback and the suspect source code to determine WHICH FILE is the root cause of the crash.
    DO NOT provide any fix instructions.

    [Traceback Error]
    {error}

    [Suspect Source Code]
    {suspects_context}

    [Output Format]
    Respond with a JSON object ONLY. 
    Format: {{"reason": "briefly explain why this file is the origin of the error", "culprit_filename": "the_name_of_the_file_to_fix.py"}}
    """

    try:
        response = safe_generate_content(
            model_id = MODEL_NORMAL,
            contents = detective_prompt,
            config = types.GenerateContentConfig(safety_settings = safety_settings, response_mime_type = "application/json")
        )
        
        result = json.loads(response.text)
        culprit_name = result.get("culprit_filename")
        
        print(f"🎯 [Detective] Diagnosis: {culprit_name} needs repair. Reason:{result.get('reason')}")
        
        for fp in filepaths:
            if os.path.basename(fp) == culprit_name:
                return fp
                
    except Exception as e:
        print(f"⚠️ [Detective] Analysis failed: {e}. Preset to return the last suspect.")
        return suspect_filepaths[-1]

#Breaking down the whole big file into multiple small files
def generate_project_roadmap(design_doc: str) -> dict:
    print("📐 [Software Architect] The project proposal is being broken down into a multi-file development blueprint. (JSON Roadmap)...")
    output_path = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\core\test_roadmap.json"

    architect_prompt = f"""
    You are an Expert Pygame Software Architect.
    Your task is to break down the provided Game Design Document into a sequential multi-file development roadmap.

    [ROADMAP DESIGN RULES]
    1. Modularity & Decoupling: Break the project into logical Python files. Merge highly coupled utility modules (e.g., FSM, Pool, Base Classes) to maintain a roadmap of 4-9 stages for optimal AI generation efficiency.
    2. Filenames: Use standard snake_case for Python filenames (e.g., `game_entities.py`).
    3. STRICT EXECUTION ORDER (CRITICAL): 
    - Foundation (Config, Constants) MUST be Step 1.
    - Core Engine & Base Classes MUST come next.
    - ALL Concrete Entities (Player, Enemies, Items, Projectiles) MUST be generated BEFORE any Managers. 
    - Managers (Collision, Dungeon Spawning, Event Logic) can ONLY be generated AFTER all entities exist, so they can safely import them.
    - High-level UI and Main Game Loop MUST be the final steps.
    
    [REQUIRED OUTPUT FORMAT - CRITICAL]
    - Your output MUST be a single JSON OBJECT (dictionary) at the root. 
    - NEVER output a JSON Array (list) at the root level.
    - The object MUST contain the key "total_stages" (int) and "stages" (list of objects).

    [EXACT JSON SCHEMA]
    {{
    "total_stages": 3,
    "stages": [
        {{
        "step": 1,
        "file_name": "game_config.py",
        "task_description": "Define game configurations, constants, and the AssetManager."
        }},
        {{
        "step": 2,
        "file_name": "game_entities.py",
        "task_description": "Define character and object classes."
        }}
    ]
    }}

    [GAME DESIGN DOCUMENT]
    {design_doc}
    """

    response = safe_generate_content(
        model_id = MODEL_SMART, 
        contents = architect_prompt,
        config = types.GenerateContentConfig(safety_settings = safety_settings)
    )
    
    try:
        clean_json_str = get_clean_json(response.text)
        roadmap = json.loads(clean_json_str)
        
        if isinstance(roadmap, list):
            roadmap = {
                "total_stages": len(roadmap),
                "stages": roadmap
            }

        print(f"✅ [Software Architect] Blueprint planning successful！There are {roadmap.get('total_stages')} small files。")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(roadmap, f, ensure_ascii = False, indent = 4)
        print(f"\n💾 Roadmap has been stored into {output_path}")
        return roadmap
    
    except Exception as e:
        print(f"❌ [Software Architect] Blueprint planning fail: {e}")
        return None
    
# Multi-turn communication
def multi_agent_code_review(initial_code: str, design_doc: str, max_turns: int = 1) -> str:
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
            "\n14. **Asset Key Strictness**: Verify the `AssetManager` configuration dictionary and every call to `get_image(key)`. The `key` MUST strictly be the `name` attribute from the JSON document (e.g., `UI_Background_Menu`). If the code uses a parsed filename (e.g., `menu_bg_dungeon`) as a key, you MUST reject the code and output: 'INVALID ASSET KEY: You must use the exact name attribute from the JSON file as the key."

            "\n\n【Output Protocol】"
            "\n- If the code passes ALL checks, output: 'PERFECT'."
            "\n- Otherwise, list the Top 3 CRITICAL bugs only. Be concise. DO NOT write code."

            f"\n\nDesign Document:\n{design_doc}"
            f"\n\nCode:\n{current_code}"
        )
        
        reviewer_feedback = safe_generate_content(
            model_id = MODEL_NORMAL,
            contents = reviewer_prompt,
            config = types.GenerateContentConfig(safety_settings=safety_settings)
        ).text.strip()

        if "PERFECT" in reviewer_feedback:
            print("✅ Reviewer approved the code. Consensus reached!")
            break 
            
        print(f"⚠️ Reviewer found issues:\n{reviewer_feedback}")

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
            model_id = MODEL_NORMAL,
            contents = programmer_prompt,
            config = types.GenerateContentConfig(safety_settings = safety_settings)
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
            contents = f"{system_instruction}\n\nUser Original Input: {user_prompt}",
            config = types.GenerateContentConfig(safety_settings=safety_settings)
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
        config = types.GenerateContentConfig(safety_settings=safety_settings)
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
                fallback_name = asset.get('name', asset.get('image', 'unknown_asset.png'))
                asset['filename'] = fallback_name.replace("[sprite] ", "[sprite]").replace("[background] ", "[background]")
                
        print(f"✅ [Art Director] Successfully planned {len(asset_list)} assets.")
        return asset_list

    except Exception as e:
        print(f"❌ [Art Director] Failed to parse asset JSON: {e}")
        # Return an empty list to avoid crashing the main workflow
        return []

# Game code generation  
def generate_py(user_prompt: str):
    # Retrieve code from database (RAG step)
    rag_context = get_rag_context(user_prompt)
    
    # Game Technical Planner
    system_instruction_planner = (
        "You are a Senior Technical Architect. Your goal is to produce a **DENSE technical specification**."
        "You must implement all game mechanics exactly as described in the instruction manual, and write down a rough outline of how to implement them (in English)."
        "Avoid introductory filler. Go straight to technical facts."

        "\n\n### 1. MANDATORY MENU SYSTEM (STRICT)"
        "\n- **Startup Menu**: MUST implement EXACTLY 3 buttons: 「GAME START」, 「RULES」, 「QUIT」."
        "\n- **Pause Menu (P/ESC)**: MUST implement EXACTLY 4 buttons: 「CONTINUE」, 「RESTART」, 「BACK TO MAIN MENU」, 「RULES」."

        "\n\n### 2. ASSET TAXONOMY & MAPPING (CRITICAL)"
        "\n- **Classification**: [background] is strictly for map/floor/wall tiles. [sprite] is for ALL other assets (Entities, UI, Buttons) to allow background removal."
        "\n- **Naming convention**: Filenames MUST match `[category]name.png` EXACTLY. NO leading/trailing spaces (e.g., `[sprite]player.png`)."
        "\n- **Naming Style**: All asset keys and variable names MUST explicitly use lowercase snake_case (e.g., 'ui_healthbar', not 'UI_HealthBar'). Maintain strict consistency across all modules."

        "\n\n### 3. TECHNICAL ARCHITECTURE"
        "\n- **RAG Integration**: Explicitly state which modules (ObjectPool, SpatialGrid) handle which logic."
        "\n- **JSON Properties**: Define constants for Speed, HP, and Cooldown using UPPER_SNAKE_CASE."
        "\n  For every entity in the entities list that acts as an environment or obstacle, you MUST explicitly define a COLLISION_TYPE inside its properties dictionary."
        "\n- COLLISION_TYPE: solid (Use for ground, walls, blocks. Solid on all 4 sides)."
        "\n- COLLISION_TYP: \"one_way\" (Use for floating platforms, scaffolds, branches. Player can jump up through it from below)."
        "\n- Example:"
        "\n  properties {" 
        "\n    \"IMAGE_SCALE\": 1.0,"
        "\n    \"COLLISION_TYPE\": \"one_way\" "
        "\n}"

        "\n\n### 4. GAMEPLAY LOGIC & PHYSICS DATA"
        "\n- **Win/Loss Conditions**: Define clear logic (e.g., `enemy_count == 0` for level clear, `player_hp == 0` for game over)."
        "\n- **Physics Properties (CRITICAL)**: DO NOT write implementation details about hitboxes. Instead, you MUST define the physical role of environment entities in the JSON using `COLLISION_TYPE`."
        "\n  - Use `'COLLISION_TYPE': 'solid'` for ground/walls."
        "\n  - Use `'COLLISION_TYPE': 'one_way'` for jump-through platforms."
        "\n  -Sprite Group Management: You MUST define distinct Pygame Sprite Groups for `player_projectiles` and `enemy_projectiles` and ensure they are updated and drawn every frame."
        "\nMove X axis -> Check X collisions against Solid objects -> Snap to edge if collided."
        "\nMove Y axis -> Check Y collisions against Solid objects -> Snap to edge if collided."

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
        contents = f"{system_instruction_planner}\n\nUser Requirements: {user_prompt}",
        config = types.GenerateContentConfig(safety_settings = safety_settings)
    )
    print("✅ Design document generated.")
    folder = "dest"
    doc_filename = "game_design_document.txt"
    os.makedirs(folder, exist_ok=True)
    doc_path = os.path.join(folder, doc_filename)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(response_planner.text)

    json_matches = re.findall(r'```json\n(.*?)\n```', response_planner.text, re.DOTALL)
    
    if json_matches:
        #find the longest one(may have shorter example in document)
        json_content = max(json_matches, key=len)
        
        json_path = os.path.join(folder, "game_config.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        print("✅ Successfully extracted and stored the longest game_config.json")
    else:
        print("⚠️ Warning! Extract JSON file failed.")

    # Art Director & Asset Generator
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

    #Roadmap
    roadmap = generate_project_roadmap(response_planner.text)
    filepaths = []
    skeleton = str()
    Accumulated_database = str()
    total_stages = roadmap['total_stages']
    base_path = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\dest"
    for i in range(total_stages):
        file_name = roadmap["stages"][i]['file_name']
        stage_prompt = roadmap['stages'][i]["task_description"]
        print(f"This is the {i + 1}/{total_stages}stages")

        system_stages_prompt = f"""
        You are an Expert Python Game Developer working on a multi-file Pygame project.
        Your task is to write the COMPLETE and RUNNABLE code for EXACTLY ONE file: `{file_name}`.

        =======================================================
        [ZERO TOLERANCE ANTI-ERROR DIRECTIVES]
        Below are the [API SKELETONS] of the files ALREADY generated.
        This is your ABSOLUTE SOURCE OF TRUTH.
        
        1. NO NameError: Import required classes strictly from the files shown below.
        2. NO AttributeError: DO NOT access attributes or call methods on external classes UNLESS they are explicitly defined in these skeletons.

        [PREVIOUS API SKELETONS]
        {Accumulated_database}
        =======================================================
        
        [FUZZER TESTING HOOK]

        If your target file is `main.py`, you MUST implement the following Fuzzer hook precisely inside the `run(self)` method, BEFORE the `while self.is_running:` loop. 
        CRITICAL ORDER: You MUST call `self._setup_new_game()` BEFORE calling `target_fsm.change()`.
        Example implementation:
        ```python
        target_fsm = self.ui_manager.fsm if hasattr(self, 'ui_manager') else getattr(self, 'fsm', None)
        if target_fsm and getattr(target_fsm, 'current_state', None) is None:
            raw_state = os.environ.get("FUZZER_START_STATE", "MAIN_MENU").upper()
            # Setup game entities FIRST if entering an active game state
            if raw_state in ["PLAYING", "PAUSED", "GAME_OVER", "VICTORY"]:
                if not getattr(self, 'entity_manager', None):
                    self._setup_new_game()

            # Change FSM state LAST
            print(f"[SYSTEM] Forcing initial state to: {{raw_state}}")
            target_fsm.change(raw_state)

        ```
        (If your target file is NOT `main.py`, completely ignore this hook.)

        =======================================================
        [YOUR MISSION]
        Task for this file: {stage_prompt}
        Align perfectly with the Global Game Specifications: {response_planner.text}

        # [THE PYGAME IMPLEMENTATION COMMANDMENTS]
        You MUST strictly follow these rules if they apply to your file.

        [CORE SYSTEM & INITIALIZATION]
        1. INITIALIZATION SEQUENCE: `Game.__init__` MUST execute in this exact order: 
           1) `pygame.init()`
           2) Initialize `GameConfig` and load `game_config.json` inside it.
           3) `pygame.display.set_mode()`
           4) `asset_manager.load_assets()`.
        
        2. ZERO-ARGUMENT INIT: `Game.__init__(self)` MUST NOT require any external arguments.

        3. NO GLOBAL EXCEPTION SWALLOWING: 
           - DO NOT wrap any function, method, or class instantiation in a broad `try...except Exception` block.
           - If an error occurs, the game MUST crash naturally and print the full Python traceback so external fuzzing tools can detect the failure.

        [ASSET MANAGEMENT & PATH RULES]
        4. STRICT ASSET LOADING (CRITICAL):
           - AVAILABLE ASSETS: {available_assets_str}
           - DICTIONARY KEY MAPPING: You MUST build the `AssetManager` dictionary using the EXACT `name` attribute from the JSON configuration as the `key`. DO NOT use parsed filenames or invented strings. 
             * Example: If JSON defines {{"name": "UI_Background", "image": "[bg]menu.png"}}, strictly call `self.asset_manager.get_image('UI_Background')`.
           - IMAGE PROCESSING & AUTO-CROP SAFETY: ALWAYS use `pygame.image.load(path).convert_alpha()`. NO `set_colorkey()`. 
             * When cropping transparent borders, you MUST check if the bounding rect is valid before cropping to prevent crashes: 
               `bbox = image.get_bounding_rect()`
               `if bbox.width > 0 and bbox.height > 0: image = image.subsurface(bbox).copy()`
           - NO STRING SPLITTING FOR FILENAMES: You MUST use the exact image filename provided in the configuration. DO NOT parse, split, or modify the strings (e.g., NEVER use `filename.split(']')`). If a filename in JSON is `[sprite]player.png`, search for exactly `[sprite]player.png`.
           - DIRECTORY STRUCTURE (NO DOUBLE DIRNAME): The execution script and the 'assets' folder share the EXACT SAME root. You MUST use `os.path.dirname(os.path.abspath(__file__))` ONLY ONCE to get the current directory, and directly join it with 'assets'.
             * CORRECT Example: 
               `base_dir = os.path.dirname(os.path.abspath(__file__))`
               `image_path = os.path.join(base_dir, 'assets', filename)`

        [GAMEPLAY LOGIC & PHYSICS]
        5. STRICT DATA SAFETY & ENTITY MAPPING (CRITICAL):
           - EXACT JSON MAPPING: When creating mapping dictionaries (e.g., mapping strings to classes in `EntityManager`), the dictionary keys MUST strictly match the exact `name` strings defined in the JSON configuration (e.g., `'BasicMeleeEnemy'`). DO NOT invent shorthand keys like `'melee'`.
           - SAFE DICTIONARY ACCESS: You MUST NEVER use direct dictionary/list indexing (e.g., `data['entities'][0]`) to fetch game data.
             * Use `config.get_entity('Exact_Name') or {{}}` to fetch entity data safely.
             * Use `config.get_prop('Exact_Name', 'PROPERTY_KEY', default_value)` to fetch properties.
           - PYGAME RECT ATTRIBUTES: NEVER use invalid tuple-property chaining like `rect.center.x`. You MUST use Pygame's built-in single attributes (e.g., `rect.centerx`).
           - COMPREHENSIVE UTILIZATION: Ensure ALL entities defined in JSON are instantiated and utilized in collision/update loops.

        6. JUICY PHYSICS & ANTI-PHASING (CRITICAL):
           - Axis Separation is MANDATORY: Move X -> Check X Collision -> Move Y -> Check Y Collision. Do NOT move both axes before checking.
           - Snap to Edge: When a collision with a `solid` object is detected, snap the character's hitbox precisely to the edge.
           - NO DOUBLE MOVEMENT: Do NOT call `self.move(dt)` inside the `update(self, dt)` method of any Character (Player/Enemies). Positional updates MUST be handled exclusively by the `CollisionManager` to ensure physics stability.
           - Hitboxes: Shrink the hitbox for `Player`/`Enemy` (`self.rect.inflate(-self.rect.width * 0.2, -self.rect.height * 0.2)`). DO NOT shrink environment hitboxes.
           - Anchor Point: Align sprites by bottom edge: `self.rect.midbottom = self.hitbox.midbottom`.

        7. LEVEL PROGRESSION MECHANIC (PORTAL/DOORS): 
           - When all enemies are defeated, the Game loop MUST explicitly iterate through the `doors` sprite group and call `door.open()`.
           - It MUST constantly check if the player's hitbox collides with an `is_open == True` door. If they collide, call `self._setup_new_game()` to transition to the next level. Open doors MUST NOT block player movement in the collision manager.

        [UI, SPRITES & FSM]
        8. SPRITE INITIALIZATION & GROUPS (ANTI-RECURSION ERROR):
           - NO STRINGS IN GROUPS (CRITICAL): NEVER pass strings or non-Group objects into Pygame's `*groups` arguments or `super().__init__(*groups)`. Passing a string (like `'gold'`) will cause Pygame to unpack the string recursively and trigger an infinite `RecursionError`. You MUST ONLY pass actual `pygame.sprite.Group` instances.
           - OBJECT POOLING: When initializing entities inside an `ObjectPool`, ensure you do not pass trailing strings as group arguments. When fetching an entity from a pool, IMMEDIATELY add it to the correct Pygame sprite groups.
           - INITIALIZATION ORDER: Initialize the image FIRST, then call `super().__init__(initial_image, ...)`.

        9. UI RENDERING:
           - AI UI images are BLANK. Render text using `pygame.font.Font` and blit it perfectly centered on the button's rect in the `draw()` method.

        10. OBJECT POOLING & SPRITE INITIALIZATION:
            - When fetching an entity from a pool, IMMEDIATELY add it to the Pygame sprite groups.
            - NEVER pass `None` to `super().__init__` if the entity has an image. Initialize the image FIRST, then call `super().__init__(initial_image, ...)`.
        =======================================================
        [OUTPUT FORMAT]
        1. Output a <THINKING> block first. List the mechanics and VERIFY that any external method you call exists in the SKELETONS.
        2. Output ONLY valid Python code wrapped in a single ```python block. Starts with `import pygame`.
        3. ALL comments must be in English.
        """

        stage_designer = safe_generate_content(
            model_id = MODEL_SMART,
            contents = f"{system_stages_prompt}\nDesign Document: {response_planner.text}",
            config = types.GenerateContentConfig(safety_settings = safety_settings)
        )
        final_code = clean_code(stage_designer.text)
        game_path = os.path.join(base_path, file_name)
        with open(game_path, "w", encoding = 'utf-8') as f:
            f.write(final_code)
        filepaths.append(game_path)
        skeleton = abstract_program(final_code)
        Accumulated_database += f"\n# ====== API SKELETON: {file_name} ======\n{skeleton}\n"

    print("✅ Code generation complete.")

    #如果有需要再開啟reviewer
    #code_content = multi_agent_code_review(code_content, response_planner.text)
    print("✅ Code debugging complete.")

    return filepaths, Accumulated_database