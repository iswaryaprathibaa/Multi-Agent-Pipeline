"""Shared ChatOpenAI factory. Using langchain_openai (not the raw OpenAI SDK)
means every call is auto-traced to LangSmith once LANGCHAIN_TRACING_V2 is set
in src.config -- no manual instrumentation needed per agent.
"""
from langchain_openai import ChatOpenAI

from src import config


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    if not config.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    return ChatOpenAI(
        model=config.OPENAI_MODEL,
        temperature=temperature,
        api_key=config.OPENAI_API_KEY,
    )
