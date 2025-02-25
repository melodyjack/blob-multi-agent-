import asyncio
import random
import re
import discord

from src.persona_handlers import call_persona, call_persona_governor
from src.classification import classify_personas
from src.memory_manager import save_memory, load_memory, clear_memory
from src.crisis_detector import crisis_detect
from src.persona_manager import (
    remove_persona, add_persona, reset_personas, isolate_persona,
    get_active_personas, is_isolation_mode
)

"""
We keep a global dictionary of user_id -> channel_id for private channels.
If a user calls '!private' and doesn't have one, we create it.
If they already have one, we point them to that channel.
"""
private_channels = {}  # Maps user_id (str) to channel_id (int)

def sanitize_persona_response(persona_name, response):
    """
    Cleans up the agent response by:
      - Removing any text enclosed in asterisks (e.g. *thinks for a sec*, *nods*, *smiles warmly*).
      - Removing unwanted phrases.
      - Stripping persona name prefixes.
    """
    # Remove italicized narrative actions (anything between asterisks)
    cleaned = re.sub(r'\*[^*]+\*', '', response)

    # Remove unwanted phrases (case-insensitive)
    unwanted_phrases = [
        "is reflecting on your question",
        "has something thoughtful to share",
        "is working on an answer right now",
    ]
    for phrase in unwanted_phrases:
        cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)

    # Remove any leading persona name prefixes, e.g., "Cyclo:" or "cyclo:"
    for prefix in [f"{persona_name}:", f"{persona_name.lower()}:", f"{persona_name.capitalize()}:" ]:
        if cleaned.strip().startswith(prefix):
            cleaned = cleaned.strip()[len(prefix):].strip()
            break

    return cleaned.strip()

