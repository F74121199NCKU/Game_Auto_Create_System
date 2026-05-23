import os
import ast
import sys
import json

# 確保能引用到 llm_agent (假設此腳本放在 Project/core/ 下)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
FILE_PATH = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\dest\generated_app.py"

import ast

import ast

def abstract_program(source_code: str) -> str:
    """
    Parses Python code and generates a structural skeleton.
    Enhanced to deeply extract instance attributes declared inside __init__.
    """
    try:
        tree = ast.parse(source_code)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node)
                extracted_attributes = []
                
                # Dig deeper into __init__ to find dynamically declared attributes
                if node.name == "__init__":
                    for child in ast.walk(node):
                        if isinstance(child, ast.Assign):
                            for target in child.targets:
                                # Check if the pattern matches `self.something = ...`
                                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                                    if target.value.id == "self":
                                        extracted_attributes.append(target.attr)
                
                # Clear the function body for skeletonization
                node.body = []
                
                # Restore the docstring if it exists
                if docstring:
                    node.body.append(ast.Expr(value=ast.Constant(value=docstring)))
                    
                # Inject the discovered attributes back into the skeleton as visual hints
                if extracted_attributes:
                    # Remove duplicates while maintaining order
                    unique_attrs = list(dict.fromkeys(extracted_attributes))
                    for attr in unique_attrs:
                        # Create a mock string hint so LLM knows this attribute exists
                        hint_str = f"self.{attr} = [Extracted by AST]"
                        mock_assignment = ast.Expr(value=ast.Constant(value=hint_str))
                        node.body.append(mock_assignment)
                        
                # Ensure the function isn't entirely empty to prevent SyntaxError
                if not node.body:
                    node.body.append(ast.Pass())
                    
            elif isinstance(node, ast.ClassDef):
                if not node.body:
                    node.body.append(ast.Pass())

        return ast.unparse(tree)
        
    except SyntaxError as e:
        print(f"[ERROR] AST Parser Syntax Error: {e}")
        return f"# [Syntax Error in extracting skeleton]\n{source_code}"
    except Exception as e:
        print(f"[ERROR] AST Parser Unexpected Error: {e}")
        return source_code
    

def test_abstract():
    with open(FILE_PATH, "r", encoding = 'utf-8') as f:
        src_code = f.read()
    skeleton = abstract_program(src_code)
    print(skeleton)

def run_fuzz_test(target_path_arg = None):
    """
    Executes Fuzzer test and returns a dictionary compatible with game_creator format.
    Returns:
        dict: {"state": bool, "Text": str}
    """

    # 1. Path resolution
    base_dir    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    debug_dir   = os.path.join(base_dir, "Debug")
    dest_dir    = os.path.join(base_dir, "dest")
    
    # Smart target selection: Priority given to debug_launcher
    launcher_path = os.path.join(debug_dir, "debug_launcher.py")
    target_script = ""

    if os.path.exists(launcher_path):
        target_script = launcher_path
    elif target_path_arg and os.path.exists(target_path_arg):
        target_script = target_path_arg
    else:
        target_script = os.path.join(dest_dir, "generated_app.py")

    print(f"🎯 Fuzzer Target Script: {target_script}")

if __name__ == "__main__":
    test_abstract()
    #run_fuzz_test()
