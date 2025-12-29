python -m pip install chromadb google-generativeai    #下載google的向量資料庫及其AI model
python -m pip install groq
Reference_modules裡存放的是給RAG搜索的檔案 可自行增加、刪減
chroma_db是向量庫 執行build_db.py後就能夠產生了

# 📂 檔案結構樹 (Project Tree)
```
Project/
│
├── 📂 __pycache__/            # 存放 Python 編譯後的快取檔 (系統自動生成)
├── 📂 chroma_db/              # 向量搜尋庫 (儲存 RAG 所需的數據)
│
├── 📂 rag_system/             # [核心邏輯] RAG 檢索系統 (我寫的)
│   ├── __init__.py            # Python 套件識別檔
│   └── core.py                # 負責搜尋與篩選模組的主要程式
│
├── 📂 reference_modules/      # [參考資料] RAG 的參考檔案庫
│   ├── camera_box.py          # 攝影機範例
│   ├── camera_player_center.py
│   ├── camera_y_sorted.py
│   ├── object_pool.py         # 物件池範例
│   └── sprite_manager.py      # 精靈管理範例
│
├── 📂 test/                   # 測試區 (目前暫存)
│
├── 📄 .env                    # API Key 設定檔 (機密)
├── 📄 .gitignore              # Git 忽略清單
├── 📄 README.md               # 專案說明文件
│
├── 🐍 game_creator.py         # [主程式] 專案入口點 (由此啟動)
├── 🐍 llm_agent.py            # [大腦] 負責 AI 思考、生成企劃與程式碼
├── 🐍 executor.py             # [手腳] 負責執行遊戲與捕捉錯誤
├── 🐍 config.py               # [設定] 全域參數配置
├── 🐍 utils.py                # [工具] 通用的小工具函式
└── 🐍 build_db.py             # [建置] 將參考檔案寫入資料庫的腳本
```