async def handle_governor_message(message, persona_clients):
    """
    Main aggregator logic.
    Also handles user commands like !private, !new, !add, etc.
    """
    channel_id = str(message.channel.id)
    user_text = message.content.strip()
    user_author = message.author.display_name
    user_id = str(message.author.id)

    # 1) Check if it's a command
    if user_text.startswith("!"):
        await process_governor_command(message, persona_clients)
        return

    # 2) Crisis detection
    in_crisis = await crisis_detect(user_text)
    if in_crisis:
        await message.channel.send(
            "I’m really sorry you’re feeling this way. If you’re considering hurting yourself, please reach out. "
            "Call 988 (US) or visit https://findahelpline.com for help."
        )
        return

    # 3) Check for forced personas via @ mention (including @[Prim])
    forced_personas = []
    for p in ["Cyclo", "Emo", "Prim", "Spri"]:
        if f"@{p.lower()}" in user_text.lower() or f"@[{p.lower()}]" in user_text.lower():
            forced_personas.append(p)

    if len(forced_personas) == 1:
        iso_p = forced_personas[0]
        isolate_persona(iso_p)
        await message.channel.send(f"**Isolation mode: only {iso_p} will respond.**")

    # If multiple forced => each responds independently
    if len(forced_personas) > 1:
        tasks = []
        for p in forced_personas:
            tasks.append(asyncio.create_task(call_persona(p, user_text, channel_id)))

        wait_msg = await message.channel.send("**Thinking...**")
        await asyncio.sleep(2)

        done, pending = await asyncio.wait(tasks, timeout=20)
        responses = {}
        for task in done:
            try:
                pn, resp = task.result()
                sanitized = sanitize_persona_response(pn, resp)
                responses[pn] = sanitized
                save_memory(channel_id, pn, sanitized)
            except Exception as e:
                print("Error in forced persona call:", e)

        try:
            await wait_msg.delete()
        except:
            pass

        # Post each forced persona's response
        for pn, text in responses.items():
            client = persona_clients.get(pn)
            if client:
                await client.get_channel(message.channel.id).send(text)
            else:
                await message.channel.send(text)

        # If 2+ forced, Governor merges
        if len(responses) >= 2 and not is_isolation_mode():
            gov_name, gov_text = await call_persona_governor(responses, user_text, channel_id)
            if gov_text:
                merged_text = f"*{gov_text.strip()}*"
                gov_client = persona_clients.get("Governor")
                if gov_client:
                    await gov_client.get_channel(message.channel.id).send(merged_text)
                else:
                    await message.channel.send(merged_text)
        return

    # 4) Save user message
    save_memory(channel_id, user_author, user_text)

    # 5) If isolation is active, only that one persona responds
    if is_isolation_mode():
        actives = get_active_personas()
        if not actives:
            await message.channel.send("**No active personas.**")
            return

        p_isolated = actives[0]
        wait_msg = await message.channel.send("**Thinking...**")
        await asyncio.sleep(2)

        iso_name, iso_resp = await call_persona(p_isolated, user_text, channel_id)
        iso_resp = sanitize_persona_response(iso_name, iso_resp)
        save_memory(channel_id, iso_name, iso_resp)

        try:
            await wait_msg.delete()
        except:
            pass

        client_iso = persona_clients.get(iso_name)
        if client_iso:
            await client_iso.get_channel(message.channel.id).send(iso_resp)
        else:
            await message.channel.send(iso_resp)
        return

    # 6) Otherwise do classification => random multi-turn
    actives = get_active_personas()
    c_list = await classify_personas(user_text)
    c_list = [p for p in c_list if p in actives]
    if not c_list:
        c_list = actives

    wait_msg = await message.channel.send("**Thinking...**")
    await asyncio.sleep(2)

    # Pick persona A
    A = random.choice(c_list)
    A_name, A_resp = await call_persona(A, user_text, channel_id)
    A_resp = sanitize_persona_response(A_name, A_resp)
    save_memory(channel_id, A_name, A_resp)

    try:
        await wait_msg.delete()
    except:
        pass

    # Post A's response
    clientA = persona_clients.get(A_name)
    if clientA:
        await clientA.get_channel(message.channel.id).send(A_resp)
    else:
        await message.channel.send(A_resp)

    # Random multi-turn approach: A; or (A,B); or (A,B,A); or (A,B,C)
    flow_roll = random.random()
    responses_map = { A_name: A_resp }

    if flow_roll <= 0.33:
        pass  # Only A responds.
    else:
        # Second persona response
        c_list_2 = [p for p in c_list if p != A_name]
        if c_list_2:
            B = random.choice(c_list_2)
            wait2 = await message.channel.send("**Thinking more...**")
            await asyncio.sleep(2)

            second_input = f"User said:\n{user_text}\n\nThe first response was:\n{A_resp}"
            B_name, B_resp = await call_persona(B, second_input, channel_id)
            B_resp = sanitize_persona_response(B_name, B_resp)
            save_memory(channel_id, B_name, B_resp)

            try:
                await wait2.delete()
            except:
                pass

            clientB = persona_clients.get(B_name)
            if clientB:
                await clientB.get_channel(message.channel.id).send(B_resp)
            else:
                await message.channel.send(B_resp)

            responses_map[B_name] = B_resp

            follow_roll = random.random()
            if flow_roll <= 0.50:
                pass  # (A,B) only
            else:
                # Third response
                if follow_roll < 0.5:
                    # (A,B,A)
                    third_wait = await message.channel.send("**A brief follow-up...**")
                    await asyncio.sleep(2)

                    third_input = (
                        f"Second response:\n{B_resp}\n\n"
                        f"Please provide a short final follow-up, {A_name}."
                    )
                    name3, resp3 = await call_persona(A_name, third_input, channel_id)
                else:
                    # (A,B,C) if possible
                    c_list_3 = [p for p in c_list_2 if p != B_name]
                    if not c_list_3:
                        c_list_3 = [A_name]
                    C = random.choice(c_list_3)
                    third_wait = await message.channel.send("**Another perspective...**")
                    await asyncio.sleep(2)

                    third_input = (
                        f"User said:\n{user_text}\n\n"
                        f"First response:\n{A_resp}\n\n"
                        f"Second response:\n{B_resp}\n\n"
                        f"Please offer your unique perspective, {C}."
                    )
                    name3, resp3 = await call_persona(C, third_input, channel_id)

                resp3 = sanitize_persona_response(name3, resp3)
                save_memory(channel_id, name3, resp3)

                try:
                    await third_wait.delete()
                except:
                    pass

                client3 = persona_clients.get(name3)
                if client3:
                    await client3.get_channel(message.channel.id).send(resp3)
                else:
                    await message.channel.send(resp3)

                responses_map[name3] = resp3

    # Governor merges if more than one distinct persona responded
    if not is_isolation_mode() and len(responses_map.keys()) > 1:
        gov_name, gov_text = await call_persona_governor(responses_map, user_text, channel_id)
        if gov_text:
            final_text = f"*{gov_text.strip()}*"
            gov_client = persona_clients.get("Governor")
            if gov_client:
                await gov_client.get_channel(message.channel.id).send(final_text)
            else:
                await message.channel.send(final_text)

