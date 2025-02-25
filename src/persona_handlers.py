import os
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

from src.memory_manager import load_memory
from src.persona_prompts import (
    cyclo_prompt,
    emo_prompt,
    prim_prompt,
    spri_prompt,
    governor_prompt
)

# Load environment variables from .env file
load_dotenv()

# Load API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY", "")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

client = OpenAI(api_key=openai_api_key)


# Temperature settings for each persona
temperature_map = {
    "Governor": 0.4,  # Governor uses OpenAI
    "Cyclo": 0.3,
    "Emo": 0.5,
    "Prim": 0.7,
    "Spri": 1.0
}

# Define the Anthropic model to use (Claude 3 Sonnet)
CLAUDE_MODEL = "claude-3-sonnet-20240229"

def get_system_prompt(persona_name):
    if persona_name == "Cyclo":
        return cyclo_prompt
    elif persona_name == "Emo":
        return emo_prompt
    elif persona_name == "Prim":
        return prim_prompt
    elif persona_name == "Spri":
        return spri_prompt
    elif persona_name == "Governor":
        return governor_prompt
    else:
        return "You are an AI assistant."

async def call_persona(persona_name, user_text, channel_id, max_tokens=350, temperature=None):
    """
    Calls the appropriate API:
    - For Governor: uses OpenAI (GPT-4)
    - For all other personas: uses Anthropic's Claude.
    """
    system_prompt = get_system_prompt(persona_name)
    if temperature is None:
        temperature = temperature_map.get(persona_name, 0.7)

    # Load conversation history and construct final input
    history = load_memory(channel_id, limit=10)
    context_str = "\n".join(history) if history else ""
    final_user_input = f"Context:\n{context_str}\n\n{user_text}"

    if persona_name == "Governor":
        return await _call_openai(persona_name, system_prompt, final_user_input, max_tokens, temperature)
    else:
        return await _call_claude(persona_name, system_prompt, final_user_input, max_tokens, temperature)

async def call_persona_governor(responses_dict, user_text, channel_id, max_tokens=350, temperature=None):
    """
    Specialized function to merge multiple persona outputs via Governor (using OpenAI).
    """
    if temperature is None:
        temperature = temperature_map.get("Governor", 0.4)

    # Combine user text and responses from other personas
    content_str = f"User's question:\n{user_text}\n\n"
    content_str += "Persona responses:\n"
    for name, text in responses_dict.items():
        content_str += f"{name} responded:\n{text}\n\n"

    history = load_memory(channel_id, limit=10)
    context_str = "\n".join(history) if history else ""
    final_user_input = f"Context:\n{context_str}\n\n{content_str}"

    return await _call_openai("Governor", governor_prompt, final_user_input, max_tokens, temperature)

async def _call_openai(persona_name, system_prompt, raw_input, max_tokens, temperature):
    """
    Helper function using OpenAI's ChatCompletion.create with the new interface.
    """
    loop = asyncio.get_running_loop()
    try:
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_input}
            ],
            max_tokens=max_tokens,
            temperature=temperature)
        )
        answer = completion.choices[0].message.content.strip()
        return (persona_name, answer)
    except Exception as e:
        print(f"OpenAI error ({persona_name}):", e)
        return (persona_name, f"Error: {str(e)}")

async def _call_claude(persona_name, system_prompt, raw_input, max_tokens, temperature):
    """
    Helper function using Anthropic's Claude API.
    """
    if not anthropic_api_key:
        return (persona_name, "Error: No Anthropic API key provided.")

    client = anthropic.Anthropic(api_key=anthropic_api_key)

    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": raw_input}]
            )
        )
        answer = response.content[0].text.strip()
        return (persona_name, answer)
    except Exception as e:
        print(f"Claude error ({persona_name}):", e)
        return (persona_name, f"Error: {str(e)}")
