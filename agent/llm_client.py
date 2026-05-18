import os
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client = None


def get_model():
    return GROQ_MODEL


def _get_client():
    global _client

    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Add it to your environment variables."
        )

    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)

    return _client


def chat(messages):
    client = _get_client()

    # Groq handles system messages natively, no need to extract them
    response = client.chat.completions.create(
        model=get_model(),
        messages=messages
    )

    return response.choices[0].message.content.strip()