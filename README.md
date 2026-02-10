目前約1300行

# Game_Auto_Create_System
A System that can create games from the User prompt

# Encironment setup
```
python -m pip install chromadb google-generativeai    # Install Google's vector database and AI models
python -m pip install groq

# Reference_modules contains files for RAG search (can be added/removed as needed)
# chroma_db is the vector database, generated after running build_db.py

# LoRA Environment Setup
git clone https://github.com/bmaltais/kohya_ss.git      # Clone the repository locally
cd kohya_ss                                             # Enter the directory
.\setup.bat

# If errors occur, ensure Python version is 3.10
# After installation, delete the kohya_ss/venv folder and re-run .\setup.bat
# Select option 1 in the Kohya_ss setup menu

```
# 📂 檔案結構樹 (Project Tree)
```
Project/
│
├── 📂 chroma_db/               # Vector Search Library (stores data required for RAG)
├── 📂 rag_system/              # Game Detection Zone
|   ├── __init__.py             # Python package identifier
│   └── core.py                 # Main program for searching and filtering modules
|   └── update_catalog.py       # Generates the RAG modules JSON file (catalog.json)
|   └── catalog.json            # JSON catalog file
|
├── 📂 Debug/                   # Responsible for debugging generated games
│   ├── executor.py             # Executes games and captures errors
│   └── fuzz_tester.py          # Randomly generates simulated button inputs
|   └── debug_launcher.py       # Skips game menus to enter the game directly
|   
│
├── 📂 Games/                   # Storage for generated games (all internal games are system-generated)
|
|
├── 📂 reference_modules/       # [Reference Materials] RAG reference file library
│   ├── camera_box.py           # Camera example
│   ├── camera_player_center.py # Player-centered camera example
│   ├── mouse_camera.py         # Mouse-controlled camera example
│   ├── object_pool.py          # Object pooling example
│   └── sprite_manager.py       # Sprite management example
|   └── collision.py            # Collision detection example
|   └── tile_map.py             # Map generation using DFS
│
├── 📂 test/                    # Testing zone (temporary storage)
│
├── 📄 .env                     # API Key configuration file (Confidential)
├── 📄 .gitignore               # Git ignore list
├── 📄 README.md                # Project documentation
│
├── game_creator.py             # [Main] Project entry point (Start here)
├── llm_agent.py                # [Brain] AI logic, handles design documents and code generation
├── config.py                   # [Config] Global parameter configurations
├── tools.py                    # [Tools] General utility functions
└── build_db.py                 # [Build] Script to write reference files into the vector database
```

# Future Plans
Integrate pathfinding algorithms and other common game development algorithms into the RAG system, such as Dijkstra, DFS, BFS, A*, etc.