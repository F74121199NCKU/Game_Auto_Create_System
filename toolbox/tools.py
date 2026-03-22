import os
import re

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