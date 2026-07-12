"""
Mem0 Persistent Memory - local Qdrant storage with HuggingFace embeddings.
Logs real add/search/get_all calls so memory failures are visible during testing.
"""

import os
import traceback
from pprint import pformat

_memory = None
_memory_init_attempted = False


def get_memory():
    """Initialize Mem0 with local storage (lazy load)."""
    global _memory, _memory_init_attempted
    if _memory is not None:
        return _memory
    if _memory_init_attempted:
        print("[Mem0] Memory was already attempted and is unavailable.")
        return None

    _memory_init_attempted = True
    try:
        from mem0 import Memory

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(root, "data", "local_memory_db")

        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "career_memory",
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

        print(f"[Mem0] Initialising with Qdrant path: {db_path}")
        _memory = Memory.from_config(config)
        print("[Mem0] Memory system initialised (local Qdrant storage).")
        return _memory

    except ImportError:
        print("[Mem0] mem0ai is not installed; memory is disabled.")
        return None
    except Exception as e:
        print(f"[Mem0] Init failed: {e}")
        traceback.print_exc()
        return None


def save_memory(user_id: str, messages: list):
    """Save conversation messages to a student's memory and log Mem0's real response."""
    mem = get_memory()
    if mem is None:
        print(f"[Mem0] Save skipped because memory is unavailable. user_id={user_id}")
        return None

    print(f"[Mem0] ADD request user_id={user_id} messages={pformat(messages)}")
    try:
        result = mem.add(messages, user_id=user_id)
        print(f"[Mem0] ADD response user_id={user_id}: {pformat(result)}")
        return result
    except Exception as e:
        print(f"[Mem0] Save failed for user_id={user_id}: {e}")
        traceback.print_exc()
        raise


def search_memory(user_id: str, query: str, limit: int = 5) -> str:
    """Retrieve relevant past memories for a student and log the raw Mem0/Qdrant result."""
    mem = get_memory()
    if mem is None:
        print(f"[Mem0] Search skipped because memory is unavailable. user_id={user_id} query={query!r}")
        return ""

    print(f"[Mem0] SEARCH request user_id={user_id} query={query!r} limit={limit}")
    try:
        results = mem.search(query, filters={"user_id": user_id}, limit=limit)
        print(f"[Mem0] SEARCH raw response user_id={user_id}: {pformat(results)}")
        if isinstance(results, dict):
            results = results.get("results") or results.get("memories") or []
        if results:
            memories = []
            for item in results:
                if isinstance(item, dict):
                    memory_text = item.get("memory") or item.get("text")
                    if memory_text:
                        memories.append(memory_text)
            return "\n".join(memories)
        return ""
    except Exception as e:
        print(f"[Mem0] Search failed for user_id={user_id}: {e}")
        traceback.print_exc()
        return ""


def get_all_memories(user_id: str) -> list:
    """Get all stored memories for a student and log the raw response."""
    mem = get_memory()
    if mem is None:
        print(f"[Mem0] get_all skipped because memory is unavailable. user_id={user_id}")
        return []

    print(f"[Mem0] GET_ALL request user_id={user_id}")
    try:
        results = mem.get_all(user_id=user_id)
        print(f"[Mem0] GET_ALL raw response user_id={user_id}: {pformat(results)}")
        if isinstance(results, dict):
            results = results.get("results") or results.get("memories") or []
        return [r.get("memory") or r.get("text") for r in results if isinstance(r, dict) and (r.get("memory") or r.get("text"))]
    except Exception as e:
        print(f"[Mem0] Get all failed for user_id={user_id}: {e}")
        traceback.print_exc()
        raise