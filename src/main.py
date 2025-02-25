import os
import asyncio
import discord
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

from src.aggregator import handle_governor_message

# Discord tokens from environment variables
TOKEN_GOVERNOR = os.getenv("BLOB_TOKEN_GOVERNOR")
TOKEN_CYCLO    = os.getenv("BLOB_TOKEN_CYCLO")
TOKEN_EMO      = os.getenv("BLOB_TOKEN_EMO")
TOKEN_PRIM     = os.getenv("BLOB_TOKEN_PRIM")
TOKEN_SPRI     = os.getenv("BLOB_TOKEN_SPRI")

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True

# Create Discord clients for each bot persona
client_governor = discord.Client(intents=intents)
client_cyclo    = discord.Client(intents=intents)
client_emo      = discord.Client(intents=intents)
client_prim     = discord.Client(intents=intents)
client_spri     = discord.Client(intents=intents)

@client_governor.event
async def on_ready():
    print(f"Governor is ready as {client_governor.user}")

@client_cyclo.event
async def on_ready():
    print(f"Cyclo is ready as {client_cyclo.user}")

@client_emo.event
async def on_ready():
    print(f"Emo is ready as {client_emo.user}")

@client_prim.event
async def on_ready():
    print(f"Prim is ready as {client_prim.user}")

@client_spri.event
async def on_ready():
    print(f"Spri is ready as {client_spri.user}")

@client_governor.event
async def on_message(message):
    # Ignore messages from self or other bots
    if message.author == client_governor.user or message.author.bot:
        return
    # Map persona names to their corresponding Discord clients
    persona_clients = {
        "Cyclo":    client_cyclo,
        "Emo":      client_emo,
        "Prim":     client_prim,
        "Spri":     client_spri,
        "Governor": client_governor
    }
    await handle_governor_message(message, persona_clients)

# --- Health server to satisfy Fly.io ---
async def handle_health(request):
    return web.Response(text="OK")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("Health server started on 0.0.0.0:8080")

# --- Main function to start both the health server and Discord bots ---
def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Start the HTTP health server
    loop.create_task(start_health_server())
    # Start Discord bot clients concurrently
    loop.create_task(client_governor.start(TOKEN_GOVERNOR))
    loop.create_task(client_cyclo.start(TOKEN_CYCLO))
    loop.create_task(client_emo.start(TOKEN_EMO))
    loop.create_task(client_prim.start(TOKEN_PRIM))
    loop.create_task(client_spri.start(TOKEN_SPRI))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.stop()

if __name__ == "__main__":
    main()
