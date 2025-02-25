import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
import asyncio


async def choose_best_response(user_text, persona_responses, second_pass=False):
    """
    Uses GPT-4 to pick the single best response from persona_responses
    with the new openai.ChatCompletion.create interface.
    """
    system_prompt = (
        "You are a meta-evaluator. Given multiple persona responses, pick the single best or most relevant. "
        "Output only the persona name. Nothing else."
    )

    combined = f"User's text:\n{user_text}\n\nPersona responses:\n"
    for p, r in persona_responses.items():
        combined += f"{p}:\n{r}\n\n"

    loop = asyncio.get_running_loop()

    try:
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined}
            ],
            max_tokens=50,
            temperature=0.2)
        )
        chosen = completion.choices[0].message.content.strip()

        if chosen not in persona_responses:
            return list(persona_responses.keys())[0]
        return chosen

    except Exception as e:
        print("Meta-model error:", e)
        return list(persona_responses.keys())[0]
