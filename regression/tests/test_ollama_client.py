"""
============================================================
SBA AI Studio
Ollama Client Regression Test
ML-026
Version : 1.0.0
============================================================

Verifies OllamaClient without any real network access or a
real Ollama instance - all urlopen calls are mocked:

- A successful response is parsed and its "response" text
  returned.
- A connection failure (Ollama not running) raises OllamaError
  with an actionable message, not a bare urllib exception.
- An HTTP error (e.g. model not found) raises OllamaError
  naming the model and suggesting 'ollama pull'.
- A malformed/unexpected JSON response raises OllamaError
  rather than crashing on a KeyError/JSONDecodeError.
"""

from __future__ import annotations

import json

from regression.base_test import BaseRegressionTest


class OllamaClientRegressionTest(BaseRegressionTest):

    name = "Ollama Client (ML-026)"

    category = "Planning"

    description = (
        "Verify Ollama client success parsing and clear error "
        "messages on connection/HTTP/parse failures, using a "
        "mocked HTTP layer (no real Ollama instance required)."
    )

    def run(self) -> None:

        import urllib.error

        import sba_resolve.core.services.ollama_client as ollama_module
        from sba_resolve.core.services.ollama_client import (
            OllamaClient,
            OllamaError,
        )

        original_urlopen = ollama_module.urllib.request.urlopen

        class FakeResponse:
            def __init__(self, body: bytes):
                self._body = body

            def read(self):
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        try:

            # --------------------------------------------------
            # 1. Successful generation.
            # --------------------------------------------------

            success_body = json.dumps(
                {"response": "Generated text here."}
            ).encode("utf-8")

            ollama_module.urllib.request.urlopen = (
                lambda *a, **k: FakeResponse(success_body)
            )

            client = OllamaClient(model="llama3.2")

            result = client.generate("test prompt")

            if result != "Generated text here.":
                raise RuntimeError(
                    f"Expected 'Generated text here.', got {result!r}."
                )

            # --------------------------------------------------
            # 2. Connection failure - Ollama not running.
            # --------------------------------------------------

            def connection_failure(*args, **kwargs):
                raise urllib.error.URLError("Connection refused")

            ollama_module.urllib.request.urlopen = connection_failure

            try:
                client.generate("test prompt")
                raise RuntimeError(
                    "Expected OllamaError for a connection failure."
                )
            except OllamaError as exc:
                if "running" not in str(exc).lower():
                    raise RuntimeError(
                        "Expected the connection-failure error to "
                        f"mention checking if Ollama is running, "
                        f"got: {exc}"
                    )

            # --------------------------------------------------
            # 3. HTTP error - e.g. model not found.
            # --------------------------------------------------

            def http_error(*args, **kwargs):
                raise urllib.error.HTTPError(
                    url="http://localhost:11434/api/generate",
                    code=404,
                    msg="Not Found",
                    hdrs=None,
                    fp=FakeResponse(b"model not found"),
                )

            ollama_module.urllib.request.urlopen = http_error

            try:
                client.generate("test prompt")
                raise RuntimeError(
                    "Expected OllamaError for an HTTP error."
                )
            except OllamaError as exc:
                if "pull" not in str(exc).lower():
                    raise RuntimeError(
                        "Expected the HTTP-error message to "
                        f"suggest 'ollama pull', got: {exc}"
                    )

            # --------------------------------------------------
            # 4. Malformed JSON response.
            # --------------------------------------------------

            ollama_module.urllib.request.urlopen = (
                lambda *a, **k: FakeResponse(b"{not valid json")
            )

            try:
                client.generate("test prompt")
                raise RuntimeError(
                    "Expected OllamaError for malformed JSON."
                )
            except OllamaError:
                pass

            # --------------------------------------------------
            # 5. Valid JSON but missing "response" field.
            # --------------------------------------------------

            ollama_module.urllib.request.urlopen = (
                lambda *a, **k: FakeResponse(
                    json.dumps({"unexpected": "shape"}).encode("utf-8")
                )
            )

            try:
                client.generate("test prompt")
                raise RuntimeError(
                    "Expected OllamaError for a missing 'response' "
                    "field."
                )
            except OllamaError:
                pass

        finally:
            ollama_module.urllib.request.urlopen = original_urlopen
