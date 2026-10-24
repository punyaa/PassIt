"""Text-completion client for listing price suggestions.

Selection (first match wins):
  1. PASSIT_BEDROCK_MODEL_ID set            -> BedrockLlmClient (AWS, IAM-authenticated)
  2. PASSIT_LLM_API_URL set                 -> HttpLlmClient (OpenAI-compatible chat API,
                                               e.g. the NUS-provided model service)
  3. neither                                -> None; callers use the heuristic fallback

Callers must treat every failure (timeout, throttling, bad JSON) as "use the heuristic":
listing creation is never blocked on the model.

B3/P1 hand-off for Bedrock (see api/README.md, "AWS hand-off"):
  1. Enable the model in the Bedrock console for ap-southeast-1.
  2. Grant the ECS task role bedrock:InvokeModel (and bedrock:ApplyGuardrail if used).
  3. `uv add --project api boto3`, set PASSIT_BEDROCK_MODEL_ID.
"""

import asyncio
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import Settings, get_settings


class LlmClient(Protocol):
    name: str

    async def complete(self, prompt: str) -> str: ...


class HttpLlmClient:
    name = "http"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def complete(self, prompt: str) -> str:
        headers = {}
        if self.settings.llm_api_key:
            headers["authorization"] = f"Bearer {self.settings.llm_api_key}"
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 300,
        }
        if self.settings.llm_model:
            body["model"] = self.settings.llm_model
        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.llm_api_url.rstrip('/')}/chat/completions",
                json=body,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


class BedrockLlmClient:
    """AWS implementation. UNVERIFIED until the model is enabled in the team account."""

    name = "bedrock"

    def __init__(self, settings: Settings) -> None:
        try:
            import boto3  # noqa: PLC0415 - optional dependency until AWS is provisioned
            from botocore.config import Config  # noqa: PLC0415
        except ImportError as error:
            raise RuntimeError("Add boto3: `uv add --project api boto3`") from error
        session = boto3.Session(profile_name=settings.aws_profile or None)
        timeout = settings.llm_timeout_seconds
        self.client = session.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            config=Config(
                read_timeout=timeout, connect_timeout=timeout, retries={"max_attempts": 1}
            ),
        )
        self.settings = settings

    async def complete(self, prompt: str) -> str:
        request = {
            "modelId": self.settings.bedrock_model_id,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 300, "temperature": 0.2},
        }
        if self.settings.bedrock_guardrail_id:
            request["guardrailConfig"] = {
                "guardrailIdentifier": self.settings.bedrock_guardrail_id,
                "guardrailVersion": self.settings.bedrock_guardrail_version or "DRAFT",
            }
        response = await asyncio.to_thread(self.client.converse, **request)
        return response["output"]["message"]["content"][0]["text"]


def _configured(value: str | None) -> bool:
    return bool(value) and not value.startswith("replace-with")


@lru_cache
def get_llm_client() -> LlmClient | None:
    settings = get_settings()
    if _configured(settings.bedrock_model_id):
        return BedrockLlmClient(settings)
    if _configured(settings.llm_api_url):
        return HttpLlmClient(settings)
    return None
