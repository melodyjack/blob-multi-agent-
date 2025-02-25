# src/memory_manager.py

import redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def load_memory(channel_id, limit=10):
    """
    Return the last 'limit*2' entries (user/bot pairs).
    """
    key = f"history:{channel_id}"
    entries = r.lrange(key, -limit * 2, -1)
    return entries

def save_memory(channel_id, author, content):
    """
    Save a new line in the conversation memory.
    Format: "author: content"
    """
    key = f"history:{channel_id}"
    entry = f"{author}: {content}"
    r.rpush(key, entry)
    # Keep last 40 lines
    r.ltrim(key, -40, -1)

def clear_memory(channel_id):
    key = f"history:{channel_id}"
    r.delete(key)