async def process_governor_command(message, persona_clients):
    user_text = message.content.strip()
    parts = user_text.split()
    cmd = parts[0].lower() if parts else None
    args = parts[1:] if len(parts) > 1 else []

    if cmd == "!remove":
        if args:
            persona = args[0].lstrip("@").capitalize()
            remove_persona(persona)
            await message.channel.send(f"**Removed {persona} from active personas.**")
        else:
            await message.channel.send("**Usage: !remove [PersonaName]**")
        return

    elif cmd == "!add":
        if args:
            persona = args[0].lstrip("@").capitalize()
            add_persona(persona)
            await message.channel.send(f"**Added {persona} to active personas.**")
        else:
            await message.channel.send("**Usage: !add [PersonaName]**")
        return

    elif cmd == "!reset":
        reset_personas()
        await message.channel.send("**All personas reset to active. Isolation mode off.**")
        return

    elif cmd == "!isolate":
        if args:
            persona = args[0].lstrip("@").capitalize()
            isolate_persona(persona)
            await message.channel.send(f"**Isolation mode: only {persona} will respond.**")
        else:
            await message.channel.send("**Usage: !isolate [PersonaName]**")
        return

    elif cmd == "!new":
        clear_memory(str(message.channel.id))
        reset_personas()
        await message.channel.send("**Memory cleared and all personas reset.**")
        return

    elif cmd == "!commands":
        await message.channel.send(
            "**Commands:**\n"
            "`!remove [PersonaName]` — Disable a persona.\n"
            "`!add [PersonaName]` — Re-enable a persona.\n"
            "`!reset` — Reset to all personas active.\n"
            "`!isolate [PersonaName]` — Only that persona is active.\n"
            "`!commands` — Show this help.\n"
            "`!new` — Reset memory & reset all personas.\n"
            "`!private` — Create a private conversation with all bots.\n"
        )
        return

    elif cmd == "!private":
        # Create (or find) a private channel for the user
        await handle_private_command(message, persona_clients)
        return

    else:
        await message.channel.send(
            f"**Unknown command: {cmd}.**\n"
            "**Use !commands to see available commands.**"
        )
        return

async def handle_private_command(message, persona_clients):
    """
    Creates (or finds) a private channel for the user, with read/write
    access only for that user and the bots.
    """
    guild = message.guild
    author = message.author
    user_id = str(author.id)

    # If a channel already exists for this user, inform them
    if user_id in private_channels:
        channel_id = private_channels[user_id]
        existing_channel = guild.get_channel(channel_id)
        if existing_channel:
            await message.channel.send(
                f"**You already have a private channel:** <#{channel_id}>"
            )
            return
        else:
            del private_channels[user_id]

    # Create a new private channel named after the user
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    # Give each bot read/write permissions
    for bot_name, bot_client in persona_clients.items():
        if bot_client.user:
            overwrites[bot_client.user] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True
            )

    private_channel = await guild.create_text_channel(
        name=f"{author.name}-private",
        overwrites=overwrites
    )
    private_channels[user_id] = private_channel.id

    await message.channel.send(
        f"**Private channel created:** <#{private_channel.id}>"
    )
