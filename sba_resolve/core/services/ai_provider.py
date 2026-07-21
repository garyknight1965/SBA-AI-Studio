"""
============================================================
SBA AI Studio
AI Provider Interface
Backlog: Add Groq Provider Support (originally speced as Gemini)
Version : 1.0.0
============================================================

A minimal structural interface (typing.Protocol - no inheritance
required) that every AI backend implements: OllamaClient (see
ollama_client.py) and GroqProvider (see groq_provider.py) both
satisfy this automatically, since Python Protocols check shape,
not class hierarchy.

Every AI-calling service in the app (IntelliScriptEditor,
YouTubeMetadataGenerator, EditingAssistantGenerator,
IntelliScriptChapterGenerator) already only ever calls
`.generate(prompt)` on whatever client it was given - this
Protocol formalizes that shape so a second backend can be added
without any of those services needing to know which one is
actually running.

system_prompt is optional and unused by every existing call site
today - it exists so a real system-instruction split is possible
for future callers without forcing today's single-prompt-string
call sites to change. Adding a second provider does not require a
prompt redesign (explicitly out of scope for this backlog item).
"""

from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        Sends prompt (and optional system_prompt) to the backend and
        returns the raw generated text. Implementations raise their
        own backend-specific error type (e.g. OllamaError, GroqError)
        on failure - never a bare/unhandled exception type a caller
        wouldn't recognize.
        """
        ...