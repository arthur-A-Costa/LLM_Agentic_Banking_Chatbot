import os

from langchain_ollama import ChatOllama


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3:8b")
ROUTER_MODEL = os.getenv("ROUTER_MODEL", DEFAULT_MODEL)
SALESMAN_MODEL = os.getenv("SALESMAN_MODEL", DEFAULT_MODEL)
CONSULTANT_MODEL = os.getenv("CONSULTANT_MODEL", DEFAULT_MODEL)
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", DEFAULT_MODEL)
ALTERNATIVE_MODEL = os.getenv("ALTTERNATIVE_MODEL", "qwen2.5:1.5b")
EDITOR_MODEL = os.getenv("REVIEWER_MODEL", DEFAULT_MODEL)
COLLECTOR_MODEL = os.getenv("COLLECTOR_MODEL", DEFAULT_MODEL)

def get_llm():
    return ChatOllama(
        model = ALTERNATIVE_MODEL,
        base_url=OLLAMA_BASE_URL,
        validate_model_on_init=True,
        temperature=0.2,
    )


def get_router_llm():
    return ChatOllama(
        model=ROUTER_MODEL,
        base_url=OLLAMA_BASE_URL,
        validate_model_on_init=True,
        temperature=0,
    )


def get_salesman_llm():
    return ChatOllama(
        model=SALESMAN_MODEL,
        base_url=OLLAMA_BASE_URL,
        validate_model_on_init=True,
        temperature=0.2,
    )


def get_consultant_llm():
    return ChatOllama(
        model=CONSULTANT_MODEL,
        base_url=OLLAMA_BASE_URL,
        validate_model_on_init=True,
        temperature=0.1,
    )


def get_reviewer_llm():
    return ChatOllama(
        model=REVIEWER_MODEL,
        base_url=OLLAMA_BASE_URL,
        validate_model_on_init=True,
        temperature=0,
    )

def get_editor_llm():
    return ChatOllama(
        model=EDITOR_MODEL,
        base_url=OLLAMA_BASE_URL,
        validate_model_on_init=True,
        temperature=0,
    )

def get_collector_llm():
    return ChatOllama(
        model=COLLECTOR_MODEL,
        base_url=OLLAMA_BASE_URL,
        validate_model_on_init=True,
        temperature=0,
    )