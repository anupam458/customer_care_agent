import google.generativeai as genai
from dotenv import load_dotenv
import os
import hashlib
import numpy as np
import database

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

chat_model = genai.GenerativeModel("gemini-flash-latest")

SYSTEM_PROMPT = """You are a helpful customer support agent.
You have access to the customer's past conversation history stored in a database.
Use that context to provide personalized, consistent answers.
If the customer mentioned preferences, past issues, or details before,
reference them naturally. Be professional, empathetic, and concise.
Always sign off as "Support Team"."""

def get_embedding(text):
    """Use Gemini to generate embedding via chat model as a workaround."""
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text
        )
        return result['embedding']
    except Exception:
        # Fallback: deterministic pseudo-embedding from text hash
        np.random.seed(int(hashlib.md5(text.encode()).hexdigest()[:8], 16))
        return np.random.rand(384).tolist()

def process_message(customer_id, user_message):
    user_embedding = get_embedding(user_message)
    memories = database.search_memories(customer_id, user_embedding, limit=5)

    context = ""
    if memories:
        context = "Relevant past interactions with this customer:\n"
        for m in memories:
            context += f"  [{m['role']}] {m['content']}\n"

    prompt = f"""{SYSTEM_PROMPT}

{context}

Customer says: "{user_message}"

Respond as the support agent:"""

    response = chat_model.generate_content(prompt)
    agent_reply = response.text.strip()

    database.store_memory(customer_id, "user", user_message, user_embedding)
    agent_embedding = get_embedding(agent_reply)
    database.store_memory(customer_id, "agent", agent_reply, agent_embedding)

    return agent_reply, memories