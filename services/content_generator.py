from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional Persian economic editor. Return only valid JSON."""

PROMPT_TEMPLATE = """
Create Telegram-ready economic content from the inputs below.

Constraints:
- Persian language only
- Neutral, factual tone
- Avoid clickbait or sales language
- Keep each section concise

Content type options: short, analytical, educational, table-number

Return JSON with exactly these keys:
lead: string (1-2 lines)
body: string
analysis: string (why this matters)
cta: string (soft, neutral CTA)

Inputs:
Headline: {headline}
Summary: {summary}
Key facts: {key_facts}
Content type: {content_type}
""".strip()


class ContentType(str, Enum):
    short = "short"
    analytical = "analytical"
    educational = "educational"
    table_number = "table-number"


class ContentGenerationError(RuntimeError):
    """Raised when content generation fails or returns invalid output."""


@dataclass(frozen=True)
class TelegramContent:
    lead: str
    body: str
    analysis: str
    cta: str


class ContentGeneratorService:
    """Generate Telegram-ready economic content with OpenAI responses API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        max_output_tokens: int = 500,
        max_input_chars: int = 6000,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._max_input_chars = max_input_chars

    def _truncate(self, text: str) -> str:
        if len(text) <= self._max_input_chars:
            return text
        logger.debug("Truncating input from %s to %s chars", len(text), self._max_input_chars)
        return text[: self._max_input_chars].rstrip()

    async def generate(
        self,
        headline: str,
        summary: str,
        key_facts: list[str],
        content_type: ContentType,
    ) -> TelegramContent:
        if not headline.strip():
            raise ContentGenerationError("Headline is required.")
        if not summary.strip():
            raise ContentGenerationError("Summary is required.")
        if not key_facts:
            raise ContentGenerationError("Key facts are required.")

        facts_text = " | ".join(item.strip() for item in key_facts if item.strip())
        if not facts_text:
            raise ContentGenerationError("Key facts are required.")

        prompt = PROMPT_TEMPLATE.format(
            headline=self._truncate(headline.strip()),
            summary=self._truncate(summary.strip()),
            key_facts=self._truncate(facts_text),
            content_type=content_type.value,
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_output_tokens=self._max_output_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - surface OpenAI errors as generation failures
            raise ContentGenerationError("OpenAI request failed.") from exc

        content = getattr(response, "output_text", None)
        if not content:
            raise ContentGenerationError("OpenAI returned empty response.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ContentGenerationError("OpenAI returned invalid JSON.") from exc

        lead = payload.get("lead")
        body = payload.get("body")
        analysis = payload.get("analysis")
        cta = payload.get("cta")

        if not all(isinstance(item, str) and item.strip() for item in [lead, body, analysis, cta]):
            raise ContentGenerationError("OpenAI response missing required fields.")

        return TelegramContent(
            lead=lead.strip(),
            body=body.strip(),
            analysis=analysis.strip(),
            cta=cta.strip(),
        )
