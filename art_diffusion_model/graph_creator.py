import os
import gc
import random
import torch                                                                        #type:ignore
from rembg import remove                                                            #type:ignore
from diffusers import StableDiffusionXLPipeline, EulerAncestralDiscreteScheduler    #type:ignore

# 1. Configuration & Path Setup
BASE_MODEL_PATH = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\art_diffusion_model\Base_models\pixelArtDiffusionXL_spriteShaper.safetensors"
LORA_PATH = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\art_diffusion_model\models\pixel_v2.safetensors"
#OUTPUT_DIR = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\diffusion_model\pictures"

# 2. Initialize SDXL Pipeline
# Using from_single_file to load local .safetensors weights
print("🚀 Initializing SDXL Pipeline (1024px optimized)...")

if not os.path.exists(BASE_MODEL_PATH):
    print(f"[-] ERROR: File not found at {BASE_MODEL_PATH}")
    # Force stop to prevent vague error messages from diffusers
    raise FileNotFoundError(f"Cannot locate the model file: {BASE_MODEL_PATH}")
else:
    print(f"[+] SUCCESS: Local model file confirmed at {BASE_MODEL_PATH}")
pipe = StableDiffusionXLPipeline.from_single_file(
    BASE_MODEL_PATH, 
    torch_dtype=torch.float16, 
    use_safetensors=True
)

# Setup Scheduler (Euler A is great for stylized art)
pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
pipe.to("cuda")

# 3. Load LoRA weights
try:
    pipe.load_lora_weights(LORA_PATH)
    print("✅ SDXL LoRA weights integrated successfully.")
except Exception as e:
    print(f"❌ LoRA Loading Error: {e}")

def generate_game_asset(item_name: str, agent_prompt: str, agent_negative_prompt: str, output_path: str) -> str:
    """
    Generates a single high-quality game asset at 1024x1024.
    Applies strict spatial constraints to prevent cropped or broken images.
    """
    # Step 2: Add spatial anchoring to the positive prompt
    framing_positive = "full body, entirely in frame, perfectly centered, isolated on a pure white background"
    final_prompt = f"rpg_pixel_style, {framing_positive}, {agent_prompt}"
    
    # Step 3: Add explicit cropping prevention to the negative prompt
    framing_negative = "cropped, out of frame, cut off, partial, close up, touching the edge, borders"
    final_negative_prompt = f"{framing_negative}, {agent_negative_prompt}"

    print(f"[SYSTEM] Generating asset: [{item_name}] at 1024x1024...")
    
    # Step 1: Use a dynamic seed to avoid getting stuck in a bad latent space, and initialize the generator
    current_seed = random.randint(0, 2147483647)
    generator = torch.Generator("cuda").manual_seed(current_seed)
    print(f"[SYSTEM] Using dynamic seed: {current_seed}")
    
    try:
        image = pipe(
            prompt=final_prompt, 
            negative_prompt=final_negative_prompt, 
            width=1024, 
            height=1024, 
            num_inference_steps=30, 
            guidance_scale=7.5,
            generator=generator,  # FIX: Explicitly pass the generator to the pipeline
            cross_attention_kwargs={"scale": 0.75} 
        ).images[0]

        if item_name.startswith("[sprite]"):
            # Step 4: Enable alpha matting to prevent aggressive foreground destruction during background removal
            image = remove(image, alpha_matting=True, alpha_matting_erode_size=5, post_process_mask=True)

        image.save(output_path)
        print(f"[SUCCESS] Asset successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        error_msg = f"[ERROR] Generation failed for {item_name}. Reason: {str(e)}"
        print(error_msg)
        return ""
def generate_game_assets(asset_list: list, dest_folder: str = "dest/assets"):
    """
    Processes a list of asset requests and generates images sequentially.
    """
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
        print(f"📁 Created directory: {dest_folder}")

    print(f"🚀 Batch generation started for {len(asset_list)} assets.")

    for asset in asset_list:
        filename = asset.get('filename', 'unknown.png')
        pos_prompt = asset.get('pos_prompt', '')
        neg_prompt = asset.get('neg_prompt', '')
        
        # Define output full path
        target_path = os.path.join(dest_folder, filename)
        
        # Execute single generation
        generate_game_asset(filename.split('.')[0], pos_prompt, neg_prompt, target_path)
        
        # CRITICAL: Clear VRAM cache after each generation for SDXL stability
        torch.cuda.empty_cache()
        gc.collect()

    print("✅ All planned assets have been generated.")