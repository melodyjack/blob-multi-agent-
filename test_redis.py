import os
import redis

# Load environment variables (ensure REDIS_URL is set)
redis_url = os.getenv("REDIS_URL")

if not redis_url:
    print("Error: REDIS_URL environment variable not set.")
    exit(1)

# Connect to Redis
try:
    r = redis.from_url(redis_url, decode_responses=True)
    print("✅ Successfully connected to Redis!")

    # Test setting a key
    success = r.set('foo', 'bar')
    if success:
        print("✅ Successfully set key 'foo' in Redis.")

    # Test retrieving the key
    result = r.get('foo')
    print(f"✅ Retrieved from Redis: foo = {result}")

except Exception as e:
    print(f"❌ Redis connection failed: {e}")

