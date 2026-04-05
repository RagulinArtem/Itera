from __future__ import annotations

import asyncio
import json
import logging
import re

from openai import AsyncOpenAI

from bot.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


def parse_llm_json(content: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = re.sub(r"```json\s*", "", content)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise


async def call_llm(
    system_prompt: str,
    user_message: str,
    model: str,
    max_retries: int = 3,
) -> dict:
    """Call OpenAI chat completion with retry and JSON parsing."""
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                timeout=60.0,
            )
            raw = response.choices[0].message.content
            return parse_llm_json(raw)
        except Exception as e:
            logger.warning("LLM call attempt %d failed: %s", attempt + 1, e)
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Unreachable")
