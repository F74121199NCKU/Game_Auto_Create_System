目前約1300行

# 🎮 Auto Game Create System (AI Game Creator)

## 📖 Project Overview
The **Auto Game Create System** is an advanced Automated Software Engineering (ASE) tool designed to generate fully playable 2D games from simple text prompts. Inspired by the ChatDev multi-agent framework, this project simulates a virtual game development company where multiple AI agents collaborate to design, code, review, and dynamically test Pygame applications.

## 🚀 Key Technologies Used

This project integrates several cutting-edge AI and software engineering methodologies:

* **Large Language Models (LLM)**: Powered by Google's Gemini SDK (`gemini-3.0-flash` and `gemini-2.5-flash`), utilized for complex reasoning, code generation, and logical debugging.
* **Multi-Agent Collaboration**: Implements specialized AI roles (Planner, Architect, Reviewer, Programmer, Tester) communicating via a "Chat Chain" to reduce coding hallucinations and improve code quality.
* **RAG (Retrieval-Augmented Generation)**: Utilizes ChromaDB to fetch optimized, pre-written Pygame components (e.g., Object Pools, Collision systems) to ground the LLM's generation in reliable architectures.
* **Automated Fuzz Testing (Chaos Engineering)**: Injects a background thread to simulate extreme player inputs (random clicks and keystrokes) to stress-test the generated games for stability.
* **Dynamic Error Solving**: Captures Python Tracebacks during runtime and feeds them back into a Tester-Programmer feedback loop for autonomous bug fixing.

## Environment setup
```Bash
python -m pip install chromadb google-generativeai    # Install Google's vector database and AI models
python -m pip install groq
```
Reference_modules contains files for RAG search (can be added/removed as needed)
chroma_db is the vector database, generated after running build_db.py

### LoRA Environment Setup
1. git clone https://github.com/bmaltais/kohya_ss.git      # Clone the repository locally
2. cd kohya_ss                                             # Enter the directory
3. .\setup.bat

If errors occur, ensure Python version is 3.10
After installation, delete the kohya_ss/venv folder and re-run .\setup.bat

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
7. How to open the kohya_ss website
    1. Enter .\gui.bat in the terminal
    2. Find the line written " Running on local URL:  http://127.0.0.1:7860", the http is the website

### 🎨 Pre-requisite: Download the LoRA Model
Because the Stable Diffusion LoRA model is too large for GitHub, you need to download it manually:
1. Download the `pixel people.safetensors` model from [Here](Put_Your_Google_Drive_Link_Here).
2. Place the model into the folder and remember to change the code in the image_generator.py

## 📂 Core Modules and File Structure

Below is a brief introduction to the key files that power the system:

### 1. Main Entry
* `game_creator.py`: The orchestrator of the entire pipeline. It takes the user's prompt, initiates the generation process, and manages the execution-repair loop until the game passes all stress tests.

### 2. LLM Multi-Agent System (`core/`)
* `llm_agent.py`: Contains the core Multi-Agent logic. It defines the personas for the game development team and handles the multi-turn "Code Review" communication between the Reviewer and the Programmer to ensure architectural integrity.
* `tools.py`: Provides helper functions for cleaning Markdown tags from LLM outputs and saving the generated code to local `.py` files.

### 3. RAG System (`rag_system/`)
* `core.py`: Manages vector embeddings and the ChromaDB vector database. It dynamically selects and retrieves the most relevant technical modules based on the user's game request.
* `update_catalog.py`: A utility script to parse metadata from reference modules and update the JSON catalog for the RAG system.

### 4. Dynamic Testing & Debugging (`Debug/`)
* `executor.py`: Compiles and runs the generated code. It includes the "System Testing" dialogue chain where the Tester agent analyzes crash tracebacks and the Programmer agent fixes them.
* `fuzz_tester.py`: The Chaos Agent. It wraps the generated game in a safe, automated testing environment, sending random keyboard and mouse events to ensure the game doesn't crash under pressure.
* `debug_launcher.py`: A clever wrapper that inherits the generated `Game` class and forces it to bypass UI menus, allowing automated tests to jump directly into the gameplay loop.

### 5. Configuration
* `config.py`: The centralized configuration hub. It stores API keys, assigns specific LLM models to different tasks (e.g., `MODEL_SMART` vs. `MODEL_FAST`), and contains the injected payload for fuzz testing.

# Future Plans
