輸入以下指令以下載資料包: pip install -r requirements.txt
輸入pip install fastapi uvicorn inngest llama-index-core llama-index-readers-file python-dotenv qdrant-client streamlit google-generativeai llama-index-llms-gemini llama-index-embeddings-gemini 以下載環境及API
uv run uvicorn setting:app                                                      # host
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery  # server
docker run -d --name qdrant(**could be modified**) -p 6333:6333 -v "$(pwd)/qdrant_storage:/qdrant//st"   # qdrant
uv run streamlit run .\streamlit_app.py