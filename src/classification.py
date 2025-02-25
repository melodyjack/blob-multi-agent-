import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
import asyncio


classification_prompt = """
We have four persona categories: Cyclo, Emo, Prim, Spri.
Given the user’s message, decide which persona(s) are most relevant.
Output a comma-separated list with no extra text.
"""

async def classify_personas(user_text):
    """
    Calls GPT-4 using openai.ChatCompletion.create (new interface),
    wrapped in run_in_executor for asynchronous usage.
    """
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a persona classifier."},
                {"role": "user", "content": f"User text:\n{user_text}\n\n{classification_prompt}"}
            ],
            max_tokens=50,
            temperature=0.1)
        )
        text = resp.choices[0].message.content.strip()
        # Parse the CSV output into a list
        persona_list = [x.strip() for x in text.split(",")]
        valid_personas = [p for p in persona_list if p in ["Cyclo", "Emo", "Prim", "Spri"]]
        if not valid_personas:
            return ["Cyclo", "Emo", "Prim", "Spri"]
        return valid_personas
    except Exception as e:
        print("Classification error:", e)
        return ["Cyclo", "Emo", "Prim", "Spri"]
