import os

import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"


class GroqConfigError(RuntimeError):
    """Raised when Groq can't be called due to missing/invalid configuration."""


def call_groq(
    messages,
    model: str = DEFAULT_MODEL,
    json_mode: bool = False,
    timeout: int = 30,
    temperature: float | None = None,
) -> str:
    """Send a chat completion request to Groq and return the response text.

    Raises GroqConfigError if GROQ_API_KEY isn't set, or requests.HTTPError
    if the API call itself fails - both are clear, catchable error paths
    rather than a raw crash.

    temperature: left at the API default (sampling) unless a caller passes
    one explicitly. Callers that need reproducible structured output (e.g.
    pdfext's format discovery) should pass temperature=0 - otherwise
    identical input can silently produce different extraction results
    across repeated runs.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise GroqConfigError(
            "GROQ_API_KEY is not set. Add it to a .env file in the project root."
        )

    payload = {"model": model, "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if temperature is not None:
        payload["temperature"] = temperature

    response = requests.post(
        GROQ_CHAT_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
