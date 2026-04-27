from __future__ import annotations

import os

from openai import APIConnectionError, APITimeoutError, APIStatusError, OpenAI, RateLimitError


class LLMUnavailableError(Exception):
    """Raised when the LLM cannot be used for this request."""


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise LLMUnavailableError("OPENAI_API_KEY is not set")

        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self._client = OpenAI(api_key=resolved_api_key, max_retries=0)

    def chat(self, system: str, user: str, max_tokens: int = 300) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
            )
        except (APIConnectionError, APITimeoutError, RateLimitError, APIStatusError) as exc:
            raise LLMUnavailableError(str(exc)) from exc

        content = response.choices[0].message.content
        if isinstance(content, str):
            return content.strip()
        return str(content).strip()
