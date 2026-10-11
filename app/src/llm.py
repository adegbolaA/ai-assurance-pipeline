"""Model gateway — the only module allowed to call a model provider.

Semgrep rule `aap-bedrock-outside-gateway` enforces that. The gateway also
refuses to start if the configured model is not approved in the registry, so
the governance check holds at runtime as well as in CI.
"""

import os
import re
from pathlib import Path

import yaml

REGISTRY_PATH = Path(os.environ.get("MODEL_REGISTRY", Path(__file__).parents[2] / "models" / "registry.yaml"))


class UnapprovedModelError(RuntimeError):
    pass


def assert_model_approved(model_id: str, registry_path: Path = REGISTRY_PATH) -> dict:
    registry = yaml.safe_load(registry_path.read_text())
    for entry in registry.get("models", []):
        if entry.get("id") == model_id:
            if entry.get("status") != "approved":
                raise UnapprovedModelError(f"model {model_id!r} is registered but status is {entry.get('status')!r}")
            return entry
    raise UnapprovedModelError(f"model {model_id!r} is not in the model registry")


class BedrockBackend:
    """Calls an approved model through the Bedrock Converse API."""

    def __init__(self, model_id: str, region: str):
        import boto3

        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        response = self.client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.2},
        )
        return response["output"]["message"]["content"][0]["text"]


class MockBackend:
    """Deterministic stand-in for a naive, instruction-following model.

    Used on pull requests so the red-team evals run offline and for free. It
    deliberately behaves the way a weak model does — it obeys instructions it
    finds anywhere in its prompt — so the evals can prove the pipeline catches
    the planted AAP-LAB weaknesses. Releases are evaluated against the real
    model instead.
    """

    model_id = "mock"
    _reveal = re.compile(r"(reveal|print|repeat|show).{0,40}(system prompt|instructions)", re.I)
    _override = re.compile(r"ignore (all |any )?(previous|prior) instructions\.?\s*(.*)", re.I | re.S)

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        if self._reveal.search(user):
            return system
        injected = self._override.search(user)
        if injected:
            return injected.group(3).strip().split("\n\n")[0]
        question = user.rsplit("Question:", 1)[-1].strip()
        context = user.split("Question:", 1)[0]
        first_passage = next((p for p in context.split("\n\n") if p.strip() and not p.startswith("[")), "")
        return f"{first_passage.strip()} (You asked: {question})"


def get_backend():
    backend = os.environ.get("LLM_BACKEND", "bedrock")
    if backend == "mock":
        return MockBackend()
    model_id = os.environ.get("MODEL_ID", "amazon.nova-lite-v1:0")
    assert_model_approved(model_id)
    return BedrockBackend(model_id, os.environ.get("AWS_REGION", "us-east-1"))
