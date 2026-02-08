from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional Persian financial editor. Return only valid JSON."""

PROMPT_TEMPLATE = """
Generate 3 Persian headline variants for the summarized economic news below.

Constraints:
- Telegram-optimized
- Max 90 characters each
- No clickbait, no exaggeration
- Keep accurate and neutral tone
- Output Persian text only

Headline types:
1) Problem-oriented
2) Number-driven
3) Question-based

Return JSON with exactly these keys:
problem_headline: string
number_headline: string
question_headline: string

Summary:
{summary}
""".strip()


class HeadlineGenerationError(RuntimeError):
    """Raised when headline generation fails or returns invalid output."""


@dataclass(frozen=True)
class HeadlineVariants:
    problem_headline: str
    number_headline: str
    question_headline: str


class HeadlineGeneratorService:
    """Generate Persian economic news headlines with OpenAI responses API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        max_output_tokens: int = 200,
        max_input_chars: int = 4000,
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

    async def generate(self, summarized_text: str) -> HeadlineVariants:
        cleaned = summarized_text.strip()
        if not cleaned:
            raise HeadlineGenerationError("No summary provided.")

        prompt = PROMPT_TEMPLATE.format(summary=self._truncate(cleaned))

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
            raise HeadlineGenerationError("OpenAI request failed.") from exc

        content = getattr(response, "output_text", None)
        if not content:
            raise HeadlineGenerationError("OpenAI returned empty response.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise HeadlineGenerationError("OpenAI returned invalid JSON.") from exc

        problem = payload.get("problem_headline")
        number = payload.get("number_headline")
        question = payload.get("question_headline")

        if not all(isinstance(item, str) and item.strip() for item in [problem, number, question]):
            raise HeadlineGenerationError("OpenAI response missing required fields.")

        return HeadlineVariants(
            problem_headline=problem.strip(),
            number_headline=number.strip(),
            question_headline=question.strip(),
        )
