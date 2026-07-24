"""
============================================================
SBA AI Studio
Ollama Client
ML-026-002 / ML-069 (thinking-mode JSON fix) / ML-070
            (context-window truncation fix) / ML-071
            (timeout fallback model)
Version : 1.4.0
============================================================

Minimal client for a local Ollama instance's HTTP API
(http://localhost:11434 by default). Uses only the standard
library (urllib) - no extra pip dependency required.

Per the project's "AI Roadmap" - local AI (Ollama) by default,
cloud AI optional and not built here yet.

v1.1.0 (2026-07-20): default timeout_seconds raised 120.0 -> 300.0.
Gary hit repeated IntelliScript timeouts even on GPU-accelerated
Ollama - a full transcript prompt is longer than YouTube metadata's,
and 120s wasn't consistently enough. Gary chose a simple raised
default over a configurable Settings option.

v1.2.0 (2026-07-24, ML-069): after switching to qwen3.6 (see
ML-068 in youtube_metadata_generator.py for the routing fix that
got Qwen actually receiving requests), generation started coming
back as "model's response wasn't valid JSON" - the same failure
mode Gary already hit once with Qwen on Groq (see groq_provider.py's
reasoning_effort handling), caused by Qwen's thinking-mode
reasoning stream interfering with clean "format": "json" output.
Fixed the same way as the Groq side: generate() now adds
"think": False to the request payload whenever the configured
model name contains "qwen" (case-insensitive substring match, not
an exact-name allowlist, so future Qwen tags/variants are covered
without a code change) - this tells Ollama to suppress the
model's thinking/reasoning stream for that request. Non-Qwen
models (llama3.2, etc.) are unaffected - they never had this
problem and don't get the extra field.

v1.3.0 (2026-07-24, ML-070): IntelliScript output was coming back
truncated mid-JSON on a real transcript (~100+ segments) -
`ollama ps` showed the loaded model's CONTEXT as only 4096, far
too small to hold a full IntelliScript prompt (one line per
segment) PLUS a decision object for every single segment in the
response. This client never told Ollama to use a larger context
window, so Ollama silently fell back to a small default and cut
the response off before it finished. Fixed by adding an explicit
"options": {"num_ctx": ...} field to the request, with a new
constructor parameter (num_ctx, default 16384) so this is no
longer left to Ollama's own default. 16384 is a starting point,
not a guaranteed ceiling - a very long ride day's transcript could
still exceed it; if truncation reappears, raise num_ctx further
(qwen3.6 supports up to 262144 natively) at the cost of more
VRAM/RAM use and slower generation.

v1.4.0 (2026-07-24, ML-071): Gary's GPU (AMD RX 7600, 8GB VRAM)
can't fully fit the Qwen models he's been testing (18-23GB), so
they run heavily CPU-offloaded and can be slow enough to risk
hitting timeout_seconds on a long IntelliScript prompt. Added a
new fallback_model constructor parameter (wired from
config/settings.json's "ollama_fallback_model" via
ai_provider_factory.py - see app_settings.py ML-071 notes).
generate() now catches a timeout on the PRIMARY model specifically
and retries once with fallback_model before giving up, so a slow
Qwen run degrades to a fast, known-working model instead of
failing generation outright. Only a genuine timeout triggers the
retry - other errors (model not found, bad JSON, connection
refused) are not masked by a fallback attempt, since a fallback
model wouldn't fix any of those and silently hiding them would
make real problems harder to diagnose. If fallback_model is "" or
equals the primary model, no retry is attempted (same as before
this version). If the fallback attempt ALSO fails, the raised
OllamaError mentions both models so the person isn't left
guessing which one broke.
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


class _OllamaTimeout(OllamaError):
    """
    Internal-only subclass raised specifically for a request
    timeout (as opposed to any other OllamaError). Lets generate()
    distinguish "this specific model was too slow" (worth retrying
    with a fallback model) from every other failure mode (not
    worth retrying, since a different model wouldn't fix a bad
    connection or a missing model pull).
    """


class OllamaClient:
    """
    Thin wrapper around Ollama's /api/generate endpoint.
    """

    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
        timeout_seconds: float = 300.0,
        num_ctx: int = 16384,
        fallback_model: str = "",
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.num_ctx = num_ctx
        self.fallback_model = fallback_model

    def generate(self, prompt: str) -> str:
        """
        Sends `prompt` to the configured model and returns the
        raw generated text.

        If the primary model times out AND a distinct
        fallback_model is configured, automatically retries once
        with fallback_model before raising (ML-071). Any other
        error (model not found, bad JSON, connection refused) is
        raised immediately without a fallback attempt, since those
        aren't timing problems a different model would fix.

        Raises OllamaError (never a bare urllib exception) if
        Ollama isn't reachable, the model isn't available, or the
        response can't be parsed.
        """

        try:
            return self._generate_with_model(self.model, prompt)
        except _OllamaTimeout as primary_timeout:

            has_fallback = (
                self.fallback_model
                and self.fallback_model.lower() != self.model.lower()
            )

            if not has_fallback:
                raise OllamaError(str(primary_timeout)) from primary_timeout

            try:
                return self._generate_with_model(
                    self.fallback_model, prompt
                )
            except OllamaError as fallback_error:
                raise OllamaError(
                    f"'{self.model}' timed out after "
                    f"{self.timeout_seconds:.0f}s, and the fallback "
                    f"model '{self.fallback_model}' also failed: "
                    f"{fallback_error}"
                ) from fallback_error

    # -----------------------------------------------------

    def _generate_with_model(self, model: str, prompt: str) -> str:
        """
        Sends `prompt` to `model` specifically (not necessarily
        self.model - see generate()'s fallback retry) and returns
        the raw generated text. Raises _OllamaTimeout for a request
        timeout specifically, or OllamaError for anything else.
        """

        request_body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_ctx": self.num_ctx,
            },
        }

        # ML-069: Qwen models' thinking-mode reasoning stream can
        # interfere with clean "format": "json" output (the same
        # failure mode hit on Groq - see groq_provider.py). Substring
        # match, not an exact-name allowlist, so any Qwen tag/variant
        # is covered without needing a code change per model release.
        if "qwen" in model.lower():
            request_body["think"] = False

        payload = json.dumps(request_body).encode("utf-8")

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
                f"model '{model}'. If this says the model wasn't "
                f"found, pull it first: 'ollama pull {model}'. "
                f"Details: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                f"Could not reach Ollama at {self.host}. Is it "
                f"running? Try 'ollama serve' in a terminal, or "
                f"check that {self.host} is correct. "
                f"Details: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise _OllamaTimeout(
                f"Ollama did not respond within "
                f"{self.timeout_seconds:.0f}s for model '{model}'. "
                f"The model may be slow to load on first use - try "
                f"again, or use a smaller model."
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
