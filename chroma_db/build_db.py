# Build Knowledge Base
import os
import chromadb
# Replaced import google.generativeai as genai with new SDK
from google import genai
from google.genai import types

# ==========================================
# 1. Environment & Client Setup
# ==========================================
api_key_user = input("Please enter your Google Gemini API Key: ").strip()

# Initialize the new SDK Client
client = genai.Client(api_key=api_key_user)

# Using the stable model name
EMBEDDING_MODEL = "models/gemini-embedding-001" 

def build_knowledge_base():
    print("🚀 Starting to build Vector Database (Knowledge Base)...")

    # Creates a 'chroma_db' directory for persistent storage
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    # Create or get a Collection (similar to a SQL Table)
    collection = chroma_client.get_or_create_collection(name="game_modules")

    # Read Reference Modules
    folder_path = r"C:\Users\user\Desktop\Big_Folder\Programs\Graduation_project\Project\reference_modules"
    if not os.path.exists(folder_path):
        print(f"❌ Error: Cannot find folder {folder_path}")
        return

    # Prepare batch data
    documents = []   # Stores code content
    ids = []         # Stores filenames as IDs
    metadatas = []   # Stores extra info (e.g., tags)

    print(f"📂 Scanning {folder_path}...")
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".py"):
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            print(f"   -> Module found: {filename}")
            
            # Simple parsing for the starting # tags:
            tags = "general"
            lines = content.split('\n')
            if lines and lines[0].startswith("# tags:"):
                tags = lines[0].replace("# tags:", "").strip()

            documents.append(content)
            ids.append(filename)
            metadatas.append({"source": filename, "tags": tags})

    if not documents:
        print("⚠️ No .py files found. Please check your setup.")
        return

    # Generate Embeddings and save to Database
    print("🧠 Calling Gemini to generate vectors (this may take a few seconds)...")
    
    try:
        # Migrated to the new client.models.embed_content syntax for batch processing
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=documents,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                title="Game Code Snippets"
            )
        )
        
        # In the new SDK, batch results are accessed via e.values for each entry in embeddings
        embeddings = [e.values for e in result.embeddings]

        print("💾 Writing to ChromaDB...")
        # Use upsert to prevent duplicates if running the script multiple times
        collection.upsert(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Success! Saved {len(documents)} modules to the database.")
        print("   Database path: ./chroma_db")
        
    except Exception as e:
        print(f"❌ An error occurred during database build: {e}")

if __name__ == "__main__":
    build_knowledge_base()