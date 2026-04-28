import os
import json
import sys
import chromadb
from google.genai import types              #type:ignore

# Import updated config
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox.config import client, EMBEDDING_MODEL

def select_relevant_modules(user_query: str) -> str:
    """
    Phase 1: Use the new Client to analyze the catalog.json.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_path = os.path.join(current_dir, "catalog.json")
    
    if not os.path.exists(catalog_path):
        print("⚠️ Warning: Module catalog not found.")
        sys.exit(1)

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)
            catalog_str = json.dumps(catalog_data, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Failed to read catalog: {e}")
        return ""

    print(f"🤔 Analyzing requirements based on the catalog...")

    prompt = (
        "You are a technical selection expert for Python game development. "
        f"Our current arsenal list is as follows (JSON format):\n{catalog_str}\n"
        f"The user's requirement is: '{user_query}'. "
        "[Task] Return ONLY the filenames of NECESSARY modules, separated by commas."
    )

    try:
        # Migrated to client.models.generate_content
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        selected = response.text.strip()
        
        if "NONE" in selected:
            print("   -> Analysis result: No specific modules required.")
            return ""
        else:
            print(f"   -> 💡 Expert suggests using: {selected}")
            return selected
            
    except Exception as e:
        print(f"❌ Selection analysis failed: {e}")
        return ""

def get_rag_context(user_query: str) -> str:
    suggested_modules = select_relevant_modules(user_query)
    enhanced_query = user_query
    if suggested_modules:
        enhanced_query = f"{user_query}. Strictly use these modules: {suggested_modules}"
    
    print(f"🔍 RAG system started: Searching database...")
    
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_collection(name="game_modules")
        
        # Migrated to client.models.embed_content
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=enhanced_query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        # In new SDK, the result structure is result.embeddings[0].values
        query_embedding = result.embeddings[0].values
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=10, 
            include=['documents', 'distances'] 
        )
        
        DISTANCE_THRESHOLD = 1.0
        found_contents = []
        
        if results['documents']:
            num_results = len(results['documents'][0])
            for i in range(num_results):
                doc_content = results['documents'][0][i]
                doc_id = results['ids'][0][i]
                distance = results['distances'][0][i]
                
                final_threshold = DISTANCE_THRESHOLD
                if suggested_modules and doc_id in suggested_modules:
                    final_threshold = 1.5 
                    print(f"   -> Required file found: {doc_id} (Threshold relaxed to 1.5)")

                print(f"   -> Candidate file: {doc_id:<30} | Distance: {distance:.4f}", end="")
                
                if distance < final_threshold:
                    print(" ✅ Adopted")
                    formatted_doc = (
                        f"\n\n# ====== Reference Module: {doc_id} ======\n"
                        f"{doc_content}\n"
                        f"# ============================================\n"
                    )
                    found_contents.append(formatted_doc)
                else:
                    print(" ❌ Discarded")

        return "".join(found_contents) if found_contents else ""
            
    except Exception as e:
        print(f"❌ RAG retrieval failed: {e}")
        return ""