"""
============================================================
SBA AI Studio
Groq Provider
Backlog: Add Groq Provider Support (originally speced as Gemini)
Version : 1.2.0
============================================================

Minimal client for Groq's cloud inference API
(https://api.groq.com/openai/v1/chat/completions) - OpenAI-compatible
chat completion format. Uses only the standard library (urllib), same
as ollama_client.py - no extra pip dependency required.

Chosen over Gemini (the backlog item's original spec) per Gary's
decision (2026-07-20): his actual complaint was Ollama's slowness/
timeouts, and Groq's custom LPU hardware runs the same Llama model
family he already uses locally, at several times the speed, with a
much higher free daily request limit than Gemini's free tier. Gemini
remains a valid future addition as a second AIProvider implementation
if ever wanted - nothing here blocks that.

The API key is used ONLY inside the Authorization header of the
request - never placed in a URL, never interpolated into any log or
error message text. Every error message below is built from fixed,
descriptive text plus the HTTP status/reason Groq/urllib themselves
provide - never the request object, headers, or payload.

Version 1.1.0 (2026-07-20): added an explicit User-Agent header.
Cloudflare fronts Groq's API and was blocking every request with
HTTP 403 / error code 1010 ("Access Denied: bad bot") because
urllib's default User-Agent signature ("Python-urllib/3.x") gets
flagged as a bot - confirmed via a Groq community forum thread
reporting this exact error. A normal-looking User-Agent avoids it.

Version 1.2.0 (2026-07-23): fixed a real "Failed to validate JSON"
(json_validate_failed) HTTP 400 that Gary hit repeatedly and
consistently on IntelliScript (a long transcript -> one decision
object per segment, potentially hundreds), after switching to
`openai/gpt-oss-120b` (the replacement for the now-deprecated
`llama-3.3-70b-versatile` - see app_settings.py). YouTube metadata
(a short, bounded response) mostly succeeded, which pointed at
truncation rather than pure model flakiness: no `max_tokens` was
ever set on this request, so a long expected response could get
cut off mid-JSON before it finished - genuinely invalid JSON,
which Groq's own `json_object` mode correctly rejects.

Two changes:
    1. DEFAULT_MAX_TOKENS is now sent explicitly, generous enough
       for a full-length IntelliScript response to complete rather
       than being cut off by whatever smaller ceiling Groq defaults
       to when max_tokens is omitted.
    2. For models known to support a reasoning-effort control
       (gpt-oss-* models: "low"/"medium"/"high"; qwen models:
       "none" to disable reasoning outright), this now explicitly
       requests LOW/no reasoning effort - since reasoning tokens
       eat into the same token budget as the actual JSON answer,
       and (per Groq's own docs/community reports) can sometimes
       leak into or interfere with the final JSON output. This is
       matched by string in self.model rather than an exhaustive
       model list, since Groq's model lineup changes over time -
       if a future model name doesn't match either pattern, no
       reasoning_effort field is sent at all (safe default -
       avoids sending an unsupported field to a model that would
       reject it).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# ML-067: how many tokens Groq is allowed to generate per response.
# Left unset before this version, which meant Groq's own smaller
# default ceiling could truncate a long expected response (e.g.
# IntelliScript's one-decision-per-segment JSON array on a full
# transcript) before the JSON was actually complete.
#
# 2026-07-23 follow-up: the first value tried here (8192) fixed the
# truncation problem but then hit a DIFFERENT wall - Groq's account-
# level tokens-per-minute (TPM) rate limit (HTTP 413, "Request too
# large", org's on_demand tier capped at 8000 TPM for gpt-oss-120b).
# Prompt tokens count against the same TPM budget as max_tokens, so
# a long transcript's prompt PLUS an 8192-token response reservation
# could together exceed the account's limit even before generation
# started. Lowered to a more conservative value as a middle ground:
# less headroom for a very long ride day's IntelliScript response
# (truncation could theoretically return if a single day's kept
# transcript segments push the response past this), but far less
# likely to collide with the account's TPM ceiling than 8192 was.
# If truncation reappears on a genuinely long transcript, raise this
# - but raising it also raises 413 risk again, so treat the two
# failure modes as a real tradeoff, not something to "solve" by
# picking a bigger number. A proper fix (upgrading Groq's account
# tier, or chunking very long transcripts into multiple requests)
# would remove this tradeoff entirely, but neither is built here.
DEFAULT_MAX_TOKENS = 4096


class GroqError(RuntimeError):
    """
    Raised when Groq can't be reached, rejects the API key, or
    returns something unparseable - always with a clear, actionable
    message rather than a bare urllib traceback.
    """


class GroqProvider:
    """
    Implements the AIProvider protocol (see ai_provider.py) against
    Groq's OpenAI-compatible chat completions endpoint.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_GROQ_MODEL,
        host: str = "https://api.groq.com/openai/v1",
        timeout_seconds: float = 120.0,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        if not api_key or not api_key.strip():
            raise GroqError(
                "No Groq API key was provided. Add one in Settings -> "
                "AI Provider, or get a free key at console.groq.com."
            )
        self.api_key = api_key
        self.model = model
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        Sends prompt (and optional system_prompt, mapped to a
        standard OpenAI-style "system" role message) to Groq and
        returns the generated text.

        Raises GroqError (never a bare urllib exception) if Groq
        isn't reachable, the API key is rejected, the model name is
        wrong, or the response can't be parsed.
        """

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_body = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "max_tokens": self.max_tokens,
        }

        # ML-067: reasoning-capable models spend part of their token
        # budget on invisible "thinking" before answering, which both
        # eats into max_tokens (leaving less room for the actual JSON)
        # and, per Groq's own docs/community reports, can sometimes
        # interfere with getting clean JSON back. Ask for the least
        # reasoning each model family supports. Matched by substring
        # rather than an exhaustive model list since Groq's lineup
        # changes over time - a model that matches neither pattern
        # simply gets no reasoning_effort field at all, which is safe
        # (omitting it is always valid; guessing a value for an
        # unsupported model could make Groq reject the request).
        model_lower = self.model.lower()
        if "gpt-oss" in model_lower:
            request_body["reasoning_effort"] = "low"
        elif "qwen" in model_lower:
            request_body["reasoning_effort"] = "none"

        payload = json.dumps(request_body).encode("utf-8")

        request = urllib.request.Request(
            f"{self.host}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                # Cloudflare fronts Groq's API and blocks requests
                # carrying urllib's default User-Agent signature
                # ("Python-urllib/3.x") with HTTP 403 / error code
                # 1010 ("Access Denied: bad bot") - confirmed via a
                # Groq community forum thread hitting this exact
                # error. A normal-looking User-Agent avoids it.
                "User-Agent": "SBA-AI-Studio/1.0",
            },
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
            if exc.code == 401:
                raise GroqError(
                    "Groq rejected the API key (HTTP 401). Check the "
                    "key in Settings -> AI Provider, or generate a new "
                    "one at console.groq.com."
                ) from exc
            if exc.code == 429:
                raise GroqError(
                    "Groq's free-tier rate limit was hit (HTTP 429). "
                    "Wait a moment and try again."
                ) from exc
            raise GroqError(
                f"Groq returned an error (HTTP {exc.code}) for model "
                f"'{self.model}'. Details: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise GroqError(
                f"Could not reach Groq at {self.host}. Check your "
                f"internet connection. Details: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise GroqError(
                f"Groq did not respond within {self.timeout_seconds:.0f}s. "
                f"Try again."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GroqError(
                f"Groq's response wasn't valid JSON: {raw[:200]!r}"
            ) from exc

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise GroqError(
                f"Groq's response had no 'choices': {data!r}"
            )

        text = choices[0].get("message", {}).get("content")
        if not isinstance(text, str):
            raise GroqError(
                f"Groq's response had no message content: {data!r}"
            )

        return text