from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Persian news editor. Return only valid JSON.
"""

PROMPT_TEMPLATE = """
Summarize the Persian news text below.

Requirements:
- Write a concise summary of 2-3 sentences.
- Extract 3-6 key points as short phrases.
- Extract 3-6 bullet key facts as complete short sentences.
- Keep output brief and faithful to the source.

Return JSON with exactly these keys:
summary: string
key_points: array of strings
key_facts: array of strings

Text:
{clean_text}
""".strip()


class SummarizationError(RuntimeError):
    """Raised when summarization fails or returns invalid output."""


@dataclass(frozen=True)
class NewsSummary:
    cleaned_text: str
    summary: str
    key_points: list[str]
    key_facts: list[str]


class NewsSummarizerService:
    """Summarize Persian news text with OpenAI responses API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        max_output_tokens: int = 400,
        max_input_chars: int = 8000,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._max_input_chars = max_input_chars

    def clean_text(self, raw_text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", raw_text)
        text = text.replace("\u200c", " ")
        text = re.sub(r"[\t\r\f\v]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    def _truncate(self, text: str) -> str:
        if len(text) <= self._max_input_chars:
            return text
        logger.debug("Truncating input from %s to %s chars", len(text), self._max_input_chars)
        return text[: self._max_input_chars].rstrip()

    async def summarize(self, raw_text: str) -> NewsSummary:
        cleaned = self.clean_text(raw_text)
        if not cleaned:
            raise SummarizationError("No content to summarize.")

        prompt = PROMPT_TEMPLATE.format(clean_text=self._truncate(cleaned))

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_output_tokens=self._max_output_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - surface OpenAI errors as summarization failures
            raise SummarizationError("OpenAI request failed.") from exc

        content = getattr(response, "output_text", None)
        if not content:
            raise SummarizationError("OpenAI returned empty response.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SummarizationError("OpenAI returned invalid JSON.") from exc

        summary = payload.get("summary")
        key_points = payload.get("key_points")
        key_facts = payload.get("key_facts")

        if not summary or not isinstance(key_points, list) or not isinstance(key_facts, list):
            raise SummarizationError("OpenAI response missing required fields.")

        return NewsSummary(
            cleaned_text=cleaned,
            summary=summary.strip(),
            key_points=[str(item).strip() for item in key_points if str(item).strip()],
            key_facts=[str(item).strip() for item in key_facts if str(item).strip()],
        )
