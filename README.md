目前約1300行

# Game_Auto_Create_System
A System that can create games from the User prompt

# 環境建置
```
python -m pip install chromadb google-generativeai    #下載google的向量資料庫及其AI model
python -m pip install groq
Reference_modules裡存放的是給RAG搜索的檔案 可自行增加、刪減
chroma_db是向量庫 執行build_db.py後就能夠產生了
```
# 📂 檔案結構樹 (Project Tree)
```
Project/
│
├── 📂 chroma_db/              # 向量搜尋庫 (儲存 RAG 所需的數據)
├── 📂 rag_system/             # 偵測遊戲區
|   ├── __init__.py            # Python 套件識別檔
│   └── core.py                # 負責搜尋與篩選模組的主要程式
|   └── update_catalog.py      # 生成RAG modules的JSON格式檔(catalog.json)
|   └── catalog.json           # JSON格式檔
|
├── 📂 Debug/                   # 負責對生成出來的遊戲debug
│   ├──  executor.py             # 負責執行遊戲與捕捉錯誤
│   └──  fuzz_tester.py          # 隨機生成模擬按鈕
|   └──  debug_launcher.py       # 跳過遊戲選單直接進入遊戲
|   
│
├── 📂 Games/                       # 放置生產出來的遊戲(內部遊戲皆為系統所產生)
|
|
├── 📂 reference_modules/           # [參考資料] RAG 的參考檔案庫
│   ├── camera_box.py               # 攝影機範例
│   ├── camera_player_center.py     # 玩家中央鏡頭
│   ├── mouse_camera.py             # 滑鼠控制鏡頭
│   ├── object_pool.py              # 物件池範例
│   └── sprite_manager.py           # 物件管理範例
|   └── collision.py                # 碰撞範例
│
├── 📂 test/                   # 測試區 (目前暫存)
│
├── 📄 .env                    # API Key 設定檔 (機密)
├── 📄 .gitignore              # Git 忽略清單
├── 📄 README.md               # 專案說明文件
│
├──  game_creator.py         # [主程式] 專案入口點 (由此啟動)
├──  llm_agent.py            # [大腦] 負責 AI 思考、生成企劃與程式碼
├──  config.py               # [設定] 全域參數配置
├──  tools.py                # [工具] 通用的小工具函式
└──  build_db.py             # [建置] 將參考檔案寫入資料庫的腳本
```

# 未來計畫
將計算路徑的演算法以及其他遊戲常見的演算法加入RAG中，例如dijkstra DFS BFS A*等等