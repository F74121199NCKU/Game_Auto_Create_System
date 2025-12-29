python -m pip install chromadb google-generativeai    #下載google的向量資料庫及其AI model
python -m pip install groq
Reference_modules裡存放的是給RAG搜索的檔案 可自行增加、刪減
chroma_db是向量庫 執行build_db.py後就能夠產生了

# 📂 檔案結構樹 (Project Tree)
Project/
│
├── 📂 __pycache__/            # [快取] Python 自動產生的編譯檔 (提升載入速度)
│
├── 📂 chroma_db/              # [資料庫] 向量搜尋庫 (Vector Database)
│                              # 儲存 RAG 系統所需的嵌入向量 (Embeddings)
│
├── 📂 rag_system/             # [核心套件] RAG (檢索增強生成) 核心邏輯
│   ├── __init__.py            #    └─ 宣告此資料夾為 Python Package
│   └── core.py                #    └─ 負責查詢 ChromaDB 與篩選模組的主要邏輯
│
├── 📂 reference_modules/      # [知識庫] RAG 的參考檔案 (Reference Code)
│   ├── camera_box.py          #    └─ 攝影機運鏡模組
│   ├── object_pool.py         #    └─ 物件池優化模組
│   ├── sprite_manager.py      #    └─ 精靈管理模組
│   └── ... (其他遊戲設計模式範例)
│
├── 📂 test/                   # [測試] 存放測試用的腳本或暫存檔
│
├── 📄 .env                    # [機密] 環境變數設定 (如 API Keys，不應上傳至 Git)
├── 📄 .gitignore              # [Git] 設定 Git 版本控制應忽略的檔案
├── 📄 README.md               # [文件] 專案說明文件
│
├── 📄 build_db.py             # [工具] 資料庫建置腳本
│                              # 用於讀取 reference_modules 並將其向量化寫入 chroma_db
│
├── 📄 config.py               # [設定] 全域配置檔
│                              # 包含 API Key 輸入、模型版本選擇、安全閾值設定
│
├── 📄 executor.py             # [執行器] 專案的「手腳」
│                              # 負責 subprocess 執行遊戲、捕捉錯誤 (Stderr) 與驗證執行結果
│
├── 📄 game_creator.py         # [主程式] 專案入口點 (Entry Point)
│                              # 作為指揮官，協調 Agent、Executor 與 RAG 系統運作
│
├── 📄 llm_agent.py            # [生成器] 專案的「大腦」
│                              # 包含 企劃師、工程師、審查員 等 AI 角色的 Prompt 邏輯
│
└── 📄 utils.py                # [工具] 通用輔助函式庫
                               # 包含字串清理 (clean_code)、檔案存檔 (code_to_py) 等功能