import os
import re
import time
import random
from google import genai
from google.genai import types      #type: ignore
from toolbox.config import *

# Save string content to a .py file
def code_to_py(code, filename = "generated_app.py", folder = "dest"):
    """
    Saves the provided code string into a Python file within the specified directory.
    """
    os.makedirs(folder, exist_ok = True)
    file_path = os.path.join(folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
        
    print(f"? File saved to: {file_path}")
    return file_path 

# Clean redundant Markdown formatting from LLM response
def clean_code(raw_text: str) -> str:
    """
    Removes Markdown code block syntax (e.g., ```python ... ```) 
    to extract the raw Python code.
    """
    clean_text = re.sub(r'^```python\s*', '', raw_text)   
    clean_text = re.sub(r'^```\s*', '', clean_text)       
    clean_text = re.sub(r'```$', '', clean_text)          
    return clean_text.strip()

def get_clean_json(raw_text: str) -> str:
    """
    Highly robust function to extract JSON array from LLM response.
    It combines Markdown parsing and raw bracket extraction.
    """
    # Try 1: Look for Markdown JSON block
    json_match = re.search(r'```json\s*(.*?)\s*```', raw_text, re.DOTALL)
    content = json_match.group(1).strip() if json_match else raw_text.strip()

    # Try 2: Final safety net - Extract everything from the first '[' to the last ']'
    start_idx = content.find('[')
    end_idx = content.rfind(']')
    
    if start_idx != -1 and end_idx != -1:
        return content[start_idx:end_idx + 1]
    
    return content


client = genai.Client(api_key=API_KEY)
#To avoid high demand of requesting and occur 503 error
def safe_generate_content(model_id, contents, config=None):
    """
    Call Gemini API with exponential backoff to handle 503/429 errors.
    """
    max_retries = 5
    base_delay = 10  # Initial wait time in seconds
    
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model_id,
                contents=contents,
                config=config
            )
        except Exception as e:
            # Check if error is related to server busy (503) or rate limit (429)
            if "503" in str(e) or "429" in str(e):
                # Calculate delay: base_delay * 2^attempt + random jitter
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 5)
                print(f"⚠️ Server overloaded (503). Retrying in {wait_time:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                # If it's a different error, re-raise it
                print(f"❌ Critical API Error: {e}")
                raise e
                
    raise Exception("❌ Max retries exceeded. Google server is still unavailable.")