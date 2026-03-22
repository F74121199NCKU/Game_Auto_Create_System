# update_catalog.py
import os
import json
import re

MODULES_DIR = "reference_modules"
CATALOG_FILE = "rag_system/catalog.json"

def extract_metadata(filepath):
    """
    Reads a Python file and extracts tags and docstrings (module descriptions).
    """
    metadata = {
        "filename": os.path.basename(filepath),
        "tags": [],
        "description": "No description"
    }
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
        # 1. Extract tags (e.g., # tags: camera, scroll)
        tag_match = re.search(r"#\s*tags:\s*(.*)", content, re.IGNORECASE)
        if tag_match:
            tags_str = tag_match.group(1)
            metadata["tags"] = [t.strip() for t in tags_str.split(",")]
            
        # 2. Extract Docstring (The """...""" block at the beginning of the file)
        # Using a simple regex to capture the first triple-quoted block
        doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if doc_match:
            # Remove redundant whitespace and newlines
            desc = doc_match.group(1).strip()
            metadata["description"] = " ".join(desc.split())
            
    return metadata

def main():
    if not os.path.exists(MODULES_DIR):
        print(f"❌ Directory not found: {MODULES_DIR}")
        return

    catalog = []
    print(f"📂 Scanning {MODULES_DIR} ...")

    for f in os.listdir(MODULES_DIR):
        if f.endswith(".py") and f != "__init__.py":
            path = os.path.join(MODULES_DIR, f)
            meta = extract_metadata(path)
            catalog.append(meta)
            print(f"   -> Indexed: {f} ({len(meta['tags'])} tags)")

    # Save as a JSON file
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Catalog update complete! Saved to {CATALOG_FILE}")
    print("💡 Remember to run this script every time you add a new module.")

if __name__ == "__main__":
    main()