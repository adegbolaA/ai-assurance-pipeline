import os
from pathlib import Path

import pytest

os.environ["LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402
from src.llm import UnapprovedModelError, assert_model_approved  # noqa: E402
from src.main import app  # noqa: E402
from src.retriever import load_corpus, retrieve  # noqa: E402

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok", "model": "mock"}


def test_answer_cites_retrieved_source():
    body = client.post("/ask", json={"question": "What are the income limits for a four-person household?"}).json()
    assert "income-limits.md" in body["sources"]
    assert "44,900" in body["answer"]


def test_retriever_ranks_relevant_document_first():
    hits = retrieve("full time students eligible", load_corpus())
    assert hits[0].source == "eligibility.md"


def test_registered_model_is_approved():
    assert assert_model_approved("amazon.nova-lite-v1:0")["status"] == "approved"


def test_unregistered_model_is_refused():
    with pytest.raises(UnapprovedModelError, match="not in the model registry"):
        assert_model_approved("some-unvetted-model")


def test_unapproved_model_is_refused(tmp_path: Path):
    registry = tmp_path / "registry.yaml"
    registry.write_text("models:\n  - id: m1\n    status: pending\n")
    with pytest.raises(UnapprovedModelError, match="status is 'pending'"):
        assert_model_approved("m1", registry)


# AIGG-LAB-04 is planted, so this guard is expected to fail. strict=True turns
# a fix into a failure too, prompting removal of the marker and the POA&M item.
@pytest.mark.xfail(strict=True, reason="AIGG-LAB-04 planted: no input or max_tokens cap")
def test_aigg_lab_04_oversized_request_rejected():
    resp = client.post("/ask", json={"question": "income " * 20000, "max_tokens": 200000})
    assert resp.status_code == 422
