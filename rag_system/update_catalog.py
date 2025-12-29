# update_catalog.py
import os
import json
import re

MODULES_DIR = "reference_modules"
CATALOG_FILE = "rag_system/catalog.json"

def extract_metadata(filepath):
    """
    讀取 Python 檔案，提取 tags 和 docstring (模組說明)。
    """
    metadata = {
        "filename": os.path.basename(filepath),
        "tags": [],
        "description": "無描述"
    }
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
        # 1. 抓取 tags (例如 # tags: camera, scroll)
        tag_match = re.search(r"#\s*tags:\s*(.*)", content, re.IGNORECASE)
        if tag_match:
            tags_str = tag_match.group(1)
            metadata["tags"] = [t.strip() for t in tags_str.split(",")]
            
        # 2. 抓取 Docstring (檔案開頭的 """...""")
        # 這裡使用簡單的正則抓取第一個三引號區塊
        doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if doc_match:
            # 去除多餘空白與換行
            desc = doc_match.group(1).strip()
            metadata["description"] = " ".join(desc.split())
            
    return metadata

def main():
    if not os.path.exists(MODULES_DIR):
        print(f"❌ 找不到目錄: {MODULES_DIR}")
        return

    catalog = []
    print(f"📂 正在掃描 {MODULES_DIR} ...")

    for f in os.listdir(MODULES_DIR):
        if f.endswith(".py") and f != "__init__.py":
            path = os.path.join(MODULES_DIR, f)
            meta = extract_metadata(path)
            catalog.append(meta)
            print(f"   -> 已索引: {f} ({len(meta['tags'])} tags)")

    # 存成 JSON 檔案
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 型錄更新完成！已儲存至 {CATALOG_FILE}")
    print("💡 請記得在每次新增模組後執行此腳本。")

if __name__ == "__main__":
    main()