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
1. git clone https://github.com/bmaltais/kohya_ss.git      # Clone the repository locally
2. cd kohya_ss                                             # Enter the directory
3. .\setup.bat

# If errors occur, ensure Python version is 3.10
# After installation, delete the kohya_ss/venv folder and re-run .\setup.bat
4. Select option 1 (Install kohya_ss GUI)in the Kohya_ss setup menu
5. Select option 5 (Manually configure Accelerate)in the Kohya_ss setup menu
IF the terminal stuck, press ctrl + C to end the process, then enter 7 to exit the setup.
Enter the following instruction in terminal
(1) .\venv\Scripts\activate 
(2) accelerate config

6. Hardware Acceleration Configuration
    Run accelerate config in your terminal and follow these instructions to complete the setup:

    1. In which compute environment are you running?
        Selection: This machine

    2. Which type of machine are you using?
        Selection: No distributed training

    3. Do you want to run deterministic algorithms?
        Selection: No

    4. Do you wish to optimize your script with torch dynamo?
        Selection: No

    5. Do you want to use DeepSpeed?
        Selection: No

    6. What GPU(s) (by id) should be used?
        Selection: all

    7. Would you like to enable numa efficiency? (Currently only supported on NVIDIA hardware). [yes/NO]: 
        Selection: IF your GPU is NVIDIA then yes, otherwise choose NO
    
    8. Do you wish to use FP16 or BF16 (mixed precision)?
        NVIDIA 30/40/50 Series GPUs: Please ensure you select bf16 for the best compatibility and performance.
        NVIDIA 10/20 Series GPUs: Please select fp16.
        Integrated Graphics or Older Devices: Please select no (None).

```
# 📂 Project Tree
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