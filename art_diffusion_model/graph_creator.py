import os
import gc
import torch                                                                        #type:ignore
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
    """
    final_prompt = f"rpg_pixel_style, {agent_prompt}"
    final_negative_prompt = agent_negative_prompt

    print(f"🎨 Generating asset: [{item_name}] at 1024x1024...")
    
    # Use fixed seed for consistency during development
    generator = torch.Generator("cuda").manual_seed(42)
    
    try:
        image = pipe(
            prompt=final_prompt, 
            negative_prompt=final_negative_prompt, 
            width=1024, 
            height=1024, 
            num_inference_steps=30, 
            guidance_scale=7.5,
            cross_attention_kwargs={"scale": 0.75} 
        ).images[0]

        image.save(output_path)
        print(f"✨ Successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        error_msg = f"❌ Generation failed for {item_name}: {str(e)}"
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