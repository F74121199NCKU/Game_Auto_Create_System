# toolbox/image_generator.py
import os
import torch                                        # type: ignore
from diffusers import StableDiffusionPipeline       # type: ignore
from PIL import Image                               # type: ignore

# Global pipeline instance to avoid reloading the model multiple times
_sd_pipe = None

def init_sd_pipeline():
    global _sd_pipe
    if _sd_pipe is not None:
        return _sd_pipe
        
    lora_path = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\diffusion_model\models\rpg_pixel_style.safetensors"
    base_model_id = "runwayml/stable-diffusion-v1-5"

    print("🎨 [Asset Generator] Loading Stable Diffusion Base Model...")
    _sd_pipe = StableDiffusionPipeline.from_pretrained(
        base_model_id, 
        torch_dtype=torch.float16,
        safety_checker=None,            
        requires_safety_checker=False   
    ).to("cuda")

    print(f"🧩 [Asset Generator] Loading LoRA weights: {lora_path}")
    try:
        _sd_pipe.load_lora_weights(lora_path)
        print("✅ [Asset Generator] LoRA loaded successfully!")
    except Exception as e:
        print(f"❌ [Asset Generator] Failed to load LoRA: {e}")
        
    return _sd_pipe

def generate_game_assets(asset_requests: list, dest_folder: str = "dest/assets"):
    """
    asset_requests format: 
    [
        {"filename": "player.png", "prompt": "a pixel art cute girl...", "size": (64, 64)},
        {"filename": "enemy.png", "prompt": "a pixel art slime...", "size": (64, 64)}
    ]
    """
    pipe = init_sd_pipeline()
    os.makedirs(dest_folder, exist_ok=True)
    
    # Base negative prompt for pixel art / game sprites
    base_negative_prompt = "blurry, realistic, 3d, worst quality, ugly, complex background, text, watermark"

    generated_files = []

    for idx, asset in enumerate(asset_requests):
        print(f"🖌️ [Asset Generator] Drawing {asset['filename']}...")
        
        # We enforce a white/simple background in the prompt to make it easier for Pygame to handle transparency later
        final_prompt = f"{asset['prompt']}, simple white background, isolated"
        
        generator = torch.Generator("cuda").manual_seed(42 + idx)
        
        # SD standard size is 512x512
        image = pipe(
            final_prompt, 
            negative_prompt=base_negative_prompt, 
            width=512, 
            height=512, 
            num_inference_steps=25, 
            guidance_scale=7.5,      
            generator=generator
        ).images[0]

        # Resize for game usage
        target_size = asset.get('size', (64, 64))
        resized_image = image.resize(target_size, Image.Resampling.LANCZOS)

        filepath = os.path.join(dest_folder, asset['filename'])
        resized_image.save(filepath)
        generated_files.append(filepath)
        print(f"✅ [Asset Generator] Saved asset to {filepath}")
        
    return generated_files