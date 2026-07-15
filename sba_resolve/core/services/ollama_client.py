"""
============================================================
SBA AI Studio
Ollama Client
ML-026-002
Version : 1.0.0 Alpha
============================================================

Minimal client for a local Ollama instance's HTTP API
(http://localhost:11434 by default). Uses only the standard
library (urllib) - no extra pip dependency required.

Per the project's "AI Roadmap" - local AI (Ollama) by default,
cloud AI optional and not built here yet.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class OllamaError(RuntimeError):
    """
    Raised when Ollama can't be reached, or returns an error -
    always with a clear, actionable message (is it running? is
    the model pulled?) rather than a bare connection traceback.
    """


class OllamaClient:
    """
    Thin wrapper around Ollama's /api/generate endpoint.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
        timeout_seconds: float = 120.0,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        """
        Sends `prompt` to the configured model and returns the
        raw generated text.

        Raises OllamaError (never a bare urllib exception) if
        Ollama isn't reachable, the model isn't available, or the
        response can't be parsed.
        """

        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                pass
            raise OllamaError(
                f"Ollama returned an error (HTTP {exc.code}) for "
                f"model '{self.model}'. If this says the model "
                f"wasn't found, pull it first: "
                f"'ollama pull {self.model}'. Details: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                f"Could not reach Ollama at {self.host}. Is it "
                f"running? Try 'ollama serve' in a terminal, or "
                f"check that {self.host} is correct. "
                f"Details: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise OllamaError(
                f"Ollama did not respond within "
                f"{self.timeout_seconds:.0f}s. The model may be "
                f"slow to load on first use - try again, or use "
                f"a smaller model."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaError(
                f"Ollama's response wasn't valid JSON: {raw[:200]!r}"
            ) from exc

        text = data.get("response")

        if not isinstance(text, str):
            raise OllamaError(
                f"Ollama's response had no 'response' text field: "
                f"{data!r}"
            )

        return text
