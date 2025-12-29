python -m pip install chromadb google-generativeai    #下載google的向量資料庫及其AI model
python -m pip install groq
Reference_modules裡存放的是給RAG搜索的檔案 可自行增加、刪減
chroma_db是向量庫 執行build_db.py後就能夠產生了

# 📂 檔案結構樹 (Project Tree)
graph TD
    %% 定義樣式類別
    classDef logic fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef data fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef config fill:#e0f2f1,stroke:#004d40,stroke-width:2px;
    classDef system fill:#eeeeee,stroke:#616161,stroke-width:1px,stroke-dasharray: 5 5;

    %% 根目錄
    Root[📂 Project /]

    %% 第一層資料夾
    subgraph Folders [資料夾結構]
        direction TB
        RAG_Sys[📂 rag_system<br/>RAG 核心邏輯套件]:::logic
        Ref_Mod[📂 reference_modules<br/>RAG 參考知識庫]:::data
        Chroma[📂 chroma_db<br/>向量資料庫]:::data
        Cache[📂 __pycache__<br/>Python 編譯快取]:::system
        Test[📂 test<br/>測試腳本]:::system
    end

    %% 第一層檔案 (核心執行邏輯)
    subgraph Core [核心執行檔案]
        GameCreator(🐍 game_creator.py<br/>專案入口點 / 指揮官):::logic
        LLM_Agent(🐍 llm_agent.py<br/>AI 生成邏輯 / 大腦):::logic
        Executor(🐍 executor.py<br/>程式執行與除錯 / 手腳):::logic
    end

    %% 第一層檔案 (工具與設定)
    subgraph Utils [工具與設定]
        Config(⚙️ config.py<br/>API Key與模型設定):::config
        Utilities(🛠️ utils.py<br/>通用工具函式):::config
        BuildDB(🏗️ build_db.py<br/>資料庫建置腳本):::config
    end

    %% 第一層檔案 (文件與環境)
    subgraph Docs [文件與環境]
        Env(🔒 .env):::config
        GitIgnore(🚫 .gitignore):::config
        Readme(📄 README.md):::config
    end

    %% RAG System 內容
    RAG_Init(🐍 __init__.py):::logic
    RAG_Core(🐍 core.py<br/>檢索與篩選邏輯):::logic

    %% 參考模組內容
    Ref_Files(🐍 camera_box.py<br/>🐍 object_pool.py<br/>🐍 sprite_manager.py<br/>...):::data

    %% 連結關係
    Root --> GameCreator
    Root --> LLM_Agent
    Root --> Executor
    Root --> Config
    Root --> Utilities
    Root --> BuildDB
    Root --> Env
    Root --> GitIgnore
    Root --> Readme
    
    Root --> RAG_Sys
    Root --> Ref_Mod
    Root --> Chroma
    Root --> Cache
    Root --> Test

    %% 資料夾內部展開
    RAG_Sys --> RAG_Init
    RAG_Sys --> RAG_Core
    Ref_Mod --> Ref_Files

    %% 視覺排版優化 (隱藏線，強制層級)
    GameCreator ~~~ Config