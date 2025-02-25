import os
import redis
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the Redis connection URL from the environment.
# If not set, default to a local Redis instance.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize the Redis client with the provided URL.
# decode_responses=True ensures that we work with Python strings.
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def load_memory(channel_id, limit=10):
    """
    Retrieve the conversation history for a given channel.

    This function returns the last 'limit * 2' entries from Redis, where each
    user message and bot response pair counts as two entries.

    Parameters:
        channel_id (str): Unique identifier for the channel.
        limit (int): The number of message pairs to retrieve. Defaults to 10.

    Returns:
        list: A list of conversation entries (strings).
    """
    key = f"history:{channel_id}"
    return r.lrange(key, -limit * 2, -1)

def save_memory(channel_id, author, content):
    """
    Save a new conversation entry into Redis memory.

    The entry is formatted as "author: content". After appending, the memory is
    trimmed to keep only the last 40 entries, ensuring that the history remains manageable.

    Parameters:
        channel_id (str): Unique identifier for the channel.
        author (str): The author of the message (user or bot).
        content (str): The content of the message.
    """
    key = f"history:{channel_id}"
    entry = f"{author}: {content}"
    r.rpush(key, entry)
    # Keep only the last 40 entries in the conversation history.
    r.ltrim(key, -40, -1)

def clear_memory(channel_id):
    """
    Clear the conversation history for a given channel by deleting its Redis key.

    Parameters:
        channel_id (str): Unique identifier for the channel.
    """
    key = f"history:{channel_id}"
    r.delete(key)
