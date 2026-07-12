import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"))

from mem0 import Memory

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_mem0_db")
config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "test_collection",
            "path": db_path,
        },
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        },
    },
}

groq_key = os.environ.get("GROQ_API_KEY", "")
if groq_key:
    config["llm"] = {
        "provider": "groq",
        "config": {
            "model": "llama-3.3-70b-versatile",
            "api_key": groq_key,
            "temperature": 0,
            "max_tokens": 2000,
        },
    }

print("Initializing Memory...")
mem = Memory.from_config(config)

user_id = "test_user_123"

# Test add
print("\n--- Testing add ---")
try:
    res_add = mem.add("I study in Pre-Medical stream.", user_id=user_id)
    print("Add success:", res_add)
except Exception as e:
    print("Add failed:", e)

# Test search with user_id
print("\n--- Testing search with user_id ---")
try:
    res_search = mem.search("What is my stream?", user_id=user_id)
    print("Search with user_id success:", res_search)
except Exception as e:
    print("Search with user_id failed:", e)

# Test search with filters
print("\n--- Testing search with filters ---")
try:
    res_search_filter = mem.search("What is my stream?", filters={"user_id": user_id})
    print("Search with filters success:", res_search_filter)
except Exception as e:
    print("Search with filters failed:", e)

# Test get_all with user_id
print("\n--- Testing get_all with user_id ---")
try:
    res_get = mem.get_all(user_id=user_id)
    print("get_all success:", res_get)
except Exception as e:
    print("get_all failed:", e)
