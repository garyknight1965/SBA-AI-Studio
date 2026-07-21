"""
============================================================
SBA AI Studio
AI Provider Factory
Backlog: Add Groq Provider Support (originally speced as Gemini)
Version : 1.0.0
============================================================

The ONE place in the app that knows both AI backends exist. Every
AI-calling service (IntelliScriptEditor, YouTubeMetadataGenerator,
EditingAssistantGenerator, IntelliScriptChapterGenerator) defaults to
calling get_ai_provider() instead of constructing OllamaClient()
directly - this is what makes switching providers in Settings take
effect immediately, with no restart and no other file needing to
know which backend is active.
"""

from __future__ import annotations

from sba_resolve.core.services.ai_provider import AIProvider
from sba_resolve.core.services.app_settings import (
    load_ai_provider,
    load_groq_api_key,
    load_groq_model,
    load_ollama_model,
)
from sba_resolve.core.services.groq_provider import GroqProvider
from sba_resolve.core.services.ollama_client import OllamaClient


def get_ai_provider() -> AIProvider:
    """
    Reads "ai_provider" from config/settings.json and returns the
    matching backend, already configured from Settings (model name,
    API key where relevant).

    Defaults to Ollama (load_ai_provider() returns "ollama" for a
    missing/malformed setting - see app_settings.py) so an untouched
    settings.json reproduces the original, Ollama-only behaviour
    exactly.
    """

    provider = load_ai_provider()

    if provider == "groq":
        return GroqProvider(
            api_key=load_groq_api_key(),
            model=load_groq_model(),
        )

    return OllamaClient(model=load_ollama_model())